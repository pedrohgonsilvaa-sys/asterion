"""Canonical Santuário do Nó Antigo encounters on the shared dungeon engine."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from asterion.domain.combat import (
    Combat,
    CombatDamageAura,
    CombatPhaseTrigger,
    CombatStatAura,
)
from asterion.domain.combat_math import StatMultipliers
from asterion.domain.dungeons import DIFFICULTIES
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import (
    VDE_OLD_KNOT_GUARDIAN,
    VDE_RADICULAR_SEAL,
    VDE_ROOT_CONTAINMENT,
    VDE_ROOTED_PRELATE,
    VDE_ROOTED_WATCHER,
    VDE_TANGLED_CUSTODIAN,
    VDE_WANDERING_BARK,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)

D = Decimal

SANCTUARY_FAMILY_ID = "dungeon.vde.santuario_no_antigo"
SANCTUARY_CONTENT_VERSION = "vde-1.0.5"
SANCTUARY_RULESET_VERSION = "dungeon-1.0"
SANCTUARY_LOCATION = "Santuário do Nó Antigo"
SANCTUARY_ENTRY_LOCATION = "Claustro das Raízes"
SANCTUARY_DISCOVERY_UNLOCK = SANCTUARY_FAMILY_ID
SANCTUARY_KNOWN_PATH_UNLOCK = SANCTUARY_DISCOVERY_UNLOCK
SANCTUARY_FIRST_CLEAR_PREFIX = f"{SANCTUARY_FAMILY_ID}.first_clear."
SANCTUARY_REWARD_PREFIX = f"{SANCTUARY_FAMILY_ID}.run."
SANCTUARY_CORE_ID = "material.vde.nucleo_no_antigo"
SANCTUARY_CORE_NAME = "Núcleo do Nó Antigo"
SANCTUARY_RECIPE_UNLOCK = "recipe.vde.santuario.guarda_no_antigo"
SANCTUARY_BRAZIER_LABEL = "Braseiro do Nó Silencioso"
SANCTUARY_CODEX_ENTRY = "codex.location.santuario_do_no_antigo"
SANCTUARY_BASIC_MATERIALS = (
    "material.vde.ferro_enredado",
    "material.vde.couro_musgoso",
    "material.vde.erva_de_turfa",
    "material.vde.resina_enredada",
)
SANCTUARY_CATALYST = "material.vde.catalisador_elite_ii"
SANCTUARY_FRAGMENT = "material.vde.fragmento_aprimoramento_ii"

SANCTUARY_ENVIRONMENTS = {
    1: "Galeria Estrangulada",
    2: "Câmara Invadida",
    3: "Custódio Enredado",
    4: "Câmara das Quatro Raízes",
    5: "Guardião do Nó Antigo",
}

_PRELATE_ROOT_KEYS = ("root_1", "root_2", "root_3", "root_4")
_GUARDIAN_SEAL_KEYS = ("seal_1", "seal_2", "seal_3")


def sanctuary_encounter_specs(
    ordinal: int,
    difficulty: str,
    initial_group_size: int,
    reference_level: int,
) -> tuple[CreatureCombatantSpec, ...]:
    if ordinal == 1:
        return (CreatureCombatantSpec(VDE_ROOTED_WATCHER, 18, "enemy"),)
    if ordinal == 2:
        return (
            CreatureCombatantSpec(VDE_ROOTED_WATCHER, 18, "watcher"),
            CreatureCombatantSpec(VDE_WANDERING_BARK, 18, "bark"),
        )
    if ordinal == 3:
        return (CreatureCombatantSpec(VDE_TANGLED_CUSTODIAN, 19, "enemy"),)
    if ordinal == 4:
        root_scale = StatMultipliers(D("0.20"), D(0), D(1), D(0))
        return (
            CreatureCombatantSpec(VDE_ROOTED_PRELATE, 19, "prelate"),
            *(
                CreatureCombatantSpec(
                    VDE_ROOT_CONTAINMENT,
                    19,
                    key,
                    stat_multipliers=root_scale,
                    passive=True,
                    required_for_victory=False,
                    defeat_on_zero=False,
                )
                for key in _PRELATE_ROOT_KEYS
            ),
        )
    if ordinal == 5:
        profile = DIFFICULTIES[difficulty]
        group_hp = D(1) + D("0.78") * (initial_group_size - 1)
        group_attack = D(1) + D("0.07") * (initial_group_size - 1)
        guardian_scale = StatMultipliers(
            D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
            profile.boss_attack_multiplier * group_attack,
            D(1),
            D(1),
        )
        seal_scale = StatMultipliers(D("0.25"), D(0), D(1), D(0))
        return (
            CreatureCombatantSpec(
                VDE_OLD_KNOT_GUARDIAN,
                20,
                "guardian",
                stat_multipliers=guardian_scale,
            ),
            *(
                CreatureCombatantSpec(
                    VDE_RADICULAR_SEAL,
                    20,
                    key,
                    stat_multipliers=seal_scale,
                    passive=True,
                    required_for_victory=False,
                    defeat_on_zero=False,
                    initially_inactive=True,
                )
                for key in _GUARDIAN_SEAL_KEYS
            ),
        )
    raise ValueError("Santuário encounter ordinal must be between 1 and 5.")


def create_sanctuary_combat(
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
    environment = SANCTUARY_ENVIRONMENTS[ordinal]
    combat = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        sanctuary_encounter_specs(
            ordinal, difficulty, initial_group_size, reference_level
        ),
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=environment,
        opening_log=f"🪢 {environment}",
        pressure_start_opportunity=(
            {"stable": 12, "fractured": 10, "rupture": 8}[difficulty]
            if ordinal == 5
            else 0
        ),
        pressure_cap=5 if ordinal == 5 else 0,
        party=party,
    )
    combat.configuration_snapshot = (combat.configuration_snapshot or {}) | {
        "active_arts": [
            {"slot": index + 1, "art_id": art_id}
            for index, art_id in enumerate(active_art_ids)
        ],
        "dungeon": {
            "family_id": SANCTUARY_FAMILY_ID,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        },
    }
    if ordinal == 4:
        combat.stat_auras = (
            CombatStatAura(
                "sanctuary.roots.prelate_defense",
                "defense",
                _PRELATE_ROOT_KEYS,
                ("prelate",),
                D("0.05"),
            ),
        )
    elif ordinal == 5:
        combat.enemy_actions["e0_fechamento_no"] = replace(
            combat.enemy_actions["e0_fechamento_no"], phase_ids=("III",)
        )
        combat.phase_id = "I"
        combat.damage_auras = (
            CombatDamageAura(
                "sanctuary.seals.guardian_damage_reduction",
                _GUARDIAN_SEAL_KEYS,
                ("guardian",),
                D("0.04"),
            ),
        )
        combat.phase_triggers = (
            CombatPhaseTrigger(
                "sanctuary.phase.ii",
                "guardian",
                D("0.70"),
                activate_fighter_keys=_GUARDIAN_SEAL_KEYS,
                phase_id="II",
            ),
            CombatPhaseTrigger(
                "sanctuary.phase.iii",
                "guardian",
                D("0.35"),
                revive_fighter_keys=_GUARDIAN_SEAL_KEYS,
                revive_hp_fraction=D("0.50"),
                phase_id="III",
            ),
        )
    return combat


def sanctuary_enemy_rewards(ordinal: int) -> tuple[tuple[str, int, str], ...]:
    rewards = {
        1: (("vigia_enraizado", 18, "uncommon"),),
        2: (("vigia_enraizado", 18, "uncommon"), ("casca_errante", 18, "uncommon")),
        3: (("custodio_enredado", 19, "elite"),),
        4: (("prelado_enraizado", 19, "elite"),),
        5: (("guardiao_no_antigo", 20, "boss"),),
    }
    try:
        return rewards[ordinal]
    except KeyError as exc:
        raise ValueError("Santuário encounter ordinal must be between 1 and 5.") from exc
