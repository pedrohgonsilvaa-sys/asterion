# Equipe de agentes do Asterion

Seis papéis em `.claude/agents/`. Cada um é um subagent do Claude Code com ferramentas limitadas.

| Agente | Quando chamar | Escreve em |
|---|---|---|
| `game-director` | Prioridade, escopo, conflito entre documentos | `docs/` |
| `game-designer` | Mecânica nova, progressão, itens, dungeons | `docs/specs/` |
| `narrative-designer` | Missões, escolhas, falas, lore, tom | `docs/specs/`, `docs/` |
| `systems-designer` | Balanceamento, economia, exploits, números | `docs/audits/`, `docs/balance/` |
| `programmer` | Implementar spec aprovada, bug, migration | `src/`, `tests/`, `alembic/` |
| `qa` | Validar contra critérios, testes, regressão | `tests/` (relatório no chat) |

## Fluxo

1. **Director** define o objetivo e quem executa.
2. **Designers** escrevem a spec (com "Lacunas para o autor" e "Critérios de aceite").
3. **Autor** responde as lacunas. Nenhum número é inventado.
4. **Programmer** implementa a spec aprovada.
5. **QA** valida contra os critérios e roda os testes.
6. **Director** confirma e propõe o próximo passo.

## Regras comuns (vêm do CLAUDE.md)

- Autoridade das fontes: `SOURCE_AUTHORITY.md`.
- Sem `.env`, sem `git add .`, sem push sem confirmar, Fase 2E fora.
- Só o Programmer altera `src/` e `alembic/`.
- Economia de créditos: leia só o necessário; `HANDOFF.md` por seção.

## Como usar

Peça em linguagem normal: "chame o game-designer para propor X" ou "use o qa para validar a branch".
Os agentes são carregados na abertura da conversa: se acabaram de ser criados, abra uma conversa nova.
