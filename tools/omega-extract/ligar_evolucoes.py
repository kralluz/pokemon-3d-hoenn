"""Preenche as evolucoes das especies e conserta o id duplicado.

Duas coisas num script so porque as duas mexem no mesmo arquivo .asset.

1. ID UNICO. O gerador original usou PokeID como id, e as formas alternativas
   compartilham o numero da dex: Venusaur e VenusaurMega ficavam ambos com id
   '3'. No catalogo um sobrescreve o outro — foi o ValidadorDeCatalogoTests
   dele que pegou isso. Agora o id vem da coluna ID, que e unica por linha.

2. EVOLUCOES. A tabela PetEvolution diz, por especie, de QUEM ela evolui
   (FromSpecies). Invertendo, sabemos para onde cada uma vai.

   As condicoes sao [SerializeReference], entao o YAML usa rid + um bloco
   RefIds no fim do arquivo com a classe de cada condicao.

Do que a tabela oferece, so o nivel vira condicao. O porque de cada exclusao
esta no relatorio que o script imprime.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_golpes import RAIZ, DEST, tabela, campo, num, limpo

# rids precisam ser unicos dentro do arquivo; a faixa alta evita colidir com
# os que a Unity gera sozinha
RID_BASE = 7100000000000000000

MEGA = re.compile(r"(mega|primal|gmax|gigantamax)", re.I)


def padrao_oculta(linha, idxP):
    """Sequencia de True/False das habilidades da especie, na mesma ordem em que
    o gerador as escreve. Duas especies so podem ser ligadas por evolucao se a
    sequencia for igual."""
    ocultas = {x.strip() for x in re.split(r"[;,]", campo(linha, idxP, "HiddenAbility"))
               if x.strip() and x.strip() not in ("0", "-1")}
    saida, ja = [], set()
    for col in ("Ability", "HiddenAbility"):
        for parte in re.split(r"[;,]", campo(linha, idxP, col)):
            parte = parte.strip()
            if not parte or parte in ja:
                continue
            ja.add(parte)
            saida.append(parte in ocultas)
    return tuple(saida)


def main():
    idxP, linhasP = tabela(RAIZ + "/pet/Pet.txt")
    idxE, linhasE = tabela(RAIZ + "/petevolution/PetEvolution.txt")
    pasta = DEST + "/Especies/Gerado"

    # ID interno -> (nome do arquivo, nome em ingles)
    porID, vistos = {}, set()
    for r in linhasP:
        en = campo(r, idxP, "OriginName") or campo(r, idxP, "Name_EN")
        if not en:
            continue
        dex = num(campo(r, idxP, "PokeID") or campo(r, idxP, "ID"))
        arq = "p%04d_%s" % (dex, limpo(en))
        if arq in vistos:
            arq += "_" + campo(r, idxP, "ID")
        vistos.add(arq)
        porID[campo(r, idxP, "ID")] = (arq, en, r)

    guids = {}
    for pid, (arq, _, _linha) in porID.items():
        meta = "%s/%s.asset.meta" % (pasta, arq)
        if os.path.exists(meta):
            m = re.search(r"^guid: (\w+)", open(meta, encoding="utf-8").read(), re.M)
            if m:
                guids[pid] = m.group(1)

    # de quem evolui -> lista de (destino, nivel exigido, motivo de recusa)
    saidas = {}
    recusas = {"mega": [], "so_item": [], "habilidade": [], "sem_destino": [], "sem_origem": []}

    for r in linhasE:
        eu = campo(r, idxE, "ID")
        de = campo(r, idxE, "FromSpecies")
        if de in ("", "0", "-1"):
            continue                                   # forma base, nao evolui de ninguem
        if eu not in porID:
            recusas["sem_destino"].append(eu)
            continue
        if de not in porID:
            recusas["sem_origem"].append(de)
            continue

        nome_destino = porID[eu][1]
        # Mega/Primal nao sao evolucao neste projeto: sao TROCA DE FORMA, e o
        # jogo tem sistema proprio para isso. Virar Evolucao faria o Pokemon
        # megaevoluir de vez, sem voltar.
        if MEGA.search(porID[eu][0]) or MEGA.search(nome_destino):
            recusas["mega"].append(f"{porID[de][1]} -> {nome_destino}")
            continue

        # O projeto exige que o slot de habilidade nao troque de comum para
        # oculta ao evoluir: senao o individuo e promovido ou rebaixado so por
        # subir de nivel. Onde a tabela do APK discorda, tiramos a ligacao em
        # vez de inventar um padrao.
        if padrao_oculta(porID[de][2], idxP) != padrao_oculta(porID[eu][2], idxP):
            recusas["habilidade"].append(f"{porID[de][1]} -> {nome_destino}")
            continue

        nivel = num(campo(r, idxE, "NeedLv"), 0)
        if nivel <= 0:
            # so exige material do gacha; sem nivel nao ha condicao que este
            # projeto saiba representar
            recusas["so_item"].append(f"{porID[de][1]} -> {nome_destino}")
            continue

        saidas.setdefault(de, []).append((eu, nivel))

    # ------------------------------------------------------ escrever nos assets
    comEvolucao = idsCorrigidos = total = 0

    for pid, (arq, _, _linha) in porID.items():
        caminho = "%s/%s.asset" % (pasta, arq)
        if not os.path.exists(caminho):
            continue
        s = open(caminho, encoding="utf-8").read()

        # 1. id unico
        novo = "  id: '%s'" % pid
        s2 = re.sub(r"^  id: .*$", novo, s, count=1, flags=re.M)
        if s2 != s:
            idsCorrigidos += 1
        s = s2

        # 2. evolucoes
        destinos = [(d, n) for d, n in saidas.get(pid, []) if d in guids]
        if destinos:
            evo, refs = [], []
            for k, (destino, nivel) in enumerate(destinos):
                rid = RID_BASE + k
                evo.append("  - destino: {fileID: 11400000, guid: %s, type: 2}" % guids[destino])
                evo.append("    condicoes:")
                evo.append("    - rid: %d" % rid)
                evo.append("    peso: 1")
                refs.append("    - rid: %d" % rid)
                refs.append("      type: {class: ExigeNivel, ns: , asm: NelOrd.Runtime}")
                refs.append("      data:")
                refs.append("        minimo: %d" % nivel)
            bloco_evo = "\n" + "\n".join(evo)
            bloco_ref = "\n" + "\n".join(refs)
            comEvolucao += 1
            total += len(destinos)
        else:
            bloco_evo = " []"
            bloco_ref = " []"

        s = re.sub(r"^  evolucoes:.*?(?=^  [a-zA-Z]|\Z)",
                   "  evolucoes:" + bloco_evo + "\n", s, count=1, flags=re.M | re.S)
        # O gerador original nunca escreveu bloco 'references' — com
        # 'evolucoes: []' ele nao fazia falta. Com condicoes por rid ele passa a
        # ser obrigatorio: sem ele a Unity le a condicao como nula, em silencio.
        s = re.sub(r"^  references:.*?(?=\Z)", "", s, count=1, flags=re.M | re.S)
        s = s.rstrip() + "\n  references:\n    version: 2\n    RefIds:" + bloco_ref + "\n"
        open(caminho, "w", encoding="utf-8").write(s)

    print("ids corrigidos para valor unico: %d" % idsCorrigidos)
    print("especies com evolucao: %d (%d ligacoes)" % (comEvolucao, total))
    print()
    print("NAO mapeado:")
    print("  %4d mega/primal — sao troca de forma neste projeto, nao evolucao"
          % len(recusas["mega"]))
    print("  %4d so exigem material de loja, sem nivel — e mecanica que o projeto nao quer"
          % len(recusas["so_item"]))
    print("  %4d o slot de habilidade mudaria de comum para oculta ao evoluir"
          % len(recusas["habilidade"]))
    for k in ("sem_destino", "sem_origem"):
        if recusas[k]:
            print("  %4d %s (linha aponta para especie que nao existe)" % (len(recusas[k]), k))
    print()
    print("  exemplos de 'so material':", ", ".join(recusas["so_item"][:6]))
    print("  exemplos de mega:", ", ".join(recusas["mega"][:4]))


if __name__ == "__main__":
    main()
