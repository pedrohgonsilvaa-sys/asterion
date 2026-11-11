"""Background jobs: timed Ronda de Caça encounters, Guild and Market upkeep, PvP."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from asterion.application.chronicle import ChronicleService
from asterion.application.expeditions import ExpeditionService
from asterion.application.guild_battle import GuildBattleService
from asterion.application.guilds import GuildService
from asterion.application.market import MarketService
from asterion.application.oaths import OathService
from asterion.application.outbox import OutboxDispatcher
from asterion.application.pvp import PvpService
from asterion.application.round import RoundService
from asterion.application.trades import TradeService
from asterion.application.world_events import WorldEventService
from asterion.bot.expedition_handlers import deliver_expedition_notices
from asterion.bot.guild_battle_handlers import deliver_guild_battle_notices
from asterion.bot.oath_handlers import deliver_oath_notices
from asterion.bot.pvp_handlers import deliver_notices
from asterion.bot.world_event_handlers import deliver_world_event_notices
from asterion.config import get_settings
from asterion.infrastructure.db.job_lock import run_exclusive
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
    guild_battle = GuildBattleService(SessionFactory, settings.server_id)

    async def run_guild_battle_maintenance() -> None:
        notices = await guild_battle.run_maintenance()
        if notices and settings.telegram_bot_enabled and settings.telegram_bot_token:
            from asterion.bot.runtime import get_bot_runtime

            await deliver_guild_battle_notices(guild_battle, get_bot_runtime().bot, notices)

    # Pairing at 20:30, both Fronts at 21:00, the Champion and the 60s turn timers.
    # Each notice follows its notification category (Essenciais or PvP/Batalha).
    scheduler.add_job(
        run_guild_battle_maintenance,
        "interval",
        seconds=5,
        id="guild-battle-upkeep",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    world_events = WorldEventService(SessionFactory, settings.server_id)

    async def run_world_event_maintenance() -> None:
        notices = await world_events.run_maintenance()
        if notices and settings.telegram_bot_enabled and settings.telegram_bot_token:
            from asterion.bot.runtime import get_bot_runtime

            await deliver_world_event_notices(get_bot_runtime().bot, notices)

    # Openings, phase timers, the deadline and paying finished occurrences.
    scheduler.add_job(
        run_world_event_maintenance,
        "interval",
        seconds=15,
        id="world-event-upkeep",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Crônica: vote close and snapshot, runoff, finalization (Renome soft reset,
    # Salão da Vigília, new Batalha de Guildas standings) and the T+14d liquidation.
    scheduler.add_job(
        ChronicleService(SessionFactory, settings.server_id).run_maintenance,
        "interval",
        seconds=60,
        id="chronicle-upkeep",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    # Transactional Outbox: claims with SKIP LOCKED, so several instances are safe.
    scheduler.add_job(
        OutboxDispatcher(SessionFactory).run_maintenance,
        "interval",
        seconds=5,
        id="outbox-dispatch",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    oaths = OathService(SessionFactory, settings.server_id)
    expeditions = ExpeditionService(SessionFactory, settings.server_id)

    async def run_oath_maintenance() -> None:
        notices = await oaths.run_maintenance()
        if notices and settings.telegram_bot_enabled and settings.telegram_bot_token:
            from asterion.bot.runtime import get_bot_runtime

            await deliver_oath_notices(get_bot_runtime().bot, notices)

    async def run_expedition_maintenance() -> None:
        notices = await expeditions.run_maintenance()
        if notices and settings.telegram_bot_enabled and settings.telegram_bot_token:
            from asterion.bot.runtime import get_bot_runtime

            await deliver_expedition_notices(get_bot_runtime().bot, notices)

    # Cycle openings, idle Provações, the grace period and paying finished cycles.
    # Frozen rosters, closed stages and paying finished Expedições.
    for job_id, job in (
        ("oath-upkeep", run_oath_maintenance),
        ("expedition-upkeep", run_expedition_maintenance),
    ):
        scheduler.add_job(
            job,
            "interval",
            seconds=15,
            id=job_id,
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    # One execution per tick across all instances (the Outbox claims rows itself).
    # Each lock holds a connection while its job runs, so the locks get their own
    # pool: one connection per job (max_instances=1), never the game's pool.
    locked = [job for job in scheduler.get_jobs() if job.id != "outbox-dispatch"]
    lock_engine = create_async_engine(
        settings.database_url, pool_pre_ping=True, pool_size=len(locked), max_overflow=0
    )
    for job in locked:
        job.modify(func=_exclusive(lock_engine, job.id, job.func))
    return scheduler


def _exclusive(lock_engine: AsyncEngine, job_id, job):
    async def run() -> None:
        await run_exclusive(lock_engine, job_id, job)

    return run
