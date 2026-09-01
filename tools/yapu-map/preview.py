"""Renderiza o JSON do mapa num PNG unico. E o teste de fumaca do conversor:
se a orientacao do recorte, a origem ou a ordem das camadas estiverem erradas,
da pra ver na hora."""
import os, sys, json, argparse
from PIL import Image

def render(map_json, tiles_dir, out_png, ts=32, scale=1):
    m = json.load(open(map_json, encoding="utf-8"))
    xs, ys = [], []
    for l in m["layers"]:
        for c in l["cells"]: xs.append(c["x"]); ys.append(c["y"])
    if not xs: print("mapa vazio"); return
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = (x1 - x0 + 1) * ts, (y1 - y0 + 1) * ts
    canvas = Image.new("RGBA", (W, H), (30, 30, 40, 255))
    cache = {}
    for l in m["layers"]:
        for c in l["cells"]:
            img = cache.get(c["png"])
            if img is None:
                p = os.path.join(tiles_dir, c["png"])
                if not os.path.exists(p): continue
                img = Image.open(p).convert("RGBA"); cache[c["png"]] = img
            e00, e01, e10, e11 = c.get("m", [1, 0, 0, 1])
            if e00 < 0: img2 = img.transpose(Image.FLIP_LEFT_RIGHT)
            elif e11 < 0: img2 = img.transpose(Image.FLIP_TOP_BOTTOM)
            else: img2 = img
            # o sprite e ancorado pelo pivot no centro da celula, nao pelo canto
            pvx, pvy = (c.get("pv") or [0.5, 0.5])
            w, h = img2.size
            px = int(round((c["x"] - x0) * ts + ts / 2 - pvx * w))
            py = int(round((y1 - c["y"]) * ts + ts / 2 - (1 - pvy) * h))
            canvas.alpha_composite(img2, (px, py))
    if scale != 1: canvas = canvas.resize((W * scale, H * scale), Image.NEAREST)
    canvas.convert("RGB").save(out_png)
    print(f"{out_png}  {canvas.width}x{canvas.height}  ({x0}..{x1}, {y0}..{y1})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("map_json"); ap.add_argument("out_png")
    ap.add_argument("--tiles", default="tools/yapu-map/out/tiles")
    ap.add_argument("--scale", type=int, default=1)
    a = ap.parse_args()
    render(a.map_json, a.tiles, a.out_png, scale=a.scale)
