"""Profession progression and the canonical TDO/VDE recipe catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.economy import crowns_per_level, round_10

D = Decimal


class ProfessionSlot(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True, slots=True)
class ProfessionDefinition:
    profession_id: str
    name: str
    descriptor: str
    emoji: str


PROFESSIONS = (
    ProfessionDefinition("blacksmith", "Ferreiro", "Armas e Armaduras", "⚒️"),
    ProfessionDefinition("artificer", "Artífice", "Runas e Encantamentos", "⚙️"),
    ProfessionDefinition("alchemist", "Alquimista", "Consumíveis", "⚗️"),
    ProfessionDefinition("leatherworker", "Curteiro", "Armaduras", "🧵"),
    ProfessionDefinition("jeweler", "Joalheiro", "Acessórios", "💎"),
)
PROFESSION_BY_ID = {entry.profession_id: entry for entry in PROFESSIONS}
PROFESSION_IDS = tuple(entry.profession_id for entry in PROFESSIONS)
SLOT_CAPS = {ProfessionSlot.PRIMARY: 30, ProfessionSlot.SECONDARY: 15}


@dataclass(frozen=True, slots=True)
class MaterialRequirement:
    material_id: str
    quantity: int
    transmits_bind: bool = True


@dataclass(frozen=True, slots=True)
class RecipeDefinition:
    recipe_id: str
    profession_id: str
    name: str
    output_kind: str
    required_level: int
    grade: int = 1
    rarity: str | None = None
    output_name: str | None = None
    output_slot: str | None = None
    output_id: str | None = None
    output_family: str | None = None
    sw: int = 1
    basic_materials: int = 0
    primary_material_id: str | None = None
    secondary_material_id: str | None = None
    primary_ratio: Decimal = D("0.70")
    fragment_per_sw: int = 0
    catalyst_per_sw: int = 0
    fragment_material_id: str | None = None
    catalyst_material_id: str | None = None
    fixed_materials: tuple[MaterialRequirement, ...] = ()
    fixed_crown_cost: int | None = None
    creation_enabled: bool = True
    unlock_id: str | None = None
    description: str = ""


IRON = "material.tdo.ferro_de_fuligem"
LEATHER = "material.tdo.couro_escoriado"
HERB = "material.tdo.erva_cinzenta"
RESIDUE = "material.tdo.residuo_ocaso"
CATALYST_I = "material.tdo.catalisador_elite_i"
FRAGMENT_I = "material.tdo.fragmento_aprimoramento_i"
CRYPT_CORE = "material.tdo.nucleo_cripta_ocaso"
GALLERIES_CORE = "material.tdo.nucleo_galerias_vigia"
VIGIA_CORE = "material.tdo.nucleo_vigia_partido"
MATRIARCH_CORE = "material.vde.nucleo_matriarca_das_raizes"
FOSSO_CORE = "material.vde.nucleo_fosso_raizes"
SANCTUARY_CORE = "material.vde.nucleo_no_antigo"
VDE_IRON = "material.vde.ferro_enredado"
VDE_LEATHER = "material.vde.couro_musgoso"
VDE_HERB = "material.vde.erva_de_turfa"
VDE_RESIN = "material.vde.resina_enredada"
VDE_CATALYST_II = "material.vde.catalisador_elite_ii"
VDE_FRAGMENT_II = "material.vde.fragmento_aprimoramento_ii"
NARETH_BRONZE = "material.nareth.bronze_de_marco"
NARETH_LEATHER = "material.nareth.couro_de_horizonte"
NARETH_HERB = "material.nareth.erva_de_vento"
NARETH_POWDER = "material.nareth.po_de_eixo"
NARETH_CATALYST_III = "material.nareth.catalisador_elite_iii"
NARETH_FRAGMENT_III = "material.nareth.fragmento_aprimoramento_iii"
NARETH_GALLERIES_CORE = "material.nareth.nucleo_galerias_meridiano"
NARETH_OBSERVATORY_CORE = "material.nareth.nucleo_observatorio_afundado"
NARETH_ARCHON_CORE = "material.nareth.nucleo_arconte_invertido"
VARZEAS_IRON = "material.varzeas.ferro_de_salmoura"
VARZEAS_LEATHER = "material.varzeas.couro_de_varzea"
VARZEAS_REAGENT = "material.varzeas.junco_ferruginoso"
VARZEAS_ESSENCE = "material.varzeas.soro_antigo"
VARZEAS_CATALYST_IV = "material.varzeas.catalisador_elite_iv"
VARZEAS_FRAGMENT_IV = "material.varzeas.fragmento_aprimoramento_iv"
VARZEAS_INFIRMARY_CORE = "material.varzeas.nucleo_enfermaria_afundada"
VARZEAS_CISTERN_CORE = "material.varzeas.nucleo_cisterna_transferencia"
VARZEAS_MATRIX_CORE = "material.varzeas.nucleo_matriz_rubra"
CATALYST_V = "material.tdo.catalisador_elite_v"
FRAGMENT_V = "material.tdo.fragmento_aprimoramento_v"
ALTOS_COLOSSUS_CORE = "material.special.altos.core.colosso_cinereo"
ALTOS_PEDREIRA_CORE = "material.special.altos.core.pedreira_contrapeso"
ALTOS_BASTILHA_CORE = "material.special.altos.core.bastilha_profunda"

MATERIAL_NAMES = {
    IRON: "Ferro de Fuligem",
    LEATHER: "Couro Escoriado",
    HERB: "Erva Cinzenta",
    RESIDUE: "Resíduo do Ocaso",
    CATALYST_I: "Catalisador de Elite I",
    FRAGMENT_I: "Fragmento de Aprimoramento I",
    CRYPT_CORE: "Núcleo da Cripta do Ocaso",
    GALLERIES_CORE: "Núcleo das Galerias do Vigia",
    VIGIA_CORE: "Núcleo do Vigia Partido",
    MATRIARCH_CORE: "Núcleo da Matriarca das Raízes",
    FOSSO_CORE: "Núcleo do Fosso das Raízes",
    SANCTUARY_CORE: "Núcleo do Nó Antigo",
    NARETH_BRONZE: "Bronze de Marco",
    NARETH_LEATHER: "Couro de Horizonte",
    NARETH_HERB: "Erva de Vento",
    NARETH_POWDER: "Pó de Eixo",
    NARETH_CATALYST_III: "Catalisador de Elite III",
    NARETH_FRAGMENT_III: "Fragmento de Aprimoramento III",
    NARETH_GALLERIES_CORE: "Núcleo das Galerias do Meridiano",
    NARETH_OBSERVATORY_CORE: "Núcleo do Observatório Afundado",
    NARETH_ARCHON_CORE: "Núcleo do Arconte Invertido",
    VARZEAS_IRON: "Ferro de Salmoura",
    VARZEAS_LEATHER: "Couro de Várzea",
    VARZEAS_REAGENT: "Junco Ferruginoso",
    VARZEAS_ESSENCE: "Soro Antigo",
    VARZEAS_CATALYST_IV: "Catalisador de Elite IV",
    VARZEAS_FRAGMENT_IV: "Fragmento de Aprimoramento IV",
    VARZEAS_INFIRMARY_CORE: "Núcleo da Enfermaria Afundada",
    VARZEAS_CISTERN_CORE: "Núcleo da Cisterna de Transferência",
    VARZEAS_MATRIX_CORE: "Núcleo da Matriz Rubra",
    "material.altos.ferro_contrapeso": "Ferro de Contrapeso",
    "material.altos.couro_escarpa": "Couro de Escarpa",
    "material.altos.liquen_pedreira": "Líquen de Pedreira",
    "material.altos.cinza_basalto": "Cinza de Basalto",
    CATALYST_V: "Catalisador de Elite V",
    ALTOS_COLOSSUS_CORE: "Núcleo do Colosso Cinéreo",
    ALTOS_PEDREIRA_CORE: "Núcleo da Pedreira do Contrapeso",
    ALTOS_BASTILHA_CORE: "Núcleo da Bastilha Profunda",
    VDE_IRON: "Ferro Enredado",
    VDE_LEATHER: "Couro Musgoso",
    VDE_HERB: "Erva de Turfa",
    VDE_RESIN: "Resina Enredada",
    VDE_CATALYST_II: "Catalisador de Elite II",
    VDE_FRAGMENT_II: "Fragmento de Aprimoramento II",
}

SLOT_ECONOMY_SW = {
    "Principal": 2,
    "Secundária": 1,
    "2H": 3,
    "Cabeça": 1,
    "Torso": 2,
    "Mãos": 1,
    "Pés": 1,
    "Acessório": 2,
    "Artefato": 2,
}
RARITY_REQUIREMENTS = {"Comum": 1, "Raro": 5, "Épico": 10}
RARITY_COST_FACTORS = {"Comum": D("0.25"), "Raro": D("0.35"), "Épico": D("0.50")}
RARITY_COSTS_PER_SW = {"Comum": 5, "Raro": 8, "Épico": 10}


def _equipment_recipes() -> list[RecipeDefinition]:
    rarity_ids = {"Comum": "comum", "Raro": "raro", "Épico": "epico"}
    families = (
        (
            "blacksmith",
            "walker_weapon",
            "Arma do Caminhante",
            "Principal",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        (
            "blacksmith",
            "walker_guard",
            "Guarda do Caminhante",
            "Secundária",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        (
            "blacksmith",
            "walker_greatweapon",
            "Arma Pesada do Caminhante",
            "2H",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        ("blacksmith", "fuligem_helm", "Elmo de Fuligem", "Cabeça", IRON, RESIDUE, D("0.70")),
        ("blacksmith", "fuligem_cuirass", "Couraça de Fuligem", "Torso", IRON, RESIDUE, D("0.70")),
        (
            "blacksmith",
            "fuligem_gauntlets",
            "Manoplas de Fuligem",
            "Mãos",
            IRON,
            RESIDUE,
            D("0.70"),
        ),
        ("blacksmith", "fuligem_steps", "Passos de Fuligem", "Pés", IRON, RESIDUE, D("0.70")),
        ("leatherworker", "ash_hood", "Capuz das Cinzas", "Cabeça", LEATHER, HERB, D("0.70")),
        ("leatherworker", "walker_vest", "Veste do Caminhante", "Torso", LEATHER, HERB, D("0.70")),
        ("leatherworker", "fuligem_gloves", "Luvas de Fuligem", "Mãos", LEATHER, HERB, D("0.70")),
        ("leatherworker", "road_boots", "Botas da Estrada", "Pés", LEATHER, HERB, D("0.70")),
        ("jeweler", "blackened_seal", "Selo Enegrecido", "Acessório", IRON, RESIDUE, D("0.60")),
        ("jeweler", "ash_reliquary", "Relicário de Cinzas", "Artefato", IRON, RESIDUE, D("0.60")),
    )
    recipes = []
    for profession_id, family_id, name, slot, primary, secondary, ratio in families:
        sw = SLOT_ECONOMY_SW[slot]
        for rarity in ("Comum", "Raro", "Épico"):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.{profession_id}.{family_id}.{rarity_ids[rarity]}",
                    profession_id=profession_id,
                    name=name,
                    output_kind="equipment",
                    required_level=RARITY_REQUIREMENTS[rarity],
                    rarity=rarity,
                    output_name=name,
                    output_slot=slot,
                    sw=sw,
                    basic_materials=RARITY_COSTS_PER_SW[rarity],
                    primary_material_id=primary,
                    secondary_material_id=secondary,
                    primary_ratio=ratio,
                    fragment_per_sw=4 if rarity == "Raro" else 6 if rarity == "Épico" else 0,
                    catalyst_per_sw=2 if rarity == "Épico" else 0,
                    description=f"{rarity} · {slot}",
                )
            )
    return recipes


def _vde_equipment_recipes() -> list[RecipeDefinition]:
    """Normal Grade II equipment published by Vales dos Enforcados v1.0.6."""
    rarity_ids = {"Comum": "comum", "Raro": "raro", "Épico": "epico"}
    families = (
        ("blacksmith", "vale_weapon", "Arma do Vale", "Principal", VDE_IRON, VDE_RESIN, D("0.70")),
        (
            "blacksmith",
            "entwined_guard",
            "Guarda Enredada",
            "Secundária",
            VDE_IRON,
            VDE_RESIN,
            D("0.70"),
        ),
        (
            "blacksmith",
            "bonds_greatweapon",
            "Arma Pesada dos Laços",
            "2H",
            VDE_IRON,
            VDE_RESIN,
            D("0.70"),
        ),
        ("blacksmith", "entwined_helm", "Elmo Enlaçado", "Cabeça", VDE_IRON, VDE_RESIN, D("0.70")),
        ("blacksmith", "vale_cuirass", "Couraça do Vale", "Torso", VDE_IRON, VDE_RESIN, D("0.70")),
        (
            "blacksmith",
            "entwined_gauntlets",
            "Manoplas Enredadas",
            "Mãos",
            VDE_IRON,
            VDE_RESIN,
            D("0.70"),
        ),
        ("blacksmith", "peat_greaves", "Grevas de Turfa", "Pés", VDE_IRON, VDE_RESIN, D("0.70")),
        ("leatherworker", "moss_hood", "Capuz Musgoso", "Cabeça", VDE_LEATHER, VDE_HERB, D("0.70")),
        (
            "leatherworker",
            "suspended_forest_vest",
            "Veste da Mata Suspensa",
            "Torso",
            VDE_LEATHER,
            VDE_HERB,
            D("0.70"),
        ),
        (
            "leatherworker",
            "peat_gloves",
            "Luvas de Turfa",
            "Mãos",
            VDE_LEATHER,
            VDE_HERB,
            D("0.70"),
        ),
        (
            "leatherworker",
            "bonds_boots",
            "Botas dos Laços",
            "Pés",
            VDE_LEATHER,
            VDE_HERB,
            D("0.70"),
        ),
        ("jeweler", "bonds_seal", "Selo dos Laços", "Acessório", VDE_IRON, VDE_RESIN, D("0.60")),
        (
            "jeweler",
            "entwined_reliquary",
            "Relicário Enredado",
            "Artefato",
            VDE_IRON,
            VDE_RESIN,
            D("0.60"),
        ),
    )
    recipes = []
    for profession_id, family_id, name, slot, primary, secondary, ratio in families:
        sw = SLOT_ECONOMY_SW[slot]
        for rarity in ("Comum", "Raro", "Épico"):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.vde.{profession_id}.{family_id}.{rarity_ids[rarity]}",
                    profession_id=profession_id,
                    name=name,
                    output_kind="equipment",
                    required_level=max(3, RARITY_REQUIREMENTS[rarity]),
                    grade=2,
                    rarity=rarity,
                    output_name=name,
                    output_slot=slot,
                    sw=sw,
                    basic_materials=RARITY_COSTS_PER_SW[rarity],
                    primary_material_id=primary,
                    secondary_material_id=secondary,
                    primary_ratio=ratio,
                    fragment_per_sw=4 if rarity == "Raro" else 6 if rarity == "Épico" else 0,
                    catalyst_per_sw=2 if rarity == "Épico" else 0,
                    fragment_material_id=VDE_FRAGMENT_II,
                    catalyst_material_id=VDE_CATALYST_II,
                    description=f"{rarity} · {slot} · Grau II",
                )
            )
    return recipes


def _nareth_equipment_recipes() -> list[RecipeDefinition]:
    """Normal Grade III equipment families published for Nareth."""
    rarity_ids = {"Comum": "comum", "Raro": "raro", "Épico": "epico"}
    families = (
        (
            "blacksmith", "meridian_weapon", "Arma do Meridiano", "Principal",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "marker_guard", "Guarda de Marco", "Secundária",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "horizon_greatweapon", "Arma Pesada do Horizonte", "2H",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "plumb_helm", "Elmo do Prumo", "Cabeça",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "nareth_cuirass", "Couraça de Nareth", "Torso",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "line_gauntlets", "Manoplas de Linha", "Mãos",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "blacksmith", "channel_greaves", "Grevas de Canal", "Pés",
            NARETH_BRONZE, NARETH_POWDER, D("0.70"),
        ),
        (
            "leatherworker", "horizon_hood", "Capuz de Horizonte", "Cabeça",
            NARETH_LEATHER, NARETH_HERB, D("0.70"),
        ),
        (
            "leatherworker", "inverted_fields_vest", "Veste dos Campos Invertidos", "Torso",
            NARETH_LEATHER, NARETH_HERB, D("0.70"),
        ),
        (
            "leatherworker", "channel_gloves", "Luvas de Canal", "Mãos",
            NARETH_LEATHER, NARETH_HERB, D("0.70"),
        ),
        (
            "leatherworker", "meridian_boots", "Botas do Meridiano", "Pés",
            NARETH_LEATHER, NARETH_HERB, D("0.70"),
        ),
        (
            "jeweler", "axis_seal", "Selo do Eixo", "Acessório",
            NARETH_BRONZE, NARETH_POWDER, D("0.60"),
        ),
        (
            "jeweler", "reference_reliquary", "Relicário de Referência", "Artefato",
            NARETH_BRONZE, NARETH_POWDER, D("0.60"),
        ),
    )
    recipes = []
    for profession_id, family_id, name, slot, primary, secondary, ratio in families:
        sw = SLOT_ECONOMY_SW[slot]
        for rarity in ("Comum", "Raro", "Épico"):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.nareth.{profession_id}.{family_id}.{rarity_ids[rarity]}",
                    profession_id=profession_id,
                    name=name,
                    output_kind="equipment",
                    required_level=max(6, RARITY_REQUIREMENTS[rarity]),
                    grade=3,
                    rarity=rarity,
                    output_name=name,
                    output_slot=slot,
                    sw=sw,
                    basic_materials=RARITY_COSTS_PER_SW[rarity],
                    primary_material_id=primary,
                    secondary_material_id=secondary,
                    primary_ratio=ratio,
                    fragment_per_sw=4 if rarity == "Raro" else 6 if rarity == "Épico" else 0,
                    catalyst_per_sw=2 if rarity == "Épico" else 0,
                    fragment_material_id=NARETH_FRAGMENT_III,
                    catalyst_material_id=NARETH_CATALYST_III,
                    description=f"{rarity} · {slot} · Grau III",
                )
            )
    return recipes


def _varzeas_equipment_recipes() -> list[RecipeDefinition]:
    rarity_ids = {"Comum": "comum", "Raro": "raro", "Épico": "epico"}
    families = (
        (
            "blacksmith", "dike_weapon", "Arma do Dique", "Principal",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "brine_guard", "Guarda de Salmoura", "Secundária",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "transfer_greatweapon", "Arma Pesada de Transferência", "2H",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "valve_helm", "Elmo das Válvulas", "Cabeça",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "varzeas_cuirass", "Couraça das Várzeas", "Torso",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "ferruginous_gauntlets", "Manoplas Ferruginosas", "Mãos",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "blacksmith", "porto_greaves", "Grevas do Porto", "Pés",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.70"),
        ),
        (
            "leatherworker", "reed_hood", "Capuz de Junco", "Cabeça",
            VARZEAS_LEATHER, VARZEAS_REAGENT, D("0.70"),
        ),
        (
            "leatherworker", "waxed_vest", "Veste Encerada", "Torso",
            VARZEAS_LEATHER, VARZEAS_REAGENT, D("0.70"),
        ),
        (
            "leatherworker", "marsh_gloves", "Luvas de Várzea", "Mãos",
            VARZEAS_LEATHER, VARZEAS_REAGENT, D("0.70"),
        ),
        (
            "leatherworker", "brine_boots", "Botas da Salmoura", "Pés",
            VARZEAS_LEATHER, VARZEAS_REAGENT, D("0.70"),
        ),
        (
            "jeweler", "transfer_seal", "Selo de Transferência", "Acessório",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.60"),
        ),
        (
            "jeweler", "restitution_reliquary", "Relicário de Restituição", "Artefato",
            VARZEAS_IRON, VARZEAS_ESSENCE, D("0.60"),
        ),
    )
    recipes = []
    for profession_id, family_id, name, slot, primary, secondary, ratio in families:
        for rarity in ("Comum", "Raro", "Épico"):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.varzeas.{profession_id}.{family_id}.{rarity_ids[rarity]}",
                    profession_id=profession_id,
                    name=name,
                    output_kind="equipment",
                    required_level=max(9, RARITY_REQUIREMENTS[rarity]),
                    grade=4,
                    rarity=rarity,
                    output_name=name,
                    output_slot=slot,
                    sw=SLOT_ECONOMY_SW[slot],
                    basic_materials=RARITY_COSTS_PER_SW[rarity],
                    primary_material_id=primary,
                    secondary_material_id=secondary,
                    primary_ratio=ratio,
                    fragment_per_sw=4 if rarity == "Raro" else 6 if rarity == "Épico" else 0,
                    catalyst_per_sw=2 if rarity == "Épico" else 0,
                    fragment_material_id=VARZEAS_FRAGMENT_IV,
                    catalyst_material_id=VARZEAS_CATALYST_IV,
                    description=f"{rarity} · {slot} · Grau IV",
                )
            )
    return recipes


def _alchemy_recipes() -> list[RecipeDefinition]:
    recipes = []
    catalogs = (
        (
            "tdo",
            "Terras do Ocaso",
            (
                "consumable.heal",
                "consumable.purification",
                "consumable.antidote.tdo.i",
                "consumable.vigor.tdo.i",
            ),
            {
                "Ervas Cinzentas": HERB,
                "Erva Cinzenta": HERB,
                "Resíduo do Ocaso": RESIDUE,
                "Resíduos do Ocaso": RESIDUE,
                "Catalisador de Elite I": CATALYST_I,
            },
            frozenset({CATALYST_I}),
        ),
        (
            "vde",
            "Vales dos Enforcados",
            (
                "consumable.heal.vde.ii",
                "consumable.purification.vde.ii",
                "consumable.antidote.vde.ii",
                "consumable.vigor.vde.ii",
                "consumable.protection.vde.ii",
            ),
            {
                "Ervas de Turfa": VDE_HERB,
                "Erva de Turfa": VDE_HERB,
                "Resina Enredada": VDE_RESIN,
                "Resinas Enredadas": VDE_RESIN,
                "Catalisador de Elite II": VDE_CATALYST_II,
            },
            frozenset({VDE_CATALYST_II}),
        ),
        (
            "nareth",
            "Planícies de Nareth",
            (
                "consumable.heal.nareth.iii",
                "consumable.purification.nareth.iii",
                "consumable.antidote.nareth.iii",
                "consumable.vigor.nareth.iii",
                "consumable.protection.nareth.iii",
                "consumable.dispeller.nareth.iii",
            ),
            {
                "Ervas de Vento": NARETH_HERB,
                "Erva de Vento": NARETH_HERB,
                "Pó de Eixo": NARETH_POWDER,
                "Pós de Eixo": NARETH_POWDER,
                "Catalisador de Elite III": NARETH_CATALYST_III,
            },
            frozenset({NARETH_CATALYST_III}),
        ),
        (
            "varzeas",
            "Várzeas Carmesins",
            (
                "consumable.heal.varzeas.iv",
                "consumable.purification.varzeas.iv",
                "consumable.antidote.varzeas.iv",
                "consumable.vigor.varzeas.iv",
                "consumable.protection.varzeas.iv",
                "consumable.dispeller.varzeas.iv",
                "consumable.warding.varzeas.iv",
            ),
            {
                "Junco Ferruginoso": VARZEAS_REAGENT,
                "Juncos Ferruginosos": VARZEAS_REAGENT,
                "Soro Antigo": VARZEAS_ESSENCE,
                "Soros Antigos": VARZEAS_ESSENCE,
                "Catalisador de Elite IV": VARZEAS_CATALYST_IV,
            },
            frozenset({VARZEAS_CATALYST_IV}),
        ),
    )
    for region_code, region_name, item_ids, material_ids, nonbinding in catalogs:
        for item_id in item_ids:
            item = consumable_definition(item_id)
            if item is None or item.region != region_name:
                raise RuntimeError(
                    f"{region_code.upper()} alchemy recipe {item_id!r} is missing "
                    "from the canonical catalog"
                )
            materials = []
            for ingredient in item.recipe.ingredients:
                material_id = material_ids.get(ingredient.name)
                if material_id is None:
                    raise RuntimeError(
                        f"No canonical {region_code.upper()} material ID for {ingredient.name!r}"
                    )
                materials.append(
                    MaterialRequirement(
                        material_id,
                        ingredient.quantity,
                        material_id not in nonbinding,
                    )
                )
            recipes.append(
                RecipeDefinition(
                    recipe_id=(
                        f"recipe.{region_code}.alchemist."
                        f"{item.id.removeprefix('consumable.')}"
                    ),
                    profession_id="alchemist",
                    name=item.name,
                    output_kind="consumable",
                    required_level=item.recipe.profession_level,
                    grade=item.grade,
                    output_id=item.id,
                    fixed_materials=tuple(materials),
                    fixed_crown_cost=item.recipe.crown_cost,
                    description=f"Consumível · Grau {item.grade}",
                )
            )
    return recipes


def _special_recipes() -> list[RecipeDefinition]:
    return [
        RecipeDefinition(
            recipe_id="recipe.tdo.cripta.relicario_sem_nome",
            profession_id="jeweler",
            name="Relicário dos Sem-Nome",
            output_kind="equipment",
            required_level=5,
            rarity="Raro",
            output_name="Relicário dos Sem-Nome",
            output_slot="Artefato",
            sw=2,
            fixed_materials=(
                MaterialRequirement(IRON, 10),
                MaterialRequirement(RESIDUE, 6),
                MaterialRequirement(FRAGMENT_I, 8, False),
                MaterialRequirement(CRYPT_CORE, 1),
            ),
            unlock_id="recipe.tdo.cripta.relicario_sem_nome",
            description="Artefato · Raro · Grau I · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.tdo.galerias.guarda_primeiro_selo",
            profession_id="blacksmith",
            name="Guarda do Primeiro Selo",
            output_kind="equipment",
            required_level=10,
            rarity="Épico",
            output_name="Guarda do Primeiro Selo",
            output_slot="Secundária",
            sw=1,
            fixed_materials=(
                MaterialRequirement(IRON, 7),
                MaterialRequirement(RESIDUE, 3),
                MaterialRequirement(CATALYST_I, 2, False),
                MaterialRequirement(FRAGMENT_I, 6, False),
                MaterialRequirement(GALLERIES_CORE, 1),
            ),
            unlock_id="recipe.tdo.galerias.guarda_primeiro_selo",
            description="Arma Secundária · Épico · Grau I · SW1",
        ),
        RecipeDefinition(
            recipe_id="recipe.tdo.vigia_partido.eco",
            profession_id="artificer",
            name="Eco do Vigia Partido",
            output_kind="enchantment",
            required_level=10,
            rarity="Épico",
            output_id="PER",
            output_family="Marca da Fresta",
            sw=2,
            fixed_materials=(
                MaterialRequirement(RESIDUE, 5),
                MaterialRequirement(IRON, 2),
                MaterialRequirement(CATALYST_I, 1, False),
                MaterialRequirement(VIGIA_CORE, 1),
            ),
            fixed_crown_cost=100,
            creation_enabled=False,
            unlock_id="recipe.tdo.vigia_partido.eco",
            description="Encantamento Épico de PER · Grau I",
        ),
        RecipeDefinition(
            recipe_id="recipe.vde.matriarca.seiva",
            profession_id="artificer",
            name="Seiva da Matriarca",
            output_kind="enchantment",
            required_level=10,
            grade=2,
            rarity="Épico",
            output_id="HP",
            output_family="Seiva da Matriarca",
            sw=2,
            fixed_materials=(
                MaterialRequirement(VDE_RESIN, 5),
                MaterialRequirement(VDE_IRON, 2),
                MaterialRequirement(VDE_CATALYST_II, 1, False),
                MaterialRequirement(MATRIARCH_CORE, 1),
            ),
            fixed_crown_cost=160,
            creation_enabled=False,
            unlock_id="recipe.vde.matriarca.seiva",
            description="Encantamento Épico de HP · Grau II",
        ),
        RecipeDefinition(
            recipe_id="recipe.vde.fosso.relicario_cordas_mortas",
            profession_id="jeweler",
            name="Relicário das Cordas Mortas",
            output_kind="equipment",
            required_level=5,
            grade=2,
            rarity="Raro",
            output_name="Relicário das Cordas Mortas",
            output_slot="Artefato",
            output_id="vde_fosso_relicario_cordas_mortas",
            sw=2,
            fixed_materials=(
                MaterialRequirement(VDE_IRON, 10),
                MaterialRequirement(VDE_RESIN, 6),
                MaterialRequirement(VDE_FRAGMENT_II, 8, False),
                MaterialRequirement(FOSSO_CORE, 1),
            ),
            unlock_id="recipe.vde.fosso.relicario_cordas_mortas",
            description="Artefato · Raro · Grau II · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.vde.santuario.guarda_no_antigo",
            profession_id="blacksmith",
            name="Guarda do Nó Antigo",
            output_kind="equipment",
            required_level=10,
            grade=2,
            rarity="Épico",
            output_name="Guarda do Nó Antigo",
            output_slot="Secundária",
            output_id="vde_santuario_guarda_no_antigo",
            sw=1,
            fixed_materials=(
                MaterialRequirement(VDE_IRON, 7),
                MaterialRequirement(VDE_RESIN, 3),
                MaterialRequirement(VDE_CATALYST_II, 2, False),
                MaterialRequirement(VDE_FRAGMENT_II, 6, False),
                MaterialRequirement(SANCTUARY_CORE, 1),
            ),
            unlock_id="recipe.vde.santuario.guarda_no_antigo",
            description="Arma Secundária · Épico · Grau II · SW1",
        ),
        RecipeDefinition(
            recipe_id="recipe.nareth.galerias.relicario_circuito_retornado",
            profession_id="jeweler",
            name="Relicário do Circuito Retornado",
            output_kind="equipment",
            required_level=5,
            grade=3,
            rarity="Raro",
            output_name="Relicário do Circuito Retornado",
            output_slot="Artefato",
            output_id="nareth_galerias_relicario_circuito_retornado",
            sw=2,
            fixed_materials=(
                MaterialRequirement(NARETH_BRONZE, 10),
                MaterialRequirement(NARETH_POWDER, 6),
                MaterialRequirement(NARETH_FRAGMENT_III, 8, False),
                MaterialRequirement(NARETH_GALLERIES_CORE, 1),
            ),
            unlock_id="recipe.nareth.galerias.relicario_circuito_retornado",
            description="Artefato · Raro · Grau III · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.nareth.observatorio.guarda_referencia",
            profession_id="blacksmith",
            name="Guarda da Referência",
            output_kind="equipment",
            required_level=10,
            grade=3,
            rarity="Épico",
            output_name="Guarda da Referência",
            output_slot="Secundária",
            output_id="nareth_observatorio_guarda_referencia",
            sw=1,
            fixed_materials=(
                MaterialRequirement(NARETH_BRONZE, 7),
                MaterialRequirement(NARETH_POWDER, 3),
                MaterialRequirement(NARETH_CATALYST_III, 2, False),
                MaterialRequirement(NARETH_FRAGMENT_III, 6, False),
                MaterialRequirement(NARETH_OBSERVATORY_CORE, 1),
            ),
            unlock_id="recipe.nareth.observatorio.guarda_referencia",
            description="Arma Secundária · Épico · Grau III · SW1",
        ),
        RecipeDefinition(
            recipe_id="recipe.nareth.arconte.calibracao",
            profession_id="artificer",
            name="Calibração do Arconte",
            output_kind="enchantment",
            required_level=10,
            grade=3,
            rarity="Épico",
            output_id="PER",
            output_family="Calibração do Arconte",
            fixed_materials=(
                MaterialRequirement(NARETH_POWDER, 5),
                MaterialRequirement(NARETH_BRONZE, 2),
                MaterialRequirement(NARETH_CATALYST_III, 1, False),
                MaterialRequirement(NARETH_ARCHON_CORE, 1),
            ),
            fixed_crown_cost=220,
            creation_enabled=False,
            unlock_id="recipe.nareth.calibracao_do_arconte",
            description="Encantamento Épico de PER · Grau III",
        ),
        RecipeDefinition(
            recipe_id="recipe.varzeas.matriz.regulacao",
            profession_id="artificer",
            name="Regulação da Matriz",
            output_kind="enchantment",
            required_level=10,
            grade=4,
            rarity="Épico",
            output_id="HP",
            output_family="Regulação da Matriz",
            fixed_materials=(
                MaterialRequirement(VARZEAS_ESSENCE, 5),
                MaterialRequirement(VARZEAS_IRON, 2),
                MaterialRequirement(VARZEAS_CATALYST_IV, 1, False),
                MaterialRequirement(VARZEAS_MATRIX_CORE, 1),
            ),
            fixed_crown_cost=280,
            creation_enabled=False,
            unlock_id="recipe.varzeas.matriz.regulacao",
            description="Encantamento Épico de HP · Grau IV · +0,30% HP",
        ),
        RecipeDefinition(
            recipe_id="recipe.varzeas.enfermaria.mascara_triagem_silenciosa",
            profession_id="leatherworker",
            name="Máscara da Triagem Silenciosa",
            output_kind="equipment",
            required_level=9,
            grade=4,
            rarity="Raro",
            output_name="Máscara da Triagem Silenciosa",
            output_slot="Cabeça",
            sw=1,
            fixed_materials=(
                MaterialRequirement(VARZEAS_LEATHER, 6),
                MaterialRequirement(VARZEAS_REAGENT, 2),
                MaterialRequirement(VARZEAS_FRAGMENT_IV, 4, False),
                MaterialRequirement(VARZEAS_INFIRMARY_CORE, 1),
            ),
            unlock_id="recipe.varzeas.enfermaria.mascara_triagem_silenciosa",
            description="Cabeça · Raro · Grau IV · SW1",
        ),
        RecipeDefinition(
            recipe_id="recipe.varzeas.cisterna.peitoral_fluxo_contido",
            profession_id="blacksmith",
            name="Peitoral do Fluxo Contido",
            output_kind="equipment",
            required_level=10,
            grade=4,
            rarity="Épico",
            output_name="Peitoral do Fluxo Contido",
            output_slot="Torso",
            sw=2,
            fixed_materials=(
                MaterialRequirement(VARZEAS_IRON, 14),
                MaterialRequirement(VARZEAS_ESSENCE, 6),
                MaterialRequirement(VARZEAS_CATALYST_IV, 4, False),
                MaterialRequirement(VARZEAS_FRAGMENT_IV, 12, False),
                MaterialRequirement(VARZEAS_CISTERN_CORE, 1),
            ),
            unlock_id="recipe.varzeas.cisterna.peitoral_fluxo_contido",
            description="Torso · Épico · Grau IV · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.altos.colosso.continuidade",
            profession_id="artificer",
            name="Continuidade do Colosso",
            output_kind="enchantment",
            required_level=12,
            grade=5,
            rarity="Épico",
            output_id="enchant.altos.continuidade_colosso",
            output_family="Continuidade do Colosso",
            fixed_materials=(
                MaterialRequirement("material.altos.cinza_basalto", 5),
                MaterialRequirement("material.altos.ferro_contrapeso", 2),
                MaterialRequirement(CATALYST_V, 1, False),
                MaterialRequirement(ALTOS_COLOSSUS_CORE, 1),
            ),
            fixed_crown_cost=340,
            creation_enabled=False,
            unlock_id="recipe.altos.colosso.continuidade",
            description="Encantamento Épico de Bloqueio · Grau V · +0,50 p.p.",
        ),
        RecipeDefinition(
            recipe_id="recipe.altos.pedreira.relicario_peso_suspenso",
            profession_id="jeweler",
            name="Relicário do Peso Suspenso",
            output_kind="equipment",
            required_level=12,
            grade=5,
            rarity="Raro",
            output_name="Relicário do Peso Suspenso",
            output_slot="Artefato",
            output_id="equipment.altos.special.relicario_peso_suspenso",
            sw=2,
            fixed_materials=(
                MaterialRequirement("material.altos.ferro_contrapeso", 10),
                MaterialRequirement("material.altos.cinza_basalto", 6),
                MaterialRequirement(FRAGMENT_V, 8, False),
                MaterialRequirement(ALTOS_PEDREIRA_CORE, 1),
            ),
            unlock_id="recipe.altos.pedreira.relicario_peso_suspenso",
            description="Artefato · Raro · Grau V · SW2",
        ),
        RecipeDefinition(
            recipe_id="recipe.altos.bastilha.guarda_ordem_profunda",
            profession_id="blacksmith",
            name="Guarda da Ordem Profunda",
            output_kind="equipment",
            required_level=12,
            grade=5,
            rarity="Épico",
            output_name="Guarda da Ordem Profunda",
            output_slot="Secundária",
            output_id="equipment.altos.special.guarda_ordem_profunda",
            sw=1,
            fixed_materials=(
                MaterialRequirement("material.altos.ferro_contrapeso", 7),
                MaterialRequirement("material.altos.cinza_basalto", 3),
                MaterialRequirement(CATALYST_V, 2, False),
                MaterialRequirement(FRAGMENT_V, 6, False),
                MaterialRequirement(ALTOS_BASTILHA_CORE, 1),
            ),
            unlock_id="recipe.altos.bastilha.guarda_ordem_profunda",
            description="Arma Secundária · Épico · Grau V · SW1 · 1H",
        ),
    ]


def _enchantment_recipes() -> list[RecipeDefinition]:
    """Known TDO enchantments are applied directly to an equipment instance."""
    families = (
        ("fio_cinereo", "Fio Cinéreo", "ATQ"),
        ("pele_de_pedra", "Pele de Pedra", "DEF"),
        ("passo_de_fuligem", "Passo de Fuligem", "AGI"),
        ("marca_da_fresta", "Marca da Fresta", "PER"),
        ("eco_do_pressagio", "Eco do Presságio", "CRIT"),
        ("sopro_persistente", "Sopro Persistente", "HP"),
        ("veu_de_desvio", "Véu de Desvio", "Esquiva"),
        ("selo_de_guarda", "Selo de Guarda", "Bloqueio"),
    )
    result = []
    for family_id, name, stat in families:
        for rarity, rarity_id, level, residue, iron, catalysts, cost in (
            ("Raro", "raro", 5, 3, 1, 0, 50),
            ("Épico", "epico", 10, 5, 2, 1, 100),
        ):
            result.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.artificer.enchantment.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="enchantment",
                    required_level=level,
                    rarity=rarity,
                    output_id=stat,
                    output_family=name,
                    fixed_materials=(
                        MaterialRequirement(RESIDUE, residue),
                        MaterialRequirement(IRON, iron),
                        *(
                            (MaterialRequirement(CATALYST_I, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                    ),
                    fixed_crown_cost=cost,
                    creation_enabled=False,
                    description=f"Encantamento {rarity} · {stat} · Grau I",
                )
            )
    return result


def _vde_enchantment_recipes() -> list[RecipeDefinition]:
    families = (
        ("fio_enredado", "Fio Enredado", "ATQ"),
        ("pele_de_casca", "Pele de Casca", "DEF"),
        ("passo_das_copas", "Passo das Copas", "AGI"),
        ("marca_do_no", "Marca do Nó", "PER"),
        ("eco_da_cacada", "Eco da Caçada", "CRIT"),
        ("sopro_de_seiva", "Sopro de Seiva", "HP"),
        ("veu_da_mata", "Véu da Mata", "Esquiva"),
        ("selo_das_raizes", "Selo das Raízes", "Bloqueio"),
    )
    result = []
    for family_id, name, stat in families:
        for rarity, rarity_id, level, resin, iron, catalysts, cost in (
            ("Raro", "raro", 5, 3, 1, 0, 80),
            ("Épico", "epico", 10, 5, 2, 1, 160),
        ):
            result.append(
                RecipeDefinition(
                    recipe_id=f"recipe.vde.artificer.enchantment.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="enchantment",
                    required_level=level,
                    grade=2,
                    rarity=rarity,
                    output_id=stat,
                    output_family=name,
                    fixed_materials=(
                        MaterialRequirement(VDE_RESIN, resin),
                        MaterialRequirement(VDE_IRON, iron),
                        *(
                            (MaterialRequirement(VDE_CATALYST_II, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                    ),
                    fixed_crown_cost=cost,
                    creation_enabled=False,
                    description=f"Encantamento {rarity} · {stat} · Grau II",
                )
            )
    return result


def _nareth_enchantment_recipes() -> list[RecipeDefinition]:
    families = (
        ("Fio do Meridiano", "ATQ"),
        ("Pele do Prumo", "DEF"),
        ("Passo do Horizonte", "AGI"),
        ("Marca de Referência", "PER"),
        ("Eco da Distância", "CRIT"),
        ("Sopro do Posto", "HP"),
        ("Véu do Desvio", "Esquiva"),
        ("Selo do Eixo", "Bloqueio"),
    )
    recipes = []
    for name, stat in families:
        family_id = name.casefold().replace(" ", "_").replace("ó", "o").replace("ê", "e")
        for rarity, rarity_id, level, powder, bronze, catalysts, cost in (
            ("Raro", "raro", 5, 3, 1, 0, 110),
            ("Épico", "epico", 10, 5, 2, 1, 220),
        ):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.nareth.artificer.enchantment.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="enchantment",
                    required_level=level,
                    grade=3,
                    rarity=rarity,
                    output_id=stat,
                    output_family=name,
                    fixed_materials=(
                        MaterialRequirement(NARETH_POWDER, powder),
                        MaterialRequirement(NARETH_BRONZE, bronze),
                        *(
                            (MaterialRequirement(NARETH_CATALYST_III, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                    ),
                    fixed_crown_cost=cost,
                    creation_enabled=False,
                    description=f"Encantamento {rarity} · {stat} · Grau III",
                )
            )
    return recipes


def _varzeas_enchantment_recipes() -> list[RecipeDefinition]:
    families = (
        ("dike_wire", "Fio do Dique", "ATQ"),
        ("containment_skin", "Pele de Contenção", "DEF"),
        ("reed_step", "Passo de Junco", "AGI"),
        ("triage_mark", "Marca de Triagem", "PER"),
        ("emergency_echo", "Eco de Emergência", "CRIT"),
        ("restitution_breath", "Sopro de Restituição", "HP"),
        ("margin_veil", "Véu da Margem", "Esquiva"),
        ("valve_seal", "Selo da Válvula", "Bloqueio"),
    )
    recipes = []
    for family_id, name, stat in families:
        for rarity, rarity_id, level, essence, iron, catalyst, cost in (
            ("Raro", "raro", 5, 3, 1, 0, 140),
            ("Épico", "epico", 10, 5, 2, 1, 280),
        ):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.varzeas.artificer.enchantment.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="enchantment",
                    required_level=level,
                    grade=4,
                    rarity=rarity,
                    output_id=stat,
                    output_family=name,
                    fixed_materials=(
                        MaterialRequirement(VARZEAS_ESSENCE, essence),
                        MaterialRequirement(VARZEAS_IRON, iron),
                        *(
                            (MaterialRequirement(VARZEAS_CATALYST_IV, catalyst, False),)
                            if catalyst else ()
                        ),
                    ),
                    fixed_crown_cost=cost,
                    creation_enabled=False,
                    description=f"Encantamento {rarity} · {stat} · Grau IV",
                )
            )
    return recipes


def _rune_recipes() -> list[RecipeDefinition]:
    from asterion.domain.road import RUNE_FAMILIES

    recipes = []
    rarity_ids = {"Rara": "rara", "Épica": "epica"}
    rarities = (
        ("Rara", 5, 80, 4, 2, 0, 2),
        ("Épica", 10, 150, 7, 3, 1, 4),
    )
    for family, stat in RUNE_FAMILIES:
        for rarity, required_level, crowns, essences, metal, catalysts, fragments in rarities:
            family_id = family.casefold().replace("á", "a").replace("ê", "e")
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.tdo.artificer.rune.{family_id}.{rarity_ids[rarity]}",
                    profession_id="artificer",
                    name=f"Runa da {family}",
                    output_kind="rune",
                    required_level=required_level,
                    rarity=rarity,
                    output_id=f"rune.tdo.{family_id}",
                    output_family=family,
                    fixed_materials=(
                        MaterialRequirement(RESIDUE, essences),
                        MaterialRequirement(IRON, metal),
                        *(
                            (MaterialRequirement(CATALYST_I, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                        MaterialRequirement(FRAGMENT_I, fragments, False),
                    ),
                    fixed_crown_cost=crowns,
                    description=f"{rarity} · {stat} · Grau I",
                )
            )
    return recipes


def _vde_rune_recipes() -> list[RecipeDefinition]:
    families = (
        ("espinho", "Espinho", "Runa do Espinho", "ATQ"),
        ("casca", "Casca", "Runa da Casca", "DEF"),
        ("copas", "Copas", "Runa das Copas", "AGI"),
        ("no", "Nó", "Runa do Nó", "PER"),
        ("cacada", "Caçada", "Runa da Caçada", "CRIT"),
        ("seiva", "Seiva", "Runa da Seiva", "HP"),
        ("nevoa", "Névoa", "Runa da Névoa", "Esquiva"),
        ("raizes", "Raízes", "Runa das Raízes", "Bloqueio"),
    )
    recipes = []
    for family_id, family, name, stat in families:
        for rarity, rarity_id, required_level, crowns, resin, iron, catalysts, fragments in (
            ("Rara", "rara", 5, 120, 4, 2, 0, 2),
            ("Épica", "epica", 10, 240, 7, 3, 1, 4),
        ):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.vde.artificer.rune.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="rune",
                    required_level=required_level,
                    grade=2,
                    rarity=rarity,
                    output_id=f"rune.vde.{family_id}",
                    output_family=family,
                    fixed_materials=(
                        MaterialRequirement(VDE_RESIN, resin),
                        MaterialRequirement(VDE_IRON, iron),
                        *(
                            (MaterialRequirement(VDE_CATALYST_II, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                        MaterialRequirement(VDE_FRAGMENT_II, fragments, False),
                    ),
                    fixed_crown_cost=crowns,
                    description=f"{rarity} · {stat} · Grau II",
                )
            )
    return recipes


def _nareth_rune_recipes() -> list[RecipeDefinition]:
    families = (
        ("Meridiano", "Runa do Meridiano", "ATQ"),
        ("Prumo", "Runa do Prumo", "DEF"),
        ("Horizonte", "Runa do Horizonte", "AGI"),
        ("Marco", "Runa do Marco", "PER"),
        ("Distância", "Runa da Distância", "CRIT"),
        ("Abrigo", "Runa do Abrigo", "HP"),
        ("Desvio", "Runa do Desvio", "Esquiva"),
        ("Referência", "Runa da Referência", "Bloqueio"),
    )
    recipes = []
    for family, name, stat in families:
        family_id = family.casefold().replace("â", "a").replace("ê", "e").replace("ç", "c")
        for rarity, rarity_id, level, crowns, powder, bronze, catalysts, fragments in (
            ("Rara", "rara", 5, 160, 4, 2, 0, 2),
            ("Épica", "epica", 10, 330, 7, 3, 1, 4),
        ):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.nareth.artificer.rune.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="rune",
                    required_level=level,
                    grade=3,
                    rarity=rarity,
                    output_id=f"rune.nareth.{family_id}",
                    output_family=family,
                    fixed_materials=(
                        MaterialRequirement(NARETH_POWDER, powder),
                        MaterialRequirement(NARETH_BRONZE, bronze),
                        *(
                            (MaterialRequirement(NARETH_CATALYST_III, catalysts, False),)
                            if catalysts
                            else ()
                        ),
                        MaterialRequirement(NARETH_FRAGMENT_III, fragments, False),
                    ),
                    fixed_crown_cost=crowns,
                    description=f"{rarity} · {stat} · Grau III",
                )
            )
    return recipes


def _varzeas_rune_recipes() -> list[RecipeDefinition]:
    families = (
        ("dike", "Dique", "Runa do Dique", "ATQ"),
        ("containment", "Contenção", "Runa da Contenção", "DEF"),
        ("reed", "Junco", "Runa do Junco", "AGI"),
        ("triage", "Triagem", "Runa da Triagem", "PER"),
        ("emergency", "Emergência", "Runa da Emergência", "CRIT"),
        ("restitution", "Restituição", "Runa da Restituição", "HP"),
        ("margin", "Margem", "Runa da Margem", "Esquiva"),
        ("valve", "Válvula", "Runa da Válvula", "Bloqueio"),
    )
    recipes = []
    for family_id, family, name, stat in families:
        for rarity, rarity_id, level, essence, iron, catalyst, fragments, cost in (
            ("Rara", "rara", 5, 4, 2, 0, 2, 210),
            ("Épica", "epica", 10, 7, 3, 1, 4, 420),
        ):
            recipes.append(
                RecipeDefinition(
                    recipe_id=f"recipe.varzeas.artificer.rune.{family_id}.{rarity_id}",
                    profession_id="artificer",
                    name=name,
                    output_kind="rune",
                    required_level=level,
                    grade=4,
                    rarity=rarity,
                    output_id=f"rune.varzeas.{family_id}",
                    output_family=family,
                    fixed_materials=(
                        MaterialRequirement(VARZEAS_ESSENCE, essence),
                        MaterialRequirement(VARZEAS_IRON, iron),
                        *(
                            (MaterialRequirement(VARZEAS_CATALYST_IV, catalyst, False),)
                            if catalyst else ()
                        ),
                        MaterialRequirement(VARZEAS_FRAGMENT_IV, fragments, False),
                    ),
                    fixed_crown_cost=cost,
                    description=f"{rarity} · {stat} · Grau IV",
                )
            )
    return recipes


RECIPE_DEFINITIONS = tuple(
    _equipment_recipes()
    + _vde_equipment_recipes()
    + _nareth_equipment_recipes()
    + _varzeas_equipment_recipes()
    + _alchemy_recipes()
    + _rune_recipes()
    + _vde_rune_recipes()
    + _nareth_rune_recipes()
    + _varzeas_rune_recipes()
    + _enchantment_recipes()
    + _vde_enchantment_recipes()
    + _nareth_enchantment_recipes()
    + _varzeas_enchantment_recipes()
    + _special_recipes()
)
RECIPE_BY_ID = {recipe.recipe_id: recipe for recipe in RECIPE_DEFINITIONS}
RECIPES_BY_PROFESSION = {
    profession_id: tuple(
        recipe for recipe in RECIPE_DEFINITIONS if recipe.profession_id == profession_id
    )
    for profession_id in PROFESSION_IDS
}


def required_pxp(level: int) -> int:
    """PXP needed for the transition from ``level`` to ``level + 1``."""
    if not 1 <= level < 30:
        raise ValueError("A profession transition level must be between 1 and 29.")
    return round_10(100 + 20 * level + 5 * level * level)


def profession_grade(level: int) -> int:
    if level < 1:
        return 0
    return max(
        grade
        for grade, minimum in ((1, 1), (2, 3), (3, 6), (4, 9), (5, 12), (6, 15))
        if level >= minimum
    )


def recipe_pxp_multiplier(current_level: int, recipe_grade: int) -> int:
    distance = profession_grade(current_level) - recipe_grade
    if distance <= 0:
        return 100
    if distance == 1:
        return 50
    if distance == 2:
        return 20
    return 0


def recipe_pxp(recipe_level: int, current_level: int, recipe_grade: int = 1) -> int:
    return (80 + 20 * recipe_level) * recipe_pxp_multiplier(current_level, recipe_grade) // 100


def apply_profession_pxp(level: int, pxp: int, gained: int, cap: int) -> tuple[int, int]:
    """Apply exact PXP, crossing levels without storing progress past the slot cap."""
    if not 1 <= level <= cap or pxp < 0 or gained < 0:
        raise ValueError("Invalid profession progression state.")
    if level >= cap:
        return cap, 0
    remaining = pxp + gained
    while level < cap:
        threshold = required_pxp(level)
        if remaining < threshold:
            return level, remaining
        remaining -= threshold
        level += 1
    return cap, 0


def profession_change_cost(character_level: int, *, replacement: bool) -> int:
    factor = D("1.00") if replacement else D("0.50")
    return round_10(D(crowns_per_level(character_level)) * factor)


def recipe_materials(recipe: RecipeDefinition, item_level: int) -> tuple[MaterialRequirement, ...]:
    if recipe.fixed_materials:
        return recipe.fixed_materials
    if recipe.output_kind != "equipment":
        return ()
    total = recipe.basic_materials * recipe.sw
    if recipe.primary_material_id is None or recipe.secondary_material_id is None:
        raise ValueError("Equipment recipe is missing its material proportion.")
    primary = int(
        (D(total) * recipe.primary_ratio + D("0.5")).to_integral_value(rounding=ROUND_FLOOR)
    )
    result = [
        MaterialRequirement(recipe.primary_material_id, primary),
        MaterialRequirement(recipe.secondary_material_id, total - primary),
    ]
    if recipe.catalyst_per_sw:
        result.append(
            MaterialRequirement(
                recipe.catalyst_material_id or CATALYST_I,
                recipe.catalyst_per_sw * recipe.sw,
                False,
            )
        )
    if recipe.fragment_per_sw:
        result.append(
            MaterialRequirement(
                recipe.fragment_material_id or FRAGMENT_I,
                recipe.fragment_per_sw * recipe.sw,
                False,
            )
        )
    return tuple(item for item in result if item.quantity > 0)


def recipe_crown_cost(recipe: RecipeDefinition, item_level: int) -> int:
    if recipe.fixed_crown_cost is not None:
        return recipe.fixed_crown_cost
    if recipe.output_kind != "equipment" or recipe.rarity is None:
        return 0
    return round_10(
        D(crowns_per_level(item_level)) * recipe.sw * RARITY_COST_FACTORS[recipe.rarity]
    )


def recipe_item_level(character_level: int, recipe_grade: int = 1) -> int:
    floors = (1, 11, 21, 31, 41, 51)
    ceilings = (10, 20, 30, 40, 50, 60)
    if not 1 <= recipe_grade <= 6:
        raise ValueError("Recipe grade must be between I and VI.")
    floor_level, ceiling = floors[recipe_grade - 1], ceilings[recipe_grade - 1]
    if character_level < floor_level:
        raise ValueError("Character does not meet the recipe grade level floor.")
    return min(character_level, ceiling)


def slot_cap(slot: ProfessionSlot | str) -> int:
    return SLOT_CAPS[ProfessionSlot(slot)]


def profession_name(profession_id: str) -> str:
    return PROFESSION_BY_ID[profession_id].name


def recipes_for(profession_id: str) -> tuple[RecipeDefinition, ...]:
    return RECIPES_BY_PROFESSION.get(profession_id, ())


def canonical_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPE_BY_ID.get(recipe_id)
