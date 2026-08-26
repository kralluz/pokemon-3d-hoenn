#!/usr/bin/env python3
"""
Baixa um subconjunto curado da Kenney Nature Kit (GLB) e o pacote de
personagem animado (FBX), via o espelho GitHub de assets Kenney.

Fonte: https://github.com/ETdoFresh/kenney.nl -- CC0, uso comercial liberado.

Uso: python tools/fetch_world_kit.py
"""

import concurrent.futures as cf
import os
import urllib.request

REPO = "ETdoFresh/kenney.nl"
BRANCH = "master"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{{path}}"
UA = {"User-Agent": "world-kit-fetch"}

OUT_ENV = os.path.join("assets", "environment")
OUT_CHAR = os.path.join("assets", "character")

# subconjunto da Nature Kit que da para montar um terreno andavel:
# chao, caminho, agua, arvores, rochas, grama, cercas, pontes
NATURE_MODELS = [
    "ground_grass.glb", "ground_pathTile.glb", "ground_pathStraight.glb", "ground_pathCorner.glb",
    "ground_riverStraight.glb", "ground_riverCorner.glb", "ground_riverTile.glb",
    "tree_default.glb", "tree_detailed.glb",
    "tree_oak.glb", "tree_palm.glb", "tree_pineDefaultA.glb", "tree_pineRoundA.glb",
    "tree_pineGroundA.glb", "tree_pineGroundB.glb",
    "rock_largeA.glb", "rock_largeB.glb", "rock_smallA.glb", "rock_smallB.glb",
    "rock_tallA.glb", "grass.glb", "grass_large.glb", "flower_purpleA.glb",
    "flower_redA.glb", "flower_yellowA.glb", "mushroom_red.glb", "mushroom_tan.glb",
    "log.glb", "log_stack.glb", "stump_round.glb", "stump_squareDetailed.glb",
    "fence_simple.glb", "fence_gate.glb", "bridge_wood.glb", "bridge_side_wood.glb",
    "path_stone.glb", "path_wood.glb",
]

CHARACTER_FILES = [
    ("animated-characters-1/Model/characterMedium.fbx", "character.fbx"),
    ("animated-characters-1/Animations/idle.fbx", "idle.fbx"),
    ("animated-characters-1/Animations/run.fbx", "run.fbx"),
    ("animated-characters-1/Animations/jump.fbx", "jump.fbx"),
    ("animated-characters-1/Skins/survivorMaleB.png", "character_skin.png"),
]


def get(url, timeout=90):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def fetch_one(args):
    repo_path, target = args
    if os.path.exists(target) and os.path.getsize(target) > 0:
        return target, "ja existe"
    try:
        data = get(RAW.format(path=urllib.request.quote(repo_path)))
    except Exception as e:
        return target, f"FALHOU: {e}"
    with open(target, "wb") as fh:
        fh.write(data)
    return target, f"{len(data) / 1024:.0f} KB"


def main():
    os.makedirs(OUT_ENV, exist_ok=True)
    os.makedirs(OUT_CHAR, exist_ok=True)

    jobs = [
        (f"kenney_natureKit_2.1/Models/GLTF format/{n}", os.path.join(OUT_ENV, n))
        for n in NATURE_MODELS
    ] + [
        (repo_path, os.path.join(OUT_CHAR, target))
        for repo_path, target in CHARACTER_FILES
    ]

    ok, fail = 0, []
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        for target, status in pool.map(fetch_one, jobs):
            print(f"  {os.path.basename(target):32s} {status}")
            if status.startswith("FALHOU"):
                fail.append(target)
            else:
                ok += 1

    print(f"\n{ok}/{len(jobs)} arquivos prontos.")
    if fail:
        print("falharam:", fail)


if __name__ == "__main__":
    main()
