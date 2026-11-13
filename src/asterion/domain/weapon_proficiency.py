"""Proficiências de Armas: explicit registry kept apart from the weapon metadata contract.

Source: ASTERION_ESPECIFICACAO_FINAL_PROFICIENCIAS_EQUIPAMENTO v1.0.0.

A Proficiência is only a permanent equip authorization. It grants no attribute,
damage, cooldown, critical, block, dodge, accuracy, range or any other combat
effect. Nothing here is inferred from ``weapon_form``, item names or visuals:

* every published weapon template is bound to one concrete catalog identity by
  ``WEAPON_TYPE_IDENTITIES`` (exact ``weapon_type_id``);
* every identity belongs to exactly one family (``IDENTITY_FAMILY``);
* every Classe has an explicit whitelist of concrete identities
  (``CLASS_WEAPON_WHITELIST``). A family never widens that whitelist.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class ProficiencyFamily(StrEnum):
    SWORDS = "proficiency.swords"
    BLADES = "proficiency.blades"
    BLUNT = "proficiency.blunt"
    AXES = "proficiency.axes"
    POLEARMS = "proficiency.polearms"
    BOWS = "proficiency.bows"
    CROSSBOWS = "proficiency.crossbows"
    ARCANE_FOCI = "proficiency.arcane_foci"
    SHIELD = "proficiency.shield"


FAMILY_LABELS = MappingProxyType(
    {
        ProficiencyFamily.SWORDS: "Espadas",
        ProficiencyFamily.BLADES: "Lâminas",
        ProficiencyFamily.BLUNT: "Contundentes",
        ProficiencyFamily.AXES: "Machados",
        ProficiencyFamily.POLEARMS: "Hastes",
        ProficiencyFamily.BOWS: "Arcos",
        ProficiencyFamily.CROSSBOWS: "Bestas",
        ProficiencyFamily.ARCANE_FOCI: "Focos Arcanos",
        ProficiencyFamily.SHIELD: "Escudo",
    }
)
FAMILY_ORDER = tuple(ProficiencyFamily)


class WeaponIdentity(StrEnum):
    SWORD = "weapon.identity.sword"
    WAR_SWORD = "weapon.identity.war_sword"
    DAGGER = "weapon.identity.dagger"
    THROWING_DAGGER = "weapon.identity.throwing_dagger"
    CHAKRAM = "weapon.identity.chakram"
    DOUBLE_BLADE = "weapon.identity.double_blade"
    MACE = "weapon.identity.mace"
    WAR_HAMMER = "weapon.identity.war_hammer"
    AXE = "weapon.identity.axe"
    WAR_AXE = "weapon.identity.war_axe"
    SPEAR = "weapon.identity.spear"
    HALBERD = "weapon.identity.halberd"
    JAVELIN = "weapon.identity.javelin"
    BOW = "weapon.identity.bow"
    HAND_CROSSBOW = "weapon.identity.hand_crossbow"
    HEAVY_CROSSBOW = "weapon.identity.heavy_crossbow"
    SCEPTER = "weapon.identity.scepter"
    ORB = "weapon.identity.orb"
    STAFF = "weapon.identity.staff"
    SHIELD = "weapon.identity.shield"


@dataclass(frozen=True, slots=True)
class WeaponIdentityDefinition:
    identity: WeaponIdentity
    label: str
    family: ProficiencyFamily
    handedness: str


_ONE = "weapon.hands.one"
_TWO = "weapon.hands.two"
_IDENTITY_ROWS = (
    (WeaponIdentity.SWORD, "Espada", ProficiencyFamily.SWORDS, _ONE),
    (WeaponIdentity.WAR_SWORD, "Espada de Guerra", ProficiencyFamily.SWORDS, _TWO),
    (WeaponIdentity.DAGGER, "Adaga", ProficiencyFamily.BLADES, _ONE),
    (WeaponIdentity.THROWING_DAGGER, "Adaga de Arremesso", ProficiencyFamily.BLADES, _ONE),
    (WeaponIdentity.CHAKRAM, "Chakram", ProficiencyFamily.BLADES, _ONE),
    (WeaponIdentity.DOUBLE_BLADE, "Lâmina Dupla", ProficiencyFamily.BLADES, _TWO),
    (WeaponIdentity.MACE, "Maça", ProficiencyFamily.BLUNT, _ONE),
    (WeaponIdentity.WAR_HAMMER, "Martelo de Guerra", ProficiencyFamily.BLUNT, _TWO),
    (WeaponIdentity.AXE, "Machado", ProficiencyFamily.AXES, _ONE),
    (WeaponIdentity.WAR_AXE, "Machado de Guerra", ProficiencyFamily.AXES, _TWO),
    (WeaponIdentity.SPEAR, "Lança", ProficiencyFamily.POLEARMS, _ONE),
    (WeaponIdentity.HALBERD, "Alabarda", ProficiencyFamily.POLEARMS, _TWO),
    (WeaponIdentity.JAVELIN, "Azagaia", ProficiencyFamily.POLEARMS, _ONE),
    (WeaponIdentity.BOW, "Arco", ProficiencyFamily.BOWS, _TWO),
    (WeaponIdentity.HAND_CROSSBOW, "Besta de Mão", ProficiencyFamily.CROSSBOWS, _ONE),
    (WeaponIdentity.HEAVY_CROSSBOW, "Besta Pesada", ProficiencyFamily.CROSSBOWS, _TWO),
    (WeaponIdentity.SCEPTER, "Cetro", ProficiencyFamily.ARCANE_FOCI, _ONE),
    (WeaponIdentity.ORB, "Orbe", ProficiencyFamily.ARCANE_FOCI, _ONE),
    (WeaponIdentity.STAFF, "Cajado", ProficiencyFamily.ARCANE_FOCI, _TWO),
    (WeaponIdentity.SHIELD, "Escudo", ProficiencyFamily.SHIELD, _ONE),
)
WEAPON_IDENTITIES = MappingProxyType(
    {row[0]: WeaponIdentityDefinition(*row) for row in _IDENTITY_ROWS}
)
IDENTITY_FAMILY = MappingProxyType(
    {identity: definition.family for identity, definition in WEAPON_IDENTITIES.items()}
)

_I = WeaponIdentity
CLASS_WEAPON_WHITELIST = MappingProxyType(
    {
        "sentinela": frozenset(
            {
                _I.SWORD, _I.WAR_SWORD,
                _I.DAGGER, _I.THROWING_DAGGER, _I.CHAKRAM, _I.DOUBLE_BLADE,
                _I.MACE, _I.WAR_HAMMER,
                _I.AXE, _I.WAR_AXE,
                _I.SPEAR, _I.HALBERD, _I.JAVELIN,
                _I.SHIELD,
            }
        ),
        "errante": frozenset(
            {
                _I.SWORD,
                _I.DAGGER, _I.THROWING_DAGGER, _I.CHAKRAM, _I.DOUBLE_BLADE,
                _I.HAND_CROSSBOW,
                _I.AXE,
            }
        ),
        "vigia": frozenset(
            {
                _I.SWORD,
                _I.DAGGER, _I.THROWING_DAGGER, _I.CHAKRAM,
                _I.BOW,
                _I.HAND_CROSSBOW, _I.HEAVY_CROSSBOW,
            }
        ),
        "tecelao": frozenset({_I.STAFF, _I.ORB, _I.SCEPTER, _I.SWORD, _I.DAGGER}),
        "oraculo": frozenset({_I.STAFF, _I.ORB, _I.SCEPTER, _I.MACE, _I.DAGGER, _I.SHIELD}),
        "luminar": frozenset(
            {_I.STAFF, _I.ORB, _I.SCEPTER, _I.SWORD, _I.MACE, _I.AXE, _I.SHIELD}
        ),
    }
)

INITIAL_PROFICIENCY = MappingProxyType(
    {
        "sentinela": ProficiencyFamily.SWORDS,
        "errante": ProficiencyFamily.BLADES,
        "vigia": ProficiencyFamily.BOWS,
        "tecelao": ProficiencyFamily.ARCANE_FOCI,
        "oraculo": ProficiencyFamily.ARCANE_FOCI,
        "luminar": ProficiencyFamily.ARCANE_FOCI,
    }
)

# Starting weapon per Classe: +0, Grau I (item_level 1), Comum (author, 2026-11-13).
STARTING_WEAPON_TYPE_IDS = MappingProxyType(
    {
        "sentinela": "weapon.type.base.espada",
        "errante": "weapon.type.base.adaga",
        "vigia": "weapon.type.base.arco",
        "tecelao": "weapon.type.base.cajado",
        "oraculo": "weapon.type.base.orbe",
        "luminar": "weapon.type.base.cetro",
    }
)
STARTING_WEAPON_RARITY = "Comum"
STARTING_WEAPON_LEVEL = 1

# Base catalog templates: one per concrete identity. They are not in any drop pool.
BASE_WEAPON_TYPE_IDS = MappingProxyType(
    {
        _I.SWORD: "weapon.type.base.espada",
        _I.WAR_SWORD: "weapon.type.base.espada_de_guerra",
        _I.DAGGER: "weapon.type.base.adaga",
        _I.THROWING_DAGGER: "weapon.type.base.adaga_de_arremesso",
        _I.CHAKRAM: "weapon.type.base.chakram",
        _I.DOUBLE_BLADE: "weapon.type.base.lamina_dupla",
        _I.MACE: "weapon.type.base.maca",
        _I.WAR_HAMMER: "weapon.type.base.martelo_de_guerra",
        _I.AXE: "weapon.type.base.machado",
        _I.WAR_AXE: "weapon.type.base.machado_de_guerra",
        _I.SPEAR: "weapon.type.base.lanca",
        _I.HALBERD: "weapon.type.base.alabarda",
        _I.JAVELIN: "weapon.type.base.azagaia",
        _I.BOW: "weapon.type.base.arco",
        _I.HAND_CROSSBOW: "weapon.type.base.besta_de_mao",
        _I.HEAVY_CROSSBOW: "weapon.type.base.besta_pesada",
        _I.SCEPTER: "weapon.type.base.cetro",
        _I.ORB: "weapon.type.base.orbe",
        _I.STAFF: "weapon.type.base.cajado",
        _I.SHIELD: "weapon.type.base.escudo",
    }
)

# Exact identity of every published weapon template. Regional items keep their
# stable IDs; the identity below is the migration decision for each one.
WEAPON_TYPE_IDENTITIES = MappingProxyType(
    {
        **{weapon_type_id: identity for identity, weapon_type_id in BASE_WEAPON_TYPE_IDS.items()},
        "weapon.type.tdo.arma_caminhante": _I.SWORD,
        "weapon.type.tdo.guarda_caminhante": _I.DAGGER,
        "weapon.type.tdo.arma_pesada_caminhante": _I.BOW,
        "weapon.type.tdo.guarda_primeiro_selo": _I.MACE,
        "weapon.type.vde.arma_vale": _I.AXE,
        "weapon.type.vde.guarda_enredada": _I.DAGGER,
        "weapon.type.vde.arma_pesada_lacos": _I.HEAVY_CROSSBOW,
        "weapon.type.vde.guarda_no_antigo": _I.SWORD,
        "weapon.type.nareth.arma_meridiano": _I.SPEAR,
        "weapon.type.nareth.guarda_marco": _I.DAGGER,
        "weapon.type.nareth.arma_pesada_horizonte": _I.BOW,
        "weapon.type.nareth.guarda_camara_invertida": _I.SWORD,
        "weapon.type.nareth.guarda_referencia": _I.MACE,
        "weapon.type.varzeas.arma_dique": _I.MACE,
        "weapon.type.varzeas.guarda_salmoura": _I.DAGGER,
        "weapon.type.varzeas.arma_pesada_transferencia": _I.HEAVY_CROSSBOW,
        "weapon.type.varzeas.guarda_transferencia": _I.SWORD,
        # One-handed hammer form; the catalog's one-handed Contundente is Maça.
        "weapon.type.altos.arma_contrapeso": _I.MACE,
        "weapon.type.altos.guarda_escora": _I.AXE,
        "weapon.type.altos.arma_pesada_pedreira": _I.HEAVY_CROSSBOW,
        "equipment.altos.campaign.p30.guarda_contraforte_final": _I.MACE,
        "equipment.altos.special.guarda_ordem_profunda": _I.SWORD,
        "equipment.confins.campaign.p36.guarda_ultimo_protocolo": _I.MACE,
        "equipment.confins.special.guarda_duas_versoes": _I.SWORD,
        "craft.confins.ferreiro.principal.lamina_baliza": _I.SWORD,
        "craft.confins.ferreiro.secundaria.guarda_marcha": _I.DAGGER,
        "craft.confins.ferreiro.2h.arco_retorno": _I.BOW,
    }
)


def weapon_identity_for_type(weapon_type_id: str | None) -> WeaponIdentity | None:
    if not isinstance(weapon_type_id, str):
        return None
    return WEAPON_TYPE_IDENTITIES.get(weapon_type_id)


def weapon_proficiency_label(definition: object | None) -> str | None:
    """'Espada · Espadas' for a canonical WeaponDefinition, else None."""
    identity = weapon_identity_for_type(getattr(definition, "weapon_type_id", None))
    if identity is None:
        return None
    entry = WEAPON_IDENTITIES[identity]
    return f"{entry.label} · {FAMILY_LABELS[entry.family]}"


def class_allows_identity(character_class: str | None, identity: WeaponIdentity) -> bool:
    return identity in CLASS_WEAPON_WHITELIST.get(character_class or "", frozenset())


def learnable_families(character_class: str | None) -> tuple[ProficiencyFamily, ...]:
    """Families with at least one concrete identity the Classe may use."""
    allowed = CLASS_WEAPON_WHITELIST.get(character_class or "", frozenset())
    families = {IDENTITY_FAMILY[identity] for identity in allowed}
    return tuple(family for family in FAMILY_ORDER if family in families)


def usable_identities(
    character_class: str | None, family: ProficiencyFamily
) -> tuple[WeaponIdentity, ...]:
    allowed = CLASS_WEAPON_WHITELIST.get(character_class or "", frozenset())
    return tuple(
        identity
        for identity in WeaponIdentity
        if identity in allowed and IDENTITY_FAMILY[identity] == family
    )


@dataclass(frozen=True, slots=True)
class AcquisitionTerms:
    ordinal: int
    min_level: int
    cost_crowns: int


_ACQUISITION_TABLE = ((1, 0), (10, 1_000), (20, 2_500), (30, 5_000), (40, 10_000))
_ACQUISITION_BEYOND = (50, 20_000)


def acquisition_terms(ordinal: int) -> AcquisitionTerms:
    """Minimum level and Coroas for the Nth Proficiência (1st is the free creation seed)."""
    if ordinal < 1:
        raise ValueError("Proficiency ordinal starts at 1.")
    min_level, cost = (
        _ACQUISITION_TABLE[ordinal - 1]
        if ordinal <= len(_ACQUISITION_TABLE)
        else _ACQUISITION_BEYOND
    )
    return AcquisitionTerms(ordinal, min_level, cost)


def parse_family(value: str | None) -> ProficiencyFamily | None:
    try:
        return ProficiencyFamily(value)
    except ValueError:
        return None
