"""Escritor minimo de GLB (glTF 2.0 binario) com suporte a skin e animacao."""
import json, struct

# tipos de componente glTF
BYTE, UBYTE, SHORT, USHORT, UINT, FLOAT = 5120, 5121, 5122, 5123, 5125, 5126
_SIZE = {BYTE: 1, UBYTE: 1, SHORT: 2, USHORT: 2, UINT: 4, FLOAT: 4}
_COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_FMT = {FLOAT: "f", UINT: "I", USHORT: "H", UBYTE: "B"}


class GLB:
    def __init__(self):
        self.json = {
            "asset": {"version": "2.0", "generator": "omega-extract"},
            "scene": 0, "scenes": [{"nodes": []}],
            "nodes": [], "meshes": [], "materials": [], "textures": [],
            "images": [], "samplers": [{"magFilter": 9729, "minFilter": 9987,
                                        "wrapS": 10497, "wrapT": 10497}],
            "accessors": [], "bufferViews": [], "skins": [], "animations": [],
        }
        self.bin = bytearray()

    # ---- buffer -------------------------------------------------------------
    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        off = len(self.bin)
        self.bin.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        self.json["bufferViews"].append(v)
        return len(self.json["bufferViews"]) - 1

    def accessor(self, values, ctype, atype, target=None, minmax=False):
        """values: lista de tuplas (ou escalares). Devolve o indice do accessor."""
        n = _COUNT[atype]
        flat = []
        for v in values:
            if n == 1:
                flat.append(v)
            else:
                flat.extend(v)
        if len(flat) != len(values) * n:
            raise ValueError(f"accessor {atype}: esperado {len(values)*n} componentes, "
                             f"recebeu {len(flat)} (tupla de tamanho errado?)")
        data = struct.pack(f"<{len(flat)}{_FMT[ctype]}", *flat)
        acc = {"bufferView": self._view(data, target), "componentType": ctype,
               "count": len(values), "type": atype}
        if minmax and values and n > 1:
            cols = list(zip(*values))
            acc["min"] = [float(min(c)) for c in cols]
            acc["max"] = [float(max(c)) for c in cols]
        elif minmax and values:
            acc["min"] = [float(min(values))]
            acc["max"] = [float(max(values))]
        self.json["accessors"].append(acc)
        return len(self.json["accessors"]) - 1

    def image_png(self, png_bytes):
        bv = self._view(png_bytes)
        self.json["images"].append({"bufferView": bv, "mimeType": "image/png"})
        return len(self.json["images"]) - 1

    def texture(self, image_idx):
        self.json["textures"].append({"sampler": 0, "source": image_idx})
        return len(self.json["textures"]) - 1

    # ---- saida --------------------------------------------------------------
    def save(self, path):
        j = {k: v for k, v in self.json.items() if v or k in ("asset", "scene", "scenes")}
        j["buffers"] = [{"byteLength": len(self.bin)}]
        jb = json.dumps(j, separators=(",", ":")).encode("utf-8")
        jb += b" " * ((4 - len(jb) % 4) % 4)
        bb = bytes(self.bin) + b"\0" * ((4 - len(self.bin) % 4) % 4)
        with open(path, "wb") as fh:
            fh.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jb) + 8 + len(bb)))
            fh.write(struct.pack("<II", len(jb), 0x4E4F534A)); fh.write(jb)
            fh.write(struct.pack("<II", len(bb), 0x004E4942)); fh.write(bb)
        return len(jb) + len(bb)
