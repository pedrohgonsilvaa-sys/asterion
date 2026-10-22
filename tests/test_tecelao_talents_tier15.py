from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest

from asterion.domain.arts import TECELAO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, _tick_path_resources, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
FENDA = "talent.tecelao.fenda_precisa"
VEU_DENSO = "talent.tecelao.veu_denso"
TRAMA_DURADOURA = "talent.tecelao.trama_duradoura"
FIO = TECELAO_ART_IDS["fio_cortante"]
CHAMA = TECELAO_ART_IDS["chama_tecida"]
RUPTURA = TECELAO_ART_IDS["ruptura_da_trama"]
VEU_ENTRELACADO = TECELAO_ART_IDS["veu_entrelacado"]
GEADA = TECELAO_ART_IDS["geada_tecida"]
SURTO = TECELAO_ART_IDS["surto_do_veu"]


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    level: int = 34,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
) -> CombatStats:
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "tecelao",
        level,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _combat(
    *,
    path: str | None = "conjurador",
    arts: tuple[str, ...] = (SURTO,),
    talent_ids: tuple[str, ...] = (),
    enemy_count: int = 1,
):
    stats = resolve_combat_stats("tecelao", 34, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Tecelão", "tecelao", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.level = 34
    actor.character_class = "tecelao"
    actor.selected_path = path
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(200),
        per=ZERO,
        crit=ZERO,
        evasion=ZERO,
        block=ZERO,
    )
    actor.hp = actor.stats.hp
    actor.talent_ids = talent_ids

    for index in range(enemy_count):
        enemy = state.fighters["enemy"] if index == 0 else None
        if enemy is None:
            from asterion.domain.combat import Fighter

            enemy = Fighter(
                f"enemy-{index}",
                f"Inimigo {index}",
                34,
                CombatStats(D(5000), D(20), D(0), D(100)),
                D(5000),
                side="enemy",
                takes_turn=False,
                required_for_victory=False,
            )
            state.fighters[f"enemy-{index}"] = enemy
        else:
            enemy.name = "Inimigo 0"
        enemy.level = 34
        enemy.stats = CombatStats(D(5000), D(20), D(0), D(100))
        enemy.hp = D(5000)
        enemy.takes_turn = False
        enemy.required_for_victory = False

    state.player_actions = class_player_actions("tecelao", arts, selected_path=path)
    state.configuration_snapshot = {
        "active_arts": tuple(
            {"slot": index, "art_id": art_id}
            for index, art_id in enumerate(arts, start=1)
        )
    }
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", ZERO, target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _action_events(state, action_id: str):
    return [event for event in state.events if event.action == action_id]


def test_tecelao_tier15_catalog_values_are_present_but_public_gate_stays_closed():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5})
    assert TALENT_DEFINITIONS[FENDA].name == "Fenda Precisa"
    assert TALENT_DEFINITIONS[FENDA].level == 15
    assert TALENT_DEFINITIONS[FENDA].crit_points == D(2)
    assert TALENT_DEFINITIONS[VEU_DENSO].name == "Véu Denso"
    assert TALENT_DEFINITIONS[VEU_DENSO].level == 15
    assert TALENT_DEFINITIONS[VEU_DENSO].defense_percent == D("0.02")
    assert TALENT_DEFINITIONS[TRAMA_DURADOURA].name == "Trama Duradoura"
    assert TALENT_DEFINITIONS[TRAMA_DURADOURA].level == 15

    for talent_id in (FENDA, VEU_DENSO, TRAMA_DURADOURA):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("tecelao", 60, (talent_id,))
        with pytest.raises(TalentSelectionError):
            validate_talent_choices("tecelao", 60, ((1, talent_id),))


@pytest.mark.parametrize("path", (None, "conjurador", "runico"))
def test_internal_static_crit_and_defense_effects_compose_once(path):
    baseline = _internal_stats((), path=path)
    fenda = _internal_stats((FENDA,), path=path)
    veu = _internal_stats((VEU_DENSO,), path=path)
    both = _internal_stats((FENDA, VEU_DENSO), path=path)
    all_three = _internal_stats((FENDA, VEU_DENSO, TRAMA_DURADOURA), path=path)

    assert fenda.crit == baseline.crit + D(2)
    assert fenda.values() == baseline.values()
    expected_veu = (
        class_stats("tecelao", 34).defense
        * (D(1) + (PATH_DEFINITIONS[path].defense if path else ZERO))
        * D("1.02")
        * D("1.015")
    ).quantize(D(1), rounding=ROUND_HALF_UP)
    assert veu.defense == expected_veu
    assert both.crit == baseline.crit + D(2)
    assert both.defense == veu.defense
    assert (both.hp, both.attack, both.agility, both.per, both.evasion, both.block) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
        baseline.per,
        baseline.evasion,
        baseline.block,
    )
    assert _internal_stats((FENDA, VEU_DENSO), path=path) == both
    assert all_three == both


def test_veu_denso_composes_equipment_runes_enchantments_and_single_final_rounding():
    equipment = EquipmentStatContribution(
        defense=D("13.25"),
        rune_percent=(ZERO, ZERO, D("0.035"), ZERO, ZERO, ZERO, ZERO, ZERO),
        rune_points=(ZERO, ZERO, D("0.4"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, D("0.025"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_points=(ZERO, ZERO, D("0.3"), ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    path = PATH_DEFINITIONS["conjurador"]
    raw = class_stats("tecelao", 34).defense * (D(1) + path.defense) * D("1.02")
    raw += equipment.defense
    raw = raw * (D(1) + equipment.rune_percent[2]) + equipment.rune_points[2]
    raw = raw * (D(1) + equipment.enchantment_percent[2]) + equipment.enchantment_points[2]
    expected = (raw * D("1.015")).quantize(D(1), rounding=ROUND_HALF_UP)

    actual = _internal_stats((VEU_DENSO,), path="conjurador", equipment=equipment)
    baseline = _internal_stats((), path="conjurador", equipment=equipment)
    assert actual.defense == expected
    assert actual.defense != baseline.defense
    assert (actual.hp, actual.attack, actual.agility) == (
        baseline.hp,
        baseline.attack,
        baseline.agility,
    )


def test_fenda_precisa_adds_two_crit_points_before_equipment_enhancements():
    equipment = EquipmentStatContribution(
        crit=D("3.5"),
        rune_percent=(ZERO, ZERO, ZERO, ZERO, ZERO, D("0.10"), ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, ZERO, ZERO, ZERO, D("0.05"), ZERO, ZERO),
    )
    expected = (D(5) + D(2) + equipment.crit)
    expected *= D(1) + equipment.rune_percent[5]
    expected *= D(1) + equipment.enchantment_percent[5]

    actual = _internal_stats((FENDA,), equipment=equipment)
    baseline = _internal_stats((), equipment=equipment)

    assert actual.crit == expected
    assert actual.crit > baseline.crit
    assert actual.values() == baseline.values()


def test_tier15_static_effects_do_not_bypass_public_attribute_composition():
    with pytest.raises(TalentSelectionError):
        resolve_combat_stats("tecelao", 60, "remanescente", talent_ids=(FENDA,))
    with pytest.raises(TalentSelectionError):
        resolve_combat_stats("tecelao", 60, "remanescente", talent_ids=(VEU_DENSO,))


@pytest.mark.parametrize(
    ("talent_ids", "expected_window"),
    (((), 2), ((TRAMA_DURADOURA,), 3)),
)
def test_eligible_art_generates_one_trama_after_resolution_with_correct_window(
    talent_ids: tuple[str, ...], expected_window: int
):
    state = _combat(arts=(SURTO,), talent_ids=talent_ids)
    actor_opportunity = state.fighters["player"].opportunity
    result = act(state, SURTO, target_id="enemy")
    events = _action_events(result, SURTO)

    assert len(events) == 1
    trama = result.fighters["player"].path_state["trama_state"]
    assert trama == {
        "origin_art": SURTO,
        "remaining": expected_window,
        "applied_opportunity": actor_opportunity,
    }
    assert "tecelao.trama_gerada" in events[0].path_triggers


def test_trama_duradoura_counts_only_owner_opportunities_and_expires_after_third():
    state = _combat(arts=(FIO,), talent_ids=(TRAMA_DURADOURA,))
    actor = state.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": CHAMA,
        "remaining": 3,
        "applied_opportunity": actor.opportunity,
    }

    _tick_path_resources(state, "enemy")
    assert actor.path_state["trama_state"]["remaining"] == 3
    for expected in (2, 1):
        actor.opportunity += 1
        _tick_path_resources(state, "player")
        assert actor.path_state["trama_state"]["remaining"] == expected
    actor.opportunity += 1
    _tick_path_resources(state, "player")
    assert "trama_state" not in actor.path_state


def test_same_origin_art_keeps_original_trama_without_consuming_or_refreshing():
    state = _combat(arts=(FIO,), talent_ids=(TRAMA_DURADOURA,))
    actor = state.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    before = actor.path_state["trama_state"].copy()
    actor.cooldowns[FIO] = actor.opportunity

    result = act(state, FIO, target_id="enemy")

    assert result.fighters["player"].path_state["trama_state"] == before
    assert _action_events(result, FIO)[0].class_resource_changes == ()


def test_replayed_committed_action_is_a_noop_and_does_not_duplicate_trama():
    state = _combat(arts=(SURTO,), talent_ids=(TRAMA_DURADOURA,))
    committed = act(state, SURTO, target_id="enemy")
    trama_before = committed.fighters["player"].path_state["trama_state"].copy()

    replay = act(committed, SURTO, target_id="enemy")

    assert replay is committed
    assert replay.fighters["player"].path_state["trama_state"] == trama_before
    assert len(_action_events(replay, SURTO)) == 1


@pytest.mark.parametrize("consumer", (SURTO, GEADA, RUPTURA, VEU_ENTRELACADO))
def test_different_eligible_art_consumes_trama_once_and_does_not_regenerate(consumer):
    state = _combat(arts=(FIO, consumer), talent_ids=(TRAMA_DURADOURA,), enemy_count=2)
    primed = act(state, FIO, target_id="enemy")
    assert primed.fighters["player"].path_state["trama_state"]["origin_art"] == FIO
    for key in primed.fighters["player"].cooldowns:
        primed.fighters["player"].cooldowns[key] = primed.fighters["player"].opportunity

    result = act(primed, consumer, target_id=None if consumer == RUPTURA else "enemy")
    events = _action_events(result, consumer)

    assert events
    assert "trama_state" not in result.fighters["player"].path_state
    assert sum(
        change[2] for event in events for change in event.class_resource_changes
        if change[0] == "trama"
    ) == 1
    assert not any("tecelao.trama_gerada" in event.path_triggers for event in events)


def test_invalid_precommit_action_preserves_trama_and_starts_no_cooldown():
    state = _combat(arts=(FIO, SURTO), talent_ids=(TRAMA_DURADOURA,))
    actor = state.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 3,
        "applied_opportunity": actor.opportunity,
    }
    before = actor.path_state["trama_state"].copy()
    result = act(state, SURTO, target_id=actor.id)

    assert result is state
    assert actor.path_state["trama_state"] == before
    assert SURTO not in actor.cooldowns
    assert not _action_events(result, SURTO)


def test_trama_window_roundtrips_codec_without_refresh_or_losing_origin():
    state = _combat(arts=(SURTO,), talent_ids=(TRAMA_DURADOURA,))
    generated = act(state, SURTO, target_id="enemy")
    before = generated.fighters["player"].path_state["trama_state"].copy()
    restored = decode(encode(generated), generated.id, generated.ruleset, generated.version)

    assert restored.fighters["player"].path_state["trama_state"] == before
    actor = restored.fighters["player"]
    actor.opportunity += 1
    _tick_path_resources(restored, "player")
    assert actor.path_state["trama_state"]["remaining"] == 2
    assert actor.path_state["trama_state"]["origin_art"] == SURTO


def test_internal_trama_duradoura_is_not_a_public_acquisition_bypass():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5})
    with pytest.raises(TalentSelectionError):
        validate_talent_choices("tecelao", 60, ((1, TRAMA_DURADOURA),))
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("tecelao", 60, (TRAMA_DURADOURA,))

    valid_tier5 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "tecelao" and definition.level == 5
    )
    assert validate_active_talent_ids("tecelao", 5, (valid_tier5,)) == (valid_tier5,)
