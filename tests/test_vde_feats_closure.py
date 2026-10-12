import pytest
from sqlalchemy import select

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.application.vde_feats import (
    VDE_BASE_CREATURES,
    VDE_CAMPAIGN_LOCATIONS,
    VDE_PERMANENT_BRAZIERS,
    VDE_VARIANT_TYPES,
    VDE_WORLD_ELITES,
    reconcile_vde_feats_for_character,
)
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    CharacterCosmetic,
    LocationDiscovery,
)
from tests.test_vde_s7_p8_integration import _seed_vde_ready


@pytest.mark.asyncio
async def test_unblocked_vales_feats_and_cosmetics_reconcile_idempotently(database):
    character_id, sessions = await _seed_vde_ready(
        database, 991901, level=20, round_ready=False
    )

    async with sessions.begin() as session:
        existing_locations = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character_id
                    )
                )
            ).all()
        )
        existing_braziers = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(Brazier.character_id == character_id)
                )
            ).all()
        )
        session.add_all(
            LocationDiscovery(character_id=character_id, location_id=location_id)
            for location_id in VDE_CAMPAIGN_LOCATIONS - existing_locations
        )
        session.add_all(
            Brazier(character_id=character_id, brazier_id=brazier_id)
            for brazier_id in VDE_PERMANENT_BRAZIERS - existing_braziers
        )
        session.add_all(
            BestiaryEntry(
                character_id=character_id,
                creature_id=creature_id,
                bkp=60,
                wins=1,
                stage="dominated",
            )
            for creature_id in VDE_BASE_CREATURES | VDE_WORLD_ELITES
        )
        variant_creature = sorted(VDE_BASE_CREATURES)[0]
        session.add_all(
            BestiaryEvidence(
                character_id=character_id,
                creature_id=variant_creature,
                evidence_id=f"variant:{variant}",
                category="variant",
            )
            for variant in VDE_VARIANT_TYPES
        )
        await session.flush()

        first = await reconcile_vde_feats_for_character(session, character_id)
        second = await reconcile_vde_feats_for_character(session, character_id)

        assert {
            "feat.vde.andarilho_dos_vales",
            "feat.vde.cacador_dos_vales",
            "feat.vde.entre_galhos_e_presas",
        } <= set(first)
        assert second == ()

    async with sessions() as session:
        earned = set(
            (
                await session.scalars(
                    select(Achievement.achievement_id).where(
                        Achievement.character_id == character_id
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

    assert {
        "feat.vde.andarilho_dos_vales",
        "feat.vde.cacador_dos_vales",
        "feat.vde.entre_galhos_e_presas",
    } <= earned
    assert {
        "cosmetic.title.vde.andarilho_dos_vales",
        "cosmetic.title.vde.cacador_dos_vales",
        "cosmetic.appearance.vde.sobrevivente_dos_vales",
    } <= cosmetics


def test_vales_cosmetic_catalog_has_all_eight_regional_entitlements():
    expected = {
        "feat.vde.andarilho_dos_vales": (
            "cosmetic.title.vde.andarilho_dos_vales",
            "title",
            "Andarilho dos Vales",
        ),
        "feat.vde.o_berco_silencia": (
            "cosmetic.title.vde.sobrevivente_do_berco",
            "title",
            "Sobrevivente do Berço",
        ),
        "feat.vde.cacador_dos_vales": (
            "cosmetic.title.vde.cacador_dos_vales",
            "title",
            "Caçador dos Vales",
        ),
        "feat.vde.nomes_presos_madeira": (
            "cosmetic.title.vde.nome_entalhado",
            "title",
            "Nome Entalhado",
        ),
        "feat.vde.raizes_fraturadas": (
            "cosmetic.frame.vde.raiz_fraturada",
            "frame",
            "Raiz Fraturada",
        ),
        "feat.vde.a_rede_nao_dorme": (
            "cosmetic.frame.vde.pedra_enlacada",
            "frame",
            "Pedra Enlaçada",
        ),
        "feat.vde.vales_dos_enforcados": (
            "cosmetic.frame.vde.vales_dos_enforcados",
            "frame",
            "Vales dos Enforcados",
        ),
        "feat.vde.entre_galhos_e_presas": (
            "cosmetic.appearance.vde.sobrevivente_dos_vales",
            "appearance",
            "Sobrevivente dos Vales",
        ),
    }

    actual = {
        achievement_id: (
            definition.cosmetic_id,
            definition.cosmetic_type,
            definition.name,
        )
        for achievement_id, definition in COSMETIC_BY_ACHIEVEMENT.items()
        if achievement_id.startswith("feat.vde.")
    }
    assert actual == expected
