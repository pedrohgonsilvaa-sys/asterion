from decimal import Decimal
from uuid import uuid4

from asterion.bot.combat_ui import CombatConsumableCallback, event_line
from asterion.domain.combat import (
    Action,
    CombatConsumableOption,
    DotState,
    Effect,
    _end_turn,
    _perform,
    act,
    apply_dot_stacks,
    apply_effect,
    apply_effect_batch,
    combat_consumable_options,
    consumable_effect_options,
    effective_heal_amount,
    use_combat_consumable,
)
from asterion.domain.combat_math import Stats
from asterion.domain.road import CREATURES, create_road_combat
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _combat():
    state = create_road_combat(
        uuid4(),
        "Luiken",
        "sentinela",
        "remanescente",
        D("500"),
        CREATURES[0],
        1,
        None,
    )
    state.fighters["player"].stats = Stats(D("1000"), D("100"), D("0"), D("100"))
    state.fighters["player"].hp = D("500")
    state.fighters["enemy"].stats = Stats(D("1000"), D("500"), D("0"), D("50"))
    return state


def test_healing_consumable_uses_official_amount_and_cd2_action_turn():
    state = _combat()
    state.fighters["player"].hp = D("500")
    result = use_combat_consumable(
        state, "consumable.heal", budget_limit=1
    )
    assert result is not state
    use_event = next(event for event in result.events if event.action.startswith("consumable:"))
    assert use_event.action == "consumable:consumable.heal"
    assert use_event.healed == D("220")
    assert result.consumable_uses == 1
    assert result.fighters["player"].cooldowns["consumable"] > result.fighters["player"].opportunity
    assert use_combat_consumable(
        result, "consumable.heal", budget_limit=1
    ) is result


def test_protection_floor_absorbs_direct_damage_and_roundtrips_decimal():
    state = _combat()
    state.fighters["player"].stats = Stats(D("1001"), D("100"), D("0"), D("100"))
    before_hp = state.fighters["player"].hp
    result = use_combat_consumable(
        state, "consumable.protection.vde.ii", budget_limit=2
    )
    use_event = next(event for event in result.events if event.action.startswith("consumable:"))
    assert use_event.barrier_value == D("120")
    result = act(result, "attack")
    incoming = next(event for event in result.events if event.barrier_absorbed > 0)
    assert incoming.barrier_absorbed > 0
    assert result.fighters["player"].hp == max(
        D(0), before_hp - (D(incoming.damage) - incoming.barrier_absorbed)
    )

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].barrier == result.fighters["player"].barrier
    assert isinstance(restored.fighters["player"].barrier, Decimal)
    assert (
        restored.fighters["player"].barrier_remaining
        == result.fighters["player"].barrier_remaining
    )


def test_protection_reapplication_replaces_value_and_duration():
    state = _combat()
    player = state.fighters["player"]
    player.barrier = D("17")
    player.barrier_remaining = 1
    player.barrier_applied_opportunity = player.opportunity - 1
    result = use_combat_consumable(
        state, "consumable.protection.vde.ii", budget_limit=2
    )
    use_event = next(event for event in result.events if event.action.startswith("consumable:"))
    assert use_event.barrier_value == D("120")
    assert result.fighters["player"].barrier_source == "player:consumable.protecao"
    assert result.fighters["player"].barrier == D("120")
    assert result.fighters["player"].barrier_remaining == 2


def test_dispeller_removes_nonstacking_effect_and_oldest_stack_without_rng():
    state = _combat()
    enemy = state.fighters["enemy"]
    enemy.effects = [
        Effect(
            "power_up",
            "attack",
            D("0.1"),
            3,
            enemy.opportunity,
            kind="buff",
            instance_id="e1",
        ),
        Effect(
            "guard_up",
            "defense",
            D("0.1"),
            3,
            enemy.opportunity,
            kind="buff",
            stackable=True,
            stacks=3,
            stack_orders=[2, 5, 8],
            instance_id="e2",
        ),
    ]
    choices = consumable_effect_options(
        state, "consumable.dispeller.iii", target_id="enemy"
    )
    assert choices == (("e1", "effect:power_up"), ("e2", "effect:guard_up"))
    rng_before = state.rng_cursor
    removed = use_combat_consumable(
        state,
        "consumable.dispeller.iii",
        target_id="enemy",
        effect_id="e2",
        budget_limit=2,
    )
    stack = next(effect for effect in removed.fighters["enemy"].effects if effect.id == "guard_up")
    assert stack.stacks == 2
    assert stack.stack_orders == [5, 8]
    use_event = next(event for event in removed.events if event.action.startswith("consumable:"))
    assert use_event.effect_id == "guard_up"
    # Only the enemy's ordinary response draws critical RNG; Dispel adds none.
    assert removed.rng_cursor == rng_before

    single = _combat()
    single.fighters["enemy"].effects.append(
        Effect("power_up", "attack", D("0.1"), 3, 0, kind="buff", instance_id="e1")
    )
    removed = use_combat_consumable(
        single,
        "consumable.dispeller.iii",
        target_id="enemy",
        effect_id="e1",
        budget_limit=2,
    )
    assert removed.fighters["enemy"].effects == []


def test_dispeller_rejects_protected_unremovable_fixed_boss_and_nondispellable():
    state = _combat()
    enemy = state.fighters["enemy"]
    enemy.effects = [
        Effect("protected", "attack", D("0.1"), 2, 0, kind="buff", protected=True),
        Effect("unremovable", "attack", D("0.1"), 2, 0, kind="buff", removable=False),
        Effect("fixed", "attack", D("0.1"), 2, 0, kind="buff", fixed_mechanic=True),
        Effect("boss", "attack", D("0.1"), 2, 0, kind="buff", boss_protected=True),
        Effect("no_dispel", "attack", D("0.1"), 2, 0, kind="buff", dissipatable=False),
    ]
    assert consumable_effect_options(state, "consumable.dispeller.iii", target_id="enemy") == ()
    assert use_combat_consumable(
        state,
        "consumable.dispeller.iii",
        target_id="enemy",
        effect_id="e1",
        budget_limit=2,
    ) is state


def test_resguardo_orders_immunity_resistance_then_interception_and_explicit_policy():
    state = _combat()
    player = state.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 2
    effect = Effect("weaken", "attack", D("0.1"), 2, 0)

    assert not apply_effect(state, player, effect, immunity_passed=False)
    assert not apply_effect(state, player, effect, resistance_passed=False)
    assert player.ward_charges == 1
    assert apply_effect(
        state,
        player,
        Effect("special", "internal_mark", D("0.1"), 2, 0),
        application_event="special-default-false",
    )
    assert player.ward_charges == 1
    assert not apply_effect(
        state,
        player,
        Effect("special_true", "internal_mark", D("0.1"), 2, 0, resguardo_eligible=True),
        application_event="special-explicit-true",
    )
    assert player.ward_charges == 0
    assert player.effects[-1].id == "special"
    assert len(player.effects) == 1

    player.ward_charges = 1
    player.ward_remaining = 2
    assert apply_effect(
        state,
        player,
        Effect("explicit_false", "attack", D("0.1"), 2, 0, resguardo_eligible=False),
        application_event="explicit-false",
    )
    assert player.ward_charges == 1


def test_resguardo_blocks_multi_stack_application_once_then_next_event_applies():
    state = _combat()
    player = state.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 2
    batch = [
        Effect("poison", "attack", D("0.1"), 2, 0, application_event="same"),
        Effect("poison", "attack", D("0.1"), 2, 0, application_event="same"),
        Effect("poison", "attack", D("0.1"), 2, 0, application_event="same"),
    ]
    assert not apply_effect_batch(
        state, player, batch, application_event="multi-stack-event"
    )
    assert player.ward_charges == 0
    assert player.effects == []
    assert "multi-stack-event" in state.blocked_application_events
    assert apply_effect(
        state,
        player,
        Effect("poison", "attack", D("0.1"), 2, 0),
        application_event="next-event",
    )
    assert [effect.id for effect in player.effects] == ["poison"]


def test_status_stacking_renews_equal_replaces_stronger_and_keeps_stronger_value():
    state = _combat()
    player = state.fighters["player"]
    player.effects = [Effect("mark", "attack", D("0.2"), 1, 0)]

    assert apply_effect(state, player, Effect("mark", "attack", D("0.2"), 3, 0))
    assert len(player.effects) == 1
    assert player.effects[0].magnitude == D("0.2")
    assert player.effects[0].remaining == 3

    assert apply_effect(state, player, Effect("mark", "attack", D("0.3"), 2, 0))
    assert player.effects[0].magnitude == D("0.3")
    assert player.effects[0].remaining == 2

    assert not apply_effect(state, player, Effect("mark", "attack", D("0.1"), 5, 0))
    assert player.effects[0].magnitude == D("0.3")
    assert player.effects[0].remaining == 2


def test_stackable_effects_stop_at_their_declared_cap():
    state = _combat()
    player = state.fighters["player"]
    player.effects = [
        Effect(
            "poison_mark",
            "attack",
            D("0.1"),
            2,
            0,
            stackable=True,
            stacks=2,
            stack_cap=3,
            stack_orders=[1, 2],
            instance_id="e-existing",
        )
    ]

    assert apply_effect(
        state,
        player,
        Effect(
            "poison_mark",
            "attack",
            D("0.1"),
            2,
            0,
            stackable=True,
            stacks=1,
            stack_cap=3,
            stack_orders=[3],
        ),
    )
    assert player.effects[0].stacks == 3
    assert player.effects[0].stack_orders == [1, 2, 3]

    assert not apply_effect(
        state,
        player,
        Effect(
            "poison_mark",
            "attack",
            D("0.1"),
            2,
            0,
            stackable=True,
            stacks=1,
            stack_cap=3,
            stack_orders=[4],
        ),
    )
    assert player.effects[0].stacks == 3
    assert player.effects[0].stack_orders == [1, 2, 3]


def test_resguardo_does_not_spend_charge_on_status_rejected_by_stacking():
    state = _combat()
    player = state.fighters["player"]
    player.effects = [Effect("mark", "attack", D("0.5"), 3, 0)]
    player.ward_charges = 1
    player.ward_remaining = 2

    assert not apply_effect(
        state,
        player,
        Effect("mark", "attack", D("0.1"), 2, 0),
        application_event="weaker-mark",
    )
    assert player.ward_charges == 1
    assert player.effects[0].magnitude == D("0.5")

    assert not apply_effect(
        state,
        player,
        Effect("mark", "attack", D("0.6"), 2, 0),
        application_event="stronger-mark",
    )
    assert player.ward_charges == 0
    assert player.effects[0].magnitude == D("0.5")
    assert state.blocked_application_events == ["stronger-mark"]


def test_dot_burn_cap_replaces_oldest_snapshot():
    state = _combat()
    player = state.fighters["player"]

    assert apply_dot_stacks(
        state,
        player,
        kind="burn",
        snapshots=[D("100"), D("120")],
        source="enemy",
        duration=2,
        application_event="burn-1",
    )
    assert apply_dot_stacks(
        state,
        player,
        kind="burn",
        snapshots=[D("150")],
        source="enemy",
        duration=2,
        application_event="burn-2",
    )
    burn = state.dot_states["player"][0]
    assert burn.stack_cap == 2
    assert burn.stack_snapshots == [D("120"), D("150")]


def test_burn_ticks_at_fifteen_percent_per_snapshot_and_keeps_two_stack_cap():
    one = _combat()
    one.fighters["player"].stats = Stats(D("1000"), D("0"), D("0"), D("100"))
    one.fighters["player"].hp = D("500")
    one.order = ("player", "enemy")
    one.turn_index = 0
    one.dot_states["player"] = [
        DotState("burn", 1, 2, D("100"), "enemy", [D("100")], stack_cap=2)
    ]
    _end_turn(one)
    assert one.fighters["player"].hp == D("485")

    two = _combat()
    two.fighters["player"].stats = Stats(D("1000"), D("0"), D("0"), D("100"))
    two.fighters["player"].hp = D("500")
    two.order = ("player", "enemy")
    two.turn_index = 0
    two.dot_states["player"] = [
        DotState(
            "burn", 2, 2, D("100"), "enemy", [D("100"), D("120")], stack_cap=2
        )
    ]
    _end_turn(two)
    assert two.fighters["player"].hp == D("467")


def test_burn_stacks_modify_cure_and_modifier_tracks_removal_expiry_and_codec():
    one = _combat()
    one.fighters["player"].hp = D("500")
    one.dot_states["player"] = [
        DotState(
            "burn", 1, 3, D("100"), "enemy", [D("100")], instance_id="d-burn", stack_cap=2
        )
    ]
    assert effective_heal_amount(one) == D("209")
    healed_one = use_combat_consumable(one, "consumable.heal", budget_limit=2)
    event_one = next(event for event in healed_one.events if event.action.startswith("consumable:"))
    assert event_one.healed == D("209")

    two = _combat()
    two.fighters["player"].hp = D("500")
    two.dot_states["player"] = [
        DotState(
            "burn",
            2,
            3,
            D("100"),
            "enemy",
            [D("100"), D("120")],
            instance_id="d-burn",
            stack_cap=2,
        )
    ]
    assert effective_heal_amount(two) == D("198")
    healed_two = use_combat_consumable(two, "consumable.heal", budget_limit=2)
    event_two = next(event for event in healed_two.events if event.action.startswith("consumable:"))
    assert event_two.healed == D("198")

    partial = use_combat_consumable(
        two,
        "consumable.purification",
        effect_id="d-burn",
        budget_limit=2,
    )
    assert partial.dot_states["player"][0].stacks == 1
    assert effective_heal_amount(partial) == D("209")
    restored = decode(encode(partial), partial.id, partial.ruleset, partial.version)
    assert restored.dot_states["player"][0].stacks == 1
    assert effective_heal_amount(restored) == D("209")

    restored.order = ("player", "enemy")
    restored.turn_index = 0
    restored.dot_states["player"][0].remaining = 1
    _end_turn(restored)
    assert restored.dot_states.get("player", []) == []
    assert effective_heal_amount(restored) == D("220")


def test_weaker_debuff_is_not_reported_as_applied_in_combat_event():
    state = _combat()
    player = state.fighters["player"]
    player.effects.append(Effect("weakening", "attack", D("0.5"), 3, 0))
    state.enemy_actions["weakening"] = Action(
        "weakening", "Enfraquecer", D("0.5"), attack_debuff=D("0.1"), duration=2
    )

    _perform(state, "enemy", "weakening")

    assert state.events[-1].effect_id == ""


def test_resguardo_blocks_all_stacks_of_one_dot_application_without_blocking_damage():
    state = _combat()
    player = state.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 2
    assert not apply_dot_stacks(
        state,
        player,
        kind="poison",
        snapshots=[D("100"), D("150"), D("175")],
        source="enemy",
        duration=3,
        application_event="poison-batch",
    )
    assert player.ward_charges == 0
    assert state.dot_states.get("player", []) == []

    state2 = _combat()
    player = state2.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 2
    before_hp = player.hp
    state2.fighters["enemy"].stats = Stats(D("1000"), D("100"), D("0"), D("50"))
    state2.order = ("enemy", "player")
    state2.turn_index = 0
    state2.enemy_actions["bite"] = Action(
        "bite", "Mordida", D("1"), attack_debuff=D("0.1"), duration=2
    )
    _perform(state2, "enemy", "bite")
    assert player.hp < before_hp
    assert player.ward_charges == 0
    assert not any(effect.id == "bite" for effect in player.effects)
    assert state2.events[-1].action == "resguardo:block"

    state3 = _combat()
    player = state3.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 2
    before_hp = player.hp
    state3.order = ("enemy", "player")
    state3.turn_index = 0
    state3.variant = "venomous"
    state3.fighters["enemy"].stats = Stats(D("1000"), D("100"), D("0"), D("50"))
    _perform(state3, "enemy", "bite")
    assert player.hp < before_hp
    assert player.ward_charges == 0
    assert state3.dot_states.get("player", []) == []
    assert state3.events[-1].action == "resguardo:block"
    assert state3.events[-1].effect_id == "poison"


def test_consumable_options_use_stable_effect_identity_and_shared_cd2_budget():
    state = _combat()
    state.dot_states["player"] = [
        DotState("poison", 2, 3, D("100"), "enemy", [D("100"), D("120")], instance_id="d9")
    ]
    state.fighters["enemy"].effects.append(
        Effect("guard", "defense", D("0.1"), 2, 0, kind="buff", instance_id="e9")
    )
    state.fighters["player"].hp = D("700")
    options = combat_consumable_options(
        state,
        [
            "consumable.heal",
            "consumable.purification",
            "consumable.antidote.tdo.i",
            "consumable.protection.vde.ii",
            "consumable.dispeller.iii",
            "consumable.warding.iv",
            "consumable.vigor.tdo.i",
        ],
        budget_limit=2,
    )
    assert {option.item_id for option in options} == {
        "consumable.heal",
        "consumable.purification",
        "consumable.antidote.tdo.i",
        "consumable.protection.vde.ii",
        "consumable.dispeller.iii",
        "consumable.warding.iv",
    }
    assert any(
        option.effect_id == "d9" and option.item_id == "consumable.antidote.tdo.i"
        for option in options
    )
    assert any(option.effect_id == "e9" and option.target_id == "enemy" for option in options)
    used = use_combat_consumable(
        state,
        "consumable.protection.vde.ii",
        budget_limit=2,
    )
    assert combat_consumable_options(used, ["consumable.heal"], budget_limit=2) == ()


def test_dissipator_event_keeps_removal_semantics_after_effect_changes_and_codec():
    cases = (
        (False, 1, "effect", "Removido"),
        (True, 2, "stack", "1 Acúmulo Removido"),
        (True, 1, "stack", "1 Acúmulo Removido"),
    )
    for index, (stackable, stacks, expected_kind, expected_label) in enumerate(cases):
        state = _combat()
        state.enemy_actions["rally"] = Action("rally", "Brado de Guerra", D(0))
        enemy = state.fighters["enemy"]
        enemy.effects = [
            Effect(
                "rally",
                "attack",
                D("0.1"),
                3,
                enemy.opportunity,
                kind="buff",
                stackable=stackable,
                stacks=stacks,
                stack_cap=3,
                stack_orders=list(range(1, stacks + 1)),
                instance_id=f"selected-{index}",
            )
        ]

        used = use_combat_consumable(
            state,
            "consumable.dispeller.iii",
            target_id="enemy",
            effect_id=f"selected-{index}",
            budget_limit=3,
        )
        event = next(
            event for event in used.events if event.action == "consumable:consumable.dispeller.iii"
        )
        assert event.effect_removal_kind == expected_kind
        if stackable and stacks == 1:
            assert not any(effect.id == "rally" for effect in used.fighters["enemy"].effects)

        # Reconstruct as a reconnect does, then reapply the same effect ID
        # under a new instance identity. The old event must remain unchanged.
        restored = decode(encode(used), used.id, used.ruleset, used.version)
        restored.fighters["enemy"].effects.append(
            Effect(
                "rally",
                "attack",
                D("0.1"),
                3,
                restored.fighters["enemy"].opportunity,
                kind="buff",
                stackable=stackable,
                stacks=1,
                instance_id=f"reapplied-{index}",
            )
        )
        rendered = event_line(restored, event)
        assert rendered.endswith(f"· {expected_label}")
        assert rendered == event_line(used, event)


def test_legacy_dissipator_event_defaults_to_neutral_label_without_current_state_lookup():
    state = _combat()
    state.enemy_actions["rally"] = Action("rally", "Brado de Guerra", D(0))
    enemy = state.fighters["enemy"]
    enemy.effects = [
        Effect(
            "rally",
            "attack",
            D("0.1"),
            3,
            enemy.opportunity,
            kind="buff",
            instance_id="selected-rally",
        )
    ]
    used = use_combat_consumable(
        state,
        "consumable.dispeller.iii",
        target_id="enemy",
        effect_id="selected-rally",
        budget_limit=3,
    )
    payload = encode(used)
    legacy_event = next(
        item for item in payload["events"]
        if item["action"] == "consumable:consumable.dispeller.iii"
    )
    legacy_event.pop("effect_removal_kind")
    restored = decode(payload, used.id, used.ruleset, used.version)
    event = next(
        event for event in restored.events
        if event.action == "consumable:consumable.dispeller.iii"
    )
    restored.fighters["enemy"].effects.append(
        Effect("rally", "attack", D("0.1"), 3, 0, kind="buff", instance_id="again")
    )
    rendered = event_line(restored, event)
    assert event.effect_removal_kind is None
    assert rendered.endswith("· Removido")
    assert "1 Acúmulo Removido" not in rendered


def test_antidote_removes_all_selected_dot_stacks_and_purification_removes_one():
    state = _combat()
    state.dot_states["player"] = [
        DotState(
            "poison",
            3,
            3,
            D("100"),
            "enemy",
            [D("100"), D("120"), D("140")],
            instance_id="d9",
        )
    ]
    purify = use_combat_consumable(
        state,
        "consumable.purification",
        effect_id="d9",
        budget_limit=2,
    )
    purify_dot = purify.dot_states["player"][0]
    assert purify_dot.stacks == 2
    assert purify_dot.stack_snapshots == [D("120"), D("140")]

    antidote = use_combat_consumable(
        state,
        "consumable.antidote.tdo.i",
        effect_id="d9",
        budget_limit=2,
    )
    assert antidote.dot_states.get("player", []) == []


def test_budget_rejection_preserves_combat_state():
    state = _combat()
    state.consumable_uses = 1
    player = state.fighters["player"]
    player.cooldowns["consumable"] = 0
    rejected = use_combat_consumable(
        state,
        "consumable.protection.vde.ii",
        budget_limit=1,
    )
    assert rejected is state
    assert state.consumable_uses == 1
    assert player.barrier == D(0)


def test_consumable_callback_roundtrips_stable_identity_without_visual_indexes():
    activity = uuid4()
    option = CombatConsumableOption(
        "consumable.dispeller.iii", "enemy", "e9", "Dissipador · Guarda"
    )
    packed = CombatConsumableCallback.for_option(activity, 123, option).pack()
    restored = CombatConsumableCallback.unpack(packed)
    assert len(packed.encode("utf-8")) <= 64
    assert restored.activity_id == activity
    assert restored.state_version == 123
    assert restored.item_id == option.item_id
    assert restored.target_id == "enemy"
    assert restored.effect_id == "e9"


def test_resguardo_is_one_charge_refreshes_and_expires_after_two_future_turns():
    state = _combat()
    state.fighters["enemy"].hp = D("1000")
    state.fighters["enemy"].stats = Stats(D("1000"), D("10"), D("0"), D("50"))
    player = state.fighters["player"]
    player.ward_charges = 1
    player.ward_remaining = 1
    player.ward_applied_opportunity = player.opportunity - 1
    applied_at = player.opportunity
    refreshed = use_combat_consumable(
        state, "consumable.warding.iv", budget_limit=2
    )
    player = refreshed.fighters["player"]
    assert player.ward_charges == 1
    assert player.ward_remaining == 2
    assert player.ward_applied_opportunity == applied_at

    one_turn = act(refreshed, "attack")
    assert one_turn.fighters["player"].ward_charges == 1
    assert one_turn.fighters["player"].ward_remaining == 1
    two_turns = act(one_turn, "attack")
    assert two_turns.fighters["player"].ward_charges == 0
    assert two_turns.fighters["player"].ward_remaining == 0


def test_stale_effect_selection_does_not_retarget_or_consume():
    state = _combat()
    player = state.fighters["player"]
    player.effects.append(Effect("weak", "attack", D("0.1"), 2, 0, instance_id="e1"))
    options = consumable_effect_options(state, "consumable.purification")
    assert options == (("e1", "effect:weak"),)
    player.effects.clear()
    rejected = use_combat_consumable(
        state,
        "consumable.purification",
        effect_id="e1",
        budget_limit=1,
    )
    assert rejected is state
    assert state.consumable_uses == 0
