from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.domain.campaign_combat import (
    campaign_boss_scaling,
    scale_campaign_boss_stats,
)
from asterion.domain.road import (
    LAST_TRACE_GUARDIAN,
    RULESET,
    VIGIA_PARTIDO,
    CreatureCombatantSpec,
    create_creature_party_combat,
    road_enemy_stats,
)

D = Decimal


@pytest.mark.parametrize("creature", [VIGIA_PARTIDO, LAST_TRACE_GUARDIAN])
def test_campaign_boss_scaling_is_exact_and_preserves_solo_stats(creature):
    solo = road_enemy_stats(creature, 10)
    expected_factors = (
        (D("1.00"), D("1.00")),
        (D("1.55"), D("1.04")),
        (D("2.10"), D("1.08")),
        (D("2.65"), D("1.12")),
    )
    assert tuple(campaign_boss_scaling(size) for size in range(1, 5)) == expected_factors

    for size in range(1, 5):
        combat = create_creature_party_combat(
            uuid4(),
            "Personagem",
            "sentinela",
            "remanescente",
            D(100),
            (
                CreatureCombatantSpec(
                    creature,
                    10,
                    "enemy",
                    campaign_boss_group_size=size,
                ),
            ),
            player_level=10,
            ruleset_version=RULESET,
        )
        boss = combat.fighters["enemy"]
        expected = scale_campaign_boss_stats(solo, size)
        assert boss.stats == expected
        assert boss.hp == expected.hp
        assert boss.stats.defense == solo.defense
        assert boss.stats.agility == solo.agility
        assert boss.stats.per == solo.per
        assert boss.stats.crit == solo.crit


def test_campaign_boss_scaling_rejects_invalid_rosters():
    for size in (0, 5):
        with pytest.raises(ValueError, match="one to four"):
            campaign_boss_scaling(size)
