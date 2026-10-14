"""Idempotent Feito and title reconciliation for Nareth's published slice."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    Character,
    CharacterCosmetic,
    LocationDiscovery,
)

NARETH_LOCATIONS = frozenset(
    {
        "nareth.location.campinas_do_meridiano",
        "nareth.location.posto_de_nareth",
        "nareth.location.canais_secos",
        "nareth.location.campos_invertidos",
        "nareth.location.observatorio_do_eixo",
    }
)
NARETH_BRAZIERS = frozenset(
    {
        "nareth.brazier.horizonte",
        "nareth.brazier.posto",
        "nareth.brazier.canal_alto",
        "nareth.brazier.linha_quebrada",
        "nareth.brazier.eixo",
    }
)
NARETH_WANDERER_FEAT = "feat.nareth.andarilho_de_nareth"


async def reconcile_nareth_feats(
    session: AsyncSession, character: Character
) -> tuple[str, ...]:
    character_id = character.id
    locations = set(
        (
            await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id.in_(NARETH_LOCATIONS),
                )
            )
        ).all()
    )
    braziers = set(
        (
            await session.scalars(
                select(Brazier.brazier_id).where(
                    Brazier.character_id == character_id,
                    Brazier.brazier_id.in_(NARETH_BRAZIERS),
                )
            )
        ).all()
    )
    eligible = NARETH_LOCATIONS <= locations and NARETH_BRAZIERS <= braziers
    existing = set(
        (
            await session.scalars(
                select(Achievement.achievement_id).where(
                    Achievement.character_id == character_id
                )
            )
        ).all()
    )
    newly_earned: tuple[str, ...] = ()
    if eligible and NARETH_WANDERER_FEAT not in existing:
        await session.execute(
            pg_insert(Achievement)
            .values(character_id=character_id, achievement_id=NARETH_WANDERER_FEAT)
            .on_conflict_do_nothing(
                index_elements=[Achievement.character_id, Achievement.achievement_id]
            )
        )
        existing.add(NARETH_WANDERER_FEAT)
        newly_earned = (NARETH_WANDERER_FEAT,)
    for achievement_id in existing:
        cosmetic = COSMETIC_BY_ACHIEVEMENT.get(achievement_id)
        if cosmetic is None:
            continue
        await session.execute(
            pg_insert(CharacterCosmetic)
            .values(
                character_id=character_id,
                cosmetic_id=cosmetic.cosmetic_id,
                cosmetic_type=cosmetic.cosmetic_type,
                source_achievement_id=achievement_id,
            )
            .on_conflict_do_nothing(
                index_elements=[CharacterCosmetic.character_id, CharacterCosmetic.cosmetic_id]
            )
        )
    return newly_earned


async def reconcile_nareth_feats_for_character(
    session: AsyncSession, character_id
) -> tuple[str, ...]:
    character = await session.scalar(
        select(Character).where(Character.id == character_id)
    )
    if character is None:
        return ()
    return await reconcile_nareth_feats(session, character)
