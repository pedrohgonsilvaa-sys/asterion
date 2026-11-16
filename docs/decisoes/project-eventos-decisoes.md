---
name: project-eventos-decisoes
description: "§21/§49.15 (etapa 6 do Beta): 8 lacunas decididas pelo autor em 2026-11-08; catálogo de Eventos segue vazio até o autor definir conteúdo"
metadata:
  node_type: memory
  type: project
  originSessionId: 720de2a7-ea85-49f1-a6ae-20ec057eafbf
  modified: 2026-11-09T01:55:44.762Z
---

O autor aceitou em 2026-11-08 estas respostas para o que o GDD v1.6.0 não define em §21/§49.15:

1. Reunião sem dano de 5 min antes da Fase 1; fase avança só quando o HP zera; entrada fecha aos 15 min ou no início da fase final, o que vier primeiro.
2. Base do Chefe = Chefe de Masmorra Solo (HP 300%, ATQ 110%, DEF 110%, AGI 100%), uma barra de HP por fase.
3. Ação Significativa = causa dano, cura ou Barreira (Defender não conta). `major_contribution` = golpe que encerra a fase.
4. 10 Vigor reservados na entrada e devolvidos se não houver recompensa. Prazo estourado: sem recompensa.
5. C, XP e Grau usam `Levento`; básicos da Região do Evento (1 Metal + 1 Couro).
6. Eventos não alimentam Recentes.
7. Foreground só durante o combate; a trava de Configuração vale a participação inteira.
8. Reentrada após derrota volta com HP cheio e a participação tem HP próprio, sem alterar `Character.hp` (escolha de implementação, seguindo Arena e retry de Masmorra; avisada ao autor).

**Why:** a fonte não nomeia nenhum Evento: `WORLD_EVENT_CATALOG` está vazio e nada é agendado. O autor adiou o conteúdo em 2026-11-09, para planejar em outra conversa (nome, Região, nível, Chefe de cada fase, textos, Sintonização e nível mínimo de entrada).
**How to apply:** não inventar Evento; ao receber o conteúdo, preencher o catálogo em `domain/world_events.py`. Faltam ainda HUD do Menu Principal e tela de Calendário. Ver [[project-escopo-beta]] e [[project-antiexploit-decisoes]].
