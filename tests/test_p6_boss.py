from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

from asterion.domain.combat import _enemy_action
from asterion.domain.road import VIGIA_PARTIDO, create_creature_combat
from asterion.infrastructure.db.combat_codec import decode, encode


def _combat():
    return create_creature_combat(
        uuid4(),
        "Viajante",
        "sentinela",
        "remanescente",
        Decimal("1000"),
        VIGIA_PARTIDO,
        10,
        None,
        player_level=10,
    )


def test_vigia_partido_uses_canonical_three_phase_kit_and_bounded_egide():
    combat = _combat()
    enemy = combat.fighters["enemy"]
    assert combat.variant is None
    assert enemy.level == 10
    assert combat.ai_priority == (
        "egide_partida",
        "marca_sentinela",
        "queda_ocaso",
        "varredura_fraturada",
        "peso_ruina",
        "golpe_vigia",
    )

    barrier = combat.enemy_actions["egide_partida"]
    assert barrier.self_barrier_coefficient == Decimal("0.90")
    assert barrier.self_barrier_duration == 2
    assert barrier.cooldown == 4
    assert barrier.max_uses_per_combat == 2
    assert barrier.skip_if_barrier_active

    prepared = combat.enemy_actions["queda_ocaso"]
    assert prepared.prepared is True
    assert prepared.coefficient == Decimal("1.85")
    assert prepared.cooldown == 5
    assert prepared.enemy_hp_fraction_at_most == Decimal("0.35")
    assert combat.enemy_actions["varredura_fraturada"].target_mode == "all_opponents"
    assert combat.enemy_actions["varredura_fraturada"].coefficient == Decimal("0.80")
    assert combat.enemy_actions["peso_ruina"].enemy_hp_fraction_below == Decimal("0.70")


def test_vigia_partido_phase_thresholds_and_barrier_skip_are_deterministic():
    combat = _combat()
    enemy = combat.fighters["enemy"]

    assert enemy.barrier > 0 and enemy.barrier_remaining == 2
    assert enemy.action_use_counts["egide_partida"] == 1

    # Even when the cooldown is ready, an active self-barrier suppresses a refresh.
    enemy.cooldowns["egide_partida"] = enemy.opportunity
    enemy.cooldowns.update(
        {
            "marca_sentinela": enemy.opportunity + 1,
            "queda_ocaso": enemy.opportunity + 1,
            "varredura_fraturada": enemy.opportunity + 1,
            "peso_ruina": enemy.opportunity + 1,
        }
    )
    assert _enemy_action(combat) == "golpe_vigia"

    enemy.barrier = Decimal(0)
    enemy.barrier_remaining = 0
    enemy.action_use_counts["egide_partida"] = 2
    enemy.cooldowns.clear()
    enemy.hp = enemy.stats.hp * Decimal("0.69")
    assert _enemy_action(combat) == "marca_sentinela"

    enemy.cooldowns["marca_sentinela"] = enemy.opportunity + 1
    assert _enemy_action(combat) == "varredura_fraturada"

    enemy.hp = enemy.stats.hp * Decimal("0.35")
    enemy.cooldowns["varredura_fraturada"] = enemy.opportunity + 1
    assert _enemy_action(combat) == "queda_ocaso"


def test_vigia_partido_phase_and_prepared_state_survive_codec_and_legacy_decode():
    combat = _combat()
    enemy = combat.fighters["enemy"]
    enemy.hp = enemy.stats.hp * Decimal("0.34")
    enemy.action_use_counts["egide_partida"] = 2
    combat.prepared_action = "queda_ocaso"
    combat.prepared_action_instance_id = "boss-phase:queda:1"
    combat.prepared_source = "enemy"
    combat.prepared_target = "player"
    combat.response_window_seen = True

    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.fighters["enemy"].hp == enemy.hp
    assert restored.fighters["enemy"].action_use_counts == {"egide_partida": 2}
    assert restored.prepared_action == "queda_ocaso"
    assert restored.prepared_action_instance_id == "boss-phase:queda:1"
    assert restored.response_window_seen
    assert restored.enemy_actions["queda_ocaso"].max_uses_per_combat is None
    assert restored.enemy_actions["queda_ocaso"].enemy_hp_fraction_at_most == Decimal("0.35")

    legacy_payload = deepcopy(encode(combat))
    legacy_payload["fighters"]["enemy"].pop("action_use_counts")
    for action in legacy_payload["enemy_actions"].values():
        action.pop("enemy_hp_fraction_below", None)
        action.pop("enemy_hp_fraction_at_most", None)
        action.pop("max_uses_per_combat", None)
    legacy = decode(legacy_payload, combat.id, combat.ruleset, combat.version)
    assert legacy.fighters["enemy"].action_use_counts == {}
    assert legacy.enemy_actions["egide_partida"].max_uses_per_combat is None
