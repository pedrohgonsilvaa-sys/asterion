"""Idempotent evaluator for the authoritative TDO Feitos."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    Unlock,
)

TDO_MAIN_LOCATIONS = frozenset(
    {
        "tdo.location.estrada_das_cinzas",
        "tdo.location.refugio_do_ocaso",
        "tdo.location.charneca_da_fuligem",
        "tdo.location.bosque_calcinado",
        "tdo.location.ruinas_do_vigia",
    }
)
TDO_PERMANENT_BRAZIERS = frozenset(
    {
        "tdo.brazier.estrada",
        "tdo.brazier.refugio_do_ocaso",
        "tdo.brazier.vento_morto",
        "tdo.brazier.galhos_mortos",
        "tdo.brazier.poente",
    }
)
TDO_BASE_CREATURES = frozenset(
    {
        "dog_cinereo",
        "corvo_fuligem",
        "peregrino_calcinado",
        "aranha_cinza",
        "cervo_escoriado",
        "carnical_fuligem",
        "mariposa_brasa",
        "vigia_rachado",
        "custodio_sem_rosto",
    }
)
TDO_ELITES = frozenset(
    {
        "alfa_cinereo",
        "viuva_fuligem",
        "custodio_poente",
        "guardiao_lapides",
        "vigia_integro",
        "preceptor_rachado",
    }
)
TDO_GUARDIANS = frozenset(
    {
        "vigia_rachado",
        "custodio_sem_rosto",
        "custodio_poente",
        "vigia_integro",
        "preceptor_rachado",
        "custodio_primeiro_selo",
        "vigia_partido",
    }
)
TDO_VARIANT_TYPES = frozenset({"furious", "resistant", "agile", "hemorrhagic", "venomous"})
CRYPT_ID = "dungeon.tdo.cripta_ocaso"
GALLERIES_ID = "dungeon.tdo.galerias_vigia"
CRYPT_CLEAR = f"{CRYPT_ID}.first_clear."
GALLERIES_CLEAR = f"{GALLERIES_ID}.first_clear."
P6_ID = "P6"


async def reconcile_tdo_feats(session: AsyncSession, character: Character) -> tuple[str, ...]:
    """Grant Feitos/cosmetics only from durable facts, without economic rewards."""
    character_id = character.id

    locations = set(
        (
            await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id.in_(TDO_MAIN_LOCATIONS),
                )
            )
        ).all()
    )
    braziers = set(
        (
            await session.scalars(
                select(Brazier.brazier_id).where(
                    Brazier.character_id == character_id,
                    Brazier.brazier_id.in_(TDO_PERMANENT_BRAZIERS),
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
    quests = {
        row.quest_id: row.status
        for row in (
            await session.scalars(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id.in_({"P1", "P6", "S2", "S6"}),
                )
            )
        ).all()
    }
    completed_prologue = await session.scalar(
        select(GameActivity.id)
        .where(
            GameActivity.character_id == character_id,
            GameActivity.content_id == "prologue_first_combat",
            GameActivity.status == "completed",
        )
        .limit(1)
    )
    # Characters at the persisted post-prologue brazier boundary predate the
    # GameActivity ledger. That stage plus the discovered first brazier is a
    # durable legacy proof of a valid victory or defeat and is safe to backfill.
    completed_legacy_prologue = (
        character.stage in {"cinzas_na_estrada:ready_for_first_brazier", "menu:ready"}
        and "tdo.brazier.estrada" in braziers
    )
    bestiary_rows = list(
        (
            await session.scalars(
                select(BestiaryEntry).where(BestiaryEntry.character_id == character_id)
            )
        ).all()
    )
    stages = {row.creature_id: row.stage for row in bestiary_rows}
    wins = {row.creature_id: row.wins for row in bestiary_rows}
    evidence_rows = list(
        (
            await session.scalars(
                select(BestiaryEvidence).where(
                    BestiaryEvidence.character_id == character_id,
                    BestiaryEvidence.evidence_id.like("variant:%"),
                )
            )
        ).all()
    )
    variants_by_type = {row.evidence_id.removeprefix("variant:") for row in evidence_rows}
    codex_entries = set(
        (
            await session.scalars(
                select(CodexEntry.entry_id).where(CodexEntry.character_id == character_id)
            )
        ).all()
    )
    codex_fragments = set(
        (
            await session.scalars(
                select(CodexFragment.fragment_id).where(CodexFragment.character_id == character_id)
            )
        ).all()
    )

    existing = await _existing_achievement_ids(session, character_id)
    first_stable_crypt = f"{CRYPT_CLEAR}stable" in unlocks
    first_stable_galleries = f"{GALLERIES_CLEAR}stable" in unlocks
    first_fractured_crypt = f"{CRYPT_CLEAR}fractured" in unlocks
    first_fractured_galleries = f"{GALLERIES_CLEAR}fractured" in unlocks
    base_dominated = TDO_BASE_CREATURES.issubset(
        {creature_id for creature_id, stage in stages.items() if stage == "dominated"}
    )
    dominated_creatures = {
        creature_id for creature_id, stage in stages.items() if stage == "dominated"
    }
    elites_dominated = len(TDO_ELITES & dominated_creatures) >= 3
    guardians_studied = TDO_GUARDIANS.issubset(
        {creature_id for creature_id, stage in stages.items() if stage in {"studied", "dominated"}}
    )

    conditions = {
        "feat.tdo.cinzas_na_estrada": (
            completed_prologue is not None or completed_legacy_prologue
        ),
        "feat.tdo.andarilho_das_cinzas": (
            TDO_MAIN_LOCATIONS.issubset(locations) and TDO_PERMANENT_BRAZIERS.issubset(braziers)
        ),
        "feat.tdo.sob_a_superficie": {CRYPT_ID, GALLERIES_ID}.issubset(unlocks),
        "feat.tdo.a_ultima_guarda": (
            wins.get("vigia_partido", 0) > 0 or "feat.tdo.a_ultima_guarda" in existing
        ),
        "feat.tdo.silencio_entre_os_nomes": first_stable_crypt,
        "feat.tdo.a_ordem_interrompida": first_stable_galleries,
        "feat.tdo.cinzas_fraturadas": (first_fractured_crypt and first_fractured_galleries),
        "feat.tdo.cacador_do_ocaso": base_dominated,
        "feat.tdo.entre_aquilo_que_caca": (
            base_dominated and elites_dominated and TDO_VARIANT_TYPES.issubset(variants_by_type)
        ),
        "feat.tdo.testemunha_dos_guardioes": guardians_studied,
        "feat.tdo.nomes_sob_a_cinza": (
            quests.get("S2") == "completed"
            and quests.get("S6") == "completed"
            and CRYPT_ID in unlocks
            and first_stable_crypt
            and "codex.history.os_sem_nome" in codex_entries
            and "codex.fragment.crypt.sem_nome" in codex_fragments
        ),
        "feat.tdo.a_ordem_ainda_permanece": (
            first_stable_galleries
            and quests.get(P6_ID) == "completed"
            and {
                "codex.history.primeiro_selo",
                "codex.history.ordens_que_permanecem",
                "codex.mystery.ancora_do_poente",
            }.issubset(codex_entries)
            and {
                "codex.fragment.galleries.first_seal",
                "codex.fragment.galleries.orders_remain",
                "codex.fragment.ancora_do_poente.nome_registrado",
            }.issubset(codex_fragments)
        ),
        "feat.tdo.terras_do_ocaso": (
            quests.get(P6_ID) == "completed"
            and character.level >= 10
            and TDO_MAIN_LOCATIONS.issubset(locations)
        ),
    }

    newly_earned: list[str] = []
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

    # Existing rows can predate this evaluator. Backfill only their cosmetic
    # entitlements; no XP, Crowns, quests, first-clear or inventory reward is replayed.
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


async def reconcile_tdo_feats_for_character(session: AsyncSession, character_id) -> tuple[str, ...]:
    character = await session.scalar(select(Character).where(Character.id == character_id))
    if character is None:
        return ()
    return await reconcile_tdo_feats(session, character)


async def _existing_achievement_ids(session: AsyncSession, character_id) -> set[str]:
    return set(
        (
            await session.scalars(
                select(Achievement.achievement_id).where(Achievement.character_id == character_id)
            )
        ).all()
    )
