"""Idempotent Feito and title reconciliation for Nareth's published slice."""

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
NARETH_BASE_CREATURES = frozenset(
    {
        "galgo_meridiano",
        "abutre_marco",
        "errante_valas",
        "escaravelho_canal",
        "cervo_horizonte",
        "serpe_campinas",
        "casco_invertido",
        "mariposa_eixo",
        "vigia_meridiano",
    }
)
NARETH_ELITES = frozenset({"alfa_horizonte", "serpe_eixo", "custodio_invertido"})
NARETH_VARIANT_CREATURES = NARETH_BASE_CREATURES
NARETH_VARIANT_TYPES = frozenset(
    {"furious", "resistant", "agile", "hemorrhagic", "venomous"}
)
NARETH_STUDIED_CREATURES = (
    "vigia_meridiano",
    "custodio_invertido",
    "custodio_meridiano",
    "preceptor_eixo",
    "guardiao_referencia",
)
NARETH_GALLERIES = "dungeon.nareth.galerias_meridiano"
NARETH_OBSERVATORY = "dungeon.nareth.observatorio_afundado"
NARETH_GALLERIES_STABLE = f"{NARETH_GALLERIES}.first_clear.stable"
NARETH_GALLERIES_FRACTURED = f"{NARETH_GALLERIES}.first_clear.fractured"
NARETH_OBSERVATORY_STABLE = f"{NARETH_OBSERVATORY}.first_clear.stable"
NARETH_OBSERVATORY_FRACTURED = f"{NARETH_OBSERVATORY}.first_clear.fractured"
NARETH_ROUTE_CODEX = "codex.route.rotas_de_nareth"
NARETH_CARTOGRAPHY_CODEX = "codex.history.cartografia_do_erro"
NARETH_PROTOCOL_CODEX = "codex.history.protocolos_de_referencia"
NARETH_CUSTODY_CODEX = "codex.history.custodia_das_ancoras"
NARETH_VEIL_STABILITY_CODEX = "codex.history.estabilidade_do_veu"
NARETH_BOSS_VICTORY_EVIDENCE = "first_victory"


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
    quests = set(
        (
            await session.scalars(
                select(Quest.quest_id).where(
                    Quest.character_id == character_id,
                    Quest.status == "completed",
                    Quest.quest_id.in_(("P13", "P18", "S16", "S18")),
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
    codex = set(
        (
            await session.scalars(
                select(CodexEntry.entry_id).where(CodexEntry.character_id == character_id)
            )
        ).all()
    )
    bestiary = dict(
        (
            await session.execute(
                select(BestiaryEntry.creature_id, BestiaryEntry.stage).where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id.in_(
                        NARETH_BASE_CREATURES | NARETH_ELITES | frozenset(NARETH_STUDIED_CREATURES)
                    ),
                )
            )
        ).all()
    )
    dominated = {
        creature_id for creature_id, stage in bestiary.items() if stage == "dominated"
    }
    evidence = set(
        (
            await session.scalars(
                select(BestiaryEvidence.evidence_id).where(
                    BestiaryEvidence.character_id == character_id,
                    BestiaryEvidence.creature_id.in_(NARETH_VARIANT_CREATURES),
                    BestiaryEvidence.evidence_id.like("variant:%"),
                )
            )
        ).all()
    )
    variant_types = {value.removeprefix("variant:") for value in evidence}
    arconte_first_victory = await session.scalar(
        select(BestiaryEvidence.id).where(
            BestiaryEvidence.character_id == character_id,
            BestiaryEvidence.creature_id == "arconte_invertido",
            BestiaryEvidence.evidence_id == NARETH_BOSS_VICTORY_EVIDENCE,
        )
    )
    fractured_pair = {NARETH_GALLERIES_FRACTURED, NARETH_OBSERVATORY_FRACTURED}
    studied = {
        creature_id
        for creature_id in NARETH_STUDIED_CREATURES
        if bestiary.get(creature_id) in {"studied", "dominated"}
    }
    condition_map = {
        "feat.nareth.primeiro_meridiano": "P13" in quests,
        NARETH_WANDERER_FEAT: eligible,
        "feat.nareth.sob_o_mesmo_eixo": {
            NARETH_GALLERIES,
            NARETH_OBSERVATORY,
        } <= unlocks,
        "feat.nareth.a_camara_se_cala": arconte_first_victory is not None,
        "feat.nareth.o_que_retorna": NARETH_GALLERIES_STABLE in unlocks,
        "feat.nareth.referencia_afundada": NARETH_OBSERVATORY_STABLE in unlocks,
        "feat.nareth.eixos_fraturados": fractured_pair <= unlocks,
        "feat.nareth.cacador_de_nareth": NARETH_BASE_CREATURES <= dominated,
        "feat.nareth.horizonte_sem_norte": (
            NARETH_BASE_CREATURES | NARETH_ELITES <= dominated
            and NARETH_VARIANT_TYPES <= variant_types
        ),
        "feat.nareth.a_medida_que_permanece": (
            set(NARETH_STUDIED_CREATURES) <= studied
        ),
        "feat.nareth.os_caminhos_que_nao_coincidem": (
            {"S16", "S18"} <= quests
            and {NARETH_ROUTE_CODEX, NARETH_CARTOGRAPHY_CODEX} <= codex
        ),
        "feat.nareth.a_rede_mede_ainda": (
            NARETH_OBSERVATORY_STABLE in unlocks
            and "P18" in quests
            and {
                NARETH_PROTOCOL_CODEX,
                NARETH_CUSTODY_CODEX,
                NARETH_VEIL_STABILITY_CODEX,
            }
            <= codex
        ),
        "feat.nareth.planicies_de_nareth": (
            "P18" in quests and character.level >= 30 and NARETH_LOCATIONS <= locations
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
    newly_earned: tuple[str, ...] = ()
    newly_earned_ids = []
    for achievement_id, is_eligible in condition_map.items():
        if not is_eligible or achievement_id in existing:
            continue
        await session.execute(
            pg_insert(Achievement)
            .values(character_id=character_id, achievement_id=achievement_id)
            .on_conflict_do_nothing(
                index_elements=[Achievement.character_id, Achievement.achievement_id]
            )
        )
        existing.add(achievement_id)
        newly_earned_ids.append(achievement_id)
    newly_earned = tuple(newly_earned_ids)
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
