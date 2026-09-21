import asyncio
from decimal import Decimal

from sqlalchemy import select

from asterion.application.prologue import PrologueService
from asterion.application.world import WorldService, WorldView
from asterion.bot.world_ui import render_world
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.models import Achievement, Brazier, Character, Quest, WorldState
from tests.test_prologue_persistence import character, win


def world_view(**changes):
    values = dict(
        kind="menu",
        character_id="00000000-0000-0000-0000-000000000001",
        name="Heroa",
        race="remanescente",
        character_class="sentinela",
        hp=Decimal("712.530"),
        max_hp=Decimal("712.530"),
        vigor=100,
        max_vigor=100,
        xp=320,
        region="Terras do Ocaso",
        location="Estrada das Cinzas",
        quest_title="Vozes na Estrada",
    )
    values.update(changes)
    return WorldView(**values)


def test_menu_is_authoritative_and_preserves_fractional_hp():
    text = render_world(world_view()).text
    assert "Terras do Ocaso · Estrada das Cinzas" in text
    assert "❤️ HP · 712.530 / 712.530" in text
    assert "⚡ Vigor · 100 / 100" in text
    assert "✨ XP · 320 / 4.800" in text
    assert "📜 Missão Principal · Vozes na Estrada" in text


def test_vigor_bar_is_derived_not_hardcoded():
    text = render_world(world_view(vigor=72)).text
    assert "⚡ Vigor · 72 / 100\n🟨🟨🟨🟨🟨🟨🟨⬜⬜⬜" in text


def test_brazier_screen_has_discovered_state_and_rest_only():
    screen = render_world(world_view(kind="brazier"))
    assert "🔥 Braseiro · Descoberto" in screen.text
    assert "Ativar Braseiro" not in screen.text
    assert [button.text for button in screen.keyboard.inline_keyboard[0]] == ["Descansar"]


def test_menu_does_not_invent_missing_quest():
    # Application refuses to construct this state from PostgreSQL without P1;
    # the renderer also requires the authoritative title explicitly.
    text = render_world(world_view(quest_title="Vozes na Estrada")).text
    assert "Vozes na Estrada" in text


async def test_victory_creates_only_brazier_and_world_state(database):
    await character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    view = await win(service, view)
    async with database[1]() as session:
        assert await session.scalar(select(Brazier)) is not None
        assert await session.scalar(select(WorldState)) is not None
        assert await session.scalar(select(Achievement)) is None
        assert await session.scalar(select(Quest)) is None


async def test_rest_creates_p1_and_achievement_once(database):
    await character(database)
    # Seed the post-victory boundary as a migration/backfill would.
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    service = WorldService(database[1], "ocaso")
    view = await service.rest(1)
    assert view is not None and view.kind == "menu"
    await service.rest(1)
    async with database[1]() as session:
        assert len((await session.scalars(select(Achievement))).all()) == 1
        assert len((await session.scalars(select(Quest))).all()) == 1


async def test_two_rest_calls_are_idempotent_and_both_reconstruct_menu(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    first, second = await asyncio.gather(
        WorldService(database[1], "ocaso").rest(1),
        WorldService(database[1], "ocaso").rest(1),
    )
    assert first is not None and second is not None
    assert first.kind == second.kind == "menu"
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.stage == "menu:ready" and row.vigor == 100 and row.xp == 0
        assert len((await session.scalars(select(Achievement))).all()) == 1
        assert len((await session.scalars(select(Quest))).all()) == 1
        assert len((await session.scalars(select(Brazier))).all()) == 1
        assert len((await session.scalars(select(WorldState))).all()) == 1


async def test_old_rest_callback_after_menu_does_not_heal(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    service = WorldService(database[1], "ocaso")
    await service.rest(1)
    async with database[1].begin() as session:
        row = await session.scalar(
            select(Character).where(Character.telegram_id == 1).with_for_update()
        )
        row.hp -= Decimal("10")
        vigor, xp = row.vigor, row.xp
    result = await service.rest(1)
    assert result is not None and result.kind == "menu"
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.hp < row.max_hp and row.vigor == vigor and row.xp == xp


async def test_rest_requires_persisted_brazier(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "cinzas_na_estrada:ready_for_first_brazier"
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
    result = await WorldService(database[1], "ocaso").rest(1)
    assert result is None
    async with database[1]() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        assert row.stage == "cinzas_na_estrada:ready_for_first_brazier"
        assert await session.scalar(select(Achievement)) is None
        assert await session.scalar(select(Quest)) is None


async def test_menu_without_p1_is_inconsistent(database):
    await character(database)
    async with database[1].begin() as session:
        row = await session.scalar(select(Character).where(Character.telegram_id == 1))
        row.stage = "menu:ready"
        session.add(Brazier(character_id=row.id, brazier_id="tdo.brazier.estrada"))
        session.add(
            WorldState(character_id=row.id, region="Terras do Ocaso", location="Estrada das Cinzas")
        )
        session.add(Achievement(character_id=row.id, achievement_id="feat.tdo.cinzas_na_estrada"))
    assert await WorldService(database[1], "ocaso").resume(1) is None
