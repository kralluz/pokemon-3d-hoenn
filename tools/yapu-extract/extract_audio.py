"""Passe de audio: o UnityPy nao resolve o .resource externo ao carregar os
arquivos soltos, entao m_AudioData vem vazio e o FMOD reprova com FORMAT.
Aqui os bytes do banco FSB5 sao lidos a mao do .resource antes de decodificar."""
import os, re, sys, collections
import UnityPy

D = r"YAPU_Demo/YAPUDevWindows/YapuDev_Data"
OUT = r"YAPU_Demo/extracted/AudioClip"

def safe(n, fallback):
    n = re.sub(r'[<>:"/\|?*\x00-\x1f]', "_", (n or "").strip()) or fallback
    return n[:120]

def uniq(p):
    if not os.path.exists(p): return p
    base, ext = os.path.splitext(p)
    i = 1
    while os.path.exists(f"{base}_{i}{ext}"): i += 1
    return f"{base}_{i}{ext}"

stats = collections.Counter()
errors = []
srcs = sorted(f for f in os.listdir(D)
              if f.endswith(".assets") or re.fullmatch(r"level\d+", f)
              or f in ("globalgamemanagers",))

for src in srcs:
    try:
        env = UnityPy.load(os.path.join(D, src))
    except Exception as e:
        errors.append(f"{src} | load | {e!r}"); continue
    for o in env.objects:
        if o.type.name != "AudioClip": continue
        try:
            d = o.read()
            if not d.m_AudioData:
                r = d.m_Resource
                p = os.path.join(D, os.path.basename(r.m_Source))
                if not os.path.exists(p):
                    stats["skip_no_resource"] += 1; continue
                with open(p, "rb") as f:
                    f.seek(r.m_Offset); d.m_AudioData = f.read(r.m_Size)
            if not d.m_AudioData:
                stats["skip_empty"] += 1; continue
            samples = d.samples
            if not samples:
                stats["skip_no_samples"] += 1; continue
            for sname, sdata in samples.items():
                dst = uniq(os.path.join(OUT, src, safe(sname, f"{o.path_id}.wav")))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f: f.write(sdata)
                stats["wav"] += 1
        except Exception as e:
            stats["err"] += 1
            errors.append(f"{src} | {o.path_id} | {e!r}")

print(dict(stats))
print(f"errors: {len(errors)}")
for e in errors[:40]: print(" ", e)
