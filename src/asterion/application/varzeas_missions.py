"""Persistent campaign progression for the Várzeas Carmesins."""

# ruff: noqa: E501

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
    campaign_actor_key,
    campaign_combat_for_activity,
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
from asterion.application.road import RoadService
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    current_combat,
    derive_consumable_selection,
    materialize,
    normalize_character_hp,
)
from asterion.application.varzeas_feats import reconcile_varzeas_feats
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.road import (
    RULESET,
    VARZEAS_BREJOS,
    VARZEAS_BREJOS_EXPLORE_UNLOCK,
    VARZEAS_BREJOS_HORTOS_ROUTE,
    VARZEAS_BREJOS_HUNT_UNLOCK,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_CAMARA,
    VARZEAS_CAMARA_ACCESS_UNLOCK,
    VARZEAS_CAMARA_LOCATION,
    VARZEAS_CRIMSON_BEARER,
    VARZEAS_DIQUES,
    VARZEAS_DIQUES_BRAZIER,
    VARZEAS_DIQUES_EXPLORE_UNLOCK,
    VARZEAS_DIQUES_HUNT_UNLOCK,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_DIQUES_PORTO_ROUTE,
    VARZEAS_GALERIAS,
    VARZEAS_GALERIAS_BRAZIER,
    VARZEAS_GALERIAS_CAMARA_ROUTE,
    VARZEAS_GALERIAS_EXPLORE_UNLOCK,
    VARZEAS_GALERIAS_HUNT_UNLOCK,
    VARZEAS_GALERIAS_LOCATION,
    VARZEAS_GARDEN_GRAFT,
    VARZEAS_HEMARIS_WARDEN,
    VARZEAS_HORTOS,
    VARZEAS_HORTOS_EXPLORE_UNLOCK,
    VARZEAS_HORTOS_GALERIAS_ROUTE,
    VARZEAS_HORTOS_HUNT_UNLOCK,
    VARZEAS_HORTOS_LOCATION,
    VARZEAS_PORTO,
    VARZEAS_PORTO_BRAZIER,
    VARZEAS_PORTO_BREJOS_ROUTE,
    VARZEAS_PORTO_LOCATION,
    VARZEAS_REED_SPIDER,
    VARZEAS_REGION_ENTRY_UNLOCK,
    VARZEAS_RUST_DEER,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    materialize_equipment,
)
from asterion.infrastructure.db.models import (
    Brazier,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    EquipmentItem,
    GameActivity,
    GroupActivityParticipant,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    SocialGroup,
    Unlock,
    WorldState,
)

REGION = "Várzeas Carmesins"
P19_ID = "P19"
S19_ID = "S19"
P20_ID = "P20"
S20_ID = "S20"
P21_ID = "P21"
S21_ID = "S21"
P22_ID = "P22"
S22_ID = "S22"
P23_ID = "P23"
S23_ID = "S23"
P19_TITLE = "Águas de Ferro"
S19_TITLE = "Sal nas Feridas"
P20_TITLE = "O Pulso sob a Lama"
S20_TITLE = "Um Corpo que Continua"
P21_TITLE = "Os Hortos Vazios"
S21_TITLE = "Cicatrizes de Cultivo"
P22_TITLE = "Transferência"
S22_TITLE = "Protocolos sem Paciente"
P23_TITLE = "O Custo da Persistência"
S23_TITLE = "Fluxo de Emergência"
CONTENT_VERSION = "varzeas-1.0.0"
P19_REWARD_SOURCE = "p19.aguas_de_ferro"
S19_REWARD_SOURCE = "s19.sal_nas_feridas"
P20_REWARD_SOURCE = "p20.o_pulso_sob_a_lama"
S20_REWARD_SOURCE = "s20.um_corpo_que_continua"
P21_REWARD_SOURCE = "p21.os_hortos_vazios"
S21_REWARD_SOURCE = "s21.cicatrizes_de_cultivo"
P22_REWARD_SOURCE = "p22.transferencia"
S22_REWARD_SOURCE = "s22.protocolos_sem_paciente"
P23_REWARD_SOURCE = "p23.o_custo_da_persistencia"
S23_REWARD_SOURCE = "s23.fluxo_de_emergencia"
ROTAS_CODEX = "codex.route.rotas_das_varzeas"
ROTAS_FRAGMENT = "codex.fragment.varzeas.p19.rotas_initial"
P20_CODEX = "codex.mystery.pulso_sob_a_lama"
P20_FRAGMENT = "codex.fragment.varzeas.p20.pulso_sob_a_lama"
P21_CODEX = "codex.history.projeto_hemaris_registro_inicial"
P21_FRAGMENT = "codex.fragment.varzeas.p21.projeto_hemaris_registro_inicial"
P22_CODEX = "codex.history.transferencia"
P22_FRAGMENT = "codex.fragment.varzeas.p22.transferencia"
S22_CODEX = "codex.mystery.protocolos_sem_paciente"
S22_FRAGMENT = "codex.fragment.varzeas.s22.protocolos_sem_paciente"
S23_CODEX = "codex.history.protocolos_de_emergencia"
S23_FRAGMENT = "codex.fragment.varzeas.s23.protocolos_emergencia"
P23_COSTS_CODEX = "codex.history.projeto_hemaris_custos_da_emergencia"
P23_COSTS_FRAGMENT = "codex.fragment.varzeas.p23.custos_emergencia"
P23_ANCESTRY_CODEX = "codex.history.origem_ancestral_alteracoes_hemarias"
P23_ANCESTRY_FRAGMENT = "codex.fragment.varzeas.p23.origem_ancestral"
P21_REWARD_CHOICES = {
    "mask": ("Máscara da Salmoura", "Cabeça"),
    "seal": ("Selo dos Diques", "Acessório"),
    "reliquary": ("Relicário do Horto Estéril", "Artefato"),
}
MISSION_CONTENT_IDS = {
    P20_ID: "campaign.varzeas.p20.arana_junco",
    S20_ID: "campaign.varzeas.s20.portador_rubro",
    P21_ID: "campaign.varzeas.p21.cervo_ferrugem",
    P22_ID: "campaign.varzeas.p22.vigia_hemaris",
    P23_ID: "campaign.varzeas.p23.persistence_cost",
    S23_ID: "campaign.varzeas.s23.emergency_flow",
}
MISSION_CHECKPOINTS = {
    P20_ID: "p20.pulse_spider",
    S20_ID: "s20.crimson_bearer",
    P21_ID: "p21.rust_deer",
    P22_ID: "p22.hemaris_warden",
    P23_ID: "p23.persistence_cost",
    S23_ID: "s23.emergency_flow",
}


@dataclass(frozen=True, slots=True)
class VarzeasMissionView:
    character_id: UUID
    quest_id: str
    title: str
    kind: str
    status: str | None
    step: int | None
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    combat: object | None = None
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


class VarzeasMissionService:
    """Persistent campaign progression for Várzeas P19–P21 and S19–S21."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        groups: GroupService | None = None,
    ):
        self.sessions = sessions
        self.server_id = server_id
        self.groups = groups
        self.road = RoadService(sessions, server_id)

    async def on_location(self, actor: int) -> None:
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None or world.region != REGION:
                return
            await self._start_p23_for_present_roster(session, character_ids)
            if world.location == VARZEAS_DIQUES:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is not None and member_world.region == REGION and member_world.location == VARZEAS_DIQUES:
                        await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_DIQUES_LOCATION)
                        await self._ensure_codex(session, member_id, "codex.location.diques_rubros")
                await self._start_p19_for_present_roster(session, character_ids)
            elif world.location == VARZEAS_PORTO:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is not None and member_world.region == REGION and member_world.location == VARZEAS_PORTO:
                        await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_PORTO_LOCATION)
                        await self._ensure_codex(session, member_id, "codex.location.porto_da_salmoura")
                await self._credit_port_arrival(session, character_ids)
                await self._start_p20_for_present_roster(session, character_ids)
            elif world.location == VARZEAS_BREJOS:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is not None and member_world.region == REGION and member_world.location == VARZEAS_BREJOS:
                        await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_BREJOS_LOCATION)
                        await self._ensure_codex(session, member_id, "codex.location.brejos_do_pulso")
                members = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=P20_ID,
                    content_version=CONTENT_VERSION,
                    step=1,
                    region=REGION,
                    location=VARZEAS_BREJOS,
                )
                for member in members:
                    member.quest.step = 2
                    member.quest.state_version += 1
                    member.quest.progress = {**(member.quest.progress or {}), "entered_brejos": True}
                    await self._credit(
                        session,
                        member.character.id,
                        P20_ID,
                        "p20.entered_brejos",
                        f"p20.entered_brejos:{member.character.id}",
                        {"location": VARZEAS_BREJOS},
                    )
                await self._start_p21_for_present_roster(session, character_ids)
            elif world.location == VARZEAS_HORTOS:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is None or member_world.region != REGION or member_world.location != VARZEAS_HORTOS:
                        continue
                    await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_HORTOS_LOCATION)
                    await self._ensure_codex(session, member_id, "codex.location.hortos_hemaris")
                    if await self._quest(session, member_id, P21_ID) is not None:
                        await self._ensure(session, Unlock, character_id=member_id, unlock_id=VARZEAS_HORTOS_HUNT_UNLOCK)
                        await self._ensure(session, Unlock, character_id=member_id, unlock_id=VARZEAS_HORTOS_EXPLORE_UNLOCK)
                members = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=P21_ID,
                    content_version=CONTENT_VERSION,
                    step=1,
                    region=REGION,
                    location=VARZEAS_HORTOS,
                )
                for member in members:
                    member.quest.step = 2
                    member.quest.state_version += 1
                    member.quest.progress = {**(member.quest.progress or {}), "entered_hortos": True}
                    await self._credit(
                        session,
                        member.character.id,
                        P21_ID,
                        "p21.entered_hortos",
                        f"p21.entered_hortos:{member.character.id}",
                        {"location": VARZEAS_HORTOS},
                    )
                await self._start_p22_for_present_roster(session, character_ids)
            elif world.location == VARZEAS_GALERIAS:
                for member_id in character_ids:
                    member_world = await self._world(session, member_id)
                    if member_world is None or member_world.region != REGION or member_world.location != VARZEAS_GALERIAS:
                        continue
                    await self._ensure(session, LocationDiscovery, character_id=member_id, location_id=VARZEAS_GALERIAS_LOCATION)
                    await self._ensure_codex(session, member_id, "codex.location.galerias_transferencia")
                members = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=P22_ID,
                    content_version=CONTENT_VERSION,
                    step=1,
                    region=REGION,
                    location=VARZEAS_GALERIAS,
                )
                for member in members:
                    member.quest.step = 2
                    member.quest.state_version += 1
                    member.quest.progress = {**(member.quest.progress or {}), "entered_galerias": True}
                    await self._credit(
                        session,
                        member.character.id,
                        P22_ID,
                        "p22.entered_galerias",
                        f"p22.entered_galerias:{member.character.id}",
                        {"location": VARZEAS_GALERIAS},
                    )
                members_at_brazier_step = await present_campaign_members(
                    session,
                    character_ids=character_ids,
                    quest_id=P22_ID,
                    content_version=CONTENT_VERSION,
                    step=2,
                    region=REGION,
                    location=VARZEAS_GALERIAS,
                )
                for member in members_at_brazier_step:
                    quest = member.quest
                    member_id = member.character.id
                    if quest.status != "active" or quest.step != 2:
                        continue
                    has_brazier = await self._has_brazier(session, member_id, VARZEAS_GALERIAS_BRAZIER)
                    if has_brazier:
                        quest.step = 3
                        quest.state_version += 1
                        quest.progress = {**(quest.progress or {}), "brazier_registered": True}
                        await self._credit(
                            session,
                            member_id,
                            P22_ID,
                            "p22.registered_brazier",
                            f"p22.brazier:{member_id}",
                            {"source": "prior_valid_discovery"},
                        )

    async def _start_p21_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or world.location != VARZEAS_BREJOS
                or member.level < 35
                or not await self._quest_completed(session, member_id, P20_ID)
                or await self._foreground(session, member_id)
            ):
                continue
            quest = await self._quest(session, member_id, P21_ID)
            if quest is not None:
                if quest.status in {"active", "completed"}:
                    await self._ensure(session, Unlock, character_id=member_id, unlock_id=VARZEAS_BREJOS_HORTOS_ROUTE)
                continue
            quest = Quest(
                character_id=member_id,
                quest_id=P21_ID,
                title=P21_TITLE,
                status="active",
                step=1,
                content_version=CONTENT_VERSION,
                state_version=0,
                progress={"beds_examined": []},
            )
            session.add(quest)
            await session.flush()
            for unlock_id in (
                VARZEAS_BREJOS_HORTOS_ROUTE,
                VARZEAS_HORTOS_HUNT_UNLOCK,
                VARZEAS_HORTOS_EXPLORE_UNLOCK,
            ):
                await self._ensure(session, Unlock, character_id=member_id, unlock_id=unlock_id)
            await self._credit(
                session,
                member_id,
                P21_ID,
                "p21.started_at_hortos_route",
                f"p21.started:{member_id}",
                {"location": VARZEAS_BREJOS, "level": member.level},
            )

    async def _start_p22_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or world.location != VARZEAS_HORTOS
                or member.level < 37
                or await self._foreground(session, member_id)
                or not await self._quest_completed(session, member_id, P21_ID)
            ):
                continue
            quest = await self._quest(session, member_id, P22_ID)
            if quest is None:
                quest = Quest(
                    character_id=member_id,
                    quest_id=P22_ID,
                    title=P22_TITLE,
                    status="active",
                    step=1,
                    content_version=CONTENT_VERSION,
                    state_version=0,
                    progress={"reservoirs_examined": [], "line_examined": False},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    member_id,
                    P22_ID,
                    "p22.started_after_p21",
                    f"p22.started:{member_id}",
                    {"location": VARZEAS_HORTOS, "level": member.level},
                )
            if quest.status == "active":
                for unlock_id in (VARZEAS_HORTOS_GALERIAS_ROUTE, VARZEAS_GALERIAS_EXPLORE_UNLOCK):
                    await self._ensure(session, Unlock, character_id=member_id, unlock_id=unlock_id)

    async def _start_p23_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or member.level < 39
                or not await self._quest_completed(session, member_id, P22_ID)
                or await self._foreground(session, member_id)
                or await self._quest(session, member_id, P23_ID) is not None
            ):
                continue
            quest = Quest(
                character_id=member_id,
                quest_id=P23_ID,
                title=P23_TITLE,
                status="active",
                step=1,
                content_version=CONTENT_VERSION,
                state_version=0,
                progress={
                    "hortos_records": False,
                    "enfermaria_record": False,
                    "galerias_records": False,
                },
            )
            session.add(quest)
            await session.flush()
            await self._credit(
                session,
                member_id,
                P23_ID,
                "p23.started_after_p22",
                f"p23.started:{member_id}",
                {"location": world.location, "level": member.level},
            )

    async def _start_p20_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or world.location != VARZEAS_PORTO
                or member.level < 33
                or await self._foreground(session, member_id)
                or not await self._quest_completed(session, member_id, P19_ID)
                or await self._quest(session, member_id, P20_ID) is not None
            ):
                continue
            quest = Quest(
                character_id=member_id,
                quest_id=P20_ID,
                title=P20_TITLE,
                status="active",
                step=1,
                content_version=CONTENT_VERSION,
                state_version=0,
                progress={"water_occurrences": []},
            )
            session.add(quest)
            await session.flush()
            await self._ensure(
                session,
                Unlock,
                character_id=member_id,
                unlock_id=VARZEAS_PORTO_BREJOS_ROUTE,
            )
            await self._credit(
                session,
                member_id,
                P20_ID,
                "p20.started_after_p19",
                f"p20.started:{member_id}",
                {"location": VARZEAS_PORTO, "level": member.level},
            )

    async def _start_p19_for_present_roster(self, session, character_ids) -> None:
        for member_id in character_ids:
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or world.region != REGION
                or world.location != VARZEAS_DIQUES
                or member.level < 31
                or await self._foreground(session, member_id)
                or not await self._quest_completed(session, member_id, "P18")
                or not await self._has_unlock(session, member_id, VARZEAS_REGION_ENTRY_UNLOCK)
            ):
                continue
            quest = await self._quest(session, member_id, P19_ID)
            if quest is None:
                quest = Quest(
                    character_id=member_id,
                    quest_id=P19_ID,
                    title=P19_TITLE,
                    status="active",
                    step=3,
                    content_version=CONTENT_VERSION,
                    state_version=0,
                    progress={"crossed_from_nareth": True, "entered_diques": True},
                )
                session.add(quest)
                await session.flush()
                for objective_id in ("p19.crossed_from_nareth", "p19.entered_diques"):
                    await self._credit(
                        session,
                        member_id,
                        P19_ID,
                        objective_id,
                        f"{objective_id}:{member_id}",
                        {"location": VARZEAS_DIQUES, "source": "authorized_region_entry"},
                    )

    async def _credit_port_arrival(self, session, character_ids) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P19_ID,
            content_version=CONTENT_VERSION,
            step=6,
            region=REGION,
            location=VARZEAS_PORTO,
        )
        for member in members:
            member.quest.step = 7
            member.quest.state_version += 1
            member.quest.progress = {**(member.quest.progress or {}), "reached_porto": True}
            await self._credit(
                session,
                member.character.id,
                P19_ID,
                "p19.reached_porto",
                f"p19.reached_porto:{member.character.id}",
                {"location": VARZEAS_PORTO},
            )
        for quest_id in (P20_ID, S20_ID):
            members = await present_campaign_members(
                session,
                character_ids=character_ids,
                quest_id=quest_id,
                content_version=CONTENT_VERSION,
                step=6,
                region=REGION,
                location=VARZEAS_PORTO,
            )
            for member in members:
                member.quest.step = 7
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "returned_to_sera": True}
                await self._credit(
                    session,
                    member.character.id,
                    quest_id,
                    f"{quest_id.lower()}.returned_to_sera",
                    f"{quest_id.lower()}.returned_to_sera:{member.character.id}",
                    {"location": VARZEAS_PORTO},
                )

    async def resume(self, actor: int, quest_id: str) -> VarzeasMissionView | None:
        if quest_id not in {P19_ID, S19_ID, P20_ID, S20_ID, P21_ID, S21_ID, P22_ID, S22_ID, P23_ID, S23_ID}:
            return None
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id, lock=False)
            world = await self._world(session, character.id, lock=False)
            view = await self._view(session, character, quest, world, quest_id)
            return await self._attach_combat(session, character, quest, world, view)

    async def resume_active(self, actor: int) -> VarzeasMissionView | None:
        await self.on_location(actor)
        for quest_id in (P23_ID, P22_ID, P21_ID, P20_ID, P19_ID, S23_ID, S22_ID, S21_ID, S20_ID, S19_ID):
            view = await self.resume(actor, quest_id)
            if view is not None and view.status == "active":
                return view
        return None

    async def board(self, actor: int) -> tuple[VarzeasMissionView | None, ...]:
        return tuple(
            [
                await self.resume(actor, P19_ID),
                await self.resume(actor, S19_ID),
                await self.resume(actor, P20_ID),
                await self.resume(actor, S20_ID),
                await self.resume(actor, P21_ID),
                await self.resume(actor, S21_ID),
                await self.resume(actor, P22_ID),
                await self.resume(actor, S22_ID),
                await self.resume(actor, P23_ID),
                await self.resume(actor, S23_ID),
            ]
        )

    async def start(self, actor: int, quest_id: str) -> VarzeasMissionView | None:
        if quest_id not in {S19_ID, S20_ID, S21_ID, S22_ID, S23_ID}:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await self._world(session, actor_row.id)
            if character is None or world is None:
                return None
            level_gate = (
                32 if quest_id == S19_ID else 34 if quest_id == S20_ID else
                35 if quest_id == S21_ID else 37 if quest_id == S22_ID else 38
            )
            prerequisite = (
                P19_ID if quest_id == S19_ID else P20_ID if quest_id == S20_ID else
                P21_ID if quest_id == S21_ID else P22_ID
            )
            giver_location = VARZEAS_PORTO if quest_id in {S19_ID, S20_ID, S23_ID} else VARZEAS_HORTOS
            prerequisite_met = (
                await self._quest_completed(session, character.id, prerequisite)
                or quest_id in {S21_ID, S22_ID}
                and await self._quest_started_or_completed(session, character.id, prerequisite)
            )
            enfermaria_discovered = quest_id != S22_ID or await self._has_unlock(
                session, character.id, "dungeon.varzeas.enfermaria_afundada.discovered"
            )
            if (
                world.region != REGION
                or world.location != giver_location
                or character.level < level_gate
                or await self._foreground(session, character.id)
                or not prerequisite_met
                or not enfermaria_discovered
            ):
                return await self._view(
                    session,
                    character,
                    await self._quest(session, character.id, quest_id),
                    world,
                    quest_id,
                )
            for member_id in character_ids:
                member = await session.scalar(
                    select(Character).where(Character.id == member_id).with_for_update()
                )
                member_world = await self._world(session, member_id)
                if (
                    member is None
                    or member_world is None
                    or member_world.region != REGION
                    or member_world.location != giver_location
                    or member.level < level_gate
                    or await self._foreground(session, member_id)
                    or not await self._quest_completed(session, member_id, prerequisite)
                    and not (quest_id in {S21_ID, S22_ID} and await self._quest_started_or_completed(session, member_id, prerequisite))
                    or quest_id == S22_ID
                    and not await self._has_unlock(session, member_id, "dungeon.varzeas.enfermaria_afundada.discovered")
                    or await self._quest(session, member_id, quest_id) is not None
                ):
                    continue
                quest = Quest(
                    character_id=member_id,
                    quest_id=quest_id,
                    title={S19_ID: S19_TITLE, S20_ID: S20_TITLE, S21_ID: S21_TITLE, S22_ID: S22_TITLE, S23_ID: S23_TITLE}[quest_id],
                    status="active",
                    step=1,
                    content_version=CONTENT_VERSION,
                    state_version=0,
                    progress=(
                        {"corrosion_points": []}
                        if quest_id == S19_ID
                        else {"observed_tracks": False}
                        if quest_id == S20_ID
                        else {"sector_examined": False, "grafts_observed": False}
                        if quest_id == S21_ID
                        else {"routines_examined": False, "preparation_recorded": False}
                        if quest_id == S22_ID
                        else {"transfer_lines_investigated": False, "emergency_markings_identified": False, "ethical_limits_recorded": False}
                    ),
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    member_id,
                    quest_id,
                    (
                        "s19.received_from_sera_morn"
                        if quest_id == S19_ID
                        else "s20.received_from_sera_morn"
                        if quest_id == S20_ID
                        else "s21.received_from_ilyan_korr"
                        if quest_id == S21_ID
                        else "s22.received_from_ilyan_korr"
                        if quest_id == S22_ID
                        else "s23.received_from_sera_morn"
                    ),
                    f"{quest_id.lower()}.started:{member_id}",
                    {"giver": "Ilyan Korr" if quest_id in {S21_ID, S22_ID} else "Sera Morn", "location": giver_location},
                )
            return await self._view(
                session,
                character,
                await self._quest(session, character.id, quest_id),
                world,
                quest_id,
            )

    async def advance(self, actor: int, quest_id: str, version: int, action: str):
        if quest_id not in {P19_ID, S19_ID, P20_ID, S20_ID, P21_ID, S21_ID, P22_ID, S22_ID, P23_ID, S23_ID}:
            return None
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
            quest = await self._quest(session, actor_row.id, quest_id)
            if character is None or world is None or quest is None:
                return None
            if (
                quest.status != "active"
                or quest.content_version != CONTENT_VERSION
                or quest.state_version != version
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, quest_id)
            members = await present_campaign_members(
                session,
                character_ids=character_ids,
                quest_id=quest_id,
                content_version=CONTENT_VERSION,
                step=quest.step,
                region=REGION,
                location=world.location,
            )
            if quest_id == P19_ID:
                await self._advance_p19(session, members, world.location, action)
            elif quest_id == S19_ID:
                await self._advance_s19(session, members, world.location, action)
            elif quest_id == P20_ID:
                await self._advance_p20(session, members, world.location, action)
            elif quest_id == P21_ID:
                await self._advance_p21(session, members, world.location, action)
            elif quest_id == S21_ID:
                await self._advance_s21(session, members, world.location, action)
            elif quest_id == P22_ID:
                await self._advance_p22(session, members, world.location, action)
            elif quest_id == S22_ID:
                await self._advance_s22(session, members, world.location, action)
            elif quest_id == P23_ID:
                await self._advance_p23(session, members, world.location, action)
            elif quest_id == S23_ID:
                await self._advance_s23(session, members, world.location, action)
            else:
                await self._advance_s20(session, members, world.location, action)
            return await self._view(
                session,
                character,
                await self._quest(session, character.id, quest_id),
                world,
                quest_id,
            )

    async def _advance_p19(self, session, members, location: str, action: str) -> None:
        expected = {
            (3, VARZEAS_DIQUES, "inspect_water"): 4,
            (4, VARZEAS_DIQUES, "register_dique_brazier"): 5,
            (5, VARZEAS_DIQUES, "follow_safe_route"): 6,
            (7, VARZEAS_PORTO, "register_porto_brazier"): 8,
            (8, VARZEAS_PORTO, "speak_sera"): 9,
        }
        if not members:
            return
        old_step = members[0].quest.step
        if action == "record_codex" and (old_step, location) == (9, VARZEAS_PORTO):
            for member in members:
                member.quest.step = 10
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "completed": True}
                await self._ensure_codex(session, member.character.id, ROTAS_CODEX)
                await self._ensure(session, CodexFragment, character_id=member.character.id, entry_id=ROTAS_CODEX, fragment_id=ROTAS_FRAGMENT)
                await self._credit(session, member.character.id, P19_ID, "p19.recorded_routes", f"p19.codex:{member.character.id}", {"codex_entry": ROTAS_CODEX})
                await self._reward(session, member.character, P19_ID, P19_REWARD_SOURCE, 34300, 570, (("material.varzeas.ferro_de_salmoura", 1), ("material.varzeas.couro_de_varzea", 1)))
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_HUNT_UNLOCK)
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_EXPLORE_UNLOCK)
                await reconcile_varzeas_feats(session, member.character)
                await consolidate_character_level(session, member.character)
            return
        next_step = expected.get((old_step, location, action))
        if next_step is None:
            return
        for member in members:
            member.quest.step = next_step
            member.quest.state_version += 1
            objective = {
                "inspect_water": "p19.examined_water_and_gate",
                "register_dique_brazier": "p19.registered_dique_brazier",
                "follow_safe_route": "p19.followed_safe_route",
                "register_porto_brazier": "p19.registered_porto_brazier",
                "speak_sera": "p19.spoke_with_sera_morn",
            }[action]
            member.quest.progress = {**(member.quest.progress or {}), objective: True}
            if action == "register_dique_brazier":
                await self._ensure(session, Brazier, character_id=member.character.id, brazier_id=VARZEAS_DIQUES_BRAZIER)
            elif action == "follow_safe_route":
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_DIQUES_PORTO_ROUTE)
            elif action == "register_porto_brazier":
                await self._ensure(session, Brazier, character_id=member.character.id, brazier_id=VARZEAS_PORTO_BRAZIER)
            elif action == "speak_sera":
                await self._ensure_codex(session, member.character.id, "codex.figure.sera_morn")
                await self._ensure(session, CodexFragment, character_id=member.character.id, entry_id="codex.figure.sera_morn", fragment_id="codex.fragment.varzeas.figure.sera_morn")
            await self._credit(session, member.character.id, P19_ID, objective, f"{objective}:{member.character.id}", {"location": location})

    async def _advance_s19(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 1 and location == VARZEAS_DIQUES and action in {"inspect_a", "inspect_b", "inspect_c"}:
            objective = f"s19.corrosion_point_{action[-1]}"
            for member in members:
                member_points = set((member.quest.progress or {}).get("corrosion_points", []))
                if action[-1] in member_points:
                    continue
                member_points.add(action[-1])
                member.quest.progress = {**(member.quest.progress or {}), "corrosion_points": sorted(member_points)}
                member.quest.state_version += 1
                await self._credit(session, member.character.id, S19_ID, objective, f"{objective}:{member.character.id}", {"location": VARZEAS_DIQUES})
                if len(member_points) == 3:
                    member.quest.step = 2
            return
        if quest.step == 2 and location == VARZEAS_DIQUES and action == "differentiate_brine_damage":
            for member in members:
                member.quest.step = 3
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "distinguished_salt_from_recent_damage": True}
                await self._credit(session, member.character.id, S19_ID, "s19.differentiated_brine", f"s19.differentiated:{member.character.id}", {"points": 3})
            return
        if quest.step == 3 and location == VARZEAS_DIQUES and action == "repair_and_record":
            for member in members:
                member.quest.step = 4
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "repair_recorded": True, "completed": True}
                await self._credit(session, member.character.id, S19_ID, "s19.repaired_and_recorded", f"s19.completed:{member.character.id}", {"location": VARZEAS_DIQUES})
                await self._reward(session, member.character, S19_ID, S19_REWARD_SOURCE, 14400, 290, ())
                await consolidate_character_level(session, member.character)

    async def _advance_p20(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 2 and location == VARZEAS_BREJOS and action in {
            "observe_pulse_a", "observe_pulse_b", "observe_pulse_c"
        }:
            point = action[-1]
            for member in members:
                occurrences = set((member.quest.progress or {}).get("water_occurrences", []))
                if point in occurrences:
                    continue
                occurrences.add(point)
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "water_occurrences": sorted(occurrences),
                }
                member.quest.state_version += 1
                if len(occurrences) == 3:
                    member.quest.step = 3
                await self._credit(
                    session,
                    member.character.id,
                    P20_ID,
                    f"p20.water_occurrence_{point}",
                    f"p20.water_occurrence_{point}:{member.character.id}",
                    {"location": VARZEAS_BREJOS},
                )
            return
        if quest.step == 3 and location == VARZEAS_BREJOS and action == "compare_buried_valves":
            for member in members:
                member.quest.step = 4
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "compared_with_buried_valves": True}
                await self._credit(
                    session,
                    member.character.id,
                    P20_ID,
                    "p20.compared_with_buried_valves",
                    f"p20.valves:{member.character.id}",
                    {"location": VARZEAS_BREJOS},
                )
            return
        if quest.step == 5 and location == VARZEAS_BREJOS and action == "examine_conduit":
            for member in members:
                member.quest.step = 6
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "examined_old_conduit": True}
                await self._credit(
                    session,
                    member.character.id,
                    P20_ID,
                    "p20.examined_old_conduit",
                    f"p20.conduit:{member.character.id}",
                    {"location": VARZEAS_BREJOS},
                )
            return
        if quest.step == 7 and location == VARZEAS_PORTO and action == "record_pulse":
            for member in members:
                member.quest.step = 8
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "recorded_prudent_interpretation": True, "completed": True}
                await self._ensure_codex(session, member.character.id, P20_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=P20_CODEX,
                    fragment_id=P20_FRAGMENT,
                )
                await self._credit(
                    session,
                    member.character.id,
                    P20_ID,
                    "p20.recorded_pulse_interpretation",
                    f"p20.codex:{member.character.id}",
                    {"codex_entry": P20_CODEX, "interpretation": "hydraulic_biological"},
                )
                await self._reward(
                    session,
                    member.character,
                    P20_ID,
                    P20_REWARD_SOURCE,
                    37800,
                    600,
                    (
                        ("material.varzeas.ferro_de_salmoura", 1),
                        ("material.varzeas.junco_ferruginoso", 2),
                        ("material.varzeas.soro_antigo", 1),
                    ),
                )
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_BREJOS_HUNT_UNLOCK)
                await self._ensure(session, Unlock, character_id=member.character.id, unlock_id=VARZEAS_BREJOS_EXPLORE_UNLOCK)
                await reconcile_varzeas_feats(session, member.character)
                await consolidate_character_level(session, member.character)

    async def _advance_s20(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        actions = {
            (1, "observe_tracks"): (2, "observed_portador_tracks"),
            (2, "follow_continuity_signs"): (3, "followed_continuity_signs"),
            (3, "locate_portador"): (4, "located_portador"),
            (5, "record_anatomy_and_environment"): (6, "recorded_anatomical_environmental_facts"),
        }
        expected_location = VARZEAS_BREJOS if quest.step <= 5 else VARZEAS_PORTO
        next_step, flag = actions.get((quest.step, action), (None, None))
        if location != expected_location or next_step is None:
            if quest.step == 7 and location == VARZEAS_PORTO and action == "report_to_sera":
                for member in members:
                    member.quest.step = 8
                    member.quest.state_version += 1
                    member.quest.status = "completed"
                    member.quest.progress = {**(member.quest.progress or {}), "reported_to_sera": True, "completed": True}
                    await self._credit(
                        session,
                        member.character.id,
                        S20_ID,
                        "s20.reported_to_sera",
                        f"s20.report:{member.character.id}",
                        {"location": VARZEAS_PORTO},
                    )
                    await self._reward(
                        session,
                        member.character,
                        S20_ID,
                        S20_REWARD_SOURCE,
                        27720,
                        460,
                        (
                            ("material.varzeas.junco_ferruginoso", 1),
                            ("material.varzeas.soro_antigo", 1),
                        ),
                    )
                    await consolidate_character_level(session, member.character)
            return
        for member in members:
            member.quest.step = next_step
            member.quest.state_version += 1
            member.quest.progress = {**(member.quest.progress or {}), flag: True}
            await self._credit(
                session,
                member.character.id,
                S20_ID,
                f"s20.{flag}",
                f"s20.{flag}:{member.character.id}",
                {"location": location},
            )

    async def _advance_p21(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 2 and location == VARZEAS_HORTOS and action in {
            "examine_bed_a", "examine_bed_b", "examine_bed_c"
        }:
            point = action[-1]
            for member in members:
                beds = set((member.quest.progress or {}).get("beds_examined", []))
                if point in beds:
                    continue
                beds.add(point)
                member.quest.progress = {**(member.quest.progress or {}), "beds_examined": sorted(beds)}
                member.quest.state_version += 1
                if len(beds) == 3:
                    member.quest.step = 3
                await self._credit(
                    session,
                    member.character.id,
                    P21_ID,
                    f"p21.examined_bed_{point}",
                    f"p21.bed_{point}:{member.character.id}",
                    {"location": VARZEAS_HORTOS},
                )
            return
        if quest.step == 4 and location == VARZEAS_HORTOS and action == "find_technical_plate":
            for member in members:
                member.quest.step = 5
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "technical_plate_found": True}
                await self._credit(
                    session,
                    member.character.id,
                    P21_ID,
                    "p21.found_hemaris_plate",
                    f"p21.plate:{member.character.id}",
                    {"observed_terms": ("cultivation", "recovery", "Hemaris")},
                )
            return
        if quest.step == 5 and location == VARZEAS_HORTOS and action == "report_to_ilyan":
            for member in members:
                member.quest.step = 6
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "reported_to_ilyan": True}
                await self._ensure_codex(session, member.character.id, "codex.figure.ilyan_korr")
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id="codex.figure.ilyan_korr",
                    fragment_id="codex.fragment.varzeas.figure.ilyan_korr",
                )
                await self._credit(
                    session,
                    member.character.id,
                    P21_ID,
                    "p21.reported_to_ilyan",
                    f"p21.report:{member.character.id}",
                    {"giver": "Ilyan Korr"},
                )
            return
        if quest.step == 6 and location == VARZEAS_HORTOS and action == "record_project_hemaris":
            for member in members:
                member.quest.step = 7
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "codex_registered": True}
                await self._ensure_codex(session, member.character.id, P21_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=P21_CODEX,
                    fragment_id=P21_FRAGMENT,
                )
                await self._credit(
                    session,
                    member.character.id,
                    P21_ID,
                    "p21.recorded_project_hemaris",
                    f"p21.codex:{member.character.id}",
                    {"codex_entry": P21_CODEX},
                )
                await reconcile_varzeas_feats(session, member.character)

    async def _advance_s21(self, session, members, location: str, action: str) -> None:
        if not members or location != VARZEAS_HORTOS:
            return
        quest = members[0].quest
        expected = {
            (1, "examine_cultivation_sector"): (2, "sector_examined"),
            (2, "observe_autonomous_grafts"): (3, "grafts_observed"),
            (3, "analyze_support_function"): (4, "support_function_recorded"),
        }
        transition = expected.get((quest.step, action))
        if transition is not None:
            next_step, flag = transition
            for member in members:
                member.quest.step = next_step
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), flag: True}
                if action == "observe_autonomous_grafts":
                    await self.road._bestiary(
                        session,
                        member.character.id,
                        VARZEAS_GARDEN_GRAFT.creature_id,
                        victory=False,
                        observation_category=VARZEAS_GARDEN_GRAFT.category,
                    )
                await self._credit(
                    session,
                    member.character.id,
                    S21_ID,
                    f"s21.{flag}",
                    f"s21.{flag}:{member.character.id}",
                    {"location": VARZEAS_HORTOS},
                )
            return
        if quest.step == 4 and action == "report_to_ilyan":
            for member in members:
                member.quest.step = 5
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "reported_to_ilyan": True,
                    "completed": True,
                }
                await self._credit(
                    session,
                    member.character.id,
                    S21_ID,
                    "s21.reported_to_ilyan",
                    f"s21.completed:{member.character.id}",
                    {"conclusion": "autonomous_support_cultures_not_transformed_people"},
                )
                await self._reward(
                    session,
                    member.character,
                    S21_ID,
                    S21_REWARD_SOURCE,
                    16580,
                    320,
                    (("material.varzeas.couro_de_varzea", 2),),
                )
                await consolidate_character_level(session, member.character)

    async def _advance_p22(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 2 and location == VARZEAS_GALERIAS and action == "register_valves_brazier":
            for member in members:
                has_brazier = await self._has_brazier(
                    session, member.character.id, VARZEAS_GALERIAS_BRAZIER
                )
                if not has_brazier:
                    discovery_source = (
                        "explore.unique:explore.varzeas.galerias.braseiro_valvulas"
                    )
                    discovery_event = await session.scalar(
                        select(RewardEvent)
                        .where(
                            RewardEvent.character_id == member.character.id,
                            RewardEvent.source_id == discovery_source,
                        )
                        .with_for_update()
                    )
                    if discovery_event is None:
                        discovery_event = RewardEvent(
                            character_id=member.character.id,
                            source_id=discovery_source,
                        )
                        session.add(discovery_event)
                        await session.flush()
                        member.character.xp += 7896
                        session.add(
                            RewardComponent(
                                reward_event_id=discovery_event.id,
                                kind="xp",
                                quantity=7896,
                            )
                        )
                        await consolidate_character_level(session, member.character)
                await self._ensure_codex(
                    session, member.character.id, "codex.location.galerias_transferencia"
                )
                await self._ensure(
                    session,
                    Brazier,
                    character_id=member.character.id,
                    brazier_id=VARZEAS_GALERIAS_BRAZIER,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id="codex.location.galerias_transferencia",
                    fragment_id="codex.fragment.varzeas.galerias.braseiro_valvulas",
                )
                member.quest.step = 3
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "brazier_registered": True}
                await self._credit(
                    session,
                    member.character.id,
                    P22_ID,
                    "p22.registered_brazier",
                    f"p22.brazier:{member.character.id}",
                    {"source": "campaign_or_prior_discovery"},
                )
            return
        if quest.step == 3 and location == VARZEAS_GALERIAS and action in {
            "examine_reservoir_a", "examine_reservoir_b", "examine_transport_line"
        }:
            for member in members:
                progress = member.quest.progress or {}
                reservoirs = set(progress.get("reservoirs_examined", []))
                line_examined = bool(progress.get("line_examined"))
                if action == "examine_reservoir_a":
                    reservoirs.add("a")
                elif action == "examine_reservoir_b":
                    reservoirs.add("b")
                else:
                    line_examined = True
                member.quest.progress = {
                    **progress,
                    "reservoirs_examined": sorted(reservoirs),
                    "line_examined": line_examined,
                }
                member.quest.state_version += 1
                if len(reservoirs) == 2 and line_examined:
                    member.quest.step = 4
                objective = action.removeprefix("examine_")
                await self._credit(
                    session,
                    member.character.id,
                    P22_ID,
                    f"p22.{objective}",
                    f"p22.{objective}:{member.character.id}",
                    {"location": VARZEAS_GALERIAS},
                )
            return
        if quest.step == 5 and location == VARZEAS_GALERIAS and action == "recover_transfer_record":
            for member in members:
                member.quest.step = 6
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "transfer_record_recovered": True}
                await self._ensure_codex(session, member.character.id, P22_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=P22_CODEX,
                    fragment_id=P22_FRAGMENT,
                )
                await self._credit(
                    session,
                    member.character.id,
                    P22_ID,
                    "p22.recovered_transfer_record",
                    f"p22.transfer_record:{member.character.id}",
                    {"term": "Transferência", "source": "technical_record"},
                )
            return
        if quest.step == 6 and location == VARZEAS_GALERIAS and action == "compare_hortos_record":
            for member in members:
                member.quest.step = 7
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), "compared_with_hortos_record": True}
                await self._credit(
                    session,
                    member.character.id,
                    P22_ID,
                    "p22.compared_hortos_record",
                    f"p22.comparison:{member.character.id}",
                    {"reference": "codex.history.projeto_hemaris_registro_inicial"},
                )
            return
        if quest.step == 7 and location == VARZEAS_HORTOS and action == "report_to_ilyan":
            for member in members:
                member.quest.step = 8
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "reported_to_ilyan": True, "completed": True}
                await self._credit(
                    session,
                    member.character.id,
                    P22_ID,
                    "p22.reported_to_ilyan",
                    f"p22.completed:{member.character.id}",
                    {"conclusion": "external biological resources supported organisms in collapse"},
                )
                await self._reward(
                    session,
                    member.character,
                    P22_ID,
                    P22_REWARD_SOURCE,
                    45300,
                    830,
                    (
                        ("material.varzeas.ferro_de_salmoura", 2),
                        ("material.varzeas.soro_antigo", 2),
                    ),
                )
                await self._ensure(
                    session,
                    Unlock,
                    character_id=member.character.id,
                    unlock_id=VARZEAS_GALERIAS_HUNT_UNLOCK,
                )
                await reconcile_varzeas_feats(session, member.character)
                await consolidate_character_level(session, member.character)
            await self._start_p23_for_present_roster(
                session, [member.character.id for member in members]
            )

    async def _advance_s22(self, session, members, location: str, action: str) -> None:
        if not members or location != VARZEAS_HORTOS:
            return
        quest = members[0].quest
        transitions = {
            (1, "inspect_automated_routines"): (2, "routines_examined"),
            (2, "record_treatment_preparation"): (3, "preparation_recorded"),
            (3, "record_no_valid_patient"): (4, "absence_of_valid_patient_recorded"),
        }
        transition = transitions.get((quest.step, action))
        if transition is not None:
            next_step, flag = transition
            for member in members:
                member.quest.step = next_step
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), flag: True}
                await self._credit(
                    session,
                    member.character.id,
                    S22_ID,
                    f"s22.{flag}",
                    f"s22.{flag}:{member.character.id}",
                    {"location": VARZEAS_HORTOS},
                )
            return
        if quest.step == 4 and action == "report_to_ilyan":
            for member in members:
                member.quest.step = 5
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {**(member.quest.progress or {}), "reported_to_ilyan": True, "completed": True}
                await self._ensure_codex(session, member.character.id, S22_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=S22_CODEX,
                    fragment_id=S22_FRAGMENT,
                )
                await self._credit(
                    session,
                    member.character.id,
                    S22_ID,
                    "s22.reported_to_ilyan",
                    f"s22.completed:{member.character.id}",
                    {"conclusion": "automated_protocol_without_valid_patient_context"},
                )
                await self._reward(
                    session,
                    member.character,
                    S22_ID,
                    S22_REWARD_SOURCE,
                    31710,
                    500,
                    (
                        ("material.varzeas.ferro_de_salmoura", 2),
                        ("material.varzeas.junco_ferruginoso", 1),
                        ("material.varzeas.soro_antigo", 1),
                    ),
                )
                await consolidate_character_level(session, member.character)

    async def _advance_p23(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        if quest.step == 1:
            record_locations = {
                (VARZEAS_HORTOS, "gather_hortos_records"): "hortos_records",
                # P23 obtains an investigative record from the Enfermaria's
                # known regional context; it does not require its optional run.
                (VARZEAS_BREJOS, "investigate_enfermaria_record"): "enfermaria_record",
                (VARZEAS_GALERIAS, "gather_galerias_records"): "galerias_records",
            }
            flag = record_locations.get((location, action))
            if flag is None:
                return
            for member in members:
                progress = {**(member.quest.progress or {}), flag: True}
                member.quest.progress = progress
                member.quest.state_version += 1
                if all(
                    progress.get(name)
                    for name in (
                        "hortos_records",
                        "enfermaria_record",
                        "galerias_records",
                    )
                ):
                    member.quest.step = 2
                await self._credit(
                    session,
                    member.character.id,
                    P23_ID,
                    f"p23.{flag}",
                    f"p23.{flag}:{member.character.id}",
                    {"location": location, "source": "campaign_investigation"},
                )
            return

        transitions = {
            (2, VARZEAS_GALERIAS, "identify_protocol_sequence"): (
                3,
                "protocol_sequence_identified",
            ),
            (3, VARZEAS_GALERIAS, "confirm_emergency_coercion"): (
                4,
                "coercion_and_external_life_recorded",
            ),
            (4, VARZEAS_GALERIAS, "record_hereditary_changes"): (
                5,
                "hereditary_changes_recorded",
            ),
            (5, VARZEAS_GALERIAS, "record_modern_hemary_distinction"): (
                6,
                "modern_hemaries_not_experiments_recorded",
            ),
            (6, VARZEAS_GALERIAS, "open_matrix_access"): (
                7,
                "matrix_access_opened",
            ),
        }
        transition = transitions.get((quest.step, location, action))
        if transition is not None:
            next_step, flag = transition
            for member in members:
                member.quest.step = next_step
                member.quest.state_version += 1
                member.quest.progress = {**(member.quest.progress or {}), flag: True}
                if flag == "matrix_access_opened":
                    await self._ensure(
                        session,
                        Unlock,
                        character_id=member.character.id,
                        unlock_id=VARZEAS_CAMARA_ACCESS_UNLOCK,
                    )
                    await self._ensure(
                        session,
                        Unlock,
                        character_id=member.character.id,
                        unlock_id=VARZEAS_GALERIAS_CAMARA_ROUTE,
                    )
                await self._credit(
                    session,
                    member.character.id,
                    P23_ID,
                    f"p23.{flag}",
                    f"p23.{flag}:{member.character.id}",
                    {"location": location},
                )
            return

        if quest.step == 7 and location == VARZEAS_GALERIAS and action == "prepare_entry_with_sera_and_ilyan":
            for member in members:
                member.quest.step = 8
                member.quest.state_version += 1
                member.quest.status = "completed"
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "entry_prepared_with_sera_and_ilyan": True,
                    "completed": True,
                }
                await self._ensure_codex(session, member.character.id, P23_COSTS_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=P23_COSTS_CODEX,
                    fragment_id=P23_COSTS_FRAGMENT,
                )
                await self._ensure_codex(session, member.character.id, P23_ANCESTRY_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=P23_ANCESTRY_CODEX,
                    fragment_id=P23_ANCESTRY_FRAGMENT,
                )
                await self._credit(
                    session,
                    member.character.id,
                    P23_ID,
                    "p23.prepared_entry_with_sera_and_ilyan",
                    f"p23.completed:{member.character.id}",
                    {"location": VARZEAS_GALERIAS, "companions": ("Sera Morn", "Ilyan Korr")},
                )
                await self._reward(
                    session,
                    member.character,
                    P23_ID,
                    P23_REWARD_SOURCE,
                    49350,
                    860,
                    (
                        ("material.varzeas.ferro_de_salmoura", 2),
                        ("material.varzeas.junco_ferruginoso", 1),
                        ("material.varzeas.soro_antigo", 1),
                    ),
                )
                await reconcile_varzeas_feats(session, member.character)
                await consolidate_character_level(session, member.character)

    async def _advance_s23(self, session, members, location: str, action: str) -> None:
        if not members:
            return
        quest = members[0].quest
        transitions = {
            (1, VARZEAS_GALERIAS, "investigate_transfer_lines"): (
                2,
                "transfer_lines_investigated",
            ),
            (2, VARZEAS_GALERIAS, "identify_emergency_markings"): (
                3,
                "emergency_markings_identified",
            ),
            (3, VARZEAS_GALERIAS, "record_progressive_ethical_limits"): (
                4,
                "progressive_ethical_limits_recorded",
            ),
            (4, VARZEAS_PORTO, "report_to_sera"): (5, "reported_to_sera"),
        }
        transition = transitions.get((quest.step, location, action))
        if transition is None:
            return
        next_step, flag = transition
        for member in members:
            member.quest.step = next_step
            member.quest.state_version += 1
            member.quest.progress = {**(member.quest.progress or {}), flag: True}
            await self._credit(
                session,
                member.character.id,
                S23_ID,
                f"s23.{flag}",
                f"s23.{flag}:{member.character.id}",
                {"location": location},
            )
            if next_step == 5:
                member.quest.status = "completed"
                member.quest.progress = {**member.quest.progress, "completed": True}
                await self._ensure_codex(session, member.character.id, S23_CODEX)
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=member.character.id,
                    entry_id=S23_CODEX,
                    fragment_id=S23_FRAGMENT,
                )
                await self._reward(
                    session,
                    member.character,
                    S23_ID,
                    S23_REWARD_SOURCE,
                    33110,
                    500,
                    (
                        ("material.varzeas.ferro_de_salmoura", 1),
                        ("material.varzeas.junco_ferruginoso", 1),
                        ("material.varzeas.soro_antigo", 2),
                    ),
                )
                await consolidate_character_level(session, member.character)

    async def choose_p21_reward(self, actor: int, version: int, choice: str):
        if choice not in P21_REWARD_CHOICES:
            return await self.resume(actor, P21_ID)
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            quest = await self._quest(session, character.id, P21_ID)
            world = await self._world(session, character.id)
            if (
                quest is None
                or world is None
                or quest.status != "active"
                or quest.content_version != CONTENT_VERSION
                or quest.state_version != version
                or quest.step != 7
                or world.region != REGION
                or world.location != VARZEAS_HORTOS
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, P21_ID)
            existing = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P21_REWARD_SOURCE,
                ).with_for_update()
            )
            selected = choice
            if existing is None:
                name, slot = P21_REWARD_CHOICES[choice]
                payload = materialize_equipment(
                    f"{P21_REWARD_SOURCE}:{character.id}:{choice}",
                    "Raro",
                    35,
                    forced_name=name,
                    forced_slot=slot,
                    bound=True,
                )
                event = RewardEvent(character_id=character.id, source_id=P21_REWARD_SOURCE)
                session.add(event)
                await session.flush()
                character.xp += 41450
                character.crowns += 630
                session.add_all(
                    (
                        RewardComponent(reward_event_id=event.id, kind="xp", quantity=41450),
                        RewardComponent(reward_event_id=event.id, kind="crowns", quantity=630),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="equipment",
                            quantity=1,
                            payload=payload | {"choice": choice},
                        ),
                    )
                )
                source_key = f"{P21_REWARD_SOURCE}:equipment:{choice}"
                if await self.road._inventory_slots(session, character.id) < 60:
                    item_id, instance = equipment_instance_payload(payload)
                    session.add(
                        EquipmentItem(
                            id=item_id,
                            character_id=character.id,
                            source_key=source_key,
                            item_name=instance["item_name"],
                            rarity=instance["rarity"],
                            slot=instance["slot"],
                            item_level=instance["item_level"],
                            bound=True,
                            payload=instance,
                        )
                    )
                else:
                    await self.road._pending(
                        session, character.id, source_key, "equipment", payload
                    )
            else:
                saved = await session.scalar(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == existing.id,
                        RewardComponent.kind == "equipment",
                    )
                )
                if saved is not None and isinstance(saved.payload, dict):
                    selected = str(saved.payload.get("choice", choice))
            quest.status = "completed"
            quest.step = 8
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "reward_choice": selected,
            }
            quest.state_version += 1
            await reconcile_varzeas_feats(session, character)
            await consolidate_character_level(session, character)
            return await self._view(session, character, quest, world, P21_ID)

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(character and await self._has_unlock(session, character.id, VARZEAS_REGION_ENTRY_UNLOCK))

    async def known_locations(self, actor: int) -> set[str]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return set()
            ids = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character.id,
                            LocationDiscovery.location_id.in_(
                                (
                                    VARZEAS_DIQUES_LOCATION,
                                    VARZEAS_PORTO_LOCATION,
                                    VARZEAS_BREJOS_LOCATION,
                                    VARZEAS_HORTOS_LOCATION,
                                    VARZEAS_GALERIAS_LOCATION,
                                    VARZEAS_CAMARA_LOCATION,
                                )
                            ),
                        )
                    )
                ).all()
            )
            return {
                label
                for key, label in (
                    (VARZEAS_DIQUES_LOCATION, VARZEAS_DIQUES),
                    (VARZEAS_PORTO_LOCATION, VARZEAS_PORTO),
                    (VARZEAS_BREJOS_LOCATION, VARZEAS_BREJOS),
                    (VARZEAS_HORTOS_LOCATION, VARZEAS_HORTOS),
                    (VARZEAS_GALERIAS_LOCATION, VARZEAS_GALERIAS),
                    (VARZEAS_CAMARA_LOCATION, VARZEAS_CAMARA),
                )
                if key in ids
            }

    async def _view(self, session, character, quest, world, quest_id) -> VarzeasMissionView:
        location = world.location if world is not None else ""
        if quest is None:
            available = False
            if quest_id == S19_ID:
                available = bool(
                    character.level >= 32
                    and location == VARZEAS_PORTO
                    and world is not None
                    and world.region == REGION
                    and await self._quest_completed(session, character.id, P19_ID)
                )
            elif quest_id == S20_ID:
                available = bool(
                    character.level >= 34
                    and location == VARZEAS_PORTO
                    and world is not None
                    and world.region == REGION
                    and await self._quest_completed(session, character.id, P20_ID)
                )
            elif quest_id == S21_ID:
                available = bool(
                    character.level >= 35
                    and location == VARZEAS_HORTOS
                    and world is not None
                    and world.region == REGION
                    and await self._quest_started_or_completed(session, character.id, P21_ID)
                )
            elif quest_id == S22_ID:
                available = bool(
                    character.level >= 37
                    and location == VARZEAS_HORTOS
                    and world is not None
                    and world.region == REGION
                    and await self._quest_started_or_completed(session, character.id, P22_ID)
                    and await self._has_unlock(
                        session,
                        character.id,
                        "dungeon.varzeas.enfermaria_afundada.discovered",
                    )
                )
            elif quest_id == S23_ID:
                available = bool(
                    character.level >= 38
                    and location == VARZEAS_PORTO
                    and world is not None
                    and world.region == REGION
                    and await self._quest_completed(session, character.id, P22_ID)
                )
            title = {
                P19_ID: P19_TITLE,
                S19_ID: S19_TITLE,
                P20_ID: P20_TITLE,
                S20_ID: S20_TITLE,
                P21_ID: P21_TITLE,
                S21_ID: S21_TITLE,
                P22_ID: P22_TITLE,
                S22_ID: S22_TITLE,
                P23_ID: P23_TITLE,
                S23_ID: S23_TITLE,
            }[quest_id]
            return VarzeasMissionView(character.id, quest_id, title, "offer" if available else "unavailable", None, None, 0, {}, location, character.level, available)
        if quest.status == "completed":
            kind = "completed"
        elif quest_id == P19_ID:
            kind = {3: "inspect_water", 4: "register_dique_brazier", 5: "follow_safe_route", 6: "arrive_porto", 7: "register_porto_brazier", 8: "speak_sera", 9: "record_codex"}.get(quest.step, "active")
        elif quest_id == P20_ID:
            kind = {
                1: "travel_brejos",
                2: "water_occurrences",
                3: "compare_valves",
                4: "combat_start",
                5: "examine_conduit",
                6: "return_sera",
                7: "record_pulse",
            }.get(quest.step, "active")
        elif quest_id == S20_ID:
            kind = {
                1: "observe_tracks",
                2: "follow_continuity_signs",
                3: "locate_portador",
                4: "combat_start",
                5: "record_anatomy_and_environment",
                6: "return_sera",
                7: "report_to_sera",
            }.get(quest.step, "active")
        elif quest_id == P21_ID:
            kind = {
                1: "travel_hortos",
                2: "examine_beds",
                3: "combat_start",
                4: "find_technical_plate",
                5: "report_to_ilyan",
                6: "record_project_hemaris",
                7: "choose_reward",
            }.get(quest.step, "active")
        elif quest_id == S21_ID:
            kind = {
                1: "examine_cultivation_sector",
                2: "observe_autonomous_grafts",
                3: "analyze_support_function",
                4: "report_to_ilyan",
            }.get(quest.step, "active")
        elif quest_id == P22_ID:
            kind = {
                1: "travel_galerias",
                2: "register_valves_brazier",
                3: "examine_transfer_infrastructure",
                4: "combat_start",
                5: "recover_transfer_record",
                6: "compare_hortos_record",
                7: "return_to_ilyan",
            }.get(quest.step, "active")
        elif quest_id == S22_ID:
            kind = {
                1: "inspect_automated_routines",
                2: "record_treatment_preparation",
                3: "record_no_valid_patient",
                4: "report_to_ilyan",
            }.get(quest.step, "active")
        elif quest_id == P23_ID:
            kind = {
                1: "gather_regional_records",
                2: "identify_protocol_sequence",
                3: "confirm_emergency_coercion",
                4: "record_hereditary_changes",
                5: "record_modern_hemary_distinction",
                6: "open_matrix_access",
                7: "prepare_entry_with_sera_and_ilyan",
            }.get(quest.step, "active")
        elif quest_id == S23_ID:
            kind = {
                1: "investigate_transfer_lines",
                2: "identify_emergency_markings",
                3: "record_progressive_ethical_limits",
                4: "report_to_sera",
            }.get(quest.step, "active")
        elif quest.step == 1:
            kind = "corrosion_points"
        elif quest.step == 2:
            kind = "differentiate_brine_damage"
        else:
            kind = "repair_and_record"
        return VarzeasMissionView(character.id, quest_id, quest.title, kind, quest.status, quest.step, quest.state_version, quest.progress or {}, location, character.level)

    @staticmethod
    def _combat_config(quest_id: str):
        if quest_id == P20_ID:
            return 4, VARZEAS_BREJOS, 33, VARZEAS_REED_SPIDER
        if quest_id == S20_ID:
            return 4, VARZEAS_BREJOS, None, VARZEAS_CRIMSON_BEARER
        if quest_id == P21_ID:
            return 3, VARZEAS_HORTOS, 35, VARZEAS_RUST_DEER
        if quest_id == P22_ID:
            return 4, VARZEAS_GALERIAS, 37, VARZEAS_HEMARIS_WARDEN
        return None

    @staticmethod
    def _mission_enemy_level(character, quest_id: str, creature) -> int:
        if quest_id == P20_ID:
            return 33
        if quest_id == P21_ID:
            return 35
        if quest_id == P22_ID:
            return 37
        return min(max(character.level, creature.unlock_level), creature.max_level)

    async def _attach_combat(self, session, character, quest, world, view):
        activity_id_text = (quest.progress or {}).get("activity_id") if quest is not None else None
        if not activity_id_text:
            return view
        try:
            activity_id = UUID(str(activity_id_text))
        except (TypeError, ValueError):
            return view
        activity = await session.get(GameActivity, activity_id)
        if activity is None:
            return view
        shared, member, combat = await campaign_combat_for_activity(
            session, activity_id, character.id
        )
        if shared is not None and member is not None and combat is not None:
            config = self._combat_config(quest.quest_id) if quest is not None else None
            consumables = await consumable_state(
                session,
                character,
                combat,
                config[3].category if config is not None else "common",
                actor_key=member.actor_key,
            )
            return replace(
                view,
                kind="combat",
                combat=combat,
                activity_id=activity_id,
                encounter_id=shared.id,
                combat_actor_key=member.actor_key,
                group_size=shared.roster_size,
                consumable_options=consumables[0],
                consumable_quantities=consumables[1],
                consumable_budget_limit=consumables[2],
            )
        if activity.status != "active":
            return view
        combat, encounter, _record = await current_combat(session, activity)
        if combat is None:
            return view
        config = self._combat_config(quest.quest_id)
        category = config[3].category if config else "common"
        consumables = await consumable_state(session, character, combat, category)
        return replace(
            view,
            kind="combat",
            combat=combat,
            activity_id=activity.id,
            encounter_id=encounter.id if encounter is not None else activity.id,
            combat_actor_key="player",
            consumable_options=consumables[0],
            consumable_quantities=consumables[1],
            consumable_budget_limit=consumables[2],
        )

    async def start_solo_combat(self, actor: int, quest_id: str, version: int):
        config = self._combat_config(quest_id)
        if config is None:
            return await self.resume(actor, quest_id)
        expected_step, location, fixed_level, creature = config
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if (
                quest is None
                or world is None
                or quest.status != "active"
                or quest.content_version != CONTENT_VERSION
                or quest.state_version != version
                or quest.step != expected_step
                or world.region != REGION
                or world.location != location
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, quest_id)
            enemy_level = fixed_level or self._mission_enemy_level(character, quest_id, creature)
            activity = await materialize(
                session,
                character,
                MISSION_CONTENT_IDS[quest_id],
                creature,
                enemy_level,
                flavor=(
                    f"{creature.name} bloqueia o setor de cultivo."
                    if quest_id == P21_ID
                    else f"{creature.name} guarda a linha de transporte."
                    if quest_id == P22_ID
                    else f"{creature.name} bloqueia a passagem entre os juncos."
                ),
                opening_log=f"{creature.name} surge à frente.",
            )
            await self.road._bestiary(
                session,
                character.id,
                creature.creature_id,
                victory=False,
                observation_category=creature.category,
            )
            quest.progress = {**(quest.progress or {}), "activity_id": str(activity.id), "awaiting_retry": False}
            quest.state_version += 1
            view = await self._view(session, character, quest, world, quest_id)
            return await self._attach_combat(session, character, quest, world, view)

    async def propose_group_combat(self, actor: int, quest_id: str, version: int):
        config = self._combat_config(quest_id)
        initial = await self.resume(actor, quest_id)
        if config is None or initial is None or initial.status != "active" or initial.step != config[0]:
            return initial
        if self.groups is None:
            return await self.start_solo_combat(actor, quest_id, version)
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, quest_id, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_varzeas",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": quest_id,
                "checkpoint": MISSION_CHECKPOINTS[quest_id],
                "title": f"{initial.title} · Encontro Roteirizado",
                "reference_character_id": str(initial.character_id),
                "location": config[1],
                "creature_id": config[3].creature_id,
            },
            journey_reference_character_id=initial.character_id,
        )
        return replace(initial, proposal_id=proposal.proposal_id, proposal_status=proposal.status)

    async def start_group_combat(self, actor: int, proposal_id: UUID, *, expected_revision: int):
        if self.groups is None:
            return await self.resume_active(actor)
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._combat_eligibility,
            create_activity=self._create_group_combat,
        )
        return await self.resume_active(actor)

    async def _combat_eligibility(self, session, character, payload) -> ActivityEligibility:
        quest_id = payload.get("quest_id")
        config = self._combat_config(quest_id)
        quest = await self._quest(session, character.id, quest_id) if config else None
        world = await self._world(session, character.id)
        active = await self._foreground(session, character.id)
        same_location = bool(
            config
            and world is not None
            and world.region == REGION
            and world.location == payload.get("location") == config[1]
        )
        required_level = (
            33 if quest_id == P20_ID
            else 35 if quest_id == P21_ID
            else 37 if quest_id == P22_ID
            else 34
        )
        if active is not None or not same_location or character.level < required_level:
            role = "ineligible"
        elif quest is not None and quest.status == "active" and quest.step == config[0]:
            role = "eligible"
        elif quest is None or quest.status == "completed" or quest.step > config[0]:
            role = "helper"
        else:
            role = "ineligible"
        snapshot = {
            "character_id": str(character.id),
            "role": role,
            "quest_status": quest.status if quest else None,
            "quest_step": quest.step if quest else None,
            "quest_version": quest.state_version if quest else None,
            "location": world.location if world else None,
            "region": world.region if world else None,
            "active_activity": str(active) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
        }
        fingerprint = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_group_combat(self, session, proposal, characters) -> str:
        quest_id = proposal.context_payload.get("quest_id")
        config = self._combat_config(quest_id)
        if config is None:
            raise GroupError("invalid_activity")
        expected_step, location, fixed_level, creature = config
        participants = list((await session.scalars(
            select(GroupActivityParticipant)
            .where(GroupActivityParticipant.proposal_id == proposal.id)
            .order_by(GroupActivityParticipant.ordinal)
        )).all())
        participant_by_id = {row.character_id: row for row in participants}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        party = []
        roster = []
        for index, character in enumerate(characters, start=1):
            participant = participant_by_id.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            actor_key = campaign_actor_key(index, len(characters))
            party.append(PlayerCombatantSpec(
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
            ))
            roster.append(CampaignRosterMember(
                character=character,
                actor_key=actor_key,
                role=participant.eligibility,
                checkpoint=MISSION_CHECKPOINTS[quest_id],
            ))
        lead = characters[0]
        reference_id = proposal.context_payload.get("reference_character_id")
        reference_character = next(
            (character for character in characters if str(character.id) == reference_id),
            lead,
        )
        enemy_level = fixed_level or self._mission_enemy_level(
            reference_character, quest_id, creature
        )
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (CreatureCombatantSpec(creature, enemy_level, "enemy"),),
            player_level=lead.level,
            equipment_configuration=party[0].equipment_configuration,
            ruleset_version=RULESET,
            flavor=(
                f"{creature.name} guarda a linha de transporte."
                if quest_id == P22_ID
                else f"{creature.name} bloqueia a passagem entre os juncos."
            ),
            opening_log=f"{creature.name} surge à frente.",
            active_art_ids=party[0].active_art_ids,
            party=tuple(party),
        )
        encounter = await create_campaign_encounter(
            session,
            group=group,
            proposal=proposal,
            roster=roster,
            quest_id=quest_id,
            content_id=MISSION_CONTENT_IDS[quest_id],
            combat=combat,
            ruleset_version=RULESET,
            checkpoint=MISSION_CHECKPOINTS[quest_id],
        )
        for member in roster:
            await self.road._bestiary(
                session,
                member.character.id,
                creature.creature_id,
                victory=False,
                observation_category=creature.category,
            )
            if member.role == "eligible":
                quest = await self._quest(session, member.character.id, quest_id)
                shared_member = await session.scalar(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id,
                        CampaignSharedEncounterMember.character_id == member.character.id,
                    )
                )
                if quest is not None and shared_member is not None:
                    quest.progress = {**(quest.progress or {}), "activity_id": str(shared_member.game_activity_id), "awaiting_retry": False}
                    quest.state_version += 1
        return str(encounter.id)

    async def action_combat(self, actor: int, activity_id: UUID, version: int, action=None, *, consumable_id=None, target_id=None, effect_id=None):
        shared_view = await self._shared_action(
            actor, activity_id, version, action,
            consumable_id=consumable_id, target_id=target_id, effect_id=effect_id,
        )
        if shared_view is not None:
            return shared_view
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id.in_(tuple(MISSION_CONTENT_IDS.values())),
                ).with_for_update()
            )
            if activity is None:
                return None
            quest_id = next((key for key, content_id in MISSION_CONTENT_IDS.items() if content_id == activity.content_id), None)
            quest = await self._quest(session, character.id, quest_id) if quest_id else None
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return None
            combat, _, _record = await current_combat(session, activity)
            config = self._combat_config(quest_id)
            if activity.status != "active" or combat is None or combat.version != version or config is None or quest.step != config[0]:
                current = await self._view(session, character, quest, world, quest_id)
                return await self._attach_combat(session, character, quest, world, current)
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=config[3].category,
            )
            if updated is None or updated.version == version:
                current = await self._view(session, character, quest, world, quest_id)
                return await self._attach_combat(session, character, quest, world, current)
            if updated.result == "victory":
                activity.status = "completed"
                await normalize_character_hp(session, character)
                quest.step += 1
                quest.progress = {**(quest.progress or {}), "activity_id": None, "awaiting_retry": False, "combat_victory": True}
                await self.road._bestiary(session, character.id, config[3].creature_id, victory=True, observation_category=config[3].category)
                await self._credit(session, character.id, quest_id, f"{quest_id.lower()}.scripted_encounter_victory", f"{quest_id.lower()}.combat:{activity.id}", {"result": "victory", "location": world.location})
            elif updated.result == "defeat":
                activity.status = "failed"
                character.hp = character.max_hp
                quest.progress = {**(quest.progress or {}), "activity_id": None, "awaiting_retry": True}
            if updated.result is not None:
                quest.state_version += 1
            view = await self._view(session, character, quest, world, quest_id)
            if updated.result is None:
                return await self._attach_combat(session, character, quest, world, view)
            return view

    async def campaign_action(self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            _shared, member, combat = await campaign_combat_for_activity(session, activity_id, character.id)
            if member is None or combat is None:
                return None
            intent = campaign_action_intent(combat, member.actor_key, action_index, target_code)
            if intent is None:
                return await self._view_for_activity(session, character, activity_id)
            action, target_id = intent
        return await self.action_combat(actor, activity_id, version, action, target_id=target_id)

    async def consumable_selection(self, actor: int, activity_id: UUID, version: int, **kwargs):
        current = await self._combat_view_for_actor(actor, activity_id)
        if current is None or current.combat is None:
            return current
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
        return derive_consumable_selection(current, **kwargs)

    async def _shared_action(self, actor, activity_id, version, action, *, consumable_id=None, target_id=None, effect_id=None):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            shared, member, _combat = await campaign_combat_for_activity(session, activity_id, seed.id)
            if shared is None or member is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id not in MISSION_CONTENT_IDS:
                return None
            quest_id = locked.encounter.quest_id
            config = self._combat_config(quest_id)
            character = locked.characters.get(seed.id)
            if config is None or character is None:
                return None
            stack = None
            if consumable_id is not None:
                stack = await session.scalar(
                    select(ConsumableStack).where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    ).with_for_update()
                )
                if stack is None:
                    return await self._view_for_activity(session, character, activity_id)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(config[3].category, 0),
            )
            if updated.version == locked.combat.version:
                return await self._view_for_activity(session, character, activity_id)
            if stack is not None:
                stack.quantity -= 1
            quests = {}
            for character_id, participant in locked.characters.items():
                roster_member = next(row for row in locked.members if row.character_id == character_id)
                quest = await self._quest(session, character_id, quest_id)
                quests[character_id] = quest
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    await self.road._bestiary(session, character_id, config[3].creature_id, victory=True, observation_category=config[3].category)
                    if roster_member.role == "eligible" and quest is not None:
                        quest.step += 1
                        quest.state_version += 1
                        quest.progress = {**(quest.progress or {}), "activity_id": None, "awaiting_retry": False, "combat_victory": True}
                        await self._credit(session, character_id, quest_id, f"{quest_id.lower()}.scripted_encounter_victory", f"{quest_id.lower()}.combat:{locked.encounter.id}", {"result": "victory", "shared": True})
                elif updated.result == "defeat":
                    participant.hp = participant.max_hp
                    if roster_member.role == "eligible" and quest is not None:
                        quest.state_version += 1
                        quest.progress = {**(quest.progress or {}), "activity_id": None, "awaiting_retry": True}
            if updated.result is not None:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view_for_activity(session, character, activity_id)

    async def _combat_view_for_actor(self, actor, activity_id):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            return await self._view_for_activity(session, character, activity_id)

    async def _view_for_activity(self, session, character, activity_id):
        shared, member, combat = await campaign_combat_for_activity(
            session, activity_id, character.id
        )
        activity = await session.get(GameActivity, activity_id)
        if activity is None:
            return None
        if shared is None or member is None:
            quest_id = next(
                (
                    candidate
                    for candidate, content_id in MISSION_CONTENT_IDS.items()
                    if content_id == activity.content_id
                ),
                None,
            )
            quest = await self._quest(session, character.id, quest_id, lock=False) if quest_id else None
            world = await self._world(session, character.id, lock=False)
            if quest is None:
                return None
            view = await self._view(session, character, quest, world, quest_id)
            return await self._attach_combat(session, character, quest, world, view)

        quest_id = shared.quest_id
        quest = await self._quest(session, character.id, quest_id, lock=False)
        world = await self._world(session, character.id, lock=False)
        if quest is None:
            view = VarzeasMissionView(
                character_id=character.id,
                quest_id=quest_id,
                title={
                    P20_ID: P20_TITLE,
                    S20_ID: S20_TITLE,
                    P21_ID: P21_TITLE,
                    P22_ID: P22_TITLE,
                    S22_ID: S22_TITLE,
                }.get(quest_id, S21_TITLE),
                kind="combat_result",
                status="helper",
                step=None,
                state_version=0,
                progress={"helper": True, "result": shared.status},
                location=world.location if world is not None else "",
                level=character.level,
            )
        else:
            view = await self._view(session, character, quest, world, quest_id)
        if shared.status != "active" or combat is None:
            if quest is not None:
                return replace(
                    view,
                    activity_id=None,
                    encounter_id=shared.id,
                    combat=None,
                    combat_actor_key=member.actor_key,
                    group_size=shared.roster_size,
                )
            return replace(
                view,
                kind="combat_result",
                activity_id=None,
                encounter_id=shared.id,
                combat=None,
                combat_actor_key=member.actor_key,
                group_size=shared.roster_size,
            )
        config = self._combat_config(quest_id)
        consumables = await consumable_state(
            session,
            character,
            combat,
            config[3].category if config is not None else "common",
            actor_key=member.actor_key,
        )
        return replace(
            view,
            kind="combat",
            combat=combat,
            activity_id=activity.id,
            encounter_id=shared.id,
            combat_actor_key=member.actor_key,
            group_size=shared.roster_size,
            consumable_options=consumables[0],
            consumable_quantities=consumables[1],
            consumable_budget_limit=consumables[2],
        )

    async def combat_view_for_actor(self, actor, activity_id):
        return await self._combat_view_for_actor(actor, activity_id)

    async def _reward(self, session, character, quest_id, source_id, xp, crowns, materials) -> None:
        existing = await session.scalar(select(RewardEvent).where(RewardEvent.character_id == character.id, RewardEvent.source_id == source_id).with_for_update())
        if existing is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all((RewardComponent(reward_event_id=event.id, kind="xp", quantity=xp), RewardComponent(reward_event_id=event.id, kind="crowns", quantity=crowns)))
        for material_id, quantity in materials:
            session.add(RewardComponent(reward_event_id=event.id, kind="material", item_id=material_id, quantity=quantity, payload={"material_id": material_id, "bound": True}))
            await self.road.deliver_material(session, character, material_id, quantity, f"{source_id}:material:{material_id}", bound=True)

    async def _credit(self, session, character_id, quest_id, objective_id, source_key, evidence) -> None:
        await record_campaign_objective_credit(session, character_id=character_id, quest_id=quest_id, objective_id=objective_id, source_key=source_key, evidence=evidence)

    async def _ensure_codex(self, session, character_id, entry_id) -> None:
        await self._ensure(session, CodexEntry, character_id=character_id, entry_id=entry_id)

    async def _ensure(self, session, model, **values) -> bool:
        found = await session.scalar(select(model).filter_by(**values).with_for_update())
        if found is not None:
            return False
        session.add(model(**values))
        return True

    async def _character(self, session, actor):
        return await session.scalar(select(Character).where(Character.telegram_id == actor, Character.server_id == self.server_id))

    async def _quest(self, session, character_id, quest_id, *, lock=True):
        statement = select(Quest).where(Quest.character_id == character_id, Quest.quest_id == quest_id)
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _world(self, session, character_id, *, lock=True):
        statement = select(WorldState).where(WorldState.character_id == character_id)
        return await session.scalar(statement.with_for_update() if lock else statement)

    async def _foreground(self, session, character_id):
        return await session.scalar(select(GameActivity.id).where(GameActivity.character_id == character_id, GameActivity.status == "active"))

    async def _quest_completed(self, session, character_id, quest_id):
        return bool(await session.scalar(select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == quest_id, Quest.status == "completed")))

    async def _quest_started_or_completed(self, session, character_id, quest_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == quest_id,
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _has_brazier(self, session, character_id, brazier_id):
        return bool(
            await session.scalar(
                select(Brazier.id).where(
                    Brazier.character_id == character_id,
                    Brazier.brazier_id == brazier_id,
                )
            )
        )

    async def _has_unlock(self, session, character_id, unlock_id):
        return bool(await session.scalar(select(Unlock.id).where(Unlock.character_id == character_id, Unlock.unlock_id == unlock_id)))
