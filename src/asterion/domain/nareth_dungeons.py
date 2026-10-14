"""Canonical Nareth dungeon encounters on the shared dungeon/combat engine."""

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
    NARETH_CHANNEL_SCARAB,
    NARETH_DITCH_WANDERER,
    NARETH_DUNGEON_BESTIARY_CREATURES,
    NARETH_INVERTED_HUSK,
    NARETH_MERIDIAN_WATCHER,
    Creature,
    CreatureCombatantSpec,
    PlayerCombatantSpec,
    create_creature_party_combat,
)

D = Decimal

NARETH_GALLERIES_FAMILY_ID = "dungeon.nareth.galerias_meridiano"
NARETH_GALLERIES_CONTENT_VERSION = "nareth-1.0.2"
NARETH_GALLERIES_RULESET_VERSION = "dungeon-1.0"
NARETH_GALLERIES_LOCATION = "Galerias do Meridiano"
NARETH_GALLERIES_DISCOVERY_UNLOCK = NARETH_GALLERIES_FAMILY_ID
NARETH_GALLERIES_KNOWN_PATH_UNLOCK = "known_path.nareth.galerias_meridiano"
NARETH_GALLERIES_FIRST_CLEAR_PREFIX = f"{NARETH_GALLERIES_FAMILY_ID}.first_clear."
NARETH_GALLERIES_REWARD_PREFIX = f"{NARETH_GALLERIES_FAMILY_ID}.run."
NARETH_GALLERIES_CORE_ID = "material.nareth.nucleo_galerias_meridiano"
NARETH_GALLERIES_CORE_NAME = "Núcleo das Galerias do Meridiano"
NARETH_GALLERIES_RECIPE_UNLOCK = "recipe.nareth.galerias.relicario_circuito_retornado"
NARETH_GALLERIES_BRAZIER_LABEL = "Braseiro da Junção Circular"
NARETH_GALLERIES_CODEX_ENTRY = "codex.location.galerias_do_meridiano"

NARETH_OBSERVATORY_FAMILY_ID = "dungeon.nareth.observatorio_afundado"
NARETH_OBSERVATORY_CONTENT_VERSION = "nareth-1.0.2"
NARETH_OBSERVATORY_RULESET_VERSION = "dungeon-1.0"
NARETH_OBSERVATORY_DUNGEON_LOCATION = "Observatório Afundado"
NARETH_OBSERVATORY_DISCOVERY_UNLOCK = NARETH_OBSERVATORY_FAMILY_ID
NARETH_OBSERVATORY_KNOWN_PATH_UNLOCK = "known_path.nareth.observatorio_afundado"
NARETH_OBSERVATORY_FIRST_CLEAR_PREFIX = f"{NARETH_OBSERVATORY_FAMILY_ID}.first_clear."
NARETH_OBSERVATORY_REWARD_PREFIX = f"{NARETH_OBSERVATORY_FAMILY_ID}.run."
NARETH_OBSERVATORY_CORE_ID = "material.nareth.nucleo_observatorio_afundado"
NARETH_OBSERVATORY_CORE_NAME = "Núcleo do Observatório Afundado"
NARETH_OBSERVATORY_RECIPE_UNLOCK = "recipe.nareth.observatorio.guarda_referencia"
NARETH_OBSERVATORY_BRAZIER_LABEL = "Braseiro do Prumo Afundado"
NARETH_OBSERVATORY_CODEX_ENTRY = "codex.location.observatorio_afundado"

NARETH_DUNGEON_BASIC_MATERIALS = (
    "material.nareth.bronze_de_marco",
    "material.nareth.couro_de_horizonte",
    "material.nareth.erva_de_vento",
    "material.nareth.po_de_eixo",
)
NARETH_DUNGEON_CATALYST = "material.nareth.catalisador_elite_iii"
NARETH_DUNGEON_FRAGMENT = "material.nareth.fragmento_aprimoramento_iii"

NARETH_GALLERIES_ENVIRONMENTS = {
    1: "Corredor de Serviço",
    2: "Junção Circular",
    3: "Escavador do Eixo",
    4: "Circuito Marcado",
    5: "O Que Retorna",
}
NARETH_OBSERVATORY_ENVIRONMENTS = {
    1: "Câmara Inclinada",
    2: "Poço de Alinhamento",
    3: "Custódio do Meridiano",
    4: "Sala de Recalibração",
    5: "Guardião da Referência",
}

NARETH_GALLERIES_PHASE_II = "nareth.galleries.same_trajectory"
NARETH_GALLERIES_PHASE_III = "nareth.galleries.trajectory_closes"
NARETH_GALLERIES_RETURN_RESOLVED = "nareth.galleries.return_to_marker_resolved"
NARETH_OBSERVATORY_PHASE_II = "nareth.observatory.correct_the_world"
NARETH_OBSERVATORY_PHASE_III = "nareth.observatory.absolute_reference"

_EXCAVATOR, _RETURNING_BOSS, _CUSTODIAN, _PRECEPTOR, _REFERENCE_GUARDIAN = (
    NARETH_DUNGEON_BESTIARY_CREATURES
)


def _mechanical_creature(creature_id: str, name: str, level: int) -> Creature:
    return Creature(creature_id, name, "common", "balanced", level, level, 0, (), ())


_SERVICE_BEACON = _mechanical_creature(
    "nareth_service_beacon_mechanic", "Baliza de Serviço", 26
)
_RETURN_MARKER = _mechanical_creature(
    "nareth_return_marker_mechanic", "Marco de Retorno", 27
)
_CALIBRATION_BEACON = _mechanical_creature(
    "nareth_calibration_beacon_mechanic", "Baliza de Calibração", 29
)
_CALIBRATION_AXIS = _mechanical_creature(
    "nareth_calibration_axis_mechanic", "Eixo de Calibração", 30
)

_RETURN_MARKER_KEYS = ("marker_1", "marker_2")
_SERVICE_BEACON_KEYS = ("beacon_1", "beacon_2", "beacon_3")
_CALIBRATION_BEACON_KEYS = (
    "calibration_1", "calibration_2", "calibration_3", "calibration_4"
)
_CALIBRATION_AXIS_KEYS = ("axis_1", "axis_2", "axis_3")


def nareth_dungeon_encounter_specs(
    family_id: str,
    ordinal: int,
    difficulty: str,
    initial_group_size: int,
    reference_level: int,
) -> tuple[CreatureCombatantSpec, ...]:
    del reference_level  # Stable/Fractured enemies use their published encounter levels.
    if family_id == NARETH_GALLERIES_FAMILY_ID:
        if ordinal == 1:
            return (CreatureCombatantSpec(NARETH_CHANNEL_SCARAB, 24, "enemy"),)
        if ordinal == 2:
            return (
                CreatureCombatantSpec(NARETH_DITCH_WANDERER, 25, "wanderer"),
                CreatureCombatantSpec(NARETH_CHANNEL_SCARAB, 25, "scarab"),
            )
        if ordinal == 3:
            return (CreatureCombatantSpec(_EXCAVATOR, 26, "enemy"),)
        if ordinal == 4:
            beacon_scale = StatMultipliers(D("0.20"), D(0), D("0.80") / D("0.90"), D(0))
            return (
                CreatureCombatantSpec(NARETH_INVERTED_HUSK, 26, "casco"),
                *(
                    CreatureCombatantSpec(
                        _SERVICE_BEACON,
                        26,
                        key,
                        stat_multipliers=beacon_scale,
                        passive=True,
                        required_for_victory=False,
                        defeat_on_zero=False,
                    )
                    for key in _SERVICE_BEACON_KEYS
                ),
            )
        if ordinal == 5:
            profile = DIFFICULTIES[difficulty]
            group_hp = D(1) + D("0.78") * (initial_group_size - 1)
            group_attack = D(1) + D("0.07") * (initial_group_size - 1)
            boss_scale = StatMultipliers(
                D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
                profile.boss_attack_multiplier * group_attack,
                D(1),
                D(1),
            )
            marker_scale = StatMultipliers(D("0.25"), D(0), D(1), D(0))
            return (
                CreatureCombatantSpec(
                    _RETURNING_BOSS, 27, "enemy", stat_multipliers=boss_scale
                ),
                *(
                    CreatureCombatantSpec(
                        _RETURN_MARKER,
                        27,
                        key,
                        stat_multipliers=marker_scale,
                        passive=True,
                        required_for_victory=False,
                        defeat_on_zero=False,
                        initially_inactive=True,
                    )
                    for key in _RETURN_MARKER_KEYS
                ),
            )
    elif family_id == NARETH_OBSERVATORY_FAMILY_ID:
        if ordinal == 1:
            return (CreatureCombatantSpec(NARETH_MERIDIAN_WATCHER, 28, "enemy"),)
        if ordinal == 2:
            return (
                CreatureCombatantSpec(NARETH_MERIDIAN_WATCHER, 28, "watcher"),
                CreatureCombatantSpec(NARETH_INVERTED_HUSK, 28, "casco"),
            )
        if ordinal == 3:
            return (CreatureCombatantSpec(_CUSTODIAN, 29, "enemy"),)
        if ordinal == 4:
            beacon_scale = StatMultipliers(D("0.20"), D(0), D(1), D(0))
            return (
                CreatureCombatantSpec(_PRECEPTOR, 29, "preceptor"),
                *(
                    CreatureCombatantSpec(
                        _CALIBRATION_BEACON,
                        29,
                        key,
                        stat_multipliers=beacon_scale,
                        passive=True,
                        required_for_victory=False,
                        defeat_on_zero=False,
                    )
                    for key in _CALIBRATION_BEACON_KEYS
                ),
            )
        if ordinal == 5:
            profile = DIFFICULTIES[difficulty]
            group_hp = D(1) + D("0.78") * (initial_group_size - 1)
            group_attack = D(1) + D("0.07") * (initial_group_size - 1)
            boss_scale = StatMultipliers(
                D(3) / D("2.20") * profile.boss_hp_multiplier * group_hp,
                profile.boss_attack_multiplier * group_attack,
                D(1),
                D(1),
            )
            axis_scale = StatMultipliers(D("0.25"), D(0), D(1), D(0))
            return (
                CreatureCombatantSpec(
                    _REFERENCE_GUARDIAN, 30, "guardian", stat_multipliers=boss_scale
                ),
                *(
                    CreatureCombatantSpec(
                        _CALIBRATION_AXIS,
                        30,
                        key,
                        stat_multipliers=axis_scale,
                        passive=True,
                        required_for_victory=False,
                        defeat_on_zero=False,
                        initially_inactive=True,
                    )
                    for key in _CALIBRATION_AXIS_KEYS
                ),
            )
    raise ValueError("Nareth dungeon encounter ordinal must be between 1 and 5.")


def create_nareth_dungeon_combat(
    combat_id: UUID,
    *,
    family_id: str,
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
    environments = (
        NARETH_GALLERIES_ENVIRONMENTS
        if family_id == NARETH_GALLERIES_FAMILY_ID
        else NARETH_OBSERVATORY_ENVIRONMENTS
        if family_id == NARETH_OBSERVATORY_FAMILY_ID
        else None
    )
    if environments is None:
        raise ValueError(f"Unknown Nareth dungeon family: {family_id}")
    specs = nareth_dungeon_encounter_specs(
        family_id, ordinal, difficulty, initial_group_size, reference_level
    )
    state = create_creature_party_combat(
        combat_id,
        name,
        character_class,
        race,
        hp,
        specs,
        player_level=level,
        equipment_configuration=equipment,
        active_art_ids=active_art_ids,
        flavor=environments[ordinal],
        opening_log=f"🌾 {environments[ordinal]}",
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
            "family_id": family_id,
            "difficulty": difficulty,
            "ordinal": ordinal,
            "seed": run_seed,
            "initial_group_size": initial_group_size,
        }
    }
    if family_id == NARETH_GALLERIES_FAMILY_ID and ordinal == 4:
        state.stat_auras = (
            CombatStatAura(
                "nareth.galleries.service_beacons.casco_defense",
                "defense",
                _SERVICE_BEACON_KEYS,
                ("casco",),
                D("0.05"),
            ),
        )
    elif family_id == NARETH_GALLERIES_FAMILY_ID and ordinal == 5:
        state.enemy_actions["e0_colisao_recorrente"] = replace(
            state.enemy_actions["e0_colisao_recorrente"], phase_ids=("III",)
        )
        state.enemy_actions["e0_casco_ciclo"] = replace(
            state.enemy_actions["e0_casco_ciclo"], phase_ids=("I", "II", "III")
        )
        state.phase_id = "I"
        state.phase_triggers = (
            CombatPhaseTrigger(
                NARETH_GALLERIES_PHASE_II,
                "enemy",
                D("0.70"),
                activate_fighter_keys=_RETURN_MARKER_KEYS,
                phase_id="II",
            ),
            CombatPhaseTrigger(
                NARETH_GALLERIES_PHASE_III,
                "enemy",
                D("0.35"),
                phase_id="III",
                resolution_id=NARETH_GALLERIES_RETURN_RESOLVED,
                heal_source_per_active_fighter_fraction=D("0.03"),
                consume_active_fighter_keys=_RETURN_MARKER_KEYS,
            ),
        )
        state.damage_auras = ()
    elif family_id == NARETH_OBSERVATORY_FAMILY_ID and ordinal == 4:
        state.stat_auras = (
            CombatStatAura(
                "nareth.observatory.calibration_beacons.preceptor_defense",
                "defense",
                _CALIBRATION_BEACON_KEYS,
                ("preceptor",),
                D("0.05"),
            ),
        )
    elif family_id == NARETH_OBSERVATORY_FAMILY_ID and ordinal == 5:
        state.enemy_actions["e0_ancora_local"] = replace(
            state.enemy_actions["e0_ancora_local"], phase_ids=("I", "II")
        )
        state.enemy_actions["e0_referencia_absoluta"] = replace(
            state.enemy_actions["e0_referencia_absoluta"], phase_ids=("III",)
        )
        state.phase_id = "I"
        state.phase_triggers = (
            CombatPhaseTrigger(
                NARETH_OBSERVATORY_PHASE_II,
                "guardian",
                D("0.70"),
                activate_fighter_keys=_CALIBRATION_AXIS_KEYS,
                phase_id="II",
            ),
            CombatPhaseTrigger(
                NARETH_OBSERVATORY_PHASE_III,
                "guardian",
                D("0.35"),
                phase_id="III",
            ),
        )
        state.damage_auras = (
            CombatDamageAura(
                "nareth.observatory.axes.guardian_damage_reduction",
                _CALIBRATION_AXIS_KEYS,
                ("guardian",),
                D("0.04"),
            ),
        )
    return state


def nareth_dungeon_enemy_rewards(
    family_id: str, ordinal: int
) -> tuple[tuple[str, int, str], ...]:
    rewards = {
        NARETH_GALLERIES_FAMILY_ID: {
            1: (("escaravelho_canal", 24, "common"),),
            2: (("errante_valas", 25, "uncommon"), ("escaravelho_canal", 25, "common")),
            3: (("escavador_eixo", 26, "elite"),),
            4: (("casco_invertido", 26, "uncommon"),),
            5: (("o_que_retorna", 27, "boss"),),
        },
        NARETH_OBSERVATORY_FAMILY_ID: {
            1: (("vigia_meridiano", 28, "uncommon"),),
            2: (("vigia_meridiano", 28, "uncommon"), ("casco_invertido", 28, "uncommon")),
            3: (("custodio_meridiano", 29, "elite"),),
            4: (("preceptor_eixo", 29, "elite"),),
            5: (("guardiao_referencia", 30, "boss"),),
        },
    }
    try:
        return rewards[family_id][ordinal]
    except KeyError as exc:
        raise ValueError("Unknown Nareth dungeon encounter.") from exc


