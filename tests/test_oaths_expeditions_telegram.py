"""Telegram surface of the Juramento and the Expedição (GDD §22, UI §48.5, §48.6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from sqlalchemy import select

from asterion.application.expeditions import (
    ExpeditionHubView,
    ExpeditionNotice,
    ExpeditionResultView,
    ExpeditionService,
    ExpeditionStageNotice,
)
from asterion.application.guilds import GuildView
from asterion.application.oaths import (
    OathAttemptResultView,
    OathCycleResultView,
    OathHubView,
    OathNotice,
    OathRewardItem,
    OathService,
    OathTurnNotice,
)
from asterion.bot.combat_ui import OathCombatCallback
from asterion.bot.expedition_handlers import deliver_expedition_notices, expedition_router
from asterion.bot.expedition_ui import render_expedition
from asterion.bot.guilds_ui import render_guild_menu
from asterion.bot.oath_handlers import deliver_oath_notices, oath_router
from asterion.bot.oath_ui import error_text, render_abandon_confirm, render_oath
from asterion.domain.expeditions import ExpeditionResult
from asterion.domain.guilds import GuildRole, Recruitment
from asterion.infrastructure.db.models import Expedition, OathCycle
from tests.outbox_drain import RecordingOutbox
from tests.test_expeditions import LEADER, ROUTE
from tests.test_expeditions import _seed as seed_expedition
from tests.test_guilds_telegram import callback_update
from tests.test_oaths import TRIAL, A, _seed

GUILD = "Aurora"
FUTURE = datetime(2026, 11, 13, 21, 0, tzinfo=UTC)


def _data(screen) -> list[str]:
    return [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]


def test_empty_oath_catalog_screen():
    screen = render_oath(OathHubView(catalog_empty=True))
    assert "Nenhum Juramento programado" in screen.text
    assert "oath:solo" not in _data(screen)
    assert "guild:root" in _data(screen)


def test_open_oath_offers_solo_and_group():
    screen = render_oath(
        OathHubView(
            guild_name=GUILD,
            window="open",
            deadline=FUTURE,
            trial_name="Provação",
            provacoes_left=2,
            individual=25,
            collective=130,
            tier=1,
            next_threshold=300,
            bound=True,
            can_start=True,
            has_group=True,
        )
    )
    assert "Provações · 2/3" in screen.text
    assert "Contribuição · 25/180" in screen.text
    assert "130 pontos · Faixa I" in screen.text
    assert {"oath:solo", "group:oath:p"} <= set(_data(screen))


def test_active_attempt_hides_start_and_only_opener_abandons():
    base = {"window": "open", "deadline": FUTURE, "active_attempt_id": UUID(int=1)}
    opener = _data(render_oath(OathHubView(can_abandon=True, **base)))
    assert "oath:go" in opener and "oath:out" in opener and "oath:solo" not in opener
    assert "oath:out" not in _data(render_oath(OathHubView(**base)))
    assert "oath:outy" in _data(render_abandon_confirm())


def test_bound_elsewhere_is_explained():
    screen = render_oath(OathHubView(window="open", deadline=FUTURE, bound_elsewhere=True))
    assert "Guilda anterior" in screen.text
    assert "oath:solo" not in _data(screen)


def test_attempt_result_follows_ui_48_6():
    screen = render_oath(OathAttemptResultView("completed", GUILD, "Cumprido.", 60, 120))
    assert screen.text.splitlines()[:2] == ["⚜️ Provação · Concluída", "Juramento · Aurora"]
    assert "Contribuição · +60" in screen.text and "Ciclo · 120/180" in screen.text


def test_cycle_result_keeps_treasury_and_reward_apart():
    screen = render_oath(
        OathCycleResultView(
            GUILD, 3, 120, True, True, 7_000, 1_000, (OathRewardItem("Fragmento", 2),)
        )
    )
    assert screen.text.startswith("⚜️ Juramento · Faixa III")
    assert "Tesouraria · +7.000 Coroas" in screen.text
    assert "🎁 Recompensas" in screen.text and "2x Fragmento" in screen.text


def test_cycle_without_eligibility_omits_rewards_and_explains():
    screen = render_oath(OathCycleResultView(GUILD, 2, 40, True, False, 4_000))
    assert "🎁" not in screen.text and "⚠️ Não Elegível" not in screen.text
    assert "não alcançou a contribuição" in screen.text
    assert "Tesouraria" in screen.text


def test_turn_notice_opens_the_provacao():
    screen = render_oath(OathTurnNotice("Provação"))
    assert "sua vez" in screen.text and _data(screen) == ["oath:go"]


def test_error_texts_are_specific():
    assert "outra Guilda" in error_text("bound_elsewhere")
    assert error_text("???") == "Não foi possível concluir essa ação."


def _guild(role: GuildRole) -> GuildView:
    return GuildView(
        guild_id=UUID(int=2),
        name=GUILD,
        tag="AUR",
        recruitment=Recruitment.CLOSED,
        revision=0,
        member_count=1,
        capacity=5,
        over_cap=False,
        viewer_character_id=UUID(int=3),
        viewer_role=role,
        members=(),
    )


def test_guild_menu_reaches_both_systems():
    data = _data(render_guild_menu(_guild(GuildRole.MEMBER)))
    assert {"oath:hub", "exp:hub"} <= set(data)


def test_expedition_hub_screens():
    assert "Nenhuma Expedição" in render_expedition(ExpeditionHubView(catalog_empty=True)).text
    active = render_expedition(
        ExpeditionHubView(
            status="active",
            expedition_id=UUID(int=5),
            route_name="Rota",
            starts_at=FUTURE,
            stage=2,
            stage_ends=FUTURE,
            stage_flavor="Barro.",
            in_roster=True,
            options=(),
        )
    )
    assert "Estágio · 2/3" in active.text and "opção padrão" in active.text


def test_expedition_result_follows_ui_48_5():
    screen = render_expedition(
        ExpeditionResultView("Rota", ExpeditionResult.DEEP, 200, "Voltam.", 3_000, True, True, 800)
    )
    assert screen.text.startswith("🚩 Expedição · Profunda")
    assert "Pontuação · 200/300" in screen.text
    assert "Tesouraria · +3.000 Coroas" in screen.text
    assert "🏆" not in screen.text


@pytest.mark.asyncio
async def test_notices_are_enqueued_once_per_player():
    # Oath: a button-driven send stays direct and survives a blocked chat.
    blocked = TelegramForbiddenError(method=SendMessage(chat_id=1, text="x"), message="blocked")
    oath_bot = AsyncMock()
    oath_bot.send_message.side_effect = [blocked, None]
    notice = OathTurnNotice("Provação")
    await deliver_oath_notices(oath_bot, [OathNotice(1, notice), OathNotice(2, notice)])
    assert oath_bot.send_message.await_count == 2
    # Expedition: scheduler-only, goes through the Outbox.
    expedition_outbox = RecordingOutbox()
    stage = ExpeditionStageNotice("Rota", 1)
    await deliver_expedition_notices(
        expedition_outbox, [ExpeditionNotice(1, stage), ExpeditionNotice(2, stage)]
    )
    assert [m.chat_id for m in expedition_outbox.messages] == [1, 2]


class _Client:
    def __init__(self, router):
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(router)
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


def _buttons(method) -> list[str]:
    return [
        button.callback_data
        for row in method.reply_markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


@pytest.mark.asyncio
async def test_start_and_fight_a_provacao_through_the_buttons(database):
    await _seed(database)
    service = OathService(database[1], "ocaso", (TRIAL,))
    client = _Client(oath_router(service, {}))
    now = datetime.now(UTC)
    async with database[1].begin() as session:
        session.add(
            OathCycle(
                server_id="ocaso",
                cycle_key="teste",
                trial_id=TRIAL.trial_id,
                status="open",
                opens_at=now - timedelta(minutes=1),
                deadline_at=now + timedelta(hours=1),
                grace_ends_at=now + timedelta(hours=2),
                ruleset_version="oath_v1",
            )
        )
    hub = await client.click(A, "oath:hub")
    assert "Provação de Teste" in hub.text and "oath:solo" in _buttons(hub)
    combat = await client.click(A, "oath:solo")
    assert combat.text.startswith("⚜️ Provação de Teste · Combate 1/3")
    packed = [item for item in _buttons(combat) if item.startswith("oa:")]
    assert packed, "the combat must use the Juramento callback"
    assert OathCombatCallback.unpack(packed[0]).action_index >= 0
    assert await client.click(A, packed[0]) is not None
    assert (await client.click(A, "oath:hub")).text.startswith("⚜️ Juramento")
    confirm = await client.click(A, "oath:out")
    assert "oath:outy" in _buttons(confirm)
    ended = await client.click(A, "oath:outy")
    assert ended.text.startswith("⚜️ Provação · Abandonada")
    await client.bot.session.close()


@pytest.mark.asyncio
async def test_build_roster_and_choose_through_the_buttons(database):
    await seed_expedition(database)
    service = ExpeditionService(database[1], "ocaso", (ROUTE,))
    client = _Client(expedition_router(service, {}))
    hub = await client.click(LEADER, "exp:hub")
    assert "Rota de Teste" in hub.text
    toggles = [item for item in _buttons(hub) if item.startswith("exp:t:")]
    assert len(toggles) == 7
    for toggle in toggles[:3]:
        last = await client.click(LEADER, toggle)
    assert "3/6" in last.text
    async with database[1].begin() as session:
        expedition = await session.scalar(select(Expedition))
        now = datetime.now(UTC)
        expedition.starts_at = now - timedelta(minutes=1)
        expedition.ends_at = now + timedelta(hours=71)
    await service.run_maintenance()
    active = await client.click(LEADER, "exp:hub")
    assert "Estágio · 1/3" in active.text
    options = [item for item in _buttons(active) if item.startswith("exp:c:")]
    assert len(options) == 3
    done = await client.click(LEADER, options[0])
    assert "Sua escolha" in done.text
    await client.bot.session.close()


def test_scheduler_registers_both_jobs():
    from asterion.bot.round_scheduler import build_round_scheduler

    job_ids = {job.id for job in build_round_scheduler().get_jobs()}
    assert {"oath-upkeep", "expedition-upkeep"} <= job_ids
