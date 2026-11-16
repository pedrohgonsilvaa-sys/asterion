---
name: project-juramento-expedicao-decisoes
description: "§22/§49.15 (etapa 7 do Beta): 4 lacunas decididas pelo autor em 2026-11-09; catálogo vazio até o autor definir conteúdo"
metadata:
  node_type: memory
  type: project
  originSessionId: f797b3f4-76e6-4a9b-bab9-6ead71599820
  modified: 2026-11-13T03:04:41.711Z
---

O autor escolheu em 2026-11-09, para o que o GDD v1.6.0 não define em §22/§49.15:

1. Provação = 3 combates seguidos: Elite, Elite, Chefe, com a escala de grupo das Masmorras. Vencer o 1º vale 10, o 2º vale 15, o 3º vale 20 + 15 de conclusão. HP continua entre os combates. Derrota mantém os pontos já ganhos.
2. Expedição: Líder ou Oficial monta o roster de 3 a 6 até segunda 18:00. Cada estágio tem 3 opções, com pista no texto: favorável 100, neutra 50, ruim 25; ausência usa o default, que vale 20. Nota do estágio = média do roster. Guilda que não joga fica em 60 (Fracassada).
3. C, básicos e Fragmentos usam o nível do próprio personagem, registrado ao entrar no ciclo. Inimigos da Provação usam a média de nível do grupo.
4. Catálogo vazio, como em Eventos: nada fica disponível até o autor definir Rotas, textos e inimigos.

Atualização 2026-11-13: as 5 Rotas aprovadas estão no main (PR 152). IDs `expedition.*` da Consolidação Final §7, opções `a`/`b`/`c`, campo "Default" das fontes ignorado. Provações continuam vazias: faltam Elite/Chefe, flavor, conclusão e mecânica das ações (P2/P5 da Consolidação).

Feito no worktree `.worktrees/juramento-expedicao`, branch `feat/juramento-expedicao`, no main desde 2026-11-09 (PR 104, merge 636db8f). Escolhas minhas, avisadas ao autor: Provação parada por 30 min encerra; contribuição individual exige dano, cura ou Barreira naquele combate; só quem abriu pode abandonar; a nota final arredonda para baixo; Região dos básicos segue o nível de 10 em 10. Falta: invalidar recompensa por fraude (§22.1), porque o jogo ainda não tem sistema de ban.

**Why:** a fonte só define janelas, limites e recompensas; não diz o que é um objetivo de Provação nem como as escolhas pontuam.
**How to apply:** não reabrir; ao receber o conteúdo, preencher os catálogos. Ver [[project-escopo-beta]] e [[project-eventos-decisoes]].
