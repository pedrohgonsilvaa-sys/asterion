# ASTERION — Revisão Técnica do Sistema de Combate, Armas e Equipamentos

**Versão do documento:** v1.0.0
**Data:** 2026-11-13
**Natureza:** revisão descritiva do estado **canônico** atual. Não propõe mudanças de design. Não altera nenhuma Fonte.
**Finalidade:** base técnica para redesenhar a identidade mecânica das armas sem criar mecânicas incompatíveis com o sistema atual.

> Regra de leitura: tudo que está aqui é o que as Fontes vigentes definem. Quando a Fonte não define algo, o texto diz **“Não definido na documentação atual.”** Nenhuma lacuna foi preenchida por inferência.

---

## 0. Fontes usadas e hierarquia

Hierarquia aplicada (conforme `SOURCE_AUTHORITY.md`, índice de 2026-11-12):

| Papel | Fonte | Uso neste documento |
|---|---|---|
| Autoridade estrutural (sistemas globais) | **GDD Estrutural v1.6.0 — Fonte Mestra** (`ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`) | Combate (§9–12), Artes (§8.3, §49.4, §56), Equipamentos (§24, §25, §49.8–49.9), Configuração de Combate (§39), Ronda (§18.2), Doutrinas (§8.5), Arma × Arte × Equipamento (§55.3) |
| Contrato global complementar | **Contrato Global de Weapon Metadata v1.0.0 FINAL** (`ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`, SHA-256 `c283b398…aa740`) | Modelo de metadata de arma, `weapon_form`, handedness, slot eligibility, compatibility tags, mapeamento das armas publicadas, legado |
| Regional (conteúdo) | Terras do Ocaso v1.0.17 FINAL; Vales dos Enforcados v1.0.6 FINAL; Planícies de Nareth v1.0.2 FINAL; Várzeas Carmesins v1.0.3 FINAL; Altos Cinéreos v1.0.1 FINAL; Confins do Véu v1.0.0 FINAL (§19.2) | Itens de arma publicados e suas declarações |
| Visual/direção (não mecânica) | Decisão visual de 06/10/2026 (arma-assinatura de Classe) | Apenas para registrar que **não** é regra mecânica |

**Excluídos deliberadamente** (não são autoridade para este documento):

- `balanceamento/` — marcado como **NÃO CANÔNICO** em seus próprios nomes de arquivo (ex.: proficiências v0.8.0 a v1.8.0).
- `docs/EQUIPAMENTOS_E_PROFICIENCIAS_ESTADO_ATUAL.md` — estado de implementação, não cânone.
- Versões superadas: GDD v1.4.x e v1.5.0; Bíblia Canônica v3.x (superada pela v4.0.7 para Lore).
- Propostas: `ASTERION_CRONICA_I_..._v0_2_PROPOSTA.md`, `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_PROPOSTA.md`.
- Fase 2E (candidata, não canônica).
- Taxonomia histórica de **14 famílias de arma**: não restaurada (Contrato §1, §10.4).

**Ponto de governança relevante:** o Contrato de Weapon Metadata foi consolidado em 2026-10-17, antes da Confins FINAL (2026-10-18). Ver seção 9.1.

---

## 1. Resumo executivo

- O combate é por turnos, com iniciativa por AGI, sem grid, sem distância e sem posição espacial.
- O dano é `ATQ × coeficiente`, reduzido por DEF pela fórmula global. **Uma arma não possui dano base, coeficiente, velocidade, alcance ou cadência próprios.** A arma contribui apenas com atributos (ex.: ATQ do núcleo de Principal) e com **compatibility tags**, que habilitam ou bloqueiam Artes.
- Arma tem quatro eixos independentes: `weapon_form` (descritivo), `handedness` (1H/2H), slot eligibility (Principal, Secundária ou 2H) e compatibility tags (`melee`, `bow`, `crossbow`).
- Não existe proficiência, maestria, árvore de arma, nem restrição global de arma por Classe.
- Não existe regra de dual wield, nem mecânica de arremesso, projeção, cone, cleave, retorno de projétil ou alcance.
- Armas e Artes se relacionam por `weapon_requirement`: `NONE` ou `TAG_ANY_OF(...)`, declarado pela Fonte de cada Arte.
- O sistema representa com objetividade: slots, mãos, compatibilidade binária, atributos, Runas, Encantamentos, Aprimoramento, Raridade, Grau e Artes com multi-hit ou AoE declarados por Arte.

---

## 2. Sistema de combate atual

### 2.1 Turnos e iniciativa (GDD §9.1)

- Combate é **por turnos**.
- Iniciativa global: maior AGI age primeiro, **uma vez por rodada**. Mudanças de AGI afetam a próxima rodada.
- Empate de AGI: prioridade determinística definida no início do combate pelo RNG do `combat_id`.
- Não há grid, distância física, linha de frente/trás ou movimentação espacial.
- “Melee” e “Ranged” são **tags/identidades mecânicas**, não posições.
- Não há friendly fire por padrão.

### 2.2 Atributos que participam do combate

| Atributo | Papel documentado |
|---|---|
| HP / HP Máximo | Vida; Barreira é HP temporário separado |
| ATQ | Base do dano bruto (`ATQ × coeficiente`), base de Cura e de DoT |
| DEF | Redução de dano direto pela fórmula global; base de DoT (50% da DEF efetiva) |
| AGI | Iniciativa; ritmo. Geada atua em AGI/ritmo (§10.5) |
| PER | Base 0%, cap 30%. Reduz DEF efetiva: `DEF_eff = max(0, DEF_mod × (1 − PER/100))` (§49.1). **A sigla PER não é expandida na Fonte.** |
| CRIT | Chance-base 5%; dano crítico-base 150%; PvP: cap 40% e dano crítico cap 200% |
| Esquiva | Base 0%; cap PvP 25% |
| Bloqueio | Base 0%; cap 30%; redução de 35% em “bloqueio válido” (ver 2.6, ponto não definido) |

Fontes: GDD §9.3, §49.1.

### 2.3 Fórmula base de dano (GDD §9.2)

1. Dano bruto: `ATQ × coeficiente`.
2. Redução por DEF: `DEF / [DEF + (100 + 5 × nível do atacante)]`.
3. Perfuração/-DEF entra **antes** da fórmula de DEF.
4. Precisão interna é alta; arredondamento só ao final da quantidade.
5. Dano final positivo usa `floor` e mínimo de 1 quando houve acerto válido, salvo imunidade/efeito que zere explicitamente.
6. Cura e Barreira usam `floor`, mínimo 0.
7. Overheal é descartado por padrão e não vira Barreira.

Ordem de resolução de um ataque (GDD §12.1):

`validação de ação/alvo → acerto/Esquiva → bruto → crítico → modificadores ofensivos → Perfuração/-DEF → DEF → Defender/Bloqueio/mitigação → Barreira → HP → Vampirismo → status/on-hit → derrotas/triggers`

### 2.4 Acerto e Esquiva

- Não há stat de acerto/precisão para jogador além do conceito “precisão interna é alta” (§9.2). A única chance de falha de acerto documentada é a **Esquiva**.
- Esquiva-base 0%. Após **2 Esquivas consecutivas**, o próximo ataque básico/ofensivo direto elegível contra aquele alvo não pode ser Esquivado.
- Ataques multi-hit: hits elegíveis são resolvidos golpe a golpe; cada hit pode critar separadamente (§11).

### 2.5 Crítico

- 5% de chance-base, dano crítico 150% (valores da Baseline v1.0, §9.3 e §49.1).
- DoTs e Curas **não critam** por padrão.
- Refletido não crita (§11).
- A forma exata de aplicação do multiplicador de crítico sobre o total não está detalhada além do valor “150%”.

### 2.6 Defender, Bloqueio e mitigação

- **Defender** (ação universal): reduz **45%** do Dano Direto até o próximo turno. Na Ruptura Final, reduz 30%. Não pode ser usado em oportunidades consecutivas em que foi de fato usado. Se um turno foi perdido por Stun sem Defender, a próxima oportunidade pode usá-lo.
- **Bloqueio**: stat com base 0%, cap 30%, e “redução em bloqueio válido” de 35% (§9.3).
  - **Não definido na documentação atual:** o que constitui um “bloqueio válido” (quais ataques podem ser bloqueados, sob quais condições e por qual origem). Não há regra que vincule Bloqueio a arma, escudo ou tipo de ataque.
- **Mitigação ativa multiplicativa:** cap de 65%, separado da redução natural por DEF (§9.3, §49.1).
- Defender e Bloqueio fazem parte da fase “Defender/Bloqueio/mitigação” da ordem de resolução.

### 2.7 Barreira, HP e Vampirismo

- Barreira é HP temporário. Barreiras de fontes diferentes coexistem até cap; em PvP, cap de 35% do HP Máximo.
- “Mesma fonte” = `applier_id + effect_definition_id`. Nova aplicação da mesma fonte substitui valor e duração.
- Vampirismo usa apenas dano direto real ao HP após mitigação/Barreira, sem overkill e sem DoT. Em AoE/multi-hit, agregado em um evento por ação.
- Não existe ressurreição em combate.

### 2.8 Tipos de dano (GDD §11)

Tipos **internos** formalmente definidos:

- Dano Direto
- DoT
- Dano de Reação
- Dano Refletido
- Dano Ambiental

Observações:

- Os termos “físico”, “mágico”, “Trama”, “Luz”, “rúnico” aparecem em descrições textuais de Artes (ex.: GDD §55.3, Golpe de Guarda “golpe físico direto”; Estilhaço do Véu “dano mágico”). **Não há regra mecânica que diferencie esses rótulos.** Não definido na documentação atual: diferença de cálculo, resistência ou interação entre “físico” e “mágico”.
- Perfuração/-DEF e PER são modificadores, não tipos de dano.

### 2.9 Ações, Artes, Recarga, duração e estados

**Ações disponíveis em combate:**

- **Ataque Básico:** 100% ATQ, Dano Direto, um inimigo, sem Recarga. Universal (§49.4).
- **Defender:** universal (§9.3).
- **Artes:** até **3 Artes Ativas** equipadas (§8.3). Ataque Básico e Defender não ocupam esses slots.
- **Consumível:** ação de combate quando elegível (§26).
- **Ação Preparada:** Arte em duas etapas (preparação/telegraph e resolução). Preparação consome a oportunidade atual e compromete a Recarga; resolução é continuação da mesma ação (§9.6).

**Recarga (cooldown):** avança por oportunidade de turno do proprietário; não há cooldown fracionário (§10.1, §10.2). Exemplo oficial: CD2 usada no T1 fica indisponível no T2 e volta no T3.

**Duração em T:** `NT` = próximas N oportunidades de turno do personagem afetado (§10.1).

**CC:** Stun consome a oportunidade. Não há stun-lock comum, silêncio total recorrente, medo, confusão ou taunt forçado (§10.5).

**Stacking:** regras gerais em §10.3; DoTs com caps próprios (Veneno 3, Sangramento 3, Queimadura 2) em §10.4.

**Recursos e marcas internas de Classe (GDD §56):** Retaliação (Sentinela), Oportunismo (Errante, condição contextual), Mira (Vigia), Trama (Tecelão), Presságio (Oráculo) e Fulgor/Julgamento (Luminar). São combat-scoped, não são Buffs/Debuffs e não atravessam `combat_id`.

**Não existem** na documentação: durabilidade de arma, munição, consumo de projétil, Vigor por ataque de arma (o Vigor é tratado em §17/§18 e não é específico de arma), “combo”, “postura de arma” ou “armas em estado ativo/inativo”.

**Não definido na documentação atual:** o custo, se existir, de trocar arma em combate além da regra geral de Configuração travada (§39.2).

### 2.10 AoE, multi-hit e triggers (GDD §11)

- Uma Arte pode declarar `hit_count`, `crit_per_hit`, `accuracy_per_hit` e escopo de triggers.
- Multi-hit: resolvido golpe a golpe.
- Triggers declaram `per_action`, `per_hit` ou `per_target`. Recursos pessoais são `per_action` por padrão.
- Seleção limitada de alvos usa critério determinístico ou RNG idempotente.
- AoE simultâneo usa estado pré-evento.

### 2.11 RNG

- Crítico, Esquiva, Bloqueio, desempate de AGI e IA aleatória são determinísticos/idempotentes, ligados a `combat_id + action_id + event_id` (§12.3).
- O cliente nunca controla seed.
- A IA PvE padrão **não usa RNG** (§9.6).

---

## 3. Sistema atual de armas

### 3.1 Classificação: quatro eixos ortogonais (Contrato §1–§5)

| Eixo | Campo canônico | Persistência | Função mecânica |
|---|---|---|---|
| `weapon_form` | Forma descritiva (10 valores fechados) | Obrigatória na definição canônica | **Nenhuma** diretamente |
| `handedness` | `weapon.hands.one` / `weapon.hands.two` | Derivada da definição canônica do item | Ocupação de slots (2H) |
| Slot eligibility | `main_only` / `secondary_only` / `main_two_handed` | Derivada da definição | Onde o item pode ser equipado |
| Compatibility tags | `weapon.compat.melee` / `.bow` / `.crossbow` | Derivada da definição | Satisfazem `weapon_requirement` de Artes |

**`weapon_family` não existe** no modelo vigente: não é armazenado, não é inferido e não pode determinar form, handedness, slot, compatibilidade, Classe ou Arte (Contrato §1.3).

A palavra “família” usada no Crafting (Principal, Secundária, 2H, Cabeça etc.) significa **grupo de receita/slot/economia**, não `weapon_family` (Contrato §1.2).

### 3.2 `weapon_form` — lista fechada (Contrato §2.4)

| ID | Player-facing | Observação oficial |
|---|---|---|
| `weapon.form.sword` | Espada | Não implica mãos nem slot |
| `weapon.form.dagger` | Adaga | Não implica Secundária |
| `weapon.form.axe` | Machado | Não implica 1H/2H |
| `weapon.form.hammer` | Martelo | Não implica 2H |
| `weapon.form.mace` | Maça | Não implica Classe defensiva |
| `weapon.form.spear` | Lança | Não implica 1H/2H |
| `weapon.form.bow` | Arco | Não implica compatibilidade sem tag |
| `weapon.form.crossbow` | Besta | Não implica compatibilidade sem tag |
| `weapon.form.staff` | Cajado | Não implica magia |
| `weapon.form.rod` | Bastão | Não implica magia |

Forma **não** determina: atributo, fórmula, proficiência, penalidade, restrição de Classe/Caminho, handedness, slot, compatibilidade ou regra de loot/Crafting (GDD §24.2, Contrato §2.1–2.2).

Lista fechada: nova forma exige revisão versionada do contrato.

### 3.3 Handedness

- Valores oficiais: `weapon.hands.one` (1 mão) e `weapon.hands.two` (2 mãos).
- **Não existem** como valores canônicos: `off-hand`, `dual-compatible`, `versatile`, `free-hand` (Contrato §3.1).
- Handedness é **explícito por item**. Não é derivado de nome, form, família, Classe, aparência, tamanho de arte ou palavra “Pesada” (Contrato §3.2).
- Um item “Espada” pode ser 1H ou 2H em conteúdo futuro, se a Fonte declarar.

### 3.4 Slots de arma e regra de 2H

- Slots de arma: **Arma Principal** e **Arma Secundária** (dos 8 slots totais).
- Três eligibility states (Contrato §4.2):
  - `weapon.slot.main_only`: só Principal.
  - `weapon.slot.secondary_only`: só Secundária.
  - `weapon.slot.main_two_handed`: equipa na Principal, ocupa 2H e bloqueia Secundária.
- **1H não significa “qualquer mão”.** Uma 1H Principal não pode ir para Secundária só por ser 1H, e vice-versa. Não existe `main_or_secondary` (Contrato §4.3).
- Não existe regra global de dual wield (Contrato §4.3).
- Ao equipar 2H, a Secundária deve ficar vazia; o item anterior vai ao Inventário na mesma transação, não fica oculto (GDD §24.2).

### 3.5 Main Hand / Off-hand

- A documentação usa **“Arma Principal”** e **“Arma Secundária”**. Os termos “Main Hand” e “Off-hand” não são definidos como conceitos canônicos.
- “Off-hand” aparece informalmente no GDD (§24.2 e §24.5, “2H/off-hand”) como referência à Secundária, mas o Contrato proíbe usá-lo como valor de handedness.
- Não existe mecânica diferenciada entre Principal e Secundária além de: (a) o slot de onde o item é equipado; (b) a regra de 2H; (c) os pools de secundários, Runas e Encantamentos de cada slot (§49.8); (d) o peso econômico de SlotWeight (§49.8).
- Cada um dos 8 slots tem pool próprio de secundários. Principal: ATQ, AGI, PER, CRIT. Secundária: ATQ, DEF, PER, CRIT, Bloqueio.

### 3.6 Escudo

- **Escudo não é um item canônico definido.** Nenhuma Fonte publica um Escudo como item, com tags ou slot.
- O Contrato (§8) diz que um escudo “pode futuramente ocupar Arma Secundária se uma Fonte de item o definir”, sem criar compatibilidade.
- O GDD chama o slot de “Arma Secundária”. A documentação não define se um futuro escudo ocuparia esse slot ou outro.
- Nenhuma Arte exige escudo (Contrato §8; Contrato §14). O “Escudo de Cinzas” (Sentinela · Bastião) é uma **Barreira**, não exige item.
- A decisão visual de 06/10/2026 mostra Sentinela com “arma de uma mão + escudo”. Isso é **direção visual**, não regra mecânica (Decisão visual, SOURCE_AUTHORITY).
- Defender é ação universal, sem requisito de item (GDD §9.3, §49.4).

### 3.7 Dual wield

- **Não existe** regra global de dual wield (Contrato §4.3).
- A decisão visual de Errante (“duas armas curtas”) é direção visual, não mecânica. O Contrato afirma: “uma skin de Classe mostrando espada… não cria loadout mecânico” (§6).
- Errante equipa uma Principal e uma Secundária como qualquer personagem; não há bônus de ter duas armas.

### 3.8 Arremesso, projeção e armas à distância

- **Não definido na documentação atual** como mecânica de arremesso ou projeção de arma.
- Armas à distância existem por tag: `weapon.compat.bow` e `weapon.compat.crossbow`, aplicadas a `weapon.form.bow` e `weapon.form.crossbow` quando declarado no item.
- Essas tags habilitam Artes “Arco ou Besta compatível”. Não existe alcance, projétil ou alvo de distância modelado (GDD §9.1).

### 3.9 Propriedades de arma que realmente afetam o combate

| Propriedade | Afeta combate? | Como |
|---|---|---|
| `weapon_form` | **Não** | Apenas descritivo (apresentação, nome, lore) |
| `handedness` | **Indiretamente** | Ocupa slots (2H bloqueia Secundária); 2H tem núcleo ATQ próprio (ver 3.10) |
| Slot eligibility | **Indiretamente** | Onde o item pode estar |
| Compatibility tags | **Sim** | Satisfazem ou não `weapon_requirement` de Artes |
| Núcleo de atributos (ex.: ATQ 25 na Principal Comum Nv.60) | **Sim** | Atributo estático do personagem |
| Secundários (atributos) | **Sim** | Atributos adicionais por raridade |
| Runas e Encantamentos | **Sim** | Potência de atributo; 2H tem duas Runas |
| Aprimoramento (+0 a +10) | **Sim** | Multiplicador total sobre o valor-base |
| Raridade / Grau / `item_level` | **Sim, indiretamente** | Raridade define secundários e budget; `item_level` define requisito de nível e Grau de componentes |
| Nome, Negociabilidade, Bind | **Não** | Economia e apresentação |

**Não existem** na documentação: dano base da arma, coeficiente de arma, velocidade/cadência de arma, alcance, dano por tipo de arma, crítico próprio da arma, chance de bloqueio própria da arma, penalidade por arma, durabilidade, munição.

### 3.10 Núcleo de atributos por slot (GDD §49.8, Nv.60, Comum +0)

| Slot | Núcleo (Comum +0, Nv.60) | SlotWeight | EconomySW |
|---|---|---|---|
| Principal | ATQ 25 | 18 | SW2 |
| Secundária | ATQ 7, DEF 5 | 10 | SW1 |
| 2H (ocupa Principal + Secundária) | ATQ 35 (ofensiva Comum Nv.60) | 28 | SW3 |

Observações:

- `SlotWeight` é **orçamento/custo**, não peso físico. Não existe carga, peso ou equip load (GDD §24.2).
- EconomySW é multiplicador econômico, diferente de SlotWeight.
- **Não explicitado:** na fórmula “Valores intermediários = `round_half_up(Value60 × G(n))`”, a variável `n` é presumivelmente `item_level`, mas a Fonte não o declara neste trecho.

### 3.11 Armas publicadas e mapeadas (Contrato §9)

O Contrato mapeia **22 armas** publicadas nas Regiões 1–5. Abaixo, o resumo mecânico de cada uma.

| Região | Arma | Form | Mãos | Slot | Tag |
|---|---|---|---|---|---|
| TDO | Arma do Caminhante | sword | 1H | main_only | melee |
| TDO | Guarda do Caminhante | dagger | 1H | secondary_only | melee |
| TDO | Arma Pesada do Caminhante | bow | 2H | main_two_handed | bow |
| TDO | Guarda do Primeiro Selo | mace | 1H | secondary_only | melee |
| VDE | Arma do Vale | axe | 1H | main_only | melee |
| VDE | Guarda Enredada | dagger | 1H | secondary_only | melee |
| VDE | Arma Pesada dos Laços | crossbow | 2H | main_two_handed | crossbow |
| VDE | Guarda do Nó Antigo | sword | 1H | secondary_only | melee |
| Nareth | Arma do Meridiano | spear | 1H | main_only | melee |
| Nareth | Guarda de Marco | dagger | 1H | secondary_only | melee |
| Nareth | Arma Pesada do Horizonte | bow | 2H | main_two_handed | bow |
| Nareth | Guarda da Câmara Invertida | sword | 1H | secondary_only | melee |
| Nareth | Guarda da Referência | mace | 1H | secondary_only | melee |
| Várzeas | Arma do Dique | mace | 1H | main_only | melee |
| Várzeas | Guarda de Salmoura | dagger | 1H | secondary_only | melee |
| Várzeas | Arma Pesada de Transferência | crossbow | 2H | main_two_handed | crossbow |
| Várzeas | Guarda de Transferência | sword | 1H | secondary_only | melee |
| Altos | Arma do Contrapeso | hammer | 1H | main_only | melee |
| Altos | Guarda de Escora | axe | 1H | secondary_only | melee |
| Altos | Arma Pesada da Pedreira | crossbow | 2H | main_two_handed | crossbow |
| Altos | Guarda do Contraforte Final (P30) | mace | 1H | secondary_only | melee |
| Altos | Guarda da Ordem Profunda (especial) | sword | 1H | secondary_only | melee |

**Confins do Véu (Região 6):** a §19.2 da Confins FINAL declara mais 5 armas (`lamina_baliza` 1H Principal sword; `guarda_marcha` 1H Secundária dagger; `arco_retorno` 2H Principal bow; `guarda_ultimo_protocolo` 1H Secundária mace; `guarda_duas_versoes` 1H Secundária sword), com a mesma estrutura. Essas cinco **não estão listadas** na §9 do Contrato (ver 9.1).

**Guarda do Berço Silente** (VDE) é **Torso**, não arma (Contrato §9.3).

**Distribuição das 22 armas por form** (contagem feita sobre a tabela acima): sword 5; dagger 4; mace 4; axe 2; bow 2; crossbow 3; hammer 1; spear 1. Total 22. O Contrato não publica essa contagem; ela é apenas conferência.

### 3.12 Armas × Classes

- **Nenhuma Classe possui proficiência, restrição global ou bônus de arma** (Contrato §6; GDD §55.3).
- Classes com Artes que exigem arma (ver seção 4.2): Sentinela, Errante, Vigia.
- Tecelão, Oráculo e Luminar: nenhuma Arte vigente exige arma (Contrato §6).

---

## 4. Equipamentos

### 4.1 Slots oficiais (GDD §24.1)

Total: **8 slots**:

1. Arma Principal
2. Arma Secundária
3. Cabeça
4. Torso
5. Mãos
6. Pés
7. Acessório (único; não há dois anéis)
8. Artefato

Não existe sistema global de armadura leve/média/pesada (GDD §24.2).

### 4.2 Regras de ocupação

- Arma 2H ocupa Principal e bloqueia Secundária (GDD §24.2; Contrato §4.3).
- Equipar 2H com Secundária preenchida: o item da Secundária vai ao Inventário na mesma transação (GDD §24.2).
- A Configuração de Combate trava a alteração de **todos os 8 slots**, incluindo Principal e Secundária, durante atividade com lock (GDD §39.2).

### 4.3 Compatibilidade e restrições

- Compatibilidade de Arte com arma: via compatibility tags (seção 5).
- Restrição de Classe/Caminho em equipamento: **só existe quando declarada explicitamente** na definição do item e validada pelo Equipment Validator (GDD §24.2). Nenhum item de arma publicado declara restrição de Classe.
- Restrição por subtipo visual: **proibida**.

### 4.4 Equipment Validator (GDD §24.5)

Toda mudança de equipamento passa por um validador central que verifica:

1. slot;
2. nível (`character_level ≥ item_level`);
3. Classe/Subclasse (quando declarado);
4. 2H/off-hand (ocupação de mãos);
5. máximo de **1 Mítico equipado**;
6. bind;
7. componentes (Runas/Encantamentos);
8. estado do item;
9. requisito especial;
10. capacidade final do Inventário.

Trocas são **atômicas**: simula-se o estado final completo; se inválido, nada muda.

Para Artes, o Validator também revalida a Configuração de Combate (GDD §55.3, Contrato §7.3).

### 4.5 Nível, Raridade, Grau, `item_level` e Aprimoramento

- **`item_level`**: todo Equipamento tem um; exige `nível do personagem ≥ item_level` para ser equipado. `required_level = item_level`; não há segundo requisito numérico.
- `item_level` é **imutável** durante a vida da `item_instance`. Aprimoramento, Reroll, Runa, Encantamento, Trade, Bind, Legado ou mudança de dono não o alteram (GDD §24.6).
- Após Legado ou redução de nível, itens acima do nível viram inelegíveis e são desequipados com segurança (não destruídos) (GDD §24.2).
- **Grau** (I–VI) é derivado de `item_level`: 1–10=I, 11–20=II, 21–30=III, 31–40=IV, 41–50=V, 51–60=VI (GDD §24.6).
- **Raridade:** Comum, Raro, Épico, Lendário, Mítico. Máximo de 1 Mítico equipado.
- Quantidade de secundários por raridade: Comum 0, Raro 1, Épico 2, Lendário 3, Mítico 4 (GDD §24.6).
- Multiplicador de raridade/budget: Comum 1,00; Raro 1,07; Épico 1,15; Lendário 1,24; Mítico 1,45 (GDD §49.8).
- **Aprimoramento:** +0 a +10, garantido, sem falha, sem destruição, sem downgrade. Multiplicadores **totais** sobre o valor-base: +0=1,00×; +1=1,02×; +2=1,04×; +3=1,06×; +4=1,08×; +5=1,10×; +6=1,125×; +7=1,15×; +8=1,175×; +9=1,20×; +10=1,25× (GDD §49.8).
- Sem durabilidade. Sem aparências cosméticas de armas no lançamento (GDD §24.2).

### 4.6 Secundários, Reroll e Bind

- Secundários são atributos adicionais do próprio item, sorteados no pool do slot, uniformemente, sem reposição e sem duplicação, salvo peso declarado pelo Conteúdo (GDD §24.6).
- **Arma 2H usa o pool de Principal** para seus secundários. Não há pool híbrido (GDD §24.6).
- Pools de secundários por slot (GDD §49.8): Principal `ATQ, AGI, PER, CRIT`; Secundária `ATQ, DEF, PER, CRIT, Bloqueio`.
- Reroll troca só a identidade de um secundário já selecionado, por outra legal não duplicada; magnitude recalculada com o mesmo share de budget (GDD §24.3).
- Bind: maioria Negociável; alguns Bind-on-Equip ou Bind-on-Acquire. Confirmação agregada na primeira vez que Doutrina equipa item Bind-on-Equip (GDD §24.3).

### 4.7 Runas e Encantamentos (GDD §25, §49.8)

**Runas**

- Componente inserível/removível. Identidade e bind preservados.
- 1 slot de Runa por item normal; **2 em 2H** (GDD §49.8).
- Raridades de Runa: Rara, Épica, Lendária.
- Grau VI de Runa: HP/ATQ `+0,60/+0,80/+1,00%`; DEF/AGI `+1,0/+1,4/+1,8%`; PER/CRIT `+0,50/+0,75/+1,00 p.p.`; Esquiva `+0,25/+0,50/+0,50`; Bloqueio `+0,50/+0,75/+1,00`.
- Pools de Runa por slot seguem o mesmo padrão dos secundários, com diferença em Mãos (ATQ, DEF, AGI, PER, CRIT).
- **Arma 2H:** afinidade A usa pool de Principal; afinidade B usa pool de Secundária (GDD §49.8).

**Encantamentos**

- Até **1 por equipamento** (GDD §25.2). Aplicar novo substitui e destrói o anterior, com aviso.
- **2H tem 1 Encantamento.** Potência `×2` apenas se o efeito existe em ambos os pools (ATQ, PER ou CRIT); normal se existe em apenas um.
- Encantamento não é componente em slot; é modificação da `item_instance`.

**Grau de componentes**

- Para instalar/aplicar: `grau_do_componente ≤ equipment_grade(item_level)`.
- Componente de Grau inferior mantém sua potência; não é promovido (GDD §25.3).
- Compatibilidade por slot e afinidades A/B da 2H devem ser satisfeitas simultaneamente.

**Escalonamento por Grau:** `Q(teto_do_Grau)` — I 0,556; II 0,625; III 0,703; IV 0,791; V 0,889; VI 1,000 (GDD §49.8).

**Ambiguidade:** “Runas: 1 slot por item normal; 2 em 2H; máximo 8” (GDD §49.8). A Fonte não esclarece se “máximo 8” é por item, por personagem ou outro escopo. Não definido na documentação atual.

### 4.8 Materialização (GDD §24.6, §49.9)

- Toda origem que cria Equipamento (Saque, Crafting, recompensa de Campanha, Receita especial) usa o mesmo materializador de `item_instance`.
- Ordem: resolver `template_id`, raridade, `item_level`, bind e seed determinística; depois secundários; depois valores pelas fórmulas globais. Não existe roll de potência fora delas.
- Equipamento nasce `+0`, sem Runa, sem Encantamento, salvo declaração da fonte.
- Torso Mítico genérico é **inelegível** enquanto Torso tiver só três identidades de secundário (GDD §24.6).
- Seleção normal de Saque usa oito grupos: Principal, Secundária, Cabeça, Torso, Mãos, Pés, Acessório, Artefato. **Arma 2H não é nono grupo**: templates 2H ficam no grupo Principal.

### 4.9 Outras regras que podem afetar armas

- **Troca de Doutrina** é atômica (GDD §8.5, §24.5).
- **Doutrina** registra equipamentos por `item_instance_id` dos 8 slots, mas Runas e Encantamentos pertencem ao estado atual da `item_instance` (GDD §8.5).
- **Doutrina incompleta** ocorre com item ausente, item em Armazém/escrow, requisito de nível não atendido, Arte indisponível etc.; não recria item nem ignora requisito (GDD §8.5).
- **Ronda de Caça** executa automaticamente apenas Artes Ativas equipadas na Configuração registrada (GDD §8.3, §18.2).
- **Legado**: Equipamentos acima do novo nível são desequipados, não destruídos (GDD §24.2).
- **Mercado:** compra parcial de itens stackable; itens não stackable são comprados como unidade (GDD §55.4). Não altera regras de arma.

---

## 5. Artes e habilidades

### 5.1 `weapon_requirement` (GDD §55.3; Contrato §7)

Modelo oficial:

```text
ART_WEAPON_REQUIREMENT_MODEL =
  NONE
  | TAG_ANY_OF(set explícito de compatibility tags)
```

- Cada Arte declara seu próprio requisito. Não pode ser inferido da Classe, Caminho, nome, animação, subtipo visual ou arma mostrada.
- `NONE` significa que a Arte pode ser usada sem arma específica, **inclusive desarmada**, se o restante do estado permitir.
- Requisitos atuais são somente três estados funcionais: `NONE`, `TAG_ANY_OF{weapon.compat.melee}`, `TAG_ANY_OF{weapon.compat.bow, weapon.compat.crossbow}`.
- A exigência é satisfeita quando **ao menos uma arma equipada em slot legal** possui a tag aceita. Se Principal e Secundária estiverem equipadas, qualquer uma pode satisfazer.
- Arma desconhecida ou sem tag explícita **não satisfaz** requisito específico.

### 5.2 Matriz de requisitos (GDD §55.3)

Contagem por Classe (6 Artes de Classe + 8 Artes de 2 Caminhos = 14 linhas por Classe, conforme a matriz):

| Classe | Artes na matriz | `melee` | `bow` / `crossbow` | `NONE` |
|---|---:|---:|---:|---:|
| Sentinela (Bastião, Devastador) | 14 | 9 | 0 | 5 |
| Errante (Carrasco, Sabotador) | 14 | 13 | 0 | 1 |
| Vigia (Atirador, Rastreador) | 14 | 0 | 13 | 1 |
| Tecelão | 14 | 0 | 0 | 14 |
| Oráculo | 14 | 0 | 0 | 14 |
| Luminar | 14 | 0 | 0 | 14 |
| **Total** | **84** | **22** | **13** | **49** |

Exemplos de requisito por Arte:

- Sentinela · Golpe de Guarda: `melee`. Sentinela · Muralha Breve: `NONE` (Barreira).
- Errante · Passo Velado: `NONE` (“passo e preparação; sem golpe de arma”). Errante · Corte Duplo: `melee` (dois cortes físicos na mesma ação).
- Vigia · Disparo Preciso: `bow/crossbow`. Vigia · Olho da Vigília: `NONE` (“mira e preparação; sem disparo”).
- Tecelão, Oráculo, Luminar: todas as Artes vigentes com `NONE` (ex.: Lança de Luz, do Luminar Inquisidor, “não declara ataque físico de arma”).

### 5.3 Diferença entre comportamento básico da arma e da Arte

| Aspecto | Arma (básico) | Arte |
|---|---|---|
| Dano | Não tem dano próprio | Coeficiente próprio sobre ATQ (`110%`, `135%` etc.) |
| Requisito | Não tem | `weapon_requirement` explícito |
| Recarga | Não tem | Sim (CD de Arte) |
| Multi-hit/AoE | Não tem | Declarado pela Arte |
| Tipo de efeito | Não tem | Declarado pela Arte (Sangramento, Veneno etc.) |

**Ataque Básico:** a documentação define 100% ATQ, Dano Direto, um inimigo, sem Recarga (GDD §49.4). **Não definido na documentação atual** se o Ataque Básico exige arma ou se funciona desarmado. §55.3 fala apenas de Artes.

**Consequência:** a arma não altera o coeficiente de dano de nenhuma Arte. Uma Arte melee com Arco equipado fica indisponível; a Arte não recebe bônus por arma.

### 5.4 Inferência por nome, tipo ou form

- **Proibida explicitamente.** A documentação diz:
  - Nome, Classe, família histórica, aparência, animação, asset visual ou arma mostrada não criam tag (Contrato §5.4).
  - `if form == bow -> add weapon.compat.bow` é inválido (Contrato §5.4).
  - `if name contains "Arco" -> add tag` é inválido (Contrato §5.4).
- Mesmo quando a intuição parecer óbvia (arco + tag `bow`), a compatibilidade é verdadeira porque a Fonte **declarou**, não porque foi deduzida.
- Legado sem correspondência canônica exata fica **`UNMAPPED`** e não satisfaz `weapon_requirement` (Contrato §10.3).

### 5.5 Configuração de Combate e validação

Validação obrigatória (GDD §55.3, Contrato §7.3):

1. ao salvar/equipar uma Arte;
2. após alteração pertinente de Equipamento;
3. antes de iniciar combate voluntário;
4. no commit da ação;
5. ao restaurar Configuração após patch ou migração.

Equipamento incompatível **não apaga a Arte**. A Configuração fica incompleta/inválida até o requisito voltar a ser satisfeito.

NPCs e inimigos usam kits próprios e **não passam** pelo Equipment Validator de personagens jogadores, salvo modelagem explícita (GDD §55.3).

Feedback de bloqueio: deve indicar o requisito funcional ausente (GDD §56.8; Contrato §12).

---

## 6. Progressão relacionada a armas

### 6.1 Como o personagem obtém, equipa, melhora ou substitui armas

| Ação | Mecanismo canônico | Fonte |
|---|---|---|
| Obter | Saque, Crafting (Ofício Ferreiro: Principal, Secundária, 2H), recompensa de Campanha, Receita especial, Mercado/Troca, Guilda (Obras) | GDD §24.6, §27, §49.9–49.11; Regionais (catálogos) |
| Equipar | Equipment Validator; `character_level ≥ item_level`; slot e 2H | GDD §24.2, §24.5 |
| Melhorar | Aprimoramento +0→+10 (multiplicador total); Runas (até 1 por slot, 2 em 2H); Encantamento (até 1, substituível) | GDD §24.2, §25, §49.8 |
| Re-rolar | Reroll de um secundário selecionado | GDD §24.3 |
| Substituir | Troca atômica; item anterior vai ao Inventário | GDD §24.2 |
| Perder elegibilidade | Legado ou redução de nível: desequipar sem destruir | GDD §24.2 |

### 6.2 Proficiência, maestria, treinamento, especialização

- **Não existe** proficiência, perícia, maestria, árvore, treinamento ou especialização de arma no sistema vigente (GDD §55.3; Contrato §6, §13.5).
- Subtipo de arma **não cria** proficiência, penalidade, restrição de Classe/Caminho ou domínio geral de arma (GDD §55.3, §24.2).
- Talentos não têm árvore de arma. A §49.5 declara que os Talentos não têm pré-requisitos.
- Caminhos e Talentos alteram atributos e Artes, não o uso de arma por tipo.

### 6.3 Nível mínimo para armas

- Único requisito de nível: **`nível do personagem ≥ item_level`** (GDD §24.2).
- Não existe segundo requisito numérico separado.

### 6.4 Canônico versus planejado ou desativado

| Item | Estado |
|---|---|
| Modelo de metadata de arma (form, handedness, slot, tags) | **Canônico**, `FINAL_IMPLEMENTABLE` (Contrato, §15) |
| Mapeamento de 22 armas publicadas (Regiões 1–5) | **Canônico** (Contrato §9) |
| Armas de Confins (5) | **Declaradas** na Regional §19.2; **não estão** no mapeamento da §9 do Contrato (ver 9.1) |
| Taxonomia de 14 famílias históricas | **Não canônica** (Contrato §10.4) |
| Legado sem correspondência exata | **`UNMAPPED`**; não satisfaz requisito (Contrato §10.3) |
| Character Progression dependente desses metadados | **Pendente de sincronização**: “A implementação deve sincronizar este contrato antes de reativar ou recuperar Character Progression dependente desses metadados” (Contrato §15). Trata-se de condição de implementação, não de regra de jogo. |
| Aparência cosmética de arma | **Fora do lançamento** (GDD §24.2) |
| Escudo como item | **Não definido** |
| Dual wield, arremesso, projeção, cone, cleave, alcance | **Não definido** |

---

## 7. Limitações técnicas do sistema

Verificação solicitada, conceito por conceito:

| Conceito | Mecanismo real? | O que existe | O que não existe |
|---|---|---|---|
| **Alcance** | Não | Tags `melee`/`ranged` como identidade; sem grid nem distância (§9.1) | Alcance numérico, faixas, penalidade por distância |
| **Ritmo / velocidade de ataque** | Não | Iniciativa por AGI; Recarga por oportunidade; Geada atua em AGI/ritmo (§10.5) | Velocidade de arma, ataques por turno por arma, cadência |
| **Padrões de ataque** | Parcial | Ataque Básico (1 alvo, 1 golpe); Arts com `hit_count` (ex.: Corte Duplo 2 cortes; Saraivada 3; Rajada 3×45%) | Padrões nomeados por arma (ex.: “perfurar”, “varrer”) como mecânica genérica |
| **Cone** | Não | Não definido | Qualquer regra de cone |
| **Cleave** | Não | Não definido como mecânica genérica; Arte pode ser AoE (ex.: Abalo, “ataque físico direto em área”) | Divisão de dano entre alvos adjacentes ou regra de cleave por arma |
| **Área (AoE)** | Sim, por Arte | Arte declara AoE; AoE usa estado pré-evento; alvos selecionados deterministicamente (§11) | Geometria de área; AoE por arma |
| **Projeção** | Não | Não definido | Qualquer projétil ou arremesso |
| **Retorno de projétil** | Não | Não definido. “Arco de retorno” (Confins) é **nome de item**; Runa de Retorno é Cura de Arte | Mecânica de retorno |
| **Quantidade de golpes** | Sim, por Arte | `hit_count` declarado pela Arte; crítico e acerto por hit | Golpes por arma |
| **Dual wield** | Não | Não existe (Contrato §4.3) | Qualquer bônus ou regra de duas armas |
| **Diferenças mecânicas 1H × 2H** | Parcial | Slot (2H ocupa Principal e bloqueia Secundária); núcleo ATQ (2H Comum Nv.60: ATQ 35; Principal + Secundária Comuns: ATQ 25 + 7); 2 Runas e Encantamento ×2 condicional; SlotWeight 28 e SW3 (economia) | Dano diferenciado por handedness, velocidade, bônus de crítico, bloqueio ou alcance |
| **Diferenças entre tipos de dano** (físico, mágico, Trama, Luz etc.) | Não | Tipos internos: Dano Direto, DoT, Reação, Refletido, Ambiental | Resistência ou interação por rótulo físico/mágico |
| **Precisão de arma** | Não | “Precisão interna é alta” (§9.2) | Acerto por arma |
| **Bloqueio por arma/escudo** | Não definido | Stat e redução de 35% (§9.3) | Regra de qual ataque é “bloqueio válido”, origem do bloqueio |
| **Arma como fonte de dano** | Não | Dano é `ATQ × coeficiente` da Arte ou do Ataque Básico | Coeficiente, dano base ou crítico de arma |

---

## 8. Conclusão técnica

## O que o sistema atual realmente suporta

### Suportado e já definido

- Turnos, iniciativa por AGI e ausência de posicionamento espacial.
- Fórmula de dano por ATQ, DEF, PER, Perfuração/-DEF, Defender, Bloqueio, Barreira e HP.
- Crítico, Esquiva (com regra de 2 consecutivas), Bloqueio e Defender com caps e valores.
- Tipos internos de dano e fases de resolução.
- Artes com coeficientes, Recarga, duração em T, DoTs e CC.
- Multi-hit e AoE declarados por Arte.
- Recursos internos de Classe (Retaliação, Oportunismo, Mira, Trama, Presságio, Fulgor/Julgamento).
- Forma descritiva (10 valores fechados), handedness (1H/2H), slots de arma (Principal, Secundária, 2H) e regra de bloqueio de Secundária por 2H.
- Compatibility tags (`melee`, `bow`, `crossbow`) explícitas por item.
- `weapon_requirement` por Arte (`NONE` ou `TAG_ANY_OF`) com matriz completa das 84 Artes de Classe/Caminho.
- Validação de Configuração de Combate em cinco momentos.
- Equipment Validator, `item_level`, Raridade, Grau, Aprimoramento, Runas (1 por slot, 2 em 2H), Encantamento (1, substituível), Reroll de secundário e pools por slot.
- Mapeamento de 22 armas publicadas (Regiões 1–5).
- Ausência de proficiência, maestria e restrição de arma por Classe.
- Nível mínimo único: `item_level`.

### Possível, mas não definido

- Bloqueio por arma ou escudo: stat existe; origem e condição de “bloqueio válido” não existem.
- Escudo como item de Secundária: contrato prevê possibilidade futura; item não definido.
- Armas 2H com mecânica própria de velocidade, alcance, crítico ou dano: a estrutura comporta, mas não há campo ou regra definidos.
- Ataque Básico com requisito de arma ou sem arma: não definido.
- Cone, cleave, projeção e retorno de projétil: a estrutura de Arte com AoE e `hit_count` poderia representar casos específicos, mas nenhuma Fonte define essas regras.
- Diferença mecânica entre físico e mágico: rótulos existem em texto; nenhuma regra os separa.
- Significado exato de PER como sigla e de “máximo 8” em Runas.
- Escopo do `n` em `round_half_up(Value60 × G(n))` para o núcleo de Equipamento.
- Arma com Encantamento ou Runa que altera requisito de Arte: a estrutura de Runa/Encantamento só altera atributos. Não há Runa que modifique `weapon_requirement`.

### Não suportado / exigiria criação de nova mecânica

- Dano base, coeficiente ou crítico próprio de arma.
- Velocidade, cadência ou ataques por turno determinados pela arma.
- Alcance numérico, distância, linha ou grid.
- Dual wield, incluindo bônus de ter duas armas.
- Arremesso, projétil e retorno de projétil.
- Proficiência, maestria ou especialização de arma.
- Restrição de arma por Classe global.
- Tags de “arma mágica” ou de Classe, e Foco como item equipável por padrão. O Contrato não as possui (§5.2 e §8).
- Inferência de compatibilidade por nome, form, família, Classe ou visual.
- Durabilidade e munição.

---

## 9. Pontos de governança e inconsistências identificadas

Estes pontos não são propostas. São registros de documentos que precisam de decisão antes de qualquer redesenho.

### 9.1 Confins do Véu e o Contrato de Weapon Metadata

- O Contrato (v1.0.0 FINAL, 2026-10-17, §6 e §9.1) afirma que **não existe Fonte Regional FINAL de Confins**.
- `SOURCE_AUTHORITY.md` (2026-10-18) registra Confins v1.0.0 FINAL e declara a §19.2 sincronizada com o Contrato.
- A §9 do Contrato **não lista** as cinco armas de Confins. O total mapeado é 22; com Confins seriam 27.
- A Regional §19.2 diz que a tabela é “proposta de conteúdo alinhada” ao Contrato até a sincronização formal.
- **Recomendação de governança:** confirmar formalmente que as cinco armas de Confins entraram no mapeamento canônico antes de redesenho.

### 9.2 Escudo e nome do slot Secundária

- O GDD chama o slot de “Arma Secundária”.
- O Contrato (§8) admite que um escudo futuro possa ocupá-lo.
- Não há item de escudo definido. Confirmar se o nome e a função do slot devem permanecer.

### 9.3 Terminologia “Off-hand”

- Usada no GDD (§24.2, §24.5) sem definição formal.
- O Contrato proíbe como handedness.
- Confirmar se é apenas sinônimo informal de Arma Secundária.

### 9.4 Visual × mecânica

- A decisão visual de 06/10/2026 mostra Sentinela com escudo e Errante com duas armas curtas.
- O próprio Contrato afirma que skin não cria loadout mecânico.
- Riscos de leitura: a arma-assinatura visual não tem efeito mecânico. Isso deve ser lembrado no redesenho.

### 9.5 Ataque Básico × arma

- §55.3 define requisitos apenas para Artes.
- Não há regra explícita sobre Ataque Básico desarmado ou com arma específica.

### 9.6 Bloqueio sem origem definida

- Stat de Bloqueio existe, com cap e redução.
- Não há regra que define o que é “bloqueio válido”.

---

## 10. Itens fora de escopo

- Balanceamento de Classes e Caminhos (exceto onde afeta `weapon_requirement`).
- Lore de armas (Bíblia Canônica v4.0.7).
- Assets e pixel art (Bíblia Técnica de Geração e Matriz de Produção).
- Implementação, schema, migrations e código.
- Nenhuma proposta de mudança é feita neste documento.

---

*Fim do documento. Versão 1.0.0. Próxima revisão deve ocorrer após decisão sobre os pontos da seção 9.*
