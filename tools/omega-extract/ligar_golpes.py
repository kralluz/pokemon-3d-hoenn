"""Liga golpes e habilidades ja gerados nas 1331 especies.

Separado do gerar_golpes.py de proposito: gerar os assets e liga-los sao passos
independentes, e este pode rodar de novo sozinho quando o formato mudar.

Os blocos sao trocados INTEIROS (chave + tudo indentado abaixo), nao so a
primeira linha: uma rodada anterior com formato errado deixava entradas orfas
logo abaixo da chave, e o YAML virava lixo silencioso.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_golpes import RAIZ, DEST, tabela, campo, num, limpo, gerar_golpes, gerar_habilidades


def bloco_habilidades(refs):
    """HabilidadeDaEspecie tem habilidade/peso/oculta — nao e referencia solta.
    A oculta segue a convencao do projeto: peso 0.1."""
    if not refs:
        return " []"
    linhas = []
    for g, oculta in refs:
        linhas.append("  - habilidade: {fileID: 11400000, guid: %s, type: 2}" % g)
        linhas.append("    peso: %s" % ("0.1" if oculta else "1"))
        linhas.append("    oculta: %d" % (1 if oculta else 0))
    return "\n" + "\n".join(linhas)


def bloco_golpes(pares):
    if not pares:
        return " []"
    linhas = []
    for nivel, g in pares:
        linhas.append("  - nivel: %d" % nivel)
        linhas.append("    golpe: {fileID: 11400000, guid: %s, type: 2}" % g)
    return "\n" + "\n".join(linhas)


def trocar_bloco(texto, chave, valor):
    """Troca a chave e tudo indentado abaixo dela, ate a proxima chave de mesmo
    nivel (dois espacos) ou o fim do arquivo."""
    padrao = r"^  " + chave + r":.*?(?=^  [a-zA-Z]|\Z)"
    return re.sub(padrao, "  " + chave + ":" + valor + "\n", texto,
                  count=1, flags=re.M | re.S)


def ligar(golpes, habilidades):
    idx, linhas = tabela(RAIZ + "/pet/Pet.txt")
    pasta = DEST + "/Especies/Gerado"

    porArquivo, vistos = {}, set()
    for r in linhas:
        en = campo(r, idx, "OriginName") or campo(r, idx, "Name_EN")
        if not en:
            continue
        dex = num(campo(r, idx, "PokeID") or campo(r, idx, "ID"))
        nome = "p%04d_%s" % (dex, limpo(en))
        if nome in vistos:
            nome += "_" + campo(r, idx, "ID")
        vistos.add(nome)
        porArquivo[nome] = r

    ligados = semGolpe = totalGolpes = totalHabil = 0

    for nome, r in porArquivo.items():
        caminho = "%s/%s.asset" % (pasta, nome)
        if not os.path.exists(caminho):
            continue

        # A coluna Ability ja CONTEM a oculta (Charizard: Ability='2;34',
        # Hidden='34'). Ler Ability primeiro e deduplicar perdia a marcacao,
        # entao descobrimos o conjunto das ocultas antes de montar a lista.
        ocultas = {x.strip() for x in re.split(r"[;,]", campo(r, idx, "HiddenAbility"))
                   if x.strip() and x.strip() not in ("0", "-1")}

        refs, jaVi = [], set()
        for col in ("Ability", "HiddenAbility"):
            for parte in re.split(r"[;,]", campo(r, idx, col)):
                parte = parte.strip()
                if not parte or parte not in habilidades or parte in jaVi:
                    continue
                jaVi.add(parte)
                refs.append((habilidades[parte], parte in ocultas))

        # InitSkill no nivel 1, depois os pares nivel/golpe. Sem dedupe o mesmo
        # golpe entra duas vezes quando e inicial E aparece na lista por nivel.
        pares, jaTem = [], set()
        for sid in re.split(r"[;,]", campo(r, idx, "InitSkill")):
            sid = sid.strip()
            if sid in golpes and sid not in jaTem:
                jaTem.add(sid)
                pares.append((1, golpes[sid][1]))

        niveis = [x for x in re.split(r"[;,]", campo(r, idx, "LearnSkillLv")) if x.strip()]
        ids = [x for x in re.split(r"[;,]", campo(r, idx, "LearnSkillId")) if x.strip()]
        for nivel, sid in zip(niveis, ids):
            sid = sid.strip()
            if sid in golpes and sid not in jaTem:
                jaTem.add(sid)
                pares.append((num(nivel, 1), golpes[sid][1]))
        pares.sort(key=lambda x: x[0])

        if not pares:
            semGolpe += 1

        s = open(caminho, encoding="utf-8").read()
        s = trocar_bloco(s, "habilidades", bloco_habilidades(refs))
        s = trocar_bloco(s, "golpes", bloco_golpes(pares))
        open(caminho, "w", encoding="utf-8").write(s)

        ligados += 1
        totalGolpes += len(pares)
        totalHabil += len(refs)

    print("especies ligadas: %d" % ligados)
    print("  golpes atribuidos: %d (media %.1f por especie)"
          % (totalGolpes, totalGolpes / max(ligados, 1)))
    print("  habilidades atribuidas: %d (media %.1f)"
          % (totalHabil, totalHabil / max(ligados, 1)))
    if semGolpe:
        print("  sem nenhum golpe: %d" % semGolpe)


if __name__ == "__main__":
    ligar(gerar_golpes(), gerar_habilidades())
