# Autoridade das Fontes

**Índice atualizado:** 2026-11-12.

> **Índice geral único:** `SOURCE_AUTHORITY.md` é o registro de governança que seleciona as versões autoritativas por escopo. Patches de sincronização são artefatos operacionais e não constituem uma segunda autoridade. Em conflito com índices/patches anteriores, este arquivo prevalece quanto à seleção de versões, sem alterar o conteúdo interno das Fontes.

> **Sincronização 2026-10-17:** este índice registra Fonte Mestra v1.6.0, Terras do Ocaso v1.0.17 FINAL (adotada em 2026-11-12), Vales dos Enforcados v1.0.6 FINAL, Planícies de Nareth v1.0.2 FINAL, Várzeas Carmesins v1.0.3 FINAL, Altos Cinéreos v1.0.1 FINAL, Lore v1.2, Visual/UI de 2026-10-13 e anatomia racial v2.0. Notas históricas mais abaixo podem citar versões anteriores apenas como registro; não reativam autoridade superada.

> **Sincronização 2026-10-18:** Confins do Véu v1.0.0 FINAL (`FINAL_APPROVED`, conteúdo regional C aprovado) está registrado na Região 6. O Contrato Global de Weapon Metadata v1.0.0 FINAL permanece íntegro e vigente, SHA-256 `c283b398949dc0a864d98b9e0e9031080a50b937db6932ffcde7d46e600aa740`. O GDD v1.6.0 permanece superior para sistemas globais; a Bíblia Canônica Consolidada v4.0.7 (`ASTERION_BIBLIA_CANONICA_v4_0_7.md`) rege Lore, identidades e limites; a Fonte Regional rege o conteúdo fechado da Região 6. **HANDOFF À ENGENHARIA AUTORIZADO** após esta sincronização; isto não declara P31 implementada.

> **Sincronização 2026-11-11:** a Bíblia Canônica Consolidada de Mundo, Raças, NPCs e Regiões **v4.0.7** (`ASTERION_BIBLIA_CANONICA_v4_0_7.md`, SHA-256 `011ad3fb0ab2f2e940baca5cbe11ee89460353ee9709693005dcc26c398a431d`) passa a reger Lore, identidades, NPCs e limites, por decisão do autor. Substitui a v3.0 FINAL e, por sucessão, a v3.2 e a v3.3. O arquivo v3.0 permanece no repositório só como registro histórico. Nenhuma regra mecânica muda; o GDD v1.6.0 segue superior para sistemas.

> **Sincronização 2026-11-12:** a especificação **Ação × Consequência Narrativa v1.0.0** (`docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md`) passa a reger a camada de escolha/memória das 72 Missões, por decisão do autor. Ela **sobrescreve explicitamente o GDD v1.6.0 §51.3/§55.1** quanto ao Coop: Principais e Secundárias são Solo em progresso, objetivos, escolhas e estado narrativo; só encontros de Chefe aceitam Grupo 1–4. Esta divergência deve entrar na próxima revisão do GDD. Nenhum número de jogo muda.

## Fonte Mestra vigente

A implementação do Asterion deve usar como autoridade principal:

**ASTERION — GDD Estrutural v1.6.0 — Fonte Mestra Consolidada**

Arquivo vigente: `ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md`.

Estado oficial:

- a v1.6.0 substitui integralmente a v1.5.0 e versões anteriores;
- a Baseline Numérica v1.0 está fechada para implementação e testes;
- a v1.4.9 formaliza o fechamento único de `HP Máximo`, `ATQ`, `DEF` e `AGI` estáticos finais em pontos inteiros com `round_half_up`, além de HP atual inteiro; não altera percentuais, curvas, custos, recompensas ou parâmetros de balanceamento;
- a reabertura anterior da conversão absoluta da unidade de XP de inimigo foi encerrada na v1.4.3;
- não existe reabertura numérica vigente na baseline;
- a v1.4.9 formaliza que HP Máximo, ATQ, DEF e AGI estáticos finais fecham uma única vez com `round_half_up` após toda a composição estática; HP atual autoritativo é inteiro e HP legado fracionário é fechado para baixo em fronteira segura;
- Cosméticos possui três categorias oficiais: Aparência, Título e Moldura.

## Contrato Global Complementar — Weapon Metadata

**ASTERION — Contrato Global de Weapon Metadata v1.0.0 FINAL**

Arquivo vigente: `ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md`.
SHA-256 verificado: `c283b398949dc0a864d98b9e0e9031080a50b937db6932ffcde7d46e600aa740`.

Este contrato global complementa o GDD Estrutural v1.6.0 e fecha, exclusivamente para armas player-equippable, `weapon_form` descritiva, `handedness`, elegibilidade de slot, tags explícitas de compatibilidade, mapeamento canônico das armas publicadas na tabela §9 e política de legado `EXACT_CANONICAL_MAPPING_OR_UNMAPPED`. `weapon_family` não é conceito canônico e não deve ser armazenado nem inferido.

O contrato não redefine economia regional nem conteúdo regional fora desse escopo, e não substitui nem rebaixa versões regionais vigentes. O GDD Estrutural v1.6.0 permanece a autoridade estrutural superior. Este contrato não é autoridade visual: assets e apresentação visual não determinam metadata mecânica.

A presença de entradas de Altos Cinéreos na tabela de metadata limita-se aos itens nela mapeados. Ela não registra nem substitui a Fonte Regional de Altos Cinéreos nem define seus gates; essa autoridade está registrada como Altos Cinéreos v1.0.1 FINAL na Região 5 abaixo.

A §19.2 de Confins do Véu v1.0.0 FINAL declara metadata explícita para as cinco armas regionais Grau VI usando os vocabulários de forma, handedness, slot e tags funcionais deste contrato. A compatibilidade foi conferida; `weapon_family` permanece não armazenado e não inferível. O conteúdo regional está registrado separadamente na Região 6.


## Camada narrativa — Ação × Consequência

**ASTERION — Sistema Narrativo de Ação × Consequência v1.0.0**

Arquivos: `docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md` (contrato) e `docs/specs/ASTERION_HANDOFF_CLAUDE_CODE_NARRATIVA_v1_0_0.md` (handoff).

- Rege os 72 nós de escolha (36 Principais + 36 Secundárias), as memórias de personagem e de NPC, o rapport qualitativo e os ganchos futuros. Contratos ficam fora.
- **Override do GDD v1.6.0 §51.3/§55.1 (decisão do autor, 2026-11-12):** Coop de Missão é exclusivo de Chefes (P5, P6, S6, P12, P18, S18, P24, S24, P30, P36, S30, S36). Objetivos comuns, Elites e encontros roteirizados são Solo. Não reativar Coop de Missão por inferência a partir do GDD.
- As Fontes Regionais continuam autoridade de missões, gates, recompensas e encontros. A camada narrativa não altera XP, Coroas, Materiais, Equipamentos, combate, economia nem `world_state`.
- O catálogo `src/asterion/domain/narrative_choices_catalog.json` é derivado do contrato por `scripts/build_narrative_choice_catalog.py`; não editar à mão.
- `rapport_state` fica `neutral` até o autor definir as transições. As falas de reação são conteúdo editorial pendente.

## Fontes regionais vigentes

As Fontes Regionais FINAL possuem o mesmo nível hierárquico entre si dentro de seus respectivos escopos. Todas permanecem subordinadas à Fonte Mestra v1.6.0 para sistemas globais e não podem sobrescrever conteúdo de outra Região.

### Região 1 — Terras do Ocaso · Nv.1–10

**ASTERION — Conteúdo: Terras do Ocaso v1.0.17 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.17_FINAL.md`.

> **Sincronização 2026-11-12:** o autor adotou a v1.0.17 no lugar da v1.0.16. A única mudança é a duração de `2T` da Barreira da **Égide do Selo** (mantém 8% do HP Máximo, CD4 e máximo 2 usos). O código já usava `2T` (`domain/road.py`, `egide_selo`); nenhum outro conteúdo ou valor regional muda.

A v1.0.16 substituiu integralmente a v1.0.15 como autoridade regional vigente. Preserva o conteúdo e os valores anteriores e fecha exclusivamente os pools temáticos de Material Básico do **Corvo de Fuligem**, **Alfa Cinéreo** e **Peregrino Calcinado**. Os pesos escolhem somente a identidade de cada unidade depois que chance e quantidade globais do contexto já foram resolvidas; não alteram Catalisadores, XP, Coroas, Equipamentos, Caçadas, Rondas, Desbravar ou qualquer outra regra econômica.

### Região 2 — Vales dos Enforcados · Nv.11–20

**Vales dos Enforcados v1.0.6 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.6_FINAL.md`.

A v1.0.6 sucede a v1.0.5 exclusivamente para fechar o perfil numérico do encontro roteirizado da Etapa 7 de S12 — Os Nomes Presos à Madeira. Não altera economia, progressão, narrativa regional, demais criaturas, pools, Caçada, Ronda, Masmorras ou recompensas regionais.

### Região 3 — Planícies de Nareth · Nv.21–30

**Planícies de Nareth v1.0.2 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_PLANICIES_DE_NARETH_v1.0.2_FINAL.md`.

A v1.0.2 sucede a v1.0.1 exclusivamente para fechar em 2T as durações das nove Barreiras inimigas publicadas. Preserva o mapeamento de Material Básico por criatura em Caçada/Ronda definido na v1.0.1 e todo o restante do conteúdo regional.

### Região 4 — Várzeas Carmesins · Nv.31–40

**Várzeas Carmesins v1.0.3 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.3_FINAL.md`.

A v1.0.3 sucede a v1.0.2 exclusivamente para esclarecer que sucesso ou falha/omissão na ação contextual dos Reservatórios Operacionais não altera a potência publicada de Transferência Externa (`165% ATQ`) nem cria consequências numéricas ou econômicas; cada Reservatório usado é consumido e não retorna, até o máximo publicado de três. Preserva todas as durações regionais de Barreira em `2T` e não cria default ou sistema universal. Todo o restante do conteúdo regional permanece inalterado. A Região cobre Nv.31–40 com saída para Nv.41 e define Locais, P19–P24, S19–S24, NPCs, Materiais Grau IV, criaturas, pools, economia, Crafting, Bestiário, Códice, Feitos e sistemas regionais, subordinados às regras globais da Fonte Mestra.

### Região 5 — Altos Cinéreos · Nv.41–50

**Altos Cinéreos v1.0.1 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_ALTOS_CINEREOS_v1.0.1_FINAL.md`.

A v1.0.1 FINAL harmoniza acesso persistente, navegação e atividades por Local. Escarpa exige P24 concluída + Nv.41 e registra acesso na etapa 1 de P25; Abrigo é descoberto na etapa 6 de P25. Pontes, Pedreiras e Bastilha abrem, respectivamente, pela ativação válida de P26 após P25 concluída + Nv.43, P27 após P26 concluída + Nv.45 e P28 após P27 concluída + Nv.47. Coração abre na etapa 7 de P29; Nv.50 continua exigido para iniciar P30. Caçada e Desbravar só são habilitados no Local correspondente após a conclusão de sua missão; Ronda exige também a primeira vitória manual válida posterior em Caçada no mesmo Local. S25 examina a ponte pelo lado da Escarpa sem antecipar acesso às Pontes. A revisão preserva os demais valores e conteúdos aprovados e não cria mecânica global.

Quando uma Fonte Regional especificar conteúdo dentro de parâmetros sistêmicos da Fonte Mestra, ambas devem ser aplicadas em conjunto. Em conflito estrutural ou numérico global, a Fonte Mestra prevalece; em conteúdo regional fechado dentro do próprio escopo, a revisão Regional vigente prevalece sobre rascunhos ou versões regionais anteriores.

### Região 6 — Confins do Véu · Nv.51–60

**Confins do Véu v1.0.0 FINAL — FINAL_APPROVED**

Arquivo vigente: `ASTERION_CONTEUDO_CONFINS_DO_VEU_v1.0.0_FINAL.md`.
SHA-256 integral verificado: `c86a0208888d14bbd653cda6174956df89b2233304dcca523d878b5b42a102fc`.

A aprovação de conteúdo regional C foi confirmada em 2026-10-18. Para sistemas, fórmulas e regras globais, prevalece o GDD Estrutural v1.6.0; para Lore, NPCs, identidades e limites, prevalece a Bíblia Canônica Consolidada v4.0.7 (substitui a v3.0 FINAL); esta Fonte define as decisões regionais C aprovadas, sem sobrepor aquelas autoridades. A §19.2 está sincronizada com o Contrato Global de Weapon Metadata v1.0.0 FINAL, registrado acima.

**Handoff à Engenharia:** autorizado após o registro desta Fonte FINAL e do Contrato Global de Weapon Metadata no índice. O handoff não significa que o conteúdo tenha sido implementado.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI v1.6.0 — sincronizada com Fonte Mestra v1.6.0 + Terras do Ocaso v1.0.15 + Vales dos Enforcados v1.0.6**

Arquivo vigente: `ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md`.

A Fonte Visual/UI permanece o arquivo sincronizado em 2026-10-13 com Fonte Mestra v1.6.0, TDO v1.0.15 e Vales v1.0.6. As revisões regionais **TDO v1.0.16** e **Nareth v1.0.2**, bem como as revisões mecânicas de **Várzeas v1.0.2** (durações de Barreira) e **v1.0.3** (estado contextual de encontro, sem novo contrato universal de UI), não criam novo componente universal nem alteram o contrato geral de navegação, layout ou nomenclatura sistêmica; por isso este mesmo documento Visual/UI continua vigente.

Ela define nomenclatura, texto, estrutura de telas, navegação, estados visuais e UX do Bot do Telegram. É subordinada à Fonte Mestra para regras mecânicas/números e à Fonte Regional para conteúdo regional oficial.

Exemplos de mockup não criam regra mecânica ou conteúdo canônico quando a autoridade correspondente já definir outro valor/estado.

## Fontes complementares de Lore e Direção Visual

As Fontes abaixo complementam as autoridades estrutural, regional e de Visual/UI. Elas não podem sobrescrever regra mecânica, conteúdo regional FINAL ou apresentação player-facing já fechada em autoridade superior.

### Lore canônica complementar

**Arquivo vigente:** `ASTERION_LORE_BIBLE_CANON_v1.2.md`

A v1.2 substitui a v1.1. Preserva a Lore consolidada e atualiza o fundamento fisiológico das cinco Raças para anatomia racial v2.0, mantendo nomes, mecânicas, compatibilidade biológica e núcleos narrativos. Quando um fato já estiver definido em Fonte Mestra ou Regional vigente, essas Fontes superiores prevalecem.

### Direção visual especializada — personagens humanoides

**Arquivo vigente:** `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`

A v2.0 substitui a v1.5 para toda produção/refação futura. Mantém Classes, Caminhos, NPCs e identidade individual, mas torna as cinco Raças imediatamente distinguíveis por anatomia/silhueta e atualiza as dez identidades canônicas das duas primeiras Regiões para a nova fisiologia.

### Direção visual especializada — Aparência Errante das Cinzas

**Arquivo vigente:** `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`

A v1.3 é a autoridade visual específica da Aparência regional **Errante das Cinzas**. Define identidade de coleção, variação de poses/olhares, famílias de armamento permitidas no escopo cosmético, materiais, fundos e QA do lote de 60 assets. Em seu escopo, prevalece sobre instruções genéricas da Matriz de Produção quando houver divergência, sem criar ou alterar mecânica, proficiência, inventário, Classe, Raça ou conteúdo regional.

### Direção visual especializada — criaturas e biomas

**Arquivo vigente:** `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`

Define ecologia visual, anatomia, silhueta, materiais, escala, habitats, Variantes, Elites, criaturas de Masmorra e Chefes. Nas Regiões 1–2, mecânica e conteúdo continuam pertencendo às Fontes Regionais FINAL.

A v1.1 substitui a v1.0 para produção futura e acrescenta o dossiê visual canônico do **Guardião do Último Rastro**, preservando ambiguidade de identidade/origem e diferenciação obrigatória de Peregrino Calcinado, Custódio Sem Rosto, Guardião das Lápides, O Sem-Nome e Vigia Partido.

### Direção visual especializada — ambientes

**Arquivo:** `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`

Define identidade ambiental, arquitetura, materiais, função histórica, Locais, hubs, clímax, Masmorras, progressão visual e limites de spoiler.

### Especificação técnica de geração

**Arquivo:** `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`

Define **como renderizar** o conteúdo já autorizado: canvas, proporção, pixel art, materiais, anatomia técnica, integridade de armas/focos, estados de pose, transparência, pós-processamento, nomenclatura e QA. Não cria Lore nem substitui as Bíblias especializadas.

### Controle operacional de produção

**Arquivo:** `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`

Documento de produção, não Fonte de cânone. A v2.0 substitui a v1.3 e refaz as 10 âncoras raciais para anatomia v2.0, mantendo as 60 combinações Raça × Classe, armas, poses e fundos como estrutura operacional. Qualquer linha que conflite com Fonte autoritativa deve ser corrigida na Matriz, nunca na Fonte superior.

### Padrão global de Aparências temáticas

**Arquivo vigente:** `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`

A v1.1 substitui a v1.0 e torna a anatomia racial v2.0 obrigatória em todas as Aparências temáticas.

### Direção visual especializada — Aparência Sobrevivente dos Vales

**Arquivo vigente:** `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`

A v1.1 substitui a v1.0 para incorporar anatomia racial v2.0 e referências documentais atualizadas; neste contêiner v2.0.1 também foi corrigido um carryover editorial indevido de exceções de armamento de `Errante das Cinzas`. `Sobrevivente dos Vales` segue as assinaturas globais de Classe; identidade regional e fundos permanecem.

### Guia operacional Raça × Classe

**Arquivo vigente:** `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`

A v1.3 substitui a v1.2 e exige que Classe e equipamento acomodem fisicamente chifres/orelhas/proporções raciais.

### Bundle Visual de recuperação

**Arquivo vigente:** `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md`

Espelho operacional dos documentos visuais vigentes para uso em Projeto ChatGPT. Não cria autoridade nova; em conflito prevalecem os documentos individuais acima.

### Contêiner visual do Projeto ChatGPT

**Arquivo vigente:** `ASTERION_CONSOLIDADO_RACAS_E_VISUAL_v2.0.2_PROJETO_FINAL.md`

Contêiner documental para economizar slots de Fontes do Projeto. Incorpora o índice de autoridade e as Fontes visuais especializadas, preservando a precedência interna de cada documento. Não cria mecânica, Lore ou conteúdo regional novo.

## Decisão visual vigente — legibilidade racial e anatomia v2.0

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

## Decisão visual aprovada em 06/10/2026 — arma-assinatura de Classe

Para as 60 Aparências padrão Raça × Classe, **toda skin deve exibir a arma-assinatura da Classe em leitura imediata**: Sentinela = arma de uma mão + escudo; Errante = duas armas curtas, preferencialmente uma em cada mão; Vigia = arco/besta; Tecelão = arma-foco de Trama; Oráculo = arma-foco simbólica/oracular; Luminar = cajado/bastão de combate-foco.

Estados `mãos livres`, Repouso ou Contemplação podem mudar a posição do armamento, mas não eliminar a assinatura. Tecelão, Oráculo e Luminar devem permanecer distinguíveis também pela linguagem formal de seus focos: técnico/Trama, simbólico/possibilidades e centrado/Luz, respectivamente.

As seis Classes da mesma Raça não podem reutilizar o mesmo traje-base como solução padrão. A diferenciação deve envolver arquitetura do torso, distribuição de equipamento, arma-assinatura e postura. Fundos monumentais genéricos repetidos — castelos, aquedutos, bandeiras e skylines épicos — devem ser rejeitados quando não vierem de fonte específica.

Esta decisão é **direção visual**, não regra mecânica de equipamento, proficiência, dano, inventário ou loadout.

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

As seções de implementação abaixo foram preservadas como registro operacional e não substituem as Fontes oficiais vigentes nem o snapshot mais recente de `REPASSE_TECNICO.md`.

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

A Fonte Regional v1.0.13 e a Fonte Visual/UI de 2026-10-04 eram as referências vigentes para P1 naquele momento. O fluxo abaixo é uma nota de implementação preservada como snapshot histórico e não substitui as autoridades atuais definidas acima.

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

O plano abaixo descreve uma etapa anterior do desenvolvimento. Use `REPASSE_TECNICO.md` para o estado de implementação e próximos passos registrados mais recentemente.

O próximo bloco de produção parte do estado pós-P1 e implementa **Travessia Refúgio ↔ Estrada + Caçada Manual Solo + familiaridade da Ronda + Desbravar da Estrada**, sem iniciar ainda a execução automática da Ronda, Caçada em Grupo, P2/S1 ou outro Local.

A especificação técnica focada está em `docs/specs/ROAD_HUNT_EXPLORE_V1.4.3_TDO_V1.0.2.md`.

Para este bloco, esse documento também registra as decisões adicionais já aprovadas e ainda pendentes de consolidação textual nas Fontes: materialização global de Equipamento/Runa de Saque; identidade regional de Materiais; textos/registro de Desbravar; UI pós-combate/exploração; IA PvE normal; Ação Preparada; e pacotes Hemorrágico/Venenoso. Essas decisões são autoridade de implementação **somente no escopo explicitamente fechado pela especificação** e não autorizam reabrir balanceamento ou extrapolar para conteúdo não coberto.

---

## Nota de escopo do pacote essencial

Este consolidado é suficiente como autoridade de **design, Lore, direção visual e produção de assets** quando usado com Fonte Mestra, Fontes Regionais e Visual/UI do pacote essencial. Referências históricas a `REPASSE_TECNICO.md` e referências de implementação a `docs/specs/OPTIONAL_SIDE_QUEST_BOSSES_V2.md` permanecem externas: elas não foram fornecidas neste conjunto e não são reconstruídas por inferência. Para tarefas estritamente de estado de código/implementação ou da regra técnica específica de Chefe opcional de S18, anexar a especificação correspondente.

---
