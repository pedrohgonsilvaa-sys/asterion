"""Etapa C6: the Crônica I kit simulator stays runnable and deterministic."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "simulate_cronica_kits.py"


def _load():
    spec = importlib.util.spec_from_file_location("simulate_cronica_kits", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


def test_simulator_covers_the_nine_kits_and_is_deterministic():
    sim = _load()
    names = [kit.name for kit in sim.KITS]
    assert len(names) == 11  # 8 Encontros + O Compasso in its 3 Fases
    assert sum(name.startswith("O Compasso") for name in names) == 3
    first = sim.fight(sim.KITS[0].build, ("sentinela", 10, "test:c6", "basico"))
    again = sim.fight(sim.KITS[0].build, ("sentinela", 10, "test:c6", "basico"))
    assert first == again
    assert first.win and first.ttk > 0 and first.pressure > 0


def test_faster_enemy_opening_counts_against_full_hp():
    sim = _load()
    # Marcador (Controlador, AGI 110%) can act before the player's first action.
    outcome = sim.fight(sim.KITS[1].build, ("tecelao", 30, "test:c6", "kit"))
    assert outcome.ttk > 0 and outcome.pressure > 0
