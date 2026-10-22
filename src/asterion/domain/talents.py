"""Authoritative Class Talent metadata and level-gated progression rules."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from decimal import Decimal

TALENT_POINT_LEVELS = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)
TALENT_CATEGORIES = ("Pressão", "Resistência", "Técnica")
IMPLEMENTED_TALENT_LEVELS = frozenset({5})


class TalentSelectionError(ValueError):
    """A persisted or proposed Talent selection is not active and legal."""


@dataclass(frozen=True, slots=True)
class TalentDefinition:
    talent_id: str
    character_class: str
    name: str
    level: int
    category: str
    description: str
    attack_percent: Decimal = Decimal(0)
    hp_percent: Decimal = Decimal(0)
    defense_percent: Decimal = Decimal(0)
    agility_percent: Decimal = Decimal(0)
    per_points: Decimal = Decimal(0)
    crit_points: Decimal = Decimal(0)
    evasion_points: Decimal = Decimal(0)
    block_points: Decimal = Decimal(0)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "_".join(
        "".join(char for char in part if char.isascii() and char.isalnum()).lower()
        for part in normalized.split()
    )


# Each tier is ordered Pressure, Resistance, Technique, matching the three
# category branches in the approved 49.5 Class Talent catalog.
_ROWS: dict[str, tuple[tuple[int, tuple[tuple[str, str], ...]], ...]] = {
    "sentinela": (
        (
            5,
            (
                ("Aço Desperto", "+1% ATQ"),
                ("Carne de Pedra", "+1% HP"),
                (
                    "Ritmo de Guarda",
                    "Retaliação válida concede +5% AGI até o fim do próximo turno.",
                ),
            ),
        ),
        (
            15,
            (
                ("Ponta Revidada", "Ação com Retaliação: +4 p.p. PER."),
                ("Placas Internas", "+2% DEF"),
                (
                    "Guarda Preparada",
                    "Após Defender reduzir Dano Direto, próxima Barreira em 2T +6%.",
                ),
            ),
        ),
        (
            25,
            (
                ("Pressão de Fissuras", "+3% Dano Direto contra alvo com −DEF."),
                ("Firme sob Impacto", "Ação inimiga que remove ≥8% HP concede +5% DEF por 1T."),
                ("Retaliação Persistente", "+1T de duração de Retaliação, sem carga extra."),
            ),
        ),
        (
            35,
            (
                ("Olho de Combate", "+2 p.p. CRIT"),
                ("Barreira Densa", "Barreiras recebidas +5%."),
                ("Contrapeso", "Após Retaliação, +4% DEF por 1T."),
            ),
        ),
        (
            45,
            (
                ("Ponta Penetrante", "+2 p.p. PER"),
                ("Postura de Ferro", "Defender +2 p.p."),
                ("Vigília", "Na primeira vez em que fica com ≤50% HP, recebe 1 Retaliação."),
            ),
        ),
        (
            55,
            (
                ("Punição Final", "+4% Dano Direto contra alvo com ≤40% HP."),
                ("Persistência", "Com ≤35% HP, recebe +7% DEF."),
                (
                    "Guarda Íntegra",
                    "Após Defender, próximo Debuff numérico removível antes do próximo turno "
                    "tem magnitude −10%.",
                ),
            ),
        ),
    ),
    "errante": (
        (
            5,
            (
                ("Fio Afiado", "+1% ATQ"),
                ("Passo Prudente", "+1% HP"),
                ("Instinto Rápido", "+3% AGI"),
            ),
        ),
        (
            15,
            (
                ("Brecha Exposta", "Ação com Oportunismo +4 p.p. PER."),
                ("Reflexo", "+1 p.p. Esquiva"),
                ("Sangue Frio", "Esquiva bem-sucedida: próximo Dano Direto em 2T +5 p.p. CRIT."),
            ),
        ),
        (
            25,
            (
                ("Precisão Cruel", "+2 p.p. CRIT"),
                ("Couro Leve", "+2% DEF"),
                ("Passos da Sombra", "Ao aplicar efeito negativo, +5% AGI até o próximo turno."),
            ),
        ),
        (
            35,
            (
                ("Oportunismo Ampliado", "Oportunismo +8%→+10%."),
                ("Sobrevivência", "Com ≤40% HP, recebe +5% DEF."),
                ("Desvio Ofensivo", "Após Esquiva, próximo Dano Direto +4 p.p. PER."),
            ),
        ),
        (
            45,
            (
                ("Fio Perfurante", "+2 p.p. PER"),
                ("Pele Endurecida", "−8% dano de DoT recebido."),
                ("Ritmo Predatório", "Após Oportunismo, +5% AGI no próximo turno."),
            ),
        ),
        (
            55,
            (
                ("Fim Próximo", "+4% Dano Direto contra alvo com ≤35% HP."),
                ("Primeiro Desvio", "Primeiro Dano Direto recebido no combate −8%."),
                (
                    "Instinto de Fuga",
                    "Na primeira vez com ≤30% HP, +10 p.p. Esquiva até o próximo turno.",
                ),
            ),
        ),
    ),
    "vigia": (
        (
            5,
            (
                ("Mão Firme", "+1% ATQ"),
                ("Sobrevivente das Trilhas", "+1% HP"),
                ("Passo do Caçador", "+3% AGI"),
            ),
        ),
        (
            15,
            (
                ("Olho Afiado", "+2 p.p. CRIT"),
                ("Postura Vigilante", "+2% DEF"),
                ("Mira Estável", "Mira +1T."),
            ),
        ),
        (
            25,
            (
                ("Perfuração Calculada", "+2 p.p. PER"),
                ("Antecipação", "Primeiro Dano Direto recebido −7%."),
                (
                    "Aquisição Rápida",
                    "Primeiro Dano Direto contra alvo sem Mira gera 1 Mira extra, 1×/alvo/combate.",
                ),
            ),
        ),
        (
            35,
            (
                ("Alvo Exposto", "Com ≥2 Mira, +3% Dano Direto."),
                ("Recuo Instintivo", "Na primeira vez com ≤40% HP, +8% DEF por 1T."),
                ("Visão Persistente", "Ao trocar alvo, preserva 1 Mira no anterior por 1T."),
            ),
        ),
        (
            45,
            (
                ("Ponto Fraco", "Com ≥3 Mira, +2 p.p. CRIT."),
                ("Couro de Campo", "−8% dano de DoT recebido."),
                ("Leitura de Movimento", "Ao aplicar −AGI, +5% AGI por 1T."),
            ),
        ),
        (
            55,
            (
                ("Disparo Implacável", "+4% Dano Direto contra alvo com ≤35% HP."),
                ("Último Horizonte", "Com ≤35% HP, recebe +6% DEF."),
                (
                    "Caçada Metódica",
                    "Ao atingir alvo com Mira máxima, próximo Dano Direto em 2T +3 p.p. PER.",
                ),
            ),
        ),
    ),
    "tecelao": (
        (
            5,
            (
                ("Fio Potente", "+1% ATQ"),
                ("Trama Vital", "+1% HP"),
                ("Passo Entre Fios", "+3% AGI"),
            ),
        ),
        (
            15,
            (
                ("Fenda Precisa", "+2 p.p. CRIT"),
                ("Véu Denso", "+2% DEF"),
                ("Trama Duradoura", "Janela de consumo de Trama 2→3T."),
            ),
        ),
        (
            25,
            (
                ("Fio Perfurante", "+2 p.p. PER"),
                ("Proteção Tecida", "Barreiras recebidas +5%."),
                ("Alternância Fluida", "Consumir Trama concede +5% AGI por 1T."),
            ),
        ),
        (
            35,
            (
                ("Trama Agressiva", "Trama consumida por dano +2 p.p. potência."),
                ("Reforço do Véu", "Enquanto sob Barreira, +5% DEF."),
                ("Fio Persistente", "Primeira Trama que expira sem uso no combate renova por 1T."),
            ),
        ),
        (
            45,
            (
                ("Ruptura Profunda", "Dano Direto contra alvo com DoT +3%."),
                ("Tecelagem Defensiva", "Primeira Barreira própria no combate +10%."),
                (
                    "Eco de Alternância",
                    "Consumir Trama com Arte diferente concede próximo ataque em 2T +3 p.p. PER.",
                ),
            ),
        ),
        (
            55,
            (
                (
                    "Sobrecarga Controlada",
                    "Dano que consome Trama contra alvo com ≤40% HP recebe +4% potência.",
                ),
                ("Véu de Emergência", "Na primeira vez com ≤30% HP, Barreira de 6% HP por 1T."),
                (
                    "Trama Precisa",
                    "Ofensiva consumida +2 p.p. CRIT; Cura/Barreira consumida +2% potência.",
                ),
            ),
        ),
    ),
    "oraculo": (
        (
            5,
            (
                ("Visão Cruel", "+1% ATQ"),
                ("Pressentimento Vital", "+1% HP"),
                ("Passos do Destino", "+3% AGI"),
            ),
        ),
        (
            15,
            (
                ("Presságio Cortante", "Presságio ofensivo consumido +2 p.p. PER."),
                ("Véu Cauteloso", "+2% DEF"),
                ("Sinal Persistente", "Presságio +1T."),
            ),
        ),
        (
            25,
            (
                ("Destino Exposto", "+2 p.p. CRIT"),
                ("Antevisão Defensiva", "Enquanto sob Barreira, +5% DEF."),
                ("Leitura dos Sinais", "Ao aplicar Presságio em inimigo, +5% AGI por 1T."),
            ),
        ),
        (
            35,
            (
                ("Profecia Dolorosa", "Presságio ofensivo consumido +2% potência."),
                ("Destino Adiado", "Primeiro Dano Direto recebido −7%."),
                (
                    "Presságio Flexível",
                    "Primeiro Presságio que expira sem uso no combate renova por 1T.",
                ),
            ),
        ),
        (
            45,
            (
                ("Fraqueza Prevista", "+3% Dano Direto contra alvo com Debuff."),
                ("Mente Velada", "Magnitude de Debuff numérico removível recebido −6%."),
                ("Sequência Profética", "Consumir Presságio concede +3% AGI por 1T."),
            ),
        ),
        (
            55,
            (
                ("Fim Anunciado", "+4% Dano Direto contra alvo com ≤35% HP."),
                ("Última Visão", "Na primeira vez com ≤30% HP, Barreira de 6% HP por 1T."),
                (
                    "Sinais Convergentes",
                    "Presságio defensivo consumido +3% potência; ofensivo consumido +2 p.p. CRIT.",
                ),
            ),
        ),
    ),
    "luminar": (
        (
            5,
            (
                ("Luz Incisiva", "+1% ATQ"),
                ("Vitalidade Solar", "+1% HP"),
                ("Clarão Ágil", "+3% AGI"),
            ),
        ),
        (
            15,
            (
                ("Julgamento Preciso", "Ofensiva fortalecida por Julgamento +2 p.p. CRIT."),
                ("Corpo Consagrado", "+2% DEF"),
                ("Contraluz Persistente", "Fulgor/Julgamento +1T."),
            ),
        ),
        (
            25,
            (
                ("Luz Perfurante", "+2 p.p. PER"),
                ("Égide Densa", "Barreiras aplicadas +4%."),
                ("Alternância Radiante", "Consumir Fulgor/Julgamento concede +4% AGI por 1T."),
            ),
        ),
        (
            35,
            (
                ("Veredito Ardente", "Dano Direto fortalecido por Julgamento +2% potência."),
                ("Cura Prudente", "Cura em alvo com ≤40% HP +5%."),
                (
                    "Ciclo Luminoso",
                    "Primeiro Fulgor/Julgamento que expira sem uso no combate renova por 1T.",
                ),
            ),
        ),
        (
            45,
            (
                ("Punição da Fraqueza", "+3% Dano Direto contra alvo com Cura reduzida."),
                ("Luz Protetora", "Enquanto sob Barreira, +5% DEF."),
                (
                    "Fluxo Restaurador",
                    "Cura efetiva consumindo Fulgor concede +4% DEF ao alvo por 1T.",
                ),
            ),
        ),
        (
            55,
            (
                ("Sentença Solar", "+4% Dano Direto contra alvo com ≤35% HP."),
                (
                    "Último Alvorecer",
                    "Na primeira vez com ≤30% HP, Cura de 5% HP sem Crit/triggers/bônus.",
                ),
                (
                    "Contraluz Perfeita",
                    "Fulgor consumido em Cura/Barreira +2% potência; Julgamento em Dano Direto "
                    "+2 p.p. PER.",
                ),
            ),
        ),
    ),
}


_STATIC_TALENT_MODIFIERS = {
    "aço desperto": {"attack_percent": Decimal("0.01")},
    "carne de pedra": {"hp_percent": Decimal("0.01")},
    "fio afiado": {"attack_percent": Decimal("0.01")},
    "passo prudente": {"hp_percent": Decimal("0.01")},
    "mão firme": {"attack_percent": Decimal("0.01")},
    "sobrevivente das trilhas": {"hp_percent": Decimal("0.01")},
    "fio potente": {"attack_percent": Decimal("0.01")},
    "trama vital": {"hp_percent": Decimal("0.01")},
    "visão cruel": {"attack_percent": Decimal("0.01")},
    "pressentimento vital": {"hp_percent": Decimal("0.01")},
    "luz incisiva": {"attack_percent": Decimal("0.01")},
    "vitalidade solar": {"hp_percent": Decimal("0.01")},
    "instinto rápido": {"agility_percent": Decimal("0.03")},
    "reflexo": {"evasion_points": Decimal("1")},
    "passo do caçador": {"agility_percent": Decimal("0.03")},
    "passo entre fios": {"agility_percent": Decimal("0.03")},
    "passos do destino": {"agility_percent": Decimal("0.03")},
    "clarão ágil": {"agility_percent": Decimal("0.03")},
    "placas internas": {"defense_percent": Decimal("0.02")},
    "olho afiado": {"crit_points": Decimal("2")},
    "postura vigilante": {"defense_percent": Decimal("0.02")},
    "fenda precisa": {"crit_points": Decimal("2")},
    "véu denso": {"defense_percent": Decimal("0.02")},
    "véu cauteloso": {"defense_percent": Decimal("0.02")},
    "corpo consagrado": {"defense_percent": Decimal("0.02")},
}


def _make_catalog() -> tuple[TalentDefinition, ...]:
    definitions: list[TalentDefinition] = []
    for character_class, tiers in _ROWS.items():
        for level, talents in tiers:
            if len(talents) != len(TALENT_CATEGORIES):
                raise RuntimeError(f"Talent tier {character_class}/{level} must have 3 entries")
            for category, (name, description) in zip(TALENT_CATEGORIES, talents, strict=True):
                static = _STATIC_TALENT_MODIFIERS.get(name.casefold(), {})
                definitions.append(
                    TalentDefinition(
                        f"talent.{character_class}.{_slug(name)}",
                        character_class,
                        name,
                        level,
                        category,
                        description,
                        **static,
                    )
                )
    return tuple(definitions)


TALENT_CATALOG = _make_catalog()
TALENT_DEFINITIONS = {definition.talent_id: definition for definition in TALENT_CATALOG}
TALENTS_BY_CLASS = {
    character_class: tuple(
        definition for definition in TALENT_CATALOG if definition.character_class == character_class
    )
    for character_class in _ROWS
}
TALENTS_BY_CLASS_AND_INDEX = {
    character_class: {index: talent for index, talent in enumerate(talents)}
    for character_class, talents in TALENTS_BY_CLASS.items()
}


def talent_points_at_level(level: int) -> int:
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 60:
        raise ValueError("Character level must be between 1 and 60.")
    return sum(required <= level for required in TALENT_POINT_LEVELS)


def validate_talent_choices(
    character_class: str,
    level: int,
    choices: tuple[tuple[int, str], ...] | list[tuple[int, str]],
) -> tuple[tuple[int, str], ...]:
    """Validate saved point slots and return their active, implemented choices.

    This codebase has no Legado state or transition yet, so it cannot prove that
    over-budget rows are legitimately dormant after an ascent. Such rows are
    rejected without deleting them; a future Legado implementation must add an
    explicit authority for dormant slots before they can be accepted here.
    """
    available_points = talent_points_at_level(level)
    if not isinstance(choices, (tuple, list)):
        raise TalentSelectionError("Talent choices must be a sequence.")
    seen_slots: set[int] = set()
    seen_talents: set[str] = set()
    active: list[tuple[int, str]] = []
    for choice in choices:
        if not isinstance(choice, (tuple, list)) or len(choice) != 2:
            raise TalentSelectionError("Invalid Talent choice record.")
        slot, talent_id = choice
        if (
            isinstance(slot, bool)
            or not isinstance(slot, int)
            or not 1 <= slot <= len(TALENT_POINT_LEVELS)
            or slot > available_points
            or not isinstance(talent_id, str)
            or not talent_id
            or slot in seen_slots
            or talent_id in seen_talents
        ):
            raise TalentSelectionError("Invalid or duplicate Talent choice.")
        definition = TALENT_DEFINITIONS.get(talent_id)
        if (
            definition is None
            or definition.character_class != character_class
            or definition.level > level
            or definition.level not in IMPLEMENTED_TALENT_LEVELS
            or definition.level > TALENT_POINT_LEVELS[slot - 1]
        ):
            raise TalentSelectionError("Talent choice is not eligible for this character.")
        seen_slots.add(slot)
        seen_talents.add(talent_id)
        active.append((slot, talent_id))
    return tuple(active)


def validate_active_talent_ids(
    character_class: str,
    level: int,
    talent_ids: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    """Validate IDs entering static attributes or a combat snapshot."""
    available_points = talent_points_at_level(level)
    if not isinstance(talent_ids, (tuple, list)) or len(talent_ids) > available_points:
        raise TalentSelectionError("Active Talent count exceeds available points.")
    if any(not isinstance(talent_id, str) or not talent_id for talent_id in talent_ids):
        raise TalentSelectionError("Invalid active Talent ID.")
    if len(set(talent_ids)) != len(talent_ids):
        raise TalentSelectionError("Duplicate active Talent ID.")
    for talent_id in talent_ids:
        definition = TALENT_DEFINITIONS.get(talent_id)
        if (
            definition is None
            or definition.character_class != character_class
            or definition.level > level
            or definition.level not in IMPLEMENTED_TALENT_LEVELS
        ):
            raise TalentSelectionError("Active Talent is not eligible for this character.")
    return tuple(talent_ids)


def active_talent_ids(
    character_class: str,
    level: int,
    choices: tuple[tuple[int, str], ...] | list[tuple[int, str]],
) -> tuple[str, ...]:
    return tuple(talent_id for _, talent_id in validate_talent_choices(
        character_class, level, choices
    ))


def static_talent_modifiers(
    character_class: str,
    level: int,
    talent_ids: tuple[str, ...] | list[str],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    definitions = [
        TALENT_DEFINITIONS[talent_id]
        for talent_id in validate_active_talent_ids(character_class, level, talent_ids)
    ]
    return _static_talent_modifier_totals(definitions)


def static_talent_secondary_modifiers(
    character_class: str,
    level: int,
    talent_ids: tuple[str, ...] | list[str],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return validated static PER, Crit, Evasion, and Block point bonuses."""
    definitions = [
        TALENT_DEFINITIONS[talent_id]
        for talent_id in validate_active_talent_ids(character_class, level, talent_ids)
    ]
    return _static_talent_secondary_modifier_totals(definitions)


def _static_talent_modifier_totals(
    definitions: tuple[TalentDefinition, ...] | list[TalentDefinition],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Sum static effects after an authority has selected the definitions.

    This lower-level helper deliberately does not decide eligibility. The public
    runtime path must use ``static_talent_modifiers`` above, which validates the
    saved choices before any modifier reaches attribute composition.
    """
    return (
        sum((definition.attack_percent for definition in definitions), Decimal(0)),
        sum((definition.hp_percent for definition in definitions), Decimal(0)),
        sum((definition.defense_percent for definition in definitions), Decimal(0)),
        sum((definition.agility_percent for definition in definitions), Decimal(0)),
    )


def _static_talent_secondary_modifier_totals(
    definitions: tuple[TalentDefinition, ...] | list[TalentDefinition],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Sum secondary percentage-point effects after controlled test selection."""
    return (
        sum((definition.per_points for definition in definitions), Decimal(0)),
        sum((definition.crit_points for definition in definitions), Decimal(0)),
        sum((definition.evasion_points for definition in definitions), Decimal(0)),
        sum((definition.block_points for definition in definitions), Decimal(0)),
    )
