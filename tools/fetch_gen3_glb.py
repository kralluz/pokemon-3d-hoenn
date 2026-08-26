#!/usr/bin/env python3
"""
Baixa os modelos GLB da 3a geracao do repositorio Pokemon-3D-api/assets e gera
viewer/models.json.

Por que GLB e nao os FBX de assets/gen3: esses GLB ja vem com a malha separada
por material (corpo, olho, boca), entao o navegador renderiza certo sem precisar
reconstruir o shader do Pokemon GO. Os FBX continuam sendo a fonte de rig para
uso em engine -- veja assets/gen3/README.md.

Uso: python tools/fetch_gen3_glb.py [--out assets/gen3_glb] [--jobs 8]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO = "Pokemon-3D-api/assets"
BRANCH = "main"
TREE = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{{path}}"
UA = {"User-Agent": "gen3-glb"}

# pasta do repo -> (rotulo, ordem)
FOLDERS = {
    "regular": ("Normal", 0),
    "mega": ("Mega", 10),
    "galar": ("Galar", 11),
    "primal": ("Primal", 12),
    "shiny": ("Shiny", 20),
    "megaShiny": ("Mega shiny", 21),
}
# arquivos de nome nao-numerico que sao da Gen 3
NAMED = {
    "multiform/Deoxys_Attack_Form": (386, "Ataque", 1),
    "multiform/Deoxys_Defense_Form": (386, "Defesa", 2),
    "multiform/Deoxys_Speed_Form": (386, "Velocidade", 3),
}

CACHE = os.path.join("tools", ".pokeapi_cache.json")


def get(url, timeout=120):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def names_and_types():
    """{dex: (nome, [tipos])} via PokeAPI, com cache local."""
    if os.path.exists(CACHE):
        try:
            types = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            types = {}
    else:
        types = {}

    def one(dex):
        try:
            d = json.loads(get(f"https://pokeapi.co/api/v2/pokemon/{dex}", 45))
            return dex, d["name"], [t["type"]["name"] for t in d["types"]]
        except Exception:
            return dex, f"pokemon-{dex}", types.get(str(dex), [])

    out = {}
    print("Buscando nomes e tipos na PokeAPI...")
    with cf.ThreadPoolExecutor(max_workers=10) as pool:
        for dex, name, tp in pool.map(one, range(252, 387)):
            out[dex] = (name, tp or types.get(str(dex), []))
    json.dump({str(d): t for d, (_, t) in out.items()}, open(CACHE, "w", encoding="utf-8"))
    return out


def title(slug):
    slug = re.sub(r"-(normal|standard)$", "", slug)
    return " ".join(p.capitalize() for p in slug.split("-"))


def collect(tree):
    """[(dex, rotulo, ordem, caminho_no_repo, tamanho)]"""
    jobs = []
    for entry in tree:
        if entry["type"] != "blob" or not entry["path"].endswith(".glb"):
            continue
        parts = entry["path"].split("/")
        if len(parts) < 4:
            continue
        folder, stem = parts[2], parts[3][:-4]
        size = entry.get("size", 0)

        if folder in FOLDERS and stem.isdigit() and 252 <= int(stem) <= 386:
            label, order = FOLDERS[folder]
            jobs.append((int(stem), label, order, entry["path"], size))
        else:
            key = f"{folder}/{stem}"
            if key in NAMED:
                dex, label, order = NAMED[key]
                jobs.append((dex, label, order, entry["path"], size))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "gen3_glb"))
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    print("Lendo a arvore do repositorio...")
    tree = json.loads(get(TREE))["tree"]
    jobs = collect(tree)
    mb = sum(j[4] for j in jobs) / 1024 / 1024
    print(f"{len(jobs)} modelos, {mb:.1f} MB")

    os.makedirs(args.out, exist_ok=True)
    meta = names_and_types()

    def fetch(job):
        dex, label, order, path, size = job
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        fname = f"{dex:04d}_{slug}.glb"
        target = os.path.join(args.out, fname)
        if not (os.path.exists(target) and os.path.getsize(target) == size):
            data = get(RAW.format(path=urllib.parse.quote(path)))
            with open(target, "wb") as fh:
                fh.write(data)
        return dex, label, order, fname, os.path.getsize(target)

    done, results = 0, []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for r in pool.map(fetch, jobs):
            done += 1
            results.append(r)
            if done % 25 == 0:
                print(f"  {done}/{len(jobs)}...")

    species = {}
    for dex, label, order, fname, size in results:
        name, types = meta.get(dex, (f"pokemon-{dex}", []))
        sp = species.setdefault(dex, {"dex": dex, "name": title(name), "slug": name,
                                      "types": types, "variants": []})
        sp["variants"].append({"id": fname[:-4], "label": label, "order": order,
                               "file": fname, "kb": size // 1024})

    for sp in species.values():
        sp["variants"].sort(key=lambda v: v["order"])
        for v in sp["variants"]:
            del v["order"]

    thumbs = os.path.join("viewer", "thumbs")
    data = {
        "generation": 3, "region": "Hoenn",
        "root": "../" + args.out.replace("\\", "/"),
        "format": "glb",
        "source": f"https://github.com/{REPO}",
        "thumbs": os.path.isdir(thumbs) and len(os.listdir(thumbs)) >= len(results),
        "species": [species[d] for d in sorted(species)],
    }
    os.makedirs("viewer", exist_ok=True)
    json.dump(data, open(os.path.join("viewer", "models.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    faltando = [d for d in range(252, 387) if d not in species]
    print(f"\n{len(species)} especies, {len(results)} modelos em {args.out}/")
    print("viewer/models.json gerado.")
    if faltando:
        print("faltando:", faltando)


if __name__ == "__main__":
    main()
