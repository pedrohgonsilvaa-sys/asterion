"""Marca de Legado effects read by Mercado and Doutrinas (GDD §16.1)."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.inventory_capacity import has_legacy_mark
from asterion.domain.legacy_marks import (
    DOCTRINE_BONUS,
    LISTING_SLOT_BONUS,
    PROMOTION_COOLDOWN_FACTOR_DENOMINATOR,
    PROMOTION_COOLDOWN_FACTOR_NUMERATOR,
    LegacyMarkId,
)
from asterion.domain.market import LISTING_SLOTS, PROMOTION_COOLDOWN

BASE_DOCTRINES = 5


async def listing_slots(session: AsyncSession, character_id: UUID) -> int:
    """Active offer slots in the character's Loja, including Banca Extra."""
    bonus = await has_legacy_mark(session, character_id, LegacyMarkId.BANCA_EXTRA)
    return LISTING_SLOTS + (LISTING_SLOT_BONUS if bonus else 0)


async def promotion_cooldown(session: AsyncSession, character_id: UUID) -> timedelta:
    """Divulgar Recarga for the character, shortened by Pregão Constante."""
    if await has_legacy_mark(session, character_id, LegacyMarkId.PREGAO_CONSTANTE):
        return (
            PROMOTION_COOLDOWN
            * PROMOTION_COOLDOWN_FACTOR_NUMERATOR
            / PROMOTION_COOLDOWN_FACTOR_DENOMINATOR
        )
    return PROMOTION_COOLDOWN


async def doctrine_limit(session: AsyncSession, character_id: UUID) -> int:
    """Doutrinas the character may own, including Sexta Doutrina."""
    bonus = await has_legacy_mark(session, character_id, LegacyMarkId.SEXTA_DOUTRINA)
    return BASE_DOCTRINES + (DOCTRINE_BONUS if bonus else 0)
