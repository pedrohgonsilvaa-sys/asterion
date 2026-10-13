# Autoridade das Fontes

**Índice atualizado:** 2026-10-12. As notas de implementação mais abaixo preservam snapshots históricos anteriores e não substituem as Fontes oficiais vigentes nem o estado atual do repositório.

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.6.0 — Fonte Mestra Consolidada**

Arquivo vigente: `ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`.

Estado oficial:

- a v1.6.0 substitui integralmente a v1.5.0 e versões anteriores;
- a v1.6.0 preserva as regras de Grupo persistente, Campanha cooperativa, escala de Chefes de Campanha, sequência PvPvE e lock de Domínio do Rastro; complementa com Referência da Jornada, Caçada multialvo como encontro e unidade econômica, composição da presa congelada antes do desfecho PvPvE, Armas × Artes, `weapon_requirement`, Mercado, Guildas e as máquinas de estado das seis Classes, sem reabrir os valores publicados da Baseline Numérica v1.0;
- a Baseline Numérica v1.0 está fechada para implementação e testes;
- a v1.4.9 formaliza o fechamento único de `HP Máximo`, `ATQ`, `DEF` e `AGI` estáticos finais em pontos inteiros com `round_half_up`, além de HP atual inteiro; não altera percentuais, curvas, custos, recompensas ou parâmetros de balanceamento;
- a reabertura anterior da conversão absoluta da unidade de XP de inimigo foi encerrada na v1.4.3;
- não existe reabertura numérica vigente na baseline;
- a v1.4.9 formaliza que HP Máximo, ATQ, DEF e AGI estáticos finais fecham uma única vez com `round_half_up` após toda a composição estática; HP atual autoritativo é inteiro e HP legado fracionário é fechado para baixo em fronteira segura;
- Cosméticos possui três categorias oficiais: Aparência, Título e Moldura.

## Fonte regional vigente

A vertical slice Nv.1–10 usa como autoridade de conteúdo:

**ASTERION — Conteúdo: Terras do Ocaso v1.0.16 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.16_FINAL.md`.

Ela define Locais, Braseiros permanentes, Missões, Feitos, Bestiário, inimigos, descobertas e demais conteúdo regional consolidado das Terras do Ocaso.

A v1.0.16 sucede a v1.0.15 exclusivamente para formalizar os pools temáticos de Material Básico do Corvo de Fuligem, do Alfa Cinéreo e do Peregrino Calcinado. Os pesos escolhem somente a identidade de cada unidade depois que a chance e a quantidade globais do contexto já foram resolvidas; não alteram Catalisadores, XP, Coroas, Equipamentos, Caçadas, Rondas, Desbravar ou qualquer outra regra econômica.

Quando a Fonte Regional especificar conteúdo dentro de parâmetros sistêmicos da Fonte Mestra, ambas devem ser aplicadas em conjunto. Em conflito estrutural ou numérico, a Fonte Mestra prevalece; em conteúdo regional fechado, a revisão vigente prevalece sobre rascunhos ou versões regionais anteriores.

A segunda região usa a autoridade de conteúdo **Vales dos Enforcados v1.0.6 FINAL**, em `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.6_FINAL.md`. A v1.0.6 sucede a v1.0.5 exclusivamente para fechar o perfil numérico do encontro roteirizado da Etapa 7 de S12 — Os Nomes Presos à Madeira. Não altera economia, progressão, narrativa regional, demais criaturas, pools, Caçada, Ronda, Masmorras ou recompensas regionais.

A terceira região usa como autoridade de conteúdo **Planícies de Nareth v1.0.0 FINAL**, em `ASTERION_CONTEUDO_PLANICIES_DE_NARETH_v1.0.0_FINAL.md`. Ela rege exclusivamente o conteúdo regional das Planícies de Nareth, no mesmo nível hierárquico regional de Terras do Ocaso e Vales dos Enforcados, subordinada à Fonte Mestra e sem prevalecer sobre outras Regiões fora de seu próprio escopo.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI — atualização 2026-10-11, sincronizada com Fonte Mestra v1.6.0 + Terras do Ocaso v1.0.15 + Vales dos Enforcados v1.0.5**

Arquivo vigente: `ASTERION_UI_DECISOES_2026-10-11_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.5.md.

A Fonte Visual/UI v1.6.0 permanece vigente. A revisão regional Vales v1.0.6 não altera apresentação e não exige nova versão Visual/UI; o documento atual, sincronizado com Vales v1.0.5, continua aplicável à apresentação. A revisão TDO v1.0.16 também não altera regras ou estrutura de apresentação; a mesma Fonte Visual/UI v1.6.0 continua aplicável sem nova versão.

Esta revisão inclui a HUD compacta de Retaliação, Oportunismo, Mira, Trama, Presságio e Fulgor/Julgamento, além do aviso de Arte inválida por falta de armamento compatível. A interface segue subordinada à regra mecânica da Fonte Mestra.

Ela define nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram. É subordinada à Fonte Mestra para regras mecânicas/números e à Fonte Regional para conteúdo regional oficial.

Exemplos de mockup não criam regra mecânica ou conteúdo canônico quando a autoridade correspondente já definir outro valor/estado.

## Regras cooperativas e roadmap técnico vigentes

A regra normativa de Grupo, Campanha cooperativa, Caçada em Grupo, PvPvE, Domínio do Rastro e integração com Ronda está incorporada à Fonte Mestra v1.6.0, §§51–57. A autoridade regional TDO v1.0.16 aplica essa regra à P1 e à S6; Vales v1.0.6 preserva o conteúdo regional vigente e fecha exclusivamente o perfil numérico do encontro roteirizado de S12.

A especificação técnica `docs/specs/MMO_PVPVE_FINAL_SPEC_V1.md` e os roadmaps `docs/specs/COOPERATIVE_MULTIPLAYER_ROADMAP_V2.md` e `docs/specs/OPTIONAL_SIDE_QUEST_BOSSES_V2.md` orientam entrega e verificação, sempre subordinados às Fontes oficiais. O antigo Decision Register MMO/PvPvE é histórico/supersedido e não é autoridade vigente.

O blocker do perfil numérico do encontro de S12 está encerrado pela Fonte Regional Vales v1.0.6, exclusivamente para o encontro roteirizado da Etapa 7. A materialização continua subordinada à fórmula e às regras globais da Fonte Mestra v1.6.0.

## Fontes complementares de Lore e Direção Visual

As Fontes abaixo complementam as autoridades estrutural, regional e de Visual/UI. Elas não podem sobrescrever regra mecânica, conteúdo regional FINAL ou apresentação player-facing já fechada em autoridade superior.

### Lore canônica complementar

**Arquivo vigente:** `ASTERION_LORE_BIBLE_CANON_v1.1.md`

A v1.1 substitui a v1.0. Define verdade narrativa consolidada, cosmologia, relações históricas, famílias fenotípicas reconhecíveis das cinco Raças, limites de revelação e segredos de autor necessários para impedir contradições de Lore. Quando um fato já estiver definido em Fonte Mestra ou Regional vigente, essas Fontes superiores prevalecem.

### Direção visual especializada — personagens humanoides

**Arquivo vigente:** `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v1.2.md`

A v1.2 substitui a v1.1 para produção futura. Define famílias fenotípicas legíveis das 5 Raças, fundos de herança, composição de fundos Raça × Classe, leitura das 6 Classes e 12 Caminhos, NPCs, adaptação regional, Aparências, estados de pose, composição e proibições de humanoides.

### Direção visual especializada — criaturas e biomas

**Arquivo vigente:** `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`

A v1.1 atualiza a direção visual de criaturas e biomas, incluindo o Guardião do Último Rastro, sem substituir mecânica ou conteúdo das Fontes Regionais FINAL.

Define ecologia visual, anatomia, silhueta, materiais, escala, habitats, Variantes, Elites, criaturas de Masmorra e Chefes. Nas Regiões 1–2, mecânica e conteúdo continuam pertencendo às Fontes Regionais FINAL.

### Direção visual especializada — ambientes

**Arquivo:** `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`

Define identidade ambiental, arquitetura, materiais, função histórica, Locais, hubs, clímax, Masmorras, progressão visual e limites de spoiler.

### Especificação técnica de geração

**Arquivo:** `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.0.md`

Define **como renderizar** o conteúdo já autorizado: canvas, proporção, pixel art, materiais, anatomia técnica, integridade de armas/focos, estados de pose, transparência, pós-processamento, nomenclatura e QA. Não cria Lore nem substitui as Bíblias especializadas.

### Controle operacional de produção

**Arquivo:** `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v1.1.md`

Documento de produção, não Fonte de cânone. A v1.1 substitui a v1.0 e distribui as 10 âncoras raciais, as 60 âncoras Raça × Classe, fenótipos dentro das faixas canônicas, pose, estado de arma/foco e os 30 fundos-base Raça × Classe. Qualquer linha que conflite com Fonte autoritativa deve ser corrigida na Matriz, nunca na Fonte superior.

## Decisão visual aprovada em 06/10/2026 — legibilidade racial e fundos

Para assets de seleção e personagens jogáveis, a identidade racial não pode depender apenas de postura, roupa ou texto. As cinco Raças possuem famílias fenotípicas recorrentes, com exceções possíveis por descendência mista. Assets de seleção usam o centro fenotípico; skins Raça × Classe preservam ao menos dois marcadores raciais fortes.

Fundos de seleção racial passam a usar motivos de herança próprios; fundos Raça × Classe combinam herança racial + função da Classe + adaptação regional quando aplicável. O mesmo fundo genérico de ruínas para todo o catálogo deve ser rejeitado.

## Regra para produção visual

Antes de gerar, refazer ou aprovar um asset:

1. localizar a entidade e o conteúdo na Fonte Mestra/Regional;
2. aplicar a Lore canônica e o gate de spoiler correspondente;
3. aplicar a Bíblia visual especializada do assunto;
4. aplicar a Fonte Visual/UI quando o asset pertencer a uma tela específica;
5. aplicar a Bíblia Técnica de Geração;
6. aplicar a Matriz de Produção quando houver âncora/linha correspondente;
7. reprovar assets com anatomia quebrada, objeto impossível, spoiler ou identidade visual contraditória mesmo que a atmosfera geral esteja boa;
8. não usar documentos antigos de prompts como autoridade quando divergirem das Fontes vigentes.

## Decisão adicional aprovada no projeto

Em 20/09/2026 foi aprovada explicitamente a seguinte regra de estado inicial, necessária antes da primeira exposição de Vigor na HUD:

**Personagem novo inicia com 100 / 100 Vigor.**

Esta é uma decisão aprovada pelo projeto e deve ser tratada como autoritativa para implementação até sua incorporação em futura consolidação textual da Fonte Mestra. Ela não altera:

- Vigor Máximo = 100;
- regeneração +1 a cada 14m24s;
- reset das 06:00 não reabastece;
- custos de Vigor já definidos;
- regra de que Braseiro permanente não restaura Vigor.

## Regra para implementação

Antes de implementar um sistema:

1. localizar a regra estrutural/mecânica na Fonte Mestra;
2. localizar o conteúdo correspondente na Fonte Regional vigente quando for regional;
3. localizar a apresentação correspondente na Fonte Visual/UI;
4. aplicar decisões adicionais explicitamente aprovadas e registradas neste documento;
5. não inventar comportamento para preencher lacunas;
6. registrar conflito real em vez de escolher silenciosamente uma interpretação;
7. preservar IDs estáveis, idempotência, estado autoritativo, transações e `ruleset_version` onde aplicável.

## Snapshot de implementação histórico — criação e primeiro combate

As seções de implementação abaixo foram preservadas como registro histórico e não substituem as Fontes oficiais vigentes nem o estado atual do repositório.

O fluxo implementado permanece:

`/start → nome → raça → classe → confirmação final → prólogo Cinzas na Estrada → Cão Cinéreo`

O primeiro encontro continua com:

- Cão Cinéreo Nv.1, Comum, Predador;
- 244 HP / 50 ATQ / 45 DEF / 56 AGI;
- tutorial Atacar/Defender/primeira Arte;
- 320 XP fixos;
- 0 Vigor consumido;
- sem Saque/Coroas/Materiais;
- suppress do bônus adicional de 1% de primeira observação nesta ocorrência.

A implementação histórica do combate foi instanciada sob `gdd-1.4.2-baseline-1.0`. Patches não devem reescrever silenciosamente combates ativos. Combates antigos devem continuar reprodutíveis no ruleset armazenado; novas instâncias/transições seguras devem adotar a Fonte Mestra vigente.

## Snapshot histórico — primeiro Braseiro e fim do Prólogo

Após a vitória do tutorial:

- o personagem chega ao **Braseiro da Estrada**, primeiro Braseiro permanente das Terras do Ocaso;
- ele já aparece como **Descoberto**; não existe `[Ativar Braseiro]` nesse passo;
- `[Descansar]` restaura HP a 100% e remove estados comuns de combate;
- Braseiro permanente não restaura Vigor;
- não existe segunda tela de “Braseiro ativado”;
- concluir esse passo encerra o Prólogo;
- registrar idempotentemente o Feito **Cinzas na Estrada** (sem cosmético);
- iniciar automaticamente a Missão Principal **P1 — Vozes na Estrada**;
- abrir diretamente o Menu Principal;
- no primeiro Menu, o personagem está em **Terras do Ocaso · Estrada das Cinzas**, Nv.1, com **320 / 4.800 XP**;
- por decisão aprovada do projeto, Vigor inicial é **100 / 100**.

A especificação focada histórica da implementação desse limite está em `docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md`. Ela permanece como registro do PR que implementou o bloco e não substitui as Fontes vigentes para conteúdo posterior.

## Snapshot histórico — P1 Vozes na Estrada

Neste snapshot histórico de P1, a Fonte Regional v1.0.13 e a Fonte Visual/UI de 2026-10-04 eram as referências vigentes naquele momento. O fluxo abaixo é uma nota de implementação preservada neste índice e não substitui as autoridades atuais definidas acima.

O fluxo autoritativo é:

`Menu pós-Prólogo → Seguir pela Estrada → Pegadas na Cinza → Sulcos Recentes → Cão Cinéreo roteirizado → Refúgio do Ocaso → Alda Veyr → Oren Cal → Braseiro do Refúgio → conclusão de P1`.

Regras essenciais para a próxima implementação:

- os dois sinais são fixos e persistentes;
- o encontro da Etapa 3 usa **Cão Cinéreo Nv.1, Comum, Solo, sem Variante**, fora do pool normal de Caçada;
- o combate usa HUD normal, sem máscara pedagógica;
- esse encontro concede `0 XP` de inimigo, `0 XP` adicional de primeira observação e nenhuma recompensa econômica própria;
- derrota retorna ao **Braseiro da Estrada**, mantém P1 na Etapa 3 e permite nova tentativa com novo encontro;
- reconnect de tentativa ainda ativa retoma o mesmo encontro;
- Refúgio, Alda, Oren e Braseiro do Refúgio são registrados na ordem definida pela Fonte Regional;
- `[Ativar Braseiro]` não equivale a `[Descansar]` e não restaura HP;
- concluir P1 concede uma única vez `2.400 XP`, `120 Coroas`, `1 Ferro de Fuligem` vinculado e `1 Couro Escoriado` vinculado;
- no mesmo commit de conclusão são liberados Caçada Manual e Desbravar na Estrada; Ronda continua dependente da primeira vitória manual válida posterior;
- no fluxo normal, o Menu pós-P1 fica em **Refúgio do Ocaso**, Nv.1, `2.720 / 4.800 XP`, sem reapresentar P1 como ativa;
- a UI separa detalhe oficial da Missão de telas contextuais e usa `[Ver Objetivo]` apenas como navegação sem mutação;
- callbacks antigos, reconnect e outro dispositivo sempre reconstroem a partir do estado persistido.

A implementação jogável de P1 foi integrada ao `main` no commit squash `bc45b2746e4cf5666134d39291fa32a6cdac524e` (PR #10). A especificação técnica de P1 permanece como registro histórico em `docs/specs/P1_VOZES_NA_ESTRADA_V1.4.3_TDO_V1.0.2.md`.

## Próximo bloco aprovado — snapshot histórico

O plano abaixo descreve uma etapa anterior do desenvolvimento e permanece apenas como snapshot histórico. Não deve ser usado para determinar o próximo bloco vigente de implementação.

O próximo bloco de produção parte do estado pós-P1 e implementa **Travessia Refúgio ↔ Estrada + Caçada Manual Solo + familiaridade da Ronda + Desbravar da Estrada**, sem iniciar ainda a execução automática da Ronda, Caçada em Grupo, P2/S1 ou outro Local.

A especificação técnica focada está em `docs/specs/ROAD_HUNT_EXPLORE_V1.4.3_TDO_V1.0.2.md`.

Para este bloco, esse documento também registra as decisões adicionais já aprovadas e ainda pendentes de consolidação textual nas Fontes: materialização global de Equipamento/Runa de Saque; identidade regional de Materiais; textos/registro de Desbravar; UI pós-combate/exploração; IA PvE normal; Ação Preparada; e pacotes Hemorrágico/Venenoso. Essas decisões são autoridade de implementação **somente no escopo explicitamente fechado pela especificação** e não autorizam reabrir balanceamento ou extrapolar para conteúdo não coberto.
