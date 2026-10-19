"""Persistent campaign progression for the Altos Cinéreos opening mission."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
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
    ALTOS_CORACAO_LABEL,
    ALTOS_ESCARPA_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    CONFINS_CAMARA_REGENCIA_LABEL,
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_MARCHA_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
    RoadService,
)
from asterion.application.scripted_combat import (
    apply_action,
    consumable_state,
    current_combat,
    derive_consumable_selection,
    normalize_character_hp,
)
from asterion.domain.altos_colossus import configure_colossus_encounter
from asterion.domain.combat import Combat, active_player_key
from asterion.domain.confins_regent import ANCHOR_KEYS as P36_ANCHOR_KEYS
from asterion.domain.confins_regent import REGENT_ID as P36_BOSS_ID
from asterion.domain.confins_regent import configure_regent_encounter
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
    ALTOS_CARNEIRO_PESO,
    ALTOS_CINZA_BASALTO,
    ALTOS_COLOSSO_CINEREO,
    ALTOS_CORACAO_ACCESS_UNLOCK,
    ALTOS_CORACAO_LOCATION,
    ALTOS_COURO_ESCARPA,
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_ESCARPA_BRAZIER,
    ALTOS_ESCARPA_EXPLORE_UNLOCK,
    ALTOS_ESCARPA_HUNT_UNLOCK,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LIQUEN_PEDREIRA,
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
    ALTOS_SUPERVISOR_CARGA,
    ALTOS_VIGIA_CARGA,
    CONFINS_ANDARILHO_REPETIDO,
    CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
    CONFINS_CAMARA_REGENCIA_LOCATION,
    CONFINS_CAO_NEVOA,
    CONFINS_CASCA_REFLEXO,
    CONFINS_COURO_MARCHA,
    CONFINS_CUSTODIO_DESFASADO,
    CONFINS_ESTRADAS_ACCESS_UNLOCK,
    CONFINS_ESTRADAS_AUSENTES_LOCATION,
    CONFINS_ESTRADAS_EXPLORE_UNLOCK,
    CONFINS_ESTRADAS_HUNT_UNLOCK,
    CONFINS_FERRO_BALIZA,
    CONFINS_FRATURAS_ACCESS_UNLOCK,
    CONFINS_FRATURAS_EXPLORE_UNLOCK,
    CONFINS_FRATURAS_HUNT_UNLOCK,
    CONFINS_FRATURAS_LIMIAR_LOCATION,
    CONFINS_LOCATION_CATALOG,
    CONFINS_MARCHA_ACCESS_UNLOCK,
    CONFINS_MARCHA_EXPLORE_UNLOCK,
    CONFINS_MARCHA_HUNT_UNLOCK,
    CONFINS_MARCHA_LOCATION,
    CONFINS_MARCO_DUPLO_BRAZIER,
    CONFINS_MUSGO_LIMIAR,
    CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
    CONFINS_NO_CENTRAL_EXPLORE_UNLOCK,
    CONFINS_NO_CENTRAL_HUNT_UNLOCK,
    CONFINS_NO_CENTRAL_LOCATION,
    CONFINS_PO_REFERENCIA,
    CONFINS_REGION,
    CONFINS_TESTEMUNHA_BRAZIER,
    CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK,
    CONFINS_ULTIMO_REFUGIO_LOCATION,
    CONFINS_VIGIA_DESFASADO,
    RULESET,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
    creature_for,
    materialize_equipment,
)
from asterion.domain.weapon_metadata import weapon_definition
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    Brazier,
    CampaignJourney,
    CampaignJourneyMember,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    CharacterCosmetic,
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
S26_ID = "S26"
S26_MISSION_ID = "mission.altos.s26"
S26_TITLE = "Turno sem Fim"
S26_CONTENT_VERSION = "altos-1.0.1"
S26_CHECKPOINT = "s26.turno_sem_fim"
S26_REWARD_SOURCE = S26_MISSION_ID
S26_CODEX_ENTRY = "codex.altos.turno_sem_fim"
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
P29_ID = "P29"
P29_MISSION_ID = "mission.altos.p29"
P29_TITLE = "Antes da Convergência"
P29_CONTENT_VERSION = "altos-1.0.1"
P29_CHECKPOINT = "p29.antes_da_convergencia"
P29_CONTENT_ID = P29_MISSION_ID
P29_REWARD_SOURCE = P29_MISSION_ID
P29_CODEX_ENTRY = "codex.altos.convergencia_objetivo"
P29_NARRATIVE_UNLOCK = "narrative.altos.convergencia_objetivo_conhecido"
P29_ACHIEVEMENT = "achievement.altos.antes_convergencia"
P30_ID = "P30"
P30_MISSION_ID = "mission.altos.p30"
P30_TITLE = "O Colosso Cinéreo"
P30_CONTENT_VERSION = "altos-1.0.1"
P30_CHECKPOINT = "p30.o_colosso_cinereo"
P30_REWARD_SOURCE = P30_MISSION_ID
P30_CORE_REWARD_SOURCE = "mission.altos.p30.first_colossus_core"
P30_CORE_ID = "material.special.altos.core.colosso_cinereo"
P30_CODEX_ENTRY = "codex.altos.sabotagem_ancora_central"
P30_NARRATIVE_UNLOCK = "narrative.altos.sabotagem_ancora_confirmada"
P30_RECIPE_UNLOCK = "recipe.altos.colosso.continuidade"
P30_ACHIEVEMENT = "achievement.altos.colosso_silenciado"
S30_ID = "S30"
S30_MISSION_ID = "mission.altos.s30"
S30_TITLE = "A Ordem que Restou"
S30_CONTENT_VERSION = "altos-1.0.1"
S31_ID = "S31"
S31_MISSION_ID = "mission.confins.s31"
S31_TITLE = "Duas Vezes a Mesma Estrada"
S31_CONTENT_VERSION = "confins-1.0.0"
S31_CHECKPOINT = "s31.duas_vezes_a_mesma_estrada"
S32_ID = "S32"
S32_MISSION_ID = "mission.confins.s32"
S32_TITLE = "A Casa que Não Chegou"
S32_CONTENT_VERSION = "confins-1.0.0"
S32_CHECKPOINT = "s32.a_casa_que_nao_chegou"
ALTOS_REGION_ACHIEVEMENT = "achievement.altos.regiao"
P30_CONFINS_UNLOCK = "unlock.region.confins"
P31_ID = "P31"
P31_MISSION_ID = "mission.confins.p31"
P31_TITLE = "Onde o Véu Afina"
P31_CONTENT_VERSION = "confins-1.0.0"
P31_REWARD_SOURCE = P31_MISSION_ID
P31_REGION_CODEX = "codex.confins.regiao"
P31_CODEX_ENTRY = "codex.confins.duas_leituras_rota"
P31_NARRATIVE_UNLOCK = "narrative.confins.duas_leituras_confirmadas"
P31_ACHIEVEMENT = "achievement.confins.primeira_marcha"
P31_TITLE_COSMETIC = "cosmetic.title.confins.testemunha_rota"
P32_ID = "P32"
P32_MISSION_ID = "mission.confins.p32"
P32_TITLE = "A Fratura"
P32_CONTENT_VERSION = "confins-1.0.0"
P32_REWARD_SOURCE = P32_MISSION_ID
P32_CODEX_ENTRY = "codex.confins.fratura_definicao"
P32_NARRATIVE_UNLOCK = "narrative.confins.fratura_reconhecida"
P32_ACHIEVEMENT = "achievement.confins.fratura_observada"
P33_ID = "P33"
P33_MISSION_ID = "mission.confins.p33"
P33_TITLE = "O Avesso"
P33_CONTENT_VERSION = "confins-1.0.0"
P33_REWARD_SOURCE = P33_MISSION_ID
P33_CODEX_ENTRY = "codex.confins.avesso_estados"
P33_NARRATIVE_UNLOCK = "narrative.confins.avesso_nomeado"
P33_ACHIEVEMENT = "achievement.confins.avesso_nomeado"
P33_TITLE_COSMETIC = "cosmetic.title.confins.leitor_incoerencias"
P34_ID = "P34"
P34_MISSION_ID = "mission.confins.p34"
P34_TITLE = "A Âncora Central"
P34_CONTENT_VERSION = "confins-1.0.0"
P34_REWARD_SOURCE = P34_MISSION_ID
P34_CODEX_ENTRY = "codex.confins.ancora_central_coordenacao"
P34_NARRATIVE_UNLOCK = "narrative.confins.ancora_central_compreendida"
P34_ACHIEVEMENT = "achievement.confins.ancora_compreendida"
P35_ID = "P35"
P35_MISSION_ID = "mission.confins.p35"
P35_TITLE = "A Noite da Convergência"
P35_CONTENT_VERSION = "confins-1.0.0"
P35_REWARD_SOURCE = P35_MISSION_ID
P35_CODEX_RECONSTRUCTION = "codex.confins.convergencia_reconstrucao"
P35_CODEX_RUPTURE = "codex.confins.cadeia_ruptura_documentada"
P35_NARRATIVE_UNLOCK = "narrative.confins.noite_convergencia_reconstruida"
P35_ACHIEVEMENT = "achievement.confins.cadeia_ruptura"
P35_FRAME_COSMETIC = "cosmetic.frame.confins.arquivo_duplo"
P35_DOCUMENT_CHAINS = (
    "custodia_ancoras",
    "regencia_continuidade",
    "oposicao_desvelados",
)
P35_TECHNICAL_SEQUENCE = (
    "pre_civil_deterioration",
    "anchors_stabilized",
    "growing_dependency_inequality",
    "coupled_convergence",
)
P36_ID = "P36"
P36_MISSION_ID = "mission.confins.p36"
P36_TITLE = "O Regente Fraturado"
P36_CONTENT_VERSION = "confins-1.0.0"
P36_CHECKPOINT = "p36.o_regente_fraturado"
P36_REWARD_SOURCE = P36_MISSION_ID
P36_CORE_SOURCE = "boss.confins.regente_fraturado.first_victory"
P36_CORE_ID = "material.special.confins.core.regente_fraturado"
P36_NARRATIVE_UNLOCK = "narrative.confins.protocolo_impossivel_encerrado"
P36_CAMPAIGN_UNLOCK = "unlock.campaign.first_journey_complete"
P36_RECIPE_UNLOCK = "recipe.confins.regente.eco_encerramento"
P36_CODEX_NATURE = "codex.confins.regente_natureza"
P36_CODEX_PROTOCOL = "codex.confins.protocolo_encerrado"
P36_FIRST_VICTORY_ACHIEVEMENT = "achievement.confins.regente_primeira"
P36_FIRST_VICTORY_FRAME = "cosmetic.frame.confins.ultima_referencia"
P36_REGION_ACHIEVEMENT = "achievement.confins.regiao"
P36_REGION_APPEARANCE = "cosmetic.appearance.confins.viajante_veu"
P36_STAGE_ONE_EVIDENCE = (
    "institutional_record",
    "local_matter",
    "incompatible_states",
)
P36_STAGE_TWO_EVIDENCE = (
    "final_evidence_a",
    "final_evidence_b",
    "final_evidence_c",
)
P36_REWARD_OPTIONS = {
    "guarda_ultimo_protocolo": (
        "equipment.confins.campaign.p36.guarda_ultimo_protocolo",
        "Guarda do Último Protocolo",
        "Secundária",
    ),
    "selo_referencia_presente": (
        "equipment.confins.campaign.p36.selo_referencia_presente",
        "Selo da Referência Presente",
        "Acessório",
    ),
    "relicario_ordem_findada": (
        "equipment.confins.campaign.p36.relicario_ordem_findada",
        "Relicário da Ordem Findada",
        "Artefato",
    ),
}
ALTOS_PRIMARY_LOCATIONS = (
    ALTOS_ESCARPA_LOCATION,
    ALTOS_ABRIGO_LOCATION,
    ALTOS_PONTES_LOCATION,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_BASTILHA_LOCATION,
    ALTOS_CORACAO_LOCATION,
)
P30_LOAD_PATHS = ("contraforte", "cabo", "escora")
P29_PRIORITY_RECORDS = (
    "priority_record_1",
    "priority_record_2",
    "priority_record_3",
)
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
P30_REWARD_OPTIONS = {
    "guarda_contraforte_final": (
        "equipment.altos.campaign.p30.guarda_contraforte_final",
        "Guarda do Contraforte Final",
        "Secundária",
    ),
    "selo_rede_sustentada": (
        "equipment.altos.campaign.p30.selo_rede_sustentada",
        "Selo da Rede Sustentada",
        "Acessório",
    ),
    "relicario_ordem_interrompida": (
        "equipment.altos.campaign.p30.relicario_ordem_interrompida",
        "Relicário da Ordem Interrompida",
        "Artefato",
    ),
}
P33_REWARD_OPTIONS = {
    "capuz_dupla_leitura": (
        "equipment.confins.campaign.p33.capuz_dupla_leitura",
        "Capuz da Dupla Leitura",
        "Cabeça",
    ),
    "selo_marco_valido": (
        "equipment.confins.campaign.p33.selo_marco_valido",
        "Selo do Marco Válido",
        "Acessório",
    ),
    "relicario_registro_incompleto": (
        "equipment.confins.campaign.p33.relicario_registro_incompleto",
        "Relicário do Registro Incompleto",
        "Artefato",
    ),
}
P25_COMBAT = {
    P25_ID: (P25_CONTENT_ID, P25_CHECKPOINT, ALTOS_ESCARPA_LABEL, ALTOS_LOBO_ESCARPA, 41, "common"),
    S26_ID: (
        S26_MISSION_ID,
        S26_CHECKPOINT,
        (ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL),
        ALTOS_CARNEIRO_PESO,
        44,
        "common",
    ),
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
    P29_ID: (
        P29_CONTENT_ID,
        P29_CHECKPOINT,
        ALTOS_BASTILHA_LABEL,
        ALTOS_SUPERVISOR_CARGA,
        49,
        "elite",
    ),
    P30_ID: (
        P30_MISSION_ID,
        P30_CHECKPOINT,
        ALTOS_CORACAO_LABEL,
        ALTOS_COLOSSO_CINEREO,
        50,
        "boss",
    ),
    S30_ID: (
        S30_MISSION_ID,
        "s30.a_ordem_que_restou",
        ALTOS_BASTILHA_LABEL,
        "boss.altos.s30.custodio_ultimo_turno",
        50,
        "boss",
    ),
    S31_ID: (
        S31_MISSION_ID,
        S31_CHECKPOINT,
        CONFINS_MARCHA_LABEL,
        "creature.confins.gralha_duas_sombras",
        52,
        "common",
    ),
    S32_ID: (
        S32_MISSION_ID,
        S32_CHECKPOINT,
        CONFINS_ESTRADAS_AUSENTES_LABEL,
        "creature.confins.aranha_limiar",
        54,
        "common",
    ),
    P31_ID: (
        P31_MISSION_ID,
        "p31.onde_o_veu_afina",
        CONFINS_MARCHA_LABEL,
        CONFINS_CAO_NEVOA,
        51,
        "common",
    ),
    P32_ID: (
        P32_MISSION_ID,
        "p32.a_fratura",
        CONFINS_ESTRADAS_AUSENTES_LABEL,
        CONFINS_ANDARILHO_REPETIDO,
        53,
        "uncommon",
    ),
    P33_ID: (
        P33_MISSION_ID,
        "p33.o_avesso",
        CONFINS_FRATURAS_LIMIAR_LABEL,
        CONFINS_CASCA_REFLEXO,
        55,
        "uncommon",
    ),
    P34_ID: (
        P34_MISSION_ID,
        "p34.a_ancora_central",
        CONFINS_NO_CENTRAL_LABEL,
        CONFINS_CUSTODIO_DESFASADO,
        57,
        "elite",
    ),
    P35_ID: (
        P35_MISSION_ID,
        "p35.a_noite_da_convergencia",
        CONFINS_NO_CENTRAL_LABEL,
        CONFINS_VIGIA_DESFASADO,
        59,
        "uncommon",
    ),
    P36_ID: (
        P36_MISSION_ID,
        P36_CHECKPOINT,
        CONFINS_CAMARA_REGENCIA_LABEL,
        P36_BOSS_ID,
        60,
        "boss",
    ),
}


def _scripted_combat_step(quest_id: str) -> int:
    if quest_id in {S31_ID, S32_ID}:
        return 4
    if quest_id == S30_ID:
        return 5
    if quest_id == P33_ID:
        return 3
    if quest_id == P34_ID:
        return 3
    if quest_id == P35_ID:
        return 3
    if quest_id == P36_ID:
        return 3
    if quest_id in {P31_ID, P32_ID}:
        return 4
    return 4 if quest_id in {P28_ID, P29_ID, P30_ID} else 3


def _combat_locations(profile) -> tuple[str, ...]:
    location = profile[2]
    return (location,) if isinstance(location, str) else tuple(location)


def _content_version(quest_id: str) -> str:
    return {
        S26_ID: S26_CONTENT_VERSION,
        P26_ID: P26_CONTENT_VERSION,
        P27_ID: P27_CONTENT_VERSION,
        P28_ID: P28_CONTENT_VERSION,
        P29_ID: P29_CONTENT_VERSION,
        P30_ID: P30_CONTENT_VERSION,
        S30_ID: S30_CONTENT_VERSION,
        S31_ID: S31_CONTENT_VERSION,
        S32_ID: S32_CONTENT_VERSION,
        P31_ID: P31_CONTENT_VERSION,
        P32_ID: P32_CONTENT_VERSION,
        P33_ID: P33_CONTENT_VERSION,
        P34_ID: P34_CONTENT_VERSION,
        P35_ID: P35_CONTENT_VERSION,
        P36_ID: P36_CONTENT_VERSION,
    }.get(quest_id, P25_CONTENT_VERSION)


def _mission_region(quest_id: str) -> str:
    return (
        CONFINS_REGION
        if quest_id in {S31_ID, S32_ID, P31_ID, P32_ID, P33_ID, P34_ID, P35_ID, P36_ID}
        else ALTOS_REGION
    )


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
            if character is None:
                return
            await self._ensure_p30_quest(session, character)
            await self._reconcile_altos_region_achievement(session, character)
            if (
                await self._quest_completed(session, character.id, P30_ID)
                and character.level >= 51
            ):
                await self._ensure(
                    session,
                    Unlock,
                    character_id=character.id,
                    unlock_id=P30_CONFINS_UNLOCK,
                )
            if world is not None and world.region == CONFINS_REGION:
                if world.location == CONFINS_MARCHA_LABEL:
                    quest = await self._ensure_p31_quest(session, character)
                    if (
                        quest is not None
                        and quest.status == "active"
                        and quest.content_version == P31_CONTENT_VERSION
                        and quest.step == 1
                    ):
                        await self._enter_confins_marcha(session, character, quest)
                    return
                if world.location == CONFINS_ULTIMO_REFUGIO_LABEL:
                    await self._enter_confins_refuge(session, character_ids)
                if world.location == CONFINS_ESTRADAS_AUSENTES_LABEL:
                    members = await self._present_p32(
                        session, character_ids, 2, CONFINS_ESTRADAS_AUSENTES_LABEL
                    )
                    for member in members:
                        if (
                            member.character.level < 53
                            or not await self._quest_completed(
                                session, member.character.id, P31_ID
                            )
                            or not await session.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == member.character.id,
                                    Unlock.unlock_id == CONFINS_ESTRADAS_ACCESS_UNLOCK,
                                )
                            )
                        ):
                            continue
                        await self._ensure(
                            session,
                            LocationDiscovery,
                            character_id=member.character.id,
                            location_id=CONFINS_ESTRADAS_AUSENTES_LOCATION,
                        )
                        progress = dict(member.quest.progress or {})
                        progress["completed_steps"] = sorted(
                            set(progress.get("completed_steps", ())) | {2}
                        )
                        progress["estradas_arrival_recorded"] = True
                        member.quest.progress = progress
                        member.quest.step = 3
                        member.quest.state_version += 1
                        await self._credit_p32(
                            session,
                            member.character.id,
                            "p32.arrived_estradas",
                            f"p32.arrived_estradas:{member.character.id}",
                            {"location_id": CONFINS_ESTRADAS_AUSENTES_LOCATION},
                        )
                if world.location == CONFINS_FRATURAS_LIMIAR_LABEL:
                    members = await self._present_p33(
                        session, character_ids, 1, CONFINS_FRATURAS_LIMIAR_LABEL
                    )
                    for member in members:
                        if (
                            member.character.level < 55
                            or not await self._quest_completed(
                                session, member.character.id, P32_ID
                            )
                            or not await session.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == member.character.id,
                                    Unlock.unlock_id == CONFINS_FRATURAS_ACCESS_UNLOCK,
                                )
                            )
                        ):
                            continue
                        await self._ensure(
                            session,
                            LocationDiscovery,
                            character_id=member.character.id,
                            location_id=CONFINS_FRATURAS_LIMIAR_LOCATION,
                        )
                        progress = dict(member.quest.progress or {})
                        progress.update(
                            completed_steps=sorted(
                                set(progress.get("completed_steps", ())) | {1}
                            ),
                            fraturas_arrival_recorded=True,
                            discordant_reference_marks=("physical_mark_a", "physical_mark_b"),
                        )
                        member.quest.progress = progress
                        member.quest.step = 2
                        member.quest.state_version += 1
                        await self._credit_p33(
                            session,
                            member.character.id,
                            "p33.fraturas_arrived",
                            f"p33.fraturas_arrived:{member.character.id}",
                            {
                                "location_id": CONFINS_FRATURAS_LIMIAR_LOCATION,
                                "observed_marks": ("physical_mark_a", "physical_mark_b"),
                            },
                        )
                if world.location == CONFINS_NO_CENTRAL_LABEL:
                    members = await self._present_p34(
                        session, character_ids, 2, CONFINS_NO_CENTRAL_LABEL
                    )
                    for member in members:
                        if (
                            member.character.level < 57
                            or not await self._quest_completed(
                                session, member.character.id, P33_ID
                            )
                            or not await session.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == member.character.id,
                                    Unlock.unlock_id == CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
                                )
                            )
                        ):
                            continue
                        await self._ensure(
                            session,
                            LocationDiscovery,
                            character_id=member.character.id,
                            location_id=CONFINS_NO_CENTRAL_LOCATION,
                        )
                        progress = dict(member.quest.progress or {})
                        if progress.get("no_arrival_recorded"):
                            continue
                        progress["no_arrival_recorded"] = True
                        member.quest.progress = progress
                        member.quest.state_version += 1
                        await self._credit_p34(
                            session,
                            member.character.id,
                            "p34.no_arrived",
                            f"p34.no_arrived:{member.character.id}",
                            {"location_id": CONFINS_NO_CENTRAL_LOCATION},
                        )
                if world.location == CONFINS_CAMARA_REGENCIA_LABEL and await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                    )
                ):
                    await self._ensure(
                        session,
                        LocationDiscovery,
                        character_id=character.id,
                        location_id=CONFINS_CAMARA_REGENCIA_LOCATION,
                    )
                    p36 = await self._ensure_p36_quest(session, character, world)
                    if p36 is not None and p36.status == "active" and p36.step == 1:
                        progress = dict(p36.progress or {})
                        if not progress.get("chamber_entered"):
                            progress["chamber_entered"] = True
                            p36.progress = progress
                            p36.state_version += 1
                            await self._credit_p36(
                                session,
                                character.id,
                                "p36.chamber_entered",
                                f"p36.chamber_entered:{character.id}",
                                {"location_id": CONFINS_CAMARA_REGENCIA_LOCATION},
                            )
                await self._reconcile_confins_region_achievement(session, character)
                return
            if world is None or world.region != ALTOS_REGION:
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
            if world.location == ALTOS_CORACAO_LABEL:
                for member_character in (
                    await session.scalars(
                        select(Character)
                        .where(Character.id.in_(character_ids))
                        .order_by(Character.id)
                        .with_for_update()
                    )
                ).all():
                    await self._ensure_p30_quest(session, member_character)
                await self._enter_p30(session, character_ids)
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

    async def _enter_p30(self, session, character_ids) -> None:
        members = await self._present_p30(
            session, character_ids, 1, ALTOS_CORACAO_LABEL
        )
        for member in members:
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=ALTOS_CORACAO_LOCATION,
            )
            member.quest.step = 2
            member.quest.state_version += 1
            member.quest.progress = {
                **(member.quest.progress or {}),
                "entered_coracao": True,
                "completed_steps": sorted(
                    set((member.quest.progress or {}).get("completed_steps", ())) | {1}
                ),
            }
            await self._credit_p30(
                session,
                member.character.id,
                "p30.entered_coracao",
                f"p30.entered_coracao:{member.character.id}",
                {"location": ALTOS_CORACAO_LOCATION},
            )

    async def _ensure_p30_quest(self, session, character) -> Quest | None:
        p29 = await self._quest(session, character.id, P29_ID)
        if (
            p29 is None
            or p29.status != "completed"
            or p29.content_version != P29_CONTENT_VERSION
            or character.level < 50
        ):
            return await self._quest(session, character.id, P30_ID)
        quest = await self._quest(session, character.id, P30_ID)
        if quest is not None:
            return quest
        quest = Quest(
            character_id=character.id,
            quest_id=P30_ID,
            title=P30_TITLE,
            status="active",
            step=1,
            content_version=P30_CONTENT_VERSION,
            state_version=0,
            progress={
                "prepared_with": ("Rava Kern", "Sel Ardan"),
                "completed_steps": [],
            },
        )
        session.add(quest)
        await session.flush()
        await self._credit_p30(
            session,
            character.id,
            "p30.activated",
            f"p30.activated:{character.id}",
            {"givers": ("Rava Kern", "Sel Ardan"), "mission_id": P30_MISSION_ID},
        )
        return quest

    async def _ensure_p31_quest(self, session, character) -> Quest | None:
        p30 = await self._quest(session, character.id, P30_ID)
        if (
            p30 is None
            or p30.status != "completed"
            or p30.content_version != P30_CONTENT_VERSION
            or character.level < 51
        ):
            return await self._quest(session, character.id, P31_ID)
        quest = await self._quest(session, character.id, P31_ID)
        if quest is not None:
            return quest
        quest = Quest(
            character_id=character.id,
            quest_id=P31_ID,
            title=P31_TITLE,
            status="active",
            step=1,
            content_version=P31_CONTENT_VERSION,
            state_version=0,
            progress={"completed_steps": [], "started_at_location": CONFINS_MARCHA_LOCATION},
        )
        session.add(quest)
        await session.flush()
        await self._credit_p31(
            session,
            character.id,
            "p31.activated_on_entry",
            f"p31.activated_on_entry:{character.id}",
            {"mission_id": P31_MISSION_ID, "location_id": CONFINS_MARCHA_LOCATION},
        )
        return quest

    async def _enter_confins_marcha(self, session, character, quest) -> None:
        if (
            quest.status != "active"
            or quest.content_version != P31_CONTENT_VERSION
            or quest.step != 1
            or character.level < 51
            or not await self._quest_completed(session, character.id, P30_ID)
        ):
            return
        for unlock_id in (P30_CONFINS_UNLOCK, CONFINS_MARCHA_ACCESS_UNLOCK):
            await self._ensure(session, Unlock, character_id=character.id, unlock_id=unlock_id)
        await self._ensure(
            session,
            LocationDiscovery,
            character_id=character.id,
            location_id=CONFINS_MARCHA_LOCATION,
        )
        await self._ensure(
            session,
            CodexEntry,
            character_id=character.id,
            entry_id=P31_REGION_CODEX,
        )
        progress = dict(quest.progress or {})
        progress["completed_steps"] = sorted(
            set(progress.get("completed_steps", ())) | {1}
        )
        progress["arrival_recorded"] = True
        quest.progress = progress
        quest.step = 2
        quest.state_version += 1
        await self._credit_p31(
            session,
            character.id,
            "p31.crossed_confins_frontier",
            f"p31.crossed_confins_frontier:{character.id}",
            {"location_id": CONFINS_MARCHA_LOCATION, "level": character.level},
        )

    async def _enter_confins_refuge(self, session, character_ids) -> None:
        members = await self._present_p31(
            session, character_ids, 5, CONFINS_ULTIMO_REFUGIO_LABEL
        )
        for member in members:
            await self._ensure(
                session,
                Unlock,
                character_id=member.character.id,
                unlock_id=CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK,
            )
            await self._ensure(
                session,
                LocationDiscovery,
                character_id=member.character.id,
                location_id=CONFINS_ULTIMO_REFUGIO_LOCATION,
            )
            progress = dict(member.quest.progress or {})
            progress["completed_steps"] = sorted(
                set(progress.get("completed_steps", ())) | {5}
            )
            progress["entered_ultimo_refugio"] = True
            member.quest.progress = progress
            member.quest.step = 6
            member.quest.state_version += 1
            await self._credit_p31(
                session,
                member.character.id,
                "p31.entered_ultimo_refugio",
                f"p31.entered_ultimo_refugio:{member.character.id}",
                {"location_id": CONFINS_ULTIMO_REFUGIO_LOCATION},
            )

    async def start_p30(self, actor: int, version: int = 0) -> AltosMissionView | None:
        """Activate the automatically available P30 quest after its level gate."""
        async with self.sessions.begin() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            await lock_campaign_roster(session, character.id)
            character = await session.scalar(
                select(Character).where(Character.id == character.id).with_for_update()
            )
            if character is None:
                return None
            quest = await self._ensure_p30_quest(session, character)
            world = await self._world(session, character.id)
            p29 = await self._quest(session, character.id, P29_ID, lock=False)
            if quest is None:
                status = (
                    "available"
                    if p29 is not None
                    and p29.status == "completed"
                    and character.level >= 50
                    else "suspended"
                )
                return self._p30_offer_view(character, world, status)
            if quest.state_version != version and version != 0:
                return await self._view(session, character, quest, world)
            return await self._view(session, character, quest, world)

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
        s30_active = False
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is not None:
                s30_active = bool(await session.scalar(
                    select(GameActivity.id).where(
                        GameActivity.character_id == character.id,
                        GameActivity.content_id == S30_MISSION_ID,
                        GameActivity.status == "active",
                    )
                ))
        if s30_active:
            return await self.resume(actor, S30_ID)
        await self.on_location(actor)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id, lock=False)
            p36 = await self._quest(session, character.id, P36_ID, lock=False)
            if p36 is not None:
                if p36.content_version != P36_CONTENT_VERSION:
                    return None
                return self._p36_view(character, p36, world)
            p35 = await self._quest(session, character.id, P35_ID, lock=False)
            if p35 is not None:
                if p35.content_version != P35_CONTENT_VERSION:
                    return None
                if (
                    p35.status == "completed"
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_CAMARA_REGENCIA_LABEL
                ):
                    status = "available" if character.level >= 60 else "suspended"
                    return self._p36_offer_view(character, world, status)
                return await self._view(session, character, p35, world)
            p34 = await self._quest(session, character.id, P34_ID, lock=False)
            if p34 is not None:
                if p34.content_version != P34_CONTENT_VERSION:
                    return None
                if (
                    p34.status == "completed"
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_NO_CENTRAL_LABEL
                ):
                    status = "available" if character.level >= 59 else "suspended"
                    return self._p35_offer_view(character, world, status)
                return await self._view(session, character, p34, world)
            p33 = await self._quest(session, character.id, P33_ID, lock=False)
            if p33 is not None:
                if p33.content_version != P33_CONTENT_VERSION:
                    return None
                if (
                    p33.status == "completed"
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
                ):
                    status = "available" if character.level >= 57 else "suspended"
                    return self._p34_offer_view(character, world, status)
                return await self._view(session, character, p33, world)
            p32 = await self._quest(session, character.id, P32_ID, lock=False)
            if p32 is not None:
                if p32.content_version != P32_CONTENT_VERSION:
                    return None
                if (
                    p32.status == "completed"
                    and world is not None
                    and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
                ):
                    status = "available" if character.level >= 55 else "suspended"
                    return self._p33_offer_view(character, world, status)
                return await self._view(session, character, p32, world)
            p31 = await self._quest(session, character.id, P31_ID, lock=False)
            if p31 is not None:
                if p31.status == "completed":
                    if world is not None and world.location == CONFINS_ULTIMO_REFUGIO_LABEL:
                        status = "available" if character.level >= 53 else "suspended"
                        return self._p32_offer_view(character, world, status)
                    return None
                return await self._view(session, character, p31, world)
            p30 = await self._quest(session, character.id, P30_ID, lock=False)
            if p30 is not None:
                return await self._view(session, character, p30, world)
            p29 = await self._quest(session, character.id, P29_ID, lock=False)
            if p29 is not None:
                if p29.status == "completed":
                    status = "available" if character.level >= 50 else "suspended"
                    return self._p30_offer_view(character, world, status)
                return await self._view(session, character, p29, world)
            p28 = await self._quest(session, character.id, P28_ID, lock=False)
            if p28 is not None:
                if (
                    p28.status == "completed"
                    and world is not None
                    and world.location == ALTOS_BASTILHA_LABEL
                ):
                    status = "available" if character.level >= 49 else "suspended"
                    return self._p29_offer_view(character, world, status)
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
                p36 = await self._quest(session, character.id, P36_ID, lock=False)
                p35 = await self._quest(session, character.id, P35_ID, lock=False)
                p34 = await self._quest(session, character.id, P34_ID, lock=False)
                p33 = await self._quest(session, character.id, P33_ID, lock=False)
                p32 = await self._quest(session, character.id, P32_ID, lock=False)
                p31 = await self._quest(session, character.id, P31_ID, lock=False)
                p30 = await self._quest(session, character.id, P30_ID, lock=False)
                p29 = await self._quest(session, character.id, P29_ID, lock=False)
                p28 = await self._quest(session, character.id, P28_ID, lock=False)
                p27 = await self._quest(session, character.id, P27_ID, lock=False)
                p26 = await self._quest(session, character.id, P26_ID, lock=False)
                quest_id = (
                    P36_ID if p36 is not None
                    else P35_ID if p35 is not None
                    else P34_ID if p34 is not None
                    else P33_ID if p33 is not None
                    else P32_ID if p32 is not None
                    else P31_ID if p31 is not None
                    else P30_ID if p30 is not None
                    else P29_ID if p29 is not None and p29.status != "completed"
                    else P30_ID if p29 is not None and p29.status == "completed"
                    else P28_ID if p28 is not None
                    else P27_ID if p27 is not None and p27.status == "active"
                    else P25_ID
                )
                if p26 is not None and p26.status == "active" and p27 is None:
                    return self._p26_view(
                        character, p26, await self._world(session, character.id, lock=False)
                    )
            quest = await self._quest(session, character.id, quest_id, lock=False)
            if quest is None and quest_id == P36_ID:
                p35 = await self._quest(session, character.id, P35_ID, lock=False)
                world = await self._world(session, character.id, lock=False)
                if (
                    p35 is not None
                    and p35.status == "completed"
                    and p35.content_version == P35_CONTENT_VERSION
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_CAMARA_REGENCIA_LABEL
                ):
                    status = "available" if character.level >= 60 else "suspended"
                    return self._p36_offer_view(character, world, status)
            if quest is None and quest_id == P35_ID:
                p34 = await self._quest(session, character.id, P34_ID, lock=False)
                world = await self._world(session, character.id, lock=False)
                if (
                    p34 is not None
                    and p34.status == "completed"
                    and p34.content_version == P34_CONTENT_VERSION
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_NO_CENTRAL_LABEL
                ):
                    status = "available" if character.level >= 59 else "suspended"
                    return self._p35_offer_view(character, world, status)
            if quest is None and quest_id == P34_ID:
                p33 = await self._quest(session, character.id, P33_ID, lock=False)
                world = await self._world(session, character.id, lock=False)
                if (
                    p33 is not None
                    and p33.status == "completed"
                    and p33.content_version == P33_CONTENT_VERSION
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
                ):
                    status = "available" if character.level >= 57 else "suspended"
                    return self._p34_offer_view(character, world, status)
            if quest is None and quest_id == P33_ID:
                p32 = await self._quest(session, character.id, P32_ID, lock=False)
                world = await self._world(session, character.id, lock=False)
                if (
                    p32 is not None
                    and p32.status == "completed"
                    and p32.content_version == P32_CONTENT_VERSION
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
                ):
                    status = "available" if character.level >= 55 else "suspended"
                    return self._p33_offer_view(character, world, status)
            if quest is None and quest_id == P32_ID:
                p31 = await self._quest(session, character.id, P31_ID, lock=False)
                world = await self._world(session, character.id, lock=False)
                if (
                    p31 is not None
                    and p31.status == "completed"
                    and p31.content_version == P31_CONTENT_VERSION
                    and world is not None
                    and world.region == CONFINS_REGION
                    and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
                ):
                    status = "available" if character.level >= 53 else "suspended"
                    return self._p32_offer_view(character, world, status)
            if quest is None and quest_id == P30_ID:
                p29 = await self._quest(session, character.id, P29_ID, lock=False)
                if p29 is not None and p29.status == "completed":
                    status = "available" if character.level >= 50 else "suspended"
                    return self._p30_offer_view(
                        character,
                        await self._world(session, character.id, lock=False),
                        status,
                    )
            if quest is None or quest.content_version != P25_CONTENT_VERSION:
                if quest is None or quest.content_version not in {
                    P25_CONTENT_VERSION,
                    P30_CONTENT_VERSION,
                    P31_CONTENT_VERSION,
                    P32_CONTENT_VERSION,
                    P33_CONTENT_VERSION,
                    P34_CONTENT_VERSION,
                    P35_CONTENT_VERSION,
                    P36_CONTENT_VERSION,
                    S30_CONTENT_VERSION,
                }:
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
                                    ALTOS_CORACAO_LOCATION,
                                    CONFINS_MARCHA_LOCATION,
                                    CONFINS_ULTIMO_REFUGIO_LOCATION,
                                    CONFINS_ESTRADAS_AUSENTES_LOCATION,
                                    CONFINS_FRATURAS_LIMIAR_LOCATION,
                                    CONFINS_NO_CENTRAL_LOCATION,
                                    CONFINS_CAMARA_REGENCIA_LOCATION,
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
                    (ALTOS_CORACAO_LOCATION, ALTOS_CORACAO_LABEL),
                    (CONFINS_MARCHA_LOCATION, CONFINS_MARCHA_LABEL),
                    (CONFINS_ULTIMO_REFUGIO_LOCATION, CONFINS_ULTIMO_REFUGIO_LABEL),
                    (CONFINS_ESTRADAS_AUSENTES_LOCATION, CONFINS_ESTRADAS_AUSENTES_LABEL),
                    (CONFINS_FRATURAS_LIMIAR_LOCATION, CONFINS_FRATURAS_LIMIAR_LABEL),
                    (CONFINS_NO_CENTRAL_LOCATION, CONFINS_NO_CENTRAL_LABEL),
                    (CONFINS_CAMARA_REGENCIA_LOCATION, CONFINS_CAMARA_REGENCIA_LABEL),
                )
                if location_id in found
            }

    async def start_p32(self, actor: int, version: int = 0) -> AltosMissionView | None:
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
            existing = await self._quest(session, character.id, P32_ID)
            if existing is not None:
                if existing.content_version != P32_CONTENT_VERSION:
                    return None
                return self._p32_view(character, existing, world)
            p31 = await self._quest(session, character.id, P31_ID)
            if (
                p31 is None
                or p31.status != "completed"
                or p31.content_version != P31_CONTENT_VERSION
                or world.region != CONFINS_REGION
                or world.location != CONFINS_ULTIMO_REFUGIO_LABEL
            ):
                return None
            if character.level < 53:
                return self._p32_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p32_offer_view(character, world, "available")
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=CONFINS_ESTRADAS_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P32_ID,
                title=P32_TITLE,
                status="active",
                step=1,
                content_version=P32_CONTENT_VERSION,
                state_version=1,
                progress={"completed_steps": [], "route_trace_ids": []},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p32(
                session,
                character.id,
                "p32.activated",
                f"p32.activated:{character.id}",
                {
                    "mission_id": P32_MISSION_ID,
                    "giver_id": "npc.confins.sera_nol",
                    "location_unlock": CONFINS_ESTRADAS_ACCESS_UNLOCK,
                },
            )
            return self._p32_view(character, quest, world)

    async def start_p33(self, actor: int, version: int = 0) -> AltosMissionView | None:
        """Activate P33 after P32, granting only the individual route right."""
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
            existing = await self._quest(session, character.id, P33_ID)
            if existing is not None:
                if existing.content_version != P33_CONTENT_VERSION:
                    return None
                return self._p33_view(character, existing, world)
            p32 = await self._quest(session, character.id, P32_ID)
            if (
                p32 is None
                or p32.status != "completed"
                or p32.content_version != P32_CONTENT_VERSION
                or world.region != CONFINS_REGION
                or world.location != CONFINS_ESTRADAS_AUSENTES_LABEL
            ):
                return None
            if character.level < 55:
                return self._p33_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p33_offer_view(character, world, "available")
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=CONFINS_FRATURAS_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P33_ID,
                title=P33_TITLE,
                status="active",
                step=1,
                content_version=P33_CONTENT_VERSION,
                state_version=1,
                progress={"completed_steps": [], "physical_evidence_ids": []},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p33(
                session,
                character.id,
                "p33.activated",
                f"p33.activated:{character.id}",
                {
                    "mission_id": P33_MISSION_ID,
                    "givers": ("npc.confins.roven_pell", "npc.confins.talen_nyr"),
                    "location_unlock": CONFINS_FRATURAS_ACCESS_UNLOCK,
                },
            )
            return self._p33_view(character, quest, world)

    async def start_p34(self, actor: int, version: int = 0) -> AltosMissionView | None:
        """Activate P34 after P33 and grant only the individual Nó route right."""
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
            existing = await self._quest(session, character.id, P34_ID)
            if existing is not None:
                if existing.content_version != P34_CONTENT_VERSION:
                    return None
                return self._p34_view(character, existing, world)
            p33 = await self._quest(session, character.id, P33_ID)
            if (
                p33 is None
                or p33.status != "completed"
                or p33.content_version != P33_CONTENT_VERSION
                or world.region != CONFINS_REGION
                or world.location != CONFINS_FRATURAS_LIMIAR_LABEL
            ):
                return None
            if character.level < 57:
                return self._p34_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p34_offer_view(character, world, "available")

            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
            )
            quest = Quest(
                character_id=character.id,
                quest_id=P34_ID,
                title=P34_TITLE,
                status="active",
                step=2,
                content_version=P34_CONTENT_VERSION,
                state_version=1,
                progress={
                    "completed_steps": [1],
                    "records_received": True,
                    "physical_point_evidence_ids": [],
                },
            )
            session.add(quest)
            await session.flush()
            await self._credit_p34(
                session,
                character.id,
                "p34.records_received",
                f"p34.records_received:{character.id}",
                {
                    "mission_id": P34_MISSION_ID,
                    "giver_ids": ("npc.confins.eris_val", "npc.confins.sera_nol"),
                    "records": 2,
                    "complete_records": False,
                    "location_unlock": CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
                },
            )
            return self._p34_view(character, quest, world)

    async def start_p35(self, actor: int, version: int = 0) -> AltosMissionView | None:
        """Start P35 only after P34 and the individual level gate are met."""
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
            existing = await self._quest(session, character.id, P35_ID)
            if existing is not None:
                if existing.content_version != P35_CONTENT_VERSION:
                    return None
                return self._p35_view(character, existing, world)
            p34 = await self._quest(session, character.id, P34_ID, lock=False)
            if (
                p34 is None
                or p34.status != "completed"
                or p34.content_version != P34_CONTENT_VERSION
                or world.region != CONFINS_REGION
                or world.location != CONFINS_NO_CENTRAL_LABEL
            ):
                return None
            if character.level < 59:
                return self._p35_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p35_offer_view(character, world, "available")
            quest = Quest(
                character_id=character.id,
                quest_id=P35_ID,
                title=P35_TITLE,
                status="active",
                step=1,
                content_version=P35_CONTENT_VERSION,
                state_version=1,
                progress={
                    "completed_steps": [],
                    "documentary_chain_evidence_ids": [],
                    "technical_sequence_evidence_ids": [],
                    "s35_contextual_knowledge_available": await self._quest_completed(
                        session, character.id, "S35"
                    ),
                },
            )
            session.add(quest)
            await session.flush()
            await self._credit_p35(
                session,
                character.id,
                "p35.activated",
                f"p35.activated:{character.id}",
                {"mission_id": P35_MISSION_ID, "level": character.level},
            )
            return self._p35_view(character, quest, world)

    async def _ensure_p36_quest(self, session, character, world):
        """Automatically activate P36 on valid personal arrival at level 60."""
        existing = await self._quest(session, character.id, P36_ID)
        if existing is not None:
            if existing.content_version != P36_CONTENT_VERSION:
                return None
            return existing
        if (
            character.level < 60
            or world is None
            or world.region != CONFINS_REGION
            or world.location != CONFINS_CAMARA_REGENCIA_LABEL
            or not await self._quest_completed(session, character.id, P35_ID)
            or not await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                )
            )
        ):
            return None
        quest = Quest(
            character_id=character.id,
            quest_id=P36_ID,
            title=P36_TITLE,
            status="active",
            step=1,
            content_version=P36_CONTENT_VERSION,
            state_version=1,
            progress={
                "completed_steps": [],
                "chamber_evidence_ids": [],
                "final_evidence_ids": [],
            },
        )
        session.add(quest)
        await session.flush()
        await self._credit_p36(
            session,
            character.id,
            "p36.activated",
            f"p36.activated:{character.id}",
            {"mission_id": P36_MISSION_ID, "level": character.level},
        )
        return quest

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

    async def start_p29(self, actor: int, version: int = 0) -> AltosMissionView | None:
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
            existing = await self._quest(session, character.id, P29_ID)
            if existing is not None:
                return self._p29_view(character, existing, world)
            p28 = await self._quest(session, character.id, P28_ID)
            if (
                p28 is None
                or p28.status != "completed"
                or p28.content_version != P28_CONTENT_VERSION
                or world.region != ALTOS_REGION
                or world.location != ALTOS_BASTILHA_LABEL
            ):
                return None
            if character.level < 49:
                return self._p29_offer_view(character, world, "suspended")
            if version != 0 or await self._foreground(session, character.id):
                return self._p29_offer_view(character, world, "available")

            quest = Quest(
                character_id=character.id,
                quest_id=P29_ID,
                title=P29_TITLE,
                status="active",
                step=1,
                content_version=P29_CONTENT_VERSION,
                state_version=1,
                progress={"activated": True, "priority_records": []},
            )
            session.add(quest)
            await session.flush()
            await self._credit_p29(
                session,
                character.id,
                "p29.activated",
                f"p29.activated:{character.id}",
                {"givers": ("Sel Ardan", "Maro Keln"), "mission_id": P29_MISSION_ID},
            )
            return self._p29_view(character, quest, world)

    def _p29_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P29_ID,
            title=P29_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location,
            level=character.level,
        )

    def _p29_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=quest.quest_id,
            title=quest.title,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else ALTOS_BASTILHA_LABEL,
            level=character.level,
        )

    def _p30_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P30_ID,
            title=P30_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else ALTOS_BASTILHA_LABEL,
            level=character.level,
        )

    def _p30_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P30_ID,
            title=P30_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else ALTOS_CORACAO_LABEL,
            level=character.level,
        )

    def _p32_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P32_ID,
            title=P32_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else CONFINS_ULTIMO_REFUGIO_LABEL,
            level=character.level,
        )

    def _p32_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P32_ID,
            title=P32_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else CONFINS_ULTIMO_REFUGIO_LABEL,
            level=character.level,
        )

    def _p33_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P33_ID,
            title=P33_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else CONFINS_ESTRADAS_AUSENTES_LABEL,
            level=character.level,
        )

    def _p33_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P33_ID,
            title=P33_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else CONFINS_FRATURAS_LIMIAR_LABEL,
            level=character.level,
        )

    def _p34_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P34_ID,
            title=P34_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else CONFINS_FRATURAS_LIMIAR_LABEL,
            level=character.level,
        )

    def _p34_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P34_ID,
            title=P34_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else CONFINS_NO_CENTRAL_LABEL,
            level=character.level,
        )

    def _p35_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P35_ID,
            title=P35_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else CONFINS_NO_CENTRAL_LABEL,
            level=character.level,
        )

    def _p35_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P35_ID,
            title=P35_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else CONFINS_NO_CENTRAL_LABEL,
            level=character.level,
        )

    def _p36_offer_view(self, character, world, status: str) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P36_ID,
            title=P36_TITLE,
            kind="mission",
            status=status,
            step=1,
            state_version=0,
            progress={},
            location=world.location if world is not None else CONFINS_CAMARA_REGENCIA_LABEL,
            level=character.level,
        )

    async def choose_p36_reward(
        self, actor: int, version: int, option_key: str
    ) -> AltosMissionView | None:
        """Persist the explicit Legendary choice; payment waits for Sera's closeout."""
        if option_key not in P36_REWARD_OPTIONS:
            return await self.resume(actor, P36_ID)
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            quest = await self._quest(session, actor_row.id, P36_ID)
            world = await self._world(session, actor_row.id)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            if (
                quest.status != "active"
                or quest.content_version != P36_CONTENT_VERSION
                or quest.step != 8
                or quest.state_version != version
                or character.level < 60
                or world.region != CONFINS_REGION
                or world.location != CONFINS_CAMARA_REGENCIA_LABEL
                or not progress.get("codices_and_recipe_recorded")
                or not progress.get("nature_recorded")
                or not progress.get("first_core_claimed")
                or 7 not in progress.get("completed_steps", ())
                or not await self._quest_completed(session, character.id, P35_ID)
            ):
                return self._p36_view(character, quest, world)
            previous = progress.get("reward_choice")
            if previous is not None and previous != option_key:
                return self._p36_view(character, quest, world)
            if previous is None:
                progress["reward_choice"] = option_key
                progress["reward_item_id"] = P36_REWARD_OPTIONS[option_key][0]
                quest.progress = progress
                quest.state_version += 1
                await self._credit_p36(
                    session,
                    character.id,
                    "p36.legendary_choice_recorded",
                    f"p36.legendary_choice_recorded:{character.id}",
                    {
                        "item_id": progress["reward_item_id"],
                        "personal": True,
                        "irreversible": True,
                    },
                )
            return self._p36_view(character, quest, world)

    def _p36_view(self, character, quest, world) -> AltosMissionView:
        return AltosMissionView(
            character_id=character.id,
            quest_id=P36_ID,
            title=P36_TITLE,
            kind="mission",
            status=quest.status,
            step=quest.step,
            state_version=quest.state_version,
            progress=quest.progress or {},
            location=world.location if world is not None else CONFINS_CAMARA_REGENCIA_LABEL,
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

    async def _advance_p29(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P29_CONTENT_VERSION
            or quest.state_version != version
            or world.location != ALTOS_BASTILHA_LABEL
            or await self._foreground(session, character.id)
        ):
            return self._p29_view(character, quest, world)

        record_id = next(
            (
                record
                for record in P29_PRIORITY_RECORDS
                if action == f"collect_{record}"
            ),
            None,
        )
        if quest.step == 1 and record_id is not None:
            members = await self._present_p29(
                session, character_ids, 1, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                records = set(progress.get("priority_records", ()))
                if record_id in records:
                    continue
                records.add(record_id)
                progress["priority_records"] = sorted(records)
                member.quest.progress = progress
                if len(records) == len(P29_PRIORITY_RECORDS):
                    member.quest.step = 2
                member.quest.state_version += 1
                await self._credit_p29(
                    session,
                    member.character.id,
                    "p29.priority_record_collected",
                    f"p29.priority_record_collected:{member.character.id}:{record_id}",
                    {"record_id": record_id, "count": len(records)},
                )
        elif quest.step == 2 and action == "locate_convergence_order":
            members = await self._present_p29(
                session, character_ids, 2, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "convergence_order_located": True,
                }
                member.quest.step = 3
                member.quest.state_version += 1
                await self._credit_p29(
                    session,
                    member.character.id,
                    "p29.convergence_order_located",
                    f"p29.convergence_order_located:{member.character.id}",
                    {"term": "Convergência"},
                )
        elif quest.step == 3 and action == "inspect_network_coupling_diagram":
            members = await self._present_p29(
                session, character_ids, 3, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                member.quest.progress = {
                    **(member.quest.progress or {}),
                    "network_coupling_diagram_verified": True,
                    "final_rupture_minutes_accessed": False,
                }
                member.quest.step = 4
                member.quest.state_version += 1
                await self._credit_p29(
                    session,
                    member.character.id,
                    "p29.network_coupling_diagram_verified",
                    f"p29.network_coupling_diagram_verified:{member.character.id}",
                    {"final_rupture_minutes_accessed": False},
                )
        elif (
            quest.step == 5
            and action == "compare_documented_risks_with_sel_and_maro"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("documented_risks_compared"):
                progress["documented_risks_compared"] = True
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p29(
                    session,
                    character.id,
                    "p29.documented_risks_compared",
                    f"p29.documented_risks_compared:{character.id}",
                    {"givers": ("Sel Ardan", "Maro Keln")},
                )
        elif quest.step == 6 and action == "record_convergence_codex":
            progress = dict(quest.progress or {})
            if not progress.get("codex_recorded"):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=P29_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=P29_CODEX_ENTRY,
                    fragment_id=P29_CODEX_ENTRY,
                )
                progress["codex_recorded"] = True
                quest.progress = progress
                quest.step = 7
                quest.state_version += 1
                await self._credit_p29(
                    session,
                    character.id,
                    "p29.convergence_codex_recorded",
                    f"p29.convergence_codex_recorded:{character.id}",
                    {"codex_entry": P29_CODEX_ENTRY},
                )
        elif (
            quest.step == 7
            and action == "open_route_to_coracao"
            and world.location == ALTOS_BASTILHA_LABEL
        ):
            members = await self._present_p29(
                session, character_ids, 7, ALTOS_BASTILHA_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                if progress.get("heart_route_opened"):
                    continue
                progress["heart_route_opened"] = True
                member.quest.progress = progress
                await self._credit_p29(
                    session,
                    member.character.id,
                    "p29.heart_route_opened",
                    f"p29.heart_route_opened:{member.character.id}",
                    {"unlock": ALTOS_CORACAO_ACCESS_UNLOCK},
                )
                await self._complete_p29(session, member.character, member.quest)

        await session.flush()
        return self._p29_view(character, quest, world)

    async def _advance_p30(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P30_CONTENT_VERSION
            or quest.state_version != version
            or world.region != ALTOS_REGION
            or world.location != ALTOS_CORACAO_LABEL
            or await self._foreground(session, character.id)
        ):
            return await self._view(session, character, quest, world)

        if quest.step == 2 and action in {
            f"inspect_load_path_{key}" for key in P30_LOAD_PATHS
        }:
            path_id = action.removeprefix("inspect_load_path_")
            members = await self._present_p30(
                session, character_ids, 2, ALTOS_CORACAO_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                paths = set(progress.get("load_paths", ()))
                if path_id in paths:
                    continue
                paths.add(path_id)
                progress["load_paths"] = sorted(paths)
                completed = set(progress.get("completed_steps", ()))
                if len(paths) == len(P30_LOAD_PATHS):
                    member.quest.step = 3
                    completed.add(2)
                    progress["completed_steps"] = sorted(completed)
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p30(
                    session,
                    member.character.id,
                    f"p30.load_path_{path_id}_examined",
                    f"p30.load_path_{path_id}_examined:{member.character.id}",
                    {"path_id": path_id, "location": ALTOS_CORACAO_LOCATION},
                )
        elif quest.step == 3 and action == "recover_exceptional_coupling_record":
            members = await self._present_p30(
                session, character_ids, 3, ALTOS_CORACAO_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                if progress.get("coupling_record_recovered"):
                    continue
                progress.update(
                    coupling_record_recovered=True,
                    full_rupture_minutes_accessed=False,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    ),
                )
                member.quest.progress = progress
                member.quest.step = 4
                member.quest.state_version += 1
                await self._credit_p30(
                    session,
                    member.character.id,
                    "p30.exceptional_coupling_record_recovered",
                    f"p30.exceptional_coupling_record_recovered:{member.character.id}",
                    {
                        "record": "incomplete_exceptional_coupling",
                        "full_rupture_minutes_accessed": False,
                    },
                )
        elif quest.step == 7 and action == "inspect_postcombat_sabotage_record":
            progress = dict(quest.progress or {})
            if not progress.get("postcombat_record_examined"):
                await self._ensure(
                    session,
                    Unlock,
                    character_id=character.id,
                    unlock_id=P30_NARRATIVE_UNLOCK,
                )
                progress.update(
                    postcombat_record_examined=True,
                    radicalized_wing_sabotage_confirmed=True,
                    collective_attribution=False,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {7}
                    ),
                )
                quest.progress = progress
                quest.step = 8
                quest.state_version += 1
                await self._credit_p30(
                    session,
                    character.id,
                    "p30.postcombat_record_examined",
                    f"p30.postcombat_record_examined:{character.id}",
                    {
                        "codex_entry": P30_CODEX_ENTRY,
                        "radicalized_wing_only": True,
                        "collective_attribution": False,
                    },
                )
        elif quest.step == 8 and action == "record_sabotage_codex":
            progress = dict(quest.progress or {})
            if not progress.get("sabotage_codex_recorded"):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=P30_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=P30_CODEX_ENTRY,
                    fragment_id=P30_CODEX_ENTRY,
                )
                progress.update(
                    sabotage_codex_recorded=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {8}
                    ),
                )
                quest.progress = progress
                quest.step = 9
                quest.state_version += 1
                await self._credit_p30(
                    session,
                    character.id,
                    "p30.sabotage_codex_recorded",
                    f"p30.sabotage_codex_recorded:{character.id}",
                    {"codex_entry": P30_CODEX_ENTRY},
                )
        elif quest.step == 9 and action == "reveal_colossus_recipe":
            progress = dict(quest.progress or {})
            if not progress.get("recipe_revealed"):
                progress.update(
                    recipe_revealed=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {9}
                    ),
                )
                quest.progress = progress
                quest.step = 10
                quest.state_version += 1
                await self._credit_p30(
                    session,
                    character.id,
                    "p30.recipe_revealed",
                    f"p30.recipe_revealed:{character.id}",
                    {"recipe_id": P30_RECIPE_UNLOCK, "direct_discovery": True},
                )

        await session.flush()
        return await self._view(session, character, quest, world)

    async def choose_p30_reward(
        self, actor: int, version: int, option_key: str
    ) -> AltosMissionView | None:
        """Finish P30 with the character's explicit, idempotent Epic choice."""
        option = P30_REWARD_OPTIONS.get(option_key)
        if option is None:
            return await self.resume(actor, P30_ID)
        item_id, item_name, slot = option
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            quest = await self._quest(session, actor_row.id, P30_ID)
            world = await self._world(session, actor_row.id)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            if (
                quest.status != "active"
                or quest.content_version != P30_CONTENT_VERSION
                or quest.step != 10
                or quest.state_version != version
                or not progress.get("recipe_revealed")
                or not progress.get("postcombat_record_examined")
            ):
                return await self._view(session, character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P30_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                weapon = weapon_definition(item_id)
                payload = materialize_equipment(
                    f"{P30_REWARD_SOURCE}:{character.id}:{item_id}",
                    "Épico",
                    50,
                    forced_name=item_name,
                    forced_slot=slot,
                    bound=True,
                    weapon_type_id=item_id if weapon is not None else None,
                )
                payload["catalog_item_id"] = item_id
                event = RewardEvent(
                    character_id=character.id,
                    source_id=P30_REWARD_SOURCE,
                )
                session.add(event)
                await session.flush()
                character.xp += 134_100
                character.crowns += 1_700
                session.add_all(
                    (
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="xp",
                            quantity=134_100,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="crowns",
                            quantity=1_700,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="equipment",
                            item_id=item_id,
                            quantity=1,
                            payload=payload,
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=ALTOS_FERRO_CONTRAPESO,
                            quantity=5,
                            payload={"material_id": ALTOS_FERRO_CONTRAPESO, "bound": True},
                        ),
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=ALTOS_CINZA_BASALTO,
                            quantity=3,
                            payload={"material_id": ALTOS_CINZA_BASALTO, "bound": True},
                        ),
                    )
                )
                source_key = f"{P30_REWARD_SOURCE}:equipment"
                if await self.road._inventory_slots(session, character.id) < 60:
                    instance_id, instance = equipment_instance_payload(payload)
                    session.add(
                        EquipmentItem(
                            id=instance_id,
                            character_id=character.id,
                            source_key=source_key,
                            item_name=item_name,
                            rarity="Épico",
                            slot=slot,
                            item_level=50,
                            bound=True,
                            payload=instance,
                        )
                    )
                else:
                    await self.road._pending(
                        session, character.id, source_key, "equipment", payload
                    )
                for material_id, quantity, key in (
                    (ALTOS_FERRO_CONTRAPESO, 5, "ferro_contrapeso"),
                    (ALTOS_CINZA_BASALTO, 3, "cinza_basalto"),
                ):
                    await self.road.deliver_material(
                        session,
                        character,
                        material_id,
                        quantity,
                        f"{P30_REWARD_SOURCE}:material:{key}",
                        bound=True,
                    )
                progress.update(reward_choice=option_key, reward_item_id=item_id)
            else:
                equipment_component = await session.scalar(
                    select(RewardComponent)
                    .where(
                        RewardComponent.reward_event_id == event.id,
                        RewardComponent.kind == "equipment",
                    )
                    .with_for_update()
                )
                chosen_id = (
                    equipment_component.item_id if equipment_component is not None else None
                )
                chosen = next(
                    (
                        (key, values)
                        for key, values in P30_REWARD_OPTIONS.items()
                        if values[0] == chosen_id
                    ),
                    None,
                )
                if chosen is None:
                    raise RuntimeError("P30 reward event has no valid equipment choice")
                progress.update(reward_choice=chosen[0], reward_item_id=chosen_id)

            quest.status = "completed"
            progress.update(
                completed=True,
                completed_steps=sorted(set(progress.get("completed_steps", ())) | {10}),
            )
            quest.progress = progress
            quest.state_version += 1
            character.ruleset_version = CHARACTER_RULESET
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=P30_RECIPE_UNLOCK,
            )
            await self._ensure(
                session,
                Unlock,
                character_id=character.id,
                unlock_id=P30_NARRATIVE_UNLOCK,
            )
            await self._ensure(
                session,
                Achievement,
                character_id=character.id,
                achievement_id=P30_ACHIEVEMENT,
            )
            await consolidate_character_level(session, character)
            await self._reconcile_altos_region_achievement(session, character)
            if character.level >= 51:
                await self._ensure(
                    session,
                    Unlock,
                    character_id=character.id,
                    unlock_id=P30_CONFINS_UNLOCK,
                )
            await self._credit_p30(
                session,
                character.id,
                "p30.completed",
                f"p30.completed:{character.id}",
                {"reward_item_id": progress["reward_item_id"]},
            )
            return await self._view(session, character, quest, world)

    async def _claim_p30_core(self, session, character) -> bool:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P30_CORE_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is not None:
            return False
        event = RewardEvent(
            character_id=character.id,
            source_id=P30_CORE_REWARD_SOURCE,
        )
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="material",
                item_id=P30_CORE_ID,
                quantity=1,
                payload={"material_id": P30_CORE_ID, "bound": True},
            )
        )
        await self.road.deliver_material(
            session,
            character,
            P30_CORE_ID,
            1,
            f"{P30_CORE_REWARD_SOURCE}:material:core",
            bound=True,
        )
        return True

    async def _reconcile_altos_region_achievement(self, session, character) -> bool:
        if (
            character.level < 50
            or not await self._quest_completed(session, character.id, P30_ID)
        ):
            return False
        discoveries = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id.in_(ALTOS_PRIMARY_LOCATIONS),
                    )
                )
            ).all()
        )
        if not set(ALTOS_PRIMARY_LOCATIONS).issubset(discoveries):
            return False
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=ALTOS_REGION_ACHIEVEMENT,
        )
        return True

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

    async def _advance_p32(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P32_CONTENT_VERSION
            or quest.state_version != version
            or world.region != CONFINS_REGION
            or await self._foreground(session, character.id)
        ):
            return self._p32_view(character, quest, world)

        if (
            quest.step == 1
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
            and action == "receive_p32_route_traces"
        ):
            progress = dict(quest.progress or {})
            trace_ids = sorted(set(progress.get("route_trace_ids", ())) | {"outbound", "return"})
            if len(trace_ids) == 2:
                progress["route_trace_ids"] = trace_ids
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {1}
                )
                progress["two_route_traces_received"] = True
                quest.progress = progress
                quest.step = 2
                quest.state_version += 1
                await self._credit_p32(
                    session,
                    character.id,
                    "p32.received_route_traces",
                    f"p32.received_route_traces:{character.id}",
                    {"trace_ids": trace_ids},
                )
        elif (
            quest.step == 3
            and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
            and action in {
                "inspect_finished_foundation",
                "inspect_absent_map_marker",
                "inspect_discordant_return_record",
            }
        ):
            members = await self._present_p32(
                session, character_ids, 3, CONFINS_ESTRADAS_AUSENTES_LABEL
            )
            for member in members:
                if member.character.level < 53:
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("physical_fracture_evidence", ()))
                if action in evidence:
                    continue
                evidence.add(action)
                progress["physical_fracture_evidence"] = sorted(evidence)
                if len(evidence) == 3:
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    )
                    member.quest.step = 4
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p32(
                    session,
                    member.character.id,
                    f"p32.{action}",
                    f"p32.{action}:{member.character.id}",
                    {
                        "location_id": CONFINS_ESTRADAS_AUSENTES_LOCATION,
                        "evidence_id": action,
                    },
                )
        elif (
            quest.step == 5
            and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
            and (quest.progress or {}).get("scripted_andarilho_victory")
            and (quest.progress or {}).get("andarilho_not_clone_nor_soul_observed")
            and action == "compare_fracture_evidence"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("fracture_evidence_compared"):
                progress["fracture_evidence_compared"] = True
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {5}
                )
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p32(
                    session,
                    character.id,
                    "p32.evidence_compared",
                    f"p32.evidence_compared:{character.id}",
                    {
                        "npc_ids": ("npc.confins.talen_nyr", "npc.confins.sera_nol"),
                        "observations": (
                            "andarilho_not_clone_nor_soul",
                            "localized_stability_failure_not_portal",
                        ),
                        "interpretation": "localized_stability_failure_not_portal",
                    },
                )
        elif (
            quest.step == 6
            and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
            and (quest.progress or {}).get("fracture_evidence_compared")
            and action == "record_fracture_codex_and_conclude"
        ):
            await self._ensure(
                session, CodexEntry, character_id=character.id, entry_id=P32_CODEX_ENTRY
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=P32_CODEX_ENTRY,
                fragment_id=P32_CODEX_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress["codex_recorded"] = True
            progress["completed_steps"] = sorted(
                set(progress.get("completed_steps", ())) | {6}
            )
            quest.progress = progress
            await self._complete_p32(session, character, quest)

        return await self._view(session, character, quest, world)

    async def _advance_p33(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P33_CONTENT_VERSION
            or quest.state_version != version
            or world.region != CONFINS_REGION
            or await self._foreground(session, character.id)
        ):
            return self._p33_view(character, quest, world)

        if (
            quest.step == 2
            and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
            and action in {
                "inspect_stone_position",
                "inspect_wear_state",
                "inspect_trail_observation_sequence",
            }
        ):
            members = await self._present_p33(
                session, character_ids, 2, CONFINS_FRATURAS_LIMIAR_LABEL
            )
            for member in members:
                if member.character.level < 55:
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("physical_evidence_ids", ()))
                if action in evidence:
                    continue
                evidence.add(action)
                progress["physical_evidence_ids"] = sorted(evidence)
                if len(evidence) == 3:
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {2}
                    )
                    member.quest.step = 3
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p33(
                    session,
                    member.character.id,
                    f"p33.{action}",
                    f"p33.{action}:{member.character.id}",
                    {
                        "location_id": CONFINS_FRATURAS_LIMIAR_LOCATION,
                        "evidence_id": action,
                    },
                )
        elif (
            quest.step == 4
            and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
            and (quest.progress or {}).get("scripted_casca_victory")
            and action == "interpret_avesso_with_roven"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("avesso_interpreted"):
                progress.update(
                    avesso_interpreted=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    ),
                )
                quest.progress = progress
                quest.step = 5
                quest.state_version += 1
                await self._credit_p33(
                    session,
                    character.id,
                    "p33.avesso_interpreted",
                    f"p33.avesso_interpreted:{character.id}",
                    {
                        "npc_id": "npc.confins.roven_pell",
                        "interpretation": "causality_matter_identity_unreliable_state",
                        "not_place_or_entity_or_will": True,
                    },
                )
        elif (
            quest.step == 5
            and world.location == CONFINS_FRATURAS_LIMIAR_LABEL
            and (quest.progress or {}).get("avesso_interpreted")
            and action == "record_avesso_codex"
        ):
            await self._ensure(
                session, CodexEntry, character_id=character.id, entry_id=P33_CODEX_ENTRY
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=P33_CODEX_ENTRY,
                fragment_id=P33_CODEX_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress.update(
                codex_recorded=True,
                completed_steps=sorted(set(progress.get("completed_steps", ())) | {5}),
            )
            quest.progress = progress
            quest.step = 6
            quest.state_version += 1
            await self._credit_p33(
                session,
                character.id,
                "p33.codex_recorded",
                f"p33.codex_recorded:{character.id}",
                {"codex_entry_id": P33_CODEX_ENTRY, "personal_record": True},
            )

        return self._p33_view(character, quest, world)

    async def _advance_p34(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P34_CONTENT_VERSION
            or quest.state_version != version
            or world.region != CONFINS_REGION
            or await self._foreground(session, character.id)
        ):
            return self._p34_view(character, quest, world)

        if (
            quest.step == 2
            and world.location == CONFINS_NO_CENTRAL_LABEL
            and (quest.progress or {}).get("no_arrival_recorded")
            and action in {
                "inspect_reference_conduction",
                "inspect_route_alignment",
                "inspect_failure_communication",
            }
        ):
            members = await self._present_p34(
                session, character_ids, 2, CONFINS_NO_CENTRAL_LABEL
            )
            for member in members:
                if member.character.level < 57 or not await self._quest_completed(
                    session, member.character.id, P33_ID
                ):
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("physical_point_evidence_ids", ()))
                if action in evidence:
                    continue
                evidence.add(action)
                progress["physical_point_evidence_ids"] = sorted(evidence)
                if len(evidence) == 3:
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {2}
                    )
                    member.quest.step = 3
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p34(
                    session,
                    member.character.id,
                    f"p34.{action}",
                    f"p34.{action}:{member.character.id}",
                    {
                        "location_id": CONFINS_NO_CENTRAL_LOCATION,
                        "evidence_id": action,
                    },
                )
        elif (
            quest.step == 4
            and world.location == CONFINS_NO_CENTRAL_LABEL
            and (quest.progress or {}).get("scripted_custodio_victory")
            and action == "observe_regional_anchor_evidence"
        ):
            members = await self._present_p34(
                session, character_ids, 4, CONFINS_NO_CENTRAL_LABEL
            )
            for member in members:
                if member.character.level < 57:
                    continue
                progress = dict(member.quest.progress or {})
                if progress.get("regional_anchor_evidence"):
                    continue
                progress.update(
                    regional_anchor_evidence=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    ),
                )
                member.quest.progress = progress
                member.quest.step = 5
                member.quest.state_version += 1
                await self._credit_p34(
                    session,
                    member.character.id,
                    "p34.regional_anchors_observed",
                    f"p34.regional_anchors_observed:{member.character.id}",
                    {
                        "different_anchors_stabilized_regions": True,
                        "before_final_night": True,
                    },
                )
        elif (
            quest.step == 5
            and world.location == CONFINS_NO_CENTRAL_LABEL
            and (quest.progress or {}).get("regional_anchor_evidence")
            and action == "compare_eris_with_roven"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("coordination_interpreted"):
                progress.update(
                    coordination_interpreted=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {5}
                    ),
                )
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p34(
                    session,
                    character.id,
                    "p34.coordination_interpreted",
                    f"p34.coordination_interpreted:{character.id}",
                    {
                        "technical_giver": "npc.confins.eris_val",
                        "civil_documentation": "npc.confins.roven_pell",
                        "finding": "coordination_and_reference_not_energy_or_master_switch",
                        "personal": True,
                    },
                )
        elif (
            quest.step == 6
            and world.location == CONFINS_NO_CENTRAL_LABEL
            and (quest.progress or {}).get("coordination_interpreted")
            and action == "record_anchor_codex_and_conclude"
        ):
            await self._ensure(
                session,
                CodexEntry,
                character_id=character.id,
                entry_id=P34_CODEX_ENTRY,
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=P34_CODEX_ENTRY,
                fragment_id=P34_CODEX_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress.update(
                codex_recorded=True,
                completed_steps=sorted(set(progress.get("completed_steps", ())) | {6}),
            )
            quest.progress = progress
            await self._credit_p34(
                session,
                character.id,
                "p34.codex_recorded",
                f"p34.codex_recorded:{character.id}",
                {
                    "codex_entry_id": P34_CODEX_ENTRY,
                    "givers": ("npc.confins.sera_nol", "npc.confins.eris_val"),
                    "personal": True,
                },
            )
            await self._complete_p34(session, character, quest)

        return self._p34_view(character, quest, world)

    async def _advance_p36(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P36_CONTENT_VERSION
            or quest.state_version != version
            or character.level < 60
            or world.region != CONFINS_REGION
            or world.location != CONFINS_CAMARA_REGENCIA_LABEL
            or not await self._p36_individually_eligible(session, character)
            or await self._foreground(session, character.id)
        ):
            return self._p36_view(character, quest, world)

        if quest.step == 1 and action in {
            f"record_chamber_{item}" for item in P36_STAGE_ONE_EVIDENCE
        }:
            evidence_id = action.removeprefix("record_chamber_")
            if not (quest.progress or {}).get("chamber_entered"):
                return self._p36_view(character, quest, world)
            members = await self._present_p36(
                session, character_ids, 1, CONFINS_CAMARA_REGENCIA_LABEL
            )
            for member in members:
                if not await self._p36_individually_eligible(session, member.character):
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("chamber_evidence_ids", ()))
                if evidence_id in evidence:
                    continue
                evidence.add(evidence_id)
                progress["chamber_evidence_ids"] = sorted(evidence)
                if set(P36_STAGE_ONE_EVIDENCE).issubset(evidence):
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {1}
                    )
                    member.quest.step = 2
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p36(
                    session,
                    member.character.id,
                    f"p36.chamber_evidence.{evidence_id}",
                    f"p36.chamber_evidence.{evidence_id}:{member.character.id}",
                    {
                        "evidence_id": evidence_id,
                        "observed_in": CONFINS_CAMARA_REGENCIA_LOCATION,
                    },
                )
        elif quest.step == 2 and action in {
            f"record_final_evidence_{item}" for item in P36_STAGE_TWO_EVIDENCE
        }:
            evidence_id = action.removeprefix("record_final_evidence_")
            members = await self._present_p36(
                session, character_ids, 2, CONFINS_CAMARA_REGENCIA_LABEL
            )
            for member in members:
                if not await self._p36_individually_eligible(session, member.character):
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("final_evidence_ids", ()))
                if evidence_id in evidence:
                    continue
                evidence.add(evidence_id)
                progress["final_evidence_ids"] = sorted(evidence)
                if set(P36_STAGE_TWO_EVIDENCE).issubset(evidence):
                    progress.update(
                        completed_steps=sorted(
                            set(progress.get("completed_steps", ())) | {2}
                        ),
                        knowledge_gaps_recorded=True,
                    )
                    member.quest.step = 3
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p36(
                    session,
                    member.character.id,
                    f"p36.final_evidence.{evidence_id}",
                    f"p36.final_evidence.{evidence_id}:{member.character.id}",
                    {
                        "evidence_id": evidence_id,
                        "continuous_final_account_not_claimed": True,
                    },
                )
        elif (
            quest.step == 6
            and (quest.progress or {}).get("first_core_claimed")
            and action == "record_regent_nature"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("nature_recorded"):
                progress.update(
                    nature_recorded=True,
                    nature_facts={
                        "manifestation_composed_of_cael_fragments_records_protocols_"
                        "matter_and_avesso_states": True,
                        "not_living_or_resurrected_cael": True,
                        "protocol_closure_does_not_cure_veil": True,
                        "protocol_closure_does_not_destroy_avesso": True,
                        "historical_certainty_is_limited": True,
                    },
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {6}
                    ),
                )
                quest.progress = progress
                quest.step = 7
                quest.state_version += 1
                await self._credit_p36(
                    session,
                    character.id,
                    "p36.regent_nature_recorded",
                    f"p36.regent_nature_recorded:{character.id}",
                    progress["nature_facts"] | {"personal": True},
                )
        elif quest.step == 7 and action == "record_regent_codices_and_recipe":
            progress = dict(quest.progress or {})
            if progress.get("nature_recorded") and not progress.get(
                "codices_and_recipe_recorded"
            ):
                for entry_id in (P36_CODEX_NATURE, P36_CODEX_PROTOCOL):
                    await self._ensure(
                        session,
                        CodexEntry,
                        character_id=character.id,
                        entry_id=entry_id,
                    )
                    await self._ensure(
                        session,
                        CodexFragment,
                        character_id=character.id,
                        entry_id=entry_id,
                        fragment_id=entry_id,
                    )
                await self._ensure(
                    session,
                    Unlock,
                    character_id=character.id,
                    unlock_id=P36_RECIPE_UNLOCK,
                )
                progress.update(
                    codices_and_recipe_recorded=True,
                    codex_records=[P36_CODEX_NATURE, P36_CODEX_PROTOCOL],
                    recipe_revealed=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {7}
                    ),
                )
                quest.progress = progress
                quest.step = 8
                quest.state_version += 1
                await self._credit_p36(
                    session,
                    character.id,
                    "p36.codices_and_recipe_recorded",
                    f"p36.codices_and_recipe_recorded:{character.id}",
                    {
                        "codex_entry_ids": (P36_CODEX_NATURE, P36_CODEX_PROTOCOL),
                        "recipe_id": P36_RECIPE_UNLOCK,
                        "direct_discovery": True,
                        "no_extra_materials": True,
                        "personal": True,
                    },
                )
        elif (
            quest.step == 8
            and action == "conclude_with_sera"
            and (quest.progress or {}).get("reward_choice") in P36_REWARD_OPTIONS
            and (quest.progress or {}).get("codices_and_recipe_recorded")
            and (quest.progress or {}).get("nature_recorded")
            and (quest.progress or {}).get("first_core_claimed")
        ):
            await self._complete_p36(session, character, quest)

        return self._p36_view(character, quest, world)

    async def _complete_p36(self, session, character, quest) -> None:
        progress = dict(quest.progress or {})
        option_key = progress.get("reward_choice")
        option = P36_REWARD_OPTIONS.get(option_key)
        if (
            option is None
            or quest.status != "active"
            or quest.step != 8
            or not progress.get("nature_recorded")
            or not progress.get("codices_and_recipe_recorded")
            or not progress.get("first_core_claimed")
            or not await self._quest_completed(session, character.id, P35_ID)
        ):
            return
        item_id, item_name, slot = option
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P36_REWARD_SOURCE,
            )
            .with_for_update()
        )
        materials = (
            (CONFINS_FERRO_BALIZA, 3, "ferro_baliza"),
            (CONFINS_COURO_MARCHA, 1, "couro_marcha"),
            (CONFINS_MUSGO_LIMIAR, 1, "musgo_limiar"),
            (CONFINS_PO_REFERENCIA, 3, "po_referencia"),
        )
        if event is None:
            weapon = weapon_definition(item_id)
            payload = materialize_equipment(
                f"{P36_REWARD_SOURCE}:{character.id}:{item_id}",
                "Lendário",
                60,
                forced_name=item_name,
                forced_slot=slot,
                bound=True,
                weapon_type_id=item_id if weapon is not None else None,
            )
            payload["catalog_item_id"] = item_id
            event = RewardEvent(character_id=character.id, source_id=P36_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 183_420
            character.crowns += 2_000
            session.add_all(
                (
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=183_420),
                    RewardComponent(reward_event_id=event.id, kind="crowns", quantity=2_000),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="equipment",
                        item_id=item_id,
                        quantity=1,
                        payload=payload,
                    ),
                    *[
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=material_id,
                            quantity=quantity,
                            payload={"material_id": material_id, "bound": True},
                        )
                        for material_id, quantity, _key in materials
                    ],
                )
            )
            equipment_source = f"{P36_REWARD_SOURCE}:equipment"
            if await self.road._inventory_slots(session, character.id) < 60:
                instance_id, instance = equipment_instance_payload(payload)
                session.add(
                    EquipmentItem(
                        id=instance_id,
                        character_id=character.id,
                        source_key=equipment_source,
                        item_name=item_name,
                        rarity="Lendário",
                        slot=slot,
                        item_level=60,
                        bound=True,
                        payload=instance,
                    )
                )
            else:
                await self.road._pending(
                    session, character.id, equipment_source, "equipment", payload
                )
            for material_id, quantity, key in materials:
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P36_REWARD_SOURCE}:material:{key}",
                    bound=True,
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
            if component is None or component.item_id != item_id:
                raise RuntimeError("P36 reward event conflicts with the persisted choice")

        await self._ensure(
            session, Unlock, character_id=character.id, unlock_id=P36_NARRATIVE_UNLOCK
        )
        await self._ensure(
            session, Unlock, character_id=character.id, unlock_id=P36_CAMPAIGN_UNLOCK
        )
        progress.update(
            completed=True,
            completed_steps=list(range(1, 9)),
            reward_item_id=item_id,
            regent_personally_inactive=True,
            campaign_completed=True,
            legacy_eligible=True,
        )
        quest.status = "completed"
        quest.step = 8
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._add_p36_bestiary_evidence(
            session, character.id, "p36_completed", points=0
        )
        await self.road.bestiary.refresh_boss_mastery(
            session, character.id, P36_BOSS_ID
        )
        await self._reconcile_confins_region_achievement(session, character)
        await self._credit_p36(
            session,
            character.id,
            "p36.completed",
            f"p36.completed:{character.id}",
            {
                "mission_id": P36_MISSION_ID,
                "first_journey_complete": True,
                "legacy_eligible": True,
                "world_state_mutated": False,
                "reward_item_id": item_id,
            },
        )

    async def _claim_p36_core(self, session, character) -> bool:
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P36_CORE_SOURCE,
            )
            .with_for_update()
        )
        if event is not None:
            return False
        event = RewardEvent(character_id=character.id, source_id=P36_CORE_SOURCE)
        session.add(event)
        await session.flush()
        session.add(
            RewardComponent(
                reward_event_id=event.id,
                kind="material",
                item_id=P36_CORE_ID,
                quantity=1,
                payload={"material_id": P36_CORE_ID, "bound": True},
            )
        )
        await self.road.deliver_material(
            session,
            character,
            P36_CORE_ID,
            1,
            f"{P36_CORE_SOURCE}:material:core",
            bound=True,
        )
        return True

    async def _reconcile_confins_region_achievement(self, session, character) -> bool:
        if (
            character.level < 60
            or not await self._quest_completed(session, character.id, P36_ID)
        ):
            return False
        locations = tuple(location_id for location_id, _name in CONFINS_LOCATION_CATALOG)
        discovered = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id.in_(locations),
                    )
                )
            ).all()
        )
        if not set(locations).issubset(discovered):
            return False
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=P36_REGION_ACHIEVEMENT,
        )
        await self._ensure(
            session,
            CharacterCosmetic,
            character_id=character.id,
            cosmetic_id=P36_REGION_APPEARANCE,
            cosmetic_type="appearance",
            source_achievement_id=P36_REGION_ACHIEVEMENT,
        )
        return True

    async def _add_p36_bestiary_evidence(
        self, session, character_id, evidence_id, *, points: int = 0
    ) -> bool:
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == P36_BOSS_ID,
            )
            .with_for_update()
        )
        if entry is None:
            return False
        created = await self.road.bestiary.add_evidence(
            session,
            entry,
            character_id,
            P36_BOSS_ID,
            evidence_id,
            "campaign",
            points,
        )
        await self.road.bestiary.refresh_boss_mastery(
            session, character_id, P36_BOSS_ID
        )
        return created

    async def _record_p36_bestiary_state(self, session, character_id, combat) -> None:
        entry = await session.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == P36_BOSS_ID,
            )
            .with_for_update()
        )
        if entry is None:
            return
        if combat.phase_id in {"I", "default"}:
            await self.road.bestiary.add_evidence(
                session, entry, character_id, P36_BOSS_ID, "phase:manter", "phase", 0
            )
        for trigger_id, evidence_id in (
            ("confins.regent.phase.ii", "phase:referencias_incompativeis"),
            ("confins.regent.phase.iii", "phase:protocolo_que_nao_pode_concluir"),
        ):
            if trigger_id in combat.phase_triggered_ids:
                await self.road.bestiary.add_evidence(
                    session, entry, character_id, P36_BOSS_ID, evidence_id, "phase", 0
                )
        if (
            combat.phase_id == "II"
            and any(
                key in combat.fighters
                and combat.fighters[key].hp > 0
                and not combat.fighters[key].encounter_hidden
                for key in P36_ANCHOR_KEYS
            )
        ):
            await self.road.bestiary.add_evidence(
                session,
                entry,
                character_id,
                P36_BOSS_ID,
                "mechanic:anchor_registry_observed",
                "mechanic",
                0,
            )
        await self.road.bestiary.refresh_boss_mastery(
            session, character_id, P36_BOSS_ID
        )

    async def _p36_individually_eligible(self, session, character) -> bool:
        return bool(
            character.level >= 60
            and await self._quest_completed(session, character.id, P35_ID)
            and await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                )
            )
        )

    async def _advance_p35(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P35_CONTENT_VERSION
            or quest.state_version != version
            or world.region != CONFINS_REGION
            or world.location != CONFINS_NO_CENTRAL_LABEL
            or character.level < 59
            or not await self._quest_completed(session, character.id, P34_ID)
            or await self._foreground(session, character.id)
        ):
            return self._p35_view(character, quest, world)

        if quest.step == 1 and action in {
            f"record_chain_{chain}" for chain in P35_DOCUMENT_CHAINS
        }:
            chain = action.removeprefix("record_chain_")
            members = await self._present_p35(
                session, character_ids, 1, CONFINS_NO_CENTRAL_LABEL
            )
            for member in members:
                if member.character.level < 59 or not await self._quest_completed(
                    session, member.character.id, P34_ID
                ):
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("documentary_chain_evidence_ids", ()))
                if chain in evidence:
                    continue
                evidence.add(chain)
                progress["documentary_chain_evidence_ids"] = sorted(evidence)
                if set(P35_DOCUMENT_CHAINS).issubset(evidence):
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {1}
                    )
                    member.quest.step = 2
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p35(
                    session,
                    member.character.id,
                    f"p35.documentary_chain.{chain}",
                    f"p35.documentary_chain.{chain}:{member.character.id}",
                    {"chain_id": chain, "location_id": CONFINS_NO_CENTRAL_LOCATION},
                )
        elif quest.step == 2 and action in {
            f"verify_sequence_{item}" for item in P35_TECHNICAL_SEQUENCE
        }:
            item = action.removeprefix("verify_sequence_")
            members = await self._present_p35(
                session, character_ids, 2, CONFINS_NO_CENTRAL_LABEL
            )
            for member in members:
                if member.character.level < 59 or not await self._quest_completed(
                    session, member.character.id, P34_ID
                ):
                    continue
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("technical_sequence_evidence_ids", ()))
                if item in evidence:
                    continue
                evidence.add(item)
                progress["technical_sequence_evidence_ids"] = sorted(evidence)
                if set(P35_TECHNICAL_SEQUENCE).issubset(evidence):
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {2}
                    )
                    member.quest.step = 3
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p35(
                    session,
                    member.character.id,
                    f"p35.technical_sequence.{item}",
                    f"p35.technical_sequence.{item}:{member.character.id}",
                    {"evidence_id": item, "materially_verified": True},
                )
        elif (
            quest.step == 4
            and (quest.progress or {}).get("scripted_vigia_victory")
            and action == "reconstruct_desvelados_sabotage"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("desvelados_reconstruction_recorded"):
                progress.update(
                    desvelados_reconstruction_recorded=True,
                    desvelados_facts={
                        "initial_opposition_legitimate": True,
                        "radicalized_faction_authorized_conscious_sabotage": True,
                        "intended_controlled_regional_isolation": True,
                        "catastrophic_risk_known": True,
                        "no_collective_blame": True,
                    },
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    ),
                )
                quest.progress = progress
                quest.step = 5
                quest.state_version += 1
                await self._credit_p35(
                    session,
                    character.id,
                    "p35.desvelados_reconstructed",
                    f"p35.desvelados_reconstructed:{character.id}",
                    progress["desvelados_facts"] | {"personal": True},
                )
        elif (
            quest.step == 5
            and (quest.progress or {}).get("desvelados_reconstruction_recorded")
            and action == "record_cael_rhen_decision_context"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("cael_decision_recorded"):
                progress.update(
                    cael_decision_recorded=True,
                    cael_decision_facts={
                        "convergence_involved_risk": True,
                        "interruption_at_exceptional_coupling_also_risked_immediate_collapse": True,
                        "did_not_desire_world_destruction": True,
                        "rupture_was_multi_factor_cascade": True,
                        "documentary_uncertainty_preserved": True,
                    },
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {5}
                    ),
                )
                quest.progress = progress
                quest.step = 6
                quest.state_version += 1
                await self._credit_p35(
                    session,
                    character.id,
                    "p35.cael_decision_context_recorded",
                    f"p35.cael_decision_context_recorded:{character.id}",
                    progress["cael_decision_facts"] | {"personal": True},
                )
        elif (
            quest.step == 6
            and (quest.progress or {}).get("cael_decision_recorded")
            and action == "record_convergence_codices"
        ):
            for entry_id in (P35_CODEX_RECONSTRUCTION, P35_CODEX_RUPTURE):
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=entry_id,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=entry_id,
                    fragment_id=entry_id,
                )
            progress = dict(quest.progress or {})
            progress.update(
                codex_records=[P35_CODEX_RECONSTRUCTION, P35_CODEX_RUPTURE],
                codex_recorded=True,
                completed_steps=sorted(set(progress.get("completed_steps", ())) | {6}),
            )
            quest.progress = progress
            quest.step = 7
            quest.state_version += 1
            await self._credit_p35(
                session,
                character.id,
                "p35.codices_recorded",
                f"p35.codices_recorded:{character.id}",
                {
                    "codex_entry_ids": (P35_CODEX_RECONSTRUCTION, P35_CODEX_RUPTURE),
                    "provenance": "cross_checked_records",
                    "missing_final_minutes_preserved": True,
                    "personal": True,
                },
            )
        elif quest.step == 7 and action == "open_chamber_route":
            members = await self._present_p35(
                session, character_ids, 7, CONFINS_NO_CENTRAL_LABEL
            )
            for member in members:
                if member.character.level < 59 or not await self._quest_completed(
                    session, member.character.id, P34_ID
                ):
                    continue
                progress = dict(member.quest.progress or {})
                if progress.get("chamber_route_opened"):
                    continue
                await self._ensure(
                    session,
                    Unlock,
                    character_id=member.character.id,
                    unlock_id=CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                )
                progress.update(
                    chamber_route_opened=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {7}
                    ),
                )
                member.quest.progress = progress
                member.quest.step = 8
                member.quest.state_version += 1
                await self._credit_p35(
                    session,
                    member.character.id,
                    "p35.chamber_route_opened",
                    f"p35.chamber_route_opened:{member.character.id}",
                    {
                        "unlock_id": CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                        "level_gate": 59,
                        "individual": True,
                    },
                )
        elif (
            quest.step == 8
            and (quest.progress or {}).get("chamber_route_opened")
            and action == "conclude_with_sera"
            and await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character.id,
                    Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                )
            )
        ):
            await self._complete_p35(session, character, quest)

        return self._p35_view(character, quest, world)

    async def _complete_p35(self, session, character, quest) -> None:
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=P35_NARRATIVE_UNLOCK,
        )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=P35_ACHIEVEMENT,
        )
        await self._ensure(
            session,
            CharacterCosmetic,
            character_id=character.id,
            cosmetic_id=P35_FRAME_COSMETIC,
            cosmetic_type="frame",
            source_achievement_id=P35_ACHIEVEMENT,
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P35_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P35_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 98_950
            character.crowns += 1_220
            materials = (
                (CONFINS_FERRO_BALIZA, 2, "ferro_baliza"),
                (CONFINS_MUSGO_LIMIAR, 1, "musgo_limiar"),
                (CONFINS_PO_REFERENCIA, 1, "po_referencia"),
            )
            session.add_all(
                [
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", quantity=98_950
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=1_220
                    ),
                    *[
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=material_id,
                            quantity=quantity,
                            payload={"material_id": material_id, "bound": True},
                        )
                        for material_id, quantity, _key in materials
                    ],
                ]
            )
            for material_id, quantity, key in materials:
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P35_REWARD_SOURCE}:material:{key}",
                    bound=True,
                )
        progress = dict(quest.progress or {})
        progress.update(
            completed=True,
            completed_steps=list(range(1, 9)),
            regent_not_confronted=True,
            campaign_not_complete=True,
        )
        quest.status = "completed"
        quest.step = 8
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p35(
            session,
            character.id,
            "p35.completed",
            f"p35.completed:{character.id}",
            {
                "mission_id": P35_MISSION_ID,
                "narrative_unlock": P35_NARRATIVE_UNLOCK,
                "regent_confronted": False,
                "campaign_complete": False,
            },
        )

    async def _complete_p34(self, session, character, quest) -> None:
        for unlock_id in (
            CONFINS_NO_CENTRAL_HUNT_UNLOCK,
            CONFINS_NO_CENTRAL_EXPLORE_UNLOCK,
            P34_NARRATIVE_UNLOCK,
        ):
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=unlock_id
            )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=P34_ACHIEVEMENT,
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P34_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P34_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 93_250
            character.crowns += 1_200
            materials = (
                (CONFINS_FERRO_BALIZA, 2, "ferro_baliza"),
                (CONFINS_COURO_MARCHA, 1, "couro_marcha"),
                (CONFINS_PO_REFERENCIA, 1, "po_referencia"),
            )
            session.add_all(
                [
                    RewardComponent(reward_event_id=event.id, kind="xp", quantity=93_250),
                    RewardComponent(reward_event_id=event.id, kind="crowns", quantity=1_200),
                    *[
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=material_id,
                            quantity=quantity,
                            payload={"material_id": material_id, "bound": True},
                        )
                        for material_id, quantity, _key in materials
                    ],
                ]
            )
            for material_id, quantity, key in materials:
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P34_REWARD_SOURCE}:material:{key}",
                    bound=True,
                )
        progress = dict(quest.progress or {})
        progress.update(completed=True, completed_steps=list(range(1, 7)))
        quest.status = "completed"
        quest.step = 6
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p34(
            session,
            character.id,
            "p34.completed",
            f"p34.completed:{character.id}",
            {"mission_id": P34_MISSION_ID, "codex_entry_id": P34_CODEX_ENTRY},
        )

    async def choose_p33_reward(
        self, actor: int, version: int, option_key: str
    ) -> AltosMissionView | None:
        """Conclude P33 only after the character makes an explicit Rare choice."""
        option = P33_REWARD_OPTIONS.get(option_key)
        if option is None:
            return await self.resume(actor, P33_ID)
        item_id, item_name, slot = option
        async with self.sessions.begin() as session:
            actor_row = await self._character(session, actor)
            if actor_row is None:
                return None
            await lock_campaign_roster(session, actor_row.id)
            character = await session.scalar(
                select(Character).where(Character.id == actor_row.id).with_for_update()
            )
            quest = await self._quest(session, actor_row.id, P33_ID)
            world = await self._world(session, actor_row.id)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            if (
                quest.status != "active"
                or quest.content_version != P33_CONTENT_VERSION
                or quest.step != 6
                or quest.state_version != version
                or world.region != CONFINS_REGION
                or world.location != CONFINS_FRATURAS_LIMIAR_LABEL
                or not progress.get("codex_recorded")
                or not progress.get("avesso_interpreted")
            ):
                return self._p33_view(character, quest, world)

            event = await session.scalar(
                select(RewardEvent)
                .where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P33_REWARD_SOURCE,
                )
                .with_for_update()
            )
            if event is None:
                payload = materialize_equipment(
                    f"{P33_REWARD_SOURCE}:{character.id}:{item_id}",
                    "Raro",
                    55,
                    forced_name=item_name,
                    forced_slot=slot,
                    bound=True,
                )
                payload["catalog_item_id"] = item_id
                event = RewardEvent(character_id=character.id, source_id=P33_REWARD_SOURCE)
                session.add(event)
                await session.flush()
                character.xp += 87_650
                character.crowns += 920
                session.add_all(
                    (
                        RewardComponent(
                            reward_event_id=event.id, kind="xp", quantity=87_650
                        ),
                        RewardComponent(
                            reward_event_id=event.id, kind="crowns", quantity=920
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
                source_key = f"{P33_REWARD_SOURCE}:equipment"
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
                            item_level=55,
                            bound=True,
                            payload=instance,
                        )
                    )
                else:
                    await self.road._pending(
                        session, character.id, source_key, "equipment", payload
                    )
                progress.update(reward_choice=option_key, reward_item_id=item_id)
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
                        for key, values in P33_REWARD_OPTIONS.items()
                        if values[0] == chosen_id
                    ),
                    None,
                )
                if chosen is None:
                    raise RuntimeError("P33 reward event has no valid equipment choice")
                progress.update(reward_choice=chosen[0], reward_item_id=chosen_id)

            quest.status = "completed"
            progress.update(
                completed=True,
                completed_steps=sorted(set(progress.get("completed_steps", ())) | {6}),
            )
            quest.progress = progress
            quest.state_version += 1
            character.ruleset_version = CHARACTER_RULESET
            for unlock_id in (
                CONFINS_FRATURAS_HUNT_UNLOCK,
                CONFINS_FRATURAS_EXPLORE_UNLOCK,
                P33_NARRATIVE_UNLOCK,
            ):
                await self._ensure(
                    session, Unlock, character_id=character.id, unlock_id=unlock_id
                )
            await self._ensure(
                session,
                Achievement,
                character_id=character.id,
                achievement_id=P33_ACHIEVEMENT,
            )
            await self._ensure(
                session,
                CharacterCosmetic,
                character_id=character.id,
                cosmetic_id=P33_TITLE_COSMETIC,
                cosmetic_type="title",
                source_achievement_id=P33_ACHIEVEMENT,
            )
            await consolidate_character_level(session, character)
            await self._credit_p33(
                session,
                character.id,
                "p33.completed",
                f"p33.completed:{character.id}",
                {
                    "mission_id": P33_MISSION_ID,
                    "reward_item_id": progress.get("reward_item_id"),
                    "codex_entry_id": P33_CODEX_ENTRY,
                },
            )
            return self._p33_view(character, quest, world)

    async def _complete_p32(self, session, character, quest) -> None:
        for unlock_id in (
            CONFINS_ESTRADAS_HUNT_UNLOCK,
            CONFINS_ESTRADAS_EXPLORE_UNLOCK,
            P32_NARRATIVE_UNLOCK,
        ):
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=unlock_id
            )
        await self._ensure(
            session, Achievement, character_id=character.id, achievement_id=P32_ACHIEVEMENT
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P32_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P32_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 82_250
            character.crowns += 900
            materials = (
                (CONFINS_FERRO_BALIZA, 2, "ferro_baliza"),
                (CONFINS_MUSGO_LIMIAR, 1, "musgo_limiar"),
                (CONFINS_PO_REFERENCIA, 1, "po_referencia"),
            )
            session.add_all(
                [
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", quantity=82_250
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=900
                    ),
                    *[
                        RewardComponent(
                            reward_event_id=event.id,
                            kind="material",
                            item_id=material_id,
                            quantity=quantity,
                            payload={"material_id": material_id, "bound": True},
                        )
                        for material_id, quantity, _key in materials
                    ],
                ]
            )
            for material_id, quantity, key in materials:
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P32_REWARD_SOURCE}:material:{key}",
                    bound=True,
                )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        progress["completed_steps"] = list(range(1, 7))
        quest.status = "completed"
        quest.step = 6
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p32(
            session,
            character.id,
            "p32.completed",
            f"p32.completed:{character.id}",
            {"mission_id": P32_MISSION_ID, "codex_entry_id": P32_CODEX_ENTRY},
        )

    async def _advance_p31(
        self, session, character_ids, character, quest, world, version, action
    ) -> AltosMissionView:
        if (
            quest.status != "active"
            or quest.content_version != P31_CONTENT_VERSION
            or quest.state_version != version
            or world.region != CONFINS_REGION
            or await self._foreground(session, character.id)
        ):
            return await self._view(session, character, quest, world)

        if quest.step == 2 and world.location == CONFINS_MARCHA_LABEL and action in {
            "inspect_talen_marker",
            "inspect_ground_marker",
        }:
            members = await self._present_p31(
                session, character_ids, 2, CONFINS_MARCHA_LABEL
            )
            for member in members:
                progress = dict(member.quest.progress or {})
                evidence = set(progress.get("route_marker_evidence", ()))
                if action in evidence:
                    continue
                evidence.add(action)
                progress["route_marker_evidence"] = sorted(evidence)
                if len(evidence) == 2:
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {2}
                    )
                    member.quest.step = 3
                member.quest.progress = progress
                member.quest.state_version += 1
                await self._credit_p31(
                    session,
                    member.character.id,
                    f"p31.{action}",
                    f"p31.{action}:{member.character.id}",
                    {"location_id": CONFINS_MARCHA_LOCATION, "evidence_id": action},
                )
        elif (
            quest.step == 3
            and world.location == CONFINS_MARCHA_LABEL
            and action == "discover_marco_duplo"
        ):
            members = await self._present_p31(
                session, character_ids, 3, CONFINS_MARCHA_LABEL
            )
            for member in members:
                await self._ensure(
                    session,
                    Brazier,
                    character_id=member.character.id,
                    brazier_id=CONFINS_MARCO_DUPLO_BRAZIER,
                )
                progress = dict(member.quest.progress or {})
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {3}
                )
                progress["marco_duplo_brazier"] = True
                member.quest.progress = progress
                member.quest.step = 4
                member.quest.state_version += 1
                await self._credit_p31(
                    session,
                    member.character.id,
                    "p31.discovered_marco_duplo",
                    f"p31.discovered_marco_duplo:{member.character.id}",
                    {"brazier_id": CONFINS_MARCO_DUPLO_BRAZIER},
                )
        elif (
            quest.step == 6
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
            and action == "discover_testemunha"
        ):
            members = await self._present_p31(
                session, character_ids, 6, CONFINS_ULTIMO_REFUGIO_LABEL
            )
            for member in members:
                await self._ensure(
                    session,
                    Brazier,
                    character_id=member.character.id,
                    brazier_id=CONFINS_TESTEMUNHA_BRAZIER,
                )
                progress = dict(member.quest.progress or {})
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {6}
                )
                progress["testemunha_brazier"] = True
                member.quest.progress = progress
                member.quest.step = 7
                member.quest.state_version += 1
                await self._credit_p31(
                    session,
                    member.character.id,
                    "p31.discovered_testemunha",
                    f"p31.discovered_testemunha:{member.character.id}",
                    {"brazier_id": CONFINS_TESTEMUNHA_BRAZIER},
                )
        elif (
            quest.step == 7
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
            and action == "compare_dual_readings"
        ):
            progress = dict(quest.progress or {})
            if not progress.get("readings_compared"):
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {7}
                )
                progress["readings_compared"] = True
                quest.progress = progress
                quest.step = 8
                quest.state_version += 1
                await self._credit_p31(
                    session,
                    character.id,
                    "p31.readings_compared",
                    f"p31.readings_compared:{character.id}",
                    {"npc_ids": ("npc.confins.sera_nol", "npc.confins.roven_pell")},
                )
        elif (
            quest.step == 8
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
            and action == "record_p31_codex_and_conclude"
            and (quest.progress or {}).get("readings_compared")
        ):
            await self._ensure(
                session, CodexEntry, character_id=character.id, entry_id=P31_CODEX_ENTRY
            )
            await self._ensure(
                session,
                CodexFragment,
                character_id=character.id,
                entry_id=P31_CODEX_ENTRY,
                fragment_id=P31_CODEX_ENTRY,
            )
            progress = dict(quest.progress or {})
            progress["completed_steps"] = sorted(
                set(progress.get("completed_steps", ())) | {8}
            )
            progress["codex_recorded"] = True
            quest.progress = progress
            await self._complete_p31(session, character, quest)

        return await self._view(session, character, quest, world)

    async def _complete_p31(self, session, character, quest) -> None:
        for unlock_id in (
            CONFINS_MARCHA_HUNT_UNLOCK,
            CONFINS_MARCHA_EXPLORE_UNLOCK,
            P31_NARRATIVE_UNLOCK,
        ):
            await self._ensure(
                session, Unlock, character_id=character.id, unlock_id=unlock_id
            )
        await self._ensure(
            session, Achievement, character_id=character.id, achievement_id=P31_ACHIEVEMENT
        )
        await self._ensure(
            session,
            CharacterCosmetic,
            character_id=character.id,
            cosmetic_id=P31_TITLE_COSMETIC,
            cosmetic_type="title",
            source_achievement_id=P31_ACHIEVEMENT,
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P31_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=P31_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += 77_050
            character.crowns += 860
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", quantity=77_050
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=860
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=CONFINS_FERRO_BALIZA,
                        quantity=1,
                        payload={"material_id": CONFINS_FERRO_BALIZA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=CONFINS_MUSGO_LIMIAR,
                        quantity=1,
                        payload={"material_id": CONFINS_MUSGO_LIMIAR, "bound": True},
                    ),
                )
            )
            await self.road.deliver_material(
                session,
                character,
                CONFINS_FERRO_BALIZA,
                1,
                f"{P31_REWARD_SOURCE}:material:ferro_baliza",
                bound=True,
            )
            await self.road.deliver_material(
                session,
                character,
                CONFINS_MUSGO_LIMIAR,
                1,
                f"{P31_REWARD_SOURCE}:material:musgo_limiar",
                bound=True,
            )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        progress["completed_steps"] = list(range(1, 9))
        quest.status = "completed"
        quest.step = 8
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p31(
            session,
            character.id,
            "p31.completed",
            f"p31.completed:{character.id}",
            {"mission_id": P31_MISSION_ID, "location_id": CONFINS_MARCHA_LOCATION},
        )

    async def advance(
        self, actor: int, version: int, action: str
    ) -> AltosMissionView | None:
        if action.startswith("choose_p36_reward_"):
            return await self.choose_p36_reward(
                actor, version, action.removeprefix("choose_p36_reward_")
            )
        if action == "activate_p35":
            return await self.start_p35(actor, version)
        if action == "activate_p34":
            return await self.start_p34(actor, version)
        if action == "activate_p33":
            return await self.start_p33(actor, version)
        if action.startswith("choose_p33_reward_"):
            return await self.choose_p33_reward(
                actor, version, action.removeprefix("choose_p33_reward_")
            )
        if action == "activate_p32":
            return await self.start_p32(actor, version)
        if action == "activate_p30":
            return await self.start_p30(actor, version)
        if action.startswith("choose_p30_reward_"):
            return await self.choose_p30_reward(
                actor, version, action.removeprefix("choose_p30_reward_")
            )
        if action == "receive_order":
            return await self.start_p26(actor, version)
        if action == "activate_p27":
            return await self.start_p27(actor, version)
        if action == "activate_p28":
            return await self.start_p28(actor, version)
        if action == "activate_p29":
            return await self.start_p29(actor, version)
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
            p36 = await self._quest(session, actor_row.id, P36_ID)
            if p36 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p36(
                    session, character_ids, character, p36, world, version, action
                )
            p35 = await self._quest(session, actor_row.id, P35_ID)
            if p35 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p35(
                    session, character_ids, character, p35, world, version, action
                )
            p34 = await self._quest(session, actor_row.id, P34_ID)
            if p34 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p34(
                    session, character_ids, character, p34, world, version, action
                )
            p33 = await self._quest(session, actor_row.id, P33_ID)
            if p33 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p33(
                    session, character_ids, character, p33, world, version, action
                )
            p32 = await self._quest(session, actor_row.id, P32_ID)
            if p32 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p32(
                    session, character_ids, character, p32, world, version, action
                )
            p31 = await self._quest(session, actor_row.id, P31_ID)
            if p31 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p31(
                    session, character_ids, character, p31, world, version, action
                )
            p30 = await self._quest(session, actor_row.id, P30_ID)
            if p30 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p30(
                    session, character_ids, character, p30, world, version, action
                )
            p29 = await self._quest(session, actor_row.id, P29_ID)
            if p29 is not None:
                if character is None or world is None:
                    return None
                return await self._advance_p29(
                    session, character_ids, character, p29, world, version, action
                )
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
            _content_id, _checkpoint, _location, _creature_id, _enemy_level, _category = profile
            if (
                quest.status != "active"
                or quest.content_version != _content_version(quest_id)
                or quest.step != _scripted_combat_step(quest_id)
                or quest.state_version != version
                or world.region != _mission_region(quest_id)
                or world.location not in _combat_locations(profile)
                or (quest_id == P31_ID and character.level < 51)
                or (
                    quest_id == S31_ID
                    and (
                        character.level < 52
                        or world.region != CONFINS_REGION
                        or world.location != CONFINS_MARCHA_LABEL
                        or not await self._quest_completed(
                            session, character.id, P31_ID
                        )
                    )
                )
                or (
                    quest_id == S32_ID
                    and (
                        character.level < 54
                        or world.region != CONFINS_REGION
                        or world.location != CONFINS_ESTRADAS_AUSENTES_LABEL
                        or not await self._quest_completed(
                            session, character.id, P32_ID
                        )
                    )
                )
                or (quest_id == P32_ID and character.level < 53)
                or (quest_id == P33_ID and character.level < 55)
                or (quest_id == P34_ID and character.level < 57)
                or (quest_id == P35_ID and character.level < 59)
                or (
                    quest_id == P36_ID
                    and (
                        character.level < 60
                        or not await self._quest_completed(session, character.id, P35_ID)
                        or not {1, 2}.issubset(
                            set((quest.progress or {}).get("completed_steps", ()))
                        )
                        or not (quest.progress or {}).get("chamber_entered")
                    )
                )
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
            if quest_id == P30_ID and not progress.get("encounter_started"):
                progress.update(
                    encounter_started=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    ),
                )
                await self._credit_p30(
                    session,
                    character.id,
                    "p30.encounter_started",
                    f"p30.encounter_started:{character.id}",
                    {"boss_id": ALTOS_COLOSSO_CINEREO, "mode": "solo"},
                )
            elif quest_id == S30_ID:
                progress["encounter_started"] = True
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {5}
                )
                await self._credit_s30(
                    session,
                    character.id,
                    "s30.custodian_faced",
                    "s30.custodian_faced",
                    {
                        "boss_id": "boss.altos.s30.custodio_ultimo_turno",
                        "mode": "solo",
                    },
                )
            elif quest_id == P36_ID and not progress.get("encounter_started"):
                progress.update(
                    encounter_started=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    ),
                )
                await self._credit_p36(
                    session,
                    character.id,
                    "p36.regent_encounter_started",
                    f"p36.regent_encounter_started:{character.id}",
                    {"boss_id": P36_BOSS_ID, "mode": "solo", "confirmed": True},
                )
            quest.progress = progress
            quest.state_version += 1
            return await self._view(session, character, quest, world)

    async def retry_combat(
        self, actor: int, version: int, quest_id: str = P25_ID
    ) -> AltosMissionView | None:
        if quest_id in {P30_ID, P36_ID}:
            return await self._retry_p30_combat(actor, version, quest_id)
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
                or (quest_id == S30_ID and world.location != ALTOS_BASTILHA_LABEL)
                or (
                    quest_id == P31_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_MARCHA_LABEL
                    )
                )
                or (
                    quest_id == S31_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_MARCHA_LABEL
                        or character.level < 52
                        or not await self._quest_completed(
                            session, character.id, P31_ID
                        )
                    )
                )
                or (
                    quest_id == S32_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_ESTRADAS_AUSENTES_LABEL
                        or character.level < 54
                        or not await self._quest_completed(
                            session, character.id, P32_ID
                        )
                    )
                )
                or (
                    quest_id == P32_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_ESTRADAS_AUSENTES_LABEL
                        or character.level < 53
                    )
                )
                or (
                    quest_id == P33_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_FRATURAS_LIMIAR_LABEL
                        or character.level < 55
                    )
                )
                or (
                    quest_id == P34_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_NO_CENTRAL_LABEL
                        or character.level < 57
                    )
                )
                or (
                    quest_id == P35_ID
                    and (
                        world.region != CONFINS_REGION
                        or world.location != CONFINS_NO_CENTRAL_LABEL
                        or character.level < 59
                    )
                )
                or (
                    quest_id == P36_ID
                    and not await self._p36_individually_eligible(session, character)
                )
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

    async def _retry_p30_combat(
        self, actor: int, version: int, quest_id: str = P30_ID
    ) -> AltosMissionView | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            await lock_campaign_roster(session, seed.id)
            character = await session.scalar(
                select(Character).where(Character.id == seed.id).with_for_update()
            )
            quest = await self._quest(session, seed.id, quest_id)
            world = await self._world(session, seed.id)
            if character is None or quest is None or world is None:
                return None
            progress = dict(quest.progress or {})
            if (
                quest.status != "active"
                or quest.content_version != _content_version(quest_id)
                or quest.step != _scripted_combat_step(quest_id)
                or quest.state_version != version
                or not progress.get("awaiting_retry")
                or world.region != _mission_region(quest_id)
                or world.location not in _combat_locations(P25_COMBAT[quest_id])
                or (quest_id == P36_ID and character.level < 60)
                or (
                    quest_id == P36_ID
                    and not await self._p36_individually_eligible(session, character)
                )
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world)

            activity_text = progress.get("combat_activity_id")
            try:
                activity_id = UUID(str(activity_text))
            except (TypeError, ValueError) as error:
                raise RuntimeError(
                    f"{quest_id} retry is missing its persistent combat identity"
                ) from error

            shared_seed = await session.scalar(
                select(CampaignSharedEncounterMember).where(
                    CampaignSharedEncounterMember.game_activity_id == activity_id,
                    CampaignSharedEncounterMember.character_id == character.id,
                )
            )
            if shared_seed is not None:
                locked = await lock_campaign_encounter(session, activity_id, character.id)
                if locked is None or locked.encounter.status != "failed":
                    return await self._view(session, character, quest, world)
                journey = await session.get(
                    CampaignJourney, locked.encounter.journey_id, with_for_update=True
                )
                snapshot = (
                    (journey.context_payload or {}).get(
                        f"{quest_id.lower()}_initial_combat_snapshot"
                    )
                    if journey is not None
                    else None
                )
                if not isinstance(snapshot, dict):
                    raise RuntimeError(f"{quest_id} group retry is missing its frozen encounter")
                combat = decode(
                    snapshot,
                    locked.encounter.id,
                    locked.encounter.ruleset_version,
                    locked.encounter.state_version + 1,
                )
                for roster_member in locked.members:
                    participant = locked.characters[roster_member.character_id]
                    fighter = combat.fighters.get(roster_member.actor_key)
                    if fighter is not None:
                        fighter.hp = min(fighter.stats.hp, participant.hp)
                    roster_activity = locked.activities[roster_member.game_activity_id]
                    roster_activity.status = "active"
                    roster_activity.state_version = combat.version
                    roster_activity.last_valid_action_at = datetime.now(UTC)
                    roster_member.result = None
                    roster_member.settlement_state = "pending"
                    roster_member.settled_at = None
                    member_quest = await self._quest(
                        session, participant.id, quest_id
                    )
                    if (
                        roster_member.role == "eligible"
                        and member_quest is not None
                        and member_quest.status == "active"
                        and member_quest.step == _scripted_combat_step(quest_id)
                    ):
                        member_progress = dict(member_quest.progress or {})
                        member_progress.pop("awaiting_retry", None)
                        member_quest.progress = member_progress
                        member_quest.state_version += 1
                    if journey is not None:
                        journey_member = await session.get(
                            CampaignJourneyMember,
                            (journey.id, participant.id),
                            with_for_update=True,
                        )
                        if journey_member is not None:
                            journey_member.status = "active"
                locked.encounter.combat_snapshot = encode(combat)
                locked.encounter.state_version = combat.version
                locked.encounter.status = "active"
                locked.encounter.resolved_at = None
                if journey is not None:
                    journey.status = "active"
                    journey.updated_at = datetime.now(UTC)
                    journey.revision += 1
                proposal = (
                    await session.get(
                        GroupActivityProposal,
                        locked.encounter.proposal_id,
                        with_for_update=True,
                    )
                    if locked.encounter.proposal_id is not None
                    else None
                )
                if proposal is not None:
                    proposal.status = "started"
                    proposal.finished_at = None
                    proposal.revision += 1
                    reservations = list(
                        (
                            await session.scalars(
                                select(GroupActivityParticipant)
                                .where(
                                    GroupActivityParticipant.proposal_id == proposal.id
                                )
                                .with_for_update()
                            )
                        ).all()
                    )
                    for reservation in reservations:
                        reservation.reservation_state = "active"
                progress.pop("awaiting_retry", None)
                quest.progress = progress
                quest.state_version += 1
            else:
                activity = await session.scalar(
                    select(GameActivity)
                    .where(
                        GameActivity.id == activity_id,
                        GameActivity.character_id == character.id,
                        GameActivity.status == "failed",
                    )
                    .with_for_update()
                )
                if activity is None:
                    return await self._view(session, character, quest, world)
                _encounter, record = await CombatRepository(session).combat(activity)
                snapshot = progress.get("initial_combat_snapshot")
                if not isinstance(snapshot, dict):
                    raise RuntimeError(f"{quest_id} retry is missing its frozen encounter")
                combat = decode(
                    snapshot,
                    record.id,
                    activity.ruleset_version,
                    activity.state_version + 1,
                )
                if "player" in combat.fighters:
                    combat.fighters["player"].hp = min(
                        combat.fighters["player"].stats.hp, character.hp
                    )
                record.snapshot = encode(combat)
                activity.status = "active"
                activity.state_version = combat.version
                activity.last_valid_action_at = datetime.now(UTC)
                progress.pop("awaiting_retry", None)
                quest.progress = progress
                quest.state_version += 1
            await session.flush()
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
        spec = CreatureCombatantSpec(
            creature_for(creature_id),
            enemy_level,
            "enemy",
            None,
            campaign_boss_group_size=1 if quest_id in {P30_ID, P36_ID, S30_ID} else None,
        )
        combat = create_creature_party_combat(
            uuid4(),
            character.name,
            character.character_class,
            character.race,
            character.hp,
            (spec,),
            player_level=character.level,
            equipment_configuration=equipment,
            ruleset_version=RULESET,
            active_art_ids=arts.art_ids,
        )
        if quest_id == P30_ID:
            combat = configure_colossus_encounter(combat)
        elif quest_id == P36_ID:
            combat = configure_regent_encounter(combat)
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | arts.to_data()
        activity, _encounter, _record = await CombatRepository(session).create(
            character, content_id, combat
        )
        if quest_id in {P30_ID, P36_ID}:
            quest = await self._quest(session, character.id, quest_id)
            if quest is not None:
                progress = dict(quest.progress or {})
                progress.setdefault("initial_combat_snapshot", encode(combat))
                progress["combat_activity_id"] = str(activity.id)
                quest.progress = progress
        await self.road._bestiary(
            session,
            character.id,
            creature_id,
            victory=False,
            evidence_id=(
                "habitat:location.altos.bastilha_carga" if quest_id == S30_ID else None
            ),
            evidence_category="habitat" if quest_id == S30_ID else None,
            evidence_points=3 if quest_id == S30_ID else 0,
            observation_category=category,
        )
        if quest_id == P36_ID:
            await self._record_p36_bestiary_state(session, character.id, combat)
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
        content_id, checkpoint, _location, _creature_id, _enemy_level, _category = (
            P25_COMBAT[quest_id]
        )
        if initial.location not in _combat_locations(P25_COMBAT[quest_id]):
            return initial
        proposal = await self.groups.propose_activity(
            actor,
            activity_type="campaign_altos",
            participant_character_ids=tuple(member.character_id for member in group.members),
            eligibility_resolver=self._combat_eligibility,
            context_payload={
                "quest_id": quest_id,
                "checkpoint": checkpoint,
                "content_id": content_id,
                "location": initial.location,
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
        self,
        actor: int,
        proposal_id: UUID,
        *,
        expected_revision: int,
        quest_id: str | None = None,
    ) -> AltosMissionView | None:
        if self.groups is None:
            return await self.resume(actor, quest_id or P25_ID)
        proposal = await self.groups.activity_proposal(actor, proposal_id)
        proposal_quest_id = (proposal.context_payload or {}).get("quest_id")
        if proposal_quest_id in P25_COMBAT:
            quest_id = proposal_quest_id
        elif quest_id not in P25_COMBAT:
            quest_id = P25_ID
        await self.groups.start_activity(
            actor,
            proposal_id,
            expected_revision=expected_revision,
            eligibility_resolver=self._combat_eligibility,
            create_activity=self._create_group_combat,
        )
        return await self.resume(actor, quest_id)

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
        allowed_locations = _combat_locations(profile) if profile is not None else ()
        requested_location = payload.get("location")
        if requested_location is None and len(allowed_locations) == 1:
            requested_location = allowed_locations[0]
        world = await self._world(session, character.id, lock=False)
        active = await self._foreground(session, character.id)
        content_version = _content_version(quest_id)
        if (
            quest_id == P36_ID
            and quest is None
            and world is not None
            and world.region == CONFINS_REGION
            and world.location == CONFINS_CAMARA_REGENCIA_LABEL
            and character.level >= 60
        ):
            quest = await self._ensure_p36_quest(session, character, world)
            if quest is not None and quest.status == "active" and quest.step == 1:
                progress = dict(quest.progress or {})
                if not progress.get("chamber_entered"):
                    progress["chamber_entered"] = True
                    quest.progress = progress
                    quest.state_version += 1
                    await self._ensure(
                        session,
                        LocationDiscovery,
                        character_id=character.id,
                        location_id=CONFINS_CAMARA_REGENCIA_LOCATION,
                    )
                    await self._credit_p36(
                        session,
                        character.id,
                        "p36.chamber_entered",
                        f"p36.chamber_entered:{character.id}",
                        {"location_id": CONFINS_CAMARA_REGENCIA_LOCATION},
                    )
        if (
            active is not None
            or world is None
            or world.region != _mission_region(quest_id)
            or world.location != requested_location
            or requested_location not in allowed_locations
        ):
            role = "ineligible"
        elif quest_id == P31_ID and character.level < 51:
            role = "ineligible"
        elif (
            quest_id == S31_ID
            and (
                character.level < 52
                or not await self._quest_completed(session, character.id, P31_ID)
            )
        ):
            role = "ineligible"
        elif (
            quest_id == S32_ID
            and (
                character.level < 54
                or not await self._quest_completed(session, character.id, P32_ID)
            )
        ):
            role = "ineligible"
        elif quest_id == P32_ID and character.level < 53:
            role = "ineligible"
        elif quest_id == P33_ID and character.level < 55:
            role = "ineligible"
        elif quest_id == P34_ID and character.level < 57:
            role = "ineligible"
        elif quest_id == P35_ID and character.level < 59:
            role = "ineligible"
        elif (
            quest_id == P36_ID
            and (
                not await self._p36_individually_eligible(session, character)
                or quest is None
                or not {1, 2}.issubset(
                    set((quest.progress or {}).get("completed_steps", ()))
                )
                or not (quest.progress or {}).get("chamber_entered")
            )
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
        enemy_spec = CreatureCombatantSpec(
            creature_for(creature_id),
            enemy_level,
            "enemy",
            None,
            campaign_boss_group_size=(
                len(characters) if quest_id in {P30_ID, P36_ID, S30_ID} else None
            ),
        )
        combat = create_creature_party_combat(
            uuid4(),
            lead.name,
            lead.character_class,
            lead.race,
            lead.hp,
            (enemy_spec,),
            player_level=lead.level,
            equipment_configuration=lead_equipment,
            ruleset_version=RULESET,
            party=tuple(party),
        )
        if quest_id == P30_ID:
            combat = configure_colossus_encounter(combat)
        elif quest_id == P36_ID:
            combat = configure_regent_encounter(combat)
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
            campaign_boss=quest_id in {P30_ID, P36_ID, S30_ID},
        )
        if quest_id == P30_ID and encounter.journey_id is not None:
            journey = await session.get(
                CampaignJourney, encounter.journey_id, with_for_update=True
            )
            if journey is not None:
                journey.context_payload = {
                    **(journey.context_payload or {}),
                    "p30_initial_combat_snapshot": encode(combat),
                }
            encounter_members = list(
                (
                    await session.scalars(
                        select(CampaignSharedEncounterMember).where(
                            CampaignSharedEncounterMember.shared_encounter_id
                            == encounter.id
                        )
                    )
                ).all()
            )
            member_by_character = {
                member.character_id: member for member in encounter_members
            }
            for roster_member in roster:
                if roster_member.role != "eligible":
                    continue
                participant_quest = await self._quest(
                    session, roster_member.character.id, P30_ID
                )
                encounter_member = member_by_character.get(
                    roster_member.character.id
                )
                if participant_quest is None or encounter_member is None:
                    continue
                progress = dict(participant_quest.progress or {})
                progress.setdefault("initial_combat_snapshot", encode(combat))
                progress["combat_activity_id"] = str(
                    encounter_member.game_activity_id
                )
                progress["campaign_encounter_id"] = str(encounter.id)
                if not progress.get("encounter_started"):
                    progress.update(
                        encounter_started=True,
                        completed_steps=sorted(
                            set(progress.get("completed_steps", ())) | {4}
                        ),
                    )
                    await self._credit_p30(
                        session,
                        roster_member.character.id,
                        "p30.encounter_started",
                        f"p30.encounter_started:{roster_member.character.id}",
                        {"boss_id": ALTOS_COLOSSO_CINEREO, "mode": "group"},
                    )
                participant_quest.progress = progress
                participant_quest.state_version += 1
        elif quest_id == P36_ID and encounter.journey_id is not None:
            journey = await session.get(
                CampaignJourney, encounter.journey_id, with_for_update=True
            )
            if journey is not None:
                journey.context_payload = {
                    **(journey.context_payload or {}),
                    "p36_initial_combat_snapshot": encode(combat),
                }
            encounter_members = list(
                (
                    await session.scalars(
                        select(CampaignSharedEncounterMember).where(
                            CampaignSharedEncounterMember.shared_encounter_id
                            == encounter.id
                        )
                    )
                ).all()
            )
            member_by_character = {
                member.character_id: member for member in encounter_members
            }
            for roster_member in roster:
                if roster_member.role != "eligible":
                    continue
                participant = roster_member.character
                participant_quest = await self._quest(session, participant.id, P36_ID)
                encounter_member = member_by_character.get(participant.id)
                if participant_quest is None or encounter_member is None:
                    continue
                progress = dict(participant_quest.progress or {})
                progress.setdefault("initial_combat_snapshot", encode(combat))
                progress.update(
                    combat_activity_id=str(encounter_member.game_activity_id),
                    campaign_encounter_id=str(encounter.id),
                    encounter_started=True,
                    completed_steps=sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    ),
                )
                participant_quest.progress = progress
                participant_quest.state_version += 1
                await self._credit_p36(
                    session,
                    participant.id,
                    "p36.regent_encounter_started",
                    f"p36.regent_encounter_started:{participant.id}",
                    {"boss_id": P36_BOSS_ID, "mode": "group", "confirmed": True},
                )
        elif quest_id == S30_ID:
            for roster_member in roster:
                if roster_member.role != "eligible":
                    continue
                participant_quest = await self._quest(
                    session, roster_member.character.id, S30_ID
                )
                if (
                    participant_quest is None
                    or participant_quest.status != "active"
                    or participant_quest.step != 5
                ):
                    continue
                progress = dict(participant_quest.progress or {})
                progress["encounter_started"] = True
                progress["completed_steps"] = sorted(
                    set(progress.get("completed_steps", ())) | {5}
                )
                participant_quest.progress = progress
                participant_quest.state_version += 1
                await self._credit_s30(
                    session,
                    roster_member.character.id,
                    "s30.custodian_faced",
                    "s30.custodian_faced",
                    {
                        "boss_id": "boss.altos.s30.custodio_ultimo_turno",
                        "mode": "group",
                    },
                )
        for member in roster:
            await self.road._bestiary(
                session,
                member.character.id,
                creature_id,
                victory=False,
                evidence_id=(
                    "habitat:location.altos.bastilha_carga"
                    if quest_id == S30_ID
                    else None
                ),
                evidence_category="habitat" if quest_id == S30_ID else None,
                evidence_points=3 if quest_id == S30_ID else 0,
                observation_category=category,
            )
            if quest_id == P36_ID:
                await self._record_p36_bestiary_state(session, member.character.id, combat)
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
            if quest_id == P36_ID:
                await self._record_p36_bestiary_state(session, character.id, updated)
            progress = dict(quest.progress or {})
            if updated.result == "victory":
                activity.status = "completed"
                progress.update(combat_result="victory", awaiting_retry=False)
                character.ruleset_version = CHARACTER_RULESET
                await self.road._bestiary(
                    session,
                    character.id,
                    creature_id,
                    victory=True,
                    observation_category=category,
                )
                if quest_id == P36_ID:
                    await consolidate_character_level(session, character)
                if quest_id == P30_ID:
                    quest.step = 7
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {5, 6}
                    )
                    progress["first_valid_victory"] = True
                    progress["first_core_claimed"] = await self._claim_p30_core(
                        session, character
                    ) or progress.get("first_core_claimed", False)
                    await self._credit_p30(
                        session,
                        character.id,
                        "p30.colossus_defeated",
                        f"p30.colossus_defeated:{character.id}",
                        {"boss_id": ALTOS_COLOSSO_CINEREO, "victory": True},
                    )
                elif quest_id == S30_ID:
                    quest.step = 7
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {5, 6}
                    )
                    await self._credit_s30(
                        session,
                        character.id,
                        "s30.custodian_defeated",
                        "s30.custodian_defeated",
                        {"boss_id": "boss.altos.s30.custodio_ultimo_turno", "victory": True},
                    )
                elif quest_id == S31_ID:
                    quest.step = 5
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    )
                    await self._credit_s31(
                        session,
                        character.id,
                        "s31.gralha_defeated",
                        "s31.gralha_defeated",
                        {
                            "creature_id": creature_id,
                            "enemy_level": enemy_level,
                            "mission_scripted": True,
                            "variant": False,
                            "economy_zero": True,
                        },
                    )
                elif quest_id == S32_ID:
                    quest.step = 5
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    )
                    await self._credit_s32(
                        session,
                        character.id,
                        "s32.aranha_defeated",
                        "s32.aranha_defeated",
                        {
                            "creature_id": creature_id,
                            "enemy_level": enemy_level,
                            "mission_scripted": True,
                            "variant": False,
                            "economy_zero": True,
                        },
                    )
                elif quest_id == P31_ID:
                    quest.step = 5
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    )
                    progress["cao_nevoa_victory"] = True
                    await self._credit_p31(
                        session,
                        character.id,
                        "p31.scripted_cao_victory",
                        f"p31.scripted_cao_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
                elif quest_id == P32_ID:
                    quest.step = 5
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {4}
                    )
                    progress["scripted_andarilho_victory"] = True
                    progress["andarilho_not_clone_nor_soul_observed"] = True
                    await self._credit_p32(
                        session,
                        character.id,
                        "p32.scripted_andarilho_victory",
                        f"p32.scripted_andarilho_victory:{character.id}",
                        {
                            "creature_id": creature_id,
                            "enemy_level": enemy_level,
                            "finding": "not_clone_nor_soul",
                        },
                    )
                elif quest_id == P33_ID:
                    quest.step = 4
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    )
                    progress["scripted_casca_victory"] = True
                    await self._credit_p33(
                        session,
                        character.id,
                        "p33.scripted_casca_victory",
                        f"p33.scripted_casca_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
                elif quest_id == P34_ID:
                    quest.step = 4
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    )
                    progress["scripted_custodio_victory"] = True
                    await self._credit_p34(
                        session,
                        character.id,
                        "p34.scripted_custodio_victory",
                        f"p34.scripted_custodio_victory:{character.id}",
                        {
                            "creature_id": creature_id,
                            "enemy_level": enemy_level,
                            "mission_scripted": True,
                            "economy_zero": True,
                        },
                    )
                elif quest_id == P35_ID:
                    quest.step = 4
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    )
                    progress["scripted_vigia_victory"] = True
                    await self._credit_p35(
                        session,
                        character.id,
                        "p35.scripted_vigia_victory",
                        f"p35.scripted_vigia_victory:{character.id}",
                        {
                            "creature_id": creature_id,
                            "enemy_level": enemy_level,
                            "mission_scripted": True,
                            "variant": False,
                            "economy_zero": True,
                        },
                    )
                elif quest_id == P36_ID:
                    quest.step = 6
                    progress.update(
                        completed_steps=sorted(
                            set(progress.get("completed_steps", ())) | {3, 4, 5}
                        ),
                        first_valid_victory=True,
                        awaiting_retry=False,
                    )
                    claimed = await self._claim_p36_core(session, character)
                    progress["first_core_claimed"] = (
                        claimed or progress.get("first_core_claimed", False)
                    )
                    if claimed:
                        await self._ensure(
                            session,
                            Achievement,
                            character_id=character.id,
                            achievement_id=P36_FIRST_VICTORY_ACHIEVEMENT,
                        )
                        await self._ensure(
                            session,
                            CharacterCosmetic,
                            character_id=character.id,
                            cosmetic_id=P36_FIRST_VICTORY_FRAME,
                            cosmetic_type="frame",
                            source_achievement_id=P36_FIRST_VICTORY_ACHIEVEMENT,
                        )
                    await self._credit_p36(
                        session,
                        character.id,
                        "p36.regent_defeated",
                        f"p36.regent_defeated:{character.id}",
                        {"boss_id": P36_BOSS_ID, "first_victory": claimed},
                    )
                else:
                    quest.step = _scripted_combat_step(quest_id) + 1
                if quest_id in {
                    P30_ID,
                    S31_ID,
                    S32_ID,
                    P31_ID,
                    P32_ID,
                    P33_ID,
                    P34_ID,
                    P35_ID,
                }:
                    pass
                elif quest_id == S30_ID:
                    pass
                elif quest_id == P29_ID:
                    await self._credit_p29(
                        session,
                        character.id,
                        "p29.scripted_supervisor_victory",
                        f"p29.scripted_supervisor_victory:{character.id}",
                        {"creature_id": creature_id, "enemy_level": enemy_level},
                    )
                elif quest_id == P28_ID:
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
                elif quest_id == S26_ID:
                    await self._credit_s26(
                        session,
                        character.id,
                        "s26.scripted_carneiro_victory",
                        f"s26.scripted_carneiro_victory:{character.id}",
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
                if quest_id == P30_ID:
                    character.hp = character.max_hp
                    world.region = ALTOS_REGION
                    world.location = ALTOS_ABRIGO_LABEL
                    progress["recovery_brazier"] = ALTOS_ABRIGO_BRAZIER
                elif quest_id == S30_ID:
                    character.hp = character.max_hp
                    world.region = ALTOS_REGION
                    world.location = ALTOS_ABRIGO_LABEL
                    progress["recovery_brazier"] = ALTOS_ABRIGO_BRAZIER
                elif quest_id == P36_ID:
                    character.hp = character.max_hp
                    world.region = CONFINS_REGION
                    world.location = CONFINS_ULTIMO_REFUGIO_LABEL
                    progress["recovery_brazier"] = CONFINS_TESTEMUNHA_BRAZIER
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
                if quest_id == P36_ID:
                    await self._record_p36_bestiary_state(
                        session, character_id, updated
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
                            progress.update(combat_result="victory", awaiting_retry=False)
                            participant.ruleset_version = CHARACTER_RULESET
                            await self.road._bestiary(
                                session,
                                participant.id,
                                creature_id,
                                victory=True,
                                observation_category=category,
                            )
                            if quest_id == P36_ID:
                                await consolidate_character_level(session, participant)
                            if quest_id == P30_ID:
                                participant_quest.step = 7
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {5, 6}
                                )
                                progress["first_valid_victory"] = True
                                progress["first_core_claimed"] = (
                                    await self._claim_p30_core(session, participant)
                                    or progress.get("first_core_claimed", False)
                                )
                                await self._credit_p30(
                                    session,
                                    participant.id,
                                    "p30.colossus_defeated",
                                    f"p30.colossus_defeated:{participant.id}",
                                    {"boss_id": ALTOS_COLOSSO_CINEREO, "victory": True},
                                )
                            elif quest_id == S30_ID:
                                participant_quest.step = 7
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {5, 6}
                                )
                                await self._credit_s30(
                                    session,
                                    participant.id,
                                    "s30.custodian_defeated",
                                    "s30.custodian_defeated",
                                    {
                                        "boss_id": "boss.altos.s30.custodio_ultimo_turno",
                                        "victory": True,
                                    },
                                )
                            elif quest_id == S31_ID:
                                participant_quest.step = 5
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {4}
                                )
                                await self._credit_s31(
                                    session,
                                    participant.id,
                                    "s31.gralha_defeated",
                                    "s31.gralha_defeated",
                                    {
                                        "creature_id": creature_id,
                                        "enemy_level": enemy_level,
                                        "mission_scripted": True,
                                        "variant": False,
                                        "economy_zero": True,
                                    },
                                )
                            elif quest_id == S32_ID:
                                participant_quest.step = 5
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {4}
                                )
                                await self._credit_s32(
                                    session,
                                    participant.id,
                                    "s32.aranha_defeated",
                                    "s32.aranha_defeated",
                                    {
                                        "creature_id": creature_id,
                                        "enemy_level": enemy_level,
                                        "mission_scripted": True,
                                        "variant": False,
                                        "economy_zero": True,
                                    },
                                )
                            elif quest_id == P31_ID:
                                participant_quest.step = 5
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {4}
                                )
                                progress["cao_nevoa_victory"] = True
                                await self._credit_p31(
                                    session,
                                    participant.id,
                                    "p31.scripted_cao_victory",
                                    f"p31.scripted_cao_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                            elif quest_id == P32_ID:
                                participant_quest.step = 5
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {4}
                                )
                                progress["scripted_andarilho_victory"] = True
                                progress["andarilho_not_clone_nor_soul_observed"] = True
                                await self._credit_p32(
                                    session,
                                    participant.id,
                                    "p32.scripted_andarilho_victory",
                                    f"p32.scripted_andarilho_victory:{participant.id}",
                                    {
                                        "creature_id": creature_id,
                                        "enemy_level": enemy_level,
                                        "finding": "not_clone_nor_soul",
                                    },
                                )
                            elif quest_id == P33_ID:
                                participant_quest.step = 4
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {3}
                                )
                                progress["scripted_casca_victory"] = True
                                await self._credit_p33(
                                    session,
                                    participant.id,
                                    "p33.scripted_casca_victory",
                                    f"p33.scripted_casca_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                            elif quest_id == P34_ID:
                                participant_quest.step = 4
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {3}
                                )
                                progress["scripted_custodio_victory"] = True
                                await self._credit_p34(
                                    session,
                                    participant.id,
                                    "p34.scripted_custodio_victory",
                                    f"p34.scripted_custodio_victory:{participant.id}",
                                    {
                                        "creature_id": creature_id,
                                        "enemy_level": enemy_level,
                                        "mission_scripted": True,
                                        "economy_zero": True,
                                    },
                                )
                            elif quest_id == P35_ID:
                                participant_quest.step = 4
                                progress["completed_steps"] = sorted(
                                    set(progress.get("completed_steps", ())) | {3}
                                )
                                progress["scripted_vigia_victory"] = True
                                await self._credit_p35(
                                    session,
                                    participant.id,
                                    "p35.scripted_vigia_victory",
                                    f"p35.scripted_vigia_victory:{participant.id}",
                                    {
                                        "creature_id": creature_id,
                                        "enemy_level": enemy_level,
                                        "mission_scripted": True,
                                        "variant": False,
                                        "economy_zero": True,
                                    },
                                )
                            elif quest_id == P36_ID:
                                participant_quest.step = 6
                                progress.update(
                                    completed_steps=sorted(
                                        set(progress.get("completed_steps", ()))
                                        | {3, 4, 5}
                                    ),
                                    first_valid_victory=True,
                                    awaiting_retry=False,
                                )
                                claimed = await self._claim_p36_core(
                                    session, participant
                                )
                                progress["first_core_claimed"] = (
                                    claimed
                                    or progress.get("first_core_claimed", False)
                                )
                                if claimed:
                                    await self._ensure(
                                        session,
                                        Achievement,
                                        character_id=participant.id,
                                        achievement_id=P36_FIRST_VICTORY_ACHIEVEMENT,
                                    )
                                    await self._ensure(
                                        session,
                                        CharacterCosmetic,
                                        character_id=participant.id,
                                        cosmetic_id=P36_FIRST_VICTORY_FRAME,
                                        cosmetic_type="frame",
                                        source_achievement_id=P36_FIRST_VICTORY_ACHIEVEMENT,
                                    )
                                await self._credit_p36(
                                    session,
                                    participant.id,
                                    "p36.regent_defeated",
                                    f"p36.regent_defeated:{participant.id}",
                                    {"boss_id": P36_BOSS_ID, "first_victory": claimed},
                                )
                            else:
                                participant_quest.step = _scripted_combat_step(quest_id) + 1
                            if quest_id in {
                                P30_ID,
                                S31_ID,
                                S32_ID,
                                P31_ID,
                                P32_ID,
                                P33_ID,
                                P34_ID,
                                P35_ID,
                            }:
                                pass
                            elif quest_id == S30_ID:
                                pass
                            elif quest_id == P29_ID:
                                await self._credit_p29(
                                    session,
                                    participant.id,
                                    "p29.scripted_supervisor_victory",
                                    f"p29.scripted_supervisor_victory:{participant.id}",
                                    {"creature_id": creature_id, "enemy_level": enemy_level},
                                )
                            elif quest_id == P28_ID:
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
                            elif quest_id == S26_ID:
                                await self._credit_s26(
                                    session,
                                    participant.id,
                                    "s26.scripted_carneiro_victory",
                                    f"s26.scripted_carneiro_victory:{participant.id}",
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
                            if quest_id == P30_ID:
                                participant.hp = participant.max_hp
                                participant_world = await self._world(
                                    session, participant.id
                                )
                                if participant_world is not None:
                                    participant_world.region = ALTOS_REGION
                                    participant_world.location = ALTOS_ABRIGO_LABEL
                                progress["recovery_brazier"] = ALTOS_ABRIGO_BRAZIER
                            elif quest_id == S30_ID:
                                participant.hp = participant.max_hp
                                participant_world = await self._world(
                                    session, participant.id
                                )
                                if participant_world is not None:
                                    participant_world.region = ALTOS_REGION
                                    participant_world.location = ALTOS_ABRIGO_LABEL
                            elif quest_id == P36_ID:
                                participant.hp = participant.max_hp
                                participant_world = await self._world(
                                    session, participant.id
                                )
                                if participant_world is not None:
                                    participant_world.region = CONFINS_REGION
                                    participant_world.location = CONFINS_ULTIMO_REFUGIO_LABEL
                                progress["recovery_brazier"] = CONFINS_TESTEMUNHA_BRAZIER
                        participant_quest.progress = progress
                        participant_quest.state_version += 1
                    elif updated.result == "defeat":
                        await normalize_character_hp(session, participant)
                        if quest_id == P30_ID:
                            participant.hp = participant.max_hp
                            participant_world = await self._world(
                                session, participant.id
                            )
                            if participant_world is not None:
                                participant_world.region = ALTOS_REGION
                                participant_world.location = ALTOS_ABRIGO_LABEL
                        elif quest_id == S30_ID:
                            participant.hp = participant.max_hp
                            participant_world = await self._world(
                                session, participant.id
                            )
                            if participant_world is not None:
                                participant_world.region = ALTOS_REGION
                                participant_world.location = ALTOS_ABRIGO_LABEL
                        elif quest_id == P36_ID:
                            participant.hp = participant.max_hp
                            participant_world = await self._world(
                                session, participant.id
                            )
                            if participant_world is not None:
                                participant_world.region = CONFINS_REGION
                                participant_world.location = CONFINS_ULTIMO_REFUGIO_LABEL
                if updated.result == "defeat" and quest_id in {P30_ID, P36_ID}:
                    await self._settle_p30_defeat(session, locked)
                else:
                    await settle_campaign_encounter(session, locked, updated.result)
            world = await self._world(session, character.id)
            return await self._view(session, character, quest, world)

    async def _settle_p30_defeat(self, session, locked) -> None:
        """Release P30 group reservations while keeping the campaign journey resumable."""
        now = datetime.now(UTC)
        encounter = locked.encounter
        journey = (
            await session.get(
                CampaignJourney, encounter.journey_id, with_for_update=True
            )
            if encounter.journey_id is not None
            else None
        )
        if journey is not None:
            journey.status = "paused"
            journey.updated_at = now
            journey.revision += 1
        for member in locked.members:
            member.settlement_state = "settled"
            member.settled_at = now
        if encounter.proposal_id is None:
            return
        proposal = await session.get(
            GroupActivityProposal, encounter.proposal_id, with_for_update=True
        )
        if proposal is not None and proposal.status == "started":
            proposal.status = "failed"
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
        for reservation in reservations:
            reservation.reservation_state = "released"

    async def campaign_action(
        self,
        actor: int,
        activity_id: UUID,
        version: int,
        action_index: int,
        target_code: str,
    ) -> AltosMissionView | None:
        view = await self.combat_view_for_actor(actor, activity_id)
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
        async with self.sessions() as session:
            activity = await session.get(GameActivity, activity_id)
            quest_id = next(
                (
                    mission_id
                    for mission_id, profile in P25_COMBAT.items()
                    if activity is not None and profile[0] == activity.content_id
                ),
                None,
            )
        if quest_id is None:
            return None
        view = await self.resume(actor, quest_id)
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

    async def _complete_p29(self, session, character, quest) -> None:
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=P29_NARRATIVE_UNLOCK,
        )
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=ALTOS_CORACAO_ACCESS_UNLOCK,
        )
        await self._ensure(
            session, CodexEntry, character_id=character.id, entry_id=P29_CODEX_ENTRY
        )
        await self._ensure(
            session,
            Achievement,
            character_id=character.id,
            achievement_id=P29_ACHIEVEMENT,
        )
        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P29_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(
                character_id=character.id,
                source_id=P29_REWARD_SOURCE,
            )
            session.add(event)
            await session.flush()
            character.xp += 72_000
            character.crowns += 1_050
            rewards = (
                ("xp", None, 72_000, {}),
                ("crowns", None, 1_050, {}),
                (
                    "material",
                    ALTOS_FERRO_CONTRAPESO,
                    2,
                    {"material_id": ALTOS_FERRO_CONTRAPESO, "bound": True},
                ),
                (
                    "material",
                    ALTOS_LIQUEN_PEDREIRA,
                    1,
                    {"material_id": ALTOS_LIQUEN_PEDREIRA, "bound": True},
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
                (ALTOS_LIQUEN_PEDREIRA, 1, "liquen_pedreira"),
                (ALTOS_CINZA_BASALTO, 1, "cinza_basalto"),
            ):
                await self.road.deliver_material(
                    session,
                    character,
                    material_id,
                    quantity,
                    f"{P29_REWARD_SOURCE}:material:{key}",
                    bound=True,
                )
        progress = dict(quest.progress or {})
        progress["completed"] = True
        quest.status = "completed"
        quest.state_version += 1
        quest.progress = progress
        character.ruleset_version = CHARACTER_RULESET
        await consolidate_character_level(session, character)
        await self._credit_p29(
            session,
            character.id,
            "p29.completed",
            f"p29.completed:{character.id}",
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

    async def _present_p29(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P29_ID,
            content_version=P29_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _present_p30(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P30_ID,
            content_version=P30_CONTENT_VERSION,
            step=step,
            region=ALTOS_REGION,
            location=location,
        )

    async def _present_p31(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P31_ID,
            content_version=P31_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
            location=location,
        )

    async def _present_p32(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P32_ID,
            content_version=P32_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
            location=location,
        )

    async def _present_p33(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P33_ID,
            content_version=P33_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
            location=location,
        )

    async def _present_p34(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P34_ID,
            content_version=P34_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
            location=location,
        )

    async def _present_p35(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P35_ID,
            content_version=P35_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
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

    async def _credit_p29(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P29_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p30(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P30_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p31(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P31_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p32(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P32_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p33(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P33_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p34(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P34_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_p35(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P35_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_s26(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S26_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _present_p36(self, session, character_ids, step, location):
        return await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=P36_ID,
            content_version=P36_CONTENT_VERSION,
            step=step,
            region=CONFINS_REGION,
            location=location,
        )

    async def _credit_p36(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=P36_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_s30(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S30_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_s31(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S31_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )

    async def _credit_s32(
        self, session, character_id, objective_id, source_key, evidence
    ):
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S32_ID,
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
