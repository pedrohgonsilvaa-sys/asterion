# Operação em produção (VPS)

Guia curto para colocar o Asterion no ar, fazer backup, restaurar e voltar uma versão.
Requisitos na VPS: Linux com Docker e Docker Compose instalados, e o repositório clonado.

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

## 3. Backup

Cria um arquivo `backups/asterion-AAAAMMDDTHHMMSSZ.dump`, confere que ele é legível e apaga os de mais de 14 dias:

```bash
scripts/backup.sh
```

Agende todo dia (exemplo: 04:00 UTC) com `crontab -e`:

```
0 4 * * * cd /caminho/do/asterion && scripts/backup.sh >> backups/backup.log 2>&1
```

**Cópia fora da VPS:** backup só na mesma máquina não protege contra perda da VPS. Copie a pasta `backups/` para outro lugar (outro servidor ou armazenamento em nuvem). Este passo depende do serviço que você escolher e ainda não está automatizado.

## 4. Teste de restauração (faça antes do lançamento e todo mês)

Restaura num banco de teste, sem tocar no jogo:

```bash
scripts/restore.sh backups/asterion-XXXX.dump
```

O script mostra quantas tabelas foram restauradas em `asterion_restore_check`.

## 5. Restaurar de verdade (desastre)

1. Pare o bot: `docker compose --env-file .env.prod -f docker-compose.prod.yml stop bot`.
2. Restaure: `FORCE_PRODUCAO=1 scripts/restore.sh backups/asterion-XXXX.dump asterion`.
3. Suba o bot de novo: `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d bot`.

Isso **apaga** o banco atual e põe o do backup no lugar. Antes, faça um backup do estado atual, se o banco ainda abrir.

## 6. Atualizar versão (deploy)

1. `scripts/backup.sh` (sempre antes).
2. `git pull origin main`.
3. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`.
4. Confira os logs do bot.

## 7. Voltar uma versão (rollback)

Migrations novas podem mudar o banco, então não dá para só voltar o código. Faça assim:

1. Pare o bot.
2. Restaure o backup tirado no passo 1 do deploy (seção 5).
3. Volte o código: `git checkout <commit anterior>`.
4. Suba de novo com `up -d --build`.

Perde-se o que aconteceu no jogo entre o backup e o rollback. Por isso o backup antes de cada deploy.

## O que ainda não está pronto

- Cópia automática dos backups para fora da VPS.
- Métricas e alertas (item B6 do plano).
- Webhook do Telegram com domínio e TLS (necessário para o pagamento Pix).
