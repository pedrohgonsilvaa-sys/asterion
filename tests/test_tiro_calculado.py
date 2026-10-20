from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.bot.character_progression_ui import _art_mechanics_lines
from asterion.bot.combat_ui import _action_resource_hints
from asterion.domain.arts import VIGIA_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, act
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
TIRO_CALCULADO = VIGIA_ART_IDS["tiro_calculado"]


def _combat(path: str | None = None):
    stats = resolve_combat_stats("vigia", 20, "remanescente")
    state = PROFILE.create(
        UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5"),
        "Vigia de Teste",
        "vigia",
        "remanescente",
        stats.hp,
    )
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    player = state.fighters["player"]
    player.selected_path = path
    player.stats = replace(
        player.stats,
        hp=D(1000),
        attack=D(100),
        defense=D(0),
        agility=D(100),
        per=D(100),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    player.hp = D(1000)
    enemy = state.fighters["enemy"]
    enemy.stats = replace(
        enemy.stats,
        hp=D(10000),
        attack=D(0),
        defense=D(0),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = D(10000)
    enemy.side = "enemy"
    state.player_actions = class_player_actions(
        "vigia", (TIRO_CALCULADO,), selected_path=path
    )
    state.enemy_actions = {"enemy.test": Action("enemy.test", "Teste", D(0))}
    state.ai_cycle = ("enemy.test",)
    return state


def _aim(target, actor, stacks: int):
    if stacks:
        target.path_state["aim_from"] = {
            actor.id: {
                "stacks": stacks,
                "remaining": 2,
                "applied_opportunity": actor.opportunity,
            }
        }


def _action_event(state):
    return next(
        event
        for event in reversed(state.events)
        if event.actor == "player" and event.action == TIRO_CALCULADO
    )


@pytest.mark.parametrize(
    ("path", "stacks", "expected_crit_bonus", "expected_after"),
    [
        (None, 0, D(0), 1),
        (None, 1, D(0), 2),
        (None, 2, D(10), 3),
        (None, 3, D(10), 3),
        ("atirador", 4, D(16), 4),
        ("rastreador", 2, D(10), 2),
    ],
)
def test_tiro_calculado_uses_target_mira_snapshot_and_keeps_marks(
    path, stacks, expected_crit_bonus, expected_after
):
    state = _combat(path)
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    _aim(target, actor, stacks)
    assert target.path_state.get("aim_from", {}).get(actor.id, {}).get(
        "stacks", 0
    ) == stacks

    updated = act(state, TIRO_CALCULADO, target_id=target.id)
    event = _action_event(updated)

    assert event.path_crit_bonus == expected_crit_bonus
    assert event.hit_count == 1
    assert updated.player_actions[TIRO_CALCULADO].coefficient == D("1.25")
    assert updated.player_actions[TIRO_CALCULADO].cooldown == 3
    aim_after = updated.fighters["enemy"].path_state.get("aim_from", {}).get(
        actor.id, {}
    )
    assert aim_after.get("stacks") == expected_after
    assert event.damage > 0


def test_tiro_calculado_bonus_uses_only_the_selected_targets_mira():
    state = _combat("rastreador")
    actor = state.fighters["player"]
    other = replace(
        state.fighters["enemy"],
        id="enemy-2",
        name="Outro alvo",
        hp=D(10000),
        path_state={},
        effects=[],
        cooldowns={},
        action_use_counts={},
    )
    state.fighters[other.id] = other
    _aim(other, actor, 2)
    assert other.path_state["aim_from"][actor.id]["stacks"] == 2
    assert not state.fighters["enemy"].path_state.get("aim_from")

    updated = act(state, TIRO_CALCULADO, target_id=state.fighters["enemy"].id)

    assert _action_event(updated).path_crit_bonus == D(0)
    assert updated.fighters["enemy-2"].path_state["aim_from"][actor.id]["stacks"] == 2
    assert updated.fighters["enemy"].path_state["aim_from"][actor.id]["stacks"] == 1


def test_tiro_calculado_snapshot_does_not_use_mira_generated_by_its_own_hit():
    state = _combat("rastreador")
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    _aim(target, actor, 1)
    assert target.path_state["aim_from"][actor.id]["stacks"] == 1

    updated = act(state, TIRO_CALCULADO, target_id=target.id)
    event = _action_event(updated)

    assert event.path_crit_bonus == D(0)
    assert updated.fighters["enemy"].path_state["aim_from"][actor.id]["stacks"] == 2


def test_tiro_calculado_conditional_bonus_changes_the_actual_critical_resolution():
    # Choose a fixed deterministic seed whose critical draw falls in the
    # 50%-to-60% interval, then compare otherwise identical real resolutions.
    for seed in range(1, 1000):
        combat_id = UUID(int=seed)
        marked = _combat()
        marked.id = combat_id
        marked.fighters["player"].stats = replace(
            marked.fighters["player"].stats, crit=D(50)
        )
        _aim(
            marked.fighters["enemy"],
            marked.fighters["player"],
            2,
        )
        marked_result = act(
            marked,
            TIRO_CALCULADO,
            target_id=marked.fighters["enemy"].id,
        )
        marked_event = _action_event(marked_result)
        if not marked_event.critical:
            continue

        unmarked = _combat()
        unmarked.id = combat_id
        unmarked.fighters["player"].stats = replace(
            unmarked.fighters["player"].stats, crit=D(50)
        )
        unmarked_result = act(
            unmarked,
            TIRO_CALCULADO,
            target_id=unmarked.fighters["enemy"].id,
        )
        unmarked_event = _action_event(unmarked_result)
        if not unmarked_event.critical:
            assert marked_event.path_crit_bonus == D(10)
            assert unmarked_event.path_crit_bonus == D(0)
            return

    pytest.fail("No deterministic critical draw distinguished the 10 p.p. bonus")


def test_tiro_calculado_conditional_definition_survives_snapshot_and_ui():
    state = _combat("atirador")
    action = state.player_actions[TIRO_CALCULADO]
    payload = encode(state)
    restored = decode(payload, state.id, state.ruleset, state.version)
    restored_action = restored.player_actions[TIRO_CALCULADO]

    assert restored_action == action
    details = "\n".join(_art_mechanics_lines(restored_action))
    assert "125% ATQ" in details
    assert "2+ Miras no alvo no início da ação" in details
    assert "+10 p.p. CRIT" in details
    assert "3 Rodadas" in details
    hints = "\n".join(
        _action_resource_hints(restored, "player", TIRO_CALCULADO, restored_action)
    )
    assert "2+ Miras no início da ação" in hints
    assert "+10 p.p. CRIT" in hints

    actor = restored.fighters["player"]
    target = restored.fighters["enemy"]
    _aim(target, actor, 2)
    resumed = decode(encode(restored), restored.id, restored.ruleset, restored.version)
    updated = act(resumed, TIRO_CALCULADO, target_id=target.id)
    assert _action_event(updated).path_crit_bonus == D(10)
    after_reconnect = decode(
        encode(updated), updated.id, updated.ruleset, updated.version
    )
    assert _action_event(after_reconnect).path_crit_bonus == D(10)
