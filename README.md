# Asterion

Fundação técnica do **Asterion**, RPG/MMORPG dark fantasy para Telegram.

## Estado atual

Este repositório começou do zero em setembro de 2026. A implementação segue duas fontes de projeto já consolidadas:

- **ASTERION — GDD Estrutural v1.3** — Fonte Mestra estrutural.
- **ASTERION — Consolidação de Visual & UI (2026-09-19)** — Fonte de apresentação e UX player-facing.

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

A migration inicial cria apenas a infraestrutura de **Transactional Outbox**. Conta, personagem e os demais sistemas entram nas próximas etapas da vertical slice.

## Próxima etapa

Implementar o primeiro fluxo persistente oficial:

`/start → conta → personagem existente ou criação → nome → raça → classe → confirmação → prólogo Cinzas na Estrada`.
