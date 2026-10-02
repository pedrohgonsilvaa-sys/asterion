"""Canonical Galerias do Vigia encounters on the shared combat engine."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import Combat, CombatDamageAura, CombatPhaseTrigger, CombatStatAura
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    CUSTODIO_PRIMEIRO_SELO,
    FACELESS_CUSTODIAN,
    GUARD_CONDUCTOR,
    PRECEPTOR_RACHADO,
    SEAL_GUARD_FRAGMENT,
    VIGIA,
    VIGIA_INTEGRO,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)

D = Decimal

GALLERIES_FAMILY_ID = "dungeon.tdo.galerias_vigia"
GALLERIES_CONTENT_VERSION = "tdo-1.0.11"
GALLERIES_RULESET_VERSION = "dungeon-1.0"
GALLERIES_LOCATION = "Galerias do Vigia"
GALLERIES_DISCOVERY_UNLOCK = GALLERIES_FAMILY_ID
GALLERIES_KNOWN_PATH_UNLOCK = "known_path.tdo.galerias_vigia"
GALLERIES_FIRST_CLEAR_PREFIX = f"{GALLERIES_FAMILY_ID}.first_clear."
GALLERIES_REWARD_PREFIX = f"{GALLERIES_FAMILY_ID}.run."
GALLERIES_RECIPE_UNLOCK = "recipe.tdo.galerias.guarda_primeiro_selo"
GALLERIES_CORE_ID = "material.tdo.nucleo_galerias_vigia"
GALLERIES_BRAZIER_LABEL = "Braseiro da Vigília"


def gallery_encounter_specs(
    ordinal: int, difficulty: str, initial_group_size: int, reference_level: int
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(VIGIA, 8, "enemy"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(VIGIA, 8, "enemy_1"),
            CreatureCombatantSpec(FACELESS_CUSTODIAN, 8, "enemy_2"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(VIGIA_INTEGRO, 9, "enemy"),)
    if ordinal == 4:
        passive_scale = StatMultipliers(D("0.30"), D(1), D(1), D(1))
        return (
            CreatureCombatantSpec(PRECEPTOR_RACHADO, 9, "preceptor"),
            CreatureCombatantSpec(
                GUARD_CONDUCTOR,
                9,
                "conductor_1",
                stat_multipliers=passive_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
            ),
            CreatureCombatantSpec(
                GUARD_CONDUCTOR,
                9,
                "conductor_2",
                stat_multipliers=passive_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
            ),
        )
    if ordinal == 5:
        profile = {
            "stable": (D(1), D(1)),
            "fractured": (D("1.15"), D("1.08")),
            "rupture": (D("1.30"), D("1.15")),
        }[difficulty]
        group_hp = D(1) + D("0.78") * (initial_group_size - 1)
        group_attack = D(1) + D("0.07") * (initial_group_size - 1)
        hp_factor = D(3) / D("2.20") * profile[0] * group_hp
        attack_factor = profile[1] * group_attack
        fragment_scale = StatMultipliers(D("0.25"), D(1), D(1), D(1))
        return (
            CreatureCombatantSpec(
                CUSTODIO_PRIMEIRO_SELO,
                10,
                "enemy",
                stat_multipliers=StatMultipliers(hp_factor, attack_factor, D(1), D(1)),
            ),
            CreatureCombatantSpec(
                SEAL_GUARD_FRAGMENT,
                reference_level,
                "fragment_1",
                stat_multipliers=fragment_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
                initially_inactive=True,
            ),
            CreatureCombatantSpec(
                SEAL_GUARD_FRAGMENT,
                reference_level,
                "fragment_2",
                stat_multipliers=fragment_scale,
                passive=True,
                required_for_victory=False,
                defeat_on_zero=False,
                initially_inactive=True,
            ),
        )
    raise ValueError("Galerias encounter ordinal must be between 1 and 5.")


def create_galleries_combat(
    combat_id: UUID,
    *,
    name: str,
    character_class: str,
    race: str,
    hp: Decimal,
    level: int,
    difficulty: str,
    reference_level: int,
    equipment: EquipmentConfigurationSnapshot,
    active_art_ids: tuple[str, ...],
    ordinal: int,
    run_seed: str,
    initial_group_size: int = 1,
    party: tuple[PlayerCombatantSpec, ...] | None = None,
) -> Combat:
    environments = {
        1: "Corredor de Guarda",
        2: "Junção dos Vigias",
        3: "Vigia Íntegro",
        4: "Câmara dos Condutores",
        5: "Custódio do Primeiro Selo",
    }
    state = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        gallery_encounter_specs(
            ordinal, difficulty, initial_group_size, reference_level
        ),
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=environments[ordinal],
        opening_log=f"🛡️ {environments[ordinal]}",
        pressure_start_opportunity=(
            {"stable": 12, "fractured": 10, "rupture": 8}[difficulty]
            if ordinal == 5
            else 0
        ),
        pressure_cap=5 if ordinal == 5 else 0,
        party=party,
    )
    state.configuration_snapshot = (state.configuration_snapshot or {}) | {
        "dungeon": {
            "family_id": GALLERIES_FAMILY_ID,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        }
    }
    if ordinal == 4:
        state.stat_auras = (
            CombatStatAura(
                aura_id="galleries.conductors.preceptor_defense",
                stat="defense",
                source_fighter_keys=("conductor_1", "conductor_2"),
                target_fighter_keys=("preceptor",),
                multiplier_per_source=D("0.10"),
            ),
        )
    if ordinal == 5:
        state.damage_auras = (
            CombatDamageAura(
                aura_id="galleries.fragments.boss_damage_reduction",
                source_fighter_keys=("fragment_1", "fragment_2"),
                target_fighter_keys=("enemy",),
                reduction_per_source=D("0.05"),
            ),
        )
        state.phase_triggers = (
            CombatPhaseTrigger(
                trigger_id="galleries.order_of_containment",
                source_fighter_key="enemy",
                hp_fraction_at_most=D("0.70"),
                activate_fighter_keys=("fragment_1", "fragment_2"),
            ),
            CombatPhaseTrigger(
                trigger_id="galleries.last_order",
                source_fighter_key="enemy",
                hp_fraction_at_most=D("0.35"),
                revive_fighter_keys=("fragment_1", "fragment_2"),
                revive_hp_fraction=D("0.50"),
            ),
        )
    return state


def gallery_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    if ordinal == 1:
        return (("vigia_rachado", 8, "common"),)
    if ordinal == 2:
        return (("vigia_rachado", 8, "common"), ("custodio_sem_rosto", 8, "uncommon"))
    if ordinal == 3:
        return (("vigia_integro", 9, "elite"),)
    if ordinal == 4:
        return (("preceptor_rachado", 9, "elite"),)
    if ordinal == 5:
        return (("custodio_primeiro_selo", 10, "boss"),)
    raise ValueError("Galerias encounter ordinal must be between 1 and 5.")
