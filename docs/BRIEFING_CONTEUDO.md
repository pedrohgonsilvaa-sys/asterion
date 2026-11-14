# Briefing de conteúdo (2026-11-12)

O código destes sistemas está pronto e testado. Os catálogos estão vazios de propósito: nada aparece no jogo até o conteúdo ser definido. Este documento diz o que escrever e em que formato, para que a engenharia só precise copiar para o catálogo.

Regras para quem escrever:

- Lore, NPCs, nomes e limites seguem a Bíblia Canônica Consolidada v4.0.7. Sistemas e números seguem o GDD v1.6.0 §49.
- Não criar mecânica nova. Se uma ideia precisar de regra que o GDD não tem, anote como pergunta, não como conteúdo.
- Números de atributos de criatura não são escritos à mão: vêm da fórmula do GDD §49 pela categoria (Elite, Chefe) e pelo nível. O conteúdo escolhe o **perfil** (Bruto, Equilibrado, Ágil etc.) e as **ações** do kit.
- Textos curtos: o jogo roda no Telegram. Flavor de fase ou de estágio com 1 a 3 frases.

## 1. Eventos Públicos (§21)

Arquivo de destino: `src/asterion/domain/world_events.py`, lista `WORLD_EVENT_CATALOG`.

Regras já fixas (não reabrir): três fases, um Chefe por fase com uma barra de HP própria; 5 minutos de reunião sem dano antes da Fase 1; a fase só avança quando o HP zera; a entrada fecha aos 15 minutos ou no início da fase final.

Para cada Evento, entregar:

| Campo | O que é |
|---|---|
| `event_id` | Identificador estável, minúsculo, ex.: `evt_tdo_cerco_das_cinzas` |
| Nome | Nome mostrado ao jogador |
| Região | Uma das 6 Regiões |
| Nível de referência | 1 a 60; normalmente dentro da faixa da Região |
| Fase 1, 2 e 3 | Para cada fase: o Chefe (nome, perfil, 3 a 5 ações descritas em palavras) e 1 a 3 frases de flavor |
| Texto de conclusão | Mostrado ao vencer a Fase 3 |
| Sintonizado? | Sim/Não (Evento sintonizado, §21) |
| Nível mínimo de entrada | Se diferente do padrão |

Quantidade sugerida para o Beta: 1 Evento por Região (6). A agenda semanal já existe; o catálogo é rodado pelos horários.

Decisão do autor (2026-11-14): nos Eventos, criar **criaturas novas** quando isso melhorar o conteúdo; não limitar a criaturas existentes. Fluxo: Narrative Designer (identidade e lore), Game Designer (perfil e ações), Systems Designer (regras e balanceamento), autor aprova o conteúdo narrativo/conceitual, QA valida a implementação. Valores de jogo só entram depois de aprovados.

## 2. Provações do Juramento (§22)

Arquivo de destino: `src/asterion/domain/oaths.py`, lista `OATH_TRIAL_CATALOG`.

Regras já fixas: 3 combates seguidos, na ordem **Elite, Elite, Chefe**; HP continua entre os combates; pontos 10 / 15 / 20 + 15 de conclusão; inimigos usam a média de nível do grupo.

Para cada Provação, entregar:

| Campo | O que é |
|---|---|
| `trial_id` | Ex.: `jur_guardioes_do_limiar` |
| Nome | Nome mostrado |
| Combate 1 (Elite) | Criatura: nome, perfil, ações; flavor de 1 a 3 frases |
| Combate 2 (Elite) | Idem |
| Combate 3 (Chefe) | Idem |
| Texto de conclusão | Ao vencer o Chefe |

A criatura pode ser nova ou reaproveitar uma já existente no Bestiário (dizer qual). Quantidade sugerida: 4 a 6 Provações, em rodízio semanal. Mínimo do Beta (2026-11-14): 4. Sempre que possível, reaproveitar criaturas existentes para reduzir escopo.

## 3. Rotas da Expedição (§22)

Arquivo de destino: `src/asterion/domain/expeditions.py`, lista `EXPEDITION_ROUTE_CATALOG`.

Regras já fixas: 3 estágios de 24 horas; cada estágio tem **exatamente 3 opções**: uma favorável (100), uma neutra (50) e uma ruim (25). A pista de qual é qual fica no texto do estágio, sem ser óbvia.

Para cada Rota, entregar:

| Campo | O que é |
|---|---|
| `route_id` | Ex.: `exp_trilha_dos_vales` |
| Nome | Nome mostrado |
| Estágio 1, 2 e 3 | Flavor com a pista (2 a 4 frases) e as 3 opções, cada uma com rótulo curto (botão) e a qualidade: favorável, neutra ou ruim |
| Texto de retorno | Ao fim do estágio 3 |

Quantidade sugerida: 4 a 6 Rotas, em rodízio semanal. Mínimo do Beta (2026-11-14): 4. Sempre que possível, reaproveitar criaturas existentes para reduzir escopo.

## 4. Revisão do Flavor Text

O banco de Flavor Text (telas de Sistema e das seis Regiões) entrou no PR 146 como **rascunho**. Arquivo: `src/asterion/domain/flavor_catalog.py`. Tarefa: ler, corrigir tom e Lore pela Bíblia v4.0.7 e marcar como aprovado. Não mudar as chaves (identificadores), só os textos.

Decisão do autor (2026-11-14): o `flavor_catalog.py` entra na auditoria completa da Crônica contra a Bíblia v4.0.7, feita antes do Beta fechado. O Narrative Designer audita primeiro, apontando arquivo, linha, trecho, regra da Bíblia, problema e correção. O autor aprova os textos canônicos e o tom, o Programmer aplica as correções e o QA valida.

## 5. Crônica I: Dia 1

Falta só a data em que a Crônica I abre no servidor (o Dia 1). O plano é abrir depois de algumas semanas do Beta. Decisão do autor, sem texto a escrever.

Esclarecimento (2026-11-14): "Dia 1 do lançamento" é o lançamento público, não o início do Beta fechado (alvo de desenvolvimento 05/12/2026). O Beta pode rodar sem iniciar a temporada competitiva da Crônica. A proposta v0.2 da Crônica não é promovida ao `SOURCE_AUTHORITY.md` até ser revisada e aprovada.

## Formato de entrega

Um arquivo Markdown por bloco (Eventos, Provações, Rotas), com uma seção por item e os campos das tabelas acima. Ao receber, a engenharia transcreve para os catálogos, gera os kits pela fórmula e roda os testes.
