"""Persistent Nareth campaign quests, objectives, and shared encounters."""

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
    create_campaign_boss_profile,
    create_campaign_encounter,
    lock_campaign_encounter,
    resolve_campaign_action,
    settle_campaign_encounter,
)
from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    lock_campaign_roster,
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
from asterion.domain.nareth_bosses import configure_nareth_campaign_boss, nareth_boss_phase_evidence
from asterion.domain.road import (
    NARETH_ARCONTE_INVERTIDO,
    NARETH_CHANNEL_SCARAB,
    NARETH_CUSTODIO_SEM_NORTE,
    NARETH_INVERTED_CUSTODIAN,
    NARETH_INVERTED_HUSK,
    NARETH_MERIDIAN_WATCHER,
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    materialize_equipment,
)
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    Brazier,
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

REGION = "Planícies de Nareth"
P13_ID = "P13"
S13_ID = "S13"
P14_ID = "P14"
S14_ID = "S14"
P15_ID = "P15"
S15_ID = "S15"
P16_ID = "P16"
S16_ID = "S16"
S17_ID = "S17"
P17_ID = "P17"
P18_ID = "P18"
S18_ID = "S18"
CONTENT_VERSION = "nareth-1.0.0"
CONTENT_VERSION_MID = "nareth-1.0.1"
P13_TITLE = "Linhas no Horizonte"
S13_TITLE = "Pedras que Apontam"
P14_TITLE = "O Canal sem Norte"
S14_TITLE = "O Peso da Distância"
P15_TITLE = "A Distância Errada"
S15_TITLE = "Sob o Mesmo Céu"
P16_TITLE = "O Eixo sob a Terra"
S16_TITLE = "Cartografia do Erro"
S17_TITLE = "O Prumo Afundado"
P17_TITLE = "Medir o que Permanece"
P18_TITLE = "O Arconte Invertido"
S18_TITLE = "Os Caminhos que Não Coincidem"
P13_REWARD_SOURCE = "p13.linhas_no_horizonte"
S13_REWARD_SOURCE = "s13.pedras_que_apontam"
P14_REWARD_SOURCE = "p14.o_canal_sem_norte"
S14_REWARD_SOURCE = "s14.peso_da_distancia"
P15_REWARD_SOURCE = "p15.a_distancia_errada"
S15_REWARD_SOURCE = "s15.sob_o_mesmo_ceu"
P16_REWARD_SOURCE = "p16.o_eixo_sob_a_terra"
S16_REWARD_SOURCE = "s16.cartografia_do_erro"
S17_REWARD_SOURCE = "s17.o_prumo_afundado"
P17_REWARD_SOURCE = "p17.medir_o_que_permanece"
P18_REWARD_SOURCE = "p18.o_arconte_invertido"
S18_REWARD_SOURCE = "s18.os_caminhos_que_nao_coincidem"
CAMPINAS = "Campinas do Meridiano"
POSTO = "Posto de Nareth"
CANAIS = "Canais Secos"
CAMPOS = "Campos Invertidos"
OBSERVATORIO = "Observatório do Eixo"
CAMARA = "Câmara do Arconte"
CAMPINAS_LOCATION_ID = "nareth.location.campinas_do_meridiano"
POSTO_LOCATION_ID = "nareth.location.posto_de_nareth"
CANAIS_LOCATION_ID = "nareth.location.canais_secos"
CAMPOS_LOCATION_ID = "nareth.location.campos_invertidos"
OBSERVATORIO_LOCATION_ID = "nareth.location.observatorio_do_eixo"
CAMARA_LOCATION_ID = "nareth.location.camara_do_arconte"
REGION_UNLOCK = "region.nareth.available"
EXPLORE_UNLOCK = "explore.nareth.campinas_do_meridiano"
HUNT_UNLOCK = "hunt.manual.nareth.campinas_do_meridiano"
CAMPINAS_POSTO_ROUTE = "route.nareth.campinas_posto"
POSTO_CANAIS_ROUTE = "route.nareth.posto_canais"
CANAIS_CAMPOS_ROUTE = "route.nareth.canais_campos"
CAMPOS_OBSERVATORIO_ROUTE = "route.nareth.campos_observatorio"
HORIZON_BRAZIER = "nareth.brazier.horizonte"
POSTO_BRAZIER = "nareth.brazier.posto"
ROTAS_CODEX = "codex.route.rotas_de_nareth"
CODEX_INITIAL_FRAGMENT = "codex.fragment.nareth.p13.routes_initial"
CODEX_S13_FRAGMENT = "codex.fragment.nareth.s13.references"
P14_CODEX = "codex.history.rede_de_medicao"
S16_CODEX = "codex.history.cartografia_do_erro"
S17_CODEX = "codex.history.protocolos_de_referencia"
P17_CODEX = "codex.history.custodia_das_ancoras"
P18_CODEX = "codex.history.estabilidade_do_veu"
S18_CODEX = "codex.route.os_caminhos_que_nao_coincidem"
CHAMBER_UNLOCK = "region.nareth.camara_arconte.available"
CHAMBER_ROUTE_UNLOCK = "route.nareth.observatorio_camara"
CRIMSON_UNLOCK = "region.varzeas_carmesins.available"
MISSION_TITLES = {
    P13_ID: P13_TITLE, S13_ID: S13_TITLE, P14_ID: P14_TITLE, S14_ID: S14_TITLE,
    P15_ID: P15_TITLE, S15_ID: S15_TITLE, P16_ID: P16_TITLE, S16_ID: S16_TITLE,
    S17_ID: S17_TITLE, P17_ID: P17_TITLE, P18_ID: P18_TITLE, S18_ID: S18_TITLE,
}
MISSION_CHECKPOINTS = {
    P14_ID: "nareth.p14.canal_sem_norte", S14_ID: "nareth.s14.peso_da_distancia",
    P15_ID: "nareth.p15.distancia_errada", S15_ID: "nareth.s15.sob_o_mesmo_ceu",
    P16_ID: "nareth.p16.eixo_sob_a_terra", S16_ID: "nareth.s16.cartografia_do_erro",
    S17_ID: "nareth.s17.o_prumo_afundado", P17_ID: "nareth.p17.medir_o_que_permanece",
    P18_ID: "nareth.p18.arconte_invertido", S18_ID: "nareth.s18.caminhos_nao_coincidem",
}
MISSION_CONTENT_IDS = {
    P14_ID: "nareth_p14_escaravelho_canal", P15_ID: "nareth_p15_casco_invertido",
    P16_ID: "nareth_p16_vigia_meridiano",
    P17_ID: "nareth_p17_custodio_invertido", P18_ID: "nareth_p18_arconte_invertido",
    S18_ID: "nareth_s18_custodio_sem_norte",
}
MISSION_COMBAT = {
    P14_ID: (5, CANAIS, 23, NARETH_CHANNEL_SCARAB),
    P15_ID: (6, CAMPOS, 25, NARETH_INVERTED_HUSK),
    P16_ID: (7, OBSERVATORIO, 28, NARETH_MERIDIAN_WATCHER),
    P17_ID: (6, OBSERVATORIO, 29, NARETH_INVERTED_CUSTODIAN),
    P18_ID: (4, CAMARA, 30, NARETH_ARCONTE_INVERTIDO),
    S18_ID: (10, OBSERVATORIO, 30, NARETH_CUSTODIO_SEM_NORTE),
}
MISSION_CAMPAIGN_BOSSES = frozenset((P18_ID, S18_ID))
MISSION_REWARD_CHOICES = {
    "1": ("Capuz dos Marcos Longos", "Cabeça"),
    "2": ("Selo do Meridiano", "Acessório"),
    "3": ("Relicário da Distância Certa", "Artefato"),
}
P18_REWARD_CHOICES = {
    "1": ("Guarda da Câmara Invertida", "Secundária"),
    "2": ("Selo do Eixo Estável", "Acessório"),
    "3": ("Relicário da Referência Perdida", "Artefato"),
}
MIDGAME_ACTIONS = {
    P14_ID: {
        "receive_map": (1, POSTO, 2, "p14.map_received"),
        "examine_gate": (3, CANAIS, 4, "p14.gate_examined"),
        "follow_bed": (4, CANAIS, 5, "p14.channel_bed_followed"),
        "recover_plate": (6, CANAIS, 7, "p14.measurement_plate_recovered"),
        "compare_plate": (7, CANAIS, 8, "p14.plate_compared"),
        "deliver_plate": (9, POSTO, 10, "p14.plate_delivered"),
    },
    S14_ID: {
        "receive_routes": (1, POSTO, 2, "s14.routes_received"),
        "examine_bridge": (3, CANAIS, 4, "s14.bridge_examined"),
        "follow_low_route": (4, CANAIS, 5, "s14.low_route_followed"),
        "mark_stable_route": (5, CANAIS, 6, "s14.stable_route_marked"),
        "find_access_signs": (6, CANAIS, 7, "s14.underground_access_signs"),
        "report": (8, POSTO, 9, "s14.reported_to_nera"),
    },
    P15_ID: {
        "speak_talen": (1, POSTO, 2, "p15.records_discussed"),
        "measure_short_distance": (3, CAMPOS, 4, "p15.short_distance_measured"),
        "repeat_with_reference": (4, CAMPOS, 5, "p15.alternate_reference_measured"),
        "review_historical_records": (5, CAMPOS, 6, "p15.historical_divergence_observed"),
        "examine_natural_plates": (7, CAMPOS, 8, "p15.natural_plates_examined"),
        "recover_marker": (8, CAMPOS, 9, "p15.marker_fragment_recovered"),
    },
    S15_ID: {
        "receive_last_point": (1, CAMPOS, 2, "s15.last_point_received"),
        "follow_tracks": (2, CAMPOS, 3, "s15.human_tracks_followed"),
        "find_cargo": (3, CAMPOS, 4, "s15.abandoned_cargo_found"),
        "find_travelers": (4, CAMPOS, 5, "s15.travelers_found_safely"),
        "confirm_no_displacement": (5, CAMPOS, 6, "s15.ambiguity_preserved"),
        "mark_return_route": (6, CAMPOS, 7, "s15.return_route_marked"),
    },
    P16_ID: {
        "receive_translation": (1, POSTO, 2, "p16.partial_translation_received"),
        "examine_alignment": (4, OBSERVATORIO, 5, "p16.alignment_platform_examined"),
        "examine_arm": (5, OBSERVATORIO, 6, "p16.mechanical_arm_examined"),
        "record_terms": (6, OBSERVATORIO, 7, "p16.reference_terms_recorded"),
        "read_analog_panel": (8, OBSERVATORIO, 9, "p16.analog_panel_accessed"),
    },
    S16_ID: {
        "receive_checkpoints": (1, POSTO, 2, "s16.checkpoints_received"),
        "reject_old_route": (4, CANAIS, 5, "s16.nonclosing_route_rejected"),
        "record_difference": (6, OBSERVATORIO, 7, "s16.map_difference_recorded"),
        "update_codex": (8, POSTO, 9, "s16.codex_cartografia_atualizado"),
    },
    S17_ID: {
        "speak_talen": (1, POSTO, 2, "s17.plumb_reading_received"),
        "examine_references": (3, OBSERVATORIO, 3, "s17.geometric_reference_examined"),
        "locate_submerged_entry": (4, OBSERVATORIO, 5, "s17.entry_checked"),
        "recover_calibration_piece": (5, OBSERVATORIO, 6, "s17.calibration_piece_recovered"),
        "update_protocols": (7, POSTO, 8, "s17.protocols_updated"),
    },
    P17_ID: {
        "gather_researchers": (1, POSTO, 2, "p17.researchers_reunited"),
        "compare_records": (2, POSTO, 3, "p17.records_compared"),
        "record_custody": (3, POSTO, 4, "p17.anchor_custody_found"),
        "confirm_stability_monitoring": (4, POSTO, 5, "p17.stability_monitoring_confirmed"),
        "open_chamber": (7, OBSERVATORIO, 8, "p17.chamber_access_opened"),
        "examine_incomplete_record": (8, CAMARA, 9, "p17.incomplete_record_examined"),
        "prepare_arconte": (10, OBSERVATORIO, 11, "p17.climax_prepared"),
    },
    P18_ID: {
        "examine_reference_lines": (2, CAMARA, 3, "p18.reference_lines_examined"),
        "identify_archon": (3, CAMARA, 4, "p18.archon_record_identified"),
        "examine_chamber_after_victory": (6, CAMARA, 7, "p18.chamber_examined_after_victory"),
        "record_anchor_function": (7, CAMARA, 8, "p18.anchor_stability_recorded"),
        "record_measurement_function": (8, CAMARA, 9, "p18.nareth_measurement_recorded"),
        "record_logistics_direction": (9, CAMARA, 10, "p18.crimson_continuity_recorded"),
    },
    S18_ID: {
        "read_cartography": (1, POSTO, 2, "s18.cartography_read"),
        "compare_old_markers": (3, CAMPINAS, 4, "s18.old_markers_compared"),
        "recover_route_plate": (5, CANAIS, 6, "s18.route_plate_recovered"),
        "compare_travel_distances": (7, CAMPOS, 8, "s18.traveler_distances_compared"),
        "follow_service_route": (9, OBSERVATORIO, 10, "s18.service_route_followed"),
        "inspect_broken_reference": (11, OBSERVATORIO, 12, "s18.broken_reference_inspected"),
        "trace_modern_route": (13, POSTO, 14, "s18.modern_route_traced"),
        "update_codex": (14, POSTO, 15, "s18.codex_updated"),
    },
}

TITLES = MISSION_TITLES


@dataclass(frozen=True, slots=True)
class NarethMissionView:
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


class NarethMissionService:
    """Reuses the persistent Quest and shared-objective records for Nareth."""

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
        """Discover a reached Nareth Local and materialize automatic P13 on entry."""
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return
            _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            world = await session.scalar(
                select(WorldState)
                .where(WorldState.character_id == actor_row.id)
                .with_for_update()
            )
            if character is None or world is None or world.region != REGION:
                return
            if character.level < 21 or not await self._p12_complete(session, character.id):
                return
            await self._ensure_auto_p18(session, character)
            await self._reconcile_crimson_gate(session, character)
            if world.location == CAMPINAS:
                await self._ensure_unlock(session, character.id, REGION_UNLOCK)
                await self._ensure_location(session, character.id, CAMPINAS_LOCATION_ID)
                for member_id in character_ids:
                    member = await session.scalar(
                        select(Character).where(Character.id == member_id).with_for_update()
                    )
                    member_world = await session.scalar(
                        select(WorldState)
                        .where(WorldState.character_id == member_id)
                        .with_for_update()
                    )
                    if (
                        member is None
                        or member_world is None
                        or member_world.region != REGION
                        or member_world.location != CAMPINAS
                        or member.level < 21
                        or not await self._p12_complete(session, member_id)
                        or await self._foreground(session, member_id)
                    ):
                        continue
                    await self._ensure_unlock(session, member_id, REGION_UNLOCK)
                    await self._ensure_unlock(session, member_id, EXPLORE_UNLOCK)
                    await self._ensure_location(session, member_id, CAMPINAS_LOCATION_ID)
                    quest = await session.scalar(
                        select(Quest)
                        .where(Quest.character_id == member_id, Quest.quest_id == P13_ID)
                        .with_for_update()
                    )
                    if quest is None:
                        quest = Quest(
                            character_id=member_id,
                            quest_id=P13_ID,
                            title=P13_TITLE,
                            status="active",
                            step=3,
                            content_version=CONTENT_VERSION,
                            state_version=0,
                            progress={"line_examined": False, "markers_compared": False},
                        )
                        session.add(quest)
                        await session.flush()
                        for objective_id in ("p13.crossed_from_vales", "p13.entered_campinas"):
                            await record_campaign_objective_credit(
                                session,
                                character_id=member_id,
                                quest_id=P13_ID,
                                objective_id=objective_id,
                                source_key=f"{objective_id}:{member_id}",
                                evidence={"location": CAMPINAS, "automatic": True},
                            )
            elif world.location == POSTO:
                await self._ensure_location(session, character.id, POSTO_LOCATION_ID)
                members = await self._present(
                    session, character.id, P13_ID, step=7, location=POSTO
                )
                for member in members:
                    await self._ensure_location(session, member.character.id, POSTO_LOCATION_ID)
                    member.quest.step = 8
                    member.quest.state_version += 1
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "reached_posto": True,
                    }
                    await self._credit(
                        session,
                        member.character.id,
                        P13_ID,
                        "p13.reached_posto",
                        f"p13.reached_posto:{member.character.id}",
                        {"location": POSTO, "shared": len(members) > 1},
                    )
                post_transitions = {
                    (P14_ID, 8): 9,
                    (S14_ID, 7): 8,
                    (P15_ID, 9): 10,
                    (S15_ID, 7): 8,
                    (P16_ID, 9): 10,
                    (S16_ID, 7): 8,
                }
                for quest_id in (P14_ID, S14_ID, P15_ID, S15_ID, P16_ID, S16_ID):
                    quest = await self._quest(session, character.id, quest_id)
                    next_step = post_transitions.get((quest_id, quest.step)) if quest else None
                    if next_step is None or quest.status != "active":
                        continue
                    members = await self._present(
                        session, character.id, quest_id, quest.step, POSTO
                    )
                    for member in members:
                        member.quest.step = next_step
                        member.quest.state_version += 1
                        await self._credit(
                            session,
                            member.character.id,
                            quest_id,
                            f"{quest_id.lower()}.returned_to_posto",
                            f"{quest_id.lower()}.return:{member.character.id}",
                            {"location": POSTO, "shared": len(members) > 1},
                        )
                        if quest_id == S15_ID:
                            await self._complete_midgame(
                                session, member.character, member.quest
                            )
                        elif quest_id == P16_ID:
                            await self._ensure_codex(
                                session, member.character.id,
                                "codex.history.protocolos_de_referencia",
                            )
                            await self._complete_midgame(session, member.character, member.quest)
            elif world.location in {CANAIS, CAMPOS, OBSERVATORIO}:
                location_id = {
                    CANAIS: CANAIS_LOCATION_ID,
                    CAMPOS: CAMPOS_LOCATION_ID,
                    OBSERVATORIO: OBSERVATORIO_LOCATION_ID,
                }[world.location]
                await self._ensure_location(session, character.id, location_id)
                await self._ensure_codex(
                    session,
                    character.id,
                    {
                        CANAIS: "codex.location.canais_secos",
                        CAMPOS: "codex.location.campos_invertidos",
                        OBSERVATORIO: "codex.location.observatorio_do_eixo",
                    }[world.location],
                )
                step_transitions = {
                    (P14_ID, 2, CANAIS): 3,
                    (S14_ID, 2, CANAIS): 3,
                    (P15_ID, 2, CAMPOS): 3,
                    (P16_ID, 2, OBSERVATORIO): 4,
                    (S16_ID, 2, CAMPOS): 3,
                    (S16_ID, 3, CANAIS): 4,
                    (S16_ID, 5, OBSERVATORIO): 6,
                }
                for quest_id in (P14_ID, S14_ID, P15_ID, P16_ID, S16_ID):
                    quest = await self._quest(session, character.id, quest_id)
                    next_step = step_transitions.get((quest_id, quest.step, world.location)) if quest else None
                    if next_step is None or quest.status != "active":
                        continue
                    members = await self._present(
                        session, character.id, quest_id, quest.step, world.location
                    )
                    for member in members:
                        await self._ensure_unlock(
                            session,
                            member.character.id,
                            {
                                CANAIS: "explore.nareth.canais_secos",
                                CAMPOS: "explore.nareth.campos_invertidos",
                                OBSERVATORIO: "explore.nareth.observatorio_do_eixo",
                            }[world.location],
                        )
                        member.quest.step = next_step
                        member.quest.state_version += 1
                        await self._credit(
                            session,
                            member.character.id,
                            quest_id,
                            f"{quest_id.lower()}.arrived.{location_id}",
                            f"{quest_id.lower()}.arrived.{location_id}:{member.character.id}",
                            {"location": world.location, "shared": len(members) > 1},
                        )
                        if quest_id in {P14_ID, P15_ID, P16_ID}:
                            await self._credit(
                                session,
                                member.character.id,
                                quest_id,
                                f"{quest_id.lower()}.location_discovered",
                                f"{quest_id.lower()}.location:{location_id}:{member.character.id}",
                                {"location": world.location, "shared": len(members) > 1},
                            )
                        if quest_id == P16_ID and quest.step == 2:
                            await self._credit(
                                session,
                                member.character.id,
                                quest_id,
                                "p16.observatory_discovered",
                                f"p16.observatory_discovered:{member.character.id}",
                                {"location": OBSERVATORIO, "shared": len(members) > 1},
                            )
            await self._process_climax_location(session, character, world)

    async def _ensure_auto_p18(self, session, character) -> None:
        if character.level < 30 or not await self._quest_completed(session, character.id, P17_ID):
            return
        quest = await self._quest(session, character.id, P18_ID)
        if quest is None:
            quest = Quest(
                character_id=character.id,
                quest_id=P18_ID,
                title=P18_TITLE,
                status="active",
                step=1,
                content_version=CONTENT_VERSION_MID,
                state_version=0,
                progress={"automatic_start": True},
            )
            session.add(quest)
            await session.flush()
            await self._credit(
                session, character.id, P18_ID, "p18.started",
                f"p18.started:{character.id}", {"automatic": True, "level": character.level},
            )

    async def _reconcile_crimson_gate(self, session, character) -> None:
        quest = await self._quest(session, character.id, P18_ID)
        if quest is not None and quest.status == "completed" and character.level >= 31:
            await self._ensure_unlock(session, character.id, CRIMSON_UNLOCK)

    async def _process_climax_location(self, session, character, world) -> None:
        location_id = {
            CAMARA: CAMARA_LOCATION_ID,
        }.get(world.location)
        if location_id and await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == CHAMBER_UNLOCK,
            )
        ):
            await self._ensure_location(session, character.id, location_id)
            await self._ensure_codex(session, character.id, "codex.location.camara_do_arconte")
        transitions = {
            (S17_ID, 2, OBSERVATORIO): 3,
            (S17_ID, 6, POSTO): 7,
            (P17_ID, 5, OBSERVATORIO): 6,
            (P17_ID, 9, OBSERVATORIO): 10,
            (P18_ID, 1, CAMARA): 2,
            (S18_ID, 2, CAMPINAS): 3,
            (S18_ID, 4, CANAIS): 5,
            (S18_ID, 6, CAMPOS): 7,
            (S18_ID, 8, OBSERVATORIO): 9,
            (S18_ID, 12, POSTO): 13,
        }
        for quest_id in (S17_ID, P17_ID, P18_ID, S18_ID):
            quest = await self._quest(session, character.id, quest_id)
            next_step = transitions.get((quest_id, quest.step, world.location)) if quest else None
            if next_step is None or quest.status != "active":
                continue
            members = await self._present(session, character.id, quest_id, quest.step, world.location)
            for member in members:
                member.quest.step = next_step
                member.quest.state_version += 1
                await self._credit(
                    session, member.character.id, quest_id,
                    f"{quest_id.lower()}.arrived.{world.location.lower().replace(' ', '_')}",
                    f"{quest_id.lower()}.arrived:{world.location}:{member.character.id}",
                    {"location": world.location, "shared": len(members) > 1},
                )

    async def resume(self, actor: int, quest_id: str) -> NarethMissionView | None:
        if quest_id not in TITLES:
            return None
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == quest_id,
                )
            )
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character.id)
            )
            return await self._view(session, character, quest, world, quest_id)

    async def resume_active(self, actor: int) -> NarethMissionView | None:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is not None and await self._world(session, character.id) is not None:
                await self._reconcile_crimson_gate(session, character)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is not None:
                shared_member = await session.scalar(
                    select(CampaignSharedEncounterMember)
                    .join(GameActivity, GameActivity.id == CampaignSharedEncounterMember.game_activity_id)
                    .where(
                        CampaignSharedEncounterMember.character_id == character.id,
                        GameActivity.status == "active",
                        GameActivity.content_id.in_(tuple(MISSION_CONTENT_IDS.values())),
                    )
                )
                if shared_member is not None:
                    return await self._view_for_character_activity(
                        session, character, shared_member.game_activity_id
                    )
        for quest_id in (
            P18_ID, P17_ID, S18_ID, S17_ID, P16_ID, P15_ID, P14_ID,
            P13_ID, S16_ID, S15_ID, S14_ID, S13_ID,
        ):
            view = await self.resume(actor, quest_id)
            if view is not None and view.status == "active":
                return view
        return None

    async def board(self, actor: int) -> tuple[NarethMissionView | None, ...]:
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is not None:
                await self._reconcile_crimson_gate(session, character)
        return tuple(
            [
                await self.resume(actor, quest_id)
                for quest_id in (
                    P13_ID, S13_ID, P14_ID, S14_ID, P15_ID, S15_ID,
                    P16_ID, S16_ID, S17_ID, P17_ID, P18_ID, S18_ID,
                )
            ]
        )

    async def region_access(self, actor: int) -> bool:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return bool(
                character
                and await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == REGION_UNLOCK,
                    )
                )
            )

    async def known_locations(self, actor: int) -> set[str]:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return set()
            location_ids = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character.id,
                            LocationDiscovery.location_id.in_(
                                (CAMPINAS_LOCATION_ID, POSTO_LOCATION_ID, CANAIS_LOCATION_ID, CAMPOS_LOCATION_ID, OBSERVATORIO_LOCATION_ID, CAMARA_LOCATION_ID)
                            ),
                        )
                    )
                ).all()
            )
            return {
                label
                for location_id, label in (
                    (CAMPINAS_LOCATION_ID, CAMPINAS),
                    (POSTO_LOCATION_ID, POSTO),
                    (CANAIS_LOCATION_ID, CANAIS),
                    (CAMPOS_LOCATION_ID, CAMPOS),
                    (OBSERVATORIO_LOCATION_ID, OBSERVATORIO),
                    (CAMARA_LOCATION_ID, CAMARA),
                )
                if location_id in location_ids
            }

    async def start(self, actor: int, quest_id: str) -> NarethMissionView | None:
        if quest_id in MIDGAME_ACTIONS:
            return await self._start_midgame(actor, quest_id)
        if quest_id != S13_ID:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, _character_ids = await self._locked_state(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if world is None:
                return None
            existing = await session.scalar(
                select(Quest)
                .where(Quest.character_id == character.id, Quest.quest_id == S13_ID)
                .with_for_update()
            )
            if existing is None:
                eligible = await self._s13_eligible(session, character, world)
                if not eligible:
                    return await self._view(session, character, None, world, S13_ID)
                members = await self._eligible_group_at(session, character.id, S13_ID)
                for member, member_world in members:
                    quest = Quest(
                        character_id=member.id,
                        quest_id=S13_ID,
                        title=S13_TITLE,
                        status="active",
                        step=2,
                        content_version=CONTENT_VERSION,
                        state_version=0,
                        progress={"markers": []},
                    )
                    session.add(quest)
                    await session.flush()
                    await self._credit(
                        session,
                        member.id,
                        S13_ID,
                        "s13.received_references",
                        f"s13.received_references:{member.id}",
                        {"giver": "Nera Voss", "location": member_world.location},
                    )
                existing = await session.scalar(
                    select(Quest)
                    .where(Quest.character_id == character.id, Quest.quest_id == S13_ID)
                    .with_for_update()
                )
            return await self._view(session, character, existing, world, S13_ID)

    async def examine(self, actor: int, quest_id: str, version: int, point: str):
        if quest_id != S13_ID or point not in {"a", "b", "c"}:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, _ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, S13_ID)
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return await self._view(session, character, quest, world, S13_ID)
            if not self._valid(
                quest, version, step=2 + len((quest.progress or {}).get("markers", []))
            ):
                return await self._view(session, character, quest, world, S13_ID)
            expected_location = CAMPINAS
            if world.region != REGION or world.location != expected_location:
                return await self._view(session, character, quest, world, S13_ID)
            members = await self._present(session, character.id, S13_ID, quest.step, CAMPINAS)
            for member in members:
                progress = dict(member.quest.progress or {})
                markers = list(progress.get("markers", []))
                next_point = ("a", "b", "c")[len(markers)] if len(markers) < 3 else None
                if point != next_point:
                    continue
                markers.append(point)
                member.quest.progress = {**progress, "markers": markers}
                member.quest.step = 2 + len(markers)
                member.quest.state_version += 1
                await self._credit(
                    session,
                    member.character.id,
                    S13_ID,
                    f"s13.marker.{point}",
                    f"s13.marker.{point}:{member.character.id}",
                    {"location": CAMPINAS, "shared": len(members) > 1},
                )
            return await self._view(session, character, quest, world, S13_ID)

    async def advance(self, actor: int, quest_id: str, version: int, action: str):
        if quest_id not in TITLES:
            return None
        if quest_id in MIDGAME_ACTIONS:
            return await self._advance_midgame(actor, quest_id, version, action)
        async with self.sessions.begin() as session:
            character, _ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return await self._view(session, character, quest, world, quest_id)

            p13_steps = {
                "line": (3, CAMPINAS, 4, "p13.old_stone_line"),
                "compare": (4, CAMPINAS, 5, "p13.compare_markers"),
                "horizon_brazier": (5, CAMPINAS, 6, "p13.register_horizon_brazier"),
                "follow_route": (6, CAMPINAS, 7, "p13.follow_verified_route"),
                "posto_brazier": (8, POSTO, 9, "p13.register_posto_brazier"),
                "speak_nera": (9, POSTO, 10, "p13.speak_nera"),
                "record_codex": (10, POSTO, 10, "p13.record_rotas_codex"),
            }
            s13_steps = {
                "compare": (5, CAMPINAS, 6, "s13.compare_references"),
                "report": (6, POSTO, 6, "s13.report_to_nera"),
            }
            config = (p13_steps if quest_id == P13_ID else s13_steps).get(action)
            if config is None:
                return await self._view(session, character, quest, world, quest_id)
            expected_step, expected_location, next_step, objective_id = config
            if not self._valid(quest, version, step=expected_step):
                return await self._view(session, character, quest, world, quest_id)
            if world.region != REGION or world.location != expected_location:
                return await self._view(session, character, quest, world, quest_id)
            members = await self._present(
                session, character.id, quest_id, expected_step, expected_location
            )
            for member in members:
                if quest_id == P13_ID and action == "horizon_brazier":
                    await self._ensure(
                        session,
                        Brazier,
                        member.character.id,
                        "brazier_id",
                        HORIZON_BRAZIER,
                    )
                elif quest_id == P13_ID and action == "posto_brazier":
                    await self._ensure(
                        session,
                        Brazier,
                        member.character.id,
                        "brazier_id",
                        POSTO_BRAZIER,
                    )
                elif quest_id == P13_ID and action == "follow_route":
                    await self._ensure_unlock(session, member.character.id, CAMPINAS_POSTO_ROUTE)
                elif quest_id == P13_ID and action == "speak_nera":
                    await self._ensure_codex(session, member.character.id, "codex.figure.nera_voss")
                elif quest_id == P13_ID and action == "record_codex":
                    await self._record_p13_codex(session, member.character.id)
                if quest_id == P13_ID and action == "line":
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "line_examined": True,
                    }
                elif quest_id == P13_ID and action == "compare":
                    member.quest.progress = {
                        **(member.quest.progress or {}),
                        "markers_compared": True,
                    }
                member.quest.step = next_step
                member.quest.state_version += 1
                await self._credit(
                    session,
                    member.character.id,
                    quest_id,
                    objective_id,
                    f"{objective_id}:{member.character.id}",
                    {"location": expected_location, "shared": len(members) > 1},
                )
                if quest_id == P13_ID and action == "record_codex":
                    await self._complete_p13(session, member.character, member.quest)
                elif quest_id == S13_ID and action == "report":
                    await self._complete_s13(session, member.character, member.quest)
            return await self._view(session, character, quest, world, quest_id)

    async def _start_midgame(self, actor: int, quest_id: str) -> NarethMissionView | None:
        async with self.sessions.begin() as session:
            character, roster_ids = await self._locked_state(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            existing = await self._quest(session, character.id, quest_id)
            if existing is not None:
                return await self._view(session, character, existing, world, quest_id)
            if not await self._midgame_eligible(session, character, world, quest_id):
                return await self._view(session, character, None, world, quest_id)
            for member_id in roster_ids:
                member = await session.scalar(
                    select(Character).where(Character.id == member_id).with_for_update()
                )
                member_world = await self._world(session, member_id)
                if (
                    member is None
                    or member_world is None
                    or not await self._midgame_eligible(session, member, member_world, quest_id)
                    or await self._quest(session, member_id, quest_id) is not None
                ):
                    continue
                session.add(
                    Quest(
                        character_id=member.id,
                        quest_id=quest_id,
                        title=MISSION_TITLES[quest_id],
                        status="active",
                        step=1,
                        content_version=CONTENT_VERSION_MID,
                        state_version=0,
                        progress={},
                    )
                )
                await session.flush()
                await self._credit(
                    session,
                    member.id,
                    quest_id,
                    f"{quest_id.lower()}.started",
                    f"{quest_id.lower()}.started:{member.id}",
                    {"location": member_world.location},
                )
            quest = await self._quest(session, character.id, quest_id)
            return await self._view(session, character, quest, world, quest_id)

    async def _midgame_eligible(self, session, character, world, quest_id: str) -> bool:
        if (
            character is None
            or world is None
            or world.region != REGION
            or await self._foreground(session, character.id) is not None
        ):
            return False
        if quest_id == P18_ID:
            return bool(
                character.level >= 30
                and await self._quest_completed(session, character.id, P17_ID)
            )
        if quest_id == S17_ID:
            return bool(
                character.level >= 28
                and world.location == POSTO
                and await session.scalar(
                    select(LocationDiscovery.id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id == OBSERVATORIO_LOCATION_ID,
                    )
                )
            )
        gates = {
            P14_ID: (23, POSTO, P13_ID, "completed"),
            S14_ID: (24, POSTO, P14_ID, "completed"),
            P15_ID: (25, POSTO, P14_ID, "completed"),
            S15_ID: (25, CAMPOS, P15_ID, ("active", "completed")),
            P16_ID: (27, POSTO, P15_ID, "completed"),
            S16_ID: (27, POSTO, P16_ID, ("active", "completed")),
            P17_ID: (29, POSTO, P16_ID, "completed"),
            S18_ID: (30, POSTO, S16_ID, "completed"),
        }
        if quest_id not in gates:
            return False
        level, location, required_quest, status = gates[quest_id]
        if character.level < level or world.location != location:
            return False
        statuses = status if isinstance(status, tuple) else (status,)
        eligible = bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == required_quest,
                    Quest.status.in_(statuses),
                )
            )
        )
        if quest_id == S17_ID:
            eligible = eligible and bool(
                await session.scalar(
                    select(LocationDiscovery.id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id == OBSERVATORIO_LOCATION_ID,
                    )
                )
            )
        if quest_id == S18_ID:
            eligible = eligible and await self._quest_completed(session, character.id, P17_ID)
        return eligible

    async def _advance_midgame(self, actor: int, quest_id: str, version: int, action: str):
        config = MIDGAME_ACTIONS[quest_id].get(action)
        if config is None:
            return await self.resume(actor, quest_id)
        expected_step, expected_location, next_step, objective_id = config
        async with self.sessions.begin() as session:
            character, _roster_ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if (
                quest is None
                or world is None
                or not self._valid_midgame(quest, version, expected_step)
                or world.region != REGION
                or world.location != expected_location
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world, quest_id)
            if quest_id == S17_ID and action == "locate_submerged_entry":
                entry_unlocked = await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == "dungeon.nareth.observatorio_afundado",
                    )
                )
                if not entry_unlocked:
                    return await self._view(session, character, quest, world, quest_id)
            members = await self._present(
                session, character.id, quest_id, expected_step, expected_location
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                member_objective_id = objective_id
                if quest_id == S17_ID and action == "examine_references":
                    reference_count = min(
                        int(progress.get("geometric_references_examined", 0)) + 1, 3
                    )
                    progress["geometric_references_examined"] = reference_count
                    member.quest.step = 4 if reference_count == 3 else 3
                    member_objective_id = f"s17.geometric_reference_{reference_count}"
                elif quest_id == P18_ID and action == "examine_chamber_after_victory":
                    member.quest.step = next_step
                else:
                    member.quest.step = next_step
                member.quest.state_version += 1
                progress[action] = True
                member.quest.progress = progress
                if quest_id == P14_ID and action == "receive_map":
                    await self._ensure_unlock(session, member.character.id, POSTO_CANAIS_ROUTE)
                elif quest_id == P15_ID and action == "speak_talen":
                    await self._ensure_unlock(session, member.character.id, CANAIS_CAMPOS_ROUTE)
                    await self._ensure_codex(session, member.character.id, "codex.figure.talen_orm")
                elif quest_id == P16_ID and action == "receive_translation":
                    await self._ensure_unlock(session, member.character.id, CAMPOS_OBSERVATORIO_ROUTE)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P14_CODEX, "codex.fragment.nareth.canais.p14_plate"
                    )
                elif quest_id == P14_ID and action == "compare_plate":
                    await self._ensure_codex(session, member.character.id, P14_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P14_CODEX, "codex.fragment.nareth.canais.p14_plate"
                    )
                elif quest_id == S14_ID and action == "mark_stable_route":
                    await self._ensure_codex(session, member.character.id, ROTAS_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, ROTAS_CODEX, "codex.fragment.nareth.canais.s14_route"
                    )
                elif quest_id == P15_ID and action == "review_historical_records":
                    await self._ensure_codex(session, member.character.id, "codex.mystery.horizonte_discordante")
                    await self._ensure_codex_fragment(
                        session, member.character.id, "codex.mystery.horizonte_discordante",
                        "codex.fragment.nareth.campos.p15_records",
                    )
                elif quest_id == S15_ID and action == "confirm_no_displacement":
                    await self._ensure_codex_fragment(
                        session, member.character.id, ROTAS_CODEX,
                        "codex.fragment.nareth.campos.s15_routes",
                    )
                elif quest_id == P16_ID and action == "read_analog_panel":
                    await self._ensure_codex(session, member.character.id, "codex.mystery.o_eixo")
                    await self._ensure_codex_fragment(
                        session, member.character.id, "codex.mystery.o_eixo",
                        "codex.fragment.nareth.observatory.p16_protocol",
                    )
                    await self._ensure_codex(session, member.character.id, "codex.history.protocolos_de_referencia")
                elif quest_id == S16_ID and action == "update_codex":
                    await self._ensure_codex(session, member.character.id, S16_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, S16_CODEX,
                        "codex.fragment.nareth.observatory.s16_cartography",
                    )
                elif quest_id == S17_ID and action == "update_protocols":
                    await self._ensure_codex(session, member.character.id, S17_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, S17_CODEX,
                        "codex.fragment.nareth.observatory.s17_plumb_protocol",
                    )
                elif quest_id == P17_ID and action == "record_custody":
                    await self._ensure_codex(session, member.character.id, P17_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P17_CODEX,
                        "codex.fragment.nareth.observatory.p17_anchor_custody",
                    )
                elif quest_id == P17_ID and action == "open_chamber":
                    await self._ensure_unlock(session, member.character.id, CHAMBER_UNLOCK)
                    await self._ensure_unlock(session, member.character.id, CHAMBER_ROUTE_UNLOCK)
                    await self._ensure_codex(
                        session, member.character.id, "codex.location.camara_do_arconte"
                    )
                elif quest_id == P17_ID and action == "examine_incomplete_record":
                    await self._ensure_codex(session, member.character.id, P18_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P18_CODEX,
                        "codex.fragment.nareth.chamber.incomplete_stability_record",
                    )
                elif quest_id == P18_ID and action == "identify_archon":
                    await self._ensure_codex(session, member.character.id, P18_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P18_CODEX,
                        "codex.fragment.nareth.chamber.archon_identified",
                    )
                elif quest_id == P18_ID and action == "record_anchor_function":
                    await self._ensure_codex(session, member.character.id, P18_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, P18_CODEX,
                        "codex.fragment.nareth.chamber.anchors_stabilized_veil",
                    )
                elif quest_id == P18_ID and action == "record_measurement_function":
                    await self._ensure_codex_fragment(
                        session, member.character.id, P18_CODEX,
                        "codex.fragment.nareth.chamber.regional_measurement",
                    )
                elif quest_id == P18_ID and action == "record_logistics_direction":
                    await self._ensure_codex_fragment(
                        session, member.character.id, ROTAS_CODEX,
                        "codex.fragment.nareth.chamber.continuity_crimson_direction",
                    )
                elif quest_id == S18_ID and action == "update_codex":
                    await self._ensure_codex(session, member.character.id, S18_CODEX)
                    await self._ensure_codex_fragment(
                        session, member.character.id, S18_CODEX,
                        "codex.fragment.nareth.routes.s18_modern_route",
                    )
                    await self._ensure_codex_fragment(
                        session, member.character.id, ROTAS_CODEX,
                        "codex.fragment.nareth.routes.s18_verified_points",
                    )
                if quest_id == P17_ID and action == "open_chamber":
                    await self._ensure_location(session, member.character.id, CAMARA_LOCATION_ID)
                await self._credit(
                    session,
                    member.character.id,
                    quest_id,
                    member_objective_id,
                    f"{member_objective_id}:{member.character.id}",
                    {
                        "location": expected_location,
                        "shared": len(members) > 1,
                        **(
                            {"ordinal": progress["geometric_references_examined"]}
                            if quest_id == S17_ID and action == "examine_references"
                            else {}
                        ),
                    },
                )
                if quest_id == P14_ID and action == "deliver_plate":
                    await self._complete_midgame(session, member.character, member.quest)
                elif quest_id == S14_ID and action == "report":
                    await self._complete_midgame(session, member.character, member.quest)
                elif quest_id == S16_ID and action == "update_codex":
                    await self._complete_midgame(session, member.character, member.quest)
                elif quest_id == S17_ID and action == "update_protocols":
                    await self._complete_midgame(session, member.character, member.quest)
                elif quest_id == P17_ID and action == "prepare_arconte":
                    await self._complete_midgame(session, member.character, member.quest)
                elif quest_id == S18_ID and action == "update_codex":
                    await self._complete_midgame(session, member.character, member.quest)
            return await self._view(session, character, quest, world, quest_id)

    async def _complete_midgame(self, session, character, quest):
        if quest.quest_id in {P15_ID, P18_ID}:
            quest.status = "active"
            quest.step = 10
            quest.progress = {**(quest.progress or {}), "awaiting_reward_choice": True}
            quest.state_version += 1
            return
        quest.status = "completed"
        quest.step = {
            P14_ID: 9,
            S14_ID: 8,
            P15_ID: 10,
            P16_ID: 9,
            S15_ID: 7,
            S16_ID: 8,
            S17_ID: 7,
            P17_ID: 11,
            P18_ID: 10,
            S18_ID: 14,
        }[quest.quest_id]
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        rewards = {
            P14_ID: (P14_REWARD_SOURCE, 22000, 450, (("material.nareth.bronze_de_marco", 1), ("material.nareth.erva_de_vento", 2), ("material.nareth.po_de_eixo", 1))),
            S14_ID: (S14_REWARD_SOURCE, 16380, 350, (("material.nareth.erva_de_vento", 1), ("material.nareth.po_de_eixo", 1))),
            S15_ID: (S15_REWARD_SOURCE, 9920, 240, (("material.nareth.couro_de_horizonte", 2),)),
            P16_ID: (P16_REWARD_SOURCE, 27800, 640, (("material.nareth.bronze_de_marco", 2), ("material.nareth.po_de_eixo", 2))),
            S16_ID: (S16_REWARD_SOURCE, 19460, 380, (("material.nareth.bronze_de_marco", 2), ("material.nareth.couro_de_horizonte", 1), ("material.nareth.po_de_eixo", 1))),
            S17_ID: (S17_REWARD_SOURCE, 20545, 390, (("material.nareth.bronze_de_marco", 1), ("material.nareth.erva_de_vento", 1), ("material.nareth.po_de_eixo", 2))),
            P17_ID: (P17_REWARD_SOURCE, 30950, 680, (("material.nareth.bronze_de_marco", 3), ("material.nareth.po_de_eixo", 1))),
            S18_ID: (S18_REWARD_SOURCE, 32600, 690, (("material.nareth.bronze_de_marco", 2), ("material.nareth.couro_de_horizonte", 2), ("material.nareth.erva_de_vento", 2), ("material.nareth.po_de_eixo", 2))),
        }
        source, xp, crowns, materials = rewards[quest.quest_id]
        await self._reward(session, character, quest, source, xp, crowns, materials)
        if quest.quest_id == P14_ID:
            await self._ensure_unlock(session, character.id, HUNT_UNLOCK.replace("campinas_do_meridiano", "canais_secos"))
        elif quest.quest_id == P16_ID:
            await self._ensure_unlock(session, character.id, "hunt.manual.nareth.observatorio_do_eixo")
        elif quest.quest_id == P17_ID:
            await self._ensure_unlock(session, character.id, CHAMBER_UNLOCK)
            await self._ensure_location(session, character.id, OBSERVATORIO_LOCATION_ID)
        elif quest.quest_id == S18_ID:
            await self._ensure_codex(session, character.id, ROTAS_CODEX)
        await consolidate_character_level(session, character)
        if quest.quest_id == P17_ID:
            await self._ensure_auto_p18(session, character)
        from asterion.application.nareth_feats import reconcile_nareth_feats

        await reconcile_nareth_feats(session, character)

    async def start_solo_combat(
        self, actor: int, quest_id: str, version: int
    ) -> NarethMissionView | None:
        config = MISSION_COMBAT.get(quest_id)
        if config is None:
            return await self.resume(actor, quest_id)
        step, location, level, creature = config
        async with self.sessions.begin() as session:
            character, _roster_ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if (
                quest is None
                or world is None
                or not self._valid_midgame(quest, version, step)
                or world.region != REGION
                or world.location != location
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world, quest_id)
            content_id = MISSION_CONTENT_IDS[quest_id]
            if quest_id in MISSION_CAMPAIGN_BOSSES:
                opening_combat = await create_campaign_boss_profile(
                    session, (character,), creature, level,
                    flavor=self._combat_flavor(quest_id),
                    opening_log=self._combat_flavor(quest_id),
                )
                opening_combat = configure_nareth_campaign_boss(
                    opening_combat, creature.creature_id, shared=False
                )
                activity, _, _ = await CombatRepository(session).create(
                    character, content_id, opening_combat
                )
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
                activity.status = "failed"
                character.hp = character.max_hp
                progress.update(activity_id=None, awaiting_retry=True, opening_defeat=True)
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world, quest_id)

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
            activity_type="campaign_nareth",
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
        return replace(
            initial, proposal_id=proposal.proposal_id, proposal_status=proposal.status
        )

    async def start_group_combat(
        self, actor: int, proposal_id: UUID, *, expected_revision: int
    ):
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
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ):
        shared_result = await self._shared_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if shared_result is not None:
            return shared_result
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
                    candidate
                    for candidate, content_id in MISSION_CONTENT_IDS.items()
                    if content_id == activity.content_id
                ),
                None,
            )
            if quest_id is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if quest is None or world is None:
                return None
            current = await self._view(session, character, quest, world, quest_id)
            combat, _, _ = await current_combat(session, activity)
            if (
                activity.status != "active"
                or combat is None
                or combat.version != version
                or not self._valid_midgame(quest, quest.state_version, MISSION_COMBAT[quest_id][0])
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
                category=MISSION_COMBAT[quest_id][3].category,
            )
            if updated is None or updated.version == version:
                return current
            if quest_id in MISSION_CAMPAIGN_BOSSES:
                await self._record_nareth_boss_evidence(
                    session, character.id, MISSION_COMBAT[quest_id][3].creature_id, updated
                )
            if updated.result == "victory":
                activity.status = "completed"
                await normalize_character_hp(session, character)
                quest.step += 2 if quest_id == P18_ID else 1
                quest.progress = {
                    **(quest.progress or {}),
                    "activity_id": None,
                    "awaiting_retry": False,
                    "combat_victory": True,
                }
                await self.road._bestiary(
                    session,
                    character.id,
                    MISSION_COMBAT[quest_id][3].creature_id,
                    victory=True,
                    observation_category=MISSION_COMBAT[quest_id][3].category,
                )
                if quest_id == P18_ID:
                    await self._grant_arconte_core(session, character)
                await record_campaign_objective_credit(
                    session,
                    character_id=character.id,
                    quest_id=quest_id,
                    objective_id=f"{quest_id.lower()}.scripted_encounter_victory",
                    source_key=f"{quest_id.lower()}.combat:{activity.id}",
                    evidence={"result": "victory", "location": world.location},
                )
            elif updated.result == "defeat":
                activity.status = "failed"
                character.hp = character.max_hp
                quest.progress = {
                    **(quest.progress or {}),
                    "activity_id": None,
                    "awaiting_retry": True,
                }
            if updated.result is not None:
                quest.state_version += 1
            return await self._view(session, character, quest, world, quest_id)

    async def campaign_action(
        self, actor: int, activity_id: UUID, version: int, action_index: int, target_code: str
    ):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            shared, member, combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is None or member is None or combat is None:
                return await self._combat_view_for_actor(actor, activity_id)
            intent = campaign_action_intent(combat, member.actor_key, action_index, target_code)
            if intent is None:
                return await self._view_for_character_activity(session, character, activity_id)
            action, target_id = intent
        return await self.action_combat(
            actor, activity_id, version, action, target_id=target_id
        )

    async def consumable_selection(
        self, actor: int, activity_id: UUID, version: int, **kwargs
    ):
        current = await self._combat_view_for_actor(actor, activity_id)
        if current is None or current.combat is None:
            return current
        if current.combat.version != version:
            return replace(current, consumable_notice="⚠️ O combate foi atualizado.")
        return derive_consumable_selection(current, **kwargs)

    async def _combat_view_for_actor(self, actor: int, activity_id: UUID):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            shared, member, _combat = await campaign_combat_for_activity(
                session, activity_id, character.id
            )
            if shared is not None and member is not None:
                return await self._view_for_character_activity(session, character, activity_id)
            activity = await session.scalar(
                select(GameActivity).where(
                    GameActivity.id == activity_id,
                    GameActivity.character_id == character.id,
                    GameActivity.content_id.in_(tuple(MISSION_CONTENT_IDS.values())),
                )
            )
            if activity is None:
                return None
            quest_id = next(
                (
                    candidate
                    for candidate, content_id in MISSION_CONTENT_IDS.items()
                    if content_id == activity.content_id
                ),
                None,
            )
            quest = await self._quest(session, character.id, quest_id) if quest_id else None
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world, quest_id)

    async def _shared_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action: str | None,
        *,
        consumable_id: str | None = None,
        target_id: str | None = None,
        effect_id: str | None = None,
    ):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _shared, member_seed, _combat = await campaign_combat_for_activity(
                session, activity_id, seed.id
            )
            if member_seed is None:
                return None
            locked = await lock_campaign_encounter(session, activity_id, seed.id)
            if locked is None or locked.encounter.quest_id not in MISSION_COMBAT:
                return None
            quest_id = locked.encounter.quest_id
            creature = MISSION_COMBAT[quest_id][3]
            character = locked.characters.get(seed.id)
            if character is None:
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
                consumable_budget=ENCOUNTER_CONSUMABLE_LIMITS.get(creature.category, 0),
            )
            if updated.version == version:
                return await self._view_for_character_activity(session, character, activity_id)
            if stack is not None:
                stack.quantity -= 1
            member_by_character = {row.character_id: row for row in locked.members}
            quest_rows = list(
                (
                    await session.scalars(
                        select(Quest)
                        .where(
                            Quest.character_id.in_(locked.characters),
                            Quest.quest_id == quest_id,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            quests = {row.character_id: row for row in quest_rows}
            for character_id, participant in locked.characters.items():
                roster_member = member_by_character[character_id]
                quest = quests.get(character_id)
                if quest_id in MISSION_CAMPAIGN_BOSSES:
                    await self._record_nareth_boss_evidence(
                        session, character_id, creature.creature_id, updated
                    )
                if updated.result == "victory":
                    await normalize_character_hp(session, participant)
                    await self.road._bestiary(
                        session,
                        participant.id,
                        creature.creature_id,
                        victory=True,
                        observation_category=creature.category,
                    )
                    if quest_id == P18_ID and roster_member.role == "eligible":
                        await self._grant_arconte_core(session, participant)
                    if roster_member.role == "eligible" and quest is not None:
                        quest.step += 2 if quest_id == P18_ID else 1
                        quest.state_version += 1
                        quest.progress = {
                            **(quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": False,
                            "combat_victory": True,
                        }
                        await record_campaign_objective_credit(
                            session,
                            character_id=character_id,
                            quest_id=quest_id,
                            objective_id=f"{quest_id.lower()}.scripted_encounter_victory",
                            source_key=f"{quest_id.lower()}.combat:{locked.encounter.id}",
                            evidence={"result": "victory", "shared": True},
                        )
                elif updated.result == "defeat":
                    participant.hp = participant.max_hp
                    if roster_member.role == "eligible" and quest is not None:
                        quest.state_version += 1
                        quest.progress = {
                            **(quest.progress or {}),
                            "activity_id": None,
                            "awaiting_retry": True,
                        }
            if updated.result is not None:
                await settle_campaign_encounter(session, locked, updated.result)
            return await self._view_for_character_activity(session, character, activity_id)

    async def _combat_eligibility(self, session, character, payload) -> ActivityEligibility:
        quest_id = payload.get("quest_id")
        config = MISSION_COMBAT.get(quest_id)
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == quest_id)
        )
        world = await self._world(session, character.id)
        active = await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character.id, GameActivity.status == "active"
            )
        )
        expected_step = config[0] if config else -1
        same_location = bool(
            config
            and world
            and world.region == REGION
            and world.location == payload.get("location") == config[1]
        )
        if active is not None or not same_location:
            role = "ineligible"
        elif quest is not None and quest.status == "active" and quest.step == expected_step:
            role = "eligible"
        elif quest is None or quest.status == "completed" or quest.step > expected_step:
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
        config = MISSION_COMBAT.get(quest_id)
        if config is None:
            raise GroupError("invalid_activity")
        _step, location, level, creature = config
        participant_rows = list(
            (
                await session.scalars(
                    select(GroupActivityParticipant)
                    .where(GroupActivityParticipant.proposal_id == proposal.id)
                    .order_by(GroupActivityParticipant.ordinal)
                )
            ).all()
        )
        participant_by_id = {row.character_id: row for row in participant_rows}
        group = await session.get(SocialGroup, proposal.group_id)
        if group is None:
            raise GroupError("not_in_group")
        roster = []
        party = []
        for index, character in enumerate(characters, start=1):
            participant = participant_by_id.get(character.id)
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
                    checkpoint=MISSION_CHECKPOINTS[quest_id],
                )
            )
        lead = characters[0]
        flavor = self._combat_flavor(quest_id)
        if quest_id in MISSION_CAMPAIGN_BOSSES:
            combat = await create_campaign_boss_profile(
                session, characters, creature, level, flavor=flavor, opening_log=flavor
            )
            combat = configure_nareth_campaign_boss(
                combat, creature.creature_id, shared=True
            )
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
                flavor=flavor,
                opening_log=flavor,
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
            campaign_boss=quest_id in MISSION_CAMPAIGN_BOSSES,
        )
        for member in roster:
            await self.road._bestiary(
                session,
                member.character.id,
                creature.creature_id,
                victory=False,
                observation_category=creature.category,
            )
            if member.role != "eligible":
                continue
            quest = await session.scalar(
                select(Quest)
                .where(
                    Quest.character_id == member.character.id,
                    Quest.quest_id == quest_id,
                )
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

    async def _view_for_character_activity(self, session, character, activity_id):
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
            if quest_id is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            if quest is None:
                return None
            return await self._view(session, character, quest, world, quest_id)

        quest_id = shared.quest_id
        quest = await self._quest(session, character.id, quest_id)
        world = await self._world(session, character.id)
        if quest is None:
            base = NarethMissionView(
                character_id=character.id,
                quest_id=quest_id,
                title=MISSION_TITLES[quest_id],
                kind="combat",
                status="helper",
                step=None,
                state_version=0,
                progress={"helper": True},
                location=world.location if world else "",
                level=character.level,
            )
        else:
            base = await self._view(session, character, quest, world, quest_id)
        if shared.status != "active" or combat is None:
            if member.role == "eligible" and quest is not None:
                return replace(base, activity_id=None, encounter_id=shared.id, combat=None)
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
        consumables = await consumable_state(
            session,
            character,
            combat,
            MISSION_COMBAT[quest_id][3].category,
            actor_key=member.actor_key,
        )
        return replace(
            base,
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

    @staticmethod
    def _combat_flavor(quest_id: str) -> str:
        return {
            P14_ID: "Um Escaravelho de Canal bloqueia a junção de referências divergentes.",
            P15_ID: "Um Casco Invertido ocupa o ponto das placas naturais.",
            P16_ID: "Um Vigia do Meridiano protege o Observatório do Eixo.",
        }.get(quest_id, "Um encontro roteirizado bloqueia o caminho.")

    async def choose_midgame_reward(
        self, actor: int, version: int, choice: str, quest_id: str = P15_ID
    ):
        choices = (
            MISSION_REWARD_CHOICES if quest_id == P15_ID
            else P18_REWARD_CHOICES if quest_id == P18_ID
            else {}
        )
        if choice not in choices:
            return await self.resume(actor, quest_id)
        async with self.sessions.begin() as session:
            character, _ids = await self._locked_state(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id, quest_id)
            world = await self._world(session, character.id)
            expected_location = POSTO if quest_id == P15_ID else CAMARA
            if (
                world is None or not self._valid_midgame(quest, version, 10)
                or world.region != REGION or world.location != expected_location
                or await self._foreground(session, character.id) is not None
            ):
                return await self._view(session, character, quest, world, quest_id)
            source_id = P15_REWARD_SOURCE if quest_id == P15_ID else P18_REWARD_SOURCE
            existing = await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == source_id,
                ).with_for_update()
            )
            selected = choice
            if existing is None:
                name, slot = choices[choice]
                xp, crowns = (24800, 480) if quest_id == P15_ID else (58680, 1100)
                rarity, item_level = ("Raro", 25) if quest_id == P15_ID else ("Épico", 30)
                payload = materialize_equipment(
                    f"{source_id}:{character.id}:{choice}", rarity, item_level,
                    forced_name=name, forced_slot=slot, bound=True,
                )
                event = RewardEvent(character_id=character.id, source_id=source_id)
                session.add(event)
                await session.flush()
                character.xp += xp
                character.crowns += crowns
                components = [
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=xp),
                    RewardComponent(reward_event_id=event.id, kind="crowns", quantity=crowns),
                    RewardComponent(
                        reward_event_id=event.id, kind="equipment", quantity=1,
                        payload=payload | {"choice": choice},
                    ),
                ]
                if quest_id == P18_ID:
                    for material_id, quantity in (
                        ("material.nareth.bronze_de_marco", 4),
                        ("material.nareth.po_de_eixo", 4),
                    ):
                        components.append(
                            RewardComponent(
                                reward_event_id=event.id, kind="material",
                                item_id=material_id, quantity=quantity,
                                payload={"material_id": material_id, "bound": True},
                            )
                        )
                        await self.road.deliver_material(
                            session, character, material_id, quantity,
                            f"{source_id}:material:{material_id}",
                        )
                session.add_all(components)
                source_key = f"{source_id}:equipment:{choice}"
                if await self.road._inventory_slots(session, character.id) < 60:
                    from asterion.application.equipment import equipment_instance_payload

                    item_id, instance = equipment_instance_payload(payload)
                    session.add(EquipmentItem(
                        id=item_id, character_id=character.id, source_key=source_key,
                        item_name=instance["item_name"], rarity=instance["rarity"],
                        slot=instance["slot"], item_level=instance["item_level"], bound=True,
                        payload=instance,
                    ))
                else:
                    await self.road._pending(session, character.id, source_key, "equipment", payload)
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
            quest.step = 10
            quest.progress = {
                **(quest.progress or {}), "completed": True, "reward_choice": selected,
            }
            quest.state_version += 1
            if quest_id == P15_ID:
                await self._ensure_unlock(session, character.id, "hunt.manual.nareth.campos_invertidos")
            else:
                await self._ensure_unlock(
                    session, character.id, "recipe.nareth.arconte.calibracao"
                )
                entry = await session.scalar(
                    select(BestiaryEntry).where(
                        BestiaryEntry.character_id == character.id,
                        BestiaryEntry.creature_id == "arconte_invertido",
                    ).with_for_update()
                )
                if entry is not None:
                    await self.road.bestiary.add_evidence(
                        session, entry, character.id, "arconte_invertido",
                        "p18_completed", "mission", 5,
                    )
                    await self.road.bestiary.refresh_boss_mastery(
                        session, character.id, "arconte_invertido"
                    )
            await consolidate_character_level(session, character)
            await self._reconcile_crimson_gate(session, character)
            from asterion.application.nareth_feats import reconcile_nareth_feats

            await reconcile_nareth_feats(session, character)
            return await self._view(session, character, quest, world, quest_id)

    async def _grant_arconte_core(self, session, character) -> None:
        source_id = "p18.arconte.first_victory.core"
        existing = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source_id,
            ).with_for_update()
        )
        if existing is not None:
            return
        material_id = "material.nareth.nucleo_arconte_invertido"
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="material",
                item_id=material_id,
                quantity=1,
                payload={"material_id": material_id, "bound": True},
            )
        )
        await self.road.deliver_material(
            session, character, material_id, 1,
            f"{source_id}:material:{material_id}", bound=True,
        )

    async def _record_nareth_boss_evidence(
        self, session, character_id, creature_id: str, combat
    ) -> None:
        await self.road.bestiary.record_combat_events(
            session, character_id, creature_id, None, combat
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            ).with_for_update()
        )
        if entry is None:
            return
        evidence_categories = {"phase": "phase", "mechanic": "mechanic", "action": "behavior"}
        for evidence_id in nareth_boss_phase_evidence(combat):
            prefix = evidence_id.split(":", 1)[0]
            await self.road.bestiary.add_evidence(
                session, entry, character_id, creature_id, evidence_id,
                evidence_categories[prefix], 5 if prefix == "mechanic" else 4,
            )
        await self.road.bestiary.refresh_boss_mastery(
            session, character_id, creature_id
        )

    async def _complete_p13(self, session, character, quest):
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await self._ensure_unlock(session, character.id, HUNT_UNLOCK)
        await self._reward(
            session,
            character,
            quest,
            P13_REWARD_SOURCE,
            19350,
            420,
            (
                ("material.nareth.bronze_de_marco", 1),
                ("material.nareth.couro_de_horizonte", 1),
            ),
        )
        achievement = await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == "feat.nareth.primeiro_meridiano",
            )
        )
        if achievement is None:
            session.add(
                Achievement(
                    character_id=character.id,
                    achievement_id="feat.nareth.primeiro_meridiano",
                )
            )
        await consolidate_character_level(session, character)

    async def _complete_s13(self, session, character, quest):
        quest.status = "completed"
        quest.progress = {**(quest.progress or {}), "completed": True}
        quest.state_version += 1
        await self._ensure_codex_fragment(session, character.id, ROTAS_CODEX, CODEX_S13_FRAGMENT)
        await self._reward(session, character, quest, S13_REWARD_SOURCE, 8260, 220, ())
        await consolidate_character_level(session, character)

    async def _reward(self, session, character, quest, source_id, xp, crowns, materials):
        existing = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=character.id, source_id=source_id)
        session.add(event)
        await session.flush()
        character.xp += xp
        character.crowns += crowns
        session.add_all(
            [
                RewardComponent(reward_event_id=event.id, kind="xp", quantity=xp),
                RewardComponent(reward_event_id=event.id, kind="crowns", quantity=crowns),
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

    async def _record_p13_codex(self, session, character_id):
        for entry in (
            "codex.location.campinas_do_meridiano",
            "codex.location.posto_de_nareth",
            "codex.figure.nera_voss",
            ROTAS_CODEX,
        ):
            await self._ensure_codex(session, character_id, entry)
        await self._ensure_codex_fragment(
            session, character_id, ROTAS_CODEX, CODEX_INITIAL_FRAGMENT
        )

    async def _view(self, session, character, quest, world, requested_quest_id):
        quest_id = quest.quest_id if quest is not None else requested_quest_id
        if quest_id in MIDGAME_ACTIONS:
            return await self._midgame_view(session, character, quest, world, quest_id)
        location = world.location if world is not None else ""
        if quest is None:
            available = (
                await self._p13_eligible(session, character, world)
                if quest_id == P13_ID
                else await self._s13_eligible(session, character, world)
            )
            return NarethMissionView(
                character.id,
                quest_id,
                TITLES[quest_id],
                "offer" if available else "unavailable",
                None,
                None,
                0,
                {},
                location,
                character.level,
                available,
            )
        if quest.status == "completed":
            kind = "completed"
        elif quest_id == P13_ID:
            kind = {
                3: "line",
                4: "compare",
                5: "horizon_brazier",
                6: "follow_route",
                7: "arrive_posto",
                8: "posto_brazier",
                9: "speak_nera",
                10: "record_codex",
            }.get(quest.step, "active")
        else:
            if quest.step == 1:
                kind = "receive"
            elif quest.step in {2, 3, 4}:
                kind = "markers"
            elif quest.step == 5:
                kind = "compare"
            else:
                kind = "report"
        return NarethMissionView(
            character.id,
            quest_id,
            TITLES[quest_id],
            kind,
            quest.status,
            quest.step,
            quest.state_version,
            dict(quest.progress or {}),
            location,
            character.level,
        )

    async def _midgame_view(self, session, character, quest, world, requested_quest_id):
        quest_id = quest.quest_id if quest is not None else requested_quest_id
        location = world.location if world is not None else ""
        progress = dict(quest.progress or {}) if quest else {}
        if quest_id == S17_ID and character is not None:
            progress["submerged_entry_discovered"] = bool(
                await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == "dungeon.nareth.observatorio_afundado",
                    )
                )
            )
        activity = combat = encounter = None
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
                    if row is not None:
                        encounter, record = row
                        if activity.status == "active":
                            combat = decode(
                                record.snapshot, record.id,
                                activity.ruleset_version, activity.state_version,
                            )
        if quest is None:
            available = await self._midgame_eligible(session, character, world, quest_id)
            kind = "offer" if available else "unavailable"
            return NarethMissionView(
                character.id, quest_id, MISSION_TITLES[quest_id], kind, None, None, 0,
                {}, location, character.level, available,
            )
        if combat is not None:
            kind = "combat"
        elif quest.status == "completed":
            kind = "completed"
        elif quest_id in {P15_ID, P18_ID} and quest.step == 10:
            kind = "choice"
        else:
            kinds = {
                P14_ID: {1: "receive_map", 2: "travel_canais", 3: "examine_gate", 4: "follow_bed", 5: "combat_start", 6: "recover_plate", 7: "compare_plate", 8: "return_posto", 9: "deliver_plate"},
                S14_ID: {1: "receive_routes", 2: "travel_canais", 3: "examine_bridge", 4: "follow_low_route", 5: "mark_stable_route", 6: "find_access_signs", 7: "return_posto", 8: "report"},
                P15_ID: {1: "speak_talen", 2: "travel_campos", 3: "measure_short_distance", 4: "repeat_with_reference", 5: "review_historical_records", 6: "combat_start", 7: "examine_natural_plates", 8: "recover_marker", 9: "return_posto"},
                S15_ID: {1: "receive_last_point", 2: "follow_tracks", 3: "find_cargo", 4: "find_travelers", 5: "confirm_no_displacement", 6: "mark_return_route", 7: "return_posto", 8: "report"},
                P16_ID: {1: "receive_translation", 2: "travel_observatorio", 3: "discover_observatorio", 4: "examine_alignment", 5: "examine_arm", 6: "record_terms", 7: "combat_start", 8: "read_analog_panel", 9: "return_posto"},
                S16_ID: {1: "receive_checkpoints", 2: "visit_campos", 3: "visit_canais", 4: "reject_old_route", 5: "visit_observatorio", 6: "record_difference", 7: "return_posto", 8: "update_codex"},
                S17_ID: {1: "speak_talen", 2: "travel_observatorio", 3: "examine_references", 4: "locate_submerged_entry", 5: "recover_calibration_piece", 6: "return_posto", 7: "update_protocols"},
                P17_ID: {1: "gather_researchers", 2: "compare_records", 3: "record_custody", 4: "confirm_stability_monitoring", 5: "travel_observatorio", 6: "combat_start", 7: "open_chamber", 8: "travel_chamber", 9: "examine_incomplete_record", 10: "return_observatorio", 11: "prepare_arconte"},
                P18_ID: {1: "enter_chamber", 2: "examine_reference_lines", 3: "identify_archon", 4: "combat_start", 5: "defeat_archon", 6: "examine_chamber_after_victory", 7: "record_anchor_function", 8: "record_measurement_function", 9: "record_logistics_direction", 10: "choice"},
                S18_ID: {1: "read_cartography", 2: "visit_campinas", 3: "compare_old_markers", 4: "visit_canais", 5: "recover_route_plate", 6: "visit_campos", 7: "compare_travel_distances", 8: "visit_observatorio", 9: "follow_service_route", 10: "combat_start", 11: "inspect_broken_reference", 12: "return_posto", 13: "trace_modern_route", 14: "update_codex"},
            }
            kind = kinds[quest_id].get(quest.step, "active")
            if quest_id == P17_ID and quest.step == 8 and location == CAMARA:
                kind = "examine_incomplete_record"
        consumables = ((), (), 0)
        if activity is not None and combat is not None:
            consumables = await consumable_state(
                session, character, combat,
                MISSION_COMBAT[quest_id][3].category,
                actor_key=actor_key,
            )
        return NarethMissionView(
            character.id, quest_id, MISSION_TITLES[quest_id], kind, quest.status,
            quest.step, quest.state_version, progress, location, character.level,
            False, combat, activity.id if activity is not None else None,
            encounter.id if encounter is not None else None, actor_key, group_size,
            consumables[0], consumables[1], consumables[2],
        )

    @staticmethod
    def _valid_midgame(quest, version, step):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == CONTENT_VERSION_MID
            and quest.state_version == version
            and quest.step == step
        )

    async def _p13_eligible(self, session, character, world):
        return bool(
            character
            and world
            and character.level >= 21
            and world.region == REGION
            and world.location == CAMPINAS
            and await self._p12_complete(session, character.id)
        )

    async def _s13_eligible(self, session, character, world):
        return bool(
            character
            and world
            and character.level >= 22
            and world.region == REGION
            and world.location == POSTO
            and await self._p13_complete(session, character.id)
            and await self._foreground(session, character.id) is None
        )

    async def _eligible_group_at(self, session, character_id, quest_id):
        members = []
        for member_id in await campaign_roster_ids(session, character_id):
            member = await session.scalar(
                select(Character).where(Character.id == member_id).with_for_update()
            )
            world = await self._world(session, member_id)
            if (
                member is None
                or world is None
                or not await self._s13_eligible(session, member, world)
            ):
                continue
            existing = await self._quest(session, member_id, quest_id)
            if existing is None:
                members.append((member, world))
        return members

    async def _present(self, session, character_id, quest_id, step, location):
        return await present_campaign_members(
            session,
            character_ids=await campaign_roster_ids(session, character_id),
            quest_id=quest_id,
            content_version=(
                CONTENT_VERSION_MID if quest_id in MIDGAME_ACTIONS else CONTENT_VERSION
            ),
            step=step,
            region=REGION,
            location=location,
        )

    async def _locked_state(self, session, actor):
        actor_row = await self._character(session, actor)
        if actor_row is None:
            return None, ()
        _group_id, character_ids = await lock_campaign_roster(session, actor_row.id)
        character = await session.scalar(
            select(Character).where(Character.id == actor_row.id).with_for_update()
        )
        return character, character_ids

    async def _character(self, session, actor):
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _quest(self, session, character_id, quest_id):
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == quest_id)
            .with_for_update()
        )

    async def _world(self, session, character_id):
        return await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id).with_for_update()
        )

    async def _foreground(self, session, character_id):
        return await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        )

    async def _p12_complete(self, session, character_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P12",
                    Quest.status == "completed",
                )
            )
        )

    async def _p13_complete(self, session, character_id):
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P13_ID,
                    Quest.status == "completed",
                )
            )
        )

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

    async def _ensure_location(self, session, character_id, location_id):
        await self._ensure(session, LocationDiscovery, character_id, "location_id", location_id)

    async def _ensure_unlock(self, session, character_id, unlock_id):
        await self._ensure(session, Unlock, character_id, "unlock_id", unlock_id)

    async def _ensure(self, session, model, character_id, key, value):
        column = getattr(model, key)
        found = await session.scalar(
            select(model.id).where(model.character_id == character_id, column == value)
        )
        if found is None:
            session.add(model(character_id=character_id, **{key: value}))
            nareth_dungeon_unlock = (
                model is Unlock and isinstance(value, str) and value.startswith("dungeon.nareth.")
            )
            if model in {LocationDiscovery, Brazier} or nareth_dungeon_unlock:
                from asterion.application.nareth_feats import (
                    NARETH_BRAZIERS,
                    NARETH_LOCATIONS,
                    reconcile_nareth_feats_for_character,
                )

                nareth_source = (
                    value in NARETH_LOCATIONS
                    if model is LocationDiscovery
                    else value in NARETH_BRAZIERS
                    if model is Brazier
                    else nareth_dungeon_unlock
                )
                if nareth_source:
                    await reconcile_nareth_feats_for_character(session, character_id)

    async def _ensure_codex(self, session, character_id, entry_id):
        await self._ensure(session, CodexEntry, character_id, "entry_id", entry_id)

    async def _ensure_codex_fragment(self, session, character_id, entry_id, fragment_id):
        found = await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == fragment_id,
            )
        )
        if found is None:
            await self._ensure_codex(session, character_id, entry_id)
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
            )

    async def _credit(self, session, character_id, quest_id, objective_id, source_key, evidence):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=quest_id,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    @staticmethod
    def _valid(quest, version, *, step):
        return bool(
            quest
            and quest.status == "active"
            and quest.content_version == CONTENT_VERSION
            and quest.state_version == version
            and quest.step == step
        )
