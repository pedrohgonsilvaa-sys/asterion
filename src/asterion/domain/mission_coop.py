"""Which mission encounters accept Coop (Ação × Consequência v1.0.0 §5, decisão 2026-11-12).

Override of GDD v1.6.0 §51.3/§55.1: Principais and Secundárias are Solo for
progress, objectives, choices and narrative state. Only encounters classified
as Chefe (Campaign Bosses and optional Secondary Bosses) accept Solo or Group
1–4. Contracts, Elites and scripted or economic mission encounters stay Solo.
Systems outside the 72 missions (Masmorras, Caçada, Crônica) keep their rules.
"""

from __future__ import annotations

from asterion.domain.narrative_choices import NARRATIVE_MISSION_IDS

# Missions whose shared encounter is created with ``campaign_boss=True``.
MISSION_BOSS_QUESTS = frozenset(
    ("P5", "P6", "S6", "P12", "P18", "S18", "P24", "S24", "P30", "P36", "S30", "S36")
)


def mission_coop_allowed(quest_id: str | None) -> bool:
    """True when a Group may fight together for ``quest_id``."""
    if quest_id is None or quest_id not in NARRATIVE_MISSION_IDS:
        return True
    return quest_id in MISSION_BOSS_QUESTS
