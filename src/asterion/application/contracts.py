"""Contratos Regionais (Documento B): quadro, estados, progresso e resgate.

Regras de jogo: so Solo; recompensa apenas XP, Coroas e Materiais; nunca Missao,
WorldState ou no de escolha. Todo numero vem de `domain/contracts_config.py`.
O estado persistido e a unica autoridade: cada acao revalida personagem, dono,
estado, versao, elegibilidade e validade antes de mudar qualquer coisa (§27).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.item_escrow import require_trading_character
from asterion.application.progression import consolidate_character_level
from asterion.domain import contracts_config as cfg
from asterion.domain.chronicle_content import REGIONS_BY_NAME
from asterion.domain.contracts_catalog import BY_ID, ContractDefinition, definitions_for
from asterion.infrastructure.db.models import (
    Character,
    ContractInstance,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

AVAILABLE = "DISPONIVEL"
ACCEPTED = "ACEITO"
IN_PROGRESS = "EM_ANDAMENTO"
COMPLETED = "CONCLUIDO"
CLAIMED = "RESGATADO"
EXPIRED = "EXPIRADO"
ABANDONED = "ABANDONADO"

LIVE_STATES = (AVAILABLE, ACCEPTED, IN_PROGRESS)
ACTIVE_STATES = (ACCEPTED, IN_PROGRESS)
HELD_STATES = (ACCEPTED, IN_PROGRESS, COMPLETED)  # §9: Concluido ainda ocupa vaga

# §8: unicas transicoes permitidas.
TRANSITIONS = {
    AVAILABLE: {ACCEPTED, EXPIRED},
    ACCEPTED: {IN_PROGRESS, COMPLETED, EXPIRED, ABANDONED},
    IN_PROGRESS: {COMPLETED, EXPIRED, ABANDONED},
    COMPLETED: {CLAIMED},
    CLAIMED: set(),
    EXPIRED: set(),
    ABANDONED: set(),
}

_REGION_BY_NAME = {name: code for code, name in cfg.REGION_NAMES.items()}
_REGION_BY_LOCAL = {
    local: _REGION_BY_NAME[region.name]
    for region in REGIONS_BY_NAME.values()
    for local in region.locals
    if region.name in _REGION_BY_NAME
}

_state = {"enabled": False}


def set_enabled(value: bool) -> None:
    _state["enabled"] = bool(value)


def is_enabled() -> bool:
    return _state["enabled"]


class ContractError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ContractView:
    instance_id: UUID
    version: int
    definition: ContractDefinition
    state: str
    progress: int
    target: int
    expires_at: datetime
    xp: int
    crowns: int
    materials: int
    material_id: str
    eligible: bool
    requirement: str
    place: str | None


@dataclass(frozen=True, slots=True)
class BoardView:
    region: str
    region_name: str
    eligible: bool
    reason: str | None
    offers: tuple[ContractView, ...]
    held: int


def _utcnow(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def reward_material(definition: ContractDefinition) -> str:
    return definition.material_id or cfg.REGION_REWARD_MATERIAL[definition.region]


def place_name(definition: ContractDefinition) -> str | None:
    """Local where Entrega/Investigacao are confirmed; None for the other types."""
    if definition.contract_type not in cfg.PLACE_BY_TYPE:
        return None
    place = cfg.PLACE_BY_DEFINITION.get(
        definition.definition_id, cfg.PLACE_BY_TYPE[definition.contract_type]
    )
    region = REGIONS_BY_NAME[cfg.REGION_NAMES[definition.region]]
    return region.hub if place == "hub" else region.locals[int(place)]


def _transition(instance: ContractInstance, state: str, now: datetime) -> None:
    if state not in TRANSITIONS[instance.state]:
        raise ContractError("state_changed")
    instance.state = state
    instance.version += 1
    instance.last_validated_at = now


def expire_if_due(instance: ContractInstance, now: datetime) -> bool:
    """§12/§32: normalize a lapsed live instance to EXPIRADO (never after completion)."""
    if instance.state in LIVE_STATES and instance.expires_at <= now:
        _transition(instance, EXPIRED, now)
        return True
    return False


async def _eligibility(session: AsyncSession, character: Character, region: str) -> str | None:
    """None when eligible, otherwise the failing dimension (§14: level, region, Principal)."""
    minimum, _ = cfg.LEVEL_BAND[region]
    if character.level < minimum:
        return "level_low"
    done = await session.scalar(
        select(Quest.id).where(
            Quest.character_id == character.id,
            Quest.quest_id == cfg.GATE_QUEST[region],
            Quest.status == "completed",
        )
    )
    return None if done is not None else "gate_locked"


def _apply_progress(instance: ContractInstance, amount: int, now: datetime) -> None:
    if instance.state == ACCEPTED:
        _transition(instance, IN_PROGRESS, now)
        instance.started_at = now
    instance.progress = min(instance.target, instance.progress + amount)
    if instance.progress >= instance.target:
        _transition(instance, COMPLETED, now)
        instance.completed_at = now
    else:
        instance.version += 1


async def _active(
    session: AsyncSession, character: Character, contract_type: str, region: str | None = None
) -> list[ContractInstance]:
    statement = (
        select(ContractInstance)
        .where(
            ContractInstance.character_id == character.id,
            ContractInstance.state.in_(ACTIVE_STATES),
            ContractInstance.contract_type == contract_type,
        )
        .order_by(ContractInstance.accepted_at, ContractInstance.contract_instance_id)
        .with_for_update()
    )
    if region is not None:
        statement = statement.where(ContractInstance.region_id == region)
    return list((await session.scalars(statement)).all())


async def record_hunt_victory(
    session: AsyncSession,
    character: Character,
    *,
    local_id: str,
    action_started_at: datetime,
    now: datetime | None = None,
) -> bool:
    """Hook of a solo manual Cacada victory (§6.1). One victory advances one Contrato.

    §30/§31: the start of the action decides: a hunt begun before the expiry may
    complete after it; a hunt begun after the expiry never does.
    """
    if not is_enabled():
        return False
    now = _utcnow(now)
    region = _REGION_BY_LOCAL.get(local_id)
    if region is None:
        return False
    for instance in await _active(session, character, "CACA", region):
        if action_started_at >= instance.expires_at:
            expire_if_due(instance, now)
            continue
        if await _eligibility(session, character, instance.region_id) is not None:
            continue  # §33: the persisted state stays; the gate is not bypassed
        _apply_progress(instance, 1, now)
        return True
    return False


async def record_material_gain(
    session: AsyncSession,
    character: Character,
    material_id: str,
    quantity: int,
    source_key: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Hook of a Material received through the game's own sources (§6.2)."""
    if not is_enabled() or quantity <= 0 or source_key.startswith("contract:"):
        return False
    now = _utcnow(now)
    for instance in await _active(session, character, "COLETA"):
        if BY_ID[instance.contract_definition_id].material_id != material_id:
            continue
        if expire_if_due(instance, now):
            continue
        if await _eligibility(session, character, instance.region_id) is not None:
            continue
        _apply_progress(instance, quantity, now)
        return True
    return False


class ContractService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str, road):
        if not server_id or len(server_id) > 64:
            raise ValueError("server_id must contain 1..64 characters")
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    # ------------------------------------------------------------------ helpers

    def _guard(self) -> None:
        if not is_enabled():
            raise ContractError("disabled")

    async def _character(self, session, actor: int, *, lock: bool = False) -> Character:
        self._guard()
        return await require_trading_character(
            session, actor, self.server_id, error=ContractError, lock=lock
        )

    async def _sweep(self, session, character: Character, now: datetime) -> None:
        rows = await session.scalars(
            select(ContractInstance)
            .where(
                ContractInstance.character_id == character.id,
                ContractInstance.state.in_(LIVE_STATES),
                ContractInstance.expires_at <= now,
            )
            .with_for_update()
        )
        for row in rows:
            expire_if_due(row, now)

    async def _lock_instance(self, session, character: Character, instance_id: UUID, now):
        row = await session.scalar(
            select(ContractInstance)
            .where(
                ContractInstance.contract_instance_id == instance_id,
                ContractInstance.character_id == character.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            raise ContractError("not_found")
        expire_if_due(row, now)
        return row

    async def _view(self, session, character: Character, row: ContractInstance) -> ContractView:
        definition = BY_ID[row.contract_definition_id]
        reward = cfg.reward_profile(row.reward_profile)
        reason = await _eligibility(session, character, row.region_id)
        minimum, _ = cfg.LEVEL_BAND[row.region_id]
        return ContractView(
            instance_id=row.contract_instance_id,
            version=row.version,
            definition=definition,
            state=row.state,
            progress=row.progress,
            target=row.target,
            expires_at=row.expires_at,
            xp=reward.xp,
            crowns=reward.crowns,
            materials=reward.materials,
            material_id=reward_material(definition),
            eligible=reason is None,
            requirement=(
                f"Nível {minimum}+ · Missão Principal {cfg.GATE_QUEST[row.region_id]} concluída"
            ),
            place=place_name(definition),
        )

    async def _current_region(self, session, character: Character) -> str:
        world = await session.get(WorldState, character.id)
        region = _REGION_BY_NAME.get(world.region) if world is not None else None
        if region is None:
            raise ContractError("no_region")
        return region

    async def _ensure_board(self, session, character: Character, region: str, now) -> None:
        window = int(now.timestamp() // cfg.BOARD_REFRESH.total_seconds())
        start = datetime.fromtimestamp(window * cfg.BOARD_REFRESH.total_seconds(), UTC)
        refresh_id = f"{region}:{window}"
        rows = [
            {
                "contract_instance_id": uuid4(),
                "character_id": character.id,
                "contract_definition_id": item.definition_id,
                "region_id": region,
                "contract_type": item.contract_type,
                "state": AVAILABLE,
                "expires_at": start + cfg.BOARD_DURATION,
                "progress": 0,
                "target": cfg.TARGET_BY_TYPE[item.contract_type],
                "version": 0,
                "claimed": False,
                "reward_profile": item.reward_profile,
                "source_refresh_id": refresh_id,
                "eligibility_snapshot": {
                    "gate": cfg.GATE_QUEST[region],
                    "level_min": cfg.LEVEL_BAND[region][0],
                    "level": character.level,
                },
                "last_validated_at": now,
            }
            for item in definitions_for(region)[: cfg.BOARD_OFFERS]
            if item.contract_type in cfg.ACTIVE_TYPES
        ]
        await session.execute(
            pg_insert(ContractInstance)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_contract_instance_offer")
        )

    # ------------------------------------------------------------------- reads

    async def board(self, actor: int, *, now: datetime | None = None) -> BoardView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            region = await self._current_region(session, character)
            await self._sweep(session, character, now)
            reason = await _eligibility(session, character, region)
            held = await self._held(session, character)
            offers: tuple[ContractView, ...] = ()
            if reason is None:
                await self._ensure_board(session, character, region, now)
                await session.flush()
                rows = (
                    await session.scalars(
                        select(ContractInstance)
                        .where(
                            ContractInstance.character_id == character.id,
                            ContractInstance.region_id == region,
                            ContractInstance.state == AVAILABLE,
                            ContractInstance.expires_at > now,
                        )
                        .order_by(ContractInstance.contract_definition_id)
                    )
                ).all()
                offers = tuple([await self._view(session, character, row) for row in rows])
            return BoardView(region, cfg.REGION_NAMES[region], reason is None, reason, offers, held)

    async def _held(self, session, character: Character) -> int:
        rows = await session.scalars(
            select(ContractInstance.contract_instance_id).where(
                ContractInstance.character_id == character.id,
                ContractInstance.state.in_(HELD_STATES),
            )
        )
        return len(rows.all())

    async def mine(self, actor: int, *, now: datetime | None = None) -> tuple[ContractView, ...]:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            await self._sweep(session, character, now)
            rows = (
                await session.scalars(
                    select(ContractInstance)
                    .where(
                        ContractInstance.character_id == character.id,
                        ContractInstance.state.in_(HELD_STATES),
                    )
                    .order_by(ContractInstance.accepted_at, ContractInstance.contract_instance_id)
                )
            ).all()
            return tuple([await self._view(session, character, row) for row in rows])

    async def get(
        self, actor: int, instance_id: UUID, *, now: datetime | None = None
    ) -> ContractView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            row = await self._lock_instance(session, character, instance_id, now)
            return await self._view(session, character, row)

    # --------------------------------------------------------------- mutations

    async def accept(
        self, actor: int, instance_id: UUID, version: int, *, now: datetime | None = None
    ) -> ContractView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            row = await self._lock_instance(session, character, instance_id, now)
            self._check(row, AVAILABLE, version)
            if await _eligibility(session, character, row.region_id) is not None:
                raise ContractError("not_eligible")
            if await self._held(session, character) >= cfg.SIMULTANEOUS_CONTRACTS:
                raise ContractError("limit")
            duplicate = await session.scalar(
                select(ContractInstance.contract_instance_id).where(
                    ContractInstance.character_id == character.id,
                    ContractInstance.contract_definition_id == row.contract_definition_id,
                    ContractInstance.state.in_(HELD_STATES),
                )
            )
            if duplicate is not None:
                raise ContractError("already_held")
            _transition(row, ACCEPTED, now)
            row.accepted_at = now
            row.expires_at = now + cfg.ACCEPTED_DURATION
            return await self._view(session, character, row)

    async def act(
        self, actor: int, instance_id: UUID, version: int, *, now: datetime | None = None
    ) -> ContractView:
        """Confirm Entrega at the destination or Investigacao at the point (§6.3/§6.4)."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            row = await self._lock_instance(session, character, instance_id, now)
            if row.state == EXPIRED:
                raise ContractError("expired")
            if row.state not in ACTIVE_STATES:
                raise ContractError("state_changed")
            if row.version != version:
                raise ContractError("stale")
            definition = BY_ID[row.contract_definition_id]
            place = place_name(definition)
            if place is None:
                raise ContractError("no_action")
            if await _eligibility(session, character, row.region_id) is not None:
                raise ContractError("not_eligible")
            world = await session.get(WorldState, character.id)
            if world is None or world.location != place:
                raise ContractError("wrong_place")
            _apply_progress(row, 1, now)
            return await self._view(session, character, row)

    async def abandon(
        self, actor: int, instance_id: UUID, version: int, *, now: datetime | None = None
    ) -> ContractView:
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            row = await self._lock_instance(session, character, instance_id, now)
            if row.state == EXPIRED:
                raise ContractError("expired")
            if row.state not in ACTIVE_STATES:
                raise ContractError("state_changed")
            if row.version != version:
                raise ContractError("stale")
            _transition(row, ABANDONED, now)
            row.abandoned_at = now
            return await self._view(session, character, row)

    async def claim(
        self, actor: int, instance_id: UUID, version: int, *, now: datetime | None = None
    ) -> ContractView:
        """§35: the only payment point, transactional and idempotent."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor, lock=True)
            row = await self._lock_instance(session, character, instance_id, now)
            if row.state != COMPLETED or row.claimed:
                raise ContractError("state_changed")
            if row.version != version:
                raise ContractError("stale")
            source_id = f"contract:{row.contract_instance_id.hex}"
            if (
                await session.scalar(
                    select(RewardEvent.id).where(
                        RewardEvent.character_id == character.id,
                        RewardEvent.source_id == source_id,
                    )
                )
                is not None
            ):
                raise ContractError("state_changed")
            definition = BY_ID[row.contract_definition_id]
            reward = cfg.reward_profile(row.reward_profile)
            material_id = reward_material(definition)
            event = RewardEvent(character_id=character.id, source_id=source_id)
            session.add(event)
            await session.flush()
            character.xp += reward.xp
            character.crowns += reward.crowns
            session.add_all(
                [
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=reward.xp),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=reward.crowns
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=material_id,
                        quantity=reward.materials,
                        payload={"material_id": material_id, "bound": True},
                    ),
                ]
            )
            await self.road.deliver_material(
                session,
                character,
                material_id,
                reward.materials,
                f"{source_id}:material",
                bound=True,
            )
            await consolidate_character_level(session, character)
            _transition(row, CLAIMED, now)
            row.claimed = True
            row.claimed_at = now
            return await self._view(session, character, row)

    @staticmethod
    def _check(row: ContractInstance, state: str, version: int) -> None:
        if row.state == EXPIRED:
            raise ContractError("expired")
        if row.state != state:
            raise ContractError("state_changed")
        if row.version != version:
            raise ContractError("stale")

    async def run_maintenance(self, *, now: datetime | None = None, limit: int = 500) -> int:
        """Normalize lapsed instances proactively; lazy validation stays authoritative."""
        now = _utcnow(now)
        async with self.sessions.begin() as session:
            rows = (
                await session.scalars(
                    select(ContractInstance)
                    .where(
                        ContractInstance.state.in_(LIVE_STATES),
                        ContractInstance.expires_at <= now,
                    )
                    .order_by(ContractInstance.expires_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                expire_if_due(row, now)
            return len(rows)
