---
name: project-admin-rbac-decisoes
description: "B5 Admin RBAC — 4 papéis, econômicas só Dono, --as + bootstrap-owner, auditar negadas e não leituras, backup fora"
metadata:
  node_type: memory
  type: project
  originSessionId: de959ced-70d6-4c64-90b8-2228918468b9
  modified: 2026-11-12T00:50:13.098Z
---

Decidido pelo autor em 2026-11-11 (GDD §43.7 não define papéis):

- Papéis: Suporte (só leitura), Moderador (sanções, flags/vínculos, denúncias), Operador (outbox requeue, chronicle maintenance), Dono (tudo + papéis).
- Ações econômicas/calendário (chronicle set-day1/extend/pass-grant, engagement code-create/enable/disable): só Dono.
- Identidade no CLI: `--as <telegram_id>` obrigatório; primeiro Dono via `admin_cli bootstrap-owner`, só enquanto não existe Dono.
- Auditoria `admin_actions` append-only: grava ações aceitas e negadas ('denied', transação própria); leituras não.
- `db_backup_cli` fica fora do RBAC.

**Why:** fonte não definia; autor escolheu as opções recomendadas.
**How to apply:** não mudar papéis/permissões sem perguntar. Ver [[project-antiexploit-decisoes]].
