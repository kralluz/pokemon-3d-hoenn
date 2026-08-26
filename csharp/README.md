# Motor de batalha Gen 3 em C#

Porte do motor de batalha para C#, pré-requisito da migração pro Unity. Roda em
terminal puro (`dotnet run`), sem Unity — o Editor só entra quando for plugar
isso num jogo visual.

## Rodar

```bash
cd csharp/BattleSim
dotnet build
./bin/Debug/net9.0/BattleSim.exe battle Blaziken Swampert
```

Sem argumentos usa Blaziken vs Swampert. Ciclo rápido: `dotnet watch run`
recompila a cada salvar, igual `node --watch`.

## Por que não usamos uma biblioteca pronta

Avaliei o [Kermalis/PokemonBattleEngine](https://github.com/Kermalis/PokemonBattleEngine)
(MIT, C#, biblioteca standalone). Descartado por medição, não por preferência:
os arquivos `To Do` dele listam **142 golpes, 49 habilidades e 112 itens não
implementados**. Cruzando com o learnset real do nosso elenco de Hoenn,
**23% dos golpes que nossos Pokémon aprendem não existem lá** — incluindo Focus
Punch, Solar Beam, Hyper Beam e Counter, que aparecem nos movesets que o próprio
protótipo gera. Também é mecânica de Gen 5, não Gen 3.

O `AJ2O/pbs-unity` foi descartado por não ter licença explícita e estar parado
desde 2020.

## Os dados não são digitados a mão

`tools/export_gen3_data.mjs` exporta do `@pkmn/sim` para
[`BattleSim/data/`](BattleSim/data/): 135 espécies (stats, tipos, learnset
legal de Gen 3), 300 golpes, tabela de tipos e naturezas. Rode de novo se quiser
atualizar:

```bash
node tools/export_gen3_data.mjs
```

Isso mantém a fonte da verdade única entre o protótipo JS e o motor C#.

## Fidelidade — 4000/4000 casos idênticos

`tools/validate_csharp_engine.mjs` gera confrontos aleatórios, roda o motor C# e
compara a faixa de dano (rolls 85 e 100) com o
[`@smogon/calc`](https://github.com/smogon/damage-calc) — o calculador oficial da
comunidade competitiva.

```bash
node tools/validate_csharp_engine.mjs 4000
```

**Resultado atual: 4000/4000 faixas idênticas, 0 divergências de HP.**

Chegar nisso exigiu acertar quatro detalhes que "quase certo" não cobre:

1. **Ordem das etapas.** A Gen 3 trunca a cada etapa, então a ordem muda o
   resultado. A ordem correta é: dano base → queimadura → `+2` → crítico →
   STAB → tipo → aleatório. Eu tinha o aleatório antes do STAB/tipo; dava ±1.
2. **Queimadura corta o dano base, não o stat de Ataque.** Truncam em pontos
   diferentes.
3. **Os dois tipos entram separados, truncando entre um e outro** — não como um
   multiplicador combinado. Com 2× e 0,5×, combinar dá 1× exato, mas o jogo
   perde o bit ímpar no meio.
4. **A ordem dos dois tipos é canônica, não a declarada pela espécie.** O jogo
   tem uma lista fixa (`TypePrecedence` em `Engine.cs`); aplicar Água antes de
   Terrestre ou o contrário muda o resultado quando trunca.

Cada um desses valia ±1 de dano — o suficiente pra mudar se um golpe mata ou não.

## O que está implementado

| | |
|---|---|
| Fórmula de dano Gen 3 | ✅ validada 1:1 |
| Stats (HP, natureza, IV/EV) | ✅ validada 1:1 |
| Tabela de tipos, STAB, imunidade | ✅ |
| Categoria física/especial **por tipo** (regra da Gen 3) | ✅ |
| Crítico (estágios 1/16…1/2, ignora boosts adversos) | ✅ |
| Estágios de stat, precisão/evasão (tabela própria) | ✅ |
| Status: brn, par, psn, tox, slp, frz + dano de fim de turno | ✅ |
| Ordem de turno (prioridade, velocidade, paralisia ÷4) | ✅ |
| Recoil, drain, multi-hit, efeitos secundários | ✅ |
| Explosion/Self-Destruct cortando Defesa (regra Gen 3) | ✅ |

## O que falta

- **Habilidades** — nenhuma implementada. Pure Power, Thick Fat, Levitate,
  Wonder Guard etc. mudam dano de verdade. A validação neutraliza a habilidade
  dos dois lados justamente para isolar a fórmula; ativá-las é o próximo passo.
- **Itens** — nenhum.
- **60 dos 300 golpes (20%) têm lógica própria** que vive em JS e não foi
  portada: Counter, Solar Beam (2 turnos), Focus Punch, Bide, Rollout... Estão
  marcados com `hasCallback: true` no `moves.json` e hoje o motor os trata como
  dano simples. A validação pula esses — o número de 100% cobre os 136 golpes
  de dano direto.
- **Clima, Reflect/Light Screen, batalha dupla, troca de Pokémon.**

## Arquivos

| | |
|---|---|
| `BattleSim/Data.cs` | modelos e carregamento do JSON exportado |
| `BattleSim/Engine.cs` | stats, dano, status, turno |
| `BattleSim/Program.cs` | modo `battle` (demo) e modo `calc` (validação) |
| `BattleSim/data/` | dados exportados do `@pkmn/sim` |
