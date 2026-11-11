#!/usr/bin/env bash
# Backup do banco do Asterion (formato custom do pg_dump) com verificação e rotação.
# Uso: scripts/backup.sh            (variáveis opcionais abaixo)
#   ENV_FILE=.env.prod  COMPOSE_FILE=docker-compose.prod.yml
#   BACKUP_DIR=backups  BACKUP_KEEP_DAYS=14
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DIR="${BACKUP_DIR:-backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
compose() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$DIR"
FILE="$DIR/asterion-$(date -u +%Y%m%dT%H%M%SZ).dump"

compose exec -T postgres pg_dump -U asterion -d asterion -Fc > "$FILE.tmp"

# Confere que o arquivo é um dump legível antes de aceitá-lo.
if ! compose exec -T postgres pg_restore --list < "$FILE.tmp" > /dev/null; then
  rm -f "$FILE.tmp"
  echo "ERRO: backup inválido, descartado." >&2
  exit 1
fi
mv "$FILE.tmp" "$FILE"

# Apaga só backups antigos desta pasta.
find "$DIR" -name 'asterion-*.dump' -mtime +"$KEEP_DAYS" -delete

echo "Backup criado: $FILE ($(wc -c < "$FILE") bytes)"
