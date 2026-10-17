from dataclasses import fields, replace
from uuid import uuid4

import pytest

from asterion.application.active_arts import (
    ActiveArtCharacterView,
    ActiveArtSlotSnapshot,
)
from asterion.bot.character_progression_ui import render_art_detail
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ART_WEAPON_REQUIREMENTS,
    ERRANTE_ART_IDS,
    SENTINEL_ART_IDS,
    VIGIA_ART_IDS,
    weapon_requirement_satisfied,
)
from asterion.domain.equipment_stats import item_snapshot_from_persisted
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_metadata import (
    COMPATIBILITY_LABELS,
    HANDEDNESS_LABELS,
    SLOT_ELIGIBILITY_LABELS,
    WEAPON_DEFINITIONS,
    WEAPON_FORM_LABELS,
    WeaponDefinition,
    WeaponMetadataStatus,
    resolve_weapon_metadata,
    weapon_definition,
    weapon_type_id_for_recipe,
    weapon_type_id_for_reward_source,
)

EXPECTED_CANONICAL_WEAPONS = (
    (
        "weapon.type.tdo.arma_caminhante",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.tdo.guarda_caminhante",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.tdo.arma_pesada_caminhante",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
    (
        "weapon.type.tdo.guarda_primeiro_selo",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.arma_vale",
        "weapon.form.axe",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.guarda_enredada",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.arma_pesada_lacos",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.vde.guarda_no_antigo",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.arma_meridiano",
        "weapon.form.spear",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.guarda_marco",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.arma_pesada_horizonte",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
    (
        "weapon.type.nareth.guarda_camara_invertida",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.guarda_referencia",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.arma_dique",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.guarda_salmoura",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.arma_pesada_transferencia",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.varzeas.guarda_transferencia",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.arma_contrapeso",
        "weapon.form.hammer",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.guarda_escora",
        "weapon.form.axe",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.arma_pesada_pedreira",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "equipment.altos.campaign.p30.guarda_contraforte_final",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "equipment.altos.special.guarda_ordem_profunda",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
)


def test_canonical_registry_matches_all_22_contract_rows():
    assert len(EXPECTED_CANONICAL_WEAPONS) == 22
    assert tuple(WEAPON_DEFINITIONS) == tuple(row[0] for row in EXPECTED_CANONICAL_WEAPONS)
    assert {
        (
            definition.weapon_type_id,
            definition.weapon_form,
            definition.handedness,
            definition.slot_eligibility,
            tuple(sorted(definition.compatibility_tags)),
        )
        for definition in WEAPON_DEFINITIONS.values()
    } == {
        (weapon_id, form, hands, slot, tuple(sorted(tags)))
        for weapon_id, form, hands, slot, tags in EXPECTED_CANONICAL_WEAPONS
    }
    assert "weapon_family" not in {entry.name for entry in fields(WeaponDefinition)}


def test_weapon_form_vocabulary_is_closed_and_invalid_values_are_rejected():
    assert set(WEAPON_FORM_LABELS) == {
        "weapon.form.sword",
        "weapon.form.dagger",
        "weapon.form.axe",
        "weapon.form.hammer",
        "weapon.form.mace",
        "weapon.form.spear",
        "weapon.form.bow",
        "weapon.form.crossbow",
        "weapon.form.staff",
        "weapon.form.rod",
    }
    assert set(HANDEDNESS_LABELS) == {"weapon.hands.one", "weapon.hands.two"}
    assert set(COMPATIBILITY_LABELS) == {
        "weapon.compat.melee",
        "weapon.compat.bow",
        "weapon.compat.crossbow",
    }
    with pytest.raises(ValueError, match="known form"):
        replace(
            WEAPON_DEFINITIONS["weapon.type.tdo.arma_caminhante"],
            weapon_form="weapon.form.unknown",
        )


def test_form_handedness_slot_and_compatibility_remain_separate_values():
    assert SLOT_ELIGIBILITY_LABELS == {
        "weapon.slot.main_only": "Principal",
        "weapon.slot.secondary_only": "Secundária",
        "weapon.slot.main_two_handed": "Duas Mãos",
    }
    main_only = WEAPON_DEFINITIONS["weapon.type.tdo.arma_caminhante"]
    secondary_only = WEAPON_DEFINITIONS["weapon.type.tdo.guarda_caminhante"]
    assert main_only.handedness == secondary_only.handedness == "weapon.hands.one"
    assert main_only.slot_eligibility == "weapon.slot.main_only"
    assert secondary_only.slot_eligibility == "weapon.slot.secondary_only"
    assert (
        replace(main_only, weapon_form="weapon.form.axe").weapon_form
        == "weapon.form.axe"
    )
    assert (
        replace(main_only, slot_eligibility="weapon.slot.secondary_only").slot_eligibility
        == "weapon.slot.secondary_only"
    )
    assert (
        replace(
            main_only,
            compatibility_tags=frozenset({"weapon.compat.bow"}),
        ).compatibility_tags
        == frozenset({"weapon.compat.bow"})
    )


def test_legacy_resolution_requires_an_exact_stable_identity():
    assert resolve_weapon_metadata(
        {"weapon_type_id": "weapon.type.tdo.arma_caminhante", "item_name": "Nome localizado"}
    ).definition == WEAPON_DEFINITIONS["weapon.type.tdo.arma_caminhante"]
    assert resolve_weapon_metadata(
        {"item_name": "Arma do Caminhante", "slot": "Principal"}
    ).status == WeaponMetadataStatus.UNMAPPED
    assert resolve_weapon_metadata(
        {"weapon_type_id": "weapon.type.unknown", "item_name": "Arco antigo"}
    ).status == WeaponMetadataStatus.UNMAPPED
    assert weapon_definition("weapon.type.unknown") is None


def test_materialization_tags_only_explicit_canonical_weapons():
    weapon = materialize_equipment(
        "canonical-weapon",
        "Comum",
        1,
        weapon_type_id="weapon.type.tdo.arma_pesada_caminhante",
    )
    assert weapon["weapon_type_id"] == "weapon.type.tdo.arma_pesada_caminhante"
    assert weapon["slot"] == "2H"
    snapshot = item_snapshot_from_persisted(
        item_instance_id="canonical-weapon",
        equipped_slot="Principal",
        item_slot="2H",
        item_level=1,
        rarity="Comum",
        payload=weapon,
    )
    assert snapshot.item_slot == "2H"

    legacy_looking_name = materialize_equipment(
        "legacy-looking-name",
        "Comum",
        1,
        forced_name="Arma do Caminhante",
        forced_slot="Principal",
    )
    assert "weapon_type_id" not in legacy_looking_name
    assert resolve_weapon_metadata(legacy_looking_name).status == WeaponMetadataStatus.UNMAPPED
    shield = materialize_equipment(
        "non-weapon",
        "Comum",
        1,
        forced_name="Escudo do Arco",
        forced_slot="Acessório",
    )
    assert "weapon_type_id" not in shield
    with pytest.raises(ValueError, match="slot does not match"):
        materialize_equipment(
            "canonical-slot-conflict",
            "Comum",
            1,
            weapon_type_id="weapon.type.tdo.arma_caminhante",
            forced_slot="Secundária",
        )


@pytest.mark.parametrize(
    ("recipe_id", "expected_id"),
    [
        ("recipe.tdo.blacksmith.walker_weapon.epico", "weapon.type.tdo.arma_caminhante"),
        ("recipe.tdo.blacksmith.walker_guard.raro", "weapon.type.tdo.guarda_caminhante"),
        (
            "recipe.tdo.blacksmith.walker_greatweapon.comum",
            "weapon.type.tdo.arma_pesada_caminhante",
        ),
        ("recipe.vde.blacksmith.vale_weapon.raro", "weapon.type.vde.arma_vale"),
        ("recipe.vde.blacksmith.entwined_guard.raro", "weapon.type.vde.guarda_enredada"),
        ("recipe.vde.blacksmith.bonds_greatweapon.raro", "weapon.type.vde.arma_pesada_lacos"),
        ("recipe.nareth.blacksmith.meridian_weapon.raro", "weapon.type.nareth.arma_meridiano"),
        ("recipe.nareth.blacksmith.marker_guard.raro", "weapon.type.nareth.guarda_marco"),
        (
            "recipe.nareth.blacksmith.horizon_greatweapon.raro",
            "weapon.type.nareth.arma_pesada_horizonte",
        ),
        ("recipe.varzeas.blacksmith.dike_weapon.raro", "weapon.type.varzeas.arma_dique"),
        ("recipe.varzeas.blacksmith.brine_guard.raro", "weapon.type.varzeas.guarda_salmoura"),
        (
            "recipe.varzeas.blacksmith.transfer_greatweapon.raro",
            "weapon.type.varzeas.arma_pesada_transferencia",
        ),
        ("recipe.tdo.galerias.guarda_primeiro_selo", "weapon.type.tdo.guarda_primeiro_selo"),
        ("recipe.vde.santuario.guarda_no_antigo", "weapon.type.vde.guarda_no_antigo"),
        ("recipe.nareth.observatorio.guarda_referencia", "weapon.type.nareth.guarda_referencia"),
    ],
)
def test_exact_current_recipe_ids_resolve_to_canonical_weapon(recipe_id, expected_id):
    assert weapon_type_id_for_recipe(recipe_id) == expected_id


def test_reward_source_mapping_is_exact_and_unmapped_sources_stay_unmapped():
    assert weapon_type_id_for_reward_source(
        "p18.o_arconte_invertido:equipment:1"
    ) == "weapon.type.nareth.guarda_camara_invertida"
    assert weapon_type_id_for_reward_source(
        "p24.a_matriz_rubra:equipment:guard"
    ) == "weapon.type.varzeas.guarda_transferencia"
    assert weapon_type_id_for_reward_source(
        "p24.a_matriz_rubra:equipment:other"
    ) is None


def test_active_art_weapon_requirements_match_the_current_explicit_matrix():
    melee = frozenset({"weapon.compat.melee"})
    ranged = frozenset({"weapon.compat.bow", "weapon.compat.crossbow"})
    assert ART_WEAPON_REQUIREMENTS == {
        SENTINEL_ART_IDS["golpe_de_guarda"]: melee,
        SENTINEL_ART_IDS["quebra_postura"]: melee,
        SENTINEL_ART_IDS["impacto_resoluto"]: melee,
        ERRANTE_ART_IDS["corte_veloz"]: melee,
        ERRANTE_ART_IDS["ferida_profunda"]: melee,
        ERRANTE_ART_IDS["golpe_oportuno"]: melee,
        VIGIA_ART_IDS["disparo_preciso"]: ranged,
        VIGIA_ART_IDS["marca_da_presa"]: ranged,
        VIGIA_ART_IDS["saraivada"]: ranged,
    }
    sentinel_art = ACTIVE_ART_DEFINITIONS[SENTINEL_ART_IDS["golpe_de_guarda"]]
    vigia_art = ACTIVE_ART_DEFINITIONS[VIGIA_ART_IDS["disparo_preciso"]]
    defensive_art = ACTIVE_ART_DEFINITIONS[SENTINEL_ART_IDS["muralha_breve"]]
    assert weapon_requirement_satisfied(sentinel_art, melee)
    assert not weapon_requirement_satisfied(sentinel_art, ranged)
    assert weapon_requirement_satisfied(vigia_art, frozenset({"weapon.compat.bow"}))
    assert weapon_requirement_satisfied(vigia_art, frozenset({"weapon.compat.crossbow"}))
    assert not weapon_requirement_satisfied(vigia_art, melee)
    assert not weapon_requirement_satisfied(vigia_art, frozenset())
    assert weapon_requirement_satisfied(defensive_art, frozenset())


def test_weapon_incompatible_art_detail_explains_requirement_without_equip_action():
    art_id = VIGIA_ART_IDS["disparo_preciso"]
    view = ActiveArtCharacterView(
        character_id=uuid4(),
        character_name="Teste",
        character_class="vigia",
        level=10,
        selected_path=None,
        combat_configuration_version=0,
        slots=(ActiveArtSlotSnapshot(1, art_id),),
        available_art_ids=(art_id,),
        foreground=False,
        weapon_incompatible_art_ids=(art_id,),
    )
    detail = render_art_detail(view, art_id)

    assert "Arco ou Besta compatível" in detail.text
    assert "equipe uma arma compatível" in detail.text
    buttons = [
        button.text
        for row in detail.keyboard.inline_keyboard
        for button in row
    ]
    assert "Equipar Arte" not in buttons
    assert "Desequipar Arte" in buttons

    unconfigured = render_art_detail(replace(view, slots=()), art_id)
    unconfigured_buttons = [
        button.text
        for row in unconfigured.keyboard.inline_keyboard
        for button in row
    ]
    assert "Equipar Arte" not in unconfigured_buttons
