from copy import deepcopy
from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
from uuid import uuid4

import pytest

from asterion.domain.arts import TECELAO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    CombatDamageAura,
    _apply_barrier,
    _barrier_received_multiplier,
    act,
    start_combat,
    use_combat_consumable,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    effective_defense,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
FIO_PERFURANTE = "talent.tecelao.fio_perfurante"
PROTECAO_TECIDA = "talent.tecelao.protecao_tecida"
ALTERNANCIA_FLUIDA = "talent.tecelao.alternancia_fluida"
TRAMA_DURADOURA = "talent.tecelao.trama_duradoura"
FIO_CORTANTE = TECELAO_ART_IDS["fio_cortante"]
CHAMA_TECIDA = TECELAO_ART_IDS["chama_tecida"]
RUPTURA_DA_TRAMA = TECELAO_ART_IDS["ruptura_da_trama"]
VEU_ENTRELACADO = TECELAO_ART_IDS["veu_entrelacado"]
SURTO_DO_VEU = TECELAO_ART_IDS["surto_do_veu"]
ALTERNANCIA_EFFECT = "class_mechanic.tecelao.alternancia_fluida.agility"


def _internal_stats(
    talent_ids: tuple[str, ...],
    *,
    level: int = 25,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
):
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
    path: str | None = None,
    arts: tuple[str, ...] = (FIO_CORTANTE, CHAMA_TECIDA),
    talent_ids: tuple[str, ...] = (),
):
    stats = resolve_combat_stats("tecelao", 25, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Tecelão", "tecelao", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.level = 25
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
    enemy = state.fighters["enemy"]
    enemy.level = 25
    enemy.stats = CombatStats(D(5000), D(20), D(0), D(100))
    enemy.hp = enemy.stats.hp
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


def _action_event(state, action_id: str):
    return next(event for event in reversed(state.events) if event.action == action_id)


def _effect(fighter, effect_id: str):
    return next((effect for effect in fighter.effects if effect.id == effect_id), None)


def test_fio_perfurante_adds_two_static_per_points_in_internal_composition():
    definition = TALENT_DEFINITIONS[FIO_PERFURANTE]
    assert (definition.character_class, definition.level, definition.per_points) == (
        "tecelao",
        25,
        D(2),
    )
    baseline = _internal_stats(())
    with_talent = _internal_stats((FIO_PERFURANTE,))
    assert with_talent.per == baseline.per + D(2)
    public_talent = resolve_combat_stats(
        "tecelao", 25, "remanescente", talent_ids=(FIO_PERFURANTE,)
    )
    public_baseline = resolve_combat_stats("tecelao", 25, "remanescente")
    assert public_talent.per == public_baseline.per + D(2)
    assert (
        with_talent.hp,
        with_talent.attack,
        with_talent.defense,
        with_talent.agility,
        with_talent.crit,
    ) == (
        baseline.hp,
        baseline.attack,
        baseline.defense,
        baseline.agility,
        baseline.crit,
    )
    equipment = EquipmentStatContribution(per=D(3))
    assert _internal_stats((FIO_PERFURANTE,), equipment=equipment).per == (
        _internal_stats((), equipment=equipment).per + D(2)
    )
    near_cap_equipment = EquipmentStatContribution(per=D(29))
    near_cap = _internal_stats((), equipment=near_cap_equipment)
    near_cap_with_talent = _internal_stats(
        (FIO_PERFURANTE,), equipment=near_cap_equipment
    )
    assert near_cap_with_talent.per == D(31)
    assert effective_defense(D(100), near_cap.per) == D(71)
    assert effective_defense(D(100), near_cap_with_talent.per) == D(70)
    assert effective_defense(D(100), D(31)) == D(70)
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("tecelao", 24, (FIO_PERFURANTE,))
    assert validate_active_talent_ids("tecelao", 25, (FIO_PERFURANTE,)) == (
        FIO_PERFURANTE,
    )
    assert resolve_combat_stats("tecelao", 25, "remanescente", talent_ids=(FIO_PERFURANTE,))


def test_same_name_tier45_talents_use_their_own_id_while_public_tier_is_open():
    errante_fio = TALENT_DEFINITIONS["talent.errante.fio_perfurante"]
    assert errante_fio.level == 45
    assert errante_fio.per_points == D(2)
    assert TALENT_DEFINITIONS[FIO_PERFURANTE].per_points == D(2)
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert validate_active_talent_ids("errante", 60, (errante_fio.talent_id,)) == (
        errante_fio.talent_id,
    )


def test_protecao_tecida_is_a_recipient_bonus_and_floors_once_on_real_self_barrier():
    protected_state = _combat(arts=(VEU_ENTRELACADO,), talent_ids=(PROTECAO_TECIDA,))
    baseline_state = _combat(arts=(VEU_ENTRELACADO,))
    assert _barrier_received_multiplier(protected_state, "player") == D("1.05")
    protected = act(protected_state, VEU_ENTRELACADO)
    baseline = act(baseline_state, VEU_ENTRELACADO)
    assert protected.fighters["player"].barrier == D(94)
    assert baseline.fighters["player"].barrier == D(90)
    assert _action_event(protected, VEU_ENTRELACADO).barrier_value == D(94)


@pytest.mark.parametrize(
    ("path", "path_barrier_bonus"), (("conjurador", D("0.06")), ("runico", D("0.15")))
)
def test_protecao_tecida_composes_with_trama_path_bonus_once(path, path_barrier_bonus):
    state = _combat(
        path=path,
        arts=(FIO_CORTANTE, VEU_ENTRELACADO),
        talent_ids=(PROTECAO_TECIDA,),
    )
    primed = act(state, FIO_CORTANTE, target_id="enemy")
    result = act(primed, VEU_ENTRELACADO)
    expected = (D(100) * D("0.90") * (D(1) + path_barrier_bonus) * D("1.05")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    event = _action_event(result, VEU_ENTRELACADO)
    assert event.barrier_value == expected
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert result.fighters["player"].barrier == expected
    assert "trama_state" not in result.fighters["player"].path_state


def test_protecao_tecida_does_not_follow_the_tecelao_caster_to_an_ally():
    state = _combat(arts=(), talent_ids=(PROTECAO_TECIDA,))
    ally = deepcopy(state.fighters["player"])
    ally.id = "ally"
    ally.name = "Aliado"
    ally.character_class = "sentinela"
    ally.side = "player"
    ally.selected_path = None
    ally.talent_ids = ()
    ally.path_state = {}
    ally.effects = []
    ally.barrier_layers = []
    ally.hp = ally.stats.hp
    ally.takes_turn = False
    state.fighters["ally"] = ally
    action = Action(
        "class_art.tecelao.barreira_aliada_teste",
        "Barreira de teste",
        ZERO,
        target_mode="ally",
        target_barrier_coefficient=D("0.50"),
        target_barrier_duration=2,
    )
    state.player_actions[action.id] = action
    result = act(state, action.id, target_id="ally")
    assert result.fighters["ally"].barrier == D(50)
    assert _barrier_received_multiplier(result, "ally") == D(1)
    assert _barrier_received_multiplier(result, "player") == D("1.05")


def test_protecao_tecida_shares_receiver_stage_and_preserves_barrier_source_caps():
    state = _combat(arts=(VEU_ENTRELACADO,), talent_ids=(PROTECAO_TECIDA,))
    state.damage_auras = (
        CombatDamageAura(
            "receiver-aura",
            ("enemy",),
            ("player",),
            ZERO,
            barrier_received_per_source=D("0.10"),
        ),
    )
    player = state.fighters["player"]
    assert _barrier_received_multiplier(state, "player") == D("1.15")
    player.barrier_cap_fraction = D("0.35")
    _apply_barrier(
        player,
        applier_id="source-a",
        effect_definition_id="barrier.a",
        value=300,
        duration=2,
        applied_opportunity=player.opportunity,
        round_number=state.round,
    )
    _apply_barrier(
        player,
        applier_id="source-b",
        effect_definition_id="barrier.b",
        value=10,
        duration=3,
        applied_opportunity=player.opportunity,
        round_number=state.round,
    )
    result = act(state, VEU_ENTRELACADO)
    assert result.fighters["player"].barrier == D(350)
    identities = {layer.identity for layer in result.fighters["player"].barriers}
    assert identities == {
        ("source-a", "barrier.a"),
        ("source-b", "barrier.b"),
        ("player", VEU_ENTRELACADO),
    }


def test_protecao_tecida_also_strengthens_a_received_protection_consumable_once():
    state = _combat(arts=(), talent_ids=(PROTECAO_TECIDA,))
    result = use_combat_consumable(
        state,
        "consumable.protection.vde.ii",
        budget_limit=2,
    )
    event = next(event for event in result.events if event.action.startswith("consumable:"))
    assert event.barrier_value == D(126)
    assert result.fighters["player"].barrier == D(126)
    assert result.fighters["player"].barrier_source == "player:consumable.protecao"


def test_barrier_trama_consumption_grants_alternancia_after_the_barrier_resolution():
    state = _combat(
        path="runico",
        arts=(FIO_CORTANTE, VEU_ENTRELACADO),
        talent_ids=(
            FIO_PERFURANTE,
            PROTECAO_TECIDA,
            ALTERNANCIA_FLUIDA,
            TRAMA_DURADOURA,
            "talent.tecelao.fio_potente",
        ),
    )
    primed = act(state, FIO_CORTANTE, target_id="enemy")
    assert primed.fighters["player"].path_state["trama_state"]["remaining"] == 3
    result = act(primed, VEU_ENTRELACADO)
    actor = result.fighters["player"]
    event = _action_event(result, VEU_ENTRELACADO)
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert event.barrier_value == D(108)
    assert "tecelao.alternancia_fluida" in event.path_triggers
    assert _effect(actor, ALTERNANCIA_EFFECT) is not None
    assert actor.path_state.get("trama_state") is None


@pytest.mark.parametrize("path", (None, "conjurador", "runico"))
def test_alternancia_fluida_is_applied_after_consumption_and_not_on_generation(path):
    state = _combat(
        path=path,
        arts=(FIO_CORTANTE, CHAMA_TECIDA),
        talent_ids=(ALTERNANCIA_FLUIDA,),
    )
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    assert generated.fighters["player"].path_state["trama_state"]["origin_art"] == FIO_CORTANTE
    assert _effect(generated.fighters["player"], ALTERNANCIA_EFFECT) is None

    consumed = act(generated, CHAMA_TECIDA, target_id="enemy")
    actor = consumed.fighters["player"]
    effect = _effect(actor, ALTERNANCIA_EFFECT)
    event = _action_event(consumed, CHAMA_TECIDA)
    assert "trama_state" not in actor.path_state
    assert effect is not None
    assert (effect.magnitude, effect.remaining) == (D("0.05"), 1)
    assert ALTERNANCIA_EFFECT not in {row[0] for row in event.actor_effect_facts}
    assert "tecelao.alternancia_fluida" in event.path_triggers
    assert actor.stat("agility") == actor.stats.agility * D("1.05")

    restored = decode(encode(consumed), consumed.id, consumed.ruleset, consumed.version)
    restored_actor = restored.fighters["player"]
    assert _effect(restored_actor, ALTERNANCIA_EFFECT).remaining == 1
    assert restored_actor.stat("agility") == actor.stats.agility * D("1.05")
    assert act(consumed, CHAMA_TECIDA, target_id="enemy") is consumed

    next_action = act(restored, "attack", target_id="enemy")
    attack_event = _action_event(next_action, "attack")
    assert ALTERNANCIA_EFFECT in {row[0] for row in attack_event.actor_effect_facts}
    assert _effect(next_action.fighters["player"], ALTERNANCIA_EFFECT) is None
    assert next_action.fighters["player"].stat("agility") == actor.stats.agility


def test_same_origin_trama_does_not_activate_alternancia_or_renew_the_resource():
    state = _combat(arts=(FIO_CORTANTE,), talent_ids=(ALTERNANCIA_FLUIDA,))
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    actor = generated.fighters["player"]
    original = actor.path_state["trama_state"].copy()
    actor.cooldowns[FIO_CORTANTE] = actor.opportunity

    repeated = act(generated, FIO_CORTANTE, target_id="enemy")

    assert repeated.fighters["player"].path_state["trama_state"]["origin_art"] == FIO_CORTANTE
    assert _effect(repeated.fighters["player"], ALTERNANCIA_EFFECT) is None
    event = _action_event(repeated, FIO_CORTANTE)
    assert not any(change[0] == "trama" for change in event.class_resource_changes)
    assert event.path_triggers.count("tecelao.trama_gerada") == 0
    assert original["origin_art"] == FIO_CORTANTE


def test_trama_consumption_buff_is_once_per_action_and_invalid_action_preserves_trama():
    state = _combat(
        arts=(FIO_CORTANTE, RUPTURA_DA_TRAMA),
        talent_ids=(ALTERNANCIA_FLUIDA,),
    )
    primed = act(state, FIO_CORTANTE, target_id="enemy")
    actor = primed.fighters["player"]
    actor.path_state["trama_state"]["origin_art"] = FIO_CORTANTE
    invalid = act(primed, RUPTURA_DA_TRAMA, target_id=actor.id)
    assert invalid is primed
    assert actor.path_state["trama_state"]["origin_art"] == FIO_CORTANTE

    for key in actor.cooldowns:
        actor.cooldowns[key] = actor.opportunity
    consumed = act(primed, RUPTURA_DA_TRAMA)
    assert "trama_state" not in consumed.fighters["player"].path_state
    effect = _effect(consumed.fighters["player"], ALTERNANCIA_EFFECT)
    assert effect is not None and effect.magnitude == D("0.05")
    assert sum(
        event.path_triggers.count("tecelao.alternancia_fluida")
        for event in consumed.events
        if event.action == RUPTURA_DA_TRAMA
    ) == 1


def test_tier25_is_valid_at_required_level_and_higher_tiers_require_their_levels():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert validate_active_talent_ids(
        "tecelao", 15, ("talent.tecelao.trama_duradoura",)
    ) == ("talent.tecelao.trama_duradoura",)
    assert talent_points_at_level(25) == 5
    for talent_id in (FIO_PERFURANTE, PROTECAO_TECIDA, ALTERNANCIA_FLUIDA):
        assert TALENT_DEFINITIONS[talent_id].level == 25
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("tecelao", 24, (talent_id,))
        assert validate_active_talent_ids("tecelao", 25, (talent_id,)) == (talent_id,)
        assert validate_active_talent_ids("tecelao", 60, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("tecelao", 60, ((1, talent_id),)) == ((1, talent_id),)
