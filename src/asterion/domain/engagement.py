"""Dádiva Diária, Chamado de Asterion and Códigos de Asterion.

Sources: GDD v1.6.0 §32, §49.10 and §49.19. Author decisions of 2026-11-08 fix what
the GDD leaves open: the Grade of basics and Fragments is the character's current
Region, basics rotate Metal, Couro, Reagente, Essência, and `C` in a Code is
C(character level at redemption).
"""

from __future__ import annotations

import re
import secrets
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.professions import (
    FRAGMENT_I,
    FRAGMENT_V,
    HERB,
    IRON,
    LEATHER,
    MATERIAL_NAMES,
    NARETH_BRONZE,
    NARETH_FRAGMENT_III,
    NARETH_HERB,
    NARETH_LEATHER,
    NARETH_POWDER,
    RESIDUE,
    VARZEAS_ESSENCE,
    VARZEAS_FRAGMENT_IV,
    VARZEAS_IRON,
    VARZEAS_LEATHER,
    VARZEAS_REAGENT,
    VDE_FRAGMENT_II,
    VDE_HERB,
    VDE_IRON,
    VDE_LEATHER,
    VDE_RESIN,
)


@dataclass(frozen=True, slots=True)
class Bundle:
    crowns: int = 0
    basics: int = 0
    fragments: int = 0


@dataclass(frozen=True, slots=True)
class RegionSupply:
    basics: tuple[str, str, str, str]  # Metal, Couro, Reagente, Essência
    fragment: str


# §49.10, seven claims: 500 Coroas + 6 basics + 5 Fragments.
DAILY_GIFT: tuple[Bundle, ...] = (
    Bundle(crowns=100),
    Bundle(basics=2),
    Bundle(fragments=1),
    Bundle(crowns=150),
    Bundle(basics=4),
    Bundle(fragments=2),
    Bundle(crowns=250, fragments=2),
)

_TDO = RegionSupply((IRON, LEATHER, HERB, RESIDUE), FRAGMENT_I)
REGION_SUPPLY: dict[str, RegionSupply] = {
    "Terras do Ocaso": _TDO,
    "Vales dos Enforcados": RegionSupply(
        (VDE_IRON, VDE_LEATHER, VDE_HERB, VDE_RESIN), VDE_FRAGMENT_II
    ),
    "Planícies de Nareth": RegionSupply(
        (NARETH_BRONZE, NARETH_LEATHER, NARETH_HERB, NARETH_POWDER), NARETH_FRAGMENT_III
    ),
    "Várzeas Carmesins": RegionSupply(
        (VARZEAS_IRON, VARZEAS_LEATHER, VARZEAS_REAGENT, VARZEAS_ESSENCE), VARZEAS_FRAGMENT_IV
    ),
    "Altos Cinéreos": RegionSupply(
        (
            "material.altos.ferro_contrapeso",
            "material.altos.couro_escarpa",
            "material.altos.liquen_pedreira",
            "material.altos.cinza_basalto",
        ),
        FRAGMENT_V,
    ),
    "Confins do Véu": RegionSupply(
        (
            "material.confins.ferro_baliza",
            "material.confins.couro_marcha",
            "material.confins.musgo_limiar",
            "material.confins.po_referencia",
        ),
        "material.tdo.fragmento_aprimoramento_vi",
    ),
}


def supply_for(region: str | None) -> RegionSupply:
    """The Prologue has no Region yet; it uses the first one."""
    return REGION_SUPPLY.get(region or "", _TDO)


def bundle_materials(bundle: Bundle, region: str | None) -> dict[str, int]:
    supply = supply_for(region)
    counts: Counter[str] = Counter(
        supply.basics[index % len(supply.basics)] for index in range(bundle.basics)
    )
    if bundle.fragments:
        counts[supply.fragment] += bundle.fragments
    return dict(counts)


def material_name(material_id: str) -> str:
    return MATERIAL_NAMES.get(material_id, material_id)


# §49.19 Chamado de Asterion.
RECRUIT_LINK_WINDOW = timedelta(hours=72)
RECRUIT_MAX_LEVEL_EXCLUSIVE = 10
RECRUITER_MIN_LEVEL = 10
RECRUIT_MILESTONES: dict[int, int] = {10: 100, 30: 200, 60: 300}
RECRUITER_PAID_RECRUITS = 10
RECRUIT_CODE_LENGTH = 8
_RECRUIT_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


@dataclass(frozen=True, slots=True)
class RecruitPrestige:
    milestone: int
    recruits: int
    cosmetic_id: str


RECRUIT_PRESTIGE: tuple[RecruitPrestige, ...] = (
    RecruitPrestige(10, 1, "cosmetic.title.chamado.guia_da_estrada"),
    RecruitPrestige(30, 3, "cosmetic.title.chamado.voz_que_reune"),
    RecruitPrestige(60, 5, "cosmetic.frame.chamado.laco_das_cinzas"),
    RecruitPrestige(60, 10, "cosmetic.frame.chamado.circulo_dos_caminhantes"),
    RecruitPrestige(60, 20, "cosmetic.appearance.chamado.arauto_de_asterion"),
)


def generate_recruit_code() -> str:
    return "".join(secrets.choice(_RECRUIT_ALPHABET) for _ in range(RECRUIT_CODE_LENGTH))


def normalize_recruit_code(raw: str) -> str | None:
    code = raw.strip().upper()
    if len(code) != RECRUIT_CODE_LENGTH or any(ch not in _RECRUIT_ALPHABET for ch in code):
        return None
    return code


# §49.19 Códigos de Asterion.
_PROMO_CODE = re.compile(r"^[A-Z0-9-]{6,24}$")
_PROMO_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
PROMO_GENERATED_LENGTH = 12
PROMO_ATTEMPTS_PER_MINUTE = 5
PROMO_ATTEMPTS_PER_HOUR = 20
PROMO_DEFAULT_DURATION = timedelta(days=30)
PROMO_NORMAL_C = Decimal("0.50")
PROMO_NORMAL_BASICS = 4
PROMO_NORMAL_FRAGMENTS = 2
PROMO_HARD_C = Decimal("1.00")
PROMO_HARD_BASICS = 8
PROMO_HARD_FRAGMENTS = 3
PROMO_SCOPES = ("account", "character")


class PromoRewardError(ValueError):
    """A Code reward breaks the §49.19 limits."""


def normalize_promo_code(raw: str) -> str | None:
    code = raw.strip().upper()
    return code if _PROMO_CODE.fullmatch(code) else None


def generate_promo_code() -> str:
    return "".join(secrets.choice(_PROMO_ALPHABET) for _ in range(PROMO_GENERATED_LENGTH))


def validate_promo_entry(
    entry: dict[str, object], *, allow_above_normal: bool
) -> dict[str, object]:
    """Return the stored form. Only Coroas, basics and Fragments can exist in a Code."""
    try:
        multiplier = Decimal(str(entry.get("c_multiplier", "0")))
        basics = int(str(entry.get("basics", 0)))
        fragments = int(str(entry.get("fragments", 0)))
        weight = int(str(entry.get("weight", 1)))
    except (InvalidOperation, ValueError) as exc:
        raise PromoRewardError("reward_malformed") from exc
    if not multiplier.is_finite() or multiplier < 0 or basics < 0 or fragments < 0 or weight < 1:
        raise PromoRewardError("reward_malformed")
    if multiplier == 0 and basics == 0 and fragments == 0:
        raise PromoRewardError("reward_empty")
    if multiplier > PROMO_HARD_C or basics > PROMO_HARD_BASICS or fragments > PROMO_HARD_FRAGMENTS:
        raise PromoRewardError("reward_above_hard_cap")
    above_normal = (
        multiplier > PROMO_NORMAL_C
        or basics > PROMO_NORMAL_BASICS
        or fragments > PROMO_NORMAL_FRAGMENTS
    )
    if above_normal and not allow_above_normal:
        raise PromoRewardError("reward_above_normal")
    return {
        "weight": weight,
        "c_multiplier": str(multiplier),
        "basics": basics,
        "fragments": fragments,
    }


def promo_crowns(c_multiplier: str, level: int) -> int:
    """§49.0: one round_10 after the multiplication."""
    return round_10(Decimal(c_multiplier) * crowns_per_level(level))
