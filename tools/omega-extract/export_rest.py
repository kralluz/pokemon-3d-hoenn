"""Exporta o que sobrou: Mesh->.obj, Shader/Font em arquivo proprio,
todo o resto como typetree JSON agrupado por bundle."""
import collections, glob, json, os, sys, time
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.62f2"

SRC = sys.argv[1] if len(sys.argv) > 1 else r"apk/_extracted/out/bundles"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"apk/_extracted/out/assets"

# ja exportados em passes anteriores, ou grandes demais para typetree
SKIP = {"TextAsset", "Texture2D", "Sprite", "AudioClip", "MonoBehaviour", "AssetBundle"}

def safe(s):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in str(s))[:120] or "unnamed"

def uniq(p):
    if not os.path.exists(p): return p
    stem, ext = os.path.splitext(p); i = 2
    while os.path.exists(f"{stem}~{i}{ext}"): i += 1
    return f"{stem}~{i}{ext}"

def write(path, data, mode="wb"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        fh.write(data)

files = sorted(glob.glob(os.path.join(SRC, "**", "*.ab"), recursive=True))
t0 = time.time(); stat = collections.Counter(); errs = []
for i, f in enumerate(files, 1):
    rel = os.path.splitext(os.path.relpath(f, SRC))[0]
    try:
        env = UnityPy.load(f)
    except Exception as e:
        errs.append((rel, repr(e)[:110])); continue
    trees = collections.defaultdict(list)
    for obj in env.objects:
        k = obj.type.name
        if k in SKIP: continue
        try:
            if k == "Mesh":
                d = obj.read()
                body = d.export()
                if isinstance(body, str):
                    write(uniq(os.path.join(OUT, "Mesh", rel, safe(d.m_Name) + ".obj")),
                          body.encode("utf-8"))
                else:
                    # mesh sem dados de vertice (gerada em runtime): guarda o typetree
                    trees[k].append(obj.read_typetree())
            elif k == "Shader":
                d = obj.read()
                try: body = d.export()
                except Exception: body = json.dumps(obj.read_typetree(), ensure_ascii=False, default=str)
                write(uniq(os.path.join(OUT, "Shader", rel, safe(d.m_Name) + ".shader")),
                      body.encode("utf-8"))
            elif k == "Font":
                d = obj.read()
                data = getattr(d, "m_FontData", None)
                if not data:
                    trees[k].append(obj.read_typetree()); stat[k + " (json)"] += 1; continue
                ext = ".otf" if bytes(data)[:4] == b"OTTO" else ".ttf"
                write(uniq(os.path.join(OUT, "Font", rel, safe(d.m_Name) + ext)), bytes(data))
            else:
                trees[k].append(obj.read_typetree())
            stat[k] += 1
        except Exception as e:
            errs.append((f"{rel}/{k}", repr(e)[:110]))
    for k, lst in trees.items():
        write(os.path.join(OUT, k, rel + ".json"),
              json.dumps(lst, ensure_ascii=False, indent=1, default=str), "w")
    if i % 400 == 0:
        top = dict(sorted(stat.items(), key=lambda kv: -kv[1])[:5])
        print(f"  {i}/{len(files)}  {top}  erros={len(errs)}  {time.time()-t0:.0f}s", flush=True)

print(f"\nexportado de {len(files)} bundles em {time.time()-t0:.0f}s")
for k, v in sorted(stat.items(), key=lambda kv: -kv[1]):
    print(f"  {k:26s} {v}")
print(f"  erros: {len(errs)}")
for e in errs[:10]: print("   ", e)
