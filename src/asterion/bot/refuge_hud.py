"""Dados reais do HUD do Refúgio do Ocaso: Dádiva Diária, Apoiador e Crônica."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.chronicle import ChronicleService
from asterion.application.engagement import DailyGiftService, EngagementError
from asterion.application.payments import patron_until_readonly
from asterion.bot.chronicle_ui import chronicle_hud_status
from asterion.domain.chronicle import TIMEZONE


@dataclass(frozen=True, slots=True)
class RefugeHud:
    gift_available: bool = False
    supporter: str | None = None
    chronicle: str | None = None


class RefugeHudLoader:
    """Lê os dados do HUD nos serviços existentes, sem criar regra nova."""

    def __init__(
        self,
        gifts: DailyGiftService,
        chronicle: ChronicleService,
        sessions: async_sessionmaker[AsyncSession],
    ):
        self.gifts, self.chronicle, self.sessions = gifts, chronicle, sessions

    async def __call__(self, actor: int, *, now: datetime | None = None) -> RefugeHud:
        moment = now or datetime.now(UTC)
        try:
            gift_available = not (await self.gifts.view(actor, now=moment)).claimed_today
        except EngagementError:
            gift_available = False
        until = await patron_until_readonly(self.sessions, actor, now=moment)
        supporter = (
            "Inativo" if until is None else f"Ativo até {until.astimezone(TIMEZONE):%d/%m}"
        )
        try:
            chronicle = chronicle_hud_status(await self.chronicle.view(actor, now=moment))
        except EngagementError:
            chronicle = None
        return RefugeHud(gift_available, supporter, chronicle)
