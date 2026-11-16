---
name: project-tdo-v1018-mapa-decisoes
description: "Decisões do autor para a proposta TDO v1.0.18 (navegação mapa único, Refúgio hub, Explorar, XP de exploração) em 2026-11-14"
metadata:
  node_type: memory
  type: project
  originSessionId: 2fc4d918-c679-4ec9-bdc5-6474904f8c27
  modified: 2026-11-15T15:09:24.292Z
---

Proposta `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_PROPOSTA.md` (delta sobre v1.0.17_FINAL), origem: seção 9 de `docs/specs/NAVEGACAO_MAPA_UNICO_TDO_PILOTO_RASCUNHO_2026-11-14.md`. Auditoria: `docs/specs/AUDITORIA_FARM_XP_TDO_v1.0.18_2026-11-14.md`. Ainda PROPOSTA, não FINAL.

Decidido pelo autor em 2026-11-14:
- Todos os Locais (Câmara do Poente inclusive) descobertos só por Explorar; Missão não revela Local.
- Refúgio do Ocaso é hub: liga a todos os Locais descobertos, todos voltam a ele. Caçar parte do Refúgio com escolha de Local.
- Inimigo no nível do Local (soulslike), nível do Local = `max_enemy_level`. `unlock_level` sai em Solo, fica individual em Grupo.
- Explorar: ação no Refúgio, sem Vigor, anti-spam 3 s, todo clique revela Local (sorteio uniforme).
- XP de Local novo 2,5% de XP_ref(min(ref, nível)); exploração total 7,70%–8,43% (meta 7–9%).
- Masmorra mantém nível mínimo individual; PowerlevelFactor vale para XP fixa de Missão em Coop.
- Travas de nível de Missões/Masmorras/Grandes viram recomendação.
- Grupo: inimigo no nível do Local; 1ª vitória libera Ronda a todos que lutaram. Masmorra: mínimo = início da Faixa (Cripta 4, Galerias 8).
- Ao abrir o jogo, personagem aparece onde estava. Estrada e Refúgio fora do sorteio. Recovery no Braseiro do próprio Local. Rotas antigas saem (só Refúgio↔Local); Travessia oculta na TdO.
- Anti-spam 3 s vale para Explorar e Desbravar.
- Recovery da Câmara (sem Braseiro) = Refúgio do Ocaso. Desbravar e Ronda agem no Local atual; após Caçar fica no Local com "Voltar ao Refúgio". Revisão 6: nenhuma sugestão aberta.

**Why:** autor quer exploração livre estilo soulslike, com a cidade como ponto de partida.
**How to apply:** ao consolidar a FINAL ou implementar, seguir isto; pendências restantes estão na seção de Pendências da proposta (spoiler da Câmara para o narrative-designer, taxa de vitória do Nv.1 para o QA, decisões 8/9/11 menores, consolidação FINAL).

## Atualização 2026-11-14: virou FINAL

- `ASTERION_CONTEUDO_TERRAS_DO_OCASO_v1.0.18_FINAL.md` vigente e registrada no SOURCE_AUTHORITY.md, com override regional da Fonte Mestra (9 itens). A PROPOSTA foi marcada SUPERADA. Delta de UI = seção 66 do arquivo de UI v1.6.0 (editado no lugar, sem cópia versionada).
- Pend. 17: Câmara no sorteio uniforme; dois textos (pré/pós P6, pela P6 de quem vê); P6 não descobre a Câmara.
- Dec. 8: S4/S5 em Grupo, qualquer criatura do tipo conta. Dec. 9: BKP Desbravar/Habitat é marco único por criatura/Local. Dec. 11: Grupo sem criatura elegível não abre a Caçada e cita todos os membros sem nível.
- L3: Caçada/Desbravar da Estrada escondidos durante P1.
- Abertos: Códice da Câmara (L9), QA-001 em docs/qa/PENDENCIAS_QA.md (taxa de vitória, bloqueada até código), 9 itens no próximo GDD.
- Nada commitado ainda.

## Atualização 2026-11-14: commit e implementação

- Docs commitados em `feat/tdo-v1.0.18` (worktree `.worktrees/tdo-v1018`, base origin/main), commit 62489a5. UI virou cópia v1.6.1 (2026-11-14); PROPOSTA apagada. Referências do override renumeradas para GDD v1.7.1 (9 itens conferidos, só linhas mudaram). Item 8 fica como override (opção A).
- L10-L13 decididas pelo autor (FINAL §33.15): descobertas antigas mantidas sem XP; quem está em Local não descoberto fica e conta como descoberto; Explorar individual em Grupo; anti-spam persistido no banco.
- Plano de 11 fatias do programmer; fatia 1 (domain/tdo_explore.py) aprovada pelo QA. Próxima: fatia 2 (persistência + caso de uso Explorar + migration).
- No worktree: Python `../../.venv/Scripts/python.exe` com `PYTHONPATH=src`.

## Atualização 2026-11-14: fatia 2 commitada

- Commit 45d2ea5 em feat/tdo-v1.0.18 (sem push): TdoExploreService, anti-spam `action_throttle.py`, migration 20261114_0055. QA aprovou com ressalvas.
- L14 decidida: reconciliação L11 na Câmara cria o Códice, sem XP.
- Nota para a fatia de Desbravar: flag `resolving` sem timeout; se Desbravar mantiver transação aberta em combate, precisa timeout/limpeza.
- Próxima: fatia 3 do plano de 11.

## Atualização 2026-11-14: plano trocado por 4 blocos

O plano de 11 fatias foi substituído por 4 blocos, nesta ordem (critérios da FINAL §33.16):
- A. Navegação: Refúgio hub, Caçar com escolha de Local, Voltar ao Refúgio, Recovery pelo Braseiro do Local, personagem aparece onde estava, Travessia oculta, botão/tela Explorar, textos da Câmara pré/pós P6 (crit. 11, 12, 13, 18, 20).
- B. Combate no Local: inimigo no nível do Local, unlock_level em Grupo + dec. 11, Ronda na 1ª vitória inclusive Grupo (crit. 5, 14, 15, 21).
- C. Desbravar: sem "Local novo", sem recarga 5 min, regra de Vigor, BKP única, Caçada/Desbravar escondidos na P1, release_action_slot (flag resolving sem timeout: precisa timeout/limpeza se transação ficar aberta em combate) (crit. 3, 6, 7, 16, 17).
- D. Missões e Masmorras: sem nível mínimo, sem LocationDiscovery, etapas aguardando, menu de Masmorra pela descoberta, nível mínimo de Masmorra, PowerlevelFactor (crit. 8, 9, 10, 21).
- Um bloco por chat. QA-001 pendente. Perguntar antes de commit/push/PR.
- 2026-11-15: bloco A implementado e aprovado com ressalvas pelo QA (265 passed, 1 skip opt-in do playthrough longo). Novos: domain/tdo_hub.py, bot/tdo_hub_ui.py. `_available_local_profile`: Locais da TdO só exigem LocationDiscovery (Estrada: P1). QA-002 aberta para o bloco D: botões de Missão Local–Local mortos, P6 legada grava descoberta da Câmara (application/p6.py), P2/P3 ativas sem "Voltar ao Refúgio". 5 textos utilitários de UI sem fonte (ex.: "Escolha o Local da caçada.").
- 2026-11-15: bloco B commitado cbe8a11 (sem push), QA aprovou com ressalvas (637 passed); F1 corrigido (combate de Desbravar TdO sem min_level em Solo). Novo domain/tdo_combat.py. QA-001 MEDIDA (autor: 1.000 lutas/classe/caso, semente fixa): Estrada ~96-97%; Ruínas Nv.1 varia 7,5% (Sentinela) a 96% (Vigia) sem Artes; Elite 0%. Sem limite de aprovação: autor decide. Para bloco C: Grandes Descobertas ainda com min_level em domain/road.py (~2384, 2406, 2430); decisão 11 virou alerta, não tela com [Voltar]. Para bloco D: limpar gate morto `ruins_route_known`.
- 2026-11-15: bloco C commitado ac1ac80 (sem push). QA aprovou com ressalvas (400 passed nos 29 arquivos afetados). Decisões do autor: RESOLVING_TIMEOUT de 30 s mantido; o BKP "investigação Desbravar 8" fica pendente para o game-designer (não existe no código e a fonte não diz o gatilho); o Habitat por Rastros e Vestígios mantém unlock_level; a decisão 11 agora é tela com [Voltar]. O playthrough opt-in falha em S3 (`s3_view.kind == "route"`, linha ~1381) já em cbe8a11; isso fica para o bloco D. Bloco D também: S4/S5 têm gate de nível 7/8 em s4.py:1099 e s5.py:1169.
- 2026-11-15: bloco D implementado (sem commit); QA aprovou com ressalvas (496 passed). Decisões do autor: travas de descanso/viagem de Braseiro (Nv.8, P2/P3/P4, unlock de rota em application/road.py ~1090/1119/1708) saem no bloco D; XP fixa de Missão com PowerlevelFactor arredonda para inteiro mais próximo; gap do Coop conta só membros elegíveis. Playthrough oscilou no S6 (8 derrotas) sem semente fixa.
- 2026-11-15: bloco D commitado 7895b49 (sem push). QA aprovou (610 passed em 61 arquivos; playthrough 4 de 4 com semente estável só no teste). Empate do arredondamento = para cima (ROUND_HALF_UP). Próximo: push/PR da branch (perguntar). Lacunas de teste baixas: gap Coop não elegível só testado no P5; viagem entre Braseiros TdO sem trava sem teste próprio.
- 2026-11-15: feat/tdo-v1.0.18 enviada; PR 174 aberto (blocos A–D + docs). Merge ainda não autorizado.
