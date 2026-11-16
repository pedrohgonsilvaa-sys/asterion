---
name: project-guildas-decisoes
description: "Decisões do autor (2026-11-07/08) sobre lacunas de Guilda no GDD v1.6.0, branches e o que falta da etapa 2"
metadata:
  node_type: memory
  type: project
  originSessionId: 10d059d0-8d94-4c59-adb4-2d58f0b5b096
  modified: 2026-11-08T16:04:44.537Z
---

Decisões do autor para lacunas da §30 do GDD v1.6.0:
- Qualquer saída de Guilda (voluntária, expulsão, dissolução, exclusão) inicia a recarga de 12h (conta+servidor).
- Fundar Guilda também respeita essa recarga.
- O Líder não pode sair; precisa transferir a liderança antes.
- As 6 Obras além de Alojamentos podem ser construídas, mas ainda não têm efeito. O efeito entra quando o autor definir.
- As Coroas vão para as Obras pela carteira do membro ou pela Tesouraria (só o Líder).
- Se o Líder for o único membro e excluir o personagem, a Guilda é dissolvida na hora.
- O Nome/TAG antigo fica reservado 30 dias após um Renome.
- Suposição minha, sem confirmação do autor: na transferência ou na sucessão, o antigo Líder vira Oficial.

Tudo juntado ao `main` em 2026-11-08 pelo PR 99 (merge c750269; migrations até 20261108_0036; telas ainda não testadas no Telegram real). O autor delegou: antigo Líder vira Oficial; as 6 Obras seguem sem efeito até ele definir. Núcleo commitado em `feat/guildas`. Telas commitadas por outra conversa (GUILDA VISUAL) no mesmo branch. Obras/Tesouraria/Renome/Dissolução/Sucessão ficam em `feat/guildas-obras`, no worktree `.worktrees/guildas-obras`, por causa do conflito com outra conversa na pasta principal. Middleware de atividade, job `guild-upkeep`, telas de Tesouraria/Obras/Renome/Dissolução e o gancho `handle_permanent_ban` também já foram feitos (o Líder banido vira Membro: suposição minha). Fora do escopo: sistema de ban, efeitos das 6 Obras, Juramento/Expedição/GvG.

**Why:** o GDD não define esses casos, e o autor escolheu as opções recomendadas.
**How to apply:** não reabrir essas decisões; confirmar com o autor a suposição sobre o antigo Líder.
