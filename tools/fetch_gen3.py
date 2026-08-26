#!/usr/bin/env python3
"""
Baixa os modelos 3D animados (FBX + texturas) de TODOS os Pokemon da 3a geracao
(#252-386, Hoenn) a partir do repositorio PokeMiners/pogo_assets.

Fonte : https://github.com/PokeMiners/pogo_assets  ("3D Assets/Addressable Assets")
Origem: assets minerados do Pokemon GO (Niantic/Nintendo/Creatures/GAME FREAK)
Formato: FBX 7.3 binario, rig com skin + 28 clipes de animacao por modelo.

Uso:  python tools/fetch_gen3.py [--out assets/gen3] [--jobs 8]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import struct
import sys
import urllib.parse
import urllib.request

REPO = "PokeMiners/pogo_assets"
BRANCH = "master"
ROOT = "3D Assets/Addressable Assets"
RAW = "https://raw.githubusercontent.com/{repo}/{branch}/{path}"
TREE = "https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
UA = {"User-Agent": "gen3-fetch"}

# sufixo do codigo de forma -> rotulo da pasta
FORM_LABELS = {
    "00": "",
    "11": "normal",
    "12": "attack" ,   # Deoxys 12 = Attack, Castform 12 = sunny (ajustado abaixo)
    "13": "defense",
    "14": "speed",
    "31": "galarian",
    "51": "mega",
    "52": "mega_y",
    "61": "alolan",
}
CASTFORM = {"11": "normal", "12": "sunny", "13": "rainy", "14": "snowy"}


def get(url, timeout=120):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pokemon_names():
    """Nomes #252-386 via PokeAPI; cai para IDs se estiver offline."""
    try:
        data = json.loads(get("https://pokeapi.co/api/v2/pokemon?limit=135&offset=251", 60))
        return {251 + i + 1: slug(r["name"]) for i, r in enumerate(data["results"])}
    except Exception as e:
        print(f"  ! PokeAPI indisponivel ({e}); usando so os IDs", file=sys.stderr)
        return {}


def fbx_animations(path):
    """Le os nomes dos AnimationStacks de um FBX binario."""
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"Kaydara"):
        return None
    names = re.findall(rb"([\x20-\x7e]{3,60})\x00\x01AnimStack", data)
    seen, out = set(), []
    for n in names:
        n = n.decode("ascii", "replace")
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def build_jobs(tree, names):
    """Agrupa os blobs do repo por pasta *_Rig canonica dentro do range da Gen 3."""
    groups = {}
    for entry in tree:
        if entry["type"] != "blob":
            continue
        p = entry["path"]
        if not p.startswith(ROOT + "/"):
            continue
        m = re.match(re.escape(ROOT) + r"/pm(\d{4})/(pm\d{4}_(\d{2})_Rig)/([^/]+)$", p)
        if not m:
            continue  # ignora as variantes "#123456" (duplicatas do datamine)
        dex, form = int(m.group(1)), m.group(3)
        if not (252 <= dex <= 386):
            continue
        groups.setdefault((dex, form), []).append((p, entry.get("size", 0)))

    jobs = []
    for (dex, form), files in sorted(groups.items()):
        label = CASTFORM.get(form, FORM_LABELS.get(form, form)) if dex == 351 else FORM_LABELS.get(form, form)
        parts = [f"{dex:04d}", names.get(dex, f"pm{dex:04d}")]
        if label:
            parts.append(label)
        jobs.append({"dex": dex, "form": form, "dir": "_".join(parts), "files": files})
    return jobs


def fetch(job, out_dir):
    dest = os.path.join(out_dir, job["dir"])
    os.makedirs(dest, exist_ok=True)
    got, fbx = [], None
    for path, size in job["files"]:
        name = path.rsplit("/", 1)[-1]
        target = os.path.join(dest, name)
        if os.path.exists(target) and os.path.getsize(target) == size:
            got.append(name)
            if name.endswith(".fbx"):
                fbx = target
            continue
        url = RAW.format(repo=REPO, branch=BRANCH, path=urllib.parse.quote(path))
        with open(target, "wb") as fh:
            fh.write(get(url))
        got.append(name)
        if name.endswith(".fbx"):
            fbx = target
    anims = fbx_animations(fbx) if fbx else None
    return {
        "dex": job["dex"],
        "form": job["form"],
        "dir": job["dir"],
        "fbx": os.path.basename(fbx) if fbx else None,
        "textures": sorted(n for n in got if n.endswith(".png")),
        "animations": anims or [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "gen3"))
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    print("Lendo a arvore de arquivos do repositorio...")
    tree = json.loads(get(TREE.format(repo=REPO, branch=BRANCH)))["tree"]
    print("Buscando os nomes na PokeAPI...")
    names = pokemon_names()

    jobs = build_jobs(tree, names)
    total = sum(len(j["files"]) for j in jobs)
    mb = sum(s for j in jobs for _, s in j["files"]) / 1024 / 1024
    print(f"{len(jobs)} modelos ({len(set(j['dex'] for j in jobs))} especies), "
          f"{total} arquivos, {mb:.1f} MB\n")

    os.makedirs(args.out, exist_ok=True)
    manifest, done = [], 0
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch, j, args.out): j for j in jobs}
        for fut in cf.as_completed(futures):
            job = futures[fut]
            done += 1
            try:
                rec = fut.result()
                manifest.append(rec)
                print(f"[{done:3d}/{len(jobs)}] {rec['dir']:34s} "
                      f"{len(rec['animations']):2d} anims, {len(rec['textures'])} texturas")
            except Exception as e:
                print(f"[{done:3d}/{len(jobs)}] {job['dir']:34s} FALHOU: {e}", file=sys.stderr)

    manifest.sort(key=lambda r: (r["dex"], r["form"]))
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"source": f"https://github.com/{REPO}", "root": ROOT,
                   "generation": 3, "models": manifest}, fh, indent=2)

    sem = [r["dir"] for r in manifest if not r["animations"]]
    print(f"\nOK: {len(manifest)} modelos em {args.out}/")
    print(f"Com animacao: {len(manifest) - len(sem)}   sem animacao: {len(sem)}")
    if sem:
        print("  sem animacao:", ", ".join(sem))
    print("manifest.json escrito.")


if __name__ == "__main__":
    main()
