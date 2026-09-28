from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import DotState, _perform
from asterion.domain.road import (
    BOSQUE_EXPLORATION_PROFILE,
    BOSQUE_LOCATION,
    BOSQUE_PROFILE,
    MATERIAL_POOLS,
    create_road_combat,
    creature_for,
    hunt_pool,
    material_for,
    materialize_equipment,
    select_exploration_result,
    select_variant,
)


def test_bosque_hunt_profile_filters_before_selection_and_has_canonical_weights():
    assert BOSQUE_PROFILE.local_id == BOSQUE_LOCATION
    assert BOSQUE_PROFILE.label == "Bosque Calcinado"
    assert BOSQUE_PROFILE.variant_chance == 12
    assert BOSQUE_PROFILE.creature_weights == (
        ("cervo_escoriado", 27),
        ("carnical_fuligem", 30),
        ("aranha_cinza", 20),
        ("mariposa_brasa", 20),
        ("viuva_fuligem", 3),
    )
    assert tuple(c.creature_id for c in hunt_pool(5, BOSQUE_PROFILE)) == (
        "cervo_escoriado",
        "carnical_fuligem",
        "aranha_cinza",
    )
    assert tuple(c.creature_id for c in hunt_pool(6, BOSQUE_PROFILE)) == tuple(
        creature_id for creature_id, _ in BOSQUE_PROFILE.creature_weights
    )
    assert select_variant("widow-variant", creature_for("viuva_fuligem"), BOSQUE_PROFILE) is None


def test_bosque_explore_gates_great_discovery_and_moth_at_level_five():
    great_ids = {
        result.result_id
        for result in BOSQUE_EXPLORATION_PROFILE.results
        if result.category == "great_discovery"
    }
    assert great_ids == {
        "explore.tdo.bosque.braseiro",
        "explore.tdo.bosque.estrutura_enterrada",
    }
    assert all(
        result.min_level == 6
        for result in BOSQUE_EXPLORATION_PROFILE.results
        if result.category == "great_discovery"
    )
    for ordinal in range(120):
        key = select_exploration_result(
            f"bosque-level-five-{ordinal}",
            5,
            profile=BOSQUE_EXPLORATION_PROFILE,
        )
        assert key not in {"braseiro", "estrutura_enterrada", "mariposa_brasa"}
    combat_creatures = {
        result.creature_id
        for result in BOSQUE_EXPLORATION_PROFILE.results
        if result.category == "combat"
    }
    assert "viuva_fuligem" not in combat_creatures


def test_bosque_creatures_ai_affinities_and_material_pools():
    ghoul = creature_for("carnical_fuligem")
    moth = creature_for("mariposa_brasa")
    widow = creature_for("viuva_fuligem")
    assert (ghoul.category, ghoul.archetype, ghoul.unlock_level, ghoul.max_level) == (
        "common", "brute", 5, 8
    )
    assert ghoul.ai == ("rend", "charge", "rend", "defend")
    assert ghoul.damage_taken_modifiers == (
        ("burn", Decimal("1.10")), ("bleed", Decimal("0.90"))
    )
    assert (moth.category, moth.archetype, moth.unlock_level, moth.max_level) == (
        "uncommon", "caster", 6, 9
    )
    assert moth.ai == (
        "incandescent_touch", "ash_flash", "incandescent_touch", "defend"
    )
    assert (widow.category, widow.archetype, widow.unlock_level, widow.max_level) == (
        "elite", "controller", 6, 7
    )
    assert widow.ai == (
        "widow_sting", "soot_web", "widow_pounce", "widow_sting", "defend"
    )
    assert set(MATERIAL_POOLS["carnical_fuligem"]) == {
        ("material.tdo.ferro_de_fuligem", 50),
        ("material.tdo.residuo_ocaso", 50),
    }
    assert set(MATERIAL_POOLS["mariposa_brasa"]) == {
        ("material.tdo.erva_cinzenta", 50),
        ("material.tdo.residuo_ocaso", 50),
    }
    assert set(MATERIAL_POOLS["viuva_fuligem"]) == set(MATERIAL_POOLS["mariposa_brasa"])
    assert material_for("carnical_fuligem", "seed") in {
        "material.tdo.ferro_de_fuligem", "material.tdo.residuo_ocaso"
    }


def test_forced_rare_equipment_uses_normal_slot_budget_and_bound_flag():
    first = materialize_equipment(
        "p3:character:choice-1",
        "Raro",
        5,
        forced_name="Véu do Bosque",
        forced_slot="Cabeça",
        bound=True,
    )
    second = materialize_equipment(
        "p3:character:choice-1",
        "Raro",
        5,
        forced_name="Véu do Bosque",
        forced_slot="Cabeça",
        bound=True,
    )
    assert first == second
    assert first["item_name"] == "Véu do Bosque"
    assert first["slot"] == "Cabeça"
    assert first["rarity"] == "Raro"
    assert first["item_level"] == 5
    assert first["enhancement"] == 0
    assert first["bound"] is True
    assert first["rune"] is None and first["enchantment"] is None
    assert set(first["core"]) == {"HP", "DEF"}
    assert len(first["secondaries"]) == 1


def test_each_p3_reward_option_uses_its_normal_rare_slot_budget():
    options = (
        ("Véu do Bosque", "Cabeça", {"HP", "DEF"}),
        ("Selo do Galho Morto", "Acessório", {"HP", "ATQ", "AGI"}),
        ("Relicário da Cinza Verde", "Artefato", {"HP", "ATQ", "DEF", "AGI"}),
    )
    for index, (name, slot, expected_core) in enumerate(options):
        seed = f"p3:reward:character:{index}"
        item = materialize_equipment(
            seed,
            "Raro",
            5,
            forced_name=name,
            forced_slot=slot,
            bound=True,
        )
        assert item == materialize_equipment(
            seed,
            "Raro",
            5,
            forced_name=name,
            forced_slot=slot,
            bound=True,
        )
        assert (item["item_name"], item["slot"], item["rarity"], item["item_level"]) == (
            name,
            slot,
            "Raro",
            5,
        )
        assert set(item["core"]) == expected_core
        assert len(item["secondaries"]) == 1
        assert item["enhancement"] == 0 and item["bound"] is True
        assert item["rune"] is None and item["enchantment"] is None


def test_widow_bote_gets_ten_per_only_while_target_has_poison(monkeypatch):
    from asterion.domain import combat as combat_domain

    captured = []
    original = combat_domain.direct_damage

    def spy(*args, **kwargs):
        captured.append(kwargs["penetration"])
        return original(*args, **kwargs)

    monkeypatch.setattr(combat_domain, "direct_damage", spy)
    widow = creature_for("viuva_fuligem")
    combat = create_road_combat(
        UUID("00000000-0000-0000-0000-000000000035"),
        "Tester",
        "sentinela",
        "cinereo",
        Decimal(1000),
        widow,
        6,
        None,
        player_level=6,
        location_label="Bosque Calcinado",
    )
    clean = deepcopy(combat)
    clean.dot_states["player"] = [
        dot for dot in clean.dot_states.get("player", ()) if dot.kind != "poison"
    ]
    _perform(clean, "enemy", "widow_pounce")
    poisoned = deepcopy(combat)
    poisoned.dot_states.setdefault("player", []).append(
        DotState("poison", 1, 2, Decimal(10), "enemy")
    )
    _perform(poisoned, "enemy", "widow_pounce")
    assert captured[-1] - captured[-2] == Decimal(10)
    action = widow.actions[2]
    assert action[1] == "Bote da Viúva"
    assert action[2] == Decimal("1.30")
    assert action[9] == 3
    assert action[11] == Decimal(10)
