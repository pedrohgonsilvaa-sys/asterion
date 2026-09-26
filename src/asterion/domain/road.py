"""Pure, deterministic rules for the Estrada das Cinzas repeatable content."""
# ruff: noqa: E501

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from hashlib import sha256
from uuid import UUID

from asterion.domain.combat import Action, Combat, Fighter, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    CombatStats,
    StatMultipliers,
    enemy_stats,
    growth,
    resolve_combat_stats,
)
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.prologue import first_art

D = Decimal
RULESET = CURRENT_COMBAT_RULESET
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
CREATURE_CATALOG = (*CREATURES, SPIDER)

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
SLOT_WEIGHTS = {"Principal": 18, "2H": 28, "Secundária": 10, "Cabeça": 10, "Torso": 16, "Mãos": 10, "Pés": 10, "Acessório": 12, "Artefato": 14}
RARITY_SECONDARIES = {"Comum": 0, "Raro": 1, "Épico": 2, "Lendário": 3, "Mítico": 4}
RUNE_FAMILIES = (("Brasa", "ATQ"), ("Pedra", "DEF"), ("Caminhante", "AGI"), ("Fresta", "PER"), ("Presságio", "CRIT"), ("Persistência", "HP"), ("Desvio", "Esquiva"), ("Guarda", "Bloqueio"))
RUNE_POTENCY = {"HP": ("0.35%", "0.45%", "0.55%"), "ATQ": ("0.35%", "0.45%", "0.55%"), "DEF": ("0.55%", "0.80%", "1.00%"), "AGI": ("0.55%", "0.80%", "1.00%"), "PER": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."), "CRIT": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p."), "Esquiva": ("0.25 p.p.", "0.25 p.p.", "0.25 p.p."), "Bloqueio": ("0.25 p.p.", "0.50 p.p.", "0.50 p.p.")}
CORE60 = {"Principal": {"ATQ": 25}, "Secundária": {"ATQ": 7, "DEF": 5}, "2H": {"ATQ": 35}, "Cabeça": {"HP": 45, "DEF": 6}, "Torso": {"HP": 95, "DEF": 12}, "Mãos": {"ATQ": 10, "DEF": 5}, "Pés": {"HP": 60, "AGI": 8}, "Acessório": {"HP": 50, "ATQ": 7, "AGI": 4}, "Artefato": {"HP": 55, "ATQ": 7, "DEF": 5, "AGI": 4}}
SECONDARY_SCALE = {"HP": D("8.5"), "ATQ": D("1.35"), "DEF": D("2.30"), "AGI": D("3.00"), "PER": D("0.80"), "CRIT": D("0.67"), "Esquiva": D("0.33"), "Bloqueio": D("0.95")}
RARITY_MULT = {"Comum": D("1"), "Raro": D("1.07"), "Épico": D("1.15"), "Lendário": D("1.24"), "Mítico": D("1.45")}

def _stable_draw(seed: str, purpose: str, modulo: int) -> int:
    return int.from_bytes(sha256(f"{seed}:{purpose}".encode()).digest(), "big") % modulo

def materialize_equipment(seed: str, rarity: str, level: int) -> dict:
    eligible = tuple((name, slot) for name, slot in EQUIPMENT_CATALOG if not (rarity == "Mítico" and slot == "Torso"))
    groups = tuple(sorted({"Principal" if slot == "2H" else slot for _, slot in eligible}))
    group = groups[_stable_draw(seed, "equipment.group", len(groups))]
    templates = tuple(item for item in eligible if item[1] == group or (group == "Principal" and item[1] == "2H"))
    name, slot = templates[_stable_draw(seed, "equipment.template", len(templates))]
    count = RARITY_SECONDARIES[rarity]
    pools = {"Principal": ("ATQ", "AGI", "PER", "CRIT"), "2H": ("ATQ", "AGI", "PER", "CRIT"), "Secundária": ("ATQ", "DEF", "PER", "CRIT", "Bloqueio"), "Cabeça": ("HP", "DEF", "PER", "CRIT"), "Torso": ("HP", "DEF", "Bloqueio"), "Mãos": ("ATQ", "AGI", "PER", "CRIT"), "Pés": ("HP", "DEF", "AGI", "Esquiva"), "Acessório": ("HP", "ATQ", "AGI", "PER", "CRIT", "Esquiva"), "Artefato": ("HP", "ATQ", "DEF", "PER", "CRIT", "Bloqueio")}
    pool = list(pools[slot])
    secondaries = []
    g = growth(level)
    core = {attribute: int((D(value) * g).quantize(D(1), rounding="ROUND_HALF_UP")) for attribute, value in CORE60[slot].items()}
    for index in range(min(count, len(pool))):
        pick = _stable_draw(seed, f"equipment.secondary.{index}", len(pool))
        attribute = pool.pop(pick)
        budget = D(SLOT_WEIGHTS["Principal" if slot == "2H" else slot]) * (RARITY_MULT[rarity] - 1) / max(1, count)
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
    return {"item_name": name, "slot": slot, "item_level": level, "rarity": rarity, "core": core, "secondaries": secondaries, "enhancement": 0, "rune": None, "enchantment": None, "bound": False}

def rune_potency(family: str, rarity: str) -> str:
    stat = dict(RUNE_FAMILIES)[family]
    return RUNE_POTENCY[stat][{"Rara": 0, "Épica": 1, "Lendária": 2}[rarity]]

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


def select_exploration_result(seed: str, player_level: int, recent: tuple[str, ...] = (), excluded: tuple[str, ...] = ()) -> str:
    eligible_categories = []
    eligible_subweights = {}
    for category, weight in EXPLORATION_CATEGORY_WEIGHTS.items():
        subweights = EXPLORATION_SUBWEIGHTS[category]
        if category == "combat":
            subweights = tuple(
                (key, value) for key, value in subweights
                if creature_for(key).unlock_level <= player_level
            )
        subweights = tuple((key, value) for key, value in subweights if key not in excluded)
        # Apply anti-repeat to the *subresults* before deciding whether this
        # category remains eligible.  In particular, a category with one
        # eligible result cannot fall back to its base weight when that result
        # is the immediately previous result.
        adjusted = tuple(
            (key, anti_repeat_weight(weight, key, recent))
            for key, weight in subweights
        )
        adjusted = tuple((key, weight) for key, weight in adjusted if weight > 0)
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
    player_level: int | None = None,
    equipment_configuration: EquipmentConfigurationSnapshot | None = None,
    ruleset_version: str | None = None,
) -> Combat:
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
        flavor="A Estrada guarda ameaças entre as cinzas.",
        opening_log=f"🦌 {creature.name} surge entre a fuligem.",
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
) -> Combat:
    player_level = level if player_level is None else player_level
    runtime_ruleset = ruleset_version or RULESET
    equipment = equipment_configuration
    player_stats = resolve_combat_stats(
        character_class,
        player_level,
        race,
        equipment.contribution() if equipment is not None else None,
    )
    enemy = road_enemy_stats(creature, level, variant)
    actions = {}
    for specification in creature.actions:
        key, label, coefficient, blocked_opportunities, debuff, duration = specification[:6]
        native_dot_kind = specification[6] if len(specification) > 6 else None
        native_dot_stacks = specification[7] if len(specification) > 7 else 0
        prepared = specification[8] if len(specification) > 8 else False
        canonical_cooldown = specification[9] if len(specification) > 9 else None
        actions[key] = Action(
            key,
            label,
            coefficient,
            blocked_opportunities,
            debuff,
            duration,
            native_dot_kind,
            native_dot_stacks,
            prepared,
            canonical_cooldown,
        )
    return start_combat(
        Combat(
            combat_id,
            runtime_ruleset,
            fighters={
                "player": Fighter("player", name, player_level, player_stats, hp, race, character_class),
                "enemy": Fighter(
                    "enemy",
                    creature.name,
                    level,
                    enemy,
                    enemy.hp,
                    damage_taken_modifiers=dict(creature.damage_taken_modifiers),
                ),
            },
            player_actions={
                "attack": Action("attack", "⚔️ Atacar", D(1)),
                "art": first_art(character_class, 1),
            },
            enemy_actions=actions,
            ai_cycle=creature.ai,
            tutorial=None,
            flavor=flavor,
            opening_log=opening_log,
            variant=variant,
            ai_priority=creature.ai_priority,
            configuration_snapshot=(
                equipment.to_data(runtime_ruleset) if equipment is not None else None
            ),
        )
    )
