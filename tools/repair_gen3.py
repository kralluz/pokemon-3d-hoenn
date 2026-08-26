#!/usr/bin/env python3
"""
Repara os modelos da Gen 3 que vieram sem clipes de animacao.

O datamine do pogo_assets guarda varias copias do mesmo rig (a canonica, as
variantes "#123456" e a pasta legada "3D Assets/Pokemon/"). Nem toda copia
carrega os AnimationStacks. Este script testa todas as copias de cada modelo
sem animacao e substitui pela que tiver mais clipes.

Uso: python tools/repair_gen3.py [--out assets/gen3]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO = "PokeMiners/pogo_assets"
BRANCH = "master"
RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
TREE = "https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
UA = {"User-Agent": "gen3-repair"}


def get(url, timeout=180):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def anims_of(blob):
    if not blob.startswith(b"Kaydara"):
        return []
    seen, out = set(), []
    for n in re.findall(rb"([\x20-\x7e]{3,60})\x00\x01AnimStack", blob):
        n = n.decode("ascii", "replace")
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def candidates(tree, rig):
    """Todos os caminhos .fbx do repo cujo nome de arquivo seja <rig>.fbx."""
    want = rig + ".fbx"
    return [e["path"] for e in tree
            if e["type"] == "blob" and e["path"].rsplit("/", 1)[-1] == want]


def best_copy(tree, rig):
    """Baixa cada copia e devolve (caminho, blob, anims) com mais animacoes."""
    best = (None, None, [])
    for path in candidates(tree, rig):
        try:
            blob = get(RAW.format(repo=REPO, branch=BRANCH, path=urllib.parse.quote(path)))
        except Exception:
            continue
        a = anims_of(blob)
        if len(a) > len(best[2]):
            best = (path, blob, a)
        if len(a) >= 27:  # ja e o set completo, nao precisa procurar mais
            break
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "gen3"))
    args = ap.parse_args()

    mpath = os.path.join(args.out, "manifest.json")
    man = json.load(open(mpath, encoding="utf-8"))
    broken = [m for m in man["models"] if not m["animations"]]
    if not broken:
        print("Nada a reparar.")
        return

    print(f"Lendo a arvore do repositorio ({len(broken)} modelos a reparar)...")
    tree = json.loads(get(TREE.format(repo=REPO, branch=BRANCH)))["tree"]

    def work(m):
        rig = m["fbx"][:-4]  # pm0257_00_Rig
        path, blob, a = best_copy(tree, rig)
        if not a:
            return m, None, []
        target = os.path.join(args.out, m["dir"], m["fbx"])
        with open(target, "wb") as fh:
            fh.write(blob)
        return m, path, a

    fixed = 0
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        for m, path, a in pool.map(work, broken):
            if a:
                m["animations"] = a
                m["fbx_source"] = path
                fixed += 1
                print(f"  OK  {m['dir']:28s} {len(a)} anims  <- {path.split('/')[2]}/...")
            else:
                print(f"  --  {m['dir']:28s} nenhuma copia animada no repo", file=sys.stderr)

    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2)

    still = [m["dir"] for m in man["models"] if not m["animations"]]
    print(f"\nReparados: {fixed}/{len(broken)}")
    print(f"Total com animacao: {len(man['models']) - len(still)}/{len(man['models'])}")
    if still:
        print("Ainda sem animacao:", ", ".join(still))


if __name__ == "__main__":
    main()
