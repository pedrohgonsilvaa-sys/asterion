#!/usr/bin/env bash
# Restaura um backup em um banco. Por segurança, o padrão é um banco de TESTE.
# Uso: scripts/restore.sh backups/asterion-XXXX.dump [banco_destino]
#   Teste de restauração:  scripts/restore.sh backups/arquivo.dump
#   Restaurar de verdade:  FORCE_PRODUCAO=1 scripts/restore.sh backups/arquivo.dump asterion
#                          (pare o bot antes: docker compose ... stop bot)
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
FILE="${1:?informe o arquivo .dump}"
TARGET="${2:-asterion_restore_check}"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

[ -f "$FILE" ] || { echo "ERRO: arquivo não existe: $FILE" >&2; exit 1; }
if [ "$TARGET" = "asterion" ] && [ "${FORCE_PRODUCAO:-0}" != "1" ]; then
  echo "ERRO: restaurar em 'asterion' (produção) exige FORCE_PRODUCAO=1." >&2
  exit 1
fi
if ! [[ "$TARGET" =~ ^[a-z0-9_]+$ ]]; then
  echo "ERRO: nome de banco inválido: $TARGET" >&2
  exit 1
fi

compose exec -T postgres psql -U asterion -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS $TARGET WITH (FORCE)" -c "CREATE DATABASE $TARGET"
compose exec -T postgres pg_restore -U asterion -d "$TARGET" --no-owner --exit-on-error < "$FILE"

TABLES=$(compose exec -T postgres psql -U asterion -d "$TARGET" -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
echo "Restaurado em '$TARGET': $TABLES tabelas."
