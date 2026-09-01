import os, csv, collections, re, UnityPy
DATA = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\YAPUDevWindows\YapuDev_Data"
RIP  = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\Ripped\ExportedProject\Assets"
IDX  = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\extracted\_monobehaviour_index.csv"
OUT  = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\extracted\MonoBehaviour_raw"

name2cls = {}
for r in csv.DictReader(open(IDX, encoding="utf-8")):
    name2cls.setdefault(r["name"], r["script_class"])

failed_classes, failed_names = set(), set()
for root, _, fs in os.walk(RIP):
    for f in fs:
        if not f.endswith(".asset"): continue
        p = os.path.join(root, f)
        if sum(1 for _ in open(p, encoding="utf-8", errors="replace")) <= 14:
            n = os.path.splitext(f)[0]
            failed_names.add(n)
            failed_classes.add(name2cls.get(n, "?"))
failed_classes.discard("?")
print("classes com layout não resolvido:", len(failed_classes))

SAFE = re.compile(r'[^A-Za-z0-9._ #\-\(\)\[\]+]')
stats = collections.Counter()
files = [os.path.join(DATA, n) for n in sorted(os.listdir(DATA))
         if os.path.isfile(os.path.join(DATA, n))
         and not n.endswith(('.resS', '.resource', '.json', '.config', '.info', '.dll'))]

manifest = []
for p in files:
    src = os.path.basename(p)
    try: env = UnityPy.load(p)
    except Exception: continue
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour": continue
        try:
            d = obj.read(check_read=False)
            name = getattr(d, "m_Name", "") or ""
            cls = d.m_Script.read().m_ClassName if d.m_Script else ""
        except Exception:
            continue
        if cls not in failed_classes and name not in failed_names: continue
        folder = os.path.join(OUT, SAFE.sub("_", cls) or "_unknown")
        os.makedirs(folder, exist_ok=True)
        fn = (SAFE.sub("_", name)[:100] or f"pathid_{obj.path_id}") + f"__{obj.path_id}.bin"
        raw = obj.get_raw_data()
        with open(os.path.join(folder, fn), "wb") as f: f.write(raw)
        manifest.append((cls, name, src, str(obj.path_id), str(len(raw))))
        stats[cls] += 1

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "_manifest.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["script_class","name","source_file","path_id","raw_bytes"]); w.writerows(manifest)
for k, v in stats.most_common(15): print(f"{v:6d}  {k}")
print("total dumped:", sum(stats.values()))
