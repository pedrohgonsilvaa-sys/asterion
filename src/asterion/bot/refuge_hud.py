"""Dados reais do HUD do Refúgio do Ocaso: Dádiva Diária e Crônica."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from asterion.application.chronicle import ChronicleService
from asterion.application.engagement import DailyGiftService, EngagementError
from asterion.bot.chronicle_ui import chronicle_hud_status


@dataclass(frozen=True, slots=True)
class RefugeHud:
    gift_available: bool = False
    chronicle: str | None = None


class RefugeHudLoader:
    """Lê os dados do HUD nos serviços existentes, sem criar regra nova."""

    def __init__(
        self,
        gifts: DailyGiftService,
        chronicle: ChronicleService,
    ):
        self.gifts, self.chronicle = gifts, chronicle

    async def __call__(self, actor: int, *, now: datetime | None = None) -> RefugeHud:
        moment = now or datetime.now(UTC)
        try:
            gift_available = not (await self.gifts.view(actor, now=moment)).claimed_today
        except EngagementError:
            gift_available = False
        try:
            chronicle = chronicle_hud_status(await self.chronicle.view(actor, now=moment))
        except EngagementError:
            chronicle = None
        return RefugeHud(gift_available, chronicle)
