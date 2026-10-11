"""Idempotent Vales Feito and cosmetic reconciliation."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEvidence,
    Character,
    CharacterCosmetic,
    CodexEntry,
    LocationDiscovery,
    Quest,
    Unlock,
)

P12_ID = "P12"
VDE_CAMPAIGN_LOCATIONS = frozenset(
    {
        "vde.location.garganta_dos_lacos",
        "vde.location.mata_suspensa",
        "vde.location.baixios_enredados",
        "vde.location.claustro_das_raizes",
        "vde.location.berco_da_matriarca",
    }
)
SANCTUARY_STABLE_CLEAR = "dungeon.vde.santuario_no_antigo.first_clear.stable"
MATRIARCH_EVIDENCE = "matriarca_raizes"


async def reconcile_vde_feats(
    session: AsyncSession, character: Character
) -> tuple[str, ...]:
    """Materialize only Feitos whose persistent regional conditions are true."""
    character_id = character.id
    locations = set(
        (
            await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id.in_(VDE_CAMPAIGN_LOCATIONS),
                )
            )
        ).all()
    )
    p12 = await session.scalar(
        select(Quest).where(
            Quest.character_id == character_id,
            Quest.quest_id == P12_ID,
            Quest.status == "completed",
        )
    )
    evidence = set(
        (
            await session.scalars(
                select(BestiaryEvidence.evidence_id).where(
                    BestiaryEvidence.character_id == character_id,
                    BestiaryEvidence.creature_id == MATRIARCH_EVIDENCE,
                )
            )
        ).all()
    )
    codex = set(
        (
            await session.scalars(
                select(CodexEntry.entry_id).where(
                    CodexEntry.character_id == character_id
                )
            )
        ).all()
    )
    unlocks = set(
        (
            await session.scalars(
                select(Unlock.unlock_id).where(Unlock.character_id == character_id)
            )
        ).all()
    )
    conditions = {
        "feat.vde.o_berco_silencia": "first_victory" in evidence,
        "feat.vde.vales_dos_enforcados": (
            p12 is not None and character.level >= 20 and VDE_CAMPAIGN_LOCATIONS <= locations
        ),
        "feat.vde.a_rede_nao_dorme": (
            p12 is not None
            and SANCTUARY_STABLE_CLEAR in unlocks
            and {
                "codex.mystery.o_no_antigo",
                "codex.mystery.estruturas_interligadas",
                "codex.mystery.a_rede_sob_os_vales",
            }
            <= codex
        ),
    }
    existing = set(
        (
            await session.scalars(
                select(Achievement.achievement_id).where(
                    Achievement.character_id == character_id
                )
            )
        ).all()
    )
    newly_earned = []
    for achievement_id, eligible in conditions.items():
        if not eligible or achievement_id in existing:
            continue
        await session.execute(
            pg_insert(Achievement)
            .values(character_id=character_id, achievement_id=achievement_id)
            .on_conflict_do_nothing(
                index_elements=[Achievement.character_id, Achievement.achievement_id]
            )
        )
        existing.add(achievement_id)
        newly_earned.append(achievement_id)
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
    return tuple(newly_earned)


async def reconcile_vde_feats_for_character(
    session: AsyncSession, character_id
) -> tuple[str, ...]:
    character = await session.scalar(select(Character).where(Character.id == character_id))
    if character is None:
        return ()
    return await reconcile_vde_feats(session, character)
