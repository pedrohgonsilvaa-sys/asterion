"""Proficiências de Armas v1.0.0: pure registry rules (no database)."""

import inspect

import pytest

import asterion.domain.weapon_proficiency as proficiency_module
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ART_WEAPON_REQUIREMENTS,
    weapon_requirement_satisfied,
)
from asterion.domain.road import EQUIPMENT_CATALOG, materialize_equipment
from asterion.domain.weapon_metadata import WEAPON_DEFINITIONS
from asterion.domain.weapon_proficiency import (
    BASE_WEAPON_TYPE_IDS,
    CLASS_WEAPON_WHITELIST,
    FAMILY_LABELS,
    IDENTITY_FAMILY,
    INITIAL_PROFICIENCY,
    STARTING_WEAPON_TYPE_IDS,
    WEAPON_IDENTITIES,
    WEAPON_TYPE_IDENTITIES,
    ProficiencyFamily,
    WeaponIdentity,
    acquisition_terms,
    class_allows_identity,
    learnable_families,
    weapon_identity_for_type,
)

F = ProficiencyFamily
I = WeaponIdentity  # noqa: E741

# Spec §9, written out independently of the implementation.
SPEC_MATRIX = {
    "sentinela": {
        "Espada", "Espada de Guerra", "Adaga", "Adaga de Arremesso", "Chakram",
        "Lâmina Dupla", "Maça", "Martelo de Guerra", "Machado", "Machado de Guerra",
        "Lança", "Alabarda", "Azagaia", "Escudo",
    },
    "errante": {
        "Espada", "Adaga", "Adaga de Arremesso", "Chakram", "Lâmina Dupla",
        "Besta de Mão", "Machado",
    },
    "vigia": {
        "Espada", "Adaga", "Adaga de Arremesso", "Chakram", "Arco", "Besta de Mão",
        "Besta Pesada",
    },
    "tecelao": {"Cajado", "Orbe", "Cetro", "Espada", "Adaga"},
    "oraculo": {"Cajado", "Orbe", "Cetro", "Maça", "Adaga", "Escudo"},
    "luminar": {"Cajado", "Orbe", "Cetro", "Espada", "Maça", "Machado", "Escudo"},
}
SPEC_CATALOG = {
    "Espadas": {("Espada", "1H"), ("Espada de Guerra", "2H")},
    "Lâminas": {
        ("Adaga", "1H"), ("Adaga de Arremesso", "1H"), ("Chakram", "1H"),
        ("Lâmina Dupla", "2H"),
    },
    "Contundentes": {("Maça", "1H"), ("Martelo de Guerra", "2H")},
    "Machados": {("Machado", "1H"), ("Machado de Guerra", "2H")},
    "Hastes": {("Lança", "1H"), ("Alabarda", "2H"), ("Azagaia", "1H")},
    "Arcos": {("Arco", "2H")},
    "Bestas": {("Besta de Mão", "1H"), ("Besta Pesada", "2H")},
    "Focos Arcanos": {("Cetro", "1H"), ("Orbe", "1H"), ("Cajado", "2H")},
    "Escudo": {("Escudo", "1H")},
}


def test_families_and_catalog_match_the_spec_exactly():
    assert [FAMILY_LABELS[family] for family in F] == list(SPEC_CATALOG)
    hands = {"weapon.hands.one": "1H", "weapon.hands.two": "2H"}
    catalog = {
        FAMILY_LABELS[family]: {
            (entry.label, hands[entry.handedness])
            for entry in WEAPON_IDENTITIES.values()
            if entry.family == family
        }
        for family in F
    }
    assert catalog == SPEC_CATALOG


def test_class_matrix_matches_the_spec_exactly():
    assert {
        character_class: {WEAPON_IDENTITIES[identity].label for identity in allowed}
        for character_class, allowed in CLASS_WEAPON_WHITELIST.items()
    } == SPEC_MATRIX


def test_removed_catalog_names_do_not_exist_as_identities_or_base_templates():
    removed = {
        "Espada Longa", "Espada Bastarda", "Faca de Combate", "Kukri", "Mangual",
        "Glaive", "Arco Curto", "Arco de Guerra", "Bastão", "Varinha", "Grimório",
        "Adaga Cerimonial", "Arremesso",
    }
    labels = {entry.label for entry in WEAPON_IDENTITIES.values()}
    assert not labels & removed
    assert not {FAMILY_LABELS[family] for family in F} & removed
    assert not {
        WEAPON_DEFINITIONS[weapon_type_id].item_name
        for weapon_type_id in BASE_WEAPON_TYPE_IDS.values()
    } & removed


def test_every_published_weapon_has_an_explicit_identity_with_matching_hands():
    assert set(WEAPON_TYPE_IDENTITIES) == set(WEAPON_DEFINITIONS)
    for weapon_type_id, definition in WEAPON_DEFINITIONS.items():
        identity = weapon_identity_for_type(weapon_type_id)
        assert identity is not None, weapon_type_id
        assert WEAPON_IDENTITIES[identity].handedness == definition.handedness, weapon_type_id


def test_base_templates_are_one_per_identity_and_never_dropped():
    assert set(BASE_WEAPON_TYPE_IDS) == set(WeaponIdentity)
    for identity, weapon_type_id in BASE_WEAPON_TYPE_IDS.items():
        assert WEAPON_DEFINITIONS[weapon_type_id].item_name == WEAPON_IDENTITIES[identity].label
    dropped = {template[2] for template in EQUIPMENT_CATALOG if template[2]}
    assert not dropped & set(BASE_WEAPON_TYPE_IDS.values())
    shield = WEAPON_DEFINITIONS[BASE_WEAPON_TYPE_IDS[I.SHIELD]]
    assert shield.slot_eligibility == "weapon.slot.secondary_only"


def test_identity_is_never_inferred_from_form_or_name():
    source = inspect.getsource(proficiency_module)
    assert ".weapon_form" not in source
    assert ".item_name" not in source
    # Same form, different identities: forms stay descriptive only.
    assert weapon_identity_for_type("weapon.type.base.espada") == I.SWORD
    assert weapon_identity_for_type("weapon.type.base.espada_de_guerra") == I.WAR_SWORD
    assert weapon_identity_for_type("weapon.type.altos.arma_contrapeso") == I.MACE
    assert weapon_identity_for_type("Espada") is None
    assert weapon_identity_for_type(None) is None


@pytest.mark.parametrize(
    ("character_class", "identity", "allowed"),
    [
        ("sentinela", I.WAR_SWORD, True),
        ("errante", I.SWORD, True),
        ("errante", I.WAR_SWORD, False),
        ("vigia", I.HEAVY_CROSSBOW, True),
        ("tecelao", I.SWORD, True),
        ("oraculo", I.SHIELD, True),
        ("oraculo", I.SWORD, False),
        ("luminar", I.AXE, True),
        ("luminar", I.WAR_AXE, False),
        (None, I.SWORD, False),
    ],
)
def test_mandatory_matrix_cases(character_class, identity, allowed):
    assert class_allows_identity(character_class, identity) is allowed


def test_learnable_families_need_at_least_one_usable_identity():
    assert learnable_families("errante") == (F.SWORDS, F.BLADES, F.AXES, F.CROSSBOWS)
    assert learnable_families("vigia") == (F.SWORDS, F.BLADES, F.BOWS, F.CROSSBOWS)
    assert learnable_families("tecelao") == (F.SWORDS, F.BLADES, F.ARCANE_FOCI)
    assert learnable_families("oraculo") == (F.BLADES, F.BLUNT, F.ARCANE_FOCI, F.SHIELD)
    assert learnable_families("luminar") == (
        F.SWORDS, F.BLUNT, F.AXES, F.ARCANE_FOCI, F.SHIELD,
    )
    assert learnable_families("sentinela") == (
        F.SWORDS, F.BLADES, F.BLUNT, F.AXES, F.POLEARMS, F.SHIELD,
    )
    assert learnable_families(None) == ()
    for character_class, families in (
        (character_class, learnable_families(character_class))
        for character_class in CLASS_WEAPON_WHITELIST
    ):
        for family in families:
            assert any(
                IDENTITY_FAMILY[identity] == family
                for identity in CLASS_WEAPON_WHITELIST[character_class]
            )


def test_acquisition_progression_and_costs_have_no_cap():
    assert [
        (terms.min_level, terms.cost_crowns)
        for terms in map(acquisition_terms, range(1, 10))
    ] == [
        (1, 0), (10, 1_000), (20, 2_500), (30, 5_000), (40, 10_000),
        (50, 20_000), (50, 20_000), (50, 20_000), (50, 20_000),
    ]
    with pytest.raises(ValueError):
        acquisition_terms(0)


def test_initial_proficiency_and_starting_weapon_are_coherent_per_class():
    assert dict(INITIAL_PROFICIENCY) == {
        "sentinela": F.SWORDS,
        "errante": F.BLADES,
        "vigia": F.BOWS,
        "tecelao": F.ARCANE_FOCI,
        "oraculo": F.ARCANE_FOCI,
        "luminar": F.ARCANE_FOCI,
    }
    expected = {
        "sentinela": "Espada",
        "errante": "Adaga",
        "vigia": "Arco",
        "tecelao": "Cajado",
        "oraculo": "Orbe",
        "luminar": "Cetro",
    }
    for character_class, weapon_type_id in STARTING_WEAPON_TYPE_IDS.items():
        identity = weapon_identity_for_type(weapon_type_id)
        assert WEAPON_IDENTITIES[identity].label == expected[character_class]
        assert IDENTITY_FAMILY[identity] == INITIAL_PROFICIENCY[character_class]
        assert class_allows_identity(character_class, identity)
        payload = materialize_equipment("seed", "Comum", 1, weapon_type_id=weapon_type_id)
        assert payload["enhancement"] == 0
        assert payload["rune"] is None and payload["enchantment"] is None
        assert payload["secondaries"] == []


def test_foci_and_shield_satisfy_no_art_requirement_and_none_arts_stay_free():
    for identity in (I.SCEPTER, I.ORB, I.STAFF, I.SHIELD):
        tags = WEAPON_DEFINITIONS[BASE_WEAPON_TYPE_IDS[identity]].compatibility_tags
        assert tags == frozenset()
    melee = WEAPON_DEFINITIONS[BASE_WEAPON_TYPE_IDS[I.CHAKRAM]].compatibility_tags
    assert melee == frozenset({"weapon.compat.melee"})
    for definition in ACTIVE_ART_DEFINITIONS.values():
        if not definition.weapon_requirement:
            assert weapon_requirement_satisfied(definition, frozenset())
        else:
            assert not weapon_requirement_satisfied(definition, frozenset())
    # Proficiência does not touch the published Art requirements.
    assert all(
        requirement <= {"weapon.compat.melee", "weapon.compat.bow", "weapon.compat.crossbow"}
        for requirement in ART_WEAPON_REQUIREMENTS.values()
    )


def test_shield_uses_the_gdd_shield_core_and_no_inherent_block():
    payload = materialize_equipment("shield", "Comum", 60, weapon_type_id="weapon.type.base.escudo")
    assert payload["slot"] == "Secundária"
    assert payload["core"] == {"HP": 25, "DEF": 10}
    weapon = materialize_equipment("dagger", "Comum", 60, weapon_type_id="weapon.type.base.adaga")
    assert weapon["core"] == {"ATQ": 25}
