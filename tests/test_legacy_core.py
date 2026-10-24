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
    P36_CAMPAIGN_UNLOCK,
    P36_COMPLETION_OBJECTIVE,
    P36_COMPLETION_SOURCE_PREFIX,
    P36_CONTENT_VERSION,
    P36_QUEST_ID,
    P36_REWARD_SOURCE,
    REFUGE,
    REFUGE_BRAZIER,
    REFUGE_REGION,
    LegacyActionRejected,
    LegacyService,
)
from asterion.application.road import CONFINS_MARCO_DUPLO_BRAZIER, RoadService
from asterion.application.talents import TalentService
from asterion.application.world import WorldService
from asterion.bot.world_handlers import world_router
from asterion.bot.world_ui import render_legacy
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.dungeons import dungeon_completion_xp
from asterion.domain.legacy import LEGACY_XP_FACTORS, legacy_xp_factor
from asterion.domain.road import enemy_xp
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    CampaignJourney,
    CampaignJourneyMember,
    CampaignObjectiveCredit,
    Character,
    CharacterActiveArtSlot,
    CharacterDoctrine,
    CharacterEquipmentSlot,
    CharacterTalentChoice,
    EquipmentItem,
    GameActivity,
    LegacyAscensionRecord,
    Quest,
    RewardEvent,
    SocialGroup,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update


async def _seed_character(database, actor: int, *, level: int = 60, p36: bool = True):
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
            legacy_level=0,
            hp=stats.hp,
            max_hp=stats.hp,
            vigor=37,
            max_vigor=100,
            crowns=12345,
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
        if p36:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P36_QUEST_ID,
                    title="Conclusão da campanha principal",
                    status="completed",
                    step=8,
                    content_version=P36_CONTENT_VERSION,
                    state_version=8,
                    progress={
                        "completed": True,
                        "campaign_completed": True,
                        "legacy_eligible": True,
                        "completed_steps": list(range(1, 9)),
                    },
                )
            )
            session.add(
                Unlock(character_id=character_id, unlock_id=P36_CAMPAIGN_UNLOCK)
            )
            session.add(
                RewardEvent(
                    character_id=character_id,
                    source_id=P36_REWARD_SOURCE,
                )
            )
            session.add(
                CampaignObjectiveCredit(
                    character_id=character_id,
                    quest_id=P36_QUEST_ID,
                    objective_id=P36_COMPLETION_OBJECTIVE,
                    source_key=f"{P36_COMPLETION_SOURCE_PREFIX}{character_id}",
                    evidence={
                        "mission_id": P36_REWARD_SOURCE,
                        "first_journey_complete": True,
                        "legacy_eligible": True,
                        "world_state_mutated": False,
                    },
                )
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
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == P36_QUEST_ID,
                Quest.status == "completed",
            )
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
async def test_first_ascension_requires_p36_safe_place_and_level(database):
    cases = ((671_202, 59, True), (671_203, 60, False))
    service = LegacyService(database[1], "ocaso")
    for actor, level, has_p36 in cases:
        await _seed_character(database, actor, level=level, p36=has_p36)
        view = await service.view(actor)
        assert view is not None and not view.can_ascend
        prepared = await _prepare(service, actor)
        assert prepared is not None and prepared.confirmation_key is None


@pytest.mark.asyncio
async def test_campaign_completion_requires_the_actual_p36_reward_and_credit(database):
    actor = 671_206
    character_id, sessions = await _seed_character(database, actor, p36=False)
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P36_QUEST_ID,
                title="Conclusão da campanha principal",
                status="completed",
                step=8,
                content_version=P36_CONTENT_VERSION,
                state_version=8,
                progress={
                    "completed": True,
                    "campaign_completed": True,
                    "legacy_eligible": True,
                    "completed_steps": list(range(1, 9)),
                },
            )
        )
        session.add(Unlock(character_id=character_id, unlock_id=P36_CAMPAIGN_UNLOCK))
        session.add(RewardEvent(character_id=character_id, source_id=P36_REWARD_SOURCE))
        session.add(
            Quest(
                character_id=character_id,
                quest_id="S36",
                title="Prova opcional",
                status="completed",
                step=1,
                content_version=P36_CONTENT_VERSION,
                state_version=1,
                progress={"completed": True},
            )
        )
        session.add(
            RewardEvent(character_id=character_id, source_id="mission.confins.s36")
        )

    view = await LegacyService(sessions, "ocaso").view(actor)
    assert view is not None and not view.can_ascend
    assert not view.campaign_complete


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
