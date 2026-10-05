from decimal import Decimal
from types import SimpleNamespace

from asterion.application.equipment_configuration import (
    hp_after_equipment_change,
    reconcile_character_hp,
)
from asterion.application.progression import consolidate_level
from asterion.domain.combat import Fighter, _deal_damage
from asterion.domain.combat_math import CombatStats, resolve_combat_stats
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot

D = Decimal


def _character(*, hp: str, max_hp: str = "713", xp: int = 0):
    return SimpleNamespace(
        character_class="sentinela",
        level=1,
        race="remanescente",
        hp=D(hp),
        max_hp=D(max_hp),
        xp=xp,
    )


def test_remanescente_sentinel_persists_closed_max_hp():
    stats = resolve_combat_stats("sentinela", 1, "remanescente")
    assert stats.hp == D(713)
    assert stats.hp == stats.hp.to_integral_value()


def test_reconcile_floors_legacy_sub_one_hp_to_zero_without_rounding_up():
    character = _character(hp="0.75")
    stats = reconcile_character_hp(character, EquipmentConfigurationSnapshot(0))
    assert stats.hp == D(713)
    assert character.max_hp == D(713)
    assert character.hp == D(0)


def test_reconcile_floors_fractional_current_hp_when_max_is_already_current():
    character = _character(hp="37.99")
    reconcile_character_hp(character, EquipmentConfigurationSnapshot(0))
    assert character.hp == D(37)


def test_equipment_boundary_never_preserves_fractional_hp_when_max_is_unchanged():
    character = _character(hp="1.99")
    assert hp_after_equipment_change(character, D(713)) == D(1)


def test_progression_boundary_normalizes_legacy_fractional_hp_without_level_up():
    character = _character(hp="0.99")
    assert consolidate_level(character) == 0
    assert character.hp == D(0)


def test_exact_whole_point_damage_has_unambiguous_survival_and_defeat():
    stats = CombatStats(D(10), D(1), D(0), D(1))
    fighter = Fighter("player", "Tester", 1, stats, D(2))

    damage, absorbed = _deal_damage(fighter, D(1))
    assert damage == D(1)
    assert absorbed == D(0)
    assert fighter.hp == D(1)

    damage, absorbed = _deal_damage(fighter, D(1))
    assert damage == D(1)
    assert absorbed == D(0)
    assert fighter.hp == D(0)
