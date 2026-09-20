# Asterion

Fundação técnica do **Asterion**, RPG/MMORPG dark fantasy para Telegram.

## Estado atual

Este repositório começou do zero em setembro de 2026. A implementação segue duas fontes de projeto consolidadas:

- **ASTERION — GDD Estrutural v1.4.2** — Fonte Mestra vigente, estruturalmente fechada para implementação do escopo vigente na **Baseline Numérica v1.0**, com uma única reabertura pontual documentada: a conversão absoluta da unidade global de XP de inimigo em 49.7.
- **ASTERION — Consolidação de Visual & UI (2026-09-20)** — Fonte de apresentação, navegação e UX player-facing.

A Fonte Mestra v1.4.2 substitui integralmente as versões anteriores. Valores da Baseline Numérica v1.0 não devem ser tratados como `SIMULAR`, exceto quando a própria Fonte Mestra registrar uma reabertura explícita. Na v1.4.2, a única reabertura vigente é a conversão absoluta da unidade global de XP de inimigo; ela não bloqueia recompensas fixas de conteúdo único/story, como o primeiro encontro do prólogo.

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
botão `Seguir pela Estrada` apenas reconstrói a tela persistente; sua transição
pertence à próxima etapa. Não há combate, Arte, Braseiro ou Menu Principal.

As imagens oficiais ainda não estão disponíveis. Todas as telas funcionam com
texto e inline keyboard; a configuração opcional `ASTERION_CREATION_IMAGES`
permite adicionar assets oficiais posteriormente, sem mudar o fluxo. Os
placeholders de imagem da especificação não são exibidos.

Consulte [operação e decisões técnicas](docs/CHARACTER_CREATION.md) para servidor,
política de nomes, mídia opcional e testes em PostgreSQL.

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
