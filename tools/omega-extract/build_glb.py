"""Exporta cada modelo como .glb com esqueleto (skin), materiais e texturas.

Substitui o caminho .obj, que perdia o rig: as submalhas de um SkinnedMeshRenderer
vivem em espaco de bind e so ficam no lugar quando as matrizes de osso sao aplicadas.
Por isso Archen, AshGreninja e afins apareciam espalhados.

Unity e canhoto (X dir, Y cima, Z frente); glTF e destro. Convertemos negando Z:
    posicao/normal (x, y, -z)
    quaternion     (x, y, z, w) -> (-x, -y, z, w)
    matriz         M' = S M S, com S = diag(1, 1, -1, 1)
    triangulos     ordem invertida (o determinante fica negativo)
"""
import glob, math, os, sys, time, zlib
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb import GLB, FLOAT, UINT, USHORT
import animclip

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.62f2"

ROOT    = r"apk/_extracted/out/bundles"          # raiz dos .ab
A       = r"apk/_extracted/out/assets"
SUB     = "model/sprite"                          # subpasta alvo (argv[1])
OUT     = r"apk/_extracted/out/glb"

GLOBAL_TEX = {}
for p in glob.glob(os.path.join(A, "Texture2D", "**", "*.png"), recursive=True):
    GLOBAL_TEX.setdefault(os.path.basename(p)[:-4].lower(), p)

def safe(s):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in str(s))[:120] or "unnamed"

def uniq(name, seen):
    seen[name] = seen.get(name, 0) + 1
    return name if seen[name] == 1 else f"{name}~{seen[name]}"

def fix_weights(w):
    """Alguns canais guardam so 3 influencias e a 4a e implicita (1 - soma);
    nesses casos o decode traz lixo no 4o componente (pesos tipo -25).
    Outros trazem menos de 4 componentes; o accessor VEC4 exige exatamente 4."""
    a = [max(0.0, min(1.0, float(x))) for x in list(w)[:3]]
    a += [0.0] * (3 - len(a))
    a.append(max(0.0, 1.0 - sum(a)))
    s = sum(a)
    return tuple(x / s for x in a) if s > 1e-6 else (1.0, 0.0, 0.0, 0.0)


def fix_joints(bi, nmax):
    a = [max(0, min(int(x), nmax)) for x in list(bi)[:4]]
    return tuple(a + [0] * (4 - len(a)))


def okey(o):
    """Chave unica de objeto: path_id sozinho colide entre arquivos do bundle."""
    return (getattr(getattr(o, "assets_file", None), "name", ""), o.path_id)


def conv_mat(e):
    """Matrix4x4f do Unity -> matriz glTF (column-major), negando Z."""
    m = [[e[f"e{r}{c}"] for c in range(4)] for r in range(4)]
    for r in range(4):
        for c in range(4):
            if (r == 2) != (c == 2):
                m[r][c] = -m[r][c]
    return [m[r][c] for c in range(4) for r in range(4)]



def pick_skeleton(objs, tt, tf_ids, node_of):
    """Escolhe UM esqueleto por modelo.

    Cada malha aparece duas vezes: presa ao esqueleto principal e a um duplicado
    `<Nome>Flash`. Misturar os dois deixa pecas soltas no lugar errado e fora do
    alcance das animacoes. Escolhemos a raiz que os proprios clips endereçam
    (as bindings usam CRC32 do caminho relativo ao root do Animator).

    Devolve (hash -> no glTF, conjunto de transforms daquele esqueleto).
    """
    go2tf = {tt[p]["m_GameObject"]["m_PathID"]: p for p in tf_ids if p in tt}
    father = {p: tt[p]["m_Father"]["m_PathID"] for p in tf_ids if p in tt}
    def nm(p):
        return (tt.get(tt[p]["m_GameObject"]["m_PathID"]) or {}).get("m_Name", "?")

    cands = set()
    for o in objs:
        if o.type.name in ("Animator", "Animation"):
            r = go2tf.get((tt.get(o.path_id) or {}).get("m_GameObject", {}).get("m_PathID"))
            if r is not None:
                cands.add(r)
    if not cands:                       # sem Animator: usa as raizes da arvore
        cands = {p for p in tf_ids if father.get(p) not in father}

    wanted = set()
    for o in objs:
        if o.type.name == "AnimationClip":
            for b in ((o.read_typetree().get("m_ClipBindingConstant") or {})
                      .get("genericBindings") or []):
                wanted.add(b["path"])

    best = None
    for r in cands:
        hm, sub = {}, set()
        for p in tf_ids:
            parts, cur = [], p
            while cur in father and cur != r:
                parts.append(nm(cur)); cur = father[cur]
            if cur != r:
                continue
            sub.add(p)
            hm.setdefault(zlib.crc32("/".join(reversed(parts)).encode()) & 0xFFFFFFFF,
                          node_of[p])
        # criterio: cobrir as bindings dos clips; sem clips, evitar o set "Flash"
        score = (len(wanted & set(hm)), not nm(r).lower().endswith("flash"), len(sub))
        if best is None or score > best[0]:
            best = (score, hm, sub)
    return (best[1], best[2]) if best else ({}, set())


def add_animations(g, objs, hm):
    """Alem de exportar os clips, assa a pose do 1o quadro do idle como pose de
    repouso dos nos. O prefab guardado no bundle nao esta numa pose util (no jogo
    o Animator sempre esta tocando algo), entao parado no Unity ele sai torto."""
    seen = set()
    first_pose = {}
    for o in objs:
        if o.type.name != "AnimationClip":
            continue
        t = o.read_typetree()
        name = t.get("m_Name", "clip")
        if name in seen:
            continue
        try:
            tracks = animclip.decode(t)
        except Exception:
            continue
        samplers, channels = [], []
        for (h, attr), keys in tracks.items():
            node = hm.get(h)
            if node is None or attr not in (1, 2, 3) or len(keys) < 2:
                continue
            times = [float(k[0]) for k in keys]
            if attr == 1:
                vals = [(v[0], v[1], -v[2]) for _, v in keys]; path, at = "translation", "VEC3"
            elif attr == 3:
                vals = [(v[0], v[1], v[2]) for _, v in keys]; path, at = "scale", "VEC3"
            else:
                vals, prev = [], None
                for _, v in keys:
                    q = (-v[0], -v[1], v[2], v[3])
                    n = math.sqrt(sum(x * x for x in q)) or 1.0
                    q = tuple(x / n for x in q)
                    if prev and sum(a * b for a, b in zip(q, prev)) < 0:
                        q = tuple(-x for x in q)          # evita o caminho longo no slerp
                    prev = q
                    vals.append(q)
                path, at = "rotation", "VEC4"
            first_pose.setdefault(name, {})[(node, path)] = vals[0]
            samplers.append({"input": g.accessor(times, FLOAT, "SCALAR", minmax=True),
                             "output": g.accessor(vals, FLOAT, at),
                             "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": node, "path": path}})
        if channels:
            seen.add(name)
            # OMEGA_NOANIM: as pecas do avatar compartilham os mesmos 20 clips;
            # duplicar em cada uma inchava o projeto. A pose de repouso continua
            # sendo assada abaixo, que e o que importa para a peca parada.
            if not os.environ.get("OMEGA_NOANIM"):
                g.json["animations"].append({"name": name, "samplers": samplers,
                                             "channels": channels})
    # pose padrao: preferimos um idle
    if first_pose:
        order = ["SceneIdle", "Idle1", "Idle"]
        pick = next((n for n in order if n in first_pose), next(iter(first_pose)))
        for (node, path), val in first_pose[pick].items():
            g.json["nodes"][node][path] = list(val)
    return len(g.json["animations"])


def export(bundle, out_path, deps=()):
    """deps: bundles extras carregados so para resolver PPtr entre arquivos
    (cenas referenciam malhas/materiais que moram em `dependent/`)."""
    env = UnityPy.load(bundle)
    mine = {getattr(o.assets_file, "name", "") for o in env.objects}
    if deps:
        env = UnityPy.load(bundle, *deps)
        objs = [o for o in env.objects
                if getattr(o.assets_file, "name", "") in mine]
        # o player guarda os clips num bundle separado (roleanimation.ab):
        # trazemos os AnimationClip das dependencias tambem
        objs += [o for o in env.objects
                 if o.type.name == "AnimationClip"
                 and getattr(o.assets_file, "name", "") not in mine]
    else:
        objs = list(env.objects)
    byid = {o.path_id: o for o in objs}
    tt = {}                                    # path_id -> typetree (componentes)
    for o in objs:
        if o.type.name in ("Transform", "RectTransform", "GameObject",
                           "SkinnedMeshRenderer", "MeshRenderer", "MeshFilter",
                           "Material", "Animator", "Animation"):
            tt[o.path_id] = o.read_typetree()

    # --- nomes de arquivo de textura, iguais aos do exportador de assets
    tex_file, seen_t = {}, {}
    for o in objs:
        if o.type.name == "Texture2D":
            d = o.read()
            img = getattr(d, "image", None)
            if img is None or img.width == 0 or img.height == 0:
                continue
            tex_file[okey(o)] = uniq(safe(d.m_Name), seen_t) + ".png"

    key = os.path.basename(bundle)[:-3]
    rel = os.path.relpath(os.path.dirname(bundle), ROOT).replace("\\", "/")
    texdir = os.path.join(A, "Texture2D", *rel.split("/"), key)

    # --- arvore de Transform -> nos glTF
    tf_ids = [o.path_id for o in objs if o.type.name in ("Transform", "RectTransform")]
    node_of = {pid: i for i, pid in enumerate(tf_ids)}
    g = GLB()
    for pid in tf_ids:
        t = tt.get(pid) or byid[pid].read_typetree()
        go = tt.get((t.get("m_GameObject") or {}).get("m_PathID"))
        p, q, s = t["m_LocalPosition"], t["m_LocalRotation"], t["m_LocalScale"]
        node = {
            "name": (go or {}).get("m_Name", "node"),
            "translation": [p["x"], p["y"], -p["z"]],
            "rotation": [-q["x"], -q["y"], q["z"], q["w"]],
            "scale": [s["x"], s["y"], s["z"]],
        }
        kids = [node_of[c["m_PathID"]] for c in (t.get("m_Children") or [])
                if c["m_PathID"] in node_of]
        if kids:
            node["children"] = kids
        g.json["nodes"].append(node)
    roots = [node_of[pid] for pid in tf_ids
             if (tt.get(pid) or byid[pid].read_typetree()).get("m_Father", {}).get("m_PathID") not in node_of]
    g.json["scenes"][0]["nodes"] = roots

    # --- materiais
    mat_cache, tex_cache = {}, {}
    padrao = {}

    def material_padrao(gg):
        """Material que nao resolveu: cinza neutro em vez de nulo (magenta)."""
        if "i" not in padrao:
            gg.json["materials"].append({
                "name": "NaoResolvido",
                "pbrMetallicRoughness": {"baseColorFactor": [0.72, 0.72, 0.70, 1],
                                         "metallicFactor": 0.0, "roughnessFactor": 1.0},
                "doubleSided": True})
            padrao["i"] = len(gg.json["materials"]) - 1
        return padrao["i"]
    def material(mobj):
        k = okey(mobj)
        if k in mat_cache:
            return mat_cache[k]
        mt = mobj.read_typetree()
        sp = mt.get("m_SavedProperties") or {}
        te = sp.get("m_TexEnvs") or []
        te = te.items() if isinstance(te, dict) else te
        main = next((kk_v[1] for kk_v in te if kk_v[0] == "_MainTex"), None)
        sc = main["m_Scale"] if main else None
        of = main["m_Offset"] if main else None
        cols = dict(sp.get("m_Colors") or {})
        c = cols.get("_Color") or {}
        tint = [c.get("r", 1), c.get("g", 1), c.get("b", 1), 1]

        # o PPtr da textura pode apontar para outro arquivo do bundle: deref tipado
        path = None
        try:
            md = mobj.read()
            items = md.m_SavedProperties.m_TexEnvs
            items = items if isinstance(items, list) else list(items.items())
            mn = next((v for kk, v in items if kk == "_MainTex"), None)
            tp = mn.m_Texture.deref() if mn is not None else None
            if tp is not None:
                if okey(tp) in tex_file:
                    path = os.path.join(texdir, tex_file[okey(tp)])
                else:
                    # textura em bundle de dependencia: acha pelo nome dela no
                    # indice global (procurar pelo nome do MATERIAL falhava)
                    tn = tp.read().m_Name.lower()
                    path = GLOBAL_TEX.get(tn) or GLOBAL_TEX.get(tn + ".tga")
        except Exception:
            pass
        if not path or not os.path.exists(path):
            nm = mt.get("m_Name", "").lower()
            path = GLOBAL_TEX.get(nm) or GLOBAL_TEX.get(nm + ".tga")

        base = None
        if path and os.path.exists(path):
            if path not in tex_cache:
                tex_cache[path] = g.texture(g.image_png(open(path, "rb").read()))
            base = tex_cache[path]

        pbr = {"baseColorFactor": tint, "metallicFactor": 0.0, "roughnessFactor": 1.0}
        if base is not None:
            t = {"index": base}
            if sc and of and (sc["x"] != 1 or sc["y"] != 1 or of["x"] or of["y"]):
                t["extensions"] = {"KHR_texture_transform": {
                    "scale": [sc["x"], sc["y"]], "offset": [of["x"], of["y"]]}}
                g.json.setdefault("extensionsUsed", [])
                if "KHR_texture_transform" not in g.json["extensionsUsed"]:
                    g.json["extensionsUsed"].append("KHR_texture_transform")
            pbr["baseColorTexture"] = t
        g.json["materials"].append({
            "name": mt.get("m_Name", "mat"), "pbrMetallicRoughness": pbr,
            "alphaMode": "MASK", "alphaCutoff": 0.35, "doubleSided": True})
        mat_cache[k] = len(g.json["materials"]) - 1
        return mat_cache[k]

    # --- malhas: um renderer por Mesh (o bundle traz o set normal e o shiny)
    mesh_filters = {}
    for o in objs:
        if o.type.name == "MeshFilter":
            try:
                d = o.read()
                mo = d.m_Mesh.deref() if d.m_Mesh else None
                if mo is not None:
                    mesh_filters[d.m_GameObject.path_id] = mo
            except Exception:
                pass

    hm, skel = pick_skeleton(objs, tt, tf_ids, node_of)

    chosen = {}
    for o in objs:
        if o.type.name not in ("SkinnedMeshRenderer", "MeshRenderer"):
            continue
        try:
            d = o.read()
            if o.type.name == "SkinnedMeshRenderer":
                mobj = d.m_Mesh.deref() if d.m_Mesh else None
                bones = [b.path_id for b in (d.m_Bones or [])]
                # so aceita o renderer preso ao esqueleto escolhido
                if skel and bones and bones[0] not in skel:
                    continue
            else:
                mobj = mesh_filters.get(d.m_GameObject.path_id)
        except Exception:
            continue
        if mobj is None or mobj.type.name != "Mesh":
            continue
        k = okey(mobj)
        if k not in chosen:
            chosen[k] = (o, d, mobj)

    n_prim = 0
    for _, (o, d, mobj) in chosen.items():
        mesh = mobj.read()
        h = MeshHandler(mesh)
        h.process()
        if not h.m_Vertices:
            continue
        pos = [(v[0], v[1], -v[2]) for v in h.m_Vertices]
        nor = [(v[0], v[1], -v[2]) for v in (h.m_Normals or [])] or None
        uv = [(v[0], 1.0 - v[1]) for v in (h.m_UV0 or [])] or None
        idx = list(h.m_IndexBuffer)

        attrs = {"POSITION": g.accessor(pos, FLOAT, "VEC3", 34962, minmax=True)}
        if nor:
            attrs["NORMAL"] = g.accessor(nor, FLOAT, "VEC3", 34962)
        if uv:
            attrs["TEXCOORD_0"] = g.accessor(uv, FLOAT, "VEC2", 34962)

        skin_idx = None
        if o.type.name == "SkinnedMeshRenderer" and h.m_BoneIndices and mesh.m_BindPose:
            joints = [node_of[b.path_id] for b in (d.m_Bones or [])
                      if b.path_id in node_of]
            if joints and len(joints) == len(mesh.m_BindPose):
                attrs["JOINTS_0"] = g.accessor(
                    [fix_joints(bi, len(joints) - 1) for bi in h.m_BoneIndices],
                    USHORT, "VEC4", 34962)
                # malha presa rigidamente a um osso nao traz pesos: peso 1 no primeiro
                bw = h.m_BoneWeights or [(1.0, 0.0, 0.0, 0.0)] * len(pos)
                attrs["WEIGHTS_0"] = g.accessor(
                    [fix_weights(w) for w in bw], FLOAT, "VEC4", 34962)
                ibm = []
                for bp in mesh.m_BindPose:
                    e = {f"e{r}{c}": getattr(bp, f"e{r}{c}") for r in range(4) for c in range(4)}
                    ibm.append(conv_mat(e))
                g.json["skins"].append({
                    "joints": joints,
                    "inverseBindMatrices": g.accessor(ibm, FLOAT, "MAT4")})
                skin_idx = len(g.json["skins"]) - 1

        prims = []
        mats = list(d.m_Materials or [])
        for si, sub in enumerate(mesh.m_SubMeshes or []):
            step = 2 if h.m_Use16BitIndices else 4
            first = sub.firstByte // step
            sl = idx[first: first + sub.indexCount]
            sl = [sl[i + j] for i in range(0, len(sl) - 2, 3) for j in (2, 1, 0)]  # winding
            if not sl:
                continue
            ctype = UINT if max(sl) > 65535 else USHORT
            prim = {"attributes": attrs,
                    "indices": g.accessor(sl, ctype, "SCALAR", 34963),
                    "mode": 4}
            if si < len(mats):
                try:                      # PPtr nulo (m_PathID == 0) nao deref
                    mo = mats[si].deref() if mats[si].m_PathID else None
                except Exception:
                    mo = None
                if mo is not None and mo.type.name == "Material":
                    prim["material"] = material(mo)
                else:
                    prim["material"] = material_padrao(g)
            prims.append(prim)
            n_prim += 1
        if not prims:
            continue
        g.json["meshes"].append({"name": mesh.m_Name, "primitives": prims})
        mi = len(g.json["meshes"]) - 1

        if skin_idx is not None:
            # no glTF o no de uma malha com skin ignora a propria transform
            g.json["nodes"].append({"name": mesh.m_Name, "mesh": mi, "skin": skin_idx})
            g.json["scenes"][0]["nodes"].append(len(g.json["nodes"]) - 1)
        else:
            gid = d.m_GameObject.path_id
            host = next((node_of[p] for p in tf_ids
                         if (tt.get(p) or {}).get("m_GameObject", {}).get("m_PathID") == gid), None)
            if host is not None:
                g.json["nodes"][host]["mesh"] = mi
            else:
                g.json["nodes"].append({"name": mesh.m_Name, "mesh": mi})
                g.json["scenes"][0]["nodes"].append(len(g.json["nodes"]) - 1)

    n_anim = add_animations(g, objs, hm)
    if not g.json["meshes"]:
        return None
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    size = g.save(out_path)
    return len(g.json["meshes"]), n_prim, len(g.json["skins"]), n_anim, size


if __name__ == "__main__":
    args = sys.argv[1:]
    sub = SUB
    if args and "/" in args[0]:
        sub = args.pop(0)
    only = args or None
    src = os.path.join(ROOT, *sub.split("/"))
    # cenas puxam geometria de `dependent/`; carregamos junto so para resolver PPtr
    deps = []
    if sub.startswith("model/role"):
        # o player e modular: renderer/material num bundle, malha em `parts/`,
        # e as 40 animacoes compartilhadas em roleanimation.ab
        deps = sorted(glob.glob(os.path.join(src, "parts", "*.ab"))) +                [os.path.join(ROOT, "model", "role", "roleanimation.ab")]
        deps = [d for d in deps if os.path.exists(d)]
        print(f"dependencias carregadas: {len(deps)}")
    elif sub.startswith("scene/"):
        # cenas referenciam material e malha espalhados por varios bundles de
        # dependencia; carregar so `scene` e `shader` deixava 19 de 41 renderers
        # sem material — e material nulo aparece magenta no Unity
        deps = sorted(glob.glob(os.path.join(ROOT, "dependent", "**", "*.ab"),
                                recursive=True))
        print(f"dependencias carregadas: {len(deps)}")
    dst = os.path.join(OUT, *sub.split("/")) if sub != "model/sprite" else OUT
    files = sorted(glob.glob(os.path.join(src, "**", "*.ab"), recursive=True))
    if sub.startswith("model/role"):
        files = [f for f in files if os.sep + "parts" + os.sep not in f]
    if only:
        files = [f for f in files if os.path.basename(f)[:-3] in only]
    print(f"origem: {src}  ({len(files)} bundles) -> {dst}")
    t0 = time.time(); ok = 0; errs = []
    for i, f in enumerate(files, 1):
        key = os.path.basename(f)[:-3]
        try:
            r = export(f, os.path.join(dst, key + ".glb"), deps)
            if r:
                ok += 1
                if only or i % 150 == 0:
                    print(f"  {key:26s} malhas={r[0]:3d} skins={r[2]:3d} anims={r[3]:3d} "
                          f"{r[4]/1024:6.0f} KB  [{i}/{len(files)}]", flush=True)
        except Exception as e:
            errs.append((key, f"{type(e).__name__}: {e}"))
    print(f"\n{ok}/{len(files)} em {time.time()-t0:.0f}s | erros: {len(errs)}")
    for e in errs[:10]:
        print("   ", e)
