"""Caso de uso Explorar das Terras do Ocaso v1.0.18 (secao 33.2, L10-L13).

Individual também em Grupo (L12): só o personagem que clica descobre e recebe XP.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.action_throttle import (
    ACTION_EXPLORE,
    acquire_action_slot,
    release_action_slot,
)
from asterion.application.campaign_objectives import lock_campaign_roster
from asterion.application.p1 import REFUGE, REGION
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.domain.tdo_explore import (
    CAMARA_LOCATION_ID,
    EXPLORE_TARGETS,
    ExploreTarget,
    discovery_xp,
    pick_explore_target,
)
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    GameActivity,
    LocationDiscovery,
    RewardComponent,
    RewardEvent,
    WorldState,
)

EXPLORE_ACTION = ACTION_EXPLORE  # L7: nome técnico da ação
EXPLORE_REWARD_SOURCE = "tdo.explore.discovery."  # + location_id
CAMARA_CODEX_ENTRY = "codex.location.camara_do_poente"  # §16, L9
_LABEL_TO_TARGET = {t.label: t for t in EXPLORE_TARGETS}


@dataclass(frozen=True)
class ExploreResult:
    # discovered | unavailable | cooldown | busy | not_in_refuge | foreground | no_character
    status: str
    location_id: str | None = None
    label: str | None = None
    xp: int = 0
    retry_after_seconds: float = 0.0
    camara_codex: bool = False


async def reconcile_current_location(
    session: AsyncSession, character_id, world: WorldState | None
) -> str | None:
    """L11: personagem parado em Local-alvo não descoberto fica lá e o Local passa a
    contar como descoberto, sem XP. Idempotente. Devolve o location_id gravado, se algum.
    """
    if world is None or world.region != REGION:
        return None
    target = _LABEL_TO_TARGET.get(world.location)
    if target is None:
        return None
    found = await session.scalar(
        select(LocationDiscovery.id).where(
            LocationDiscovery.character_id == character_id,
            LocationDiscovery.location_id == target.location_id,
        )
    )
    if found is not None:
        return None
    session.add(LocationDiscovery(character_id=character_id, location_id=target.location_id))
    if target.location_id == CAMARA_LOCATION_ID:
        await _ensure_camara_codex(session, character_id)
    await session.flush()
    return target.location_id


async def discover_all_locations(session: AsyncSession, character_id) -> None:
    """Decisão do autor: todos os Locais da Região nascem descobertos e clicáveis.

    Grava a descoberta de Charneca, Bosque, Ruínas e Câmara do Poente (e o registro
    da Câmara no Códice, como a descoberta por Explorar faz), sem XP. Idempotente.
    """
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for target in EXPLORE_TARGETS:
        await session.execute(
            pg_insert(LocationDiscovery)
            .values(character_id=character_id, location_id=target.location_id)
            .on_conflict_do_nothing()
        )
    await session.execute(
        pg_insert(CodexEntry)
        .values(character_id=character_id, entry_id=CAMARA_CODEX_ENTRY)
        .on_conflict_do_nothing()
    )


async def _ensure_camara_codex(session: AsyncSession, character_id) -> None:
    has = await session.scalar(
        select(CodexEntry.id).where(
            CodexEntry.character_id == character_id,
            CodexEntry.entry_id == CAMARA_CODEX_ENTRY,
        )
    )
    if has is None:
        session.add(CodexEntry(character_id=character_id, entry_id=CAMARA_CODEX_ENTRY))


async def _discovered_ids(session: AsyncSession, character_id) -> set[str]:
    return set(
        (
            await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character_id
                )
            )
        ).all()
    )


class TdoExploreService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        clock: Callable[[], datetime] | None = None,
        seed_factory: Callable[[], str] | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.clock = clock or (lambda: datetime.now(UTC))
        self.seed_factory = seed_factory or (lambda: uuid4().hex)

    async def remaining(self, actor: int) -> tuple[ExploreTarget, ...] | None:
        """Leitura sem escrita: alvos que faltam (L10/L11 já contados). None sem personagem."""
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character is None:
                return None
            known = await _discovered_ids(session, character.id)
            world = await session.get(WorldState, character.id)
            if world is not None and world.region == REGION:
                here = _LABEL_TO_TARGET.get(world.location)
                if here is not None:
                    known.add(here.location_id)
            return tuple(t for t in EXPLORE_TARGETS if t.location_id not in known)

    async def explore(self, actor: int) -> ExploreResult:
        now = self.clock()
        async with self.sessions.begin() as session:
            seed = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if seed is None:
                return ExploreResult("no_character")
            await lock_campaign_roster(session, seed.id)
            character = await session.scalar(
                select(Character).where(Character.id == seed.id).with_for_update()
            )
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            # L11 antes de tudo: persiste mesmo se o clique for recusado depois.
            await reconcile_current_location(session, character.id, world)

            if world is None or world.region != REGION or world.location != REFUGE:
                return ExploreResult("not_in_refuge")
            active = await session.scalar(
                select(GameActivity.id)
                .where(GameActivity.character_id == character.id, GameActivity.status == "active")
                .limit(1)
            )
            if active is not None:
                return ExploreResult("foreground")

            known = await _discovered_ids(session, character.id)
            # Sem alvo: indisponível, sem consumir o anti-spam.
            target = pick_explore_target(f"{character.id}:{self.seed_factory()}", known)
            if target is None:
                return ExploreResult("unavailable")

            decision = await acquire_action_slot(session, character.id, EXPLORE_ACTION, now)
            if not decision.allowed:
                return ExploreResult(
                    "busy" if decision.reason == "resolving" else "cooldown",
                    retry_after_seconds=decision.retry_after.total_seconds(),
                )

            session.add(
                LocationDiscovery(character_id=character.id, location_id=target.location_id)
            )
            xp = discovery_xp(target.reference_level, character.level, level_xp)
            source = EXPLORE_REWARD_SOURCE + target.location_id
            event = await session.scalar(
                select(RewardEvent)
                .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
                .with_for_update()
            )
            paid = 0
            if event is None:
                event = RewardEvent(character_id=character.id, source_id=source)
                session.add(event)
                await session.flush()
                session.add(
                    RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=xp)
                )
                character.xp += xp
                paid = xp
                await consolidate_character_level(session, character)

            codex = False
            if target.location_id == CAMARA_LOCATION_ID:
                await _ensure_camara_codex(session, character.id)
                codex = True

            await session.flush()
            await release_action_slot(session, character.id)
            return ExploreResult(
                "discovered",
                location_id=target.location_id,
                label=target.label,
                xp=paid,
                camara_codex=codex,
            )
