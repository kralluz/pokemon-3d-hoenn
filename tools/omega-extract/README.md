# omega-extract

Extrai os assets do `apk/Omega.Ruby.ver.1.2.22.build.22.apks`
(Unity 2022.3.62f2, IL2CPP + HybridCLR).

## Como o pacote é montado

```
.apks (zip)
 ├── base.apk                        data.unity3d (UnityFS puro: só o launcher)
 ├── split_config.arm64_v8a.apk      libil2cpp.so, libunity.so
 └── split_install_time_asset_pack.apk
      └── assets/<GUID>/<GUID>/...   3450 arquivos criptografados
```

Cada arquivo do asset pack é: **AssetBundle → comprimido em 7z → cifrado**.

## A cifra

`Assets/Scripts/Main/Framework/AssetBundleVersionMgr/AssetBundleEncryption/`,
reconstruída do ARM64 de `AssetBundleEncryption::DecryStream`:

```
pb  = base64(utf8(abLoadPath))       # abLoadPath = AssetName do manifesto
L   = len(pb)
hdr = arquivo[0:L]                   # Random.Next(255) gravado por EncryFile
size = decode255(arquivo[L:L+4]) ^ KEYS_1[0] ^ KEYS_2[0] ^ randKeys[0]

randKeys[i] = pb[i] ^ hdr[i] ^ KEYS_1[i%7] ^ KEYS_2[i%14]
corpo[j]   ^= randKeys[j%L] ^ KEYS_1[(L+j)%7] ^ KEYS_2[(L+j)%14]
```

Como `KEYS_1` e `KEYS_2` só aparecem em XOR, basta `F[i] = KEYS_1[i%7] ^ KEYS_2[i%14]`
(período 14). Os dois índices usados têm sempre a mesma paridade, então a constante
global de cada componente cancela — não foi preciso extrair as chaves da metadata.

`F` foi recuperado do manifesto (`AssetBundleConst.ENCRYABINFOFILE`,
`D1C2327F-8C01-2EC1-8BD0-91F351F97D14`, `abLoadPath` = o próprio nome, L=48):
o keystream tem período `lcm(48,14)=336` e o conteúdo é TSV, então cada resíduo
sai por força bruta de 1 byte contra o alfabeto do arquivo.

O `abLoadPath` de cada bundle é o `AssetName` do manifesto. O nome é descoberto
calculando os 8 primeiros chars do base64 a partir do magic 7z (constante) e
confirmando com **dois CRC32** do header 7z. 3447/3447 casaram sem ambiguidade.

## Uso

```bash
python build_map.py                  # gera abmap.json (arquivo GUID -> AssetName)
python extract.py                    # decifra + desempacota 7z -> out/bundles/*.ab
python export.py <src> <out> "**" TextAsset,Texture2D,Sprite,AudioClip,MonoBehaviour
python export_rest.py                # Mesh->.obj, Shader, Font e todo o resto (typetree)
```

Requer `UnityPy`, `py7zr` (venv em `.venv-apk`).

## O que sai

`out/bundles/` — 3447 AssetBundles (.ab), 2,0 GB, um por AssetName do manifesto:

| pasta      | bundles | conteúdo                                    |
|------------|---------|---------------------------------------------|
| `model`    | 1398    | Mesh, Material, Texture2D, AnimationClip    |
| `effect`   | 969     | efeitos/partículas                          |
| `ui`       | 473     | prefabs, MonoBehaviour, atlas               |
| `config`   | 280     | TextAssets TSV: tabelas de dados do jogo    |
| `scene`    | 125     | cenas                                       |
| `dependent`| 118     | dependências compartilhadas                 |
| `sound`    | 77      | AudioClip                                   |

`out/assets/` — 5,2 GB, 46 tipos de objeto Unity. Um diretório por tipo:

| tipo            | arquivos | formato                                      |
|-----------------|----------|----------------------------------------------|
| `AnimationClip` | 1.031    | JSON typetree (agrupado por bundle)          |
| `Mesh`          | 9.356    | `.obj`                                       |
| `AudioClip`     | 608      | `.wav`                                       |
| `Texture2D`     | 8.033    | `.png`                                       |
| `TextAsset`     | 412      | `.txt` — 278 tabelas TSV, 86.350 linhas      |
| `MonoBehaviour` | 1.828    | JSON typetree                                |
| `Material`      | 2.341    | JSON typetree                                |
| `Shader`        | 1.233    | `.shader`                                    |
| `Font`          | 2        | `.ttf` / `.otf`                              |
| demais 37 tipos | —        | JSON typetree, um arquivo por bundle         |

Meshes sem dados de vértice (geradas em runtime) caem para typetree JSON.

`config_catalog.json` indexa as 412 tabelas com colunas e contagem de linhas.

## Modelos em glTF (rig + animacao)

```bash
python build_glb.py              # todos -> out/glb/<nome>.glb
python build_glb.py pikachu      # so um, para depurar
```

`.obj` guarda so geometria. Numa malha com skin os vertices ficam em **espaco de
bind** e so vao para o lugar quando as matrizes de osso sao aplicadas — por isso
Archen, AshGreninja e afins apareciam espalhados. `build_glb.py` monta um `.glb`
completo lendo o bundle:

| do Unity | para o glTF |
|---|---|
| arvore de `Transform` | nos com translation/rotation/scale |
| `SkinnedMeshRenderer.m_Bones` | `skin.joints` |
| `Mesh.m_BindPose` | `skin.inverseBindMatrices` |
| `MeshHandler` (posicao, normal, UV, indices, pesos) | accessors |
| `Material._MainTex` / `_Color` / `m_Scale` `m_Offset` | material PBR + `KHR_texture_transform` |
| `AnimationClip.m_MuscleClip` | `animations` |

`glb.py` e um escritor de GLB minimo (sem dependencia externa).

### Conversao de eixos

Unity e canhoto (X dir, Y cima, **Z frente**); glTF e destro. Negamos Z:

```
posicao/normal  (x, y, -z)
quaternion      (x, y, z, w) -> (-x, -y, z, w)
matriz          M' = S M S,  S = diag(1, 1, -1, 1)
triangulos      ordem invertida (o determinante fica negativo)
```

Como personagens Unity olham para +Z, depois da conversao eles olham para -Z —
por isso a camera do viewer fica no lado negativo de Z.

### Pose de repouso

O prefab guardado no bundle **nao esta numa pose util**: no jogo o Animator esta
sempre tocando algo, entao a pose salva nunca importou. Exportada como esta, o
modelo parado fica torto — a chama do Charmeleon virava uma lasca na mao, a folha
da Chikorita saia do lugar. No navegador nao aparecia porque o viewer sempre toca
um idle; no Unity, com o prefab parado na cena, aparecia na hora.

`add_animations()` assa o **primeiro quadro do idle** (`SceneIdle` > `Idle1` >
`Idle` > primeiro clip) como TRS padrao dos nos. Assim o modelo parado ja nasce
correto, e a animacao continua sobrescrevendo normalmente.

### Duas armadilhas do skin

1. **4o peso corrompido.** Varios canais guardam so 3 influencias e a 4a e
   implicita (`1 - soma`); o decode traz lixo no 4o componente (pesos tipo -25),
   o que esticava o modelo. `fix_weights()` recalcula e renormaliza.
2. **Malha sem pesos.** Vinculo rigido a um unico osso vem com
   `m_BoneWeights = None`; nesse caso peso 1 no primeiro indice.

### Animacao (`animclip.py`)

Os clips sao Mecanim, nao legacy — as curvas estao em `m_MuscleClip.m_Clip`,
divididas em tres blocos concatenados por indice de curva:

```
m_StreamedClip   quadros esparsos: [tempo, nKeys, (indice, coef[4]) * nKeys]
                 o valor no quadro e coef[3]; 1o e ultimo quadro sao sentinelas
m_DenseClip      amostragem regular: m_SampleArray[frame * nCurves + i]
m_ConstantClip   valor fixo no clip inteiro
```

`m_ClipBindingConstant.genericBindings` diz de quem e cada curva. Cada binding
consome varias curvas (posicao 3, rotacao 4, escala 3). O campo `path` e o
**CRC32 do caminho do Transform relativo ao GameObject que tem o Animator** —
CRC32 padrao (zlib), o que foi confirmado batendo 36/36 hashes no Pikachu.

Nas rotacoes, quando o produto escalar entre quaternions consecutivos e negativo
o sinal e invertido, senao o slerp faz o caminho longo e o osso da uma cambalhota.

## Viewer 3D

```bash
python build_glb.py        # gera out/glb/*.glb (rig + animacao)
python build_viewer.py     # gera out/viewer_models.json (nomes, dex, contagens)
python serve_viewer.py     # sobe em http://127.0.0.1:8765 e abre o navegador
```

623 modelos com miniatura 3D gerada sob demanda (um renderer WebGL compartilhado,
fila por IntersectionObserver) e viewer com OrbitControls ao clicar. Busca por nome
em ingles, chines ou numero da dex.

O viewer carrega os `.glb`, entao material, textura e esqueleto ja vem prontos do
bundle. So trocamos o material PBR por difuso (`MeshLambertMaterial`): PBR com
ambiente forte lavava a cor — Charizard saia bege em vez de laranja.

### Como o material e resolvido

Tanto `build_glb.py` quanto `build_viewer.py` nao casam por nome: leem o bundle
com UnityPy e seguem os PPtr reais

```
Renderer.m_Mesh      -> Mesh        -> qual .obj
Renderer.m_Materials -> Material
                        _MainTex             -> Texture2D -> qual .png
                        _MainTex.m_Scale/Offset -> repeat/offset de UV
                        _Color                  -> tint multiplicado na textura
```

Tudo vem do dado do material. **Nenhuma heuristica** — uma tentativa anterior de
"corrigir" o `m_Scale` quando ele parecia grande demais so quebrava modelos, porque
o scale esta sempre certo: as texturas de corpo costumam ter metade da largura
(128 em vez de 256) e sao feitas para ladrilhar 2x num modelo simetrico.

Quatro armadilhas que custaram caro e ja estao tratadas:

1. **Nomes duplicados.** Um bundle tem duas `Texture2D` chamadas `pm0004_00_Body1.tga`
   (normal e shiny). O exportador gravou a segunda como `...~2.png`. O script reproduz
   a mesma numeracao para casar `path_id` com arquivo, e prefere a variante sem `~`
   (a base) quando o modelo traz os dois sets de renderer.
2. **Textura em outro bundle.** As chamas (`FireCoreA1`, `FireStenA1`) vivem em
   `dependent/model/sprite/sprite2`. PPtr com `m_FileID != 0` cai num indice global
   por nome.
3. **`_Color` importa.** As chamas sao textura cinza + tint no material
   (`ff7700` no nucleo, `ffea00` na borda). Ignorar o `_Color` deixava a cauda do
   Charmander branca. 98 malhas tem tint nao-branco.
4. **Corrida de textura.** A textura vazia do three.js e transparente; renderizar a
   miniatura antes do `.png` carregar fazia o `alphaTest` apagar a malha inteira.
   `build()` espera `loadAsync` de todas as texturas antes de renderizar.

Iluminacao: difuso puro (`MeshLambertMaterial`) com ambiente moderado. PBR com
ambiente forte lavava a cor — Charizard saia bege em vez de laranja.

three.js fica em `out/viewer/vendor/` (funciona offline).

Os `.obj` de `out/assets/Mesh/` continuam la para quem quiser so a geometria, mas
o viewer usa os `.glb` — sao eles que tem rig e animacao.

## Importar no Unity

O projeto e `unity/Unity` (Unity 6000.5.10f1). O Unity **nao importa `.glb`
nativamente**, entao `Packages/manifest.json` ganhou `com.unity.cloud.gltfast`.

```bash
cp apk/_extracted/out/glb/*.glb unity/Unity/Assets/OmegaModels/
"/c/Program Files/Unity/Hub/Editor/6000.5.10f1/Editor/Unity.exe"    -batchmode -quit -nographics    -projectPath <projeto> -executeMethod OmegaImportReport.Run -logFile <log>
```

`Assets/Editor/OmegaImportReport.cs` roda em batchmode e confere o que entrou de
fato em cada prefab (skinned renderers, ossos, malhas, materiais, texturas,
clips) — conferencia por dado, nao a olho. Resultado do lote completo:

```
623 modelos | sem skin=0 | sem clip=28 | sem textura=0 | erros de import=0
```

Cada `.glb` vira um prefab com SkinnedMeshRenderer + esqueleto + AnimationClips.
Os 28 sem clip sao variantes que no jogo reusam a animacao da forma base.

Custo em disco: `Assets/OmegaModels` 612 MB, `Library` ~2,5 GB.

### Cenas (`scene/main`, `scene/battle`)

```bash
python build_glb.py scene/main
python build_glb.py scene/battle
```

Cenas nao sao como modelos e quebraram o exportador tres vezes:

1. **PPtr entre arquivos.** Um bundle de cena tem *dois* arquivos serializados
   (a cena e o `.sharedassets`), e eu resolvia ponteiros por `path_id` num mapa
   local, ignorando `m_FileID` — pegava o objeto errado. Agora tudo passa por
   `PPtr.deref()` tipado, que resolve entre arquivos. Isso deixou o caminho dos
   modelos mais correto tambem.
2. **Geometria em `dependent/`.** As cenas referenciam malhas que moram noutro
   bundle. Carregamos `dependent/scene` + `dependent/shader` junto (17 bundles)
   so para resolver PPtr, filtrando os objetos que sao mesmo da cena.
3. **PPtr nulo** (`m_PathID == 0`) num material.

O Unity fez *batching estatico* nessas cenas, entao o cenario inteiro vem como
uma malha `Combined Mesh (root: scene)` com varios submeshes — por isso a
contagem de malhas e baixa mesmo com dezenas de MeshRenderers no bundle.
Os `*_navmesh.ab` so tem `NavMeshData` e nao geram `.glb`.

### Esqueleto duplicado (o bug que mais custou)

Cada malha aparece **duas vezes** no bundle: presa ao esqueleto principal e a um
duplicado `<Nome>Flash` (o efeito de piscar ao levar dano). Escolher renderer por
textura misturava os dois dentro do mesmo modelo, e o resultado era peca flutuando
(posicionada pelo esqueleto errado) e imune a animacao (os clips so endereçam o
principal). `pick_skeleton()` escolhe uma raiz so — a que as bindings dos clips
realmente cobrem — e descarta os renderers da outra.
