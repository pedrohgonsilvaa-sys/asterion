from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Action,
    Combat,
    Fighter,
    act,
    action_target_ids,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("c0a8e780-2c1e-4d7e-a356-a25a1da39f11")


def fighter(
    fighter_id: str,
    *,
    hp: str = "500",
    attack: str = "100",
    defense: str = "20",
    agility: str = "10",
    side: str = "",
    takes_turn: bool = True,
    defeat_on_zero: bool | None = None,
    required_for_victory: bool | None = None,
    character_class: str = "",
) -> Fighter:
    stats = CombatStats(D(hp), D(attack), D(defense), D(agility), crit=D(0))
    return Fighter(
        fighter_id,
        fighter_id,
        10,
        stats,
        D(hp),
        character_class=character_class,
        side=side,
        takes_turn=takes_turn,
        defeat_on_zero=defeat_on_zero,
        required_for_victory=required_for_victory,
    )


def multi_battle(*, player_actions: dict[str, Action] | None = None) -> Combat:
    return Combat(
        COMBAT_ID,
        CURRENT_COMBAT_RULESET,
        {
            "player": fighter("player", agility="30"),
            "enemy": fighter("trial.enemy", hp="900", agility="10"),
            "manifest": fighter(
                "trial.manifestation",
                hp="300",
                agility="50",
                side="enemy",
                takes_turn=False,
                required_for_victory=False,
            ),
        },
        player_actions
        or {
            "attack": Action("attack", "Ataque", D("1.0")),
        },
        {},
        (),
    )


def test_passive_manifestation_has_hp_and_targetability_but_no_turn():
    state = start_combat(multi_battle())
    assert "manifest" not in state.order
    assert action_target_ids(state, "attack") == (
        "trial.enemy",
        "trial.manifestation",
    )

    # With more than one valid single target, player intent must name the target.
    assert act(state, "attack") is state

    enemy_hp = state.fighters["enemy"].hp
    manifest_hp = state.fighters["manifest"].hp
    updated = act(state, "attack", target_id="trial.manifestation")
    assert updated is not state
    assert updated.fighters["enemy"].hp == enemy_hp
    assert updated.fighters["manifest"].hp < manifest_hp
    player_events = [e for e in updated.events if e.actor == "player"]
    assert player_events[0].target == "trial.manifestation"
    assert updated.result is None


def test_aoe_freezes_target_set_and_commits_cooldown_and_retaliation_once():
    action = Action(
        "ruptura",
        "Ruptura",
        D("0.80"),
        cooldown=3,
        target_mode="all_opponents",
    )
    state = multi_battle(player_actions={"ruptura": action})
    player = state.fighters["player"]
    player.character_class = "sentinela"
    player.retaliation_charges = 1
    player.retaliation_remaining = 1
    player.retaliation_activation_id = "ret-aoe"
    player.retaliation_source_type = "defender"
    player.retaliation_source_event_id = "source-event"
    player.retaliation_source_actor_id = "trial.enemy"
    state = start_combat(state)

    updated = act(state, "ruptura")
    events = [e for e in updated.events if e.actor == "player" and e.action == "ruptura"]
    assert len(events) == 2
    assert {e.target for e in events} == {"trial.enemy", "trial.manifestation"}
    assert len({e.action_instance_id for e in events}) == 1
    assert events[0].action_instance_id
    assert updated.fighters["player"].cooldowns["ruptura"] == 4
    assert updated.fighters["player"].retaliation_charges == 0
    retaliation_events = [
        e.retaliation_event
        for e in updated.mechanic_events
        if e.retaliation_activation_id == "ret-aoe"
    ]
    assert retaliation_events.count("consumed") == 1
    assert retaliation_events.count("action_resolved") == 1


def test_allied_echo_accepts_targeted_heal_and_barrier_without_getting_a_turn():
    heal = Action(
        "renovacao",
        "Renovação",
        D(0),
        cooldown=2,
        target_mode="ally",
        heal_coefficient=D("0.85"),
    )
    barrier = Action(
        "egide",
        "Égide Solar",
        D(0),
        cooldown=3,
        target_mode="ally",
        target_barrier_coefficient=D("0.90"),
        target_barrier_duration=2,
    )
    state = Combat(
        COMBAT_ID,
        CURRENT_COMBAT_RULESET,
        {
            "player": fighter("player", attack="100", agility="30"),
            "ally": fighter(
                "trial.ally_echo",
                hp="480",
                defense="80",
                agility="99",
                side="player",
                takes_turn=False,
                defeat_on_zero=True,
                required_for_victory=False,
            ),
            "enemy": fighter("trial.enemy", hp="900", agility="10"),
        },
        {"renovacao": heal, "egide": barrier},
        {},
        (),
    )
    state.fighters["ally"].hp = D("200")
    state = start_combat(state)
    assert "ally" not in state.order
    assert set(action_target_ids(state, "renovacao")) == {"player", "trial.ally_echo"}
    assert act(state, "renovacao") is state

    healed = act(state, "renovacao", target_id="trial.ally_echo")
    assert healed.fighters["ally"].hp == D("285")
    heal_event = next(e for e in healed.events if e.action == "renovacao")
    assert heal_event.target == "trial.ally_echo"
    assert heal_event.healed == D("85")

    shielded = act(healed, "egide", target_id="trial.ally_echo")
    assert shielded.fighters["ally"].barrier == D("90")
    assert shielded.fighters["ally"].barrier_remaining == 2
    barrier_event = next(e for e in shielded.events if e.action == "egide")
    assert barrier_event.target == "trial.ally_echo"
    assert barrier_event.barrier_value == D("90")


def test_required_allied_echo_zero_hp_causes_defeat_from_enemy_aoe():
    enemy_blast = Action(
        "blast",
        "Pressão Simultânea",
        D("5.0"),
        target_mode="all_opponents",
    )
    state = Combat(
        COMBAT_ID,
        CURRENT_COMBAT_RULESET,
        {
            "player": fighter("player", hp="1000", defense="100", agility="10"),
            "ally": fighter(
                "trial.ally_echo",
                hp="480",
                defense="80",
                agility="5",
                side="player",
                takes_turn=False,
                defeat_on_zero=True,
                required_for_victory=False,
            ),
            "enemy": fighter("trial.enemy", attack="1000", agility="50"),
        },
        {"attack": Action("attack", "Ataque", D("1.0"))},
        {"blast": enemy_blast},
        ("blast",),
    )
    state.fighters["ally"].hp = D(1)
    started = start_combat(state)
    assert started.result == "defeat"
    assert started.fighters["ally"].hp == 0
    blast_events = [e for e in started.events if e.action == "blast"]
    assert {e.target for e in blast_events} == {"player", "trial.ally_echo"}


def test_optional_manifestation_does_not_block_victory_when_required_enemy_falls():
    state = start_combat(multi_battle())
    state.fighters["enemy"].hp = D(1)
    updated = act(state, "attack", target_id="trial.enemy")
    assert updated.result == "victory"
    assert updated.fighters["enemy"].hp == 0
    assert updated.fighters["manifest"].hp > 0


def test_multi_target_fields_survive_combat_codec_roundtrip():
    state = multi_battle(
        player_actions={
            "support": Action(
                "support",
                "Support",
                D(0),
                target_mode="ally",
                heal_coefficient=D("0.85"),
                target_barrier_coefficient=D("0.90"),
                target_barrier_duration=2,
            )
        }
    )
    state.fighters["manifest"].defeat_on_zero = False
    state = start_combat(state)
    restored = decode(encode(state), state.id, state.ruleset, state.version)

    manifest = restored.fighters["manifest"]
    assert manifest.side == "enemy"
    assert manifest.takes_turn is False
    assert manifest.required_for_victory is False
    assert manifest.defeat_on_zero is False
    support = restored.player_actions["support"]
    assert support.target_mode == "ally"
    assert support.heal_coefficient == D("0.85")
    assert support.target_barrier_coefficient == D("0.90")
    assert support.target_barrier_duration == 2


def test_multiple_active_enemies_each_receive_their_own_turn_and_gate_victory():
    state = Combat(
        COMBAT_ID,
        CURRENT_COMBAT_RULESET,
        {
            "player": fighter("player", agility="30"),
            "enemy": fighter("trial.enemy.one", hp="500", agility="20"),
            "enemy_two": fighter(
                "trial.enemy.two",
                hp="500",
                agility="10",
                side="enemy",
            ),
        },
        {"attack": Action("attack", "Ataque", D("1.0"))},
        {},
        (),
    )
    state = start_combat(state)
    assert state.order == ("player", "enemy", "enemy_two")
    assert act(state, "attack") is state

    state.fighters["enemy"].hp = D(1)
    updated = act(state, "attack", target_id="trial.enemy.one")
    assert updated.result is None
    assert updated.fighters["enemy"].hp == 0
    assert updated.fighters["enemy_two"].hp > 0
    assert [event.actor for event in updated.events] == [
        "player",
        "enemy_two",
    ]
    assert updated.fighters["enemy_two"].opportunity == 1


def test_trial_projection_keeps_shared_action_instance_for_aoe_events():
    from asterion.domain.class_trials import trial_event_from_combat_event

    state = start_combat(
        multi_battle(
            player_actions={
                "ruptura": Action(
                    "ruptura",
                    "Ruptura",
                    D("0.80"),
                    target_mode="all_opponents",
                )
            }
        )
    )
    updated = act(state, "ruptura")
    combat_events = [
        event
        for event in updated.events
        if event.actor == "player" and event.action == "ruptura"
    ]
    projected = [trial_event_from_combat_event(updated, event) for event in combat_events]
    assert len(projected) == 2
    assert projected[0].action_instance_id
    assert projected[0].action_instance_id == projected[1].action_instance_id
