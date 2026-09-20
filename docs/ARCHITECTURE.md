# Arquitetura inicial do Asterion

## Autoridade das fontes

A implementação deve ser confrontada continuamente com:

1. **ASTERION — GDD Estrutural v1.4.1**, Fonte Mestra vigente;
2. **ASTERION — Consolidação de Visual & UI (2026-09-20)**.

A Fonte Mestra v1.4.1 substitui integralmente v1.4 e todas as versões anteriores. Sua **Baseline Numérica v1.0 está fechada para implementação e testes**.

Este documento registra somente decisões de implementação da fundação. Ele não substitui as Fontes. Exemplos de mockup ainda podem usar `SIMULAR` quando não correspondem a conteúdo autoritativo, mas valores, custos, limites, fórmulas e slots já consolidados na Baseline Numérica v1.0 devem ser implementados como oficiais.

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

1. Fundação técnica e CI.
2. Conta/personagem e `/start` persistente.
3. Atividade Foreground autoritativa.
4. Prólogo `Cinzas na Estrada`.
5. Motor de combate determinístico.
6. Terras do Ocaso: mundo, Caçada, Missões, Desbravar, Inventário/equipamentos e uma Masmorra representativa.
