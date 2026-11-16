# Instruções para agentes do Asterion

Asterion é um RPG dark fantasy para Telegram. O autor é iniciante: responda em português, com passos curtos e explicando termos técnicos. Créditos são limitados; evite leituras e mensagens desnecessárias. Ao concluir uma tarefa, avise quando for hora de abrir uma conversa nova e qual modelo usar.

## Regras do projeto

- Nunca abra nem copie o `.env`. Use `.env.example` para consultar os nomes das variáveis.
- Nunca use `git add .`. Adicione arquivos pelo nome. ZIPs, `assets/`, `balanceamento/` e `.worktrees/` não vão para o Git; `balanceamento/` contém um arquivo acima do limite de 100 MB do GitHub.
- Antes de mudar uma regra de jogo, consulte `SOURCE_AUTHORITY.md` para identificar qual versão é autoritativa. Não escolha versão pelo nome do arquivo nem pela data.
- Não invente números de jogo. Se uma fonte não definir o valor, pergunte ao autor.
- Fase 2E (v1.9.x) é candidata e não canônica: não integre nem publique.
- Confirme com o autor antes de `git push`.
- Só o papel `programmer` altera `src/` e `alembic/`. Para implementar, siga uma spec aprovada. Sem spec ou briefing claro, pare e pergunte ao autor.
- `HANDOFF.md` contém o panorama do projeto; leia somente a seção necessária.

## Organização e observação de código

- `src/asterion/domain/` contém regras puras e catálogos; `application/` contém casos de uso; `bot/` contém handlers e telas (`*_handlers.py`, `*_ui.py`); `infrastructure/db/` contém ORM e codecs.
- Ações de inimigos em `domain/road.py` são tuplas posicionais: o índice 13 é a duração da Barreira; duração 0 não concede Barreira.

## Testes e banco de dados

Testes de banco são pulados sem `ASTERION_TEST_DATABASE_URL`; um teste pulado não é aprovado. Use um PostgreSQL descartável na porta `55432` para não tocar no banco do jogo. O Docker Desktop precisa estar aberto.

No Git Bash, `MSYS_NO_PATHCONV=1` é obrigatório ao iniciar o banco:

```bash
MSYS_NO_PATHCONV=1 docker run -d --rm --name asterion-test-pg --tmpfs /var/lib/postgresql/data -e POSTGRES_DB=asterion_test -e POSTGRES_USER=asterion -e POSTGRES_PASSWORD=asterion -p 127.0.0.1:55432:5432 postgres:16-alpine -c fsync=off -c synchronous_commit=off -c full_page_writes=off -c max_connections=200
```

Para rodar testes de banco:

```bash
ASTERION_TEST_DATABASE_URL='postgresql+asyncpg://asterion:asterion@127.0.0.1:55432/asterion_test' .venv/Scripts/python.exe -m pytest -o addopts='' -v -n 3 -p no:cacheprovider -W ignore --tb=short -rf
```

- A suíte completa leva cerca de uma hora: rode em segundo plano e grave em arquivo. Prefira rodar somente os arquivos afetados.
- Pare o banco descartável ao terminar: `docker stop asterion-test-pg`.
- `pytest-xdist` (`-n 3`) está instalado no `.venv`, mas não consta no `pyproject.toml`.
- Lint: `.venv/Scripts/python.exe -m ruff check src tests alembic`.
- Migrations: execute `alembic upgrade head` e `alembic check` em banco descartável.

Dois testes conhecidos podem falhar por sorteio de crítico porque comparam dano sem fixar o crítico. Se falharem por esse motivo, relate que são instáveis:

- `test_talents_tier25_unlock.py::test_publicly_acquired_vigia_tier25_effects_are_per_combat_and_per_target`
- `test_talents_tier15_unlock.py::test_publicly_acquired_sentinela_talents_drive_retalie_and_guard_barrier`
