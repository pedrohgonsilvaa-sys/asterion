"""Dados reais do HUD do Refúgio do Ocaso: Dádiva Diária, Crônica e barra do Flagelo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from asterion.application.chronicle import ChronicleService
from asterion.application.engagement import DailyGiftService, EngagementError
from asterion.application.flagelos import FlageloError, FlageloService, RegionStatus
from asterion.bot.chronicle_ui import chronicle_hud_status


@dataclass(frozen=True, slots=True)
class RefugeHud:
    gift_available: bool = False
    chronicle: str | None = None
    # O Despertar dos Flagelos (espec. final §17): barra da Região atual e Flagelo desperto.
    flagelo: RegionStatus | None = None


class RefugeHudLoader:
    """Lê os dados do HUD nos serviços existentes, sem criar regra nova."""

    def __init__(
        self,
        gifts: DailyGiftService,
        chronicle: ChronicleService,
        flagelos: FlageloService | None = None,
    ):
        self.gifts, self.chronicle, self.flagelos = gifts, chronicle, flagelos

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
        flagelo = None
        if self.flagelos is not None:
            try:
                flagelo = await self.flagelos.region_status(actor)
            except FlageloError:
                flagelo = None
        return RefugeHud(gift_available, chronicle, flagelo)
