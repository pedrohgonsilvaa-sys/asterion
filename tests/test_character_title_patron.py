"""HUD do Refúgio: Título persistido do personagem e estado de Patrono da conta."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from asterion.application.road import REFUGE
from asterion.application.world import WorldService
from asterion.bot.world_ui import render_refuge_dashboard
from asterion.domain.creation import STARTING_CHARACTER_TITLE
from asterion.infrastructure.db.models import Character, PatronAccount
from tests.test_road_integration import _seed_road
from tests.test_tdo_refuge_menu_principal import _set_state


@pytest.mark.asyncio
async def test_new_character_persists_the_starting_title_and_hud_shows_it(database):
    actor, _road = await _seed_road(database, actor=893401)
    sessions = database[1]
    await _set_state(sessions, actor, region="Terras do Ocaso", location=REFUGE)
    async with sessions() as session:
        title = await session.scalar(select(Character.title).where(Character.telegram_id == actor))
    assert title == STARTING_CHARACTER_TITLE == "Caminhante das Cinzas"

    view = await WorldService(sessions, "ocaso").resume(actor)
    assert view.selected_title == "Caminhante das Cinzas"
    assert view.patron_active is False
    text = render_refuge_dashboard(view).text
    assert "🎖️ <code>Caminhante das Cinzas</code>" in text
    assert "Patrono" not in text


@pytest.mark.asyncio
async def test_persisted_title_is_a_character_value_not_fixed_ui_text(database):
    actor, _road = await _seed_road(database, actor=893402)
    sessions = database[1]
    await _set_state(sessions, actor, region="Terras do Ocaso", location=REFUGE)
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.title = "Outro Título"
    view = await WorldService(sessions, "ocaso").resume(actor)
    assert view.selected_title == "Outro Título"


@pytest.mark.asyncio
async def test_patron_state_changes_with_the_account_status(database):
    actor, _road = await _seed_road(database, actor=893403)
    sessions = database[1]
    await _set_state(sessions, actor, region="Terras do Ocaso", location=REFUGE)
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        session.add(
            PatronAccount(
                account_id=actor,
                active_until=now + timedelta(days=3),
                paid_days=30,
                temporary_granted=True,
                updated_at=now,
            )
        )
    service = WorldService(sessions, "ocaso")
    assert (await service.resume(actor)).patron_active is True
    async with sessions.begin() as session:
        row = await session.get(PatronAccount, actor)
        row.active_until = now - timedelta(days=1)
    assert (await service.resume(actor)).patron_active is False
