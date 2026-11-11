"""Telegram surface for Eventos Mundiais (GDD §21, UI §48.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.world_events import (
    WorldEventHubView,
    WorldEventNotice,
    WorldEventResultView,
    WorldEventRewardItem,
    WorldEventService,
    WorldEventStatus,
)
from asterion.bot.combat_ui import WorldEventCombatCallback
from asterion.bot.guilds_ui import pack
from asterion.bot.world_event_handlers import (
    deliver_world_event_notices,
    world_event_router,
)
from asterion.bot.world_event_ui import error_text, render_withdraw_confirm, render_world_event
from tests.outbox_drain import RecordingOutbox
from tests.test_guilds_telegram import callback_update
from tests.test_world_events import EVENT, A, _seed

OCCURRENCE = UUID(int=9)


def _status(**changes) -> WorldEventStatus:
    base = {
        "occurrence_id": OCCURRENCE,
        "name": "Evento de Teste",
        "region": "Terras do Ocaso",
        "flavor": "O ar pesa.",
        "status": "active",
        "phase": 2,
        "boss_name": "Chefe de Teste",
        "boss_hp": Decimal(500),
        "boss_max_hp": Decimal(1000),
        "participants": 7,
        "seconds_to_start": 0,
        "can_enter": False,
        "joined": False,
        "withdrawn": False,
        "in_combat": False,
        "reentry_seconds": 0,
        "significant_actions": 3,
        "phases_done": 1,
        "eligible": False,
        "consumables_left": 2,
    }
    return WorldEventStatus(**(base | changes))


def _callbacks(screen) -> set[str]:
    return {button.callback_data for row in screen.keyboard.inline_keyboard for button in row}


def test_empty_catalog_screen():
    screen = render_world_event(WorldEventHubView(None, None))
    assert "Nenhum Evento Mundial programado." in screen.text
    assert _callbacks(screen) == {"world:adventure"}


def test_next_opening_uses_sao_paulo_time():
    opening = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)
    screen = render_world_event(WorldEventHubView(None, opening))
    assert "Próximo Evento · Terça às 12:00" in screen.text


def test_gathering_offers_entry_with_the_vigor_cost():
    view = WorldEventHubView(
        _status(status="gathering", phase=0, boss_name=None, can_enter=True, seconds_to_start=90),
        None,
    )
    screen = render_world_event(view)
    assert "Reunindo participantes · 90s" in screen.text
    assert "Entrar · 10 Vigor" in str(screen.keyboard)
    assert f"wev:in:{pack(OCCURRENCE)}" in _callbacks(screen)


def test_joined_screen_shows_progress_and_combat_button():
    screen = render_world_event(WorldEventHubView(_status(joined=True), None))
    assert "Fase 2/3" in screen.text
    assert "Ações Significativas · 3/8" in screen.text
    assert "Fases · 1/2" in screen.text
    assert f"wev:go:{pack(OCCURRENCE)}" in _callbacks(screen)
    assert f"wev:out:{pack(OCCURRENCE)}" in _callbacks(screen)


def test_waiting_for_reentry_hides_the_combat_button():
    screen = render_world_event(WorldEventHubView(_status(joined=True, reentry_seconds=45), None))
    assert "Reentrada em 45s" in screen.text
    assert f"wev:go:{pack(OCCURRENCE)}" not in _callbacks(screen)


def test_withdraw_needs_confirmation():
    screen = render_withdraw_confirm("abc")
    assert "perde o direito de reentrada" in screen.text
    assert _callbacks(screen) == {"wev:oy:abc", "wev:hub"}


def test_eligible_result_follows_ui_48_4():
    view = WorldEventResultView(
        "Evento",
        "Terras do Ocaso",
        "O silêncio volta.",
        True,
        True,
        100,
        80,
        (WorldEventRewardItem("Metal", 1),),
    )
    screen = render_world_event(view)
    assert screen.text.startswith("🏆 Evento Mundial · Concluído\nEvento · Terras do Ocaso")
    assert "✅ Participação · Elegível" in screen.text
    assert "🎁 Recompensas" in screen.text
    assert _callbacks(screen) == {"wev:hub"}


def test_insufficient_result_omits_the_rewards_block():
    screen = render_world_event(
        WorldEventResultView("Evento", "Terras do Ocaso", "O silêncio volta.", True, False)
    )
    assert "⚠️ Participação · Insuficiente" in screen.text
    assert "Recompensas" not in screen.text


def test_failed_event_explains_the_refund():
    screen = render_world_event(WorldEventResultView("Evento", "Terras do Ocaso", "", False, False))
    assert "Evento Mundial · Encerrado" in screen.text
    assert "Vigor foi devolvido" in screen.text


def test_error_text_shows_the_wait():
    assert error_text("reentry_wait", 30) == "Sua reentrada ainda não abriu. Faltam 30s."


@pytest.mark.asyncio
async def test_deliver_notices_enqueues_one_per_player():
    outbox = RecordingOutbox()
    view = WorldEventResultView("Evento", "Região", "", True, False)
    await deliver_world_event_notices(
        outbox, [WorldEventNotice(1, view), WorldEventNotice(2, view)]
    )
    assert [m.chat_id for m in outbox.messages] == [1, 2]


class _Client:
    def __init__(self, database):
        self.service = WorldEventService(database[1], "ocaso", (EVENT,))
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(world_event_router(self.service, {}))
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.sent = {}
        self.ids = iter(range(9000, 9900))

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, (SendMessage, EditMessageText)):
                self.sent["last"] = method
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or next(self.ids),
                    date=1,
                    chat=Chat(id=getattr(method, "chat_id", None) or 1, type="private"),
                    from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                    text=method.text,
                )
            return True

        self.bot.session.make_request = AsyncMock(side_effect=respond)

    async def click(self, actor, data):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, callback_update(data, actor=actor, update_id=self.update_id)
        )
        return self.sent.get("last")


def _keyboard_data(method) -> list[str]:
    return [
        button.callback_data
        for row in method.reply_markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


@pytest.mark.asyncio
async def test_join_and_fight_through_the_buttons(database):
    await _seed(database)
    client = _Client(database)
    await client.service.run_maintenance(now=datetime.now(UTC) - timedelta(days=30))
    # The router uses the real clock: place an occurrence around it.
    await _force_open_occurrence(database)
    hub = await client.click(A, "wev:hub")
    assert "Evento de Teste" in hub.text
    token = pack((await client.service.hub(A)).status.occurrence_id)
    joined = await client.click(A, f"wev:in:{token}")
    assert "Participação" in joined.text
    # Enter through the gathering window, then make the phase transition deterministic.
    await _start_phase_for_test(database, (await client.service.hub(A)).status.occurrence_id)
    combat = await client.click(A, f"wev:go:{token}")
    assert combat.text.startswith("🌍 Evento de Teste · Fase 1/3")
    packed = [item for item in _keyboard_data(combat) if item.startswith("we:")]
    assert packed, "the combat must use the Event callback"
    parsed = WorldEventCombatCallback.unpack(packed[0])
    assert parsed.action_index >= 0
    after = await client.click(A, packed[0])
    assert after is not None
    await client.bot.session.close()


async def _force_open_occurrence(database) -> None:
    from uuid import uuid4

    from asterion.infrastructure.db.models import WorldEventOccurrence

    now = datetime.now(UTC)
    opened = now - timedelta(minutes=6)
    async with database[1].begin() as session:
        session.add(
            WorldEventOccurrence(
                id=uuid4(),
                server_id="ocaso",
                event_id=EVENT.event_id,
                occurrence_key="forced",
                status="gathering",
                phase=0,
                opened_at=opened,
                phase_one_at=now - timedelta(seconds=1),
                entry_closes_at=now + timedelta(minutes=9),
                deadline_at=now + timedelta(minutes=54),
                participants_snapshot=0,
                boss_hp=Decimal(0),
                boss_max_hp=Decimal(0),
                state_version=0,
                ruleset_version="world_event_v1",
            )
        )


async def _start_phase_for_test(database, occurrence_id: UUID) -> None:
    """Make the phase transition due without depending on wall-clock timing."""
    from asterion.infrastructure.db.models import WorldEventOccurrence

    async with database[1].begin() as session:
        occurrence = await session.get(WorldEventOccurrence, occurrence_id, with_for_update=True)
        assert occurrence is not None
        occurrence.phase_one_at = datetime.now(UTC) - timedelta(seconds=1)
