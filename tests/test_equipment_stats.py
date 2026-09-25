from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain.combat import _perform, initiative
from asterion.domain.combat_math import class_stats, resolve_combat_stats
from asterion.domain.equipment import EquipmentSlot
from asterion.domain.equipment_stats import (
    EquipmentConfigurationError,
    EquipmentConfigurationSnapshot,
    EquipmentStatContribution,
    equipment_configuration_from_data,
    equipment_stat_contribution,
    item_snapshot_from_persisted,
)
from asterion.domain.prologue import PROFILE, p1_combat_profile
from asterion.domain.road import CREATURES, create_road_combat
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
COMBAT_ID = UUID("f77365ce-14b2-467f-bcd4-395ac6e8f3a5")


def _item(
    item_id: str,
    slot: EquipmentSlot,
    item_slot: str,
    *,
    core: dict | None = None,
    secondaries: list[dict] | None = None,
    enhancement: int = 0,
    rune=None,
    enchantment=None,
):
    default_core = {
        "Principal": {"ATQ": 1},
        "2H": {"ATQ": 1},
        "Secundária": {"ATQ": 1},
        "Cabeça": {"HP": 1},
        "Torso": {"HP": 1},
        "Mãos": {"ATQ": 1},
        "Pés": {"HP": 1},
        "Acessório": {"HP": 1},
        "Artefato": {"HP": 1},
    }[item_slot]
    payload = {
        "item_instance_id": item_id,
        "slot": item_slot,
        "core": core or default_core,
        "secondaries": secondaries or [],
        "enhancement": enhancement,
        "rune": rune,
        "enchantment": enchantment,
    }
    return item_snapshot_from_persisted(
        item_instance_id=item_id,
        equipped_slot=slot.value,
        item_slot=item_slot,
        item_level=1,
        rarity="Comum",
        payload=payload,
    )


@pytest.mark.parametrize(
    ("attribute", "equipped_slot", "item_slot", "core", "secondary", "expected"),
    [
        ("HP", EquipmentSlot.CABECA, "Cabeça", {"HP": 12}, None, D(12)),
        ("ATQ", EquipmentSlot.PRINCIPAL, "Principal", {"ATQ": 12}, None, D(12)),
        ("DEF", EquipmentSlot.CABECA, "Cabeça", {"DEF": 12}, None, D(12)),
        ("AGI", EquipmentSlot.PES, "Pés", {"AGI": 12}, None, D(12)),
        (
            "PER", EquipmentSlot.PRINCIPAL, "Principal", {},
            {"attribute": "PER", "value": "1.25"}, D("1.25"),
        ),
        (
            "CRIT", EquipmentSlot.PRINCIPAL, "Principal", {},
            {"attribute": "CRIT", "value": "1.25"}, D("1.25"),
        ),
        (
            "Esquiva", EquipmentSlot.PES, "Pés", {},
            {"attribute": "Esquiva", "value": "1.25"}, D("1.25"),
        ),
        (
            "Bloqueio", EquipmentSlot.SECUNDARIA, "Secundária", {},
            {"attribute": "Bloqueio", "value": "1.25"}, D("1.25"),
        ),
    ],
)
def test_item_contribution_maps_all_eight_materialized_attributes(
    attribute, equipped_slot, item_slot, core, secondary, expected
):
    item = _item(
            "item-1",
            equipped_slot,
            item_slot,
            core=core,
        secondaries=[secondary] if secondary else [],
    )
    contribution = equipment_stat_contribution(item)
    field = {
        "HP": "hp",
        "ATQ": "attack",
        "DEF": "defense",
        "AGI": "agility",
        "PER": "per",
        "CRIT": "crit",
        "Esquiva": "evasion",
        "Bloqueio": "block",
    }[attribute]
    assert getattr(contribution, field) == expected


def test_core_secondaries_and_enhancement_use_exact_decimal_order():
    item = _item(
        "item-enhanced",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 10},
        secondaries=[{"attribute": "ATQ", "value": "1.25"}],
    )
    assert equipment_stat_contribution(item).attack == D("11.25")
    enhanced = _item(
        "item-enhanced-10",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 10},
        secondaries=[{"attribute": "ATQ", "value": "1.25"}],
        enhancement=10,
    )
    assert equipment_stat_contribution(enhanced).attack == D("14.0625")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"slot": "Principal", "core": {"ATQ": 1.5}, "secondaries": [], "enhancement": 0},
            "exact",
        ),
        (
            {"slot": "Principal", "core": {"XYZ": 1}, "secondaries": [], "enhancement": 0},
            "core attribute",
        ),
        (
            {
                "slot": "Principal",
                "core": {"ATQ": 1},
                "secondaries": [{"attribute": "XYZ", "value": "1"}],
                "enhancement": 0,
            },
            "secondary",
        ),
        (
            {
                "slot": "Principal",
                "core": {"ATQ": 1},
                "secondaries": [{"attribute": "Bloqueio", "value": "1"}],
                "enhancement": 0,
            },
            "eligible",
        ),
        (
            {"slot": "Principal", "core": {"DEF": 1}, "secondaries": [], "enhancement": 0},
            "Core attribute is not eligible",
        ),
        (
            {"slot": "Principal", "core": {"ATQ": 1}, "secondaries": [], "enhancement": 11},
            "enhancement",
        ),
        (
            {
                "slot": "Principal",
                "core": {"ATQ": 1},
                "secondaries": [],
                "enhancement": 0,
                "rune": {"id": "rune"},
            },
            "unsupported",
        ),
    ],
)
def test_invalid_materialized_item_payload_is_rejected(payload, message):
    payload = payload | {"item_instance_id": "bad-item", "enchantment": None}
    with pytest.raises(EquipmentConfigurationError, match=message):
        item_snapshot_from_persisted(
            item_instance_id="bad-item",
            equipped_slot="Principal",
            item_slot="Principal",
            item_level=1,
            rarity="Comum",
            payload=payload,
        )


def test_all_eight_slots_aggregate_once_and_keep_neutral_bonuses_at_zero():
    config = EquipmentConfigurationSnapshot(
        8,
        (
            _item(
                "p", EquipmentSlot.PRINCIPAL, "Principal", core={"ATQ": 1},
                secondaries=[{"attribute": "PER", "value": "0.25"}],
            ),
            _item(
                "s", EquipmentSlot.SECUNDARIA, "Secundária", core={"DEF": 1},
                secondaries=[{"attribute": "Bloqueio", "value": "0.25"}],
            ),
            _item(
                "h", EquipmentSlot.CABECA, "Cabeça", core={"HP": 1},
                secondaries=[{"attribute": "CRIT", "value": "0.25"}],
            ),
            _item(
                "t", EquipmentSlot.TORSO, "Torso", core={"HP": 1},
                secondaries=[{"attribute": "Bloqueio", "value": "0.25"}],
            ),
            _item("m", EquipmentSlot.MAOS, "Mãos", core={"ATQ": 1}),
            _item(
                "f", EquipmentSlot.PES, "Pés", core={"AGI": 1},
                secondaries=[{"attribute": "Esquiva", "value": "0.25"}],
            ),
            _item(
                "a", EquipmentSlot.ACESSORIO, "Acessório", core={"HP": 1},
                secondaries=[{"attribute": "CRIT", "value": "0.25"}],
            ),
            _item(
                "x", EquipmentSlot.ARTEFATO, "Artefato", core={"ATQ": 1},
                secondaries=[{"attribute": "PER", "value": "0.25"}],
            ),
        ),
    )
    bonus = config.contribution()
    assert bonus.values() == (
        D(3), D(3), D(1), D(1), D("0.5"), D("0.5"), D("0.25"), D("0.5")
    )
    assert EquipmentStatContribution().values() == (D(0),) * 8


def test_two_handed_item_contributes_once_and_forbids_secondary_slot():
    two_handed = _item(
        "two-handed",
        EquipmentSlot.PRINCIPAL,
        "2H",
        core={"ATQ": 35},
    )
    assert EquipmentConfigurationSnapshot(1, (two_handed,)).contribution().attack == 35
    offhand = _item("offhand", EquipmentSlot.SECUNDARIA, "Secundária", core={"DEF": 5})
    with pytest.raises(EquipmentConfigurationError, match="two-handed"):
        EquipmentConfigurationSnapshot(1, (two_handed, offhand)).contribution()


def test_configuration_snapshot_round_trips_item_identity_decimal_state_and_version():
    item = _item(
        "stable-instance-id",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 10},
        secondaries=[{"attribute": "CRIT", "value": "1.25"}],
        enhancement=6,
    )
    original = EquipmentConfigurationSnapshot(12, (item,))
    restored = equipment_configuration_from_data(
        original.to_data("gdd-1.4.6-baseline-1.0")
    )
    assert restored == original
    assert restored.items[0].item_instance_id == "stable-instance-id"
    assert restored.contribution().crit == D("1.40625")


def test_resolver_adds_equipment_before_static_racial_modifiers_only():
    bonus = EquipmentStatContribution(
        hp=D(100),
        attack=D(10),
        defense=D(20),
        agility=D(5),
        per=D(3),
        crit=D(2),
        evasion=D(4),
        block=D(1),
    )
    remnant = resolve_combat_stats("sentinela", 1, "remanescente", bonus)
    assert remnant.values() == (
        D("814.030"), D("103.530"), D("102.515"), D("75.110")
    )
    assert (remnant.per, remnant.crit, remnant.evasion, remnant.block) == (
        D(3), D(7), D(4), D(1)
    )
    alvorano = resolve_combat_stats("errante", 1, "alvorano", bonus)
    assert alvorano.agility == D("92.40")
    assert (alvorano.per, alvorano.crit, alvorano.evasion, alvorano.block) == (
        D(3), D(7), D(4), D(1)
    )
    assert class_stats("sentinela", 1).crit == D(5)


def test_new_road_combat_uses_and_persists_the_frozen_equipment_configuration():
    item = _item(
        "combat-item",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 50},
        secondaries=[
            {"attribute": "PER", "value": "10"},
            {"attribute": "CRIT", "value": "5"},
        ],
    )
    feet = _item(
        "combat-feet",
        EquipmentSlot.PES,
        "Pés",
        core={"AGI": 100},
    )
    configuration = EquipmentConfigurationSnapshot(3, (item, feet))
    combat = create_road_combat(
        COMBAT_ID,
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
        equipment_configuration=configuration,
    )
    player = combat.fighters["player"]
    assert player.stats.attack == D(142)
    assert player.stats.agility == D(169)
    assert player.stats.per == D(10)
    assert player.stats.crit == D(10)
    assert combat.configuration_snapshot == configuration.to_data(combat.ruleset)
    assert combat.configuration_snapshot["equipment"][0]["item_instance_id"] == "combat-item"
    restored = equipment_configuration_from_data(combat.configuration_snapshot)
    assert restored == configuration
    persisted = encode(combat)
    decoded = decode(persisted, combat.id, combat.ruleset, combat.version)
    assert decoded.configuration_snapshot == combat.configuration_snapshot
    assert decoded.fighters["player"].stats == combat.fighters["player"].stats

    legacy_payload = dict(persisted)
    legacy_payload.pop("configuration_snapshot")
    legacy = decode(legacy_payload, combat.id, combat.ruleset, combat.version)
    assert legacy.configuration_snapshot is None
    assert legacy.fighters["player"].stats == combat.fighters["player"].stats


def test_legacy_combat_configuration_snapshot_can_be_absent_without_recalculation():
    legacy = EquipmentConfigurationSnapshot(0)
    combat = create_road_combat(
        COMBAT_ID,
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
    )
    assert combat.configuration_snapshot is None
    assert legacy.contribution() == EquipmentStatContribution()


def test_prologue_and_p1_profiles_use_the_shared_equipped_stats_resolver():
    item = _item("opening-gear", EquipmentSlot.PRINCIPAL, "Principal", core={"ATQ": 25})
    configuration = EquipmentConfigurationSnapshot(4, (item,))
    expected = resolve_combat_stats(
        "sentinela", 1, "remanescente", configuration.contribution()
    )

    prologue = PROFILE.create(
        COMBAT_ID, "Heroa", "sentinela", "remanescente", expected.hp, configuration
    )
    p1 = p1_combat_profile(
        UUID(int=3), "Heroa", "sentinela", "remanescente", expected.hp, configuration
    )

    for combat in (prologue, p1):
        assert combat.fighters["player"].stats == expected
        assert combat.configuration_snapshot["combat_configuration_version"] == 4
        assert combat.configuration_snapshot["equipment"][0]["item_instance_id"] == (
            "opening-gear"
        )


def test_equipped_attack_defense_and_per_change_real_combat_resolution():
    attack_item = _item(
        "attack-gear", EquipmentSlot.PRINCIPAL, "Principal", core={"ATQ": 100}
    )
    attack_combat = create_road_combat(
        COMBAT_ID,
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
        equipment_configuration=EquipmentConfigurationSnapshot(1, (attack_item,)),
    )
    attack_combat.fighters["player"].stats = replace(
        attack_combat.fighters["player"].stats, crit=D(0)
    )
    attack_combat.fighters["enemy"].stats = replace(
        attack_combat.fighters["enemy"].stats,
        defense=D(0), evasion=D(0), block=D(0),
    )
    _perform(attack_combat, "player", "attack")
    assert attack_combat.events[-1].damage == 192

    defender = _item(
        "defense-gear", EquipmentSlot.CABECA, "Cabeça", core={"DEF": 100}
    )
    defense_combat = create_road_combat(
        UUID(int=1),
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
        equipment_configuration=EquipmentConfigurationSnapshot(1, (defender,)),
    )
    defense_combat.fighters["enemy"].stats = replace(
        defense_combat.fighters["enemy"].stats, attack=D(100), crit=D(0)
    )
    defense_combat.fighters["player"].stats = replace(
        defense_combat.fighters["player"].stats, evasion=D(0), block=D(0)
    )
    _perform(defense_combat, "enemy", "bite")
    assert defense_combat.events[-1].damage == 36

    penetration = _item(
        "per-gear",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 1},
        secondaries=[{"attribute": "PER", "value": "30"}],
    )
    per_combat = create_road_combat(
        UUID(int=2),
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
        equipment_configuration=EquipmentConfigurationSnapshot(1, (penetration,)),
    )
    per_combat.fighters["player"].stats = replace(
        per_combat.fighters["player"].stats, attack=D(100), crit=D(0), per=D(0)
    )
    per_combat.fighters["enemy"].stats = replace(
        per_combat.fighters["enemy"].stats,
        defense=D(100), evasion=D(0), block=D(0),
    )
    baseline = deepcopy(per_combat)
    equipped = deepcopy(per_combat)
    equipped.fighters["player"].stats = replace(
        equipped.fighters["player"].stats, per=D(30)
    )
    _perform(baseline, "player", "attack")
    _perform(equipped, "player", "attack")
    assert equipped.events[-1].damage > baseline.events[-1].damage


def test_equipped_agility_crit_evasion_and_block_reach_the_combat_engine():
    main = _item(
        "crit-gear",
        EquipmentSlot.PRINCIPAL,
        "Principal",
        core={"ATQ": 1},
        secondaries=[{"attribute": "CRIT", "value": "95"}],
    )
    feet = _item(
        "agility-dodge-gear",
        EquipmentSlot.PES,
        "Pés",
        core={"AGI": 100},
        secondaries=[{"attribute": "Esquiva", "value": "100"}],
    )
    offhand = _item(
        "block-gear",
        EquipmentSlot.SECUNDARIA,
        "Secundária",
        core={"DEF": 1},
        secondaries=[{"attribute": "Bloqueio", "value": "100"}],
    )
    configuration = EquipmentConfigurationSnapshot(1, (main, feet, offhand))
    combat = create_road_combat(
        COMBAT_ID,
        "Heroa",
        "sentinela",
        "velado",
        D(702),
        CREATURES[0],
        1,
        None,
        equipment_configuration=configuration,
    )
    player = combat.fighters["player"]
    expected = resolve_combat_stats(
        "sentinela", 1, "velado", configuration.contribution()
    )
    assert player.stats == expected
    assert player.stats.agility == class_stats("sentinela", 1).agility + D(100)
    assert initiative(combat) == ("player", "enemy")
    assert (player.stats.crit, player.stats.evasion, player.stats.block) == (
        D(100), D(100), D(100)
    )

    critical_combat = deepcopy(combat)
    critical_combat.fighters["enemy"].stats = replace(
        critical_combat.fighters["enemy"].stats,
        defense=D(0), evasion=D(0), block=D(0),
    )
    _perform(critical_combat, "player", "attack")
    assert critical_combat.events[-1].critical

    dodge_combat = deepcopy(combat)
    dodge_combat.fighters["enemy"].stats = replace(
        dodge_combat.fighters["enemy"].stats, attack=D(100), crit=D(0)
    )
    _perform(dodge_combat, "enemy", "bite")
    assert dodge_combat.events[-1].dodged

    block_combat = deepcopy(combat)
    block_combat.fighters["player"].stats = replace(
        block_combat.fighters["player"].stats, evasion=D(0)
    )
    block_combat.fighters["enemy"].stats = replace(
        block_combat.fighters["enemy"].stats, attack=D(100), crit=D(0)
    )
    _perform(block_combat, "enemy", "bite")
    assert block_combat.events[-1].blocked
