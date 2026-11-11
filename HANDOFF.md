# ASTERION — Handoff técnico e de produto

**Data da auditoria:** 2026-11-06  
**Checkout:** `docs/asterion-proficiency-equipment-v1.9.0` · `HEAD 5abfb64` (`docs: add Asterion proficiency phase 2E drafts`)  
**Repositório:** `origin` → `https://github.com/pedrohgonsilvaa-sys/asterion.git`  
**Estado deste documento:** retrato estático do repositório e dos documentos presentes nesta data. Não representa homologação de release nem afirma que os testes passaram.

> **Como ler este handoff:** distinções entre “implementado”, “em andamento” e “canônico” são importantes aqui. O checkout está sujo: há alterações locais em código/testes e arquivos não rastreados, incluindo uma migration de Armazém. A documentação Fase 2E v1.9.1 também se declara candidata, não canônica e não pronta para integração. Não trate essas alterações como código publicado sem primeiro revisar o diff e a autoridade documental.

## 1. Visão geral

ASTERION é um RPG/MMORPG de fantasia sombria medieval que será lançado inicialmente como bot privado do Telegram, sem Mini App. A experiência combina campanha narrativa, combate por turnos, evolução persistente de personagem, exploração de um mundo dividido em regiões, coleta/crafting, masmorras e atividades sociais. O tom definido no GDD é decadente, melancólico e misterioso; a referência é a sensação de descoberta de dark fantasy moderno, sem copiar uma propriedade intelectual específica.

O jogador cria um personagem escolhendo uma das cinco raças (`remanescente`, `velado`, `cinereo`, `hemario`, `alvorano`) e uma das seis classes (`sentinela`, `errante`, `vigia`, `tecelao`, `oraculo`, `luminar`). A criação leva ao prólogo, à campanha e a sistemas persistentes como Caminho, Artes, Talentos, Equipamentos, Ofícios, Cosméticos e Legado. A regra de conta registrada no GDD é **uma conta Telegram = um personagem por servidor**; múltiplas contas são permitidas, sujeitas às regras antiabuso.

O ciclo jogável implementado gira em torno de: abrir Aventura/Mapa, avançar missões e descobrir locais, preparar a configuração de combate, lutar ou executar uma atividade de Caçada/Ronda/Desbravar, receber XP/recursos, equipar/craftear e retomar a campanha. Masmorras preservam runs persistentes; grupos permitem atividades cooperativas e colisões PvPvE. A Ronda de Caça automatiza encontros em lotes finitos, não é uma simulação offline ilimitada.

**Público-alvo:** o GDD define gênero e plataforma, mas não foi encontrada uma persona demográfica formal. Pela proposta documentada, o público pretendido são jogadores de Telegram que gostam de progressão de longo prazo, combate tático por turnos, exploração e lore de fantasia sombria, além de atividades cooperativas e crafting. Essa descrição do perfil é uma inferência de produto, não uma regra canônica.

## 2. Stack e operação

### Linguagem, serviços e dependências

| Camada | Tecnologia | Versão declarada no repositório |
|---|---|---|
| Linguagem | Python | `>=3.12,<3.14`; Docker usa Python 3.12 |
| Bot Telegram | `aiogram` | `>=3,<4` |
| API/HTTP | FastAPI + Uvicorn | `fastapi >=0.115,<1`; `uvicorn[standard] >=0.30,<1` |
| Persistência | PostgreSQL + SQLAlchemy async + asyncpg | PostgreSQL 16 no Compose/CI; `SQLAlchemy[asyncio] >=2,<3`; `asyncpg >=0.29,<1` |
| Migrações | Alembic | `>=1.13,<2` |
| Redis | redis-py async | `redis >=5,<7`; Redis 7 no Compose |
| Agendador | APScheduler AsyncIO | `>=3.10,<4` |
| Configuração | Pydantic Settings | `>=2,<3` |
| Build | setuptools | `>=75` |
| Testes/desenvolvimento | pytest, pytest-asyncio, httpx, Ruff, tzdata (Windows) | `pytest >=8,<9`, `pytest-asyncio >=0.24,<1`, `httpx >=0.27,<1`, `ruff >=0.8,<1`, `tzdata >=2024.1` (Windows) |
| Container/CI | Docker/Compose, GitHub Actions | Dockerfile `python:3.12-slim`; CI Ubuntu + PostgreSQL 16 |

As faixas acima são as dependências permitidas por `pyproject.toml`; **não há lockfile** (`uv.lock`, Poetry lock ou requirements congelado) no checkout. Portanto, não são versões exatas instaladas em produção. O pacote declara versão `0.1.0`, instala por setuptools e publica os comandos `asterion-api` e `asterion-bot`.

### Executar localmente

Requer Python 3.12 e Docker Compose. O caminho com containers sobe PostgreSQL, Redis, migration e API:

```powershell
docker compose up --build
```

API local: `http://localhost:8000`; endpoints de operação: `GET /health` e `GET /ready` (o segundo valida PostgreSQL e Redis). Para incluir o bot em polling, definir `ASTERION_TELEGRAM_BOT_TOKEN` no `.env` e rodar:

```powershell
docker compose --profile bot up --build
```

Alternativa sem Docker (depois de iniciar PostgreSQL e Redis localmente):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
alembic upgrade head
asterion-api
```

O comando preserva um `.env` já existente. No Bash, ative com `source .venv/bin/activate` e copie `.env.example` somente se ainda não houver `.env`. O bot em polling é um processo separado: habilitar `ASTERION_TELEGRAM_BOT_ENABLED=true`, configurar o token e `ASTERION_TELEGRAM_MODE=polling`, depois executar `asterion-bot`.

### Deployment e CI

- `Dockerfile` cria uma imagem Python, instala o pacote e copia `src/` e `alembic/`. Não copia o diretório raiz `assets/`; imagens configuradas por caminho `file:` precisam ser montadas ou incluídas explicitamente na imagem.
- `docker-compose.yml` é uma composição de desenvolvimento: Postgres 16, Redis 7, serviço one-shot `migrate`, API na porta 8000 e serviço de bot sob o profile `bot`. Credenciais e URLs do Compose são valores locais de desenvolvimento, não devem ser reutilizados em produção.
- Atenção ao estado deste checkout: como `alembic/versions/20261026_0032_inventory_warehouse.py` está no contexto local, `docker compose up --build` pode aplicar a migration WIP 0032 ao Postgres do Compose. Use apenas um banco descartável de desenvolvimento até revisar migration e diff; nunca aponte esse Compose para uma base compartilhada/produção.
- `ASTERION_TELEGRAM_MODE=webhook` é suportado pela API em `src/asterion/api/app.py` (`POST /telegram/webhook`); exige bot habilitado, token e secret de webhook. Não foi encontrada configuração de domínio/TLS, registro do webhook no Telegram, provedor de hosting, pipeline de release ou ambiente de produção definido. O deployment de produção, portanto, ainda precisa ser formalizado.
- `.github/workflows/ci.yml` declara lint (`ruff check .`), testes (`pytest`) e verificação de migrações (`alembic upgrade head`, `alembic check`) em push de `main`, pull request e `workflow_dispatch`, com PostgreSQL 16. O status real do workflow não foi consultado nesta auditoria.
- `ASTERION_TEST_DATABASE_URL` é necessária para a suíte com PostgreSQL descrita no README. **Nenhum teste ou lint foi executado para produzir este handoff.**

### Variáveis de ambiente

Prefixo Pydantic: `ASTERION_`; arquivo lido localmente: `.env`. `src/asterion/config.py` define defaults para os campos e valida bot habilitado/token e webhook/secret.

| Variável | Uso |
|---|---|
| `ASTERION_APP_ENV` | `development`, `test` ou `production` |
| `ASTERION_APP_HOST`, `ASTERION_APP_PORT` | bind HTTP (default `0.0.0.0:8000`) |
| `ASTERION_DATABASE_URL` | conexão PostgreSQL async (`postgresql+asyncpg://...`) |
| `ASTERION_REDIS_URL` | conexão Redis; hoje usada pelo `/ready` para `PING` |
| `ASTERION_SERVER_ID` | identidade do servidor decidida no backend |
| `ASTERION_BLOCKED_CHARACTER_NAMES` | conjunto JSON de nomes bloqueados, comparação case-insensitive |
| `ASTERION_CREATION_IMAGES` | JSON `tela -> Telegram file_id` ou `file:caminho`; opcional |
| `ASTERION_TELEGRAM_BOT_ENABLED` | liga/desliga integração do bot |
| `ASTERION_TELEGRAM_BOT_TOKEN` | token fornecido pelo BotFather; não armazenar no Git |
| `ASTERION_TELEGRAM_MODE` | `polling` ou `webhook` |
| `ASTERION_TELEGRAM_WEBHOOK_SECRET` | obrigatório para bot ativo em webhook |
| `ASTERION_TEST_DATABASE_URL` | URL do PostgreSQL isolado usado pelos testes |

Não abrir nem copiar o `.env` existente: ele pode conter credenciais locais. Use `.env.example` como inventário seguro.

## 3. Estrutura do repositório

Estrutura funcional (arquivos de conteúdo e testes longos omitidos da árvore compacta):

```text
.
├── src/asterion/
│   ├── api/app.py                 # FastAPI, health/readiness, webhook e ciclo do scheduler
│   ├── bot/                       # Aiogram: routers/handlers, renderização UI e runtime
│   ├── application/               # casos de uso, coordenação de transações e serviços
│   ├── domain/                    # regras puras, fórmulas, catálogos e conteúdo de combate
│   ├── infrastructure/db/         # Base, sessão, ORM e codecs/repositórios de combate
│   ├── config.py                  # Pydantic Settings e validação de configurações Telegram
│   └── main.py                    # entrypoint da API
├── alembic/versions/              # histórico de schema 0001…0032 (0032 está sem commit)
├── tests/                         # testes unitários, integração DB/Telegram e playthroughs
├── docs/                          # especificações técnicas e handoff anterior (mais antigo)
├── ASTERION_GDD_Estrutural_v1.6.0_Fonte_Mestra.md
├── ASTERION_CONTEUDO_*             # fontes regionais, versões antigas e propostas
├── ASTERION_CONTRATO_GLOBAL_WEAPON_METADATA_v1.0.0_FINAL.md
├── SOURCE_AUTHORITY.md             # índice operacional da hierarquia de fontes
├── pyproject.toml                  # dependências, scripts, pytest e Ruff
├── Dockerfile / docker-compose.yml # imagem e stack de desenvolvimento
└── .env.example                    # nomes de variáveis, sem segredo real
```

### Arquivos importantes por responsabilidade

**Bot e API**

- `src/asterion/bot/runtime.py`: composição de serviços e routers; ponto principal para descobrir o que está conectado no bot.
- `src/asterion/bot/polling.py`: entrypoint de polling e início/fim do agendador de Ronda.
- `src/asterion/bot/round_scheduler.py`: dispara `RoundService.advance_due_rounds` a cada 15 segundos.
- `src/asterion/bot/*_handlers.py`: tradução de mensagens/callbacks em chamadas de serviços; há pares de UI para várias telas.
- `src/asterion/bot/*_ui.py`: `Screen`, textos, teclados inline e callback data.
- `src/asterion/api/app.py`: health/readiness, endpoint de webhook e scheduler quando webhook está ativo.
- `src/asterion/config.py`, `src/asterion/main.py`: settings e comando `asterion-api`.

**Aplicação (casos de uso)**

- `creation.py`, `prologue.py`, `account.py`, `character_names.py`, `character_deletion.py`: onboarding, conta, nome e ciclo de personagem.
- `combat_configuration_guard.py`, `progression.py`, `path_selection.py`, `talents.py`, `active_arts.py`, `class_trials.py`: configuração e evolução do personagem.
- `road.py`, `round.py`, `world.py`, `vigor.py`, `scripted_combat.py`: mapa/mundo, Caçada, Ronda, Desbravar, Vigor e encontros roteirizados.
- `p1.py`–`p7.py`, `vde_missions.py`, `nareth_missions.py`, `varzeas_missions.py`, `altos_missions.py`, `s1.py`–`s6.py`, `s25.py`–`s36.py`: serviços de campanha/side quests e conteúdo por região. P31–P36 aparecem sob nomes/serviços `altos_*`; verificar o escopo interno antes de expandir esse padrão.
- `dungeons.py`, `campaign_coop.py`, `groups.py`, `group_hunts.py`, `pvpve.py`: masmorras persistentes, jornadas cooperativas, grupo e conflito PvPvE.
- `inventory.py`, `equipment.py`, `equipment_modifications.py`, `crafting.py`, `professions.py`, `consumables.py`, `legacy.py`, `cosmetics.py`, `doctrines.py`: inventário, itens, aprimoramentos, crafting, consumíveis, Legado e customização.
- `inventory_capacity.py`, `safe_location.py`, `warehouse.py`: alterações locais não rastreadas nesta branch para capacidade, validação de Braseiro e Armazém.

**Domínio**

- `domain/combat.py`, `combat_math.py`, `campaign_combat.py`: máquina de combate, resolução e aritmética.
- `domain/creation.py`, `paths.py`, `path_arts.py`, `arts.py`, `talents.py`, `class_trials.py`: catálogos e regras de criação/progressão.
- `domain/road.py`, `economy.py`, `consumables.py`, `professions.py`, `legacy.py`: conteúdo de atividade, economia, itens consumíveis, receitas e fatores de Legado.
- `domain/equipment.py`, `equipment_stats.py`, `equipment_modifications.py`, `weapon_metadata.py`: regras de equipamento e composição de atributos.
- `domain/dungeons.py` e `*_dungeon.py`, `tdo_*.py`, `vde_*.py`, `nareth_*.py`, `varzeas_*.py`, `altos_*.py`, `confins_*.py`: perfil global e encontros/dungeons específicos.

**Persistência e qualidade**

- `src/asterion/infrastructure/db/base.py`, `session.py`, `models.py`: declarative base, conexão/session factory e schema ORM.
- `combat_codec.py`, `combat_repository.py`: serialização/reconstrução e repositório do estado de combate.
- `alembic/versions/20260920_0001_...` a `20261023_0031_...`: migrações rastreadas; `20261026_0032_inventory_warehouse.py` é arquivo local não rastreado.
- `tests/`: cerca de 230 arquivos `test_*.py` no checkout. Os testes PostgreSQL provisionam schema isolado por teste, conforme README/`tests/conftest.py`.

### Fontes de design que devem ser consultadas antes de alterar regras

O índice `SOURCE_AUTHORITY.md` é a seleção operacional; o GDD estrutural v1.6.0 é a autoridade de regras globais e a baseline numérica está fechada. Fontes regionais atuais: Terras do Ocaso v1.0.16, Vales dos Enforcados v1.0.6, Planícies de Nareth v1.0.2, Várzeas Carmesins v1.0.3, Altos Cinéreos v1.0.1 e Confins do Véu v1.0.0 FINAL_APPROVED. O Contrato Global de Weapon Metadata v1.0.0 FINAL rege metadata mecânica de armas. UI: `ASTERION_UI_DECISOES_2026-10-13_FINAL_SYNC_v1.6.0_TDO_v1.0.15_VALES_v1.0.6.md`.

Existem muitos snapshots e propostas antigos. Não escolha a versão pelo nome/recência isoladamente. Em particular, o `SOURCE_AUTHORITY.md` da raiz mantém TDO v1.0.16 como atual; uma cópia em worktree seleciona TDO v1.0.17 como alvo e não é autoridade operacional deste checkout. A Bíblia Canônica v3.0 FINAL e Lore v1.2 constam no índice; a Bíblia v3.2 no diretório raiz não está selecionada pelo índice e está sem rastreamento. `docs/REPASSE_TECNICO.md` é anterior e não reflete integralmente o estado atual.

## 4. Arquitetura e fluxo de uma ação

O desenho é um **monólito modular assíncrono**. Aiogram cuida do Telegram; FastAPI hospeda health checks e webhook; serviços em `application/` coordenam regras de domínio e SQLAlchemy; PostgreSQL guarda o estado autoritativo.

Fluxo típico (ex.: jogador confirma uma ação de combate por botão):

1. Telegram envia update/callback ao `Dispatcher` do runtime (`bot/runtime.py`), que encaminha a um router registrado.
2. Um handler em `bot/combat_handlers.py` ou handler regional valida formato e contexto básico do callback e chama um serviço de aplicação. A UI nunca deve ser tratada como fonte de autorização.
3. O serviço abre sessão via `SessionFactory`, resolve o personagem pelo Telegram actor + `server_id`, lê/valida a atividade persistida e, em operações críticas, aplica lock/revisão de configuração ou estado.
4. Regras puras de `domain/combat.py`, `combat_math.py` e conteúdo regional resolvem ação, RNG determinístico, efeitos e resultado. A camada de aplicação persiste snapshot/estado com SQLAlchemy e finaliza a transação antes de apresentar resultado.
5. O serviço retorna uma view; `bot/*_ui.py` renderiza texto + inline keyboard e o handler envia/edita mensagem via `present(...)`.

Padrões que aparecem no código e nos contratos:

- PostgreSQL é a fonte de verdade; a sessão/chat/mensagem Telegram é apresentação, não estado de jogo.
- Atividades persistentes têm status/revisão e callbacks versionados. Ações críticas usam IDs de operação/fonte e validação no serviço para reduzir replay e duplicação.
- `combat_codec.py` reconstrói estado de combate serializado; `combat_repository.py` desacopla a persistência da máquina de combate.
- RNG de combate e sorteios de conteúdo relevantes são determinísticos por IDs/seeds; reconectar ou reconstruir a UI não deve rerrolar resultado já materializado.
- Configuração de combate é bloqueada/snapshotada em atividades que exigem isso (`combat_configuration_guard.py`).
- O GDD prevê Transactional Outbox e há `outbox_messages` + migration inicial, mas a busca de código não encontrou worker/dispatcher de outbox conectado. A integração externa não deve ser considerada pronta só porque o modelo existe.
- Redis está configurado e `GET /ready` dá `PING`, mas não foi encontrado uso de Redis no fluxo de gameplay/cache/fila.

O scheduler APScheduler acorda a cada 15 segundos. `max_instances=1` limita a execução dentro de cada processo; em deployment com réplicas, o scheduler pode iniciar em cada instância (API webhook ou processo polling). Antes de escalar horizontalmente, definir scheduler único ou lock distribuído/claim transacional e provar a idempotência de `advance_due_rounds` entre processos.

## 5. Banco de dados

Banco relacional PostgreSQL. O inventário abaixo é gerado a partir de `Base.metadata` carregado de `src/asterion/infrastructure/db/models.py` neste checkout: **80 tabelas, 629 colunas e 126 referências FK**. Tipos são os tipos PostgreSQL compilados pelo SQLAlchemy; `[PK]`, `[NOT NULL]`, `[FK ...]`, `UNIQUE` e checks são declarados no ORM.

**Limite importante:** `models.py` está modificado localmente e a migration `20261026_0032_inventory_warehouse.py` não está rastreada. Assim, este inventário descreve o modelo ORM do checkout, inclusive WIP; não comprova que um banco externo foi migrado até 0032, nem que a migration esteja correta/implantável. A última migration rastreada em Git é `20261023_0031_legacy_core.py`.

As FKs listadas junto a cada coluna são as relações declaradas. Relações sem FK física ou relações de domínio implícitas precisam ser confirmadas em `models.py`; o inventário não infere semântica adicional. `NULL` é indicado explicitamente quando permitido.

### `accounts`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `telegram_id` | `BIGINT` | NOT NULL | PK |

### `achievements`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `achievement_id` | `VARCHAR(64)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `achievement_id`)

### `bestiary_entries`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `creature_id` | `VARCHAR(64)` | NOT NULL | — |
| `bkp` | `INTEGER` | NOT NULL | — |
| `stage` | `VARCHAR(32)` | NOT NULL | — |
| `wins` | `INTEGER` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `creature_id`)

### `bestiary_evidence`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `creature_id` | `VARCHAR(64)` | NOT NULL | — |
| `evidence_id` | `VARCHAR(96)` | NOT NULL | — |
| `category` | `VARCHAR(32)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `creature_id`, `evidence_id`)

### `blocked_deliveries`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `source_key` | `VARCHAR(160)` | NOT NULL | — |
| `kind` | `VARCHAR(24)` | NOT NULL | — |
| `payload` | `JSONB` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`source_key`)

**Checks:** `quantity > 0`; `status IN ('pending','resolved')`

### `braziers`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `brazier_id` | `VARCHAR(64)` | NOT NULL | — |
| `discovered_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `brazier_id`)

### `campaign_journey_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `journey_id` | `UUID` | NOT NULL | PK; FK `campaign_journeys.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `role` | `VARCHAR(16)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `checkpoint_snapshot` | `VARCHAR(96)` | NOT NULL | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `left_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `role IN ('eligible','helper')`; `status IN ('active','left','completed')`

### `campaign_journeys`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `group_id` | `UUID` | NOT NULL | FK `social_groups.id` (ON DELETE CASCADE) |
| `quest_id` | `VARCHAR(32)` | NOT NULL | — |
| `checkpoint` | `VARCHAR(96)` | NOT NULL | — |
| `journey_reference_character_id` | `UUID` | NULL | FK `characters.id` (ON DELETE SET NULL) |
| `technical_host_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE RESTRICT) |
| `context_payload` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `context_payload IS NULL OR jsonb_typeof(context_payload) = 'object'`; `revision >= 0`; `status IN ('active','paused','completed','cancelled')`

### `campaign_objective_credits`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `journey_id` | `UUID` | NULL | FK `campaign_journeys.id` (ON DELETE SET NULL) |
| `quest_id` | `VARCHAR(32)` | NOT NULL | — |
| `objective_id` | `VARCHAR(96)` | NOT NULL | — |
| `source_key` | `VARCHAR(128)` | NOT NULL | — |
| `evidence` | `JSONB` | NOT NULL | — |
| `recorded_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `quest_id`, `objective_id`, `source_key`)

### `campaign_shared_encounter_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `shared_encounter_id` | `UUID` | NOT NULL | PK; FK `campaign_shared_encounters.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` (ON DELETE CASCADE) |
| `actor_key` | `VARCHAR(16)` | NOT NULL | — |
| `role` | `VARCHAR(16)` | NOT NULL | — |
| `checkpoint_snapshot` | `VARCHAR(96)` | NOT NULL | — |
| `settlement_state` | `VARCHAR(16)` | NOT NULL | — |
| `result` | `VARCHAR(16)` | NULL | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `settled_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`game_activity_id`); UNIQUE (`shared_encounter_id`, `actor_key`)

**Checks:** `role IN ('eligible','helper')`; `settlement_state IN ('pending','settled')`

### `campaign_shared_encounters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `journey_id` | `UUID` | NULL | FK `campaign_journeys.id` (ON DELETE SET NULL) |
| `proposal_id` | `UUID` | NULL | FK `group_activity_proposals.id` (ON DELETE SET NULL) |
| `quest_id` | `VARCHAR(32)` | NOT NULL | — |
| `content_id` | `VARCHAR(64)` | NOT NULL | — |
| `journey_reference_character_id` | `UUID` | NULL | FK `characters.id` (ON DELETE SET NULL) |
| `technical_host_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE RESTRICT) |
| `roster_size` | `INTEGER` | NOT NULL | — |
| `scaling_snapshot` | `JSONB` | NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `combat_snapshot` | `JSONB` | NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`proposal_id`)

**Checks:** `combat_snapshot IS NULL OR jsonb_typeof(combat_snapshot) = 'object'`; `roster_size BETWEEN 1 AND 4`; `scaling_snapshot IS NULL OR jsonb_typeof(scaling_snapshot) = 'object'`; `state_version >= 0`; `status IN ('active','completed','failed','paused')`

### `character_account_inputs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `prompt_message_id` | `BIGINT` | NOT NULL | — |
| `current_name` | `VARCHAR(16)` | NOT NULL | — |
| `new_name` | `VARCHAR(16)` | NULL | — |
| `last_update_id` | `BIGINT` | NULL | — |
| `error` | `VARCHAR(16)` | NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `prompt_message_id > 0`; `revision >= 0`; `status IN ('awaiting','preview','invalid','unavailable')`

### `character_active_art_slots`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `slot` | `INTEGER` | NOT NULL | PK |
| `art_id` | `VARCHAR(96)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `art_id`)

**Checks:** `slot BETWEEN 1 AND 3`

### `character_cosmetic_selections`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `character_cosmetics.character_id` (ON DELETE CASCADE) |
| `cosmetic_type` | `VARCHAR(16)` | NOT NULL | PK; FK `character_cosmetics.cosmetic_type` (ON DELETE CASCADE) |
| `cosmetic_id` | `VARCHAR(96)` | NOT NULL | FK `character_cosmetics.cosmetic_id` (ON DELETE CASCADE) |

**Checks:** `cosmetic_type IN ('appearance','title','emblem','frame','banner')`

### `character_cosmetics`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `cosmetic_id` | `VARCHAR(96)` | NOT NULL | PK |
| `cosmetic_type` | `VARCHAR(16)` | NOT NULL | — |
| `source_achievement_id` | `VARCHAR(64)` | NOT NULL | — |
| `acquired_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `cosmetic_type`, `cosmetic_id`)

**Checks:** `cosmetic_type IN ('appearance','title','emblem','frame','banner')`

### `character_deletion_requests`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | — |
| `telegram_id` | `BIGINT` | NOT NULL | — |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `name_at_request` | `VARCHAR(16)` | NOT NULL | — |
| `requested_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `due_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `cancelled_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |

**Checks:** `due_at > requested_at`; `revision >= 0`; `status IN ('preview','pending','cancelled','completed')`

### `character_doctrine_inputs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `character_doctrines.character_id` (ON DELETE CASCADE); FK `characters.id` (ON DELETE CASCADE) |
| `action` | `VARCHAR(8)` | NOT NULL | — |
| `doctrine_id` | `UUID` | NULL | FK `character_doctrines.id` (ON DELETE CASCADE) |
| `expected_revision` | `INTEGER` | NOT NULL | — |
| `expected_configuration_version` | `INTEGER` | NOT NULL | — |
| `prompt_message_id` | `BIGINT` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `(action = 'create' AND doctrine_id IS NULL) OR (action = 'rename' AND doctrine_id IS NOT NULL)`; `action IN ('create','rename')`; `expected_configuration_version >= 0`; `expected_revision >= 0`; `prompt_message_id > 0`

### `character_doctrines`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `name` | `VARCHAR(40)` | NOT NULL | — |
| `configuration` | `JSONB` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`id`, `character_id`)

**Checks:** `char_length(name) BETWEEN 1 AND 40`; `jsonb_typeof(configuration) = 'object'`; `revision >= 0`

### `character_equipment_slots`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `slot` | `VARCHAR(24)` | NOT NULL | PK |
| `equipment_item_id` | `UUID` | NOT NULL | FK `equipment_items.id` (ON DELETE RESTRICT) |

**Restrições únicas:** UNIQUE (`equipment_item_id`)

**Checks:** `slot IN ('Principal', 'Secundária', 'Cabeça', 'Torso', 'Mãos', 'Pés', 'Acessório', 'Artefato')`

### `character_name_reservations`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `server_id` | `VARCHAR(64)` | NOT NULL | PK |
| `normalized_name` | `VARCHAR(16)` | NOT NULL | PK |
| `reserved_until` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `source` | `VARCHAR(16)` | NOT NULL | — |
| `origin_character_id` | `UUID` | NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `normalized_name ~ '^[a-z]{3,16}$'`; `source IN ('rename','deletion')`

### `character_notification_preferences`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `category` | `VARCHAR(16)` | NOT NULL | PK |
| `enabled` | `BOOLEAN` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `category IN ('essentials','events','competitive','guild','market','chronicle')`; `revision >= 0`

### `character_pending_inputs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `input_kind` | `VARCHAR(24)` | NOT NULL | — |
| `prompt_message_id` | `BIGINT` | NOT NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `input_kind IN ('history','doctrine_name','rename')`; `prompt_message_id > 0`

### `character_professions`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `slot` | `VARCHAR(12)` | NOT NULL | PK |
| `profession_id` | `VARCHAR(24)` | NOT NULL | — |
| `level` | `INTEGER` | NOT NULL | — |
| `pxp` | `BIGINT` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `profession_id`)

**Checks:** `level BETWEEN 1 AND 30`; `profession_id IN ('blacksmith','artificer','alchemist','leatherworker','jeweler')`; `pxp >= 0`; `slot != 'secondary' OR level <= 15`; `slot IN ('primary','secondary')`

### `character_profiles`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `history` | `TEXT` | NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `history_prompt_message_id` | `BIGINT` | NULL | — |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `history IS NULL OR char_length(history) <= 1200`; `history_prompt_message_id IS NULL OR history_prompt_message_id > 0`; `revision >= 0`

### `character_rename_history`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | — |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `old_name` | `VARCHAR(16)` | NOT NULL | — |
| `new_name` | `VARCHAR(16)` | NOT NULL | — |
| `renamed_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `origin` | `VARCHAR(16)` | NOT NULL | — |

**Checks:** `origin IN ('player')`

### `character_talent_choices`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `point_slot` | `INTEGER` | NOT NULL | PK |
| `talent_id` | `VARCHAR(96)` | NOT NULL | — |
| `publicly_acquired` | `BOOLEAN` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `talent_id`)

**Checks:** `point_slot BETWEEN 1 AND 12`

### `characters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `telegram_id` | `BIGINT` | NOT NULL | FK `accounts.telegram_id` |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `name` | `VARCHAR(16)` | NOT NULL | — |
| `race` | `VARCHAR(24)` | NOT NULL | — |
| `character_class` | `VARCHAR(24)` | NOT NULL | — |
| `selected_path` | `VARCHAR(24)` | NULL | — |
| `stage` | `VARCHAR(64)` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `level` | `INTEGER` | NOT NULL | — |
| `xp` | `BIGINT` | NOT NULL | — |
| `legacy_level` | `INTEGER` | NOT NULL | — |
| `hp` | `NUMERIC` | NOT NULL | — |
| `max_hp` | `NUMERIC` | NOT NULL | — |
| `vigor` | `INTEGER` | NOT NULL | — |
| `vigor_regen_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `max_vigor` | `INTEGER` | NOT NULL | — |
| `crowns` | `BIGINT` | NOT NULL | — |
| `elite_equipment_pity` | `INTEGER` | NOT NULL | — |
| `elite_legendary_pity` | `INTEGER` | NOT NULL | — |
| `delivery_blocked` | `BOOLEAN` | NOT NULL | — |
| `tracked_secondary_quest_id` | `VARCHAR(32)` | NULL | — |
| `vigor_consumable_cycle` | `DATE` | NULL | — |
| `combat_configuration_version` | `INTEGER` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`telegram_id`, `server_id`)

**Checks:** `character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')`; `combat_configuration_version >= 0`; `crowns >= 0`; `hp >= 0 AND hp <= max_hp AND max_hp > 0`; `legacy_level BETWEEN 0 AND 5`; `level BETWEEN 1 AND 60 AND xp >= 0`; `name ~ '^[A-Z][a-z]{2,15}$'`; `race IN ('remanescente','velado','cinereo','hemario','alvorano')`; `selected_path IS NULL OR selected_path IN ('bastiao','devastador','carrasco','sabotador','atirador','rastreador','conjurador','runico','agoureiro','invocador','guardiao','inquisidor')`; `vigor BETWEEN 0 AND max_vigor AND max_vigor = 100`

### `class_trial_states`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE); FK `game_activities.character_id` |
| `character_class` | `VARCHAR(24)` | NOT NULL | — |
| `trial_id` | `VARCHAR(64)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `current_stage` | `INTEGER` | NOT NULL | — |
| `completed_stages` | `JSONB` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `context` | `VARCHAR(16)` | NOT NULL | — |
| `current_attempt_id` | `UUID` | NULL | FK `game_activities.id` |
| `stage_definition` | `JSONB` | NULL | — |
| `attempt_state` | `JSONB` | NULL | — |

**Restrições únicas:** UNIQUE (`current_attempt_id`)

**Checks:** `(status = 'active') = (attempt_state IS NOT NULL)`; `(status = 'active') = (current_attempt_id IS NOT NULL)`; `attempt_state IS NULL OR jsonb_typeof(attempt_state) = 'object'`; `character_class IN ('sentinela','errante','vigia','tecelao','oraculo','luminar')`; `context IN ('circle','refuge')`; `current_stage BETWEEN 1 AND 3`; `jsonb_typeof(completed_stages) = 'array'`; `stage_definition IS NULL OR jsonb_typeof(stage_definition) = 'object'`; `state_version >= 0`; `status != 'completed' OR completed_stages = '[1,2,3]'::jsonb`; `status IN ('ready','active','completed')`

### `codex_entries`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `entry_id` | `VARCHAR(96)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `entry_id`)

### `codex_fragments`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `entry_id` | `VARCHAR(96)` | NOT NULL | — |
| `fragment_id` | `VARCHAR(96)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `fragment_id`)

### `combats`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `encounter_id` | `UUID` | NOT NULL | FK `encounters.id` |
| `snapshot` | `JSONB` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`encounter_id`)

### `consumable_stacks`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `consumable_id` | `VARCHAR(64)` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `consumable_id`)

**Checks:** `quantity BETWEEN 0 AND 99`

### `crafting_receipts`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `recipe_id` | `VARCHAR(96)` | NOT NULL | — |
| `source_key` | `VARCHAR(160)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `preview_fingerprint` | `VARCHAR(64)` | NOT NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `output_kind` | `VARCHAR(24)` | NULL | — |
| `output_payload` | `JSONB` | NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `committed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `source_key`)

**Checks:** `output_payload IS NULL OR jsonb_typeof(output_payload) = 'object'`; `status IN ('preview','committed','cancelled','expired')`

### `creation_drafts`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `telegram_id` | `BIGINT` | NOT NULL | FK `accounts.telegram_id` |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `version` | `INTEGER` | NOT NULL | — |
| `step` | `VARCHAR(48)` | NOT NULL | — |
| `name` | `VARCHAR(16)` | NULL | — |
| `race` | `VARCHAR(24)` | NULL | — |
| `character_class` | `VARCHAR(24)` | NULL | — |
| `editing` | `BOOLEAN` | NOT NULL | — |
| `error` | `VARCHAR(24)` | NULL | — |
| `rejected_name` | `VARCHAR(16)` | NULL | — |

**Restrições únicas:** UNIQUE (`telegram_id`, `server_id`)

**Checks:** `version >= 0`

### `creation_inputs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `telegram_id` | `BIGINT` | NOT NULL | PK; FK `accounts.telegram_id` |
| `server_id` | `VARCHAR(64)` | NOT NULL | PK |
| `update_id` | `BIGINT` | NOT NULL | PK |

### `dungeon_invites`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `lobby_id` | `UUID` | NOT NULL | FK `dungeon_lobbies.id` (ON DELETE CASCADE) |
| `inviter_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `invitee_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`lobby_id`, `invitee_character_id`)

**Checks:** `state_version >= 0`; `status IN ('pending','accepted','declined','cancelled','expired')`

### `dungeon_lobbies`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `dungeon_family_id` | `VARCHAR(96)` | NOT NULL | — |
| `difficulty` | `VARCHAR(16)` | NOT NULL | — |
| `mode` | `VARCHAR(16)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `leader_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `state_version` | `BIGINT` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `confirmation_deadline` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `run_id` | `UUID` | NULL | FK `dungeon_runs.id` (ON DELETE SET NULL) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `mode IN ('invite','matchmaking')`; `state_version >= 0`; `status IN ('forming','confirming','started','cancelled','expired')`

### `dungeon_lobby_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `lobby_id` | `UUID` | NOT NULL | PK; FK `dungeon_lobbies.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `foreground_activity_id` | `UUID` | NULL | FK `game_activities.id` (ON DELETE SET NULL) |
| `position` | `INTEGER` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `confirmed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`foreground_activity_id`); UNIQUE (`lobby_id`, `position`)

**Checks:** `position BETWEEN 1 AND 4`; `status IN ('invited','joined','queued','matched','confirmed','declined','left')`

### `dungeon_match_queue`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `dungeon_family_id` | `VARCHAR(96)` | NOT NULL | — |
| `difficulty` | `VARCHAR(16)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `lobby_id` | `UUID` | NULL | FK `dungeon_lobbies.id` (ON DELETE SET NULL) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `status IN ('queued','matched','cancelled','expired')`

### `dungeon_pity_states`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `legendary_plus_points` | `INTEGER` | NOT NULL | — |
| `mythic_points` | `INTEGER` | NOT NULL | — |

**Checks:** `legendary_plus_points >= 0`; `mythic_points >= 0`

### `dungeon_run_encounters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `run_id` | `UUID` | NOT NULL | PK; FK `dungeon_runs.id` (ON DELETE CASCADE) |
| `encounter_ordinal` | `INTEGER` | NOT NULL | PK |
| `definition_id` | `VARCHAR(96)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `activity_id` | `UUID` | NULL | FK `game_activities.id` |
| `attempt_count` | `INTEGER` | NOT NULL | — |
| `progress` | `JSONB` | NOT NULL | — |
| `reward_settled` | `BOOLEAN` | NOT NULL | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`activity_id`)

**Checks:** `attempt_count >= 0`; `encounter_ordinal >= 1`; `jsonb_typeof(progress) = 'object'`; `status IN ('pending','active','completed')`

### `dungeon_run_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `run_id` | `UUID` | NOT NULL | PK; FK `dungeon_runs.id` (ON DELETE CASCADE) |
| `foreground_activity_id` | `UUID` | NULL | FK `game_activities.id` (ON DELETE SET NULL) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `position` | `INTEGER` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `vigor_reserved` | `INTEGER` | NOT NULL | — |
| `vigor_refunded` | `BOOLEAN` | NOT NULL | — |
| `consumable_uses` | `INTEGER` | NOT NULL | — |
| `combat_configuration` | `JSONB` | NOT NULL | — |
| `hp` | `NUMERIC` | NOT NULL | — |
| `max_hp` | `NUMERIC` | NOT NULL | — |
| `run_state` | `JSONB` | NOT NULL | — |
| `contribution` | `JSONB` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`foreground_activity_id`); UNIQUE (`run_id`, `position`)

**Checks:** `consumable_uses >= 0`; `hp >= 0 AND max_hp > 0 AND hp <= max_hp`; `jsonb_typeof(combat_configuration) = 'object'`; `jsonb_typeof(contribution) = 'object'`; `jsonb_typeof(run_state) = 'object'`; `position BETWEEN 1 AND 4`; `status IN ('active','defeated','left')`; `vigor_reserved >= 0`

### `dungeon_runs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `dungeon_family_id` | `VARCHAR(96)` | NOT NULL | — |
| `difficulty` | `VARCHAR(16)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `content_version` | `VARCHAR(48)` | NOT NULL | — |
| `reference_level` | `INTEGER` | NOT NULL | — |
| `initial_group_size` | `INTEGER` | NOT NULL | — |
| `current_encounter_ordinal` | `INTEGER` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `has_brazier` | `BOOLEAN` | NOT NULL | — |
| `brazier_activated` | `BOOLEAN` | NOT NULL | — |
| `brazier_after_encounter` | `INTEGER` | NULL | — |
| `active_checkpoint_encounter` | `INTEGER` | NULL | — |
| `progress` | `JSONB` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `last_activity_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `failed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `expired_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `active_checkpoint_encounter IS NULL OR active_checkpoint_encounter >= 1`; `current_encounter_ordinal >= 1`; `difficulty IN ('stable','fractured','rupture')`; `initial_group_size BETWEEN 1 AND 4`; `jsonb_typeof(progress) = 'object'`; `state_version >= 0`; `status IN ('active','completed','failed','expired')`

### `encounters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` |

**Restrições únicas:** UNIQUE (`game_activity_id`)

### `equipment_items`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `source_key` | `VARCHAR(160)` | NOT NULL | — |
| `item_name` | `VARCHAR(120)` | NOT NULL | — |
| `rarity` | `VARCHAR(16)` | NOT NULL | — |
| `slot` | `VARCHAR(24)` | NOT NULL | — |
| `item_level` | `INTEGER` | NOT NULL | — |
| `bound` | `BOOLEAN` | NOT NULL | — |
| `payload` | `JSONB` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`source_key`)

### `exploration_attempts`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `local_id` | `VARCHAR(64)` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `category` | `VARCHAR(32)` | NOT NULL | — |
| `result_id` | `VARCHAR(96)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `progress` | `JSONB` | NOT NULL | — |
| `activity_id` | `UUID` | NULL | FK `game_activities.id` |
| `encounter_id` | `UUID` | NULL | FK `encounters.id` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `result_acknowledged` | `BOOLEAN` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `id`)

**Checks:** `state_version >= 0`; `status IN ('active','completed','failed')`

### `game_activities`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `content_id` | `VARCHAR(64)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `last_valid_action_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`id`, `character_id`)

**Checks:** `state_version >= 0`; `status IN ('active','completed','failed')`

### `group_activity_participants`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `proposal_id` | `UUID` | NOT NULL | PK; FK `group_activity_proposals.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `ordinal` | `INTEGER` | NOT NULL | — |
| `eligibility` | `VARCHAR(16)` | NOT NULL | — |
| `eligibility_fingerprint` | `VARCHAR(64)` | NULL | — |
| `eligibility_snapshot` | `JSONB` | NOT NULL | — |
| `response` | `VARCHAR(16)` | NOT NULL | — |
| `reservation_state` | `VARCHAR(16)` | NOT NULL | — |
| `responded_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `eligibility != 'ineligible' OR response = 'not_required'`; `eligibility = 'ineligible' OR response != 'not_required'`; `eligibility IN ('eligible','helper','ineligible')`; `eligibility_snapshot IS NULL OR jsonb_typeof(eligibility_snapshot) = 'object'`; `ordinal >= 0`; `reservation_state IN ('active','released')`; `response IN ('pending','accepted','declined','not_required')`

### `group_activity_proposals`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `group_id` | `UUID` | NOT NULL | FK `social_groups.id` (ON DELETE CASCADE) |
| `activity_type` | `VARCHAR(32)` | NOT NULL | — |
| `proposer_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `journey_reference_character_id` | `UUID` | NULL | FK `characters.id` (ON DELETE SET NULL) |
| `context_payload` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `cancel_reason` | `VARCHAR(48)` | NULL | — |
| `activity_reference` | `VARCHAR(96)` | NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `started_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `finished_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `activity_type <> ''`; `context_payload IS NULL OR jsonb_typeof(context_payload) = 'object'`; `expires_at > created_at`; `revision >= 0`; `status IN ('pending','ready','declined','expired','cancelled','started','completed','failed')`

### `group_hunt_encounters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `group_id` | `UUID` | NOT NULL | FK `social_groups.id` (ON DELETE CASCADE) |
| `proposal_id` | `UUID` | NOT NULL | FK `group_activity_proposals.id` (ON DELETE RESTRICT) |
| `local_id` | `VARCHAR(64)` | NOT NULL | — |
| `creature_id` | `VARCHAR(64)` | NOT NULL | — |
| `category` | `VARCHAR(16)` | NOT NULL | — |
| `enemy_level` | `INTEGER` | NOT NULL | — |
| `reference_level` | `INTEGER` | NOT NULL | — |
| `variant` | `VARCHAR(24)` | NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `roster_size` | `INTEGER` | NOT NULL | — |
| `scaling_snapshot` | `JSONB` | NOT NULL | — |
| `combat_id` | `UUID` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `combat_snapshot` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`combat_id`); UNIQUE (`proposal_id`)

**Checks:** `enemy_level >= 1`; `jsonb_typeof(combat_snapshot) = 'object'`; `jsonb_typeof(scaling_snapshot) = 'object'`; `reference_level >= 1`; `roster_size BETWEEN 2 AND 4`; `state_version >= 0`; `status IN ('active','completed','failed')`

### `group_hunt_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `group_hunt_encounter_id` | `UUID` | NOT NULL | PK; FK `group_hunt_encounters.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` (ON DELETE CASCADE) |
| `actor_key` | `VARCHAR(16)` | NOT NULL | — |
| `ordinal` | `INTEGER` | NOT NULL | — |
| `loot_seed` | `VARCHAR(128)` | NOT NULL | — |
| `consumable_uses` | `INTEGER` | NOT NULL | — |
| `settlement_state` | `VARCHAR(16)` | NOT NULL | — |
| `result` | `VARCHAR(16)` | NULL | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `settled_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`game_activity_id`); UNIQUE (`group_hunt_encounter_id`, `actor_key`)

**Checks:** `consumable_uses >= 0`; `ordinal BETWEEN 1 AND 4`; `settlement_state IN ('pending','settled')`

### `hunt_contexts`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `local_id` | `VARCHAR(64)` | NOT NULL | — |
| `creature_id` | `VARCHAR(64)` | NOT NULL | — |
| `category` | `VARCHAR(16)` | NOT NULL | — |
| `enemy_level` | `INTEGER` | NOT NULL | — |
| `variant` | `VARCHAR(24)` | NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `loot_profile` | `VARCHAR(32)` | NOT NULL | — |
| `pvpve_collision_id` | `UUID` | NULL | FK `pvpve_collisions.id` (ON DELETE SET NULL) |
| `pvpve_reference_level` | `INTEGER` | NULL | — |
| `pvpve_domain_eligible` | `BOOLEAN` | NOT NULL | — |
| `result_acknowledged` | `BOOLEAN` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`game_activity_id`)

**Checks:** `enemy_level >= 1`

### `hunt_round_encounters`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `round_id` | `UUID` | NOT NULL | FK `hunt_rounds.id` |
| `ordinal` | `INTEGER` | NOT NULL | — |
| `activity_id` | `UUID` | NULL | FK `game_activities.id` |
| `combat_id` | `UUID` | NOT NULL | — |
| `seed` | `VARCHAR(160)` | NOT NULL | — |
| `creature_id` | `VARCHAR(64)` | NOT NULL | — |
| `category` | `VARCHAR(16)` | NOT NULL | — |
| `enemy_level` | `INTEGER` | NOT NULL | — |
| `variant` | `VARCHAR(24)` | NULL | — |
| `status` | `VARCHAR(24)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `combat_snapshot` | `JSONB` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`activity_id`); UNIQUE (`combat_id`); UNIQUE (`round_id`, `ordinal`)

**Checks:** `enemy_level >= 1`; `ordinal >= 1`; `state_version >= 0`; `status IN ('materialized','completed','defeated','interrupted','elite_combat')`

### `hunt_rounds`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `activity_id` | `UUID` | NULL | FK `game_activities.id` |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `end_reason` | `VARCHAR(32)` | NULL | — |
| `batch_size` | `INTEGER` | NOT NULL | — |
| `completed_encounters` | `INTEGER` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `seed` | `VARCHAR(128)` | NOT NULL | — |
| `prepared_heal` | `BOOLEAN` | NOT NULL | — |
| `prepared_purify` | `BOOLEAN` | NOT NULL | — |
| `config_snapshot` | `JSONB` | NOT NULL | — |
| `cancel_requested` | `BOOLEAN` | NOT NULL | — |
| `next_resolution_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `result_acknowledged` | `BOOLEAN` | NOT NULL | — |
| `elite_engaged` | `BOOLEAN` | NOT NULL | — |
| `started_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`activity_id`)

**Checks:** `batch_size IN (5, 10, 20)`; `completed_encounters >= 0`; `state_version >= 0`; `status IN ('preparing','active','completed','cancelled','defeated','ended','interrupted')`

### `legacy_ascension_confirmations`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `confirmation_key` | `UUID` | NOT NULL | — |
| `expected_configuration_version` | `INTEGER` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`confirmation_key`)

**Checks:** `expected_configuration_version >= 0`; `expires_at > created_at`

### `legacy_ascensions`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `legacy_level_after` | `INTEGER` | NOT NULL | — |
| `character_level_before` | `INTEGER` | NOT NULL | — |
| `xp_before` | `BIGINT` | NOT NULL | — |
| `campaign_quest_id` | `VARCHAR(32)` | NOT NULL | — |
| `operation_key` | `UUID` | NOT NULL | — |
| `configuration_version_before` | `INTEGER` | NOT NULL | — |
| `ascended_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `legacy_level_after`); UNIQUE (`operation_key`)

**Checks:** `character_level_before = 60`; `configuration_version_before >= 0`; `legacy_level_after BETWEEN 1 AND 5`; `xp_before >= 0`

### `location_discoveries`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `location_id` | `VARCHAR(64)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `location_id`)

### `material_stacks`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `material_id` | `VARCHAR(96)` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |
| `bound` | `BOOLEAN` | NOT NULL | — |

**Checks:** `quantity BETWEEN 0 AND 999`

### `outbox_messages`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `topic` | `VARCHAR(100)` | NOT NULL | — |
| `dedup_key` | `VARCHAR(200)` | NOT NULL | — |
| `aggregate_key` | `VARCHAR(200)` | NULL | — |
| `payload` | `JSON` | NOT NULL | — |
| `status` | `VARCHAR(20)` | NOT NULL | — |
| `attempt_count` | `INTEGER` | NOT NULL | — |
| `last_error` | `TEXT` | NULL | — |
| `available_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `delivered_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`dedup_key`)

### `pending_items`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `source_key` | `VARCHAR(160)` | NOT NULL | — |
| `kind` | `VARCHAR(24)` | NOT NULL | — |
| `payload` | `JSONB` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `source_key`)

**Checks:** `quantity > 0`

### `pvpve_account_cooldowns`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `account_id` | `BIGINT` | NOT NULL | PK; FK `accounts.telegram_id` (ON DELETE CASCADE) |
| `pvp_until` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

### `pvpve_account_pairs`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `account_a` | `BIGINT` | NOT NULL | PK; FK `accounts.telegram_id` (ON DELETE CASCADE) |
| `account_b` | `BIGINT` | NOT NULL | PK; FK `accounts.telegram_id` (ON DELETE CASCADE) |
| `last_match_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |
| `domain_until` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `account_a < account_b`

### `pvpve_collision_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `collision_id` | `UUID` | NOT NULL | PK; FK `pvpve_collisions.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `account_id` | `BIGINT` | NOT NULL | FK `accounts.telegram_id` (ON DELETE CASCADE) |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` (ON DELETE CASCADE) |
| `actor_key` | `VARCHAR(16)` | NOT NULL | — |
| `side` | `VARCHAR(1)` | NOT NULL | — |
| `contributed` | `BOOLEAN` | NOT NULL | — |
| `domain_eligible` | `BOOLEAN` | NOT NULL | — |
| `round_takeover` | `BOOLEAN` | NOT NULL | — |
| `result_acknowledged` | `BOOLEAN` | NOT NULL | — |
| `prey_result` | `VARCHAR(16)` | NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `settled_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`collision_id`, `actor_key`); UNIQUE (`game_activity_id`)

**Checks:** `prey_result IS NULL OR prey_result IN ('victory','defeat')`; `side IN ('a','b')`; `status IN ('active','prey','defeated','settled')`

### `pvpve_collisions`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `local_id` | `VARCHAR(64)` | NOT NULL | — |
| `roster_size` | `INTEGER` | NOT NULL | — |
| `queue_a_id` | `UUID` | NOT NULL | FK `pvpve_queues.id` (ON DELETE RESTRICT) |
| `queue_b_id` | `UUID` | NOT NULL | FK `pvpve_queues.id` (ON DELETE RESTRICT) |
| `combat_id` | `UUID` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `combat_snapshot` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `winner_side` | `VARCHAR(1)` | NULL | — |
| `prey_reference_level` | `INTEGER` | NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`combat_id`); UNIQUE (`queue_a_id`); UNIQUE (`queue_b_id`)

**Checks:** `jsonb_typeof(combat_snapshot) = 'object'`; `roster_size BETWEEN 1 AND 4`; `state_version >= 0`; `status IN ('active','prey','completed','failed')`; `winner_side IS NULL OR winner_side IN ('a','b')`

### `pvpve_domain_grants`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `collision_id` | `UUID` | NOT NULL | PK; FK `pvpve_collisions.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `crowns` | `BIGINT` | NOT NULL | — |
| `material_id` | `VARCHAR(96)` | NULL | — |
| `status` | `VARCHAR(24)` | NOT NULL | — |
| `granted_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `crowns >= 0`; `status IN ('granted','locked','no_economic_reward','no_opponent')`

### `pvpve_queue_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `queue_id` | `UUID` | NOT NULL | PK; FK `pvpve_queues.id` (ON DELETE CASCADE) |
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `account_id` | `BIGINT` | NOT NULL | FK `accounts.telegram_id` (ON DELETE CASCADE) |
| `game_activity_id` | `UUID` | NOT NULL | FK `game_activities.id` (ON DELETE CASCADE) |
| `actor_key` | `VARCHAR(16)` | NOT NULL | — |
| `ordinal` | `INTEGER` | NOT NULL | — |

**Checks:** `ordinal BETWEEN 1 AND 4`

### `pvpve_queues`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `local_id` | `VARCHAR(64)` | NOT NULL | — |
| `roster_size` | `INTEGER` | NOT NULL | — |
| `source_type` | `VARCHAR(16)` | NOT NULL | — |
| `group_id` | `UUID` | NULL | FK `social_groups.id` (ON DELETE SET NULL) |
| `proposal_id` | `UUID` | NULL | FK `group_activity_proposals.id` (ON DELETE SET NULL) |
| `roster_snapshot` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Restrições únicas:** UNIQUE (`proposal_id`)

**Checks:** `jsonb_typeof(roster_snapshot) = 'array'`; `roster_size BETWEEN 1 AND 4`; `source_type IN ('manual','group','round')`; `status IN ('waiting','matched','expired','cancelled')`

### `quests`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `quest_id` | `VARCHAR(32)` | NOT NULL | — |
| `title` | `VARCHAR(120)` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `step` | `INTEGER` | NOT NULL | — |
| `content_version` | `VARCHAR(32)` | NOT NULL | — |
| `state_version` | `BIGINT` | NOT NULL | — |
| `progress` | `JSONB` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `quest_id`)

**Checks:** `state_version >= 0`; `status IN ('active','completed','abandoned')`; `step >= 1`

### `reward_components`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `reward_event_id` | `UUID` | NOT NULL | FK `reward_events.id` |
| `kind` | `VARCHAR(32)` | NOT NULL | — |
| `item_id` | `VARCHAR(96)` | NULL | — |
| `quantity` | `BIGINT` | NOT NULL | — |
| `payload` | `JSONB` | NOT NULL | — |

### `reward_events`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `source_id` | `VARCHAR(96)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `source_id`)

### `reward_grants`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `game_activity_id` | `UUID` | NOT NULL | PK; FK `game_activities.id` |
| `character_id` | `UUID` | NOT NULL | FK `characters.id`; FK `game_activities.character_id` |
| `xp` | `BIGINT` | NOT NULL | — |
| `ruleset_version` | `VARCHAR(48)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `xp >= 0`

### `rune_stacks`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `family` | `VARCHAR(32)` | NOT NULL | — |
| `rarity` | `VARCHAR(16)` | NOT NULL | — |
| `grade` | `INTEGER` | NOT NULL | — |
| `potency` | `VARCHAR(24)` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |
| `bound` | `BOOLEAN` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `family`, `rarity`, `grade`, `bound`)

### `social_group_invites`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `group_id` | `UUID` | NOT NULL | FK `social_groups.id` (ON DELETE CASCADE) |
| `inviter_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `invitee_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `responded_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `revision >= 0`; `status IN ('pending','accepted','declined','cancelled','expired')`

### `social_group_members`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` (ON DELETE CASCADE) |
| `group_id` | `UUID` | NOT NULL | FK `social_groups.id` (ON DELETE CASCADE) |
| `joined_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

### `social_groups`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `server_id` | `VARCHAR(64)` | NOT NULL | — |
| `leader_character_id` | `UUID` | NOT NULL | FK `characters.id` (ON DELETE CASCADE) |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `revision` | `INTEGER` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Checks:** `revision >= 0`; `status IN ('active','disbanded')`

### `unlocks`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `unlock_id` | `VARCHAR(96)` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `unlock_id`)

### `warehouse_equipment_items`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `source_key` | `VARCHAR(160)` | NOT NULL | — |
| `item_name` | `VARCHAR(120)` | NOT NULL | — |
| `rarity` | `VARCHAR(16)` | NOT NULL | — |
| `slot` | `VARCHAR(24)` | NOT NULL | — |
| `item_level` | `INTEGER` | NOT NULL | — |
| `bound` | `BOOLEAN` | NOT NULL | — |
| `payload` | `JSONB` | NOT NULL | — |
| `stored_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |

**Restrições únicas:** UNIQUE (`character_id`, `source_key`)

### `warehouse_material_stacks`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `material_id` | `VARCHAR(96)` | NOT NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |
| `bound` | `BOOLEAN` | NOT NULL | — |

**Checks:** `quantity BETWEEN 1 AND 999`

### `warehouse_operations`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `id` | `UUID` | NOT NULL | PK |
| `character_id` | `UUID` | NOT NULL | FK `characters.id` |
| `direction` | `VARCHAR(20)` | NOT NULL | — |
| `kind` | `VARCHAR(16)` | NOT NULL | — |
| `source_id` | `VARCHAR(64)` | NOT NULL | — |
| `source_key` | `VARCHAR(160)` | NULL | — |
| `quantity` | `INTEGER` | NOT NULL | — |
| `fingerprint` | `VARCHAR(64)` | NOT NULL | — |
| `snapshot` | `JSONB` | NOT NULL | — |
| `status` | `VARCHAR(16)` | NOT NULL | — |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `expires_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | — |
| `completed_at` | `TIMESTAMP WITH TIME ZONE` | NULL | — |

**Checks:** `direction IN ('deposit','withdraw','claim_pending')`; `kind IN ('equipment','material','rune','consumable')`; `quantity > 0`; `status IN ('preview','committed','cancelled','stale','expired')`

### `world_states`

| Coluna | Tipo PostgreSQL | Nulabilidade | Chave/relacionamento |
|---|---|---|---|
| `character_id` | `UUID` | NOT NULL | PK; FK `characters.id` |
| `region` | `VARCHAR(64)` | NOT NULL | — |
| `location` | `VARCHAR(64)` | NOT NULL | — |


## 6. Sistemas do jogo e regras atuais

Os valores abaixo são os encontrados no código e nas fontes vigentes. Conteúdo regional tem pools grandes de criatura, materiais, receitas e encontros; para os valores individuais, consulte o arquivo regional indicado em `SOURCE_AUTHORITY.md` e os catálogos de `domain/road.py`, `domain/professions.py` e módulos `*_dungeon.py`. Não copie propostas candidatas como balanceamento publicado.

### Criação, mundo e campanha

- Cinco raças e seis classes, conforme `domain/creation.py`; a tela `/start` persiste cada passo no banco e pode ser retomada. Uma conta Telegram por servidor tem um personagem.
- O fluxo implementado descrito no README começa em `/start`, nome, raça, classe, confirmação, prólogo `Cinzas na Estrada`, primeiro combate, Braseiro e Menu Principal. O combate do prólogo tem resultado de vitória ou derrota; a recompensa tutorial de 320 XP é apenas para vitória, segundo o GDD.
- Campanha modular por missão/região. O código contém serviços para P1–P36 (com agrupamento em `p1`–`p7`, `vde_missions`, `nareth_missions`, `varzeas_missions`, `altos_missions` e módulos de etapas `s*`). Isso é evidência de implementação no checkout, não declaração de que cada etapa foi validada contra fonte/release.
- Regiões autoritativas listadas no índice: Terras do Ocaso Nv.1–10; Vales dos Enforcados Nv.11–20; Planícies de Nareth Nv.21–30; Várzeas Carmesins Nv.31–40; Altos Cinéreos Nv.41–50; Confins do Véu Nv.51–60.

### Combate, atributos e evolução

- Combate por turnos; AGI resolve iniciativa, com desempate determinístico no começo do encontro. A baseline atual é `gdd-1.4.9-baseline-1.0` em `domain/combat_math.py`.
- Curva de crescimento de classe: `G(L) = 4^((L−60)/59)`, para Nv.1–60. Valores base no Nv.60 (`HP / ATQ / DEF / AGI`): Sentinela `2808/368/324/276`; Errante `2470/424/282/330`; Vigia `2522/420/288/321`; Tecelão `2418/436/273/300`; Oráculo `2574/400/291/309`; Luminar `2678/384/309/288`.
- Modificadores raciais atualmente codificados: Remanescente multiplica todos os quatro atributos primários por `1,015`; Alvorano multiplica AGI por `1,05`; as outras raças não alteram esses atributos nessa função.
- Composição estática: atributos base → percentuais do Caminho (aplicados à parcela de classe) → percentuais de Talento → equipamento → percentuais e pontos de Runa → percentuais e pontos de Encantamento → raça → uma finalização `ROUND_HALF_UP` dos quatro atributos primários. Secundários (PER, crítico, esquiva, bloqueio) são pontos percentuais.
- Defesa: redução natural `DEF / (DEF + 100 + 5 × nível do atacante)`. PER reduz DEF efetiva em até 30 pontos percentuais. Mitigações ativas combinam multiplicativamente, com teto de 65%. Dano direto = `floor(ATQ × coeficiente × fator crítico × (1 − redução DEF) × (1 − mitigação ativa))`; crítico é `×1,5`; dano mínimo 1 salvo ação explicitamente zero. DoT usa snapshot de ATQ, não crita e calcula redução usando 50% da DEF efetiva.
- XP por nível em `application/progression.py`: requisito para avançar a partir do nível `L` = `ROUND_HALF_UP_100(4000 + 750L + 43L²)`. XP é progresso dentro do nível; consolidação ocorre em fronteira de atividade válida. Nível máximo 60; excedente ao cap é descartado.
- A Baseline numérica está fechada pelo GDD v1.6.0. Não reequilibrar estes valores sem revisão da autoridade documental.

### Economia, Vigor, Caçada, Ronda e Desbravar

- `domain/economy.py::crowns_per_level(L) = round_10(100 + 15L)`; arredondamento em dezenas é `ROUND_HALF_EVEN`. Troca de Caminho custa `round_10(1,5 × coroas_por_nível)`.
- XP inimigo (`domain/road.py::enemy_xp`): `XP(L)=round_100(4000+750L+43L²)` com half-even; `H(L)=0,905903+0,094097L`; recompensa bruta arredondada a dezenas half-even de `XP(L)/(20×H(L)) × fator_categoria × fator_delta_nível × fatores de powerlevel/participação/Vigor/Legado`. Fatores por categoria: comum 1,00; incomum 1,35; elite 2,75; chefe 6,00. Diferença nível inimigo−jogador: `≥+5:1,10`; `+3/+4:1,05`; `−2…+2:1,00`; `−3…−5:0,80`; `−6…−10:0,50`; `−11…−20:0,20`; `≤−21:0,05`.
- Coroas por categoria em `domain/road.py`: valor base `100+15L` multiplicado por comum `0,05`, incomum `0,08`, elite `0,25`, chefe `0,60`, com arredondamento a dezenas half-even.
- Vigor máximo 100; regeneração de 1 ponto a cada 14 min 24 s (864 s), com fração do intervalo carregada enquanto abaixo do cap; tempo no cap/futuro é descartado (`application/vigor.py`). Novo personagem parte com 100/100 conforme criação.
- Poção de Vigor restaura 20, só pode ser usada com Vigor `≤80`, ciclo diário às 06:00 `America/Sao_Paulo` (`domain/consumables.py`, `application/consumables.py`).
- Caçada manual e Desbravar são atividades por local, com gates de descoberta/missão e tabelas/pools por região em `domain/road.py`. Saque e escolhas usam seeds determinísticos; resultados de exploração respeitam categorias/subpesos, disponibilidade e anti-repetição.
- Ronda: lote finito de 5/10/20 encontros (preparação e serviço em `application/round.py`); cadência de 3 minutos por encontro; custo econômico de 2 Vigor por encontro segundo GDD. A configuração de combate e os consumíveis escolhidos ficam snapshotados pelo lote. Há limites/heurísticas de cura e segurança em `round.py` (`SAFETY_THRESHOLD=0,35`, recuperação `0,50`, crítico `0,30`, cura mínima efetiva `0,10`). Scheduler processa vencimentos a cada 15 s. Interrupções evitam consumir o lote sem condição válida.

### Itens, consumíveis, inventário e crafting

- Famílias de consumíveis: cura, purificação, antídoto, Vigor, proteção, dissipador e proteção contra efeitos (warding). Política atual: cura restaura `22%` do HP máximo; purificação remove 1 efeito negativo; antídoto remove todos os stacks de DoT; proteção cria barreira `floor(12% HP máximo)` por 2 turnos; dissipador remove 1 positivo do inimigo (stack mais antigo); warding dá 1 carga por 2 turnos. Consumíveis de combate compartilham cooldown group `consumable`; elegibilidade para Ronda varia por família.
- Ofícios: Ferreiro, Artífice, Alquimista, Curteiro e Joalheiro. Um slot primário tem cap de nível 30; secundário, 15. Graus 1–6 abrem nos níveis 1, 3, 6, 9, 12 e 15. PXP de transição é `round_10(100+20L+5L²)`; ganho por receita é `(80+20×nível_requerido) × multiplicador/100`. O multiplicador é 100% quando o grau da receita é igual/superior ao grau atual do Ofício; cai para 50% se a receita estiver um grau abaixo, 20% dois graus abaixo e 0% três ou mais abaixo. Receitas/custos são regionais e vivem em `domain/professions.py` e `domain/consumables.py`.
- Equipamentos, slots, raridades, aprimoramentos, Runas/Encantamentos e compatibilidade de arma estão em `domain/equipment*.py` e `weapon_metadata.py`. O contrato global v1.0.0 é vigente para `weapon_form`, `handedness`, slot e tags explícitas; `weapon_family` não deve ser armazenado nem inferido.
- A migration 0032 e os arquivos de capacidade/Armazém estão WIP local: os valores codificados são inventário 60 slots, Armazém 100 e pendentes 20; stacks de material 999, consumíveis 99; operação de confirmação expira em 5 min; transferência por inteiro de equipamento/material; acesso exige estar num Braseiro permanente descoberto. Runas/consumíveis não aparecem como conteúdo transferível neste serviço.

### Masmorras, grupos e Legado

- Há 12 famílias de dungeon no código, duas por região: Cripta do Ocaso/Galerias do Vigia; Fosso das Raízes/Santuário do Nó Antigo; Galerias do Meridiano/Observatório Afundado; Enfermaria Afundada/Cisterna de Transferência; Pedreira do Contrapeso/Bastilha Profunda; Arquivo do Retorno/Câmara das Contradições.
- Perfil global de dificuldade em `domain/dungeons.py`:

| Dificuldade | Vigor | Limite de consumíveis | Braseiro | Ref. Nv. / duração / eficiência | Fator Coroas | Básicos / catalisadores / núcleos / fragmentos | Runa / receita | Pressão inicial | Chefe HP/ATQ |
|---|---:|---:|---|---|---:|---|---|---:|---|
| Estável | 25 | 6 | 70% | 6 / 30 min / 1,00 | 0,80 | 8 / 2 / 1 / 2 | 20% / 8% | 12 | 1,00 / 1,00 |
| Fraturada | 35 | 5 | 40% | 6 / 35 min / 1,05 | 1,20 | 11 / 3 / 2 / 4 | 35% / 15% | 10 | 1,15 / 1,08 |
| Ruptura | 50 | 4 | 20% | 60 / 42,5 min / 1,10 | 1,80 | 14 / 4 / 4 / 7 | 50% / 25% | 8 | 1,30 / 1,15 |

  XP de conclusão usa `H(L)=0,905903+0,094097L`, a curva `4000+750L+43L²` arredondada a centena half-even e `duração/60 × eficiência`; primeiro clear multiplica XP por `1,60`, Legado aplica seu fator, e o total fecha em dezenas half-even. Coroas usam `100+15×nível de referência` multiplicado pelo fator da dificuldade. Distribuição de raridade de equipamento (Comum/Raro/Épico/Lendário/Mítico) é 25/50/22/2,8/0,2% em Estável; 10/45/38/6,5/0,5% em Fraturada; 0/20/60/19/1% em Ruptura. A tabela é de peso em 10.000. Faixas de raridade das Runas (Rara/Épica/Lendária) são 70/28/2%, 55/40/5% e 35/55/10% nessas dificuldades. Runs persistem estado, grupo/lobby, ready check, checkpoint/Braseiro, retry e resolução/recompensas.
- `groups.py`, `campaign_coop.py`, `group_hunts.py` suportam grupos, convites persistentes/expiráveis, jornadas e caçadas em grupo. `pvpve.py` é colisão PvP-vs-PvE ligada a caçadas/fila; não significa que Duelo, Arena ranked ou GvG estejam implementados.
- Guildas (§30, núcleo, migration `20261107_0034`): `domain/guilds.py` e `application/guilds.py`, com tabelas `guilds`, `guild_members`, `guild_invites`, `guild_applications`, `guild_switch_cooldowns` e `guild_audit_log`. Cobre fundação gratuita, cargos, Convites sem TTL, Recrutamento Aberto/Fechado, Inscrições com limites da §49.18, Procurar Guilda, página pública, expulsão, saída e recarga de 12h por conta+servidor. Ordem de lock: Guilda → Personagem → convites/inscrições. Decisões do autor: toda saída (inclusive expulsão) e a fundação respeitam a recarga; o Líder não sai sem transferir. Telas em `bot/guilds_handlers.py`/`guilds_ui.py`.
- Guildas §30.2–§30.3 (migration `20261108_0036`, manutenção em `application/guild_upkeep.py`): Tesouraria com ledger (`guild_treasury_ledger`), depósitos finais, 7 Obras com níveis I–V e custos/tempos da §49.10 (`guild_projects`, `guild_project_contributions`; só Alojamentos tem efeito, as outras 6 ainda sem efeito por decisão do autor), contribuição da carteira (qualquer membro) ou da Tesouraria (só Líder), limitada ao restante; Renome 15.000 da Tesouraria com recarga de 30 dias e Nome/TAG antigos reservados 30 dias (`guild_name_history`); Dissolução com 72h, congelamento, perda explícita do saldo e do Financiamento, espera Construção terminar; Sucessão após 168h sem atividade (`guild_members.last_active_at`, ordem da §49.18); exclusão de Líder passa a liderança ou dissolve se ele era o único membro. A manutenção roda de forma preguiçosa antes de cada ação e no job `guild-upkeep` (a cada 60s) de `bot/round_scheduler.py`, que chama `GuildService.run_maintenance()`. A atividade autenticada vem de `bot/guild_activity.py` (middleware de update, no máximo uma gravação por jogador por minuto). Telas em `guilds_ui.py`: "Tesouraria e Obras" (depositar, contribuir pela carteira ou pela Tesouraria, iniciar Obra), Renomear e Dissolver/Cancelar dissolução (só Líder); o candidato recebe aviso no Telegram quando a Inscrição é aprovada ou recusada. `GuildService.handle_permanent_ban()` é o gancho para a futura moderação: sucessão imediata, e o Líder banido vira Membro. `delete_character_owned_data` agora ignora FKs `ON DELETE SET NULL` (antes apagava auditoria e convites de terceiros). Fora daqui: sistema de ban em si, efeitos das 6 Obras, Juramento/Expedição/GvG (etapas 7–8).
- Eventos Mundiais §21/§49.15 (migration `20261108_0040`): `domain/world_events.py` (agenda, escala por fase, elegibilidade, Sintonização), `application/world_events.py` (ordem de bloqueio Character → Occurrence → Participation → ConsumableStack; o HP do Chefe só muda sob o lock da ocorrência) e `bot/world_event_*`. O `WORLD_EVENT_CATALOG` está vazio de propósito: a fonte não nomeia nenhum Evento, e sem catálogo nada é agendado. Decisões do autor em 2026-11-08: reunião de 5 min antes da Fase 1, base do Chefe igual à do Chefe de Masmorra Solo, Ação Significativa = dano, cura ou Barreira, `major_contribution` = golpe que encerra a fase, 10 Vigor reservados e devolvidos sem recompensa, não alimenta Recentes. A participação tem HP próprio e não altera `Character.hp`.
- Legado: fator XP por nível 0→5: `1,00`, `1,75`, `2,00`, `2,25`, `2,50`, `2,75`. O fluxo implementado só permite a primeira ascensão (personagem ainda no Legado 0), no Nv.60, após P36 estar completa e comprovada por Quest + unlock + evento de recompensa, no Braseiro permanente do Refúgio do Ocaso e sem atividade incompatível. A confirmação é single-use, vinculada à versão da configuração de combate e expira em 10 minutos; a mutação é transacional/idempotente. O serviço marca transições de ranks acima de 0 como `legacy_transition_undefined`; não presumir ciclos de ascensão implementados só porque há fatores definidos até 5.
- Batalha de Guildas §15/§49.14 (migration `20261109_0042`, regras em `domain/guild_battle.py`, caso de uso em `application/guild_battle.py`, travas lidas por outros serviços em `application/guild_battle_locks.py`): quarta e domingo 21:00 (America/Sao_Paulo); Inscrição só pelo Líder de 24h antes até 20:30 (Frente I 2v2, Frente II 3v3, Campeão entre os 5, até 2 reservas, todos Nv.30 atual); pareamento às 20:30 por rating técnico vizinho, bye para a Guilda com menos byes, depois menor rating, depois menor id; Confirmação de Entrada de 20:30 a 20:50 cria a `GameActivity` `guild_battle`, que trava a Configuração de Combate até o fim da frente (ou da Batalha, para o Campeão); reserva substitui combatente não confirmado até 20:50 e herda a vaga e o papel de Campeão; frentes simultâneas às 21:00, turno 60s, AFK retira só o jogador (`withdraw_fighter` em `domain/combat.py`), sem rendição; lado com combatente não confirmado perde a frente, os dois ausentes = 0/0; empate em pontos leva ao Campeão 1v1 com HP cheio; rating Elo da Arena (K48 nas 5 primeiras batalhas reais, depois K32, sem piso) e classificação 3/1/0, bye 0, desempate por rating e depois id. Roster travado do pareamento ao resultado: sair/ser removido da Guilda (`guild_battle_roster_locked`) e Ascensão são bloqueados; dissolução final espera Inscrição ou Batalha em aberto; contas ligadas na mesma luta geram flag `guild_battle` (§36). Decisões do autor em 2026-11-09 estão no docstring do domínio. Telas do Telegram em `bot/guild_battle_handlers.py`/`bot/guild_battle_ui.py` (entrada pela tela de Guilda, callbacks `gb:*` e combate `gbf:*`; o rascunho da Inscrição viaja no callback como índices dos membros Nv.30+ com fingerprint e recomeça se a lista mudar) e job `guild-battle-upkeep` (5s) no `round_scheduler.py`. Decisões do autor em 2026-11-09 para as telas: aviso de pareamento e turnos de combate seguem a categoria Essenciais, bye/fim de frente/resultado seguem a categoria competitiva (`notice_category`); a Classificação oculta o rating técnico e mostra o top 10 + a própria Guilda; o `{Flavor curto}` da UI §48.3 fica omitido até o autor escrever os textos. Ainda fora: entrega de recompensas (só classificação e elegibilidade: 10 batalhas reais por Guilda, 4 participações por jogador) e corte por Crônica (não existe sistema de Crônica; o perfil acumula como na Arena).

## 7. Comandos, menus e callbacks inline

Os routers são orientados a chat privado. Comandos reconhecidos no código atual:

| Comando | Ação |
|---|---|
| `/start` | Recupera personagem/atividade ou inicia/retoma criação persistente. |
| `/menu` | Volta ao menu principal quando há personagem; os handlers também protegem telas pendentes de conta. |
| `/perfil` | Exibe perfil persistido do personagem. |
| `/ajuda` | Abre raiz da ajuda e tópicos navegáveis. |
| `/cancelar` | Cancela apenas entrada textual transitória pendente; não cancela atividade/progresso. |
| `/grupo` | Abre o menu de Grupo. |
| `/grupo convidar <nome do personagem>` | Envia convite ao personagem indicado; convite expira em 10 minutos. |
| `/dungeon_invite <nome exato do personagem>` | Convida personagem para o lobby/run de masmorra ativa. |

`/reiniciar` aparece em documentação histórica, mas não há handler de comando correspondente no código atual.

### Menus principais visíveis

- **Menu principal:** Aventura (`world:adventure`), Personagem (`character:root`), Códice (`knowledge:codex`), Vínculos (`links:root`), Configurações (`settings:root`), Legado (`legacy:root`).
- **Aventura:** Local Atual (`world:local`), Mapa (`world:map`), Missões (`world:missions`), Masmorras (`dungeon:known`), voltar ao Menu (`menu:back`).
- **Personagem:** Inventário, Equipamentos, Artes, Talentos, Atributos, Ofícios, Perfil, Caminho, Doutrinas, Cosméticos e voltar. Os valores `callback_data` são definidos em `bot/character_ui.py`.
- **Braseiro:** `Descansar` (`world:rest`) restaura HP conforme regras do serviço; viagem entre braseiros usa telas de mapa/rota.

### Catálogo de callbacks inline

As telas constroem callbacks dinâmicos (IDs de entidade, versão/revisão, estado, etapa de missão); a lista abaixo enumera as famílias registradas no checkout e sua finalidade. Os routers/contratos de payload ficam nos módulos citados. Ações precisam sempre voltar ao serviço para validação de permissão/revisão.

| Família de callback | Módulos/ações |
|---|---|
| `cc:*`, `prologue:continue` | `creation_handlers.py`, `creation_ui.py`: etapas e confirmação de criação; seguir/retomar prólogo. |
| `fight:*`, `p1fight:*`, `p2fight:*`, `p3fight:*`, `p4fight:*`, `p5fight:*`, `p6fight:*`, `s2fight:*`, `s3fight:*`, `s4fight:*`, `s5fight:*`, `s6fight:*`, `df:*`, `vsc:*` | `combat_handlers.py` e handlers de missão/dungeon: ações de turno, alvos, fluxos especiais cooperativos e combate de dungeon. Há payloads específicos de missão/instância. |
| `p1:*`…`p7:*`, `s1:*`…`s6:*`, `s25:*`…`s36:*`, `vde:*`, `nareth:*`, `varzeas:*`, `altos:*`, `asc:*` | handlers/UI de campanha e side quests: avançar etapa, escolha, confirmação e encontro roteirizado; `asc:*` cobre ação contextual associada a conteúdo Altos/Confins. |
| `character:*`, `profile:edit:*`, `tal:*`, `art:*`, `path:*`, `trial:*`, `trialact:*` | telas de personagem, atributos/perfil, redistribuição/aprendizado de Talentos, slots de Arte ativa, troca de Caminho e prova de Classe. |
| `eq:*`, `em:*`, `inventory:*`, `consumable:vigor`, `cu:*`, `cf:*` | equipar/inspecionar/selecionar itens, aprimorar/modificar, categorias/uso de consumível e confirmação do fluxo de uso. |
| `prof:*`, `craft:*` | escolha/troca de slots de Ofício, confirmação, lista de receitas, inspeção e confirmação de craft. |
| `warehouse:*`, `pending:*` | abrir Armazém, inventário, depósito/retirada, confirmar/cancelar; entrega pendente, reivindicar ou tentar novamente. Esses callbacks pertencem à alteração WIP nesta branch. |
| `cos:*`, `doc:*` | cosméticos e Doutrinas. |
| `dungeon:known`, `dungeon:group`, `dungeon:queue`, `dungeon:ready`, `dungeon:conf`, `dungeon:inv`, `dungeon:cancel`, `dungeon:start:*`, `dungeon:e:*`, `dungeon:b:*`, `dungeon:r:*`, `dungeon:confirm:*`, `dungeon:a:*`, `dungeon:back`, `dungeon:noop`, `df:*` | conhecer dungeon, lobby/grupo, fila, pronto, configuração, convite/cancelamento, iniciar solo/run por família e dificuldade (`s` Estável, `f` Fraturada, `r` Ruptura), escolher/navegar e agir durante combate. |
| `links:root`, `group:root`, `group:create`, `group:inbox`, `group:invite:*`, `group:leave:*`, `group:kick:*`, `group:lead:*`, `group:hunt:open`, `group:hunt:t:*`, `group:hunt:p:*`, `group:proposal:*` | tela de Vínculos/Grupo, criar grupo, caixa de entrada, convite aceitar/recusar, sair/remover/promover, abrir/propor Caçada em Grupo e confirmar proposta. |
| `world:rest`, `world:rest:*`, `world:adventure`, `world:missions`, `world:oren`, `world:principal`, `world:objective`, `world:local`, `world:round`, `world:map`, `world:map:region:*`, `world:map:local:*`, `world:travel`, `world:travel:to:*`, `road:hunt`, `road:pvpve:refresh`, `road:prepare`, `road:repeat`, `road:local`, `road:explore`, `road:explore:start`, `road:round:new`, `road:route`, `road:travel`, `road:takeover`, `prepare:view`, `cons`, `toggle`, `start`, `cancel`, `elite`, `back`, `continue`, `legacy:root`, `legacy:prepare:*`, `legacy:cancel:*`, `legacy:confirm:*`, `menu:back` | aventura, descanso, mapa/região/local, viagem, missões/objetivos/Oren, preparar/repetir/iniciar Caçada/Ronda/Desbravar, atualizar fila PvPvE, takeover/cancelamento e confirmação de ascensão. |
| `settings:*`, `help:*`, `account:*`, `kb:*` | preferências/notificações, ajuda, renome/entrada/confirmar/cancelar exclusão de conta/personagem e navegação do Códice. |

Os nomes literais de botões por contexto podem mudar conforme estado e disponibilidade; consulte `*_ui.py` e não reutilize callback antigo como contrato público de API.

## 8. Estado atual do projeto

### O que existe no código

- Fundação executável: API FastAPI, bot Aiogram (polling/webhook), criação persistente, prólogo e menu.
- Aventura/região: serviços e handlers de campanhas, mundo, missões, navegação, Caçada manual, Ronda agendada e Desbravar. No checkout há módulos até P36 e side-content S36, mas o estado de release de cada módulo não está comprovado.
- Combate por turnos persistente, configuração travada para atividades, talentos/artes/caminhos, consumíveis e conteúdo de inimigos/bosses.
- Inventário, equipamento, modificações, crafting/ofícios, cosméticos, doutrinas, códice, Legado, masmorras por região, grupos, campanha cooperativa, caçadas de grupo e PvPvE.
- Persistência SQLAlchemy/Alembic, testes unitários/integração e CI declarados.

### Em andamento ou não integrado

1. **Armazém/capacidade:** alterações locais em `inventory_capacity.py`, `safe_location.py`, `warehouse.py`, `warehouse_ui.py`, `models.py` e migration 0032. Migration, implementação, UI e teste `test_warehouse_integration.py` estão sem commit. Estado do banco local/remoto não foi consultado.
2. **Fase 2E — proficiências/equipamentos:** branch e pacote v1.9.1 contêm documentação candidata. O README do pacote diz “não canônico, não publicado, não pronto para importação ou integração operacional”. Três decisões de Game Design ainda estão abertas: identidade/ID de templates e release snapshot (0/226 IDs verificados); contratos/saídas de receitas e itens; elegibilidade individual de Saque (24 pares excluídos, 63 evidências favoráveis ainda não finais e 633 combinações pendentes). Há 160 vínculos existentes + 198 propostas de receita/output sem validação de release; 24 recompensas de campanha não reconciliadas com identidade publicada. GDD v1.6.0 e contrato Weapon Metadata v1.0.0 permanecem as fontes da raiz.
3. **Assets:** há diretório `assets/` local não rastreado. `config.py` aceita Telegram `file_id` ou `file:` path, mas o Dockerfile não empacota `assets/`. Assets não são considerados bundle oficial até revisar procedência e versionamento.
4. **Autoridade regional divergente:** `SOURCE_AUTHORITY.md` da raiz seleciona Terras do Ocaso v1.0.16. Uma worktree local de Phase 2B aponta v1.0.17 como alvo aprovado, ainda não operacional. Resolver e publicar por processo documental antes de usar no conteúdo.

O GDD também especifica Duelo/Arena ranked, Batalha de Guildas (GvG), Eventos Públicos/Sintonização do Véu, Juramento/Expedição, Mercado/Loja Pessoal, Trade direto e Guildas. Não foram encontrados módulos de aplicação/routers correspondentes a esses sistemas completos neste checkout; Grupo, Caçada em Grupo e colisão PvPvE são funcionalidades diferentes e parciais, não substitutos para todos eles.

### Quebrado/bugs conhecidos

Não foi feito teste de execução, migração em banco ou leitura de issue tracker nesta auditoria; portanto, não há base para declarar “sem bugs” nem para confirmar um bug reproduzível específico. O que está objetivamente pendente são as integrações/gates acima, o risco de scheduler duplicado em deployment multi-réplica, a ausência de worker de Outbox localizado e a divergência entre fontes de design. Trate como **não verificado** o resultado da suíte e o funcionamento do código alterado localmente. O `README.md` também está desatualizado: seu resumo cita TDO v1.0.15, não lista Nareth e aponta uma meta inicial P1, enquanto `SOURCE_AUTHORITY.md` da raiz seleciona conteúdo até Confins e o código já cobre sistemas além da fundação.

### Git e estado do checkout

- Branch atual `docs/asterion-proficiency-equipment-v1.9.0`; `HEAD 5abfb64`, commit local de documentação Fase 2E. Branch `main` local está em `7f67903`; o ref local `origin/main` em `d76b420` é de 2026-10-14 e não foi atualizado por fetch durante a auditoria.
- Um único remote configurado: `origin` (URL no cabeçalho). Sem tags Git observadas. O histórico da branch excede o ref remoto local, mas não inferir estado atual do GitHub a partir de refs sem fetch.
- Há muitas modificações rastreadas em `src/asterion/**`, `tests/**` e no manifesto Fase 2E, além de arquivos novos e `.worktrees/`. Leia `git status --short` e `git diff` antes de alternar branch, resetar, limpar ou criar commit. Não descarte os arquivos locais inadvertidamente.

### Status do Beta (atualizado em 2026-11-09)

O plano de lançamento é o backlog da auditoria Fase 4A (`docs/audits/ASTERION_AUDITORIA_GLOBAL_LANCAMENTO_FASE4A.md`, seção H). A numeração "etapa N do Beta" aparece nos PRs desde a saída do Codex.

| Etapa | Entregue | PR |
|---|---|---|
| (antes) | Legado (Ascensão transacional e XP de reprogressão), Armazém | #95, #96 |
| 1–2 | Guildas (núcleo, telas, Tesouraria, Obras, Dissolução, Sucessão) e flags de multicontas (§36) | #97, #98, #99 |
| 3 | Mercado, Loja Pessoal e Troca Direta | #100 |
| 4 | Duelo e Arena da Vigília | #101 |
| 5 | Vínculos, Relatos, Dádiva, Chamado, Códigos e Comunidade | #102 |
| 6 | Eventos Mundiais (catálogo vazio de propósito) | #103 |
| 7 | Juramento e Expedição (catálogos vazios de propósito) | #104 |
| 8 | Batalha de Guildas (núcleo e telas) | #105, #106 |
| 9 (bloco A) | Crônica I (ciclo, calendário, voto), Nova Vigília, Trilha da Crônica, fechamento competitivo de Arena e Batalha de Guildas, Salão da Vigília | branch `claude/cronica-ecos-convergencia-s8fs2t` |

Os números 1 e 2 não aparecem nos PRs; a divisão acima é inferida pela ordem.

**Sistemas de jogo que faltam** (conferido no código em 2026-11-09):

- Crônica I "Ecos da Convergência": o bloco A da etapa 9 entregou o sistema (ver "Etapa 9 · bloco A" abaixo). Falta o conteúdo jogável dos capítulos (bloco B).
- Passe da Crônica: a camada Premium existe, mas só é ativada pelo operador (`chronicle_cli pass-grant`), porque ainda não há provedor de pagamento.
- Serviços de Ofícios entre jogadores (§27.3): não existe; ficou fora da etapa 3.
- Marcas de Legado (§16.1): não existem; a Ascensão existe.
- Patrono e pagamentos: não existem; depende de escolher um provedor.
- Catálogo de Flavor Text contextual: não existe.
- Integração de visuais/skins: não existe.

**Operação que falta:** agendador que sobreviva a restart e a várias instâncias, métricas e alertas, deploy/rollback de produção, backup e restore, administração/RBAC/sanções (hoje só CLIs), rate limiting e antiabuso geral, jornada E2E criação→Nv.60→Legado com as 6 Classes e smoke test no Telegram real.

**Pendências das etapas entregues:** recompensas da Batalha de Guildas e efeitos de 6 das 7 Obras; frases de flavor dos resultados da Arena, do Duelo e da Batalha de Guildas; conteúdo dos catálogos de Eventos, Juramento e Expedição (o autor define).

#### Etapa 9 · bloco A (entregue)

- **Regras puras** em `domain/chronicle.py`: calendário derivado do Dia 1, fases (`scheduled`, `active`, `closing` T→T+2h, `rescue` T+2h→T+14d, `archived`), os 32 objetivos e 8 conclusões com pontos da proposta v0.2, fontes repetíveis e limites, Trilha (20 Marcos Livres e 10 Premium, 15 cosméticos `cos_cr01_*`), voto (elegibilidade 4/8 + 1, apuração, runoff, `em_espera`, ordem embaralhada por conta), camadas de spoiler C1–C4/H por missão concluída e faixa da recompensa de Elo.
- **Serviço** em `application/chronicle.py`: `record_objective` e `record_repeatable` (para as fontes chamarem dentro da própria transação; idempotentes por conta), conclusão de capítulo, Resgatar Disponíveis, voto, Salão da Vigília, histórico por conta e a manutenção (fecha voto e congela o eleitorado, fecha runoff, finaliza em T+2h e liquida em T+14d). Job `chronicle-upkeep` a cada 60s.
- **Integração competitiva** (`application/competitive_cycle.py`): entre T e a finalização a fila da Arena e a Inscrição de Batalhas com início ≥ T ficam fechadas. Na finalização: Salão da Vigília (Arena, Guildas e participações individuais), soft reset de Renome `1000+0,5×(R−1000)` só para quem completou a Colocação, MMR intacto, `cycle_matches` zerado, classificação da Batalha de Guildas zerada (rating e `career_real_battles` persistem). As participações individuais passam a contar só o ciclo atual.
- **Fontes já ligadas:** só `rep_cr01_masmorra` (fim de run de Masmorra com participação > 0).
- **Telas:** Benefícios → Trilha da Crônica → Crônica (capítulos, objetivos, conclusão, voto, epílogo depois de T) e Classificação da Vigília → Salão da Vigília. Frases de flavor da proposta §10 nos resultados de Arena, Duelo e Batalha de Guildas.
- **Operação:** `python -m asterion.chronicle_cli status | set-day1 AAAA-MM-DD --note … | extend AAAA-MM-DDTHH:MM --note … | pass-grant <telegram_id> | maintenance`. Sem Dia 1 nada abre. Toda troca fica em `chronicle_cycle_logs`.
- **Banco:** migration `20261110_0043`.

**Escolhas do bloco A (aprovadas pelo autor):**

1. Os capítulos abrem às 06:00 (reset diário, §34) do dia D1, D8…D50.
2. T é o último dia da semana 8 (D56) às 21:00.
3. "Semanas liberadas" do teto de repetíveis = capítulos já abertos.
4. O soft reset de Renome só vale para quem completou a Colocação (quem nunca jogou não vai para 400).
5. Regente com 20–29 partidas recebe a recompensa do Elo logo abaixo (Arauto I).
6. Depois da finalização a Arena e a Batalha de Guildas reabrem e acumulam para o próximo ciclo, mesmo sem Crônica II definida.
7. Excluir o personagem apaga o estado narrativo dele; pontos, resgates, voto e elegibilidade continuam da conta. Os cosméticos da Trilha voltam ao novo personagem ao abrir a Trilha.
8. Personagem sem conta no servidor na liquidação: o direito é marcado como liquidado sem entrega.

**Ainda falta (sem número ou conteúdo definido):** os cosméticos das recompensas de Elo e da Batalha de Guildas (hoje o Salão só registra quem é elegível e o Elo); a entrada Calendário do menu (a Crônica está em Benefícios → Trilha).

**Bloco B (próximo):** conteúdo jogável dos capítulos: Leituras (`lei_cr01_*`), resultados de Desbravar (`dsc_cr01_*`), Falar com NPC por Região de Ressonância, Masmorra em foco/espelho e o alternativo `dsc_cr01_vestigio_profundo`, os 8 Encontros e as 9 criaturas (kits em `SIMULAR`, precisam de Balanceamento), o Evento Mundial O Compasso, Entradas do Códice, Feitos, Crônica Arquivada e a regra `pr_cr01_encontro_grupo`.

#### Etapa 9 · bloco B

**Divisão em partes:**

1. Falar com NPC, Leituras e Desbravar (`dsc_cr01_*` e `dsc_cr01_vestigio`): entregue nesta parte.
2. Encontros e criaturas Comum/Incomum/Elite (capítulos 1, 2, 3, 5, 6 e 7), `[Enfrentar]`, recompensa da primeira vitória, `rep_cr01_encontro` e Feitos das Elites: entregue (ver "Parte 2" abaixo).
3. Chefes Mestre de Turno e O Que Aguarda Resposta (capítulos 4 e 8), a regra `pr_cr01_encontro_grupo`, o Coro e os Feitos dos Chefes e do voto: entregue (ver "Parte 3" abaixo).
4. Masmorra em foco/espelho e o alternativo `dsc_cr01_vestigio_profundo`: entregue (ver "Parte 4" abaixo).
5. Evento Mundial O Compasso e `rep_cr01_evento`: entregue (ver "Parte 5" abaixo).
6. Entradas do Códice, Feitos restantes e Crônica Arquivada: entregue (ver "Parte 6" abaixo). O bloco B está completo.

Todo capítulo tem um Encontro obrigatório. Com a parte 3, os 8 capítulos podem ser concluídos. Os kits das criaturas e dos Chefes continuam em `SIMULAR`.

**Parte 1 (entregue):**

- **Conteúdo** em `domain/chronicle_content.py`: Regiões, hubs, NPCs por papel, 8 falas, 18 pontos de Leitura (3, 3, 4 e 8) e 5 resultados de Desbravar, com versão em foco, espelho e complementos de camada.
- **Serviço** em `application/chronicle_activities.py`: `talk`, `readings`, `examine`, `actions`, `here` e o gancho `desbravar_offer`/`settle_desbravar`, ligados a `record_objective` e `record_repeatable`.
- **Desbravar:** enquanto há resultado de capítulo pendente no Local, ele ocupa a categoria Narrativo (decisão do autor em 2026-11-09). A 3ª tentativa é garantida (GDD §49.15). O `dsc_cr01_vestigio` tem peso 100 no Narrativo (decisão do autor, sujeita a Balanceamento). Nenhum dos dois gasta Vigor nem concede XP ou economia.
- **Telas:** o capítulo mostra onde fazer cada objetivo e os botões quando o personagem está no lugar certo. O Local Atual ganha `🌌 Crônica · Neste Local` quando há algo a fazer ali.
- **Banco:** sem migration. As flags de Leitura ficam em `chronicle_completions`.

**Escolhas da parte 1 (aprovadas pelo autor em 2026-11-11, por delegação):**

1. A Região de Ressonância considera só Regiões onde o personagem já tem Desbravar liberado. Assim, quem acabou de chegar a uma Região continua na anterior até liberar o Desbravar, em vez de ficar sem hub e sem Local. A Região-foco segue a mesma regra.
2. A garantia da 3ª tentativa conta as tentativas no Local desde a abertura do capítulo.
3. Com vários capítulos pendentes no mesmo Local, sai primeiro o mais antigo.
4. O Vestígio sai do sorteio quando o limite diário ou o teto semanal já não pagariam pontos.
5. **Os textos são rascunho:** a proposta define quem, onde e quantos, mas não as falas de NPC, as Leituras e os resultados de Desbravar. Eles foram escritos a partir dos resumos de cada capítulo, e os complementos de camada usam o texto da proposta. O autor precisa revisar `domain/chronicle_content.py`.

**Parte 2 (entregue):**

- **Criaturas** em `domain/road.py` (`CR01_*`, no `CREATURE_CATALOG`, fora de qualquer pool de Caçada, Ronda ou Desbravar): Repetidor, Marcador, Guarda Repetida, Carregador Repetido, Multidão Repetida e Escriba Repetido, com os coeficientes da proposta §11.3 e os atributos da fórmula do GDD §49.6. Continuam em `SIMULAR`.
- **Encontros** em `domain/chronicle_encounters.py`: qual criatura cada objetivo usa, o nível (nível do personagem dentro da faixa da Região de Ressonância), a matéria por Região (§11.2) e os ajustes que a tupla posicional não cobre (multi-hit e marca de DEF).
- **Serviço** em `application/chronicle_encounters.py`: `start` (`[Enfrentar]` e `[Enfrentar o Eco de novo]`), `action`, consumíveis, `foreground` (o `/start` e o `/menu` voltam à luta) e a lista de Encontros por capítulo. Usa o motor de combate compartilhado e `scripted_combat`.
- **Regras:** a luta exige estar no Local de Ressonância (decisão do autor em 2026-11-10). O nível é congelado na criação; depois de uma derrota, a nova tentativa reaproveita o nível e a cena da anterior. Primeira vitória: XP normal de inimigo (uma vez por personagem por encontro), objetivo da Crônica e Bestiário; nada de Coroas, Materiais, Saque, Equipamento ou Vigor. Derrota: sem perda, HP restaurado pela regra regional de derrota de PvE. Repetição: 0 XP, só `rep_cr01_encontro` (25 pontos, 2 por dia por conta). Elites exigem Nv.3 e concedem `feito_cr01_multidao` e `feito_cr01_escriba`.
- **Barreiras:** Postura Copiada e Revisão duram 2 turnos (decisão do autor em 2026-11-10; a proposta só dava o valor).
- **Telas:** o capítulo lista o Encontro e mostra `⚔️ Enfrentar` ou `🔁 Enfrentar o Eco de novo` quando o personagem está no Local. `🌌 Crônica · Neste Local` também os oferece. Os botões de combate usam o prefixo `crf:`.
- **Banco:** sem migration. O nível congelado é lido do snapshot do combate anterior (`game_activities.content_id` = `chronicle.enc_cr01_cNN` e `….eco` na repetição).

**Escolhas da parte 2 (aprovadas pelo autor em 2026-11-11, por delegação):**

1. **Defender do Carregador Repetido não foi aplicado.** O motor não tem Defender de criatura (o `defend` no ciclo de qualquer criatura é ignorado hoje). Aplicar exige mexer no motor compartilhado.
2. ~~Coro da Multidão Repetida não existe ainda.~~ Entrou na parte 3.
3. **"Redução de DEF igual ou maior"** (Marcador e Escriba) virou "a criatura não reaplica enquanto a própria marca estiver ativa". O motor não compara reduções de outras fontes.
4. **Telegraph próprio** das Ações Preparadas ("ergue algo que não está ali" etc.) não aparece: a tela mostra o aviso padrão "prepara <Arte>".
5. `[Enfrentar o Eco de novo]` some quando o limite diário ou o teto semanal já não pagariam pontos (mesma regra do Vestígio na parte 1).
6. Os Feitos das Elites usam o nome da criatura e a frase "Venceu pela primeira vez…" como rascunho, na categoria Crônicas.
7. As 6 criaturas registram progresso de Bestiário, mas **ainda não aparecem na tela do Bestiário**: ela agrupa por Região e habitat, e estas criaturas não têm Região. ~~Fica para a parte 6.~~ Entrou na parte 6: grupo próprio na tela do Bestiário.
8. Depois de uma derrota fora das Terras do Ocaso o personagem fica onde está, com HP cheio: é a regra regional de derrota que já existe (só o Ocaso move para um Braseiro).

**Parte 3 (entregue):**

- **Chefes** em `domain/road.py`: Mestre de Turno (Bruto) e O Que Aguarda Resposta (Equilibrado), perfil de Chefe do GDD §49.6, Nv.5, coeficientes da proposta §11.4, em `SIMULAR`. Encontros `enc_cr01_c04` e `enc_cr01_c08` em `domain/chronicle_encounters.py`. Com isso os 8 capítulos podem ser concluídos.
- **Fases** em `70%` e `35%` (`CombatPhaseTrigger`, snapshotadas). Mestre: Chamada invoca 1 add com o kit do Repetidor e HP ×0,50 (decisão do autor em 2026-11-10), opcional, sem escala de Grupo, sem XP nem Bestiário; Ordem Coletiva na Fase II+; Fim de Turno na Fase III. Aguarda: Espera (sem ataque, `DEF −12%` em si por 1T) na 4ª, 8ª… oportunidade contada da entrada na Fase II (decisão do autor em 2026-11-10); Insistência na Fase II+; Confirmação Exigida na Fase III; Selo Pendente dura 2 turnos (decisão do autor em 2026-11-10).
- **Coro** da Multidão Repetida (AoE `75%`, CD3) entrou. Coro, Ordem Coletiva e Insistência só saem com 2+ alvos vivos.
- **Motor:** dois campos novos e opcionais: `Action.min_living_opponents` e `CombatPhaseTrigger.cooldown_action_ids/cooldown_opportunities`. Reviver um fighter agora também o mostra (`encounter_hidden = False`).
- **Grupo (`pr_cr01_encontro_grupo`):** botão `👥 Em Grupo` ao lado de `⚔️ Enfrentar` para quem está num Grupo social. Usa a Confirmação de Entrada de 60s (`GroupService`, tipo `chronicle_encounter`) e o combate compartilhado da Campanha (`campaign_coop`). A proposta e o início ficam na tela 👥 Grupo. Todos precisam estar no Local de Ressonância da Referência (decisão do autor em 2026-11-10). Membro com o mesmo objetivo ativo, a mesma Região de Ressonância e o nível mínimo é `eligible`; outro presente é Ajudante e não conta. Só os Chefes escalam (GDD §51.5).
- **Feitos:** `feito_cr01_mestre_de_turno` (Fim de Turno), `feito_cr01_aguarda_resposta` (Sem Resposta) e `feito_cr01_respondeu_ao_eco` (Respondeu ao Eco, `pr_cr01_feito_resposta`), entregue no fechamento do voto principal e do desempate a quem votou estando no eleitorado.
- **Telas:** o Chefe com add e a luta em Grupo usam o callback `cri:` (ação por índice e alvo).
- **Banco:** sem migration.

**Escolhas da parte 3 (aprovadas pelo autor em 2026-11-11, por delegação):**

1. A Chamada é uma ação do Chefe (gasta a vez dele), na primeira oportunidade depois de cair abaixo de 70%, mesmo se ele pular direto para a Fase III.
2. O N da escala de Chefe conta todo o roster confirmado, Ajudantes incluídos ("roster ativo inicial", GDD §51.5).
3. Na repetição em Grupo (Eco), conta só quem já venceu e ainda recebe Trilha hoje; quem nunca venceu entra como Ajudante. Na primeira luta, quem já venceu entra como Ajudante.
4. Ajudante não recebe XP, Bestiário, Feito, objetivo nem Trilha; recupera o HP como os demais.
5. Em Grupo, o nível congelado vem da última luta perdida da Referência naquele Encontro (como no Solo).
6. A proposta não manda aviso no Telegram: aparece na tela 👥 Grupo, como na Campanha. O resultado só aparece para quem deu o último golpe; os outros voltam ao menu sem a tela de resultado.
7. O id `feito_cr01_respondeu_ao_eco` e as descrições dos 3 Feitos são rascunho.

**Parte 4 (entregue):**

- **Conteúdo** em `domain/chronicle_content.py`: `DUNGEON_FOCUS` liga cada objetivo de Masmorra às 2 Masmorras da Região-foco (`cap_02_obj_04` Galerias do Vigia ou Cripta do Ocaso; `cap_03_obj_03` Santuário do Nó Antigo ou Fosso das Raízes; `cap_05_obj_04` Cisterna de Transferência ou Enfermaria Afundada; `cap_06_obj_03` Bastilha Profunda ou Pedreira do Contrapeso). `DEEP_VESTIGIO_RESULT` e `DEEP_VESTIGIO_TEXT` são o alternativo.
- **Fim da run** (`DungeonService._settle_run`): para cada participante com participação > 0, além de `rep_cr01_masmorra`, chama `record_dungeon_run` (`application/chronicle_activities.py`), que conclui o objetivo de Masmorra pendente mais antigo aceito por aquela Masmorra. Em foco, só o par da Região-foco; em espelho, qualquer Masmorra. Usa `started_at = run.created_at`.
- **"Estável liberada"** (`stable_released` em `application/dungeons.py`): Masmorra descoberta, missões exigidas concluídas e nível mínimo da família. É a mesma regra da tela da Masmorra.
- **Alternativo:** com o objetivo pendente e nenhuma Masmorra aceita liberada, `desbravar_offer` põe `dsc_cr01_vestigio_profundo` no Narrativo do LR do capítulo, com a garantia da 3ª tentativa da parte 1. O objetivo vai em `ExplorationAttempt.progress["chronicle_objective"]`, porque o mesmo resultado serve aos 4 capítulos. Paga os pontos do objetivo (70, 70, 60 e 60), sem Vigor, XP ou economia.
- **Telas:** o capítulo mostra `Masmorra: <A> ou <B>` em foco, `qualquer Masmorra com Estável liberada` em espelho, ou `sem Masmorra liberada: Desbravar em <Local>`. Não há botão: a Masmorra entra pelo próprio menu e o alternativo pelo Desbravar.
- **Banco:** sem migration.

**Escolhas da parte 4 (aprovadas pelo autor em 2026-11-11, por delegação):**

1. Em foco, só as 2 Masmorras da Região-foco contam. Se nenhuma das duas tem Estável liberada, vale o alternativo, mesmo que outra Masmorra esteja liberada (leitura literal da regra 0.3.4).
2. Uma run conclui no máximo 1 objetivo de Masmorra (o do capítulo mais antigo), além do repetível.
3. Qualquer dificuldade conta, porque Fraturada e Ruptura já exigem a Estável.
4. A garantia da 3ª tentativa do alternativo conta as tentativas no Local desde a abertura do capítulo, como na escolha 2 da parte 1. Quem já desbravou 2 vezes ali no capítulo recebe o alternativo na tentativa seguinte.
5. O alternativo não conta como `rep_cr01_desbravar`: só o `dsc_cr01_vestigio` conta.
6. Enquanto o alternativo está pendente no Local, o `dsc_cr01_vestigio` não aparece ali (o resultado de capítulo ocupa o Narrativo).
7. A liberação é conferida a cada tentativa: liberar uma Masmorra depois tira o alternativo do Desbravar.
8. Masmorra não tem Ajudante: todo membro passou pelos gates de entrada. Conta quem tem participação > 0, o capítulo aberto no início da run e a P1 concluída.
9. O texto do Vestígio Profundo é rascunho e é o mesmo nos 4 capítulos. A tela de resultado da run não ganha linha da Crônica (como já acontece com o repetível); o ✅ aparece no capítulo.

**Parte 5 (entregue):**

- **Chefe** `boss_evento.cr01.o_compasso` em `domain/road.py` (`CR01_O_COMPASSO`, Equilibrado, perfil de Chefe de Evento do GDD §49.15), kit da proposta §11.5, em `SIMULAR`. Como cada fase do Evento é um combate próprio, as travas de fase ficam em `domain/chronicle_events.py` (`configure_compasso`): Fase 1 Batida e Contratempo; Fase 2 + Onda de Compasso e Batida Plena; Fase 3 + Ressonância.
- **Agenda** em `domain/chronicle_events.py`: do Dia 1 até T, todo horário normal (ter/qui/sáb, 12:00 e 20:00) roda O Compasso, com 6 ocorrências no mesmo horário, uma por faixa de Região (nível de evento 10/20/30/40/50/60, com Sintonização do Véu). Até o D42 é `evt_cr01_ressonancia`; do D43 em diante, `evt_cr01_ressonancia_plena`. Fora da Crônica vale o catálogo normal (vazio).
- **Serviço** (`application/world_events.py`): a versão vai no `occurrence_key` (`<horário>.cr01r1` … `cr01p6`), então não há migration. O personagem escolhe uma versão por horário, de uma Região onde já tem Desbravar liberado (erros `region_locked` e `other_version`). As regras do Evento não mudam: HP compartilhado, 3 fases, escala `N^0,88`, elegibilidade ≥2 fases + 8 Ações Significativas, reentrada em 2 min, economia padrão.
- **Plena:** na Fase 2, cada instância ganha 1 Repetidor (kit do Repetidor, HP ×0,30, opcional, sem XP nem Bestiário). O dano nele não reduz a barra do Chefe.
- **Crônica:** no acerto da ocorrência, cada participante elegível chama `record_world_event` (`application/chronicle_activities.py`): `rep_cr01_evento` com chave `occurrence_id` (1 por ocorrência) e, no máximo, 1 objetivo de Evento (o pendente mais antigo que aceita aquele Evento). `cap_04_obj_03` aceita Ressonância; `cap_07_obj_04` e `cap_08_obj_03` aceitam Plena.
- **Telas:** o capítulo mostra `📍 <objetivo> · <dia> às <hora> · Eventos Mundiais, versão <Região de Ressonância>`, ou `acontecendo agora, entrada até <hora>`. Não há botão: entra pelo menu 🌍 Eventos, que lista as versões liberadas quando o horário tem mais de uma.
- **Banco:** sem migration. O `content_id` da atividade de combate do Evento agora leva a fase (`world_event:<id>:<fase>`), para saber se é a primeira instância da Fase 3.

**Decisões do autor na parte 5 (2026-11-11):**

1. A Plena começa no D43: até o D42 só Ressonância; a partir do D43 só Plena. O `cap_04_obj_03` (opcional) deixa de ser possível no D43.
2. O jogador escolhe a versão entre as Regiões já liberadas; nas inferiores, Sintonização do Véu.
3. Repetidores da Plena: 1 por instância, HP ×0,30.
4. Durante a Crônica, todos os horários de Evento são da Crônica.
5. A Barreira da Ressonância dura 2 turnos e sai só na 1ª instância de Fase 3 de cada participante (quem reentra não a enfrenta de novo).
6. Ordem de IA de O Compasso: resolver Batida Plena pendente; Ressonância; preparar Batida Plena; Onda de Compasso; Contratempo (não reaplica enquanto a própria marca está ativa); Batida.

**Escolhas da parte 5 (aguardam aprovação do autor):**

1. "Região já acessada" é a Região com Desbravar liberado, a mesma regra da Região de Ressonância (escolha 1 da parte 1).
2. Elegibilidade é a do Evento normal: exige a ocorrência concluída. Se o tempo acaba, ninguém conta, nem para objetivo nem para Trilha.
3. Uma ocorrência conclui no máximo 1 objetivo de Evento, o mais antigo. Assim o `cap_08_obj_03` sempre vem de uma ocorrência diferente da do `cap_07_obj_04`.
4. Onda de Compasso e Batida Plena não têm a regra de "2+ alvos": cada instância é Solo, então elas acertam só o jogador. A proposta não dá restrição.
5. Os textos das 3 fases e da conclusão são rascunho. Os nomes na tela são "Ressonância" e "Ressonância Plena".
6. A manutenção agendada (`round_scheduler`) não recebe a consulta de Locais: ele só abre, encerra e acerta ocorrências.

**Parte 6 (entregue):**

- **Códice** em `domain/chronicle_codex.py`: as 12 Entradas da proposta §6 (`codex_cr01_ecos` contínua, as 10 por capítulo e `codex_cr01_desfecho`) e seus Trechos, com o texto da proposta. Cada Trecho de camada (`_c1`, `_c2`, `_h`, `_c3`, `_c4`) é separado e só é registrado com a flag da camada (P6, P18, P24, P29, P35). O desfecho usa o epílogo já aprovado (`EPILOGUES`) e o complemento C3/C4 do epílogo da proposta §4.
- **Registro** em `application/chronicle_codex.py` (`sync_chronicle_codex`): idempotente por `character_id + fragment_id`. Roda depois de concluir um capítulo e sempre que o Códice abre (`CharacterSurfacesService.knowledge`), então uma camada ganha depois, uma Região descoberta depois e o desfecho publicado em T aparecem sem job. Trechos nunca são removidos.
- **Crônica Arquivada:** `Calendar.archived` (depois de T+14d) e `Calendar.playable` (Crônica aceitando progresso ou arquivada). Falar, Leituras, Desbravar (`dsc_cr01_*` e o alternativo), Masmorra, Encontros e a conclusão de capítulo voltam a funcionar, com todos os 8 capítulos abertos. `record_objective` grava o objetivo, mas não paga pontos. As fontes `rep_cr01_*` ficam fechadas (`repeatable_available` exige a Crônica aceitando progresso), então somem o Vestígio e `[Enfrentar o Eco de novo]`. O Evento Mundial continua só na Crônica ativa. Sem Grupo (`👥 Em Grupo` some e a proposta vira Solo). Durante o resgate (T+2h a T+14d) nada da história é jogável.
- **Recompensa na Arquivada:** primeira vitória dá Bestiário e Feito, sem XP (decisão do autor em 2026-11-11). Nada de pontos, voto ou economia.
- **Feitos:** a proposta só cita 5 Feitos e todos já existiam (partes 2 e 3). Nada a criar (decisão do autor em 2026-11-11).
- **Bestiário:** as 8 criaturas e Chefes `*.cr01.*` e O Compasso têm `CreaturePresentation` no grupo `cr01`, exibido como `🌌 Crônica I · Ecos da Convergência`, depois das Regiões, sem habitat.
- **Telas:** na fase arquivada, a Crônica mostra o texto da Crônica Arquivada e o capítulo não mostra pontos. A categoria Regiões e Locais do Códice agora lista também Entradas sem Local (é o caso de `codex_cr01_marcas_que_vibram`).
- **Banco:** sem migration. A Arquivada usa `chronicle_completions` (o histórico do perfil conta pontos, que a Arquivada não gera).

**Decisões do autor na parte 6 (2026-11-11):**

1. A Crônica Arquivada abre depois de T+14d e continua o progresso do personagem: o que ele já fez continua ✅.
2. Só Solo, sem Evento Mundial e sem repetível. Masmorra e o alternativo continuam valendo para o objetivo opcional, sem pontos.
3. Primeira vitória na Arquivada: Bestiário e Feito, sem XP.
4. Quem conclui o primeiro capítulo só na Arquivada também recebe a Entrada do desfecho.
5. Nenhum Feito novo.

**Escolhas da parte 6 (aguardam aprovação do autor):**

1. As Entradas e Trechos de cada capítulo são registrados na **conclusão** do capítulo (a proposta só dá o capítulo). Assim `codex_cr01_formas_do_pulso` não sai na primeira luta, e sim ao concluir o Capítulo 1.
2. Os Trechos `codex_cr01_herdeiros_altos` (Maro Keln) e `_confins` (Eris Val) exigem um Local descoberto dos Altos ou dos Confins, para não nomear NPC de Região que o personagem não conhece.
3. A Entrada do desfecho aparece a partir de T, como o epílogo na tela da Crônica, para quem tem ao menos 1 capítulo concluído.
4. Ordem dentro de cada categoria: as Entradas da Crônica vêm depois das regionais.
5. **Textos rascunho:** os títulos dos Trechos (a proposta não traz títulos): "Capítulo N · <título>" na Entrada contínua; o título da Entrada no Trecho base; e, nos de camada, "Perto da Âncora", "Estados guardados", "Referências sem resposta", "Protocolos em espera", "A noite da Ruptura", "Maro Keln", "Eris Val", "A etapa final", "A origem do pedido" e "Além do registro". Também é rascunho o texto da tela da Crônica Arquivada (`ARCHIVED_TEXT` em `bot/chronicle_ui.py`).

**Pendências encontradas na parte 6 (corrigidas no PR seguinte, `fix/bestiario-codice-regioes`):**

- As telas do Bestiário e de Regiões e Locais do Códice só tinham rótulo para Ocaso, Vales e Altos, e os Locais dos Confins (`location.confins.*`) não eram reconhecidos como Região. Agora as 6 Regiões aparecem, na ordem de progressão; a Crônica fica por último no Bestiário.
- `codex.altos.regiao` e `codex.confins.regiao` geravam a mesma chave de botão (`kb:e:regiao`). Agora, quando o último trecho do id se repete, a chave usa os dois últimos (`altos_regiao`, `confins_regiao`). Botões antigos com `kb:e:regiao` deixam de abrir essas duas Entradas.

**Etapa 9 (origem):** Crônica I, Nova Vigília e Trilha, integradas com Arena e Batalha de Guildas. O conteúdo está proposto em `ASTERION_CRONICA_I_ECOS_DA_CONVERGENCIA_v0_2_PROPOSTA.md` (2026-11-09). Os kits das 9 criaturas novas estão em `SIMULAR` e precisam de Balanceamento antes do lançamento.

**Decisões do autor sobre a proposta (2026-11-09):**

- **Data:** o Dia 1 da Crônica é configurável e o autor define depois. Sem data configurada, nada abre. D8…D50, voto, T, T+2h e T+14d derivam do Dia 1. A data pode ser trocada antes do início; depois, só pela extensão excepcional do GDD §5.3, com registro.
- **Bíblia:** o documento usa a Bíblia Canônica v4.0.7, que o autor aprovou como referência, mas o arquivo ainda não está no repositório e o `SOURCE_AUTHORITY.md` ainda registra a v3.0 FINAL. O autor vai enviar o arquivo; até lá, a validação de lore fica pendente.
- **Dúvidas 1–7 e 9–22:** aprovadas as recomendações. Gate de entrada: P1 concluída. Evento da Crônica nos horários normais, com uma versão do Chefe por faixa de Região no mesmo horário. Voto abre em D50 e T às 21:00 America/Sao_Paulo. A Entrada do desfecho vai para quem concluiu ao menos 1 capítulo. Os básicos usam o Grau da Dádiva Diária. Os limites de 2/dia são conteúdo, sujeitos a revisão de Balanceamento. Ajudante não conta. Uma run vale para objetivo e repetível. O alternativo de Masmorra por Desbravar é aceito. As opções do voto são embaralhadas por jogador. A Crônica Arquivada é jogável sem pontos. Elegibilidade 4/8 + 1. As 9 criaturas são aprovadas, com um único material visual no lançamento. Os kits passam por simulação de Balanceamento. XP normal na primeira vitória. Elite Nv.3 e Chefe Nv.5. A luta acontece na Região de Ressonância do jogador.
- **Dúvida 8 (Aparências):** a skin da Crônica é **especial e única**, com **fundo próprio da Crônica**; não segue o padrão regional nem o céu neutro.
- **PROPOSTAS DE REGRA:** `pr_cr01_encontro_grupo` e `pr_cr01_feito_resposta` aprovadas; `pr_cr01_eco_residual` adiada (o desfecho fica só narrativo).

## 9. Próximos passos recomendados

Não foi encontrado backlog/sprint ativo confiável para afirmar “o próximo item planejado” pelo autor. A ordem abaixo é uma reconstrução técnica a partir do estado do Git e dos gates dos próprios documentos:

1. **Congelar o retrato e revisar diffs:** registrar `git status --short`, comparar `HEAD`, `main`, refs remotos e cada worktree; identificar autoria/objetivo das alterações antes de editar ou limpar. Separar candidato documental Fase 2E de código WIP de Armazém.
2. **Escolher a autoridade de design operacional:** resolver v1.0.16 vs alvo v1.0.17 de TDO e qualquer diferença de Bíblia/metadata; atualizar somente pelo fluxo de publicação e `SOURCE_AUTHORITY.md`.
3. **Fechar os gates de Fase 2E com Game Design/Release:** aprovar as três linhas pendentes, conferir os 226 template IDs contra um snapshot de release, consolidar receitas/output IDs e as combinações de elegibilidade de loot. O pacote marca publicação/importação/migration/flag/merge/deploy como NO-GO enquanto isso não for resolvido.
4. **Concluir Armazém/capacidade como feature independente:** revisar o diff completo e migration 0032, confirmar constraints/índices/idempotência/locks e entrega pendente, então validar numa base PostgreSQL limpa e numa base de upgrade antes de considerar integrar. Revisar se item ligado/equipado, stacks e operação concorrente seguem a regra de negócio pretendida.
5. **Alinhar schema e migrations:** `alembic heads`, `upgrade head` e `alembic check` precisam concordar com o modelo da branch; separar o schema local de Armazém do restante do diff de `models.py`.
6. **Executar validação automatizada depois de estabilizar diffs:** Ruff, suíte completa com `ASTERION_TEST_DATABASE_URL`, playthroughs regionais e CI. A auditoria atual não executou essas verificações.
7. **Definir deployment real:** escolher polling ou webhook, processo único de scheduler, número de réplicas, segredo/TLS/registro webhook, backups e migração pre-deploy; garantir que assets `file:` estejam acessíveis no container. Confirmar se Outbox será implementada agora ou removida da promessa operacional.

## 10. Pontos de atenção e riscos

- **Não migrar nem publicar candidato por engano.** Fase 2E v1.9.1 é explicitamente não canônica; sua minuta não sobrescreve GDD v1.6.0, Weapon Metadata v1.0.0 ou `SOURCE_AUTHORITY.md`.
- **WIP no mesmo checkout:** alterações locais de regra/sistema e testes coexistem com documentação de Fase 2E. Um `git add .` pode incluir `.worktrees/`, assets, ZIPs e candidatos. Revisar staged diff arquivo a arquivo.
- **Schema vs banco:** 80 tabelas são derivadas do ORM alterado; código de migration 0032 não está rastreado. Não assumir que produção/banco de outra branch tem essas tabelas ou colunas.
- **Idempotência, concorrência e callback replay:** o GDD exige resolução autoritativa, locks e callbacks como intenção do cliente. Manter commits de recompensas/consumo/estado em transação única; validar actor, server, estado, revisão, cooldown e origem no serviço. Nunca confiar em `callback_data` ou texto para conceder acesso/recompensa.
- **Agendador:** `replace_existing`/`max_instances=1` são por processo. Um API por réplica em webhook inicia scheduler na inicialização; cada processo polling também inicia um. Uma implantação horizontal pode avançar a mesma Ronda em paralelo.
- **Outbox com Telegram (2026-11-11):** o dispatcher (`application/outbox.py`, job `outbox-dispatch` a cada 5 s) usa `FOR UPDATE SKIP LOCKED` com lease de 2 min, entrega fora da transação, 5 tentativas com espera de 30 s/2 min/10 min/1 h e depois `status='dead'` (reenvio: `python -m asterion.outbox_cli requeue`). Mesmo `aggregate_key` segue a ordem de criação. Handler pode lançar `PermanentOutboxError` (vai direto a `dead`) ou `OutboxRetryLater(segundos)`. Tópico real: `telegram.send_message` em `bot/telegram_outbox.py` (`TelegramOutbox.send`/`send_many` grava com `ON CONFLICT (dedup_key) DO NOTHING`, `aggregate_key=telegram:<chat>`). O handler respeita o flood wait do Telegram, manda bot bloqueado/chat inexistente/pedido inválido direto para `dead` e descarta aviso vencido (`expires_at` vindo de `seconds_left`/`deadline` da tela, do `expires_at` do convite de Grupo ou da Troca aberta). Passam pela Outbox (aprovado pelo autor em 2026-11-11): avisos de Arena/Duelo, Batalha de Guildas, Evento Mundial, Juramento e Expedição (do job e do oponente), convite de Grupo, convite de Guilda, resultado da Inscrição, venda no Mercado e avisos de Troca. Ficam diretos, porque precisam do resultado na hora: Divulgar loja e Publicar Relato no tópico da comunidade. Limites: o aviso é gravado logo depois do commit do jogo, não na mesma transação (as telas são montadas na camada do bot); e o Telegram não tem chave de idempotência, então um crash entre o envio e a marca `delivered` pode repetir uma mensagem. Nos testes, `tests/outbox_drain.py` entrega a fila por um bot falso.
- **Redis subutilizado:** variável e health check estão presentes, mas não há cache/lock/fila identificado no fluxo atual; não o trate como requisito de persistência do jogo.
- **Segredos/configuração:** o token Telegram e webhook secret não podem ser commitados/logados. Os defaults locais de DB são previsíveis; produção precisa credencial forte, TLS/rede restrita, rotação, backup e permissões mínimas. `.env` não faz parte do handoff.
- **Assets:** referências `file:` dependem de caminho dentro do processo; Docker não copia `assets/`. Evite path traversal e assets não revisados; preferir IDs hospedados/volumes declarados para operação.
- **Metadados de arma:** manter vocabulário e mapping exatos do contrato v1.0.0. Não inferir `weapon_family` nem transformar aparência/skin em regra mecânica.
- **Unidades/rounding:** secundários são pontos percentuais; primários fecham uma vez em `ROUND_HALF_UP`; economia arredonda dezenas em `ROUND_HALF_EVEN`; XP é consolidado em fronteira de atividade. Misturar políticas cria drift de balanceamento.

## Apêndice A — Migrações Alembic

O diretório contém revisões `20260920_0001_foundation_outbox.py` até `20261023_0031_legacy_core.py` rastreadas; e `20261026_0032_inventory_warehouse.py` local, sem commit. As revisões cobrem, em ordem geral: infraestrutura/outbox, conta/criação, combate/foreground, mundo/prólogo, campanha, Caçada/Desbravar/Ronda, missões secundárias, consumíveis, equipamentos, contexto por local, provas de classe, slots de Arte, Caminho, Talentos, masmorras, profissões/crafting, perfil/cosméticos/doutrinas, preferências, Vigor, grupo/co-op, caçada em grupo/PvPvE e takeover, talentos em níveis 35/45/55, Legado e por fim Armazém.


