"""O Despertar dos Flagelos: regras puras (escalonamento, IA, participação, ranking, prêmio)."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from asterion.domain import flagelos as fl
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.professions import MATERIAL_NAMES
from asterion.domain.veu_bestiary import ActionKind

D = Decimal
T0 = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def test_six_regions_with_the_published_flagelos_and_baseline_stats():
    expected = {
        "tdo": ("Varkhenn, o Flagelo das Cinzas", 10, 35_060, 138, 100, 94),
        "vde": ("Nharvek, o Flagelo dos Laços", 20, 51_000, 195, 120, 101),
        "nareth": ("Azharel, o Flagelo do Meridiano", 30, 53_300, 198, 160, 165),
        "varzeas": ("Hemrath, o Flagelo Rubro", 40, 63_880, 320, 177, 190),
        "altos": ("Korvann, o Flagelo do Contrapeso", 50, 98_740, 310, 306, 204),
        "confins_do_veu": ("Vaelith, o Flagelo da Fratura", 60, 107_840, 401, 322, 334),
    }
    assert [region.region_id for region in fl.REGIONS] == list(expected)
    for region in fl.REGIONS:
        f = region.flagelo
        assert (f.name, f.level, f.hp, f.attack, f.defense, f.agility) == expected[region.region_id]
        assert len(f.actions) == 5
        assert f.actions[0].coefficient == D("1.00") and f.actions[0].cooldown is None
        prepared = [a for a in f.actions if a.prepared]
        assert len(prepared) == 1
        assert (prepared[0].coefficient, prepared[0].cooldown) == (D("1.80"), 5)


def test_fragment_names_match_the_material_catalog():
    for region in fl.REGIONS:
        assert MATERIAL_NAMES[region.flagelo.fragment_material_id] == region.flagelo.fragment_name


def test_special_kits_follow_the_specification():
    hem = {a.key: a for a in fl.kit("hemrath")}
    assert hem["restituicao_rubra"].kind is ActionKind.HEAL
    assert (hem["restituicao_rubra"].heal_hp_fraction, hem["restituicao_rubra"].max_uses) == (
        D("0.05"),
        3,
    )
    assert (hem["soro_corrosivo"].dot_kind, hem["soro_corrosivo"].dot_stacks) == ("poison", 1)
    var = {a.key: a for a in fl.kit("varkhenn")}
    assert var["sopro_de_fuligem"].kind is ActionKind.AOE
    assert var["sopro_de_fuligem"].dot_kind == "burn"
    kor = {a.key: a for a in fl.kit("korvann")}
    escora = kor["escora_inversa"]
    assert (escora.stat, escora.magnitude, escora.second_stat, escora.second_magnitude) == (
        "ATQ",
        D("0.08"),
        "DEF",
        -D("0.08"),
    )
    aza = {a.key: a for a in fl.kit("azharel")}
    assert aza["meridiano_divergente"].stat == "AGI" and aza["meridiano_divergente"].cooldown == 4


def test_contribution_points_and_frozen_bar():
    assert fl.CONTRIBUTION_POINTS == {
        "hunt": 1,
        "group_hunt": 1,
        "desbravar": 1,
        "contract": 2,
        "mission": 4,
        "dungeon": 6,
    }
    assert fl.contribution_points("ronda") == 0
    assert fl.apply_points(10, 6, frozen=False) == (16, 6)
    assert fl.apply_points(498, 6, frozen=False) == (500, 2)
    assert fl.apply_points(120, 6, frozen=True) == (120, 0)
    assert fl.percent(271) == 54 and fl.percent(500) == 100


@pytest.mark.parametrize(
    ("minutes", "hp", "atq"),
    [
        (0, "0", "0"),
        (15, "0.08", "0.03"),
        (30, "0.16", "0.06"),
        (45, "0.24", "0.09"),
        (60, "0.32", "0.12"),
        (75, "0.40", "0.15"),
        (90, "0.48", "0.18"),
        (105, "0.56", "0.21"),
        (120, "0.64", "0.24"),
        (135, "0.72", "0.27"),
        (150, "0.80", "0.30"),
        (600, "0.80", "0.30"),
    ],
)
def test_abandonment_table(minutes, hp, atq):
    steps = fl.due_steps(0, T0, T0 + timedelta(minutes=minutes), 0)
    scaling = fl.scaling_for_steps(steps)
    assert (scaling.hp_bonus, scaling.atq_bonus) == (D(hp), D(atq))


def test_scaling_pauses_with_one_combatant_and_needs_complete_intervals():
    assert fl.due_steps(0, T0, T0 + timedelta(hours=5), 1) == 0
    assert fl.due_steps(0, T0, T0 + timedelta(minutes=14, seconds=59), 0) == 0
    assert fl.due_steps(9, T0, T0 + timedelta(hours=5), 0) == 1
    assert fl.due_steps(10, T0, T0 + timedelta(hours=5), 0) == 0


def test_effective_stats_round_once_and_def_agi_do_not_scale():
    assert fl.effective_max_hp(35_060, D("0.08")) == 37_865  # 37.864,8
    assert fl.effective_attack(138, D("0.03")) == 142  # 142,14
    assert fl.effective_max_hp(107_840, D("0.80")) == 194_112
    assert fl.effective_attack(401, D("0.30")) == 521  # 521,3


def test_ai_prepared_then_longest_cooldown_special_then_basic():
    kw = {"hp": D(100), "max_hp": D(100)}
    assert fl.choose_action("varkhenn", cooldowns={}, uses={}, **kw).key == "ultima_fagulha"
    cds = {"ultima_fagulha": 4}
    # CD3 especiais antes da AoE sem recarga; empate pela ordem do kit.
    assert fl.choose_action("varkhenn", cooldowns=cds, uses={}, **kw).key == "cinza_no_pulso"
    cds |= {"cinza_no_pulso": 2}
    assert fl.choose_action("varkhenn", cooldowns=cds, uses={}, **kw).key == "peso_do_entulho"
    cds |= {"peso_do_entulho": 2}
    assert fl.choose_action("varkhenn", cooldowns=cds, uses={}, **kw).key == "sopro_de_fuligem"
    all_cd = {"protocolo_incompativel": 1, "duas_leituras": 1, "reflexo_partido": 1}
    assert fl.choose_action("vaelith", cooldowns=all_cd, uses={}, **kw).key == "fratura_local"
    korvann = {
        "queda_do_contrapeso": 1,
        "escora_inversa": 1,
        "ruptura_de_cabo": 1,
        "carga_distribuida": 1,
    }
    assert fl.choose_action("korvann", cooldowns=korvann, uses={}, **kw).key == (
        "golpe_de_contrapeso"
    )


def test_ai_skips_self_heal_at_full_hp_and_after_three_uses():
    cds = {"sobrecarga_de_matriz": 2}
    full = fl.choose_action("hemrath", cooldowns=cds, uses={}, hp=D(100), max_hp=D(100))
    assert full.key != "restituicao_rubra"
    hurt = fl.choose_action("hemrath", cooldowns=cds, uses={}, hp=D(50), max_hp=D(100))
    assert hurt.key == "restituicao_rubra"
    spent = fl.choose_action(
        "hemrath", cooldowns=cds, uses={"restituicao_rubra": 3}, hp=D(50), max_hp=D(100)
    )
    assert spent.key != "restituicao_rubra"


def test_targets_are_deterministic_and_aoe_hits_everyone():
    present = [uuid4() for _ in range(5)]
    single = fl.action("varkhenn", "golpe_de_cinza")
    assert fl.choose_targets(single, present, 42) == fl.choose_targets(single, present, 42)
    assert len(fl.choose_targets(single, present, 42)) == 1
    aoe = fl.action("varkhenn", "sopro_de_fuligem")
    assert set(fl.choose_targets(aoe, present, 1)) == set(present)


def test_participation_points_count_only_real_results():
    assert fl.participation_points(fl.ParticipationMetrics()) == 0
    # Defender sem prevenção e cura só de overheal chegam aqui como zero.
    assert not fl.is_eligible(fl.ParticipationMetrics(effective_damage=10, meaningful_effects=1))
    assert fl.is_eligible(
        fl.ParticipationMetrics(effective_damage=1, defender_prevented_damage=1, barrier_absorbed=1)
    )
    assert fl.participation_points(fl.ParticipationMetrics(1, 1, 1, 1, 1)) == 5


def test_rankings_metrics_and_tie_breaks():
    a, b, c, d = (UUID(int=i) for i in (1, 2, 3, 4))
    m = fl.ParticipationMetrics
    entries = [
        fl.RankingEntry(a, m(effective_damage=100), T0 + timedelta(seconds=20)),
        fl.RankingEntry(
            b, m(effective_damage=100, effective_healing=5), T0 + timedelta(seconds=30)
        ),
        fl.RankingEntry(c, m(effective_damage=100), T0 + timedelta(seconds=10)),
        fl.RankingEntry(d, m(effective_damage=100), T0 + timedelta(seconds=10)),
    ]
    ranked = [entry.character_id for entry in fl.rank("offensive", entries)]
    # b: mais Participation Points; c e d empatam no instante: character_id decide.
    assert ranked == [b, c, d]
    defensive = fl.rank(
        "defensive",
        [
            fl.RankingEntry(a, m(defender_prevented_damage=10, barrier_absorbed=5), T0),
            fl.RankingEntry(b, m(effective_damage=999), T0),
        ],
    )
    assert [entry.character_id for entry in defensive] == [a]
    assert [e.character_id for e in fl.rank("support", entries)] == [b]


def test_base_reward_uses_global_conventions():
    for level in (10, 20, 30, 40, 50, 60):
        bundle = fl.reward_bundle(level)
        assert bundle.crowns == round_10(D("0.50") * crowns_per_level(level))
        assert (bundle.basics, bundle.fragments) == (3, 0)
    assert fl.reward_xp(10_000) == 800
    assert fl.RANKING_REWARDS == {1: (3, 3), 2: (2, 2), 3: (1, 1)}


def test_equipment_roll_is_one_eligible_with_equal_chance_and_stable():
    eligible = [UUID(int=i) for i in range(1, 5)]
    winner = fl.equipment_winner("evt", eligible)
    assert winner in eligible and fl.equipment_winner("evt", list(reversed(eligible))) == winner
    assert fl.equipment_winner("evt", []) is None
    wins = Counter(fl.equipment_winner(f"evt{i}", eligible) for i in range(4000))
    assert all(800 < wins[c] < 1200 for c in eligible)


def test_recipe_roll_is_25_percent_without_pity_and_stops_after_nine():
    # Com as 9 conhecidas não existe sorteio.
    assert fl.recipe_roll("evt", uuid4(), []) is None
    found = sum(1 for i in range(8000) if fl.recipe_roll(f"evt{i}", "c", ["r1", "r2"]))
    assert 0.22 < found / 8000 < 0.28
    assert {flagelo: len(ids) for flagelo, ids in fl.FLAGELO_RECIPES.items()} == {
        region.flagelo.flagelo_id: 9 for region in fl.REGIONS
    }
