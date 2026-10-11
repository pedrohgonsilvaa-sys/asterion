"""Shared persistence primitives for cooperative campaign encounters."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.domain.campaign_combat import campaign_boss_scaling
from asterion.domain.combat import (
    Combat,
    act,
    action_target_ids,
    active_player_key,
    allowed_actions,
    player_actions_for,
    use_combat_consumable,
)
from asterion.domain.road import (
    RULESET,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    CampaignJourney,
    CampaignJourneyMember,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    GameActivity,
    GroupActivityProposal,
    SocialGroup,
)


async def create_campaign_boss_profile(
    session: AsyncSession,
    characters: Sequence[Character],
    creature: Creature,
    enemy_level: int,
    *,
    flavor: str,
    opening_log: str,
) -> Combat:
    """Freeze real individual configurations and the approved boss scaling."""
    if not 1 <= len(characters) <= 4:
        raise ValueError("A campaign boss roster needs one to four participants.")
    party = []
    for index, character in enumerate(characters, start=1):
        equipment = await load_equipment_configuration(session, character)
        arts = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, equipment)
        party.append(
            PlayerCombatantSpec(
                fighter_key=campaign_actor_key(index, len(characters)),
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
    lead = characters[0]
    return create_creature_party_combat(
        uuid4(),
        lead.name,
        lead.character_class,
        lead.race,
        lead.hp,
        (
            CreatureCombatantSpec(
                creature,
                enemy_level,
                "enemy",
                campaign_boss_group_size=len(characters),
            ),
        ),
        player_level=lead.level,
        equipment_configuration=party[0].equipment_configuration,
        ruleset_version=RULESET,
        flavor=flavor,
        opening_log=opening_log,
        active_art_ids=party[0].active_art_ids,
        party=tuple(party),
    )


def campaign_actor_key(index: int, roster_size: int) -> str:
    """Use the legacy Solo fighter identity for a one-person social roster."""
    if not 1 <= index <= roster_size <= 4:
        raise ValueError("Campaign actor index must belong to a roster of one to four.")
    return "player" if roster_size == 1 else f"p{index}"


async def campaign_combat_for_activity(session, activity_id, character_id):
    """Load a shared encounter snapshot without consulting another member's activity."""
    member = await session.scalar(
        select(CampaignSharedEncounterMember).where(
            CampaignSharedEncounterMember.game_activity_id == activity_id,
            CampaignSharedEncounterMember.character_id == character_id,
        )
    )
    if member is None:
        return None, None, None
    encounter = await session.get(CampaignSharedEncounter, member.shared_encounter_id)
    if encounter is None or encounter.combat_snapshot is None:
        return None, member, None
    combat = decode(
        encounter.combat_snapshot,
        encounter.id,
        encounter.ruleset_version,
        encounter.state_version,
    )
    return encounter, member, combat


def campaign_action_intent(combat: Combat, actor_key: str, index: int, target_code: str):
    """Resolve a compact combat callback against the current shared snapshot."""
    actions = []
    for action_id in allowed_actions(combat, actor_key):
        if action_id == "defend":
            actions.append(action_id)
            continue
        if player_actions_for(combat, actor_key).get(action_id) and action_target_ids(
            combat, action_id, actor_key=actor_key
        ):
            actions.append(action_id)
    if not 0 <= index < len(actions):
        return None
    action = actions[index]
    target_id = None
    if target_code.startswith("d"):
        try:
            target_index = int(target_code[1:])
        except ValueError:
            return None
        targets = action_target_ids(combat, action, actor_key=actor_key)
        if not 0 <= target_index < len(targets):
            return None
        entity_id = targets[target_index]
        target_id = next(
            (key for key, fighter in combat.fighters.items() if fighter.id == entity_id),
            None,
        )
        if target_id is None:
            return None
    elif target_code not in {"s", "x"}:
        return None
    return action, target_id


@dataclass(frozen=True, slots=True)
class CampaignRosterMember:
    character: Character
    actor_key: str
    role: str
    checkpoint: str


@dataclass(slots=True)
class LockedCampaignEncounter:
    encounter: CampaignSharedEncounter
    members: list[CampaignSharedEncounterMember]
    characters: dict[UUID, Character]
    activities: dict[UUID, GameActivity]
    combat: Combat


async def create_campaign_encounter(
    session: AsyncSession,
    *,
    group: SocialGroup,
    proposal: GroupActivityProposal,
    roster: Sequence[CampaignRosterMember],
    quest_id: str,
    content_id: str,
    combat: Combat,
    ruleset_version: str,
    checkpoint: str,
    campaign_boss: bool = False,
) -> CampaignSharedEncounter:
    """Freeze a campaign roster and create an active foreground for each member."""
    if not 1 <= len(roster) <= 4:
        raise ValueError("Campaign encounters require one to four participants.")
    character_ids = [member.character.id for member in roster]
    if len(set(character_ids)) != len(character_ids):
        raise ValueError("Campaign encounter participants must be unique.")
    if len({member.actor_key for member in roster}) != len(roster):
        raise ValueError("Campaign combat actor keys must be unique.")
    if any(member.role not in {"eligible", "helper"} for member in roster):
        raise ValueError("Campaign roster role must be eligible or helper.")

    now = datetime.now(UTC)
    reference_id = proposal.journey_reference_character_id or proposal.proposer_character_id
    journey = CampaignJourney(
        group_id=group.id,
        quest_id=quest_id,
        checkpoint=checkpoint,
        journey_reference_character_id=reference_id,
        technical_host_character_id=proposal.proposer_character_id,
        context_payload={
            "proposal_id": str(proposal.id),
            "activity_type": proposal.activity_type,
            "checkpoint": checkpoint,
        },
        status="active",
        revision=0,
        created_at=now,
        updated_at=now,
    )
    session.add(journey)
    await session.flush()

    scaling = None
    if campaign_boss:
        hp_factor, attack_factor = campaign_boss_scaling(len(roster))
        scaling = {
            "roster_size": len(roster),
            "hp_factor": str(hp_factor),
            "attack_factor": str(attack_factor),
            "defense_factor": "1",
            "agility_factor": "1",
            "frozen_at": now.isoformat(),
        }
    encounter = CampaignSharedEncounter(
        id=uuid4(),
        journey_id=journey.id,
        proposal_id=proposal.id,
        quest_id=quest_id,
        content_id=content_id,
        journey_reference_character_id=reference_id,
        technical_host_character_id=proposal.proposer_character_id,
        roster_size=len(roster),
        scaling_snapshot=scaling,
        ruleset_version=ruleset_version,
        state_version=combat.version,
        combat_snapshot=encode(combat),
        status="active",
        created_at=now,
    )
    session.add(encounter)
    for item in roster:
        session.add(
            CampaignJourneyMember(
                journey_id=journey.id,
                character_id=item.character.id,
                role=item.role,
                status="active",
                checkpoint_snapshot=item.checkpoint,
                joined_at=now,
            )
        )
        activity = GameActivity(
            id=uuid4(),
            character_id=item.character.id,
            content_id=content_id,
            status="active",
            state_version=combat.version,
            ruleset_version=ruleset_version,
            last_valid_action_at=now,
        )
        session.add(activity)
        await session.flush()
        session.add(
            CampaignSharedEncounterMember(
                shared_encounter_id=encounter.id,
                character_id=item.character.id,
                game_activity_id=activity.id,
                actor_key=item.actor_key,
                role=item.role,
                checkpoint_snapshot=item.checkpoint,
                settlement_state="pending",
                joined_at=now,
            )
        )
    await session.flush()
    return encounter


async def lock_campaign_encounter(
    session: AsyncSession, activity_id: UUID, character_id: UUID
) -> LockedCampaignEncounter | None:
    """Lock one encounter, then its roster in stable order to serialize all actors."""
    member_seed = await session.scalar(
        select(CampaignSharedEncounterMember).where(
            CampaignSharedEncounterMember.game_activity_id == activity_id,
            CampaignSharedEncounterMember.character_id == character_id,
        )
    )
    if member_seed is None:
        return None
    encounter = await session.scalar(
        select(CampaignSharedEncounter)
        .where(CampaignSharedEncounter.id == member_seed.shared_encounter_id)
        .with_for_update()
    )
    if encounter is None:
        return None
    members = list(
        (
            await session.scalars(
                select(CampaignSharedEncounterMember)
                .where(CampaignSharedEncounterMember.shared_encounter_id == encounter.id)
                .order_by(CampaignSharedEncounterMember.character_id)
                .with_for_update()
            )
        ).all()
    )
    ids = sorted(member.character_id for member in members)
    characters = list(
        (
            await session.scalars(
                select(Character)
                .where(Character.id.in_(ids))
                .order_by(Character.id)
                .with_for_update()
            )
        ).all()
    )
    activities = list(
        (
            await session.scalars(
                select(GameActivity)
                .where(GameActivity.id.in_([member.game_activity_id for member in members]))
                .order_by(GameActivity.id)
                .with_for_update()
            )
        ).all()
    )
    if len(characters) != len(ids) or len(activities) != len(members):
        return None
    combat = decode(
        encounter.combat_snapshot or {},
        encounter.id,
        encounter.ruleset_version,
        encounter.state_version,
    )
    return LockedCampaignEncounter(
        encounter,
        members,
        {character.id: character for character in characters},
        {activity.id: activity for activity in activities},
        combat,
    )


async def settle_campaign_encounter(session, locked: LockedCampaignEncounter, result: str) -> None:
    """Release the activity reservation once every character result is persisted."""
    from asterion.infrastructure.db.models import GroupActivityParticipant

    if result not in {"victory", "defeat"}:
        raise ValueError("Campaign encounter result must be terminal.")
    now = datetime.now(UTC)
    encounter = locked.encounter
    journey = await session.get(
        CampaignJourney, encounter.journey_id, with_for_update=True
    )
    if journey is not None:
        journey.status = "completed" if result == "victory" else "paused"
        journey.updated_at = now
        journey.revision += 1
        rows = list(
            (
                await session.scalars(
                    select(CampaignJourneyMember)
                    .where(CampaignJourneyMember.journey_id == journey.id)
                    .with_for_update()
                )
            ).all()
        )
        for row in rows:
            row.status = "completed" if result == "victory" else "paused"
    if encounter.proposal_id is not None:
        proposal = await session.get(
            GroupActivityProposal, encounter.proposal_id, with_for_update=True
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "completed" if result == "victory" else "failed"
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


def resolve_campaign_action(
    locked: LockedCampaignEncounter,
    *,
    activity_id: UUID,
    version: int,
    action: str | None = None,
    consumable_id: str | None = None,
    target_id: str | None = None,
    effect_id: str | None = None,
    consumable_budget: int | None = None,
) -> Combat:
    """Apply one idempotent, actor-owned turn to the frozen shared snapshot."""
    encounter = locked.encounter
    activity = locked.activities.get(activity_id)
    member = next(
        (row for row in locked.members if row.game_activity_id == activity_id), None
    )
    if (
        encounter.status != "active"
        or encounter.state_version != version
        or activity is None
        or activity.status != "active"
        or activity.state_version != version
        or member is None
        or active_player_key(locked.combat) != member.actor_key
    ):
        return locked.combat
    if (action is None) == (consumable_id is None):
        return locked.combat
    if action is not None:
        updated = act(
            locked.combat,
            action,
            target_id=target_id,
            actor_key=member.actor_key,
        )
    else:
        updated = use_combat_consumable(
            locked.combat,
            consumable_id or "",
            target_id=target_id,
            effect_id=effect_id,
            budget_limit=consumable_budget,
            actor_key=member.actor_key,
        )
    if updated.version == locked.combat.version:
        return locked.combat
    now = datetime.now(UTC)
    encounter.combat_snapshot = encode(updated)
    encounter.state_version = updated.version
    if updated.result:
        encounter.status = "completed" if updated.result == "victory" else "failed"
        encounter.resolved_at = now
    for roster_member in locked.members:
        roster_activity = locked.activities[roster_member.game_activity_id]
        fighter = updated.fighters.get(roster_member.actor_key)
        if fighter is not None:
            locked.characters[roster_member.character_id].hp = fighter.hp
        roster_activity.state_version = updated.version
        roster_activity.last_valid_action_at = now
        if updated.result:
            roster_activity.status = "completed" if updated.result == "victory" else "failed"
            roster_member.result = updated.result
    locked.combat = updated
    return updated
