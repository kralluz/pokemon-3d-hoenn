"""Gera viewer_models.json ligando malha -> material -> textura pelos PPtr reais.

Nada de casar por nome: le cada bundle com UnityPy e segue
    Renderer.m_Mesh      -> Mesh
    Renderer.m_Materials -> Material._MainTex -> Texture2D
reproduzindo a mesma numeracao de arquivo que export.py/export_rest.py usaram
(duplicatas de nome viram `nome~2`), para casar path_id com o arquivo em disco.
"""
import glob, json, os, re, struct, sys
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.62f2"

BUNDLES = r"apk/_extracted/out/bundles/model/sprite"
A       = r"apk/_extracted/out/assets"
DEST    = sys.argv[1] if len(sys.argv) > 1 else r"apk/_extracted/out/viewer_models.json"

def safe(s):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in str(s))[:120] or "unnamed"

def uniq(name, seen):
    """Mesma regra do exportador: 1a ocorrencia `x`, depois `x~2`, `x~3`..."""
    seen[name] = seen.get(name, 0) + 1
    return name if seen[name] == 1 else f"{name}~{seen[name]}"

# --- indice global de texturas por nome, para PPtr que apontam para outro bundle
GLOBAL_TEX = {}
for p in glob.glob(os.path.join(A, "Texture2D", "**", "*.png"), recursive=True):
    GLOBAL_TEX.setdefault(os.path.basename(p)[:-4].lower(), p.replace("\\", "/"))

# --- dados de especie
ls = open(os.path.join(A, "TextAsset/config/pet/Pet.txt"), encoding="utf-8").read().split("\n")
h = ls[1].split("\t")
iR, iN, iP, iNm = (h.index(c) for c in ("ResourceName", "OriginName", "PokeID", "Name"))
info = {}
for l in ls[2:]:
    c = l.split("\t")
    if len(c) > iR and c[iR]:
        info.setdefault(c[iR].lower(), (c[iP], c[iN], c[iNm]))

out, n_ext, n_scaled, n_miss = {}, 0, 0, 0
files = sorted(glob.glob(os.path.join(BUNDLES, "*.ab")))
for bi, bundle in enumerate(files, 1):
    key = os.path.basename(bundle)[:-3]
    try:
        env = UnityPy.load(bundle)
    except Exception:
        continue
    objs = list(env.objects)
    byid = {o.path_id: o for o in objs}

    # reproduz os nomes de arquivo gravados pelo exportador
    tex_file, mesh_file = {}, {}
    seen_t, seen_m = {}, {}
    for o in objs:
        if o.type.name == "Texture2D":
            d = o.read()
            img = getattr(d, "image", None)
            if img is None or img.width == 0 or img.height == 0:
                continue
            tex_file[o.path_id] = uniq(safe(d.m_Name), seen_t) + ".png"
        elif o.type.name == "Mesh":
            d = o.read()
            if isinstance(d.export(), str):
                mesh_file[o.path_id] = uniq(safe(d.m_Name), seen_m) + ".obj"

    def resolve(matid):
        """material -> (textura, repeat, offset, tint)"""
        mo = byid.get(matid)
        if mo is None:
            return None, [1, 1], [0, 0], "ffffff"
        mt = mo.read_typetree()
        te = mt["m_SavedProperties"]["m_TexEnvs"]
        te = te.items() if isinstance(te, dict) else te
        main = next((v for k, v in te if k == "_MainTex"), None)
        nm = mt.get("m_Name", "").lower()
        texrel, rep, off = None, [1, 1], [0, 0]
        if main:
            tid = main["m_Texture"]["m_PathID"]
            if tid in tex_file:
                texrel = f"assets/Texture2D/model/sprite/{key}/{tex_file[tid]}"
            sx, sy = main["m_Scale"]["x"], main["m_Scale"]["y"]
            rep = [sx or 1, sy or 1]
            off = [main["m_Offset"]["x"], main["m_Offset"]["y"]]
        if texrel is None:      # PPtr externo ou material sem _MainTex: acha pelo nome
            g = GLOBAL_TEX.get(nm) or GLOBAL_TEX.get(nm + ".tga")
            if g:
                texrel = os.path.relpath(g, "apk/_extracted/out").replace("\\", "/")
        # tint do material: as chamas, por exemplo, sao texturas cinza + _Color
        cols = mt["m_SavedProperties"]["m_Colors"]
        cols = dict(cols) if isinstance(cols, dict) else dict(cols)
        c = cols.get("_Color") or {"r": 1, "g": 1, "b": 1}
        color = "%02x%02x%02x" % tuple(
            max(0, min(255, round((c.get(ch, 1) ** (1 / 2.2)) * 255))) for ch in "rgb")
        return texrel, rep, off, color

    # o bundle traz o set normal e o shiny; a variante base e a que nao ganhou
    # sufixo `~n` no export, entao para cada malha preferimos essa
    cand = {}
    for o in objs:
        if o.type.name not in ("SkinnedMeshRenderer", "MeshRenderer"):
            continue
        t = o.read_typetree()
        mid = (t.get("m_Mesh") or {}).get("m_PathID")
        mats = t.get("m_Materials") or []
        if mid not in mesh_file or not mats:
            continue
        r = resolve(mats[0].get("m_PathID"))
        prev = cand.get(mid)
        if prev is None or ("~" in (prev[0] or "~") and "~" not in (r[0] or "~")):
            cand[mid] = r

    parts = []
    for mid, (texrel, rep, off, color) in cand.items():
        if texrel is None:
            n_miss += 1
        elif "/model/sprite/" + key + "/" not in texrel:
            n_ext += 1
        if color != "ffffff":
            n_scaled += 1
        parts.append({"obj": f"assets/Mesh/model/sprite/{key}/{mesh_file[mid]}",
                      "tex": texrel, "rep": rep, "off": off, "col": color})

    if not parts:
        continue
    pid, orig, cn = info.get(key, ("", "", ""))
    ntex = len(tex_file)
    out[key] = {"id": pid, "en": orig or key, "cn": cn, "parts": parts, "ntex": ntex}
    if bi % 150 == 0:
        print(f"  {bi}/{len(files)}", flush=True)

json.dump(out, open(DEST, "w", encoding="utf-8"), ensure_ascii=False)
tot = sum(len(v["parts"]) for v in out.values())
print(f"{len(out)} modelos | {tot} malhas | {tot-n_miss} com textura "
      f"({n_ext} resolvidas em outro bundle) | {n_scaled} com tint _Color nao-branco")
