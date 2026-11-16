---
name: project-mercado-decisoes
description: Decisões do autor (2026-11-08) para lacunas do Mercado §28 e Troca Direta §29 no GDD v1.6.0
metadata:
  node_type: memory
  type: project
  originSessionId: d7161925-4ef5-4d20-a2c9-18224f147905
  modified: 2026-11-08T19:22:16.824Z
---

Decisões do autor para lacunas da §28/§29 do GDD v1.6.0:
- Sem teto de Coroas por agora: a venda sempre credita tudo; Crédito Financeiro Pendente espera o autor definir o número.
- Mercado e Troca Direta ficam disponíveis depois do Prólogo.
- Serviços públicos (§27.3, 3 ofertas por Loja) ficam para uma etapa própria.
- Divulgar Loja publica no tópico Mercado se houver configuração (ID do grupo e do tópico); sem ela, mostra texto para copiar. Recarga de 30 min nos dois casos.

Trabalho em `feat/mercado-troca`, no worktree `.worktrees/mercado-troca`, criado do main c750269 (migration 20261108_0037). Implementado em 2026-11-08, no main via PR 100 (merge 1eaf847, feito pelo autor em 2026-11-08, antes de o CI terminar). O repositório é privado no plano gratuito: a API de proteção de branch responde 403 pedindo GitHub Pro, então merge automático não tem como esperar o CI; conferir o CI e fazer o merge à mão. Sem ferramenta de patch de item, as regras "patch suspende listing" e "patch reseta confirmações" não foram feitas. Telas não testadas no Telegram real.

**Why:** o GDD cita teto e "regras de progressão" sem definir valor ou condição; o autor escolheu as opções recomendadas.
**How to apply:** não reabrir essas decisões. Quando o autor definir o teto, ligar o Crédito Pendente na venda. Relacionado: [[project-escopo-beta]], [[project-antiexploit-decisoes]].
