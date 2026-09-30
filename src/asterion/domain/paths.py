"""Canonical character Paths and their inherent class-stat modifiers."""

from dataclasses import dataclass
from decimal import Decimal

D = Decimal

PATHS_BY_CLASS: dict[str, tuple[str, str]] = {
    "sentinela": ("bastiao", "devastador"),
    "errante": ("carrasco", "sabotador"),
    "vigia": ("atirador", "rastreador"),
    "tecelao": ("conjurador", "runico"),
    "oraculo": ("agoureiro", "invocador"),
    "luminar": ("guardiao", "inquisidor"),
}


@dataclass(frozen=True, slots=True)
class PathDefinition:
    path_id: str
    character_class: str
    name: str
    emoji: str
    specialty: str
    passive_name: str
    passive_summary: str
    hp: Decimal
    attack: Decimal
    defense: Decimal
    agility: Decimal

    def modifiers(self) -> tuple[tuple[str, Decimal], ...]:
        return (
            ("HP", self.hp),
            ("ATQ", self.attack),
            ("DEF", self.defense),
            ("AGI", self.agility),
        )


_DEFINITIONS = (
    PathDefinition(
        "bastiao",
        "sentinela",
        "Bastião",
        "🏰",
        "Defesa",
        "Fortaleza",
        "Barreiras aplicadas +10%; Defender que reduz Dano Direto e ativa Retaliação "
        "concede Barreira de 4% do HP Máximo.",
        D(".05"),
        D("-.05"),
        D(".07"),
        D("-.02"),
    ),
    PathDefinition(
        "devastador",
        "sentinela",
        "Devastador",
        "💥",
        "Ofensiva",
        "Ímpeto Doloroso",
        "Receber dano real de uma ação inimiga igual ou superior a 8% do HP Máximo "
        "fortalece a próxima Arte de Dano Direto em +12% por até 2T.",
        D("-.02"),
        D(".08"),
        D("-.04"),
        D(".02"),
    ),
    PathDefinition(
        "carrasco",
        "errante",
        "Carrasco",
        "☠️",
        "Execução",
        "Sentença",
        "Dano Direto contra alvo com até 40% do HP Máximo recebe +8% de Dano Final.",
        D("-.03"),
        D(".07"),
        D("-.02"),
        D(".02"),
    ),
    PathDefinition(
        "sabotador",
        "errante",
        "Sabotador",
        "🕷️",
        "Controle",
        "Interferência",
        "Debuffs não-CC com duração-base de 1–2T recebem +1T, até 3T.",
        D(".02"),
        D("-.02"),
        D(0),
        D(".05"),
    ),
    PathDefinition(
        "atirador",
        "vigia",
        "Atirador",
        "🎯",
        "Precisão",
        "Mira Perfeita",
        "Até 4 Miras no alvo; cada Mira concede +3 p.p. PER e 4 Miras também "
        "concedem +6 p.p. CRIT.",
        D("-.01"),
        D(".07"),
        D("-.03"),
        D(".02"),
    ),
    PathDefinition(
        "rastreador",
        "vigia",
        "Rastreador",
        "👣",
        "Rastreamento",
        "Rastros Múltiplos",
        "Até 2 Miras por alvo em até 3 alvos; aplicar DoT ou reduzir AGI também concede Mira.",
        D(".02"),
        D("-.01"),
        D(".02"),
        D(".03"),
    ),
    PathDefinition(
        "conjurador",
        "tecelao",
        "Conjurador",
        "🌀",
        "Ofensiva",
        "Convergência",
        "Trama consumida por dano concede +15% de potência; por Cura/Barreira, +6%.",
        D("-.03"),
        D(".08"),
        D("-.04"),
        D(0),
    ),
    PathDefinition(
        "runico",
        "tecelao",
        "Rúnico",
        "🔷",
        "Proteção",
        "Inscrição",
        "Trama consumida por Cura/Barreira concede +15% de potência; por dano, +6%.",
        D(".04"),
        D("-.04"),
        D(".05"),
        D("-.01"),
    ),
    PathDefinition(
        "agoureiro",
        "oraculo",
        "Agoureiro",
        "🦉",
        "Presságio",
        "Mau Presságio",
        "Presságio Ofensivo consumido concede +16% de potência; o Defensivo mantém +12%.",
        D("-.01"),
        D(".03"),
        D("-.01"),
        D(".02"),
    ),
    PathDefinition(
        "invocador",
        "oraculo",
        "Invocador",
        "🐺",
        "Manifestações",
        "Tríade",
        "Usar uma manifestação diferente da anterior dentro de 2T concede +12% de potência.",
        D(".03"),
        D("-.01"),
        D(".01"),
        D("-.01"),
    ),
    PathDefinition(
        "guardiao",
        "luminar",
        "Guardião",
        "🪬",
        "Suporte",
        "Aurora",
        "Fulgor em Cura/Barreira concede +15%; Julgamento em Dano Direto concede +6%.",
        D(".05"),
        D("-.05"),
        D(".05"),
        D("-.02"),
    ),
    PathDefinition(
        "inquisidor",
        "luminar",
        "Inquisidor",
        "⚖️",
        "Ofensiva",
        "Julgamento Implacável",
        "Julgamento em Dano Direto concede +15%; Fulgor em Cura/Barreira concede +6%.",
        D("-.03"),
        D(".08"),
        D("-.03"),
        D(".02"),
    ),
)

PATH_DEFINITIONS = {definition.path_id: definition for definition in _DEFINITIONS}
PATH_CLASS = {definition.path_id: definition.character_class for definition in _DEFINITIONS}


def paths_for_class(character_class: str) -> tuple[str, ...]:
    return PATHS_BY_CLASS.get(character_class, ())


def path_belongs_to_class(path_id: str | None, character_class: str) -> bool:
    return path_id is not None and PATH_CLASS.get(path_id) == character_class
