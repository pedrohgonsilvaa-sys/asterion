# Auditoria — Navegação, Missões, Narrativa individual e Coop (2026-11-11)

Origem: brief `ASTERION_POST_CLAUDE_CODE_IMPLEMENTACAO_NAVEGACAO_MISSOES_COOP_v1_0_2.md`.
Os quatro documentos de decisão citados no brief (Bíblia v4.0.7, Decisão Consolidada de
Navegação, Auditoria de Compatibilidade, Decisão Final de Missões/Coop) não existem no
repositório nem estão registrados em `SOURCE_AUTHORITY.md`. Por decisão do autor, a
implementação seguiu apenas o brief, sem inventar conteúdo.

## Arquitetura encontrada (reaproveitada sem mudança)

| Conceito do brief | Implementação existente |
|---|---|
| Local atual | `WorldState.location` / `region` por personagem (`world_states`) |
| Rotas | `OVERLAND_ROUTE_PAIRS` e gates por par em `RoadService._travel` (`application/road.py`) |
| Descoberta de Local | `LocationDiscovery`, `UNIQUE(character_id, location_id)` |
| Braseiro permanente | `Brazier`, `UNIQUE(character_id, brazier_id)`; `travel_brazier` só entre Braseiros descobertos da mesma Região |
| Braseiro de Masmorra | Rolado por run (`domain/dungeons.py::roll_brazier`); nunca grava em `braziers` |
| Braseiro não remove rota | `travel` escolhe rota quando o par existe, Braseiro só como alternativa |
| Desbravar | `RoadService.explore`: usa `world.location` com lock, não altera Local; semente persistida em `ExplorationAttempt`; retry devolve a tentativa ativa (sem reroll) |
| Mapa | `map_screen` lista só Regiões conhecidas; sem `???`, porcentagem ou catálogo futuro |
| Campanha individual | `Quest` com `UNIQUE(character_id, quest_id)`; progresso, escolhas e `progress` por personagem |
| Coop de combate | `CampaignJourney`, `CampaignSharedEncounter(Member)`, papéis `eligible`/`helper`, scaling congelado, settlement individual |
| Recompensa idempotente | `RewardEvent` e `CampaignObjectiveCredit` por personagem; Ajudante não repete one-time |

## Conflitos reais

1. **Escopo do Coop.** O brief diz que Coop é principalmente Chefes. O GDD v1.6.0 §51.3 e
   §55.1 diz que a cooperação "não é limitada a Chefes" e que evidência objetiva
   (alcançar Local, examinar pista) é creditada a cada participante elegível presente.
   Pela precedência do próprio brief (§24: GDD acima das decisões finais), o comportamento
   do GDD foi mantido. Escolhas e estado narrativo já são individuais (GDD §51.3).
2. **Votação.** Só existem a votação de abandono de Masmorra (não narrativa) e a votação
   da Crônica (evento global por conta, GDD §49, não é Campanha). Nenhuma foi removida.
3. **Caso Alda.** Alda é a NPC da P2, mas "Entregar/Ajudar/Abandonar Alda" não é conteúdo
   canônico. O teste usa flags exclusivas de teste.

## Implementado

- `domain/narrative_identity.py`: condições narrativas declarativas (estado de Missão,
  consequências, Raça, Classe, par Raça + Classe, descobertas, Local) e resolvedor
  determinístico. Ordem: `priority` explícita, depois especificidade, depois id.
  Cada fala exige um fallback comum. Catálogo `NARRATIVE_SCENES` vazio até o autor
  definir o conteúdo.
- `application/narrative_identity.py`: monta o contexto de um personagem a partir das
  tabelas existentes (`characters`, `quests`, `unlocks`, `codex_entries`,
  `location_discoveries`, `braziers`, `world_states`). Sem tabela nova, sem migration.

## Primeira cena: oferta da P2 (Alda Veyr)

Texto aprovado pelo autor em 2026-11-11. A fala canônica da oferta não muda; a fala de
identidade aparece depois dela.

- Raça Cinéreo: Alda liga o nome à história das rotas de cinza (Bíblia v3.0 §2:
  "Cinéreo" não descreve a cor da pele).
- Classe Vigia (sem ser Cinéreo): Alda, que coordena os vigias do Refúgio, reconhece
  o ofício.
- Par Cinéreo + Vigia: opção `[Perguntar pelas rotas antigas]` com resposta da Alda.
  Ela só mostra a fala e não grava estado nem altera a Missão.
- Demais combinações: só a fala canônica. Hemário não recebe fala porque o único gancho
  seria Hemaris, protegido pelo limite de revelação das Terras do Ocaso.

## Não implementado

- Só a oferta da P2 usa o resolvedor; outras cenas dependem de texto aprovado pelo autor.
- Relacionamento/reputação por NPC: não existe modelo reutilizável no código.
