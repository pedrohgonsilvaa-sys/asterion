"""Direct Trade between two characters of the same server.

Sources: GDD Estrutural v1.6.0 §29, §23.2, §43.2 and §49.18.

Lock order (every write follows it, which rules out deadlocks):
TradeSession -> Characters in ascending id order. An invite locks only the two
Characters, and creating the row under those locks is what keeps each character
in at most one live trade.

Offered items wait in escrow, so a commit only has to fit what each side receives
(§29 full-to-full swaps work). A deleted character leaves a NULL party behind; the
trade then closes at the next touch, returning only the other side's items.

Crowns never move through a trade: there is no column or path for them.

Not implemented: §29 "patch reseta confirmações", since no item patch tool exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.account_risk import record_linked_cooccurrence
from asterion.application.item_escrow import (
    EscrowError,
    NegotiableEntry,
    deliver_to_inventory,
    is_mythic,
    negotiable_entries,
    require_trading_character,
    return_to_owner,
    take_from_inventory,
)
from asterion.domain.market import (
    TRADE_IDLE_TIMEOUT,
    TRADE_MAX_DURATION,
    market_unlocked,
    trade_steps_required,
)
from asterion.infrastructure.db.models import Character, TradeItem, TradeSession

LIVE_STATUSES = ("invited", "open")


class TradeError(ValueError):
    """A Direct Trade action is invalid for the current, revalidated state."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class _DoesNotFit(Exception):
    """Aborts the savepoint of a commit when an Inventory cannot take its items."""


@dataclass(frozen=True, slots=True)
class TradeItemView:
    item_id: UUID
    kind: str
    title: str
    rarity: str | None
    quantity: int


@dataclass(frozen=True, slots=True)
class TradeView:
    trade_id: UUID
    status: str
    revision: int
    viewer_is_initiator: bool
    counterpart_name: str
    counterpart_telegram_id: int | None
    my_items: tuple[TradeItemView, ...]
    their_items: tuple[TradeItemView, ...]
    my_steps: int
    their_steps: int
    steps_required: int
    expires_at: datetime
    close_reason: str | None = None


@dataclass(frozen=True, slots=True)
class TradeOutcome:
    """`status` is "waiting", "committed" or "no_space"."""

    status: str
    view: TradeView


class TradeService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id

    # ---------------------------------------------------------------- upkeep

    async def run_maintenance(self, *, now: datetime | None = None, limit: int = 100) -> int:
        """Close trades past a §49.18 timeout or missing a party; safe to call often."""
        now = _utcnow(now)
        async with self.sessions() as session:
            due = (
                await session.scalars(
                    select(TradeSession.id)
                    .where(
                        TradeSession.server_id == self.server_id,
                        TradeSession.status.in_(LIVE_STATUSES),
                        or_(
                            TradeSession.last_activity_at <= now - TRADE_IDLE_TIMEOUT,
                            TradeSession.expires_at <= now,
                            TradeSession.initiator_character_id.is_(None),
                            TradeSession.partner_character_id.is_(None),
                        ),
                    )
                    .order_by(TradeSession.last_activity_at)
                    .limit(limit)
                )
            ).all()
        for trade_id in due:
            await self._settle(trade_id, now)
        return len(due)

    async def _settle(self, trade_id: UUID, now: datetime) -> None:
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            if trade is None or trade.status not in LIVE_STATUSES:
                return
            if _party_missing(trade):
                await self._close(session, trade, "cancelled", "party_deleted", now)
            elif _is_due(trade, now):
                await self._close(session, trade, "expired", "timeout", now)

    async def _settle_character(self, character_id: UUID, now: datetime) -> None:
        async with self.sessions() as session:
            trades = (
                await session.scalars(
                    select(TradeSession.id).where(
                        TradeSession.status.in_(LIVE_STATUSES),
                        _involves(character_id),
                    )
                )
            ).all()
        for trade_id in trades:
            await self._settle(trade_id, now)

    async def _close(self, session, trade, status: str, reason: str, now: datetime) -> None:
        """Ends a live trade and gives every escrowed item back to its owner."""
        owners = await self._lock_parties(session, trade)
        items = await self._escrow_items(session, trade.id)
        for item in items:
            owner = owners.get(item.owner_character_id)
            if owner is None:
                item.status = "discarded"
                continue
            await return_to_owner(
                session,
                owner,
                item.item_kind,
                item.item_snapshot,
                item.quantity,
                f"market:trade:{item.id}",
            )
            item.status = "returned"
        trade.status = status
        trade.close_reason = reason
        trade.closed_at = now

    # ------------------------------------------------------------------ reads

    async def current(self, actor: int, *, now: datetime | None = None) -> TradeView | None:
        """The actor's live trade or incoming invite, rebuilt from persisted state."""
        now = _utcnow(now)
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            character_id = character.id
        await self._settle_character(character_id, now)
        async with self.sessions() as session:
            trade = await session.scalar(
                select(TradeSession)
                .where(TradeSession.status.in_(LIVE_STATUSES), _involves(character_id))
                .order_by(TradeSession.created_at.desc())
                .limit(1)
            )
            return None if trade is None else await self._view(session, trade, character_id)

    async def sources(self, actor: int, kind: str) -> tuple[NegotiableEntry, ...]:
        async with self.sessions() as session:
            character = await self._require_character(session, actor)
            try:
                return await negotiable_entries(session, character.id, kind)
            except EscrowError as exc:
                raise TradeError(exc.code) from exc

    # -------------------------------------------------------------- lifecycle

    async def invite(
        self, actor: int, partner_name: str, *, now: datetime | None = None
    ) -> TradeView:
        now = _utcnow(now)
        async with self.sessions() as session:
            initiator = await self._require_character(session, actor)
            initiator_id = initiator.id
            partner_id = await session.scalar(
                select(Character.id).where(
                    func.lower(Character.name) == partner_name.strip().casefold(),
                    Character.server_id == self.server_id,
                )
            )
        if partner_id is None:
            raise TradeError("partner_unavailable")
        if partner_id == initiator_id:
            raise TradeError("self_trade")
        await self._settle_character(initiator_id, now)
        await self._settle_character(partner_id, now)
        async with self.sessions.begin() as session:
            locked = await self._lock_characters(session, [initiator_id, partner_id])
            if len(locked) != 2:
                raise TradeError("partner_unavailable")
            if not market_unlocked(locked[partner_id].stage):
                raise TradeError("partner_unavailable")
            busy = await session.scalar(
                select(func.count(TradeSession.id)).where(
                    TradeSession.status.in_(LIVE_STATUSES),
                    or_(_involves(initiator_id), _involves(partner_id)),
                )
            )
            if busy:
                raise TradeError("trade_busy")
            trade = TradeSession(
                server_id=self.server_id,
                initiator_character_id=initiator_id,
                partner_character_id=partner_id,
                status="invited",
                revision=0,
                initiator_steps=0,
                partner_steps=0,
                created_at=now,
                last_activity_at=now,
                expires_at=now + TRADE_MAX_DURATION,
            )
            session.add(trade)
            await session.flush()
            return await self._view(session, trade, initiator_id)

    async def respond(
        self, actor: int, trade_id: UUID, *, accept: bool, now: datetime | None = None
    ) -> TradeView:
        now = _utcnow(now)
        await self._settle(trade_id, now)
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            character = await self._require_character(session, actor)
            if trade is None or trade.status != "invited":
                raise TradeError("trade_unavailable")
            if trade.partner_character_id != character.id:
                raise TradeError("not_invited")
            if accept:
                trade.status = "open"
                trade.last_activity_at = now
            else:
                trade.status = "declined"
                trade.close_reason = "declined"
                trade.closed_at = now
            return await self._view(session, trade, character.id)

    async def cancel(self, actor: int, trade_id: UUID, *, now: datetime | None = None) -> TradeView:
        now = _utcnow(now)
        await self._settle(trade_id, now)
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            character = await self._require_character(session, actor)
            _require_party(trade, character.id)
            if trade.status not in LIVE_STATUSES:
                raise TradeError("trade_unavailable")
            await self._close(session, trade, "cancelled", "cancelled", now)
            return await self._view(session, trade, character.id)

    # ------------------------------------------------------------------ offer

    async def add_item(
        self,
        actor: int,
        trade_id: UUID,
        kind: str,
        source_id: UUID,
        quantity: int,
        *,
        now: datetime | None = None,
    ) -> TradeView:
        """§29: the item is reserved at once and every confirmation is reset."""
        now = _utcnow(now)
        await self._settle(trade_id, now)
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            character = await self._require_character(session, actor, guard=True)
            _require_open_party(trade, character.id)
            try:
                taken = await take_from_inventory(session, character.id, kind, source_id, quantity)
            except EscrowError as exc:
                raise TradeError(exc.code) from exc
            session.add(
                TradeItem(
                    trade_id=trade.id,
                    owner_character_id=character.id,
                    item_kind=taken.kind,
                    title=taken.title,
                    rarity=taken.rarity,
                    item_snapshot=taken.snapshot,
                    quantity=taken.quantity,
                    status="escrow",
                    added_at=now,
                )
            )
            _touch(trade, now)
            await session.flush()
            return await self._view(session, trade, character.id)

    async def remove_item(
        self, actor: int, trade_id: UUID, item_id: UUID, *, now: datetime | None = None
    ) -> TradeView:
        now = _utcnow(now)
        await self._settle(trade_id, now)
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            character = await self._require_character(session, actor, lock=True)
            _require_open_party(trade, character.id)
            item = await session.scalar(
                select(TradeItem).where(
                    TradeItem.id == item_id,
                    TradeItem.trade_id == trade.id,
                    TradeItem.owner_character_id == character.id,
                    TradeItem.status == "escrow",
                )
            )
            if item is None:
                raise TradeError("item_unavailable")
            await return_to_owner(
                session,
                character,
                item.item_kind,
                item.item_snapshot,
                item.quantity,
                f"market:trade:{item.id}",
            )
            item.status = "withdrawn"
            _touch(trade, now)
            await session.flush()
            return await self._view(session, trade, character.id)

    # ----------------------------------------------------------- confirmation

    async def confirm(
        self, actor: int, trade_id: UUID, revision: int, *, now: datetime | None = None
    ) -> TradeOutcome:
        """§29 confirmation steps; the last one commits both sides atomically."""
        now = _utcnow(now)
        await self._settle(trade_id, now)
        async with self.sessions.begin() as session:
            trade = await self._lock_trade(session, trade_id)
            character = await self._require_character(session, actor)
            _require_open_party(trade, character.id)
            if revision != trade.revision:
                raise TradeError("trade_changed")
            items = await self._escrow_items(session, trade.id)
            if not items:
                raise TradeError("trade_empty")
            required = trade_steps_required(any(is_mythic(item.rarity) for item in items))
            is_initiator = trade.initiator_character_id == character.id
            mine = trade.initiator_steps if is_initiator else trade.partner_steps
            theirs = trade.partner_steps if is_initiator else trade.initiator_steps
            if mine >= required or theirs < mine:
                raise TradeError("waiting_partner")
            mine += 1
            if is_initiator:
                trade.initiator_steps = mine
            else:
                trade.partner_steps = mine
            trade.last_activity_at = now
            status = "waiting"
            if mine == required and theirs == required:
                status = await self._commit(session, trade, items, now)
            await session.flush()
            return TradeOutcome(status, await self._view(session, trade, character.id))

    async def _commit(self, session, trade, items, now: datetime) -> str:
        parties = await self._lock_parties(session, trade)
        if len(parties) != 2:
            raise TradeError("trade_unavailable")
        receivers = {
            trade.initiator_character_id: trade.partner_character_id,
            trade.partner_character_id: trade.initiator_character_id,
        }
        try:
            async with session.begin_nested():
                for item in items:
                    undelivered = await deliver_to_inventory(
                        session,
                        receivers[item.owner_character_id],
                        item.item_kind,
                        item.item_snapshot,
                        item.quantity,
                        new_owner=True,
                    )
                    if undelivered:
                        raise _DoesNotFit
        except _DoesNotFit:
            # §23.2: no Pending for a voluntary trade. Both must review it again.
            _touch(trade, now)
            return "no_space"
        for item in items:
            item.status = "delivered"
        trade.status = "committed"
        trade.close_reason = "committed"
        trade.closed_at = now
        await record_linked_cooccurrence(
            session,
            server_id=self.server_id,
            activity_kind="direct_trade",
            activity_reference=str(trade.id),
            characters=list(parties.values()),
            now=now,
        )
        return "committed"

    # ---------------------------------------------------------------- helpers

    async def _view(self, session, trade, viewer_id: UUID) -> TradeView:
        is_initiator = trade.initiator_character_id == viewer_id
        other_id = trade.partner_character_id if is_initiator else trade.initiator_character_id
        other = await session.get(Character, other_id) if other_id is not None else None
        rows = (
            await session.scalars(
                select(TradeItem)
                .where(TradeItem.trade_id == trade.id, TradeItem.status != "withdrawn")
                .order_by(TradeItem.added_at, TradeItem.id)
            )
        ).all()
        mine = tuple(_item_view(row) for row in rows if row.owner_character_id == viewer_id)
        theirs = tuple(_item_view(row) for row in rows if row.owner_character_id != viewer_id)
        return TradeView(
            trade_id=trade.id,
            status=trade.status,
            revision=trade.revision,
            viewer_is_initiator=is_initiator,
            counterpart_name=other.name if other else "",
            counterpart_telegram_id=other.telegram_id if other else None,
            my_items=mine,
            their_items=theirs,
            my_steps=trade.initiator_steps if is_initiator else trade.partner_steps,
            their_steps=trade.partner_steps if is_initiator else trade.initiator_steps,
            steps_required=trade_steps_required(any(is_mythic(row.rarity) for row in rows)),
            expires_at=min(trade.expires_at, trade.last_activity_at + TRADE_IDLE_TIMEOUT),
            close_reason=trade.close_reason,
        )

    async def _escrow_items(self, session, trade_id: UUID) -> list[TradeItem]:
        rows = await session.scalars(
            select(TradeItem)
            .where(TradeItem.trade_id == trade_id, TradeItem.status == "escrow")
            .order_by(TradeItem.added_at, TradeItem.id)
        )
        return list(rows.all())

    async def _lock_trade(self, session, trade_id: UUID) -> TradeSession | None:
        return await session.scalar(
            select(TradeSession)
            .where(TradeSession.id == trade_id, TradeSession.server_id == self.server_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def _lock_parties(self, session, trade) -> dict[UUID, Character]:
        ids = [
            value
            for value in (trade.initiator_character_id, trade.partner_character_id)
            if value is not None
        ]
        return await self._lock_characters(session, ids)

    async def _lock_characters(self, session, ids) -> dict[UUID, Character]:
        rows = await session.scalars(
            select(Character)
            .where(Character.id.in_(ids))
            .order_by(Character.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return {row.id: row for row in rows.all()}

    async def _require_character(
        self, session, actor: int, *, lock: bool = False, guard: bool = False
    ) -> Character:
        return await require_trading_character(
            session, actor, self.server_id, lock=lock, guard=guard, error=TradeError
        )


def _involves(character_id: UUID):
    return or_(
        TradeSession.initiator_character_id == character_id,
        TradeSession.partner_character_id == character_id,
    )


def _party_missing(trade: TradeSession) -> bool:
    return trade.initiator_character_id is None or trade.partner_character_id is None


def _is_due(trade: TradeSession, now: datetime) -> bool:
    return trade.expires_at <= now or trade.last_activity_at + TRADE_IDLE_TIMEOUT <= now


def _require_party(trade: TradeSession | None, character_id: UUID) -> None:
    if trade is None:
        raise TradeError("trade_unavailable")
    if character_id not in (trade.initiator_character_id, trade.partner_character_id):
        raise TradeError("not_a_party")


def _require_open_party(trade: TradeSession | None, character_id: UUID) -> None:
    _require_party(trade, character_id)
    if trade.status != "open":
        raise TradeError("trade_unavailable")


def _touch(trade: TradeSession, now: datetime) -> None:
    """§29: any change resets every confirmation and invalidates old buttons."""
    trade.revision += 1
    trade.initiator_steps = 0
    trade.partner_steps = 0
    trade.last_activity_at = now


def _item_view(row: TradeItem) -> TradeItemView:
    return TradeItemView(row.id, row.item_kind, row.title, row.rarity, row.quantity)


def _utcnow(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)
