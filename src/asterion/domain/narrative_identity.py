"""Declarative narrative conditions keyed by who the character is.

A scene declares its lines and dialogue options once. Each entry may be
restricted by Race, Class, the Race + Class pair, mission state, recorded
consequences, discoveries and the current Local. The resolver is pure and
deterministic: the same character context always yields the same result.

Race and Class are read from the existing ``Character`` row; this module never
stores a second copy. Every input belongs to one character, so two players in
the same scene, including a host and a helper in a cooperative fight, are
resolved independently.

Lines and options are canonical content: a scene enters the catalog only after
the author approves its text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

RACES = frozenset(("remanescente", "velado", "cinereo", "hemario", "alvorano"))
CLASSES = frozenset(("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar"))


@dataclass(frozen=True, slots=True)
class QuestState:
    status: str
    step: int


@dataclass(frozen=True, slots=True)
class NarrativeContext:
    """Everything one character brings to a scene. Never shared between characters."""

    character_id: str
    race: str
    character_class: str
    quests: Mapping[str, QuestState] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()
    discoveries: frozenset[str] = frozenset()
    location: str | None = None


@dataclass(frozen=True, slots=True)
class QuestRequirement:
    quest_id: str
    statuses: frozenset[str]
    min_step: int | None = None
    max_step: int | None = None

    def matches(self, quests: Mapping[str, QuestState]) -> bool:
        state = quests.get(self.quest_id)
        if state is None:
            return "absent" in self.statuses
        if state.status not in self.statuses:
            return False
        if self.min_step is not None and state.step < self.min_step:
            return False
        return self.max_step is None or state.step <= self.max_step


@dataclass(frozen=True, slots=True)
class NarrativeCondition:
    """All constrained dimensions must match. An empty condition is the common fallback.

    ``race_classes`` holds explicit (race, class) pairs, for a line that neither
    attribute unlocks alone.
    """

    quests: tuple[QuestRequirement, ...] = ()
    required_flags: frozenset[str] = frozenset()
    forbidden_flags: frozenset[str] = frozenset()
    races: frozenset[str] = frozenset()
    classes: frozenset[str] = frozenset()
    race_classes: frozenset[tuple[str, str]] = frozenset()
    discoveries: frozenset[str] = frozenset()
    locations: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        unknown_races = (self.races | {race for race, _ in self.race_classes}) - RACES
        unknown_classes = (
            self.classes | {klass for _, klass in self.race_classes}
        ) - CLASSES
        if unknown_races:
            raise ValueError(f"Unknown race in narrative condition: {sorted(unknown_races)}")
        if unknown_classes:
            raise ValueError(
                f"Unknown class in narrative condition: {sorted(unknown_classes)}"
            )

    @property
    def is_fallback(self) -> bool:
        return self.specificity == 0

    @property
    def specificity(self) -> int:
        """How many dimensions this condition constrains; used only to break priority ties."""
        return sum(
            (
                bool(self.quests),
                bool(self.required_flags or self.forbidden_flags),
                bool(self.races),
                bool(self.classes),
                2 * bool(self.race_classes),
                bool(self.discoveries),
                bool(self.locations),
            )
        )

    def matches(self, context: NarrativeContext) -> bool:
        return (
            all(requirement.matches(context.quests) for requirement in self.quests)
            and self.required_flags <= context.flags
            and not (self.forbidden_flags & context.flags)
            and (not self.races or context.race in self.races)
            and (not self.classes or context.character_class in self.classes)
            and (
                not self.race_classes
                or (context.race, context.character_class) in self.race_classes
            )
            and self.discoveries <= context.discoveries
            and (not self.locations or context.location in self.locations)
        )


@dataclass(frozen=True, slots=True)
class NarrativeLine:
    """One way a speaker can deliver a beat. The highest-ranked match wins."""

    line_id: str
    text: str
    condition: NarrativeCondition = NarrativeCondition()
    priority: int = 0


@dataclass(frozen=True, slots=True)
class NarrativeOption:
    """A dialogue choice. Every matching option is offered, in declared order.

    ``reply`` is what the speaker answers when the option is picked.
    """

    option_id: str
    label: str
    condition: NarrativeCondition = NarrativeCondition()
    consequence_flags: frozenset[str] = frozenset()
    reply: str = ""


@dataclass(frozen=True, slots=True)
class NarrativeBeat:
    beat_id: str
    lines: tuple[NarrativeLine, ...]

    def __post_init__(self) -> None:
        ids = [line.line_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate line id in beat {self.beat_id}.")
        if sum(line.condition.is_fallback for line in self.lines) != 1:
            raise ValueError(f"Beat {self.beat_id} needs exactly one common fallback line.")


@dataclass(frozen=True, slots=True)
class NarrativeScene:
    """One scene of one mission. Identity varies beats and options, never the mission."""

    scene_id: str
    beats: tuple[NarrativeBeat, ...]
    options: tuple[NarrativeOption, ...] = ()

    def __post_init__(self) -> None:
        beat_ids = [beat.beat_id for beat in self.beats]
        option_ids = [option.option_id for option in self.options]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError(f"Duplicate beat id in scene {self.scene_id}.")
        if len(option_ids) != len(set(option_ids)):
            raise ValueError(f"Duplicate option id in scene {self.scene_id}.")


@dataclass(frozen=True, slots=True)
class ResolvedScene:
    scene_id: str
    character_id: str
    lines: tuple[NarrativeLine, ...]
    options: tuple[NarrativeOption, ...]

    @property
    def spoken_lines(self) -> tuple[str, ...]:
        """Lines to show; an empty common fallback means the beat adds nothing."""
        return tuple(line.text for line in self.lines if line.text)

    def option(self, option_id: str) -> NarrativeOption | None:
        return next((row for row in self.options if row.option_id == option_id), None)


def resolve_line(lines: Iterable[NarrativeLine], context: NarrativeContext) -> NarrativeLine:
    """Pick by explicit priority, then specificity, then id, so ties never depend on order."""
    matching = [line for line in lines if line.condition.matches(context)]
    if not matching:
        raise ValueError("No narrative line matched; the beat is missing its fallback.")
    return min(
        matching,
        key=lambda line: (-line.priority, -line.condition.specificity, line.line_id),
    )


def resolve_scene(scene: NarrativeScene, context: NarrativeContext) -> ResolvedScene:
    return ResolvedScene(
        scene_id=scene.scene_id,
        character_id=context.character_id,
        lines=tuple(resolve_line(beat.lines, context) for beat in scene.beats),
        options=tuple(
            option for option in scene.options if option.condition.matches(context)
        ),
    )


P2_ALDA_OFFER_SCENE = "p2.alda.offer"

# Canonical scenes. Text approved by the author on 2026-11-11.
NARRATIVE_SCENES: Mapping[str, NarrativeScene] = {
    P2_ALDA_OFFER_SCENE: NarrativeScene(
        scene_id=P2_ALDA_OFFER_SCENE,
        beats=(
            # Shown after Alda's fixed P2 line; the empty fallback keeps the
            # official offer unchanged for every other identity.
            NarrativeBeat(
                beat_id="identity",
                lines=(
                    NarrativeLine("identity.common", ""),
                    NarrativeLine(
                        "identity.cinereo",
                        "— O nome que você carrega veio das rotas de cinza, não da cor "
                        "de ninguém. Se as histórias da sua gente falam de fuligem que "
                        "aparece sem fogo, quero ouvir antes de você sair.",
                        NarrativeCondition(races=frozenset({"cinereo"})),
                        priority=1,
                    ),
                    NarrativeLine(
                        "identity.vigia",
                        "— Você olha para o chão antes de olhar para mim. Bom. Conte os "
                        "pontos de fuligem, não as impressões que eles deixam.",
                        NarrativeCondition(classes=frozenset({"vigia"})),
                    ),
                ),
            ),
        ),
        options=(
            NarrativeOption(
                "rotas",
                "Perguntar pelas rotas antigas",
                NarrativeCondition(race_classes=frozenset({("cinereo", "vigia")})),
                reply="— Rotas de cinza não andam sozinhas. Se essa fuligem seguir uma "
                "linha, me traga a linha. Se não seguir, me traga isso também.",
            ),
        ),
    ),
}
