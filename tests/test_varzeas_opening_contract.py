from decimal import Decimal
from uuid import uuid4

from asterion.application.bestiary import VARZEAS_DISTINCTIVE_ELITE_MASTERY
from asterion.application.inventory import MATERIAL_LABELS as INVENTORY_MATERIAL_LABELS
from asterion.application.knowledge_catalog import (
    CODEX_ENTRIES,
    CODEX_FRAGMENTS,
    VARZEAS_REGION_LABEL,
)
from asterion.application.road import (
    VARZEAS_EXPLORATION_UNIQUE_XP,
    _grade_catalyst_for_level,
    _grade_fragment_for_level,
)
from asterion.application.varzeas_missions import P20_ID, S20_ID, VarzeasMissionView
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.equipment_modifications import equipment_grade
from asterion.domain.professions import MATERIAL_NAMES
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    VARIANT_POOL,
    VARZEAS_BREJOS_EXPLORATION_PROFILE,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_BREJOS_PROFILE,
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


def test_varzeas_region_label_uses_canonical_global_icon():
    assert VARZEAS_REGION_LABEL == "🥀 Várzeas Carmesins · Nv. 31–40"


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


def test_varzeas_creature_kits_are_canonical():
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
        "aranha_junco": (
            "Picada de Junco",
            "Fio entre Hastes",
            "Salto de Margem",
        ),
        "cervo_ferrugem": (
            "Chifrada Ferruginosa",
            "Pisoteio de Brejo",
            "Carga de Junco",
        ),
        "viuva_rubra": (
            "Picada Rubra",
            "Teia de Junco",
            "Toxina Concentrada",
            "Salto sobre a Água",
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
    spider = creature_for("aranha_junco")
    assert (spider.category, spider.archetype, spider.unlock_level, spider.max_level) == (
        "common", "controller", 33, 36
    )
    assert spider.actions[0][2] == Decimal("0.80")
    assert spider.actions[0][6:10] == ("poison", 1, False, 2)
    assert spider.actions[1][2] == Decimal("0.75")
    assert spider.actions[1][4:6] == (Decimal("0.12"), 2)
    assert spider.actions[1][9:11] == (3, "agility")
    deer = creature_for("cervo_ferrugem")
    assert (deer.category, deer.archetype, deer.unlock_level, deer.max_level) == (
        "common", "brute", 33, 37
    )
    assert deer.actions[0][2] == Decimal("1.05")
    assert deer.actions[1][2] == Decimal("1.25") and deer.actions[1][9] == 3
    assert deer.actions[2][2] == Decimal("1.75")
    assert deer.actions[2][8:10] == (True, 4)
    widow = creature_for("viuva_rubra")
    assert (widow.category, widow.archetype, widow.unlock_level, widow.max_level) == (
        "elite", "controller", 35, 37
    )
    assert widow.actions[0][2] == Decimal("0.80")
    assert widow.actions[0][6:10] == ("poison", 1, False, 2)
    assert widow.actions[1][2] == Decimal("0.75")
    assert widow.actions[1][4:6] == (Decimal("0.15"), 2)
    assert widow.actions[2][2] == Decimal("0.95")
    assert widow.actions[2][7] == 0 and widow.actions[2][27] == 1
    assert widow.actions[3][2] == Decimal("1.60")
    assert widow.actions[3][8:10] == (True, 4)
    assert VARIANT_POOL["aranha_junco"] == ("venomous", "agile")
    assert VARIANT_POOL["cervo_ferrugem"] == ("furious", "resistant")
    assert VARIANT_POOL["viuva_rubra"] == ()
    assert VARZEAS_DISTINCTIVE_ELITE_MASTERY["viuva_rubra"] == {
        "first_victory",
        "mechanic:poison",
        "action:teia_junco",
        "action:salto_agua",
    }


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


def test_varzeas_brejos_hunt_pool_levels_weights_and_variants_match_source():
    assert HUNT_PROFILES[VARZEAS_BREJOS_LOCATION] == VARZEAS_BREJOS_PROFILE
    assert VARZEAS_BREJOS_PROFILE.creature_weights == (
        ("cao_salmoura", 18),
        ("garca_ferruginosa", 17),
        ("portador_rubro", 15),
        ("aranha_junco", 20),
        ("cervo_ferrugem", 24),
        ("alfa_salmoura", 3),
        ("viuva_rubra", 3),
    )
    assert VARZEAS_BREJOS_PROFILE.variant_chance == 13
    assert {creature.creature_id for creature in hunt_pool(33, VARZEAS_BREJOS_PROFILE)} == {
        "cao_salmoura",
        "garca_ferruginosa",
        "portador_rubro",
        "aranha_junco",
        "cervo_ferrugem",
        "alfa_salmoura",
    }
    assert {creature.creature_id for creature in hunt_pool(35, VARZEAS_BREJOS_PROFILE)} == {
        "portador_rubro",
        "aranha_junco",
        "cervo_ferrugem",
        "viuva_rubra",
    }
    assert sum(weight for _creature, weight in VARZEAS_BREJOS_PROFILE.creature_weights) == 100


def test_varzeas_brejos_material_pools_match_source_and_use_seed_ordinals():
    expected = {
        "aranha_junco": (
            ("material.varzeas.junco_ferruginoso", 65),
            ("material.varzeas.soro_antigo", 35),
        ),
        "cervo_ferrugem": (("material.varzeas.couro_de_varzea", 100),),
        "viuva_rubra": (
            ("material.varzeas.junco_ferruginoso", 60),
            ("material.varzeas.soro_antigo", 40),
        ),
    }
    assert {creature_id: MATERIAL_POOLS[creature_id] for creature_id in expected} == expected
    for creature_id, pool in expected.items():
        allowed = {material for material, _weight in pool}
        for ordinal in range(4):
            seed = f"persisted:material.basic.{ordinal}"
            selected = material_for(creature_id, seed)
            assert selected in allowed
            assert selected == material_for(creature_id, seed)
    assert material_for("cervo_ferrugem", "s:material.basic.0") == material_for(
        "cervo_ferrugem", "s:material.basic.1"
    )


def test_varzeas_brejos_exploration_pools_unique_gates_and_xp_match_source():
    profile = EXPLORATION_PROFILES[VARZEAS_BREJOS_LOCATION]
    assert profile == VARZEAS_BREJOS_EXPLORATION_PROFILE
    assert profile.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items()) == (
        ("great_discovery", 8),
        ("knowledge", 22),
        ("narrative", 15),
        ("combat", 25),
        ("resource", 10),
        ("atmospheric", 20),
    )
    actual = {
        result.result_id: (
            result.category,
            result.weight,
            result.unique,
            result.creature_id,
            result.min_level,
        )
        for result in profile.results
    }
    assert actual == {
        "explore.varzeas.brejos.braseiro_juncos_baixos": ("great_discovery", 50, True, None, 33),
        "explore.varzeas.brejos.entrada_enfermaria_afundada": ("great_discovery", 50, True, None, 34),
        "explore.varzeas.brejos.pulso_de_pressao": ("knowledge", 55, True, None, 33),
        "explore.varzeas.brejos.bolhas_sob_turfa": ("knowledge", 45, False, None, 33),
        "explore.varzeas.brejos.junco_dobrado": ("narrative", 55, False, None, 33),
        "explore.varzeas.brejos.agua_que_respira": ("narrative", 45, False, None, 33),
        "explore.varzeas.brejos.combat.cao_salmoura": ("combat", 18, False, "cao_salmoura", 33),
        "explore.varzeas.brejos.combat.garca_ferruginosa": ("combat", 17, False, "garca_ferruginosa", 33),
        "explore.varzeas.brejos.combat.portador_rubro": ("combat", 15, False, "portador_rubro", 33),
        "explore.varzeas.brejos.combat.aranha_junco": ("combat", 24, False, "aranha_junco", 33),
        "explore.varzeas.brejos.combat.cervo_ferrugem": ("combat", 26, False, "cervo_ferrugem", 33),
        "explore.varzeas.brejos.junco_ferruginoso": ("resource", 35, False, None, 33),
        "explore.varzeas.brejos.couro_varzea": ("resource", 25, False, None, 33),
        "explore.varzeas.brejos.soro_antigo": ("resource", 25, False, None, 33),
        "explore.varzeas.brejos.ferro_salmoura": ("resource", 15, False, None, 33),
        "explore.varzeas.brejos.lama_em_circulos": ("atmospheric", 34, False, None, 33),
        "explore.varzeas.brejos.nevoa_salobra": ("atmospheric", 33, False, None, 33),
        "explore.varzeas.brejos.estaca_submersa": ("atmospheric", 33, False, None, 33),
    }
    assert {
        result_id: VARZEAS_EXPLORATION_UNIQUE_XP[result_id]
        for result_id in (
            "explore.varzeas.brejos.braseiro_juncos_baixos",
            "explore.varzeas.brejos.entrada_enfermaria_afundada",
            "explore.varzeas.brejos.pulso_de_pressao",
        )
    } == {
        "explore.varzeas.brejos.braseiro_juncos_baixos": 6336,
        "explore.varzeas.brejos.entrada_enfermaria_afundada": 6336,
        "explore.varzeas.brejos.pulso_de_pressao": 1980,
    }


def test_varzeas_p20_s20_mission_screens_use_the_published_gates_and_steps():
    p20 = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=P20_ID,
        title="O Pulso sob a Lama",
        kind="water_occurrences",
        status="active",
        step=2,
        state_version=9,
        progress={"water_occurrences": ["a"]},
        location="Brejos do Pulso",
        level=33,
    )
    p20_screen = render_varzeas_mission(p20)
    p20_callbacks = {
        button.callback_data
        for row in p20_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "varzeas:action:P20:9:observe_pulse_b" in p20_callbacks
    assert "varzeas:action:P20:9:observe_pulse_c" in p20_callbacks
    assert "varzeas:action:P20:9:observe_pulse_a" not in p20_callbacks

    s20_offer = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=S20_ID,
        title="Um Corpo que Continua",
        kind="offer",
        status=None,
        step=None,
        state_version=0,
        progress={},
        location="Porto da Salmoura",
        level=34,
        available=True,
    )
    offer_screen = render_varzeas_mission(s20_offer)
    assert "Missão Padrão" in offer_screen.text
    assert "P20 concluída · Nv.34 · Porto da Salmoura" in offer_screen.text

    s20_travel = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=S20_ID,
        title="Um Corpo que Continua",
        kind="observe_tracks",
        status="active",
        step=1,
        state_version=2,
        progress={},
        location="Porto da Salmoura",
        level=34,
    )
    travel_screen = render_varzeas_mission(s20_travel)
    travel_callbacks = {
        button.callback_data
        for row in travel_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "road:route:varzeas_brejos" in travel_callbacks
    assert "varzeas:action:S20:2:observe_tracks" not in travel_callbacks


def test_varzeas_p20_codex_text_stays_within_the_published_revelation_limit():
    entry = next(
        item for item in CODEX_ENTRIES if item.entry_id == "codex.mystery.pulso_sob_a_lama"
    )
    assert (entry.title, entry.category) == ("Pulso sob a Lama", "mysteries")
    fragment = CODEX_FRAGMENTS["codex.fragment.varzeas.p20.pulso_sob_a_lama"]
    normalized = f"{fragment.title} {fragment.text}".casefold()
    assert "água" in normalized
    assert "pressão" in normalized
    assert "atividade biológica" in normalized
    assert "infraestrutura antiga enterrada" in normalized
    for premature_term in (
        "hemaris",
        "restituição",
        "persistência histórica",
        "transferência",
        "matriz rubra",
        "avesso",
        "regência",
        "desvelados",
    ):
        assert premature_term not in normalized


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
