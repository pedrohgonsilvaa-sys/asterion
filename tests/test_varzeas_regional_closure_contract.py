from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from asterion.application.cosmetic_catalog import COSMETICS_BY_ID
from asterion.application.knowledge_catalog import (
    ACHIEVEMENTS,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
)
from asterion.application.varzeas_feats import (
    VARZEAS_BASE_CREATURES,
    VARZEAS_UNIQUE_EXPLORATION,
)
from asterion.application.varzeas_missions import (
    P24_ID,
    S24_ID,
    VarzeasMissionService,
    VarzeasMissionView,
)
from asterion.bot.varzeas_missions_ui import render_varzeas_mission
from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.combat import CombatEvent, _resolve_phase_triggers
from asterion.domain.equipment_modifications import (
    ENCHANTMENT_FAMILIES,
    RUNE_FAMILIES,
    enchantment_potency_for,
    rune_potency_for,
)
from asterion.domain.professions import (
    RECIPE_BY_ID,
    RECIPE_DEFINITIONS,
    recipe_crown_cost,
)
from asterion.domain.road import (
    RULESET,
    VARZEAS_CAMPAIGN_BOSSES,
    CreatureCombatantSpec,
    create_creature_party_combat,
    road_enemy_stats,
)
from asterion.domain.varzeas_bosses import (
    MATRIX_PHASE_II,
    MATRIX_PHASE_III,
    configure_varzeas_campaign_boss,
    varzeas_boss_phase_evidence,
)

D = Decimal


def _boss_combat(creature, group_size: int = 1):
    combat = create_creature_party_combat(
        uuid4(),
        "Ilyan",
        "sentinela",
        "remanescente",
        D("5000"),
        (
            CreatureCombatantSpec(
                creature,
                40,
                "enemy",
                campaign_boss_group_size=group_size,
            ),
        ),
        player_level=40,
        ruleset_version=RULESET,
    )
    return configure_varzeas_campaign_boss(
        combat,
        creature.creature_id,
        shared=group_size > 1,
    )


def test_varzeas_campaign_bosses_use_only_global_campaign_scaling():
    for creature in VARZEAS_CAMPAIGN_BOSSES:
        solo = road_enemy_stats(creature, 40)
        for size in range(1, 5):
            combat = _boss_combat(creature, size)
            assert combat.fighters["enemy"].level == 40
            assert combat.fighters["enemy"].stats == scale_campaign_boss_stats(
                solo, size
            )
        two = _boss_combat(creature, 2).fighters["enemy"].stats
        assert two.defense == solo.defense
        assert two.agility == solo.agility


def test_matrix_actions_phases_healing_limits_and_telegraphs_are_explicit():
    combat = _boss_combat(VARZEAS_CAMPAIGN_BOSSES[0])
    actions = combat.enemy_actions
    assert set(actions) == {
        "pulso_regulador",
        "coleta_dirigida",
        "membrana_contencao",
        "transferencia_externa",
        "regulacao_emergencia",
        "sobrecarga_matriz",
        "triagem_terminal",
    }
    assert actions["pulso_regulador"].coefficient == D("0.80")
    assert actions["pulso_regulador"].target_mode == "all_opponents"
    assert actions["pulso_regulador"].cooldown == 3
    assert actions["coleta_dirigida"].coefficient == D("1.00")
    assert actions["coleta_dirigida"].attack_debuff == D("0.10")
    assert actions["coleta_dirigida"].duration == 2
    assert actions["coleta_dirigida"].cooldown == 3
    assert actions["coleta_dirigida"].skip_if_target_effect_active == "coleta_dirigida"

    membrane = actions["membrana_contencao"]
    assert membrane.self_barrier_hp_fraction == D("0.08")
    assert membrane.self_barrier_duration == 2
    assert membrane.cooldown == 4
    assert membrane.skip_if_barrier_active is True
    assert membrane.skip_if_actor_last_action == ("sobrecarga_matriz",)

    transfer = actions["transferencia_externa"]
    assert transfer.coefficient == D("1.65")
    assert transfer.prepared is True
    assert transfer.cooldown == 4

    heal = actions["regulacao_emergencia"]
    assert heal.phase_ids == ("II",)
    assert heal.cooldown == 4
    assert heal.max_uses_per_combat == 3
    assert heal.heal_coefficient * combat.fighters["enemy"].stats.attack == (
        combat.fighters["enemy"].stats.hp * D("0.04")
    )
    assert heal.skip_if_barrier_active is True

    overload = actions["sobrecarga_matriz"]
    assert overload.coefficient == D("1.10")
    assert overload.target_mode == "all_opponents"
    assert overload.prepared is True
    assert overload.phase_ids == ("III",)
    assert overload.cooldown == 5
    assert overload.skip_if_actor_last_action == ("membrana_contencao",)

    terminal = actions["triagem_terminal"]
    assert terminal.coefficient == D("1.35")
    assert terminal.phase_ids == ("III",)
    assert terminal.actor_per_bonus_if_target_hp_fraction_at_most == D("0.10")
    assert terminal.actor_per_bonus_hp_fraction_threshold == D("0.40")
    assert terminal.cooldown == 3

    enemy = combat.fighters["enemy"]
    enemy.hp = enemy.stats.hp * D("0.70")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "II"
    assert MATRIX_PHASE_II in combat.phase_triggered_ids
    assert "phase:persistencia" in varzeas_boss_phase_evidence(combat)
    enemy.hp = enemy.stats.hp * D("0.35")
    _resolve_phase_triggers(combat)
    assert combat.phase_id == "III"
    assert MATRIX_PHASE_III in combat.phase_triggered_ids
    assert "phase:emergencia" in varzeas_boss_phase_evidence(combat)


def test_quarantine_custodian_has_no_unpublished_phases_or_economy_actions():
    combat = _boss_combat(VARZEAS_CAMPAIGN_BOSSES[1])
    actions = combat.enemy_actions
    assert set(actions) == {
        "golpe_isolamento",
        "rota_selada",
        "correcao_perimetro",
        "fecho_quarentena",
    }
    assert actions["golpe_isolamento"].coefficient == D("1.00")
    route = actions["rota_selada"]
    assert (route.coefficient, route.duration, route.cooldown) == (
        D("0.90"),
        2,
        3,
    )
    assert route.effect_stat == "agility"
    assert route.skip_if_target_effect_active == "rota_selada"
    assert actions["correcao_perimetro"].coefficient == D("1.25")
    assert actions["correcao_perimetro"].cooldown == 3
    finisher = actions["fecho_quarentena"]
    assert finisher.coefficient == D("1.75")
    assert finisher.prepared is True
    assert finisher.cooldown == 4
    assert combat.phase_triggers == ()


def test_varzeas_campaign_boss_masteries_require_published_evidence():
    matrix = _boss_combat(VARZEAS_CAMPAIGN_BOSSES[0])
    assert "phase:persistencia" not in varzeas_boss_phase_evidence(matrix)
    assert "phase:emergencia" not in varzeas_boss_phase_evidence(matrix)
    assert "action:transferencia_externa" not in varzeas_boss_phase_evidence(matrix)

    custodian = _boss_combat(VARZEAS_CAMPAIGN_BOSSES[1])
    assert "action:rota_selada" not in varzeas_boss_phase_evidence(custodian)
    assert "action:fecho_quarentena" not in varzeas_boss_phase_evidence(custodian)


def test_grade_iv_normal_equipment_family_catalog_matches_published_names_and_baselines():
    expected = {
        "Arma do Dique": (
            "blacksmith", "Principal", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Guarda de Salmoura": (
            "blacksmith", "Secundária", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Arma Pesada de Transferência": (
            "blacksmith", "2H", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Elmo das Válvulas": (
            "blacksmith", "Cabeça", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Couraça das Várzeas": (
            "blacksmith", "Torso", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Manoplas Ferruginosas": (
            "blacksmith", "Mãos", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Grevas do Porto": (
            "blacksmith", "Pés", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.70"),
        ),
        "Capuz de Junco": (
            "leatherworker", "Cabeça", "material.varzeas.couro_de_varzea",
            "material.varzeas.junco_ferruginoso", D("0.70"),
        ),
        "Veste Encerada": (
            "leatherworker", "Torso", "material.varzeas.couro_de_varzea",
            "material.varzeas.junco_ferruginoso", D("0.70"),
        ),
        "Luvas de Várzea": (
            "leatherworker", "Mãos", "material.varzeas.couro_de_varzea",
            "material.varzeas.junco_ferruginoso", D("0.70"),
        ),
        "Botas da Salmoura": (
            "leatherworker", "Pés", "material.varzeas.couro_de_varzea",
            "material.varzeas.junco_ferruginoso", D("0.70"),
        ),
        "Selo de Transferência": (
            "jeweler", "Acessório", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.60"),
        ),
        "Relicário de Restituição": (
            "jeweler", "Artefato", "material.varzeas.ferro_de_salmoura",
            "material.varzeas.soro_antigo", D("0.60"),
        ),
    }
    recipes = [
        recipe
        for recipe in RECIPE_DEFINITIONS
        if recipe.grade == 4
        and recipe.output_kind == "equipment"
        and recipe.unlock_id is None
    ]
    assert len(recipes) == 39
    by_name = {}
    for recipe in recipes:
        by_name.setdefault(recipe.name, []).append(recipe)
    assert set(by_name) == set(expected)
    for name, (profession, slot, primary, secondary, ratio) in expected.items():
        family = by_name[name]
        assert {recipe.rarity for recipe in family} == {"Comum", "Raro", "Épico"}
        for recipe in family:
            assert recipe.profession_id == profession
            assert recipe.output_name == name
            assert recipe.output_slot == slot
            assert recipe.primary_material_id in {
                "material.varzeas.ferro_de_salmoura",
                "material.varzeas.couro_de_varzea",
            }
            assert recipe.secondary_material_id in {
                "material.varzeas.soro_antigo",
                "material.varzeas.junco_ferruginoso",
            }
            assert recipe.primary_ratio == ratio
            assert recipe.grade == 4
            assert recipe.creation_enabled is True
            assert recipe.unlock_id is None
        assert family[0].primary_material_id == primary
        assert family[0].secondary_material_id == secondary


def test_grade_iv_rune_and_enchantment_catalogs_match_source_values_and_costs():
    rune_attributes = {
        "Dique": "ATQ",
        "Contenção": "DEF",
        "Junco": "AGI",
        "Triagem": "PER",
        "Emergência": "CRIT",
        "Restituição": "HP",
        "Margem": "Esquiva",
        "Válvula": "Bloqueio",
    }
    rune_power = {
        "HP": ("0.45%", "0.65%", "0.80%"),
        "ATQ": ("0.45%", "0.65%", "0.80%"),
        "DEF": ("0.80%", "1.10%", "1.40%"),
        "AGI": ("0.80%", "1.10%", "1.40%"),
        "PER": ("0.50 p.p.", "0.50 p.p.", "0.75 p.p."),
        "CRIT": ("0.50 p.p.", "0.50 p.p.", "0.75 p.p."),
        "Esquiva": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."),
        "Bloqueio": ("0.50 p.p.", "0.50 p.p.", "0.75 p.p."),
    }
    assert {family: RUNE_FAMILIES[family][0] for family in rune_attributes} == rune_attributes
    assert len(
        [
            recipe
            for recipe in RECIPE_DEFINITIONS
            if recipe.grade == 4 and recipe.output_kind == "rune"
        ]
    ) == 16
    rune_slugs = {
        "Dique": "dike",
        "Contenção": "containment",
        "Junco": "reed",
        "Triagem": "triage",
        "Emergência": "emergency",
        "Restituição": "restitution",
        "Margem": "margin",
        "Válvula": "valve",
    }
    for family, stat in rune_attributes.items():
        assert tuple(
            rune_potency_for(family, rarity, 4)
            for rarity in ("Rara", "Épica", "Lendária")
        ) == rune_power[stat]
        for rarity, level, essences, metal, catalysts, fragments, crowns in (
            ("Rara", 5, 4, 2, 0, 2, 210),
            ("Épica", 10, 7, 3, 1, 4, 420),
        ):
            rarity_id = "rara" if rarity == "Rara" else "epica"
            recipe = RECIPE_BY_ID[
                f"recipe.varzeas.artificer.rune.{rune_slugs[family]}.{rarity_id}"
            ]
            assert (recipe.grade, recipe.required_level, recipe.rarity) == (4, level, rarity)
            assert recipe.output_family == family
            assert recipe.output_id.startswith("rune.varzeas.")
            materials = {
                material.material_id: material.quantity
                for material in recipe.fixed_materials
            }
            expected_materials = {
                "material.varzeas.soro_antigo": essences,
                "material.varzeas.ferro_de_salmoura": metal,
                "material.varzeas.fragmento_aprimoramento_iv": fragments,
            }
            if catalysts:
                expected_materials["material.varzeas.catalisador_elite_iv"] = catalysts
            assert materials == expected_materials
            assert recipe_crown_cost(recipe, 40) == crowns

    enchantment_attributes = {
        "Fio do Dique": "ATQ",
        "Pele de Contenção": "DEF",
        "Passo de Junco": "AGI",
        "Marca de Triagem": "PER",
        "Eco de Emergência": "CRIT",
        "Sopro de Restituição": "HP",
        "Véu da Margem": "Esquiva",
        "Selo da Válvula": "Bloqueio",
    }
    enchantment_power = {
        "HP": ("0.15%", "0.30%", "0.40%"),
        "ATQ": ("0.15%", "0.30%", "0.40%"),
        "DEF": ("0.30%", "0.55%", "0.80%"),
        "AGI": ("0.30%", "0.55%", "0.80%"),
        "PER": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."),
        "CRIT": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."),
        "Esquiva": ("0.25 p.p.", "0.25 p.p.", "0.50 p.p."),
        "Bloqueio": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."),
    }
    enchantment_slugs = {
        "Fio do Dique": "dike_wire",
        "Pele de Contenção": "containment_skin",
        "Passo de Junco": "reed_step",
        "Marca de Triagem": "triage_mark",
        "Eco de Emergência": "emergency_echo",
        "Sopro de Restituição": "restitution_breath",
        "Véu da Margem": "margin_veil",
        "Selo da Válvula": "valve_seal",
    }
    assert {
        family: ENCHANTMENT_FAMILIES[family] for family in enchantment_attributes
    } == enchantment_attributes
    assert len(
        [
            recipe
            for recipe in RECIPE_DEFINITIONS
            if recipe.grade == 4 and recipe.output_kind == "enchantment"
        ]
    ) == 17  # 16 normal recipes plus the direct P24 recipe.
    for family, stat in enchantment_attributes.items():
        assert tuple(
            enchantment_potency_for(family, rarity, 4)
            for rarity in ("Raro", "Épico", "Lendário")
        ) == enchantment_power[stat]
        for rarity, rarity_id, level, essences, metal, catalysts, crowns in (
            ("Raro", "raro", 5, 3, 1, 0, 140),
            ("Épico", "epico", 10, 5, 2, 1, 280),
        ):
            recipe = RECIPE_BY_ID[
                f"recipe.varzeas.artificer.enchantment.{enchantment_slugs[family]}.{rarity_id}"
            ]
            assert (recipe.grade, recipe.required_level, recipe.rarity) == (4, level, rarity)
            assert recipe.output_family == family
            assert recipe.output_id == stat
            materials = {
                material.material_id: material.quantity
                for material in recipe.fixed_materials
            }
            expected_materials = {
                "material.varzeas.soro_antigo": essences,
                "material.varzeas.ferro_de_salmoura": metal,
            }
            if catalysts:
                expected_materials["material.varzeas.catalisador_elite_iv"] = catalysts
            assert materials == expected_materials
            assert recipe_crown_cost(recipe, 40) == crowns

    assert not any(
        recipe.grade == 4
        and recipe.output_kind in {"rune", "enchantment"}
        and recipe.rarity == "Lendário"
        for recipe in RECIPE_DEFINITIONS
    )


def test_varzeas_consumables_and_three_special_recipes_use_exact_published_costs():
    expected_consumables = {
        "consumable.heal.varzeas.iv": (
            9, 70,
            {"material.varzeas.junco_ferruginoso": 3, "material.varzeas.soro_antigo": 1},
        ),
        "consumable.purification.varzeas.iv": (
            9, 100,
            {"material.varzeas.junco_ferruginoso": 2, "material.varzeas.soro_antigo": 2},
        ),
        "consumable.antidote.varzeas.iv": (
            9, 100,
            {"material.varzeas.junco_ferruginoso": 4, "material.varzeas.soro_antigo": 1},
        ),
        "consumable.vigor.varzeas.iv": (
            10, 350,
            {
                "material.varzeas.junco_ferruginoso": 6,
                "material.varzeas.soro_antigo": 4,
                "material.varzeas.catalisador_elite_iv": 1,
            },
        ),
        "consumable.protection.varzeas.iv": (
            9, 140,
            {"material.varzeas.junco_ferruginoso": 3, "material.varzeas.soro_antigo": 2},
        ),
        "consumable.dispeller.varzeas.iv": (
            10, 180,
            {"material.varzeas.junco_ferruginoso": 2, "material.varzeas.soro_antigo": 3},
        ),
        "consumable.warding.varzeas.iv": (
            12, 210,
            {"material.varzeas.junco_ferruginoso": 4, "material.varzeas.soro_antigo": 2},
        ),
    }
    for consumable_id, (level, crowns, expected_materials) in expected_consumables.items():
        recipe = next(
            recipe
            for recipe in RECIPE_DEFINITIONS
            if recipe.output_id == consumable_id and recipe.output_kind == "consumable"
        )
        assert recipe.grade == 4
        assert recipe.required_level == level
        assert recipe_crown_cost(recipe, 40) == crowns
        assert {
            material.material_id: material.quantity
            for material in recipe.fixed_materials
        } == expected_materials

    expected_specials = {
        "recipe.varzeas.enfermaria.mascara_triagem_silenciosa": (
            ("leatherworker", 9), "Máscara da Triagem Silenciosa", "Cabeça",
            "equipment", "Raro", 1, 9, True, 240,
            {
                "material.varzeas.couro_de_varzea": 6,
                "material.varzeas.junco_ferruginoso": 2,
                "material.varzeas.fragmento_aprimoramento_iv": 4,
                "material.varzeas.nucleo_enfermaria_afundada": 1,
            },
        ),
        "recipe.varzeas.cisterna.peitoral_fluxo_contido": (
            ("blacksmith", 10), "Peitoral do Fluxo Contido", "Torso",
            "equipment", "Épico", 2, 10, True, 700,
            {
                "material.varzeas.ferro_de_salmoura": 14,
                "material.varzeas.soro_antigo": 6,
                "material.varzeas.catalisador_elite_iv": 4,
                "material.varzeas.fragmento_aprimoramento_iv": 12,
                "material.varzeas.nucleo_cisterna_transferencia": 1,
            },
        ),
        "recipe.varzeas.matriz.regulacao": (
            ("artificer", 10), "Regulação da Matriz", "HP",
            "enchantment", "Épico", None, 10, False, 280,
            {
                "material.varzeas.soro_antigo": 5,
                "material.varzeas.ferro_de_salmoura": 2,
                "material.varzeas.catalisador_elite_iv": 1,
                "material.varzeas.nucleo_matriz_rubra": 1,
            },
        ),
    }
    for recipe_id, (
        profession, name, slot_or_stat, output_kind, rarity, sw, level,
        creation_enabled, expected_crowns, expected_materials,
    ) in expected_specials.items():
        recipe = RECIPE_BY_ID[recipe_id]
        assert (recipe.profession_id, recipe.required_level) == profession
        assert recipe.name == name
        assert recipe.output_kind == output_kind
        assert recipe.grade == 4
        assert recipe.rarity == rarity
        if sw is not None:
            assert recipe.sw == sw
        assert recipe.required_level == level
        # Recipe discovery is gated separately from equipment/enchantment output.
        assert recipe.unlock_id == recipe_id
        assert recipe.creation_enabled is creation_enabled
        assert recipe_crown_cost(recipe, 40) == expected_crowns
        assert {
            material.material_id: material.quantity
            for material in recipe.fixed_materials
        } == expected_materials
        if recipe_id == "recipe.varzeas.matriz.regulacao":
            assert recipe.fixed_crown_cost == expected_crowns
            assert recipe.output_id == slot_or_stat
            assert enchantment_potency_for("Regulação da Matriz", "Épico", 4) == "0.30%"
        else:
            assert recipe.fixed_crown_cost is None
            assert recipe.output_slot == slot_or_stat


def test_varzeas_closure_catalog_has_all_feats_codex_and_unassigned_cosmetics():
    expected_feats = {
        "feat.varzeas.agua_de_ferro",
        "feat.varzeas.entre_os_diques",
        "feat.varzeas.o_pulso_sob_a_lama",
        "feat.varzeas.hortos_vazios",
        "feat.varzeas.nome_recuperado",
        "feat.varzeas.transferencia",
        "feat.varzeas.sem_paciente",
        "feat.varzeas.fluxo_contido",
        "feat.varzeas.quarentena_encerrada",
        "feat.varzeas.persistencia_tem_preco",
        "feat.varzeas.matriz_silenciada",
        "feat.varzeas.naturalista_das_varzeas",
        "feat.varzeas.cartografo_carmesim",
    }
    assert {
        item.achievement_id
        for item in ACHIEVEMENTS
        if item.achievement_id.startswith("feat.varzeas.")
    } == expected_feats
    assert len(VARZEAS_BASE_CREATURES) == 9
    assert len(VARZEAS_UNIQUE_EXPLORATION) == len(set(VARZEAS_UNIQUE_EXPLORATION)) == 11

    expected_cosmetics = {
        "Andarilho da Salmoura": "title",
        "Guardião dos Diques": "title",
        "Testemunha de Hemaris": "title",
        "Persistente sem Protocolo": "title",
        "Moldura Ferruginosa": "frame",
        "Moldura de Vidro Escurecido": "frame",
        "Sobrevivente das Várzeas": "appearance",
        "Capa do Porto da Salmoura": "appearance",
    }
    cosmetics = [
        item for item in COSMETICS_BY_ID.values()
        if item.cosmetic_id.startswith("cosmetic.") and ".varzeas." in item.cosmetic_id
    ]
    assert len(cosmetics) == 8
    assert {item.name: item.cosmetic_type for item in cosmetics} == expected_cosmetics
    assert all(item.achievement_id is None for item in cosmetics)
    assert all(item.origin == "Concessão não definida pela Fonte" for item in cosmetics)

    for entry_id, category in (
        ("codex.history.queda_operacional_matriz_rubra", "history"),
        ("codex.mystery.quarentena_sem_supervisao", "mysteries"),
    ):
        assert CODEX_BY_ID[entry_id].category == category
    p24 = CODEX_FRAGMENTS["codex.fragment.varzeas.p24.queda_operacional_matriz_rubra"]
    assert "responsáveis políticos" in p24.text
    assert "cadeia completa da Ruptura" in p24.text
    s24 = CODEX_FRAGMENTS["codex.fragment.varzeas.s24.quarentena_sem_supervisao"]
    assert "não punição moral" in s24.text
    assert "não atribui culpa" in s24.text


def test_p24_reward_and_s24_offer_ui_keep_choices_and_optional_gate_clear():
    p24 = VarzeasMissionView(
        uuid4(), P24_ID, "A Matriz Rubra", "choose_reward", "active", 7, 3,
        {}, "Câmara da Matriz", 40,
    )
    screen = render_varzeas_mission(p24)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert {
        "varzeas:choice:P24:3:guard",
        "varzeas:choice:P24:3:seal",
        "varzeas:choice:P24:3:reliquary",
    }.issubset(callbacks)

    s24 = VarzeasMissionView(
        uuid4(), S24_ID, "A Porta de Quarentena", "offer", None, None, 0,
        {}, "Hortos Hemaris", 40, available=True,
    )
    offer = render_varzeas_mission(s24)
    assert "S22 e P23 concluídas" in offer.text
    assert "P24" not in offer.text


def test_matrix_reservoir_windows_are_one_shot_and_capped_at_three():
    event = CombatEvent(
        sequence=0,
        round=1,
        actor="enemy",
        action="transferencia_externa",
        prepared_resolution=True,
        prepared_action_instance_id="transfer-window-1",
    )
    previous = SimpleNamespace(events=[])
    updated = SimpleNamespace(events=[event, event])
    assert VarzeasMissionService._matrix_transfer_windows_resolved(
        previous, updated
    ) == ("transfer-window-1",)

    progress = {"reservoirs_used": []}
    assert VarzeasMissionService._next_matrix_reservoir(progress) == "a"
    progress["reservoirs_used"].append("a")
    assert VarzeasMissionService._next_matrix_reservoir(progress) == "b"
    progress["reservoirs_used"].append("b")
    assert VarzeasMissionService._next_matrix_reservoir(progress) == "c"
    progress["reservoirs_used"].append("c")
    assert VarzeasMissionService._next_matrix_reservoir(progress) is None


def test_matrix_reservoir_ui_offers_contextual_action_and_shows_persisted_outcome(
    monkeypatch,
):
    hud = SimpleNamespace(text="combate", keyboard=None, parse_mode="HTML")
    monkeypatch.setitem(
        render_varzeas_mission.__globals__, "render_combat", lambda _view: hud
    )
    activity_id = uuid4()
    character_id = uuid4()
    combat = SimpleNamespace(
        prepared_action="transferencia_externa",
        prepared_action_instance_id="transfer-window-1",
        version=8,
    )
    available = VarzeasMissionView(
        character_id, P24_ID, "A Matriz Rubra", "combat", "active", 4, 2,
        {}, "Câmara da Matriz", 40, combat=combat, activity_id=activity_id,
        encounter_id=uuid4(),
    )
    screen = render_varzeas_mission(available)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    button_labels = {
        button.text
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert (
        f"varzeas:reservoir:{activity_id.hex}:8:a" in callbacks
    )
    assert "Telegraph contextual: Reservatório A." in screen.text
    assert "Resolver registra sucesso e consome o Reservatório." in screen.text
    assert "Resolver Reservatório A" in button_labels
    assert "165% ATQ" in screen.text
    assert "sem efeito numérico adicional" in screen.text

    combat.prepared_action = None
    combat.prepared_action_instance_id = None
    for outcome, expected in (
        ("resolved", "sucesso contextual registrado"),
        ("failed", "janela não resolvida; falha contextual registrada"),
    ):
        view = replace(
            available,
            progress={
                "reservoirs_used": ["a"],
                "recorded_transfer_windows": ["transfer-window-1"],
                "resolved_transfer_windows": ["transfer-window-1"],
                "reservoir_window_results": {
                    "transfer-window-1": {
                        "reservoir_id": "a",
                        "state": outcome,
                        "consumed": True,
                    }
                },
            },
        )
        screen = render_varzeas_mission(view)
        assert expected in screen.text
        assert "Reservatório A consumido" in screen.text
        assert "165% ATQ" in screen.text

    combat.prepared_action = "transferencia_externa"
    combat.prepared_action_instance_id = "transfer-window-4"
    exhausted = replace(available, progress={"reservoirs_used": ["a", "b", "c"]})
    screen = render_varzeas_mission(exhausted)
    assert "Resolver Reservatório" not in screen.text
    assert "não recebe outro Reservatório" in screen.text
    assert "165% ATQ" in screen.text
