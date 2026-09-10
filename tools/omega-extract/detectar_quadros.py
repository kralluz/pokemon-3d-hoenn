"""Descobre os quadros de cada folha de sprite pelo canal alfa.

A regra ingenua (largura / altura) so vale para tira horizontal de quadros
quadrados. Na pratica as folhas vem em dois formatos:

  0007.png   1118x43   tira horizontal
  0004.png   256x256   grade 4x4

Fatiar a grade pela regra da tira devolve UM quadro com dezesseis Pokemons
dentro — foi o que apareceu na tela.

Aqui procuramos as colunas e linhas totalmente transparentes: sao os vaos entre
quadros. O que sobra entre dois vaos e um quadro, em qualquer um dos formatos.
Escreve quadros.json, que o importador da Unity le.
"""
import json
import os
import sys

from PIL import Image

PASTA = "nel-ord/Assets/Omega/Resources/Batalha"
SAIDA = "nel-ord/Assets/Omega/Editor/quadros.json"  # fora de Resources


def faixas(vazio):
    """Lista de (inicio, fim) das corridas de False em 'vazio'."""
    saida, ini = [], None
    for i, v in enumerate(vazio):
        if not v and ini is None:
            ini = i
        elif v and ini is not None:
            saida.append((ini, i))
            ini = None
    if ini is not None:
        saida.append((ini, len(vazio)))
    return saida


def quadros(caminho):
    im = Image.open(caminho).convert("RGBA")
    a = im.getchannel("A")
    L, A = im.size
    px = a.load()

    col_vazia = [all(px[x, y] == 0 for y in range(A)) for x in range(L)]
    faixas_x = faixas(col_vazia)
    if not faixas_x:
        return []

    # descarta vaos minusculos: sprite com um pixel solto viraria quadro proprio
    largura_media = sum(f - i for i, f in faixas_x) / len(faixas_x)
    faixas_x = [(i, f) for i, f in faixas_x if f - i >= max(4, largura_media * 0.35)]

    saida = []
    for x0, x1 in faixas_x:
        lin_vazia = [all(px[x, y] == 0 for x in range(x0, x1)) for y in range(A)]
        fy = faixas(lin_vazia)
        altura_media = (sum(f - i for i, f in fy) / len(fy)) if fy else 0
        fy = [(i, f) for i, f in fy if f - i >= max(4, altura_media * 0.35)]
        for y0, y1 in fy or [(0, A)]:
            # o eixo Y da Unity cresce para cima; o do Pillow, para baixo
            saida.append([x0, A - y1, x1 - x0, y1 - y0])
    return saida


def main():
    if not os.path.isdir(PASTA):
        print("pasta nao encontrada:", PASTA, file=sys.stderr)
        return

    mapa, total, grades, tiras = {}, 0, 0, 0
    arquivos = sorted(f for f in os.listdir(PASTA) if f.endswith(".png"))
    for k, nome in enumerate(arquivos):
        if k % 200 == 0:
            print(f"  {k}/{len(arquivos)}...")
        try:
            q = quadros(os.path.join(PASTA, nome))
        except Exception as e:
            print(f"  {nome}: {e}", file=sys.stderr)
            continue
        if not q:
            continue
        mapa[os.path.splitext(nome)[0]] = q
        total += len(q)
        # varias linhas distintas de Y = grade; uma so = tira
        if len({r[1] for r in q}) > 1:
            grades += 1
        else:
            tiras += 1

    json.dump(mapa, open(SAIDA, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"\n{len(mapa)} folhas, {total} quadros ({tiras} tiras, {grades} grades)")
    for exemplo in ("0004", "0004b", "0007"):
        if exemplo in mapa:
            print(f"  {exemplo}: {len(mapa[exemplo])} quadros, primeiro {mapa[exemplo][0]}")
    print("escrito em", SAIDA)


if __name__ == "__main__":
    main()
