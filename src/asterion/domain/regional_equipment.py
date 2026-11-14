"""Regional weapon/shield templates (plan: equipamentos dropaveis por regiao, Etapas A+B).

The region lives in the *template*, never in item_level.  Every template points
to the shared mechanical ``weapon.type.base.*`` identity (hands, slot, tags), so
Weapon Proficiency keeps answering to the mechanical type, not to the name.
Names come from ASTERION_CATALOGO_REGIONAL_ARMAS_E_ARMADURAS.md (proposal names).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

REGION_IDS = {
    "tdo": "region.terras_do_ocaso",
    "vde": "region.vales_dos_enforcados",
    "nareth": "region.planicies_de_nareth",
    "varzeas": "region.varzeas_carmesins",
    "altos": "region.altos_cinereos",
    "confins": "region.confins_do_veu",
}
REGION_KEY_BY_DISPLAY = {
    "Terras do Ocaso": "tdo",
    "Vales dos Enforcados": "vde",
    "Planícies de Nareth": "nareth",
    "Várzeas Carmesins": "varzeas",
    "Altos Cinéreos": "altos",
    "Confins do Véu": "confins",
}

_WEAPON_NAMES = {
    "tdo": (
        ("espada", "Espada da Fuligem"),
        ("espada_de_guerra", "Espada de Guerra do Último Caminho"),
        ("adaga", "Adaga da Cinza"),
        ("adaga_de_arremesso", "Adaga do Peregrino"),
        ("chakram", "Chakram do Poente"),
        ("lamina_dupla", "Lâmina Dupla das Cinzas"),
        ("maca", "Maça do Posto"),
        ("martelo_de_guerra", "Martelo de Guerra do Carvão"),
        ("machado", "Machado do Caminhante"),
        ("machado_de_guerra", "Machado de Guerra da Estrada Morta"),
        ("lanca", "Lança do Marco Enegrecido"),
        ("alabarda", "Alabarda do Último Posto"),
        ("azagaia", "Azagaia do Caminho"),
        ("arco", "Arco das Cinzas"),
        ("besta_de_mao", "Besta de Mão do Vigia"),
        ("besta_pesada", "Besta Pesada do Caminho Velado"),
        ("cetro", "Cetro do Poente"),
        ("orbe", "Orbe da Cinza Verde"),
        ("cajado", "Cajado do Bosque Carbonizado"),
        ("escudo", "Escudo do Último Posto"),
    ),
    "vde": (
        ("espada", "Espada dos Laços"),
        ("espada_de_guerra", "Espada de Guerra do Nó Antigo"),
        ("adaga", "Adaga Enredada"),
        ("adaga_de_arremesso", "Adaga do Galho Suspenso"),
        ("chakram", "Chakram das Raízes"),
        ("lamina_dupla", "Lâmina Dupla do Nó"),
        ("maca", "Maça da Turfa"),
        ("martelo_de_guerra", "Martelo de Guerra das Forcas"),
        ("machado", "Machado do Vale"),
        ("machado_de_guerra", "Machado de Guerra das Raízes"),
        ("lanca", "Lança dos Galhos Suspensos"),
        ("alabarda", "Alabarda dos Enforcados"),
        ("azagaia", "Azagaia Enredada"),
        ("arco", "Arco das Copas"),
        ("besta_de_mao", "Besta de Mão do Caçador Enredado"),
        ("besta_pesada", "Besta Pesada dos Laços"),
        ("cetro", "Cetro do Nó Velado"),
        ("orbe", "Orbe da Turfa Profunda"),
        ("cajado", "Cajado das Raízes Suspensas"),
        ("escudo", "Escudo do Berço Enredado"),
    ),
    "nareth": (
        ("espada", "Espada do Meridiano"),
        ("espada_de_guerra", "Espada de Guerra do Horizonte"),
        ("adaga", "Adaga de Marco"),
        ("adaga_de_arremesso", "Adaga da Referência"),
        ("chakram", "Chakram do Meridiano"),
        ("lamina_dupla", "Lâmina Dupla do Horizonte"),
        ("maca", "Maça da Câmara"),
        ("martelo_de_guerra", "Martelo de Guerra do Marco"),
        ("machado", "Machado do Horizonte"),
        ("machado_de_guerra", "Machado de Guerra da Linha"),
        ("lanca", "Lança do Meridiano"),
        ("alabarda", "Alabarda da Câmara Invertida"),
        ("azagaia", "Azagaia do Marco"),
        ("arco", "Arco do Horizonte"),
        ("besta_de_mao", "Besta de Mão do Observador"),
        ("besta_pesada", "Besta Pesada do Horizonte"),
        ("cetro", "Cetro da Referência"),
        ("orbe", "Orbe do Meridiano"),
        ("cajado", "Cajado da Linha Distante"),
        ("escudo", "Escudo do Marco Invertido"),
    ),
    "varzeas": (
        ("espada", "Espada da Salmoura"),
        ("espada_de_guerra", "Espada de Guerra do Dique"),
        ("adaga", "Adaga Ferruginosa"),
        ("adaga_de_arremesso", "Adaga do Porto"),
        ("chakram", "Chakram das Válvulas"),
        ("lamina_dupla", "Lâmina Dupla da Transferência"),
        ("maca", "Maça do Dique"),
        ("martelo_de_guerra", "Martelo de Guerra das Válvulas"),
        ("machado", "Machado da Ferrugem"),
        ("machado_de_guerra", "Machado de Guerra da Salmoura"),
        ("lanca", "Lança do Porto"),
        ("alabarda", "Alabarda das Válvulas"),
        ("azagaia", "Azagaia da Várzea"),
        ("arco", "Arco da Salmoura"),
        ("besta_de_mao", "Besta de Mão do Porto"),
        ("besta_pesada", "Besta Pesada de Transferência"),
        ("cetro", "Cetro das Válvulas"),
        ("orbe", "Orbe da Restituição"),
        ("cajado", "Cajado da Várzea"),
        ("escudo", "Escudo do Dique"),
    ),
    "altos": (
        ("espada", "Espada do Contrapeso"),
        ("espada_de_guerra", "Espada de Guerra da Pedreira"),
        ("adaga", "Adaga da Escora"),
        ("adaga_de_arremesso", "Adaga do Contraforte"),
        ("chakram", "Chakram da Pedreira"),
        ("lamina_dupla", "Lâmina Dupla do Contrapeso"),
        ("maca", "Maça do Contrapeso"),
        ("martelo_de_guerra", "Martelo de Guerra da Pedreira"),
        ("machado", "Machado de Escora"),
        ("machado_de_guerra", "Machado de Guerra do Contraforte"),
        ("lanca", "Lança da Pedreira"),
        ("alabarda", "Alabarda dos Altos"),
        ("azagaia", "Azagaia do Contrapeso"),
        ("arco", "Arco da Pedreira"),
        ("besta_de_mao", "Besta de Mão da Escora"),
        ("besta_pesada", "Besta Pesada da Pedreira"),
        ("cetro", "Cetro do Contraforte"),
        ("orbe", "Orbe dos Altos Cinéreos"),
        ("cajado", "Cajado da Pedreira"),
        ("escudo", "Escudo do Contraforte"),
    ),
    "confins": (
        ("espada", "Espada da Baliza"),
        ("espada_de_guerra", "Espada de Guerra do Último Protocolo"),
        ("adaga", "Adaga da Marcha"),
        ("adaga_de_arremesso", "Adaga das Duas Versões"),
        ("chakram", "Chakram do Véu"),
        ("lamina_dupla", "Lâmina Dupla da Travessia"),
        ("maca", "Maça do Último Protocolo"),
        ("martelo_de_guerra", "Martelo de Guerra da Baliza"),
        ("machado", "Machado da Marcha"),
        ("machado_de_guerra", "Machado de Guerra do Véu"),
        ("lanca", "Lança da Travessia"),
        ("alabarda", "Alabarda da Última Vigília"),
        ("azagaia", "Azagaia da Marcha"),
        ("arco", "Arco do Retorno"),
        ("besta_de_mao", "Besta de Mão da Baliza"),
        ("besta_pesada", "Besta Pesada do Véu"),
        ("cetro", "Cetro da Baliza"),
        ("orbe", "Orbe das Duas Versões"),
        ("cajado", "Cajado do Retorno"),
        ("escudo", "Escudo da Última Vigília"),
    ),
}


@dataclass(frozen=True, slots=True)
class RegionalWeaponTemplate:
    template_id: str
    region_key: str
    region_id: str
    weapon_type_id: str
    display_name: str


REGIONAL_WEAPON_TEMPLATES = tuple(
    RegionalWeaponTemplate(
        template_id=f"equipment.{region_key}.weapon.{slug}",
        region_key=region_key,
        region_id=REGION_IDS[region_key],
        weapon_type_id=f"weapon.type.base.{slug}",
        display_name=name,
    )
    for region_key, entries in _WEAPON_NAMES.items()
    for slug, name in entries
)
_BY_REGION = {
    key: tuple(t for t in REGIONAL_WEAPON_TEMPLATES if t.region_key == key) for key in REGION_IDS
}
_BY_ID = {t.template_id: t for t in REGIONAL_WEAPON_TEMPLATES}


def regional_weapon_templates(region_key: str) -> tuple[RegionalWeaponTemplate, ...]:
    try:
        return _BY_REGION[region_key]
    except KeyError:
        raise ValueError(f"unknown equipment region {region_key!r}") from None


def regional_weapon_template(template_id: str) -> RegionalWeaponTemplate | None:
    return _BY_ID.get(template_id)


# Accessories and Artifacts: 3 + 3 per region (drop pool).  Special-recipe
# Artifacts are crafted/campaign-only and deliberately NOT in the drop pool.
_JEWEL_NAMES = {
    "tdo": (
        ("Selo Enegrecido", "Selo do Galho Morto", "Selo do Poente"),
        ("Relicário de Cinzas", "Relicário da Cinza Verde", "Relicário da Âncora Velada"),
    ),
    "vde": (
        ("Selo dos Laços", "Selo do Caminho Enredado", "Selo da Rede Antiga"),
        ("Relicário Enredado", "Relicário do Nó Velado", "Relicário da Pedra Pulsante"),
    ),
    "nareth": (
        ("Selo do Eixo", "Selo do Meridiano", "Selo do Eixo Estável"),
        (
            "Relicário de Referência",
            "Relicário da Distância Certa",
            "Relicário da Referência Perdida",
        ),
    ),
    "varzeas": (
        ("Selo de Transferência", "Selo dos Diques", "Selo da Matriz Estável"),
        ("Relicário de Restituição", "Relicário do Horto Estéril", "Relicário da Persistência"),
    ),
    "altos": (
        ("Selo da Prioridade", "Selo da Carga Compartilhada", "Selo da Rede Sustentada"),
        (
            "Relicário da Continuidade",
            "Relicário do Peso Distribuído",
            "Relicário da Ordem Interrompida",
        ),
    ),
    "confins": (
        ("Selo de Referência", "Selo do Marco Válido", "Selo da Referência Presente"),
        (
            "Relicário de Duas Leituras",
            "Relicário do Registro Incompleto",
            "Relicário da Ordem Findada",
        ),
    ),
}


def _slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "_".join(plain.lower().split())


@dataclass(frozen=True, slots=True)
class RegionalJewelTemplate:
    template_id: str
    region_key: str
    region_id: str
    slot: str
    display_name: str


REGIONAL_JEWEL_TEMPLATES = tuple(
    RegionalJewelTemplate(
        template_id=f"equipment.{region_key}.{kind}.{_slug(name)}",
        region_key=region_key,
        region_id=REGION_IDS[region_key],
        slot=slot,
        display_name=name,
    )
    for region_key, (accessories, artifacts) in _JEWEL_NAMES.items()
    for kind, slot, names in (
        ("accessory", "Acessório", accessories),
        ("artifact", "Artefato", artifacts),
    )
    for name in names
)


def regional_jewel_templates(region_key: str) -> tuple[RegionalJewelTemplate, ...]:
    if region_key not in REGION_IDS:
        raise ValueError(f"unknown equipment region {region_key!r}")
    return tuple(t for t in REGIONAL_JEWEL_TEMPLATES if t.region_key == region_key)


# Armor: each region lists 16 pieces in four groups of four slots (Cabeça, Torso, Mãos,
# Pés): Veste, Leve, Média, Pesada.  The class belongs to the template (spec Classes de
# Armadura v1.0.0 §1, §8) and is derived from that grouping, never stored per item.
ARMOR_CLASSES = ("veste", "leve", "media", "pesada")
ARMOR_SLOTS = ("Cabeça", "Torso", "Mãos", "Pés")
# Spec §2: percentage points of (Esquiva, Bloqueio) added per equipped piece.
ARMOR_CLASS_BONUS = {
    "veste": ("1.00", "0"),
    "leve": ("0.75", "0.25"),
    "media": ("0.50", "0.50"),
    "pesada": ("0", "1.00"),
}
_ARMOR_NAMES = {
    "tdo": (
        ("Cabeça", "Capuz das Cinzas"),
        ("Torso", "Veste do Caminhante"),
        ("Mãos", "Luvas de Fuligem"),
        ("Pés", "Botas da Estrada"),
        ("Cabeça", "Elmo Leve da Fuligem"),
        ("Torso", "Couraça Leve do Caminho"),
        ("Mãos", "Manoplas Leves do Caminhante"),
        ("Pés", "Passos Leves da Cinza"),
        ("Cabeça", "Elmo Médio do Último Posto"),
        ("Torso", "Couraça Média da Estrada"),
        ("Mãos", "Manoplas Médias do Poente"),
        ("Pés", "Grevas Médias da Fuligem"),
        ("Cabeça", "Elmo Pesado do Contraforte"),
        ("Torso", "Couraça Pesada das Cinzas"),
        ("Mãos", "Manoplas Pesadas do Último Posto"),
        ("Pés", "Grevas Pesadas do Caminho"),
    ),
    "vde": (
        ("Cabeça", "Capuz Musgoso"),
        ("Torso", "Veste da Mata Suspensa"),
        ("Mãos", "Luvas de Turfa"),
        ("Pés", "Botas dos Laços"),
        ("Cabeça", "Capuz Leve das Copas"),
        ("Torso", "Veste Leve dos Enforcados"),
        ("Mãos", "Luvas Leves do Musgo"),
        ("Pés", "Botas Leves da Turfa"),
        ("Cabeça", "Elmo Médio do Nó"),
        ("Torso", "Couraça Média do Vale"),
        ("Mãos", "Manoplas Médias Enredadas"),
        ("Pés", "Grevas Médias dos Laços"),
        ("Cabeça", "Elmo Pesado dos Enforcados"),
        ("Torso", "Couraça Pesada das Raízes"),
        ("Mãos", "Manoplas Pesadas do Nó Antigo"),
        ("Pés", "Grevas Pesadas da Mata Suspensa"),
    ),
    "nareth": (
        ("Cabeça", "Capuz do Horizonte"),
        ("Torso", "Veste do Meridiano"),
        ("Mãos", "Luvas do Marco"),
        ("Pés", "Botas da Linha"),
        ("Cabeça", "Elmo Leve do Meridiano"),
        ("Torso", "Couraça Leve do Horizonte"),
        ("Mãos", "Manoplas Leves do Marco"),
        ("Pés", "Grevas Leves da Referência"),
        ("Cabeça", "Elmo Médio da Câmara"),
        ("Torso", "Couraça Média do Meridiano"),
        ("Mãos", "Manoplas Médias do Horizonte"),
        ("Pés", "Grevas Médias do Marco"),
        ("Cabeça", "Elmo Pesado da Câmara Invertida"),
        ("Torso", "Couraça Pesada do Horizonte"),
        ("Mãos", "Manoplas Pesadas do Meridiano"),
        ("Pés", "Grevas Pesadas da Linha"),
    ),
    "varzeas": (
        ("Cabeça", "Capuz de Junco"),
        ("Torso", "Veste Encerada"),
        ("Mãos", "Luvas de Várzea"),
        ("Pés", "Botas da Salmoura"),
        ("Cabeça", "Capuz Leve do Junco"),
        ("Torso", "Veste Leve Encerada"),
        ("Mãos", "Luvas Leves da Várzea"),
        ("Pés", "Botas Leves da Salmoura"),
        ("Cabeça", "Elmo Médio das Válvulas"),
        ("Torso", "Couraça Média das Várzeas"),
        ("Mãos", "Manoplas Médias Ferruginosas"),
        ("Pés", "Grevas Médias do Porto"),
        ("Cabeça", "Elmo Pesado da Transferência"),
        ("Torso", "Couraça Pesada do Dique"),
        ("Mãos", "Manoplas Pesadas da Ferrugem"),
        ("Pés", "Grevas Pesadas da Salmoura"),
    ),
    "altos": (
        ("Cabeça", "Capuz Cinéreo"),
        ("Torso", "Veste da Pedreira"),
        ("Mãos", "Luvas de Escora"),
        ("Pés", "Botas do Contraforte"),
        ("Cabeça", "Elmo Leve dos Altos"),
        ("Torso", "Couraça Leve da Pedreira"),
        ("Mãos", "Manoplas Leves de Escora"),
        ("Pés", "Grevas Leves do Contrapeso"),
        ("Cabeça", "Elmo Médio do Contraforte"),
        ("Torso", "Couraça Média dos Altos"),
        ("Mãos", "Manoplas Médias da Pedreira"),
        ("Pés", "Grevas Médias de Escora"),
        ("Cabeça", "Elmo Pesado do Contrapeso"),
        ("Torso", "Couraça Pesada do Contraforte"),
        ("Mãos", "Manoplas Pesadas dos Altos"),
        ("Pés", "Grevas Pesadas da Pedreira"),
    ),
    "confins": (
        ("Cabeça", "Capuz do Véu"),
        ("Torso", "Veste da Travessia"),
        ("Mãos", "Luvas da Marcha"),
        ("Pés", "Botas do Retorno"),
        ("Cabeça", "Capuz Leve da Baliza"),
        ("Torso", "Veste Leve do Véu"),
        ("Mãos", "Luvas Leves da Marcha"),
        ("Pés", "Botas Leves da Travessia"),
        ("Cabeça", "Elmo Médio da Baliza"),
        ("Torso", "Couraça Média do Retorno"),
        ("Mãos", "Manoplas Médias do Véu"),
        ("Pés", "Grevas Médias da Marcha"),
        ("Cabeça", "Elmo Pesado da Última Vigília"),
        ("Torso", "Couraça Pesada das Duas Versões"),
        ("Mãos", "Manoplas Pesadas da Baliza"),
        ("Pés", "Grevas Pesadas do Retorno"),
    ),
}



@dataclass(frozen=True, slots=True)
class RegionalArmorTemplate:
    template_id: str
    region_key: str
    region_id: str
    slot: str
    display_name: str
    armor_class: str


def _build_armor_templates() -> tuple[RegionalArmorTemplate, ...]:
    templates = []
    for region_key, entries in _ARMOR_NAMES.items():
        if len(entries) != 16:
            raise ValueError(f"region {region_key!r} must list 16 armor pieces")
        for index, (slot, name) in enumerate(entries):
            if slot != ARMOR_SLOTS[index % 4]:
                raise ValueError(f"armor {name!r} is out of slot order")
            templates.append(
                RegionalArmorTemplate(
                    template_id=f"equipment.{region_key}.armor.{_slug(slot)}.{_slug(name)}",
                    region_key=region_key,
                    region_id=REGION_IDS[region_key],
                    slot=slot,
                    display_name=name,
                    armor_class=ARMOR_CLASSES[index // 4],
                )
            )
    return tuple(templates)


REGIONAL_ARMOR_TEMPLATES = _build_armor_templates()
_ARMOR_CLASS_BY_TEMPLATE_ID = {t.template_id: t.armor_class for t in REGIONAL_ARMOR_TEMPLATES}

# Legacy Terras do Ocaso armor (no template_id on the stored item), spec §7.
LEGACY_ARMOR_CLASS_BY_NAME = {
    "Capuz das Cinzas": "veste",
    "Veste do Caminhante": "veste",
    "Luvas de Fuligem": "veste",
    "Botas da Estrada": "veste",
    "Elmo de Fuligem": "leve",
    "Couraça de Fuligem": "leve",
    "Manoplas de Fuligem": "leve",
    "Passos de Fuligem": "leve",
}


_REGION_LABEL_BY_ID = {
    REGION_IDS[key]: display for display, key in REGION_KEY_BY_DISPLAY.items()
}


def region_label(region_id: str | None) -> str | None:
    """Display name of a region id, or None when the item carries no known Region."""
    return _REGION_LABEL_BY_ID.get(region_id or "")


def armor_class_of(
    *, slot: str | None, template_id: str | None = None, item_name: str | None = None
) -> str | None:
    """Armor class of an item, or None (weapons, accessories, artifacts, unknown)."""
    if slot not in ARMOR_SLOTS:
        return None
    if template_id is not None:
        return _ARMOR_CLASS_BY_TEMPLATE_ID.get(template_id)
    return LEGACY_ARMOR_CLASS_BY_NAME.get(item_name or "")


def regional_armor_templates(region_key: str) -> tuple[RegionalArmorTemplate, ...]:
    if region_key not in REGION_IDS:
        raise ValueError(f"unknown equipment region {region_key!r}")
    return tuple(t for t in REGIONAL_ARMOR_TEMPLATES if t.region_key == region_key)
