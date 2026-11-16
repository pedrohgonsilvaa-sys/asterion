---
name: project-fase2e-decisoes
description: "Fase 2E v1.9.1: autor aprovou as 3 pendências de GD em 2026-11-13; gates técnicos seguem NO-GO"
metadata:
  node_type: memory
  type: project
  originSessionId: 9ff2fd94-9a6f-40bf-a476-5e241432e0b8
  modified: 2026-11-13T09:46:06.189Z
---

Em 2026-11-13 o autor aprovou as 3 pendências de Game Design da Fase 2E (pacote v1.9.1): IDs e 198 receitas dos 66 regionais, contrato Weapon Metadata v1.1.0, e Saque com os 696 pares (63 + 633) elegíveis; os 24 Torso/Mítico seguem inelegíveis. Registro em `docs/FASE2E_DECISOES_GD_2026-11-13.md` (PR 159).

**Why:** o autor delegou tudo a Claude ("confio em você") e aprovou em bloco, sem rever a lista de pares.

**How to apply:** Fase 2E continua sem integrar nem publicar. Faltam gates técnicos: snapshot assinado do release (Release/DBA), publicação canônica com `SOURCE_AUTHORITY.md`, importação, migration, flag e deploy. Conferência no código do `main`: 226 IDs únicos, sem colisão com os 66 novos e 34 de Origem; 26 dos 46 "existentes" não foram achados no código. Ver [[project-juramento-expedicao-decisoes]] para o catálogo de conteúdo já entregue (6 Eventos, 11 Provações, 5 Rotas no main).
