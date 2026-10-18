"""Persistent campaign progression for the Altos Cinéreos opening mission."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import (
    CampaignRosterMember,
    campaign_action_intent,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
    settle_campaign_encounter,
)
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.groups import ActivityEligibility, GroupError, GroupService
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_BASTILHA_LABEL,
    ALTOS_ESCARPA_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    RoadService,
)
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    current_combat,
    derive_consumable_selection,
    normalize_character_hp,
)
from asterion.domain.combat import Combat, active_player_key
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.creation import RULESET as CHARACTER_RULESET
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_ABRIGO_BRAZIER,
    ALTOS_ABRIGO_LOCATION,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_BASTILHA_EXPLORE_UNLOCK,
    ALTOS_BASTILHA_HUNT_UNLOCK,
    ALTOS_BASTILHA_LOCATION,
    ALTOS_CINZA_BASALTO,
    ALTOS_COURO_ESCARPA,
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_ESCARPA_BRAZIER,
    ALTOS_ESCARPA_EXPLORE_UNLOCK,
    ALTOS_ESCARPA_HUNT_UNLOCK,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LOBO_ESCARPA,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
    ALTOS_PEDREIRAS_HUNT_UNLOCK,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PONTES_EXPLORE_UNLOCK,
    ALTOS_PONTES_HUNT_UNLOCK,
    ALTOS_PONTES_LOCATION,
    ALTOS_REGION,
    ALTOS_VIGIA_CARGA,
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
    materialize_equipment,
)
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    EquipmentItem,
    GameActivity,
    GroupActivityParticipant,
    GroupActivityProposal,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    Unlock,
    WorldState,
)

P25_ID = "P25"
P25_MISSION_ID = "mission.altos.p25"
P25_TITLE = "O Peso Antigo"
P25_CONTENT_VERSION = "altos-1.0.1"
P25_CHECKPOINT = "p25.o_peso_antigo"
P25_CONTENT_ID = P25_MISSION_ID
P25_REWARD_SOURCE = P25_MISSION_ID
P25_CODEX_ENTRY = "codex.altos.infraestrutura_sustentacao"
P25_REGION_CODEX = "codex.altos.regiao"
P25_NARRATIVE_UNLOCK = "narrative.altos.infraestrutura_reconhecida"
P25_ACHIEVEMENT = "achievement.altos.peso_antigo"
P26_ID = "P26"
P26_MISSION_ID = "mission.altos.p26"
P26_TITLE = "Ordens de Emergência"
P26_CONTENT_VERSION = "altos-1.0.1"
P26_REWARD_SOURCE = P26_MISSION_ID
P26_CODEX_ENTRY = "codex.altos.regencia_continuidade"
P26_NARRATIVE_UNLOCK = "narrative.altos.regencia_identificada"
P26_ACHIEVEMENT = "achievement.altos.ordens_emergencia"
P27_ID = "P27"
P27_MISSION_ID = "mission.altos.p27"
P27_TITLE = "A Continuidade a Qualquer Custo"
P27_CONTENT_VERSION = "altos-1.0.1"
P27_CHECKPOINT = "p27.a_continuidade_a_qualquer_custo"
P27_CONTENT_ID = P27_MISSION_ID
P27_REWARD_SOURCE = P27_MISSION_ID
P27_CODEX_ENTRY = "codex.altos.prioridades_carga"
P27_NARRATIVE_UNLOCK = "narrative.altos.prioridades_confirmadas"
P27_ACHIEVEMENT = "achievement.altos.continuidade_custo"
P28_ID = "P28"
P28_MISSION_ID = "mission.altos.p28"
P28_TITLE = "Os Desvelados"
P28_CONTENT_VERSION = "altos-1.0.1"
P28_CHECKPOINT = "p28.os_desvelados"
P28_CONTENT_ID = P28_MISSION_ID
P28_REWARD_SOURCE = P28_MISSION_ID
P28_CODEX_ENTRY = "codex.altos.desvelados_origem"
P28_NARRATIVE_UNLOCK = "narrative.altos.desvelados_contextualizados"
P28_ACHIEVEMENT = "achievement.altos.desvelados"
P27_REWARD_OPTIONS = {
    "capuz_vento_preso": (
        "equipment.altos.campaign.p27.capuz_vento_preso",
        "Capuz do Vento Preso",
        "Cabeça",
    ),
    "selo_carga_compartilhada": (
        "equipment.altos.campaign.p27.selo_carga_compartilhada",
        "Selo da Carga Compartilhada",
        "Acessório",
    ),
    "relicario_peso_distribuido": (
        "equipment.altos.campaign.p27.relicario_peso_distribuido",
        "Relicário do Peso Distribuído",
        "Artefato",
    ),
}
P25_COMBAT = {
    P25_ID: (P25_CONTENT_ID, P25_CHECKPOINT, ALTOS_ESCARPA_LABEL, ALTOS_LOBO_ESCARPA, 41, "common"),
    P27_ID: (
        P27_CONTENT_ID,
        P27_CHECKPOINT,
        ALTOS_PEDREIRAS_LABEL,
        "creature.altos.carcaca_mineral",
        45,
        "uncommon",
    ),
    P28_ID: (
        P28_CONTENT_ID,
        P28_CHECKPOINT,
        ALTOS_BASTILHA_LABEL,
        ALTOS_VIGIA_CARGA,
        47,
        "uncommon",
    ),
}


def _scripted_combat_step(quest_id: str) -> int:
    return 4 if quest_id == P28_ID else 3


@dataclass(frozen=True, slots=True)
class AltosMissionView:
    character_id: UUID
    quest_id: str
    title: str
    kind: str
    status: str
    step: int
    state_version: int
    progress: dict
    location: str
    level: int
    combat: Combat | None = None
    activity_id: UUID | None = None
    encounter_id: UUID | None = None
    combat_actor_key: str | None = None
    group_size: int = 1
    consumable_options: tuple = ()
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    consumable_quantities: tuple = ()
    consumable_budget_limit: int = 0
    ready_consumable_option: object | None = None
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class AltosMissionService:
    """Persistent mission progression for the Altos Cinéreos campaign."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        self.road = RoadService(sessions, server_id)

    async def on_location(self, actor: int) -> None:
        """Commit Altos location discovery and shared campaign arrivals."""
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None or world.region != ALTOS_REGION:
                return
            if world.location == ALTOS_ESCARPA_LABEL:
                await self._enter_escarpa(session, character, world)
                return
            if world.location == ALTOS_PONTES_LABEL:
                await self._enter_pontes(session, character_ids)
                return
            if world.location == ALTOS_PEDREIRAS_LABEL:
                await self._enter_pedreiras(session, character_ids)
                return
            if world.location == ALTOS_BASTILHA_LABEL:
                await self._enter_bastilha(session, character_ids)
                return
            if world.location != ALTOS_ABRIGO_LABEL:
                return
            members = await present_campaign_members(
                session,
                character_ids=character_ids,
                quest_id=P25_ID,
                content_version=P25_CONTENT_VERSION,
                step=6,
                region=ALTOS_REGION,
                location=ALTOS_ABRIGO_LABEL,
            )
            for member in members:
                await self._ensure(
                    session,
                    Unlock,
                    character_id=member.character.id,
                    unlock_id=ALTOS_ABRIGO_ACCESS_UNLOCK,
                )
                await self._ensure(
                    session,
                    LocationDiscovery,
                    character_id=member.character.id,
                    location_id=ALTOS_ABRIGO_LOCATION,
                )
                member.quest.step = 7
                member.quest.state_version += 1
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "entered_abrigo": True,
                }
                await self._credit(
                    session,
                    member.character.id,
                    "p25.abrigo_arrival",
                    f"p25.abrigo_arrival:{member.character.id}",
                    {"location": ALTOS_ABRIGO_LABEL},
                )

    async def _enter_pontes(self, session, character_ids) -> None:
        members = await self._present_p26(
            session, character_ids, 2, ALTOS_PONTES_LABEL
        )
        for member in members:
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=ALTOS_PONTES_LOCATION,
            )
            member.quest.step = 3
            member.quest.state_version += 1
            member.quest.progress = {
                **(member.quest.progress or {}),
                "pontes_discovered": True,
            }
            await self._credit_p26(
                session,
                member.character.id,
                "p26.discovered_pontes",
                f"p26.discovered_pontes:{member.character.id}",
                {"location": ALTOS_PONTES_LOCATION},
            )

    async def _enter_pedreiras(self, session, character_ids) -> None:
        members = await self._present_p27(
            session, character_ids, 1, ALTOS_PEDREIRAS_LABEL
        )
        for member in members:
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=ALTOS_PEDREIRAS_LOCATION,
            )
            member.quest.step = 2
            member.quest.state_version += 1
            member.quest.progress = {
                **(member.quest.progress or {}),
                "pedreiras_discovered": True,
            }
            await self._credit_p27(
                session,
                member.character.id,
                "p27.discovered_pedreiras",
                f"p27.discovered_pedreiras:{member.character.id}",
                {"location": ALTOS_PEDREIRAS_LOCATION},
            )

    async def _enter_bastilha(self, session, character_ids) -> None:
        members = await self._present_p28(
            session, character_ids, 1, ALTOS_BASTILHA_LABEL
        )
        for member in members:
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=ALTOS_BASTILHA_LOCATION,
            )
            member.quest.step = 2
            member.quest.state_version += 1
            member.quest.progress = {
                **(member.quest.progress or {}),
                "bastilha_discovered": True,
            }
            await self._credit_p28(
                session,
                member.character.id,
                "p28.discovered_bastilha",
                f"p28.discovered_bastilha:{member.character.id}",
                {"location": ALTOS_BASTILHA_LOCATION},
            )

    async def _enter_escarpa(self, session, character, world) -> None:
        if character.level < 41 or not await self._quest_completed(
            session, character.id, "P24"
        ):
            return
        quest = await self._quest(session, character.id, P25_ID)
        if quest is not None:
            return
        if await self._foreground(session, character.id):
            return
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=ALTOS_ESCARPA_ACCESS_UNLOCK,
        )
        await self._ensure(
            session,
            LocationDiscovery,
            character_id=character.id,
            location_id=ALTOS_ESCARPA_LOCATION,
        )
        quest = Quest(
            character_id=character.id,
            quest_id=P25_ID,
            title=P25_TITLE,
            status="active",
            step=2,
            content_version=P25_CONTENT_VERSION,
            state_version=0,
            progress={"entered_escarpa": True, "support_points": []},
        )
        session.add(quest)
        await session.flush()
        await self._credit(
            session,
            character.id,
            "p25.entered_escarpa",
            f"p25.entered_escarpa:{character.id}",
            {"location": world.location, "level": character.level},
        )

    async def resume_active(self, actor: int) -> AltosMissionView | None:
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id, lock=False)
            p28 = await self._quest(session, character.id, P28_ID, lock=False)
            if p28 is not None:
                return await self._view(session, character, p28, world)
            p27 = await self._quest(session, character.id, P27_ID, lock=False)
            if p27 is not None and p27.status == "active":
                return await self._view(session, character, p27, world)
            if (
                p27 is not None
                and p27.status == "completed"
                and world is not None
                and world.location == ALTOS_PEDREIRAS_LABEL
            ):
                status = "available" if character.level >= 47 else "suspended"
                return self._p28_offer_view(character, world, status)
            if p27 is not None and p27.status == "completed":
                return await self._view(session, character, p27, world)
            p26 = await self._quest(session, character.id, P26_ID, lock=False)
            if p26 is not None:
                if (
                    p26.status == "completed"
                    and world is not None
                    and world.location == ALTOS_ABRIGO_LABEL
                ):
                    status = "available" if character.level >= 45 else "suspended"
                    return self._p27_offer_view(character, world, status)
                return self._p26_view(character, p26, world)
            p25 = await self._quest(session, character.id, P25_ID, lock=False)
            if p25 is not None and p25.status == "active":
                if p25.content_version != P25_CONTENT_VERSION:
                    return None
                return await self._view(session, character, p25, world)
            if (
                p25 is not None
                and p25.status == "completed"
                and world is not None
                and world.location == ALTOS_ABRIGO_LABEL
            ):
                status = "available" if character.level >= 43 else "suspended"
                return self._p26_offer_view(character, world, status)
            if p25 is None or p25.content_version != P25_CONTENT_VERSION:
                return None
            return await self._view(session, character, p25, world)

    async def resume(
        self, actor: int, quest_id: str | None = None
    ) -> AltosMissionView | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            if quest_id is None:
                p28 = await self._quest(session, character.id, P28_ID, lock=False)
                p27 = await self._quest(session, character.id, P27_ID, lock=False)
                p26 = await self._quest(session, character.id, P26_ID, lock=False)
                quest_id = (
                    P28_ID if p28 is not None
                    else P27_ID if p27 is not None and p27.status == "active"
                    else P25_ID
                )
                if p26 is not None and p26.status == "active" and p27 is None:
                    return self._p26_view(
                        character, p26, await self._world(session, character.id, lock=False)
                    )
            quest = await self._quest(session, character.id, quest_id, lock=False)
            if quest is None or quest.content_version != P25_CONTENT_VERSION:
                return None
            world = await self._world(session, character.id, lock=False)
            return await self._view(session, character, quest, world)

    async def available(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or character.level < 41:
                return False
            return await self._quest_completed(session, character.id, "P24")

    async def known_locations(self, actor: int) -> set[str]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return set()
            found = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character.id,
                            LocationDiscovery.location_id.in_(
                                (
                                    ALTOS_ESCARPA_LOCATION,
                                    ALTOS_ABRIGO_LOCATION,
                                    ALTOS_PONTES_LOCATION,
                                    ALTOS_PEDREIRAS_LOCATION,
                                    ALTOS_BASTILHA_LOCATION,
                                )
                            ),
                        )
                    )
                ).all()
            )
            return {
                label
                for location_id, label in (
                    (ALTOS_ESCARPA_LOCATION, ALTOS_ESCARPA_LABEL),
                    (ALTOS_ABRIGO_LOCATION, ALTOS_ABRIGO_LABEL),
                    (ALTOS_PONTES_LOCATION, ALTOS_PONTES_LABEL),
                    (ALTOS_PEDREIRAS_LOCATION, ALTOS_PEDREIRAS_LABEL),
                    (ALTOS_BASTILHA_LOCATION, ALTOS_BASTILHA_LABEL),
                )
                if location_id in found
            }

    async def start_p26(self, actor: int, version: int = 0) -> AltosMissionView | None:
        await self.on_location(actor)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None:
                return None
            existing = await self._quest(session, character.id, P26_ID)
            if existing is not None:
                return self._p26_view(character, existing, world)
            p25 = await self._quest(session, character.id, P25_ID)
            if (
                p25 is None
                or p25.status != "completed"
                or p25.content_version != P25_CONTENT_VERSION
                or world.region != ALTOS_REGION
                or world.location != ALTOS_ABRIGO_LABEL
            ):
                return None
            if character.level < 43:
                return self._p26_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p26_offer_view(character, world, "available")

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ALTOS_PONTES_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P26_ID,
                title=P26_TITLE,
                status="active",
                step=2,
                content_version=P26_CONTENT_VERSION,
                state_version=1,
                progress={"order_received": True},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p26(
                session,
                character.id,
                "p26.received_order",
                f"p26.received_order:{character.id}",
                {"giver": "Sel Ardan", "mission_id": P26_MISSION_ID},
            )
            return self._p26_view(character, quest, world)

    def _p26_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P26_ID,
            title=P26_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location,
            level=character.level,
        )

    def _p26_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=quest.quest_id,
            title=quest.title,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else ALTOS_ABRIGO_LABEL,
            level=character.level,
        )

    async def start_p27(self, actor: int, version: int = 0) -> AltosMissionView | None:
        await self.on_location(actor)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None:
                return None
            existing = await self._quest(session, character.id, P27_ID)
            if existing is not None:
                return self._p27_view(character, existing, world)
            p26 = await self._quest(session, character.id, P26_ID)
            if (
                p26 is None
                or p26.status != "completed"
                or p26.content_version != P26_CONTENT_VERSION
                or world.region != ALTOS_REGION
                or world.location != ALTOS_ABRIGO_LABEL
            ):
                return None
            if character.level < 45:
                return self._p27_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p27_offer_view(character, world, "available")

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ALTOS_PEDREIRAS_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P27_ID,
                title=P27_TITLE,
                status="active",
                step=1,
                content_version=P27_CONTENT_VERSION,
                state_version=1,
                progress={"activated": True},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p27(
                session,
                character.id,
                "p27.activated",
                f"p27.activated:{character.id}",
                {"givers": ("Doren Vask", "Rava Kern"), "mission_id": P27_MISSION_ID},
            )
            return self._p27_view(character, quest, world)

    def _p27_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P27_ID,
            title=P27_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location,
            level=character.level,
        )

    def _p27_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=quest.quest_id,
            title=quest.title,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else ALTOS_ABRIGO_LABEL,
            level=character.level,
        )

    async def start_p28(self, actor: int, version: int = 0) -> AltosMissionView | None:
        await self.on_location(actor)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None:
                return None
            existing = await self._quest(session, character.id, P28_ID)
            if existing is not None:
                return self._p28_view(character, existing, world)
            p27 = await self._quest(session, character.id, P27_ID)
            if (
                p27 is None
                or p27.status != "completed"
                or p27.content_version != P27_CONTENT_VERSION
                or world.region != ALTOS_REGION
                or world.location != ALTOS_PEDREIRAS_LABEL
            ):
                return None
            if character.level < 47:
                return self._p28_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p28_offer_view(character, world, "available")

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=ALTOS_BASTILHA_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P28_ID,
                title=P28_TITLE,
                status="active",
                step=1,
                content_version=P28_CONTENT_VERSION,
                state_version=1,
                progress={"activated": True},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p28(
                session,
                character.id,
                "p28.activated",
                f"p28.activated:{character.id}",
                {"givers": ("Sel Ardan", "Maro Keln"), "mission_id": P28_MISSION_ID},
            )
            return self._p28_view(character, quest, world)

    def _p28_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P28_ID,
            title=P28_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location,
            level=character.level,
        )

    def _p28_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=quest.quest_id,
            title=quest.title,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else ALTOS_PEDREIRAS_LABEL,
            level=character.level,
        )

    async def _advance_p28(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P28_CONTENT_VERSION
            or quest.state_version != version
            or await self._foreground(session, character.id)
        ):
            return self._p28_view(character, quest, world)

        if (
            quest.step == 2
            and world.location == ALTOS_BASTILHA_LABEL
            and action == "locate_containment_archive"
        ):
            members = await self._present_p28(
                session, character_ids, 2, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "containment_archive_located": True,
                }
                member.quest.step = 3
                member.quest.state_version += 1
                await self._credit_p28(
                    session,
                    member.character.id,
                    "p28.containment_archive_located",
                    f"p28.containment_archive_located:{member.character.id}",
                    {"location": ALTOS_BASTILHA_LOCATION, "source": "official_archive"},
                )
        elif (
            quest.step == 3
            and world.location == ALTOS_BASTILHA_LABEL
            and action == "locate_critical_memorial"
        ):
            members = await self._present_p28(
                session, character_ids, 3, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "critical_memorial_located": True,
                }
                member.quest.step = 4
                member.quest.state_version += 1
                await self._credit_p28(
                    session,
                    member.character.id,
                    "p28.critical_memorial_located",
                    f"p28.critical_memorial_located:{member.character.id}",
                    {"location": ALTOS_BASTILHA_LOCATION, "source": "independent_memorial"},
                )
        elif (
            quest.step == 5
            and world.location == ALTOS_BASTILHA_LABEL
            and action == "compare_sources_with_sel_and_maro"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("sources_compared"):
                progress["sources_compared"] = True
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p28(
                    session,
                    character.id,
                    "p28.sources_compared",
                    f"p28.sources_compared:{character.id}",
                    {"givers": ("Sel Ardan", "Maro Keln")},
                )
        elif (
            quest.step == 6
            and world.location == ALTOS_BASTILHA_LABEL
            and action == "record_desvelados_codex"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("codex_recorded"):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=P28_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=P28_CODEX_ENTRY,
                    fragment_id=P28_CODEX_ENTRY,
                )
                progress["codex_recorded"] = True
                quest.progress = progress
                quest.step = 7
                quest.state_version += 1
                await self._credit_p28(
                    session,
                    character.id,
                    "p28.recorded_desvelados_origin",
                    f"p28.recorded_desvelados_origin:{character.id}",
                    {"codex_entry": P28_CODEX_ENTRY},
                )
        elif (
            quest.step == 7
            and world.location == ALTOS_BASTILHA_LABEL
            and action == "record_non_attribution"
            and (quest.progress or {}).get("codex_recorded")
        ):
            quest.progress = {
                **(quest.progress or {}),
                "collective_attribution_withheld": True,
                "anchor_sabotage_unconfirmed": True,
            }
            await self._credit_p28(
                session,
                character.id,
                "p28.non_attribution_recorded",
                f"p28.non_attribution_recorded:{character.id}",
                {
                    "collective_attribution_withheld": True,
                    "anchor_sabotage_unconfirmed": True,
                },
            )
            await self._complete_p28(session, character, quest)

        await session.flush()
        return self._p28_view(character, quest, world)

    async def _advance_p27(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P27_CONTENT_VERSION
            or quest.state_version != version
            or await self._foreground(session, character.id)
        ):
            return self._p27_view(character, quest, world)

        if quest.step == 2 and world.location == ALTOS_PEDREIRAS_LABEL and action in {
            "inspect_block_route",
            "inspect_cable_record",
            "inspect_distribution_table",
        }:
            members = await self._present_p27(
                session, character_ids, 2, ALTOS_PEDREIRAS_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("pedreira_records", ()))
                if action in evidence:
                    continue
                evidence.add(action)
                progress["pedreira_records"] = sorted(evidence)
                member.quest.progress = progress
                if len(evidence) == 3:
                    member.quest.step = 3
                member.quest.state_version += 1
                await self._credit_p27(
                    session,
                    member.character.id,
                    f"p27.{action}",
                    f"p27.{action}:{member.character.id}",
                    {"location": ALTOS_PEDREIRAS_LOCATION, "record": action},
                )
        elif (
            quest.step == 4
            and world.location == ALTOS_PEDREIRAS_LABEL
            and action == "recover_priority_plate"
        ):
            members = await self._present_p27(
                session, character_ids, 4, ALTOS_PEDREIRAS_LABEL
            )
            for member in members:
                member.quest.step = 5
                member.quest.state_version += 1
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "priority_plate_recovered": True,
                }
                await self._credit_p27(
                    session,
                    member.character.id,
                    "p27.priority_plate_recovered",
                    f"p27.priority_plate_recovered:{member.character.id}",
                    {"economic_value": 0, "location": ALTOS_PEDREIRAS_LOCATION},
                )
        elif (
            quest.step == 5
            and world.location == ALTOS_PEDREIRAS_LABEL
            and action == "compare_plate_with_doren_and_rava"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("plate_compared"):
                progress["plate_compared"] = True
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p27(
                    session,
                    character.id,
                    "p27.plate_compared",
                    f"p27.plate_compared:{character.id}",
                    {"givers": ("Doren Vask", "Rava Kern")},
                )
        elif (
            quest.step == 6
            and world.location == ALTOS_PEDREIRAS_LABEL
            and action == "record_priorities_codex"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("codex_recorded"):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=P27_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=P27_CODEX_ENTRY,
                    fragment_id=P27_CODEX_ENTRY,
                )
                progress["codex_recorded"] = True
                quest.progress = progress
                quest.step = 7
                quest.state_version += 1
                await self._credit_p27(
                    session,
                    character.id,
                    "p27.recorded_priorities_carga",
                    f"p27.recorded_priorities_carga:{character.id}",
                    {"codex_entry": P27_CODEX_ENTRY},
                )

        await session.flush()
        return self._p27_view(character, quest, world)

    async def choose_p27_reward(
        self, actor: int, version: int, option_key: str
    ) -> AltosMissionView | None:
        """Persist the character's one-time P27 Rare equipment choice and reward."""
        option = P27_REWARD_OPTIONS.get(option_key)
        if option is None:
            return await self.resume(actor, P27_ID)
        item_id, item_name, slot = option
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            quest = await self._quest(session, actor_row.id, P27_ID)
            world = await self._world(session, actor_row.id)
            if character is None or quest is None or world is None:
                return None
            if (
                quest.content_version != P27_CONTENT_VERSION
                or quest.status != "active"
                or quest.step != 7
                or quest.state_version != version
                or not (quest.progress or {}).get("codex_recorded")
            ):
                return self._p27_view(character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P27_REWARD_SOURCE,
                )
                .with_for_update()
            )
            progress = dict(quest.progress or {})
            if event is None:
                payload = materialize_equipment(
                    f"{P27_REWARD_SOURCE}:{character.id}:{item_id}",
                    "Raro",
                    45,
                    forced_name=item_name,
                    forced_slot=slot,
                    bound=True,
                )
                payload["catalog_item_id"] = item_id
                event = RewardEvent(
                    character_id=character.id,
                    source_id=P27_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 62_400
                character.crowns += 780
                session.add_all(
                    (
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="xp",
                            quantity=62_400,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="crowns",
                            quantity=780,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="equipment",
                            item_id=item_id,
                            quantity=1,
                            payload=payload,
                        ),
                    )
                )
                source_key = f"{P27_REWARD_SOURCE}:equipment"
                if await self.road._inventory_slots(session, character.id) < 60:
                    instance_id, instance = equipment_instance_payload(payload)
                    session.add(
                        EquipmentItem(
                            id=instance_id,
                            character_id=character.id,
                            source_key=source_key,
                            item_name=item_name,
                            rarity="Raro",
                            slot=slot,
                            item_level=45,
                            bound=True,
                            payload=instance,
                        )
                    )
                else:
                    await self.road._pending(
                        session,
                        character.id,
                        source_key,
                        "equipment",
                        payload,
                    )
                progress["reward_choice"] = option_key
                progress["reward_item_id"] = item_id
                await self._credit_p27(
                    session,
                    character.id,
                    "p27.completed",
                    f"p27.completed:{character.id}",
                    {"location": ALTOS_PEDREIRAS_LOCATION, "reward_item_id": item_id},
                )
            else:
                component = await session.scalar(
                    select(RewardComponent)
                    .where(
                        RewardComponent.reward_event_id == event.id,
                        RewardComponent.kind == "equipment",
                    )
                    .with_for_update()
                )
                chosen_id = component.item_id if component is not None else None
                chosen = next(
                    (
                        (key, values)
                        for key, values in P27_REWARD_OPTIONS.items()
                        if values[0] == chosen_id
                    ),
                    None,
                )
                if chosen is None:
                    raise RuntimeError("P27 reward event has no valid equipment choice")
                progress["reward_choice"] = chosen[0]
                progress["reward_item_id"] = chosen_id

            for unlock_id in (
                ALTOS_PEDREIRAS_HUNT_UNLOCK,
                ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
                P27_NARRATIVE_UNLOCK,
            ):
                await self._ensure(
                    session, Unlock, character_id=character.id, unlock_id=unlock_id
                )
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=P27_CODEX_ENTRY,
            )
            await self._ensure(
                session,
                Achievement,
                character_id=character.id,
                achievement_id=P27_ACHIEVEMENT,
            )
            quest.status = "completed"
            quest.state_version += 1
            quest.progress = progress | {"completed": True}
            character.ruleset_version = CHARACTER_RULESET
            await consolidate_character_level(session, character)
            return self._p27_view(character, quest, world)

    async def _advance_p26(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P26_CONTENT_VERSION
            or quest.state_version != version
            or await self._foreground(session, character.id)
        ):
            return self._p26_view(character, quest, world)

        if quest.step == 3 and world.location == ALTOS_PONTES_LABEL and action in {
            "inspect_order_station_1",
            "inspect_order_station_2",
            "inspect_order_station_3",
        }:
            members = await self._present_p26(
                session, character_ids, 3, ALTOS_PONTES_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                stations = set(progress.get("order_stations", ()))
                if action in stations:
                    continue
                stations.add(action)
                progress["order_stations"] = sorted(stations)
                member.quest.progress = progress
                if len(stations) == 3:
                    member.quest.step = 4
                member.quest.state_version += 1
                await self._credit_p26(
                    session,
                    member.character.id,
                    f"p26.{action}",
                    f"p26.{action}:{member.character.id}",
                    {"location": ALTOS_PONTES_LOCATION, "station": action},
                )
        elif (
            quest.step == 4
            and world.location == ALTOS_PONTES_LABEL
            and action == "verify_waiting_bridge"
        ):
            members = await self._present_p26(
                session, character_ids, 4, ALTOS_PONTES_LABEL
            )
            for member in members:
                member.quest.step = 5
                member.quest.state_version += 1
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "verified_waiting_bridge": True,
                }
                await self._credit_p26(
                    session,
                    member.character.id,
                    "p26.verified_waiting_bridge",
                    f"p26.verified_waiting_bridge:{member.character.id}",
                    {"location": ALTOS_PONTES_LOCATION},
                )
        elif (
            quest.step == 5
            and world.location == ALTOS_PONTES_LABEL
            and action == "compare_records_with_sel"
        ):
            quest.step = 6
            quest.state_version += 1
            quest.progress = {
                **(quest.progress or {}),
                "compared_records_with_sel": True,
            }
            await self._credit_p26(
                session,
                character.id,
                "p26.compared_records_with_sel",
                f"p26.compared_records_with_sel:{character.id}",
                {"giver": "Sel Ardan"},
            )
        elif (
            quest.step == 6
            and world.location == ALTOS_PONTES_LABEL
            and action == "record_regencia_codex"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("codex_recorded"):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=P26_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=P26_CODEX_ENTRY,
                    fragment_id=P26_CODEX_ENTRY,
                )
                progress["codex_recorded"] = True
                quest.progress = progress
                quest.step = 7
                quest.state_version += 1
                await self._credit_p26(
                    session,
                    character.id,
                    "p26.recorded_regencia_continuidade",
                    f"p26.recorded_regencia_continuidade:{character.id}",
                    {"codex_entry": P26_CODEX_ENTRY},
                )
        elif (
            quest.step == 7
            and world.location == ALTOS_PONTES_LABEL
            and action == "conclude_emergency_authority"
            and (quest.progress or {}).get("codex_recorded")
        ):
            await self._complete_p26(session, character, quest)

        await session.flush()
        return self._p26_view(character, quest, world)

    async def _complete_p26(self, session, character, quest) -> None:
        for unlock_id in (
            ALTOS_PONTES_HUNT_UNLOCK,
            ALTOS_PONTES_EXPLORE_UNLOCK,
            P26_NARRATIVE_UNLOCK,
        ):
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=unlock_id
            )
        await self._ensure(
            session, CodexEntry, character_id=character.id, entry_id=P26_CODEX_ENTRY
        )
        await self._ensure(
            session,
            CodexFragment,
            character_id=character.id,
            entry_id=P26_CODEX_ENTRY,
            fragment_id=P26_CODEX_ENTRY,
        )
        await self._ensure(
            session, Achievement, character_id=character.id, achievement_id=P26_ACHIEVEMENT
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P26_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P26_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 57_900
            character.crowns += 750
            session.add_all(
                (
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=57_900),
                    RewardComponent(reward_event_id=event.id, kind="crowns", quantity=750),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id="material.altos.ferro_contrapeso",
                        quantity=3,
                        payload={"material_id": "material.altos.ferro_contrapeso", "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id="material.altos.cinza_basalto",
                        quantity=1,
                        payload={"material_id": "material.altos.cinza_basalto", "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                "material.altos.ferro_contrapeso",
                3,
                f"{P26_REWARD_SOURCE}:material:ferro_contrapeso",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                "material.altos.cinza_basalto",
                1,
                f"{P26_REWARD_SOURCE}:material:cinza_basalto",
                bound=True,
            )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        quest.status = "completed"
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p26(
            session,
            character.id,
            "p26.completed",
            f"p26.completed:{character.id}",
            {"location": ALTOS_PONTES_LOCATION},
        )

    async def advance(
        self, actor: int, version: int, action: str
    ) -> AltosMissionView | None:
        if action == "receive_order":
            return await self.start_p26(actor, version)
        if action == "activate_p27":
            return await self.start_p27(actor, version)
        if action == "activate_p28":
            return await self.start_p28(actor, version)
        await self.on_location(actor)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            p28 = await self._quest(session, actor_row.id, P28_ID)
            if p28 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p28(
                    session, character_ids, character, p28, world, version, action
                )
            p27 = await self._quest(session, actor_row.id, P27_ID)
            if p27 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p27(
                    session, character_ids, character, p27, world, version, action
                )
            p26 = await self._quest(session, actor_row.id, P26_ID)
            if p26 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p26(
                    session, character_ids, character, p26, world, version, action
                )
            quest = await self._quest(session, actor_row.id, P25_ID)
            if character is None or quest is None or world is None:
                return None
            if (
                quest.status != "active"
                or quest.content_version != P25_CONTENT_VERSION
                or quest.state_version != version
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            if quest.step == 2 and world.location == ALTOS_ESCARPA_LABEL and action in {
                "inspect_contraforte",
                "inspect_cabo",
                "inspect_escora",
            }:
                members = await self._present(session, character_ids, 2, ALTOS_ESCARPA_LABEL)
                for member in members:
                    progress = dict(member.quest.progress or {})
                    points = set(progress.get("support_points", ()))
                    if action in points:
                        continue
                    points.add(action)
                    progress["support_points"] = sorted(points)
                    member.quest.progress = progress
                    if len(points) == 3:
                        member.quest.step = 3
                    member.quest.state_version += 1
                    await self._credit(
                        session,
                        member.character.id,
                        f"p25.{action}",
                        f"p25.{action}:{member.character.id}",
                        {"location": ALTOS_ESCARPA_LABEL},
                    )
            elif (
                quest.step == 4
                and world.location == ALTOS_ESCARPA_LABEL
                and action == "register_escarpa_brazier"
            ):
                members = await self._present(session, character_ids, 4, ALTOS_ESCARPA_LABEL)
                for member in members:
                    await self._ensure(
                        session,
                        Brazier,
                        character_id=member.character.id,
                        brazier_id=ALTOS_ESCARPA_BRAZIER,
                    )
                    member.quest.step = 5
                    member.quest.state_version += 1
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "registered_escarpa_brazier": True,
                    }
                    await self._credit(
                        session,
                        member.character.id,
                        "p25.registered_escarpa_brazier",
                        f"p25.registered_escarpa_brazier:{member.character.id}",
                        {"brazier_id": ALTOS_ESCARPA_BRAZIER},
                    )
            elif (
                quest.step == 5
                and world.location == ALTOS_ESCARPA_LABEL
                and action == "confirm_redundant_repairs"
            ):
                members = await self._present(session, character_ids, 5, ALTOS_ESCARPA_LABEL)
                for member in members:
                    member.quest.step = 6
                    member.quest.state_version += 1
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "confirmed_redundant_repairs": True,
                    }
                    await self._credit(
                        session,
                        member.character.id,
                        "p25.confirmed_redundant_repairs",
                        f"p25.confirmed_redundant_repairs:{member.character.id}",
                        {"location": ALTOS_ESCARPA_LABEL},
                    )
            elif (
                quest.step == 7
                and world.location == ALTOS_ABRIGO_LABEL
                and action == "register_abrigo_brazier"
            ):
                members = await self._present(session, character_ids, 7, ALTOS_ABRIGO_LABEL)
                for member in members:
                    await self._ensure(
                        session,
                        Brazier,
                        character_id=member.character.id,
                        brazier_id=ALTOS_ABRIGO_BRAZIER,
                    )
                    member.quest.step = 8
                    member.quest.state_version += 1
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "registered_abrigo_brazier": True,
                    }
                    await self._credit(
                        session,
                        member.character.id,
                        "p25.registered_abrigo_brazier",
                        f"p25.registered_abrigo_brazier:{member.character.id}",
                        {"brazier_id": ALTOS_ABRIGO_BRAZIER},
                    )
            elif quest.step == 8 and world.location == ALTOS_ABRIGO_LABEL and action in {
                "speak_rava",
                "speak_doren",
            }:
                progress = dict(quest.progress or {})
                flag = "spoke_rava" if action == "speak_rava" else "spoke_doren"
                if not progress.get(flag):
                    progress[flag] = True
                    quest.progress = progress
                    if progress.get("spoke_rava") and progress.get("spoke_doren"):
                        quest.step = 9
                    quest.state_version += 1
                    await self._credit(
                        session,
                        character.id,
                        f"p25.{flag}",
                        f"p25.{flag}:{character.id}",
                        {"location": ALTOS_ABRIGO_LABEL},
                    )
            elif (
                quest.step == 9
                and world.location == ALTOS_ABRIGO_LABEL
                and action == "record_codex"
            ):
                progress = dict(quest.progress or {})
                if not progress.get("codex_recorded"):
                    await self._ensure(
                        session, CodexEntry, character_id=character.id, entry_id=P25_CODEX_ENTRY
                    )
                    await self._ensure(
                        session,
                        CodexFragment,
                        character_id=character.id,
                        entry_id=P25_CODEX_ENTRY,
                        fragment_id=P25_CODEX_ENTRY,
                    )
                    progress["codex_recorded"] = True
                    quest.progress = progress
                    quest.state_version += 1
                    await self._credit(
                        session,
                        character.id,
                        "p25.recorded_carga_observavel",
                        f"p25.recorded_carga_observavel:{character.id}",
                        {"codex_entry": P25_CODEX_ENTRY},
                    )
            elif (
                quest.step == 9
                and world.location == ALTOS_ABRIGO_LABEL
                and action == "conclude_with_rava"
                and (quest.progress or {}).get("codex_recorded")
            ):
                await self._complete(session, character, quest)

            quest = await self._quest(session, character.id, P25_ID)
            return await self._view(session, character, quest, world)

    async def start_solo_combat(
        self, actor: int, version: int, quest_id: str = P25_ID
    ) -> AltosMissionView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            _group_id, _members = await lock_campaign_roster(session, character.id)
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if character is None or quest is None or world is None:
                return None
            profile = P25_COMBAT.get(quest_id)
            if profile is None:
                return None
            _content_id, _checkpoint, location, _creature_id, _enemy_level, _category = profile
            if (
                quest.status != "active"
                or quest.content_version != P25_CONTENT_VERSION
                or quest.step != _scripted_combat_step(quest_id)
                or quest.state_version != version
                or world.region != ALTOS_REGION
                or world.location != location
            ):
                return await self._view(session, character, quest, world)
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                )
                .with_for_update()
            )
            if activity is not None:
                return await self._view(session, character, quest, world)
            await self._create_solo_combat(session, character, quest_id)
            progress = dict(quest.progress or {})
            progress.pop("awaiting_retry", None)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry_combat(
        self, actor: int, version: int, quest_id: str = P25_ID
    ) -> AltosMissionView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            await lock_campaign_roster(session, character.id)
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if (
                character is None
                or quest is None
                or world is None
                or quest.status != "active"
                or quest.step != _scripted_combat_step(quest_id)
                or quest.state_version != version
                or not (quest.progress or {}).get("awaiting_retry")
            ):
                return (
                    await self._view(session, character, quest, world)
                    if character and quest
                    else None
                )
            if await self._foreground(session, character.id):
                return await self._view(session, character, quest, world)
            await self._create_solo_combat(session, character, quest_id)
            progress = dict(quest.progress or {})
            progress.pop("awaiting_retry", None)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _create_solo_combat(
        self, session, character, quest_id: str = P25_ID
    ) -> GameActivity:
        content_id, _checkpoint, _location, creature_id, enemy_level, category = P25_COMBAT[
            quest_id
        ]
        equipment = await load_equipment_configuration(session, character)
        arts = await load_active_art_configuration(session, character)
        reconcile_character_hp(character, equipment)
        combat = create_creature_party_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            (CreatureCombatantSpec(creature_for(creature_id), enemy_level, "enemy", None),),
            player_level=character.level,
            equipment_configuration=equipment,
            ruleset_version=RULESET,
            active_art_ids=arts.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | arts.to_data()
        activity, _encounter, _record = await CombatRepository(session).create(
            character, content_id, combat
        )
        await self.road._bestiary(
            session,
            character.id,
            creature_id,
            victory=False,
            observation_category=category,
        )
        return activity

    async def propose_group_combat(
        self, actor: int, version: int, quest_id: str = P25_ID
    ) -> AltosMissionView | None:
        if self.groups is None:
            return await self.start_solo_combat(actor, version, quest_id)
        initial = await self.resume(actor, quest_id)
        if (
            initial is None
            or initial.status != "active"
            or initial.step != _scripted_combat_step(quest_id)
            or initial.state_version != version
        ):
            return initial
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, version, quest_id)
        content_id, checkpoint, location, _creature_id, _enemy_level, _category = (
            P25_COMBAT[quest_id]
        )
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_altos",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": quest_id,
                "checkpoint": checkpoint,
                "content_id": content_id,
                "location": location,
            },
            journey_reference_character_id=initial.character_id,
        )
        view = await self.resume(actor, quest_id)
        return (
            replace(
                view,
                proposal_id=proposal.proposal_id,
                proposal_status=proposal.status,
            )
            if view
            else None
        )

    async def start_group_combat(
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ) -> AltosMissionView | None:
        if self.groups is None:
            return await self.resume(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._combat_eligibility,
            create_activity=self._create_group_combat,
        )
        return await self.resume(actor)

    async def _combat_eligibility(
        self, session: AsyncSession, character: Character, payload: dict
    ) -> ActivityEligibility:
        quest_id = payload.get("quest_id", P25_ID)
        profile = P25_COMBAT.get(quest_id)
        quest = (
            await self._quest(session, character.id, quest_id, lock=False)
            if profile is not None
            else None
        )
        location = profile[2] if profile is not None else None
        world = await self._world(session, character.id, lock=False)
        active = await self._foreground(session, character.id)
        content_version = (
            P28_CONTENT_VERSION
            if quest_id == P28_ID
            else P27_CONTENT_VERSION
            if quest_id == P27_ID
            else P25_CONTENT_VERSION
        )
        if (
            active is not None
            or world is None
            or world.region != ALTOS_REGION
            or world.location != location
        ):
            role = "ineligible"
        elif (
            quest is not None
            and quest.status == "active"
            and quest.step == _scripted_combat_step(quest_id)
            and quest.content_version == content_version
        ):
            role = "eligible"
        elif (
            quest is not None
            and quest.status == "completed"
            and quest.content_version == content_version
        ):
            role = "helper"
        else:
            role = "ineligible"
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "quest_status": quest.status if quest else None,
            "quest_step": quest.step if quest else None,
            "quest_version": quest.state_version if quest else None,
            "world_location": world.location if world else None,
            "world_region": world.region if world else None,
            "active_activity": str(active) if active else None,
            "level": character.level,
            "combat_configuration_version": character.combat_configuration_version,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_group_combat(
        self,
        session: AsyncSession,
        proposal: GroupActivityProposal,
        characters: tuple[Character, ...],
    ) -> str:
        quest_id = (proposal.context_payload or {}).get("quest_id", P25_ID)
        profile = P25_COMBAT.get(quest_id)
        if profile is None:
            raise GroupError("eligibility_changed")
        content_id, checkpoint, _location, creature_id, enemy_level, category = profile
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        participant_by_character = {row.character_id: row for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        roster: list[CampaignRosterMember] = []
        party: list[PlayerCombatantSpec] = []
        for index, character in enumerate(characters, start=1):
            participant = participant_by_character.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            actor_key = "player" if len(characters) == 1 else f"p{index}"
            party.append(
                PlayerCombatantSpec(
                    fighter_key=actor_key,
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
            roster.append(
                CampaignRosterMember(
                    character=character,
                    actor_key=actor_key,
                    role=participant.eligibility,
                    checkpoint=checkpoint,
                )
            )
        lead = characters[0]
        lead_equipment = await load_equipment_configuration(session, lead)
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(creature_for(creature_id), enemy_level, "enemy", None),),
            player_level=lead.level,
            equipment_configuration=lead_equipment,
            ruleset_version=RULESET,
            party=tuple(party),
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=quest_id,
            content_id=content_id,
            combat=combat,
            ruleset_version=combat.ruleset,
            checkpoint=checkpoint,
        )
        for member in roster:
            await self.road._bestiary(
                session,
                member.character.id,
                creature_id,
                victory=False,
                observation_category=category,
            )
        return str(encounter.id)

    async def action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ) -> AltosMissionView | None:
        shared = await self._shared_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if shared is not None:
            return shared
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            await lock_campaign_roster(session, character.id)
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                )
                .with_for_update()
            )
            quest_id = next(
                (
                    mission_id
                    for mission_id, profile in P25_COMBAT.items()
                    if activity is not None and profile[0] == activity.content_id
                ),
                None,
            )
            profile = P25_COMBAT.get(quest_id)
            if quest_id is None or profile is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if character is None or quest is None or world is None or activity is None:
                return None
            _content_id, _checkpoint, _location, creature_id, enemy_level, category = profile
            current = await self._view(session, character, quest, world)
            if (
                quest.status != "active"
                or quest.step != _scripted_combat_step(quest_id)
                or activity.status != "active"
                or activity.state_version != version
                or (action is None) == (consumable_id is None)
            ):
                return current
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=category,
            )
            if updated is None or updated.version == version:
                return await self._view(session, character, quest, world)
            await self.road.bestiary.record_combat_events(
                session, character.id, creature_id, None, updated
            )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                quest.step = _scripted_combat_step(quest_id) + 1
                progress.update(combat_result="victory", awaiting_retry=False)
                character.ruleset_version = CHARACTER_RULESET
                await self.road._bestiary(
                    session,
                    character.id,
                    creature_id,
                    victory=True,
                    observation_category=category,
                )
                if quest_id == P28_ID:
                    await self._credit_p28(
                        session,
                        character.id,
                        "p28.scripted_vigia_victory",
                        f"p28.scripted_vigia_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
                elif quest_id == P27_ID:
                    await self._credit_p27(
                        session,
                        character.id,
                        "p27.scripted_carcaca_victory",
                        f"p27.scripted_carcaca_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
                else:
                    await self._credit(
                        session,
                        character.id,
                        "p25.scripted_lobo_victory",
                        f"p25.scripted_lobo_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
            elif updated.result == "defeat":
                activity.status = "failed"
                await normalize_character_hp(session, character)
                progress.update(combat_result="defeat", awaiting_retry=True)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def _shared_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None,
        *,
        consumable_id: str | None,
        target_id: str | None,
        effect_id: str | None,
    ) -> AltosMissionView | None:
        async with self.sessions.begin() as session:
            character_seed = await self._character(session, actor)
            if character_seed is None:
                return None
            seed = await session.scalar(
                select(CampaignSharedEncounterMember).where(
                    CampaignSharedEncounterMember.game_activity_id == activity_id,
                    CampaignSharedEncounterMember.character_id == character_seed.id,
                )
            )
            if seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, character_seed.id)
            if locked is None:
                return None
            quest_id = locked.encounter.quest_id
            profile = P25_COMBAT.get(quest_id)
            if (
                locked is None
                or profile is None
                or locked.encounter.content_id != profile[0]
            ):
                return None
            _content_id, _checkpoint, _location, creature_id, enemy_level, category = profile
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id),
                None,
            )
            character = locked.characters.get(character_seed.id)
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(tuple(locked.characters)),
                            Quest.quest_id == quest_id,
                        )
                        .order_by(Quest.character_id)
                        .with_for_update()
                    )
                ).all()
            )
            quest_by_character = {row.character_id: row for row in quest_rows}
            quest = quest_by_character.get(character_seed.id)
            activity = locked.activities.get(activity_id)
            if character is None or quest is None or activity is None:
                return None
            world = await self._world(session, character.id)
            current = await self._view(session, character, quest, world)
            if (
                member is None
                or activity.status != "active"
                or activity.state_version != version
                or locked.encounter.state_version != version
                or (action is None) == (consumable_id is None)
            ):
                return current
            stack = None
            if consumable_id is not None:
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
                    return current
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(category, 0),
            )
            if updated.version == version:
                return current
            if stack is not None:
                stack.quantity -= 1
            for character_id in locked.characters:
                await self.road.bestiary.record_combat_events(
                    session, character_id, creature_id, None, updated
                )
            if updated.result is not None:
                member_by_character = {row.character_id: row for row in locked.members}
                for character_id, participant in locked.characters.items():
                    roster_member = member_by_character[character_id]
                    participant_quest = quest_by_character.get(character_id)
                    if (
                        participant_quest is not None
                        and roster_member.role == "eligible"
                        and participant_quest.status == "active"
                        and participant_quest.step == _scripted_combat_step(quest_id)
                    ):
                        progress = dict(participant_quest.progress or {})
                        if updated.result == "victory":
                            participant_quest.step = _scripted_combat_step(quest_id) + 1
                            progress.update(combat_result="victory", awaiting_retry=False)
                            participant.ruleset_version = CHARACTER_RULESET
                            await self.road._bestiary(
                                session,
                                participant.id,
                                creature_id,
                                victory=True,
                                observation_category=category,
                            )
                            if quest_id == P28_ID:
                                await self._credit_p28(
                                    session,
                                    participant.id,
                                    "p28.scripted_vigia_victory",
                                    f"p28.scripted_vigia_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                            elif quest_id == P27_ID:
                                await self._credit_p27(
                                    session,
                                    participant.id,
                                    "p27.scripted_carcaca_victory",
                                    f"p27.scripted_carcaca_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                            else:
                                await self._credit(
                                    session,
                                    participant.id,
                                    "p25.scripted_lobo_victory",
                                    f"p25.scripted_lobo_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                        else:
                            progress.update(combat_result="defeat", awaiting_retry=True)
                            await normalize_character_hp(session, participant)
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
                    elif updated.result == "defeat":
                        await normalize_character_hp(session, participant)
                await settle_campaign_encounter(session, locked, updated.result)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> AltosMissionView | None:
        view = await self.resume(actor)
        if (
            view is None
            or view.activity_id != activity_id
        ):
            return None
        if (
            view.combat is None
            or view.combat.version != version
            or view.combat_actor_key != active_player_key(view.combat)
        ):
            return view
        intent = campaign_action_intent(
            view.combat, view.combat_actor_key, action_index, target_code
        )
        if intent is None:
            return view
        action, target_id = intent
        return await self.action(actor, activity_id, version, action, target_id=target_id)

    async def consumable_selection(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        *,
        screen: str,
        item_id: str | None = None,
        target_id: str | None = None,
        parent: str = "items",
    ) -> AltosMissionView | None:
        view = await self.combat_view_for_actor(actor, activity_id)
        if view is None or view.combat is None or view.combat.version != version:
            return view
        return derive_consumable_selection(
            view, screen=screen, item_id=item_id, target_id=target_id, parent=parent
        )

    async def combat_view_for_actor(
        self, actor: int, activity_id: UUID
    ) -> AltosMissionView | None:
        view = await self.resume(actor)
        return view if view is not None and view.activity_id == activity_id else None

    async def _view(self, session, character, quest, world) -> AltosMissionView | None:
        if character is None or quest is None:
            return None
        location = world.location if world is not None else ALTOS_ESCARPA_LABEL
        activity = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == P25_COMBAT.get(quest.quest_id, (None,))[0],
                GameActivity.status == "active",
            )
        )
        profile = P25_COMBAT.get(quest.quest_id)
        category = profile[5] if profile is not None else "common"
        combat = encounter = member = None
        actor_key = None
        group_size = 1
        if activity is not None:
            shared_encounter = await session.scalar(
                select(CampaignSharedEncounterMember).where(
                    CampaignSharedEncounterMember.game_activity_id == activity.id,
                    CampaignSharedEncounterMember.character_id == character.id,
                )
            )
            if shared_encounter is not None:
                encounter_row = await session.get(
                    CampaignSharedEncounter, shared_encounter.shared_encounter_id
                )
                if encounter_row is not None and encounter_row.combat_snapshot is not None:
                    combat = decode(
                        encounter_row.combat_snapshot,
                        encounter_row.id,
                        encounter_row.ruleset_version,
                        encounter_row.state_version,
                    )
                    encounter = encounter_row
                    member = shared_encounter
                    actor_key = member.actor_key
                    group_size = encounter_row.roster_size
            else:
                combat, encounter, _combat_record = await current_combat(session, activity)
            if combat is not None:
                options, quantities, budget = await consumable_state(
                    session, character, combat, category, actor_key=actor_key
                )
            else:
                options, quantities, budget = (), (), 0
        else:
            options, quantities, budget = (), (), 0
        proposal_pair = None
        if activity is None:
            proposal_pair = (
                await session.execute(
                    select(GroupActivityParticipant, GroupActivityProposal)
                    .join(
                        GroupActivityProposal,
                        GroupActivityProposal.id == GroupActivityParticipant.proposal_id,
                    )
                    .where(
                        GroupActivityParticipant.character_id == character.id,
                        GroupActivityParticipant.reservation_state == "active",
                        GroupActivityProposal.activity_type == "campaign_altos",
                        GroupActivityProposal.status.in_(("pending", "ready")),
                    )
                    .order_by(GroupActivityProposal.created_at.desc())
                    .limit(1)
                )
            ).first()
            if (
                proposal_pair is not None
                and (proposal_pair[1].context_payload or {}).get("quest_id", P25_ID)
                != quest.quest_id
            ):
                proposal_pair = None
        return AltosMissionView(
            character_id=character.id,
            quest_id=quest.quest_id,
            title=quest.title,
            kind="combat" if combat is not None else "mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=location,
            level=character.level,
            combat=combat,
            activity_id=activity.id if activity is not None else None,
            encounter_id=encounter.id if encounter is not None else None,
            combat_actor_key=actor_key,
            group_size=group_size,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
            proposal_id=proposal_pair[1].id if proposal_pair else None,
            proposal_status=proposal_pair[1].status if proposal_pair else None,
        )

    async def _complete(self, session, character, quest) -> None:
        await self._ensure(
            session, Unlock, character_id=character.id, unlock_id=ALTOS_ESCARPA_HUNT_UNLOCK
        )
        await self._ensure(
            session, Unlock, character_id=character.id, unlock_id=ALTOS_ESCARPA_EXPLORE_UNLOCK
        )
        await self._ensure(
            session, Unlock, character_id=character.id, unlock_id=P25_NARRATIVE_UNLOCK
        )
        await self._ensure(
            session, CodexEntry, character_id=character.id, entry_id=P25_REGION_CODEX
        )
        await self._ensure(
            session, Achievement, character_id=character.id, achievement_id=P25_ACHIEVEMENT
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P25_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P25_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 53_500
            character.crowns += 720
            session.add_all(
                (
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=53_500),
                    RewardComponent(reward_event_id=event.id, kind="crowns", quantity=720),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id="material.altos.ferro_contrapeso",
                        quantity=1,
                        payload={"material_id": "material.altos.ferro_contrapeso", "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id="material.altos.liquen_pedreira",
                        quantity=1,
                        payload={"material_id": "material.altos.liquen_pedreira", "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                "material.altos.ferro_contrapeso",
                1,
                f"{P25_REWARD_SOURCE}:material:ferro_contrapeso",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                "material.altos.liquen_pedreira",
                1,
                f"{P25_REWARD_SOURCE}:material:liquen_pedreira",
                bound=True,
            )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        quest.status = "completed"
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit(
            session,
            character.id,
            "p25.completed",
            f"p25.completed:{character.id}",
            {"location": ALTOS_ABRIGO_LABEL},
        )

    async def _complete_p28(self, session, character, quest) -> None:
        for unlock_id in (
            ALTOS_BASTILHA_HUNT_UNLOCK,
            ALTOS_BASTILHA_EXPLORE_UNLOCK,
            P28_NARRATIVE_UNLOCK,
        ):
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=unlock_id
            )
        await self._ensure(
            session, CodexEntry, character_id=character.id, entry_id=P28_CODEX_ENTRY
        )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=P28_ACHIEVEMENT,
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P28_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(
                character_id=character.id,
                source_id=P28_REWARD_SOURCE,
            )
            session.add(event)
            await session.flush()
            character.xp += 67_100
            character.crowns += 1_010
            rewards = (
                ("xp", None, 67_100, {}),
                ("crowns", None, 1_010, {}),
                (
                    "material",
                    ALTOS_FERRO_CONTRAPESO,
                    2,
                    {"material_id": ALTOS_FERRO_CONTRAPESO, "bound": True},
                ),
                (
                    "material",
                    ALTOS_COURO_ESCARPA,
                    1,
                    {"material_id": ALTOS_COURO_ESCARPA, "bound": True},
                ),
                (
                    "material",
                    ALTOS_CINZA_BASALTO,
                    1,
                    {"material_id": ALTOS_CINZA_BASALTO, "bound": True},
                ),
            )
            session.add_all(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
                for kind, item_id, quantity, payload in rewards
            )
            for material_id, quantity, key in (
                (ALTOS_FERRO_CONTRAPESO, 2, "ferro_contrapeso"),
                (ALTOS_COURO_ESCARPA, 1, "couro_escarpa"),
                (ALTOS_CINZA_BASALTO, 1, "cinza_basalto"),
            ):
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P28_REWARD_SOURCE}:material:{key}",
                    bound=True,
                )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        quest.status = "completed"
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p28(
            session,
            character.id,
            "p28.completed",
            f"p28.completed:{character.id}",
            {"location": ALTOS_BASTILHA_LOCATION},
        )

    async def _present(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P25_ID,
            content_version=P25_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _present_p26(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P26_ID,
            content_version=P26_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _present_p27(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P27_ID,
            content_version=P27_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _present_p28(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P28_ID,
            content_version=P28_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _credit(self, session, character_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P25_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p26(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P26_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p27(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P27_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p28(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P28_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _ensure(self, session, model, **values):
        existing = await session.scalar(select(model).filter_by(**values).with_for_update())
        if existing is None:
            session.add(model(**values))
        return existing

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _quest(self, session, character_id, quest_id, *, lock=True):
        statement = select(Quest).where(
            Quest.character_id == character_id,
            Quest.quest_id == quest_id,
        )
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _world(self, session, character_id, *, lock=True):
        statement = select(WorldState).where(WorldState.character_id == character_id)
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _quest_completed(self, session, character_id, quest_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == quest_id,
                    Quest.status == "completed",
                )
            )
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )
