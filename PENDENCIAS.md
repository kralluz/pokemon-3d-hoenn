# Nel Ord — o que falta

Levantado em 10/09/2026, depois de mesclar os 113 commits do Higor com a
extração do APK.

**Como ler:** cada item diz de onde veio a afirmação.
- 🔍 = medido nesta sessão (contei, rodei, ou li o código)
- 📋 = do relatório de estado do Higor (05/09) — anterior ao merge, pode ter mudado

**Restrição de design:** o projeto **não terá gacha, apostas, roleta ou bet**.
Isso já eliminou um grupo de evoluções do APK (ver seção 6).

---

## 1. Amizade — o motor existe e está inerte

🔍 Está tudo implementado e testado:

| | |
|---|---|
| Campo | `amizade`, 0–255, começa em **70** |
| Alteração | `Pokemon.AlterarAmizade(delta)`, com clamp |
| Condição de evolução | `ExigeAmizade { minima }` |
| Testes | 4, passando |

**O problema é a única fonte de ganho: `+1` por nível ganho.** Saindo de 70,
chegar aos 220 clássicos exigiria 150 níveis, e o teto é 100. Na prática,
**evolução por amizade nunca dispara.**

Não falta motor — faltam **fontes**. `AlterarAmizade` já existe; falta chamá-lo
de mais lugares:

- [ ] Andar com o Pokémon na equipe
- [ ] Vencer batalha
- [ ] Curar no Centro Pokémon (o `Curandeiro` já existe)
- [ ] Itens que dão amizade
- [ ] Perder amizade ao desmaiar

**Destrava:** 38 evoluções hoje impossíveis, sem tocar em mecânica de loja.

---

## 2. Ligações de dado que faltam

O dado existe dos dois lados; falta o campo que liga um no outro.

- [ ] 🔍 **Sprites nas espécies.** 1.174 ícones 2D recortados em
      `apk/_extracted/out/sprites/`, e o campo `sprite` das 1.338 espécies está
      vazio. É uma rodada de script — **maior retorno por esforço da lista.**
- [ ] 🔍 **Modelos 3D nas espécies.** 623 modelos importados, mas `EspecieData`
      **não tem campo de modelo**. Exige mudar o script do Higor — combinar antes.
- [ ] 🔍 **Características de golpe.** `Bala` e `Som` existem e estão em zero
      golpes. O APK tem essas flags (`IsBallOrBomb`, `IsSound`, `IsPunch`,
      `IsBiting`, `IsPowder`, `IsTouch`, `IsAura`) nos 514 golpes gerados.
- [ ] 🔍 **Sprites de batalha.** ~12.435 arquivos numéricos em
      `YAPU_Demo/extracted/Sprite/resources.assets/` que **presumo** serem os
      sprites de batalha. O mapeamento para o número da dex **não foi
      confirmado** — é o primeiro passo antes de qualquer uso.

---

## 3. O jogo simula e não mostra

📋 Lista do Higor. É o grupo mais barato e o que mais muda a sensação de jogar.

- [ ] Clima e terreno **da batalha** na UI (hoje a tela mostra os do mundo, que
      são outros)
- [ ] Efeito de campo instalado é invisível até machucar alguém
- [ ] Ficha do Pokémon sem natureza, IV/EV, XP em número nem amizade
- [ ] Habilidade sem campo de texto no prefab — existe e fica em silêncio
- [ ] Pokédex sem stats base, habilidades possíveis nem learnset —
      🔍 **o dado agora existe, falta só exibir**
- [ ] `TravaDeAcao` invisível: o Pokémon para de aceitar ordem e a tela não explica
- [ ] `RegistroDaBatalha` existe desde 03/09 e nada o mostra

---

## 4. Conteúdo

- [ ] 📋 **Áudio: zero arquivos.** O sistema inteiro existe e está ligado onde há
      evento. Falta o som.
- [ ] 📋🔍 **Um NPC, um treinador, uma área de encontro, tudo numa cena.**
      `SistemaTransicao`, clima e encontros por contexto foram desenhados para
      uma variedade que ainda não existe.
- [ ] 📋 **8 Pokébolas sem identidade** — mesmo nome e mesmo preço.
- [ ] 🔍 **872 assets que só o catálogo conhece** — existem, estão corretos, e o
      jogador nunca encontra. Caiu de 1.458 ao ligar as evoluções; o resto
      depende de povoar tabelas de encontro.

**Já resolvido nesta sessão** (a lista do Higor de 05/09 dizia "zero"):
animação de gameplay — 12 clipes do Mixamo com retargeting Humanoid.

---

## 5. Sistemas ainda não atacados

- [ ] **Batalha 2D** — a tela. O motor está pronto e testado (dano com tipo,
      STAB, crítico, clima, estágios; status; IA com 6 perfis; captura validada
      em 200 mil simulações).
- [ ] 📋 **Rede.** Falta repor a foto do estado (`Fotografar()` só tira), o
      transporte e o árbitro remoto. E escrever "não sincronizar tudo" **antes**
      do primeiro `NetworkBehaviour`.
- [ ] **Troca de forma em jogo.** Mega existe como dado; nada dispara em partida.
- [ ] 📋 **Nenhuma medição de desempenho e nenhuma meta**, apesar do alvo
      declarado de 2 a 15–18 jogadores.

---

## 6. Evoluções que não mapearam

🔍 370 evoluções por nível foram ligadas. Estas ficaram de fora, e cada grupo
tem um motivo diferente:

| Casos | Motivo | Saída |
|---:|---|---|
| **235** | Mudariam o slot de habilidade de comum para oculta — regra do projeto: evoluir não promove nem rebaixa o indivíduo | Conversa com o Higor; os dados do APK discordam entre espécie e evolução |
| **57** | Mega / Primal — aqui é **troca de forma**, com sistema próprio. Virar evolução faria megaevoluir de vez, sem voltar | Usar o sistema de forma |
| **38** | Só exigem material de loja, sem nível | **Trocar por `ExigeAmizade`** — é como funciona no original (Pichu→Pikachu, Golbat→Crobat, Cleffa→Clefairy…) |

Também sem equivalente no projeto, e sem dado no APK: período do dia
(`DayTime` está `-1` em todas as 1.331 linhas), amizade mínima e golpe
conhecido (colunas existem, zero linhas preenchidas).

---

## 7. Débito nosso

🔍 Coisas que não são "falta implementar", são risco acumulado:

- [ ] **O código vindo da extração não tem um único teste.** O projeto tem 243
      verdes; o nosso, zero. E ele vive em `Assembly-CSharp`, fora das assembly
      definitions — logo fora da disciplina de teste também. Foi a suíte do
      Higor que achou dois defeitos meus que eu não teria visto.
- [ ] **Duas formas de autorar o mundo.** Ele posiciona à mão; a extração gera
      por script. Funcionou neste merge porque o nosso é regenerável, mas todo
      merge futuro reencosta aí. Vale combinar quem manda em quê.
- [ ] **`CatalogoJogo` carrega 1.338 espécies no boot.** São 7,8 MB em disco,
      referenciados direto pelo `Sistemas.prefab`. Funciona hoje; vai incomodar
      quando cada espécie tiver sprite e modelo pendurados. A saída padrão é
      **Addressables** — carregar por id, sob demanda.
- [ ] **Licença dos assets 2D.** Os sprites vêm da demo do YAPU, fan project com
      licença própria, e o repositório do Higor é **público**. Decisão dos dois
      antes de versionar.

---

## Ordem sugerida

1. **Sprites nas espécies** — uma rodada de script, transforma a Pokédex inteira
2. **Fontes de amizade** — pequeno, e destrava 38 evoluções sem gacha
3. **Características de golpe** — o dado já está nos 514 golpes gerados
4. **Mostrar o que já se simula** (seção 3) — barato, e é o que muda a sensação
5. **Confirmar o mapeamento dos sprites de batalha** — antes de qualquer batalha 2D
