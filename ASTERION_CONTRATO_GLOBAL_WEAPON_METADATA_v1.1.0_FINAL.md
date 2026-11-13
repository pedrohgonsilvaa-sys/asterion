# ASTERION — Contrato Global de Weapon Metadata

## v1.1.0 FINAL

**Data de consolidação:** 2026-10-17 (v1.0.0) · revisão v1.1.0 de 2026-11-13
**Escopo:** contrato global de Game Design para `weapon_family`, `weapon_form`, `handedness`, slot eligibility e compatibility tags de armas de personagem jogador.
**Autoridade estrutural de base:** `ASTERION_GDD_Estrutural_v1.7.0_Fonte_Mestra.md`.
**Fontes de conteúdo consultadas:** Fontes Regionais FINAL vigentes de Terras do Ocaso, Vales dos Enforcados, Planícies de Nareth, Várzeas Carmesins, Altos Cinéreos e Confins do Véu.
**Fontes visuais consultadas apenas para não-confusão de escopo:** Fonte Mestra Visual v2.6.4 e Catálogo PLAYER_CLASS RC4.1.

> Este documento é Game Design / System Design. Não define schema, tabela, migration, classe, enum de linguagem de programação nem arquitetura de software.

> Este documento NÃO restaura a taxonomia histórica de 14 famílias e NÃO autoriza inferência por nome, Classe, família histórica, aparência, animação, asset visual ou arma mostrada em uma skin.

> Quando este contrato for formalmente registrado no índice autoritativo do Projeto, ele complementa o GDD v1.7.0 especificamente no fechamento de metadata de arma. A semântica preexistente do GDD — requisitos declarados pela Arte, 2H bloqueando Secundária e compatibilidade explícita por item — permanece integralmente preservada.

> **Registro da v1.1.0 (2026-11-13):** Proficiência de equipagem passa a ser um eixo separado, declarado por item e definido no GDD v1.7.0 §24.2; Escudo é equipamento não-arma de Secundária; lista `compatibility_tags` vazia explícita é válida; Confins do Véu entra no mapeamento (§9.7, 27 armas nas Regiões 1–6). A tabela de requisitos das Artes e a semântica das tags não mudam. Os 12 Cajados/Bastões regionais candidatos (lista vazia aprovada) e os IDs candidatos da Fase 2E **não** entram no mapeamento até a conciliação com o snapshot de release.

---

# 0. Resultado executivo

```text
WEAPON_METADATA_MODEL =
  DESCRIPTIVE_FORM
  + EXPLICIT_HANDEDNESS
  + EXPLICIT_SLOT_ELIGIBILITY
  + EXPLICIT_COMPATIBILITY_TAGS

WEAPON_FAMILY_STORED = NO
WEAPON_FAMILY_VALUES = N/A

WEAPON_FORM_STORED = YES
WEAPON_FORM_VALUES =
  weapon.form.sword
  weapon.form.dagger
  weapon.form.axe
  weapon.form.hammer
  weapon.form.mace
  weapon.form.spear
  weapon.form.bow
  weapon.form.crossbow
  weapon.form.staff
  weapon.form.rod

HANDEDNESS_VALUES =
  weapon.hands.one
  weapon.hands.two

SLOT_RULES =
  weapon.slot.main_only
  weapon.slot.secondary_only
  weapon.slot.main_two_handed

COMPATIBILITY_TAG_MODEL =
  EXPLICIT_PER_ITEM
  weapon.compat.melee
  weapon.compat.bow
  weapon.compat.crossbow

CLASS_WEAPON_RULES =
  EQUIPMENT_PROFICIENCY_IS_SEPARATE_AXIS (GDD v1.7.0 §24.2)
  ART_REQUIREMENTS_ONLY

ART_WEAPON_REQUIREMENT_MODEL =
  NONE
  TAG_ANY_OF(...)

NON_WEAPON_ITEM_POLICY =
  WEAPON_METADATA_NA_BY_DEFAULT

LEGACY_ITEM_POLICY =
  EXACT_CANONICAL_MAPPING_OR_UNMAPPED
  NEVER_INFER_BY_NAME_CLASS_OLD_FAMILY_OR_VISUAL

PLAYER_FACING_FIELDS =
  Nome
  Slot
  Forma
  Mãos
  Compatibilidade de Artes
```

---

# 1. `weapon_family`

## 1.1 Decisão

**WEAPON_FAMILY_STORED = NO**

`weapon_family` não existe como conceito canônico persistível de Game Design no modelo vigente.

A taxonomia histórica de 14 famílias não é restaurada, não é autoridade e não pode ser usada como fonte automática para compatibilidade, mãos, slot, Classe, Arte ou form.

## 1.2 Conceitos que substituem sua função

As responsabilidades são separadas em quatro eixos ortogonais:

1. **`weapon_form`** — descreve a forma física/player-facing.
2. **`handedness`** — declara quantas mãos o item ocupa.
3. **slot eligibility** — declara em qual slot o item pode ser equipado.
4. **compatibility tags** — declaram quais predicados de armamento o item satisfaz para Artes.

A palavra **“família”** usada no Crafting global — Principal, Secundária, 2H, Cabeça, Torso, Mãos, Pés — continua significando agrupamento de Receita/slot/economia. Ela NÃO passa a significar `weapon_family`.

## 1.3 Consequência

Nenhuma regra pode fazer:

```text
family -> form
family -> handedness
family -> slot
family -> compatibility
family -> Class
family -> Art
```

porque `weapon_family` não existe no contrato canônico.

---

# 2. `weapon_form`

## 2.1 Semântica

`weapon_form` é uma **classificação descritiva controlada da forma física da arma**.

É:

- descritiva;
- player-facing;
- útil para nome, lore, UI, pixel art e apresentação;
- metadata estável da definição canônica do item.

Não é:

- proficiência;
- categoria de dano;
- requisito de Classe;
- requisito de Caminho;
- requisito de Arte;
- handedness;
- slot;
- compatibilidade;
- modificador de atributos;
- regra automática de loot ou Crafting.

`weapon_form` permanece classificação física descritiva. A **Proficiência de equipagem** é um requisito separado, declarado pela definição do item quando aplicável. Não existe regra automática forma→Proficiência. A Proficiência apenas permite equipar e não altera atributos, dano, Artes ou compatibility tags.

## 2.2 Uso por sistemas

| Uso | Contrato |
|---|---|
| Mecânica de combate | Não diretamente |
| Artes | Não diretamente |
| UI de equipamento | Sim |
| Visual/pixel art | Sim |
| Lore/nome | Sim |
| Loot | Pode ser exibido/filtrado, mas não altera elegibilidade/potência por si |
| Crafting | Pode ser exibido no resultado, mas não altera Receita/custo por si |
| Classe/Caminho | Nunca inferidos de `weapon_form` |

Se no futuro uma Arte precisar especificamente de uma forma, a Fonte da Arte deverá publicar **compatibility tag explícita** correspondente. A Arte não consulta `weapon_form` como atalho mecânico.

## 2.3 Obrigatoriedade

O GDD v1.6.0 permitia o subtipo/forma como informação descritiva opcional. Este contrato fecha a lacuna de conteúdo:

> **Toda arma player-equippable canônica definida a partir deste contrato deve possuir `weapon_form` não nulo.**

Para itens não-arma, usa-se **N/A**.

## 2.4 Enumeração fechada vigente

| ID | Player-facing | Definição |
|---|---|---|
| `weapon.form.sword` | Espada | lâmina de espada, independentemente de tamanho; não implica mãos nem slot |
| `weapon.form.dagger` | Adaga | lâmina curta de punho; não implica Secundária |
| `weapon.form.axe` | Machado | cabeça cortante montada em cabo; não implica 1H/2H |
| `weapon.form.hammer` | Martelo | cabeça de impacto predominantemente martelo; não implica 2H |
| `weapon.form.mace` | Maça | cabeça de impacto compacta; não implica Classe defensiva |
| `weapon.form.spear` | Lança | arma de ponta em haste; não implica 1H/2H |
| `weapon.form.bow` | Arco | plataforma física de arco; não implica compatibilidade sem tag explícita |
| `weapon.form.crossbow` | Besta | plataforma física de besta; não implica compatibilidade sem tag explícita |
| `weapon.form.staff` | Cajado | haste longa usada como arma/objeto físico; não implica magia |
| `weapon.form.rod` | Bastão | bastão curto/médio usado como arma/objeto físico; não implica magia |

A lista é fechada para esta versão. Nova forma exige revisão versionada deste contrato ou de autoridade que explicitamente o substitua.

**Foco visual/mágico não é automaticamente `weapon_form`.** Uma Fonte futura pode criar um item de Foco como equipamento, mas isso exigirá contrato próprio de slot/compatibilidade; não nasce do asset visual.

---

# 3. `handedness`

## 3.1 Valores oficiais

| ID | Player-facing | Semântica |
|---|---|---|
| `weapon.hands.one` | 1 mão | ocupa uma mão lógica; slot exato continua sendo declarado separadamente |
| `weapon.hands.two` | 2 mãos | equipado na Arma Principal e bloqueia Arma Secundária |

Não existem, nesta versão, valores canônicos de handedness chamados:

- `off-hand`;
- `dual-compatible`;
- `versatile`;
- `free-hand`.

Esses conceitos não são “mãos”; quando necessários, pertencem ao contrato de slot/eligibilidade.

## 3.2 Regra de declaração

**Handedness é explícito por item.**

Não pode ser derivado de:

- nome;
- `weapon_form`;
- `weapon_family`;
- Classe;
- aparência;
- tamanho da arte;
- palavra “Pesada”;
- arma mostrada em asset visual.

Uma Espada pode ser 1H ou 2H em conteúdo futuro se a Fonte declarar.
Uma Lança pode ser 1H ou 2H se a Fonte declarar.
Uma Besta pode ser 1H ou 2H se a Fonte declarar.

A lista vigente abaixo resolve cada arma atual sem inferência.

---

# 4. Slots

## 4.1 Slots globais preservados

O contrato não cria novo slot. Os slots de arma continuam:

- **Arma Principal**;
- **Arma Secundária**.

A regra especial de **Arma 2H** permanece: ocupa Principal e bloqueia Secundária.

## 4.2 Slot eligibility de arma

| ID conceitual | Semântica |
|---|---|
| `weapon.slot.main_only` | só pode ser equipada em Arma Principal |
| `weapon.slot.secondary_only` | só pode ser equipada em Arma Secundária |
| `weapon.slot.main_two_handed` | equipa em Principal, ocupa 2H e bloqueia Secundária |

Esses IDs são contrato de conteúdo, não prescrição de schema.

## 4.3 Regras fechadas

- Slot é independente de `weapon_form`.
- Slot é independente de compatibility tag.
- **1H NÃO significa “pode ir em qualquer mão”.**
- Uma arma 1H Principal não pode ser colocada em Secundária só por ser 1H.
- Uma arma 1H Secundária não pode ser colocada em Principal só por ser 1H.
- Não existe, nesta versão, elegibilidade genérica `main_or_secondary`.
- Não existe regra global de dual wield.
- Arma 2H continua declarada em Principal, usa `weapon.hands.two` e bloqueia Secundária; Secundária deve ficar vazia com Principal 2H.
- **Escudo** é equipamento não-arma de Secundária e exige a Proficiência Escudo. Não recebe `weapon_form`, `handedness` nem compatibility tags, é incompatível com Principal 2H e não concede Bloqueio inerente nem satisfaz requisito de Arte pela própria existência.
- Estas regras não alteram a elegibilidade cruzada explícita das armas de uma mão nem criam dual wield.
- 2H sempre usa `weapon.hands.two + weapon.slot.main_two_handed`.
- Ao equipar 2H, Secundária deve ficar vazia pelas regras globais; o item antes equipado em Secundária não fica “oculto”.

---

# 5. Compatibility tags

## 5.1 Modelo

Compatibility tags são **capacidades mecânicas explícitas do item para satisfazer `weapon_requirement` de uma Arte**.

São independentes de:

- form;
- handedness;
- slot;
- nome;
- Classe;
- Caminho;
- aparência;
- animação.

## 5.2 Tags vigentes

| ID | Semântica |
|---|---|
| `weapon.compat.melee` | satisfaz requisito “Arma corpo a corpo compatível” |
| `weapon.compat.bow` | satisfaz ramo Arco do requisito “Arco ou Besta compatível” |
| `weapon.compat.crossbow` | satisfaz ramo Besta do requisito “Arco ou Besta compatível” |

Não há tag de Classe.

Não há tag de “arma mágica”.

Não há tag de “Sentinela”, “Errante”, “Vigia”, “Tecelão”, “Oráculo” ou “Luminar”.

Não há tag derivada automaticamente do `weapon_form`.

## 5.3 Avaliação

A exigência de uma Arte é satisfeita quando **ao menos uma arma atualmente equipada em slot legal** possui uma tag aceita pela regra da Arte.

Exemplos:

```text
Arma corpo a corpo compatível
= TAG_ANY_OF{weapon.compat.melee}

Arco ou Besta compatível
= TAG_ANY_OF{weapon.compat.bow, weapon.compat.crossbow}

Nenhum
= NONE
```

Se Principal e Secundária estiverem ambas equipadas, uma tag válida em qualquer uma das armas pode satisfazer o requisito.

Arma desconhecida ou sem tag explícita **não satisfaz** requisito específico.

## 5.4 Proibição de inferência

É inválido fazer:

```text
if form == bow -> add weapon.compat.bow
if form == dagger -> add weapon.compat.melee
if Class == Vigia -> weapon is compatible
if name contains "Arco" -> add tag
if old_family == X -> add tags
```

Mesmo quando a tabela canônica atual possua combinações intuitivas, a compatibilidade é verdadeira porque **esta Fonte a declarou**, não porque foi deduzida.

## 5.5 Lista vazia, campo ausente e null

Quando a definição de uma arma exigir declaração explícita de `compatibility_tags`, a lista vazia `[]` é uma declaração válida de conjunto sem tags. Ela significa que o item não satisfaz requisito de Arte baseado em tag e não funciona como curinga.

Campo ausente e valor `null` são metadata incompleta e não equivalem à lista vazia. São inválidos quando a declaração explícita for exigida pelo contrato. A política de item legado sem correspondência exata permanece a §10; não se converte metadata ausente em declaração vazia.

---

# 6. Relação com Classes

Não existe Proficiência de arma inferida pela forma ou pela Arte. A Proficiência de equipagem é requisito do item e vem da matriz de Proficiências naturais por Classe do GDD v1.7.0 §24.2; Raça e Caminho não concedem Proficiências naturais. As regras de tags de Artes abaixo permanecem inalteradas.

| Classe | Proficiência de equipagem | Regra funcional vigente |
|---|---|---|
| Sentinela | Proficiências naturais conforme GDD v1.7.0 §24.2 | Artes físicas publicadas que exigem arma usam `weapon.compat.melee`; Artes defensivas sem requisito continuam `NONE` |
| Errante | Proficiências naturais conforme GDD v1.7.0 §24.2 | Artes físicas publicadas que exigem arma usam `weapon.compat.melee`; Artes sem golpe de arma continuam `NONE` |
| Vigia | Proficiências naturais conforme GDD v1.7.0 §24.2 | Artes de disparo publicadas exigem `weapon.compat.bow` ou `weapon.compat.crossbow`; Artes sem disparo podem ser `NONE` |
| Tecelão | Proficiências naturais conforme GDD v1.7.0 §24.2 | Todas as Artes vigentes publicadas têm `weapon_requirement = NONE` |
| Oráculo | Proficiências naturais conforme GDD v1.7.0 §24.2 | Todas as Artes vigentes publicadas têm `weapon_requirement = NONE` |
| Luminar | Proficiências naturais conforme GDD v1.7.0 §24.2 | Todas as Artes vigentes publicadas têm `weapon_requirement = NONE` |

Consequências deliberadas:

- Sentinela ou Errante podem possuir/equipar arma ranged quando todos os demais requisitos de equipamento permitirem; suas Artes que exigem melee ficam indisponíveis enquanto nenhuma arma equipada tiver `weapon.compat.melee`.
- Vigia pode possuir/equipar arma melee; suas Artes de disparo ficam indisponíveis enquanto nenhuma arma equipada tiver `weapon.compat.bow` ou `weapon.compat.crossbow`.
- Tecelão, Oráculo e Luminar não recebem restrição de arma implícita por Arte; suas Proficiências de equipagem seguem a matriz do GDD v1.7.0 §24.2.
- Uma skin de Classe mostrando espada, martelo, bastão, cajado, arco, besta ou foco **não cria loadout mecânico**.

---

# 7. Relação com Artes

## 7.1 Modelo oficial

```text
ART_WEAPON_REQUIREMENT_MODEL =
  NONE
  | TAG_ANY_OF(set explícito de compatibility tags)
```

Cada Arte declara sua própria regra.

O requisito não pode ser inferido da Classe ou do Caminho.

## 7.2 Requisitos vigentes

Há somente três estados funcionais necessários para as Artes atuais:

1. `NONE`;
2. `TAG_ANY_OF{weapon.compat.melee}`;
3. `TAG_ANY_OF{weapon.compat.bow, weapon.compat.crossbow}`.

Ter Proficiência de equipagem para uma arma não adiciona tags e não torna uma Arte utilizável se os equipamentos legais não satisfizerem o requisito daquela Arte. A tabela de requisitos das Artes atuais, os nomes das tags e a semântica de avaliação permanecem sem alteração.

## 7.3 Validação

A Configuração de Combate preserva o comportamento global:

- valida ao salvar/equipar Arte;
- revalida após mudança pertinente de Equipamento;
- valida antes de combate voluntário;
- valida no commit da ação;
- revalida após patch/recuperação pertinente.

Equipamento incompatível **não apaga a Arte**. A Configuração fica incompleta/inválida até o requisito voltar a ser satisfeito.

---

# 8. Itens não-arma

| Tipo | weapon_family | weapon_form | handedness | weapon.compat.* |
|---|---|---|---|---|
| Escudo | N/A | N/A | N/A | nenhuma por padrão |
| Foco | N/A | N/A | N/A | nenhuma por padrão |
| Acessório | N/A | N/A | N/A | nenhuma |
| Artefato | N/A | N/A | N/A | nenhuma |
| Cabeça | N/A | N/A | N/A | nenhuma |
| Torso | N/A | N/A | N/A | nenhuma |
| Mãos | N/A | N/A | N/A | nenhuma |
| Pés | N/A | N/A | N/A | nenhuma |
| Cosmético | N/A | N/A | N/A | nenhuma |

Observações:

- Um **escudo** é equipamento não-arma de Arma Secundária e exige a Proficiência Escudo (GDD v1.7.0 §24.1); isso não o torna arma corpo a corpo, não o inclui na tabela §9 e não cria compatibility tag.
- Um **foco** visual não é automaticamente item equipável.
- Se uma Arte futura exigir Escudo, Foco ou outra categoria não-arma, a Fonte da Arte deve criar requisito explícito apropriado. O presente contrato não inventa essa exigência.
- Equipamento defensivo e cosmético nunca herda weapon metadata por aparência.

---

# 9. Mapeamento canônico do conteúdo vigente

## 9.1 Escopo

Esta tabela cobre **todos os equipamentos de arma explicitamente publicados nas Fontes Regionais FINAL vigentes das Regiões 1–6**. Para Confins do Véu, ela incorpora somente os cinco registros explícitos de metadata publicados na §19.2 da Fonte Regional FINAL v1.0.0.

O Catálogo PLAYER_CLASS visual não adiciona armas mecânicas a esta lista.

Os `WEAPON_ID_OR_TYPE` abaixo são IDs estáveis de conteúdo deste contrato. Não prescrevem nome de tabela/campo de implementação.

## 9.2 Terras do Ocaso

| WEAPON_ID_OR_TYPE | Item | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `weapon.type.tdo.arma_caminhante` | Arma do Caminhante | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `weapon.type.tdo.guarda_caminhante` | Guarda do Caminhante | N/A | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.tdo.arma_pesada_caminhante` | Arma Pesada do Caminhante | N/A | `weapon.form.bow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.bow` |
| `weapon.type.tdo.guarda_primeiro_selo` | Guarda do Primeiro Selo | N/A | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

A forma/tags desta tabela são **novas decisões explícitas deste contrato**, não inferências pelo nome.

## 9.3 Vales dos Enforcados

| WEAPON_ID_OR_TYPE | Item | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `weapon.type.vde.arma_vale` | Arma do Vale | N/A | `weapon.form.axe` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `weapon.type.vde.guarda_enredada` | Guarda Enredada | N/A | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.vde.arma_pesada_lacos` | Arma Pesada dos Laços | N/A | `weapon.form.crossbow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.crossbow` |
| `weapon.type.vde.guarda_no_antigo` | Guarda do Nó Antigo | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

**Guarda do Berço Silente não entra nesta tabela:** a Fonte Regional a define como **Torso**, não arma.

## 9.4 Planícies de Nareth

| WEAPON_ID_OR_TYPE | Item | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `weapon.type.nareth.arma_meridiano` | Arma do Meridiano | N/A | `weapon.form.spear` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `weapon.type.nareth.guarda_marco` | Guarda de Marco | N/A | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.nareth.arma_pesada_horizonte` | Arma Pesada do Horizonte | N/A | `weapon.form.bow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.bow` |
| `weapon.type.nareth.guarda_camara_invertida` | Guarda da Câmara Invertida | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.nareth.guarda_referencia` | Guarda da Referência | N/A | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

## 9.5 Várzeas Carmesins

| WEAPON_ID_OR_TYPE | Item | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `weapon.type.varzeas.arma_dique` | Arma do Dique | N/A | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `weapon.type.varzeas.guarda_salmoura` | Guarda de Salmoura | N/A | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.varzeas.arma_pesada_transferencia` | Arma Pesada de Transferência | N/A | `weapon.form.crossbow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.crossbow` |
| `weapon.type.varzeas.guarda_transferencia` | Guarda de Transferência | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

## 9.6 Altos Cinéreos

O patch v1.0.1 de Altos corrige exclusivamente o contrato de unlock de Locais; o catálogo de Equipamentos permanece o publicado no fechamento regional.

| WEAPON_ID_OR_TYPE | Item / fonte | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `weapon.type.altos.arma_contrapeso` | Arma do Contrapeso · `craft.altos.ferreiro.principal.arma_contrapeso` | N/A | `weapon.form.hammer` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `weapon.type.altos.guarda_escora` | Guarda de Escora · `craft.altos.ferreiro.secundaria.guarda_escora` | N/A | `weapon.form.axe` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `weapon.type.altos.arma_pesada_pedreira` | Arma Pesada da Pedreira · `craft.altos.ferreiro.2h.arma_pedreira` | N/A | `weapon.form.crossbow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.crossbow` |
| `equipment.altos.campaign.p30.guarda_contraforte_final` | Guarda do Contraforte Final | N/A | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `equipment.altos.special.guarda_ordem_profunda` | Guarda da Ordem Profunda | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

## 9.7 Confins do Véu

Transcrito de Confins do Véu v1.0.0 FINAL, §19.2.

| WEAPON_ID_OR_TYPE | Item / fonte | FAMILY | FORM | HANDEDNESS | SLOT | COMPATIBILITY_TAGS |
|---|---|---|---|---|---|---|
| `craft.confins.ferreiro.principal.lamina_baliza` | Lâmina de Baliza | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `craft.confins.ferreiro.secundaria.guarda_marcha` | Guarda da Marcha | N/A | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `craft.confins.ferreiro.2h.arco_retorno` | Arco do Retorno | N/A | `weapon.form.bow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.bow` |
| `equipment.confins.campaign.p36.guarda_ultimo_protocolo` | Guarda do Último Protocolo | N/A | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `equipment.confins.special.guarda_duas_versoes` | Guarda das Duas Versões | N/A | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

Os IDs são os publicados pela Fonte Regional; nenhum alias é criado. Os nomes de exibição seguem a Fonte Regional de Confins do Véu v1.0.0.

## 9.8 Auditoria do mapeamento

Total de armas player-equippable publicadas e mapeadas neste contrato: **27** (22 + 5).

Distribuição:

- Terras do Ocaso: 4;
- Vales dos Enforcados: 4;
- Planícies de Nareth: 5;
- Várzeas Carmesins: 4;
- Altos Cinéreos: 5;
- Confins do Véu: 5.

Todo item possui explicitamente:

- form;
- handedness;
- slot eligibility;
- compatibility tags.

Nenhum depende de inferência.

---

# 10. Conteúdo legado

## 10.1 Política escolhida

**LEGACY_ITEM_POLICY = D — EXACT_CANONICAL_MAPPING_OR_UNMAPPED**

Não será feito backfill semântico por texto/família histórica.

## 10.2 Regra

Um equipamento criado antes deste contrato pode receber o metadata vigente **somente quando sua identidade de conteúdo for comprovadamente a mesma de uma entrada canônica da tabela da seção 9**.

Mapeamento permitido:

```text
identidade canônica exata conhecida
-> entrada exata da seção 9
-> metadata exato da mesma linha
```

Proibido:

```text
nome parecido -> mapear
old_family -> mapear
Classe do dono -> mapear
slot histórico -> adivinhar form/tag
asset visual -> mapear
aparência -> mapear
"sempre foi assim no código" -> mapear
```

## 10.3 Legado sem correspondência

Se um ID técnico histórico não possui correspondência unívoca com uma entrada da seção 9:

**LEGACY_WEAPON_STATUS = UNMAPPED**

Sem correspondência canônica:

- não recebe form por aproximação;
- não recebe handedness por aproximação;
- não recebe compatibility tag;
- não pode ser considerado capaz de satisfazer `weapon_requirement`;
- não vira cânone por existir no banco/código;
- deve ser reportado ao Game Design como identidade de conteúdo a reconciliar caso precise continuar vigente.

Se estiver presente em estado recuperado, o item continua sendo propriedade do personagem; porém a Configuração que dependa dele como arma válida não pode ser considerada completa até existir correspondência canônica inequívoca. Este contrato não prescreve como bytes/linhas devem ser migrados ou armazenados.

## 10.4 Taxonomia histórica

As 14 famílias históricas:

- não recebem tabela de conversão;
- não são alias canônico;
- não podem ser usadas para inferir os quatro eixos vigentes;
- só podem ser consultadas pela engenharia como evidência histórica para localizar possíveis IDs, nunca como autoridade do resultado.

---

# 11. Persistência — contrato sem schema

A classificação abaixo descreve o que precisa existir de modo autoritativo e recuperável; não obriga campo/coluna específica.

```text
WEAPON_FAMILY_PERSISTENCE = NOT_STORED

WEAPON_FORM_PERSISTENCE = REQUIRED
  Fonte canônica: definição vigente do weapon item/type.
  Não é estado mutável por item_instance.

HANDEDNESS_PERSISTENCE = DERIVED
  Fonte canônica da derivação: definição vigente exata do weapon item/type.
  Nunca derivar de form/nome/família histórica.

COMPATIBILITY_TAGS_PERSISTENCE = DERIVED
  Fonte canônica da derivação: definição vigente exata do weapon item/type.
  Nunca derivar de form/nome/Classe/aparência.

SLOT_ELIGIBILITY_PERSISTENCE = DERIVED
  Fonte canônica da derivação: definição vigente exata do weapon item/type.
```

### Interpretação de `WEAPON_FORM_PERSISTENCE = REQUIRED`

“Required” significa que toda definição canônica de arma precisa carregar uma forma inequívoca e recuperável. Não significa que Game Design exige duplicar o valor mutável dentro de cada instância se a implementação já possui referência estável à definição de conteúdo.

---

# 12. Player-facing

Na ficha/detalhe de uma arma, além dos campos de Equipamento globais já existentes, exibir:

1. **Nome**;
2. **Slot** — Principal / Secundária / Duas Mãos;
3. **Forma** — player-facing de `weapon_form`;
4. **Mãos** — `1 mão` ou `2 mãos`;
5. **Compatibilidade de Artes**:
   - Corpo a corpo;
   - Arco;
   - Besta;
   - ou combinação explícita futura.

Não exibir raw IDs ao jogador.

Não exibir “Família de Arma”, pois `weapon_family` não existe.

Não exibir “Classe permitida” quando não houver restrição explícita.

Quando uma Arte estiver bloqueada por armamento, o feedback deve informar o requisito funcional ausente, como já exige o GDD.

---

# 13. Validação de consistência

## 13.1 Family × Form

Aprovado.

`weapon_family` não existe, portanto não pode contradizer nem comandar `weapon_form`.

## 13.2 Form × Handedness

Aprovado.

Nenhum form possui handedness implícito. A tabela da seção 9 declara cada combinação individualmente.

## 13.3 Handedness × Slot

Aprovado.

- toda 1H atual declara `main_only` ou `secondary_only`;
- toda 2H atual declara `main_two_handed`;
- nenhuma 1H recebe acesso automático ao slot oposto.

## 13.4 Form × Compatibility

Aprovado.

A compatibilidade está repetida explicitamente por item. Mesmo uma relação intuitiva como `bow + weapon.compat.bow` é declaração, não regra derivada.

## 13.5 Classes

Aprovado.

Proficiências de equipagem seguem a matriz do GDD v1.7.0 §24.2; nenhuma Classe recebe compatibility tag por isso.

## 13.6 Artes

Aprovado.

As regras vigentes cabem em `NONE` ou `TAG_ANY_OF`. Nenhuma Arte atual exige family/form diretamente.

## 13.7 Itens não-arma

Aprovado.

Escudos, focos, armaduras, acessórios, artefatos e cosméticos não recebem weapon metadata por aparência ou slot.

## 13.8 Legado

Aprovado.

Existe política fechada para IDs conhecidos e desconhecidos, sem inferência textual ou histórica.

## 13.9 Conteúdo atual

Aprovado.

As 27 armas publicadas nas Fontes Regionais FINAL vigentes das Regiões 1–6 estão mapeadas integralmente na seção 9, incluindo os cinco registros de Confins do Véu da §9.7.

IDs de arma existentes apenas em código histórico e não publicados pelas Fontes **não são “arma vigente” por esse fato**. Permanecem legado não canônico até correspondência explícita.

---

# 14. Contrato final

```text
WEAPON_METADATA_MODEL =
  DESCRIPTIVE_FORM
  + EXPLICIT_HANDEDNESS
  + EXPLICIT_SLOT_ELIGIBILITY
  + EXPLICIT_COMPATIBILITY_TAGS

WEAPON_FAMILY_STORED = NO
WEAPON_FAMILY_VALUES = N/A

WEAPON_FORM_STORED = YES
WEAPON_FORM_NULL_FOR_CANONICAL_WEAPON = NO
WEAPON_FORM_VALUES =
  weapon.form.sword
  weapon.form.dagger
  weapon.form.axe
  weapon.form.hammer
  weapon.form.mace
  weapon.form.spear
  weapon.form.bow
  weapon.form.crossbow
  weapon.form.staff
  weapon.form.rod

HANDEDNESS_VALUES =
  weapon.hands.one
  weapon.hands.two

SLOT_RULES =
  weapon.slot.main_only
  weapon.slot.secondary_only
  weapon.slot.main_two_handed
  2H_BLOCKS_SECONDARY = YES
  ONE_HANDED_CROSS_SLOT_INFERENCE = NO

COMPATIBILITY_TAG_MODEL =
  EXPLICIT_PER_ITEM
  weapon.compat.melee
  weapon.compat.bow
  weapon.compat.crossbow

CLASS_WEAPON_RULES =
  GLOBAL_CLASS_PROFICIENCY_AS_ART_GATE = NONE
  SENTINELA = ART_REQUIREMENTS_ONLY
  ERRANTE = ART_REQUIREMENTS_ONLY
  VIGIA = ART_REQUIREMENTS_ONLY
  TECELAO = NO_CURRENT_WEAPON_REQUIREMENT
  ORACULO = NO_CURRENT_WEAPON_REQUIREMENT
  LUMINAR = NO_CURRENT_WEAPON_REQUIREMENT

ART_WEAPON_REQUIREMENT_MODEL =
  NONE
  TAG_ANY_OF(tags_explicitly_published)

NON_WEAPON_ITEM_POLICY =
  WEAPON_FAMILY = N/A
  WEAPON_FORM = N/A
  HANDEDNESS = N/A
  COMPATIBILITY_TAGS = NONE
  UNLESS_FUTURE_SOURCE_EXPLICITLY_DEFINES_OTHERWISE

LEGACY_ITEM_POLICY =
  EXACT_CANONICAL_MAPPING_OR_UNMAPPED
  NO_NAME_INFERENCE
  NO_CLASS_INFERENCE
  NO_OLD_FAMILY_INFERENCE
  NO_VISUAL_INFERENCE

WEAPON_FAMILY_PERSISTENCE = NOT_STORED
WEAPON_FORM_PERSISTENCE = REQUIRED
HANDEDNESS_PERSISTENCE = DERIVED_FROM_CANONICAL_ITEM_DEFINITION
COMPATIBILITY_TAGS_PERSISTENCE = DERIVED_FROM_CANONICAL_ITEM_DEFINITION

PLAYER_FACING_FIELDS =
  Nome
  Slot
  Forma
  Mãos
  Compatibilidade de Artes

EQUIPMENT_PROFICIENCY_REQUIRED = DECLARADA POR ITEM QUANDO APLICÁVEL
EQUIPMENT_PROFICIENCY_FROM_WEAPON_FORM = NO
ART_REQUIREMENT_FROM_EQUIP_PROFICIENCY = NO
COMPATIBILITY_TAGS_EMPTY_LIST = VALID_EXPLICIT_EMPTY_SET
COMPATIBILITY_TAGS_ABSENT_OR_NULL = INVALID_WHEN_EXPLICIT_DECLARATION_REQUIRED
SHIELD = NON_WEAPON_SECONDARY_REQUIRES_PROFICIENCY_ESCUDO
TWO_HANDED_MAIN_BLOCKS_SECONDARY = YES

CURRENT_WEAPON_MAPPING =
  SECTION_9
```

---

# 15. Estado de Game Design

Não permanece arma vigente publicada nas Fontes atuais das Regiões 1–6 dependendo de inferência de:

- family;
- form;
- handedness;
- slot;
- compatibility.

Confins do Véu possui Fonte Regional FINAL v1.0.0. Os cinco registros de arma publicados em sua §19.2 estão relacionados na §9.7 deste contrato. A cobertura desta tabela passa a ser Regiões 1–6; nenhum dos demais itens ou IDs candidatos da Fase 2E é validado por esta revisão.

A taxonomia histórica de 14 famílias não é reativada.

A implementação deve sincronizar este contrato antes de reativar ou recuperar Character Progression dependente desses metadados.

**WEAPON_METADATA_DESIGN_STATUS = FINAL_IMPLEMENTABLE**
