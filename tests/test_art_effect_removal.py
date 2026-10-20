import asyncio
from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from asterion.bot.combat_ui import event_line
from asterion.domain.combat import (
    Action,
    ActionEffectRemoval,
    Combat,
    DotState,
    Effect,
    Fighter,
    _remove_selected_effect_component,
    act,
    action_effect_removal_options,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import CombatRecord, GameActivity
from tests.test_road_integration import ROAD, _seed_road

D = Decimal
ZERO = D(0)
PURIFY = "class_art.synthetic.returning_rune"
DISPEL = "class_art.synthetic.ardent_purge"


def _battle(
    *,
    action: Action | None = None,
    player_effects: tuple[Effect, ...] = (),
    player_dots: tuple[DotState, ...] = (),
    enemy_effects: tuple[Effect, ...] = (),
    enemy_evasion: Decimal = ZERO,
) -> Combat:
    player = Fighter(
        "player",
        "Sentinela",
        20,
        CombatStats(D(1000), D(100), D(0), D(100), evasion=D(0)),
        hp=D(500),
        character_class="sentinela",
        takes_turn=True,
        effects=list(player_effects),
    )
    enemy = Fighter(
        "enemy",
        "Vigia",
        20,
        CombatStats(
            D(1000), D(0), D(100), D(0), evasion=enemy_evasion, block=D(0)
        ),
        hp=D(1000),
        side="enemy",
        takes_turn=False,
        effects=list(enemy_effects),
    )
    actions = {"attack": Action("attack", "Ataque Básico", D(1))}
    if action is not None:
        actions[action.id] = action
    combat = Combat(
        UUID("d2111609-92ee-4e54-a471-bd3f1bc09001"),
        CURRENT_COMBAT_RULESET,
        {"player": player, "enemy": enemy},
        actions,
        {},
        (),
        dot_states={"player": list(player_dots)} if player_dots else {},
    )
    return start_combat(combat)


def _purification_action(**kwargs) -> Action:
    return Action(
        PURIFY,
        "Runa de Retorno (teste de componente)",
        D(0),
        cooldown=4,
        target_mode="self",
        effect_removal=ActionEffectRemoval("purification", **kwargs),
    )


def test_purification_removes_one_nonstack_debuff_as_one_action():
    weak = Effect("weak", "attack", D("0.2"), 3, 0, kind="debuff", instance_id="weak-1")
    combat = _battle(action=_purification_action(), player_effects=(weak,))
    cooldown_deadline = combat.fighters["player"].opportunity + 4

    updated = act(combat, PURIFY, effect_id="weak-1")

    assert updated.version == combat.version + 1
    assert updated.fighters["player"].effects == []
    event = next(event for event in updated.events if event.action == PURIFY)
    assert event.effect_removal_component == "purification"
    assert event.effect_removal_result == "removed"
    assert event.removed_effect_ids == ("weak",)
    assert event.effect_removal_kinds == ("effect",)
    assert updated.fighters["player"].cooldowns[PURIFY] == cooldown_deadline


def test_purification_removes_single_dot_stack_and_deletes_empty_dot():
    combat = _battle(
        action=_purification_action(),
        player_dots=(
            DotState(
                "poison", 1, 3, D(40), "enemy", [D(40)], instance_id="dot-one"
            ),
        ),
    )

    updated = act(combat, PURIFY, effect_id="dot-one")

    assert updated.dot_states.get("player", []) == []
    event = next(event for event in updated.events if event.action == PURIFY)
    assert event.removed_effect_ids == ("dot:poison",)
    assert event.effect_removal_kinds == ("stack",)


def test_purification_removes_oldest_dot_snapshot_without_resetting_remaining_state():
    combat = _battle(
        player_dots=(
            DotState(
                "poison",
                3,
                4,
                D(10),
                "original-source",
                [D(10), D(20), D(30)],
                instance_id="dot-stacks",
            ),
        ),
    )
    dot = combat.dot_states["player"][0]

    removed = _remove_selected_effect_component(
        combat, "player", "dot-stacks", "purification"
    )

    assert removed == ("dot:poison", "stack")
    assert dot.stack_snapshots == [D(20), D(30)]
    assert dot.snapshot_attack == D(20)
    assert dot.stacks == 2
    assert dot.remaining == 4
    assert dot.source == "original-source"


def test_purification_removes_oldest_stack_of_a_stackable_debuff():
    debuff = Effect(
        "weakened",
        "attack",
        D("0.1"),
        3,
        0,
        kind="debuff",
        stackable=True,
        stacks=3,
        stack_orders=[4, 8, 12],
        instance_id="debuff-stacks",
    )
    combat = _battle(action=_purification_action(), player_effects=(debuff,))

    updated = act(combat, PURIFY, effect_id="debuff-stacks")

    remaining = updated.fighters["player"].effects[0]
    assert remaining.stacks == 2
    assert remaining.stack_orders == [8, 12]
    assert remaining.remaining == 2
    event = next(event for event in updated.events if event.action == PURIFY)
    assert event.effect_removal_kinds == ("stack",)


def test_explicit_selection_is_required_and_component_count_removes_exact_units():
    dot = DotState(
        "poison", 3, 4, D(10), "source", [D(10), D(20), D(30)],
        instance_id="counted-dot",
    )
    action = _purification_action(count=2)
    combat = _battle(action=action, player_dots=(dot,))

    assert act(combat, PURIFY) is combat
    assert combat.version == 0

    updated = act(
        combat,
        PURIFY,
        effect_selections=(("player", "counted-dot"), ("player", "counted-dot")),
    )
    remaining = updated.dot_states["player"][0]
    event = next(event for event in updated.events if event.action == PURIFY)

    assert remaining.stacks == 1
    assert remaining.stack_snapshots == [D(30)]
    assert event.effect_removal_kinds == ("stack", "stack")
    assert event.remaining_effect_stacks == (2, 1)


def test_dispel_removes_nonstack_buff_and_one_oldest_stack_when_stackable():
    action = Action(
        DISPEL,
        "Purga Ardente (teste de componente)",
        D("1.2"),
        cooldown=4,
        effect_removal=ActionEffectRemoval(
            "dispel", trigger="successful_direct_hit"
        ),
    )
    rally = Effect(
        "enemy.rally", "attack", D("0.1"), 3, 0, kind="buff", instance_id="rally"
    )
    combat = _battle(action=action, enemy_effects=(rally,))

    updated = act(combat, DISPEL, target_id="enemy", effect_id="rally")

    assert updated.fighters["enemy"].effects == []
    event = next(event for event in updated.events if event.action == DISPEL)
    assert event.effective_damage > 0
    assert event.effect_removal_component == "dispel"
    assert event.removed_effect_ids == ("enemy.rally",)
    assert "Dispel" in event_line(updated, event)

    stacked = Effect(
        "enemy.rally",
        "attack",
        D("0.1"),
        3,
        0,
        kind="buff",
        stackable=True,
        stacks=2,
        stack_orders=[1, 2],
        instance_id="rally-stacked",
    )
    stacked_combat = _battle(action=action, enemy_effects=(stacked,))
    stacked_updated = act(
        stacked_combat, DISPEL, target_id="enemy", effect_id="rally-stacked"
    )
    remaining = stacked_updated.fighters["enemy"].effects[0]
    assert (remaining.stacks, remaining.stack_orders) == (1, [2])
    dispel_event = next(
        event for event in stacked_updated.events if event.action == DISPEL
    )
    assert dispel_event.effect_removal_kinds == ("stack",)


def test_removal_options_exclude_expired_protected_fixed_and_class_resources():
    dispel = Action(
        DISPEL,
        "Dispel",
        D("1.2"),
        effect_removal=ActionEffectRemoval("dispel", trigger="successful_direct_hit"),
    )
    buffs = (
        Effect("ordinary", "attack", D("0.1"), 2, 0, kind="buff", instance_id="ordinary"),
        Effect("expired", "attack", D("0.1"), 0, 0, kind="buff", instance_id="expired"),
        Effect(
            "fixed", "attack", D("0.1"), 2, 0, kind="buff",
            fixed_mechanic=True, instance_id="fixed",
        ),
        Effect(
            "protected", "attack", D("0.1"), 2, 0, kind="buff",
            boss_protected=True, instance_id="protected",
        ),
        Effect(
            "locked", "attack", D("0.1"), 2, 0, kind="buff",
            unremovable=True, instance_id="locked",
        ),
        Effect(
            "no-dispel", "attack", D("0.1"), 2, 0, kind="buff",
            dissipatable=False, instance_id="no-dispel",
        ),
    )
    combat = _battle(action=dispel, enemy_effects=buffs)
    combat.fighters["player"].path_state["aim_current_target_id"] = "enemy"
    combat.fighters["player"].path_state["trama_state"] = {"stacks": 2}

    options = action_effect_removal_options(combat, DISPEL, target_id="enemy")

    assert [(option.effect_id, option.label) for option in options] == [
        ("ordinary", "effect:ordinary")
    ]
    assert combat.fighters["player"].path_state["aim_current_target_id"] == "enemy"
    assert combat.fighters["player"].path_state["trama_state"] == {"stacks": 2}


def test_selected_missing_or_ambiguous_effect_rejects_before_action_commit():
    weak = Effect("weak", "attack", D("0.1"), 2, 0, instance_id="weak")
    slow = Effect("slow", "agility", D("0.1"), 2, 0, instance_id="slow")
    combat = _battle(
        action=_purification_action(),
        player_effects=(weak, slow),
    )

    ambiguous = act(combat, PURIFY)
    stale = act(combat, PURIFY, effect_id="no-longer-present")

    assert ambiguous is combat
    assert stale is combat
    assert combat.version == 0
    assert combat.fighters["player"].cooldowns == {}


def test_no_eligible_effect_rejects_pure_removal_but_hybrid_action_still_resolves():
    pure = _battle(action=_purification_action())

    assert act(pure, PURIFY) is pure

    hybrid_action = Action(
        PURIFY,
        "Runa de Retorno (teste de componente)",
        D(0),
        heal_coefficient=D("0.7"),
        target_mode="self",
        effect_removal=ActionEffectRemoval("purification"),
    )
    hybrid = _battle(action=hybrid_action)
    hybrid.fighters["player"].hp = D(100)

    updated = act(hybrid, PURIFY)

    assert updated.fighters["player"].hp > D(100)
    event = next(event for event in updated.events if event.action == PURIFY)
    assert event.healed > 0
    assert event.effect_removal_result == "no_eligible_effect"


def test_dispel_component_runs_after_direct_damage_and_is_skipped_on_dodge():
    action = Action(
        DISPEL,
        "Purga Ardente (teste de componente)",
        D("1.2"),
        effect_removal=ActionEffectRemoval("dispel", trigger="successful_direct_hit"),
    )
    buff = Effect("rally", "attack", D("0.1"), 2, 0, kind="buff", instance_id="rally")
    hit = _battle(action=action, enemy_effects=(deepcopy(buff),))
    resolved = act(hit, DISPEL, target_id="enemy", effect_id="rally")
    event = next(event for event in resolved.events if event.action == DISPEL)
    assert event.effective_damage > 0
    assert event.removed_effect_ids == ("rally",)

    dodged = _battle(
        action=action,
        enemy_effects=(deepcopy(buff),),
        enemy_evasion=D(100),
    )
    missed = act(dodged, DISPEL, target_id="enemy", effect_id="rally")
    miss_event = next(event for event in missed.events if event.action == DISPEL)
    assert miss_event.dodged is True
    assert miss_event.effect_removal_result == "missed"
    assert missed.fighters["enemy"].effects[0].instance_id == "rally"


def test_multi_hit_and_aoe_do_not_repeat_per_action_removal():
    multi = Action(
        DISPEL,
        "Multi-hit com Dispel",
        D("0.2"),
        hit_count=3,
        effect_removal=ActionEffectRemoval(
            "dispel", trigger="successful_direct_hit", scope="per_action"
        ),
    )
    buff = Effect("rally", "attack", D("0.1"), 2, 0, kind="buff", instance_id="rally")
    combat = _battle(action=multi, enemy_effects=(buff,))
    updated = act(combat, DISPEL, target_id="enemy", effect_id="rally")
    action_events = [event for event in updated.events if event.action == DISPEL]
    assert len(action_events) == 3
    assert sum(bool(event.removed_effect_ids) for event in action_events) == 1
    assert updated.fighters["enemy"].effects == []

    aoe = Action(
        DISPEL,
        "Dispel de área (teste de escopo)",
        D(0),
        target_mode="all_opponents",
        effect_removal=ActionEffectRemoval("dispel", scope="per_action"),
    )
    area = _battle(action=aoe, enemy_effects=(deepcopy(buff),))
    area.fighters["enemy-two"] = Fighter(
        "enemy-two",
        "Vigia 2",
        20,
        CombatStats(D(1000), D(0), D(0), D(0)),
        hp=D(1000),
        side="enemy",
        takes_turn=False,
        effects=[Effect("rally", "attack", D("0.1"), 2, 0, kind="buff", instance_id="rally-2")],
    )
    area.order = ("player",)
    assert act(area, DISPEL) is area  # two eligible choices require explicit selection
    area_updated = act(area, DISPEL, effect_id="rally")
    assert area_updated.fighters["enemy"].effects == []
    assert area_updated.fighters["enemy-two"].effects[0].instance_id == "rally-2"


def test_action_component_round_trips_and_ui_reports_removal():
    effect = Effect("weak", "attack", D("0.1"), 2, 0, instance_id="weak")
    combat = _battle(action=_purification_action(), player_effects=(effect,))
    updated = act(combat, PURIFY, effect_id="weak")

    restored = decode(encode(updated), updated.id, updated.ruleset, updated.version)
    action = restored.player_actions[PURIFY]
    event = next(event for event in restored.events if event.action == PURIFY)

    assert action.effect_removal == ActionEffectRemoval("purification")
    assert event.removed_effect_ids == ("weak",)
    assert "weak" in event_line(restored, event)
    assert "Purificação" in event_line(restored, event)
    assert "Removido" in event_line(restored, event)

    stacked_combat = _battle(
        action=_purification_action(),
        player_effects=(
            Effect(
                "weak-stack",
                "attack",
                D("0.1"),
                3,
                0,
                kind="debuff",
                stackable=True,
                stacks=2,
                stack_orders=[1, 2],
                instance_id="weak-stack-instance",
            ),
        ),
    )
    stacked_updated = act(
        stacked_combat, PURIFY, effect_id="weak-stack-instance"
    )
    stacked_event = next(
        event for event in stacked_updated.events if event.action == PURIFY
    )
    assert "Restam 1" in event_line(stacked_updated, stacked_event)


async def _save_synthetic_combat(database, view, action: Action, effect: Effect) -> int:
    _, sessions = database
    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity)
            .where(GameActivity.id == view.activity_id)
            .with_for_update()
        )
        record = await session.scalar(
            select(CombatRecord)
            .where(CombatRecord.id == view.combat_id)
            .with_for_update()
        )
        assert activity is not None and record is not None
        combat = decode(
            record.snapshot,
            record.id,
            activity.ruleset_version,
            activity.state_version,
        )
        combat.player_actions[action.id] = action
        combat.fighters["player"].effects = [effect]
        combat.order = ("player", "enemy")
        combat.turn_index = 0
        combat.version += 1
        activity.state_version = combat.version
        record.snapshot = encode(combat)
        return combat.version


@pytest.mark.asyncio
async def test_postgres_action_removal_is_atomic_and_survives_reconnect(database):
    actor = 770905
    _, service = await _seed_road(database, actor=actor)
    await service.travel(actor, ROAD)
    initial = await service.start_hunt(actor)
    assert initial is not None and initial.kind == "combat"
    action = _purification_action()
    await _save_synthetic_combat(
        database,
        initial,
        action,
        Effect("weak", "attack", D("0.1"), 3, 0, instance_id="persistent-weak"),
    )
    current = await service.resume(actor)
    assert current is not None and current.kind == "combat"
    assert [
        (effect.id, effect.instance_id)
        for effect in current.combat.fighters["player"].effects
    ] == [("weak", "persistent-weak")]

    results = await asyncio.gather(
        service.action(
            actor,
            current.activity_id,
            current.combat.version,
            action=PURIFY,
            effect_id="persistent-weak",
        ),
        service.action(
            actor,
            current.activity_id,
            current.combat.version,
            action=PURIFY,
            effect_id="persistent-weak",
        ),
    )
    assert all(result is not None for result in results)
    latest = await service.resume(actor)
    assert latest is not None and latest.kind == "combat"
    removed_events = [
        event
        for event in latest.combat.events
        if event.action == PURIFY and event.removed_effect_ids
    ]
    assert len(removed_events) == 1
    removed_event = removed_events[0]
    assert removed_event.effect_removal_component == "purification"
    assert removed_event.effect_removal_result == "removed"
    assert removed_event.target == "player"
    assert removed_event.target_effect_ids == ("weak",)
    assert removed_event.removed_effect_ids == ("weak",)
    assert removed_event.effect_removal_kinds == ("effect",)

    remaining_effects = latest.combat.fighters["player"].effects
    assert all(effect.instance_id != "persistent-weak" for effect in remaining_effects)
    for effect in remaining_effects:
        application_events = [
            event
            for event in latest.combat.events
            if event.sequence > removed_event.sequence
            and event.actor != "player"
            and event.target == "player"
            and event.effect_application_event_id == effect.application_event
        ]
        assert len(application_events) == 1
        application = application_events[0]
        assert effect.application_event
        assert application.effect_id == effect.id
        assert application.actor_entity_id
        assert application.applied_effect_stat == effect.stat
        assert application.applied_effect_magnitude == effect.magnitude
        assert application.applied_effect_duration == effect.remaining
        assert application.applied_effect_kind == effect.kind
        assert application.applied_effect_removable == effect.removable
        assert effect.remaining > 0
        assert not effect.protected
        assert not effect.unremovable
        assert not effect.fixed_mechanic
        assert not effect.boss_protected

    stale = await service.action(
        actor,
        current.activity_id,
        current.combat.version,
        action=PURIFY,
        effect_id="persistent-weak",
    )
    assert stale is not None
    reconnected = await service.resume(actor)
    assert reconnected is not None and reconnected.kind == "combat"
    assert reconnected.combat.fighters["player"].effects == remaining_effects
    assert reconnected.combat.events == latest.combat.events
    assert all(
        effect.instance_id != "persistent-weak"
        for effect in reconnected.combat.fighters["player"].effects
    )
    assert sum(
        event.action == PURIFY and bool(event.removed_effect_ids)
        for event in reconnected.combat.events
    ) == 1
