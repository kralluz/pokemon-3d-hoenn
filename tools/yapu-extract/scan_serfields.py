"""Recupera os marcadores [SerializeField]/[NonSerialized] do codigo-fonte do YAPU.

Necessario porque o Cpp2IL apaga atributos customizados ao reconstruir o
Assembly-CSharp.dll a partir da build IL2CPP, e sem eles nao da para saber
quais campos privados o Unity serializa.
"""
import os, re, json

SRC = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serfields.json")

line_c  = re.compile(r'//.*?$', re.M)
block_c = re.compile(r'/\*.*?\*/', re.S)
ns_re   = re.compile(r'\bnamespace\s+([\w\.]+)')
cls_re  = re.compile(r'\b(?:class|struct)\s+(\w+)')
ident   = re.compile(r'[A-Za-z_]\w*')

def skip_noise(text, i):
    """Advance past whitespace, further [Attribute(...)] groups and #if/#endif lines."""
    while i < len(text):
        while i < len(text) and text[i].isspace(): i += 1
        if i >= len(text): return i
        if text[i] == '#':
            i = text.find("\n", i)
            if i < 0: return len(text)
            continue
        if text[i] != '[': return i
        depth = 0
        while i < len(text):
            if text[i] == '[': depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0: i += 1; break
            i += 1
    return i

def owner(text, pos):
    ns = cls = ""
    for m in ns_re.finditer(text, 0, pos): ns = m.group(1)
    for m in cls_re.finditer(text, 0, pos): cls = m.group(1)
    return ns, cls

ser, nonser = set(), set()
for root, _, files in os.walk(SRC):
    for fn in files:
        if not fn.endswith(".cs"): continue
        text = block_c.sub("", line_c.sub("", open(os.path.join(root, fn), encoding="utf-8-sig", errors="replace").read()))
        for attr, bucket in (("[SerializeField]", ser), ("[NonSerialized]", nonser)):
            start = 0
            while True:
                i = text.find(attr, start)
                if i < 0: break
                start = i + len(attr)
                seg = text[skip_noise(text, start):][:600]
                cut = min([p for p in (seg.find(";"), seg.find("=")) if p >= 0] or [-1])
                if cut < 0: continue
                seg = seg[:cut]
                if "(" in seg or "{" in seg: continue      # property or method, not a field
                names = ident.findall(seg)
                if not names: continue
                ns, cls = owner(text, i)
                bucket.add(f"{ns}.{cls}.{names[-1]}")

# Runtime-only private fields in third-party assemblies. We have no C# source for those,
# so the default there is "assume Unity serializes private fields" -- which is wrong for
# these caches/flags. Each entry below was pinned down by the byte-consumption check.
nonser.update({
    "WhateverDevs.TwoDAudio.Runtime.AudioLibrary.initialized",
})

json.dump({"serialize": sorted(ser), "nonSerialized": sorted(nonser)},
          open(OUT, "w", encoding="utf-8"), indent=1)
print("SerializeField:", len(ser), " NonSerialized:", len(nonser))
for k in ("OnCalculateNatureToPassOnBreedingItemEffects","DataByForm","DocsURL","OtherLearnMoves","GrowthData"):
    print("  ", k, "->", bool([x for x in ser if x.endswith("." + k)]))
