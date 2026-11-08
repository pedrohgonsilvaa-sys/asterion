from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application.active_arts import ActiveArtService
from asterion.application.dungeons import DungeonService, DungeonView
from asterion.bot import dungeon_handlers
from asterion.bot.combat_ui import DungeonCombatCallback, class_trial_action_ids
from asterion.bot.dungeon_handlers import dungeon_router
from asterion.bot.dungeon_ui import render_dungeon_targets, render_dungeons
from asterion.domain.arts import DEVASTADOR_ART_IDS
from asterion.domain.combat import action_target_ids
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    VDE_VINE_SPIDER,
    CreatureCombatantSpec,
    create_creature_party_combat,
)
from asterion.domain.vde_fosso import FOSSO_DISCOVERY_UNLOCK, FOSSO_FAMILY_ID
from asterion.infrastructure.db.models import (
    Character,
    CombatRecord,
    DungeonRun,
    DungeonRunEncounter,
    GameActivity,
    Unlock,
    WorldState,
)
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts
from tests.test_creation_ui import callback_update
from tests.test_tdo_crypt import _seed
from tests.test_vde_s7_p8_integration import _seed_vde_ready


def _telegram():
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    return bot


def _button(screen, label):
    return next(
        button for row in screen.keyboard.inline_keyboard for button in row if button.text == label
    )


def _button_containing(screen, fragment):
    return next(
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if fragment in button.text
    )


@pytest.mark.asyncio
async def test_clicking_attack_in_crypt_routes_through_the_live_dungeon_service(database):
    actor = 774405
    character_id, sessions = await _seed(database, actor=actor)
    service = DungeonService(sessions, "ocaso")
    lobby = await service.start_solo(actor, "stable")
    fight = await service.begin_encounter(actor, lobby.run_id, lobby.state_version)
    # Dungeon encounters use party-style turn rendering, but are not campaign
    # shared encounters. Encounter five covers the Enfermaria screen that
    # exposed the missing campaign_shared field on DungeonView.
    fight = replace(fight, ordinal=5, dungeon_name="Enfermaria Afundada")
    screen = render_dungeons(fight)
    attack = _button(screen, "Atacar")
    assert "Masmorra ·" in screen.text
    assert attack.callback_data.startswith("df:")
    assert len(attack.callback_data.encode("utf-8")) <= 64
    callback = DungeonCombatCallback.unpack(attack.callback_data)
    assert callback.run == fight.run_id.hex[:16]
    assert callback.activity_id == fight.activity_id

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    # A different Telegram actor cannot use the visible character's callback.
    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=774405, actor=actor + 1),
    )
    unauthorized = await service.resume(actor)
    assert unauthorized is not None
    assert unauthorized.combat.version == fight.combat.version

    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=774406, actor=actor),
    )

    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.combat.version == fight.combat.version + 1
    async with sessions() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == fight.activity_id)
        )
        record = await session.get(CombatRecord, fight.encounter_id)
        assert activity.state_version == resumed.combat.version
        assert record is not None
        assert record.snapshot["rng_cursor"] == resumed.combat.rng_cursor

    # The already-processed callback is stale and cannot apply the action twice.
    await dispatcher.feed_raw_update(
        bot,
        callback_update(attack.callback_data, update_id=774409, actor=actor),
    )
    replayed = await service.resume(actor)
    assert replayed is not None
    assert replayed.combat.version == resumed.combat.version

    current_attack = _button(render_dungeons(resumed), "Atacar")
    current = DungeonCombatCallback.unpack(current_attack.callback_data)
    forged_indices = DungeonCombatCallback(
        run=current.run,
        activity=current.activity,
        version=current.version,
        action="-1",
        target="d0",
    ).pack()
    forged_target = DungeonCombatCallback(
        run=current.run,
        activity=current.activity,
        version=current.version,
        action=current.action,
        target="z",
    ).pack()
    await dispatcher.feed_raw_update(
        bot, callback_update(forged_indices, update_id=774407, actor=actor)
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(forged_target, update_id=774408, actor=actor)
    )
    after_forgery = await service.resume(actor)
    assert after_forgery is not None
    assert after_forgery.combat.version == resumed.combat.version


@pytest.mark.asyncio
async def test_explicit_unknown_dungeon_family_resumes_without_falling_back_to_crypt():
    actor = 774410
    service = AsyncMock()
    service.resume.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot,
        callback_update("dungeon:start:x:s", update_id=774411, actor=actor),
    )

    service.resume.assert_awaited_once_with(actor)
    service.start_solo.assert_not_awaited()
    service.detail.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_dungeon_start_callback_still_targets_the_crypt():
    actor = 774412
    service = AsyncMock()
    service.start_solo.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot,
        callback_update("dungeon:start:s", update_id=774413, actor=actor),
    )

    service.start_solo.assert_awaited_once_with(
        actor, "stable", "dungeon.tdo.cripta_ocaso"
    )


@pytest.mark.parametrize(
    ("family_key", "family_id"),
    (
        ("i", "dungeon.varzeas.enfermaria_afundada"),
        ("t", "dungeon.varzeas.cisterna_transferencia"),
    ),
)
@pytest.mark.asyncio
async def test_varzeas_dungeon_start_callback_resolves_family(family_key, family_id):
    actor = 774414
    service = AsyncMock()
    service.start_solo.return_value = None
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            f"dungeon:start:{family_key}:s", update_id=774415, actor=actor
        ),
    )

    service.start_solo.assert_awaited_once_with(actor, "stable", family_id)


async def _fosso_encounter_two_fixture(database, actor):
    character_id, sessions = await _seed_vde_ready(
        database, actor, level=16, round_ready=False
    )
    ariete = DEVASTADOR_ART_IDS["ariete"]
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.selected_path = "devastador"
        world.location = "Mata Suspensa"
        session.add(Unlock(character_id=character_id, unlock_id=FOSSO_DISCOVERY_UNLOCK))
        await add_compatible_weapon_for_arts(session, character_id, (ariete,))

    equipped = await ActiveArtService(sessions, "ocaso").equip_art(
        actor, 1, ariete, expected_configuration_version=0
    )
    assert equipped is not None and equipped.changed
    service = DungeonService(sessions, "ocaso")
    ready = await service.start_solo(actor, "stable", family_id=FOSSO_FAMILY_ID)
    assert ready is not None and ready.kind == "ready" and ready.run_id is not None

    # Position a test-only run fixture at the same public encounter boundary
    # as the supplied checkpoint. The next encounter is still created by the
    # public DungeonService and its combat is persisted normally.
    async with sessions.begin() as session:
        run = await session.get(DungeonRun, ready.run_id)
        first = await session.get(DungeonRunEncounter, (ready.run_id, 1))
        assert run is not None and first is not None
        run.seed = f"e87-target-selection-{actor}"
        run.current_encounter_ordinal = 2
        first.status = "completed"
        first.reward_settled = True

    fight = await service.begin_encounter(actor, ready.run_id, ready.state_version)
    assert fight is not None and fight.kind == "combat" and fight.combat is not None
    return character_id, sessions, service, fight


@pytest.mark.parametrize(
    ("actor", "target_name"),
    ((889701, "Aranha de Cipó"), (889702, "Peregrino Enredado")),
)
@pytest.mark.asyncio
async def test_fosso_ariete_target_button_dispatches_and_persists_selected_enemy(
    database, monkeypatch, actor, target_name
):
    _character_id, sessions, service, fight = await _fosso_encounter_two_fixture(
        database, actor
    )
    buttons_presented = []

    async def capture_present(_message, screen, _images, *, edit):
        assert edit is True
        buttons_presented.append(screen)

    monkeypatch.setattr(dungeon_handlers, "present", capture_present)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(dungeon_router(service, {}))
    bot = _telegram()

    public_screen = render_dungeons(fight)
    ariete_button = _button_containing(public_screen, "Aríete")
    ariete_callback = DungeonCombatCallback.unpack(ariete_button.callback_data)
    assert ariete_callback.target == "s"
    enemy_hp_before = {
        fighter.id: fighter.hp
        for fighter in fight.combat.fighters.values()
        if fighter.side == "enemy"
    }

    await dispatcher.feed_raw_update(
        bot, callback_update(ariete_button.callback_data, update_id=889710, actor=actor)
    )
    assert len(buttons_presented) == 1
    target_screen = buttons_presented[-1]
    target_button = _button_containing(target_screen, target_name)
    target_callback = DungeonCombatCallback.unpack(target_button.callback_data)
    assert target_callback.combat_version == fight.combat.version
    canonical_targets = action_target_ids(
        fight.combat,
        DEVASTADOR_ART_IDS["ariete"],
        actor_key=fight.combat_actor_key or "player",
    )
    selected_id = canonical_targets[target_callback.target_index]
    assert next(
        fighter.name for fighter in fight.combat.fighters.values() if fighter.id == selected_id
    ) == target_name

    # A different Telegram actor cannot spend the displayed target callback.
    await dispatcher.feed_raw_update(
        bot,
        callback_update(target_button.callback_data, update_id=889711, actor=actor + 100),
    )
    unchanged = await service.resume(actor)
    assert unchanged is not None and unchanged.combat.version == fight.combat.version

    await dispatcher.feed_raw_update(
        bot,
        callback_update(target_button.callback_data, update_id=889712, actor=actor),
    )
    persisted = await service.resume(actor)
    assert persisted is not None and persisted.kind == "combat"
    assert persisted.combat.version == fight.combat.version + 1
    assert persisted.combat.rng_cursor >= fight.combat.rng_cursor
    enemy_hp_after = {
        fighter.id: fighter.hp
        for fighter in persisted.combat.fighters.values()
        if fighter.side == "enemy"
    }
    assert enemy_hp_after[selected_id] < enemy_hp_before[selected_id]
    assert {
        fighter_id
        for fighter_id, hp in enemy_hp_after.items()
        if hp != enemy_hp_before[fighter_id]
    } == {selected_id}

    async with sessions() as session:
        activity = await session.get(GameActivity, fight.activity_id)
        record = await session.get(CombatRecord, fight.encounter_id)
        assert activity is not None and activity.state_version == persisted.combat.version
        assert record is not None
        assert record.snapshot["rng_cursor"] == persisted.combat.rng_cursor
        assert record.snapshot["fighters"][
            next(
                key
                for key, fighter in persisted.combat.fighters.items()
                if fighter.id == selected_id
            )
        ]["hp"] == str(enemy_hp_after[selected_id])

    # The same versioned callback is stale and cannot damage either target twice.
    await dispatcher.feed_raw_update(
        bot,
        callback_update(target_button.callback_data, update_id=889713, actor=actor),
    )
    repeated = await service.resume(actor)
    assert repeated is not None and repeated.combat.version == persisted.combat.version
    assert {
        fighter.id: fighter.hp
        for fighter in repeated.combat.fighters.values()
        if fighter.side == "enemy"
    } == enemy_hp_after

def test_dungeon_target_picker_keeps_same_species_instances_distinct():
    combat = create_creature_party_combat(
        uuid4(),
        "Testador",
        "sentinela",
        "remanescente",
        Decimal("1000"),
        (
            CreatureCombatantSpec(VDE_VINE_SPIDER, 15, "spider_one"),
            CreatureCombatantSpec(VDE_VINE_SPIDER, 15, "spider_two"),
        ),
        player_level=16,
        equipment_configuration=EquipmentConfigurationSnapshot(0),
        active_art_ids=(),
        flavor="Emaranhado Inferior",
    )
    run_id = uuid4()
    activity_id = uuid4()
    view = DungeonView(
        kind="combat",
        character_id=uuid4(),
        character_name="Testador",
        level=16,
        location="Fosso das Raízes",
        hp=combat.fighters["player"].hp,
        max_hp=combat.fighters["player"].stats.hp,
        vigor=50,
        max_vigor=100,
        run_id=run_id,
        activity_id=activity_id,
        combat=combat,
        context="dungeon",
        combat_actor_key="player",
    )
    actions = class_trial_action_ids(combat)
    screen = render_dungeon_targets(view, actions.index("attack"))
    target_buttons = [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data != "dungeon:noop"
        and "Aranha de Cipó" in button.text
    ]
    assert len(target_buttons) == 2
    callbacks = [DungeonCombatCallback.unpack(button.callback_data) for button in target_buttons]
    assert [callback.target_index for callback in callbacks] == [0, 1]
    assert len({callback.pack() for callback in callbacks}) == 2

    combat.fighters["spider_one"].hp = Decimal(0)
    live_targets = action_target_ids(combat, "attack")
    assert live_targets == (combat.fighters["spider_two"].id,)
    dead_target_screen = render_dungeon_targets(view, actions.index("attack"))
    live_buttons = [
        button
        for row in dead_target_screen.keyboard.inline_keyboard
        for button in row
        if "Aranha de Cipó" in button.text
    ]
    assert len(live_buttons) == 1
    assert DungeonCombatCallback.unpack(live_buttons[0].callback_data).target_index == 0
