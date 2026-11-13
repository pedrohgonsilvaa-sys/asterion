"""Canonical weapon metadata catalog from the approved global contract."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

WEAPON_FORM_LABELS = {
    "weapon.form.sword": "Espada",
    "weapon.form.dagger": "Adaga",
    "weapon.form.axe": "Machado",
    "weapon.form.hammer": "Martelo",
    "weapon.form.mace": "Maça",
    "weapon.form.spear": "Lança",
    "weapon.form.bow": "Arco",
    "weapon.form.crossbow": "Besta",
    "weapon.form.staff": "Cajado",
    # v1.0.0 Proficiências catalog: identities the previous forms could not describe.
    # "weapon.form.rod" (Bastão) was consolidated into Cajado; no template used it.
    "weapon.form.chakram": "Chakram",
    "weapon.form.double_blade": "Lâmina Dupla",
    "weapon.form.halberd": "Alabarda",
    "weapon.form.javelin": "Azagaia",
    "weapon.form.scepter": "Cetro",
    "weapon.form.orb": "Orbe",
    "weapon.form.shield": "Escudo",
}
HANDEDNESS_LABELS = {
    "weapon.hands.one": "1 mão",
    "weapon.hands.two": "2 mãos",
}
SLOT_ELIGIBILITY_TO_ITEM_SLOT = {
    "weapon.slot.main_only": "Principal",
    "weapon.slot.secondary_only": "Secundária",
    "weapon.slot.main_two_handed": "2H",
}
SLOT_ELIGIBILITY_LABELS = {
    "weapon.slot.main_only": "Principal",
    "weapon.slot.secondary_only": "Secundária",
    "weapon.slot.main_two_handed": "Duas Mãos",
}
COMPATIBILITY_LABELS = {
    "weapon.compat.melee": "Corpo a corpo",
    "weapon.compat.bow": "Arco",
    "weapon.compat.crossbow": "Besta",
}
_VALID_FORMS = frozenset(WEAPON_FORM_LABELS)
_VALID_HANDS = frozenset(HANDEDNESS_LABELS)
_VALID_SLOTS = frozenset(SLOT_ELIGIBILITY_TO_ITEM_SLOT)
_VALID_TAGS = frozenset(COMPATIBILITY_LABELS)
VALID_COMPATIBILITY_TAGS = _VALID_TAGS


@dataclass(frozen=True, slots=True)
class WeaponDefinition:
    weapon_type_id: str
    item_name: str
    weapon_form: str
    handedness: str
    slot_eligibility: str
    compatibility_tags: frozenset[str]

    def __post_init__(self) -> None:
        if not self.weapon_type_id or self.weapon_type_id not in _CANONICAL_WEAPON_IDS:
            raise ValueError("Unknown canonical weapon type ID.")
        if not self.item_name or self.weapon_form not in _VALID_FORMS:
            raise ValueError("Canonical weapons require a known form and item name.")
        if self.handedness not in _VALID_HANDS or self.slot_eligibility not in _VALID_SLOTS:
            raise ValueError("Canonical weapons require explicit hands and slot eligibility.")
        # An empty set is an explicit declaration: the item satisfies no Art
        # weapon requirement (Focos Arcanos and Escudo in the v1.0.0 catalog).
        if not isinstance(self.compatibility_tags, frozenset) or not (
            self.compatibility_tags <= _VALID_TAGS
        ):
            raise ValueError("Canonical weapons require explicit compatibility tags.")
        expected_item_slot = SLOT_ELIGIBILITY_TO_ITEM_SLOT[self.slot_eligibility]
        if self.handedness == "weapon.hands.two" and expected_item_slot != "2H":
            raise ValueError("Two-handed weapons must declare the two-handed main slot.")
        if self.handedness == "weapon.hands.one" and expected_item_slot == "2H":
            raise ValueError("One-handed weapons cannot declare the two-handed main slot.")

    @property
    def form_label(self) -> str:
        return WEAPON_FORM_LABELS[self.weapon_form]

    @property
    def handedness_label(self) -> str:
        return HANDEDNESS_LABELS[self.handedness]

    @property
    def slot_label(self) -> str:
        return SLOT_ELIGIBILITY_LABELS[self.slot_eligibility]

    @property
    def persisted_item_slot(self) -> str:
        return SLOT_ELIGIBILITY_TO_ITEM_SLOT[self.slot_eligibility]

    @property
    def compatibility_label(self) -> str:
        return ", ".join(
            COMPATIBILITY_LABELS[tag]
            for tag in ("weapon.compat.melee", "weapon.compat.bow", "weapon.compat.crossbow")
            if tag in self.compatibility_tags
        )


_CANONICAL_WEAPON_ROWS = (
    (
        "weapon.type.tdo.arma_caminhante",
        "Arma do Caminhante",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.tdo.guarda_caminhante",
        "Guarda do Caminhante",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.tdo.arma_pesada_caminhante",
        "Arma Pesada do Caminhante",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
    (
        "weapon.type.tdo.guarda_primeiro_selo",
        "Guarda do Primeiro Selo",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.arma_vale",
        "Arma do Vale",
        "weapon.form.axe",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.guarda_enredada",
        "Guarda Enredada",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.vde.arma_pesada_lacos",
        "Arma Pesada dos Laços",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.vde.guarda_no_antigo",
        "Guarda do Nó Antigo",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.arma_meridiano",
        "Arma do Meridiano",
        "weapon.form.spear",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.guarda_marco",
        "Guarda de Marco",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.arma_pesada_horizonte",
        "Arma Pesada do Horizonte",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
    (
        "weapon.type.nareth.guarda_camara_invertida",
        "Guarda da Câmara Invertida",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.nareth.guarda_referencia",
        "Guarda da Referência",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.arma_dique",
        "Arma do Dique",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.guarda_salmoura",
        "Guarda de Salmoura",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.varzeas.arma_pesada_transferencia",
        "Arma Pesada de Transferência",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.varzeas.guarda_transferencia",
        "Guarda de Transferência",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.arma_contrapeso",
        "Arma do Contrapeso",
        "weapon.form.hammer",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.guarda_escora",
        "Guarda de Escora",
        "weapon.form.axe",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.altos.arma_pesada_pedreira",
        "Arma Pesada da Pedreira",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "equipment.altos.campaign.p30.guarda_contraforte_final",
        "Guarda do Contraforte Final",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "equipment.altos.special.guarda_ordem_profunda",
        "Guarda da Ordem Profunda",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "equipment.confins.campaign.p36.guarda_ultimo_protocolo",
        "Guarda do Último Protocolo",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "equipment.confins.special.guarda_duas_versoes",
        "Guarda das Duas Versões",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    # Confins do Véu §19.2 blacksmith weapons (contract v1.1.0 §9.7); no recipe yet.
    (
        "craft.confins.ferreiro.principal.lamina_baliza",
        "Lâmina de Baliza",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "craft.confins.ferreiro.secundaria.guarda_marcha",
        "Guarda da Marcha",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        ("weapon.compat.melee",),
    ),
    (
        "craft.confins.ferreiro.2h.arco_retorno",
        "Arco do Retorno",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
)
# v1.0.0 base catalog (Proficiências): one template per concrete identity. Starting
# equipment uses six of them; none is in a drop pool. Focos Arcanos and Escudo
# declare no Art compatibility tag.
_BASE_WEAPON_ROWS = (
    (
        "weapon.type.base.espada",
        "Espada",
        "weapon.form.sword",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.espada_de_guerra",
        "Espada de Guerra",
        "weapon.form.sword",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.adaga",
        "Adaga",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.adaga_de_arremesso",
        "Adaga de Arremesso",
        "weapon.form.dagger",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.chakram",
        "Chakram",
        "weapon.form.chakram",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.lamina_dupla",
        "Lâmina Dupla",
        "weapon.form.double_blade",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.maca",
        "Maça",
        "weapon.form.mace",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.martelo_de_guerra",
        "Martelo de Guerra",
        "weapon.form.hammer",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.machado",
        "Machado",
        "weapon.form.axe",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.machado_de_guerra",
        "Machado de Guerra",
        "weapon.form.axe",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.lanca",
        "Lança",
        "weapon.form.spear",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.alabarda",
        "Alabarda",
        "weapon.form.halberd",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.azagaia",
        "Azagaia",
        "weapon.form.javelin",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.melee",),
    ),
    (
        "weapon.type.base.arco",
        "Arco",
        "weapon.form.bow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.bow",),
    ),
    (
        "weapon.type.base.besta_de_mao",
        "Besta de Mão",
        "weapon.form.crossbow",
        "weapon.hands.one",
        "weapon.slot.main_only",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.base.besta_pesada",
        "Besta Pesada",
        "weapon.form.crossbow",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        ("weapon.compat.crossbow",),
    ),
    (
        "weapon.type.base.cetro",
        "Cetro",
        "weapon.form.scepter",
        "weapon.hands.one",
        "weapon.slot.main_only",
        (),
    ),
    (
        "weapon.type.base.orbe",
        "Orbe",
        "weapon.form.orb",
        "weapon.hands.one",
        "weapon.slot.main_only",
        (),
    ),
    (
        "weapon.type.base.cajado",
        "Cajado",
        "weapon.form.staff",
        "weapon.hands.two",
        "weapon.slot.main_two_handed",
        (),
    ),
    (
        "weapon.type.base.escudo",
        "Escudo",
        "weapon.form.shield",
        "weapon.hands.one",
        "weapon.slot.secondary_only",
        (),
    ),
)
_ALL_WEAPON_ROWS = (*_CANONICAL_WEAPON_ROWS, *_BASE_WEAPON_ROWS)
_CANONICAL_WEAPON_IDS = frozenset(row[0] for row in _ALL_WEAPON_ROWS)
WEAPON_DEFINITIONS = MappingProxyType(
    {
        weapon_id: WeaponDefinition(
            weapon_id,
            item_name,
            weapon_form,
            handedness,
            slot_eligibility,
            frozenset(compatibility_tags),
        )
        for (
            weapon_id,
            item_name,
            weapon_form,
            handedness,
            slot_eligibility,
            compatibility_tags,
        ) in _ALL_WEAPON_ROWS
    }
)


class WeaponMetadataStatus(StrEnum):
    CANONICAL = "canonical"
    UNMAPPED = "unmapped"


@dataclass(frozen=True, slots=True)
class WeaponMetadataResolution:
    status: WeaponMetadataStatus
    definition: WeaponDefinition | None = None


def weapon_definition(weapon_type_id: str | None) -> WeaponDefinition | None:
    if not isinstance(weapon_type_id, str):
        return None
    return WEAPON_DEFINITIONS.get(weapon_type_id)


def resolve_weapon_metadata(payload: Mapping[str, Any] | None) -> WeaponMetadataResolution:
    """Resolve only by stable canonical identity; never infer from display data."""
    raw_id = payload.get("weapon_type_id") if isinstance(payload, Mapping) else None
    definition = weapon_definition(raw_id)
    if definition is None:
        return WeaponMetadataResolution(WeaponMetadataStatus.UNMAPPED)
    return WeaponMetadataResolution(WeaponMetadataStatus.CANONICAL, definition)


_RECIPE_PREFIX_TO_WEAPON_ID = {
    "recipe.tdo.blacksmith.walker_weapon": "weapon.type.tdo.arma_caminhante",
    "recipe.tdo.blacksmith.walker_guard": "weapon.type.tdo.guarda_caminhante",
    "recipe.tdo.blacksmith.walker_greatweapon": "weapon.type.tdo.arma_pesada_caminhante",
    "recipe.vde.blacksmith.vale_weapon": "weapon.type.vde.arma_vale",
    "recipe.vde.blacksmith.entwined_guard": "weapon.type.vde.guarda_enredada",
    "recipe.vde.blacksmith.bonds_greatweapon": "weapon.type.vde.arma_pesada_lacos",
    "recipe.nareth.blacksmith.meridian_weapon": "weapon.type.nareth.arma_meridiano",
    "recipe.nareth.blacksmith.marker_guard": "weapon.type.nareth.guarda_marco",
    "recipe.nareth.blacksmith.horizon_greatweapon": (
        "weapon.type.nareth.arma_pesada_horizonte"
    ),
    "recipe.varzeas.blacksmith.dike_weapon": "weapon.type.varzeas.arma_dique",
    "recipe.varzeas.blacksmith.brine_guard": "weapon.type.varzeas.guarda_salmoura",
    "recipe.varzeas.blacksmith.transfer_greatweapon": (
        "weapon.type.varzeas.arma_pesada_transferencia"
    ),
}
_EXACT_RECIPE_TO_WEAPON_ID = {
    "recipe.tdo.galerias.guarda_primeiro_selo": "weapon.type.tdo.guarda_primeiro_selo",
    "recipe.vde.santuario.guarda_no_antigo": "weapon.type.vde.guarda_no_antigo",
    "recipe.nareth.observatorio.guarda_referencia": "weapon.type.nareth.guarda_referencia",
    "recipe.altos.bastilha.guarda_ordem_profunda": (
        "equipment.altos.special.guarda_ordem_profunda"
    ),
    "recipe.confins.contradicoes.guarda_duas_versoes": (
        "equipment.confins.special.guarda_duas_versoes"
    ),
}


def weapon_type_id_for_recipe(recipe_id: str | None) -> str | None:
    """Bind explicit current recipe IDs to canonical weapon identities."""
    if not isinstance(recipe_id, str):
        return None
    exact = _EXACT_RECIPE_TO_WEAPON_ID.get(recipe_id)
    if exact is not None:
        return exact
    for suffix in ("comum", "raro", "epico"):
        prefix = recipe_id.removesuffix(f".{suffix}")
        weapon_id = _RECIPE_PREFIX_TO_WEAPON_ID.get(prefix)
        if weapon_id is not None:
            return weapon_id
    return None


_REWARD_SOURCE_TO_WEAPON_ID = {
    "p18.o_arconte_invertido:equipment:1": "weapon.type.nareth.guarda_camara_invertida",
    "p24.a_matriz_rubra:equipment:guard": "weapon.type.varzeas.guarda_transferencia",
}


def weapon_type_id_for_reward_source(source_key: str | None) -> str | None:
    if not isinstance(source_key, str):
        return None
    return _REWARD_SOURCE_TO_WEAPON_ID.get(source_key)
