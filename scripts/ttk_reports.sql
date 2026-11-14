-- Relatórios de TTK do Beta (docs/TTK_DESENHO.md).
-- Uso (banco de produção, somente leitura):
--   psql "$DATABASE_URL" -f scripts/ttk_reports.sql
-- Regras: Caçada Manual (hunt_manual) e Ronda (round_auto) nunca se misturam.
-- A métrica principal é player_actions (ações válidas do jogador, um proxy: NÃO é
-- automaticamente as "ações equivalentes" do GDD). duration_seconds é só auxiliar.
-- Mostre sempre o n. Não há meta automática de aprovado/reprovado.
-- Troque o filtro de data e, depois de uma mudança de balanceamento, compare por build_version.

-- 1) TTK por Região e Categoria da criatura (só vitórias, Caçada Manual)
SELECT region_id, creature_category, count(*) AS n,
       round(avg(player_actions), 1) AS media,
       percentile_cont(0.1) WITHIN GROUP (ORDER BY player_actions) AS p10,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY player_actions) AS mediana,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY player_actions) AS p90
FROM combat_ttk_records
WHERE source = 'hunt_manual' AND result = 'victory' AND player_actions > 0
  AND finished_at >= now() - interval '7 days'
GROUP BY region_id, creature_category
ORDER BY region_id, creature_category;

-- 2) Por criatura: TTK das vitórias e taxa de vitória (todas as saídas), Caçada Manual
SELECT creature_id, region_id, creature_category, count(*) AS n,
       round(count(*) FILTER (WHERE result = 'victory')::numeric / count(*), 3) AS taxa_vitoria,
       round(avg(player_actions) FILTER (WHERE result = 'victory' AND player_actions > 0), 1) AS media_vitorias,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY player_actions)
         FILTER (WHERE result = 'victory' AND player_actions > 0) AS mediana_vitorias,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY player_actions)
         FILTER (WHERE result = 'victory' AND player_actions > 0) AS p90_vitorias
FROM combat_ttk_records
WHERE source = 'hunt_manual' AND finished_at >= now() - interval '7 days'
GROUP BY creature_id, region_id, creature_category
ORDER BY region_id, creature_category, creature_id;

-- 3) Chefes: quantas vitórias ficam entre 12 e 18 ações (referência do GDD §49, não é regra)
SELECT count(*) AS n,
       count(*) FILTER (WHERE player_actions BETWEEN 12 AND 18) AS entre_12_e_18,
       round(count(*) FILTER (WHERE player_actions BETWEEN 12 AND 18)::numeric
             / NULLIF(count(*), 0), 3) AS fracao,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY player_actions) AS mediana
FROM combat_ttk_records
WHERE source = 'hunt_manual' AND result = 'victory' AND player_actions > 0
  AND creature_category = 'boss' AND finished_at >= now() - interval '7 days';

-- 4) Resultado por desnível de nível (player_level - enemy_level) e por Classe
SELECT character_class, (player_level - enemy_level) AS desnivel, count(*) AS n,
       count(*) FILTER (WHERE result = 'victory') AS vitorias,
       count(*) FILTER (WHERE result = 'defeat') AS derrotas,
       count(*) FILTER (WHERE result = 'abandoned') AS abandonos
FROM combat_ttk_records
WHERE source = 'hunt_manual' AND finished_at >= now() - interval '7 days'
GROUP BY character_class, (player_level - enemy_level)
ORDER BY character_class, desnivel;

-- 5) Antes e depois de uma mudança: mesma medida por build_version (e ruleset_version)
SELECT build_version, ruleset_version, source, count(*) AS n,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY player_actions) AS mediana,
       percentile_cont(0.1) WITHIN GROUP (ORDER BY player_actions) AS p10,
       percentile_cont(0.9) WITHIN GROUP (ORDER BY player_actions) AS p90
FROM combat_ttk_records
WHERE result = 'victory' AND player_actions > 0
GROUP BY build_version, ruleset_version, source
ORDER BY min(finished_at);

-- Retenção (manual): durante todo o Beta mantenha tudo; depois de encerrada a análise,
-- guarde por mais 90 dias e então apague. Rode só depois dessa data:
--   DELETE FROM combat_ttk_records WHERE finished_at < <data_de_corte>;
