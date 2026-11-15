"""TdO v1.0.18, bloco D: Missões sem nível e sem descoberta, Masmorras e PowerlevelFactor.

Critérios 33.16 itens 8, 9, 10 e 21; QA-002 (botões de Missão no hub).
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.dungeons import DungeonService
from asterion.application.p2 import P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.p5 import P5Service
from asterion.application.p6 import P6_REWARD_SOURCE, P6Service
from asterion.application.road import (
    BOSQUE,
    BRAZIER_FOR_LOCATION,
    CAMARA,
    CHARNECA,
    REFUGE,
    REGION,
    RUINS,
    RoadService,
)
from asterion.application.s1 import S1Service
from asterion.application.s4 import S4Service
from asterion.application.s5 import S5Service
from asterion.application.s6 import S6Service
from asterion.bot.p2_ui import render_p2
from asterion.bot.p3_ui import render_p3
from asterion.bot.p4_ui import render_p4
from asterion.bot.p6_ui import render_p6
from asterion.bot.tdo_hub_ui import mission_hub_button
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.road import fixed_quest_xp, powerlevel_factor
from asterion.domain.tdo_explore import (
    BOSQUE_LOCATION_ID,
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    RUINS_LOCATION_ID,
)
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

CRYPT = "dungeon.tdo.cripta_ocaso"
GALLERIES = "dungeon.tdo.galerias_vigia"
SERVER = "ocaso"


async def _seed(
    database,
    actor,
    *,
    level=1,
    location=REFUGE,
    quests=(("P1", "completed"),),
    discovered=(),
    unlocks=(),
):
    _engine, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats("sentinela", max(level, 1), "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id=SERVER,
                name=f"Hero{chr(ord('a') + actor % 26)}",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        await session.flush()
        for quest_id, status in quests:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=quest_id,
                    title=quest_id,
                    status=status,
                    step=9 if status == "completed" else 1,
                    content_version="tdo-1.0.2",
                    progress={"door_known": True} if quest_id == "P5" else {},
                )
            )
        session.add(WorldState(character_id=character_id, region=REGION, location=location))
        for location_id in discovered:
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))
        for unlock_id in unlocks:
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))
    return character_id, sessions


async def _discoveries(sessions, character_id, location_id=None):
    async with sessions() as session:
        query = select(func.count(LocationDiscovery.id)).where(
            LocationDiscovery.character_id == character_id
        )
        if location_id is not None:
            query = query.where(LocationDiscovery.location_id == location_id)
        return await session.scalar(query)


async def _set_quest(sessions, character_id, quest_id, **values):
    async with sessions.begin() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == quest_id)
        )
        progress = values.pop("progress", None)
        for key, value in values.items():
            setattr(quest, key, value)
        if progress is not None:
            quest.progress = {**(quest.progress or {}), **progress}


# ---------------------------------------------------------------- item 1: sem nível


@pytest.mark.asyncio
async def test_each_mission_is_available_at_nv1_when_its_chain_is_done(database):
    _a, sessions_a = await _seed(database, 771011, level=1)
    assert (await P2Service(sessions_a, SERVER).alda(771011)).available
    assert (await S1Service(sessions_a, SERVER).offer(771011)).kind == "offer"

    _b, sessions_b = await _seed(
        database, 771012, level=1, quests=(("P1", "completed"), ("P2", "completed"))
    )
    assert (await P3Service(sessions_b, SERVER).offer(771012)).available

    _c, sessions_c = await _seed(
        database,
        771013,
        level=1,
        quests=(("P1", "completed"), ("P2", "completed"), ("P3", "completed")),
    )
    assert (await P4Service(sessions_c, SERVER).offer(771013)).available

    _d, sessions_d = await _seed(
        database,
        771014,
        level=1,
        quests=tuple((q, "completed") for q in ("P1", "P2", "P3", "P4")),
    )
    assert (await P5Service(sessions_d, SERVER).offer(771014)).available

    _e, sessions_e = await _seed(
        database,
        771015,
        level=1,
        quests=tuple((q, "completed") for q in ("P1", "P2", "P3", "P4", "P5", "S2")),
    )
    assert (await S6Service(sessions_e, SERVER).offer(771015)).available

    _f, sessions_f = await _seed(
        database,
        771016,
        level=1,
        quests=tuple((q, "completed") for q in ("P1", "P2", "P3", "P4")),
    )
    assert (await S4Service(sessions_f, SERVER).offer(771016)).available
    assert (await S5Service(sessions_f, SERVER).offer(771016)).available


@pytest.mark.asyncio
async def test_p6_starts_automatically_after_p5_without_level(database):
    done = tuple((q, "completed") for q in ("P1", "P2", "P3", "P4", "P5"))
    _id, sessions = await _seed(database, 771021, level=1, quests=done)
    view = await P6Service(sessions, SERVER).resume(771021)
    assert view is not None and view.status == "active" and view.step == 1


# ------------------------------------------------ itens 2 e 8: aguardando, sem descobrir


@pytest.mark.asyncio
async def test_p2_waits_for_charneca_then_arrives_without_writing_discovery(database):
    actor = 772001
    character_id, sessions = await _seed(database, actor, level=1)
    service = P2Service(sessions, SERVER)
    view = await service.accept(actor, (await service.alda(actor)).state_version)
    assert view.step == 1 and view.awaiting_exploration

    waiting = await service.travel_to_charneca(actor, view.state_version)
    assert waiting.step == 1 and waiting.location == REFUGE and waiting.awaiting_exploration
    assert await _discoveries(sessions, character_id) == 0

    async with sessions.begin() as session:
        session.add(LocationDiscovery(character_id=character_id, location_id=CHARNECA_LOCATION_ID))
    resumed = await service.resume(actor)
    assert not resumed.awaiting_exploration
    arrived = await service.travel_to_charneca(actor, resumed.state_version)
    assert arrived.step == 2 and arrived.location == CHARNECA
    assert await _discoveries(sessions, character_id, CHARNECA_LOCATION_ID) == 1


@pytest.mark.asyncio
async def test_p2_can_leave_to_refuge_and_resume_in_hub(database):
    actor = 772011
    character_id, sessions = await _seed(
        database, actor, discovered=(CHARNECA_LOCATION_ID,)
    )
    service = P2Service(sessions, SERVER)
    view = await service.accept(actor, (await service.alda(actor)).state_version)
    view = await service.travel_to_charneca(actor, view.state_version)
    assert view.step == 2 and view.location == CHARNECA
    callbacks = [b.callback_data for row in render_p2(view).keyboard.inline_keyboard for b in row]
    assert f"p2:{view.state_version}:leave" in callbacks

    left = await service.leave_to_refuge(actor, view.state_version)
    assert left.location == REFUGE and left.step == 2
    callbacks = [b.callback_data for row in render_p2(left).keyboard.inline_keyboard for b in row]
    assert f"p2:{left.state_version}:back" in callbacks
    assert not any(c.startswith("p2:") and ":ash:" in c for c in callbacks)

    back = await service.back_to_charneca(actor, left.state_version)
    assert back.location == CHARNECA and back.step == 2
    assert await _discoveries(sessions, character_id) == 1


@pytest.mark.asyncio
async def test_p3_waits_for_bosque_then_enters_from_refuge(database):
    actor = 772021
    character_id, sessions = await _seed(
        database, actor, quests=(("P1", "completed"), ("P2", "completed"))
    )
    service = P3Service(sessions, SERVER)
    view = await service.accept(actor, 0)
    assert view.step == 1 and view.awaiting_exploration
    callbacks = [b.callback_data for row in render_p3(view).keyboard.inline_keyboard for b in row]
    assert "tdo:explore" in callbacks

    waiting = await service.enter_bosque(actor, view.state_version)
    assert waiting.step == 1 and waiting.location == REFUGE
    assert await _discoveries(sessions, character_id) == 0

    async with sessions.begin() as session:
        session.add(LocationDiscovery(character_id=character_id, location_id=BOSQUE_LOCATION_ID))
    resumed = await service.resume(actor)
    entered = await service.enter_bosque(actor, resumed.state_version)
    assert entered.step == 2 and entered.location == BOSQUE
    assert await _discoveries(sessions, character_id, BOSQUE_LOCATION_ID) == 1

    keyboard = render_p3(entered).keyboard.inline_keyboard
    callbacks = [b.callback_data for row in keyboard for b in row]
    assert f"p3:{entered.state_version}:route:refuge" in callbacks
    left = await service.mission_route(actor, entered.state_version, REFUGE)
    assert left.location == REFUGE
    again = await service.enter_bosque(actor, left.state_version)
    assert again.location == BOSQUE and again.step == 2


@pytest.mark.asyncio
async def test_p4_waits_for_ruins_then_enters_from_refuge(database):
    actor = 772031
    character_id, sessions = await _seed(
        database,
        actor,
        quests=tuple((q, "completed") for q in ("P1", "P2", "P3")),
        discovered=(BOSQUE_LOCATION_ID,),
    )
    service = P4Service(sessions, SERVER)
    view = await service.accept(actor, 0)
    path = await service.action(actor, view.state_version, "path")
    assert path.step == 2 and path.kind == "enter_ruins" and path.awaiting_exploration

    waiting = await service.action(actor, path.state_version, "enter")
    assert waiting.step == 2 and waiting.location == REFUGE
    assert await _discoveries(sessions, character_id, RUINS_LOCATION_ID) == 0

    async with sessions.begin() as session:
        session.add(LocationDiscovery(character_id=character_id, location_id=RUINS_LOCATION_ID))
    resumed = await service.resume(actor)
    assert not resumed.awaiting_exploration
    entered = await service.action(actor, resumed.state_version, "enter")
    assert entered.step == 3 and entered.location == RUINS
    assert await _discoveries(sessions, character_id, RUINS_LOCATION_ID) == 1


@pytest.mark.asyncio
async def test_p6_waits_for_camara_then_arrives_from_refuge_without_writing_discovery(database):
    actor = 772041
    done = tuple((q, "completed") for q in ("P1", "P2", "P3", "P4", "P5"))
    character_id, sessions = await _seed(database, actor, quests=done)
    service = P6Service(sessions, SERVER)
    view = await service.resume(actor)
    await _set_quest(
        sessions, character_id, "P6", progress={"door_known": True}
    )
    view = await service.resume(actor)
    crossed = await service.action(actor, view.state_version, "cross_door")
    assert crossed.step == 2 and crossed.kind == "enter_chamber" and crossed.awaiting_exploration

    waiting = await service.action(actor, crossed.state_version, "enter_chamber")
    assert waiting.step == 2 and waiting.location == REFUGE
    assert await _discoveries(sessions, character_id, CAMARA_LOCATION_ID) == 0
    keyboard = render_p6(waiting).keyboard.inline_keyboard
    callbacks = [b.callback_data for row in keyboard for b in row]
    assert "tdo:explore" in callbacks

    async with sessions.begin() as session:
        session.add(LocationDiscovery(character_id=character_id, location_id=CAMARA_LOCATION_ID))
    resumed = await service.resume(actor)
    entered = await service.action(actor, resumed.state_version, "enter_chamber")
    assert entered.step == 3 and entered.location == CAMARA
    assert await _discoveries(sessions, character_id, CAMARA_LOCATION_ID) == 1

    left = await service.action(actor, entered.state_version, "return_refuge")
    assert left.location == REFUGE and left.step == 3
    again = await service.action(actor, left.state_version, "enter_chamber")
    assert again.location == CAMARA and again.step == 3


# ------------------------------------------------------------ item 6: botões no hub


def test_mission_hub_button_never_goes_local_to_local():
    button = mission_hub_button(REFUGE, BOSQUE)
    assert button is not None and button.callback_data == "road:route:bosque"
    assert mission_hub_button(REFUGE, RUINS).callback_data == "road:route:ruinas"
    assert mission_hub_button(REFUGE, CAMARA).callback_data == "road:route:camara"
    assert mission_hub_button(BOSQUE, RUINS).callback_data == "road:route:refuge"
    assert mission_hub_button(CHARNECA, BOSQUE).callback_data == "road:route:refuge"
    assert mission_hub_button(RUINS, RUINS) is None
    assert mission_hub_button(CAMARA, RUINS).callback_data == "road:route:refuge"


@pytest.mark.asyncio
async def test_mission_screens_have_no_local_to_local_buttons(database):
    actor = 773001
    done = tuple((q, "completed") for q in ("P1", "P2", "P3"))
    character_id, sessions = await _seed(
        database,
        actor,
        quests=done,
        discovered=(BOSQUE_LOCATION_ID, RUINS_LOCATION_ID),
    )
    service = P4Service(sessions, SERVER)
    await service.accept(actor, 0)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        world.location = RUINS
    # Etapa 4 (estruturas) nas Ruínas, sem combate em primeiro plano.
    await _set_quest(
        sessions, character_id, "P4", step=4, progress={"western_path_followed": True}
    )
    view = await service.resume(actor)
    assert view.kind == "structures" and view.location == RUINS
    callbacks = [b.callback_data for row in render_p4(view).keyboard.inline_keyboard for b in row]
    assert f"p4:{view.state_version}:route:refuge" in callbacks
    assert not [c for c in callbacks if c.startswith("road:route:")]

    left = await service.mission_route(actor, view.state_version, REFUGE)
    assert left.location == REFUGE
    callbacks = [b.callback_data for row in render_p4(left).keyboard.inline_keyboard for b in row]
    assert f"p4:{left.state_version}:enter" in callbacks
    assert not [c for c in callbacks if c.startswith("road:route:")]
    back = await service.action(actor, left.state_version, "enter")
    assert back.location == RUINS and back.step == 4


# --------------------------------------------------------------- itens 3 e 4: Masmorra


@pytest.mark.asyncio
async def test_dungeon_menu_shows_only_discovered_dungeons(database):
    _id, sessions = await _seed(database, 774001, level=1)
    service = DungeonService(sessions, SERVER)
    assert (await service.known(774001)).kind == "empty"

    _id2, sessions2 = await _seed(database, 774002, level=1, unlocks=(CRYPT,))
    view = await DungeonService(sessions2, SERVER).known(774002)
    assert view.kind == "known"
    assert [row[0] for row in view.known_dungeons] == [CRYPT]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family", "location", "low", "ok"),
    [(CRYPT, CHARNECA, 3, 4), (GALLERIES, RUINS, 7, 8)],
)
async def test_dungeon_solo_minimum_level_is_start_of_band(database, family, location, low, ok):
    actor = 774100 + low
    _id, sessions = await _seed(
        database, actor, level=low, location=location, unlocks=(family,)
    )
    refused = await DungeonService(sessions, SERVER).start_solo(actor, "stable", family)
    assert refused is not None and refused.reason == "level"

    actor2 = 774200 + ok
    _id2, sessions2 = await _seed(
        database, actor2, level=ok, location=location, unlocks=(family,)
    )
    entered = await DungeonService(sessions2, SERVER).start_solo(actor2, "stable", family)
    assert entered is not None and entered.reason != "level" and entered.run_id is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("family", "location", "low", "ok"),
    [(CRYPT, CHARNECA, 3, 4), (GALLERIES, RUINS, 7, 8)],
)
async def test_dungeon_group_refuses_member_below_minimum(database, family, location, low, ok):
    host, guest = 774300 + low, 774400 + low
    _h, sessions = await _seed(
        database, host, level=ok, location=location, unlocks=(family,)
    )
    async with sessions.begin() as session:
        guest_id = uuid4()
        session.add(Account(telegram_id=guest))
        session.add(
            Character(
                id=guest_id,
                telegram_id=guest,
                server_id=SERVER,
                name="Convidado",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=low,
                xp=0,
                hp=Decimal(702),
                max_hp=Decimal(702),
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
        session.add(WorldState(character_id=guest_id, region=REGION, location=location))
        session.add(Unlock(character_id=guest_id, unlock_id=family))
    service = DungeonService(sessions, SERVER)
    lobby = await service.prepare_group(host, family, "stable")
    invited = await service.invite_by_name(host, lobby.lobby_id, lobby.lobby_version, "Convidado")
    pending = await service.pending_invite(guest)
    if pending is None:
        assert invited.reason != "invited:Convidado"
        return
    response = await service.respond_invite(guest, pending.invite_id, accept=True)
    assert response.kind == "invite" and response.reason == "level"


# ------------------------------------------------------- item 5: PowerlevelFactor


@pytest.mark.parametrize(
    ("gap", "factor"),
    [
        (0, "1.00"),
        (10, "1.00"),
        (11, "0.70"),
        (15, "0.70"),
        (16, "0.45"),
        (20, "0.45"),
        (21, "0.20"),
        (30, "0.20"),
        (31, "0.05"),
        (-4, "1.00"),
    ],
)
def test_powerlevel_factor_table(gap, factor):
    assert powerlevel_factor(gap) == Decimal(factor)


def test_fixed_quest_xp_applies_factor_to_p5_p6_s6_values():
    assert fixed_quest_xp(7100, 0) == 7100
    assert fixed_quest_xp(14220, 12) == 9954
    assert fixed_quest_xp(7900, 18) == 3555
    assert fixed_quest_xp(14220, 25) == 2844
    assert fixed_quest_xp(7100, 40) == 355


def test_fixed_quest_xp_rounds_half_up():
    # Decisao do autor (2026-11-15): inteiro mais proximo, meio para cima.
    assert fixed_quest_xp(10, 18) == 5  # 4,5 -> 5 (par daria 4)
    assert fixed_quest_xp(30, 18) == 14  # 13,5 -> 14
    assert fixed_quest_xp(5, 12) == 4  # 3,5 -> 4


async def _xp_component(sessions, character_id):
    async with sessions() as session:
        return await session.scalar(
            select(RewardComponent.quantity)
            .join(RewardEvent, RewardEvent.id == RewardComponent.reward_event_id)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P6_REWARD_SOURCE,
                RewardComponent.kind == "xp",
            )
        )


@pytest.mark.asyncio
async def test_p6_completion_applies_powerlevel_factor_to_fixed_xp(database):
    actor = 775001
    done = tuple((q, "completed") for q in ("P1", "P2", "P3", "P4", "P5"))
    character_id, sessions = await _seed(database, actor, level=1, quests=done)
    service = P6Service(sessions, SERVER)
    await service.resume(actor)
    await _set_quest(sessions, character_id, "P6", step=9, progress={"coop_level_gap": 12})
    view = await service.resume(actor)
    result = await service.choose_reward(actor, view.state_version, "last_post")
    assert result.status == "completed"
    assert await _xp_component(sessions, character_id) == 9954


@pytest.mark.asyncio
async def test_p6_completion_solo_keeps_full_fixed_xp(database):
    actor = 775002
    done = tuple((q, "completed") for q in ("P1", "P2", "P3", "P4", "P5"))
    character_id, sessions = await _seed(database, actor, level=1, quests=done)
    service = P6Service(sessions, SERVER)
    await service.resume(actor)
    await _set_quest(sessions, character_id, "P6", step=9)
    view = await service.resume(actor)
    await service.choose_reward(actor, view.state_version, "last_post")
    assert await _xp_component(sessions, character_id) == 14220


# ------------------------------------------- Braseiro por Local descoberto (v1.0.18)


async def _hurt(sessions, character_id):
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.hp = Decimal("1")


async def _know_brazier(sessions, character_id, location):
    async with sessions.begin() as session:
        session.add(
            Brazier(character_id=character_id, brazier_id=BRAZIER_FOR_LOCATION[location])
        )


async def _hp(sessions, character_id):
    async with sessions() as session:
        return (await session.get(Character, character_id)).hp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("location", "location_id"),
    [
        (CHARNECA, CHARNECA_LOCATION_ID),
        (BOSQUE, BOSQUE_LOCATION_ID),
        (RUINS, RUINS_LOCATION_ID),
    ],
)
async def test_nv1_rests_at_brazier_of_discovered_local(database, location, location_id):
    actor = 776000 + len(location)
    character_id, sessions = await _seed(
        database, actor, level=1, location=location, discovered=(location_id,)
    )
    await _know_brazier(sessions, character_id, location)
    await _hurt(sessions, character_id)
    view = await RoadService(sessions, SERVER).rest(actor)
    assert view is not None
    assert await _hp(sessions, character_id) > Decimal("1")


@pytest.mark.asyncio
@pytest.mark.parametrize("location", [CHARNECA, BOSQUE, RUINS])
async def test_nv1_does_not_rest_at_brazier_of_undiscovered_local(database, location):
    actor = 776100 + len(location)
    done = tuple((q, "completed") for q in ("P1", "P2", "P3", "P4"))
    character_id, sessions = await _seed(
        database, actor, level=1, location=location, quests=done
    )
    await _know_brazier(sessions, character_id, location)
    await _hurt(sessions, character_id)
    assert await RoadService(sessions, SERVER).rest(actor) is None
    assert await _hp(sessions, character_id) == Decimal("1")
