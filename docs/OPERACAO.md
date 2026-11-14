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
3. Atualize `ASTERION_BUILD_VERSION` no `.env.prod` para o commit que acabou de baixar (seção 7.1).
4. `docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build`.
5. Confira os logs do bot.
6. Se a telemetria estiver ligada, confira o `build_version` gravado (seção 7.1).

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

## 7. Telemetria de TTK do Beta

Desenho completo em [TTK_DESENHO.md](TTK_DESENHO.md). A tabela é `combat_ttk_records`; consultas prontas em `scripts/ttk_reports.sql`. Ligue com `ASTERION_TTK_TELEMETRY=true` (padrão: desligada) depois de `alembic upgrade head`.

Os comandos `psql` abaixo supõem o container do banco chamado `asterion-postgres-1` (o mesmo da seção 3; confira com `docker ps`) e usuário/banco `asterion`.

### 7.1 `ASTERION_BUILD_VERSION` no deploy

Esta variável é o que separa "antes" e "depois" de um deploy nos relatórios (consulta 5 do `ttk_reports.sql`). Sem ela, a telemetria grava `unknown` (esse comportamento continua igual). Um valor antigo faz o deploy novo parecer o anterior.

**Regra:** o valor deve ser exatamente o commit que está de fato rodando. Nunca invente nem reaproveite o valor do deploy anterior.

No deploy, depois do `git pull` e **antes** do `up -d --build`:

1. Confirme que a pasta não tem alteração local, senão o commit não descreve o que será implantado. O comando abaixo deve imprimir nada:

   ```bash
   git status --porcelain
   ```

2. Pegue o commit:

   ```bash
   git rev-parse --short HEAD
   ```

3. Edite `.env.prod` e deixe a linha com esse valor (exemplo com um commit fictício): `ASTERION_BUILD_VERSION=2a4ee36`. Mantenha uma única linha dessa variável. O limite é 64 caracteres.
4. Suba com `up -d --build` (seção 4). Atenção: `docker compose restart` **não** relê o `.env.prod`; para o valor novo valer, o container precisa ser recriado com `up -d`.

**Depois de reiniciar o bot, confira o valor gravado.** A linha só é gravada quando um combate de Caçada Manual ou Ronda termina, então termine um combate (ou espere um jogador terminar) e rode:

```bash
docker exec -i asterion-postgres-1 psql -U asterion -d asterion -c \
"SELECT build_version, count(*) AS n, max(finished_at) AS ultimo
   FROM combat_ttk_records GROUP BY build_version ORDER BY ultimo DESC LIMIT 5;"
```

A primeira linha deve mostrar o commit do passo 2. Se aparecer `unknown` ou o commit antigo: a variável não foi lida (nome errado, linha duplicada, container não recriado) ou a telemetria está desligada. Corrija e suba de novo; as linhas já gravadas não são alteradas.

**Recomendação (não implementada):** um aviso no log quando `ASTERION_TTK_TELEMETRY=true` e `build_version == "unknown"` seria útil, mas exige mexer em código (`runtime.py` ou `ttk_telemetry.py`) e em testes. Fica para decisão do autor; por ora a conferência acima cobre o risco.

### 7.2 Retenção (remoção manual)

- Os registros são **mantidos durante todo o Beta**.
- Permanecem por **mais 90 dias após o encerramento da análise**.
- Depois disso, a remoção é **manual**. Não existe job automático e nenhum deve ser criado sem decisão do autor.
- **Pendente (autor):** a data de encerramento da análise ainda não foi definida. Enquanto não houver essa data registrada abaixo, **não apague nada**.

Data de encerramento da análise (D): `____-__-__` (preencher quando o autor decidir).
Instante de corte (D, com fuso, por exemplo `YYYY-MM-DD 00:00:00+00`): `__________` (o autor define se o dia D entra ou não).

**Conferência (somente leitura, pode rodar a qualquer momento).** Troque `<CORTE>` pelo instante de corte acima:

```bash
docker exec -i asterion-postgres-1 psql -U asterion -d asterion -c \
"SELECT count(*) AS total,
        count(*) FILTER (WHERE finished_at < '<CORTE>') AS seriam_removidas,
        count(*) FILTER (WHERE finished_at >= '<CORTE>') AS seriam_mantidas,
        min(finished_at) AS mais_antiga, max(finished_at) AS mais_recente,
        now() >= timestamptz '<CORTE>' + interval '90 days' AS prazo_de_90_dias_cumprido
   FROM combat_ttk_records;"
```

**Remoção.** Só execute quando **todas** as condições forem verdadeiras:

1. D e o instante de corte estão preenchidos acima, definidos pelo autor.
2. `prazo_de_90_dias_cumprido` da conferência é `t` (verdadeiro).
3. A análise do Beta foi dada como encerrada pelo autor e as consultas finais já foram guardadas.
4. Há um backup recente (seção 3). Se quiser guardar os dados, exporte antes: `\copy (SELECT * FROM combat_ttk_records WHERE finished_at < '<CORTE>') TO 'ttk_beta.csv' CSV HEADER`.

Passos (a transação permite desfazer antes de confirmar):

```bash
docker exec -it asterion-postgres-1 psql -U asterion -d asterion
```

```sql
BEGIN;
DELETE FROM combat_ttk_records WHERE finished_at < '<CORTE>';
-- Confira o número de linhas informado ("DELETE n") com "seriam_removidas" da conferência.
-- Se o número bater: COMMIT;   Se não bater: ROLLBACK;
```

Depois, repita a conferência: `seriam_removidas` deve ser 0. Anote a data da remoção no HANDOFF.md.

## O que ainda não está pronto

- Cópia automática dos backups para fora da VPS.
- Monitor externo que avise se a VPS ou o bot inteiro cair.
- Webhook do Telegram com domínio e TLS (necessário para o pagamento Pix).
- Data de encerramento da análise do Beta (define quando a retenção da seção 7.2 pode ser executada): decisão do autor, ainda em aberto.
