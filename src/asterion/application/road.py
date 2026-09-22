"""Application services for the post-P1 Road hunt and exploration loop."""
# ruff: noqa: E501

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.domain.combat import act
from asterion.domain.road import (
    EXPLORE_UNLOCK,
    HUNT_UNLOCK,
    ROUND_FAMILIARITY,
    RULESET,
    create_road_combat,
    creature_for,
    crowns,
    equipment_rarity,
    enemy_xp,
    material_for,
    materialize_equipment,
    rune_potency,
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
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)

ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"
HUNT_CONTENT = "road_manual_hunt"
EXPLORE_CONTENT = "road_exploration"


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


class RoadService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id

    async def resume(self, actor: int) -> RoadView | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None and active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                if active.content_id == HUNT_CONTENT:
                    return await self._combat_view(s, c, active)
                attempt = await s.scalar(
                    select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                )
                return self._attempt_view(c, attempt, ROAD)
            if active is not None:
                return None
            failed = await s.scalar(
                select(GameActivity)
                .where(
                    GameActivity.character_id == c.id,
                    GameActivity.content_id == HUNT_CONTENT,
                    GameActivity.status == "failed",
                )
                .order_by(GameActivity.id.desc())
                .limit(1)
            )
            if failed is not None:
                return RoadView(
                    "hunt_defeat",
                    c.id,
                    ROAD,
                    activity_id=failed.id,
                    vigor=c.vigor,
                    max_vigor=c.max_vigor,
                )
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
            if c is None or world is None or destination not in {ROAD, REFUGE}:
                return None
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                return await self._view_for_world(s, c, world)
            target_brazier = (
                "tdo.brazier.estrada" if destination == ROAD else "tdo.brazier.refugio_do_ocaso"
            )
            if not await s.scalar(
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
            if c is None or world is None or world.location != ROAD:
                return None
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
            await self._bestiary(s, c.id, creature.creature_id)
            await s.flush()
            return await self._combat_view(s, c, activity)

    async def prepare_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions() as s:
            c = await self._character(s, actor)
            if c is None:
                return None
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if world is None or world.location != ROAD:
                return None
            return RoadView("hunt_prepare", c.id, ROAD, vigor=c.vigor, max_vigor=c.max_vigor,
                            name=c.name, hp=c.hp, max_hp=c.max_hp)

    async def action(
        self, actor: int, activity_id: UUID, version: int, action: str
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, _ = await self._locked_world(s, actor)
            if c is None:
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
            if activity.status != "active" or activity.state_version != version:
                return await self._combat_view(s, c, activity)
            encounter, record = await CombatRepository(s).combat(activity)
            combat = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
            updated = act(combat, action)
            if updated.version == combat.version:
                return await self._combat_view(s, c, activity)
            activity.state_version = updated.version
            record.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            if updated.result == "victory":
                activity.status = "completed"
                if activity.content_id == HUNT_CONTENT:
                    xp = await self._settle_hunt(s, c, activity, encounter.id)
                    return RoadView(
                        "hunt_victory",
                        c.id,
                        ROAD,
                        activity_id=activity.id,
                        vigor=c.vigor,
                        max_vigor=c.max_vigor,
                        name=c.name,
                        hp=c.hp,
                        max_hp=c.max_hp,
                        reward_lines=(f"✨ XP · {xp}",),
                    )
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
                        self._attempt_view(c, attempt, ROAD, "A exploração foi concluída.")
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
        return await self.start_hunt(actor)

    async def explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None or world.location != ROAD:
                return None
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
                    return await self._combat_view(s, c, active)
                attempt = await s.scalar(
                    select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
                )
                return self._attempt_view(c, attempt, ROAD)
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
            if recent >= 6 or (
                last and last.created_at and last.created_at > now - timedelta(minutes=5)
            ):
                return await self._view_for_world(s, c, world)
            seed = uuid4().hex
            recent_rows = (await s.scalars(
                select(ExplorationAttempt.result_id)
                .where(ExplorationAttempt.character_id == c.id, ExplorationAttempt.local_id == ROAD)
                .order_by(ExplorationAttempt.created_at.desc()).limit(3)
            )).all()
            result = _explore_result(
                seed, c.level, tuple(str(item).rsplit(".", 1)[-1] for item in recent_rows)
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
                progress={},
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
                await s.flush()
                return await self._combat_view(s, c, activity)
            await self._settle_exploration(s, c, attempt)
            return self._attempt_view(c, attempt, ROAD, result_text)

    async def _settle_hunt(self, s, c, activity, encounter_id):
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
        components = [("xp", None, xp)]
        if crowns_award:
            components.append(("crowns", None, crowns_award))
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
                components.append(("material", material, 1))
                stack = await s.scalar(
                    select(MaterialStack)
                    .where(
                        MaterialStack.character_id == c.id,
                        MaterialStack.material_id == material,
                        MaterialStack.bound.is_(False),
                    )
                    .with_for_update()
                )
                if stack is None:
                    s.add(
                        MaterialStack(
                            character_id=c.id, material_id=material, quantity=1, bound=False
                        )
                    )
                else:
                    stack.quantity += 1
            if context.category == "elite":
                components.append(("catalyst", "material.tdo.catalisador_elite_i", 1))
                if _draw_int(context.seed, "fragment", 100) < 40:
                    components.append(("fragment", "material.tdo.fragmento_aprimoramento_i", 1))
            await self._materialize_optional_loot(s, c, context, components)
            for kind, item_id, quantity in components:
                if kind in {"catalyst", "fragment"}:
                    pending_count = await s.scalar(select(func.count(PendingItem.id)).where(PendingItem.character_id == c.id)) or 0
                    if pending_count < 20:
                        s.add(PendingItem(character_id=c.id, source_key=f"activity:{activity.id}:{kind}", kind=kind, payload={"item_id": item_id}, quantity=quantity))
        for kind, item_id, quantity in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id, kind=kind, item_id=item_id, quantity=quantity
                )
            )
        await self._bestiary(s, c.id, context.creature_id, victory=True)
        await self._ensure(s, Unlock, character_id=c.id, unlock_id=ROUND_FAMILIARITY)
        return xp

    async def _materialize_optional_loot(self, s, c, context, components):
        equipment_chance = 35 if context.category == "elite" else 8
        rune_chance = 50 if context.category == "elite" else 5
        if _draw_int(context.seed, "equipment", 100) < equipment_chance:
            rarity = equipment_rarity(context.seed, context.category)
            item = materialize_equipment(context.seed, rarity, context.enemy_level)
            equipment_count = await s.scalar(select(func.count(EquipmentItem.id)).where(EquipmentItem.character_id == c.id)) or 0
            if equipment_count < 60:
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
                s.add(PendingItem(character_id=c.id, source_key=f"activity:{context.game_activity_id}:equipment", kind="equipment", payload=item, quantity=1))
            components.append(("equipment", item["item_name"], 1))
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
                s.add(
                    RuneStack(
                        character_id=c.id,
                        family=family,
                        rarity=rarity,
                        grade=1,
                        potency=rune_potency(family, rarity),
                        quantity=1,
                        bound=False,
                    )
                )
            else:
                stack.quantity += 1
            components.append(("rune", family, 1))

    async def _settle_exploration(self, s, c, attempt):
        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == attempt.activity_id)
            )
            if context is not None:
                factor = Decimal(1) if c.vigor >= 4 else Decimal("0.25")
                c.xp += enemy_xp(context.enemy_level, context.category, factor, player_level=c.level)
                if c.vigor >= 4:
                    c.vigor -= 4
                    c.crowns += int(
                        ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10).quantize(
                            Decimal(1), rounding="ROUND_HALF_EVEN"
                        )
                        * 10
                    )
                    pool = (("material.tdo.ferro_de_fuligem", 30), ("material.tdo.couro_escoriado", 30), ("material.tdo.erva_cinzenta", 20), ("material.tdo.residuo_ocaso", 20))
                    units = 1 + (1 if _draw_int(attempt.seed, "exploration-material-extra", 100) < 20 else 0)
                    for ordinal in range(units):
                        material = weighted_choice(
                            f"{attempt.seed}:exploration-material:{ordinal}", pool
                        )
                        stack = await s.scalar(
                            select(MaterialStack).where(
                                MaterialStack.character_id == c.id,
                                MaterialStack.material_id == material,
                                MaterialStack.bound.is_(False),
                            ).with_for_update()
                        )
                        if stack is None:
                            s.add(MaterialStack(character_id=c.id, material_id=material, quantity=1, bound=False))
                        else:
                            stack.quantity += 1
                await self._bestiary(s, c.id, context.creature_id, victory=True)
            return
        if attempt.category == "resource":
            if c.vigor >= 4:
                c.vigor -= 4
                c.crowns += int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding="ROUND_HALF_EVEN"
                    )
                    * 10
                )
                material_ids = {
                    "ferro": "material.tdo.ferro_de_fuligem",
                    "couro": "material.tdo.couro_escoriado",
                    "erva": "material.tdo.erva_cinzenta",
                    "residuo": "material.tdo.residuo_ocaso",
                }
                material = material_ids.get(attempt.result_id.rsplit(".", 1)[-1])
                if material:
                    stack = await s.scalar(
                        select(MaterialStack)
                        .where(
                            MaterialStack.character_id == c.id,
                            MaterialStack.material_id == material,
                            MaterialStack.bound.is_(False),
                        )
                        .with_for_update()
                    )
                    if stack is None:
                        s.add(
                            MaterialStack(
                                character_id=c.id, material_id=material, quantity=1, bound=False
                            )
                        )
                    else:
                        stack.quantity += 1
            return
        if attempt.result_id == "explore.tdo.estrada.marco_viajantes":
            c.xp += 456
            await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.memoria_viajantes",
            )
        elif attempt.result_id == "explore.tdo.estrada.luzes":
            c.xp += 143
            await self._ensure(
                s, CodexEntry, character_id=c.id, entry_id="codex.location.estrada_das_cinzas"
            )
            await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id="codex.location.estrada_das_cinzas",
                fragment_id="codex.fragment.estrada.luzes_na_estrada",
            )

    async def _bestiary(self, s, character_id, creature_id, *, victory=False):
        entry = await s.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == creature_id
            )
            .with_for_update()
        )
        if entry is None:
            entry = BestiaryEntry(
                character_id=character_id, creature_id=creature_id, bkp=7, wins=1 if victory else 0
            )
            s.add(entry)
        elif victory:
            entry.wins += 1
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
        if victory:
            first_victory = await s.scalar(select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == creature_id,
                BestiaryEvidence.evidence_id == "first_victory",
            ))
            if first_victory is None:
                s.add(BestiaryEvidence(character_id=character_id, creature_id=creature_id, evidence_id="first_victory", category="victory"))
                entry.bkp += 5
        if entry.bkp >= 60:
            entry.stage = "dominated"
        elif entry.bkp >= 30:
            entry.stage = "studied"
        else:
            entry.stage = "known"

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

    def _attempt_view(self, c, attempt, location, text=None):
        return RoadView(
            "exploration",
            c.id,
            location,
            attempt_id=attempt.id if attempt else None,
            result_id=attempt.result_id if attempt else None,
            result_text=text,
            state_version=attempt.state_version if attempt else 0,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
        )


def _explore_result(seed: str, player_level: int = 1, recent: tuple[str, ...] = ()) -> tuple[str, str, str]:
    result = select_exploration_result(seed, player_level, recent)
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
