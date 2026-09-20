"""Creation rules. No Telegram, database or combat dependencies."""

import re
from dataclasses import dataclass, replace
from uuid import UUID

RACES = ("remanescente", "velado", "cinereo", "hemario", "alvorano")
CLASSES = ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
PROLOGUE = "cinzas_na_estrada:intro"
RULESET = "gdd-1.4.2-baseline-1.0"


def normalize_name(value: str) -> str | None:
    if re.fullmatch(r"[A-Za-z]{3,16}", value) is None:
        return None
    return value.capitalize()


@dataclass(frozen=True)
class NamePolicy:
    """Deployment-owned policy; deliberately ships without an editorial blocklist."""

    blocked: frozenset[str] = frozenset()

    def accepts(self, name: str) -> bool:
        return name.casefold() not in {item.casefold() for item in self.blocked}


@dataclass(frozen=True)
class Creation:
    id: UUID
    version: int = 0
    step: str = "name"
    name: str | None = None
    race: str | None = None
    character_class: str | None = None
    editing: bool = False
    error: str | None = None
    rejected_name: str | None = None


def navigate(state: Creation, action: str) -> Creation | None:
    """Allow only buttons actually offered by the current authoritative page."""
    step = state.step
    if action in ("name", "race", "class") and step == "confirm":
        return replace(state, step=action, editing=True, error=None, rejected_name=None)
    if action == "backname" and step == "race":
        return replace(state, step="name", error=None, rejected_name=None)
    if action == "races" and (step.startswith("race:") or step == "class"):
        return replace(state, step="race")
    if action == "classes" and (step.startswith("class:") or step == "confirm"):
        return replace(state, step="class")
    if step == "race" and action in {f"r{i}" for i in range(len(RACES))}:
        return replace(state, step=f"race:{RACES[int(action[1:])]}")
    if step == "class" and action in {f"c{i}" for i in range(len(CLASSES))}:
        return replace(state, step=f"class:{CLASSES[int(action[1:])]}")
    if action == "choose" and step.startswith("race:"):
        return replace(
            state,
            race=step.split(":")[1],
            step="confirm" if state.editing and state.character_class else "class",
            editing=False,
        )
    if action == "choose" and step.startswith("class:") and state.race:
        return replace(state, character_class=step.split(":")[1], step="confirm", editing=False)
    return None
