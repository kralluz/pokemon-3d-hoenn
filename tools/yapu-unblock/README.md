# Destravar o YAPU sem os plugins pagos/privados

Levantamento do que impede o [YAPU](../../YAPU/) de compilar fora da máquina do autor, e
o que já está resolvido. Números medidos com Mono.Cecil em cima das DLLs reconstruídas pelo
Cpp2IL em `YAPU_Demo/Ripped/AuxiliaryFiles/GameAssemblies/`, cruzados com o código-fonte.

## Situação por dependência

| dependência | uso no YAPU | situação |
|---|---|---|
| **Odin Inspector** (pago) | 583 usings, **só atributos de inspector** | ✅ **resolvido** — `generated/OdinShim.cs` |
| **WhateverDevs.\*** (privado) | 1.119 usings · 41 tipos · 328 membros públicos | 🔴 precisa ser obtido ou reimplementado |
| **Text Animator** (pago) | diálogos | 🟡 docs do autor dizem "substituível" |
| Extenject/Zenject | 152 usings | 🟢 grátis (MIT) |
| DOTween free | 197 usings | 🟢 já está em `DOTween_extracted/` |
| TMPro, Cinemachine, MLAgents | poucos | 🟢 grátis |
| `YAPUAssets.zip` (arte) | — | 🟢 extraído da demo |

## O Odin: resolvido

O YAPU **não usa a serialização do Odin** — não há `SerializedScriptableObject`,
`SerializedMonoBehaviour` nem `OdinSerialize` em lugar nenhum. Confirmado de duas formas
independentes: por grep no fonte, e pela decodificação byte a byte dos ScriptableObjects,
que fechou 1.033/1.033 usando só as regras de serialização nativas do Unity. Se houvesse
serialização Odin, aqueles bytes não teriam fechado.

Logo o Odin ali é decoração de inspector, e stubs vazios bastam para compilar.
`generated/OdinShim.cs` tem 52 tipos gerados a partir das assinaturas reais da
`Sirenix.OdinInspector.Attributes.dll` — inclusive os campos e propriedades, para que os
argumentos nomeados do código (`[ListDrawerSettings(IsReadOnly = true)]`) continuem válidos.
Fecho transitivo incluído: enums como `ButtonStyle` e `SdfIconType` entram junto.

Compila limpo (testado isolado; a única referência externa é `UnityEngine.FilterMode`).
O arquivo é guardado por `#if !ODIN_INSPECTOR`, então some sozinho se você comprar o plugin.

**O que se perde:** a UI do inspector e as ferramentas de autoria. O jogo roda igual — os
atributos não têm efeito em runtime.

**Delimitação importante:** `YAPU/Runtime/` (o jogo) **não usa `Sirenix.OdinInspector.Editor`
em nenhum arquivo**. Só 4 dos 30 arquivos de `YAPU/Editor/` usam. Então o runtime compila
com este shim; o `Editor/` (5.266 linhas) pode ficar de fora num primeiro momento.

## As libs WhateverDevs: o bloqueio real

Não estão no GitHub do autor, não estão no OpenUPM, e o release do YAPU só tem
`Project.zip` (que é a pasta `YAPU/`) e a demo. São bibliotecas privadas dele.

Das 113 classes públicas nas DLLs, **41 são realmente usadas**, somando **328 membros
públicos**. Tabela completa em [`generated/whateverdevs-usage.md`](generated/whateverdevs-usage.md).
Por subsistema:

| subsistema | tipos | dificuldade |
|---|---|---|
| Core (Loggable, WhateverBehaviour, Singleton, CoroutineRunner, Utils, SerializableDictionary, ObjectPair) | 12 | baixa — plumbing; o layout do `SerializableDictionary` já é conhecido da decodificação |
| UI helpers (HidableUiElement, EasyUpdateText) | 3 | baixa |
| DI/Zenject (GameObjectFactory, instaladores) | 3 | baixa |
| Configuração, persistência, serialização, Version | 9 | baixa/média — é JSON em disco |
| Áudio (AudioManager, AudioLibrary, AudioReference) | 4 | média — temos o `AudioLibrary` decodificado e os 1.343 `.ogg` |
| Localização (ILocalizer, Localizer, LocalizedTextMeshPro) | 4 | média — 910 menções no fonte, mas é tabela chave→string |
| Scene management sobre Addressables | 4 | **alta** — a peça mais arriscada |

As DLLs no build têm assinatura mas **não têm corpo** (IL2CPP + Cpp2IL), então servem para
gerar esqueletos, não para rodar.

### Armadilha das GUIDs

Prefabs e cenas da demo referenciam scripts por `guid` de assembly + `fileID` derivado do
nome da classe (`type: 3`). Uma reimplementação precisa casar com isso, senão todo o
conteúdo exportado vem desconectado. O AssetRipper não gerou `.cs` para essas classes — só
60 stubs de um plugin de console. Isso encarece a reimplementação bem além dos 328 membros.

## Recomendação

**Peça os pacotes ao autor antes de reimplementar.** Ele convida ao contato no README do
YAPU (Telegram e Discord) e afirma explicitamente que o projeto depende de plugins pagos e
assets com copyright — ou seja, sabe que terceiros esbarram nisso. Uma mensagem custa
minutos; a reimplementação custa semanas e ainda esbarra no problema das GUIDs.

Se ele não puder liberar, aí sim a reimplementação é viável e este levantamento diz
exatamente o tamanho dela.

## Como rodar de novo

```sh
dotnet build
dotnet run -- <GameAssembliesDir> <YAPUSourceDir> <outDir>
```
