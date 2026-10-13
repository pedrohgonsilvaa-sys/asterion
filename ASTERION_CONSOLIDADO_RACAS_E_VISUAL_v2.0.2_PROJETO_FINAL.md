# ASTERION — CONSOLIDADO DE RAÇAS E DIREÇÃO VISUAL v2.0.2 — ARQUIVO ÚNICO PARA PROJETO

**Data de consolidação deste contêiner:** 2026-10-13  
**Revisão v2.0.2:** sincronização exclusiva do índice de autoridade com TDO v1.0.16, Nareth v1.0.1 e Várzeas v1.0.0; preserva integralmente o conteúdo visual v2.0.1 e não altera mecânica, Lore, anatomia, assets ou direção de arte.  
**Finalidade:** reunir em um único arquivo de Projeto as fontes enviadas para a migração racial/visual v2.0, reduzindo o número de vagas ocupadas nas Fontes do Projeto ChatGPT.  
**Natureza:** contêiner documental. Este arquivo não cria cânone novo, não altera mecânica e não muda a precedência interna das fontes incorporadas.

## Regra de uso deste consolidado

1. O bloco **PARTE A — Autoridade das Fontes** continua sendo o índice de precedência e autoridade.
2. Cada documento incorporado mantém seu nome, versão, escopo e autoridade originais.
3. O `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md` já contém integralmente as fontes visuais individuais listadas em seu próprio manifesto. Para evitar duplicação desnecessária, essas cópias individuais não são repetidas fora do Bundle neste contêiner.
4. Quando este consolidado for usado como arquivo único no Projeto, referências internas a nomes de arquivos incorporados devem ser resolvidas pela seção correspondente dentro deste próprio documento.
5. Referências históricas a versões superadas permanecem apenas como histórico quando o documento original assim as preserva; não reativam autoridade antiga.

## Manifesto dos 10 arquivos enviados cobertos por este consolidado

- `SOURCE_AUTHORITY.md`
- `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`
- `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md`
- `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`
- `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`
- `ASTERION_NOTA_MIGRACAO_RACAS_VISUAIS_v2.0.md`
- `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`

### Observação de deduplicação

Os seguintes arquivos enviados já estão incorporados **integralmente** dentro de `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md` e, por isso, aparecem uma única vez no conteúdo consolidado:

- `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`
- `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`
- `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`
- `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`

Além deles, o Bundle já preserva `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md` e `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`, conforme seu manifesto original.

---

# PARTE A — ÍNDICE DE AUTORIDADE VIGENTE
## Arquivo original: `SOURCE_AUTHORITY.md`
# Autoridade das Fontes

**Índice atualizado:** 2026-10-13.

> **Índice geral único:** `SOURCE_AUTHORITY.md` é o registro de governança que seleciona as versões autoritativas por escopo. Patches de sincronização são artefatos operacionais e não constituem uma segunda autoridade. Em conflito com índices/patches anteriores, este arquivo prevalece quanto à seleção de versões, sem alterar o conteúdo interno das Fontes.

> **Sincronização 2026-10-13:** este índice registra Fonte Mestra v1.6.0, Terras do Ocaso v1.0.16 FINAL, Vales dos Enforcados v1.0.6 FINAL, Planícies de Nareth v1.0.1 FINAL, Várzeas Carmesins v1.0.0 FINAL, Lore v1.2, Visual/UI de 2026-10-13 e anatomia racial v2.0. Notas históricas mais abaixo podem citar versões anteriores apenas como registro; não reativam autoridade superada.

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

## Fontes regionais vigentes

As Fontes Regionais FINAL possuem o mesmo nível hierárquico entre si dentro de seus respectivos escopos. Todas permanecem subordinadas à Fonte Mestra v1.6.0 para sistemas globais e não podem sobrescrever conteúdo de outra Região.

### Região 1 — Terras do Ocaso · Nv.1–10

**ASTERION — Conteúdo: Terras do Ocaso v1.0.16 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.16_FINAL.md`.

A v1.0.16 substitui integralmente a v1.0.15 como autoridade regional vigente. Preserva o conteúdo e os valores anteriores e fecha exclusivamente os pools temáticos de Material Básico do **Corvo de Fuligem**, **Alfa Cinéreo** e **Peregrino Calcinado**. Os pesos escolhem somente a identidade de cada unidade depois que chance e quantidade globais do contexto já foram resolvidas; não alteram Catalisadores, XP, Coroas, Equipamentos, Caçadas, Rondas, Desbravar ou qualquer outra regra econômica.

### Região 2 — Vales dos Enforcados · Nv.11–20

**Vales dos Enforcados v1.0.6 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.6_FINAL.md`.

A v1.0.6 sucede a v1.0.5 exclusivamente para fechar o perfil numérico do encontro roteirizado da Etapa 7 de S12 — Os Nomes Presos à Madeira. Não altera economia, progressão, narrativa regional, demais criaturas, pools, Caçada, Ronda, Masmorras ou recompensas regionais.

### Região 3 — Planícies de Nareth · Nv.21–30

**Planícies de Nareth v1.0.1 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_PLANICIES_DE_NARETH_v1.0.1_FINAL.md`.

A v1.0.1 sucede a v1.0.0 exclusivamente para fechar o mapeamento de Material Básico por criatura em Caçada/Ronda. Os pesos selecionam somente a identidade de cada unidade depois que chance e quantidade globais já foram resolvidas; não alteram pools de criaturas, XP, Coroas, Catalisadores, Fragmentos, Equipamentos, Runas, Desbravar, Masmorras, progressão ou narrativa.

### Região 4 — Várzeas Carmesins · Nv.31–40

**Várzeas Carmesins v1.0.0 FINAL**

Arquivo vigente: `ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.0_FINAL.md`.

Esta é a autoridade regional da quarta jornada, Nv.31–40 com saída para Nv.41. Fecha identidade regional, progressão, Locais, Braseiros, P19–P24, S19–S24, NPCs, Materiais Grau IV, mapeamento de Material por criatura, criaturas, Elites, Chefe opcional de S24, Caçada, Ronda, Desbravar, Masmorras, Matriz Rubra, Bestiário, Códice, Feitos, Cosméticos, Crafting Grau IV, Runas, Encantamentos, Consumíveis, Receitas especiais e auditoria regional de XP/Coroas/Materiais/gate Nv.41. Não cria novo sistema universal.

Quando uma Fonte Regional especificar conteúdo dentro de parâmetros sistêmicos da Fonte Mestra, ambas devem ser aplicadas em conjunto. Em conflito estrutural ou numérico global, a Fonte Mestra prevalece; em conteúdo regional fechado dentro do próprio escopo, a revisão Regional vigente prevalece sobre rascunhos ou versões regionais anteriores.

## Fonte Visual/UI

A apresentação player-facing deve seguir:

**ASTERION — Consolidação de Visual & UI v1.6.0 — sincronizada com Fonte Mestra v1.6.0 + Terras do Ocaso v1.0.15 + Vales dos Enforcados v1.0.6**

Arquivo vigente: `ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md`.

A Fonte Visual/UI permanece o arquivo sincronizado em 2026-10-13 com Fonte Mestra v1.6.0, TDO v1.0.15 e Vales v1.0.6. As revisões regionais **TDO v1.0.16** e **Nareth v1.0.1**, bem como a formalização de **Várzeas v1.0.0**, não criam novo componente universal de apresentação nem alteram contrato de navegação, layout ou nomenclatura sistêmica; por isso este mesmo documento Visual/UI continua vigente.

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

---

# PARTE B — NOTA DE MIGRAÇÃO RACIAL E VISUAL
## Arquivo original: `ASTERION_NOTA_MIGRACAO_RACAS_VISUAIS_v2.0.md`

# ASTERION — NOTA DE MIGRAÇÃO RACIAL E VISUAL v2.0

**Data:** 2026-10-12  
**Escopo:** migração das cinco Raças jogáveis para silhuetas/anatomias imediatamente distinguíveis, sem alterar nomes, Classes, Caminhos ou balanceamento racial.

## 1. Decisão

O padrão anterior diferenciava as Raças principalmente por pigmentação, cabelo, rosto e presença dentro de anatomia humana plausível. Esse modelo produzia baixa legibilidade em miniatura e fazia skins/NPCs parecerem variações humanas muito próximas.

A revisão v2.0 adota cinco famílias de silhueta:

| Raça | Leitura anatômica canônica |
|---|---|
| Remanescente | polo humano; maior diversidade; sem apêndice racial obrigatório |
| Velado | menor/esguio; orelhas largas laterais recuadas; olhos maiores; dedos longos |
| Cinéreo | compacto/denso; mãos grandes; mandíbula forte; caninos inferiores curtos |
| Hemário | humanoide funcional com exatamente um par de chifres de queratina |
| Alvorano | alto/alongado; orelhas longas pontiagudas para cima/trás; coordenação evidente |

As referências de fantasia popular usadas na fase de design são apenas vocabulário comparativo e **não existem na Lore**.

## 2. O que NÃO muda

- nomes das cinco Raças;
- passivas/efeitos raciais do GDD;
- Classes e Caminhos;
- armas-assinatura de Classe;
- progressão, economia, atributos ou balanceamento;
- conteúdo regional já fechado;
- Bestiário e ambientes;
- identidade temática de Errante das Cinzas e Sobrevivente dos Vales.

## 3. Fontes substituídas

Usar daqui em diante:

- `ASTERION_LORE_BIBLE_CANON_v1.2.md` no lugar de v1.1;
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` no lugar de v1.5;
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` no lugar de v1.0;
- `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md` no lugar de v1.0;
- `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md` no lugar de v1.2;
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` no lugar de v1.3;
- `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md` no lugar de v1.2.2;
- `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md` no lugar de v1.0;
- `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md` no lugar do bundle v1.0 quando o Projeto usar o bundle consolidado;
- `SOURCE_AUTHORITY.md` como índice de autoridade atualizado.

## 4. Assets que precisam ser refeitos/revisados

**Obrigatório revisar:**

- 10 imagens de seleção racial;
- 60 Aparências padrão Raça × Classe;
- 60 Errante das Cinzas;
- 60 Sobrevivente dos Vales;
- retratos/assets dos 10 NPCs persistentes das Terras do Ocaso e Vales;
- qualquer arte futura player-facing em que uma das cinco Raças apareça.

Cenas ambientais sem personagem, mapas, criaturas, Chefes não humanoides, ambientes e UI sem retrato racial não precisam ser refeitos por esta migração.

## 5. Ordem segura de refação

1. gerar as 10 novas âncoras raciais;
2. aprovar leitura sem nome/texto;
3. gerar um lote de calibração de 10–12 Raça × Classe cobrindo as cinco Raças;
4. fechar escala/câmera;
5. refazer as 60 Aparências padrão;
6. refazer NPCs;
7. refazer Errante das Cinzas e Sobrevivente dos Vales;
8. somente depois produzir novas Aparências regionais.

## 6. Regra de escala para skins

A escala de câmera continua padronizada. Raça alta não fica maior por zoom; Raça baixa não fica menor por afastamento de câmera. A diferença deve vir da proporção anatômica real.

- canvas: 1:1, 1024×1024;
- corpo inteiro;
- câmera média/neutra;
- figura temática preferencialmente 76–80% do canvas, faixa operacional 72–82%;
- comparar pés/solo e linha de câmera entre assets;
- Alvorano pode usar mais altura interna por anatomia, não por zoom;
- Velado preserva leitura menor sem ser miniaturizado artificialmente;
- Cinéreo ganha massa horizontal;
- chifres Hemários entram na área segura e nunca tocam bordas por acidente.

## 7. Critério de aprovação racial

Cobrir nome, ícone e fundo. Se o avaliador não distinguir as cinco Raças em miniatura apenas por corpo/cabeça/silhueta, o asset falha mesmo que roupa e Classe estejam corretas.

---

# PARTE C — BUNDLE VISUAL CONSOLIDADO
## Arquivo original: `ASTERION_BUNDLE_VISUAL_CHATGPT_v2.0.md`

# ASTERION — BUNDLE VISUAL PARA PROJETO CHATGPT v2.0

> **Sincronização no contêiner v2.0.1 (2026-10-13):** referências editoriais, anatomia racial nas Fontes Especializadas, armamento de Sobrevivente dos Vales e nomenclatura temática foram corrigidos no consolidado sem alterar mecânicas.

**Data de consolidação do bundle:** 2026-10-12  
**Finalidade:** consolidar as fontes visuais vigentes após a migração anatômica das cinco Raças.  
**Natureza:** espelho/consolidação operacional para recuperação e busca no Projeto ChatGPT. **Não é uma nova autoridade canônica e não substitui, no repositório, os documentos originais.**

## Regra de autoridade deste bundle

1. A autoridade formal continua pertencendo a `SOURCE_AUTHORITY.md` e às Fontes canônicas vigentes.
2. Cada documento incorporado abaixo preserva seu escopo e texto, já migrado para anatomia racial v2.0 quando aplicável.
3. Bestiário e Ambientes permanecem inalterados nesta revisão.
4. Referências históricas internas não reativam versões superadas.
5. Este bundle existe para ocupar uma única vaga nas fontes do Projeto ChatGPT.

## Documentos incorporados integralmente

- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`
- `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`
- `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`
- `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`
- `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`
- `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`
- `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`

---

# DOCUMENTO INCORPORADO 1/9
## Arquivo original: `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`
# ASTERION — BÍBLIA VISUAL DE PERSONAGENS, RAÇAS, CLASSES E NPCs v2.0

**Data de consolidação:** 2026-10-12  
**Escopo:** direção visual canônica para personagens humanoides, Raças, Classes, Caminhos, NPCs persistentes e figuras históricas  
**Uso principal:** geração/revisão de skins, retratos, imagens contextuais, Aparências e concept art em pixel art dark fantasy medieval  

**Revisão v1.4:** preserva integralmente a v1.3 e torna a **arma-assinatura da Classe** um eixo obrigatório de leitura nas Aparências padrão: Sentinela usa arma de uma mão + escudo; Errante prioriza duas lâminas curtas; Vigia mantém arco/besta; Tecelão usa arma-foco de Trama; Oráculo usa arma-foco oracular/simbólica; Luminar prioriza cajado/bastão de combate-foco. A mudança é visual/editorial e não cria proficiência, dano, inventário ou loadout mecânico.

**Revisão v1.5:** preserva integralmente a v1.4 e formaliza a **identidade visual individual canônica** dos dez NPCs persistentes das duas primeiras Regiões (cinco das Terras do Ocaso e cinco dos Vales dos Enforcados), incluindo Raça funcional, faixa etária, constituição, pigmentação, cabelo, olhos, marcas, paleta, objeto de assinatura e âncoras que devem permanecer reconhecíveis em futuras aparições. A distribuição destes NPCs não estabelece cota demográfica regional, não cria Classe para NPC e não implica parentesco, cultura ou profissão por Raça.

**Revisão v2.0:** substitui o modelo em que as cinco Raças permaneciam visualmente dentro de anatomia humana plausível indistinguível. Mantém nomes, mecânicas e núcleos narrativos, mas estabelece anatomia racial de leitura imediata: Remanescentes permanecem no polo humano; Velados tornam-se humanoides menores de orelhas largas laterais e olhos maiores; Cinéreos tornam-se compactos/densos com caninos inferiores curtos; Hemários passam a possuir par de chifres hereditários; Alvoranos tornam-se humanoides mais altos de orelhas longas pontiagudas. Atualiza NPCs, templates, checklists e QA para essa nova direção sem alterar mecânica de Raça ou Classe.

> Este documento não redefine números, Artes, regras de combate, progressão, economia ou conteúdo regional implementável. Em conflito, prevalecem `SOURCE_AUTHORITY.md`, Fonte Mestra, Fonte Regional vigente e Fonte Visual/UI conforme seu escopo.

---

# 1. OBJETIVO

Esta Bíblia existe para impedir que novas gerações visuais transformem identidades canônicas de Asterion em arquétipos genéricos de fantasia.

Ela deve responder, para qualquer personagem:

1. **O que precisa ser legível à primeira vista?**
2. **O que pode variar livremente?**
3. **Quais elementos são proibidos por contradizer a Lore?**
4. **Como Raça, Classe, Caminho e Região se combinam sem um apagar o outro?**
5. **Quais elementos pertencem à pessoa e quais pertencem apenas ao equipamento?**

A regra central é:

> **Raça define fisiologia; Classe define formação; Caminho define especialização; Região define adaptação material; indivíduo define identidade.**

Nenhuma dessas camadas deve substituir as outras.

## 1.1 Assinatura obrigatória de Classe em skins jogáveis

Para **Aparência padrão Raça × Classe**, a leitura de Classe não pode depender de um único objeto pequeno nem apenas do fundo. A skin deve possuir simultaneamente:

1. **silhueta de Classe**;
2. **arquitetura de vestuário/armadura própria da Classe**;
3. **arma-assinatura fisicamente visível e reconhecível**;
4. postura/gestual coerente;
5. quando aplicável, foco, ferramenta ou efeito extraordinário secundário.

### Arma-assinatura obrigatória

Toda Aparência padrão jogável deve mostrar a arma ou arma-foco que comunica a Classe em leitura rápida. Ela pode estar empunhada, baixa, apoiada, embainhada, presa ao corpo ou em suporte funcional, mas **não pode desaparecer da composição**.

A arma-assinatura é uma regra de direção visual. **Não cria restrição mecânica de equipamento, proficiência, dano, bônus, inventário ou loadout real.**

### Assinatura-base das seis Classes

| Classe | Assinatura visual prioritária |
|---|---|
| **Sentinela** | **arma de uma mão + escudo claramente visível**. O escudo é obrigatório nas Aparências padrão de identificação de Classe, ainda que Caminhos/arte narrativa possam variar. |
| **Errante** | **duas armas curtas e rápidas visíveis**, preferencialmente uma em cada mão quando a pose permitir: adagas, facas longas, espada curta + adaga ou duas lâminas curtas. |
| **Vigia** | **arco ou besta** como assinatura principal; faca/adaga de campo pode ser secundária. |
| **Tecelão** | **arma-foco de Trama** claramente extraordinária e técnica: lâmina-foco, bastão-foco, cetro técnico, agulha/fuso de Trama ou equivalente. Uma espada comum isolada não basta. |
| **Oráculo** | **arma-foco oracular/simbólica**: cajado/cetro oracular, bastão marcado ou lâmina simbólica ritual; pode combinar foco principal com lâmina curta secundária. |
| **Luminar** | **cajado ou bastão de combate-foco** como assinatura preferencial das Aparências padrão; espada/maça podem aparecer como secundárias ou em artes especiais, sem substituir a leitura luminosa de sustentação. |

### Diferença entre as três Classes extraordinárias

- **Tecelão:** implemento técnico; geometria funcional; tensão/linhas da Trama; nada sacerdotal.
- **Oráculo:** implemento simbólico e interpretativo; marcadores, placas, fios ou lâminas rituais; nada de tecnologia de Trama.
- **Luminar:** cajado/bastão robusto, limpo e centrado, preparado para sustentação/projeção; nenhum amuleto profético e nenhum símbolo religioso obrigatório.

### Regra para mãos livres e estados passivos

`Mãos livres`, `Repouso`, `Contemplação` ou `sem efeito ativo` alteram **o estado** da arma, não sua presença. Se a pose exigir mãos livres, a arma-assinatura deve permanecer guardada, apoiada ou presa ao corpo de modo legível. Para Tecelão, Oráculo e Luminar, o foco pode estar inativo, mas sua identidade formal deve continuar visível.

### Vestuário não intercambiável

As seis Classes da mesma Raça **não podem parecer o mesmo traje-base com um adereço trocado**. Compartilhar materiais e cultura racial é permitido; reciclar a mesma túnica, mesmo lenço dominante, mesmo casaco e mesma distribuição de couro/metal em várias Classes é motivo de reprovação.

Em leitura de miniatura, o tórax, a silhueta principal e a arma-assinatura devem mudar de Classe para Classe.

---

# 2. DIREÇÃO DE ARTE GLOBAL

## 2.1 Linguagem principal

- dark fantasy medieval;
- estética de fim da era 16-bit / início da era 32-bit;
- pixels deliberadamente visíveis;
- alto nível de acabamento sem pintura lisa moderna;
- melancolia, desgaste e materialidade;
- anatomia humanoide legível;
- silhuetas reconhecíveis;
- equipamento funcional antes de ornamental;
- fantasia contida: o extraordinário aparece como exceção significativa, não como excesso constante.

## 2.2 Para skins de personagem

Padrão recomendado:

- corpo inteiro;
- personagem centralizado no eixo geométrico e visual;
- cabeça, tórax e quadril próximos ao centro;
- margens equilibradas à esquerda e à direita;
- espaço seguro acima da cabeça e abaixo dos pés;
- pose capaz de comunicar Classe sem esconder anatomia;
- fundo simples ou contextual discreto, subordinado ao personagem;
- sem texto, HUD, moldura de interface ou números dentro da imagem.

## 2.3 Escala do extraordinário

Asterion não deve parecer high fantasy saturado de efeitos.

Mesmo personagens extraordinários devem manter:

- peso físico;
- tecido, couro, metal, madeira e pedra reconhecíveis;
- postura corporal funcional;
- sinais de fadiga, clima e uso;
- efeitos sobrenaturais localizados, com propósito.

Evitar permanentemente:

- auras ocupando metade da imagem sem necessidade;
- armaduras impossíveis de mover;
- armas maiores que o corpo sem função narrativa;
- dezenas de cristais luminosos decorativos;
- símbolos mágicos aleatórios;
- partículas genéricas apenas para “parecer fantasia”.

---

# 3. ANATOMIA HUMANOIDE RACIAL GLOBAL

As cinco Raças jogáveis continuam pertencendo a uma mesma família humanoide e permanecem biologicamente compatíveis, mas a direção visual v2.0 abandona a exigência de que todas permaneçam dentro de uma anatomia humana indistinguível.

Todas preservam o plano corporal humanoide fundamental:

- uma cabeça;
- dois braços;
- duas mãos com cinco dígitos;
- duas pernas;
- dois pés;
- postura bípede;
- rosto com dois olhos, nariz e boca;
- equipamento e arquitetura pensados para corpos humanoides.

A partir da v2.0, algumas linhagens possuem **estruturas raciais hereditárias maiores** — orelhas racialmente especializadas, chifres, dentição aumentada ou diferenças estáveis de proporção corporal. Esses elementos são fisiologia, não Cosmético, maldição, Classe ou efeito mágico.

A leitura racial oficial deve funcionar primeiro pela **silhueta anatômica**, depois por pigmentação, cabelo e acabamento. Roupa, fundo, ícone ou cor não podem ser a única forma de identificar a Raça.

As faixas de altura abaixo são **centros de produção visual**, não modificadores de atributo, hitbox, alcance, velocidade ou regra mecânica.

## 3.1 Descendência mista

Descendência entre Raças continua normal. Um indivíduo manifesta uma **linhagem funcional principal**, como já ocorre no sistema, e pode herdar traços familiares secundários de outras linhagens.

Para impedir ambiguidade visual e mecânica:

- estruturas diagnósticas maiores seguem prioritariamente a linhagem funcional principal;
- um Hemário funcional apresenta chifres hemários;
- um Alvorano funcional apresenta arquitetura auricular alvorana;
- um Velado funcional apresenta arquitetura auricular/ocular velada;
- um Cinéreo funcional apresenta a densidade esquelética e a dentição cinérea;
- um Remanescente funcional permanece sem apêndice racial obrigatório.

Traços familiares secundários podem aparecer em pigmentação, cabelo, formato de nariz, maçãs do rosto, largura corporal, estatura dentro da faixa individual, sardas, cicatrizes e outras características não diagnósticas.

Não criar categorias de “meio-Raça”, passiva híbrida, sangue puro ou hierarquia biológica.

## 3.2 Regra de legibilidade racial v2.0

Para produção player-facing considerar cinco eixos:

1. **silhueta/proporção**;
2. **estrutura racial diagnóstica** — quando existir;
3. **rosto**;
4. **pigmentação/cabelo**;
5. **presença corporal**.

Regras:

- **seleção de Raça:** a silhueta + pelo menos um marcador anatômico diagnóstico devem ser legíveis imediatamente nas quatro Raças não-remanescentes;
- **Remanescente:** a ausência deliberada de apêndice racial extraordinário, combinada com anatomia humana ampla e identidade individual forte, é parte da leitura;
- **Raça × Classe:** armadura, capuz, elmo e arma não podem esconder todos os marcadores anatômicos;
- **NPC canônico:** preservar a anatomia da Raça funcional em todas as aparições;
- **Aparência cosmética:** não remover chifres, remodelar orelhas, apagar dentição diagnóstica ou alterar proporções raciais sem Fonte específica de transformação.

Fenótipo continua não determinando caráter, moralidade, inteligência, profissão, cultura ou Classe.

# 4. REGRA DE LEITURA EM CAMADAS

Uma skin completa deve ser projetada nesta ordem:

### Camada 1 — Pessoa
Idade, rosto, corpo, postura, temperamento.

### Camada 2 — Raça
Família fenotípica, fisiologia e presença racial.

### Camada 3 — Classe
Treinamento, distribuição de peso, equipamento e linguagem de combate.

### Camada 4 — Caminho
Especialização mais específica da Classe.

### Camada 5 — Região
Materiais, reparos, clima, poeira, umidade e adaptações práticas.

### Camada 6 — Aparência/Cosmético
Personalização final, sem apagar as camadas anteriores quando a arte tiver função identificadora.

---

# 5. 🕯️ REMANESCENTES — DIREÇÃO VISUAL

## Natureza

Remanescentes são populações que atravessaram a Ruptura sem uma transformação profunda comum de natureza. Na revisão v2.0, ocupam deliberadamente o polo **mais próximo da anatomia humana comum** entre as cinco Raças, sem serem tratados como “Raça padrão”, pura ou superior.

## Anatomia diagnóstica

- anatomia humana sem chifres, orelhas racialmente alongadas, presas/tusks raciais ou alteração estrutural obrigatória;
- centro de altura muito amplo, aproximadamente 1,58–1,92 m em adultos, com exceções individuais plausíveis;
- maior liberdade de proporção corporal do elenco jogável;
- cinco dedos, pés humanos e dentição humana comum.

A ausência de um apêndice extraordinário **não significa ausência de identidade**. Remanescentes devem parecer pessoas específicas, nunca bonecos-base neutros.

## Centro fenotípico

Preservar a maior diversidade interna das cinco linhagens: pele clara a negra, grande variedade de subtons, cabelo liso a crespo, diferentes formatos faciais, corpos e idades. No material de seleção, usar contraste individual forte e acabamento de adaptação/reparo para evitar o “humano genérico”.

## Silhueta

É a Raça com maior liberdade: esguio a robusto, baixo a alto, jovem a idoso. A característica é **amplitude humana + adaptação**, não um corpo único.

## Rosto e corpo

- forte individualidade facial;
- nenhuma marca sobrenatural obrigatória;
- cicatrizes, assimetrias e sinais ambientais conforme história individual;
- não copiar um único centro étnico do mundo real como equivalente da Raça.

## Vestuário

Favorece peças acumuladas e reparadas: couro, tecido, metais reutilizados e equipamento mantido ao longo da vida. Isso é tendência visual, não definição cultural universal.

## Fundo de herança — seleção racial

Paisagem de sobrevivência reconstruída: via antiga reaproveitada, oficina, ponte ou habitação feita em camadas, sem transformar o fundo em miséria caricata ou Local específico de Mapa.

## Leitura desejada

> **Uma pessoa plenamente humana em anatomia, marcada não pela ausência de mudança, mas pela capacidade de continuar.**

## Evitar

- “humano genérico” sem identidade;
- pureza racial;
- uniforme obrigatório;
- acrescentar chifres, orelhas longas, presas/tusks ou pele fantástica apenas para “competir” com outras Raças.

# 6. 🌘 VELADOS — DIREÇÃO VISUAL

## Natureza

Velados são uma linhagem pós-Ruptura de sensibilidade velar estabilizada hereditariamente. A revisão v2.0 torna essa linhagem imediatamente reconhecível por **proporção menor, arquitetura auricular própria, olhos maiores e extremidades finas**, sem convertê-la em goblin, gnomo, elfo, morto-vivo ou ser do Avesso.

## Anatomia diagnóstica

Centro de produção visual:

- adultos geralmente entre aproximadamente **1,45–1,68 m**;
- corpo baixo a médio-baixo e esguio;
- braços e pernas relativamente longos para a altura, sem deformação caricata;
- cabeça discretamente maior em relação ao corpo do que em Remanescentes;
- **orelhas grandes, abertas para as laterais e varridas para trás**, com ponta arredondada ou angular suave — nunca a lâmina longa e ascendente dos Alvoranos;
- **olhos 10–15% maiores** que o centro humano, com íris muito legível e reflexo natural forte;
- mandíbula estreita, queixo menor, nariz curto a médio;
- mãos finas, dedos relativamente longos;
- dentição humanoide comum, sem presas raciais.

## Centro fenotípico

Pele pode percorrer profundidades humanas, mas a produção oficial favorece subtons frios/neutros. Cabelo liso ou levemente ondulado é frequente; preto, castanho-acinzentado, prata e branco continuam recorrentes. Olhos cinza, aço, azul acinzentado, verde dessaturado e castanho frio são comuns, sem glow.

Não usar pele verde como assinatura racial.

## Silhueta

Leitura: **pequeno, fino, atento, silencioso e ligeiramente fora da proporção humana esperada**. A estranheza vem do conjunto corpo baixo + orelhas largas + olhos maiores + extremidades precisas.

## Rosto

- olhos estáveis e muito atentos;
- orelhas sempre visíveis ou claramente acomodadas por capuz/elmo;
- contraste frio;
- expressão difícil de ler é possível, mas não obrigatória;
- nunca cadavérico.

## Corpo

- centro de gravidade leve e controlado;
- passos econômicos;
- musculatura possível, porém raramente volumosa;
- nada de pés peludos, proporções infantis ou comicidade automática.

## Vestuário

Capuzes, elmos e golas devem ser construídos para a orelha Velada: aberturas, recortes, dobras ou volume lateral plausível. Nunca esmagar ou apagar a anatomia para facilitar a geração.

## Fundo de herança — seleção racial

Vinheta liminar não sobrenatural: corredor/terraço antigo de pedra fria, umbrais e passagens sobrepostas, névoa fina e alinhamentos quase corretos. Não criar “reino Velado”.

## Efeitos visuais

Eco do Véu, quando autorizado, permanece mínimo e residual. Para seleção racial neutra, preferir nenhum efeito ativo.

## Leitura desejada

> **Um humanoide menor e silencioso, feito para perceber antes de ser percebido, sem parecer uma criatura feérica.**

## Evitar

- pele verde obrigatória;
- nariz cômico gigante;
- barba de gnomo como assinatura;
- pés desproporcionais/peludos;
- orelhas élficas longas e ascendentes;
- dentes de goblin;
- criança em corpo adulto;
- morto-vivo, fantasma ou ser do Avesso.

# 7. 🌪️ CINÉREOS — DIREÇÃO VISUAL

## Natureza

Cinéreos descendem de populações antigas moldadas por condições severas e consolidadas como linhagem moderna após a Ruptura. A revisão v2.0 torna essa adaptação visível por **densidade estrutural, torso compacto, mãos grandes e dentição inferior discretamente aumentada**. Não são anões, orcs, golems ou seres minerais, embora sua leitura use a força arquetípica de corpos compactos e mandíbulas poderosas.

## Anatomia diagnóstica

Centro de produção visual:

- adultos geralmente entre aproximadamente **1,55–1,80 m**;
- tronco profundo e largo;
- ombros e quadris com estrutura óssea evidente;
- pescoço curto a médio e forte;
- mãos e pés proporcionalmente grandes;
- sobrancelha, maçãs e mandíbula mais robustas;
- nariz frequentemente largo/estrutural;
- **caninos inferiores/tusks curtos e discretos**, visíveis em parte dos ângulos mesmo com boca relaxada, sem transformar o rosto em focinho;
- orelhas pequenas a médias, arredondadas ou levemente angulares;
- pele sempre orgânica e humana em textura, nunca pedra.

## Centro fenotípico

Pele em toda faixa humana, com produção oficial frequentemente bronzeada a profunda e subtons terrosos. Cabelo escuro, espesso, ondulado, cacheado, crespo ou muito denso continua recorrente. Barbas são comuns em vários gêneros conforme indivíduo/cultura, nunca obrigatórias.

## Silhueta

Leitura de **massa e sustentação**: corpo parece difícil de deslocar, não porque é gigantesco, mas porque é compacto e assentado. Mesmo um Cinéreo alto deve parecer denso.

## Rosto e corpo

- ossatura forte;
- mandíbula legível;
- caninos inferiores curtos, nunca presas vampíricas;
- mãos, antebraços e pernas podem comunicar trabalho físico;
- musculatura de fisiculturista não é necessária.

## Vestuário

Peças estruturadas, cintas, reforços, proteção contra abrasão e equipamento com pontos de carga claros. Armaduras precisam respeitar tórax e pescoço mais largos.

## Fundo de herança — seleção racial

Paisagem severa de sustentação: terreno rochoso, muros de contenção, blocos, contrapesos, pontes curtas e estruturas de carga. Não implica origem geográfica universal.

## Leitura desejada

> **Um humanoide compacto cuja anatomia parece feita para suportar carga e impacto.**

## Evitar

- pele verde como regra;
- orc clássico copiado;
- anão clássico copiado;
- presas gigantes;
- pele de pedra;
- fissuras de magma;
- cristais corporais;
- baixa estatura caricata obrigatória.

# 8. 🩸 HEMÁRIOS — DIREÇÃO VISUAL

## Natureza

Hemários são descendentes das alterações estáveis do Projeto Hemaris. A revisão v2.0 torna a linhagem imediatamente legível por **um par de chifres de queratina hereditários** combinado à assinatura vascular já existente. Não são demônios, tieflings, vampiros ou mortos-vivos; os chifres são fisiologia de Asterion.

## Anatomia diagnóstica

Centro de produção visual:

- adultos geralmente entre aproximadamente **1,62–1,92 m**;
- proporção humanoide atlética ou funcional, com grande variedade;
- **um par de chifres** nascendo da região temporal/parietal superior;
- chifres fisicamente integrados ao crânio, com base clara e peso plausível;
- famílias permitidas: curtos recuados, médios varridos para trás, curvos laterais controlados, assimetria por quebra/cicatriz;
- nunca galhadas ramificadas, coroas de chifre ou múltiplos pares por padrão;
- queratina em carvão, marrom escuro, osso envelhecido, cobre-marrom ou variação individual natural;
- sem cauda racial obrigatória, cascos, asas ou pele demoníaca;
- dentição humanoide; caninos podem ser discretamente marcados individualmente, mas nunca como assinatura vampírica.

## Centro fenotípico

Qualquer profundidade de pele é possível; subtons quentes, cobre, rubro ou avermelhado continuam recorrentes. Zonas de circulação vivas em lábios, orelhas, mãos e face; cabelo preto, castanho profundo, auburn e cobre escuro; olhos castanhos, âmbar, avelã ou verde-castanho.

## Silhueta

A primeira leitura racial vem do **par de chifres**, sem exigir pose agressiva. A segunda leitura é de vitalidade corporal e tensão física.

## Rosto e corpo

- aparência viva, nunca exangue;
- base dos chifres deve afetar cabelo e acessórios de forma plausível;
- penteados podem contornar, atravessar entre ou prender ao redor dos chifres sem fundi-los;
- capacetes e capuzes precisam possuir encaixe/abertura coerente.

## Fome Hemária

Preservar a regra anterior: tensão de mandíbula, respiração, foco e vascularização discretos quando ativa. Nunca transformação demoníaca, crescimento de chifres em combate ou sede visual automática por sangue.

## Vestuário

Funcional, móvel, com acesso para tratamento quando apropriado. Proteções de cabeça devem reconhecer a anatomia dos chifres.

## Fundo de herança — seleção racial

Vinheta histórica envelhecida de Hemaris: pátio clínico/logístico antigo, pedra funcional, metal oxidado, canais cobertos e suportes analógicos. Sem gore, laboratório sci-fi ou revelação futura.

## Leitura desejada

> **Um corpo intensamente vivo cuja linhagem carrega no próprio crânio a marca estável de uma transformação antiga.**

## Evitar

- diabo/demônio;
- tiefling copiado;
- cauda obrigatória;
- cascos;
- asas;
- pele vermelha obrigatória;
- presas vampíricas;
- chifres luminosos;
- sangue decorativo;
- coroa de chifres.

# 9. 🔆 ALVORANOS — DIREÇÃO VISUAL

## Natureza

Alvoranos são linhagem natural anterior à Ruptura, marcada por prontidão neuromuscular e homeostase responsiva. A revisão v2.0 torna essa linhagem reconhecível por **estatura mais alta, proporções alongadas controladas e orelhas longas pontiagudas de arquitetura própria**. Não são elfos de outra propriedade, seres solares, anjos ou povo sagrado.

## Anatomia diagnóstica

Centro de produção visual:

- adultos geralmente entre aproximadamente **1,72–2,02 m**;
- pernas e braços discretamente alongados;
- tórax e quadris proporcionais, sem magreza obrigatória;
- **orelhas longas, estreitas e pontiagudas**, orientadas para cima e para trás, claramente diferentes das orelhas largas/laterais dos Velados;
- comprimento auricular em torno de 1,3–1,6× o centro humano, sem exagero de high fantasy;
- olhos frequentemente amendoados;
- mãos proporcionais, coordenação corporal muito legível;
- sem asas, halo, pele metálica ou brilho corporal.

## Centro fenotípico

Pele pode existir em toda faixa humana; produção oficial pode favorecer oliva, dourado, bronze e castanhos quente-neutros sem limitar famílias. Cabelo liso/ondulado de queda controlada; preto, castanho, cobre e castanho-dourado recorrentes. Olhos avelã, âmbar, castanho-claro, verde-oliva e outras variações naturais sem glow.

## Silhueta

Leitura de **altura + prontidão + linhas longas**. Não é fragilidade: Alvoranos podem ser robustos, mas sua coordenação e alcance corporal permanecem evidentes.

## Rosto e corpo

- orelhas precisam permanecer legíveis ou ser acomodadas por capuz/elmo;
- maçãs marcadas e olhos amendoados são recorrentes, não universais;
- postura parece pronta para deslocamento;
- nenhuma serenidade, nobreza ou superioridade moral automática.

## Vestuário

Fechos rápidos, equipamento organizado e peças que não prendam movimento. Proteções de cabeça precisam respeitar o comprimento auricular.

## Fundo de herança — seleção racial

Vinheta civil anterior à Ruptura: terraço de rota, posto de coordenação, pátio de treinamento ou marcadores baixos sob luz clara. Amanhecer é atmosfera, não simbolismo divino.

## Leitura desejada

> **Um humanoide alto e coordenado que parece pronto um instante antes dos demais.**

## Evitar

- “elfo genérico” copiado;
- floresta feérica automática;
- halo;
- asas;
- pele dourada metálica;
- olhos solares brilhantes;
- nobreza racial automática;
- confundir orelha Alvorana com a orelha larga/lateral Velada.

# 10. RAÇA NÃO DEFINE CLASSE — FENÓTIPO DEVE SOBREVIVER AO EQUIPAMENTO

Nenhuma combinação recebe regra de Classe exclusiva por Raça.

Exemplos válidos:

- Velado Luminar;
- Hemário Guardião;
- Alvorano Tecelão;
- Cinéreo Errante;
- Remanescente Oráculo.

A imagem deve mostrar uma pessoa que pertence a uma Raça **e** aprendeu uma Classe, não uma fusão mística entre as duas.

Nas skins Raça × Classe:

- o equipamento pode dominar a leitura de função;
- a pose pode dominar a leitura de treinamento;
- **a anatomia diagnóstica da Raça nunca pode ser neutralizada pelo equipamento**;
- Hemários mantêm chifres legíveis; Alvoranos mantêm orelhas longas; Velados preservam o conjunto orelha larga + proporção menor/olhos maiores; Cinéreos preservam massa estrutural e dentição; Remanescentes preservam anatomia humana sem apêndice racial obrigatório;
- pelo menos dois marcadores raciais adicionais de rosto/pigmentação/cabelo/presença devem permanecer quando a composição permitir;
- elmos, capuzes e armaduras devem ser desenhados para a anatomia racial, não o contrário;
- o fundo deve combinar herança racial + função de Classe conforme a Matriz.

---
# 11. 🛡️ SENTINELA — LINGUAGEM VISUAL

## Núcleo

Resistência, posição e Retaliação.

## Silhueta

- base ampla;
- pernas firmes;
- proteção em tronco, braços e ombros;
- peso visual concentrado no centro;
- pose que parece capaz de absorver impacto e responder.

## Equipamento recomendado

- armadura média ou pesada;
- placas parciais, malha e couro reforçado;
- **arma de uma mão sempre visível**: espada, maça, martelo curto ou machado curto conforme a âncora;
- **escudo sempre visível nas Aparências padrão de identificação de Classe**; pode estar no braço, apoiado ou preso às costas conforme a pose;
- lança curta só quando puder coexistir com escudo sem comprometer a leitura/anatomia.

## Assinatura de vestuário

- blocos de proteção legíveis no torso/ombros/antebraços;
- cintura menos carregada que a do Errante;
- linhas de peso verticais e centrais;
- não usar lenço/manto como principal identificador;
- armadura deve ser a primeira leitura antes de acessórios.

## Gestual

- postura defensiva ativa;
- arma nunca completamente abandonada atrás do corpo;
- leitura de distância e base.

## Evitar

- cavaleiro sagrado/paladino; o escudo é assinatura visual de Classe, não símbolo religioso;
- paladino sagrado;
- tanque imóvel como estátua;
- berserker por padrão.

## 🏰 Bastião

Leitura: proteção espacial.

- armadura mais completa;
- placas sobrepostas;
- elementos largos de defesa;
- escudo reforça a identidade e permanece visível nas Aparências padrão;
- silhueta capaz de “ocupar espaço”.

Evitar castelo literal sobre armadura, muralha flutuante ou aura santa.

## 💥 Devastador

Leitura: contra-pressão calculada.

- armadura ainda funcional, mas menos fechada;
- arma mais ofensiva;
- marcas de impacto e reparos;
- postura avançada, pronta para usar exposição inimiga.

Evitar bárbaro irracional, raiva vermelha, músculos sem proteção ou fogo de fúria genérico.

---

# 12. 🗡️ ERRANTE — LINGUAGEM VISUAL

## Núcleo

Mobilidade, brechas e Oportunismo.

## Silhueta

- assimetria controlada;
- centro de gravidade móvel;
- pernas livres;
- torso protegido sem rigidez excessiva;
- equipamento rente ao corpo.

## Equipamento recomendado

- couro, tecido reforçado e placas pequenas;
- **duas armas curtas/rápidas visíveis** como assinatura preferencial: duas adagas, duas facas longas, duas lâminas curtas ou espada curta + adaga;
- quando a pose permitir, preferir **uma arma em cada mão**;
- em Repouso/Contemplação, uma ou ambas podem permanecer embainhadas, mas as duas devem ser legíveis;
- evitar espada longa/pesada como assinatura principal.

## Assinatura de vestuário

- casaco curto, sobreposição dividida ou painéis que liberem quadril e pernas;
- fechos laterais e equipamento rente ao corpo;
- pouca massa nos ombros;
- assimetria funcional;
- não reutilizar o mesmo peitoral/lenço do Sentinela, Tecelão ou Oráculo.

## Evitar

- ladrão encapuzado obrigatório;
- assassino ninja;
- criminoso visual por definição;
- excesso de bolsas decorativas sem função.

## ☠️ Carrasco

Leitura: conclusão decisiva.

- lâmina mais contundente ou perfil visual de finalização;
- linhas limpas e agressivas;
- menos elementos de sabotagem;
- postura focada em um alvo.

Evitar executor medieval com capuz de carrasco obrigatório, caveiras em excesso ou sadismo visual.

## 🕷️ Sabotador

Leitura: interferência progressiva.

- fios, ganchos, frascos e pequenas ferramentas podem aparecer quando coerentes;
- visual mais técnico e modular;
- bolsos funcionais;
- arma secundária facilmente acessível.

Evitar steampunk, alquimista puro, aranha literal, veneno verde fluorescente permanente.

---

# 13. 🏹 VIGIA — LINGUAGEM VISUAL

## Núcleo

Observação acumulada transformada em precisão.

## Silhueta

- postura alinhada;
- olhos e arma seguindo o mesmo eixo;
- equipamento de campo organizado;
- leitura de distância.

## Armas

Armas de disparo são a gramática visual prioritária da Classe e devem estar **sempre visíveis**:

- arco;
- besta;
- variantes tecnicamente plausíveis no mundo.

Quando a arma de disparo estiver nas costas, apoiada ou fora das mãos, uma faca de campo ou lâmina curta secundária pode permanecer visível na cintura para reforçar materialidade, sem substituir arco/besta como assinatura principal.

Não introduzir arma de fogo moderna.

## Vestuário

- proteção leve a média;
- capa curta ou manto controlável de leitura própria;
- proteção de antebraço claramente funcional;
- arnês de arco/besta;
- aljava ou sistema de munição legível quando aplicável;
- composição vertical limpa para não parecer Errante carregado de bolsas.

## 🎯 Atirador

Leitura: profundidade sobre um alvo.

- silhueta mais limpa;
- arma de maior precisão visual;
- menos equipamento pendente;
- pose estável e concentrada.

Evitar sniper moderno, mira telescópica industrial ou estética militar contemporânea.

## 👣 Rastreador

Leitura: consciência distribuída do campo.

- mais ferramentas de campo;
- cordas, pequenos marcadores, laços e utilidades;
- roupa adaptada para deslocamento prolongado;
- desgaste ambiental mais evidente.

Evitar ranger “da floresta” obrigatório: pode existir em qualquer Região.

---

# 14. 🪄 TECELÃO — LINGUAGEM VISUAL

## Núcleo

Manipulação técnica da Trama: **Perceber → Tensionar → Resolver**.

## Silhueta

- corpo em posição de controle, não de êxtase;
- mãos e braços podem participar da leitura da Trama;
- vestes permitem movimento preciso;
- efeitos visuais devem parecer tensões, linhas, dobras ou relações, não “mana líquida”.

## Equipamento

A Aparência padrão deve possuir **arma-foco de Trama claramente visível**. Famílias recomendadas:

- lâmina-foco;
- bastão-foco curto;
- cetro técnico de Trama;
- agulha/fuso de Trama de escala de combate;
- haste segmentada de tensão;
- braceletes/luvas técnicas como equipamento secundário.

A arma-foco deve parecer **mágica pela função**, não por excesso de brilho: encaixes, placas, tensores, geometria física, linhas localizadas de Trama ou reação material discreta. Uma espada comum embainhada, sozinha, **não classifica Tecelão**.

Quando a pose pedir mãos livres, a arma-foco fica em suporte dorsal, presilha ou bainha técnica, ainda claramente visível.

## Assinatura de vestuário

- casaco técnico ou sobreposição estruturada com mangas presas/ajustadas;
- braceletes/luvas claramente diferentes do equipamento de arqueiro;
- pequenos pontos de fixação, placas de medida e instrumentos físicos;
- painéis de trabalho assimétricos podem existir, sem virar avental de artesão genérico;
- evitar repetir túnica clara + lenço colorido como solução padrão.

## Efeito da Trama

Visual recomendado:

- linhas tensionadas;
- pequenas distorções de espaço local;
- fios de luz não homogêneos;
- pontos conectados por tensão;
- calor, geada ou impacto surgindo como consequência material.

Evitar:

- barra de mana visual;
- galáxias;
- constelações genéricas;
- portais para o Avesso;
- cajado clássico de mago; o Tecelão usa arma-foco técnica, não bastão sacerdotal/arcano genérico.

## 🌀 Conjurador

Leitura: liberação dirigida.

- efeitos mais abertos e ofensivos;
- tecido e cabelo respondendo à descarga;
- postura de resolução, não caos;
- sinais de calor/geada/ruptura material podem aparecer.

Evitar feiticeiro caótico ou “mago elemental” de escola clássica.

## 🔷 Rúnico

Leitura: estabilização temporária.

- inscrições geométricas funcionais;
- placas, fitas, pedras ou metais marcados;
- círculos podem existir, mas não precisam ser perfeitos;
- proteção deve parecer sustentada e construída.

Evitar runas nórdicas copiadas, alfabetos reais, círculos mágicos de anime ou hologramas digitais.

---

# 15. 🔮 ORÁCULO — LINGUAGEM VISUAL

## Núcleo

Leitura de possibilidades próximas.

## Silhueta

- atenção direcionada antes do movimento;
- postura menos explosiva que Alvorano;
- elementos visuais sugerem antecipação, não clarividência absoluta.

## Ferramentas possíveis

Podem existir culturalmente:

- placas marcadas;
- fios;
- ossos não humanos de uso simbólico;
- cartas ou lâminas simbólicas;
- sinos;
- objetos de observação.

Nenhum é universal e nenhum contém “o futuro”.

A Aparência padrão de Oráculo deve mostrar **arma-foco oracular/simbólica** claramente legível. Priorizar cajado/cetro oracular, bastão marcado ou lâmina simbólica ritual; uma lâmina curta secundária pode permanecer na cintura. O implemento deve comunicar leitura de possibilidades, não combate marcial puro.

Diferença do Tecelão: o Oráculo usa **marcadores, placas, fios, lâminas simbólicas e relações interpretativas**, não encaixes/tensores técnicos da Trama. Diferença do Luminar: o foco oracular pode ser mais esguio, assimétrico ou marcado; não deve parecer bastão robusto de sustentação.

## Assinatura de vestuário

- camadas de viagem com distribuição mais vertical que a do Errante;
- suporte próprio para placas, fios, lâminas simbólicas ou instrumentos;
- marcadores pequenos e repetidos, nunca ornamento excessivo;
- assimetria de leitura/observação, não de agilidade acrobática;
- não reciclar o mesmo lenço, túnica e braçadeiras do Tecelão.

## Efeitos visuais

- duplicação breve de gesto possível;
- linhas de trajetória incompletas;
- sombra sugerindo mais de uma ação;
- pequenos sinais convergentes.

Evitar:

- terceiro olho obrigatório;
- bola de cristal universal;
- estrelas e zodíaco genérico;
- relógios quebrados em toda arte;
- “ver o futuro” como tela holográfica.

## 🦉 Agoureiro

Leitura: aprofundamento de possibilidade desfavorável.

- olhar fixo no ponto de falha;
- efeitos discretamente convergentes sobre o alvo;
- roupa pode apresentar elementos de aviso, contraste ou marcas repetidas.

Evitar bruxa de maldição, necromante, fumaça negra moralizada.

## 🐺 Invocador

Leitura: alternância simbólica entre Lobo, Coruja e Urso.

As manifestações:

- são efeitos temporários;
- podem aparecer como contornos, gestos, sombras ou formas energéticas incompletas;
- nunca possuem corpo autônomo completo com postura de pet;
- não usam coleira, sela, HP visual ou iniciativa própria.

Lobo = pressão.  
Coruja = observação/limitação.  
Urso = sustentação/proteção.

Evitar druida, domador, xamã que convoca espíritos animais reais.

---

# 16. ☀️ LUMINAR — LINGUAGEM VISUAL

## Núcleo

Vitalidade exteriorizada como Luz.

## Silhueta

- postura firme e centrada;
- respiração e estabilidade corporal devem parecer parte da técnica;
- equipamento suporta presença e continuidade;
- a Luz emerge do praticante, não de uma entidade externa obrigatória.

## Luz

Pode assumir:

- luminosidade quente ou neutra;
- pressão luminosa;
- brilho concentrado;
- calor controlado;
- Barreira translúcida ou densa.

Não existe cor universal canônica.

## Equipamento

- armadura leve a pesada conforme indivíduo;
- **cajado ou bastão de combate-foco sempre visível** como assinatura prioritária das Aparências padrão;
- o cajado pode ser curto, médio ou longo, mas deve ser robusto, funcional e fisicamente utilizável;
- espada curta, maça ou escudo podem existir como secundários quando a âncora pedir, sem substituir o cajado como leitura principal;
- quando a Luz estiver ativa e as mãos precisarem ficar livres, o cajado permanece apoiado, preso ou em suporte de modo legível;
- nenhum símbolo religioso é obrigatório.

## Assinatura de vestuário

- composição mais centrada e contínua que a das outras Classes;
- proteção construída para permanência em campo, não para absorver impacto como Sentinela;
- frente do torso clara, fechos estáveis e braços livres para sustentação/projeção;
- pode usar peça frontal dividida ou casaco reforçado, sem linguagem sacerdotal;
- não usar branco, dourado ou símbolo sagrado como atalho de reconhecimento.

## Evitar

- paladino cristão genérico;
- cruzes por padrão;
- asas de anjo;
- halo;
- deus solar visível;
- moralidade expressa por pureza branca obrigatória.

## 🪬 Guardião

Leitura: sustentação ativa.

- silhueta protetora, porém não imóvel;
- Barreiras mais amplas e inclusivas;
- mãos, braços ou foco orientados para outra pessoa;
- equipamento preparado para permanecer funcional enquanto protege.

Evitar sacerdote pacifista obrigatório ou “healer de robe branco”.

## ⚖️ Inquisidor

Leitura: interrupção e consequência.

- linhas mais estreitas e agressivas;
- Luz concentrada em projeções ofensivas;
- postura de decisão, não fanatismo;
- balança pode existir como símbolo cultural, nunca obrigatória.

Evitar inquisidor católico histórico literal, caçador de bruxas obrigatório, cruzes, fogueiras religiosas ou aura de “verdade divina”.

---

# 17. DIFERENÇA VISUAL ENTRE AS CLASSES EXTRAORDINÁRIAS

## Tecelão

A realidade ao redor parece **tensionada**.

## Oráculo

A ação parece possuir **possibilidades concorrentes** antes de acontecer.

## Luminar

O corpo do praticante exterioriza **força vital luminosa**.

Nunca usar o mesmo efeito com três cores diferentes.

---

# 18. VESTUÁRIO CIVIL DE ASTERION

O mundo atual é fragmentado e regional.

A roupa civil deve parecer:

- reparável;
- reaproveitável;
- feita para clima real;
- produzida localmente;
- transmitida ou modificada ao longo do tempo.

Materiais recorrentes:

- lã;
- linho;
- couro;
- feltro;
- corda;
- madeira;
- ferro;
- bronze ou ligas locais quando coerentes;
- tecidos encerados;
- placas reaproveitadas.

Evitar moda renascentista luxuosa universal ou uniformes idênticos entre Regiões.

---

# 19. ADAPTAÇÃO REGIONAL DE PERSONAGENS

## 🌑 Terras do Ocaso

- cinza seca acumulada;
- tecido desbotado;
- couro ressecado;
- metal fosco;
- proteção de boca/olhos opcional;
- capas curtas contra poeira;
- remendos frequentes.

Leitura: **sobrevivência exposta**.

## 🪢 Vales dos Enforcados

- tecidos encerados;
- couro escurecido pela umidade;
- cordas e amarrações;
- botas altas;
- capas contra névoa e água;
- musgo ou resíduos vegetais apenas por uso, não decoração arbitrária.

Leitura: **umidade, raízes e passagem difícil**.

## 🌾 Planícies de Nareth

- roupa aerodinâmica para vento;
- capas laterais presas;
- proteção solar e contra poeira fina;
- marcadores de orientação;
- linhas horizontais e equipamento de viagem.

Leitura: **distância e orientação**.

## 🥀 Várzeas Carmesins

- tecido encerado;
- botas e polainas para água;
- luvas;
- máscaras ou filtros simples quando justificados;
- metal protegido contra ferrugem;
- manchas minerais e orgânicas contidas.

Leitura: **umidade biológica e cautela sanitária**.

## ⛰️ Altos Cinéreos

- camadas térmicas;
- couro espesso;
- lã;
- cintas estruturais;
- proteção de vento;
- metal escuro e muito reparado;
- botas de alta aderência.

Leitura: **peso, frio e vento severo**.

## 🌫️ Confins do Véu

- roupa prática de expedição;
- marcadores redundantes de posição;
- nós, fitas, placas ou inscrições pessoais para confirmar equipamento;
- proteção contra névoa;
- nada deve virar roupa “cósmica”.

Leitura: **a pessoa precisa confirmar que ainda está onde acredita estar**.

---

# 20. ARMAS E EQUIPAMENTOS — REGRA DE COERÊNCIA

Armas de Asterion devem parecer:

- utilizáveis;
- reparáveis;
- equilibradas;
- compatíveis com metalurgia e artesanato do mundo;
- personalizadas por uso, não por excesso ornamental.

Pode haver equipamento extraordinário, mas o extraordinário deve ser legível como tecnologia/Arte específica.

Evitar:

- firearms modernos;
- motores;
- neon;
- painéis digitais;
- cabos elétricos modernos;
- cristal como solução universal de design.

---

# 21. APARÊNCIAS COSMÉTICAS

**Aparência** é o termo player-facing oficial para o visual principal do personagem.

Uma Aparência pode alterar:

- vestuário;
- armadura aparente;
- acessórios;
- acabamento;
- tema regional;
- grau de desgaste;
- ornamentos.

Por padrão não deve alterar:

- Raça funcional;
- anatomia racial central;
- identidade narrativa de Classe quando a imagem é usada para comunicar Classe;
- gênero ou identidade do personagem sem escolha explícita do usuário;
- arma mecânica real quando isso produzir leitura enganosa em contexto onde a arma importa.

Cosmético não deve transformar personagem em criatura de outra categoria sem uma Aparência explicitamente concebida para isso.

---

# 22. NPCs — PRINCÍPIO GERAL

NPC persistente deve ser visualmente reconhecível sem depender de placa de nome.

## 22.1 Identidade individual persistente — regra v1.5

Quando um NPC persistente possuir bloco **Identidade canônica**, esse bloco passa a ser âncora obrigatória em retratos, telas contextuais, cenas futuras e novas Regiões. Mudanças de roupa, clima, idade futura, ferimentos ou situação narrativa podem alterar o acabamento, mas não devem trocar silenciosamente:

- Raça funcional;
- centro de leitura do rosto;
- pigmentação-base;
- família de cabelo;
- cor dos olhos;
- constituição-base;
- marcas físicas explicitamente fixadas;
- objeto/elemento de assinatura quando ele estiver presente naquela cena;
- postura comportamental central.

A função de um NPC **não cria Classe jogável**. Não inferir Sentinela, Errante, Vigia, Tecelão, Oráculo ou Luminar apenas por arma, ofício ou postura.

A Raça individual **não transforma profissão em traço racial**. A presença de um Cinéreo artesão, Velado pesquisador, Hemário líder, Alvorano herborista etc. não define regra cultural universal.

A escolha de Raça abaixo é uma decisão de identidade do personagem, não uma amostra estatística da população da Região.

Cada NPC precisa de:

- silhueta própria;
- 1–2 materiais recorrentes;
- uma ferramenta ou objeto funcional quando apropriado;
- postura coerente com função;
- paleta subordinada à Região;
- nenhum símbolo de cargo que a Lore não tenha estabelecido.

---

# 23. TERRAS DO OCASO — NPCs PERSISTENTES

## 🪖 Alda Veyr

**Função:** segurança, rotas e necessidades práticas do Refúgio.

### Identidade canônica — v1.5

- **Raça:** Hemária.
- **Apresentação:** feminina.
- **Faixa etária:** início dos 40.
- **Altura/constituição:** cerca de 1,72 m; atlética compacta, ombros firmes, sem fisiculturismo.
- **Anatomia racial v2.0:** par de chifres médios varridos para trás, base larga e queratina castanho-escura; penteado e proteção de cabeça sempre acomodam os chifres.
- **Pele:** castanho-média de subtom quente/cobre; circulação viva perceptível em lábios, orelhas e mãos sem efeito sobrenatural.
- **Rosto:** oval curto, maçãs discretamente fortes, nariz reto com leve desvio antigo.
- **Olhos:** castanho-âmbar escuros, atentos.
- **Cabelo:** castanho muito escuro com reflexo auburn; ondulado/cacheado, preso em trança baixa funcional.
- **Marca recorrente:** cicatriz curta e fina sob a maçã direita.
- **Paleta pessoal:** carvão, couro escuro, vinho queimado muito dessaturado, ferro envelhecido.
- **Objeto de assinatura:** pequeno marcador metálico de rota preso ao cinturão; pode coexistir com arma simples de patrulha.
- **Postura:** sempre parece medir passagem, distância e risco antes de falar.
- **Âncoras imutáveis:** par de chifres médios recuados, trança baixa, olhos âmbar escuros, cicatriz curta na face direita, presença prática e não cerimonial.

### Direção visual

- mulher adulta de presença funcional e pouco cerimonial;
- porte firme, não necessariamente muito musculoso;
- armadura parcial ou casaco reforçado de patrulha;
- botas e luvas usadas;
- capa curta ou manto contra cinza;
- arma simples e confiável;
- cabelo preso ou controlado por necessidade prática.

### Leitura

> **A pessoa que mantém a passagem funcionando porque alguém precisa fazê-lo.**

### Evitar

- coroa;
- insígnia de prefeita/governadora;
- armadura real;
- comandante militar de exército formal.

---

## ✒️ Oren Cal

**Função:** escriba, preservação de relatos, nomes e inscrições.

### Identidade canônica — v1.5

- **Raça:** Remanescente.
- **Apresentação:** masculina.
- **Faixa etária:** fim dos 30.
- **Altura/constituição:** cerca de 1,79 m; esguio, ombros levemente fechados pelo hábito de leitura/escrita.
- **Pele:** castanho-escura de subtom neutro.
- **Rosto:** alongado, testa alta, expressão cansada e concentrada.
- **Olhos:** avelã escuro/castanho-esverdeado, sem brilho sobrenatural.
- **Cabelo:** preto, crespo curto, com início discreto de grisalho nas têmporas.
- **Barba:** curta e irregular, normalmente aparada por praticidade.
- **Marca recorrente:** dedos e unha do polegar frequentemente manchados de carvão/pigmento.
- **Paleta pessoal:** cinza de fuligem, marrom seco, bege gasto, preto de tinta.
- **Objeto de assinatura:** estojo rígido de carvão e pequena prancha de escrita/cópia protegida.
- **Postura:** inclina-se para inscrições, observa antes de tocar, fala com cautela intelectual.
- **Âncoras imutáveis:** pele castanho-escura, cabelo crespo curto, olhos avelã escuros, estojo de carvão, aparência atenta e cansada.

### Direção visual

- adulto de aparência atenta e cansada;
- roupa prática protegendo cadernos e instrumentos;
- estojo de carvão, pena, raspador, pequenos papéis ou placas;
- dedos com manchas de pigmento;
- proteção contra fuligem sem parecer sacerdote.

### Postura

- observa antes de tocar;
- frequentemente inclinado sobre inscrição ou registro;
- expressão de cautela intelectual.

### Evitar

- mago de biblioteca;
- vidente;
- arqueólogo moderno;
- óculos modernos obrigatórios;
- traje acadêmico contemporâneo.

---

## 🛠️ Torren Vhal

**Função:** introdução a Ferreiro, Crafting, Desmontagem e Aprimoramento.

### Identidade canônica — v1.5

- **Raça:** Cinéreo.
- **Apresentação:** masculina.
- **Faixa etária:** fim dos 40.
- **Altura/constituição:** cerca de 1,66 m; baixo-médio, muito denso, tronco e antebraços fortes por ofício.
- **Anatomia racial v2.0:** mãos grandes, pescoço forte e caninos inferiores curtos visíveis em ângulo frontal/3⁄4; pele totalmente orgânica.
- **Pele:** castanho-escura de subtom terroso/quente.
- **Rosto:** quadrado, mandíbula forte, nariz largo, linhas de expressão profundas.
- **Olhos:** castanho muito escuro.
- **Cabelo:** preto muito escuro, espesso e crespo, cortado curto; grisalho concentrado nas laterais.
- **Barba:** curta, salpicada de cinza.
- **Marca recorrente:** queimadura de trabalho antiga no antebraço esquerdo, sem gore.
- **Paleta pessoal:** ferro escurecido, couro marrom, fuligem, tecido cinza-ocre.
- **Objeto de assinatura:** martelo de ofício de cabeça compacta e uma pequena ferramenta de medição.
- **Postura:** peso bem assentado, movimentos econômicos e seguros de quem trabalha com impacto e calor.
- **Âncoras imutáveis:** corpo denso, caninos inferiores curtos, cabelo curto crespo com grisalho lateral, queimadura antiga no antebraço esquerdo, martelo de ofício.

### Direção visual

- artesão robusto ou densamente construído;
- avental pesado;
- mangas presas;
- queimaduras pequenas e cicatrizes de trabalho;
- martelo, tenaz ou ferramenta de medição;
- metal e fuligem reais, sem estética industrial moderna.

### Evitar

- anão obrigatório;
- ferreiro mágico cercado de lava;
- armadura completa trabalhando na forja.

---

## 🌿 Sila Renn

**Função:** contextualização de Alquimista, Cura, Purificação e Antídoto.

### Identidade canônica — v1.5

- **Raça:** Velada.
- **Apresentação:** feminina.
- **Faixa etária:** meados dos 30.
- **Altura/constituição:** cerca de 1,58 m; baixa e longilínea, mãos finas e dedos relativamente longos.
- **Anatomia racial v2.0:** orelhas grandes varridas lateralmente para trás, ponta suave; olhos discretamente maiores que o centro humano e muito reflexivos, sem glow.
- **Pele:** oliva muito clara de subtom frio/neutro, humana e saudável, nunca cadavérica.
- **Rosto:** oval alongado, mandíbula estreita, simetria alta.
- **Olhos:** verde-cinza dessaturado.
- **Cabelo:** castanho-acinzentado muito escuro, liso, preso em coque baixo; uma mecha frontal naturalmente prateada é recorrente.
- **Marca recorrente:** pequena cicatriz química clara no dorso da mão direita.
- **Paleta pessoal:** cinza frio, couro marrom escuro, verde de erva seca, cerâmica negra.
- **Objeto de assinatura:** estojo acolchoado de frascos cerâmicos e pequena lâmina de corte/preparo.
- **Postura:** avalia quantidade e condição com calma clínica, sem teatralidade mágica.
- **Âncoras imutáveis:** orelhas largas recuadas, olhos ligeiramente maiores verde-cinza, pele oliva muito clara fria, mecha prateada frontal, coque baixo, cicatriz no dorso da mão direita.

### Direção visual

- roupas em camadas leves e práticas;
- bolsas de reagentes;
- luvas ou proteção de dedos;
- recipientes cerâmicos/vidro grosso compatível com o mundo;
- ervas secas protegidas da cinza;
- postura de quem avalia quantidade e condição, não de feiticeira.

### Evitar

- bruxa de caldeirão;
- poções neon;
- laboratório moderno;
- médico contemporâneo.

---

## ⚔️ Vael Orin

**Função:** ponto narrativo das Provações de Classe no Círculo da Cinza.

### Identidade canônica — v1.5

- **Raça:** Alvorano.
- **Apresentação:** masculina.
- **Faixa etária:** meados/fim dos 50.
- **Altura/constituição:** cerca de 1,88 m; magro-atlético, musculatura funcional e mobilidade preservada.
- **Anatomia racial v2.0:** orelhas longas e pontiagudas orientadas para cima/trás; membros discretamente alongados e proporção corporal alta.
- **Pele:** bronzeada de subtom quente-neutro.
- **Rosto:** maçãs marcadas, nariz quebrado e consolidado no passado, sobrancelhas claras na expressão.
- **Olhos:** âmbar-avelã.
- **Cabelo:** castanho-escuro ondulado, curto e controlado, com grisalho cobre/cinza nas têmporas.
- **Barba:** por fazer curta ou barba muito baixa, também grisalha.
- **Marca recorrente:** cicatriz antiga atravessando a sobrancelha esquerda.
- **Paleta pessoal:** couro castanho, pano cinza quente, bronze envelhecido, preto fosco.
- **Objeto de assinatura:** bastão simples de prova/treinamento e fichas de treino presas ao cinto.
- **Postura:** corpo parece pronto um instante antes de agir; observa pés, mãos e distribuição de peso do oponente.
- **Âncoras imutáveis:** orelhas longas pontiagudas, altura corporal elevada, nariz consolidado, cicatriz na sobrancelha esquerda, olhos âmbar-avelã, grisalho nas têmporas, bastão simples de prova.

### Direção visual

- veterano capaz de ser reconhecido por qualquer Classe sem parecer mestre exclusivo de uma delas;
- equipamento de treinamento misto e neutro;
- arma simples ou bastão de prova opcional;
- cicatrizes e manutenção cuidadosa;
- postura de observador de combate;
- presença severa, porém não teatral.

### Leitura

> **Ele não ensina uma Classe do zero. Ele sabe reconhecer quando alguém domina os próprios fundamentos.**

### Evitar

- arquimago;
- grande mestre de artes marciais oriental genérico;
- sacerdote;
- entidade sobrenatural.

---

# 24. VALES DOS ENFORCADOS — NPCs PERSISTENTES

## 🪖 Dara Venn

**Função:** segurança, rotas e sobrevivência da Vigília.

### Identidade canônica — v1.5

- **Raça:** Remanescente.
- **Apresentação:** feminina.
- **Faixa etária:** fim dos 30/início dos 40.
- **Altura/constituição:** cerca de 1,76 m; atlética de campo, pernas fortes e ombros funcionais.
- **Pele:** castanho-escura de subtom neutro-quente.
- **Rosto:** amplo e expressivo, nariz médio, mandíbula firme.
- **Olhos:** castanho-escuros.
- **Cabelo:** preto, crespo, em tranças médias presas para trás e acima da gola.
- **Marca recorrente:** pequena cicatriz vertical no centro do queixo.
- **Paleta pessoal:** couro quase preto, verde-musgo dessaturado, tecido encerado cinza-marrom, metal oxidado.
- **Objeto de assinatura:** corda de passagem com nós de referência claramente utilitários presa ao cinturão.
- **Arma visual recorrente:** lança curta ou arma de campo simples, sem converter Dara em Classe jogável específica.
- **Postura:** atenção distribuída ao terreno; corpo orientado para proteger rota e passagem, não para pose heroica.
- **Âncoras imutáveis:** tranças presas, cicatriz no queixo, pele castanho-escura, corda de passagem com nós de referência.

### Direção visual

- adulta pragmática;
- roupa de patrulha adaptada à umidade;
- couro escuro, tecido encerado, botas altas;
- corda e ferramenta de passagem;
- arma de campo confiável;
- pouca ornamentação.

### Evitar

- “rainha da floresta”;
- druida;
- armadura coberta de folhas decorativas.

---

## ✒️ Iven Raal

**Função:** registrador e investigador das estruturas antigas.

### Identidade canônica — v1.5

- **Raça:** Hemário.
- **Apresentação:** masculina.
- **Faixa etária:** início dos 30.
- **Altura/constituição:** cerca de 1,75 m; esguio, resistente a caminhada, mãos de trabalho fino.
- **Anatomia racial v2.0:** chifres curtos a médios recuados, assimétricos apenas por desgaste natural; queratina carvão/cobre-escura.
- **Pele:** castanho-média com subtom quente/rubro discreto e circulação viva.
- **Rosto:** estreito, maçãs altas, olheiras de trabalho e viagem.
- **Olhos:** avelã com reflexo âmbar natural.
- **Cabelo:** castanho-escuro com reflexos auburn, cacheado curto/médio, frequentemente úmido ou preso parcialmente.
- **Barba:** curta e irregular, castanho-avermelhada.
- **Marca recorrente:** pequena falha na sobrancelha direita por cicatriz antiga.
- **Paleta pessoal:** marrom encerado, cinza úmido, ferrugem escura, vermelho-cobre muito contido.
- **Objeto de assinatura:** estojo impermeabilizado de cadernos e fio de medição com pequenos pesos de metal.
- **Postura:** pesquisador de campo; frequentemente compara medidas, pedra e anotação, nunca “mago estudioso”.
- **Âncoras imutáveis:** par de chifres recuados, cabelo cacheado auburn escuro, olhos avelã-âmbar, falha na sobrancelha direita, fio de medição com pesos.

### Direção visual

- roupa de viagem mais organizada que a de Oren;
- cadernos protegidos contra umidade;
- placas de cópia, fios de medição ou carvão;
- capa curta impermeabilizada;
- mãos frequentemente sujas de barro e pedra apesar do perfil intelectual.

### Leitura

> **Um pesquisador que precisa atravessar o lugar que estuda.**

---

## 🛠️ Mira Sel

**Função:** artesã da Vigília.

### Identidade canônica — v1.5

- **Raça:** Alvorana.
- **Apresentação:** feminina.
- **Faixa etária:** início/meados dos 40.
- **Altura/constituição:** cerca de 1,79 m; coordenada e firme, braços fortes sem volume exagerado.
- **Anatomia racial v2.0:** orelhas longas pontiagudas orientadas para cima/trás; linhas corporais altas e prontidão de movimento.
- **Pele:** castanho-clara/bronze de subtom quente-neutro.
- **Rosto:** maçãs marcadas, olhos amendoados, expressão de avaliação rápida.
- **Olhos:** castanho-claro/âmbar.
- **Cabelo:** preto a castanho muito escuro, ondulado de queda controlada, preso em coque alto curto ou rabo compacto durante o trabalho.
- **Marca recorrente:** pequena cicatriz de corte no polegar esquerdo e resina seca frequente nas luvas/ferramentas.
- **Paleta pessoal:** marrom de madeira molhada, bege encerado, ferro escuro, âmbar de resina muito discreto.
- **Objeto de assinatura:** raspador de resina e calibre/medidor dobrável de oficina.
- **Postura:** sempre parece já ter calculado o próximo encaixe ou reparo antes de mover a ferramenta.
- **Âncoras imutáveis:** orelhas longas pontiagudas, olhos âmbar, cabelo escuro preso alto, ferramentas compactas de medição, resina seca nas luvas.

### Direção visual

- equipamento de oficina adaptado a madeira úmida, metal e resina;
- avental curto ou cintas de ferramenta;
- proteção de mãos;
- resina seca nas ferramentas;
- postura confiante de ofício.

### Evitar

- inventora steampunk;
- ferramentas elétricas;
- goggles industriais.

---

## 🌿 Saera Nol

**Função:** herborista/alquimista dos Vales.

### Identidade canônica — v1.5

- **Raça:** Cinérea.
- **Apresentação:** feminina.
- **Faixa etária:** fim dos 20/início dos 30.
- **Altura/constituição:** cerca de 1,61 m; corpo firme e compacto de campo, mãos proporcionalmente grandes para coleta e preparo.
- **Anatomia racial v2.0:** mandíbula/maçãs fortes, pescoço firme e caninos inferiores curtos; pele sempre orgânica.
- **Pele:** castanho-escura de subtom terroso/quente.
- **Rosto:** maçãs fortes, sobrancelhas espessas, nariz curto-largo, expressão observadora.
- **Olhos:** castanho profundo.
- **Cabelo:** preto, muito denso e crespo, usado em torções/tranças curtas recolhidas sob faixa impermeável.
- **Marca recorrente:** dois pequenos sinais de cicatriz no antebraço direito por coleta de campo.
- **Paleta pessoal:** verde-pântano dessaturado, marrom de turfa, tecido encerado cinza, couro escuro.
- **Objeto de assinatura:** estojo dividido de coleta + pequena lâmina curva de colheita.
- **Postura:** baixa o centro de gravidade para examinar solo, planta e fungo; abordagem prática, não druídica.
- **Âncoras imutáveis:** corpo compacto, caninos inferiores curtos, cabelo denso recolhido sob faixa, pele castanho-escura terrosa, estojo dividido, lâmina de coleta, duas cicatrizes pequenas no antebraço direito.

### Direção visual

- roupas resistentes à água;
- cestos, estojos ou bolsas ventiladas;
- pequenas lâminas de coleta;
- ervas de turfa, fungos e resinas acondicionados separadamente;
- aparência de campo, não de salão alquímico.

### Evitar

- druida floral;
- bruxa da floresta;
- coroas de flores.

---

## 🧭 Edras Vhal

**Função:** referência local para troca de Caminho.

### Identidade canônica — v1.5

- **Raça:** Velado.
- **Apresentação:** masculina.
- **Faixa etária:** início dos 60.
- **Altura/constituição:** cerca de 1,63 m; baixo, longilíneo, seco, ainda funcional, postura controlada.
- **Anatomia racial v2.0:** orelhas largas e recuadas, olhos cinza-aço um pouco maiores que o centro humano, dedos longos e precisos.
- **Pele:** clara fria a oliva muito clara, humana e saudável.
- **Rosto:** alongado, mandíbula estreita, rugas finas de concentração, expressão difícil de ler.
- **Olhos:** cinza-aço.
- **Cabelo:** cinza-prata predominantemente, liso/levemente ondulado, preso atrás ou cortado até a nuca.
- **Barba:** curta, cinza escuro/prata.
- **Marca recorrente:** cicatriz fina horizontal no dorso do nariz.
- **Paleta pessoal:** cinza frio, couro escuro, azul-cinza muito dessaturado, bronze envelhecido mínimo.
- **Objeto de assinatura:** conjunto modular de fichas/marcadores de treino e pequeno mapa dobrado protegido da umidade.
- **Postura:** economia de movimento; demonstra alternativas sem performar uma única escola de combate.
- **Âncoras imutáveis:** orelhas largas recuadas, olhos cinza-aço ligeiramente maiores, cabelo prata, cicatriz no dorso do nariz, corpo baixo-longilíneo, fichas de treino modulares.
- **Nota de cânone:** o sobrenome Vhal compartilhado com Torren Vhal **não estabelece parentesco** nesta revisão; nenhuma relação familiar entre ambos deve ser inferida sem Fonte futura.

### Direção visual

- viajante veterano;
- equipamento modular;
- sinais de ter usado mais de uma configuração de combate ao longo da vida;
- mapa, marcadores ou fichas de treino;
- não deve representar visualmente um Caminho específico como superior.

### Evitar

- mestre secreto de uma subclasse;
- vendedor de respec cômico;
- roupa metade de um Caminho/metade de outro de forma literal.

---

# 25. FIGURAS HISTÓRICAS — USO DE AUTOR / SPOILER

Estas figuras pertencem à camada histórica da Bíblia de Lore. Imagens player-facing devem respeitar gates narrativos.

## Elyra Sen

**Papel histórico:** demonstrou que anomalias veláricas distantes possuíam causa comum.

### Direção visual

- estudiosa asteriana adulta;
- vestuário técnico de alto nível sem aparência futurista;
- instrumentos analógicos de registro, placas, fios ou escalas;
- postura de observação e comparação;
- arquitetura asteriana limpa e funcional ao fundo quando apropriado.

### Leitura

> **A pessoa que percebeu que incidentes isolados formavam um padrão.**

---

## Teren Mor

**Papel histórico:** grande arquiteto da rede de Âncoras; defensor de redundância regional.

### Direção visual

- engenheiro/arquitetor asteriano maduro;
- roupas técnicas estruturadas;
- luvas, compasso, esquemas ou placas de referência;
- sem “mago construtor”.

### Leitura

> **Pensava em sistemas grandes demais para caber em uma única sala.**

---

## Maera Soln

**Papel histórico:** última grande diretora do Projeto Hemaris.

### Direção visual

- médica/pesquisadora adulta;
- aparência inicialmente clínica e controlada;
- roupas práticas, claras apenas quando funcionalmente plausíveis, nunca “jaleco moderno”; 
- luvas, instrumentos e recipientes biológicos antigos;
- sinais de exaustão crescente em imagens tardias.

### Leitura

> **Alguém que começou salvando vidas e terminou autorizando coisas que antes consideraria inadmissíveis.**

### Evitar

- cientista louca;
- vampira;
- vilã de laboratório com risada teatral.

---

## Neris Olan

**Papel histórico:** principal teórico político dos Desvelados tardios; autorizou a sabotagem.

### Direção visual

- intelectual político, não cultista;
- roupas civis asterianas sóbrias;
- sinais de deslocamento clandestino apenas em fase tardia;
- documentos, mapas de rede ou registros confiscados;
- aparência capaz de transmitir convicção sem maldade caricata.

### Evitar

- máscara de culto;
- capuz demoníaco;
- tatuagens de seita;
- “vilão do vazio”.

---

## Cael Rhen

**Papel histórico:** último Regente de Continuidade.

### Direção visual em vida

- administrador de crise;
- roupa formal asteriana funcional, sem coroa;
- sinais de autoridade institucional discretos;
- capa ou manto técnico de função possível, porém sem regalia monárquica;
- cansaço e pressão crescentes nas imagens finais.

### Evitar

- rei;
- imperador;
- sacerdote;
- necromante.

Para o **Regente Fraturado**, usar a Bíblia de Bestiário/Chefes: ele não deve ser representado simplesmente como Cael vivo após três séculos.

---

# 26. POVO ASTERIANO ANTIGO — VISUAL HUMANOIDE

A civilização asteriana era plural.

Portanto imagens do passado devem mostrar:

- diversidade de aparência;
- ausência de raça única “asteriana”;
- vestuário civil mais integrado e padronizado em construção que o presente;
- melhores acabamentos e manutenção;
- infraestrutura funcionando;
- símbolos institucionais discretos;
- nenhuma estética romana, egípcia ou tecnológica copiada diretamente.

## Materiais

- pedra trabalhada;
- metal de acabamento preciso;
- madeira tratada;
- cerâmica;
- vidro e cristal apenas onde função exigir;
- tecidos de boa qualidade;
- mecanismos de encaixe e tensão.

## Evitar

- sci-fi;
- hologramas;
- togas romanas universais;
- armadura de “Atlântida”;
- civilização de magos brancos.

---

# 27. HERDEIROS — DIREÇÃO VISUAL

Herdeiros são custodianos modernos de conhecimento antigo, não linhagem sanguínea obrigatória.

Visualmente:

- equipamento contemporâneo de Asterion adaptado para lidar com estruturas antigas;
- ferramentas de registro, reparo e contenção;
- peças asterianas reaproveitadas podem existir;
- símbolos de custódia podem variar entre núcleos;
- não existe uniforme mundial obrigatório.

Evitar:

- ordem secreta toda de branco;
- “descendentes escolhidos” visualmente perfeitos;
- sangue real.

---

# 28. PERSONAGENS POR REGIÃO — MATRIZ DE MATERIAL

| Região | Tecido | Couro | Metal | Resíduo visual |
|---|---|---|---|---|
| Terras do Ocaso | seco, desbotado | ressecado | fosco | cinza/fuligem |
| Vales dos Enforcados | encerado, úmido | escuro | oxidado moderado | turfa/musgo |
| Planícies de Nareth | leve, preso ao vento | claro ou curtido | gasto por areia | poeira/palha |
| Várzeas Carmesins | encerado, pesado | úmido | protegido/ferruginoso | salmoura/ferrugem |
| Altos Cinéreos | lã e camadas | espesso | escuro e reparado | fuligem/mineral |
| Confins do Véu | viagem técnica | funcional | marcas de orientação | névoa/condensação |

Essa tabela orienta material, não paleta obrigatória de pele ou cabelo.

---

# 29. MATRIZ DE SILHUETA DAS CLASSES

| Classe | Centro visual | Leitura imediata |
|---|---|---|
| Sentinela | tronco/base | sustentar pressão |
| Errante | pernas/quadril | mudar posição |
| Vigia | eixo olhos–arma | observar e disparar |
| Tecelão | mãos/espaço próximo | tensionar estrutura |
| Oráculo | olhar/antecipação | agir antes da consequência |
| Luminar | tórax/postura | exteriorizar vitalidade |

---

# 30. MATRIZ DOS CAMINHOS

| Caminho | Palavra visual | Não transformar em |
|---|---|---|
| Bastião | cobertura | cavaleiro santo |
| Devastador | contra-pressão | berserker |
| Carrasco | conclusão | serial killer |
| Sabotador | interferência | ninja/engenheiro steampunk |
| Atirador | concentração | sniper moderno |
| Rastreador | campo | druida/ranger florestal obrigatório |
| Conjurador | liberação | mago elemental genérico |
| Rúnico | estabilização | runemaster nórdico |
| Agoureiro | possibilidade ruim | bruxa amaldiçoadora |
| Invocador | alternância | pet class/druida |
| Guardião | sustentação | sacerdote healer |
| Inquisidor | interrupção | cruzado religioso |

---

# 31. EXPRESSÃO E PERSONALIDADE

Raça nunca determina personalidade obrigatória.

Não usar:

- todo Velado frio;
- todo Cinéreo estoico;
- todo Hemário agressivo;
- todo Alvorano confiante;
- todo Remanescente humilde.

Esses podem ser temas culturais ou tensões narrativas, não personalidade biológica.

Para retratos, personalidade individual deve vir antes do estereótipo racial.

---

# 32. IDADE

Todas as Raças devem poder ser retratadas em diferentes idades adultas.

Não estabelecer longevidade extraordinária sem Fonte específica.

Velado idoso continua humanoide.  
Hemário idoso não é vampiro ancião.  
Cinéreo idoso não petrifica.  
Alvorano idoso pode continuar atento sem parecer jovem artificialmente.

---

# 33. CABELO, BARBA E PILOSIDADE

As Raças possuem **faixas recorrentes de cabelo**, não uma única cor obrigatória.

A produção oficial deve respeitar os centros fenotípicos dos capítulos 5–9:

- Velados: liso/levemente ondulado e preto, acinzentado, prateado ou branco são recorrentes;
- Cinéreos: cabelo escuro, espesso e frequentemente ondulado/cacheado/crespo é recorrente;
- Hemários: preto, castanho profundo, auburn e cobre escuro são recorrentes;
- Alvoranos: preto, castanho, cobre e castanho-dourado com queda lisa/ondulada são recorrentes;
- Remanescentes: maior diversidade, com cabelo escuro ondulado/cacheado/crespo muito frequente no centro de produção.

Descendência mista, tingimento cultural, idade e conceito individual podem produzir exceções.

Não transformar uma tendência em uniformidade absoluta. Dois personagens da mesma Raça não precisam ter o mesmo cabelo.

---

# 34. OLHOS

Olhos ajudam a leitura racial, mas continuam humanos e não funcionam como LEDs de facção.

Tendências de produção:

- Velados: cinza, aço, azul/verde dessaturado ou castanho frio; reflexo sutil possível;
- Hemários: castanho profundo, âmbar, avelã ou verde-castanho de contraste mais vivo;
- Alvoranos: avelã, âmbar, castanho-claro ou verde-oliva, com atenção evidente;
- Cinéreos: tons humanos escuros e terrosos, sem cor sobrenatural;
- Remanescentes: diversidade ampla.

Evitar olhos luminosos permanentes como regra racial.

---

# 35. CICATRIZES E MARCAS

Cicatrizes devem contar história individual.

Não transformar cicatriz em decoração aleatória em todos os personagens.

Marcas institucionais devem existir somente quando a instituição estiver definida.

Tatuagens raciais universais não existem.

Fenótipo racial deve ser reconhecido por anatomia/pigmentação/cabelo/presença, não por um símbolo estampado no corpo.

---
# 36. POSTURA POR CLASSE

A postura comunica treinamento e hábito corporal. Ela **não obriga toda arte a representar combate iminente**. A Classe deve continuar legível em repouso, observação, deslocamento, preparação e ação.

## Sentinela
Pés firmes, ombros preparados e base capaz de receber pressão. Em pose combativa, a arma pode estar pronta para resposta; em repouso ou vigilância, pode estar abaixada, apoiada ou embainhada sem perder a leitura de Classe.

## Errante
Peso em transição, um pé já indicando a próxima linha. Mesmo parado, deve parecer capaz de mudar de posição sem rigidez excessiva.

## Vigia
Atenção, orientação corporal e arma de disparo podem formar um mesmo eixo quando a cena exigir mira. Em repouso, patrulha ou observação, a Classe continua legível com arco/besta abaixado, apoiado, nas costas ou sendo preparado.

## Tecelão
Mãos, foco ou espaço próximo sugerem controle preciso. Não é obrigatório conjurar em toda arte; examinar, medir, inscrever ou preparar uma tensão da Trama também comunica a Classe.

## Oráculo
Movimento parece começar antes da ameaça se completar. A leitura pode surgir apenas de atenção antecipatória, escolha de posição e uso contido de instrumentos, sem efeito sobrenatural obrigatório.

## Luminar
Tórax e respiração centrados; gesto vem depois da decisão. A Luz pode estar ausente em repouso ou surgir de forma localizada quando a ação exigir.

## 36.1 Estados de pose e intensidade

Para evitar que o catálogo pareça uma coleção de personagens repetindo a mesma pose de combate, cada arte humanoide deve declarar um **estado de pose**. Os estados oficiais de produção são:

1. **Repouso** — corpo relaxado, equipamento seguro, identidade ainda legível.
2. **Contemplação** — observação do ambiente, objeto ou horizonte; baixa tensão corporal.
3. **Vigilância** — atenção ativa sem ataque em curso.
4. **Deslocamento** — caminhada, mudança de posição, subida, avanço ou travessia.
5. **Preparação** — arma/foco sendo acessado, postura sendo montada ou técnica prestes a começar.
6. **Ação controlada** — execução legível e funcional, sem teatralidade excessiva.
7. **Ação intensa** — momento de maior esforço; usar com parcimônia para que não se torne o padrão do catálogo.

Regras:

- nenhuma Classe fica restrita aos estados 5–7;
- artes de seleção, Perfil e Aparência devem privilegiar variedade entre 1–6;
- **Ação intensa** deve ser minoria em um conjunto grande de skins;
- a pose deve preservar leitura de anatomia, silhueta e equipamento;
- personalidade individual não pode ser inferida automaticamente do estado de pose;
- Raça não determina agressividade, serenidade ou heroísmo da pose.

## 36.2 Estado da arma não é identidade da Classe

A arma/foco pode aparecer:

- embainhada;
- abaixada;
- apoiada;
- nas costas;
- sendo sacada/preparada;
- em guarda;
- em uso.

Não forçar todos os personagens a segurar a arma em posição de ataque. A leitura de Classe deve combinar postura, distribuição de peso, roupa/equipamento e ferramenta, não depender de uma única pose icônica.

### Arcos e bestas

Um Vigia **não precisa estar mirando ou disparando**. Estados válidos incluem arco nas costas, arco abaixado, arco apoiado, retirada de flecha, encaixe da flecha, observação do terreno, deslocamento, ajoelhamento de campo, mira e disparo.

Quando o arco estiver tensionado:

- a corda deve ser contínua e conectar corretamente as duas extremidades do arco;
- usar uma única flecha coerente com a ação;
- mão da corda, mão do arco, flecha e linha de mira devem formar uma geometria plausível;
- não cruzar corda, braço, flecha, aljava e roupa de forma impossível;
- se a anatomia ficar confusa, preferir um estado anterior ou posterior ao disparo em vez de insistir na pose mais complexa.

Essas regras de integridade anatômica e de objeto são detalhadas em `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`.

---

# 36.3 ACOMODAÇÃO DE ANATOMIA RACIAL EM EQUIPAMENTO

- **Velado:** capuz/elmo precisa deixar a orelha larga livre, dobrada de modo plausível ou protegida por volume lateral; nunca amputar visualmente.
- **Cinéreo:** gola, gorjal e peitoral precisam respeitar pescoço/tórax mais densos; boca não pode esconder caninos por erro de geração.
- **Hemário:** elmo/capuz deve ter recortes, canais, placas separadas ou desenho aberto para o par de chifres; não atravessar metal pelo chifre.
- **Alvorano:** capuz/elmo deve acomodar orelhas longas pontiagudas; não cortá-las nem convertê-las em ornamento do capacete.
- **Remanescente:** equipamento segue anatomia humana individual, sem adicionar apêndice apenas por estética.

Essas adaptações são visuais e não criam slots, bônus, penalidades ou equipamentos raciais mecânicos.

---

# 37. COMPOSIÇÃO DE RETRATOS DE SELEÇÃO

Quando a imagem for usada para **seleção de Raça**:

- priorizar centro fenotípico, rosto, corpo e presença racial;
- usar o **fundo de herança** da Raça descrito nos capítulos 5–9;
- tratar o fundo como vinheta evocativa, não como Local de Mapa literal nem prova de Estado racial;
- minimizar elementos de Classe;
- roupa civil/aventura coerente com a linhagem, sem uniforme militar;
- não colocar arma icônica que faça parecer escolha de Classe;
- entre apresentação masculina e feminina, variar rosto, idade e composição, mantendo a mesma família de fundo.

Quando usada para **seleção de Classe** ou para skin **Raça × Classe**:

- priorizar silhueta/equipamento da Classe;
- preservar pelo menos dois marcadores fenotípicos fortes da Raça;
- combinar o motivo histórico do fundo racial com um motivo funcional de Classe;
- não insinuar que uma Classe pertence a uma única Raça;
- não usar o mesmo cenário genérico para as 30 combinações Raça × Classe.

Quando usada para Caminho:

- manter base reconhecível da Classe;
- alterar especialização, não transformar em outra Classe.

---

# 38. REGRA DE DIVERSIDADE DAS ARTES OFICIAIS

Diversidade é planejada **dentro e entre** as famílias fenotípicas.

O conjunto oficial deve evitar dois erros opostos:

1. tornar todas as Raças visualmente intercambiáveis;
2. transformar cada Raça em um único rosto repetido.

Regras:

- usar o centro fenotípico para assets de seleção e primeiras âncoras;
- variar idade, gênero, constituição, rosto e detalhes dentro da faixa racial;
- usar descendência mista para exceções individuais deliberadas, não para neutralizar todo o catálogo;
- distribuir Raças entre Classes e NPCs;
- não usar sempre Cinéreo para Sentinela, Velado para Tecelão, Alvorano para Luminar, Hemário para Carrasco ou Remanescente para tudo.

---

# 39. GÊNERO NAS ARTES

As seis Classes e doze Caminhos devem possuir variedade de gênero ao longo das artes oficiais.

Não transformar:

- Guardião em função feminina obrigatória;
- Devastador em função masculina obrigatória;
- Oráculo em “feiticeira” por padrão;
- Vigia em “arqueiro homem” por padrão.

Apresentações masculina/feminina do lote são controle de produção, não limite de gênero da Lore.

---

# 40. FUNDO CONTEXTUAL PARA SKINS

Para skin isolada, o fundo deve servir como referência, nunca competir.

## 40.1 Fundo mínimo

- chão compatível com o conceito;
- partículas ambientais discretas;
- 1–2 formas arquitetônicas ou naturais reconhecíveis;
- luz coerente;
- contraste e microdetalhe inferiores ao personagem.

## 40.2 Fundos de herança racial

Os cinco fundos raciais oficiais são **motivos históricos/evocativos**, não Locais jogáveis obrigatórios:

- **Remanescente:** reconstrução em camadas, pedra reaproveitada, madeira nova, estrada/ponte/oficina remendada;
- **Velado:** limiar de pedra fria, arcos/umbrais repetidos, névoa fina, alinhamento quase perfeito; nunca Avesso explícito;
- **Cinéreo:** terreno severo, muros de sustentação, contrapesos, vento e arquitetura de carga; nunca magma;
- **Hemário:** pátio clínico/logístico antigo de Hemaris, metal oxidado, canais cobertos e instrumentos analógicos; nunca gore/laboratório sci-fi;
- **Alvorano:** terraço/rota civil pré-Ruptura, marcadores de orientação, horizonte aberto e luz clara; nunca templo solar.

## 40.3 Motivos funcionais de Classe

Para combinar com a herança racial:

- **Sentinela:** passagem defensiva, portão, posto de contenção, parapeito ou área de treino de pressão;
- **Errante:** rota partida, escada, corredor lateral, travessia estreita ou bifurcação;
- **Vigia:** mirante, torre baixa, linha longa de visão, marco de distância;
- **Tecelão:** área de manutenção, juntas de pedra, trilhos, placas e relações geométricas físicas sem círculo mágico;
- **Oráculo:** cruzamento, marcadores repetidos, caminhos possíveis, fitas/placas de orientação sem destino “profetizado”;
- **Luminar:** posto de recuperação, abrigo de campanha, pátio de apoio ou foco de calor/luz funcional; sem templo.

## 40.4 Regra Raça × Classe

O fundo de cada combinação deve ser construído por:

`HERANÇA RACIAL + FUNÇÃO DE CLASSE + CONTEXTO REGIONAL/APARÊNCIA (quando aplicável)`

A Matriz de Produção fecha os 30 fundos-base Raça × Classe.

Para apresentações masculina e feminina da mesma combinação:

- manter a mesma família espacial;
- variar enquadramento, lado do ponto de interesse, horário ou detalhe secundário;
- evitar duplicar exatamente a mesma imagem de fundo.

## 40.5 Não fazer

- castelo monumental, aqueduto épico, muralha distante ou bandeiras heráldicas como “fantasia genérica” quando a fonte não pedir;
- repetir o mesmo skyline/fortaleza em várias Classes da mesma Raça;
- usar o fundo como principal responsável por diferenciar Classes;
- batalha completa atrás do personagem;
- Chefe escondido no fundo sem necessidade;
- spoilers narrativos;
- Âncora identificável antes do gate correto;
- Avesso em arte inicial;
- mesmo conjunto de ruínas avermelhadas para todas as Raças;
- cenário tão detalhado que a Raça/Classe deixe de ser foco.

Para o mesmo personagem racial, os seis fundos de Classe devem parecer **seis espaços funcionais diferentes**, ainda que compartilhem materiais e herança. Um mesmo monumento dominante não deve aparecer como assinatura recorrente do conjunto.

Usar `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` quando o fundo representar uma Região ou Local real. Fundos de herança simbólicos não devem inventar um novo Local canônico.

---
# 41. PERSONAGEM DENTRO DE MASMORRA

Quando uma skin/arte mostra personagem em Masmorra:

- o personagem continua seguindo esta Bíblia;
- a Masmorra segue a Bíblia de Ambientes;
- criatura segue a Bíblia de Bestiário;
- o grau de conhecimento exibido respeita a Campanha.

Não permitir que o ambiente “contamine” visualmente a Raça sem evento narrativo explícito.

Exemplo:

um Remanescente na Várzea pode estar sujo de ferrugem e salmoura. Isso não o transforma em Hemário.

---

# 42. EFEITOS DE COMBATE EM ARTES PROMOCIONAIS

Efeitos precisam comunicar mecânica sem criar nova cosmologia.

### Barreira
Mostrar resistência temporária, não escudo divino universal.

### Cura
Mostrar recuperação/sustentação, não ressurreição.

### Debuff
Mostrar enfraquecimento contextual, não “maldição” automaticamente.

### Sangramento/Veneno/Queimadura
Mostrar com parcimônia; evitar gore excessivo em arte de seleção.

### Presságio
Mostrar possibilidade, não futuro definitivo.

### Trama
Mostrar tensão estrutural, não Mana.

### Luz
Mostrar vitalidade exteriorizada, não bênção divina.

---

# 43. NEGATIVE PROMPT GLOBAL — PERSONAGENS

Para prompts de geração, considerar como bloco negativo conceitual:

- modern clothing;
- guns;
- sci-fi;
- cyberpunk;
- steampunk machinery;
- neon;
- holograms;
- anime magic circles;
- generic high fantasy glow;
- oversized impossible weapons;
- excessive ornamental armor;
- World of Warcraft proportions;
- superhero costume;
- modern tactical gear;
- UI elements;
- text;
- logo;
- watermark;
- Velado ears shaped like long ascending Alvorano ears;
- extra horn pairs, glowing horns, demon wings, hooves or mandatory tails for Hemários;
- giant tusks, green-skin stereotype or stone skin for Cinéreos;
- angel wings/halo or metallic golden skin for Alvoranos or Luminares;
- undead anatomy for Velados;
- same generic face across different Raças;
- same generic ruin background across all race-selection assets;
- phenotype outside the approved racial center in a selection anchor unless intentionally marked as mixed ancestry;
- independent animal pets for Invocador;
- digital glitch for Avesso-related characters;
- religious crosses as default Luminar/Inquisidor iconography.

---

# 44. TEMPLATE — PROMPT DE PERSONAGEM JOGÁVEL

Use esta estrutura ao produzir um novo prompt:

## Identidade

**Personagem:** [nome ou função]  
**Raça:** [Raça]  
**Classe:** [Classe]  
**Caminho:** [se aplicável]  
**Região/contexto:** [Região]  
**Idade aparente:** [faixa]  
**Gênero/apresentação:** [quando definido]  
**Estado de pose:** [Repouso / Contemplação / Vigilância / Deslocamento / Preparação / Ação controlada / Ação intensa]
**Centro fenotípico / exceção familiar:** [marcadores raciais que precisam permanecer legíveis]
**Fundo:** [herança racial + função de Classe + Região, quando aplicável]

## Anatomia e presença

[Traços individuais] + [invariantes raciais] + [o que não pode virar].

## Rosto

[Formato, expressão, pele, olhos, cabelo, marcas individuais].

## Corpo e postura

[Constituição] + [postura de Classe] + [leitura de Caminho].

## Equipamento

[Armadura/roupa] + [arma/foco] + [materiais regionais].

## Efeito extraordinário

Somente quando aplicável, seguindo Trama/Presságio/Luz.

## Composição

Corpo inteiro, centralização, margens, fundo subordinado; em Raça × Classe, combinar herança racial e motivo funcional de Classe sem transformar o cenário em Local canônico novo.

## Estética

Pixel art dark fantasy medieval, fim 16-bit/início 32-bit, pixels deliberadamente visíveis.

## Proibições

Inserir negativos específicos de Raça + Classe + Região.

---

# 45. TEMPLATE — NPC

**NPC:** [nome]  
**Papel:** [função real, sem inventar título]  
**Região:** [Região]  
**Raça:** [somente se canonizada; se não, não fixar]  

### Leitura principal
[O que deve ser compreendido sem texto]

### Anatomia
[Não inventar Raça se desconhecida]

### Vestuário
[função + materiais regionais]

### Objeto de assinatura
[1 item funcional]

### Postura
[perfil comportamental]

### Proibições
[títulos, símbolos ou poderes que o NPC não possui]

---

# 46. REGRA CRÍTICA PARA NPCs SEM RAÇA CANÔNICA

Se a Fonte não disser a Raça de um NPC nomeado:

> **não transformar uma escolha de concept art em verdade de Lore automaticamente.**

A arte pode usar uma Raça para uma versão visual aprovada, mas isso deve ser formalizado separadamente se quisermos que passe a ser cânone textual.

Até essa formalização, o documento preserva a função e a estética do NPC sem declarar sua Raça.

Essa regra se aplica aos NPCs de Terras do Ocaso e Vales quando sua Raça não estiver explicitamente estabelecida na Fonte Regional.

---

# 47. SPOILERS E PERSONAGENS HISTÓRICOS

Não exibir em material inicial:

- Neris Olan associado explicitamente à sabotagem;
- Maera Soln como diretora de Hemaris;
- Cael Rhen relacionado ao Regente Fraturado;
- uniformes Desvelados que revelem iconografia antes da descoberta;
- ferramentas que expliquem função das Âncoras antes de Nareth;
- anatomia Hemária “de laboratório” como se todos soubessem a origem.

As artes internas de produção podem conter tudo.

Arte player-facing respeita gate.

---

# 48. CONSISTÊNCIA COM O BESTIÁRIO

Humanoides alterados e criaturas não devem reutilizar diretamente silhuetas de personagens jogáveis a ponto de sugerir origem racial falsa.

Exemplo:

- Peregrino Calcinado não deve parecer “Remanescente corrompido confirmado” se a Fonte não confirma isso naquele gate;
- Vigias não devem parecer Sentinelas humanos usando armadura;
- Matriz Rubra não deve parecer Hemária gigante;
- criaturas dos Confins não devem parecer Velados monstruosos.

---

# 49. CONSISTÊNCIA COM AMBIENTES

A roupa deve carregar o ambiente de modo físico:

- Ocaso deposita cinza;
- Vales umedecem tecido e couro;
- Nareth dobra e tensiona peças pelo vento;
- Várzeas deixam salmoura, lodo e ferrugem;
- Altos desgastam por fuligem, pedra e frio;
- Confins introduzem condensação e marcadores de orientação, não “corrupção cósmica”.

---

# 50. CHECKLIST DE APROVAÇÃO DE SKIN

Antes de aprovar uma skin, responder:

1. A Raça está legível por fenótipo/presença sem depender do nome e sem virar caricatura?
2. Pelo menos dois marcadores fenotípicos sobrevivem quando a Classe domina a roupa?
3. A Classe está legível pela postura/equipamento?
4. O Caminho é uma especialização da Classe, não outra profissão?
5. A Região aparece nos materiais sem transformar o corpo?
6. O fundo combina herança racial/função de Classe sem competir com o personagem?
7. Existe algum clichê proibido?
8. O efeito sobrenatural pertence realmente à Classe?
9. Algum elemento revela spoiler?
10. A arma parece utilizável?
11. O personagem está centralizado e inteiro quando a finalidade exige skin completa?
12. A arte continua parecendo Asterion sem o nome escrito nela?

Se qualquer resposta crítica for “não”, revisar antes de integrar.

---

# 51. CHECKLIST DE RAÇAS

### Remanescente
- diversidade interna alta, porém identidade material clara;
- centro de produção favorece pele média/escura e cabelo escuro ondulado/cacheado/crespo sem universalizar;
- adaptabilidade e reparo;
- não “humano padrão puro”.

### Velado
- pele clara/pálida/oliva fria predominante no centro de seleção;
- cabelo liso/levemente ondulado preto, acinzentado, prateado ou branco recorrente;
- linhas longas, olhar estável e inquietação sutil;
- sem elfo, morto-vivo ou Avesso.

### Cinéreo
- pigmentação terrosa e cabelo escuro espesso recorrentes;
- ossatura/base firme e resistência estrutural;
- sem pedra corporal, magma ou anão obrigatório.

### Hemário
- subtom quente/rubro/cobre e circulação visualmente viva;
- cabelo preto/castanho/auburn/cobre recorrente;
- tensão e vitalidade intensa;
- sem vampiro.

### Alvorano
- pele oliva/dourada/bronze humana, cabelo liso/ondulado escuro/cobre e olhos avelã/âmbar recorrentes;
- coordenação e prontidão;
- sem anjo, halo ou luz racial.

---

# 52. CHECKLIST DE CLASSES

### Sentinela
Pressão e resposta, não paladino.

### Errante
Mobilidade e brecha, não ladrão obrigatório.

### Vigia
Observação e precisão, não ranger florestal obrigatório.

### Tecelão
Estrutura/Trama, não mago de Mana.

### Oráculo
Possibilidade, não profeta onisciente.

### Luminar
Vitalidade/Luz, não sacerdote divino obrigatório.

---

# 53. AUTORIDADE DE USO PARA GERAÇÃO DE IMAGEM

Para gerar **personagem jogável ou NPC humanoide**, usar em conjunto:

1. `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` — identidade humanoide;
2. `ASTERION_LORE_BIBLE_CANON_v1.2.md` — verdade narrativa;
3. `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` — fundo/Região;
4. Fonte Regional vigente — nomes e conteúdo específico;
5. Fonte Visual/UI — enquadramento player-facing;
6. `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` — execução gráfica, integridade anatômica, armas, pixel art e QA;
7. `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` — atribuições concretas do lote, incluindo arma-assinatura obrigatória, quando houver âncora correspondente.

Para criatura, prevalece a Bíblia de Bestiário Visual em identidade/anatomia; a Bíblia Técnica continua válida para execução gráfica e QA.

---

# 54. ESTADO FINAL

Com esta Fonte ficam fechados para direção visual:

- anatomia global humanoide;
- famílias fenotípicas e leitura imediata das 5 Raças;
- fundos de herança racial e composição Raça × Classe;
- descendência mista;
- leitura das 6 Classes;
- leitura dos 12 Caminhos;
- diferença visual dos três sistemas extraordinários;
- vestuário civil;
- adaptação material por Região;
- armas e equipamento;
- uso de Aparências cosméticas;
- NPCs persistentes das Terras do Ocaso;
- NPCs persistentes dos Vales dos Enforcados;
- figuras históricas centrais já definidas na Bíblia de Lore;
- antigo povo asteriano;
- Herdeiros;
- composição de skins;
- efeitos de combate em arte;
- negative prompt global;
- templates para prompts futuros;
- estados de pose e intensidade;
- checklist de aprovação.

A execução técnica de pixel art, canvas, integridade anatômica, armas, transparência, exportação e QA raster segue `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`, sem alterar a identidade canônica definida aqui.

Não são transformados em cânone sem definição adicional:

- Raça individual de NPC persistente que não possua bloco **Identidade canônica** nesta Bíblia ou definição explícita em Fonte superior;
- detalhes faciais exatos de NPCs ainda sem concept aprovado;
- cor oficial universal de Trama, Presságio ou Luz;
- uniforme obrigatório de qualquer Classe;
- armas exclusivas não definidas mecanicamente;
- NPCs persistentes ainda não escritos para Regiões 3–6.

Esses pontos podem ser definidos durante produção visual ou regional sem reabrir os fundamentos deste documento.

---

# 55. FRASE-GUIA

> **Em Asterion, um personagem deve parecer alguém que vive neste mundo antes de parecer uma coleção de símbolos de fantasia.**

---

# DOCUMENTO INCORPORADO 2/9
## Arquivo original: `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`
# ASTERION — BÍBLIA VISUAL DE BIOMAS E BESTIÁRIO v1.1

**Estado:** fechamento de Lore + direção visual para geração/refação de skins de criaturas.  
**Base autoritativa preservada:** Fonte Mestra v1.6.0; Terras do Ocaso v1.0.16 FINAL; Vales dos Enforcados v1.0.6 FINAL; Consolidação Visual/UI 2026-10-13.\
**Escopo deste documento:** biomas, ecologia visual, anatomia, silhueta, materiais, escala, leitura combatente, sinais regionais, proibições visuais, Elites, criaturas de Masmorra e Chefes das seis Regiões.

> Este documento NÃO reabre números de combate, economia, loot, níveis ou regras mecânicas já fechadas. Quando uma criatura das Regiões 1–2 já possui Categoria, Arquétipo, Habitat, Variante ou função definida na Fonte Regional, tudo isso permanece inalterado. As descrições visuais abaixo expandem essa identidade sem substituir a mecânica.

> **Revisão v1.1:** incorpora o **Guardião do Último Rastro**, Chefe roteirizado da S6 nas Terras do Ocaso, e fecha sua linguagem visual sem resolver origem, identidade ou natureza ontológica. Nenhuma criatura anterior é substituída no Bestiário normal; o Custódio Sem Rosto permanece criatura distinta.

---

# 1. REGRAS VISUAIS GLOBAIS DAS CRIATURAS

## 1.1 Direção geral

A fauna e os inimigos de Asterion devem parecer pertencentes ao mesmo mundo físico. Mesmo quando extraordinários, devem conservar peso, matéria, desgaste, gravidade e anatomia legível.

Priorizar:

- dark fantasy medieval melancólico;
- formas reconhecíveis antes de formas abstratas;
- materiais envelhecidos, orgânicos, minerais ou asterianos coerentes com a origem;
- assimetria controlada;
- sinais de adaptação ao bioma;
- ameaça transmitida por anatomia/postura, não por excesso de aura;
- cicatrizes, erosão, raízes, fuligem, ferrugem, turfa, mineralização ou distorção apenas quando fizerem sentido para a Região.

Evitar como padrão:

- neon intenso;
- aura colorida genérica de raridade;
- cristais aleatórios sem origem;
- chifres demoníacos adicionados por “fantasia”;
- olhos brilhantes em todas as criaturas;
- armaduras completas em animais sem justificativa;
- tentáculos em criaturas que não possuem motivo biológico/cosmológico;
- aparência de MMO cartunesco;
- gore excessivo como substituto de design;
- transformar todo inimigo antigo em morto-vivo.

## 1.2 Escala visual

**Comum:** escala natural ou ligeiramente ampliada; silhueta limpa.  
**Incomum:** uma anomalia anatômica, material ou comportamental claramente legível.  
**Elite:** presença maior, massa ou refinamento visual claramente superior à criatura-base relacionada; não usar apenas “mesmo monstro, 30% maior”.  
**Chefe:** silhueta própria e memorável, com leitura imediata do tema regional.

## 1.3 Variantes — linguagem visual global

As Variantes mecânicas existentes podem alterar visualmente a criatura, mas nunca devem apagar sua identidade-base.

### Furioso
- postura mais agressiva e inclinada para frente;
- musculatura tensa;
- lesões recentes ou tecido exposto apenas de forma moderada;
- mandíbula/garras/estrutura ofensiva mais marcada;
- **não usar aura vermelha genérica**.

### Resistente
- massa mais compacta;
- pele, carapaça, couro, casca ou placas mais espessas conforme a espécie;
- cicatrizes antigas;
- membros de apoio visualmente mais fortes;
- **não transformar automaticamente em pedra**.

### Ágil
- silhueta mais esguia;
- membros mais longos ou articulações mais leves;
- massa reduzida;
- postura pronta para deslocamento;
- **não usar rastros luminosos ou speed lines incorporados à criatura**.

### Hemorrágico
- estruturas cortantes, dentes, garras ou bordas anatômicas mais aptas a abrir feridas;
- manchas de sangue seco podem existir;
- **não tornar a criatura uma massa gore**.

### Venenoso
- glândulas, ferrões, presas, cerdas ou secreções biologicamente plausíveis;
- tons doentios podem aparecer de forma contida;
- **não usar verde neon obrigatório**.

## 1.4 Construtos asterianos

Vigias, Custódios, Preceptores e outras construções antigas devem compartilhar uma linguagem:

- pedra trabalhada + metal escurecido/oxidado + encaixes precisos;
- geometria funcional, não ornamental em excesso;
- placas sobrepostas e juntas mecânicas discretas;
- rosto inexistente, simplificado ou funcional quando aplicável;
- inscrições mínimas, técnicas;
- brilho interno apenas onde houver função, nunca como “runas mágicas por toda parte”.

Eles não são robôs sci-fi, cavaleiros humanos petrificados ou golens elementais genéricos.

## 1.5 Humanos alterados, Peregrinos e Ecos

Quando um inimigo deriva de uma pessoa ou memória humana:

- preservar proporções humanoides reconhecíveis;
- evitar zumbi genérico;
- roupas, ferramentas e marcas devem contar origem regional;
- não presumir morto-vivo, possessão ou alma aprisionada se a Lore não disser isso.

---

# 2. 🌑 TERRAS DO OCASO — BIOMA VISUAL

**Faixa:** Nv.1–10.  
**Identidade:** cinza, secura, fuligem, ruína exposta, vegetação queimada, céu frio, silêncio e estruturas antigas de guarda.

## 2.1 Paleta e materiais

- cinza frio;
- carvão;
- marrom ressecado;
- ferrugem escura;
- pedra enegrecida;
- pequenos pontos âmbar de brasa apenas quando justificados;
- couro ressecado;
- madeira carbonizada.

A Região **não** deve parecer um inferno vulcânico. A maior parte do fogo já passou. O visual é de **depois do incêndio**, não de uma floresta permanentemente em chamas.

## 2.2 Locais

### Estrada das Cinzas
Estrada antiga coberta de cinza fina, campos secos, marcos de pedra gastos, cercas quebradas, vegetação baixa morta e horizonte aberto. Criaturas usam a estrada como corredor de caça.

### Refúgio do Ocaso
Zona segura. Não usar como habitat visual de monstros normais.

### Charneca da Fuligem
Terreno aberto irregular, montes de fuligem, arbustos secos, covas antigas e bolsões onde resíduos químicos/orgânicos sobrevivem. Mais hostil que a Estrada.

### Bosque Calcinado
Troncos negros, galhos secos, raízes expostas e pequenas brasas profundas. Não representar fogo florestal ativo generalizado.

### Ruínas do Vigia
Arquitetura asteriana defensiva, pedra escura, corredores quebrados, torres parciais e mecanismos ainda ativos.

### Câmara do Poente
Espaço asteriano monumental, austero e funcional. A imagem não deve revelar visualmente a verdadeira função cosmológica da Âncora antes do momento narrativo apropriado.

---

# 3. 🌑 TERRAS DO OCASO — BESTIÁRIO VISUAL

## Criaturas-base oficiais

### 3.1 Cão Cinéreo · Comum · Predador
**Habitat:** Estrada das Cinzas; Charneca da Fuligem.  
**Silhueta:** canídeo de porte médio, peito estreito, pernas resistentes, cabeça baixa.  
**Anatomia:** pelo curto irregular coberto por poeira cinzenta; pele visível em pontos escoriados; orelhas parcialmente danificadas; patas largas para solo de cinza.  
**Leitura combatente:** perseguidor direto, mordida e investida curta.  
**Direção visual:** deve parecer um animal que vive há gerações num ambiente abrasivo, não um “lobo demoníaco”.  
**Evitar:** fogo saindo da boca, ossos expostos exagerados, múltiplos olhos, chifres, aparência de morto-vivo.

### 3.2 Corvo de Fuligem · Comum · Predador
**Habitat:** Estrada e áreas abertas do Ocaso.  
**Silhueta:** corvídeo grande, asas longas, pescoço curto, bico gasto.  
**Anatomia:** penas pretas foscas cobertas de fuligem; bordas das penas acinzentadas; patas fortes.  
**Leitura combatente:** rasantes e assédio, capaz de prejudicar movimento.  
**Evitar:** corvo mágico de olhos neon, tamanho de dragão, aura sobrenatural sem base.

### 3.3 Peregrino Calcinado · Comum · Equilibrado
**Habitat:** Estrada; Charneca.  
**Silhueta:** humanoide curvado, roupas de viagem antigas queimadas e endurecidas.  
**Anatomia:** corpo ressecado e marcado por fuligem, mas não deve ser classificado visualmente como cadáver ambulante de forma definitiva; identidade/origem permanece ambígua na Região.  
**Equipamento:** restos de bastão, lâmina simples, bolsa ou fragmentos de vestimenta de peregrino.  
**Leitura combatente:** golpe desesperado e defesa ocasional.  
**Evitar:** zumbi clássico, fogo permanente no corpo, símbolos que revelem origem não conhecida.

### 3.4 Aranha de Cinza · Incomum · Controlador
**Habitat:** Charneca; Bosque.  
**Silhueta:** aracnídeo baixo, abdômen compacto, pernas longas mas não finíssimas.  
**Anatomia:** carapaça cinza fosca com depósitos de fuligem; quelíceras robustas; glândulas tóxicas discretas.  
**Leitura combatente:** veneno e controle por picada.  
**Evitar:** aranha de lava, verde venenoso neon, tamanho de edifício.

### 3.5 Cervo Escoriado · Comum · Bruto
**Habitat:** Charneca; Bosque.  
**Silhueta:** cervídeo forte, tórax pesado, galhada irregular.  
**Anatomia:** couro áspero com áreas sem pelo e cicatrizes por vegetação queimada/cinza abrasiva; galhos partidos e regenerados.  
**Leitura combatente:** carga anunciada e impacto físico.  
**Evitar:** cervo demoníaco, crânio exposto, galhada flamejante.

### 3.6 Carniçal de Fuligem · Comum · Bruto
**Habitat:** Bosque; Ruínas.  
**Silhueta:** humanoide predatório largo, braços fortes, postura inclinada.  
**Anatomia:** pele grossa escurecida por fuligem e cicatrização irregular; unhas/garras naturais capazes de rasgar. A palavra Carniçal descreve comportamento e aparência, não confirma morto-vivo.  
**Leitura combatente:** dilaceração, sangramento e arrancada.  
**Evitar:** cadáver putrefato genérico, mandíbula sobrenatural impossível sem motivo.

### 3.7 Mariposa de Brasa · Incomum · Conjurador
**Habitat:** Bosque; Ruínas.  
**Silhueta:** grande lepidóptero de asas largas e corpo curto.  
**Anatomia:** padrões de asas lembram carvão rachado com pontos quentes; escamas retêm calor.  
**Leitura combatente:** queimadura e clarão de cinzas.  
**Evitar:** fênix, criatura inteiramente feita de fogo, asas de energia pura.

### 3.8 Vigia Rachado · Comum · Blindado
**Habitat:** Ruínas do Vigia.  
**Natureza:** construto asteriano.  
**Silhueta:** guardião humanoide robusto, sem aparência humana real.  
**Materiais:** pedra trabalhada rachada, ferragens escuras, placas defensivas; fissuras físicas reais.  
**Leitura combatente:** golpe pesado e Barreira/guarda parcial.  
**Evitar:** cavaleiro fantasma, estátua clássica greco-romana, robô sci-fi.

### 3.9 Custódio Sem Rosto · Incomum · Controlador
**Habitat:** Ruínas do Vigia.  
**Natureza:** construto asteriano.  
**Silhueta:** mais alto e estreito que o Vigia Rachado; cabeça/face lisa ou funcionalmente ausente.  
**Materiais:** pedra escura, metal, placas com encaixes mais precisos.  
**Leitura combatente:** marca, proteção e impacto.  
**Evitar:** máscara humana branca, monge sobrenatural, horror facial orgânico.

## Elites oficiais de mundo aberto

### 3.10 Alfa Cinéreo · Elite · Predador
**Habitat:** Estrada das Cinzas.  
**Base visual:** parente maior e dominante do Cão Cinéreo, porém com silhueta própria: ombros altos, mandíbula larga, cicatrizes de disputa, patas dianteiras fortes.  
**Leitura:** caçador que abre ferida e prepara salto predatório.  
**Evitar:** apenas escalar um Cão Cinéreo comum; adicionar armadura humana.

### 3.11 Viúva da Fuligem · Elite · Controlador
**Habitat:** Bosque Calcinado.  
**Visual:** aranha grande de abdômen alongado, placas escuras, fiandeiras fortes, pernas capazes de prender-se a troncos carbonizados.  
**Leitura:** veneno + redução de mobilidade.  
**Evitar:** vermelho/preto de “viúva-negra” obrigatório; estética tropical brilhante.

### 3.12 Custódio do Poente · Elite
**Habitat:** Ruínas do Vigia.  
**Natureza:** construto asteriano de guarda superior.  
**Silhueta:** torso largo, membros pesados, placas frontais de proteção, cabeça mínima; deve parecer projetado para defender passagem.  
**Leitura:** Guarda do Poente e Queda do Poente.  
**Evitar:** cavaleiro com escudo humano comum; símbolos que expliquem a Âncora.

## Chefe de Missão — S6

### 3.12-A Guardião do Último Rastro · Chefe

**Missão:** S6 — Onde os Nomes Terminaram.  
**Local:** Ruínas do Vigia, no último trecho acessível da rota investigada.  
**Faixa:** Nv.10.  
**Formato:** Solo.  
**Variante:** nenhuma.  
**Natureza real:** desconhecida e deliberadamente não confirmada.

#### Conceito central

Uma figura humanoide de travessia que deixou de parecer apenas um viajante, mas cuja forma ainda é definida por caminho, desgaste, bloqueio e permanência.

A primeira leitura desejada é:

> **“Algo permaneceu aqui para impedir que alguém percorresse o último trecho.”**

A imagem deve apresentar essa presença sem responder quem ou o que ela é.

#### Silhueta

- humanoide alta e severa;
- aproximadamente uma cabeça acima de um humano adulto, sem escala monumental;
- torso relativamente estreito, mas mais sólido e protegido que o Peregrino Calcinado;
- pernas longas e firmes de viajante;
- ombro esquerdo visualmente mais pesado/protegido;
- lado direito mais livre para manejar a arma;
- assimetria produzida por equipamento e reparos, não por mutação anatômica;
- postura ligeiramente inclinada para frente, como alguém acostumado a atravessar vento, cinza e terreno ruim.

Em leitura reduzida, deve parecer **Chefe humanoide de passagem**, não construto asteriano, cavaleiro ou massa funerária.

#### Anatomia aparente

- exatamente uma cabeça, dois braços, duas mãos, duas pernas e dois pés;
- proporção humanoide plausível;
- nenhuma deformação que prove espécie/natureza diferente;
- nenhuma parte cadavérica necessária;
- nenhum membro extra;
- nenhum elemento flutuante.

O corpo pode sugerir que existe algo humano sob as camadas, mas isso nunca pode ser confirmado pela imagem.

#### Cabeça e rosto

- capuz de viagem antigo, seco e endurecido por fuligem;
- placa facial estreita e irregular cobrindo principalmente a porção superior do rosto;
- tecido envolvendo a parte inferior;
- olhos não claramente visíveis;
- nenhuma luz ocular;
- placa sem feições humanas esculpidas, sorriso, caveira ou símbolo ritual;
- a placa deve parecer proteção reaproveitada, não máscara cerimonial nem rosto mecânico.

Pergunta visual permitida:

> “Há um rosto aí embaixo?”

A imagem não responde.

#### Roupa e proteção

Camada-base:

- túnica de viagem espessa;
- calças resistentes;
- botas altas muito gastas;
- capas/tecidos curtos em camadas;
- couro escurecido;
- fuligem profundamente impregnada;
- reparos visíveis de épocas diferentes.

Proteção assimétrica:

- pequenas placas de ferro/metal escurecido;
- reforços de couro;
- um ombro esquerdo mais protegido por peça irregular;
- tiras e fivelas funcionais;
- poucas peças rígidas reaproveitadas da própria rota.

Não usar armadura completa. A roupa deve parecer **mantida e remendada durante uma travessia excessivamente longa**, não uniforme de ordem conhecida.

#### Arma

Usar uma **longa haste de travessia reforçada**, sem nome de item canônico próprio.

Construção visual:

- madeira muito escura e ressecada;
- reforço metálico parcial;
- ponteira grossa/ferrão funcional em uma extremidade;
- pequeno travessão ou encaixe lateral irregular próximo ao topo;
- comprimento aproximado da altura do próprio Guardião ou pouco maior;
- marcas fortes de uso repetido.

A arma deve poder ter sido, em algum momento, ferramenta de apoio, sondagem, movimentação de carga, marcação ou defesa de passagem. A imagem não escolhe uma dessas origens como verdade.

Não representar como:

- cajado mágico;
- lança nobre/elegante;
- alabarda militar formal;
- relíquia luminosa;
- arma asteriana inequívoca.

#### Leitura das Artes

**Golpe da Última Trilha — 100% ATQ**  
A haste funciona como arma física direta: golpe lateral, diagonal, de ponta ou com o corpo reforçado.

**Marca do Rastro — 90% ATQ + AGI −10% · 2T, CD3**  
A redução de AGI deve ter leitura física: golpe/interceptação dirigida a apoio, joelho, perna, passada, equipamento ou trajetória. Não desenhar marca arcana, selo luminoso ou maldição visível.

**Queda da Travessia — Preparada · 165% ATQ, CD4**  
A ação deve possuir telegraph corporal inequívoco: base ampla, peso transferido para trás, mãos espaçadas na haste, extremidade pesada erguida e trajetória de descida brutal claramente preparada. A ameaça vem de massa + alcance + preparação, não de energia.

#### Assinaturas visuais exclusivas

Usar **duas assinaturas principais**:

1. **Fragmentos de marcadores da rota** — três ou quatro pequenos elementos rígidos no máximo, presos funcionalmente a ombro, cinto ou costas. Podem ser pedra marcada, madeira antiga ou metal, mas nenhuma inscrição pode ser legível e nenhum símbolo pode explicar a história.
2. **Desgaste direcional recorrente** — bota, tecido, ombro, placas e haste apresentam abrasão repetida em direções coerentes, como se os mesmos movimentos e contatos tivessem sido realizados vezes demais. Isso é sugestão visual, não confirmação de repetição sobrenatural.

#### Materiais

- tecido seco e enegrecido;
- couro ressecado;
- madeira antiga;
- ferro/metal escurecido;
- ferrugem discreta;
- pedra escura em poucos fragmentos;
- fuligem e cinza fina.

Nada deve parecer novo, polido ou cerimonial.

#### Paleta

Dominantes:

- carvão;
- cinza seco;
- marrom quase negro;
- ferro oxidado;
- couro queimado/ressecado.

Secundários controlados:

- bege morto de tecido antigo;
- ferrugem profunda;
- bronze escurecido muito pontual.

Evitar vermelho saturado, roxo, verde espectral, azul mágico, branco luminoso e qualquer glow.

#### Pose-base da skin

- corpo inteiro;
- 3/4 consistente com o catálogo;
- um pé ligeiramente à frente;
- haste em diagonal quase vertical, tocando ou próxima do chão;
- ombro mais protegido parcialmente oferecido ao observador;
- cabeça discretamente baixa;
- postura imóvel e deliberada de bloqueio;
- nenhuma pose heroica;
- nenhum grito;
- não representar a Queda da Travessia já totalmente executada na skin-base.

A sensação deve ser:

> **“Você ainda pode recuar.”**

#### Relação com as demais criaturas das Terras do Ocaso

**Peregrino Calcinado:** compartilha apenas linguagem material de viagem e exposição regional. O Guardião é mais alto, mais deliberado, mais equipado e menos curvado. Não deve parecer “Peregrino Elite”.

**Custódio Sem Rosto:** permanece construto asteriano vertical e preciso. O Guardião deve possuir tecido, couro, madeira e organização corporal aparentemente humanoide; nada de juntas/placas técnicas que o classifiquem como construto.

**Custódio do Poente / Vigias:** não compartilhar DNA tecnológico inequívoco. O Guardião não possui cabeça funcional asteriana, placas geométricas coordenadas ou engenharia de Barreira.

**Guardião das Lápides:** este é maciço, funerário e integrado a lajes. O Guardião do Último Rastro é alto, de travessia e relativamente móvel. Não usar lápides como proteção.

**O Sem-Nome:** monumental, funerário e baseado em identidade apagada. O Guardião do Último Rastro não usa volume de tecidos funerários, objetos pessoais acumulados, placas tumulares ou escala monumental. Nenhum detalhe deve sugerir que sejam a mesma entidade.

**Vigia Partido:** clímax regional asteriano monumental. O Guardião deve permanecer muito abaixo dessa escala e sem linguagem de máquina/ordem asteriana confirmada.

#### Fundo para Bestiário/skin

Fundo simples e subordinado, usando apenas sinais mínimos das Ruínas do Vigia:

- pedra escurecida;
- fuligem no piso;
- fragmento de parede/passagem;
- ferrugem discreta;
- céu/luz fria quando houver abertura externa.

Não mostrar o último registro legível em detalhe. Não incluir texto legível, O Sem-Nome, Peregrinos reconhecíveis, Âncora, Câmara do Poente ou outra revelação narrativa.

#### Limites de spoiler

A imagem pode comunicar:

- humanoide desconhecido;
- longa exposição às Terras do Ocaso;
- relação material com travessia/rota;
- função presente de bloquear passagem;
- capacidade de marcar deslocamento e preparar impacto.

A imagem **não pode confirmar**:

- identidade anterior;
- que seja O Sem-Nome;
- que seja um Peregrino específico;
- que seja um Peregrino transformado;
- que seja construto asteriano;
- que seja morto-vivo, fantasma, espírito ou possuído;
- que pertença a uma Raça jogável;
- ligação com Avesso, Âncora, Convergência ou qualquer causa cosmológica;
- motivo consciente para guardar a passagem.

#### Proibições visuais específicas

- nenhuma caveira como rosto;
- nenhum rosto humano claramente revelado;
- nenhum olho luminoso;
- nenhuma aura;
- nenhuma runa brilhante;
- nenhum portal;
- nenhuma corrente mágica;
- nenhuma necromancia;
- nenhum sangue/gore como identidade;
- nenhuma lápide incorporada;
- nenhum uniforme de Custódio/Vigia;
- nenhuma máscara branca lisa semelhante ao Custódio Sem Rosto;
- nenhuma coroa;
- nenhum símbolo religioso real;
- nenhum texto legível;
- nenhum elemento sci-fi;
- nenhuma anatomia impossível;
- nenhuma arma lendária ornamentada.

#### QA de leitura em miniatura

Quando reduzido para leitura de Bestiário/Telegram, ainda devem permanecer claros:

1. humanoide alto;
2. Chefe;
3. silhueta assimétrica;
4. ombro esquerdo mais protegido;
5. longa haste reforçada;
6. equipamento de travessia em camadas;
7. capuz + rosto oculto;
8. postura de bloqueio;
9. materiais de cinza/fuligem;
10. ausência de magia explícita.

#### Frase-guia visual

> **“A estrada terminou. Ele não.”**

## Cripta do Ocaso

### 3.13 Profanador Calcinado · Comum
Humanoide deformado pelo ambiente da Cripta; restos de vestimenta funerária ou ferramentas de saque. Não confirmar visualmente se é morto-vivo, peregrino alterado ou outra origem antes do conhecimento apropriado.

### 3.14 Guardião das Lápides · Elite
Figura maciça associada a pedra funerária quebrada, placas/lajes incorporadas à proteção. Visual deve justificar “Lápide Partida” e “Peso dos Mortos” sem transformá-lo em necromante.

### 3.15 O Sem-Nome · Chefe
**Silhueta:** humanoide monumental, envolto em camadas de tecidos funerários, placas, marcas apagadas e objetos sem identificação.  
**Tema:** perda de identidade, nomes apagados, sepulcro e memória.  
**Evitar:** revelar identidade anterior, coroa de lich, estética de rei morto-vivo genérico.

## Galerias do Vigia

### 3.16 Vigia Íntegro · Elite
Versão preservada da linguagem asteriana dos Vigias: placas completas, simetria funcional, juntas em bom estado. Deve mostrar como um Vigia era antes de séculos de dano, sem parecer novo ou brilhante demais.

### 3.17 Preceptor Rachado · Elite
Construto de comando, mais esguio, com braços/estruturas capazes de regular Condutores. Visual deve transmitir autoridade técnica, não sacerdócio.

### 3.18 Custódio do Primeiro Selo · Chefe
Grande guardião asteriano de contenção. Placas sobrepostas, estrutura frontal reforçada e pontos físicos onde Fragmentos de Guarda se vinculam. O Primeiro Selo é precursor técnico; não representar portal dimensional explícito.

## Chefe regional

### 3.19 Vigia Partido · Chefe
**Silhueta:** guardião asteriano monumental quebrado de forma assimétrica.  
**Materiais:** pedra antiga, metal escurecido, mecanismos de Barreira incompletos.  
**Fases visuais:**
- A Sentinela: ainda legível como guardião;
- A Fratura: placas se deslocam, proteção falha, assimetria aumenta;
- O Último Posto: postura mais baixa e comprometida, mas ainda obedecendo à função de guarda.
**Tema:** uma ordem que continua depois de tudo aquilo que dava sentido à ordem ter desaparecido.  
**Evitar:** monstro do Avesso explícito; cavaleiro humano; coração luminoso genérico.

---

# 4. 🪢 VALES DOS ENFORCADOS — BIOMA VISUAL

**Faixa:** Nv.11–20.  
**Identidade:** desfiladeiros úmidos, raízes gigantes, musgo, turfa, névoa baixa, madeira escura, ruínas presas/suspensas.

> A natureza não voltou a ocupar as ruínas. Ela as aprisionou.

## 4.1 Paleta e materiais

- verdes escuros e dessaturados;
- marrom de madeira molhada;
- cinza de pedra úmida;
- turfa quase preta;
- fungos e resinas em pequenos acentos;
- névoa fria;
- água escura.

Evitar floresta feérica luminosa. Os Vales são orgânicos, sufocantes e pesados.

## 4.2 Locais

### Garganta dos Laços
Paredões altos, raízes descendentes, restos de estruturas suspensas.

### Vigília do Vale
Hub seguro; madeira, pedra, cordas, passarelas e umidade controlada.

### Mata Suspensa
Árvores inclinadas, copas conectadas, passagens em níveis diferentes, ruínas acima e abaixo das trilhas.

### Baixios Enredados
Água escura, turfa, juncos, raízes submersas, vegetação fechada.

### Claustro das Raízes
Arquitetura asteriana comprimida e atravessada por raízes; pedra antiga ainda discernível.

### Berço da Matriarca
Rede radicular monumental que converge em torno de estrutura anterior a ela; orgânico e antigo coexistem sem se fundirem completamente.

---

# 5. 🪢 VALES DOS ENFORCADOS — BESTIÁRIO VISUAL

## Criaturas-base oficiais

### 5.1 Lobo Musgoso · Comum · Predador
**Habitat principal:** Garganta/Mata.  
**Silhueta:** lobo alongado, pelo pesado pela umidade.  
**Anatomia:** musgo verdadeiro cresce em áreas do dorso e cauda, alimentado por umidade; não é lobo vegetal. Raízes não devem substituir ossos.  
**Leitura:** sangramento e bote entre raízes.  
**Evitar:** espírito da floresta, olhos verdes luminosos.

### 5.2 Gralha do Vale · Comum · Predador
Corvídeo úmido de plumagem escura com reflexos verde-musgo discretos; bico robusto, asas adequadas a voos curtos entre paredes e copas. Deve parecer oportunista e agressiva, não ave mística.

### 5.3 Peregrino Enredado · Incomum · Equilibrado
Humanoide com vestes de viagem antigas tomadas por fibras, raízes finas e cordas naturais. A vegetação limita movimentos e ajuda a justificar Laço Improvisado. Não determinar visualmente identidade individual nem fazê-lo parecer planta senciente pura.

### 5.4 Aranha de Cipó · Comum · Controlador
Aranha de pernas longas com cerdas semelhantes a fibras vegetais; fios misturam seda e fragmentos de cipó. Veneno orgânico discreto. Não é uma planta em forma de aranha.

### 5.5 Cervo do Nó · Comum · Bruto
Cervídeo grande, galhada retorcida como galhos que se encontraram e cresceram sob pressão. Pequenos nós de madeira/queratina marcam a galhada e ombros. A anatomia continua animal.

### 5.6 Sanguessuga de Turfa · Comum · Equilibrado
Sanguessuga terrestre/semiaquática grande, corpo pesado e escuro, ventosas fortes, segmentos que incham após alimentação. Não usar dentes humanos ou gore excessivo.

### 5.7 Casca Errante · Incomum · Blindado
Humanoide/organismo coberto por placas de casca grossa, com núcleo corporal ainda orgânico. Movimento lento e pesado. Deve parecer algo progressivamente encapsulado por madeira, não um ent ou árvore consciente clássica.

### 5.8 Mariposa do Breu Verde · Comum · Conjurador
Lepidóptero grande de asas verde-escuras quase negras, padrões opacos, pó visível apenas em pequena quantidade. A coloração deve sugerir breu vegetal, não bioluminescência feérica.

### 5.9 Vigia Enraizado · Incomum · Blindado
Construto asteriano com raízes atravessando juntas, torso e base. A raiz não “possui” o construto; ambos se tornaram funcionalmente integrados. Partes originais ainda claramente legíveis.

## Elites oficiais

### 5.10 Nó-Feroz · Elite · Predador
Predador canídeo mais pesado que o Lobo Musgoso, com cicatrizes nodosas e musgo espesso nos ombros. Salto do Nó deve ser legível pela potência das pernas traseiras. Não adicionar galhada.

### 5.11 Viúva dos Cipós · Elite · Controlador
Aranha alta e larga, abdômen irregular, fios grossos que se confundem com cipós. Posição de ataque frequentemente suspensa ou inclinada. Veneno e controle, não magia vegetal.

### 5.12 Carrasco de Casca · Elite · Blindado
Humanoide colossal de casca sobreposta, um braço mais pesado como lâmina/bloco natural. “Carrasco” descreve função ameaçadora; não adicionar capuz humano de executor por obrigação.

## Masmorras

### 5.13 Tecelã do Fosso · Elite
Aranha especializada em teias grossas e verticais; pernas longas para paredes de poço. Casulos discretos, sem transformar cenário inteiro em seda branca limpa.

### 5.14 O Que Pende · Chefe
Forma grande mantida acima/entre estruturas por raízes e cordas naturais. Corpo deve parecer pesado demais para sua sustentação, reforçando a ameaça de despencar. Identidade não deve virar “enforcado humano gigante”.

### 5.15 Custódio Enredado · Elite
Construto asteriano de guarda com raiz abraçando placas e pontos de articulação. Mais íntegro que Vigia Enraizado, porém profundamente incorporado à rede.

### 5.16 Prelado Enraizado · Elite
Construto/figura técnica alongada ligada a raízes de suporte. “Prelado” é nome funcional/cultural; não representar sacerdote cristão ou clérigo genérico.

### 5.17 Guardião do Nó Antigo · Chefe
Construto monumental parcialmente encerrado por raiz e pedra. O centro visual é um sistema de contenção em forma de nó estrutural, não um cristal mágico.

## Chefe regional

### 5.18 Matriarca das Raízes · Chefe
**Natureza:** criatura viva antiga integrada progressivamente à rede de raízes. Não é asteriana transformada, construto, deusa vegetal ou manifestação consciente de Âncora.  
**Silhueta:** corpo animal/organismo ancestral enorme, baixo e largo, parcialmente fundido ao leito radicular; cabeça e membros ainda discerníveis.  
**Raízes:** atravessam e sustentam partes do corpo, mas não devem substituir completamente a criatura.  
**Tema:** uma vida antiga que deixou de ser separável do ecossistema ao redor.  
**Evitar:** mulher-árvore, deusa dríade, rosto humano, coroa de flores, coração mágico exposto.

---

# 6. 🌾 PLANÍCIES DE NARETH — BIOMA VISUAL

**Faixa:** Nv.21–30.  
**Função narrativa:** revelar que as Âncoras estabilizavam o Véu.  
**Identidade:** planícies vastas, antigos eixos viários, canais secos, marcos de medição e distorções de referência espacial.

> Nas planícies, nada impede a visão — exceto aquilo que faz o horizonte mentir.

## 6.1 Paleta e materiais

- palha seca;
- verde-acinzentado;
- terra clara;
- pedra calcária/pálida;
- bronze envelhecido;
- céu grande e frio;
- acentos azul-cinza muito discretos em fenômenos de referência.

Nareth não deve parecer “deserto” nem “pradaria feliz”. O desconforto vem da abertura e da geometria errada.

## 6.2 Locais visuais

**Campinas do Meridiano:** campos de gramíneas altas cortados por linhas antigas quase retas demais.  
**Posto de Nareth:** núcleo habitado em torno de marco viário e cisternas reparadas.  
**Canais Secos:** valas de engenharia antiga, leitos rachados, pontes estreitas.  
**Campos Invertidos:** marcos apontam para direções incompatíveis; inclinações e perspectiva parecem erradas sem virar surrealismo total.  
**Observatório do Eixo:** torres baixas, instrumentos de alinhamento e grandes linhas de referência.  
**Câmara do Arconte:** arquitetura de coordenação regional, precisa e geométrica.

## 6.3 Criaturas-base — NOVO CÂNONE

### 6.3.1 Galgo do Meridiano · Comum · Predador
Canídeo esguio de planície, pernas longas, peito profundo, pelo curto cor de palha suja. Caça usando linhas abertas e perseguição. Não é cão mágico.

### 6.3.2 Abutre de Marco · Comum · Predador
Ave grande que utiliza marcos asterianos como poleiro. Penas cinza-pardas, pescoço protegido por pequenas escamas/calosidades do vento. Ataques de rasante e oportunismo.

### 6.3.3 Errante das Valas · Incomum · Equilibrado
Humanoide adaptado aos canais secos, coberto por tecidos endurecidos de poeira e tiras de couro. Origem individual incerta; não representar zumbi. Usa ferramentas/armas improvisadas e o terreno das valas.

### 6.3.4 Escaravelho de Canal · Comum · Controlador
Besouro grande de carapaça achatada capaz de se prender às paredes dos canais. Antenas longas e placas sobrepostas; secreção irritante pode dificultar movimento.

### 6.3.5 Cervo do Horizonte · Comum · Bruto
Cervídeo alto de pernas longas e galhada horizontalizada pelo vento/seleção regional. Carga em terreno aberto. Visual elegante, mas agressivo quando acuado.

### 6.3.6 Serpe das Campinas · Comum · Controlador
Serpente longa de coloração seca, corpo parcialmente enterrável entre gramíneas. Presas discretas; veneno não neon. Ataques rápidos e reposicionamento.

### 6.3.7 Casco Invertido · Incomum · Blindado
Grande quadrúpede semelhante a tartaruga terrestre/couraçado natural, com placas dorsais cuja sobreposição parece “orientada ao contrário”. A anatomia ainda deve funcionar; a estranheza é estrutural, não abstrata.

### 6.3.8 Mariposa do Eixo · Comum · Conjurador
Mariposa grande de asas pálidas com padrões lineares que lembram mapas/meridianos apenas por coincidência visual. Pó pode desorientar leitura espacial. Não usar runas escritas nas asas.

### 6.3.9 Vigia do Meridiano · Incomum · Blindado
Construto asteriano de medição e guarda. Silhueta mais alta e estreita que os Vigias do Ocaso; placas orientadas em linhas verticais/horizontais de referência. Equipamento não deve parecer telescópio moderno.

## 6.4 Elites de mundo aberto — NOVO CÂNONE

### Alfa do Horizonte · Elite · Predador
Galgo dominante de grande porte, peito largo e pernas excepcionalmente longas. Deve parecer capaz de cruzar enorme distância muito rápido sem estética sobrenatural.

### Serpe do Eixo · Elite · Controlador
Serpente massiva que vive ao redor de marcos antigos. Escamas formam faixas que parecem mudar de orientação conforme o corpo curva. Sem múltiplas cabeças.

### Custódio Invertido · Elite · Blindado
Construto cujo conjunto de placas e juntas foi reconfigurado por séculos de operação incorreta. Ainda funcional, mas certas articulações parecem montar a defesa “do lado errado”. Não é criatura do Avesso.

## 6.5 Masmorra I — Galerias do Meridiano

### Escavador do Eixo · Elite
Construto baixo e pesado de manutenção subterrânea, braços largos, ferramentas integradas de corte/remoção de material.

### O Que Retorna · Chefe
Grande organismo/constructo que percorre repetidamente o mesmo circuito das galerias e se adaptou à repetição. Silhueta circular/segmentada, com sinais físicos de múltiplos impactos nos mesmos pontos. Não é entidade temporal consciente.

## 6.6 Masmorra II — Observatório Afundado

### Custódio do Meridiano · Elite
Guardião de alinhamento, placas precisas, membros que travam em posições geométricas.

### Preceptor do Eixo · Elite
Construto de comando com múltiplos braços/instrumentos de calibração, mas sem aparência de mago.

### Guardião da Referência · Chefe
Estrutura humanoide monumental que tenta manter todas as posições “corretas”. Design com eixos, contrapesos e placas móveis; nada de globo holográfico sci-fi.

## 6.7 Chefe regional — Arconte Invertido

**Natureza:** antigo custódio técnico-administrativo da rede regional.  
**Silhueta:** construto alto, quase régio sem ser monarca; manto/placas rígidas de pedra e metal formam linhas de autoridade técnica.  
**Inversão:** componentes montados em orientações contraditórias, braços ou placas compensando direções erradas; não colocar cabeça de ponta-cabeça apenas por literalidade.  
**Tema:** uma inteligência funcional tentando corrigir aquilo que já está correto e preservar aquilo que deveria mudar.  
**Evitar:** rei fantasma, mago cósmico, entidade do Avesso explícita.

---

# 7. 🥀 VÁRZEAS CARMESINS — BIOMA VISUAL

**Faixa:** Nv.31–40.  
**Função narrativa:** revelar Projeto Hemaris e a origem ancestral das alterações Hemárias.  
**Identidade:** pântanos ferruginosos, águas avermelhadas, salmoura, juncos, instalações médico-biológicas antigas e vida adaptada a resíduos orgânicos.

> A água não lembra sangue. É o sangue que passou a lembrar a água.

## 7.1 Paleta e materiais

- ferrugem;
- vermelho escuro dessaturado;
- marrom de turfa;
- verde de junco;
- branco sujo de instalações antigas;
- metal médico oxidado;
- vidro antigo escurecido;
- sal e crostas minerais.

Evitar transformar toda a Região em carne viva ou gore. O horror é clínico, úmido e biológico, não uma “dimensão de sangue”.

## 7.2 Locais visuais

**Diques Rubros:** barragens antigas, água ferruginosa, passagens elevadas.  
**Porto da Salmoura:** assentamento moderno adaptado a cais antigos.  
**Brejos do Pulso:** juncos, bolsas de gás, água que pulsa por pressão hidráulica/biológica.  
**Hortos Hemaris:** antigos cultivos terapêuticos tomados por vegetação.  
**Galerias de Transferência:** tubos, reservatórios, canais e salas de contenção.  
**Câmara da Matriz:** estrutura biológica-técnica central, enorme, organizada, perturbadora sem ser “coração demoníaco”.

## 7.3 Criaturas-base — NOVO CÂNONE

### 7.3.1 Cão de Salmoura · Comum · Predador
Canídeo de pântano, pelo ralo e impermeabilizado por óleo natural, patas abertas, focinho longo. Caça em bordas de água. Não vampírico.

### 7.3.2 Garça Ferruginosa · Comum · Predador
Ave alta de pernas compridas, penas cinza com manchas ferruginosas. Bico forte para perfurar presas de água rasa. Elegante e inquietante, não sobrenatural.

### 7.3.3 Portador Rubro · Incomum · Equilibrado
Humanoide derivado de antigos sujeitos/funcionários ou descendências alteradas locais, profundamente deteriorado por exposição ambiental específica. **Não representa Hemários modernos.** Pele com alterações vasculares e vestes clínicas/operárias em farrapos. Não usar presas vampíricas.

### 7.3.4 Aranha de Junco · Comum · Controlador
Aranha de pernas finas adaptadas a vegetação aquática, abdômen achatado, fios entre juncos. Toxinas discretas.

### 7.3.5 Cervo Ferrugem · Comum · Bruto
Cervídeo pesado de pântano, pelo castanho-avermelhado por minerais, galhada curta e grossa para vegetação fechada.

### 7.3.6 Lampreia de Várzea · Comum · Equilibrado
Peixe/organismo semiaquático comprido, boca circular funcional, corpo escuro com listras ferruginosas. Pode mover-se brevemente em lama úmida. Não gigante grotesco por padrão.

### 7.3.7 Enxerto de Horto · Incomum · Blindado
Organismo criado originalmente como cultura biológica de suporte e regeneração, hoje crescido de forma autônoma. Corpo vegetal-carnoso protegido por fibras e casca. Não é pessoa transformada nem Hemário.

### 7.3.8 Mariposa de Soro · Comum · Conjurador
Mariposa pálida, asas semitranslúcidas com manchas cor de ferrugem; escamas carregam compostos irritantes e resíduos dos Hortos.

### 7.3.9 Vigia Hemaris · Incomum · Blindado
Construto/estrutura móvel de segurança de instalações Hemaris. Design asteriano, porém adaptado a ambientes clínicos: placas menores, superfícies laváveis antigas, suportes para contenção. Não deve parecer médico humano.

## 7.4 Elites — NOVO CÂNONE

### Alfa de Salmoura · Elite · Predador
Canídeo massivo de pântano, pescoço espesso, cicatrizes de mordida, patas largas. Sem estética de “cão de sangue”.

### Viúva Rubra · Elite · Controlador
Aranha de junco enorme, abdômen escuro com marcas ferruginosas, teias impregnadas de lama e compostos tóxicos. Vermelho deve ser mineral/orgânico, não neon.

### Coletor Hemático · Elite · Blindado
Antigo sistema móvel do Projeto Hemaris destinado a recolher/transportar material biológico. Estrutura asteriana com reservatórios opacos, mangueiras antigas e membros de contenção. Horror técnico, não robô moderno.

## 7.5 Masmorra I — Enfermaria Afundada

### Transfundido · Comum
Antigo sujeito profundamente alterado por protocolos locais e séculos de exposição. Humanoide reconhecível, porém assimétrico e debilitado. Não confundir com Hemário moderno.

### Curador Vazio · Elite
Sistema automatizado de tratamento sem paciente válido: braços de suporte, placas clínicas, instrumentos contundentes/cauterizantes. Não tem rosto humano.

### O Persistente · Chefe
Organismo antigo que sobreviveu graças a protocolos repetidos de manutenção. Corpo reúne cicatrizes de intervenções sucessivas e suportes médicos antigos. Tema: continuidade sem capacidade de terminar.

## 7.6 Masmorra II — Cisterna de Transferência

### Condutor Rubro · Elite
Estrutura móvel que regula fluxo entre reservatórios; corpo segmentado, tubos grossos, válvulas antigas.

### Executor de Hemaris · Elite
Unidade de contenção e emergência, não carrasco moral. Construção compacta e pesada, projetada para imobilizar incidentes biológicos.

### Coração de Transferência · Chefe
Nó biotécnico móvel/semi-fixo de bombeamento e redistribuição. Não é coração literal gigante; pode possuir câmaras pulsantes cercadas por estrutura metálica.

## 7.7 Chefe regional — Matriz Rubra

**Natureza:** sistema biológico central de regulação do Projeto Hemaris.  
**Silhueta:** massa arquitetônica viva organizada por anéis, reservatórios, membranas espessas, estruturas metálicas e canais de transferência.  
**Presença:** deve parecer uma instalação que aprendeu a continuar operando sem supervisão, não um monstro que foi colocado numa sala.  
**Tema:** preservar vida até que vida se torne apenas recurso operacional.  
**Evitar:** deusa de sangue, vampira gigante, coração anatômico simples, “mãe dos Hemários”.

---

# 8. ⛰️ ALTOS CINÉREOS — BIOMA VISUAL

**Faixa:** Nv.41–50.  
**Função narrativa:** revelar Regência de Continuidade, Convergência e sabotagem Desvelada.  
**Identidade:** montanhas, vento, cinza mineral, basaltos, pedreiras, pontes, contrapesos, instalações de sustentação e arquitetura feita para suportar cargas extremas.

> Nos Altos, tudo que permanece o faz porque alguma coisa ainda suporta o peso.

## 8.1 Paleta e materiais

- grafite;
- cinza mineral;
- basalto quase negro;
- aço/ferro envelhecido;
- pano grosso desbotado;
- pó claro de pedreira;
- raros acentos quentes de fornalha/atrito.

Não transformar a Região em vulcão ativo nem fazer a raça Cinérea controlar pedra.

## 8.2 Locais visuais

**Escarpa da Cinza:** paredões, trilhas estreitas, vento forte.  
**Abrigo do Peso:** hub moderno incrustado em arquitetura de sustentação antiga.  
**Pontes de Fuligem:** pontes suspensas e contrapesos enormes.  
**Pedreiras Suspensas:** cortes de montanha e plataformas abandonadas.  
**Bastilha de Carga:** complexo de controle emergencial.  
**Coração do Colosso:** núcleo estrutural de manutenção e sustentação.

## 8.3 Criaturas-base — NOVO CÂNONE

### 8.3.1 Lobo de Escarpa · Comum · Predador
Canídeo compacto, patas curtas e fortes, garras para pedra, pelo denso cinza-pardo. Deve parecer adaptado a subida, não lobo de gelo.

### 8.3.2 Abutre da Fuligem · Comum · Predador
Ave de grande envergadura usando correntes ascendentes. Penas escuras e gastas, bico espesso. Não repetir visual do Corvo/Gralha.

### 8.3.3 Escaravelho de Basalto · Comum · Blindado
Besouro robusto com carapaça semelhante a rocha por textura e deposição mineral, não literalmente feito de pedra.

### 8.3.4 Carneiro do Peso · Comum · Bruto
Caprino de montanha largo, chifres baixos e grossos, musculatura de ombros muito marcada. Carga em terreno estreito.

### 8.3.5 Lagarto de Escória · Comum · Equilibrado
Réptil baixo de rocha quente/fria, escamas escuras e ásperas, cauda forte. Não cospe lava.

### 8.3.6 Morcego de Chaminé · Comum · Predador
Morcego grande de orelhas curtas, asas espessas e escuras; habita dutos, fendas e antigas chaminés técnicas.

### 8.3.7 Carcaça Mineral · Incomum · Blindado
Organismo antigo progressivamente mineralizado por ambiente e resíduos, ainda com partes orgânicas discerníveis. Não é golem nem morto-vivo.

### 8.3.8 Quebra-Cabos · Comum · Controlador
Artrópode/roedor de grande porte que se alimenta de fibras, couro, musgo e isolantes antigos; mandíbulas capazes de cortar cordas e cabos. Corpo baixo para atravessar estruturas.

### 8.3.9 Vigia de Carga · Incomum · Blindado
Construto asteriano robusto de manutenção/proteção. Ombros e braços largos, pontos de fixação para correntes/contrapesos. Visual industrial medieval, nunca sci-fi.

## 8.4 Elites — NOVO CÂNONE

### Quebra-Escarpas · Elite · Bruto
Carneiro colossal com chifres marcados por lascas de pedra, cicatrizes frontais e corpo baixo. Não adicionar metal natural aos chifres.

### Devorador de Escória · Elite · Predador
Lagarto enorme de mandíbula larga, placas dorsais irregulares e marcas de calor/abrasão. Não dragão.

### Supervisor de Carga · Elite · Blindado
Construto de comando/controle, com estrutura central alta e braços auxiliares para travas, correntes e mecanismos. Autoridade técnica, não oficial militar humano.

## 8.5 Masmorra I — Pedreira do Contrapeso

### Operário Petrificado · Comum
Figura humanoide antiga parcialmente mineralizada e incorporada a equipamento de trabalho. Não confirmar morto-vivo; ferramentas e arreios antigos contam a história.

### Prensor Antigo · Elite
Máquina móvel de compactação/ancoragem, corpo largo, placas de pressão e pernas curtas.

### Peso sem Fim · Chefe
Estrutura de contrapeso que adquiriu ciclo autônomo e desloca massa enorme. Visual de blocos, correntes e carro estrutural; não criatura de pedra com rosto.

## 8.6 Masmorra II — Bastilha Profunda

### Custódio de Ponte · Elite
Guardião alto com braços capazes de travar passagens e placas que lembram parapeitos móveis.

### Coordenador de Carga · Elite
Construto de coordenação emergencial menor, com placas de comando, selos técnicos e múltiplos pontos de conexão.

### Guardião do Contrapeso · Chefe
Construto monumental cuja própria postura distribui forças por cabos/ancoragens. Visual deve comunicar “segurar o complexo” mesmo parado.

## 8.7 Chefe regional — Colosso Cinéreo

**Natureza:** construção asteriana feita para sustentar e proteger grande complexo regional durante crises. Não criou nem representa biologicamente os Cinéreos.  
**Silhueta:** colossal humanoide/arquitetônica, costas largas como contrafortes, pernas como pilares, braços de sustentação e placas mineralizadas.  
**Materiais:** pedra, metal, cinza compactada, séculos de depósitos minerais.  
**Tema:** algo construído para suportar peso que nunca recebeu ordem de largá-lo.  
**Evitar:** gigante elemental de pedra, deus dos Cinéreos, ancestral racial, lava viva.

---

# 9. 🌫️ CONFINS DO VÉU — BIOMA VISUAL

**Faixa:** Nv.51–60.  
**Função narrativa:** revelar Fraturas, Avesso e a verdadeira cadeia da Ruptura.  
**Identidade:** névoa, continuidade falha, arquitetura parcialmente contraditória, caminhos que parecem ocupar duas posições e natureza que conserva versões incompatíveis de si.

> Nos Confins, o mundo continua inteiro principalmente quando observado de longe.

## 9.1 Paleta e materiais

- cinza pálido;
- azul dessaturado;
- pedra quase branca;
- preto profundo em recessos;
- verde muito frio em vegetação rara;
- pequenos desvios cromáticos em duplicações/Fraturas.

Não transformar os Confins em galáxia, espaço sideral ou dimensão roxa neon. O estranho deve parecer **quase normal**.

## 9.2 Regra visual de distorção

Priorizar:

- duplicação parcial;
- simetria errada;
- anatomia com “eco” físico discreto;
- partes que parecem ter ocupado outra posição;
- desgaste incompatível entre lados do mesmo objeto;
- padrões repetidos com pequena diferença.

Evitar:

- glitch digital;
- pixels quebrados como estética interna da criatura;
- hologramas;
- tentáculos cósmicos genéricos;
- estrelas dentro do corpo.

## 9.3 Locais visuais

**Marcha Nebulosa:** estradas e marcos aparecem e desaparecem na névoa.  
**Último Refúgio:** assentamento que reforça constantemente sua orientação e registro.  
**Estradas Ausentes:** trechos de caminho terminam em terreno que parece nunca tê-los possuído.  
**Fraturas do Limiar:** falhas veláricas abertas e observáveis.  
**Nó Central:** estruturas de coordenação danificadas.  
**Câmara da Regência:** restos do centro de decisão e da referência central.

## 9.4 Criaturas-base — NOVO CÂNONE

### 9.4.1 Cão de Névoa · Comum · Predador
Canídeo magro de pelo muito claro e úmido, focinho longo, olhos normais. Sua borda corporal pode parecer duplicada em pequenos pontos por instabilidade local; ele continua um animal real.

### 9.4.2 Gralha de Duas Sombras · Comum · Predador
Ave escura cujas penas de um lado apresentam desgaste diferente do outro, como se duas histórias ambientais tivessem sido sobrepostas. Em arte isolada, sugerir segunda leitura por pequena duplicação de penas/contorno, não sombra desenhada obrigatória.

### 9.4.3 Andarilho Repetido · Incomum · Equilibrado
Humanoide cuja roupa e corpo exibem dois estados próximos sobrepostos: rasgo intacto ao lado do mesmo rasgo costurado, mão com leve eco posicional, objeto repetido parcialmente. Não é clone nem fantasma.

### 9.4.4 Aranha de Limiar · Comum · Controlador
Aracnídeo de pernas muito finas com pares que parecem divergir por alguns graus impossíveis. O corpo ainda possui anatomia central coerente.

### 9.4.5 Cervo de Passo Duplo · Comum · Bruto
Cervídeo alto com articulações marcadas por duplicações sutis de cascos/joelhos, como posições consecutivas registradas ao mesmo tempo. Não dar oito pernas completas.

### 9.4.6 Sanguessuga Pálida · Comum · Equilibrado
Organismo semiaquático translúcido apenas o suficiente para sugerir órgãos em posições levemente incompatíveis. Não tornar gelatina cósmica.

### 9.4.7 Casca de Reflexo · Incomum · Blindado
Humanoide/organismo com placas rígidas que repetem formas de partes vizinhas do corpo, como se a proteção tivesse “copiado” estrutura incorreta. Material físico real.

### 9.4.8 Mariposa sem Horizonte · Comum · Conjurador
Asas largas com padrões de perspectiva que parecem convergir para pontos diferentes. Corpo normal de inseto; o desconforto vem do padrão, não de energia brilhante.

### 9.4.9 Vigia Desfasado · Incomum · Blindado
Construto asteriano cujas placas e braços não ocupam perfeitamente a mesma referência espacial. Uma articulação pode apresentar duas posições sobrepostas por pequena distância. Ainda é claramente uma máquina/guardião físico.

## 9.5 Elites — NOVO CÂNONE

### Predador de Duas Pegadas · Elite · Predador
Canídeo grande cujo deslocamento deixa pequenas incongruências físicas no próprio corpo: patas em posições ligeiramente duplicadas, pelo orientado por dois ventos. Não usar transparência de fantasma.

### Viúva de Intervalo · Elite · Controlador
Aranha grande com abdômen aparentemente interrompido por uma faixa de espaço onde a anatomia “salta” alguns centímetros; a conexão continua implícita/funcional. Deve parecer erro de continuidade, não corpo cortado com gore.

### Custódio Desfasado · Elite · Blindado
Construto superior com duas configurações defensivas parcialmente coexistindo. Placas duplicadas/interpenetradas de forma limpa e inquietante.

## 9.6 Masmorra I — Arquivo do Retorno

### Eco sem Origem · Comum
Forma humanoide produzida por repetição de registro/estado, com roupa e equipamento incompletos. Não afirmar que é alma de uma pessoa específica.

### Guardião do Retorno · Elite
Construto que recompõe postura anterior repetidamente; visual com peças em duas posições possíveis, mas estrutura central sólida.

### O Que Chega Antes · Chefe
Criatura/eco cuja anatomia frontal parece ligeiramente mais “antiga” que a traseira, como se partes diferentes ocupassem instantes adjacentes. Silhueta quadrúpede ou humanoide maciça, claramente visualizável; não abstração de tempo pura.

## 9.7 Masmorra II — Câmara das Contradições

### Custódio do Nó Central · Elite
Guardião de alta hierarquia, placas de coordenação e pontos de conexão rompidos. Design asteriano central, severo.

### Preceptor de Contradição · Elite
Construto técnico cuja função era reconciliar leituras incompatíveis; agora mantém duas ordens ao mesmo tempo. Dois conjuntos parciais de braços/placas podem coexistir.

### Testemunha Impossível · Chefe
Manifestação ligada a registros incompatíveis da Ruptura. Humanoide alto coberto por camadas de placas/documentos/fragmentos de inscrição que contam versões mutuamente contraditórias. Não é entidade onisciente nem deus do tempo.

## 9.8 Chefe regional — Regente Fraturado

**Origem:** manifestação formada pela sobreposição de fragmentos de Cael Rhen, registros, protocolos da Regência, matéria local e estados do Avesso. Não é Cael Rhen simplesmente vivo ou ressuscitado.  
**Silhueta:** humanoide alto de autoridade asteriana, manto/placas administrativas quebradas, corpo dividido em estados parcialmente incompatíveis.  
**Rosto:** pode preservar traços humanos incompletos em uma das leituras, mas nunca rosto perfeitamente vivo; outras áreas parecem substituídas por placa, vazio físico ou repetição.  
**Tema:** a última decisão de uma civilização tentando continuar depois de a própria referência ter falhado.  
**Evitar:** lich, demônio, mago do vazio, imperador maligno, universo estrelado dentro do corpo, glitch digital.

---

# 10. DISTRIBUIÇÃO ECOLÓGICA E LEITURA DAS REGIÕES

## Terras do Ocaso
Fauna ressecada + predadores oportunistas + humanoides ambíguos + primeiros construtos asterianos.

## Vales dos Enforcados
Fauna úmida + adaptação vegetal + organismos de turfa + construtos progressivamente integrados às raízes.

## Planícies de Nareth
Fauna de campo aberto + criaturas de canais + primeiros efeitos de referência espacial + construtos de medição/alinhamento.

## Várzeas Carmesins
Fauna de pântano + resíduos biológicos + legados experimentais + sistemas Hemaris abandonados.

## Altos Cinéreos
Fauna de montanha + mineralização + criaturas adaptadas a infraestrutura pesada + construtos de sustentação/carga.

## Confins do Véu
Fauna ainda reconhecível + organismos fraturados + Ecos + construtos desfasados + manifestações de continuidade falha.

A progressão visual deve acompanhar a progressão narrativa: o jogo começa com alterações plausíveis e ruínas; somente nas últimas Regiões a própria coerência do mundo se torna visualmente instável.

---

# 11. REGRAS PARA REFazer SKINS

Para cada criatura, o prompt mestre pode consumir os seguintes campos deste documento:

1. **Nome canônico**  
2. **Região/bioma**  
3. **Categoria e arquétipo**  
4. **Silhueta**  
5. **Anatomia**  
6. **Materiais/superfícies**  
7. **Escala**  
8. **Leitura combatente**  
9. **Sinais regionais obrigatórios**  
10. **Proibições visuais**

## 11.1 Regra de fundo para skin isolada

Quando a imagem for destinada a skin/Bestiário:

- criatura inteira visível;
- centralizada;
- margem segura ao redor;
- pose que demonstre anatomia e papel, sem esconder membros essenciais;
- perspectiva consistente entre criaturas do mesmo catálogo;
- fundo simples/transparente ou muito discreto conforme pipeline visual;
- não incorporar cenário complexo à skin;
- sinais de bioma devem estar NO CORPO/vestimenta/material da criatura, e não depender de uma paisagem atrás dela.

## 11.2 Consistência entre Base e Variante

Uma Variante deve reutilizar:

- mesma espécie;
- mesma anatomia central;
- mesmos elementos canônicos;
- mesma família de proporções.

Alterar apenas aquilo que comunica o modificador.

## 11.3 Consistência entre criatura e Elite relacionada

Elite não deve parecer recolor da criatura comum. Reforçar:

- idade;
- massa;
- cicatrização;
- especialização anatômica;
- comportamento;
- relação com habitat.

## 11.4 Construtos

Todos os construtos asterianos devem compartilhar DNA visual suficiente para o jogador perceber parentesco antes de compreender sua função histórica.

Esse parentesco deve vir de:

- geometria;
- juntas;
- placas;
- materiais;
- linguagem de inscrição;
- proporções funcionais.

Não usar o mesmo modelo corporal para todos.

---

# 12. CATÁLOGO RESUMIDO POR REGIÃO

## 🌑 Terras do Ocaso
**Base:** Cão Cinéreo; Corvo de Fuligem; Peregrino Calcinado; Aranha de Cinza; Cervo Escoriado; Carniçal de Fuligem; Mariposa de Brasa; Vigia Rachado; Custódio Sem Rosto.  
**Elites:** Alfa Cinéreo; Viúva da Fuligem; Custódio do Poente.  
**Chefe de Missão:** Guardião do Último Rastro · S6.  
**Cripta:** Profanador Calcinado; Guardião das Lápides; O Sem-Nome.  
**Galerias:** Vigia Íntegro; Preceptor Rachado; Custódio do Primeiro Selo.  
**Regional:** Vigia Partido.

## 🪢 Vales dos Enforcados
**Base:** Lobo Musgoso; Gralha do Vale; Peregrino Enredado; Aranha de Cipó; Cervo do Nó; Sanguessuga de Turfa; Casca Errante; Mariposa do Breu Verde; Vigia Enraizado.  
**Elites:** Nó-Feroz; Viúva dos Cipós; Carrasco de Casca.  
**Masmorras:** Tecelã do Fosso; O Que Pende; Custódio Enredado; Prelado Enraizado; Guardião do Nó Antigo.  
**Regional:** Matriarca das Raízes.

## 🌾 Planícies de Nareth
**Base:** Galgo do Meridiano; Abutre de Marco; Errante das Valas; Escaravelho de Canal; Cervo do Horizonte; Serpe das Campinas; Casco Invertido; Mariposa do Eixo; Vigia do Meridiano.  
**Elites:** Alfa do Horizonte; Serpe do Eixo; Custódio Invertido.  
**Galerias do Meridiano:** Escavador do Eixo; O Que Retorna.  
**Observatório Afundado:** Custódio do Meridiano; Preceptor do Eixo; Guardião da Referência.  
**Regional:** Arconte Invertido.

## 🥀 Várzeas Carmesins
**Base:** Cão de Salmoura; Garça Ferruginosa; Portador Rubro; Aranha de Junco; Cervo Ferrugem; Lampreia de Várzea; Enxerto de Horto; Mariposa de Soro; Vigia Hemaris.  
**Elites:** Alfa de Salmoura; Viúva Rubra; Coletor Hemático.  
**Enfermaria Afundada:** Transfundido; Curador Vazio; O Persistente.  
**Cisterna de Transferência:** Condutor Rubro; Executor de Hemaris; Coração de Transferência.  
**Regional:** Matriz Rubra.

## ⛰️ Altos Cinéreos
**Base:** Lobo de Escarpa; Abutre da Fuligem; Escaravelho de Basalto; Carneiro do Peso; Lagarto de Escória; Morcego de Chaminé; Carcaça Mineral; Quebra-Cabos; Vigia de Carga.  
**Elites:** Quebra-Escarpas; Devorador de Escória; Supervisor de Carga.  
**Pedreira do Contrapeso:** Operário Petrificado; Prensor Antigo; Peso sem Fim.  
**Bastilha Profunda:** Custódio de Ponte; Coordenador de Carga; Guardião do Contrapeso.  
**Regional:** Colosso Cinéreo.

## 🌫️ Confins do Véu
**Base:** Cão de Névoa; Gralha de Duas Sombras; Andarilho Repetido; Aranha de Limiar; Cervo de Passo Duplo; Sanguessuga Pálida; Casca de Reflexo; Mariposa sem Horizonte; Vigia Desfasado.  
**Elites:** Predador de Duas Pegadas; Viúva de Intervalo; Custódio Desfasado.  
**Arquivo do Retorno:** Eco sem Origem; Guardião do Retorno; O Que Chega Antes.  
**Câmara das Contradições:** Custódio do Nó Central; Preceptor de Contradição; Testemunha Impossível.  
**Regional:** Regente Fraturado.

---

# 13. ESTADO DE FECHAMENTO

Com esta Bíblia Visual ficam fechados, para fins de Lore e geração de assets:

- identidade visual dos seis biomas;
- progressão estética entre as Regiões;
- catálogo de criaturas-base das seis Regiões;
- três Elites de mundo aberto por Região;
- criaturas-chave de duas Masmorras por Região;
- todos os seis Chefes regionais;
- linguagem visual de construtos asterianos;
- linguagem visual de Variantes;
- limites para humanos alterados/Ecos;
- proibições contra leituras erradas de Hemários, Velados, Cinéreos, Avesso e tecnologia asteriana;
- campos necessários para transformar cada entrada em prompt de skin padronizado.

## Observação de implementação

Nas Regiões 1–2, categorias, habitats, kits, variantes e demais mecânicas já existentes continuam sendo definidos pelas Fontes Regionais oficiais.  
Nas Regiões 3–6, este documento fecha **nome, identidade, ecologia e direção visual** das criaturas; números de combate, pools, pesos, drops e IA detalhada deverão ser consolidados quando as respectivas Fontes Regionais mecânicas forem produzidas, sem alterar a identidade visual aqui estabelecida.

---

# DOCUMENTO INCORPORADO 3/9
## Arquivo original: `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md`
# ASTERION — BÍBLIA VISUAL DE AMBIENTES, LOCAIS E MASMORRAS v1.0

**Estado:** Fonte visual/literária complementar para produção de cenários, imagens contextuais, fundos, telas de Local e Masmorras.  
**Escopo:** seis Regiões de Asterion, seus Locais principais, hubs, clímax regionais, Masmorras, identidade ambiental, arquitetura, história visual, limites de spoiler e invariantes de geração.  
**Complementa:** `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`.

**Não substitui:** Fonte Mestra, Fontes Regionais FINAL de Terras do Ocaso e Vales dos Enforcados, nem Fonte Visual/UI vigente.

> **Regra de autoridade:** em Terras do Ocaso e Vales dos Enforcados, nomes, progressão, conteúdo e revelações seguem as Fontes Regionais vigentes. Nas Regiões 3–6, este documento fecha a identidade literária/visual e a geografia de produção aprovada nesta frente de Lore, sem antecipar números de Balanceamento ou implementação.

---

# 1. PRINCÍPIOS VISUAIS GLOBAIS DE ASTERION

## 1.1 Tom

Asterion é dark fantasy medieval de decadência, permanência e ruína funcional.

Os cenários devem transmitir:
- mundo antigo ainda presente;
- vida moderna construída entre restos;
- beleza contida, nunca fantasia exuberante sem custo;
- abandono parcial, não ausência total de pessoas;
- estruturas com função anterior discernível;
- mistério por contexto, não por excesso de símbolos indecifráveis.

Evitar:
- fantasia genérica de parque temático;
- excesso de runas brilhantes em toda superfície;
- tecnologia sci-fi limpa;
- arquitetura impossível apenas para parecer “mágica”;
- ruínas sem função reconhecível;
- saturação exagerada;
- horror cósmico explícito antes dos Confins;
- estética infernal por padrão.

## 1.2 Civilização asteriana — linguagem arquitetônica

A arquitetura asteriana deve parecer:
- planejada;
- funcional;
- durável;
- modular;
- integrada ao terreno;
- feita para manutenção e continuidade.

Materiais recorrentes:
- pedra cortada de grandes blocos;
- metal escurecido ou bronze envelhecido;
- encaixes mecânicos;
- canais;
- trilhos, fendas ou juntas funcionais;
- placas de orientação e marcação;
- contrafortes;
- corredores de serviço;
- câmaras com propósito claro.

Não usar:
- telas eletrônicas;
- hologramas;
- neon;
- cabos plásticos;
- circuitos modernos;
- arquitetura alienígena orgânica sem motivo;
- “runa = eletricidade” como atalho visual.

Asterianos não eram uma civilização sci-fi escondida sob fantasia medieval.

## 1.3 Construções modernas

Comunidades atuais reaproveitam:
- madeira;
- pedra local;
- metal recuperado;
- couro;
- tecido;
- corda;
- restos asterianos quando seguros.

O contraste deve ser legível:
- antigo = preciso, integrado e durável;
- moderno = reparado, adaptado, remendado, vivido.

## 1.4 Escala

Asterion não exige monumentalidade constante.

A escala deve crescer com a narrativa:
- Terras do Ocaso: estrada, abrigo, ruína defensiva.
- Vales: natureza sufocando estruturas.
- Nareth: território e horizonte.
- Várzeas: infraestrutura biológica.
- Altos: peso e engenharia monumental.
- Confins: falha da própria continuidade espacial.

## 1.5 Spoilers visuais

A imagem jamais deve revelar por si só uma verdade que a narrativa ainda não permitiu.

Exemplos:
- Âncora do Poente não deve mostrar “estabilizando o Véu” visualmente antes da revelação.
- Vales não devem exibir mapas claros da rede global.
- Nareth pode revelar função de estabilização apenas depois do gate narrativo correspondente.
- Hemaris não deve ser antecipado visualmente nas Regiões 1–3.
- Desvelados e Convergência não devem aparecer como informação explícita antes dos Altos.
- Avesso não deve aparecer diretamente antes dos Confins.

---

# 2. 🌑 TERRAS DO OCASO

**Faixa:** Nv.1–10  
**Chefe regional:** Vigia Partido  
**Função narrativa:** apresentar sobrevivência, ruína asteriana e o primeiro nome “Âncora”, sem revelar sua função.  
**Fantasia central:** uma estrada que continua depois de o mundo que a construiu ter acabado.

## 2.1 Identidade regional

Terras secas cobertas por cinza fina e fuligem antiga.

Não são um deserto vulcânico ativo. O fogo pertence ao passado.

Elementos:
- céu frio e opaco;
- luz difusa;
- campos mortos;
- arbustos ressecados;
- pedra enegrecida;
- árvores carbonizadas;
- marcos viários antigos;
- pequenas ruínas;
- vento baixo carregando cinza;
- brasas raras em matéria ainda reagente.

Paleta:
- cinza frio;
- carvão;
- marrom seco;
- ferrugem;
- bege morto;
- âmbar muito discreto.

Sensação:
> algo aconteceu aqui há muito tempo, mas o lugar ainda não terminou de esfriar.

## 2.2 História ambiental

As Terras do Ocaso já foram atravessadas por rotas e estruturas asterianas de guarda.

Depois da Ruptura:
- incêndios e falhas estruturais devastaram grandes áreas;
- rotas perderam manutenção;
- comunidades diminuíram;
- peregrinos continuaram atravessando a região;
- alguns sistemas antigos permaneceram ativos.

A Região deve sugerir civilização perdida antes de explicar sua escala.

---

## 2.3 Estrada das Cinzas

**Tipo:** Local inicial / rota aberta.

### Aparência
Estrada antiga de pedra parcialmente soterrada por cinza. Em alguns pontos, apenas alinhamentos de pedras laterais denunciam que já houve pavimentação completa.

Elementos:
- marco de pedra gasto;
- cercas ou postes quebrados;
- campos secos;
- ruínas de pequenos abrigos;
- braseiro distante;
- pegadas e sulcos recentes;
- horizonte amplo.

### Lore visual
A estrada deve parecer ainda utilizável porque pessoas continuam escolhendo utilizá-la, não porque alguém a mantém formalmente.

### Atmosfera
Solidão, começo de jornada, perigo moderado, possibilidade de abrigo ao longe.

### Evitar
- cadáveres em excesso;
- campo de batalha ativo;
- floresta fechada;
- lava;
- cidade destruída ocupando toda a cena.

---

## 2.4 Refúgio do Ocaso

**Tipo:** hub seguro.

### Aparência
Assentamento pequeno construído em torno de estruturas reaproveitadas e madeira nova.

Elementos:
- paliçadas simples;
- oficinas;
- coberturas de tecido;
- depósitos;
- pedra antiga incorporada a construções recentes;
- Braseiro como referência comunitária;
- sinais de viajantes.

### Lore visual
O Refúgio não é capital nem fortaleza.

É um lugar que sobrevive porque:
- pessoas mantêm rotas;
- artesãos consertam;
- vigias observam;
- registros são preservados.

### Sensação
Segurança relativa, trabalho cotidiano e continuidade.

### Evitar
- castelo;
- catedral;
- grande muralha;
- cidade rica;
- estética de acampamento temporário descartável.

---

## 2.5 Charneca da Fuligem

**Tipo:** campo hostil aberto.

### Aparência
Terreno irregular e exposto, com:
- montes de fuligem;
- depressões;
- arbustos secos;
- pedras marcadas;
- bolsões de solo escuro;
- cinza acumulada em ondulações.

### Lore visual
Resíduos persistem em pontos onde matéria orgânica e química não se degradou completamente.

A Charneca é onde o jogador percebe:
> a cinza não é apenas clima; ela preserva histórias.

### Assinatura
Pedras marcadas e vestígios devem parecer intencionais sem explicar autoria/função.

### Evitar
- pântano;
- dunas de areia;
- fogo ativo por toda parte;
- runas brilhantes explícitas.

---

## 2.6 Cripta do Ocaso

**Tipo:** Masmorra · entrada pela Charneca.

### Função histórica aparente
Complexo funerário reutilizado ao longo de períodos diferentes.

A Fonte Regional fixa associações com:
- Camadas de Sepultamento;
- Câmara dos Nomes;
- O Último Guardião;
- Os Sem-Nome.

### Arquitetura
- corredores estreitos;
- câmaras de pedra;
- nichos funerários;
- lápides ou placas gastas;
- inscrições parcialmente raspadas;
- ampliações feitas em épocas diferentes;
- fuligem infiltrada por fendas.

### Progressão visual
1. **Vestíbulo Raspado:** entrada danificada, inscrições removidas, ferramentas abandonadas.
2. **Ossário da Fuligem:** nichos e restos reorganizados pela passagem de saqueadores/profanadores.
3. **Galerias dos Nomes:** placas pessoais, marcas de identificação, nomes parcialmente apagados.
4. **Câmara dos Nomes:** maior concentração de registros funerários.
5. **Câmara de O Sem-Nome:** espaço onde identidade e memória social são o tema, não necromancia genérica.

### Lore
A Cripta não prova vida após a morte.

Seu horror vem da perda de identidade e da violação de memória.

### Evitar
- necromante sentado em trono;
- energia verde de morto-vivo;
- cemitério gótico genérico;
- cruzes ou religião real;
- inferno subterrâneo.

---

## 2.7 Bosque Calcinado

**Tipo:** floresta morta / transição intermediária.

### Aparência
- troncos negros;
- galhos secos;
- raízes expostas;
- clareiras de cinza;
- brasa residual rara;
- vegetação baixa tentando retornar em pontos isolados.

### Lore visual
O Bosque queimou no passado. Sua identidade é o que restou.

A floresta não está constantemente pegando fogo.

### Sensação
Espaço mais fechado que a Charneca, som abafado, predadores próximos.

### Evitar
- floresta tropical;
- folhas verdes abundantes;
- incêndio florestal ativo;
- “floresta demoníaca”.

---

## 2.8 Ruínas do Vigia

**Tipo:** complexo defensivo asteriano.

### Aparência
- torres quebradas;
- pátios;
- corredores defensivos;
- muros de pedra escura;
- passagens estreitas;
- mecanismos de guarda;
- marcas de patrulha;
- áreas reutilizadas por ocupação posterior.

### Lore visual
A função defensiva deve ser compreensível.

O jogador pode deduzir:
> alguém guardava alguma coisa.

Ainda não:
> por que aquilo era cosmologicamente importante.

### Evitar
- palácio;
- templo;
- laboratório sci-fi;
- mural explicando a Convergência.

---

## 2.9 Galerias do Vigia

**Tipo:** Masmorra · entrada pelas Ruínas do Vigia.

### Função histórica
Rede interior de defesa, manutenção e contenção.

A Fonte Regional associa:
- Rede de Defesa;
- Câmara de Contenção;
- Primeiro Selo;
- Ordens que Permanecem.

### Arquitetura
- corredores de guarda;
- junções;
- portas de contenção;
- nichos de mecanismos;
- áreas de manutenção;
- placas de ordem;
- estruturas que ainda respondem.

### Progressão visual
1. **Corredor de Guarda:** desenho austero, estreito, controlável.
2. **Junção dos Vigias:** cruzamento com diferentes rotas de patrulha.
3. **Câmara de Vigia Íntegro:** estrutura menos degradada.
4. **Câmara de Contenção:** travas, placas e elementos defensivos.
5. **Primeiro Selo:** construção antiga de contenção, sem ainda explicar o que era “selado”.

### Lore
As máquinas não devem parecer conscientes.

Elas executam rotinas.

### Evitar
- robôs futuristas;
- inteligência artificial holográfica;
- portal dimensional explícito;
- arquitetura religiosa.

---

## 2.10 Câmara do Poente

**Tipo:** Local de clímax regional.

### Aparência
Câmara monumental asteriana, mais intacta e deliberada que as Ruínas exteriores.

Elementos:
- geometria funcional;
- plataformas;
- estruturas de sustentação;
- grande mecanismo central parcialmente oculto;
- sinais de guarda;
- pedra e metal escurecidos.

### Lore
Depois do clímax, o jogador aprende o nome:
**Âncora do Poente**.

A imagem não deve revelar:
- Véu estabilizado;
- Avesso;
- Convergência;
- rede mundial.

### Evitar
- esfera cósmica;
- rachadura dimensional explícita;
- mapa luminoso das seis Regiões.

---

# 3. 🪢 VALES DOS ENFORCADOS

**Faixa:** Nv.11–20  
**Chefe regional:** Matriarca das Raízes  
**Função narrativa:** provar que as estruturas antigas não eram isoladas.  
**Fantasia central:** a natureza não reconquistou as ruínas; aprisionou-as.

## 3.1 Identidade regional

Desfiladeiros úmidos e profundos.

Elementos:
- paredões;
- raízes gigantes;
- árvores inclinadas;
- musgo;
- água escura;
- turfa;
- névoa baixa;
- passarelas;
- ruínas suspensas.

Paleta:
- verde escuro;
- marrom molhado;
- cinza úmido;
- preto de turfa;
- névoa azul-cinza;
- resina âmbar discreta.

### Sensação
Peso orgânico, umidade, estrangulamento e profundidade.

### Evitar
- floresta feérica luminosa;
- cogumelos neon;
- “selva” tropical;
- árvores conscientes com rostos.

---

## 3.2 Garganta dos Laços

Passagem de entrada entre paredões altos.

Elementos:
- raízes descendo das paredes;
- restos de estrada;
- estruturas presas no alto;
- cordas e passagens improvisadas modernas;
- visibilidade estreita para cima.

Lore visual:
> o terreno força todos a passar por poucos corredores.

---

## 3.3 Vigília do Vale

**Tipo:** hub seguro.

Assentamento adaptado à umidade:
- plataformas;
- madeira tratada;
- pedra;
- coberturas inclinadas;
- passarelas;
- cordas;
- drenagem;
- Braseiro protegido.

Não é uma aldeia sobre árvores.

É um ponto de sobrevivência construído onde o terreno permite controle.

---

## 3.4 Mata Suspensa

Árvores inclinadas e níveis verticais diferentes.

Elementos:
- trilhas no solo;
- raízes formando passagens;
- troncos que sustentam ruínas;
- passarelas naturais e artificiais;
- estruturas antigas visíveis acima e abaixo.

Sensação:
> o chão deixou de ser a única direção possível.

---

## 3.5 Fosso das Raízes

**Tipo:** Masmorra · entrada pela Mata Suspensa.

### Identidade oficial
Fenda profunda sob a Mata. Troncos, passarelas e raízes gigantes atravessam o vazio. Quanto mais fundo, menos as raízes parecem pertencer apenas às árvores da superfície.

### Arquitetura/ambiente
- precipício escuro;
- raízes como pontes;
- plataformas quebradas;
- estruturas antigas presas às paredes;
- gotejamento constante;
- névoa no fundo;
- cordas velhas;
- madeira gemendo.

### Progressão visual
1. **Passagem Pendente:** travessia instável.
2. **Emaranhado Inferior:** raízes mais densas.
3. **Domínio da Tecelã:** redes e pontos de ancoragem.
4. **Profundezas Suspensas:** arquitetura antiga aparece presa no vazio.
5. **Câmara de O Que Pende:** peso, sustentação e risco de queda.

### Lore
A Masmorra sugere que as raízes seguem algo anterior à floresta.

Não explica por quê.

### Evitar
- abismo infinito cósmico;
- raízes brilhantes;
- árvore-mundo sagrada.

---

## 3.6 Baixios Enredados

Fundo úmido dos Vales.

Elementos:
- água escura;
- turfa;
- juncos;
- raízes submersas;
- caminhos estreitos;
- neblina rente à água.

Sensação:
lento, pesado, insalubre.

A água não precisa ser venenosa por aparência.

---

## 3.7 Claustro das Raízes

**Tipo:** ruína asteriana central.

Pedra antiga atravessada por raízes.

Arquitetura deve continuar discernível:
- corredores;
- câmaras;
- ligações;
- suportes;
- portas.

A natureza domina fisicamente, mas não apaga a organização anterior.

---

## 3.8 Santuário do Nó Antigo

**Tipo:** Masmorra · entrada pelo Claustro.

### Identidade oficial
Estrutura asteriana parcialmente subterrânea, atravessada por raízes, sem revelar ainda a finalidade verdadeira das Âncoras.

### “Santuário”
O nome moderno não significa templo.

É um nome dado por quem encontrou uma estrutura preservada e incompreendida.

### Arquitetura
- galerias de pedra;
- quatro eixos/raízes principais;
- mecanismos parcialmente ativos;
- câmaras de contenção;
- placas antigas;
- interseções da estrutura com raízes.

### Progressão visual
1. **Galeria Estrangulada:** corredor técnico tomado por raízes.
2. **Câmara Invadida:** natureza e construtos coexistem.
3. **Custódio Enredado:** setor de guarda.
4. **Câmara das Quatro Raízes:** organização quase ritual à primeira vista, mas funcional.
5. **Nó Antigo:** mecanismo de ligação, não altar.

### Evitar
- templo religioso confirmado;
- sacerdotes vegetais;
- coração mágico da floresta.

---

## 3.9 Berço da Matriarca

**Tipo:** Local de clímax.

Rede de raízes converge sobre estrutura asteriana antiga.

A Matriarca:
- ocupou;
- integrou-se;
- alterou o ecossistema.

Ela não construiu o lugar.

Visual:
- câmara ampla;
- raízes monumentais;
- pedra anterior;
- conexões radiculares;
- espaço central ocupado pelo corpo da Matriarca.

Evitar:
- trono vegetal;
- deusa;
- altar dedicado a ela.

---

# 4. 🌾 PLANÍCIES DE NARETH

**Faixa:** Nv.21–30  
**Chefe regional:** Arconte Invertido  
**Função narrativa:** revelar que as Âncoras estabilizavam o Véu.  
**Fantasia central:** a paisagem é aberta o suficiente para ver longe — e justamente por isso fica evidente quando as referências deixam de concordar.

> Nas planícies, nada impede a visão — exceto aquilo que faz o horizonte mentir.

## 4.1 Identidade regional

Planícies frias e ventosas atravessadas por infraestrutura antiga:
- estradas;
- canais;
- marcos;
- torres de medição;
- fundações;
- linhas de pedra.

Paleta:
- palha;
- verde-acinzentado;
- terra clara;
- calcário;
- bronze envelhecido;
- céu azul-cinza;
- sombras longas.

A Região não é deserto.

Também não é pradaria idílica.

## 4.2 História ambiental

Nareth funcionava como um território de:
- medição;
- distribuição;
- orientação;
- passagem.

Sua paisagem preserva a ideia de rede de forma mais evidente que as Regiões anteriores.

Depois da Ruptura, estruturas de referência passaram a discordar.

Isso gerou:
- rotas inconsistentes;
- áreas evitadas;
- assentamentos concentrados em pontos confiáveis;
- fauna adaptada a grandes campos e canais.

---

## 4.3 Campinas do Meridiano

Campos de gramíneas altas atravessados por linhas antigas quase retas demais.

Elementos:
- pedras de marcação;
- estrada quase apagada;
- marcos a intervalos regulares;
- vento constante;
- ruínas baixas.

Sensação:
espaço amplo, vulnerabilidade e orientação.

---

## 4.4 Posto de Nareth

**Tipo:** hub seguro.

Assentamento moderno construído ao redor de:
- cisternas reparadas;
- antigo posto viário;
- paredes baixas;
- depósitos;
- estábulos;
- oficinas de cartografia e manutenção.

Identidade:
quem vive aqui mede distâncias, registra rotas e confia em marcos verificados.

Evitar:
- cidade rica;
- grande fortaleza;
- observatório mágico cheio de astrólogos.

---

## 4.5 Canais Secos

Sistema antigo de valas e condução.

Elementos:
- paredes de pedra;
- leitos rachados;
- pontes estreitas;
- comportas antigas;
- vegetação seca;
- animais escondidos nos desníveis.

A profundidade das valas cria combate e exploração vertical em uma Região geralmente aberta.

---

## 4.6 Galerias do Meridiano

**Tipo:** Masmorra I.

### Função histórica
Galerias de manutenção subterrânea associadas à infraestrutura de alinhamento e distribuição regional.

### Ambiente
- túneis largos;
- trilhos de serviço;
- canais;
- nichos de ferramentas;
- eixos de acesso;
- marcas repetidas;
- paredes raspadas por ciclos antigos.

### Particularidade
Certos trajetos parecem levar de volta ao mesmo lugar por engenharia circular e falhas de referência.

Não tratar como loop temporal confirmado.

### Progressão visual
1. corredor de serviço;
2. junção circular;
3. setores de escavação/manutenção;
4. circuito repetido;
5. câmara de O Que Retorna.

### Evitar
- labirinto mágico com portas flutuantes;
- viagem no tempo explícita.

---

## 4.7 Campos Invertidos

Área onde:
- marcos apontam para direções incompatíveis;
- declives parecem errados;
- sombras ajudam menos que deveriam;
- distância visual e distância percorrida nem sempre coincidem.

A distorção deve ser sutil.

Evitar:
- céu de ponta-cabeça;
- ilha flutuante;
- mundo totalmente surreal.

---

## 4.8 Observatório do Eixo

Complexo asteriano baixo e extenso.

Não é observatório astronômico.

Sua função era:
- medir alinhamento;
- comparar referências;
- monitorar estabilidade regional.

Elementos:
- linhas marcadas no piso;
- grandes armações;
- lentes/minerais apenas se coerentes;
- braços mecânicos;
- plataformas de observação do terreno.

---

## 4.9 Observatório Afundado

**Tipo:** Masmorra II.

Parte antiga do complexo cedeu ao solo.

### Ambiente
- câmaras inclinadas;
- níveis parcialmente enterrados;
- poços de alinhamento;
- instrumentos quebrados;
- corredores em ângulos desconfortáveis.

### História visual
O lugar tenta preservar referências geométricas mesmo depois de o próprio edifício ter se deslocado.

### Progressão
1. acesso inclinado;
2. câmara de medição;
3. custódios;
4. sala de recalibração;
5. Guardião da Referência.

### Evitar
- telescópios modernos;
- planetário;
- mapa holográfico.

---

## 4.10 Câmara do Arconte

**Tipo:** clímax regional.

Centro de coordenação regional.

Arquitetura:
- precisa;
- simétrica originalmente;
- agora contraditória;
- placas e braços mecânicos corrigindo posições erradas.

Aqui o jogador pode finalmente receber evidência visual coerente de:
> a rede tinha função de estabilização.

O Arconte não é rei.

A “regência” visual dele deve vir de autoridade técnica.

---

# 5. 🥀 VÁRZEAS CARMESINS

**Faixa:** Nv.31–40  
**Chefe regional:** Matriz Rubra  
**Função narrativa:** revelar Projeto Hemaris e a origem ancestral das alterações Hemárias.  
**Fantasia central:** medicina de emergência preservada tempo demais até começar a tratar a vida como matéria de processo.

> A água não lembra sangue. É o sangue que passou a lembrar a água.

## 5.1 Identidade regional

Terras baixas, úmidas e ferruginosas.

Elementos:
- diques;
- água avermelhada por minerais e resíduos;
- salmoura;
- juncos;
- madeira encharcada;
- vidro escurecido;
- instalações clínicas antigas;
- tubos e reservatórios;
- vegetação adaptada.

Paleta:
- ferrugem;
- vermelho escuro dessaturado;
- marrom;
- verde de junco;
- branco sujo;
- metal oxidado;
- vidro âmbar.

Evitar:
- rio de sangue literal em toda parte;
- paredes de carne;
- dimensão gore.

---

## 5.2 Diques Rubros

Passagem de entrada pela borda das várzeas.

Elementos:
- barragens antigas;
- passarelas;
- água ferruginosa;
- comportas;
- juncos;
- depósitos sedimentares.

Sensação:
engenharia antiga ainda influencia o curso da água.

---

## 5.3 Porto da Salmoura

**Tipo:** hub seguro.

Assentamento de passarelas e cais:
- madeira escura;
- pedra;
- barcos rasos;
- tanques de água;
- oficinas;
- depósitos;
- plataformas elevadas contra inundação.

A comunidade vive da travessia e da adaptação ao pântano.

Evitar:
- porto marítimo grande;
- navios oceânicos;
- cidade pirata.

---

## 5.4 Brejos do Pulso

Pântano de pressão variável.

Elementos:
- água rasa;
- bolsas de gás;
- juncos;
- elevações de turfa;
- tubulações antigas sob o solo;
- pulsações hidráulicas ocasionais.

O “pulso” não precisa parecer coração.

---

## 5.5 Enfermaria Afundada

**Tipo:** Masmorra I.

### Função histórica
Instalação médica do Projeto Hemaris parcialmente submersa.

### Arquitetura
- corredores clínicos estreitos;
- pedra clara suja;
- metal oxidado;
- leitos;
- suportes;
- frascos;
- canaletas;
- tanques;
- portas de isolamento.

### História visual
Primeiras salas sugerem medicina.

Salas posteriores sugerem:
- emergência;
- superlotação;
- protocolos extremos;
- perda gradual de distinção entre tratamento e experimentação.

### Progressão
1. recepção/triagem;
2. enfermaria inundada;
3. sala de transferência;
4. setor de persistência;
5. O Persistente.

### Evitar
- hospital moderno;
- lâmpadas fluorescentes;
- laboratório sci-fi;
- gore gratuito;
- vampiros.

---

## 5.6 Hortos Hemaris

Antigos cultivos terapêuticos.

Elementos:
- estufas quebradas;
- canteiros elevados;
- plantas medicinais;
- reservatórios;
- treliças;
- vegetação escapando para o pântano.

O local deve mostrar que Hemaris começou com objetivos de cuidado.

Isso é importante para a tragédia.

---

## 5.7 Galerias de Transferência

Infraestrutura onde líquidos, nutrientes e recursos biológicos eram conduzidos.

Elementos:
- canais;
- reservatórios;
- tubos de metal/cerâmica;
- válvulas;
- câmaras de pressão;
- suportes para recipientes.

Evitar estética industrial moderna.

---

## 5.8 Cisterna de Transferência

**Tipo:** Masmorra II.

### Função histórica
Grande sistema de armazenamento, medição e redistribuição biológica.

### Ambiente
- níveis circulares;
- tanques;
- pontes;
- colunas;
- reservatórios opacos;
- condensação;
- ferrugem;
- resíduos secos.

### História visual
Quanto mais fundo:
- menos o lugar se parece com medicina individual;
- mais se parece com logística de recurso biológico.

Essa transição é central.

### Progressão
1. condutos;
2. sala de medição;
3. coletores;
4. reservatório central;
5. Coração de Transferência.

“Coração” é apelido visual/funcional, não órgão demoníaco.

---

## 5.9 Câmara da Matriz

**Tipo:** clímax regional.

Estrutura biológica-técnica de grande escala.

Elementos:
- tubos;
- tanques;
- membranas estabilizadas;
- metal;
- placas;
- câmaras de distribuição;
- conexões.

A Matriz deve parecer:
> algo construído para manter sistemas vivos funcionando.

E hoje:
> algo que continua tentando cumprir isso sem compreender indivíduo, consentimento ou limite.

Evitar:
- rainha vampira;
- deusa de sangue;
- coração gigante exposto como demônio;
- templo Hemário.

---

# 6. ⛰️ ALTOS CINÉREOS

**Faixa:** Nv.41–50  
**Chefe regional:** Colosso Cinéreo  
**Função narrativa:** revelar crise política, Regência de Continuidade, Convergência, Desvelados e sabotagem.  
**Fantasia central:** tudo permanece porque alguma coisa ainda suporta o peso.

> Nos Altos, aquilo que não desaba sempre está apoiado em algo que também pode falhar.

## 6.1 Identidade regional

Montanhas frias, cinza mineral e estruturas de engenharia pesada.

Elementos:
- escarpas;
- pontes;
- pedreiras;
- contrapesos;
- cabos;
- correntes;
- chaminés técnicas;
- pedra escura;
- fuligem;
- vento forte.

Paleta:
- grafite;
- cinza mineral;
- marrom ferrugem;
- bege de pedra;
- branco sujo de neve/cinzas em pontos altos;
- metal negro.

Evitar:
- vulcão ativo como identidade dominante;
- lava em todo lugar;
- anões genéricos;
- cidade subterrânea dourada.

---

## 6.2 Escarpa da Cinza

Entrada regional.

Estrada estreita em paredão.

Elementos:
- rocha;
- vento;
- cinza mineral;
- postes de amarração;
- pequenas pontes;
- marcas de quedas antigas.

A escala vertical cresce em relação às Regiões anteriores.

---

## 6.3 Abrigo do Peso

**Tipo:** hub seguro.

Assentamento encaixado em depressão protegida.

Arquitetura:
- pedra pesada;
- vigas;
- coberturas baixas;
- muros de contenção;
- depósitos;
- oficinas;
- passagens protegidas do vento.

Cultura visual:
reparo, manutenção e redundância.

---

## 6.4 Pontes de Fuligem

Rede de travessias sobre desfiladeiros.

Elementos:
- pontes de pedra e madeira;
- cabos antigos;
- suportes asterianos;
- fuligem nos encaixes;
- estruturas duplicadas de segurança.

Sensação:
tudo foi pensado para não cair — e ainda assim partes caíram.

---

## 6.5 Pedreira do Contrapeso

**Tipo:** Masmorra I.

### Função histórica
Complexo de extração e preparação de massa estrutural para obras dos Altos.

### Ambiente
- taludes;
- corredores de corte;
- blocos;
- guindastes mecânicos antigos;
- trilhos;
- contrapesos;
- poeira mineral.

### Progressão
1. frente de corte;
2. oficina;
3. prensa;
4. poço de contrapesos;
5. Peso sem Fim.

### Lore
A Masmorra fala de trabalho e infraestrutura.

Não de culto à pedra.

---

## 6.6 Pedreiras Suspensas

Local aberto com plataformas de extração em diferentes cotas.

Elementos:
- paredões cortados;
- passarelas;
- guinchos;
- correntes;
- plataformas abandonadas;
- blocos ainda presos.

Sensação:
trabalho antigo congelado no meio do processo.

---

## 6.7 Bastilha de Carga

Grande instalação asteriana de proteção estrutural.

“Bastilha” aqui é moderna designação para um complexo fortificado, não prisão obrigatória.

Elementos:
- muros;
- travas;
- contrafortes;
- corredores;
- grandes mecanismos;
- pontos de fixação.

---

## 6.8 Bastilha Profunda

**Tipo:** Masmorra II.

Camadas inferiores da Bastilha.

### Função histórica
Coordenação de cargas e contenção de falhas em grandes obras regionais.

### Ambiente
- corredores monumentais;
- eixos de cabos;
- câmaras de travamento;
- placas de ordem emergencial;
- pontos de conexão.

### Progressão
1. ponte interna;
2. câmara de trava;
3. setor de coordenação;
4. sala de ordens;
5. Guardião do Contrapeso.

### Lore
Aqui aparecem registros de:
- emergência;
- centralização;
- ordens contraditórias;
- preparação da Convergência.

As imagens ainda não devem transformar esses registros em mural explicativo completo.

---

## 6.9 Coração do Colosso

**Tipo:** clímax regional.

O Colosso faz parte de um sistema de sustentação do complexo.

Ambiente:
- pilares;
- cabos;
- contrapesos;
- plataformas;
- espaço amplo necessário para sua movimentação;
- cinza acumulada por séculos.

O clímax deve comunicar:
> uma estrutura inteira dependeu de coisas que foram obrigadas a continuar suportando.

Evitar:
- templo de gigante;
- lava;
- ancestral dos Cinéreos;
- estátua divina.

---

# 7. 🌫️ CONFINS DO VÉU

**Faixa:** Nv.51–60  
**Chefe regional:** Regente Fraturado  
**Função narrativa:** revelar Fraturas, Avesso e a cadeia real da Ruptura.  
**Fantasia central:** a realidade continua reconhecível, mas não confiável.

> Nos Confins, o mundo continua inteiro principalmente quando observado de longe.

## 7.1 Identidade regional

Elementos:
- névoa;
- pedra clara;
- vegetação rara;
- estradas incompletas;
- edifícios com desgaste contraditório;
- pequenas duplicações;
- objetos em posições incompatíveis;
- espaços que parecem lembrar versões diferentes de si.

Paleta:
- cinza pálido;
- azul dessaturado;
- branco sujo;
- preto profundo;
- verde muito frio;
- pequenos desvios cromáticos.

Evitar:
- espaço sideral;
- nebulosas;
- roxo neon;
- glitch digital;
- tentáculos cósmicos.

## 7.2 Regra da estranheza

A imagem deve primeiro parecer normal.

Só depois o observador percebe:
- duas sombras;
- degrau repetido;
- desgaste diferente;
- janela que não coincide;
- pedra duplicada;
- caminho que deveria continuar.

Quanto mais cedo a imagem parece “dimensão cósmica”, pior.

---

## 7.3 Marcha Nebulosa

Estrada de entrada.

Elementos:
- marcos que aparecem e somem na névoa;
- trechos preservados;
- vegetação baixa;
- pequenas duplicações de elementos.

Ainda deve ser possível viajar.

---

## 7.4 Último Refúgio

**Tipo:** hub seguro.

Assentamento que combate desorientação por organização.

Elementos:
- placas com datas;
- cordas de orientação;
- marcas repetidas;
- sinos;
- mapas físicos;
- postes;
- números;
- construções reforçadas.

Lore visual:
as pessoas registram o mundo porque nem sempre confiam na lembrança do lugar.

Evitar:
- comunidade enlouquecida;
- culto ao vazio;
- cidade fantasma.

---

## 7.5 Estradas Ausentes

Lugar onde fragmentos de infraestrutura terminam de maneira impossível.

Exemplo:
- ponte chega a margem sem estrada;
- calçamento desaparece sob terreno antigo demais;
- marco aponta para rota inexistente.

A estranheza é histórica e espacial.

---

## 7.6 Arquivo do Retorno

**Tipo:** Masmorra I.

### Função histórica
Arquivo asteriano de registros operacionais e estados de sistema.

### Estado atual
Fraturas fizeram registros, espaços e rotinas repetirem versões incompatíveis.

### Arquitetura
- estantes de placas;
- arquivos físicos;
- salas de catalogação;
- corredores;
- nichos;
- mecanismos de registro.

### Progressão
1. arquivo exterior;
2. corredor repetido;
3. seção de registros divergentes;
4. sala de retorno;
5. O Que Chega Antes.

### Lore
“Retorno” não significa viagem no tempo controlável.

O lugar conserva e repete estados de maneira defeituosa.

### Evitar
- biblioteca infinita mágica;
- relógios voando;
- portal temporal azul.

---

## 7.7 Fraturas do Limiar

Zona onde Fraturas reais podem ser observadas.

Visual:
- bordas duplicadas;
- espaço com continuidade quebrada;
- objetos parcialmente repetidos;
- som implícito por arquitetura vazia;
- terreno que não encaixa perfeitamente.

Não usar:
- rasgo preto com galáxia dentro;
- portal circular genérico.

---

## 7.8 Nó Central

Restos da infraestrutura de coordenação que conduzia à Âncora Central.

Elementos:
- múltiplas rotas convergindo;
- placas;
- sistemas de referência;
- estruturas quebradas;
- ordens sobrepostas.

É o lugar onde o jogador começa a conectar a rede inteira.

---

## 7.9 Câmara das Contradições

**Tipo:** Masmorra II.

### Função histórica
Setor de reconciliação de leituras incompatíveis e registros de emergência.

### Estado atual
O sistema continua tentando manter simultaneamente informações que não podem ser verdade ao mesmo tempo.

### Arquitetura
- câmaras simétricas com diferenças pequenas;
- placas duplicadas;
- duas versões de uma porta;
- salas que “discordam” sobre danos sofridos;
- registros conflitantes.

### Progressão
1. corredor duplo;
2. setor de leituras;
3. custódio;
4. sala de decisões;
5. Testemunha Impossível.

### Evitar
- quebra-cabeça abstrato sem arquitetura física;
- sonho surreal sem referência ao mundo;
- glitch digital.

---

## 7.10 Câmara da Regência

**Tipo:** clímax final da campanha.

Restos do centro de decisão da Regência de Continuidade e da coordenação central.

Arquitetura:
- monumental, mas administrativa/técnica;
- plataformas;
- mapas físicos/placas;
- postos de comando;
- conexões com a rede;
- danos incompatíveis entre partes;
- setores preservados ao lado de setores “repetidos”.

A sala deve parecer:
> lugar onde pessoas tomaram decisões reais.

Não:
> templo do chefe final.

O Regente Fraturado ocupa essa memória de autoridade.

Evitar:
- trono imperial;
- altar;
- salão demoníaco;
- universo no teto.

---

# 8. MASMORRAS — REGRA GLOBAL DE DIREÇÃO DE ARTE

Cada Masmorra precisa parecer um **lugar que existia antes de virar conteúdo de combate**.

Uma imagem de Masmorra deve conseguir responder visualmente:
1. para que esse lugar servia?
2. quem o construiu?
3. como o ambiente regional o transformou?
4. por que é perigoso agora?
5. que verdade narrativa ele pode sugerir sem entregar demais?

## 8.1 Diferença de dificuldade

**Estável:** lugar degradado, mas continuidade espacial majoritariamente normal.  
**Fraturada:** sinais mais fortes de falha, dano e comportamento anormal.  
**Ruptura:** pode aprofundar fenômenos de Ruptura no endgame.

A dificuldade não exige redesenhar toda a Masmorra como outra dimensão.

## 8.2 Braseiros de Masmorra

Quando existirem:
- pequenos;
- improvisados ou reaproveitados;
- visualmente distintos dos mecanismos antigos;
- nunca devem parecer parte natural da tecnologia asteriana sem definição explícita.

## 8.3 Chefes de Masmorra

A arena deve refletir função histórica do local.

Não criar “arena circular de boss” sem motivo arquitetônico.

---

# 9. PROGRESSÃO VISUAL DAS SEIS REGIÕES

1. **Terras do Ocaso** — o jogador vê ruínas.
2. **Vales dos Enforcados** — percebe que ruínas estão conectadas.
3. **Planícies de Nareth** — entende que a conexão possuía função.
4. **Várzeas Carmesins** — descobre o preço humano da crise.
5. **Altos Cinéreos** — descobre o conflito político que precedeu a queda.
6. **Confins do Véu** — descobre o que realmente aconteceu.

A direção de arte deve acompanhar essa curva.

O cenário não deve parecer igualmente “cosmológico” desde o início.

---

# 10. TEMPLATE PARA PROMPT DE CENÁRIO

Ao gerar uma imagem de Região/Local/Masmorra, usar esta ordem:

1. **Nome canônico do Local**
2. **Região**
3. **tipo de espaço**
4. **função histórica**
5. **bioma**
6. **arquitetura**
7. **materiais**
8. **clima/luz**
9. **sinais de ocupação moderna ou abandono**
10. **nível de deterioração**
11. **mistério permitido**
12. **elementos obrigatórios**
13. **elementos proibidos**
14. **enquadramento**
15. **estilo visual global de Asterion**

Exemplo de bloco sem estilo específico:

> Câmara asteriana de manutenção em ruína, parcialmente tomada por raízes úmidas; grandes blocos de pedra funcional, encaixes metálicos envelhecidos, canais técnicos, névoa baixa, sinais claros de que a arquitetura antecede a vegetação; nenhuma runa neon, nenhum templo, nenhuma tecnologia sci-fi, nenhuma revelação cosmológica explícita.

---

# 11. REGRAS PARA FUNDOS DE SKIN DE CRIATURAS

Quando a imagem for uma **skin isolada de monstro**, o fundo deve identificar o habitat sem competir com a criatura.

### Terras do Ocaso
cinza, pedra, madeira carbonizada, ruína seca.

### Vales
raízes, umidade, musgo, pedra molhada.

### Nareth
grama seca, céu amplo, marco ou canal.

### Várzeas
água ferruginosa, juncos, metal/vidro antigo.

### Altos
rocha, fuligem mineral, correntes, estrutura pesada.

### Confins
névoa, pedra pálida, pequena contradição espacial.

O fundo não deve introduzir lore que a própria criatura não conhece/representa.

---

# 12. ESTADO DE CÂNONE E IMPLEMENTAÇÃO

## Terras do Ocaso
Conteúdo regional oficial já fechado. Este documento apenas detalha direção visual/literária sem substituir a Fonte Regional.

## Vales dos Enforcados
Conteúdo regional oficial já fechado. Este documento apenas detalha direção visual/literária sem substituir a Fonte Regional.

## Planícies de Nareth
Identidade, Locais, Masmorras e direção visual fechados nesta frente de Lore. Balanceamento e conteúdo regional implementável detalhado ainda precisam de Fonte Regional própria.

## Várzeas Carmesins
Identidade, Locais, Masmorras e direção visual fechados nesta frente de Lore. Balanceamento e conteúdo regional implementável detalhado ainda precisam de Fonte Regional própria.

## Altos Cinéreos
Identidade, Locais, Masmorras e direção visual fechados nesta frente de Lore. Balanceamento e conteúdo regional implementável detalhado ainda precisam de Fonte Regional própria.

## Confins do Véu
Identidade, Locais, Masmorras e direção visual fechados nesta frente de Lore. Balanceamento e conteúdo regional implementável detalhado ainda precisam de Fonte Regional própria.

---

# 13. CHECKLIST PARA NOVA ARTE

Antes de aprovar qualquer cenário:

- [ ] O Local pertence visualmente à Região correta?
- [ ] A arquitetura tem função discernível?
- [ ] O nível de tecnologia continua medieval/fantástico e não sci-fi?
- [ ] O clima e os materiais regionais estão corretos?
- [ ] O cenário evita clichê genérico que substitui a identidade regional?
- [ ] A imagem respeita o gate narrativo e não contém spoiler visual?
- [ ] Se for ruína asteriana, parece integrada a uma rede civilizacional funcional?
- [ ] Se for construção moderna, parece adaptação/reparo e não arquitetura antiga intacta?
- [ ] A Masmorra parece ter existido por um motivo antes de ser “dungeon”?
- [ ] O chefe/clímax pertence organicamente ao espaço?
- [ ] O Avesso não aparece antes do momento correto?
- [ ] O cenário pode ser reconhecido sem depender do nome escrito na tela?

---

# 14. FECHAMENTO

Com esta Fonte + `ASTERION_BESTIARIO_VISUAL_E_BIOMAS_v1.1.md`, a produção visual passa a possuir uma referência conjunta para:

- Regiões;
- biomas;
- paletas;
- materiais;
- arquitetura antiga;
- arquitetura moderna;
- Locais principais;
- hubs;
- clímax regionais;
- Masmorras;
- função histórica de Masmorras;
- progressão visual;
- limites de spoiler;
- criaturas-base;
- Elites;
- Chefes;
- habitats;
- direção de skin;
- consistência entre criatura e cenário.

O que permanece fora dessas duas Fontes é principalmente:
- composição exata de cada tela do Bot;
- números de combate das Regiões 3–6;
- pools e Balanceamento;
- diálogos finais;
- Flavor Text final;
- assets produzidos.

Esses itens não impedem a reconstrução visual coerente de skins e cenários.

---

# DOCUMENTO INCORPORADO 4/9
## Arquivo original: `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`
# ASTERION — PADRÃO GLOBAL DE SKINS TEMÁTICAS v1.1

**Data de consolidação:** 2026-10-12  
**Escopo:** produção, geração, revisão e QA de Aparências/skins temáticas de personagens jogáveis  
**Estado:** fonte visual operacional global aprovada para produção futura  
**Aplicação:** prospectiva para novas levas e imediata para levas ainda em produção; assets já aprovados não são reabertos automaticamente  

> Este documento não cria Lore, mecânica, proficiência, inventário, Raça, Classe, Caminho, Região, Local ou Cosmético. Ele formaliza o **método global de produção** de skins temáticas para que Asterion permaneça visualmente coerente entre lotes, Regiões e ferramentas de geração.

---

# 1. POSIÇÃO NA HIERARQUIA DE FONTES

Para uma skin temática, usar as fontes nesta ordem:

1. `SOURCE_AUTHORITY.md` ou sua atualização vigente;
2. Fonte Mestra vigente;
3. Fonte Regional FINAL vigente, quando a Aparência pertencer a uma Região;
4. `ASTERION_LORE_BIBLE_CANON_v1.2.md` ou revisão vigente;
5. `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` ou revisão vigente;
6. **este `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md`**;
7. Fonte Visual Especializada da Aparência, quando existir;
8. `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` quando houver Região/Local real;
9. Fonte Visual/UI vigente quando o asset pertencer a uma tela específica;
10. `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` ou revisão vigente;
11. `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` ou revisão vigente.

## 1.1 Regra de precedência

- conteúdo regional FINAL nunca é substituído por uma decisão estética genérica;
- identidade de Raça e Classe vem da Bíblia Visual vigente;
- a Bíblia Técnica continua definindo canvas, pixel art, anatomia e QA técnico;
- este padrão fecha **consistência de catálogo, escala, câmera, variação e construção de fundo para skins temáticas**;
- uma Fonte Visual Especializada de Aparência pode criar exceção ao padrão global **somente no escopo explicitamente declarado** e somente quando registrada na Autoridade das Fontes;
- documento antigo de prompts não é autoridade se divergir das Fontes vigentes.

Exemplo já existente: `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md` preserva suas exceções específicas de armamento e composição e não é reaberto por este documento.

---

# 2. PRINCÍPIO GLOBAL

Toda skin temática deve comunicar, nesta ordem de leitura:

1. **Pessoa / indivíduo** — não parecer um personagem diferente por acidente;
2. **Classe** — função imediatamente legível por silhueta, equipamento, arma/foco e postura;
3. **Raça** — fenótipo reconhecível sem depender de texto, roupa ou símbolo;
4. **Aparência/tema** — materiais, desgaste, solução de traje e assinatura cosmética;
5. **Região**, quando aplicável — ambiente, clima e materialidade coerentes com o conteúdo regional.

Regra-guia:

> **A skin muda a apresentação; não apaga a pessoa, a Raça, a Classe nem o mundo ao redor dela.**

---

# 3. IDENTIDADE TÉCNICA OBRIGATÓRIA

Todas as skins temáticas devem preservar a identidade visual global de Asterion:

- dark fantasy medieval;
- estética de fim da era 16-bit / início da era 32-bit;
- **pixel art nativa**, não pintura suave com filtro de pixel;
- pixels deliberadamente visíveis;
- clusters intencionais;
- formas grandes antes de microdetalhe;
- materiais físicos antes de efeitos;
- saturação baixa/moderada;
- fantasia contida;
- anatomia humanoide legível;
- fundo subordinado ao personagem.

Reprovar:

- concept art painterly suavizada e depois pixelizada;
- 3D/CGI com pixels falsos;
- acabamento moderno liso;
- blur amplo;
- bloom/glow para esconder forma ou anatomia;
- ruído de pixel uniforme em toda a imagem;
- microdetalhe que destrói a leitura da silhueta.

---

# 4. CANVAS, ESCALA E PADRÃO DE “TAMANHO DE TELA”

## 4.1 Formato

Para skin jogável:

- proporção `1:1`;
- master `1024×1024`;
- PNG;
- corpo inteiro;
- cabeça e pés completos;
- margens seguras em todos os lados;
- arma/foco/equipamento principal integral sempre que possível.

## 4.2 Escala vertical — regra global

A Bíblia Técnica permite normalmente **72–84% da altura do quadro** para a figura. Para lotes temáticos, este documento fecha um alvo operacional mais estreito para reduzir deriva:

- **alvo preferencial de catálogo:** aproximadamente **76–80%** da altura do quadro, medido do topo natural da cabeça/cabelo até a sola do pé mais baixo;
- **faixa operacional aceitável:** **72–82%** quando pose, arma, cabelo, chapéu ou constituição justificarem;
- **83–84%:** apenas exceção deliberada de silhueta, nunca default de geração;
- acima de 84% ou abaixo de 72%: reprovar salvo Fonte Especializada explícita.

A arma longa, arco, cajado ou adereço não deve obrigar o corpo a ficar minúsculo; ajustar composição e ângulo para preservar o tamanho corporal do catálogo.

## 4.3 Padrão de enquadramento

A imagem deve manter:

- respiro claramente visível acima da cabeça;
- pés totalmente visíveis e assentados no terreno;
- chão suficiente para dar peso físico ao personagem;
- margens laterais que não comprimam escudo, arma, arco, cajado ou capa;
- eixo cabeça–tórax–quadril próximo do centro visual;
- personagem dominante, **porém não gigante**;
- ambiente ainda legível como contexto.

## 4.4 Câmera

Padrão para skins:

- distância média de câmera;
- perspectiva neutra ou levemente dinâmica;
- leitura de corpo inteiro prioritária;
- câmera à altura aproximada do torso/peito ou próxima da linha natural de observação;
- pequena variação de altura é permitida para composição, sem transformar a arte em pôster heroico.

Evitar:

- grande-angular aparente;
- câmera excessivamente próxima;
- ângulo muito baixo de “herói gigante”;
- vista aérea extrema;
- foreshortening forte;
- braço, perna, arma ou escudo projetados para a lente de modo a aumentar artificialmente o tamanho da figura;
- pose em que um pé avançado ocupe área desproporcional do primeiro plano.

## 4.5 Coerência entre assets

Em um mesmo lote:

- diferenças reais de altura/constituição podem existir, mas **não podem parecer diferenças de zoom**;
- personagens altos continuam altos por proporção anatômica, não por ocupar mais canvas;
- personagens robustos ganham massa horizontal, não escala de câmera maior;
- personagem esguio não deve ser afastado da câmera só para parecer menor;
- Classes com equipamento volumoso não recebem automaticamente enquadramento mais fechado.

Ao comparar o lote em grade, nenhuma imagem deve parecer claramente “zoomada” ou “miniaturizada” sem motivo explícito.

---

# 5. BENCHMARK VISUAL E CALIBRAÇÃO DE LOTE

Antes de produzir uma nova leva grande:

1. selecionar entre **6 e 10 skins já aprovadas** que representem o padrão atual do jogo;
2. usar essas imagens como **benchmark de tamanho de tela, densidade de pixel art, contraste e relação personagem/fundo**;
3. gerar um pequeno lote de calibração antes da produção completa;
4. comparar em grade/contato visual;
5. somente depois travar a produção do restante do lote.

Para um lote de 60 assets, recomenda-se calibrar no mínimo:

- 1 Sentinela;
- 1 Errante;
- 1 Vigia;
- 1 Classe extraordinária;
- 2 combinações adicionais cobrindo constituições/alturas diferentes.

Se o teste apresentar deriva de escala, câmera ou cenário, corrigir **o padrão do prompt/matriz antes** de continuar a produção em massa.

---

# 6. IDENTIDADE RACIAL EM SKINS TEMÁTICAS

## 6.1 Regra obrigatória

A skin não pode depender de texto, cor de roupa ou adereço para comunicar Raça. Na v1.1, a anatomia racial v2.0 é prioritária: chifres Hemários, orelhas Alvoranas, conjunto auricular/ocular Velado e densidade/dentição Cinérea não podem ser apagados pela temática.

Cada prompt individual de nova leva temática deve explicitar, quando a Matriz/Fonte possuir esses dados:

- profundidade e subtom natural de pele;
- cor e textura de cabelo;
- penteado funcional da imagem específica;
- cor dos olhos;
- estrutura/traços faciais relevantes;
- constituição corporal;
- pelo menos um marcador anatômico diagnóstico obrigatório da Raça quando aplicável, mais marcadores fenotípicos secundários;
- sinais individuais, quando definidos.

## 6.2 Iluminação não muda fenótipo

O prompt deve distinguir explicitamente:

- pigmentação natural;
- luz quente/fria do ambiente;
- lama, cinza, fuligem, umidade, sangue, poeira ou musgo superficial.

Exemplo de regra:

> “A luz âmbar pode aquecer highlights, mas não deve trocar o subtom natural da pele nem fazer um Velado parecer Hemário.”

## 6.3 Cabelo e variedade

Penteados podem variar entre skins temáticas desde que:

- permaneçam dentro da faixa racial/individual;
- não troquem textura natural sem justificativa;
- sejam funcionais para a Classe, clima e tema;
- não façam a pessoa parecer outra identidade por acidente.

Evitar repetir o mesmo penteado em todo o lote.

---

# 7. IDENTIDADE DE CLASSE E ARMAMENTO

## 7.1 Regra-base

Sem Fonte Especializada autorizando exceção, usar as assinaturas vigentes:

- **Sentinela:** arma de uma mão + escudo visível;
- **Errante:** duas armas curtas visíveis;
- **Vigia:** arco ou besta;
- **Tecelão:** arma-foco de Trama claramente técnica;
- **Oráculo:** arma-foco oracular/simbólica;
- **Luminar:** cajado/bastão de combate-foco.

A assinatura visual não cria regra mecânica de equipamento.

## 7.2 Variedade interna

Uma skin temática pode variar:

- modelo exato da arma dentro da família autorizada;
- posição da arma;
- estado ativo/passivo;
- bainha, suporte, aljava, foco e acessórios;
- proporção entre couro, tecido, malha e metal;
- arquitetura do torso e distribuição de equipamento.

Não variar a ponto de apagar a Classe.

## 7.3 Fonte Especializada de Aparência

Uma Aparência específica pode ampliar famílias de armamento ou criar exceções cosméticas, como ocorre em `Errante das Cinzas`.

Essas exceções:

- valem somente para a Aparência declarada;
- devem ser registradas em Fonte Especializada;
- não retroagem para a assinatura global de Classe;
- não criam proficiência ou loadout mecânico.

---

# 8. POSE, OLHAR E DINAMISMO DE CATÁLOGO

## 8.1 Estados oficiais

Usar os sete estados já reconhecidos pelo projeto:

1. Repouso;
2. Contemplação;
3. Vigilância;
4. Deslocamento;
5. Preparação;
6. Ação controlada;
7. Ação intensa.

Ação intensa deve continuar sendo minoria.

## 8.2 Vetor corporal

Variar deliberadamente:

- frontal;
- 3/4 esquerdo;
- 3/4 direito;
- perfil parcial esquerdo;
- perfil parcial direito;
- rotação contrária entre torso e cabeça;
- peso na perna dianteira/traseira;
- passo, subida, apoio, guarda ou repouso.

## 8.3 Cabeça e olhar

Para lotes grandes, declarar explicitamente em cada linha/prompt:

- direção da cabeça;
- direção dominante do olhar;
- relação entre olhar e arma/foco.

Regra de diversidade de produção para lotes de aproximadamente 60 assets:

- não repetir automaticamente a mesma direção dominante em assets consecutivos;
- evitar mais de duas imagens consecutivas com o mesmo vetor principal;
- em qualquer janela de seis assets, buscar pelo menos quatro vetores distintos de cabeça/olhar quando a matriz permitir;
- não permitir que “3/4 olhando para a direita” se torne pose default da ferramenta.

Essa regra generaliza o controle de composição que se mostrou eficaz na Fonte Especializada `Errante das Cinzas`.

---

# 9. FUNDO: REGRA GLOBAL

## 9.1 Fórmula

Para skins temáticas com contexto regional:

`REGIÃO/APARÊNCIA + FUNÇÃO ESPACIAL DA CLASSE + MOTIVO RACIAL COMPATÍVEL + VARIAÇÃO DE SUBCENÁRIO`

A Região/Aparência deve dominar quando a arte representa um ambiente real.

## 9.2 Fundo subordinado

O fundo precisa:

- ter contraste local e microdetalhe menores que o personagem;
- usar 1–3 formas ambientais reconhecíveis em vez de competir com a figura;
- contextualizar sem transformar a skin em concept art de cenário;
- evitar batalhas completas, multidões ou Chefes escondidos ao fundo;
- respeitar o gate de spoiler.

## 9.3 Motivo racial não é geografia automática

Os fundos de herança racial são motivos históricos/evocativos, não autorização para transplantar Locais raciais para qualquer Região.

Portanto:

- um Hemário nos Vales **não exige** uma instalação Hemaris literal ao fundo;
- um Alvorano nos Vales **não exige** um terraço civil pré-Ruptura específico;
- um Velado nos Vales **não exige** um umbral “do povo Velado”;
- um Cinéreo nos Vales **não exige** arquitetura dos Altos Cinéreos;
- um Remanescente nos Vales **não exige** um assentamento reconstruído dominante.

Quando o motivo racial literal inventaria geografia ou Lore, transferir a herança para:

- organização do equipamento;
- reparos;
- materiais pessoais;
- distribuição de acessórios;
- pequenos padrões estruturais não geográficos;
- gestual e solução funcional do personagem.

## 9.4 Função espacial da Classe

O fundo pode apoiar a Classe sem se repetir:

- **Sentinela:** gargalo, passagem defensiva, ruína estreita, barricada mínima, parapeito;
- **Errante:** bifurcação, trilha partida, passagem lateral, ponte, mudança de nível;
- **Vigia:** mirante, borda elevada, linha longa de visão, passarela alta;
- **Tecelão:** junta estrutural, reparo de campo, ruína técnica, ponto de manutenção;
- **Oráculo:** encruzilhada, marcadores de rota, caminhos divergentes, umbral funcional;
- **Luminar:** abrigo de estrada, posto de recuperação, braseiro funcional, área de apoio pequena.

Essas funções não obrigam um único Local ou a repetição do mesmo posto em todas as skins.

---

# 10. DIVERSIDADE DE CENÁRIOS DENTRO DE UMA REGIÃO

## 10.1 Assinatura fixa + subcenário variável

Uma coleção regional deve funcionar como:

> **mesma Região, muitos trechos do caminho.**

Manter constante:

- paleta regional;
- clima;
- materiais;
- vegetação/geologia;
- arquitetura compatível;
- tipo de desgaste;
- lógica de iluminação;
- fantasia central da Região.

Variar:

- Local ou microbioma;
- terreno;
- altura/profundidade;
- densidade de vegetação;
- quantidade de ruína;
- presença/ausência de estrutura humana;
- direção do caminho;
- foreground/midground;
- hora/luz compatível;
- chuva, névoa, vento, água ou cinza quando autorizados;
- lado do ponto de interesse.

## 10.2 Matriz ambiental de lote

Toda leva regional grande deve possuir uma **matriz de fundo** antes da geração em massa.

Campos mínimos:

- ID do asset;
- Região;
- Local/microbioma ou vinheta regional;
- função espacial da Classe;
- terreno;
- estrutura principal;
- elemento natural principal;
- clima/atmosfera;
- luz;
- enquadramento do fundo;
- restrição de spoiler.

## 10.3 Distribuição

Para lote de aproximadamente 60 assets:

- usar pelo menos **4–6 famílias ambientais** quando a Região possuir variedade canônica suficiente;
- não usar o mesmo Local/microcenário como default do catálogo;
- evitar repetir o mesmo subcenário em mais de dois assets consecutivos;
- apresentações masculina/feminina da mesma combinação devem variar enquadramento, ponto de interesse ou microcenário;
- o hub seguro **não deve dominar** um cosmético regional, salvo se a própria Aparência for explicitamente centrada no hub;
- como alvo editorial, hubs devem ocupar uma parcela minoritária do lote, idealmente não mais que cerca de um quinto quando houver alternativas canônicas suficientes;
- Masmorras, clímax e Locais tardios só entram quando o gate de conhecimento da Aparência permitir.

## 10.4 Local real versus vinheta regional

Quando a arte usa um Local nomeado:

- seguir `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS` e a Fonte Regional;
- não inventar arquitetura ou função ausente;
- não revelar elementos que o jogador ainda não deveria conhecer.

Quando não for necessário fixar um Local real:

- criar uma **vinheta regional derivada do cânone**, sem nomear ou inventar um novo Local de Mapa.

---

# 11. EXEMPLO DE APLICAÇÃO — VALES DOS ENFORCADOS

Este capítulo é exemplo operacional, não nova Fonte Regional.

A assinatura constante dos Vales permanece:

- desfiladeiros úmidos e profundos;
- raízes gigantes;
- árvores inclinadas;
- musgo;
- água escura;
- turfa;
- névoa baixa;
- passarelas;
- ruínas suspensas/aprisionadas;
- madeira escura/molhada;
- cinza de pedra úmida;
- verde escuro dessaturado;
- acentos discretos de resina/âmbar.

Fantasia central:

> **A natureza não reconquistou as ruínas; aprisionou-as.**

Para variar skins regionais sem perder a assinatura, distribuir o lote entre famílias como:

### Garganta dos Laços

- paredões altos;
- raízes descendo das paredes;
- restos de estrada;
- estruturas presas no alto;
- cordas e passagens improvisadas;
- leitura vertical estreita.

### Vigília do Vale

- uso minoritário no lote quando a Aparência for regional e não centrada no hub;
- madeira tratada;
- pedra;
- coberturas inclinadas;
- passarelas;
- drenagem;
- Braseiro protegido;
- sensação de ponto de sobrevivência, não vila em árvore.

### Mata Suspensa

- árvores inclinadas;
- níveis verticais;
- raízes formando passagens;
- troncos sustentando ruínas;
- passarelas naturais e artificiais;
- estruturas acima e abaixo do personagem.

### Baixios Enredados

- água escura;
- turfa;
- juncos;
- raízes submersas;
- vegetação fechada;
- terreno baixo e encharcado.

### Claustro das Raízes

- arquitetura asteriana comprimida;
- pedra antiga ainda discernível;
- raízes atravessando estrutura;
- sensação de pressão e confinamento.

### Berço / Masmorras / conteúdo tardio

Somente usar quando o gate narrativo e o momento de obtenção da Aparência permitirem. Se houver dúvida, não usar; preferir uma vinheta regional segura.

A coleção deve parecer uma travessia pelos Vales, **não sessenta personagens diante do mesmo posto de madeira**.

---

## 11.5 Nomenclatura global de arquivos temáticos

Para Aparências temáticas, usar pasta e basename com o slug do tema:

```text
<nome_da_skin>/<nome_da_skin>_<classe>_<raca>_<masculino|feminino>.png
```

Regras: minúsculas, `snake_case`, sem acentos. Exemplos: `cinereo`, `hemario`, `tecelao`, `oraculo`. Esta convenção prevalece sobre exemplos históricos de basename curto dentro das Fontes Especializadas.

---

# 12. TRAJE TEMÁTICO E MATERIALIDADE

A Aparência temática deve ser reconhecível sem uniformizar todas as Classes.

Separar três camadas:

1. **Classe:** arquitetura do torso, proteção, liberdade de movimento, distribuição de equipamento, arma/foco;
2. **Tema/Aparência:** material, acabamento, desgaste, adaptações, elementos recorrentes;
3. **Região:** clima, sujeira, umidade, cinza, vento, calor, vegetação, lama ou corrosão.

Reprovar se as seis Classes de uma Raça parecerem o mesmo traje-base com a arma trocada.

Elementos recorrentes do tema podem existir, mas variar:

- comprimento de capa;
- posição de amarrações;
- distribuição de couro/tecido/metal;
- estado de desgaste;
- bolsas e suportes;
- proteção de pernas/braços;
- detalhes de fechamento;
- tratamento regional.

---

# 13. MODELO DE PROMPT PARA COPIAR E COLAR NO PROJETO

Todo prompt individual de produção futura deve começar com um bloco deste tipo:

```text
Antes de gerar, leia e respeite as fontes disponíveis nesta conversa/projeto, na ordem de autoridade vigente.

Use obrigatoriamente:
- SOURCE_AUTHORITY vigente;
- Fonte Regional vigente, se a skin for regional;
- ASTERION_LORE_BIBLE_CANON vigente;
- ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS vigente;
- ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS vigente;
- Fonte Visual Especializada desta Aparência, se existir;
- ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS quando o fundo representar a Região/Local;
- ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS vigente;
- ASTERION_MATRIZ_DE_PRODUCAO_VISUAL vigente quando houver linha correspondente.

Se alguma Fonte necessária não estiver acessível, não invente a lacuna como fato canônico.
```

Em seguida, o prompt individual deve explicitar:

- nome da Aparência;
- ID/nome do arquivo;
- Raça;
- Classe;
- apresentação;
- identidade fenotípica/individual;
- arma/foco;
- traje;
- estado de pose;
- direção de corpo/cabeça/olhar;
- escala/enquadramento;
- família ambiental/subcenário;
- assinatura regional;
- negativos específicos;
- checklist final.

---

# 14. QA INDIVIDUAL OBRIGATÓRIO

Reprovar a imagem se qualquer item crítico falhar:

1. Formato 1:1 correto.
2. Corpo inteiro, cabeça e pés intactos.
3. Escala dentro do padrão do catálogo; sem aparência de zoom acidental.
4. Câmera neutra; sem grande-angular/foreshortening dominante.
5. Anatomia humanoide íntegra.
6. Raça reconhecível sem texto.
7. Identidade individual preservada quando houver âncora.
8. Classe reconhecível em miniatura.
9. Arma/foco fisicamente coerente e legível.
10. Traje pertence à Classe e ao tema.
11. Pixel art nativa; sem acabamento liso moderno.
12. Região/Aparência reconhecível quando aplicável.
13. Fundo subordinado ao personagem.
14. Fundo não inventa Lore ou Local inexistente.
15. Nenhum spoiler visual indevido.
16. Pose/olhar não repetem mecanicamente o padrão recente do lote.
17. Fundo não é cópia quase idêntica de outro asset.
18. A skin continua parecendo parte do mesmo jogo e do mesmo catálogo.

---

# 15. QA DE LOTE

Além do QA individual, lotes grandes devem ser avaliados em conjunto.

Criar uma grade/contact sheet e verificar:

- uniformidade de tamanho de tela;
- distribuição de altura aparente;
- equilíbrio entre corpos altos, baixos, robustos e esguios sem mudança de zoom;
- diversidade de pose;
- diversidade de direção de olhar;
- distribuição de armas dentro das famílias autorizadas;
- variedade de cabelo e rosto;
- preservação das famílias raciais;
- variedade de subcenários;
- ausência de um único hub/ruína/skyline dominando o lote;
- consistência de paleta regional;
- consistência de pixel art;
- ausência de uma Classe inteira com o mesmo traje-base;
- ausência de uma Raça inteira com o mesmo rosto/penteado;
- nenhum asset claramente maior ou menor por erro de câmera.

Se a grade parecer uma sequência de variações do mesmo pôster, o lote ainda não está aprovado.

---

# 16. FLUXO PADRÃO PARA UMA NOVA APARÊNCIA TEMÁTICA

## Etapa 1 — confirmar cânone

Localizar:

- origem/recompensa da Aparência;
- Região e gate de progressão;
- Classes e Raças envolvidas;
- restrições narrativas;
- conteúdo visual permitido.

## Etapa 2 — criar Fonte Visual Especializada quando necessário

Para levas grandes, especialmente `5 Raças × 6 Classes × 2 apresentações`, criar:

`ASTERION_APARENCIA_<NOME>_FONTE_VISUAL_v1.0.md`

Ela deve fechar:

- identidade da coleção;
- materiais do tema;
- variedade de armamento permitida;
- distribuição de poses/olhares;
- matriz de fundos/subcenários;
- exceções explícitas ao padrão global;
- QA específico.

## Etapa 3 — construir matriz dos assets

Antes de gerar as imagens, cada asset deve possuir:

- ID;
- Raça;
- Classe;
- apresentação;
- idade aproximada;
- pele/subtom;
- cabelo;
- rosto/marcadores;
- corpo;
- pose;
- olhar;
- arma/foco;
- subcenário;
- arquivo final.

## Etapa 4 — calibrar

Gerar 6–10 assets de teste e conferir:

- escala;
- câmera;
- pixel art;
- leitura racial;
- leitura de Classe;
- assinatura temática;
- fundo.

## Etapa 5 — produção

Somente após calibração, produzir o restante do lote na ordem definida pela Matriz/Fonte Especializada.

## Etapa 6 — QA de lote

Avaliar contact sheet antes de considerar a coleção encerrada.

---

# 17. CONTINUIDADE E RETROATIVIDADE

Este padrão entra em vigor para:

- novas Aparências temáticas;
- novas versões ainda não fechadas de Aparências em produção;
- regenerações solicitadas explicitamente.

Não reabre automaticamente:

- assets antigos já aprovados;
- `Errante das Cinzas v1.2.2`;
- Aparências concluídas que não apresentem problema visual relatado.

Quando uma coleção antiga for revisitada, aplicar este padrão apenas se a revisão for deliberadamente aberta.

---

# 18. PRINCÍPIOS FINAIS

> **Mesma escala de jogo, não mesmo corpo.**

> **Mesma assinatura regional, não mesmo cenário.**

> **Mesma Classe reconhecível, não mesma pose.**

> **Mesma Raça reconhecível, não mesmo rosto.**

> **Mesmo tema, não mesmo traje.**

> **Asterion deve parecer um único jogo mesmo quando cada skin for produzida em um momento diferente.**

---

# DOCUMENTO INCORPORADO 5/9
## Arquivo original: `ASTERION_APARENCIA_ERRANTE_DAS_CINZAS_FONTE_VISUAL_v1.3.md`
# ASTERION — APARÊNCIA ERRANTE DAS CINZAS · FONTE VISUAL ESPECIALIZADA v1.3

**Data de consolidação:** 2026-10-08  
**Escopo:** produção das 60 imagens da Aparência cosmética regional `Errante das Cinzas` — 5 Raças × 6 Classes × 2 apresentações  
**Estado:** fonte visual especializada aprovada para produção; subordinada às autoridades canônicas vigentes  

**Revisão v1.2:** amplia, exclusivamente para `Errante das Cinzas`, a variedade visual de armamento por Classe. Sentinela pode abandonar o escudo em parte do lote e usar armamento pesado ou duplo; Vigia pode usar besta de mão e duas bestas de mão; Tecelão, Oráculo e Luminar podem converter seus focos em armas mágicas fisicamente legíveis. A mudança é visual/editorial, não cria proficiência, loadout, dano, bônus ou regra mecânica de equipamento.

**Revisão v1.2.1:** corrige a distribuição de composição do lote sem alterar identidade, armas, fenótipos, fundos ou mecânicas. As 60 poses foram revisadas como conjunto para impedir repetição consecutiva da direção dominante do olhar e reduzir o viés visual de personagens olhando para o mesmo lado. Cada asset passa a ter vetor de cabeça/olhar explícito e obrigatório.

**Revisão v1.2.2:** QA final da distribuição móvel de olhares. Corrige os assets 31 e 51 para que **qualquer janela consecutiva de 6 assets** cumpra o mínimo de quatro vetores distintos de cabeça/olhar definido nesta própria Fonte. Nenhuma arma, fenótipo, corpo, fundo, identidade racial, identidade de Classe ou regra mecânica foi alterada.

> Esta Fonte não cria regra mecânica de equipamento, Classe, Raça, bônus, dano, Inventário, progressão ou Cosmético. Ela define somente a identidade visual e o método de produção da Aparência `Errante das Cinzas`.

## 1. Autoridades preservadas

- `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.16_FINAL.md` — define a Aparência `Errante das Cinzas` como recompensa do Feito oculto **Entre Aquilo que Caça**.
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` — define fenótipos raciais, silhuetas e assinaturas de Classe.
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` — define formato, pixel art, anatomia, área segura, armas/focos e QA.
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` — permanece válida no que não for explicitamente substituído por esta Fonte especializada.
- `SOURCE_AUTHORITY.md` — mantém a hierarquia documental global.

## 2. Decisão operacional nova — independência das 60 identidades

Para `Errante das Cinzas`, as 60 imagens deixam de ser produzidas como “a mesma pessoa da Aparência padrão com roupa diferente”. Cada combinação Raça × Classe × apresentação é tratada como **um indivíduo novo e autônomo**, criado diretamente das regras raciais, de Classe e do tema regional.

Esta decisão substitui, **somente para o lote Errante das Cinzas**, a regra operacional anterior da Matriz v1.3 que preservava rosto, cabelo e pose da Aparência padrão. Não altera Lore racial nem a existência da Aparência padrão.

Consequências obrigatórias:

- não usar imagem da Aparência padrão como referência;
- não copiar rosto, cabelo, barba, cicatriz, pose ou direção do olhar da skin-base;
- cada uma das 60 imagens deve representar pessoa distinta;
- identidade racial deve vir do **fenótipo**, não da repetição de um rosto oficial;
- identidade de Classe deve vir de **silhueta + vestuário + arma/foco + gestual**;
- identidade temática deve vir de **materiais, desgaste, cinza/fuligem e fundo regional**, nunca de transformação corporal ou “poder de cinza”.

## 3. Núcleo temático — Errante das Cinzas

Leitura desejada: **alguém que atravessou as Terras do Ocaso por tempo suficiente para adaptar tudo que veste e carrega, sem ser transformado sobrenaturalmente pela Região.**

### 3.1 Materiais obrigatórios

- tecido seco, desbotado e muito usado;
- cinza e fuligem físicas depositadas em roupa, botas, bainhas, escudo, foco e equipamento;
- couro ressecado, mantido e reparado;
- metal fosco, escurecido, oxidado ou substituído por peças de acabamentos diferentes;
- costuras, remendos, rebites, fivelas e reforços que indiquem manutenção real;
- nenhuma peça precisa parecer miserável: desgaste deve comunicar **uso prolongado + competência de manutenção**.

### 3.2 Proibições temáticas

- nenhum poder de cinzas;
- nenhuma transformação corporal causada pela Região;
- nenhuma pele coberta por rachaduras de brasa;
- nenhum fogo permanente no corpo, no ambiente ou como “poder de cinza”; **fogo/energia localizada em uma arma-foco de Classe é permitido quando vier da linguagem do Tecelão, Oráculo ou Luminar e não da Região**;
- nenhum glow de raridade;
- nenhuma aura de fuligem;
- nenhuma associação automática a morto-vivo;
- nenhuma roupa nova/polida que negue a travessia.

## 4. Paleta e linguagem material

Dominantes: carvão, cinza frio, marrom ressecado, preto queimado, couro escuro, ferro oxidado e tecido bege/cinza morto. Acentos pequenos de ferrugem profunda, bronze escurecido ou âmbar de brasa são permitidos apenas quando fisicamente justificados.

A Região deve parecer **depois do incêndio**, não um inferno vulcânico ativo.

## 5. Fundo temático compartilhado — padronização sem repetição

Todas as 60 imagens usam a mesma **família ambiental** das Terras do Ocaso. O fundo não é idêntico; ele gira entre cinco vinhetas seguras e não-spoiler, sempre rasas, discretas e subordinadas ao personagem:

1. **Estrada de cinzas:** trecho antigo de estrada coberto por cinza fina, marco de pedra gasto, cerca quebrada baixa, vegetação morta e céu frio; sem cidade monumental.
2. **Charneca de fuligem:** terreno aberto e irregular com montes baixos de fuligem, arbustos secos, covas rasas e pedra escurecida; horizonte simples, sem fogo ativo.
3. **Borda do bosque calcinado:** poucos troncos negros, raízes expostas, chão cinzento e uma ou duas brasas profundas muito discretas; nunca floresta inteira em chamas.
4. **Passagem das ruínas:** fragmento próximo de passagem defensiva em pedra escura, ferragens oxidadas e piso com cinza; arquitetura simples, sem revelar Âncora ou Câmara do Poente.
5. **Caminho quebrado:** pequena ponte ou calçamento partido entre pedra antiga, madeira carbonizada e poeira de cinza; fundo raso e funcional, sem skyline épico.

Elementos comuns obrigatórios da família de fundo: cinza/fuligem no piso, céu ou luz fria dessaturada quando visível, vegetação seca ou pedra escurecida, profundidade baixa e ausência de skyline épico. Não mostrar Âncora, Câmara do Poente, Avesso, portal ou revelação cosmológica.

## 6. Diversidade individual obrigatória

O lote deve evitar o problema observado nas skins-base: “mesma pessoa, mesma cabeça e mesmo 3/4 olhando para o mesmo lado”. Para aprovação, distribuir conscientemente:

- frontal, 3/4 esquerdo, 3/4 direito e perfis parciais;
- cabeça olhando esquerda, direita, frente, alto, baixo e sobre o ombro;
- peso corporal na perna dianteira, traseira, lateral ou central;
- Repouso, Contemplação, Vigilância, Deslocamento, Preparação e Ação controlada;
- cabelos curtos, médios, longos, presos, parcialmente presos, trançados, locs, cachos, cortes assimétricos e grisalhos quando racialmente coerentes;
- rostos largos, estreitos, angulares, ovais, quadrados ou alongados dentro do centro fenotípico de cada Raça;
- idades adultas variadas;
- corpos esguios, médios, altos, compactos, densos ou robustos dentro das tendências raciais;
- cicatrizes e sinais individuais apenas quando discretos e plausíveis.

**Regra de lote:** nenhum par consecutivo deve repetir simultaneamente orientação do torso + direção da cabeça + posição dominante da arma. O mesmo penteado exato não deve aparecer duas vezes dentro da mesma Raça.

### 6.1 Distribuição obrigatória de cabeça e olhar

- a **direção dominante do olhar não pode se repetir em dois assets consecutivos**;
- em qualquer bloco de 6 assets consecutivos, usar pelo menos quatro vetores claramente diferentes entre esquerda, direita, frente, acima, abaixo e sobre o ombro;
- evitar sequências visuais em que três personagens próximos pareçam olhar para o mesmo lado, mesmo quando o torso ou a arma variem;
- a direção de cabeça/olhar escrita na matriz é **obrigatória** e deve prevalecer sobre qualquer tendência automática do gerador;
- cabeça, torso e arma devem formar vetores independentes sempre que a pose permitir, evitando o padrão repetitivo de 3/4 + rosto para o mesmo lado.

## 7. Regras raciais

A anatomia racial v2.0 da Bíblia Visual é obrigatória nesta Aparência e nunca pode ser apagada por capuz, elmo, cabelo, pose ou material temático.

### Remanescente
- **Núcleo:** polo humano e maior diversidade interna; não pode virar “humano genérico”.
- **Anatomia:** proporção humana normal, sem chifres, orelhas racialmente alongadas ou dentição aumentada obrigatória.
- **Variação:** tons de pele, cabelos, rostos e constituições amplos; a individualidade deve fazer a leitura funcionar.
- **Evitar:** inventar apêndice racial extraordinário para diferenciá-lo.

### Velado
- **Núcleo:** porte menor e esguio, presença silenciosa e percepção corporal controlada.
- **Anatomia obrigatória:** orelhas largas abertas lateralmente e recuadas; olhos proporcionalmente maiores; dedos longos; rosto mais estreito.
- **Equipamento:** capuzes/elmos devem acomodar as orelhas sem escondê-las nem convertê-las em orelhas élficas.
- **Evitar:** elfo alto, goblin verde, gnomo caricatural, vampiro, cadáver, orelhas longas ascendentes de Alvorano.

### Cinéreo
- **Núcleo:** corpo compacto/denso, sensação de sustentação e força estrutural.
- **Anatomia obrigatória:** mãos grandes, ossatura facial forte, mandíbula/pescoço marcados e caninos inferiores curtos discretamente aumentados.
- **Equipamento:** massa vem da constituição real, não de zoom ou armadura inflada.
- **Evitar:** anão ou orc copiado, pele de pedra, magma, cristal, golem humano.

### Hemário
- **Núcleo:** vitalidade vascular e contraste quente; corpo intensamente vivo, nunca morto-vivo.
- **Anatomia obrigatória:** exatamente um par de chifres de queratina integrado ao crânio; assinatura vascular quente.
- **Equipamento:** capuzes/elmos devem respeitar base, direção e volume dos chifres.
- **Evitar:** vampiro, demônio, tiefling copiado, asas, cascos, cauda obrigatória, presas vampíricas ou sangue decorativo.

### Alvorano
- **Núcleo:** porte mais alto/alongado, coordenação e prontidão neuromuscular.
- **Anatomia obrigatória:** orelhas longas e pontiagudas orientadas para cima e para trás; membros discretamente alongados.
- **Equipamento:** proteções de cabeça devem acomodar as orelhas sem escondê-las por padrão.
- **Evitar:** elfo copiado, halo, asas, pele metálica dourada, brilho corporal racial ou estética angelical.

## 8. Regras de Classe

### Sentinela

- **Núcleo:** Resistência, posição e Retaliação. A leitura vem de base firme, torso protegido, massa de equipamento e postura preparada para absorver ou devolver impacto — **não depende obrigatoriamente de escudo nesta Aparência**.
- **Traje:** armadura média/pesada de estrada, placas parciais, malha localizada, couro reforçado, proteção legível em torso/ombros/antebraços; cintura menos carregada que a do Errante.
- **Arma/foco:** variar entre **arma de uma mão + escudo**, **espada de duas mãos**, **martelo de duas mãos**, **lança curta + escudo** e **duas espadas longas**. Quando não houver escudo, compensar a leitura de Sentinela com armadura mais blocada, base firme e postura de guarda/Retaliação.
- **Extraordinário:** nenhum efeito sobrenatural necessário; ameaça física, defensiva e de contra-impacto.
- **Evitar:** paladino, cavaleiro sagrado, berserker, dual wield acrobático de Errante, armadura ornamental ou escudo com iconografia religiosa.

### Errante

- **Núcleo:** Mobilidade, brechas e Oportunismo. Silhueta assimétrica, pernas livres, centro de gravidade móvel e equipamento rente ao corpo.
- **Traje:** proteção leve/média, casaco curto ou dividido, couro e tecido reforçado, pequenas placas, bainhas compactas e pouca massa nos ombros.
- **Arma/foco:** **duas armas curtas e rápidas** visíveis, de preferência uma em cada mão quando a pose permitir: adagas, facas longas, duas lâminas curtas ou espada curta + adaga.
- **Extraordinário:** sem efeito mágico; movimento e leitura de brecha fazem a Classe.
- **Evitar:** ladrão encapuzado obrigatório, ninja, duas espadas longas, armamento pesado de Sentinela, excesso de bolsas decorativas.

### Vigia

- **Núcleo:** Observação acumulada transformada em precisão. Olhos, postura e arma de disparo formam o mesmo eixo de leitura.
- **Traje:** proteção leve/média, capa curta controlada, proteção funcional de antebraço, arnês, aljava ou sistema de virotes claramente legível.
- **Arma/foco:** variar entre **arco**, **besta**, **besta de mão** e **duas bestas de mão, uma em cada mão**. Faca/adaga de campo pode ser secundária. Dupla besta deve parecer ferramenta de precisão compacta, não pistola moderna.
- **Extraordinário:** nenhuma mira mágica; precisão deve nascer da postura, do olhar e do equipamento.
- **Evitar:** sniper moderno, estética militar contemporânea, arma de fogo disfarçada, ranger de floresta obrigatório.

### Tecelão

- **Núcleo:** Manipulação técnica da Trama: Perceber → Tensionar → Resolver. Mãos e foco parecem operar relações físicas e tensões, não êxtase mágico.
- **Traje:** casaco técnico/sobreposição estruturada, mangas ajustadas, braceletes ou luvas técnicas, placas de medida, fixações e pequenos instrumentos físicos.
- **Arma/foco:** **arma mágica que também é instrumento técnico de Trama**: adaga-foco, espada curta-foco, lâmina-foco, bastão-foco, cetro técnico, agulha/fuso ou haste segmentada. É especialmente aprovada a família de **adaga ou espada ornamentada com um fio/filamento de Trama emergindo da arma**.
- **Extraordinário:** efeito opcional e contido: poucas linhas tensionadas, pontos conectados, reação material localizada ou **fio/aresta ígnea muito localizada na arma-foco**. O fogo pertence ao foco/Trama, nunca à cinza regional; nunca “mana líquida”.
- **Evitar:** espada comum sem função de foco, mago clássico, cajado arcano genérico, holograma, portal, galáxia, runas nórdicas copiadas.

### Oráculo

- **Núcleo:** Leitura de possibilidades próximas. O corpo parece perceber uma alternativa antes de se comprometer com o movimento.
- **Traje:** camadas verticais de viagem, suporte para placas/fios/lâminas simbólicas, marcadores pequenos e repetidos, assimetria de observação e não de acrobacia.
- **Arma/foco:** **arma mágica simbólica/oracular**: cajado/cetro marcado, bastão oracular, adaga ritual, espada curta simbólica, lâmina curva ou duas lâminas simbólicas. O objeto deve parecer instrumento de interpretação de possibilidades, não ferramenta técnica de Trama.
- **Extraordinário:** efeito opcional muito sutil: trajetória incompleta, duplicação breve de gesto, sinais convergentes ou brilho localizado em marcas da arma; não mostrar futuro literal.
- **Evitar:** bola de cristal, terceiro olho, tarot moderno, zodíaco, relógios quebrados, profecia holográfica, cartomante teatral ou foco técnico de Tecelão.

### Luminar

- **Núcleo:** Vitalidade exteriorizada como Luz. A silhueta é firme, centrada e construída para permanência e sustentação.
- **Traje:** proteção funcional de estrada, frente do torso clara, fechos estáveis, braços livres para sustentação/projeção; sem linguagem sacerdotal.
- **Arma/foco:** família principal de **arma-foco luminosa fisicamente utilizável**. Cajado e bastão continuam centrais, mas podem alternar com **espada-foco, maça-foco ou lança curta-foco** quando a leitura de Luz permanecer inequívoca.
- **Extraordinário:** Luz pode estar ausente ou localizada em pequena intensidade; quando ativa, percorre ou emerge do praticante/foco de forma concentrada, nunca da cinza.
- **Evitar:** paladino cristão, cruz, halo, asas, deus solar, branco/dourado como atalho moral, sacerdote genérico ou arma comum sem leitura de foco.

### 8.1 Regra de variedade do lote

- nenhuma família de armamento deve ocupar todas as 10 imagens de uma Classe;
- Sentinela deve conter exemplos **com e sem escudo**;
- Vigia deve conter pelo menos dois exemplos de **duas bestas de mão**;
- Tecelão deve conter pelo menos dois exemplos de **lâmina-foco** e pelo menos um exemplo da família **lâmina ornamentada + fio/filamento de Trama**;
- Oráculo deve alternar armas longas e lâminas simbólicas;
- Luminar deve preservar cajado/bastão como família mais frequente, mas incluir pelo menos duas armas-foco não-cajado;
- a variedade nunca pode apagar a leitura de Classe, Raça ou tema `Errante das Cinzas`.

## 9. Nomenclatura e armazenamento

Para preservar identificação inequívoca fora da pasta, o tema aparece **na pasta e no nome do arquivo**:

```text
errante_das_cinzas/errante_das_cinzas_<classe>_<raca>_<masculino|feminino>.png
```

Exemplos:

```text
errante_das_cinzas/errante_das_cinzas_sentinela_remanescente_masculino.png
errante_das_cinzas/errante_das_cinzas_tecelao_velado_feminino.png
errante_das_cinzas/errante_das_cinzas_luminar_alvorano_feminino.png
```

## 10. Especificação técnica comum

- master 1:1, 1024×1024, PNG;
- corpo inteiro; cabeça e pés completos;
- figura normalmente em 72–84% da altura;
- margem segura em todos os lados;
- pixels deliberadamente visíveis; fim da era 16-bit / início da era 32-bit;
- formas grandes antes do microdetalhe;
- materiais físicos antes de efeitos;
- fundo com contraste e detalhe inferiores aos do personagem;
- anatomia humanoide correta; mãos coerentes; armas/focos fisicamente conectados;
- sem texto legível, UI, moldura ou logo.

## 11. Matriz de identidade dos 60 assets

| # | Raça | Classe | Apres. | Idade | Fenótipo / rosto / cabelo | Corpo | Pose e olhar | Fundo | Arquivo |
|---:|---|---|---|---:|---|---|---|---|---|
| 01 | Remanescente | Sentinela | M | 36 | negra retinta de subtom neutro-quente; rosto retangular com nariz largo, sobrancelhas densas e pequena cicatriz vertical na bochecha direita; cabelo crespo preto muito curto com topo ligeiramente mais cheio | alto, ombros largos, físico funcional | base ampla quase frontal; escudo avançado à esquerda e espada longa baixa à direita; cabeça levemente virada para a direita, olhar firme passando por cima do escudo | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_sentinela_remanescente_masculino.png` |
| 02 | Remanescente | Errante | M | 27 | castanha média quente; rosto oval curto, nariz reto largo, maxilar estreito e barba curta irregular; tranças curtas presas para trás com laterais bem baixas | médio e ágil, pernas longas | passo diagonal para a esquerda, torso gira para a direita; espada curta baixa e adaga próxima ao peito; cabeça gira sobre o ombro esquerdo e o olhar busca uma abertura à esquerda | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_errante_remanescente_masculino.png` |
| 03 | Remanescente | Vigia | M | 43 | bronzeada escura; rosto alongado, maçãs altas, nariz aquilino discreto e barba grisalha curta; locs pretos médios presos em meio coque baixo | esguio, alto e resistente | corpo em 3/4 esquerdo, arco longo baixo na mão e aljava totalmente legível; cabeça quase frontal e olhar ligeiramente acima da linha do observador, como acompanhando movimento distante | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_vigia_remanescente_masculino.png` |
| 04 | Remanescente | Tecelão | M | 31 | castanha clara oliva quente; rosto triangular, sobrancelhas arqueadas, nariz arredondado e sem barba; cachos escuros médios com uma lateral raspada | médio, braços longos e mãos precisas | 3/4 direito, adaga-foco ornamentada baixa com fino filamento de Trama saindo do pomo/lâmina; mão livre pinça a linha; cabeça inclinada para baixo à esquerda, olhos seguindo o filamento entre dois pontos | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_tecelao_remanescente_masculino.png` |
| 05 | Remanescente | Oráculo | M | 49 | negra de subtom frio-neutro; rosto largo, olhos fundos, nariz curto e barba fechada com grisalho nas laterais; cabelo crespo curto com entrada natural e fios grisalhos | compacto e magro, postura paciente | 3/4 esquerdo, espada curta simbólica baixa e mão livre tocando um pequeno marcador; corpo aponta para uma rota, enquanto cabeça e olhar se deslocam para uma possibilidade acima à direita | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_oraculo_remanescente_masculino.png` |
| 06 | Remanescente | Luminar | M | 34 | castanha escura quente; rosto quadrado, nariz largo, olhos grandes e bigode curto separado da barba; ondulado preto curto penteado para trás de modo irregular | médio robusto, peito aberto | frontal centrado, cajado médio de combate-foco apoiado no chão ao lado do corpo; uma mão no foco e outra relaxada junto ao torso; cabeça alinhada ao corpo e olhar direto para a frente, calmo e sustentado | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_luminar_remanescente_masculino.png` |
| 07 | Remanescente | Sentinela | F | 41 | castanha média dourada; rosto arredondado com queixo forte, nariz largo, pequena marca antiga sobre a sobrancelha esquerda; cachos castanho-escuros presos em coque alto baixo-volume, com mechas soltas | média robusta e firme | corpo em 3/4 direito, peso na perna traseira; espada de duas mãos apoiada em guarda baixa sem escudo; cabeça voltada para a esquerda, como ouvindo uma aproximação fora do quadro | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_sentinela_remanescente_feminino.png` |
| 08 | Remanescente | Errante | F | 24 | negra retinta; rosto fino com maçãs altas, nariz médio e sobrancelhas retas; microtranças pretas de comprimento médio, parte presas e parte soltas | esguia, muito móvel | corpo em perfil parcial direito, joelhos baixos, duas adagas em alturas diferentes; cabeça acompanha o vetor do corpo e o olhar corta para a direita, avaliando uma abertura | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_errante_remanescente_feminino.png` |
| 09 | Remanescente | Vigia | F | 38 | bronzeada média; rosto oval alongado, nariz curvo discreto e olhos estreitos; locs curtos castanho-escuros presos para trás por tira de tecido | alta, braços fortes e postura ereta | perfil direito quase completo, duas bestas de mão baixas, uma em cada mão, sem postura de pistoleiro; arnês de virotes legível; cabeça gira por cima do ombro esquerdo e o olhar sobe para a esquerda | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_vigia_remanescente_feminino.png` |
| 10 | Remanescente | Tecelão | F | 29 | castanha escura avermelhada; rosto em coração, nariz curto, lábios cheios e duas pequenas cicatrizes de trabalho na mandíbula; cabelo crespo curto assimétrico, mais cheio à direita | média, mãos finas e precisas | frontal assimétrico, espada curta-foco com aresta ígnea localizada na mão esquerda baixa e mão direita aberta sobre uma tensão; cabeça baixa e olhar dirigido para baixo à direita, acompanhando o ponto de resolução | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_tecelao_remanescente_feminino.png` |
| 11 | Remanescente | Oráculo | F | 46 | castanha clara quente; rosto largo, nariz longo, olhos fundos e linhas de idade visíveis; ondulado castanho-escuro até os ombros, parcialmente trançado na lateral | média esguia, presença calma | frontal ligeiramente deslocado, lâmina ritual longa baixa com marcas discretas e bastão curto preso ao corpo; cabeça quase reta e olhos fixos para a frente, como aguardando uma possibilidade se confirmar | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_oraculo_remanescente_feminino.png` |
| 12 | Remanescente | Luminar | F | 33 | negra de subtom quente; rosto quadrado suave, nariz largo, sobrancelhas fortes e sorriso ausente mas expressão acolhedora; cachos pretos presos em coque baixo com franja curta natural | forte e equilibrada | 3/4 direito, maça-foco curta mantida horizontalmente baixa; pequeno traço de Luz no núcleo da arma, ombros abertos; cabeça voltada à esquerda e olhar atento para alguém fora do quadro | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_luminar_remanescente_feminino.png` |
| 13 | Velado | Sentinela | M | 32 | clara fria; rosto oval longo, mandíbula estreita, nariz reto e olhos cinza-aço muito estáveis; preto profundo liso até a mandíbula, repartido no centro | alto e longilíneo | 3/4 esquerdo com um pé sobre pedra baixa; escudo estreito protegendo o flanco e martelo de uma mão relaxado mas pronto; cabeça gira discretamente para a direita e o olhar desce para o terreno próximo | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_sentinela_velado_masculino.png` |
| 14 | Velado | Errante | M | 45 | oliva muito clara fria; rosto estreito, maçãs discretas, nariz longo e olhos verde-cinza; castanho-acinzentado liso médio preso em rabo baixo | esguio, ombros estreitos | avanço curto para a frente com o torso levemente inclinado; duas lâminas abertas em V baixo; cabeça solta do eixo do torso e olhar nítido para a esquerda | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_errante_velado_masculino.png` |
| 15 | Velado | Vigia | M | 28 | pálida neutra-fria; rosto simétrico, nariz fino, olhos azul-acinzentados e sobrancelhas quase retas; prateado escuro curto, penteado para trás sem volume | alto, leve e alinhado | corpo frontal com besta leve baixa atravessando a linha do quadril, sem mirar; cabeça alinhada ao observador e olhos no horizonte, ligeiramente acima da linha frontal | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_vigia_velado_masculino.png` |
| 16 | Velado | Tecelão | M | 37 | clara fria com sardas discretas; rosto alongado, queixo fino, nariz reto curto e olhos cinza-esverdeados; preto liso médio com mecha frontal longa presa atrás da orelha | médio esguio, braços longos | perfil esquerdo, cetro técnico próximo ao antebraço e mão livre alinhando dois pontos no espaço; cabeça gira parcialmente para a direita em direção ao observador, olhos verificando o segundo ponto | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_tecelao_velado_masculino.png` |
| 17 | Velado | Oráculo | M | 51 | oliva pálida fria; rosto muito fino, olhos castanho-frio, nariz aquilino discreto e linhas de idade limpas; cinza-prata liso até a nuca, preso por faixa estreita | alto e magro, presença imóvel | perfil direito com cajado oracular esguio apoiado; mão livre segura pequena placa opaca; cabeça retorna para a esquerda e o olhar desce até a placa, como comparando alternativas | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_oraculo_velado_masculino.png` |
| 18 | Velado | Luminar | M | 30 | clara neutra; rosto oval, nariz médio, olhos azul-cinza e boca estreita; branco-prateado curto com laterais longas e topo penteado para trás | médio longilíneo | perfil esquerdo, cajado médio vertical próximo ao corpo; mão livre aberta junto ao peito sem gesto religioso; cabeça gira para a frente e o olhar repousa diretamente adiante | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_luminar_velado_masculino.png` |
| 19 | Velado | Sentinela | F | 35 | pálida fria; rosto oval longo, olhos aço, nariz delicado e sobrancelhas definidas; preto liso longo preso em trança única baixa | alta, muito esguia | quase perfil direito; duas espadas longas mantidas em guarda baixa e compacta, sem acrobacia; cabeça acompanha parcialmente o perfil e o olhar permanece firme para a direita, fora do quadro | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_sentinela_velado_feminino.png` |
| 20 | Velado | Errante | F | 44 | oliva muito clara neutra; rosto estreito, maçãs altas, nariz longo e olhos verde dessaturado; prateado médio em corte reto na altura do queixo | média longilínea, postura precisa | 3/4 esquerdo, uma lâmina junto à coxa e outra recuada atrás do quadril; cabeça gira contra o movimento e olhos apontam para a esquerda, antecipando perseguição | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_errante_velado_feminino.png` |
| 21 | Velado | Vigia | F | 26 | clara fria; rosto quase triangular, olhos cinza-azulados grandes, nariz curto e queixo fino; castanho-acinzentado liso longo preso em dois segmentos baixos | alta e leve | 3/4 direito com arco inclinado diagonalmente; uma perna elevada em pedra baixa; cabeça quase frontal e olhar para baixo diante dos pés, como lendo rastros | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_vigia_velado_feminino.png` |
| 22 | Velado | Tecelão | F | 39 | pálida neutra; rosto oval simétrico, olhos castanho-frio, nariz reto e cicatriz muito fina no lábio superior; preto liso curto com franja lateral longa | média esguia, braços precisos | 3/4 esquerdo, fuso técnico horizontal junto ao torso; mão livre mede uma distância curta; cabeça ergue levemente e o olhar sobe para a direita, alinhando um ponto distante | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_tecelao_velado_feminino.png` |
| 23 | Velado | Oráculo | F | 48 | clara muito fria; rosto alongado, olhos cinza-claro, nariz aquilino e linhas finas ao redor dos olhos; branco-prateado ondulado leve até os ombros, metade preso | alta e delgada | 3/4 direito, duas lâminas simbólicas mantidas baixas e separadas; marcas mínimas nas lâminas sugerem possibilidades concorrentes; cabeça frontal e olhar fixo diretamente adiante em um ponto de possível falha | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_oraculo_velado_feminino.png` |
| 24 | Velado | Luminar | F | 31 | oliva pálida fria; rosto oval curto para padrão Velado, olhos verde-cinza, nariz médio e maxilar estreito; preto profundo liso preso em coque baixo extremamente simples | média alta, firme sem massa excessiva | frontal com leve passo adiante, espada-foco luminosa em diagonal baixa; pequena Luz localizada apenas ao longo do canal central da lâmina; cabeça baixa e olhar dirigido para a esquerda, acompanhando a linha da arma | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_luminar_velado_feminino.png` |
| 25 | Cinéreo | Sentinela | M | 47 | castanha média terrosa; rosto quadrado largo, mandíbula forte, nariz largo e sobrancelhas espessas; preto ondulado muito denso, curto, com fios grisalhos nas têmporas | alto, denso e assentado | posição compacta e assentada, joelhos flexionados; martelo de duas mãos atravessando diagonal baixa, sem escudo; cabeça ergue para a direita e o olhar acompanha algo acima sob o vento de cinza | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_sentinela_cinereo_masculino.png` |
| 26 | Cinéreo | Errante | M | 29 | negra retinta de subtom quente; rosto oval largo, nariz curto, maçãs fortes e barba curta fechada; crespo preto baixo com topo arredondado denso | compacto e musculoso sem exagero | passo lateral firme sobre terreno irregular; facas em pegadas diferentes, uma baixa e outra protegendo o centro; cabeça quase frontal e olhar baixo, lendo o espaço imediato à frente | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_errante_cinereo_masculino.png` |
| 27 | Cinéreo | Vigia | M | 38 | bronzeada escura; rosto retangular, nariz aquilino largo, olhos fundos e barba curta apenas no queixo; cacheado castanho muito escuro médio preso para trás | alto e robusto, pernas grossas | perfil esquerdo, arco robusto apoiado no ombro; mão livre junto à faca de campo sem sacá-la; cabeça permanece no perfil e o olhar se projeta para a esquerda, além do quadro | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_vigia_cinereo_masculino.png` |
| 28 | Cinéreo | Tecelão | M | 52 | castanha escura neutra; rosto largo envelhecido, nariz quebrado antigo, sobrancelhas grossas e barba grisalha curta; preto muito curto e denso, fortemente grisalho nas laterais | compacto, mãos grandes e ombros firmes | corpo frontal compacto, haste segmentada apoiada diagonalmente; ambas as mãos próximas ao foco como ajustando tensão; cabeça gira para a direita e os olhos verificam um ponto lateral da Trama | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_tecelao_cinereo_masculino.png` |
| 29 | Cinéreo | Oráculo | M | 34 | bronzeada média terrosa; rosto trapezoidal, nariz largo, olhos pequenos e maxilar marcado; ondulado preto curto com franja pesada lateral | médio denso, centro de gravidade baixo | quase frontal, lâmina curta assimétrica marcada ao lado do corpo; fios curtos entre dedos da mão livre, sem efeito brilhante; cabeça alinhada e olhos baixos para o centro frontal, como comparando duas possibilidades próximas | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_oraculo_cinereo_masculino.png` |
| 30 | Cinéreo | Luminar | M | 42 | negra de subtom neutro; rosto quadrado, maçãs largas, nariz reto e barba cheia curta; crespo preto médio em torções curtas presas atrás | alto e muito firme | 3/4 esquerdo, cajado curto apoiado no ombro sem pose heroica; outra mão junto ao centro do torso; cabeça se volta à esquerda e o olhar acompanha uma presença fora do quadro | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_luminar_cinereo_masculino.png` |
| 31 | Cinéreo | Sentinela | F | 36 | negra retinta quente; rosto quadrado suave, nariz largo, sobrancelhas espessas e cicatriz curta na testa; crespo preto curto e muito denso, laterais naturais | robusta estável, pernas fortes | corpo frontal com peso assimétrico; escudo redondo apoiado no braço fora do centro e maça baixa; cabeça inclinada para a direita, olhos baixando para o flanco direito como avaliando um ataque próximo | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_sentinela_cinereo_feminino.png` |
| 32 | Cinéreo | Errante | F | 27 | castanha média terrosa; rosto oval largo, nariz curto, olhos grandes e queixo forte; cacheado castanho-escuro médio preso em rabo baixo espesso | compacta e móvel | corpo quase frontal, uma perna já cruzando a outra para mudar de direção; lâmina de corte baixa e adaga curta alta; cabeça permanece frontal e o olhar sobe ligeiramente acima do observador | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_errante_cinereo_feminino.png` |
| 33 | Cinéreo | Vigia | F | 45 | bronzeada escura; rosto retangular com maçãs fortes, nariz longo e linhas de vento na pele; ondulado preto grosso até os ombros, preso em trança simples | alta e densa, mãos largas | 3/4 esquerdo em postura alta, duas bestas de mão compactas mantidas em alturas diferentes; sistema de virotes no arnês; cabeça acompanha a esquerda e o olhar distante segue o mesmo lado | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_vigia_cinereo_feminino.png` |
| 34 | Cinéreo | Tecelão | F | 32 | castanha escura quente; rosto largo, nariz arredondado, sobrancelhas retas e pequena cicatriz no queixo; crespo preto com laterais curtas e topo alto compacto | média robusta, braços fortes | 3/4 direito, adaga-foco robusta baixa e mão livre afastada do corpo; uma única linha tensionada liga foco e ponto próximo; cabeça baixa para a direita, olhos presos ao ponto de tensão | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_tecelao_cinereo_feminino.png` |
| 35 | Cinéreo | Oráculo | F | 50 | negra de subtom neutro-terroso; rosto quadrado alongado, nariz largo, olhos fundos e linhas de idade marcadas; cacheado muito escuro curto com grisalho visível na frente | alta, densa e extremamente estável | perfil esquerdo, cetro assimétrico perto do corpo e adaga ritual baixa na outra mão; gesto interrompido; cabeça gira para a frente e o olhar encontra diretamente o espaço diante do personagem | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_oraculo_cinereo_feminino.png` |
| 36 | Cinéreo | Luminar | F | 30 | bronzeada média; rosto oval de mandíbula forte, nariz reto e maçãs marcadas; ondulado preto curto em corte irregular funcional | média atlética, base firme | quase frontal em repouso ativo, bastão médio de combate-foco apoiado com duas mãos separadas; cabeça alta e levemente voltada para a esquerda, olhar acima da linha do observador | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_luminar_cinereo_feminino.png` |
| 37 | Hemário | Sentinela | M | 33 | clara quente rubra; rosto alongado, nariz reto, olhos âmbar e têmporas discretamente vascularizadas sob esforço; auburn escuro ondulado curto | atlético tenso e médio-alto | 3/4 direito, espada de duas mãos mantida baixa em guarda de contra-impacto, sem escudo; mandíbula tensa, cabeça e olhar orientados para a direita, como esperando o golpe | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_sentinela_hemario_masculino.png` |
| 38 | Hemário | Errante | M | 41 | castanha escura de subtom cobre; rosto quadrado, nariz largo, olhos avelã e barba preta-avermelhada curta; preto cacheado curto com reflexos auburn | compacto e vigoroso | 3/4 direito com movimento interrompido por um instante; espada curta à frente e adaga para trás; cabeça desacopla do torso e gira para a frente, olhar direto e alerta | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_errante_hemario_masculino.png` |
| 39 | Hemário | Vigia | M | 28 | castanha média quente; rosto oval, nariz aquilino curto, olhos verde-castanho e lábios de cor viva; cobre escuro liso-ondulado médio preso atrás | alto e atlético, musculatura seca | frontal ligeiramente assimétrico, besta de mão baixa em uma mão e segunda besta de mão recolhida junto ao quadril; capa afastada do campo de visão; cabeça gira para a esquerda e o olhar procura um alvo lateral | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_vigia_hemario_masculino.png` |
| 40 | Hemário | Tecelão | M | 46 | negra de subtom cobre; rosto largo, nariz curto, olhos âmbar escuros e pequenas linhas de tensão na mandíbula; preto crespo muito curto com alguns fios avermelhados | médio forte, antebraços marcados | perfil direito, bastão de duas seções preso junto ao antebraço; mão oposta estendida para um ponto fora do quadro; cabeça e olhar acompanham a mão para a direita | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_tecelao_hemario_masculino.png` |
| 41 | Hemário | Oráculo | M | 35 | clara oliva quente; rosto triangular, olhos castanho profundo, nariz longo e barba auburn curta; castanho-avermelhado ondulado até a nuca | esguio, musculatura tensa | 3/4 direito, espada curta oracular com marcas discretas apoiada baixa; ombros tranquilos; cabeça quase frontal e olhar ligeiramente acima da linha do horizonte, como percebendo uma opção antes dos demais | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_oraculo_hemario_masculino.png` |
| 42 | Hemário | Luminar | M | 50 | castanha média avermelhada; rosto quadrado envelhecido, nariz largo, olhos avelã escuros e barba grisalha com cobre; preto curto com grisalho e reflexos castanhos | alto, forte e controlado | 3/4 direito, cajado curvo apoiado no chão, uma mão no foco e outra estendida baixa; pequena Luz neutra localizada perto da mão, sem halo; cabeça se volta à esquerda e o olhar acompanha a mão iluminada | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_luminar_hemario_masculino.png` |
| 43 | Hemário | Sentinela | F | 34 | castanha escura cobre; rosto oval forte, nariz largo, olhos avelã e lábios de cor viva; cacheado preto-auburn médio preso alto com volume controlado | atlética funcional, ombros firmes | passo curto de reposicionamento lateral, escudo pequeno cobrindo o centro e lança curta recolhida; cabeça inclina para baixo à direita e os olhos acompanham o ponto provável de impacto | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_sentinela_hemario_feminino.png` |
| 44 | Hemário | Errante | F | 25 | clara quente rosada; rosto em coração, nariz curto, olhos âmbar claros e sardas avermelhadas discretas; cobre escuro ondulado curto até o queixo | esguia atlética e muito rápida | perfil esquerdo em deslocamento controlado; duas lâminas próximas ao corpo; cabeça gira parcialmente para a frente e o olhar baixa ao espaço imediatamente adiante | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_errante_hemario_feminino.png` |
| 45 | Hemário | Vigia | F | 43 | negra de subtom rubro profundo; rosto longo, maçãs altas, nariz reto e olhos castanho-quentes intensos; crespo preto médio em torções presas para trás | alta e forte, postura tensa | 3/4 direito, arco longo nas costas mas inteiramente legível; uma flecha na mão sem estar encaixada; cabeça vira para a esquerda e o olhar sobe acima do horizonte | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_vigia_hemario_feminino.png` |
| 46 | Hemário | Tecelão | F | 31 | castanha média quente; rosto quadrado suave, nariz arredondado, olhos verde-castanho e cicatriz fina no lábio; auburn escuro cacheado curto e assimétrico | média atlética, mãos precisas | quase frontal, espada curta-foco compacta perto do quadril com filamento discreto saindo do guarda-mão; a outra mão gira como resolvendo relação espacial; cabeça voltada para a direita, olhos seguindo o filamento | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_tecelao_hemario_feminino.png` |
| 47 | Hemário | Oráculo | F | 47 | oliva quente avermelhada; rosto alongado, nariz aquilino, olhos âmbar escuros e linhas finas de idade; castanho-avermelhado ondulado longo preso em coque baixo | alta esguia, musculatura firme | frontal com torso já iniciando uma direção e cabeça deliberadamente voltada para a esquerda; lâmina simbólica baixa e bastão preso às costas; olhar permanece no lado oposto ao deslocamento do corpo | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_oraculo_hemario_feminino.png` |
| 48 | Hemário | Luminar | F | 37 | castanha escura cobre; rosto redondo forte, nariz largo, olhos castanho profundo e sobrancelhas marcadas; preto cacheado curto com mechas auburn discretas | robusta atlética e centrada | perfil direito, lança curta-foco luminosa mantida vertical com duas mãos espaçadas; Luz concentrada apenas na junção do foco; postura respiratória centrada; cabeça gira para a frente e o olhar é calmo e direto | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_luminar_hemario_feminino.png` |
| 49 | Alvorano | Sentinela | M | 35 | bronzeada dourada; rosto oval angular, maçãs marcadas, olhos avelã amendoados e nariz reto; preto liso médio preso em meio rabo curto | alto ágil e coordenado | quase frontal, duas espadas longas em guarda fechada e pesada, uma ligeiramente à frente da outra; corpo pronto para deslocar; cabeça voltada nitidamente para a esquerda e olhar firme no flanco | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_sentinela_alvorano_masculino.png` |
| 50 | Alvorano | Errante | M | 26 | oliva dourada média; rosto triangular, olhos âmbar, nariz curto e sobrancelhas de linha clara; castanho-escuro ondulado curto com franja afastada | médio leve, pernas rápidas | passo para trás controlado, torso ainda voltado ao adversário; facão curto baixo e adaga alta; cabeça gira para a direita enquanto o corpo recua, olhar intenso para esse lado | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_errante_alvorano_masculino.png` |
| 51 | Alvorano | Vigia | M | 44 | castanha clara quente-neutra; rosto alongado, maçãs altas, olhos verde-oliva e nariz aquilino discreto; preto liso curto penteado para trás com fios grisalhos mínimos | alto e esguio, postura alerta | quase perfil direito, besta de mão estreita apoiada sobre antebraço baixo e adaga de campo embainhada visível; cabeça gira para a frente e o olhar sobe ligeiramente acima do observador, buscando movimento distante | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_vigia_alvorano_masculino.png` |
| 52 | Alvorano | Tecelão | M | 30 | bronzeada média; rosto oval curto, olhos castanho-claro, nariz reto largo e mandíbula fina; castanho escuro ondulado médio preso atrás das orelhas | médio atlético, mãos rápidas | 3/4 esquerdo, fuso alongado erguido apenas até a altura do peito, sem gesto de mago; cabeça baixa para a esquerda e o olhar alterna entre foco e solo | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_tecelao_alvorano_masculino.png` |
| 53 | Alvorano | Oráculo | M | 39 | oliva quente; rosto retangular estreito, olhos âmbar escuros, nariz longo e sobrancelhas definidas; cobre-castanho liso médio preso em nó baixo | alto e coordenado | 3/4 esquerdo, lâmina curva simbólica horizontal baixa e mão livre comparando dois pequenos marcadores; cabeça ergue para a direita e o olhar acompanha uma possibilidade acima | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_oraculo_alvorano_masculino.png` |
| 54 | Alvorano | Luminar | M | 48 | castanha média dourada; rosto quadrado suave, olhos avelã, nariz médio e linhas de idade discretas; preto ondulado curto com mechas castanhas e grisalho leve | médio firme, postura muito centrada | 3/4 esquerdo, espada-foco luminosa cruzando diagonal baixa e mão livre projetando uma barreira translúcida mínima junto ao antebraço; cabeça gira para a frente, olhar centrado através da barreira | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_luminar_alvorano_masculino.png` |
| 55 | Alvorano | Sentinela | F | 32 | oliva dourada clara; rosto oval angular, olhos âmbar amendoados, nariz reto e maçãs marcadas; castanho-cobre ondulado curto, com uma lateral presa | média móvel e atlética | 3/4 esquerdo em repouso vigilante; espada de duas mãos apoiada diagonalmente junto ao corpo, sem escudo; cabeça levemente virada para a esquerda e olhar atento fora do quadro | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_sentinela_alvorano_feminino.png` |
| 56 | Alvorano | Errante | F | 23 | bronzeada clara; rosto em coração, olhos verde-oliva, nariz curto e sobrancelhas retas; preto liso longo preso em rabo alto segmentado | esguia e muito ágil | 3/4 esquerdo com joelhos flexíveis e peso na ponta do pé dianteiro; duas adagas desenhando diagonais opostas; cabeça gira para a direita e o olhar mede uma rota de saída | Estrada de cinzas | `errante_das_cinzas/errante_das_cinzas_errante_alvorano_feminino.png` |
| 57 | Alvorano | Vigia | F | 40 | castanha média quente-neutra; rosto alongado, olhos avelã claros, nariz aquilino suave e maçãs altas; castanho-escuro ondulado médio preso em trança única curta | alta e coordenada, braços longos | 3/4 esquerdo com duas bestas de mão, uma baixa e outra próxima ao torso; arnês de virotes lateral; cabeça gira para a frente e o olhar sobe ligeiramente, procurando um alvo distante | Charneca de fuligem | `errante_das_cinzas/errante_das_cinzas_vigia_alvorano_feminino.png` |
| 58 | Alvorano | Tecelão | F | 28 | oliva média dourada; rosto triangular suave, olhos âmbar, nariz médio e cicatriz fina na sobrancelha; cobre escuro curto e ondulado, penteado para trás | média atlética, gestual preciso | frontal com leve rotação do torso, lâmina-foco ornamentada cruzando diagonal baixa com um fio de Trama e pequena reação ígnea localizada; mão livre fechando gesto técnico; cabeça baixa para a esquerda e olhos acompanham o fio de Trama | Borda do bosque calcinado | `errante_das_cinzas/errante_das_cinzas_tecelao_alvorano_feminino.png` |
| 59 | Alvorano | Oráculo | F | 46 | bronzeada dourada; rosto oval largo, olhos castanho-claro, nariz reto e linhas de idade ao redor dos olhos; castanho dourado escuro ondulado até os ombros, metade preso | alta, magra e muito estável | perfil parcial direito, bastão oracular apoiado e lâmina curta simbólica embainhada visível; cabeça acompanha o perfil e o olhar se projeta para a direita, como aguardando uma confirmação fora do quadro | Passagem das ruínas | `errante_das_cinzas/errante_das_cinzas_oraculo_alvorano_feminino.png` |
| 60 | Alvorano | Luminar | F | 36 | castanha clara quente; rosto quadrado leve, olhos verde-oliva, nariz curto largo e sobrancelhas marcadas; preto liso curto com franja lateral curta | média forte e centrada | frontal assimétrico, bastão curto de combate-foco baixo em uma mão, outra próxima ao centro do peito com pequena Luz concentrada; cabeça alinhada para a frente e olhar direto, estável e acolhedor | Caminho quebrado | `errante_das_cinzas/errante_das_cinzas_luminar_alvorano_feminino.png` |

## 12. QA de aprovação

Reprovar a imagem se qualquer item abaixo falhar:

1. Raça reconhecível pelo fenótipo, sem depender de texto.
2. Classe reconhecível por silhueta, traje, arma/foco e gestual.
3. Tema `Errante das Cinzas` reconhecível por materiais/desgaste, sem magia de cinza.
4. Indivíduo claramente diferente dos demais: rosto, cabelo, pose e direção do olhar não parecem clonados.
5. Fundo pertence à família Terras do Ocaso, mas não é cenário monumental nem cópia exata de outro asset.
6. Arma/foco integral, legível e fisicamente coerente; quando a Classe usar uma exceção de armamento desta v1.2, a silhueta/postura ainda precisa comunicar a Classe sem depender do nome.
7. Anatomia íntegra, sem membros extras, dedos fundidos ou objetos atravessando o corpo.
8. Pixel art verdadeira, sem acabamento liso de pintura digital com filtro.
9. Nenhum spoiler ou símbolo que invente Lore.
10. Em miniatura, personagem continua legível antes do fundo.
11. Sentinelas sem escudo não parecem Errantes/berserkers; Vigias com duas bestas não parecem usuários de armas de fogo; focos mágicos de Tecelão, Oráculo e Luminar permanecem formalmente distintos.
12. A direção dominante do olhar respeita a matriz, não repete o asset imediatamente anterior e não recai automaticamente para o lado direito.

## 13. Frase-guia

> **A cinza marca o caminho; não apaga quem o percorre.**

---

# DOCUMENTO INCORPORADO 6/9
## Arquivo original: `ASTERION_APARENCIA_SOBREVIVENTE_DOS_VALES_FONTE_VISUAL_v1.1.md`
# ASTERION — APARÊNCIA SOBREVIVENTE DOS VALES · FONTE VISUAL ESPECIALIZADA v1.1

**Data de consolidação:** 2026-10-12  
**Escopo:** produção das 60 imagens da Aparência cosmética regional `Sobrevivente dos Vales` — 5 Raças × 6 Classes × 2 apresentações  
**Estado:** fonte visual especializada aprovada para produção; subordinada às autoridades canônicas vigentes  

> Esta Fonte existe para que a Aparência `Sobrevivente dos Vales` siga o mesmo grau de padronização, clareza e controle de lote já aplicado em `Errante das Cinzas`, mas adaptado integralmente à identidade regional de **Vales dos Enforcados**.

> Esta Fonte não cria regra mecânica de equipamento, Classe, Raça, bônus, dano, Inventário, progressão ou Cosmético. Ela define somente a identidade visual e o método de produção da Aparência `Sobrevivente dos Vales`.

> **Revisão anatômica 2026-10-12:** esta Aparência adota integralmente a anatomia racial v2.0. Tema regional, desgaste, roupa e armamento nunca removem ou remodelam os marcadores anatômicos obrigatórios da Raça. Elmos/capuzes devem acomodá-los fisicamente.

---

## 0. Motivo desta Fonte

A produção anterior dos prompts dos Vales apresentou um problema recorrente: vários fundos passaram a parecer **hub/assentamento**, como se os personagens estivessem em uma base segura, e não atravessando os ambientes da segunda Região.

Esta Fonte corrige isso de forma estrutural:

- o **padrão-base** será o mesmo rigor de `Errante das Cinzas`;
- os **fundos passam a ser explicitamente regionais** e não-hub;
- a coleção deve percorrer **subambientes dos Vales** sem perder unidade temática;
- a identidade da skin deve ser lida de imediato como **“Sobrevivente dos Vales”**;
- nenhuma imagem deve parecer apenas “personagem no assentamento”.

---

## 1. Autoridades preservadas

- `ASTERION_CONTEUDO_VALES_DOS_ENFORCADOS_v1.0.3_FINAL.md` — define a Aparência `Sobrevivente dos Vales` como recompensa do Feito oculto **Entre Galhos e Presas**.
- `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md` — define fenótipos raciais, silhuetas, assinaturas de Classe e NPCs canônicos.
- `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` — define formato, pixel art, anatomia, área segura, armas/focos e QA.
- `ASTERION_AMBIENTES_LOCAIS_E_MASMORRAS_v1.0.md` — define a identidade ambiental e os subambientes de Vales dos Enforcados.
- `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md` — permanece válida no que não for explicitamente substituído por esta Fonte especializada.
- `ASTERION_PADRAO_GLOBAL_SKINS_TEMATICAS_v1.1.md` — define o padrão global consolidado das coleções futuras.
- `SOURCE_AUTHORITY.md` — mantém a hierarquia documental global.

---

## 2. Decisão operacional — independência das 60 identidades

Para `Sobrevivente dos Vales`, as 60 imagens devem ser produzidas como **60 indivíduos novos e autônomos**, e não como reaproveitamento direto da Aparência padrão, nem como cópia de rosto/cabelo/pose de outras skins.

Consequências obrigatórias:

- não usar a Aparência padrão como molde de rosto/cabelo;
- não copiar pose, direção de olhar ou estrutura facial entre assets consecutivos;
- cada combinação Raça × Classe × apresentação representa **uma pessoa diferente**;
- identidade racial vem do **fenótipo**;
- identidade de Classe vem de **silhueta + vestuário + arma/foco + gestual**;
- identidade temática vem de **umidade, raízes, lama, cordas, desgaste úmido e fundo regional**, nunca de “mutação vegetal”.

---

## 3. Núcleo temático — Sobrevivente dos Vales

Leitura desejada: **alguém que atravessou por muito tempo os Vales dos Enforcados, aprendeu a se mover em desfiladeiros úmidos, passagens suspensas, ruínas enraizadas e baixios escuros, e adaptou vestes e equipamento a esse ambiente sem se transformar em criatura vegetal.**

A imagem precisa transmitir:

- sobrevivência em ambiente úmido e opressivo;
- uso constante de trilhas estreitas, cordas, passarelas e ruínas presas por raízes;
- roupa e equipamento mantidos com competência, mas marcados pela umidade e pelo atrito do terreno;
- familiaridade com lama, musgo, madeira encharcada, pedra molhada e raízes grossas;
- personagem que **pertence visualmente à segunda Região**.

A skin não deve transmitir:

- assentamento tranquilo;
- fantasia feérica de floresta encantada;
- culto druidesco;
- “pessoa possuída por raízes”; 
- selva tropical genérica;
- “explorador neutro” sem assinatura regional.

### 3.1 Materiais obrigatórios

- tecido pesado ou médio com sinais de umidade e uso contínuo;
- barras, bainhas e botas com marcas de lama, turfa ou água escura;
- couro encerado, tratado ou remendado para resistir à umidade;
- cordas, tiras, nós, ganchos e amarrações funcionais;
- metal fosco, úmido, oxidado ou manchado;
- madeira de equipamento escurecida por uso e clima;
- musgo, sujeira e desgaste localizados — nunca excesso decorativo;
- manutenção visível: costuras, reforços, rebites, presilhas, remendos e encaixes.

### 3.2 Proibições temáticas

- nenhum crescimento de raízes saindo do corpo;
- nenhuma “armadura viva” vegetal espontânea;
- nenhum brilho feérico verde por toda a imagem;
- nenhum cogumelo neon;
- nenhuma floresta mágica luminosa;
- nenhum fundo de praça, mercado, alojamento ou pátio seguro como padrão da coleção;
- nenhuma silhueta de aldeia/hub como pano de fundo principal;
- nenhum uso de `Vigília do Vale` como fundo-base desta coleção;
- nenhum céu aberto ensolarado que negue a sensação de vale profundo e úmido.

---

## 4. Paleta e linguagem material

Dominantes:

- verde escuro úmido;
- marrom molhado;
- cinza úmido;
- preto de turfa;
- azul-cinza de névoa;
- pedra fria;
- madeira escurecida;
- couro encharcado ou encerado.

Acentos pequenos permitidos:

- âmbar de resina discreta;
- ferrugem escura;
- bronze envelhecido;
- vermelho apagado em tecido utilitário;
- luz localizada de Classe quando canonicamente pertinente.

A Região deve parecer **úmida, funda, estreita e enredada**, nunca ensolarada, aberta ou heroicamente limpa.

---

## 5. Fundo temático compartilhado — padronização sem repetição

Todas as 60 imagens usam a mesma **família ambiental** de Vales dos Enforcados. O fundo não é idêntico; ele circula entre cinco vinhetas oficiais, sempre rasas, discretas e subordinadas ao personagem.

### 5.1 Vinhetas oficiais de fundo

1. **Garganta dos Laços**  
   Entrada entre paredões altos, raízes descendo pelas paredes, restos de estrada antiga, pouca abertura para o céu, umidade visível e profundidade comprimida.

2. **Mata Suspensa**  
   Troncos inclinados, raízes formando passagens, ruínas antigas visíveis entre níveis diferentes, sensação de verticalidade e travessia.

3. **Baixios Enredados**  
   Água escura, turfa, juncos, raízes submersas, neblina rente ao chão e trilha estreita insegura.

4. **Claustro Externo Enraizado**  
   Pedra asteriana reconhecível, arcos/corredores/apoios ainda discerníveis, atravessados por raízes e umidade. Não revelar câmaras internas, mecanismos-chave ou spoilers da estrutura.

5. **Travessia Suspensa dos Vales**  
   Pequena plataforma, passarela, borda de escarpa ou trecho de ponte/tronco/ruína pendida sobre desnível, com cordas, tábuas ou pedras úmidas e raízes pendentes.

### 5.2 Regras obrigatórias do fundo

- o fundo deve parecer **mapa/região**, não hub;
- o personagem continua sendo o sujeito principal;
- o fundo precisa ser legível mesmo em leitura pequena, mas com menos contraste local que o personagem;
- deve existir sensação de profundidade, umidade e confinamento;
- o céu, quando aparecer, deve ser parcial, estreito e frio;
- **não usar Vigília do Vale** como fundo desta coleção;
- não usar interior de abrigo, barraca, comércio, dormitório, oficina ou pátio seguro;
- nenhum skyline monumental genérico.

### 5.3 Distribuição mínima de fundo no lote

Em cada bloco de 10 assets, usar pelo menos **4 das 5 vinhetas** oficiais.  
No conjunto completo de 60 assets:

- Garganta dos Laços: mínimo 10 usos;
- Mata Suspensa: mínimo 10 usos;
- Baixios Enredados: mínimo 10 usos;
- Claustro Externo Enraizado: mínimo 10 usos;
- Travessia Suspensa dos Vales: mínimo 10 usos.

Os 10 usos restantes podem reforçar qualquer uma das cinco vinhetas, desde que o lote não pareça repetitivo.

---

## 6. Diversidade individual obrigatória

O lote deve evitar repetição de rosto, silhueta, pose, vetor de cabeça e arranjo de armamento.

Distribuir conscientemente:

- frontal, 3/4 esquerdo, 3/4 direito e perfis parciais;
- cabeça olhando esquerda, direita, frente, alto, baixo e sobre o ombro;
- peso corporal na perna dianteira, traseira, lateral ou central;
- Repouso, Contemplação, Vigilância, Deslocamento, Preparação e Ação controlada;
- cabelos curtos, médios, longos, presos, parcialmente presos, trançados, locs, cachos, grisalhos e assimétricos quando racialmente coerentes;
- idades adultas variadas;
- corpos esguios, médios, altos, compactos, densos ou robustos, dentro das tendências raciais;
- cicatrizes e sinais individuais apenas quando discretos e plausíveis.

### 6.1 Distribuição obrigatória de cabeça e olhar

- a direção dominante do olhar não pode se repetir em dois assets consecutivos;
- em qualquer bloco de 6 assets consecutivos, usar pelo menos quatro vetores claramente diferentes entre esquerda, direita, frente, acima, abaixo e sobre o ombro;
- evitar que três personagens próximos pareçam olhar para o mesmo lado;
- a direção de cabeça/olhar escrita na matriz desta Fonte é obrigatória.

---

## 7. Regras raciais

A anatomia racial v2.0 é obrigatória em todas as 60 imagens. O tema Sobrevivente dos Vales altera materiais, desgaste e adaptação regional, mas não neutraliza a fisiologia da Raça.

### Remanescente
Anatomia humana normal, maior diversidade interna e nenhum apêndice racial obrigatório. A leitura não pode depender de “humano genérico”; rosto, cabelo, pele, constituição e história material precisam individualizar a pessoa.

### Velado
Porte menor/esguio; orelhas largas orientadas lateralmente para trás; olhos proporcionalmente maiores; dedos longos e rosto estreito. Capuzes e proteções devem acomodar essa anatomia. Nunca parecer elfo alto, goblin verde, gnomo caricatural, vampiro ou cadáver.

### Cinéreo
Corpo compacto/denso; mãos grandes; ossatura facial e mandíbula fortes; caninos inferiores curtos discretamente aumentados. A pele permanece orgânica e pode variar amplamente. Nunca parecer pessoa de pedra, golem, anão ou orc copiado.

### Hemário
Exatamente um par de chifres de queratina integrado ao crânio, combinado à assinatura vascular quente. Equipamento de cabeça deve ser construído ao redor dos chifres. Nunca representar como vampiro/demônio, nem adicionar asas, cascos, cauda obrigatória ou presas vampíricas.

### Alvorano
Porte mais alto/alongado; orelhas longas pontiagudas orientadas para cima e para trás; coordenação corporal evidente e membros discretamente alongados. Nunca representar como ser sagrado, anjo ou elfo copiado.

## 8. Regras de Classe e armamento

`Sobrevivente dos Vales` segue as **assinaturas globais de Classe**. As exceções cosméticas de armamento documentadas para `Errante das Cinzas` são exclusivas daquela Aparência e não são herdadas por esta coleção. A variação abaixo é visual e permanece dentro da família autorizada de cada Classe.

### Sentinela
- arma de uma mão + **escudo visível** em todas as imagens;
- pode variar entre espada, maça, machado de uma mão ou lança curta funcional, sempre acompanhada de escudo;
- postura de guarda, sustentação ou Retaliação legível.

### Errante
- duas armas curtas e rápidas visíveis;
- exemplos: duas adagas, espada curta + adaga, duas lâminas curtas, sabre curto + faca;
- não usar armas longas/pesadas como assinatura.

### Vigia
- **arco ou besta** como arma-assinatura;
- uma única arma de disparo principal claramente legível;
- não usar duas bestas de mão como padrão desta Aparência.

### Tecelão
- arma-foco de Trama claramente técnica;
- haste, bastão-foco, lâmina-foco, agulha/fuso ou cetro técnico são aceitáveis quando a função de Trama permanecer inequívoca.

### Oráculo
- arma-foco oracular/simbólica;
- bastão, cetro, lâmina-foco ou combinação compacta somente quando a leitura principal continuar sendo possibilidade/presságio, não dual wield marcial.

### Luminar
- cajado ou bastão de combate-foco como assinatura;
- Luz localizada e controlada quando a pose pedir;
- não substituir a assinatura por espada ou maça comum.

## 9. Escala, enquadramento e padrão técnico obrigatório

- categoria: personagem jogável;
- proporção: **1:1**;
- master de produção: **1024×1024**;
- personagem de corpo inteiro, sem corte;
- figura ocupando preferencialmente **76–80% da altura útil**;
- tolerância operacional máxima: **72–82%**;
- cabeça e pés totalmente visíveis;
- margem segura real em todos os lados;
- câmera média consistente, sem grande-angular ou exagero de perspectiva;
- pixel art concebida como pixel art, com pixels visíveis;
- sem acabamento liso de pintura digital moderna;
- fundo subordinado ao personagem;
- silhueta legível em leitura pequena.

### 9.1 QA técnico obrigatório

Reprovar:

- personagem pequeno demais ou grande demais em comparação ao catálogo;
- fundo competindo com o sujeito principal;
- anatomia quebrada;
- mãos, braços, joelhos ou pés incoerentes;
- corda de arco ou mecanismo de besta bugados;
- arma/foco sem leitura material convincente;
- pose colapsada;
- fundo parecendo assentamento/hub;
- imagem “limpa demais”, “pintada demais” ou distante do pixel art-base da série.

---

## 10. Matriz oficial dos 60 assets

**Ordem oficial do lote:** Remanescente, Velado, Cinéreo, Hemário, Alvorano; dentro de cada Raça: Sentinela, Errante, Vigia, Tecelão, Oráculo, Luminar; masculino depois feminino.

### 10.1 Remanescente

| Nº | ID | Classe | Apres. | Fenótipo & cabelo | Pose / armamento / olhar | Fundo | Arquivo |
|---:|---|---|---|---|---|---|---|
| 01 | SV-REM-SEN-M | Sentinela | M | castanho-escuro; crespo curto | Vigilância; espada de uma mão + escudo; torso 3/4 esquerdo, olhar à direita | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_remanescente_masculino.png` |
| 02 | SV-REM-SEN-F | Sentinela | F | negra retinta; tranças presas | Preparação; maça de uma mão + escudo; perfil parcial direito, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_remanescente_feminino.png` |
| 03 | SV-REM-ERR-M | Errante | M | bronzeado médio; ondulado curto | Deslocamento; duas adagas; passo lateral, olhar baixo à frente | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_remanescente_masculino.png` |
| 04 | SV-REM-ERR-F | Errante | F | castanha clara; cachos curtos | Vigilância; espada curta + adaga; 3/4 direito, olhar sobre o ombro esquerdo | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_remanescente_feminino.png` |
| 05 | SV-REM-VIG-M | Vigia | M | castanha escura; locs curtos presos | Contemplação; arco; frontal, olhar para cima à esquerda | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_remanescente_masculino.png` |
| 06 | SV-REM-VIG-F | Vigia | F | oliva quente; ondulado médio preso | Vigilância; besta; perfil esquerdo, olhar à frente | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_remanescente_feminino.png` |
| 07 | SV-REM-TEC-M | Tecelão | M | negra; crespo médio | Preparação; bastão-foco técnico de Trama; frontal assimétrico, olhar para baixo | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_remanescente_masculino.png` |
| 08 | SV-REM-TEC-F | Tecelão | F | castanha média; microtranças | Ação controlada; lâmina-foco técnica de Trama; 3/4 esquerdo, olhar à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_remanescente_feminino.png` |
| 09 | SV-REM-ORA-M | Oráculo | M | bronzeado escuro; barba curta e cabelo ondulado | Contemplação; bastão-foco oracular; perfil direito, olhar para a frente | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_remanescente_masculino.png` |
| 10 | SV-REM-ORA-F | Oráculo | F | castanha quente; cabelo cacheado preso baixo | Vigilância; cetro-foco oracular; 3/4 frontal, olhar acima à direita | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_remanescente_feminino.png` |
| 11 | SV-REM-LUM-M | Luminar | M | negra de subtom quente; crespo curto | Repouso firme; cajado de combate-foco; torso frontal, olhar à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_remanescente_masculino.png` |
| 12 | SV-REM-LUM-F | Luminar | F | castanha escura; cachos médios presos | Preparação; bastão de combate-foco; 3/4 direito, olhar baixo à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_remanescente_feminino.png` |

### 10.2 Velado

| Nº | ID | Classe | Apres. | Fenótipo & cabelo | Pose / armamento / olhar | Fundo | Arquivo |
|---:|---|---|---|---|---|---|---|
| 13 | SV-VEL-SEN-M | Sentinela | M | pálido frio; preto liso médio | Vigilância; machado de uma mão + escudo; 3/4 esquerdo, olhar para baixo à direita | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_velado_masculino.png` |
| 14 | SV-VEL-SEN-F | Sentinela | F | oliva fria clara; trança prateada baixa | Repouso atento; lança curta + escudo; perfil parcial direito, olhar à direita | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_velado_feminino.png` |
| 15 | SV-VEL-ERR-M | Errante | M | clara fria; castanho-acinzentado preso | Deslocamento; duas lâminas curtas; passo estreito, olhar à esquerda | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_velado_masculino.png` |
| 16 | SV-VEL-ERR-F | Errante | F | pálida; branco-prateado reto | Vigilância; sabre curto + faca; 3/4 direito, olhar sobre o ombro direito | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_velado_feminino.png` |
| 17 | SV-VEL-VIG-M | Vigia | M | clara fria; cabelo liso curto para trás | Contemplação; arco recurvo; frontal, olhar acima à frente | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_velado_masculino.png` |
| 18 | SV-VEL-VIG-F | Vigia | F | oliva pálida; preto liso preso | Vigilância; besta leve; perfil esquerdo, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_velado_feminino.png` |
| 19 | SV-VEL-TEC-M | Tecelão | M | clara neutra; preto liso com mecha longa | Preparação; agulha/fuso de Trama; 3/4 frontal, olhar para baixo à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_velado_masculino.png` |
| 20 | SV-VEL-TEC-F | Tecelão | F | pálida fria; prateado curto lateral | Ação controlada; cetro técnico de Trama; 3/4 esquerdo, olhar à direita alta | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_velado_feminino.png` |
| 21 | SV-VEL-ORA-M | Oráculo | M | oliva fria clara; cinza-prata preso baixo | Contemplação; lâmina-foco simbólica; perfil direito, olhar para baixo à frente | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_velado_masculino.png` |
| 22 | SV-VEL-ORA-F | Oráculo | F | clara fria; branco-prateado ondulado | Vigilância; bastão curto de presságio; frontal assimétrico, olhar direto à frente | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_velado_feminino.png` |
| 23 | SV-VEL-LUM-M | Luminar | M | pálido; branco curto penteado | Repouso; cajado curto de combate-foco; 3/4 direito, olhar à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_velado_masculino.png` |
| 24 | SV-VEL-LUM-F | Luminar | F | oliva fria; preto liso em coque baixo | Preparação; bastão longo de combate-foco; frontal, olhar baixo à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_velado_feminino.png` |

### 10.3 Cinéreo

| Nº | ID | Classe | Apres. | Fenótipo & cabelo | Pose / armamento / olhar | Fundo | Arquivo |
|---:|---|---|---|---|---|---|---|
| 25 | SV-CIN-SEN-M | Sentinela | M | castanha terrosa; ondulado denso curto | Base firme; espada de uma mão + escudo; 3/4 esquerdo, olhar acima à direita | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_cinereo_masculino.png` |
| 26 | SV-CIN-SEN-F | Sentinela | F | negra retinta; crespo preso alto | Preparação; maça de uma mão + escudo; perfil parcial direito, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_cinereo_feminino.png` |
| 27 | SV-CIN-ERR-M | Errante | M | bronze escuro; crespo baixo denso | Deslocamento; duas adagas; torso frontal, olhar baixo à frente | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_cinereo_masculino.png` |
| 28 | SV-CIN-ERR-F | Errante | F | castanha média; cacheado curto | Vigilância; espada curta + adaga; 3/4 direito, olhar sobre o ombro esquerdo | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_cinereo_feminino.png` |
| 29 | SV-CIN-VIG-M | Vigia | M | castanho-escuro; cacheado médio preso | Contemplação; arco; perfil esquerdo, olhar à esquerda | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_cinereo_masculino.png` |
| 30 | SV-CIN-VIG-F | Vigia | F | negra; tranças grossas curtas | Vigilância; besta; frontal, olhar à frente alta | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_cinereo_feminino.png` |
| 31 | SV-CIN-TEC-M | Tecelão | M | terroso médio; ondulado espesso | Preparação; bastão-foco técnico de Trama; 3/4 frontal, olhar para baixo à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_cinereo_masculino.png` |
| 32 | SV-CIN-TEC-F | Tecelão | F | negra quente; crespo curto arredondado | Ação controlada; lâmina-foco técnica de Trama; 3/4 esquerdo, olhar à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_cinereo_feminino.png` |
| 33 | SV-CIN-ORA-M | Oráculo | M | castanho terroso; barba curta e cabelo espesso | Contemplação; bastão-foco oracular; perfil direito, olhar abaixo à frente | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_cinereo_masculino.png` |
| 34 | SV-CIN-ORA-F | Oráculo | F | bronze escura; cachos presos baixos | Vigilância; cetro-foco oracular; frontal assimétrico, olhar direto à frente | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_cinereo_feminino.png` |
| 35 | SV-CIN-LUM-M | Luminar | M | castanha média; ondulado curto grisalho nas têmporas | Repouso centrado; cajado de combate-foco; 3/4 direito, olhar à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_cinereo_masculino.png` |
| 36 | SV-CIN-LUM-F | Luminar | F | negra; tranças grossas presas | Preparação; bastão de combate-foco; frontal, olhar baixo à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_cinereo_feminino.png` |

### 10.4 Hemário

| Nº | ID | Classe | Apres. | Fenótipo & cabelo | Pose / armamento / olhar | Fundo | Arquivo |
|---:|---|---|---|---|---|---|---|
| 37 | SV-HEM-SEN-M | Sentinela | M | clara quente/rubra; auburn curto | Vigilância; machado de uma mão + escudo; 3/4 esquerdo, olhar à direita | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_hemario_masculino.png` |
| 38 | SV-HEM-SEN-F | Sentinela | F | castanha cobre; preto-auburn preso | Preparação; lança curta + escudo; perfil parcial direito, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_hemario_feminino.png` |
| 39 | SV-HEM-ERR-M | Errante | M | rubra clara; castanho profundo ondulado | Deslocamento; duas lâminas curtas; passo diagonal, olhar baixo à frente | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_hemario_masculino.png` |
| 40 | SV-HEM-ERR-F | Errante | F | castanha quente; cacheado cobre escuro | Vigilância; sabre curto + faca; 3/4 direito, olhar sobre o ombro esquerdo | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_hemario_feminino.png` |
| 41 | SV-HEM-VIG-M | Vigia | M | clara rubra; auburn curto | Contemplação; arco recurvo; frontal, olhar acima à esquerda | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_hemario_masculino.png` |
| 42 | SV-HEM-VIG-F | Vigia | F | castanha cobre; preto ondulado preso | Vigilância; besta leve; perfil esquerdo, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_hemario_feminino.png` |
| 43 | SV-HEM-TEC-M | Tecelão | M | clara quente; auburn escuro médio | Preparação; agulha/fuso de Trama; 3/4 frontal, olhar para baixo | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_hemario_masculino.png` |
| 44 | SV-HEM-TEC-F | Tecelão | F | castanha quente; cobre escuro preso | Ação controlada; cetro técnico de Trama; 3/4 esquerdo, olhar à direita alta | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_hemario_feminino.png` |
| 45 | SV-HEM-ORA-M | Oráculo | M | rubro claro; barba curta e cabelo ondulado | Contemplação; lâmina-foco simbólica; perfil direito, olhar abaixo à frente | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_hemario_masculino.png` |
| 46 | SV-HEM-ORA-F | Oráculo | F | castanha cobre; cacheado baixo | Vigilância; bastão curto de presságio; frontal assimétrico, olhar direto à frente | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_hemario_feminino.png` |
| 47 | SV-HEM-LUM-M | Luminar | M | quente clara; castanho profundo curto | Repouso firme; cajado curto de combate-foco; 3/4 direito, olhar à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_hemario_masculino.png` |
| 48 | SV-HEM-LUM-F | Luminar | F | castanha rubra; auburn escuro preso baixo | Preparação; bastão longo de combate-foco; frontal, olhar baixo à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_hemario_feminino.png` |

### 10.5 Alvorano

| Nº | ID | Classe | Apres. | Fenótipo & cabelo | Pose / armamento / olhar | Fundo | Arquivo |
|---:|---|---|---|---|---|---|---|
| 49 | SV-ALV-SEN-M | Sentinela | M | bronze dourado; preto liso preso | Vigilância; espada de uma mão + escudo; 3/4 esquerdo, olhar à direita | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_alvorano_masculino.png` |
| 50 | SV-ALV-SEN-F | Sentinela | F | oliva dourada clara; castanho-cobre trançado | Preparação; maça de uma mão + escudo; perfil parcial direito, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_sentinela_alvorano_feminino.png` |
| 51 | SV-ALV-ERR-M | Errante | M | oliva média; cabelo preto ondulado curto | Deslocamento; duas adagas; passo diagonal, olhar baixo à frente | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_alvorano_masculino.png` |
| 52 | SV-ALV-ERR-F | Errante | F | dourada clara; castanho-cobre médio preso | Vigilância; espada curta + adaga; 3/4 direito, olhar sobre o ombro esquerdo | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_errante_alvorano_feminino.png` |
| 53 | SV-ALV-VIG-M | Vigia | M | bronzeado dourado; preto preso baixo | Contemplação; arco; frontal, olhar acima à esquerda | Garganta dos Laços | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_alvorano_masculino.png` |
| 54 | SV-ALV-VIG-F | Vigia | F | oliva dourada; cobre escuro preso | Vigilância; besta; perfil esquerdo, olhar à esquerda | Travessia Suspensa dos Vales | `sobrevivente_dos_vales/sobrevivente_dos_vales_vigia_alvorano_feminino.png` |
| 55 | SV-ALV-TEC-M | Tecelão | M | oliva quente; castanho escuro curto | Preparação; bastão-foco técnico de Trama; 3/4 frontal, olhar para baixo | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_alvorano_masculino.png` |
| 56 | SV-ALV-TEC-F | Tecelão | F | dourada clara; cabelo ondulado cobre preso | Ação controlada; lâmina-foco técnica de Trama; 3/4 esquerdo, olhar à direita alta | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_tecelao_alvorano_feminino.png` |
| 57 | SV-ALV-ORA-M | Oráculo | M | bronze dourado; preto liso médio | Contemplação; bastão-foco oracular; perfil direito, olhar abaixo à frente | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_alvorano_masculino.png` |
| 58 | SV-ALV-ORA-F | Oráculo | F | oliva dourada; castanho-cobre curto | Vigilância; cetro-foco oracular; frontal assimétrico, olhar direto à frente | Baixios Enredados | `sobrevivente_dos_vales/sobrevivente_dos_vales_oraculo_alvorano_feminino.png` |
| 59 | SV-ALV-LUM-M | Luminar | M | bronzeado dourado; cabelo preto preso | Repouso centrado; cajado de combate-foco; 3/4 direito, olhar à esquerda | Claustro Externo Enraizado | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_alvorano_masculino.png` |
| 60 | SV-ALV-LUM-F | Luminar | F | oliva dourada clara; cobre escuro preso em coque baixo | Preparação; bastão de combate-foco; frontal, olhar baixo à direita | Mata Suspensa | `sobrevivente_dos_vales/sobrevivente_dos_vales_luminar_alvorano_feminino.png` |

---

## 11. Regra de aprovação do lote

Uma imagem só é aprovada se atender simultaneamente aos pontos abaixo:

1. o personagem é imediatamente legível como membro de sua Raça;
2. a Classe é legível pela silhueta, armamento/foco e postura;
3. a skin parece claramente `Sobrevivente dos Vales`;
4. o fundo parece **Vales dos Enforcados**, e não assentamento/hub;
5. o fundo é regional, mas subordinado ao personagem;
6. a escala do corpo está dentro do padrão do catálogo;
7. a pixel art parece da mesma família visual já aprovada nas melhores artes anteriores;
8. não há anatomia quebrada, arma impossível, corda bugada, mãos deformadas ou limpeza excessiva;
9. o asset funciona em leitura pequena;
10. a imagem pode ser colocada ao lado de outras do lote sem parecer pertencer a outro jogo.

---

## 12. Prompt-mestre de uso operacional

Quando esta Fonte for usada para gerar um asset individual da coleção, o prompt operacional deve sempre mencionar explicitamente:

- que o asset segue `ASTERION — APARÊNCIA SOBREVIVENTE DOS VALES · FONTE VISUAL ESPECIALIZADA v1.0`;
- que a coleção usa o mesmo rigor formal de `Errante das Cinzas`, mas com identidade regional dos Vales;
- que o fundo deve ser escolhido entre as **cinco vinhetas oficiais** desta Fonte;
- que o fundo **não pode parecer assentamento/hub**;
- que a identidade racial deve seguir a Bíblia Visual v1.5;
- que a Classe deve seguir a assinatura obrigatória de armamento/foco;
- que a figura deve ser de **corpo inteiro em 1:1**, com escala padronizada do catálogo;
- que a pose/olhar/armamento/fundo específicos devem seguir a matriz da linha correspondente.

---

## 13. Resultado esperado

Ao bater o olho em qualquer imagem do lote, a leitura desejada é:

**“Essa é claramente uma skin temática dos Vales dos Enforcados.”**

E não:

- “personagem em um assentamento”; 
- “personagem genérico de floresta”; 
- “personagem neutro com roupa úmida”; 
- “arte bonita, mas de outra linha visual”.

---

# DOCUMENTO INCORPORADO 7/9
## Arquivo original: `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md`
# ASTERION — BÍBLIA TÉCNICA DE GERAÇÃO DE IMAGENS v1.1

**Data de consolidação:** 2026-10-05  
**Escopo:** especificação técnica de produção, geração, revisão, pós-processamento e exportação dos assets visuais de Asterion  
**Uso principal:** transformar as Bíblias de Lore e Direção Visual em imagens coerentes entre si, reduzindo deriva estilística, erros anatômicos, artefatos de IA e inconsistência de pixel art

> Esta Fonte não cria Lore, mecânica, conteúdo regional, Raça, Classe, Caminho, criatura, Local ou cosmético. Ela define **como renderizar** aquilo que as Fontes autoritativas já definem. Em conflito de conteúdo, prevalecem `SOURCE_AUTHORITY.md`, Fonte Mestra, Fonte Regional, Fonte Visual/UI e a Bíblia visual especializada do assunto.

---

# 1. OBJETIVO

Asterion precisa parecer um único jogo mesmo quando seus assets forem produzidos em momentos diferentes, por prompts diferentes ou por ferramentas diferentes.

Esta Bíblia fecha:

- proporção e canvas de produção;
- linguagem técnica de pixel art;
- agrupamento de pixels e controle de borda;
- sombreamento, dithering, contraste e saturação;
- renderização de materiais;
- anatomia e integridade de mãos, membros e rostos;
- coerência de armas, focos e equipamentos;
- estados de pose;
- regras específicas de arco/besta;
- composição de personagens, criaturas e cenários;
- transparência e overlays;
- pós-processamento;
- nomeação de arquivos;
- QA visual antes de aprovação.

Não fecha:

- identidade visual de Raça/Classe/Caminho, que pertence à Bíblia Visual de Personagens;
- anatomia/ecologia de criaturas, que pertence à Bíblia de Bestiário Visual;
- arquitetura/bioma de cenários, que pertence à Bíblia de Ambientes;
- composição de tela do Bot, que pertence à Fonte Visual/UI.

---

# 2. ORDEM DE USO PARA PRODUÇÃO

Para qualquer asset, aplicar na seguinte ordem:

1. identificar o conteúdo canônico na Fonte Mestra/Regional;
2. consultar a Bíblia de Lore quando houver origem, cosmologia ou spoiler envolvidos;
3. consultar a Bíblia visual especializada:
   - humanoide → Personagens/Raças/Classes/NPCs;
   - criatura → Bestiário Visual e Biomas;
   - ambiente → Ambientes, Locais e Masmorras;
4. consultar a Fonte Visual/UI quando a imagem pertencer a uma tela específica;
5. aplicar esta Bíblia Técnica para renderização, composição e QA;
6. aplicar a Matriz de Produção Visual quando existir uma atribuição concreta para aquele asset.

A Matriz de Produção Visual não pode contradizer nenhuma Fonte acima.

---

# 3. IDENTIDADE TÉCNICA GLOBAL

Toda imagem de Asterion deve perseguir simultaneamente:

- dark fantasy medieval;
- decadência e materialidade;
- estética de fim da era 16-bit / início da era 32-bit;
- pixels deliberadamente visíveis;
- silhueta legível em tela pequena;
- formas reconhecíveis antes de microdetalhe;
- materiais físicos antes de efeitos;
- fantasia contida;
- iluminação funcional;
- ausência de acabamento liso de pintura digital moderna.

Asterion **não usa pixelização como filtro decorativo**. A imagem precisa ser concebida como pixel art desde a leitura das formas.

Rejeitar imagens que sejam essencialmente:

- pintura digital suave com mosaico aplicado por cima;
- ilustração 3D/CGI com pixels falsos;
- anime com filtro retrô;
- concept art painterly reduzida;
- vetor com ruído pixelado;
- imagem excessivamente nítida e lisa que apenas simule baixa resolução.

---

# 4. FORMATOS E CANVAS DE PRODUÇÃO

## 4.1 Masters de produção

| Categoria | Proporção | Master recomendado | Formato |
|---|---:|---:|---|
| Personagem jogável | 1:1 | 1024×1024 | PNG |
| NPC humanoide | 1:1 | 1024×1024 | PNG |
| Criatura / Elite / Chefe | 1:1 | 1024×1024 | PNG |
| Região / Local / Masmorra / Braseiro / cena narrativa | 4:3 horizontal | 1024×768 | PNG |
| Mapa ilustrado | 4:3 horizontal | 1024×768 | PNG |
| Moldura cosmética | 1:1 | 1024×1024 | PNG RGBA |
| Overlay de tela | igual ao canvas-alvo | igual ao master-alvo | PNG RGBA |

Essas dimensões são **masters de produção**, não uma afirmação sobre a resolução lógica dos pixels do mundo.

## 4.2 Área segura

### Personagem/criatura 1:1

- manter cabeça e pés inteiros;
- preservar margem visual em todos os lados;
- figura normalmente ocupa aproximadamente 72–84% da altura;
- evitar armas, galhadas, asas ou acessórios tocando a borda sem necessidade;
- o eixo cabeça–tórax–quadril deve permanecer próximo ao centro em skins completas.

### Cenário 4:3

- nenhum elemento narrativo indispensável deve tocar os 4% externos do quadro;
- manter leitura clara de foreground, midground e background quando aplicável;
- quando a imagem for usada como fundo de personagem/perfil, preservar uma zona de contraste moderado no centro;
- não esconder informação importante em áreas que provavelmente receberão personagem, moldura ou recorte.

### Moldura

- exterior transparente;
- centro transparente;
- decoração concentrada em bordas/cantos;
- evitar invadir excessivamente a área útil do personagem;
- elementos de prestígio podem ser assimétricos, mas a leitura do perfil continua prioritária.

---

# 5. GRAMÁTICA DE PIXEL ART

## 5.1 Clusters

Priorizar **clusters de pixels** com intenção clara.

Usar:

- massas contínuas de sombra;
- bordas quebradas de forma deliberada;
- pixels isolados somente quando cumprem função de brilho, poeira, faísca ou textura específica;
- microdetalhe subordinado à forma maior.

Evitar:

- ruído de 1 pixel espalhado por toda a imagem;
- “sal e pimenta” em superfícies;
- textura igualmente intensa em pele, tecido, pedra e céu;
- bordas serrilhadas sem ritmo.

## 5.2 Anti-aliasing

O padrão é **sem anti-aliasing borrado**.

Permitido:

- anti-aliasing manual e localizado;
- uma transição curta de cor em curvas importantes;
- suavização mínima quando ela não destrói a leitura dos pixels.

Proibido:

- blur de borda;
- feathering amplo;
- glow usado para esconder serrilhado;
- interpolação bilinear/bicúbica em redimensionamento final de pixel art.

## 5.3 Dithering

Dithering é recurso pontual, não textura padrão.

Usos adequados:

- névoa;
- céu de transição curta;
- pedra muito gasta;
- metal oxidado;
- fumaça/cinza dispersa;
- passagem entre dois valores quando uma superfície exige granulação.

Evitar dithering forte em:

- pele;
- olhos;
- rosto;
- couro liso;
- superfícies pequenas;
- toda a imagem simultaneamente.

## 5.4 Gradientes

Gradiente suave contínuo deve ser evitado.

Preferir:

- bandas de valor;
- transições quebradas;
- massas de luz/sombra;
- dithering contido quando necessário.

---

# 6. VALOR, CONTRASTE E SATURAÇÃO

## 6.1 Hierarquia de valor

Cada asset precisa funcionar primeiro em valores, depois em cor.

Regras:

- silhueta principal distinguível do fundo;
- rosto/cabeça legíveis quando forem foco;
- arma/foco separado do corpo quando importante;
- pontos de luz não podem competir em quantidade com o foco principal;
- fundo recebe menos contraste local que o sujeito principal quando houver personagem/criatura.

## 6.2 Saturação

Asterion trabalha majoritariamente com saturação baixa a moderada.

Acentos saturados devem ser:

- pequenos;
- justificados por material, fogo, biologia, Trama, Presságio, Luz ou função regional;
- subordinados à composição.

Não usar saturação alta como atalho para “raridade”, “magia” ou “importância”.

## 6.3 Luz

Preferir:

- uma fonte dominante compreensível;
- luz secundária apenas quando justificada;
- sombras coerentes com a direção da luz;
- highlights concentrados em material apropriado.

Evitar:

- rim light genérico em todos os personagens;
- glow em todo objeto extraordinário;
- iluminação de estúdio moderna em cena medieval;
- luz contraditória apenas para recortar a silhueta.

---

# 7. RENDERIZAÇÃO DE MATERIAIS

## 7.1 Pele

- volumes do rosto e mãos legíveis;
- poucas faixas de valor bem controladas;
- textura não deve parecer pedra, plástico ou metal;
- tons de pele preservam diversidade definida na Bíblia de Personagens;
- fuligem, poeira, umidade ou sangue seco são camadas ambientais, não mudança racial.

## 7.2 Cabelo e barba

- tratar como massas antes de fios;
- mechas maiores definem volume;
- textura crespa/cacheada é construída por agrupamentos, não ruído aleatório;
- evitar fios individuais demais em resolução de pixel art;
- brilho deve seguir volume, não parecer plástico.

## 7.3 Tecido

- dobras principais indicam peso e direção;
- pano seco: borda mais rígida e poeira;
- pano encerado/úmido: massa mais pesada e brilho discreto;
- evitar tecido flutuando sem vento.

## 7.4 Couro

- menos brilho que metal;
- vincos próximos a articulações e fechos;
- desgaste em bordas e pontos de uso;
- não transformar todo couro em preto brilhante.

## 7.5 Metal

- highlights compactos;
- contraste mais duro que tecido/couro;
- ferrugem/oxidação localizadas;
- superfícies antigas continuam estruturais e não viram sucata amorfa;
- metal asteriano não parece cromado sci-fi.

## 7.6 Pedra

- massas grandes antes de rachaduras;
- rachaduras seguem tensão/idade, não padrão aleatório uniforme;
- ruína antiga conserva função arquitetônica legível;
- evitar cobrir toda pedra com runas.

## 7.7 Madeira

- veios sugeridos por poucos agrupamentos;
- madeira carbonizada usa preto/cinza com volume ainda legível;
- madeira úmida fica mais escura e pesada, não necessariamente verde.

## 7.8 Água, névoa e fumaça

- água: planos de valor e reflexo interrompido;
- névoa: reduz contraste, não apaga a cena inteira;
- fumaça/cinza: massas suaves construídas em pixels, sem brush airbrushed;
- nenhuma dessas camadas pode encobrir anatomia crítica sem motivo.

## 7.9 Fogo, brasa e Luz

- núcleo mais claro deve ocupar área pequena;
- bordas quentes se dissipam rapidamente;
- brasa é ponto de calor, não lava;
- Luz do Luminar não é automaticamente dourada, sagrada ou angelical.

---

# 8. ANATOMIA HUMANOIDE — QA OBRIGATÓRIO

A IA não pode ser autorizada a “resolver” anatomia por sugestão visual quando a imagem é usada como asset oficial.

## 8.1 Estrutura geral

Confirmar:

- uma cabeça;
- dois braços;
- duas pernas;
- ombros conectados corretamente ao tronco;
- cotovelos e joelhos em posições plausíveis;
- mãos conectadas aos punhos;
- pés conectados às pernas;
- nenhuma duplicação de membro causada por capa, sombra ou arma;
- roupa acompanhando o corpo sem atravessá-lo de forma impossível.

## 8.2 Mãos

Quando a mão estiver suficientemente visível:

- cinco dígitos no total, incluindo polegar;
- polegar em lado anatômico correto;
- dedos não duplicados;
- dedos não fundidos em massa sem motivo de perspectiva;
- empunhadura coerente com o objeto;
- palma e punho conectados.

Quando a pose tornaria a mão extremamente complexa e ela não for importante para a leitura, preferir:

- mão parcialmente coberta por luva/manopla;
- ângulo mais simples;
- objeto segurado por geometria limpa;
- pose diferente.

Não esconder erros anatômicos com fumaça, glow, partículas ou tecido aleatório.

## 8.3 Rosto

Confirmar:

- dois olhos quando ambos deveriam estar visíveis;
- nariz e boca alinhados com a perspectiva;
- orelhas coerentes com a cabeça;
- cabelo nasce do couro cabeludo e não atravessa face/olhos;
- barba conecta-se ao rosto;
- orelhas Veladas largas/laterais corretamente conectadas, sem duplicação;
- exatamente um par de chifres Hemários quando a Raça for Hemária, fisicamente conectado ao crânio;
- caninos inferiores Cinéreos curtos e integrados à dentição, sem duplicação de boca/dentes;
- orelhas Alvoranas longas/pontiagudas corretamente conectadas;
- ausência de halo/asas raciais em Alvoranos.

## 8.3.1 Estruturas raciais v1.1

Quando presentes, tratar estruturas raciais como anatomia crítica:

- chifres precisam nascer do crânio e manter perspectiva/simetria plausível;
- nunca gerar chifre flutuante, terceiro chifre ou base atravessando cabelo/elmo sem encaixe;
- orelhas Veladas e Alvoranas precisam manter duas unidades, posição coerente e conexão anatômica;
- equipamento de cabeça deve ser desenhado ao redor dessas estruturas;
- caninos Cinéreos não podem se multiplicar, atravessar lábio ou virar presas gigantes;
- nenhuma Aparência temática pode remover marcador anatômico obrigatório sem Fonte específica.

## 8.4 Pés

- ambos completos quando visíveis;
- contato claro com o chão;
- botas não podem fundir-se com pedra/sombra;
- direção dos pés precisa acompanhar a postura.

---

# 9. ESTADOS DE POSE

Usar os sete estados definidos na Bíblia Visual de Personagens:

1. Repouso;
2. Contemplação;
3. Vigilância;
4. Deslocamento;
5. Preparação;
6. Ação controlada;
7. Ação intensa.

## Regra de distribuição

Em uma coleção grande de personagens:

- não concentrar todos em Preparação/Ação;
- Repouso, Contemplação, Vigilância e Deslocamento devem aparecer com frequência real;
- Ação intensa deve ser minoria;
- classes diferentes podem compartilhar o mesmo estado sem repetir exatamente a mesma pose;
- duas versões cosméticas do mesmo personagem podem usar estados diferentes, mantendo a identidade física.

## Regra de legibilidade

A pose nunca pode sacrificar:

- anatomia;
- leitura racial;
- leitura da Classe;
- integridade da arma;
- centralização quando a arte for skin completa.

---

# 10. ARMAS, FOCOS E EQUIPAMENTO

Toda arma/foco deve parecer:

- completa;
- utilizável;
- equilibrada;
- conectada corretamente;
- compatível com metalurgia/artesanato de Asterion;
- segura na mão, bainha, suporte ou alça.

Rejeitar:

- lâmina sem cabo;
- cabo que atravessa a mão;
- duas pontas incompatíveis geradas por duplicação;
- escudo fundido ao antebraço;
- aljava atravessando capa;
- arma que muda de formato entre frente e fundo;
- foco flutuante sem motivo canônico;
- arma moderna.

## 10.1 Estado do equipamento

O equipamento pode estar:

- guardado;
- apoiado;
- carregado;
- preparado;
- em guarda;
- em uso.

A ferramenta não precisa dominar a imagem para comunicar Classe.

## 10.2 Escudos

- escudo é opcional para Sentinela salvo asset específico;
- mão/antebraço devem conectar-se ao sistema de pegada/alça;
- perspectiva do escudo deve coincidir com a postura;
- não ocultar metade do corpo em toda arte de Sentinela;
- não transformar escudo em símbolo religioso automático.

## 10.3 Arcos

### Estado relaxado

Permitido:

- arco nas costas;
- arco abaixado;
- arco apoiado no ombro;
- arco segurado lateralmente;
- arco durante deslocamento.

A corda continua existindo e conecta as duas extremidades.

### Preparação

Permitido:

- retirar flecha da aljava;
- posicionar flecha;
- encaixar nock;
- erguer o arco;
- ajustar postura.

### Tensionado

Obrigatório:

- uma corda contínua;
- corda presa às duas extremidades;
- uma flecha coerente;
- nock alinhado à corda;
- mão do arco segurando o grip;
- mão da corda puxando em direção plausível;
- flecha orientada para a linha de mira;
- membros do arco flexionados de maneira consistente.

Rejeitar imediatamente:

- duas cordas;
- corda atravessando torso/rosto;
- flecha sem ponta/haste contínua;
- flecha atravessando mão;
- arco com membros desconectados;
- aljava na frente da corda durante a puxada;
- flecha flutuando sem contato com arco/corda.

## 10.4 Bestas

- coronha, arco, corda e trilho precisam formar um único objeto;
- virote alinhado ao trilho;
- não transformar em rifle moderno;
- mecanismo medieval/fantástico plausível e simples.

## 10.5 Focos de Tecelão/Oráculo/Luminar

- nenhum foco é universal;
- objeto extraordinário deve parecer fisicamente segurável/transportável;
- efeitos surgem ao redor do gesto/foco, não substituem sua geometria;
- não criar cajado obrigatório para Tecelão;
- não criar bola de cristal obrigatória para Oráculo;
- não criar símbolo religioso obrigatório para Luminar.

---

# 11. PERSONAGENS E APARÊNCIAS

## 11.1 Identidade persistente

Quando duas imagens representam a mesma âncora de personagem em Aparências diferentes, preservar preferencialmente:

- estrutura facial;
- tom de pele;
- textura/cor de cabelo, salvo mudança cosmética intencional;
- idade aparente;
- constituição corporal;
- traços raciais centrais;
- gênero/apresentação escolhidos.

A Aparência pode mudar roupa, armadura aparente, acabamento, acessórios, desgaste e tema regional conforme a Fonte de Personagens.

## 11.2 Aparência não reescreve Classe

Uma Aparência deve adaptar-se à Classe sem apagar a Classe.

Exemplos:

- Errante das Cinzas + Sentinela continua lendo como Sentinela;
- Errante das Cinzas + Vigia continua lendo como Vigia;
- Errante das Cinzas + Tecelão não vira “mago de cinzas”.

## 11.3 Equipamento real

Quando o contexto da tela fizer a arma mecânica real importar, não usar uma Aparência fixa que induza leitura falsa do equipamento. Nesses contextos, a implementação pode:

- usar arte sem arma dominante;
- escolher variante compatível;
- renderizar arma separadamente no futuro;
- ou usar imagem contextual diferente.

Isso é uma restrição de apresentação, não criação de sistema novo.

---

# 12. CRIATURAS

Para criaturas, aplicar integralmente a Bíblia de Bestiário Visual antes desta seção.

Regras técnicas adicionais:

- contar membros quando a anatomia tiver número definido;
- patas devem tocar o chão ou superfície de forma plausível;
- mandíbula e olhos não podem se duplicar por textura;
- asas, galhadas, caudas e carapaças devem conectar-se ao corpo;
- não usar fumaça/sombra para esconder erro estrutural;
- Elite deve diferenciar-se por design, não apenas escala;
- Chefe precisa de silhueta reconhecível em miniatura.

---

# 13. CENÁRIOS

Para ambientes, aplicar integralmente a Bíblia de Ambientes antes desta seção.

## 13.1 Profundidade

Usar, quando aplicável:

- foreground com formas de enquadramento;
- midground com ação espacial principal;
- background com horizonte/arquitetura/bioma.

A profundidade deve surgir por:

- sobreposição;
- escala;
- contraste decrescente;
- saturação decrescente;
- névoa atmosférica controlada.

Evitar desfoque fotográfico intenso.

## 13.2 Perspectiva

- linhas arquitetônicas devem convergir de forma consistente;
- escadas, portas e passagens precisam ser utilizáveis;
- pilares não podem mudar de espessura sem motivo;
- pontes e plataformas precisam conectar-se a algo;
- ruína pode estar quebrada, mas sua função anterior ainda deve ser inferível.

## 13.3 Céu e clima

- céu serve ao bioma e à luz;
- não usar tempestade dramática por padrão;
- nuvens não precisam ter o mesmo contraste do foco principal;
- névoa deve obedecer profundidade.

---

# 14. TRANSPARÊNCIA E COMPOSIÇÃO

## 14.1 PNG RGBA

Usar transparência somente quando o asset tiver função real de composição:

- Moldura;
- Overlay;
- elemento isolado explicitamente reutilizável.

Não exigir transparência de todo personagem ou criatura se a arte oficial utilizar fundo contextual.

## 14.2 Alpha

- bordas transparentes precisam ser limpas;
- evitar halo branco/preto ao redor do recorte;
- nenhum pixel semitransparente amplo usado para fingir blur;
- sombras projetadas só permanecem quando fizerem sentido no contexto de composição.

## 14.3 Overlay

Overlay não substitui imagem-base.

- deve comunicar estado sem ocultar contexto;
- ornamento ocupa borda/áreas negativas;
- centro preserva leitura do evento;
- não adicionar texto dentro do PNG salvo decisão explícita de UI;
- canvas e proporção precisam coincidir exatamente com a imagem-base.

---

# 15. PÓS-PROCESSAMENTO

Permitido:

- limpeza manual de pixels;
- correção de anatomia localizada;
- ajuste controlado de valor/saturação;
- remoção de artefatos;
- reforço de cluster;
- conversão/exportação PNG;
- redimensionamento por nearest-neighbor quando a escala for inteira.

Evitar:

- filtro automático de pixelização como solução para arte lisa;
- sharpen forte;
- denoise que apague clusters;
- blur;
- interpolação bicúbica no master final;
- JPEG intermediário;
- chromatic aberration;
- film grain fotográfico;
- bloom genérico.

Se a geração-base não possui linguagem de pixel art suficiente, **regenerar** é preferível a tentar “salvar” com filtro.

---

# 16. ARQUITETURA DE PROMPT

Todo prompt oficial deve conter, nesta ordem lógica:

1. tipo de asset;
2. identidade canônica;
3. Região/contexto;
4. anatomia/silhueta;
5. Classe/Caminho ou função, quando aplicável;
6. roupa/equipamento/material;
7. estado de pose;
8. ação específica, se houver;
9. ambiente/fundo;
10. iluminação;
11. composição e centralização;
12. gramática de pixel art;
13. elementos obrigatórios;
14. proibições específicas;
15. negative prompt técnico global.

Não depender apenas de uma frase como “pixel art 16-bit”.

---

# 17. NEGATIVE PROMPT TÉCNICO GLOBAL

Acrescentar conceitualmente, adaptando à ferramenta:

- smooth digital painting;
- painterly brushwork;
- photorealism;
- 3D render;
- CGI;
- vector illustration;
- fake pixel filter;
- blurry edges;
- soft airbrush gradients;
- excessive bloom;
- chromatic aberration;
- film grain;
- JPEG artifacts;
- oversharpening;
- extra fingers;
- missing fingers;
- fused fingers;
- duplicated hands;
- duplicated arms;
- duplicated legs;
- malformed feet;
- disconnected limbs;
- broken weapon geometry;
- duplicated weapon;
- floating weapon parts;
- impossible grip;
- text;
- logo;
- watermark;
- UI baked into the art unless explicitly requested.

Somar a isso os negativos de Raça, Classe, criatura, Região ou Local definidos nas Bíblias especializadas.

---

# 18. NOMENCLATURA DE ARQUIVOS

Padrão de produção recomendado:

- letras minúsculas;
- `snake_case`;
- sem acentos;
- sem espaços;
- sem versão no nome do asset final de runtime quando o pipeline já possuir versionamento externo;
- nome deve indicar entidade antes de estado secundário.

Exemplos:

```text
mapa_terras_do_ocaso.png
cao_cinereo.png
vigia_partido.png
alda_veyr.png
moldura_pedra_fraturada.png
errante_das_cinzas/errante_das_cinzas_sentinela_remanescente_masculino.png
```

Para arquivos de produção/revisão, sufixos temporários são permitidos:

```text
_rascunho01
_revisao02
_aprovado
```

Remover esses sufixos do nome final consumido pelo runtime, se a implementação esperar um identificador estável.

---

# 19. QA DE PERSONAGEM / NPC

Antes de aprovar:

- [ ] Raça correta sem caricatura?
- [ ] Classe/função correta?
- [ ] Estado de pose declarado e legível?
- [ ] Corpo inteiro quando exigido?
- [ ] Cabeça–tórax–quadril centralizados quando exigido?
- [ ] Exatamente dois braços e duas pernas?
- [ ] Mãos plausíveis e sem dedos extras/fundidos?
- [ ] Pés completos e apoiados?
- [ ] Rosto coerente?
- [ ] Cabelo/barba conectados corretamente?
- [ ] Arma/foco é um objeto completo?
- [ ] Empunhadura é plausível?
- [ ] Arco/besta passa o checklist específico, se presente?
- [ ] Roupa não atravessa corpo/arma?
- [ ] Materiais parecem diferentes entre si?
- [ ] Fundo está subordinado?
- [ ] Pixel art é estrutural, não filtro?
- [ ] Não há texto/logo/watermark?
- [ ] Não há spoiler?

Qualquer falha anatômica crítica reprova o asset mesmo quando a atmosfera estiver boa.

---

# 20. QA DE CRIATURA

- [ ] espécie/natureza canônica legível?
- [ ] número e conexão de membros corretos?
- [ ] silhueta reconhecível?
- [ ] habitat coerente?
- [ ] variante/Elite/Chefe não substitui identidade-base indevidamente?
- [ ] materiais biológicos/minerais coerentes?
- [ ] sem aura genérica de raridade?
- [ ] sem membros/olhos/bocas duplicados por erro?
- [ ] fundo subordinado?
- [ ] pixel art coerente com personagens/cenários?

---

# 21. QA DE CENÁRIO

Além do checklist da Bíblia de Ambientes:

- [ ] proporção 4:3 correta?
- [ ] perspectiva consistente?
- [ ] passagens/escadas/portas possuem função espacial?
- [ ] foreground, midground e background estão separados?
- [ ] clima não apaga a leitura?
- [ ] materiais possuem tratamento próprio?
- [ ] sem excesso de microtextura?
- [ ] sem gradiente liso dominante?
- [ ] sem runas/luzes genéricas?
- [ ] sem elementos cortados na borda que pareçam erro?
- [ ] nenhuma informação crítica está na área de risco da interface?

---

# 22. POLÍTICA DE REGENERAÇÃO

## Regenerar obrigatoriamente quando houver

- anatomia quebrada;
- mão importante com erro evidente;
- arma/foco estruturalmente impossível;
- arco/besta incoerente;
- identidade racial contraditória;
- identidade de Classe perdida;
- criatura transformada em outro arquétipo;
- cenário em Região errada;
- spoiler visual;
- linguagem visual claramente fora de Asterion;
- pintura lisa impossível de corrigir sem filtro agressivo.

## Pode ser corrigido manualmente quando houver

- 1–3 pixels isolados de ruído;
- pequeno artefato de borda;
- assimetria mínima não intencional;
- contraste local ligeiramente ruim;
- detalhe secundário simples desconectado;
- pequeno erro de transparência.

A correção manual não deve reescrever silenciosamente o design canônico.

---

# 23. MATRIZ DE PRODUÇÃO VISUAL

`ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v1.0.md` funciona como controle editorial/operacional.

Ela pode definir, para um lote específico:

- idade aparente;
- tom de pele;
- cabelo;
- constituição;
- estado de pose;
- visibilidade da arma/foco;
- variação de enquadramento;
- ordem de produção;
- estado de aprovação.

Essas atribuições **não transformam tais características em regra biológica de Raça ou Classe**. Elas existem para garantir diversidade, consistência e evitar repetição no conjunto oficial de assets.

---

# 24. FECHAMENTO

Com esta Bíblia Técnica, a produção visual de Asterion passa a separar claramente três perguntas:

1. **O que existe?** — Fontes canônicas e regionais.
2. **Como isso deve parecer?** — Bíblias visuais especializadas.
3. **Como isso deve ser renderizado e aprovado?** — esta Bíblia Técnica.

A frase-guia de produção é:

> **Pixels visíveis não bastam. A forma, a matéria, a anatomia e a função precisam sobreviver ao pixel.**

---

# DOCUMENTO INCORPORADO 8/9
## Arquivo original: `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md`
# ASTERION — GUIA OPERACIONAL DE GERAÇÃO DE SKINS RAÇA × CLASSE v1.3

**Data:** 2026-10-12  
**Escopo:** Aparências padrão Raça × Classe, derivadas de imagem racial de referência  
**Estado:** documento operacional de produção visual  
**Subordinação:** este guia não cria cânone novo. Deve ser aplicado em conjunto com `SOURCE_AUTHORITY.md`, `ASTERION_BIBLIA_VISUAL_PERSONAGENS_RACAS_CLASSES_E_NPCS_v2.0.md`, `ASTERION_BIBLIA_TECNICA_DE_GERACAO_DE_IMAGENS_v1.1.md` e `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`.

---

# 1. OBJETIVO DESTE GUIA

Este documento existe para tornar a produção das 60 Aparências padrão Raça × Classe mais curta, consistente e reconhecível.

A regra editorial principal é:

> **Ao olhar a skin sem texto, o jogador deve reconhecer primeiro a Classe e ainda reconhecer claramente a Raça/personagem-base.**

**Regra v1.3 — anatomia racial:** a Classe pode cobrir parte do corpo, mas não pode apagar a anatomia diagnóstica da Raça. O prompt deve declarar explicitamente como capuz/elmo/armadura acomodam chifres ou orelhas quando presentes.

A imagem racial anexada é a **referência visual da identidade da pessoa**. O gerador pode e deve mudar pose, gestual, traje, armadura, arma/foco, acessórios e enquadramento do fundo para tornar a Classe imediatamente legível, mas não deve substituir o personagem por outra pessoa.

---

# 2. AUTORIDADE DA IMAGEM DE REFERÊNCIA

Ao gerar uma skin a partir de uma imagem racial anexada, preservar:

- identidade facial;
- estrutura do rosto;
- tom/subtom de pele;
- textura e cor-base do cabelo;
- idade aparente geral;
- constituição corporal geral;
- marcadores raciais fortes;
- sinais individuais reconhecíveis.

Pode variar para a skin de Classe:

- pose;
- direção da cabeça e do olhar;
- postura;
- penteado funcional **sem descaracterizar a pessoa**;
- vestuário;
- armadura;
- arma/foco;
- acessórios;
- reparos e acabamento;
- enquadramento e detalhes secundários do fundo;
- horário/luz, desde que o contexto permaneça correto.

Não transformar uma variação de Classe em outra pessoa da mesma Raça.

Para futuras skins alternativas do mesmo personagem, pose, penteado, armas, acabamentos e contexto podem variar ainda mais. Tom de pele e identidade facial permanecem estáveis, salvo decisão explícita de produzir outro personagem/âncora.

---

# 3. PRIORIDADE DE LEGIBILIDADE DE CLASSE

A Aparência padrão é básica, mas **não deve ser genérica**.

Em leitura de miniatura, a Classe deve ser identificável por pelo menos três eixos: silhueta, arma-assinatura, traje/armadura, postura/gestual e função espacial do fundo.

## Arma-assinatura obrigatória

> **Toda Aparência padrão Raça × Classe deve mostrar a arma-assinatura da Classe de forma imediatamente legível.**

- **Sentinela:** arma de uma mão + escudo visível.
- **Errante:** duas armas curtas visíveis; preferir uma em cada mão quando a pose permitir.
- **Vigia:** arco ou besta como arma principal.
- **Tecelão:** arma-foco de Trama visível; não usar espada comum como único marcador.
- **Oráculo:** arma-foco oracular/simbólica visível.
- **Luminar:** cajado/bastão de combate-foco visível como assinatura principal.

A arma pode estar empunhada, baixa, apoiada, embainhada ou presa em suporte funcional conforme a pose. Estados `mãos livres`, Repouso ou Contemplação **não removem a assinatura**.

Essa regra é exclusivamente visual/editorial e não define o equipamento mecânico do personagem.

## Regra anti-personagem genérico

Reprovar se duas ou mais Classes da mesma Raça parecerem o mesmo traje-base com objeto trocado. Em especial, não repetir mesma túnica principal, mesmo lenço/cachecol dominante, mesmas braçadeiras, mesma distribuição de couro/metal ou mesmo skyline/fortaleza.

A Classe deve mudar **arquitetura do torso + distribuição de equipamento + arma-assinatura + postura**.

---

# 4. REGRA DE POSE E VARIEDADE

Não repetir a pose-base da imagem racial.

Variar deliberadamente entre as skins:

- direção do corpo;
- direção da cabeça;
- direção dos olhos;
- inclinação do queixo;
- distribuição de peso;
- posição dos pés;
- rotação de torso/quadril;
- posição dos braços;
- estado da arma/foco.

Evitar catálogo em que todos:

- olham para o mesmo lado;
- ficam em 3/4 idêntico;
- mantêm pés paralelos;
- deixam ambos os braços caídos;
- usam a mesma distância de câmera.

Estados de pose válidos:

- Repouso;
- Contemplação;
- Vigilância;
- Deslocamento;
- Preparação;
- Ação controlada;
- Ação intensa.

Ação intensa deve ser minoria. A Aparência padrão deve privilegiar leitura clara de Classe, não espetáculo.

---

# 5. GRAMÁTICA VISUAL DAS SEIS CLASSES

## 5.1 Sentinela

**Leitura imediata:** resistência, posição, defesa ativa e resposta.

**Assinatura obrigatória:** **arma de uma mão + escudo visível**. O escudo pode estar no braço, apoiado ou preso às costas, mas não desaparecer.

**Traje:** armadura média/pesada, placas, malha, couro reforçado, torso blocado e ombros protegidos.

**Não fazer:** paladino, berserker, tanque imóvel, escudo com iconografia religiosa.

## 5.2 Errante

**Leitura imediata:** mobilidade, brecha, oportunismo e mudança de direção.

**Assinatura obrigatória:** **duas armas curtas** — adagas, facas longas, duas lâminas curtas ou espada curta + adaga. Preferir **uma em cada mão** quando a anatomia/pose permitir; em repouso, uma pode estar guardada, mas as duas devem ser visíveis.

**Traje:** camadas leves, couro/tecido reforçado, casaco curto/dividido, pernas livres e equipamento rente ao corpo.

**Não fazer:** ninja, assassino genérico, espada longa pesada, ladrão encapuzado obrigatório.

## 5.3 Vigia

**Leitura imediata:** distância, observação acumulada e precisão.

**Assinatura obrigatória:** **arco ou besta sempre visível**; faca/adaga de campo pode ser secundária.

**Traje:** proteção leve/média, manto curto, braçadeira funcional, arnês e munição organizada.

**Não fazer:** sniper moderno, ranger-floresta obrigatório, equipamento militar contemporâneo.

## 5.4 Tecelão

**Leitura imediata:** manipulação técnica da Trama — Perceber → Tensionar → Resolver.

**Assinatura obrigatória:** **arma-foco de Trama**, escolhida entre lâmina-foco, bastão-foco curto, cetro técnico, agulha/fuso de Trama ou haste segmentada. Deve parecer extraordinária pela função e construção, não por glow genérico.

**Traje:** casaco técnico/sobreposição estruturada, mangas ajustadas, braceletes/luvas, placas de medida e instrumentos físicos.

**Não fazer:** espada comum como único marcador, cajado de mago clássico, mana líquida, portal, holograma.

## 5.5 Oráculo

**Leitura imediata:** antecipação e leitura de possibilidades próximas.

**Assinatura obrigatória:** **arma-foco oracular/simbólica** — cajado/cetro oracular, bastão marcado ou lâmina simbólica ritual. Pode haver lâmina curta secundária. O foco deve ser visualmente interpretativo/simbólico, não técnico como o Tecelão.

**Traje:** camadas de viagem verticais, suporte para placas/fios/marcadores e assimetria de observação.

**Não fazer:** bola de cristal universal, terceiro olho, zodíaco, cartomante genérica, foco técnico de Trama.

## 5.6 Luminar

**Leitura imediata:** vitalidade, estabilidade e Luz exteriorizada pelo praticante.

**Assinatura obrigatória:** **cajado ou bastão de combate-foco** sempre visível. Pode ser curto, médio ou longo; deve ser robusto e funcional. Espada/maça/escudo podem aparecer como secundários quando a âncora pedir.

**Traje:** proteção variável, composição centrada, frente do torso clara e braços livres para sustentação/projeção.

**Luz:** somente quando a âncora permitir; sem halo. A classe deve continuar legível pelo cajado, traje e postura mesmo sem Luz ativa.

**Não fazer:** paladino cristão, cruzes, halo, asas, sacerdote de robe branco.

---

# 6. REGRA DE TRAJE

Para toda Aparência padrão, o traje deve ser imediatamente compatível com a Classe.

Não basta trocar apenas a arma.

A roupa deve alterar:

- distribuição visual de peso;
- proteção;
- liberdade de movimento;
- quantidade de equipamento;
- leitura de função.

Resumo:

| Classe | Traje-base |
|---|---|
| Sentinela | armadura média/pesada; placas, malha, couro reforçado |
| Errante | camadas leves; couro/tecido reforçado; pequenas placas; pernas livres |
| Vigia | proteção leve/média; capa curta; braçadeira; munição/equipamento de campo |
| Tecelão | roupa técnica de precisão; braceletes/luvas/instrumentos; proteção leve |
| Oráculo | roupa prática de viagem; marcadores/ferramentas simbólicas discretas |
| Luminar | proteção variável, porém firme/centrada; arma/foco claro; sem estética religiosa automática |

---

# 7. FUNDOS DE HERANÇA RACIAL

O fundo nunca é apenas decoração genérica. Ele combina herança racial e função de Classe.

| Raça | Motivo de herança | Evitar |
|---|---|---|
| Remanescente | reconstrução em camadas; via, ponte, oficina e materiais reaproveitados | miséria caricata, ruína vazia genérica |
| Velado | limiar frio; arcos/umbrais repetidos; névoa fina; quase-alinhamento | Avesso, portal, void purple, cemitério gótico |
| Cinéreo | terreno severo; sustentação; contrapesos; vento; arquitetura de carga | lava, magma, corpo/arquitetura de pedra racial |
| Hemário | instalação Hemaris clínico-logística envelhecida; metal oxidado; canais cobertos | gore, laboratório sci-fi, Matriz Rubra explícita |
| Alvorano | terraço/rota civil pré-Ruptura; horizonte; orientação; luz clara | templo solar, halo, arquitetura celestial |

---

# 8. MATRIZ DOS 30 FUNDOS RAÇA × CLASSE

A apresentação masculina e feminina da mesma combinação usa a mesma família espacial, mas deve variar câmera, lado do foco, horário e detalhe secundário.

| Raça | Classe | Fundo-base |
|---|---|---|
| Remanescente | Sentinela | portão reconstruído com pedra de épocas diferentes e madeira nova; área de guarda comunitária |
| Remanescente | Errante | bifurcação entre rua antiga e passarela reparada, com várias rotas improvisadas |
| Remanescente | Vigia | torre/andaime reconstruído sobre ruína baixa, oferecendo linha de visão sobre assentamento vivo |
| Remanescente | Tecelão | oficina de reparo instalada sobre juntas antigas de pedra, medições físicas e peças reaproveitadas |
| Remanescente | Oráculo | encruzilhada de rotas remendadas com placas de direção de épocas diferentes, sem profecia explícita |
| Remanescente | Luminar | posto comunitário de recuperação junto a abrigo reconstruído e braseiro funcional discreto |
| Velado | Sentinela | umbral frio e estreito entre arcos quase alinhados, transformado em passagem defensiva |
| Velado | Errante | sequência de corredores/escadas liminares com duas saídas visualmente próximas e névoa fina |
| Velado | Vigia | mirante de pedra pálida com arcos repetidos e horizonte parcialmente oculto por névoa |
| Velado | Tecelão | galeria fria de juntas geométricas e placas técnicas antigas, linhas físicas quase coincidentes |
| Velado | Oráculo | cruzamento de três umbrais semelhantes com marcadores discretos; caminhos possíveis sem destino afirmado |
| Velado | Luminar | abrigo liminar de pedra clara com foco de calor funcional e sombras suaves, sem templo ou aura |
| Cinéreo | Sentinela | passagem entre muros de contenção e blocos pesados, feita para receber carga e impacto |
| Cinéreo | Errante | trilha estreita entre rocha e contrapesos, com vento lateral e apoios firmes |
| Cinéreo | Vigia | mirante de pedra robusta acima de terreno severo, marcos de distância presos contra vento |
| Cinéreo | Tecelão | estação de manutenção de contrapesos e juntas estruturais, pedra/metal sob tensão física |
| Cinéreo | Oráculo | entroncamento de passagens pesadas marcado por pilares, correntes e orientação redundante |
| Cinéreo | Luminar | posto de recuperação protegido do vento por paredes baixas e lã/couro, calor funcional discreto |
| Hemário | Sentinela | portão interno de antiga instalação Hemaris, placas de proteção e corredor clínico-logístico gasto |
| Hemário | Errante | passagem de serviço entre alas antigas, tubos/canais cobertos e rotas de manutenção laterais |
| Hemário | Vigia | plataforma logística elevada sobre pátio médico antigo, visão longa e ferrugem controlada |
| Hemário | Tecelão | sala de manutenção analógica com placas, escalas e juntas de infraestrutura Hemaris, sem sci-fi |
| Hemário | Oráculo | cruzamento de corredores clínicos com sinalização apagada e múltiplas rotas possíveis |
| Hemário | Luminar | posto de triagem/recuperação antigo, leitos vazios ou bancos funcionais sem gore, luz quente pequena |
| Alvorano | Sentinela | posto civil pré-Ruptura de controle de passagem, linhas limpas e horizonte aberto |
| Alvorano | Errante | terraço de rota com duas rampas e marcadores baixos, sugerindo decisão rápida de deslocamento |
| Alvorano | Vigia | plataforma de orientação com horizonte amplo, marcos de distância e instrumentos analógicos simples |
| Alvorano | Tecelão | pátio técnico pré-Ruptura com placas de medição, juntas e organização metódica, sem brilho |
| Alvorano | Oráculo | cruzamento civil de rotas com marcadores duplicados e caminhos divergentes sob luz clara |
| Alvorano | Luminar | pátio de apoio e recuperação pré-Ruptura com foco de calor funcional e equipamentos organizados, sem templo |

---

# 9. ÂNCORAS DE APARÊNCIA PADRÃO — EQUIPAMENTO/POSE

A identidade física vem da imagem racial anexada. A tabela abaixo controla principalmente **estado, arma/foco e gestual-base**.

## 9.1 Remanescente

| ID | Classe | Apresentação | Aparência padrão |
|---|---|---|---|
| PV-REM-SEN-M | Sentinela | Masculina | **Vigilância** — espada de uma mão baixa + escudo médio no braço |
| PV-REM-ERR-M | Errante | Masculina | **Deslocamento** — espada curta + adaga, uma em cada mão |
| PV-REM-VIG-M | Vigia | Masculina | **Contemplação** — arco nas costas; mãos livres; faca de campo visível |
| PV-REM-TEC-M | Tecelão | Masculina | **Contemplação** — bastão-foco curto de Trama na mão; outra mão examina relação espacial |
| PV-REM-ORA-M | Oráculo | Masculina | **Contemplação** — cetro oracular curto + placa marcada; lâmina simbólica visível |
| PV-REM-LUM-M | Luminar | Masculina | **Repouso** — cajado de combate-foco apoiado; sem Luz ativa |
| PV-REM-SEN-F | Sentinela | Feminina | **Repouso** — maça apoiada + escudo médio visível |
| PV-REM-ERR-F | Errante | Feminina | **Vigilância** — duas lâminas curtas, uma em cada mão |
| PV-REM-VIG-F | Vigia | Feminina | **Vigilância** — arco abaixado; adaga secundária visível |
| PV-REM-TEC-F | Tecelão | Feminina | **Vigilância** — lâmina-foco baixa e bracelete técnico |
| PV-REM-ORA-F | Oráculo | Feminina | **Vigilância** — lâmina simbólica curta + fio de marcadores; cetro preso |
| PV-REM-LUM-F | Luminar | Feminina | **Contemplação** — cajado de combate-foco curto; sem brilho |

## 9.2 Velado

| ID | Classe | Apresentação | Aparência padrão |
|---|---|---|---|
| PV-VEL-SEN-M | Sentinela | Masculina | **Contemplação** — martelo de uma mão guardado + escudo estreito visível; mãos livres |
| PV-VEL-ERR-M | Errante | Masculina | **Repouso** — duas lâminas curtas visíveis, uma baixa e outra guardada |
| PV-VEL-VIG-M | Vigia | Masculina | **Deslocamento** — besta carregada baixa + adaga secundária |
| PV-VEL-TEC-M | Tecelão | Masculina | **Repouso** — cetro técnico de Trama apoiado + lâmina-foco secundária |
| PV-VEL-ORA-M | Oráculo | Masculina | **Repouso** — cajado oracular esguio apoiado + lâmina simbólica |
| PV-VEL-LUM-M | Luminar | Masculina | **Vigilância** — cajado de combate-foco baixo; postura centrada |
| PV-VEL-SEN-F | Sentinela | Feminina | **Preparação** — espada reta sendo sacada + escudo leve |
| PV-VEL-ERR-F | Errante | Feminina | **Ação controlada** — passo lateral com espada curta + adaga off-hand |
| PV-VEL-VIG-F | Vigia | Feminina | **Preparação** — retirando flecha; arco visível + faca longa |
| PV-VEL-TEC-F | Tecelão | Feminina | **Preparação** — agulha/fuso de Trama + bracelete técnico |
| PV-VEL-ORA-F | Oráculo | Feminina | **Preparação** — duas lâminas simbólicas + cetro oracular curto |
| PV-VEL-LUM-F | Luminar | Feminina | **Preparação** — bastão de combate-foco + Luz localizada mínima |

## 9.3 Cinéreo

| ID | Classe | Apresentação | Aparência padrão |
|---|---|---|---|
| PV-CIN-SEN-M | Sentinela | Masculina | **Deslocamento** — machado curto baixo + escudo robusto |
| PV-CIN-ERR-M | Errante | Masculina | **Contemplação** — duas facas longas visíveis; uma guardada e outra baixa |
| PV-CIN-VIG-M | Vigia | Masculina | **Repouso** — arco robusto apoiado no ombro + faca de campo |
| PV-CIN-TEC-M | Tecelão | Masculina | **Deslocamento** — haste segmentada de Trama baixa + lâmina-foco curta |
| PV-CIN-ORA-M | Oráculo | Masculina | **Deslocamento** — bastão oracular marcado + pequeno sino + lâmina simbólica |
| PV-CIN-LUM-M | Luminar | Masculina | **Deslocamento** — cajado de combate-foco curto; brilho ausente |
| PV-CIN-SEN-F | Sentinela | Feminina | **Ação controlada** — guarda com maça + escudo robusto |
| PV-CIN-ERR-F | Errante | Feminina | **Preparação** — espada curta + adaga sendo acessadas |
| PV-CIN-VIG-F | Vigia | Feminina | **Ação controlada** — arco recurvo robusto erguido + lâmina curta |
| PV-CIN-TEC-F | Tecelão | Feminina | **Ação controlada** — lâmina-foco robusta e linhas de Trama localizadas |
| PV-CIN-ORA-F | Oráculo | Feminina | **Ação controlada** — lâmina simbólica curta + cetro oracular; trajetória incompleta |
| PV-CIN-LUM-F | Luminar | Feminina | **Ação controlada** — cajado de combate-foco + Luz localizada, sem halo |

## 9.4 Hemário

| ID | Classe | Apresentação | Aparência padrão |
|---|---|---|---|
| PV-HEM-SEN-M | Sentinela | Masculina | **Repouso** — espada de uma mão embainhada + escudo médio apoiado |
| PV-HEM-ERR-M | Errante | Masculina | **Vigilância** — sabre curto + adaga off-hand, corpo em transição |
| PV-HEM-VIG-M | Vigia | Masculina | **Vigilância** — besta compacta baixa + espada curta secundária |
| PV-HEM-TEC-M | Tecelão | Masculina | **Contemplação** — lâmina-foco estreita + placa de inscrição técnica |
| PV-HEM-ORA-M | Oráculo | Masculina | **Contemplação** — cetro oracular + lâmina simbólica curta; estojo fechado |
| PV-HEM-LUM-M | Luminar | Masculina | **Repouso** — cajado de combate-foco apoiado + escudo pequeno secundário |
| PV-HEM-SEN-F | Sentinela | Feminina | **Vigilância** — lança curta de uma mão + escudo pequeno |
| PV-HEM-ERR-F | Errante | Feminina | **Deslocamento** — duas lâminas curtas visíveis, uma em cada mão |
| PV-HEM-VIG-F | Vigia | Feminina | **Contemplação** — arco longo ao lado do corpo + faca de campo |
| PV-HEM-TEC-F | Tecelão | Feminina | **Preparação** — bastão-foco curto de Trama + lâmina secundária |
| PV-HEM-ORA-F | Oráculo | Feminina | **Vigilância** — lâmina simbólica baixa + bastão oracular curto |
| PV-HEM-LUM-F | Luminar | Feminina | **Vigilância** — cajado/bastão de combate-foco baixo; tórax centrado |

## 9.5 Alvorano

| ID | Classe | Apresentação | Aparência padrão |
|---|---|---|---|
| PV-ALV-SEN-M | Sentinela | Masculina | **Deslocamento** — martelo curto baixo + escudo pequeno no braço |
| PV-ALV-ERR-M | Errante | Masculina | **Preparação** — espada curta + adaga, duas mãos armadas |
| PV-ALV-VIG-M | Vigia | Masculina | **Preparação** — encaixando flecha; arco recurvo + lâmina curta secundária |
| PV-ALV-TEC-M | Tecelão | Masculina | **Vigilância** — cetro técnico/agulha de Trama + luvas técnicas |
| PV-ALV-ORA-M | Oráculo | Masculina | **Preparação** — bastão/cetro oracular + fio de marcação + lâmina simbólica |
| PV-ALV-LUM-M | Luminar | Masculina | **Preparação** — cajado de combate-foco em guarda; Luz apenas localizada |
| PV-ALV-SEN-F | Sentinela | Feminina | **Preparação** — espada reta em guarda + escudo leve |
| PV-ALV-ERR-F | Errante | Feminina | **Repouso** — duas lâminas leves/curtas visíveis, uma apoiada e outra guardada |
| PV-ALV-VIG-F | Vigia | Feminina | **Ação controlada** — mira com arco longo tensionado + espada curta secundária |
| PV-ALV-TEC-F | Tecelão | Feminina | **Ação controlada** — lâmina-foco resolvendo tensão localizada |
| PV-ALV-ORA-F | Oráculo | Feminina | **Ação controlada** — lâmina simbólica + cetro curto; duplicação breve de gesto |
| PV-ALV-LUM-F | Luminar | Feminina | **Ação controlada** — cajado de combate-foco + barreira curta translúcida |

---

# 10. ORDEM OPERACIONAL DE PRODUÇÃO

Produzir uma Raça inteira antes de passar à próxima.

Dentro de cada Raça:

1. Sentinela Masculino
2. Errante Masculino
3. Vigia Masculino
4. Tecelão Masculino
5. Oráculo Masculino
6. Luminar Masculino
7. Sentinela Feminino
8. Errante Feminino
9. Vigia Feminino
10. Tecelão Feminino
11. Oráculo Feminino
12. Luminar Feminino

Ordem racial:

1. Remanescente
2. Velado
3. Cinéreo
4. Hemário
5. Alvorano

---

# 11. NOMENCLATURA

Arquivo de Aparência padrão:

```text
aparencia_padrao_<raca>_<classe>_<masculino|feminino>.png
```

Exemplos:

```text
aparencia_padrao_remanescente_vigia_feminino.png
aparencia_padrao_velado_tecelao_masculino.png
aparencia_padrao_cinereo_sentinela_feminino.png
```

---

# 12. FORMATO TÉCNICO OBRIGATÓRIO

Para skins jogáveis:

- 1:1;
- master 1024×1024;
- PNG;
- corpo inteiro;
- cabeça e pés completos;
- margens seguras;
- personagem normalmente ocupa 72–84% da altura;
- eixo cabeça–tórax–quadril próximo ao centro;
- arma/foco completamente dentro da área segura quando possível;
- fundo subordinado ao personagem.

Pixel art:

- clusters intencionais;
- microdetalhe subordinado à forma;
- sem blur de anti-aliasing;
- dithering pontual;
- baixa/moderada saturação;
- uma fonte de luz dominante compreensível;
- materiais distintos: pele, cabelo, tecido, couro, metal, pedra e madeira.

---

# 13. ANATOMIA E INTEGRIDADE DE ARMA — QA

Confirmar antes de aprovar:

- uma cabeça;
- dois braços;
- duas mãos;
- duas pernas;
- dois pés;
- ombros, cotovelos e joelhos plausíveis;
- mãos conectadas aos punhos;
- cinco dígitos quando suficientemente visíveis;
- polegar no lado correto;
- arma/foco não atravessa corpo;
- empunhadura coerente;
- bainha/aljava/escudo presos fisicamente;
- roupa acompanha anatomia;
- nenhuma fumaça, glow ou tecido usado para esconder erro.

---

# 14. CHECKLIST DE APROVAÇÃO RÁPIDA

Aprovar somente se todas as respostas críticas forem `SIM`:

1. É claramente a mesma pessoa da imagem racial anexada?
2. A Raça continua legível?
3. Sem título ou nome, a Classe é reconhecível em poucos segundos?
4. A arma/foco/equipamento pertence visualmente à Classe?
5. O traje pertence visualmente à Classe?
6. A pose está diferente das skins anteriores?
7. Cabeça e olhar variam em relação às imagens anteriores?
8. O fundo mantém herança racial + função de Classe?
9. O personagem continua sendo o foco?
10. Anatomia está correta?
11. Arma/foco está fisicamente íntegro?
12. Não existe clichê proibido da Classe/Raça?

Se a resposta para `3`, `4` ou `5` for `NÃO`, **regenerar mesmo que a imagem esteja bonita**.

---

# 15. PROMPT-MESTRE CURTO PARA USAR COM ESTE DOCUMENTO

Quando este arquivo estiver adicionado às Fontes do Projeto, anexar a imagem racial e usar um prompt curto no seguinte formato:

```text
Leia integralmente `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md` e use também as Fontes visuais vigentes do Projeto.

Use a imagem anexada como personagem-base obrigatório e gere a Aparência padrão:

RAÇA: <RAÇA>
CLASSE: <CLASSE>
APRESENTAÇÃO: <MASCULINA/FEMININA>
ID: <ID DA MATRIZ>
ARQUIVO: <NOME EXATO>.png

Prioridade: a skin deve ser imediatamente reconhecível como <CLASSE> por **arma-assinatura visível**, traje exclusivo da Classe, silhueta e pose, sem perder a identidade da pessoa e da Raça da imagem de referência. Mesmo com `mãos livres` ou `sem foco`, mantenha a arma embainhada/presa conforme a Matriz v1.3.

Pode mudar pose, direção da cabeça/olhar, traje, arma/foco, acessórios e enquadramento do fundo. Preserve o contexto Raça × Classe e respeite a âncora de Aparência padrão correspondente.

Não escreva explicações: gere a imagem.
```

---

# 16. PROMPT ULTRACURTO PARA O FLUXO DIÁRIO

Depois que o documento estiver nas Fontes e a imagem racial estiver anexada:

```text
Leia `ASTERION_GUI_GERACAO_SKINS_RACA_CLASSE_v1.3.md` e as Fontes visuais vigentes. Use a imagem anexada como a mesma pessoa e gere a próxima Aparência padrão da sequência: <ID / RAÇA / CLASSE / APRESENTAÇÃO>. Priorize leitura imediata da Classe por arma-assinatura visível, traje exclusivo, silhueta e pose; varie cabeça/olhar/pose e preserve o fundo Raça × Classe. Gere a imagem sem explicações.
```

---

# 17. PRINCÍPIO FINAL

> **A Raça diz quem é a pessoa. A Classe diz imediatamente o que ela faz. A skin padrão precisa comunicar as duas coisas antes de qualquer efeito especial.**

---

# DOCUMENTO INCORPORADO 9/9
## Arquivo original: `ASTERION_MATRIZ_DE_PRODUCAO_VISUAL_v2.0.md`
# ASTERION — MATRIZ DE PRODUÇÃO VISUAL v2.0

**Data de consolidação:** 2026-10-12  
**Escopo:** controle editorial de identidade fenotípica, diversidade, continuidade visual, pose, variação e fundos para seleção racial e produção Raça × Classe  
**Estado:** documento operacional de produção — subordinado às Fontes canônicas e à Bíblia Visual de Personagens v2.0

> A v1.3 substitui a v1.2. Preserva integralmente a distribuição fenotípica, poses e fundos aprovados e fecha **arma-assinatura de Classe obrigatória para as 60 Aparências padrão**: Sentinela com escudo + arma, Errante com par de lâminas curtas, Vigia com arco/besta, Tecelão com arma-foco de Trama, Oráculo com arma-foco simbólica/oracular e Luminar com cajado/bastão de combate-foco. A decisão é visual/editorial e não cria equipamento mecânico.

> **A v2.0 substitui a v1.3 para toda produção/refação de personagem.** Preserva IDs, Classes, armas, poses e fundos, mas substitui as âncoras raciais anteriores pela anatomia v2.0. Assets antigos devem ser tratados como escala/composição, não como anatomia racial autoritativa.

---

# 1. FUNÇÃO E ESCOPO DO LOTE

Esta Matriz controla dois conjuntos relacionados:

- **10 âncoras de seleção racial:** 5 Raças × 2 apresentações;
- **60 âncoras Raça × Classe:** 5 Raças × 6 Classes × 2 apresentações.

As 60 âncoras Raça × Classe podem originar mais de uma Aparência. Para a frente inicial:

- Aparência padrão: 60 imagens;
- Errante das Cinzas: 60 imagens;
- seleção racial: 10 imagens;
- total planejado: **130 imagens**.

Asterion permite qualquer gênero em seu cânone; masculino/feminino são apenas as duas apresentações do lote visual inicial.

Os 10 representantes raciais são **âncoras de leitura**, não “o rosto oficial” de toda a Raça.

---

# 2. REGRA DE CONTINUIDADE ENTRE APARÊNCIAS

Quando a Aparência padrão e `Errante das Cinzas` representarem a mesma âncora Raça × Classe, preservar:

- rosto e estrutura facial;
- tom/subtom de pele;
- idade aparente;
- textura e cor principal do cabelo;
- constituição corporal;
- leitura racial;
- gênero/apresentação;
- sinais individuais importantes.

Pode variar entre Aparências:

- roupa/armadura aparente;
- reparos;
- acessórios;
- grau de fuligem/cinza;
- acabamento;
- estado de pose;
- estado visível da arma/foco, desde que não gere leitura mecânica enganosa.

---

# 3. IDENTIDADE DE “ERRANTE DAS CINZAS” PARA PRODUÇÃO

A Fonte Regional define `Errante das Cinzas` como Aparência conquistada pelo Feito **Entre Aquilo que Caça**. Para produção:

- vestuário de estrada funcional e muito usado;
- cinza e fuligem físicas;
- couro ressecado;
- metal fosco e reparado;
- tecido seco e desbotado;
- proteção adaptada à Classe;
- nenhuma transformação corporal pela Região;
- nenhum poder de cinzas inventado.

Adaptação de Classe:

- **Sentinela:** casaco/armadura de estrada reforçada, placas parciais, base firme; escudo opcional.
- **Errante:** camadas mais leves, manto/casaco dividido, bainhas e cintas funcionais, pernas livres.
- **Vigia:** proteção leve/média, capa curta controlável, aljava/sistema de munição quando aplicável.
- **Tecelão:** camadas que permitam precisão, braceletes/luvas/instrumentos técnicos; sem “magia de cinzas”.
- **Oráculo:** roupa de viagem prática com placas, fios ou marcadores discretos quando usados; sem cartomante teatral.
- **Luminar:** proteção funcional e vestuário marcado pela fuligem; Luz apenas quando a Classe/pose pedir, nunca halo ou santidade.

---

# 4. NOMENCLATURA

Âncora de seleção racial:

```text
RAC-<RACA>-<M/F>
```

Arquivo:

```text
raca_<raca>_<masculino|feminino>.png
```

Âncora Raça × Classe:

```text
PV-<RACA>-<CLASSE>-<M/F>
```

Arquivos:

```text
aparencia_padrao_<raca>_<classe>_<masculino|feminino>.png
errante_das_cinzas/errante_das_cinzas_<classe>_<raca>_<masculino|feminino>.png
```

Os nomes são de produção; IDs de backend permanecem responsabilidade de Implementação.

---

# 5. MATRIZ DAS 10 ÂNCORAS DE SELEÇÃO RACIAL

| ID | Raça | Apresentação | Idade | Pele | Cabelo | Constituição | Anatomia racial obrigatória | Pose | Fundo de herança |
|---|---|---|---|---|---|---|---|---|---|
| RAC-REM-M | Remanescente | Masculina | 34–40 | negra retinta | crespo preto, curto | média funcional | anatomia humana; nenhum apêndice racial; rosto individual forte | Contemplação | reconstrução em camadas |
| RAC-REM-F | Remanescente | Feminina | 38–45 | castanha média quente | ondulado/cacheado castanho-escuro | média funcional | anatomia humana; nenhum apêndice racial; pessoa claramente distinta do masculino | Deslocamento leve | reconstrução/oficina civil |
| RAC-VEL-M | Velado | Masculina | 29–35 | clara fria | liso preto, médio preso | baixo longilíneo | 1,58–1,64 m visual; orelhas largas laterais recuadas; olhos 10–15% maiores; dedos longos | Repouso controlado | limiar de pedra fria |
| RAC-VEL-F | Velado | Feminina | 42–49 | oliva muito clara fria | liso prateado-branco | baixa esguia | 1,52–1,60 m visual; orelhas largas laterais; olhos maiores; queixo estreito | Contemplação | umbrais frios quase alinhados |
| RAC-CIN-M | Cinéreo | Masculina | 46–54 | castanha média terrosa | ondulado preto, curto e espesso | baixo-médio muito denso | 1,64–1,72 m visual; mãos grandes; mandíbula/pescoço fortes; caninos inferiores curtos | Repouso firme | terreno rochoso e sustentação |
| RAC-CIN-F | Cinéreo | Feminina | 30–38 | negra retinta quente | crespo preto, curto e denso | compacta robusta | 1,58–1,66 m visual; mãos grandes; estrutura óssea forte; caninos inferiores curtos | Vigilância cotidiana | ponte curta pesada |
| RAC-HEM-M | Hemário | Masculina | 30–37 | clara quente/rubra | ondulado auburn escuro | atlético tenso | par de chifres médios varridos para trás; assinatura vascular viva; sem cauda/asas | Repouso tenso | pátio Hemaris envelhecido |
| RAC-HEM-F | Hemário | Feminina | 33–40 | castanha escura cobre | cacheado preto-auburn | atlética funcional | par de chifres curvos controlados; base integrada ao crânio; zonas de circulação vivas | Deslocamento controlado | corredor logístico envelhecido |
| RAC-ALV-M | Alvorano | Masculina | 31–38 | bronzeada dourada | liso preto, médio preso | alto ágil | 1,86–1,96 m visual; orelhas longas pontiagudas para cima/trás; membros discretamente alongados | Vigilância | terraço civil pré-Ruptura |
| RAC-ALV-F | Alvorano | Feminina | 34–41 | oliva dourada clara | ondulado castanho-cobre | alta coordenada | 1,78–1,88 m visual; orelhas longas pontiagudas; corpo alto e pronto para deslocamento | Deslocamento leve | posto civil ao amanhecer |

### Regra de aprovação das 10 âncoras

- o jogador deve distinguir as cinco Raças sem ler o nome;
- Velado e Remanescente não podem parecer apenas variações de roupa da mesma população;
- a anatomia diagnóstica deve ser reconhecível em silhueta: Velado (porte menor + orelhas largas/olhos maiores), Cinéreo (massa compacta + caninos curtos), Hemário (par de chifres), Alvorano (porte alto + orelhas longas), Remanescente (anatomia humana sem apêndice obrigatório);
- fundos devem ser diferentes entre as cinco Raças e subordinados ao personagem;
- apresentações M/F da mesma Raça compartilham a família histórica do fundo, mas não o mesmo enquadramento exato.

---

# 5.1 CONTROLE ANTI-GENÉRICO DE CLASSE

Para as 60 skins Raça × Classe:

- **toda Aparência padrão deve mostrar a arma-assinatura da Classe**;
- a arma-assinatura não pode ser substituída por mapa, placa, fio, sino, ferramenta civil ou efeito visual;
- `mãos livres`, Repouso e Contemplação apenas mudam o estado/posição do armamento;
- a escolha visual não cria regra mecânica de equipamento;
- dentro de uma mesma Raça, não reciclar o mesmo conjunto de túnica + lenço/capa + braçadeiras nas seis Classes;
- Sentinela, Errante, Vigia, Tecelão, Oráculo e Luminar devem possuir arquitetura de torso, distribuição de equipamento e família de armamento diferentes;
- não repetir castelo monumental, aqueduto, bandeiras ou skyline épico como fundo-padrão de várias Classes.

## 5.2 ASSINATURA DE ARMAMENTO POR CLASSE

| Classe | Regra obrigatória de leitura |
|---|---|
| Sentinela | arma de uma mão + escudo visível |
| Errante | duas armas curtas visíveis; preferir uma em cada mão quando a pose permitir |
| Vigia | arco ou besta sempre como arma principal visível |
| Tecelão | arma-foco de Trama visível e tecnicamente distinta de arma comum |
| Oráculo | arma-foco oracular/simbólica visível; foco ritual não pode parecer ferramenta civil comum |
| Luminar | cajado/bastão de combate-foco visível como assinatura principal |

## 5.3 ARMAMENTO VISÍVEL OBRIGATÓRIO — 60 APARÊNCIAS PADRÃO

Esta tabela complementa a coluna `Aparência padrão`. Em conflito de estado, preservar a pose e reposicionar o armamento sem apagar a assinatura da Classe.

| ID | Arma-assinatura obrigatória |
|---|---|
| PV-REM-SEN-M | espada de uma mão + escudo médio visível |
| PV-REM-SEN-F | maça curta + escudo médio visível |
| PV-REM-ERR-M | espada curta + adaga, preferencialmente uma em cada mão |
| PV-REM-ERR-F | duas adagas/lâminas curtas, uma em cada mão |
| PV-REM-VIG-M | arco longo nas costas + faca de campo secundária |
| PV-REM-VIG-F | arco recurvo abaixado + adaga secundária |
| PV-REM-TEC-M | bastão-foco curto de Trama + bracelete técnico |
| PV-REM-TEC-F | lâmina-foco de Trama + faca técnica secundária |
| PV-REM-ORA-M | cetro/bastão oracular curto + lâmina simbólica embainhada |
| PV-REM-ORA-F | lâmina simbólica ritual + bastão/cetro oracular preso |
| PV-REM-LUM-M | cajado de combate-foco médio, sem Luz ativa |
| PV-REM-LUM-F | cajado de combate-foco curto apoiado, sem brilho |
| PV-VEL-SEN-M | martelo de uma mão + escudo estreito |
| PV-VEL-SEN-F | espada reta + escudo leve |
| PV-VEL-ERR-M | duas lâminas curtas estreitas, uma em cada mão quando possível |
| PV-VEL-ERR-F | espada curta + adaga off-hand |
| PV-VEL-VIG-M | besta leve + adaga secundária |
| PV-VEL-VIG-F | arco longo + faca longa secundária |
| PV-VEL-TEC-M | cetro técnico de Trama + lâmina-foco secundária |
| PV-VEL-TEC-F | agulha/fuso de Trama de combate + bracelete técnico |
| PV-VEL-ORA-M | cajado oracular esguio + lâmina simbólica curta |
| PV-VEL-ORA-F | duas lâminas simbólicas + cetro oracular curto |
| PV-VEL-LUM-M | cajado de combate-foco médio |
| PV-VEL-LUM-F | bastão de combate-foco + Luz localizada mínima quando permitido |
| PV-CIN-SEN-M | machado curto + escudo robusto |
| PV-CIN-SEN-F | maça + escudo robusto |
| PV-CIN-ERR-M | duas facas longas/lâminas curtas de dorso largo |
| PV-CIN-ERR-F | espada curta + adaga curta |
| PV-CIN-VIG-M | arco robusto + faca de campo |
| PV-CIN-VIG-F | arco recurvo robusto + lâmina curta secundária |
| PV-CIN-TEC-M | haste segmentada de Trama + lâmina-foco curta |
| PV-CIN-TEC-F | lâmina-foco robusta + bracelete de tensão |
| PV-CIN-ORA-M | bastão oracular marcado + faca/lâmina simbólica |
| PV-CIN-ORA-F | lâmina simbólica curta + cetro oracular preso |
| PV-CIN-LUM-M | cajado de combate-foco curto e robusto |
| PV-CIN-LUM-F | cajado de combate-foco médio + Luz localizada quando permitida |
| PV-HEM-SEN-M | espada de uma mão + escudo médio |
| PV-HEM-SEN-F | lança curta de uma mão + escudo pequeno |
| PV-HEM-ERR-M | sabre curto + adaga off-hand |
| PV-HEM-ERR-F | duas lâminas curtas rápidas, uma em cada mão |
| PV-HEM-VIG-M | besta compacta + espada curta secundária |
| PV-HEM-VIG-F | arco longo + faca de campo |
| PV-HEM-TEC-M | lâmina-foco estreita + placa de inscrição técnica |
| PV-HEM-TEC-F | bastão-foco curto de Trama + lâmina secundária |
| PV-HEM-ORA-M | cetro oracular + lâmina simbólica curta |
| PV-HEM-ORA-F | lâmina simbólica baixa + bastão oracular curto |
| PV-HEM-LUM-M | cajado de combate-foco + escudo pequeno opcional secundário |
| PV-HEM-LUM-F | cajado/bastão de combate-foco baixo |
| PV-ALV-SEN-M | martelo curto + escudo pequeno |
| PV-ALV-SEN-F | espada reta + escudo leve |
| PV-ALV-ERR-M | espada curta + adaga utilitária, duas mãos armadas quando possível |
| PV-ALV-ERR-F | duas lâminas leves/curtas, uma em cada mão |
| PV-ALV-VIG-M | arco recurvo + lâmina curta secundária |
| PV-ALV-VIG-F | arco longo + espada curta secundária |
| PV-ALV-TEC-M | cetro técnico de Trama/agulha de tensão + braceletes |
| PV-ALV-TEC-F | lâmina-foco de Trama em uso |
| PV-ALV-ORA-M | bastão/cetro oracular + lâmina simbólica curta |
| PV-ALV-ORA-F | lâmina simbólica + cetro oracular curto |
| PV-ALV-LUM-M | cajado de combate-foco em guarda |
| PV-ALV-LUM-F | cajado de combate-foco + Barreira curta quando permitida |

---

# 6. MATRIZ DAS 60 ÂNCORAS RAÇA × CLASSE

## Remanescente

**Regra anatômica para todas as linhas Remanescentes:** anatomia humana individual; não adicionar chifres, orelhas raciais alongadas ou caninos/tusks como marcador de Raça.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-REM-SEN-M | Sentinela | Masculina | 24–29 | negra retinta | crespo curto preto | atlético leve | **Vigilância** — espada de uma mão baixa + escudo médio no braço | **Deslocamento** — espada baixa; casaco cinéreo reforçado |
| PV-REM-SEN-F | Sentinela | Feminina | 31–37 | castanha média quente | cacheado castanho-escuro, médio | robusta funcional | **Repouso** — maça apoiada + escudo médio visível | **Vigilância** — escudo apoiado e maça na mão |
| PV-REM-ERR-M | Errante | Masculina | 40–48 | oliva média | ondulado preto, curto | compacta | **Deslocamento** — espada curta + adaga, uma em cada mão | **Vigilância** — espada leve baixa sob manto dividido |
| PV-REM-ERR-F | Errante | Feminina | 27–34 | castanha clara quente | cacheado castanho, curto | esguia | **Vigilância** — duas lâminas curtas, uma em cada mão | **Deslocamento** — lâmina guardada, passos pela cinza |
| PV-REM-VIG-M | Vigia | Masculina | 50–58 | castanho-escura | crespo grisalho, curto | robusta | **Contemplação** — arco nas costas; mãos livres; faca de campo visível | **Vigilância** — arco abaixado; cinza no manto curto |
| PV-REM-VIG-F | Vigia | Feminina | 22–28 | oliva clara quente | ondulado castanho-escuro, curto | longilínea | **Vigilância** — arco abaixado; adaga secundária visível | **Contemplação** — arco nas costas olhando horizonte |
| PV-REM-TEC-M | Tecelão | Masculina | 35–42 | castanha média | tranças curtas escuras | atlética | **Contemplação** — bastão-foco curto de Trama na mão; outra mão examina relação espacial | **Vigilância** — braceletes cobertos de fuligem; sem efeito |
| PV-REM-TEC-F | Tecelão | Feminina | 29–36 | negra | crespo volumoso preso | alta e forte | **Vigilância** — lâmina-foco baixa e bracelete técnico | **Contemplação** — examinando pedra rachada com lâmina-foco baixa |
| PV-REM-ORA-M | Oráculo | Masculina | 44–52 | oliva média | ondulado grisalho, médio | média | **Contemplação** — cetro oracular curto + placa marcada; lâmina simbólica visível | **Vigilância** — placa marcada baixa; cinza passando ao fundo |
| PV-REM-ORA-F | Oráculo | Feminina | 25–31 | castanha escura | cacheado curto preto | compacta e ágil | **Vigilância** — lâmina simbólica curta + fio de marcadores; cetro preso | **Contemplação** — pequenos marcadores nas mãos, sem brilho |
| PV-REM-LUM-M | Luminar | Masculina | 33–40 | castanha clara quente | ondulado preto, curto | média | **Repouso** — cajado de combate-foco apoiado; sem Luz ativa | **Vigilância** — espada baixa; traço de calor contido na mão |
| PV-REM-LUM-F | Luminar | Feminina | 47–55 | negra retinta | tranças longas presas | robusta e estável | **Contemplação** — cajado de combate-foco curto; sem brilho | **Repouso** — arma guardada; tecido cinéreo sem Luz ativa |

## Velado

**Regra anatômica para todas as linhas Veladas:** porte baixo/esguio, orelhas largas varridas lateralmente para trás, olhos discretamente maiores e dedos relativamente longos. Capuzes/elmos acomodam as orelhas.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-VEL-SEN-M | Sentinela | Masculina | 28–35 | clara fria | liso preto, médio e preso | longilíneo | **Contemplação** — martelo de uma mão guardado + escudo estreito visível; mãos livres | **Preparação** — arma sendo erguida, placas cobertas de cinza |
| PV-VEL-SEN-F | Sentinela | Feminina | 36–44 | pálida fria | liso prateado, médio | baixa e esguia | **Preparação** — espada reta sendo sacada + escudo leve | **Repouso** — espada embainhada, ombro contra ruína |
| PV-VEL-ERR-M | Errante | Masculina | 23–30 | oliva clara fria | liso castanho-acinzentado, médio | esguio | **Repouso** — duas lâminas curtas visíveis, uma baixa e outra guardada | **Preparação** — mão no cabo, casaco de estrada aberto |
| PV-VEL-ERR-F | Errante | Feminina | 41–49 | clara fria | liso grisalho-escuro, curto | baixa/média e alongada | **Ação controlada** — passo lateral com espada curta + adaga off-hand | **Contemplação** — observando pegadas com arma embainhada |
| PV-VEL-VIG-M | Vigia | Masculina | 31–38 | pálida rosada fria | ondulado preto, preso baixo | baixo longilíneo atlético | **Deslocamento** — besta carregada baixa + adaga secundária | **Preparação** — retirando flecha, sem tensão |
| PV-VEL-VIG-F | Vigia | Feminina | 52–60 | oliva muito clara fria | liso branco-prateado, curto | baixa/média e contida | **Preparação** — retirando flecha; arco visível + faca longa | **Deslocamento** — besta baixa entre ruínas |
| PV-VEL-TEC-M | Tecelão | Masculina | 26–33 | clara fria | liso preto, longo preso | esguia | **Repouso** — cetro técnico de Trama apoiado + lâmina-foco secundária | **Preparação** — linhas curtas de Trama entre dedos |
| PV-VEL-TEC-F | Tecelão | Feminina | 34–42 | pálida fria | ondulado prateado, curto | média | **Preparação** — agulha/fuso de Trama + bracelete técnico | **Repouso** — bastão curto apoiado, tecido seco e desbotado |
| PV-VEL-ORA-M | Oráculo | Masculina | 45–53 | oliva clara fria | liso preto com grisalho, curto | baixa/média e magra | **Repouso** — cajado oracular esguio apoiado + lâmina simbólica | **Preparação** — fio simples entre dedos, olhar antecipatório |
| PV-VEL-ORA-F | Oráculo | Feminina | 24–31 | clara fria | liso branco, médio preso | longilínea | **Preparação** — duas lâminas simbólicas + cetro oracular curto | **Repouso** — objetos guardados sob manto de estrada |
| PV-VEL-LUM-M | Luminar | Masculina | 38–46 | pálida rosada | liso castanho-acinzentado com grisalho | média | **Vigilância** — cajado de combate-foco baixo; postura centrada | **Preparação** — maça baixa e Luz pequena no antebraço |
| PV-VEL-LUM-F | Luminar | Feminina | 29–36 | oliva clara fria | ondulado preto, curto | esguia atlética | **Preparação** — bastão de combate-foco + Luz localizada mínima | **Contemplação** — bastão apoiado diante de limiar frio |

## Cinéreo

**Regra anatômica para todas as linhas Cinéreas:** corpo compacto/denso, mãos grandes, mandíbula forte e caninos inferiores curtos; pele nunca mineral.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-CIN-SEN-M | Sentinela | Masculina | 32–39 | castanha média terrosa | crespo curto preto e espesso | compacto e denso | **Deslocamento** — machado curto baixo + escudo robusto | **Ação controlada** — passo de interceptação; escudo opcional |
| PV-CIN-SEN-F | Sentinela | Feminina | 24–31 | castanha escura quente | cacheado escuro preso curto | robusta e estável | **Ação controlada** — guarda com maça + escudo robusto | **Contemplação** — arma baixa diante de estrutura de carga |
| PV-CIN-ERR-M | Errante | Masculina | 46–54 | negra retinta | crespo baixo, barba grisalha curta | médio-baixo e assentado | **Contemplação** — duas facas longas visíveis; uma guardada e outra baixa | **Ação controlada** — mudança lateral de linha, uma lâmina curta |
| PV-CIN-ERR-F | Errante | Feminina | 28–35 | bronzeada média | ondulado preto e espesso, curto | média e firme | **Preparação** — espada curta + adaga sendo acessadas | **Repouso** — faca utilitária à cintura, mãos livres |
| PV-CIN-VIG-M | Vigia | Masculina | 37–45 | castanho-escura | tranças curtas grossas presas | atlético denso | **Repouso** — arco robusto apoiado no ombro + faca de campo | **Ação controlada** — mira curta com arco tensionado |
| PV-CIN-VIG-F | Vigia | Feminina | 52–60 | castanha média terrosa | ondulado grisalho, curto e espesso | robusta | **Ação controlada** — arco recurvo robusto erguido + lâmina curta | **Repouso** — arco apoiado, capa castigada pelo vento |
| PV-CIN-TEC-M | Tecelão | Masculina | 23–29 | negra | crespo médio preso alto | compacta e ágil | **Deslocamento** — haste segmentada de Trama baixa + lâmina-foco curta | **Ação controlada** — tensão localizada dobrando poeira no ar |
| PV-CIN-TEC-F | Tecelão | Feminina | 41–49 | castanha clara bronzeada | cacheado castanho-escuro, curto e denso | média-baixa e estável | **Ação controlada** — lâmina-foco robusta e linhas de Trama localizadas | **Deslocamento** — instrumentos de inscrição presos ao corpo |
| PV-CIN-ORA-M | Oráculo | Masculina | 30–37 | bronzeada escura | ondulado preto, raspado lateral | médio e firme | **Deslocamento** — bastão oracular marcado + pequeno sino + lâmina simbólica | **Ação controlada** — duas trajetórias incompletas muito discretas |
| PV-CIN-ORA-F | Oráculo | Feminina | 26–33 | castanha escura | crespo curto e espesso | robusta funcional | **Ação controlada** — lâmina simbólica curta + cetro oracular; trajetória incompleta | **Deslocamento** — sino pequeno preso, sem teatralidade |
| PV-CIN-LUM-M | Luminar | Masculina | 43–51 | castanha média quente | ondulado grisalho, médio preso | compacto | **Deslocamento** — cajado de combate-foco curto; brilho ausente | **Ação controlada** — barreira curta e densa, sem símbolo religioso |
| PV-CIN-LUM-F | Luminar | Feminina | 34–41 | negra retinta | tranças grossas curtas | alta e densa | **Ação controlada** — cajado de combate-foco + Luz localizada, sem halo | **Deslocamento** — espada curta baixa; camadas estruturadas |

## Hemário

**Regra anatômica para todas as linhas Hemárias:** exatamente um par de chifres de queratina integrado ao crânio; sem cauda/asas/cascos obrigatórios.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-HEM-SEN-M | Sentinela | Masculina | 25–32 | oliva quente/rubra | liso preto, curto | atlético tenso | **Repouso** — espada de uma mão embainhada + escudo médio apoiado | **Vigilância** — escudo no braço, arma ainda baixa |
| PV-HEM-SEN-F | Sentinela | Feminina | 39–47 | negra de subtom cobre | crespo curto preto com cobre e grisalho discreto | robusta funcional | **Vigilância** — lança curta de uma mão + escudo pequeno | **Deslocamento** — lança curta carregada verticalmente |
| PV-HEM-ERR-M | Errante | Masculina | 30–37 | clara quente/rubra | ondulado ruivo-escuro, curto | médio e musculatura funcional | **Vigilância** — sabre curto + adaga off-hand, corpo em transição | **Deslocamento** — manto dividido acompanhando passo |
| PV-HEM-ERR-F | Errante | Feminina | 22–28 | castanha escura de subtom rubro | cacheado preto com reflexo auburn, médio preso | esguia atlética | **Deslocamento** — duas lâminas curtas visíveis, uma em cada mão | **Vigilância** — espada baixa e corpo angulado |
| PV-HEM-VIG-M | Vigia | Masculina | 48–56 | castanho-escura quente | raspado, barba castanho-avermelhada grisalha | compacto e vigoroso | **Vigilância** — besta compacta baixa + espada curta secundária | **Contemplação** — ajoelhado observando terreno; arco no chão ao lado |
| PV-HEM-VIG-F | Vigia | Feminina | 33–40 | clara cobre | liso castanho-avermelhado, médio | alta e forte | **Contemplação** — arco longo ao lado do corpo + faca de campo | **Preparação** — encaixando flecha |
| PV-HEM-TEC-M | Tecelão | Masculina | 27–34 | negra retinta de subtom quente | tranças curtas preto-auburn | atlética compacta | **Contemplação** — lâmina-foco estreita + placa de inscrição técnica | **Contemplação** — mão sobre marca física, sem círculo mágico |
| PV-HEM-TEC-F | Tecelão | Feminina | 42–50 | oliva quente | ondulado auburn com grisalho | média e tensa | **Preparação** — bastão-foco curto de Trama + lâmina secundária | **Vigilância** — foco baixo e olhar técnico |
| PV-HEM-ORA-M | Oráculo | Masculina | 35–43 | castanha média cobre | cacheado castanho-escuro/auburn preso | robusto ágil | **Contemplação** — cetro oracular + lâmina simbólica curta; estojo fechado | **Contemplação** — observando estrutura distante, mãos livres |
| PV-HEM-ORA-F | Oráculo | Feminina | 23–30 | clara rosada quente | cacheado cobre-escuro, curto | esguia e vigorosa | **Vigilância** — lâmina simbólica baixa + bastão oracular curto | **Vigilância** — lâmina simbólica baixa, sem aura |
| PV-HEM-LUM-M | Luminar | Masculina | 51–59 | negra de subtom rubro | crespo preto-grisalho baixo | alto e forte | **Repouso** — cajado de combate-foco apoiado + escudo pequeno secundário | **Vigilância** — escudo pequeno no braço, sem halo |
| PV-HEM-LUM-F | Luminar | Feminina | 31–38 | castanha clara quente | liso preto com reflexo castanho-avermelhado, longo preso | atlética | **Vigilância** — cajado/bastão de combate-foco baixo; tórax centrado | **Preparação** — mão aberta com brilho neutro localizado |

## Alvorano

**Regra anatômica para todas as linhas Alvoranas:** porte médio-alto/alto, orelhas longas pontiagudas orientadas para cima/trás e coordenação corporal evidente; sem halo/asas.



| ID | Classe | Apresentação | Idade | Pele | Cabelo | Constituição | Aparência padrão | Errante das Cinzas |
|---|---|---|---|---|---|---|---|---|
| PV-ALV-SEN-M | Sentinela | Masculina | 23–30 | bronzeada dourada | liso preto, curto | atlético e leve | **Deslocamento** — martelo curto baixo + escudo pequeno no braço | **Repouso** — arma apoiada, manto curto chamuscado |
| PV-ALV-SEN-F | Sentinela | Feminina | 34–41 | oliva dourada clara | ondulado castanho-cobre, curto | média e móvel | **Preparação** — espada reta em guarda + escudo leve | **Ação controlada** — guarda firme sem efeito sobrenatural |
| PV-ALV-ERR-M | Errante | Masculina | 45–53 | oliva média dourada | liso castanho-escuro com grisalho, curto | alto e coordenado | **Preparação** — espada curta + adaga, duas mãos armadas | **Contemplação** — ajoelhado examinando terreno, arma guardada |
| PV-ALV-ERR-F | Errante | Feminina | 27–34 | bronzeada média | liso/ondulado preto preso curto | compacta e ágil | **Repouso** — duas lâminas leves/curtas visíveis, uma apoiada e outra guardada | **Preparação** — lâmina sendo sacada sem pose de assassino |
| PV-ALV-VIG-M | Vigia | Masculina | 31–38 | oliva clara dourada | ondulado castanho, médio | esguio atlético | **Preparação** — encaixando flecha; arco recurvo + lâmina curta secundária | **Vigilância** — besta apoiada no ombro |
| PV-ALV-VIG-F | Vigia | Feminina | 50–58 | bronzeada escura | liso preto com grisalho, curto | robusta móvel | **Ação controlada** — mira com arco longo tensionado + espada curta secundária | **Deslocamento** — arco baixo e passo cuidadoso |
| PV-ALV-TEC-M | Tecelão | Masculina | 25–32 | castanha média dourada | liso castanho-escuro, médio preso | alta e ágil | **Vigilância** — cetro técnico/agulha de Trama + luvas técnicas | **Preparação** — placa marcada e linha tensionada discreta |
| PV-ALV-TEC-F | Tecelão | Feminina | 38–46 | oliva clara | ondulado preto-cobre, curto | média e pronta | **Ação controlada** — lâmina-foco resolvendo tensão localizada | **Ação controlada** — resolução de Trama curta, sem aura ampla |
| PV-ALV-ORA-M | Oráculo | Masculina | 29–36 | bronzeada média | liso castanho-escuro, médio preso | atlético | **Preparação** — bastão/cetro oracular + fio de marcação + lâmina simbólica | **Preparação** — marcadores sobre placa simples |
| PV-ALV-ORA-F | Oráculo | Feminina | 42–50 | oliva dourada clara | ondulado cobre-escuro, curto | compacta e coordenada | **Ação controlada** — lâmina simbólica + cetro curto; duplicação breve de gesto | **Ação controlada** — gesto duplicado sutil, sem fumaça moralizada |
| PV-ALV-LUM-M | Luminar | Masculina | 33–40 | castanha bronzeada | liso preto, curto e preso | alto e leve | **Preparação** — cajado de combate-foco em guarda; Luz apenas localizada | **Repouso** — foco guardado, respiração centrada |
| PV-ALV-LUM-F | Luminar | Feminina | 24–31 | oliva clara dourada | ondulado castanho-cobre, longo preso | esguia atlética | **Ação controlada** — cajado de combate-foco + barreira curta translúcida | **Ação controlada** — Luz concentrada em projeção curta |

---

# 7. REGRA DE DISTRIBUIÇÃO FENOTÍPICA

A regra de distribuição consolidada na v1.1 substituiu a regra antiga de distribuição uniforme entre todas as Raças.

Agora:

- cada Raça possui um **centro fenotípico reconhecível** definido pela Bíblia Visual v1.4;
- a diversidade acontece primeiro **dentro da faixa racial**;
- descendência mista permite exceções deliberadas, mas a exceção deve ser uma decisão de personagem, não aleatoriedade do gerador;
- não usar a mesma combinação de pele, cabelo, rosto e corpo como default para múltiplas Raças;
- representação negra permanece distribuída de modo forte entre Remanescentes, Cinéreos e Hemários, além de poder aparecer em indivíduos de outras linhagens por família mista;
- Velados de seleção usam contraste frio e cabelo preto/prateado/branco para legibilidade;
- Alvoranos usam centro oliva/dourado/bronze humano sem estética angelical;
- nenhum marcador racial autoriza estereótipo moral ou cultural.

---

# 8. ESTADOS DE POSE — CONTROLE DO LOTE

Antes de gerar o lote final, verificar a distribuição global dos sete estados:

- Repouso;
- Contemplação;
- Vigilância;
- Deslocamento;
- Preparação;
- Ação controlada;
- Ação intensa.

Objetivo editorial: não permitir que Preparação + Ação dominem visualmente o catálogo.

---

# 9. FUNDOS DE HERANÇA DAS 5 RAÇAS

| Raça | Motivo de fundo | O que comunica | Proibido |
|---|---|---|---|
| Remanescente | reconstrução em camadas, via/ponte/oficina reaproveitada | persistência, mistura histórica, adaptação | miséria caricata, ruína vazia, cenário genérico idêntico aos outros |
| Velado | limiar frio, arcos/umbrais repetidos, névoa fina | sensibilidade liminar e percepção | Avesso, portal, void purple, cemitério gótico |
| Cinéreo | terreno severo, sustentação, contrapesos, vento | populações moldadas por carga e condições duras | lava, magma, pele/arquitetura “racialmente de pedra” |
| Hemário | pátio clínico/logístico Hemaris envelhecido | origem histórica no Projeto Hemaris | gore, experimento gráfico, laboratório sci-fi, Matriz Rubra explícita |
| Alvorano | terraço/rota civil pré-Ruptura, horizonte e marcadores | linhagem natural anterior à Ruptura, prontidão | templo solar, halo, arquitetura celestial |

Esses fundos são vinhetas de herança e **não criam novos Locais de Mapa**.

---

# 10. MATRIZ DOS 30 FUNDOS RAÇA × CLASSE

A mesma combinação serve como família para as apresentações masculina e feminina; variar câmera, lado do ponto focal, horário e detalhe secundário para não duplicar exatamente a composição.

| Raça | Classe | Fundo-base |
|---|---|---|
| Remanescente | Sentinela | portão reconstruído com pedra de épocas diferentes e madeira nova; área de guarda comunitária |
| Remanescente | Errante | bifurcação entre rua antiga e passarela reparada, com várias rotas improvisadas |
| Remanescente | Vigia | torre/andaime reconstruído sobre ruína baixa, oferecendo linha de visão sobre assentamento vivo |
| Remanescente | Tecelão | oficina de reparo instalada sobre juntas antigas de pedra, medições físicas e peças reaproveitadas |
| Remanescente | Oráculo | encruzilhada de rotas remendadas com placas de direção de épocas diferentes, sem profecia explícita |
| Remanescente | Luminar | posto comunitário de recuperação junto a abrigo reconstruído e braseiro funcional discreto |
| Velado | Sentinela | umbral frio e estreito entre arcos quase alinhados, transformado em passagem defensiva |
| Velado | Errante | sequência de corredores/escadas liminares com duas saídas visualmente próximas e névoa fina |
| Velado | Vigia | mirante de pedra pálida com arcos repetidos e horizonte parcialmente oculto por névoa |
| Velado | Tecelão | galeria fria de juntas geométricas e placas técnicas antigas, linhas físicas quase coincidentes |
| Velado | Oráculo | cruzamento de três umbrais semelhantes com marcadores discretos; caminhos possíveis sem destino afirmado |
| Velado | Luminar | abrigo liminar de pedra clara com foco de calor funcional e sombras suaves, sem templo ou aura |
| Cinéreo | Sentinela | passagem entre muros de contenção e blocos pesados, feita para receber carga e impacto |
| Cinéreo | Errante | trilha estreita entre rocha e contrapesos, com vento lateral e apoios firmes |
| Cinéreo | Vigia | mirante de pedra robusta acima de terreno severo, marcos de distância presos contra vento |
| Cinéreo | Tecelão | estação de manutenção de contrapesos e juntas estruturais, pedra/metal sob tensão física |
| Cinéreo | Oráculo | entroncamento de passagens pesadas marcado por pilares, correntes e orientação redundante |
| Cinéreo | Luminar | posto de recuperação protegido do vento por paredes baixas e lã/couro, calor funcional discreto |
| Hemário | Sentinela | portão interno de antiga instalação Hemaris, placas de proteção e corredor clínico-logístico gasto |
| Hemário | Errante | passagem de serviço entre alas antigas, tubos/canais cobertos e rotas de manutenção laterais |
| Hemário | Vigia | plataforma logística elevada sobre pátio médico antigo, visão longa e ferrugem controlada |
| Hemário | Tecelão | sala de manutenção analógica com placas, escalas e juntas de infraestrutura Hemaris, sem sci-fi |
| Hemário | Oráculo | cruzamento de corredores clínicos com sinalização apagada e múltiplas rotas possíveis |
| Hemário | Luminar | posto de triagem/recuperação antigo, leitos vazios ou bancos funcionais sem gore, luz quente pequena |
| Alvorano | Sentinela | posto civil pré-Ruptura de controle de passagem, linhas limpas e horizonte aberto |
| Alvorano | Errante | terraço de rota com duas rampas e marcadores baixos, sugerindo decisão rápida de deslocamento |
| Alvorano | Vigia | plataforma de orientação com horizonte amplo, marcos de distância e instrumentos analógicos simples |
| Alvorano | Tecelão | pátio técnico pré-Ruptura com placas de medição, juntas e organização metódica, sem brilho |
| Alvorano | Oráculo | cruzamento civil de rotas com marcadores duplicados e caminhos divergentes sob luz clara |
| Alvorano | Luminar | pátio de apoio e recuperação pré-Ruptura com foco de calor funcional e equipamentos organizados, sem templo |

### Regra de composição

Cada fundo Raça × Classe deve conter:

1. **motivo histórico racial** reconhecível;
2. **função espacial da Classe**;
3. quando a Aparência for regional, **materiais da Região** como terceira camada.

Exemplo: um **Velado Vigia em Errante das Cinzas** mantém um mirante/limiar frio de leitura Velada, recebe linha longa de visão de Vigia e ganha cinza/couro seco/metal fosco das Terras do Ocaso. Não vira simplesmente “o mesmo fundo de ruínas do Ocaso” usado por todos.

---

# 11. FUNDO DO LOTE TERRAS DO OCASO

Para as Aparências produzidas durante a frente de Terras do Ocaso:

- formato 1:1;
- corpo inteiro;
- personagem centralizado;
- fundo contextual discreto, nunca batalha completa;
- materiais regionais de cinza/pedra podem ser adicionados como terceira camada;
- luz fria/desaturada quando coerente;
- nenhum spoiler de Âncora, Avesso ou revelação posterior;
- **não apagar o fundo de herança racial nem o motivo funcional de Classe com uma ruína genérica igual para todo o catálogo**;
- diferença entre Aparência padrão e Errante das Cinzas vem principalmente do personagem/material regional, preservando a família espacial da combinação quando útil.

---

# 12. CONTROLE DE STATUS

| Campo | Valores recomendados |
|---|---|
| Status | Não iniciado / Gerado / Revisar / Regenerar / Aprovado |
| Anatomia | OK / Falha |
| Fenótipo racial | OK / Fraco / Falha |
| Classe | OK / Falha |
| Fundo racial | OK / Genérico / Falha |
| Fundo de Classe | OK / Fraco / Falha |
| Pose | OK / Repetitiva / Falha |
| Arma/foco | OK / Corrigir / Falha |
| Pixel art | OK / Lisa demais / Ruído |
| Spoiler | OK / Falha |
| Arquivo final | caminho/nome |

Não considerar “bonita” uma imagem equivalente a “aprovada”. Se a Raça não for distinguível em leitura rápida, o asset deve ser regenerado mesmo que anatomia e atmosfera estejam boas.

---

# 13. MIGRAÇÃO DA v1.0

Os assets raciais e prompts produzidos com a v1.0 antes deste fechamento devem ser revisados. Em especial:

- `raca_remanescente_masculino.png`;
- `raca_remanescente_feminino.png`;
- `raca_velado_masculino.png`;
- `raca_velado_feminino.png`;
- qualquer prompt Raça × Classe que use a distribuição antiga “qualquer tom/cabelo em qualquer Raça” como regra principal;
- qualquer skin que use o mesmo fundo genérico de ruínas para todas as Raças.

Esses assets não são automaticamente inválidos como ilustração, mas **não devem ser aprovados como âncoras oficiais de identificação racial** se a linhagem não estiver legível sem o nome.

---

# 14. FECHAMENTO

A Matriz v1.3 existe para impedir três problemas:

1. aleatoriedade sem direção;
2. padronização excessiva dentro de uma Raça;
3. intercambialidade visual entre Raças diferentes.

Frase-guia:

> **Diversidade é planejada dentro de famílias reconhecíveis; identidade racial precisa sobreviver ao figurino, à Classe e ao fundo.**
