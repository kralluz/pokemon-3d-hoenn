#!/usr/bin/env python3
"""
Leitor minimo de FBX binario (7.x).

O FBXLoader do three.js so pega uma textura por material, mas esses modelos
empilham varias texturas num atlas endereçado pela coordenada V (0-1 = telha 0,
1-2 = telha 1, ...). Para montar o atlas na ordem certa e preciso ler as
conexoes Material -> Texture do proprio arquivo.

Uso como biblioteca:  from fbx_reader import read_fbx, material_textures
Uso na linha de comando:  python tools/fbx_reader.py <arquivo.fbx>
"""

import struct
import sys
import zlib

_ARRAY = {b"f": ("f", 4), b"d": ("d", 8), b"l": ("q", 8), b"i": ("i", 4), b"b": ("b", 1)}
_SCALAR = {b"Y": ("h", 2), b"C": ("?", 1), b"I": ("i", 4), b"F": ("f", 4), b"D": ("d", 8), b"L": ("q", 8)}


class Node:
    __slots__ = ("name", "props", "children")

    def __init__(self, name, props, children):
        self.name, self.props, self.children = name, props, children

    def find(self, name):
        return [c for c in self.children if c.name == name]

    def first(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def __repr__(self):
        return f"<{self.name} props={len(self.props)} kids={len(self.children)}>"


def _read_prop(buf, pos):
    t = buf[pos:pos + 1]
    pos += 1
    if t in _SCALAR:
        fmt, size = _SCALAR[t]
        return struct.unpack_from("<" + fmt, buf, pos)[0], pos + size
    if t in _ARRAY:
        fmt, size = _ARRAY[t]
        n, enc, clen = struct.unpack_from("<III", buf, pos)
        pos += 12
        raw = buf[pos:pos + clen]
        pos += clen
        if enc:
            raw = zlib.decompress(raw)
        return struct.unpack_from("<%d%s" % (n, fmt), raw, 0), pos
    if t in (b"S", b"R"):
        (n,) = struct.unpack_from("<I", buf, pos)
        pos += 4
        data = buf[pos:pos + n]
        pos += n
        return (data.decode("utf-8", "replace") if t == b"S" else data), pos
    raise ValueError(f"tipo de propriedade desconhecido: {t!r} em {pos}")


def _read_node(buf, pos, version):
    wide = version >= 7500
    fmt, hdr = ("<QQQB", 25) if wide else ("<IIIB", 13)
    end, nprops, _plen, namelen = struct.unpack_from(fmt, buf, pos)
    pos += hdr
    if end == 0:
        return None, pos           # sentinela de fim de lista
    name = buf[pos:pos + namelen].decode("utf-8", "replace")
    pos += namelen

    props = []
    for _ in range(nprops):
        val, pos = _read_prop(buf, pos)
        props.append(val)

    children = []
    while pos < end - (hdr if wide else 13):
        child, pos = _read_node(buf, pos, version)
        if child is None:
            break
        children.append(child)
    return Node(name, props, children), end


def read_fbx(path):
    """Devolve o no raiz com todos os nos de topo como filhos."""
    with open(path, "rb") as fh:
        buf = fh.read()
    if not buf.startswith(b"Kaydara FBX Binary"):
        raise ValueError("nao e um FBX binario")
    version = struct.unpack_from("<I", buf, 23)[0]
    pos = 27
    top = []
    while pos < len(buf) - 16:
        node, pos = _read_node(buf, pos, version)
        if node is None:
            break
        top.append(node)
    return Node("root", [version], top)


def material_textures(root):
    """
    {nome_do_material: [(propriedade, arquivo_da_textura), ...]}
    na ordem em que o FBX conecta as texturas ao material.
    """
    objects = root.first("Objects")
    conns = root.first("Connections")
    if not objects or not conns:
        return {}

    materials, textures, videos = {}, {}, {}
    for n in objects.children:
        if not n.props:
            continue
        oid = n.props[0]
        name = n.props[1].split("\x00")[0] if len(n.props) > 1 and isinstance(n.props[1], str) else ""
        if n.name == "Material":
            materials[oid] = name
        elif n.name == "Texture":
            rel = n.first("RelativeFilename")
            textures[oid] = {"name": name,
                             "file": (rel.props[0].replace("\\", "/").split("/")[-1] if rel and rel.props else None)}
        elif n.name == "Video":
            rel = n.first("RelativeFilename")
            videos[oid] = rel.props[0].replace("\\", "/").split("/")[-1] if rel and rel.props else None

    # Texture -> Video, quando o nome do arquivo so existe no Video
    for c in conns.children:
        if len(c.props) >= 3 and c.props[1] in videos and c.props[2] in textures:
            if not textures[c.props[2]]["file"]:
                textures[c.props[2]]["file"] = videos[c.props[1]]

    out = {}
    for c in conns.children:
        if len(c.props) < 3:
            continue
        kind, child, parent = c.props[0], c.props[1], c.props[2]
        if child in textures and parent in materials:
            prop = c.props[3] if len(c.props) > 3 else "OO"
            out.setdefault(materials[parent], []).append((prop, textures[child]["file"]))
    return out


if __name__ == "__main__":
    for path in sys.argv[1:]:
        root = read_fbx(path)
        print(f"\n=== {path}  (FBX {root.props[0]}) ===")
        for mat, texs in material_textures(root).items():
            print(f"  material '{mat}':")
            for prop, f in texs:
                print(f"     {prop:<22} {f}")
