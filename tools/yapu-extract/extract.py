import os, sys, re, json, collections, traceback
import UnityPy

DATA = sys.argv[1]
OUT  = sys.argv[2]
ONLY = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None

SAFE = re.compile(r'[^A-Za-z0-9._ #\-\(\)\[\]+]')
def safe(n, fallback):
    n = SAFE.sub("_", (n or "").strip())[:120]
    return n or fallback

def uniq(path):
    if not os.path.exists(path): return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base}#{i}{ext}"): i += 1
    return f"{base}#{i}{ext}"

def jdefault(o):
    if isinstance(o, bytes): return o.hex()
    for a in ("__dict__",):
        if hasattr(o, a): return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
    return str(o)

stats = collections.Counter()
MB_INDEX = []
errors = []

files = []
for n in sorted(os.listdir(DATA)):
    p = os.path.join(DATA, n)
    if os.path.isfile(p) and not n.endswith(('.resS','.resource','.json','.config','.info','.dll')):
        files.append(p)

for idx, p in enumerate(files, 1):
    src = os.path.basename(p)
    print(f"[{idx}/{len(files)}] {src}", flush=True)
    try:
        env = UnityPy.load(p)
    except Exception as e:
        errors.append((src, "-", "load", repr(e))); continue

    for obj in env.objects:
        t = obj.type.name
        if ONLY and t not in ONLY: continue
        if t not in ("Texture2D", "Sprite", "AudioClip", "TextAsset", "MonoBehaviour", "Font", "Mesh"):
            continue
        try:
            d = obj.read(check_read=(t != "MonoBehaviour"))
            name = safe(getattr(d, "m_Name", ""), f"{t}_{obj.path_id}")

            if t in ("Texture2D", "Sprite"):
                dst = uniq(os.path.join(OUT, t, src, name + ".png"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                img = d.image
                if img is None or img.width == 0 or img.height == 0:
                    stats["skip_empty_" + t] += 1; continue
                img.save(dst)

            elif t == "AudioClip":
                samples = d.samples
                if not samples: stats["skip_empty_AudioClip"] += 1; continue
                for sname, sdata in samples.items():
                    dst = uniq(os.path.join(OUT, "AudioClip", src, safe(sname, name)))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(dst, "wb") as f: f.write(sdata)

            elif t == "TextAsset":
                dst = uniq(os.path.join(OUT, "TextAsset", src, name + ".bytes"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                raw = d.m_Script
                with open(dst, "wb") as f:
                    f.write(raw.encode("utf-8", "surrogateescape") if isinstance(raw, str) else raw)

            elif t == "Font":
                raw = d.m_FontData
                if not raw: stats["skip_empty_Font"] += 1; continue
                ext = ".otf" if raw[:4] == b"OTTO" else ".ttf"
                dst = uniq(os.path.join(OUT, "Font", src, name + ext))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f: f.write(raw)

            elif t == "Mesh":
                dst = uniq(os.path.join(OUT, "Mesh", src, name + ".obj"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "w", encoding="utf-8") as f: f.write(d.export())

            elif t == "MonoBehaviour":
                script = ""
                try:
                    sp = d.m_Script
                    if sp: script = sp.read().m_ClassName or ""
                except Exception: pass
                MB_INDEX.append((src, str(obj.path_id), script, getattr(d, "m_Name", "") or ""))

            stats[t] += 1
        except Exception as e:
            stats["err_" + t] += 1
            if len(errors) < 400: errors.append((src, t, str(getattr(obj, "path_id", "?")), repr(e)[:200]))

os.makedirs(OUT, exist_ok=True)
import csv
with open(os.path.join(OUT, "_monobehaviour_index.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["file", "path_id", "script_class", "name"]); w.writerows(MB_INDEX)
with open(os.path.join(OUT, "_extraction_report.txt"), "w", encoding="utf-8") as f:
    for k, v in sorted(stats.items()): f.write(f"{v:8d}  {k}\n")
    f.write("\n--- errors (first 400) ---\n")
    for e in errors: f.write(" | ".join(e) + "\n")
print("\n=== DONE ===")
for k, v in sorted(stats.items()): print(f"{v:8d}  {k}")
print(f"errors logged: {len(errors)}")
