from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

import pytest

from asterion.domain.arts import ORACULO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    _apply_barrier,
    _finish_combat,
    _perform,
    _tick_path_resources,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
PROFECIA_DOLOROSA = "talent.oraculo.profecia_dolorosa"
DESTINO_ADIADO = "talent.oraculo.destino_adiado"
PRESSAGIO_FLEXIVEL = "talent.oraculo.pressagio_flexivel"
PRESSAGIO_CORTANTE = "talent.oraculo.pressagio_cortante"
SINAL_PERSISTENTE = "talent.oraculo.sinal_persistente"
SINAL = ORACULO_ART_IDS["sinal_funesto"]
SELO = ORACULO_ART_IDS["selo_da_queda"]
RUINA = ORACULO_ART_IDS["ruina_predita"]
COMBAT_ID = UUID("618e5814-943e-48df-a403-269fa3d273c6")


def _combat(
    *,
    talents: tuple[str, ...] = (),
    path: str | None = None,
    arts: tuple[str, ...] = (SELO, SINAL, RUINA),
    enemy_count: int = 1,
) -> Combat:
    stats = CombatStats(
        hp=D(10000),
        attack=D(100),
        defense=D(100),
        agility=D(100),
    )
    state = PROFILE.create(COMBAT_ID, "Oráculo", "oraculo", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.level = 60
    actor.character_class = "oraculo"
    actor.selected_path = path
    actor.talent_ids = talents
    actor.stats = replace(stats, evasion=ZERO, crit=ZERO, block=ZERO, per=ZERO)
    actor.hp = actor.stats.hp
    actor.side = "player"

    for index in range(enemy_count):
        key = "enemy" if index == 0 else f"enemy-{index}"
        if index == 0:
            target = state.fighters["enemy"]
        else:
            target = Fighter(
                id=f"enemy-entity-{index}",
                name=f"Enemy {index}",
                level=60,
                stats=stats,
                hp=stats.hp,
                side="enemy",
                takes_turn=False,
                required_for_victory=False,
            )
            state.fighters[key] = target
        target.stats = replace(
            stats, attack=D(1000), defense=ZERO, crit=ZERO, evasion=ZERO, block=ZERO
        )
        target.hp = target.stats.hp
        target.side = "enemy"
        target.takes_turn = False

    state.player_actions = class_player_actions("oraculo", arts, path)
    state.enemy_actions = {
        "hit": Action("enemy.hit", "Direct hit", D(1)),
        "multi": Action("enemy.multi", "Multi-hit", D(1), hit_count=3),
        "dot": Action(
            "enemy.dot",
            "Apply poison",
            ZERO,
            native_dot_kind="poison",
            native_dot_stacks=1,
            duration=2,
        ),
        "wait": Action("enemy.wait", "Wait", ZERO, target_mode="self"),
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _mark(state: Combat, kind: str, target_key: str, *, remaining: int = 2) -> None:
    owner = state.fighters["player"]
    target = state.fighters[target_key]
    owner.path_state.setdefault(f"omen_{kind}", {})[target.id] = {
        "remaining": remaining,
        "applied_opportunity": owner.opportunity,
    }


def _event(state: Combat, action_id: str):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action_id
        and event.actor_entity_id == state.fighters["player"].id
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    ((None, D("1.1424")), ("agoureiro", D("1.1832")), ("invocador", D("1.1424"))),
)
def test_profecia_dolorosa_multiplies_the_consumed_offensive_omen_power(path, expected):
    state = _combat(path=path, talents=(PROFECIA_DOLOROSA,))
    _mark(state, "offensive", "enemy")

    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(result, SELO)

    # The GDD says +2% potency (not +2 percentage points): the implemented
    # offensive Omen multiplier is multiplied by 1.02 at the same power stage.
    assert event.path_power_multiplier == expected
    assert event.class_resource_changes == (
        ("omen_offensive", state.fighters["enemy"].id, 1, 0),
    )
    assert "pressagio.ofensivo_consumido" in event.path_triggers


def test_profecia_dolorosa_does_not_apply_without_a_consumed_offensive_mark():
    state = _combat(talents=(PROFECIA_DOLOROSA,))
    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(result, SELO)

    assert event.path_power_multiplier == D(1)
    assert "pressagio.ofensivo_consumido" not in event.path_triggers
    # Selo da Queda can create a new Omen only after resolving its own Debuff.
    assert result.fighters["player"].path_state["omen_offensive"][
        state.fighters["enemy"].id
    ]["remaining"] == 2


def test_profecia_dolorosa_is_target_specific_and_does_not_consume_defensive_omen():
    state = _combat(talents=(PROFECIA_DOLOROSA,), enemy_count=2)
    _mark(state, "offensive", "enemy-1")
    _mark(state, "defensive", "player")
    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(result, SELO)

    assert event.path_power_multiplier == D(1)
    owner = result.fighters["player"]
    assert state.fighters["enemy-1"].id in owner.path_state["omen_offensive"]
    assert owner.id in owner.path_state["omen_defensive"]


def test_profecia_dolorosa_coexists_with_pressagio_cortante_without_double_consumption():
    state = _combat(talents=(PROFECIA_DOLOROSA, PRESSAGIO_CORTANTE))
    _mark(state, "offensive", "enemy")
    target_id = state.fighters["enemy"].id

    result = act(state, SELO, target_id=target_id)
    event = _event(result, SELO)

    assert event.path_power_multiplier == D("1.1424")
    assert event.path_per_bonus == D(2)
    assert event.class_resource_changes == (("omen_offensive", target_id, 1, 0),)


def test_profecia_dolorosa_strengthens_ruina_predita_and_consumes_an_extended_omen():
    state = _combat(
        talents=(PROFECIA_DOLOROSA, PRESSAGIO_FLEXIVEL),
        arts=(RUINA,),
    )
    target_id = state.fighters["enemy"].id
    _mark(state, "offensive", "enemy", remaining=1)
    owner = state.fighters["player"]
    owner.opportunity += 1
    _tick_path_resources(state, "player")
    assert owner.path_state["omen_flexible_used"] is True
    assert owner.path_state["omen_offensive"][target_id]["remaining"] == 1

    result = act(state, RUINA, target_id=target_id)
    event = _event(result, RUINA)

    assert event.path_power_multiplier == D("1.1424")
    assert event.class_resource_changes == (("omen_offensive", target_id, 1, 0),)
    assert target_id not in result.fighters["player"].path_state.get(
        "omen_offensive", {}
    )
    assert result.fighters["player"].path_state["omen_flexible_used"] is True


def _incoming(state: Combat, action_id: str = "hit"):
    attacker_id = state.fighters["enemy"].id
    assert _perform(
        state,
        "enemy",
        action_id,
        target_id=state.fighters["player"].id,
    )
    return [
        event
        for event in state.events
        if event.actor_entity_id == attacker_id and event.action == action_id
    ]


def test_destino_adiado_reduces_the_first_positive_direct_component_before_barrier():
    protected = _combat(talents=(DESTINO_ADIADO,))
    baseline = _combat()
    protected_events = _incoming(protected)
    baseline_events = _incoming(baseline)

    assert protected_events[0].calculated_damage == int(
        (D(baseline_events[0].calculated_damage) * D("0.93")).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    assert protected.fighters["player"].path_state["oraculo_destino_adiado_used"]

    next_damage = _incoming(protected)[-1]
    next_baseline = _incoming(baseline)[-1]
    assert next_damage.calculated_damage == next_baseline.calculated_damage


def test_destino_adiado_miss_and_fully_reduced_component_do_not_spend_it():
    missed = _combat(talents=(DESTINO_ADIADO,))
    missed.fighters["player"].stats = replace(
        missed.fighters["player"].stats, evasion=D(100)
    )
    event = _incoming(missed)[0]
    assert event.dodged
    assert "oraculo_destino_adiado_used" not in missed.fighters["player"].path_state

    reduced = _combat(talents=(DESTINO_ADIADO,))
    target = reduced.fighters["player"]
    target.training_state_tags = ("full_direct_reduction",)
    target.tagged_direct_damage_reductions = {"full_direct_reduction": D(1)}
    event = _incoming(reduced)[0]
    assert event.calculated_damage == 0
    assert "oraculo_destino_adiado_used" not in target.path_state

    target.training_state_tags = ()
    target.tagged_direct_damage_reductions.clear()
    _incoming(reduced)
    assert target.path_state["oraculo_destino_adiado_used"]


def test_destino_adiado_counts_positive_direct_damage_even_if_barrier_absorbs_all():
    state = _combat(talents=(DESTINO_ADIADO,))
    target = state.fighters["player"]
    _apply_barrier(
        target,
        applier_id="ally",
        effect_definition_id="barrier.ally",
        value=D(10000),
        duration=2,
        applied_opportunity=target.opportunity,
        round_number=state.round,
    )

    event = _incoming(state)[0]
    assert event.calculated_damage > 0
    assert event.effective_damage == 0
    assert target.path_state["oraculo_destino_adiado_used"] is True


def test_destino_adiado_does_not_spend_on_dot_or_non_oraculo_target():
    state = _combat(talents=(DESTINO_ADIADO,))
    _incoming(state, "dot")
    assert "oraculo_destino_adiado_used" not in state.fighters["player"].path_state

    other_class = _combat()
    target = other_class.fighters["player"]
    target.character_class = "vigia"
    target.talent_ids = (DESTINO_ADIADO,)
    _incoming(other_class)
    assert "oraculo_destino_adiado_used" not in target.path_state


def test_destino_adiado_applies_to_only_first_positive_multihit_component():
    protected = _combat(talents=(DESTINO_ADIADO,))
    baseline = _combat()
    protected_events = _incoming(protected, "multi")
    baseline_events = _incoming(baseline, "multi")

    assert len(protected_events) == len(baseline_events) == 3
    assert protected_events[0].calculated_damage == int(
        (D(baseline_events[0].calculated_damage) * D("0.93")).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    assert [event.calculated_damage for event in protected_events[1:]] == [
        event.calculated_damage for event in baseline_events[1:]
    ]


@pytest.mark.parametrize("kind", ("offensive", "defensive"))
def test_pressagio_flexivel_renews_first_unused_omen_expiry_and_survives_codec(kind):
    state = _combat(talents=(PRESSAGIO_FLEXIVEL,))
    owner = state.fighters["player"]
    target_key = "enemy" if kind == "offensive" else "player"
    target_id = state.fighters[target_key].id
    owner.path_state[f"omen_{kind}"] = {
        target_id: {"remaining": 1, "applied_opportunity": owner.opportunity}
    }
    owner.opportunity += 1

    _tick_path_resources(state, "player")
    renewed = owner.path_state[f"omen_{kind}"][target_id]
    assert renewed["remaining"] == 1
    assert renewed["applied_opportunity"] == owner.opportunity
    assert owner.path_state["omen_flexible_used"] is True

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    restored_owner = restored.fighters["player"]
    assert restored_owner.path_state[f"omen_{kind}"][target_id] == renewed
    restored_owner.opportunity += 1
    _tick_path_resources(restored, "player")
    assert target_id not in restored_owner.path_state.get(f"omen_{kind}", {})
    assert restored_owner.path_state["omen_flexible_used"] is True


def test_pressagio_flexivel_uses_one_shared_deterministic_allowance_for_simultaneous_expiries():
    state = _combat(talents=(PRESSAGIO_FLEXIVEL,), enemy_count=2)
    owner = state.fighters["player"]
    # Reverse insertion order to verify stable target ordering within the
    # offensive type; defensive marks share the same once-per-combat allowance.
    owner.path_state["omen_offensive"] = {
        state.fighters["enemy-1"].id: {"remaining": 1, "applied_opportunity": 0},
        state.fighters["enemy"].id: {"remaining": 1, "applied_opportunity": 0},
    }
    owner.path_state["omen_defensive"] = {
        owner.id: {"remaining": 1, "applied_opportunity": 0}
    }
    owner.opportunity = 1

    _tick_path_resources(state, "player")

    assert owner.path_state["omen_flexible_used"] is True
    offensive = owner.path_state["omen_offensive"]
    assert offensive[state.fighters["enemy"].id]["remaining"] == 1
    assert state.fighters["enemy-1"].id not in offensive
    assert owner.id not in owner.path_state.get("omen_defensive", {})


def test_consumed_omen_does_not_spend_pressagio_flexivel_expiry_allowance():
    state = _combat(talents=(PRESSAGIO_FLEXIVEL,))
    _mark(state, "offensive", "enemy")
    result = act(state, SELO, target_id=state.fighters["enemy"].id)
    owner = result.fighters["player"]

    assert "omen_flexible_used" not in owner.path_state
    # A fresh Omen created by Selo is a new mark and may be the first unused
    # natural expiry, but consumption itself never spends the special renewal.
    owner.path_state["omen_defensive"] = {
        owner.id: {"remaining": 1, "applied_opportunity": owner.opportunity}
    }
    owner.opportunity += 1
    _tick_path_resources(result, "player")
    assert owner.path_state["omen_flexible_used"] is True
    assert owner.path_state["omen_defensive"][owner.id]["remaining"] == 1


def test_pressagio_flexivel_waits_for_normal_three_turn_sinal_persistente_expiry():
    state = _combat(talents=(PRESSAGIO_FLEXIVEL, SINAL_PERSISTENTE))
    owner = state.fighters["player"]
    target_id = state.fighters["enemy"].id
    owner.path_state["omen_offensive"] = {
        target_id: {"remaining": 3, "applied_opportunity": owner.opportunity}
    }

    for expected in (2, 1):
        owner.opportunity += 1
        _tick_path_resources(state, "player")
        assert owner.path_state["omen_offensive"][target_id]["remaining"] == expected
        assert "omen_flexible_used" not in owner.path_state

    owner.opportunity += 1
    _tick_path_resources(state, "player")
    assert owner.path_state["omen_offensive"][target_id]["remaining"] == 1
    assert owner.path_state["omen_flexible_used"] is True


def test_oraculo_tier35_effects_are_valid_after_public_release():
    ids = (PROFECIA_DOLOROSA, DESTINO_ADIADO, PRESSAGIO_FLEXIVEL)
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45, 55})
    assert talent_points_at_level(35) == 7
    for talent_id in ids:
        assert TALENT_DEFINITIONS[talent_id].level == 35
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("oraculo", 34, (talent_id,))
        assert validate_active_talent_ids("oraculo", 35, (talent_id,)) == (talent_id,)
        assert validate_active_talent_ids("oraculo", 60, (talent_id,)) == (talent_id,)


def test_destino_adiado_flag_roundtrips_and_clears_at_combat_end():
    state = _combat(talents=(DESTINO_ADIADO,))
    _incoming(state)
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.fighters["player"].path_state["oraculo_destino_adiado_used"] is True

    second_event = _incoming(restored)[-1]
    baseline = _incoming(_combat())[-1]
    assert second_event.calculated_damage == baseline.calculated_damage

    _finish_combat(restored, "victory")
    assert "oraculo_destino_adiado_used" not in restored.fighters["player"].path_state
