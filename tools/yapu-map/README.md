# Recriação dos mapas 2D da demo YAPU

Converte as cenas ripadas em `YAPU_Demo/Ripped/ExportedProject/` num mapa que o projeto
Unity em `unity/Unity/` monta sozinho: tilemaps por camada, sprites recortados e a grade
de colisão.

## A ideia central

As cenas ripadas guardam, **por célula**, o sprite que a rule tile já resolveu
(`m_TileSpriteIndex` aponta para `m_TileSpriteArray`). Ou seja, o resultado das regras de
vizinhança vem assado do build original — não é preciso reimplementar `RuleTile` nenhuma,
nem depender dos 2.244 assets de RuleTile que o AssetRipper exportou vazios.

A colisão sai do `TileData.json`, o dicionário global `tile -> TileType` que só o decoder
em `tools/yapu-extract/` conseguiu recuperar (é um dos 1.033 ScriptableObjects que o
AssetRipper esvaziou).

## Etapas

1. **`build_index.py`** — varre os `.meta` do `ExportedProject` e monta `guid_index.json`
   (36.761 guids). Lê só o cabeçalho de cada arquivo.
2. **`unityyaml.py`** — leitor do dialeto YAML do Unity. O PyYAML não serve: engasga nas
   tags `!u!` e leva minutos num `.unity` de 10 MB. Duas pegadinhas do formato, ambas
   descobertas porque o parse saía truncado:
   - uma sequência abaixo de `chave:` fica na **mesma** indentação da chave, não mais fundo;
   - listas vazias aparecem como `[]` na própria linha, e viram string se tratadas como escalar.
3. **`convert_scene.py`** — extrai as camadas, resolve cada sprite (guid → asset `Sprite` →
   textura + retângulo) e recorta o PNG do atlas, deduplicando por hash. Pontos que exigiram
   cuidado:
   - o retângulo do Unity conta a partir de **baixo**, o PNG conta de cima;
   - a walkability é consultada pelo `m_Name` de dentro do asset, **não** pelo nome do
     arquivo: quando dois assets colidem de nome o AssetRipper renomeia o arquivo
     (`Grass` → `Grass_1`), e a busca falhava justo nas tiles mais comuns — o mapa saía com
     1.102 células sem tipo;
   - o pivot de cada sprite é preservado. Nem todo tile é 32×32 e há pivots **fora de 0..1**
     (decoração que invade a célula vizinha de propósito); ancorar tudo no canto entorta o mapa.
4. **`walkability.py`** — reproduz `GetTypeOfTileDirectlyBelowSortOrder` do `GridController`:
   vale a camada de maior `sortingOrder` **abaixo** do personagem. O corte é 20, o sort order
   do corpo (`Shadow=15`, `Body=20`, `Head=45` nos NPCs das cenas originais). Isso não é
   detalhe: os prédios são tiles, com a **base** em `OverShadowDetail` (17, abaixo → bloqueia)
   e o **topo** em `OverBodyDetail` (25, acima → você passa por trás). Cortar por "nome começa
   com Over" deixaria todas as casas atravessáveis.
5. **`emit_unity.py`** — grava `Assets/MapData/<cena>.json` em arrays paralelos (a
   `JsonUtility` não lê lista de objetos aninhados, mas lê `int[]`/`string[]`) e copia os PNGs
   para `Assets/Art/YAPU/<cena>/Tiles/`.
6. **`preview.py`** — renderiza o mapa inteiro num PNG. É o teste de fumaça: erro de
   orientação, de origem ou de ordem de camada aparece na hora.

Do lado da Unity, `Assets/Editor/YapuMapImporter.cs` (menu **YAPU ▸ Construir mapa**) importa
as texturas, cria os assets de `Tile` e monta a cena. O pivot original de cada tile entra na
**matriz do Tile**, não no import da textura, para que o mesmo PNG possa ser usado com pivots
diferentes sem duplicar o arquivo.

## Como rodar

```sh
V=tools/yapu-extract/.venv/Scripts/python.exe
$V tools/yapu-map/build_index.py                     # uma vez
$V tools/yapu-map/convert_scene.py "YAPU_Demo/Ripped/ExportedProject/Assets/YAPUExampleProject/Regions/DemoRegion1/StartingVillage/StartingVillage.unity"
$V tools/yapu-map/emit_unity.py tools/yapu-map/out/StartingVillage.json
$V tools/yapu-map/preview.py tools/yapu-map/out/StartingVillage.json preview.png   # conferência

"/c/Program Files/Unity/Hub/Editor/6000.5.10f1/Editor/Unity.exe" -batchmode -quit -nographics \
  -projectPath unity/Unity -executeMethod Yapu.EditorTools.YapuMapImporter.BuildStartingVillage
```

## Estado

`StartingVillage` pronta e jogável: 9 camadas, 8.766 células, 217 tiles únicos, 4.661 células
de colisão. Faltam as outras 43 cenas de `DemoRegion1` (Route1, Route2, PortTown, LeagueTown,
RainbowCave e os interiores) — o conversor já aceita qualquer uma delas por caminho.
