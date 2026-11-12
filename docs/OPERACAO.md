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

## 6. Métricas e alertas

### Métricas

O bot mostra números da operação no endereço `/metrics`, no formato do Prometheus (uma ferramenta que coleta e guarda métricas). No `docker-compose.prod.yml` ele escuta na porta 9000, só para a própria VPS. Para ver:

```bash
curl -s http://127.0.0.1:9000/metrics
```

Se você definir `ASTERION_METRICS_TOKEN`, a consulta precisa do cabeçalho `Authorization: Bearer <token>`. No modo webhook, a API (FastAPI) mostra o mesmo `/metrics`.

| Métrica | O que mostra |
|---|---|
| `asterion_telegram_updates_total{type,outcome}` | Mensagens e botões do Telegram tratados (`ok` ou `error`) |
| `asterion_telegram_update_duration_seconds` | Tempo para tratar cada update (histograma) |
| `asterion_job_runs_total{job,outcome}` | Execuções de cada job do agendador (`ok` ou `error`) |
| `asterion_job_duration_seconds{job}` | Tempo de cada execução de job (histograma) |
| `asterion_job_consecutive_failures{job}` | Falhas seguidas de um job (volta a 0 quando dá certo) |
| `asterion_job_last_success_timestamp_seconds{job}` | Hora (Unix) do último sucesso de um job |
| `asterion_outbox_messages{status}` | Avisos na Outbox por estado (`pending`, `processing`, `delivered`, `dead`) |
| `asterion_outbox_oldest_open_age_seconds` | Idade do aviso mais antigo ainda esperando entrega |
| `asterion_outbox_dispatch_total{outcome}` | Entregas feitas por este processo (`delivered`, `retried`, `dead`) |
| `asterion_db_up` | 1 se o banco respondeu, 0 se não |
| `asterion_db_pool_connections{state}` | Conexões do jogo com o banco: em uso, livres, extras e tamanho do pool |

Os contadores começam do zero quando o bot reinicia. Isso é normal no Prometheus.

### Alertas no Telegram

Defina `ASTERION_ALERT_CHAT_ID` com o id do chat que vai receber os avisos (seu chat privado com o bot ou um grupo só da equipe). Para descobrir o id, mande uma mensagem ao bot e abra `https://api.telegram.org/bot<TOKEN>/getUpdates` no navegador: o número em `chat.id` é o id. Depois reinicie o bot.

O job `ops-alerts` verifica a cada 60 segundos e manda mensagem direto (sem passar pela Outbox) quando:

- um job falha `ASTERION_ALERT_JOB_FAILURES` vezes seguidas (padrão 3);
- a Outbox tem `ASTERION_ALERT_OUTBOX_BACKLOG` avisos esperando (padrão 500);
- o aviso mais antigo espera há `ASTERION_ALERT_OUTBOX_AGE_SECONDS` segundos (padrão 1800, ou seja, 30 min);
- o banco não responde;
- avisos novos foram para `dead` (veja e reenvie com `python -m asterion.outbox_cli`).

Enquanto o problema continua, o aviso se repete a cada `ASTERION_ALERT_COOLDOWN_SECONDS` (padrão 30 min). Quando o problema some, chega uma mensagem "resolvido". Esses números são limites técnicos, não regras de jogo: ajuste no `.env.prod` se avisar demais ou de menos.

**Limite:** se o bot inteiro cair, ele não consegue avisar. Para isso use um monitor externo que consulte a VPS (por exemplo, um serviço de uptime) ou o Prometheus com as regras abaixo.

### Regras para o Prometheus (opcional)

Se um dia instalar Prometheus e Alertmanager, estas regras equivalem aos alertas acima:

```yaml
groups:
  - name: asterion
    rules:
      - alert: AsterionForaDoAr
        expr: up{job="asterion"} == 0
        for: 2m
      - alert: AsterionBancoFora
        expr: asterion_db_up == 0
        for: 1m
      - alert: AsterionJobFalhando
        expr: asterion_job_consecutive_failures >= 3
      - alert: AsterionOutboxAcumulada
        expr: sum(asterion_outbox_messages{status=~"pending|processing"}) >= 500
        for: 5m
      - alert: AsterionOutboxAtrasada
        expr: asterion_outbox_oldest_open_age_seconds >= 1800
      - alert: AsterionOutboxDead
        expr: increase(asterion_outbox_dispatch_total{outcome="dead"}[15m]) > 0
      - alert: AsterionErrosNoTelegram
        expr: sum(rate(asterion_telegram_updates_total{outcome="error"}[5m])) > 0.1
        for: 10m
```

## O que ainda não está pronto

- Cópia automática dos backups para fora da VPS.
- Monitor externo que avise se a VPS ou o bot inteiro cair.
- Webhook do Telegram com domínio e TLS (necessário para o pagamento Pix).
