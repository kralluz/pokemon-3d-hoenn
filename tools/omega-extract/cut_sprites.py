"""Recorta os icones 2D dos pokemons dos atlas de UI do APK.

Os atlas nao usam Sprite do Unity: sao UIAtlas do NGUI, um MonoBehaviour com a
lista mSprites (nome, x, y, width, height). Os nomes batem com OriginName do
Pet.txt, o que permite ligar cada icone a sua especie depois.
"""
import json
import os
import re
import sys

import UnityPy

BUNDLES = "apk/_extracted/out/bundles/dependent/ui/atlas"
ATLAS = ["petatlas", "pet2atlas", "pet3atlas"]
SAIDA = "apk/_extracted/out/sprites"


def limpo(nome):
    return re.sub(r"[^A-Za-z0-9_-]", "_", nome).strip("_") or "sem_nome"


def main():
    os.makedirs(SAIDA, exist_ok=True)
    indice, total, colisoes = {}, 0, 0

    for nome in ATLAS:
        caminho = f"{BUNDLES}/{nome}.ab"
        if not os.path.exists(caminho):
            print(f"  {nome}: bundle nao encontrado", file=sys.stderr)
            continue

        env = UnityPy.load(caminho)
        tex = next((o.read() for o in env.objects if o.type.name == "Texture2D"), None)
        mb = next((o for o in env.objects if o.type.name == "MonoBehaviour"), None)
        if tex is None or mb is None:
            print(f"  {nome}: sem textura ou sem UIAtlas", file=sys.stderr)
            continue

        atlas = tex.image
        dados = mb.read_typetree()
        entradas = dados.get("mSprites", [])
        print(f"{nome}: atlas {atlas.width}x{atlas.height}, {len(entradas)} icones")

        for e in entradas:
            x, y = int(e["x"]), int(e["y"])
            w, h = int(e["width"]), int(e["height"])
            if w <= 0 or h <= 0:
                continue

            # NGUI conta y a partir do topo, igual ao Pillow, e o UnityPy ja
            # entrega a textura desvirada — recortar direto e o certo. Virar
            # antes (o que parece natural vindo da Unity) devolve o pedaco errado.
            corte = atlas.crop((x, y, x + w, y + h))

            base = limpo(e["name"])
            arq = f"{SAIDA}/{base}.png"
            if base in indice:
                colisoes += 1
                arq = f"{SAIDA}/{base}__{nome}.png"
            corte.save(arq)
            indice.setdefault(base, os.path.basename(arq))
            total += 1

    with open(f"{SAIDA}/index.json", "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=1, sort_keys=True)

    print(f"\n{total} icones recortados em {SAIDA} ({colisoes} nomes repetidos)")
    print(f"indice: {SAIDA}/index.json")


if __name__ == "__main__":
    main()
