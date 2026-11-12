"""Coop de Missão exclusivo de Chefes (Ação × Consequência v1.0.0 §5)."""

import re
from pathlib import Path

from asterion.application.nareth_missions import MISSION_CAMPAIGN_BOSSES
from asterion.domain.mission_coop import MISSION_BOSS_QUESTS, mission_coop_allowed

APPLICATION = Path(__file__).resolve().parents[1] / "src/asterion/application"


def _boss_quests_declared_in_code() -> set[str]:
    found: set[str] = set(MISSION_CAMPAIGN_BOSSES)
    for path in APPLICATION.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "campaign_boss=True" in source:
            found.add(path.stem.upper())
        for literal in re.findall(
            r"campaign_boss=quest_id (?:==|in) \{?([^,}\n]+(?:, [^}\n]+)*)\}?", source
        ):
            found.update(name.strip().removesuffix("_ID") for name in literal.split(","))
    found.discard("MISSION_CAMPAIGN_BOSSES")
    return found


def test_boss_list_matches_every_encounter_created_as_campaign_boss():
    assert _boss_quests_declared_in_code() == set(MISSION_BOSS_QUESTS)


def test_only_bosses_of_the_72_missions_accept_a_group():
    assert mission_coop_allowed("P6") and mission_coop_allowed("S36")
    for quest_id in ("P1", "P2", "P7", "S1", "S5", "P21", "S31", "P35"):
        assert not mission_coop_allowed(quest_id)
    # Outside the 72 missions (Crônica, Masmorras, Caçada) the old rules stay.
    assert mission_coop_allowed(None)
    assert mission_coop_allowed("cr01")
