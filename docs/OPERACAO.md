# Operação em produção (VPS)

Guia curto para colocar o Asterion no ar, fazer backup, restaurar e voltar uma versão.
Requisitos na VPS: Linux com Docker e Docker Compose, Python 3.12 e o repositório clonado.

## 1. Primeira instalação

1. Copie as variáveis: `cp .env.example .env.prod`.
2. Edite `.env.prod` e preencha: `POSTGRES_PASSWORD` (senha forte e única), `ASTERION_TELEGRAM_BOT_TOKEN`, `ASTERION_SERVER_ID` e as demais variáveis que o jogo usa. Nunca faça commit desse arquivo.
3. Se o jogo usa imagens `file:`, coloque-as na pasta `assets/` da VPS.
4. Suba tudo:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

O serviço `migrate` cria ou atualiza as tabelas antes do bot iniciar. O bot reinicia sozinho se cair (`restart: unless-stopped`).

**Importante:** rode apenas **um** `bot` por banco. O agendador roda dentro do bot e há um lock no banco para evitar jobs duplicados, mas uma única instância é o jeito seguro.

## 2. Ver o estado e os logs

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail 100 bot
```

## 3. Backup e restauração

Use a ferramenta `python -m asterion.db_backup_cli`, descrita em [BACKUP_RESTORE.md](BACKUP_RESTORE.md). Na VPS, o Postgres roda dentro do Docker, então use a opção `--docker-container` com o nome do container do banco (veja com `docker compose ... ps`; costuma ser `<pasta>-postgres-1`).

Prepare a ferramenta uma vez na VPS:

```bash
python3 -m venv .venv && .venv/bin/pip install .
```

Agende um backup por dia (exemplo: 04:00 UTC) com `crontab -e`:

```
0 4 * * * cd /caminho/do/asterion && ASTERION_DATABASE_URL=postgresql+asyncpg://asterion:SENHA@localhost/asterion .venv/bin/python -m asterion.db_backup_cli --docker-container asterion-postgres-1 backup >> backups/backup.log 2>&1
```

**Cópia fora da VPS:** backup só na mesma máquina não protege contra perda da VPS. Copie a pasta `backups/` para outro lugar (outro servidor ou armazenamento em nuvem). Este passo depende do serviço que você escolher e ainda não está automatizado.

**Teste de restauração:** faça antes do lançamento e uma vez por mês, num banco vazio de teste (veja o BACKUP_RESTORE.md). Um backup que nunca foi restaurado não é prova de nada.

## 4. Atualizar versão (deploy)

1. Faça um backup (seção 3).
2. `git pull origin main`.
3. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`.
4. Confira os logs do bot.

## 5. Voltar uma versão (rollback)

Migrations novas podem mudar o banco, então não dá para só voltar o código. Faça assim:

1. Pare o bot: `docker compose --env-file .env.prod -f docker-compose.prod.yml stop bot`.
2. Restaure o backup tirado antes do deploy (seção 3, restauração com `--clean --yes`).
3. Volte o código: `git checkout <commit anterior>`.
4. Suba de novo com `up -d --build`.

Perde-se o que aconteceu no jogo entre o backup e o rollback. Por isso o backup antes de cada deploy.

## O que ainda não está pronto

- Cópia automática dos backups para fora da VPS.
- Métricas e alertas (item B6 do plano).
- Webhook do Telegram com domínio e TLS (necessário para o pagamento Pix).
