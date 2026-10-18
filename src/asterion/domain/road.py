"""Pure, deterministic rules for the Estrada das Cinzas repeatable content."""
# ruff: noqa: E501

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from hashlib import sha256
from uuid import UUID

from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    StatMultipliers,
    enemy_stats,
    growth,
    resolve_combat_stats,
)
from asterion.domain.equipment_modifications import (
    RARITY_MULT,
    SECONDARY_SCALE,
    SLOT_WEIGHTS,
    rune_potency_for,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.prologue import first_art
from asterion.domain.weapon_metadata import weapon_definition

D = Decimal
RULESET = CURRENT_COMBAT_RULESET
ROAD_LOCATION = "tdo.location.estrada_das_cinzas"
CHARNECA_LOCATION = "tdo.location.charneca_da_fuligem"
BOSQUE_LOCATION = "tdo.location.bosque_calcinado"
RUINS_LOCATION = "tdo.location.ruinas_do_vigia"
VDE_GARGANTA_LOCATION = "vde.location.garganta_dos_lacos"
VDE_VIGILIA_LOCATION = "vde.location.vigilia_do_vale"
VDE_MATA_LOCATION = "vde.location.mata_suspensa"
VDE_BAIXIOS_LOCATION = "vde.location.baixios_enredados"
VDE_CLAUSTRO_LOCATION = "vde.location.claustro_das_raizes"
VDE_BERCO_LOCATION = "vde.location.berco_da_matriarca"
NARETH_CAMPINAS_LOCATION = "nareth.location.campinas_do_meridiano"
NARETH_POSTO_LOCATION = "nareth.location.posto_de_nareth"
NARETH_CANAIS_LOCATION = "nareth.location.canais_secos"
NARETH_CAMPOS_LOCATION = "nareth.location.campos_invertidos"
NARETH_OBSERVATORIO_LOCATION = "nareth.location.observatorio_do_eixo"
NARETH_CAMARA_LOCATION = "nareth.location.camara_do_arconte"
VARZEAS_DIQUES_LOCATION = "varzeas.location.diques_rubros"
VARZEAS_PORTO_LOCATION = "varzeas.location.porto_da_salmoura"
VARZEAS_BREJOS_LOCATION = "varzeas.location.brejos_do_pulso"
VARZEAS_HORTOS_LOCATION = "varzeas.location.hortos_hemaris"
VARZEAS_GALERIAS_LOCATION = "varzeas.location.galerias_transferencia"
VARZEAS_CAMARA = "Câmara da Matriz"
VARZEAS_CAMARA_LOCATION = "varzeas.location.camara_da_matriz"
VARZEAS_CAMARA_ACCESS_UNLOCK = "region.varzeas.camara_matriz.available"
ALTOS_REGION = "Altos Cinéreos"
ALTOS_ESCARPA = "Escarpa da Cinza"
ALTOS_ABRIGO = "Abrigo do Peso"
ALTOS_PONTES = "Pontes de Fuligem"
ALTOS_PEDREIRAS = "Pedreiras Suspensas"
ALTOS_BASTILHA = "Bastilha de Carga"
ALTOS_CORACAO = "Coração do Colosso"
ALTOS_ESCARPA_LOCATION = "location.altos.escarpa_cinza"
ALTOS_ABRIGO_LOCATION = "location.altos.abrigo_peso"
ALTOS_PONTES_LOCATION = "location.altos.pontes_fuligem"
ALTOS_PEDREIRAS_LOCATION = "location.altos.pedreiras_suspensas"
ALTOS_BASTILHA_LOCATION = "location.altos.bastilha_carga"
ALTOS_CORACAO_LOCATION = "location.altos.coracao_colosso"
ALTOS_ESCARPA_ACCESS_UNLOCK = "unlock.location.altos.escarpa_cinza"
ALTOS_ABRIGO_ACCESS_UNLOCK = "unlock.location.altos.abrigo_peso"
ALTOS_PONTES_ACCESS_UNLOCK = "unlock.location.altos.pontes_fuligem"
ALTOS_PEDREIRAS_ACCESS_UNLOCK = "unlock.location.altos.pedreiras_suspensas"
ALTOS_BASTILHA_ACCESS_UNLOCK = "unlock.location.altos.bastilha_carga"
ALTOS_CORACAO_ACCESS_UNLOCK = "unlock.location.altos.coracao_colosso"
ALTOS_ESCARPA_BRAZIER = "bonfire.altos.escarpa"
ALTOS_ABRIGO_BRAZIER = "bonfire.altos.abrigo"
ALTOS_PONTES_BRAZIER = "bonfire.altos.ponte_alta"
ALTOS_PEDREIRA_BRAZIER = "bonfire.altos.pedreira_velha"
ALTOS_BASTILHA_BRAZIER = "bonfire.altos.bastilha_externa"
ALTOS_ESCARPA_HUNT_UNLOCK = "unlock.hunt.altos.escarpa"
ALTOS_ESCARPA_EXPLORE_UNLOCK = "unlock.explore.altos.escarpa"
ALTOS_ESCARPA_ROUND_UNLOCK = "unlock.round.altos.escarpa"
ALTOS_PONTES_HUNT_UNLOCK = "unlock.hunt.altos.pontes"
ALTOS_PONTES_EXPLORE_UNLOCK = "unlock.explore.altos.pontes"
ALTOS_PONTES_ROUND_UNLOCK = "unlock.round.altos.pontes"
ALTOS_PEDREIRAS_HUNT_UNLOCK = "unlock.hunt.altos.pedreiras"
ALTOS_PEDREIRAS_EXPLORE_UNLOCK = "unlock.explore.altos.pedreiras"
ALTOS_PEDREIRAS_ROUND_UNLOCK = "unlock.round.altos.pedreiras"
ALTOS_PEDREIRAS_DUNGEON_UNLOCK = "unlock.dungeon.altos.pedreira_contrapeso"
ALTOS_BASTILHA_HUNT_UNLOCK = "unlock.hunt.altos.bastilha"
ALTOS_BASTILHA_EXPLORE_UNLOCK = "unlock.explore.altos.bastilha"
ALTOS_BASTILHA_ROUND_UNLOCK = "unlock.round.altos.bastilha"
ALTOS_BASTILHA_DUNGEON_UNLOCK = "unlock.dungeon.altos.bastilha_profunda"
ALTOS_LOBO_ESCARPA = "creature.altos.lobo_escarpa"
ALTOS_ABUTRE_FULIGEM = "creature.altos.abutre_fuligem"
ALTOS_ESCARAVELHO_BASALTO = "creature.altos.escaravelho_basalto"
ALTOS_CARNEIRO_PESO = "creature.altos.carneiro_peso"
ALTOS_QUEBRA_ESCARPAS = "elite.altos.quebra_escarpas"
ALTOS_LAGARTO_ESCORIA = "creature.altos.lagarto_escoria"
ALTOS_QUEBRA_CABOS = "creature.altos.quebra_cabos"
ALTOS_DEVORADOR_ESCORIA = "elite.altos.devorador_escoria"
ALTOS_MORCEGO_CHAMINE = "creature.altos.morcego_chamine"
ALTOS_CARCACA_MINERAL = "creature.altos.carcaca_mineral"
ALTOS_VIGIA_CARGA = "creature.altos.vigia_carga"
ALTOS_SUPERVISOR_CARGA = "elite.altos.supervisor_carga"
ALTOS_COLOSSO_CINEREO = "boss.altos.colosso_cinereo"
ALTOS_CUSTODIO_ULTIMO_TURNO = "boss.altos.s30.custodio_ultimo_turno"
ALTOS_FERRO_CONTRAPESO = "material.altos.ferro_contrapeso"
ALTOS_COURO_ESCARPA = "material.altos.couro_escarpa"
ALTOS_LIQUEN_PEDREIRA = "material.altos.liquen_pedreira"
ALTOS_CINZA_BASALTO = "material.altos.cinza_basalto"
NARETH_CAMPINAS = "Campinas do Meridiano"
NARETH_POSTO = "Posto de Nareth"
NARETH_CANAIS = "Canais Secos"
NARETH_CAMPOS = "Campos Invertidos"
NARETH_OBSERVATORIO = "Observatório do Eixo"
NARETH_CAMARA = "Câmara do Arconte"
NARETH_REGION = "Planícies de Nareth"
VARZEAS_DIQUES = "Diques Rubros"
VARZEAS_PORTO = "Porto da Salmoura"
VARZEAS_BREJOS = "Brejos do Pulso"
VARZEAS_HORTOS = "Hortos Hemaris"
VARZEAS_GALERIAS = "Galerias de Transferência"
VARZEAS_REGION = "Várzeas Carmesins"
NARETH_BRAZIER_HORIZONTE = "nareth.brazier.horizonte"
NARETH_BRAZIER_POSTO = "nareth.brazier.posto"
NARETH_BRAZIER_CANAIS = "nareth.brazier.canal_alto"
NARETH_BRAZIER_CAMPOS = "nareth.brazier.linha_quebrada"
NARETH_BRAZIER_OBSERVATORIO = "nareth.brazier.eixo"
NARETH_HUNT_UNLOCK = "hunt.manual.nareth.campinas_do_meridiano"
NARETH_EXPLORE_UNLOCK = "explore.nareth.campinas_do_meridiano"
NARETH_ROUND_FAMILIARITY = "hunt_round.nareth.campinas_do_meridiano"
NARETH_CAMPINAS_POSTO_ROUTE = "route.nareth.campinas_posto"
NARETH_POSTO_CANAIS_ROUTE = "route.nareth.posto_canais"
NARETH_CANAIS_CAMPOS_ROUTE = "route.nareth.canais_campos"
NARETH_CAMPOS_OBSERVATORIO_ROUTE = "route.nareth.campos_observatorio"
NARETH_OBSERVATORIO_CAMARA_ROUTE = "route.nareth.observatorio_camara"
NARETH_REGION_UNLOCK = "region.nareth.available"
VARZEAS_REGION_ENTRY_UNLOCK = "region.varzeas_carmesins.available"
VARZEAS_DIQUES_BRAZIER = "varzeas.brazier.dique_alto"
VARZEAS_PORTO_BRAZIER = "varzeas.brazier.porto"
VARZEAS_BREJOS_BRAZIER = "varzeas.brazier.juncos_baixos"
VARZEAS_HORTOS_BRAZIER = "varzeas.brazier.horto_seco"
VARZEAS_GALERIAS_BRAZIER = "varzeas.brazier.valvulas"
VARZEAS_DIQUES_HUNT_UNLOCK = "hunt.manual.varzeas.diques_rubros"
VARZEAS_DIQUES_EXPLORE_UNLOCK = "explore.varzeas.diques_rubros"
VARZEAS_DIQUES_ROUND_FAMILIARITY = "hunt_round.varzeas.diques_rubros"
VARZEAS_DIQUES_PORTO_ROUTE = "route.varzeas.diques_porto"
VARZEAS_BREJOS_HUNT_UNLOCK = "hunt.manual.varzeas.brejos_do_pulso"
VARZEAS_BREJOS_EXPLORE_UNLOCK = "explore.varzeas.brejos_do_pulso"
VARZEAS_BREJOS_ROUND_FAMILIARITY = "hunt_round.varzeas.brejos_do_pulso"
VARZEAS_PORTO_BREJOS_ROUTE = "route.varzeas.porto_brejos"
VARZEAS_BREJOS_HORTOS_ROUTE = "route.varzeas.brejos_hortos"
VARZEAS_HORTOS_HUNT_UNLOCK = "hunt.manual.varzeas.hortos_hemaris"
VARZEAS_HORTOS_EXPLORE_UNLOCK = "explore.varzeas.hortos_hemaris"
VARZEAS_HORTOS_ROUND_FAMILIARITY = "hunt_round.varzeas.hortos_hemaris"
VARZEAS_GALERIAS_HUNT_UNLOCK = "hunt.manual.varzeas.galerias_transferencia"
VARZEAS_GALERIAS_EXPLORE_UNLOCK = "explore.varzeas.galerias_transferencia"
VARZEAS_GALERIAS_ROUND_FAMILIARITY = "hunt_round.varzeas.galerias_transferencia"
VARZEAS_HORTOS_GALERIAS_ROUTE = "route.varzeas.hortos_galerias_transferencia"
VARZEAS_GALERIAS_CAMARA_ROUTE = "route.varzeas.galerias_camara_matriz"
ROAD_BRAZIER = "tdo.brazier.estrada"
CHARNECA_BRAZIER = "tdo.brazier.vento_morto"
BOSQUE_BRAZIER = "tdo.brazier.galhos_mortos"
RUINS_BRAZIER = "tdo.brazier.poente"
HUNT_UNLOCK = "hunt_manual.estrada_das_cinzas"
EXPLORE_UNLOCK = "explore.estrada_das_cinzas"
ROUND_FAMILIARITY = "hunt_round.estrada_das_cinzas"
CHARNECA_HUNT_UNLOCK = "hunt_manual.charneca_da_fuligem"
CHARNECA_EXPLORE_UNLOCK = "explore.charneca_da_fuligem"
CHARNECA_ROUND_FAMILIARITY = "hunt_round.charneca_da_fuligem"
CHARNECA_ROUTE_UNLOCK = "route.tdo.refugio_charneca"
BOSQUE_HUNT_UNLOCK = "hunt_manual.bosque_calcinado"
BOSQUE_EXPLORE_UNLOCK = "explore.bosque_calcinado"
BOSQUE_ROUND_FAMILIARITY = "hunt_round.bosque_calcinado"
BOSQUE_ROUTE_UNLOCK = "route.tdo.charneca_bosque"
RUINS_HUNT_UNLOCK = "hunt_manual.ruinas_do_vigia"
RUINS_EXPLORE_UNLOCK = "explore.ruinas_do_vigia"
RUINS_ROUND_FAMILIARITY = "hunt_round.ruinas_do_vigia"
RUINS_ROUTE_UNLOCK = "route.tdo.bosque_ruinas"
VDE_GARGANTA_BRAZIER = "vde.brazier.garganta_dos_lacos"
VDE_MATA_BRAZIER = "vde.brazier.mata_suspensa"
VDE_BAIXIOS_BRAZIER = "vde.brazier.turfa_fria"
VDE_GARGANTA_HUNT_UNLOCK = "hunt.manual.vde.garganta_dos_lacos"
VDE_GARGANTA_EXPLORE_UNLOCK = "explore.vde.garganta_dos_lacos"
VDE_GARGANTA_ROUND_FAMILIARITY = "hunt_round.vde.garganta_dos_lacos"
VDE_GARGANTA_VIGILIA_ROUTE = "route.vde.garganta_vigilia"
VDE_VIGILIA_MATA_ROUTE = "route.vde.vigilia_mata"
VDE_MATA_HUNT_UNLOCK = "hunt.manual.vde.mata_suspensa"
VDE_MATA_EXPLORE_UNLOCK = "explore.vde.mata_suspensa"
VDE_MATA_ROUND_FAMILIARITY = "hunt_round.vde.mata_suspensa"
VDE_BAIXIOS_HUNT_UNLOCK = "hunt.manual.vde.baixios_enredados"
VDE_BAIXIOS_EXPLORE_UNLOCK = "explore.vde.baixios_enredados"
VDE_BAIXIOS_ROUND_FAMILIARITY = "hunt_round.vde.baixios_enredados"
VDE_MATA_BAIXIOS_ROUTE = "route.vde.mata_baixios"
VDE_CLAUSTRO_BRAZIER = "vde.brazier.pedras_enlacadas"
VDE_CLAUSTRO_HUNT_UNLOCK = "hunt.manual.vde.claustro_das_raizes"
VDE_CLAUSTRO_EXPLORE_UNLOCK = "explore.vde.claustro_das_raizes"
VDE_CLAUSTRO_ROUND_FAMILIARITY = "hunt_round.vde.claustro_das_raizes"
VDE_BAIXIOS_CLAUSTRO_ROUTE = "route.vde.baixios_claustro"
VDE_CLAUSTRO_BERCO_ROUTE = "route.vde.claustro_berco"
VDE_SANCTUARY_UNLOCK = "dungeon.vde.santuario_no_antigo"
EXPLORATION_CATEGORY_WEIGHTS = {
    "great_discovery": 8,
    "knowledge": 22,
    "narrative": 15,
    "combat": 25,
    "resource": 10,
    "atmospheric": 20,
}
EXPLORATION_SUBWEIGHTS = {
    "great_discovery": (("marco_viajantes", 100),),
    "knowledge": (("rastros_cinereos", 60), ("sinais_margem", 40)),
    "narrative": (("luzes", 70), ("vozes_vento", 30)),
    "combat": (("dog_cinereo", 40), ("corvo_fuligem", 35), ("peregrino_calcinado", 25)),
    "resource": (("ferro", 30), ("couro", 30), ("erva", 20), ("residuo", 20)),
    "atmospheric": (("cinza_pegadas", 34), ("carroca", 33), ("fogueira", 33)),
}

def anti_repeat_weight(weight: int, key: str, recent: tuple[str, ...] = ()) -> int:
    """Return an exact hundredths weight for the result-specific penalty."""
    if recent and key == recent[0]:
        return 0
    return weight * 35 if key in recent else weight * 100


def weighted_recent_choice(seed: str, entries: tuple[tuple[str, int], ...], recent: tuple[str, ...] = ()) -> str:
    """Select with the official anti-repeat weights, before drawing a subresult."""
    adjusted = tuple(
        (key, anti_repeat_weight(weight, key, recent))
        for key, weight in entries
    )
    eligible = tuple((key, weight) for key, weight in adjusted if weight > 0)
    if not eligible:
        raise ValueError("no eligible result after anti-repeat filtering")
    return weighted_choice(seed, eligible)

CATEGORY = {
    "common": StatMultipliers(D("0.70"), D("0.82"), D("0.90"), D("0.95")),
    "uncommon": StatMultipliers(D("0.85"), D("0.90"), D("0.95"), D("1.00")),
    "elite": StatMultipliers(D("1.50"), D("1.05"), D("1.05"), D("1.02")),
    "boss": StatMultipliers(D("2.20"), D("1.10"), D("1.10"), D("1.00")),
}
ARCHETYPE = {
    "balanced": StatMultipliers(D(1), D(1), D(1), D(1)),
    "brute": StatMultipliers(D("1.15"), D("1.12"), D("0.95"), D("0.85")),
    "predator": StatMultipliers(D("0.90"), D("1.10"), D("0.90"), D("1.20")),
    "armored": StatMultipliers(D("1.10"), D("0.88"), D("1.20"), D("0.85")),
    "caster": StatMultipliers(D("0.85"), D("1.15"), D("0.88"), D("1.00")),
    "controller": StatMultipliers(D("0.95"), D("0.90"), D("1.00"), D("1.10")),
}


@dataclass(frozen=True)
class Creature:
    creature_id: str
    name: str
    category: str
    archetype: str
    unlock_level: int
    max_level: int
    weight: int
    ai: tuple[str, ...]
    actions: tuple[tuple, ...]
    ai_priority: tuple[str, ...] = ()
    damage_taken_modifiers: tuple[tuple[str, Decimal], ...] = ()


CREATURES = (
    Creature(
        "dog_cinereo",
        "Cão Cinéreo",
        "common",
        "predator",
        1,
        3,
        34,
        ("bite", "bite", "charge"),
        (
            ("bite", "Mordida Faminta", D("1.00"), 0, D(0), 0),
            ("charge", "Investida Curta", D("1.10"), 1, D(0), 0),
        ),
    ),
    Creature(
        "corvo_fuligem",
        "Corvo de Fuligem",
        "common",
        "predator",
        1,
        4,
        33,
        ("dive", "peck"),
        (
            ("peck", "Bicada", D("0.95"), 0, D(0), 0),
            ("dive", "Rasante", D("0.90"), 1, D("0.08"), 1),
        ),
    ),
    Creature(
        "peregrino_calcinado",
        "Peregrino Calcinado",
        "common",
        "balanced",
        2,
        5,
        30,
        ("strike", "strike", "defend"),
        (("strike", "Golpe Desesperado", D("1.05"), 0, D(0), 0),),
    ),
    Creature(
        "alfa_cinereo",
        "Alfa Cinéreo",
        "elite",
        "predator",
        3,
        4,
        3,
        ("rend", "rend", "leap", "bite"),
        (
            ("bite", "Mordida Alfa", D("1.00"), 0, D(0), 0),
            ("rend", "Investida Rasgante", D("0.90"), 1, D(0), 0, "bleed", 1, False),
            ("leap", "Salto Predatório", D("1.60"), 3, D(0), 0, None, 0, True),
        ),
    ),
)

CERVO = Creature(
    "cervo_escoriado",
    "Cervo Escoriado",
    "common",
    "brute",
    4,
    7,
    0,
    ("antler_gore", "ocaso_charge"),
    (
        ("antler_gore", "Chifrada", D("1.05"), 0, D(0), 0),
        ("ocaso_charge", "Carga do Ocaso", D("1.60"), 0, D(0), 0, None, 0, True),
    ),
)

SPIDER = Creature(
    "aranha_cinza",
    "Aranha de Cinza",
    "uncommon",
    "controller",
    3,
    6,
    0,
    ("toxic_bite", "bite"),
    (
        ("toxic_bite", "Picada Tóxica", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("bite", "Mordida", D("0.95"), 0, D(0), 0),
    ),
    ai_priority=("toxic_bite", "bite"),
    damage_taken_modifiers=(("burn", D("1.10")), ("poison", D("0.90"))),
)
GHOUL = Creature(
    "carnical_fuligem",
    "Carniçal de Fuligem",
    "common",
    "brute",
    5,
    8,
    0,
    ("rend", "charge", "rend", "defend"),
    (
        ("rend", "Dilacerar", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        ("charge", "Arrancada", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    damage_taken_modifiers=(("burn", D("1.10")), ("bleed", D("0.90"))),
)

MOTH = Creature(
    "mariposa_brasa",
    "Mariposa de Brasa",
    "uncommon",
    "caster",
    6,
    9,
    0,
    ("incandescent_touch", "ash_flash", "incandescent_touch", "defend"),
    (
        ("incandescent_touch", "Toque Incandescente", D("0.80"), 0, D(0), 0, "burn", 1, False, 2),
        ("ash_flash", "Clarão de Cinzas", D("1.20"), 0, D(0), 0, None, 0, False, 3),
    ),
    damage_taken_modifiers=(("burn", D("0.90")),),
)

WIDOW = Creature(
    "viuva_fuligem",
    "Viúva da Fuligem",
    "elite",
    "controller",
    6,
    7,
    0,
    ("widow_sting", "soot_web", "widow_pounce", "widow_sting", "defend"),
    (
        ("widow_sting", "Picada da Viúva", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("soot_web", "Teia de Fuligem", D("0.75"), 0, D(0), 2, None, 0, False, 3, "agility"),
        ("widow_pounce", "Bote da Viúva", D("1.30"), 0, D(0), 0, None, 0, False, 3, None, D(10)),
    ),
)

CREATURE_CATALOG = (*CREATURES, SPIDER, CERVO, GHOUL, MOTH, WIDOW)

VIGIA = Creature(
    "vigia_rachado", "Vigia Rachado", "common", "armored", 7, 10, 0,
    ("golpe_pedra",),
    (
        ("golpe_pedra", "Golpe de Pedra", D("1.00"), 0, D(0), 0),
        ("guarda_rachada", "Guarda Rachada", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.70"), 2),
    ),
    ai_priority=("guarda_rachada",),
)
FACELESS_CUSTODIAN = Creature(
    "custodio_sem_rosto", "Custódio Sem Rosto", "uncommon", "controller", 8, 10, 0,
    ("marca_peso", "protecao_antiga", "impacto", "defend"),
    (
        ("marca_peso", "Marca do Peso", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
        ("protecao_antiga", "Proteção Antiga", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.80"), 2),
        ("impacto", "Impacto", D("1.20"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("protecao_antiga", "marca_peso", "impacto"),
)
SUNSET_CUSTODIAN = Creature(
    "custodio_poente", "Custódio do Poente", "elite", "armored", 9, 10, 0,
    ("golpe_custodio",),
    (
        ("golpe_custodio", "Golpe do Custódio", D("1.00"), 0, D(0), 0),
        ("guarda_poente", "Guarda do Poente", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2, True),
        ("marca_poente", "Marca do Poente", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("queda_poente", "Queda do Poente", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("marca_poente", "guarda_poente", "queda_poente"),
)
LAST_TRACE_GUARDIAN = Creature(
    "guardiao_ultimo_rastro",
    "Guardião do Último Rastro",
    "boss",
    "balanced",
    10,
    10,
    0,
    ("marca_rastro", "golpe_guardiao", "golpe_guardiao", "queda_travessia"),
    (
        ("golpe_guardiao", "Golpe da Última Trilha", D("1.00"), 0, D(0), 0),
        (
            "marca_rastro", "Marca do Rastro", D("0.90"), 0, D("0.10"), 2,
            None, 0, False, 3, "agility",
        ),
        (
            "queda_travessia", "Queda da Travessia", D("1.65"), 0, D(0), 0,
            None, 0, True, 4,
        ),
    ),
    ai_priority=("marca_rastro", "queda_travessia"),
)
VIGIA_PARTIDO = Creature(
    "vigia_partido",
    "Vigia Partido",
    "boss",
    "balanced",
    10,
    10,
    0,
    ("golpe_vigia",),
    (
        ("golpe_vigia", "Golpe do Vigia", D("1.00"), 0, D(0), 0),
        ("marca_sentinela", "Marca da Sentinela", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("egide_partida", "Égide Partida", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D("0.90"), 2, True, "self", None, None, 2),
        ("varredura_fraturada", "Varredura Fraturada", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents", D("0.70")),
        ("peso_ruina", "Peso da Ruína", D("1.35"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", D("0.70")),
        ("queda_ocaso", "Queda do Ocaso", D("1.85"), 0, D(0), 0, None, 0, True, 5, None, D(0), D(0), 0, False, "opponent", None, D("0.35")),
    ),
    ai_priority=("egide_partida", "marca_sentinela", "queda_ocaso", "varredura_fraturada", "peso_ruina", "golpe_vigia"),
)
PROFANADOR_CALCINADO = Creature(
    "profanador_calcinado", "Profanador Calcinado", "common", "balanced", 4, 7, 0,
    ("ferramenta_quebrada", "golpe_impuro", "ferramenta_quebrada"),
    (
        ("ferramenta_quebrada", "Ferramenta Quebrada", D("1.00"), 0, D(0), 0),
        ("golpe_impuro", "Golpe Impuro", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
    ),
    ai_priority=("golpe_impuro", "ferramenta_quebrada"),
)
GUARDIAO_LAPIDES = Creature(
    "guardiao_lapides", "Guardião das Lápides", "elite", "brute", 6, 7, 0,
    ("pancada_pedra", "lapide_partida", "pancada_pedra", "peso_mortos"),
    (
        ("pancada_pedra", "Pancada de Pedra", D("1.00"), 0, D(0), 0),
        ("lapide_partida", "Lápide Partida", D("0.85"), 0, D(0), 0, "bleed", 1, False, 2),
        ("peso_mortos", "Peso dos Mortos", D("1.65"), 0, D(0), 0, None, 0, True),
    ),
)
SEM_NOME = Creature(
    "sem_nome", "O Sem-Nome", "boss", "balanced", 7, 7, 0,
    ("golpe_lapide", "marca_apagada", "maos_esquecidos", "peso_sepulcro"),
    (
        ("golpe_lapide", "Golpe de Lápide", D("1.00"), 0, D(0), 0),
        ("marca_apagada", "Marca Apagada", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
        ("peso_sepulcro", "Peso do Sepulcro", D("1.70"), 0, D(0), 0, None, 0, True, None, None, D(0), D(0), 0, False, "opponent", D("0.70")),
        ("maos_esquecidos", "Mãos dos Esquecidos", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents", D("0.70")),
    ),
    ai_priority=("maos_esquecidos", "marca_apagada", "peso_sepulcro", "golpe_lapide"),
)
LAPIDE_SEM_NOME = Creature(
    "lapide_sem_nome", "Lápide sem Nome", "common", "balanced", 6, 6, 0, (), ()
)
CREATURE_CATALOG = (
    *CREATURE_CATALOG, VIGIA, FACELESS_CUSTODIAN, SUNSET_CUSTODIAN,
    LAST_TRACE_GUARDIAN, VIGIA_PARTIDO, PROFANADOR_CALCINADO, GUARDIAO_LAPIDES, SEM_NOME,
    LAPIDE_SEM_NOME,
)

VIGIA_INTEGRO = Creature(
    "vigia_integro", "Vigia Íntegro", "elite", "armored", 9, 9, 0,
    ("golpe_guarda", "marca_restricao", "queda_guarda", "egide_integra"),
    (
        ("golpe_guarda", "Golpe de Guarda", D("1.00"), 0, D(0), 0),
        ("egide_integra", "Égide Íntegra", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.80"), 2, True, "self"),
        ("marca_restricao", "Marca de Restrição", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
        ("queda_guarda", "Queda da Guarda", D("1.60"), 0, D(0), 0, None, 0, True),
    ),
    ai_priority=("egide_integra", "marca_restricao", "queda_guarda", "golpe_guarda"),
)
PRECEPTOR_RACHADO = Creature(
    "preceptor_rachado", "Preceptor Rachado", "elite", "controller", 9, 9, 0,
    ("restabelecer_conduto", "peso_ordem", "impacto_regulador"),
    (
        ("impacto_regulador", "Impacto Regulador", D("1.00"), 0, D(0), 0),
        ("peso_ordem", "Peso da Ordem", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "attack"),
        ("restabelecer_conduto", "Restabelecer Conduto", D(0), 0, D(0), 0, None, 0, False, None, None, D(0), D(0), 0, False, "self", None, None, 1, ("conductor_1", "conductor_2"), ("conductor_1", "conductor_2"), D("0.50")),
    ),
    ai_priority=("restabelecer_conduto", "peso_ordem", "impacto_regulador"),
)
GUARD_CONDUCTOR = Creature(
    "condutor_guarda", "Condutor de Guarda", "common", "balanced", 9, 9, 0, (), ()
)
SEAL_GUARD_FRAGMENT = Creature(
    "fragmento_guarda", "Fragmento de Guarda", "common", "balanced", 9, 60, 0, (), ()
)
CUSTODIO_PRIMEIRO_SELO = Creature(
    "custodio_primeiro_selo", "Custódio do Primeiro Selo", "boss", "armored", 10, 10, 0,
    ("golpe_regulador", "marca_contencao", "egide_selo", "varredura_selo", "ruptura_selo"),
    (
        ("golpe_regulador", "Golpe Regulador", D("1.00"), 0, D(0), 0),
        ("marca_contencao", "Marca de Contenção", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
        ("egide_selo", "Égide do Selo", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D(0), 0, False, "self", None, None, 2, (), (), D("0.50"), D("0.08")),
        ("varredura_selo", "Varredura do Selo", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
        ("ruptura_selo", "Ruptura do Primeiro Selo", D("1.75"), 0, D(0), 0, None, 0, True, 5, None, D(0), D(0), 0, False, "opponent", None, D("0.35")),
    ),
    ai_priority=("egide_selo", "marca_contencao", "ruptura_selo", "varredura_selo", "golpe_regulador"),
)
CREATURE_CATALOG = (
    *CREATURE_CATALOG,
    VIGIA_INTEGRO,
    PRECEPTOR_RACHADO,
    GUARD_CONDUCTOR,
    SEAL_GUARD_FRAGMENT,
    CUSTODIO_PRIMEIRO_SELO,
)

VDE_MOSS_WOLF = Creature(
    "lobo_musgoso", "Lobo Musgoso", "common", "predator", 11, 14, 34,
    ("mordida_umida", "rasgo_alcateia", "bote_raizes"),
    (
        ("mordida_umida", "Mordida Úmida", D("1.00"), 0, D(0), 0),
        ("rasgo_alcateia", "Rasgo da Alcateia", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        ("bote_raizes", "Bote entre Raízes", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("rasgo_alcateia", "bote_raizes"),
)
VDE_VALLEY_CROW = Creature(
    "gralha_vale", "Gralha do Vale", "common", "predator", 11, 14, 33,
    ("bicada_escura", "rasante_vale", "assedio"),
    (
        ("bicada_escura", "Bicada Escura", D("0.95"), 0, D(0), 0),
        ("rasante_vale", "Rasante do Vale", D("1.05"), 0, D(0), 0, None, 0, False, 2),
        (
            "assedio", "Assédio", D("0.80"), 0, D(0), 0, None, 0, False, 3,
            None, D(0), D(0), 0, False, "opponent", None, None, None, (), (),
            D("0.50"), D(0), D(0), D(0), D("0.10"), D("0.40"), 0,
        ),
    ),
    ai_priority=("assedio",),
)
VDE_TANGLED_PILGRIM = Creature(
    "peregrino_enredado", "Peregrino Enredado", "uncommon", "balanced", 11, 15, 30,
    ("golpe_enredado", "laco_improvisado", "defend"),
    (
        ("golpe_enredado", "Golpe Enredado", D("1.00"), 0, D(0), 0),
        ("laco_improvisado", "Laço Improvisado", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
    ),
    ai_priority=("laco_improvisado",),
)
VDE_VINE_SPIDER = Creature(
    "aranha_cipo", "Aranha de Cipó", "common", "controller", 13, 16, 0,
    ("picada_cipo", "fio_tenso", "mordida_cipo"),
    (
        ("picada_cipo", "Picada de Cipó", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("fio_tenso", "Fio Tenso", D("0.75"), 0, D("0.12"), 2, None, 0, False, 3, "agility"),
        ("mordida_cipo", "Mordida", D("0.95"), 0, D(0), 0),
    ),
    damage_taken_modifiers=(("burn", D("1.10")), ("poison", D("0.90"))),
)
VDE_KNOT_DEER = Creature(
    "cervo_no", "Cervo do Nó", "common", "brute", 13, 17, 0,
    ("chifrada_nodosa", "pisoteio_no", "investida_galhos"),
    (
        ("chifrada_nodosa", "Chifrada Nodosa", D("1.05"), 0, D(0), 0),
        ("pisoteio_no", "Pisoteio", D("1.25"), 0, D(0), 0, None, 0, False, 3),
        ("investida_galhos", "Investida dos Galhos", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
)
VDE_FEROCIOUS_KNOT = Creature(
    "no_feroz", "Nó-Feroz", "elite", "predator", 13, 14, 0,
    ("mordida_feroz", "rasgo_raizes", "cacada_ferido", "salto_no"),
    (
        ("mordida_feroz", "Mordida Feroz", D("1.00"), 0, D(0), 0),
        ("rasgo_raizes", "Rasgo das Raízes", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        (
            "cacada_ferido", "Caçada do Ferido", D("1.30"), 0, D(0), 0,
            None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None,
            None, None, (), (), D("0.50"), D(0), D(0), D("0.10"), D(0),
            D("0.40"), 0,
        ),
        ("salto_no", "Salto do Nó", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("rasgo_raizes", "cacada_ferido", "salto_no"),
)
VDE_VINE_WIDOW = Creature(
    "viuva_cipos", "Viúva dos Cipós", "elite", "controller", 15, 17, 0,
    ("picada_viuva", "trama_cipos", "veneno_concentrado", "bote_suspenso"),
    (
        ("picada_viuva", "Picada da Viúva", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("trama_cipos", "Trama dos Cipós", D("0.75"), 0, D("0.15"), 2, None, 0, False, 3, "agility"),
        (
            "veneno_concentrado", "Veneno Concentrado", D("0.95"), 0, D(0),
            0, "poison", 1, False, 3, None, D(0), D(0), 0, False,
            "opponent", None, None, None, (), (), D("0.50"), D(0), D(0),
            D(0), D(0), D("0.40"), 1,
        ),
        ("bote_suspenso", "Bote Suspenso", D("1.55"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("picada_viuva", "trama_cipos", "veneno_concentrado", "bote_suspenso"),
)
VDE_TURF_LEECH = Creature(
    "sanguessuga_turfa", "Sanguessuga de Turfa", "common", "balanced", 15, 18, 0,
    ("mordida_lodosa", "succao", "inchar"),
    (
        ("mordida_lodosa", "Mordida Lodosa", D("0.95"), 0, D(0), 0),
        ("succao", "Sucção", D("0.85"), 0, D(0), 0, None, 0, False, 2, None, D(0), D(0), 0, False, "opponent", None, None, None, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"), 0, D("0.30")),
        ("inchar", "Inchar", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D(0), 0, False, "self", None, D("0.40"), None, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"), 0, D(0), D("0.55")),
    ),
    damage_taken_modifiers=(("burn", D("1.10")),),
)
VDE_WANDERING_BARK = Creature(
    "casca_errante", "Casca Errante", "uncommon", "armored", 15, 19, 0,
    ("braco_casca", "casca_fechada", "estilhaco_organico"),
    (
        ("braco_casca", "Braço de Casca", D("1.00"), 0, D(0), 0),
        ("casca_fechada", "Casca Fechada", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.85"), 2, True),
        ("estilhaco_organico", "Estilhaço Orgânico", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    damage_taken_modifiers=(("burn", D("1.10")), ("bleed", D("0.90"))),
)
VDE_GREEN_DUSK_MOTH = Creature(
    "mariposa_breu_verde", "Mariposa do Breu Verde", "common", "caster", 16, 19, 0,
    ("po_breu", "toque_verde", "clarao_noturno"),
    (
        ("po_breu", "Pó do Breu", D("0.75"), 0, D("0.08"), 2, None, 0, False, 3, "attack"),
        ("toque_verde", "Toque Verde", D("0.90"), 0, D(0), 0, "poison", 1, False, 2),
        ("clarao_noturno", "Clarão Noturno", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
)
VDE_ROOTED_WATCHER = Creature(
    "vigia_enraizado", "Vigia Enraizado", "uncommon", "armored", 18, 20, 0,
    ("golpe_enraizado", "egide_enredada", "marca_raizes", "peso_antigo"),
    (
        ("golpe_enraizado", "Golpe Enraizado", D("1.00"), 0, D(0), 0),
        ("egide_enredada", "Égide Enredada", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2, True),
        ("marca_raizes", "Marca das Raízes", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("peso_antigo", "Peso Antigo", D("1.60"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("egide_enredada", "marca_raizes", "peso_antigo"),
)
VDE_BARK_EXECUTIONER = Creature(
    "carrasco_casca", "Carrasco de Casca", "elite", "armored", 18, 20, 0,
    ("golpe_carrasco", "couraça_enrijecida", "fenda_casca", "queda_tronco"),
    (
        ("golpe_carrasco", "Golpe do Carrasco", D("1.05"), 0, D(0), 0),
        ("couraça_enrijecida", "Couraça Enrijecida", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("1.00"), 2, True),
        ("fenda_casca", "Fenda de Casca", D("1.35"), 0, D(0), 0, None, 0, False, 3),
        ("queda_tronco", "Queda do Tronco", D("1.80"), 0, D(0), 0, None, 0, True, 4),
    ),
    damage_taken_modifiers=(("burn", D("1.10")), ("bleed", D("0.90"))),
)
NARETH_MERIDIAN_HOUND = Creature(
    "galgo_meridiano", "Galgo do Meridiano", "common", "predator", 21, 24, 34,
    ("mordida_campo", "corte_passagem", "corrida_meridiano"),
    (
        ("mordida_campo", "Mordida de Campo", D("1.00"), 0, D(0), 0),
        ("corte_passagem", "Corte de Passagem", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        ("corrida_meridiano", "Corrida do Meridiano", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("corte_passagem", "corrida_meridiano"),
)
NARETH_MARKER_VULTURE = Creature(
    "abutre_marco", "Abutre de Marco", "common", "predator", 21, 24, 33,
    ("bicada_marco", "rasante_longo", "oportunismo_horizonte"),
    (
        ("bicada_marco", "Bicada de Marco", D("0.95"), 0, D(0), 0),
        ("rasante_longo", "Rasante Longo", D("1.05"), 0, D(0), 0, None, 0, False, 2),
        (
            "oportunismo_horizonte", "Oportunismo do Horizonte", D("0.80"), 0, D(0), 0,
            None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None, None, None,
            (), (), D("0.50"), D(0), D(0), D(0), D("0.10"), D("0.40"),
        ),
    ),
    ai_priority=("oportunismo_horizonte", "rasante_longo"),
)
NARETH_DITCH_WANDERER = Creature(
    "errante_valas", "Errante das Valas", "uncommon", "balanced", 21, 25, 30,
    ("golpe_vala", "gancho_improvisado", "golpe_vala"),
    (
        ("golpe_vala", "Golpe de Vala", D("1.00"), 0, D(0), 0),
        ("gancho_improvisado", "Gancho Improvisado", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
    ),
    ai_priority=("gancho_improvisado",),
)
NARETH_HORIZON_ALPHA = Creature(
    "alfa_horizonte", "Alfa do Horizonte", "elite", "predator", 23, 24, 3,
    ("mordida_alfa", "rasgo_travessia", "cacada_campo", "corrida_sem_abrigo"),
    (
        ("mordida_alfa", "Mordida do Alfa", D("1.00"), 0, D(0), 0),
        ("rasgo_travessia", "Rasgo de Travessia", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        (
            "cacada_campo", "Caçada de Campo", D("1.30"), 0, D(0), 0, None, 0, False, 3,
            None, D(0), D(0), 0, False, "opponent", None, None, None, (), (), D("0.50"),
            D(0), D(0), D("0.10"),
        ),
        ("corrida_sem_abrigo", "Corrida sem Abrigo", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("rasgo_travessia", "corrida_sem_abrigo"),
)
NARETH_CHANNEL_SCARAB = Creature(
    "escaravelho_canal", "Escaravelho de Canal", "common", "controller", 23, 26, 21,
    ("mandibula_canal", "secrecao_irritante", "carapaca_baixa"),
    (
        ("mandibula_canal", "Mandíbula de Canal", D("0.95"), 0, D(0), 0),
        ("secrecao_irritante", "Secreção Irritante", D("0.80"), 0, D("0.12"), 2, None, 0, False, 3, "agility"),
        ("carapaca_baixa", "Carapaça Baixa", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D("0.70"), 2, True),
    ),
    ai_priority=("secrecao_irritante", "carapaca_baixa"),
)
NARETH_HORIZON_DEER = Creature(
    "cervo_horizonte", "Cervo do Horizonte", "common", "brute", 23, 27, 23,
    ("chifrada_horizonte", "pisoteio_campo", "carga_longa"),
    (
        ("chifrada_horizonte", "Chifrada do Horizonte", D("1.05"), 0, D(0), 0),
        ("pisoteio_campo", "Pisoteio de Campo", D("1.25"), 0, D(0), 0, None, 0, False, 3),
        ("carga_longa", "Carga Longa", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
)
NARETH_FIELD_SERPENT = Creature(
    "serpe_campinas", "Serpe das Campinas", "common", "controller", 25, 28, 22,
    ("bote_seco", "veneno_campinas", "enroscar_palha"),
    (
        ("bote_seco", "Bote Seco", D("0.95"), 0, D(0), 0),
        ("veneno_campinas", "Veneno de Campinas", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("enroscar_palha", "Enroscar na Palha", D("0.75"), 0, D("0.12"), 2, None, 0, False, 3, "agility"),
    ),
    ai_priority=("veneno_campinas", "enroscar_palha"),
)
NARETH_INVERTED_HUSK = Creature(
    "casco_invertido", "Casco Invertido", "uncommon", "armored", 25, 29, 18,
    ("impacto_casco", "placas_contrarias", "reverso_peso"),
    (
        ("impacto_casco", "Impacto de Casco", D("1.00"), 0, D(0), 0),
        ("placas_contrarias", "Placas Contrárias", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.85"), 2, True),
        ("reverso_peso", "Reverso de Peso", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    damage_taken_modifiers=(("bleed", D("0.90")),),
)
NARETH_AXIS_MOTH = Creature(
    "mariposa_eixo", "Mariposa do Eixo", "common", "caster", 26, 29, 15,
    ("po_eixo", "toque_palida", "clarao_referencia"),
    (
        ("po_eixo", "Pó de Eixo", D("0.75"), 0, D("0.08"), 2, None, 0, False, 3, "attack"),
        ("toque_palida", "Toque Pálido", D("0.90"), 0, D(0), 0),
        ("clarao_referencia", "Clarão de Referência", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
)
NARETH_MERIDIAN_WATCHER = Creature(
    "vigia_meridiano", "Vigia do Meridiano", "uncommon", "armored", 28, 30, 32,
    ("golpe_medicao", "egide_meridiano", "marca_referencia", "prumo_descendente"),
    (
        ("golpe_medicao", "Golpe de Medição", D("1.00"), 0, D(0), 0),
        ("egide_meridiano", "Égide do Meridiano", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2, True),
        ("marca_referencia", "Marca de Referência", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("prumo_descendente", "Prumo Descendente", D("1.60"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("egide_meridiano", "marca_referencia", "prumo_descendente"),
)
NARETH_AXIS_SERPENT = Creature(
    "serpe_eixo", "Serpe do Eixo", "elite", "controller", 25, 27, 2,
    ("picada_eixo", "laco_escamas", "veneno_concentrado", "bote_marco"),
    (
        ("picada_eixo", "Picada do Eixo", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("laco_escamas", "Laço de Escamas", D("0.75"), 0, D("0.15"), 2, None, 0, False, 3, "agility"),
        ("veneno_concentrado", "Veneno Concentrado", D("0.95"), 0, D(0), 0, "poison", 1, False, 3, None, D(0), D(0), 0, False, "opponent", None, None, None, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"), 1),
        ("bote_marco", "Bote do Marco", D("1.55"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("picada_eixo", "laco_escamas", "veneno_concentrado", "bote_marco"),
)
NARETH_INVERTED_CUSTODIAN = Creature(
    "custodio_invertido", "Custódio Invertido", "elite", "armored", 28, 30, 2,
    ("golpe_invertido", "couraça_referencia", "corte_eixo", "queda_prumo"),
    (
        ("golpe_invertido", "Golpe Invertido", D("1.05"), 0, D(0), 0),
        ("couraça_referencia", "Couraça de Referência", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("1.00"), 2, True),
        ("corte_eixo", "Corte de Eixo", D("1.35"), 0, D(0), 0, None, 0, False, 3),
        ("queda_prumo", "Queda do Prumo", D("1.80"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("couraça_referencia", "corte_eixo", "queda_prumo"),
)
NARETH_CUSTODIO_SEM_NORTE = Creature(
    "custodio_sem_norte",
    "Custódio sem Norte",
    "boss",
    "controller",
    30,
    30,
    0,
    ("golpe_marco", "rota_negada", "correcao_cega", "queda_sem_norte"),
    (
        ("golpe_marco", "Golpe de Marco", D("1.00"), 0, D(0), 0),
        ("rota_negada", "Rota Negada", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "agility"),
        ("correcao_cega", "Correção Cega", D("1.25"), 0, D(0), 0, None, 0, False, 3),
        ("queda_sem_norte", "Queda sem Norte", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("queda_sem_norte", "rota_negada", "correcao_cega", "golpe_marco"),
)
NARETH_ARCONTE_INVERTIDO = Creature(
    "arconte_invertido",
    "Arconte Invertido",
    "boss",
    "armored",
    30,
    30,
    0,
    ("golpe_diretiva",),
    (("golpe_diretiva", "Golpe de Diretiva", D("1.00"), 0, D(0), 0),),
)
VARZEAS_SALMOURA_HOUND = Creature(
    "cao_salmoura", "Cão de Salmoura", "common", "predator", 31, 34, 34,
    ("mordida_varzea", "rasgo_salgado", "investida_dique"),
    (
        ("mordida_varzea", "Mordida de Várzea", D("1.00"), 0, D(0), 0),
        ("rasgo_salgado", "Rasgo Salgado", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        ("investida_dique", "Investida de Dique", D("1.30"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("rasgo_salgado", "investida_dique"),
)
VARZEAS_IRON_HERON = Creature(
    "garca_ferruginosa", "Garça Ferruginosa", "common", "predator", 31, 34, 33,
    ("bicada_agua_rasa", "passo_longo", "perfuracao_oportunista"),
    (
        ("bicada_agua_rasa", "Bicada de Água Rasa", D("0.95"), 0, D(0), 0),
        ("passo_longo", "Passo Longo", D("1.05"), 0, D(0), 0, None, 0, False, 2),
        (
            "perfuracao_oportunista", "Perfuração Oportunista", D("0.85"), 0, D(0), 0,
            None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None,
            None, None, (), (), D("0.50"), D(0), D(0), D(0), D("0.10"), D("0.40"),
        ),
    ),
    ai_priority=("perfuracao_oportunista", "passo_longo"),
)
VARZEAS_CRIMSON_BEARER = Creature(
    "portador_rubro", "Portador Rubro", "uncommon", "balanced", 31, 35, 30,
    ("golpe_contencao", "ferramenta_quebrada", "persistencia_residual"),
    (
        ("golpe_contencao", "Golpe de Contenção", D("1.00"), 0, D(0), 0),
        (
            "ferramenta_quebrada", "Ferramenta Quebrada", D("0.90"), 0, D("0.10"), 2,
            None, 0, False, 3, "defense",
        ),
        (
            "persistencia_residual", "Persistência Residual", D(0), 0, D(0), 0,
            None, 0, False, 5, None, D(0), D(0), 0, False, "self", None,
            D("0.35"), 1, (), (), D("0.50"), D(0), D(0), D(0), D(0), D(0),
            D("0.40"), 0, D(0), D("0.04"),
        ),
    ),
    ai_priority=("persistencia_residual", "ferramenta_quebrada"),
)
VARZEAS_BRINE_ALPHA = Creature(
    "alfa_salmoura", "Alfa de Salmoura", "elite", "predator", 33, 34, 3,
    ("mordida_alfa_salmoura", "rasgo_salmoura", "cacada_margem", "corrida_dique"),
    (
        ("mordida_alfa_salmoura", "Mordida do Alfa", D("1.00"), 0, D(0), 0),
        ("rasgo_salmoura", "Rasgo de Salmoura", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
        (
            "cacada_margem", "Caçada de Margem", D("1.35"), 0, D(0), 0,
            None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None,
            None, None, (), (), D("0.50"), D(0), D(0), D("0.10"),
        ),
        ("corrida_dique", "Corrida pelo Dique", D("1.75"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("rasgo_salmoura", "cacada_margem", "corrida_dique"),
)
VARZEAS_REED_SPIDER = Creature(
    "aranha_junco", "Aranha de Junco", "common", "controller", 33, 36, 20,
    ("picada_junco", "fio_entre_hastes", "salto_margem"),
    (
        ("picada_junco", "Picada de Junco", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("fio_entre_hastes", "Fio entre Hastes", D("0.75"), 0, D("0.12"), 2, None, 0, False, 3, "agility"),
        ("salto_margem", "Salto de Margem", D("1.15"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("picada_junco", "fio_entre_hastes", "salto_margem"),
)
VARZEAS_RUST_DEER = Creature(
    "cervo_ferrugem", "Cervo Ferrugem", "common", "brute", 33, 37, 24,
    ("chifrada_ferruginosa", "pisoteio_brejo", "carga_junco"),
    (
        ("chifrada_ferruginosa", "Chifrada Ferruginosa", D("1.05"), 0, D(0), 0),
        ("pisoteio_brejo", "Pisoteio de Brejo", D("1.25"), 0, D(0), 0, None, 0, False, 3),
        ("carga_junco", "Carga de Junco", D("1.75"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("carga_junco", "pisoteio_brejo"),
)
VARZEAS_CRIMSON_WIDOW = Creature(
    "viuva_rubra", "Viúva Rubra", "elite", "controller", 35, 37, 3,
    ("picada_rubra", "teia_junco", "toxina_concentrada", "salto_agua"),
    (
        ("picada_rubra", "Picada Rubra", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("teia_junco", "Teia de Junco", D("0.75"), 0, D("0.15"), 2, None, 0, False, 3, "agility"),
        ("toxina_concentrada", "Toxina Concentrada", D("0.95"), 0, D(0), 0, "poison", 0, False, 3, None, D(0), D(0), 0, False, "opponent", None, None, None, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"), 1),
        ("salto_agua", "Salto sobre a Água", D("1.60"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("picada_rubra", "teia_junco", "toxina_concentrada", "salto_agua"),
)
VARZEAS_MARSH_LAMPREY = Creature(
    "lampreia_varzea", "Lampreia de Várzea", "common", "balanced", 35, 38, 20,
    ("mordida_circular", "drenagem_lama", "bote_margem"),
    (
        ("mordida_circular", "Mordida Circular", D("0.95"), 0, D(0), 0),
        (
            "drenagem_lama", "Drenagem de Lama", D("0.95"), 0, D(0), 0,
            None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None,
            None, None, (), (), D("0.50"), D(0), D(0), D(0), D(0),
            D("0.40"), 0, D("0.30"), D(0), D(0), D("0.04"),
        ),
        ("bote_margem", "Bote de Margem", D("1.30"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("drenagem_lama", "bote_margem"),
)
VARZEAS_GARDEN_GRAFT = Creature(
    "enxerto_horto", "Enxerto de Horto", "uncommon", "armored", 35, 39, 18,
    ("pancada_fibrosa", "casca_suporte", "regeneracao_residual"),
    (
        ("pancada_fibrosa", "Pancada Fibrosa", D("0.95"), 0, D(0), 0),
        ("casca_suporte", "Casca de Suporte", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2, True),
        (
            "regeneracao_residual", "Regeneração Residual", D(0), 0, D(0), 0,
            None, 0, False, 4, None, D(0), D(0), 0, False, "self", None,
            None, 2, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"),
            0, D(0), D(0), D("0.04"),
        ),
    ),
    ai_priority=("casca_suporte", "regeneracao_residual"),
)
VARZEAS_SERUM_MOTH = Creature(
    "mariposa_soro", "Mariposa de Soro", "common", "caster", 36, 39, 16,
    ("escama_iritante", "toque_palida", "clarao_vidro"),
    (
        ("escama_iritante", "Escama Irritante", D("0.75"), 0, D("0.10"), 2, None, 0, False, 3, "attack"),
        ("toque_palida", "Toque Pálido", D("0.90"), 0, D(0), 0),
        ("clarao_vidro", "Clarão de Vidro", D("1.25"), 0, D(0), 0, None, 0, False, 3),
    ),
    ai_priority=("escama_iritante", "clarao_vidro"),
)
VARZEAS_HEMATIC_COLLECTOR = Creature(
    "coletor_hematico", "Coletor Hemático", "elite", "armored", 38, 40, 3,
    ("impacto_coleta", "reservatorio_blindado", "marca_extracao", "extracao_forcada"),
    (
        ("impacto_coleta", "Impacto de Coleta", D("1.05"), 0, D(0), 0),
        ("reservatorio_blindado", "Reservatório Blindado", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("1.00"), 2),
        ("marca_extracao", "Marca de Extração", D("0.85"), 0, D("0.12"), 2, None, 0, False, 3, "defense"),
        ("extracao_forcada", "Extração Forçada", D("1.80"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("reservatorio_blindado", "marca_extracao", "extracao_forcada"),
)
VARZEAS_HEMARIS_WARDEN = Creature(
    "vigia_hemaris", "Vigia Hemaris", "uncommon", "armored", 38, 40, 33,
    ("golpe_contencao", "placa_lavavel", "marca_triagem", "queda_suporte"),
    (
        ("golpe_contencao", "Golpe de Contenção", D("1.00"), 0, D(0), 0),
        ("placa_lavavel", "Placa Lavável", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.95"), 2),
        ("marca_triagem", "Marca de Triagem", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("queda_suporte", "Queda de Suporte", D("1.65"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("placa_lavavel", "marca_triagem", "queda_suporte"),
)
VARZEAS_DUNGEON_TRANSFUSED = Creature(
    "transfundido", "Transfundido", "common", "balanced", 37, 37, 0,
    ("golpe_assimetrico", "ferida_reaberta"),
    (
        ("golpe_assimetrico", "Golpe Assimétrico", D("1.00"), 0, D(0), 0),
        ("ferida_reaberta", "Ferida Reaberta", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
    ),
)
VARZEAS_DUNGEON_CURATOR = Creature(
    "curador_vazio", "Curador Vazio", "elite", "controller", 37, 37, 0,
    ("braco_suporte", "cauterizacao_inadequada", "placa_procedimento", "intervencao_brusca"),
    (
        ("braco_suporte", "Braço de Suporte", D("1.00"), 0, D(0), 0),
        ("cauterizacao_inadequada", "Cauterização Inadequada", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "attack"),
        ("placa_procedimento", "Placa de Procedimento", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("1.00"), 2, True),
        ("intervencao_brusca", "Intervenção Brusca", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("placa_procedimento", "cauterizacao_inadequada", "intervencao_brusca"),
)
VARZEAS_DUNGEON_PERSISTENT = Creature(
    "o_persistente", "O Persistente", "boss", "balanced", 37, 37, 0,
    ("golpe_mantido", "sutura_forcada", "protocolo_continuidade", "manutencao_repetida", "intervencao_final"),
    (
        ("golpe_mantido", "Golpe Mantido", D("1.00"), 0, D(0), 0),
        ("sutura_forcada", "Sutura Forçada", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("protocolo_continuidade", "Protocolo de Continuidade", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D(0), 2, True, "self", None, None, None, (), (), D("0.50"), D("0.08")),
        ("manutencao_repetida", "Manutenção Repetida", D(0), 0, D(0), 0, None, 0, False, 5, None, D(0), D(0), 0, False, "self", None, D("0.65"), 2, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.40"), 0, D(0), D(0), D("0.05")),
        ("intervencao_final", "Intervenção Final", D("1.75"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("intervencao_final", "manutencao_repetida", "protocolo_continuidade", "sutura_forcada"),
)
VARZEAS_DUNGEON_CONDUCTOR = Creature(
    "condutor_rubro", "Condutor Rubro", "elite", "armored", 40, 40, 0,
    ("impacto_valvula", "linha_pressurizada", "descarga_fluxo", "fecho_seguranca"),
    (
        ("impacto_valvula", "Impacto de Válvula", D("1.05"), 0, D(0), 0),
        ("linha_pressurizada", "Linha Pressurizada", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.95"), 2, True),
        ("descarga_fluxo", "Descarga de Fluxo", D("1.30"), 0, D(0), 0, None, 0, False, 3),
        ("fecho_seguranca", "Fecho de Segurança", D("1.75"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("linha_pressurizada", "fecho_seguranca", "descarga_fluxo"),
)
VARZEAS_DUNGEON_EXECUTOR = Creature(
    "executor_hemaris", "Executor de Hemaris", "elite", "brute", 40, 40, 0,
    ("golpe_contencao_executor", "fixar_incidente", "resposta_emergencia", "imobilizacao_pesada"),
    (
        ("golpe_contencao_executor", "Golpe de Contenção", D("1.10"), 0, D(0), 0),
        ("fixar_incidente", "Fixar Incidente", D("0.90"), 0, D("0.15"), 2, None, 0, False, 3, "agility"),
        ("resposta_emergencia", "Resposta de Emergência", D("1.40"), 0, D(0), 0, None, 0, False, 3),
        ("imobilizacao_pesada", "Imobilização Pesada", D("1.80"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("imobilizacao_pesada", "fixar_incidente", "resposta_emergencia"),
)
VARZEAS_DUNGEON_TRANSFER_HEART = Creature(
    "coracao_transferencia", "Coração de Transferência", "boss", "controller", 40, 40, 0,
    ("pulso_bomba", "pressao_linha", "linha_aberta", "linha_fechada", "transferencia_final"),
    (
        ("pulso_bomba", "Pulso de Bomba", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
        ("pressao_linha", "Pressão de Linha", D("1.00"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        ("linha_aberta", "Linha Aberta", D(0), 0, D(0), 0, None, 0, False, 5, None, D(0), D(0), 0, False, "self"),
        ("linha_fechada", "Linha Fechada", D(0), 0, D(0), 0, None, 0, False, 5, None, D(0), D(0), 2, True, "self", None, None, None, (), (), D("0.50"), D("0.08")),
        ("transferencia_final", "Transferência Final", D("1.10"), 0, D(0), 0, None, 0, True, 5, None, D(0), D(0), 0, False, "all_opponents"),
    ),
    ai_priority=("transferencia_final", "linha_fechada", "linha_aberta", "pressao_linha", "pulso_bomba"),
)
VARZEAS_DUNGEON_CREATURES = (
    VARZEAS_DUNGEON_TRANSFUSED,
    VARZEAS_DUNGEON_CURATOR,
    VARZEAS_DUNGEON_PERSISTENT,
    VARZEAS_DUNGEON_CONDUCTOR,
    VARZEAS_DUNGEON_EXECUTOR,
    VARZEAS_DUNGEON_TRANSFER_HEART,
)
VARZEAS_CREATURES = (
    VARZEAS_SALMOURA_HOUND,
    VARZEAS_IRON_HERON,
    VARZEAS_CRIMSON_BEARER,
    VARZEAS_BRINE_ALPHA,
    VARZEAS_REED_SPIDER,
    VARZEAS_RUST_DEER,
    VARZEAS_CRIMSON_WIDOW,
    VARZEAS_MARSH_LAMPREY,
    VARZEAS_GARDEN_GRAFT,
    VARZEAS_SERUM_MOTH,
    VARZEAS_HEMATIC_COLLECTOR,
    VARZEAS_HEMARIS_WARDEN,
)

# Campaign bosses are globally lookupable for Bestiário, but never enter a
# regional Hunt, Round, or Explore pool.
VARZEAS_CAMPAIGN_BOSSES = (
    Creature(
        "matriz_rubra", "Matriz Rubra", "boss", "controller", 40, 40, 0,
        (), (),
    ),
    Creature(
        "custodio_quarentena", "Custódio de Quarentena", "boss", "controller", 40, 40, 0,
        (), (),
    ),
)

NARETH_CREATURES = (
    NARETH_MERIDIAN_HOUND,
    NARETH_MARKER_VULTURE,
    NARETH_DITCH_WANDERER,
    NARETH_CHANNEL_SCARAB,
    NARETH_HORIZON_DEER,
    NARETH_FIELD_SERPENT,
    NARETH_INVERTED_HUSK,
    NARETH_AXIS_MOTH,
    NARETH_MERIDIAN_WATCHER,
    NARETH_HORIZON_ALPHA,
    NARETH_AXIS_SERPENT,
    NARETH_INVERTED_CUSTODIAN,
)
NARETH_CAMPAIGN_BOSSES = (NARETH_CUSTODIO_SEM_NORTE, NARETH_ARCONTE_INVERTIDO)
NARETH_DUNGEON_BESTIARY_CREATURES = (
    Creature(
        "escavador_eixo",
        "Escavador do Eixo",
        "elite",
        "armored",
        26,
        26,
        0,
        ("pancada_escavacao", "travar_trilho", "corte_canal", "broca_servico"),
        (
            ("pancada_escavacao", "Pancada de Escavação", D("1.05"), 0, D(0), 0),
            (
                "travar_trilho", "Travar Trilho", D(0), 0, D(0), 0, None, 0,
                False, 3, None, D(0), D("0.85"), 2, True,
            ),
            ("corte_canal", "Corte de Canal", D("1.30"), 0, D(0), 0, None, 0, False, 3),
            ("broca_servico", "Broca de Serviço", D("1.75"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("travar_trilho", "corte_canal", "broca_servico"),
    ),
    Creature(
        "o_que_retorna",
        "O Que Retorna",
        "boss",
        "brute",
        27,
        27,
        0,
        (
            "impacto_recorrente", "rastro_repetido", "curva_retorno",
            "casco_ciclo", "colisao_recorrente",
        ),
        (
            ("impacto_recorrente", "Impacto Recorrente", D("1.00"), 0, D(0), 0),
            (
                "rastro_repetido", "Rastro Repetido", D("0.85"), 0,
                D("0.10"), 2, None, 0, False, 3, "defense",
            ),
            (
                "curva_retorno", "Curva de Retorno", D("0.80"), 0, D(0), 0,
                None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents",
            ),
            (
                "casco_ciclo", "Casco de Ciclo", D(0), 0, D(0), 0,
                None, 0, False, 4, None, D(0), D(0), 2, True, "opponent",
                None, None, 2, (), (), D("0.50"), D("0.08"),
            ),
            (
                "colisao_recorrente", "Colisão Recorrente", D("1.75"), 0,
                D(0), 0, None, 0, True, 4,
            ),
        ),
        ai_priority=(
            "colisao_recorrente", "casco_ciclo", "rastro_repetido",
            "curva_retorno", "impacto_recorrente",
        ),
    ),
    Creature(
        "custodio_meridiano",
        "Custódio do Meridiano",
        "elite",
        "armored",
        29,
        29,
        0,
        ("impacto_calibracao", "travar_referencia", "ajuste_forcado", "queda_prumo"),
        (
            ("impacto_calibracao", "Impacto de Calibração", D("1.00"), 0, D(0), 0),
            (
                "travar_referencia", "Travar Referência", D(0), 0, D(0), 0,
                None, 0, False, 3, None, D(0), D("0.90"), 2, True,
            ),
            (
                "ajuste_forcado", "Ajuste Forçado", D("0.85"), 0,
                D("0.12"), 2, None, 0, False, 3, "agility",
            ),
            ("queda_prumo", "Queda do Prumo", D("1.70"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("travar_referencia", "ajuste_forcado", "queda_prumo"),
    ),
    Creature(
        "preceptor_eixo",
        "Preceptor do Eixo",
        "elite",
        "caster",
        29,
        29,
        0,
        ("pulso_eixo", "desvio_medido", "recalibrar_baliza"),
        (
            ("pulso_eixo", "Pulso do Eixo", D("1.00"), 0, D(0), 0),
            (
                "desvio_medido", "Desvio Medido", D("0.80"), 0,
                D("0.10"), 2, None, 0, False, 3, "attack",
            ),
            (
                "recalibrar_baliza", "Recalibrar Baliza", D(0), 0, D(0), 0,
                None, 0, False, 0, None, D(0), D(0), 0, False, "opponent",
                None, None, 1,
                ("calibration_1", "calibration_2", "calibration_3", "calibration_4"),
                ("calibration_1", "calibration_2", "calibration_3", "calibration_4"),
                D("0.50"),
            ),
        ),
        ai_priority=("recalibrar_baliza", "desvio_medido", "pulso_eixo"),
    ),
    Creature(
        "guardiao_referencia",
        "Guardião da Referência",
        "boss",
        "armored",
        30,
        30,
        0,
        (
            "impacto_referencia", "linha_correcao", "ancora_local",
            "varredura_eixo", "referencia_absoluta",
        ),
        (
            ("impacto_referencia", "Impacto de Referência", D("1.00"), 0, D(0), 0),
            (
                "linha_correcao", "Linha de Correção", D("0.90"), 0,
                D("0.10"), 2, None, 0, False, 3, "defense",
            ),
            (
                "ancora_local", "Âncora Local", D(0), 0, D(0), 0,
                None, 0, False, 4, None, D(0), D(0), 2, True, "opponent",
                None, None, 2, (), (), D("0.50"), D("0.08"),
            ),
            (
                "varredura_eixo", "Varredura do Eixo", D("0.85"), 0,
                D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False,
                "all_opponents",
            ),
            (
                "referencia_absoluta", "Referência Absoluta", D("1.80"), 0,
                D(0), 0, None, 0, True, 5,
            ),
        ),
        ai_priority=(
            "referencia_absoluta", "ancora_local", "varredura_eixo",
            "linha_correcao", "impacto_referencia",
        ),
    ),
)

VDE_MATRIARCH = Creature(
    "matriarca_raizes",
    "Matriarca das Raízes",
    "boss",
    "brute",
    20,
    20,
    0,
    (
        "golpe_matriarca",
        "raiz_constritiva",
        "seiva_corrompida",
        "chicote_radicular",
    ),
    (
        ("golpe_matriarca", "Golpe da Matriarca", D("1.00"), 0, D(0), 0),
        (
            "raiz_constritiva",
            "Raiz Constritiva",
            D("0.90"),
            0,
            D("0.10"),
            2,
            None,
            0,
            False,
            3,
            "agility",
        ),
        (
            "seiva_corrompida",
            "Seiva Corrompida",
            D("0.80"),
            0,
            D(0),
            0,
            "poison",
            1,
            False,
            3,
        ),
        (
            "chicote_radicular",
            "Chicote Radicular",
            D("1.30"),
            0,
            D(0),
            0,
            None,
            0,
            False,
            3,
        ),
    ),
    ai_priority=(
        "raiz_constritiva",
        "seiva_corrompida",
        "chicote_radicular",
        "golpe_matriarca",
    ),
)

# Masmorra A — creature entries are registered in the shared Bestiário
# catalog, but are not part of the world-open Vales creature contract/pools.
VDE_PIT_WEAVER = Creature(
    "tecela_fosso",
    "Tecelã do Fosso",
    "elite",
    "controller",
    16,
    16,
    0,
    ("picada_profunda", "fio_arrasto", "casulo_breve", "queda_tecela"),
    (
        ("picada_profunda", "Picada Profunda", D("0.85"), 0, D(0), 0, "poison", 1, False, 2),
        ("fio_arrasto", "Fio de Arrasto", D("0.80"), 0, D("0.15"), 2, None, 0, False, 3, "agility"),
        ("casulo_breve", "Casulo Breve", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D("0.75"), 2, True),
        ("queda_tecela", "Queda da Tecelã", D("1.65"), 0, D(0), 0, None, 0, True, 4),
    ),
)
VDE_PIT_HANGER = Creature(
    "o_que_pende",
    "O Que Pende",
    "boss",
    "controller",
    17,
    17,
    0,
    ("garra_suspensa", "laco_fosso", "seiva_escura", "varredura_cordas", "despencar"),
    (
        ("garra_suspensa", "Garra Suspensa", D("1.00"), 0, D(0), 0),
        ("laco_fosso", "Laço do Fosso", D("0.90"), 0, D("0.12"), 2, None, 0, False, 3, "agility"),
        ("seiva_escura", "Seiva Escura", D("0.80"), 0, D(0), 0, "poison", 1, False, 2),
        ("varredura_cordas", "Varredura das Cordas", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
        ("despencar", "Despencar", D("1.75"), 0, D(0), 0, None, 0, True, 4),
    ),
)
VDE_PULSING_NODE = Creature(
    "fosso_no_pulsante", "Nó Pulsante", "common", "balanced", 16, 16, 0, (), ()
)
VDE_HANGING_ROOT = Creature(
    "fosso_raiz_sustentacao", "Raiz de Sustentação", "common", "balanced", 17, 17, 0, (), ()
)

# Masmorra B — catalogued dungeon creatures do not enter open-world Vales pools.
VDE_TANGLED_CUSTODIAN = Creature(
    "custodio_enredado", "Custódio Enredado", "elite", "armored", 19, 19, 0,
    ("impacto_guarda", "egide_tomada", "marca_constritiva", "peso_no"),
    (
        ("impacto_guarda", "Impacto de Guarda", D("1.00"), 0, D(0), 0),
        ("egide_tomada", "Égide Tomada", D(0), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2, True, "self"),
        ("marca_constritiva", "Marca Constritiva", D("0.90"), 0, D("0.12"), 2, None, 0, False, 3, "defense"),
        ("peso_no", "Peso do Nó", D("1.70"), 0, D(0), 0, None, 0, True, 4),
    ),
    ai_priority=("egide_tomada", "marca_constritiva", "peso_no"),
)
VDE_ROOTED_PRELATE = Creature(
    "prelado_enraizado", "Prelado Enraizado", "elite", "controller", 19, 19, 0,
    ("golpe_liturgico", "seiva_restritiva", "restabelecer_raiz"),
    (
        ("golpe_liturgico", "Golpe Litúrgico", D("1.00"), 0, D(0), 0),
        ("seiva_restritiva", "Seiva Restritiva", D("0.80"), 0, D("0.10"), 2, None, 0, False, 3, "attack"),
        (
            "restabelecer_raiz", "Restabelecer Raiz", D(0), 0, D(0), 0, None, 0,
            False, None, None, D(0), D(0), 0, False, "self", None, None, 1,
            ("root_1", "root_2", "root_3", "root_4"),
            ("root_1", "root_2", "root_3", "root_4"), D("0.50"),
        ),
    ),
    ai_priority=("restabelecer_raiz", "seiva_restritiva"),
)
VDE_OLD_KNOT_GUARDIAN = Creature(
    "guardiao_no_antigo", "Guardião do Nó Antigo", "boss", "armored", 20, 20, 0,
    (
        "golpe_no", "marca_de_constricao", "egide_raizes", "varredura_enredada",
        "fechamento_no",
    ),
    (
        ("golpe_no", "Golpe do Nó", D("1.00"), 0, D(0), 0),
        ("marca_de_constricao", "Marca de Constrição", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
        (
            "egide_raizes", "Égide das Raízes", D(0), 0, D(0), 0, None, 0,
            False, 4, None, D(0), D(0), 2, True, "self", None, None, 2,
            (), (), D("0.50"), D("0.08"),
        ),
        ("varredura_enredada", "Varredura Enredada", D("0.85"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
        ("fechamento_no", "Fechamento do Nó", D("1.80"), 0, D(0), 0, None, 0, True),
    ),
    ai_priority=("fechamento_no", "egide_raizes", "varredura_enredada", "marca_de_constricao"),
)

# Mechanical targets are combatants, never Bestiário/catalog entities.
VDE_ROOT_CONTAINMENT = Creature(
    "vde_root_containment_mechanic", "Raiz de Contenção", "common", "balanced", 19, 19, 0, (), ()
)
VDE_RADICULAR_SEAL = Creature(
    "vde_radicular_seal_mechanic", "Selo Radicular", "common", "balanced", 20, 20, 0, (), ()
)

VDE_DUNGEON_CREATURES = (
    VDE_PIT_WEAVER,
    VDE_PIT_HANGER,
    VDE_TANGLED_CUSTODIAN,
    VDE_ROOTED_PRELATE,
    VDE_OLD_KNOT_GUARDIAN,
)

VDE_CREATURES = (
    VDE_MOSS_WOLF,
    VDE_VALLEY_CROW,
    VDE_TANGLED_PILGRIM,
    VDE_VINE_SPIDER,
    VDE_KNOT_DEER,
    VDE_FEROCIOUS_KNOT,
    VDE_VINE_WIDOW,
    VDE_TURF_LEECH,
    VDE_WANDERING_BARK,
    VDE_GREEN_DUSK_MOTH,
    VDE_ROOTED_WATCHER,
    VDE_BARK_EXECUTIONER,
)
CAMPAIGN_BOSS_CREATURES = (
    VDE_MATRIARCH,
    *NARETH_CAMPAIGN_BOSSES,
    *VARZEAS_CAMPAIGN_BOSSES,
    Creature(
        ALTOS_COLOSSO_CINEREO,
        "Colosso Cinéreo",
        "boss",
        "armored",
        50,
        50,
        0,
        (
            "golpe_contraforte",
            "marca_carga",
            "placa_sustentacao",
            "varredura_contrapeso",
            "carga_distribuida",
        ),
        (
            ("golpe_contraforte", "Golpe de Contraforte", D("1.00"), 0, D(0), 0),
            ("marca_carga", "Marca de Carga", D("0.90"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
            ("placa_sustentacao", "Placa de Sustentação", D(0), 0, D(0), 0, None, 0, False, 4, None, D(0), D(0), -1, True, "self", None, None, 2, (), (), D("0.50"), D("0.08")),
            ("varredura_contrapeso", "Varredura de Contrapeso", D("0.85"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
            ("carga_distribuida", "Carga Distribuída", D("1.80"), 0, D(0), 0, None, 0, True, 5, None, D(0), D(0), 0, False, "all_opponents"),
        ),
        ai_priority=(),
    ),
    Creature(
        ALTOS_CUSTODIO_ULTIMO_TURNO,
        "Custódio do Último Turno",
        "boss",
        "controller",
        50,
        50,
        0,
        (
            "golpe_rotina",
            "ordem_vencida",
            "fecho_protocolo",
            "ultimo_turno",
        ),
        (
            ("golpe_rotina", "Golpe de Rotina", D("1.00"), 0, D(0), 0),
            (
                "ordem_vencida",
                "Ordem Vencida",
                D("0.90"),
                0,
                D("0.10"),
                2,
                None,
                0,
                False,
                3,
                "agility",
            ),
            (
                "fecho_protocolo",
                "Fecho de Protocolo",
                D("1.25"),
                0,
                D(0),
                0,
                None,
                0,
                False,
                3,
            ),
            (
                "ultimo_turno",
                "Último Turno",
                D("1.75"),
                0,
                D(0),
                0,
                None,
                0,
                True,
                4,
            ),
        ),
        ai_priority=(),
    ),
)
CREATURE_CATALOG = (
    *CREATURE_CATALOG,
    *VDE_CREATURES,
    *VDE_DUNGEON_CREATURES,
    *VARZEAS_CREATURES,
    *VARZEAS_DUNGEON_CREATURES,
    *NARETH_CREATURES,
    *NARETH_DUNGEON_BESTIARY_CREATURES,
    *CAMPAIGN_BOSS_CREATURES,
    Creature(
        ALTOS_LOBO_ESCARPA, "Lobo de Escarpa", "common", "predator", 41, 44, 0,
        ("mordida_escarpa", "rasgo_cornija", "investida_ascendente"),
        (
            ("mordida_escarpa", "Mordida de Escarpa", D("1.00"), 0, D(0), 0),
            ("rasgo_cornija", "Rasgo de Cornija", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
            ("investida_ascendente", "Investida Ascendente", D("1.30"), 0, D(0), 0, None, 0, False, 3),
        ),
        ai_priority=("rasgo_cornija", "investida_ascendente"),
    ),
    Creature(
        ALTOS_ABUTRE_FULIGEM, "Abutre da Fuligem", "common", "predator", 41, 44, 0,
        ("bicada_fuligem", "rasante_corrente", "queda_oportunista"),
        (
            ("bicada_fuligem", "Bicada de Fuligem", D("0.95"), 0, D(0), 0),
            ("rasante_corrente", "Rasante de Corrente", D("1.10"), 0, D(0), 0, None, 0, False, 2),
            (
                "queda_oportunista", "Queda Oportunista", D("0.85"), 0, D(0), 0,
                None, 0, False, 3, None, D(0), D(0), 0, False, "opponent", None,
                None, None, (), (), D("0.50"), D(0), D(0), D(0), D(0), D("0.10"), D("0.40"),
            ),
        ),
        ai_priority=("queda_oportunista", "rasante_corrente"),
    ),
    Creature(
        ALTOS_ESCARAVELHO_BASALTO, "Escaravelho de Basalto", "common", "armored", 41, 45, 0,
        ("impacto_carapaca", "casco_basalto", "tranco_pedreira"),
        (
            ("impacto_carapaca", "Impacto de Carapaça", D("0.95"), 0, D(0), 0),
            ("casco_basalto", "Casco Basáltico", D("0.90"), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.90"), 2),
            ("tranco_pedreira", "Tranco de Pedreira", D("1.25"), 0, D(0), 0, None, 0, False, 3),
        ),
        ai_priority=("casco_basalto", "tranco_pedreira"),
    ),
    Creature(
        ALTOS_CARNEIRO_PESO, "Carneiro do Peso", "common", "brute", 42, 46, 0,
        ("chifrada_peso", "pisoteio_contraforte", "carga_cornija"),
        (
            ("chifrada_peso", "Chifrada do Peso", D("1.05"), 0, D(0), 0),
            ("pisoteio_contraforte", "Pisoteio de Contraforte", D("1.30"), 0, D(0), 0, None, 0, False, 3),
            ("carga_cornija", "Carga de Cornija", D("1.75"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("carga_cornija", "pisoteio_contraforte"),
    ),
    Creature(
        ALTOS_QUEBRA_ESCARPAS, "Quebra-Escarpas", "elite", "brute", 43, 45, 0,
        ("chifrada_ruptura", "fratura_apoio", "pisoteio_alto", "carga_escarpa"),
        (
            ("chifrada_ruptura", "Chifrada de Ruptura", D("1.10"), 0, D(0), 0),
            ("fratura_apoio", "Fratura de Apoio", D("0.90"), 0, D("0.12"), 2, None, 0, False, 3, "defense"),
            ("pisoteio_alto", "Pisoteio Alto", D("0.75"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
            ("carga_escarpa", "Carga de Escarpa", D("1.80"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("fratura_apoio", "pisoteio_alto", "carga_escarpa"),
    ),
    Creature(
        ALTOS_LAGARTO_ESCORIA, "Lagarto de Escória", "common", "balanced", 43, 47, 0,
        ("mordida_escoria", "cauda_atrito", "placa_atrito"),
        (
            ("mordida_escoria", "Mordida de Escória", D("1.00"), 0, D(0), 0),
            ("cauda_atrito", "Cauda de Atrito", D("1.20"), 0, D(0), 0, None, 0, False, 3),
            ("placa_atrito", "Placa de Atrito", D("0.80"), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.80"), 2),
        ),
        ai_priority=("placa_atrito", "cauda_atrito"),
    ),
    Creature(
        ALTOS_QUEBRA_CABOS, "Quebra-Cabos", "common", "controller", 43, 49, 0,
        ("mordida_fibra", "romper_apoio", "investida_baixa"),
        (
            ("mordida_fibra", "Mordida de Fibra", D("0.90"), 0, D(0), 0),
            ("romper_apoio", "Romper Apoio", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
            ("investida_baixa", "Investida Baixa", D("1.20"), 0, D(0), 0, None, 0, False, 3),
        ),
        ai_priority=("romper_apoio", "investida_baixa"),
    ),
    Creature(
        ALTOS_DEVORADOR_ESCORIA, "Devorador de Escória", "elite", "predator", 46, 48, 0,
        ("mordida_devorador", "rasgo_escoria", "cauda_abrasao", "salto_predatorio"),
        (
            ("mordida_devorador", "Mordida do Devorador", D("1.05"), 0, D(0), 0),
            ("rasgo_escoria", "Rasgo de Escória", D("0.90"), 0, D(0), 0, "bleed", 1, False, 2),
            ("cauda_abrasao", "Cauda de Abrasão", D("0.75"), 0, D(0), 0, None, 0, False, 3, None, D(0), D(0), 0, False, "all_opponents"),
            ("salto_predatorio", "Salto Predatório", D("1.75"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("rasgo_escoria", "cauda_abrasao", "salto_predatorio"),
    ),
    Creature(
        ALTOS_MORCEGO_CHAMINE, "Morcego de Chaminé", "common", "predator", 44, 48, 0,
        ("mordida_chamine", "rasante_duto", "eco_duto"),
        (
            ("mordida_chamine", "Mordida de Chaminé", D("0.90"), 0, D(0), 0),
            ("rasante_duto", "Rasante de Duto", D("1.10"), 0, D(0), 0, None, 0, False, 2),
            ("eco_duto", "Eco de Duto", D("0.80"), 0, D("0.10"), 2, None, 0, False, 3, "perception"),
        ),
        ai_priority=("eco_duto", "rasante_duto"),
    ),
    Creature(
        ALTOS_CARCACA_MINERAL, "Carcaça Mineral", "uncommon", "armored", 45, 49, 0,
        ("golpe_mineralizado", "crosta_deposito", "arrasto_pesado"),
        (
            ("golpe_mineralizado", "Golpe Mineralizado", D("1.00"), 0, D(0), 0),
            ("crosta_deposito", "Crosta de Depósito", D("0.95"), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.95"), 2),
            ("arrasto_pesado", "Arrasto Pesado", D("1.30"), 0, D(0), 0, None, 0, False, 3),
        ),
        ai_priority=("crosta_deposito", "arrasto_pesado"),
    ),
    Creature(
        ALTOS_VIGIA_CARGA, "Vigia de Carga", "uncommon", "armored", 47, 50, 0,
        ("impacto_carga", "placa_ancoragem", "marcacao_peso", "descarga_contrapeso"),
        (
            ("impacto_carga", "Impacto de Carga", D("1.00"), 0, D(0), 0),
            ("placa_ancoragem", "Placa de Ancoragem", D("0.95"), 0, D(0), 0, None, 0, False, 3, None, D(0), D("0.95"), 2),
            ("marcacao_peso", "Marcação de Peso", D("0.85"), 0, D("0.10"), 2, None, 0, False, 3, "defense"),
            ("descarga_contrapeso", "Descarga de Contrapeso", D("1.65"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("placa_ancoragem", "marcacao_peso", "descarga_contrapeso"),
    ),
    Creature(
        ALTOS_SUPERVISOR_CARGA, "Supervisor de Carga", "elite", "armored", 48, 50, 0,
        ("impacto_supervisao", "travar_carga", "ordem_pressao", "descarga_linha"),
        (
            ("impacto_supervisao", "Impacto de Supervisão", D("1.00"), 0, D(0), 0),
            ("travar_carga", "Travar Carga", D("1.00"), 0, D(0), 0, None, 0, False, 3, None, D(0), D("1.00"), 2),
            ("ordem_pressao", "Ordem de Pressão", D("0.85"), 0, D("0.12"), 2, None, 0, False, 3, "attack"),
            ("descarga_linha", "Descarga de Linha", D("1.80"), 0, D(0), 0, None, 0, True, 4),
        ),
        ai_priority=("travar_carga", "ordem_pressao", "descarga_linha"),
    ),
)

VARIANTS = {
    "furious": StatMultipliers(D(1), D("1.08"), D("0.92"), D(1)),
    "resistant": StatMultipliers(D(1), D("0.94"), D("1.10"), D(1)),
    "agile": StatMultipliers(D("0.93"), D(1), D(1), D("1.12")),
    "hemorrhagic": StatMultipliers(D(1), D("0.95"), D(1), D(1)),
    "venomous": StatMultipliers(D("0.95"), D(1), D(1), D(1)),
}
VARIANT_POOL = {
    "dog_cinereo": ("furious", "agile"),
    "corvo_fuligem": ("agile", "furious"),
    "peregrino_calcinado": ("furious", "resistant", "hemorrhagic"),
    "alfa_cinereo": (),
    "aranha_cinza": ("venomous", "agile"),
    "cervo_escoriado": ("furious", "resistant"),
    "carnical_fuligem": ("hemorrhagic", "resistant"),
    "mariposa_brasa": ("agile", "furious"),
    "viuva_fuligem": (),
    "vigia_rachado": ("resistant", "furious"),
    "custodio_sem_rosto": ("resistant", "agile"),
    "custodio_poente": (),
    "lobo_musgoso": ("furious", "agile", "hemorrhagic"),
    "gralha_vale": ("agile", "furious"),
    "peregrino_enredado": ("furious", "resistant", "agile"),
    "aranha_cipo": ("venomous", "agile"),
    "cervo_no": ("furious", "resistant"),
    "no_feroz": (),
    "viuva_cipos": (),
    "sanguessuga_turfa": ("resistant", "venomous"),
    "casca_errante": ("resistant", "furious"),
    "mariposa_breu_verde": ("venomous", "agile", "furious"),
    "vigia_enraizado": ("resistant", "furious"),
    "carrasco_casca": (),
    "galgo_meridiano": ("furious", "agile", "hemorrhagic"),
    "abutre_marco": ("agile", "furious"),
    "errante_valas": ("resistant", "furious", "agile"),
    "escaravelho_canal": ("resistant", "agile"),
    "cervo_horizonte": ("furious", "resistant"),
    "serpe_campinas": ("venomous", "agile"),
    "casco_invertido": ("resistant", "furious"),
    "mariposa_eixo": ("agile", "furious"),
    "vigia_meridiano": ("resistant", "furious"),
    "alfa_horizonte": (),
    "serpe_eixo": (),
    "custodio_invertido": (),
    "cao_salmoura": ("furious", "agile", "hemorrhagic"),
    "garca_ferruginosa": ("agile", "furious"),
    "portador_rubro": ("resistant", "furious", "agile"),
    "alfa_salmoura": (),
    "aranha_junco": ("venomous", "agile"),
    "cervo_ferrugem": ("furious", "resistant"),
    "viuva_rubra": (),
    "lampreia_varzea": ("hemorrhagic", "agile"),
    "enxerto_horto": ("resistant", "furious"),
    "mariposa_soro": ("agile", "furious"),
    "coletor_hematico": (),
    "vigia_hemaris": ("resistant", "furious"),
    ALTOS_LOBO_ESCARPA: ("furious", "agile", "hemorrhagic"),
    ALTOS_ABUTRE_FULIGEM: ("agile", "furious"),
    ALTOS_ESCARAVELHO_BASALTO: ("resistant", "agile"),
    ALTOS_CARNEIRO_PESO: ("furious", "resistant"),
    ALTOS_QUEBRA_ESCARPAS: (),
    ALTOS_LAGARTO_ESCORIA: ("furious", "resistant", "agile"),
    ALTOS_QUEBRA_CABOS: ("agile", "resistant"),
    ALTOS_DEVORADOR_ESCORIA: (),
    ALTOS_MORCEGO_CHAMINE: ("agile", "furious"),
    ALTOS_CARCACA_MINERAL: ("resistant", "furious"),
    ALTOS_VIGIA_CARGA: ("resistant", "furious"),
    ALTOS_SUPERVISOR_CARGA: (),
}

EQUIPMENT_CATALOG = (
    (None, "Principal", "weapon.type.tdo.arma_caminhante"),
    (None, "Secundária", "weapon.type.tdo.guarda_caminhante"),
    (None, "2H", "weapon.type.tdo.arma_pesada_caminhante"),
    ("Elmo de Fuligem", "Cabeça", None),
    ("Couraça de Fuligem", "Torso", None),
    ("Manoplas de Fuligem", "Mãos", None),
    ("Passos de Fuligem", "Pés", None),
    ("Capuz das Cinzas", "Cabeça", None),
    ("Veste do Caminhante", "Torso", None),
    ("Luvas de Fuligem", "Mãos", None),
    ("Botas da Estrada", "Pés", None),
    ("Selo Enegrecido", "Acessório", None),
    ("Relicário de Cinzas", "Artefato", None),
)
RARITY_SECONDARIES = {"Comum": 0, "Raro": 1, "Épico": 2, "Lendário": 3, "Mítico": 4}
RUNE_FAMILIES = (("Brasa", "ATQ"), ("Pedra", "DEF"), ("Caminhante", "AGI"), ("Fresta", "PER"), ("Presságio", "CRIT"), ("Persistência", "HP"), ("Desvio", "Esquiva"), ("Guarda", "Bloqueio"))
CORE60 = {"Principal": {"ATQ": 25}, "Secundária": {"ATQ": 7, "DEF": 5}, "2H": {"ATQ": 35}, "Cabeça": {"HP": 45, "DEF": 6}, "Torso": {"HP": 95, "DEF": 12}, "Mãos": {"ATQ": 10, "DEF": 5}, "Pés": {"HP": 60, "AGI": 8}, "Acessório": {"HP": 50, "ATQ": 7, "AGI": 4}, "Artefato": {"HP": 55, "ATQ": 7, "DEF": 5, "AGI": 4}}

def _stable_draw(seed: str, purpose: str, modulo: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest(), "big") % modulo

def materialize_equipment(
    seed: str,
    rarity: str,
    level: int,
    *,
    forced_name: str | None = None,
    forced_slot: str | None = None,
    bound: bool = False,
    weapon_type_id: str | None = None,
) -> dict:
    if weapon_type_id is not None:
        definition = weapon_definition(weapon_type_id)
        if definition is None:
            raise ValueError("Unknown canonical weapon type ID.")
        expected_slot = definition.persisted_item_slot
        if forced_name is not None and forced_name != definition.item_name:
            raise ValueError("Canonical weapon name does not match its identity.")
        if forced_slot is not None and forced_slot != expected_slot:
            raise ValueError("Canonical weapon slot does not match its identity.")
        forced_name = definition.item_name
        forced_slot = expected_slot

    eligible = tuple(
        template
        for template in EQUIPMENT_CATALOG
        if not (rarity == "Mítico" and template[1] == "Torso")
    )
    selected_weapon_type_id = weapon_type_id
    if forced_slot is not None:
        if forced_slot not in {template[1] for template in eligible}:
            raise ValueError(f"unknown forced equipment slot {forced_slot!r}")
        slot = forced_slot
        if forced_name is None:
            templates = tuple(template for template in eligible if template[1] == slot)
            name, _, selected_weapon_type_id = templates[
                _stable_draw(seed, "equipment.template", len(templates))
            ]
        else:
            name = forced_name
    else:
        groups = tuple(
            sorted({"Principal" if template[1] == "2H" else template[1] for template in eligible})
        )
        group = groups[_stable_draw(seed, "equipment.group", len(groups))]
        templates = tuple(
            template
            for template in eligible
            if template[1] == group or (group == "Principal" and template[1] == "2H")
        )
        if forced_name is None:
            name, slot, selected_weapon_type_id = templates[
                _stable_draw(seed, "equipment.template", len(templates))
            ]
        else:
            name, slot = forced_name, templates[0][1]
    if selected_weapon_type_id is not None:
        definition = weapon_definition(selected_weapon_type_id)
        if definition is None or definition.persisted_item_slot != slot:
            raise ValueError("Equipment template has invalid canonical weapon metadata.")
        if name is None:
            name = definition.item_name
        elif name != definition.item_name:
            raise ValueError("Equipment template name does not match its canonical identity.")
    if name is None:
        raise ValueError("Equipment template is missing its item name.")
    count = RARITY_SECONDARIES[rarity]
    pools = {"Principal": ("ATQ", "AGI", "PER", "CRIT"), "2H": ("ATQ", "AGI", "PER", "CRIT"), "Secundária": ("ATQ", "DEF", "PER", "CRIT", "Bloqueio"), "Cabeça": ("HP", "DEF", "PER", "CRIT"), "Torso": ("HP", "DEF", "Bloqueio"), "Mãos": ("ATQ", "AGI", "PER", "CRIT"), "Pés": ("HP", "DEF", "AGI", "Esquiva"), "Acessório": ("HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"), "Artefato": ("HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio")}
    pool = list(pools[slot])
    secondaries = []
    g = growth(level)
    core = {attribute: int((D(value) * g).quantize(D(1), rounding="ROUND_HALF_UP")) for attribute, value in CORE60[slot].items()}
    for index in range(min(count, len(pool))):
        pick = _stable_draw(seed, f"equipment.secondary.{index}", len(pool))
        attribute = pool.pop(pick)
        budget = D(SLOT_WEIGHTS[slot]) * (RARITY_MULT[rarity] - 1) / max(1, count)
        scale = g.sqrt() if attribute in {"PER", "CRIT", "Esquiva", "Bloqueio"} else g
        raw = budget * SECONDARY_SCALE[attribute] * scale
        if attribute in {"PER", "CRIT", "Esquiva", "Bloqueio"}:
            # Percentage secondaries are quarter percentage points.  Decimal
            # quantization with ROUND_HALF_EVEN is the authoritative ties-to-even
            # rule; a positive roll always retains the 0.25 p.p. minimum.
            value = (
                (raw / D("0.25")).quantize(D(1), rounding=ROUND_HALF_EVEN) * D("0.25")
            )
            value = max(D("0.25"), value)
        else:
            value = raw.quantize(D(1), rounding=ROUND_HALF_UP)
        secondaries.append({"attribute": attribute, "value": str(value)})
    payload = {
        "item_name": name,
        "slot": slot,
        "item_level": level,
        "rarity": rarity,
        "core": core,
        "secondaries": secondaries,
        "enhancement": 0,
        "rune": None,
        "enchantment": None,
        "bound": bound,
    }
    if selected_weapon_type_id is not None:
        payload["weapon_type_id"] = selected_weapon_type_id
    return payload


def rune_potency(family: str, rarity: str, grade: int = 1) -> str:
    return rune_potency_for(family, rarity, grade)

def equipment_rarity(seed: str, category: str, elite_pity: int = 0, legendary_pity: int = 0) -> str:
    roll = _stable_draw(seed, "equipment.rarity", 10000) / 100
    if category == "elite":
        if legendary_pity >= 50:
            return "Lendário" if roll < 95 else "Mítico"
        if elite_pity >= 12:
            return "Épico" if roll < 80 else "Lendário" if roll < 99 else "Mítico"
        bands = ((45, "Comum"), (87, "Raro"), (98, "Épico"), (99.9, "Lendário"), (100, "Mítico"))
    elif category == "common":
        bands = ((78, "Comum"), (97, "Raro"), (99.8, "Épico"), (100, "Lendário"))
    elif category == "uncommon":
        bands = ((65, "Comum"), (94, "Raro"), (99.5, "Épico"), (100, "Lendário"))
    else:
        raise ValueError(f"equipment rarity is not configured for category {category!r}")
    for limit, rarity in bands:
        if roll < limit:
            return rarity
    return bands[-1][1]


@dataclass(frozen=True)
class HuntLocationProfile:
    local_id: str
    label: str
    creature_weights: tuple[tuple[str, int], ...]
    variant_chance: int
    hunt_unlock: str
    round_familiarity: str
    explore_unlock: str = EXPLORE_UNLOCK


ROAD_PROFILE = HuntLocationProfile(
    local_id=ROAD_LOCATION,
    label="Estrada das Cinzas",
    creature_weights=(
        ("dog_cinereo", 34),
        ("corvo_fuligem", 33),
        ("peregrino_calcinado", 30),
        ("alfa_cinereo", 3),
    ),
    variant_chance=8,
    hunt_unlock=HUNT_UNLOCK,
    round_familiarity=ROUND_FAMILIARITY,
)

ALTOS_ESCARPA_PROFILE = HuntLocationProfile(
    local_id=ALTOS_ESCARPA_LOCATION,
    label=ALTOS_ESCARPA,
    creature_weights=(
        (ALTOS_LOBO_ESCARPA, 31),
        (ALTOS_ABUTRE_FULIGEM, 29),
        (ALTOS_ESCARAVELHO_BASALTO, 20),
        (ALTOS_CARNEIRO_PESO, 17),
        (ALTOS_QUEBRA_ESCARPAS, 3),
    ),
    variant_chance=11,
    hunt_unlock=ALTOS_ESCARPA_HUNT_UNLOCK,
    round_familiarity=ALTOS_ESCARPA_ROUND_UNLOCK,
    explore_unlock=ALTOS_ESCARPA_EXPLORE_UNLOCK,
)

ALTOS_PONTES_PROFILE = HuntLocationProfile(
    local_id=ALTOS_PONTES_LOCATION,
    label=ALTOS_PONTES,
    creature_weights=(
        (ALTOS_LOBO_ESCARPA, 15),
        (ALTOS_ABUTRE_FULIGEM, 18),
        (ALTOS_CARNEIRO_PESO, 20),
        (ALTOS_QUEBRA_CABOS, 25),
        (ALTOS_LAGARTO_ESCORIA, 17),
        (ALTOS_QUEBRA_ESCARPAS, 2),
        (ALTOS_DEVORADOR_ESCORIA, 3),
    ),
    variant_chance=13,
    hunt_unlock=ALTOS_PONTES_HUNT_UNLOCK,
    round_familiarity=ALTOS_PONTES_ROUND_UNLOCK,
    explore_unlock=ALTOS_PONTES_EXPLORE_UNLOCK,
)

ALTOS_PEDREIRAS_PROFILE = HuntLocationProfile(
    local_id=ALTOS_PEDREIRAS_LOCATION,
    label=ALTOS_PEDREIRAS,
    creature_weights=(
        (ALTOS_ESCARAVELHO_BASALTO, 18),
        (ALTOS_CARNEIRO_PESO, 16),
        (ALTOS_LAGARTO_ESCORIA, 22),
        (ALTOS_MORCEGO_CHAMINE, 17),
        (ALTOS_CARCACA_MINERAL, 21),
        (ALTOS_QUEBRA_ESCARPAS, 2),
        (ALTOS_DEVORADOR_ESCORIA, 4),
    ),
    variant_chance=16,
    hunt_unlock=ALTOS_PEDREIRAS_HUNT_UNLOCK,
    round_familiarity=ALTOS_PEDREIRAS_ROUND_UNLOCK,
    explore_unlock=ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
)

ALTOS_BASTILHA_PROFILE = HuntLocationProfile(
    local_id=ALTOS_BASTILHA_LOCATION,
    label=ALTOS_BASTILHA,
    creature_weights=(
        (ALTOS_MORCEGO_CHAMINE, 14),
        (ALTOS_CARCACA_MINERAL, 22),
        (ALTOS_QUEBRA_CABOS, 24),
        (ALTOS_VIGIA_CARGA, 34),
        (ALTOS_DEVORADOR_ESCORIA, 2),
        (ALTOS_SUPERVISOR_CARGA, 4),
    ),
    variant_chance=18,
    hunt_unlock=ALTOS_BASTILHA_HUNT_UNLOCK,
    round_familiarity=ALTOS_BASTILHA_ROUND_UNLOCK,
    explore_unlock=ALTOS_BASTILHA_EXPLORE_UNLOCK,
)

LOCATION_LEVEL_BANDS = {
    "Estrada das Cinzas": (1, 10),
    "Charneca da Fuligem": (3, 5),
    "Bosque Calcinado": (5, 8),
    "Ruínas do Vigia": (8, 10),
    "Garganta dos Laços": (11, 13),
    "Mata Suspensa": (13, 16),
    "Baixios Enredados": (15, 18),
    "Claustro das Raízes": (18, 20),
    "Campinas do Meridiano": (21, 23),
    "Posto de Nareth": (21, 23),
    "Câmara do Arconte": (30, 30),
    "Diques Rubros": (31, 34),
    "Porto da Salmoura": (31, 34),
    "Brejos do Pulso": (33, 37),
    "Hortos Hemaris": (35, 39),
    "Galerias de Transferência": (37, 40),
    ALTOS_ESCARPA: (41, 45),
    ALTOS_PONTES: (43, 49),
    ALTOS_PEDREIRAS: (45, 49),
    ALTOS_BASTILHA: (47, 50),
}

CHARNECA_PROFILE = HuntLocationProfile(
    local_id=CHARNECA_LOCATION,
    label="Charneca da Fuligem",
    creature_weights=(
        ("peregrino_calcinado", 31),
        ("dog_cinereo", 31),
        ("aranha_cinza", 18),
        ("cervo_escoriado", 20),
    ),
    variant_chance=10,
    hunt_unlock=CHARNECA_HUNT_UNLOCK,
    round_familiarity=CHARNECA_ROUND_FAMILIARITY,
    explore_unlock=CHARNECA_EXPLORE_UNLOCK,
)

BOSQUE_LOCATION_LABEL = "Bosque Calcinado"
BOSQUE_PROFILE = HuntLocationProfile(
    local_id=BOSQUE_LOCATION,
    label=BOSQUE_LOCATION_LABEL,
    creature_weights=(
        ("cervo_escoriado", 27),
        ("carnical_fuligem", 30),
        ("aranha_cinza", 20),
        ("mariposa_brasa", 20),
        ("viuva_fuligem", 3),
    ),
    variant_chance=12,
    hunt_unlock=BOSQUE_HUNT_UNLOCK,
    round_familiarity=BOSQUE_ROUND_FAMILIARITY,
    explore_unlock=BOSQUE_EXPLORE_UNLOCK,
)

RUINS_PROFILE = HuntLocationProfile(
    local_id=RUINS_LOCATION,
    label="Ruínas do Vigia",
    creature_weights=(("carnical_fuligem", 25), ("vigia_rachado", 32), ("mariposa_brasa", 20), ("custodio_sem_rosto", 20), ("custodio_poente", 3)),
    variant_chance=15,
    hunt_unlock=RUINS_HUNT_UNLOCK,
    round_familiarity=RUINS_ROUND_FAMILIARITY,
    explore_unlock=RUINS_EXPLORE_UNLOCK,
)

VDE_GARGANTA_PROFILE = HuntLocationProfile(
    local_id=VDE_GARGANTA_LOCATION,
    label="Garganta dos Laços",
    creature_weights=(
        ("lobo_musgoso", 34),
        ("gralha_vale", 33),
        ("peregrino_enredado", 30),
        ("no_feroz", 3),
    ),
    variant_chance=10,
    hunt_unlock=VDE_GARGANTA_HUNT_UNLOCK,
    round_familiarity=VDE_GARGANTA_ROUND_FAMILIARITY,
    explore_unlock=VDE_GARGANTA_EXPLORE_UNLOCK,
)

VDE_MATA_PROFILE = HuntLocationProfile(
    local_id=VDE_MATA_LOCATION,
    label="Mata Suspensa",
    creature_weights=(
        ("lobo_musgoso", 20),
        ("gralha_vale", 17),
        ("peregrino_enredado", 15),
        ("aranha_cipo", 21),
        ("cervo_no", 23),
        ("no_feroz", 2),
        ("viuva_cipos", 2),
    ),
    variant_chance=12,
    hunt_unlock=VDE_MATA_HUNT_UNLOCK,
    round_familiarity=VDE_MATA_ROUND_FAMILIARITY,
    explore_unlock=VDE_MATA_EXPLORE_UNLOCK,
)
VDE_BAIXIOS_PROFILE = HuntLocationProfile(
    local_id=VDE_BAIXIOS_LOCATION,
    label="Baixios Enredados",
    creature_weights=(
        ("aranha_cipo", 22), ("cervo_no", 20), ("sanguessuga_turfa", 22),
        ("casca_errante", 18), ("mariposa_breu_verde", 15),
        ("viuva_cipos", 1), ("carrasco_casca", 2),
    ),
    variant_chance=15,
    hunt_unlock=VDE_BAIXIOS_HUNT_UNLOCK,
    round_familiarity=VDE_BAIXIOS_ROUND_FAMILIARITY,
    explore_unlock=VDE_BAIXIOS_EXPLORE_UNLOCK,
)
VDE_CLAUSTRO_PROFILE = HuntLocationProfile(
    local_id=VDE_CLAUSTRO_LOCATION,
    label="Claustro das Raízes",
    creature_weights=(
        ("casca_errante", 35),
        ("mariposa_breu_verde", 30),
        ("vigia_enraizado", 32),
        ("carrasco_casca", 3),
    ),
    variant_chance=18,
    hunt_unlock=VDE_CLAUSTRO_HUNT_UNLOCK,
    round_familiarity=VDE_CLAUSTRO_ROUND_FAMILIARITY,
    explore_unlock=VDE_CLAUSTRO_EXPLORE_UNLOCK,
)


NARETH_CAMPINAS_PROFILE = HuntLocationProfile(
    local_id=NARETH_CAMPINAS_LOCATION,
    label=NARETH_CAMPINAS,
    creature_weights=(("galgo_meridiano", 34), ("abutre_marco", 33), ("errante_valas", 30), ("alfa_horizonte", 3)),
    variant_chance=10,
    hunt_unlock=NARETH_HUNT_UNLOCK,
    round_familiarity=NARETH_ROUND_FAMILIARITY,
    explore_unlock=NARETH_EXPLORE_UNLOCK,
)
NARETH_POSTO_PROFILE = HuntLocationProfile(
    local_id=NARETH_POSTO_LOCATION,
    label=NARETH_POSTO,
    creature_weights=(),
    variant_chance=0,
    hunt_unlock=NARETH_HUNT_UNLOCK,
    round_familiarity=NARETH_ROUND_FAMILIARITY,
    explore_unlock=NARETH_EXPLORE_UNLOCK,
)

@dataclass(frozen=True)
class ExplorationResultDefinition:
    key: str
    category: str
    result_id: str
    weight: int
    text: str
    min_level: int = 1
    creature_id: str | None = None
    unique: bool = False


@dataclass(frozen=True)
class ExplorationLocationProfile:
    local_id: str
    category_weights: tuple[tuple[str, int], ...]
    results: tuple[ExplorationResultDefinition, ...]

    def result(self, key: str) -> ExplorationResultDefinition:
        return next(result for result in self.results if result.key == key)


ROAD_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=ROAD_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("marco_viajantes", "great_discovery", "explore.tdo.estrada.marco_viajantes", 100, "Um marco de pedra inclina-se à margem da estrada. Marcas gastas ao redor mostram que viajantes paravam aqui muito antes das passagens mais recentes.", unique=True),
        ExplorationResultDefinition("rastros_cinereos", "knowledge", "explore.tdo.estrada.rastros_cinereos", 60, "Marcas interrompidas atravessam a fuligem e desaparecem alguns passos adiante. Há sinais suficientes para reconhecer que alguma criatura utiliza esta rota."),
        ExplorationResultDefinition("sinais_margem", "knowledge", "explore.tdo.estrada.sinais_margem", 40, "Pedras movidas, tecido preso aos espinhos e cinza revolvida mostram que viajantes ainda usam as margens da Estrada para descansar ou passar despercebidos."),
        ExplorationResultDefinition("luzes", "narrative", "explore.tdo.estrada.luzes", 70, "Uma luz pálida surge entre as pedras por alguns instantes. Não há chama nem calor suficiente para explicá-la; quando você se aproxima, ela já desapareceu.", unique=True),
        ExplorationResultDefinition("vozes_vento", "narrative", "explore.tdo.estrada.vozes_vento", 30, "O vento atravessa a estrada e traz um som que lembra uma voz distante. Quando você tenta segui-lo, resta apenas o ruído da cinza contra a pedra."),
        ExplorationResultDefinition("dog_cinereo", "combat", "explore.tdo.estrada.combat.dog_cinereo", 40, "Um Cão Cinéreo surge entre as cinzas.", creature_id="dog_cinereo"),
        ExplorationResultDefinition("corvo_fuligem", "combat", "explore.tdo.estrada.combat.corvo_fuligem", 35, "Um Corvo de Fuligem desce sobre a estrada.", creature_id="corvo_fuligem"),
        ExplorationResultDefinition("peregrino_calcinado", "combat", "explore.tdo.estrada.combat.peregrino_calcinado", 25, "Um Peregrino Calcinado bloqueia a passagem.", creature_id="peregrino_calcinado"),
        ExplorationResultDefinition("cinza_pegadas", "atmospheric", "explore.tdo.estrada.cinza_pegadas", 34, "Uma rajada atravessa a Estrada. Em poucos instantes, a cinza cobre marcas antigas até não restar indicação de quem passou por ali."),
        ExplorationResultDefinition("carroca", "atmospheric", "explore.tdo.estrada.carroca", 33, "A estrutura apodrecida de uma carroça repousa fora da estrada. As rodas desapareceram há muito; o restante já não guarda nada de valor."),
        ExplorationResultDefinition("fogueira", "atmospheric", "explore.tdo.estrada.fogueira", 33, "Pedras enegrecidas cercam uma fogueira antiga. A cinza está fria e nenhum sinal recente indica quem a acendeu."),
        ExplorationResultDefinition("ferro", "resource", "explore.tdo.estrada.ferro", 30, "Entre pedras partidas, um veio escuro de metal aflora sob a fuligem. Há material suficiente para ser recolhido."),
        ExplorationResultDefinition("couro", "resource", "explore.tdo.estrada.couro", 30, "Entre restos secos à margem da estrada, uma porção de couro ainda aproveitável resistiu à cinza e ao tempo."),
        ExplorationResultDefinition("erva", "resource", "explore.tdo.estrada.erva", 20, "Folhas acinzentadas crescem entre rachaduras protegidas do vento. Algumas ainda podem ser colhidas."),
        ExplorationResultDefinition("residuo", "resource", "explore.tdo.estrada.residuo", 20, "Um depósito escuro se acumulou entre as pedras. A substância é fina, mas distinta da fuligem comum da Estrada."),
    ),
)

CHARNECA_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=CHARNECA_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro", "great_discovery", "explore.tdo.charneca.braseiro", 50, "Braseiro do Vento Morto encontrado.", min_level=4, unique=True),
        ExplorationResultDefinition("cripta", "great_discovery", "explore.tdo.charneca.cripta", 50, "Entrada da Cripta do Ocaso encontrada.", min_level=4, unique=True),
        ExplorationResultDefinition("pedra_marcada", "knowledge", "explore.tdo.charneca.pedra_marcada", 60, "A Pedra Marcada foi examinada.", unique=True),
        ExplorationResultDefinition("vestigios_fuligem", "knowledge", "explore.tdo.charneca.vestigios_fuligem", 40, "Vestígios de criaturas foram observados na fuligem."),
        ExplorationResultDefinition("vento_morto", "narrative", "explore.tdo.charneca.vento_morto", 65, "Uma área identificada como Vento Morto foi observada." , unique=True),
        ExplorationResultDefinition("cinzas_nao_assentam", "narrative", "explore.tdo.charneca.cinzas_nao_assentam", 35, "As cinzas não assentam sobre o terreno."),
        ExplorationResultDefinition("peregrino_calcinado", "combat", "explore.tdo.charneca.combat.peregrino_calcinado", 35, "Um Peregrino Calcinado surge na Charneca.", creature_id="peregrino_calcinado"),
        ExplorationResultDefinition("aranha_cinza", "combat", "explore.tdo.charneca.combat.aranha_cinza", 35, "Uma Aranha de Cinza surge na Charneca.", min_level=3, creature_id="aranha_cinza"),
        ExplorationResultDefinition("cervo_escoriado", "combat", "explore.tdo.charneca.combat.cervo_escoriado", 30, "Um Cervo Escoriado surge na Charneca.", min_level=4, creature_id="cervo_escoriado"),
        ExplorationResultDefinition("erva", "resource", "explore.tdo.charneca.erva", 45, "Erva Cinzenta pode ser recolhida na Charneca."),
        ExplorationResultDefinition("residuo", "resource", "explore.tdo.charneca.residuo", 30, "Resíduo do Ocaso pode ser recolhido na Charneca."),
        ExplorationResultDefinition("couro", "resource", "explore.tdo.charneca.couro", 25, "Couro Escoriado pode ser recolhido na Charneca."),
        ExplorationResultDefinition("pedras_negras", "atmospheric", "explore.tdo.charneca.pedras_negras", 34, "Pedras negras cobrem parte do terreno."),
        ExplorationResultDefinition("capim_coberto_cinza", "atmospheric", "explore.tdo.charneca.capim_coberto_cinza", 33, "Capim coberto de cinza foi observado."),
        ExplorationResultDefinition("silencio_sem_passaros", "atmospheric", "explore.tdo.charneca.silencio_sem_passaros", 33, "Nenhum pássaro foi ouvido na área."),
    ),
)

BOSQUE_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=BOSQUE_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro", "great_discovery", "explore.tdo.bosque.braseiro", 50, "Braseiro dos Galhos Mortos encontrado.", min_level=6, unique=True),
        ExplorationResultDefinition("estrutura_enterrada", "great_discovery", "explore.tdo.bosque.estrutura_enterrada", 50, "Uma estrutura enterrada foi encontrada sob as raízes.", min_level=6, unique=True),
        ExplorationResultDefinition("caminho_ocidental", "knowledge", "explore.tdo.bosque.caminho_ocidental", 60, "O Caminho Ocidental foi reconhecido entre as árvores.", unique=True),
        ExplorationResultDefinition("rastros_galhos", "knowledge", "explore.tdo.bosque.rastros_galhos", 40, "Rastros entre os galhos indicam a passagem de criaturas conhecidas."),
        ExplorationResultDefinition("arvores_fumegam", "narrative", "explore.tdo.bosque.arvores_fumegam", 55, "Árvores que Ainda Fumegam."),
        ExplorationResultDefinition("cinzas_raizes", "narrative", "explore.tdo.bosque.cinzas_raizes", 45, "Cinzas sob as Raízes."),
        ExplorationResultDefinition("cervo_escoriado", "combat", "explore.tdo.bosque.combat.cervo_escoriado", 25, "Um Cervo Escoriado surge entre as raízes.", creature_id="cervo_escoriado"),
        ExplorationResultDefinition("carnical_fuligem", "combat", "explore.tdo.bosque.combat.carnical_fuligem", 30, "Um Carniçal de Fuligem bloqueia o caminho.", creature_id="carnical_fuligem"),
        ExplorationResultDefinition("aranha_cinza", "combat", "explore.tdo.bosque.combat.aranha_cinza", 20, "Uma Aranha de Cinza desce dos galhos.", creature_id="aranha_cinza"),
        ExplorationResultDefinition("mariposa_brasa", "combat", "explore.tdo.bosque.combat.mariposa_brasa", 25, "Uma Mariposa de Brasa se aproxima.", min_level=6, creature_id="mariposa_brasa"),
        ExplorationResultDefinition("couro", "resource", "explore.tdo.bosque.couro", 35, "Couro Escoriado pode ser recolhido no Bosque."),
        ExplorationResultDefinition("erva", "resource", "explore.tdo.bosque.erva", 30, "Erva Cinzenta pode ser recolhida no Bosque."),
        ExplorationResultDefinition("residuo", "resource", "explore.tdo.bosque.residuo", 35, "Resíduo do Ocaso pode ser recolhido no Bosque."),
        ExplorationResultDefinition("troncos_ocos", "atmospheric", "explore.tdo.bosque.troncos_ocos", 34, "Troncos ocos atravessam a camada de cinza."),
        ExplorationResultDefinition("brasa_casca", "atmospheric", "explore.tdo.bosque.brasa_casca", 33, "Uma brasa permanece sob a casca escurecida."),
        ExplorationResultDefinition("som_galhos", "atmospheric", "explore.tdo.bosque.som_galhos", 33, "Um som distante atravessa os galhos."),
    ),
)

RUINS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=RUINS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_poente", "great_discovery", "explore.tdo.ruinas.braseiro", 50, "Braseiro do Poente encontrado.", unique=True),
        ExplorationResultDefinition("galerias_vigia", "great_discovery", "explore.tdo.ruinas.galerias", 50, "A entrada das Galerias do Vigia foi descoberta.", min_level=8, unique=True),
        ExplorationResultDefinition("estruturas_guarda", "knowledge", "explore.tdo.ruinas.estruturas_guarda", 40, "Estruturas de guarda foram registradas.", unique=True),
        ExplorationResultDefinition("ocupacao_posterior", "knowledge", "explore.tdo.ruinas.ocupacao_posterior", 40, "Sinais de ocupação posterior foram encontrados.", unique=True),
        ExplorationResultDefinition("marcas_patrulha", "knowledge", "explore.tdo.ruinas.marcas_patrulha", 20, "Marcas de patrulha foram observadas."),
        ExplorationResultDefinition("passos_ninguem", "narrative", "explore.tdo.ruinas.passos_ninguem", 50, "Passos onde Ninguém Passa."),
        ExplorationResultDefinition("pedra_vigilia", "narrative", "explore.tdo.ruinas.pedra_vigilia", 50, "Pedra ainda em Vigília."),
        ExplorationResultDefinition("vigia_rachado", "combat", "explore.tdo.ruinas.combat.vigia_rachado", 35, "Um Vigia Rachado bloqueia o caminho.", creature_id="vigia_rachado"),
        ExplorationResultDefinition("custodio_sem_rosto", "combat", "explore.tdo.ruinas.combat.custodio_sem_rosto", 30, "Um Custódio Sem Rosto se aproxima.", creature_id="custodio_sem_rosto"),
        ExplorationResultDefinition("carnical_fuligem", "combat", "explore.tdo.ruinas.combat.carnical_fuligem", 20, "Um Carniçal de Fuligem surge nas Ruínas.", creature_id="carnical_fuligem"),
        ExplorationResultDefinition("mariposa_brasa", "combat", "explore.tdo.ruinas.combat.mariposa_brasa", 15, "Uma Mariposa de Brasa cruza as Ruínas.", min_level=8, creature_id="mariposa_brasa"),
        ExplorationResultDefinition("ferro", "resource", "explore.tdo.ruinas.ferro", 45, "Ferro de Fuligem pode ser recolhido nas Ruínas."),
        ExplorationResultDefinition("residuo", "resource", "explore.tdo.ruinas.residuo", 35, "Resíduo do Ocaso pode ser recolhido nas Ruínas."),
        ExplorationResultDefinition("erva", "resource", "explore.tdo.ruinas.erva", 10, "Erva Cinzenta pode ser recolhida nas Ruínas."),
        ExplorationResultDefinition("couro", "resource", "explore.tdo.ruinas.couro", 10, "Couro Escoriado pode ser recolhido nas Ruínas."),
        ExplorationResultDefinition("porta_fechada", "atmospheric", "explore.tdo.ruinas.porta_nao_abre", 34, "Uma porta não se abre."),
        ExplorationResultDefinition("estatua", "atmospheric", "explore.tdo.ruinas.estatua_sem_rosto", 33, "Uma estátua sem rosto permanece entre as pedras."),
        ExplorationResultDefinition("eco_pedra", "atmospheric", "explore.tdo.ruinas.eco_sob_pedra", 33, "Um eco ressoa sob a pedra."),
    ),
)

VDE_GARGANTA_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VDE_GARGANTA_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("marco_lacos", "great_discovery", "explore.vde.garganta.marco_dos_lacos", 100, "Marco dos Laços · vestígio de uma rota antiga construída antes das passagens atuais.", min_level=11, unique=True),
        ExplorationResultDefinition("pegadas_barranco", "knowledge", "explore.vde.garganta.pegadas_no_barranco", 60, "Pegadas foram encontradas no barranco."),
        ExplorationResultDefinition("cordas_arrastadas", "knowledge", "explore.vde.garganta.cordas_arrastadas", 40, "Cordas arrastadas foram observadas junto à antiga rota."),
        ExplorationResultDefinition("sinos_sem_maos", "narrative", "explore.vde.garganta.sinos_sem_maos", 70, "Sinos sem Mãos foram observados.", min_level=11, unique=True),
        ExplorationResultDefinition("nevoa_paredoes", "narrative", "explore.vde.garganta.nevoa_entre_paredoes", 30, "A névoa se mantém entre os paredões."),
        ExplorationResultDefinition("lobo_musgoso", "combat", "explore.vde.garganta.combat.lobo_musgoso", 40, "Um Lobo Musgoso surge entre as raízes.", min_level=11, creature_id="lobo_musgoso"),
        ExplorationResultDefinition("gralha_vale", "combat", "explore.vde.garganta.combat.gralha_vale", 35, "Uma Gralha do Vale cruza a névoa.", min_level=11, creature_id="gralha_vale"),
        ExplorationResultDefinition("peregrino_enredado", "combat", "explore.vde.garganta.combat.peregrino_enredado", 25, "Um Peregrino Enredado bloqueia a passagem.", min_level=11, creature_id="peregrino_enredado"),
        ExplorationResultDefinition("ferro", "resource", "explore.vde.garganta.ferro_enredado", 30, "Ferro Enredado pode ser recolhido na Garganta.", min_level=11),
        ExplorationResultDefinition("couro", "resource", "explore.vde.garganta.couro_musgoso", 30, "Couro Musgoso pode ser recolhido na Garganta.", min_level=11),
        ExplorationResultDefinition("erva", "resource", "explore.vde.garganta.erva_de_turfa", 25, "Erva de Turfa pode ser recolhida na Garganta.", min_level=11),
        ExplorationResultDefinition("resina", "resource", "explore.vde.garganta.resina_enredada", 15, "Resina Enredada pode ser recolhida na Garganta.", min_level=11),
        ExplorationResultDefinition("pedra_musgo", "atmospheric", "explore.vde.garganta.pedra_coberta_de_musgo", 34, "Pedra coberta de musgo ocupa a margem do caminho."),
        ExplorationResultDefinition("ponte_sem_caminho", "atmospheric", "explore.vde.garganta.ponte_sem_caminho", 33, "Uma ponte sem caminho visível atravessa a névoa."),
        ExplorationResultDefinition("cordas_abismo", "atmospheric", "explore.vde.garganta.cordas_sobre_abismo", 33, "Cordas antigas passam sobre o abismo."),
    ),
)

VDE_MATA_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VDE_MATA_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("brazier_copas", "great_discovery", "explore.vde.mata.braseiro_das_copas", 50, "Braseiro das Copas Suspensas encontrado.", min_level=13, unique=True),
        ExplorationResultDefinition("fosso_raizes", "great_discovery", "explore.vde.mata.entrada_fosso_raizes", 50, "A entrada do Fosso das Raízes foi encontrada.", min_level=13, unique=True),
        ExplorationResultDefinition("passarela_partida", "knowledge", "explore.vde.mata.passarela_partida", 55, "A Passarela Partida foi examinada.", min_level=13, unique=True),
        ExplorationResultDefinition("rastros_copas", "knowledge", "explore.vde.mata.rastros_nas_copas", 45, "Rastros foram observados nas copas."),
        ExplorationResultDefinition("madeira_geme", "narrative", "explore.vde.mata.madeira_que_geme", 55, "A madeira geme sob o movimento dos galhos."),
        ExplorationResultDefinition("galhos_sem_vento", "narrative", "explore.vde.mata.galhos_sem_vento", 45, "Galhos se movem sem vento aparente."),
        ExplorationResultDefinition("lobo_musgoso", "combat", "explore.vde.mata.combat.lobo_musgoso", 20, "Um Lobo Musgoso surge entre os troncos.", min_level=11, creature_id="lobo_musgoso"),
        ExplorationResultDefinition("gralha_vale", "combat", "explore.vde.mata.combat.gralha_vale", 15, "Uma Gralha do Vale desce sobre a passarela.", min_level=11, creature_id="gralha_vale"),
        ExplorationResultDefinition("peregrino_enredado", "combat", "explore.vde.mata.combat.peregrino_enredado", 15, "Um Peregrino Enredado aparece entre as raízes.", min_level=11, creature_id="peregrino_enredado"),
        ExplorationResultDefinition("aranha_cipo", "combat", "explore.vde.mata.combat.aranha_cipo", 25, "Uma Aranha de Cipó desce dos galhos.", min_level=13, creature_id="aranha_cipo"),
        ExplorationResultDefinition("cervo_no", "combat", "explore.vde.mata.combat.cervo_no", 25, "Um Cervo do Nó ocupa a passagem.", min_level=13, creature_id="cervo_no"),
        ExplorationResultDefinition("couro", "resource", "explore.vde.mata.couro_musgoso", 35, "Couro Musgoso pode ser recolhido na Mata Suspensa.", min_level=13),
        ExplorationResultDefinition("erva", "resource", "explore.vde.mata.erva_de_turfa", 30, "Erva de Turfa pode ser recolhida na Mata Suspensa.", min_level=13),
        ExplorationResultDefinition("resina", "resource", "explore.vde.mata.resina_enredada", 25, "Resina Enredada pode ser recolhida na Mata Suspensa.", min_level=13),
        ExplorationResultDefinition("ferro", "resource", "explore.vde.mata.ferro_enredado", 10, "Ferro Enredado pode ser recolhido na Mata Suspensa.", min_level=13),
        ExplorationResultDefinition("troncos_vazio", "atmospheric", "explore.vde.mata.troncos_sobre_vazio", 34, "Troncos atravessam o vazio entre as copas."),
        ExplorationResultDefinition("folhas_nao_caem", "atmospheric", "explore.vde.mata.folhas_que_nao_caem", 33, "Folhas permanecem suspensas entre os galhos."),
        ExplorationResultDefinition("ruina_copas", "atmospheric", "explore.vde.mata.ruina_entre_copas", 33, "Uma ruína aparece entre as copas."),
    ),
)

VDE_BAIXIOS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VDE_BAIXIOS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("brazier_turfa", "great_discovery", "explore.vde.baixios.braseiro_turfa_fria", 50, "Braseiro da Turfa Fria encontrado.", min_level=15, unique=True),
        ExplorationResultDefinition("galeria_afogada", "great_discovery", "explore.vde.baixios.galeria_afogada", 50, "A Galeria Afogada confirma apenas uma estrutura antiga sob os Baixios.", min_level=15, unique=True),
        ExplorationResultDefinition("marcas_agua", "knowledge", "explore.vde.baixios.marcas_sob_a_agua", 60, "Marcas sob a Água foram registradas.", min_level=15, unique=True),
        ExplorationResultDefinition("rastros_turfa", "knowledge", "explore.vde.baixios.rastros_na_turfa", 40, "Rastros foram encontrados na turfa.", min_level=15),
        ExplorationResultDefinition("agua_sem_reflexo", "narrative", "explore.vde.baixios.agua_sem_reflexo", 55, "A água dos Baixios não devolve um reflexo nítido.", min_level=15),
        ExplorationResultDefinition("raizes_lama", "narrative", "explore.vde.baixios.raizes_sob_a_lama", 45, "Raízes atravessam a lama sob a água.", min_level=15),
        ExplorationResultDefinition("aranha_cipo", "combat", "explore.vde.baixios.combat.aranha_cipo", 22, "Uma Aranha de Cipó surge entre as raízes submersas.", min_level=15, creature_id="aranha_cipo"),
        ExplorationResultDefinition("cervo_no", "combat", "explore.vde.baixios.combat.cervo_no", 20, "Um Cervo do Nó ocupa a passagem alagada.", min_level=15, creature_id="cervo_no"),
        ExplorationResultDefinition("sanguessuga_turfa", "combat", "explore.vde.baixios.combat.sanguessuga_turfa", 23, "Uma Sanguessuga de Turfa se aproxima.", min_level=15, creature_id="sanguessuga_turfa"),
        ExplorationResultDefinition("casca_errante", "combat", "explore.vde.baixios.combat.casca_errante", 18, "Uma Casca Errante bloqueia a passagem.", min_level=15, creature_id="casca_errante"),
        ExplorationResultDefinition("mariposa_breu_verde", "combat", "explore.vde.baixios.combat.mariposa_breu_verde", 17, "Uma Mariposa do Breu Verde cruza a água escura.", min_level=16, creature_id="mariposa_breu_verde"),
        ExplorationResultDefinition("erva", "resource", "explore.vde.baixios.erva_de_turfa", 35, "Erva de Turfa pode ser recolhida nos Baixios.", min_level=15),
        ExplorationResultDefinition("resina", "resource", "explore.vde.baixios.resina_enredada", 30, "Resina Enredada pode ser recolhida nos Baixios.", min_level=15),
        ExplorationResultDefinition("couro", "resource", "explore.vde.baixios.couro_musgoso", 25, "Couro Musgoso pode ser recolhido nos Baixios.", min_level=15),
        ExplorationResultDefinition("ferro", "resource", "explore.vde.baixios.ferro_enredado", 10, "Ferro Enredado pode ser recolhido nos Baixios.", min_level=15),
        ExplorationResultDefinition("agua_negra", "atmospheric", "explore.vde.baixios.agua_negra", 34, "Água negra ocupa uma depressão entre as raízes."),
        ExplorationResultDefinition("troncos_submersos", "atmospheric", "explore.vde.baixios.troncos_submersos", 33, "Troncos permanecem submersos sob a turfa."),
        ExplorationResultDefinition("luz_turfa", "atmospheric", "explore.vde.baixios.luz_sob_a_turfa", 33, "Uma luz tênue aparece sob a turfa e logo se apaga."),
    ),
)

VDE_CLAUSTRO_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VDE_CLAUSTRO_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("brazier_pedras_enlacadas", "great_discovery", "explore.vde.claustro.braseiro_pedras_enlacadas", 50, "Braseiro das Pedras Enlaçadas encontrado.", unique=True),
        ExplorationResultDefinition("santuario_no_antigo", "great_discovery", "explore.vde.claustro.entrada_santuario_no_antigo", 50, "A entrada do Santuário do Nó Antigo foi descoberta.", unique=True),
        ExplorationResultDefinition("tracado_no", "knowledge", "explore.vde.claustro.tracado_do_no", 60, "O Traçado do Nó foi registrado.", unique=True),
        ExplorationResultDefinition("passos_vigia", "knowledge", "explore.vde.claustro.passos_de_vigia", 40, "Passos de Vigia foram observados."),
        ExplorationResultDefinition("pedra_sob_madeira", "narrative", "explore.vde.claustro.pedra_sob_madeira", 55, "Pedra antiga permanece sob a madeira e as raízes."),
        ExplorationResultDefinition("corredores_persistem", "narrative", "explore.vde.claustro.corredores_que_persistem", 45, "Corredores antigos continuam atravessando o Claustro."),
        ExplorationResultDefinition("casca_errante", "combat", "explore.vde.claustro.combat.casca_errante", 35, "Uma Casca Errante atravessa o corredor.", min_level=15, creature_id="casca_errante"),
        ExplorationResultDefinition("mariposa_breu_verde", "combat", "explore.vde.claustro.combat.mariposa_breu_verde", 30, "Uma Mariposa do Breu Verde se agita sob a pedra.", min_level=16, creature_id="mariposa_breu_verde"),
        ExplorationResultDefinition("vigia_enraizado", "combat", "explore.vde.claustro.combat.vigia_enraizado", 35, "Um Vigia Enraizado ocupa a passagem.", min_level=18, creature_id="vigia_enraizado"),
        ExplorationResultDefinition("ferro", "resource", "explore.vde.claustro.ferro_enredado", 35, "Ferro Enredado pode ser recolhido no Claustro.", min_level=18),
        ExplorationResultDefinition("resina", "resource", "explore.vde.claustro.resina_enredada", 35, "Resina Enredada pode ser recolhida no Claustro.", min_level=18),
        ExplorationResultDefinition("erva", "resource", "explore.vde.claustro.erva_de_turfa", 20, "Erva de Turfa pode ser recolhida no Claustro.", min_level=18),
        ExplorationResultDefinition("couro", "resource", "explore.vde.claustro.couro_musgoso", 10, "Couro Musgoso pode ser recolhido no Claustro.", min_level=18),
        ExplorationResultDefinition("colunas_estranguladas", "atmospheric", "explore.vde.claustro.colunas_estranguladas", 34, "Colunas antigas permanecem estranguladas por raízes."),
        ExplorationResultDefinition("portas_sem_passagem", "atmospheric", "explore.vde.claustro.portas_sem_passagem", 33, "Portas antigas não oferecem passagem."),
        ExplorationResultDefinition("raizes_dentro_pedra", "atmospheric", "explore.vde.claustro.raizes_dentro_da_pedra", 33, "Raízes atravessam a pedra do Claustro."),
    ),
)

NARETH_CAMPINAS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=NARETH_CAMPINAS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("first_meridian", "great_discovery", "explore.nareth.campinas.marco_primeiro_meridiano", 100, "O Marco do Primeiro Meridiano confirma que a antiga estrada usava referências repetidas em intervalos regulares.", min_level=21, unique=True),
        ExplorationResultDefinition("pegadas_alongadas", "knowledge", "explore.nareth.campinas.pegadas_alongadas", 60, "Pegadas alongadas foram registradas nas Campinas.", min_level=21),
        ExplorationResultDefinition("medidas_pedra", "knowledge", "explore.nareth.campinas.medidas_na_pedra", 40, "Medidas antigas foram observadas na pedra.", min_level=21),
        ExplorationResultDefinition("duas_medidas", "narrative", "explore.nareth.campinas.duas_medidas_mesma_estrada", 70, "Duas medidas para a mesma estrada divergem sem explicar a função das referências.", min_level=21, unique=True),
        ExplorationResultDefinition("vento_palha", "narrative", "explore.nareth.campinas.vento_sobre_palha", 30, "O vento atravessa a palha alta das Campinas.", min_level=21),
        ExplorationResultDefinition("galgo_meridiano", "combat", "explore.nareth.campinas.combat.galgo_meridiano", 40, "Um Galgo do Meridiano surge no campo.", min_level=21, creature_id="galgo_meridiano"),
        ExplorationResultDefinition("abutre_marco", "combat", "explore.nareth.campinas.combat.abutre_marco", 35, "Um Abutre de Marco desce sobre a rota.", min_level=21, creature_id="abutre_marco"),
        ExplorationResultDefinition("errante_valas", "combat", "explore.nareth.campinas.combat.errante_valas", 25, "Um Errante das Valas bloqueia a passagem.", min_level=21, creature_id="errante_valas"),
        ExplorationResultDefinition("bronze_marco", "resource", "explore.nareth.campinas.bronze_de_marco", 30, "Bronze de Marco pode ser recolhido nas Campinas.", min_level=21),
        ExplorationResultDefinition("couro_horizonte", "resource", "explore.nareth.campinas.couro_de_horizonte", 30, "Couro de Horizonte pode ser recolhido nas Campinas.", min_level=21),
        ExplorationResultDefinition("erva_vento", "resource", "explore.nareth.campinas.erva_de_vento", 25, "Erva de Vento pode ser recolhida nas Campinas.", min_level=21),
        ExplorationResultDefinition("po_eixo", "resource", "explore.nareth.campinas.po_de_eixo", 15, "Pó de Eixo pode ser recolhido nas Campinas.", min_level=21),
        ExplorationResultDefinition("linha_relva", "atmospheric", "explore.nareth.campinas.linha_sob_relva", 34, "Uma linha de pedra permanece sob a relva.", min_level=21),
        ExplorationResultDefinition("horizonte_sem_abrigo", "atmospheric", "explore.nareth.campinas.horizonte_sem_abrigo", 33, "O horizonte aberto não oferece abrigo.", min_level=21),
        ExplorationResultDefinition("pedra_duas_sombras", "atmospheric", "explore.nareth.campinas.pedra_duas_sombras", 33, "Uma pedra projeta duas sombras alongadas.", min_level=21),
    ),
)

NARETH_CANAIS_PROFILE = HuntLocationProfile(
    local_id=NARETH_CANAIS_LOCATION,
    label=NARETH_CANAIS,
    creature_weights=(
        ("galgo_meridiano", 20), ("abutre_marco", 17), ("errante_valas", 15),
        ("escaravelho_canal", 21), ("cervo_horizonte", 23), ("alfa_horizonte", 2),
        ("serpe_eixo", 2),
    ),
    variant_chance=12,
    hunt_unlock="hunt.manual.nareth.canais_secos",
    round_familiarity="hunt_round.nareth.canais_secos",
    explore_unlock="explore.nareth.canais_secos",
)
NARETH_CAMPOS_PROFILE = HuntLocationProfile(
    local_id=NARETH_CAMPOS_LOCATION,
    label=NARETH_CAMPOS,
    creature_weights=(
        ("escaravelho_canal", 22), ("cervo_horizonte", 20), ("serpe_campinas", 22),
        ("casco_invertido", 18), ("mariposa_eixo", 15), ("serpe_eixo", 1),
        ("custodio_invertido", 2),
    ),
    variant_chance=15,
    hunt_unlock="hunt.manual.nareth.campos_invertidos",
    round_familiarity="hunt_round.nareth.campos_invertidos",
    explore_unlock="explore.nareth.campos_invertidos",
)
NARETH_OBSERVATORIO_PROFILE = HuntLocationProfile(
    local_id=NARETH_OBSERVATORIO_LOCATION,
    label=NARETH_OBSERVATORIO,
    creature_weights=(
        ("casco_invertido", 35), ("mariposa_eixo", 30),
        ("vigia_meridiano", 32), ("custodio_invertido", 3),
    ),
    variant_chance=18,
    hunt_unlock="hunt.manual.nareth.observatorio_do_eixo",
    round_familiarity="hunt_round.nareth.observatorio_do_eixo",
    explore_unlock="explore.nareth.observatorio_do_eixo",
)
VARZEAS_DIQUES_PROFILE = HuntLocationProfile(
    local_id=VARZEAS_DIQUES_LOCATION,
    label=VARZEAS_DIQUES,
    creature_weights=(
        ("cao_salmoura", 34),
        ("garca_ferruginosa", 33),
        ("portador_rubro", 30),
        ("alfa_salmoura", 3),
    ),
    variant_chance=10,
    hunt_unlock=VARZEAS_DIQUES_HUNT_UNLOCK,
    round_familiarity=VARZEAS_DIQUES_ROUND_FAMILIARITY,
    explore_unlock=VARZEAS_DIQUES_EXPLORE_UNLOCK,
)
VARZEAS_BREJOS_PROFILE = HuntLocationProfile(
    local_id=VARZEAS_BREJOS_LOCATION,
    label=VARZEAS_BREJOS,
    creature_weights=(
        ("cao_salmoura", 18),
        ("garca_ferruginosa", 17),
        ("portador_rubro", 15),
        ("aranha_junco", 20),
        ("cervo_ferrugem", 24),
        ("alfa_salmoura", 3),
        ("viuva_rubra", 3),
    ),
    variant_chance=13,
    hunt_unlock=VARZEAS_BREJOS_HUNT_UNLOCK,
    round_familiarity=VARZEAS_BREJOS_ROUND_FAMILIARITY,
    explore_unlock=VARZEAS_BREJOS_EXPLORE_UNLOCK,
)
VARZEAS_HORTOS_PROFILE = HuntLocationProfile(
    local_id=VARZEAS_HORTOS_LOCATION,
    label=VARZEAS_HORTOS,
    creature_weights=(
        ("aranha_junco", 22),
        ("cervo_ferrugem", 19),
        ("lampreia_varzea", 20),
        ("enxerto_horto", 18),
        ("mariposa_soro", 16),
        ("viuva_rubra", 2),
        ("coletor_hematico", 3),
    ),
    variant_chance=16,
    hunt_unlock=VARZEAS_HORTOS_HUNT_UNLOCK,
    round_familiarity=VARZEAS_HORTOS_ROUND_FAMILIARITY,
    explore_unlock=VARZEAS_HORTOS_EXPLORE_UNLOCK,
)
VARZEAS_GALERIAS_PROFILE = HuntLocationProfile(
    local_id=VARZEAS_GALERIAS_LOCATION,
    label=VARZEAS_GALERIAS,
    creature_weights=(
        ("enxerto_horto", 34),
        ("mariposa_soro", 30),
        ("vigia_hemaris", 33),
        ("coletor_hematico", 3),
    ),
    variant_chance=18,
    hunt_unlock=VARZEAS_GALERIAS_HUNT_UNLOCK,
    round_familiarity=VARZEAS_GALERIAS_ROUND_FAMILIARITY,
    explore_unlock=VARZEAS_GALERIAS_EXPLORE_UNLOCK,
)

NARETH_CANAIS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=NARETH_CANAIS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_canal_alto", "great_discovery", "explore.nareth.canais.braseiro_canal_alto", 50, "O Braseiro do Canal Alto foi descoberto entre as comportas secas.", min_level=23, unique=True),
        ExplorationResultDefinition("entrada_galerias", "great_discovery", "explore.nareth.canais.entrada_galerias_meridiano", 50, "Uma entrada das Galerias do Meridiano foi encontrada sob o canal.", min_level=23, unique=True),
        ExplorationResultDefinition("comporta_sem_agua", "knowledge", "explore.nareth.canais.comporta_sem_agua", 55, "A comporta foi registrada sem água e com marcas de medição.", min_level=23, unique=True),
        ExplorationResultDefinition("marcas_vazao", "knowledge", "explore.nareth.canais.marcas_de_vazao", 45, "Marcas de vazão foram observadas no leito seco.", min_level=23),
        ExplorationResultDefinition("pedra_raspada", "narrative", "explore.nareth.canais.pedra_raspada", 55, "A pedra do canal apresenta marcas de desgaste.", min_level=23),
        ExplorationResultDefinition("ponte_seco", "narrative", "explore.nareth.canais.ponte_sobre_seco", 45, "Uma ponte atravessa o canal sem água.", min_level=23),
        ExplorationResultDefinition("galgo", "combat", "explore.nareth.canais.combat.galgo_meridiano", 20, "Um Galgo do Meridiano surge no canal.", min_level=23, creature_id="galgo_meridiano"),
        ExplorationResultDefinition("abutre", "combat", "explore.nareth.canais.combat.abutre_marco", 15, "Um Abutre de Marco desce sobre o canal.", min_level=23, creature_id="abutre_marco"),
        ExplorationResultDefinition("errante", "combat", "explore.nareth.canais.combat.errante_valas", 15, "Um Errante das Valas bloqueia o canal.", min_level=23, creature_id="errante_valas"),
        ExplorationResultDefinition("escaravelho", "combat", "explore.nareth.canais.combat.escaravelho_canal", 25, "Um Escaravelho de Canal ocupa a passagem.", min_level=23, creature_id="escaravelho_canal"),
        ExplorationResultDefinition("cervo", "combat", "explore.nareth.canais.combat.cervo_horizonte", 25, "Um Cervo do Horizonte atravessa o leito.", min_level=23, creature_id="cervo_horizonte"),
        ExplorationResultDefinition("bronze", "resource", "explore.nareth.canais.bronze_de_marco", 35, "Bronze de Marco pode ser recolhido entre as pedras.", min_level=23),
        ExplorationResultDefinition("erva", "resource", "explore.nareth.canais.erva_de_vento", 30, "Erva de Vento cresce junto ao leito.", min_level=23),
        ExplorationResultDefinition("po", "resource", "explore.nareth.canais.po_de_eixo", 25, "Pó de Eixo pode ser recolhido nas marcas antigas.", min_level=23),
        ExplorationResultDefinition("couro", "resource", "explore.nareth.canais.couro_de_horizonte", 10, "Couro de Horizonte pode ser obtido nesta área.", min_level=23),
        ExplorationResultDefinition("canal_some", "atmospheric", "explore.nareth.canais.canal_que_some", 34, "O leito do canal desaparece sob uma curva seca.", min_level=23),
        ExplorationResultDefinition("eco_ponte", "atmospheric", "explore.nareth.canais.eco_sob_a_ponte", 33, "O vento devolve um eco sob a ponte.", min_level=23),
        ExplorationResultDefinition("vento_comporta", "atmospheric", "explore.nareth.canais.vento_na_comporta", 33, "O vento atravessa a comporta vazia.", min_level=23),
    ),
)
NARETH_CAMPOS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=NARETH_CAMPOS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_linha_quebrada", "great_discovery", "explore.nareth.campos.braseiro_linha_quebrada", 50, "O Braseiro da Linha Quebrada foi descoberto nos Campos.", min_level=25, unique=True),
        ExplorationResultDefinition("linha_nao_fecha", "great_discovery", "explore.nareth.campos.linha_que_nao_fecha", 50, "Uma linha de referência persiste sem fechar.", min_level=25, unique=True),
        ExplorationResultDefinition("sombras_discordam", "knowledge", "explore.nareth.campos.sombras_que_discordam", 60, "Sombras discordantes foram registradas sem explicar o fenômeno.", min_level=25, unique=True),
        ExplorationResultDefinition("rastros_capim", "knowledge", "explore.nareth.campos.rastros_no_capim", 40, "Rastros seguem pelo capim alto.", min_level=25),
        ExplorationResultDefinition("marco_costas", "narrative", "explore.nareth.campos.marco_de_costas", 55, "Um marco parece voltado para longe da rota atual.", min_level=25),
        ExplorationResultDefinition("distancia_silencio", "narrative", "explore.nareth.campos.distancia_em_silencio", 45, "A distância entre marcos deixa a área silenciosa.", min_level=25),
        ExplorationResultDefinition("escaravelho", "combat", "explore.nareth.campos.combat.escaravelho_canal", 22, "Um Escaravelho de Canal ocupa o campo.", min_level=25, creature_id="escaravelho_canal"),
        ExplorationResultDefinition("cervo", "combat", "explore.nareth.campos.combat.cervo_horizonte", 20, "Um Cervo do Horizonte cruza os Campos.", min_level=25, creature_id="cervo_horizonte"),
        ExplorationResultDefinition("serpe", "combat", "explore.nareth.campos.combat.serpe_campinas", 23, "Uma Serpe das Campinas emerge do capim.", min_level=25, creature_id="serpe_campinas"),
        ExplorationResultDefinition("casco", "combat", "explore.nareth.campos.combat.casco_invertido", 18, "Um Casco Invertido bloqueia a linha.", min_level=25, creature_id="casco_invertido"),
        ExplorationResultDefinition("mariposa", "combat", "explore.nareth.campos.combat.mariposa_eixo", 17, "Uma Mariposa do Eixo cruza os Campos.", min_level=26, creature_id="mariposa_eixo"),
        ExplorationResultDefinition("couro", "resource", "explore.nareth.campos.couro_de_horizonte", 30, "Couro de Horizonte pode ser recolhido nos Campos.", min_level=25),
        ExplorationResultDefinition("erva", "resource", "explore.nareth.campos.erva_de_vento", 25, "Erva de Vento cresce nos Campos.", min_level=25),
        ExplorationResultDefinition("po", "resource", "explore.nareth.campos.po_de_eixo", 30, "Pó de Eixo pode ser recolhido nos marcos.", min_level=25),
        ExplorationResultDefinition("bronze", "resource", "explore.nareth.campos.bronze_de_marco", 15, "Bronze de Marco pode ser recolhido nos Campos.", min_level=25),
        ExplorationResultDefinition("declive", "atmospheric", "explore.nareth.campos.declive_improvavel", 34, "O declive parece não corresponder à distância percorrida.", min_level=25),
        ExplorationResultDefinition("ceu_grande", "atmospheric", "explore.nareth.campos.ceu_grande", 33, "O céu aberto ocupa quase todo o horizonte.", min_level=25),
        ExplorationResultDefinition("duas_linhas", "atmospheric", "explore.nareth.campos.duas_linhas_mesmo_chao", 33, "Duas linhas permanecem visíveis no mesmo terreno.", min_level=25),
    ),
)
NARETH_OBSERVATORIO_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=NARETH_OBSERVATORIO_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_eixo", "great_discovery", "explore.nareth.observatorio.braseiro_do_eixo", 50, "O Braseiro do Eixo foi descoberto na plataforma.", min_level=27, unique=True),
        ExplorationResultDefinition("observatorio_afundado", "great_discovery", "explore.nareth.observatorio.entrada_observatorio_afundado", 50, "Uma entrada para o Observatório Afundado foi registrada.", min_level=27, unique=True),
        ExplorationResultDefinition("prumo_fora", "knowledge", "explore.nareth.observatorio.prumo_fora_do_centro", 60, "O prumo foi registrado fora do centro esperado.", min_level=27, unique=True),
        ExplorationResultDefinition("placas_calibracao", "knowledge", "explore.nareth.observatorio.placas_calibracao", 40, "Placas de calibração foram observadas.", min_level=27),
        ExplorationResultDefinition("bracos_imoveis", "narrative", "explore.nareth.observatorio.bracos_imoveis", 55, "Braços mecânicos permanecem imóveis.", min_level=27),
        ExplorationResultDefinition("linha_gravada", "narrative", "explore.nareth.observatorio.linha_gravada", 45, "Uma linha antiga foi gravada na plataforma.", min_level=27),
        ExplorationResultDefinition("casco", "combat", "explore.nareth.observatorio.combat.casco_invertido", 35, "Um Casco Invertido protege a plataforma.", min_level=27, creature_id="casco_invertido"),
        ExplorationResultDefinition("mariposa", "combat", "explore.nareth.observatorio.combat.mariposa_eixo", 30, "Uma Mariposa do Eixo surge no observatório.", min_level=27, creature_id="mariposa_eixo"),
        ExplorationResultDefinition("vigia", "combat", "explore.nareth.observatorio.combat.vigia_meridiano", 35, "Um Vigia do Meridiano guarda o observatório.", min_level=28, creature_id="vigia_meridiano"),
        ExplorationResultDefinition("bronze", "resource", "explore.nareth.observatorio.bronze_de_marco", 35, "Bronze de Marco pode ser recolhido no observatório.", min_level=27),
        ExplorationResultDefinition("po", "resource", "explore.nareth.observatorio.po_de_eixo", 35, "Pó de Eixo pode ser recolhido nas placas.", min_level=27),
        ExplorationResultDefinition("erva", "resource", "explore.nareth.observatorio.erva_de_vento", 20, "Erva de Vento cresce nas fissuras.", min_level=27),
        ExplorationResultDefinition("couro", "resource", "explore.nareth.observatorio.couro_de_horizonte", 10, "Couro de Horizonte pode ser obtido nesta área.", min_level=27),
        ExplorationResultDefinition("piso_marcado", "atmospheric", "explore.nareth.observatorio.piso_marcado", 34, "O piso possui marcas de alinhamento.", min_level=27),
        ExplorationResultDefinition("torre_baixa", "atmospheric", "explore.nareth.observatorio.torre_baixa", 33, "A torre parece baixa em relação aos marcos próximos.", min_level=27),
        ExplorationResultDefinition("horizonte_medido", "atmospheric", "explore.nareth.observatorio.horizonte_medido", 33, "O horizonte é observado como referência de medição.", min_level=27),
    ),
)

VARZEAS_DIQUES_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VARZEAS_DIQUES_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("first_dike_gate", "great_discovery", "explore.varzeas.diques.comporta_primeiro_dique", 100, "A comporta do primeiro dique conserva marcas de manutenção e níveis de água.", min_level=31, unique=True),
        ExplorationResultDefinition("level_marks", "knowledge", "explore.varzeas.diques.marcas_nivel", 60, "Marcas de nível ajudam a comparar o avanço da água ferruginosa.", min_level=31),
        ExplorationResultDefinition("layered_rust", "knowledge", "explore.varzeas.diques.ferrugem_camadas", 40, "A ferrugem se acumula em camadas distintas ao longo das estruturas.", min_level=31),
        ExplorationResultDefinition("water_without_rain", "narrative", "explore.varzeas.diques.agua_sobe_sem_chuva", 70, "A água sobe sem chuva recente observável.", min_level=31, unique=True),
        ExplorationResultDefinition("salt_walkway", "narrative", "explore.varzeas.diques.passarela_sal", 30, "Uma passarela conserva depósitos de salmoura.", min_level=31),
        ExplorationResultDefinition("cao_salmoura", "combat", "explore.varzeas.diques.combat.cao_salmoura", 40, "Um Cão de Salmoura surge entre os diques.", min_level=31, creature_id="cao_salmoura"),
        ExplorationResultDefinition("garca_ferruginosa", "combat", "explore.varzeas.diques.combat.garca_ferruginosa", 35, "Uma Garça Ferruginosa ocupa a margem rasa.", min_level=31, creature_id="garca_ferruginosa"),
        ExplorationResultDefinition("portador_rubro", "combat", "explore.varzeas.diques.combat.portador_rubro", 25, "Um Portador Rubro atravessa a passarela.", min_level=31, creature_id="portador_rubro"),
        ExplorationResultDefinition("ferro_salmoura", "resource", "explore.varzeas.diques.ferro_salmoura", 35, "Ferro de Salmoura pode ser recolhido entre as peças do dique.", min_level=31),
        ExplorationResultDefinition("couro_varzea", "resource", "explore.varzeas.diques.couro_varzea", 30, "Couro de Várzea pode ser recolhido nas margens.", min_level=31),
        ExplorationResultDefinition("junco_ferruginoso", "resource", "explore.varzeas.diques.junco_ferruginoso", 25, "Junco Ferruginoso cresce junto à água.", min_level=31),
        ExplorationResultDefinition("soro_antigo", "resource", "explore.varzeas.diques.soro_antigo", 10, "Soro Antigo pode ser obtido nas margens.", min_level=31),
        ExplorationResultDefinition("stuck_gate", "atmospheric", "explore.varzeas.diques.comporta_travada", 34, "Uma comporta permanece travada apesar das marcas recentes de manutenção.", min_level=31),
        ExplorationResultDefinition("salt_on_wood", "atmospheric", "explore.varzeas.diques.sal_madeira", 33, "O sal se acumula nas tábuas da passarela.", min_level=31),
        ExplorationResultDefinition("red_water_gray_sky", "atmospheric", "explore.varzeas.diques.agua_vermelha_ceu_cinza", 33, "A água vermelha reflete apenas o céu cinzento.", min_level=31),
    ),
)

VARZEAS_BREJOS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VARZEAS_BREJOS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_juncos_baixos", "great_discovery", "explore.varzeas.brejos.braseiro_juncos_baixos", 50, "O Braseiro dos Juncos Baixos foi descoberto entre as passarelas alagadas.", min_level=33, unique=True),
        ExplorationResultDefinition("entrada_enfermaria", "great_discovery", "explore.varzeas.brejos.entrada_enfermaria_afundada", 50, "Uma entrada da Enfermaria Afundada foi descoberta sob a lama.", min_level=34, unique=True),
        ExplorationResultDefinition("pulso_pressao", "knowledge", "explore.varzeas.brejos.pulso_de_pressao", 55, "A pressão sob a turfa coincide com pequenas elevações periódicas da água.", min_level=33, unique=True),
        ExplorationResultDefinition("bolhas_turfa", "knowledge", "explore.varzeas.brejos.bolhas_sob_turfa", 45, "Bolhas surgem sob a turfa e desaparecem sem explicar a origem do movimento.", min_level=33),
        ExplorationResultDefinition("junco_dobrado", "narrative", "explore.varzeas.brejos.junco_dobrado", 55, "Juncos dobrados acompanham a passagem da água.", min_level=33),
        ExplorationResultDefinition("agua_respira", "narrative", "explore.varzeas.brejos.agua_que_respira", 45, "A água sobe e recua em intervalos perceptíveis.", min_level=33),
        ExplorationResultDefinition("cao_salmoura", "combat", "explore.varzeas.brejos.combat.cao_salmoura", 18, "Um Cão de Salmoura surge entre os juncos.", min_level=33, creature_id="cao_salmoura"),
        ExplorationResultDefinition("garca_ferruginosa", "combat", "explore.varzeas.brejos.combat.garca_ferruginosa", 17, "Uma Garça Ferruginosa ocupa a margem alagada.", min_level=33, creature_id="garca_ferruginosa"),
        ExplorationResultDefinition("portador_rubro", "combat", "explore.varzeas.brejos.combat.portador_rubro", 15, "Um Portador Rubro cruza a água rasa.", min_level=33, creature_id="portador_rubro"),
        ExplorationResultDefinition("aranha_junco", "combat", "explore.varzeas.brejos.combat.aranha_junco", 24, "Uma Aranha de Junco desce entre as hastes.", min_level=33, creature_id="aranha_junco"),
        ExplorationResultDefinition("cervo_ferrugem", "combat", "explore.varzeas.brejos.combat.cervo_ferrugem", 26, "Um Cervo Ferrugem bloqueia a passagem entre os juncos.", min_level=33, creature_id="cervo_ferrugem"),
        ExplorationResultDefinition("junco_ferruginoso", "resource", "explore.varzeas.brejos.junco_ferruginoso", 35, "Junco Ferruginoso pode ser recolhido junto à água.", min_level=33),
        ExplorationResultDefinition("couro_varzea", "resource", "explore.varzeas.brejos.couro_varzea", 25, "Couro de Várzea pode ser obtido nas margens.", min_level=33),
        ExplorationResultDefinition("soro_antigo", "resource", "explore.varzeas.brejos.soro_antigo", 25, "Soro Antigo pode ser recolhido entre os depósitos da turfa.", min_level=33),
        ExplorationResultDefinition("ferro_salmoura", "resource", "explore.varzeas.brejos.ferro_salmoura", 15, "Ferro de Salmoura pode ser recolhido nas estruturas expostas.", min_level=33),
        ExplorationResultDefinition("lama_circulos", "atmospheric", "explore.varzeas.brejos.lama_em_circulos", 34, "A lama conserva círculos concêntricos sem marca de impacto.", min_level=33),
        ExplorationResultDefinition("nevoa_salobra", "atmospheric", "explore.varzeas.brejos.nevoa_salobra", 33, "Uma névoa salobra se mantém baixa sobre o brejo.", min_level=33),
        ExplorationResultDefinition("estaca_submersa", "atmospheric", "explore.varzeas.brejos.estaca_submersa", 33, "Uma estaca parcialmente submersa marca a borda de uma passagem.", min_level=33),
    ),
)
VARZEAS_HORTOS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VARZEAS_HORTOS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_horto_seco", "great_discovery", "explore.varzeas.hortos.braseiro_horto_seco", 50, "O Braseiro do Horto Seco foi descoberto entre os canais de cultivo.", min_level=35, unique=True),
        ExplorationResultDefinition("estufa_restituicao", "great_discovery", "explore.varzeas.hortos.estufa_restituicao", 50, "Uma estufa antiga conserva sinais de cultivo técnico.", min_level=35, unique=True),
        ExplorationResultDefinition("canteiro_dupla_funcao", "knowledge", "explore.varzeas.hortos.canteiro_dupla_funcao", 60, "Um canteiro apresenta duas funções de cultivo registradas sem associação nominal antecipada.", min_level=35, unique=True),
        ExplorationResultDefinition("fibras_suporte", "knowledge", "explore.varzeas.hortos.fibras_suporte", 40, "Fibras de suporte foram observadas nos canteiros antigos.", min_level=35),
        ExplorationResultDefinition("vidro_escurecido", "narrative", "explore.varzeas.hortos.vidro_escurecido", 55, "O vidro escurecido ainda cobre parte dos cultivos.", min_level=35),
        ExplorationResultDefinition("raiz_bandeja", "narrative", "explore.varzeas.hortos.raiz_em_bandeja", 45, "Uma raiz cresce dentro de uma bandeja técnica.", min_level=35),
        ExplorationResultDefinition("aranha_junco", "combat", "explore.varzeas.hortos.combat.aranha_junco", 22, "Uma Aranha de Junco surge entre as bandejas.", min_level=35, creature_id="aranha_junco"),
        ExplorationResultDefinition("cervo_ferrugem", "combat", "explore.varzeas.hortos.combat.cervo_ferrugem", 19, "Um Cervo Ferrugem atravessa o setor de cultivo.", min_level=35, creature_id="cervo_ferrugem"),
        ExplorationResultDefinition("lampreia_varzea", "combat", "explore.varzeas.hortos.combat.lampreia_varzea", 21, "Uma Lampreia de Várzea emerge de um canal raso.", min_level=35, creature_id="lampreia_varzea"),
        ExplorationResultDefinition("enxerto_horto", "combat", "explore.varzeas.hortos.combat.enxerto_horto", 20, "Um Enxerto de Horto se move entre as estruturas.", min_level=35, creature_id="enxerto_horto"),
        ExplorationResultDefinition("mariposa_soro", "combat", "explore.varzeas.hortos.combat.mariposa_soro", 18, "Uma Mariposa de Soro cruza o vidro pálido.", min_level=36, creature_id="mariposa_soro"),
        ExplorationResultDefinition("soro_antigo", "resource", "explore.varzeas.hortos.soro_antigo", 35, "Soro Antigo foi recolhido junto aos canais de cultivo.", min_level=35),
        ExplorationResultDefinition("junco_ferruginoso", "resource", "explore.varzeas.hortos.junco_ferruginoso", 30, "Junco Ferruginoso cresce nos leitos úmidos.", min_level=35),
        ExplorationResultDefinition("couro_varzea", "resource", "explore.varzeas.hortos.couro_varzea", 20, "Couro de Várzea pode ser obtido nesta área.", min_level=35),
        ExplorationResultDefinition("ferro_salmoura", "resource", "explore.varzeas.hortos.ferro_salmoura", 15, "Ferro de Salmoura pode ser recolhido nas estruturas expostas.", min_level=35),
        ExplorationResultDefinition("etiquetas_sem_nome", "atmospheric", "explore.varzeas.hortos.etiquetas_sem_nome", 34, "Etiquetas sem nomes permanecem junto aos cultivos.", min_level=35),
        ExplorationResultDefinition("canais_irrigacao", "atmospheric", "explore.varzeas.hortos.canais_irrigacao", 33, "Canais de irrigação atravessam o setor de cultivo.", min_level=35),
        ExplorationResultDefinition("folhas_palidas", "atmospheric", "explore.varzeas.hortos.folhas_palidas", 33, "Folhas pálidas cobrem uma bandeja seca.", min_level=35),
    ),
)
VARZEAS_GALERIAS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=VARZEAS_GALERIAS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition("braseiro_valvulas", "great_discovery", "explore.varzeas.galerias.braseiro_valvulas", 50, "O Braseiro das Válvulas foi descoberto junto aos reservatórios.", min_level=37, unique=True),
        ExplorationResultDefinition("entrada_cisterna", "great_discovery", "explore.varzeas.galerias.entrada_cisterna_transferencia", 50, "Uma entrada da Cisterna de Transferência foi descoberta; seu interior permanece fechado.", min_level=37, unique=True),
        ExplorationResultDefinition("linha_retorno", "knowledge", "explore.varzeas.galerias.linha_retorno", 60, "Uma linha de retorno foi identificada entre os reservatórios.", min_level=37, unique=True),
        ExplorationResultDefinition("reservatorio_vazio", "knowledge", "explore.varzeas.galerias.reservatorio_vazio", 40, "Um reservatório permanece vazio apesar das marcas de uso.", min_level=37),
        ExplorationResultDefinition("valvula_marcada", "narrative", "explore.varzeas.galerias.valvula_marcada", 55, "Uma válvula conserva marcas de manutenção.", min_level=37),
        ExplorationResultDefinition("tubo_parede", "narrative", "explore.varzeas.galerias.tubo_sob_parede", 45, "Um tubo segue sob a parede entre duas salas.", min_level=37),
        ExplorationResultDefinition("enxerto_horto", "combat", "explore.varzeas.galerias.combat.enxerto_horto", 34, "Um Enxerto de Horto se move entre as estruturas.", min_level=37, creature_id="enxerto_horto"),
        ExplorationResultDefinition("mariposa_soro", "combat", "explore.varzeas.galerias.combat.mariposa_soro", 30, "Uma Mariposa de Soro cruza a passagem.", min_level=37, creature_id="mariposa_soro"),
        ExplorationResultDefinition("vigia_hemaris", "combat", "explore.varzeas.galerias.combat.vigia_hemaris", 36, "Um Vigia Hemaris guarda a linha de transporte.", min_level=37, creature_id="vigia_hemaris"),
        ExplorationResultDefinition("ferro_salmoura", "resource", "explore.varzeas.galerias.ferro_salmoura", 35, "Ferro de Salmoura pode ser recolhido nas válvulas.", min_level=37),
        ExplorationResultDefinition("soro_antigo", "resource", "explore.varzeas.galerias.soro_antigo", 35, "Soro Antigo permanece nos reservatórios.", min_level=37),
        ExplorationResultDefinition("junco_ferruginoso", "resource", "explore.varzeas.galerias.junco_ferruginoso", 20, "Junco Ferruginoso pode ser recolhido junto aos canais.", min_level=37),
        ExplorationResultDefinition("couro_varzea", "resource", "explore.varzeas.galerias.couro_varzea", 10, "Couro de Várzea pode ser obtido nesta área.", min_level=37),
        ExplorationResultDefinition("eco_reservatorio", "atmospheric", "explore.varzeas.galerias.eco_reservatorio", 34, "Um eco curto retorna do reservatório.", min_level=37),
        ExplorationResultDefinition("goteira_escura", "atmospheric", "explore.varzeas.galerias.goteira_escura", 33, "Uma goteira escura atravessa a parede.", min_level=37),
        ExplorationResultDefinition("pressao_sem_fluxo", "atmospheric", "explore.varzeas.galerias.pressao_sem_fluxo", 33, "Há pressão no tubo sem fluxo visível.", min_level=37),
    ),
)

ALTOS_ESCARPA_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=ALTOS_ESCARPA_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition(
            "mirante_escoras", "great_discovery", "explore.altos.escarpa.mirante_escoras",
            100, "O Mirante das Escoras foi registrado; a distribuição da carga foi observada.",
            min_level=41, unique=True,
        ),
        ExplorationResultDefinition(
            "fissuras_antigas", "knowledge", "explore.altos.escarpa.fissuras_antigas",
            60, "Fissuras Antigas foram observadas na Escarpa.", min_level=41,
        ),
        ExplorationResultDefinition(
            "marcas_resgate", "knowledge", "explore.altos.escarpa.marcas_resgate",
            40, "Marcas de Resgate foram observadas na Escarpa.", min_level=41,
        ),
        ExplorationResultDefinition(
            "caderno_resgate_rasgado", "narrative",
            "explore.altos.escarpa.caderno_resgate_rasgado", 70,
            "Um Caderno de Resgate Rasgado foi encontrado e registrado no Códice.",
            min_level=41, unique=True,
        ),
        ExplorationResultDefinition(
            "vento_contraforte", "narrative", "explore.altos.escarpa.vento_contraforte",
            30, "O vento passa sob o contraforte.", min_level=41,
        ),
        ExplorationResultDefinition(
            "lobo_escarpa", "combat", "explore.altos.escarpa.combat.lobo_escarpa",
            40, "Um Lobo de Escarpa surge no caminho.", min_level=41,
            creature_id=ALTOS_LOBO_ESCARPA,
        ),
        ExplorationResultDefinition(
            "abutre_fuligem", "combat", "explore.altos.escarpa.combat.abutre_fuligem",
            35, "Um Abutre da Fuligem desce sobre a Escarpa.", min_level=41,
            creature_id=ALTOS_ABUTRE_FULIGEM,
        ),
        ExplorationResultDefinition(
            "escaravelho_basalto", "combat",
            "explore.altos.escarpa.combat.escaravelho_basalto", 25,
            "Um Escaravelho de Basalto bloqueia a passagem.", min_level=41,
            creature_id=ALTOS_ESCARAVELHO_BASALTO,
        ),
        ExplorationResultDefinition(
            "ferro_contrapeso", "resource", "explore.altos.escarpa.ferro_contrapeso",
            30, "Ferro de Contrapeso pode ser recolhido entre as estruturas.", min_level=41,
        ),
        ExplorationResultDefinition(
            "couro_escarpa", "resource", "explore.altos.escarpa.couro_escarpa",
            30, "Couro de Escarpa pode ser recolhido no local.", min_level=41,
        ),
        ExplorationResultDefinition(
            "liquen_pedreira", "resource", "explore.altos.escarpa.liquen_pedreira",
            25, "Líquen de Pedreira cresce junto à rocha protegida.", min_level=41,
        ),
        ExplorationResultDefinition(
            "cinza_basalto", "resource", "explore.altos.escarpa.cinza_basalto",
            15, "Cinza de Basalto pode ser recolhida entre as pedras.", min_level=41,
        ),
        ExplorationResultDefinition(
            "pilares_silencio", "atmospheric", "explore.altos.escarpa.pilares_silencio",
            34, "Pilares permanecem em silêncio acima da passagem.", min_level=41,
        ),
        ExplorationResultDefinition(
            "poeira_cornija", "atmospheric", "explore.altos.escarpa.poeira_cornija",
            33, "Poeira se acumula sobre a cornija.", min_level=41,
        ),
        ExplorationResultDefinition(
            "cabo_sem_tensao", "atmospheric", "explore.altos.escarpa.cabo_sem_tensao",
            33, "Um cabo permanece sem tensão junto ao contraforte.", min_level=41,
        ),
    ),
)

ALTOS_PONTES_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=ALTOS_PONTES_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition(
            "braseiro_ponte_alta", "great_discovery",
            "explore.altos.pontes.braseiro_ponte_alta", 50,
            "O Braseiro da Ponte Alta foi descoberto entre as estruturas de travessia.",
            min_level=43, unique=True,
        ),
        ExplorationResultDefinition(
            "plataforma_contrapeso", "great_discovery",
            "explore.altos.pontes.plataforma_contrapeso", 50,
            "A Plataforma de Contrapeso Externa foi registrada.",
            min_level=43, unique=True,
        ),
        ExplorationResultDefinition(
            "livro_prioridades", "knowledge",
            "explore.altos.pontes.livro_prioridades", 55,
            "O Livro de Prioridades de Travessia registra a existência de prioridades.",
            min_level=43, unique=True,
        ),
        ExplorationResultDefinition(
            "marcas_cabos", "knowledge",
            "explore.altos.pontes.marcas_cabos", 45,
            "Marcas nos Cabos foram observadas nas Pontes de Fuligem.",
            min_level=43,
        ),
        ExplorationResultDefinition(
            "corda_substituicao", "narrative",
            "explore.altos.pontes.corda_substituicao", 55,
            "Uma Corda de Substituição permanece junto à passagem.",
            min_level=43,
        ),
        ExplorationResultDefinition(
            "sinal_retorno", "narrative",
            "explore.altos.pontes.sinal_retorno", 45,
            "Um Sinal de Retorno aponta para a rota atravessada.",
            min_level=43,
        ),
        ExplorationResultDefinition(
            "lobo_escarpa", "combat",
            "explore.altos.pontes.combat.lobo_escarpa", 15,
            "Um Lobo de Escarpa surge na passarela.", min_level=43,
            creature_id=ALTOS_LOBO_ESCARPA,
        ),
        ExplorationResultDefinition(
            "abutre_fuligem", "combat",
            "explore.altos.pontes.combat.abutre_fuligem", 15,
            "Um Abutre da Fuligem desce sobre as Pontes.", min_level=43,
            creature_id=ALTOS_ABUTRE_FULIGEM,
        ),
        ExplorationResultDefinition(
            "carneiro_peso", "combat",
            "explore.altos.pontes.combat.carneiro_peso", 25,
            "Um Carneiro do Peso bloqueia a passarela.", min_level=43,
            creature_id=ALTOS_CARNEIRO_PESO,
        ),
        ExplorationResultDefinition(
            "quebra_cabos", "combat",
            "explore.altos.pontes.combat.quebra_cabos", 25,
            "Um Quebra-Cabos rompe a tensão de uma estrutura próxima.", min_level=43,
            creature_id=ALTOS_QUEBRA_CABOS,
        ),
        ExplorationResultDefinition(
            "lagarto_escoria", "combat",
            "explore.altos.pontes.combat.lagarto_escoria", 20,
            "Um Lagarto de Escória atravessa a passarela.", min_level=43,
            creature_id=ALTOS_LAGARTO_ESCORIA,
        ),
        ExplorationResultDefinition(
            "ferro_contrapeso", "resource",
            "explore.altos.pontes.ferro_contrapeso", 35,
            "Ferro de Contrapeso pode ser recolhido entre os cabos.", min_level=43,
        ),
        ExplorationResultDefinition(
            "couro_escarpa", "resource",
            "explore.altos.pontes.couro_escarpa", 20,
            "Couro de Escarpa pode ser recolhido no local.", min_level=43,
        ),
        ExplorationResultDefinition(
            "liquen_pedreira", "resource",
            "explore.altos.pontes.liquen_pedreira", 25,
            "Líquen de Pedreira cresce entre as pedras protegidas.", min_level=43,
        ),
        ExplorationResultDefinition(
            "cinza_basalto", "resource",
            "explore.altos.pontes.cinza_basalto", 20,
            "Cinza de Basalto pode ser recolhida entre as estruturas.", min_level=43,
        ),
        ExplorationResultDefinition(
            "fuligem_vento", "atmospheric",
            "explore.altos.pontes.fuligem_vento", 34,
            "A fuligem se desloca pelo vento entre as passarelas.", min_level=43,
        ),
        ExplorationResultDefinition(
            "contrapeso_imovel", "atmospheric",
            "explore.altos.pontes.contrapeso_imovel", 33,
            "Um contrapeso permanece imóvel sobre a estrutura.", min_level=43,
        ),
        ExplorationResultDefinition(
            "passarela_longa", "atmospheric",
            "explore.altos.pontes.passarela_longa", 33,
            "A passarela se estende sobre o vão entre as encostas.", min_level=43,
        ),
    ),
)

ALTOS_PEDREIRAS_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=ALTOS_PEDREIRAS_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition(
            "braseiro_pedreira_velha", "great_discovery",
            "explore.altos.pedreiras.braseiro_pedreira_velha", 50,
            "O Braseiro da Pedreira Velha foi descoberto entre as estruturas suspensas.",
            min_level=45, unique=True,
        ),
        ExplorationResultDefinition(
            "entrada_contrapeso", "great_discovery",
            "explore.altos.pedreiras.entrada_contrapeso", 50,
            "A Entrada da Pedreira do Contrapeso foi registrada.",
            min_level=45, unique=True,
        ),
        ExplorationResultDefinition(
            "mapa_extracao", "knowledge",
            "explore.altos.pedreiras.mapa_extracao", 60,
            "O Mapa de Extração Recortado foi registrado no Códice.",
            min_level=45, unique=True,
        ),
        ExplorationResultDefinition(
            "marcas_peso", "knowledge",
            "explore.altos.pedreiras.marcas_peso", 40,
            "Marcas de peso foram observadas nas Pedreiras Suspensas.", min_level=45,
        ),
        ExplorationResultDefinition(
            "bloco_suspenso", "narrative",
            "explore.altos.pedreiras.bloco_suspenso", 55,
            "Um bloco permanece suspenso sobre a rota.", min_level=45,
        ),
        ExplorationResultDefinition(
            "trilho_interrompido", "narrative",
            "explore.altos.pedreiras.trilho_interrompido", 45,
            "Um trilho interrompido marca a distribuição das cargas.", min_level=45,
        ),
        ExplorationResultDefinition(
            "escaravelho_basalto", "combat",
            "explore.altos.pedreiras.combat.escaravelho_basalto", 18,
            "Um Escaravelho de Basalto bloqueia a rota.", min_level=45,
            creature_id=ALTOS_ESCARAVELHO_BASALTO,
        ),
        ExplorationResultDefinition(
            "carneiro_peso", "combat",
            "explore.altos.pedreiras.combat.carneiro_peso", 17,
            "Um Carneiro do Peso surge entre as estruturas.", min_level=45,
            creature_id=ALTOS_CARNEIRO_PESO,
        ),
        ExplorationResultDefinition(
            "lagarto_escoria", "combat",
            "explore.altos.pedreiras.combat.lagarto_escoria", 25,
            "Um Lagarto de Escória ocupa a passagem.", min_level=45,
            creature_id=ALTOS_LAGARTO_ESCORIA,
        ),
        ExplorationResultDefinition(
            "morcego_chamine", "combat",
            "explore.altos.pedreiras.combat.morcego_chamine", 18,
            "Um Morcego de Chaminé desce sobre a rota.", min_level=45,
            creature_id=ALTOS_MORCEGO_CHAMINE,
        ),
        ExplorationResultDefinition(
            "carcaca_mineral", "combat",
            "explore.altos.pedreiras.combat.carcaca_mineral", 22,
            "Uma Carcaça Mineral bloqueia a passagem.", min_level=45,
            creature_id=ALTOS_CARCACA_MINERAL,
        ),
        ExplorationResultDefinition(
            "ferro_contrapeso", "resource",
            "explore.altos.pedreiras.ferro_contrapeso", 35,
            "Ferro de Contrapeso pode ser recolhido entre as estruturas.", min_level=45,
        ),
        ExplorationResultDefinition(
            "cinza_basalto", "resource",
            "explore.altos.pedreiras.cinza_basalto", 30,
            "Cinza de Basalto pode ser recolhida entre as pedras.", min_level=45,
        ),
        ExplorationResultDefinition(
            "couro_escarpa", "resource",
            "explore.altos.pedreiras.couro_escarpa", 20,
            "Couro de Escarpa pode ser recolhido no local.", min_level=45,
        ),
        ExplorationResultDefinition(
            "liquen_pedreira", "resource",
            "explore.altos.pedreiras.liquen_pedreira", 15,
            "Líquen de Pedreira cresce junto à rocha protegida.", min_level=45,
        ),
        ExplorationResultDefinition(
            "poeira_clara", "atmospheric",
            "explore.altos.pedreiras.poeira_clara", 34,
            "Poeira clara atravessa a plataforma vazia.", min_level=45,
        ),
        ExplorationResultDefinition(
            "plataforma_vazia", "atmospheric",
            "explore.altos.pedreiras.plataforma_vazia", 33,
            "Uma plataforma vazia permanece suspensa sobre o vão.", min_level=45,
        ),
        ExplorationResultDefinition(
            "corrente_abismo", "atmospheric",
            "explore.altos.pedreiras.corrente_sobre_abismo", 33,
            "Uma corrente atravessa o abismo entre as estruturas.", min_level=45,
        ),
    ),
)

ALTOS_BASTILHA_EXPLORATION_PROFILE = ExplorationLocationProfile(
    local_id=ALTOS_BASTILHA_LOCATION,
    category_weights=tuple(EXPLORATION_CATEGORY_WEIGHTS.items()),
    results=(
        ExplorationResultDefinition(
            "braseiro_externo", "great_discovery",
            "explore.altos.bastilha.braseiro_externo", 50,
            "O Braseiro da Bastilha Externa foi descoberto.",
            min_level=47, unique=True,
        ),
        ExplorationResultDefinition(
            "entrada_profunda", "great_discovery",
            "explore.altos.bastilha.entrada_profunda", 50,
            "A Entrada da Bastilha Profunda foi registrada.",
            min_level=47, unique=True,
        ),
        ExplorationResultDefinition(
            "tabela_validade", "knowledge",
            "explore.altos.bastilha.tabela_validade", 60,
            "A Tabela de Validade de Ordens foi registrada.",
            min_level=47, unique=True,
        ),
        ExplorationResultDefinition(
            "selos_reemitidos", "knowledge",
            "explore.altos.bastilha.selos_reemitidos", 40,
            "Selos reemitidos foram observados na Bastilha.", min_level=47,
        ),
        ExplorationResultDefinition(
            "porta_prioridade", "narrative",
            "explore.altos.bastilha.porta_prioridade", 55,
            "Uma porta registra uma prioridade de acesso.", min_level=47,
        ),
        ExplorationResultDefinition(
            "arquivo_sem_destino", "narrative",
            "explore.altos.bastilha.arquivo_sem_destino", 45,
            "Um arquivo permanece sem destino registrado.", min_level=47,
        ),
        ExplorationResultDefinition(
            "morcego_chamine", "combat",
            "explore.altos.bastilha.combat.morcego_chamine", 15,
            "Um Morcego de Chaminé surge entre as passarelas.", min_level=47,
            creature_id=ALTOS_MORCEGO_CHAMINE,
        ),
        ExplorationResultDefinition(
            "carcaca_mineral", "combat",
            "explore.altos.bastilha.combat.carcaca_mineral", 20,
            "Uma Carcaça Mineral bloqueia o acesso.", min_level=47,
            creature_id=ALTOS_CARCACA_MINERAL,
        ),
        ExplorationResultDefinition(
            "quebra_cabos", "combat",
            "explore.altos.bastilha.combat.quebra_cabos", 25,
            "Um Quebra-Cabos ocupa a passagem.", min_level=47,
            creature_id=ALTOS_QUEBRA_CABOS,
        ),
        ExplorationResultDefinition(
            "vigia_carga", "combat",
            "explore.altos.bastilha.combat.vigia_carga", 40,
            "Um Vigia de Carga guarda a rota.", min_level=47,
            creature_id=ALTOS_VIGIA_CARGA,
        ),
        ExplorationResultDefinition(
            "ferro_contrapeso", "resource",
            "explore.altos.bastilha.ferro_contrapeso", 40,
            "Ferro de Contrapeso pode ser recolhido na Bastilha.", min_level=47,
        ),
        ExplorationResultDefinition(
            "cinza_basalto", "resource",
            "explore.altos.bastilha.cinza_basalto", 35,
            "Cinza de Basalto pode ser recolhida na Bastilha.", min_level=47,
        ),
        ExplorationResultDefinition(
            "liquen_pedreira", "resource",
            "explore.altos.bastilha.liquen_pedreira", 15,
            "Líquen de Pedreira cresce entre as estruturas.", min_level=47,
        ),
        ExplorationResultDefinition(
            "couro_escarpa", "resource",
            "explore.altos.bastilha.couro_escarpa", 10,
            "Couro de Escarpa pode ser recolhido no local.", min_level=47,
        ),
        ExplorationResultDefinition(
            "correntes_vazio", "atmospheric",
            "explore.altos.bastilha.correntes_vazio", 34,
            "Correntes permanecem suspensas no vazio.", min_level=47,
        ),
        ExplorationResultDefinition(
            "pedra_administrativa", "atmospheric",
            "explore.altos.bastilha.pedra_administrativa", 33,
            "Uma pedra conserva marcas administrativas.", min_level=47,
        ),
        ExplorationResultDefinition(
            "sala_sem_turno", "atmospheric",
            "explore.altos.bastilha.sala_sem_turno", 33,
            "Uma sala permanece sem turno designado.", min_level=47,
        ),
    ),
)

EXPLORATION_PROFILES = {
    ROAD_LOCATION: ROAD_EXPLORATION_PROFILE,
    CHARNECA_LOCATION: CHARNECA_EXPLORATION_PROFILE,
    BOSQUE_LOCATION: BOSQUE_EXPLORATION_PROFILE,
    RUINS_LOCATION: RUINS_EXPLORATION_PROFILE,
    VDE_GARGANTA_LOCATION: VDE_GARGANTA_EXPLORATION_PROFILE,
    VDE_MATA_LOCATION: VDE_MATA_EXPLORATION_PROFILE,
    VDE_BAIXIOS_LOCATION: VDE_BAIXIOS_EXPLORATION_PROFILE,
    VDE_CLAUSTRO_LOCATION: VDE_CLAUSTRO_EXPLORATION_PROFILE,
    NARETH_CAMPINAS_LOCATION: NARETH_CAMPINAS_EXPLORATION_PROFILE,
    NARETH_CANAIS_LOCATION: NARETH_CANAIS_EXPLORATION_PROFILE,
    NARETH_CAMPOS_LOCATION: NARETH_CAMPOS_EXPLORATION_PROFILE,
    NARETH_OBSERVATORIO_LOCATION: NARETH_OBSERVATORIO_EXPLORATION_PROFILE,
    VARZEAS_DIQUES_LOCATION: VARZEAS_DIQUES_EXPLORATION_PROFILE,
    VARZEAS_BREJOS_LOCATION: VARZEAS_BREJOS_EXPLORATION_PROFILE,
    VARZEAS_HORTOS_LOCATION: VARZEAS_HORTOS_EXPLORATION_PROFILE,
    VARZEAS_GALERIAS_LOCATION: VARZEAS_GALERIAS_EXPLORATION_PROFILE,
    ALTOS_ESCARPA_LOCATION: ALTOS_ESCARPA_EXPLORATION_PROFILE,
    ALTOS_PONTES_LOCATION: ALTOS_PONTES_EXPLORATION_PROFILE,
    ALTOS_PEDREIRAS_LOCATION: ALTOS_PEDREIRAS_EXPLORATION_PROFILE,
    ALTOS_BASTILHA_LOCATION: ALTOS_BASTILHA_EXPLORATION_PROFILE,
}

HUNT_PROFILES = {
    ROAD_LOCATION: ROAD_PROFILE,
    CHARNECA_LOCATION: CHARNECA_PROFILE,
    BOSQUE_LOCATION: BOSQUE_PROFILE,
    RUINS_LOCATION: RUINS_PROFILE,
    VDE_GARGANTA_LOCATION: VDE_GARGANTA_PROFILE,
    VDE_MATA_LOCATION: VDE_MATA_PROFILE,
    VDE_BAIXIOS_LOCATION: VDE_BAIXIOS_PROFILE,
    VDE_CLAUSTRO_LOCATION: VDE_CLAUSTRO_PROFILE,
    NARETH_CAMPINAS_LOCATION: NARETH_CAMPINAS_PROFILE,
    NARETH_POSTO_LOCATION: NARETH_POSTO_PROFILE,
    NARETH_CANAIS_LOCATION: NARETH_CANAIS_PROFILE,
    NARETH_CAMPOS_LOCATION: NARETH_CAMPOS_PROFILE,
    NARETH_OBSERVATORIO_LOCATION: NARETH_OBSERVATORIO_PROFILE,
    VARZEAS_DIQUES_LOCATION: VARZEAS_DIQUES_PROFILE,
    VARZEAS_BREJOS_LOCATION: VARZEAS_BREJOS_PROFILE,
    VARZEAS_HORTOS_LOCATION: VARZEAS_HORTOS_PROFILE,
    VARZEAS_GALERIAS_LOCATION: VARZEAS_GALERIAS_PROFILE,
    ALTOS_ESCARPA_LOCATION: ALTOS_ESCARPA_PROFILE,
    ALTOS_PONTES_LOCATION: ALTOS_PONTES_PROFILE,
    ALTOS_PEDREIRAS_LOCATION: ALTOS_PEDREIRAS_PROFILE,
    ALTOS_BASTILHA_LOCATION: ALTOS_BASTILHA_PROFILE,
}
HUNT_PROFILES_BY_LABEL = {
    profile.label: profile for profile in HUNT_PROFILES.values()
}


def hunt_profile_for_location(location: str) -> HuntLocationProfile | None:
    return HUNT_PROFILES_BY_LABEL.get(location)


def hunt_profile_for_local_id(local_id: str | None) -> HuntLocationProfile:
    # Pre-PR-C round snapshots with no local_id are historical Road batches.
    if local_id in {None, ROAD_LOCATION, "Estrada das Cinzas"}:
        return ROAD_PROFILE
    return HUNT_PROFILES[local_id]


def creature_for(creature_id: str) -> Creature:
    return next(c for c in CREATURE_CATALOG if c.creature_id == creature_id)


def hunt_pool(
    player_level: int, profile: HuntLocationProfile = ROAD_PROFILE
) -> tuple[Creature, ...]:
    return tuple(
        creature_for(creature_id)
        for creature_id, _ in profile.creature_weights
        if player_level >= creature_for(creature_id).unlock_level
    )


def road_pool(player_level: int) -> tuple[Creature, ...]:
    return hunt_pool(player_level, ROAD_PROFILE)


def weighted_choice(seed: str, entries: tuple[tuple[str, int], ...]) -> str:
    total = sum(weight for _, weight in entries)
    value = int.from_bytes(sha256(seed.encode()).digest(), "big") % total
    for key, weight in entries:
        if value < weight:
            return key
        value -= weight
    return entries[-1][0]


def select_creature(
    seed: str, player_level: int, profile: HuntLocationProfile = ROAD_PROFILE
) -> Creature:
    eligible = tuple(
        (creature_id, weight)
        for creature_id, weight in profile.creature_weights
        if player_level >= creature_for(creature_id).unlock_level
    )
    if not eligible:
        raise ValueError(f"no eligible creatures for {profile.local_id} at level {player_level}")
    return creature_for(weighted_choice(seed, eligible))


def select_exploration_result(
    seed: str,
    player_level: int,
    recent: tuple[str, ...] = (),
    excluded: tuple[str, ...] = (),
    profile: ExplorationLocationProfile = ROAD_EXPLORATION_PROFILE,
) -> str:
    """Select one eligible local result, filtering level gates before the draw."""
    eligible_categories = []
    eligible_subweights = {}
    excluded_set = set(excluded)
    for category, weight in profile.category_weights:
        results = tuple(
            result
            for result in profile.results
            if result.category == category
            and player_level >= result.min_level
            and (result.creature_id is None or player_level >= creature_for(result.creature_id).unlock_level)
            and result.key not in excluded_set
            and result.result_id not in excluded_set
        )
        # Apply the result-specific repeat penalty before keeping its parent
        # category eligible. An exhausted unique result never gets selected.
        adjusted = tuple(
            (result.key, anti_repeat_weight(result.weight, result.key, recent))
            for result in results
        )
        adjusted = tuple((key, value) for key, value in adjusted if value > 0)
        if adjusted:
            eligible_categories.append((category, weight))
            eligible_subweights[category] = adjusted
    category = weighted_recent_choice(seed, tuple(eligible_categories), recent)
    return weighted_choice(f"{seed}:category:{category}", eligible_subweights[category])


def select_variant(
    seed: str,
    creature: Creature,
    profile: HuntLocationProfile = ROAD_PROFILE,
) -> str | None:
    if not VARIANT_POOL[creature.creature_id]:
        return None
    chance = int.from_bytes(sha256(f"{seed}:variant.chance".encode()).digest(), "big") % 100
    if chance >= profile.variant_chance:
        return None
    family = int.from_bytes(sha256(f"{seed}:variant.family".encode()).digest(), "big")
    return VARIANT_POOL[creature.creature_id][family % len(VARIANT_POOL[creature.creature_id])]


def road_enemy_stats(creature: Creature, level: int, variant: str | None = None) -> CombatStats:
    factors = [CATEGORY[creature.category], ARCHETYPE[creature.archetype]]
    if variant:
        factors.append(VARIANTS[variant])
    return enemy_stats(level, *factors)


def enemy_xp(
    level: int,
    category: str,
    vigor_factor: Decimal | None = None,
    player_level: int | None = None,
    powerlevel_factor: Decimal | None = None,
    participation_factor: Decimal | None = None,
    legacy_factor: Decimal | None = None,
) -> int:
    with localcontext() as ctx:
        ctx.prec = 50
        xp = (D(4000) + D(750) * level + D(43) * level * level).quantize(
            D("1E2"), rounding="ROUND_HALF_EVEN"
        )
        h = D("0.905903") + D("0.094097") * level
        category_factor = {
            "common": D("1.00"),
            "uncommon": D("1.35"),
            "elite": D("2.75"),
            "boss": D("6.00"),
        }[category]
        delta = level - (level if player_level is None else player_level)
        level_factor = (
            D("1.10") if delta >= 5 else D("1.05") if delta >= 3 else
            D("0.80") if delta <= -3 and delta >= -5 else
            D("0.50") if delta <= -6 and delta >= -10 else
            D("0.20") if delta <= -11 and delta >= -20 else
            D("0.05") if delta <= -21 else D(1)
        )
        value = (
            xp / (D(20) * h) * category_factor * level_factor * (powerlevel_factor or D(1))
            * (participation_factor or D(1)) * (vigor_factor or D(1)) * (legacy_factor or D(1))
        )
        return int((value / 10).quantize(D(1), rounding="ROUND_HALF_EVEN") * 10)


def crowns(level: int, category: str) -> int:
    value = D(100) + D(15) * level
    factor = {
        "common": D("0.05"),
        "uncommon": D("0.08"),
        "elite": D("0.25"),
        "boss": D("0.60"),
    }[category]
    return int(((value * factor) / 10).quantize(D(1), rounding="ROUND_HALF_EVEN") * 10)


VDE_BASIC_MATERIAL_CREATURE_IDS = frozenset(
    {
        "lobo_musgoso",
        "gralha_vale",
        "peregrino_enredado",
        "aranha_cipo",
        "cervo_no",
        "sanguessuga_turfa",
        "casca_errante",
        "mariposa_breu_verde",
        "vigia_enraizado",
        "no_feroz",
        "viuva_cipos",
        "carrasco_casca",
    }
)

NARETH_BASIC_MATERIAL_CREATURE_IDS = frozenset(
    {
        "galgo_meridiano",
        "abutre_marco",
        "errante_valas",
        "escaravelho_canal",
        "cervo_horizonte",
        "serpe_campinas",
        "casco_invertido",
        "mariposa_eixo",
        "vigia_meridiano",
        "alfa_horizonte",
        "serpe_eixo",
        "custodio_invertido",
    }
)
VARZEAS_BASIC_MATERIAL_CREATURE_IDS = frozenset(
    {
        "cao_salmoura",
        "garca_ferruginosa",
        "portador_rubro",
        "alfa_salmoura",
        "aranha_junco",
        "cervo_ferrugem",
        "viuva_rubra",
        "lampreia_varzea",
        "enxerto_horto",
        "mariposa_soro",
        "coletor_hematico",
        "vigia_hemaris",
    }
)

ALTOS_BASIC_MATERIAL_CREATURE_IDS = frozenset(
    {
        ALTOS_LOBO_ESCARPA,
        ALTOS_ABUTRE_FULIGEM,
        ALTOS_ESCARAVELHO_BASALTO,
        ALTOS_CARNEIRO_PESO,
        ALTOS_QUEBRA_ESCARPAS,
        ALTOS_LAGARTO_ESCORIA,
        ALTOS_QUEBRA_CABOS,
        ALTOS_DEVORADOR_ESCORIA,
        ALTOS_MORCEGO_CHAMINE,
        ALTOS_CARCACA_MINERAL,
        ALTOS_VIGIA_CARGA,
        ALTOS_SUPERVISOR_CARGA,
    }
)

MATERIAL_POOLS = {
    "dog_cinereo": (("material.tdo.couro_escoriado", 100),),
    "alfa_cinereo": (("material.tdo.couro_escoriado", 100),),
    "corvo_fuligem": (("material.tdo.residuo_ocaso", 100),),
    "peregrino_calcinado": (
        ("material.tdo.ferro_de_fuligem", 1),
        ("material.tdo.erva_cinzenta", 1),
    ),
    "aranha_cinza": (
        ("material.tdo.erva_cinzenta", 50),
        ("material.tdo.residuo_ocaso", 50),
    ),
    "cervo_escoriado": (("material.tdo.couro_escoriado", 100),),
    "carnical_fuligem": (
        ("material.tdo.ferro_de_fuligem", 50),
        ("material.tdo.residuo_ocaso", 50),
    ),
    "mariposa_brasa": (
        ("material.tdo.erva_cinzenta", 50),
        ("material.tdo.residuo_ocaso", 50),
    ),
    "viuva_fuligem": (
        ("material.tdo.erva_cinzenta", 50),
        ("material.tdo.residuo_ocaso", 50),
    ),
    "vigia_rachado": (("material.tdo.ferro_de_fuligem", 50), ("material.tdo.residuo_ocaso", 50)),
    "custodio_sem_rosto": (("material.tdo.ferro_de_fuligem", 50), ("material.tdo.residuo_ocaso", 50)),
    "custodio_poente": (("material.tdo.ferro_de_fuligem", 50), ("material.tdo.residuo_ocaso", 50)),
    # The Vales table selects the identity of each already-awarded basic
    # material unit. The caller supplies an independent stable seed per unit.
    "lobo_musgoso": (("material.vde.couro_musgoso", 100),),
    "gralha_vale": (
        ("material.vde.erva_de_turfa", 70),
        ("material.vde.resina_enredada", 30),
    ),
    "peregrino_enredado": (
        ("material.vde.ferro_enredado", 70),
        ("material.vde.resina_enredada", 30),
    ),
    "aranha_cipo": (
        ("material.vde.erva_de_turfa", 60),
        ("material.vde.resina_enredada", 40),
    ),
    "cervo_no": (("material.vde.couro_musgoso", 100),),
    "sanguessuga_turfa": (
        ("material.vde.erva_de_turfa", 80),
        ("material.vde.resina_enredada", 20),
    ),
    "casca_errante": (
        ("material.vde.resina_enredada", 80),
        ("material.vde.erva_de_turfa", 20),
    ),
    "mariposa_breu_verde": (
        ("material.vde.erva_de_turfa", 65),
        ("material.vde.resina_enredada", 35),
    ),
    "vigia_enraizado": (
        ("material.vde.ferro_enredado", 90),
        ("material.vde.resina_enredada", 10),
    ),
    "no_feroz": (
        ("material.vde.couro_musgoso", 80),
        ("material.vde.resina_enredada", 20),
    ),
    "viuva_cipos": (
        ("material.vde.erva_de_turfa", 60),
        ("material.vde.resina_enredada", 40),
    ),
    "carrasco_casca": (
        ("material.vde.resina_enredada", 70),
        ("material.vde.ferro_enredado", 30),
    ),
    # Nareth weights select each already-awarded basic material unit; the
    # global chance and quantity are resolved before these independent draws.
    "galgo_meridiano": (("material.nareth.couro_de_horizonte", 100),),
    "abutre_marco": (
        ("material.nareth.erva_de_vento", 65),
        ("material.nareth.po_de_eixo", 35),
    ),
    "errante_valas": (
        ("material.nareth.bronze_de_marco", 65),
        ("material.nareth.po_de_eixo", 35),
    ),
    "escaravelho_canal": (
        ("material.nareth.erva_de_vento", 55),
        ("material.nareth.po_de_eixo", 45),
    ),
    "cervo_horizonte": (("material.nareth.couro_de_horizonte", 100),),
    "serpe_campinas": (
        ("material.nareth.erva_de_vento", 75),
        ("material.nareth.couro_de_horizonte", 25),
    ),
    "casco_invertido": (
        ("material.nareth.couro_de_horizonte", 80),
        ("material.nareth.po_de_eixo", 20),
    ),
    "mariposa_eixo": (
        ("material.nareth.po_de_eixo", 70),
        ("material.nareth.erva_de_vento", 30),
    ),
    "vigia_meridiano": (
        ("material.nareth.bronze_de_marco", 90),
        ("material.nareth.po_de_eixo", 10),
    ),
    "alfa_horizonte": (
        ("material.nareth.couro_de_horizonte", 85),
        ("material.nareth.po_de_eixo", 15),
    ),
    "serpe_eixo": (
        ("material.nareth.erva_de_vento", 60),
        ("material.nareth.po_de_eixo", 40),
    ),
    "custodio_invertido": (
        ("material.nareth.bronze_de_marco", 75),
        ("material.nareth.po_de_eixo", 25),
    ),
    "cao_salmoura": (("material.varzeas.couro_de_varzea", 100),),
    "garca_ferruginosa": (
        ("material.varzeas.junco_ferruginoso", 70),
        ("material.varzeas.soro_antigo", 30),
    ),
    "portador_rubro": (
        ("material.varzeas.soro_antigo", 70),
        ("material.varzeas.ferro_de_salmoura", 30),
    ),
    "alfa_salmoura": (
        ("material.varzeas.couro_de_varzea", 80),
        ("material.varzeas.soro_antigo", 20),
    ),
    "aranha_junco": (
        ("material.varzeas.junco_ferruginoso", 65),
        ("material.varzeas.soro_antigo", 35),
    ),
    "cervo_ferrugem": (("material.varzeas.couro_de_varzea", 100),),
    "viuva_rubra": (
        ("material.varzeas.junco_ferruginoso", 60),
        ("material.varzeas.soro_antigo", 40),
    ),
    "lampreia_varzea": (
        ("material.varzeas.junco_ferruginoso", 75),
        ("material.varzeas.soro_antigo", 25),
    ),
    "enxerto_horto": (
        ("material.varzeas.soro_antigo", 80),
        ("material.varzeas.junco_ferruginoso", 20),
    ),
    "mariposa_soro": (
        ("material.varzeas.soro_antigo", 65),
        ("material.varzeas.junco_ferruginoso", 35),
    ),
    "coletor_hematico": (
        ("material.varzeas.soro_antigo", 70),
        ("material.varzeas.ferro_de_salmoura", 30),
    ),
    "vigia_hemaris": (
        ("material.varzeas.ferro_de_salmoura", 90),
        ("material.varzeas.soro_antigo", 10),
    ),
    ALTOS_LOBO_ESCARPA: ((ALTOS_COURO_ESCARPA, 100),),
    ALTOS_ABUTRE_FULIGEM: (
        (ALTOS_LIQUEN_PEDREIRA, 60),
        (ALTOS_CINZA_BASALTO, 40),
    ),
    ALTOS_ESCARAVELHO_BASALTO: (
        (ALTOS_CINZA_BASALTO, 60),
        (ALTOS_FERRO_CONTRAPESO, 40),
    ),
    ALTOS_CARNEIRO_PESO: (
        (ALTOS_COURO_ESCARPA, 80),
        (ALTOS_CINZA_BASALTO, 20),
    ),
    ALTOS_QUEBRA_ESCARPAS: (
        (ALTOS_COURO_ESCARPA, 85),
        (ALTOS_CINZA_BASALTO, 15),
    ),
    ALTOS_LAGARTO_ESCORIA: ((ALTOS_COURO_ESCARPA, 70), (ALTOS_CINZA_BASALTO, 30)),
    ALTOS_QUEBRA_CABOS: ((ALTOS_LIQUEN_PEDREIRA, 65), (ALTOS_COURO_ESCARPA, 35)),
    ALTOS_DEVORADOR_ESCORIA: ((ALTOS_COURO_ESCARPA, 70), (ALTOS_CINZA_BASALTO, 30)),
    ALTOS_MORCEGO_CHAMINE: (
        (ALTOS_COURO_ESCARPA, 60),
        (ALTOS_LIQUEN_PEDREIRA, 40),
    ),
    ALTOS_CARCACA_MINERAL: (
        (ALTOS_CINZA_BASALTO, 70),
        (ALTOS_FERRO_CONTRAPESO, 30),
    ),
    ALTOS_VIGIA_CARGA: (
        (ALTOS_FERRO_CONTRAPESO, 90),
        (ALTOS_CINZA_BASALTO, 10),
    ),
    ALTOS_SUPERVISOR_CARGA: (
        (ALTOS_FERRO_CONTRAPESO, 75),
        (ALTOS_CINZA_BASALTO, 25),
    ),
}


def material_for(creature_id: str, seed: str) -> str:
    pool = MATERIAL_POOLS.get(creature_id)
    if pool is None:
        raise ValueError(f"no creature material pool configured for {creature_id!r}")
    return weighted_choice(seed, pool)


def create_road_combat(
    combat_id: UUID,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    creature: Creature,
    level: int,
    variant: str | None,
    player_level: int | None = None,
    equipment_configuration: EquipmentConfigurationSnapshot | None = None,
    ruleset_version: str | None = None,
    location_label: str = "Estrada das Cinzas",
    active_art_ids: tuple[str, ...] | None = None,
) -> Combat:
    flavor = (
        "A Estrada guarda ameaças entre as cinzas."
        if location_label == "Estrada das Cinzas"
        else f"A {location_label} guarda ameaças entre as cinzas."
    )
    opening_log = (
        f"🦌 {creature.name} surge entre a fuligem."
        if location_label == "Estrada das Cinzas"
        else f"🦌 {creature.name} surge na região."
    )
    return create_creature_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        creature,
        level,
        variant,
        player_level=player_level,
        equipment_configuration=equipment_configuration,
        ruleset_version=ruleset_version,
        flavor=flavor,
        opening_log=opening_log,
        active_art_ids=active_art_ids,
    )


def create_creature_combat(
    combat_id: UUID,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    creature: Creature,
    level: int,
    variant: str | None,
    player_level: int | None = None,
    equipment_configuration: EquipmentConfigurationSnapshot | None = None,
    ruleset_version: str | None = None,
    flavor: str = "",
    opening_log: str = "",
    active_art_ids: tuple[str, ...] | None = None,
) -> Combat:
    return create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        (CreatureCombatantSpec(creature, level, "enemy", variant),),
        player_level=player_level,
        equipment_configuration=equipment_configuration,
        ruleset_version=ruleset_version,
        flavor=flavor,
        opening_log=opening_log,
        active_art_ids=active_art_ids,
    )


@dataclass(frozen=True)
class CreatureCombatantSpec:
    creature: Creature
    level: int
    fighter_key: str
    variant: str | None = None
    stat_multipliers: StatMultipliers | None = None
    campaign_boss_group_size: int | None = None
    passive: bool = False
    required_for_victory: bool = True
    defeat_on_zero: bool = False
    initially_inactive: bool = False


@dataclass(frozen=True)
class PlayerCombatantSpec:
    """One dungeon party member with a frozen individual combat setup."""

    fighter_key: str
    character_id: str
    name: str
    character_class: str
    race: str
    level: int
    hp: Decimal
    equipment_configuration: EquipmentConfigurationSnapshot
    active_art_ids: tuple[str, ...]
    active: bool = True
    active_art_snapshots: tuple[dict, ...] = ()


def create_player_versus_player_combat(
    combat_id: UUID,
    left: tuple[PlayerCombatantSpec, ...],
    right: tuple[PlayerCombatantSpec, ...],
    *,
    ruleset_version: str | None = None,
    flavor: str = "",
    opening_log: str = "",
) -> Combat:
    """Create a shared manual-vs-manual combat using each real frozen setup."""
    if not 1 <= len(left) <= 4 or len(left) != len(right):
        raise ValueError("PvPvE collision sides must have equal size from one to four.")
    participants = (*left, *right)
    if len({item.character_id for item in participants}) != len(participants):
        raise ValueError("A character cannot occupy both sides of a PvP collision.")
    runtime_ruleset = ruleset_version or RULESET
    fighters: dict[str, Fighter] = {}
    actions_by_fighter: dict[str, dict[str, Action]] = {}
    configuration_snapshots: dict[str, dict] = {}
    first_actions: dict[str, Action] | None = None
    for side, roster in (("player", left), ("enemy", right)):
        for member in roster:
            equipment = member.equipment_configuration
            talent_ids = tuple(talent_id for _, talent_id in equipment.talent_choices)
            stats = resolve_combat_stats(
                member.character_class,
                member.level,
                member.race,
                equipment.contribution(),
                equipment.selected_path,
                talent_ids,
            )
            actions = class_player_actions(member.character_class, member.active_art_ids)
            actions_by_fighter[member.fighter_key] = actions
            first_actions = first_actions or actions
            configuration_snapshots[member.fighter_key] = (
                equipment.to_data(runtime_ruleset)
                | {"active_arts": list(member.active_art_snapshots)}
            )
            fighters[member.fighter_key] = Fighter(
                id=member.character_id,
                name=member.name,
                level=member.level,
                stats=stats,
                hp=member.hp,
                race=member.race,
                character_class=member.character_class,
                selected_path=equipment.selected_path,
                talent_ids=talent_ids,
                side=side,
                takes_turn=member.active,
                defeat_on_zero=False,
                required_for_victory=(side == "enemy"),
            )
    assert first_actions is not None
    return start_combat(
        Combat(
            combat_id,
            runtime_ruleset,
            fighters=fighters,
            player_actions=first_actions,
            enemy_actions={},
            ai_cycle=(),
            flavor=flavor,
            opening_log=opening_log,
            player_actions_by_fighter=actions_by_fighter,
            player_configuration_snapshots=configuration_snapshots,
            party_mode=True,
            manual_sides=("player", "enemy"),
            external_consumables_allowed=False,
        )
    )


def _creature_actions(
    creature: Creature,
    prefix: str = "",
    *,
    actor_hp: Decimal | None = None,
    actor_attack: Decimal | None = None,
) -> tuple[dict[str, Action], tuple[str, ...], tuple[str, ...]]:
    actions: dict[str, Action] = {}
    key_map: dict[str, str] = {}
    for specification in creature.actions:
        key, label, coefficient, blocked_opportunities, debuff, duration = specification[:6]
        actual_key = f"{prefix}{key}"
        key_map[key] = actual_key
        native_dot_kind = specification[6] if len(specification) > 6 else None
        native_dot_stacks = specification[7] if len(specification) > 7 else 0
        prepared = specification[8] if len(specification) > 8 else False
        canonical_cooldown = specification[9] if len(specification) > 9 else None
        effect_stat = specification[10] if len(specification) > 10 else None
        poison_per_bonus = specification[11] if len(specification) > 11 else D(0)
        self_barrier_coefficient = specification[12] if len(specification) > 12 else D(0)
        self_barrier_duration = specification[13] if len(specification) > 13 else 0
        skip_if_barrier_active = specification[14] if len(specification) > 14 else False
        target_mode = specification[15] if len(specification) > 15 else "opponent"
        enemy_hp_fraction_below = specification[16] if len(specification) > 16 and specification[16] is not None else None
        enemy_hp_fraction_at_most = specification[17] if len(specification) > 17 and specification[17] is not None else None
        max_uses_per_combat = specification[18] if len(specification) > 18 else None
        revive_fighter_keys = tuple(specification[19]) if len(specification) > 19 else ()
        requires_defeated_fighter_keys = tuple(specification[20]) if len(specification) > 20 else ()
        revive_hp_fraction = D(specification[21]) if len(specification) > 21 else D("0.50")
        self_barrier_hp_fraction = D(specification[22]) if len(specification) > 22 else D(0)
        actor_per_bonus = D(specification[23]) if len(specification) > 23 else D(0)
        actor_per_bonus_if_target_bleeding = (
            D(specification[24]) if len(specification) > 24 else D(0)
        )
        actor_per_bonus_if_target_hp_fraction_at_most = (
            D(specification[25]) if len(specification) > 25 else D(0)
        )
        actor_per_bonus_hp_fraction_threshold = (
            D(specification[26]) if len(specification) > 26 else D("0.40")
        )
        native_dot_stacks_if_target_poisoned = (
            specification[27] if len(specification) > 27 else 0
        )
        vampirism_fraction = D(specification[28]) if len(specification) > 28 else D(0)
        heal_coefficient = D(specification[29]) if len(specification) > 29 else D(0)
        heal_hp_fraction = D(specification[30]) if len(specification) > 30 else D(0)
        vampirism_cap_hp_fraction = (
            D(specification[31]) if len(specification) > 31 else None
        )
        if heal_hp_fraction > 0:
            if actor_hp is None or actor_attack is None or actor_attack <= 0:
                raise ValueError("HP-fraction creature healing requires resolved actor stats.")
            heal_coefficient = actor_hp * heal_hp_fraction / actor_attack
        actions[actual_key] = Action(
            actual_key,
            label,
            coefficient,
            blocked_opportunities,
            debuff,
            duration,
            native_dot_kind,
            native_dot_stacks,
            prepared,
            canonical_cooldown,
            effect_stat,
            poison_per_bonus,
            self_barrier_coefficient,
            self_barrier_duration,
            skip_if_barrier_active,
            target_mode=target_mode,
            enemy_hp_fraction_below=D(enemy_hp_fraction_below) if enemy_hp_fraction_below is not None else None,
            enemy_hp_fraction_at_most=D(enemy_hp_fraction_at_most) if enemy_hp_fraction_at_most is not None else None,
            max_uses_per_combat=max_uses_per_combat,
            revive_fighter_keys=revive_fighter_keys,
            requires_defeated_fighter_keys=requires_defeated_fighter_keys,
            revive_hp_fraction=revive_hp_fraction,
            self_barrier_hp_fraction=self_barrier_hp_fraction,
            actor_per_bonus=actor_per_bonus,
            actor_per_bonus_if_target_bleeding=actor_per_bonus_if_target_bleeding,
            actor_per_bonus_if_target_hp_fraction_at_most=(
                actor_per_bonus_if_target_hp_fraction_at_most
            ),
            actor_per_bonus_hp_fraction_threshold=actor_per_bonus_hp_fraction_threshold,
            native_dot_stacks_if_target_poisoned=native_dot_stacks_if_target_poisoned,
            vampirism_fraction=vampirism_fraction,
            vampirism_cap_hp_fraction=vampirism_cap_hp_fraction,
            heal_coefficient=heal_coefficient,
        )
    cycle = tuple(key_map[key] for key in creature.ai if key in key_map)
    priority = tuple(key_map[key] for key in creature.ai_priority if key in key_map)
    return actions, cycle, priority


def _apply_stat_multipliers(stats: CombatStats, factors: StatMultipliers) -> CombatStats:
    return CombatStats(
        stats.hp * factors.hp,
        stats.attack * factors.attack,
        stats.defense * factors.defense,
        stats.agility * factors.agility,
        stats.per,
        stats.crit,
        stats.evasion,
        stats.block,
    )


def create_creature_party_combat(
    combat_id: UUID,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    enemies: tuple[CreatureCombatantSpec, ...],
    *,
    player_level: int,
    equipment_configuration: EquipmentConfigurationSnapshot | None = None,
    ruleset_version: str | None = None,
    flavor: str = "",
    opening_log: str = "",
    active_art_ids: tuple[str, ...] | None = None,
    pressure_start_opportunity: int = 0,
    pressure_cap: int = 0,
    party: tuple[PlayerCombatantSpec, ...] | None = None,
) -> Combat:
    """Create a shared-engine combat with independent AI schedules per enemy."""
    if not enemies:
        raise ValueError("A creature combat requires at least one enemy entity.")
    player_level = enemies[0].level if player_level is None else player_level
    runtime_ruleset = ruleset_version or RULESET
    equipment = equipment_configuration
    player_stats = resolve_combat_stats(
        character_class,
        player_level,
        race,
        equipment.contribution() if equipment is not None else None,
        equipment.selected_path if equipment is not None else None,
        tuple(talent_id for _, talent_id in equipment.talent_choices)
        if equipment is not None
        else (),
    )
    talent_ids = (
        tuple(talent_id for _, talent_id in equipment.talent_choices)
        if equipment is not None
        else ()
    )
    actions: dict[str, Action] = {}
    fighters: dict[str, Fighter] = {}
    player_actions: dict[str, Action] = {}
    player_actions_by_fighter: dict[str, dict[str, Action]] = {}
    player_configuration_snapshots: dict[str, dict] = {}
    if party is not None and len(party) > 1:
        if len(party) > 4 or len({member.character_id for member in party}) != len(party):
            raise ValueError("Dungeon parties contain one to four unique characters.")
        for member in party:
            member_equipment = member.equipment_configuration
            member_stats = resolve_combat_stats(
                member.character_class,
                member.level,
                member.race,
                member_equipment.contribution(),
                member_equipment.selected_path,
                tuple(talent_id for _, talent_id in member_equipment.talent_choices),
            )
            member_actions = class_player_actions(
                member.character_class, member.active_art_ids
            )
            for action_id, action in member_actions.items():
                existing = player_actions.get(action_id)
                if existing is not None and existing != action:
                    raise ValueError("Party action ids must resolve to one canonical action.")
                player_actions[action_id] = action
            player_actions_by_fighter[member.fighter_key] = member_actions
            player_configuration_snapshots[member.fighter_key] = (
                member.equipment_configuration.to_data(runtime_ruleset)
                | {"active_arts": list(member.active_art_snapshots)}
            )
            fighters[member.fighter_key] = Fighter(
                id=member.character_id,
                name=member.name,
                level=member.level,
                stats=member_stats,
                hp=member.hp,
                race=member.race,
                character_class=member.character_class,
                selected_path=member_equipment.selected_path,
                talent_ids=tuple(talent_id for _, talent_id in member_equipment.talent_choices),
                side="player",
                takes_turn=member.active,
                defeat_on_zero=False,
                required_for_victory=False,
            )
    else:
        fighters["player"] = Fighter(
            "player", name, player_level, player_stats, hp, race, character_class,
            selected_path=(equipment.selected_path if equipment is not None else None),
            talent_ids=talent_ids,
        )
    ai_cycles: dict[str, tuple[str, ...]] = {}
    ai_positions: dict[str, int] = {}
    ai_priorities: dict[str, tuple[str, ...]] = {}
    for index, specification in enumerate(enemies):
        if specification.fighter_key in fighters:
            raise ValueError("Creature combat fighter keys must be unique.")
        creature = specification.creature
        prefix = "" if len(enemies) == 1 else f"e{index}_"
        base_stats = road_enemy_stats(
            creature, specification.level, specification.variant
        )
        if specification.campaign_boss_group_size is not None:
            from asterion.domain.campaign_combat import scale_campaign_boss_stats

            base_stats = scale_campaign_boss_stats(
                base_stats, specification.campaign_boss_group_size
            )
        elif specification.stat_multipliers is not None:
            base_stats = _apply_stat_multipliers(
                base_stats, specification.stat_multipliers
            )
        enemy_actions, cycle, priority = _creature_actions(
            creature,
            prefix,
            actor_hp=base_stats.hp,
            actor_attack=base_stats.attack,
        )
        actions.update(enemy_actions)
        fighters[specification.fighter_key] = Fighter(
            id=(
                "enemy"
                if len(enemies) == 1 and specification.fighter_key == "enemy"
                else f"dungeon:{creature.creature_id}:{index + 1}"
            ),
            name=creature.name,
            level=specification.level,
            stats=base_stats,
            hp=D(0) if specification.initially_inactive else base_stats.hp,
            side="enemy",
            takes_turn=not specification.passive,
            defeat_on_zero=specification.defeat_on_zero,
            required_for_victory=specification.required_for_victory,
            damage_taken_modifiers=dict(creature.damage_taken_modifiers),
        )
        ai_cycles[specification.fighter_key] = cycle
        ai_positions[specification.fighter_key] = 0
        ai_priorities[specification.fighter_key] = priority
    if not player_actions:
        player_actions = (
            {
                "attack": Action("attack", "⚔️ Atacar", D(1)),
                "art": first_art(character_class, 1),
            }
            if active_art_ids is None
            else class_player_actions(character_class, tuple(active_art_ids))
        )
    return start_combat(
        Combat(
            combat_id,
            runtime_ruleset,
            fighters=fighters,
            player_actions=player_actions,
            enemy_actions=actions,
            ai_cycle=ai_cycles.get("enemy", ()),
            tutorial=None,
            flavor=flavor,
            opening_log=opening_log,
            variant=enemies[0].variant if len(enemies) == 1 else None,
            ai_priority=ai_priorities.get("enemy", ()),
            configuration_snapshot=(
                equipment.to_data(runtime_ruleset) if equipment is not None else None
            ),
            ai_cycles=ai_cycles,
            ai_positions=ai_positions,
            ai_priorities=ai_priorities,
            pressure_start_opportunity=pressure_start_opportunity,
            pressure_cap=pressure_cap,
            player_actions_by_fighter=player_actions_by_fighter,
            player_configuration_snapshots=player_configuration_snapshots,
            party_mode=party is not None and len(party) > 1,
            ai_target_cycle=(tuple(member.character_id for member in party or ())
                             if party is not None and len(party) > 1 else ()),
        )
    )
