"""Gera GolpeData e HabilidadeData do APK, e liga tudo nas especies.

Mesma abordagem do gerar_especies.py: escreve o YAML direto, sem abrir a Unity.

Fontes:
  skill/Skill.txt        514 golpes  (tipo, poder, precisao, PP, prioridade, alvo)
  petability/PetAbility.txt  396 habilidades
  pet/Pet.txt            LearnSkillLv + LearnSkillId = o learnset por nivel

DamageClass conferido contra golpes conhecidos: 1=Status, 2=Fisico, 3=Especial
(Growl=1, Tackle=2, Ember=3).
"""
import hashlib
import os
import re

RAIZ = "apk/_extracted/out/assets/TextAsset/config"
DEST = "nel-ord/Assets/Data"

GUID_GOLPE = "5be6db1c70c7951419ace57ed5768a5e"
GUID_HABIL = "1a20a778d07b10743ae74ca9669ea9df"

TIPOS = {
    1: "7788c1f5a8e370e4caa8bc627229e2e3",  2: "3ec9b8b09c1873b4c8b073eb41b7ebb8",
    3: "faf80c8941105994687a08e7c02fedac",  4: "d4a3f35e52be3b4409e1bf5eef2fec3e",
    5: "6e6a0c3264bab96439da1692723df636",  6: "3c6dbf83891dc7449bc1e8adfa475b5f",
    7: "72c4e174e01ea98458539278104ff2b7",  8: "ccd9dac8993f3fc4db09d5939152277e",
    9: "be01fb925829165429b63d05174ea775", 10: "0820d0a6e22f742479b34a3adb3eea59",
    11: "6acb3a60b55b87e4ebaf57b203943857", 12: "94b3a349329baeb41b81057d660ccdc7",
    13: "3eb675cf620da974aa1343f2a86cad2b", 14: "508b442b7fa36a44694627426ea5323f",
    15: "9cbdc79084c61764e907faec7150a3a1", 16: "90e0303f1ab646242ab1baf8f5df64de",
    17: "8540c1fb509668e49a2ac89357ec3301", 18: "716b8da9b1a9cad4e828905b1432d565",
}


def tabela(caminho):
    """As tabelas do jogo tem 2 linhas de cabecalho; a 2a e a dos nomes."""
    linhas = open(caminho, encoding="utf-8").read().replace("\r", "").split("\n")
    cols = [c.strip() for c in linhas[1].split("\t")]
    idx = {c: i for i, c in enumerate(cols)}
    saida = []
    for l in linhas[2:]:
        r = l.split("\t")
        if len(r) < 3 or not r[0].strip():
            continue
        saida.append(r)
    return idx, saida


def campo(r, idx, nome, padrao=""):
    i = idx.get(nome, -1)
    return r[i].strip() if 0 <= i < len(r) else padrao


def num(s, padrao=0):
    try:
        return int(float(str(s).strip()))
    except Exception:
        return padrao


def aspas(s):
    s = (s or "").replace("\n", " ").replace("\r", " ").replace("\t", " ").strip()
    return "'" + s.replace("'", "''") + "'" if s else "''"


def limpo(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "") or "SemNome"


def guid(txt):
    return hashlib.md5(txt.encode()).hexdigest()


def escrever(caminho, corpo, g):
    open(caminho, "w", encoding="utf-8").write(corpo)
    open(caminho + ".meta", "w", encoding="utf-8").write(
        f"fileFormatVersion: 2\nguid: {g}\nNativeFormatImporter:\n"
        f"  externalObjects: {{}}\n  mainObjectFileID: 11400000\n"
        f"  userData: \n  assetBundleName: \n  assetBundleVariant: \n")


# ----------------------------------------------------------------- golpes
def gerar_golpes():
    idx, linhas = tabela(f"{RAIZ}/skill/Skill.txt")
    pasta = f"{DEST}/Golpes/Gerado"
    os.makedirs(pasta, exist_ok=True)

    porId, vistos, semTipo = {}, set(), 0
    for r in linhas:
        sid = campo(r, idx, "NewID")
        if not sid:
            continue
        en = campo(r, idx, "Name_EN") or campo(r, idx, "Name")
        nome_arq = f"g{sid}_{limpo(en)}"
        if nome_arq in vistos:
            continue
        vistos.add(nome_arq)

        tipo = TIPOS.get(num(campo(r, idx, "Type")), "")
        if not tipo:
            semTipo += 1

        dc = num(campo(r, idx, "DamageClass"), 2)
        poder = num(campo(r, idx, "Power"), 0)
        if poder < 0:
            poder = 0                       # -1 na tabela = golpe de status
        prec = num(campo(r, idx, "Accuracy"), 100)
        if prec < 0 or prec > 100:
            prec = 100                      # -1 = nunca erra
        alvo = {1: 0, 2: 1}.get(num(campo(r, idx, "Target"), 1), 0)

        corpo = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 0}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {GUID_GOLPE}, type: 3}}
  m_Name: {nome_arq}
  m_EditorClassIdentifier: NelOrd.Runtime::GolpeData
  id: {aspas(sid)}
  nomeExibicao: {aspas(campo(r, idx, 'Name_PT') or campo(r, idx, 'Name_EN') or en)}
  descricao: {aspas(campo(r, idx, 'Describe_PT') or campo(r, idx, 'Describe_EN') or campo(r, idx, 'Describe'))}
  tipo: {{fileID: 11400000, guid: {tipo}, type: 2}}
  atributoOfensivo: {1 if dc == 3 else 0}
  atributoDefensivo: {1 if dc == 3 else 0}
  poder: {poder}
  precisao: {prec}
  pp: {max(1, num(campo(r, idx, 'PP'), 15))}
  som: {{fileID: 0}}
  prioridade: {num(campo(r, idx, 'Priority'), 0)}
  caracteristicas: []
  efeitos: []
  regras: []
  alvo: {alvo}
  ignoraHabilidadeDefensiva: 0
  references:
    version: 2
    RefIds: []
"""
        escrever(f"{pasta}/{nome_arq}.asset", corpo, guid("omega-golpe:" + nome_arq))
        porId[sid] = (nome_arq, guid("omega-golpe:" + nome_arq))

    print(f"golpes: {len(porId)} gerados em {pasta}" +
          (f" ({semTipo} sem tipo reconhecido)" if semTipo else ""))
    return porId


# ------------------------------------------------------------ habilidades
def gerar_habilidades():
    idx, linhas = tabela(f"{RAIZ}/petability/PetAbility.txt")
    pasta = f"{DEST}/Habilidades/Gerado"
    os.makedirs(pasta, exist_ok=True)

    porId, vistos = {}, set()
    for r in linhas:
        hid = campo(r, idx, "ID")
        if not hid:
            continue
        en = campo(r, idx, "Name_EN") or campo(r, idx, "OriginName") or campo(r, idx, "Name")
        nome_arq = f"h{hid}_{limpo(en)}"
        if nome_arq in vistos:
            continue
        vistos.add(nome_arq)

        corpo = f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!114 &11400000
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: 0}}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {{fileID: 11500000, guid: {GUID_HABIL}, type: 3}}
  m_Name: {nome_arq}
  m_EditorClassIdentifier: NelOrd.Runtime::HabilidadeData
  id: {aspas(hid)}
  nomeExibicao: {aspas(campo(r, idx, 'Name_PT') or campo(r, idx, 'Name_EN') or en)}
  descricao: {aspas(campo(r, idx, 'Describe_PT') or campo(r, idx, 'Describe_EN') or campo(r, idx, 'Describe'))}
  regras: []
  gatilhos: []
  references:
    version: 2
    RefIds: []
"""
        escrever(f"{pasta}/{nome_arq}.asset", corpo, guid("omega-habil:" + nome_arq))
        porId[hid] = guid("omega-habil:" + nome_arq)

    print(f"habilidades: {len(porId)} geradas em {pasta}")
    return porId


if __name__ == "__main__":
    gerar_golpes()
    gerar_habilidades()
