# Batalha — protótipo jogável

`battle.html` fecha o ciclo: escolhe dois Pokémon, cada um entra com um
moveset de Gen 3 real e legal, e a luta roda de verdade — dano, tipo,
prioridade, status, tudo calculado pelo motor da comunidade competitiva, não
por uma fórmula inventada. Continua sendo HTML/CSS/JS puro, sem servidor de
aplicação.

## Rodar

Com `python tools/serve.py` no ar: `http://localhost:8080/viewer/battle.html`
(tem link no topo da Pokédex e "← Pokédex 3D" aqui para voltar).

Escolhe um Pokémon pra cada lado (busca por nome/número/tipo, ou "🎲 sortear
os dois"), clica **Lutar!**. Na tela de batalha, clica um dos 4 golpes — o
oponente responde sozinho (IA simples: golpe legal aleatório).

## O motor: `@pkmn/sim` rodando no navegador

[@pkmn/sim](https://github.com/pkmn/ps) é a extração oficial, mantida pela
mesma equipe do [Pokémon Showdown](https://github.com/smogon/pokemon-showdown),
licença MIT. Resolve dano, STAB, efetividade de tipo, crítico, prioridade,
status, habilidades — a simulação completa de Gen 3.

O pacote é feito pra Node, então precisou de um passo a mais: **[esbuild](https://esbuild.github.io/)
empacota `BattleStreams`/`Teams`/`Dex` num único arquivo ESM** que roda direto
no navegador, sem nenhum servidor por trás. Confirmado rodando batalhas
completas em ~1,5s (bundle + partida) em Chrome headless.

```bash
node_modules/.bin/esbuild tools/pkmn_bundle_src/entry.js \
  --bundle --format=esm --platform=browser --target=es2020 --minify \
  --outfile=viewer/vendor/pkmn/sim.js
```

Rode de novo se o `@pkmn/sim` for atualizado (`viewer/vendor/pkmn/sim.js`,
6,6 MB minificado, já está no lugar — não precisa gerar de novo pra usar).

## Como o time é montado

Cada Pokémon entra **nível 50, IVs perfeitos**, com até 4 golpes escolhidos
do **learnset real de Gen 3** da própria espécie — nunca um golpe inventado:

1. Busca o learnset via `Dex.forGen(3).learnsets.get(id)`
2. Filtra só fontes que começam com `3` (`3L` level-up, `3M` TM/HM, `3T`
   tutor, `3S` evento) — moves que a espécie aprende *nela mesma* em Gen 3,
   sem depender de herança de pré-evolução (evita todo o histórico complexo
   de legalidade entre gerações)
3. Prioriza: até 2 golpes de dano do próprio tipo (STAB), depois cobertura,
   depois status, até fechar 4 — ou menos, se o learnset for curto
4. Natureza e EVs seguem o maior entre Ataque/Ataque Especial (252 no
   atacante, 252 em Velocidade, 4 em HP); habilidade é a primeira da espécie

Testado nos dois extremos do elenco: **Silcoon** (só tem `Harden`, zero
golpes de dano) e **Beldum** (só tem `Take Down`) batalham normalmente até o
fim, sem travar — o motor força `Struggle` sozinho quando não sobra PP.

## O que é real e o que é simplificação

| | |
|---|---|
| Dano, tipo, status, prioridade, crítico | ✅ motor de verdade, Gen 3 completo |
| Movesets | ✅ legais, vindos do learnset real |
| HP, log de batalha | ✅ números exatos dos dois lados (stream `omniscient`) |
| Format | `gen3customgame` — sem clause de tier, qualquer combinação passa |
| Itens | ❌ nenhum time carrega item |
| Trocar de Pokémon | ❌ é 1x1, sem banco — desmaiou, acabou |
| IA do oponente | golpe legal aleatório, sem estratégia |

## Arquivos

| | |
|---|---|
| `battle.html` / `battle.css` / `battle.js` | a página |
| `vendor/pkmn/sim.js` | `@pkmn/sim` empacotado pro navegador |
| `tools/pkmn_bundle_src/entry.js` | fonte do bundle acima |

## Testes

```bash
node tools/shoot_battle.mjs <url> <pasta>              # sorteia 2, joga ate o fim
node tools/shoot_battle_specific.mjs <url> Nome1 Nome2  # forca um confronto especifico
node tools/repro_stall.mjs <url>                        # roda ate 12 partidas sorteadas seguidas
```

Todos rodam a batalha inteira em Chrome headless clicando golpes de verdade,
e conferem que o HP mudou, o log encheu e o banner de vencedor apareceu — não
só que a página carregou sem erro. Foi o `repro_stall.mjs` que pegou o bug real
do empate (dois Pokémon desmaiando no mesmo turno, ex.: golpe final sendo
`Explosion`) — o protocolo manda `|tie|` em vez de `|win|`, e faltava esse
`case` no parser do log.
