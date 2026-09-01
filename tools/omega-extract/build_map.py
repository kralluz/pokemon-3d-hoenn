"""Descobre qual AssetName corresponde a cada arquivo GUID do asset pack."""
import base64, collections, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import omega

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"apk/_extracted/pack/assets"

man = omega.read_manifest(os.path.join(ROOT, "75A02161-4E73-5433-27EF-01F68878B63D", omega.MANIFEST))
print(f"manifesto: {len(man)} entradas")

by_key = collections.defaultdict(list)
for e in man:
    b = base64.b64encode(e["name"].encode())
    by_key[(len(b), bytes(b[:8]))].append(e["name"])
lens = sorted({L for L, _ in by_key})

files = [os.path.join(dp, x) for dp, _, fn in os.walk(ROOT) for x in fn]
mapping, stat = {}, collections.Counter()
for fp in files:
    data = open(fp, "rb").read()
    hits = []
    for L in lens:
        pre = omega.prefix8(data, L)
        if pre is None:
            continue
        for nm in by_key.get((L, pre), []):
            if omega.valid(data, nm):
                hits.append(nm)
    if len(hits) > 1:
        hits = [nm for nm in hits if omega.valid_full(data, nm)]
    rel = os.path.relpath(fp, ROOT).replace("\\", "/")
    if len(hits) == 1:
        mapping[rel] = hits[0]; stat["ok"] += 1
    else:
        stat["ambiguo" if hits else "sem match"] += 1
        if not hits and stat["sem match"] <= 5:
            print("  sem match:", rel, len(data))

print(dict(stat))
json.dump(mapping, open(os.path.join(os.path.dirname(__file__), "abmap.json"), "w"), indent=0)
print("mapa salvo em tools/omega-extract/abmap.json")
