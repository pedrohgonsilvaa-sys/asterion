"""O Despertar dos Flagelos — V1 não tem "outro PvE equivalente": o conjunto efetivo de
contribuição é exatamente Caçada, Caçada em Grupo, Desbravar, Contrato, Missão e Masmorra."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import func, select

from asterion.application.flagelo_contributions import record_contribution
from asterion.domain import flagelos as fl
from asterion.infrastructure.db.models import Character, FlageloContribution
from tests.test_flagelos_service import _characters

SRC = Path(__file__).resolve().parents[1] / "src" / "asterion"

V1_CONTRIBUTIONS = {
    "hunt": 1,
    "group_hunt": 1,
    "desbravar": 1,
    "contract": 2,
    "mission": 4,
    "dungeon": 6,
}

# Atividades PvE/PvP que existem no jogo e NÃO contribuem na V1.
NOT_CONTRIBUTING = (
    "hunt_round",
    "ronda",
    "ronda_de_caca",
    "road_hunt",
    "world_event",
    "veu",
    "expedition",
    "oath",
    "arena",
    "duel",
    "guild_battle",
    "other_pve",
    "",
)


def test_v1_contribution_set_is_exactly_the_six_approved_activities():
    assert fl.CONTRIBUTION_POINTS == V1_CONTRIBUTIONS
    for kind, points in V1_CONTRIBUTIONS.items():
        assert fl.contribution_points(kind) == points


@pytest.mark.parametrize("kind", NOT_CONTRIBUTING)
def test_any_other_activity_grants_zero_points(kind):
    assert fl.contribution_points(kind) == 0


def _record_contribution_kinds() -> set[str]:
    kinds: set[str] = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or len(node.args) < 3:
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name != "record_contribution":
                continue
            arg = node.args[2]
            options = [arg.body, arg.orelse] if isinstance(arg, ast.IfExp) else [arg]
            assert all(isinstance(o, ast.Constant) for o in options), (
                f"{path}: a Região/tipo da contribuição deve ser literal"
            )
            kinds.update(o.value for o in options)
    return kinds


def test_no_call_site_contributes_outside_the_v1_set():
    # Missão entra pelo ouvinte ``after_flush`` de ``Quest`` (não por ``record_contribution``).
    assert _record_contribution_kinds() | {"mission"} == set(V1_CONTRIBUTIONS)


@pytest.mark.parametrize("kind", NOT_CONTRIBUTING)
async def test_recording_another_activity_writes_nothing(database, kind):
    ((_, character_id),) = await _characters(database, 1, base=884_000)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        assert await record_contribution(
            session, character, kind, f"other:{kind}", region_id="tdo"
        ) is False
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(FlageloContribution)) == 0
