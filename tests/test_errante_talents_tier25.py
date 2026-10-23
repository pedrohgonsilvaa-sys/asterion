from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import pytest

from asterion.domain.class_trials import ERRANTE_ART_IDS, class_player_actions
from asterion.domain.combat import (
    Action,
    ActionEffect,
    Combat,
    DotState,
    Effect,
    Fighter,
    _clear_class_mechanics_for_death,
    _finish_combat,
    _perform,
    act,
    apply_dot_stacks,
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
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
PRECISAO_CRUEL = "talent.errante.precisao_cruel"
COURO_LEVE = "talent.errante.couro_leve"
PASSOS_DA_SOMBRA = "talent.errante.passos_da_sombra"
PASSOS_EFFECT = "class_mechanic.errante.passos_da_sombra.agility"
FERIDA_PROFUNDA = ERRANTE_ART_IDS["ferida_profunda"]
COMBAT_ID = UUID("292d385b-8d9c-4b06-a185-2ec8ca89e09a")


def _battle(
    *,
    arts: tuple[str, ...] = (),
    talents: tuple[str, ...] = (),
    path: str | None = None,
    player_stats: CombatStats | None = None,
    enemy_effects: tuple[Effect, ...] = (),
    enemy_dots: tuple[DotState, ...] = (),
    enemy_evasion: Decimal = ZERO,
    enemy_barrier: Decimal = ZERO,
    player_dots: tuple[DotState, ...] = (),
    combat_id: UUID = COMBAT_ID,
    second_enemy: bool = False,
    level: int = 25,
    enemy_takes_turn: bool = False,
) -> Combat:
    player = Fighter(
        "player.entity",
        "Errante",
        level,
        player_stats or CombatStats(D(1000), D(100), D(100), D(100), crit=D(5)),
        D(1000),
        race="remanescente",
        character_class="errante",
        selected_path=path,
        talent_ids=talents,
    )
    enemy = Fighter(
        "enemy.entity",
        "Alvo",
        level,
        CombatStats(D(10000), ZERO, D(100), D(1), evasion=enemy_evasion),
        D(10000),
        side="enemy",
        takes_turn=enemy_takes_turn,
        effects=list(enemy_effects),
        barrier=enemy_barrier,
        barrier_remaining=2 if enemy_barrier > ZERO else 0,
        barrier_source="test:barrier" if enemy_barrier > ZERO else "",
    )
    actions = class_player_actions("errante", arts, selected_path=path)
    actions["negative_probe"] = Action(
        "negative_probe",
        "Aplicação negativa de teste",
        ZERO,
        attack_debuff=D("0.10"),
        duration=2,
        effect_stat="defense",
        effect_id="test.defense.down",
    )
    actions["weaker_negative_probe"] = Action(
        "weaker_negative_probe",
        "Aplicação rejeitada de teste",
        ZERO,
        attack_debuff=D("0.05"),
        duration=2,
        effect_stat="defense",
        effect_id="test.defense.down",
    )
    actions["multi_negative_probe"] = Action(
        "multi_negative_probe",
        "Aplicação negativa em dois hits",
        D("0.20"),
        hit_count=2,
        effect_trigger_scope="per_hit",
        target_effects=(
            ActionEffect(
                "test.attack.down",
                "attack",
                D("0.10"),
                2,
                kind="debuff",
            ),
        ),
    )
    actions["area_negative_probe"] = Action(
        "area_negative_probe",
        "Aplicação negativa em área",
        ZERO,
        target_mode="all_opponents",
        effect_trigger_scope="per_target",
        target_effects=(
            ActionEffect(
                "test.attack.down",
                "attack",
                D("0.10"),
                2,
                kind="debuff",
            ),
        ),
    )
    actions["positive_probe"] = Action(
        "positive_probe",
        "Buff positivo de teste",
        ZERO,
        target_effects=(
            ActionEffect(
                "test.attack.up",
                "attack",
                D("0.10"),
                2,
                kind="buff",
            ),
        ),
    )
    actions["utility_probe"] = Action(
        "utility_probe", "Utilidade", ZERO, target_mode="self"
    )
    fighters = {"player": player, "enemy": enemy}
    if second_enemy:
        fighters["enemy_two"] = Fighter(
            "enemy.two",
            "Segundo alvo",
            level,
            CombatStats(D(10000), ZERO, D(100), D(1)),
            D(10000),
            side="enemy",
            takes_turn=False,
        )
    state = Combat(
        id=combat_id,
        ruleset=CURRENT_COMBAT_RULESET,
        fighters=fighters,
        player_actions=actions,
        ai_cycle=("enemy.debuff",),
        enemy_actions={
            "enemy.debuff": Action(
                "enemy.debuff",
                "Debuff de outro combatente",
                ZERO,
                attack_debuff=D("0.10"),
                duration=2,
                effect_stat="defense",
                effect_id="enemy.test.defense.down",
            ),
        },
    )
    state.dot_states[enemy.id] = list(enemy_dots)
    state.dot_states[player.id] = list(player_dots)
    return start_combat(state)


def _action_event(state: Combat, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
    )


def _passos_effect(fighter: Fighter) -> Effect | None:
    return next((effect for effect in fighter.effects if effect.id == PASSOS_EFFECT), None)


def _stats_with_internal_talents(
    talent_ids: tuple[str, ...],
    *,
    path: str | None = None,
    equipment: EquipmentStatContribution | None = None,
) -> CombatStats:
    definitions = tuple(TALENT_DEFINITIONS[talent_id] for talent_id in talent_ids)
    return _resolve_combat_stats_with_static_talent_modifiers(
        "errante",
        25,
        "remanescente",
        equipment,
        path,
        _static_talent_modifier_totals(definitions),
        _static_talent_secondary_modifier_totals(definitions),
    )


def _seed_between_chances(lower: Decimal, upper: Decimal, purpose: str) -> UUID:
    for value in range(1, 10000):
        combat_id = UUID(int=value)
        below = CombatRng(combat_id, 0).chance(lower / D(100), purpose)
        above = CombatRng(combat_id, 0).chance(upper / D(100), purpose)
        if not below and above:
            return combat_id
    raise AssertionError("No deterministic combat seed exists for the requested interval.")


@pytest.mark.parametrize(
    ("talent_id", "field", "expected"),
    (
        (PRECISAO_CRUEL, "crit_points", D(2)),
        (COURO_LEVE, "defense_percent", D("0.02")),
    ),
)
@pytest.mark.parametrize("path", (None, "carrasco", "sabotador"))
def test_static_errante_tier25_modifiers_use_the_shared_internal_compositor(
    talent_id: str, field: str, expected: Decimal, path: str | None
):
    baseline = resolve_combat_stats("errante", 25, "remanescente", selected_path=path)
    actual = _stats_with_internal_talents((talent_id,), path=path)
    assert getattr(TALENT_DEFINITIONS[talent_id], field) == expected
    if talent_id == PRECISAO_CRUEL:
        assert actual.crit == baseline.crit + D(2)
        assert actual.values() == baseline.values()
    else:
        path_definition = PATH_DEFINITIONS.get(path or "")
        path_defense = path_definition.defense if path_definition is not None else ZERO
        expected = (
            class_stats("errante", 25).defense
            * (D(1) + path_defense)
            * D("1.02")
            * D("1.015")
        ).quantize(D(1), rounding=ROUND_HALF_UP)
        assert actual.defense == expected
        assert actual.defense > baseline.defense
        assert (actual.hp, actual.attack, actual.agility) == (
            baseline.hp,
            baseline.attack,
            baseline.agility,
        )
        assert (actual.per, actual.crit, actual.evasion, actual.block) == (
            baseline.per,
            baseline.crit,
            baseline.evasion,
            baseline.block,
        )


def test_static_errante_tier25_modifiers_compose_equipment_runes_and_enchantments_once():
    equipment = EquipmentStatContribution(
        defense=D("3"),
        crit=D("1.5"),
        rune_percent=(ZERO, ZERO, D("0.04"), ZERO, ZERO, ZERO, ZERO, ZERO),
        enchantment_percent=(ZERO, ZERO, D("0.03"), ZERO, ZERO, ZERO, ZERO, ZERO),
    )
    baseline = resolve_combat_stats(
        "errante", 25, "remanescente", equipment, "sabotador"
    )
    actual = _stats_with_internal_talents(
        (PRECISAO_CRUEL, COURO_LEVE), path="sabotador", equipment=equipment
    )
    assert actual.crit == baseline.crit + D(2)
    assert actual.defense > baseline.defense
    before_equipment = (
        class_stats("errante", 25).defense
        * (D(1) + PATH_DEFINITIONS["sabotador"].defense)
        * D("1.02")
        + D(3)
    )
    expected = (
        before_equipment
        * D("1.04")
        * D("1.03")
        * D("1.015")
    ).quantize(D(1), rounding=ROUND_HALF_UP)
    assert actual.defense == expected


@pytest.mark.parametrize("talent_id", (PRECISAO_CRUEL, COURO_LEVE, PASSOS_DA_SOMBRA))
def test_errante_nv25_talents_are_valid_only_at_the_required_level(
    talent_id: str,
):
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35})
    assert TALENT_DEFINITIONS[talent_id].level == 25
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("errante", 24, (talent_id,))
    assert validate_active_talent_ids("errante", 25, (talent_id,)) == (talent_id,)
    assert validate_talent_choices("errante", 25, ((1, talent_id),)) == ((1, talent_id),)
    assert resolve_combat_stats("errante", 25, "remanescente", talent_ids=(talent_id,))
    assert talent_points_at_level(25) == 5
    assert validate_active_talent_ids("errante", 25, ("talent.errante.fio_afiado",)) == (
        "talent.errante.fio_afiado",
    )
    assert validate_active_talent_ids("errante", 25, ("talent.errante.brecha_exposta",)) == (
        "talent.errante.brecha_exposta",
    )


def test_precision_cruel_is_exactly_two_static_crit_points_and_is_not_prepared_or_consumed():
    baseline = resolve_combat_stats("errante", 25, "remanescente")
    actual = _stats_with_internal_talents((PRECISAO_CRUEL,))
    assert actual.crit == baseline.crit + D(2)
    assert actual.crit != baseline.crit * D("1.02")
    assert _stats_with_internal_talents((PRECISAO_CRUEL,)).crit == actual.crit


@pytest.mark.parametrize("pvp", (True, False))
def test_precision_cruel_respects_the_pvp_crit_cap_without_changing_pve(
    pvp: bool,
):
    stats = _stats_with_internal_talents(
        (PRECISAO_CRUEL,), equipment=EquipmentStatContribution(crit=D(35))
    )
    purpose = "critical:player:attack:enemy.entity"
    combat_id = _seed_between_chances(D(40), D(42), purpose)
    state = _battle(
        talents=(PRECISAO_CRUEL,),
        player_stats=stats,
        combat_id=combat_id,
    )
    state.pvp_mode = pvp
    resolved = act(state, "attack", target_id="enemy.entity")
    assert _action_event(resolved, "attack").critical is (not pvp)


def test_couro_leve_is_public_only_from_nv25_and_earlier_tiers_stay_valid():
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("errante", 24, (COURO_LEVE,))
    assert validate_active_talent_ids("errante", 25, (COURO_LEVE,)) == (COURO_LEVE,)
    legal = (
        "talent.errante.instinto_rapido",
        "talent.errante.brecha_exposta",
    )
    assert validate_active_talent_ids("errante", 25, legal) == legal


def test_ferida_profunda_applies_bleed_then_grants_five_percent_agility_once():
    state = _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,))
    actor_opportunity = state.fighters["player"].opportunity
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    effect = _passos_effect(resolved.fighters["player"])
    event = _action_event(resolved, FERIDA_PROFUNDA)
    assert resolved.dot_states["enemy.entity"]
    assert resolved.dot_states["enemy.entity"][0].kind == "bleed"
    assert effect is not None
    assert (effect.magnitude, effect.remaining, effect.applied_opportunity) == (
        D("0.05"),
        1,
        actor_opportunity,
    )
    assert resolved.fighters["player"].stat("agility") == D("105")
    assert "errante.passos_da_sombra" in event.path_triggers
    assert PASSOS_EFFECT not in event.actor_effect_ids


def test_successful_debuff_application_without_direct_damage_grants_passos_da_sombra():
    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    resolved = act(state, "negative_probe", target_id="enemy.entity")
    assert any(
        effect.id == "test.defense.down"
        and effect.kind == "debuff"
        and effect.remaining > 0
        for effect in resolved.fighters["enemy"].effects
    )
    assert _passos_effect(resolved.fighters["player"]) is not None
    assert "errante.passos_da_sombra" in _action_event(
        resolved, "negative_probe"
    ).path_triggers


@pytest.mark.parametrize("condition", ("preexisting_debuff", "preexisting_dot"))
def test_existing_negative_state_without_a_new_application_does_not_activate_passos(
    condition: str,
):
    effects = (
        (Effect("enemy.old.down", "defense", D("0.10"), 2, 0, kind="debuff"),)
        if condition == "preexisting_debuff"
        else ()
    )
    dots = (
        (DotState("bleed", 1, 2, D(100), "enemy.entity"),)
        if condition == "preexisting_dot"
        else ()
    )
    state = _battle(
        talents=(PASSOS_DA_SOMBRA,),
        enemy_effects=effects,
        enemy_dots=dots,
    )
    resolved = act(state, "attack", target_id="enemy.entity")
    assert _passos_effect(resolved.fighters["player"]) is None
    assert "errante.passos_da_sombra" not in _action_event(resolved, "attack").path_triggers


def test_weaker_rejected_debuff_attempt_does_not_activate_passos():
    prior = Effect("test.defense.down", "defense", D("0.20"), 2, 0, kind="debuff")
    state = _battle(talents=(PASSOS_DA_SOMBRA,), enemy_effects=(prior,))
    resolved = act(state, "weaker_negative_probe", target_id="enemy.entity")
    assert _passos_effect(resolved.fighters["player"]) is None
    assert "errante.passos_da_sombra" not in _action_event(
        resolved, "weaker_negative_probe"
    ).path_triggers


def test_successful_reapplication_of_an_existing_debuff_activates_passos():
    prior = Effect("test.defense.down", "defense", D("0.10"), 1, 0, kind="debuff")
    state = _battle(talents=(PASSOS_DA_SOMBRA,), enemy_effects=(prior,))
    resolved = act(state, "negative_probe", target_id="enemy.entity")
    assert _passos_effect(resolved.fighters["player"]) is not None
    refreshed = next(
        effect
        for effect in resolved.fighters["enemy"].effects
        if effect.id == "test.defense.down"
    )
    assert refreshed.remaining == 2


@pytest.mark.parametrize("blocked_by", ("resguardo", "dodge"))
def test_blocked_or_dodged_ferida_profunda_does_not_activate_passos(
    blocked_by: str,
):
    state = _battle(
        arts=(FERIDA_PROFUNDA,),
        talents=(PASSOS_DA_SOMBRA,),
        enemy_evasion=D(100) if blocked_by == "dodge" else ZERO,
    )
    enemy = state.fighters["enemy"]
    if blocked_by == "resguardo":
        enemy.ward_charges = 1
        enemy.ward_remaining = 2
        enemy.ward_applied_opportunity = enemy.opportunity
    resolved = act(state, FERIDA_PROFUNDA, target_id=enemy.id)
    event = _action_event(resolved, FERIDA_PROFUNDA)
    assert _passos_effect(resolved.fighters["player"]) is None
    assert not resolved.dot_states[enemy.id]
    if blocked_by == "dodge":
        assert event.dodged
    else:
        assert resolved.fighters["enemy"].ward_charges == 0
        assert any(
            ":dot:bleed:" in event_id
            for event_id in resolved.blocked_application_events
        )


@pytest.mark.parametrize("outcome", ("resists", "immune"))
def test_effect_pipeline_rejections_do_not_create_a_passos_trigger(outcome: str):
    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    target = state.fighters["enemy"]
    effect = Effect("test.negative", "defense", D("0.10"), 2, target.opportunity)
    from asterion.domain.combat import apply_effect

    applied = apply_effect(
        state,
        target,
        effect,
        application_event=f"rejected:{outcome}",
        immunity_passed=outcome != "immune",
        resistance_passed=outcome != "resists",
    )
    assert not applied
    dot_applied = apply_dot_stacks(
        state,
        target,
        kind="bleed",
        snapshots=(D(100),),
        source=state.fighters["player"].id,
        duration=2,
        application_event=f"rejected-dot:{outcome}",
        immunity_passed=outcome != "immune",
        resistance_passed=outcome != "resists",
    )
    assert not dot_applied
    resolved = act(state, "attack", target_id=target.id)
    assert _passos_effect(resolved.fighters["player"]) is None


def test_full_barrier_absorption_does_not_block_a_successful_bleed_application():
    state = _battle(
        arts=(FERIDA_PROFUNDA,),
        talents=(PASSOS_DA_SOMBRA,),
        enemy_barrier=D(10000),
    )
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    event = _action_event(resolved, FERIDA_PROFUNDA)
    assert event.barrier_absorbed > ZERO
    assert event.effective_damage == 0
    assert resolved.dot_states["enemy.entity"]
    assert _passos_effect(resolved.fighters["player"]) is not None


def test_successful_buff_or_defender_or_basic_attack_against_oportunism_do_not_activate_passos():
    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    positive = act(state, "positive_probe", target_id="enemy.entity")
    assert _passos_effect(positive.fighters["player"]) is None

    prior_dot = DotState("bleed", 1, 2, D(100), "enemy.entity")
    state = _battle(talents=(PASSOS_DA_SOMBRA,), enemy_dots=(prior_dot,))
    basic = act(state, "attack", target_id="enemy.entity")
    assert _passos_effect(basic.fighters["player"]) is None

    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    defended = act(state, "defend")
    assert _passos_effect(defended.fighters["player"]) is None


def test_dot_tick_and_another_characters_debuff_do_not_trigger_passos():
    player_dot = DotState("poison", 1, 2, D(100), "enemy.entity")
    state = _battle(talents=(PASSOS_DA_SOMBRA,), player_dots=(player_dot,))
    ticked = act(state, "attack", target_id="enemy.entity")
    assert any(event.action == "dot:poison:tick" for event in ticked.mechanic_events)
    assert _passos_effect(ticked.fighters["player"]) is None

    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    assert _perform(state, "enemy", "enemy.debuff", target_id="player.entity")
    assert any(effect.kind == "debuff" for effect in state.fighters["player"].effects)
    assert _passos_effect(state.fighters["player"]) is None


def test_multi_hit_negative_applications_activate_passos_once_per_action():
    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    resolved = act(state, "multi_negative_probe", target_id="enemy.entity")
    events = [
        event
        for event in resolved.events
        if event.action == "multi_negative_probe"
        and event.actor_entity_id == resolved.fighters["player"].id
    ]
    assert len(events) == 2
    assert len({event.action_instance_id for event in events}) == 1
    assert sum("errante.passos_da_sombra" in event.path_triggers for event in events) == 1
    assert sum(effect.id == PASSOS_EFFECT for effect in resolved.fighters["player"].effects) == 1
    assert len(resolved.fighters["enemy"].effects) == 1


def test_aoe_negative_applications_on_multiple_targets_trigger_once_for_the_action():
    state = _battle(talents=(PASSOS_DA_SOMBRA,), second_enemy=True)
    resolved = act(state, "area_negative_probe")
    assert any(effect.id == "test.attack.down" for effect in resolved.fighters["enemy"].effects)
    assert any(effect.id == "test.attack.down" for effect in resolved.fighters["enemy_two"].effects)
    events = [event for event in resolved.events if event.action == "area_negative_probe"]
    assert len(events) == 2
    assert sum("errante.passos_da_sombra" in event.path_triggers for event in events) == 1
    assert sum(effect.id == PASSOS_EFFECT for effect in resolved.fighters["player"].effects) == 1


def test_passos_is_not_retroactive_and_expires_after_next_owner_turn():
    state = _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,))
    initial_opportunity = state.fighters["player"].opportunity
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    event = _action_event(resolved, FERIDA_PROFUNDA)
    assert PASSOS_EFFECT not in event.actor_effect_ids
    assert all(fact[0] != PASSOS_EFFECT for fact in event.actor_effect_facts)
    effect = _passos_effect(resolved.fighters["player"])
    assert effect is not None
    assert effect.applied_opportunity == initial_opportunity
    assert resolved.fighters["player"].stat("agility") == D(105)

    next_turn_action = act(resolved, "attack", target_id="enemy.entity")
    next_event = _action_event(next_turn_action, "attack")
    assert PASSOS_EFFECT in next_event.actor_effect_ids
    assert _passos_effect(next_turn_action.fighters["player"]) is None
    assert next_turn_action.fighters["player"].stat("agility") == D(100)


def test_interleaved_enemy_turn_does_not_consume_passos_owner_duration():
    state = _battle(
        arts=(FERIDA_PROFUNDA,),
        talents=(PASSOS_DA_SOMBRA,),
        enemy_takes_turn=True,
    )
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    effect = _passos_effect(resolved.fighters["player"])
    assert effect is not None
    assert effect.remaining == 1
    assert resolved.fighters["player"].stat("agility") == D(105)


def test_passos_reapplication_refreshes_one_source_without_stacking():
    state = _battle(talents=(PASSOS_DA_SOMBRA,))
    first = act(state, "negative_probe", target_id="enemy.entity")
    first_effect = _passos_effect(first.fighters["player"])
    assert first_effect is not None
    first_opportunity = first.fighters["player"].opportunity

    second = act(first, "negative_probe", target_id="enemy.entity")
    effects = [effect for effect in second.fighters["player"].effects if effect.id == PASSOS_EFFECT]
    assert len(effects) == 1
    assert effects[0].magnitude == D("0.05")
    assert effects[0].remaining == 1
    assert effects[0].applied_opportunity >= first_opportunity


def test_passos_on_sabotador_does_not_change_interferencia_debuff_duration():
    state = _battle(talents=(PASSOS_DA_SOMBRA,), path="sabotador")
    resolved = act(state, "negative_probe", target_id="enemy.entity")
    debuff = next(
        effect
        for effect in resolved.fighters["enemy"].effects
        if effect.id == "test.defense.down"
    )
    assert debuff.remaining == 3
    effect = _passos_effect(resolved.fighters["player"])
    assert effect is not None and effect.remaining == 1 and effect.magnitude == D("0.05")


def test_passos_and_oportunismo_are_distinct_action_start_and_application_triggers():
    brecha_exposta = "talent.errante.brecha_exposta"
    state = _battle(
        arts=(FERIDA_PROFUNDA,),
        talents=(PASSOS_DA_SOMBRA, brecha_exposta),
    )
    first = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    first_event = _action_event(first, FERIDA_PROFUNDA)
    assert first_event.path_per_bonus == ZERO
    assert _passos_effect(first.fighters["player"]) is not None

    later = act(first, "attack", target_id="enemy.entity")
    later_event = _action_event(later, "attack")
    assert later_event.path_per_bonus == D(4)
    assert "errante.passos_da_sombra" not in later_event.path_triggers


def test_brecha_mortal_against_existing_negative_state_does_not_trigger_passos_by_presence():
    brecha_mortal = ERRANTE_ART_IDS["brecha_mortal"]
    prior = DotState("bleed", 1, 2, D(100), "enemy.entity")
    state = _battle(
        arts=(brecha_mortal,),
        talents=(PASSOS_DA_SOMBRA,),
        enemy_dots=(prior,),
        level=34,
    )
    resolved = act(state, brecha_mortal, target_id="enemy.entity")
    assert _passos_effect(resolved.fighters["player"]) is None


@pytest.mark.parametrize(
    "talent_ids",
    (
        (PRECISAO_CRUEL,),
        (COURO_LEVE,),
        (PASSOS_DA_SOMBRA,),
        (PRECISAO_CRUEL, COURO_LEVE),
        (PRECISAO_CRUEL, PASSOS_DA_SOMBRA),
        (COURO_LEVE, PASSOS_DA_SOMBRA),
        (PRECISAO_CRUEL, COURO_LEVE, PASSOS_DA_SOMBRA),
    ),
)
def test_three_tier25_effects_coexist_without_activating_each_other(
    talent_ids: tuple[str, ...],
):
    stats = _stats_with_internal_talents(talent_ids)
    state = _battle(
        arts=(FERIDA_PROFUNDA,),
        talents=talent_ids,
        player_stats=stats,
    )
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    baseline = resolve_combat_stats("errante", 25, "remanescente")
    assert resolved.fighters["player"].stats.crit == baseline.crit + (
        D(2) if PRECISAO_CRUEL in talent_ids else ZERO
    )
    expected_defense = _stats_with_internal_talents(
        (COURO_LEVE,) if COURO_LEVE in talent_ids else ()
    ).defense
    assert resolved.fighters["player"].stats.defense == expected_defense
    assert (_passos_effect(resolved.fighters["player"]) is not None) is (
        PASSOS_DA_SOMBRA in talent_ids
    )


def test_passos_class_mechanic_buff_is_cleared_on_death_and_combat_end():
    state = act(
        _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,)),
        FERIDA_PROFUNDA,
        target_id="enemy.entity",
    )
    assert _passos_effect(state.fighters["player"]) is not None
    _clear_class_mechanics_for_death(state, "player")
    assert _passos_effect(state.fighters["player"]) is None

    state = act(
        _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,)),
        FERIDA_PROFUNDA,
        target_id="enemy.entity",
    )
    _finish_combat(state, "victory")
    assert _passos_effect(state.fighters["player"]) is None


def test_passos_roundtrips_through_combat_codec_without_resetting_duration_or_source():
    state = _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,))
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    before = _passos_effect(resolved.fighters["player"])
    assert before is not None
    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    after = _passos_effect(restored.fighters["player"])
    assert after is not None
    assert (after.id, after.stat, after.magnitude, after.remaining, after.applied_opportunity) == (
        before.id,
        before.stat,
        before.magnitude,
        before.remaining,
        before.applied_opportunity,
    )
    assert restored.fighters["player"].stat("agility") == D(105)
    consumed = act(restored, "attack", target_id="enemy.entity")
    assert _passos_effect(consumed.fighters["player"]) is None


def test_retry_and_precommit_rejections_do_not_duplicate_or_create_the_agility_buff():
    state = _battle(arts=(FERIDA_PROFUNDA,), talents=(PASSOS_DA_SOMBRA,))
    invalid_action = act(state, "not-an-action")
    invalid_target = act(state, FERIDA_PROFUNDA, target_id="outside.encounter")
    assert invalid_action is state
    assert invalid_target is state
    assert _passos_effect(state.fighters["player"]) is None

    first = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    retry = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    replay = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    assert encode(retry) == encode(first)
    assert encode(replay) == encode(first)
    assert sum(effect.id == PASSOS_EFFECT for effect in first.fighters["player"].effects) == 1


def test_nv5_nv15_nv25_and_nv35_are_valid_while_future_points_accrue():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35})
    assert talent_points_at_level(5) == 1
    assert talent_points_at_level(15) == 3
    assert talent_points_at_level(25) == 5
    assert validate_active_talent_ids(
        "errante", 25, ("talent.errante.fio_afiado", "talent.errante.brecha_exposta")
    ) == ("talent.errante.fio_afiado", "talent.errante.brecha_exposta")
    for future_level in (45, 55):
        future_id = next(
            definition.talent_id
            for definition in TALENT_DEFINITIONS.values()
            if definition.character_class == "errante" and definition.level == future_level
        )
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("errante", 60, (future_id,))
