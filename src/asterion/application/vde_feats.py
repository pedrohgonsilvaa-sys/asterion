"""Idempotent Vales Feito and cosmetic reconciliation."""

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
VDE_PERMANENT_BRAZIERS = frozenset(
    {
        "vde.brazier.garganta_dos_lacos",
        "vde.brazier.vigilia_do_vale",
        "vde.brazier.mata_suspensa",
        "vde.brazier.turfa_fria",
        "vde.brazier.pedras_enlacadas",
    }
)
VDE_BASE_CREATURES = frozenset(
    {
        "lobo_musgoso",
        "gralha_vale",
        "peregrino_enredado",
        "aranha_cipo",
        "cervo_no",
        "sanguessuga_turfa",
        "casca_errante",
        "mariposa_breu_verde",
        "vigia_enraizado",
    }
)
VDE_WORLD_ELITES = frozenset({"no_feroz", "viuva_cipos", "carrasco_casca"})
VDE_VARIANT_TYPES = frozenset({"furious", "resistant", "agile", "hemorrhagic", "venomous"})
SANCTUARY_STABLE_CLEAR = "dungeon.vde.santuario_no_antigo.first_clear.stable"
SANCTUARY_FRACTURED_CLEAR = "dungeon.vde.santuario_no_antigo.first_clear.fractured"
FOSSO_STABLE_CLEAR = "dungeon.vde.fosso_raizes.first_clear.stable"
FOSSO_FRACTURED_CLEAR = "dungeon.vde.fosso_raizes.first_clear.fractured"
SANCTUARY_UNLOCK = "dungeon.vde.santuario_no_antigo"
FOSSO_UNLOCK = "dungeon.vde.fosso_raizes"
MATRIARCH_EVIDENCE = "matriarca_raizes"
VDE_STUDIED_BESTIARY_CREATURES = (
    "vigia_enraizado",
    "custodio_enredado",
    "prelado_enraizado",
    "guardiao_no_antigo",
)
BESTIARY_STAGE_ORDER = {"observed": 0, "known": 1, "studied": 2, "dominated": 3}


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
    braziers = set(
        (
            await session.scalars(
                select(Brazier.brazier_id).where(
                    Brazier.character_id == character_id,
                    Brazier.brazier_id.in_(VDE_PERMANENT_BRAZIERS),
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
    variant_evidence = set(
        (
            await session.scalars(
                select(BestiaryEvidence.evidence_id).where(
                    BestiaryEvidence.character_id == character_id,
                    BestiaryEvidence.evidence_id.like("variant:%"),
                )
            )
        ).all()
    )
    discovered_variant_types = {
        evidence_id.removeprefix("variant:") for evidence_id in variant_evidence
    }
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
    feat_bestiary_creatures = (
        VDE_BASE_CREATURES
        | VDE_WORLD_ELITES
        | frozenset(VDE_STUDIED_BESTIARY_CREATURES)
    )
    bestiary_stages = dict(
        (
            await session.execute(
                select(BestiaryEntry.creature_id, BestiaryEntry.stage).where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id.in_(feat_bestiary_creatures),
                )
            )
        ).all()
    )
    dominated = {
        creature_id
        for creature_id, stage in bestiary_stages.items()
        if stage == "dominated"
    }
    bases_dominated = VDE_BASE_CREATURES <= dominated
    three_elites_dominated = VDE_WORLD_ELITES <= dominated
    both_fractured = {
        FOSSO_FRACTURED_CLEAR,
        SANCTUARY_FRACTURED_CLEAR,
    } <= unlocks
    conditions = {
        "feat.vde.andarilho_dos_vales": (
            VDE_CAMPAIGN_LOCATIONS <= locations
            and VDE_PERMANENT_BRAZIERS <= braziers
        ),
        "feat.vde.aquilo_que_pende": FOSSO_STABLE_CLEAR in unlocks,
        "feat.vde.sob_as_raizes": {FOSSO_UNLOCK, SANCTUARY_UNLOCK} <= unlocks,
        "feat.vde.o_no_antigo": SANCTUARY_STABLE_CLEAR in unlocks,
        "feat.vde.raizes_fraturadas": both_fractured,
        "feat.vde.cacador_dos_vales": bases_dominated,
        "feat.vde.entre_galhos_e_presas": (
            bases_dominated
            and three_elites_dominated
            and VDE_VARIANT_TYPES <= discovered_variant_types
        ),
        "feat.vde.a_pedra_que_ainda_guarda": all(
            BESTIARY_STAGE_ORDER.get(bestiary_stages.get(creature_id, "observed"), 0) >= 2
            for creature_id in VDE_STUDIED_BESTIARY_CREATURES
        ),
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
