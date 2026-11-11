"""Effects of the six Obras beyond Alojamentos (§30.2).

The GDD names the Obras but defines no effect for them. The author delegated
the values on 2026-11-11 ("use valores balanceados; o balanceamento geral vem
depois"), so every number here is provisional and lives only in this module.
Design rules used: no combat attribute, no power snowball, only small economic
or quality-of-life effects. Leaving the Guilda removes them at once (§30.3),
because each effect is read from the current membership at the moment of use.

Index 0 is "not built"; indexes 1-5 are the completed levels I-V.
"""

from __future__ import annotations

from dataclasses import dataclass

from asterion.domain.guilds import ProjectKind

# Forja: discount on the Coroas cost of Aprimoramento.
FORGE_ENHANCEMENT_DISCOUNT_PERCENT = (0, 2, 4, 6, 8, 10)
# Altar do Véu: discount on Troca de Caminho and Respec de Talentos.
VEIL_ALTAR_RESPEC_DISCOUNT_PERCENT = (0, 10, 20, 30, 40, 50)
# Tesouraria: Market fee (basis points) for listings created by a member.
TREASURY_MARKET_FEE_BPS = (500, 450, 400, 350, 300, 250)
# Arquivo do Véu: discount on the Coroas cost of Ofício Receitas.
VEIL_ARCHIVE_RECIPE_DISCOUNT_PERCENT = (0, 4, 8, 12, 16, 20)
# Posto dos Caçadores: bonus on the Coroas of a Caçada encounter.
HUNTERS_POST_CROWN_BONUS_PERCENT = (0, 2, 4, 6, 8, 10)
# Salão de Guerra: Coroas per combatant in each finished real Batalha de Guildas,
# 0,10×C(30) per level (C(30) = 550, §49.10).
WAR_HALL_BATTLE_CROWNS = (0, 55, 110, 165, 220, 275)


@dataclass(frozen=True, slots=True)
class WorkLevels:
    """Completed level (0-5) of each Obra for one character's current Guilda."""

    forge: int = 0
    veil_altar: int = 0
    treasury: int = 0
    veil_archive: int = 0
    hunters_post: int = 0
    war_hall: int = 0

    @classmethod
    def from_levels(cls, levels: dict[str, int]) -> WorkLevels:
        return cls(
            **{
                kind: _clamp(levels.get(kind, 0))
                for kind in (
                    ProjectKind.FORGE.value,
                    ProjectKind.VEIL_ALTAR.value,
                    ProjectKind.TREASURY.value,
                    ProjectKind.VEIL_ARCHIVE.value,
                    ProjectKind.HUNTERS_POST.value,
                    ProjectKind.WAR_HALL.value,
                )
            }
        )

    @property
    def enhancement_discount(self) -> int:
        return FORGE_ENHANCEMENT_DISCOUNT_PERCENT[self.forge]

    @property
    def respec_discount(self) -> int:
        return VEIL_ALTAR_RESPEC_DISCOUNT_PERCENT[self.veil_altar]

    @property
    def market_fee_bps(self) -> int:
        return TREASURY_MARKET_FEE_BPS[self.treasury]

    @property
    def recipe_discount(self) -> int:
        return VEIL_ARCHIVE_RECIPE_DISCOUNT_PERCENT[self.veil_archive]

    @property
    def hunt_crown_bonus(self) -> int:
        return HUNTERS_POST_CROWN_BONUS_PERCENT[self.hunters_post]

    @property
    def battle_crowns(self) -> int:
        return WAR_HALL_BATTLE_CROWNS[self.war_hall]


NO_WORKS = WorkLevels()


def _clamp(level: int) -> int:
    return max(0, min(5, int(level)))


def discounted(cost: int, percent: int) -> int:
    """Cost after a percent discount; the discount rounds down, never below 0."""
    if cost <= 0 or percent <= 0:
        return max(cost, 0)
    return cost - cost * percent // 100


def with_bonus(amount: int, percent: int) -> int:
    """Amount plus a percent bonus rounded down."""
    if amount <= 0 or percent <= 0:
        return amount
    return amount + amount * percent // 100


def effect_text(kind: ProjectKind, level: int) -> str | None:
    """Short player-facing effect of an Obra at a completed level (0 = none)."""
    level = _clamp(level)
    if kind is ProjectKind.FORGE:
        value = FORGE_ENHANCEMENT_DISCOUNT_PERCENT[level]
        return f"−{value}% Coroas no Aprimoramento"
    if kind is ProjectKind.VEIL_ALTAR:
        value = VEIL_ALTAR_RESPEC_DISCOUNT_PERCENT[level]
        return f"−{value}% na Troca de Caminho e no Respec de Talentos"
    if kind is ProjectKind.TREASURY:
        bps = TREASURY_MARKET_FEE_BPS[level]
        return f"Taxa do Mercado {_percent(bps)} nos anúncios criados"
    if kind is ProjectKind.VEIL_ARCHIVE:
        value = VEIL_ARCHIVE_RECIPE_DISCOUNT_PERCENT[level]
        return f"−{value}% Coroas nas Receitas de Ofício"
    if kind is ProjectKind.HUNTERS_POST:
        value = HUNTERS_POST_CROWN_BONUS_PERCENT[level]
        return f"+{value}% Coroas na Caçada"
    if kind is ProjectKind.WAR_HALL:
        value = WAR_HALL_BATTLE_CROWNS[level]
        return f"+{value} Coroas por combatente em cada Batalha de Guildas"
    return None


def _percent(bps: int) -> str:
    whole, rest = divmod(bps, 100)
    return f"{whole}%" if rest == 0 else f"{whole},{rest // 10}%"
