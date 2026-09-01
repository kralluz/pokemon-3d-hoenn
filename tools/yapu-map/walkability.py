"""Grade de andabilidade a partir do JSON do mapa.

Segue GetTypeOfTileDirectlyBelowSortOrder do GridController: vale a camada de
maior sortingOrder ABAIXO do personagem que tenha tile na celula.

O corte e o sort order do corpo do personagem, 20 (Shadow=15, Body=20, Head=45
nos SpriteRenderers dos NPCs das cenas ripadas). Isso importa: os predios sao
tiles, com a BASE em OverShadowDetail (17, abaixo -> bloqueia) e o TOPO em
OverBodyDetail (25, acima -> voce passa por tras). Cortar em 'nome comeca com
Over' deixaria as casas andaveis.
"""
import json

# TileType (YAPU/Runtime/World/TileType.cs)
NONEXISTENT, WALKABLE, NONWALKABLE, JUMPABLE, BRIDGE, BRIDGE_ENTRANCE, \
    WATER, WATERFALL, SLIPPERY, WALKABLE_NOT_BIKABLE = range(10)

WALKABLE_TYPES = {WALKABLE, JUMPABLE, BRIDGE, BRIDGE_ENTRANCE, SLIPPERY, WALKABLE_NOT_BIKABLE}
NAMES = ["NonExistent", "Walkable", "NonWalkable", "Jumpable", "Bridge",
         "BridgeEntrance", "Water", "Waterfall", "Slippery", "WalkableNotBikable"]


PLAYER_SORT_ORDER = 20


def ground_layers(m):
    return [l for l in m["layers"]
            if l["order"] < PLAYER_SORT_ORDER or l["name"].startswith("Bridge")]


def build(m):
    """(x,y) -> TileType da camada mais alta abaixo do personagem."""
    best = {}
    for l in ground_layers(m):
        o = l["order"]
        for c in l["cells"]:
            k = (c["x"], c["y"])
            prev = best.get(k)
            if prev is None or o > prev[0]:
                best[k] = (o, c["type"])
    return {k: v[1] for k, v in best.items()}


def stats(grid):
    from collections import Counter
    c = Counter(grid.values())
    return {NAMES[t]: n for t, n in sorted(c.items())}
