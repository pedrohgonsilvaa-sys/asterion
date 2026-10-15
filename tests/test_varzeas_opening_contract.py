from decimal import Decimal
from uuid import uuid4

from asterion.application.inventory import MATERIAL_LABELS as INVENTORY_MATERIAL_LABELS
from asterion.application.road import (
    _grade_catalyst_for_level,
    _grade_fragment_for_level,
)
from asterion.application.varzeas_missions import VarzeasMissionView
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.equipment_modifications import equipment_grade
from asterion.domain.professions import MATERIAL_NAMES
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    VARIANT_POOL,
    VARZEAS_CREATURES,
    VARZEAS_DIQUES_EXPLORATION_PROFILE,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PROFILE,
    creature_for,
    hunt_pool,
    material_for,
)


def test_varzeas_global_settlement_supports_grade_iv_materials():
    assert equipment_grade(31) == equipment_grade(40) == 4
    assert _grade_catalyst_for_level(31) == "material.varzeas.catalisador_elite_iv"
    assert _grade_fragment_for_level(40) == "material.varzeas.fragmento_aprimoramento_iv"
    for material_id, label in {
        "material.varzeas.ferro_de_salmoura": "Ferro de Salmoura",
        "material.varzeas.couro_de_varzea": "Couro de Várzea",
        "material.varzeas.junco_ferruginoso": "Junco Ferruginoso",
        "material.varzeas.soro_antigo": "Soro Antigo",
        "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
        "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
    }.items():
        assert MATERIAL_NAMES[material_id] == label
        assert INVENTORY_MATERIAL_LABELS[material_id] == label


def test_varzeas_diques_hunt_pool_levels_weights_and_variants_match_source():
    assert HUNT_PROFILES[VARZEAS_DIQUES_LOCATION] == VARZEAS_DIQUES_PROFILE
    assert VARZEAS_DIQUES_PROFILE.creature_weights == (
        ("cao_salmoura", 34),
        ("garca_ferruginosa", 33),
        ("portador_rubro", 30),
        ("alfa_salmoura", 3),
    )
    assert VARZEAS_DIQUES_PROFILE.variant_chance == 10
    assert {
        creature.creature_id: (
            creature.category,
            creature.archetype,
            creature.unlock_level,
            creature.max_level,
            creature.weight,
        )
        for creature in VARZEAS_CREATURES
    } == {
        "cao_salmoura": ("common", "predator", 31, 34, 34),
        "garca_ferruginosa": ("common", "predator", 31, 34, 33),
        "portador_rubro": ("uncommon", "balanced", 31, 35, 30),
        "alfa_salmoura": ("elite", "predator", 33, 34, 3),
    }
    assert VARIANT_POOL["cao_salmoura"] == ("furious", "agile", "hemorrhagic")
    assert VARIANT_POOL["garca_ferruginosa"] == ("agile", "furious")
    assert VARIANT_POOL["portador_rubro"] == ("resistant", "furious", "agile")
    assert VARIANT_POOL["alfa_salmoura"] == ()
    assert {creature.creature_id for creature in hunt_pool(31, VARZEAS_DIQUES_PROFILE)} == {
        "cao_salmoura",
        "garca_ferruginosa",
        "portador_rubro",
    }
    assert {creature.creature_id for creature in hunt_pool(33, VARZEAS_DIQUES_PROFILE)} == {
        "cao_salmoura",
        "garca_ferruginosa",
        "portador_rubro",
        "alfa_salmoura",
    }


def test_varzeas_creature_kits_are_canonical_and_no_scripted_encounter_was_added():
    expected = {
        "cao_salmoura": ("Mordida de Várzea", "Rasgo Salgado", "Investida de Dique"),
        "garca_ferruginosa": (
            "Bicada de Água Rasa",
            "Passo Longo",
            "Perfuração Oportunista",
        ),
        "portador_rubro": (
            "Golpe de Contenção",
            "Ferramenta Quebrada",
            "Persistência Residual",
        ),
        "alfa_salmoura": (
            "Mordida do Alfa",
            "Rasgo de Salmoura",
            "Caçada de Margem",
            "Corrida pelo Dique",
        ),
    }
    for creature_id, labels in expected.items():
        creature = creature_for(creature_id)
        assert tuple(spec[1] for spec in creature.actions) == labels
    assert creature_for("portador_rubro").actions[-1][18] == 1
    assert creature_for("portador_rubro").actions[-1][30] == Decimal("0.04")
    assert creature_for("alfa_salmoura").actions[-1][8] is True
    assert creature_for("alfa_salmoura").actions[2][23] == Decimal(0)
    assert creature_for("alfa_salmoura").actions[2][24] == Decimal("0.10")
    assert creature_for("garca_ferruginosa").actions[2][25:27] == (
        Decimal("0.10"),
        Decimal("0.40"),
    )


def test_varzeas_material_pools_and_per_unit_subdraws_match_source():
    expected = {
        "cao_salmoura": (("material.varzeas.couro_de_varzea", 100),),
        "garca_ferruginosa": (
            ("material.varzeas.junco_ferruginoso", 70),
            ("material.varzeas.soro_antigo", 30),
        ),
        "portador_rubro": (
            ("material.varzeas.soro_antigo", 70),
            ("material.varzeas.ferro_de_salmoura", 30),
        ),
        "alfa_salmoura": (
            ("material.varzeas.couro_de_varzea", 80),
            ("material.varzeas.soro_antigo", 20),
        ),
    }
    assert {key: MATERIAL_POOLS[key] for key in expected} == expected

    for creature_id, pool in expected.items():
        results = [
            material_for(creature_id, f"persisted-seed:material.basic.{ordinal}")
            for ordinal in range(4)
        ]
        assert results == [
            material_for(creature_id, f"persisted-seed:material.basic.{ordinal}")
            for ordinal in range(4)
        ]
        assert set(results).issubset({material for material, _weight in pool})
    # Repeated identities are valid; units are independent draws, not a forced-unique set.
    assert material_for("cao_salmoura", "seed:material.basic.0") == material_for(
        "cao_salmoura", "seed:material.basic.1"
    )


def test_varzeas_diques_exploration_pools_and_unique_xp_match_source():
    profile = EXPLORATION_PROFILES[VARZEAS_DIQUES_LOCATION]
    assert profile == VARZEAS_DIQUES_EXPLORATION_PROFILE
    assert profile.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items()) == (
        ("great_discovery", 8),
        ("knowledge", 22),
        ("narrative", 15),
        ("combat", 25),
        ("resource", 10),
        ("atmospheric", 20),
    )
    actual = {
        result.result_id: (result.category, result.weight, result.unique, result.creature_id)
        for result in profile.results
    }
    assert actual == {
        "explore.varzeas.diques.comporta_primeiro_dique": ("great_discovery", 100, True, None),
        "explore.varzeas.diques.marcas_nivel": ("knowledge", 60, False, None),
        "explore.varzeas.diques.ferrugem_camadas": ("knowledge", 40, False, None),
        "explore.varzeas.diques.agua_sobe_sem_chuva": ("narrative", 70, True, None),
        "explore.varzeas.diques.passarela_sal": ("narrative", 30, False, None),
        "explore.varzeas.diques.combat.cao_salmoura": ("combat", 40, False, "cao_salmoura"),
        "explore.varzeas.diques.combat.garca_ferruginosa": (
            "combat", 35, False, "garca_ferruginosa"
        ),
        "explore.varzeas.diques.combat.portador_rubro": (
            "combat", 25, False, "portador_rubro"
        ),
        "explore.varzeas.diques.ferro_salmoura": ("resource", 35, False, None),
        "explore.varzeas.diques.couro_varzea": ("resource", 30, False, None),
        "explore.varzeas.diques.junco_ferruginoso": ("resource", 25, False, None),
        "explore.varzeas.diques.soro_antigo": ("resource", 10, False, None),
        "explore.varzeas.diques.comporta_travada": ("atmospheric", 34, False, None),
        "explore.varzeas.diques.sal_madeira": ("atmospheric", 33, False, None),
        "explore.varzeas.diques.agua_vermelha_ceu_cinza": ("atmospheric", 33, False, None),
    }
    assert sum(result.weight for result in profile.results if result.category == "combat") == 100
    assert sum(result.weight for result in profile.results if result.category == "resource") == 100


def test_varzeas_mission_screen_uses_versioned_player_actions():
    view = VarzeasMissionView(
        character_id=uuid4(),
        quest_id="P19",
        title="Águas de Ferro",
        kind="inspect_water",
        status="active",
        step=3,
        state_version=7,
        progress={},
        location="Diques Rubros",
        level=31,
    )
    screen = render_varzeas_mission(view)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert "varzeas:action:P19:7:inspect_water" in callbacks
    assert "world:local" in callbacks
