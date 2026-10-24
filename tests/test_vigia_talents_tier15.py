from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import VIGIA_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    _aim_entry,
    _finish_combat,
    _grant_aim,
    _switch_aim_target,
    _tick_path_resources,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatRng,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_modifiers,
    static_talent_secondary_modifiers,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
BASE_CRIT = D(5)
OLHO = "talent.vigia.olho_afiado"
POSTURA = "talent.vigia.postura_vigilante"
MIRA_ESTAVEL = "talent.vigia.mira_estavel"
MAO_FIRME = "talent.vigia.mao_firme"
VOLEIO = "class_art.vigia.voleio"
SARAIVADA = VIGIA_ART_IDS["saraivada"]
COMBAT_ID = UUID("88cfab20-fd98-48df-ae04-dcf7f3ca8ad4")


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    level: int = 34,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
) -> CombatStats:
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "vigia",
        level,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _battle(
    *,
    talents: tuple[str, ...] = (),
    path: str | None = None,
    pvp: bool = False,
    crit: Decimal = BASE_CRIT,
    evasion: Decimal = ZERO,
    enemy_count: int = 1,
    combat_id: UUID = COMBAT_ID,
) -> Combat:
    player = Fighter(
        "player.entity",
        "Vigia",
        34,
        CombatStats(D(1000), D(200), D(80), D(100), crit=crit, evasion=evasion),
        D(1000),
        race="remanescente",
        character_class="vigia",
        selected_path=path,
        talent_ids=talents,
        side="player",
        takes_turn=True,
    )
    fighters = {"player": player}
    for index in range(enemy_count):
        key = f"enemy-{index}"
        fighters[key] = Fighter(
            key,
            key,
            34,
            CombatStats(D(10000), D(10), D(30), D(1)),
            D(10000),
            side="enemy",
            takes_turn=False,
            required_for_victory=False,
        )
    actions = class_player_actions("vigia", (VOLEIO, SARAIVADA), selected_path=path)
    return start_combat(
        Combat(
            combat_id,
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {"hold": Action("hold", "Aguardar", ZERO, target_mode="self")},
            ("hold",),
            pvp_mode=pvp,
        )
    )


def _aim(state: Combat, target_key: str = "enemy-0") -> dict | None:
    return _aim_entry(state.fighters[target_key], state.fighters["player"])


def test_vigia_nv15_definitions_have_canonical_values_and_are_publicly_eligible():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert TALENT_DEFINITIONS[OLHO].level == 15
    assert TALENT_DEFINITIONS[OLHO].crit_points == D(2)
    assert TALENT_DEFINITIONS[POSTURA].level == 15
    assert TALENT_DEFINITIONS[POSTURA].defense_percent == D("0.02")
    assert TALENT_DEFINITIONS[MIRA_ESTAVEL].level == 15

    for slot, talent_id in enumerate((OLHO, POSTURA, MIRA_ESTAVEL), 1):
        assert validate_active_talent_ids("vigia", 15, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("vigia", 15, ((slot, talent_id),)) == (
            (slot, talent_id),
        )
        static_talent_modifiers("vigia", 15, (talent_id,))
        static_talent_secondary_modifiers("vigia", 15, (talent_id,))
        resolve_combat_stats("vigia", 15, "remanescente", talent_ids=(talent_id,))
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("vigia", 14, (talent_id,))

    assert validate_active_talent_ids("vigia", 15, (MAO_FIRME,)) == (MAO_FIRME,)
    assert resolve_combat_stats("vigia", 15, "remanescente", talent_ids=(MAO_FIRME,)).attack > (
        resolve_combat_stats("vigia", 15, "remanescente").attack
    )


@pytest.mark.parametrize(
    ("talent_ids", "expect_crit", "expect_defense"),
    [
        ((), D(5), False),
        ((OLHO,), D(7), False),
        ((POSTURA,), D(5), True),
        ((MIRA_ESTAVEL,), D(5), False),
        ((OLHO, POSTURA), D(7), True),
        ((OLHO, MIRA_ESTAVEL), D(7), False),
        ((POSTURA, MIRA_ESTAVEL), D(5), True),
        ((OLHO, POSTURA, MIRA_ESTAVEL), D(7), True),
    ],
)
def test_static_vigia_tier15_effects_are_independent_and_compose_once(
    talent_ids: tuple[str, ...], expect_crit: Decimal, expect_defense: bool
):
    actual = _internal_stats(talent_ids, path="atirador")
    baseline = _internal_stats((), path="atirador")
    base_def = class_stats("vigia", 34).defense
    path_def = PATH_DEFINITIONS["atirador"].defense
    expected_def = (
        base_def * (D(1) + path_def) * (D("1.02") if expect_defense else D(1))
        * D("1.015")
    ).quantize(D(1), rounding=ROUND_HALF_UP)
    assert actual.crit == expect_crit
    assert actual.defense == expected_def
    assert (actual.hp, actual.attack, actual.agility) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
    )
    assert _internal_stats(talent_ids, path="atirador") == actual


@pytest.mark.parametrize("path", (None, "atirador", "rastreador"))
def test_olho_afiado_and_postura_vigilante_use_shared_static_composition(path):
    equipment = EquipmentStatContribution(
        defense=D("13.25"),
        crit=D("3.5"),
        rune_percent=(ZERO, ZERO, D("0.035"), ZERO, ZERO, D("0.10"), ZERO, ZERO),
        rune_points=(ZERO, ZERO, D("0.4"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, D("0.025"), ZERO, ZERO, D("0.05"), ZERO, ZERO),
        enchantment_points=(ZERO, ZERO, D("0.3"), ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    talents = (OLHO, POSTURA)
    actual = _internal_stats(talents, path=path, equipment=equipment)
    baseline = _internal_stats((), path=path, equipment=equipment)

    base_def = class_stats("vigia", 34).defense
    path_def = PATH_DEFINITIONS[path].defense if path else ZERO
    raw = (base_def * (D(1) + path_def) * D("1.02") + equipment.defense)
    raw = raw * (D(1) + equipment.rune_percent[2]) + equipment.rune_points[2]
    raw = raw * (D(1) + equipment.enchantment_percent[2]) + equipment.enchantment_points[2]
    raw *= D("1.015")

    expected_def = raw.quantize(D(1), rounding=ROUND_HALF_UP)
    expected_crit = (D(5) + D(2) + equipment.crit)
    expected_crit *= D(1) + equipment.rune_percent[5]
    expected_crit *= D(1) + equipment.enchantment_percent[5]
    assert actual.defense == expected_def
    assert actual.crit == expected_crit
    assert actual.defense > baseline.defense
    assert actual.crit == baseline.crit + D(2) * (
        D(1) + equipment.rune_percent[5]
    ) * (D(1) + equipment.enchantment_percent[5])
    assert (actual.hp, actual.attack, actual.agility, actual.per, actual.evasion, actual.block) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
        baseline.per,
        baseline.evasion,
        baseline.block,
    )


def test_olho_afiado_coexists_with_atirador_four_mira_crit_bonus():
    state = _battle(talents=(OLHO,), path="atirador", crit=D(7))
    target = state.fighters["enemy-0"]
    target.path_state["aim_from"] = {
        "player.entity": {
            "stacks": 4,
            "remaining": 2,
            "applied_opportunity": state.fighters["player"].opportunity,
        }
    }
    resolved = act(state, "attack", target_id=target.id)
    event = next(event for event in resolved.events if event.action == "attack")
    assert event.aim_stacks == 4
    assert event.path_crit_bonus == D(6)
    assert resolved.fighters["player"].stats.crit == D(7)


def _seed_between_crit_caps() -> UUID:
    purpose = "critical:player.entity:attack:enemy-0"
    for value in range(1, 10000):
        combat_id = UUID(int=value)
        rng = CombatRng(combat_id)
        if not rng.chance(D("0.40"), purpose) and rng.chance(D("0.43"), purpose):
            return combat_id
    raise AssertionError("No deterministic seed found between the PvP and uncapped chances.")


def test_olho_afiado_crit_remains_percentage_points_and_respects_pvp_only_cap():
    combat_id = _seed_between_crit_caps()
    pvp = _battle(talents=(OLHO,), pvp=True, crit=D(43), combat_id=combat_id)
    pvp_result = act(pvp, "attack", target_id="enemy-0")
    pvp_event = next(event for event in pvp_result.events if event.action == "attack")
    assert not pvp_event.critical

    pve = _battle(talents=(OLHO,), pvp=False, crit=D(43), combat_id=combat_id)
    pve_result = act(pve, "attack", target_id="enemy-0")
    pve_event = next(event for event in pve_result.events if event.action == "attack")
    assert pve_event.critical


@pytest.mark.parametrize(
    ("talents", "expected_duration"),
    [((), 2), ((MIRA_ESTAVEL,), 3)],
)
def test_mira_estavel_changes_only_duration_and_uses_vigia_opportunities(
    talents: tuple[str, ...], expected_duration: int
):
    state = _battle(talents=talents)
    player = state.fighters["player"]
    assert _grant_aim(state, "player", "enemy-0", trigger="direct") == 1
    assert _aim(state)["remaining"] == expected_duration

    # Another participant's turn does not spend a Vigia opportunity.
    _tick_path_resources(state, "enemy-0")
    assert _aim(state)["remaining"] == expected_duration
    for expected_remaining in range(expected_duration - 1, 0, -1):
        player.opportunity += 1
        _tick_path_resources(state, "player")
        assert _aim(state)["remaining"] == expected_remaining
    player.opportunity += 1
    _tick_path_resources(state, "player")
    assert _aim(state) is None


def test_new_mira_renews_window_without_exceeding_path_cap():
    for path, maximum in ((None, 3), ("atirador", 4), ("rastreador", 2)):
        state = _battle(talents=(MIRA_ESTAVEL,), path=path)
        for _ in range(maximum):
            _grant_aim(state, "player", "enemy-0", trigger="direct")
        entry = _aim(state)
        assert entry["stacks"] == maximum
        entry["remaining"] = 1
        previous_opportunity = entry["applied_opportunity"]
        assert _grant_aim(state, "player", "enemy-0", trigger="direct") == maximum
        renewed = _aim(state)
        assert renewed["stacks"] == maximum
        assert renewed["remaining"] == 3
        assert renewed["applied_opportunity"] == previous_opportunity


def test_rastreador_mira_estavel_keeps_three_independent_targets_and_frees_expired_slot():
    state = _battle(talents=(MIRA_ESTAVEL,), path="rastreador", enemy_count=4)
    for target_key in ("enemy-0", "enemy-1", "enemy-2"):
        assert _grant_aim(state, "player", target_key, trigger="direct") == 1
        assert state.fighters[target_key].path_state["aim_from"]["player.entity"]["remaining"] == 3
    assert _grant_aim(state, "player", "enemy-3", trigger="direct") == 0

    state.fighters["enemy-0"].path_state["aim_from"]["player.entity"]["remaining"] = 1
    player = state.fighters["player"]
    player.opportunity += 1
    _tick_path_resources(state, "player")
    assert _aim(state, "enemy-0") is None
    assert _aim(state, "enemy-1")["remaining"] == 2
    assert _aim(state, "enemy-2")["remaining"] == 2
    assert _grant_aim(state, "player", "enemy-3", trigger="direct") == 1
    assert _aim(state, "enemy-3")["remaining"] == 3


def test_atirador_target_switch_still_clears_old_mira_without_visao_persistente():
    state = _battle(talents=(MIRA_ESTAVEL,), path="atirador", enemy_count=2)
    _grant_aim(state, "player", "enemy-0", trigger="direct")
    _switch_aim_target(state, "player", "enemy-1")
    assert _aim(state, "enemy-0") is None


def test_voleio_mira_stavel_marks_only_explicit_successful_primary():
    state = _battle(talents=(MIRA_ESTAVEL,), path="atirador", enemy_count=2)
    resolved = act(state, VOLEIO, target_id="enemy-1")
    assert _aim(resolved, "enemy-1")["remaining"] == 3
    assert _aim(resolved, "enemy-1")["stacks"] == 1
    assert _aim(resolved, "enemy-0") is None

    no_primary = act(
        _battle(talents=(MIRA_ESTAVEL,), path="atirador", enemy_count=2), VOLEIO
    )
    assert all(_aim(no_primary, key) is None for key in ("enemy-0", "enemy-1"))

    dodger = _battle(talents=(MIRA_ESTAVEL,), path="atirador", enemy_count=1)
    dodger.fighters["enemy-0"].stats = CombatStats(
        D(10000), D(10), D(30), D(1), evasion=D(100)
    )
    missed = act(dodger, VOLEIO, target_id="enemy-0")
    miss_event = next(event for event in missed.events if event.action == VOLEIO)
    assert miss_event.dodged and _aim(missed) is None

    barriered = _battle(talents=(MIRA_ESTAVEL,), path="atirador", enemy_count=1)
    target = barriered.fighters["enemy-0"]
    target.barrier = D(100000)
    target.barrier_remaining = 2
    absorbed = act(barriered, VOLEIO, target_id=target.id)
    event = next(event for event in absorbed.events if event.action == VOLEIO)
    assert event.calculated_damage > 0 and event.effective_damage == 0
    assert _aim(absorbed)["remaining"] == 3


def test_mira_estavel_saraivada_generates_at_most_one_mira_per_action():
    state = _battle(talents=(MIRA_ESTAVEL,), path="rastreador")
    resolved = act(state, SARAIVADA, target_id="enemy-0")
    hits = [event for event in resolved.events if event.action == SARAIVADA]
    assert len(hits) == 3
    assert len({event.action_instance_id for event in hits}) == 1
    assert _aim(resolved)["stacks"] == 1
    assert _aim(resolved)["remaining"] == 3


def test_mira_stavel_state_survives_reconnect_and_is_cleared_at_combat_end():
    state = _battle(talents=(MIRA_ESTAVEL,), path="rastreador")
    _grant_aim(state, "player", "enemy-0", trigger="direct")
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert _aim(restored) == _aim(state)

    _finish_combat(restored, "victory")
    assert _aim(restored) is None


def test_vigia_nv5_nv15_nv25_and_nv35_are_authorized():
    assert validate_active_talent_ids("vigia", 15, (MAO_FIRME,)) == (MAO_FIRME,)
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert validate_active_talent_ids("vigia", 60, (OLHO,)) == (OLHO,)
    tier25 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "vigia" and definition.level == 25
    )
    assert validate_active_talent_ids("vigia", 25, (tier25,)) == (tier25,)
    future = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "vigia" and definition.level == 35
    )
    with pytest.raises(TalentSelectionError):
        resolve_combat_stats("vigia", 34, "remanescente", talent_ids=(future,))
    assert resolve_combat_stats("vigia", 60, "remanescente", talent_ids=(future,))
