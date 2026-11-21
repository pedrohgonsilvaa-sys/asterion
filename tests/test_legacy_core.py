"""Focused PostgreSQL tests for the first public Legacy Ascension."""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.active_arts import (
    ACTIVE_ART_DEFINITIONS,
    load_active_art_configuration,
)
from asterion.application.doctrines import DoctrineRejected, DoctrineService
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.legacy import (
    REFUGE,
    REFUGE_BRAZIER,
    REFUGE_REGION,
    LegacyActionRejected,
    LegacyReason,
    LegacyService,
)
from asterion.application.road import CONFINS_MARCO_DUPLO_BRAZIER, RoadService
from asterion.application.talents import TalentService
from asterion.application.world import WorldService
from asterion.bot.world_handlers import world_router
from asterion.bot.world_ui import render_legacy
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.dungeons import dungeon_completion_xp
from asterion.domain.legacy import (
    LEGACY_ASCENSION_COSTS,
    LEGACY_XP_FACTORS,
    legacy_ascension_cost,
    legacy_xp_factor,
)
from asterion.domain.road import enemy_xp
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    CampaignJourney,
    CampaignJourneyMember,
    Character,
    CharacterActiveArtSlot,
    CharacterDoctrine,
    CharacterEquipmentSlot,
    CharacterTalentChoice,
    EquipmentItem,
    GameActivity,
    LegacyAscensionRecord,
    RewardEvent,
    SocialGroup,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update

# Campaign journey ids used only to seed an activity lock (not a Legado requirement).
P36_QUEST_ID = "P36"


async def _seed_character(
    database, actor: int, *, level: int = 60, legacy_level: int = 0, crowns: int = 12345
):
    _, sessions = database
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(char)) for char in str(actor)[-5:])
    path = "bastiao"
    stats = resolve_combat_stats(
        "sentinela", level, "remanescente", selected_path=path
    )
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        character = Character(
            id=character_id,
            telegram_id=actor,
            server_id="ocaso",
            name=f"Leg{suffix}",
            race="remanescente",
            character_class="sentinela",
            selected_path=path,
            stage="menu:ready",
            ruleset_version="gdd-1.6.0",
            level=level,
            xp=817,
            legacy_level=legacy_level,
            hp=stats.hp,
            max_hp=stats.hp,
            vigor=37,
            max_vigor=100,
            crowns=crowns,
            combat_configuration_version=4,
        )
        session.add(character)
        await session.flush()
        session.add(
            WorldState(character_id=character_id, region=REFUGE_REGION, location=REFUGE)
        )
        session.add(Brazier(character_id=character_id, brazier_id=REFUGE_BRAZIER))
        session.add(
            Unlock(character_id=character_id, unlock_id="class_trial_completed")
        )
    return character_id, sessions


async def _prepare(service: LegacyService, actor: int):
    view = await service.view(actor)
    assert view is not None
    return await service.prepare(
        actor, expected_configuration_version=view.configuration_version
    )


@pytest.mark.asyncio
async def test_first_ascension_preserves_campaign_and_items_but_dormants_high_level_loadout(
    database,
):
    actor = 671_201
    character_id, sessions = await _seed_character(database, actor)
    doctrine_id = uuid4()
    path = "bastiao"
    async with sessions.begin() as session:
        high_item = EquipmentItem(
            id=uuid4(),
            character_id=character_id,
            source_key=f"test-legacy:{uuid4()}",
            item_name="Armadura de teste preservada",
            rarity="epic",
            slot="Torso",
            item_level=55,
            bound=True,
            payload={},
        )
        session.add(high_item)
        await session.flush()
        session.add(
            CharacterEquipmentSlot(
                character_id=character_id,
                slot="Torso",
                equipment_item_id=high_item.id,
            )
        )
        high_art = next(
            definition
            for definition in ACTIVE_ART_DEFINITIONS.values()
            if definition.character_class == "sentinela" and definition.min_level == 52
        )
        session.add(
            CharacterActiveArtSlot(
                character_id=character_id, slot=1, art_id=high_art.art_id
            )
        )
        high_talent = next(
            talent
            for talent in TALENTS_BY_CLASS["sentinela"]
            if talent.level == 55
        )
        session.add(
            CharacterTalentChoice(
                character_id=character_id,
                point_slot=1,
                talent_id=high_talent.talent_id,
                publicly_acquired=True,
            )
        )
        session.add(
            Brazier(
                character_id=character_id,
                brazier_id=CONFINS_MARCO_DUPLO_BRAZIER,
            )
        )
        session.add(
            CharacterDoctrine(
                id=doctrine_id,
                character_id=character_id,
                name="Loadout de campanha",
                configuration={
                    "path": path,
                    "equipment": {},
                    "arts": {"1": high_art.art_id},
                    "talents": [
                        {"point_slot": 1, "talent_id": high_talent.talent_id}
                    ],
                },
            )
        )

    service = LegacyService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None and view.can_ascend
    prepared = await _prepare(service, actor)
    assert prepared is not None and prepared.confirmation_key is not None
    result = await service.confirm(actor, prepared.confirmation_key)
    assert result is not None and result.succeeded
    assert (result.legacy_level, result.level, result.xp) == (1, 1, 0)
    assert result.location == REFUGE

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.character_class, character.selected_path) == ("sentinela", "bastiao")
        assert (character.vigor, character.crowns, character.combat_configuration_version) == (
            37,
            12345,
            5,
        )
        assert await session.get(EquipmentItem, high_item.id) is not None
        assert await session.scalar(
            select(CharacterEquipmentSlot.equipment_item_id).where(
                CharacterEquipmentSlot.character_id == character_id
            )
        ) is None
        assert await session.get(CharacterActiveArtSlot, (character_id, 1)) is not None
        arts = await load_active_art_configuration(session, character)
        assert arts.slots == ()
        equipment = await load_equipment_configuration(session, character)
        assert equipment.talent_choices == ()
        choice = await session.get(CharacterTalentChoice, (character_id, 1))
        assert choice is not None and choice.talent_id == high_talent.talent_id
        assert await session.scalar(
            select(LegacyAscensionRecord.id).where(
                LegacyAscensionRecord.character_id == character_id
            )
        )

    talent_view = await TalentService(sessions, "ocaso").view(actor)
    assert talent_view is not None
    assert talent_view.choices[0].talent_id == high_talent.talent_id
    assert not talent_view.choices[0].active
    doctrines = DoctrineService(sessions, "ocaso")
    doctrine_view = await doctrines.view(actor)
    assert doctrine_view is not None
    saved_doctrine = next(
        item for item in doctrine_view.doctrines if item.doctrine_id == doctrine_id
    )
    assert not saved_doctrine.can_apply
    assert saved_doctrine.incomplete_reason is not None
    assert saved_doctrine.configuration["arts"] == {"1": high_art.art_id}
    assert saved_doctrine.configuration["talents"] == [
        {"point_slot": 1, "talent_id": high_talent.talent_id}
    ]
    with pytest.raises(DoctrineRejected):
        await doctrines.apply(
            actor,
            doctrine_id,
            saved_doctrine.revision,
            doctrine_view.configuration_version,
        )
    blocked_travel = await RoadService(sessions, "ocaso").travel_brazier(
        actor, CONFINS_MARCO_DUPLO_BRAZIER
    )
    assert blocked_travel is None or blocked_travel.location == REFUGE
    final_view = await service.view(actor)
    assert final_view is not None
    assert "Ascensão concluída" in render_legacy(final_view, succeeded=True).text


@pytest.mark.asyncio
async def test_legado_i_requires_nv60_not_p36_and_nv59_is_rejected(database):
    service = LegacyService(database[1], "ocaso")
    # Nv.59 without campaign: blocked by level.
    await _seed_character(database, 671_202, level=59)
    view = await service.view(671_202)
    assert view is not None and not view.can_ascend
    assert LegacyReason.LEVEL_REQUIRED in view.reasons
    prepared = await _prepare(service, 671_202)
    assert prepared is not None and prepared.confirmation_key is None
    # Nv.60 without any P36 or campaign row: Legado I is allowed.
    await _seed_character(database, 671_203, level=60)
    view = await service.view(671_203)
    assert view is not None and view.can_ascend
    assert view.reasons == ()
    assert view.ascension_cost == 0


@pytest.mark.asyncio
async def test_legado_ladder_costs_and_requirements_i_to_v(database):
    actor = 671_220
    character_id, sessions = await _seed_character(database, actor, crowns=200_000)
    service = LegacyService(sessions, "ocaso")
    # Canonical costs to ascend into I..V (author decision).
    assert LEGACY_ASCENSION_COSTS == {1: 0, 2: 10_000, 3: 20_000, 4: 40_000, 5: 80_000}
    assert [legacy_ascension_cost(rank) for rank in range(5)] == [0, 10_000, 20_000, 40_000, 80_000]
    assert [legacy_xp_factor(rank) for rank in range(6)] == [
        LEGACY_XP_FACTORS[rank] for rank in range(6)
    ]

    expected_crowns = 200_000
    for rank in range(5):
        # Each step: Nv.60 again (Ascension resets to Nv.1), safe place, enough Coroas.
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            assert character is not None
            character.level = 60
        view = await service.view(actor)
        assert view is not None and view.legacy_level == rank
        assert view.ascension_cost == legacy_ascension_cost(rank)
        assert view.can_ascend, view.reasons
        prepared = await _prepare(service, actor)
        assert prepared is not None and prepared.confirmation_key is not None
        result = await service.confirm(actor, prepared.confirmation_key)
        assert result is not None and result.succeeded, result
        assert (result.legacy_level, result.level, result.xp) == (rank + 1, 1, 0)
        expected_crowns -= legacy_ascension_cost(rank)
        async with sessions() as session:
            character = await session.get(Character, character_id)
            assert character is not None
            assert character.legacy_level == rank + 1
            assert character.crowns == expected_crowns
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"legacy.ascension:{character_id}:{rank + 1}",
                )
            )

    # Legado V is the maximum: no further ascension at Nv.60.
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.level = 60
        character.crowns = 10**9
    maxed = await service.view(actor)
    assert maxed is not None and maxed.legacy_level == 5 and not maxed.can_ascend
    assert LegacyReason.LEGACY_MAX_REACHED in maxed.reasons


@pytest.mark.asyncio
async def test_legado_ii_to_v_require_enough_crowns(database):
    actor = 671_221
    await _seed_character(database, actor, legacy_level=1, crowns=9_999)
    service = LegacyService(database[1], "ocaso")
    view = await service.view(actor)
    assert view is not None and view.ascension_cost == 10_000
    assert not view.can_ascend
    assert LegacyReason.CROWNS_REQUIRED in view.reasons
    assert (await _prepare(service, actor)).confirmation_key is None


@pytest.mark.asyncio
async def test_legado_i_is_not_gated_by_campaign_roster_free_of_p36(database):
    actor = 671_222
    await _seed_character(database, actor, level=60)
    view = await LegacyService(database[1], "ocaso").view(actor)
    assert view is not None and view.can_ascend
    assert not any(reason.value.startswith("campaign") for reason in view.reasons)


@pytest.mark.asyncio
async def test_ascension_rejects_unsafe_location_and_foreground_activity(database):
    actor = 671_207
    character_id, sessions = await _seed_character(database, actor)
    service = LegacyService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = "Estrada das Cinzas"
        world.region = REFUGE_REGION
    view = await service.view(actor)
    assert view is not None and not view.can_ascend
    unsafe = await _prepare(service, actor)
    assert unsafe is not None and unsafe.confirmation_key is None

    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = REFUGE
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="test_active_foreground",
                status="active",
                state_version=0,
                ruleset_version="gdd-1.6.0",
            )
        )
    locked = await service.view(actor)
    assert locked is not None and not locked.can_ascend
    blocked = await _prepare(service, actor)
    assert blocked is not None and blocked.confirmation_key is None


@pytest.mark.asyncio
async def test_ascension_rejects_active_or_paused_campaign_roster(database):
    actor = 671_209
    character_id, sessions = await _seed_character(database, actor)
    journey_id = uuid4()
    group_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            SocialGroup(
                id=group_id,
                server_id="ocaso",
                leader_character_id=character_id,
            )
        )
        await session.flush()
        session.add(
            CampaignJourney(
                id=journey_id,
                group_id=group_id,
                quest_id=P36_QUEST_ID,
                checkpoint="p36.o_regente_fraturado",
                technical_host_character_id=character_id,
                status="paused",
            )
        )
        session.add(
            CampaignJourneyMember(
                journey_id=journey_id,
                character_id=character_id,
                role="eligible",
                status="active",
                checkpoint_snapshot="p36.o_regente_fraturado",
            )
        )
    view = await LegacyService(sessions, "ocaso").view(actor)
    assert view is not None and not view.can_ascend


@pytest.mark.asyncio
async def test_confirmation_becomes_stale_when_configuration_changes(database):
    actor = 671_208
    character_id, sessions = await _seed_character(database, actor)
    service = LegacyService(sessions, "ocaso")
    prepared = await _prepare(service, actor)
    assert prepared is not None and prepared.confirmation_key is not None
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.combat_configuration_version += 1
    result = await service.confirm(actor, prepared.confirmation_key)
    assert result is not None and not result.succeeded
    assert result.reason == "stale_confirmation"
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.legacy_level, character.level, character.xp) == (0, 60, 817)


@pytest.mark.asyncio
async def test_confirmation_is_single_use_and_concurrent_callbacks_ascend_once(database):
    actor = 671_204
    character_id, sessions = await _seed_character(database, actor)
    service = LegacyService(sessions, "ocaso")
    prepared = await _prepare(service, actor)
    assert prepared is not None and prepared.confirmation_key is not None

    outcomes = await asyncio.gather(
        service.confirm(actor, prepared.confirmation_key),
        service.confirm(actor, prepared.confirmation_key),
        return_exceptions=True,
    )
    assert sum(not isinstance(value, BaseException) for value in outcomes) == 1
    assert sum(
        isinstance(value, LegacyActionRejected) for value in outcomes
    ) == 1
    async with sessions() as session:
        assert await session.scalar(
            select(LegacyAscensionRecord.id).where(
                LegacyAscensionRecord.character_id == character_id
            )
        )


@pytest.mark.asyncio
async def test_failed_ascension_transaction_rolls_back_all_changes(database, monkeypatch):
    actor = 671_205
    character_id, sessions = await _seed_character(database, actor)
    service = LegacyService(sessions, "ocaso")
    prepared = await _prepare(service, actor)
    assert prepared is not None and prepared.confirmation_key is not None

    async def fail_after_level_change(*args, **kwargs):
        raise RuntimeError("injected failure before commit")

    monkeypatch.setattr(
        "asterion.application.legacy.load_active_art_configuration",
        fail_after_level_change,
    )
    with pytest.raises(RuntimeError, match="injected failure"):
        await service.confirm(actor, prepared.confirmation_key)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.legacy_level, character.level, character.xp) == (0, 60, 817)
        assert await session.scalar(
            select(LegacyAscensionRecord.id).where(
                LegacyAscensionRecord.character_id == character_id
            )
        ) is None


def test_legacy_factors_scale_enemy_and_dungeon_xp_only():
    assert tuple(legacy_xp_factor(rank) for rank in range(6)) == tuple(
        LEGACY_XP_FACTORS[rank] for rank in range(6)
    )
    base_enemy = enemy_xp(3, "uncommon", player_level=3)
    legacy_enemy = enemy_xp(
        3, "uncommon", player_level=3, legacy_factor=legacy_xp_factor(1)
    )
    assert abs(legacy_enemy - base_enemy * 1.75) <= 15
    base_dungeon = dungeon_completion_xp(6, "stable")
    legacy_dungeon = dungeon_completion_xp(
        6, "stable", legacy_factor=Decimal("1.75")
    )
    assert abs(legacy_dungeon - base_dungeon * 1.75) <= 10
    first_clear = dungeon_completion_xp(6, "stable", first_clear=True)
    first_clear_legacy = dungeon_completion_xp(
        6,
        "stable",
        first_clear=True,
        legacy_factor=Decimal("1.75"),
    )
    assert first_clear_legacy > first_clear


@pytest.mark.asyncio
async def test_public_legacy_callbacks_prepare_confirm_and_reject_replay(database):
    actor = 671_210
    character_id, sessions = await _seed_character(database, actor)
    legacy = LegacyService(sessions, "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(world_router(WorldService(sessions, "ocaso"), {}, legacy=legacy))
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)

    await dispatcher.feed_raw_update(
        bot, callback_update("legacy:root", actor=actor, update_id=31)
    )
    assert "Multiplicador de XP elegível" in bot.session.make_request.call_args.args[1].text

    view = await legacy.view(actor)
    assert view is not None and view.can_ascend
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            f"legacy:prepare:{view.configuration_version}",
            actor=actor,
            update_id=32,
        ),
    )
    confirmation_screen = bot.session.make_request.call_args.args[1]
    assert "não pode ser desfeita" in confirmation_screen.text
    confirmation_button = next(
        button
        for row in confirmation_screen.reply_markup.inline_keyboard
        for button in row
        if button.text == "Confirmar Ascensão"
    )

    await dispatcher.feed_raw_update(
        bot,
        callback_update(confirmation_button.callback_data, actor=actor, update_id=33),
    )
    assert "Ascensão concluída" in bot.session.make_request.call_args.args[1].text
    await dispatcher.feed_raw_update(
        bot,
        callback_update(confirmation_button.callback_data, actor=actor, update_id=34),
    )
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert (character.legacy_level, character.level, character.xp) == (1, 1, 0)
        assert await session.scalar(
            select(LegacyAscensionRecord.id).where(
                LegacyAscensionRecord.character_id == character_id
            )
        )


@pytest.mark.asyncio
async def test_ascension_is_allowed_at_any_discovered_permanent_brazier(database):
    """P36 ends in the Confins and Braseiro travel stays inside one region."""
    actor = 671_299
    character_id, sessions = await _seed_character(database, actor)
    service = LegacyService(sessions, "ocaso")
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = "Confins do Véu"
        world.location = "Marcha Nebulosa"
    undiscovered = await service.view(actor)
    assert undiscovered is not None and not undiscovered.can_ascend

    async with sessions.begin() as session:
        session.add(
            Brazier(character_id=character_id, brazier_id=CONFINS_MARCO_DUPLO_BRAZIER)
        )
    prepared = await _prepare(service, actor)
    assert prepared is not None and prepared.confirmation_key is not None
    result = await service.confirm(actor, prepared.confirmation_key)
    assert result is not None and result.succeeded
    assert (result.legacy_level, result.level, result.location) == (1, 1, REFUGE)
