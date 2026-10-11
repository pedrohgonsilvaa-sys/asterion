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
CAMPAIGN_BOSS_CREATURES = (VDE_MATRIARCH,)
CREATURE_CATALOG = (
    *CREATURE_CATALOG,
    *VDE_CREATURES,
    *VDE_DUNGEON_CREATURES,
    *CAMPAIGN_BOSS_CREATURES,
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
}

EQUIPMENT_CATALOG = (
    ("Arma do Caminhante", "Principal"), ("Guarda do Caminhante", "Secundária"),
    ("Arma Pesada do Caminhante", "2H"), ("Elmo de Fuligem", "Cabeça"),
    ("Couraça de Fuligem", "Torso"), ("Manoplas de Fuligem", "Mãos"),
    ("Passos de Fuligem", "Pés"), ("Capuz das Cinzas", "Cabeça"),
    ("Veste do Caminhante", "Torso"), ("Luvas de Fuligem", "Mãos"),
    ("Botas da Estrada", "Pés"), ("Selo Enegrecido", "Acessório"),
    ("Relicário de Cinzas", "Artefato"),
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
) -> dict:
    eligible = tuple((name, slot) for name, slot in EQUIPMENT_CATALOG if not (rarity == "Mítico" and slot == "Torso"))
    if forced_slot is not None:
        if forced_slot not in {slot for _, slot in eligible}:
            raise ValueError(f"unknown forced equipment slot {forced_slot!r}")
        slot = forced_slot
        if forced_name is None:
            templates = tuple(item for item in eligible if item[1] == slot)
            name = templates[_stable_draw(seed, "equipment.template", len(templates))][0]
        else:
            name = forced_name
    else:
        groups = tuple(sorted({"Principal" if slot == "2H" else slot for _, slot in eligible}))
        group = groups[_stable_draw(seed, "equipment.group", len(groups))]
        templates = tuple(item for item in eligible if item[1] == group or (group == "Principal" and item[1] == "2H"))
        if forced_name is None:
            name, slot = templates[_stable_draw(seed, "equipment.template", len(templates))]
        else:
            name, slot = forced_name, templates[0][1]
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
    return {"item_name": name, "slot": slot, "item_level": level, "rarity": rarity, "core": core, "secondaries": secondaries, "enhancement": 0, "rune": None, "enchantment": None, "bound": bound}

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

LOCATION_LEVEL_BANDS = {
    "Estrada das Cinzas": (1, 10),
    "Charneca da Fuligem": (3, 5),
    "Bosque Calcinado": (5, 8),
    "Ruínas do Vigia": (8, 10),
    "Garganta dos Laços": (11, 13),
    "Mata Suspensa": (13, 16),
    "Baixios Enredados": (15, 18),
    "Claustro das Raízes": (18, 20),
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

EXPLORATION_PROFILES = {
    ROAD_LOCATION: ROAD_EXPLORATION_PROFILE,
    CHARNECA_LOCATION: CHARNECA_EXPLORATION_PROFILE,
    BOSQUE_LOCATION: BOSQUE_EXPLORATION_PROFILE,
    RUINS_LOCATION: RUINS_EXPLORATION_PROFILE,
    VDE_GARGANTA_LOCATION: VDE_GARGANTA_EXPLORATION_PROFILE,
    VDE_MATA_LOCATION: VDE_MATA_EXPLORATION_PROFILE,
    VDE_BAIXIOS_LOCATION: VDE_BAIXIOS_EXPLORATION_PROFILE,
    VDE_CLAUSTRO_LOCATION: VDE_CLAUSTRO_EXPLORATION_PROFILE,
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


def _creature_actions(creature: Creature, prefix: str = "") -> tuple[dict[str, Action], tuple[str, ...], tuple[str, ...]]:
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
        enemy_actions, cycle, priority = _creature_actions(creature, prefix)
        actions.update(enemy_actions)
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
