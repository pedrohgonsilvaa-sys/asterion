# Asterion

Fundação técnica do **Asterion**, RPG/MMORPG dark fantasy para Telegram.

## Estado atual

Este repositório começou do zero em setembro de 2026. As fontes autoritativas
vigentes e sua hierarquia estão listadas em [`docs/SOURCE_AUTHORITY.md`](docs/SOURCE_AUTHORITY.md).
Nesta sincronização, elas são a Fonte Mestra v1.4.9, Terras do Ocaso v1.0.13,
Vales dos Enforcados v1.0.3 e a consolidação Visual/UI de 2026-10-04.

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
e personagens com o estágio inicial persistente do prólogo. A `20260920_0003`
adiciona a atividade Foreground e o primeiro combate persistente; a `20260920_0004`
adiciona Vigor, Braseiros permanentes, estado mundial, Feitos e Missões mínimos
necessários para o fim do Prólogo e o Menu Principal.

## Criação persistente implementada

`/start → Nome → Raça → Classe → Confirmação Final → Cinzas na Estrada`.

`/start` recupera o personagem ou a tela exata do draft no PostgreSQL, inclusive
detalhes e revisão de escolhas. A confirmação é transacional e idempotente. O
botão `Seguir pela Estrada` cria ou retoma a atividade Foreground persistente do
primeiro Cão Cinéreo. O tutorial implementa Atacar, Defender, primeira Arte,
combate normal, vitória e o grant fixo de 320 XP. O **Braseiro da Estrada**, a ação
`Descansar`, a conclusão do Prólogo, o Feito **Cinzas na Estrada**, o início
automático de **P1 — Vozes na Estrada** e o Menu Principal persistente também já
estão implementados. O próximo bloco jogável é a execução de P1 conforme Terras do
Ocaso v1.0.2 + Visual/UI sincronizada de 21/09/2026.

As imagens oficiais ainda não estão disponíveis. Todas as telas funcionam com
texto e inline keyboard; a configuração opcional `ASTERION_CREATION_IMAGES`
permite adicionar assets oficiais posteriormente, sem mudar o fluxo. Os
placeholders de imagem da especificação não são exibidos.

Consulte [operação e decisões técnicas](docs/CHARACTER_CREATION.md) para servidor,
política de nomes, mídia opcional e testes em PostgreSQL.

A implementação técnica do primeiro encontro está documentada em
[`docs/PROLOGUE_FIRST_COMBAT.md`](docs/PROLOGUE_FIRST_COMBAT.md). A especificação
histórica do primeiro Braseiro, fim do Prólogo e Menu Principal permanece em
[`docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md`](docs/specs/PROLOGUE_BRAZIER_MENU_V1.4.3_TDO_V1.0.1.md).

Este trecho preserva um snapshot histórico da implementação de P1. Para trabalho
atual, use as autoridades listadas em `docs/SOURCE_AUTHORITY.md`. A especificação
focada de P1 permanece como registro histórico em
[`docs/specs/P1_VOZES_NA_ESTRADA_V1.4.3_TDO_V1.0.2.md`](docs/specs/P1_VOZES_NA_ESTRADA_V1.4.3_TDO_V1.0.2.md).

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
