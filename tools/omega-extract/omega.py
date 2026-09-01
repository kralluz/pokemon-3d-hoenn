"""Decryptor dos AssetBundles do Omega Ruby (Unity 2022.3 + HybridCLR).

Esquema (reconstruido de AssetBundleEncryption::DecryStream, arm64):
    pb  = base64(utf8(abLoadPath))          ; abLoadPath = AssetName do manifesto
    L   = len(pb)
    hdr = arquivo[0:L]                      ; bytes aleatorios gravados por EncryFile
    randKeys[i] = pb[i] ^ hdr[i] ^ F[i % 14]
    corpo[j]   ^= randKeys[j % L] ^ F[(L + j) % 14]
F[i] = KEYS_1[i%7] ^ KEYS_2[i%14]. Só as diferenças de F importam (a constante
global cancela, pois os dois indices tem sempre a mesma paridade).
O texto decifrado e um arquivo .7z contendo o AssetBundle.
"""
import base64, json, os, string, struct, zlib

MAGIC = bytes.fromhex("377abcaf271c0004")          # assinatura 7z
MANIFEST = "D1C2327F-8C01-2EC1-8BD0-91F351F97D14"  # AssetBundleConst.ENCRYABINFOFILE
F = [0x00, 0x00, 0xaf, 0x89, 0x03, 0x4a, 0x58, 0xa6,
     0x4a, 0xfe, 0xce, 0x4d, 0x8a, 0xb2]

def decrypt(data, name):
    pb = base64.b64encode(name.encode())
    L = len(pb)
    if len(data) < L + 4:
        return None
    rk = bytes(pb[i] ^ data[i] ^ F[i % 14] for i in range(L))
    body = data[L + 4:]
    ks = bytes(rk[j % L] ^ F[(L + j) % 14] for j in range(_period(L)))
    return bytes(b ^ ks[i % len(ks)] for i, b in enumerate(body))

def _period(L):
    import math
    return math.lcm(L, 14)

def head32(data, name):
    """Primeiros 32 bytes decifrados, ou None se nao couber."""
    pb = base64.b64encode(name.encode())
    L = len(pb)
    if len(data) < L + 36:
        return None
    rk = [pb[i] ^ data[i] ^ F[i % 14] for i in range(L)]
    return bytes(data[L + 4 + j] ^ rk[j % L] ^ F[(L + j) % 14] for j in range(32))

def valid(data, name):
    h = head32(data, name)
    return (h is not None and h[:8] == MAGIC
            and struct.pack("<I", zlib.crc32(h[12:32])) == h[8:12])

def prefix8(data, L):
    """Os 8 primeiros chars do base64 do nome (= 6 primeiros chars do nome)."""
    if len(data) < L + 12:
        return None
    return bytes(data[L + 4 + u] ^ MAGIC[u] ^ data[u] ^ F[u % 14] ^ F[(L + u) % 14]
                 for u in range(8))

_TSV = set((string.ascii_letters + string.digits + "_/.-").encode()) | set(b"\t\n\r")

def read_manifest(path):
    """Decifra o manifesto sem chave, resolvendo o keystream pelo alfabeto TSV."""
    d = open(path, "rb").read()
    L, P = 48, _period(48)
    body = d[L + 4:]
    ks = bytearray(P)
    for r in range(P):
        col = body[r::P]
        c = [k for k in range(256) if all((b ^ k) in _TSV for b in col)]
        ks[r] = c[0] if c else max(range(256),
                                   key=lambda k: sum(((b ^ k) in _TSV) for b in col))
    txt = bytes(b ^ ks[i % P] for i, b in enumerate(body)).decode("utf-8", "replace")
    out = []
    for line in txt.split("\n"):
        f = line.strip("\r").split("\t")
        if len(f) == 4 and f[1].isdigit():
            out.append({"name": f[0], "size": int(f[1]), "hash": f[2]})
    return out

def _ks_at(pb, data, L, j):
    return (pb[j % L] ^ data[j % L] ^ F[(j % L) % 14]) ^ F[(L + j) % 14]

def valid_full(data, name):
    """Confirma o nome checando tambem o CRC do next-header do 7z (fim do arquivo)."""
    h = head32(data, name)
    if h is None or h[:8] != MAGIC:
        return False
    if struct.pack("<I", zlib.crc32(h[12:32])) != h[8:12]:
        return False
    off, sz, hcrc = struct.unpack_from("<QQI", h, 12)
    pb = base64.b64encode(name.encode())
    L = len(pb)
    start, end = L + 4 + 32 + off, L + 4 + 32 + off + sz
    if sz == 0 or end > len(data):
        return False
    nh = bytes(data[i] ^ _ks_at(pb, data, L, i - L - 4) for i in range(start, end))
    return zlib.crc32(nh) == hcrc
