from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from asterion.application.bestiary import (
    VARZEAS_DISTINCTIVE_ELITE_MASTERY,
    VARZEAS_IMPORTANT_FIRST_VICTORY_XP,
)
from asterion.application.inventory import MATERIAL_LABELS as INVENTORY_MATERIAL_LABELS
from asterion.application.knowledge_catalog import (
    CODEX_ENTRIES,
    CODEX_FRAGMENTS,
    CREATURE_PRESENTATION,
    VARZEAS_REGION_LABEL,
)
from asterion.application.road import (
    VARZEAS_EXPLORATION_UNIQUE_XP,
    _grade_catalyst_for_level,
    _grade_fragment_for_level,
)
from asterion.application.varzeas_missions import (
    P20_ID,
    P21_FRAGMENT,
    P21_ID,
    P21_REWARD_CHOICES,
    P22_CODEX,
    P22_FRAGMENT,
    P22_ID,
    S20_ID,
    S21_ID,
    S22_CODEX,
    S22_FRAGMENT,
    S22_ID,
    VarzeasMissionService,
    VarzeasMissionView,
)
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.combat import Action, _perform
from asterion.domain.equipment_modifications import equipment_grade
from asterion.domain.professions import MATERIAL_NAMES
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    LOCATION_LEVEL_BANDS,
    MATERIAL_POOLS,
    VARIANT_POOL,
    VARZEAS_BREJOS_EXPLORATION_PROFILE,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_BREJOS_PROFILE,
    VARZEAS_CREATURES,
    VARZEAS_DIQUES_EXPLORATION_PROFILE,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PROFILE,
    VARZEAS_GALERIAS_EXPLORATION_PROFILE,
    VARZEAS_GALERIAS_LOCATION,
    VARZEAS_GALERIAS_PROFILE,
    VARZEAS_GARDEN_GRAFT,
    VARZEAS_HEMARIS_WARDEN,
    VARZEAS_HEMATIC_COLLECTOR,
    VARZEAS_HORTOS_EXPLORATION_PROFILE,
    VARZEAS_HORTOS_LOCATION,
    VARZEAS_HORTOS_PROFILE,
    VARZEAS_MARSH_LAMPREY,
    create_creature_combat,
    creature_for,
    hunt_pool,
    material_for,
)
from asterion.infrastructure.db.combat_codec import decode, encode


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


def test_varzeas_hortos_hunt_explore_variants_and_materials_match_source():
    assert HUNT_PROFILES[VARZEAS_HORTOS_LOCATION] == VARZEAS_HORTOS_PROFILE
    assert LOCATION_LEVEL_BANDS["Hortos Hemaris"] == (35, 39)
    for creature_id in ("aranha_junco", "cervo_ferrugem", "viuva_rubra"):
        assert "varzeas.location.hortos_hemaris" in CREATURE_PRESENTATION[
            creature_id
        ].habitats
    assert "codex.fragment.varzeas.figure.ilyan_korr" in CODEX_FRAGMENTS
    assert VARZEAS_HORTOS_PROFILE.creature_weights == (
        ("aranha_junco", 22),
        ("cervo_ferrugem", 19),
        ("lampreia_varzea", 20),
        ("enxerto_horto", 18),
        ("mariposa_soro", 16),
        ("viuva_rubra", 2),
        ("coletor_hematico", 3),
    )
    assert VARZEAS_HORTOS_PROFILE.variant_chance == 16
    assert {creature.creature_id for creature in hunt_pool(35, VARZEAS_HORTOS_PROFILE)} == {
        "aranha_junco", "cervo_ferrugem", "lampreia_varzea", "enxerto_horto", "viuva_rubra"
    }
    assert {creature.creature_id for creature in hunt_pool(36, VARZEAS_HORTOS_PROFILE)} >= {
        "mariposa_soro"
    }
    assert {creature.creature_id for creature in hunt_pool(38, VARZEAS_HORTOS_PROFILE)} >= {
        "coletor_hematico"
    }
    assert {
        creature.creature_id: (creature.min_level, creature.max_level)
        for creature in VARZEAS_CREATURES
        if creature.creature_id
        in {
            "aranha_junco", "cervo_ferrugem", "lampreia_varzea", "enxerto_horto",
            "mariposa_soro", "viuva_rubra", "coletor_hematico",
        }
    } == {
        "aranha_junco": (33, 36),
        "cervo_ferrugem": (33, 37),
        "lampreia_varzea": (35, 38),
        "enxerto_horto": (35, 39),
        "mariposa_soro": (36, 39),
        "viuva_rubra": (35, 37),
        "coletor_hematico": (38, 40),
    }
    assert VARIANT_POOL["viuva_rubra"] == VARIANT_POOL["coletor_hematico"] == ()
    assert VARIANT_POOL["lampreia_varzea"] == ("hemorrhagic", "agile")
    assert VARIANT_POOL["enxerto_horto"] == ("resistant", "furious")
    assert VARIANT_POOL["mariposa_soro"] == ("agile", "furious")

    expected_materials = {
        "lampreia_varzea": (
            ("material.varzeas.junco_ferruginoso", 75),
            ("material.varzeas.soro_antigo", 25),
        ),
        "enxerto_horto": (
            ("material.varzeas.soro_antigo", 80),
            ("material.varzeas.junco_ferruginoso", 20),
        ),
        "mariposa_soro": (
            ("material.varzeas.soro_antigo", 65),
            ("material.varzeas.junco_ferruginoso", 35),
        ),
        "coletor_hematico": (
            ("material.varzeas.soro_antigo", 70),
            ("material.varzeas.ferro_de_salmoura", 30),
        ),
    }
    assert {key: MATERIAL_POOLS[key] for key in expected_materials} == expected_materials
    for creature_id, pool in expected_materials.items():
        draws = [material_for(creature_id, f"persisted:material.basic.{i}") for i in range(4)]
        assert draws == [
            material_for(creature_id, f"persisted:material.basic.{i}") for i in range(4)
        ]
        assert set(draws) <= {material for material, _weight in pool}

    profile = EXPLORATION_PROFILES[VARZEAS_HORTOS_LOCATION]
    assert profile == VARZEAS_HORTOS_EXPLORATION_PROFILE
    assert profile.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items()) == (
        ("great_discovery", 8),
        ("knowledge", 22),
        ("narrative", 15),
        ("combat", 25),
        ("resource", 10),
        ("atmospheric", 20),
    )
    result_weights = {
        result.result_id: (
            result.category,
            result.weight,
            result.unique,
            result.creature_id,
            result.min_level,
        )
        for result in profile.results
    }
    assert result_weights == {
        "explore.varzeas.hortos.braseiro_horto_seco": ("great_discovery", 50, True, None, 35),
        "explore.varzeas.hortos.estufa_restituicao": ("great_discovery", 50, True, None, 35),
        "explore.varzeas.hortos.canteiro_dupla_funcao": ("knowledge", 60, True, None, 35),
        "explore.varzeas.hortos.fibras_suporte": ("knowledge", 40, False, None, 35),
        "explore.varzeas.hortos.vidro_escurecido": ("narrative", 55, False, None, 35),
        "explore.varzeas.hortos.raiz_em_bandeja": ("narrative", 45, False, None, 35),
        "explore.varzeas.hortos.combat.aranha_junco": ("combat", 22, False, "aranha_junco", 35),
        "explore.varzeas.hortos.combat.cervo_ferrugem": ("combat", 19, False, "cervo_ferrugem", 35),
        "explore.varzeas.hortos.combat.lampreia_varzea": (
            "combat", 21, False, "lampreia_varzea", 35
        ),
        "explore.varzeas.hortos.combat.enxerto_horto": ("combat", 20, False, "enxerto_horto", 35),
        "explore.varzeas.hortos.combat.mariposa_soro": ("combat", 18, False, "mariposa_soro", 36),
        "explore.varzeas.hortos.soro_antigo": ("resource", 35, False, None, 35),
        "explore.varzeas.hortos.junco_ferruginoso": ("resource", 30, False, None, 35),
        "explore.varzeas.hortos.couro_varzea": ("resource", 20, False, None, 35),
        "explore.varzeas.hortos.ferro_salmoura": ("resource", 15, False, None, 35),
        "explore.varzeas.hortos.etiquetas_sem_nome": ("atmospheric", 34, False, None, 35),
        "explore.varzeas.hortos.canais_irrigacao": ("atmospheric", 33, False, None, 35),
        "explore.varzeas.hortos.folhas_palidas": ("atmospheric", 33, False, None, 35),
    }
    assert {
        result_id: VARZEAS_EXPLORATION_UNIQUE_XP[result_id]
        for result_id in (
            "explore.varzeas.hortos.braseiro_horto_seco",
            "explore.varzeas.hortos.estufa_restituicao",
            "explore.varzeas.hortos.canteiro_dupla_funcao",
        )
    } == {
        "explore.varzeas.hortos.braseiro_horto_seco": 7248,
        "explore.varzeas.hortos.estufa_restituicao": 7248,
        "explore.varzeas.hortos.canteiro_dupla_funcao": 2265,
    }


def test_varzeas_horto_creature_actions_and_mastery_contract():
    expected = {
        "lampreia_varzea": ("Mordida Circular", "Drenagem de Lama", "Bote de Margem"),
        "enxerto_horto": ("Pancada Fibrosa", "Casca de Suporte", "Regeneração Residual"),
        "mariposa_soro": ("Escama Irritante", "Toque Pálido", "Clarão de Vidro"),
        "coletor_hematico": (
            "Impacto de Coleta", "Reservatório Blindado", "Marca de Extração", "Extração Forçada"
        ),
    }
    for creature_id, labels in expected.items():
        creature = creature_for(creature_id)
        assert tuple(action[1] for action in creature.actions) == labels
    assert creature_for("enxerto_horto").actions[1][12:15] == (
        Decimal("0.90"), 2, True
    )
    healing = creature_for("enxerto_horto").actions[2]
    assert healing[9] == 4 and healing[17] is None and healing[18] == 2
    assert healing[30] == Decimal("0.04")
    assert creature_for("lampreia_varzea").actions[0][2] == Decimal("0.95")
    assert creature_for("lampreia_varzea").actions[2][2] == Decimal("1.30")
    assert creature_for("mariposa_soro").actions[0][2:6] == (
        Decimal("0.75"), 0, Decimal("0.10"), 2
    )
    assert creature_for("mariposa_soro").actions[0][9] == 3
    assert creature_for("mariposa_soro").actions[1][2] == Decimal("0.90")
    assert creature_for("mariposa_soro").actions[2][2] == Decimal("1.25")
    assert creature_for("mariposa_soro").actions[2][9] == 3
    assert creature_for("coletor_hematico").actions[1][12:14] == (
        Decimal("1.00"), 2
    )
    assert creature_for("coletor_hematico").actions[1][9] == 3
    assert creature_for("coletor_hematico").actions[2][2:6] == (
        Decimal("0.85"), 0, Decimal("0.12"), 2
    )
    assert creature_for("coletor_hematico").actions[3][2] == Decimal("1.80")
    assert creature_for("coletor_hematico").actions[3][8:10] == (True, 4)
    lamprey_drain = creature_for("lampreia_varzea").actions[1]
    assert lamprey_drain[28] == Decimal("0.30")
    assert lamprey_drain[31] == Decimal("0.04")
    assert VARZEAS_DISTINCTIVE_ELITE_MASTERY["coletor_hematico"] == {
        "first_victory",
        "action:reservatorio_blindado",
        "action:marca_extracao",
        "action:extracao_forcada",
    }
    assert VARZEAS_IMPORTANT_FIRST_VICTORY_XP["coletor_hematico"] == (40, 3084)


def test_varzeas_transfer_galleries_hunt_explore_and_vigia_match_source():
    profile = VARZEAS_GALERIAS_PROFILE
    assert HUNT_PROFILES[VARZEAS_GALERIAS_LOCATION] == profile
    assert LOCATION_LEVEL_BANDS["Galerias de Transferência"] == (37, 40)
    assert profile.creature_weights == (
        ("enxerto_horto", 34),
        ("mariposa_soro", 30),
        ("vigia_hemaris", 33),
        ("coletor_hematico", 3),
    )
    assert profile.variant_chance == 18
    assert {creature.creature_id for creature in hunt_pool(37, profile)} == {
        "enxerto_horto",
        "mariposa_soro",
    }
    assert {creature.creature_id for creature in hunt_pool(38, profile)} == {
        "enxerto_horto",
        "mariposa_soro",
        "vigia_hemaris",
        "coletor_hematico",
    }
    assert VARZEAS_HEMARIS_WARDEN in VARZEAS_CREATURES
    warden = creature_for("vigia_hemaris")
    assert (warden.category, warden.archetype, warden.unlock_level, warden.max_level) == (
        "uncommon", "armored", 38, 40
    )
    assert tuple(action[1] for action in warden.actions) == (
        "Golpe de Contenção",
        "Placa Lavável",
        "Marca de Triagem",
        "Queda de Suporte",
    )
    assert warden.actions[1][12:14] == (Decimal("0.95"), 2)
    assert warden.actions[1][9] == 3
    assert warden.actions[2][2:6] == (
        Decimal("0.85"), 0, Decimal("0.10"), 2
    )
    assert warden.actions[3][2] == Decimal("1.65")
    assert warden.actions[3][8:10] == (True, 4)
    assert VARIANT_POOL["vigia_hemaris"] == ("resistant", "furious")

    expected_materials = {
        "vigia_hemaris": (
            ("material.varzeas.ferro_de_salmoura", 90),
            ("material.varzeas.soro_antigo", 10),
        ),
        "coletor_hematico": (
            ("material.varzeas.soro_antigo", 70),
            ("material.varzeas.ferro_de_salmoura", 30),
        ),
    }
    assert {key: MATERIAL_POOLS[key] for key in expected_materials} == expected_materials
    for creature_id, pool in expected_materials.items():
        draws = [
            material_for(creature_id, f"persisted:material.basic.{ordinal}")
            for ordinal in range(4)
        ]
        assert draws == [
            material_for(creature_id, f"persisted:material.basic.{ordinal}")
            for ordinal in range(4)
        ]
        assert set(draws) <= {material_id for material_id, _weight in pool}

    exploration = VARZEAS_GALERIAS_EXPLORATION_PROFILE
    assert EXPLORATION_PROFILES[VARZEAS_GALERIAS_LOCATION] == exploration
    assert exploration.category_weights == tuple(EXPLORATION_CATEGORY_WEIGHTS.items())
    actual = {
        result.result_id: (result.category, result.weight, result.unique, result.creature_id)
        for result in exploration.results
    }
    assert actual == {
        "explore.varzeas.galerias.braseiro_valvulas": ("great_discovery", 50, True, None),
        "explore.varzeas.galerias.entrada_cisterna_transferencia": (
            "great_discovery",
            50,
            True,
            None,
        ),
        "explore.varzeas.galerias.linha_retorno": ("knowledge", 60, True, None),
        "explore.varzeas.galerias.reservatorio_vazio": ("knowledge", 40, False, None),
        "explore.varzeas.galerias.valvula_marcada": ("narrative", 55, False, None),
        "explore.varzeas.galerias.tubo_sob_parede": ("narrative", 45, False, None),
        "explore.varzeas.galerias.combat.enxerto_horto": ("combat", 34, False, "enxerto_horto"),
        "explore.varzeas.galerias.combat.mariposa_soro": ("combat", 30, False, "mariposa_soro"),
        "explore.varzeas.galerias.combat.vigia_hemaris": ("combat", 36, False, "vigia_hemaris"),
        "explore.varzeas.galerias.ferro_salmoura": ("resource", 35, False, None),
        "explore.varzeas.galerias.soro_antigo": ("resource", 35, False, None),
        "explore.varzeas.galerias.junco_ferruginoso": ("resource", 20, False, None),
        "explore.varzeas.galerias.couro_varzea": ("resource", 10, False, None),
        "explore.varzeas.galerias.eco_reservatorio": ("atmospheric", 34, False, None),
        "explore.varzeas.galerias.goteira_escura": ("atmospheric", 33, False, None),
        "explore.varzeas.galerias.pressao_sem_fluxo": ("atmospheric", 33, False, None),
    }
    assert {
        result_id: VARZEAS_EXPLORATION_UNIQUE_XP[result_id]
        for result_id in (
            "explore.varzeas.galerias.braseiro_valvulas",
            "explore.varzeas.galerias.entrada_cisterna_transferencia",
            "explore.varzeas.galerias.linha_retorno",
        )
    } == {
        "explore.varzeas.galerias.braseiro_valvulas": 7896,
        "explore.varzeas.galerias.entrada_cisterna_transferencia": 7896,
        "explore.varzeas.galerias.linha_retorno": 2468,
    }
    assert VarzeasMissionService._combat_config(P22_ID)[1:] == (
        "Galerias de Transferência", 37, VARZEAS_HEMARIS_WARDEN
    )


def test_varzeas_p22_s22_codex_and_screens_stay_within_published_scope():
    assert any(entry.entry_id == P22_CODEX for entry in CODEX_ENTRIES)
    assert CODEX_FRAGMENTS[P22_FRAGMENT].title == "Registro técnico das Galerias"
    assert any(entry.entry_id == S22_CODEX for entry in CODEX_ENTRIES)
    assert CODEX_FRAGMENTS[S22_FRAGMENT].title == "Rotinas sem paciente válido"
    assert "Emergência" not in CODEX_FRAGMENTS[P22_FRAGMENT].text
    assert "Hemário moderno" not in CODEX_FRAGMENTS[S22_FRAGMENT].text

    p22 = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=P22_ID,
        title="Transferência",
        kind="combat_start",
        status="active",
        step=4,
        state_version=7,
        progress={},
        location="Galerias de Transferência",
        level=37,
    )
    p22_screen = render_varzeas_mission(p22)
    assert "Vigia Hemaris Nv.37" in p22_screen.text
    p22_callbacks = {
        button.callback_data
        for row in p22_screen.keyboard.inline_keyboard
        for button in row
    }
    assert "varzeas:combat:P22:7:solo" in p22_callbacks
    assert "varzeas:combat:P22:7:group" in p22_callbacks

    s22 = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=S22_ID,
        title="Protocolos sem Paciente",
        kind="inspect_automated_routines",
        status="active",
        step=1,
        state_version=3,
        progress={},
        location="Hortos Hemaris",
        level=37,
    )
    s22_screen = render_varzeas_mission(s22)
    assert "Inspecione as rotinas automatizadas" in s22_screen.text
    assert "Curador Vazio" not in s22_screen.text
    assert not any(
        button.callback_data.startswith("varzeas:combat:S22:")
        for row in s22_screen.keyboard.inline_keyboard
        for button in row
    )
    assert VARZEAS_IMPORTANT_FIRST_VICTORY_XP["viuva_rubra"] == (37, 2718)


def test_horto_lamprey_vampirism_uses_effective_damage_and_hp_cap():
    def combat(combat_id: int):
        return create_creature_combat(
            UUID(int=combat_id),
            "Teste",
            "sentinela",
            "remanescente",
            Decimal("100000"),
            VARZEAS_MARSH_LAMPREY,
            35,
            None,
            player_level=35,
        )

    state = combat(351)
    action = state.enemy_actions["drenagem_lama"]
    assert action.vampirism_fraction == Decimal("0.30")
    assert action.vampirism_cap_hp_fraction == Decimal("0.04")
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    assert restored.enemy_actions["drenagem_lama"].vampirism_cap_hp_fraction == Decimal(
        "0.04"
    )
    legacy = encode(state)
    legacy["enemy_actions"]["drenagem_lama"].pop("vampirism_cap_hp_fraction")
    assert decode(legacy, state.id, state.ruleset, state.version).enemy_actions[
        "drenagem_lama"
    ].vampirism_cap_hp_fraction is None
    enemy = state.fighters["enemy"]
    enemy.hp = enemy.stats.hp / Decimal(2)
    before = enemy.hp
    player = state.fighters["player"]
    player.stats = replace(player.stats, evasion=Decimal(0))
    player.barrier = Decimal("100000")
    player.barrier_remaining = 2
    _perform(state, "enemy", "drenagem_lama")
    assert state.events[-1].effective_damage == 0
    assert enemy.hp == before

    state = combat(352)
    enemy = state.fighters["enemy"]
    enemy.hp = enemy.stats.hp / Decimal(2)
    before = enemy.hp
    player = state.fighters["player"]
    player.stats = replace(player.stats, evasion=Decimal(0))
    player.hp = Decimal(1)
    _perform(state, "enemy", "drenagem_lama")
    assert state.events[-1].effective_damage == 1
    assert enemy.hp == before

    graft = create_creature_combat(
        UUID(int=353),
        "Teste",
        "sentinela",
        "remanescente",
        Decimal("100000"),
        VARZEAS_GARDEN_GRAFT,
        35,
        None,
        player_level=35,
    )
    heal = graft.enemy_actions["regeneracao_residual"]
    actor = graft.fighters["enemy"]
    assert heal.max_uses_per_combat == 2
    assert heal.cooldown == 4
    assert abs(
        heal.heal_coefficient * actor.stats.attack - actor.stats.hp * Decimal("0.04")
    ) < Decimal("0.000001")
    assert graft.enemy_actions["casca_suporte"].skip_if_barrier_active is True

    collector = create_creature_combat(
        UUID(int=354),
        "Teste",
        "sentinela",
        "remanescente",
        Decimal("100000"),
        VARZEAS_HEMATIC_COLLECTOR,
        38,
        None,
        player_level=38,
    )
    assert collector.enemy_actions["reservatorio_blindado"].skip_if_barrier_active is False


def test_varzeas_p21_choice_screen_is_individual_and_explicit():
    assert P21_REWARD_CHOICES == {
        "mask": ("Máscara da Salmoura", "Cabeça"),
        "seal": ("Selo dos Diques", "Acessório"),
        "reliquary": ("Relicário do Horto Estéril", "Artefato"),
    }
    codex_text = CODEX_FRAGMENTS[P21_FRAGMENT].text
    assert "Projeto Hemaris" in codex_text
    assert not any(
        forbidden in codex_text
        for forbidden in (
            "Transferência",
            "Emergência",
            "coerção",
            "origem ancestral",
            "Matriz Rubra",
            "Regência",
            "Desvelados",
        )
    )
    view = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=P21_ID,
        title="Os Hortos Vazios",
        kind="choose_reward",
        status="active",
        step=7,
        state_version=12,
        progress={},
        location="Hortos Hemaris",
        level=35,
    )
    screen = render_varzeas_mission(view)
    callbacks = [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]
    assert "Escolha exatamente um Equipamento Raro Nv.35." in screen.text
    assert {
        "varzeas:choice:P21:12:mask",
        "varzeas:choice:P21:12:seal",
        "varzeas:choice:P21:12:reliquary",
    } <= set(callbacks)
    assert len(
        [value for value in callbacks if value and value.startswith("varzeas:choice:P21:")]
    ) == 3


def test_varzeas_s21_screen_uses_only_the_published_investigation_beats():
    view = VarzeasMissionView(
        character_id=uuid4(),
        quest_id=S21_ID,
        title="Cicatrizes de Cultivo",
        kind="observe_autonomous_grafts",
        status="active",
        step=2,
        state_version=4,
        progress={},
        location="Hortos Hemaris",
        level=35,
    )
    screen = render_varzeas_mission(view)
    assert "culturas de suporte se tornaram autônomas" in screen.text
    assert "pessoas transformadas" in screen.text
    assert "Transferência" not in screen.text
    assert "Emergência" not in screen.text
    assert "varzeas:action:S21:4:observe_autonomous_grafts" in {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }


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
        "explore.varzeas.brejos.braseiro_juncos_baixos": (
            "great_discovery", 50, True, None, 33
        ),
        "explore.varzeas.brejos.entrada_enfermaria_afundada": (
            "great_discovery", 50, True, None, 34
        ),
        "explore.varzeas.brejos.pulso_de_pressao": ("knowledge", 55, True, None, 33),
        "explore.varzeas.brejos.bolhas_sob_turfa": ("knowledge", 45, False, None, 33),
        "explore.varzeas.brejos.junco_dobrado": ("narrative", 55, False, None, 33),
        "explore.varzeas.brejos.agua_que_respira": ("narrative", 45, False, None, 33),
        "explore.varzeas.brejos.combat.cao_salmoura": ("combat", 18, False, "cao_salmoura", 33),
        "explore.varzeas.brejos.combat.garca_ferruginosa": (
            "combat", 17, False, "garca_ferruginosa", 33
        ),
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


def test_varzeas_v1_0_2_barrier_contract_and_source_authority_mirrors():
    root = Path(__file__).resolve().parents[1]
    authority = (root / "SOURCE_AUTHORITY.md").read_bytes()
    assert authority == (root / "docs/SOURCE_AUTHORITY.md").read_bytes()
    assert b"ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.2_FINAL.md" in authority

    source = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.2_FINAL.md").read_text(
        encoding="utf-8"
    )
    published_barriers = (
        "Casca de Suporte · Barreira `90% ATQ` por `2T`, CD3.",
        "Placa Lavável · Barreira `95% ATQ` por `2T`, CD3.",
        "Reservatório Blindado · Barreira `100% ATQ` por `2T`, CD3.",
        "Placa de Procedimento · Barreira `100% ATQ` por `2T`, CD3.",
        "Linha Pressurizada · Barreira `95% ATQ` por `2T`, CD3.",
        "Membrana de Contenção · Barreira `8% HP Máximo` por `2T`, CD4.",
        "Protocolo de Continuidade · Barreira igual a `8% HP Máximo` por `2T`, CD4.",
    )
    assert all(barrier in source for barrier in published_barriers)
    assert "Revisão v1.0.2" in source
    assert Action("duration-default", "duration-default", Decimal(0)).self_barrier_duration == 0