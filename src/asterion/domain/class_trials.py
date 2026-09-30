"""Shared, content-neutral state shapes for the three-stage Class Trials."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from asterion.domain.arts import SENTINEL_ART_IDS
from asterion.domain.combat import Action, Combat, CombatEvent, Fighter
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats

TRIAL_IDS_BY_CLASS = {
    "sentinela": "trial.sentinela.guarda",
    "errante": "trial.errante.brecha",
    "vigia": "trial.vigia.alvo",
    "tecelao": "trial.tecelao.fios",
    "oraculo": "trial.oraculo.pressagio",
    "luminar": "trial.luminar.luz",
}

CLASS_PATHS = {
    "sentinela": ("bastiao", "devastador"),
    "errante": ("carrasco", "sabotador"),
    "vigia": ("atirador", "rastreador"),
    "tecelao": ("conjurador", "runico"),
    "oraculo": ("agoureiro", "invocador"),
    "luminar": ("guardiao", "inquisidor"),
}

TRIAL_COMPLETED_UNLOCK = "class_trial_completed"
TRIAL_CONTENT_PREFIX = "class_trial."
TRIAL_ENTITY_PREFIX = "trial_entity."
SENTINEL_TRIAL_ID = TRIAL_IDS_BY_CLASS["sentinela"]
SENTINEL_CONDITION_IDS = {
    1: "sentinel.stage_1.impact_mitigated",
    2: "sentinel.stage_2.break_window_hit",
    3: "sentinel.stage_3.resolute_retaliation",
}
SENTINEL_ENTITY_IDS = {
    1: "trial_entity.sentinela.impacto",
    2: "trial_entity.sentinela.blindado",
    3: "trial_entity.sentinela.revidar",
}


@dataclass(frozen=True, slots=True)
class TrialEntityDefinition:
    """Immutable entity template; encounter content supplies every combat value."""

    entity_id: str
    team: str
    turn_policy: str
    max_hp: Decimal
    stats: Mapping[str, Decimal]
    action_ids: tuple[str, ...] = ()
    required_to_survive: bool = False
    variant: None = None

    def __post_init__(self) -> None:
        if not self.entity_id.startswith(TRIAL_ENTITY_PREFIX) or len(self.entity_id) > 96:
            raise ValueError("Class Trial entities require a stable trial_entity.* id.")
        if self.team not in {"hostile", "ally"}:
            raise ValueError("Class Trial entity team must be hostile or ally.")
        if self.turn_policy not in {"active", "passive"}:
            raise ValueError("Class Trial entity turn policy must be active or passive.")
        if self.max_hp <= 0 or any(value < 0 for value in self.stats.values()):
            raise ValueError("Class Trial entity combat values must be non-negative.")
        if self.variant is not None:
            raise ValueError("Class Trial entities never have a Variant.")
        if self.turn_policy == "passive" and self.action_ids:
            raise ValueError("Passive Class Trial entities cannot have actions.")
        if self.team == "ally" and self.turn_policy != "passive":
            raise ValueError("Training allies do not receive offensive opportunities.")
        if self.team == "ally" and self.action_ids:
            raise ValueError("Training allies cannot have offensive actions.")
        if self.required_to_survive and self.team != "ally":
            raise ValueError("Only allied entities may be required to survive.")
        if len(set(self.action_ids)) != len(self.action_ids):
            raise ValueError("Class Trial entity action ids must be unique.")

    def to_data(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "team": self.team,
            "turn_policy": self.turn_policy,
            "max_hp": str(self.max_hp),
            "stats": {key: str(value) for key, value in self.stats.items()},
            "action_ids": list(self.action_ids),
            "required_to_survive": self.required_to_survive,
            "variant": None,
        }

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> "TrialEntityDefinition":
        if data.get("variant") is not None:
            raise ValueError("Persisted Class Trial entities cannot contain a Variant.")
        return cls(
            entity_id=str(data["entity_id"]),
            team=str(data["team"]),
            turn_policy=str(data["turn_policy"]),
            max_hp=Decimal(str(data["max_hp"])),
            stats={key: Decimal(str(value)) for key, value in data.get("stats", {}).items()},
            action_ids=tuple(data.get("action_ids", ())),
            required_to_survive=bool(data.get("required_to_survive", False)),
            variant=None,
        )


@dataclass(frozen=True, slots=True)
class TrialStageDefinition:
    """Frozen stage template reused unchanged on every retry of that stage."""

    stage: int
    entities: tuple[TrialEntityDefinition, ...]
    required_conditions: tuple[str, ...] = ()
    allowed_art_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.stage not in {1, 2, 3}:
            raise ValueError("A Class Trial stage must be I, II, or III.")
        ids = tuple(entity.entity_id for entity in self.entities)
        if not self.entities or len(set(ids)) != len(ids):
            raise ValueError("A Class Trial stage needs uniquely identified entities.")
        if not any(entity.team == "hostile" for entity in self.entities):
            raise ValueError("A Class Trial stage needs at least one hostile target.")
        if len(set(self.required_conditions)) != len(self.required_conditions):
            raise ValueError("Required pedagogic conditions must be unique.")
        if any(not value or len(value) > 96 for value in self.required_conditions):
            raise ValueError("Pedagogic condition ids must be stable and non-empty.")
        if len(set(self.allowed_art_ids)) != len(self.allowed_art_ids):
            raise ValueError("Configured Class Trial Arts must be unique.")
        if len(self.allowed_art_ids) > 3:
            raise ValueError("Class Trials use at most three configured Class Arts.")

    def to_data(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "entities": [entity.to_data() for entity in self.entities],
            "required_conditions": list(self.required_conditions),
            "allowed_art_ids": list(self.allowed_art_ids),
        }

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> "TrialStageDefinition":
        return cls(
            stage=int(data["stage"]),
            entities=tuple(TrialEntityDefinition.from_data(row) for row in data["entities"]),
            required_conditions=tuple(data.get("required_conditions", ())),
            allowed_art_ids=tuple(data.get("allowed_art_ids", ())),
        )


def sentinel_stage_definition(
    stage: int, *, allowed_art_ids: tuple[str, ...] = ()
) -> TrialStageDefinition:
    """Return the frozen Sentinela training template using TDO v1.0.12 values."""
    if stage not in SENTINEL_ENTITY_IDS:
        raise ValueError("Sentinela has three documented trial stages.")
    if len(allowed_art_ids) > 3 or not set(allowed_art_ids).issubset(
        set(SENTINEL_ART_IDS.values())
    ):
        raise ValueError("Sentinela trials accept at most three valid equipped Arts.")

    stage_values = {
        1: (Decimal("650"), Decimal("105"), Decimal("90"), Decimal("80"),
            ("trial.sentinela.golpe_contido", "trial.sentinela.impacto_anunciado")),
        2: (Decimal("620"), Decimal("90"), Decimal("135"), Decimal("75"),
            ("trial.sentinela.golpe_pedra_treino",)),
        3: (Decimal("700"), Decimal("105"), Decimal("100"), Decimal("85"),
            ("trial.sentinela.golpe_guarda_treino", "trial.sentinela.martelo_anunciado")),
    }
    hp, attack, defense, agility, action_ids = stage_values[stage]
    entity = TrialEntityDefinition(
        entity_id=SENTINEL_ENTITY_IDS[stage],
        team="hostile",
        turn_policy="active",
        max_hp=hp,
        stats={"attack": attack, "defense": defense, "agility": agility},
        action_ids=action_ids,
    )
    return TrialStageDefinition(
        stage=stage,
        entities=(entity,),
        required_conditions=(SENTINEL_CONDITION_IDS[stage],),
        allowed_art_ids=tuple(allowed_art_ids),
    )


def sentinel_player_actions(allowed_art_ids: tuple[str, ...]) -> dict[str, Action]:
    """Build only the Sentinela Arts present in the frozen combat configuration."""
    if len(allowed_art_ids) > 3 or len(set(allowed_art_ids)) != len(allowed_art_ids):
        raise ValueError("Sentinela combat configuration accepts at most three unique Arts.")
    if not set(allowed_art_ids).issubset(set(SENTINEL_ART_IDS.values())):
        raise ValueError("Unknown Sentinela Art in trial combat configuration.")
    definitions = {
        SENTINEL_ART_IDS["golpe_de_guarda"]: Action(
            SENTINEL_ART_IDS["golpe_de_guarda"], "Golpe de Guarda", Decimal("1.10"),
            cooldown=2,
        ),
        SENTINEL_ART_IDS["quebra_postura"]: Action(
            SENTINEL_ART_IDS["quebra_postura"], "Quebra-Postura", Decimal("0.90"),
            attack_debuff=Decimal("0.10"), duration=2, cooldown=3,
            effect_stat="defense", effect_id="sentinel.quebra_postura",
        ),
        SENTINEL_ART_IDS["muralha_breve"]: Action(
            SENTINEL_ART_IDS["muralha_breve"], "Muralha Breve", Decimal(0),
            cooldown=3, self_barrier_coefficient=Decimal("0.70"),
            self_barrier_duration=2,
        ),
        SENTINEL_ART_IDS["impacto_resoluto"]: Action(
            SENTINEL_ART_IDS["impacto_resoluto"], "Impacto Resoluto", Decimal("1.35"),
            cooldown=3,
        ),
    }
    return {
        "attack": Action("attack", "Ataque Básico", Decimal(1)),
        **{art_id: definitions[art_id] for art_id in allowed_art_ids},
    }


def sentinel_enemy_actions(stage: int) -> dict[str, Action]:
    """Return the documented deterministic Echo actions for the selected stage."""
    if stage == 1:
        return {
            "trial.sentinela.golpe_contido": Action(
                "trial.sentinela.golpe_contido", "Golpe Contido", Decimal("1.00")
            ),
            "trial.sentinela.impacto_anunciado": Action(
                "trial.sentinela.impacto_anunciado", "Impacto Anunciado", Decimal("1.65"),
                prepared=True,
            ),
        }
    if stage == 2:
        return {
            "trial.sentinela.golpe_pedra_treino": Action(
                "trial.sentinela.golpe_pedra_treino", "Golpe de Pedra de Treino",
                Decimal("0.95"),
            )
        }
    if stage == 3:
        return {
            "trial.sentinela.golpe_guarda_treino": Action(
                "trial.sentinela.golpe_guarda_treino", "Golpe de Guarda de Treino",
                Decimal("1.00"),
            ),
            "trial.sentinela.martelo_anunciado": Action(
                "trial.sentinela.martelo_anunciado", "Martelo Anunciado", Decimal("1.60"),
                prepared=True, self_effect_stat="defense",
                self_effect_magnitude=Decimal("0.20"), self_effect_duration=1,
                self_effect_id="sentinel.guarda_aberta",
            ),
        }
    raise ValueError("Sentinela has three documented trial stages.")


def create_sentinel_trial_combat(
    player: Fighter, definition: TrialStageDefinition
) -> Combat:
    """Materialize a one-Echo duel without using a Bestiary creature or Variant."""
    canonical = sentinel_stage_definition(
        definition.stage, allowed_art_ids=definition.allowed_art_ids
    )
    if canonical.to_data() != definition.to_data():
        raise ValueError("Sentinela trial parameters must match the authoritative stage plan.")
    entity = definition.entities[0]
    enemy = Fighter(
        id=entity.entity_id,
        name={1: "Eco de Impacto", 2: "Eco Blindado", 3: "Eco de Guardar e Revidar"}[
            definition.stage
        ],
        level=10,
        stats=CombatStats(
            entity.max_hp,
            entity.stats["attack"],
            entity.stats["defense"],
            entity.stats["agility"],
        ),
        hp=entity.max_hp,
    )
    return Combat(
        id=uuid4(),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions=sentinel_player_actions(definition.allowed_art_ids),
        enemy_actions=sentinel_enemy_actions(definition.stage),
        ai_cycle=entity.action_ids,
        variant=None,
        external_consumables_allowed=False,
    )


@dataclass(frozen=True, slots=True)
class TrialCombatEvent:
    """Server-observed combat facts used by deterministic pedagogy evaluators."""

    event_id: str
    event_type: str
    actor_id: str
    target_ids: tuple[str, ...] = ()
    action_id: str = ""
    satisfied_conditions: tuple[str, ...] = ()
    entity_hp: Mapping[str, Decimal] | None = None
    entity_barriers: Mapping[str, tuple[Decimal, int]] | None = None
    player_hp: Decimal | None = None
    data: Mapping[str, Any] | None = None
    calculated_damage: Decimal = Decimal(0)
    effective_damage: Decimal = Decimal(0)
    barrier_absorbed: Decimal = Decimal(0)
    target_barrier_source: str = ""
    target_effect_ids: tuple[str, ...] = ()
    defender_mitigation_applied: bool = False
    defender_prevented_damage: Decimal = Decimal(0)
    prepared_resolution: bool = False
    effect_applied: bool = False
    actor_effect_id: str = ""
    retaliation_valid: bool = False
    retaliation_used: bool = False
    retaliation_activation_id: str = ""
    retaliation_source_type: str = ""
    retaliation_source_event_id: str = ""
    retaliation_source_actor_id: str = ""
    dodged: bool = False

    def __post_init__(self) -> None:
        if not self.event_id or len(self.event_id) > 128:
            raise ValueError("Class Trial combat events require a stable id.")
        if not self.event_type or len(self.event_type) > 64:
            raise ValueError("Class Trial combat events require a type.")
        if len(set(self.satisfied_conditions)) != len(self.satisfied_conditions):
            raise ValueError("One combat event cannot repeat a condition id.")
        if self.player_hp is not None and self.player_hp < 0:
            raise ValueError("Player HP cannot be negative.")
        if min(
            self.calculated_damage,
            self.effective_damage,
            self.barrier_absorbed,
            self.defender_prevented_damage,
        ) < 0:
            raise ValueError("Class Trial combat damage facts cannot be negative.")
        if any(value < 0 for value in (self.entity_hp or {}).values()):
            raise ValueError("Training entity HP cannot be negative.")
        if any(
            value < 0 or duration < 0
            for value, duration in (self.entity_barriers or {}).values()
        ):
            raise ValueError("Training entity barriers cannot be negative.")


def trial_event_from_combat_event(
    combat: Combat, event: CombatEvent
) -> TrialCombatEvent:
    """Translate an objective shared-engine event into trial-domain facts."""
    actor = event.actor_entity_id
    if not actor:
        actor = combat.fighters[event.actor].id if event.actor in combat.fighters else event.actor
    action_id = event.action
    event_type = "combat_action"
    if action_id.startswith("prepare:"):
        action_id = action_id.removeprefix("prepare:")
        event_type = "prepared_action"
    return TrialCombatEvent(
        event_id=f"{combat.id.hex}:{event.sequence}",
        event_type=event_type,
        actor_id=actor,
        target_ids=(event.target,) if event.target else (),
        action_id=action_id,
        calculated_damage=Decimal(event.calculated_damage),
        effective_damage=Decimal(event.effective_damage),
        barrier_absorbed=event.barrier_absorbed,
        target_barrier_source=event.target_barrier_source,
        target_effect_ids=event.target_effect_ids,
        defender_mitigation_applied=event.defender_mitigation_applied,
        defender_prevented_damage=Decimal(event.defender_prevented_damage),
        prepared_resolution=event.prepared_resolution,
        effect_applied=bool(event.effect_id or event.actor_effect_id),
        actor_effect_id=event.actor_effect_id,
        retaliation_valid=event.retaliation_valid,
        retaliation_used=event.retaliation_used,
        retaliation_activation_id=event.retaliation_activation_id,
        retaliation_source_type=event.retaliation_source_type,
        retaliation_source_event_id=event.retaliation_source_event_id,
        retaliation_source_actor_id=event.retaliation_source_actor_id,
        dodged=event.dodged,
    )


def sentinel_conditions_for_event(
    stage: int, event: TrialCombatEvent
) -> tuple[str, ...]:
    """Interpret objective combat facts for the Sentinela's three pedagogy checks."""
    if event.event_type != "combat_action":
        return ()
    condition = SENTINEL_CONDITION_IDS.get(stage)
    if condition is None:
        return ()
    echo_id = SENTINEL_ENTITY_IDS[stage]
    if stage == 1:
        muralha_source = f"player:{SENTINEL_ART_IDS['muralha_breve']}"
        mitigated = event.defender_mitigation_applied or (
            event.target_barrier_source == muralha_source
            and event.barrier_absorbed >= 1
        )
        if (
            event.actor_id == echo_id
            and event.action_id == "trial.sentinela.impacto_anunciado"
            and event.target_ids == ("player",)
            and event.prepared_resolution
            and not event.dodged
            and mitigated
        ):
            return (condition,)
    elif stage == 2:
        if (
            event.actor_id == "player"
            and event.action_id in {"attack", *SENTINEL_ART_IDS.values()}
            and event.target_ids == (echo_id,)
            and event.effective_damage > 0
            and "sentinel.quebra_postura" in event.target_effect_ids
        ):
            return (condition,)
    elif stage == 3:
        if (
            event.actor_id == "player"
            and event.action_id == SENTINEL_ART_IDS["impacto_resoluto"]
            and event.target_ids == (echo_id,)
            and event.retaliation_valid
            and event.retaliation_used
            and event.retaliation_source_type == "defender"
            and event.retaliation_source_actor_id == echo_id
            and bool(event.retaliation_activation_id)
        ):
            return (condition,)
    return ()


def fresh_attempt_state(
    definition: TrialStageDefinition, player_hp: Decimal
) -> dict[str, Any]:
    """Create an empty, full-health attempt snapshot without balance defaults."""
    return {
        "player": {
            "hp": str(player_hp),
            "effects": [],
            "barrier": "0",
            "barrier_remaining": 0,
            "cooldowns": {},
            "resources": {},
        },
        "entities": {
            entity.entity_id: {
                "hp": str(entity.max_hp),
                "effects": [],
                "barrier": "0",
                "barrier_remaining": 0,
                "cooldowns": {},
                "resources": {},
            }
            for entity in definition.entities
        },
        "pedagogic_conditions": [],
        "processed_event_ids": [],
        "events": [],
        "external_consumables_used": 0,
    }


def reset_trial_combat(
    combat: Combat,
    definition: TrialStageDefinition,
    player_hp: Decimal,
) -> Combat:
    """Reset dynamic combat state while retaining the frozen stage's combat setup."""
    if combat.variant is not None or combat.result is not None:
        raise ValueError("Class Trial combats cannot start with a Variant or resolved result.")
    if "player" not in combat.fighters or combat.fighters["player"].id != "player":
        raise ValueError("Class Trial combat needs the canonical player fighter.")
    entity_by_id = {entity.entity_id: entity for entity in definition.entities}
    fighters_by_id = {
        fighter.id: fighter
        for key, fighter in combat.fighters.items()
        if key != "player"
    }
    if set(fighters_by_id) != set(entity_by_id):
        raise ValueError("Combat fighters must match the persisted trial entity identities.")
    if not set(definition.allowed_art_ids).issubset(combat.player_actions):
        raise ValueError("Configured Class Trial Arts are missing from the combat snapshot.")
    enemy_action_ids = {
        action_id for entity in definition.entities for action_id in entity.action_ids
    }
    if not enemy_action_ids.issubset(combat.enemy_actions):
        raise ValueError("Training entity actions are missing from the combat snapshot.")

    result = deepcopy(combat)
    result.id = uuid4()
    result.version = 0
    result.round = 1
    result.order = ()
    result.turn_index = 0
    result.used_attack = False
    result.used_defend = False
    result.used_art = False
    result.pending_response = None
    result.ai_position = 0
    result.rng_cursor = 0
    result.result = None
    result.events = []
    result.mechanic_events = []
    result.prepared_action = None
    result.prepared_source = None
    result.prepared_target = None
    result.resolving_prepared = False
    result.response_window_seen = False
    result.variant = None
    result.dot_states = {}
    result.effect_sequence = 0
    result.application_sequence = 0
    result.blocked_application_events = []
    result.consumable_uses = 0
    result.external_consumables_allowed = False
    result.evasion_streaks = {}
    result.tutorial = None
    result.player_actions = {
        key: action
        for key, action in result.player_actions.items()
        if key in {"attack", "defend", *definition.allowed_art_ids}
    }
    for key, fighter in result.fighters.items():
        fighter.opportunity = 0
        fighter.defending = False
        fighter.last_action = None
        fighter.cooldowns = {}
        fighter.effects = []
        fighter.barrier = Decimal(0)
        fighter.barrier_remaining = 0
        fighter.barrier_applied_opportunity = 0
        fighter.barrier_source = ""
        fighter.ward_remaining = 0
        fighter.ward_charges = 0
        fighter.ward_applied_opportunity = 0
        fighter.retaliation_charges = 0
        fighter.retaliation_remaining = 0
        fighter.retaliation_applied_opportunity = 0
        fighter.retaliation_activation_id = ""
        fighter.retaliation_source_type = ""
        fighter.retaliation_source_event_id = ""
        fighter.retaliation_source_actor_id = ""
        if key == "player":
            fighter.hp = player_hp
        else:
            fighter.hp = entity_by_id[fighter.id].max_hp
    return result
