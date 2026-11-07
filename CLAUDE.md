# Asterion

RPG dark fantasy para Telegram. Python 3.12, aiogram 3, FastAPI, PostgreSQL 16, SQLAlchemy async, Alembic.

## Como falar com o autor

- Dev iniciante: responder em português, com passos curtos, explicando cada termo técnico.
- Créditos são limitados: evite leituras e mensagens desnecessárias. Avise quando for hora de abrir uma conversa nova, e com qual modelo.

## Regras do projeto

- Nunca abra nem copie o `.env`. Use `.env.example` para ver os nomes das variáveis.
- Nunca use `git add .`. Adicione arquivos pelo nome: a raiz tem ZIPs, `assets/`, `balanceamento/` e `.worktrees/` que não vão para o Git.
- `balanceamento/` tem um arquivo acima do limite de 100 MB do GitHub.
- Antes de mudar regra de jogo, consulte `SOURCE_AUTHORITY.md`. Ele diz qual versão de cada documento vale. Não escolha pelo nome do arquivo nem pela data.
- Não invente números de jogo. Se a fonte não define um valor, pergunte ao autor.
- Fase 2E (v1.9.x) é candidata e não canônica: não integre nem publique.
- Confirme com o autor antes de `git push`.

## Onde fica cada coisa

- `src/asterion/domain/`: regras puras e catálogos. `application/`: casos de uso. `bot/`: handlers e telas (`*_handlers.py`, `*_ui.py`). `infrastructure/db/`: ORM e codecs.
- `HANDOFF.md`: panorama completo. Tem 99 KB, então leia só a seção necessária.
- Ações de inimigos em `domain/road.py` são tuplas posicionais: o índice 13 é a duração da barreira, e duração 0 não concede barreira.

## Testes

Os testes de banco são pulados sem `ASTERION_TEST_DATABASE_URL`, e pulado não é aprovado. Use um Postgres descartável, na porta 55432, para não tocar no banco do jogo. O Docker Desktop precisa estar aberto.

No Git Bash, `MSYS_NO_PATHCONV=1` é obrigatório neste comando:

```bash
MSYS_NO_PATHCONV=1 docker run -d --rm --name asterion-test-pg --tmpfs /var/lib/postgresql/data -e POSTGRES_DB=asterion_test -e POSTGRES_USER=asterion -e POSTGRES_PASSWORD=asterion -p 127.0.0.1:55432:5432 postgres:16-alpine -c fsync=off -c synchronous_commit=off -c full_page_writes=off -c max_connections=200
```

```bash
ASTERION_TEST_DATABASE_URL='postgresql+asyncpg://asterion:asterion@127.0.0.1:55432/asterion_test' .venv/Scripts/python.exe -m pytest -o addopts='' -v -n 3 -p no:cacheprovider -W ignore --tb=short -rf
```

- A suíte completa leva cerca de 1 hora: rode em segundo plano e grave em arquivo. Prefira rodar só os arquivos afetados.
- Pare o banco no final: `docker stop asterion-test-pg`.
- `pytest-xdist` (a opção `-n 3`) está instalado no `.venv`, mas não consta no `pyproject.toml`.
- Lint: `.venv/Scripts/python.exe -m ruff check src tests alembic`.
- Migrations: `alembic upgrade head` e `alembic check`, num banco descartável.

## Testes instáveis conhecidos

Comparam o dano de dois golpes sem fixar o crítico, então falham por sorteio:

- `test_talents_tier25_unlock.py::test_publicly_acquired_vigia_tier25_effects_are_per_combat_and_per_target`
- `test_talents_tier15_unlock.py::test_publicly_acquired_sentinela_talents_drive_retalie_and_guard_barrier`
