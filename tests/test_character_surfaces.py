from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from asterion.application.character_surfaces import (
    MAX_HISTORY_CHARACTERS,
    CharacterSurfacesService,
    HistoryInputResult,
)
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.knowledge_catalog import CODEX_BY_ID
from asterion.application.p2 import CHARNECA_LOCATION_ID
from asterion.domain.equipment import EquipmentSlot, assign_equipment_instance_id
from asterion.domain.equipment_modifications import (
    enchantment_potency_for,
    rune_potency_for,
)
from asterion.domain.road import materialize_equipment
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CharacterEquipmentSlot,
    CharacterProfile,
    CharacterTalentChoice,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    LocationDiscovery,
)
from tests.test_road_integration import _seed_road


@pytest.mark.asyncio
async def test_attributes_match_authoritative_combat_configuration_with_path_talent_and_equipment(
    database,
):
    actor, _ = await _seed_road(database, actor=890101)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 10
        character.selected_path = "bastiao"
        character.hp = Decimal("350")
        character.max_hp = Decimal("702")
        talent = next(
            definition
            for definition in TALENTS_BY_CLASS[character.character_class]
            if definition.level == 5 and definition.attack_percent
        )
        session.add(
            CharacterTalentChoice(
                character_id=character.id,
                point_slot=1,
                talent_id=talent.talent_id,
            )
        )
        payload = materialize_equipment(
            "character-surfaces-stat-fixture",
            "Raro",
            10,
            forced_name="Arma do Caminhante",
            forced_slot="Principal",
        )
        payload["enhancement"] = 7
        payload["rune"] = {
            "family": "Brasa",
            "effect": "ATQ",
            "rarity": "Rara",
            "grade": 1,
            "potency": rune_potency_for("Brasa", "Rara", 1),
            "bound": False,
        }
        payload["enchantment"] = {
            "family": "Fio Cinéreo",
            "effect": "ATQ",
            "rarity": "Raro",
            "grade": 1,
            "potency": enchantment_potency_for("Fio Cinéreo", "Raro", 1),
            "bound": False,
            "enchantment_id": "enchantment.tdo.fio_cinereo.raro",
            "name": "Fio Cinéreo",
        }
        item_id, payload = assign_equipment_instance_id(payload)
        item = EquipmentItem(
            id=item_id,
            character_id=character.id,
            source_key=f"test.character-surfaces.{item_id}",
            item_name=payload["item_name"],
            rarity=payload["rarity"],
            slot=payload["slot"],
            item_level=payload["item_level"],
            bound=False,
            payload=payload,
        )
        session.add(item)
        await session.flush()
        session.add(
            CharacterEquipmentSlot(
                character_id=character.id,
                slot=EquipmentSlot.PRINCIPAL.value,
                equipment_item_id=item_id,
            )
        )
        character_id = character.id

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_equipment_configuration(session, character, lock_rows=False)
        expected = resolve_character_combat_stats(character, configuration)

    view = await CharacterSurfacesService(sessions, "ocaso").attributes(actor)
    assert view is not None
    assert view.hp == Decimal("350")
    assert view.max_hp == expected.hp
    assert view.attack == expected.attack
    assert view.defense == expected.defense
    assert view.agility == expected.agility
    assert view.perception == expected.per
    assert view.critical == expected.crit
    assert view.evasion == expected.evasion
    assert view.block == expected.block
    assert view.selected_path == "bastiao"


@pytest.mark.asyncio
async def test_profile_history_is_optional_persistent_escaped_and_prompt_versioned(database):
    actor, _ = await _seed_road(database, actor=890102)
    service = CharacterSurfacesService(database[1], "ocaso")

    initial = await service.profile(actor)
    assert initial is not None and initial.history is None and initial.revision == 0
    assert await service.begin_history_input(actor, 0, 7001)
    raw_history = '<script>alert("cinzas")</script>\nUma história & memória.'
    assert await service.save_history(actor, 7001, raw_history) == HistoryInputResult.SAVED

    reopened = await CharacterSurfacesService(database[1], "ocaso").profile(actor)
    assert reopened is not None
    assert reopened.history == raw_history
    assert reopened.revision == 1
    assert await service.begin_history_input(actor, 1, 7002)
    assert await service.save_history(actor, 7001, "resposta atrasada") == HistoryInputResult.STALE
    assert await service.save_history(actor, 7002, "   \n\t ") == HistoryInputResult.EMPTY
    assert (
        await service.save_history(actor, 7002, "x" * (MAX_HISTORY_CHARACTERS + 1))
        == HistoryInputResult.TOO_LONG
    )
    assert await service.save_history(actor, 7002, "A versão atual") == HistoryInputResult.SAVED
    await service.cancel_history_input(actor)

    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        profile = await session.get(CharacterProfile, character.id)
        assert profile.history == "A versão atual"
        assert profile.history_prompt_message_id is None
        assert profile.revision == 2


@pytest.mark.asyncio
async def test_knowledge_appears_only_from_persisted_records_and_known_locations(database):
    actor, _ = await _seed_road(database, actor=890103)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character_id = character.id
        await session.execute(
            delete(BestiaryEvidence).where(BestiaryEvidence.character_id == character_id)
        )
        await session.execute(
            delete(BestiaryEntry).where(BestiaryEntry.character_id == character_id)
        )

    service = CharacterSurfacesService(sessions, "ocaso")
    empty = await service.knowledge(actor)
    assert empty is not None
    assert empty.bestiary == ()
    assert empty.codex_entries == ()
    assert empty.achievements == ()

    async with sessions.begin() as session:
        session.add(
            BestiaryEntry(
                character_id=character_id, creature_id="dog_cinereo", bkp=7, stage="observed"
            )
        )
        session.add_all(
            [
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="first_observation",
                    category="observation",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="habitat:Charneca da Fuligem",
                    category="habitat",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="variant:furious",
                    category="variant",
                ),
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id="dog_cinereo",
                    evidence_id="variant:future_unknown",
                    category="variant",
                ),
            ]
        )
        session.add(
            CodexEntry(character_id=character_id, entry_id="codex.history.antigos_asterianos")
        )
        session.add(
            CodexEntry(character_id=character_id, entry_id="codex.location.camara_do_poente")
        )
        session.add(
            CodexFragment(
                character_id=character_id,
                entry_id="codex.history.antigos_asterianos",
                fragment_id="codex.fragment.antigos_asterianos.outras_ancoras_existiram",
            )
        )
        session.add_all(
            [
                Achievement(character_id=character_id, achievement_id="feat.tdo.cinzas_na_estrada"),
                Achievement(
                    character_id=character_id, achievement_id="feat.tdo.campaign.completed"
                ),
            ]
        )

    observed = await service.knowledge(actor)
    assert observed is not None
    assert len(observed.bestiary) == 1
    creature = observed.bestiary[0]
    assert creature.name == "Cão Cinéreo"
    assert creature.habitats == ()
    assert creature.variants == ("Furioso",)
    assert observed.codex_entries[0].entry_id == "codex.history.antigos_asterianos"
    assert len(observed.codex_entries[0].fragments) == 1
    assert "codex.location.camara_do_poente" not in {
        entry.entry_id for entry in observed.codex_entries
    }
    assert "Âncora do Poente" not in {entry.title for entry in observed.codex_entries}
    assert [item.name for item in observed.achievements] == ["Cinzas na Estrada"]

    async with sessions.begin() as session:
        session.add_all(
            [
                LocationDiscovery(character_id=character_id, location_id=CHARNECA_LOCATION_ID),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.camara_do_poente",
                ),
            ]
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "dog_cinereo",
            )
        )
        entry.stage = "studied"
        session.add(
            BestiaryEvidence(
                character_id=character_id,
                creature_id="dog_cinereo",
                evidence_id="material:material.tdo.couro_escoriado",
                category="material",
            )
        )
        session.add(
            BestiaryEvidence(
                character_id=character_id,
                creature_id="dog_cinereo",
                evidence_id="action:bite",
                category="action",
            )
        )

    studied = await service.knowledge(actor)
    assert studied is not None
    creature = studied.bestiary[0]
    assert creature.habitats == (CHARNECA_LOCATION_ID,)
    assert creature.materials == ("Couro Escoriado",)
    assert "Mordida Faminta" in creature.observed_actions
    assert "codex.location.camara_do_poente" in {
        entry.entry_id for entry in studied.codex_entries
    }


@pytest.mark.asyncio
async def test_player_surfaces_do_not_mutate_game_progress_when_opened(database):
    actor, _ = await _seed_road(database, actor=890104)
    service = CharacterSurfacesService(database[1], "ocaso")
    assert await service.attributes(actor) is not None
    assert await service.profile(actor) is not None
    assert await service.knowledge(actor) is not None
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2720
        assert character.crowns == 0
        assert character.vigor == 100
        assert character.combat_configuration_version == 0
        assert await session.scalar(select(func.count()).select_from(CharacterProfile)) == 0


def test_catalog_has_unique_ids_and_official_codex_metadata():
    assert len(CODEX_BY_ID) == len({item.entry_id for item in CODEX_BY_ID.values()})
    assert CODEX_BY_ID["codex.mystery.ancora_do_poente"].title == "Âncora do Poente"
    assert all(item.category for item in CODEX_BY_ID.values())
