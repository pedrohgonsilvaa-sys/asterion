from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import _perform
from asterion.domain.road import (
    MATERIAL_POOLS,
    RUINS_EXPLORATION_PROFILE,
    RUINS_LOCATION,
    RUINS_PROFILE,
    create_road_combat,
    creature_for,
    hunt_pool,
    select_exploration_result,
)
from asterion.infrastructure.db.combat_codec import decode, encode


def test_ruins_hunt_profile_filters_custodio_before_level_nine():
    assert RUINS_PROFILE.local_id == RUINS_LOCATION
    assert RUINS_PROFILE.label == "Ruínas do Vigia"
    assert RUINS_PROFILE.variant_chance == 15
    assert RUINS_PROFILE.creature_weights == (
        ("carnical_fuligem", 25),
        ("vigia_rachado", 32),
        ("mariposa_brasa", 20),
        ("custodio_sem_rosto", 20),
        ("custodio_poente", 3),
    )
    assert "custodio_poente" not in {item.creature_id for item in hunt_pool(8, RUINS_PROFILE)}
    assert "custodio_poente" in {item.creature_id for item in hunt_pool(9, RUINS_PROFILE)}


def test_ruins_exploration_keeps_reference_level_distinct_from_minimum_level():
    great = [
        item for item in RUINS_EXPLORATION_PROFILE.results if item.category == "great_discovery"
    ]
    assert {item.result_id for item in great} == {
        "explore.tdo.ruinas.braseiro",
        "explore.tdo.ruinas.galerias",
    }
    assert next(item for item in great if item.key == "braseiro_poente").min_level == 1
    assert next(item for item in great if item.key == "galerias_vigia").min_level == 8
    assert all(
        select_exploration_result(f"ruins-eight-{index}", 8, profile=RUINS_EXPLORATION_PROFILE)
        in {"braseiro_poente", "galerias_vigia", "estruturas_guarda", "ocupacao_posterior",
            "marcas_patrulha", "passos_ninguem", "pedra_vigilia", "vigia_rachado",
            "custodio_sem_rosto", "carnical_fuligem", "mariposa_brasa", "ferro", "residuo",
            "erva", "couro", "porta_fechada", "estatua", "eco_pedra"}
        for index in range(80)
    )


def test_ruins_creatures_have_canonical_catalog_and_material_pools():
    vigia = creature_for("vigia_rachado")
    faceless = creature_for("custodio_sem_rosto")
    sunset = creature_for("custodio_poente")
    assert (vigia.category, vigia.archetype, vigia.unlock_level, vigia.max_level) == (
        "common", "armored", 7, 10
    )
    assert (faceless.category, faceless.archetype, faceless.unlock_level, faceless.max_level) == (
        "uncommon", "controller", 8, 10
    )
    assert (sunset.category, sunset.archetype, sunset.unlock_level, sunset.max_level) == (
        "elite", "armored", 9, 10
    )
    iron_residue = {
        ("material.tdo.ferro_de_fuligem", 50),
        ("material.tdo.residuo_ocaso", 50),
    }
    assert set(MATERIAL_POOLS["vigia_rachado"]) == iron_residue
    assert set(MATERIAL_POOLS["custodio_sem_rosto"]) == iron_residue
    assert set(MATERIAL_POOLS["custodio_poente"]) == iron_residue
    assert sunset.actions[1][12:15] == (Decimal("0.90"), 2, True)


def test_enemy_barrier_action_uses_floor_two_opportunities_and_codec_defaults():
    creature = creature_for("vigia_rachado")
    battle = create_road_combat(
        UUID("00000000-0000-0000-0000-000000000036"),
        "Tester", "sentinela", "cinereo", Decimal(1000), creature, 7, None,
        player_level=7, location_label="Ruínas do Vigia",
    )
    battle.fighters["enemy"].stats = battle.fighters["enemy"].stats.__class__(
        hp=Decimal(100), attack=Decimal(101), defense=Decimal(20), agility=Decimal(1)
    )
    _perform(battle, "enemy", "guarda_rachada")
    guard = battle.fighters["enemy"]
    assert guard.barrier == Decimal(70)
    assert guard.barrier_remaining == 2
    assert battle.events[-1].barrier_value == Decimal(70)
    snapshot = encode(battle)
    restored = decode(snapshot, battle.id, battle.ruleset, battle.version)
    assert restored.fighters["enemy"].barrier_source == "enemy:guarda_rachada"
    assert encode(restored) == snapshot

    legacy = deepcopy(snapshot)
    for action in legacy["enemy_actions"].values():
        action.pop("self_barrier_coefficient", None)
        action.pop("self_barrier_duration", None)
        action.pop("skip_if_barrier_active", None)
    legacy_roundtrip = decode(legacy, battle.id, battle.ruleset, battle.version)
    assert all(
        action.self_barrier_coefficient == 0
        for action in legacy_roundtrip.enemy_actions.values()
    )
