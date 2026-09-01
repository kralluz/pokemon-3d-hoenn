"""Empacota o JSON da cena no formato que o importador da Unity consome.

Compacto de proposito: JsonUtility nao le lista de dicionarios aninhados de
forma pratica, mas le int[]/string[] direto. Entao cada camada vira arrays
paralelos (xs, ys, indice do sprite, flip) em vez de 8 mil objetos.
"""
import os, sys, json, shutil, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import walkability as W


def emit(map_json, tiles_src, unity_root, subdir="YAPU/StartingVillage"):
    m = json.load(open(map_json, encoding="utf-8"))
    scene = m["scene"]

    # a chave e (png, pivot): o mesmo recorte pode ser ancorado em pontos
    # diferentes, e ha pivots fora de 0..1 (decoracao que invade a celula vizinha)
    pngs, pivots, index = [], [], {}
    layers = []
    for l in m["layers"]:
        if not l["cells"]: continue
        xs, ys, ti, fl = [], [], [], []
        for c in l["cells"]:
            pv = c.get("pv") or [0.5, 0.5]
            key = (c["png"], pv[0], pv[1])
            p = c["png"]
            if key not in index:
                index[key] = len(pngs); pngs.append(p); pivots.append(pv)
            xs.append(c["x"]); ys.append(c["y"]); ti.append(index[key])
            e00, e01, e10, e11 = c.get("m", [1, 0, 0, 1])
            fl.append((1 if e00 < 0 else 0) | (2 if e11 < 0 else 0))
        layers.append(dict(name=l["name"], order=l["order"], xs=xs, ys=ys, tile=ti, flip=fl))

    grid = W.build(m)
    wx, wy, wt = [], [], []
    for (x, y), t in sorted(grid.items()):
        wx.append(x); wy.append(y); wt.append(t)

    art = os.path.join(unity_root, "Assets", "Art", subdir, "Tiles")
    os.makedirs(art, exist_ok=True)
    for p in set(pngs):
        dst = os.path.join(art, p)
        if not os.path.exists(dst): shutil.copyfile(os.path.join(tiles_src, p), dst)

    out = dict(scene=scene, tiles=pngs,
               pivotX=[p[0] for p in pivots], pivotY=[p[1] for p in pivots],
               layers=layers,
               walkX=wx, walkY=wy, walkType=wt,
               tilesFolder=f"Assets/Art/{subdir}/Tiles")
    data_dir = os.path.join(unity_root, "Assets", "MapData")
    os.makedirs(data_dir, exist_ok=True)
    dst = os.path.join(data_dir, f"{scene}.json")
    json.dump(out, open(dst, "w", encoding="utf-8"))
    print(f"{scene}: {len(layers)} camadas, {sum(len(l['xs']) for l in layers)} celulas, "
          f"{len(pngs)} tiles ({len(set(pngs))} PNGs), {len(wx)} celulas de colisao")
    print(f"  -> {dst}")
    print(f"  -> {art} ({len(pngs)} PNGs)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json")
    ap.add_argument("--tiles", default="tools/yapu-map/out/tiles")
    ap.add_argument("--unity", default="unity/Unity")
    ap.add_argument("--subdir", default="YAPU/StartingVillage")
    a = ap.parse_args()
    emit(a.map_json, a.tiles, a.unity, a.subdir)
