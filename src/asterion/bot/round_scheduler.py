"""Background jobs: timed Ronda de Caça encounters, Guild and Market upkeep."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from asterion.application.guilds import GuildService
from asterion.application.market import MarketService
from asterion.application.pvp import PvpService
from asterion.application.round import RoundService
from asterion.application.trades import TradeService
from asterion.bot.pvp_handlers import deliver_notices
from asterion.config import get_settings
from asterion.infrastructure.db.session import SessionFactory


def build_round_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    service = RoundService(SessionFactory, settings.server_id)
    guilds = GuildService(SessionFactory, settings.server_id)
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        service.advance_due_rounds,
        "interval",
        seconds=15,
        id="hunt-round-advance",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Finished Obras, Leader succession and due dissolutions also run lazily on
    # every Guild action; this sweep covers Guilds nobody opens.
    scheduler.add_job(
        guilds.run_maintenance,
        "interval",
        seconds=60,
        id="guild-upkeep",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Listings and trades also settle lazily; this covers the ones nobody opens.
    for job_id, job in (
        ("market-upkeep", MarketService(SessionFactory, settings.server_id).run_maintenance),
        ("trade-upkeep", TradeService(SessionFactory, settings.server_id).run_maintenance),
    ):
        scheduler.add_job(
            job,
            "interval",
            seconds=60,
            id=job_id,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    pvp = PvpService(SessionFactory, settings.server_id)

    async def run_pvp_maintenance() -> None:
        notices = await pvp.run_maintenance()
        if notices and settings.telegram_bot_enabled and settings.telegram_bot_token:
            from asterion.bot.runtime import get_bot_runtime

            await deliver_notices(get_bot_runtime().bot, notices)

    # Turn timers, Entry Confirmations, pairing, the Arena windows and decay.
    scheduler.add_job(
        run_pvp_maintenance,
        "interval",
        seconds=5,
        id="pvp-upkeep",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    return scheduler
