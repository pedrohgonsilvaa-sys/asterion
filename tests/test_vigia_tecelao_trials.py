from copy import deepcopy
from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
from uuid import uuid4

from asterion.domain.arts import TECELAO_ART_IDS, VIGIA_ART_IDS
from asterion.domain.class_trials import (
    TECELAO_CONDITION_IDS,
    TECELAO_ENTITY_IDS,
    VIGIA_CONDITION_IDS,
    VIGIA_ENTITY_IDS,
    TrialCombatEvent,
    create_tecelao_trial_combat,
    create_vigia_trial_combat,
    tecelao_conditions_for_event,
    tecelao_player_actions,
    tecelao_stage_definition,
    trial_event_from_combat_event,
    vigia_conditions_for_event,
    vigia_stage_definition,
)
from asterion.domain.combat import Action, Combat, DotState, Fighter, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    direct_damage,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _player(character_class: str) -> Fighter:
    stats = CombatStats(D("2000"), D("200"), D("150"), D("300"), crit=D(0))
    return Fighter(
        "player",
        "Treinando",
        10,
        stats,
        D("2000"),
        character_class=character_class,
    )


def _vigia(stage: int, art_names: tuple[str, ...]):
    arts = tuple(VIGIA_ART_IDS[name] for name in art_names)
    definition = vigia_stage_definition(stage, allowed_art_ids=arts)
    combat = create_vigia_trial_combat(_player("vigia"), definition)
    return definition, start_combat(combat)


def _tecelao(stage: int, art_names: tuple[str, ...]):
    arts = tuple(TECELAO_ART_IDS[name] for name in art_names)
    definition = tecelao_stage_definition(stage, allowed_art_ids=arts)
    combat = create_tecelao_trial_combat(_player("tecelao"), definition)
    return definition, start_combat(combat)


def _generic_chain_combat():
    player = _player("tecelao")
    target = Fighter(
        "dummy",
        "Dummy",
        10,
        CombatStats(D("2000"), D("10"), D("0"), D("10"), evasion=D(0), block=D(0)),
        D("2000"),
        side="enemy",
    )
    combat = Combat(
        uuid4(),
        CURRENT_COMBAT_RULESET,
        {"player": player, "dummy": target},
        {
            "normal": Action(
                "normal",
                "Normal",
                D(1),
                prepares_chain="thread",
                consumes_chain="thread",
                chain_power_bonus=D("0.20"),
                prepares_chain_duration=2,
            ),
            "different": Action(
                "different",
                "Different",
                D(1),
                consumes_chain="thread",
                chain_power_bonus=D("0.20"),
            ),
            "attack": Action("attack", "Attack", D(1)),
        },
        {"hold": Action("hold", "Hold", D(0))},
        ("hold",),
        variant=None,
    )
    return start_combat(combat)


def test_vigia_definitions_have_fixed_values_and_three_protection_layers():
    expected = {
        1: ("trial_entity.vigia.marca", "600", "95", "125", "85"),
        2: ("trial_entity.vigia.camadas", "650", "90", "90", "85"),
        3: ("trial_entity.vigia.momento", "650", "100", "90", "90"),
    }
    for stage, row in expected.items():
        definition = vigia_stage_definition(stage)
        entity = definition.entities[0]
        assert (entity.entity_id, str(entity.max_hp)) == row[:2]
        assert tuple(str(entity.stats[key]) for key in ("attack", "defense", "agility")) == row[2:]
        assert entity.variant is None

    layered = vigia_stage_definition(2).entities[0]
    assert layered.protection_layers == 3
    assert layered.protection_reduction_per_layer == D("0.12")


def test_vigia_saraivada_is_one_multihit_action_and_removes_one_layer_per_hit():
    _, combat = _vigia(2, ("saraivada",))
    art_id = VIGIA_ART_IDS["saraivada"]
    updated = act(combat, art_id)
    echo = updated.fighters["enemy"]
    hits = [event for event in updated.events if event.action == art_id]

    assert len(hits) == 3
    assert {event.action_instance_id for event in hits} == {hits[0].action_instance_id}
    assert [(event.hit_index, event.hit_count) for event in hits] == [(1, 3), (2, 3), (3, 3)]
    assert [event.protection_layers_before for event in hits] == [3, 2, 1]
    assert [event.protection_layers_after for event in hits] == [2, 1, 0]
    base_damage = direct_damage(
        updated.fighters["player"].stat("attack"),
        D("0.40"),
        echo.stat("defense"),
        updated.fighters["player"].level,
    )
    assert [event.calculated_damage for event in hits] == [
        int(
            (D(base_damage) * (D(1) - D(layers) * D("0.12"))).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
        for layers in (3, 2, 1)
    ]
    assert echo.protection_layers == 0
    assert updated.fighters["player"].cooldowns[art_id] == 4

    context = {}
    conditions = ()
    for event in hits:
        observed = trial_event_from_combat_event(updated, event)
        new_conditions, context = vigia_conditions_for_event(2, observed, context)
        conditions += new_conditions
    assert conditions == (VIGIA_CONDITION_IDS[2],)


def test_vigia_single_hit_miss_and_dot_follow_protection_layer_rules():
    _, combat = _vigia(2, ())
    single_hit = act(combat, "attack")
    attack_event = next(event for event in single_hit.events if event.action == "attack")
    assert attack_event.protection_layers_before == 3
    assert attack_event.protection_layers_after == 2

    _, missed_combat = _vigia(2, ())
    enemy = missed_combat.fighters["enemy"]
    enemy.stats = replace(enemy.stats, evasion=D("100"))
    missed = act(missed_combat, "attack")
    miss_event = next(event for event in missed.events if event.action == "attack")
    assert miss_event.dodged
    assert miss_event.protection_layers_before == 3
    assert miss_event.protection_layers_after == 3

    _, dot_combat = _vigia(2, ())
    enemy_id = dot_combat.fighters["enemy"].id
    dot_combat.dot_states[enemy_id] = [
        DotState("burn", 1, 1, D("10"), "player", application_event="test-burn")
    ]
    ticked = act(dot_combat, "defend")
    tick = next(event for event in ticked.mechanic_events if event.action == "dot:burn:tick")
    assert tick.dot_application_event_id == "test-burn"
    assert ticked.fighters["enemy"].protection_layers == 3

    _, unprotected_combat = _vigia(2, ())
    unprotected_combat.fighters["enemy"].protection_layers = 0
    unprotected = act(unprotected_combat, "attack")
    unprotected_event = next(
        event for event in unprotected.events if event.action == "attack"
    )
    assert unprotected_event.protection_layers_before == 0
    assert unprotected_event.protection_layers_after == 0
    assert unprotected_event.calculated_damage == direct_damage(
        unprotected.fighters["player"].stat("attack"),
        D(1),
        unprotected.fighters["enemy"].stat("defense"),
        unprotected.fighters["player"].level,
    )


def test_vigia_mark_condition_requires_same_echo_and_real_active_effect():
    _, combat = _vigia(1, ("marca_da_presa",))
    mark_id = VIGIA_ART_IDS["marca_da_presa"]
    marked = act(combat, mark_id)
    mark_event = next(event for event in marked.events if event.action == mark_id)
    mark_observed = trial_event_from_combat_event(marked, mark_event)
    conditions, context = vigia_conditions_for_event(1, mark_observed)
    assert conditions == ()

    attack = act(marked, "attack")
    hit = next(event for event in attack.events if event.action == "attack")
    observed = trial_event_from_combat_event(attack, hit)
    conditions, _ = vigia_conditions_for_event(1, observed, context)
    assert conditions == (VIGIA_CONDITION_IDS[1],)

    wrong_target = TrialCombatEvent(
        event_id="wrong-target",
        event_type="combat_action",
        actor_id="player",
        target_ids=("another-echo",),
        action_id="attack",
        effective_damage=D(1),
        target_effect_ids=("vigia.marca_da_presa",),
        target_effect_application_event_ids=(context["mark_application_event_id"],),
    )
    assert vigia_conditions_for_event(1, wrong_target, context)[0] == ()


def test_vigia_stage_three_requires_exposed_window_and_active_eye_effects():
    _, combat = _vigia(3, ("olho_da_vigilia", "disparo_preciso"))
    eye = act(combat, VIGIA_ART_IDS["olho_da_vigilia"])
    exposed_attack = act(eye, VIGIA_ART_IDS["disparo_preciso"])
    hit = next(
        event
        for event in exposed_attack.events
        if event.action == VIGIA_ART_IDS["disparo_preciso"]
    )
    observed = trial_event_from_combat_event(exposed_attack, hit)
    assert "vigia.exposto" in observed.target_state_tags
    conditions, _ = vigia_conditions_for_event(3, observed)
    assert conditions == (VIGIA_CONDITION_IDS[3],)

    protected = TrialCombatEvent(
        event_id="protected-hit",
        event_type="combat_action",
        actor_id="player",
        target_ids=(VIGIA_ENTITY_IDS[3],),
        action_id=VIGIA_ART_IDS["disparo_preciso"],
        effective_damage=D(1),
        target_state_tags=("vigia.protegido",),
        actor_effect_ids=("vigia.olho_da_vigilia.per", "vigia.olho_da_vigilia.crit"),
    )
    assert vigia_conditions_for_event(3, protected)[0] == ()


def test_tecelao_passive_manifestations_are_targetable_but_never_take_turns():
    definition, combat = _tecelao(1, ("ruptura_da_trama",))
    manifestations = [entity for entity in definition.entities if entity.turn_policy == "passive"]
    assert len(manifestations) == 2
    assert all(not entity.action_ids for entity in manifestations)
    assert all(not combat.fighters[entity.entity_id].takes_turn for entity in manifestations)
    assert all(combat.fighters[entity.entity_id].hp == D("180") for entity in manifestations)

    updated = act(combat, TECELAO_ART_IDS["ruptura_da_trama"])
    hit_events = [
        event
        for event in updated.events
        if event.action == TECELAO_ART_IDS["ruptura_da_trama"]
    ]
    assert {event.target for event in hit_events} == {
        entity.entity_id for entity in definition.entities
    }
    assert len({event.action_instance_id for event in hit_events}) == 1
    assert updated.order.count(TECELAO_ENTITY_IDS[1][1]) == 0
    assert updated.order.count(TECELAO_ENTITY_IDS[1][2]) == 0


def test_tecelao_aoe_condition_correlates_two_valid_targets_to_one_action():
    definition, combat = _tecelao(2, ("ruptura_da_trama",))
    art_id = TECELAO_ART_IDS["ruptura_da_trama"]
    updated = act(combat, art_id)
    hits = [event for event in updated.events if event.action == art_id]
    assert len(hits) == 3
    assert len({event.action_instance_id for event in hits}) == 1
    assert updated.fighters["player"].cooldowns[art_id] == 4

    context = {}
    conditions = ()
    for event in hits:
        observed = trial_event_from_combat_event(updated, event)
        new_conditions, context = tecelao_conditions_for_event(2, observed, context)
        conditions += new_conditions
    assert conditions == (TECELAO_CONDITION_IDS[2][0],)

    first = trial_event_from_combat_event(updated, hits[0])
    second_action = replace(
        first,
        event_id="separate-action-target",
        action_instance_id="different-action-instance",
        target_ids=(definition.entities[1].entity_id,),
    )
    conditions, context = tecelao_conditions_for_event(2, first, {})
    conditions, context = tecelao_conditions_for_event(2, second_action, context)
    assert conditions == ()

    _, outside_combat = _vigia(3, ("olho_da_vigilia", "disparo_preciso"))
    outside_combat = act(outside_combat, VIGIA_ART_IDS["olho_da_vigilia"])
    outside_combat = act(outside_combat, "defend")
    protected_attack = act(outside_combat, VIGIA_ART_IDS["disparo_preciso"])
    protected_event = next(
        event
        for event in protected_attack.events
        if event.action == VIGIA_ART_IDS["disparo_preciso"]
    )
    assert "vigia.protegido" in protected_event.target_state_tags
    assert vigia_conditions_for_event(
        3, trial_event_from_combat_event(protected_attack, protected_event)
    )[0] == ()


def test_tecelao_chain_is_generic_persisted_and_empowers_only_a_different_art():
    combat = _generic_chain_combat()
    prepared = act(combat, "normal")
    pending = prepared.fighters["player"].action_chains["thread"]
    assert pending["remaining"] == 2
    assert pending["duration"] == 2
    persisted = decode(encode(prepared), prepared.id, prepared.ruleset, prepared.version)
    assert persisted.fighters["player"].action_chains == prepared.fighters["player"].action_chains

    repeated = act(persisted, "normal")
    repeated_event = [event for event in repeated.events if event.action == "normal"][-1]
    assert not repeated_event.chain_consumed
    assert repeated_event.chain_window_before == 2
    assert repeated_event.chain_window_after == 2
    assert repeated.fighters["player"].action_chains["thread"]["prepared_by_action_id"] == "normal"
    assert (
        repeated.fighters["player"].action_chains["thread"]["action_instance_id"]
        == pending["action_instance_id"]
    )
    assert repeated.fighters["player"].action_chains["thread"]["remaining"] == 1

    empowered = act(repeated, "different")
    event = next(event for event in empowered.events if event.action == "different")
    assert event.chain_consumed and event.chain_empowered
    assert event.empowered_by_action_instance_id
    assert event.chain_prepared_by_action_instance_id == pending["action_instance_id"]
    assert event.chain_consumed_by_action_instance_id == event.action_instance_id
    assert event.power_component == "damage"
    assert event.power_multiplier == D("1.20")
    assert event.damage_power_multiplier == D("1.20")
    assert event.calculated_damage == direct_damage(
        D("200"), D("1.20"), D(0), 10, critical=False
    )
    assert empowered.fighters["player"].action_chains == {}


def test_tecelao_chain_same_art_does_not_refresh_and_expires_after_two_turns():
    combat = _generic_chain_combat()
    prepared = act(combat, "normal")
    source_id = prepared.fighters["player"].action_chains["thread"]["action_instance_id"]

    same_art = act(prepared, "normal")
    repeated = [event for event in same_art.events if event.action == "normal"][-1]
    assert not repeated.chain_consumed and not repeated.chain_empowered
    assert repeated.chain_window_before == repeated.chain_window_after == 2
    assert (
        same_art.fighters["player"].action_chains["thread"]["action_instance_id"]
        == source_id
    )
    assert same_art.fighters["player"].action_chains["thread"]["remaining"] == 1

    same_art_again = act(same_art, "normal")
    third = [event for event in same_art_again.events if event.action == "normal"][-1]
    assert not third.chain_consumed
    assert third.chain_window_before == third.chain_window_after == 1
    assert same_art_again.fighters["player"].action_chains == {}
    expired = [event for event in same_art_again.events if event.action == "chain:expired"]
    assert len(expired) == 1
    assert expired[0].chain_state_before == "ready"
    assert expired[0].chain_state_after == "expired"
    assert expired[0].chain_prepared_by_action_instance_id == source_id


def test_tecelao_chain_rejected_action_does_not_consume_or_change_window():
    prepared = act(_generic_chain_combat(), "normal")
    prepared.fighters["dummy2"] = Fighter(
        "dummy2",
        "Second Dummy",
        10,
        CombatStats(D("2000"), D("10"), D("0"), D("9"), evasion=D(0), block=D(0)),
        D("2000"),
        side="enemy",
    )
    unchanged = act(prepared, "different", target_id="missing")
    assert unchanged is prepared
    assert unchanged.fighters["player"].action_chains["thread"]["remaining"] == 2


def test_chain_power_applies_to_every_hit_of_one_multihit_action():
    combat = _generic_chain_combat()
    combat.player_actions["different"] = replace(
        combat.player_actions["different"], hit_count=3
    )
    prepared = act(combat, "normal")
    resolved = act(prepared, "different")
    events = [event for event in resolved.events if event.action == "different"]
    assert [(event.hit_index, event.hit_count) for event in events] == [(1, 3), (2, 3), (3, 3)]
    assert len({event.action_instance_id for event in events}) == 1
    assert all(event.chain_consumed and event.chain_empowered for event in events)
    assert all(event.power_multiplier == D("1.20") for event in events)
    assert len({event.chain_consumed_by_action_instance_id for event in events}) == 1
    assert resolved.fighters["player"].action_chains == {}


def test_chain_component_policy_supports_future_path_specific_healing_bonus():
    player = _player("tecelao")
    player.hp = D("1000")
    ally = Fighter(
        "ally",
        "Ally",
        10,
        CombatStats(D("2000"), D("10"), D("0"), D("10")),
        D("500"),
        side="player",
    )
    enemy = Fighter(
        "dummy",
        "Dummy",
        10,
        CombatStats(D("2000"), D("10"), D("0"), D("10"), evasion=D(0), block=D(0)),
        D("2000"),
        side="enemy",
    )
    combat = start_combat(
        Combat(
            uuid4(),
            CURRENT_COMBAT_RULESET,
            {"player": player, "ally": ally, "dummy": enemy},
            {
                "prepare": Action("prepare", "Prepare", D(1), prepares_chain="thread"),
                "mending": Action(
                    "mending",
                    "Mending",
                    D(0),
                    target_mode="ally",
                    heal_coefficient=D("0.50"),
                    consumes_chain="thread",
                    chain_power_bonus_damage=D("0.15"),
                    chain_power_bonus_healing=D("0.06"),
                    chain_power_bonus_barrier=D("0.06"),
                ),
            },
            {"hold": Action("hold", "Hold", D(0))},
            ("hold",),
            variant=None,
        )
    )
    prepared = act(combat, "prepare")
    healed = act(prepared, "mending", target_id="ally")
    event = next(event for event in healed.events if event.action == "mending")
    assert event.power_component == "healing"
    assert event.power_multiplier == D("1.06")
    assert event.healed == D("106")
    assert healed.fighters["ally"].hp == D("606")


def test_tecelao_class_arts_prepare_then_a_different_art_consumes_the_chain():
    _, combat = _tecelao(1, ("fio_cortante", "chama_tecida"))
    principal_id = TECELAO_ENTITY_IDS[1][0]
    priming = act(combat, TECELAO_ART_IDS["fio_cortante"], target_id=principal_id)
    priming_event = next(
        event
        for event in priming.events
        if event.action == TECELAO_ART_IDS["fio_cortante"]
    )
    assert priming_event.chain_state_after == "ready"
    assert priming.fighters["player"].action_chains["trama_encadeada"][
        "prepared_by_action_id"
    ] == TECELAO_ART_IDS["fio_cortante"]

    flame = act(priming, TECELAO_ART_IDS["chama_tecida"], target_id=principal_id)
    flame_event = next(
        event for event in flame.events if event.action == TECELAO_ART_IDS["chama_tecida"]
    )
    assert flame_event.dot_kind == "burn" and flame_event.dot_application_event_id
    assert flame_event.chain_consumed and flame_event.chain_empowered
    assert flame_event.power_multiplier == D("1.10")
    assert flame_event.calculated_damage == direct_damage(
        flame.fighters["player"].stat("attack"),
        D("0.85") * D("1.10"),
        next(
            fighter for fighter in flame.fighters.values() if fighter.id == principal_id
        ).stat("defense"),
        flame.fighters["player"].level,
        critical=False,
    )
    assert flame_event.chain_prepared_by_action_id == TECELAO_ART_IDS["fio_cortante"]
    assert flame_event.chain_prepared_by_action_instance_id == priming_event.action_instance_id
    assert flame_event.chain_consumed_by_action_instance_id == flame_event.action_instance_id
    assert flame.fighters["player"].action_chains == {}
    # The strengthened Chama applies only its normal one Burn stack.
    burn_states = [
        dot
        for dot in flame.dot_states.get(principal_id, ())
        if dot.kind == "burn"
    ]
    assert sum(dot.stacks for dot in burn_states) == 1


def test_tecelao_baseline_chain_bonus_and_window_are_applied_to_each_primary_component():
    for art_id in TECELAO_ART_IDS.values():
        action = tecelao_player_actions((art_id,))[art_id]
        assert action.chain_power_bonus == D("0.10")
        assert action.prepares_chain_duration == 2

    _, rupture_combat = _tecelao(2, ("fio_cortante", "ruptura_da_trama"))
    first_target = TECELAO_ENTITY_IDS[2][0]
    primed = act(rupture_combat, TECELAO_ART_IDS["fio_cortante"], target_id=first_target)
    rupture = act(primed, TECELAO_ART_IDS["ruptura_da_trama"])
    rupture_events = [
        event
        for event in rupture.events
        if event.action == TECELAO_ART_IDS["ruptura_da_trama"]
        and event.actor == "player"
    ]
    assert len(rupture_events) == 3
    assert len({event.action_instance_id for event in rupture_events}) == 1
    assert len({event.chain_consumed_by_action_instance_id for event in rupture_events}) == 1
    assert {event.power_multiplier for event in rupture_events} == {D("1.10")}
    expected_rupture_damage = {
        direct_damage(
            rupture.fighters["player"].stat("attack"),
            D("0.80") * D("1.10"),
            next(
                fighter
                for fighter in rupture.fighters.values()
                if fighter.id == entity_id
            ).stat("defense"),
            rupture.fighters["player"].level,
            critical=False,
        )
        for entity_id in TECELAO_ENTITY_IDS[2]
    }
    assert {event.calculated_damage for event in rupture_events} == expected_rupture_damage

    _, barrier_combat = _tecelao(3, ("chama_tecida", "veu_entrelacado"))
    principal = TECELAO_ENTITY_IDS[3][0]
    primed_barrier = act(
        barrier_combat, TECELAO_ART_IDS["chama_tecida"], target_id=principal
    )
    protected = act(primed_barrier, TECELAO_ART_IDS["veu_entrelacado"])
    barrier_event = next(
        event
        for event in protected.events
        if event.action == TECELAO_ART_IDS["veu_entrelacado"]
    )
    assert barrier_event.chain_empowered
    assert barrier_event.power_component == "barrier"
    assert barrier_event.power_multiplier == D("1.10")
    assert barrier_event.barrier_value == D("198")


def test_tecelao_chain_event_condition_requires_real_baseline_power_and_is_idempotent():
    context = {}
    action_id = TECELAO_ART_IDS["fio_cortante"]
    event = TrialCombatEvent(
        event_id="chain-one",
        event_type="combat_action",
        actor_id="player",
        action_id=action_id,
        action_instance_id="consumer-one",
        chain_consumed=True,
        chain_empowered=True,
        chain_prepared_by_action_id=TECELAO_ART_IDS["chama_tecida"],
        power_component="damage",
        power_multiplier=D("1.00"),
    )
    conditions, context = tecelao_conditions_for_event(3, event, context)
    assert conditions == ()
    valid = replace(event, event_id="chain-two", power_multiplier=D("1.10"))
    conditions, context = tecelao_conditions_for_event(3, valid, context)
    assert conditions == ()
    second = replace(
        valid,
        event_id="chain-three",
        action_instance_id="consumer-two",
    )
    conditions, context = tecelao_conditions_for_event(3, second, context)
    assert conditions == (TECELAO_CONDITION_IDS[3][0],)
    conditions, context = tecelao_conditions_for_event(3, second, context)
    assert conditions == ()


def test_vigia_and_tecelao_combat_codec_roundtrips_and_decodes_legacy_defaults():
    _, combat = _vigia(3, ("olho_da_vigilia", "disparo_preciso"))
    encoded = encode(combat)
    decoded = decode(encoded, combat.id, combat.ruleset, combat.version)
    assert decoded.fighters["enemy"].training_state_tags == (
        "vigia.protegido",
    )
    assert (
        decoded.player_actions[VIGIA_ART_IDS["olho_da_vigilia"]].self_effects
        == combat.player_actions[VIGIA_ART_IDS["olho_da_vigilia"]].self_effects
    )

    legacy = deepcopy(encoded)
    for action_group in (legacy["player_actions"], legacy["enemy_actions"]):
        for action in action_group.values():
            for key in (
                "hit_count",
                "self_effects",
                "self_state_tags_after",
                "effect_trigger_scope",
                "prepares_chain",
                "consumes_chain",
                "chain_power_bonus",
                "chain_power_bonus_damage",
                "chain_power_bonus_healing",
                "chain_power_bonus_barrier",
                "prepares_chain_duration",
            ):
                action.pop(key, None)
    for event in (*legacy["events"], *legacy.get("mechanic_events", ())):
        for key in (
            "chain_prepared_by_action_instance_id",
            "chain_consumed_by_action_instance_id",
            "chain_window_before",
            "chain_window_after",
            "power_component",
            "power_multiplier",
            "damage_power_multiplier",
            "healing_power_multiplier",
            "barrier_power_multiplier",
        ):
            event.pop(key, None)
    for fighter in legacy["fighters"].values():
        for key in (
            "protection_layers",
            "protection_reduction_per_layer",
            "training_state_tags",
            "tagged_direct_damage_reductions",
            "action_chains",
        ):
            fighter.pop(key, None)
    restored = decode(legacy, combat.id, combat.ruleset, combat.version)
    assert restored.fighters["enemy"].protection_layers == 0
    assert restored.fighters["enemy"].training_state_tags == ()
    assert restored.player_actions[VIGIA_ART_IDS["olho_da_vigilia"]].hit_count == 1
