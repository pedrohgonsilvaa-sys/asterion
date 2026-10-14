"""Shared, idempotent S7/P8 mission progression for Vales dos Enforcados."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.campaign_coop import (
    CampaignRosterMember,
    campaign_action_intent,
    campaign_actor_key,
    campaign_combat_for_activity,
    create_campaign_boss_profile,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
    settle_campaign_encounter,
)
from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    present_campaign_members,
    record_campaign_objective_credit,
)
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
from asterion.domain.consumables import ENCOUNTER_CONSUMABLE_LIMITS
from asterion.domain.road import (
    RULESET,
    VDE_BERCO_LOCATION,
    VDE_CLAUSTRO_BERCO_ROUTE,
    VDE_KNOT_DEER,
    VDE_MATRIARCH,
    VDE_ROOTED_WATCHER,
    VDE_TANGLED_PILGRIM,
    VDE_TURF_LEECH,
    VDE_WANDERING_BARK,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    materialize_equipment,
)
from asterion.domain.vde_matriarch import (
    configure_matriarch_combat,
    matriarch_phase_evidence,
)
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    CampaignSharedEncounterMember,
    Character,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    ConsumableStack,
    Encounter,
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

REGION = "Vales dos Enforcados"
GARGANTA = "Garganta dos Laços"
VIGILIA = "Vigília do Vale"
MATA = "Mata Suspensa"
BAIXIOS = "Baixios Enredados"
CLAUSTRO = "Claustro das Raízes"
BERCO = "Berço da Matriarca"
P7_ID = "P7"
S7_ID = "S7"
P8_ID = "P8"
S8_ID = "S8"
P9_ID = "P9"
S9_ID = "S9"
P10_ID = "P10"
S10_ID = "S10"
S11_ID = "S11"
P11_ID = "P11"
P12_ID = "P12"
S12_ID = "S12"
CONTENT_VERSION = "vales-1.0.3"
CONTENT_VERSION_MID = "vales-1.0.4"
CONTENT_VERSION_CLIMAX = "vales-1.0.4"
CONTENT_VERSION_S12 = "vales-1.0.6"
S7_TITLE = "Cordas na Névoa"
P8_TITLE = "Entre Galhos Suspensos"
S8_TITLE = "O Peso da Passagem"
P9_TITLE = "Sob a Madeira Morta"
S9_TITLE = "Sob a Casca"
P10_TITLE = "Pedra sob as Raízes"
S10_TITLE = "Água sem Reflexo"
S11_TITLE = "A Guarda que Não Dorme"
P11_TITLE = "Onde Tudo se Enreda"
P12_TITLE = "A Matriarca das Raízes"
S12_TITLE = "Os Nomes Presos à Madeira"
S7_CHECKPOINT = "vde.s7.cordas_na_nevoa"
P8_CHECKPOINT = "vde.p8.entre_galhos_suspensos"
S8_CHECKPOINT = "vde.s8.peso_da_passagem"
P9_CHECKPOINT = "vde.p9.sob_a_madeira_morta"
S9_CHECKPOINT = "vde.s9.sob_a_casca"
P10_CHECKPOINT = "vde.p10.pedra_sob_as_raizes"
S10_CHECKPOINT = "vde.s10.agua_sem_reflexo"
S11_CHECKPOINT = "vde.s11.guarda_que_nao_dorme"
P11_CHECKPOINT = "vde.p11.onde_tudo_se_enreda"
P12_CHECKPOINT = "vde.p12.a_matriarca_das_raizes"
S12_CHECKPOINT = "vde.s12.nomes_presos_madeira"
S7_CONTENT = "vde_s7_scripted_combat"
P8_CONTENT = "vde_p8_scripted_combat"
S8_CONTENT = "vde_s8_cervo_no"
P9_CONTENT = "vde_p9_casca_errante"
S9_CONTENT = "vde_s9_casca_errante"
P10_CONTENT = "vde_p10_vigia_enraizado"
S10_CONTENT = "vde_s10_scripted_combat"
S11_CONTENT = "vde_s11_vigia_enraizado"
P11_CONTENT = "vde_p11_scripted_combat"
P12_CONTENT = "vde_p12_matriarch"
S12_CONTENT = "vde_s12_peregrino_enredado"
S7_REWARD_SOURCE = "s7.cordas_na_nevoa"
P8_REWARD_SOURCE = "p8.entre_galhos_suspensos"
S8_REWARD_SOURCE = "s8.peso_da_passagem"
P9_REWARD_SOURCE = "p9.sob_a_madeira_morta"
S9_REWARD_SOURCE = "s9.sob_a_casca"
P10_REWARD_SOURCE = "p10.pedra_sob_as_raizes"
S10_REWARD_SOURCE = "s10.agua_sem_reflexo"
S11_REWARD_SOURCE = "s11.guarda_que_nao_dorme"
P11_REWARD_SOURCE = "p11.onde_tudo_se_enreda"
P12_REWARD_SOURCE = "p12.a_matriarca_das_raizes"
S12_REWARD_SOURCE = "s12.nomes_presos_madeira"
S12_CODEX_ENTRY = "codex.history.nomes_dos_vales"
S12_CODEX_FRAGMENTS = frozenset(
    {
        "codex.fragment.vales.nomes.registro_s10",
        "codex.fragment.vales.nomes.registro_final",
        "codex.fragment.vales.nomes.registro_vigilia",
    }
)
P12_NUCLEUS = "material.vde.nucleo_matriarca_das_raizes"
P12_NUCLEUS_SOURCE = "p12.matriarca.nucleo:first_victory"
P12_RECIPE_UNLOCK = "recipe.vde.matriarca.seiva"
VDE_CAMPAIGN_UNLOCK = "campaign.vde.completed"
NARETH_UNLOCK = "region.nareth.available"
MATA_LOCATION_ID = "vde.location.mata_suspensa"
BAIXIOS_LOCATION_ID = "vde.location.baixios_enredados"
MATA_ROUTE_UNLOCK = "route.vde.vigilia_mata"
MATA_HUNT_UNLOCK = "hunt.manual.vde.mata_suspensa"
MATA_EXPLORE_UNLOCK = "explore.vde.mata_suspensa"
BAIXIOS_ROUTE_UNLOCK = "route.vde.mata_baixios"
BAIXIOS_HUNT_UNLOCK = "hunt.manual.vde.baixios_enredados"
BAIXIOS_EXPLORE_UNLOCK = "explore.vde.baixios_enredados"
CLAUSTRO_LOCATION_ID = "vde.location.claustro_das_raizes"
CLAUSTRO_ROUTE_UNLOCK = "route.vde.baixios_claustro"
CLAUSTRO_HUNT_UNLOCK = "hunt.manual.vde.claustro_das_raizes"
CLAUSTRO_EXPLORE_UNLOCK = "explore.vde.claustro_das_raizes"
SANCTUARY_UNLOCK = "dungeon.vde.santuario_no_antigo"
BERCO_LOCATION_ID = VDE_BERCO_LOCATION
BERCO_ROUTE_UNLOCK = VDE_CLAUSTRO_BERCO_ROUTE

MISSION_TITLES = {
    S7_ID: S7_TITLE,
    P8_ID: P8_TITLE,
    S8_ID: S8_TITLE,
    P9_ID: P9_TITLE,
    S9_ID: S9_TITLE,
    P10_ID: P10_TITLE,
    S10_ID: S10_TITLE,
    S11_ID: S11_TITLE,
    P11_ID: P11_TITLE,
    P12_ID: P12_TITLE,
    S12_ID: S12_TITLE,
}
MISSION_VERSIONS = {
    S7_ID: CONTENT_VERSION,
    P8_ID: CONTENT_VERSION,
    S12_ID: CONTENT_VERSION_S12,
}
MISSION_CONTENT_IDS = {
    S7_ID: S7_CONTENT,
    P8_ID: P8_CONTENT,
    S8_ID: S8_CONTENT,
    P9_ID: P9_CONTENT,
    S9_ID: S9_CONTENT,
    P10_ID: P10_CONTENT,
    S10_ID: S10_CONTENT,
    S11_ID: S11_CONTENT,
    P11_ID: P11_CONTENT,
    P12_ID: P12_CONTENT,
    S12_ID: S12_CONTENT,
}
MISSION_CHECKPOINTS = {
    S7_ID: S7_CHECKPOINT,
    P8_ID: P8_CHECKPOINT,
    S8_ID: S8_CHECKPOINT,
    P9_ID: P9_CHECKPOINT,
    S9_ID: S9_CHECKPOINT,
    P10_ID: P10_CHECKPOINT,
    S10_ID: S10_CHECKPOINT,
    S11_ID: S11_CHECKPOINT,
    P11_ID: P11_CHECKPOINT,
    P12_ID: P12_CHECKPOINT,
    S12_ID: S12_CHECKPOINT,
}
P9_REWARD_CHOICES = {
    "1": ("Capuz das Copas Suspensas", "Cabeça"),
    "2": ("Selo do Caminho Enredado", "Acessório"),
    "3": ("Relicário do Nó Velado", "Artefato"),
}
P12_REWARD_CHOICES = {
    "1": ("Guarda do Berço Silente", "Torso"),
    "2": ("Selo da Rede Antiga", "Acessório"),
    "3": ("Relicário da Pedra Pulsante", "Artefato"),
}

# The regional text leaves the scripted species unnamed. This internal common
# combatant uses the global common/balanced level curve and never enters the
# Bestiary or repeatable reward settlement.
_SCRIPTED_FAUNA = Creature(
    "vde_scripted_fauna",
    "Criatura entre as raízes",
    "common",
    "balanced",
    1,
    60,
    0,
    ("investida_instintiva",),
    (("investida_instintiva", "Investida Instintiva", Decimal("1.00"), 0, Decimal(0), 0),),
)
MISSION_COMBAT = {
    S7_ID: (2, GARGANTA, 12, _SCRIPTED_FAUNA),
    P8_ID: (3, MATA, 13, _SCRIPTED_FAUNA),
    S8_ID: (3, MATA, 14, VDE_KNOT_DEER),
    P9_ID: (4, BAIXIOS, 15, VDE_WANDERING_BARK),
    S9_ID: (2, BAIXIOS, 15, VDE_WANDERING_BARK),
    P10_ID: (4, CLAUSTRO, 18, VDE_ROOTED_WATCHER),
    S10_ID: (5, BAIXIOS, 17, _SCRIPTED_FAUNA),
    S11_ID: (2, CLAUSTRO, 18, VDE_ROOTED_WATCHER),
    P11_ID: (3, CLAUSTRO, 19, _SCRIPTED_FAUNA),
    P12_ID: (5, BERCO, 20, VDE_MATRIARCH),
    S12_ID: (7, BAIXIOS, 20, VDE_TANGLED_PILGRIM),
}


@dataclass(frozen=True, slots=True)
class VDEMissionView:
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
    combat_id: UUID | None = None
    combat_actor_key: str | None = None
    group_size: int = 1
    consumable_options: tuple = ()
    consumable_quantities: tuple = ()
    consumable_budget_limit: int = 0
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    ready_consumable_option: object | None = None
    proposal_id: UUID | None = None
    proposal_status: str | None = None


class VDEMissionService:
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

    async def resume(self, actor: int, quest_id: str) -> VDEMissionView | None:
        if quest_id not in MISSION_TITLES:
            return None
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None:
                return None
            if quest_id == P12_ID and quest is not None and quest.status == "completed":
                await self._ensure_nareth_gate(session, character, quest)
            return await self._view(session, character, quest, world, requested_quest_id=quest_id)

    async def resume_active(self, actor: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character = await session.scalar(
                select(Character)
                .where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
                .with_for_update()
            )
            if character is None:
                return None
            await self._ensure_p12_started(session, character)
            p12 = await session.scalar(
                select(Quest)
                .where(Quest.character_id == character.id, Quest.quest_id == P12_ID)
                .with_for_update()
            )
            if p12 is not None and p12.status == "completed":
                await self._ensure_nareth_gate(session, character, p12)
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.character_id == character.id,
                    GameActivity.status == "active",
                    GameActivity.content_id.in_(tuple(MISSION_CONTENT_IDS.values())),
                )
                .with_for_update()
            )
            if activity is not None:
                shared, member, _combat = await campaign_combat_for_activity(
                    session, activity.id, character.id
                )
                if shared is not None and member is not None:
                    return await self._view_for_character_activity(session, character, activity.id)
                quest_id = next(
                    (
                        key
                        for key, content_id in MISSION_CONTENT_IDS.items()
                        if content_id == activity.content_id
                    ),
                    None,
                )
                quest = (
                    await session.scalar(
                        select(Quest).where(
                            Quest.character_id == character.id,
                            Quest.quest_id == quest_id,
                            Quest.status == "active",
                        )
                    )
                    if quest_id is not None
                    else None
                )
                if quest is not None:
                    return await self._view(
                        session, character, quest, await self._world(session, character.id)
                    )
        for quest_id in (
            P12_ID, P11_ID, S11_ID, S12_ID, P10_ID, S10_ID, S7_ID, P8_ID, S8_ID, P9_ID, S9_ID
        ):
            view = await self.resume(actor, quest_id)
            if view is not None and (
                view.status == "active"
                or (view.quest_id == P12_ID and view.kind == "choice")
            ):
                return view
        return None

    async def board(self, actor: int) -> tuple[VDEMissionView | None, ...]:
        return tuple(
            [
                await self.resume(actor, quest_id)
                for quest_id in (
                    S7_ID, P8_ID, S8_ID, P9_ID, S9_ID, P10_ID, S10_ID, S11_ID, P11_ID, P12_ID,
                    S12_ID,
                )
            ]
        )

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return False
            return bool(
                await session.scalar(
                    select(Quest.id).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == P7_ID,
                        Quest.status == "completed",
                    )
                )
            )

    async def start(self, actor: int, quest_id: str) -> VDEMissionView | None:
        if quest_id not in MISSION_TITLES:
            return None
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or world is None:
                return None
            if quest is not None:
                return await self._view(
                    session, character, quest, world, requested_quest_id=quest_id
                )
            prerequisite_id = {
                S7_ID: P7_ID,
                P8_ID: P7_ID,
                S8_ID: P8_ID,
                P9_ID: P8_ID,
                S9_ID: P9_ID,
                P10_ID: P9_ID,
                S10_ID: P10_ID,
                S11_ID: P10_ID,
                P11_ID: P10_ID,
                P12_ID: P11_ID,
                S12_ID: P11_ID,
            }[quest_id]
            prerequisite = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == prerequisite_id,
                    Quest.status == "completed",
                )
            )
            if quest_id == S9_ID and prerequisite is None:
                prerequisite = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == P9_ID,
                        Quest.status == "active",
                    )
                )
            if quest_id == S10_ID and prerequisite is None:
                prerequisite = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == P10_ID,
                        Quest.status == "active",
                    )
                )
            if quest_id == S11_ID:
                prerequisite = None
            if quest_id == S12_ID and prerequisite is not None:
                prerequisite = await session.scalar(
                    select(Quest.id).where(
                        Quest.character_id == character.id,
                        Quest.quest_id == S10_ID,
                        Quest.status == "completed",
                    )
                )
            required_level, required_location = {
                S7_ID: (12, GARGANTA),
                P8_ID: (13, VIGILIA),
                S8_ID: (14, MATA),
                P9_ID: (15, MATA),
                S9_ID: (15, BAIXIOS),
                P10_ID: (17, BAIXIOS),
                S10_ID: (17, BAIXIOS),
                S11_ID: (18, CLAUSTRO),
                P11_ID: (19, CLAUSTRO),
                P12_ID: (20, BERCO),
                S12_ID: (20, CLAUSTRO),
            }[quest_id]
            if quest_id == S11_ID:
                prerequisite = await session.scalar(
                    select(LocationDiscovery.id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id == CLAUSTRO_LOCATION_ID,
                    )
                )
            if (
                prerequisite is None
                or character.level < required_level
                or world.region != REGION
                or world.location != required_location
                or await self._foreground(session, character.id)
            ):
                return await self._view(
                    session, character, None, world, requested_quest_id=quest_id
                )
            progress = {
                S7_ID: {"markers": []},
                P8_ID: {"roots": []},
                S8_ID: {"structures": [], "hardware_sets": []},
                P9_ID: {"structures": []},
                S9_ID: {},
                P10_ID: {"inscriptions": []},
                S10_ID: {"markers": []},
                S11_ID: {"patrols": [], "marking_fragments": []},
                P11_ID: {"pressure_points": []},
                P12_ID: {"external_connections": [], "reward_choice": None},
                S12_ID: {"passage_mark_found": False, "personal_object_recovered": False},
            }[quest_id]
            quest = Quest(
                character_id=character.id,
                quest_id=quest_id,
                title=MISSION_TITLES[quest_id],
                status="active",
                step=1,
                content_version=self._content_version(quest_id),
                state_version=0,
                progress=progress,
            )
            session.add(quest)
            await session.flush()
            if quest_id == P8_ID:
                await self._ensure_unlock(session, character.id, MATA_ROUTE_UNLOCK)
            elif quest_id == P9_ID:
                await self._ensure_unlock(session, character.id, BAIXIOS_ROUTE_UNLOCK)
                await self._ensure_unlock(session, character.id, BAIXIOS_EXPLORE_UNLOCK)
            await record_campaign_objective_credit(
                session,
                character_id=character.id,
                quest_id=quest_id,
                objective_id=f"{quest_id.lower()}.started",
                source_key=f"{quest_id.lower()}:start:{character.id}",
                evidence={"location": world.location, "level": character.level},
            )
            return await self._view(session, character, quest, world)

    async def enter_mata(self, actor: int, version: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P8_ID)
            if not self._valid(quest, version, step=1) or character is None or world is None:
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != MATA:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P8_ID, step=1, location=MATA)
            for member in members:
                await self._ensure_location(session, member.character.id, MATA_LOCATION_ID)
                await self._ensure_unlock(session, member.character.id, MATA_EXPLORE_UNLOCK)
                member.quest.step = 2
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "entered_mata": True,
                    "roots": [],
                }
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P8_ID,
                    objective_id="p8.enter_mata",
                    source_key="p8.enter_mata:first_entry",
                    evidence={"region": REGION, "location": MATA, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def enter_baixios(self, actor: int, version: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P9_ID)
            if not self._valid(quest, version, step=2) or character is None or world is None:
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != BAIXIOS:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P9_ID, step=2, location=BAIXIOS)
            for member in members:
                await self._ensure_location(session, member.character.id, BAIXIOS_LOCATION_ID)
                member.quest.step = 3
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "entered_baixios": True,
                    "structures": [],
                }
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P9_ID,
                    objective_id="p9.enter_baixios",
                    source_key="p9.enter_baixios:first_entry",
                    evidence={"region": REGION, "location": BAIXIOS, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def open_claustro(self, actor: int, version: int) -> VDEMissionView | None:
        """Open the Claustro through the P10 journey for all eligible present members."""
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P10_ID)
            if character is None or world is None or not self._valid(quest, version, step=2):
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != BAIXIOS:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P10_ID, step=2, location=BAIXIOS)
            for member in members:
                member_world = await self._world(session, member.character.id)
                if member_world is None:
                    continue
                member_world.region = REGION
                member_world.location = CLAUSTRO
                await self._ensure_location(
                    session, member.character.id, CLAUSTRO_LOCATION_ID
                )
                await self._ensure_unlock(session, member.character.id, CLAUSTRO_ROUTE_UNLOCK)
                await self._ensure_unlock(session, member.character.id, CLAUSTRO_EXPLORE_UNLOCK)
                member.quest.step = 3
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "claustro_opened": True,
                    "inscriptions": [],
                }
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=P10_ID,
                    objective_id="p10.open_claustro",
                    source_key="p10.open_claustro:first_entry",
                    evidence={"location": CLAUSTRO, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def examine(
        self, actor: int, quest_id: str, version: int, point: str
    ) -> VDEMissionView | None:
        if quest_id not in MISSION_TITLES:
            return None
        if point not in {"a", "b", "c"}:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            quest_step, location, key, next_step = {
                S7_ID: (1, GARGANTA, "markers", 2),
                P8_ID: (2, MATA, "roots", 3),
                S8_ID: (2, MATA, "structures", 3),
                P9_ID: (3, BAIXIOS, "structures", 4),
                P10_ID: (3, CLAUSTRO, "inscriptions", 4),
                S10_ID: (1, BAIXIOS, "markers", 2),
                S11_ID: (1, CLAUSTRO, "patrols", 2),
                P11_ID: (1, CLAUSTRO, "pressure_points", 2),
                P12_ID: (3, BERCO, "external_connections", 4),
            }.get(quest_id, (0, "", "", 0))
            if character is None or not self._valid(quest, version, step=quest_step):
                return await self._view(session, character, quest, world)
            if quest_id not in {
                S7_ID, P8_ID, S8_ID, P9_ID, P10_ID, S10_ID, S11_ID, P11_ID, P12_ID
            }:
                return await self._view(session, character, quest, world)
            if quest_id == P10_ID and point == "c":
                return await self._view(session, character, quest, world)
            members = await self._present(
                session,
                character.id,
                quest_id,
                step=quest_step,
                location=location,
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                points = list(progress.get(key, ()))
                if point in points:
                    continue
                points.append(point)
                progress[key] = sorted(points)
                member.quest.progress = progress
                required_points = 2 if quest_id in {P10_ID, S11_ID} else 3
                if len(points) >= required_points:
                    member.quest.step = next_step
                member.quest.state_version += 1
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=quest_id,
                    objective_id=f"{quest_id.lower()}.{key}.{point}",
                    source_key=f"{quest_id.lower()}.{key}.{point}:{location}",
                    evidence={"location": location, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def advance(
        self, actor: int, quest_id: str, version: int, action: str
    ) -> VDEMissionView | None:
        if quest_id == P10_ID and action == "passage":
            return await self.open_claustro(actor, version)
        steps = {
            (S7_ID, "rope"): (3, GARGANTA, 4, "s7.find_rope"),
            (S7_ID, "report"): (4, VIGILIA, 5, "s7.report_dara"),
            (S8_ID, "hardware"): (4, MATA, 4, "s8.hardware_sets"),
            (P8_ID, "compare"): (4, MATA, 5, "p8.compare_roots"),
            (P8_ID, "masonry"): (5, MATA, 6, "p8.find_masonry"),
            (P8_ID, "record"): (6, MATA, 7, "p8.record_find"),
            (S8_ID, "passage"): (1, MATA, 2, "s8.supply_passage"),
            (S8_ID, "route"): (5, MATA, 6, "s8.alternate_route"),
            (S8_ID, "report"): (6, VIGILIA, 7, "s8.report_dara"),
            (P9_ID, "follow"): (1, MATA, 2, "p9.follow_trace"),
            (P9_ID, "inscription"): (5, BAIXIOS, 6, "p9.damaged_inscription"),
            (P9_ID, "fragment"): (6, BAIXIOS, 7, "p9.structural_fragment"),
            (P9_ID, "report"): (7, BAIXIOS, 8, "p9.report_iven"),
            (S9_ID, "locate"): (1, BAIXIOS, 2, "s9.locate_bark"),
            (S9_ID, "fragments"): (3, BAIXIOS, 4, "s9.inspect_fragments"),
            (S9_ID, "sample"): (4, BAIXIOS, 5, "s9.collect_sample"),
            (S9_ID, "report"): (5, BAIXIOS, 6, "s9.report_iven"),
            (P10_ID, "follow"): (1, BAIXIOS, 2, "p10.follow_p9_markers"),
            (P10_ID, "structure"): (5, CLAUSTRO, 6, "p10.inspect_structure"),
            (P10_ID, "sanctuary"): (6, CLAUSTRO, 7, "p10.discover_sanctuary"),
            (P10_ID, "report"): (7, BAIXIOS, 8, "p10.report_iven"),
            (S10_ID, "zone"): (2, BAIXIOS, 3, "s10.cross_leech_zone"),
            (S10_ID, "bag"): (3, BAIXIOS, 4, "s10.find_bag"),
            (S10_ID, "tracks"): (4, BAIXIOS, 5, "s10.follow_tracks"),
            (S10_ID, "survivor"): (6, BAIXIOS, 7, "s10.find_survivor"),
            (S10_ID, "report"): (7, VIGILIA, 8, "s10.return_survivor"),
            (S11_ID, "return_place"): (3, CLAUSTRO, 4, "s11.inspect_return_place"),
            (S11_ID, "fragment"): (4, CLAUSTRO, 4, "s11.marking_fragments"),
            (S11_ID, "report"): (5, CLAUSTRO, 6, "s11.report_iven"),
            (P11_ID, "roots"): (2, CLAUSTRO, 3, "p11.clear_roots"),
            (P11_ID, "chamber"): (4, CLAUSTRO, 5, "p11.inspect_chamber"),
            (P11_ID, "traces"): (5, CLAUSTRO, 6, "p11.record_large_creature_traces"),
            (P11_ID, "convergence"): (6, CLAUSTRO, 7, "p11.follow_root_convergence"),
            (P11_ID, "open_berco"): (7, CLAUSTRO, 8, "p11.open_berco_access"),
            (P12_ID, "enter_berco"): (1, BERCO, 2, "p12.enter_berco"),
            (P12_ID, "advance_network"): (2, BERCO, 3, "p12.advance_external_network"),
            (P12_ID, "central_chamber"): (4, BERCO, 5, "p12.reach_central_chamber"),
            (P12_ID, "examine_center"): (6, BERCO, 7, "p12.examine_center"),
            (P12_ID, "register"): (7, BERCO, 7, "p12.register_regional_discovery"),
            (S12_ID, "read_record"): (1, CLAUSTRO, 2, "s12.read_s10_record"),
            (S12_ID, "visit_garganta"): (2, GARGANTA, 3, "s12.visit_garganta"),
            (S12_ID, "find_mark"): (3, GARGANTA, 4, "s12.find_passage_mark"),
            (S12_ID, "visit_mata"): (4, MATA, 5, "s12.visit_mata"),
            (S12_ID, "recover_object"): (5, MATA, 6, "s12.recover_personal_object"),
            (S12_ID, "visit_baixios"): (6, BAIXIOS, 7, "s12.visit_baixios"),
            (S12_ID, "examine_site"): (8, BAIXIOS, 9, "s12.examine_site"),
            (S12_ID, "visit_claustro"): (9, CLAUSTRO, 10, "s12.visit_claustro"),
            (S12_ID, "last_record"): (10, CLAUSTRO, 11, "s12.find_last_record"),
            (S12_ID, "report_iven"): (11, CLAUSTRO, 12, "s12.return_to_iven"),
            (S12_ID, "register_names"): (12, VIGILIA, 12, "s12.record_names_vigilia"),
        }
        config = steps.get((quest_id, action))
        if config is None:
            return await self.resume(actor, quest_id)
        expected_step, location, next_step, objective_id = config
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or not self._valid(quest, version, step=expected_step):
                return await self._view(session, character, quest, world)
            if world is None or world.region != REGION or world.location != location:
                return await self._view(session, character, quest, world)
            members = await self._present(
                session, character.id, quest_id, step=expected_step, location=location
            )
            for member in members:
                if quest_id == S7_ID and action == "report":
                    await self._complete_s7(session, member.character, member.quest)
                    continue
                if quest_id == S8_ID and action == "report":
                    await self._complete_s8(session, member.character, member.quest)
                    continue
                if quest_id == S9_ID and action == "report":
                    await self._complete_s9(session, member.character, member.quest)
                    continue
                if quest_id == P10_ID and action == "report":
                    await self._complete_p10(session, member.character, member.quest)
                    continue
                if quest_id == S10_ID and action == "report":
                    await self._complete_s10(session, member.character, member.quest)
                    continue
                if quest_id == S11_ID and action == "report":
                    await self._complete_s11(session, member.character, member.quest)
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=quest_id,
                        objective_id=objective_id,
                        source_key=f"{objective_id}:{location}",
                        evidence={"location": location, "shared": len(members) > 1},
                    )
                    continue
                if quest_id == P11_ID and action == "open_berco":
                    await self._ensure_location(session, member.character.id, BERCO_LOCATION_ID)
                    await self._ensure_unlock(session, member.character.id, BERCO_ROUTE_UNLOCK)
                    await self._record_p11_codex(session, member.character.id)
                    await self._complete_p11(session, member.character, member.quest)
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=quest_id,
                        objective_id=objective_id,
                        source_key=f"{objective_id}:{location}",
                        evidence={"location": BERCO, "shared": len(members) > 1},
                    )
                    continue
                if quest_id == P12_ID and action == "register":
                    await self._complete_p12(session, member.character, member.quest)
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=P12_ID,
                        objective_id=objective_id,
                        source_key=f"{objective_id}:{member.character.id}",
                        evidence={"location": BERCO, "shared": len(members) > 1},
                    )
                    continue
                if quest_id == S12_ID and action == "register_names":
                    await self._complete_s12(session, member.character, member.quest)
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=S12_ID,
                        objective_id=objective_id,
                        source_key=f"{objective_id}:{member.character.id}",
                        evidence={"location": VIGILIA, "shared": len(members) > 1},
                    )
                    continue
                if quest_id == P12_ID and action == "enter_berco":
                    await self._ensure_location(
                        session, member.character.id, BERCO_LOCATION_ID
                    )
                    progress = dict(member.quest.progress or {})
                    progress["entered_berco"] = True
                    member.quest.progress = progress
                    member.quest.step = next_step
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=P12_ID,
                        objective_id=objective_id,
                        source_key=f"{objective_id}:{member.character.id}",
                        evidence={"location": BERCO},
                    )
                    continue
                progress = dict(member.quest.progress or {})
                if quest_id == S11_ID and action == "fragment":
                    fragments = list(progress.get("marking_fragments", ()))
                    if len(fragments) >= 3:
                        continue
                    fragment = str(len(fragments) + 1)
                    fragments.append(fragment)
                    progress["marking_fragments"] = fragments
                    member.quest.progress = progress
                    member.quest.step = 5 if len(fragments) == 3 else 4
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=quest_id,
                        objective_id=f"s11.marking_fragment.{fragment}",
                        source_key=f"s11.marking_fragment.{fragment}:{location}",
                        evidence={"location": location, "shared": len(members) > 1},
                    )
                    continue
                if quest_id == S8_ID and action == "hardware":
                    hardware = set(progress.get("hardware_sets", ()))
                    hardware.add("a" if "a" not in hardware else "b")
                    progress["hardware_sets"] = sorted(hardware)
                    if len(hardware) >= 2:
                        member.quest.step = 5
                    member.quest.progress = progress
                    member.quest.state_version += 1
                    await record_campaign_objective_credit(
                        session,
                        character_id=member.character.id,
                        quest_id=quest_id,
                        objective_id=f"s8.hardware_set.{len(hardware)}",
                        source_key=f"s8.hardware_set.{len(hardware)}:{world.location}",
                        evidence={"location": location, "shared": len(members) > 1},
                    )
                    continue
                progress[action] = True
                member.quest.progress = progress
                member.quest.step = next_step
                member.quest.state_version += 1
                if quest_id == P10_ID and action == "sanctuary":
                    await self._ensure_unlock(session, member.character.id, SANCTUARY_UNLOCK)
                    await self._ensure_codex(
                        session, member.character.id, "codex.location.claustro_das_raizes"
                    )
                    await self._ensure_codex(
                        session, member.character.id, "codex.mystery.estruturas_interligadas"
                    )
                    await self._ensure_codex(
                        session, member.character.id, "codex.mystery.o_no_antigo"
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.location.claustro_das_raizes",
                        "codex.fragment.claustro.entry_recorded",
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.mystery.estruturas_interligadas",
                        "codex.fragment.claustro.structures_linked",
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.mystery.o_no_antigo",
                        "codex.fragment.no_antigo.network_relation",
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.mystery.o_no_antigo",
                        "codex.fragment.no_antigo.entrada_santuario_descoberta",
                    )
                if quest_id == P8_ID and action == "record":
                    await self._ensure_codex(
                        session, member.character.id, "codex.location.mata_suspensa"
                    )
                    await self._ensure_codex(
                        session, member.character.id, "codex.mystery.raizes_que_seguem_pedra"
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.location.mata_suspensa",
                        "codex.fragment.mata.entrada_registrada",
                    )
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        "codex.mystery.raizes_que_seguem_pedra",
                        "codex.fragment.mata.raizes_sob_a_pedra",
                    )
                if quest_id == P9_ID and action == "report":
                    await self._record_p9_codex(session, member.character.id)
                if quest_id == S9_ID and action == "sample":
                    progress["sample_recovered"] = True
                    member.quest.progress = progress
                if quest_id == S10_ID and action == "survivor":
                    progress["one_explorer_found_alive"] = True
                    progress["second_explorer_status"] = "missing"
                    member.quest.progress = progress
                if quest_id == S10_ID and action == "zone":
                    await self.road._bestiary(
                        session,
                        member.character.id,
                        VDE_TURF_LEECH.creature_id,
                        victory=False,
                        observation_category=VDE_TURF_LEECH.category,
                    )
                if quest_id == S12_ID and action == "read_record":
                    # Existing characters may have completed S10 before this
                    # Codex entry shipped. Reading its persisted record keeps
                    # their S12 path complete without requiring a replay.
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        S12_CODEX_ENTRY,
                        "codex.fragment.vales.nomes.registro_s10",
                    )
                if quest_id == S12_ID and action == "last_record":
                    await self._ensure_codex_fragment(
                        session,
                        member.character.id,
                        S12_CODEX_ENTRY,
                        "codex.fragment.vales.nomes.registro_final",
                    )
                await record_campaign_objective_credit(
                    session,
                    character_id=member.character.id,
                    quest_id=quest_id,
                    objective_id=objective_id,
                    source_key=f"{objective_id}:{location}",
                    evidence={"location": location, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world)

    async def return_vigilia(self, actor: int, version: int) -> VDEMissionView | None:
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P8_ID)
            if character is None or world is None or not self._valid(quest, version, step=7):
                return await self._view(session, character, quest, world)
            if world.region != REGION or world.location != VIGILIA:
                return await self._view(session, character, quest, world)
            members = await self._present(session, character.id, P8_ID, step=7, location=VIGILIA)
            for member in members:
                await self._complete_p8(session, member.character, member.quest)
            return await self._view(session, character, quest, world)

    async def choose_p9_reward(self, actor: int, version: int, choice: str):
        if choice not in P9_REWARD_CHOICES:
            return await self.resume(actor, P9_ID)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P9_ID)
            if (
                character is None
                or world is None
                or not self._valid(quest, version, step=8)
                or world.region != REGION
                or world.location != BAIXIOS
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P9_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                name, slot = P9_REWARD_CHOICES[choice]
                payload = materialize_equipment(
                    f"{P9_REWARD_SOURCE}:{character.id}:{choice}",
                    "Raro",
                    15,
                    forced_name=name,
                    forced_slot=slot,
                    bound=True,
                )
                event = RewardEvent(character_id=character.id, source_id=P9_REWARD_SOURCE)
                session.add(event)
                await session.flush()
                character.xp += 12450
                character.crowns += 330
                session.add_all(
                    (
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="xp",
                            item_id=None,
                            quantity=12450,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="crowns",
                            item_id=None,
                            quantity=330,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="equipment",
                            item_id=None,
                            quantity=1,
                            payload=payload | {"choice": choice},
                        ),
                    )
                )
                source_key = f"{P9_REWARD_SOURCE}:equipment:{choice}"
                if await self.road._inventory_slots(session, character.id) < 60:
                    from asterion.application.equipment import equipment_instance_payload

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
            await self._ensure_unlock(session, character.id, BAIXIOS_HUNT_UNLOCK)
            quest.status = "completed"
            quest.step = 8
            quest.progress = {
                **(quest.progress or {}),
                "completed": True,
                "reward_choice": choice,
            }
            quest.state_version += 1
            await consolidate_character_level(session, character)
            return await self._view(session, character, quest, world)

    async def choose_p12_reward(self, actor: int, version: int, choice: str):
        """Persist one individual, one-time Epic choice after P12 completion."""
        if choice not in P12_REWARD_CHOICES:
            return await self.resume(actor, P12_ID)
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, P12_ID)
            if character is None:
                return None
            progress = dict(quest.progress or {}) if quest is not None else {}
            if (
                quest is None
                or quest.status != "completed"
                or quest.state_version != version
                or progress.get("reward_choice")
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world)
            source_id = f"{P12_REWARD_SOURCE}:equipment"
            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == source_id,
                )
                .with_for_update()
            )
            if event is None:
                name, slot = P12_REWARD_CHOICES[choice]
                payload = materialize_equipment(
                    f"{source_id}:{character.id}:{choice}",
                    "Épico",
                    20,
                    forced_name=name,
                    forced_slot=slot,
                    bound=True,
                )
                event = RewardEvent(character_id=character.id, source_id=source_id)
                session.add(event)
                await session.flush()
                session.add(
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="equipment",
                        item_id=None,
                        quantity=1,
                        payload=payload | {"choice": choice},
                    )
                )
                source_key = f"{source_id}:{choice}"
                if await self.road._inventory_slots(session, character.id) < 60:
                    from asterion.application.equipment import equipment_instance_payload

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
            progress["reward_choice"] = choice
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def start_solo_combat(
        self, actor: int, quest_id: str, version: int
    ) -> VDEMissionView | None:
        config = MISSION_COMBAT.get(quest_id)
        if config is None:
            return await self.resume(actor, quest_id)
        step, location, level, creature = config
        async with self.sessions.begin() as session:
            character, quest, world = await self._locked_state(session, actor, quest_id)
            if character is None or world is None or not self._valid(quest, version, step=step):
                return await self._view(session, character, quest, world)
            if (
                world.region != REGION
                or world.location != location
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)
            content_id = MISSION_CONTENT_IDS[quest_id]
            if quest_id == P12_ID:
                combat = await create_campaign_boss_profile(
                    session,
                    (character,),
                    VDE_MATRIARCH,
                    20,
                    flavor=self._combat_flavor(P12_ID),
                    opening_log=self._combat_flavor(P12_ID),
                )
                combat = configure_matriarch_combat(combat, shared=False)
                activity, _, _ = await CombatRepository(session).create(
                    character, content_id, combat
                )
                await self.road._bestiary(
                    session,
                    character.id,
                    VDE_MATRIARCH.creature_id,
                    victory=False,
                    observation_category="boss",
                )
                opening_combat = combat
            else:
                activity = await materialize(
                    session,
                    character,
                    content_id,
                    creature,
                    level,
                    flavor=self._combat_flavor(quest_id),
                    opening_log=self._combat_flavor(quest_id),
                )
                opening_combat, _, _ = await current_combat(session, activity)
            if creature is not _SCRIPTED_FAUNA:
                if quest_id != P12_ID:
                    await self.road._bestiary(
                        session,
                        character.id,
                        creature.creature_id,
                        victory=False,
                        observation_category=creature.category,
                    )
            progress = dict(quest.progress or {})
            progress.update(activity_id=str(activity.id), awaiting_retry=False)
            if opening_combat is not None and opening_combat.result == "defeat":
                # Opening enemy actions are resolved during materialization. Settle
                # an immediate defeat here so a dead player is not left in an
                # active, unanswerable Campaign foreground.
                activity.status = "failed"
                character.hp = character.max_hp
                progress.update(
                    activity_id=None,
                    awaiting_retry=True,
                    opening_defeat=True,
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def propose_group_combat(self, actor: int, quest_id: str, version: int):
        initial = await self.resume(actor, quest_id)
        config = MISSION_COMBAT.get(quest_id)
        if config is None:
            return initial
        step, location, _level, creature = config
        if initial is None or initial.status != "active" or initial.step != step:
            return initial
        if self.groups is None:
            return await self.start_solo_combat(actor, quest_id, version)
        group = await self.groups.group(actor)
        if group is None or len(group.members) < 2:
            return await self.start_solo_combat(actor, quest_id, version)
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_vde",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": quest_id,
                "checkpoint": MISSION_CHECKPOINTS[quest_id],
                "title": f"{initial.title} · Encontro Roteirizado",
                "reference_character_id": str(initial.character_id),
                "location": location,
                "creature_id": creature.creature_id,
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

    async def action_combat(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None = None,
        *,
        consumable_id=None,
        target_id=None,
        effect_id=None,
    ):
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
            activity = await session.scalar(
                select(GameActivity)
                .where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id.in_(tuple(MISSION_CONTENT_IDS.values())),
                )
                .with_for_update()
            )
            if activity is None:
                return None
            quest_id = next(
                (
                    key
                    for key, content_id in MISSION_CONTENT_IDS.items()
                    if content_id == activity.content_id
                ),
                None,
            )
            if quest_id is None:
                return None
            quest = await session.scalar(
                select(Quest)
                .where(
                    Quest.character_id == character.id,
                    Quest.quest_id == quest_id,
                    Quest.status == "active",
                )
                .with_for_update()
            )
            if quest is None:
                return None
            world = await self._world(session, character.id)
            current = await self._view(session, character, quest, world)
            if activity.status != "active" or activity.state_version != version:
                return current
            updated = await apply_action(
                session,
                character,
                activity,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                category=self._creature_for_quest(quest.quest_id).category,
            )
            if updated is None or updated.version == version:
                return current
            if quest_id == P12_ID:
                await self._record_matriarch_bestiary(
                    session,
                    character.id,
                    updated,
                    victory=updated.result == "victory",
                )
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                await normalize_character_hp(session, character)
                if quest_id == P12_ID:
                    quest.step = 6
                    progress["boss_defeated"] = True
                    await self._grant_p12_nucleus(session, character)
                    from asterion.application.vde_feats import reconcile_vde_feats

                    await reconcile_vde_feats(session, character)
                else:
                    quest.step += 1
                progress.update(activity_id=None, awaiting_retry=False, combat_victory=True)
                await record_campaign_objective_credit(
                    session,
                    character_id=character.id,
                    quest_id=quest.quest_id,
                    objective_id=f"{quest.quest_id.lower()}.scripted_encounter_victory",
                    source_key=f"{quest.quest_id.lower()}.combat:{activity.id}",
                    evidence={"result": "victory", "location": world.location if world else None},
                )
                creature = self._creature_for_quest(quest.quest_id)
                if creature is not _SCRIPTED_FAUNA and quest_id != P12_ID:
                    await self.road._bestiary(
                        session,
                        character.id,
                        creature.creature_id,
                        victory=True,
                        observation_category=creature.category,
                    )
            elif updated.result == "defeat":
                activity.status = "failed"
                character.hp = character.max_hp
                progress.update(activity_id=None, awaiting_retry=True)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def campaign_action(
        self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str
    ):
        view = await self.resume_active(actor)
        if view is None or view.activity_id != activity_id:
            return None
        if view.combat is None or view.combat_actor_key is None:
            return view
        intent = campaign_action_intent(
            view.combat, view.combat_actor_key, action_index, target_code
        )
        if intent is None:
            return view
        action, target = intent
        return await self.action_combat(actor, activity_id, version, action, target_id=target)

    async def consumable_selection(self, actor: int, activity_id: UUID, version: int, **kwargs):
        current = await self.resume_active(actor)
        if current is None or current.activity_id != activity_id or current.combat is None:
            return None
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
        return derive_consumable_selection(current, **kwargs)

    async def _shared_action(
        self,
        actor,
        activity_id,
        version,
        action,
        *,
        consumable_id=None,
        target_id=None,
        effect_id=None,
    ):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _, member_seed, _ = await campaign_combat_for_activity(session, activity_id, seed.id)
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id not in MISSION_TITLES:
                return None
            mission_creature = self._creature_for_quest(locked.encounter.quest_id)
            character = locked.characters.get(seed.id)
            member = next(
                (row for row in locked.members if row.game_activity_id == activity_id), None
            )
            activity = locked.activities.get(activity_id)
            if character is None or member is None or activity is None:
                return None
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
                    return await self._view_for_character_activity(session, character, activity_id)
            updated = resolve_campaign_action(
                locked,
                activity_id=activity_id,
                version=version,
                action=action,
                consumable_id=consumable_id,
                target_id=target_id,
                effect_id=effect_id,
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(mission_creature.category, 0),
            )
            if updated.version == version:
                return await self._view_for_character_activity(session, character, activity_id)
            if locked.encounter.quest_id == P12_ID:
                for participant in locked.characters.values():
                    await self._record_matriarch_bestiary(
                        session,
                        participant.id,
                        updated,
                        victory=updated.result == "victory",
                    )
            if stack is not None:
                stack.quantity -= 1
            roster_by_id = {row.character_id: row for row in locked.members}
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == locked.encounter.quest_id,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            for character_id, participant in locked.characters.items():
                roster_row = roster_by_id[character_id]
                participant_quest = quests.get(character_id)
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    if locked.encounter.quest_id == P12_ID:
                        await self._grant_p12_nucleus(session, participant)
                        from asterion.application.vde_feats import reconcile_vde_feats

                        await reconcile_vde_feats(session, participant)
                    elif mission_creature is not _SCRIPTED_FAUNA:
                        await self.road._bestiary(
                            session,
                            participant.id,
                            mission_creature.creature_id,
                            victory=True,
                            observation_category=mission_creature.category,
                        )
                    if roster_row.role == "eligible" and participant_quest is not None:
                        participant_quest.step = (
                            6 if locked.encounter.quest_id == P12_ID
                            else participant_quest.step + 1
                        )
                        participant_quest.state_version += 1
                        participant_quest.progress = {
                            **(participant_quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": False,
                            "combat_victory": True,
                            "boss_defeated": (
                                True
                                if locked.encounter.quest_id == P12_ID
                                else (participant_quest.progress or {}).get("boss_defeated")
                            ),
                        }
                        await record_campaign_objective_credit(
                            session,
                            character_id=character_id,
                            quest_id=participant_quest.quest_id,
                            objective_id=f"{participant_quest.quest_id.lower()}.scripted_encounter_victory",
                            source_key=f"{participant_quest.quest_id.lower()}.combat:{locked.encounter.id}",
                            evidence={"result": "victory", "shared": True},
                        )
                elif updated.result == "defeat":
                    participant.hp = participant.max_hp
                    if roster_row.role == "eligible" and participant_quest is not None:
                        participant_quest.state_version += 1
                        participant_quest.progress = {
                            **(participant_quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": True,
                        }
            if updated.result:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view_for_character_activity(session, character, activity_id)

    async def _combat_eligibility(self, session, character, payload) -> ActivityEligibility:
        quest_id = payload.get("quest_id")
        combat_config = MISSION_COMBAT.get(quest_id)
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == quest_id)
        )
        world = await self._world(session, character.id)
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id, GameActivity.status == "active"
            )
        )
        quest_step = combat_config[0] if combat_config is not None else -1
        same_location = bool(
            world
            and world.region == REGION
            and world.location == payload.get("location")
            and combat_config is not None
            and world.location == combat_config[1]
        )
        if active is not None or not same_location:
            role = "ineligible"
        elif quest is not None and quest.status == "active" and quest.step == quest_step:
            role = "eligible"
        elif quest is None or quest.status == "completed" or (quest and quest.step > quest_step):
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
            "active_activity": str(active.id) if active else None,
            "combat_configuration_version": character.combat_configuration_version,
        }
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ActivityEligibility(role, fingerprint, snapshot)

    async def _create_group_combat(self, session, proposal, characters) -> str:
        quest_id = proposal.context_payload.get("quest_id")
        combat_config = MISSION_COMBAT.get(quest_id)
        if combat_config is None:
            raise GroupError("invalid_activity")
        _step, location, level, creature = combat_config
        content_id = MISSION_CONTENT_IDS[quest_id]
        checkpoint = MISSION_CHECKPOINTS[quest_id]
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        by_character = {row.character_id: row for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        party = []
        roster = []
        for index, character in enumerate(characters, start=1):
            participant = by_character.get(character.id)
            if participant is None or participant.eligibility not in {"eligible", "helper"}:
                raise GroupError("eligibility_changed")
            equipment = await load_equipment_configuration(session, character)
            arts = await load_active_art_configuration(session, character)
            reconcile_character_hp(character, equipment)
            actor_key = campaign_actor_key(index, len(characters))
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
        if quest_id == P12_ID:
            combat = await create_campaign_boss_profile(
                session,
                characters,
                VDE_MATRIARCH,
                20,
                flavor=self._combat_flavor(P12_ID),
                opening_log=self._combat_flavor(P12_ID),
            )
            combat = configure_matriarch_combat(combat, shared=True)
        else:
            combat = create_creature_party_combat(
                uuid4(),
                lead.name,
                lead.character_class,
                lead.race,
                lead.hp,
                (CreatureCombatantSpec(creature, level, "enemy"),),
                player_level=lead.level,
                equipment_configuration=party[0].equipment_configuration,
                ruleset_version=RULESET,
                flavor=self._combat_flavor(quest_id),
                opening_log=self._combat_flavor(quest_id),
                active_art_ids=party[0].active_art_ids,
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
            ruleset_version=RULESET,
            checkpoint=checkpoint,
            campaign_boss=quest_id == P12_ID,
        )
        if creature is not _SCRIPTED_FAUNA and quest_id != P12_ID:
            for member in roster:
                await self.road._bestiary(
                    session,
                    member.character.id,
                    creature.creature_id,
                    victory=False,
                    observation_category=creature.category,
                )
        elif quest_id == P12_ID:
            for member in roster:
                await self.road._bestiary(
                    session,
                    member.character.id,
                    VDE_MATRIARCH.creature_id,
                    victory=False,
                    observation_category="boss",
                )
        for member in roster:
            if member.role == "eligible":
                quest = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == member.character.id, Quest.quest_id == quest_id)
                    .with_for_update()
                )
                shared_member = await session.scalar(
                    select(CampaignSharedEncounterMember).where(
                        CampaignSharedEncounterMember.shared_encounter_id == encounter.id,
                        CampaignSharedEncounterMember.character_id == member.character.id,
                    )
                )
                if quest is not None and shared_member is not None:
                    quest.progress = {
                        **(quest.progress or {}),
                        "activity_id": str(shared_member.game_activity_id),
                        "awaiting_retry": False,
                    }
                    quest.state_version += 1
        return str(encounter.id)

    async def _complete_s7(self, session, character, quest):
        await self._reward(session, character, quest, S7_REWARD_SOURCE, 3840, 140, ())
        await self._ensure_codex(session, character.id, "codex.route.rotas_dos_vales")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.route.rotas_dos_vales",
            "codex.fragment.vales.routes.s7_marker_shift",
        )
        quest.status = "completed"
        quest.step = 5
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_p8(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 1),
            ("material.vde.erva_de_turfa", 2),
            ("material.vde.resina_enredada", 1),
        )
        await self._reward(session, character, quest, P8_REWARD_SOURCE, 10500, 300, materials)
        for unlock_id in (MATA_HUNT_UNLOCK, MATA_EXPLORE_UNLOCK):
            await self._ensure_unlock(session, character.id, unlock_id)
        quest.status = "completed"
        quest.step = 7
        quest.progress = {**(quest.progress or {}), "completed": True, "returned_vigilia": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_s8(self, session, character, quest):
        materials = (
            ("material.vde.erva_de_turfa", 1),
            ("material.vde.resina_enredada", 1),
        )
        await self._reward(session, character, quest, S8_REWARD_SOURCE, 8015, 230, materials)
        await self._ensure_codex(session, character.id, "codex.location.mata_suspensa")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.location.mata_suspensa",
            "codex.fragment.mata.rotas_adaptadas",
        )
        await self._ensure_codex(session, character.id, "codex.route.rotas_dos_vales")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.route.rotas_dos_vales",
            "codex.fragment.vales.routes.s8_alternate_passage",
        )
        quest.status = "completed"
        quest.step = 7
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_s9(self, session, character, quest):
        materials = (("material.vde.couro_musgoso", 2),)
        await self._reward(session, character, quest, S9_REWARD_SOURCE, 4980, 170, materials)
        await self._ensure_codex(session, character.id, "codex.mystery.raizes_que_seguem_pedra")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.mystery.raizes_que_seguem_pedra",
            "codex.fragment.mata.casca_camadas_externas",
        )
        quest.status = "completed"
        quest.step = 6
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_p10(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 2),
            ("material.vde.resina_enredada", 2),
        )
        await self._reward(session, character, quest, P10_REWARD_SOURCE, 14600, 450, materials)
        await self._ensure_unlock(session, character.id, SANCTUARY_UNLOCK)
        await self._ensure_unlock(session, character.id, CLAUSTRO_HUNT_UNLOCK)
        quest.status = "completed"
        quest.step = 8
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)
        from asterion.application.vde_feats import reconcile_vde_feats

        await reconcile_vde_feats(session, character)

    async def _complete_s10(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 2),
            ("material.vde.couro_musgoso", 1),
            ("material.vde.resina_enredada", 1),
        )
        await self._reward(session, character, quest, S10_REWARD_SOURCE, 10220, 270, materials)
        await self._ensure_codex_fragment(
            session,
            character.id,
            S12_CODEX_ENTRY,
            "codex.fragment.vales.nomes.registro_s10",
        )
        quest.status = "completed"
        quest.step = 8
        quest.progress = {
            **(quest.progress or {}),
            "completed": True,
            "one_explorer_returned_alive": True,
            "second_explorer_status": "missing",
        }
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_s11(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 1),
            ("material.vde.erva_de_turfa", 1),
            ("material.vde.resina_enredada", 2),
        )
        await self._reward(session, character, quest, S11_REWARD_SOURCE, 10990, 280, materials)
        await self._ensure_codex(session, character.id, "codex.mystery.rotinas_que_permanecem")
        await self._ensure_codex_fragment(
            session,
            character.id,
            "codex.mystery.rotinas_que_permanecem",
            "codex.fragment.vigia.rotinas_que_permanecem",
        )
        quest.status = "completed"
        quest.step = 5
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)

    async def _complete_s12(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 2),
            ("material.vde.couro_musgoso", 2),
            ("material.vde.erva_de_turfa", 2),
            ("material.vde.resina_enredada", 2),
        )
        await self._reward(session, character, quest, S12_REWARD_SOURCE, 18100, 500, materials)
        await self._ensure_codex_fragment(
            session,
            character.id,
            S12_CODEX_ENTRY,
            "codex.fragment.vales.nomes.registro_vigilia",
        )
        quest.status = "completed"
        quest.step = 12
        quest.progress = {**(quest.progress or {}), "completed": True, "names_recorded": True}
        quest.state_version += 1
        await consolidate_character_level(session, character)
        from asterion.application.vde_feats import reconcile_vde_feats

        await reconcile_vde_feats(session, character)

    async def _complete_p11(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 3),
            ("material.vde.resina_enredada", 1),
        )
        await self._reward(session, character, quest, P11_REWARD_SOURCE, 16900, 490, materials)
        quest.status = "completed"
        quest.step = 7
        quest.progress = {
            **(quest.progress or {}),
            "berco_access_open": True,
            "completed": True,
        }
        quest.state_version += 1
        await consolidate_character_level(session, character)
        await self._ensure_p12_started(session, character)

    async def _record_p11_codex(self, session, character_id):
        for entry_id, fragment_id in (
            (
                "codex.location.berco_da_matriarca",
                "codex.fragment.berco.access_opened",
            ),
            (
                "codex.mystery.a_rede_sob_os_vales",
                "codex.fragment.vales.network_and_matriarch",
            ),
        ):
            await self._ensure_codex_fragment(session, character_id, entry_id, fragment_id)

    async def _complete_p12(self, session, character, quest):
        materials = (
            ("material.vde.ferro_enredado", 4),
            ("material.vde.resina_enredada", 4),
        )
        await self._reward(
            session, character, quest, P12_REWARD_SOURCE, 32580, 800, materials
        )
        for entry_id, fragment_id in (
            (
                "codex.location.berco_da_matriarca",
                "codex.fragment.berco.matriarca_antiga_viva",
            ),
            (
                "codex.mystery.a_rede_sob_os_vales",
                "codex.fragment.vales.matriarca_nao_origem",
            ),
            (
                "codex.mystery.a_rede_sob_os_vales",
                "codex.fragment.vales.pos_vitoria",
            ),
            (
                "codex.mystery.pulsacao_sob_a_pedra",
                "codex.fragment.vales.pulsacao_estrutura_ativa",
            ),
            (
                "codex.mystery.estruturas_interligadas",
                "codex.fragment.vales.continuidade_nareth",
            ),
        ):
            await self._ensure_codex_fragment(
                session, character.id, entry_id, fragment_id
            )
        await self._ensure_unlock(session, character.id, P12_RECIPE_UNLOCK)
        await self._ensure_unlock(session, character.id, VDE_CAMPAIGN_UNLOCK)
        quest.status = "completed"
        quest.step = 7
        quest.progress = {
            **(quest.progress or {}),
            "completed": True,
            "regional_campaign_completed": True,
        }
        quest.state_version += 1
        await consolidate_character_level(session, character)
        await self._ensure_nareth_gate(session, character, quest)
        await self._record_matriarch_completion_evidence(session, character.id)
        from asterion.application.vde_feats import reconcile_vde_feats

        await reconcile_vde_feats(session, character)

    async def _record_matriarch_completion_evidence(self, session, character_id):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VDE_MATRIARCH.creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            await self.road._bestiary(
                session,
                character_id,
                VDE_MATRIARCH.creature_id,
                observation_category="boss",
            )
            entry = await session.scalar(
                select(BestiaryEntry)
                .where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == VDE_MATRIARCH.creature_id,
                )
                .with_for_update()
            )
        if entry is None:
            return
        await self.road.bestiary.add_evidence(
            session,
            entry,
            character_id,
            VDE_MATRIARCH.creature_id,
            "p12_completed",
            "campaign",
            5,
        )
        await self.road.bestiary.refresh_boss_mastery(
            session, character_id, VDE_MATRIARCH.creature_id
        )

    async def _record_matriarch_bestiary(
        self, session, character_id, combat, *, victory
    ):
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VDE_MATRIARCH.creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            await self.road._bestiary(
                session,
                character_id,
                VDE_MATRIARCH.creature_id,
                observation_category="boss",
            )
            entry = await session.scalar(
                select(BestiaryEntry)
                .where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == VDE_MATRIARCH.creature_id,
                )
                .with_for_update()
            )
        if entry is None:
            return
        await self.road.bestiary.record_combat_events(
            session, character_id, VDE_MATRIARCH.creature_id, None, combat
        )
        evidence_categories = {
            "phase": "phase",
            "mechanic": "mechanic",
            "action": "behavior",
        }
        for evidence_id in matriarch_phase_evidence(combat):
            prefix = evidence_id.split(":", 1)[0]
            await self.road.bestiary.add_evidence(
                session,
                entry,
                character_id,
                VDE_MATRIARCH.creature_id,
                evidence_id,
                evidence_categories[prefix],
                5 if prefix == "mechanic" else 4,
            )
        await self.road.bestiary.record(
            session,
            character_id,
            VDE_MATRIARCH.creature_id,
            victory=victory,
            observation_category="boss",
        )
        from asterion.application.vde_feats import reconcile_vde_feats

        character = await session.scalar(
            select(Character).where(Character.id == character_id)
        )
        if character is not None:
            await reconcile_vde_feats(session, character)

    async def _grant_p12_nucleus(self, session, character):
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P12_NUCLEUS_SOURCE,
            )
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(
            character_id=character.id,
            source_id=P12_NUCLEUS_SOURCE,
        )
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="material",
                item_id=P12_NUCLEUS,
                quantity=1,
                payload={"material_id": P12_NUCLEUS, "bound": True, "first_victory": True},
            )
        )
        await self.road.deliver_material(
            session,
            character,
            P12_NUCLEUS,
            1,
            f"{P12_NUCLEUS_SOURCE}:material",
            bound=True,
        )

    async def _record_p9_codex(self, session, character_id):
        entries = (
            (
                "codex.location.baixios_enredados",
                "codex.fragment.baixios.entry_recorded",
            ),
            ("codex.figure.iven_raal", "codex.fragment.iven.regional_register"),
            (
                "codex.mystery.o_no_antigo",
                "codex.fragment.no_antigo.translation_hypothesis",
            ),
        )
        for entry_id, fragment_id in entries:
            await self._ensure_codex_fragment(session, character_id, entry_id, fragment_id)

    @staticmethod
    def _creature_for_quest(quest_id):
        config = MISSION_COMBAT.get(quest_id)
        return config[3] if config is not None else _SCRIPTED_FAUNA

    @staticmethod
    def _combat_flavor(quest_id):
        return {
            S7_ID: "Uma criatura ocupa a marcação de rota; a espécie não é identificada.",
            P8_ID: (
                "Criaturas ocupam o ponto investigado entre as raízes; "
                "a missão não identifica uma espécie."
            ),
            S8_ID: "Um Cervo do Nó bloqueia a passagem de suprimentos.",
            P9_ID: "Uma Casca Errante guarda as estruturas parcialmente soterradas.",
            S9_ID: "Uma Casca Errante foi localizada nos Baixios.",
            P10_ID: "Um Vigia Enraizado guarda a estrutura no Claustro.",
            S10_ID: (
                "Um encontro roteirizado ocorre na região inundada; "
                "a espécie não é identificada."
            ),
            S12_ID: (
                "Um Peregrino Enredado Nv.20 bloqueia a passagem junto a uma marca antiga."
            ),
        }.get(quest_id, "Um encontro roteirizado bloqueia o caminho.")

    async def _reward(self, session, character, quest, source_id, xp, crowns, materials):
        event = await session.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == character.id, RewardEvent.source_id == source_id)
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all(
            [
                RewardComponent(reward_event_id=event.id, kind="xp", item_id=None, quantity=xp),
                RewardComponent(
                    reward_event_id=event.id, kind="crowns", item_id=None, quantity=crowns
                ),
            ]
        )
        for material_id, quantity in materials:
            session.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind="material",
                    item_id=material_id,
                    quantity=quantity,
                    payload={"material_id": material_id, "bound": True},
                )
            )
            await self.road.deliver_material(
                session,
                character,
                material_id,
                quantity,
                f"{source_id}:material:{material_id}",
                bound=True,
            )

    async def _present(self, session, character_id, quest_id, *, step, location):
        return await present_campaign_members(
            session,
            character_ids=await campaign_roster_ids(session, character_id),
            quest_id=quest_id,
            content_version=self._content_version(quest_id),
            step=step,
            region=REGION,
            location=location,
        )

    async def _view(self, session, character, quest, world, *, requested_quest_id=None):
        progress = dict(quest.progress or {}) if quest else {}
        quest_id = quest.quest_id if quest else (requested_quest_id or S7_ID)
        title = MISSION_TITLES.get(quest_id, S7_TITLE)
        activity = combat = encounter = record = None
        actor_key = None
        group_size = 1
        try:
            activity_id = UUID(progress["activity_id"]) if progress.get("activity_id") else None
        except (TypeError, ValueError):
            activity_id = None
        if activity_id is not None and character is not None:
            shared, shared_member, shared_combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is not None:
                activity = await session.get(GameActivity, activity_id)
                encounter = shared
                combat = shared_combat if shared.status == "active" else None
                actor_key = shared_member.actor_key if shared_member else None
                group_size = shared.roster_size
            else:
                content_id = MISSION_CONTENT_IDS.get(quest_id)
                activity = await session.scalar(
                    select(GameActivity).where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == content_id,
                    )
                )
                if activity is not None:
                    row = (
                        await session.execute(
                            select(Encounter, CombatRecord)
                            .join(CombatRecord)
                            .where(Encounter.game_activity_id == activity.id)
                        )
                    ).one_or_none()
                    if row:
                        encounter, record = row
                        if activity.status == "active":
                            combat = decode(
                                record.snapshot,
                                record.id,
                                activity.ruleset_version,
                                activity.state_version,
                            )
        available = False
        if quest is None:
            available = await self._can_start(session, character, world, quest_id)
            kind = "offer" if available else "unavailable"
        elif combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = (
                "choice"
                if quest_id == P12_ID and not progress.get("reward_choice")
                else "completed"
            )
        else:
            kind = {
                S7_ID: {
                    1: "markers",
                    2: "retry" if progress.get("awaiting_retry") else "combat_start",
                    3: "rope",
                    4: "report",
                },
                P8_ID: {
                    1: "enter_mata",
                    2: "roots",
                    3: "retry" if progress.get("awaiting_retry") else "combat_start",
                    4: "compare",
                    5: "masonry",
                    6: "record",
                    7: "return_vigilia",
                },
                S8_ID: {
                    1: "passage",
                    2: "structures",
                    3: "retry" if progress.get("awaiting_retry") else "combat_start",
                    4: "hardware",
                    5: "alternate_route",
                    6: "report",
                },
                P9_ID: {
                    1: "follow",
                    2: "enter_baixios",
                    3: "structures",
                    4: "retry" if progress.get("awaiting_retry") else "combat_start",
                    5: "inscription",
                    6: "fragment",
                    7: "report",
                    8: "choice",
                },
                S9_ID: {
                    1: "locate",
                    2: "retry" if progress.get("awaiting_retry") else "combat_start",
                    3: "fragments",
                    4: "sample",
                    5: "report",
                },
                P10_ID: {
                    1: "follow",
                    2: "open_claustro",
                    3: "inscriptions",
                    4: "retry" if progress.get("awaiting_retry") else "combat_start",
                    5: "structure",
                    6: "sanctuary",
                    7: "report",
                },
                S10_ID: {
                    1: "markers",
                    2: "zone",
                    3: "bag",
                    4: "tracks",
                    5: "retry" if progress.get("awaiting_retry") else "combat_start",
                    6: "survivor",
                    7: "return_vigilia",
                },
                S11_ID: {
                    1: "patrols",
                    2: "retry" if progress.get("awaiting_retry") else "combat_start",
                    3: "return_place",
                    4: "fragments",
                    5: "report",
                },
                P11_ID: {
                    1: "pressure_points",
                    2: "clear_roots",
                    3: "retry" if progress.get("awaiting_retry") else "combat_start",
                    4: "chamber",
                    5: "traces",
                    6: "convergence",
                    7: "open_berco",
                },
                P12_ID: {
                    1: "enter_berco",
                    2: "advance_network",
                    3: "connections",
                    4: "central_chamber",
                    5: "retry" if progress.get("awaiting_retry") else "combat_start",
                    6: "examine_center",
                    7: "register",
                },
            S12_ID: {
                1: "read_record",
                2: "visit_garganta",
                3: "find_mark",
                4: "visit_mata",
                5: "recover_object",
                6: "visit_baixios",
                7: "retry" if progress.get("awaiting_retry") else "combat_start",
                8: "examine_site",
                9: "visit_claustro",
                10: "last_record",
                11: "report_iven",
                12: "register_names",
            },
            }.get(quest_id, {}).get(quest.step, "unavailable")
        options = quantities = ()
        budget = 0
        if (
            activity is not None
            and activity.status == "active"
            and combat is not None
            and character is not None
        ):
            options, quantities, budget = await consumable_state(
                session,
                character,
                combat,
                self._creature_for_quest(quest_id).category,
                actor_key=actor_key,
            )
        if quest_id == P12_ID and combat is not None and actor_key is None:
            actor_key = "player"
        return VDEMissionView(
            character_id=character.id if character else UUID(int=0),
            quest_id=quest_id,
            title=title,
            kind=kind,
            status=quest.status if quest else None,
            step=quest.step if quest else None,
            state_version=quest.state_version if quest else 0,
            progress=progress,
            location=world.location if world else "",
            level=character.level if character else 0,
            available=(quest.status == "active" if quest is not None else available),
            combat=combat,
            activity_id=activity.id if activity else None,
            encounter_id=encounter.id if encounter else None,
            combat_id=record.id if record else None,
            combat_actor_key=actor_key,
            group_size=group_size,
            consumable_options=options,
            consumable_quantities=quantities,
            consumable_budget_limit=budget,
        )

    async def _view_for_character_activity(self, session, character, activity_id):
        shared, member, combat = await campaign_combat_for_activity(
            session, activity_id, character.id
        )
        activity = await session.get(GameActivity, activity_id)
        if shared is None or member is None or activity is None:
            return None
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == shared.quest_id,
            )
        )
        world = await self._world(session, character.id)
        if quest is None:
            title = MISSION_TITLES.get(shared.quest_id, S7_TITLE)
            base = VDEMissionView(
                character_id=character.id,
                quest_id=shared.quest_id,
                title=title,
                kind="combat",
                status="helper",
                step=None,
                state_version=0,
                progress={"helper": True, "result": shared.status},
                location=world.location if world else "",
                level=character.level,
                available=False,
            )
        else:
            base = await self._view(session, character, quest, world)
        consumables = ((), (), 0)
        if shared.status == "active" and combat is not None:
            consumables = await consumable_state(
                session,
                character,
                combat,
                self._creature_for_quest(shared.quest_id).category,
                actor_key=member.actor_key,
            )
        if shared.status != "active":
            if quest is not None and member.role == "eligible":
                # Eligible participants now see their own next mission objective.
                # Helpers without quest credit receive a result-only view below.
                return replace(
                    base,
                    activity_id=None,
                    encounter_id=shared.id,
                    combat=None,
                    group_size=shared.roster_size,
                )
            return replace(
                base,
                kind="combat_result",
                progress={"helper": True, "result": shared.status},
                activity_id=None,
                encounter_id=shared.id,
                combat=None,
                combat_actor_key=member.actor_key,
                group_size=shared.roster_size,
            )
        return replace(
            base,
            kind="combat",
            combat=combat,
            activity_id=activity.id,
            encounter_id=shared.id,
            combat_id=None,
            combat_actor_key=member.actor_key,
            group_size=shared.roster_size,
            consumable_options=consumables[0],
            consumable_quantities=consumables[1],
            consumable_budget_limit=consumables[2],
        )

    async def _locked_state(self, session, actor, quest_id):
        character = await session.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if character is None:
            return None, None, None
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == quest_id)
            .with_for_update()
        )
        if quest_id == P12_ID and quest is None:
            quest = await self._ensure_p12_started(session, character)
        elif quest_id == P12_ID and quest is not None and quest.status == "completed":
            await self._ensure_nareth_gate(session, character, quest)
        world = await self._world(session, character.id)
        return character, quest, world

    async def _ensure_p12_started(self, session, character):
        """Lazily materialize the automatic P12 quest at its individual gate."""
        quest = await session.scalar(
            select(Quest)
            .where(Quest.character_id == character.id, Quest.quest_id == P12_ID)
            .with_for_update()
        )
        if quest is not None or character.level < 20:
            return quest
        p11 = await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id == P11_ID,
                Quest.status == "completed",
            )
        )
        if p11 is None:
            return None
        quest = Quest(
            character_id=character.id,
            quest_id=P12_ID,
            title=P12_TITLE,
            status="active",
            step=1,
            content_version=CONTENT_VERSION_CLIMAX,
            state_version=0,
            progress={"external_connections": [], "reward_choice": None},
        )
        session.add(quest)
        await session.flush()
        await record_campaign_objective_credit(
            session,
            character_id=character.id,
            quest_id=P12_ID,
            objective_id="p12.started_automatically",
            source_key=f"p12:auto:{character.id}",
            evidence={"level": character.level, "p11_completed": True},
        )
        return quest

    async def _ensure_nareth_gate(self, session, character, quest):
        if quest.status != "completed":
            return
        await self._ensure_unlock(session, character.id, VDE_CAMPAIGN_UNLOCK)
        if character.level >= 21:
            await self._ensure_unlock(session, character.id, NARETH_UNLOCK)

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.server_id
            )
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id, GameActivity.status == "active"
            )
        )

    async def _active_quest_for_character(self, session, character_id):
        return await session.scalar(
            select(Quest)
            .where(
                Quest.character_id == character_id,
                Quest.quest_id.in_(tuple(MISSION_TITLES)),
                Quest.status == "active",
            )
            .with_for_update()
        )

    @staticmethod
    def _valid(quest, version, *, step):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == VDEMissionService._content_version(quest.quest_id)
            and quest.state_version == version
            and quest.step == step
        )

    @staticmethod
    def _content_version(quest_id):
        return MISSION_VERSIONS.get(quest_id, CONTENT_VERSION_MID)

    async def _can_start(self, session, character, world, quest_id):
        if character is None or world is None or quest_id not in MISSION_TITLES:
            return False
        required_level, required_location = {
            S7_ID: (12, GARGANTA),
            P8_ID: (13, VIGILIA),
            S8_ID: (14, MATA),
            P9_ID: (15, MATA),
            S9_ID: (15, BAIXIOS),
            P10_ID: (17, BAIXIOS),
            S10_ID: (17, BAIXIOS),
            S11_ID: (18, CLAUSTRO),
            P11_ID: (19, CLAUSTRO),
            P12_ID: (20, BERCO),
            S12_ID: (20, CLAUSTRO),
        }[quest_id]
        prerequisite_id = {
            S7_ID: P7_ID,
            P8_ID: P7_ID,
            S8_ID: P8_ID,
            P9_ID: P8_ID,
            S9_ID: P9_ID,
            P10_ID: P9_ID,
            S10_ID: P10_ID,
            P11_ID: P10_ID,
            S11_ID: P10_ID,
            P12_ID: P11_ID,
            S12_ID: P11_ID,
        }[quest_id]
        status_filter = ("completed",)
        if quest_id in {S9_ID, S10_ID}:
            status_filter = ("active", "completed")
        if quest_id == S12_ID:
            s10_completed = await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == S10_ID,
                    Quest.status == "completed",
                )
            )
            if s10_completed is None:
                return False
        if quest_id == S11_ID:
            prerequisite = await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character.id,
                    LocationDiscovery.location_id == CLAUSTRO_LOCATION_ID,
                )
            )
        else:
            prerequisite = await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == prerequisite_id,
                    Quest.status.in_(status_filter),
                )
            )
        return bool(
            prerequisite is not None
            and character.level >= required_level
            and world.region == REGION
            and world.location == required_location
            and await self._foreground(session, character.id) is None
        )

    async def _ensure_location(self, session, character_id, location_id):
        if (
            await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == location_id,
                )
            )
            is None
        ):
            session.add(LocationDiscovery(character_id=character_id, location_id=location_id))

    async def _ensure_unlock(self, session, character_id, unlock_id):
        if (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id, Unlock.unlock_id == unlock_id
                )
            )
            is None
        ):
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))

    async def _ensure_codex(self, session, character_id, entry_id):
        if (
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character_id, CodexEntry.entry_id == entry_id
                )
            )
            is None
        ):
            session.add(CodexEntry(character_id=character_id, entry_id=entry_id))

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        if (
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == fragment_id,
                )
            )
            is None
        ):
            await self._ensure_codex(session, character_id, entry_id)
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
            )
