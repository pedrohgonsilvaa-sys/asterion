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
    _finish_combat,
    act,
    start_combat,
)
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatRng,
    CombatStats,
    direct_damage,
)
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
PLAYER_HP_DEFAULT = D(1000)
ENEMY_ATTACK_DEFAULT = D(100)
OPORTUNISMO_AMPLIADO = "talent.errante.oportunismo_ampliado"
SOBREVIVENCIA = "talent.errante.sobrevivencia"
DESVIO_OFENSIVO = "talent.errante.desvio_ofensivo"
SANGUE_FRIO = "talent.errante.sangue_frio"
BRECHA_EXPOSTA = "talent.errante.brecha_exposta"
COURO_LEVE = "talent.errante.couro_leve"
PASSOS_DA_SOMBRA = "talent.errante.passos_da_sombra"
FERIDA_PROFUNDA = ERRANTE_ART_IDS["ferida_profunda"]
CORTE_DUPLO = ERRANTE_ART_IDS["corte_duplo"]
BRECHA_MORTAL = ERRANTE_ART_IDS["brecha_mortal"]
COMBAT_ID = UUID("b7f49670-257b-4bad-8769-1bb03cd18e13")


def _battle(
    *,
    arts: tuple[str, ...] = (),
    talents: tuple[str, ...] = (),
    path: str | None = None,
    player_hp: Decimal = PLAYER_HP_DEFAULT,
    player_stats: CombatStats | None = None,
    player_evasion: Decimal = ZERO,
    player_block: Decimal = ZERO,
    player_barrier: Decimal = ZERO,
    enemy_evasion: Decimal = ZERO,
    enemy_barrier: Decimal = ZERO,
    enemy_effects: tuple[Effect, ...] = (),
    enemy_dots: tuple[DotState, ...] = (),
    enemy_takes_turn: bool = False,
    enemy_attack: Decimal = ENEMY_ATTACK_DEFAULT,
    enemy_hit_count: int = 1,
    combat_id: UUID = COMBAT_ID,
) -> Combat:
    stats = player_stats or CombatStats(
        D(1000),
        D(100),
        D(100),
        D(100),
        crit=ZERO,
        evasion=player_evasion,
        block=player_block,
    )
    player = Fighter(
        "player.entity",
        "Errante",
        35,
        stats,
        player_hp,
        race="remanescente",
        character_class="errante",
        selected_path=path,
        talent_ids=talents,
        barrier=player_barrier,
        barrier_remaining=2 if player_barrier > ZERO else 0,
        barrier_source="test:barrier" if player_barrier > ZERO else "",
    )
    enemy = Fighter(
        "enemy.entity",
        "Alvo",
        35,
        CombatStats(
            D(10000), enemy_attack, D(100), D(1), crit=ZERO, evasion=enemy_evasion
        ),
        D(10000),
        side="enemy",
        takes_turn=enemy_takes_turn,
        effects=list(enemy_effects),
        barrier=enemy_barrier,
        barrier_remaining=2 if enemy_barrier > ZERO else 0,
        barrier_source="test:barrier" if enemy_barrier > ZERO else "",
    )
    actions = class_player_actions("errante", arts, selected_path=path)
    actions["utility_probe"] = Action("utility_probe", "Utilidade", ZERO, target_mode="self")
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
    )
    state.dot_states[enemy.id] = list(enemy_dots)
    return start_combat(state)


def _player_event(state: Combat, action_id: str, hit_index: int | None = None):
    return next(
        event
        for event in reversed(state.events)
        if event.actor_entity_id == state.fighters["player"].id
        and event.action == action_id
        and (hit_index is None or event.hit_index == hit_index)
    )


def _enemy_dodge(*, talents: tuple[str, ...], arts: tuple[str, ...] = ()) -> Combat:
    state = _battle(
        arts=arts,
        talents=talents,
        player_evasion=D(100),
        enemy_takes_turn=True,
    )
    prepared = act(state, "defend")
    dodge = next(
        event
        for event in prepared.events
        if event.actor_entity_id == prepared.fighters["enemy"].id
        and event.target == prepared.fighters["player"].id
        and event.dodged
    )
    assert dodge.dodged
    prepared.fighters["enemy"].takes_turn = False
    return prepared


def _seed_for_failed_dodge() -> UUID:
    purpose = "evasion:enemy:enemy.hit:player.entity"
    for value in range(1, 10000):
        combat_id = UUID(int=value)
        if not CombatRng(combat_id).chance(D("0.01"), purpose):
            return combat_id
    raise AssertionError("No deterministic seed found for a failed dodge roll.")


def test_opportunism_ampliado_replaces_eight_with_ten_and_needs_action_start_effect():
    slow = Effect("enemy.slow", "agility", D("0.10"), 2, 0, kind="debuff")
    base = _battle(arts=(BRECHA_MORTAL,), enemy_effects=(slow,))
    amplified = _battle(
        arts=(BRECHA_MORTAL,),
        talents=(OPORTUNISMO_AMPLIADO,),
        enemy_effects=(slow,),
    )
    clean_target = _battle(arts=(BRECHA_MORTAL,), talents=(OPORTUNISMO_AMPLIADO,))

    base_event = _player_event(
        act(base, BRECHA_MORTAL, target_id="enemy.entity"), BRECHA_MORTAL
    )
    assert base_event.path_final_damage_bonus == D("0.08")
    amplified_event = _player_event(
        act(amplified, BRECHA_MORTAL, target_id="enemy.entity"), BRECHA_MORTAL
    )
    assert amplified_event.path_final_damage_bonus == D("0.10")
    assert amplified_event.path_final_damage_bonus != D("0.18")
    clean_event = _player_event(
        act(clean_target, BRECHA_MORTAL, target_id="enemy.entity"), BRECHA_MORTAL
    )
    assert clean_event.path_final_damage_bonus == ZERO
    assert "oportunismo" not in clean_event.path_triggers


def test_ferida_profunda_does_not_enable_opportunism_retroactively():
    state = _battle(
        arts=(FERIDA_PROFUNDA, BRECHA_MORTAL),
        talents=(OPORTUNISMO_AMPLIADO, BRECHA_EXPOSTA, PASSOS_DA_SOMBRA),
    )
    applied = act(state, FERIDA_PROFUNDA, target_id="enemy.entity")
    first_event = _player_event(applied, FERIDA_PROFUNDA)
    assert first_event.path_final_damage_bonus == ZERO
    assert first_event.path_per_bonus == ZERO
    assert any(dot.remaining > 0 for dot in applied.dot_states["enemy.entity"])

    later = act(applied, BRECHA_MORTAL, target_id="enemy.entity")
    later_event = _player_event(later, BRECHA_MORTAL)
    assert later_event.path_final_damage_bonus == D("0.10")
    assert later_event.path_per_bonus == D(14)


def test_oportunismo_ampliado_is_snapshotted_once_for_both_corte_duplo_hits():
    slow = Effect("enemy.slow", "agility", D("0.10"), 2, 0, kind="debuff")
    state = _battle(
        arts=(CORTE_DUPLO,),
        talents=(OPORTUNISMO_AMPLIADO,),
        enemy_effects=(slow,),
    )
    resolved = act(state, CORTE_DUPLO, target_id="enemy.entity")
    events = [
        event
        for event in resolved.events
        if event.actor_entity_id == resolved.fighters["player"].id
        and event.action == CORTE_DUPLO
    ]
    assert len(events) == 2
    assert [event.path_final_damage_bonus for event in events] == [D("0.10"), D("0.10")]
    assert all(event.path_triggers.count("oportunismo") == 1 for event in events)


def test_oportunismo_ampliado_keeps_carrasco_sentenca_as_an_independent_source():
    slow = Effect("enemy.slow", "agility", D("0.10"), 2, 0, kind="debuff")
    state = _battle(
        arts=(BRECHA_MORTAL,),
        talents=(OPORTUNISMO_AMPLIADO,),
        path="carrasco",
        enemy_effects=(slow,),
    )
    state.fighters["enemy"].hp = D(4000)
    resolved = act(state, BRECHA_MORTAL, target_id="enemy.entity")
    event = _player_event(resolved, BRECHA_MORTAL)
    assert "oportunismo" in event.path_triggers
    assert "carrasco.sentenca" in event.path_triggers
    assert event.path_final_damage_bonus == D("0.18")


@pytest.mark.parametrize(
    ("hp", "expected"),
    (
        (D(401), D(100)),
        (D(400), D(105)),
        (D(399), D(105)),
        (D(1), D(105)),
        (ZERO, D(100)),
    ),
)
def test_sobrevivencia_is_dynamic_at_exactly_forty_percent_and_does_not_save_defeated(
    hp: Decimal, expected: Decimal
):
    state = _battle(talents=(SOBREVIVENCIA,), player_hp=hp)
    fighter = state.fighters["player"]
    static_defense = fighter.stats.defense
    assert fighter.stat("defense") == expected
    assert fighter.stats.defense == static_defense == D(100)


def test_sobrevivencia_tracks_healing_and_exact_integer_threshold_for_non_round_maximum():
    stats = CombatStats(D(999), D(100), D(101), D(100))
    state = _battle(talents=(SOBREVIVENCIA,), player_hp=D(400), player_stats=stats)
    fighter = state.fighters["player"]
    assert fighter.stat("defense") == D(101)
    fighter.hp = D(399)  # 399/999 <= 40%; no float or rounded-percent comparison.
    assert fighter.stat("defense") == D("106.05")
    fighter.hp = D(400)  # 400/999 > 40%.
    assert fighter.stat("defense") == D(101)


def test_sobrevivencia_coexists_with_couro_leve_and_is_not_a_timed_effect():
    stats = CombatStats(D(1000), D(100), D(102), D(100))
    state = _battle(
        talents=(SOBREVIVENCIA, COURO_LEVE), player_hp=D(400), player_stats=stats
    )
    fighter = state.fighters["player"]
    # Base 100 * static 1.02 is composed before the dynamic 1.05.
    assert fighter.stats.defense == D("102.00")
    assert fighter.stat("defense") == D("107.1000")
    assert not any(effect.id.endswith("sobrevivencia") for effect in fighter.effects)
    fighter.hp = D(410)
    assert fighter.stat("defense") == D("102.00")
    fighter.hp = D(400)
    assert fighter.stat("defense") == D("107.1000")


def test_sobrevivencia_does_not_change_damage_snapshot_that_crosses_threshold():
    player_stats = CombatStats(D(1000), D(100), D(100), D(100), evasion=ZERO)
    common = dict(
        player_hp=D(410),
        player_stats=player_stats,
        enemy_takes_turn=True,
        enemy_attack=D(2000),
    )
    without = act(_battle(**common), "defend")
    with_talent = act(_battle(talents=(SOBREVIVENCIA,), **common), "defend")
    without_event = next(event for event in without.events if event.action == "enemy.hit")
    with_event = next(event for event in with_talent.events if event.action == "enemy.hit")
    assert with_event.calculated_damage == without_event.calculated_damage
    assert with_talent.fighters["player"].hp <= D(400)
    assert with_talent.fighters["player"].stat("defense") == D(105)


def test_successful_dodge_arms_one_combat_scoped_desvio_preparation():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    prepared = state.fighters["player"].path_state["errante_desvio_ofensivo_per"]
    assert prepared["combat_id"] == str(state.id)
    assert any(
        "errante.desvio_ofensivo_preparado" in event.path_triggers
        for event in state.events
        if event.dodged
    )

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["errante_desvio_ofensivo_per"] == prepared
    resolved = act(restored, "attack", target_id="enemy.entity")
    event = _player_event(resolved, "attack")
    assert event.path_per_bonus == D(4)
    assert "errante.desvio_ofensivo_consumido" in event.path_triggers
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state
    assert ("errante_desvio_ofensivo_per", "player.entity", 1, 0) in event.class_resource_changes


def test_desvio_preparation_survives_non_direct_actions_but_is_consumed_by_next_direct_action():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    prepared = state.fighters["player"].path_state["errante_desvio_ofensivo_per"].copy()
    utility = act(state, "utility_probe")
    assert utility.fighters["player"].path_state["errante_desvio_ofensivo_per"] == prepared
    restored = decode(encode(utility), utility.id, utility.ruleset, utility.version)
    resolved = act(restored, "attack", target_id="enemy.entity")
    assert _player_event(resolved, "attack").path_per_bonus == D(4)
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state


def test_invalid_action_does_not_consume_desvio_preparation():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    prepared = state.fighters["player"].path_state["errante_desvio_ofensivo_per"].copy()
    assert act(state, "missing_action") is state
    assert act(state, "attack", target_id="outside.encounter") is state
    assert state.fighters["player"].path_state["errante_desvio_ofensivo_per"] == prepared


def test_desvio_preparation_applies_once_to_all_hits_of_one_multi_hit_action():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,), arts=(CORTE_DUPLO,))
    resolved = act(state, CORTE_DUPLO, target_id="enemy.entity")
    events = [
        event
        for event in resolved.events
        if event.actor_entity_id == resolved.fighters["player"].id
        and event.action == CORTE_DUPLO
    ]
    assert len(events) == 2
    assert [event.path_per_bonus for event in events] == [D(4), D(4)]
    assert all("errante.desvio_ofensivo_consumido" in event.path_triggers for event in events)
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state


def test_desvio_per_is_real_action_penetration_and_respects_the_thirty_point_cap():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    player = state.fighters["player"]
    player.stats = replace(player.stats, per=D(29))
    resolved = act(state, "attack", target_id="enemy.entity")
    event = _player_event(resolved, "attack")
    assert event.path_per_bonus == D(4)
    assert event.calculated_damage == direct_damage(
        D(100), D(1), D(100), 35, penetration=D(30)
    )


@pytest.mark.parametrize("outcome", ("target_evades", "barrier_absorbs"))
def test_committed_direct_action_consumes_desvio_even_when_hit_does_not_reach_hp(
    outcome: str,
):
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    target = state.fighters["enemy"]
    if outcome == "target_evades":
        target.stats = replace(target.stats, evasion=D(100))
    else:
        target.barrier = D(10000)
        target.barrier_remaining = 2
        target.barrier_source = "test:barrier"

    resolved = act(state, "attack", target_id="enemy.entity")
    event = _player_event(resolved, "attack")
    assert event.path_per_bonus == D(4)
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state
    if outcome == "target_evades":
        assert event.dodged
    else:
        assert event.calculated_damage > ZERO
        assert event.barrier_absorbed == event.calculated_damage


def test_multiple_real_dodges_in_one_enemy_multihit_do_not_stack_desvio():
    state = _battle(
        talents=(DESVIO_OFENSIVO,),
        player_evasion=D(100),
        enemy_takes_turn=True,
        enemy_hit_count=2,
    )
    state = act(state, "defend")
    dodges = [
        event
        for event in state.events
        if event.actor_entity_id == state.fighters["enemy"].id
        and event.target == state.fighters["player"].id
        and event.dodged
    ]
    assert len(dodges) == 2
    prepared = state.fighters["player"].path_state["errante_desvio_ofensivo_per"]
    assert prepared["source_event_index"] == dodges[-1].sequence
    state.fighters["enemy"].takes_turn = False
    resolved = act(state, "attack", target_id="enemy.entity")
    assert _player_event(resolved, "attack").path_per_bonus == D(4)


def test_desvio_coexists_with_sangue_frio_as_independent_per_and_crit_preparations():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO, SANGUE_FRIO))
    assert "errante_desvio_ofensivo_per" in state.fighters["player"].path_state
    assert "errante_sangue_frio_crit" in state.fighters["player"].path_state
    resolved = act(state, "attack", target_id="enemy.entity")
    event = _player_event(resolved, "attack")
    assert event.path_per_bonus == D(4)
    assert "errante.sangue_frio.crit" in event.actor_effect_ids
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state
    assert "errante_sangue_frio_crit" not in resolved.fighters["player"].path_state


@pytest.mark.parametrize("defense_kind", ("failed_dodge", "block", "barrier"))
def test_non_dodge_defense_does_not_arm_desvio(defense_kind: str):
    options = {"enemy_takes_turn": True}
    if defense_kind == "failed_dodge":
        options.update(player_evasion=D(1), combat_id=_seed_for_failed_dodge())
    elif defense_kind == "block":
        options.update(player_block=D(100))
    else:
        options.update(player_barrier=D(1000))
    state = _battle(talents=(DESVIO_OFENSIVO,), **options)
    resolved = act(state, "defend")
    enemy_event = next(event for event in resolved.events if event.action == "enemy.hit")
    if defense_kind == "failed_dodge":
        assert not enemy_event.dodged
    elif defense_kind == "block":
        assert enemy_event.blocked
    else:
        assert enemy_event.barrier_absorbed > ZERO
    assert "errante_desvio_ofensivo_per" not in resolved.fighters["player"].path_state
    assert not any(
        "errante.desvio_ofensivo_preparado" in event.path_triggers
        for event in resolved.events
    )


def test_desvio_preparation_is_cleared_on_death_and_combat_end():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    actor = state.fighters["player"]
    _clear_class_mechanics_for_death(state, "player")
    assert "errante_desvio_ofensivo_per" not in actor.path_state

    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    _finish_combat(state, "victory")
    assert "errante_desvio_ofensivo_per" not in state.fighters["player"].path_state


def test_errante_nv35_ids_remain_internally_defined_but_publicly_closed():
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25})
    for talent_id in (OPORTUNISMO_AMPLIADO, SOBREVIVENCIA, DESVIO_OFENSIVO):
        assert TALENT_DEFINITIONS[talent_id].level == 35
        for level in (34, 35, 60):
            with pytest.raises(TalentSelectionError):
                validate_active_talent_ids("errante", level, (talent_id,))

    # Public static composition also delegates to the authoritative validator.
    from asterion.domain.talents import static_talent_modifiers

    with pytest.raises(TalentSelectionError):
        static_talent_modifiers("errante", 60, (OPORTUNISMO_AMPLIADO,))


def test_desvio_state_does_not_cross_combat_identity_or_cleanup():
    state = _enemy_dodge(talents=(DESVIO_OFENSIVO,))
    old_preparation = state.fighters["player"].path_state[
        "errante_desvio_ofensivo_per"
    ].copy()
    next_combat = _battle(
        talents=(DESVIO_OFENSIVO,),
        combat_id=UUID("f418d8ad-dc66-42bc-812f-6218b5e1efc2"),
    )
    next_combat.fighters["player"].path_state["errante_desvio_ofensivo_per"] = old_preparation
    next_combat = start_combat(next_combat)
    assert "errante_desvio_ofensivo_per" not in next_combat.fighters["player"].path_state
    resolved = act(next_combat, "attack", target_id="enemy.entity")
    assert _player_event(resolved, "attack").path_per_bonus == ZERO
