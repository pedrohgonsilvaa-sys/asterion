# Plano de ação (2026-11-11)

Meta: fechar o código de jogo, com 3 trilhas em paralelo. A Crônica abre depois de algumas semanas de jogo. Monetização (§35) por último.

## Regras comuns

- Uma conversa nova por item, numa worktree própria (`.worktrees/<nome>`), com branch `feat/<nome>`.
- Trilhas não tocam nos mesmos arquivos.
- Antes de mexer em regra de jogo: ler `SOURCE_AUTHORITY.md` e a seção da §49 do GDD. Se faltar valor, perguntar ao autor. Não inventar número.
- Rodar só os testes dos arquivos afetados, mais o Ruff. Suíte completa só na Trilha C.
- Cada PR é pequeno e passa pelo check `test` do CI antes do merge.
- Ao terminar um item, atualizar a seção correspondente do `HANDOFF.md` (só a seção necessária).

## Trilha A: código de jogo

| # | Item | Modelo | Pronto quando |
|---|---|---|---|
| A1 | Obras da Batalha de Guildas: efeitos de 6 das 7 Obras e recompensas | Opus | Efeitos e recompensas aplicados, com testes e telas |
| A2 | Marcas de Legado (§16.1) | Opus | Marcas ganhas, guardadas e mostradas, ligadas à Ascensão |
| A3 | Serviços de Ofícios entre jogadores (§27.3) | Opus | Pedido, aceite e entrega transacionais, com testes |
| A4 | Entrada "Calendário" no menu | Sonnet | Tela do Calendário no menu principal |
| A5 | Catálogo de Flavor Text contextual (estrutura) | Sonnet | Catálogo e seleção prontos, textos como rascunho |
| A6 | Integração de visuais e skins (estrutura) | Sonnet | Mecanismo pronto, sem alterar regra mecânica |

## Trilha B: operação

| # | Item | Modelo | Pronto quando |
|---|---|---|---|
| B1 | Agendador único (lock entre instâncias) | Opus | Duas instâncias não rodam o mesmo job ao mesmo tempo, com teste |
| B2 | Backup e restore | Sonnet | Script de backup e restore testado numa base descartável |
| B3 | Deploy, rollback e Dockerfile com `assets/` | Sonnet | Passo a passo documentado e imagem com os assets |
| B4 | Rate limiting e antiabuso geral | Sonnet | Limite por conta nos handlers, com teste |
| B5 | Admin com RBAC e sanções | Opus | Papéis, sanções e registro de auditoria |
| B6 | Métricas e alertas | Sonnet | Métricas expostas e alertas básicos |
| B7 | Teste E2E (criação até Nv.60 e Legado, 6 Classes) e smoke test no Telegram real | Opus | E2E verde. O smoke test é feito pelo autor |

## Trilha C: fechamento

1. Merge do PR 123 (Outbox).
2. Atualizar HANDOFF §8–9 e `README.md`.
3. Autor aprova as escolhas pendentes das partes 5 e 6 da Crônica.
4. ~~Suíte completa em segundo plano, corrigindo as falhas.~~ Feito em 2026-11-12 no main `0f5d07f`: 0 falhas (3.298 passaram; os 290 que perderam o banco no meio foram refeitos por arquivo: 482 passaram).
5. ~~Resolver a divergência TDO v1.0.16 × v1.0.17.~~ Feito em 2026-11-12: v1.0.17 adotada (Bíblia v4.0.7 registrada em 2026-11-11).
6. ~~Balanceamento dos kits em `SIMULAR`.~~ Feito no PR 147.

## Depois

1. Beta fechado no ar, com A e B prontas. Alvo de desenvolvimento: 05/12/2026 (não é promessa pública). Antes dele: telemetria mínima de TTK, auditoria da Crônica contra a Bíblia v4.0.7 e smoke test interno no bot de staging (decisões de 2026-11-14 em `docs/DECISIONS.md`). O Beta pode rodar sem iniciar a temporada competitiva da Crônica.
2. Autor define o Dia 1 da Crônica (o "Dia 1 do lançamento" é o lançamento público, não o início do Beta fechado), envia a Bíblia v4.0.7 e revisa os textos rascunho. A proposta v0.2 da Crônica só é promovida ao `SOURCE_AUTHORITY.md` depois de revisada e aprovada.
3. Monetização §35: provedor de pagamento, Patrono, pagamentos e Passe.

## Briefings (colar na conversa nova)

**A1 (Opus):** Item A1 de `docs/PLANO_DE_ACAO.md`. Implementar os efeitos de 6 das 7 Obras de Guilda e as recompensas da Batalha de Guildas. Ler antes a §49 e a seção de Guildas e Batalha de Guildas do HANDOFF. Se a fonte não definir um valor, perguntar. Worktree `.worktrees/obras-guilda`, branch `feat/obras-guilda`. Pronto: efeitos e recompensas com testes, Ruff limpo, PR aberto.

**B1 (Opus):** Item B1 de `docs/PLANO_DE_ACAO.md`. Garantir que só uma instância rode cada job do agendador (hoje `max_instances=1` vale por processo; ver HANDOFF §10, "Agendador"). Preferir lock no PostgreSQL. Worktree `.worktrees/agendador-unico`, branch `feat/agendador-unico`. Pronto: duas instâncias não duplicam jobs, com teste, Ruff limpo, PR aberto.

**C (Sonnet):** Itens 1 a 2 da Trilha C de `docs/PLANO_DE_ACAO.md`: acompanhar o PR 123 até o merge e atualizar HANDOFF §8–9 e `README.md` com o estado real (Armazém, Fase 2E e Outbox já no main). Só documentação.
