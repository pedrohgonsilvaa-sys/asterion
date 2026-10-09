"""Test helpers for advancing PvPvE queues without waiting on wall-clock time."""

from datetime import timedelta


def disable_round_pvpve_for_test(service):
    """Keep tests of ordinary Ronda behavior independent from PvPvE matching."""

    async def no_round_match(*_args, **_kwargs):
        return False

    service.pvpve.queue_round_hunt = no_round_match
    return service


async def start_manual_hunt_after_no_match(service, actor: int, monkeypatch):
    """Resolve an unmatched manual queue at its real expiry and return its PvE combat."""
    queued = await service.start_hunt(actor)
    if queued is None or queued.kind != "hunt_queue":
        return queued
    if queued.activity_id is None:
        raise AssertionError("waiting Hunt queue has no persisted activity id")

    from sqlalchemy import select

    from asterion.application import pvpve as pvpve_module
    from asterion.infrastructure.db.models import PvpveQueue, PvpveQueueMember

    async with service.sessions() as session:
        queue = await session.scalar(
            select(PvpveQueue)
            .join(PvpveQueueMember, PvpveQueueMember.queue_id == PvpveQueue.id)
            .where(PvpveQueueMember.game_activity_id == queued.activity_id)
        )
        if queue is None:
            raise AssertionError("waiting Hunt activity has no PvPvE queue")
        expires_at = queue.expires_at

    with monkeypatch.context() as clock:
        clock.setattr(
            pvpve_module,
            "_utcnow",
            lambda: expires_at + timedelta(seconds=1),
        )
        if not await service.pvpve.refresh_queue(actor, queued.activity_id):
            raise AssertionError("unmatched Hunt queue did not resolve at expiry")
        resolved = await service.resume(actor)

    if resolved is None or resolved.kind != "combat":
        raise AssertionError("an unmatched Hunt did not continue as ordinary PvE")
    return resolved
