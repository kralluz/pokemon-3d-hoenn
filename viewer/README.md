# Pokédex 3D — visualizador

Site local em HTML + CSS + JS puro. Sem build, sem framework, sem CDN —
three.js vendorizado em `vendor/`.

## Rodar

```bash
python tools/serve.py
```

Abre `http://localhost:8080/viewer/`. Precisa de servidor HTTP: ES modules e
`fetch` não funcionam por `file://`.

## O que dá pra fazer

- **Girar / zoom / mover** — arrastar, scroll, botão direito
- **Lista** das 135 espécies com número, nome e cor dos tipos
- **Buscar** por nome, número, tipo (pt ou en) ou nome de variante
- **Filtrar por tipo** — chips no topo, acumulam
- **Variantes** — botões embaixo: Normal, Mega, Shiny, Mega shiny, Galar, Primal
- **Toggles** — girar sozinho, wireframe, grade, fundo claro/escuro, recentrar
- **Teclado** — `↑` `↓` troca de Pokémon, `/` busca, `R` `W` `G` `B`, espaço recentra
- **URL** — `#384` ou `#0384_mega` abre direto naquele modelo

## Por que GLB e não os FBX de `assets/gen3`

Os FBX crus do Pokémon GO empacotam corpo e rosto **numa textura só**, endereçada
pela coordenada V (V 0–1 = corpo, V ≥ 1 = rosto). Sem reimplementar o shader do
jogo, os olhos saem errados — foi exatamente o bug que apareceu.

Os GLB do [Pokemon-3D-api/assets](https://github.com/Pokemon-3D-api/assets) já vêm
com a malha separada por material (`body_mat`, `eye_mat`, `mouth_mat`), então o
three.js renderiza certo sem nenhuma gambiarra.

O preço é resolução: são versões otimizadas pra web (Draco + decimação), na casa
de 2–12 mil triângulos contra 4–15 mil dos FBX. Para **olhar**, é o certo. Para
**usar em engine**, os rigs em [assets/gen3/](../assets/gen3/) continuam sendo a
fonte boa (malha densa, esqueleto completo, texturas separadas).

## Conteúdo

177 modelos, 135 espécies, 30 MB em `assets/gen3_glb/`:

| variante | quantos |
|---|---|
| Normal | 135 |
| Mega | 20 |
| Shiny | 12 |
| Mega shiny | 6 |
| Galar | 2 (Zigzagoon, Linoone) |
| Primal | 2 (Kyogre, Groudon) |

## Arquivos

| | |
|---|---|
| `index.html` / `style.css` / `app.js` | o viewer |
| `models.json` | índice gerado por `tools/fetch_gen3_glb.py` |
| `vendor/` | three.js 0.185 + GLTFLoader, DRACOLoader, OrbitControls (3,2 MB) |
| `thumbs/` | miniaturas opcionais — rode `node tools/thumbs.mjs` com o servidor no ar |

## Ferramentas

```bash
python tools/fetch_gen3_glb.py    # rebaixa os GLB e regera models.json
python tools/serve.py             # servidor local
node   tools/shoot.mjs <url> <pasta> 384 300 …   # screenshots em Chrome headless
node   tools/verify_fbx.mjs       # valida os FBX de assets/gen3 (outra fonte)
```

`app.js` expõe `window.__viewer` (`scene`, `camera`, `renderer`, `root`,
`controls`, `grid`, `fitCamera`) — é o que esses scripts usam.
