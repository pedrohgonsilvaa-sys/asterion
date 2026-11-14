"""Narrative choice nodes: Ação → Consequência → Memória → Reação futura.

Source: ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA v1.0.0 (docs/specs). The
catalog JSON is generated from that document by
``scripts/build_narrative_choice_catalog.py`` and must not be edited by hand.

Rules held here, all pure:

- one node per Principal/Secundária, three options, commit once;
- each option leaves at least one memory (character and/or NPC);
- a future hook only reads what is legitimately known: the character's own
  choice, and, when the hook names NPCs, the memory that NPC actually received;
- Race/Class only qualify a node (``identity_conditions``); they never block
  an option unless the option declares ``requires``;
- nothing here touches XP, Coroas, Materiais, combat or ``world_state``.

Player-facing copy beyond the option labels (NPC reactions, future lines) is
editorial content still pending; until it exists, screens show no extra line.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources

from asterion.domain.narrative_identity import CLASSES, RACES

CATALOG_VERSION = "1.0.0"

RAPPORT_STATES = frozenset(
    ("neutral", "open", "trusting", "guarded", "skeptical", "respectful", "strained")
)
DEFAULT_RAPPORT = "neutral"

MEMORY_KINDS = frozenset(("FACTUAL", "RELATIONAL", "METHOD", "ETHICAL", "EVIDENCE", "IDENTITY"))
TENDENCIES = frozenset(
    (
        "evidence_first", "hypothesis_marked", "corroborates", "preserves_records",
        "community_first", "safety_first", "risk_accepting", "risk_averse", "pragmatic",
        "protective", "questions_authority", "institutional_trust",
        "institutional_skepticism", "continuity_first", "limits_coercion",
        "accepts_controlled_cost", "context_before_judgment", "preserves_contradiction",
        "results_first", "cause_first",
    )
)

# How an NPC came to know a choice (§3.2). The catalog records the NPCs that
# the scene itself puts in contact with the decision, so they are "witnessed".
KNOWLEDGE_SOURCES = frozenset(("witnessed", "report", "record"))

PLAYER_SOURCE = "player"
HOOK_BASIS_NPC = "npc_memory"
HOOK_BASIS_CHARACTER = "character_memory"
HOOK_BASES = frozenset((HOOK_BASIS_NPC, HOOK_BASIS_CHARACTER))
BACKFILL_SOURCE = "neutral_backfill"
BACKFILL_OPTION = "neutral_backfill"


@dataclass(frozen=True, slots=True)
class NpcMemoryTarget:
    npc_id: str
    tag: str
    knowledge: str = "witnessed"


@dataclass(frozen=True, slots=True)
class IdentityCondition:
    kind: str  # race | class | race_class
    values: tuple[str | tuple[str, str], ...]

    def matches(self, race: str, character_class: str) -> bool:
        if self.kind == "race":
            return race in self.values
        if self.kind == "class":
            return character_class in self.values
        return (race, character_class) in self.values

    def matched_key(self, race: str, character_class: str) -> str | None:
        if not self.matches(race, character_class):
            return None
        if self.kind == "race":
            return f"race:{race}"
        if self.kind == "class":
            return f"class:{character_class}"
        return f"race_class:{race}+{character_class}"


@dataclass(frozen=True, slots=True)
class ChoiceOption:
    option_id: str
    label: str
    character_memory_tags: tuple[str, ...]
    npc_memory_targets: tuple[NpcMemoryTarget, ...]
    requires: tuple[IdentityCondition, ...] = ()
    memory_type: str = ""

    def available_to(self, race: str, character_class: str) -> bool:
        return all(condition.matches(race, character_class) for condition in self.requires)


@dataclass(frozen=True, slots=True)
class FutureHook:
    """A later scene that may react to a choice.

    ``when_option`` limits the hook to one option of the node (the Prologue's 1:1
    option-to-reaction mapping). ``basis`` says what the NPC reacts to: the memory
    it holds (``npc_memory``, the 72 mission nodes) or only the demeanor the
    character shows in the NPC's own scene (``character_memory``, the Prologue):
    nothing is ever written to the NPC.
    """

    hook_id: str
    target: str
    knowledge_holders: tuple[str, ...]
    summary: str
    when_option: str | None = None
    basis: str = HOOK_BASIS_NPC


@dataclass(frozen=True, slots=True)
class ChoiceNode:
    choice_id: str
    mission_id: str
    mission_kind: str
    title: str
    region: str
    step: int | None
    step_context: str
    question: str
    options: tuple[ChoiceOption, ...]
    future_hooks: tuple[FutureHook, ...]
    identity_conditions: tuple[IdentityCondition, ...]

    def option(self, option_id: str) -> ChoiceOption | None:
        return next((item for item in self.options if item.option_id == option_id), None)

    def matched_identity(self, race: str, character_class: str) -> tuple[str, ...]:
        return tuple(
            key
            for condition in self.identity_conditions
            if (key := condition.matched_key(race, character_class)) is not None
        )

    def available_options(self, race: str, character_class: str) -> tuple[ChoiceOption, ...]:
        return tuple(item for item in self.options if item.available_to(race, character_class))


def _condition(data: Mapping) -> IdentityCondition:
    kind = data["kind"]
    if kind == "race_class":
        values = tuple(tuple(pair) for pair in data["values"])
        if any(race not in RACES or klass not in CLASSES for race, klass in values):
            raise ValueError(f"Unknown race/class pair in {data!r}.")
    else:
        values = tuple(data["values"])
        allowed = RACES if kind == "race" else CLASSES if kind == "class" else None
        if allowed is None or any(value not in allowed for value in values):
            raise ValueError(f"Unknown identity condition {data!r}.")
    return IdentityCondition(kind=kind, values=values)


def build_node(data: Mapping) -> ChoiceNode:
    options = tuple(
        ChoiceOption(
            option_id=item["option_id"],
            label=item["label"],
            character_memory_tags=tuple(item["character_memory_tags"]),
            npc_memory_targets=tuple(
                NpcMemoryTarget(
                    target["npc_id"], target["tag"], target.get("knowledge", "witnessed")
                )
                for target in item["npc_memory_targets"]
            ),
            requires=tuple(_condition(cond) for cond in item.get("requires", ())),
            memory_type=item.get("memory_type", ""),
        )
        for item in data["options"]
    )
    node = ChoiceNode(
        choice_id=data["choice_id"],
        mission_id=data["mission_id"],
        mission_kind=data["mission_kind"],
        title=data["title"],
        region=data["region"],
        step=data["step"],
        step_context=data["step_context"],
        question=data["question"],
        options=options,
        future_hooks=tuple(
            FutureHook(
                hook_id=hook["hook_id"],
                target=hook["target"],
                knowledge_holders=tuple(hook["knowledge_holders"]),
                summary=hook["summary"],
                when_option=hook.get("when_option"),
                basis=hook.get("basis", HOOK_BASIS_NPC),
            )
            for hook in data.get("future_hooks", ())
        ),
        identity_conditions=tuple(_condition(cond) for cond in data["identity_conditions"]),
    )
    validate_node(node)
    return node


PROLOGUE_MISSION_ID = "PRO"
PROLOGUE_KIND = "prologo"


def _validate_prologue_node(node: ChoiceNode) -> None:
    """The Prologue has no Quest and no NPC witness: character memory only (Documento A)."""
    if node.mission_id != PROLOGUE_MISSION_ID or len(node.options) != 3:
        raise ValueError(f"{node.choice_id}: prologue node needs mission PRO and 3 options.")
    option_ids = {item.option_id for item in node.options}
    hooked: set[str | None] = set()
    for hook in node.future_hooks:
        if hook.basis != HOOK_BASIS_CHARACTER or hook.knowledge_holders:
            raise ValueError(f"{hook.hook_id}: prologue hooks read character memory only.")
        if hook.when_option not in option_ids or hook.when_option in hooked:
            raise ValueError(f"{hook.hook_id}: one hook per option, on a real option.")
        if not hook.hook_id.startswith(f"{node.choice_id}->"):
            raise ValueError(f"{hook.hook_id}: hook id must start with the choice id.")
        hooked.add(hook.when_option)
    for item in node.options:
        if item.npc_memory_targets or item.requires:
            raise ValueError(f"{node.choice_id}/{item.option_id}: no NPC memory or gate.")
        tags = item.character_memory_tags
        if len(tags) != 2 or not set(tags) <= TENDENCIES:
            raise ValueError(f"{node.choice_id}/{item.option_id}: two known tags required.")
        if item.memory_type not in MEMORY_KINDS:
            raise ValueError(f"{node.choice_id}/{item.option_id}: unknown memory type.")


def validate_node(node: ChoiceNode) -> None:
    if node.mission_kind == PROLOGUE_KIND:
        _validate_prologue_node(node)
        if BACKFILL_OPTION in {item.option_id for item in node.options}:
            raise ValueError(f"{node.choice_id}: option id is reserved.")
        return
    if node.mission_kind not in {"principal", "secundaria"}:
        raise ValueError(f"{node.choice_id}: contracts never carry narrative nodes.")
    if len(node.options) < 2 or len({item.option_id for item in node.options}) != len(
        node.options
    ):
        raise ValueError(f"{node.choice_id}: options must be unique and at least two.")
    if BACKFILL_OPTION in {item.option_id for item in node.options}:
        raise ValueError(f"{node.choice_id}: option id is reserved.")
    for item in node.options:
        if not item.character_memory_tags and not item.npc_memory_targets:
            raise ValueError(f"{node.choice_id}/{item.option_id}: choice leaves no memory.")
        if any(target.knowledge not in KNOWLEDGE_SOURCES for target in item.npc_memory_targets):
            raise ValueError(f"{node.choice_id}/{item.option_id}: unknown knowledge source.")
    if not node.future_hooks:
        raise ValueError(f"{node.choice_id}: node needs at least one future hook.")
    receivers = {
        target.npc_id for item in node.options for target in item.npc_memory_targets
    }
    for hook in node.future_hooks:
        if hook.basis != HOOK_BASIS_NPC or hook.when_option is not None:
            raise ValueError(f"{hook.hook_id}: mission hooks read NPC memory for any option.")
        if not set(hook.knowledge_holders) <= receivers:
            raise ValueError(f"{hook.hook_id}: holder never receives this memory.")


@dataclass(frozen=True, slots=True)
class ChoiceCatalog:
    nodes: Mapping[str, ChoiceNode]

    def by_mission(self, mission_id: str) -> ChoiceNode | None:
        return next((node for node in self.nodes.values() if node.mission_id == mission_id), None)

    def hook(self, hook_id: str) -> tuple[ChoiceNode, FutureHook] | None:
        choice_id = hook_id.split("->", 1)[0]
        node = self.nodes.get(choice_id)
        if node is None:
            return None
        hook = next((item for item in node.future_hooks if item.hook_id == hook_id), None)
        return (node, hook) if hook is not None else None

    def hooks_for(self, target: str) -> tuple[tuple[ChoiceNode, FutureHook], ...]:
        return tuple(
            (node, hook)
            for node in self.nodes.values()
            for hook in node.future_hooks
            if hook.target == target
        )


def build_catalog(nodes: Iterable[Mapping]) -> ChoiceCatalog:
    built: dict[str, ChoiceNode] = {}
    missions: set[str] = set()
    for data in nodes:
        node = build_node(data)
        if node.choice_id in built or node.mission_id in missions:
            raise ValueError(f"{node.choice_id}: duplicated node or mission.")
        built[node.choice_id] = node
        missions.add(node.mission_id)
    return ChoiceCatalog(built)


@cache
def narrative_catalog() -> ChoiceCatalog:
    raw = resources.files("asterion.domain").joinpath("narrative_choices_catalog.json")
    data = json.loads(raw.read_text(encoding="utf-8"))
    if data.get("version") != CATALOG_VERSION:
        raise ValueError("Narrative catalog version mismatch.")
    return build_catalog(data["nodes"])


def build_prologue_catalog(nodes: Iterable[Mapping]) -> ChoiceCatalog:
    built: dict[str, ChoiceNode] = {}
    for data in nodes:
        node = build_node(data)
        if node.mission_kind != PROLOGUE_KIND or node.choice_id in built:
            raise ValueError(f"{node.choice_id}: not a unique prologue node.")
        built[node.choice_id] = node
    return ChoiceCatalog(built)


@cache
def prologue_catalog() -> ChoiceCatalog:
    """The two Prologue nodes (Documento A), kept apart from the 72 mission nodes."""
    raw = resources.files("asterion.domain").joinpath("narrative_choices_prologue_catalog.json")
    data = json.loads(raw.read_text(encoding="utf-8"))
    if data.get("version") != CATALOG_VERSION:
        raise ValueError("Prologue catalog version mismatch.")
    return build_prologue_catalog(data["nodes"])


NARRATIVE_MISSION_IDS = frozenset(
    {f"P{i}" for i in range(1, 37)} | {f"S{i}" for i in range(1, 37)}
)


@dataclass(frozen=True, slots=True)
class CommittedChoice:
    """What a character legitimately carries from one node."""

    choice_id: str
    selected_option: str
    source: str
    npc_memories: frozenset[tuple[str, str]]  # (npc_id, tag) recorded for this character


def resolve_hook(
    node: ChoiceNode, hook: FutureHook, committed: CommittedChoice | None
) -> str | None:
    """Return the option a future scene may react to, or None for the common fallback.

    A missing choice (never taken, or ``neutral_backfill``) yields None: no
    retroactive consequence is invented. When the hook names NPCs, at least one
    of them must hold a memory from this choice; otherwise nobody in the scene
    could know it.
    """
    if committed is None or committed.choice_id != node.choice_id:
        return None
    if committed.source != PLAYER_SOURCE:
        return None
    option = node.option(committed.selected_option)
    if option is None:
        return None
    if hook.when_option is not None and option.option_id != hook.when_option:
        return None
    if hook.basis == HOOK_BASIS_CHARACTER:
        return option.option_id
    if hook.knowledge_holders:
        known = {npc for npc, _tag in committed.npc_memories}
        if not known.intersection(hook.knowledge_holders):
            return None
    return option.option_id


@dataclass(frozen=True, slots=True)
class ReactionLine:
    speaker: str
    speaker_name: str
    text: str
    draft: bool = False  # copy still waiting for the author's final approval


@cache
def reaction_lines() -> Mapping[tuple[str, str], ReactionLine]:
    """Approved future-reaction copy (Textos de Reação dos NPCs v1.0.1), by choice and option."""
    raw = resources.files("asterion.domain").joinpath("narrative_reactions_catalog.json")
    data = json.loads(raw.read_text(encoding="utf-8"))
    return {
        (choice_id, option_id): ReactionLine(**line)
        for choice_id, options in data["reactions"].items()
        for option_id, line in options.items()
    }


def legitimate_reaction(
    node: ChoiceNode, hook: FutureHook, committed: CommittedChoice | None
) -> ReactionLine | None:
    """The approved line a later scene may show, only if its speaker holds the memory."""
    option_id = resolve_hook(node, hook, committed)
    if option_id is None:
        return None
    line = reaction_lines().get((node.choice_id, option_id))
    if line is None:
        return None
    if hook.basis == HOOK_BASIS_NPC and line.speaker not in {
        npc for npc, _tag in committed.npc_memories
    }:
        return None
    return line
