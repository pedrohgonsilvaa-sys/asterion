# ASTERION — Especificação Final do Núcleo MMO/PvPvE

**Versão:** 1.0 · 2026-10-08
**Estado:** decisões registradas na auditoria de 2026-10-08 e incorporadas à Fonte Mestra v1.5.0 naquela revisão; a autoridade normativa atual é a Fonte Mestra v1.6.0, e esta especificação técnica permanece subordinada a ela para regras globais.
**Escopo:** Grupo persistente, progressão cooperativa, Caçada em Grupo, PvPvE, Ronda, Desbravar, navegação, telemetria e roadmap de Crônicas.

> Esta especificação registra o escopo e os critérios de implementação aprovados. A autoridade normativa vigente é a Fonte Mestra v1.6.0; a matriz abaixo é um snapshot de auditoria de 2026-10-08 e não redefine regras de produto.

## 1. Princípios

1. A Campanha deve ser concluível Solo por qualquer build legal.
2. Cooperação é opcional e comporta até quatro personagens, salvo exceção explícita de conteúdo.
3. Progresso, gates, escolhas, conhecimento e recompensas da Campanha pertencem a cada personagem. Grupo compartilha atividade, não save narrativo.
4. Cada atividade tem roster próprio; Grupo social e roster do encontro são conceitos distintos.
5. Nível, Equipamento e poder permanecem reais; não há sincronização de veterano nesta baseline.
6. Settlement é individual, conforme fonte, contribuição, elegibilidade e idempotência.
7. PvP não paga diretamente; Domínio do Rastro só é liquidado após vitória econômica na presa PvE subsequente.
8. Baseline Beta deve gerar telemetria de escala, duração, participação, reconnect, mortes e resultados.

## 2. Grupo persistente

### 2.1 Grupo e roster

- Grupo tem até 4 personagens, persiste após Missão/Caçada/Masmorra e não exige co-localização.
- Cada atividade reúne membros online, elegíveis e participantes. Grupo 4/4 pode iniciar com 2–3 participantes.
- Roster congela quando atividade/encontro/run começa. Novo membro participa apenas de atividade posterior.
- Elegibilidade é revalidada por personagem antes do custo, lockout e criação da atividade.
- Convite expira em 10 minutos. Expulsão só fora de Foreground compartilhado.
- Sair do Grupo não encerra atividade nem é fuga; abandono segue regra própria da atividade.
- Offline não dissolve Grupo nem transfere liderança. Saída explícita do Líder transfere liderança social ao membro restante ativo mais antigo.
- Membros podem propor atividade mesmo com Líder offline.

### 2.2 Papéis e Jornada

| Papel | Responsabilidade | Limite |
| --- | --- | --- |
| Líder Social | Administração do Grupo | Não controla progresso ou loot alheio |
| Personagem de Referência | Checkpoint/objetivo executado ou ajudado | Não substitui gates pessoais |
| Host Técnico | Responsabilidade operacional da instância persistida | Não decide settlement pessoal |

Os três papéis podem ser distintos. O servidor é a autoridade da instância; disconnect do Host Técnico não descarta estado. Se a Referência sair fora de combate, membro legitimamente no mesmo checkpoint pode assumir. Sem sucessor, a Jornada ativa pausa/encerra conforme estado persistido, mas o Grupo permanece. Disconnect durante encontro usa reconnect do mesmo estado.

### 2.3 Confirmação de entrada

Atividade compartilhada com custo, lockout ou risco coletivo usa confirmação unânime de 60 segundos:

1. qualquer membro propõe;
2. contexto e roster candidato são preparados;
3. cada participante confirma;
4. elegibilidade é revalidada;
5. só então se cria a atividade econômica.

Sem unanimidade, por recusa, expiração ou inelegibilidade: retorna ao lobby, sem encounter_id econômico, Vigor, derrota ou lockout. O roster pode ser ajustado e submetido novamente. Confirmar Caçada já aceita PvPvE; não há segunda confirmação PvPvE.

## 3. Campanha cooperativa

### 3.1 Regra universal

- Prólogo pode ser Solo.
- P1 em diante, toda Principal e Secundária aceita Solo ou Grupo de 1–4, salvo exceção explícita publicada.
- O princípio vale para as 36 Principais e 36 Secundárias planejadas; cada etapa é classificada como compartilhável, pessoal ou adaptada.
- A Campanha segue individualmente. O Grupo pode conter personagens em checkpoints diferentes.

### 3.2 Crédito objetivo

Podem ser compartilhados com evidência idempotente para todos os participantes elegíveis e presentes: derrotar inimigo/Chefe, sobreviver, alcançar Local, atravessar trecho, examinar pista objetiva, encontrar objeto/estrutura, resolver puzzle compartilhável, concluir encontro roteirizado e obter descoberta objetiva diante do Grupo.

Presença e contribuição precisam corresponder à natureza do objetivo; pertencer ao Grupo não basta. Usa-se o avaliador compartilhado, sem novo threshold de DPS. Cada personagem recebe seu registro próprio.

Escolhas narrativas, decisões irreversíveis, flags incompatíveis, respostas que alteram estado, gates e escolha de recompensa permanecem pessoais. Códice e Bestiário são individuais, embora uma descoberta compartilhada legítima possa registrar conhecimento para cada elegível presente.

### 3.3 P1 e retorno ao progresso

P1 suporta investigação dos dois sinais, combate do Cão Cinéreo, chegada ao Refúgio e registro individual do Braseiro pelo Grupo. Diálogos/flags pessoais continuam individuais.

Fluxo obrigatório: A/B/C/D iniciam P1; A sai; B/C/D continuam; depois retornam para ajudar A em seu checkpoint. Ninguém regride nem recebe etapas futuras fora de ordem. Objetivo compartilhável novo registra progresso próprio para presentes elegíveis.

### 3.4 Ajudantes

Ajudante que já completou a etapa pode participar sem regressão. Recebe somente recompensa repetível que a fonte já autorizaria; se a fonte só tiver recompensa one-time, settlement econômico do ajudante é zero.

Nunca duplicar XP/Coroas únicas de Quest, material único, Equipamento escolhido, Núcleo, Receita, first-clear, flags, Feitos ou conhecimento one-time. Personagem no próprio checkpoint e com direito à primeira conclusão recebe a própria recompensa uma vez. Settlement é individual/idempotente.

### 3.5 Chefes de Campanha

Chefes aceitam 1–4; Solo conserva números canônicos. Para N, o roster ativo no spawn, congelar:

| Participantes N | HP do Chefe | ATQ do Chefe |
| ---: | ---: | ---: |
| 1 | ×1,00 | ×1,00 |
| 2 | ×1,55 | ×1,04 |
| 3 | ×2,10 | ×1,08 |
| 4 | ×2,65 | ×1,12 |

HP = HP Solo × [1 + 0,55 × (N−1)]. ATQ = ATQ Solo × [1 + 0,04 × (N−1)]. DEF e AGI não escalam. Morte, saída ou disconnect não recalculam escala. Não adicionar scaling de fase, Arte, Cura, Barreira ou adds sem necessidade explícita.

Usar materialização central de inimigos e arredondamento autoritativo, sem fórmula paralela/intermediária. S6 / Guardião do Último Rastro é Solo ou Grupo e recebe esta escala, sem alteração de ficha, identidade, stats Solo ou recompensa.

### 3.6 Poder real e viabilidade Solo

Veterano usa configuração real, sem sync/compressão. Pode carregar novato, sem ignorar gates nem duplicar reward único.

Toda build legal deve concluir Campanha Solo; não é exigido DPS ou duração iguais. Não pode existir soft-lock matemático por cura do Chefe acima do DPS mínimo legal, DPS check impossível, enrage incompatível, função ausente ou loop de Cura/Barreira. Ataque Básico e ferramentas legais da Classe devem permitir progresso. Testar builds legais defensivas/suporte e registrar duração, dano, sustain, fase e resultado. Não rebalancear nesta fase.

## 4. Caçada em Grupo

- Usa Grupo social; não existe Grupo de Caçada como entidade social separada.
- Qualquer membro propõe. Preparar Região/Local, formar roster elegível e obter confirmação unânime em 60 segundos.
- Grupo 4/4 pode iniciar com 2–3 membros ativos. Roster congelado define tamanho para scaling, contribuição e PvPvE.
- Pareamento PvPvE exige lados iguais: 1v1, 2v2, 3v3 ou 4v4.
- Caçada mantém seus pools, scaling, Vigor, contribuição e recompensas próprios; não usa escala de Chefe de Campanha.
- Custos e reward são individuais; configuração é congelada por encontro e nenhum membro entra em combate em andamento.

## 5. PvPvE e Domínio do Rastro

### 5.1 Sequência

Na fronteira segura da Caçada tenta-se pareamento antes de materializar a próxima presa. PvE já iniciado termina primeiro. Se não houver rival e a Caçada prosseguir, materializa-se presa normal. Presa já materializada/iniciada não é rerrolada.

Com colisão: PvP → vencedores sobreviventes/elegíveis continuam → presa PvE é materializada → combate PvE → settlement. No Beta, PvP e monstro não são um combate simultâneo. O encounter_id da presa é criado depois do PvP e congela nível de referência, roster sobrevivente/elegível, escala aplicável, loot seed e estado.

### 5.2 Participação e resultado

Pareamento exige mesmo Local e tamanho igual. Mantêm-se filas vigentes: até 20 min para Manual/Grupo, até 75 min para Ronda. Sair da área/entrar em atividade incompatível torna o lado inelegível. Monstro descoberto por Desbravar termina antes do PvPvE.

PvP não concede XP, Coroas, materiais, Equipamento, Runa ou pity. Vitória válida cria estado individual DOMÍNIO DO RASTRO para vencedor com contribuição válida pelo avaliador compartilhado, sobrevivente e ainda elegível. Derrotado retorna a recovery/Braseiro e não segue à presa. Empate/morte simultânea encerra oportunidade, sem Domínio e com recovery normal.

Participante que sobrevive ao PvP e depois cai no PvE ainda pode receber settlement normal e bônus se a vitória econômica do encontro e contribuição individual qualificarem.

### 5.3 Economia

A presa usa custo e recompensa normais da Caçada, inclusive Vigor por encontro. PvP custa zero Vigor. Vitória econômica PvE válida liquida para cada participante qualificado: 0,05 × C(nível de referência do loot) Coroas, arredondadas pela regra monetária global, e 1 Material Básico regional. Sem vitória econômica válida, Domínio não paga. O bônus não tem custo extra; a presa mantém seu custo normal.

O lock econômico de 30 minutos bloqueia somente a nova materialização do bônus Domínio do Rastro. Não bloqueia, reduz nem adia XP normal elegível, Coroas normais, Materiais normais, Equipamento, Runa, pity, Bestiário ou quaisquer efeitos normais da Caçada da presa. A recompensa normal da presa segue integralmente suas próprias regras de Vigor, contribuição e settlement.

O lock é simétrico por par de contas e começa quando um bônus Domínio válido é materializado envolvendo aquele par. Um rematch permitido continua sendo confronto válido e pode determinar quem segue à presa; se houver lock ativo entre contas pertinentes, a conta vencedora não recebe seu pacote Domínio (0 Coroas adicionais e 0 Material Básico adicional). No Grupo, verificar cada participante vencedor individualmente contra as contas adversárias participantes pertinentes. Uma pessoa bloqueada perde somente o próprio Domínio; isso não remove a recompensa PvE normal nem bloqueia o Domínio de outro vencedor que seja elegível. Para o pacote individual — que não é fracionado por adversário — qualquer par pertinente ainda bloqueado torna aquele vencedor inelegível ao bônus nesta resolução.

### 5.4 Cadência e anti-farm

- 3 min de cooldown geral pós-PvP por conta.
- 10 min sem novo pareamento contra os mesmos adversários/roster.
- 30 min para novo bônus Domínio envolvendo a mesma conta; lock simétrico por par de contas.
- Sem limite diário. Histórico acompanha contas participantes, não group_id; trocar membros ou Grupo não limpa histórico.
- Prioridade: adversário não recente, depois enfrentado há mais tempo, depois repetição permitida. Cooldown é hard gate.
- Padrões suspeitos entram em telemetria; sem ban automático no Beta.

### 5.5 Ronda e Assumir Combate

Ronda continua Solo e presente no PvPvE do Local. Roster 1 pareia somente com lado de tamanho 1: Manual Solo ou Ronda Solo. Preservar cadência, Vigor e automação atuais.

Vitória PvP mantém o lote, segue para presa e pode estender ETA. Derrota encerra lote; settlements anteriores ficam, encontros futuros não rodam e novo lote exige nova preparação/início. Não suspender/retomar. Empate encerra oportunidade sem Domínio e aplica recovery.

Assumir Combate: IA começa/continua; dono assume na próxima oportunidade válida sem trocar configuração. Adversário não vê se é IA ou controle manual.

## 6. Desbravar e coleta contextual

Desbravar é Solo no lançamento, mesmo com Grupo social persistente. exploration_attempt_id, RNG, descoberta, custo, Vigor, entrega, economia, Códice e Bestiário pertencem a cada personagem. Desbravar atual não compartilha rolagem, saque físico ou custo.

Não criar Mineração, Minerador, nível, ferramenta ou botão raiz de coleta. Recursos contextuais só aparecem em resultado autorizado pelo conteúdo/economia. Encontro de monstro segue integração PvPvE quando Local/pool for elegível, respeitando fronteira segura.

## 7. Navegação

- Sem entrada raiz permanente de Grupo no Menu Principal.
- Hub administrativo: **Vínculos → Grupo**.
- Atalhos [Grupo] contextuais em Missão, Caçada, Masmorra e Local apropriado.
- Dashboard compacto: “👥 Grupo · X/4”.
- Missão solo: [Seguir Objetivo] [Formar Grupo]. Já agrupado: [Seguir Objetivo] [Grupo].
- Não criar modos redundantes Solo/Grupo/Ajudar.
- Antes da confirmação, identificar elegível/ajudante/inelegível e resumir efeito em progresso/recompensa.

## 8. Crônicas

Roadmap aprovado:

1. Fechar núcleo MMO/Campanha coop/Grupo/PvPvE.
2. Implementar e fazer QA completo de TDO.
3. Concluir Vales P7–P12/S7–S12 na arquitetura cooperativa.
4. Implementar infraestrutura real de Crônica.
5. Testar scheduler, capítulos, progresso global, objetivos, voto, Trilha, filtro de spoilers e recovery em ambiente acelerado.
6. Continuar Regiões 3–6.
7. Preparar Ecos da Convergência completa.
8. Crônica I canônica começa no Dia 1.

Cânone segue 8 semanas, 8 capítulos e 7 dias por capítulo. Aceleração vale somente para relógio de engenharia/teste.

## 9. Persistência, idempotência e telemetria

Persistir Grupo/convites/liderança; roster e confirmações; referência/checkpoint/papéis; evidências de missão pessoais; encounter_id, snapshots individuais, escala congelada, reconnect e resultado; Domínio, contas/adversários/cooldowns; encadeamento PvP→presa→settlement; e chaves idempotentes individuais de objetivo/recompensa.

Telemetria Beta mínima:

- conteúdo/local, tamanho/composição/contribuição, nível e poder relativos, escala e roster inicial/final;
- duração, ações, dano, cura, barreira, mitigação, consumíveis, mortes, reconnect, abandono e resultado;
- Chefe: fase, tempo, contribuição, build defensiva/suporte;
- PvPvE: colisões, adversários/rosters, cooldowns, resultado, empate, Domínio, presa e settlement;
- Ronda: lote previsto/feito, interrupção, PvP e ETA;
- anti-farm: frequência por conta/par, sem ban automático;
- Crônicas: capítulo/objetivo/voto/Trilha/spoilers/recovery.

Telemetria não substitui ledger ou estado autoritativo e não deve conter secrets.

## 10. Matriz de auditoria — snapshot pré-sincronização

| DECISÃO | STATUS | FONTE ATUAL | ALTERAÇÃO NECESSÁRIA | IMPLEMENTAÇÃO ATUAL | GAP |
| --- | --- | --- | --- | --- | --- |
| Grupo persistente até 4, não co-localizado | APROVADO; implementação parcial | GDD v1.4.9 §§20/49.18; roadmap local | Formalizar TTL 10m, offline, kick e roster por atividade | SocialGroup até 4 existe; convite está em 15m; Caçada usa grupo completo e exige Líder | TTL, proponente livre, roster subset congelado |
| Ready check unânime 60s | APROVADO; fonte parcial | GDD §20.2 exige consentimento, não define janela | Publicar timeout/cancelamento sem custo | Sem ready check geral para Caçada/campanha | Serviço persistente/versionado e retorno ao lobby |
| Papéis Líder/Jornada/Host | APROVADO; falta formalização | GDD trata liderança, não separação universal | Definir papéis e sucessão da Referência | SharedActivity existe; papéis não estão separados universalmente | Identidades distintas e política por checkpoint |
| Campanha P1+ coop e 72 missões | APROVADO; roadmap conflita | Roadmap diz P1 Solo; GDD não expressa universalidade completa | Formalizar P1+ e exceções explícitas | P1 atual é Solo; P5/P6 e S6 têm protótipos coop | Motor geral de objetivo/progresso individual |
| Crédito compartilhável | APROVADO; regra parcial | GDD §20.2 exige presença/contribuição | Publicar categorias e idempotência por participante | Settlement parcial em fluxos de campanha | Evidência pessoal para objetivos e decisões pessoais |
| S6 Guardião coop | APROVADO; fonte regional conflita | TDO v1.0.14 diz Solo | Atualizar formato, sem mexer na ficha | Protótipo S6 tem convocação | Sincronizar fonte e aplicar scaling |
| Scaling D de Chefe de Campanha | APROVADO; ausente da fonte | GDD tem outras curvas, não esta | Publicar fórmula e congelamento | P6/S6 usam stats Solo | Materialização central, arredondamento e telemetria |
| Ajudantes e veterano real | APROVADO; parcial | GDD prevê gates, contribuição e rewards individuais | Formalizar repetível vs one-time | Poder real; progresso/reward parcial por participante/host | Aplicar regra em toda missão sem duplicação |
| Solo para builds legais | APROVADO; sem cobertura geral | GDD de combate, sem invariante global | Publicar princípio e teste de soft-lock | Sem bateria global extrema | Teste de baixo dano/sustain/sem soft-lock |
| Caçada em Grupo | APROVADO; operacional diverge | GDD §18.1/§20.2 | Ready check, qualquer membro e roster ativo | GroupHunt exige Líder, grupo inteiro e mesmo Local | Roster parcial e preparação unânime |
| PvPvE em duas etapas | APROVADO; fonte/código divergem | GDD §18.1 descreve auto-pareamento sem sequência completa | Formalizar PvP→presa, economia e Domínio | PvpService combina lados e monstro neutro | Separar PvP, presa, persistência e settlement |
| Domínio do Rastro | APROVADO; nova regra | Sem estado na Fonte/código | Publicar condição, bônus, rounding e idempotência | Não existe ledger específico | Estado pessoal e liquidação após presa |
| Ronda × PvPvE | APROVADO; código diverge | GDD §§18.1–18.2 permite parada segura | Vitória continua, derrota/empate encerram | Match interrompe/cancela lote | Encadear resultado e preservar continuação |
| Cooldown/rematch/anti-farm | APROVADO | Regras atuais são de fila ou PvP competitivo | Publicar 3m/10m/30m; 30m se aplica somente ao bônus Domínio e é simétrico por par de contas | Sem histórico específico de adversário | Registro account-pair-based, avaliação individual e telemetria |
| Desbravar Solo | APROVADO; alinhado em parte | GDD §18.1; Road usa ExplorationAttempt individual | Manter individual e conectar fila em fronteira segura | Attempt próprio por personagem | Validar sequência de combate/PvPvE |
| Navegação | APROVADO; precisa UX sync | Roadmap/UI locais antigos | Vínculos → Grupo e atalhos sem raiz nem modos redundantes | Há superfícies de Grupo, navegação não consolidada | Ajustar hub, contexto e elegibilidade |
| Roadmap de Crônicas | APROVADO | GDD fixa ciclo 8 semanas/8 capítulos/7 dias | Atualizar ordem de entrega, sem alterar cânone | Infra de Crônica não implementada | QA TDO/Vales; infra e relógio acelerado |
| Vales P7–P12/S7–S12 | APROVADO estruturalmente; implementação posterior | Vales v1.0.3 e regra global | Implementar após núcleo/TDO | Campanha Vales ausente | Seguir arquitetura coop aprovada |
| Kit numérico S12 | BLOCKER DE CONTEÚDO | Ficha numérica não está fechada | Publicar kit/stats antes do combate | S12 não implementada | Não inventar; arquitetura não bloqueada |
| Quatro falhas test_combat_ui.py | QA PENDENTE | Baseline limpa não comparada | Atribuir causa antes de merge | Quatro falhas conhecidas sem origem provada | Comparação limpa e correção se regressão |
| Isolamento Git | BLOQUEIO OPERACIONAL PRÉ-COMMIT | Worktree misturado | Inventariar e separar hunks/commits | Protótipo junto de alterações preexistentes | Isolar sem descartar trabalho |

## 11. Estado registrado na auditoria de 2026-10-08

### Decisões de produto ainda abertas

Nenhuma. As decisões player-facing do núcleo MMO/PvPvE estão encerradas e formalizadas na Fonte Mestra v1.5.0.

### Blockers observados naquele snapshot

1. **Sincronização canônica naquele momento:** GDD v1.4.9 ainda não incorporava cooperação P1+, escala de Chefe, ready check, sequência/economia PvPvE, anti-farm e Ronda×PvPvE; TDO v1.0.14 ainda descrevia S6 como Solo. Esta lacuna é fechada pelas Fontes v1.5.0/v1.0.15 que acompanham esta especificação.
2. **S12:** falta ficha numérica/kit; bloquear somente a implementação do combate S12, não a arquitetura coop.
3. **QA pré-merge:** quatro falhas conhecidas em test_combat_ui.py não têm atribuição comprovada; comparar com baseline limpa e corrigir regressões reais.
4. **Isolamento de trabalho:** worktree contém alterações preexistentes misturadas; inventariar e isolar por área antes de commits, sem descartar nada.
**Decisões de produto encerradas. Esta especificação técnica permanece subordinada à Fonte Mestra v1.6.0.**
