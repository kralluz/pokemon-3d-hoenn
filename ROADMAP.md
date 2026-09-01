# Roadmap — Pokémon-like 2D

Objetivo final: jogo 2D estilo Pokémon (gens 1-3), online, com história própria.
Foco agora: protótipo mínimo — mapa pequeno, andar (WASD), entrar em batalha.

## Fase 0 — Base do projeto
- [ ] Projeto Unity 2D (URP 2D ou built-in, tanto faz pro protótipo)
- [ ] Estrutura de pastas: Scripts/Player, Scripts/Battle, Scripts/Data, Art, Scenes

## Fase A — Pipeline de assets (concluída)
Fonte: `apk/Omega.Ruby.ver.1.2.22.build.22.apks` (Unity 2022.3.62f2, IL2CPP + HybridCLR).
Ferramenta: `tools/omega-extract/` (ver README de lá para o esquema da cifra).
- [x] Desempacotar o `.apks` → `base.apk`, `split_config.arm64_v8a.apk`, asset pack (625 MB)
- [x] Abrir `data.unity3d` do base (UnityFS puro) — só cena de launcher/hot-update
- [x] Il2CppDumper sobre `libil2cpp.so` + `global-metadata.dat`
- [x] Reconstruir `AssetBundleEncryption::DecryStream` do ARM64 (XOR triplo, chave por arquivo)
- [x] Recuperar a chave global `F` pelo manifesto, sem precisar da metadata
- [x] Mapear os 3447 arquivos GUID → AssetName (validado com 2x CRC32, 100%)
- [x] Decifrar + desempacotar 7z → 3447 AssetBundles (2,06 GB)
- [x] Exportar com UnityPy: 46 tipos, 5,2 GB (mesh .obj, textura .png, audio .wav, resto typetree)
- [x] Catalogar as tabelas de config (`tools/omega-extract/config_catalog.json`)
- [x] Exportar os modelos em glTF com esqueleto e animacao (`build_glb.py`)
- [x] Viewer 3D no navegador com player de animacao
- [x] Importar pro projeto Unity via glTFast (623 prefabs, 0 erros)

## Fase 1 — Movimento (mapa de teste)
- [ ] Tilemap pequeno (grama, caminho, água, umas árvores de colisão)
- [ ] PlayerController 2D: WASD/grid ou free-move, sprite com 4 direções
- [ ] Câmera seguindo o player (Cinemachine ou script simples)
- [ ] Colisão com cenário

## Fase 2 — Dados de monstro (ScriptableObjects)
- [ ] `MonsterSpecies` (SO): nome, tipo, stats base, sprite
- [ ] `MoveData` (SO): nome, tipo, poder, precisão, PP
- [ ] 2-3 monstros e 4-6 golpes pra testar o fluxo
- [ ] `MonsterInstance` (classe runtime): level, HP atual, moves aprendidos

## Fase 3 — Encontro selvagem
- [ ] Trigger na grama (chance por passo) → inicia batalha
- [ ] Transição de cena/tela pra Battle

## Fase 4 — Batalha por turno (mínima)
- [ ] Battle state machine: Início → Escolha ação → Resolve turno → Checa fim
- [ ] Ações: Atacar (escolher golpe), Fugir
- [ ] Cálculo de dano simples (sem tabela de efetividade complexa ainda)
- [ ] UI: HP bar dos dois lados, menu de ação, log de texto
- [ ] Vitória/derrota → volta pro mapa

## Fase 5 — Loop jogável
- [ ] Player pode ter 1 monstro inicial
- [ ] Perder todo HP do monstro = "apagar" / voltar a um ponto
- [ ] Save simples (PlayerPrefs ou JSON) — level e HP do monstro

## Depois do protótipo (não agora)
- Múltiplos mapas, cidades, NPCs, diálogo
- Time de até 6 monstros, troca em batalha, itens
- Evolução, captura
- Multiplayer/online
- Assets de arte definitivos
