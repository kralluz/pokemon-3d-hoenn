"""Converte uma cena ripada do YAPU num mapa reutilizavel: JSON de camadas +
PNGs de tile recortados. O trabalho pesado ja esta feito pelo Unity: cada
celula do Tilemap guarda o sprite JA RESOLVIDO pela rule tile
(m_TileSpriteIndex), entao nao e preciso reimplementar as regras de vizinhanca.
"""
import os, sys, json, hashlib, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unityyaml
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RIPPED = "YAPU_Demo/Ripped/ExportedProject/Assets"
GUIDS = json.load(open(os.path.join(HERE, "guid_index.json"), encoding="utf-8"))

CID_GAMEOBJECT, CID_TRANSFORM = 1, 4
CID_TILEMAP, CID_TILEMAP_RENDERER, CID_GRID = 1839735485, 483693784, 156049354

_sprite_cache, _tex_cache, _tile_png_cache, _rule_name_cache = {}, {}, {}, {}


def rule_tile_name(guid):
    """m_Name real da tile (nao o nome do arquivo, que o AssetRipper desambigua)."""
    if guid in _rule_name_cache: return _rule_name_cache[guid]
    p, name = GUIDS.get(guid), None
    if p and os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("  m_Name:"):
                        name = line.split(":", 1)[1].strip(); break
        except OSError: pass
        if not name: name = os.path.basename(p).replace(".asset", "")
    _rule_name_cache[guid] = name
    return name


def tiledata_types():
    """nome da tile -> TileType (0..9), do TileData global que so o decoder leu."""
    p = "YAPU_Demo/extracted/MonoBehaviour_decoded/TileData/TileData.json"
    d = json.load(open(p, encoding="utf-8"))
    return {e["Key"]: e["Value"] for e in d["Types"]["SerializedList"] if e.get("Key")}


def sprite_info(guid):
    """guid do Sprite -> nome, textura e retangulo dentro do atlas."""
    if guid in _sprite_cache: return _sprite_cache[guid]
    path = GUIDS.get(guid)
    info = None
    if path and os.path.exists(path):
        for cid, fid, tname, body in unityyaml.load_documents(path):
            if tname != "Sprite": continue
            rect = body["m_Rect"]
            info = dict(name=body.get("m_Name"),
                        rect=(int(rect["x"]), int(rect["y"]), int(rect["width"]), int(rect["height"])),
                        ppu=body.get("m_PixelsToUnits") or 32,
                        pivot=body.get("m_Pivot"),
                        tex=(body.get("m_RD") or {}).get("texture", {}).get("guid"))
            break
    _sprite_cache[guid] = info
    return info


def texture(guid):
    if guid in _tex_cache: return _tex_cache[guid]
    p = GUIDS.get(guid)
    img = None
    if p and os.path.exists(p):
        try: img = Image.open(p).convert("RGBA")
        except Exception: img = None
    _tex_cache[guid] = img
    return img


def tile_png(sguid, outdir):
    """Recorta o sprite do atlas e devolve o nome do PNG (deduplicado por hash).
    O retangulo do Unity conta a partir de baixo; o PNG conta de cima."""
    if sguid in _tile_png_cache: return _tile_png_cache[sguid]
    info = sprite_info(sguid)
    res = None
    if info:
        tex = texture(info["tex"])
        if tex:
            x, y, w, h = info["rect"]
            box = (x, tex.height - (y + h), x + w, tex.height - y)
            crop = tex.crop(box)
            digest = hashlib.sha1(crop.tobytes() + f"{w}x{h}".encode()).hexdigest()[:16]
            name = f"{digest}.png"
            dst = os.path.join(outdir, name)
            if not os.path.exists(dst):
                os.makedirs(outdir, exist_ok=True)
                crop.save(dst)
            res = dict(png=name, w=w, h=h, ppu=info["ppu"], pivot=info["pivot"], src=info["name"])
    _tile_png_cache[sguid] = res
    return res


def convert(scene_path, out_json, tiles_dir):
    docs = unityyaml.load_documents(scene_path)
    by_fid = {fid: (cid, tname, body) for cid, fid, tname, body in docs}
    types = tiledata_types()

    def go_name(fid):
        e = by_fid.get(fid)
        return (e[2].get("m_Name") if e else None) or f"fid{fid}"

    # TilemapRenderer -> ordem de desenho, indexado pelo GameObject
    order = {}
    for cid, fid, tname, body in docs:
        if cid == CID_TILEMAP_RENDERER:
            order[body["m_GameObject"]["fileID"]] = body.get("m_SortingOrder", 0)

    cell = {"x": 1, "y": 1}
    for cid, fid, tname, body in docs:
        if cid == CID_GRID: cell = body.get("m_CellSize", cell)

    layers, unknown = [], set()
    for cid, fid, tname, body in docs:
        if cid != CID_TILEMAP: continue
        goid = body["m_GameObject"]["fileID"]
        sprites = body.get("m_TileSpriteArray") or []
        assets = body.get("m_TileAssetArray") or []
        mats = body.get("m_TileMatrixArray") or []

        # nome da RuleTile de cada indice, para consultar a walkability.
        # Tem que ser o m_Name de dentro do asset: quando dois assets colidem de
        # nome o AssetRipper renomeia o ARQUIVO (Grass -> Grass_1), e ai a busca
        # no TileData falha justamente nos tiles mais comuns.
        asset_names = [rule_tile_name((a.get("m_Data") or {}).get("guid")) for a in assets]

        sprite_refs = []
        for s in sprites:
            g = (s.get("m_Data") or {}).get("guid")
            sprite_refs.append(tile_png(g, tiles_dir) if g else None)

        cells = []
        for t in body.get("m_Tiles") or []:
            pos, v = t["first"], t["second"]
            si, ai = v.get("m_TileSpriteIndex", -1), v.get("m_TileIndex", -1)
            ref = sprite_refs[si] if 0 <= si < len(sprite_refs) else None
            if ref is None: continue
            aname = asset_names[ai] if 0 <= ai < len(asset_names) else None
            if aname is not None and aname not in types: unknown.add(aname)
            mi = v.get("m_TileMatrixIndex", 0)
            m = (mats[mi].get("m_Data") if 0 <= mi < len(mats) else None) or {}
            pv = ref.get("pivot") or {"x": 0.5, "y": 0.5}
            cells.append(dict(x=int(pos["x"]), y=int(pos["y"]), png=ref["png"],
                              pv=[round(pv.get("x", .5), 4), round(pv.get("y", .5), 4)],
                              wh=[ref["w"], ref["h"]],
                              tile=aname, type=types.get(aname, 0),
                              m=[m.get("e00", 1), m.get("e01", 0), m.get("e10", 0), m.get("e11", 1)]))

        layers.append(dict(name=go_name(goid), order=order.get(goid, 0),
                           origin=body.get("m_Origin"), size=body.get("m_Size"),
                           anchor=body.get("m_TileAnchor"), cells=cells))

    layers.sort(key=lambda l: l["order"])
    out = dict(scene=os.path.basename(scene_path).replace(".unity", ""),
               cellSize=cell, layers=layers)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    json.dump(out, open(out_json, "w", encoding="utf-8"))
    total = sum(len(l["cells"]) for l in layers)
    print(f"{out['scene']}: {len(layers)} camadas, {total} celulas, "
          f"{len(_tile_png_cache)} sprites unicos")
    if unknown: print(f"  tiles sem TileType: {len(unknown)} (ex: {sorted(unknown)[:5]})")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", default="tools/yapu-map/out")
    a = ap.parse_args()
    name = os.path.basename(a.scene).replace(".unity", "")
    convert(a.scene, os.path.join(a.out, f"{name}.json"), os.path.join(a.out, "tiles"))
