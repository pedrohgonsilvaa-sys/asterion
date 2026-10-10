"""Test helpers for exercising PvPvE queues without artificial wait periods."""


def disable_round_pvpve_for_test(service):
    """Keep tests of ordinary Ronda behavior independent from PvPvE matching."""

    async def no_round_match(*_args, **_kwargs):
        return False

    service.pvpve.queue_round_hunt = no_round_match
    return service


async def start_manual_hunt_after_no_match(service, actor: int, monkeypatch):
    """Continue an unmatched manual queue immediately as its PvE combat."""
    queued = await service.start_hunt(actor)
    if queued is None or queued.kind != "hunt_queue":
        return queued
    if queued.activity_id is None:
        raise AssertionError("waiting Hunt queue has no persisted activity id")

    from sqlalchemy import select

    from asterion.infrastructure.db.models import PvpveQueue, PvpveQueueMember

    async with service.sessions() as session:
        queue = await session.scalar(
            select(PvpveQueue)
            .join(PvpveQueueMember, PvpveQueueMember.queue_id == PvpveQueue.id)
            .where(PvpveQueueMember.game_activity_id == queued.activity_id)
        )
        if queue is None:
            raise AssertionError("waiting Hunt activity has no PvPvE queue")
        queue_id = queue.id

    resolved = await service.pvpve.continue_queue(actor, queue_id)

    if resolved is None or resolved.kind != "combat":
        raise AssertionError("an unmatched Hunt did not continue as ordinary PvE")
    return resolved
