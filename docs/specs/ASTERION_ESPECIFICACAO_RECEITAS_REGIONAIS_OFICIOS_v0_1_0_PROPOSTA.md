# Especificação: Ofícios fabricam o catálogo regional (v0.1.0, PROPOSTA)

**Status:** proposta. Aguarda aprovação do autor. Nenhum código antes disso.
**Data:** 2026-11-25.
**Origem:** a auditoria `docs/audits/ASTERION_AUDITORIA_FASE2E_v1.9.1_VS_MAIN_2026-11-25.md` (§9 e §10) encerrou a Fase 2E como superada. A lacuna que sobrou: os Ofícios (`src/asterion/domain/professions.py`) não fabricam nenhum item do catálogo regional de Saque (`src/asterion/domain/regional_equipment.py`).
**Autores:** game-designer (desenho), systems-designer (custos e economia), consolidado pela sessão principal.

## 1. Fontes

As versões vigentes são as do `SOURCE_AUTHORITY.md` (raiz, sincronização 2026-11-19):

| Assunto | Fonte |
|---|---|
| Fórmula de crafting, Graus, requisitos, PXP, Desmontagem, Mercado | GDD Estrutural v1.7.1, §49.9, §49.10 e §49.11 |
| Materiais e receitas-família por região | TDO v1.0.18, VDE v1.0.6 §18, Nareth v1.0.2, Várzeas v1.0.3, Altos v1.0.1 §7 e §17, Confins v1.0.0 §8, §9 e §19 |
| Tipos de arma e mãos (1H/2H) | Contrato Weapon Metadata v1.1.1 (`domain/weapon_metadata.py`) |
| Classes de armadura | Spec Classes de Armadura v1.0.0, com a exceção autoral de 2026-11-14/19 registrada no `SOURCE_AUTHORITY.md` |
| Catálogo de itens | `domain/regional_equipment.py` (código na `main`) |

Esta spec **não cria nenhum número novo**. Todo custo sai da fórmula do GDD §49.11, que o systems-designer conferiu contra o código: não há divergência (§6).

## 2. Escopo

Por região (6 regiões: `tdo`, `vde`, `nareth`, `varzeas`, `altos`, `confins`), os Ofícios passam a fabricar os 42 itens do catálogo:

- 20 armas: 19 tipos `weapon.type.base.*` e o Escudo;
- 16 armaduras: Veste, Leve, Média e Pesada × Cabeça, Torso, Mãos e Pés;
- 3 Selos (Acessório) e 3 Relicários (Artefato).

Cada item tem 3 receitas: Comum, Raro e Épico. Total: 42 × 3 × 6 = **756 receitas**.

Fora do escopo:

- Lendário e Mítico. O Lendário continua só com Receita especial (hoje, só a dos Flagelos). O Mítico não é receita genérica (Altos §17; Confins §19).
- Receitas especiais, alquimia, runas, encantamentos e Flagelos: não mudam.
- Os 66 itens novos e o ledger da Fase 2E: cancelados (auditoria §10).

## 3. Decisões do autor (2026-11-25)

| # | Pergunta | Decisão |
|---|---|---|
| A1 | Cobertura | Os Ofícios fabricam os 42 itens do catálogo, nas 6 regiões. |
| A2 | Ofício por classe de armadura | O Curteiro faz Veste e Leve. O Ferreiro faz Média e Pesada. |
| A3 | Receitas-família atuais | Converter (ver §7). |
| A4 | Confins §19 Regra A ("sem armadura leve/média/pesada mecânica") versus a exceção de Classes de Armadura | A exceção vence. Confins fabrica as 4 classes. A fonte de Confins fica superada neste ponto, por decisão do autor. |

## 4. Recomendações que dependem de aprovação

Os agentes propõem estas regras. Nenhuma tem número novo. O autor aprova ou corrige cada uma.

| # | Ponto | Recomendação | Por quê |
|---|---|---|---|
| R1 | Ofício das armas | O Ferreiro fabrica as 20, incluindo Cetro, Orbe, Cajado, Arco e Bestas. | O GDD §49.11 só tem Ferreiro nas famílias Principal, Secundária e 2H. Confins §19.1 já põe um arco no Ferreiro. |
| R2 | Ofício das joias | O Joalheiro fabrica os 3 Selos e os 3 Relicários. | GDD §49.11. |
| R3 | 1H ou 2H | Vem da `handedness` do Weapon Metadata. 2H usa o slot de economia `2H` (SW 3). 1H usa `Principal` (SW 2). Escudo usa `Secundária` (SW 1). | A fonte define SW por slot, e o metadata já define as mãos de cada tipo. |
| R4 | Custo por classe de armadura | Igual nas 4 classes. O custo depende só do slot. | A fonte não diferencia classe. Diferenciar exigiria número novo. |
| R5 | Material por tipo de arma ou classe | Par único por Ofício e região (§5). | Idem. |
| R6 | Requisito de Ofício | `max(requisito do Grau, requisito da raridade)`, como o código já faz. | GDD §49.11. É coerente com Altos §17 (Ofício 12) e Confins §19 (mínimo 15). |
| R7 | Saque | Os itens fabricáveis continuam caindo no Saque. Não há item "só craft". | GDD §49.9 (templates normais são elegíveis a Saque). |
| R8 | Vínculo (bind) | Sem mudança: o item fabricado é Negociável se todos os básicos forem Negociáveis (`transmits_bind`). | Regra atual, GDD §27 e §49.9. |
| R9 | `region_id` no item fabricado | O item fabricado leva o `region_id` e o `template_id` do catálogo, igual ao do Saque. | O item fabricado e o item de Saque ficam iguais na UI e nas regras de classe e proficiência. |
| R10 | Itens já fabricados | Ficam como estão, sem migração nesta etapa. As armas antigas `weapon.type.<reg>.arma_*` continuam equipáveis. | Migrar inventário é arriscado e merece etapa própria. |
| R11 | IDs de Fragmento e Catalisador V e VI | Manter os IDs atuais `material.tdo.*_v` e `material.tdo.*_vi`. | As fontes os tratam como globais pré-existentes. Renomear não é regra de jogo. |

## 5. Ofício e materiais

### 5.1 Ofício por grupo

| Grupo | Ofício | Slot de economia (SW) |
|---|---|---|
| Arma 1H (11 tipos) | Ferreiro | Principal (2) |
| Arma 2H (8 tipos) | Ferreiro | 2H (3) |
| Escudo | Ferreiro | Secundária (1) |
| Veste e Leve (8 peças) | Curteiro | Cabeça 1, Torso 2, Mãos 1, Pés 1 |
| Média e Pesada (8 peças) | Ferreiro | Cabeça 1, Torso 2, Mãos 1, Pés 1 |
| Selos | Joalheiro | Acessório (2) |
| Relicários | Joalheiro | Artefato (2) |

### 5.2 Materiais por região

A proporção vem do GDD §49.11: Ferreiro e Curteiro 70/30, Joalheiro 60/40. O Joalheiro usa o mesmo par do Ferreiro.

| Região | Grau | Ferreiro e Joalheiro (primário / secundário) | Curteiro (primário / secundário) | Fragmento / Catalisador |
|---|---|---|---|---|
| TDO | I | `material.tdo.ferro_de_fuligem` / `material.tdo.residuo_ocaso` | `material.tdo.couro_escoriado` / `material.tdo.erva_cinzenta` | `material.tdo.fragmento_aprimoramento_i` / `material.tdo.catalisador_elite_i` |
| VDE | II | `material.vde.ferro_enredado` / `material.vde.resina_enredada` | `material.vde.couro_musgoso` / `material.vde.erva_de_turfa` | `material.vde.fragmento_aprimoramento_ii` / `material.vde.catalisador_elite_ii` |
| Nareth | III | `material.nareth.bronze_de_marco` / `material.nareth.po_de_eixo` | `material.nareth.couro_de_horizonte` / `material.nareth.erva_de_vento` | `material.nareth.fragmento_aprimoramento_iii` / `material.nareth.catalisador_elite_iii` |
| Várzeas | IV | `material.varzeas.ferro_de_salmoura` / `material.varzeas.soro_antigo` | `material.varzeas.couro_de_varzea` / `material.varzeas.junco_ferruginoso` | `material.varzeas.fragmento_aprimoramento_iv` / `material.varzeas.catalisador_elite_iv` |
| Altos | V | `material.altos.ferro_contrapeso` / `material.altos.cinza_basalto` | `material.altos.couro_escarpa` / `material.altos.liquen_pedreira` | `material.tdo.fragmento_aprimoramento_v` / `material.tdo.catalisador_elite_v` |
| Confins | VI | `material.confins.ferro_baliza` / `material.confins.po_referencia` | `material.confins.couro_marcha` / `material.confins.musgo_limiar` | `material.tdo.fragmento_aprimoramento_vi` / `material.tdo.catalisador_elite_vi` |

Fontes dos materiais: código atual (`professions.py`, constantes e `MATERIAL_NAMES`), VDE §18.1, Altos §7.1 e §17, Confins §9.1 e §19.1. Antes de implementar, o `programmer` confirma que os IDs `material.confins.*` existem no inventário do código.

## 6. Custos (fórmula vigente, sem número novo)

GDD §49.11, já implementada em `professions.py`:

- Básicos por SW: Comum 5, Raro 8, Épico 10.
- Fragmentos por SW: Raro 4, Épico 6.
- Catalisadores por SW: Épico 2.
- Divisão primário/secundário: `floor(total × proporção + 0,5)`, aplicada uma vez, depois de multiplicar pelo SW.
- Taxa em Coroas: `round_10(C(item_level) × SW × fator)`, com `C(n) = round_10(100 + 15n)` e fator Comum 0,25, Raro 0,35, Épico 0,50.
- `item_level = min(nível do destinatário, teto do Grau)`.
- Requisito de Ofício: Grau I 1, II 3, III 6, IV 9, V 12, VI 15; raridade Comum 1, Raro 5, Épico 10. Vale o maior (R6).
- PXP: `(80 + 20 × nível da receita) × multiplicador de Grau` (100%, 50%, 20%, 0).

### 6.1 Materiais por receita (Ferreiro e Curteiro, 70/30)

| SW | Comum | Raro | Épico |
|---|---|---|---|
| 1 | 5 (4/1) | 8 (6/2) + 4 Fragmentos | 10 (7/3) + 6 Fragmentos + 2 Catalisadores |
| 2 | 10 (7/3) | 16 (11/5) + 8 Fragmentos | 20 (14/6) + 12 Fragmentos + 4 Catalisadores |
| 3 (2H) | 15 (11/4) | 24 (17/7) + 12 Fragmentos | 30 (21/9) + 18 Fragmentos + 6 Catalisadores |

Joalheiro (60/40, sempre SW 2): Comum 10 (6/4); Raro 16 (10/6) + 8 Fragmentos; Épico 20 (12/8) + 12 Fragmentos + 4 Catalisadores.

### 6.2 Taxa em Coroas no teto de cada Grau

| SW | Raridade | I (10) | II (20) | III (30) | IV (40) | V (50) | VI (60) |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Comum | 60 | 100 | 140 | 180 | 210 | 250 |
| 1 | Raro | 90 | 140 | 190 | 240 | 300 | 350 |
| 1 | Épico | 120 | 200 | 280 | 350 | 420 | 500 |
| 2 | Comum | 120 | 200 | 280 | 350 | 420 | 500 |
| 2 | Raro | 180 | 280 | 380 | 490 | 600 | 700 |
| 2 | Épico | 250 | 400 | 550 | 700 | 850 | 1000 |
| 3 | Comum | 190 | 300 | 410 | 520 | 640 | 750 |
| 3 | Raro | 260 | 420 | 580 | 740 | 890 | 1050 |
| 3 | Épico | 380 | 600 | 820 | 1050 | 1280 | 1500 |

Abaixo do teto, a taxa segue a mesma fórmula com o `item_level` real. Os valores foram calculados pelo systems-designer com as funções do código (`recipe_crown_cost`, `round_10` com desempate pelo par).

## 7. Conversão das receitas-família (decisão A3)

Hoje cada região de TDO a Várzeas tem 13 famílias × 3 raridades. Altos e Confins não têm famílias genéricas no código, só receitas especiais.

1. **Nome igual a um item do catálogo** (as 4 Vestes de Curteiro em TDO, VDE e Várzeas; o Selo e o Relicário do Joalheiro nas 6 regiões): a receita mantém o `recipe_id` e passa a apontar para o `template_id` do item (`output_id`).
2. **Nome quase igual** (Nareth: "Capuz de Horizonte" na receita, "Capuz do Horizonte" no catálogo): o autor decide se conta como igual (pergunta P1).
3. **Família sem item correspondente** (as 3 famílias de arma e as 4 peças de Ferreiro "de Fuligem", "Enlaçado" etc.): a receita fica com `creation_enabled = False`. Ela some da lista de fabricação, mas o ID continua existindo para desbloqueios (`unlock_id`) e Serviços (`service_offer`) antigos. Os itens já fabricados continuam nos inventários (R10).
4. **Itens do catálogo sem receita**: ganham receita nova com o ID `recipe.<região>.<ofício>.<slug do template>.<raridade>`. O `programmer` pode ajustar o formato, desde que não colida com IDs existentes.

## 8. Como a receita aponta para o item

| Campo da receita | Arma | Armadura | Selo e Relicário |
|---|---|---|---|
| `output_id` | `template_id` do catálogo (`equipment.<reg>.weapon.<slug>`) | `equipment.<reg>.armor.<slot>.<nome>` | `equipment.<reg>.accessory.<slug>` ou `.artifact.<slug>` |
| `output_name` | `display_name` do template | idem | idem |
| `output_slot` | do metadata da arma (1H, 2H, Escudo) | `slot` do template | `slot` do template |
| Tipo de arma | `weapon.type.base.<slug>` | não se aplica | não se aplica |
| Classe de armadura | não se aplica | `armor_class` do template (nunca gravada por item) | não se aplica |
| `region_id` | do template (R9) | idem | idem |

Pontos de código encontrados pelos agentes. A implementação é do `programmer`:

- `road.py::materialize_equipment` hoje proíbe `region_key` junto com `forced_name` ou `weapon_type_id`, e exige que o `forced_name` de arma seja o nome canônico do tipo. O craft precisa materializar pelo `template_id` regional.
- `weapon_metadata.py::weapon_type_id_for_recipe` mapeia receita para `weapon.type.<reg>.*`. As receitas novas devem usar o tipo do template.
- `recipe_materials` usa Fragmento e Catalisador I por padrão. As receitas de Altos e Confins (e de todas as regiões) devem passar os IDs explícitos de §5.2.
- `armor_class_of` só resolve itens antigos sem `template_id` em TDO. Não muda nesta etapa (R10).

## 9. Riscos de economia (systems-designer)

- **Sem loop de Desmontagem.** O retorno fica em até 33% por insumo, e o Núcleo não retorna (GDD §49.9).
- **Taxa em Coroas é sumidouro.** Fabricar não emite Coroas. Sem teto de carteira, não há risco novo de inflação.
- **Mercado.** Com os 42 itens fabricáveis (A1), nenhum item regional fica artificialmente raro. O preço de referência de um item fabricado é o custo dos insumos mais a taxa, dividido por 0,95 (taxa de 5% do Mercado, GDD §49.10).
- **Vínculo.** Fragmento e Catalisador não transmitem vínculo (regra atual). Isso não muda.
- **PXP.** O multiplicador por Grau (100/50/20/0) já impede subir de nível com receita barata de região baixa.

## 10. Perguntas ainda abertas

| # | Pergunta | Opções |
|---|---|---|
| P1 | Em Nareth, "Capuz de Horizonte" (receita) e "Capuz do Horizonte" (catálogo) contam como o mesmo item na conversão? | (a) sim, converte; (b) não, a receita antiga é desativada |
| P2 | As recomendações R1 a R11 estão aprovadas? | aprovar todas, ou indicar quais mudam |

## 11. Critérios de aceite (para a implementação depois da aprovação)

1. Cada um dos 252 templates do catálogo tem exatamente 3 receitas ativas: Comum, Raro e Épico.
2. O Ofício de cada receita segue §5.1. Os materiais seguem §5.2.
3. Materiais, Fragmentos, Catalisadores, taxa em Coroas e requisito de Ofício batem com §6 para cada slot, raridade e Grau (teste por amostragem em todas as 6 regiões e nos 3 SW).
4. O item fabricado tem o mesmo `template_id`, nome, slot, tipo de arma, classe de armadura e `region_id` do item de Saque do mesmo template.
5. As receitas convertidas mantêm o `recipe_id`. As famílias sem item correspondente ficam com `creation_enabled = False` e continuam resolvendo por ID.
6. Itens já fabricados antes da mudança continuam equipáveis e com os mesmos atributos.
7. Nenhuma receita Lendária ou Mítica genérica é criada.
8. Testes de domínio e de integração de crafting passam com o banco de teste. Teste pulado não conta como aprovado.
9. Migration, se houver, roda com `alembic upgrade head` e `alembic check` num banco descartável.
