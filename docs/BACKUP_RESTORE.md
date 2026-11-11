# Backup e restore do PostgreSQL

Ferramenta: `python -m asterion.db_backup_cli` (usa `pg_dump -Fc` e `pg_restore`).
A URL vem de `--database-url` ou da variável `ASTERION_DATABASE_URL`. O `.env` não é lido.
Sem cliente PostgreSQL no PATH, use `--docker-container NOME` (roda as ferramentas dentro do container).

```bash
# backup (grava backups/<banco>-<data>.dump e confere se o arquivo é legível)
python -m asterion.db_backup_cli --docker-container asterion-postgres-1 backup

# restore em banco vazio
python -m asterion.db_backup_cli --database-url postgresql+asyncpg://u:p@host/novo restore backups/arquivo.dump

# sobrescrever banco com dados (exige as duas flags)
python -m asterion.db_backup_cli ... restore arquivo.dump --clean --yes
```

- O restore recusa banco que já tem tabelas, a menos que `--clean --yes`.
- `backups/` está no `.gitignore`. Guarde cópias fora da máquina.
- Teste: `tests/test_db_backup_cli.py` (precisa do Postgres descartável `asterion-test-pg`).
