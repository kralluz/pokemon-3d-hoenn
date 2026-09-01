"""Exporta os assets dos .ab: TextAsset, Texture2D, Sprite, AudioClip, MonoBehaviour."""
import glob, json, os, sys, time
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.62f2"

SRC   = sys.argv[1] if len(sys.argv) > 1 else r"apk/_extracted/out/bundles"
OUT   = sys.argv[2] if len(sys.argv) > 2 else r"apk/_extracted/out/assets"
SUB   = sys.argv[3] if len(sys.argv) > 3 else "**"
KINDS = set((sys.argv[4] if len(sys.argv) > 4 else
             "TextAsset,Texture2D,Sprite,AudioClip,MonoBehaviour").split(","))

def safe(s):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in str(s))[:120] or "unnamed"

def uniq(path):
    """Evita que assets de mesmo nome no mesmo bundle se sobrescrevam."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{stem}~{i}{ext}"):
        i += 1
    return f"{stem}~{i}{ext}"

def write(path, data, mode="wb"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        fh.write(data)

files = sorted(glob.glob(os.path.join(SRC, SUB, "*.ab"), recursive=True))
t0 = time.time(); stat = {}; errs = []
for i, f in enumerate(files, 1):
    rel = os.path.splitext(os.path.relpath(f, SRC))[0]
    try:
        env = UnityPy.load(f)
    except Exception as e:
        errs.append((rel, repr(e)[:120])); continue
    behaviours = []
    for obj in env.objects:
        k = obj.type.name
        if k not in KINDS:
            continue
        try:
            if k == "MonoBehaviour":
                # um JSON por bundle, nao por objeto (senao viram ~86k arquivinhos)
                behaviours.append(obj.read_typetree())
            else:
                d = obj.read()
                name = safe(getattr(d, "m_Name", "") or f"{k}_{obj.path_id}")
                base = os.path.join(OUT, k, rel, name)
                if k == "TextAsset":
                    raw = (d.m_Script.encode("utf-8", "surrogateescape")
                           if isinstance(d.m_Script, str) else bytes(d.m_Script))
                    write(uniq(base + ".txt"), raw)
                elif k in ("Texture2D", "Sprite"):
                    img = d.image
                    if not img or img.width == 0 or img.height == 0:
                        continue
                    p = uniq(base + ".png")
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    img.save(p)
                elif k == "AudioClip":
                    for sname, wav in d.samples.items():
                        write(uniq(os.path.join(OUT, k, rel, safe(sname))), wav)
            stat[k] = stat.get(k, 0) + 1
        except Exception as e:
            errs.append((f"{rel}/{k}", repr(e)[:110]))
    if behaviours:
        write(os.path.join(OUT, "MonoBehaviour", rel + ".json"),
              json.dumps(behaviours, ensure_ascii=False, indent=1, default=str), "w")
    if i % 400 == 0:
        print(f"  {i}/{len(files)}  {stat}  erros={len(errs)}  {time.time()-t0:.0f}s", flush=True)

print(f"\nexportado de {len(files)} bundles em {time.time()-t0:.0f}s")
for k, v in sorted(stat.items()):
    print(f"  {k:16s} {v}")
print(f"  erros: {len(errs)}")
for e in errs[:8]:
    print("   ", e)
