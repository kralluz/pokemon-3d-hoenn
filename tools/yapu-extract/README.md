# Extração de assets da demo YAPU

Pipeline usado para tirar os assets de `YAPU_Demo/YAPUDevWindows/` (build Unity 6000.0.27
IL2CPP) e colocá-los em `YAPU_Demo/Ripped/` e `YAPU_Demo/extracted/` (ambos no `.gitignore`).

## Por que precisou de ferramenta própria

A build é IL2CPP: não existem DLLs gerenciadas, e o AssetRipper reconstrói os tipos com
Cpp2IL. Isso recupera nomes, ordem e tipos dos campos — **mas o Cpp2IL apaga os atributos
customizados**. Sem `[SerializeField]` o AssetRipper não sabe quais campos privados o Unity
serializa, erra o layout binário e exporta o objeto vazio. Foi o que aconteceu com 1.033
ScriptableObjects, entre eles os 430 `MonsterEntry` (stats base, tipos, habilidades,
learnsets, evoluções).

A solução combina as duas metades da informação:

| origem | o que fornece |
|---|---|
| `Ripped/AuxiliaryFiles/GameAssemblies/Assembly-CSharp.dll` (Cpp2IL) | nomes, ordem e tipos dos campos |
| código-fonte em `YAPU/` (MIT) | os marcadores `[SerializeField]` / `[NonSerialized]` |

## Etapas

1. **`scan_serfields.py`** — varre o `.cs` do YAPU e produz `serfields.json` com os campos
   marcados. Trata declarações quebradas em várias linhas e diretivas `#if` no meio dos
   atributos, que uma varredura linha a linha perde.
2. **`layout/`** (C# + Mono.Cecil) — lê o `Assembly-CSharp.dll`, aplica as regras de
   serialização do Unity e emite o layout binário em JSON (`layouts.json`,
   `layouts_all.json`). Pontos que exigiram tratamento, cada um descoberto porque a
   checagem de bytes reprovou:
   - a cadeia de herança para em tipos `System.*`, senão `SerializableDictionary`
     (que herda de `List<T>`) arrasta `_items`/`_size`/`_version`;
   - ao subir a cadeia é preciso **preservar os argumentos genéricos** de cada nível:
     `Resolve()` direto transforma `Foo : SerializableDictionary<Status, float>` de volta
     no genérico aberto e deixa os campos como `TK`/`TV`, sem layout possível;
   - tipos de terceiros (WhateverDevs) não têm fonte, então lá os campos privados entram
     pela regra padrão do Unity — com exceções pontuais listadas em `scan_serfields.py`
     para flags de runtime como `AudioLibrary.initialized`;
   - classe abstrata em campo = `[SerializeReference]`, serializada como um `rid` de 64 bits
     com o objeto real num registro no fim do buffer. O catálogo de subclasses concretas
     também é emitido, para decodificar esse registro;
   - `AnimationCurve` é modelada à mão (`m_Curve` de `Keyframe` + três ints), já que o Unity
     não a serializa campo a campo como uma classe comum;
   - na resolução por nome curto, tipos do jogo têm prioridade sobre os da engine — existe
     um `UnityEngine.SceneManager` que sequestrava o `SceneManager` do YAPU.
3. **`decode.py`** (só `MonsterEntry`) e **`decode_all.py`** (todas as classes) — leem os
   bytes crus via UnityPy e aplicam o layout. **Um objeto só é aceito se o parser consumir
   exatamente todos os bytes do buffer**; qualquer sobra ou falta reprova o registro. É essa
   checagem que garante que o layout está certo, e não só plausível. Dois detalhes do
   formato: arrays de primitivos de 1 e 2 bytes são empacotados (alinha só no fim, não a
   cada elemento), e um objeto cujo buffer acaba logo após `m_Name` simplesmente não tem
   campos serializados — é registrado como vazio em vez de forçar um layout em cima de
   bytes que não existem.

4. **`extract_audio.py`** — passe de áudio. Carregando os arquivos soltos o UnityPy não
   resolve o `.resource` externo, então `m_AudioData` chega vazio e o decodificador FMOD
   reprova com `FORMAT` — foi o que derrubou os 1.343 `AudioClip` na primeira passada. Aqui
   os bytes do banco FSB5 são lidos à mão do `.resource` pelo offset/tamanho de
   `m_Resource` antes de decodificar.

`extract.py` e `raw_mb.py` são os passes auxiliares com UnityPy: PNGs soltos e dump dos
bytes crus dos objetos que o AssetRipper não conseguiu ler.

## Como rodar

```sh
python scan_serfields.py
cd layout && dotnet build
SERFIELDS=../serfields.json dotnet run -- <GameAssemblies> ../layouts.json <TipoRaiz>...
python ../decode_all.py     # precisa de UnityPy (pip install UnityPy)
python ../extract_audio.py
```

## Resultado

**1.033 de 1.033** objetos recuperados, todos com consumo exato de bytes. Isso fecha
integralmente a lacuna deixada pelo AssetRipper.

- 430/430 `MonsterEntry`, conferidos contra dados conhecidos: Bulbasaur 45/49/49/65/65/45,
  catch 45, evolui no nível 16; Charizard 78/84/78/109/85/100, catch 45, base exp 267;
  Pikachu com as 16 formas e as evoluções condicionais por tag de cena.
- 1.033 objetos em 404 classes em `YAPU_Demo/extracted/MonoBehaviour_decoded/`.
- 1.343/1.343 `AudioClip` em WAV (641 MB) em `YAPU_Demo/extracted/AudioClip/`.

Somando com o que o AssetRipper já exportava corretamente, os 26.757 ScriptableObjects da
demo estão 100% legíveis.
