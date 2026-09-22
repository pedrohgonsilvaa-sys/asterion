"""Pure, deterministic rules for the Estrada das Cinzas repeatable content."""
# ruff: noqa: E501

from dataclasses import dataclass
from decimal import Decimal, localcontext
from hashlib import sha256
from uuid import UUID

from asterion.domain.combat import Action, Combat, Fighter, start_combat
from asterion.domain.combat_math import Stats, class_stats, enemy_stats, racial_stats
from asterion.domain.prologue import first_art

D = Decimal
RULESET = "gdd-1.4.3-baseline-1.0"
ROAD_LOCATION = "tdo.location.estrada_das_cinzas"
ROAD_BRAZIER = "tdo.brazier.estrada"
HUNT_UNLOCK = "hunt_manual.estrada_das_cinzas"
EXPLORE_UNLOCK = "explore.estrada_das_cinzas"
ROUND_FAMILIARITY = "hunt_round.estrada_das_cinzas"
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

CATEGORY = {
    "common": Stats(D("0.70"), D("0.82"), D("0.90"), D("0.95")),
    "elite": Stats(D("1.50"), D("1.05"), D("1.05"), D("1.02")),
}
ARCHETYPE = {
    "balanced": Stats(D(1), D(1), D(1), D(1)),
    "predator": Stats(D("0.90"), D("1.10"), D("0.90"), D("1.20")),
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
    actions: tuple[tuple[str, str, Decimal, int, Decimal, int], ...]


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
            ("rend", "Investida Rasgante", D("0.90"), 1, D(0), 0),
            ("leap", "Salto Predatório", D("1.60"), 3, D(0), 0),
        ),
    ),
)

VARIANTS = {
    "furious": Stats(D(1), D("1.08"), D("0.92"), D(1)),
    "resistant": Stats(D(1), D("0.94"), D("1.10"), D(1)),
    "agile": Stats(D("0.93"), D(1), D(1), D("1.12")),
    "hemorrhagic": Stats(D(1), D("0.95"), D(1), D(1)),
    "venomous": Stats(D("0.95"), D(1), D(1), D(1)),
}
VARIANT_POOL = {
    "dog_cinereo": ("furious", "agile"),
    "corvo_fuligem": ("agile", "furious"),
    "peregrino_calcinado": ("furious", "resistant", "hemorrhagic"),
    "alfa_cinereo": (),
}


def creature_for(creature_id: str) -> Creature:
    return next(c for c in CREATURES if c.creature_id == creature_id)


def road_pool(player_level: int) -> tuple[Creature, ...]:
    return tuple(c for c in CREATURES if player_level >= c.unlock_level)


def weighted_choice(seed: str, entries: tuple[tuple[str, int], ...]) -> str:
    total = sum(weight for _, weight in entries)
    value = int.from_bytes(sha256(seed.encode()).digest(), "big") % total
    for key, weight in entries:
        if value < weight:
            return key
        value -= weight
    return entries[-1][0]


def select_creature(seed: str, player_level: int) -> Creature:
    pool = road_pool(player_level)
    return creature_for(weighted_choice(seed, tuple((c.creature_id, c.weight) for c in pool)))


def select_variant(seed: str, creature: Creature) -> str | None:
    if not VARIANT_POOL[creature.creature_id]:
        return None
    digest = int.from_bytes(sha256(f"{seed}:variant:chance".encode()).digest(), "big")
    if digest % 100 >= 8:
        return None
    return VARIANT_POOL[creature.creature_id][digest % len(VARIANT_POOL[creature.creature_id])]


def road_enemy_stats(creature: Creature, level: int, variant: str | None = None) -> Stats:
    factors = [CATEGORY[creature.category], ARCHETYPE[creature.archetype]]
    if variant:
        factors.append(VARIANTS[variant])
    return enemy_stats(level, *factors)


def enemy_xp(level: int, category: str, vigor_factor: Decimal | None = None) -> int:
    with localcontext() as ctx:
        ctx.prec = 50
        xp = (D(4000) + D(750) * level + D(43) * level * level).quantize(
            D(100), rounding="ROUND_HALF_EVEN"
        )
        h = D("0.905903") + D("0.094097") * level
        category_factor = D("1") if category == "common" else D("2.75")
        value = xp / (D(20) * h) * category_factor * (vigor_factor or D(1))
        return int((value / 10).quantize(D(1), rounding="ROUND_HALF_EVEN") * 10)


def crowns(level: int, category: str) -> int:
    value = D(100) + D(15) * level
    factor = D("0.05") if category == "common" else D("0.25")
    return int(((value * factor) / 10).quantize(D(1), rounding="ROUND_HALF_EVEN") * 10)


def material_for(creature_id: str, seed: str) -> str:
    if creature_id in {"dog_cinereo", "alfa_cinereo"}:
        return "material.tdo.couro_escoriado"
    if creature_id == "corvo_fuligem":
        return "material.tdo.residuo_ocaso"
    return weighted_choice(
        seed, (("material.tdo.ferro_de_fuligem", 1), ("material.tdo.erva_cinzenta", 1))
    )


def create_road_combat(
    combat_id: UUID,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    creature: Creature,
    level: int,
    variant: str | None,
) -> Combat:
    player_stats = racial_stats(class_stats(character_class, 1), race)
    enemy = road_enemy_stats(creature, level, variant)
    actions = {
        key: Action(key, label, coefficient, cooldown, debuff, duration)
        for key, label, coefficient, cooldown, debuff, duration in creature.actions
    }
    return start_combat(
        Combat(
            combat_id,
            RULESET,
            fighters={
                "player": Fighter("player", name, 1, player_stats, hp, race, character_class),
                "enemy": Fighter("enemy", creature.name, level, enemy, enemy.hp),
            },
            player_actions={
                "attack": Action("attack", "⚔️ Atacar", D(1)),
                "art": first_art(character_class, 1),
            },
            enemy_actions=actions,
            ai_cycle=creature.ai,
            tutorial=None,
            flavor="A Estrada guarda ameaças entre as cinzas.",
            opening_log=f"🦌 {creature.name} surge entre a fuligem.",
        )
    )
