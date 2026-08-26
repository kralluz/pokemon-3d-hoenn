# Mundo — protótipo de movimentação

`world.html` é a segunda metade do protótipo jogável: um cenário aberto onde dá
para andar, correr, pular e orbitar a câmera com um personagem animado de
verdade. Mesma stack do Pokédex — HTML/CSS/JS puro, three.js vendorizado.

## Rodar

Com `python tools/serve.py` no ar: `http://localhost:8080/viewer/world.html`
(tem um link "🌍 Mundo" no topo da Pokédex, e "← Pokédex 3D" aqui para voltar).

## Controles

| tecla | ação |
|---|---|
| `W A S D` ou setas | andar (relativo à direção da câmera) |
| `Shift` | correr |
| `espaço` | pular |
| clicar na cena | trava o mouse (Pointer Lock) |
| mover o mouse | olha ao redor (free-look, sem precisar segurar botão) |
| scroll | zoom |
| `Esc` | destrava o mouse (padrão do navegador) |

## Assets — Kenney, CC0

Baixados via [ETdoFresh/kenney.nl](https://github.com/ETdoFresh/kenney.nl)
(espelho GitHub dos packs oficiais [kenney.nl](https://kenney.nl)), licença
**CC0** — uso comercial liberado, sem crédito obrigatório.

- **Cenário**: subconjunto de 36 modelos da *Nature Kit* (árvores, rochas,
  flores, cogumelos, caminhos, trecho de rio, ponte, cerca) em
  [assets/environment/](../assets/environment/)
- **Personagem**: *Animated Characters 1* (Kay Lousberg) em
  [assets/character/](../assets/character/) — malha + esqueleto
  (`character.fbx`) e três clipes de animação reais (`idle.fbx`, `run.fbx`,
  `jump.fbx`), todos com os mesmos nomes de osso, tocam direto sem retarget

`tools/fetch_world_kit.py` rebaixa e regenera essas duas pastas.

## Como funciona

- **Cenário**: cada `.glb` é carregado uma vez e clonado várias vezes
  (`place()`/`scatterRing()`) — árvores formam um anel na borda deixando o
  centro livre, o resto (rochas, flores, cogumelos, capim) espalha numa
  clareira, mais um trecho de rio decorativo com ponte e uma trilha de pedras
- **Personagem**: `character.fbx` entra a 0,00465 de escala (a malha crua do
  Kenney vem em ~376 unidades de altura; essa escala dá ~1,75 m). A pele
  (`character_skin.png`) é aplicada manualmente no material — é a única
  textura, então não tem o problema de atlas dos modelos de Pokémon
- **Movimento**: direção calculada relativa ao yaw da câmera, personagem gira
  suavemente para encarar pra onde anda, `AnimationMixer` faz crossfade entre
  idle/run/jump
- **Câmera**: free-look por mouse via [Pointer Lock API](https://developer.mozilla.org/docs/Web/API/Pointer_Lock_API)
  — clicar na cena trava o cursor e `mousemove` (via `movementX/Y`) ajusta
  yaw/pitch direto, sem precisar segurar botão nenhum. A cada frame a posição
  da câmera é recalculada do zero a partir de yaw/pitch/distância ao redor de
  um alvo que persegue o personagem (`updateCamera()`) — não é
  `OrbitControls`, é uma órbita mão-feita, mais simples e sem o problema de
  "seguir por delta" que o `OrbitControls` tinha aqui (veja bugs abaixo)

## Bugs achados e corrigidos

- **A/D invertidos.** O cálculo do vetor "direita" tinha um `.negate()` a mais
  (`right.crossVectors(forward, up).negate()`) — invertia esquerda e direita.
  Confirmado por conta na mão e depois medido ao vivo (apertar D media
  deslocamento para a esquerda). `tools/check_strafe.mjs` testa isso.
- **Câmera não acompanhava o jogador.** Com o `OrbitControls` original, o
  código só movia `controls.target` a cada frame; o `OrbitControls` recalcula
  a posição da câmera a partir do offset atual (posição − alvo), então mover
  só o alvo faz a câmera girar para olhar o personagem sem de fato se
  deslocar com ele. Medido: a câmera ficava 36% atrás do deslocamento real do
  jogador. Isso foi uma das razões pra trocar `OrbitControls` pela órbita
  mão-feita descrita acima, que recalcula posição a partir do alvo do zero a
  cada frame — não tem offset acumulado pra sobrar (`tools/check_camera_follow.mjs`,
  100% de acompanhamento confirmado).
- **`$('#lock-hint')` retornava `null`.** O helper `$` deste arquivo é
  `getElementById` (não `querySelector`), então passar `'#lock-hint'` com o
  `#` (hábito de CSS) buscava um id literal `"#lock-hint"`, que não existe.
  O erro ficava só no `pageerror`, nunca aparecia no console normal — por
  isso `tools/check_mouselook.mjs` escuta os dois. O sintoma: o aviso "clique
  para travar o mouse" nunca sumia depois de travar.
- **Árvores e pedras pretas em certos ângulos.** As 87 malhas do Nature Kit
  vêm sem `metallicFactor` no glTF — o padrão da especificação pra esse campo
  é **1.0** (100% metálico), não 0. Sem mapa de ambiente pra refletir, um
  material metálico só mostra o reflexo especular direto, que em alguns
  ângulos cai a praticamente zero e o objeto renderiza preto sólido. Corrigido
  forçando `metalness = 0` em todo material carregado de `assets/environment/`
  (`loadDecor()` em `world.js`).

## Simplificações conhecidas

- **Sem colisão** — dá pra atravessar árvore e rocha. Para um protótipo de
  "anda que roda", não importou; um jogo de verdade precisa de física básica
  (câmera + capsule collider, ou pelo menos raio de repulsão nos objetos
  grandes do cenário)
- **Um clipe só pro deslocamento** — o Kenney não distingue andar de correr,
  então `run.fbx` toca nas duas velocidades, só muda o quanto o personagem
  desloca por segundo. Se quiser andar visualmente mais lento, precisa de um
  clipe de "walk" de outra fonte (o *Universal Animation Library* do
  Quaternius tem)
- **Sem chão fora do círculo** — o terreno é um disco de raio 48; o movimento
  é limitado a isso, não tem borda visual além do horizonte com neblina

## Testes

```bash
node tools/shoot_world.mjs <url> <pasta>       # andar/correr/pular + 4 screenshots
node tools/check_strafe.mjs <url>              # mede se A/D vao pro lado certo
node tools/check_camera_follow.mjs <url>       # mede se a camera acompanha o jogador
node tools/check_mouselook.mjs <url>           # pointer lock + mousemove giram a camera; scroll da zoom
node tools/explore_world.mjs <url> <pasta>     # anda pelo mapa inteiro, cata bug visual
```

Todos rodam em Chrome headless e **medem** o resultado (posição real, ângulo
real) em vez de só checar "carregou sem erro" — foi assim que os três bugs
acima foram achados, não por inspeção visual.
