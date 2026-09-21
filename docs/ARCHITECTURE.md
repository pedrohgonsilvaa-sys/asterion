# Arquitetura inicial do Asterion

## Autoridade das fontes

A implementação deve ser confrontada continuamente com:

1. **ASTERION — GDD Estrutural v1.4.3**, Fonte Mestra vigente;
2. **ASTERION — Conteúdo: Terras do Ocaso v1.0.2 FINAL**, autoridade regional;
3. **ASTERION — Consolidação de Visual & UI (2026-09-21), sincronizada com GDD v1.4.3 + TDO v1.0.2**.

A Fonte Mestra v1.4.3 substitui integralmente v1.4.2 e todas as versões anteriores. Sua **Baseline Numérica v1.0 está fechada para implementação e testes**; a reabertura da conversão absoluta de XP de inimigos foi encerrada.

Este documento registra somente decisões de implementação da fundação. Ele não substitui as Fontes. Exemplos de mockup ainda podem usar `SIMULAR` quando não correspondem a conteúdo autoritativo. Valores, custos, limites, fórmulas e slots consolidados na Baseline Numérica v1.0 e o conteúdo fechado de Terras do Ocaso v1.0.2 devem ser tratados como oficiais.

## Modular monolith

O código permanece em um único produto implantável, separado internamente por responsabilidade:

- `domain`: regras puras e invariantes do jogo;
- `application`: casos de uso, transações e orquestração;
- `infrastructure`: PostgreSQL, Redis, scheduler, outbox e adapters externos;
- `bot`: apresentação Telegram/aiogram;
- `api`: FastAPI, health, webhook e futuras superfícies administrativas autorizadas.

A camada Telegram não deve conter a verdade do jogo. Handlers convertem mensagens/callbacks em comandos para a aplicação e renderizam o resultado.

## Persistência e concorrência

PostgreSQL é a autoridade final. Redis poderá ser usado para cache, coordenação, rate limit e facilidades transitórias, mas não será a única proteção contra duplicidade ou unicidade.

Operações críticas devem usar transação, constraints, locks de linha e/ou versionamento otimista conforme o caso. A implementação futura de atividades seguirá `game_activity_id`, IDs estáveis e `state_version` suficiente para rejeitar callbacks obsoletos.

## Rulesets

Atividades instanciadas carregarão `ruleset_version`. Patches não devem mudar silenciosamente uma run/combate já iniciado. Conteúdo permanente deve usar IDs estáveis e nunca reutilizados.

O primeiro combate materializa essa regra com `game_activity_id`, `encounter_id`,
`combat_id`, `state_version` e snapshot determinístico. A transação de aplicação
bloqueia a identidade persistente do ator; índices parciais e grants únicos são a
proteção final contra atividades e recompensas duplicadas. Consulte
`docs/PROLOGUE_FIRST_COMBAT.md`.

## Transactional Outbox

A fundação já cria a tabela `outbox_messages`.

A intenção é que uma transação de jogo grave simultaneamente:

1. a mudança autoritativa do jogo;
2. a intenção de produzir um efeito externo.

Um worker posterior entregará Telegram/notificações. Falha de apresentação não desfaz uma operação do jogo que já foi commitada. `dedup_key` protege contra duplicação do mesmo efeito lógico e `aggregate_key` permite preservar ordem quando necessário.

O worker e a política de retry serão implementados antes de qualquer fluxo econômico ou de recompensa depender do outbox.

## Telegram

- desenvolvimento: polling;
- produção: webhook;
- callbacks não são autorização;
- `/start`, `/menu`, reconnect e mensagens antigas deverão reconstruir a interface a partir do estado autoritativo;
- UI seguirá a Fonte Visual/UI e deverá preferir edição da mesma mensagem quando apropriado.

## Etapas imediatas

Já implementados no `main`: fundação técnica/CI, conta e criação persistentes, atividade Foreground, Prólogo `Cinzas na Estrada`, primeiro combate determinístico, Braseiro da Estrada, conclusão do Prólogo, início de P1 e Menu Principal persistente.

Próxima sequência de produção:

1. **P1 — Vozes na Estrada** completa, usando TDO v1.0.2 + Visual/UI sincronizada de 21/09/2026;
2. gates iniciais de Caçada Manual e Desbravar concedidos pela conclusão de P1;
3. expansão incremental do mundo regional sem antecipar conteúdo fora das Fontes;
4. Inventário/equipamentos e uma Masmorra representativa quando seus blocos entrarem no escopo do vertical slice.

Cada novo bloco deve preservar reconstrução autoritativa, idempotência, `ruleset_version`/versão de conteúdo quando aplicável e compatibilidade com estados já persistidos.
