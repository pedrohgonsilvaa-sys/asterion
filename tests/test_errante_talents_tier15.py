from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.class_trials import ERRANTE_ART_IDS, class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    DotState,
    Effect,
    Fighter,
    _clear_class_mechanics_for_death,
    _effect_token,
    _end_turn,
    _finish_combat,
    _remove_selected_effect_component,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatRng,
    CombatStats,
    _resolve_combat_stats_with_static_talent_modifiers,
    class_stats,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentStatContribution
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    _static_talent_modifier_totals,
    _static_talent_secondary_modifier_totals,
    static_talent_secondary_modifiers,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
BRECHA_EXPOSTA = "talent.errante.brecha_exposta"
REFLEXO = "talent.errante.reflexo"
SANGUE_FRIO = "talent.errante.sangue_frio"
BRECHA_MORTAL = ERRANTE_ART_IDS["brecha_mortal"]
FERIDA_PROFUNDA = ERRANTE_ART_IDS["ferida_profunda"]
CORTE_VELOZ = ERRANTE_ART_IDS["corte_veloz"]
GOLPE_OPORTUNO = ERRANTE_ART_IDS["golpe_oportuno"]
CORTE_DUPLO = ERRANTE_ART_IDS["corte_duplo"]
PASSO_VELADO = ERRANTE_ART_IDS["passo_velado"]
COMBAT_ID = UUID("e1a71f89-9940-4bc1-a77c-b5b66fdaf241")
SANGUE_EFFECT_ID = "errante.sangue_frio.crit"
DEFAULT_ENEMY_HP = D(10000)


def _battle(
    *,
    arts: tuple[str, ...] = (),
    talents: tuple[str, ...] = (),
    path: str | None = None,
    player_evasion: Decimal = ZERO,
    player_crit: Decimal = ZERO,
    player_per: Decimal = ZERO,
    enemy_evasion: Decimal = ZERO,
    enemy_effects: tuple[Effect, ...] = (),
    enemy_dots: tuple[DotState, ...] = (),
    enemy_takes_turn: bool = False,
    enemy_hit_count: int = 1,
    pvp: bool = False,
    enemy_hp: Decimal = DEFAULT_ENEMY_HP,
    combat_id: UUID = COMBAT_ID,
) -> Combat:
    player = Fighter(
        "player.entity",
        "Errante",
        34,
        CombatStats(
            D(1000), D(100), D(100), D(100),
            per=player_per, crit=player_crit, evasion=player_evasion,
        ),
        D(1000),
        race="remanescente",
        character_class="errante",
        selected_path=path,
        talent_ids=talents,
    )
    enemy = Fighter(
        "enemy.entity",
        "Alvo",
        34,
        CombatStats(
            enemy_hp,
            ZERO,
            D(100),
            D(1),
            crit=ZERO,
            evasion=enemy_evasion,
        ),
        enemy_hp,
        side="enemy",
        takes_turn=enemy_takes_turn,
        effects=list(enemy_effects),
    )
    actions = class_player_actions("errante", arts, selected_path=path)
    actions["two_hit_probe"] = Action(
        "two_hit_probe", "Teste de dois hits", D("0.30"), hit_count=2
    )
    actions["utility_probe"] = Action(
        "utility_probe", "Utilidade", ZERO, target_mode="self"
    )
    state = Combat(
        id=combat_id,
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions=actions,
        enemy_actions={
            "enemy.hit": Action(
                "enemy.hit", "Golpe inimigo", D("0.20"), hit_count=enemy_hit_count
            ),
            "hold": Action("hold", "Aguardar", ZERO, target_mode="self"),
        },
        ai_cycle=("enemy.hit",),
        pvp_mode=pvp,
    )
    state.dot_states[enemy.id] = list(enemy_dots)
    return start_combat(state)


def _event(state: Combat, action_id: str, *, hit_index: int | None = None):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
        and (hit_index is None or event.hit_index == hit_index)
    )


def _seed_between_chances(
    lower: Decimal,
    upper: Decimal,
    purpose: str,
    *,
    cursor: int = 0,
) -> UUID:
    for value in range(1, 10000):
        combat_id = UUID(int=value)
        below = CombatRng(combat_id, cursor).chance(lower / D(100), purpose)
        above = CombatRng(combat_id, cursor).chance(upper / D(100), purpose)
        if not below and above:
            return combat_id
    raise AssertionError("No deterministic seed found for the requested chance interval.")


def _seed_for_multihit_crits() -> UUID:
    for value in range(1, 10000):
        combat_id = UUID(int=value)
        first = CombatRng(combat_id, 1).chance(
            D("0.05"), "critical:player:two_hit_probe:enemy.entity:hit:1"
        )
        second = CombatRng(combat_id, 2).chance(
            D("0.05"), "critical:player:two_hit_probe:enemy.entity:hit:2"
        )
        if first and second:
            return combat_id
    raise AssertionError("No deterministic multi-hit seed found.")


def _incoming_dodge(*, combat_id: UUID = COMBAT_ID) -> Combat:
    state = _battle(
        talents=(SANGUE_FRIO,),
        player_evasion=D(100),
        enemy_takes_turn=True,
        combat_id=combat_id,
    )
    state = act(state, "defend")
    dodge = next(
        event
        for event in state.events
        if event.actor_entity_id == state.fighters["enemy"].id
        and event.target == state.fighters["player"].id
        and event.dodged
    )
    assert "errante.sangue_frio_preparado" in dodge.path_triggers
    state.fighters["enemy"].takes_turn = False
    return state


def test_errante_nv15_definitions_are_public_at_level_and_remain_level_gated():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert TALENT_DEFINITIONS[BRECHA_EXPOSTA].level == 15
    assert TALENT_DEFINITIONS[REFLEXO].level == 15
    assert TALENT_DEFINITIONS[SANGUE_FRIO].level == 15
    for talent_id in (BRECHA_EXPOSTA, REFLEXO, SANGUE_FRIO):
        assert validate_active_talent_ids("errante", 15, (talent_id,)) == (talent_id,)
        assert validate_talent_choices("errante", 15, ((1, talent_id),)) == ((1, talent_id),)
        assert static_talent_secondary_modifiers("errante", 15, (talent_id,)) is not None
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("errante", 14, (talent_id,))


@pytest.mark.parametrize(
    ("condition", "expected_bonus"),
    [
        ("dot", D(4)),
        ("debuff", D(4)),
        ("multiple", D(4)),
        ("expired", ZERO),
        ("fixed_effect", ZERO),
        ("buff", ZERO),
        ("internal_mark", ZERO),
        ("none", ZERO),
    ],
)
def test_brecha_exposta_uses_only_valid_action_start_negative_effects(
    condition: str, expected_bonus: Decimal
):
    effects = ()
    dots = ()
    if condition in {"debuff", "multiple", "expired", "fixed_effect"}:
        effects = (
            Effect(
                "enemy.defense.down",
                "defense",
                D("0.10"),
                0 if condition == "expired" else 2,
                0,
                kind="debuff",
                fixed_mechanic=condition == "fixed_effect",
            ),
        )
    if condition == "multiple":
        effects += (
            Effect("enemy.attack.down", "attack", D("0.10"), 2, 0, kind="debuff"),
        )
        dots = (DotState("poison", 1, 2, D(100), "enemy.entity"),)
    if condition == "dot":
        dots = (DotState("poison", 1, 2, D(100), "enemy.entity"),)
    if condition == "buff":
        effects = (
            Effect("enemy.positive", "agility", D("0.10"), 2, 0, kind="buff"),
        )
    state = _battle(
        talents=(BRECHA_EXPOSTA,),
        enemy_effects=effects,
        enemy_dots=dots,
    )
    if condition == "internal_mark":
        state.fighters["enemy"].path_state["omen_offensive"] = {"player.entity": {"remaining": 2}}

    resolved = act(state, "attack", target_id="enemy.entity")
    assert _event(resolved, "attack").path_per_bonus == expected_bonus
    if condition in {"dot", "multiple"}:
        assert len(resolved.dot_states["enemy.entity"]) == 1


def test_brecha_exposta_applies_to_brecha_mortal_with_its_own_ten_points():
    state = _battle(
        arts=(BRECHA_MORTAL,),
        talents=(BRECHA_EXPOSTA,),
        enemy_effects=(Effect("enemy.down", "defense", D("0.1"), 2, 0, kind="debuff"),),
    )
    resolved = act(state, BRECHA_MORTAL, target_id="enemy.entity")
    assert _event(resolved, BRECHA_MORTAL).path_per_bonus == D(14)


def test_brecha_mortal_and_brecha_exposta_respect_the_global_per_cap():
    state = _battle(
        arts=(BRECHA_MORTAL,),
        talents=(BRECHA_EXPOSTA,),
        player_per=D(25),
        enemy_effects=(Effect("enemy.down", "defense", D("0.1"), 2, 0, kind="debuff"),),
    )
    resolved = act(state, BRECHA_MORTAL, target_id="enemy.entity")
    event = _event(resolved, BRECHA_MORTAL)
    expected_base = direct_damage(
        D(100), D("1.30"), D(90), 34, penetration=D(30)
    )
    expected = int(D(expected_base) * D("1.08"))
    assert event.path_per_bonus == D(14)
    assert event.calculated_damage == expected


@pytest.mark.parametrize(
    "art_id",
    ("attack", CORTE_VELOZ, GOLPE_OPORTUNO, BRECHA_MORTAL, CORTE_DUPLO),
)
def test_brecha_exposta_is_shared_across_offensive_errante_actions(art_id: str):
    arts = (art_id,) if art_id in ERRANTE_ART_IDS.values() else ()
    state = _battle(
        arts=arts,
        talents=(BRECHA_EXPOSTA,),
        enemy_effects=(Effect("enemy.down", "defense", D("0.1"), 2, 0, kind="debuff"),),
    )
    resolved = act(state, art_id, target_id="enemy.entity")
    events = [event for event in resolved.events if event.action == art_id]
    assert events
    expected_bonus = D(14) if art_id == BRECHA_MORTAL else D(4)
    assert all(event.path_per_bonus == expected_bonus for event in events)
    if art_id == CORTE_DUPLO:
        assert [(event.hit_index, event.hit_count) for event in events] == [(1, 2), (2, 2)]


def test_ferida_profunda_does_not_retroactively_enable_oportunismo():
    state = _battle(arts=(FERIDA_PROFUNDA,), talents=(BRECHA_EXPOSTA,))
    resolved = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    first = _event(resolved, FERIDA_PROFUNDA)
    assert first.path_per_bonus == ZERO
    assert resolved.dot_states["enemy.entity"]
    next_action = act(resolved, "attack", target_id="enemy.entity")
    assert _event(next_action, "attack").path_per_bonus == D(4)


def test_purification_of_the_only_negative_effect_removes_brecha_exposta_eligibility():
    debuff = Effect("enemy.down", "defense", D("0.1"), 2, 0, kind="debuff")
    state = _battle(talents=(BRECHA_EXPOSTA,), enemy_effects=(debuff,))
    target = state.fighters["enemy"]
    removed = _remove_selected_effect_component(
        state,
        "enemy",
        _effect_token(state.fighters["enemy"].effects[0], 0),
        "purification",
    )
    assert removed is not None
    resolved = act(state, "attack", target_id=target.id)
    assert _event(resolved, "attack").path_per_bonus == ZERO


def test_reflexo_is_one_static_evasion_point_and_composes_with_equipment():
    definition = TALENT_DEFINITIONS[REFLEXO]
    secondary = _static_talent_secondary_modifier_totals((definition,))
    assert secondary == (ZERO, ZERO, D(1), ZERO)

    equipment = EquipmentStatContribution(evasion=D("2.5"))
    baseline = _resolve_combat_stats_with_static_talent_modifiers(
        "errante", 34, "remanescente", equipment, "carrasco",
        (ZERO, ZERO, ZERO, ZERO),
    )
    actual = _resolve_combat_stats_with_static_talent_modifiers(
        "errante", 34, "remanescente", equipment, "carrasco",
        _static_talent_modifier_totals((definition,)), secondary,
    )
    assert actual.evasion == baseline.evasion + D(1)
    assert (actual.hp, actual.attack, actual.defense, actual.agility) == (
        baseline.hp,
        baseline.attack,
        baseline.defense,
        baseline.agility,
    )
    assert actual.evasion == class_stats("errante", 34).evasion + D("2.5") + D(1)


def test_reflexo_static_modifier_is_available_through_public_stats():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    baseline = resolve_combat_stats("errante", 34, "remanescente")
    actual = resolve_combat_stats("errante", 34, "remanescente", talent_ids=(REFLEXO,))
    assert actual.evasion == baseline.evasion + D(1)
    assert actual.defense == baseline.defense


def test_reflexo_adds_to_passo_velado_without_changing_its_duration_or_magnitude():
    # The runtime tier gate is intentionally bypassed only at the internal stats fixture.
    state = _battle(player_evasion=D(7))
    player = state.fighters["player"]
    state.fighters["player"].effects.append(
        Effect(
            "errante.passo_velado.evasao",
            "evasion",
            D(15),
            1,
            1,
            kind="buff",
            stat_modifier_mode="percentage_points",
        )
    )
    assert player.stat("evasion") == D(22)
    assert player.effects[0].remaining == 1


def test_reflexo_stats_survive_combat_snapshot_reconnect_without_duplication():
    secondary = _static_talent_secondary_modifier_totals(
        (TALENT_DEFINITIONS[REFLEXO],)
    )
    stats = _resolve_combat_stats_with_static_talent_modifiers(
        "errante",
        34,
        "remanescente",
        None,
        None,
        _static_talent_modifier_totals((TALENT_DEFINITIONS[REFLEXO],)),
        secondary,
    )
    state = _battle(player_evasion=stats.evasion)
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].stats.evasion == stats.evasion
    assert restored.fighters["player"].stats.evasion == D(1)


def test_sangue_frio_arms_only_from_a_real_dodge_and_records_the_trigger():
    state = _incoming_dodge()
    pending = state.fighters["player"].path_state["errante_sangue_frio_crit"]
    assert pending["expires_opportunity"] == pending["applied_opportunity"] + 2


@pytest.mark.parametrize("defense_kind", ("barrier", "block", "miss"))
def test_non_dodge_defense_does_not_arm_sangue_frio(defense_kind: str):
    state = _battle(
        talents=(SANGUE_FRIO,),
        player_evasion=ZERO,
        enemy_takes_turn=True,
    )
    if defense_kind == "barrier":
        state.fighters["player"].barrier = D(1000)
        state.fighters["player"].barrier_remaining = 2
        state.fighters["player"].barrier_source = "test:barrier"
    elif defense_kind == "block":
        state.fighters["player"].stats = replace(state.fighters["player"].stats, block=D(100))
    else:
        state.enemy_actions["enemy.hit"] = Action(
            "enemy.hit", "Ataque sem dano", ZERO, target_mode="opponent"
        )
    resolved = act(state, "defend")
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state
    assert not any(
        event.target == resolved.fighters["player"].id
        and "errante.sangue_frio_preparado" in event.path_triggers
        for event in resolved.events
    )


def test_passo_velado_without_a_dodge_does_not_arm_sangue_frio():
    state = _battle(arts=(PASSO_VELADO,), talents=(SANGUE_FRIO,))
    resolved = act(state, PASSO_VELADO)
    assert resolved.fighters["player"].next_direct_crit_bonus == D(10)
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state


def test_sangue_frio_is_consumed_once_on_the_next_direct_action_and_persists():
    state = _incoming_dodge()
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["errante_sangue_frio_crit"] == (
        state.fighters["player"].path_state["errante_sangue_frio_crit"]
    )
    resolved = act(restored, "attack", target_id="enemy.entity")
    event = _event(resolved, "attack")
    assert SANGUE_EFFECT_ID in event.actor_effect_ids
    assert event.class_resource_changes == ((
        "errante_sangue_frio_crit", "player.entity", 1, 0
    ),)
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state


def test_sangue_frio_changes_real_next_direct_crit_chance_by_five_points():
    combat_id = _seed_between_chances(
        ZERO,
        D(5),
        "critical:player:attack:enemy.entity",
        cursor=1,
    )
    state = _incoming_dodge(combat_id=combat_id)
    assert state.rng_cursor == 1
    resolved = act(state, "attack", target_id="enemy.entity")
    assert _event(resolved, "attack").critical is True

    baseline = _battle(combat_id=combat_id)
    baseline = act(baseline, "attack", target_id="enemy.entity")
    assert _event(baseline, "attack").critical is False


def test_sangue_frio_preparation_does_not_consumed_by_invalid_or_non_direct_action():
    state = _incoming_dodge()
    prepared = state.fighters["player"].path_state["errante_sangue_frio_crit"].copy()
    invalid = act(state, "missing_action")
    assert invalid is state
    invalid_target = act(state, "attack", target_id="outside.encounter")
    assert invalid_target is state
    assert invalid.fighters["player"].path_state["errante_sangue_frio_crit"] == prepared
    assert invalid_target.fighters["player"].path_state["errante_sangue_frio_crit"] == prepared
    utility = act(state, "utility_probe")
    assert utility.fighters["player"].path_state["errante_sangue_frio_crit"] == prepared


def test_sangue_frio_and_passo_velado_coexist_and_consume_once():
    state = _battle(
        arts=(PASSO_VELADO,),
        talents=(SANGUE_FRIO,),
        player_evasion=D(100),
        enemy_takes_turn=True,
        combat_id=_seed_between_chances(
            ZERO,
            D(15),
            "critical:player:attack:enemy.entity",
            cursor=1,
        ),
    )
    prepared = act(state, PASSO_VELADO)
    player = prepared.fighters["player"]
    assert player.next_direct_crit_bonus == D(10)
    assert "errante_sangue_frio_crit" in player.path_state
    player_before = player.opportunity
    prepared.fighters["enemy"].takes_turn = False
    attack = act(prepared, "attack", target_id="enemy.entity")
    event = _event(attack, "attack")
    assert {
        "errante.passo_velado.janela_ofensiva",
        SANGUE_EFFECT_ID,
    }.issubset(set(event.actor_effect_ids))
    assert event.critical is True
    assert event.class_resource_changes.count(
        ("errante_sangue_frio_crit", "player.entity", 1, 0)
    ) == 1
    assert attack.fighters["player"].next_direct_crit_bonus == ZERO
    assert attack.fighters["player"].next_direct_crit_expires_opportunity is None
    assert "errante_sangue_frio_crit" not in attack.fighters["player"].path_state
    assert attack.fighters["player"].opportunity == player_before + 1


def test_sangue_frio_applies_to_both_individual_hits_but_is_consumed_once():
    state = _incoming_dodge(combat_id=_seed_for_multihit_crits())
    resolved = act(state, "two_hit_probe", target_id="enemy.entity")
    events = [event for event in resolved.events if event.action == "two_hit_probe"]
    assert len(events) == 2
    assert all(SANGUE_EFFECT_ID in event.actor_effect_ids for event in events)
    assert all(event.critical for event in events)
    assert len({event.action_instance_id for event in events}) == 1
    assert sum(
        event.class_resource_changes.count(
            ("errante_sangue_frio_crit", "player.entity", 1, 0)
        )
        for event in events
    ) == 1
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state


@pytest.mark.parametrize("outcome", ("target_dodge", "barrier_absorption"))
def test_sangue_frio_is_consumed_at_commit_even_without_hp_damage(outcome: str):
    state = _incoming_dodge()
    enemy = state.fighters["enemy"]
    if outcome == "target_dodge":
        enemy.stats = replace(enemy.stats, evasion=D(100))
    else:
        enemy.barrier = D(10000)
        enemy.barrier_remaining = 2
        enemy.barrier_source = "test:barrier"
    resolved = act(state, "attack", target_id=enemy.id)
    event = _event(resolved, "attack")
    assert (event.dodged if outcome == "target_dodge" else event.barrier_absorbed > 0)
    assert ("errante_sangue_frio_crit", "player.entity", 1, 0) in event.class_resource_changes
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state


def test_multiple_dodges_in_one_action_replace_one_preparation_without_stacking():
    state = _battle(
        talents=(SANGUE_FRIO,),
        player_evasion=D(100),
        enemy_takes_turn=True,
        enemy_hit_count=2,
    )
    resolved = act(state, "defend")
    dodge_events = [
        event
        for event in resolved.events
        if event.actor_entity_id == resolved.fighters["enemy"].id and event.dodged
    ]
    assert len(dodge_events) == 2
    assert all("errante.sangue_frio_preparado" in event.path_triggers for event in dodge_events)
    pending = resolved.fighters["player"].path_state["errante_sangue_frio_crit"]
    assert pending["expires_opportunity"] == pending["applied_opportunity"] + 2


def test_sangue_frio_window_expires_after_two_owner_opportunities_and_clears_at_combat_end():
    state = _incoming_dodge()
    player = state.fighters["player"]
    expiry = player.path_state["errante_sangue_frio_crit"]["expires_opportunity"]
    player.opportunity = expiry + 1
    _end_turn(state)
    assert "errante_sangue_frio_crit" not in player.path_state

    state = _incoming_dodge()
    _finish_combat(state, "victory")
    assert "errante_sangue_frio_crit" not in state.fighters["player"].path_state

    state = _incoming_dodge()
    _clear_class_mechanics_for_death(state, "player")
    assert "errante_sangue_frio_crit" not in state.fighters["player"].path_state


def test_sangue_frio_crit_is_capped_at_forty_in_pvp_but_not_pve():
    combat_id = _seed_between_chances(
        D(40), D(44), "critical:player:attack:enemy.entity"
    )
    states = []
    for pvp in (True, False):
        state = _battle(combat_id=combat_id, player_crit=D(39), pvp=pvp)
        player = state.fighters["player"]
        player.talent_ids = (SANGUE_FRIO,)
        player.path_state["errante_sangue_frio_crit"] = {
            "applied_opportunity": player.opportunity,
            "expires_opportunity": player.opportunity + 2,
            "source_action_instance_id": "dodge:test",
        }
        states.append(act(state, "attack", target_id="enemy.entity"))
    assert _event(states[0], "attack").critical is False
    assert _event(states[1], "attack").critical is True


def test_reflexo_evasion_obeys_pvp_cap_without_imposing_it_in_pve():
    combat_id = _seed_between_chances(
        D(25), D(30), "evasion:player:attack:enemy.entity"
    )
    pvp = _battle(combat_id=combat_id, enemy_evasion=D(30), pvp=True)
    pve = _battle(combat_id=combat_id, enemy_evasion=D(30), pvp=False)
    pvp_resolved = act(pvp, "attack", target_id="enemy.entity")
    pve_resolved = act(pve, "attack", target_id="enemy.entity")
    assert _event(pvp_resolved, "attack").dodged is False
    assert _event(pve_resolved, "attack").dodged is True


@pytest.mark.parametrize("talent_id", (BRECHA_EXPOSTA, REFLEXO, SANGUE_FRIO))
def test_nv15_ids_are_level_gated_and_nv25_is_authorized(talent_id: str):
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("errante", 14, (talent_id,))
    with pytest.raises(TalentSelectionError):
        validate_talent_choices("errante", 14, ((1, talent_id),))
    assert validate_active_talent_ids("errante", 15, (talent_id,)) == (talent_id,)
    tier25 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "errante" and definition.level == 25
    )
    assert validate_active_talent_ids("errante", 25, (tier25,)) == (tier25,)
    tier35 = next(
        definition.talent_id
        for definition in TALENT_DEFINITIONS.values()
        if definition.character_class == "errante" and definition.level == 35
    )
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids("errante", 34, (tier35,))
    assert validate_active_talent_ids("errante", 35, (tier35,)) == (tier35,)
    assert validate_active_talent_ids("errante", 60, (tier35,)) == (tier35,)


def test_valid_nv5_errante_choices_remain_legal_and_points_still_accrue_at_nv15():
    valid = "talent.errante.fio_afiado"
    assert validate_active_talent_ids("errante", 15, (valid,)) == (valid,)
    assert TALENT_DEFINITIONS[valid].level == 5
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
