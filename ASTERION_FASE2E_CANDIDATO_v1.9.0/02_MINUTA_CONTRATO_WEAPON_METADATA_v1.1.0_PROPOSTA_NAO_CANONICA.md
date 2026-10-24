# Minuta do Contrato Global de Weapon Metadata
## Proposta de revisão v1.1.0 · PROPOSTA_NAO_CANONICA

**Estado:** minuta sujeita a aprovação e publicação. O contrato v1.0.0 FINAL permanece vigente.  
**Escopo:** patch documental proposto; não define schema ou implementação.  
**Fonte estrutural:** GDD Estrutural v1.6.0, com as alterações de Proficiência contidas na minuta irmã deste pacote.

## 1. Resultado proposto

Manter separados os conceitos:

| Conceito | Função |
|---|---|
| weapon_form | Forma física descritiva da arma. Não concede Proficiência, mãos, slot ou tags. |
| Proficiência de equipagem | Requisito independente do item para permitir equipagem. Não é compatibility tag e não atende requisito de Arte. |
| handedness | Ocupação de uma ou duas mãos, declarada por item. |
| slot eligibility | Slot permitido, declarado por item. |
| compatibility_tags | Capacidades explícitas do item usadas somente para validar weapon_requirement de Artes. |

O requisito de cada Arte permanece independente da Proficiência de equipagem. A forma e a Proficiência são declaradas em eixos separados; uma relação de mesmo nome em um item é dado explícito do item, não transformação automática forma→Proficiência.

## 2. Alterações precisas no texto v1.0.0

| Local vigente | Tratamento proposto |
|---|---|
| Introdução e §0 | Preservar o escopo, atualizando a descrição para reconhecer Proficiência de equipagem separada, sem mudar a semântica das tags de Arte. |
| §2.1 Semântica de weapon_form | Acrescentar que a Proficiência de equipagem é declarada separadamente e nunca é inferida da forma. |
| §4.2–§4.3 | Preservar os slots e a regra 2H; registrar que Escudo fica fora do conjunto de armas e ocupa Secundária como equipamento não-arma. |
| §5.1–§5.4 | Acrescentar a semântica de lista explicitamente vazia e a distinção entre lista vazia, campo ausente e null. Preservar a proibição de inferência. |
| §6 Relação com Classes | Substituir a negação de Proficiências naturais de equipagem; remeter a matriz por Classe ao GDD. Preservar as regras de tags de Artes. |
| §7 Relação com Artes | Explicitar que Proficiência de equipagem não satisfaz weapon_requirement. A tabela vigente de Artes permanece intacta. |
| §8 Itens não-arma | Substituir a linha de Escudo: não-arma, Secundária, Proficiência Escudo, sem weapon metadata; bloqueado por Principal 2H. |
| §9.1 Escopo e §9.7 Auditoria | Corrigir o escopo para Regiões 1–6, incluir as cinco entradas de Confins publicadas em §19.2 da Fonte Regional v1.0.0 e atualizar a contagem para 27 armas. |
| §15 Estado de Game Design | Remover a afirmação de que Confins não possui Fonte Regional FINAL; apontar para Confins do Véu v1.0.0 e manter o status de publicação separado. |
| §14 Contrato final | Acrescentar declarações separadas para Proficiência de equipagem e tags explicitamente vazias. |

## 3. Texto proposto para forma e Proficiência

Acrescentar a §2.1:

> weapon_form permanece classificação física descritiva. A Proficiência de equipagem é um requisito separado, declarado pela definição do item quando aplicável. Não existe regra automática forma→Proficiência. A Proficiência apenas permite equipar e não altera atributos, dano, Artes ou compatibility tags.

A lista de formas fechada em §2.4 permanece a mesma. O contrato não cria nova forma.

## 4. Texto proposto para compatibility_tags

Acrescentar a §5:

> Quando a definição de uma arma exigir declaração explícita de compatibility_tags, a lista vazia [] é uma declaração válida de conjunto sem tags. Ela significa que o item não satisfaz requisito de Arte baseado em tag e não funciona como curinga.
>
> Campo ausente e valor null são metadata incompleta e não equivalem à lista vazia. São inválidos quando a declaração explícita for exigida pelo contrato. A política de item legado sem correspondência exata permanece a §10; não se converte metadata ausente em declaração vazia.

Preservar os vocabulários de tags existentes e a proibição de inferir tags por forma, nome, Classe, Caminho ou visual.

As seis armas Cajado e seis armas Bastão regionais candidatas conservam compatibility_tags: [] conforme aprovação de Game Design. Nenhuma forma dessas armas concede tag de Arte. Seus registros continuam candidatos enquanto as identidades não forem verificadas no snapshot de release.

## 5. Texto proposto para §4 e §8 — Escudo e mãos

- Arma 2H continua declarada em Principal, usa handedness duas mãos e bloqueia Secundária.
- Secundária deve ficar vazia com Principal 2H; arma de Secundária não fica ocultada.
- Escudo é equipamento não-arma de Secundária e exige Proficiência Escudo. Não recebe weapon_type_id, weapon_form, handedness ou compatibility_tags.
- Escudo é incompatível com Principal 2H.
- Escudo não concede Bloqueio inerente nem satisfaz requisito de Arte pela própria existência.

As regras acima não alteram a elegibilidade cruzada explícita das armas de uma mão nem criam dual wield.

## 6. Texto proposto para §§6–7 — Proficiências e Artes

A Proficiência de equipagem é validada pelo contrato de Equipamentos do GDD e pela definição do item. A matriz de Proficiências naturais por Classe é a do GDD; Raça e Caminho não concedem Proficiências naturais.

weapon_requirement continua sendo declarado pela definição da Arte como NONE ou TAG_ANY_OF(tags explicitamente publicados). Ter Proficiência para equipar uma arma não adiciona tags e não torna uma Arte utilizável se os equipamentos legais não satisfizerem o requisito daquela Arte.

A tabela de requisitos das Artes atuais, os nomes das tags e a semântica de avaliação da versão v1.0.0 permanecem sem alteração.

## 7. Correção da autoridade de Confins e linhas da §9

A afirmação atual em §9.1 de que não existe Fonte Regional FINAL de Confins deve ser substituída por:

> SOURCE_AUTHORITY.md raiz registra Confins do Véu v1.0.0 FINAL. Sua §19.2 publica metadata explícita para cinco armas regionais. A revisão deste contrato incorpora esses registros sem inferir nem ampliar as declarações da Fonte.

Proposta de linhas a inserir no mapeamento, copiadas dos identificadores e valores publicados em Confins v1.0.0 §19.2:

| ID da definição publicado | Forma | Mãos | Slot | Tags |
|---|---|---|---|---|
| craft.confins.ferreiro.principal.lamina_baliza | weapon.form.sword | weapon.hands.one | weapon.slot.main_only | weapon.compat.melee |
| craft.confins.ferreiro.secundaria.guarda_marcha | weapon.form.dagger | weapon.hands.one | weapon.slot.secondary_only | weapon.compat.melee |
| craft.confins.ferreiro.2h.arco_retorno | weapon.form.bow | weapon.hands.two | weapon.slot.main_two_handed | weapon.compat.bow |
| equipment.confins.campaign.p36.guarda_ultimo_protocolo | weapon.form.mace | weapon.hands.one | weapon.slot.secondary_only | weapon.compat.melee |
| equipment.confins.special.guarda_duas_versoes | weapon.form.sword | weapon.hands.one | weapon.slot.secondary_only | weapon.compat.melee |

Mover a auditoria de conteúdo de §9.7 para §9.8 e atualizar a contagem de 22 para 27 armas publicadas abrangidas (Regiões 1–6). Não criar weapon_type_id nem equipment_template_id alternativo para substituir os IDs de definição acima.

A declaração final da §15 que nega a existência de Confins FINAL deve ser removida e substituída por referência à §19.2 de Confins v1.0.0. Isso corrige uma referência documental; não afirma que os 226 IDs candidatos deste pacote foram verificados em release.

## 8. Alteração proposta ao contrato final da §14

Acrescentar declarações independentes:

- EQUIPMENT_PROFICIENCY_REQUIRED = DECLARADA POR ITEM QUANDO APLICÁVEL
- EQUIPMENT_PROFICIENCY_FROM_WEAPON_FORM = NO
- ART_REQUIREMENT_FROM_EQUIP_PROFICIENCY = NO
- COMPATIBILITY_TAGS_EMPTY_LIST = VALID_EXPLICIT_EMPTY_SET
- COMPATIBILITY_TAGS_ABSENT_OR_NULL = INVALID_WHEN_EXPLICIT_DECLARATION_REQUIRED
- SHIELD = NON_WEAPON_SECONDARY_REQUIRES_PROFICIENCY_ESCUDO
- TWO_HANDED_MAIN_BLOCKS_SECONDARY = YES

Nenhum campo de implementação ou schema é prescrito por esta minuta.

## 9. Limites de catálogo e autoridade

- A tabela original de 22 armas das Regiões 1–5 é preservada; as cinco armas de Confins vêm da fonte regional canônica indicada.
- Os 12 Cajados/Bastões regionais com lista vazia permanecem dados candidatos. Não são acrescentados como identidades canônicas de §9 antes da conciliação de release.
- Escudo não integra a tabela de armas.
- Nenhum dos 226 template IDs candidatos é declarado validado em release.
- O contrato v1.0.0 FINAL continua sendo a autoridade operacional até uma publicação versionada e atualização autorizada de SOURCE_AUTHORITY.md.
