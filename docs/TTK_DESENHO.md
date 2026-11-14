# Telemetria de TTK do Beta: desenho e operação

TTK (*time to kill*) é quanto o jogador demora para derrotar uma criatura. Esta telemetria só **observa**: ela não altera combate, XP, loot, liquidação, IA, Ronda nem Caçada. Decisões do autor em 2026-11-14 (`docs/DECISIONS.md`, D-BETA-04). A base é o GDD v1.7.1 §1 (ajustes de Beta são Balanceamento/Telemetria), §49 (Chefe normal com TTK de referência 12–18 ações equivalentes) e §54 (telemetria não substitui o estado autoritativo e não altera regras sozinha).

## O que decide

1. Uma criatura está mais fácil ou mais difícil que as outras da mesma Categoria e Região.
2. O Chefe normal está perto da referência do GDD (12–18 ações equivalentes). **É referência, não regra**: não há aprovado/reprovado automático.
3. Regiões, Categorias e Classes destoando.
4. Depois de uma mudança de balanceamento, o número realmente mudou (compare por `build_version`).

## Escopo (primeira entrega)

Dentro: Caçada Manual (`hunt_manual`), Ronda de Caça (`round_auto`) e expiração/abandono da Caçada Manual. Os dois `source` **nunca** se misturam nos relatórios.

Fora: Eventos Públicos e Provações (segunda entrega), Missões, Masmorras, PvP, PvPvE (inclusive caça-presa de PvPvE), Caçada em Grupo, Exploração com combate e combates roteirizados (Prólogo). Um Elite da Ronda que o jogador enfrenta à mão vira Caçada Manual e é gravado como `hunt_manual`.

## Quando grava

Uma linha por combate, **só no fim**. Não há registro de início.

| Situação | Onde | `result` |
|---|---|---|
| Vitória na Caçada Manual | `RoadService.action`, antes de `_settle_hunt` | `victory` |
| Derrota na Caçada Manual (inclui a que já nasce terminada) | `_settle_road_defeat` | `defeat` |
| Atividade expirada | `_expire_activity` | `abandoned` |
| Encontro da Ronda (vitória ou derrota) | `RoundService._resolve_auto_encounter` | `victory` / `defeat` |

Dupla contagem: a chave primária é `combat_id` e o insert usa `ON CONFLICT DO NOTHING`. Callback repetido, reconnect e `/start` não criam segunda linha. Um retry cria outro combate (outro `combat_id`) e, portanto, outra linha. Uma Caçada que já terminou (vitória ou derrota) nunca é registrada de novo como `abandoned`, porque a expiração só age sobre atividade ainda ativa.

## Tabela `combat_ttk_records`

| Campo | Observação |
|---|---|
| `combat_id` (PK) | O `Combat.id`. |
| `source` | `hunt_manual` ou `round_auto`. |
| `character_id` | Referência com `ON DELETE SET NULL`: ao apagar o personagem, a linha fica, sem vínculo. |
| `character_class`, `player_level` | Do combatente no combate (não o nível depois do XP). |
| `creature_id`, `creature_category`, `enemy_level`, `region_id` | Da `HuntContext`; a Região vem do Local (`tdo`, `vde`, `nareth`, `varzeas`, `altos`, `confins`). |
| `party_size` | 1 (só Solo nesta entrega). |
| `result` | `victory`, `defeat`, `abandoned`. |
| `player_actions` | Ações válidas do jogador = `Combat.version − 0`. |
| `rounds`, `consumable_uses` | `Combat.round` e `Combat.consumable_uses`. |
| `started_at`, `finished_at`, `duration_seconds` | Auxiliares. Só a Caçada Manual finalizada tem duração; Ronda e `abandoned` ficam sem. |
| `ruleset_version` | O `Combat.ruleset` já existente (hoje `gdd-1.4.9-baseline-1.0`). |
| `build_version` | `ASTERION_BUILD_VERSION`. |

Não há `difficulty`: use `creature_category`, `player_level` e `enemy_level` (o desnível é `player_level - enemy_level`, calculado na consulta). Não grava `telegram_id`, nome nem texto.

## Métricas e limites de leitura

- **`player_actions` é um proxy observável.** Conta as ações válidas do jogador (ataque, defesa, Arte, consumível). A linha de base (`start_combat` entrega `version = 0`) é fixada por teste. **Não é automaticamente o conceito de "ações equivalentes" do GDD.**
- **Duração em tempo real é auxiliar.** Na Caçada Manual inclui o tempo em que o jogador ficou parado. A métrica principal é ações/rodadas.
- Percentis com `percentile_cont` (média, mediana, P10, P90). Mostre sempre o `n`; não há tamanho mínimo de amostra definido.
- **Combate que nasce terminado** é gravado com 0 ações; os relatórios filtram `player_actions > 0`.

## Versionamento

- `ruleset_version`: o `Combat.ruleset` que o motor já grava. Ele muda só quando o conjunto de regras muda de versão.
- `build_version`: identificador do deploy, vindo de `ASTERION_BUILD_VERSION` (por exemplo `git rev-parse --short HEAD` no `.env.prod`). **O projeto não tem hoje um identificador de build embutido** (sem SHA no Dockerfile ou no CI), então, sem a variável, grava `unknown`. Uma mudança de balanceamento que não troque o `ruleset` só aparece separada nos relatórios se o `build_version` mudar no deploy. O `pyproject.toml` não foi alterado.

## Ligar, desligar e reverter

- `ASTERION_TTK_TELEMETRY=true` liga (padrão: desligado). Aplique antes `alembic upgrade head`. Desligar é trocar para `false` e reiniciar.
- A gravação é **síncrona na mesma transação** da liquidação e roda num **savepoint**; qualquer erro vira log (`TTK telemetry ...`) e a liquidação segue. Não há fila.
- Reverter o código: remover as 3 chamadas a `_record_ttk` (`road.py`, 3 pontos) e a 1 de `round.py`. Reverter a tabela: `alembic downgrade 20261113_0053` (só apaga `combat_ttk_records`; nenhuma tabela existente foi alterada).

## Consultas

`scripts/ttk_reports.sql` traz as cinco consultas: TTK por Região/Categoria, por criatura (com taxa de vitória), Chefes contra a referência de 12–18, resultado por desnível e Classe, e antes/depois por `build_version`.

## Volume e retenção

Cerca de 250 bytes por linha. Linhas por dia = jogadores × combates por jogador por dia; a Ronda gera muitos combates (todos são gravados, por decisão do autor). Retenção: manter durante todo o Beta e, **depois de encerrada a análise do Beta**, por mais 90 dias; então apagar (`DELETE ... WHERE finished_at < <corte>`). A remoção é manual; nenhum job apaga sozinho.

## Segunda entrega (não feita)

Eventos Públicos e Provações, `local_id` e `variant`, HP final, dano/cura, poder do equipamento, comando de relatório e métricas Prometheus de volume/erro.
