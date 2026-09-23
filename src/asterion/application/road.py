"""Application services for the post-P1 Road hunt and exploration loop."""
# ruff: noqa: E501

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.progression import consolidate_level, level_xp
from asterion.domain.combat import act
from asterion.domain.road import (
    EXPLORE_UNLOCK,
    HUNT_UNLOCK,
    ROUND_FAMILIARITY,
    RULESET,
    create_road_combat,
    creature_for,
    crowns,
    enemy_xp,
    equipment_rarity,
    material_for,
    materialize_equipment,
    rune_potency,
    select_charneca_creature,
    select_charneca_exploration_result,
    select_creature,
    select_exploration_result,
    select_variant,
    weighted_choice,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    BlockedDelivery,
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    MaterialStack,
    PendingItem,
    Quest,
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)

ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
CHARNECA = "Charneca da Fuligem"
REGION = "Terras do Ocaso"
HUNT_CONTENT = "road_manual_hunt"
EXPLORE_CONTENT = "road_exploration"
CHARNECA_HUNT_UNLOCK = "hunt_manual.charneca_da_fuligem"
CHARNECA_EXPLORE_UNLOCK = "explore.charneca_da_fuligem"
CHARNECA_ROUND_FAMILIARITY = "hunt_round.charneca_da_fuligem"
CHARNECA_BRAZIER = "tdo.brazier.vento_morto"
REFUGE_BRAZIER = "tdo.brazier.refugio_do_ocaso"

VARIANT_LABELS = {
    "furious": "Furioso",
    "agile": "Ágil",
    "resistant": "Resistente",
    "hemorrhagic": "Hemorrágico",
    "venomous": "Venenoso",
}
ROAD_ACTIVITY_GRACE = timedelta(minutes=30)
RASTROS_CONTEXT_TEXT = {
    "dog_cinereo": "Pegadas de quatro patas cortam a fuligem em passadas rápidas. Marcas de garras indicam que a criatura percorre a Estrada com frequência.",
    "corvo_fuligem": "Pequenas marcas interrompem a cinza junto a riscos estreitos no chão. Algo pousa e parte repetidamente deste trecho da Estrada.",
    "peregrino_calcinado": "Passadas irregulares seguem por alguns metros antes de desaparecer entre pedra e fuligem. O mesmo padrão já foi associado aos Peregrinos da região.",
}
MATERIAL_LABELS = {
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
}
BESTIARY_STAGE_LABELS = {
    "observed": "Observado",
    "known": "Conhecido",
    "studied": "Estudado",
    "dominated": "Dominado",
}


@dataclass(frozen=True)
class RoadView:
    kind: str
    character_id: UUID
    location: str
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_id: UUID | None = None
    combat: object | None = None
    attempt_id: UUID | None = None
    result_id: str | None = None
    result_text: str | None = None
    state_version: int = 0
    vigor: int = 0
    max_vigor: int = 100
    name: str = ""
    hp: Decimal = Decimal(0)
    max_hp: Decimal = Decimal(0)
    reward_lines: tuple[str, ...] = ()
    familiar: bool = False
    retry_available: bool = True
    explore_available: bool = True
    creature: str | None = None
    variant: str | None = None


class RoadService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def resume(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            if not await self._p1_completed(s, c.id):
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                return None
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if world is None or world.location not in {ROAD, REFUGE}:
                return None
            return RoadView(
                "road" if world.location == ROAD else "refuge",
                c.id,
                world.location,
                vigor=c.vigor,
                max_vigor=c.max_vigor,
            )

    async def travel(self, actor: int, destination: str) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if (
                c is None
                or world is None
                or destination not in {ROAD, REFUGE}
                or not await self._p1_completed(s, c.id)
                or world.location not in {ROAD, REFUGE}
            ):
                return None
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id not in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    return None
                if self._expired(active):
                    return await self._expire_activity(s, c, active)
                return await self._road_blocking_view(s, c)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            source_brazier = (
                "tdo.brazier.estrada"
                if world.location == ROAD
                else "tdo.brazier.refugio_do_ocaso"
            )
            target_brazier = (
                "tdo.brazier.estrada" if destination == ROAD else "tdo.brazier.refugio_do_ocaso"
            )
            if not await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id, Brazier.brazier_id == source_brazier
                )
            ) or not await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id, Brazier.brazier_id == target_brazier
                )
            ):
                return None
            world.location = destination
            return await self._view_for_world(s, c, world)

    async def start_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None or world.location != ROAD or not await self._p1_completed(s, c.id):
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            if not await s.scalar(
                select(Unlock).where(Unlock.character_id == c.id, Unlock.unlock_id == HUNT_UNLOCK)
            ):
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                if active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    return await self._combat_view(s, c, active)
                return await self._view_for_world(s, c, world)
            seed = uuid4().hex
            creature = select_creature(seed, c.level)
            level = min(c.level, creature.max_level)
            variant = select_variant(seed, creature)
            combat_id = uuid4()
            combat = create_road_combat(
                combat_id, c.name, c.character_class, c.race, c.hp, creature, level, variant,
                player_level=c.level,
            )
            activity, encounter, record = await CombatRepository(s).create(c, HUNT_CONTENT, combat)
            s.add(
                HuntContext(
                    game_activity_id=activity.id,
                    character_id=c.id,
                    creature_id=creature.creature_id,
                    category=creature.category,
                    enemy_level=level,
                    variant=variant,
                    seed=seed,
                    loot_profile="hunt",
                )
            )
            await self._bestiary(
                s,
                c.id,
                creature.creature_id,
                variant=variant,
                elite=creature.category == "elite",
                grant_observation_xp=True,
                observation_level=level,
                observation_category=creature.category,
            )
            await s.flush()
            return await self._combat_view(s, c, activity)

    async def prepare_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None:
                return None
            if not await self._p1_completed(s, c.id):
                return None
            if world is None or world.location != ROAD:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            return RoadView("hunt_prepare", c.id, ROAD, vigor=c.vigor, max_vigor=c.max_vigor,
                            name=c.name, hp=c.hp, max_hp=c.max_hp)

    async def action(
        self, actor: int, activity_id: UUID, version: int, action: str
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None:
                return None
            if not await self._p1_completed(s, c.id):
                return None
            activity = await s.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == c.id,
                    GameActivity.content_id.in_((HUNT_CONTENT, EXPLORE_CONTENT)),
                )
                .with_for_update()
            )
            if activity is None:
                return None
            if activity.status != "active":
                return await self._result_view_for_activity(s, c, activity, world)
            if self._expired(activity):
                return await self._expire_activity(s, c, activity)
            if activity.state_version != version:
                return await self._combat_view(s, c, activity)
            encounter, record = await CombatRepository(s).combat(activity)
            combat = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
            updated = act(combat, action)
            if updated.version == combat.version:
                return await self._combat_view(s, c, activity)
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            context = await s.scalar(select(HuntContext).where(HuntContext.game_activity_id == activity.id))
            bestiary_evidence_ids = set()
            if context is not None:
                bestiary_evidence_ids = await self._record_bestiary_combat_events(
                    s, c.id, context, updated
                )
            if updated.result == "victory":
                activity.status = "completed"
                if activity.content_id == HUNT_CONTENT:
                    await self._settle_hunt(
                        s, c, activity, encounter.id, bestiary_evidence_ids
                    )
                    return await self._hunt_victory_view(s, c, activity)
                else:
                    attempt = await s.scalar(
                        select(ExplorationAttempt)
                        .where(ExplorationAttempt.activity_id == activity.id)
                        .with_for_update()
                    )
                    if attempt is not None:
                        attempt.status = "completed"
                        attempt.state_version += 1
                        await self._settle_exploration(s, c, attempt)
                    return (
                        await self._attempt_view(s, c, attempt, ROAD)
                        if attempt is not None
                        else await self._combat_view(s, c, activity)
                    )
            elif updated.result == "defeat":
                activity.status = "failed"
                c.hp = c.max_hp
                if activity.content_id == EXPLORE_CONTENT:
                    attempt = await s.scalar(
                        select(ExplorationAttempt)
                        .where(ExplorationAttempt.activity_id == activity.id)
                        .with_for_update()
                    )
                    if attempt is not None:
                        attempt.status = "failed"
                        attempt.completed_at = datetime.now(UTC)
                        attempt.progress = {
                            **(attempt.progress or {}),
                            "receipt_text": "A exploração foi interrompida. Recuperado na Estrada.",
                            "settled": True,
                        }
                        consolidate_level(c)
                        return await self._attempt_view(s, c, attempt, ROAD)
                consolidate_level(c)
                return RoadView(
                    "hunt_defeat",
                    c.id,
                    ROAD,
                    activity_id=activity.id,
                    vigor=c.vigor,
                    max_vigor=c.max_vigor,
                )
            return await self._combat_view(s, c, activity)

    async def retry_hunt(self, actor: int) -> RoadView | None:
        return await self.prepare_hunt(actor)

    async def retry_blocked_deliveries(self, actor: int) -> bool:
        """Retry durable delivery holds without rerolling or duplicating loot."""
        async with self.sessions.begin() as s:
            c = await s.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is None:
                return False
            await self._retry_blocked_deliveries(s, c)
            return not c.delivery_blocked

    async def acknowledge_defeat(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            context = await s.scalar(
                select(HuntContext)
                .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
                .where(HuntContext.character_id == c.id, GameActivity.status == "failed")
                .order_by(GameActivity.id.desc()).limit(1).with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._view_for_world(s, c, world) if world else None

    async def acknowledge_result(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            attempt = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.status.in_(("completed", "failed")),
                    ExplorationAttempt.result_acknowledged.is_(False),
                )
                .order_by(ExplorationAttempt.completed_at.desc(), ExplorationAttempt.id.desc())
                .limit(1)
                .with_for_update()
            )
            if attempt is not None:
                attempt.result_acknowledged = True
                world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
                return await self._view_for_world(s, c, world) if world else None
            context = await s.scalar(
                select(HuntContext)
                .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
                .where(HuntContext.character_id == c.id, GameActivity.content_id == HUNT_CONTENT)
                .order_by(GameActivity.id.desc()).limit(1).with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._view_for_world(s, c, world) if world else None

    async def explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if (
                c is None
                or world is None
                or world.location != ROAD
                or not await self._p1_completed(s, c.id)
            ):
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            if not await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == EXPLORE_UNLOCK
                )
            ):
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id == HUNT_CONTENT:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    return await self._combat_view(s, c, active)
                if active.content_id != EXPLORE_CONTENT:
                    return None
                if self._expired(active):
                    return await self._expire_activity(s, c, active)
                attempt = await s.scalar(
                    select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                )
                return await self._combat_view(s, c, active) if attempt and attempt.status == "active" else await self._attempt_view(s, c, attempt, ROAD)
            now = datetime.now(UTC)
            recent = await s.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                )
            )
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(ExplorationAttempt.character_id == c.id, ExplorationAttempt.local_id == ROAD)
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            if recent >= 6:
                sixth = await s.scalar(select(ExplorationAttempt).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                ).order_by(ExplorationAttempt.created_at.desc()).offset(5).limit(1))
                return self._explore_limit_view(c, recent, last, now, sixth)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now)
            seed = uuid4().hex
            recent_rows = (await s.scalars(
                select(ExplorationAttempt.result_id)
                .where(ExplorationAttempt.character_id == c.id, ExplorationAttempt.local_id == ROAD)
                .order_by(ExplorationAttempt.created_at.desc()).limit(3)
            )).all()
            resolved_unique = tuple(
                (await s.scalars(select(ExplorationAttempt.result_id).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                    ExplorationAttempt.status == "completed",
                    ExplorationAttempt.result_id.in_((
                        "explore.tdo.estrada.marco_viajantes",
                        "explore.tdo.estrada.luzes",
                    )),
                ))).all()
            )
            result = _explore_result(
                seed, c.level, tuple(str(item).rsplit(".", 1)[-1] for item in recent_rows),
                tuple(str(item).rsplit(".", 1)[-1] for item in resolved_unique),
            )
            category, result_id, result_text = result
            attempt = ExplorationAttempt(
                character_id=c.id,
                local_id=ROAD,
                ruleset_version=RULESET,
                seed=seed,
                category=category,
                result_id=result_id,
                status="active" if category == "combat" else "completed",
                state_version=0 if category == "combat" else 1,
                progress={"result_text": result_text},
            )
            s.add(attempt)
            await s.flush()
            if category == "combat":
                creature_id = result_id.rsplit(".", 1)[-1]
                creature = creature_for(creature_id)
                level = min(c.level, creature.max_level)
                variant = select_variant(seed, creature)
                combat = create_road_combat(
                    uuid4(), c.name, c.character_class, c.race, c.hp, creature, level, variant,
                    player_level=c.level,
                )
                activity, encounter, _ = await CombatRepository(s).create(
                    c, EXPLORE_CONTENT, combat
                )
                attempt.activity_id = activity.id
                attempt.encounter_id = encounter.id
                s.add(
                    HuntContext(
                        game_activity_id=activity.id,
                        character_id=c.id,
                        creature_id=creature.creature_id,
                        category=creature.category,
                        enemy_level=level,
                        variant=variant,
                        seed=seed,
                        loot_profile="exploration_combat",
                    )
                )
                await self._bestiary(
                    s, c.id, creature.creature_id, variant=variant,
                    elite=creature.category == "elite",
                    grant_observation_xp=True,
                    observation_level=level,
                    observation_category=creature.category,
                )
                await s.flush()
                return await self._combat_view(s, c, activity)
            await self._settle_exploration(s, c, attempt)
            return await self._attempt_view(s, c, attempt, ROAD)

    async def prepare_explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None or world.location != ROAD:
                return None
            if not await self._p1_completed(s, c.id):
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(select(GameActivity).where(
                GameActivity.character_id == c.id, GameActivity.status == "active"
            ))
            if active is not None:
                if active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    if active.content_id == HUNT_CONTENT:
                        return await self._combat_view(s, c, active)
                    attempt = await s.scalar(
                        select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                    )
                    return await self._combat_view(s, c, active) if attempt and attempt.status == "active" else await self._attempt_view(s, c, attempt, ROAD)
                return None
            now = datetime.now(UTC)
            recent = await s.scalar(select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == ROAD,
                ExplorationAttempt.created_at >= now - timedelta(minutes=60),
            )) or 0
            last = await s.scalar(select(ExplorationAttempt).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == ROAD,
            ).order_by(ExplorationAttempt.created_at.desc()).limit(1))
            if recent >= 6:
                sixth = await s.scalar(select(ExplorationAttempt).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                ).order_by(ExplorationAttempt.created_at.desc()).offset(5).limit(1))
                return self._explore_limit_view(c, recent, last, now, sixth)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now)
            return RoadView("explore_prepare", c.id, ROAD, vigor=c.vigor, max_vigor=c.max_vigor, name=c.name, hp=c.hp, max_hp=c.max_hp)

    async def _settle_hunt(
        self, s, c, activity, encounter_id, bestiary_evidence_ids=frozenset()
    ):
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id).with_for_update()
        )
        if context is None:
            return 0
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id, RewardEvent.source_id == f"activity:{activity.id}"
            )
            .with_for_update()
        )
        if event is not None:
            return 0
        event = RewardEvent(character_id=c.id, source_id=f"activity:{activity.id}")
        s.add(event)
        await s.flush()
        enough = c.vigor >= 2
        factor = Decimal(1) if enough else Decimal("0.25")
        xp = enemy_xp(context.enemy_level, context.category, factor, player_level=c.level)
        c.xp += xp
        crowns_award = crowns(context.enemy_level, context.category) if enough else 0
        c.crowns += crowns_award
        components = [("xp", None, xp, {})]
        if crowns_award:
            components.append(("crowns", None, crowns_award, {}))
        if enough:
            c.vigor -= 2
            material_count = (
                0
                if context.category == "common"
                and _draw_int(context.seed, "material-roll", 100) >= 80
                else 1
                if context.category == "common"
                else 3 + _draw_int(context.seed, "elite-materials", 2)
            )
            for ordinal in range(material_count):
                material = material_for(context.creature_id, f"{context.seed}:material:{ordinal}")
                components.append(("material", material, 1, {"material_id": material, "bound": False}))
                await self._deliver_material(
                    s, c, material, 1, f"activity:{activity.id}:material:{ordinal}"
                )
            if context.category == "elite":
                components.append(("catalyst", "material.tdo.catalisador_elite_i", 1, {}))
                if _draw_int(context.seed, "fragment", 100) < 40:
                    components.append(("fragment", "material.tdo.fragmento_aprimoramento_i", 1, {}))
            await self._materialize_optional_loot(s, c, context, components)
            for kind, item_id, quantity, *_ in components:
                if kind in {"catalyst", "fragment"}:
                    await self._deliver_material(
                        s, c, item_id, quantity, f"activity:{activity.id}:{kind}"
                    )
        bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
        if bestiary_update is None and bestiary_evidence_ids:
            entry = await s.scalar(
                select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id,
                    BestiaryEntry.creature_id == context.creature_id,
                )
            )
            if entry is not None:
                bestiary_update = {
                    "creature_id": context.creature_id,
                    "creature_name": creature_for(context.creature_id).name,
                    "stage": entry.stage,
                    "stage_label": BESTIARY_STAGE_LABELS[entry.stage],
                }
        if bestiary_update is not None:
            components.append(("bestiary", context.creature_id, 1, bestiary_update))
        for component in components:
            kind, item_id, quantity = component[:3]
            payload = component[3] if len(component) > 3 else {}
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        await self._ensure(s, Unlock, character_id=c.id, unlock_id=ROUND_FAMILIARITY)
        consolidate_level(c)
        return xp

    async def _materialize_optional_loot(self, s, c, context, components):
        equipment_chance = 35 if context.category == "elite" else 8
        rune_chance = 50 if context.category == "elite" else 5
        if _draw_int(context.seed, "equipment", 100) < equipment_chance:
            rarity = equipment_rarity(
                context.seed, context.category,
                c.elite_equipment_pity if context.category == "elite" else 0,
                c.elite_legendary_pity if context.category == "elite" else 0,
            )
            if context.category == "elite":
                c.elite_equipment_pity += 1
                if rarity in {"Épico", "Lendário", "Mítico"}:
                    c.elite_equipment_pity = 0
                c.elite_legendary_pity += 1
                if rarity in {"Lendário", "Mítico"}:
                    c.elite_legendary_pity = 0
            item = materialize_equipment(context.seed, rarity, context.enemy_level)
            if await self._inventory_slots(s, c.id) < 60:
                s.add(
                    EquipmentItem(
                        character_id=c.id,
                        source_key=f"activity:{context.game_activity_id}:equipment",
                        item_name=item["item_name"],
                        rarity=item["rarity"],
                        slot=item["slot"],
                        item_level=context.enemy_level,
                        bound=False,
                        payload=item,
                    )
                )
            else:
                await self._pending(
                    s, c.id, f"activity:{context.game_activity_id}:equipment", "equipment", item
                )
            components.append(("equipment", item["item_name"], 1, dict(item)))
        if _draw_int(context.seed, "rune", 1000) < rune_chance:
            rarity = _rarity(context.seed, context.category, "rune")
            families = (
                "Brasa",
                "Pedra",
                "Caminhante",
                "Fresta",
                "Presságio",
                "Persistência",
                "Desvio",
                "Guarda",
            )
            family = families[_draw_int(context.seed, "rune.family", len(families))]
            stack = await s.scalar(
                select(RuneStack)
                .where(
                    RuneStack.character_id == c.id,
                    RuneStack.family == family,
                    RuneStack.rarity == rarity,
                    RuneStack.grade == 1,
                    RuneStack.bound.is_(False),
                )
                .with_for_update()
            )
            if stack is None:
                rune_payload = {
                    "family": family,
                    "rarity": rarity,
                    "grade": 1,
                    "potency": rune_potency(family, rarity),
                    "bound": False,
                }
                if await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        RuneStack(
                            character_id=c.id,
                            family=family,
                            rarity=rarity,
                            grade=1,
                            potency=rune_payload["potency"],
                            quantity=1,
                            bound=False,
                        )
                    )
                else:
                    await self._pending(
                        s,
                        c.id,
                        f"activity:{context.game_activity_id}:rune",
                        "rune",
                        rune_payload,
                    )
            else:
                stack.quantity += 1
                rune_payload = {
                    "family": family,
                    "rarity": rarity,
                    "grade": stack.grade,
                    "potency": stack.potency,
                    "bound": stack.bound,
                }
            components.append(("rune", family, 1, rune_payload))

    async def _settle_exploration(self, s, c, attempt):
        if (attempt.progress or {}).get("settled"):
            return
        base_text = (attempt.progress or {}).get("result_text", "")
        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == attempt.activity_id)
            )
            if context is not None:
                source_id = f"explore:{attempt.id}"
                event = await s.scalar(select(RewardEvent).where(
                    RewardEvent.character_id == c.id,
                    RewardEvent.source_id == source_id,
                ).with_for_update())
                if event is not None:
                    return
                event = RewardEvent(character_id=c.id, source_id=source_id)
                s.add(event)
                await s.flush()
                factor = Decimal(1) if c.vigor >= 4 else Decimal("0.25")
                xp = enemy_xp(
                    context.enemy_level,
                    context.category,
                    factor,
                    player_level=c.level,
                )
                c.xp += xp
                components = [("xp", None, xp, {})]
                receipt_lines = [base_text, f"✨ XP · {xp}"]
                if c.vigor >= 4:
                    c.vigor -= 4
                    # Exploration combat pays the normal repeatable currency
                    # coefficient, independently of the full Hunt reward.
                    crowns_award = int(
                        ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10)
                        .quantize(Decimal(1), rounding=ROUND_HALF_EVEN) * 10
                    )
                    c.crowns += crowns_award
                    components.append(("crowns", None, crowns_award, {}))
                    receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                    pool = (("material.tdo.ferro_de_fuligem", 30), ("material.tdo.couro_escoriado", 30), ("material.tdo.erva_cinzenta", 20), ("material.tdo.residuo_ocaso", 20))
                    units = 1 + (1 if _draw_int(attempt.seed, "exploration-material-extra", 100) < 20 else 0)
                    for ordinal in range(units):
                        material = weighted_choice(
                            f"{attempt.seed}:exploration-material:{ordinal}", pool
                        )
                        components.append(("material", material, 1, {"material_id": material}))
                        receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                        await self._deliver_material(s, c, material, 1, f"explore:{attempt.id}:material:{ordinal}")
                bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
                if bestiary_update is not None:
                    components.append(("bestiary", context.creature_id, 1, bestiary_update))
                    receipt_lines.append(
                        f"📖 Bestiário · {bestiary_update['creature_name']} · "
                        f"{bestiary_update['stage_label']}"
                    )
                for kind, item_id, quantity, payload in components:
                    s.add(RewardComponent(
                        reward_event_id=event.id,
                        kind=kind,
                        item_id=item_id,
                        quantity=quantity,
                        payload=payload,
                    ))
                attempt.progress = {
                    **(attempt.progress or {}),
                    "receipt_text": "\n\n".join(receipt_lines),
                    "settled": True,
                }
                attempt.completed_at = attempt.completed_at or datetime.now(UTC)
                consolidate_level(c)
            return
        if attempt.category == "resource":
            receipt_lines = [base_text]
            if c.vigor >= 4:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding="ROUND_HALF_EVEN"
                    )
                    * 10
                )
                c.crowns += crowns_award
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                material_ids = {
                    "ferro": "material.tdo.ferro_de_fuligem",
                    "couro": "material.tdo.couro_escoriado",
                    "erva": "material.tdo.erva_cinzenta",
                    "residuo": "material.tdo.residuo_ocaso",
                }
                material = material_ids.get(attempt.result_id.rsplit(".", 1)[-1])
                if material:
                    receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                    await self._deliver_material(s, c, material, 1, f"explore:{attempt.id}:resource")
            attempt.progress = {
                **(attempt.progress or {}),
                "receipt_text": "\n\n".join(receipt_lines),
                "settled": True,
            }
            attempt.completed_at = attempt.completed_at or datetime.now(UTC)
            consolidate_level(c)
            return
        receipt_lines = [base_text]
        if attempt.result_id == "explore.tdo.estrada.marco_viajantes":
            c.xp += 456
            entry_new = await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            fragment_new = await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.memoria_viajantes",
            )
            receipt_lines.append("✨ XP · 456")
            if entry_new or fragment_new:
                receipt_lines.append("📖 Códice/Trecho novo")
        elif attempt.result_id == "explore.tdo.estrada.luzes":
            c.xp += 143
            entry_new = await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            fragment_new = await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.luzes_na_estrada",
            )
            receipt_lines.append("✨ XP · 143")
            if entry_new or fragment_new:
                receipt_lines.append("📖 Códice/Trecho novo")
        elif attempt.result_id == "explore.tdo.estrada.rastros_cinereos":
            identifiable = []
            without_habitat = []
            for creature in ("dog_cinereo", "corvo_fuligem", "peregrino_calcinado"):
                profile = creature_for(creature)
                entry = await s.scalar(select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == creature
                ))
                habitat = await s.scalar(select(BestiaryEvidence).where(
                    BestiaryEvidence.character_id == c.id,
                    BestiaryEvidence.creature_id == creature,
                    BestiaryEvidence.evidence_id == "habitat:estrada",
                ))
                if c.level >= profile.unlock_level and entry is not None:
                    identifiable.append(creature)
                    if habitat is None:
                        without_habitat.append(creature)
            eligible = without_habitat or identifiable
            if eligible:
                chosen = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(select(BestiaryEntry).where(
                    BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == chosen
                ).with_for_update())
                if entry is not None:
                    added_habitat = False
                    if chosen in without_habitat:
                        added_habitat = await self._add_bestiary_evidence(
                            s, entry, c.id, chosen, "habitat:estrada", "habitat", 3
                        )
                    context_text = RASTROS_CONTEXT_TEXT[chosen]
                    attempt.progress = {
                        **(attempt.progress or {}),
                        "context_creature_id": chosen,
                        "context_materialized": True,
                        "result_text": f"{base_text}\n\n{context_text}",
                    }
                    receipt_lines[0] = attempt.progress["result_text"]
                    if added_habitat:
                        receipt_lines.append(
                            f"📖 Bestiário · {creature_for(chosen).name} · Habitat novo"
                        )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(receipt_lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        consolidate_level(c)

    async def _bestiary(
        self,
        s,
        character_id,
        creature_id,
        *,
        victory=False,
        evidence_id=None,
        variant=None,
        elite=False,
        grant_observation_xp=False,
        observation_level=None,
        observation_category="common",
    ):
        before_evidence_ids = set(
            (
                await s.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == creature_id,
                    )
                )
            ).all()
        )
        first_observation_new = "first_observation" not in before_evidence_ids
        entry = await s.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == creature_id
            )
            .with_for_update()
        )
        if entry is None:
            entry = BestiaryEntry(
                character_id=character_id, creature_id=creature_id, bkp=0, wins=1 if victory else 0
            )
            s.add(entry)
            previous_stage = None
        elif victory:
            previous_stage = entry.stage
            entry.wins += 1
        else:
            previous_stage = entry.stage
        for evidence, category in (
            ("first_observation", "observation"),
            ("first_combat", "combat"),
        ):
            exists = await s.scalar(select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
                BestiaryEvidence.evidence_id == evidence,
            ))
            if exists is None:
                s.add(BestiaryEvidence(character_id=character_id, creature_id=creature_id, evidence_id=evidence, category=category))
                entry.bkp += 4 if evidence == "first_observation" else 3
        if first_observation_new and grant_observation_xp and observation_level is not None:
            await self._grant_observation_xp(s, character_id, creature_id, observation_level)
        if evidence_id:
            await self._add_bestiary_evidence(s, entry, character_id, creature_id, evidence_id, evidence_id)
        if variant:
            await self._add_bestiary_evidence(s, entry, character_id, creature_id, f"variant:{variant}", "variant", 8)
            if victory:
                await self._add_bestiary_evidence(
                    s, entry, character_id, creature_id,
                    f"variant_victory:{variant}", "variant_victory", 6,
                )
        if elite:
            await self._add_bestiary_evidence(s, entry, character_id, creature_id, "elite", "elite", 8)
            if victory:
                await self._add_bestiary_evidence(
                    s, entry, character_id, creature_id, "elite_victory", "elite_victory", 6,
                )
        if victory:
            first_victory = await s.scalar(select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
                BestiaryEvidence.evidence_id == "first_victory",
            ))
            if first_victory is None:
                s.add(BestiaryEvidence(character_id=character_id, creature_id=creature_id, evidence_id="first_victory", category="victory"))
                entry.bkp += 5
                if creature_id == "alfa_cinereo":
                    await self._grant_alpha_victory_xp(s, character_id, creature_id)
            else:
                entry.bkp += _repeat_bkp(entry.wins, elite)
        categories = {
            row
            for row in (await s.scalars(select(BestiaryEvidence.category).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
            ))).all()
        }
        evidence_ids = {
            row
            for row in (await s.scalars(select(BestiaryEvidence.evidence_id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
            ))).all()
        }
        if elite:
            if creature_id == "alfa_cinereo":
                special = {"first_victory", "mechanic:bleed", "mechanic:prepared_leap"}.issubset(evidence_ids)
            else:
                special = bool({"elite_victory", "mechanic"} & categories)
            entry.stage = (
                "dominated"
                if entry.bkp >= 45 and entry.wins >= 1 and special
                else "studied"
                if entry.bkp >= 25
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        else:
            entry.stage = (
                "dominated"
                if entry.bkp >= 60 and len(categories) >= 3
                else "studied"
                if entry.bkp >= 30 and len(categories) >= 2
                else "known"
                if entry.bkp >= 10
                else "observed"
            )
        new_evidence_ids = evidence_ids - before_evidence_ids
        if (previous_stage is not None and previous_stage != entry.stage) or (
            victory and new_evidence_ids
        ):
            return {
                "creature_id": creature_id,
                "creature_name": creature_for(creature_id).name,
                "stage": entry.stage,
                "stage_label": BESTIARY_STAGE_LABELS[entry.stage],
            }
        return None

    async def _grant_observation_xp(self, s, character_id, creature_id, reference_level):
        source_id = f"bestiary:observation:{character_id}:{creature_id}"
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return 0
        xp = int(
            (Decimal(level_xp(reference_level)) * Decimal("0.01")).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
        )
        event = RewardEvent(character_id=character_id, source_id=source_id)
        s.add(event)
        await s.flush()
        s.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary_observation_xp",
                item_id=creature_id,
                quantity=xp,
                payload={"reference_level": reference_level, "fixed_percent": "0.01"},
            )
        )
        character = await s.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        if character is not None:
            character.xp += xp
        return xp

    async def _grant_alpha_victory_xp(self, s, character_id, creature_id):
        source_id = f"bestiary:first_victory:{character_id}:{creature_id}"
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return False
        event = RewardEvent(character_id=character_id, source_id=source_id)
        s.add(event)
        await s.flush()
        s.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary_first_victory_xp",
                item_id=creature_id,
                quantity=198,
                payload={"reference_level": 3, "milestone": "first_major_victory"},
            )
        )
        character = await s.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        if character is not None:
            character.xp += 198
        return True

    async def _add_bestiary_evidence(self, s, entry, character_id, creature_id, evidence_id, category, points=0):
        exists = await s.scalar(select(BestiaryEvidence).where(
            BestiaryEvidence.character_id == character_id,
            BestiaryEvidence.creature_id == creature_id,
            BestiaryEvidence.evidence_id == evidence_id,
        ))
        if exists is None:
            s.add(BestiaryEvidence(character_id=character_id, creature_id=creature_id, evidence_id=evidence_id, category=category))
            entry.bkp += points
            return True
        return False

    async def _record_bestiary_combat_events(self, s, character_id, context, combat):
        entry = await s.scalar(select(BestiaryEntry).where(
            BestiaryEntry.character_id == character_id,
            BestiaryEntry.creature_id == context.creature_id,
        ).with_for_update())
        if entry is None:
            return set()
        new_evidence_ids = set()
        for event in combat.events:
            if event.actor != "enemy":
                continue
            action_id = event.action.removeprefix("prepare:")
            if await self._add_bestiary_evidence(
                s, entry, character_id, context.creature_id,
                f"action:{action_id}", "behavior", 4,
            ):
                new_evidence_ids.add(f"action:{action_id}")
            if event.action == "prepare:leap":
                if await self._add_bestiary_evidence(
                    s, entry, character_id, context.creature_id,
                    "mechanic:prepared_leap", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:prepared_leap")
            if event.action == "rend":
                if await self._add_bestiary_evidence(
                    s, entry, character_id, context.creature_id,
                    "mechanic:bleed", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:bleed")
            if combat.variant == "hemorrhagic" and event.actor == "enemy" and event.damage > 0:
                if await self._add_bestiary_evidence(
                    s, entry, character_id, context.creature_id,
                    "mechanic:hemorrhage", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:hemorrhage")
            if combat.variant == "venomous" and event.actor == "enemy" and event.damage > 0:
                if await self._add_bestiary_evidence(
                    s, entry, character_id, context.creature_id,
                    "mechanic:poison", "mechanic", 5,
                ):
                    new_evidence_ids.add("mechanic:poison")
        return new_evidence_ids

    async def _p1_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P1",
                    Quest.status == "completed",
                )
            )
        )

    async def _road_blocking_view(self, s, c):
        """Return the authoritative Road foreground/result before new callbacks run."""
        active = await s.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == c.id, GameActivity.status == "active")
            .with_for_update()
        )
        if active is not None:
            if active.content_id not in {HUNT_CONTENT, EXPLORE_CONTENT}:
                return None
            if self._expired(active):
                return await self._expire_activity(s, c, active)
            if active.content_id == HUNT_CONTENT:
                return await self._combat_view(s, c, active)
            attempt = await s.scalar(
                select(ExplorationAttempt).where(
                    ExplorationAttempt.activity_id == active.id
                )
            )
            if attempt is None or attempt.status == "active":
                return await self._combat_view(s, c, active)
            return await self._attempt_view(s, c, attempt, ROAD)

        attempt = await s.scalar(
            select(ExplorationAttempt)
            .where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.status.in_(("completed", "failed")),
                ExplorationAttempt.result_acknowledged.is_(False),
            )
            .order_by(ExplorationAttempt.completed_at.desc(), ExplorationAttempt.id.desc())
            .limit(1)
            .with_for_update()
        )
        if attempt is not None:
            return await self._attempt_view(s, c, attempt, ROAD)

        context = await s.scalar(
            select(HuntContext)
            .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
            .where(
                HuntContext.character_id == c.id,
                GameActivity.content_id == HUNT_CONTENT,
                GameActivity.status.in_(("completed", "failed")),
                HuntContext.result_acknowledged.is_(False),
            )
            .order_by(GameActivity.id.desc())
            .limit(1)
            .with_for_update()
        )
        if context is None:
            return None
        activity = await s.scalar(
            select(GameActivity).where(GameActivity.id == context.game_activity_id)
        )
        if activity is None:
            return None
        if activity.status == "completed":
            return await self._hunt_victory_view(s, c, activity)
        return RoadView(
            "hunt_defeat",
            c.id,
            ROAD,
            activity_id=activity.id,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
        )

    @staticmethod
    def _expired(activity) -> bool:
        return bool(
            activity.last_valid_action_at
            and datetime.now(UTC) - activity.last_valid_action_at > ROAD_ACTIVITY_GRACE
        )

    async def _expire_activity(self, s, c, activity):
        """Resolve an abandoned Road foreground exactly once."""
        if activity.status != "active":
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._result_view_for_activity(s, c, activity, world)
        activity.status = "failed"
        activity.last_valid_action_at = datetime.now(UTC)
        c.hp = c.max_hp
        if activity.content_id == EXPLORE_CONTENT:
            attempt = await s.scalar(
                select(ExplorationAttempt)
                .where(ExplorationAttempt.activity_id == activity.id)
                .with_for_update()
            )
            if attempt is not None:
                attempt.status = "failed"
                attempt.completed_at = datetime.now(UTC)
                attempt.progress = {
                    **(attempt.progress or {}),
                    "receipt_text": "A exploração expirou por inatividade. Recuperado na Estrada.",
                    "settled": True,
                }
                consolidate_level(c)
                return await self._attempt_view(s, c, attempt, ROAD)
        consolidate_level(c)
        return RoadView(
            "hunt_defeat",
            c.id,
            ROAD,
            activity_id=activity.id,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
        )

    async def _result_view_for_activity(self, s, c, activity, world):
        if activity.content_id == HUNT_CONTENT:
            if activity.status == "completed":
                context = await s.scalar(
                    select(HuntContext).where(HuntContext.game_activity_id == activity.id)
                )
                if context is not None and not context.result_acknowledged:
                    return await self._hunt_victory_view(s, c, activity)
            else:
                context = await s.scalar(
                    select(HuntContext)
                    .where(HuntContext.game_activity_id == activity.id)
                    .with_for_update()
                )
                if context is not None and not context.result_acknowledged:
                    return RoadView(
                        "hunt_defeat",
                        c.id,
                        ROAD,
                        activity_id=activity.id,
                        vigor=c.vigor,
                        max_vigor=c.max_vigor,
                    )
        elif activity.content_id == EXPLORE_CONTENT:
            attempt = await s.scalar(
                select(ExplorationAttempt).where(ExplorationAttempt.activity_id == activity.id)
            )
            if attempt is not None and not attempt.result_acknowledged:
                return await self._attempt_view(s, c, attempt, ROAD)
        return await self._view_for_world(s, c, world) if world is not None else None

    async def _combat_view(self, s, c, activity):
        encounter, record = await CombatRepository(s).combat(activity)
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        return RoadView(
            "combat",
            c.id,
            ROAD,
            activity.id,
            encounter.id,
            record.id,
            combat,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
        )

    async def _view_for_world(self, s, c, world):
        familiar = bool(await s.scalar(select(Unlock).where(Unlock.character_id == c.id, Unlock.unlock_id == ROUND_FAMILIARITY)))
        explore_available = True
        if world.location == ROAD:
            now = datetime.now(UTC)
            recent = await s.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                )
            ) or 0
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == ROAD,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            explore_available = not (
                recent >= 6
                or (last is not None and last.created_at > now - timedelta(minutes=5))
            )
        return RoadView(
            "road" if world.location == ROAD else "refuge",
            c.id,
            world.location,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            familiar=familiar,
            explore_available=explore_available,
        )

    async def _locked_world(self, s, actor):
        c = await s.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if c is None:
            return None, None
        world = await s.scalar(
            select(WorldState).where(WorldState.character_id == c.id).with_for_update()
        )
        return c, world

    async def _character(self, s, actor):
        return await s.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _ensure(self, s, model, **values):
        found = await s.scalar(select(model).filter_by(**values).with_for_update())
        if found is None:
            s.add(model(**values))
            return True
        return False

    async def _deliver_material(self, s, c, material_id: str, quantity: int, source_key: str) -> None:
        existing_delivery = await s.scalar(
            select(BlockedDelivery)
            .where(
                BlockedDelivery.character_id == c.id,
                BlockedDelivery.source_key == source_key,
            )
            .with_for_update()
        )
        if existing_delivery is not None:
            if existing_delivery.status == "pending":
                c.delivery_blocked = True
            return
        if await s.scalar(
            select(PendingItem)
            .where(
                PendingItem.character_id == c.id,
                PendingItem.source_key == source_key,
            )
            .with_for_update()
        ) is not None:
            return
        remaining = await self._deliver_material_to_inventory(s, c, material_id, quantity, False)
        if remaining:
            await self._pending(
                s,
                c.id,
                source_key,
                "material",
                {"material_id": material_id, "bound": False},
                remaining,
            )

    async def _deliver_material_to_inventory(self, s, c, material_id, quantity, bound):
        stacks = (
            await s.scalars(
                select(MaterialStack)
                .where(
                    MaterialStack.character_id == c.id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(bound),
                )
                .order_by(MaterialStack.id)
                .with_for_update()
            )
        ).all()
        remaining = quantity
        for stack in stacks:
            if remaining <= 0:
                break
            available = max(0, 999 - stack.quantity)
            added = min(remaining, available)
            stack.quantity += added
            remaining -= added
        while remaining > 0 and await self._inventory_slots(s, c.id) < 60:
            added = min(remaining, 999)
            s.add(
                MaterialStack(
                    character_id=c.id,
                    material_id=material_id,
                    quantity=added,
                    bound=bound,
                )
            )
            remaining -= added
        return remaining

    async def _inventory_slots(self, s, character_id):
        equipment = await s.scalar(select(func.count(EquipmentItem.id)).where(EquipmentItem.character_id == character_id)) or 0
        materials = await s.scalar(select(func.count(MaterialStack.id)).where(MaterialStack.character_id == character_id)) or 0
        runes = await s.scalar(select(func.count(RuneStack.id)).where(RuneStack.character_id == character_id)) or 0
        return int(equipment + materials + runes)

    async def _pending(self, s, character_id, source_key, kind, payload, quantity=1):
        hold = await s.scalar(
            select(BlockedDelivery)
            .where(
                BlockedDelivery.character_id == character_id,
                BlockedDelivery.source_key == source_key,
            )
            .with_for_update()
        )
        if hold is not None:
            character = await s.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
            if character is not None and hold.status == "pending":
                character.delivery_blocked = True
            return
        existing = await s.scalar(select(PendingItem).where(
            PendingItem.character_id == character_id, PendingItem.source_key == source_key
        ).with_for_update())
        if existing is not None:
            return
        count = await s.scalar(select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)) or 0
        if count < 20:
            s.add(PendingItem(character_id=character_id, source_key=source_key, kind=kind, payload=payload, quantity=quantity))
        else:
            character = await s.scalar(select(Character).where(Character.id == character_id).with_for_update())
            if character is not None:
                character.delivery_blocked = True
                s.add(
                    BlockedDelivery(
                        character_id=character_id,
                        source_key=source_key,
                        kind=kind,
                        payload=payload,
                        quantity=quantity,
                        status="pending",
                    )
                )

    async def _retry_blocked_deliveries(self, s, c) -> None:
        holds = (
            await s.scalars(
                select(BlockedDelivery)
                .where(
                    BlockedDelivery.character_id == c.id,
                    BlockedDelivery.status == "pending",
                )
                .order_by(BlockedDelivery.created_at, BlockedDelivery.id)
                .with_for_update()
            )
        ).all()
        for hold in holds:
            payload = dict(hold.payload or {})
            if hold.kind == "material":
                remaining = await self._deliver_material_to_inventory(
                    s,
                    c,
                    payload["material_id"],
                    hold.quantity,
                    bool(payload.get("bound", False)),
                )
                if remaining and await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=remaining,
                        )
                    )
                    remaining = 0
                hold.quantity = remaining or hold.quantity
                if remaining == 0:
                    self._resolve_delivery(hold)
            elif hold.kind == "equipment":
                if await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        EquipmentItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            item_name=payload["item_name"],
                            rarity=payload["rarity"],
                            slot=payload["slot"],
                            item_level=payload["item_level"],
                            bound=bool(payload.get("bound", False)),
                            payload=payload,
                        )
                    )
                    self._resolve_delivery(hold)
                elif await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=hold.quantity,
                        )
                    )
                    self._resolve_delivery(hold)
            elif hold.kind == "rune":
                stack = await s.scalar(
                    select(RuneStack)
                    .where(
                        RuneStack.character_id == c.id,
                        RuneStack.family == payload["family"],
                        RuneStack.rarity == payload["rarity"],
                        RuneStack.grade == payload.get("grade", 1),
                        RuneStack.bound.is_(bool(payload.get("bound", False))),
                    )
                    .with_for_update()
                )
                if stack is not None:
                    stack.quantity += hold.quantity
                    self._resolve_delivery(hold)
                elif await self._inventory_slots(s, c.id) < 60:
                    s.add(
                        RuneStack(
                            character_id=c.id,
                            family=payload["family"],
                            rarity=payload["rarity"],
                            grade=payload.get("grade", 1),
                            potency=payload["potency"],
                            quantity=hold.quantity,
                            bound=bool(payload.get("bound", False)),
                        )
                    )
                    self._resolve_delivery(hold)
                elif await self._pending_slots(s, c.id) > 0:
                    s.add(
                        PendingItem(
                            character_id=c.id,
                            source_key=hold.source_key,
                            kind=hold.kind,
                            payload=payload,
                            quantity=hold.quantity,
                        )
                    )
                    self._resolve_delivery(hold)
        c.delivery_blocked = bool(
            await s.scalar(
                select(func.count(BlockedDelivery.id)).where(
                    BlockedDelivery.character_id == c.id,
                    BlockedDelivery.status == "pending",
                )
            )
        )

    async def _pending_slots(self, s, character_id):
        count = await s.scalar(
            select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)
        ) or 0
        return 20 - int(count)

    @staticmethod
    def _resolve_delivery(hold):
        hold.status = "resolved"
        hold.resolved_at = datetime.now(UTC)

    async def _hunt_victory_view(self, s, c, activity):
        context = await s.scalar(select(HuntContext).where(HuntContext.game_activity_id == activity.id))
        if context is None:
            return None
        rows = (await s.scalars(select(RewardComponent).join(RewardEvent).where(
            RewardEvent.character_id == c.id,
            RewardEvent.source_id == f"activity:{activity.id}",
        ).order_by(RewardComponent.id))).all()
        labels = {
            "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
            "material.tdo.couro_escoriado": "Couro Escoriado",
            "material.tdo.erva_cinzenta": "Erva Cinzenta",
            "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
        }
        reward_lines = []
        for row in rows:
            payload = row.payload or {}
            if row.kind == "xp":
                reward_lines.append(f"✨ XP · {row.quantity}")
            elif row.kind == "crowns":
                reward_lines.append(f"🪙 Coroas · {row.quantity}")
            elif row.kind == "equipment":
                reward_lines.append(
                    "🛡️ "
                    f"{payload.get('item_name', row.item_id or 'Equipamento')} · "
                    f"+{payload.get('enhancement', 0)} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')} · "
                    f"{payload.get('slot', 'Slot desconhecido')} · "
                    f"Nível do Item {payload.get('item_level', '?')} · "
                    f"{'Vinculado' if payload.get('bound', False) else 'Negociável'}"
                )
            elif row.kind == "rune":
                reward_lines.append(
                    "🔮 Runa "
                    f"{payload.get('family', row.item_id or 'desconhecida')} · "
                    f"{payload.get('rarity', 'Raridade desconhecida')} · "
                    f"Grau {payload.get('grade', 1)} · "
                    f"{'Vinculada' if payload.get('bound', False) else 'Negociável'}"
                )
            elif row.kind == "bestiary":
                reward_lines.append(
                    f"📖 Bestiário · {payload.get('creature_name', 'Atualização registrada')} · "
                    f"{payload.get('stage_label', payload.get('stage', 'Atualizado'))}"
                )
            else:
                reward_lines.append(f"📦 {labels.get(row.item_id, row.item_id or row.kind)} · {row.quantity}")
        return RoadView(
            "hunt_victory", c.id, ROAD,
            activity_id=activity.id,
            vigor=c.vigor, max_vigor=c.max_vigor,
            name=c.name, hp=c.hp, max_hp=c.max_hp,
            reward_lines=tuple(reward_lines),
            creature=creature_for(context.creature_id).name,
            variant=VARIANT_LABELS.get(context.variant, context.variant),
        )

    def _explore_limit_view(self, c, recent, last, now, sixth=None):
        if recent >= 6:
            attempts = [sixth.created_at + timedelta(minutes=60)] if sixth and sixth.created_at else []
            available_at = min(attempts) if attempts else now
            return RoadView("explore_limit", c.id, ROAD, vigor=c.vigor, max_vigor=c.max_vigor,
                            name=c.name, hp=c.hp, max_hp=c.max_hp,
                            result_text=_remaining(available_at, now))
        available_at = last.created_at + timedelta(minutes=5)
        return RoadView("explore_cooldown", c.id, ROAD, vigor=c.vigor, max_vigor=c.max_vigor,
                        name=c.name, hp=c.hp, max_hp=c.max_hp,
                        result_text=_remaining(available_at, now))

    async def _explore_retry_available(self, s, c, attempt) -> bool:
        if attempt is None or attempt.status == "active":
            return False
        now = datetime.now(UTC)
        recent = await s.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == ROAD,
                ExplorationAttempt.created_at >= now - timedelta(minutes=60),
            )
        ) or 0
        if recent >= 6:
            return False
        last = await s.scalar(
            select(ExplorationAttempt)
            .where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == ROAD,
            )
            .order_by(ExplorationAttempt.created_at.desc(), ExplorationAttempt.id.desc())
            .limit(1)
        )
        return not (
            last is not None
            and last.created_at
            and last.created_at > now - timedelta(minutes=5)
        )

    async def _attempt_view(self, s, c, attempt, location, text=None):
        persisted = (attempt.progress or {}).get("receipt_text") or (attempt.progress or {}).get("result_text")
        return RoadView(
            "exploration",
            c.id,
            location,
            attempt_id=attempt.id if attempt else None,
            result_id=attempt.result_id if attempt else None,
            result_text=text or persisted,
            state_version=attempt.state_version if attempt else 0,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            retry_available=await self._explore_retry_available(s, c, attempt),
        )


def _explore_result(seed: str, player_level: int = 1, recent: tuple[str, ...] = (), excluded: tuple[str, ...] = ()) -> tuple[str, str, str]:
    result = select_exploration_result(seed, player_level, recent, excluded)
    texts = {
        "marco_viajantes": (
            "great_discovery",
            "explore.tdo.estrada.marco_viajantes",
            "Um marco de pedra inclina-se à margem da estrada. Marcas gastas ao redor mostram que viajantes paravam aqui muito antes das passagens mais recentes.",
        ),
        "rastros_cinereos": (
            "knowledge",
            "explore.tdo.estrada.rastros_cinereos",
            "Marcas interrompidas atravessam a fuligem e desaparecem alguns passos adiante. Há sinais suficientes para reconhecer que alguma criatura utiliza esta rota.",
        ),
        "sinais_margem": (
            "knowledge",
            "explore.tdo.estrada.sinais_margem",
            "Pedras movidas, tecido preso aos espinhos e cinza revolvida mostram que viajantes ainda usam as margens da Estrada para descansar ou passar despercebidos.",
        ),
        "luzes": (
            "narrative",
            "explore.tdo.estrada.luzes",
            "Uma luz pálida surge entre as pedras por alguns instantes. Não há chama nem calor suficiente para explicá-la; quando você se aproxima, ela já desapareceu.",
        ),
        "vozes_vento": (
            "narrative",
            "explore.tdo.estrada.vozes_vento",
            "O vento atravessa a estrada e traz um som que lembra uma voz distante. Quando você tenta segui-lo, resta apenas o ruído da cinza contra a pedra.",
        ),
        "cinza_pegadas": (
            "atmospheric",
            "explore.tdo.estrada.cinza_pegadas",
            "Uma rajada atravessa a Estrada. Em poucos instantes, a cinza cobre marcas antigas até não restar indicação de quem passou por ali.",
        ),
        "carroca": (
            "atmospheric",
            "explore.tdo.estrada.carroca",
            "A estrutura apodrecida de uma carroça repousa fora da estrada. As rodas desapareceram há muito; o restante já não guarda nada de valor.",
        ),
        "fogueira": (
            "atmospheric",
            "explore.tdo.estrada.fogueira",
            "Pedras enegrecidas cercam uma fogueira antiga. A cinza está fria e nenhum sinal recente indica quem a acendeu.",
        ),
        "ferro": (
            "resource",
            "explore.tdo.estrada.ferro",
            "Entre pedras partidas, um veio escuro de metal aflora sob a fuligem. Há material suficiente para ser recolhido.",
        ),
        "couro": (
            "resource",
            "explore.tdo.estrada.couro",
            "Entre restos secos à margem da estrada, uma porção de couro ainda aproveitável resistiu à cinza e ao tempo.",
        ),
        "erva": (
            "resource",
            "explore.tdo.estrada.erva",
            "Folhas acinzentadas crescem entre rachaduras protegidas do vento. Algumas ainda podem ser colhidas.",
        ),
        "residuo": (
            "resource",
            "explore.tdo.estrada.residuo",
            "Um depósito escuro se acumulou entre as pedras. A substância é fina, mas distinta da fuligem comum da Estrada.",
        ),
        "dog_cinereo": (
            "combat",
            "explore.tdo.estrada.combat.dog_cinereo",
            "Um Cão Cinéreo surge entre as cinzas.",
        ),
        "corvo_fuligem": (
            "combat",
            "explore.tdo.estrada.combat.corvo_fuligem",
            "Um Corvo de Fuligem desce sobre a estrada.",
        ),
        "peregrino_calcinado": (
            "combat",
            "explore.tdo.estrada.combat.peregrino_calcinado",
            "Um Peregrino Calcinado bloqueia a passagem.",
        ),
    }
    return texts[result]


def _draw_int(seed: str, purpose: str, modulo: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest(), "big") % modulo


def _repeat_bkp(wins: int, elite: bool) -> int:
    if elite:
        return 3 if wins == 2 else 2 if wins == 3 else 1 if 4 <= wins <= 5 else 0
    if 2 <= wins <= 5:
        return 2
    if 6 <= wins <= 10:
        return 1
    if wins in {15, 25, 40}:
        return 3
    return 0


def _remaining(available_at, now) -> str:
    seconds = max(0, int((available_at - now).total_seconds() + 0.999999))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _rarity(seed: str, category: str, purpose: str) -> str:
    roll = _draw_int(seed, purpose + ":rarity", 10000) / 100
    if purpose == "equipment":
        bands = (
            (
                (78, "Comum"),
                (97, "Raro"),
                (99.8, "Épico"),
                (100, "Lendário"),
            )
            if category == "common"
            else (
                (45, "Comum"),
                (87, "Raro"),
                (98, "Épico"),
                (99.9, "Lendário"),
                (100, "Mítico"),
            )
        )
    else:
        bands = (
            ((90, "Rara"), (99.5, "Épica"), (100, "Lendária"))
            if category == "common"
            else ((80, "Rara"), (98, "Épica"), (100, "Lendária"))
        )
    for limit, rarity in bands:
        if roll < limit:
            return rarity
    return bands[-1][1]
