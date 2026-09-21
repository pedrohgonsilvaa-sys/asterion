# Asterion

Fundação técnica do **Asterion**, RPG/MMORPG dark fantasy para Telegram.

## Estado atual

Este repositório começou do zero em setembro de 2026. A implementação segue duas fontes de projeto consolidadas:

- **ASTERION — GDD Estrutural v1.4.3** — Fonte Mestra vigente, com a **Baseline Numérica v1.0 fechada para implementação e testes**.
- **ASTERION — Conteúdo: Terras do Ocaso v1.0.1 FINAL** — autoridade regional da vertical slice Nv.1–10.
- **ASTERION — Consolidação de Visual & UI (2026-09-20), sincronizada com GDD v1.4.3 + Terras do Ocaso v1.0.1** — Fonte de apresentação, navegação e UX player-facing.

A Fonte Mestra v1.4.3 substitui integralmente a v1.4.2 e versões anteriores. A reabertura da conversão absoluta de XP de inimigos foi encerrada na v1.4.3; a Baseline Numérica v1.0 não possui reabertura numérica vigente.

A primeira meta de produção é uma **vertical slice das Terras do Ocaso**, antes da produção integral do conteúdo de lançamento.

## Stack oficial

- Python
- aiogram 3
- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Redis
- APScheduler (ou scheduler persistente equivalente)
- Pytest
- Docker
- Git/GitHub
- arquitetura inicial: modular monolith
- polling no desenvolvimento; webhook em produção

## Princípios técnicos já incorporados

- PostgreSQL é a fonte final de verdade.
- Estado crítico não depende de mensagem Telegram, sessão de UI ou dispositivo.
- Operações críticas devem ser atômicas e idempotentes.
- Atividades instanciadas carregarão `ruleset_version`.
- Integrações externas serão desacopladas por Transactional Outbox.
- Callbacks serão tratados como intenção do cliente, nunca como autorização.

## Estrutura inicial

```text
src/asterion/
├── api/             # HTTP, health e webhook Telegram
├── bot/             # integração aiogram / polling
├── application/     # casos de uso e orquestração
├── domain/          # regras de domínio puras
└── infrastructure/  # banco, Redis, outbox e adapters
```

## Autoridade de implementação

Leia também `docs/SOURCE_AUTHORITY.md` antes de implementar regras de jogo. Em conflito entre documentação técnica local e a Fonte Mestra, a Fonte Mestra vigente prevalece.

## Subir a fundação localmente

Requer Docker com Docker Compose.

```bash
docker compose up --build
```

A API ficará disponível em `http://localhost:8000`.

- `GET /health` — liveness do processo.
- `GET /ready` — verifica PostgreSQL e Redis.

O bot Telegram permanece desligado por padrão até existir um token válido.

Para executar o bot em polling durante o desenvolvimento:

```bash
export ASTERION_TELEGRAM_BOT_TOKEN="token-do-bot"
docker compose --profile bot up --build
```

Não grave tokens reais no repositório.

## Desenvolvimento sem Docker

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -e ".[dev]"
cp .env.example .env
pytest
ruff check .
```

No Windows, ative a virtualenv conforme o shell utilizado.

## Migrações

```bash
alembic upgrade head
```

A migration inicial cria a infraestrutura de **Transactional Outbox**. A migration
`20260920_0002` adiciona contas Telegram, drafts versionados, deduplicação de entrada
e personagens com o estágio inicial persistente do prólogo.

## Criação persistente implementada

`/start → Nome → Raça → Classe → Confirmação Final → Cinzas na Estrada`.

`/start` recupera o personagem ou a tela exata do draft no PostgreSQL, inclusive
detalhes e revisão de escolhas. A confirmação é transacional e idempotente. O
botão `Seguir pela Estrada` cria ou retoma a atividade Foreground persistente do
primeiro Cão Cinéreo. O tutorial implementa Atacar, Defender, primeira Arte,
combate normal, vitória e o grant fixo de 320 XP. O estado final fica pronto para
o primeiro Braseiro; Braseiro, Descansar e Menu Principal não estão implementados.

As imagens oficiais ainda não estão disponíveis. Todas as telas funcionam com
texto e inline keyboard; a configuração opcional `ASTERION_CREATION_IMAGES`
permite adicionar assets oficiais posteriormente, sem mudar o fluxo. Os
placeholders de imagem da especificação não são exibidos.

Consulte [operação e decisões técnicas](docs/CHARACTER_CREATION.md) para servidor,
política de nomes, mídia opcional e testes em PostgreSQL.

A implementação técnica do primeiro encontro está documentada em
[`docs/PROLOGUE_FIRST_COMBAT.md`](docs/PROLOGUE_FIRST_COMBAT.md). A próxima etapa
é o primeiro Braseiro, conclusão do prólogo e Menu Principal, especificados em
[`docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md`](docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md).

## Testes completos

Além de `pip install -e ".[dev]"`, disponibilize um PostgreSQL exclusivo para testes
e configure `ASTERION_TEST_DATABASE_URL`. A suíte cria um schema isolado por teste,
aplica as migrations reais e remove somente esse schema ao terminar.

```bash
export ASTERION_TEST_DATABASE_URL="postgresql+asyncpg://asterion:asterion@localhost:5432/asterion_test"
ruff check .
pytest
```

Sem essa variável, os testes que exigem PostgreSQL são explicitamente pulados;
isso não constitui execução completa. O CI fornece PostgreSQL 16 e executa toda a suíte.
