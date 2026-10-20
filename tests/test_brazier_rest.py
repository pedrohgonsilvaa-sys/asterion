import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from sqlalchemy import select

from asterion.application import road as road_module
from asterion.application.road import (
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_REGION_LABEL,
    BRAZIER_DETAILS,
    BRAZIER_FOR_LOCATION,
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_REGION_UNLOCK,
    CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK,
    NARETH_REGION,
    NARETH_REGION_UNLOCK,
    REFUGE,
    REGION,
    ROAD,
    RUINS_LOCATION,
    VARZEAS_REGION,
    VDE_BAIXIOS,
    VDE_BAIXIOS_CLAUSTRO_ROUTE,
    VDE_CLAUSTRO,
    VDE_GARGANTA,
    VDE_GARGANTA_VIGILIA_ROUTE,
    VDE_MATA,
    VDE_MATA_BAIXIOS_ROUTE,
    VDE_REGION,
    VDE_VIGILIA,
    VDE_VIGILIA_MATA_ROUTE,
    RoadService,
    RoadView,
)
from asterion.application.world import WorldService
from asterion.bot.road_ui import render_current_local
from asterion.bot.world_handlers import world_router
from asterion.domain.road import LOCATION_LEVEL_BANDS
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    ConsumableStack,
    DungeonRun,
    DungeonRunMember,
    GameActivity,
    LocationDiscovery,
    Quest,
    Unlock,
    WorldState,
)
from tests.test_creation_ui import callback_update
from tests.test_prologue_persistence import character

REGION_LEVEL = {
    REGION: 1,
    VDE_REGION: 11,
    NARETH_REGION: 21,
    VARZEAS_REGION: 31,
    ALTOS_REGION_LABEL: 41,
    CONFINS_REGION_LABEL: 51,
}
REGION_GATE_QUEST = {
    REGION: "P1",
    VDE_REGION: "P7",
    NARETH_REGION: "P12",
    VARZEAS_REGION: "P18",
    ALTOS_REGION_LABEL: "P24",
    CONFINS_REGION_LABEL: "P30",
}
ALL_ROAD_ACCESS_UNLOCKS = tuple(
    sorted(
        {
            value
            for name, value in vars(road_module).items()
            if isinstance(value, str)
            and value.startswith(("route.", "region.", "unlock.location."))
        }
    )
)


async def _seed_brazier_character(database, actor, location, brazier_id):
    await character(database, actor)
    region = RoadService._travel_region(location)
    region_name = {
        "tdo": REGION,
        "vde": VDE_REGION,
        "nareth": NARETH_REGION,
        "varzeas": VARZEAS_REGION,
        "altos": ALTOS_REGION_LABEL,
        "confins": CONFINS_REGION_LABEL,
    }[region]
    level = max(
        REGION_LEVEL[region_name],
        LOCATION_LEVEL_BANDS.get(location, (REGION_LEVEL[region_name], 60))[0],
    )
    async with database[1].begin() as session:
        c = await session.scalar(select(Character).where(Character.telegram_id == actor))
        c.stage = "menu:ready"
        c.level = level
        c.hp = Decimal("17.5")
        c.max_hp = Decimal("100")
        c.vigor = 43
        c.vigor_regen_at = datetime.now(UTC) + timedelta(days=1)
        c.xp = 2345
        c.crowns = 678
        session.add(WorldState(character_id=c.id, region=region_name, location=location))
        session.add(Brazier(character_id=c.id, brazier_id=brazier_id))
        session.add(
            ConsumableStack(
                character_id=c.id,
                consumable_id="consumable.heal.vde.ii",
                quantity=3,
            )
        )
        quest_ids = {
            "P1", "P2", "P3", "P4", "P7", "P8", "P9", "P10", "P11", "P12",
            "P13", "P14", "P15", "P16", "P17", "P18", "P19", "P20", "P21",
            "P22", "P24", "P25", "P26", "P27", "P28", "P29", "P30", "P31",
            "P32", "P33", "P34",
        }
        for quest_id in quest_ids:
            session.add(
                Quest(
                    character_id=c.id,
                    quest_id=quest_id,
                    title=quest_id,
                    status="completed",
                    step=1,
                )
            )
        required_unlocks = set(
            {
                "Vigília do Vale": (VDE_GARGANTA_VIGILIA_ROUTE,),
                "Mata Suspensa": (VDE_VIGILIA_MATA_ROUTE,),
                "Baixios Enredados": (VDE_MATA_BAIXIOS_ROUTE,),
                "Claustro das Raízes": (VDE_BAIXIOS_CLAUSTRO_ROUTE,),
                "Campinas do Meridiano": (NARETH_REGION_UNLOCK,),
                "Escarpa da Cinza": (ALTOS_ESCARPA_ACCESS_UNLOCK,),
                "Último Refúgio": (
                    CONFINS_REGION_UNLOCK,
                    CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK,
                ),
            }.get(location, ())
        )
        required_unlocks.update(ALL_ROAD_ACCESS_UNLOCKS)
        if region == "confins":
            required_unlocks.add(CONFINS_REGION_UNLOCK)
        for unlock_id in required_unlocks:
            session.add(Unlock(character_id=c.id, unlock_id=unlock_id))
        if location == ROAD:
            c.stage = "menu:ready"
        if location == "Ruínas do Vigia":
            session.add(LocationDiscovery(character_id=c.id, location_id=RUINS_LOCATION))
    return c.id


async def _move_seeded_character_to_brazier(database, actor, location, brazier_id):
    region = RoadService._travel_region(location)
    region_name = {
        "tdo": REGION,
        "vde": VDE_REGION,
        "nareth": NARETH_REGION,
        "varzeas": VARZEAS_REGION,
        "altos": ALTOS_REGION_LABEL,
        "confins": CONFINS_REGION_LABEL,
    }[region]
    level = max(
        REGION_LEVEL[region_name],
        LOCATION_LEVEL_BANDS.get(location, (REGION_LEVEL[region_name], 60))[0],
    )
    async with database[1].begin() as session:
        c = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == c.id)
        )
        c.level = level
        c.hp = Decimal("17.5")
        c.max_hp = Decimal("100")
        world.region = region_name
        world.location = location
        session.add(Brazier(character_id=c.id, brazier_id=brazier_id))


@pytest.mark.parametrize(
    "location,region_name",
    [
        (REFUGE, REGION),
        ("Vigília do Vale", VDE_REGION),
        ("Campinas do Meridiano", NARETH_REGION),
        ("Diques Rubros", VARZEAS_REGION),
        ("Escarpa da Cinza", ALTOS_REGION_LABEL),
        ("Último Refúgio", CONFINS_REGION_LABEL),
    ],
)
async def test_permanent_brazier_rest_recovers_individual_without_economic_changes(
    database, location, region_name
):
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    view = await RoadService(database[1], "ocaso").rest(
        1, expected_brazier_id=brazier_id
    )
    assert view is not None
    assert view.location == location
    assert view.hp == Decimal("100")
    async with database[1]() as session:
        c = await session.scalar(select(Character).where(Character.id == character_id))
        world = await session.scalar(select(WorldState).where(WorldState.character_id == c.id))
        consumables = await session.scalars(
            select(ConsumableStack).where(ConsumableStack.character_id == c.id)
        )
        assert c.hp == c.max_hp == Decimal("100")
        assert c.vigor == 43
        assert c.xp == 2345 and c.crowns == 678
        assert [(row.consumable_id, row.quantity) for row in consumables] == [
            ("consumable.heal.vde.ii", 3)
        ]
        assert world.region == region_name and world.location == location


async def test_all_five_vales_permanent_braziers_allow_individual_rest(database):
    locations = (VDE_GARGANTA, VDE_VIGILIA, VDE_MATA, VDE_BAIXIOS, VDE_CLAUSTRO)
    service = RoadService(database[1], "ocaso")
    for actor, location in enumerate(locations, start=1):
        brazier_id = BRAZIER_FOR_LOCATION[location]
        await _seed_brazier_character(database, actor, location, brazier_id)
        view = await service.rest(actor, expected_brazier_id=brazier_id)
        assert view is not None and view.location == location
        assert view.hp == Decimal("100")


async def test_every_catalogued_permanent_brazier_allows_rest(database):
    service = RoadService(database[1], "ocaso")
    assert len(BRAZIER_DETAILS) == 30
    for index, (brazier_id, (location, _label)) in enumerate(
        sorted(BRAZIER_DETAILS.items())
    ):
        actor = index % 26 + 1
        if index < 26:
            await _seed_brazier_character(database, actor, location, brazier_id)
        else:
            await _move_seeded_character_to_brazier(
                database, actor, location, brazier_id
            )
        view = await service.rest(actor, expected_brazier_id=brazier_id)
        assert view is not None, (brazier_id, location)
        assert view.location == location
        assert view.hp == Decimal("100")


async def test_rest_is_idempotent_concurrent_and_never_heals_group_members(database):
    location = REFUGE
    brazier_id = BRAZIER_FOR_LOCATION[location]
    first_id = await _seed_brazier_character(database, 1, location, brazier_id)
    second_id = await _seed_brazier_character(database, 2, location, brazier_id)
    first, second = await asyncio.gather(
        RoadService(database[1], "ocaso").rest(1, expected_brazier_id=brazier_id),
        RoadService(database[1], "ocaso").rest(1, expected_brazier_id=brazier_id),
    )
    assert first is not None and second is not None
    async with database[1]() as session:
        first_character = await session.get(Character, first_id)
        second_character = await session.get(Character, second_id)
        assert first_character.hp == first_character.max_hp
        assert second_character.hp == Decimal("17.5")


async def test_rest_rejects_unknown_brazier_wrong_server_level_and_stale_callback(database):
    location = "Último Refúgio"
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    service = RoadService(database[1], "ocaso")
    assert await service.rest(1, expected_brazier_id="bonfire.dungeon.fake") is None
    assert await RoadService(database[1], "other-server").rest(
        1, expected_brazier_id=brazier_id
    ) is None
    async with database[1].begin() as session:
        c = await session.get(Character, character_id)
        c.level = 50
        c.hp = Decimal("20")
    assert await service.rest(1, expected_brazier_id=brazier_id) is None
    async with database[1]() as session:
        c = await session.get(Character, character_id)
        assert c.hp == Decimal("20")


async def test_rest_rejects_brazier_record_in_a_region_local_location_not_yet_open(database):
    location = CONFINS_ESTRADAS_AUSENTES_LABEL
    brazier_id = BRAZIER_FOR_LOCATION[location]
    await _seed_brazier_character(database, 1, location, brazier_id)
    async with database[1].begin() as session:
        c = await session.scalar(select(Character).where(Character.telegram_id == 1))
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == c.id, Quest.quest_id == "P32")
        )
        await session.delete(quest)
    assert await RoadService(database[1], "ocaso").rest(
        1, expected_brazier_id=brazier_id
    ) is None


async def test_rest_requires_discovered_brazier_and_blocks_foreground_or_dungeon(database):
    location = REFUGE
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    service = RoadService(database[1], "ocaso")
    async with database[1].begin() as session:
        brazier = await session.scalar(
            select(Brazier).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == brazier_id,
            )
        )
        await session.delete(brazier)
    assert await service.rest(1, expected_brazier_id=brazier_id) is None
    async with database[1].begin() as session:
        c = await session.get(Character, character_id)
        session.add(Brazier(character_id=c.id, brazier_id=brazier_id))
        session.add(
            GameActivity(
                character_id=c.id,
                content_id="road_manual_hunt",
                status="active",
                ruleset_version="test",
            )
        )
    assert await service.rest(1, expected_brazier_id=brazier_id) is None


async def test_active_dungeon_run_blocks_external_world_rest_without_activity_row(database):
    location = REFUGE
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    async with database[1].begin() as session:
        run = DungeonRun(
            dungeon_family_id="dungeon.test.active",
            difficulty="stable",
            status="active",
            ruleset_version="test",
            content_version="test",
            reference_level=60,
            initial_group_size=1,
            seed="rest-block-test",
            has_brazier=False,
            progress={},
        )
        session.add(run)
        await session.flush()
        session.add(
            DungeonRunMember(
                run_id=run.id,
                character_id=character_id,
                position=1,
                status="active",
                vigor_reserved=25,
                combat_configuration={},
                hp=Decimal("17.5"),
                max_hp=Decimal("100"),
                run_state={},
                contribution={},
            )
        )
    assert (
        await RoadService(database[1], "ocaso").rest(
            1, expected_brazier_id=brazier_id
        )
        is None
    )


def test_current_local_offers_rest_only_for_its_discovered_permanent_brazier():
    view = RoadView(
        kind="local",
        character_id="00000000-0000-0000-0000-000000000001",
        location=REFUGE,
        name="Heroa",
        hp=Decimal("17.5"),
        max_hp=Decimal("100"),
        brazier_id=BRAZIER_FOR_LOCATION[REFUGE],
        brazier_label=BRAZIER_DETAILS[BRAZIER_FOR_LOCATION[REFUGE]][1],
    )
    screen = render_current_local(view)
    rest_buttons = [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.text == "Descansar"
    ]
    assert len(rest_buttons) == 1
    assert rest_buttons[0].callback_data == f"world:rest:{view.brazier_id}"
    assert "Descansar · Restaura HP" in screen.text


async def test_telegram_rest_callback_uses_current_brazier_and_rebuilds_local_ui(database):
    location = REFUGE
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    road = RoadService(database[1], "ocaso")
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(WorldService(database[1], "ocaso"), {}, road=road)
    )
    await dispatcher.feed_raw_update(
        bot,
        callback_update(f"world:rest:{brazier_id}", actor=1),
    )
    async with database[1]() as session:
        c = await session.get(Character, character_id)
        assert c.hp == c.max_hp == Decimal("100")
    assert bot.session.make_request.await_count >= 2


async def test_legacy_rest_callback_is_rejected_after_prologue_menu(database):
    location = ROAD
    brazier_id = BRAZIER_FOR_LOCATION[location]
    character_id = await _seed_brazier_character(database, 1, location, brazier_id)
    bot = Bot("123456:local-test-token")
    bot.session.make_request = AsyncMock(return_value=True)
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        world_router(
            WorldService(database[1], "ocaso"),
            {},
            road=RoadService(database[1], "ocaso"),
        )
    )
    await dispatcher.feed_raw_update(bot, callback_update("world:rest", actor=1))
    async with database[1]() as session:
        c = await session.get(Character, character_id)
        assert c.hp == Decimal("17.5")
    assert bot.session.make_request.await_count >= 2
