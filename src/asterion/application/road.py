"""Application services for the post-P1 Road hunt and exploration loop."""
# ruff: noqa: E501

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from hashlib import sha256
from types import SimpleNamespace
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.bestiary import BESTIARY_STAGE_LABELS, BestiaryRecorder
from asterion.application.chronicle_activities import desbravar_offer, settle_desbravar
from asterion.application.combat_configuration_guard import (
    CombatConfigurationLocked,
    lock_for_combat_configuration_mutation,
)
from asterion.application.equipment import equipment_instance_payload
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    reconcile_character_hp,
)
from asterion.application.inventory_capacity import (
    INVENTORY_CAPACITY,
    PENDING_CAPACITY,
    inventory_slots,
)
from asterion.application.progression import consolidate_character_level, level_xp
from asterion.application.vigor import reconcile_character_vigor
from asterion.domain.chronicle_content import REGIONS_BY_NAME, is_chronicle_result
from asterion.domain.combat import (
    CombatConsumableOption,
    act,
    active_player_key,
    combat_consumable_options,
    use_combat_consumable,
)
from asterion.domain.consumables import (
    ENCOUNTER_CONSUMABLE_LIMITS,
    ConsumableFamily,
)
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.equipment_modifications import equipment_grade
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.road import (
    ALTOS_ABRIGO,
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_ABRIGO_BRAZIER,
    ALTOS_ABRIGO_LOCATION,
    ALTOS_BASIC_MATERIAL_CREATURE_IDS,
    ALTOS_BASTILHA,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_BASTILHA_BRAZIER,
    ALTOS_BASTILHA_DUNGEON_UNLOCK,
    ALTOS_BASTILHA_EXPLORE_UNLOCK,
    ALTOS_BASTILHA_HUNT_UNLOCK,
    ALTOS_BASTILHA_LOCATION,
    ALTOS_CORACAO,
    ALTOS_CORACAO_ACCESS_UNLOCK,
    ALTOS_CORACAO_LOCATION,
    ALTOS_ESCARPA,
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_ESCARPA_BRAZIER,
    ALTOS_ESCARPA_EXPLORE_UNLOCK,
    ALTOS_ESCARPA_HUNT_UNLOCK,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_PEDREIRA_BRAZIER,
    ALTOS_PEDREIRAS,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_DUNGEON_UNLOCK,
    ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
    ALTOS_PEDREIRAS_HUNT_UNLOCK,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_PONTES,
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PONTES_BRAZIER,
    ALTOS_PONTES_EXPLORE_UNLOCK,
    ALTOS_PONTES_HUNT_UNLOCK,
    ALTOS_PONTES_LOCATION,
    ALTOS_REGION,
    BOSQUE_BRAZIER,
    BOSQUE_LOCATION,
    BOSQUE_ROUTE_UNLOCK,
    CHARNECA_BRAZIER,
    CHARNECA_LOCATION,
    CHARNECA_ROUTE_UNLOCK,
    CONFINS_ANDARILHO_REPETIDO,
    CONFINS_ARANHA_LIMIAR,
    CONFINS_ARQUIVO_RETORNO_DUNGEON_UNLOCK,
    CONFINS_BASIC_MATERIAL_CREATURE_IDS,
    CONFINS_CAMARA_CONTRADICOES_DUNGEON_UNLOCK,
    CONFINS_CAMARA_REGENCIA,
    CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
    CONFINS_CAMARA_REGENCIA_LOCATION,
    CONFINS_CAO_NEVOA,
    CONFINS_CASCA_REFLEXO,
    CONFINS_CERVO_PASSO_DUPLO,
    CONFINS_COURO_MARCHA,
    CONFINS_ESTRADA_CONFERIDA_BRAZIER,
    CONFINS_ESTRADAS_ACCESS_UNLOCK,
    CONFINS_ESTRADAS_AUSENTES,
    CONFINS_ESTRADAS_AUSENTES_LOCATION,
    CONFINS_ESTRADAS_EXPLORE_UNLOCK,
    CONFINS_ESTRADAS_HUNT_UNLOCK,
    CONFINS_FERRO_BALIZA,
    CONFINS_FRATURAS_ACCESS_UNLOCK,
    CONFINS_FRATURAS_EXPLORE_UNLOCK,
    CONFINS_FRATURAS_HUNT_UNLOCK,
    CONFINS_FRATURAS_LIMIAR,
    CONFINS_FRATURAS_LIMIAR_LOCATION,
    CONFINS_GRALHA_DUAS_SOMBRAS,
    CONFINS_LIMIAR_FIRME_BRAZIER,
    CONFINS_MARCHA,
    CONFINS_MARCHA_ACCESS_UNLOCK,
    CONFINS_MARCHA_EXPLORE_UNLOCK,
    CONFINS_MARCHA_HUNT_UNLOCK,
    CONFINS_MARCHA_LOCATION,
    CONFINS_MARCO_DUPLO_BRAZIER,
    CONFINS_MARIPOSA_SEM_HORIZONTE,
    CONFINS_MUSGO_LIMIAR,
    CONFINS_NO_CENTRAL,
    CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
    CONFINS_NO_CENTRAL_EXPLORE_UNLOCK,
    CONFINS_NO_CENTRAL_HUNT_UNLOCK,
    CONFINS_NO_CENTRAL_LOCATION,
    CONFINS_NO_RETORNO_BRAZIER,
    CONFINS_PO_REFERENCIA,
    CONFINS_REGION,
    CONFINS_REGION_UNLOCK,
    CONFINS_SANGUESSUGA_PALIDA,
    CONFINS_TESTEMUNHA_BRAZIER,
    CONFINS_ULTIMO_REFUGIO,
    CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK,
    CONFINS_ULTIMO_REFUGIO_LOCATION,
    CONFINS_VIGIA_DESFASADO,
    EXPLORATION_PROFILES,
    LOCATION_LEVEL_BANDS,
    MATERIAL_POOLS,
    NARETH_BASIC_MATERIAL_CREATURE_IDS,
    NARETH_BRAZIER_CAMPOS,
    NARETH_BRAZIER_CANAIS,
    NARETH_BRAZIER_HORIZONTE,
    NARETH_BRAZIER_OBSERVATORIO,
    NARETH_BRAZIER_POSTO,
    NARETH_CAMARA,
    NARETH_CAMARA_LOCATION,
    NARETH_CAMPINAS,
    NARETH_CAMPINAS_LOCATION,
    NARETH_CAMPINAS_POSTO_ROUTE,
    NARETH_CAMPOS,
    NARETH_CAMPOS_LOCATION,
    NARETH_CAMPOS_OBSERVATORIO_ROUTE,
    NARETH_CANAIS,
    NARETH_CANAIS_CAMPOS_ROUTE,
    NARETH_CANAIS_LOCATION,
    NARETH_EXPLORE_UNLOCK,
    NARETH_OBSERVATORIO,
    NARETH_OBSERVATORIO_CAMARA_ROUTE,
    NARETH_OBSERVATORIO_LOCATION,
    NARETH_POSTO,
    NARETH_POSTO_CANAIS_ROUTE,
    NARETH_POSTO_LOCATION,
    NARETH_REGION_UNLOCK,
    ROAD_EXPLORATION_PROFILE,
    ROAD_LOCATION,
    RUINS_BRAZIER,
    RUINS_LOCATION,
    RUINS_ROUTE_UNLOCK,
    RULESET,
    VARZEAS_BASIC_MATERIAL_CREATURE_IDS,
    VARZEAS_BREJOS,
    VARZEAS_BREJOS_BRAZIER,
    VARZEAS_BREJOS_EXPLORE_UNLOCK,
    VARZEAS_BREJOS_HORTOS_ROUTE,
    VARZEAS_BREJOS_HUNT_UNLOCK,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_CAMARA,
    VARZEAS_CAMARA_ACCESS_UNLOCK,
    VARZEAS_CAMARA_LOCATION,
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
    VARZEAS_HORTOS,
    VARZEAS_HORTOS_BRAZIER,
    VARZEAS_HORTOS_EXPLORE_UNLOCK,
    VARZEAS_HORTOS_GALERIAS_ROUTE,
    VARZEAS_HORTOS_HUNT_UNLOCK,
    VARZEAS_HORTOS_LOCATION,
    VARZEAS_PORTO,
    VARZEAS_PORTO_BRAZIER,
    VARZEAS_PORTO_BREJOS_ROUTE,
    VARZEAS_PORTO_LOCATION,
    VARZEAS_REGION_ENTRY_UNLOCK,
    VDE_BAIXIOS_BRAZIER,
    VDE_BAIXIOS_CLAUSTRO_ROUTE,
    VDE_BAIXIOS_LOCATION,
    VDE_BASIC_MATERIAL_CREATURE_IDS,
    VDE_BERCO_LOCATION,
    VDE_CLAUSTRO_BERCO_ROUTE,
    VDE_CLAUSTRO_BRAZIER,
    VDE_CLAUSTRO_LOCATION,
    VDE_GARGANTA_BRAZIER,
    VDE_GARGANTA_LOCATION,
    VDE_GARGANTA_VIGILIA_ROUTE,
    VDE_MATA_BAIXIOS_ROUTE,
    VDE_MATA_BRAZIER,
    VDE_MATA_EXPLORE_UNLOCK,
    VDE_MATA_LOCATION,
    VDE_SANCTUARY_UNLOCK,
    VDE_VIGILIA_MATA_ROUTE,
    create_road_combat,
    creature_for,
    crowns,
    enemy_xp,
    equipment_rarity,
    hunt_profile_for_local_id,
    hunt_profile_for_location,
    material_for,
    materialize_equipment,
    rune_potency,
    select_creature,
    select_exploration_result,
    select_variant,
    weighted_choice,
)
from asterion.domain.road import CONFINS_LOCATION_CATALOG as CONFINS_LOCATION_ENTRIES
from asterion.domain.vde_fosso import (
    FOSSO_DISCOVERY_UNLOCK,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.combat_repository import CombatRepository
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    BlockedDelivery,
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    ConsumableStack,
    DungeonLobby,
    DungeonLobbyMember,
    DungeonMatchQueue,
    DungeonRun,
    DungeonRunMember,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    MaterialStack,
    PendingItem,
    PvpveCollision,
    PvpveCollisionMember,
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
BOSQUE = "Bosque Calcinado"
RUINS = "Ruínas do Vigia"
VDE_GARGANTA = "Garganta dos Laços"
VDE_VIGILIA = "Vigília do Vale"
VDE_MATA = "Mata Suspensa"
VDE_BAIXIOS = "Baixios Enredados"
VDE_CLAUSTRO = "Claustro das Raízes"
VDE_BERCO = "Berço da Matriarca"
NARETH_CAMPINAS_LABEL = NARETH_CAMPINAS
NARETH_POSTO_LABEL = NARETH_POSTO
NARETH_CAMARA_LABEL = NARETH_CAMARA
REGION = "Terras do Ocaso"
VDE_REGION = "Vales dos Enforcados"
NARETH_REGION = "Planícies de Nareth"
VARZEAS_REGION = "Várzeas Carmesins"
ALTOS_REGION_LABEL = ALTOS_REGION
CONFINS_REGION_LABEL = CONFINS_REGION
ALTOS_ESCARPA_LABEL = ALTOS_ESCARPA
ALTOS_ABRIGO_LABEL = ALTOS_ABRIGO
ALTOS_PONTES_LABEL = ALTOS_PONTES
ALTOS_PEDREIRAS_LABEL = ALTOS_PEDREIRAS
ALTOS_BASTILHA_LABEL = ALTOS_BASTILHA
ALTOS_CORACAO_LABEL = ALTOS_CORACAO
CONFINS_MARCHA_LABEL = CONFINS_MARCHA
CONFINS_ULTIMO_REFUGIO_LABEL = CONFINS_ULTIMO_REFUGIO
CONFINS_ESTRADAS_AUSENTES_LABEL = CONFINS_ESTRADAS_AUSENTES
CONFINS_FRATURAS_LIMIAR_LABEL = CONFINS_FRATURAS_LIMIAR
CONFINS_NO_CENTRAL_LABEL = CONFINS_NO_CENTRAL
CONFINS_CAMARA_REGENCIA_LABEL = CONFINS_CAMARA_REGENCIA
CONFINS_LOCATION_CATALOG = tuple(label for _, label in CONFINS_LOCATION_ENTRIES)
VARZEAS_DIQUES_LABEL = VARZEAS_DIQUES
VARZEAS_PORTO_LABEL = VARZEAS_PORTO
VARZEAS_BREJOS_LABEL = VARZEAS_BREJOS
VARZEAS_HORTOS_LABEL = VARZEAS_HORTOS
VARZEAS_GALERIAS_LABEL = VARZEAS_GALERIAS
VARZEAS_CAMARA_LABEL = VARZEAS_CAMARA
ALTOS_LOCATIONS = frozenset((ALTOS_ESCARPA_LABEL, ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL, ALTOS_PEDREIRAS_LABEL, ALTOS_BASTILHA_LABEL, ALTOS_CORACAO_LABEL))
CONFINS_LOCATIONS = frozenset((CONFINS_MARCHA_LABEL, CONFINS_ULTIMO_REFUGIO_LABEL, CONFINS_ESTRADAS_AUSENTES_LABEL, CONFINS_FRATURAS_LIMIAR_LABEL, CONFINS_NO_CENTRAL_LABEL))
VDE_LOCATIONS = frozenset((VDE_GARGANTA, VDE_VIGILIA, VDE_MATA, VDE_BAIXIOS, VDE_CLAUSTRO, VDE_BERCO))
NARETH_LOCATIONS = frozenset((NARETH_CAMPINAS_LABEL, NARETH_POSTO_LABEL, NARETH_CANAIS, NARETH_CAMPOS, NARETH_OBSERVATORIO, NARETH_CAMARA_LABEL))
VARZEAS_LOCATIONS = frozenset((VARZEAS_DIQUES_LABEL, VARZEAS_PORTO_LABEL, VARZEAS_BREJOS_LABEL, VARZEAS_HORTOS_LABEL, VARZEAS_GALERIAS_LABEL, VARZEAS_CAMARA_LABEL))
NARETH_REGION_ROUTE_ENDPOINTS = frozenset((VDE_BERCO, NARETH_CAMPINAS_LABEL))
NARETH_VARZEAS_ROUTE_ENDPOINTS = frozenset((NARETH_CAMARA_LABEL, VARZEAS_DIQUES_LABEL))
VARZEAS_DIQUES_PORTO_ROUTE_ENDPOINTS = frozenset((VARZEAS_DIQUES_LABEL, VARZEAS_PORTO_LABEL))
VARZEAS_PORTO_BREJOS_ROUTE_ENDPOINTS = frozenset((VARZEAS_PORTO_LABEL, VARZEAS_BREJOS_LABEL))
VARZEAS_BREJOS_HORTOS_ROUTE_ENDPOINTS = frozenset((VARZEAS_BREJOS_LABEL, VARZEAS_HORTOS_LABEL))
VARZEAS_HORTOS_GALERIAS_ROUTE_ENDPOINTS = frozenset((VARZEAS_HORTOS_LABEL, VARZEAS_GALERIAS_LABEL))
VARZEAS_GALERIAS_CAMARA_ROUTE_ENDPOINTS = frozenset((VARZEAS_GALERIAS_LABEL, VARZEAS_CAMARA_LABEL))
VARZEAS_CAMARA_ALTOS_ROUTE_ENDPOINTS = frozenset((VARZEAS_CAMARA_LABEL, ALTOS_ESCARPA_LABEL))
ALTOS_ESCARPA_ABRIGO_ROUTE_ENDPOINTS = frozenset((ALTOS_ESCARPA_LABEL, ALTOS_ABRIGO_LABEL))
ALTOS_ABRIGO_PONTES_ROUTE_ENDPOINTS = frozenset((ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL))
ALTOS_PONTES_PEDREIRAS_ROUTE_ENDPOINTS = frozenset((ALTOS_PONTES_LABEL, ALTOS_PEDREIRAS_LABEL))
ALTOS_PEDREIRAS_BASTILHA_ROUTE_ENDPOINTS = frozenset((ALTOS_PEDREIRAS_LABEL, ALTOS_BASTILHA_LABEL))
ALTOS_BASTILHA_CORACAO_ROUTE_ENDPOINTS = frozenset((ALTOS_BASTILHA_LABEL, ALTOS_CORACAO_LABEL))
ALTOS_CONFINS_ROUTE_ENDPOINTS = frozenset((ALTOS_CORACAO_LABEL, CONFINS_MARCHA_LABEL))
CONFINS_MARCHA_REFUGIO_ROUTE_ENDPOINTS = frozenset((CONFINS_MARCHA_LABEL, CONFINS_ULTIMO_REFUGIO_LABEL))
CONFINS_REFUGIO_ESTRADAS_ROUTE_ENDPOINTS = frozenset((CONFINS_ULTIMO_REFUGIO_LABEL, CONFINS_ESTRADAS_AUSENTES_LABEL))
CONFINS_ESTRADAS_FRATURAS_ROUTE_ENDPOINTS = frozenset((CONFINS_ESTRADAS_AUSENTES_LABEL, CONFINS_FRATURAS_LIMIAR_LABEL))
CONFINS_FRATURAS_NO_ROUTE_ENDPOINTS = frozenset((CONFINS_FRATURAS_LIMIAR_LABEL, CONFINS_NO_CENTRAL_LABEL))
CONFINS_NO_CAMARA_ROUTE_ENDPOINTS = frozenset((CONFINS_NO_CENTRAL_LABEL, CONFINS_CAMARA_REGENCIA_LABEL))
NARETH_CAMPINAS_POSTO_ROUTE_ENDPOINTS = frozenset((NARETH_CAMPINAS_LABEL, NARETH_POSTO_LABEL))
NARETH_POSTO_CANAIS_ROUTE_ENDPOINTS = frozenset((NARETH_POSTO_LABEL, NARETH_CANAIS))
NARETH_CANAIS_CAMPOS_ROUTE_ENDPOINTS = frozenset((NARETH_CANAIS, NARETH_CAMPOS))
NARETH_CAMPOS_OBSERVATORIO_ROUTE_ENDPOINTS = frozenset((NARETH_CAMPOS, NARETH_OBSERVATORIO))
NARETH_OBSERVATORIO_CAMARA_ROUTE_ENDPOINTS = frozenset((NARETH_OBSERVATORIO, NARETH_CAMARA_LABEL))
P2_QUEST_ID = "P2"
P3_QUEST_ID = "P3"
P4_QUEST_ID = "P4"
S4_QUEST_ID = "S4"
CHARNECA_ROUTE_ENDPOINTS = frozenset((REFUGE, CHARNECA))
BOSQUE_ROUTE_ENDPOINTS = frozenset((CHARNECA, BOSQUE))
BOSQUE_RUINS_ROUTE_ENDPOINTS = frozenset((BOSQUE, RUINS))
VDE_GARGANTA_VIGILIA_ROUTE_ENDPOINTS = frozenset((VDE_GARGANTA, VDE_VIGILIA))
VDE_VIGILIA_MATA_ROUTE_ENDPOINTS = frozenset((VDE_VIGILIA, VDE_MATA))
VDE_MATA_BAIXIOS_ROUTE_ENDPOINTS = frozenset((VDE_MATA, VDE_BAIXIOS))
VDE_BAIXIOS_CLAUSTRO_ROUTE_ENDPOINTS = frozenset((VDE_BAIXIOS, VDE_CLAUSTRO))
VDE_CLAUSTRO_BERCO_ROUTE_ENDPOINTS = frozenset((VDE_CLAUSTRO, VDE_BERCO))
OVERLAND_ROUTE_PAIRS = (
    CHARNECA_ROUTE_ENDPOINTS,
    BOSQUE_ROUTE_ENDPOINTS,
    BOSQUE_RUINS_ROUTE_ENDPOINTS,
    VDE_GARGANTA_VIGILIA_ROUTE_ENDPOINTS,
    VDE_VIGILIA_MATA_ROUTE_ENDPOINTS,
    VDE_MATA_BAIXIOS_ROUTE_ENDPOINTS,
    VDE_BAIXIOS_CLAUSTRO_ROUTE_ENDPOINTS,
    VDE_CLAUSTRO_BERCO_ROUTE_ENDPOINTS,
    NARETH_REGION_ROUTE_ENDPOINTS,
    NARETH_CAMPINAS_POSTO_ROUTE_ENDPOINTS,
    NARETH_POSTO_CANAIS_ROUTE_ENDPOINTS,
    NARETH_CANAIS_CAMPOS_ROUTE_ENDPOINTS,
    NARETH_CAMPOS_OBSERVATORIO_ROUTE_ENDPOINTS,
    NARETH_OBSERVATORIO_CAMARA_ROUTE_ENDPOINTS,
    NARETH_VARZEAS_ROUTE_ENDPOINTS,
    VARZEAS_DIQUES_PORTO_ROUTE_ENDPOINTS,
    VARZEAS_PORTO_BREJOS_ROUTE_ENDPOINTS,
    VARZEAS_BREJOS_HORTOS_ROUTE_ENDPOINTS,
    VARZEAS_HORTOS_GALERIAS_ROUTE_ENDPOINTS,
    VARZEAS_GALERIAS_CAMARA_ROUTE_ENDPOINTS,
    VARZEAS_CAMARA_ALTOS_ROUTE_ENDPOINTS,
    ALTOS_ESCARPA_ABRIGO_ROUTE_ENDPOINTS,
    ALTOS_ABRIGO_PONTES_ROUTE_ENDPOINTS,
    ALTOS_PONTES_PEDREIRAS_ROUTE_ENDPOINTS,
    ALTOS_PEDREIRAS_BASTILHA_ROUTE_ENDPOINTS,
    ALTOS_BASTILHA_CORACAO_ROUTE_ENDPOINTS,
    ALTOS_CONFINS_ROUTE_ENDPOINTS,
    CONFINS_MARCHA_REFUGIO_ROUTE_ENDPOINTS,
    CONFINS_REFUGIO_ESTRADAS_ROUTE_ENDPOINTS,
    CONFINS_ESTRADAS_FRATURAS_ROUTE_ENDPOINTS,
    CONFINS_FRATURAS_NO_ROUTE_ENDPOINTS,
    CONFINS_NO_CAMARA_ROUTE_ENDPOINTS,
)
TRAVEL_LOCATIONS = frozenset((ROAD, REFUGE, CHARNECA, BOSQUE, RUINS, VDE_GARGANTA, VDE_VIGILIA, VDE_MATA, VDE_BAIXIOS, VDE_CLAUSTRO, VDE_BERCO, NARETH_CAMPINAS_LABEL, NARETH_POSTO_LABEL, NARETH_CANAIS, NARETH_CAMPOS, NARETH_OBSERVATORIO, NARETH_CAMARA_LABEL, VARZEAS_DIQUES_LABEL, VARZEAS_PORTO_LABEL, VARZEAS_BREJOS_LABEL, VARZEAS_HORTOS_LABEL, VARZEAS_GALERIAS_LABEL, VARZEAS_CAMARA_LABEL, ALTOS_ESCARPA_LABEL, ALTOS_ABRIGO_LABEL, ALTOS_PONTES_LABEL, ALTOS_PEDREIRAS_LABEL, ALTOS_BASTILHA_LABEL, ALTOS_CORACAO_LABEL, CONFINS_MARCHA_LABEL, CONFINS_ULTIMO_REFUGIO_LABEL, CONFINS_ESTRADAS_AUSENTES_LABEL, CONFINS_FRATURAS_LIMIAR_LABEL, CONFINS_NO_CENTRAL_LABEL, CONFINS_CAMARA_REGENCIA_LABEL))
BRAZIER_FOR_LOCATION = {
    ROAD: "tdo.brazier.estrada",
    REFUGE: "tdo.brazier.refugio_do_ocaso",
    CHARNECA: CHARNECA_BRAZIER,
    BOSQUE: BOSQUE_BRAZIER,
    RUINS: RUINS_BRAZIER,
    VDE_GARGANTA: VDE_GARGANTA_BRAZIER,
    VDE_VIGILIA: "vde.brazier.vigilia_do_vale",
    VDE_MATA: VDE_MATA_BRAZIER,
    VDE_BAIXIOS: VDE_BAIXIOS_BRAZIER,
    VDE_CLAUSTRO: VDE_CLAUSTRO_BRAZIER,
    NARETH_CAMPINAS_LABEL: NARETH_BRAZIER_HORIZONTE,
    NARETH_POSTO_LABEL: NARETH_BRAZIER_POSTO,
    NARETH_CANAIS: NARETH_BRAZIER_CANAIS,
    NARETH_CAMPOS: NARETH_BRAZIER_CAMPOS,
    NARETH_OBSERVATORIO: NARETH_BRAZIER_OBSERVATORIO,
    VARZEAS_DIQUES_LABEL: VARZEAS_DIQUES_BRAZIER,
    VARZEAS_PORTO_LABEL: VARZEAS_PORTO_BRAZIER,
    VARZEAS_BREJOS_LABEL: VARZEAS_BREJOS_BRAZIER,
    VARZEAS_HORTOS_LABEL: VARZEAS_HORTOS_BRAZIER,
    VARZEAS_GALERIAS_LABEL: VARZEAS_GALERIAS_BRAZIER,
    ALTOS_ESCARPA_LABEL: ALTOS_ESCARPA_BRAZIER,
    ALTOS_ABRIGO_LABEL: ALTOS_ABRIGO_BRAZIER,
    ALTOS_PONTES_LABEL: ALTOS_PONTES_BRAZIER,
    ALTOS_PEDREIRAS_LABEL: ALTOS_PEDREIRA_BRAZIER,
    ALTOS_BASTILHA_LABEL: ALTOS_BASTILHA_BRAZIER,
    CONFINS_MARCHA_LABEL: CONFINS_MARCO_DUPLO_BRAZIER,
    CONFINS_ULTIMO_REFUGIO_LABEL: CONFINS_TESTEMUNHA_BRAZIER,
    CONFINS_ESTRADAS_AUSENTES_LABEL: CONFINS_ESTRADA_CONFERIDA_BRAZIER,
    CONFINS_FRATURAS_LIMIAR_LABEL: CONFINS_LIMIAR_FIRME_BRAZIER,
    CONFINS_NO_CENTRAL_LABEL: CONFINS_NO_RETORNO_BRAZIER,
}
BRAZIER_DETAILS = {
    "tdo.brazier.estrada": (ROAD, "Braseiro da Estrada"),
    "tdo.brazier.refugio_do_ocaso": (REFUGE, "Braseiro do Refúgio"),
    CHARNECA_BRAZIER: (CHARNECA, "Braseiro do Vento Morto"),
    BOSQUE_BRAZIER: (BOSQUE, "Braseiro dos Galhos Mortos"),
    RUINS_BRAZIER: (RUINS, "Braseiro do Poente"),
    VDE_GARGANTA_BRAZIER: (VDE_GARGANTA, "Braseiro dos Laços"),
    "vde.brazier.vigilia_do_vale": (VDE_VIGILIA, "Braseiro da Vigília"),
    VDE_MATA_BRAZIER: (VDE_MATA, "Braseiro das Copas Suspensas"),
    VDE_BAIXIOS_BRAZIER: (VDE_BAIXIOS, "Braseiro da Turfa Fria"),
    VDE_CLAUSTRO_BRAZIER: (VDE_CLAUSTRO, "Braseiro das Pedras Enlaçadas"),
    NARETH_BRAZIER_HORIZONTE: (NARETH_CAMPINAS_LABEL, "Braseiro do Horizonte"),
    NARETH_BRAZIER_POSTO: (NARETH_POSTO_LABEL, "Braseiro do Posto"),
    NARETH_BRAZIER_CANAIS: (NARETH_CANAIS, "Braseiro do Canal Alto"),
    NARETH_BRAZIER_CAMPOS: (NARETH_CAMPOS, "Braseiro da Linha Quebrada"),
    NARETH_BRAZIER_OBSERVATORIO: (NARETH_OBSERVATORIO, "Braseiro do Eixo"),
    VARZEAS_DIQUES_BRAZIER: (VARZEAS_DIQUES_LABEL, "Braseiro do Dique Alto"),
    VARZEAS_PORTO_BRAZIER: (VARZEAS_PORTO_LABEL, "Braseiro do Porto"),
    VARZEAS_BREJOS_BRAZIER: (VARZEAS_BREJOS_LABEL, "Braseiro dos Juncos Baixos"),
    VARZEAS_HORTOS_BRAZIER: (VARZEAS_HORTOS_LABEL, "Braseiro do Horto Seco"),
    VARZEAS_GALERIAS_BRAZIER: (VARZEAS_GALERIAS_LABEL, "Braseiro das Válvulas"),
    ALTOS_ESCARPA_BRAZIER: (ALTOS_ESCARPA_LABEL, "Braseiro da Escarpa"),
    ALTOS_ABRIGO_BRAZIER: (ALTOS_ABRIGO_LABEL, "Braseiro do Abrigo"),
    ALTOS_PONTES_BRAZIER: (ALTOS_PONTES_LABEL, "Braseiro da Ponte Alta"),
    ALTOS_PEDREIRA_BRAZIER: (ALTOS_PEDREIRAS_LABEL, "Braseiro da Pedreira Velha"),
    ALTOS_BASTILHA_BRAZIER: (ALTOS_BASTILHA_LABEL, "Braseiro da Bastilha Externa"),
    CONFINS_MARCO_DUPLO_BRAZIER: (CONFINS_MARCHA_LABEL, "Braseiro do Marco Duplo"),
    CONFINS_TESTEMUNHA_BRAZIER: (CONFINS_ULTIMO_REFUGIO_LABEL, "Braseiro da Testemunha"),
    CONFINS_ESTRADA_CONFERIDA_BRAZIER: (CONFINS_ESTRADAS_AUSENTES_LABEL, "Braseiro da Estrada Conferida"),
    CONFINS_LIMIAR_FIRME_BRAZIER: (CONFINS_FRATURAS_LIMIAR_LABEL, "Braseiro do Limiar Firme"),
    CONFINS_NO_RETORNO_BRAZIER: (CONFINS_NO_CENTRAL_LABEL, "Braseiro do Nó de Retorno"),
}
HUNT_CONTENT = "road_manual_hunt"
GROUP_HUNT_CONTENT = "road_group_hunt"
PVPVE_QUEUE_CONTENT = "road_pvpve_queue"
PVPVE_CONTENT = "road_pvpve"
EXPLORE_CONTENT = "road_exploration"
CHARNECA_DUNGEON_UNLOCK = "dungeon.tdo.cripta_ocaso"
CHARNECA_KNOWN_PATH_UNLOCK = "known_path.tdo.cripta_ocaso"
CHARNECA_MARKS_CODEX_ENTRY = "codex.mystery.marcas_na_fuligem"

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
    "material.confins.ferro_baliza": "Ferro de Baliza",
    "material.confins.couro_marcha": "Couro de Marcha",
    "material.confins.musgo_limiar": "Musgo de Limiar",
    "material.confins.po_referencia": "Pó de Referência",
    "material.special.confins.core.arquivo_retorno": "Núcleo do Arquivo do Retorno",
    "material.tdo.catalisador_elite_vi": "Catalisador de Elite VI",
    "material.tdo.fragmento_aprimoramento_vi": "Fragmento de Aprimoramento VI",
    "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
    "material.tdo.couro_escoriado": "Couro Escoriado",
    "material.tdo.erva_cinzenta": "Erva Cinzenta",
    "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
    "material.vde.ferro_enredado": "Ferro Enredado",
    "material.vde.couro_musgoso": "Couro Musgoso",
    "material.vde.erva_de_turfa": "Erva de Turfa",
    "material.vde.resina_enredada": "Resina Enredada",
    "material.vde.catalisador_elite_ii": "Catalisador de Elite II",
    "material.vde.fragmento_aprimoramento_ii": "Fragmento de Aprimoramento II",
    "material.nareth.bronze_de_marco": "Bronze de Marco",
    "material.nareth.couro_de_horizonte": "Couro de Horizonte",
    "material.nareth.erva_de_vento": "Erva de Vento",
    "material.nareth.po_de_eixo": "Pó de Eixo",
    "material.nareth.catalisador_elite_iii": "Catalisador de Elite III",
    "material.nareth.fragmento_aprimoramento_iii": "Fragmento de Aprimoramento III",
    "material.nareth.nucleo_arconte_invertido": "Núcleo do Arconte Invertido",
    "material.nareth.nucleo_galerias_meridiano": "Núcleo das Galerias do Meridiano",
    "material.nareth.nucleo_observatorio_afundado": "Núcleo do Observatório Afundado",
    "material.varzeas.ferro_de_salmoura": "Ferro de Salmoura",
    "material.varzeas.couro_de_varzea": "Couro de Várzea",
    "material.varzeas.junco_ferruginoso": "Junco Ferruginoso",
    "material.varzeas.soro_antigo": "Soro Antigo",
    "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
    "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
    "material.varzeas.nucleo_enfermaria_afundada": "Núcleo da Enfermaria Afundada",
    "material.varzeas.nucleo_cisterna_transferencia": "Núcleo da Cisterna de Transferência",
    "material.varzeas.nucleo_matriz_rubra": "Núcleo da Matriz Rubra",
    "material.altos.ferro_contrapeso": "Ferro de Contrapeso",
    "material.altos.couro_escarpa": "Couro de Escarpa",
    "material.altos.liquen_pedreira": "Líquen de Pedreira",
    "material.altos.cinza_basalto": "Cinza de Basalto",
}
VDE_EXPLORATION_RESOURCE_MATERIALS = {
    "explore.vde.garganta.ferro_enredado": "material.vde.ferro_enredado",
    "explore.vde.garganta.couro_musgoso": "material.vde.couro_musgoso",
    "explore.vde.garganta.erva_de_turfa": "material.vde.erva_de_turfa",
    "explore.vde.garganta.resina_enredada": "material.vde.resina_enredada",
    "explore.vde.mata.couro_musgoso": "material.vde.couro_musgoso",
    "explore.vde.mata.erva_de_turfa": "material.vde.erva_de_turfa",
    "explore.vde.mata.resina_enredada": "material.vde.resina_enredada",
    "explore.vde.mata.ferro_enredado": "material.vde.ferro_enredado",
    "explore.vde.baixios.erva_de_turfa": "material.vde.erva_de_turfa",
    "explore.vde.baixios.resina_enredada": "material.vde.resina_enredada",
    "explore.vde.baixios.couro_musgoso": "material.vde.couro_musgoso",
    "explore.vde.baixios.ferro_enredado": "material.vde.ferro_enredado",
    "explore.vde.claustro.ferro_enredado": "material.vde.ferro_enredado",
    "explore.vde.claustro.resina_enredada": "material.vde.resina_enredada",
    "explore.vde.claustro.erva_de_turfa": "material.vde.erva_de_turfa",
    "explore.vde.claustro.couro_musgoso": "material.vde.couro_musgoso",
}
VARZEAS_EXPLORATION_RESOURCE_MATERIALS = {
    "explore.varzeas.diques.ferro_salmoura": "material.varzeas.ferro_de_salmoura",
    "explore.varzeas.diques.couro_varzea": "material.varzeas.couro_de_varzea",
    "explore.varzeas.diques.junco_ferruginoso": "material.varzeas.junco_ferruginoso",
    "explore.varzeas.diques.soro_antigo": "material.varzeas.soro_antigo",
    "explore.varzeas.brejos.ferro_salmoura": "material.varzeas.ferro_de_salmoura",
    "explore.varzeas.brejos.couro_varzea": "material.varzeas.couro_de_varzea",
    "explore.varzeas.brejos.junco_ferruginoso": "material.varzeas.junco_ferruginoso",
    "explore.varzeas.brejos.soro_antigo": "material.varzeas.soro_antigo",
    "explore.varzeas.hortos.soro_antigo": "material.varzeas.soro_antigo",
    "explore.varzeas.hortos.junco_ferruginoso": "material.varzeas.junco_ferruginoso",
    "explore.varzeas.hortos.couro_varzea": "material.varzeas.couro_de_varzea",
    "explore.varzeas.hortos.ferro_salmoura": "material.varzeas.ferro_de_salmoura",
    "explore.varzeas.galerias.ferro_salmoura": "material.varzeas.ferro_de_salmoura",
    "explore.varzeas.galerias.soro_antigo": "material.varzeas.soro_antigo",
    "explore.varzeas.galerias.junco_ferruginoso": "material.varzeas.junco_ferruginoso",
    "explore.varzeas.galerias.couro_varzea": "material.varzeas.couro_de_varzea",
}
ALTOS_EXPLORATION_RESOURCE_MATERIALS = {
    "explore.altos.escarpa.ferro_contrapeso": "material.altos.ferro_contrapeso",
    "explore.altos.escarpa.couro_escarpa": "material.altos.couro_escarpa",
    "explore.altos.escarpa.liquen_pedreira": "material.altos.liquen_pedreira",
    "explore.altos.escarpa.cinza_basalto": "material.altos.cinza_basalto",
    "explore.altos.pontes.ferro_contrapeso": "material.altos.ferro_contrapeso",
    "explore.altos.pontes.couro_escarpa": "material.altos.couro_escarpa",
    "explore.altos.pontes.liquen_pedreira": "material.altos.liquen_pedreira",
    "explore.altos.pontes.cinza_basalto": "material.altos.cinza_basalto",
    "explore.altos.pedreiras.ferro_contrapeso": "material.altos.ferro_contrapeso",
    "explore.altos.pedreiras.cinza_basalto": "material.altos.cinza_basalto",
    "explore.altos.pedreiras.couro_escarpa": "material.altos.couro_escarpa",
    "explore.altos.pedreiras.liquen_pedreira": "material.altos.liquen_pedreira",
    "explore.altos.bastilha.ferro_contrapeso": "material.altos.ferro_contrapeso",
    "explore.altos.bastilha.cinza_basalto": "material.altos.cinza_basalto",
    "explore.altos.bastilha.liquen_pedreira": "material.altos.liquen_pedreira",
    "explore.altos.bastilha.couro_escarpa": "material.altos.couro_escarpa",
}
ALTOS_EXPLORATION_UNIQUE_XP = {
    "explore.altos.escarpa.mirante_escoras": 8912,
    "explore.altos.escarpa.caderno_resgate_rasgado": 2785,
    "explore.altos.pontes.braseiro_ponte_alta": 9616,
    "explore.altos.pontes.plataforma_contrapeso": 9616,
    "explore.altos.pontes.livro_prioridades": 3005,
    "explore.altos.pedreiras.braseiro_pedreira_velha": 10736,
    "explore.altos.pedreiras.entrada_contrapeso": 10736,
    "explore.altos.pedreiras.mapa_extracao": 3355,
    "explore.altos.bastilha.braseiro_externo": 11520,
    "explore.altos.bastilha.entrada_profunda": 11520,
    "explore.altos.bastilha.tabela_validade": 3600,
}
CONFINS_EXPLORATION_UNIQUE_XP = {
    "explore.confins.marcha.duas_balizas": 12_744,
    "explore.confins.marcha.caderno_marcha": 3_983,
    "explore.confins.estradas.braseiro_conferida": 14_024,
    "explore.confins.estradas.arquivo_retorno": 14_024,
    "explore.confins.estradas.memoria_fundacao": 4_383,
    "explore.confins.fraturas.braseiro_limiar": 14_920,
    "explore.confins.fraturas.corte_referencia": 14_920,
    "explore.confins.fraturas.ficha_dupla": 4_663,
    "explore.confins.no.braseiro_retorno": 16_304,
    "explore.confins.no.camara_contradicoes": 16_304,
    "explore.confins.no.rede_incompleta": 5_095,
}
CONFINS_EXPLORATION_RESOURCE_POOL = (
    (CONFINS_FERRO_BALIZA, 25),
    (CONFINS_COURO_MARCHA, 25),
    (CONFINS_MUSGO_LIMIAR, 35),
    (CONFINS_PO_REFERENCIA, 15),
)
CONFINS_ESTRADAS_EXPLORATION_RESOURCE_POOL = (
    (CONFINS_FERRO_BALIZA, 25),
    (CONFINS_COURO_MARCHA, 25),
    (CONFINS_MUSGO_LIMIAR, 30),
    (CONFINS_PO_REFERENCIA, 20),
)
CONFINS_FRATURAS_EXPLORATION_RESOURCE_POOL = (
    (CONFINS_FERRO_BALIZA, 20),
    (CONFINS_COURO_MARCHA, 20),
    (CONFINS_MUSGO_LIMIAR, 25),
    (CONFINS_PO_REFERENCIA, 35),
)
CONFINS_NO_EXPLORATION_RESOURCE_POOL = (
    (CONFINS_FERRO_BALIZA, 40),
    (CONFINS_COURO_MARCHA, 10),
    (CONFINS_MUSGO_LIMIAR, 15),
    (CONFINS_PO_REFERENCIA, 35),
)
CONFINS_CARTOGRAPHER_UNIQUE_IDS = (
    "explore.confins.marcha.duas_balizas",
    "explore.confins.marcha.caderno_marcha",
    "explore.confins.estradas.braseiro_conferida",
    "explore.confins.estradas.arquivo_retorno",
    "explore.confins.estradas.memoria_fundacao",
    "explore.confins.fraturas.braseiro_limiar",
    "explore.confins.fraturas.corte_referencia",
    "explore.confins.fraturas.ficha_dupla",
    "explore.confins.no.braseiro_retorno",
    "explore.confins.no.camara_contradicoes",
    "explore.confins.no.rede_incompleta",
)
CONFINS_CARTOGRAPHER_ACHIEVEMENT = "achievement.confins.cartografo_ausencias"
ALTOS_CARTOGRAPHER_ACHIEVEMENT = "achievement.altos.cartografo_peso"
VARZEAS_EXPLORATION_UNIQUE_XP = {
    "explore.varzeas.diques.comporta_primeiro_dique": 5760,
    "explore.varzeas.diques.agua_sobe_sem_chuva": 1800,
    "explore.varzeas.brejos.braseiro_juncos_baixos": 6336,
    "explore.varzeas.brejos.entrada_enfermaria_afundada": 6336,
    "explore.varzeas.brejos.pulso_de_pressao": 1980,
    "explore.varzeas.hortos.braseiro_horto_seco": 7248,
    "explore.varzeas.hortos.estufa_restituicao": 7248,
    "explore.varzeas.hortos.canteiro_dupla_funcao": 2265,
    "explore.varzeas.galerias.braseiro_valvulas": 7896,
    "explore.varzeas.galerias.entrada_cisterna_transferencia": 7896,
    "explore.varzeas.galerias.linha_retorno": 2468,
}
NARETH_EXPLORATION_RESOURCE_MATERIALS = {
    "explore.nareth.campinas.bronze_de_marco": "material.nareth.bronze_de_marco",
    "explore.nareth.campinas.couro_de_horizonte": "material.nareth.couro_de_horizonte",
    "explore.nareth.campinas.erva_de_vento": "material.nareth.erva_de_vento",
    "explore.nareth.campinas.po_de_eixo": "material.nareth.po_de_eixo",
    "explore.nareth.canais.bronze_de_marco": "material.nareth.bronze_de_marco",
    "explore.nareth.canais.erva_de_vento": "material.nareth.erva_de_vento",
    "explore.nareth.canais.po_de_eixo": "material.nareth.po_de_eixo",
    "explore.nareth.canais.couro_de_horizonte": "material.nareth.couro_de_horizonte",
    "explore.nareth.campos.couro_de_horizonte": "material.nareth.couro_de_horizonte",
    "explore.nareth.campos.erva_de_vento": "material.nareth.erva_de_vento",
    "explore.nareth.campos.po_de_eixo": "material.nareth.po_de_eixo",
    "explore.nareth.campos.bronze_de_marco": "material.nareth.bronze_de_marco",
    "explore.nareth.observatorio.bronze_de_marco": "material.nareth.bronze_de_marco",
    "explore.nareth.observatorio.po_de_eixo": "material.nareth.po_de_eixo",
    "explore.nareth.observatorio.erva_de_vento": "material.nareth.erva_de_vento",
    "explore.nareth.observatorio.couro_de_horizonte": "material.nareth.couro_de_horizonte",
}
VDE_EXPLORATION_UNIQUE_XP = {
    "explore.vde.garganta.marco_dos_lacos": 1536,
    "explore.vde.garganta.sinos_sem_maos": 480,
    "explore.vde.mata.braseiro_das_copas": 1832,
    "explore.vde.mata.entrada_fosso_raizes": 1832,
    "explore.vde.mata.passarela_partida": 573,
    "explore.vde.baixios.braseiro_turfa_fria": 2336,
    "explore.vde.baixios.galeria_afogada": 2336,
    "explore.vde.baixios.marcas_sob_a_agua": 730,
    "explore.vde.claustro.braseiro_pedras_enlacadas": 2704,
    "explore.vde.claustro.entrada_santuario_no_antigo": 2704,
    "explore.vde.claustro.tracado_do_no": 845,
}
NARETH_EXPLORATION_UNIQUE_XP = {
    "explore.nareth.campinas.marco_primeiro_meridiano": 3304,
    "explore.nareth.campinas.duas_medidas_mesma_estrada": 1033,
    "explore.nareth.canais.braseiro_canal_alto": 3744,
    "explore.nareth.canais.entrada_galerias_meridiano": 3744,
    "explore.nareth.canais.comporta_sem_agua": 1170,
    "explore.nareth.canais.pedra_raspada": 0,
    "explore.nareth.campos.braseiro_linha_quebrada": 4448,
    "explore.nareth.campos.linha_que_nao_fecha": 4448,
    "explore.nareth.campos.sombras_que_discordam": 1390,
    "explore.nareth.observatorio.braseiro_do_eixo": 4952,
    "explore.nareth.observatorio.entrada_observatorio_afundado": 4952,
    "explore.nareth.observatorio.prumo_fora_do_centro": 1548,
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
    hunt_enabled: bool = True
    explore_enabled: bool = True
    retry_available: bool = True
    explore_available: bool = True
    creature: str | None = None
    variant: str | None = None
    consumable_options: tuple[CombatConsumableOption, ...] = ()
    consumable_screen: str | None = None
    selected_consumable_id: str | None = None
    selected_target_id: str | None = None
    selection_parent: str = "items"
    consumable_notice: str | None = None
    consumable_quantities: tuple[tuple[str, int], ...] = ()
    consumable_budget_limit: int = 0
    ready_consumable_option: CombatConsumableOption | None = None
    route_available: bool = False
    route_destinations: tuple[str, ...] = ()
    brazier_id: str | None = None
    brazier_label: str | None = None
    brazier_destinations: tuple[tuple[str, str, str], ...] = ()
    recovery_brazier: str | None = None
    recovery_location: str | None = None
    combat_context: str = "road"
    combat_actor_key: str | None = None
    pvpve_round_queue: bool = False
    pvpve_round_ai: bool = False
    pvpve_round_takeover: bool = False
    pvpve_queue_id: UUID | None = None


def _exploration_local_id(profile) -> str:
    # Keep historical Road ExplorationAttempt.local_id rows query-compatible.
    return ROAD if profile.local_id == ROAD_LOCATION else profile.local_id


def _location_label(local_id: str | None) -> str:
    profile = hunt_profile_for_local_id(local_id)
    return profile.label


def _grade_fragment_for_level(level: int) -> str:
    return _grade_material_for_level(level, "fragmento_aprimoramento")


def _grade_catalyst_for_level(level: int) -> str:
    return _grade_material_for_level(level, "catalisador_elite")


def _grade_material_for_level(level: int, material_kind: str) -> str:
    grade = equipment_grade(level)
    regional_grade = {
        1: ("tdo", "i"),
        2: ("vde", "ii"),
        3: ("nareth", "iii"),
        4: ("varzeas", "iv"),
        5: ("tdo", "v"),
        6: ("tdo", "vi"),
    }.get(grade)
    if regional_grade is not None:
        region, roman_grade = regional_grade
        return f"material.{region}.{material_kind}_{roman_grade}"
    raise ValueError(f"no global {material_kind} configured for level {level}")


class RoadService:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], server_id: str):
        self.sessions, self.server_id = sessions, server_id
        self.bestiary = BestiaryRecorder()
        from asterion.application.group_hunts import GroupHuntService
        from asterion.application.pvpve import PvpveService

        self.group_hunts = GroupHuntService(sessions, server_id, self)
        self.pvpve = PvpveService(sessions, server_id, self)

    async def resume(self, actor: int) -> RoadView | None:
        # Resolve/expire a waiting PvPvE queue before taking the character lock
        # used to render the Road foreground. Queue refresh locks the whole
        # roster in deterministic order, so doing it first avoids lock inversion
        # during reconnect from a shared Hunt.
        async with self.sessions() as read_session:
            character_id = await read_session.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
            )
            queued_activity_id = None
            if character_id is not None:
                persisted_location = await read_session.scalar(
                    select(WorldState.location).where(WorldState.character_id == character_id)
                )
                if persisted_location in TRAVEL_LOCATIONS:
                    queued_activity_id = await read_session.scalar(
                        select(GameActivity.id).where(
                            GameActivity.character_id == character_id,
                            GameActivity.status == "active",
                            GameActivity.content_id == PVPVE_QUEUE_CONTENT,
                        )
                    )
        if queued_activity_id is not None:
            await self.pvpve.refresh_queue(actor, queued_activity_id)
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            if world.location not in TRAVEL_LOCATIONS:
                return self._invalid_location_view(c, world)
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
            if world.location == CHARNECA:
                if not await self._p2_completed(s, c.id):
                    return None
            elif world.location == BOSQUE:
                if not await self._p3_completed(s, c.id):
                    return None
            elif world.location == RUINS:
                if c.level < 8 or not await self._p4_completed(s, c.id):
                    return None
                if not await self._has_location(s, c.id, RUINS_LOCATION):
                    return None
            elif world.location in VDE_LOCATIONS:
                if not await self._p7_completed(s, c.id):
                    return None
                if world.location == VDE_MATA and not await self._p8_started_or_completed(s, c.id):
                    return None
                if world.location == VDE_BAIXIOS and not await self._p9_started_or_completed(s, c.id):
                    return None
                if world.location == VDE_CLAUSTRO and not await self._p10_started_or_completed(s, c.id):
                    return None
                if world.location == VDE_BERCO and not (
                    await self._has_location(s, c.id, VDE_BERCO_LOCATION)
                    and await s.scalar(
                        select(Unlock.id).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == VDE_CLAUSTRO_BERCO_ROUTE,
                        )
                    )
                    and await s.scalar(
                        select(Quest.id).where(
                            Quest.character_id == c.id,
                            Quest.quest_id == "P11",
                            Quest.status == "completed",
                        )
                    )
                ):
                    return None
            elif world.location in NARETH_LOCATIONS:
                if c.level < 21 or not await self._p12_completed(s, c.id):
                    return None
                await self._ensure(
                    s, Unlock, character_id=c.id, unlock_id=NARETH_REGION_UNLOCK
                )
                if world.location == NARETH_POSTO_LABEL and not (
                    await self._nareth_p13_started_or_completed(s, c.id)
                    and await self._nareth_p13_route_open(s, c.id)
                ):
                    return None
                if world.location == NARETH_CANAIS and not await self._nareth_mission_started_or_completed(s, c.id, "P14"):
                    return None
                if world.location == NARETH_CAMPOS and not await self._nareth_mission_started_or_completed(s, c.id, "P15"):
                    return None
                if world.location == NARETH_OBSERVATORIO and not await self._nareth_mission_started_or_completed(s, c.id, "P16"):
                    return None
                if world.location == NARETH_CAMARA_LABEL and not (
                    await self._nareth_mission_started_or_completed(s, c.id, "P17")
                    and await s.scalar(
                        select(Unlock.id).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == "region.nareth.camara_arconte.available",
                        )
                    )
                ):
                    return None
            elif not await self._p1_completed(s, c.id):
                return None
            return await self._view_for_world(s, c, world)

    async def travel(self, actor: int, destination: str) -> RoadView | None:
        """Compatibility entry point; route and brazier travel stay distinct."""
        if destination not in TRAVEL_LOCATIONS:
            return None
        async with self.sessions() as s:
            c = await self._character(s, actor)
            world = (
                await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
                if c is not None
                else None
            )
            current = world.location if world is not None else None
        if current is None:
            return None
        if any({current, destination} == pair for pair in OVERLAND_ROUTE_PAIRS):
            return await self.travel_route(actor, destination)
        brazier_id = BRAZIER_FOR_LOCATION.get(destination)
        if brazier_id is None:
            return None
        return await self.travel_brazier(actor, brazier_id)

    async def travel_route(self, actor: int, destination: str) -> RoadView | None:
        """Use the free, post-P2 Refuge/Charneca overland connection."""
        if not any(destination in pair for pair in OVERLAND_ROUTE_PAIRS):
            return None
        return await self._travel(actor, destination, mode="route")

    async def travel_brazier(self, actor: int, brazier_id: str) -> RoadView | None:
        """Travel only between permanent Braziers already discovered by the character."""
        detail = BRAZIER_DETAILS.get(brazier_id)
        if detail is None:
            return None
        return await self._travel(actor, detail[0], mode="brazier", brazier_id=brazier_id)

    async def rest(
        self, actor: int, *, expected_brazier_id: str | None = None
    ) -> RoadView | None:
        """Restore only this character at their currently discovered world Brazier."""
        location: str | None = None
        async with self.sessions.begin() as s:
            c = await s.scalar(
                select(Character)
                .where(Character.telegram_id == actor, Character.server_id == self.server_id)
                .with_for_update()
            )
            if c is None or c.stage != "menu:ready":
                return None
            world = await s.scalar(
                select(WorldState).where(WorldState.character_id == c.id).with_for_update()
            )
            if world is None or world.location not in TRAVEL_LOCATIONS:
                return None
            brazier_id = BRAZIER_FOR_LOCATION.get(world.location)
            detail = BRAZIER_DETAILS.get(brazier_id) if brazier_id is not None else None
            if (
                brazier_id is None
                or detail is None
                or detail[0] != world.location
                or (expected_brazier_id is not None and expected_brazier_id != brazier_id)
                or not await self._permanent_brazier_rest_gate(s, c, world)
            ):
                return None

            # The unique active foreground row covers combat, exploration,
            # queues, and other activities. Keep the dungeon checks explicit:
            # a run remains a foreground even if a stale/missing UI activity row
            # is encountered during recovery.
            active_activity = await s.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == c.id,
                    GameActivity.status == "active",
                ).with_for_update()
            )
            active_dungeon_member = await s.scalar(
                select(DungeonRunMember.character_id)
                .join(DungeonRun, DungeonRun.id == DungeonRunMember.run_id)
                .where(
                    DungeonRunMember.character_id == c.id,
                    DungeonRun.status == "active",
                    DungeonRunMember.status.in_(("active", "defeated")),
                )
                .with_for_update()
            )
            open_lobby = await s.scalar(
                select(DungeonLobbyMember.character_id)
                .join(DungeonLobby, DungeonLobby.id == DungeonLobbyMember.lobby_id)
                .where(
                    DungeonLobbyMember.character_id == c.id,
                    DungeonLobbyMember.status.in_(
                        ("joined", "queued", "matched", "confirmed")
                    ),
                    DungeonLobby.status.in_(("forming", "confirming")),
                )
                .with_for_update()
            )
            queued_match = await s.scalar(
                select(DungeonMatchQueue.character_id)
                .where(
                    DungeonMatchQueue.character_id == c.id,
                    DungeonMatchQueue.status.in_(("queued", "matched")),
                )
                .with_for_update()
            )
            if (
                active_activity is not None
                or active_dungeon_member is not None
                or open_lobby is not None
                or queued_match is not None
            ):
                return None

            known_brazier = await s.scalar(
                select(Brazier)
                .where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == brazier_id,
                )
                .with_for_update()
            )
            if known_brazier is None:
                return None

            # Combat effects live in the encounter snapshot, not on Character.
            # Reaching this point guarantees there is no active encounter whose
            # state could be mutated or resumed after the rest.
            c.hp = c.max_hp
            location = world.location

        view = await self.resume(actor)
        if view is None or view.location != location:
            return None
        return view

    async def _permanent_brazier_rest_gate(self, s, character, world) -> bool:
        location = world.location
        region = self._travel_region(location)
        expected_region = {
            "tdo": REGION,
            "vde": VDE_REGION,
            "nareth": NARETH_REGION,
            "varzeas": VARZEAS_REGION,
            "altos": ALTOS_REGION,
            "confins": CONFINS_REGION,
        }.get(region)
        if expected_region is None or world.region != expected_region:
            return False

        regional_minimum = {
            "tdo": 1,
            "vde": 11,
            "nareth": 21,
            "varzeas": 31,
            "altos": 41,
            "confins": 51,
        }[region]
        local_band = LOCATION_LEVEL_BANDS.get(location)
        current_level_minimum = local_band[0] if local_band is not None else regional_minimum
        if character.level < max(regional_minimum, current_level_minimum):
            return False

        async def has_unlock(unlock_id: str) -> bool:
            return bool(
                await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == unlock_id,
                    )
                )
            )

        if region == "tdo":
            if not await self._p1_completed(s, character.id):
                return False
            if location == CHARNECA and not (
                await self._p2_completed(s, character.id)
                and await has_unlock(CHARNECA_ROUTE_UNLOCK)
            ):
                return False
            if location == BOSQUE and not (
                await self._p3_completed(s, character.id)
                and await has_unlock(BOSQUE_ROUTE_UNLOCK)
            ):
                return False
            if location == RUINS and not (
                character.level >= 8
                and await self._p4_completed(s, character.id)
                and await self._has_location(s, character.id, RUINS_LOCATION)
                and await has_unlock(RUINS_ROUTE_UNLOCK)
            ):
                return False
        elif region == "vde":
            if not await self._p7_completed(s, character.id):
                return False
            if location == VDE_VIGILIA and not await has_unlock(
                VDE_GARGANTA_VIGILIA_ROUTE
            ):
                return False
            if location == VDE_MATA and not await self._p8_started_or_completed(
                s, character.id
            ):
                return False
            if location == VDE_MATA and not await has_unlock(VDE_VIGILIA_MATA_ROUTE):
                return False
            if location == VDE_BAIXIOS and not await self._p9_started_or_completed(
                s, character.id
            ):
                return False
            if location == VDE_BAIXIOS and not await has_unlock(VDE_MATA_BAIXIOS_ROUTE):
                return False
            if location == VDE_CLAUSTRO and not await self._p10_started_or_completed(
                s, character.id
            ):
                return False
            if location == VDE_CLAUSTRO and not await has_unlock(
                VDE_BAIXIOS_CLAUSTRO_ROUTE
            ):
                return False
            if location == VDE_BERCO and not (
                await self._has_location(s, character.id, VDE_BERCO_LOCATION)
                and await has_unlock(VDE_CLAUSTRO_BERCO_ROUTE)
                and await self._nareth_mission_completed(s, character.id, "P11")
            ):
                return False
        elif region == "nareth":
            if not await self._p12_completed(s, character.id):
                return False
            if location == NARETH_POSTO_LABEL and not (
                await self._nareth_p13_started_or_completed(s, character.id)
                and await self._nareth_p13_route_open(s, character.id)
            ):
                return False
            for local, quest_id in (
                (NARETH_CANAIS, "P14"),
                (NARETH_CAMPOS, "P15"),
                (NARETH_OBSERVATORIO, "P16"),
            ):
                if location == local and not await self._nareth_mission_started_or_completed(
                    s, character.id, quest_id
                ):
                    return False
            for local, route_unlock in (
                (NARETH_CANAIS, NARETH_POSTO_CANAIS_ROUTE),
                (NARETH_CAMPOS, NARETH_CANAIS_CAMPOS_ROUTE),
                (NARETH_OBSERVATORIO, NARETH_CAMPOS_OBSERVATORIO_ROUTE),
            ):
                if location == local and not await has_unlock(route_unlock):
                    return False
            if location == NARETH_CAMARA_LABEL and not (
                await self._nareth_mission_started_or_completed(s, character.id, "P17")
                and await has_unlock("region.nareth.camara_arconte.available")
                and await has_unlock(NARETH_OBSERVATORIO_CAMARA_ROUTE)
            ):
                return False
        elif region == "varzeas":
            if not (
                await self._nareth_mission_completed(s, character.id, "P18")
                and await has_unlock(VARZEAS_REGION_ENTRY_UNLOCK)
            ):
                return False
            if location == VARZEAS_PORTO_LABEL and not (
                await self._nareth_mission_started_or_completed(s, character.id, "P19")
                and await has_unlock(VARZEAS_DIQUES_PORTO_ROUTE)
            ):
                return False
            if location == VARZEAS_BREJOS_LABEL and not (
                character.level >= 33
                and await self._nareth_mission_started_or_completed(s, character.id, "P20")
                and await has_unlock(VARZEAS_PORTO_BREJOS_ROUTE)
            ):
                return False
            if location == VARZEAS_HORTOS_LABEL and not (
                character.level >= 35
                and await self._nareth_mission_completed(s, character.id, "P20")
                and await self._nareth_mission_started_or_completed(s, character.id, "P21")
                and await has_unlock(VARZEAS_BREJOS_HORTOS_ROUTE)
            ):
                return False
            if location == VARZEAS_GALERIAS_LABEL and not (
                character.level >= 37
                and await self._nareth_mission_started_or_completed(s, character.id, "P22")
                and await has_unlock(VARZEAS_HORTOS_GALERIAS_ROUTE)
            ):
                return False
        elif region == "altos":
            if not (
                await self._nareth_mission_completed(s, character.id, "P24")
                and await has_unlock(ALTOS_ESCARPA_ACCESS_UNLOCK)
            ):
                return False
            if location == ALTOS_ABRIGO_LABEL and not await has_unlock(
                ALTOS_ABRIGO_ACCESS_UNLOCK
            ):
                return False
            for local, level, preceding_quest, access_unlock in (
                (ALTOS_PONTES_LABEL, 43, "P25", ALTOS_PONTES_ACCESS_UNLOCK),
                (ALTOS_PEDREIRAS_LABEL, 45, "P26", ALTOS_PEDREIRAS_ACCESS_UNLOCK),
                (ALTOS_BASTILHA_LABEL, 47, "P27", ALTOS_BASTILHA_ACCESS_UNLOCK),
            ):
                if location == local and not (
                    character.level >= level
                    and await self._nareth_mission_completed(
                        s, character.id, preceding_quest
                    )
                    and await has_unlock(access_unlock)
                ):
                    return False
            if location == ALTOS_CORACAO_LABEL and not (
                await self._nareth_mission_completed(s, character.id, "P29")
                and await has_unlock(ALTOS_CORACAO_ACCESS_UNLOCK)
            ):
                return False
        elif region == "confins":
            if not (
                await self._nareth_mission_completed(s, character.id, "P30")
                and await has_unlock(CONFINS_REGION_UNLOCK)
            ):
                return False
            if location == CONFINS_ULTIMO_REFUGIO_LABEL and not (
                await self._nareth_mission_started_or_completed(s, character.id, "P31")
                and await has_unlock(CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK)
            ):
                return False
            if location == CONFINS_ESTRADAS_AUSENTES_LABEL and not (
                character.level >= 53
                and await self._nareth_mission_completed(s, character.id, "P31")
                and await self._nareth_mission_started_or_completed(s, character.id, "P32")
                and await has_unlock(CONFINS_ESTRADAS_ACCESS_UNLOCK)
            ):
                return False
            if location == CONFINS_FRATURAS_LIMIAR_LABEL and not (
                character.level >= 55
                and await self._nareth_mission_completed(s, character.id, "P32")
                and await self._nareth_mission_started_or_completed(s, character.id, "P33")
                and await has_unlock(CONFINS_FRATURAS_ACCESS_UNLOCK)
            ):
                return False
            if location == CONFINS_NO_CENTRAL_LABEL and not (
                character.level >= 57
                and await self._nareth_mission_completed(s, character.id, "P33")
                and await self._nareth_mission_started_or_completed(s, character.id, "P34")
                and await has_unlock(CONFINS_NO_CENTRAL_ACCESS_UNLOCK)
            ):
                return False
        return True

    async def _travel(
        self,
        actor: int,
        destination: str,
        *,
        mode: str,
        brazier_id: str | None = None,
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if (
                c is None
                or world is None
                or destination not in TRAVEL_LOCATIONS
                or world.location not in TRAVEL_LOCATIONS
                or destination == world.location
            ):
                return None
            if mode == "brazier" and self._travel_region(world.location) != self._travel_region(destination):
                return None
            active_p2 = await s.scalar(
                select(Quest).where(
                    Quest.character_id == c.id,
                    Quest.quest_id == P2_QUEST_ID,
                    Quest.status == "active",
                )
            )
            if active_p2 is not None:
                return None
            active_p3 = await s.scalar(
                select(Quest).where(
                    Quest.character_id == c.id,
                    Quest.quest_id == P3_QUEST_ID,
                    Quest.status == "active",
                )
            )
            if active_p3 is not None:
                return None
            active_p4 = await s.scalar(
                select(Quest).where(
                    Quest.character_id == c.id,
                    Quest.quest_id == P4_QUEST_ID,
                    Quest.status == "active",
                )
            )
            if active_p4 is not None and mode == "brazier":
                return None
            if mode == "route":
                grant_route_unlock_on_arrival = False
                pair = next(
                    (
                        candidate
                        for candidate in OVERLAND_ROUTE_PAIRS
                        if {world.location, destination} == candidate
                    ),
                    None,
                )
                if pair is None:
                    return None
                if pair == CHARNECA_ROUTE_ENDPOINTS:
                    gate_ok = await self._p2_completed(s, c.id)
                    route_unlock = CHARNECA_ROUTE_UNLOCK
                elif pair == VDE_GARGANTA_VIGILIA_ROUTE_ENDPOINTS:
                    gate_ok = await self._p7_completed(s, c.id)
                    route_unlock = VDE_GARGANTA_VIGILIA_ROUTE
                elif pair == VDE_VIGILIA_MATA_ROUTE_ENDPOINTS:
                    gate_ok = (
                        c.level >= 13
                        and await self._p7_completed(s, c.id)
                        and await self._p8_started_or_completed(s, c.id)
                    )
                    route_unlock = VDE_VIGILIA_MATA_ROUTE
                elif pair == VDE_MATA_BAIXIOS_ROUTE_ENDPOINTS:
                    gate_ok = await self._p9_started_or_completed(s, c.id)
                    route_unlock = VDE_MATA_BAIXIOS_ROUTE
                elif pair == VDE_BAIXIOS_CLAUSTRO_ROUTE_ENDPOINTS:
                    gate_ok = await self._p10_started_or_completed(s, c.id)
                    route_unlock = VDE_BAIXIOS_CLAUSTRO_ROUTE
                elif pair == VDE_CLAUSTRO_BERCO_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        await self._has_location(s, c.id, VDE_BERCO_LOCATION)
                        and await s.scalar(
                            select(Quest.id).where(
                                Quest.character_id == c.id,
                                Quest.quest_id == "P11",
                                Quest.status == "completed",
                            )
                        )
                    )
                    route_unlock = VDE_CLAUSTRO_BERCO_ROUTE
                elif pair == NARETH_REGION_ROUTE_ENDPOINTS:
                    gate_ok = c.level >= 21 and await self._p12_completed(s, c.id)
                    route_unlock = NARETH_REGION_UNLOCK
                    if gate_ok:
                        await self._ensure(s, Unlock, character_id=c.id, unlock_id=route_unlock)
                elif pair == NARETH_CAMPINAS_POSTO_ROUTE_ENDPOINTS:
                    gate_ok = await self._nareth_p13_route_open(s, c.id)
                    route_unlock = NARETH_CAMPINAS_POSTO_ROUTE
                elif pair == NARETH_POSTO_CANAIS_ROUTE_ENDPOINTS:
                    gate_ok = await self._nareth_mission_started_or_completed(s, c.id, "P14")
                    route_unlock = NARETH_POSTO_CANAIS_ROUTE
                elif pair == NARETH_CANAIS_CAMPOS_ROUTE_ENDPOINTS:
                    gate_ok = await self._nareth_mission_started_or_completed(s, c.id, "P15")
                    route_unlock = NARETH_CANAIS_CAMPOS_ROUTE
                elif pair == NARETH_CAMPOS_OBSERVATORIO_ROUTE_ENDPOINTS:
                    gate_ok = await self._nareth_mission_started_or_completed(s, c.id, "P16")
                    route_unlock = NARETH_CAMPOS_OBSERVATORIO_ROUTE
                elif pair == NARETH_OBSERVATORIO_CAMARA_ROUTE_ENDPOINTS:
                    gate_ok = await self._nareth_mission_started_or_completed(s, c.id, "P17")
                    route_unlock = NARETH_OBSERVATORIO_CAMARA_ROUTE
                elif pair == NARETH_VARZEAS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 31
                        and await self._nareth_mission_completed(s, c.id, "P18")
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == VARZEAS_REGION_ENTRY_UNLOCK,
                            )
                        )
                    )
                    route_unlock = VARZEAS_REGION_ENTRY_UNLOCK
                elif pair == VARZEAS_DIQUES_PORTO_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        await self._nareth_mission_started_or_completed(s, c.id, "P19")
                    )
                    route_unlock = VARZEAS_DIQUES_PORTO_ROUTE
                elif pair == VARZEAS_PORTO_BREJOS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 33
                        and await self._nareth_mission_started_or_completed(s, c.id, "P20")
                    )
                    route_unlock = VARZEAS_PORTO_BREJOS_ROUTE
                elif pair == VARZEAS_BREJOS_HORTOS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 35
                        and await self._nareth_mission_completed(s, c.id, "P20")
                        and await self._nareth_mission_started_or_completed(s, c.id, "P21")
                    )
                    route_unlock = VARZEAS_BREJOS_HORTOS_ROUTE
                elif pair == VARZEAS_HORTOS_GALERIAS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 37
                        and await self._nareth_mission_started_or_completed(s, c.id, "P22")
                    )
                    route_unlock = VARZEAS_HORTOS_GALERIAS_ROUTE
                elif pair == VARZEAS_GALERIAS_CAMARA_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 39
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == VARZEAS_CAMARA_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = VARZEAS_GALERIAS_CAMARA_ROUTE
                elif pair == VARZEAS_CAMARA_ALTOS_ROUTE_ENDPOINTS:
                    if destination == ALTOS_ESCARPA_LABEL:
                        gate_ok = bool(
                            c.level >= 41
                            and await self._nareth_mission_completed(s, c.id, "P24")
                        )
                        route_unlock = ALTOS_ESCARPA_ACCESS_UNLOCK
                        grant_route_unlock_on_arrival = gate_ok
                    else:
                        gate_ok = bool(
                            await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == ALTOS_ESCARPA_ACCESS_UNLOCK,
                                )
                            )
                        )
                        route_unlock = VARZEAS_REGION_ENTRY_UNLOCK
                elif pair == ALTOS_ESCARPA_ABRIGO_ROUTE_ENDPOINTS:
                    if destination == ALTOS_ABRIGO_LABEL:
                        active_p25_step = await s.scalar(
                            select(Quest.id).where(
                                Quest.character_id == c.id,
                                Quest.quest_id == "P25",
                                Quest.status == "active",
                                Quest.step == 6,
                            )
                        )
                        gate_ok = bool(
                            active_p25_step
                            or await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == ALTOS_ABRIGO_ACCESS_UNLOCK,
                                )
                            )
                        )
                        route_unlock = ALTOS_ABRIGO_ACCESS_UNLOCK
                        grant_route_unlock_on_arrival = bool(active_p25_step)
                    else:
                        gate_ok = bool(
                            await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == ALTOS_ESCARPA_ACCESS_UNLOCK,
                                )
                            )
                        )
                        route_unlock = ALTOS_ESCARPA_ACCESS_UNLOCK
                elif pair == ALTOS_ABRIGO_PONTES_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 43
                        and await self._nareth_mission_completed(s, c.id, "P25")
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == ALTOS_PONTES_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = ALTOS_PONTES_ACCESS_UNLOCK
                elif pair == ALTOS_PONTES_PEDREIRAS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 45
                        and await self._nareth_mission_completed(s, c.id, "P26")
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == ALTOS_PEDREIRAS_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = ALTOS_PEDREIRAS_ACCESS_UNLOCK
                elif pair == ALTOS_PEDREIRAS_BASTILHA_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 47
                        and await self._nareth_mission_completed(s, c.id, "P27")
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = ALTOS_BASTILHA_ACCESS_UNLOCK
                elif pair == ALTOS_BASTILHA_CORACAO_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        await self._nareth_mission_completed(s, c.id, "P29")
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = ALTOS_CORACAO_ACCESS_UNLOCK
                elif pair == ALTOS_CONFINS_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        c.level >= 51
                        and await self._nareth_mission_completed(s, c.id, "P30")
                    )
                    route_unlock = CONFINS_REGION_UNLOCK
                    if gate_ok:
                        await self._ensure(
                            s, Unlock, character_id=c.id, unlock_id=route_unlock
                        )
                elif pair == CONFINS_MARCHA_REFUGIO_ROUTE_ENDPOINTS:
                    if destination == CONFINS_ULTIMO_REFUGIO_LABEL:
                        p31 = await s.scalar(
                            select(Quest).where(
                                Quest.character_id == c.id,
                                Quest.quest_id == "P31",
                                Quest.status == "active",
                                Quest.step == 5,
                            )
                        )
                        already_open = await self._has_location(
                            s, c.id, CONFINS_ULTIMO_REFUGIO_LOCATION
                        )
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and c.level >= 51
                            and (p31 is not None or already_open)
                        )
                        route_unlock = CONFINS_ULTIMO_REFUGIO_ACCESS_UNLOCK
                        grant_route_unlock_on_arrival = bool(p31 is not None)
                    else:
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and c.level >= 51
                            and await self._has_location(
                                s, c.id, CONFINS_ULTIMO_REFUGIO_LOCATION
                            )
                        )
                        route_unlock = CONFINS_MARCHA_ACCESS_UNLOCK
                elif pair == CONFINS_REFUGIO_ESTRADAS_ROUTE_ENDPOINTS:
                    p32 = await s.scalar(
                        select(Quest).where(
                            Quest.character_id == c.id,
                            Quest.quest_id == "P32",
                            Quest.status.in_(("active", "completed")),
                        )
                    )
                    if destination == CONFINS_ESTRADAS_AUSENTES_LABEL:
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and c.level >= 53
                            and await self._nareth_mission_completed(s, c.id, "P31")
                            and p32 is not None
                            and await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == CONFINS_ESTRADAS_ACCESS_UNLOCK,
                                )
                            )
                        )
                    else:
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and await self._has_location(
                                s, c.id, CONFINS_ESTRADAS_AUSENTES_LOCATION
                            )
                            and p32 is not None
                        )
                    route_unlock = CONFINS_ESTRADAS_ACCESS_UNLOCK
                elif pair == CONFINS_ESTRADAS_FRATURAS_ROUTE_ENDPOINTS:
                    p33 = await s.scalar(
                        select(Quest).where(
                            Quest.character_id == c.id,
                            Quest.quest_id == "P33",
                            Quest.status.in_(("active", "completed")),
                        )
                    )
                    if destination == CONFINS_FRATURAS_LIMIAR_LABEL:
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and c.level >= 55
                            and await self._nareth_mission_completed(s, c.id, "P32")
                            and p33 is not None
                            and await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == CONFINS_FRATURAS_ACCESS_UNLOCK,
                                )
                            )
                        )
                    else:
                        gate_ok = bool(
                            world.region == CONFINS_REGION
                            and await self._has_location(
                                s, c.id, CONFINS_FRATURAS_LIMIAR_LOCATION
                            )
                            and p33 is not None
                            and await s.scalar(
                                select(Unlock.id).where(
                                    Unlock.character_id == c.id,
                                    Unlock.unlock_id == CONFINS_FRATURAS_ACCESS_UNLOCK,
                                )
                            )
                        )
                    route_unlock = CONFINS_FRATURAS_ACCESS_UNLOCK
                elif pair == CONFINS_FRATURAS_NO_ROUTE_ENDPOINTS:
                    p34 = await s.scalar(
                        select(Quest).where(
                            Quest.character_id == c.id,
                            Quest.quest_id == "P34",
                            Quest.status.in_(("active", "completed")),
                        )
                    )
                    gate_ok = bool(
                        world.region == CONFINS_REGION
                        and c.level >= 57
                        and await self._nareth_mission_completed(s, c.id, "P33")
                        and p34 is not None
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = CONFINS_NO_CENTRAL_ACCESS_UNLOCK
                elif pair == CONFINS_NO_CAMARA_ROUTE_ENDPOINTS:
                    gate_ok = bool(
                        world.region == CONFINS_REGION
                        and await s.scalar(
                            select(Unlock.id).where(
                                Unlock.character_id == c.id,
                                Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                            )
                        )
                    )
                    route_unlock = CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK
                elif pair == BOSQUE_RUINS_ROUTE_ENDPOINTS:
                    gate_ok = (
                        await self._p4_completed(s, c.id)
                        and await self._ruins_route_level_gate(s, c)
                        and await self._has_location(s, c.id, RUINS_LOCATION)
                    )
                    route_unlock = RUINS_ROUTE_UNLOCK
                else:
                    gate_ok = await self._p3_completed(s, c.id)
                    route_unlock = BOSQUE_ROUTE_UNLOCK
                if not gate_ok or (
                    not grant_route_unlock_on_arrival
                    and not await s.scalar(
                        select(Unlock).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == route_unlock,
                        )
                    )
                ):
                    return None
            elif mode == "brazier":
                if brazier_id not in BRAZIER_DETAILS:
                    return None
                source_brazier = BRAZIER_FOR_LOCATION.get(world.location)
                if source_brazier is None or source_brazier == brazier_id:
                    return None
                if world.location in {CHARNECA, BOSQUE} or destination in {CHARNECA, BOSQUE}:
                    if not await self._p2_completed(s, c.id) or not await s.scalar(
                        select(Unlock).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == CHARNECA_ROUTE_UNLOCK,
                        )
                    ):
                        return None
                if world.location == BOSQUE or destination == BOSQUE:
                    if not await self._p3_completed(s, c.id):
                        return None
                if world.location == RUINS or destination == RUINS:
                    if (
                        c.level < 8
                        or not await self._p4_completed(s, c.id)
                        or not await self._has_location(s, c.id, RUINS_LOCATION)
                    ):
                        return None
                if world.location in {VDE_GARGANTA, VDE_VIGILIA} or destination in {
                    VDE_GARGANTA, VDE_VIGILIA,
                }:
                    if not await self._p7_completed(s, c.id):
                        return None
                if world.location == VDE_MATA or destination == VDE_MATA:
                    if not await self._p8_started_or_completed(s, c.id):
                        return None
                if world.location == VDE_BAIXIOS or destination == VDE_BAIXIOS:
                    if not await self._p9_started_or_completed(s, c.id):
                        return None
                if world.location == VDE_CLAUSTRO or destination == VDE_CLAUSTRO:
                    if not await self._p10_started_or_completed(s, c.id):
                        return None
                elif not await self._p1_completed(s, c.id):
                    return None
                source_known = await s.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == source_brazier,
                    )
                )
                target_known = await s.scalar(
                    select(Brazier).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == brazier_id,
                    )
                )
                if source_known is None or target_known is None:
                    return None
            else:
                return None
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id not in {
                    HUNT_CONTENT,
                    GROUP_HUNT_CONTENT,
                    PVPVE_QUEUE_CONTENT,
                    PVPVE_CONTENT,
                    EXPLORE_CONTENT,
                }:
                    return None
                if active.content_id == GROUP_HUNT_CONTENT:
                    return await self._road_blocking_view(s, c)
                if active.content_id in {PVPVE_QUEUE_CONTENT, PVPVE_CONTENT}:
                    return await self._road_blocking_view(s, c)
                if self._expired(active):
                    return await self._expire_activity(s, c, active)
                return await self._road_blocking_view(s, c)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            world.location = destination
            world.region = (
                CONFINS_REGION
                if destination in CONFINS_LOCATIONS or destination == CONFINS_CAMARA_REGENCIA_LABEL
                else ALTOS_REGION
                if destination in ALTOS_LOCATIONS
                else
                VARZEAS_REGION
                if destination in VARZEAS_LOCATIONS
                else
                NARETH_REGION
                if destination in NARETH_LOCATIONS
                else VDE_REGION
                if destination in VDE_LOCATIONS
                else REGION
            )
            if destination == CONFINS_NO_CENTRAL_LABEL:
                await self._ensure(
                    s,
                    LocationDiscovery,
                    character_id=c.id,
                    location_id=CONFINS_NO_CENTRAL_LOCATION,
                )
            elif destination == CONFINS_CAMARA_REGENCIA_LABEL:
                await self._ensure(
                    s,
                    LocationDiscovery,
                    character_id=c.id,
                    location_id=CONFINS_CAMARA_REGENCIA_LOCATION,
                )
            if mode == "route" and grant_route_unlock_on_arrival:
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=route_unlock,
                )
            if destination == VDE_BAIXIOS:
                await self._ensure(
                    s,
                    LocationDiscovery,
                    character_id=c.id,
                    location_id=VDE_BAIXIOS_LOCATION,
                )
            elif destination == NARETH_CAMPINAS_LABEL:
                await self._ensure(
                    s, LocationDiscovery, character_id=c.id, location_id=NARETH_CAMPINAS_LOCATION
                )
            elif destination == NARETH_POSTO_LABEL:
                await self._ensure(
                    s, LocationDiscovery, character_id=c.id, location_id=NARETH_POSTO_LOCATION
                )
            elif destination == NARETH_CANAIS:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_CANAIS_LOCATION)
            elif destination == NARETH_CAMPOS:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_CAMPOS_LOCATION)
            elif destination == NARETH_OBSERVATORIO:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_OBSERVATORIO_LOCATION)
            elif destination == NARETH_CAMARA_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_CAMARA_LOCATION)
            elif destination == VARZEAS_DIQUES_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_DIQUES_LOCATION)
            elif destination == VARZEAS_PORTO_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_PORTO_LOCATION)
            elif destination == VARZEAS_BREJOS_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_BREJOS_LOCATION)
            elif destination == VARZEAS_HORTOS_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_HORTOS_LOCATION)
            elif destination == VARZEAS_GALERIAS_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_GALERIAS_LOCATION)
            elif destination == VARZEAS_CAMARA_LABEL:
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=VARZEAS_CAMARA_LOCATION)
            elif destination == ALTOS_CORACAO_LABEL:
                await self._ensure(
                    s,
                    LocationDiscovery,
                    character_id=c.id,
                    location_id=ALTOS_CORACAO_LOCATION,
                )
            return await self._view_for_world(s, c, world)

    async def start_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            if world.location not in TRAVEL_LOCATIONS:
                return self._invalid_location_view(c, world)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            profile = await self._available_local_profile(s, c, world, "hunt")
            if profile is None:
                return None
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity)
                .where(GameActivity.character_id == c.id, GameActivity.status == "active")
                .with_for_update()
            )
            if active is not None:
                if active.content_id in {HUNT_CONTENT, PVPVE_QUEUE_CONTENT, PVPVE_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    return await self._combat_view(s, c, active)
                return await self._view_for_world(s, c, world)
            return await self.pvpve.queue_manual_hunt(s, c, world, profile)

    async def _materialize_manual_hunt(
        self,
        s,
        c,
        world,
        profile,
        *,
        activity: GameActivity | None = None,
        collision_id: UUID | None = None,
        domain_eligible: bool = False,
        reference_level: int | None = None,
        seed: str | None = None,
    ) -> RoadView:
        seed = seed or uuid4().hex
        creature = select_creature(seed, reference_level or c.level, profile=profile)
        level = min(reference_level or c.level, creature.max_level)
        variant = select_variant(seed, creature, profile=profile)
        combat_id = uuid4()
        equipment_configuration = await load_equipment_configuration(s, c)
        active_art_configuration = await load_active_art_configuration(s, c)
        reconcile_character_hp(c, equipment_configuration)
        combat = create_road_combat(
            combat_id,
            c.name,
            c.character_class,
            c.race,
            c.hp,
            creature,
            level,
            variant,
            player_level=c.level,
            equipment_configuration=equipment_configuration,
            location_label=profile.label,
            active_art_ids=active_art_configuration.art_ids,
        )
        combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
            active_art_configuration.to_data()
        )
        if activity is None:
            activity, _encounter, record = await CombatRepository(s).create(
                c, HUNT_CONTENT, combat
            )
        else:
            activity.content_id = HUNT_CONTENT
            activity.status = "active"
            activity.state_version = combat.version
            activity.ruleset_version = RULESET
            activity.last_valid_action_at = datetime.now(UTC)
            from asterion.infrastructure.db.models import CombatRecord, Encounter

            encounter = Encounter(id=uuid4(), game_activity_id=activity.id)
            s.add(encounter)
            await s.flush()
            record = CombatRecord(id=combat.id, encounter_id=encounter.id, snapshot=encode(combat))
            s.add(record)
            await s.flush()
        s.add(
            HuntContext(
                game_activity_id=activity.id,
                character_id=c.id,
                local_id=profile.local_id,
                creature_id=creature.creature_id,
                category=creature.category,
                enemy_level=level,
                variant=variant,
                seed=seed,
                loot_profile="hunt",
                pvpve_collision_id=collision_id,
                pvpve_reference_level=reference_level if collision_id is not None else None,
                pvpve_domain_eligible=domain_eligible,
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
        await self._record_charneca_habitat(s, c.id, creature.creature_id, profile)
        await s.flush()
        if combat.result == "defeat":
            return await self._settle_road_defeat(s, c, activity, combat, world, record=record)
        return await self._combat_view(s, c, activity)

    async def prepare_hunt(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            profile = await self._available_local_profile(s, c, world, "hunt")
            if profile is None:
                return None
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            return RoadView(
                "hunt_prepare",
                c.id,
                profile.label,
                vigor=c.vigor,
                max_vigor=c.max_vigor,
                name=c.name,
                hp=c.hp,
                max_hp=c.max_hp,
            )

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
    ) -> RoadView | None:
        handled, pvpve_view = await self.pvpve.handle_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if handled:
            return pvpve_view
        handled, group_view = await self.group_hunts.handle_action(
            actor,
            activity_id,
            version,
            action,
            consumable_id=consumable_id,
            target_id=target_id,
            effect_id=effect_id,
        )
        if handled:
            return group_view
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
                current = await self._combat_view(s, c, activity)
                if consumable_id is not None:
                    return replace(
                        current,
                        consumable_notice=self._consumable_rejection_notice(
                            current.combat, current.consumable_budget_limit
                        ),
                    )
                return current
            encounter, record = await CombatRepository(s).combat(activity)
            combat = decode(
                record.snapshot, record.id, activity.ruleset_version, activity.state_version
            )
            if consumable_id is None:
                if action is None:
                    return await self._combat_view(s, c, activity)
                updated = act(
                    combat,
                    action,
                    target_id=target_id,
                    effect_id=effect_id,
                )
            else:
                context = await s.scalar(
                    select(HuntContext).where(HuntContext.game_activity_id == activity.id)
                )
                budget_limit = (
                    ENCOUNTER_CONSUMABLE_LIMITS.get(context.category, 0)
                    if context is not None
                    else 0
                )
                stack = await s.scalar(
                    select(ConsumableStack)
                    .where(
                        ConsumableStack.character_id == c.id,
                        ConsumableStack.consumable_id == consumable_id,
                        ConsumableStack.quantity > 0,
                    )
                    .with_for_update()
                )
                if stack is None:
                    return replace(
                        await self._combat_view(s, c, activity),
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                before = combat.version
                updated = use_combat_consumable(
                    combat,
                    consumable_id,
                    target_id=target_id,
                    effect_id=effect_id,
                    budget_limit=budget_limit,
                )
                if updated.version == before:
                    current = await self._combat_view(s, c, activity)
                    notice = self._consumable_rejection_notice(current.combat, budget_limit)
                    return replace(
                        current,
                        consumable_notice=notice or "⚠️ Consumível · Não está mais disponível.",
                    )
                stack.quantity -= 1
            if updated.version == combat.version:
                return await self._combat_view(s, c, activity)
            activity.state_version = updated.version
            activity.last_valid_action_at = datetime.now(UTC)
            record.snapshot = encode(updated)
            c.hp = updated.fighters["player"].hp
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == activity.id)
            )
            bestiary_evidence_ids = set()
            if context is not None:
                bestiary_evidence_ids = await self._record_bestiary_combat_events(
                    s, c.id, context, updated
                )
            if updated.result == "victory":
                activity.status = "completed"
                if activity.content_id == HUNT_CONTENT:
                    await self._settle_hunt(s, c, activity, encounter.id, bestiary_evidence_ids)
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
                        await self._attempt_view(s, c, attempt)
                        if attempt is not None
                        else await self._combat_view(s, c, activity)
                    )
            elif updated.result == "defeat":
                return await self._settle_road_defeat(
                    s, c, activity, updated, world, context=context, record=record
                )
            return await self._combat_view(s, c, activity)

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
    ) -> RoadView | None:
        """Rebuild a read-only Consumable choice screen from current combat state."""
        pvpve_view = await self.pvpve.consumable_selection(
            actor,
            activity_id,
            version,
            screen=screen,
            item_id=item_id,
            target_id=target_id,
            parent=parent,
        )
        if pvpve_view is not None:
            return pvpve_view
        group_view = await self.group_hunts.consumable_selection(
            actor,
            activity_id,
            version,
            screen=screen,
            item_id=item_id,
            target_id=target_id,
            parent=parent,
        )
        if group_view is not None:
            return group_view
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or not await self._p1_completed(s, c.id):
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

            current = await self._combat_view(s, c, activity)
            if activity.state_version != version:
                return replace(
                    current,
                    consumable_notice=self._consumable_rejection_notice(
                        current.combat, current.consumable_budget_limit
                    ),
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
            item_options = tuple(
                option for option in current.consumable_options if option.item_id == item_id
            )
            if item is None or not item_options:
                if current.consumable_options:
                    return replace(
                        current,
                        consumable_screen="items",
                        consumable_notice="⚠️ Consumível · Não está mais disponível.",
                    )
                return current

            if screen == "choose_item":
                if item.family == ConsumableFamily.DISPELLER:
                    target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
                    if len(target_ids) > 1:
                        return replace(
                            current,
                            consumable_screen="targets",
                            selected_consumable_id=item.id,
                            selection_parent="items",
                        )
                    target_id = target_ids[0] if target_ids else None
                    parent = "items"
                else:
                    target_id = "player"
                    parent = "items"
                selected = tuple(option for option in item_options if option.target_id == target_id)
                return self._selection_after_target(
                    current, item, target_id, selected, parent=parent
                )

            if screen == "choose_target" and item.family == ConsumableFamily.DISPELLER:
                selected = tuple(option for option in item_options if option.target_id == target_id)
                if not selected:
                    return replace(
                        current,
                        consumable_screen="items" if current.consumable_options else None,
                        consumable_notice="⚠️ Dissipador · Sem Alvo Válido",
                    )
                return self._selection_after_target(
                    current, item, target_id, selected, parent="targets"
                )

            if screen == "targets" and item.family == ConsumableFamily.DISPELLER:
                target_ids = tuple(dict.fromkeys(option.target_id for option in item_options))
                if len(target_ids) > 1:
                    return replace(
                        current,
                        consumable_screen="targets",
                        selected_consumable_id=item.id,
                        selection_parent="items",
                    )
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice=(
                        "⚠️ Dissipador · Sem Alvo Válido" if not target_ids else None
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
                        current,
                        consumable_screen="effects",
                        selected_consumable_id=item.id,
                        selected_target_id=target_id,
                        selection_parent=parent,
                    )
                return replace(
                    current,
                    consumable_screen="items",
                    consumable_notice=(
                        "⚠️ Dissipador · Sem Efeito Removível"
                        if item.family == ConsumableFamily.DISPELLER and not selected
                        else "⚠️ Consumível · Não está mais disponível."
                        if not selected
                        else None
                    ),
                )

            return replace(
                current,
                consumable_screen="items",
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
            )

    @staticmethod
    def _selection_after_target(current, item, target_id, selected, *, parent):
        if not selected:
            return replace(
                current,
                consumable_screen="items" if current.consumable_options else None,
                consumable_notice="⚠️ Consumível · Não está mais disponível.",
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

    @staticmethod
    def _consumable_rejection_notice(combat, budget_limit):
        key = active_player_key(combat) or "player"
        player = combat.fighters.get(key) or combat.fighters.get("player")
        if player is None:
            return None
        if player.cooldowns.get("consumable", 0) > player.opportunity:
            return "⏳ Consumíveis · Em Recarga"
        if budget_limit and combat.consumable_uses >= budget_limit:
            return "🔒 Consumíveis · Limite Atingido"
        return None

    async def retry_hunt(self, actor: int) -> RoadView | None:
        return await self.prepare_hunt(actor)

    async def retry_blocked_deliveries(self, actor: int) -> bool:
        """Retry durable delivery holds without rerolling or duplicating loot."""
        async with self.sessions.begin() as s:
            character_id = await s.scalar(
                select(Character.id).where(
                    Character.telegram_id == actor, Character.server_id == self.server_id
                )
            )
            if character_id is None:
                return False
            try:
                c = await lock_for_combat_configuration_mutation(s, character_id)
            except CombatConfigurationLocked:
                return False
            if c is None:
                return False
            await self._retry_blocked_deliveries(s, c)
            return not c.delivery_blocked

    async def acknowledge_defeat(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None:
                return None
            if await self.pvpve.acknowledge_defeat(s, c):
                return await self._view_for_world(s, c, world) if world else None
            context = await s.scalar(
                select(HuntContext)
                .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
                .where(
                    HuntContext.character_id == c.id,
                    GameActivity.content_id.in_((HUNT_CONTENT, GROUP_HUNT_CONTENT)),
                    GameActivity.status == "failed",
                    HuntContext.result_acknowledged.is_(False),
                )
                .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
                .limit(1)
                .with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            return await self._view_for_world(s, c, world) if world else None

    async def acknowledge_result(
        self, actor: int, attempt_id: UUID | None = None
    ) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, _world = await self._locked_world(s, actor)
            if c is None:
                return None
            if attempt_id is not None:
                attempt = await s.scalar(
                    select(ExplorationAttempt)
                    .where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.id == attempt_id,
                        ExplorationAttempt.status.in_(("completed", "failed")),
                        ExplorationAttempt.result_acknowledged.is_(False),
                    )
                    .with_for_update()
                )
                if attempt is not None:
                    attempt.result_acknowledged = True
                blocking = await self._road_blocking_view(s, c)
                if blocking is not None:
                    return blocking
                world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
                return await self._view_for_world(s, c, world) if world else None
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
                .where(
                    HuntContext.character_id == c.id,
                    GameActivity.content_id.in_((HUNT_CONTENT, GROUP_HUNT_CONTENT)),
                    GameActivity.status.in_(("completed", "failed")),
                    HuntContext.result_acknowledged.is_(False),
                )
                .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
                .limit(1)
                .with_for_update()
            )
            if context is not None:
                context.result_acknowledged = True
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._view_for_world(s, c, world) if world else None

    async def explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            if world.location not in TRAVEL_LOCATIONS:
                return self._invalid_location_view(c, world)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            hunt_profile = await self._available_local_profile(s, c, world, "explore")
            if hunt_profile is None:
                return None
            explore_profile = EXPLORATION_PROFILES[hunt_profile.local_id]
            attempt_local_id = _exploration_local_id(hunt_profile)
            await self._retry_blocked_deliveries(s, c)
            if c.delivery_blocked:
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
                return (
                    await self._combat_view(s, c, active)
                    if attempt and attempt.status == "active"
                    else await self._attempt_view(s, c, attempt)
                )
            now = datetime.now(UTC)
            recent = (
                await s.scalar(
                    select(func.count(ExplorationAttempt.id)).where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                        ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                    )
                )
                or 0
            )
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            if recent >= 6:
                sixth = await s.scalar(
                    select(ExplorationAttempt)
                    .where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                        ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                    )
                    .order_by(ExplorationAttempt.created_at.desc())
                    .offset(5)
                    .limit(1)
                )
                return self._explore_limit_view(c, recent, last, now, sixth, hunt_profile.label)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now, location=hunt_profile.label)
            seed = uuid4().hex
            recent_rows = (
                await s.scalars(
                    select(ExplorationAttempt.result_id)
                    .where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                    )
                    .order_by(ExplorationAttempt.created_at.desc())
                    .limit(3)
                )
            ).all()
            unique_result_ids = tuple(
                item.result_id for item in explore_profile.results if item.unique
            )
            resolved_unique = tuple(
                (
                    await s.scalars(
                        select(ExplorationAttempt.result_id).where(
                            ExplorationAttempt.character_id == c.id,
                            ExplorationAttempt.local_id == attempt_local_id,
                            ExplorationAttempt.status == "completed",
                            ExplorationAttempt.result_id.in_(unique_result_ids),
                        )
                    )
                ).all()
            )
            if hunt_profile.local_id == VDE_CLAUSTRO_LOCATION and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VDE_SANCTUARY_UNLOCK,
                )
            ):
                # P10 and Desbravar claim the same canonical entrance. Once
                # either path records it, the unique exploration result is
                # exhausted and cannot grant its discovery XP again.
                resolved_unique = (*resolved_unique, "explore.vde.claustro.entrada_santuario_no_antigo")
            if hunt_profile.local_id == VARZEAS_GALERIAS_LOCATION and await s.scalar(
                select(Brazier.id).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == VARZEAS_GALERIAS_BRAZIER,
                )
            ):
                resolved_unique = (
                    *resolved_unique,
                    "explore.varzeas.galerias.braseiro_valvulas",
                )
            if hunt_profile.local_id == CONFINS_NO_CENTRAL_LOCATION:
                if await s.scalar(
                    select(Brazier.id).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == CONFINS_NO_RETORNO_BRAZIER,
                    )
                ):
                    resolved_unique = (*resolved_unique, "explore.confins.no.braseiro_retorno")
                if await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_CAMARA_CONTRADICOES_DUNGEON_UNLOCK,
                    )
                ):
                    resolved_unique = (*resolved_unique, "explore.confins.no.camara_contradicoes")
            offer = await desbravar_offer(
                s, c, explore_profile, attempt_local_id, self.latest_explorable_local, now
            )
            if offer.forced is not None:
                result = (offer.forced.category, offer.forced.result_id, offer.forced.text)
            else:
                result = _explore_result(
                    seed,
                    c.level,
                    tuple(str(item).rsplit(".", 1)[-1] for item in recent_rows),
                    tuple(str(item) for item in resolved_unique),
                    offer.profile,
                )
            category, result_id, result_text = result
            selected_creature_id = None
            if (
                category == "combat"
                and hunt_profile.local_id == CONFINS_MARCHA_LOCATION
            ):
                candidates = tuple(
                    (creature_id, weight)
                    for creature_id, weight in (
                        (CONFINS_CAO_NEVOA, 45),
                        (CONFINS_GRALHA_DUAS_SOMBRAS, 35),
                        (CONFINS_CERVO_PASSO_DUPLO, 20),
                    )
                    if c.level >= creature_for(creature_id).min_level
                )
                if not candidates:
                    raise RuntimeError("Confins exploration combat has no level-eligible creature")
                selected_creature_id = weighted_choice(seed, candidates)
                result_text = f"Combate · {creature_for(selected_creature_id).name}"
            elif (
                category == "combat"
                and hunt_profile.local_id == CONFINS_ESTRADAS_AUSENTES_LOCATION
            ):
                candidates = tuple(
                    (creature_id, weight)
                    for creature_id, weight in (
                        (CONFINS_ANDARILHO_REPETIDO, 30),
                        (CONFINS_ARANHA_LIMIAR, 30),
                        (CONFINS_GRALHA_DUAS_SOMBRAS, 20),
                        (CONFINS_CAO_NEVOA, 20),
                    )
                    if creature_for(creature_id).min_level
                    <= c.level
                    <= creature_for(creature_id).max_level
                )
                if not candidates:
                    raise RuntimeError("Confins exploration combat has no level-eligible creature")
                selected_creature_id = weighted_choice(seed, candidates)
                result_text = f"Combate · {creature_for(selected_creature_id).name}"
            elif (
                category == "combat"
                and hunt_profile.local_id == CONFINS_FRATURAS_LIMIAR_LOCATION
            ):
                candidates = tuple(
                    (creature_id, weight)
                    for creature_id, weight in (
                        (CONFINS_ARANHA_LIMIAR, 20),
                        (CONFINS_CERVO_PASSO_DUPLO, 20),
                        (CONFINS_SANGUESSUGA_PALIDA, 20),
                        (CONFINS_CASCA_REFLEXO, 20),
                        (CONFINS_MARIPOSA_SEM_HORIZONTE, 20),
                    )
                    if creature_for(creature_id).min_level
                    <= c.level
                    <= creature_for(creature_id).max_level
                )
                if not candidates:
                    raise RuntimeError("Confins exploration combat has no level-eligible creature")
                selected_creature_id = weighted_choice(seed, candidates)
                result_text = f"Combate · {creature_for(selected_creature_id).name}"
            elif category == "combat" and hunt_profile.local_id == CONFINS_NO_CENTRAL_LOCATION:
                candidates = tuple(
                    (creature_id, weight)
                    for creature_id, weight in (
                        (CONFINS_SANGUESSUGA_PALIDA, 20),
                        (CONFINS_CASCA_REFLEXO, 25),
                        (CONFINS_MARIPOSA_SEM_HORIZONTE, 20),
                        (CONFINS_VIGIA_DESFASADO, 35),
                    )
                    if creature_for(creature_id).min_level
                    <= c.level
                    <= creature_for(creature_id).max_level
                )
                if not candidates:
                    raise RuntimeError("Confins exploration combat has no level-eligible creature")
                selected_creature_id = weighted_choice(seed, candidates)
                result_text = f"Combate · {creature_for(selected_creature_id).name}"
            attempt = ExplorationAttempt(
                character_id=c.id,
                local_id=attempt_local_id,
                ruleset_version=RULESET,
                seed=seed,
                category=category,
                result_id=result_id,
                status="active" if category == "combat" else "completed",
                state_version=0 if category == "combat" else 1,
                progress={
                    "result_text": result_text,
                    **({"creature_id": selected_creature_id} if selected_creature_id else {}),
                    **(
                        {"chronicle_objective": offer.objective_id}
                        if offer.objective_id and is_chronicle_result(result_id)
                        else {}
                    ),
                },
            )
            s.add(attempt)
            await s.flush()
            if category == "combat":
                result_definition = next(
                    (item for item in explore_profile.results if item.result_id == result_id),
                    None,
                )
                creature_id = selected_creature_id or (
                    result_definition.creature_id if result_definition is not None else None
                )
                if creature_id is None:
                    raise RuntimeError(f"combat exploration result {result_id!r} has no creature")
                creature = creature_for(creature_id)
                level = min(c.level, creature.max_level)
                variant = select_variant(seed, creature, profile=hunt_profile)
                equipment_configuration = await load_equipment_configuration(s, c)
                active_art_configuration = await load_active_art_configuration(s, c)
                reconcile_character_hp(c, equipment_configuration)
                combat = create_road_combat(
                    uuid4(),
                    c.name,
                    c.character_class,
                    c.race,
                    c.hp,
                    creature,
                    level,
                    variant,
                    player_level=c.level,
                    equipment_configuration=equipment_configuration,
                    location_label=hunt_profile.label,
                    active_art_ids=active_art_configuration.art_ids,
                )
                combat.configuration_snapshot = (combat.configuration_snapshot or {}) | (
                    active_art_configuration.to_data()
                )
                activity, encounter, record = await CombatRepository(s).create(
                    c, EXPLORE_CONTENT, combat
                )
                attempt.activity_id = activity.id
                attempt.encounter_id = encounter.id
                s.add(
                    HuntContext(
                        game_activity_id=activity.id,
                        character_id=c.id,
                        local_id=hunt_profile.local_id,
                        creature_id=creature.creature_id,
                        category=creature.category,
                        enemy_level=level,
                        variant=variant,
                        seed=seed,
                        loot_profile="exploration_combat",
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
                await self._record_charneca_habitat(s, c.id, creature_id, hunt_profile)
                await s.flush()
                if combat.result == "defeat":
                    return await self._settle_road_defeat(
                        s, c, activity, combat, world, record=record
                    )
                return await self._combat_view(s, c, activity)
            await self._settle_exploration(s, c, attempt)
            return await self._attempt_view(s, c, attempt)

    async def prepare_explore(self, actor: int) -> RoadView | None:
        async with self.sessions.begin() as s:
            c, world = await self._locked_world(s, actor)
            if c is None or world is None:
                return None
            hunt_profile = await self._available_local_profile(s, c, world, "explore")
            if hunt_profile is None:
                return None
            attempt_local_id = _exploration_local_id(hunt_profile)
            blocking = await self._road_blocking_view(s, c)
            if blocking is not None:
                return blocking
            if c.delivery_blocked:
                return await self._view_for_world(s, c, world)
            active = await s.scalar(
                select(GameActivity).where(
                    GameActivity.character_id == c.id, GameActivity.status == "active"
                )
            )
            if active is not None:
                if active.content_id in {HUNT_CONTENT, EXPLORE_CONTENT}:
                    if self._expired(active):
                        return await self._expire_activity(s, c, active)
                    if active.content_id == HUNT_CONTENT:
                        return await self._combat_view(s, c, active)
                    attempt = await s.scalar(
                        select(ExplorationAttempt).where(
                            ExplorationAttempt.activity_id == active.id
                        )
                    )
                    return (
                        await self._combat_view(s, c, active)
                        if attempt and attempt.status == "active"
                        else await self._attempt_view(s, c, attempt)
                    )
                return None
            now = datetime.now(UTC)
            recent = (
                await s.scalar(
                    select(func.count(ExplorationAttempt.id)).where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                        ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                    )
                )
                or 0
            )
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            if recent >= 6:
                sixth = await s.scalar(
                    select(ExplorationAttempt)
                    .where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                        ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                    )
                    .order_by(ExplorationAttempt.created_at.desc())
                    .offset(5)
                    .limit(1)
                )
                return self._explore_limit_view(c, recent, last, now, sixth, hunt_profile.label)
            if last and last.created_at and last.created_at > now - timedelta(minutes=5):
                return self._explore_limit_view(c, recent, last, now, location=hunt_profile.label)
            return RoadView(
                "explore_prepare",
                c.id,
                hunt_profile.label,
                vigor=c.vigor,
                max_vigor=c.max_vigor,
                name=c.name,
                hp=c.hp,
                max_hp=c.max_hp,
            )

    async def _settle_hunt(
        self,
        s,
        c,
        activity,
        encounter_id,
        bestiary_evidence_ids=frozenset(),
        *,
        equipment_configuration: EquipmentConfigurationSnapshot | None = None,
        now: datetime | None = None,
    ):
        await reconcile_character_vigor(s, c, now=now)
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id).with_for_update()
        )
        if context is None:
            return 0
        if context.category not in {"common", "uncommon", "elite"}:
            raise ValueError(f"Hunt settlement is not configured for {context.category!r}")
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
        xp = enemy_xp(
            context.enemy_level,
            context.category,
            factor,
            player_level=c.level,
            legacy_factor=legacy_xp_factor(c.legacy_level),
        )
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
                else 1 + _draw_int(context.seed, "uncommon-materials", 2)
                if context.category == "uncommon"
                else 3 + _draw_int(context.seed, "elite-materials", 2)
            )
            for ordinal in range(material_count):
                # Regional source tables select each already-awarded basic
                # material unit with its own persisted-seed ordinal.
                if (
                    context.creature_id in VDE_BASIC_MATERIAL_CREATURE_IDS
                    or context.creature_id in NARETH_BASIC_MATERIAL_CREATURE_IDS
                    or context.creature_id in VARZEAS_BASIC_MATERIAL_CREATURE_IDS
                    or context.creature_id in ALTOS_BASIC_MATERIAL_CREATURE_IDS
                    or context.creature_id in CONFINS_BASIC_MATERIAL_CREATURE_IDS
                ):
                    material_seed = f"{context.seed}:material.basic.{ordinal}"
                elif context.category == "common" and ordinal == 0:
                    material_seed = context.seed
                else:
                    material_seed = f"{context.seed}:material:{ordinal}"
                material = material_for(context.creature_id, material_seed)
                components.append(
                    ("material", material, 1, {"material_id": material, "bound": False})
                )
                await self._deliver_material(
                    s, c, material, 1, f"activity:{activity.id}:material:{ordinal}"
                )
            if context.category == "elite":
                components.append(
                    ("catalyst", _grade_catalyst_for_level(context.enemy_level), 1, {})
                )
                if _draw_int(context.seed, "fragment", 100) < 40:
                    components.append(
                        ("fragment", _grade_fragment_for_level(context.enemy_level), 1, {})
                    )
            elif context.category == "uncommon" and _draw_int(context.seed, "fragment", 100) < 5:
                components.append(
                    ("fragment", _grade_fragment_for_level(context.enemy_level), 1, {})
                )
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
        if context.pvpve_collision_id is not None:
            await self.pvpve.settle_domain(
                s,
                c,
                activity,
                context,
                event,
                components,
                paid=enough,
            )
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
        profile = hunt_profile_for_local_id(context.local_id)
        round_gate_quest = {
            ALTOS_ESCARPA_LOCATION: "P25",
            ALTOS_PONTES_LOCATION: "P26",
            ALTOS_PEDREIRAS_LOCATION: "P27",
            ALTOS_BASTILHA_LOCATION: "P28",
            CONFINS_MARCHA_LOCATION: "P31",
            CONFINS_ESTRADAS_AUSENTES_LOCATION: "P32",
            CONFINS_FRATURAS_LIMIAR_LOCATION: "P33",
            CONFINS_NO_CENTRAL_LOCATION: "P34",
        }.get(context.local_id)
        if round_gate_quest is None or await self._nareth_mission_completed(
            s, c.id, round_gate_quest
        ):
            await self._ensure(
                s,
                Unlock,
                character_id=c.id,
                unlock_id=profile.round_familiarity,
            )
        await consolidate_character_level(s, c, equipment_configuration)
        if context.pvpve_collision_id is not None:
            await self.pvpve.finish_prey_member(
                s, context.pvpve_collision_id, c.id, victory=True
            )
        return xp

    async def _materialize_optional_loot(self, s, c, context, components):
        equipment_chance = {"common": 8, "uncommon": 14, "elite": 35}[context.category]
        rune_chance = {"common": 5, "uncommon": 15, "elite": 50}[context.category]
        if _draw_int(context.seed, "equipment", 100) < equipment_chance:
            rarity = equipment_rarity(
                context.seed,
                context.category,
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
            item_instance_id, item = equipment_instance_payload(item)
            if await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
                s.add(
                    EquipmentItem(
                        id=item_instance_id,
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
                if await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
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
                rune_payload = {
                    "family": family,
                    "rarity": rarity,
                    "grade": stack.grade,
                    "potency": stack.potency,
                    "bound": stack.bound,
                }
                if stack.quantity > 0 or await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
                    stack.quantity += 1
                else:
                    await self._pending(
                        s,
                        c.id,
                        f"activity:{context.game_activity_id}:rune",
                        "rune",
                        rune_payload,
                    )
            components.append(("rune", family, 1, rune_payload))

    async def _settle_exploration(self, s, c, attempt):
        if (attempt.progress or {}).get("settled"):
            return
        await reconcile_character_vigor(s, c)
        if is_chronicle_result(attempt.result_id):
            await settle_desbravar(s, c, attempt, datetime.now(UTC))
            return
        base_text = (attempt.progress or {}).get("result_text", "")
        if attempt.local_id in {
            ALTOS_ESCARPA_LOCATION,
            ALTOS_PONTES_LOCATION,
            ALTOS_PEDREIRAS_LOCATION,
            ALTOS_BASTILHA_LOCATION,
        }:
            await self._settle_altos_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == CONFINS_MARCHA_LOCATION:
            await self._settle_confins_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == CONFINS_ESTRADAS_AUSENTES_LOCATION:
            await self._settle_confins_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == CONFINS_FRATURAS_LIMIAR_LOCATION:
            await self._settle_confins_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == CONFINS_NO_CENTRAL_LOCATION:
            await self._settle_confins_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == CHARNECA_LOCATION:
            await self._settle_charneca_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == BOSQUE_LOCATION:
            await self._settle_bosque_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id == RUINS_LOCATION:
            await self._settle_ruins_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id in {
            NARETH_CAMPINAS_LOCATION,
            NARETH_CANAIS_LOCATION,
            NARETH_CAMPOS_LOCATION,
            NARETH_OBSERVATORIO_LOCATION,
        }:
            await self._settle_nareth_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id in {VARZEAS_DIQUES_LOCATION, VARZEAS_BREJOS_LOCATION, VARZEAS_HORTOS_LOCATION, VARZEAS_GALERIAS_LOCATION}:
            await self._settle_varzeas_exploration(s, c, attempt, base_text)
            return
        if attempt.local_id in {
            VDE_GARGANTA_LOCATION,
            VDE_MATA_LOCATION,
            VDE_BAIXIOS_LOCATION,
            VDE_CLAUSTRO_LOCATION,
        }:
            await self._settle_vde_exploration(s, c, attempt, base_text)
            return
        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == attempt.activity_id)
            )
            if context is not None:
                source_id = f"explore:{attempt.id}"
                event = await s.scalar(
                    select(RewardEvent)
                    .where(
                        RewardEvent.character_id == c.id,
                        RewardEvent.source_id == source_id,
                    )
                    .with_for_update()
                )
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
                    legacy_factor=legacy_xp_factor(c.legacy_level),
                )
                c.xp += xp
                components = [("xp", None, xp, {})]
                receipt_lines = [base_text, f"✨ XP · {xp}"]
                if c.vigor >= 4:
                    c.vigor -= 4
                    # Exploration combat pays the normal repeatable currency
                    # coefficient, independently of the full Hunt reward.
                    crowns_award = int(
                        ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10).quantize(
                            Decimal(1), rounding=ROUND_HALF_EVEN
                        )
                        * 10
                    )
                    c.crowns += crowns_award
                    components.append(("crowns", None, crowns_award, {}))
                    receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                    pool = (
                        ("material.tdo.ferro_de_fuligem", 30),
                        ("material.tdo.couro_escoriado", 30),
                        ("material.tdo.erva_cinzenta", 20),
                        ("material.tdo.residuo_ocaso", 20),
                    )
                    units = 1 + (
                        1 if _draw_int(attempt.seed, "exploration-material-extra", 100) < 20 else 0
                    )
                    for ordinal in range(units):
                        material = weighted_choice(
                            f"{attempt.seed}:exploration-material:{ordinal}", pool
                        )
                        components.append(("material", material, 1, {"material_id": material}))
                        receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                        await self._deliver_material(
                            s, c, material, 1, f"explore:{attempt.id}:material:{ordinal}"
                        )
                bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
                if bestiary_update is not None:
                    components.append(("bestiary", context.creature_id, 1, bestiary_update))
                    receipt_lines.append(
                        f"📖 Bestiário · {bestiary_update['creature_name']} · "
                        f"{bestiary_update['stage_label']}"
                    )
                for kind, item_id, quantity, payload in components:
                    s.add(
                        RewardComponent(
                            reward_event_id=event.id,
                            kind=kind,
                            item_id=item_id,
                            quantity=quantity,
                            payload=payload,
                        )
                    )
                attempt.progress = {
                    **(attempt.progress or {}),
                    "receipt_text": "\n\n".join(receipt_lines),
                    "settled": True,
                }
                attempt.completed_at = attempt.completed_at or datetime.now(UTC)
                await consolidate_character_level(s, c)
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
                    await self._deliver_material(
                        s, c, material, 1, f"explore:{attempt.id}:resource"
                    )
            attempt.progress = {
                **(attempt.progress or {}),
                "receipt_text": "\n\n".join(receipt_lines),
                "settled": True,
            }
            attempt.completed_at = attempt.completed_at or datetime.now(UTC)
            await consolidate_character_level(s, c)
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
                entry = await s.scalar(
                    select(BestiaryEntry).where(
                        BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == creature
                    )
                )
                habitat = await s.scalar(
                    select(BestiaryEvidence).where(
                        BestiaryEvidence.character_id == c.id,
                        BestiaryEvidence.creature_id == creature,
                        BestiaryEvidence.evidence_id == "habitat:estrada",
                    )
                )
                if c.level >= profile.unlock_level and entry is not None:
                    identifiable.append(creature)
                    if habitat is None:
                        without_habitat.append(creature)
            eligible = without_habitat or identifiable
            if eligible:
                chosen = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(
                    select(BestiaryEntry)
                    .where(BestiaryEntry.character_id == c.id, BestiaryEntry.creature_id == chosen)
                    .with_for_update()
                )
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
        await consolidate_character_level(s, c)

    async def _settle_vde_exploration(self, s, c, attempt, base_text: str) -> None:
        """Settle VDE Desbravar without requiring Hunt/Round creature drops.

        Regional resource outcomes name their own material. Exploration combat
        retains its normal XP, crown, and Bestiary effects, but does not invent
        a creature-to-material mapping absent from the regional source.
        """
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Vales exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * context.enemy_level) * Decimal("0.15"))
                        / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
            bestiary = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(
                    f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}"
                )
            should_consolidate = True

        elif attempt.category == "resource":
            material_id = VDE_EXPLORATION_RESOURCE_MATERIALS.get(attempt.result_id)
            if material_id is None:
                raise RuntimeError(
                    f"unknown Vales exploration resource result {attempt.result_id!r}"
                )
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * c.level) * Decimal("0.10"))
                        / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.extend(
                    (
                        ("crowns", None, award, {}),
                        ("material", material_id, 1, {"material_id": material_id}),
                    )
                )
                lines.extend(
                    (f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material_id]} · 1")
                )
                await self._deliver_material(
                    s, c, material_id, 1, f"explore:{attempt.id}:resource"
                )

        else:
            xp = VDE_EXPLORATION_UNIQUE_XP.get(attempt.result_id, 0)
            if xp:
                c.xp += xp
                components.append(("xp", None, xp, {}))
                lines.append(f"✨ XP · {xp}")
                should_consolidate = True
            if attempt.result_id == "explore.vde.mata.braseiro_das_copas":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=VDE_MATA_BRAZIER)
                await self._ensure(
                    s, LocationDiscovery, character_id=c.id, location_id=VDE_MATA_LOCATION
                )
                components.append(("brazier", VDE_MATA_BRAZIER, 1, {}))
            elif attempt.result_id == "explore.vde.baixios.braseiro_turfa_fria":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=VDE_BAIXIOS_BRAZIER)
                await self._ensure(
                    s, LocationDiscovery, character_id=c.id, location_id=VDE_BAIXIOS_LOCATION
                )
                components.append(("brazier", VDE_BAIXIOS_BRAZIER, 1, {}))
            elif attempt.result_id == "explore.vde.claustro.braseiro_pedras_enlacadas":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=VDE_CLAUSTRO_BRAZIER)
                await self._ensure(
                    s, LocationDiscovery, character_id=c.id, location_id=VDE_CLAUSTRO_LOCATION
                )
                components.append(("brazier", VDE_CLAUSTRO_BRAZIER, 1, {}))
            elif attempt.result_id == "explore.vde.claustro.entrada_santuario_no_antigo":
                await self._ensure(s, Unlock, character_id=c.id, unlock_id=VDE_SANCTUARY_UNLOCK)
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.mystery.o_no_antigo")
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id="codex.mystery.o_no_antigo",
                    fragment_id="codex.fragment.no_antigo.entrada_santuario_descoberta",
                )
                from asterion.application.vde_feats import reconcile_vde_feats

                await reconcile_vde_feats(s, c)
            elif attempt.result_id == "explore.vde.mata.entrada_fosso_raizes":
                if await self._ensure(
                    s, Unlock, character_id=c.id, unlock_id=FOSSO_DISCOVERY_UNLOCK
                ):
                    components.append(("unlock", FOSSO_DISCOVERY_UNLOCK, 1, {}))
                await self._ensure(
                    s,
                    CodexEntry,
                    character_id=c.id,
                    entry_id="codex.location.fosso_das_raizes",
                )
                from asterion.application.vde_feats import reconcile_vde_feats

                await reconcile_vde_feats(s, c)

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)

    async def _settle_nareth_exploration(self, s, c, attempt, base_text: str) -> None:
        """Settle the authored Campinas outcomes without inventing creature drops."""
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == c.id, RewardEvent.source_id == source_id)
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Nareth exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
            bestiary = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}")
            should_consolidate = True
        elif attempt.category == "resource":
            material_id = NARETH_EXPLORATION_RESOURCE_MATERIALS.get(attempt.result_id)
            if material_id is None:
                raise RuntimeError(f"unknown Nareth exploration resource {attempt.result_id!r}")
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.extend(
                    (
                        ("crowns", None, award, {}),
                        ("material", material_id, 1, {"material_id": material_id}),
                    )
                )
                lines.extend((f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material_id]} · 1"))
                await self._deliver_material(s, c, material_id, 1, f"explore:{attempt.id}:resource")
        else:
            xp = NARETH_EXPLORATION_UNIQUE_XP.get(attempt.result_id, 0)
            if xp:
                c.xp += xp
                components.append(("xp", None, xp, {}))
                lines.append(f"✨ XP · {xp}")
                should_consolidate = True
            if attempt.result_id == "explore.nareth.campinas.marco_primeiro_meridiano":
                await self._ensure(
                    s,
                    CodexEntry,
                    character_id=c.id,
                    entry_id="codex.location.campinas_do_meridiano",
                )
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id="codex.location.campinas_do_meridiano",
                    fragment_id="codex.fragment.nareth.campinas.meridian_marker",
                )
            elif attempt.result_id == "explore.nareth.campinas.duas_medidas_mesma_estrada":
                await self._ensure(
                    s, CodexEntry, character_id=c.id, entry_id="codex.route.rotas_de_nareth"
                )
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id="codex.route.rotas_de_nareth",
                    fragment_id="codex.fragment.nareth.campinas.divergent_measures",
                )
            elif attempt.result_id == "explore.nareth.canais.braseiro_canal_alto":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=NARETH_BRAZIER_CANAIS)
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_CANAIS_LOCATION)
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.canais_secos")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.location.canais_secos", fragment_id="codex.fragment.nareth.canais.brazier")
                components.append(("brazier", NARETH_BRAZIER_CANAIS, 1, {}))
            elif attempt.result_id == "explore.nareth.canais.entrada_galerias_meridiano":
                await self._ensure(s, Unlock, character_id=c.id, unlock_id="dungeon.nareth.galerias_meridiano")
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.galerias_do_meridiano")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.location.galerias_do_meridiano", fragment_id="codex.fragment.nareth.galerias.entry")
            elif attempt.result_id == "explore.nareth.canais.comporta_sem_agua":
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.history.rede_de_medicao")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.history.rede_de_medicao", fragment_id="codex.fragment.nareth.canais.measurement_gate")
            elif attempt.result_id == "explore.nareth.campos.braseiro_linha_quebrada":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=NARETH_BRAZIER_CAMPOS)
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_CAMPOS_LOCATION)
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.campos_invertidos")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.location.campos_invertidos", fragment_id="codex.fragment.nareth.campos.brazier")
                components.append(("brazier", NARETH_BRAZIER_CAMPOS, 1, {}))
            elif attempt.result_id == "explore.nareth.campos.linha_que_nao_fecha":
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.mystery.linha_que_nao_fecha")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.mystery.linha_que_nao_fecha", fragment_id="codex.fragment.nareth.campos.line_does_not_close")
            elif attempt.result_id == "explore.nareth.observatorio.braseiro_do_eixo":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=NARETH_BRAZIER_OBSERVATORIO)
                await self._ensure(s, LocationDiscovery, character_id=c.id, location_id=NARETH_OBSERVATORIO_LOCATION)
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.observatorio_do_eixo")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.location.observatorio_do_eixo", fragment_id="codex.fragment.nareth.observatory.brazier")
                components.append(("brazier", NARETH_BRAZIER_OBSERVATORIO, 1, {}))
            elif attempt.result_id == "explore.nareth.observatorio.entrada_observatorio_afundado":
                await self._ensure(s, Unlock, character_id=c.id, unlock_id="dungeon.nareth.observatorio_afundado")
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.observatorio_afundado")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.location.observatorio_afundado", fragment_id="codex.fragment.nareth.observatory.submerged_entry")
            elif attempt.result_id == "explore.nareth.observatorio.prumo_fora_do_centro":
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.mystery.o_eixo")
                await self._ensure(s, CodexFragment, character_id=c.id, entry_id="codex.mystery.o_eixo", fragment_id="codex.fragment.nareth.observatory.off_center_plumb")

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {**(attempt.progress or {}), "receipt_text": "\n\n".join(lines), "settled": True}
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)

    async def _settle_varzeas_exploration(self, s, c, attempt, base_text: str) -> None:
        """Settle published Várzeas exploration outcomes with the shared road economy."""
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(RewardEvent.character_id == c.id, RewardEvent.source_id == source_id)
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Varzeas exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
            bestiary = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}")
            should_consolidate = True
        elif attempt.category == "resource":
            material_id = VARZEAS_EXPLORATION_RESOURCE_MATERIALS.get(attempt.result_id)
            if material_id is None:
                raise RuntimeError(f"unknown Varzeas exploration resource {attempt.result_id!r}")
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10)
                    .quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.extend(
                    (("crowns", None, award, {}), ("material", material_id, 1, {"material_id": material_id}))
                )
                lines.extend((f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material_id]} · 1"))
                await self._deliver_material(s, c, material_id, 1, f"explore:{attempt.id}:resource")
        else:
            xp = VARZEAS_EXPLORATION_UNIQUE_XP.get(attempt.result_id, 0)
            if (
                attempt.result_id == "explore.varzeas.galerias.braseiro_valvulas"
                and await s.scalar(
                    select(Brazier.id).where(
                        Brazier.character_id == c.id,
                        Brazier.brazier_id == VARZEAS_GALERIAS_BRAZIER,
                    )
                )
            ):
                # P22 and Desbravar share this one canonical discovery reward.
                xp = 0
            if xp:
                c.xp += xp
                components.append(("xp", None, xp, {}))
                lines.append(f"✨ XP · {xp}")
                should_consolidate = True
            if attempt.result_id == "explore.varzeas.diques.comporta_primeiro_dique":
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id="codex.location.diques_rubros")
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id="codex.location.diques_rubros",
                    fragment_id="codex.fragment.varzeas.diques.comporta_primeiro_dique",
                )
            elif attempt.local_id == VARZEAS_BREJOS_LOCATION:
                await self._ensure(
                    s,
                    CodexEntry,
                    character_id=c.id,
                    entry_id="codex.location.brejos_do_pulso",
                )
                if attempt.result_id == "explore.varzeas.brejos.braseiro_juncos_baixos":
                    await self._ensure(s, Brazier, character_id=c.id, brazier_id=VARZEAS_BREJOS_BRAZIER)
                    await self._ensure(
                        s,
                        CodexFragment,
                        character_id=c.id,
                        entry_id="codex.location.brejos_do_pulso",
                        fragment_id="codex.fragment.varzeas.brejos.braseiro_juncos_baixos",
                    )
                elif attempt.result_id == "explore.varzeas.brejos.entrada_enfermaria_afundada":
                    await self._ensure(
                        s,
                        Unlock,
                        character_id=c.id,
                        unlock_id="dungeon.varzeas.enfermaria_afundada.discovered",
                    )
                    await self._ensure(
                        s,
                        CodexFragment,
                        character_id=c.id,
                        entry_id="codex.location.brejos_do_pulso",
                        fragment_id="codex.fragment.varzeas.brejos.entrada_enfermaria_afundada",
                    )
                elif attempt.result_id == "explore.varzeas.brejos.pulso_de_pressao":
                    await self._ensure(
                        s,
                        CodexEntry,
                        character_id=c.id,
                        entry_id="codex.mystery.pulso_sob_a_lama",
                    )
                    await self._ensure(
                        s,
                        CodexFragment,
                        character_id=c.id,
                        entry_id="codex.mystery.pulso_sob_a_lama",
                        fragment_id="codex.fragment.varzeas.brejos.pulso_de_pressao",
                    )
            elif attempt.local_id == VARZEAS_HORTOS_LOCATION:
                entry_id = "codex.location.hortos_hemaris"
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                fragment_id = {
                    "explore.varzeas.hortos.braseiro_horto_seco": "codex.fragment.varzeas.hortos.braseiro_horto_seco",
                    "explore.varzeas.hortos.estufa_restituicao": (
                        "codex.fragment.varzeas.hortos.estufa_therapeutic"
                        if await s.scalar(
                            select(CodexEntry.id).where(
                                CodexEntry.character_id == c.id,
                                CodexEntry.entry_id
                                == "codex.history.projeto_hemaris_registro_inicial",
                            )
                        )
                        else "codex.fragment.varzeas.hortos.estufa_technical"
                    ),
                    "explore.varzeas.hortos.canteiro_dupla_funcao": "codex.fragment.varzeas.hortos.canteiro_dupla_funcao",
                }.get(attempt.result_id)
                if attempt.result_id == "explore.varzeas.hortos.braseiro_horto_seco":
                    await self._ensure(s, Brazier, character_id=c.id, brazier_id=VARZEAS_HORTOS_BRAZIER)
                if fragment_id is not None:
                    await self._ensure(
                        s,
                        CodexFragment,
                        character_id=c.id,
                        entry_id=entry_id,
                        fragment_id=fragment_id,
                    )
            elif attempt.local_id == VARZEAS_GALERIAS_LOCATION:
                entry_id = "codex.location.galerias_transferencia"
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                if attempt.result_id == "explore.varzeas.galerias.braseiro_valvulas":
                    await self._ensure(s, Brazier, character_id=c.id, brazier_id=VARZEAS_GALERIAS_BRAZIER)
                    fragment_id = "codex.fragment.varzeas.galerias.braseiro_valvulas"
                elif attempt.result_id == "explore.varzeas.galerias.entrada_cisterna_transferencia":
                    await self._ensure(
                        s,
                        Unlock,
                        character_id=c.id,
                        unlock_id="dungeon.varzeas.cisterna_transferencia.discovered",
                    )
                    await self._ensure(
                        s,
                        CodexEntry,
                        character_id=c.id,
                        entry_id="codex.location.cisterna_transferencia",
                    )
                    fragment_id = "codex.fragment.varzeas.galerias.entrada_cisterna"
                elif attempt.result_id == "explore.varzeas.galerias.linha_retorno":
                    fragment_id = "codex.fragment.varzeas.galerias.linha_retorno"
                else:
                    fragment_id = None
                if fragment_id is not None:
                    await self._ensure(
                        s,
                        CodexFragment,
                        character_id=c.id,
                        entry_id=(
                            "codex.location.cisterna_transferencia"
                            if attempt.result_id == "explore.varzeas.galerias.entrada_cisterna_transferencia"
                            else entry_id
                        ),
                        fragment_id=fragment_id,
                    )

        for kind, item_id, quantity, payload in components:
            s.add(RewardComponent(reward_event_id=event.id, kind=kind, item_id=item_id, quantity=quantity, payload=payload))
        attempt.progress = {**(attempt.progress or {}), "receipt_text": "\n\n".join(lines), "settled": True}
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)
        from asterion.application.varzeas_feats import reconcile_varzeas_feats

        await reconcile_varzeas_feats(s, c)

    async def _settle_altos_exploration(self, s, c, attempt, base_text: str) -> None:
        """Settle Escarpa exploration with the global economy and published outcomes."""
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Altos exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * context.enemy_level) * Decimal("0.15"))
                        / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
            bestiary = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(
                    f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}"
                )
            should_consolidate = True
        elif attempt.category == "resource":
            material_id = ALTOS_EXPLORATION_RESOURCE_MATERIALS.get(attempt.result_id)
            if material_id is None:
                raise RuntimeError(f"unknown Altos exploration resource {attempt.result_id!r}")
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.extend(
                    (
                        ("crowns", None, award, {}),
                        ("material", material_id, 1, {"material_id": material_id}),
                    )
                )
                lines.extend(
                    (f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material_id]} · 1")
                )
                await self._deliver_material(
                    s, c, material_id, 1, f"explore:{attempt.id}:resource"
                )
        else:
            xp = ALTOS_EXPLORATION_UNIQUE_XP.get(attempt.result_id, 0)
            if xp:
                c.xp += xp
                components.append(("xp", None, xp, {}))
                lines.append(f"✨ XP · {xp}")
                should_consolidate = True
            if attempt.result_id == "explore.altos.escarpa.caderno_resgate_rasgado":
                entry_id = "codex.altos.infraestrutura_sustentacao"
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=attempt.result_id,
                )
                components.append(
                    ("codex", entry_id, 1, {"fragment_id": attempt.result_id})
                )
                lines.append("📖 Códice · Caderno de Resgate Rasgado")
            elif attempt.result_id == "explore.altos.pontes.braseiro_ponte_alta":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=ALTOS_PONTES_BRAZIER,
                )
                components.append(("brazier", ALTOS_PONTES_BRAZIER, 1, {}))
                lines.append("🔥 Braseiro da Ponte Alta descoberto")
            elif attempt.result_id == "explore.altos.pontes.livro_prioridades":
                entry_id = "codex.altos.prioridades_carga"
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=attempt.result_id,
                )
                components.append(
                    ("codex", entry_id, 1, {"fragment_id": attempt.result_id})
                )
                lines.append("📖 Códice · Livro de Prioridades de Travessia")
            elif attempt.result_id == "explore.altos.pedreiras.braseiro_pedreira_velha":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=ALTOS_PEDREIRA_BRAZIER,
                )
                components.append(("brazier", ALTOS_PEDREIRA_BRAZIER, 1, {}))
                lines.append("🔥 Braseiro da Pedreira Velha descoberto")
            elif attempt.result_id == "explore.altos.pedreiras.entrada_contrapeso":
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=ALTOS_PEDREIRAS_DUNGEON_UNLOCK,
                )
                await self._ensure(
                    s,
                    CodexEntry,
                    character_id=c.id,
                    entry_id="codex.altos.dungeon.pedreira_contrapeso",
                )
                components.append(
                    ("unlock", ALTOS_PEDREIRAS_DUNGEON_UNLOCK, 1, {})
                )
                lines.append("🗺️ Entrada da Pedreira do Contrapeso registrada")
            elif attempt.result_id == "explore.altos.pedreiras.mapa_extracao":
                entry_id = "codex.altos.prioridades_carga"
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=attempt.result_id,
                )
                components.append(
                    ("codex", entry_id, 1, {"fragment_id": attempt.result_id})
                )
                lines.append("📖 Códice · Mapa de Extração Recortado")
            elif attempt.result_id == "explore.altos.bastilha.braseiro_externo":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=ALTOS_BASTILHA_BRAZIER,
                )
                components.append(("brazier", ALTOS_BASTILHA_BRAZIER, 1, {}))
                lines.append("🔥 Braseiro da Bastilha Externa descoberto")
            elif attempt.result_id == "explore.altos.bastilha.entrada_profunda":
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=ALTOS_BASTILHA_DUNGEON_UNLOCK,
                )
                components.append(
                    ("unlock", ALTOS_BASTILHA_DUNGEON_UNLOCK, 1, {})
                )
                lines.append("🗺️ Entrada da Bastilha Profunda registrada")

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\\n\\n".join(lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)
        if attempt.result_id in ALTOS_EXPLORATION_UNIQUE_XP:
            await s.flush()
            completed_unique = await s.scalar(
                select(func.count(func.distinct(ExplorationAttempt.result_id))).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.status == "completed",
                    ExplorationAttempt.result_id.in_(ALTOS_EXPLORATION_UNIQUE_XP),
                )
            )
            if completed_unique == len(ALTOS_EXPLORATION_UNIQUE_XP):
                await self._ensure(
                    s,
                    Achievement,
                    character_id=c.id,
                    achievement_id=ALTOS_CARTOGRAPHER_ACHIEVEMENT,
                )

    async def _settle_confins_exploration(self, s, c, attempt, base_text: str) -> None:
        """Settle Marcha results with global Desbravar rules and Confins identities."""
        if (attempt.progress or {}).get("settled"):
            return
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Confins exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * context.enemy_level) * Decimal("0.15"))
                        / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
                units = 1 + (
                    1
                    if _draw_int(
                        attempt.seed, "exploration-material-extra", 100
                    ) < 20
                    else 0
                )
                for ordinal in range(units):
                    material = material_for(
                        context.creature_id,
                        f"{attempt.seed}:exploration-material:{ordinal}",
                    )
                    components.append(
                        ("material", material, 1, {"material_id": material})
                    )
                    lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                    await self._deliver_material(
                        s, c, material, 1, f"explore:{attempt.id}:material:{ordinal}"
                    )
            bestiary = await self._bestiary(
                s, c.id, context.creature_id, victory=True, observation_category=context.category
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(
                    f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}"
                )
            should_consolidate = True
        elif attempt.category == "resource":
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    (
                        (Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10
                    ).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
                    * 10
                )
                resource_pool = (
                    CONFINS_NO_EXPLORATION_RESOURCE_POOL
                    if attempt.local_id == CONFINS_NO_CENTRAL_LOCATION
                    else CONFINS_FRATURAS_EXPLORATION_RESOURCE_POOL
                    if attempt.local_id == CONFINS_FRATURAS_LIMIAR_LOCATION
                    else CONFINS_ESTRADAS_EXPLORATION_RESOURCE_POOL
                    if attempt.local_id == CONFINS_ESTRADAS_AUSENTES_LOCATION
                    else CONFINS_EXPLORATION_RESOURCE_POOL
                )
                material = weighted_choice(
                    f"{attempt.seed}:exploration-resource:0", resource_pool
                )
                c.crowns += award
                components.extend(
                    (
                        ("crowns", None, award, {}),
                        ("material", material, 1, {"material_id": material}),
                    )
                )
                lines.extend(
                    (f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material]} · 1")
                )
                await self._deliver_material(
                    s, c, material, 1, f"explore:{attempt.id}:resource"
                )
        else:
            xp = CONFINS_EXPLORATION_UNIQUE_XP.get(attempt.result_id, 0)
            if xp:
                c.xp += xp
                components.append(("xp", None, xp, {}))
                lines.append(f"✨ XP · {xp}")
                should_consolidate = True
            if attempt.result_id == "explore.confins.marcha.duas_balizas":
                entry_id = "codex.confins.marcos_incompativeis"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Marcos Incompatíveis")
            elif attempt.result_id == "explore.confins.marcha.caderno_marcha":
                entry_id = "codex.confins.duas_leituras_rota"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Caderno de Ida e Volta")
            elif attempt.result_id == "explore.confins.estradas.braseiro_conferida":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=CONFINS_ESTRADA_CONFERIDA_BRAZIER,
                )
                components.append(
                    ("brazier", CONFINS_ESTRADA_CONFERIDA_BRAZIER, 1, {})
                )
                lines.append("🔥 Braseiro da Estrada Conferida · Descoberto")
            elif attempt.result_id == "explore.confins.estradas.arquivo_retorno":
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=CONFINS_ARQUIVO_RETORNO_DUNGEON_UNLOCK,
                )
                components.append(
                    ("unlock", CONFINS_ARQUIVO_RETORNO_DUNGEON_UNLOCK, 1, {})
                )
                lines.append("🧭 Entrada do Arquivo do Retorno · Descoberta")
            elif attempt.result_id == "explore.confins.estradas.memoria_fundacao":
                entry_id = "codex.confins.casa_presente_ausente"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Memória de Fundação")
            elif attempt.result_id == "explore.confins.fraturas.braseiro_limiar":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=CONFINS_LIMIAR_FIRME_BRAZIER,
                )
                components.append(("brazier", CONFINS_LIMIAR_FIRME_BRAZIER, 1, {}))
                lines.append("🔥 Braseiro do Limiar Firme · Descoberto")
            elif attempt.result_id == "explore.confins.fraturas.corte_referencia":
                entry_id = "codex.confins.fratura_definicao"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Evidência observada da Fratura")
            elif attempt.result_id == "explore.confins.fraturas.ficha_dupla":
                entry_id = "codex.confins.avesso_estados"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Ficha de Duas Posições")
            elif attempt.result_id == "explore.confins.no.braseiro_retorno":
                await self._ensure(
                    s,
                    Brazier,
                    character_id=c.id,
                    brazier_id=CONFINS_NO_RETORNO_BRAZIER,
                )
                components.append(("brazier", CONFINS_NO_RETORNO_BRAZIER, 1, {}))
                lines.append("🔥 Braseiro do Nó de Retorno · Descoberto")
            elif attempt.result_id == "explore.confins.no.camara_contradicoes":
                await self._ensure(
                    s,
                    Unlock,
                    character_id=c.id,
                    unlock_id=CONFINS_CAMARA_CONTRADICOES_DUNGEON_UNLOCK,
                )
                components.append(
                    ("unlock", CONFINS_CAMARA_CONTRADICOES_DUNGEON_UNLOCK, 1, {})
                )
                lines.append("🧭 Entrada da Câmara das Contradições · Descoberta")
            elif attempt.result_id == "explore.confins.no.rede_incompleta":
                entry_id = "codex.confins.ancora_central_coordenacao"
                fragment_id = attempt.result_id
                await self._ensure(s, CodexEntry, character_id=c.id, entry_id=entry_id)
                await self._ensure(
                    s,
                    CodexFragment,
                    character_id=c.id,
                    entry_id=entry_id,
                    fragment_id=fragment_id,
                )
                components.append(("codex", entry_id, 1, {"fragment_id": fragment_id}))
                lines.append("📖 Códice · Diagrama da Rede Incompleta")

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)
        if attempt.result_id in CONFINS_CARTOGRAPHER_UNIQUE_IDS:
            await s.flush()
            completed_unique = await s.scalar(
                select(func.count(func.distinct(ExplorationAttempt.result_id))).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.status == "completed",
                    ExplorationAttempt.result_id.in_(CONFINS_CARTOGRAPHER_UNIQUE_IDS),
                )
            )
            if completed_unique == len(CONFINS_CARTOGRAPHER_UNIQUE_IDS):
                await self._ensure(
                    s,
                    Achievement,
                    character_id=c.id,
                    achievement_id=CONFINS_CARTOGRAPHER_ACHIEVEMENT,
                )

    async def _settle_charneca_exploration(self, s, c, attempt, base_text: str):
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        receipt_lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Charneca exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            receipt_lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                units = 1 + int(_draw_int(attempt.seed, "exploration-material-extra", 100) < 20)
                for ordinal in range(units):
                    material = material_for(
                        context.creature_id,
                        f"{attempt.seed}:exploration-material:{ordinal}",
                    )
                    components.append(("material", material, 1, {"material_id": material}))
                    receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                    await self._deliver_material(
                        s,
                        c,
                        material,
                        1,
                        f"explore:{attempt.id}:material:{ordinal}",
                    )
            bestiary_update = await self._bestiary(s, c.id, context.creature_id, victory=True)
            if bestiary_update is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary_update))
                receipt_lines.append(
                    f"📖 Bestiário · {bestiary_update['creature_name']} · "
                    f"{bestiary_update['stage_label']}"
                )
            should_consolidate = True

        elif attempt.category == "resource":
            if c.vigor >= 4:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                material_id = {
                    "explore.tdo.charneca.erva": "material.tdo.erva_cinzenta",
                    "explore.tdo.charneca.residuo": "material.tdo.residuo_ocaso",
                    "explore.tdo.charneca.couro": "material.tdo.couro_escoriado",
                }.get(attempt.result_id)
                if material_id is None:
                    raise RuntimeError(f"unknown Charneca resource result {attempt.result_id!r}")
                components.append(("material", material_id, 1, {"material_id": material_id}))
                receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material_id, material_id)} · 1")
                await self._deliver_material(s, c, material_id, 1, f"explore:{attempt.id}:resource")

        elif attempt.result_id == "explore.tdo.charneca.braseiro":
            xp = _fixed_percent_xp(4, "0.08")
            c.xp += xp
            await self._ensure(
                s,
                Brazier,
                character_id=c.id,
                brazier_id=CHARNECA_BRAZIER,
            )
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.08"}),
                    ("brazier", CHARNECA_BRAZIER, 1, {}),
                )
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.cripta":
            xp = _fixed_percent_xp(4, "0.08")
            c.xp += xp
            for unlock_id in (CHARNECA_DUNGEON_UNLOCK, CHARNECA_KNOWN_PATH_UNLOCK):
                await self._ensure(s, Unlock, character_id=c.id, unlock_id=unlock_id)
                components.append(("unlock", unlock_id, 1, {}))
            components.append(("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.08"}))
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.pedra_marcada":
            xp = _fixed_percent_xp(4, "0.025")
            c.xp += xp
            await self._ensure(
                s,
                CodexEntry,
                character_id=c.id,
                entry_id=CHARNECA_MARKS_CODEX_ENTRY,
            )
            components.append(("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.025"}))
            components.append(("codex", CHARNECA_MARKS_CODEX_ENTRY, 1, {}))
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.charneca.vestigios_fuligem":
            creatures = ("aranha_cinza", "cervo_escoriado", "peregrino_calcinado")
            identifiable = []
            without_habitat = []
            habitat_id = f"habitat:{CHARNECA_LOCATION}"
            for creature_id in creatures:
                profile = creature_for(creature_id)
                entry = await s.scalar(
                    select(BestiaryEntry).where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == creature_id,
                    )
                )
                if entry is None or c.level < profile.unlock_level:
                    continue
                identifiable.append(creature_id)
                habitat = await s.scalar(
                    select(BestiaryEvidence).where(
                        BestiaryEvidence.character_id == c.id,
                        BestiaryEvidence.creature_id == creature_id,
                        BestiaryEvidence.evidence_id == habitat_id,
                    )
                )
                if habitat is None:
                    without_habitat.append(creature_id)
            eligible = without_habitat or identifiable
            if eligible:
                creature_id = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(
                    select(BestiaryEntry)
                    .where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == creature_id,
                    )
                    .with_for_update()
                )
                if entry is not None and creature_id in without_habitat:
                    added = await self._add_bestiary_evidence(
                        s,
                        entry,
                        c.id,
                        creature_id,
                        habitat_id,
                        "habitat",
                        3,
                    )
                    if added:
                        components.append(("bestiary_habitat", creature_id, 3, {}))

        elif (
            attempt.category == "narrative"
            and attempt.result_id == "explore.tdo.charneca.vento_morto"
        ):
            xp = _fixed_percent_xp(4, "0.025")
            c.xp += xp
            components.append(("xp", None, xp, {"reference_level": 4, "fixed_percent": "0.025"}))
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(receipt_lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)

    async def _settle_bosque_exploration(self, s, c, attempt, base_text: str):
        source_id = f"explore:{attempt.id}"
        existing = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if existing is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        receipt_lines = [base_text]
        should_consolidate = False

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Bosque exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            receipt_lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                units = 1 + int(_draw_int(attempt.seed, "exploration-material-extra", 100) < 20)
                for ordinal in range(units):
                    material = material_for(
                        context.creature_id,
                        f"{attempt.seed}:exploration-material:{ordinal}",
                    )
                    components.append(("material", material, 1, {"material_id": material}))
                    receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material, material)} · 1")
                    await self._deliver_material(
                        s, c, material, 1, f"explore:{attempt.id}:material:{ordinal}"
                    )
            bestiary_update = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary_update is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary_update))
                receipt_lines.append(
                    f"📖 Bestiário · {bestiary_update['creature_name']} · "
                    f"{bestiary_update['stage_label']}"
                )
            should_consolidate = True

        elif attempt.category == "resource":
            if c.vigor >= 4:
                c.vigor -= 4
                crowns_award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += crowns_award
                components.append(("crowns", None, crowns_award, {}))
                receipt_lines.append(f"🪙 Coroas · {crowns_award}")
                resource_materials = {
                    "explore.tdo.bosque.couro": "material.tdo.couro_escoriado",
                    "explore.tdo.bosque.erva": "material.tdo.erva_cinzenta",
                    "explore.tdo.bosque.residuo": "material.tdo.residuo_ocaso",
                }
                material_id = resource_materials.get(attempt.result_id)
                if material_id is None:
                    raise RuntimeError(f"unknown Bosque resource result {attempt.result_id!r}")
                components.append(("material", material_id, 1, {"material_id": material_id}))
                receipt_lines.append(f"📦 {MATERIAL_LABELS.get(material_id, material_id)} · 1")
                await self._deliver_material(s, c, material_id, 1, f"explore:{attempt.id}:resource")

        elif attempt.result_id == "explore.tdo.bosque.braseiro":
            xp = _fixed_percent_xp(6, "0.08")
            c.xp += xp
            await self._ensure(s, Brazier, character_id=c.id, brazier_id=BOSQUE_BRAZIER)
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 6, "fixed_percent": "0.08"}),
                    ("brazier", BOSQUE_BRAZIER, 1, {}),
                )
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.bosque.estrutura_enterrada":
            xp = _fixed_percent_xp(6, "0.08")
            c.xp += xp
            codex_id = "codex.history.antigos_asterianos"
            await self._ensure(s, CodexEntry, character_id=c.id, entry_id=codex_id)
            await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id=codex_id,
                fragment_id="codex.fragment.bosque.estrutura_enterrada",
            )
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 6, "fixed_percent": "0.08"}),
                    ("codex", codex_id, 1, {}),
                )
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.bosque.caminho_ocidental":
            xp = _fixed_percent_xp(6, "0.025")
            c.xp += xp
            unlock_id = "known_path.tdo.caminho_ocidental"
            await self._ensure(s, Unlock, character_id=c.id, unlock_id=unlock_id)
            codex_id = "codex.history.antigos_asterianos"
            await self._ensure(s, CodexEntry, character_id=c.id, entry_id=codex_id)
            await self._ensure(
                s,
                CodexFragment,
                character_id=c.id,
                entry_id=codex_id,
                fragment_id="codex.fragment.bosque.caminho_ocidental",
            )
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 6, "fixed_percent": "0.025"}),
                    ("unlock", unlock_id, 1, {}),
                    ("codex", codex_id, 1, {}),
                )
            )
            receipt_lines.append(f"✨ XP · {xp}")
            should_consolidate = True

        elif attempt.result_id == "explore.tdo.bosque.rastros_galhos":
            creatures = (
                "cervo_escoriado",
                "carnical_fuligem",
                "aranha_cinza",
                "mariposa_brasa",
            )
            identifiable = []
            without_habitat = []
            habitat_id = f"habitat:{BOSQUE_LOCATION}"
            for creature_id in creatures:
                creature = creature_for(creature_id)
                entry = await s.scalar(
                    select(BestiaryEntry).where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == creature_id,
                    )
                )
                if entry is None or c.level < creature.unlock_level:
                    continue
                identifiable.append(creature_id)
                habitat = await s.scalar(
                    select(BestiaryEvidence).where(
                        BestiaryEvidence.character_id == c.id,
                        BestiaryEvidence.creature_id == creature_id,
                        BestiaryEvidence.evidence_id == habitat_id,
                    )
                )
                if habitat is None:
                    without_habitat.append(creature_id)
            eligible = without_habitat or identifiable
            if eligible:
                chosen = eligible[_draw_int(attempt.seed, "habitat", len(eligible))]
                entry = await s.scalar(
                    select(BestiaryEntry)
                    .where(
                        BestiaryEntry.character_id == c.id,
                        BestiaryEntry.creature_id == chosen,
                    )
                    .with_for_update()
                )
                if entry is not None and chosen in without_habitat:
                    if await self._add_bestiary_evidence(
                        s, entry, c.id, chosen, habitat_id, "habitat", 3
                    ):
                        components.append(("bestiary_habitat", chosen, 3, {}))

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(receipt_lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if should_consolidate:
            await consolidate_character_level(s, c)

    async def _settle_ruins_exploration(self, s, c, attempt, base_text: str) -> None:
        if (attempt.progress or {}).get("settled"):
            return
        source_id = f"explore:{attempt.id}"
        event = await s.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == c.id,
                RewardEvent.source_id == source_id,
            )
            .with_for_update()
        )
        if event is not None:
            return
        event = RewardEvent(character_id=c.id, source_id=source_id)
        s.add(event)
        await s.flush()
        components: list[tuple[str, str | None, int, dict]] = []
        lines = [base_text]
        consolidate = False
        result_id = attempt.result_id

        if attempt.category == "combat" and attempt.activity_id is not None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == attempt.activity_id)
                .with_for_update()
            )
            if context is None:
                raise RuntimeError("Ruins exploration combat is missing HuntContext")
            enough = c.vigor >= 4
            xp = enemy_xp(
                context.enemy_level,
                context.category,
                Decimal(1) if enough else Decimal("0.25"),
                player_level=c.level,
                legacy_factor=legacy_xp_factor(c.legacy_level),
            )
            c.xp += xp
            components.append(("xp", None, xp, {}))
            lines.append(f"✨ XP · {xp}")
            if enough:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * context.enemy_level) * Decimal("0.15")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += award
                components.append(("crowns", None, award, {}))
                lines.append(f"🪙 Coroas · {award}")
                units = 1 + int(_draw_int(attempt.seed, "exploration-material-extra", 100) < 20)
                for ordinal in range(units):
                    material_id = material_for(
                        context.creature_id,
                        f"{attempt.seed}:exploration-material:{ordinal}",
                    )
                    components.append(("material", material_id, 1, {"material_id": material_id}))
                    lines.append(f"📦 {MATERIAL_LABELS.get(material_id, material_id)} · 1")
                    await self._deliver_material(
                        s, c, material_id, 1, f"explore:{attempt.id}:material:{ordinal}"
                    )
            bestiary = await self._bestiary(
                s,
                c.id,
                context.creature_id,
                victory=True,
                elite=context.category == "elite",
                observation_category=context.category,
            )
            if bestiary is not None:
                components.append(("bestiary", context.creature_id, 1, bestiary))
                lines.append(
                    f"📖 Bestiário · {bestiary['creature_name']} · {bestiary['stage_label']}"
                )
            consolidate = True
        elif attempt.category == "resource":
            materials = {
                "explore.tdo.ruinas.ferro": "material.tdo.ferro_de_fuligem",
                "explore.tdo.ruinas.residuo": "material.tdo.residuo_ocaso",
                "explore.tdo.ruinas.erva": "material.tdo.erva_cinzenta",
                "explore.tdo.ruinas.couro": "material.tdo.couro_escoriado",
            }
            material_id = materials.get(result_id)
            if material_id is None:
                raise RuntimeError(f"unknown Ruins resource result {result_id!r}")
            if c.vigor >= 4:
                c.vigor -= 4
                award = int(
                    ((Decimal(100 + 15 * c.level) * Decimal("0.10")) / 10).quantize(
                        Decimal(1), rounding=ROUND_HALF_EVEN
                    )
                    * 10
                )
                c.crowns += award
                components.extend(
                    (
                        ("crowns", None, award, {}),
                        ("material", material_id, 1, {"material_id": material_id}),
                    )
                )
                lines.extend((f"🪙 Coroas · {award}", f"📦 {MATERIAL_LABELS[material_id]} · 1"))
                await self._deliver_material(s, c, material_id, 1, f"explore:{attempt.id}:resource")
        elif result_id in {"explore.tdo.ruinas.braseiro", "explore.tdo.ruinas.galerias"}:
            xp = _fixed_percent_xp(9, "0.08")
            c.xp += xp
            components.append(("xp", None, xp, {"reference_level": 9, "fixed_percent": "0.08"}))
            if result_id == "explore.tdo.ruinas.braseiro":
                await self._ensure(s, Brazier, character_id=c.id, brazier_id=RUINS_BRAZIER)
                components.append(("brazier", RUINS_BRAZIER, 1, {}))
            else:
                for unlock_id in ("dungeon.tdo.galerias_vigia", "known_path.tdo.galerias_vigia"):
                    await self._ensure(s, Unlock, character_id=c.id, unlock_id=unlock_id)
                    components.append(("unlock", unlock_id, 1, {}))
            lines.append(f"✨ XP · {xp}")
            consolidate = True
        elif result_id in {
            "explore.tdo.ruinas.estruturas_guarda",
            "explore.tdo.ruinas.ocupacao_posterior",
        }:
            xp = _fixed_percent_xp(9, "0.025")
            c.xp += xp
            codex_id = "codex.history.antigos_asterianos"
            fragment_id = (
                "codex.fragment.ruinas.estruturas_guarda"
                if result_id.endswith("estruturas_guarda")
                else "codex.fragment.ruinas.ocupacao_posterior"
            )
            await self._ensure(s, CodexEntry, character_id=c.id, entry_id=codex_id)
            await self._ensure(
                s, CodexFragment, character_id=c.id, entry_id=codex_id, fragment_id=fragment_id
            )
            components.extend(
                (
                    ("xp", None, xp, {"reference_level": 9, "fixed_percent": "0.025"}),
                    ("codex", codex_id, 1, {}),
                )
            )
            lines.append(f"✨ XP · {xp}")
            consolidate = True

        for kind, item_id, quantity, payload in components:
            s.add(
                RewardComponent(
                    reward_event_id=event.id,
                    kind=kind,
                    item_id=item_id,
                    quantity=quantity,
                    payload=payload,
                )
            )
        attempt.progress = {
            **(attempt.progress or {}),
            "receipt_text": "\n\n".join(lines),
            "settled": True,
        }
        attempt.completed_at = attempt.completed_at or datetime.now(UTC)
        if consolidate:
            await consolidate_character_level(s, c)

    async def _bestiary(
        self,
        s,
        character_id,
        creature_id,
        *,
        victory=False,
        evidence_id=None,
        evidence_category=None,
        evidence_points=0,
        variant=None,
        elite=False,
        grant_observation_xp=False,
        observation_level=None,
        observation_category="common",
    ):
        return await self.bestiary.record(
            s,
            character_id,
            creature_id,
            victory=victory,
            evidence_id=evidence_id,
            evidence_category=evidence_category,
            evidence_points=evidence_points,
            variant=variant,
            elite=elite,
            grant_observation_xp=grant_observation_xp,
            observation_level=observation_level,
            observation_category=observation_category,
        )

    async def _record_bestiary_combat_events(self, s, character_id, context, combat):
        return await self.bestiary.record_combat_events(
            s, character_id, context.creature_id, context.variant, combat
        )

    async def _add_bestiary_evidence(
        self, s, entry, character_id, creature_id, evidence_id, category, points=0
    ):
        return await self.bestiary.add_evidence(
            s, entry, character_id, creature_id, evidence_id, category, points
        )

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

    async def _p2_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P2_QUEST_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _p3_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P3_QUEST_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _p4_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P4_QUEST_ID,
                    Quest.status == "completed",
                )
            )
        )

    async def _p7_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P7",
                    Quest.status == "completed",
                )
            )
        )

    async def _p8_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P8",
                    Quest.status == "completed",
                )
            )
        )

    async def _p8_started_or_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P8",
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _p9_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P9",
                    Quest.status == "completed",
                )
            )
        )

    async def _p9_started_or_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P9",
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _p10_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P10",
                    Quest.status == "completed",
                )
            )
        )

    async def _p10_started_or_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P10",
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _p12_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P12",
                    Quest.status == "completed",
                )
            )
        )

    async def _nareth_region_open(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == NARETH_REGION_UNLOCK,
                )
            )
        )

    async def _nareth_p13_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P13",
                    Quest.status == "completed",
                )
            )
        )

    async def _nareth_p13_started_or_completed(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == "P13",
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    async def _nareth_p13_route_open(self, s, character_id) -> bool:
        return bool(
            await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == NARETH_CAMPINAS_POSTO_ROUTE,
                )
            )
        )

    async def _nareth_mission_completed(self, s, character_id, quest_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == quest_id,
                    Quest.status == "completed",
                )
            )
        )

    async def _nareth_mission_started_or_completed(self, s, character_id, quest_id) -> bool:
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == quest_id,
                    Quest.status.in_(("active", "completed")),
                )
            )
        )

    @staticmethod
    def _travel_region(location: str) -> str:
        if location in CONFINS_LOCATIONS or location == CONFINS_CAMARA_REGENCIA_LABEL:
            return "confins"
        if location in ALTOS_LOCATIONS:
            return "altos"
        if location in VARZEAS_LOCATIONS:
            return "varzeas"
        if location in VDE_LOCATIONS:
            return "vde"
        if location in NARETH_LOCATIONS:
            return "nareth"
        return "tdo"

    async def _ruins_route_level_gate(self, s, character) -> bool:
        if character.level >= 8:
            return True
        if character.level < 7:
            return False
        return bool(
            await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == S4_QUEST_ID,
                    Quest.status == "active",
                )
            )
        )

    async def _has_location(self, s, character_id, location_id) -> bool:
        return bool(
            await s.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == location_id,
                )
            )
        )

    async def latest_explorable_local(self, s, c, region: str) -> str | None:
        """The most advanced Local of ``region`` where Desbravar is released (Crônica)."""
        for local_id in reversed(REGIONS_BY_NAME[region].locals):
            world = SimpleNamespace(
                region=region, location=hunt_profile_for_local_id(local_id).label
            )
            if await self._available_local_profile(s, c, world, "explore") is not None:
                return local_id
        return None

    async def _available_local_profile(self, s, c, world, activity_kind: str):
        profile = hunt_profile_for_location(world.location) if world is not None else None
        if profile is None:
            return None
        if profile.local_id == ROAD_LOCATION:
            if not await self._p1_completed(s, c.id):
                return None
        elif profile.local_id == CHARNECA_LOCATION and not await self._p2_completed(s, c.id):
            return None
        elif profile.local_id == BOSQUE_LOCATION and not await self._p3_completed(s, c.id):
            return None
        elif profile.local_id == RUINS_LOCATION:
            if c.level < 8 or not await self._p4_completed(s, c.id):
                return None
            if not await self._has_location(s, c.id, RUINS_LOCATION):
                return None
        elif profile.local_id == VDE_GARGANTA_LOCATION:
            if not await self._p7_completed(s, c.id):
                return None
        elif profile.local_id == VDE_MATA_LOCATION:
            if c.level < 13:
                return None
            if activity_kind == "hunt" and not await self._p8_completed(s, c.id):
                return None
            if activity_kind == "explore" and not await self._p8_started_or_completed(s, c.id):
                return None
        elif profile.local_id == VDE_BAIXIOS_LOCATION:
            if c.level < 15 or not await self._p9_started_or_completed(s, c.id):
                return None
            if activity_kind == "hunt" and not await self._p9_completed(s, c.id):
                return None
        elif profile.local_id == VDE_CLAUSTRO_LOCATION:
            if c.level < 18 or not await self._p10_started_or_completed(s, c.id):
                return None
            if activity_kind == "hunt" and not await self._p10_completed(s, c.id):
                return None
        elif profile.local_id == NARETH_CAMPINAS_LOCATION:
            if (
                c.level < 21
                or world.region != NARETH_REGION
                or not await self._p12_completed(s, c.id)
                or not await self._nareth_region_open(s, c.id)
            ):
                return None
            if activity_kind == "hunt" and not await self._nareth_p13_completed(s, c.id):
                return None
        elif profile.local_id == NARETH_POSTO_LOCATION:
            return None
        elif profile.local_id == NARETH_CANAIS_LOCATION:
            if world.region != NARETH_REGION or not await self._nareth_mission_started_or_completed(s, c.id, "P14"):
                return None
            if activity_kind == "hunt" and not await self._nareth_mission_completed(s, c.id, "P14"):
                return None
        elif profile.local_id == NARETH_CAMPOS_LOCATION:
            if world.region != NARETH_REGION or not await self._nareth_mission_started_or_completed(s, c.id, "P15"):
                return None
            if activity_kind == "hunt" and not await self._nareth_mission_completed(s, c.id, "P15"):
                return None
        elif profile.local_id == NARETH_OBSERVATORIO_LOCATION:
            if world.region != NARETH_REGION or not await self._nareth_mission_started_or_completed(s, c.id, "P16"):
                return None
            if activity_kind == "hunt" and not await self._nareth_mission_completed(s, c.id, "P16"):
                return None
        elif profile.local_id == VARZEAS_DIQUES_LOCATION:
            if (
                world.region != VARZEAS_REGION
                or c.level < 31
                or not await self._nareth_mission_completed(s, c.id, "P19")
            ):
                return None
        elif profile.local_id == VARZEAS_BREJOS_LOCATION:
            if (
                world.region != VARZEAS_REGION
                or c.level < 33
                or not await self._nareth_mission_completed(s, c.id, "P20")
            ):
                return None
        elif profile.local_id == VARZEAS_HORTOS_LOCATION:
            if (
                world.region != VARZEAS_REGION
                or c.level < 35
                or not await self._nareth_mission_started_or_completed(s, c.id, "P21")
            ):
                return None
        elif profile.local_id == VARZEAS_GALERIAS_LOCATION:
            if (
                world.region != VARZEAS_REGION
                or c.level < 37
                or not await self._nareth_mission_started_or_completed(s, c.id, "P22")
            ):
                return None
            if activity_kind == "hunt" and not await self._nareth_mission_completed(s, c.id, "P22"):
                return None
        elif profile.local_id == ALTOS_ESCARPA_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 41
                or not await self._nareth_mission_completed(s, c.id, "P25")
                or not await self._has_location(s, c.id, ALTOS_ESCARPA_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_PONTES_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 43
                or not await self._nareth_mission_completed(s, c.id, "P25")
                or not await self._nareth_mission_completed(s, c.id, "P26")
                or not await self._has_location(s, c.id, ALTOS_PONTES_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_PEDREIRAS_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 45
                or not await self._nareth_mission_completed(s, c.id, "P26")
                or not await self._nareth_mission_completed(s, c.id, "P27")
                or not await self._has_location(s, c.id, ALTOS_PEDREIRAS_LOCATION)
            ):
                return None
        elif profile.local_id == ALTOS_BASTILHA_LOCATION:
            if (
                world.region != ALTOS_REGION
                or c.level < 47
                or not await self._nareth_mission_completed(s, c.id, "P27")
                or not await self._nareth_mission_completed(s, c.id, "P28")
                or not await self._has_location(s, c.id, ALTOS_BASTILHA_LOCATION)
            ):
                return None
        elif profile.local_id == CONFINS_MARCHA_LOCATION:
            if (
                world.region != CONFINS_REGION
                or c.level < 51
                or not await self._nareth_mission_completed(s, c.id, "P30")
                or not await self._nareth_mission_completed(s, c.id, "P31")
                or not await self._has_location(s, c.id, CONFINS_MARCHA_LOCATION)
            ):
                return None
        elif profile.local_id == CONFINS_ESTRADAS_AUSENTES_LOCATION:
            if (
                world.region != CONFINS_REGION
                or c.level < 53
                or not await self._nareth_mission_completed(s, c.id, "P31")
                or not await self._nareth_mission_completed(s, c.id, "P32")
                or not await self._has_location(s, c.id, CONFINS_ESTRADAS_AUSENTES_LOCATION)
            ):
                return None
        elif profile.local_id == CONFINS_FRATURAS_LIMIAR_LOCATION:
            if (
                world.region != CONFINS_REGION
                or c.level < 55
                or not await self._nareth_mission_completed(s, c.id, "P32")
                or not await self._nareth_mission_completed(s, c.id, "P33")
                or not await self._has_location(s, c.id, CONFINS_FRATURAS_LIMIAR_LOCATION)
            ):
                return None
        elif profile.local_id == CONFINS_NO_CENTRAL_LOCATION:
            if (
                world.region != CONFINS_REGION
                or c.level < 57
                or not await self._nareth_mission_completed(s, c.id, "P33")
                or not await self._nareth_mission_completed(s, c.id, "P34")
                or not await self._has_location(s, c.id, CONFINS_NO_CENTRAL_LOCATION)
            ):
                return None
        unlock_id = profile.hunt_unlock if activity_kind == "hunt" else profile.explore_unlock
        if not await s.scalar(
            select(Unlock).where(
                Unlock.character_id == c.id,
                Unlock.unlock_id == unlock_id,
            )
        ):
            return None
        if activity_kind == "hunt" and profile.local_id in {
            VDE_GARGANTA_LOCATION,
            VDE_MATA_LOCATION,
            VDE_BAIXIOS_LOCATION,
            VDE_CLAUSTRO_LOCATION,
            NARETH_CAMPINAS_LOCATION,
            NARETH_CANAIS_LOCATION,
            NARETH_CAMPOS_LOCATION,
            NARETH_OBSERVATORIO_LOCATION,
            VARZEAS_DIQUES_LOCATION,
            VARZEAS_BREJOS_LOCATION,
            VARZEAS_HORTOS_LOCATION,
            VARZEAS_GALERIAS_LOCATION,
            ALTOS_ESCARPA_LOCATION,
            ALTOS_PONTES_LOCATION,
            ALTOS_PEDREIRAS_LOCATION,
            ALTOS_BASTILHA_LOCATION,
            CONFINS_MARCHA_LOCATION,
            CONFINS_ESTRADAS_AUSENTES_LOCATION,
            CONFINS_FRATURAS_LIMIAR_LOCATION,
            CONFINS_NO_CENTRAL_LOCATION,
        } and any(
            creature_id not in MATERIAL_POOLS for creature_id, _ in profile.creature_weights
        ):
            # Fail closed if any regional Hunt/Round creature lacks its
            # authoritative basic-material pool.
            return None
        return profile

    async def recover_normal_pve_defeat(self, s, c, local_id, world=None):
        """Apply the shared regional recovery rule to a normal PvE defeat."""
        return await self._recover_normal_pve_defeat(s, c, local_id, world)

    async def _recover_normal_pve_defeat(self, s, c, local_id, world=None):
        """Apply the regional destination rule for normal open-world PvE defeats."""
        c.hp = c.max_hp
        if local_id not in {CHARNECA_LOCATION, BOSQUE_LOCATION, RUINS_LOCATION}:
            return None, None
        if world is None:
            world = await s.scalar(
                select(WorldState).where(WorldState.character_id == c.id).with_for_update()
            )
        if local_id == RUINS_LOCATION:
            poente = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == RUINS_BRAZIER,
                )
            )
            galhos = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == BOSQUE_BRAZIER,
                )
            )
            vento = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == CHARNECA_BRAZIER,
                )
            )
            brazier_id = (
                RUINS_BRAZIER
                if poente is not None
                else BOSQUE_BRAZIER
                if galhos is not None
                else CHARNECA_BRAZIER
                if vento is not None
                else BRAZIER_FOR_LOCATION[REFUGE]
            )
            recovery_location = BRAZIER_DETAILS[brazier_id][0]
        elif local_id == BOSQUE_LOCATION:
            galhos = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == BOSQUE_BRAZIER,
                )
            )
            vento = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == CHARNECA_BRAZIER,
                )
            )
            brazier_id = (
                BOSQUE_BRAZIER
                if galhos is not None
                else CHARNECA_BRAZIER
                if vento is not None
                else BRAZIER_FOR_LOCATION[REFUGE]
            )
            recovery_location = BRAZIER_DETAILS[brazier_id][0]
        else:
            vento = await s.scalar(
                select(Brazier).where(
                    Brazier.character_id == c.id,
                    Brazier.brazier_id == CHARNECA_BRAZIER,
                )
            )
            brazier_id = CHARNECA_BRAZIER if vento is not None else BRAZIER_FOR_LOCATION[REFUGE]
            recovery_location = BRAZIER_DETAILS[brazier_id][0]
        if world is not None:
            world.region = REGION
            world.location = recovery_location
        return BRAZIER_DETAILS[brazier_id][1], recovery_location

    async def _settle_road_defeat(
        self, s, c, activity, combat, world, *, context=None, record=None
    ):
        """Settle a terminal manual-Hunt or combat-Exploration defeat once.

        Road combat can already be terminal when it is created: the shared combat
        engine resolves opening enemy actions before returning the initial state.
        Route that case through the same failure receipt and regional recovery used
        after a player action so it cannot remain an active foreground forever.
        """
        if activity.status != "active":
            return await self._result_view_for_activity(s, c, activity, world)
        if record is not None:
            record.snapshot = encode(combat)
        activity.status = "failed"
        activity.state_version = combat.version
        activity.last_valid_action_at = datetime.now(UTC)
        c.hp = combat.fighters["player"].hp
        if context is None:
            context = await s.scalar(
                select(HuntContext)
                .where(HuntContext.game_activity_id == activity.id)
                .with_for_update()
            )
        if context is not None:
            await self._record_bestiary_combat_events(s, c.id, context, combat)
        recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
            s,
            c,
            context.local_id if context is not None else None,
            world,
        )
        if context is not None and context.pvpve_collision_id is not None:
            await self.pvpve.finish_prey_member(
                s, context.pvpve_collision_id, c.id, victory=False
            )
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
                    "receipt_text": "A exploração foi interrompida.",
                    **(
                        {
                            "recovery_brazier": recovery_brazier,
                            "recovery_location": recovery_location,
                        }
                        if recovery_brazier is not None
                        else {}
                    ),
                    "settled": True,
                }
                await consolidate_character_level(s, c)
                return await self._attempt_view(s, c, attempt)
        await consolidate_character_level(s, c)
        return await self._hunt_defeat_view(s, c, activity, context)

    async def _record_charneca_habitat(self, s, character_id, creature_id, profile):
        if profile.local_id not in {CHARNECA_LOCATION, BOSQUE_LOCATION, RUINS_LOCATION}:
            return False
        entry = await s.scalar(
            select(BestiaryEntry)
            .where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
            .with_for_update()
        )
        if entry is None:
            return False
        return await self._add_bestiary_evidence(
            s,
            entry,
            character_id,
            creature_id,
            f"habitat:{profile.local_id}",
            "habitat",
            3,
        )

    async def _road_blocking_view(self, s, c):
        """Return the authoritative Road foreground/result before new callbacks run."""
        active = await s.scalar(
            select(GameActivity)
            .where(GameActivity.character_id == c.id, GameActivity.status == "active")
            .with_for_update()
        )
        if active is not None:
            if active.content_id not in {
                HUNT_CONTENT,
                GROUP_HUNT_CONTENT,
                PVPVE_QUEUE_CONTENT,
                PVPVE_CONTENT,
                EXPLORE_CONTENT,
            }:
                return None
            if active.content_id == GROUP_HUNT_CONTENT:
                return await self.group_hunts.view_for_activity(s, c, active)
            if active.content_id in {PVPVE_QUEUE_CONTENT, PVPVE_CONTENT}:
                return await self.pvpve.view_for_activity(s, c, active)
            if self._expired(active):
                return await self._expire_activity(s, c, active)
            if active.content_id == HUNT_CONTENT:
                return await self._combat_view(s, c, active)
            attempt = await s.scalar(
                select(ExplorationAttempt).where(ExplorationAttempt.activity_id == active.id)
            )
            if attempt is None or attempt.status == "active":
                return await self._combat_view(s, c, active)
            return await self._attempt_view(s, c, attempt)

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
            return await self._attempt_view(s, c, attempt)

        pvpve_member = await s.scalar(
            select(PvpveCollisionMember)
            .join(PvpveCollision, PvpveCollision.id == PvpveCollisionMember.collision_id)
            .where(
                PvpveCollisionMember.character_id == c.id,
                PvpveCollisionMember.status == "defeated",
                PvpveCollisionMember.result_acknowledged.is_(False),
            )
            .order_by(PvpveCollision.created_at.desc(), PvpveCollision.id.desc())
            .limit(1)
            .with_for_update()
        )
        if pvpve_member is not None:
            activity = await s.get(GameActivity, pvpve_member.game_activity_id)
            if activity is not None:
                return await self.pvpve.view_for_activity(s, c, activity)

        context = await s.scalar(
            select(HuntContext)
            .join(GameActivity, HuntContext.game_activity_id == GameActivity.id)
            .where(
                HuntContext.character_id == c.id,
                GameActivity.content_id.in_((HUNT_CONTENT, GROUP_HUNT_CONTENT)),
                GameActivity.status.in_(("completed", "failed")),
                HuntContext.result_acknowledged.is_(False),
            )
            .order_by(GameActivity.last_valid_action_at.desc(), GameActivity.id.desc())
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
        if activity.content_id == GROUP_HUNT_CONTENT:
            return await self.group_hunts.view_for_activity(s, c, activity)
        if activity.status == "completed":
            return await self._hunt_victory_view(s, c, activity)
        return await self._hunt_defeat_view(s, c, activity, context)

    async def _hunt_defeat_view(self, s, c, activity, context=None):
        if context is None:
            context = await s.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == activity.id)
            )
        recovery_brazier = recovery_location = None
        if context is not None and context.local_id in {
            CHARNECA_LOCATION,
            BOSQUE_LOCATION,
            RUINS_LOCATION,
        }:
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            if world is not None and world.location in {REFUGE, CHARNECA, BOSQUE, RUINS}:
                recovery_location = world.location
                brazier_id = BRAZIER_FOR_LOCATION[world.location]
                recovery_brazier = BRAZIER_DETAILS[brazier_id][1]
        return RoadView(
            "hunt_defeat",
            c.id,
            _location_label(context.local_id if context is not None else None),
            activity_id=activity.id,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            recovery_brazier=recovery_brazier,
            recovery_location=recovery_location,
            route_available=(
                context is not None
                and (
                    (context.local_id == CHARNECA_LOCATION and recovery_location == REFUGE)
                    or (context.local_id == BOSQUE_LOCATION and recovery_location == CHARNECA)
                    or (
                        context.local_id == RUINS_LOCATION
                        and recovery_location in {BOSQUE, CHARNECA, REFUGE}
                    )
                )
            ),
        )

    @staticmethod
    def _expired(activity) -> bool:
        return bool(
            activity.last_valid_action_at
            and datetime.now(UTC) - activity.last_valid_action_at > ROAD_ACTIVITY_GRACE
        )

    async def _expire_activity(self, s, c, activity):
        """Resolve an abandoned Road foreground exactly once."""
        if activity.content_id == GROUP_HUNT_CONTENT:
            return await self.group_hunts.expire_from_road(s, c, activity)
        if activity.status != "active":
            world = await s.scalar(select(WorldState).where(WorldState.character_id == c.id))
            return await self._result_view_for_activity(s, c, activity, world)
        activity.status = "failed"
        activity.last_valid_action_at = datetime.now(UTC)
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        if context is not None and context.pvpve_collision_id is not None:
            await self.pvpve.finish_prey_member(
                s, context.pvpve_collision_id, c.id, victory=False
            )
        recovery_brazier, recovery_location = await self._recover_normal_pve_defeat(
            s,
            c,
            context.local_id if context is not None else None,
        )
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
                    "receipt_text": "A exploração expirou por inatividade.",
                    **(
                        {
                            "recovery_brazier": recovery_brazier,
                            "recovery_location": recovery_location,
                        }
                        if recovery_brazier is not None
                        else {}
                    ),
                    "settled": True,
                }
                await consolidate_character_level(s, c)
                return await self._attempt_view(s, c, attempt)
        await consolidate_character_level(s, c)
        return await self._hunt_defeat_view(s, c, activity, context)

    async def _result_view_for_activity(self, s, c, activity, world):
        if activity.content_id == GROUP_HUNT_CONTENT:
            return await self.group_hunts.view_for_activity(s, c, activity)
        if activity.content_id == PVPVE_CONTENT:
            return await self.pvpve.view_for_activity(s, c, activity)
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
                    return await self._hunt_defeat_view(s, c, activity, context)
        elif activity.content_id == EXPLORE_CONTENT:
            attempt = await s.scalar(
                select(ExplorationAttempt).where(ExplorationAttempt.activity_id == activity.id)
            )
            if attempt is not None and not attempt.result_acknowledged:
                return await self._attempt_view(s, c, attempt)
        return await self._view_for_world(s, c, world) if world is not None else None

    async def _combat_view(self, s, c, activity):
        if activity.content_id == GROUP_HUNT_CONTENT:
            return await self.group_hunts.view_for_activity(s, c, activity)
        encounter, record = await CombatRepository(s).combat(activity)
        combat = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        budget_limit = (
            ENCOUNTER_CONSUMABLE_LIMITS.get(context.category, 0) if context is not None else 0
        )
        stock = (
            await s.scalars(
                select(ConsumableStack)
                .where(
                    ConsumableStack.character_id == c.id,
                    ConsumableStack.quantity > 0,
                )
                .order_by(ConsumableStack.consumable_id)
            )
        ).all()
        stock_ids = tuple(row.consumable_id for row in stock)
        consumable_options = combat_consumable_options(combat, stock_ids, budget_limit=budget_limit)
        return RoadView(
            "combat",
            c.id,
            _location_label(context.local_id if context is not None else None),
            activity.id,
            encounter.id,
            record.id,
            combat,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            consumable_options=consumable_options,
            consumable_quantities=tuple((row.consumable_id, row.quantity) for row in stock),
            consumable_budget_limit=budget_limit,
        )

    @staticmethod
    def _invalid_location_view(c, world) -> RoadView:
        """Render an unknown persisted location without inventing recovery state."""
        return RoadView(
            "invalid_location",
            c.id,
            world.location,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            hunt_enabled=False,
            explore_enabled=False,
            retry_available=False,
            explore_available=False,
            route_available=False,
            route_destinations=(),
            brazier_id=None,
            brazier_label=None,
            brazier_destinations=(),
        )

    async def _view_for_world(self, s, c, world):
        if world.location not in TRAVEL_LOCATIONS:
            return self._invalid_location_view(c, world)
        hunt_profile = hunt_profile_for_location(world.location)
        familiar = bool(
            hunt_profile
            and await s.scalar(
                select(Unlock).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == hunt_profile.round_familiarity,
                )
            )
        )
        explore_available = True
        if hunt_profile is not None:
            now = datetime.now(UTC)
            attempt_local_id = _exploration_local_id(hunt_profile)
            recent = (
                await s.scalar(
                    select(func.count(ExplorationAttempt.id)).where(
                        ExplorationAttempt.character_id == c.id,
                        ExplorationAttempt.local_id == attempt_local_id,
                        ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                    )
                )
                or 0
            )
            last = await s.scalar(
                select(ExplorationAttempt)
                .where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == attempt_local_id,
                )
                .order_by(ExplorationAttempt.created_at.desc())
                .limit(1)
            )
            explore_available = not (
                recent >= 6 or (last is not None and last.created_at > now - timedelta(minutes=5))
            )
        known_brazier_ids = set(
            (await s.scalars(select(Brazier.brazier_id).where(Brazier.character_id == c.id))).all()
        )
        p7_complete = await self._p7_completed(s, c.id)
        p8_complete = await self._p8_completed(s, c.id)
        p8_started_or_complete = await self._p8_started_or_completed(s, c.id)
        p9_complete = await self._p9_completed(s, c.id)
        p9_started_or_complete = await self._p9_started_or_completed(s, c.id)
        p10_complete = await self._p10_completed(s, c.id)
        p10_started_or_complete = await self._p10_started_or_completed(s, c.id)
        berco_access = bool(
            await self._has_location(s, c.id, VDE_BERCO_LOCATION)
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VDE_CLAUSTRO_BERCO_ROUTE,
                )
            )
            and await s.scalar(
                select(Quest.id).where(
                    Quest.character_id == c.id,
                    Quest.quest_id == "P11",
                    Quest.status == "completed",
                )
            )
        )
        p12_complete = await self._p12_completed(s, c.id)
        nareth_access = c.level >= 21 and p12_complete
        nareth_p13_complete = await self._nareth_p13_completed(s, c.id)
        nareth_p14_open = await self._nareth_mission_started_or_completed(s, c.id, "P14")
        nareth_p14_complete = await self._nareth_mission_completed(s, c.id, "P14")
        nareth_p15_open = await self._nareth_mission_started_or_completed(s, c.id, "P15")
        nareth_p15_complete = await self._nareth_mission_completed(s, c.id, "P15")
        nareth_p16_open = await self._nareth_mission_started_or_completed(s, c.id, "P16")
        nareth_p16_complete = await self._nareth_mission_completed(s, c.id, "P16")
        nareth_p17_open = await self._nareth_mission_started_or_completed(s, c.id, "P17")
        nareth_p18_complete = await self._nareth_mission_completed(s, c.id, "P18")
        varzeas_entry_open = bool(
            c.level >= 31
            and nareth_p18_complete
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_REGION_ENTRY_UNLOCK,
                )
            )
        )
        varzeas_p19_open = await self._nareth_mission_started_or_completed(s, c.id, "P19")
        varzeas_p19_complete = await self._nareth_mission_completed(s, c.id, "P19")
        varzeas_p20_open = await self._nareth_mission_started_or_completed(s, c.id, "P20")
        varzeas_p20_complete = await self._nareth_mission_completed(s, c.id, "P20")
        varzeas_p21_open = await self._nareth_mission_started_or_completed(s, c.id, "P21")
        varzeas_p22_open = await self._nareth_mission_started_or_completed(s, c.id, "P22")
        varzeas_p22_complete = await self._nareth_mission_completed(s, c.id, "P22")
        varzeas_matrix_access = bool(
            c.level >= 39
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_CAMARA_ACCESS_UNLOCK,
                )
            )
        )
        altos_entry_open = bool(
            c.level >= 41
            and await self._nareth_mission_completed(s, c.id, "P24")
        )
        altos_p25_complete = await self._nareth_mission_completed(s, c.id, "P25")
        altos_p26_complete = await self._nareth_mission_completed(s, c.id, "P26")
        altos_p27_complete = await self._nareth_mission_completed(s, c.id, "P27")
        altos_p28_complete = await self._nareth_mission_completed(s, c.id, "P28")
        altos_p29_complete = await self._nareth_mission_completed(s, c.id, "P29")
        confins_entry_open = bool(
            c.level >= 51
            and await self._nareth_mission_completed(s, c.id, "P30")
        )
        confins_p31_complete = await self._nareth_mission_completed(s, c.id, "P31")
        confins_p32_complete = await self._nareth_mission_completed(s, c.id, "P32")
        confins_p32_open = await self._nareth_mission_started_or_completed(s, c.id, "P32")
        confins_p33_complete = await self._nareth_mission_completed(s, c.id, "P33")
        confins_p33_open = await self._nareth_mission_started_or_completed(s, c.id, "P33")
        confins_p34_complete = await self._nareth_mission_completed(s, c.id, "P34")
        confins_p34_open = await self._nareth_mission_started_or_completed(s, c.id, "P34")
        confins_marcha_discovered = await self._has_location(
            s, c.id, CONFINS_MARCHA_LOCATION
        )
        confins_refuge_discovered = await self._has_location(
            s, c.id, CONFINS_ULTIMO_REFUGIO_LOCATION
        )
        confins_estradas_discovered = await self._has_location(
            s, c.id, CONFINS_ESTRADAS_AUSENTES_LOCATION
        )
        confins_fraturas_discovered = await self._has_location(
            s, c.id, CONFINS_FRATURAS_LIMIAR_LOCATION
        )
        confins_no_discovered = await self._has_location(
            s, c.id, CONFINS_NO_CENTRAL_LOCATION
        )
        confins_camara_access_open = bool(
            await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CONFINS_CAMARA_REGENCIA_ACCESS_UNLOCK,
                )
            )
        )
        confins_camara_discovered = await self._has_location(
            s, c.id, CONFINS_CAMARA_REGENCIA_LOCATION
        )
        confins_estradas_access_open = bool(
            c.level >= 53
            and confins_p31_complete
            and confins_p32_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CONFINS_ESTRADAS_ACCESS_UNLOCK,
                )
            )
        )
        confins_fraturas_access_open = bool(
            c.level >= 55
            and confins_p32_complete
            and confins_p33_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CONFINS_FRATURAS_ACCESS_UNLOCK,
                )
            )
        )
        confins_no_access_open = bool(
            c.level >= 57
            and confins_p33_complete
            and confins_p34_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CONFINS_NO_CENTRAL_ACCESS_UNLOCK,
                )
            )
        )
        altos_escarpa_discovered = await self._has_location(s, c.id, ALTOS_ESCARPA_LOCATION)
        altos_abrigo_discovered = await self._has_location(s, c.id, ALTOS_ABRIGO_LOCATION)
        altos_pontes_discovered = await self._has_location(s, c.id, ALTOS_PONTES_LOCATION)
        altos_pedreiras_discovered = await self._has_location(s, c.id, ALTOS_PEDREIRAS_LOCATION)
        altos_bastilha_discovered = await self._has_location(s, c.id, ALTOS_BASTILHA_LOCATION)
        altos_pontes_access_open = bool(
            c.level >= 43
            and altos_p25_complete
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == ALTOS_PONTES_ACCESS_UNLOCK,
                )
            )
        )
        altos_pedreiras_access_open = bool(
            c.level >= 45
            and altos_p26_complete
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == ALTOS_PEDREIRAS_ACCESS_UNLOCK,
                )
            )
        )
        altos_bastilha_access_open = bool(
            c.level >= 47
            and altos_p27_complete
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == ALTOS_BASTILHA_ACCESS_UNLOCK,
                )
            )
        )
        altos_coracao_access_open = bool(
            altos_p29_complete
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
                )
            )
        )
        varzeas_inner_route_open = bool(
            varzeas_p19_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_DIQUES_PORTO_ROUTE,
                )
            )
        )
        varzeas_brejos_route_open = bool(
            varzeas_p20_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_PORTO_BREJOS_ROUTE,
                )
            )
        )
        varzeas_hortos_route_open = bool(
            c.level >= 35
            and varzeas_p20_complete
            and varzeas_p21_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_BREJOS_HORTOS_ROUTE,
                )
            )
        )
        varzeas_galerias_route_open = bool(
            c.level >= 37
            and varzeas_p22_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_HORTOS_GALERIAS_ROUTE,
                )
            )
        )
        nareth_chamber_open = bool(
            nareth_p17_open
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == "region.nareth.camara_arconte.available",
                )
            )
        )
        if nareth_access:
            await self._ensure(s, Unlock, character_id=c.id, unlock_id=NARETH_REGION_UNLOCK)
        nareth_route_open = await self._nareth_p13_route_open(s, c.id)
        current_brazier = BRAZIER_FOR_LOCATION.get(world.location)
        brazier_id = current_brazier if current_brazier in known_brazier_ids else None
        brazier_label = BRAZIER_DETAILS[brazier_id][1] if brazier_id is not None else None
        brazier_destinations = tuple(
            (candidate_id, label, location)
            for candidate_id, (location, label) in BRAZIER_DETAILS.items()
            if candidate_id in known_brazier_ids and location != world.location
            and self._travel_region(location) == self._travel_region(world.location)
            and (location not in {VDE_GARGANTA, VDE_VIGILIA, VDE_MATA, VDE_BAIXIOS} or p7_complete)
            and (location != VDE_MATA or p8_started_or_complete)
            and (location != VDE_BAIXIOS or p9_started_or_complete)
            and (location != VDE_CLAUSTRO or p10_started_or_complete)
            and (location != NARETH_CANAIS or nareth_p14_open)
            and (location != NARETH_CAMPOS or nareth_p15_open)
            and (location != NARETH_OBSERVATORIO or nareth_p16_open)
            and (location != ALTOS_ESCARPA_LABEL or altos_entry_open)
            and (location != ALTOS_ABRIGO_LABEL or altos_abrigo_discovered)
            and (location != ALTOS_PONTES_LABEL or altos_pontes_discovered)
            and (location != ALTOS_PEDREIRAS_LABEL or altos_pedreiras_discovered)
            and (location != ALTOS_BASTILHA_LABEL or altos_bastilha_discovered)
            and (location != CONFINS_MARCHA_LABEL or confins_marcha_discovered)
            and (location != CONFINS_ULTIMO_REFUGIO_LABEL or confins_refuge_discovered)
            and (location != CONFINS_ESTRADAS_AUSENTES_LABEL or confins_estradas_discovered)
            and (location != CONFINS_FRATURAS_LIMIAR_LABEL or confins_fraturas_discovered)
            and (location != CONFINS_NO_CENTRAL_LABEL or confins_no_discovered)
        ) if world.location not in {VDE_BERCO, NARETH_CAMARA_LABEL} else ()
        active_p3 = await s.scalar(
            select(Quest.id).where(
                Quest.character_id == c.id,
                Quest.quest_id == P3_QUEST_ID,
                Quest.status == "active",
            )
        )
        active_p4 = await s.scalar(
            select(Quest.id).where(
                Quest.character_id == c.id,
                Quest.quest_id == P4_QUEST_ID,
                Quest.status == "active",
            )
        )
        active_s4 = await s.scalar(
            select(Quest.id).where(
                Quest.character_id == c.id,
                Quest.quest_id == S4_QUEST_ID,
                Quest.status == "active",
            )
        )
        if active_p3 or active_p4:
            brazier_id = None
            brazier_label = None
            brazier_destinations = ()
        route_destinations: list[str] = []
        charneca_route_known = bool(
            await self._p2_completed(s, c.id)
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == CHARNECA_ROUTE_UNLOCK,
                )
            )
        )
        bosque_route_known = bool(
            await self._p3_completed(s, c.id)
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == BOSQUE_ROUTE_UNLOCK,
                )
            )
        )
        ruins_route_known = bool(
            (c.level >= 8 or (c.level >= 7 and active_s4 is not None))
            and await self._p4_completed(s, c.id)
            and await self._has_location(s, c.id, RUINS_LOCATION)
            and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == RUINS_ROUTE_UNLOCK,
                )
            )
        )
        if not active_p3:
            if world.location == REFUGE and charneca_route_known:
                route_destinations.append(CHARNECA)
            elif world.location == CHARNECA:
                if charneca_route_known:
                    route_destinations.append(REFUGE)
                if bosque_route_known:
                    route_destinations.append(BOSQUE)
            elif world.location == BOSQUE and bosque_route_known:
                route_destinations.append(CHARNECA)
                if ruins_route_known and not active_p4:
                    route_destinations.append(RUINS)
            elif world.location == RUINS and ruins_route_known and not active_p4:
                route_destinations.append(BOSQUE)
            elif world.location == VDE_GARGANTA and p7_complete:
                route_destinations.append(VDE_VIGILIA)
            elif world.location == VDE_VIGILIA and p7_complete:
                route_destinations.append(VDE_GARGANTA)
                if (
                    c.level >= 13
                    and p8_started_or_complete
                    and await s.scalar(
                        select(Unlock.id).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == VDE_VIGILIA_MATA_ROUTE,
                        )
                    )
                ):
                    route_destinations.append(VDE_MATA)
            elif world.location == VDE_MATA and p7_complete:
                route_destinations.append(VDE_VIGILIA)
                if p9_started_or_complete and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VDE_MATA_BAIXIOS_ROUTE,
                    )
                ):
                    route_destinations.append(VDE_BAIXIOS)
            elif world.location == VDE_BAIXIOS and p9_started_or_complete:
                route_destinations.append(VDE_MATA)
                if p10_started_or_complete and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VDE_BAIXIOS_CLAUSTRO_ROUTE,
                    )
                ):
                    route_destinations.append(VDE_CLAUSTRO)
            elif world.location == VDE_CLAUSTRO and p10_started_or_complete and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VDE_BAIXIOS_CLAUSTRO_ROUTE,
                )
            ):
                route_destinations.append(VDE_BAIXIOS)
                if berco_access:
                    route_destinations.append(VDE_BERCO)
            elif world.location == VDE_BERCO and berco_access:
                route_destinations.append(VDE_CLAUSTRO)
                if nareth_access:
                    route_destinations.append(NARETH_CAMPINAS_LABEL)
            elif world.location == NARETH_CAMPINAS_LABEL and nareth_access:
                route_destinations.append(VDE_BERCO)
                if nareth_route_open:
                    route_destinations.append(NARETH_POSTO_LABEL)
            elif world.location == NARETH_POSTO_LABEL and nareth_access and nareth_route_open:
                route_destinations.append(NARETH_CAMPINAS_LABEL)
                if nareth_p14_open:
                    route_destinations.append(NARETH_CANAIS)
            elif world.location == NARETH_CANAIS and nareth_access and nareth_p14_open:
                route_destinations.append(NARETH_POSTO_LABEL)
                if nareth_p15_open:
                    route_destinations.append(NARETH_CAMPOS)
            elif world.location == NARETH_CAMPOS and nareth_access and nareth_p15_open:
                route_destinations.append(NARETH_CANAIS)
                if nareth_p16_open:
                    route_destinations.append(NARETH_OBSERVATORIO)
            elif world.location == NARETH_OBSERVATORIO and nareth_access and nareth_p16_open:
                route_destinations.append(NARETH_CAMPOS)
                if nareth_chamber_open and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == NARETH_OBSERVATORIO_CAMARA_ROUTE,
                    )
                ):
                    route_destinations.append(NARETH_CAMARA_LABEL)
            elif world.location == NARETH_CAMARA_LABEL and nareth_access and nareth_chamber_open and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == NARETH_OBSERVATORIO_CAMARA_ROUTE,
                )
            ):
                route_destinations.append(NARETH_OBSERVATORIO)
                if varzeas_entry_open:
                    route_destinations.append(VARZEAS_DIQUES_LABEL)
            elif world.location == VARZEAS_DIQUES_LABEL and varzeas_entry_open:
                route_destinations.append(NARETH_CAMARA_LABEL)
                if varzeas_inner_route_open:
                    route_destinations.append(VARZEAS_PORTO_LABEL)
            elif world.location == VARZEAS_PORTO_LABEL and varzeas_entry_open and varzeas_inner_route_open:
                route_destinations.append(VARZEAS_DIQUES_LABEL)
                if varzeas_brejos_route_open:
                    route_destinations.append(VARZEAS_BREJOS_LABEL)
            elif world.location == VARZEAS_BREJOS_LABEL and varzeas_entry_open and varzeas_brejos_route_open:
                route_destinations.append(VARZEAS_PORTO_LABEL)
                if varzeas_hortos_route_open:
                    route_destinations.append(VARZEAS_HORTOS_LABEL)
            elif world.location == VARZEAS_HORTOS_LABEL and varzeas_hortos_route_open:
                route_destinations.append(VARZEAS_BREJOS_LABEL)
                if varzeas_galerias_route_open:
                    route_destinations.append(VARZEAS_GALERIAS_LABEL)
            elif world.location == VARZEAS_GALERIAS_LABEL and varzeas_galerias_route_open:
                route_destinations.append(VARZEAS_HORTOS_LABEL)
                if varzeas_matrix_access and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_GALERIAS_CAMARA_ROUTE,
                    )
                ):
                    route_destinations.append(VARZEAS_CAMARA_LABEL)
            elif world.location == VARZEAS_CAMARA_LABEL and varzeas_matrix_access and await s.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == c.id,
                    Unlock.unlock_id == VARZEAS_GALERIAS_CAMARA_ROUTE,
                )
            ):
                route_destinations.append(VARZEAS_GALERIAS_LABEL)
                if altos_entry_open:
                    route_destinations.append(ALTOS_ESCARPA_LABEL)
            elif world.location == ALTOS_ESCARPA_LABEL and altos_escarpa_discovered:
                if altos_entry_open:
                    route_destinations.append(VARZEAS_CAMARA_LABEL)
                if altos_abrigo_discovered:
                    route_destinations.append(ALTOS_ABRIGO_LABEL)
            elif world.location == ALTOS_ABRIGO_LABEL and altos_abrigo_discovered:
                if altos_escarpa_discovered:
                    route_destinations.append(ALTOS_ESCARPA_LABEL)
                if altos_pontes_access_open:
                    route_destinations.append(ALTOS_PONTES_LABEL)
            elif world.location == ALTOS_PONTES_LABEL and altos_pontes_access_open:
                route_destinations.append(ALTOS_ABRIGO_LABEL)
                if altos_pedreiras_access_open:
                    route_destinations.append(ALTOS_PEDREIRAS_LABEL)
            elif world.location == ALTOS_PEDREIRAS_LABEL and altos_pedreiras_access_open:
                route_destinations.append(ALTOS_PONTES_LABEL)
                if altos_bastilha_access_open:
                    route_destinations.append(ALTOS_BASTILHA_LABEL)
            elif world.location == ALTOS_BASTILHA_LABEL and altos_bastilha_access_open:
                route_destinations.append(ALTOS_PEDREIRAS_LABEL)
                if altos_coracao_access_open:
                    route_destinations.append(ALTOS_CORACAO_LABEL)
            elif world.location == ALTOS_CORACAO_LABEL and altos_coracao_access_open:
                if altos_bastilha_discovered:
                    route_destinations.append(ALTOS_BASTILHA_LABEL)
                if confins_entry_open:
                    route_destinations.append(CONFINS_MARCHA_LABEL)
            elif world.location == CONFINS_MARCHA_LABEL and confins_marcha_discovered:
                if confins_entry_open:
                    route_destinations.append(ALTOS_CORACAO_LABEL)
                if confins_refuge_discovered:
                    route_destinations.append(CONFINS_ULTIMO_REFUGIO_LABEL)
            elif world.location == CONFINS_ULTIMO_REFUGIO_LABEL and confins_refuge_discovered:
                if confins_marcha_discovered:
                    route_destinations.append(CONFINS_MARCHA_LABEL)
                if confins_estradas_access_open:
                    route_destinations.append(CONFINS_ESTRADAS_AUSENTES_LABEL)
            elif world.location == CONFINS_ESTRADAS_AUSENTES_LABEL and confins_estradas_discovered:
                if confins_refuge_discovered:
                    route_destinations.append(CONFINS_ULTIMO_REFUGIO_LABEL)
                if confins_fraturas_access_open:
                    route_destinations.append(CONFINS_FRATURAS_LIMIAR_LABEL)
            elif world.location == CONFINS_FRATURAS_LIMIAR_LABEL and confins_fraturas_discovered:
                if confins_estradas_discovered and confins_fraturas_access_open:
                    route_destinations.append(CONFINS_ESTRADAS_AUSENTES_LABEL)
                if confins_no_access_open:
                    route_destinations.append(CONFINS_NO_CENTRAL_LABEL)
            elif world.location == CONFINS_NO_CENTRAL_LABEL and confins_no_discovered:
                if confins_fraturas_discovered and confins_no_access_open:
                    route_destinations.append(CONFINS_FRATURAS_LIMIAR_LABEL)
                if confins_camara_access_open:
                    route_destinations.append(CONFINS_CAMARA_REGENCIA_LABEL)
            elif (
                world.location == CONFINS_CAMARA_REGENCIA_LABEL
                and confins_camara_access_open
                and confins_camara_discovered
            ):
                route_destinations.append(CONFINS_NO_CENTRAL_LABEL)
        route_available = bool(route_destinations)
        material_table_ready = bool(
            hunt_profile
            and all(
                creature_id in MATERIAL_POOLS
                for creature_id, _ in hunt_profile.creature_weights
            )
        )
        if world.location == VDE_GARGANTA:
            hunt_enabled = p7_complete and material_table_ready and bool(
                await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.hunt_unlock,
                    )
                )
            )
            explore_enabled = p7_complete and bool(
                await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.explore_unlock,
                    )
                )
            )
        elif world.location == VDE_MATA:
            hunt_enabled = p8_complete and material_table_ready and c.level >= 13 and bool(
                hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.hunt_unlock,
                    )
                )
            )
            explore_enabled = (
                p8_started_or_complete
                and c.level >= 13
                and bool(
                    await s.scalar(
                        select(Unlock.id).where(
                            Unlock.character_id == c.id,
                            Unlock.unlock_id == VDE_MATA_EXPLORE_UNLOCK,
                        )
                    )
                )
            )
        elif world.location == VDE_BAIXIOS:
            hunt_enabled = p9_complete and material_table_ready and c.level >= 15 and bool(
                hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.hunt_unlock,
                    )
                )
            )
            explore_enabled = p9_started_or_complete and c.level >= 15 and bool(
                await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.explore_unlock,
                    )
                )
            )
        elif world.location == VDE_CLAUSTRO:
            hunt_enabled = c.level >= 18 and p10_complete and material_table_ready and bool(
                hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.hunt_unlock,
                    )
                )
            )
            explore_enabled = c.level >= 18 and p10_started_or_complete and bool(
                hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.explore_unlock,
                    )
                )
            )
        elif world.location == VDE_VIGILIA:
            # Vigília do Vale is a safe hub, never a generic hunt/explore local.
            hunt_enabled = False
            explore_enabled = False
        elif world.location == VDE_BERCO:
            # The Berço is a campaign climax location with no generic activity profile.
            hunt_enabled = False
            explore_enabled = False
        elif world.location in {ROAD, REFUGE, CHARNECA, BOSQUE, RUINS}:
            hunt_enabled = True
            explore_enabled = True
        elif world.location == NARETH_CAMPINAS_LABEL:
            hunt_enabled = bool(
                nareth_access
                and nareth_p13_complete
                and material_table_ready
                and hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == hunt_profile.hunt_unlock,
                    )
                )
            )
            explore_enabled = bool(
                nareth_access
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == NARETH_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == NARETH_POSTO_LABEL:
            # Posto de Nareth is a safe hub without generic activities.
            hunt_enabled = False
            explore_enabled = False
        elif world.location == NARETH_CANAIS:
            hunt_enabled = bool(
                nareth_access and nareth_p14_complete and material_table_ready and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.hunt_unlock
                ))
            )
            explore_enabled = bool(
                nareth_access and nareth_p14_open and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.explore_unlock
                ))
            )
        elif world.location == NARETH_CAMPOS:
            hunt_enabled = bool(
                nareth_access and nareth_p15_complete and material_table_ready and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.hunt_unlock
                ))
            )
            explore_enabled = bool(
                nareth_access and nareth_p15_open and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.explore_unlock
                ))
            )
        elif world.location == NARETH_OBSERVATORIO:
            hunt_enabled = bool(
                nareth_access and nareth_p16_complete and material_table_ready and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.hunt_unlock
                ))
            )
            explore_enabled = bool(
                nareth_access and nareth_p16_open and hunt_profile
                and await s.scalar(select(Unlock.id).where(
                    Unlock.character_id == c.id, Unlock.unlock_id == hunt_profile.explore_unlock
                ))
            )
        elif world.location == NARETH_CAMARA_LABEL:
            hunt_enabled = False
            explore_enabled = False
        elif world.location == VARZEAS_DIQUES_LABEL:
            hunt_enabled = bool(
                varzeas_p19_complete
                and c.level >= 31
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_DIQUES_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                varzeas_p19_complete
                and c.level >= 31
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_DIQUES_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == VARZEAS_PORTO_LABEL:
            hunt_enabled = False
            explore_enabled = False
        elif world.location == VARZEAS_BREJOS_LABEL:
            hunt_enabled = bool(
                varzeas_p20_complete
                and c.level >= 33
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_BREJOS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                varzeas_p20_complete
                and c.level >= 33
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_BREJOS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == VARZEAS_HORTOS_LABEL:
            hunt_enabled = bool(
                varzeas_p21_open
                and c.level >= 35
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_HORTOS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                varzeas_p21_open
                and c.level >= 35
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_HORTOS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == VARZEAS_GALERIAS_LABEL:
            hunt_enabled = bool(
                varzeas_p22_complete
                and c.level >= 37
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_GALERIAS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                varzeas_p22_open
                and c.level >= 37
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == VARZEAS_GALERIAS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == VARZEAS_CAMARA_LABEL:
            hunt_enabled = False
            explore_enabled = False
        elif world.location == ALTOS_ESCARPA_LABEL:
            hunt_enabled = bool(
                altos_entry_open
                and altos_p25_complete
                and altos_escarpa_discovered
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_ESCARPA_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                altos_entry_open
                and altos_p25_complete
                and altos_escarpa_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_ESCARPA_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == ALTOS_ABRIGO_LABEL:
            # Abrigo do Peso is a campaign hub without Hunt or Desbravar.
            hunt_enabled = False
            explore_enabled = False
        elif world.location == ALTOS_PONTES_LABEL:
            hunt_enabled = bool(
                altos_pontes_access_open
                and altos_p26_complete
                and altos_pontes_discovered
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_PONTES_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                altos_pontes_access_open
                and altos_p26_complete
                and altos_pontes_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_PONTES_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == ALTOS_PEDREIRAS_LABEL:
            hunt_enabled = bool(
                altos_pedreiras_access_open
                and altos_p27_complete
                and altos_pedreiras_discovered
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_PEDREIRAS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                altos_pedreiras_access_open
                and altos_p27_complete
                and altos_pedreiras_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == ALTOS_BASTILHA_LABEL:
            hunt_enabled = bool(
                altos_bastilha_access_open
                and altos_p28_complete
                and altos_bastilha_discovered
                and material_table_ready
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_BASTILHA_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                altos_bastilha_access_open
                and altos_p28_complete
                and altos_bastilha_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == ALTOS_BASTILHA_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == ALTOS_CORACAO_LABEL:
            hunt_enabled = False
            explore_enabled = False
        elif world.location == CONFINS_MARCHA_LABEL:
            hunt_enabled = bool(
                confins_entry_open
                and confins_p31_complete
                and confins_marcha_discovered
                and material_table_ready
                and hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_MARCHA_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                confins_entry_open
                and confins_p31_complete
                and confins_marcha_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_MARCHA_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == CONFINS_ULTIMO_REFUGIO_LABEL:
            hunt_enabled = False
            explore_enabled = False
        elif world.location == CONFINS_ESTRADAS_AUSENTES_LABEL:
            hunt_enabled = bool(
                confins_entry_open
                and confins_p32_complete
                and confins_estradas_discovered
                and material_table_ready
                and hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_ESTRADAS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                confins_entry_open
                and confins_p32_complete
                and confins_estradas_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_ESTRADAS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == CONFINS_FRATURAS_LIMIAR_LABEL:
            hunt_enabled = bool(
                confins_entry_open
                and confins_p33_complete
                and confins_fraturas_discovered
                and material_table_ready
                and hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_FRATURAS_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                confins_entry_open
                and confins_p33_complete
                and confins_fraturas_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_FRATURAS_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == CONFINS_NO_CENTRAL_LABEL:
            hunt_enabled = bool(
                confins_entry_open
                and confins_p34_complete
                and confins_no_discovered
                and material_table_ready
                and hunt_profile
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_NO_CENTRAL_HUNT_UNLOCK,
                    )
                )
            )
            explore_enabled = bool(
                confins_entry_open
                and confins_p34_complete
                and confins_no_discovered
                and await s.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == c.id,
                        Unlock.unlock_id == CONFINS_NO_CENTRAL_EXPLORE_UNLOCK,
                    )
                )
            )
        elif world.location == CONFINS_CAMARA_REGENCIA_LABEL:
            hunt_enabled = False
            explore_enabled = False
        else:
            # Every other known travel location must be handled explicitly above.
            return self._invalid_location_view(c, world)
        kind_by_location = {
            ROAD: "road",
            REFUGE: "refuge",
            CHARNECA: "charneca",
            BOSQUE: "bosque",
            RUINS: "ruinas",
            VDE_GARGANTA: "vde_garganta",
            VDE_VIGILIA: "vde_vigilia",
            VDE_MATA: "vde_mata",
            VDE_BAIXIOS: "vde_baixios",
            VDE_CLAUSTRO: "vde_claustro",
            VDE_BERCO: "vde_berco",
            NARETH_CAMPINAS_LABEL: "nareth_campinas",
            NARETH_POSTO_LABEL: "nareth_posto",
            NARETH_CANAIS: "nareth_canais",
            NARETH_CAMPOS: "nareth_campos",
            NARETH_OBSERVATORIO: "nareth_observatorio",
            NARETH_CAMARA_LABEL: "nareth_camara",
            VARZEAS_DIQUES_LABEL: "varzeas_diques",
            VARZEAS_PORTO_LABEL: "varzeas_porto",
            VARZEAS_BREJOS_LABEL: "varzeas_brejos",
            VARZEAS_HORTOS_LABEL: "varzeas_hortos",
            VARZEAS_GALERIAS_LABEL: "varzeas_galerias",
            VARZEAS_CAMARA_LABEL: "varzeas_camara",
            ALTOS_ESCARPA_LABEL: "altos_escarpa",
            ALTOS_ABRIGO_LABEL: "altos_abrigo",
            ALTOS_PONTES_LABEL: "altos_pontes",
            ALTOS_PEDREIRAS_LABEL: "altos_pedreiras",
            ALTOS_BASTILHA_LABEL: "altos_bastilha",
            ALTOS_CORACAO_LABEL: "altos_coracao",
            CONFINS_MARCHA_LABEL: "confins_marcha",
            CONFINS_ULTIMO_REFUGIO_LABEL: "confins_ultimo_refugio",
            CONFINS_ESTRADAS_AUSENTES_LABEL: "confins_estradas_ausentes",
            CONFINS_FRATURAS_LIMIAR_LABEL: "confins_fraturas_limiar",
            CONFINS_NO_CENTRAL_LABEL: "confins_no_central",
            CONFINS_CAMARA_REGENCIA_LABEL: "confins_camara_regencia",
        }
        return RoadView(
            kind_by_location[world.location],
            c.id,
            world.location,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            familiar=familiar,
            hunt_enabled=hunt_enabled,
            explore_enabled=explore_enabled,
            explore_available=explore_available,
            route_available=route_available,
            route_destinations=tuple(route_destinations),
            brazier_id=brazier_id,
            brazier_label=brazier_label,
            brazier_destinations=brazier_destinations,
        )

    async def _locked_world(self, s, actor):
        c = await s.scalar(
            select(Character)
            .where(Character.telegram_id == actor, Character.server_id == self.server_id)
            .with_for_update()
        )
        if c is None:
            return None, None
        await reconcile_character_vigor(s, c)
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
            character_id = values.get("character_id")
            should_reconcile = model in {LocationDiscovery, Brazier}
            if model is Unlock and values.get("unlock_id") in {
                "dungeon.tdo.cripta_ocaso",
                "dungeon.tdo.galerias_vigia",
            }:
                should_reconcile = True
            if character_id is not None and should_reconcile:
                from asterion.application.tdo_feats import reconcile_tdo_feats_for_character

                await reconcile_tdo_feats_for_character(s, character_id)
                from asterion.application.nareth_feats import (
                    NARETH_BRAZIERS,
                    NARETH_LOCATIONS,
                    reconcile_nareth_feats_for_character,
                )

                nareth_source = (
                    values.get("location_id") in NARETH_LOCATIONS
                    if model is LocationDiscovery
                    else values.get("brazier_id") in NARETH_BRAZIERS
                )
                if nareth_source:
                    await reconcile_nareth_feats_for_character(s, character_id)
            return True
        return False

    async def deliver_material(
        self,
        s,
        c,
        material_id: str,
        quantity: int,
        source_key: str,
        *,
        bound: bool = False,
    ) -> None:
        """Share the existing Inventory/Pending/Blocked material policy."""
        await self._deliver_material(s, c, material_id, quantity, source_key, bound=bound)

    async def _deliver_material(
        self,
        s,
        c,
        material_id: str,
        quantity: int,
        source_key: str,
        *,
        bound: bool = False,
    ) -> None:
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
        if (
            await s.scalar(
                select(PendingItem)
                .where(
                    PendingItem.character_id == c.id,
                    PendingItem.source_key == source_key,
                )
                .with_for_update()
            )
            is not None
        ):
            return
        remaining = await self._deliver_material_to_inventory(s, c, material_id, quantity, bound)
        if remaining:
            await self._pending(
                s,
                c.id,
                source_key,
                "material",
                {"material_id": material_id, "bound": bound},
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
                    MaterialStack.quantity > 0,
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
        while remaining > 0 and await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
            added = min(remaining, 999)
            empty_stack = await s.scalar(
                select(MaterialStack)
                .where(
                    MaterialStack.character_id == c.id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(bound),
                    MaterialStack.quantity == 0,
                )
                .order_by(MaterialStack.id)
                .with_for_update()
            )
            if empty_stack is not None:
                empty_stack.quantity = added
            else:
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

    async def _deliver_consumable_to_inventory(self, s, c, consumable_id, quantity):
        stack = await s.scalar(
            select(ConsumableStack)
            .where(
                ConsumableStack.character_id == c.id,
                ConsumableStack.consumable_id == consumable_id,
            )
            .with_for_update()
        )
        if stack is not None:
            room = max(0, 99 - stack.quantity)
            if stack.quantity > 0 or await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
                added = min(quantity, room)
                if added:
                    stack.quantity += added
                    quantity -= added
            return quantity
        if quantity > 0 and await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
            added = min(quantity, 99)
            s.add(
                ConsumableStack(
                    character_id=c.id,
                    consumable_id=consumable_id,
                    quantity=added,
                )
            )
            quantity -= added
        return quantity

    async def _inventory_slots(self, s, character_id):
        return await inventory_slots(s, character_id)

    async def _pending(self, s, character_id, source_key, kind, payload, quantity=1):
        if kind == "equipment":
            _, payload = equipment_instance_payload(payload)
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
        existing = await s.scalar(
            select(PendingItem)
            .where(PendingItem.character_id == character_id, PendingItem.source_key == source_key)
            .with_for_update()
        )
        if existing is not None:
            return
        count = (
            await s.scalar(
                select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)
            )
            or 0
        )
        if count < PENDING_CAPACITY:
            s.add(
                PendingItem(
                    character_id=character_id,
                    source_key=source_key,
                    kind=kind,
                    payload=payload,
                    quantity=quantity,
                )
            )
        else:
            character = await s.scalar(
                select(Character).where(Character.id == character_id).with_for_update()
            )
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
                item_instance_id, payload = equipment_instance_payload(payload)
                if await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
                    s.add(
                        EquipmentItem(
                            id=item_instance_id,
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
                if stack is not None and (
                    stack.quantity > 0
                    or await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY
                ):
                    stack.quantity += hold.quantity
                    self._resolve_delivery(hold)
                elif await self._inventory_slots(s, c.id) < INVENTORY_CAPACITY:
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
            elif hold.kind == "consumable":
                remaining = await self._deliver_consumable_to_inventory(
                    s, c, payload["consumable_id"], hold.quantity
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
                if remaining == 0:
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
        count = (
            await s.scalar(
                select(func.count(PendingItem.id)).where(PendingItem.character_id == character_id)
            )
            or 0
        )
        return PENDING_CAPACITY - int(count)

    @staticmethod
    def _resolve_delivery(hold):
        hold.status = "resolved"
        hold.resolved_at = datetime.now(UTC)

    async def _hunt_victory_view(self, s, c, activity):
        context = await s.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == activity.id)
        )
        if context is None:
            return None
        rows = (
            await s.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(
                    RewardEvent.character_id == c.id,
                    RewardEvent.source_id == f"activity:{activity.id}",
                )
                .order_by(RewardComponent.id)
            )
        ).all()
        labels = {
            "material.tdo.ferro_de_fuligem": "Ferro de Fuligem",
            "material.tdo.couro_escoriado": "Couro Escoriado",
            "material.tdo.erva_cinzenta": "Erva Cinzenta",
            "material.tdo.residuo_ocaso": "Resíduo do Ocaso",
            "material.tdo.catalisador_elite_i": "Catalisador de Elite I",
            "material.tdo.fragmento_aprimoramento_i": "Fragmento de Aprimoramento I",
            "material.nareth.catalisador_elite_iii": "Catalisador de Elite III",
            "material.nareth.fragmento_aprimoramento_iii": "Fragmento de Aprimoramento III",
            "material.varzeas.ferro_de_salmoura": "Ferro de Salmoura",
            "material.varzeas.couro_de_varzea": "Couro de Várzea",
            "material.varzeas.junco_ferruginoso": "Junco Ferruginoso",
            "material.varzeas.soro_antigo": "Soro Antigo",
            "material.varzeas.catalisador_elite_iv": "Catalisador de Elite IV",
            "material.varzeas.fragmento_aprimoramento_iv": "Fragmento de Aprimoramento IV",
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
                reward_lines.append(
                    f"📦 {labels.get(row.item_id, row.item_id or row.kind)} · {row.quantity}"
                )
        return RoadView(
            "hunt_victory",
            c.id,
            _location_label(context.local_id),
            activity_id=activity.id,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            reward_lines=tuple(reward_lines),
            creature=creature_for(context.creature_id).name,
            variant=VARIANT_LABELS.get(context.variant, context.variant),
        )

    def _explore_limit_view(self, c, recent, last, now, sixth=None, location=ROAD):
        if recent >= 6:
            attempts = (
                [sixth.created_at + timedelta(minutes=60)] if sixth and sixth.created_at else []
            )
            available_at = min(attempts) if attempts else now
            return RoadView(
                "explore_limit",
                c.id,
                location,
                vigor=c.vigor,
                max_vigor=c.max_vigor,
                name=c.name,
                hp=c.hp,
                max_hp=c.max_hp,
                result_text=_remaining(available_at, now),
            )
        available_at = last.created_at + timedelta(minutes=5)
        return RoadView(
            "explore_cooldown",
            c.id,
            location,
            vigor=c.vigor,
            max_vigor=c.max_vigor,
            name=c.name,
            hp=c.hp,
            max_hp=c.max_hp,
            result_text=_remaining(available_at, now),
        )

    async def _explore_retry_available(self, s, c, attempt) -> bool:
        if attempt is None or attempt.status == "active":
            return False
        now = datetime.now(UTC)
        local_id = attempt.local_id
        recent = (
            await s.scalar(
                select(func.count(ExplorationAttempt.id)).where(
                    ExplorationAttempt.character_id == c.id,
                    ExplorationAttempt.local_id == local_id,
                    ExplorationAttempt.created_at >= now - timedelta(minutes=60),
                )
            )
            or 0
        )
        if recent >= 6:
            return False
        last = await s.scalar(
            select(ExplorationAttempt)
            .where(
                ExplorationAttempt.character_id == c.id,
                ExplorationAttempt.local_id == local_id,
            )
            .order_by(ExplorationAttempt.created_at.desc(), ExplorationAttempt.id.desc())
            .limit(1)
        )
        return not (
            last is not None and last.created_at and last.created_at > now - timedelta(minutes=5)
        )

    async def _attempt_view(self, s, c, attempt, location=None, text=None):
        location = location or _location_label(attempt.local_id if attempt else ROAD)
        persisted = (attempt.progress or {}).get("receipt_text") or (attempt.progress or {}).get(
            "result_text"
        )
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
            recovery_brazier=(attempt.progress or {}).get("recovery_brazier"),
            recovery_location=(attempt.progress or {}).get("recovery_location"),
            route_available=(
                attempt.local_id == CHARNECA_LOCATION
                and (attempt.progress or {}).get("recovery_location") == REFUGE
                or attempt.local_id == BOSQUE_LOCATION
                and (attempt.progress or {}).get("recovery_location") == CHARNECA
                or attempt.local_id == RUINS_LOCATION
                and (attempt.progress or {}).get("recovery_location") in {BOSQUE, CHARNECA, REFUGE}
            ),
        )


def _explore_result(
    seed: str,
    player_level: int = 1,
    recent: tuple[str, ...] = (),
    excluded: tuple[str, ...] = (),
    profile=ROAD_EXPLORATION_PROFILE,
) -> tuple[str, str, str]:
    key = select_exploration_result(seed, player_level, recent, excluded, profile=profile)
    result = profile.result(key)
    return result.category, result.result_id, result.text


def _draw_int(seed: str, purpose: str, modulo: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest(), "big") % modulo


def _fixed_percent_xp(reference_level: int, percent: str) -> int:
    return int(
        (Decimal(level_xp(reference_level)) * Decimal(percent)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


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
    if category not in {"common", "uncommon", "elite"}:
        raise ValueError(f"Hunt loot rarity is not configured for {category!r}")
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
            else ((65, "Comum"), (94, "Raro"), (99.5, "Épico"), (100, "Lendário"))
            if category == "uncommon"
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
            if category in {"common", "uncommon"}
            else ((80, "Rara"), (98, "Épica"), (100, "Lendária"))
        )
    for limit, rarity in bands:
        if roll < limit:
            return rarity
    return bands[-1][1]
