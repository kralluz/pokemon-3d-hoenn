# Pokémon 3D — protótipo (Hoenn / Gen 3)

Protótipo de jogo estilo Pokémon em 3D: visualizador de modelos, mundo aberto
andável e motor de batalha fiel à Gen 3 — rodando em três frentes em paralelo
(web/JS e C#/.NET), migrando para Unity.

## O que tem aqui

| pasta | o quê |
|---|---|
| [`viewer/`](viewer/) | Pokédex 3D, mundo aberto (Kenney CC0) e batalha jogável — HTML/CSS/JS puro, three.js |
| [`csharp/`](csharp/) | Porte do motor de batalha Gen 3 pra C#, validado 1:1 contra o `@smogon/calc` |
| [`tools/`](tools/) | scripts de download de asset, build, teste automatizado (Puppeteer) e utilidades |
| [`assets/`](assets/) | modelos 3D — ver nota de licença abaixo |
| `unity/` | projeto Unity (em andamento) |

## Rodar

```bash
npm install
python tools/serve.py            # viewer web em http://localhost:8080/viewer/

cd csharp/BattleSim
dotnet run -- battle Blaziken Swampert   # motor de batalha em C#, terminal puro
```

Documentação detalhada de cada parte: [`viewer/README.md`](viewer/README.md),
[`viewer/WORLD.md`](viewer/WORLD.md), [`viewer/BATTLE.md`](viewer/BATTLE.md),
[`csharp/README.md`](csharp/README.md), [`INGREDIENTES.md`](INGREDIENTES.md)
(inventário do que falta pra virar um jogo completo).

## Licenças e o que NÃO está neste repositório

- **Kenney Nature Kit e Animated Characters** (`assets/environment/`,
  `assets/character/`) — CC0, uso comercial liberado, incluídos aqui.
- **Dados de jogo** (`csharp/BattleSim/data/*.json`, `viewer/models.json`) —
  stats, tipos e movesets vêm da [PokeAPI](https://pokeapi.co) (BSD-3) e do
  [`@pkmn/sim`](https://github.com/pkmn/ps) (MIT). Fatos de jogo, não expressão
  criativa protegida.
- **Modelos de Pokémon** (`assets/gen3/`, `assets/gen3_glb/`) — **propositalmente
  fora deste repositório** (`.gitignore`). São datamine do Pokémon GO,
  © Niantic / Nintendo / Creatures / GAME FREAK, sem licença de redistribuição
  pública. Ficam só na cópia local, pra estudo e protótipo pessoal — não pra
  publicação. Instruções de como baixar de novo: `tools/fetch_gen3.py` e
  `tools/fetch_gen3_glb.py`.
- **Motor de batalha** — lógica em [`csharp/`](csharp/) é código próprio
  (validado contra dados públicos de dano, não copiado de nenhum jogo).

Em resumo: código e dados de jogo são livres pra usar; os modelos 3D dos
Pokémon precisam ser baixados à parte por quem for rodar isso localmente.
