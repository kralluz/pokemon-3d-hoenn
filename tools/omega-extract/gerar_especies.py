"""Gera EspecieData (.asset + .meta) do Nel-Ord a partir do Pet.txt extraido.

Escreve o YAML direto, sem abrir o Unity: e a via mais rapida para 1331 itens.
O formato foi copiado de um asset feito a mao pelo proprio projeto.
"""
import hashlib, os, sys

TSV  = "apk/_extracted/out/assets/TextAsset/config/pet/Pet.txt"
SAIDA = "nel-ord/Assets/Data/Especies/Gerado"
GUID_SCRIPT = "50670ded453b8444c8f55c8fe6789f19"      # EspecieData.cs

# id do tipo no jogo -> GUID do TipoData ja existente no projeto dele
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

def guid(txt):
    return hashlib.md5(("omega-especie:" + txt).encode()).hexdigest()

def aspas(s):
    s = (s or "").replace("\n", " ").replace("\r", " ").strip()
    return "'" + s.replace("'", "''") + "'" if s else "''"

def num(s, padrao=0.0):
    try: return float(str(s).strip())
    except Exception: return padrao

def ref(g):
    return "{fileID: 0}" if not g else f"{{fileID: 11400000, guid: {g}, type: 2}}"

def main():
    linhas = open(TSV, encoding="utf-8").read().split("\n")
    cols = [c.strip() for c in linhas[1].split("\t")]
    idx = {c: i for i, c in enumerate(cols)}
    def campo(r, nome, padrao=""):
        i = idx.get(nome, -1)
        return r[i].strip() if 0 <= i < len(r) else padrao

    os.makedirs(SAIDA, exist_ok=True)
    vistos = set()
    n = semTipo = 0
    for l in linhas[2:]:
        r = l.split("\t")
        if len(r) < 20 or not r[0].strip():
            continue

        eng = campo(r, "OriginName") or campo(r, "Name_EN")
        if not eng:
            continue
        dex = campo(r, "PokeID") or campo(r, "ID")
        nome_arq = f"p{int(num(dex)):04d}_{''.join(c for c in eng if c.isalnum())}"
        # formas alternativas (mega, regionais) repetem dex+OriginName; sem
        # desempate um arquivo sobrescreve o outro e a forma some.
        if nome_arq in vistos:
            nome_arq += "_" + campo(r, "ID")
        vistos.add(nome_arq)

        tipos = [int(num(t)) for t in campo(r, "Type").split(";") if t.strip()]
        t1 = TIPOS.get(tipos[0] if tipos else 0, "")
        t2 = TIPOS.get(tipos[1], "") if len(tipos) > 1 and tipos[1] != tipos[0] else ""
        if not t1:
            semTipo += 1

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
  m_Script: {{fileID: 11500000, guid: {GUID_SCRIPT}, type: 3}}
  m_Name: {nome_arq}
  m_EditorClassIdentifier: Assembly-CSharp::EspecieData
  id: {aspas(dex)}
  nomeExibicao: {aspas(campo(r, "Name_PT") or campo(r, "Name_EN") or eng)}
  sprite: {{fileID: 0}}
  descricao: {aspas(campo(r, "PetDexIntro_PT") or campo(r, "PetDexIntro_EN"))}
  categoria: {aspas(campo(r, "JLType_PT") or campo(r, "JLType_EN") or "Pokemon")}
  alturaMetros: {num(campo(r, "Height"), 0.7)}
  pesoKg: {num(campo(r, "Weight"), 6.9)}
  habitat: ''
  tipoPrimario: {ref(t1)}
  tipoSecundario: {ref(t2)}
  hpBase: {int(num(campo(r, "HP"), 45))}
  ataqueBase: {int(num(campo(r, "Attack"), 49))}
  defesaBase: {int(num(campo(r, "Defense"), 49))}
  ataqueEspecialBase: {int(num(campo(r, "SpecialAttack"), 65))}
  defesaEspecialBase: {int(num(campo(r, "SpecialDefense"), 65))}
  velocidadeBase: {int(num(campo(r, "Speed"), 45))}
  habilidades: []
  xpBase: {int(num(campo(r, "BaseExp"), 64))}
  taxaCaptura: {int(num(campo(r, "CatchRate"), 45))}
  evConcedido: 0
  quantidadeDeEv: 0
  golpes: []
  evolucoes: []
"""
        g = guid(nome_arq)
        open(f"{SAIDA}/{nome_arq}.asset", "w", encoding="utf-8").write(corpo)
        open(f"{SAIDA}/{nome_arq}.asset.meta", "w", encoding="utf-8").write(
            f"fileFormatVersion: 2\nguid: {g}\nNativeFormatImporter:\n"
            f"  externalObjects: {{}}\n  mainObjectFileID: 11400000\n"
            f"  userData: \n  assetBundleName: \n  assetBundleVariant: \n")
        n += 1

    print(f"especies geradas: {n}  (sem tipo reconhecido: {semTipo})")
    print(f"destino: {SAIDA}")

if __name__ == "__main__":
    main()
