from decimal import Decimal
from types import SimpleNamespace

from asterion.domain.dungeons import (
    DIFFICULTIES,
    difficulty_gate,
    dungeon_completion_xp,
    dungeon_crowns,
    fragment_material_id,
    material_for_ordinal,
    rarity_with_pity,
    roll_brazier,
    rune_grade,
)
from asterion.domain.road import RUNE_FAMILIES, enemy_xp
from asterion.domain.tdo_crypt import CRYPT_ENCOUNTERS, encounter_specs, enemy_rewards


def test_crypt_discovery_and_difficulty_gates():
    assert (
        difficulty_gate(
            level=3, discovered=False, stable_first_clear=False, fractured_first_clear=False
        )
        == {}
    )
    assert difficulty_gate(
        level=3, discovered=True, stable_first_clear=False, fractured_first_clear=False
    ) == {"stable": "level", "fractured": "level", "rupture": "level"}
    assert difficulty_gate(
        level=4, discovered=True, stable_first_clear=False, fractured_first_clear=False
    ) == {"stable": "available", "fractured": "first_stable", "rupture": "level"}
    assert (
        difficulty_gate(
            level=59, discovered=True, stable_first_clear=True, fractured_first_clear=False
        )["fractured"]
        == "available"
    )
    assert (
        difficulty_gate(
            level=60, discovered=True, stable_first_clear=True, fractured_first_clear=False
        )["rupture"]
        == "first_fractured"
    )
    assert (
        difficulty_gate(
            level=60, discovered=True, stable_first_clear=True, fractured_first_clear=True
        )["rupture"]
        == "available"
    )


def test_stable_crypt_xp_crowns_and_internal_enemy_xp_are_audited():
    assert [
        sum(
            enemy_xp(level, category, powerlevel_factor=Decimal("0.25"))
            for _, level, category in enemy_rewards(ordinal)
        )
        for ordinal in range(1, 6)
    ] == [80, 160, 230, 180, 550]
    assert (
        sum(
            sum(
                enemy_xp(level, category, powerlevel_factor=Decimal("0.25"))
                for _, level, category in enemy_rewards(ordinal)
            )
            for ordinal in range(1, 6)
        )
        == 1200
    )
    assert dungeon_completion_xp(6, "stable") == 3400
    assert dungeon_completion_xp(6, "stable", first_clear=True) == 5440
    assert dungeon_crowns(6, "stable") == 150


def test_reward_rolls_are_seeded_and_pity_boundaries_are_deterministic():
    assert roll_brazier("same-run", "stable") == roll_brazier("same-run", "stable")
    assert material_for_ordinal("same-run", 0) == material_for_ordinal("same-run", 0)
    assert DIFFICULTIES["stable"].vigor == 25
    assert DIFFICULTIES["fractured"].vigor == 35
    assert DIFFICULTIES["rupture"].vigor == 50
    assert DIFFICULTIES["stable"].consumable_limit == 6
    assert DIFFICULTIES["fractured"].consumable_limit == 5
    assert DIFFICULTIES["rupture"].consumable_limit == 4
    assert rarity_with_pity("x", "stable", 23, 199)[0] in {"Lendário", "Mítico"}
    assert rarity_with_pity("x", "stable", 0, 199) == ("Mítico", 0, 0)
    assert rune_grade(6) == 1
    assert rune_grade(60) == 6
    assert fragment_material_id(6) == "material.tdo.fragmento_aprimoramento_i"
    assert fragment_material_id(60) == "material.tdo.fragmento_aprimoramento_vi"


def test_crypt_has_five_stable_encounter_definitions_and_no_variants():
    assert tuple(CRYPT_ENCOUNTERS) == (1, 2, 3, 4, 5)
    for ordinal in range(1, 6):
        for spec in encounter_specs(ordinal, "stable"):
            assert spec.variant is None
    assert len(encounter_specs(2, "stable")) == 2
    assert len(encounter_specs(4, "stable")) == 5
    assert sum(spec.passive for spec in encounter_specs(4, "stable")) == 3
    boss = encounter_specs(5, "stable")[0].creature
    assert boss.creature_id == "sem_nome"
    assert boss.category == "boss"


def test_seeded_rune_drop_uses_every_canonical_family_uniformly():
    from asterion.application.dungeons import DungeonService

    service = object.__new__(DungeonService)
    observed = set()
    for index in range(3000):
        drop = service._roll_rune(
            SimpleNamespace(seed=f"crypt-rune-{index}", difficulty="stable", reference_level=6)
        )
        if drop is not None:
            observed.add(drop["family"])

    assert observed == {family for family, _stat in RUNE_FAMILIES}
