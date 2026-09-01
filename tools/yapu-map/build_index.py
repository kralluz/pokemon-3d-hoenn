"""Indice guid -> caminho do asset no ExportedProject do AssetRipper.
Le so o cabecalho de cada .meta (o guid esta nas primeiras linhas)."""
import os, json, sys, time

ROOT = r"YAPU_Demo/Ripped/ExportedProject/Assets"
OUT = r"tools/yapu-map/guid_index.json"

idx = {}
n = 0
t0 = time.time()
for root, dirs, files in os.walk(ROOT):
    for f in files:
        if not f.endswith(".meta"): continue
        p = os.path.join(root, f)
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for _ in range(6):
                    line = fh.readline()
                    if not line: break
                    if line.startswith("guid:"):
                        idx[line[5:].strip()] = p[:-5].replace("\\", "/")
                        break
        except OSError:
            continue
        n += 1
        if n % 20000 == 0:
            print(f"  {n} metas, {len(idx)} guids, {time.time()-t0:.0f}s", flush=True)

json.dump(idx, open(OUT, "w", encoding="utf-8"))
print(f"metas: {n} | guids: {len(idx)} | {time.time()-t0:.0f}s -> {OUT}")
