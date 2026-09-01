"""Leitor minimo do dialeto YAML que o Unity/AssetRipper escreve.

Nao e um YAML generico: cobre so o que aparece nos .unity/.asset -- mapas por
indentacao, sequencias com '-', escalares e os flow maps {x: 1, y: 2}. Em troca
le um arquivo de 10 MB em segundos, o que o PyYAML nao faz.
"""
import re

FLOW = re.compile(r"^\{(.*)\}$")


def _scalar(s):
    s = s.strip()
    if not s: return None
    if s == "[]": return []
    if s == "{}": return {}
    m = FLOW.match(s)
    if m:
        out = {}
        for part in m.group(1).split(","):
            if ":" not in part: continue
            k, v = part.split(":", 1)
            out[k.strip()] = _scalar(v)
        return out
    if s.startswith("'") and s.endswith("'"): return s[1:-1]
    if s.startswith('"') and s.endswith('"'): return s[1:-1]
    try: return int(s)
    except ValueError: pass
    try: return float(s)
    except ValueError: pass
    return s


class _Lines:
    def __init__(self, lines):
        self.lines, self.i = lines, 0

    def peek(self):
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            s = raw.strip()
            if not s or s.startswith("#"):
                self.i += 1; continue
            return len(raw) - len(raw.lstrip(" ")), s
        return None, None


def _value(lines, indent):
    """Valor de 'chave:' sem escalar na linha. No dialeto do Unity uma sequencia
    fica na MESMA indentacao da chave; um mapa aninhado fica mais fundo."""
    ind, s = lines.peek()
    if s is None: return None
    if ind == indent and (s == "-" or s.startswith("- ")): return _seq(lines, ind)
    if ind > indent:
        if s == "-" or s.startswith("- "): return _seq(lines, ind)
        return _map(lines, ind)
    return None


def _seq(lines, indent):
    out = []
    while True:
        ind, s = lines.peek()
        if s is None or ind != indent or not (s == "-" or s.startswith("- ")): break
        lines.i += 1
        rest = s[2:] if s.startswith("- ") else ""
        if not rest:
            out.append(_value(lines, indent))
            continue
        if ":" in rest and not FLOW.match(rest):
            # '- key: valor' abre um mapa cujo restante vem indentado abaixo
            k, v = rest.split(":", 1)
            item = {}
            if v.strip():
                item[k.strip()] = _scalar(v)
            else:
                item[k.strip()] = _value(lines, indent + 2)
            sub = _map(lines, indent + 2, into=item)
            out.append(sub)
        else:
            out.append(_scalar(rest))
    return out


def _map(lines, indent, into=None):
    out = into if into is not None else {}
    while True:
        ind, s = lines.peek()
        if s is None or ind < indent: break
        if ind > indent or s.startswith("- "): break
        if ":" not in s: break
        lines.i += 1
        k, v = s.split(":", 1)
        k, v = k.strip(), v.strip()
        out[k] = _scalar(v) if v else _value(lines, indent)
    return out


def load_documents(path):
    """Devolve [(class_id, file_id, tipo, corpo)] para cada '--- !u!N &M'."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read().splitlines()
    heads = [i for i, l in enumerate(raw) if l.startswith("--- !u!")]
    docs = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(raw)
        m = re.match(r"--- !u!(\d+) &(-?\d+)", raw[start])
        if not m: continue
        body_lines = raw[start + 1:end]
        lines = _Lines(body_lines)
        top = _map(lines, 0)
        if not top: continue
        tname = next(iter(top))
        docs.append((int(m.group(1)), int(m.group(2)), tname, top[tname] or {}))
    return docs
