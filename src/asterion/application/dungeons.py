"""Persistent dungeon-run lifecycle and solo Cripta do Ocaso execution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BestiaryRecorder
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import CHARNECA, REGION, RUINS, RoadService
from asterion.application.vigor import add_vigor_state, reconcile_character_vigor, utcnow
from asterion.domain.combat import (
    CombatConsumableOption,
    act,
    active_player_key,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import ConsumableFamily
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.dungeons import (
    CRYPT_FAMILY_ID,
    CRYPT_RULESET_VERSION,
    DIFFICULTIES,
    difficulty_gate,
    dungeon_completion_xp,
    dungeon_crowns,
    fragment_material_id,
    material_for_ordinal,
    rarity_with_pity,
    roll_brazier,
    roll_weighted,
    stable_draw,
)
from asterion.domain.equipment_stats import (
    equipment_configuration_from_data,
)
from asterion.domain.road import (
    RULESET,
    PlayerCombatantSpec,
    enemy_xp,
    materialize_equipment,
    rune_potency,
)
from asterion.domain.road import (
    RUNE_FAMILIES as ROAD_RUNE_FAMILIES,
)
from asterion.domain.tdo_crypt import (
    CRYPT_ENCOUNTERS,
    create_crypt_combat,
    encounter_specs,
    enemy_rewards,
)
from asterion.domain.tdo_galleries import (
    GALLERIES_BRAZIER_LABEL,
    GALLERIES_CONTENT_VERSION,
    GALLERIES_CORE_ID,
    GALLERIES_DISCOVERY_UNLOCK,
    GALLERIES_FAMILY_ID,
    GALLERIES_FIRST_CLEAR_PREFIX,
    GALLERIES_KNOWN_PATH_UNLOCK,
    GALLERIES_RECIPE_UNLOCK,
    GALLERIES_REWARD_PREFIX,
    GALLERIES_RULESET_VERSION,
    create_galleries_combat,
    gallery_encounter_specs,
    gallery_enemy_rewards,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    DungeonInvite,
    DungeonLobby,
    DungeonLobbyMember,
    DungeonMatchQueue,
    DungeonPityState,
    DungeonRun,
    DungeonRunEncounter,
    DungeonRunMember,
    EquipmentItem,
    GameActivity,
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)

D = Decimal
REFUGE = "Refúgio do Ocaso"
CRYPT_LOCATION = "Cripta do Ocaso"
CRYPT_DISCOVERY_UNLOCK = "dungeon.tdo.cripta_ocaso"
CRYPT_KNOWN_PATH_UNLOCK = "known_path.tdo.cripta_ocaso"
CRYPT_FIRST_CLEAR_PREFIX = "dungeon.tdo.cripta_ocaso.first_clear."
CRYPT_REWARD_PREFIX = "dungeon.tdo.cripta_ocaso.run."
CRYPT_CODEX_ENTRY = "codex.location.cripta_do_ocaso"
CRYPT_CONTENT = "dungeon_crypt_encounter"
DUNGEON_ACTIVITY_PREFIX = "dungeon_run_"
DUNGEON_IDLE_LIMIT = timedelta(hours=4)
DUNGEON_ABSOLUTE_LIMIT = timedelta(hours=24)
LOBBY_IDLE_LIMIT = timedelta(minutes=30)
READY_CHECK_LIMIT = timedelta(seconds=60)
INVITE_LIMIT = timedelta(minutes=10)
RUNE_FAMILY_IDS = tuple(family for family, _stat in ROAD_RUNE_FAMILIES)


@dataclass(frozen=True, slots=True)
class DungeonFamily:
    family_id: str
    name: str
    range_label: str
    entry_location: str
    entry_display: str
    discovery_unlock: str
    known_path_unlock: str
    first_clear_prefix: str
    reward_prefix: str
    content_id: str
    content_version: str
    ruleset_version: str
    reference_level: int
    minimum_level: int
    codex_entry: str
    core_id: str
    core_name: str
    recipe_unlock: str
    brazier_label: str


DUNGEON_FAMILIES = {
    CRYPT_FAMILY_ID: DungeonFamily(
        CRYPT_FAMILY_ID,
        "Cripta do Ocaso",
        "Nv.4–7",
        CHARNECA,
        "Charneca da Fuligem",
        CRYPT_DISCOVERY_UNLOCK,
        CRYPT_KNOWN_PATH_UNLOCK,
        CRYPT_FIRST_CLEAR_PREFIX,
        CRYPT_REWARD_PREFIX,
        CRYPT_CONTENT,
        "tdo-1.0.11",
        CRYPT_RULESET_VERSION,
        6,
        4,
        CRYPT_CODEX_ENTRY,
        "material.tdo.nucleo_cripta_ocaso",
        "Núcleo da Cripta do Ocaso",
        "recipe.tdo.cripta.relicario_sem_nome",
        "Braseiro do Silêncio",
    ),
    GALLERIES_FAMILY_ID: DungeonFamily(
        GALLERIES_FAMILY_ID,
        "Galerias do Vigia",
        "Nv.8–10",
        RUINS,
        "Ruínas do Vigia",
        GALLERIES_DISCOVERY_UNLOCK,
        GALLERIES_KNOWN_PATH_UNLOCK,
        GALLERIES_FIRST_CLEAR_PREFIX,
        GALLERIES_REWARD_PREFIX,
        "dungeon_galleries_encounter",
        GALLERIES_CONTENT_VERSION,
        GALLERIES_RULESET_VERSION,
        9,
        8,
        "codex.location.galerias_do_vigia",
        GALLERIES_CORE_ID,
        "Núcleo das Galerias do Vigia",
        GALLERIES_RECIPE_UNLOCK,
        GALLERIES_BRAZIER_LABEL,
    ),
}


def _family(family_id: str | None) -> DungeonFamily:
    return DUNGEON_FAMILIES.get(family_id or CRYPT_FAMILY_ID, DUNGEON_FAMILIES[CRYPT_FAMILY_ID])


def _encounter_count(family_id: str) -> int:
    return len(CRYPT_ENCOUNTERS) if family_id == CRYPT_FAMILY_ID else 5


def _encounter_environment(family_id: str, ordinal: int) -> str:
    if family_id == CRYPT_FAMILY_ID:
        return CRYPT_ENCOUNTERS[ordinal].environment
    return {
        1: "Corredor de Guarda",
        2: "Junção dos Vigias",
        3: "Vigia Íntegro",
        4: "Câmara dos Condutores",
        5: "Custódio do Primeiro Selo",
    }[ordinal]


def _encounter_specs(run, ordinal: int):
    family_id = getattr(run, "dungeon_family_id", CRYPT_FAMILY_ID)
    if family_id == CRYPT_FAMILY_ID:
        return encounter_specs(ordinal, run.difficulty)
    return gallery_encounter_specs(
        ordinal, run.difficulty, run.initial_group_size, run.reference_level
    )


def _enemy_rewards_for(run, ordinal: int):
    return (
        enemy_rewards(ordinal)
        if run.dungeon_family_id == CRYPT_FAMILY_ID
        else gallery_enemy_rewards(ordinal)
    )


@dataclass(frozen=True, slots=True)
class DungeonView:
    kind: str
    character_id: UUID
    character_name: str
    level: int
    location: str
    hp: Decimal
    max_hp: Decimal
    vigor: int
    max_vigor: int
    run_id: UUID | None = None
    state_version: int = 0
    difficulty: str | None = None
    difficulty_label: str | None = None
    difficulty_gates: tuple[tuple[str, str], ...] = ()
    ordinal: int = 0
    environment: str = ""
    has_brazier: bool | None = None
    brazier_activated: bool = False
    consumable_uses: int = 0
    consumable_limit: int = 0
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat: object | None = None
    context: str = "dungeon"
    stage: str = "dungeon"
    xp: int = 0
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: CombatConsumableOption | None = None
    trial_stage_caption: str | None = None
    reward_lines: tuple[str, ...] = ()
    first_clear: bool = False
    reason: str | None = None
    family_id: str = CRYPT_FAMILY_ID
    dungeon_name: str = "Cripta do Ocaso"
    range_label: str = "Nv.4–7"
    entry_display: str = "Charneca da Fuligem"
    known_dungeons: tuple[tuple[str, str, str, str], ...] = ()
    lobby_id: UUID | None = None
    lobby_mode: str | None = None
    party_members: tuple[tuple[str, int, Decimal, Decimal, int, str], ...] = ()
    combat_actor_key: str | None = None
    lobby_version: int = 0
    invite_id: UUID | None = None
    lobby_leader: bool = False
    lobby_member_status: str | None = None
    member_status: str | None = None


class DungeonService:
    """Global durable run semantics. D1 exposes only solo run creation."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        if not server_id or len(server_id) > 64:
            raise ValueError("A trusted server id is required")
        self.sessions = sessions
        self.server_id = server_id
        self.bestiary = BestiaryRecorder()
        self.road = RoadService(sessions, server_id)

    async def known(self, actor: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            known = []
            for family in DUNGEON_FAMILIES.values():
                if await self._has_unlock(session, character.id, family.discovery_unlock):
                    known.append(
                        (
                            family.family_id,
                            family.name,
                            family.range_label,
                            family.entry_display,
                        )
                    )
            return self._view(
                character,
                kind="known" if known else "empty",
                known_dungeons=tuple(known),
            )

    async def detail(self, actor: int, family_id: str = CRYPT_FAMILY_ID) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            family = DUNGEON_FAMILIES.get(family_id)
            if family is None or not await self._has_unlock(
                session, character.id, family.discovery_unlock
            ):
                return self._view(character, kind="hidden", family_id=family_id)
            stable = await self._has_unlock(
                session, character.id, family.first_clear_prefix + "stable"
            )
            fractured = await self._has_unlock(
                session, character.id, family.first_clear_prefix + "fractured"
            )
            gates = difficulty_gate(
                level=character.level,
                discovered=True,
                stable_first_clear=stable,
                fractured_first_clear=fractured,
                minimum_level=family.minimum_level,
            )
            return self._view(
                character,
                kind="detail",
                difficulty_gates=tuple(gates.items()),
                family_id=family.family_id,
            )

    async def prepare_group(
        self, actor: int, family_id: str, difficulty: str
    ) -> DungeonView | None:
        """Open a durable invitation lobby without reserving Vigor."""
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            family = DUNGEON_FAMILIES.get(family_id)
            reason = await self._eligibility_reason(session, character, family, difficulty)
            if reason:
                return self._view(character, kind="detail", reason=reason, family_id=family_id)
            lobby = DungeonLobby(
                id=uuid4(),
                dungeon_family_id=family_id,
                difficulty=difficulty,
                mode="invite",
                status="forming",
                leader_character_id=character.id,
                state_version=0,
                expires_at=datetime.now(UTC) + LOBBY_IDLE_LIMIT,
            )
            session.add(lobby)
            member = DungeonLobbyMember(
                lobby_id=lobby.id,
                character_id=character.id,
                position=1,
                status="joined",
            )
            session.add(member)
            await session.flush()
            member.foreground_activity_id = await self._new_lobby_foreground(
                session, character, family, lobby.id, lobby.state_version
            )
            return await self._lobby_view(session, character, lobby, member)

    async def invite_by_name(
        self, actor: int, lobby_id: UUID, version: int, character_name: str
    ) -> DungeonView | None:
        """Invite one eligible character using only their exact public character name."""
        async with self.sessions.begin() as session:
            leader = await self._locked_character(session, actor)
            if leader is None:
                return None
            lobby = await session.scalar(
                select(DungeonLobby).where(DungeonLobby.id == lobby_id).with_for_update()
            )
            if lobby is None or lobby.state_version != version or lobby.status != "forming":
                return await self._view_for_lobby(session, leader, lobby_id, kind="stale")
            if lobby.leader_character_id != leader.id:
                return await self._lobby_view(session, leader, lobby, None, reason="leader")
            target_name = character_name.strip()
            target = await session.scalar(
                select(Character)
                .where(
                    Character.server_id == self.server_id,
                    Character.name == target_name,
                )
                .with_for_update()
            )
            if target is None or target.id == leader.id:
                return await self._lobby_view(session, leader, lobby, None, reason="not_found")
            reason = await self._eligibility_reason(
                session,
                target,
                DUNGEON_FAMILIES.get(lobby.dungeon_family_id),
                lobby.difficulty,
            )
            if reason:
                return await self._lobby_view(session, leader, lobby, None, reason=reason)
            members = (
                await session.scalars(
                    select(DungeonLobbyMember).where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_(("joined", "matched", "confirmed")),
                    )
                )
            ).all()
            existing_invite = await session.scalar(
                select(DungeonInvite).where(
                    DungeonInvite.lobby_id == lobby.id,
                    DungeonInvite.invitee_character_id == target.id,
                    DungeonInvite.status == "pending",
                )
            )
            if len(members) >= 4 or existing_invite is not None:
                return await self._lobby_view(session, leader, lobby, None, reason="full")
            invite = DungeonInvite(
                id=uuid4(),
                lobby_id=lobby.id,
                inviter_character_id=leader.id,
                invitee_character_id=target.id,
                status="pending",
                state_version=0,
                expires_at=datetime.now(UTC) + INVITE_LIMIT,
            )
            session.add(invite)
            lobby.expires_at = datetime.now(UTC) + LOBBY_IDLE_LIMIT
            lobby.state_version += 1
            await session.flush()
            return await self._lobby_view(
                session, leader, lobby, None, reason=f"invited:{target.name}"
            )

    async def invite_active_lobby_by_name(
        self, actor: int, character_name: str
    ) -> DungeonView | None:
        """Invite a character by exact name from the caller's forming group."""
        async with self.sessions.begin() as session:
            leader = await self._character(session, actor)
            if leader is None:
                return None
            lobby = await session.scalar(
                select(DungeonLobby)
                .join(DungeonLobbyMember, DungeonLobbyMember.lobby_id == DungeonLobby.id)
                .where(
                    DungeonLobbyMember.character_id == leader.id,
                    DungeonLobby.leader_character_id == leader.id,
                    DungeonLobby.status == "forming",
                )
                .order_by(DungeonLobby.created_at.desc())
            )
            if lobby is None:
                return self._view(leader, kind="stale")
            lobby_id, version = lobby.id, lobby.state_version
        return await self.invite_by_name(actor, lobby_id, version, character_name)

    async def pending_invite(self, actor: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            invite = await session.scalar(
                select(DungeonInvite)
                .where(
                    DungeonInvite.invitee_character_id == character.id,
                    DungeonInvite.status == "pending",
                    DungeonInvite.expires_at > datetime.now(UTC),
                )
                .order_by(DungeonInvite.created_at)
            )
            if invite is None:
                return None
            lobby = await session.get(DungeonLobby, invite.lobby_id)
            if lobby is None or lobby.status != "forming":
                return None
            return await self._lobby_view(
                session, character, lobby, None, kind="invite", invite_id=invite.id
            )

    async def respond_invite(
        self, actor: int, invite_id: UUID, *, accept: bool
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            invite = await session.scalar(
                select(DungeonInvite).where(DungeonInvite.id == invite_id).with_for_update()
            )
            if (
                invite is None
                or invite.invitee_character_id != character.id
                or invite.status != "pending"
                or invite.expires_at <= datetime.now(UTC)
            ):
                return self._view(character, kind="stale")
            lobby = await session.scalar(
                select(DungeonLobby).where(DungeonLobby.id == invite.lobby_id).with_for_update()
            )
            if lobby is None or lobby.status != "forming":
                invite.status = "expired"
                return self._view(character, kind="stale")
            if not accept:
                invite.status = "declined"
                invite.state_version += 1
                return await self._lobby_view(
                    session, character, lobby, None, kind="invite_declined"
                )
            family = DUNGEON_FAMILIES.get(lobby.dungeon_family_id)
            reason = await self._eligibility_reason(session, character, family, lobby.difficulty)
            if reason:
                invite.status = "expired"
                return await self._lobby_view(
                    session, character, lobby, None, kind="invite", reason=reason
                )
            members = (
                await session.scalars(
                    select(DungeonLobbyMember)
                    .where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_({"joined", "queued", "matched", "confirmed"}),
                    )
                    .order_by(DungeonLobbyMember.position)
                    .with_for_update()
                )
            ).all()
            if len(members) >= 4:
                invite.status = "expired"
                return await self._lobby_view(
                    session, character, lobby, None, kind="invite", reason="full"
                )
            member = DungeonLobbyMember(
                lobby_id=lobby.id,
                character_id=character.id,
                position=next(
                    position
                    for position in range(1, 5)
                    if position not in {row.position for row in members}
                ),
                status="joined",
            )
            session.add(member)
            invite.status = "accepted"
            invite.state_version += 1
            lobby.state_version += 1
            lobby.expires_at = datetime.now(UTC) + LOBBY_IDLE_LIMIT
            await session.flush()
            member.foreground_activity_id = await self._new_lobby_foreground(
                session, character, family, lobby.id, lobby.state_version
            )
            return await self._lobby_view(session, character, lobby, member)

    async def open_entry_confirmation(
        self, actor: int, lobby_id: UUID, version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            lobby = await session.scalar(
                select(DungeonLobby).where(DungeonLobby.id == lobby_id).with_for_update()
            )
            if lobby is None or lobby.state_version != version or lobby.status != "forming":
                return await self._view_for_lobby(session, character, lobby_id, kind="stale")
            if lobby.leader_character_id != character.id:
                return await self._lobby_view(session, character, lobby, None, reason="leader")
            members = (
                await session.scalars(
                    select(DungeonLobbyMember)
                    .where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_({"joined", "queued"}),
                    )
                    .order_by(DungeonLobbyMember.position)
                    .with_for_update()
                )
            ).all()
            if not 2 <= len(members) <= 4:
                return await self._lobby_view(session, character, lobby, None, reason="group_size")
            family = DUNGEON_FAMILIES.get(lobby.dungeon_family_id)
            for candidate in members:
                candidate_character = await session.scalar(
                    select(Character)
                    .where(Character.id == candidate.character_id)
                    .with_for_update()
                )
                if candidate_character is None:
                    return await self._lobby_view(
                        session, character, lobby, None, reason="eligibility"
                    )
                reason = await self._eligibility_reason(
                    session,
                    candidate_character,
                    family,
                    lobby.difficulty,
                    allowed_activity_id=candidate.foreground_activity_id,
                    allowed_lobby_id=lobby.id,
                )
                if reason:
                    return await self._lobby_view(session, character, lobby, None, reason=reason)
            lobby.status = "confirming"
            lobby.confirmation_deadline = datetime.now(UTC) + READY_CHECK_LIMIT
            lobby.expires_at = lobby.confirmation_deadline
            lobby.state_version += 1
            for member in members:
                member.status = "matched"
            queue_rows = (
                await session.scalars(
                    select(DungeonMatchQueue)
                    .where(DungeonMatchQueue.lobby_id == lobby.id)
                    .with_for_update()
                )
            ).all()
            for row in queue_rows:
                if row.status == "queued":
                    row.status = "matched"
            return await self._lobby_view(session, character, lobby, None)

    async def confirm_entry(
        self, actor: int, lobby_id: UUID, version: int, *, confirm: bool
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            lobby = await session.scalar(
                select(DungeonLobby).where(DungeonLobby.id == lobby_id).with_for_update()
            )
            if (
                lobby is None
                or lobby.status != "confirming"
                or lobby.state_version != version
                or lobby.confirmation_deadline is None
                or lobby.confirmation_deadline <= datetime.now(UTC)
            ):
                if lobby is not None and lobby.status == "confirming":
                    await self._cancel_lobby(session, lobby, expired=True)
                return await self._view_for_lobby(session, character, lobby_id, kind="stale")
            member = await session.scalar(
                select(DungeonLobbyMember)
                .where(
                    DungeonLobbyMember.lobby_id == lobby.id,
                    DungeonLobbyMember.character_id == character.id,
                )
                .with_for_update()
            )
            if member is None or member.status not in {"matched", "confirmed"}:
                return await self._lobby_view(
                    session, character, lobby, member, reason="membership"
                )
            if not confirm:
                await self._cancel_lobby(session, lobby)
                return await self._lobby_view(session, character, lobby, member, kind="cancelled")
            member.status = "confirmed"
            member.confirmed_at = datetime.now(UTC)
            members = (
                await session.scalars(
                    select(DungeonLobbyMember)
                    .where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_({"matched", "confirmed"}),
                    )
                    .order_by(DungeonLobbyMember.position)
                    .with_for_update()
                )
            ).all()
            if all(row.status == "confirmed" for row in members):
                run = await self._materialize_lobby_run(session, lobby, members)
                if run is None:
                    await self._cancel_lobby(session, lobby)
                    return await self._lobby_view(
                        session, character, lobby, member, kind="cancelled", reason="eligibility"
                    )
                lobby.status = "started"
                lobby.run_id = run.id
                lobby.state_version += 1
                run_member = await session.scalar(
                    select(DungeonRunMember).where(
                        DungeonRunMember.run_id == run.id,
                        DungeonRunMember.character_id == character.id,
                    )
                )
                return await self._run_view(session, character, run, run_member)
            return await self._lobby_view(session, character, lobby, member)

    async def join_matchmaking(
        self, actor: int, family_id: str, difficulty: str
    ) -> DungeonView | None:
        """Join a persistent, family/difficulty-specific two-to-four-player queue."""
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            family = DUNGEON_FAMILIES.get(family_id)
            reason = await self._eligibility_reason(session, character, family, difficulty)
            if reason:
                return self._view(character, kind="detail", reason=reason, family_id=family_id)
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
                {"key": f"dungeon-match:{family_id}:{difficulty}"},
            )
            existing = await session.scalar(
                select(DungeonMatchQueue).where(DungeonMatchQueue.character_id == character.id)
            )
            if existing is not None and existing.status in {"queued", "matched"}:
                lobby = await session.get(DungeonLobby, existing.lobby_id)
                if lobby is not None and lobby.status in {"forming", "confirming"}:
                    lobby_member = await session.scalar(
                        select(DungeonLobbyMember).where(
                            DungeonLobbyMember.lobby_id == lobby.id,
                            DungeonLobbyMember.character_id == character.id,
                        )
                    )
                    kind = "confirming" if lobby.status == "confirming" else "queue"
                    return await self._lobby_view(
                        session, character, lobby, lobby_member, kind=kind
                    )
            queue = await session.scalars(
                select(DungeonMatchQueue)
                .where(
                    DungeonMatchQueue.dungeon_family_id == family_id,
                    DungeonMatchQueue.difficulty == difficulty,
                    DungeonMatchQueue.status == "queued",
                )
                .order_by(DungeonMatchQueue.created_at, DungeonMatchQueue.character_id)
                .limit(3)
                .with_for_update()
            )
            queued = list(queue.all())
            lobby = await session.get(DungeonLobby, queued[0].lobby_id) if queued else None
            if lobby is None:
                lobby = DungeonLobby(
                    id=uuid4(),
                    dungeon_family_id=family_id,
                    difficulty=difficulty,
                    mode="matchmaking",
                    status="forming",
                    leader_character_id=character.id,
                    state_version=0,
                    expires_at=datetime.now(UTC) + LOBBY_IDLE_LIMIT,
                )
                session.add(lobby)
                await session.flush()
            rows = (
                await session.scalars(
                    select(DungeonLobbyMember)
                    .where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_({"joined", "queued", "matched", "confirmed"}),
                    )
                    .order_by(DungeonLobbyMember.position)
                    .with_for_update()
                )
            ).all()
            if any(row.character_id == character.id for row in rows):
                return await self._lobby_view(session, character, lobby, None, kind="queue")
            lobby_member = DungeonLobbyMember(
                lobby_id=lobby.id,
                character_id=character.id,
                position=next(
                    position
                    for position in range(1, 5)
                    if position not in {row.position for row in rows}
                ),
                status="queued",
            )
            session.add(lobby_member)
            queue_row = existing or DungeonMatchQueue(
                character_id=character.id,
                dungeon_family_id=family_id,
                difficulty=difficulty,
                status="queued",
                lobby_id=lobby.id,
            )
            queue_row.dungeon_family_id = family_id
            queue_row.difficulty = difficulty
            queue_row.status = "queued"
            queue_row.lobby_id = lobby.id
            session.add(queue_row)
            lobby.state_version += 1
            lobby.expires_at = datetime.now(UTC) + LOBBY_IDLE_LIMIT
            for existing_member in rows:
                if existing_member.foreground_activity_id is None:
                    continue
                existing_shell = await session.get(
                    GameActivity, existing_member.foreground_activity_id
                )
                if existing_shell is not None and existing_shell.status == "active":
                    existing_shell.state_version = lobby.state_version
            await session.flush()
            lobby_member.foreground_activity_id = await self._new_lobby_foreground(
                session, character, family, lobby.id, lobby.state_version
            )
            for other in queued:
                other.lobby_id = lobby.id
            members = (
                await session.scalars(
                    select(DungeonLobbyMember)
                    .where(
                        DungeonLobbyMember.lobby_id == lobby.id,
                        DungeonLobbyMember.status.in_({"joined", "queued", "matched", "confirmed"}),
                    )
                    .order_by(DungeonLobbyMember.position)
                    .with_for_update()
                )
            ).all()
            if len(members) == 4:
                lobby.status = "confirming"
                lobby.confirmation_deadline = datetime.now(UTC) + READY_CHECK_LIMIT
                lobby.expires_at = lobby.confirmation_deadline
                lobby.state_version += 1
                for row in members:
                    row.status = "matched"
                queue_rows = (
                    await session.scalars(
                        select(DungeonMatchQueue)
                        .where(DungeonMatchQueue.lobby_id == lobby.id)
                        .with_for_update()
                    )
                ).all()
                for row in queue_rows:
                    if row.status == "queued":
                        row.status = "matched"
            return await self._lobby_view(session, character, lobby, lobby_member)

    async def cancel_queue_or_lobby(
        self, actor: int, lobby_id: UUID | None, version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            if lobby_id is None:
                return self._view(character, kind="stale")
            lobby = await session.scalar(
                select(DungeonLobby).where(DungeonLobby.id == lobby_id).with_for_update()
            )
            if (
                lobby is None
                or lobby.state_version != version
                or lobby.status not in {"forming", "confirming"}
            ):
                return await self._view_for_lobby(session, character, lobby_id, kind="stale")
            participant = await session.scalar(
                select(DungeonLobbyMember).where(
                    DungeonLobbyMember.lobby_id == lobby.id,
                    DungeonLobbyMember.character_id == character.id,
                )
            )
            if participant is None:
                return self._view(character, kind="stale")
            if lobby.status == "confirming" or (
                lobby.mode != "matchmaking" and lobby.leader_character_id == character.id
            ):
                await self._cancel_lobby(session, lobby)
                return await self._lobby_view(
                    session, character, lobby, participant, kind="cancelled"
                )
            participant.status = "left"
            await self._finish_lobby_foreground(session, participant)
            await session.delete(participant)
            if lobby.mode == "matchmaking":
                queue_row = await session.scalar(
                    select(DungeonMatchQueue)
                    .where(DungeonMatchQueue.character_id == character.id)
                    .with_for_update()
                )
                if queue_row is not None and queue_row.status in {"queued", "matched"}:
                    queue_row.status = "cancelled"
                remaining = (
                    await session.scalars(
                        select(DungeonLobbyMember)
                        .where(
                            DungeonLobbyMember.lobby_id == lobby.id,
                            DungeonLobbyMember.status.in_(
                                {"joined", "queued", "matched", "confirmed"}
                            ),
                        )
                        .order_by(DungeonLobbyMember.position)
                    )
                ).all()
                if not remaining:
                    lobby.status = "cancelled"
                elif lobby.leader_character_id == character.id:
                    lobby.leader_character_id = remaining[0].character_id
            lobby.state_version += 1
            return await self._lobby_view(session, character, lobby, participant, kind="cancelled")

    async def start_solo(
        self,
        actor: int,
        difficulty: str,
        family_id: str = CRYPT_FAMILY_ID,
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            family = DUNGEON_FAMILIES.get(family_id)
            if family is None:
                return self._view(character, kind="stale")
            run, member = await self._active_run(session, character.id, lock=True)
            if run is not None:
                if self._expired(run):
                    await self._expire(session, character, run, member)
                    return await self._run_view(session, character, run, member, kind="expired")
                return await self._run_view(session, character, run, member)
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            if (
                difficulty not in DIFFICULTIES
                or world is None
                or world.location != family.entry_location
                or not await self._has_unlock(session, character.id, family.discovery_unlock)
            ):
                return self._view(character, kind="detail", reason="gate", family_id=family_id)
            stable = await self._has_unlock(
                session, character.id, family.first_clear_prefix + "stable"
            )
            fractured = await self._has_unlock(
                session, character.id, family.first_clear_prefix + "fractured"
            )
            gates = difficulty_gate(
                level=character.level,
                discovered=True,
                stable_first_clear=stable,
                fractured_first_clear=fractured,
                minimum_level=family.minimum_level,
            )
            if gates.get(difficulty) != "available":
                return self._view(
                    character,
                    kind="detail",
                    difficulty_gates=tuple(gates.items()),
                    reason="gate",
                    family_id=family.family_id,
                )
            active_activity = await session.scalar(
                select(GameActivity.id)
                .where(GameActivity.character_id == character.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active_activity is not None:
                return self._view(character, kind="detail", reason="foreground")
            profile = DIFFICULTIES[difficulty]
            if character.vigor < profile.vigor:
                return self._view(character, kind="detail", reason="vigor")
            equipment = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, equipment)
            arts = await load_active_art_configuration(session, character)
            snapshot = equipment.to_data(RULESET) | arts.to_data()
            run_id = uuid4()
            seed = uuid4().hex
            now = datetime.now(UTC)
            character.vigor -= profile.vigor
            run = DungeonRun(
                id=run_id,
                dungeon_family_id=family.family_id,
                difficulty=difficulty,
                status="active",
                ruleset_version=family.ruleset_version,
                content_version=family.content_version,
                reference_level=(
                    family.reference_level if difficulty != "rupture" else profile.reference_level
                ),
                initial_group_size=1,
                current_encounter_ordinal=1,
                state_version=0,
                seed=seed,
                has_brazier=roll_brazier(seed, difficulty),
                brazier_activated=False,
                brazier_after_encounter=3,
                active_checkpoint_encounter=None,
                progress={
                    "internal_xp": 0,
                    "retry_available": False,
                    "family_id": family.family_id,
                },
                created_at=now,
                last_activity_at=now,
            )
            member = DungeonRunMember(
                run_id=run_id,
                character_id=character.id,
                position=1,
                status="active",
                vigor_reserved=profile.vigor,
                vigor_refunded=False,
                consumable_uses=0,
                combat_configuration=snapshot,
                hp=character.hp,
                max_hp=character.max_hp,
                run_state={},
                contribution={},
            )
            session.add_all([run, member])
            session.add_all(
                DungeonRunEncounter(
                    run_id=run_id,
                    encounter_ordinal=ordinal,
                    definition_id=(
                        CRYPT_ENCOUNTERS[ordinal].definition_id
                        if family.family_id == CRYPT_FAMILY_ID
                        else f"galleries.encounter.{ordinal}"
                    ),
                    status="pending",
                    activity_id=None,
                    attempt_count=0,
                    progress={},
                    reward_settled=False,
                )
                for ordinal in range(1, 6)
            )
            await session.flush()
            await self._create_lobby_activity(session, character, run)
            await self._ensure_codex_entry(session, character.id, family.codex_entry)
            world.region = REGION
            world.location = family.name
            return await self._run_view(session, character, run, member)

    async def resume(self, actor: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, lock=True)
            if run is None:
                now = datetime.now(UTC)
                invite = await session.scalar(
                    select(DungeonInvite)
                    .where(
                        DungeonInvite.invitee_character_id == character.id,
                        DungeonInvite.status == "pending",
                    )
                    .order_by(DungeonInvite.created_at)
                    .with_for_update()
                )
                if invite is not None:
                    if invite.expires_at <= now:
                        invite.status = "expired"
                    else:
                        lobby = await session.scalar(
                            select(DungeonLobby).where(DungeonLobby.id == invite.lobby_id)
                        )
                        if lobby is not None and lobby.status == "forming":
                            return await self._lobby_view(
                                session,
                                character,
                                lobby,
                                None,
                                kind="invite",
                                invite_id=invite.id,
                            )
                lobby_member = await session.scalar(
                    select(DungeonLobbyMember)
                    .join(DungeonLobby, DungeonLobby.id == DungeonLobbyMember.lobby_id)
                    .where(
                        DungeonLobbyMember.character_id == character.id,
                        DungeonLobbyMember.status.in_(("joined", "queued", "matched", "confirmed")),
                        DungeonLobby.status.in_(("forming", "confirming")),
                    )
                    .order_by(DungeonLobby.created_at.desc())
                    .with_for_update(of=DungeonLobbyMember)
                )
                if lobby_member is not None:
                    lobby = await session.scalar(
                        select(DungeonLobby)
                        .where(DungeonLobby.id == lobby_member.lobby_id)
                        .with_for_update()
                    )
                    if lobby.expires_at <= now:
                        await self._cancel_lobby(session, lobby, expired=True)
                        return await self._lobby_view(
                            session, character, lobby, lobby_member, kind="expired"
                        )
                    if (
                        lobby.status == "confirming"
                        and lobby.confirmation_deadline is not None
                        and lobby.confirmation_deadline <= now
                    ):
                        await self._cancel_lobby(session, lobby, expired=True)
                        return await self._lobby_view(
                            session, character, lobby, lobby_member, kind="expired"
                        )
                    kind = (
                        "queue"
                        if lobby.mode == "matchmaking" and lobby.status == "forming"
                        else None
                    )
                    return await self._lobby_view(
                        session, character, lobby, lobby_member, kind=kind
                    )
                return None
            now = datetime.now(UTC)
            if (
                now - run.last_activity_at >= DUNGEON_IDLE_LIMIT
                or now - run.created_at >= DUNGEON_ABSOLUTE_LIMIT
            ):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            activity = await self._active_activity(session, character.id)
            return await self._run_view(session, character, run, member, activity=activity)

    async def begin_encounter(
        self, actor: int, run_id: UUID, state_version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            if run.state_version != state_version or (run.progress or {}).get("awaiting_brazier"):
                activity = await self._active_activity(session, character.id)
                return await self._run_view(session, character, run, member, activity=activity)
            if member.status != "active":
                return await self._run_view(session, character, run, member)
            encounter = await session.scalar(
                select(DungeonRunEncounter)
                .where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.encounter_ordinal == run.current_encounter_ordinal,
                )
                .with_for_update()
            )
            if encounter is None or encounter.status == "completed":
                return await self._run_view(session, character, run, member, kind="stale")
            if encounter.status == "active" and encounter.activity_id is not None:
                canonical_activity = await session.get(GameActivity, encounter.activity_id)
                if canonical_activity is not None and canonical_activity.status == "active":
                    return await self._run_view(
                        session,
                        character,
                        run,
                        member,
                        activity=canonical_activity,
                        encounter=encounter,
                    )
            current = await self._active_activity(session, character.id)
            if current is not None:
                linked = await session.scalar(
                    select(DungeonRunEncounter).where(DungeonRunEncounter.activity_id == current.id)
                )
                if linked is not None:
                    if linked.status == "active":
                        return await self._run_view(
                            session, character, run, member, activity=current
                        )
                current.status = "completed"
                await session.flush()
            family = _family(run.dungeon_family_id)
            run_members = (
                await session.scalars(
                    select(DungeonRunMember)
                    .where(DungeonRunMember.run_id == run.id)
                    .order_by(DungeonRunMember.position)
                    .with_for_update()
                )
            ).all()
            member_characters = list(
                (
                    await session.scalars(
                        select(Character)
                        .where(Character.id.in_(row.character_id for row in run_members))
                        .order_by(Character.id)
                        .with_for_update()
                    )
                ).all()
            )
            character_by_id = {row.id: row for row in member_characters}
            active_members = [row for row in run_members if row.status == "active"]
            if not active_members:
                return await self._run_view(session, character, run, member, kind="failed")
            party_specs = []
            for run_member in run_members:
                member_character = character_by_id[run_member.character_id]
                config = equipment_configuration_from_data(run_member.combat_configuration)
                art_ids = tuple(
                    str(entry["art_id"])
                    for entry in run_member.combat_configuration.get("active_arts", ())
                    if isinstance(entry, dict) and entry.get("art_id")
                )
                party_specs.append(
                    PlayerCombatantSpec(
                        f"member_{run_member.position}",
                        str(member_character.id),
                        member_character.name,
                        member_character.character_class,
                        member_character.race,
                        member_character.level,
                        run_member.hp if run_member.status == "active" else D(0),
                        config,
                        art_ids,
                        active=run_member.status == "active",
                    )
                )
            primary_member = active_members[0]
            primary_character = character_by_id[primary_member.character_id]
            equipment = equipment_configuration_from_data(primary_member.combat_configuration)
            active_arts = party_specs[primary_member.position - 1].active_art_ids
            group = tuple(party_specs) if run.initial_group_size > 1 else None
            combat = (
                create_crypt_combat(
                    uuid4(),
                    name=primary_character.name,
                    character_class=primary_character.character_class,
                    race=primary_character.race,
                    hp=primary_member.hp,
                    level=primary_character.level,
                    difficulty=run.difficulty,
                    equipment=equipment,
                    active_art_ids=active_arts,
                    ordinal=run.current_encounter_ordinal,
                    run_seed=run.seed,
                    initial_group_size=run.initial_group_size,
                    party=group,
                )
                if run.dungeon_family_id == CRYPT_FAMILY_ID
                else create_galleries_combat(
                    uuid4(),
                    name=primary_character.name,
                    character_class=primary_character.character_class,
                    race=primary_character.race,
                    hp=primary_member.hp,
                    level=primary_character.level,
                    difficulty=run.difficulty,
                    reference_level=run.reference_level,
                    equipment=equipment,
                    active_art_ids=active_arts,
                    ordinal=run.current_encounter_ordinal,
                    run_seed=run.seed,
                    initial_group_size=run.initial_group_size,
                    party=group,
                )
            )
            combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
                "members": [
                    {
                        "fighter_key": f"member_{row.position}",
                        "character_id": str(row.character_id),
                        "configuration": row.combat_configuration,
                    }
                    for row in run_members
                ],
            }
            for run_member in run_members:
                old_shell = await session.get(GameActivity, run_member.foreground_activity_id)
                if old_shell is not None and old_shell.status == "active":
                    old_shell.status = "completed"
            activity, _, record = await CombatRepository(session).create(
                primary_character, family.content_id, combat
            )
            primary_member.foreground_activity_id = activity.id
            for run_member in run_members:
                shell = await session.get(GameActivity, run_member.foreground_activity_id)
                if run_member.character_id == primary_character.id:
                    continue
                if shell is None or shell.status != "active":
                    shell = GameActivity(
                        id=uuid4(),
                        character_id=run_member.character_id,
                        content_id=f"{DUNGEON_ACTIVITY_PREFIX}{run.id.hex}",
                        status="active",
                        state_version=combat.version,
                        ruleset_version=family.ruleset_version,
                        last_valid_action_at=datetime.now(UTC),
                    )
                    session.add(shell)
                    await session.flush()
                    run_member.foreground_activity_id = shell.id
                else:
                    shell.state_version = combat.version
            encounter.activity_id = activity.id
            encounter.status = "active"
            encounter.attempt_count += 1
            encounter.progress = {"event_cursor": 0}
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            for participant in run_members:
                participant_character = character_by_id[participant.character_id]
                await self._record_encounter_observations(
                    session,
                    participant_character,
                    run.current_encounter_ordinal,
                    family_id=run.dungeon_family_id,
                )
                await self._ensure_codex_for_encounter(
                    session,
                    participant_character.id,
                    run.current_encounter_ordinal,
                    family_id=run.dungeon_family_id,
                )
            return await self._run_view(
                session,
                character,
                run,
                member,
                activity=activity,
                combat=combat,
                record=record,
                encounter=encounter,
            )

    async def action(
        self,
        actor: int,
        run_id: UUID,
        activity_id: UUID,
        version: int,
        action_id: str,
        target_id: str | None = None,
        *,
        consumable_id: str | None = None,
        effect_id: str | None = None,
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            members = (
                await session.scalars(
                    select(DungeonRunMember)
                    .where(DungeonRunMember.run_id == run.id)
                    .order_by(DungeonRunMember.position)
                    .with_for_update()
                )
            ).all()
            characters = (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_([row.character_id for row in members]))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
            character_by_id = {row.id: row for row in characters}
            character = character_by_id.get(character.id)
            if character is None or member is None or member.status != "active":
                return self._view(character, kind="stale") if character is not None else None
            activity = await session.get(GameActivity, member.foreground_activity_id)
            encounter = await session.scalar(
                select(DungeonRunEncounter)
                .where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.encounter_ordinal == run.current_encounter_ordinal,
                )
                .with_for_update()
            )
            canonical_activity = (
                await session.get(GameActivity, encounter.activity_id)
                if encounter is not None and encounter.activity_id is not None
                else None
            )
            if (
                activity is None
                or activity.id != activity_id
                or activity.status != "active"
                or encounter is None
                or encounter.status != "active"
                or canonical_activity is None
                or canonical_activity.status != "active"
                or canonical_activity.state_version != version
                or activity.state_version != version
            ):
                return await self._run_view(session, character, run, member, activity=activity)
            pair = await CombatRepository(session).combat(canonical_activity)
            _combat_encounter, record = pair
            state = decode(
                record.snapshot,
                record.id,
                canonical_activity.ruleset_version,
                canonical_activity.state_version,
            )
            actor_key = f"member_{member.position}" if run.initial_group_size > 1 else "player"
            if active_player_key(state) != actor_key:
                return await self._run_view(
                    session,
                    character,
                    run,
                    member,
                    activity=activity,
                    combat=state,
                    record=record,
                    encounter=encounter,
                )
            stack = None
            if consumable_id is not None:
                remaining = DIFFICULTIES[run.difficulty].consumable_limit - member.consumable_uses
                if remaining <= 0:
                    return await self._run_view(
                        session,
                        character,
                        run,
                        member,
                        activity=activity,
                        combat=state,
                        record=record,
                        encounter=encounter,
                    )
                stack = await session.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None:
                    return await self._run_view(
                        session,
                        character,
                        run,
                        member,
                        activity=activity,
                        combat=state,
                        record=record,
                        encounter=encounter,
                    )
                updated = use_combat_consumable(
                    state,
                    consumable_id,
                    target_id=target_id or actor_key,
                    effect_id=effect_id,
                    budget_limit=remaining,
                    actor_key=actor_key,
                )
            else:
                updated = act(state, action_id, target_id=target_id, actor_key=actor_key)
            if updated.version == state.version:
                return await self._run_view(
                    session,
                    character,
                    run,
                    member,
                    activity=activity,
                    combat=state,
                    record=record,
                    encounter=encounter,
                )
            if stack is not None:
                stack.quantity -= 1
                member.consumable_uses += 1
            record.snapshot = encode(updated)
            now = datetime.now(UTC)
            canonical_activity.state_version = updated.version
            canonical_activity.last_valid_action_at = now
            for run_member in members:
                shell = await session.get(GameActivity, run_member.foreground_activity_id)
                if shell is not None and shell.status == "active":
                    shell.state_version = updated.version
                    shell.last_valid_action_at = now
            run.last_activity_at = datetime.now(UTC)
            for run_member in members:
                fighter_key = (
                    f"member_{run_member.position}" if run.initial_group_size > 1 else "player"
                )
                fighter = updated.fighters.get(fighter_key)
                if fighter is None:
                    continue
                run_member.hp = fighter.hp
                member_character = character_by_id[run_member.character_id]
                member_character.hp = fighter.hp
                if fighter.hp <= 0 and run_member.status == "active":
                    run_member.status = "defeated"
                elif fighter.hp > 0 and run_member.status == "defeated":
                    run_member.status = "active"
            self._record_contribution(member, state, updated, actor_key, character.max_hp)
            await self._record_combat_events(session, character, run, encounter, state, updated)
            if updated.result == "victory":
                await self._encounter_victory(
                    session,
                    character,
                    run,
                    members,
                    character_by_id,
                    encounter,
                    canonical_activity,
                    updated,
                )
                return await self._run_view(session, character, run, member)
            if updated.result == "defeat":
                await self._encounter_defeat(
                    session,
                    character,
                    run,
                    members,
                    character_by_id,
                    encounter,
                    canonical_activity,
                    updated,
                )
                return await self._run_view(session, character, run, member)
            return await self._run_view(
                session,
                character,
                run,
                member,
                activity=activity,
                combat=updated,
                record=record,
                encounter=encounter,
            )

    @staticmethod
    def _record_contribution(member, before, after, actor_key, max_hp) -> None:
        """Accumulate objective useful actions; rewards use relative party bands."""
        new_events = after.events[len(before.events) :]
        events = [event for event in new_events if event.actor == actor_key and not event.internal]
        if not events:
            return
        contribution = dict(member.contribution or {})
        points = D(contribution.get("points", 0))
        scale = max(D(1), D(max_hp))
        for event in events:
            points += D(1)
            points += D(max(0, event.effective_damage)) / scale
            points += max(D(0), D(event.healed)) / scale
            points += max(D(0), D(event.barrier_absorbed)) / scale
            points += D(max(0, event.defender_prevented_damage)) / scale
            if event.effect_id or event.actor_effect_id:
                points += D("0.25")
        contribution["points"] = str(points)
        contribution["actions"] = int(contribution.get("actions", 0)) + 1
        contribution["event_count"] = int(contribution.get("event_count", 0)) + len(events)
        member.contribution = contribution

    async def activate_brazier(
        self, actor: int, run_id: UUID, state_version: int
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            progress = dict(run.progress or {})
            if (
                run.state_version != state_version
                or not run.has_brazier
                or run.brazier_activated
                or not progress.get("awaiting_brazier")
                or run.current_encounter_ordinal != 4
            ):
                return await self._run_view(session, character, run, member)
            members = (
                await session.scalars(
                    select(DungeonRunMember)
                    .where(DungeonRunMember.run_id == run.id)
                    .order_by(DungeonRunMember.position)
                    .with_for_update()
                )
            ).all()
            characters = (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_([row.character_id for row in members]))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
            character_by_id = {row.id: row for row in characters}
            for run_member in members:
                if run_member.status not in {"active", "defeated"}:
                    continue
                run_member.status = "active"
                run_member.hp = run_member.max_hp
                character_by_id[run_member.character_id].hp = run_member.max_hp
            run.brazier_activated = True
            run.active_checkpoint_encounter = 4
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            progress["awaiting_brazier"] = False
            progress["retry_available"] = False
            run.progress = progress
            return await self._run_view(session, character, run, member)

    async def retry(self, actor: int, run_id: UUID, state_version: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            progress = dict(run.progress or {})
            if (
                run.state_version != state_version
                or not run.brazier_activated
                or not progress.get("retry_available")
            ):
                return await self._run_view(session, character, run, member)
            progress["retry_available"] = False
            run.progress = progress
            run.state_version += 1
            run.last_activity_at = datetime.now(UTC)
            return await self._run_view(session, character, run, member)

    async def abandon(self, actor: int, run_id: UUID, state_version: int) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, run_id=run_id, lock=True)
            if run is None:
                return self._view(character, kind="stale")
            if self._expired(run):
                await self._expire(session, character, run, member)
                return await self._run_view(session, character, run, member, kind="expired")
            members = (
                await session.scalars(
                    select(DungeonRunMember)
                    .where(DungeonRunMember.run_id == run.id)
                    .order_by(DungeonRunMember.position)
                    .with_for_update()
                )
            ).all()
            characters = (
                await session.scalars(
                    select(Character)
                    .where(Character.id.in_([row.character_id for row in members]))
                    .order_by(Character.id)
                    .with_for_update()
                )
            ).all()
            character_by_id = {row.id: row for row in characters}
            character = character_by_id.get(character.id)
            if character is None:
                return None
            active_encounter = await session.scalar(
                select(DungeonRunEncounter.encounter_ordinal).where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.status == "active",
                )
            )
            if run.state_version != state_version or active_encounter is not None:
                return await self._run_view(session, character, run, member)
            progress = dict(run.progress or {})
            votes = set(progress.get("abandon_votes", ()))
            votes.add(str(character.id))
            participant_ids = {str(row.character_id) for row in members if row.status != "left"}
            if votes != participant_ids:
                progress["abandon_votes"] = sorted(votes)
                run.progress = progress
                run.state_version += 1
                for run_member in members:
                    shell = await session.get(GameActivity, run_member.foreground_activity_id)
                    if shell is not None and shell.status == "active":
                        shell.state_version = run.state_version
                return await self._run_view(session, character, run, member, kind="abandon_pending")
            for run_member in members:
                if run_member.status == "left":
                    continue
                run_member.status = "left"
                await self._refund_vigor(
                    session, character_by_id[run_member.character_id], run_member
                )
                shell = await session.get(GameActivity, run_member.foreground_activity_id)
                if shell is not None and shell.status == "active":
                    shell.status = "failed"
                await self._return_to_entry(session, run_member.character_id, run.dungeon_family_id)
            run.status = "failed"
            run.failed_at = datetime.now(UTC)
            run.state_version += 1
            progress["internal_xp"] = 0
            progress["abandoned"] = True
            progress["abandon_votes"] = []
            run.progress = progress
            return await self._run_view(session, character, run, member, kind="failed")

    async def _encounter_victory(
        self, session, character, run, members, character_by_id, encounter, activity, combat
    ) -> None:
        ordinal = encounter.encounter_ordinal
        for participant in members:
            participant_character = character_by_id[participant.character_id]
            await self._record_combat_events(
                session, participant_character, run, encounter, combat, combat
            )
        specs = (
            encounter_specs(ordinal, run.difficulty)
            if run.dungeon_family_id == CRYPT_FAMILY_ID
            else gallery_encounter_specs(
                ordinal, run.difficulty, run.initial_group_size, run.reference_level
            )
        )
        for participant in members:
            participant_character = character_by_id[participant.character_id]
            if self._participation_factor(participant, members) <= 0:
                continue
            for spec in specs:
                fighter = combat.fighters[spec.fighter_key]
                if spec.required_for_victory and fighter.hp <= 0:
                    await self.bestiary.record(
                        session,
                        participant_character.id,
                        spec.creature.creature_id,
                        victory=True,
                        elite=spec.creature.category == "elite",
                        observation_category=spec.creature.category,
                    )
                    if spec.creature.creature_id == "sem_nome":
                        await self._grant_boss_milestone(
                            session, participant_character, run, spec.creature.creature_id
                        )
                        await self._refresh_crypt_boss_mastery(session, participant_character.id)
                    elif spec.creature.creature_id == "custodio_primeiro_selo":
                        await self._grant_boss_milestone(
                            session,
                            participant_character,
                            run,
                            spec.creature.creature_id,
                            fixed_xp=474,
                        )
        encounter.status = "completed"
        encounter.reward_settled = True
        encounter.completed_at = datetime.now(UTC)
        activity.status = "completed"
        progress = dict(run.progress or {})
        encounter_rewards = (
            enemy_rewards(ordinal)
            if run.dungeon_family_id == CRYPT_FAMILY_ID
            else gallery_enemy_rewards(ordinal)
        )
        earned = sum(
            enemy_xp(level, category, powerlevel_factor=D("0.25"))
            for _, level, category in encounter_rewards
        )
        progress["internal_xp"] = int(progress.get("internal_xp", 0)) + earned
        progress["internal_rewards"] = list(progress.get("internal_rewards", ())) + [
            [level, category] for _, level, category in encounter_rewards
        ]
        progress["retry_available"] = False
        run.progress = progress
        if ordinal == 5:
            await self._settle_run(session, character, run, members, character_by_id)
            for participant in members:
                shell = await session.get(GameActivity, participant.foreground_activity_id)
                if shell is not None and shell.status == "active":
                    shell.status = "completed"
                await self._return_to_entry(
                    session, participant.character_id, run.dungeon_family_id
                )
            return
        run.current_encounter_ordinal = ordinal + 1
        run.state_version += 1
        run.last_activity_at = datetime.now(UTC)
        if ordinal == 3 and run.has_brazier:
            progress["awaiting_brazier"] = True
            run.progress = progress
        await self._create_lobby_activity(session, character, run)

    async def _encounter_defeat(
        self, session, character, run, members, character_by_id, encounter, activity, combat
    ) -> None:
        for participant in members:
            participant_character = character_by_id[participant.character_id]
            await self._record_combat_events(
                session, participant_character, run, encounter, combat, combat
            )
        encounter.status = "pending"
        activity.status = "failed"
        progress = dict(run.progress or {})
        progress["retry_available"] = False
        if not run.brazier_activated:
            run.status = "failed"
            run.failed_at = datetime.now(UTC)
            progress["internal_xp"] = 0
            progress["internal_rewards"] = []
            run.progress = progress
            run.state_version += 1
            for participant in members:
                shell = await session.get(GameActivity, participant.foreground_activity_id)
                if shell is not None and shell.status == "active":
                    shell.status = "failed"
                participant.status = "left"
                await self._refund_vigor(
                    session, character_by_id[participant.character_id], participant
                )
                await self._return_to_entry(
                    session, participant.character_id, run.dungeon_family_id
                )
            return
        for participant in members:
            participant_character = character_by_id[participant.character_id]
            participant.hp = participant.max_hp
            participant.status = "active"
            participant_character.hp = participant.max_hp
        progress["retry_available"] = True
        run.progress = progress
        run.state_version += 1
        run.last_activity_at = datetime.now(UTC)
        await self._create_lobby_activity(session, character, run)

    @staticmethod
    def _participation_factor(member, members) -> Decimal:
        """Classify useful participation relative to the expedition average.

        At least 75% of the party-average score is normal (100%); 35–75% is
        low (70%); 10–35% is very low (25%); below 10%, including AFK, is 0%.
        The persisted score includes valid actions plus objective combat impact.
        """
        scores = [D((row.contribution or {}).get("points", 0)) for row in members]
        total = sum(scores, D(0))
        if total <= 0:
            return D(0)
        expected = total / max(1, len(members))
        ratio = D((member.contribution or {}).get("points", 0)) / expected
        if ratio >= D("0.75"):
            return D(1)
        if ratio >= D("0.35"):
            return D("0.70")
        if ratio >= D("0.10"):
            return D("0.25")
        return D(0)

    async def _settle_run(self, session, character, run, members, character_by_id) -> None:
        family = _family(run.dungeon_family_id)
        root_source = family.reward_prefix + run.id.hex
        progress = dict(run.progress or {})
        reward_lines_by_character = dict(progress.get("reward_lines_by_character", {}))
        first_clear_by_character = dict(progress.get("first_clear_by_character", {}))
        participation_by_character = dict(progress.get("participation_by_character", {}))
        consumed_vigor = {str(row.character_id): row.vigor_reserved for row in members}
        raw_internal_rewards = tuple(progress.get("internal_rewards", ()))
        profile = DIFFICULTIES[run.difficulty]
        for member in members:
            character = character_by_id[member.character_id]
            participation = self._participation_factor(member, members)
            participation_by_character[str(character.id)] = str(participation)
            source = (
                root_source
                if run.initial_group_size == 1
                else f"dungeon:{run.id.hex}:{character.id.hex}"
            )
            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == source,
                )
                .with_for_update()
            )
            member.vigor_reserved = 0
            member.status = "left"
            if participation <= 0:
                continue
            if event is not None:
                continue
            first_clear_id = family.first_clear_prefix + run.difficulty
            first_clear = not await self._has_unlock(session, character.id, first_clear_id)
            completion_xp = dungeon_completion_xp(
                run.reference_level, run.difficulty, first_clear=first_clear
            )
            internal_xp = sum(
                enemy_xp(
                    int(row[0]),
                    str(row[1]),
                    player_level=character.level,
                    powerlevel_factor=D("0.25"),
                    participation_factor=participation,
                )
                for row in raw_internal_rewards
            )
            total_xp = internal_xp + completion_xp
            crown_reward = dungeon_crowns(run.reference_level, run.difficulty)
            character.xp += total_xp
            character.crowns += crown_reward
            event = RewardEvent(character_id=character.id, source_id=source)
            session.add(event)
            await session.flush()
            components = [
                RewardComponent(
                    reward_event_id=event.id,
                    kind="xp",
                    item_id=None,
                    quantity=total_xp,
                    payload={
                        "internal": internal_xp,
                        "completion": completion_xp,
                        "first_clear": first_clear,
                        "participation_factor": str(participation),
                    },
                ),
                RewardComponent(
                    reward_event_id=event.id,
                    kind="crowns",
                    item_id=None,
                    quantity=crown_reward,
                    payload={},
                ),
            ]
            member_seed = f"{run.seed}:member:{character.id.hex}"
            material_counts: dict[str, int] = {}
            for ordinal in range(profile.basic_materials):
                material_id = material_for_ordinal(member_seed, ordinal)
                material_counts[material_id] = material_counts.get(material_id, 0) + 1
            material_counts["material.tdo.catalisador_elite_i"] = profile.catalysts
            material_counts[family.core_id] = profile.cores
            material_counts[fragment_material_id(run.reference_level)] = profile.fragments
            for material_id, quantity in sorted(material_counts.items()):
                material_source = f"{source}:material:{material_id}"
                if len(material_source) > 96:
                    material_digest = hashlib.sha256(material_id.encode("utf-8")).hexdigest()[:16]
                    material_source = f"{source}:m:{material_digest}"
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=material_id,
                        quantity=quantity,
                        payload={"material_id": material_id, "bound": False},
                    )
                )
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    material_source,
                    bound=False,
                )
            pity = await session.scalar(
                select(DungeonPityState)
                .where(DungeonPityState.character_id == character.id)
                .with_for_update()
            )
            if pity is None:
                pity = DungeonPityState(
                    character_id=character.id, legendary_plus_points=0, mythic_points=0
                )
                session.add(pity)
                await session.flush()
            rarity, legendary_points, mythic_points = rarity_with_pity(
                member_seed,
                run.difficulty,
                pity.legendary_plus_points,
                pity.mythic_points,
            )
            pity.legendary_plus_points = legendary_points
            pity.mythic_points = mythic_points
            equipment_payload = materialize_equipment(
                f"{source}:equipment",
                rarity,
                run.reference_level,
                bound=False,
            )
            components.append(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="equipment",
                    item_id=None,
                    quantity=1,
                    payload=equipment_payload,
                )
            )
            await self._deliver_equipment(
                session, character.id, f"{source}:equipment", equipment_payload
            )
            rune_payload = self._roll_rune(run, seed=member_seed)
            if rune_payload is not None:
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="rune",
                        item_id=rune_payload["family"],
                        quantity=1,
                        payload=rune_payload,
                    )
                )
                await self._deliver_rune(session, character.id, f"{source}:rune", rune_payload)
            has_recipe = await self._has_unlock(session, character.id, family.recipe_unlock)
            recipe_revealed = (
                not has_recipe
                and stable_draw(member_seed, "recipe.discovery", 10_000)
                < profile.recipe_chance * 100
            )
            if recipe_revealed:
                await self._ensure_unlock(session, character.id, family.recipe_unlock)
                components.append(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="unlock",
                        item_id=family.recipe_unlock,
                        quantity=1,
                        payload={"revealed": True},
                    )
                )
            if first_clear:
                await self._ensure_unlock(session, character.id, first_clear_id)
                first_clear_by_character[str(character.id)] = True
                if run.difficulty == "stable":
                    if run.dungeon_family_id == CRYPT_FAMILY_ID:
                        await self._refresh_crypt_boss_mastery(session, character.id)
                    else:
                        await self._refresh_galleries_boss_mastery(session, character.id)
            else:
                first_clear_by_character[str(character.id)] = False
            if run.dungeon_family_id == CRYPT_FAMILY_ID:
                await self._record_crypt_codex_completion(session, character.id)
            else:
                await self._record_galleries_codex_completion(session, character.id)
            session.add_all(components)
            reward_lines_by_character[str(character.id)] = self._reward_lines(
                total_xp,
                crown_reward,
                material_counts,
                equipment_payload,
                rune_payload,
                recipe_revealed,
                family=family,
            )
            await consolidate_character_level(session, character)
            from asterion.application.tdo_feats import reconcile_tdo_feats
            from asterion.application.vde_feats import reconcile_vde_feats

            await reconcile_tdo_feats(session, character)
            await reconcile_vde_feats(session, character)
        progress.update(
            internal_xp=0,
            internal_rewards=[],
            completed=True,
            reward_lines_by_character=reward_lines_by_character,
            first_clear_by_character=first_clear_by_character,
            participation_by_character=participation_by_character,
            reward_lines=reward_lines_by_character.get(str(character.id), ()),
            first_clear=first_clear_by_character.get(str(character.id), False),
            consumed_vigor_by_character=consumed_vigor,
        )
        run.progress = progress
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
        run.last_activity_at = datetime.now(UTC)
        run.state_version += 1

    def _roll_rune(self, run, *, seed: str | None = None) -> dict | None:
        profile = DIFFICULTIES[run.difficulty]
        seed = seed or run.seed
        if stable_draw(seed, "rune.drop", 10_000) >= profile.rune_chance * 100:
            return None
        rarity = roll_weighted(seed, "rune.rarity", profile.rune_rarity_bands)
        family = RUNE_FAMILY_IDS[stable_draw(seed, "rune.family", len(RUNE_FAMILY_IDS))]
        grade = min(6, max(1, (run.reference_level - 1) // 10 + 1))
        return {
            "family": family,
            "rarity": rarity,
            "grade": grade,
            "potency": rune_potency(family, rarity, grade),
            "bound": False,
        }

    def _reward_lines(
        self, xp, crowns, materials, equipment, rune, recipe, *, family=None
    ) -> tuple[str, ...]:
        family = family or DUNGEON_FAMILIES[CRYPT_FAMILY_ID]
        lines = [f"✨ XP · {xp:,}".replace(",", "."), f"🪙 Coroas · {crowns:,}".replace(",", ".")]
        labels = {
            "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
            "material.tdo.couro_escoriado": "Couro Escoriado",
            "material.tdo.erva_cinzenta": "Erva Cinzenta",
            "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            family.core_id: family.core_name,
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
        }
        for material_id, quantity in sorted(materials.items()):
            lines.append(f"📦 {labels.get(material_id, material_id)} · {quantity}")
        lines.append(
            f"🛡️ {equipment['item_name']} · {equipment['rarity']} · Nv.{equipment['item_level']}"
        )
        if rune:
            lines.append(f"🔷 Runa · {rune['family']} · {rune['rarity']} · Grau {rune['grade']}")
        if recipe:
            label = (
                "Guarda do Primeiro Selo"
                if family.family_id == GALLERIES_FAMILY_ID
                else "Relicário dos Sem-Nome"
            )
            lines.append(f"📜 Receita · {label} · Revelada")
        return tuple(lines)

    async def _deliver_equipment(self, session, character_id, source_key, payload):
        item_id, item_data = equipment_instance_payload(payload)
        if await self.road._inventory_slots(session, character_id) < 60:
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character_id,
                    source_key=source_key,
                    item_name=item_data["item_name"],
                    rarity=item_data["rarity"],
                    slot=item_data["slot"],
                    item_level=item_data["item_level"],
                    bound=False,
                    payload=item_data,
                )
            )
        else:
            await self.road._pending(session, character_id, source_key, "equipment", item_data)

    async def _deliver_rune(self, session, character_id, source_key, payload):
        stack = await session.scalar(
            select(RuneStack)
            .where(
                RuneStack.character_id == character_id,
                RuneStack.family == payload["family"],
                RuneStack.rarity == payload["rarity"],
                RuneStack.grade == payload["grade"],
                RuneStack.bound.is_(False),
            )
            .with_for_update()
        )
        if stack is not None:
            stack.quantity += 1
        elif await self.road._inventory_slots(session, character_id) < 60:
            session.add(
                RuneStack(
                    character_id=character_id,
                    family=payload["family"],
                    rarity=payload["rarity"],
                    grade=payload["grade"],
                    potency=payload["potency"],
                    quantity=1,
                    bound=False,
                )
            )
        else:
            await self.road._pending(session, character_id, source_key, "rune", payload)

    async def _grant_boss_milestone(
        self, session, character, run, creature_id, *, fixed_xp: int = 342
    ):
        source = f"bestiary.first_victory:{creature_id}"
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source)
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source)
        session.add(event)
        await session.flush()
        character.xp += fixed_xp
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="xp",
                item_id=None,
                quantity=fixed_xp,
                payload={"bestiary_milestone": True},
            )
        )

    async def _refresh_crypt_boss_mastery(self, session, character_id):
        if not await self._has_unlock(session, character_id, CRYPT_FIRST_CLEAR_PREFIX + "stable"):
            return
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == "sem_nome"
            )
            .with_for_update()
        )
        if entry is None:
            return
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == "sem_nome",
                    )
                )
            ).all()
        )
        required = {
            "first_victory",
            "phase:nobody_rest",
            "action:peso_sepulcro",
            "action:maos_esquecidos",
        }
        entry.stage = "dominated" if required.issubset(evidence) else entry.stage

    async def _record_encounter_observations(
        self, session, character, ordinal, *, family_id=CRYPT_FAMILY_ID
    ):
        dummy_run = type(
            "EncounterContext",
            (),
            {
                "dungeon_family_id": family_id,
                "difficulty": "stable",
                "initial_group_size": 1,
                "reference_level": _family(family_id).reference_level,
            },
        )()
        for spec in _encounter_specs(dummy_run, ordinal):
            if spec.passive:
                continue
            await self.bestiary.record(
                session,
                character.id,
                spec.creature.creature_id,
                elite=spec.creature.category == "elite",
                observation_category=spec.creature.category,
            )

    async def _record_combat_events(self, session, character, run, encounter, before, after):
        family_id = getattr(run, "dungeon_family_id", CRYPT_FAMILY_ID)
        progress = dict(encounter.progress or {})
        member_cursors = dict(progress.get("member_event_cursors", {}))
        cursor_data = member_cursors.get(str(character.id), {})
        group_size = getattr(run, "initial_group_size", 1)
        legacy_event_cursor = progress.get("event_cursor", 0) if group_size == 1 else 0
        legacy_mechanic_cursor = progress.get("mechanic_cursor", 0) if group_size == 1 else 0
        cursor = int(cursor_data.get("event", legacy_event_cursor))
        mechanic_cursor = int(cursor_data.get("mechanic", legacy_mechanic_cursor))
        if cursor > len(after.events):
            cursor = 0
        mechanic_events = getattr(after, "mechanic_events", ())
        if mechanic_cursor > len(mechanic_events):
            mechanic_cursor = 0
        specs = _encounter_specs(run, encounter.encounter_ordinal)
        creature_by_key = {spec.fighter_key: spec.creature for spec in specs}
        boss_key = next(
            (spec.fighter_key for spec in specs if spec.creature.category == "boss"),
            "enemy",
        )
        boss = after.fighters.get(boss_key) if encounter.encounter_ordinal == 5 else None
        boss_creature_id = "sem_nome" if family_id == CRYPT_FAMILY_ID else "custodio_primeiro_selo"
        for event in after.events[cursor:]:
            if boss is not None:
                for fighter_id, hp in event.fighter_hp_after:
                    if fighter_id == boss.id and boss.stats.hp > 0:
                        ratio = D(hp) / D(boss.stats.hp)
                        if family_id == CRYPT_FAMILY_ID:
                            await self._phase_evidence(session, character.id, ratio)
                        elif ratio <= D("0.35"):
                            await self._add_bestiary_evidence(
                                session,
                                character.id,
                                boss_creature_id,
                                "phase:ultima_ordem",
                                "phase",
                                5,
                            )
                        elif ratio < D("0.70"):
                            await self._add_bestiary_evidence(
                                session,
                                character.id,
                                boss_creature_id,
                                "phase:ordem_de_contencao",
                                "phase",
                                5,
                            )
            creature = creature_by_key.get(event.actor)
            if creature is None:
                continue
            action_id = event.action.removeprefix("prepare:")
            prefix, separator, suffix = action_id.partition("_")
            if separator and prefix.startswith("e") and prefix[1:].isdigit():
                action_id = suffix
            entry = await session.scalar(
                select(BestiaryEntry)
                .where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == creature.creature_id,
                )
                .with_for_update()
            )
            if entry is not None:
                await self.bestiary.add_evidence(
                    session,
                    entry,
                    character.id,
                    creature.creature_id,
                    f"action:{action_id}",
                    "behavior",
                    4,
                )
                if event.action.startswith("prepare:"):
                    await self.bestiary.add_evidence(
                        session,
                        entry,
                        character.id,
                        creature.creature_id,
                        f"mechanic:prepared_{action_id}",
                        "mechanic",
                        5,
                    )

        for event in mechanic_events[mechanic_cursor:]:
            if event.action == "phase:galleries.order_of_containment":
                await self._add_bestiary_evidence(
                    session,
                    character.id,
                    boss_creature_id,
                    "mechanic:fragmentos_ativos",
                    "mechanic",
                    5,
                )
            elif event.action == "phase:galleries.last_order":
                await self._add_bestiary_evidence(
                    session,
                    character.id,
                    boss_creature_id,
                    "phase:ultima_ordem",
                    "phase",
                    5,
                )
        member_cursors[str(character.id)] = {
            "event": len(after.events),
            "mechanic": len(mechanic_events),
        }
        progress.update(member_event_cursors=member_cursors)
        if group_size == 1:
            progress.update(event_cursor=len(after.events), mechanic_cursor=len(mechanic_events))
        encounter.progress = progress
        if encounter.encounter_ordinal == 5:
            if family_id == CRYPT_FAMILY_ID:
                await self._refresh_crypt_boss_mastery(session, character.id)
            else:
                await self._refresh_galleries_boss_mastery(session, character.id)

    async def _add_bestiary_evidence(
        self, session, character_id, creature_id, evidence_id, category, value
    ):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is not None:
            await self.bestiary.add_evidence(
                session, entry, character_id, creature_id, evidence_id, category, value
            )

    async def _refresh_galleries_boss_mastery(self, session, character_id):
        if not await self._has_unlock(
            session, character_id, GALLERIES_FIRST_CLEAR_PREFIX + "stable"
        ):
            return
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "custodio_primeiro_selo",
            )
            .with_for_update()
        )
        if entry is None:
            return
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == "custodio_primeiro_selo",
                    )
                )
            ).all()
        )
        required = {
            "first_victory",
            "phase:ultima_ordem",
            "mechanic:fragmentos_ativos",
            "action:ruptura_selo",
        }
        entry.stage = "dominated" if required.issubset(evidence) else entry.stage

    async def _phase_evidence(self, session, character_id, hp_ratio):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id, BestiaryEntry.creature_id == "sem_nome"
            )
            .with_for_update()
        )
        if entry is None:
            return
        if hp_ratio < D("0.70"):
            await self.bestiary.add_evidence(
                session, entry, character_id, "sem_nome", "phase:weight_of_dead", "phase", 5
            )
        if hp_ratio <= D("0.35"):
            await self.bestiary.add_evidence(
                session, entry, character_id, "sem_nome", "phase:nobody_rest", "phase", 5
            )

    async def _ensure_codex_for_encounter(
        self, session, character_id, ordinal, *, family_id=CRYPT_FAMILY_ID
    ):
        if family_id == GALLERIES_FAMILY_ID:
            fragments = {
                1: ("codex.location.galerias_do_vigia", "codex.fragment.galleries.entry"),
                3: ("codex.history.rede_de_defesa", "codex.fragment.galleries.defense_network"),
                4: ("codex.history.camara_de_contencao", "codex.fragment.galleries.containment"),
            }
            if ordinal == 5:
                return
            values = fragments.get(ordinal)
            if values is not None:
                await self._ensure_codex_entry(session, character_id, values[0])
                await self._ensure_fragment(session, character_id, values[0], values[1])
            return
        fragments = {
            1: ("codex.location.cripta_do_ocaso", "codex.fragment.crypt.entry"),
            3: ("codex.history.camadas_de_sepultamento", "codex.fragment.crypt.layers"),
            4: ("codex.history.camara_dos_nomes", "codex.fragment.crypt.names"),
        }
        if ordinal == 5:
            return
        values = fragments.get(ordinal)
        if values is None:
            return
        entry_id, fragment_id = values
        await self._ensure_codex_entry(session, character_id, entry_id)
        await self._ensure_fragment(session, character_id, entry_id, fragment_id)

    async def _record_crypt_codex_completion(self, session, character_id):
        for entry_id, fragment_id in (
            ("codex.history.o_ultimo_guardiao", "codex.fragment.crypt.last_guardian"),
            ("codex.history.os_sem_nome", "codex.fragment.crypt.sem_nome"),
        ):
            await self._ensure_codex_entry(session, character_id, entry_id)
            await self._ensure_fragment(session, character_id, entry_id, fragment_id)

    async def _record_galleries_codex_completion(self, session, character_id):
        for entry_id, fragment_id in (
            ("codex.history.primeiro_selo", "codex.fragment.galleries.first_seal"),
            ("codex.history.ordens_que_permanecem", "codex.fragment.galleries.orders_remain"),
        ):
            await self._ensure_codex_entry(session, character_id, entry_id)
            await self._ensure_fragment(session, character_id, entry_id, fragment_id)

    async def _eligibility_reason(
        self,
        session,
        character,
        family,
        difficulty,
        *,
        allowed_activity_id=None,
        allowed_lobby_id=None,
    ):
        if family is None or difficulty not in DIFFICULTIES:
            return "gate"
        await reconcile_character_vigor(session, character)
        if not await self._has_unlock(session, character.id, family.discovery_unlock):
            return "discovery"
        stable = await self._has_unlock(session, character.id, family.first_clear_prefix + "stable")
        fractured = await self._has_unlock(
            session, character.id, family.first_clear_prefix + "fractured"
        )
        gate = difficulty_gate(
            level=character.level,
            discovered=True,
            stable_first_clear=stable,
            fractured_first_clear=fractured,
            minimum_level=family.minimum_level,
        ).get(difficulty)
        if gate != "available":
            return gate or "gate"
        world = await session.get(WorldState, character.id)
        if world is None or world.location != family.entry_location:
            return "location"
        active = await session.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == character.id, GameActivity.status == "active")
            .with_for_update()
        )
        if active is not None and active.id != allowed_activity_id:
            return "foreground"
        run, _member = await self._active_run(session, character.id)
        if run is not None:
            return "foreground"
        if character.vigor < DIFFICULTIES[difficulty].vigor:
            return "vigor"
        lobby_membership = select(DungeonLobbyMember.character_id).where(
            DungeonLobbyMember.character_id == character.id,
            DungeonLobbyMember.status.in_(("invited", "joined", "queued", "matched", "confirmed")),
        )
        if allowed_lobby_id is not None:
            lobby_membership = lobby_membership.where(
                DungeonLobbyMember.lobby_id != allowed_lobby_id
            )
        open_member = await session.scalar(lobby_membership)
        if open_member is not None:
            return "foreground"
        return None

    async def _new_lobby_foreground(self, session, character, family, lobby_id, version):
        activity = GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=f"dungeon_lobby_{lobby_id.hex}",
            status="active",
            state_version=version,
            ruleset_version=family.ruleset_version,
            last_valid_action_at=datetime.now(UTC),
        )
        session.add(activity)
        await session.flush()
        return activity.id

    async def _lobby_view(
        self, session, character, lobby, member, *, kind=None, reason=None, invite_id=None
    ):
        if lobby is None:
            return self._view(character, kind="stale")
        rows = (
            await session.execute(
                select(DungeonLobbyMember, Character)
                .join(Character, Character.id == DungeonLobbyMember.character_id)
                .where(
                    DungeonLobbyMember.lobby_id == lobby.id,
                    DungeonLobbyMember.status.in_({"joined", "queued", "matched", "confirmed"}),
                )
                .order_by(DungeonLobbyMember.position)
            )
        ).all()
        party_members = tuple(
            (
                member_character.name,
                member_character.level,
                D(member_character.hp),
                D(member_character.max_hp),
                member_character.vigor,
                lobby_member.status,
            )
            for lobby_member, member_character in rows
        )
        if kind is None:
            kind = (
                "confirming"
                if lobby.status == "confirming"
                else ("queue" if lobby.mode == "matchmaking" else "lobby")
            )
        view = self._view(
            character,
            kind=kind,
            family_id=lobby.dungeon_family_id,
            reason=reason,
            activity_id=member.foreground_activity_id if member is not None else None,
            lobby_id=lobby.id,
            lobby_mode=lobby.mode,
            party_members=party_members,
            lobby_version=lobby.state_version,
            invite_id=invite_id,
        )
        return replace(
            view,
            difficulty=lobby.difficulty,
            difficulty_label=DIFFICULTIES[lobby.difficulty].label,
            lobby_leader=lobby.leader_character_id == character.id,
            lobby_member_status=member.status if member is not None else None,
        )

    async def _view_for_lobby(self, session, character, lobby_id, *, kind="stale"):
        lobby = await session.get(DungeonLobby, lobby_id) if lobby_id else None
        return await self._lobby_view(session, character, lobby, None, kind=kind)

    async def _finish_lobby_foreground(self, session, lobby_member):
        if lobby_member.foreground_activity_id is None:
            return
        activity = await session.get(GameActivity, lobby_member.foreground_activity_id)
        if activity is not None and activity.status == "active":
            activity.status = "failed"

    async def _cancel_lobby(self, session, lobby, *, expired=False):
        if lobby.status not in {"forming", "confirming"}:
            return
        lobby.status = "expired" if expired else "cancelled"
        lobby.state_version += 1
        members = (
            await session.scalars(
                select(DungeonLobbyMember)
                .where(DungeonLobbyMember.lobby_id == lobby.id)
                .with_for_update()
            )
        ).all()
        for member in members:
            if member.status not in {"left", "declined"}:
                member.status = "left"
            await self._finish_lobby_foreground(session, member)
        invites = (
            await session.scalars(
                select(DungeonInvite).where(
                    DungeonInvite.lobby_id == lobby.id,
                    DungeonInvite.status == "pending",
                )
            )
        ).all()
        for invite in invites:
            invite.status = "expired" if expired else "cancelled"
            invite.state_version += 1
        queue_rows = (
            await session.scalars(
                select(DungeonMatchQueue).where(DungeonMatchQueue.lobby_id == lobby.id)
            )
        ).all()
        for queue_row in queue_rows:
            if queue_row.status in {"queued", "matched"}:
                queue_row.status = "expired" if expired else "cancelled"

    async def _materialize_lobby_run(self, session, lobby, lobby_members):
        family = DUNGEON_FAMILIES.get(lobby.dungeon_family_id)
        if family is None or not 2 <= len(lobby_members) <= 4:
            return None
        character_ids = sorted((row.character_id for row in lobby_members), key=str)
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
        by_id = {row.id: row for row in characters}
        if len(by_id) != len(character_ids):
            return None
        ordered_members = sorted(lobby_members, key=lambda row: row.position)
        for lobby_member in ordered_members:
            character = by_id[lobby_member.character_id]
            reason = await self._eligibility_reason(
                session,
                character,
                family,
                lobby.difficulty,
                allowed_activity_id=lobby_member.foreground_activity_id,
                allowed_lobby_id=lobby.id,
            )
            if reason or lobby_member.status != "confirmed":
                return None
        shell_ids = [row.foreground_activity_id for row in ordered_members]
        shells = (
            await session.scalars(
                select(GameActivity)
                .where(
                    GameActivity.id.in_(shell_ids),
                    GameActivity.status == "active",
                )
                .order_by(GameActivity.id)
                .with_for_update()
            )
        ).all()
        shell_by_id = {row.id: row for row in shells}
        if len(shell_by_id) != len(shell_ids):
            return None
        configs = {}
        for lobby_member in ordered_members:
            character = by_id[lobby_member.character_id]
            equipment = await load_equipment_configuration(session, character)
            reconcile_character_hp(character, equipment)
            arts = await load_active_art_configuration(session, character)
            configs[character.id] = equipment.to_data(RULESET) | arts.to_data()
        run_id = uuid4()
        seed = uuid4().hex
        now = datetime.now(UTC)
        profile = DIFFICULTIES[lobby.difficulty]
        run = DungeonRun(
            id=run_id,
            dungeon_family_id=family.family_id,
            difficulty=lobby.difficulty,
            status="active",
            ruleset_version=family.ruleset_version,
            content_version=family.content_version,
            reference_level=(
                family.reference_level if lobby.difficulty != "rupture" else profile.reference_level
            ),
            initial_group_size=len(ordered_members),
            current_encounter_ordinal=1,
            state_version=0,
            seed=seed,
            has_brazier=roll_brazier(seed, lobby.difficulty),
            brazier_activated=False,
            brazier_after_encounter=3,
            active_checkpoint_encounter=None,
            progress={"internal_xp": 0, "retry_available": False, "family_id": family.family_id},
            created_at=now,
            last_activity_at=now,
        )
        session.add(run)
        for position, lobby_member in enumerate(ordered_members, 1):
            character = by_id[lobby_member.character_id]
            shell = shell_by_id[lobby_member.foreground_activity_id]
            character.vigor -= profile.vigor
            shell.content_id = f"{DUNGEON_ACTIVITY_PREFIX}{run_id.hex}"
            shell.state_version = run.state_version
            shell.ruleset_version = family.ruleset_version
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id).with_for_update()
            )
            if world is not None:
                world.region = REGION
                world.location = family.name
            session.add(
                DungeonRunMember(
                    run_id=run_id,
                    foreground_activity_id=lobby_member.foreground_activity_id,
                    character_id=character.id,
                    position=position,
                    status="active",
                    vigor_reserved=profile.vigor,
                    vigor_refunded=False,
                    consumable_uses=0,
                    combat_configuration=configs[character.id],
                    hp=character.hp,
                    max_hp=character.max_hp,
                    run_state={},
                    contribution={},
                )
            )
            await self._ensure_codex_entry(session, character.id, family.codex_entry)
        session.add_all(
            DungeonRunEncounter(
                run_id=run_id,
                encounter_ordinal=ordinal,
                definition_id=(
                    CRYPT_ENCOUNTERS[ordinal].definition_id
                    if family.family_id == CRYPT_FAMILY_ID
                    else f"galleries.encounter.{ordinal}"
                ),
                status="pending",
                activity_id=None,
                attempt_count=0,
                progress={},
                reward_settled=False,
            )
            for ordinal in range(1, 6)
        )
        await session.flush()
        return run

    async def _create_lobby_activity(self, session, character, run):
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(
                    DungeonRunMember.run_id == run.id,
                    DungeonRunMember.status.in_(("active", "defeated")),
                )
                .order_by(DungeonRunMember.position)
                .with_for_update()
            )
        ).all()
        for member in members:
            old = await session.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == member.character_id,
                    GameActivity.status == "active",
                )
            )
            if old is not None:
                old.status = "completed"
            activity = GameActivity(
                id=uuid4(),
                character_id=member.character_id,
                content_id=f"{DUNGEON_ACTIVITY_PREFIX}{run.id.hex}",
                status="active",
                state_version=run.state_version,
                ruleset_version=_family(run.dungeon_family_id).ruleset_version,
                last_valid_action_at=datetime.now(UTC),
            )
            session.add(activity)
            await session.flush()
            member.foreground_activity_id = activity.id
        await session.flush()

    async def _run_view(
        self,
        session,
        character,
        run,
        member,
        *,
        activity=None,
        combat=None,
        record=None,
        encounter=None,
        kind=None,
    ):
        member_activity = (
            await session.get(GameActivity, member.foreground_activity_id)
            if member is not None and member.foreground_activity_id is not None
            else None
        )
        if member_activity is None or member_activity.status != "active":
            member_activity = await self._active_activity(session, character.id)
        activity = member_activity
        encounter = encounter or await session.scalar(
            select(DungeonRunEncounter).where(
                DungeonRunEncounter.run_id == run.id,
                DungeonRunEncounter.encounter_ordinal == run.current_encounter_ordinal,
            )
        )
        canonical_activity = None
        if encounter is not None and encounter.activity_id is not None:
            canonical_activity = await session.get(GameActivity, encounter.activity_id)
        if (
            combat is None
            and encounter is not None
            and encounter.status == "active"
            and canonical_activity is not None
            and canonical_activity.status == "active"
        ):
            _, record = await CombatRepository(session).combat(canonical_activity)
            combat = decode(
                record.snapshot,
                record.id,
                canonical_activity.ruleset_version,
                canonical_activity.state_version,
            )
        if combat is not None and activity is not None:
            quantities = tuple(
                (row.consumable_id, row.quantity)
                for row in (
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
            remaining = max(
                0, DIFFICULTIES[run.difficulty].consumable_limit - member.consumable_uses
            )
            actor_key = (
                f"member_{member.position}"
                if run.initial_group_size > 1 and member.status == "active"
                else "player"
                if run.initial_group_size == 1 and member.status == "active"
                else None
            )
            options = combat_consumable_options(
                combat,
                tuple(item for item, _ in quantities),
                budget_limit=remaining,
                actor_key=actor_key,
            )
            return self._view(
                character,
                kind=kind or "combat",
                run=run,
                member=member,
                activity_id=activity.id,
                encounter_id=record.id if record is not None else None,
                combat=combat,
                consumable_options=options,
                consumable_quantities=quantities,
                consumable_budget_limit=remaining,
                family_id=run.dungeon_family_id,
                combat_actor_key=actor_key,
                member_status=member.status if member is not None else None,
            )
        if kind is None:
            progress = run.progress or {}
            if run.status == "completed":
                kind = "completed"
            elif run.status in {"failed", "expired"}:
                kind = run.status
            elif progress.get("awaiting_brazier"):
                kind = "brazier"
            elif progress.get("retry_available"):
                kind = "retry"
            elif member is not None and member.status == "defeated":
                kind = "spectating"
            else:
                kind = "ready"
        return self._view(character, kind=kind, run=run, member=member)

    def _view(
        self,
        character,
        *,
        kind,
        run=None,
        member=None,
        difficulty_gates=(),
        reason=None,
        activity_id=None,
        encounter_id=None,
        combat=None,
        consumable_options=(),
        consumable_quantities=(),
        consumable_budget_limit=0,
        family_id=CRYPT_FAMILY_ID,
        known_dungeons=(),
        lobby_id=None,
        lobby_mode=None,
        party_members=(),
        combat_actor_key=None,
        lobby_version=0,
        invite_id=None,
        member_status=None,
    ):
        ordinal = run.current_encounter_ordinal if run is not None else 0
        family_id = run.dungeon_family_id if run is not None else family_id
        family = _family(family_id)
        environment = (
            _encounter_environment(family_id, ordinal)
            if ordinal and ordinal <= _encounter_count(family_id)
            else ""
        )
        progress = run.progress or {} if run is not None else {}
        member_key = str(character.id)
        member_reward_lines = progress.get("reward_lines_by_character", {}).get(
            member_key, progress.get("reward_lines", ())
        )
        member_first_clear = progress.get("first_clear_by_character", {}).get(
            member_key, progress.get("first_clear", False)
        )
        return DungeonView(
            kind=kind,
            character_id=character.id,
            character_name=character.name,
            level=character.level,
            location=(
                family.name if run is not None and run.status == "active" else self._location(None)
            ),
            hp=D(character.hp),
            max_hp=D(character.max_hp),
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            run_id=run.id if run is not None else None,
            state_version=run.state_version if run is not None else 0,
            difficulty=run.difficulty if run is not None else None,
            difficulty_label=DIFFICULTIES[run.difficulty].label if run is not None else None,
            difficulty_gates=tuple(difficulty_gates),
            ordinal=ordinal,
            environment=environment,
            has_brazier=run.has_brazier if run is not None and ordinal >= 4 else None,
            brazier_activated=run.brazier_activated if run is not None else False,
            consumable_uses=member.consumable_uses if member is not None else 0,
            consumable_limit=DIFFICULTIES[run.difficulty].consumable_limit
            if run is not None
            else 0,
            activity_id=activity_id,
            encounter_id=encounter_id,
            combat=combat,
            context="dungeon",
            stage="dungeon",
            xp=character.xp,
            consumable_options=tuple(consumable_options),
            consumable_quantities=tuple(consumable_quantities),
            consumable_budget_limit=consumable_budget_limit,
            reward_lines=tuple(member_reward_lines),
            first_clear=bool(member_first_clear),
            reason=reason,
            family_id=family.family_id,
            dungeon_name=family.name,
            range_label=family.range_label,
            entry_display=family.entry_display,
            known_dungeons=tuple(known_dungeons),
            lobby_id=lobby_id,
            lobby_mode=lobby_mode,
            party_members=tuple(party_members),
            combat_actor_key=combat_actor_key,
            lobby_version=lobby_version,
            invite_id=invite_id,
            member_status=member_status,
        )

    @staticmethod
    def _location(_world):
        return "Charneca da Fuligem"

    @staticmethod
    def _expired(run) -> bool:
        now = datetime.now(UTC)
        return (
            now - run.last_activity_at >= DUNGEON_IDLE_LIMIT
            or now - run.created_at >= DUNGEON_ABSOLUTE_LIMIT
        )

    async def _expire(self, session, character, run, member):
        members = (
            await session.scalars(
                select(DungeonRunMember)
                .where(DungeonRunMember.run_id == run.id)
                .order_by(DungeonRunMember.position)
                .with_for_update()
            )
        ).all()
        characters = (
            await session.scalars(
                select(Character)
                .where(Character.id.in_([row.character_id for row in members]))
                .order_by(Character.id)
                .with_for_update()
            )
        ).all()
        character_by_id = {row.id: row for row in characters}
        run.status = "expired"
        run.expired_at = datetime.now(UTC)
        run.state_version += 1
        run.progress = {**(run.progress or {}), "internal_xp": 0, "expired": True}
        for run_member in members:
            if run_member.status == "left":
                continue
            run_member.status = "left"
            await self._refund_vigor(session, character_by_id[run_member.character_id], run_member)
            shell = await session.get(GameActivity, run_member.foreground_activity_id)
            if shell is not None and shell.status == "active":
                shell.status = "failed"
            await self._return_to_entry(session, run_member.character_id, run.dungeon_family_id)

    async def _refund_vigor(self, session, character, member):
        if member.vigor_refunded or member.vigor_reserved <= 0:
            return
        now = utcnow()
        await reconcile_character_vigor(session, character, now=now)
        add_vigor_state(character, member.vigor_reserved, now=now)
        member.vigor_refunded = True
        member.vigor_reserved = 0

    async def _active_run(self, session, character_id, *, run_id=None, lock=False):
        statement = (
            select(DungeonRun)
            .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
            .where(
                DungeonRunMember.character_id == character_id,
                DungeonRunMember.status.in_(("active", "defeated")),
                DungeonRun.status == "active",
            )
            .order_by(DungeonRun.created_at.desc())
            .limit(1)
        )
        if run_id is not None:
            statement = statement.where(DungeonRun.id == run_id)
        if lock:
            statement = statement.with_for_update(of=DungeonRun)
        run = await session.scalar(statement)
        if run is None:
            return None, None
        member_statement = select(DungeonRunMember).where(
            DungeonRunMember.run_id == run.id,
            DungeonRunMember.character_id == character_id,
        )
        if lock:
            member_statement = member_statement.with_for_update()
        member = await session.scalar(member_statement)
        return run, member

    async def _active_activity(self, session, character_id):
        return await session.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == character_id, GameActivity.status == "active")
            .with_for_update()
        )

    async def _locked_character(self, session, actor):
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is not None:
            await reconcile_character_vigor(session, character)
        return character

    async def _character(self, session, actor):
        return await self._locked_character(session, actor)

    async def _has_unlock(self, session, character_id, unlock_id):
        return (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
                )
            )
            is not None
        )

    async def _ensure_unlock(self, session, character_id, unlock_id):
        existing = await session.scalar(
            select(Unlock)
            .where(Unlock.character_id == character_id, Unlock.unlock_id == unlock_id)
            .with_for_update()
        )
        if existing is None:
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))
            await session.flush()
            return True
        return False

    async def _ensure_codex_entry(self, session, character_id, entry_id):
        existing = await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character_id, CodexEntry.entry_id == entry_id
            )
        )
        if existing is None:
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))
            await session.flush()

    async def _ensure_fragment(self, session, character_id, entry_id, fragment_id):
        existing = await session.scalar(
            select(CodexFragment).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == fragment_id,
            )
        )
        if existing is None:
            session.add(
                CodexFragment(character_id=character_id, entry_id=entry_id, fragment_id=fragment_id)
            )
            await session.flush()

    async def _return_to_charneca(self, session, character_id):
        await self._return_to_entry(session, character_id, CRYPT_FAMILY_ID)

    async def _return_to_entry(self, session, character_id, family_id):
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )
        if world is not None:
            world.region = REGION
            world.location = _family(family_id).entry_location

    @staticmethod
    def _view_base(character, kind):
        return DungeonView(
            kind=kind,
            character_id=character.id,
            character_name=character.name,
            level=character.level,
            location=CHARNECA,
            hp=D(character.hp),
            max_hp=D(character.max_hp),
            vigor=character.vigor,
            max_vigor=character.max_vigor,
            xp=character.xp,
        )

    async def consume_for_activity(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        item_id: str,
        target_id: str,
        effect_id: str | None,
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            run, _member = await self._active_run(session, character.id)
            if run is None:
                return None
            owns_activity = await session.scalar(
                select(DungeonRunEncounter.run_id).where(
                    DungeonRunEncounter.run_id == run.id,
                    DungeonRunEncounter.activity_id == activity_id,
                )
            )
            if owns_activity is None:
                return None
        return await self.action(
            actor,
            run.id,
            activity_id,
            version,
            "consumable",
            target_id,
            consumable_id=item_id,
            effect_id=effect_id,
        )

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
    ) -> DungeonView | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            run, member = await self._active_run(session, character.id, lock=True)
            if run is None:
                return None
            activity = await self._active_activity(session, character.id)
            if activity is None or activity.id != activity_id:
                return await self._run_view(session, character, run, member, activity=activity)
            current = await self._run_view(session, character, run, member, activity=activity)
            if activity.state_version != version:
                return replace(
                    current, consumable_notice="⚠️ Consumível · A tela ficou desatualizada."
                )
            if screen == "combat":
                return current
            if screen == "items":
                return (
                    replace(current, consumable_screen="items")
                    if current.consumable_options
                    else current
                )
            item = consumable_definition(item_id or "")
            options = tuple(
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not options:
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice="⚠️ Consumível · Não está disponível.",
                )
            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(dict.fromkeys(option.target_id for option in options))
                    if len(target_ids) > 1:
                        return replace(
                            current, consumable_screen="targets", selected_consumable_id=item.id
                        )
                    target_id = target_ids[0] if target_ids else None
                    parent = "items"
                else:
                    target_id = "player"
                    parent = "items"
                selected = tuple(option for option in options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )
            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )
            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(dict.fromkeys(option.target_id for option in options))
                return (
                    replace(current, consumable_screen="targets", selected_consumable_id=item.id)
                    if len(target_ids) > 1
                    else replace(current, consumable_screen="items")
                )
            if screen == "effects" and target_id is not None:
                selected = tuple(
                    option
                    for option in options
                    if option.target_id == target_id and option.effect_id is not None
                )
                if len(selected) == 1:
                    return replace(current, ready_consumable_option=selected[0])
                return replace(
                    current,
                    consumable_screen="effects",
                    selected_consumable_id=item.id,
                    selected_target_id=target_id,
                    selection_parent=parent,
                )
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if not selected:
            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Sem alvo válido.",
            )
        if len(selected) == 1:
            return replace(current, ready_consumable_option=selected[0])
        return replace(
            current,
            consumable_screen="effects",
            selected_consumable_id=item.id,
            selected_target_id=target_id,
            selection_parent=parent,
        )

    async def consume(
        self,
        actor: int,
        run_id: UUID,
        activity_id: UUID,
        version: int,
        item_id: str,
        target_id: str,
        effect_id: str | None = None,
    ) -> DungeonView | None:
        return await self.action(
            actor,
            run_id,
            activity_id,
            version,
            "consumable",
            target_id,
            consumable_id=item_id,
            effect_id=effect_id,
        )
