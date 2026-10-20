"""Persistent shared combat for manual Caçadas started from a social Group."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import ActivityEligibility, GroupError
from asterion.domain.combat import (
    act,
    active_player_key,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.road import (
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    select_creature,
    select_variant,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    ConsumableStack,
    ExplorationAttempt,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    GroupHuntEncounter,
    GroupHuntMember,
    HuntContext,
    SocialGroup,
    WorldState,
)

if TYPE_CHECKING:
    from asterion.application.road import RoadService, RoadView

GROUP_HUNT_CONTENT = "road_group_hunt"
GROUP_HUNT_HP_FACTORS = (Decimal("1.00"), Decimal("1.72"), Decimal("2.44"), Decimal("3.16"))
GROUP_HUNT_ATTACK_FACTORS = (
    Decimal("1.00"), Decimal("1.08"), Decimal("1.16"), Decimal("1.24")
)


def group_hunt_scaling(roster_size: int) -> StatMultipliers:
    if not 2 <= roster_size <= 4:
        raise ValueError("group hunts require a frozen roster of two to four characters")
    index = roster_size - 1
    return StatMultipliers(
        GROUP_HUNT_HP_FACTORS[index],
        GROUP_HUNT_ATTACK_FACTORS[index],
        Decimal(1),
        Decimal(1),
    )


class GroupHuntService:
    """Owns the shared snapshot; each member keeps an individual activity and receipt."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        road: RoadService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.road = road

    async def context_payload(self, actor: int) -> dict:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                raise GroupError("character_missing")
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            profile = (
                await self.road._available_local_profile(session, character, world, "hunt")
                if world is not None
                else None
            )
            if profile is None:
                raise GroupError("hunt_unavailable")
            return {
                "local_id": profile.local_id,
                "location": world.location,
                "title": "Caçada em Grupo",
                "checkpoint": profile.label,
            }

    async def character_id(self, actor: int) -> UUID | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return character.id if character is not None else None

    async def eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        local_id = payload.get("local_id")
        location = payload.get("location")
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        profile = (
            await self.road._available_local_profile(session, character, world, "hunt")
            if world is not None
            else None
        )
        active = await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            ).limit(1)
        )
        pending_hunt_result = await session.scalar(
            select(HuntContext.id)
            .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
            .where(
                HuntContext.character_id == character.id,
                HuntContext.result_acknowledged.is_(False),
                GameActivity.content_id.in_(("road_manual_hunt", GROUP_HUNT_CONTENT)),
                GameActivity.status.in_(("completed", "failed")),
            )
            .limit(1)
        )
        pending_exploration = await session.scalar(
            select(ExplorationAttempt.id)
            .where(
                ExplorationAttempt.character_id == character.id,
                ExplorationAttempt.status.in_(("completed", "failed")),
                ExplorationAttempt.result_acknowledged.is_(False),
            )
            .limit(1)
        )
        eligible = bool(
            profile is not None
            and world is not None
            and profile.local_id == local_id
            and world.location == location
            and character.hp > 0
            and not character.delivery_blocked
            and active is None
            and pending_hunt_result is None
            and pending_exploration is None
        )
        if not eligible:
            return ActivityEligibility("ineligible")
        facts = {
            "character": character.id.hex,
            "level": character.level,
            "local_id": profile.local_id,
            "location": world.location,
            "hp_alive": character.hp > 0,
        }
        fingerprint = sha256(repr(sorted(facts.items())).encode()).hexdigest()
        return ActivityEligibility("eligible", fingerprint, facts)

    async def create_activity(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: Sequence[Character],
    ) -> str:
        return await self.road.pvpve.queue_group_hunt(session, proposal, characters)

    async def materialize_queued_pve(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: Sequence[Character],
        activities: Sequence[GameActivity],
        *,
        collision_id: UUID | None = None,
        domain_eligible: dict[UUID, bool] | None = None,
        reference_level: int | None = None,
        seed: str | None = None,
    ) -> str:
        """Turn an accepted hunt intent into its frozen shared PvE encounter."""
        return await self._create_pve_encounter(
            session,
            proposal,
            characters,
            activities=activities,
            collision_id=collision_id,
            domain_eligible=domain_eligible,
            reference_level=reference_level,
            seed=seed,
        )

    async def _create_pve_encounter(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: Sequence[Character],
        *,
        activities: Sequence[GameActivity] | None = None,
        collision_id: UUID | None = None,
        domain_eligible: dict[UUID, bool] | None = None,
        reference_level: int | None = None,
        seed: str | None = None,
    ) -> str:
        if not 2 <= len(characters) <= 4:
            raise GroupError("group_roster_size_invalid")
        if activities is not None and len(activities) != len(characters):
            raise GroupError("hunt_context_changed")
        context = proposal.context_payload
        world_rows = list(
            (
                await session.scalars(
                    select(WorldState)
                    .where(WorldState.character_id.in_([item.id for item in characters]))
                    .order_by(WorldState.character_id)
                    .with_for_update()
                )
            ).all()
        )
        worlds = {row.character_id: row for row in world_rows}
        if len(worlds) != len(characters):
            raise GroupError("hunt_context_changed")
        profile = None
        for character in characters:
            world = worlds[character.id]
            current = await self.road._available_local_profile(
                session, character, world, "hunt"
            )
            if (
                current is None
                or current.local_id != context.get("local_id")
                or world.location != context.get("location")
                or character.hp <= 0
                or character.delivery_blocked
            ):
                raise GroupError("hunt_context_changed")
            if profile is None:
                profile = current
            elif profile.local_id != current.local_id:
                raise GroupError("hunt_context_changed")
        assert profile is not None

        seed = seed or sha256(f"group-hunt:{proposal.id.hex}".encode()).hexdigest()
        reference_level = reference_level or max(character.level for character in characters)
        creature = select_creature(seed, reference_level, profile=profile)
        enemy_level = min(reference_level, creature.max_level)
        variant = select_variant(seed, creature, profile=profile)
        roster_size = len(characters)
        scale = group_hunt_scaling(roster_size)

        specs: list[PlayerCombatantSpec] = []
        config_by_character: dict[UUID, object] = {}
        for index, character in enumerate(characters, start=1):
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            config_by_character[character.id] = equipment
            specs.append(
                PlayerCombatantSpec(
                    fighter_key=f"p{index}",
                    character_id=str(character.id),
                    name=character.name,
                    character_class=character.character_class,
                    race=character.race,
                    level=character.level,
                    hp=character.hp,
                    equipment_configuration=equipment,
                    active_art_ids=arts.art_ids,
                    active_art_snapshots=tuple(slot.to_data() for slot in arts.slots),
                )
            )

        encounter_id = uuid4()
        combat = create_creature_party_combat(
            encounter_id,
            characters[0].name,
            characters[0].character_class,
            characters[0].race,
            characters[0].hp,
            (
                CreatureCombatantSpec(
                    creature,
                    enemy_level,
                    "enemy",
                    variant,
                    stat_multipliers=scale,
                ),
            ),
            player_level=reference_level,
            equipment_configuration=config_by_character[characters[0].id],
            ruleset_version=RULESET,
            flavor=f"A ameaça surge em {profile.label}.",
            opening_log=f"🐾 {creature.name} surge entre a fuligem.",
            party=tuple(specs),
        )
        group_id = await session.scalar(
            select(SocialGroup.id).where(
                SocialGroup.server_id == self.server_id,
                SocialGroup.id == proposal.group_id,
                SocialGroup.status == "active",
            )
        )
        if group_id is None:
            raise GroupError("not_in_group")
        encounter = GroupHuntEncounter(
            id=encounter_id,
            group_id=proposal.group_id,
            proposal_id=proposal.id,
            local_id=profile.local_id,
            creature_id=creature.creature_id,
            category=creature.category,
            enemy_level=enemy_level,
            reference_level=reference_level,
            variant=variant,
            seed=seed,
            roster_size=roster_size,
            scaling_snapshot={
                "roster_size": roster_size,
                "hp_factor": str(scale.hp),
                "attack_factor": str(scale.attack),
                "defense_factor": str(scale.defense),
                "agility_factor": str(scale.agility),
            },
            combat_id=combat.id,
            ruleset_version=RULESET,
            state_version=combat.version,
            combat_snapshot=encode(combat),
            status="active",
        )
        session.add(encounter)
        await session.flush()
        for index, (character, spec) in enumerate(zip(characters, specs, strict=True), start=1):
            activity = (
                activities[index - 1]
                if activities is not None
                else GameActivity(
                    id=uuid4(),
                    character_id=character.id,
                    content_id=GROUP_HUNT_CONTENT,
                    status="active",
                    state_version=combat.version,
                    ruleset_version=RULESET,
                    last_valid_action_at=datetime.now(UTC),
                )
            )
            activity.content_id = GROUP_HUNT_CONTENT
            activity.status = "active"
            activity.state_version = combat.version
            activity.ruleset_version = RULESET
            activity.last_valid_action_at = datetime.now(UTC)
            session.add(activity)
            await session.flush()
            member_seed = f"{seed}:{character.id.hex}"
            session.add(
                GroupHuntMember(
                    group_hunt_encounter_id=encounter.id,
                    character_id=character.id,
                    game_activity_id=activity.id,
                    actor_key=spec.fighter_key,
                    ordinal=index,
                    loot_seed=member_seed,
                )
            )
            session.add(
                HuntContext(
                    game_activity_id=activity.id,
                    character_id=character.id,
                    local_id=profile.local_id,
                    creature_id=creature.creature_id,
                    category=creature.category,
                    enemy_level=enemy_level,
                    variant=variant,
                    seed=member_seed,
                    loot_profile="hunt",
                    pvpve_collision_id=collision_id,
                    pvpve_reference_level=reference_level if collision_id is not None else None,
                    pvpve_domain_eligible=bool(
                        domain_eligible and domain_eligible.get(character.id, False)
                    ),
                )
            )
            await self.road._bestiary(
                session,
                character.id,
                creature.creature_id,
                variant=variant,
                elite=creature.category == "elite",
                grant_observation_xp=True,
                observation_level=enemy_level,
                observation_category=creature.category,
            )
            await self.road._record_charneca_habitat(
                session, character.id, creature.creature_id, profile
            )
        await session.flush()
        return encounter.id.hex

    async def handle_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> tuple[bool, RoadView | None]:
        async with self.sessions.begin() as session:
            character_seed = await self._character(session, actor)
            if character_seed is None:
                return False, None
            encounter_id = await self._member_encounter_id(
                session, activity_id, character_seed.id
            )
            seed_member = (
                await session.get(GroupHuntMember, (encounter_id, character_seed.id))
                if encounter_id is not None
                else None
            )
            if seed_member is None:
                return False, None
            encounter = await session.scalar(
                select(GroupHuntEncounter)
                .where(GroupHuntEncounter.id == seed_member.group_hunt_encounter_id)
                .with_for_update()
            )
            if encounter is None:
                return True, None
            members = list(
                (
                    await session.scalars(
                        select(GroupHuntMember)
                        .where(GroupHuntMember.group_hunt_encounter_id == encounter.id)
                        .order_by(GroupHuntMember.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            character_ids = sorted((row.character_id for row in members), key=str)
            characters = list(
                (
                    await session.scalars(
                        select(Character)
                        .where(Character.id.in_(character_ids))
                        .order_by(Character.id)
                        .with_for_update()
                    )
                ).all()
            )
            activities = list(
                (
                    await session.scalars(
                        select(GameActivity)
                        .where(GameActivity.id.in_([row.game_activity_id for row in members]))
                        .order_by(GameActivity.id)
                        .with_for_update()
                    )
                ).all()
            )
            member_by_character = {row.character_id: row for row in members}
            activity_by_id = {row.id: row for row in activities}
            character_by_id = {row.id: row for row in characters}
            member = member_by_character.get(character_seed.id)
            activity = activity_by_id.get(activity_id)
            if member is None or activity is None or activity.status != "active":
                return True, await self._result_view(session, character_seed, activity)
            if encounter.status != "active":
                return True, await self._result_view(session, character_seed, activity)
            if self.road._expired(activity):
                return True, await self._expire_in_session(
                    session,
                    encounter,
                    members,
                    character_by_id,
                    activity_by_id,
                    character_seed.id,
                )
            combat = decode(
                encounter.combat_snapshot,
                encounter.combat_id,
                encounter.ruleset_version,
                encounter.state_version,
            )
            if (
                version != encounter.state_version
                or activity.state_version != version
                or active_player_key(combat) != member.actor_key
            ):
                current = await self._combat_view(
                    session, character_seed, activity, encounter, members, combat
                )
                if consumable_id is not None:
                    current = replace(
                        current,
                        consumable_notice=self._consumable_notice(
                            combat, member, encounter.category
                        ),
                    )
                return True, current
            if (action is None) == (consumable_id is None):
                return True, await self._combat_view(
                    session, character_seed, activity, encounter, members, combat
                )
            if action is not None:
                updated = act(
                    combat,
                    action,
                    target_id=target_id,
                    actor_key=member.actor_key,
                    effect_id=effect_id,
                )
            else:
                limit = ENCOUNTER_CONSUMABLE_LIMITS.get(encounter.category, 0)
                stack = await session.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character_seed.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None or member.consumable_uses >= limit:
                    return True, await self._combat_view(
                        session, character_seed, activity, encounter, members, combat
                    )
                updated = use_combat_consumable(
                    combat,
                    consumable_id or "",
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=None,
                    actor_key=member.actor_key,
                )
                if updated.version != combat.version:
                    stack.quantity -= 1
                    member.consumable_uses += 1
            if updated.version == combat.version:
                return True, await self._combat_view(
                    session, character_seed, activity, encounter, members, combat
                )

            now = datetime.now(UTC)
            encounter.combat_snapshot = encode(updated)
            encounter.state_version = updated.version
            for row in members:
                roster_activity = activity_by_id[row.game_activity_id]
                fighter = updated.fighters.get(row.actor_key)
                if fighter is not None:
                    character_by_id[row.character_id].hp = fighter.hp
                roster_activity.state_version = updated.version
                roster_activity.last_valid_action_at = now
                if updated.result:
                    roster_activity.status = (
                        "completed" if updated.result == "victory" else "failed"
                    )
                    row.result = updated.result
            if updated.result:
                await self._settle_terminal(
                    session, encounter, members, character_by_id, activity_by_id, updated
                )
                return True, await self._result_view(session, character_seed, activity)
            await session.flush()
            return True, await self._combat_view(
                session, character_seed, activity, encounter, members, updated
            )

    async def view_for_activity(self, session, character, activity):
        member = await session.scalar(
            select(GroupHuntMember).where(GroupHuntMember.game_activity_id == activity.id)
        )
        if member is None:
            return None
        encounter = await session.get(GroupHuntEncounter, member.group_hunt_encounter_id)
        if encounter is None:
            return None
        members = list(
            (
                await session.scalars(
                    select(GroupHuntMember)
                    .where(GroupHuntMember.group_hunt_encounter_id == encounter.id)
                    .order_by(GroupHuntMember.character_id)
                )
            ).all()
        )
        if activity.status != "active" or encounter.status != "active":
            view = await self._result_view(session, character, activity)
            return replace(view, combat_context="group_hunt") if view is not None else None
        combat = decode(
            encounter.combat_snapshot,
            encounter.combat_id,
            encounter.ruleset_version,
            encounter.state_version,
        )
        return await self._combat_view(session, character, activity, encounter, members, combat)

    async def expire_from_road(self, session, character, activity):
        """Keep reads lock-safe; the next submitted action performs expiration atomically.

        Road resume already holds one member's Character row. Mutating the entire
        roster from that lock order could deadlock against the encounter-first action
        path, so expiration is committed by ``handle_action`` instead.
        """
        return await self.view_for_activity(session, character, activity)

    async def consumable_selection(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        screen: str = "items",
        item_id: str | None = None,
        target_id: str | None = None,
        parent: str = "items",
    ):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                )
            )
            if activity is None:
                return None
            view = await self.view_for_activity(session, character, activity)
            if view is None or view.kind != "combat":
                return view
            if view.state_version != version:
                member = await session.scalar(
                    select(GroupHuntMember).where(
                        GroupHuntMember.game_activity_id == activity_id,
                        GroupHuntMember.character_id == character.id,
                    )
                )
                encounter = (
                    await session.get(GroupHuntEncounter, member.group_hunt_encounter_id)
                    if member is not None
                    else None
                )
                return replace(
                    view,
                    consumable_notice=(
                        self._consumable_notice(view.combat, member, encounter.category)
                        if member is not None and encounter is not None
                        else None
                    ),
                )
            if screen == "combat":
                return view
            if screen == "items":
                return replace(view, consumable_screen="items") if view.consumable_options else view

            from asterion.domain.consumables import definition as consumable_definition

            item = consumable_definition(item_id or "")
            item_options = tuple(
                option for option in view.consumable_options if option.item_id == item_id
            )
            if item is None or not item_options:
                return replace(
                    view,
                    consumable_screen="items" if view.consumable_options else None,
                    consumable_notice="⚠️ Consumível · Não está mais disponível.",
                )
            if screen == "choose_item":
                if item.family.value == "dispeller":
                    targets = tuple(dict.fromkeys(option.target_id for option in item_options))
                    if len(targets) > 1:
                        return replace(
                            view,
                            consumable_screen="targets",
                            selected_consumable_id=item.id,
                            selection_parent="items",
                        )
                    target_id = targets[0] if targets else None
                    parent = "items"
                else:
                    target_id = "player"
                    parent = "items"
                selected = tuple(option for option in item_options if option.target_id == target_id)
                return self.road._selection_after_target(
                    view, item, target_id, selected, parent=parent
                )
            if screen == "choose_target" and item.family.value == "dispeller":
                selected = tuple(option for option in item_options if option.target_id == target_id)
                if not selected:
                    return replace(
                        view,
                        consumable_screen="items" if view.consumable_options else None,
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self.road._selection_after_target(
                    view, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family.value == "dispeller":
                targets = tuple(dict.fromkeys(option.target_id for option in item_options))
                return replace(
                    view,
                    consumable_screen="targets" if len(targets) > 1 else "items",
                    selected_consumable_id=item.id if len(targets) > 1 else None,
                    selection_parent="items",
                    consumable_notice=(
                        "⚠️ Dissipador · Sem Alvo Válido" if not targets else None
                    ),
                )
            if screen == "effects" and target_id is not None:
                selected = tuple(
                    option
                    for option in item_options
                    if option.target_id == target_id and option.effect_id is not None
                )
                if len(selected) > 1:
                    return replace(
                        view,
                        consumable_screen="effects",
                        selected_consumable_id=item.id,
                        selected_target_id=target_id,
                        selection_parent=parent,
                    )
                if len(selected) == 1:
                    return replace(view, ready_consumable_option=selected[0])
            return replace(
                view,
                consumable_screen="items" if view.consumable_options else None,
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )

    async def _combat_view(self, session, character, activity, encounter, members, combat):
        member = next((row for row in members if row.game_activity_id == activity.id), None)
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        actor_key = member.actor_key if member is not None else None
        consumables = ()
        quantities = ()
        budget = 0
        if actor_key is not None and active_player_key(combat) == actor_key:
            limit = ENCOUNTER_CONSUMABLE_LIMITS.get(context.category, 0) if context else 0
            budget = max(0, limit - member.consumable_uses)
            stacks = list(
                (
                    await session.scalars(
                        select(ConsumableStack)
                        .where(
                            ConsumableStack.character_id == character.id,
                            ConsumableStack.quantity > 0,
                        )
                        .order_by(ConsumableStack.consumable_id)
                    )
                ).all()
            )
            quantities = tuple((row.consumable_id, row.quantity) for row in stacks)
            consumables = combat_consumable_options(
                combat,
                tuple(item for item, _ in quantities),
                budget_limit=None,
                actor_key=actor_key,
            ) if budget > 0 else ()
        from asterion.application.road import RoadView, _location_label

        return RoadView(
            "combat",
            character.id,
            _location_label(encounter.local_id),
            activity_id=activity.id,
            encounter_id=encounter.id,
            combat_id=encounter.combat_id,
            combat=combat,
            state_version=encounter.state_version,
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            name=character.name,
            hp=character.hp,
            max_hp=character.max_hp,
            consumable_options=consumables,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            combat_context="group_hunt",
            combat_actor_key=actor_key,
        )

    @staticmethod
    def _consumable_notice(combat, member, category: str) -> str | None:
        actor_key = active_player_key(combat) or member.actor_key
        fighter = combat.fighters.get(actor_key)
        if fighter is None:
            return None
        if fighter.cooldowns.get("consumable", 0) > fighter.opportunity:
            return "⏳ Consumíveis · Em Recarga"
        limit = ENCOUNTER_CONSUMABLE_LIMITS.get(category, 0)
        if limit and member.consumable_uses >= limit:
            return "🔒 Consumíveis · Limite Atingido"
        return None

    async def _result_view(self, session, character, activity):
        if activity is None:
            return None
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        if context is not None and context.result_acknowledged:
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            return await self.road._view_for_world(session, character, world) if world else None
        if activity.status == "completed":
            view = await self.road._hunt_victory_view(session, character, activity)
        else:
            view = await self.road._hunt_defeat_view(session, character, activity, context)
        return replace(view, combat_context="group_hunt") if view is not None else None

    async def _settle_terminal(
        self, session, encounter, members, characters, activities, combat
    ) -> None:
        now = datetime.now(UTC)
        encounter.status = "completed" if combat.result == "victory" else "failed"
        encounter.resolved_at = now
        for member in members:
            character = characters[member.character_id]
            activity = activities[member.game_activity_id]
            context = await session.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == activity.id)
                .with_for_update()
            )
            evidence_ids = set()
            if context is not None:
                evidence_ids = await self.road._record_bestiary_combat_events(
                    session, character.id, context, combat
                )
            fighter = combat.fighters[member.actor_key]
            if combat.result == "victory":
                config = await load_equipment_configuration(session, character)
                await self.road._settle_hunt(
                    session,
                    character,
                    activity,
                    encounter.id,
                    evidence_ids,
                    equipment_configuration=config,
                )
                if fighter.hp <= 0:
                    world = await session.scalar(
                        select(WorldState)
                        .where(WorldState.character_id == character.id)
                        .with_for_update()
                    )
                    await self.road._recover_normal_pve_defeat(
                        session, character, encounter.local_id, world
                    )
                activity.status = "completed"
                member.result = "victory"
            else:
                activity.status = "failed"
                member.result = "defeat"
                if context is not None and context.pvpve_collision_id is not None:
                    await self.road.pvpve.finish_prey_member(
                        session,
                        context.pvpve_collision_id,
                        character.id,
                        victory=False,
                    )
                world = await session.scalar(
                    select(WorldState)
                    .where(WorldState.character_id == character.id)
                    .with_for_update()
                )
                await self.road._recover_normal_pve_defeat(
                    session, character, encounter.local_id, world
                )
            member.settlement_state = "settled"
            member.settled_at = now
            activity.last_valid_action_at = now
        proposal = await session.get(
            GroupActivityProposal, encounter.proposal_id, with_for_update=True
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "completed" if combat.result == "victory" else "failed"
            proposal.finished_at = now
            proposal.revision += 1
        reservations = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == encounter.proposal_id)
                    .with_for_update()
                )
            ).all()
        )
        for row in reservations:
            row.reservation_state = "released"
        await session.flush()

    async def _expire_in_session(
        self,
        session,
        encounter,
        members,
        characters,
        activities,
        viewer_character_id,
    ):
        now = datetime.now(UTC)
        encounter.status = "failed"
        encounter.resolved_at = now
        viewer_activity = None
        for member in members:
            character = characters[member.character_id]
            activity = activities[member.game_activity_id]
            if member.character_id == viewer_character_id:
                viewer_activity = activity
            if activity.status == "active":
                activity.status = "failed"
                activity.last_valid_action_at = now
                context = await session.scalar(
                    select(HuntContext)
                    .where(HuntContext.game_activity_id == activity.id)
                    .with_for_update()
                )
                if context is not None and context.pvpve_collision_id is not None:
                    await self.road.pvpve.finish_prey_member(
                        session,
                        context.pvpve_collision_id,
                        character.id,
                        victory=False,
                    )
                await self.road._recover_normal_pve_defeat(
                    session, character, encounter.local_id
                )
                from asterion.application.progression import consolidate_character_level

                await consolidate_character_level(session, character)
                member.result = "defeat"
                member.settlement_state = "settled"
                member.settled_at = now
        proposal = await session.get(
            GroupActivityProposal, encounter.proposal_id, with_for_update=True
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "failed"
            proposal.finished_at = now
            proposal.cancel_reason = "activity_expired"
            proposal.revision += 1
        reservations = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == encounter.proposal_id)
                    .with_for_update()
                )
            ).all()
        )
        for row in reservations:
            row.reservation_state = "released"
        await session.flush()
        if viewer_activity is None:
            return None
        viewer = characters[viewer_character_id]
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == viewer_activity.id)
        )
        view = await self.road._hunt_defeat_view(session, viewer, viewer_activity, context)
        return replace(view, combat_context="group_hunt") if view is not None else None

    async def _character(self, session, actor: int):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    @staticmethod
    async def _member_encounter_id(session, activity_id, character_id):
        return await session.scalar(
            select(GroupHuntMember.group_hunt_encounter_id).where(
                GroupHuntMember.game_activity_id == activity_id,
                GroupHuntMember.character_id == character_id,
            )
        )
