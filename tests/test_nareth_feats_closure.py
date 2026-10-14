import pytest
from sqlalchemy import select

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.application.nareth_feats import (
    NARETH_BASE_CREATURES,
    NARETH_BRAZIERS,
    NARETH_ELITES,
    NARETH_GALLERIES,
    NARETH_GALLERIES_FRACTURED,
    NARETH_GALLERIES_STABLE,
    NARETH_LOCATIONS,
    NARETH_OBSERVATORY,
    NARETH_OBSERVATORY_FRACTURED,
    NARETH_OBSERVATORY_STABLE,
    NARETH_STUDIED_CREATURES,
    NARETH_VARIANT_TYPES,
    reconcile_nareth_feats_for_character,
)
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
from tests.test_nareth_opening_integration import _seed_nareth_entry


@pytest.mark.asyncio
async def test_nareth_feats_reconcile_from_durable_conditions_and_are_idempotent(database):
    character_id, sessions = await _seed_nareth_entry(database, 991915, level=30)
    all_nareth_creatures = NARETH_BASE_CREATURES | NARETH_ELITES | frozenset(
        NARETH_STUDIED_CREATURES
    )
    unlocks = {
        NARETH_GALLERIES,
        NARETH_OBSERVATORY,
        NARETH_GALLERIES_STABLE,
        NARETH_OBSERVATORY_STABLE,
        NARETH_GALLERIES_FRACTURED,
        NARETH_OBSERVATORY_FRACTURED,
    }
    codex_entries = {
        "codex.route.rotas_de_nareth",
        "codex.history.cartografia_do_erro",
        "codex.history.protocolos_de_referencia",
        "codex.history.custodia_das_ancoras",
        "codex.history.estabilidade_do_veu",
    }
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 30
        session.add_all(
            Quest(
                character_id=character_id,
                quest_id=quest_id,
                title=quest_id,
                status="completed",
                step=1,
                content_version="nareth-1.0.1",
                progress={"completed": True},
            )
            for quest_id in ("P13", "P18", "S16", "S18")
        )
        session.add_all(
            LocationDiscovery(character_id=character_id, location_id=location_id)
            for location_id in NARETH_LOCATIONS
        )
        session.add_all(
            Brazier(character_id=character_id, brazier_id=brazier_id)
            for brazier_id in NARETH_BRAZIERS
        )
        session.add_all(
            Unlock(character_id=character_id, unlock_id=unlock_id) for unlock_id in unlocks
        )
        session.add_all(
            CodexEntry(character_id=character_id, entry_id=entry_id)
            for entry_id in codex_entries
        )
        session.add_all(
            BestiaryEntry(
                character_id=character_id,
                creature_id=creature_id,
                bkp=60,
                wins=1,
                stage="dominated",
            )
            for creature_id in all_nareth_creatures
        )
        session.add(
            BestiaryEvidence(
                character_id=character_id,
                creature_id="arconte_invertido",
                evidence_id="first_victory",
                category="victory",
            )
        )
        session.add_all(
            BestiaryEvidence(
                character_id=character_id,
                creature_id=sorted(NARETH_BASE_CREATURES)[0],
                evidence_id=f"variant:{variant_type}",
                category="variant",
            )
            for variant_type in NARETH_VARIANT_TYPES
        )
        await session.flush()

        first = set(await reconcile_nareth_feats_for_character(session, character_id))
        second = await reconcile_nareth_feats_for_character(session, character_id)
        assert len(first) == 13
        assert second == ()

    async with sessions() as session:
        earned = set(
            (
                await session.scalars(
                    select(Achievement.achievement_id).where(
                        Achievement.character_id == character_id,
                        Achievement.achievement_id.like("feat.nareth.%"),
                    )
                )
            ).all()
        )
        cosmetics = set(
            (
                await session.scalars(
                    select(CharacterCosmetic.cosmetic_id).where(
                        CharacterCosmetic.character_id == character_id
                    )
                )
            ).all()
        )

    assert len(earned) == 13
    assert {
        "feat.nareth.sob_o_mesmo_eixo",
        "feat.nareth.a_camara_se_cala",
        "feat.nareth.o_que_retorna",
        "feat.nareth.referencia_afundada",
        "feat.nareth.eixos_fraturados",
        "feat.nareth.cacador_de_nareth",
        "feat.nareth.horizonte_sem_norte",
        "feat.nareth.a_medida_que_permanece",
        "feat.nareth.os_caminhos_que_nao_coincidem",
        "feat.nareth.a_rede_mede_ainda",
        "feat.nareth.planicies_de_nareth",
    } <= earned
    assert {
        "cosmetic.title.nareth.andarilho_de_nareth",
        "cosmetic.title.nareth.sobrevivente_do_eixo",
        "cosmetic.frame.nareth.eixo_fraturado",
        "cosmetic.title.nareth.cacador_de_nareth",
        "cosmetic.appearance.nareth.sobrevivente_de_nareth",
        "cosmetic.title.nareth.sem_norte",
        "cosmetic.frame.nareth.meridiano_antigo",
        "cosmetic.frame.nareth.planicies_de_nareth",
    } <= cosmetics


def test_nareth_cosmetic_catalog_matches_the_eight_published_entitlements():
    actual = {
        (definition.cosmetic_type, definition.name)
        for achievement_id, definition in COSMETIC_BY_ACHIEVEMENT.items()
        if achievement_id.startswith("feat.nareth.")
    }
    assert actual == {
        ("title", "Andarilho de Nareth"),
        ("title", "Sobrevivente do Eixo"),
        ("frame", "Eixo Fraturado"),
        ("title", "Caçador de Nareth"),
        ("appearance", "Sobrevivente de Nareth"),
        ("title", "Sem Norte"),
        ("frame", "Meridiano Antigo"),
        ("frame", "Planícies de Nareth"),
    }
