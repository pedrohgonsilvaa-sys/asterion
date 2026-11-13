"""Focused public-flow coverage supporting the long organic P1–P12 journey."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import func, select

from asterion.application.creation import CreationService
from asterion.application.equipment import EquipmentService
from asterion.application.p1 import P1Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.talents import TalentService
from asterion.application.weapon_metadata import (
    equipped_weapon_compatibility_tags,
    resolve_equipment_weapon,
)
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.combat_ui import CombatCallback, P1CombatCallback
from asterion.bot.creation_handlers import creation_router
from asterion.bot.creation_ui import CreationCallback
from asterion.bot.p1_handlers import p1_router
from asterion.domain.prologue import POST_COMBAT_STAGE, PROFILE
from asterion.infrastructure.db.models import (
    Character,
    CreationDraft,
    EquipmentItem,
    Quest,
    RewardEvent,
)
from tests.helpers.tdo_playthrough import TDOPlaythrough


def _message_update(text: str, *, actor: int, update_id: int) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1,
            "from": {"id": actor, "is_bot": False, "first_name": "Player"},
            "chat": {"id": actor, "type": "private"},
            "text": text,
            "entities": [{"type": "bot_command", "offset": 0, "length": 6}]
            if text == "/start"
            else [],
        },
    }


def _callback_update(data: str, *, actor: int, update_id: int) -> dict:
    return {
        "update_id": update_id,
        "callback_query": {
            "id": str(update_id),
            "from": {"id": actor, "is_bot": False, "first_name": "Player"},
            "chat_instance": "alpha-a1-test",
            "data": data,
            "message": {
                "message_id": update_id,
                "date": 1,
                "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
                "chat": {"id": actor, "type": "private"},
                "text": "Asterion",
            },
        },
    }


@pytest.mark.asyncio
async def test_public_start_creation_tutorial_and_p1_survive_reconnect(database):
    """Create from Telegram updates, then finish P1 only through public services."""
    actor = 7_100_000_000_000 + uuid4().int % 900_000_000_000
    sessions = database[1]
    creation = CreationService(sessions, "ocaso")
    prologue = PrologueService(sessions, "ocaso", PROFILE)
    world = WorldService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    p1 = P1Service(sessions, "ocaso")

    telegram = Bot("123456:local-test-token")
    telegram.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        creation_router(creation, {}, prologue=prologue, world=world, p1=p1, road=road)
    )
    dispatcher.include_router(p1_router(p1, {}))
    dispatcher.include_router(combat_router(prologue, {}, world=world, road=road))

    update_id = 1
    await dispatcher.feed_raw_update(
        telegram, _message_update("/start", actor=actor, update_id=update_id)
    )
    update_id += 1
    first = await creation.resume(actor)
    assert first is not None and first.step == "name"

    await dispatcher.feed_raw_update(
        telegram, _message_update("/start", actor=actor, update_id=update_id)
    )
    update_id += 1
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(CreationDraft)) == 1
        assert await session.scalar(select(func.count()).select_from(Character)) == 0

    await dispatcher.feed_raw_update(
        telegram, _message_update("Aster", actor=actor, update_id=update_id)
    )
    update_id += 1
    state = await creation.resume(actor)
    assert state is not None and state.step == "gender"

    for action in ("g0", "r0", "choose", "c0", "choose", "confirm"):
        callback = CreationCallback(
            draft=state.id.hex,
            version=state.version,
            action=action,
        ).pack()
        await dispatcher.feed_raw_update(
            telegram, _callback_update(callback, actor=actor, update_id=update_id)
        )
        update_id += 1
        state = await creation.resume(actor)
        assert state is not None

    assert (state.name, state.race, state.character_class, state.step) == (
        "Aster",
        "remanescente",
        "sentinela",
        "cinzas_na_estrada:intro",
    )
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor, Character.server_id == "ocaso")
        )
        assert character is not None
        character_id = character.id
        assert await session.scalar(select(func.count()).select_from(Character)) == 1

    # Repeated /start resumes the existing character and the public tutorial button.
    await dispatcher.feed_raw_update(
        telegram, _message_update("/start", actor=actor, update_id=update_id)
    )
    update_id += 1
    await dispatcher.feed_raw_update(
        telegram,
        _callback_update("prologue:continue", actor=actor, update_id=update_id),
    )
    update_id += 1
    tutorial = await prologue.resume(actor)
    assert tutorial is not None and tutorial.combat.tutorial_stage == "basics"

    for action in ("attack", "defend", "art"):
        callback = CombatCallback(
            activity=tutorial.activity_id.hex,
            version=tutorial.combat.version,
            action=action,
        ).pack()
        await dispatcher.feed_raw_update(
            telegram, _callback_update(callback, actor=actor, update_id=update_id)
        )
        update_id += 1
        tutorial = await prologue.resume(actor)
    assert tutorial is not None and tutorial.combat.tutorial_stage == "normal"

    driver = TDOPlaythrough(actor, sessions)
    tutorial = await driver.combat_to_result(
        tutorial,
        lambda current, action: prologue.action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: PrologueService(sessions, "ocaso", PROFILE).resume(actor),
        label="A1 · prólogo público",
    )
    assert tutorial.stage == POST_COMBAT_STAGE
    brazier = await world.resume(actor)
    assert brazier is not None and brazier.kind == "brazier"
    ready = await world.rest(actor)
    assert ready is not None and ready.kind == "menu"
    async with sessions() as session:
        character_after_tutorial = await session.get(Character, character_id)
        assert character_after_tutorial is not None
        xp_before_p1 = character_after_tutorial.xp

    quest = await p1.resume(actor)
    assert quest is not None and quest.status == "active" and quest.step == 1
    stale_version = quest.state_version
    for action in ("follow", "examine:pegadas", "examine:sulcos"):
        await dispatcher.feed_raw_update(
            telegram,
            _callback_update(
                f"p1:{quest.state_version}:{action}",
                actor=actor,
                update_id=update_id,
            ),
        )
        update_id += 1
        quest = await p1.resume(actor)
    assert quest is not None and quest.combat is not None and quest.step == 3

    async def p1_fight_callback(current, action):
        nonlocal update_id
        callback = P1CombatCallback(
            activity=current.activity_id.hex,
            version=current.combat.version,
            action=action,
        ).pack()
        await dispatcher.feed_raw_update(
            telegram,
            _callback_update(callback, actor=actor, update_id=update_id),
        )
        update_id += 1
        return await p1.resume(actor)

    for attempt in range(1, 5):
        fight = quest
        await driver.combat_to_result(
            fight,
            p1_fight_callback,
            lambda: P1Service(sessions, "ocaso").resume(actor),
            label=f"A1 · P1 · tentativa {attempt}",
            max_actions=250,
        )
        quest = await p1.resume(actor)
        assert quest is not None
        if quest.progress.get("arrival"):
            break
        assert quest.progress.get("recovery"), quest
        quest = await p1.retry(actor, quest.state_version)
        assert quest is not None and quest.combat is not None
    assert quest.progress.get("arrival"), quest

    for action in ("refuge", "nc:o1", "oren", "activate"):
        await dispatcher.feed_raw_update(
            telegram,
            _callback_update(
                f"p1:{quest.state_version}:{action}",
                actor=actor,
                update_id=update_id,
            ),
        )
        update_id += 1
        quest = await p1.resume(actor)
    assert quest is not None and quest.status == "completed"
    completed = quest

    async with sessions() as session:
        stored = await session.get(Character, character_id)
        assert stored is not None and stored.level >= 1
        assert stored.xp > xp_before_p1
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character_id,
                Quest.quest_id == "P1",
                Quest.status == "completed",
            )
        ) is not None
        reward_count = await session.scalar(
            select(func.count(RewardEvent.id)).where(RewardEvent.character_id == character_id)
        )
        crowns = stored.crowns
        xp = stored.xp

    # A fresh service graph and fresh DB connection recover the same completed state.
    await database[0].dispose()
    resumed = await P1Service(sessions, "ocaso").resume(actor)
    world_after = await WorldService(sessions, "ocaso").resume(actor)
    assert resumed == completed
    assert world_after is not None and world_after.location == "Refúgio do Ocaso"

    # Replaying a stale transition cannot grant P1 XP, Coroas or reward rows twice.
    await dispatcher.feed_raw_update(
        telegram,
        _callback_update(
            f"p1:{stale_version}:follow",
            actor=actor,
            update_id=update_id,
        ),
    )
    async with sessions() as session:
        stored = await session.get(Character, character_id)
        assert stored is not None and (stored.crowns, stored.xp) == (crowns, xp)
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(RewardEvent.character_id == character_id)
        ) == reward_count


@pytest.mark.skipif(
    os.getenv("ASTERION_RUN_ALPHA_P1_P12_ORGANIC_JOURNEY") != "1",
    reason="jornada orgânica longa; habilite ASTERION_RUN_ALPHA_P1_P12_ORGANIC_JOURNEY=1",
)
@pytest.mark.asyncio
async def test_alpha_p1_p12_organic_journey_long(database, monkeypatch):
    """Reuse the proven public campaign driver with weapon-aware legal prep."""
    import tests.test_vde_full_playthrough as vde_journey
    equip_best = vde_journey._equip_best_available_combat_gear
    resume = vde_journey.VDEMissionService.resume

    async def equip_best_with_melee_fallback(sessions, actor):
        changed = await equip_best(sessions, actor)
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor,
                    Character.server_id == "ocaso",
                )
            )
            assert character is not None
            tags = await equipped_weapon_compatibility_tags(session, character.id)
            if "weapon.compat.melee" in tags:
                return changed
            candidates = []
            for item in await session.scalars(
                select(EquipmentItem).where(EquipmentItem.character_id == character.id)
            ):
                if item.slot != "Principal" or item.item_level > character.level:
                    continue
                definition = await resolve_equipment_weapon(session, item)
                if (
                    definition is not None
                    and "weapon.compat.melee" in definition.compatibility_tags
                ):
                    candidates.append((item.item_level, str(item.id), item.id, item.item_name))
            assert candidates, "A jornada deve possuir arma corpo a corpo obtida legitimamente."
            _level, _item_key, item_id, item_name = max(candidates)
            version = character.combat_configuration_version

        result = await EquipmentService(sessions, "ocaso").equip_item(
            actor,
            item_id,
            expected_configuration_version=version,
        )
        assert result is not None and result.changed
        return (*changed, ("Principal", item_name, "compatível com as Artes ativas"))

    async def resume_p12_with_public_talents(self, actor, quest_id):
        result = await resume(self, actor, quest_id)
        if (
            quest_id != vde_journey.P12_ID
            or result is None
            or result.status != "active"
        ):
            return result
        talents = TalentService(self.sessions, self.server_id)
        current = await talents.view(actor)
        assert current is not None and current.level >= 20
        for talent_id in (
            "talent.sentinela.ponta_revidada",
            "talent.sentinela.guarda_preparada",
        ):
            if current.available_points == 0 or talent_id in {
                choice.talent_id for choice in current.choices
            }:
                continue
            mutation = await talents.acquire(
                actor,
                talent_id,
                current.combat_configuration_version,
            )
            assert mutation is not None and mutation.changed
            current = mutation.view
        return result

    monkeypatch.setattr(
        vde_journey,
        "_equip_best_available_combat_gear",
        equip_best_with_melee_fallback,
    )
    monkeypatch.setattr(
        vde_journey.VDEMissionService,
        "resume",
        resume_p12_with_public_talents,
    )
    await vde_journey.test_vde_full_playthrough_from_fresh_tdo_exit(database, monkeypatch)
