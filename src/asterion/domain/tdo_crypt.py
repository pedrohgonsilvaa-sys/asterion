"""Canonical Cripta do Ocaso encounters composed on the shared combat engine."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatStatAura
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    GUARDIAO_LAPIDES,
    LAPIDE_SEM_NOME,
    PROFANADOR_CALCINADO,
    SEM_NOME,
    CreatureCombatantSpec,
    create_creature_party_combat,
)

D = Decimal


@dataclass(frozen=True, slots=True)
class CryptEncounter:
    ordinal: int
    environment: str
    definition_id: str
    enemy_levels: tuple[int, ...]


CRYPT_ENCOUNTERS = {
    1: CryptEncounter(1, "Vestíbulo Raspado", "crypt.entrada", (4,)),
    2: CryptEncounter(2, "Ossário da Fuligem", "crypt.ossario", (5, 5)),
    3: CryptEncounter(3, "Guardião das Lápides", "guardiao_lapides", (6,)),
    4: CryptEncounter(4, "Câmara dos Nomes", "crypt.camadas", (6, 6, 6, 6, 6)),
    5: CryptEncounter(5, "O Último Guardião", "sem_nome", (7,)),
}


def encounter_specs(ordinal: int, difficulty: str) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(PROFANADOR_CALCINADO, 4, "enemy"),)
    if ordinal == 2:
        from asterion.domain.road import GHOUL

        return (
            CreatureCombatantSpec(PROFANADOR_CALCINADO, 5, "enemy_1"),
            CreatureCombatantSpec(GHOUL, 5, "enemy_2"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(GUARDIAO_LAPIDES, 6, "enemy"),)
    if ordinal == 4:
        prof_factors = StatMultipliers(D(1), D(1), D(1), D(1))
        tomb_factors = StatMultipliers(D("0.20"), D(1), D("0.80"), D(1))
        return (
            CreatureCombatantSpec(
                PROFANADOR_CALCINADO, 6, "enemy_1", stat_multipliers=prof_factors
            ),
            CreatureCombatantSpec(
                PROFANADOR_CALCINADO, 6, "enemy_2", stat_multipliers=prof_factors
            ),
            *(
                CreatureCombatantSpec(
                    LAPIDE_SEM_NOME,
                    6,
                    f"tomb_{index}",
                    stat_multipliers=tomb_factors,
                    passive=True,
                    required_for_victory=False,
                    defeat_on_zero=False,
                )
                for index in range(1, 4)
            ),
        )
    if ordinal == 5:
        profile = {
            "stable": (D(1), D(1)),
            "fractured": (D("1.15"), D("1.08")),
            "rupture": (D("1.30"), D("1.15")),
        }[difficulty]
        hp_multiplier, attack_multiplier = profile
        boss_factors = StatMultipliers(
            D(3) / D("2.20") * hp_multiplier,
            attack_multiplier,
            D(1),
            D(1),
        )
        return (CreatureCombatantSpec(SEM_NOME, 7, "enemy", stat_multipliers=boss_factors),)
    raise ValueError("Crypt encounter ordinal must be between 1 and 5.")


def create_crypt_combat(
    combat_id: UUID,
    *,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    level: int,
    difficulty: str,
    equipment: EquipmentConfigurationSnapshot,
    active_art_ids: tuple[str, ...],
    ordinal: int,
    run_seed: str,
) -> Combat:
    definition = CRYPT_ENCOUNTERS[ordinal]
    state = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        encounter_specs(ordinal, difficulty),
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=definition.environment,
        opening_log=f"⛓️ {definition.environment}",
        pressure_start_opportunity=(
            {"stable": 12, "fractured": 10, "rupture": 8}[difficulty] if ordinal == 5 else 0
        ),
        pressure_cap=5 if ordinal == 5 else 0,
    )
    state.configuration_snapshot = (state.configuration_snapshot or {}) | {
        "active_arts": [
            {"slot": index + 1, "art_id": art_id} for index, art_id in enumerate(active_art_ids)
        ],
        "dungeon": {
            "family_id": "dungeon.tdo.cripta_ocaso",
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
        },
    }
    if ordinal == 4:
        state.stat_auras = (
            CombatStatAura(
                aura_id="crypt.tombstones.defense",
                stat="defense",
                source_fighter_keys=("tomb_1", "tomb_2", "tomb_3"),
                target_fighter_keys=("enemy_1", "enemy_2"),
                multiplier_per_source=D("0.05"),
            ),
        )
    return state


def enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    """Canonical eligible enemy XP sources; passive tombs are intentionally absent."""
    if ordinal == 1:
        return (("profanador_calcinado", 4, "common"),)
    if ordinal == 2:
        return (("profanador_calcinado", 5, "common"), ("carnical_fuligem", 5, "common"))
    if ordinal == 3:
        return (("guardiao_lapides", 6, "elite"),)
    if ordinal == 4:
        return (("profanador_calcinado", 6, "common"),) * 2
    if ordinal == 5:
        return (("sem_nome", 7, "boss"),)
    raise ValueError("Crypt encounter ordinal must be between 1 and 5.")
