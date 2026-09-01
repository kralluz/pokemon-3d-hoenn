"""Decodifica AnimationClip do Mecanim (m_MuscleClip) para curvas por osso.

O clip guarda as curvas em tres blocos, concatenados nesta ordem de indice:
    m_StreamedClip   quadros esparsos: [tempo, nKeys, (indice, coef[4]) * nKeys]
                     o valor da curva no quadro e coef[3]
                     o primeiro e o ultimo quadro sao sentinelas (-3.4e38 / +inf)
    m_DenseClip      amostragem regular: m_SampleArray[frame * nCurves + i]
    m_ConstantClip   valor fixo ao longo de todo o clip

m_ClipBindingConstant.genericBindings diz a que osso/propriedade cada indice
pertence. Cada binding consome varias curvas (posicao 3, rotacao 4, escala 3).
O campo `path` e o CRC32 do caminho do Transform relativo ao root do Animator.
"""
import struct

F32 = struct.Struct("<f")
U32 = struct.Struct("<I")

def _f(u):
    return F32.unpack(U32.pack(u & 0xFFFFFFFF))[0]

# atributos de Transform
POS, ROT, SCALE, EULER = 1, 2, 3, 4
_SIZE = {POS: 3, ROT: 4, SCALE: 3, EULER: 3}

def curve_size(b):
    return _SIZE.get(b["attribute"], 1) if b.get("typeID") == 4 else 1


def read_streamed(data):
    """[(tempo, [(indice, coef[4])])] — ja sem os quadros sentinela."""
    out, i, n = [], 0, len(data)
    while i + 1 < n:
        t = _f(data[i]); i += 1
        k = data[i]; i += 1
        keys = []
        for _ in range(k):
            if i + 4 >= n:
                break
            idx = data[i]; i += 1
            keys.append((idx, [_f(data[i + j]) for j in range(4)]))
            i += 4
        out.append((t, keys))
    return [f for f in out if -1e30 < f[0] < 1e30]


def decode(clip_tt):
    """Devolve {(path_hash, attribute): [(tempo, [valores])]} ordenado por tempo."""
    mc = clip_tt.get("m_MuscleClip") or {}
    blocks = (mc.get("m_Clip") or {}).get("data") or {}
    streamed = blocks.get("m_StreamedClip") or {}
    dense = blocks.get("m_DenseClip") or {}
    const = blocks.get("m_ConstantClip") or {}
    bindings = (clip_tt.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
    stop = float(mc.get("m_StopTime") or 0.0)

    # indice de curva -> (binding, componente)
    index_map = []
    for b in bindings:
        for k in range(curve_size(b)):
            index_map.append((b, k))

    tracks = {}
    def put(t, ci, val):
        if ci >= len(index_map):
            return
        b, sub = index_map[ci]
        tr = tracks.setdefault((b["path"], b["attribute"]), {})
        tr.setdefault(round(t, 6), [0.0] * curve_size(b))[sub] = val

    for t, keys in read_streamed(streamed.get("data") or []):
        for idx, coeff in keys:
            put(t, idx, coeff[3])

    sc = int(streamed.get("curveCount") or 0)
    dc = int(dense.get("m_CurveCount") or 0)
    fc = int(dense.get("m_FrameCount") or 0)
    arr = dense.get("m_SampleArray") or []
    rate = float(dense.get("m_SampleRate") or 30.0) or 30.0
    begin = float(dense.get("m_BeginTime") or 0.0)
    for f in range(fc):
        for i in range(dc):
            j = f * dc + i
            if j < len(arr):
                put(begin + f / rate, sc + i, arr[j])

    for i, v in enumerate(const.get("data") or []):
        put(0.0, sc + dc + i, v)
        if stop > 0:
            put(stop, sc + dc + i, v)

    return {k: sorted(v.items()) for k, v in tracks.items() if v}
