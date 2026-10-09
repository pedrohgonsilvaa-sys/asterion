from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.combat import act, action_target_ids, active_player_key
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    PlayerCombatantSpec,
    create_player_versus_player_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _roster(side: str, size: int, *, level: int = 5):
    return tuple(
        PlayerCombatantSpec(
            fighter_key=f"{side}{index}",
            character_id=f"{side}-character-{index}",
            name=f"{side.title()}{index}",
            character_class="sentinela",
            race="remanescente",
            level=level,
            hp=D(10000),
            equipment_configuration=EquipmentConfigurationSnapshot(0),
            active_art_ids=(),
        )
        for index in range(1, size + 1)
    )


@pytest.mark.parametrize("roster_size", (1, 2, 3, 4))
def test_pvp_combat_uses_real_individual_fighters_and_manual_turns(roster_size):
    combat = create_player_versus_player_combat(
        uuid4(), _roster("l", roster_size), _roster("r", roster_size)
    )

    assert combat.party_mode is True
    assert combat.manual_sides == ("player", "enemy")
    assert sum(fighter.side == "player" for fighter in combat.fighters.values()) == roster_size
    assert sum(fighter.side == "enemy" for fighter in combat.fighters.values()) == roster_size
    assert len(combat.player_configuration_snapshots) == roster_size * 2

    # Initiative can place either side first; both sides must wait for a player action.
    for _ in range(2):
        actor_key = active_player_key(combat)
        assert actor_key is not None
        actor = combat.fighters[actor_key]
        target_ids = action_target_ids(combat, "attack", actor_key=actor_key)
        assert target_ids
        target = next(
            fighter
            for fighter in combat.fighters.values()
            if fighter.id == target_ids[0]
        )
        assert target.side != actor.side
        before = combat.version
        combat = act(combat, "attack", target_id=target.id, actor_key=actor_key)
        assert combat.version == before + 1
        assert combat.events[-1].actor == actor_key
        assert active_player_key(combat) is not None


def test_pvp_combat_rejects_unequal_or_duplicate_sides():
    with pytest.raises(ValueError, match="equal size"):
        create_player_versus_player_combat(
            uuid4(), _roster("l", 1), _roster("r", 2)
        )

    duplicate = PlayerCombatantSpec(
        "same",
        "same-character",
        "Same",
        "sentinela",
        "remanescente",
        5,
        D(100),
        EquipmentConfigurationSnapshot(0),
        (),
    )
    with pytest.raises(ValueError, match="both sides"):
        create_player_versus_player_combat(uuid4(), (duplicate,), (duplicate,))


def test_pvp_manual_sides_survive_snapshot_reconnect():
    combat = create_player_versus_player_combat(
        uuid4(), _roster("l", 2), _roster("r", 2)
    )
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)

    assert restored.manual_sides == ("player", "enemy")
    assert restored.order == combat.order
    assert active_player_key(restored) == active_player_key(combat)
    assert set(restored.player_actions_by_fighter) == set(combat.player_actions_by_fighter)
