# ASTERION — FONTE DE CONTEÚDO REGIONAL
## 🌫️ Confins do Véu · v1.0.0 FINAL

**Estado:** **Fonte Regional de Game Design FINAL APROVADA**, condicionada à sincronização do índice de autoridade antes do handoff ao Codex. **Aprovação de conteúdo:** 2026-10-18.  
**Região:** `region.confins_do_veu` · **Nv.51–60** · **Campanha:** P31–P36 · **Secundárias:** S31–S36.  
**Fontes superiores:** `ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`; `ASTERION_BIBLIA_CANONICA_MUNDO_REGIOES_BESTIARIO_NPCS_v3.0_FINAL.md`.  
**Referência de fechamento regional anterior:** `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_FINAL.md` (validada, 1.987 linhas).  
**Contrato global correlato:** `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`, preparado em etapa própria; seu reconhecimento no índice `SOURCE_AUTHORITY` deve ser confirmado antes de formalização mecânica. Este documento declara metadata de todas as armas que introduz, sem deduzi-la da forma ou de Classe.

**Status dos dados:** todo número novo de conteúdo, nome regional novo, ID novo e composição específica abaixo é uma **decisão regional C deliberada e APROVADA pelo Game Design nesta revisão**. Valores/sistemas da Fonte Mestra são **A** e identidades importadas da Bíblia/Altos são **B**. O registro desta Fonte e do contrato Weapon Metadata no `SOURCE_AUTHORITY` continua **pendente de sincronização externa**; não se presume registro concluído.

**Princípio:** *Nos Confins, a verdade não desaparece quando dois registros discordam; ela exige descobrir por que ambos puderam existir.*

**Escopo fechado neste documento:** seis Locais, cinco Braseiros permanentes, doze Missões, quatro Materiais Básicos Grau VI, nove criaturas-base e três Elites, pools, Ronda, Desbravar, duas Masmorras completas, Chefes e bestiário, chefe opcional de S36, Regente Fraturado, Códice, Feitos, catálogo de Crafting Grau VI, Runas, Encantamentos, Alquimia, Receitas, economia auditável, progressão a Legado e inventário de IDs. Nenhuma arquitetura, schema ou migration é prescrita.

**Regras de precedência:** GDD para sistemas/fórmulas; Bíblia para lore, NPCs, identidades e limites; Altos para a condição exata de entrada e padrão editorial; esta Fonte proposta somente para decisões regionais novas que não colidam com superiores.

# 0. Protocolo de autoridade e validação FINAL

- **A — Global derivado:** nível das Missões, XP, Coroas, UC, UM, raridade de Equipamento de Campanha, templates de recompensa, caps, perfis estatísticos, Vigor, Bestiário, Saque, Ronda, Masmorra, Crafting, Alquimia, Runas, Encantamentos, Legado e arredondamentos. Estes NÃO são rebalanceados aqui.
- **B — Cânone superior:** região, faixas, seis Locais, dois nomes de Masmorra e Chefes, cinco NPCs, nove criaturas-base, três Elites, respectivos arquétipos/raridades, P31–P36/S31–S36 e seus eixos narrativos, revelação central e natureza do Regente/Avesso.
- **C — Conteúdo regional aprovado:** nomes/IDs de Braseiros e materiais, níveis exatos de criaturas, kits, IA, pools, composição do Grau VI, encontros, escolhas de itens, resultados exploratórios, Feitos, receitas e elementos concretos da cena. A deliberação explícita consta na §29.

**Proibição:** não transformar narrativa em nova mecânica de viagem no tempo, inimigo senciente chamado Avesso, duplicação de item/recompensa, sétima Região, proficiência de Classe ou dungeon engine própria.

# 1. Identidade e continuidade

**Ícone:** 🌫️. **Faixa:** Nv.51–60. **Hub:** Último Refúgio. **Chefe final:** Regente Fraturado.  
**Fluxo canônico:** `Marcha Nebulosa → Último Refúgio → Estradas Ausentes → Fraturas do Limiar → Nó Central → Câmara da Regência`.

Ao entrar, o personagem sabe legitimamente que a Regência existiu, a Convergência buscava recalibrar a rede, os Desvelados começaram como dissidência legítima e uma ala radical sabotou a Âncora Central em acoplamento excepcional. **Não** sabe integralmente o que é o Avesso, a chance histórica de êxito da Convergência, a sequência final completa ou a natureza do Regente.

O Último Refúgio é um hub **multi-racial** de orientação redundante e cuidado: Vigília de Referência, Cartógrafos da Ausência, registros duplos, testemunhas independentes e Braseiros materiais. A cultura não controla o Véu por rituais, não cura Fraturas e não rotula testemunhas contraditórias como mentirosas.

Progressão conceitual: observar duas leituras → nomear Fratura → compreender Avesso como estado → compreender Âncora Central como coordenação → reconstruir Convergência, sabotagem, Regência e cascata → encerrar protocolo impossível. O final não elimina o problema cosmológico; restaura possibilidade de escolha presente.

**Continuidade canônica final:** deterioração do Véu precede civilização asteriana; Âncoras funcionaram e compraram tempo, com dependência e desigualdade; Convergência provavelmente estabilizaria por gerações sem sabotagem, mas não curaria eternamente; ala de Neris Olan autorizou sabotagem consciente esperando isolamento; Cael Rhen prosseguiu sob risco de colapso por interrupção; a Ruptura foi cascata de múltiplos fatores. Códice revela só o que evidências efetivamente sustentam, nunca onisciência. Projeto Hemaris permanece programa biomédico de sobrevivência que degenerou em coerção; Hemários modernos não herdam culpa.

**Saída regional:** P36 concluída é o marco narrativo da campanha completa. Nv.60 + P36 concluída torna o primeiro Legado **elegível**, não executado automaticamente. O personagem pode continuar no mundo em Nv.60, fazer secundárias/Masmorras/Crônica ou ascender num local seguro válido seguindo o GDD. Campanha NÃO repete após Legado e níveis altos voltam a restringir acesso a conteúdo pela faixa. Não há Nv.61. XP recebida em Nv.60 é consumida/descartada no cap, não guardada para Legado.

# 2. Locais e navegação — contrato de gates

`unlock.location.*` = direito **persistente de acesso real pelo Road/Travel**, não simples existência do ID no catálogo; chegada válida registra descoberta. `unlock.hunt.*`, `unlock.explore.*`, `unlock.round.*` e `unlock.dungeon.*` são direitos independentes e com gates próprios. Exibir a rota futura no diálogo não a concede. Não existem custos especiais de passagem nem ganho de XP só por Road.

| Local (ID) | Direito de acesso/descoberta | Uso | Caçada | Desbravar | Ronda | Masmorra | Braseiro |
|---|---|---|---|---|---|---|---|
| `location.confins.marcha_nebulosa` — Marcha Nebulosa | P30 concluída + Nv.51; P31 etapa 1 | P31, S31 | P31 concluída | P31 concluída | P31 + vitória manual local posterior | — | Braseiro do Marco Duplo |
| `location.confins.ultimo_refugio` — Último Refúgio | chegada válida P31 etapa 5 | P31–P36, S32–S36, hub | não | não | não | — | Braseiro da Testemunha |
| `location.confins.estradas_ausentes` — Estradas Ausentes | P31 concluída + ativação válida de P32 Nv.53 | P32, S32 | P32 concluída | P32 concluída | P32 + vitória manual local posterior | Arquivo do Retorno | Braseiro da Estrada Conferida |
| `location.confins.fraturas_limiar` — Fraturas do Limiar | P32 concluída + ativação válida de P33 Nv.55 | P33, S33, S34 | P33 concluída | P33 concluída | P33 + vitória manual local posterior | — | Braseiro do Limiar Firme |
| `location.confins.no_central` — Nó Central | P33 concluída + ativação válida de P34 Nv.57 | P34, P35, S34, S35, S36 | P34 concluída | P34 concluída | P34 + vitória manual local posterior | Câmara das Contradições | Braseiro do Nó de Retorno |
| `location.confins.camara_regencia` — Câmara da Regência | P35 etapa final; P36 exige Nv.60 | P35, P36 | não | não | não | — | nenhum |

**Semântica de ativação:** uma missão pode ser ofertada somente quando missão anterior e nível são válidos. Ativação válida cria/retoma a Missão em Andamento e concede a navegação para seu Local de objetivo. A conclusão dessa Missão, e **não** a mera ativação, concede Caçada/Desbravar local.

**Não antecipar:** P31 só concede acesso à Marcha e ao Último Refúgio. P32 abre Estradas; P33 abre Fraturas; P34 abre Nó; P35 abre Câmara. Cada registro de Local/atividade é individual e idempotente. Atividade bloqueada não fica elegível por estar em Grupo com alguém mais avançado.

**Chegada ao Local vs. conclusão da missão:** a chegada grava descoberta e pode alimentar Códice sem liberar farm; antes do gate de conclusão, somente objetivos/contexto de Quest são utilizáveis. Após P36, Câmara permanece conhecida e acessível como área de memória/visita, sem Caçada/Desbravar/Ronda normal e sem respawn econômico do Chefe.

# 3. Braseiros

| ID | Nome | Local | Registro e gate | Travessia permanente |
|---|---|---|---|---|
| `bonfire.confins.marco_duplo` | Braseiro do Marco Duplo | Marcha Nebulosa | P31 etapa 3, após entrada Nv.51 | sim |
| `bonfire.confins.testemunha` | Braseiro da Testemunha | Último Refúgio | P31 etapa 6 | sim |
| `bonfire.confins.estrada_conferida` | Braseiro da Estrada Conferida | Estradas Ausentes | Desbravar grande único; P32 concluída | sim |
| `bonfire.confins.limiar_firme` | Braseiro do Limiar Firme | Fraturas do Limiar | Desbravar grande único; P33 concluída | sim |
| `bonfire.confins.no_retorno` | Braseiro do Nó de Retorno | Nó Central | Desbravar grande único; P34 concluída | sim |

**5 permanentes; Câmara sem Braseiro.** Todo Braseiro é material, seguro, verificável; não é portal nem ritual que domestica o Véu. Desbloqueio descoberto apenas uma vez por personagem, sem reward repetido.

Braseiros internos condicionais de Masmorra: `dungeon_bonfire.confins.arquivo.ala_retorno` (**Braseiro da Ala de Retorno**) e `dungeon_bonfire.confins.contradicoes.patio_referencia` (**Braseiro do Pátio de Referência**). No máximo 1 por run, após encontro 3, sorteio Estável70%/Fraturada40%/Ruptura20%; nunca pertencem à Travessia permanente.

# 4. NPCs persistentes — funções sem alterar biografias

| NPC | ID | Papel mecânico | Missões |
|---|---|---|---|
| **Sera Nol**, Velada, coordena Vigília de Referência | `npc.confins.sera_nol` | principal autoridade civil do hub, validação de rotas, primeira e última decisão pública | P31, P32, P35, P36, S35, S36 |
| **Roven Pell**, Remanescente, registrador | `npc.confins.roven_pell` | Códice, arquivo, notação de documentos contraditórios, não escolhe verdade arbitrária | P31, P33, P35, S32, S33, S35 |
| **Talen Nyr**, Cinéreo, Cartógrafos da Ausência | `npc.confins.talen_nyr` | campo, Caçada, Desbravar, Ronda, localização do Arquivo e trilhas de retorno | P31, P32, P33, S31, S34 |
| **Eris Val**, Alvorana, Herdeira de registros centrais | `npc.confins.eris_val` | Âncora Central, Convergência, validação histórica, Câmara das Contradições | P34, P35, P36, S35 |
| **Haro Sen**, Hemário, Guardador de Braseiro | `npc.confins.haro_sen` | Braseiros, apoio a recém-chegados, Alquimia/Consumíveis, suporte de viagem | P31, S32, S36 |

Ofícios normais Grau VI no **Último Refúgio**: Ferreiro, Curteiro, Joalheiro, Alquimista, Artífice (facilidade de crafting normal do hub, não novos personagens). Nenhum NPC persistente novo é necessário. `Oris Pell` pertence exclusivamente às Várzeas; **Roven Pell** é o registrador canônico dos Confins.

# 5. Economia de Missões — fórmula global, Grade VI

**Obrigatório A:** `XP(n)=round_100(4000+750n+43n²)`, com `XP_ref(60)=203.800` apenas para normalização no cap; recompensa fixa percentual usa `round_half_up(XP_ref(n)×percentual)`; `C(n)=round_10(100+15n)`; recompensa em Coroas=`round_10(C(n)×UC)`; `1 UM = 2 Materiais Básicos regionais vinculados`. Principais comuns 50%, clímax 90%, Secundária Curta20%/Padrão35%/Longa50%. `round_10` usa ties-to-even.

| Missão | Nv. | Tipo | XP de Missão | UC | Coroas | UM | Básicos vinculados | Distribuição C proposta |
|---|---:|---|---:|---:|---:|---:|---:|---|
| P31 | 51 | Principal | 77.050 | 1 | 860 | 1 | 2 | 1 Ferro de Baliza + 1 Musgo de Limiar |
| P32 | 53 | Principal | 82.250 | 1 | 900 | 2 | 4 | 2 Ferros de Baliza + 1 Musgo de Limiar + 1 Pó de Referência |
| P33 | 55 | Principal | 87.650 | 1 | 920 | 0 | 0 | — |
| P34 | 57 | Principal | 93.250 | 1,25 | 1.200 | 2 | 4 | 2 Ferros de Baliza + 1 Couro de Marcha + 1 Pó de Referência |
| P35 | 59 | Principal | 98.950 | 1,25 | 1.220 | 2 | 4 | 2 Ferros de Baliza + 1 Musgo de Limiar + 1 Pó de Referência |
| P36 | 60 | Clímax | 183.420 | 2 | 2.000 | 4 | 8 | 3 Ferros de Baliza + 1 Couro de Marcha + 1 Musgo de Limiar + 3 Pós de Referência |
| S31 | 52 | Curta | 31.860 | 0,5 | 440 | 0 | 0 | — |
| S32 | 54 | Padrão | 59.465 | 0,75 | 680 | 1 | 2 | 1 Couro de Marcha + 1 Musgo de Limiar |
| S33 | 55 | Curta | 35.060 | 0,5 | 460 | 1 | 2 | 1 Ferro de Baliza + 1 Musgo de Limiar |
| S34 | 57 | Padrão | 65.275 | 0,75 | 720 | 2 | 4 | 1 Ferro de Baliza + 1 Couro de Marcha + 1 Musgo de Limiar + 1 Pó de Referência |
| S35 | 58 | Padrão | 67.270 | 0,75 | 730 | 2 | 4 | 1 Ferro de Baliza + 2 Musgos de Limiar + 1 Pó de Referência |
| S36 | 60 | Longa | 101.900 | 1,25 | 1.250 | 4 | 8 | 2 Ferros de Baliza + 2 Couros de Marcha + 2 Musgos de Limiar + 2 Pós de Referência |

**Auditoria:** Principais **622.570 XP / 7.100 Coroas / 7,5 UC / 11 UM / 22 Básicos**, Secundárias **360.830 XP / 4.280 Coroas / 4,5 UC / 10 UM / 20 Básicos**. Total regional **983.400 XP / 11.380 Coroas / 12 UC / 21 UM / 42 Básicos vinculados**. Distribuição por identidade: **15 Ferros de Baliza, 6 Couros de Marcha, 11 Musgos de Limiar, 10 Pós de Referência = 42**.

**Faixa:** `51→60` soma **1.580.500 XP**; **não** existe XP de `60→61`. O marco P36 concede nominalmente **183.420 XP (90%×203.800)** conforme a referência de clímax Nv.60, mas em personagem já no cap a parcela XP não vira overflow, reserva, moeda nem XP pós-Legado; a conclusão narrativa e demais recompensas permanecem entregues uma única vez. P35/P36 não autorizam reset automático de campanha. A curva/pagamento global tem prioridade sobre qualquer somatório regional em documento editorial.

**Equipamentos de Campanha:** P33 (terceira Principal) escolha de 1 entre **3 Raros Nv.55**; P36 escolha de 1 entre **3 Lendários Nv.60**. Sempre +0, Vinculado ao Adquirir, somente um por Missão/personagem, sem proc, Arte, passiva ou poder acima do budget global.

# 6. Contratos comuns de Missões

- Missões Principais não podem ser abandonadas; requisito de nível/progresso ausente as mantém **Suspensas**, preservando progressos válidos, restauradas quando o requisito se torna válido. Ativação/aceite ocorre somente quando elegível; abrir UI, catálogo ou conversa antecipada não cria grant.
- Missões Secundárias são opcionais, podem ser abandonadas e reaceitas sob as regras globais: progresso narrativo/único legitimamente commitado e recompensas já liquidadas persistem, sem refazer combate de vitória válida ou regenerar pagamento.
- Em Grupo 1–4, objetivos físicos e encontros sinalizados **Compartilhável** progridem apenas para participantes presentes/elegíveis; fala, escolha, fragmentos de Códice, estados pessoais e recompensas são **Pessoais**. Um veterano não concede progressão a participante que não satisfaz gates individuais.
- Encontros `MISSION_SCRIPTED` são fixos na composição/nível especificado, **0 Vigor, 0 EnemyXP, 0 Coroas, 0 Saque, 0 Runa, 0 material, 0 núcleo, 0 pity**, salvo prêmio explicitamente ligado à Missão. Vitória válida progride; derrota não progride; retry recupera o mesmo objetivo, sem reroll de recompensa. Bestiário pode observar fatos sem gerar economia oculta.
- Cada conclusão paga exatamente uma vez, inclusive após reconnect ou falha na entrega material. Diálogos, leitura de registro, descoberta e unlock não multiplicam XP. World state servidor global **não** muda por progresso pessoal de campanha.
- Não há decisões econômicas em diálogos, exceto escolha P33/P36; divergências de testemunhas são interpretadas/registradas, não escolhidas como ramo alternativo do final.

# 7. Missões Principais P31–P36

## 7.1 P31 — Onde o Véu Afina

**ID:** `mission.confins.p31` · **Nv.51** · **início:** automático após P30 concluída + Nv.51 no acesso Altos→Marcha; **responsáveis:** Talen Nyr no campo, Sera Nol e Haro Sen no hub. **Local:** Marcha Nebulosa → Último Refúgio.

1. **[Pessoal]** cruzar a fronteira habilitada após P30/Nv.51; conceder `unlock.location.confins.marcha_nebulosa` e registrar chegada válida.
2. **[Compartilhável]** verificar dois marcos físicos da mesma estrada com posições incompatíveis, fotografias não requeridas e duas leituras honestas: uma anotação recente de Talen e uma marca do próprio terreno.
3. **[Compartilhável]** registrar `bonfire.confins.marco_duplo` e aprender regra civil de verificação por testemunhas, sem nova mecânica global.
4. **[Compartilhável]** enfrentar exatamente 1 `creature.confins.cao_nevoa` **Nv.51** roteirizado (economia 0, sem Variante), que é animal real.
5. **[Compartilhável]** chegar ao Último Refúgio; conceder `unlock.location.confins.ultimo_refugio` e descobrir o Local.
6. **[Compartilhável]** descobrir `bonfire.confins.testemunha` com Haro Sen.
7. **[Pessoal]** comparar os dois registros com Sera e Roven, preservando discrepância como dado, sem declarar mentira ou “duas dimensões”.
8. **[Pessoal]** adquirir `codex.confins.duas_leituras_rota` (Trecho *Dois marcos honestos*) e concluir com Sera.

**Saídas permanentes:** somente Marcha e Último Refúgio conhecidos; ambos os Braseiros; `unlock.hunt.confins.marcha`, `unlock.explore.confins.marcha`, `narrative.confins.duas_leituras_confirmadas`. **Não** abrir Estradas/Fraturas/Nó/Câmara. **Pagamento:** 77.050 XP +860 Coroas +1 Ferro de Baliza +1 Musgo de Limiar. Reconnect/derrota preservam os registros e o ponto de retomada; nenhuma escolha narrativa exclusiva.

## 7.2 P32 — A Fratura

**ID:** `mission.confins.p32` · **Nv.53** · **giver:** Sera Nol com exploração de Talen. **Pré:** P31 concluída + Nv.53; ativação válida concede `unlock.location.confins.estradas_ausentes`. **Local:** Estradas Ausentes.

1. **[Pessoal]** receber dois traçados de ida/volta do mesmo trajeto, sem aceitar uma “versão correta” automaticamente.
2. **[Compartilhável]** alcançar Estradas Ausentes; registrar chegada.
3. **[Compartilhável]** conferir três indícios: fundação terminada, marco que não existe no mapa e registro de retorno discordante.
4. **[Compartilhável]** enfrentar 1 `creature.confins.andarilho_repetido` **Nv.53** roteirizado (economia zero, sem Variante); registrar que não é clone nem alma.
5. **[Pessoal]** reunir as evidências com Talen/Sera; legitimar o termo **Fratura** como falha localizada de estabilidade, não portal.
6. **[Pessoal]** registrar `codex.confins.fratura_definicao`; fechar P32.

**Saídas:** `unlock.hunt.confins.estradas`, `unlock.explore.confins.estradas`; `narrative.confins.fratura_reconhecida`. Arquivo do Retorno **não** é descoberto automaticamente. **Pagamento:** 82.250 XP +900 Coroas +2 Ferros +1 Musgo +1 Pó. Nenhuma revelação completa do Avesso.

## 7.3 P33 — O Avesso

**ID:** `mission.confins.p33` · **Nv.55** · **giver:** Roven Pell com Talen Nyr. **Pré:** P32 concluída + Nv.55; ativação concede `unlock.location.confins.fraturas_limiar`. **Local:** Fraturas do Limiar.

1. **[Compartilhável]** entrar e registrar o Local; identificar duas marcas de referência que discordam enquanto ambas são fisicamente observáveis.
2. **[Compartilhável]** conferir três evidências: posição de pedra, estado de desgaste e sequência de observação de trilha.
3. **[Compartilhável]** enfrentar `creature.confins.casca_reflexo` **Nv.55** (economia zero, sem Variante).
4. **[Pessoal]** ler com Roven a definição do termo **Avesso**: estado em que relações de causalidade/matéria/identidade deixam de ser confiáveis; não lugar, malignidade ou vontade.
5. **[Pessoal]** registrar `codex.confins.avesso_estados`, sem afirmar efeitos nunca observados.
6. **[Pessoal]** escolher **1 Raro Nv.55** de três opções P33, concluir com Roven.

**Saídas:** `unlock.hunt.confins.fraturas`, `unlock.explore.confins.fraturas`; `narrative.confins.avesso_nomeado`. **Pagamento:** 87.650 XP +920 Coroas + escolha Rara.

Escolha econômica, todos Raros +0, vinculados ao adquirir, item_level55:
- `equipment.confins.campaign.p33.capuz_dupla_leitura` — **Capuz da Dupla Leitura** · Cabeça;
- `equipment.confins.campaign.p33.selo_marco_valido` — **Selo do Marco Válido** · Acessório;
- `equipment.confins.campaign.p33.relicario_registro_incompleto` — **Relicário do Registro Incompleto** · Artefato.

## 7.4 P34 — A Âncora Central

**ID:** `mission.confins.p34` · **Nv.57** · **giver:** Eris Val e Sera Nol. **Pré:** P33 concluída + Nv.57; ativação concede `unlock.location.confins.no_central`. **Local:** Nó Central.

1. **[Pessoal]** receber de Eris dois registros técnicos incompletos de coordenação regional.
2. **[Compartilhável]** entrar no Nó Central; examinar três pontos físicos: condução de referência, alinhamento de rotas, comunicação de falha.
3. **[Compartilhável]** enfrentar um `elite.confins.custodio_desfasado` **Nv.57** em combate roteirizado (economia zero, sem Variante). **Exceção declarada de conteúdo `MISSION_SCRIPTED`:** o Nv.57 é fixo somente em P34 e não altera a faixa Nv.59–60 da Elite em Caçada/Ronda.
4. **[Compartilhável]** localizar evidência de que diferentes Âncoras já estabilizavam regiões antes da noite final.
5. **[Pessoal]** comparar interpretação de Eris com documentação civil em Roven; registrar que **Âncora Central é coordenação/referência**, não fonte de energia ou interruptor mestre.
6. **[Pessoal]** adquirir `codex.confins.ancora_central_coordenacao`; concluir com Sera/Eris.

**Saídas:** `unlock.hunt.confins.no`, `unlock.explore.confins.no`; `narrative.confins.ancora_central_compreendida`. Câmara das Contradições só é descoberta por Desbravar; P34 não a concede por script. **Pagamento:** 93.250 XP +1.200 Coroas +2 Ferros +1 Couro +1 Pó.

## 7.5 P35 — A Noite da Convergência

**ID:** `mission.confins.p35` · **Nv.59** · **giver:** Eris Val, Roven Pell e Sera Nol. **Pré:** P34 concluída + Nv.59. **Local:** Nó Central → rota final à Câmara da Regência.

1. **[Compartilhável]** obter registros de três cadeias documentais (Custódia das Âncoras, Regência de Continuidade, oposição dos Desvelados) no Nó Central. A conclusão de S35 **não** é requisito.
2. **[Compartilhável]** conferir materialmente a sequência técnica: deterioração prévia, funcionamento das Âncoras, dependência crescente e Convergência em rede acoplada.
3. **[Compartilhável]** vencer `creature.confins.vigia_desfasado` **Nv.59** roteirizado (economia zero, sem Variante).
4. **[Pessoal]** reconstruir com Eris e Roven que Neris Olan/ala radical autorizou sabotagem consciente visando isolamento regional controlado apesar de risco catastrófico; preservar oposição legítima sem culpabilização coletiva.
5. **[Pessoal]** registrar que Cael Rhen prosseguiu sob risco de colapso imediato também ao interromper; não atribuir desejo de destruir mundo.
6. **[Pessoal]** registrar `codex.confins.convergencia_reconstrucao` e `codex.confins.cadeia_ruptura_documentada`, com procedência e limites das lacunas.
7. **[Compartilhável]** abrir a rota física da Câmara da Regência e conceder `unlock.location.confins.camara_regencia` **nesta etapa**, sem exigir Nv.60 para acesso; Nv.60 pertence ao gate de P36.
8. **[Pessoal]** encerrar o relato com Sera; o Regente Fraturado ainda não foi confrontado.

**Saídas:** Câmara conhecida/acessível; `narrative.confins.noite_convergencia_reconstruida`. **Pagamento:** 98.950 XP +1.220 Coroas +2 Ferros +1 Musgo +1 Pó. Sem solução eterna, sem cronologia onisciente.

## 7.6 P36 — O Regente Fraturado

**ID:** `mission.confins.p36` · **Nv.60** · **início:** automático ao satisfazer P35 concluída + Nv.60; **responsáveis:** Sera, Eris e Roven. **Local:** Câmara da Regência, já acessível desde P35 etapa 7.

1. **[Compartilhável]** entrar na Câmara; comparar registro institucional, matéria local e marcas de estados incompatíveis.
2. **[Compartilhável]** examinar três evidências que não formam um único relato contínuo dos últimos minutos; declarar limites do conhecimento.
3. **[Compartilhável]** iniciar `boss.confins.regente_fraturado` sob as regras globais Solo/Grupo de Chefe de Campanha.
4. **[Compartilhável]** vencer o Regente Fraturado, com seus três protocolos e telegraph completo; derrota mantém a etapa ativa.
5. **[Pessoal]** conceder uma vez `material.special.confins.core.regente_fraturado` — **1 Núcleo do Regente Fraturado**, por primeira vitória válida, sem settlement de Caçada.
6. **[Pessoal]** ler registro pós-confronto: o Regente é manifestação sobreposta de Cael Rhen, protocolos, registros, matéria e estados avessos; **não Cael vivo/ressuscitado**. A operação encerrada não cura Véu nem destrói Avesso.
7. **[Pessoal]** registrar `codex.confins.regente_natureza` e `codex.confins.protocolo_encerrado`; revelar `recipe.confins.regente.eco_encerramento` uma vez.
8. **[Pessoal]** escolher 1 dos três Equipamentos **Lendários Nv.60**; completar a Campanha com o diálogo final de Sera, sem exigir Masmorras, S31–S36 ou Feitos.

**Saídas:** `narrative.confins.protocolo_impossivel_encerrado` + `unlock.campaign.first_journey_complete`; `world_state` permanece sem alteração global pelo personagem. **Pagamento nominal:** 183.420 XP (sujeita ao cap60, sem reserva) +2.000 Coroas +3 Ferros +1 Couro +1 Musgo +3 Pós +1 Lendário entre três.

Escolhas (todas +0, Vinculadas ao Adquirir, sem efeitos fora do orçamento Lendário):
- `equipment.confins.campaign.p36.guarda_ultimo_protocolo` — **Guarda do Último Protocolo** · Arma Secundária · handedness1H, forma Maça, tag melee explícita;
- `equipment.confins.campaign.p36.selo_referencia_presente` — **Selo da Referência Presente** · Acessório;
- `equipment.confins.campaign.p36.relicario_ordem_findada` — **Relicário da Ordem Findada** · Artefato.

**Primeira jornada/Legado:** P36 concluída + Nv.60 = elegibilidade para Legado I; Legado é ato separado em local seguro e pelas condições globais. Campanha P1–P36 nunca reinicia. P36 não cria ramo alternativo, eleição de Crônica, cura do Véu ou expansão de cap. A Câmara continua acessível como Local de memória, sem farm repetível do Regente. A derrota retorna ao Braseiro da Testemunha; Retry preserva o encounter e seu direito de primeira vitória, sem reroll econômico.

# 8. Missões Secundárias S31–S36

Todas as S são **opcionais**; abandonar/reaceitar não retrocede Códice, feitos, vitórias únicas, descobertas ou pagamento já consolidado. Oferta não cria Aceite. Objetivos compartilháveis exigem os mesmos gates individuais. Encontros roteirizados têm economia própria zero. A conclusão depende de diálogo/registro pessoal final após etapas explícitas.

## 8.1 S31 — Duas Vezes a Mesma Estrada

**ID:** `mission.confins.s31` · **Nv.52, Curta** · **giver:** Talen Nyr na Marcha · **gate:** P31 concluída + Nv.52 · **Local:** Marcha Nebulosa **somente**; não entra prematuramente em Estradas Ausentes (P32 é Nv.53).

1. [Pessoal] aceitar levantamento de pegadas de Talen; 2. [Compartilhável] observar 3 pontos da mesma trilha na Marcha; 3. [Compartilhável] encontrar duas impressões plausíveis com número diferente de passadas, sem declarar clones; 4. [Compartilhável] enfrentar 1 `creature.confins.gralha_duas_sombras` Nv.52 roteirizada, economia zero; 5. [Pessoal] comparar com Talen e registrar `codex.confins.pegadas_incompativeis`; 6. [Pessoal] concluir com Talen.

**Recompensa:** 31.860 XP +440 Coroas, sem Material/Equipamento. **Persistência:** `quest.confins.s31.completed`; Códice idem; não concede Local nem Ronda.

## 8.2 S32 — A Casa que Não Chegou

**ID:** `mission.confins.s32` · **Nv.54, Padrão** · **giver:** Haro Sen com Roven Pell · **gate:** P32 concluída + Nv.54 · **Local:** Estradas Ausentes / retorno ao Último Refúgio.

1. [Pessoal] aceitar relato de uma casa cuja base consta em dois registros; 2. [Compartilhável] reconhecer 3 elementos físicos da fundação; 3. [Compartilhável] recuperar duas fichas sem valor econômico registrando presença/ausência; 4. [Compartilhável] enfrentar 1 `creature.confins.aranha_limiar` Nv.54 (roteirizada, economia zero); 5. [Pessoal] comparar as fichas com Roven, sem decidir qual memória é “falsa”; 6. [Pessoal] registrar `codex.confins.casa_presente_ausente`; concluir com Haro.

**Recompensa:** 59.465 XP +680 Coroas +1 Couro de Marcha +1 Musgo de Limiar. **Persistência:** `quest.confins.s32.completed`. Não cria NPC familiar permanente nem Local extra.

## 8.3 S33 — Nomes em Ordem Errada

**ID:** `mission.confins.s33` · **Nv.55, Curta** · **giver:** Roven Pell · **gate:** P33 concluída + Nv.55 · **Local:** Último Refúgio → Fraturas do Limiar.

1. [Pessoal] aceitar reconciliação de duas listas; 2. [Compartilhável] localizar duas inscrições de campo na zona já acessível; 3. [Pessoal] separar erro simples de cópia comprovável de discrepância material não resolvida; 4. [Pessoal] registrar `codex.confins.nomes_ordem_errada` com ambas as evidências, sem criar “pessoa duplicada”; 5. [Pessoal] concluir com Roven. **Sem combate obrigatório.**

**Recompensa:** 35.060 XP +460 Coroas +1 Ferro de Baliza +1 Musgo de Limiar. **Persistência:** `quest.confins.s33.completed`. Não concede novo gate espacial.

## 8.4 S34 — A Testemunha de Ontem

**ID:** `mission.confins.s34` · **Nv.57, Padrão** · **giver:** Talen Nyr · **gate:** P34 concluída + Nv.57 · **Local:** Fraturas do Limiar → periferia acessível do Nó Central.

1. [Pessoal] receber depoimento datado que antecede seu aparente evento de emissão; 2. [Compartilhável] conferir duas marcas físicas e uma ficha com cadeia de custódia; 3. [Compartilhável] vencer `creature.confins.andarilho_repetido` Nv.57, zero economia, sem Variante (**override fixo `MISSION_SCRIPTED` exclusivo de S34; faixa normal Nv.52–56 preservada**); 4. [Pessoal] registrar discrepância na ordem local sem declarar profecia ou deslocamento temporal consciente; 5. [Pessoal] adquirir `codex.confins.testemunha_ontem`; concluir com Talen.

**Recompensa:** 65.275 XP +720 Coroas +1 Ferro +1 Couro +1 Musgo +1 Pó. **Persistência:** `quest.confins.s34.completed`. Não modifica ordem da Campanha.

## 8.5 S35 — O Registro que Discorda

**ID:** `mission.confins.s35` · **Nv.58, Padrão** · **giver:** Roven Pell / Eris Val · **gate:** P34 concluída + Nv.58, **não P35** (P35 exige Nv.59) · **Local:** Nó Central / Último Refúgio.

1. [Pessoal] receber cópias físicas de duas ordens oficiais sobre o mesmo intervalo; 2. [Compartilhável] localizar a origem de dois lacres e a trilha de transmissão; 3. [Compartilhável] vencer 1 `creature.confins.vigia_desfasado` Nv.58 roteirizado, economia zero; 4. [Pessoal] preservar ordens incompatíveis lado a lado; não escolher uma para apagar; 5. [Pessoal] adquirir `codex.confins.duas_ordens_oficiais`; concluir com Roven/Eris.

**Recompensa:** 67.270 XP +730 Coroas +1 Ferro +2 Musgos +1 Pó. **Persistência:** `quest.confins.s35.completed`; P35 pode reconhecer o Trecho se existir, mas não o exige nem repaga seu XP.

## 8.6 S36 — Depois da Última Ordem

**ID:** `mission.confins.s36` · **Nv.60, Longa** · **giver:** Haro Sen e Sera Nol · **gate:** P36 concluída + Nv.60, sem exigência de Masmorra/Feito · **Local:** Último Refúgio → Nó Central (sem novo Local).

1. [Pessoal] ouvir Haro/Sera sobre quais rotinas de referência ainda protegem moradores.
2. [Compartilhável] inspecionar três pontos de controle civil, distinguindo rotina necessária de ordem obsoleta.
3. [Compartilhável] recolher duas provas materiais de que um verificador antigo continua barrando retorno mesmo após protocolo final encerrado.
4. [Compartilhável] iniciar encontro roteirizado exclusivo contra `boss.confins.s36.verificador_sem_testemunhas`, **Nv.60**; vitória obrigatória para esta Secundária, não para Legado.
5. [Pessoal] registrar Bestiário do verificador como fatos observados, sem atribuir consciência à falha.
6. [Pessoal] registrar `codex.confins.depois_ultima_ordem`; decidir apenas **como narrar** a continuidade de procedimentos civis, não abolir sistemas globais nem mudar mundo de todos.
7. [Pessoal] concluir com Sera e Haro. A rotina civil razoável persiste; não se cria “final secreto” nem estado de mundo alternativo.

**Recompensa:** 101.900 XP nominal (em Nv.60 descartada pela regra do cap) +1.250 Coroas +2 de cada Básico Grau VI. **Persistência:** `quest.confins.s36.completed`; `achievement.confins.s36` uma vez. Abandono/reaceite preserva vitória do boss e não regenera Núcleo, loot ou Economia.

### Chefe opcional exclusivo S36 — Verificador sem Testemunhas (C)

**ID:** `boss.confins.s36.verificador_sem_testemunhas` · BOSS Nv.60 · Controlador · 1–4 jogadores; perfil de Chefe normal + scaling global de Chefe de Campanha, sem perfil de Caçada/Masmorra.

Artes: **Golpe de Comprovação** 100% ATQ; **Desvio de Registro** 90% ATQ + AGI−10% por 2T CD3; **Selagem de Retorno** Barreira 90% ATQ CD4, máximo 2 usos; **Conferência Final** Preparada 175% ATQ CD5, telegraph completo. Sem adds, Cure, Hard CC, fases ou Variante.

**Economia do encontro:** EnemyXP0, Coroas0, Materiais0, Equipamento0, Runa0, Núcleo0, Fragmentos0, Catalisadores0, pity0, Saque0; nenhuma Primeira Conclusão econômica. Bestiário apenas conhecimento observado, sem marco configurado adicional de XP. Derrota mantém etapa, recovery no Braseiro da Testemunha. Vitória no encontro é idempotente; remuneração é apenas S36. Não aparece em Hunt, Round, Explore ou Dungeon.

# 9. Materiais regionais Grau VI

Quatro categorias obrigatórias globais, sem categoria inédita:

| ID | Nome | Categoria | Origem regional C | Uso |
|---|---|---|---|---|
| `material.confins.ferro_baliza` | **Ferro de Baliza** | Metal VI | ferragens de marcos, vigias, estruturas e atividade econômica | Ferreiro, Joalheiro, Runa, Enchant, receitas |
| `material.confins.couro_marcha` | **Couro de Marcha** | Couro VI | fauna de trilha/limiar, couro tratável | Curteiro, crafting de campo |
| `material.confins.musgo_limiar` | **Musgo de Limiar** | Reagente VI | material vegetal/musgoso verificável, sem portal mágico | Curteiro, Alquimia |
| `material.confins.po_referencia` | **Pó de Referência** | Essência VI | pó físico mineral/residual de balizas e construtos; não energia consciente | Crafting, Artífice, Alquimia |

**Recursos globais:** Catalisador de Elite VI e Fragmento de Aprimoramento VI (identidades e IDs globais preexistentes, sem redefinição regional); Núcleos de Masmorra `material.special.confins.core.arquivo_retorno` e `material.special.confins.core.camara_contradicoes`; Núcleo único de P36 `material.special.confins.core.regente_fraturado`. IDs especiais locais são C; quantidades/drop obedecem fórmulas A.

**Distribuição de Missões auditada:** Ferro15 / Couro6 / Musgo11 / Pó10 =42, já exposta linha a linha na §5. Tudo vinculado pelas regras de recompensa de Missão. Essas quantidades não são a chance de drop em Caçada.

## 9.1 Material Básico por unidade de Caçada/Ronda

Cada seleção abaixo acontece **depois** da regra global definir se houve Material Básico e quantas unidades; os pesos só elegem identidade, individualmente por unidade e ordinal determinístico `material.basic.0`, `material.basic.1` etc. Nunca convertem Comum80% em 100% drop nem adicionam quantidades ao Elite.

- `creature.confins.cao_nevoa` — **Cão de Névoa** · Comum · Predador · Nv.51–54 · material por unidade: **Couro 100%** · habitats M, E.

- `creature.confins.gralha_duas_sombras` — **Gralha de Duas Sombras** · Comum · Predador · Nv.51–54 · material por unidade: **Musgo 60% / Pó 40%** · habitats M, E.

- `creature.confins.andarilho_repetido` — **Andarilho Repetido** · Incomum · Equilibrado · Nv.52–56 · material por unidade: **Ferro 55% / Pó 45%** · habitats E, F.

- `creature.confins.aranha_limiar` — **Aranha de Limiar** · Comum · Controlador · Nv.53–56 · material por unidade: **Musgo 80% / Pó 20%** · habitats E, F.

- `creature.confins.cervo_passo_duplo` — **Cervo de Passo Duplo** · Comum · Bruto · Nv.54–57 · material por unidade: **Couro 90% / Musgo 10%** · habitats M, F.

- `creature.confins.sanguessuga_palida` — **Sanguessuga Pálida** · Comum · Equilibrado · Nv.55–58 · material por unidade: **Musgo 65% / Pó 35%** · habitats F, N.

- `creature.confins.casca_reflexo` — **Casca de Reflexo** · Incomum · Blindado · Nv.55–59 · material por unidade: **Ferro 40% / Pó 60%** · habitats F, N.

- `creature.confins.mariposa_sem_horizonte` — **Mariposa sem Horizonte** · Comum · Conjurador · Nv.56–59 · material por unidade: **Pó 75% / Musgo 25%** · habitats F, N.

- `creature.confins.vigia_desfasado` — **Vigia Desfasado** · Incomum · Blindado · Nv.58–60 · material por unidade: **Ferro 85% / Pó 15%** · habitats N, E.

- `elite.confins.predador_duas_pegadas` — **Predador de Duas Pegadas** · Elite · Predador · Nv.54–56 · material por unidade: **Couro 85% / Pó 15%** · habitats M, E.

- `elite.confins.viuva_intervalo` — **Viúva de Intervalo** · Elite · Controlador · Nv.57–59 · material por unidade: **Musgo 60% / Pó 40%** · habitats E, F.

- `elite.confins.custodio_desfasado` — **Custódio Desfasado** · Elite · Blindado · Nv.59–60 · material por unidade: **Ferro 80% / Pó 20%** · habitats F, N.

**Exceções fixas de missão, sem mutação da faixa de Caçada:** P34 usa `elite.confins.custodio_desfasado` Nv.57, apesar de a Elite permanecer Nv.59–60 no mundo aberto; S34 usa `creature.confins.andarilho_repetido` Nv.57, apesar de sua faixa normal Nv.52–56. São dois encontros obrigatórios `MISSION_SCRIPTED`, ambos com nível explicitamente publicado, sem Variante, sem economia de combate e sem elegibilidade adicional em Caçada/Ronda/Desbravar. O GDD já permite encontros roteirizados com alvo fixo; não se cria mecânica nova nem se altera o nível da Missão.

**Distribuição só de identidade:** soma =100% em todas as criaturas. Cão/Gralha/Aranha/Cervo/Sanguessuga/etc. podem conceder zero material no encontro pela regra global de raridade/categoria. Elites seguem o lote global 3–4 básicos + Catalisador, além do restante da economia global, não pesos de “chance de drop”.

**Legenda de habitat:** M=Marcha Nebulosa, E=Estradas Ausentes, F=Fraturas do Limiar, N=Nó Central. Uma criatura citada em roteiro fora de seu habitat aberto continua encontro roteirizado de missão, não inclusão no pool. Nenhum inimigo de Masmorra tem tabela aberta de Caçada/Ronda. O Verificador S36 e o Regente P36 têm economia exclusiva zero e ficam fora.

# 10. Bestiário — níveis, kits, IA, variantes

Os nove nomes, categorias e arquétipos de criaturas-base e três Elites vêm da **Bíblia v3.0** (B); níveis, habilidades, CD e IA específicos são C. Atributos nunca são números absolutos regionais inventados: `K(n) × Categoria × Arquétipo × Variante × conteúdo × scaling global` com pisos/caps/regras globais. Incomum usa perfil Bestiário `RARE`, sem renomear a raridade player-facing. Todos os efeitos abaixo são atributos/status globais conhecidos, sem “temporização alternativa”, clonagem mecânica ou interação com vontade do Avesso.

## 10.1 Nove criaturas-base

**Cão de Névoa** — `creature.confins.cao_nevoa` · Comum/COMMON · Predador · 51–54.
- Mordida de Marcha `100% ATQ`.
- Corrida entre Marcos `120% ATQ`, CD3.
- Rasgo em Névoa `90% ATQ +1 Sangramento`, CD3.
- IA: inicia rasgo se alvo sem Sangramento; depois maior ataque disponível; sem alteração especial por posição duplicada visual. **Variantes:** Ágil, Furioso.

**Gralha de Duas Sombras** — `creature.confins.gralha_duas_sombras` · Comum/COMMON · Predador · 51–54.
- Bicada de Marca `95% ATQ`.
- Asa de Retorno `115% ATQ`, CD2.
- Vista Contraditória `85% ATQ + PER−10% 2T`, CD3.
- IA: aplica PER Debuff quando ausente; não duplica dano porque o animal parece possuir duas sombras. **Variantes:** Ágil, Furioso.

**Andarilho Repetido** — `creature.confins.andarilho_repetido` · Incomum/RARE · Equilibrado · 52–56.
- Golpe Desfasado `100% ATQ`.
- Passo Refeito `120% ATQ`, CD3.
- Estado Discordante `90% ATQ + DEF−10% 2T`, CD3.
- IA: evita reaplicar DEF Debuff enquanto efeito equivalente tem duração suficiente. Não clona personagem, loot ou turno. **Variantes:** Resistente, Ágil.

**Aranha de Limiar** — `creature.confins.aranha_limiar` · Comum/COMMON · Controlador · 53–56.
- Mordida de Limiar `90% ATQ`.
- Fio Desalinhado `85% ATQ + AGI−10% 2T`, CD3.
- Salto de Perna `120% ATQ`, CD3.
- IA: debuff AGI antes de ação forte quando útil, sem restrição de ação ou Hard CC. **Variantes:** Ágil, Hemorrágico.

**Cervo de Passo Duplo** — `creature.confins.cervo_passo_duplo` · Comum/COMMON · Bruto · 54–57.
- Chifrada Dupla Leitura `105% ATQ`.
- Investida de Trilha `130% ATQ`, CD3.
- Salto de Casco · **Preparada** `175% ATQ`, CD4; telegraph integral, não move o alvo nem aplica Hard CC.
- IA: ação preparada na primeira oportunidade válida após cooldown; não ganha duas ações pelo visual de passo duplo. **Variantes:** Resistente, Furioso.

**Sanguessuga Pálida** — `creature.confins.sanguessuga_palida` · Comum/COMMON · Equilibrado · 55–58.
- Sucção Rasa `95% ATQ`.
- Mordida de Água Fria `85% ATQ +1 Sangramento`, CD3.
- Agarrar sem Trava `115% ATQ`, CD3; só dano, sem imobilização mecânica.
- IA: prioriza um Sangramento vigente, sem Vampirismo oculto, Cura ou mecânica nova. **Variantes:** Ágil, Furioso.

**Casca de Reflexo** — `creature.confins.casca_reflexo` · Incomum/RARE · Blindado · 55–59.
- Placa Repetida `100% ATQ`.
- Cobertura Reflexa · Barreira `95% ATQ`, CD3.
- Tranco de Referência `125% ATQ`, CD3.
- IA: Barreira só quando proteção útil e sem empilhamento fora do global; não replica dano recebido. **Variantes:** Resistente, Furioso.

**Mariposa sem Horizonte** — `creature.confins.mariposa_sem_horizonte` · Comum/COMMON · Conjurador · 56–59.
- Pó do Limiar `95% ATQ`, Dano Direto sem elemento novo.
- Leque Divergente · AoE `75% ATQ`, CD3.
- Giro de Asa `85% ATQ + ATQ−10% 2T`, CD3.
- IA: AoE útil com 2+ alvos; nenhuma manipulação real de perspectiva como status. **Variantes:** Ágil, Furioso.

**Vigia Desfasado** — `creature.confins.vigia_desfasado` · Incomum/RARE · Blindado · 58–60.
- Golpe de Registro `100% ATQ`.
- Placa Deslocada · Barreira `100% ATQ`, CD3.
- Ordem de Revisão `90% ATQ + DEF−12% 2T`, CD3.
- Aproximação Impossível · **Preparada** `165% ATQ`, CD4; telegraph completo, sem teleporte mecânico, sem Hard CC.
- IA: Barreira se válida, depois pressão DEF/Dano; ausência de comando não significa consciência de antagonista. **Variantes:** Resistente, Furioso.

## 10.2 Três Elites — sem Variante adicional

**Predador de Duas Pegadas** — `elite.confins.predador_duas_pegadas` · Elite/ELITE · Predador · 54–56.
- Presa de Marcha `105% ATQ`; Rasgo em Duas Trilhas `90% ATQ +1 Sangramento`, CD3; Finta de Retorno `130% ATQ`, CD3; Queda de Pegadas · **Preparada** `180% ATQ`, CD4. IA: debuff antes da Preparada quando útil, sem ataque extra por pata duplicada.

**Viúva de Intervalo** — `elite.confins.viuva_intervalo` · Elite/ELITE · Controlador · 57–59.
- Mordida do Intervalo `100% ATQ`; Sutura Errada `90% ATQ + AGI−12% 2T`, CD3; Trama Fendida · AoE `75% ATQ`, CD3; Fio sobre o Vazio · **Preparada** `175% ATQ`, CD4. IA: não tenta loop de reaplicação; sem Hard CC.

**Custódio Desfasado** — `elite.confins.custodio_desfasado` · Elite/ELITE · Blindado · 59–60.
- Impacto de Referência `105% ATQ`; Pranchas Alternadas · Barreira `105% ATQ`, CD3; Marca de Correção `90% ATQ + DEF−12% 2T`, CD3; Protocolo Bifurcado · **Preparada** `185% ATQ`, CD4. IA: Barreira útil/pressão DEF/Preparada; zero Cura e Hard CC.

## 10.3 Variantes e perfil de campo

Somente as nove criaturas-base aceitam Variantes listadas; as três Elites, criaturas exclusivas de Masmorra, boss S36 e Regente não recebem Variante. Os perfis Furioso, Resistente, Ágil e Hemorrágico usam estritamente as modificações globais do GDD: Furioso `ATQ+8%/DEF−8%`, Resistente `DEF+10%/ATQ−6%`, Ágil `AGI+12%/HP−7%`, Hemorrágico habilita pacote global de Sangramento com `ATQ−5%`. Variante altera o que a Fonte Mestra autoriza, sem “turnos duplicados” por aparência. Pesos/chances regionais aprovados C (14/16/18/20% de Variante) estão na §11, não importados automaticamente de Altos.

## 10.4 Bestiário BKP (A)

- Comum/COMMON: Conhecido10, Estudado30, Dominado60; evidências ≥2 categorias para Estudado, ≥3 para Dominado.
- Incomum/RARE: 8/22/40; Dominado ≥2 categorias.
- Elite/ELITE: 10/25/45; exige vitória e comportamento específico.
- Chefe/BOSS: 10/30/50; Estudado 1 vitória e 2 fases/mecânicas; Dominado `mastery_required` completo.
- Primeira observação válida segue `1% XP(reference_level)`. `3% XP` de marco importante somente para os inimigos enumerados em §10.6. Repetições e BKP seguem integralmente o GDD; nenhuma criatura concede duas observações pela duplicação visual.

## 10.5 Condições distintivas de Dominado

| ID | Exigência além do BKP do perfil |
|---|---|
| `elite.confins.predador_duas_pegadas` | primeira vitória, Rasgo em Duas Trilhas e Queda de Pegadas observados |
| `elite.confins.viuva_intervalo` | primeira vitória, Sutura Errada e Fio sobre o Vazio observados |
| `elite.confins.custodio_desfasado` | primeira vitória, Pranchas Alternadas e Protocolo Bifurcado observados |
| `boss.confins.arquivo.o_que_chega_antes` | primeira vitória, estados Registro Antecipado/Registro Refeito, Queda do Retorno observada, Primeira Conclusão Estável Arquivo |
| `boss.confins.contradicoes.testemunha_impossivel` | primeira vitória, duas placas de afirmação simultâneas observadas e Revisão Contraditória, Primeira Conclusão Estável Câmara |
| `boss.confins.s36.verificador_sem_testemunhas` | primeira vitória, Desvio de Registro e Conferência Final; sem XP especial adicional |
| `boss.confins.regente_fraturado` | primeira vitória, três protocolos/fases, observar Ancoragem em Conflito e Desfecho da Última Ordem; P36 concluída |

Os demais Comuns/Incomuns obedecem thresholds/categorias globais e observação de suas Artes/Variantes aplicáveis, sem requerer “duas versões da mesma alma”.

## 10.6 Marcos importantes configurados (C; XP derivada A)

| Marco de primeira vitória | Reference Level | XP único (`3% XP_ref`) |
|---|---:|---:|
| Predador de Duas Pegadas | 55 | 5.259 |
| Viúva de Intervalo | 58 | 5.766 |
| Custódio Desfasado | 60 | 6.114 |
| O Que Chega Antes | 57 | 5.595 |
| Testemunha Impossível | 60 | 6.114 |
| Regente Fraturado | 60 | 6.114 |

**Total nominal: 34.962 XP**, sujeito ao cap Nv.60 nas ocorrências efetivas. Verificador de S36 não gera marco regional extra. Todos os marcos são idempotentes. A Primeira Conclusão de Masmorra e a vitória de campanha são direitos distintos do marco de conhecimento; um mesmo encontro só cria cada direito elegível uma vez.

# 11. Caçada — quatro pools exatos

Caçada existe **somente** nos quatro Locais de campo, individualmente: Marcha depois de P31, Estradas depois de P32, Fraturas depois de P33 e Nó depois de P34. Último Refúgio/Câmara da Regência jamais possuem Caçada normal. Os pesos C de cada pool somam100 antes de filtrar elegibilidade de criatura/nível; qualquer entrada inelegível é removida e os pesos restantes renormalizados pela seleção global. Nenhuma exceção modifica fórmula de settlement, chance de material/equipamento/Runa ou pity.

| Local | ID da Caçada | Missão concluída | Pool exato (pesos, não chances de drop) | Chance regional C de Variante nos elegíveis |
|---|---|---|---|---|
| Marcha Nebulosa | `unlock.hunt.confins.marcha` | P31 | cao_nevoa 50, gralha_duas_sombras 26, cervo_passo_duplo 15, predador_duas_pegadas 9 | 14% |
| Estradas Ausentes | `unlock.hunt.confins.estradas` | P32 | cao_nevoa 14, gralha_duas_sombras 14, andarilho_repetido 22, aranha_limiar 36, vigia_desfasado 6, viuva_intervalo 8 | 16% |
| Fraturas do Limiar | `unlock.hunt.confins.fraturas` | P33 | andarilho_repetido 14, aranha_limiar 12, cervo_passo_duplo 14, sanguessuga_palida 17, casca_reflexo 15, mariposa_sem_horizonte 10, viuva_intervalo 10, custodio_desfasado 8 | 18% |
| Nó Central | `unlock.hunt.confins.no` | P34 | sanguessuga_palida 10, casca_reflexo 19, mariposa_sem_horizonte 17, vigia_desfasado 39, custodio_desfasado 15 | 20% |

**Referências locais de conteúdo (C):** Marcha `51–54`, Estradas `53–56`, Fraturas `55–59`, Nó `57–60`. Cada criatura usa sua faixa explícita §9/§10; a composição elegível e o `enemy_level` são materializados e congelados pela regra do GDD. A chance de Variante é aplicada somente a criaturas-base já elegíveis, nunca a Elite. Inimigo cuja faixa não sobreponha nível selecionável fica inelegível naquele momento; não subir sua faixa arbitrariamente.

**Raro/Elite:** material de criatura segue §9; Categoria e perfis BKP seguem a Bíblia. Ao sortear Elite, a Ronda interrompe antes de enfrentá-la, mas a Caçada Manual pode enfrentá-la. Grupo e PvPvE seguem sistema global; um encontro econômico multialvo, quando ocorrer pelo GDD, liquida uma só recompensa normal por participante elegível e não a multiplica pelo número de criaturas. Não há caça direta do Regente nem de inimigos de Masmorra.

# 12. Desbravar — pools completos e descobertas únicas

**Disponibilidade:** Marcha somente após P31; Estradas após P32; Fraturas após P33; Nó após P34. Último Refúgio e Câmara nunca possuem Desbravar. Pool A por categoria: Grande Descoberta8%, Conhecimento22%, Narrativo15%, Combate25%, Pequeno Recurso10%, Atmosférico20%; redistribuir só entre resultados elegíveis. Recarga5min, máximo6 tentativas por Local/60min, proteção de conteúdo obrigatório elegível após 3 tentativas e anti-repetição globais. Desbravar econômico custa 4 Vigor conforme settlement; resultados únicos de descoberta seguem a regra global própria, sem transformar descoberta única em Saque adicional.

**XP de Descoberta:** `round_half_up(XP_ref(reference_level)×0,08)` grande; `×0,025` menor. Resultados atmosféricos =0 XP extra; combate/recurso repetíveis seguem exclusivamente §49.15 do GDD. **A descoberta já concedida sai do pool de resultados únicos; repetir categoria não reemite reward.**

## 12.1 Marcha Nebulosa · reference_level 52

**Grande:** `explore.confins.marcha.duas_balizas` — **Duas Balizas no Mesmo Marco** · único peso100, XP **12.744**, registra `codex.confins.marcos_incompativeis` como fato observado (não afirma existência de dois mundos).

**Conhecimento:** `explore.confins.marcha.caderno_marcha` — **Caderno de Ida e Volta** · Descoberta Menor única, peso60, XP **3.983**, adendo `codex.confins.duas_leituras_rota`; `explore.confins.marcha.giz_apagado` — **Giz Apagado**, repetível peso40, sem XP fixa de Descoberta.

**Narrativo:** `explore.confins.marcha.marca_repetida` `explore.confins.marcha.marca_repetida` Marca Repetida peso55; `explore.confins.marcha.sino_distante` `explore.confins.marcha.sino_distante` Sino Distante peso45; repetíveis, sem alteração de estado de mundo.

**Combate:** `explore.confins.marcha.combate` — Cão de Névoa45 / Gralha de Duas Sombras35 / Cervo de Passo Duplo20, sujeito à elegibilidade.
**Pequeno Recurso:** `explore.confins.marcha.recurso` — Ferro25 / Couro25 / Musgo35 / Pó15 (apenas identidade do 1 básico global).
**Atmosférico:** `explore.confins.marcha.atmos.nevoa_sem_vento` Névoa sem Vento34 / `explore.confins.marcha.atmos.pedra_volta` Pedra de Volta33 / `explore.confins.marcha.atmos.passo_umido` Passo Úmido33, sem economia adicional.

## 12.2 Estradas Ausentes · reference_level 55

**Grandes:** `explore.confins.estradas.braseiro_conferida` — **Braseiro da Estrada Conferida** · único peso50, XP **14.024**; `explore.confins.estradas.arquivo_retorno` — **Entrada do Arquivo do Retorno** · único peso50, XP **14.024**, concede `unlock.dungeon.confins.arquivo_retorno` (pode-se descobrir com Nv.53, mas entrar Estável requer Nv.54).

**Conhecimento:** `explore.confins.estradas.memoria_fundacao` — **Memória de Fundação** · menor única peso60, XP **4.383**, trecho `codex.confins.casa_presente_ausente` sem completar S32; `explore.confins.estradas.estacas_alternadas` Estacas Alternadas repetível peso40.

**Narrativo:** `explore.confins.estradas.estrada_sem_ponte` Estrada sem Ponte55 / `explore.confins.estradas.retorno_sem_ida` Retorno sem Ida45, ambos repetíveis.
**Combate:** `explore.confins.estradas.combate` — Andarilho Repetido30 / Aranha de Limiar30 / Gralha de Duas Sombras20 / Cão de Névoa20.
**Pequeno Recurso:** `explore.confins.estradas.recurso` — Ferro25 / Couro25 / Musgo30 / Pó20.
**Atmosférico:** `explore.confins.estradas.atmos.lama_incompleta` Lama Incompleta34 / `explore.confins.estradas.atmos.placa_curva` Placa na Curva33 / `explore.confins.estradas.atmos.marco_nao_visto` Marco Não-Visto33.

## 12.3 Fraturas do Limiar · reference_level 57

**Grandes:** `explore.confins.fraturas.braseiro_limiar` — **Braseiro do Limiar Firme** · único peso50, XP **14.920**; `explore.confins.fraturas.corte_referencia` — **Corte de Referência Observável** · único peso50, XP **14.920**, acrescenta fato observável `codex.confins.fratura_definicao`.

**Conhecimento:** `explore.confins.fraturas.ficha_dupla` — **Ficha de Duas Posições** · menor única peso60, XP **4.663**, fragmento `codex.confins.avesso_estados`; `explore.confins.fraturas.linhas_gastas` Linhas Gastas repetível peso40.

**Narrativo:** `explore.confins.fraturas.angulo_sem_retorno` Ângulo sem Retorno55 / `explore.confins.fraturas.eco_pedra` Eco de Pedra45, repetíveis.
**Combate:** `explore.confins.fraturas.combate` — Aranha de Limiar20 / Cervo de Passo Duplo20 / Sanguessuga Pálida20 / Casca de Reflexo20 / Mariposa sem Horizonte20.
**Pequeno Recurso:** `explore.confins.fraturas.recurso` — Ferro20 / Couro20 / Musgo25 / Pó35.
**Atmosférico:** `explore.confins.fraturas.atmos.silencio_limiar` Silêncio do Limiar34 / `explore.confins.fraturas.atmos.dobras_nevoa` Dobras da Névoa33 / `explore.confins.fraturas.atmos.pedra_sem_mancha` Pedra sem Mancha33.

## 12.4 Nó Central · reference_level 60

**Grandes:** `explore.confins.no.braseiro_retorno` — **Braseiro do Nó de Retorno** · único peso50, XP **16.304**; `explore.confins.no.camara_contradicoes` — **Entrada da Câmara das Contradições** · único peso50, XP **16.304**, concede `unlock.dungeon.confins.camara_contradicoes` (Estável somente Nv.58+).

**Conhecimento:** `explore.confins.no.rede_incompleta` — **Diagrama da Rede Incompleta** · menor única peso60, XP **5.095**, trecho `codex.confins.ancora_central_coordenacao`; `explore.confins.no.junta_marco` Junta de Marco repetível peso40.

**Narrativo:** `explore.confins.no.ordem_muro` Ordem no Muro55 / `explore.confins.no.corda_medida` Corda de Medida45, repetíveis.
**Combate:** `explore.confins.no.combate` — Sanguessuga Pálida20 / Casca de Reflexo25 / Mariposa sem Horizonte20 / Vigia Desfasado35, conforme elegibilidade do nível.
**Pequeno Recurso:** `explore.confins.no.recurso` — Ferro40 / Couro10 / Musgo15 / Pó35.
**Atmosférico:** `explore.confins.no.atmos.metal_paz` Metal em Paz34 / `explore.confins.no.atmos.registro_sem_voz` Registro sem Voz33 / `explore.confins.no.atmos.parede_repetida` Parede Repetida33.

## 12.5 Auditoria das descobertas

Unicidades que contam para `achievement.confins.cartografo_ausencias`: **11** IDs exatamente: Marcha2 + Estradas3 + Fraturas3 + Nó3. XP única nominal = `12.744+3.983+14.024+14.024+4.383+14.920+14.920+4.663+16.304+16.304+5.095 = 121.364 XP` (sujeita a cap quando obtida em Nv.60). Cada uma só registra uma vez por personagem; nenhuma atmosférica/repetível conta. Entradas de Masmorra são **desbloqueios por descoberta única**, não grants automáticos da Campanha; os Braseiros de descoberta também são individuais.

# 13. Ronda de Caça

**ID do entitlement:** `unlock.round.confins.marcha`, `unlock.round.confins.estradas`, `unlock.round.confins.fraturas`, `unlock.round.confins.no`, respectivamente. Para cada Local, requisitos cumulativos são:

| Local | Gate narrativo/atividade | Familiaridade necessária | Pool |
|---|---|---|---|
| Marcha Nebulosa | P31 concluída + `unlock.hunt.confins.marcha` | primeira vitória **posterior a P31** em Caçada Manual válida na Marcha | pool Marcha §11 |
| Estradas Ausentes | P32 concluída + `unlock.hunt.confins.estradas` | primeira vitória **posterior a P32** em Caçada Manual válida nas Estradas | pool Estradas §11 |
| Fraturas do Limiar | P33 concluída + `unlock.hunt.confins.fraturas` | primeira vitória **posterior a P33** em Caçada Manual válida nas Fraturas | pool Fraturas §11 |
| Nó Central | P34 concluída + `unlock.hunt.confins.no` | primeira vitória **posterior a P34** em Caçada Manual válida no Nó | pool Nó §11 |

**Não contam:** vitória em combate roteirizado, encontro de Desbravar, Masmorra, Caçada em outro Local, vitória anterior à conclusão local, Caçada Manual derrotada, participação sem elegibilidade. Grant da Ronda é idempotente e não depende de S31–S36.

**Só Solo.** Lotes ×5/×10/×20, 3min por encontro, Vigor2 por encontro econômico, HP e Configuração persistem como no GDD; até 3 Artes Ativas equipadas, snapshot durante lote, mais Ataque Básico/Defender, auto-uso apenas de Cura/Purificação elegíveis. Elite sorteada interrompe Ronda antes de luta automática; o lote preserva só encontros já concluídos. No Nv.60 não acumular XP para Legado. A Ronda reusa a exata seleção do pool da Caçada daquele Local, com identidade de Materiais por criatura §9; não cria probabilidade de drop nova.

# 14. Masmorra I — Arquivo do Retorno

**ID:** `dungeon.confins.arquivo_retorno` · **entrada:** Estradas Ausentes, somente após resultado único `explore.confins.estradas.arquivo_retorno` (não P32 automaticamente). **Faixa canônica global A:** Nv.54–57 (L=51, L+3→L+6); **gate Estável:** entrada descoberta + Nv.54 e Local acessível; **ref. Estável/Fraturada:** **Nv.57**; **Ruptura:** Nv.60 e primeira Fraturada, `dungeon_reference_level=60`. Fraturada exige Primeira Conclusão Estável. Chefe **O Que Chega Antes**. Não é viagem no tempo controlável: o arquivo preserva estados repetidos materialmente.

**Roster autoritativo B (IDs C):** `dungeon_creature.confins.arquivo.eco_sem_origem` (Eco sem Origem · Comum/COMMON · Equilibrado), `dungeon_elite.confins.arquivo.guardiao_retorno` (Guardião do Retorno · Elite/ELITE · Blindado), `boss.confins.arquivo.o_que_chega_antes` (BOSS · Equilibrado, perfil Chefe de Masmorra).

## 14.1 Encontros fixos (5)

| Ordem | Nome / Nv. de conteúdo | Formação / objetivo | Condição de progressão |
|---|---|---|---|
| 1 | Mesa de Entrada, Nv.54 | 1 Eco sem Origem; examinar entrada de equipe | derrotar Eco e registrar cabeçalho |
| 2 | Ala de Registros, Nv.55 | 2 Ecos sem Origem em **um encontro multialvo**; cotejar livros | vencer encontro, coletar duas páginas sem loot próprio |
| 3 | Corredor de Volta, Nv.56 | 1 Guardião do Retorno, Elite | derrotar Elite; resolver checkpoint elegível da run |
| 4 | Livro Fechado, Nv.57 | 1 Eco sem Origem com **2 Placas de Registro** inertes que só servem de objeto interagível/contextual | derrotar Eco e ler ambos os estados; placas 0 HP econômico, 0 XP, 0 Bestiário |
| 5 | Sala do Retorno, Nv.57 | O Que Chega Antes | vitória do Chefe conclui a run elegível |

O número de inimigos do encontro multialvo **não multiplica o orçamento completo de scaling de Grupo nem o settlement econômico**. Encontros internos usam a XP global normalizada de inimigo interno (25% da Caçada quando aplicável) e o settlement principal pertence à conclusão da run. Placas não são entidades de recompensa, nem novo sistema de tempo.

## 14.2 Kits

**Eco sem Origem** — `dungeon_creature.confins.arquivo.eco_sem_origem`: Sinal de Presença `95% ATQ`; Passagem Repetida `110% ATQ` CD2; Rasura de Registro `85% ATQ + PER−10% 2T` CD3. IA: não reaplica Debuff inútil; não é alma identificada.

**Guardião do Retorno** — `dungeon_elite.confins.arquivo.guardiao_retorno`: Golpe de Protocolo `100% ATQ`; Reconstituir Postura, Barreira `100% ATQ` CD3; Revisão de Retorno `90% ATQ + DEF−10% 2T` CD3; Volta Indevida Preparada `175% ATQ` CD4. Não ressuscita inimigos, não retrocede turnos, sem Cura/Hard CC.

**O Que Chega Antes** — `boss.confins.arquivo.o_que_chega_antes`: Marca de Chegada `100% ATQ`; Registro Antecipado `90% ATQ + AGI−10% 2T` CD3; Cobertura Anterior, Barreira `8% HP Máximo` CD4, no máximo 2 usos; Queda do Retorno AoE `80% ATQ` CD3; Retorno sem Ida **Preparada** `180% ATQ` CD5. Sem Cura, adds obrigatórios, Hard CC nem refazer dano já registrado.

**Fases C:** Fase I — **Registro Antecipado** (`100→70% HP`) apresenta Marca/Registro; Fase II — **Registro Refeito** (`70→35%`) habilita Cobertura/Queda; Fase III — **Retorno sem Ida** (`≤35%`) habilita a Arte homônima com telegraph integral. Os nomes identificam as mesmas três fases já propostas; não adicionam efeito ou etapa. Fase/telegraph são boss-specific sob a mecânica global de Ação Preparada. No final, a incongruência do registro torna-se observável, sem transmitir profecia.

## 14.3 Economia e run (A + pools C)

Recompensa de **conclusão elegível por jogador**, usando referência Estável/Fraturada 57 e Ruptura60:

| Dificuldade | XP de conclusão repetível | Coroas derivadas | Básicos VI | Catalisadores VI | Núcleos Arquivo | Fragmentos VI | Equipamento/Runa |
|---|---:|---:|---:|---:|---:|---:|---|
| Estável | **14.870** | **770** | 8 | 2 | 1 | 2 | 1 roll garantido de Equipamento; Runa conforme GDD |
| Fraturada | **18.220** | **1.150** | 11 | 3 | 2 | 4 | id. |
| Ruptura | **24.240** | **1.800** | 14 | 4 | 4 | 7 | id.; referência60 |

Primeira Conclusão Estável tem recompensa de XP da conclusão `14.870×1,60=**23.792**` uma vez; Fraturada `18.220×1,60=**29.152**`; Ruptura `24.240×1,60=**38.784**`, sujeitas ao cap. Não duplicar bônus de primeira vitória em retry. Quantidade de básicos usa distribuição por unidade **Ferro30 / Couro15 / Musgo20 / Pó35** (100%). Núcleo é o `material.special.confins.core.arquivo_retorno`; não existe Núcleo do boss separado por combate.

**Equipamento de Masmorra:** 1 roll garantido por conclusão, raridades A — Estável Comum25/Raro50/Épico22/Lendário2,8/Mítico0,2; Fraturada 10/45/38/6,5/0,5; Ruptura 0/20/60/19/1. **Runa:** chance Estável20%/Fraturada35%/Ruptura50% e raridades condicionais GDD. **Pity:** 1/2/4 pontos, hard Lendário+24, Mítico200. **Receita:** `recipe.confins.arquivo.relicario_entrada_duplicada`, roll Estável8%/Fraturada15%/Ruptura25%, somente desconhecida. Sem prêmio de Receita garantido na Primeira Conclusão.

**Vigor:** 25/35/50. Consumo por run/recursos, estado provisório e confirmação ficam no contrato global. `dungeon_bonfire.confins.arquivo.ala_retorno` possível após encontro3 (70/40/20 por dificuldade). Retry ilimitado dentro da mesma `run_id` válida; não reseta consumo, HP, slot de consumíveis ou Vigor, respeita checkpoint e validade4h inatividade/24h absoluta. Escala fica congelada no roster inicial1–4; confirmação60s e sem reposição.

**Códice:** `codex.confins.dungeon.arquivo_retorno`, `codex.confins.dungeon.registro_repetido`, `codex.confins.dungeon.chegada_antes`. **Bestiário:** Eco sem Origem, Guardião do Retorno e O Que Chega Antes. **Feito:** `achievement.confins.arquivo_estavel` requer Primeira Conclusão Estável. Chefe só paga settlement por conclusão, não núcleo/loot paralelo a inimigo.

# 15. Masmorra II — Câmara das Contradições

**ID:** `dungeon.confins.camara_contradicoes` · **entrada:** Nó Central, descoberta única `explore.confins.no.camara_contradicoes`; **faixa global A:** Nv.58–60 (L+7→L+9); **Estável:** descoberta + Nv.58 + acesso ao Nó; **Fraturada:** Primeira Estável; **Ruptura:** Nv.60 + Primeira Fraturada. **Ref. Estável/Fraturada=60; Ruptura=60** (a dificuldade altera regras globais aplicáveis, não cria Nv.61). Chefe: Testemunha Impossível; não é profeta, deus ou fonte onisciente.

**Roster B/IDs C:** `dungeon_elite.confins.contradicoes.custodio_no_central` — Custódio do Nó Central, Elite/ELITE, Blindado; `dungeon_elite.confins.contradicoes.preceptor_contradicao` — Preceptor de Contradição, Elite/ELITE, Controlador; `boss.confins.contradicoes.testemunha_impossivel` — Chefe/BOSS, Controlador. `creature.confins.vigia_desfasado` pode figurar no primeiro encontro como inimigo de mundo aberto explicitamente importado, mas não altera seu pool territorial.

## 15.1 Encontros (5)

| Ordem | Nome / Nv. | Formação / mecânica | Vitória |
|---|---|---|---|
| 1 | Corredor da Referência, Nv.58 | 1 Vigia Desfasado; leitura inicial | vencer e ler placa A |
| 2 | Ponto de Controle, Nv.59 | 1 Custódio do Nó Central | vencer e ler placa B, sem escolher “verdade” |
| 3 | Mesa das Ordens, Nv.60 | 1 Preceptor de Contradição | vencer e verificar checkpoint por run |
| 4 | Duas Ordens, Nv.60 | 1 Custódio do Nó Central +1 Preceptor em **um** encontro multialvo; examinar registro físico após vitória | um settlement interno normal, nunca 2 encounters econômicos independentes |
| 5 | Sala da Testemunha, Nv.60 | Testemunha Impossível; placas documentais **inertes no cenário** (distintas das duas Placas de Afirmação de combate ativadas na Fase II) | vitória encerra run |

## 15.2 Kits e boss

**Custódio do Nó Central** — Impacto de Coordenação `100% ATQ`; Placa de Nó, Barreira `100% ATQ` CD3; Pressão de Referência `90% ATQ+DEF−10% 2T` CD3; Travamento de Passagem Preparada `175% ATQ` CD4. Nenhuma alteração de rota durante combate.

**Preceptor de Contradição** — Golpe de Ordem `95% ATQ`; Ordem A `85% ATQ+AGI−10% 2T` CD3; Ordem B `85% ATQ+ATQ−10% 2T` CD3; Confronto de Registros Preparada `175% ATQ` CD4. IA alterna debuffs distintos quando úteis, mas não ganha ações extras por “duas ordens”.

**Testemunha Impossível** — Referência Incompatível `100% ATQ`; Revisão Contraditória `90% ATQ+DEF−12% 2T` CD3; Placa de Evidência, Barreira `8% HP Máximo`, CD4 máximo2 usos; Leitura sobreposta AoE `80% ATQ` CD3; Afirmação Final Preparada `185% ATQ` CD5, telegraph integral.

**Mecânica específica C, sem novo motor:** no limiar de `70% HP`, aparecem **duas Placas de Afirmação** (objetos físicos de combate, distintos das placas documentais inertes presentes no cenário; não são inimigos e não possuem ação/loot/Bestiário). Cada placa possui HP = `25% do HP-base de Comum da referência60`, DEF=`100%` da referência, reduz dano final recebido pelo boss em `5%` enquanto ativa; máximo10%. Podem ser destruídas por Ações de ataque que aceitem alvo de objeto. Aos `35% HP`, as placas restantes são consumidas, removendo mitigação e concedendo **Barreira única de 5% HP Máximo por placa restante** (máx10%, sujeita às regras globais); placas destruídas não retornam. Não existe regeneração de placas, imortalidade por estados nem escolha que altere permanentemente história. A regra é apenas encontro boss-specific, analogia mecânica permitida aos elementos físicos dos bosses anteriores.

**Fases:** I `100→70%` leitura inicial; II `70→35%` duas Placas; III `≤35%` consome remanescentes e libera Afirmação Final. IA: não usa Barreira inútil/cura, respeita telegraph e CD; sem adds obrigatórios, Hard CC ou alteração cosmológica do mundo.

## 15.3 Economia e run

| Dificuldade | XP conclusão repetível | Coroas | Básicos VI | Catalisadores VI | Núcleos Câmara | Fragmentos VI | Saque |
|---|---:|---:|---:|---:|---:|---:|---|
| Estável | **15.550** | **800** | 8 | 2 | 1 | 2 | equipamento 1 roll, Runa global |
| Fraturada | **19.050** | **1.200** | 11 | 3 | 2 | 4 | idem |
| Ruptura | **24.240** | **1.800** | 14 | 4 | 4 | 7 | idem, referência60 |

Primeira Conclusão Estável nominal `15.550×1,60=**24.880 XP**`; Fraturada `19.050×1,60=**30.480**`; Ruptura `24.240×1,60=**38.784**`. XP não acumula em Nv.60. Básicos por unidade de conclusão: Ferro40 / Couro10 / Musgo15 / Pó35 (soma100). Núcleo `material.special.confins.core.camara_contradicoes`. Não existe prêmio econômico adicional do boss.

Equipamento 1 roll garantido, tabelas globais de raridade; Runa20/35/50%; pity1/2/4 pontos e thresholds24/200, Vigor25/35/50, limites de consumíveis6/5/4, durações e Retry/runs como §14. **Receita:** `recipe.confins.contradicoes.guarda_duas_versoes` com chances8/15/25% somente enquanto desconhecida. Checkpoint condicional `dungeon_bonfire.confins.contradicoes.patio_referencia`, após encontro3, sorteio70/40/20 sem virar Travessia.

**Códice:** `codex.confins.dungeon.camara_contradicoes`, `codex.confins.dungeon.ordens_irreconciliaveis`, `codex.confins.dungeon.testemunha_impossivel`. **Bestiário:** Vigia Desfasado, Custódio do Nó Central, Preceptor de Contradição e Testemunha Impossível. **Feito:** `achievement.confins.contradicoes_estavel` requer Primeira Conclusão Estável. Códice não concede “cronologia verdadeira” automática antes de P35/P36; registros técnicos anteriores são fragmentos observados.

# 16. P36 — Regente Fraturado, encontro final

**ID:** `boss.confins.regente_fraturado` · **Nv.60** · **Local:** Câmara da Regência · **gatilho:** etapa 3 de P36 após P35 concluída e Nv.60, com início do encontro consciente/confirmado. **Perfil:** Chefe normal de arquétipo **Equilibrado** com `220% HP /110% ATQ /110% DEF /100% AGI` sobre a referência global (não substitui cálculos de K(level)); Solo ou Grupo1–4 na escala global de Chefe de Campanha, viável Solo em todas as builds legais. Não usa scaling de Caçada/Masmorra.

**Identidade B:** sobreposição de fragmentos de Cael Rhen, registros, protocolos, matéria local e estados avessos; não Cael vivo/ressuscitado, nem deus, demônio, lich, mago do vazio, pessoa onisciente ou agente consciente chamado Avesso. Não é o último segredo de todas as eras.

## 16.1 Artes (C)

| Arte | Efeito de combate já existente | CD/limite |
|---|---|---|
| **Ordem Sobreposta** | `100% ATQ`, 1 alvo | Básico |
| **Selo de Continuidade** | Barreira `8% HP Máximo`, duração global, sem stack fora regra | CD4, máx.2 usos por combate |
| **Marca de Divergência** | `90% ATQ + DEF−12% por 2T` | CD3 |
| **Leitura de Duas Ordens** | AoE `80% ATQ`, 1 ocorrência normal de ação | CD3 |
| **Ancoragem em Conflito** | `130% ATQ`, 1 alvo | CD3 |
| **Desfecho da Última Ordem** | Ação Preparada `185% ATQ`, 1 alvo, telegraph integral | CD5; desbloqueada na fase III |

## 16.2 Fases e elementos do encontro (C)

- **Fase I — Manter** (`100→70%`): apresenta Ordem Sobreposta, Marca de Divergência e Selo. O combate ensina que a manifestação tenta sustentar um protocolo sem operador íntegro.
- **Fase II — Referências Incompatíveis** (`70→35%`): ativa duas **Âncoras de Registro** como objetos físicos do encontro, **não** estruturas estabilizadoras reais do mundo, não novas entidades econômicas. Cada objeto: HP=`25% HP-base Comum Nv.60`, DEF=`100% referência Comum Nv.60`, sem turno/ação/loot/XP/Bestiário; cada objeto ativo reduz dano final recebido pelo Regente em `5%`, máximo10%, e pode ser destruído. Leitura de Duas Ordens torna-se utilizável.
- **Fase III — O Protocolo que Não Pode Concluir** (`≤35%`): objetos restantes são consumidos, redução desaparece e cada restante concede Barreira única ao Chefe de `5% HP Máximo` (máx10%). Objetos destruídos não retornam. Desbloqueia Desfecho da Última Ordem (Preparada, CD5). Sem cura, adds obrigatórios, Hard CC, enrage ou repetição de turnos.

**IA:** prioriza Barreira somente quando útil e ainda dentro de 2 usos, aplica Marca quando não existe Debuff equivalente eficaz, intercala AoE quando há múltiplos alvos e telegraph da Preparada conforme cooldown e elegibilidade. Fase não concede turno extra. Transições são triggers por HP, idempotentes, com estado snapshotado; uma transição não repete evento ao reconectar. O jogador pode derrotar o Regente com Ataque Básico e kit legal das seis Classes; não existe DPS check de destruir objetos obrigatoriamente para remover invulnerabilidade.

## 16.3 Condições de resultado e economia

**Vitória:** HP boss chega a0 por combate válido → registra direito `boss.confins.regente_fraturado.first_victory` por personagem elegível uma vez → 1 Núcleo do Regente Fraturado, atualização de Bestiário e progresso P36. P36 só conclui depois de Códice, Receita e escolha de Equipamento. **Derrota:** P36 permanece no confronto, sem Núcleo/recompensa, recovery Braseiro da Testemunha; retry sem rerroll de composição e sem pagamento duplicado.

Economia **do inimigo**: EnemyXP0, Coroas0, Materiais0, Saque0, Equipamento0, Runa0, Fragmentos0, Catalisadores0, pity0, Vigor de Caçada0. Exceção explícita: **1 Núcleo único por primeira vitória**. Economia da Missão é a linha P36 §5; Bestiário 3% só no marco configurado, idempotente.

**Estado pós-chefe:** `narrative.confins.protocolo_impossivel_encerrado` pessoal; Regente apresentado inativo para o personagem; não há `world_state` global do servidor alterado por vitória individual. **Não** cura o Véu, **não** elimina Fraturas, **não** destrói Avesso, **não** antecipa Crônica/voto e **não** autoriza um futuro Nv.61. O Códice contém reconstrução documental, não Verdade Absoluta de Autor.

# 17. Códice — entradas, fragmentos, conhecimento e spoiler

Códice é **aquilo que o personagem legitimamente sabe**, não narração onisciente. Cada linha distingue evidência observada, registro histórico e interpretação apoiada. Novo Trecho pode anexar evidência à mesma entrada sem reescrever retroativamente a informação que um personagem teria visto antes. Entradas de dungeon/Desbravar antes da Campanha avançada não revelam conclusões P34–P36.

| ID | Entrada | Natureza da informação | Aquisição mínima | Limite |
|---|---|---|---|---|
| `codex.confins.regiao` | Confins do Véu | fato observado | entrada P31 | bioma/cultura, sem Avesso completo |
| `codex.confins.duas_leituras_rota` | Duas Leituras da Rota | fatos + testemunho | P31 | dois registros honestos não provam realidade paralela |
| `codex.confins.marcos_incompativeis` | Marcos Incompatíveis | observação direta | Desbravar Marcha | posições observadas, sem causa total |
| `codex.confins.pegadas_incompativeis` | Duas Vezes a Mesma Estrada | observação comparada | S31 | não provar duplicatas conscientes |
| `codex.confins.fratura_definicao` | Fratura Observável | observação + definição | P32; trecho Desbravar Fraturas | não portal |
| `codex.confins.casa_presente_ausente` | A Casa que Não Chegou | documento + matéria | S32; trecho Desbravar | ausência/presença, sem “fantasma doméstico” |
| `codex.confins.avesso_estados` | Avesso — Estados | conceito corroborado | P33; trecho Desbravar | não entidade nem sétima Região |
| `codex.confins.nomes_ordem_errada` | Nomes em Ordem Errada | crítica de fontes | S33 | distingue cópia errada de incongruência real |
| `codex.confins.ancora_central_coordenacao` | Âncora Central | documento técnico | P34; trecho Desbravar Nó | nó, não botão mestre |
| `codex.confins.testemunha_ontem` | A Testemunha de Ontem | evidência cronológica local | S34 | não afirma profecia/viagem temporal |
| `codex.confins.duas_ordens_oficiais` | Ordens Discordantes | registro oficial duplo | S35 | preservar ambos sem apagar |
| `codex.confins.convergencia_reconstrucao` | Convergência — Reconstrução | registros cruzados | P35 | chance histórica provável, não prova matemática absoluta |
| `codex.confins.cadeia_ruptura_documentada` | Cadeia da Ruptura | síntese histórica corroborada | P35 | revela sequência plausível, minutos não preservados continuam lacuna |
| `codex.confins.regente_natureza` | Regente Fraturado | matéria observada + fragmentos | P36 pós-vítória | não Cael vivo; consciência não afirmada |
| `codex.confins.protocolo_encerrado` | Depois do Protocolo | fato do confronto | P36 | Véu/Avesso permanecem |
| `codex.confins.depois_ultima_ordem` | Rotinas Depois da Ordem | observação civil | S36 | decisão local presente, não final alternativo |
| `codex.confins.dungeon.arquivo_retorno` | Arquivo do Retorno | Local observado | descoberta + entrada válida | arquivo operacional |
| `codex.confins.dungeon.registro_repetido` | Registro Repetido | matéria/arquivo | Arquivo encontros1–4 | não viagem temporal controlada |
| `codex.confins.dungeon.chegada_antes` | O Que Chega Antes | observação de chefe | vitória Arquivo | não alma nem onisciência |
| `codex.confins.dungeon.camara_contradicoes` | Câmara das Contradições | Local/infraestrutura | descoberta + entrada válida | reconciliação de leituras |
| `codex.confins.dungeon.ordens_irreconciliaveis` | Ordens Irreconciliáveis | documentos | Câmara encontros2–4 | sem solução forçada |
| `codex.confins.dungeon.testemunha_impossivel` | Testemunha Impossível | observação + registro | vitória Câmara | não deus/cronista absoluto |

**Ordem de revelação (B):** P31 leituras → P32 Fratura → P33 Avesso → P34 Âncora Central → P35 operação Convergência/Desvelados/Regência e cadeia provável → P36 natureza da manifestação e encerramento. S31–S36 acrescentam textura, não condição oculta de campanha. O Códice nunca apaga fragmento antigo para “corrigir realidade”; anexa corroboração com procedência registrada. `codex.confins.cadeia_ruptura_documentada` é a grafia única e oficial da entrada na proposta.

# 18. Feitos e Cosméticos (C)

Todos os Feitos são grants pessoais idempotentes, sem atributos, proficiências, XP adicional, Runa, drop ou poder oculto. Condição exata inclui evidência válida e não pode ser simulada pelo texto de UI.

| ID | Nome | Condição exata | Cosmético autorizado |
|---|---|---|---|
| `achievement.confins.primeira_marcha` | Primeira Marcha | P31 concluída | Título **Testemunha de Rota** |
| `achievement.confins.cinco_braseiros` | Cinco Referências | 5 Braseiros permanentes Confins descobertos | Moldura **Marcos do Véu** |
| `achievement.confins.fratura_observada` | O Nome da Fratura | P32 concluída | — |
| `achievement.confins.avesso_nomeado` | Nomear sem Dominar | P33 concluída | Título **Leitor de Incoerências** |
| `achievement.confins.ancora_compreendida` | Nó Não é Fonte | P34 concluída | — |
| `achievement.confins.cadeia_ruptura` | A Noite Reconstruída | P35 concluída | Moldura **Arquivo Duplo** |
| `achievement.confins.s36` | Depois da Ordem | S36 concluída | Título **Guardião de Testemunhas** |
| `achievement.confins.arquivo_estavel` | Retorno Verificado | Primeira Conclusão Estável do Arquivo | — |
| `achievement.confins.contradicoes_estavel` | Versões Preservadas | Primeira Conclusão Estável da Câmara | — |
| `achievement.confins.regente_primeira` | Encerrar sem Curar | primeira vitória P36 válida | Moldura **Última Referência** |
| `achievement.confins.naturalista` | Naturalista dos Confins | 9 criaturas-base Dominadas no Bestiário | — |
| `achievement.confins.cartografo_ausencias` | Cartógrafo das Ausências | exatamente 11 resultados únicos §12 concluídos | — |
| `achievement.confins.regiao` | Confins do Véu | P36 concluída + Nv.60 + seis Locais descobertos; S36/Masmorras opcionais | Aparência **Viajante do Véu** |

**Cosméticos totais:** **3 Títulos + 3 Molduras + 1 Aparência = 7**; seis dos treze Feitos não concedem Cosmético. Só existe Aparência do personagem, não skin de arma/equipamento do lançamento; produção visual posterior deve obedecer às fontes visuais vigentes e ao cânone multi-racial.

# 19. Crafting regional — Grau VI

**Regra A:** Grau VI=`item_level 51–60`; `item_level=min(nível atual do destinatário,60)` com destinatário Nv.51+; ofício mínimo de Grau VI=15; Comum/Raro/Épico seguem requisito de raridade global, Lendário Ofício16 + Receita especial, Mítico26 + Receita específica (não genérica). Craft +0 sem falha, SW econômico por slot e budget global. Sem armadura leve/média/pesada mecânica, sem dano elementar criado por tema.

## 19.1 Catálogo das 13 famílias/slots (nomes C)

| ID de catálogo/template | Nome oficial | Ofício | Slot | EconomySW | Básicos por Receita |
|---|---|---|---|---:|---|
| `craft.confins.ferreiro.principal.lamina_baliza` | **Lâmina de Baliza** | Ferreiro | Principal | 2 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.secundaria.guarda_marcha` | **Guarda da Marcha** | Ferreiro | Secundária | 1 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.2h.arco_retorno` | **Arco do Retorno** | Ferreiro | 2H | 3 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.cabeca.elmo_referencia` | **Elmo de Referência** | Ferreiro | Cabeça | 1 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.torso.couraca_marcha` | **Couraça da Marcha** | Ferreiro | Torso | 2 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.maos.manoplas_marco` | **Manoplas do Marco** | Ferreiro | Mãos | 1 | 70% Ferro /30% Pó |
| `craft.confins.ferreiro.pes.grevas_retorno` | **Grevas do Retorno** | Ferreiro | Pés | 1 | 70% Ferro /30% Pó |
| `craft.confins.curteiro.cabeca.capuz_nevoa` | **Capuz da Névoa** | Curteiro | Cabeça | 1 | 70% Couro /30% Musgo |
| `craft.confins.curteiro.torso.casaco_ausencias` | **Casaco das Ausências** | Curteiro | Torso | 2 | 70% Couro /30% Musgo |
| `craft.confins.curteiro.maos.luvas_testemunha` | **Luvas da Testemunha** | Curteiro | Mãos | 1 | 70% Couro /30% Musgo |
| `craft.confins.curteiro.pes.botas_limiar` | **Botas do Limiar** | Curteiro | Pés | 1 | 70% Couro /30% Musgo |
| `craft.confins.joalheiro.acessorio.selo_referencia` | **Selo de Referência** | Joalheiro | Acessório | 2 | 60% Ferro /40% Pó |
| `craft.confins.joalheiro.artefato.relicario_duplo` | **Relicário de Duas Leituras** | Joalheiro | Artefato | 2 | 60% Ferro /40% Pó |

**Custo A de material por SW:** Comum5 Básicos×SW; Raro8 Básicos×SW+4 Fragmentos×SW; Épico10 Básicos×SW+2 Catalisadores×SW+6 Fragmentos×SW; Lendário14 Básicos×SW+4 Catalisadores×SW+12 Fragmentos×SW+1 Núcleo×SW quando Receita elegível; Mítico mínimo20/8/20/3 por SW e Receita específica inexistente nesta Regional genérica. **Arredondamento de identidade:** Primário=`floor(total×proporção+0,5)`, Secundário=restante, uma vez após SW.

**Taxa A:** `round_10(C(item_level)×EconomySW×RarityFactor)`, Comum0,25/Raro0,35/Épico0,50/Lendário0,75. Crafting não cria escolha de nível futuro nem efeito extra por título da Receita. Templates normais elegíveis para Saque por grupo global de slot, inclusive 2H no grupo Principal; exclusivos de Campanha/Receita fora do pool genérico.

## 19.2 Weapon Metadata explícita dos itens de arma VI (C)

Não usar `weapon_family` histórica. Form é descritiva, handedness e slot são próprios do item e tags funcionais explicitamente declaradas; Classe não cria proficiência. Este contrato segue o fechamento global Weapon Metadata preparado separadamente e deve ser sincronizado junto dele antes de implementação; não se infere compatibilidade por nome, material ou aparência.

| Item/ID da definição | Form | Handedness | Slot eligibility | Tags de compatibilidade |
|---|---|---|---|---|
| `craft.confins.ferreiro.principal.lamina_baliza` | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.main_only` | `weapon.compat.melee` |
| `craft.confins.ferreiro.secundaria.guarda_marcha` | `weapon.form.dagger` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `craft.confins.ferreiro.2h.arco_retorno` | `weapon.form.bow` | `weapon.hands.two` | `weapon.slot.main_two_handed` | `weapon.compat.bow` |
| `equipment.confins.campaign.p36.guarda_ultimo_protocolo` | `weapon.form.mace` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |
| `equipment.confins.special.guarda_duas_versoes` | `weapon.form.sword` | `weapon.hands.one` | `weapon.slot.secondary_only` | `weapon.compat.melee` |

Form não impõe tag por regra; esta tabela as publica explicitamente. Armas 1H Principal/Secundária não cruzam slots automaticamente; 2H bloqueia Secundária e desloca item anterior conforme GDD. Selo, Relicário, escudo não-arma, armaduras e cosméticos têm metadados de arma **N/A**. As seis Classes não ganham restrição global; Artes consultam as tags publicadas por sua Fonte.

**Atenção à governança:** se o contrato global `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md` não estiver formalmente registrado no `SOURCE_AUTHORITY`, esta tabela é uma proposta de conteúdo alinhada a ele, não substituto de sua autoridade global. A sincronização simultânea é condição do handoff, não lacuna de números desta Regional.

# 20. Runas e Encantamentos Grau VI

**A:** Ofício Artífice15 para Grau VI; potência de atributos e taxas são as tabelas globais do GDD; materiais do Grau VI e raridade aplicável. Artífice16 + Receita especial para raridade Lendária se exigida globalmente. Nenhuma Runa/Enchant recebe proc ou efeito novo pelo nome.

## 20.1 Runas — 8 famílias C

| ID | Nome | Atributo |
|---|---|---|
| `rune.confins.marco` | Runa do Marco | ATQ |
| `rune.confins.resguardo` | Runa do Resguardo | DEF |
| `rune.confins.passagem` | Runa da Passagem | AGI |
| `rune.confins.testemunha` | Runa da Testemunha | PER |
| `rune.confins.fenda` | Runa da Fenda | CRIT |
| `rune.confins.permanencia` | Runa da Permanência | HP |
| `rune.confins.desvio` | Runa do Desvio | Esquiva |
| `rune.confins.retorno` | Runa do Retorno | Bloqueio |

**Potências Grau VI (A):** HP/ATQ Rara+0,60% Épica+0,80% Lendária+1,00%; DEF/AGI +1,00/+1,40/+1,80%; PER/CRIT +0,50/+0,75/+1,00 p.p.; Esquiva +0,25/+0,50/+0,50 p.p.; Bloqueio +0,50/+0,75/+1,00 p.p. **Taxas A:** 300/600/1.000 Coroas por Rara/Épica/Lendária. **Materiais A:** Rara 4 Pós+2 Ferros+2 Fragmentos VI; Épica 7 Pós+3 Ferros+1 Catalisador VI+4 Fragmentos VI; Lendária 10 Pós+4 Ferros+2 Catalisadores VI+8 Fragmentos VI. Compatibilidade por slot e limite normal 8 Runas/2 em 2H são globais.

## 20.2 Encantamentos — 8 famílias C

| ID | Nome | Atributo |
|---|---|---|
| `enchant.confins.fio_presente` | Fio Presente | ATQ |
| `enchant.confins.pedra_lida` | Pedra Lida | DEF |
| `enchant.confins.trilha_segura` | Trilha Segura | AGI |
| `enchant.confins.ordem_conferida` | Ordem Conferida | PER |
| `enchant.confins.duas_sombras` | Duas Sombras | CRIT |
| `enchant.confins.abrigo_ultimo` | Abrigo Último | HP |
| `enchant.confins.passo_sem_eco` | Passo sem Eco | Esquiva |
| `enchant.confins.ancora_valida` | Âncora Válida | Bloqueio |

**Potências Grau VI (A):** HP/ATQ Raro+0,20%, Épico+0,35%, Lendário+0,50%; DEF/AGI +0,40/+0,70/+1,00%; PER/CRIT +0,25/+0,50/+0,75 p.p.; Esquiva +0,25/+0,25/+0,50 p.p.; Bloqueio +0,25/+0,50/+0,75 p.p. **Taxas:** 200/400/700 Coroas. **Materiais:** Raro 3 Pós+1 Ferro; Épico 5 Pós+2 Ferros+1 Catalisador VI; Lendário 8 Pós+3 Ferros+2 Catalisadores VI+3 Fragmentos VI. Nenhum efeito especial de alteração de cronologia ou duplicação de equipamento.

# 21. Alquimia e Consumíveis Grau VI

Sete famílias globais, efeitos não variam por Grau; **Alquimista15** (requisitos de Grau VI e família satisfeitos), sem nova família ou limite de uso. `Musgo de Limiar` = Reagente VI, `Pó de Referência` = Essência VI.

| ID | Nome regional | Família | Materiais/catalisador | Taxa A | Efeito A |
|---|---|---|---|---:|---|
| `consumable.confins.cura` | Poção de Cura da Marcha | Cura | 3 Musgos +1 Pó | 100 | Cura própria 22% HP Máximo |
| `consumable.confins.purificacao` | Preparado de Referência Limpa | Purificação | 2 Musgos +2 Pós | 150 | remove 1 efeito negativo removível |
| `consumable.confins.antidoto` | Antídoto do Limiar | Antídoto | 4 Musgos +1 Pó | 150 | remove stacks de 1 DoT removível |
| `consumable.confins.vigor` | Poção de Vigor do Refúgio | Vigor | 6 Musgos +4 Pós +1 Catalisador VI | 500 | +20 Vigor, fora de combate, 1/ciclo e Vigor≤80 |
| `consumable.confins.protecao` | Preparado de Proteção da Baliza | Proteção | 3 Musgos +2 Pós | 200 | Barreira floor(12% HP Máx), 2T, PvE |
| `consumable.confins.dissipador` | Dissipador de Ordem | Dissipador | 2 Musgos +3 Pós | 250 | remove 1 efeito positivo elegível, PvE |
| `consumable.confins.resguardo` | Preparado de Resguardo do Véu | Resguardo | 4 Musgos +2 Pós | 300 | 2T/1 carga contra primeira aplicação negativa elegível, PvE |

CD2 compartilhado dos Consumíveis de combate, uso consome ação/unidade, limites encontro Comum1/Incomum1/Elite2/Chefe3, Masmorra por run Estável6/Fraturada5/Ruptura4, PvP não usa Consumível externo. Ronda automatiza **somente Cura e Purificação**. “Dissipador de Ordem” dissipa apenas Buff removível normal; não remove estado fixo do Regente, Fratura, Avesso ou fase.

# 22. Receitas especiais regionais (C)

As duas Masmorras usam chances globais de descoberta Estável8%, Fraturada15%, Ruptura25%, **somente enquanto a Receita permanece desconhecida**. Não exige profissão ativa para descobrir, mas exige requisito completo para fabricar. Receita do Regente é **revelação direta única em P36**, não roll de Caçada nem loot extra. Núcleos usados são consumidos, não retornam na Desmontagem.

## 22.1 Relicário da Entrada Duplicada

- **Receita:** `recipe.confins.arquivo.relicario_entrada_duplicada`.
- **Template:** `equipment.confins.special.relicario_entrada_duplicada`.
- **Resultado:** Artefato Raro Grau VI, Joalheiro15, EconomySW2, item_level do destinatário dentro de51–60.
- **Materiais:** 10 Ferros de Baliza +6 Pós de Referência +8 Fragmentos VI +1 Núcleo do Arquivo do Retorno.
- **Taxa:** fórmula global do Craft Raro `round_10(C(item_level)×SW2×0,35)` (em item_level60, **700 Coroas**).
- **Aquisição:** conclusão elegível do Arquivo do Retorno, chance8/15/25%, somente desconhecida; resultado não possui proc nem excede Raro.
- **Economia:** igual a Receita Especial Rara global, sem Núcleo adicional pelo boss.

## 22.2 Guarda das Duas Versões

- **Receita:** `recipe.confins.contradicoes.guarda_duas_versoes`.
- **Template:** `equipment.confins.special.guarda_duas_versoes`.
- **Resultado:** Arma Secundária Épica Grau VI, Ferreiro15, EconomySW1, item_level51–60.
- **Materiais:** 7 Ferros de Baliza +3 Pós de Referência +2 Catalisadores VI +6 Fragmentos VI +1 Núcleo da Câmara das Contradições.
- **Taxa:** fórmula global Épico `round_10(C(item_level)×SW1×0,50)` (item_level60 **500 Coroas**).
- **Aquisição:** conclusão elegível Câmara, chance8/15/25%, somente desconhecida.
- **Weapon metadata:** `weapon.form.sword`, `weapon.hands.one`, `weapon.slot.secondary_only`, `weapon.compat.melee`, publicado explicitamente na §19.2.
- **Efeito:** exclusivamente budget de slot/raridade Épico normal, sem duplicar ataque ou turno.

## 22.3 Eco do Encerramento

- **Receita:** `recipe.confins.regente.eco_encerramento`.
- **Resultado:** `enchant.confins.eco_encerramento`, Encantamento **Épico PER Grau VI**, Artífice15, +0,50 p.p. PER (mesma potência do Encantamento Épico PER VI).
- **Materiais:** 5 Pós de Referência +2 Ferros de Baliza +1 Catalisador VI +1 Núcleo do Regente Fraturado.
- **Taxa:** **400 Coroas**, Encantamento Épico Grau VI A.
- **Aquisição:** P36 concluída, revelação direta única e sem RNG; Núcleo P36 é único. Se consumido, não reaparece via replay do boss.
- **Efeito:** nenhum bônus histórico, temporal, de Crônica, Legado ou cap; apenas PER normal dentro do budget.

# 23. World state, narrative state e unlocks

**World state:** nenhum novo `world_state` global é mutado por Missão, Caçada, Masmorra ou vitória P36 de personagem individual. P36 encerra um protocolo **para a trajetória desse personagem**, não altera o servidor de todos por clique. Eventos Mundiais/Crônicas continuam usando seu sistema global independente.

**Character narrative state** (pessoal, grants idempotentes; não duplicar Quest/Unlock em narrativas):

| ID | Evento/condição | Uso permitido |
|---|---|---|
| `narrative.confins.duas_leituras_confirmadas` | P31 concluída | contexto do hub/Marcha |
| `narrative.confins.fratura_reconhecida` | P32 concluída | contextualização de Fratura em falas/Códice |
| `narrative.confins.avesso_nomeado` | P33 concluída | usa nome Avesso sem fingir que é lugar/agente |
| `narrative.confins.ancora_central_compreendida` | P34 concluída | contextualiza função coordenadora da Âncora |
| `narrative.confins.noite_convergencia_reconstruida` | P35 concluída | documentos históricos consultáveis, spoiler legítimo |
| `narrative.confins.protocolo_impossivel_encerrado` | P36 concluída | apresentação pessoal da Câmara; pós-campanha |

**Unlocks de atividade** já enumerados pelo Local: `unlock.hunt.confins.{marcha,estradas,fraturas,no}`, `unlock.explore.confins.{marcha,estradas,fraturas,no}`, `unlock.round.confins.marcha`, `unlock.round.confins.estradas`, `unlock.round.confins.fraturas`, `unlock.round.confins.no`, `unlock.dungeon.confins.{arquivo_retorno,camara_contradicoes}`. Gate de conclusão de campanha: `unlock.campaign.first_journey_complete` (nominalmente concedido P36; se a Fonte Mestra/runtime já possuir entitlement canônico equivalente, **o contrato é o mesmo marco P36 e não uma segunda conclusão**). Nenhum unlock de nível por si só equivale a decisão do jogador de executar Legado.

**Conflito de nomenclatura protegido:** nomes de NPC, IDs do Códice e IDs de unlock não são strings player-facing obrigatórias. Catálogo de IDs é inventário, jamais concessão. O fato de `unlock.location.confins.camara_regencia` estar no inventário não significa que P31–P34 o concedem.

# 24. Idempotência, Crônica, Legado e saída do jogo-base

**Ações únicas:** settlement de Missão, 1 escolha de Equipamento P33/P36, Núcleo único de P36, Receita direta, primeira vitória e primeira conclusão de Masmorra, Descoberta Única, Braseiro, Códice, Feito e unlock são direitos distintos, mas todos idempotentes. Reconnect, callbacks duplicados, resgate de Pending, perda de conexão e reaceite de Secundária não criam novos direitos econômicos.

**P36:** progresso Solo ou Grupo 1–4 preserva contribuições individuais; um membro com P36 não desbloqueia conclusão de quem não tem P35/Nv.60. A vitória válida pode ser compartilhada conforme elegibilidade; o diálogo, a escolha e a conclusão da própria Quest continuam pessoais. O Regente não respawna como farm normal da Câmara.

**Crônica:** a Campanha histórica P1–P36 é linha principal permanente, **não substitui** capítulos, votos, pré-requisitos ou calendário da Crônica; nenhuma votação de Crônica é resolvida por P36 e nenhuma Crônica reabre a Ruptura por mudança de world state da missão. A campanha termina no ato de encerramento do protocolo impossível e o mundo segue com seus perigos.

**Legado:** `Nv.60 + campanha P36 concluída` torna Legado I elegível, sem custo/evento inventado e sem execução automática; a ação real só ocorre em local seguro autorizado, fora de estados incompatíveis, e segue requisitos globais. Após Legado: volta a Nv.1, mantém Campanha completa, NPCs descobertos, Códice, Bestiário, Feitos, receitas, Braseiros permanentes, equipamentos e inventários segundo GDD, porém Regiões altas e Masmorras retornam a gate de nível. P36 não é repetida; XP em Nv.60 não fica em reserva. S36 é opcional e pode ser concluída antes ou depois de qualquer Legado, se os gates de nível vigentes forem atendidos no momento da missão.

**Retorno a Altos:** acesso anterior continua conhecido; requisitos de nível pós-Legado continuam globais. Não existe Região 7 nem portal do Avesso.

# 25. Auditoria de necessidade sistêmica

| Comportamento dos Confins | Sistema global que resolve |
|---|---|
| doze Missões, suspensão, abandono e aceite | Campaign / Quest |
| gates por Local e rota final | Road / Travel / Unlock |
| pools, materiais e Variantes | Hunt / Reward / Loot |
| únicos e Braseiros de campo | Explore / Bonfire |
| familiaridade após primeira manual | Round / Hunt |
| duas Masmorras, 5 encontros, checkpoint e retry | Dungeon |
| regente, placas e telegraph | Combat / Encounter Objects / Boss Phases |
| evidências observadas, objetivos de estudo | Bestiary / Codex |
| cosméticos e milestones | Achievement / Cosmetics |
| 13 catálogos, Runas, Enchants, consumíveis | Crafting / Consumables |
| exclusividade por personagem | Quest / Reward / Idempotency |
| narrativa individual e memória após P36 | Character Narrative State |
| conclusão de P36, cap60 e escolha de Legado | Campaign / Level Cap / Legacy |
| Crônica independente | Chronicle |

**Conclusão proposta:** `NO_NEW_GLOBAL_MECHANIC_REQUIRED`. Placas físicas de boss são elementos de encontro já utilizados em Regiões anteriores; o Avesso nunca vira recurso mecânico novo, e falhas de continuidade são representadas com alvos, Barreiras, telegraphs e evidência narrativa, não viagem temporal.

# 26. Auditoria única de números (classificação A/B/C)

| Contrato / números | Valores finais APROVADOS | Origem |
|---|---|---|
| Região / cap | Confins Nv.51–60; máximo permanente Nv.60 | **B** (faixa) / **A** (cap) |
| Entrada | P30 concluída + Nv.51 | **B** de Altos v1.0.1 / **A** gate global |
| 6 Locais, 2 Masmorras, boss final | nomes e sequência §1–3, §14–16 | **B** |
| Gates Principais | P31 51; P32 53; P33 55; P34 57; P35 59; P36 60 | **A** |
| Gates Secundárias | S31 52; S32 54; S33 55; S34 57; S35 58; S36 60 | **A** |
| Valores UC/UM | Principais7,5UC/11UM; secundárias4,5UC/10UM; total12UC/21UM | **A** |
| Missões XP / Coroas | §5: Principais622.570XP/7.100; Secundárias360.830XP/4.280; total983.400XP/11.380 | **A** derivado |
| Material de Missão | 21UM×2=42 básicos vinculados; distribuição Ferro15/Couro6/Musgo11/Pó10 | **A** quantidade; **C** identidade/divisão |
| Campanha | P33 escolha Raro Nv.55; P36 escolha Lendário Nv.60, sempre 1 de 3, +0, Bind-on-Acquire | **A**; nomes **C** |
| Curva | 51→60=1.580.500XP; XP_ref(60)=203.800; XP_P36=183.420 nominal, cap impede acúmulo | **A** |
| NPCs / criaturas e arquétipos | 5 NPCs, 9 bases, 3 Elites, nomes e perfis B | **B** |
| Kits, níveis, IA e pools | níveis de §9/10; pools §11 com pesos100; chances de Variante 14/16/18/20% (Marcha/Estradas/Fraturas/Nó) | **C** |
| Material básico de Hunt | Comum80%→1, Incomum100%→1–2, Elite3–4 + Catalisador; §9 escolhe só identidade | **A** chance/quantidade; **C** pesos |
| Desbravar | categorias8/22/15/25/10/20, grande8%, menor2,5%, 4V econômico; 11 únicos, 121.364XP nominal | **A** fórmula; **C** resultados/ref levels |
| Ronda | ×5/×10/×20, 3min, 2V, 1ª vitória manual **posterior** local | **A** motor/familiaridade; **C** grants locais |
| Dungeon A | Nv.54–57, ref.57, Ruptura60; XP 14.870/18.220/24.240; Coroas770/1.150/1.800 | **A** intervalo/fórmula; **C** ref regional57 |
| Dungeon B | Nv.58–60, ref.60; XP15.550/19.050/24.240; Coroas800/1.200/1.800 | **A** intervalo/fórmula; **C** ref regional60 |
| Economia de Dungeon | Estável 8+2Cat+1Núcleo+2Frag; Fraturada11+3+2+4; Ruptura14+4+4+7 | **A** |
| Primeira Conclusão | XP da conclusão ×1,60 uma vez por dificuldade elegível | **A** |
| Equipamento de Dungeon | 1 roll; chances de raridade 25/50/22/2,8/0,2; 10/45/38/6,5/0,5; 0/20/60/19/1 | **A** |
| Runa Dungeon | chances20/35/50%, raridades globais | **A** |
| Pity Dungeon | pontos1/2/4; hard Lendário+24; Mítico200 | **A** |
| Receita Dungeon | Estável8%/Fraturada15%/Ruptura25%, só desconhecida | **A** |
| Vigor Dungeon | 25/35/50; limites de consumíveis6/5/4; checkpoint70/40/20 após encontro3 | **A** |
| Dungeon duração/Retry | 25–35/30–40/35–50min; 4h inatividade/24h absoluta; 60s confirmação; retry mesmo run | **A** |
| Objetos Chefes | 2×HP25% Comum referência, DEF100%, 5% mitigação cada, Barreira5% por restante; fases70/35 | **C**, sem nova mecânica global |
| Regente | perfil Chefe HP220%/ATQ110%/DEF110%/AGI100%, Nv.60; 1 Núcleo primeira vitória | **A** perfil / **B** nome / **C** kit & núcleo |
| Bestiário | COMMON10/30/60; RARE8/22/40; ELITE10/25/45; BOSS10/30/50; marcos3% | **A**; configuração de marcos **C** |
| Grau VI | item_level51–60; Ofício15; Lendário16+Receita; raridade/crafting por SW | **A** |
| Runa VI taxas | 300/600/1.000; materiais e potência §20 | **A** |
| Enchant VI taxas | 200/400/700; materiais e potência §20 | **A** |
| Consumível VI taxas | 100/150/150/500/200/250/300; poder global | **A** |
| Feitos/Códice | 13 Feitos, 22 entradas de Códice; sem bônus oculto | **C** nomes/condições; **A** sem bônus |
| Legado / Crônica | primeiro Legado Nv.60+P36; não automático; Crônica separada; cap XP | **A** |

**Controle:** cada percentual acima é ou fórmula/constante do GDD A ou peso/kits propostos C identificados como tal. Nenhuma chance de economia normal é redefinida pela tabela de identidade do Material. Os totais de Missões respeitam a baseline; a distribuição-alvo de XP do GDD é diretriz não rígida, e parte da XP nominal Nv.60 não é recebida porque o cap descarta excedente, conforme regra A.

# 27. Auditoria de continuidade, spoilers e exclusividade

**Altos → Confins:** P30 final + Nv.51 abre Marcha. Personagem não entra conhecendo natureza integral do Avesso nem desfecho total do Regente. Braseiros/Locais de Altos permanecem conhecidos, e gates após Legado respeitam nível atual.

**Fratura/Avesso:** não criar portal, inferno, Reino do Avesso, inimigo moral consciente, teleporte/rewind de personagem ou criatura abstrata autossuficiente. Efeitos de duas posições são biologia/ecologia visual e fenômeno de estado observado, não segunda recompensa nem ação extra.

**Instituições:** Conselho/Câmara das Rotas, Custódia, Regência, Hemaris, Desvelados são instituições/obras históricas distintas. Âncora Central coordena referências; não é gerador de energia. Deterioração precede Asterianos; Regência e Desvelados não são blocos moralmente uniformes. Neris autorizou sabotagem consciente, Cael prosseguiu sob opções perigosas, a cascata encerrou o mundo conhecido sem prova de uma única causa pura. Não substituir nome **Roven Pell** por Oris Pell.

**Regente:** não é Cael vivo/ressuscitado, deus, assassino moral onisciente nem Avesso encarnado. Derrotá-lo encerra o protocolo, não cura sistema cósmico. Códice admite registros ausentes/desconhecidos.

**P36 + Legado + Crônica:** P36 fecha só a campanha permanente da primeira jornada; Legado é escolha posterior com os pré-requisitos globais; Crônica mantém sistema coletivo/temporal separado. S36 opcional pós-P36 não altera fechamento ou destruição do Véu.

**Novo conteúdo C:** nomes de Materiais, Braseiros, S36 Verificador, kits, objetos e recompensas foram propostos explicitamente e não podem ser considerados já canônicos na Bíblia. Não há NPC moderno permanente adicional, sétimo Local, nova Raça, novo recurso de combate ou taxonomia de weapon_family restaurada.

# 28. Inventário autoritativo de IDs da Fonte FINAL

**Os IDs seguintes são uma lista editorial fechada, não um comando de concessão.** Geração efetiva de instâncias, chaves econômicas e schema pertencem à Engenharia. Um mesmo ID mencionado em Missão + Códice + auditoria só existe uma vez no catálogo de conteúdo. Os prefixos `confins` e `region.confins_do_veu` não se chocam com `tdo`, `vde`, `nareth`, `varzeas` ou `altos`.

## 28.1 achievement (13)

- `achievement.confins.ancora_compreendida`
- `achievement.confins.arquivo_estavel`
- `achievement.confins.avesso_nomeado`
- `achievement.confins.cadeia_ruptura`
- `achievement.confins.cartografo_ausencias`
- `achievement.confins.cinco_braseiros`
- `achievement.confins.contradicoes_estavel`
- `achievement.confins.fratura_observada`
- `achievement.confins.naturalista`
- `achievement.confins.primeira_marcha`
- `achievement.confins.regente_primeira`
- `achievement.confins.regiao`
- `achievement.confins.s36`

## 28.2 bonfire (5)

- `bonfire.confins.estrada_conferida`
- `bonfire.confins.limiar_firme`
- `bonfire.confins.marco_duplo`
- `bonfire.confins.no_retorno`
- `bonfire.confins.testemunha`

## 28.3 boss (4 Chefes + 1 direito de primeira vitória)

- `boss.confins.arquivo.o_que_chega_antes`
- `boss.confins.contradicoes.testemunha_impossivel`
- `boss.confins.regente_fraturado`
- `boss.confins.regente_fraturado.first_victory`
- `boss.confins.s36.verificador_sem_testemunhas`

## 28.4 codex (22)

- `codex.confins.ancora_central_coordenacao`
- `codex.confins.avesso_estados`
- `codex.confins.cadeia_ruptura_documentada`
- `codex.confins.casa_presente_ausente`
- `codex.confins.convergencia_reconstrucao`
- `codex.confins.depois_ultima_ordem`
- `codex.confins.duas_leituras_rota`
- `codex.confins.duas_ordens_oficiais`
- `codex.confins.dungeon.arquivo_retorno`
- `codex.confins.dungeon.camara_contradicoes`
- `codex.confins.dungeon.chegada_antes`
- `codex.confins.dungeon.ordens_irreconciliaveis`
- `codex.confins.dungeon.registro_repetido`
- `codex.confins.dungeon.testemunha_impossivel`
- `codex.confins.fratura_definicao`
- `codex.confins.marcos_incompativeis`
- `codex.confins.nomes_ordem_errada`
- `codex.confins.pegadas_incompativeis`
- `codex.confins.protocolo_encerrado`
- `codex.confins.regente_natureza`
- `codex.confins.regiao`
- `codex.confins.testemunha_ontem`

## 28.5 consumable (7)

- `consumable.confins.antidoto`
- `consumable.confins.cura`
- `consumable.confins.dissipador`
- `consumable.confins.protecao`
- `consumable.confins.purificacao`
- `consumable.confins.resguardo`
- `consumable.confins.vigor`

## 28.6 craft (13)

- `craft.confins.curteiro.cabeca.capuz_nevoa`
- `craft.confins.curteiro.maos.luvas_testemunha`
- `craft.confins.curteiro.pes.botas_limiar`
- `craft.confins.curteiro.torso.casaco_ausencias`
- `craft.confins.ferreiro.2h.arco_retorno`
- `craft.confins.ferreiro.cabeca.elmo_referencia`
- `craft.confins.ferreiro.maos.manoplas_marco`
- `craft.confins.ferreiro.pes.grevas_retorno`
- `craft.confins.ferreiro.principal.lamina_baliza`
- `craft.confins.ferreiro.secundaria.guarda_marcha`
- `craft.confins.ferreiro.torso.couraca_marcha`
- `craft.confins.joalheiro.acessorio.selo_referencia`
- `craft.confins.joalheiro.artefato.relicario_duplo`

## 28.7 creature (9)

- `creature.confins.andarilho_repetido`
- `creature.confins.aranha_limiar`
- `creature.confins.cao_nevoa`
- `creature.confins.casca_reflexo`
- `creature.confins.cervo_passo_duplo`
- `creature.confins.gralha_duas_sombras`
- `creature.confins.mariposa_sem_horizonte`
- `creature.confins.sanguessuga_palida`
- `creature.confins.vigia_desfasado`

## 28.8 dungeon (2)

- `dungeon.confins.arquivo_retorno`
- `dungeon.confins.camara_contradicoes`

## 28.9 dungeon_bonfire (2)

- `dungeon_bonfire.confins.arquivo.ala_retorno`
- `dungeon_bonfire.confins.contradicoes.patio_referencia`

## 28.10 dungeon_creature (1)

- `dungeon_creature.confins.arquivo.eco_sem_origem`

## 28.11 dungeon_elite (3)

- `dungeon_elite.confins.arquivo.guardiao_retorno`
- `dungeon_elite.confins.contradicoes.custodio_no_central`
- `dungeon_elite.confins.contradicoes.preceptor_contradicao`

## 28.12 elite (3)

- `elite.confins.custodio_desfasado`
- `elite.confins.predador_duas_pegadas`
- `elite.confins.viuva_intervalo`

## 28.13 enchant (9)

- `enchant.confins.abrigo_ultimo`
- `enchant.confins.ancora_valida`
- `enchant.confins.duas_sombras`
- `enchant.confins.eco_encerramento`
- `enchant.confins.fio_presente`
- `enchant.confins.ordem_conferida`
- `enchant.confins.passo_sem_eco`
- `enchant.confins.pedra_lida`
- `enchant.confins.trilha_segura`

## 28.14 equipment (8)

- `equipment.confins.campaign.p33.capuz_dupla_leitura`
- `equipment.confins.campaign.p33.relicario_registro_incompleto`
- `equipment.confins.campaign.p33.selo_marco_valido`
- `equipment.confins.campaign.p36.guarda_ultimo_protocolo`
- `equipment.confins.campaign.p36.relicario_ordem_findada`
- `equipment.confins.campaign.p36.selo_referencia_presente`
- `equipment.confins.special.guarda_duas_versoes`
- `equipment.confins.special.relicario_entrada_duplicada`

## 28.15 explore (43)

- `explore.confins.estradas.arquivo_retorno`
- `explore.confins.estradas.atmos.lama_incompleta`
- `explore.confins.estradas.atmos.marco_nao_visto`
- `explore.confins.estradas.atmos.placa_curva`
- `explore.confins.estradas.braseiro_conferida`
- `explore.confins.estradas.combate`
- `explore.confins.estradas.estacas_alternadas`
- `explore.confins.estradas.estrada_sem_ponte`
- `explore.confins.estradas.memoria_fundacao`
- `explore.confins.estradas.recurso`
- `explore.confins.estradas.retorno_sem_ida`
- `explore.confins.fraturas.angulo_sem_retorno`
- `explore.confins.fraturas.atmos.dobras_nevoa`
- `explore.confins.fraturas.atmos.pedra_sem_mancha`
- `explore.confins.fraturas.atmos.silencio_limiar`
- `explore.confins.fraturas.braseiro_limiar`
- `explore.confins.fraturas.combate`
- `explore.confins.fraturas.corte_referencia`
- `explore.confins.fraturas.eco_pedra`
- `explore.confins.fraturas.ficha_dupla`
- `explore.confins.fraturas.linhas_gastas`
- `explore.confins.fraturas.recurso`
- `explore.confins.marcha.atmos.nevoa_sem_vento`
- `explore.confins.marcha.atmos.passo_umido`
- `explore.confins.marcha.atmos.pedra_volta`
- `explore.confins.marcha.caderno_marcha`
- `explore.confins.marcha.combate`
- `explore.confins.marcha.duas_balizas`
- `explore.confins.marcha.giz_apagado`
- `explore.confins.marcha.marca_repetida`
- `explore.confins.marcha.recurso`
- `explore.confins.marcha.sino_distante`
- `explore.confins.no.atmos.metal_paz`
- `explore.confins.no.atmos.parede_repetida`
- `explore.confins.no.atmos.registro_sem_voz`
- `explore.confins.no.braseiro_retorno`
- `explore.confins.no.camara_contradicoes`
- `explore.confins.no.combate`
- `explore.confins.no.corda_medida`
- `explore.confins.no.junta_marco`
- `explore.confins.no.ordem_muro`
- `explore.confins.no.recurso`
- `explore.confins.no.rede_incompleta`

## 28.16 location (6)

- `location.confins.camara_regencia`
- `location.confins.estradas_ausentes`
- `location.confins.fraturas_limiar`
- `location.confins.marcha_nebulosa`
- `location.confins.no_central`
- `location.confins.ultimo_refugio`

## 28.17 material (4)

- `material.confins.couro_marcha`
- `material.confins.ferro_baliza`
- `material.confins.musgo_limiar`
- `material.confins.po_referencia`

## 28.18 material.special (3)

- `material.special.confins.core.arquivo_retorno`
- `material.special.confins.core.camara_contradicoes`
- `material.special.confins.core.regente_fraturado`

## 28.19 mission (12)

- `mission.confins.p31`
- `mission.confins.p32`
- `mission.confins.p33`
- `mission.confins.p34`
- `mission.confins.p35`
- `mission.confins.p36`
- `mission.confins.s31`
- `mission.confins.s32`
- `mission.confins.s33`
- `mission.confins.s34`
- `mission.confins.s35`
- `mission.confins.s36`

## 28.20 narrative (6)

- `narrative.confins.ancora_central_compreendida`
- `narrative.confins.avesso_nomeado`
- `narrative.confins.duas_leituras_confirmadas`
- `narrative.confins.fratura_reconhecida`
- `narrative.confins.noite_convergencia_reconstruida`
- `narrative.confins.protocolo_impossivel_encerrado`

## 28.21 npc (5)

- `npc.confins.eris_val`
- `npc.confins.haro_sen`
- `npc.confins.roven_pell`
- `npc.confins.sera_nol`
- `npc.confins.talen_nyr`

## 28.22 quest (6)

- `quest.confins.s31.completed`
- `quest.confins.s32.completed`
- `quest.confins.s33.completed`
- `quest.confins.s34.completed`
- `quest.confins.s35.completed`
- `quest.confins.s36.completed`

## 28.23 recipe (3)

- `recipe.confins.arquivo.relicario_entrada_duplicada`
- `recipe.confins.contradicoes.guarda_duas_versoes`
- `recipe.confins.regente.eco_encerramento`

## 28.24 rune (8)

- `rune.confins.desvio`
- `rune.confins.fenda`
- `rune.confins.marco`
- `rune.confins.passagem`
- `rune.confins.permanencia`
- `rune.confins.resguardo`
- `rune.confins.retorno`
- `rune.confins.testemunha`

## 28.25 unlock (21)

- `unlock.campaign.first_journey_complete`
- `unlock.dungeon.confins.arquivo_retorno`
- `unlock.dungeon.confins.camara_contradicoes`
- `unlock.explore.confins.estradas`
- `unlock.explore.confins.fraturas`
- `unlock.explore.confins.marcha`
- `unlock.explore.confins.no`
- `unlock.hunt.confins.estradas`
- `unlock.hunt.confins.fraturas`
- `unlock.hunt.confins.marcha`
- `unlock.hunt.confins.no`
- `unlock.location.confins.camara_regencia`
- `unlock.location.confins.estradas_ausentes`
- `unlock.location.confins.fraturas_limiar`
- `unlock.location.confins.marcha_nebulosa`
- `unlock.location.confins.no_central`
- `unlock.location.confins.ultimo_refugio`
- `unlock.round.confins.estradas`
- `unlock.round.confins.fraturas`
- `unlock.round.confins.marcha`
- `unlock.round.confins.no`

# 29. Deliberação final de Game Design, auditoria e governança

## 29.1 Decisões C aprovadas, sem alterar fontes superiores

A revisão de Game Design **aprova expressamente** como escolhas regionais próprias e fechadas da sexta Região, e não como valores presumidos do GDD/Bíblia:

| Eixo C | Deliberação aprovada | Justificativa e limite |
|---|---|---|
| Identidade regional aplicada | Ícone 🌫️, papel seguro do Último Refúgio, progressão das evidências e interpretação contextual dos fenômenos | Importa o cânone; não define Avesso como agente ou Local adicional |
| Cinco Braseiros | §3, nomes, IDs, Local, gates e modo de descoberta | Rede permanente comum, sem portais/rituais/mecânica nova |
| Quatro Materiais VI | Ferro de Baliza, Couro de Marcha, Musgo de Limiar, Pó de Referência, distribuição das 42 unidades de Missão e identidade de material por criatura | Taxonomia Metal/Couro/Reagente/Essência global preservada; pesos não são chances de drop |
| Progressão espacial e 12 Missões | §2 e §§7–8, grants de acesso, Caçada, Desbravar e Ronda individual por Local, objetivos e encontros de cada Missão | Gate P30+Nv.51, offsets do GDD e sequência de 6 Locais preservados |
| Boss opcional S36 | Verificador sem Testemunhas, kit, Lv.60 e economia zero | Conflito sobre rotinas úteis/obsoletas após P36; não cria fim alternativo |
| Criaturas/Elites | Faixas, kits, IA, Variantes e distribuições §9–10; duas exceções fixas `MISSION_SCRIPTED` de P34/S34 | Identidades canônicas B intactas, sem turnos/clones/estados globais novos |
| Caçada e Ronda | Pesos exatos §11 e chances de Variante **14/16/18/20%**; familiaridade manual posterior local §13 | Mantém settlement, elegibilidade, grupos e Vigor globais |
| Desbravar | 11 descobertas únicas e 43 IDs de resultados, XP derivada por `reference_level` local §12 | Sem recompensas extras por Fraturas, sem repetir grants únicos |
| Masmorra A/B | Encontros, chefes, estados/telegraphs, referências 57/60, material por unidade e objetos de encontro §§14–15 | Usa 5 encontros, dificuldade, run, Retry, checkpoint, economia, pity e chances globais |
| Regente Fraturado | §16: três fases, duas Âncoras de Registro como objetos do combate e Núcleo único | Manifestação de Cael/protocolos/registros, sem cura do Véu ou destruição do Avesso |
| Bestiário, Códice, Feitos | §10, §§17–18, condições de domínio, 22 entradas e 13 Feitos | Conhecimento documentado, não onisciência; cosméticos sem poder |
| Grau VI e recompensas | §§5, 19–22: 13 famílias de Crafting, oito Runas, oito Encantamentos, sete Consumíveis, três receitas e duas escolhas de Campanha | Fórmulas, raridades, potência, tags e orçamento globais não modificados |
| Pós-campanha | P36 encerra protocolo impossível; Legado I exige P36+Nv.60, ação separada; S36 opcional | Mantém cap60, Crônica distinta e acesso conhecido condicionado ao nível após Legado |

## 29.2 Auditoria de gates, conteúdo e números

- **Entrada:** P30 concluída + Nv.51 abre Marcha/P31; P31 só abre Marcha e Último Refúgio. P32/Nv.53 abre Estradas; P33/Nv.55 abre Fraturas; P34/Nv.57 abre Nó; P35 etapa 7 abre Câmara sem exigir Nv.60 para a navegação. P36 exige separadamente P35 concluída + Nv.60. S31 não atravessa Estradas antes de P32. S35 não exige P35/Nv.59 e S36 exige P36 sem tornar-se requisito da Campanha.
- **Economia de atividade:** conclusão da Principal local concede apenas `unlock.hunt` e `unlock.explore` daquele Local. `unlock.round` exige vitória válida na Caçada Manual do mesmo Local **posterior** à conclusão da Principal. Desbravar/Masmorras/roteirizados não antecipam esse direito.
- **Encontros roteirizados:** P34 usa Custódio Desfasado **Nv.57** e S34 usa Andarilho Repetido **Nv.57** como overrides de nível próprios de Missão, expressamente permitidos como encontros de conteúdo fixo. Não mudam as faixas de mundo aberto Nv.59–60 e Nv.52–56, respectivamente; sem nova elegibilidade de Caçada, Variante ou economia.
- **Masmorras:** Arquivo do Retorno e Câmara das Contradições mantêm cinco encontros, dois Chefes oficiais, referências, progressão de dificuldades, chance de Receita, recompensas, Núcleos, Códice, Bestiário, Feitos e fechamento por run. Fases Registro Antecipado/Registro Refeito no Arquivo são apenas nomes de fases já existentes, para alinhar `mastery_required`. As placas inertes da sala da Testemunha não são as Placas de Afirmação interativas da Fase II.
- **Aritmética verificada:** Principais **622.570 XP nominais / 7.100 Coroas**; Secundárias **360.830 XP nominais / 4.280 Coroas**; total **983.400 XP nominais / 11.380 Coroas / 12 UC / 21 UM / 42 Materiais Básicos vinculados**. Curva Nv.51→60 **1.580.500 XP**. P36 **183.420 XP nominais** usa `XP_ref(60)=203.800` e jamais acumula XP além do cap. Valores de §5 preservados.
- **IDs:** inventário editorial de **219 entradas catalogadas** nas §§28.1–28.25 (inclui um direito de primeira vitória sob `boss.*`, que não é um quinto inimigo). IDs são regionais, sem reutilização dos namespaces das cinco Regiões anteriores. Um catálogo não concede entitlement.
- **Lore:** Bíblia v3.0 preservada em nomes de NPCs, Bestiário, Masmorras, Regente, natureza do Avesso e sequência histórica. Códice mostra evidências proporcionais ao progresso; P36 encerra o protocolo, não cura o Véu, não apaga o Avesso e não cria Região 7.

## 29.3 Weapon Metadata e dependência externa de sincronização

A §19.2 declara explicitamente `weapon_form`, `handedness`, slot eligibility e compatibility tags para **todas as cinco armas regionais Grau VI** nela publicadas. Seus IDs e valores pertencem ao vocabulário de `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`: `weapon.form.sword/dagger/bow/mace`, `weapon.hands.one/two`, `weapon.slot.main_only/secondary_only/main_two_handed` e `weapon.compat.melee/bow`. Não se restaura `weapon_family` nem se deduz compatibilidade de nome, Classe ou visual. Não foi encontrada divergência semântica entre as duas Fontes.

**Dependência de governança, não lacuna de Game Design:** registrar esta **Fonte Regional FINAL** e o **Contrato Global de Weapon Metadata FINAL** como autoridades vigentes no `SOURCE_AUTHORITY` do repositório, e sincronizar a Engenharia a partir desse índice. Este trabalho **não alterou nem verificou o registro atualizado do repositório**; a aprovação documental não prova sincronização. O handoff de implementação deve aguardar essa confirmação externa, sem o Codex preencher lacunas por código legado.

## 29.4 Histórico PROPOSTA → FINAL · mudanças exatas

Base auditada: `ASTERION_CONTEUDO_CONFINS_DO_VEU_v1.0.0_PROPOSTA.md`, SHA-256 **`deffaa01fc983fc8c61f4456702a5f321575666eaa393ffb1ea3ef8a94e55a9c`**.

1. **Promoção documental** para `v1.0.0 FINAL` e deliberação explícita de todas as categorias regionais C já propostas, sem trocar seus conteúdos.
2. **Correção de transcrição:** a linha-resumo da §26 é harmonizada com a tabela real §11: chances de Variante Marcha/Estradas/Fraturas/Nó **14/16/18/20%**, não `12/14/16/18%`.
3. **P34/S34:** esclarecer que Custódio Desfasado Nv.57 e Andarilho Repetido Nv.57 são **encontros roteirizados de nível fixo**, exceções documentadas às respectivas faixas de Caçada, preservadas em suas definições normais.
4. **Bestiário Arquivo:** nomear as fases já existentes I/II como **Registro Antecipado/Registro Refeito**, satisfazendo a referência de Domínio sem criar nova fase, recompensa ou efeito.
5. **Câmara:** explicitar que placas documentais inertes do cenário são distintas das duas Placas de Afirmação combatíveis da Fase II, sem modificar número, HP, mitigação ou loot.
6. **Catálogo de IDs:** explicitar que quatro inimigos `boss.confins.*` mais um marco de primeira vitória não constituem cinco Chefes. Corrigir a classificação editorial da faixa da Masmorra B de **B para A** (a fórmula de faixa é global).
7. **Fechamento de governança:** registrar aprovação, contrato Weapon Metadata compatível e pendência real de sincronização no `SOURCE_AUTHORITY`; remover avisos de “proposta pendente” incompatíveis com este estado.

**Nenhum valor de XP, Coroas, UC, UM, Material, peso de pool, nível de Missão, nível de encontro, quantidade de objeto, dano, cooldown, recompensa, item, Receita, Runa, Encantamento, Consumível ou Núcleo da PROPOSTA foi rebalanceado.** Não houve alteração na Bíblia, GDD, Altos nem no código.

## 29.5 Estado de design FINAL

**Design:** nenhuma contradição de conteúdo pendente para os contratos publicados nesta Fonte após a auditoria. Não é necessário mecanismo global novo.

`NO_NEW_GLOBAL_MECHANIC_REQUIRED`

`CONFINS_DO_VEU_CONTENT_STATUS = FINAL_APPROVED`

**Handoff à Engenharia:** permitido **após** reconhecimento desta Fonte e do contrato Weapon Metadata no `SOURCE_AUTHORITY`. Não confundir `FINAL_APPROVED` com sincronização executada, PR mesclado ou código implementado.
