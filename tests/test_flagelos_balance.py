"""O Despertar dos Flagelos — suíte de balanceamento determinística (espec. final §23).

Mede com o motor real; não altera valores nem decide buff/nerf. As asserções cobrem o que é
fato (baseline intacto, mesmo resultado em duas execuções, formas esperadas). Os números e os
outliers ficam no relatório; defini-los como falha seria uma decisão de balanceamento.

``ASTERION_BALANCE_REPORT=<arquivo>`` grava o relatório em Markdown.
"""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pytest

from asterion.domain import flagelos as fl
from tests import flagelo_balance as fb

BASELINE = {
    "varkhenn": (10, 35_060, 138, 100, 94),
    "nharvek": (20, 51_000, 195, 120, 101),
    "azharel": (30, 53_300, 198, 160, 165),
    "hemrath": (40, 63_880, 320, 177, 190),
    "korvann": (50, 98_740, 310, 306, 204),
    "vaelith": (60, 107_840, 401, 322, 334),
}


def test_baseline_stats_are_untouched_by_the_balance_step():
    got = {
        r.flagelo.flagelo_id: (
            r.flagelo.level, r.flagelo.hp, r.flagelo.attack, r.flagelo.defense, r.flagelo.agility
        )
        for r in fl.REGIONS
    }
    assert got == BASELINE


@pytest.fixture
async def report(database):
    profiles = {
        r.flagelo.flagelo_id: await fb.measure_profile(database[1], r) for r in fl.REGIONS
    }
    return fb.build(profiles), profiles


async def test_profiles_come_from_the_real_engine(report):
    _, profiles = report
    for region in fl.REGIONS:
        profile = profiles[region.flagelo.flagelo_id]
        assert profile.level == region.reference_level
        assert profile.damage > 0 and profile.max_hp > 0 and profile.defense > 0
        assert profile.damage_atk_debuffed < profile.damage  # ATQ −10% reduz o dano real
        assert profile.evasion_agi_debuffed <= profile.evasion


async def test_the_measurement_is_deterministic_and_covers_every_requested_axis(report, database):
    built, profiles = report
    text = fb.render(built)
    again = fb.render(fb.build(profiles))
    assert text == again
    for needle in (
        "## 1. TTK", "## 2. Diferença relativa", "## 3. Dano recebido", "## 4. Ações isoladas",
        "## 5. Peso de cada família", "Preparada: golpe isolado", "Pontos de atenção",
        "Restituição Rubra", "## 6. Escalonamento", "## Outliers",
    ):
        assert needle in text
    # Faixas pedidas: 3, 5, 6–12 e 20+ participantes, e escalonamento 0/5/10 passos.
    assert {3, 5, 6, 12, 20} <= set(fb.PARTICIPANT_COUNTS) and fb.SCALING_STEPS == (0, 5, 10)
    path = os.environ.get("ASTERION_BALANCE_REPORT")
    if path:
        Path(path).write_text(text, encoding="utf-8")


async def test_shapes_follow_from_the_rules(report):
    built, _ = report
    for region in fl.REGIONS:
        code = region.flagelo.flagelo_id
        # Mais participantes nunca atrasam a morte (mesmo HP, mais dano por rodada).
        times = [built.ttk[(code, n)].rounds for n in fb.PARTICIPANT_COUNTS]
        assert times == sorted(times, reverse=True), code
        # Escalonamento só aumenta HP e ATQ do Flagelo: nunca encurta o TTK.
        steps = [built.scaling[(code, fb.ABLATION_COUNT, s)] for s in fb.SCALING_STEPS]
        assert [r.boss_hp for r in steps] == [
            fl.effective_max_hp(region.flagelo.hp, fl.scaling_for_steps(s).hp_bonus)
            for s in fb.SCALING_STEPS
        ]
        assert steps[0].rounds <= steps[1].rounds <= steps[2].rounds, code
    hemrath = built.ablation[("hemrath", "base")]
    assert hemrath.by_action.get("restituicao_rubra", {}).get("uses", 0) <= 3
    assert Decimal(hemrath.healed) <= Decimal(hemrath.boss_hp) * Decimal("0.05") * 3
