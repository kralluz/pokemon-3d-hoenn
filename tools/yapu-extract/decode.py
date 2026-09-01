"""Decodifica os MonsterEntry da build IL2CPP da demo YAPU.

O layout de serializacao vem de layouts.json (gerado por layout/Program.cs a partir do
Assembly-CSharp.dll reconstruido pelo Cpp2IL + os marcadores [SerializeField] lidos do
codigo-fonte do YAPU, ja que o Cpp2IL apaga os atributos).

Cada objeto so e aceito se o parser consumir exatamente todos os bytes do buffer.
"""
import os, sys, json, struct, collections, UnityPy

DATA    = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\YAPUDevWindows\YapuDev_Data"
LAYOUTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts.json")
OUT     = r"C:\Users\Carlos Henrique\OneDrive\Desktop\pokemon\YAPU_Demo\extracted\MonsterEntry_decoded"
TARGET  = "MonsterEntry"

J        = json.load(open(LAYOUTS, encoding="utf-8"))
layout   = list(J["layouts"].values())[0]
REFTYPES = J["refTypes"]

FMT = {"bool":("<?",1),"u8":("<B",1),"i8":("<b",1),"char":("<B",1),"i16":("<h",2),"u16":("<H",2),
       "i32":("<i",4),"u32":("<I",4),"i64":("<q",8),"u64":("<Q",8),"f32":("<f",4),"f64":("<d",8)}

class Reader:
    def __init__(self, buf): self.b, self.p = buf, 0
    def align(self): self.p = (self.p + 3) & ~3
    def take(self, n):
        if self.p + n > len(self.b): raise EOFError(f"faltam {n} bytes em {self.p}/{len(self.b)}")
        v = self.b[self.p:self.p+n]; self.p += n; return v
    def prim(self, c):
        f, n = FMT[c]; return struct.unpack(f, self.take(n))[0]
    def string(self):
        n = self.prim("i32")
        if n < 0 or self.p + n > len(self.b): raise EOFError(f"tamanho de string invalido {n} em {self.p}")
        v = self.take(n).decode("utf-8", "replace"); self.align(); return v
    def pptr(self): return (self.prim("i32"), self.prim("i64"))

def read_node(r, node, resolve, rids):
    k = node["kind"]
    if k == "prim":
        v = r.prim(node["type"])
        if node.get("align"): r.align()
        return v
    if k == "string": return r.string()
    if k == "pptr":   return resolve(r.pptr())
    if k == "managedref":
        rid = r.prim("i64"); rids.append(rid); return {"$rid": rid}
    if k == "array":
        n = r.prim("i32")
        if n < 0 or n > 5_000_000: raise EOFError(f"contagem de array invalida {n} em {r.p-4}")
        elem = node["elem"]
        # Unity packs arrays of 1- and 2-byte primitives: no padding between elements,
        # a single align at the end.
        if elem["kind"] == "prim" and elem.get("align"):
            v = [r.prim(elem["type"]) for _ in range(n)]
        else:
            v = [read_node(r, elem, resolve, rids) for _ in range(n)]
        r.align(); return v
    if k == "class":
        return {f["name"]: read_node(r, f["node"], resolve, rids) for f in node["fields"]}
    raise ValueError("kind desconhecido: " + k)

def read_registry(r, resolve, rids):
    """ManagedReferencesRegistry: version, depois RefIds[rid, class, ns, asm, dados]."""
    version = r.prim("i32")
    count   = r.prim("i32")
    if count < 0 or count > 100_000: raise EOFError(f"contagem de refs invalida {count}")
    out = {}
    for _ in range(count):
        rid = r.prim("i64")
        cls, ns, asm = r.string(), r.string(), r.string()
        full = f"{ns}.{cls}" if ns else cls
        node = REFTYPES.get(full)
        if node is None: raise EOFError(f"tipo de managed reference desconhecido: {full}")
        obj = read_node(r, node, resolve, rids)
        obj["$type"] = cls
        out[rid] = obj
    return version, out

def splice(value, refs):
    """Troca os marcadores {'$rid': n} pelos objetos do registro."""
    if isinstance(value, dict):
        if set(value) == {"$rid"}:
            rid = value["$rid"]
            if rid in (-1, -2) or rid not in refs: return None
            return splice(refs[rid], refs)
        return {k: splice(v, refs) for k, v in value.items()}
    if isinstance(value, list): return [splice(v, refs) for v in value]
    return value

# ---------------- passo 1: indice global (arquivo, path_id) -> nome ----------------
files = [os.path.join(DATA, n) for n in sorted(os.listdir(DATA))
         if os.path.isfile(os.path.join(DATA, n))
         and not n.endswith((".resS", ".resource", ".json", ".config", ".info", ".dll"))]
WANT = {"MonoBehaviour", "Sprite", "Material", "Texture2D", "AudioClip", "GameObject"}
index, envs = {}, {}
print("indexando objetos...", flush=True)
for p in files:
    src = os.path.basename(p)
    try: env = UnityPy.load(p)
    except Exception: continue
    envs[src] = env
    for o in env.objects:
        if o.type.name not in WANT: continue
        try:
            d = o.read(check_read=(o.type.name != "MonoBehaviour"))
            index[(src, o.path_id)] = getattr(d, "m_Name", "") or ""
        except Exception:
            index[(src, o.path_id)] = ""
print(f"  {len(index)} objetos indexados", flush=True)

# ---------------- passo 2: decodificar ----------------
os.makedirs(OUT, exist_ok=True)
stats, problems, results = collections.Counter(), [], {}

for src, env in envs.items():
    for o in env.objects:
        if o.type.name != "MonoBehaviour": continue
        try:
            d = o.read(check_read=False)
            if (d.m_Script.read().m_ClassName if d.m_Script else "") != TARGET: continue
        except Exception:
            continue

        exts = [os.path.basename(e.path) for e in o.assets_file.externals]
        def resolve(ptr, _src=src, _exts=exts):
            fid, pid = ptr
            if pid == 0: return None
            f = _src if fid == 0 else (_exts[fid-1] if 0 < fid <= len(_exts) else None)
            nm = index.get((f, pid))
            return nm if nm else {"pathID": pid, "fileID": fid, "unresolved": True}

        raw, rids = o.get_raw_data(), []
        r = Reader(raw)
        try:
            r.pptr(); r.prim("u8"); r.align(); r.pptr()   # m_GameObject, m_Enabled, m_Script
            name = r.string()
            # An object whose payload ends right after m_Name has no serialized fields at all;
            # there are no bytes to interpret, so record it as empty rather than forcing a layout.
            if r.p == len(raw):
                obj = {}
            else:
                obj = {f["name"]: read_node(r, f["node"], resolve, rids) for f in layout["fields"]}
            refs = {}
            if rids or r.p < len(raw):
                _, refs = read_registry(r, resolve, rids)
            obj = splice(obj, refs)
        except Exception as e:
            stats["falha"] += 1; problems.append((src, str(o.path_id), repr(e)[:150])); continue

        left = len(raw) - r.p
        if left != 0:
            stats["bytes sobrando"] += 1
            problems.append((src, name, f"{left} de {len(raw)} bytes nao consumidos")); continue

        stats["ok"] += 1
        results[name] = obj
        json.dump(obj, open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)

json.dump(results, open(os.path.join(OUT, "_all_monster_entries.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)
print("\n=== RESULTADO ===")
for k, v in stats.most_common(): print(f"  {k}: {v}")
for p in problems[:12]: print("  !", " | ".join(p))
