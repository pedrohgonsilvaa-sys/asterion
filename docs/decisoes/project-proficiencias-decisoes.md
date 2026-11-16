---
name: project-proficiencias-decisoes
description: Decisões do autor (2026-11-13) para implementar a Espec. Proficiências de Armas v1.0.0; substitui o kit de Origem antigo
metadata:
  node_type: memory
  type: project
  originSessionId: 3b0d0c0e-0472-42d2-8afb-e7c60df615be
  modified: 2026-11-13T18:05:12.981Z
---

Spec `ASTERION_ESPECIFICACAO_FINAL_PROFICIENCIAS_EQUIPAMENTO_v1_0_0.md` (upload do autor, 2026-11-13) é a autoridade do sistema de Proficiências. Ela traz Maça de volta ao catálogo e manda o kit inicial ser só a arma.

Decisões tomadas na implementação (branch `feat/proficiencias-armas-v1`, worktree `.worktrees/proficiencias-v1`):
- Arma inicial: raridade Comum, nível 1, +0. Só a arma (sem armaduras do kit antigo).
- Treinador de Armas: botão no menu do Refúgio.
- "Arma do Contrapeso" (martelo 1H) recebe identidade Maça (autor delegou).
- Armas antigas sem `weapon_type_id`: migração grava a identidade nos 3 drops antigos de TDO; o resto sem identidade não pode ser equipado (autor delegou).

- Conflito com GDD v1.7.0 (sistema de Proficiências da Fase 2E, categorias Vestes/Leve/Média/Pesada, treino 250-700): autor escolheu a spec nova. Gerados GDD v1.7.1 e contrato Weapon Metadata v1.1.1; SOURCE_AUTHORITY atualizado.

**Why:** a spec não fechava esses pontos. **How to apply:** não reabrir; ver [[project-kit-origem-atualizado]] (armaduras do kit ficaram para depois).
