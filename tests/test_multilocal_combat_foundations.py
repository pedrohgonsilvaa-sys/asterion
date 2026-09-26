from copy import deepcopy
from dataclasses import replace
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import (
    DotState,
    _end_turn,
    _enemy_action,
    _perform,
    allowed_actions,
)
from asterion.domain.combat_math import StatMultipliers, dot_damage
from asterion.domain.road import (
    ARCHETYPE,
    CATEGORY,
    CREATURE_CATALOG,
    CREATURES,
    ROAD_LOCATION,
    ROAD_PROFILE,
    SPIDER,
    Creature,
    create_creature_combat,
    create_road_combat,
    crowns,
    enemy_xp,
    road_enemy_stats,
    road_pool,
    select_creature,
    select_variant,
    weighted_choice,
)

D = Decimal


def _spider_combat(variant: str | None = None):
    state = create_creature_combat(
        UUID(int=72),
        "Heroa",
        "sentinela",
        "remanescente",
        D("100000"),
        SPIDER,
        3,
        variant,
        player_level=3,
    )
    state.fighters["player"].hp = D("100000")
    state.fighters["enemy"].hp = D("100000")
    state.fighters["enemy"].cooldowns = {}
    state.fighters["enemy"].opportunity = 0
    state.fighters["enemy"].last_action = None
    state.result = None
    state.events = []
    state.dot_states = {}
    state.ruleset = "legacy-test"
    return state


def test_global_category_and_archetype_multipliers_are_explicit():
    assert {key: value.values() for key, value in CATEGORY.items()} == {
        "common": (D("0.70"), D("0.82"), D("0.90"), D("0.95")),
        "uncommon": (D("0.85"), D("0.90"), D("0.95"), D("1.00")),
        "elite": (D("1.50"), D("1.05"), D("1.05"), D("1.02")),
        "boss": (D("2.20"), D("1.10"), D("1.10"), D("1.00")),
    }
    assert {key: value.values() for key, value in ARCHETYPE.items()} == {
        "balanced": (D(1), D(1), D(1), D(1)),
        "brute": (D("1.15"), D("1.12"), D("0.95"), D("0.85")),
        "predator": (D("0.90"), D("1.10"), D("0.90"), D("1.20")),
        "armored": (D("1.10"), D("0.88"), D("1.20"), D("0.85")),
        "caster": (D("0.85"), D("1.15"), D("0.88"), D("1.00")),
        "controller": (D("0.95"), D("0.90"), D("1.00"), D("1.10")),
    }
    assert isinstance(CATEGORY["uncommon"], StatMultipliers)
    with pytest.raises(KeyError):
        road_enemy_stats(
            Creature("bad", "Bad", "mystery", "controller", 1, 1, 1, (), ()),
            1,
        )


def test_enemy_xp_and_crowns_use_explicit_category_multipliers():
    assert [enemy_xp(1, category) for category in ("common", "uncommon", "elite", "boss")] == [
        240,
        320,
        660,
        1440,
    ]
    assert [enemy_xp(3, category) for category in ("common", "uncommon", "elite", "boss")] == [
        280,
        370,
        760,
        1670,
    ]
    assert enemy_xp(3, "uncommon", player_level=6) < enemy_xp(3, "uncommon")
    assert [crowns(1, category) for category in ("common", "uncommon", "elite", "boss")] == [
        10,
        10,
        30,
        70,
    ]
    assert [crowns(3, category) for category in ("common", "uncommon", "elite", "boss")] == [
        10,
        10,
        40,
        90,
    ]
    with pytest.raises(KeyError):
        enemy_xp(1, "unclassified")
    with pytest.raises(KeyError):
        crowns(1, "unclassified")


def test_road_profile_keeps_its_roster_weights_unlocks_and_seed_results():
    assert ROAD_PROFILE.local_id == ROAD_LOCATION
    assert ROAD_PROFILE.creature_weights == (
        ("dog_cinereo", 34),
        ("corvo_fuligem", 33),
        ("peregrino_calcinado", 30),
        ("alfa_cinereo", 3),
    )
    assert ROAD_PROFILE.variant_chance == 8
    assert [creature.creature_id for creature in road_pool(1)] == [
        "dog_cinereo",
        "corvo_fuligem",
    ]
    assert [creature.creature_id for creature in road_pool(2)] == [
        "dog_cinereo",
        "corvo_fuligem",
        "peregrino_calcinado",
    ]
    assert [creature.creature_id for creature in road_pool(3)] == [
        creature.creature_id for creature in CREATURES
    ]
    assert SPIDER in CREATURE_CATALOG
    assert SPIDER not in road_pool(60)
    for seed in ("stable-seed", "road-vector-1", "road-vector-2"):
        expected = weighted_choice(
            seed,
            tuple((creature.creature_id, creature.weight) for creature in road_pool(3)),
        )
        assert select_creature(seed, 3).creature_id == expected
        assert select_creature(seed, 3) == select_creature(seed, 3, profile=ROAD_PROFILE)
        assert select_variant(seed, CREATURES[0]) == select_variant(
            seed, CREATURES[0], profile=ROAD_PROFILE
        )


def test_spider_domain_definition_and_priority_use_canonical_action_metadata():
    state = _spider_combat()
    toxic = state.enemy_actions["toxic_bite"]
    bite = state.enemy_actions["bite"]
    enemy = state.fighters["enemy"]
    assert (SPIDER.creature_id, SPIDER.category, SPIDER.archetype) == (
        "aranha_cinza",
        "uncommon",
        "controller",
    )
    assert (SPIDER.unlock_level, SPIDER.max_level) == (3, 6)
    assert (toxic.coefficient, toxic.native_dot_kind, toxic.native_dot_stacks) == (
        D("0.80"),
        "poison",
        1,
    )
    assert toxic.cooldown == 2
    assert bite.coefficient == D("0.95")
    assert state.ai_priority == ("toxic_bite", "bite")
    assert enemy.damage_taken_modifiers == {"burn": D("1.10"), "poison": D("0.90")}
    assert _enemy_action(state) == "toxic_bite"
    enemy.cooldowns["toxic_bite"] = enemy.opportunity + 1
    assert _enemy_action(state) == "bite"


def test_spider_cd2_is_unavailable_next_opportunity_then_ready():
    state = _spider_combat()
    enemy = state.fighters["enemy"]
    enemy.opportunity = 1
    _perform(state, "enemy", "toxic_bite")
    assert enemy.cooldowns["toxic_bite"] == 3
    enemy.opportunity = 2
    assert _enemy_action(state) == "bite"
    enemy.opportunity = 3
    assert _enemy_action(state) == "toxic_bite"


def test_native_poison_stacks_once_even_with_venomous_variant_and_replaces_oldest():
    state = _spider_combat("venomous")
    state.dot_states["player"] = [
        DotState("poison", 3, 2, D(100), "enemy", [D(100), D(200), D(300)])
    ]
    _perform(state, "enemy", "toxic_bite")
    poison = state.dot_states["player"][0]
    assert poison.stacks == 3
    assert poison.remaining == 3
    assert poison.stack_snapshots == [D(200), D(300), state.fighters["enemy"].stat("attack")]
    assert poison.stack_snapshots.count(state.fighters["enemy"].stat("attack")) == 1


def test_native_dot_is_not_applied_when_direct_action_is_dodged():
    from asterion.domain.combat_math import CURRENT_COMBAT_RULESET

    state = _spider_combat()
    state.ruleset = CURRENT_COMBAT_RULESET
    state.fighters["player"].stats = replace(
        state.fighters["player"].stats, evasion=D(100)
    )
    _perform(state, "enemy", "toxic_bite")
    assert not state.dot_states.get("player")
    assert state.events[-1].dodged


@pytest.mark.parametrize(
    ("kind", "coefficient", "modifier"),
    (("poison", D("0.12"), D("0.90")), ("burn", D("0.15"), D("1.10"))),
)
def test_spider_damage_affinity_changes_only_corresponding_dot_tick(kind, coefficient, modifier):
    state = _spider_combat()
    spider = state.fighters["enemy"]
    source = state.fighters["player"]
    spider.hp = D("100000")
    state.order = ("enemy", "player")
    state.turn_index = 0
    state.dot_states["enemy"] = [DotState(kind, 1, 3, D(100), "player", [D(100)])]
    expected_normal = dot_damage(
        [D(100)],
        coefficient,
        spider.stat("defense"),
        source.level,
        penetration=source.stat("per"),
    )
    expected_modified = max(
        1,
        int((D(expected_normal) * modifier).to_integral_value(rounding=ROUND_FLOOR)),
    )
    _end_turn(state)
    assert spider.hp == D("100000") - expected_modified
    assert state.dot_states["enemy"][0].stacks == 1
    assert state.dot_states["enemy"][0].remaining == 2


def test_native_dot_metadata_codec_roundtrip_preserves_exact_decimals():
    from asterion.infrastructure.db.combat_codec import decode, encode

    state = _spider_combat()
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored == state
    assert restored.enemy_actions["toxic_bite"].native_dot_kind == "poison"
    assert restored.enemy_actions["toxic_bite"].cooldown == 2
    assert restored.ai_priority == ("toxic_bite", "bite")
    assert restored.fighters["enemy"].damage_taken_modifiers["poison"] == D("0.90")


def test_legacy_alfa_snapshot_without_metadata_keeps_rend_and_leap_behavior():
    from asterion.infrastructure.db.combat_codec import decode, encode

    old = create_road_combat(
        UUID(int=73), "Heroa", "sentinela", "remanescente", D(10000), CREATURES[3], 3, None
    )
    payload = encode(old)
    payload.pop("ai_priority", None)
    for actions in (payload["enemy_actions"], payload["player_actions"]):
        for action in actions.values():
            for key in ("native_dot_kind", "native_dot_stacks", "prepared", "cooldown"):
                action.pop(key, None)
    for fighter in payload["fighters"].values():
        fighter.pop("damage_taken_modifiers", None)

    rend_state = decode(deepcopy(payload), old.id, old.ruleset, old.version)
    rend_state.ruleset = "legacy-test"
    rend_state.dot_states = {}
    rend_state.events = []
    _perform(rend_state, "enemy", "rend")
    assert rend_state.dot_states["player"][0].kind == "bleed"
    assert rend_state.dot_states["player"][0].stacks == 1

    leap_state = decode(deepcopy(payload), old.id, old.ruleset, old.version)
    leap_state.ruleset = "legacy-test"
    leap_state.prepared_action = None
    leap_state.resolving_prepared = False
    leap_state.response_window_seen = False
    _perform(leap_state, "enemy", "leap")
    assert leap_state.prepared_action == "leap"
    assert leap_state.fighters["enemy"].cooldowns["leap"] == (
        leap_state.fighters["enemy"].opportunity + 4
    )
    assert leap_state.ai_priority == ()
    assert leap_state.fighters["enemy"].damage_taken_modifiers == {}


def test_alfa_new_actions_declare_metadata_without_changing_old_cooldowns():
    state = create_road_combat(
        UUID(int=74), "Heroa", "sentinela", "remanescente", D(10000), CREATURES[3], 3, None
    )
    assert state.enemy_actions["rend"].native_dot_kind == "bleed"
    assert state.enemy_actions["rend"].native_dot_stacks == 1
    assert state.enemy_actions["leap"].prepared is True
    assert state.enemy_actions["leap"].cooldown is None


def test_player_actions_without_native_dot_metadata_remain_unchanged():
    state = _spider_combat()
    state.order = ("player", "enemy")
    state.turn_index = 0
    state.fighters["player"].opportunity += 1
    assert "attack" in allowed_actions(state)
