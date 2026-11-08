"""Background jobs: timed Ronda de Caça encounters and Guild upkeep."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from asterion.application.guilds import GuildService
from asterion.application.round import RoundService
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
    return scheduler
