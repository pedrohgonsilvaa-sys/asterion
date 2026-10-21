from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    LUMINAR_ART_IDS,
    LUMINAR_ART_LEVELS,
    ORACULO_ART_IDS,
    ORACULO_ART_LEVELS,
)
from asterion.domain.class_trials import (
    LUMINAR_ALLY_ENTITY_ID,
    LUMINAR_CONDITION_IDS,
    LUMINAR_ENTITY_IDS,
    ORACULO_CONDITION_IDS,
    ORACULO_ENTITY_IDS,
    ORACULO_OFFENSIVE_WINDOW_TAG,
    ORACULO_SINAL_EFFECT_ID,
    TrialCombatEvent,
    create_luminar_trial_combat,
    create_oraculo_trial_combat,
    luminar_conditions_for_event,
    luminar_stage_definition,
    oraculo_conditions_for_event,
    oraculo_stage_definition,
    trial_event_from_combat_event,
)
from asterion.domain.combat import (
    Action,
    Combat,
    Effect,
    Fighter,
    _deal_damage,
    _end_turn,
    act,
    apply_effect,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _player(character_class: str, *, agility: str = "110", hp: str = "2000") -> Fighter:
    stats = CombatStats(
        D(hp), D("200"), D("100"), D(agility), crit=D(0), evasion=D(0), block=D(0)
    )
    return Fighter(
        "player", "Treinando", 10, stats, D(hp), character_class=character_class
    )


def _oraculo(stage: int, arts: tuple[str, ...]):
    definition = oraculo_stage_definition(stage, allowed_art_ids=arts)
    combat = start_combat(create_oraculo_trial_combat(_player("oraculo"), definition))
    return definition, combat


def _luminar(stage: int, arts: tuple[str, ...]):
    definition = luminar_stage_definition(stage, allowed_art_ids=arts)
    combat = start_combat(create_luminar_trial_combat(_player("luminar"), definition))
    return definition, combat


def _apply_new(before, after, stage, evaluator, context):
    events = after.events[len(before.events) :] + after.mechanic_events[
        len(before.mechanic_events) :
    ]
    conditions = []
    for combat_event in events:
        event = trial_event_from_combat_event(after, combat_event)
        matched, context = evaluator(stage, event, context)
        conditions.extend(matched)
    return tuple(conditions), context


def test_oraculo_and_luminar_active_art_catalogs_are_canonical_through_level_ten():
    assert tuple(level for level in ORACULO_ART_LEVELS.values() if level <= 10) == (
        1,
        4,
        7,
        9,
    )
    assert ORACULO_ART_LEVELS[ORACULO_ART_IDS["augurio_favoravel"]] == 18
    assert tuple(level for level in LUMINAR_ART_LEVELS.values() if level <= 10) == (
        1,
        4,
        7,
        9,
    )
    assert LUMINAR_ART_LEVELS[LUMINAR_ART_IDS["luz_restauradora"]] == 18
    assert {ACTIVE_ART_DEFINITIONS[art].character_class for art in ORACULO_ART_IDS.values()} == {
        "oraculo"
    }
    assert {ACTIVE_ART_DEFINITIONS[art].character_class for art in LUMINAR_ART_IDS.values()} == {
        "luminar"
    }


def test_oraculo_stage_plans_are_fixed_single_echo_and_variant_free():
    expected = {
        1: ("trial_entity.oraculo.sinal", "620", "105", "90", "90"),
        2: ("trial_entity.oraculo.antevisao", "650", "110", "90", "90"),
        3: ("trial_entity.oraculo.futuro_possivel", "680", "110", "95", "95"),
    }
    for stage, row in expected.items():
        definition = oraculo_stage_definition(stage)
        entity = definition.entities[0]
        assert (entity.entity_id, str(entity.max_hp)) == row[:2]
        assert tuple(str(entity.stats[key]) for key in ("attack", "defense", "agility")) == row[2:]
        assert entity.variant is None
        assert len(definition.entities) == 1


def test_oraculo_stage_one_requires_the_actual_sinal_and_a_later_weakened_attack():
    _, combat = _oraculo(1, (ORACULO_ART_IDS["sinal_funesto"],))
    signal_id = ORACULO_ART_IDS["sinal_funesto"]
    echo_id = ORACULO_ENTITY_IDS[1]
    signal = act(combat, signal_id)
    signal_event = next(event for event in signal.events if event.action == signal_id)
    observed = trial_event_from_combat_event(signal, signal_event)
    assert observed.effect_applied
    assert observed.applied_effect_id == ORACULO_SINAL_EFFECT_ID
    assert observed.applied_effect_stat == "attack"
    assert observed.applied_effect_magnitude == D("0.08")
    assert oraculo_conditions_for_event(1, observed)[0] == ()

    enemy_attack = next(
        event for event in signal.events if event.actor_entity_id == echo_id
    )
    observed_attack = trial_event_from_combat_event(signal, enemy_attack)
    conditions, context = oraculo_conditions_for_event(1, observed)
    matched, _ = oraculo_conditions_for_event(1, observed_attack, context)
    assert conditions == ()
    assert matched == (ORACULO_CONDITION_IDS[1],)
    assert any(
        effect_id == ORACULO_SINAL_EFFECT_ID
        and stat == "attack"
        and magnitude == D("0.08")
        and remaining > 0
        for effect_id, stat, magnitude, remaining, _kind in observed_attack.actor_effect_facts
    )

    no_application = replace(observed, event_id="blocked-signal", effect_applied=False)
    _, empty_context = oraculo_conditions_for_event(1, no_application)
    expired_attack = replace(
        observed_attack,
        event_id="expired-signal-attack",
        actor_effect_facts=(),
    )
    assert oraculo_conditions_for_event(1, expired_attack, empty_context)[0] == ()


@pytest.mark.parametrize(
    "response_art",
    [ORACULO_ART_IDS["vislumbre"], ORACULO_ART_IDS["veu_premonitorio"], "defend"],
)
def test_oraculo_stage_two_correlates_each_valid_answer_to_the_prepared_threat(response_art):
    arts = tuple(
        art
        for art in (
            ORACULO_ART_IDS["vislumbre"],
            ORACULO_ART_IDS["veu_premonitorio"],
        )
        if art == response_art or response_art == "defend"
    )
    _, combat = _oraculo(2, arts)
    context = {}
    before = combat
    combat = act(combat, "attack")
    _matched, context = _apply_new(before, combat, 2, oraculo_conditions_for_event, context)
    before = combat
    combat = act(combat, "attack")
    _matched, context = _apply_new(before, combat, 2, oraculo_conditions_for_event, context)
    prepared_id = combat.prepared_action_instance_id
    assert prepared_id

    before = combat
    combat = act(combat, response_art)
    matched, context = _apply_new(before, combat, 2, oraculo_conditions_for_event, context)
    assert matched == (ORACULO_CONDITION_IDS[2],)
    assert context["prepared_responses"][prepared_id] == response_art
    resolution = next(
        event
        for event in combat.events[len(before.events) :]
        if event.prepared_resolution
    )
    assert resolution.prepared_action_instance_id == prepared_id
    assert (
        trial_event_from_combat_event(
            combat, next(event for event in combat.events if event.action == response_art)
        ).response_to_prepared_action_instance_id
        == prepared_id
    )

    unrelated = TrialCombatEvent(
        event_id="unrelated-answer",
        event_type="combat_action",
        actor_id="player",
        action_id="defend",
        response_to_prepared_action_instance_id="another-threat",
    )
    assert oraculo_conditions_for_event(2, unrelated, {"prepared_ids": [prepared_id]})[0] == ()


def test_oraculo_stage_three_requires_ruina_in_the_real_window_then_correlated_defense():
    _, combat = _oraculo(
        3,
        (
            ORACULO_ART_IDS["ruina_predita"],
            ORACULO_ART_IDS["vislumbre"],
            ORACULO_ART_IDS["veu_premonitorio"],
        ),
    )
    context = {}
    before = combat
    combat = act(combat, "defend")
    _matched, context = _apply_new(before, combat, 3, oraculo_conditions_for_event, context)
    assert ORACULO_OFFENSIVE_WINDOW_TAG in combat.fighters["enemy"].training_state_tags

    before = combat
    combat = act(combat, ORACULO_ART_IDS["ruina_predita"])
    matched, context = _apply_new(before, combat, 3, oraculo_conditions_for_event, context)
    assert ORACULO_CONDITION_IDS[3][0] in matched
    prepared_id = combat.prepared_action_instance_id
    assert prepared_id

    before = combat
    combat = act(combat, "defend")
    matched, context = _apply_new(before, combat, 3, oraculo_conditions_for_event, context)
    assert ORACULO_CONDITION_IDS[3][1] in matched
    assert set(ORACULO_CONDITION_IDS[3]).issubset(
        set(matched) | {ORACULO_CONDITION_IDS[3][0]}
    )
    assert context["prepared_responses"][prepared_id] == "defend"

    outside_window = TrialCombatEvent(
        event_id="outside-window",
        event_type="combat_action",
        actor_id="player",
        target_ids=(ORACULO_ENTITY_IDS[3],),
        action_id=ORACULO_ART_IDS["ruina_predita"],
        action_instance_id="accepted-action",
    )
    assert oraculo_conditions_for_event(3, outside_window)[0] == ()


def test_luminar_ally_is_passive_required_and_receives_healing_and_barriers():
    definition, combat = _luminar(
        1,
        (
            LUMINAR_ART_IDS["fulgor"],
            LUMINAR_ART_IDS["renovacao"],
            LUMINAR_ART_IDS["egide_solar"],
        ),
    )
    ally_definition = next(entity for entity in definition.entities if entity.team == "ally")
    ally = combat.fighters[LUMINAR_ALLY_ENTITY_ID]
    assert ally_definition.required_to_survive
    assert ally_definition.variant is None
    assert ally.stats.hp == D("480") and ally.stats.defense == D("80")
    assert ally.takes_turn is False and ally.defeat_on_zero is True
    assert LUMINAR_ALLY_ENTITY_ID not in combat.order

    before = combat
    combat = act(combat, "attack", target_id=LUMINAR_ENTITY_IDS[1][0])
    _matched, context = _apply_new(before, combat, 1, luminar_conditions_for_event, {})
    assert combat.fighters[LUMINAR_ALLY_ENTITY_ID].hp < D("480")
    before = combat
    combat = act(combat, LUMINAR_ART_IDS["renovacao"], target_id=LUMINAR_ALLY_ENTITY_ID)
    matched, context = _apply_new(before, combat, 1, luminar_conditions_for_event, context)
    assert matched == (LUMINAR_CONDITION_IDS[1],)
    heal = next(
        event
        for event in combat.events[len(before.events) :]
        if event.action == LUMINAR_ART_IDS["renovacao"]
    )
    assert heal.target == LUMINAR_ALLY_ENTITY_ID
    assert heal.effective_healing > 0


def test_luminar_stage_one_barrier_requires_real_absorption_and_target_correlation():
    _, combat = _luminar(
        1,
        (LUMINAR_ART_IDS["egide_solar"], LUMINAR_ART_IDS["fulgor"]),
    )
    context = {}
    before = combat
    combat = act(combat, "attack", target_id=LUMINAR_ENTITY_IDS[1][0])
    _matched, context = _apply_new(before, combat, 1, luminar_conditions_for_event, context)
    before = combat
    combat = act(combat, LUMINAR_ART_IDS["egide_solar"], target_id=LUMINAR_ALLY_ENTITY_ID)
    matched, context = _apply_new(before, combat, 1, luminar_conditions_for_event, context)
    assert combat.fighters[LUMINAR_ALLY_ENTITY_ID].barrier > 0
    assert matched == (LUMINAR_CONDITION_IDS[1],)
    attack = next(
        event
        for event in combat.events[len(before.events) :]
        if event.actor_entity_id == LUMINAR_ENTITY_IDS[1][0]
    )
    assert attack.barrier_absorbed > 0
    assert attack.target_barrier_source == f"player:{LUMINAR_ART_IDS['egide_solar']}"

    no_absorption = TrialCombatEvent(
        event_id="barrier-not-tested",
        event_type="combat_action",
        actor_id=LUMINAR_ENTITY_IDS[1][0],
        target_ids=(LUMINAR_ALLY_ENTITY_ID,),
        target_barrier_source=f"player:{LUMINAR_ART_IDS['egide_solar']}",
        barrier_absorbed=D(0),
    )
    prior_barrier = dict(
        context,
        ally_trial_barrier_source=no_absorption.target_barrier_source,
    )
    assert luminar_conditions_for_event(1, no_absorption, prior_barrier)[0] == ()


def test_luminar_stage_two_judgment_reduces_real_recovery_and_reports_healing_facts():
    _, combat = _luminar(
        2,
        (LUMINAR_ART_IDS["julgamento"], LUMINAR_ART_IDS["fulgor"]),
    )
    context = {}
    before = combat
    combat = act(combat, "attack")
    _matched, context = _apply_new(before, combat, 2, luminar_conditions_for_event, context)
    before = combat
    combat = act(combat, LUMINAR_ART_IDS["julgamento"])
    matched, context = _apply_new(before, combat, 2, luminar_conditions_for_event, context)
    assert matched == (LUMINAR_CONDITION_IDS[2],)
    recovery = next(
        event
        for event in combat.events[len(before.events) :]
        if event.action == "trial.luminar.recuperacao_treino"
    )
    assert recovery.healing_received_multiplier == D("0.85")
    assert recovery.calculated_healing < recovery.base_healing
    assert recovery.effective_healing == recovery.calculated_healing > 0
    assert recovery.overheal == 0
    assert recovery.target_effect_ids == ("luminar.julgamento.cura",)

    not_judged = replace(
        trial_event_from_combat_event(combat, recovery),
        event_id="no-judgment",
        target_effect_ids=(),
        target_effect_application_event_ids=(),
    )
    assert luminar_conditions_for_event(2, not_judged, {})[0] == ()


def test_luminar_stage_three_requires_both_pressure_a_decision_then_survival():
    _, combat = _luminar(
        3,
        (
            LUMINAR_ART_IDS["fulgor"],
            LUMINAR_ART_IDS["renovacao"],
            LUMINAR_ART_IDS["egide_solar"],
        ),
    )
    context = {}
    before = combat
    combat = act(combat, "defend")
    _matched, context = _apply_new(before, combat, 3, luminar_conditions_for_event, context)
    assert context.get("pressured_entities") == ["player"]
    before = combat
    combat = act(combat, LUMINAR_ART_IDS["fulgor"])
    matched, context = _apply_new(before, combat, 3, luminar_conditions_for_event, context)
    assert LUMINAR_CONDITION_IDS[3][0] in matched
    assert context.get("priority_decision_event_id") is None
    before = combat
    combat = act(combat, LUMINAR_ART_IDS["renovacao"], target_id=LUMINAR_ALLY_ENTITY_ID)
    _matched, context = _apply_new(before, combat, 3, luminar_conditions_for_event, context)
    assert context["priority_decision_event_id"]
    before = combat
    combat = act(combat, "attack", target_id=LUMINAR_ENTITY_IDS[3][0])
    matched, context = _apply_new(before, combat, 3, luminar_conditions_for_event, context)
    assert LUMINAR_CONDITION_IDS[3][1] in matched
    assert combat.fighters["player"].hp > 0
    assert combat.fighters[LUMINAR_ALLY_ENTITY_ID].hp > 0


def test_required_luminar_ally_zero_hp_immediately_defeats_attempt():
    _, combat = _luminar(1, (LUMINAR_ART_IDS["fulgor"],))
    ally = combat.fighters[LUMINAR_ALLY_ENTITY_ID]
    ally.hp = D(1)
    result = act(combat, "defend")
    assert result.result == "defeat"
    assert result.fighters[LUMINAR_ALLY_ENTITY_ID].hp == 0


def test_generic_veil_barrier_reduces_only_removable_numeric_debuff_magnitude():
    player = _player("oraculo")
    enemy = Fighter(
        "enemy", "Target", 10, CombatStats(D(1000), D(1), D(1), D(1)), D(1000), side="enemy"
    )
    combat = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        {
            "barrier": Action(
                "barrier",
                "Barrier",
                D(0),
                self_barrier_coefficient=D("0.70"),
                self_barrier_duration=2,
                self_barrier_debuff_magnitude_reduction=D("0.10"),
            ),
            "attack": Action("attack", "Attack", D(1)),
        },
        {"hit": Action("hit", "Hit", D(1))},
        ("hit",),
    )
    combat = start_combat(combat)
    combat = act(combat, "barrier")
    target = combat.fighters["player"]
    assert target.barrier_debuff_magnitude_reduction == D("0.10")
    assert apply_effect(combat, target, Effect("atk", "attack", D("0.20"), 2, 0))
    assert target.effects[-1].magnitude == D("0.1800")
    assert apply_effect(combat, target, Effect("dot", "burn", D("0.20"), 2, 0))
    assert target.effects[-1].magnitude == D("0.20")
    assert apply_effect(
        combat,
        target,
        Effect("fixed", "defense", D("0.20"), 2, 0, fixed_mechanic=True),
    )
    assert target.effects[-1].magnitude == D("0.20")


def test_veil_protection_ends_when_its_barrier_breaks_or_expires():
    arts = (ORACULO_ART_IDS["veu_premonitorio"],)
    for expiration in (False, True):
        _, combat = _oraculo(2, arts)
        combat = act(combat, ORACULO_ART_IDS["veu_premonitorio"])
        target = combat.fighters["player"]
        assert target.barrier > 0
        assert target.barrier_debuff_magnitude_reduction == D("0.10")

        if expiration:
            target.barrier_remaining = 1
            target.barrier_applied_opportunity = target.opportunity - 1
            _end_turn(combat)
        else:
            _deal_damage(target, target.barrier + 1)

        assert target.barrier == 0
        assert target.barrier_debuff_magnitude_reduction == 0
        assert apply_effect(
            combat, target, Effect("after-veil", "attack", D("0.20"), 2, 0)
        )
        assert target.effects[-1].magnitude == D("0.20")


def test_generic_ally_healing_reports_calculated_effective_and_overheal():
    player = _player("luminar")
    ally = Fighter(
        "ally",
        "Ally",
        10,
        CombatStats(D(100), D(10), D(0), D(0)),
        D(60),
        side="player",
        takes_turn=False,
    )
    enemy = Fighter(
        "enemy", "Enemy", 10, CombatStats(D(100), D(1), D(0), D(1)), D(100), side="enemy"
    )
    combat = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": replace(player, stats=CombatStats(D(100), D(100), D(0), D(110)), hp=D(100)),
         "ally": ally, "enemy": enemy},
        {
            "heal": Action("heal", "Heal", D(0), target_mode="ally", heal_coefficient=D(1)),
            "attack": Action("attack", "Attack", D(1)),
        },
        {"hit": Action("hit", "Hit", D(0))},
        ("hit",),
    )
    combat = start_combat(combat)
    updated = act(combat, "heal", target_id="ally")
    event = next(event for event in updated.events if event.action == "heal")
    assert event.base_healing == D(100)
    assert event.calculated_healing == D(100)
    assert event.effective_healing == D(40)
    assert event.overheal == D(60)
    assert event.healed == D(40)


def test_oraculo_luminar_snapshot_roundtrip_and_legacy_defaults():
    definition, combat = _luminar(
        3,
        (
            LUMINAR_ART_IDS["fulgor"],
            LUMINAR_ART_IDS["renovacao"],
            LUMINAR_ART_IDS["egide_solar"],
        ),
    )
    combat = act(combat, "defend")
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.ai_target_cycle == definition.ai_target_cycle
    assert restored.ai_target_position == combat.ai_target_position
    assert restored.fighters[LUMINAR_ALLY_ENTITY_ID].takes_turn is False
    assert restored.events == combat.events

    legacy = encode(combat)
    legacy.pop("ai_target_cycle")
    legacy.pop("ai_target_position")
    for fighter in legacy["fighters"].values():
        fighter.pop("barrier_debuff_magnitude_reduction", None)
    for action in list(legacy["player_actions"].values()) + list(
        legacy["enemy_actions"].values()
    ):
        action.pop("self_barrier_debuff_magnitude_reduction", None)
        action.pop("target_barrier_debuff_magnitude_reduction", None)
        action.pop("target_effects", None)
    for event in legacy["events"]:
        for key in (
            "barrier_applied_source",
            "applied_effect_stat",
            "applied_effect_magnitude",
            "applied_effect_duration",
            "applied_effect_kind",
            "applied_effect_removable",
            "actor_effect_facts",
            "actor_applied_effect_stat",
            "actor_applied_effect_magnitude",
            "actor_applied_effect_duration",
            "actor_applied_effect_kind",
            "base_healing",
            "calculated_healing",
            "effective_healing",
            "healing_received_multiplier",
            "overheal",
            "target_hp_after",
            "fighter_hp_after",
        ):
            event.pop(key, None)
    decoded_legacy = decode(legacy, combat.id, combat.ruleset, combat.version)
    assert decoded_legacy.ai_target_cycle == ()
    assert decoded_legacy.ai_target_position == 0
    assert decoded_legacy.events[0].healing_received_multiplier == D(1)
