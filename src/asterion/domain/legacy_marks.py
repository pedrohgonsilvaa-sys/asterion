"""Canonical catalog of Marcas de Legado (GDD §16.1).

The GDD fixes the frame (10 horizontal quality-of-life options, at most 5 active,
no combat attributes, respec for 5.000 Coroas with a 7-day Recarga in a safe
place, no removal into an invalid state). The 10 Marcas, their effects and the
slot rule (one slot per Legado rank) were defined by the author on 2026-11-11.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum


class LegacyMarkId(StrEnum):
    BOLSA_FUNDA = "bolsa_funda"
    ARMAZEM_AMPLO = "armazem_amplo"
    ENTREGAS_GUARDADAS = "entregas_guardadas"
    BANCA_EXTRA = "banca_extra"
    SEXTA_DOUTRINA = "sexta_doutrina"
    CHAMADO_DO_BRASEIRO = "chamado_do_braseiro"
    PREGAO_CONSTANTE = "pregao_constante"
    VIGIA_DO_VIGOR = "vigia_do_vigor"
    MENSAGEIRO = "mensageiro"
    LEMBRETE_DE_RECARGAS = "lembrete_de_recargas"


MAX_ACTIVE_MARKS = 5
RESPEC_COST_CROWNS = 5_000
RESPEC_COOLDOWN = timedelta(days=7)

INVENTORY_BONUS = 10
WAREHOUSE_BONUS = 25
PENDING_BONUS = 10
LISTING_SLOT_BONUS = 2
DOCTRINE_BONUS = 1
# Pregão Constante shortens the Divulgar Recarga by 25%.
PROMOTION_COOLDOWN_FACTOR_NUMERATOR = 3
PROMOTION_COOLDOWN_FACTOR_DENOMINATOR = 4


@dataclass(frozen=True, slots=True)
class LegacyMark:
    id: LegacyMarkId
    name: str
    descriptor: str
    effect: str
    # False while the effect is not wired yet: the Marca stays visible but cannot
    # be activated, so no slot is ever spent on an effect that does nothing.
    available: bool


LEGACY_MARKS: tuple[LegacyMark, ...] = (
    LegacyMark(
        LegacyMarkId.BOLSA_FUNDA,
        "Bolsa Funda",
        "Capacidade",
        f"Inventário +{INVENTORY_BONUS} espaços.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.ARMAZEM_AMPLO,
        "Armazém Amplo",
        "Capacidade",
        f"Armazém +{WAREHOUSE_BONUS} espaços.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.ENTREGAS_GUARDADAS,
        "Entregas Guardadas",
        "Capacidade",
        f"Entregas Pendentes +{PENDING_BONUS} espaços.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.BANCA_EXTRA,
        "Banca Extra",
        "Mercado",
        f"+{LISTING_SLOT_BONUS} vagas de oferta na sua Loja.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.SEXTA_DOUTRINA,
        "Sexta Doutrina",
        "Doutrinas",
        f"+{DOCTRINE_BONUS} Doutrina.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.CHAMADO_DO_BRASEIRO,
        "Chamado do Braseiro",
        "Retorno",
        "1 viagem grátis por dia a um Braseiro permanente já descoberto.",
        False,
    ),
    LegacyMark(
        LegacyMarkId.PREGAO_CONSTANTE,
        "Pregão Constante",
        "Mercado",
        "Recarga de Divulgar 25% menor.",
        True,
    ),
    LegacyMark(
        LegacyMarkId.VIGIA_DO_VIGOR,
        "Vigia do Vigor",
        "Aviso",
        "Aviso quando o Vigor chega a 100.",
        False,
    ),
    LegacyMark(
        LegacyMarkId.MENSAGEIRO,
        "Mensageiro",
        "Aviso",
        "Aviso quando uma oferta do Mercado é vendida ou expira.",
        False,
    ),
    LegacyMark(
        LegacyMarkId.LEMBRETE_DE_RECARGAS,
        "Lembrete de Recargas",
        "Aviso",
        "Aviso quando a Recarga de Divulgar ou de Redistribuição termina.",
        False,
    ),
)

LEGACY_MARKS_BY_ID: dict[LegacyMarkId, LegacyMark] = {mark.id: mark for mark in LEGACY_MARKS}


def mark_slots(legacy_level: int) -> int:
    """One Marca slot per Legado rank, capped at the GDD maximum of 5."""
    if isinstance(legacy_level, bool) or not isinstance(legacy_level, int):
        raise ValueError("Legacy level must be an integer from 0 through 5.")
    if not 0 <= legacy_level <= 5:
        raise ValueError("Legacy level must be an integer from 0 through 5.")
    return min(legacy_level, MAX_ACTIVE_MARKS)


def parse_mark_id(value: str) -> LegacyMarkId | None:
    try:
        return LegacyMarkId(value)
    except ValueError:
        return None
