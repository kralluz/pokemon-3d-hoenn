# Ingredientes para o jogo

Levantamento do que existe pronto, do que dá pra baixar de graça e do que vai
ter que ser feito. Números conferidos, não chutados.

Legenda: ✅ já está no projeto · 🟢 é só baixar · 🟡 existe pela metade · 🔴 tem que fazer

---

## 1. Modelos de Pokémon

| | |
|---|---|
| status | ✅ |
| onde | [assets/gen3/](assets/gen3/) (FBX) e [assets/gen3_glb/](assets/gen3_glb/) (GLB) |
| o que tem | 135 espécies + variantes. FBX com malha densa, esqueleto e skinning. GLB leve com material já separado |

Fonte: [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets) e
[Pokemon-3D-api/assets](https://github.com/Pokemon-3D-api/assets).

## 2. Animações dos Pokémon

| | |
|---|---|
| status | 🔴 **este é o buraco principal** |
| o que tem | 8 GLB com set completo (253, 271, 302, 330, 341, 348, 353, 386) + bundles Unity de 18 espécies |
| o que falta | os outros ~120 |

Três caminhos, do mais barato ao mais caro:

1. **Clipes genéricos retargetados** — animar idle/andar/correr/ataque/dano uma vez
   por tipo de corpo (bípede, quadrúpede, serpente, flutuante, inseto) e aplicar nos
   rigs FBX. Cobre os 135 com ~5 sets. Não fica no nível oficial, mas fica jogável.
2. **Bundles Unity do PokeMiners** — keyframes reais, ~15 clipes por bicho, mas só
   18 espécies da Gen 3. Serve pra validar o pipeline rápido.
3. **Rip de ORAS / X-Y (3DS)** — única fonte com os 135 completos e animados.
   Ferramentas: [Ohana3DS](https://github.com/dnasdw/Ohana3DS),
   [pokemon-3ds-model-loader](https://github.com/dragonation/pokemon-3ds-model-loader).
   Precisa da ROM.

## 3. Treinadores, NPCs e jogador

| | |
|---|---|
| status | 🟢 |
| onde | `PokeMiners/pogo_assets` → `3D Assets/Characters` |
| o que tem | **29 FBX riggados, 100 MB** — avatar masculino e feminino, Blanche, Candela, Professor Willow, Giovanni, Jessie, James, grunts e executivos da Rocket |
| bônus | `3D Assets/Clothing` — **850 peças de roupa, 219 MB** para customização de avatar |

Mesma pegadinha dos Pokémon: riggados, sem keyframes.

## 4. Mapa e cenário

| | |
|---|---|
| status | 🔴 |
| o que falta | tudo — terreno, prédios, árvores, água, interiores |

Não existe rip aproveitável: Gen 3 original é 2D em tiles, e Pokémon GO usa mapa
procedural do OpenStreetMap. Caminhos:

- **Packs CC0 prontos** — [Kenney Nature Kit](https://kenney.nl/assets/nature-kit)
  (330 modelos), [Quaternius](https://quaternius.com/),
  [KayKit](https://kaylousberg.itch.io/). Tudo CC0, uso comercial liberado, estilo
  low-poly que combina bem com esses modelos.
- **Layout das cidades e rotas de Hoenn** — o decomp
  [pret/pokeemerald](https://github.com/pret/pokeemerald) tem os dados de mapa
  originais. Serve de planta baixa pra reconstruir em 3D.

## 5. Sons

| | |
|---|---|
| status | 🟢 efeitos · 🔴 música |

| o que | quantos | onde |
|---|---|---|
| Cries dos Pokémon | 1.967 arquivos, 62 MB | PokeMiners `Sounds/Pokemon Cries` |
| Cries (alternativa) | .ogg por dex | [PokeAPI cries](https://github.com/PokeAPI/cries) — campo `cries` na API |
| Sons de ataque | 346 arquivos, 22 MB | PokeMiners `Sounds/Pokemon Moves` |
| Sons de combate | 12 arquivos | PokeMiners `Sounds/Combat` |
| Sons de menu/UI | 49 arquivos | PokeMiners `Sounds/Menu Sounds` |
| **Trilha sonora** | — | 🔴 não tem fonte livre. Compor, encomendar, ou pack royalty-free |

## 6. Itens

| | |
|---|---|
| status | 🟢 |

- **3D**: PokeMiners `3D Assets/Items` — 34 FBX (Pokébola, Great, Ultra, Master,
  Premier, berries, caixas)
- **Ícones 2D**: PokeMiners `Images/Items` (164 arquivos) e
  [msikma/pokesprite](https://github.com/msikma/pokesprite) (MIT) — sprites de
  inventário de todos os itens dos jogos principais
- **Dados**: PokeAPI — **2.223 itens** com efeito, categoria, preço

## 7. Ataques e efeitos visuais

| | |
|---|---|
| status | 🟡 |

- **Dados dos 937 movimentos**: PokeAPI e Showdown — poder, precisão, PP, tipo,
  categoria, efeito secundário, prioridade
- **Sprites de efeito**: PokeMiners `Images/Effects` (228) e `Images/Combat` (73)
- **Partículas 3D**: 🔴 não tem rip aproveitável. Faz no sistema de partículas da
  engine ou usa pack VFX pronto

## 8. Estatísticas e dados

| | |
|---|---|
| status | 🟢 **esta camada está completa e é de graça** |

| fonte | licença | o que tem |
|---|---|---|
| [PokeAPI](https://pokeapi.co/) | BSD-3 | 937 movimentos, 373 habilidades, 2.223 itens, 25 naturezas, 68 berries, 2.372 TMs, 1.104 locais, stats/tipos/learnsets/evoluções |
| [veekun/pokedex](https://github.com/veekun/pokedex) | MIT | os mesmos dados em CSV, offline, sem depender de API |
| [smogon/pokemon-showdown](https://github.com/smogon/pokemon-showdown) | MIT | `data/` com stats, movimentos, habilidades já em TypeScript |

Isso normalmente são semanas de digitação. Está pronto.

## 9. Algoritmo de batalha

| | |
|---|---|
| status | 🟢 **você acertou, está pronto** |

| projeto | licença | pra quê |
|---|---|---|
| [smogon/pokemon-showdown](https://github.com/smogon/pokemon-showdown) | MIT | simulador completo, todas as gerações, 5,8k ★. É a referência que a comunidade competitiva usa — dano, prioridade, status, clima, terreno, habilidades, itens |
| [pkmn/engine](https://github.com/pkmn/engine) | MIT | motor minimalista e rápido, feito pra rodar milhões de batalhas. Bom se performance importar |
| [pkmn/ps](https://github.com/pkmn/ps) | MIT | Showdown modularizado — dá pra usar só a parte que interessa |
| [pret/pokeemerald](https://github.com/pret/pokeemerald) | sem licença ⚠️ | decompilação do Emerald. Consulta pra mecânica exata da Gen 3, mas é código da Nintendo — **não copie, use só pra entender** |

## 10. UI e fontes

| | |
|---|---|
| status | 🟡 |
| o que tem | PokeMiners `Images` — **18.738 arquivos, 1,4 GB** de UI: badges, botões, fundos, ícones, telas |
| ressalva | é UI do Pokémon GO, layout de mobile. Serve de referência e de peça solta, não como interface pronta pro seu jogo |

## 11. A engine e o jogo

| | |
|---|---|
| status | 🔴 |

Sistema de batalha ligando os dados, captura, party, mochila, save, diálogo,
câmera, controles, transições. O Showdown resolve a **matemática** da batalha,
não o jogo em volta dela.

---

## Resumo

| ingrediente | status |
|---|---|
| Modelos de Pokémon | ✅ |
| Dados (stats, moves, itens) | 🟢 completo |
| Algoritmo de batalha | 🟢 pronto, MIT |
| Sons e cries | 🟢 |
| Itens | 🟢 |
| Treinadores e NPCs | 🟢 |
| Efeitos de ataque | 🟡 dados sim, VFX 3D não |
| UI | 🟡 peças sim, interface não |
| **Animações** | 🔴 gargalo |
| **Mapa e cenário** | 🔴 |
| **Trilha sonora** | 🔴 |
| **O jogo em si** | 🔴 |

Os dois primeiros buracos vermelhos são os que travam um protótipo jogável:
**animação** e **mapa**. Os outros dois são de acabamento e de programação, não
de asset.

---

## Aviso de licença

Tudo que vem do PokeMiners é datamine do Pokémon GO — © Niantic / Nintendo /
Creatures / GAME FREAK, sem licença de redistribuição. Serve para protótipo,
estudo e portfólio pessoal. **Não dá para publicar comercialmente.**

O que é limpo para uso comercial: PokeAPI (BSD-3), veekun/pokedex (MIT),
pokemon-showdown (MIT), pkmn/engine (MIT), pokesprite (MIT), Kenney / Quaternius
/ KayKit (CC0). Ou seja: o **código e os dados** são livres; o que prende é a
**arte**. Se um dia o projeto for para a loja, a troca é dos modelos e sons —
o pipeline e a lógica ficam.
