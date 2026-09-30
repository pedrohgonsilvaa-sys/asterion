"""Shared, content-neutral state shapes for the three-stage Class Trials."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import uuid4

from asterion.domain.arts import (
    ERRANTE_ART_IDS,
    SENTINEL_ART_IDS,
    TECELAO_ART_IDS,
    VIGIA_ART_IDS,
)
from asterion.domain.combat import Action, ActionEffect, Combat, CombatEvent, Fighter
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
ERRANTE_TRIAL_ID = TRIAL_IDS_BY_CLASS["errante"]
ERRANTE_CONDITION_IDS = {
    1: "errante.stage_1.bleed_tick",
    2: "errante.stage_2.prepared_response_hit",
    3: "errante.stage_3.exposed_opportunity",
}
ERRANTE_ENTITY_IDS = {
    1: "trial_entity.errante.primeiro_corte",
    2: "trial_entity.errante.passo",
    3: "trial_entity.errante.brecha",
}
ERRANTE_TRAINING_CUT_ACTION_ID = "trial.errante.corte_de_treino"
ERRANTE_SHORT_CUT_ACTION_ID = "trial.errante.corte_curto"
ERRANTE_PREPARED_ACTION_ID = "trial.errante.golpe_de_ruptura_treino"
ERRANTE_STAGE_3_CUT_A_ACTION_ID = "trial.errante.corte_treino_a"
ERRANTE_STAGE_3_CUT_B_ACTION_ID = "trial.errante.corte_treino_b"
ERRANTE_EXPOSE_ACTION_ID = "trial.errante.exposto"
ERRANTE_EXPOSED_EFFECT_ID = "errante.exposto"
ERRANTE_STEP_EVASION_EFFECT_ID = "errante.passo_velado.evasao"
ERRANTE_STEP_WINDOW_EFFECT_ID = "errante.passo_velado.janela_ofensiva"
VIGIA_TRIAL_ID = TRIAL_IDS_BY_CLASS["vigia"]
VIGIA_CONDITION_IDS = {
    1: "vigia.stage_1.marked_window_hit",
    2: "vigia.stage_2.layers_removed",
    3: "vigia.stage_3.exposed_art_hit",
}
VIGIA_ENTITY_IDS = {
    1: "trial_entity.vigia.marca",
    2: "trial_entity.vigia.camadas",
    3: "trial_entity.vigia.momento",
}
VIGIA_MARK_EFFECT_ID = "vigia.marca_da_presa"
VIGIA_EYE_PER_EFFECT_ID = "vigia.olho_da_vigilia.per"
VIGIA_EYE_CRIT_EFFECT_ID = "vigia.olho_da_vigilia.crit"
VIGIA_PROTECTED_TAG = "vigia.protegido"
VIGIA_EXPOSED_TAG = "vigia.exposto"
TECELAO_TRIAL_ID = TRIAL_IDS_BY_CLASS["tecelao"]
TECELAO_CONDITION_IDS = {
    1: ("tecelao.stage_1.burn_applied",),
    2: ("tecelao.stage_2.multi_target_rupture",),
    3: ("tecelao.stage_3.thread_consumed_twice", "tecelao.stage_3.barrier_absorbed"),
}
TECELAO_ENTITY_IDS = {
    1: (
        "trial_entity.tecelao.acender.principal",
        "trial_entity.tecelao.acender.manifestacao_1",
        "trial_entity.tecelao.acender.manifestacao_2",
    ),
    2: (
        "trial_entity.tecelao.romper.1",
        "trial_entity.tecelao.romper.2",
        "trial_entity.tecelao.romper.3",
    ),
    3: ("trial_entity.tecelao.entrelacar",),
}
TECELAO_THREAD_KEY = "trama_encadeada"
TECELAO_THREAD_BASE_POWER_BONUS = Decimal("0.10")
TECELAO_THREAD_BASE_DURATION = 2


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
    protection_layers: int = 0
    protection_reduction_per_layer: Decimal = Decimal(0)
    initial_state_tags: tuple[str, ...] = ()
    tagged_direct_damage_reductions: Mapping[str, Decimal] = field(default_factory=dict)
    action_cycle: tuple[str, ...] = ()

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
        if self.protection_layers < 0 or self.protection_reduction_per_layer < 0:
            raise ValueError("Training protection layers cannot be negative.")
        if any(not tag for tag in self.initial_state_tags):
            raise ValueError("Training state tags must be non-empty.")
        if any(value < 0 or value > 1 for value in self.tagged_direct_damage_reductions.values()):
            raise ValueError("Training direct damage reductions must be between zero and one.")
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
        if self.action_cycle and not set(self.action_cycle).issubset(self.action_ids):
            raise ValueError("Training action cycles must use declared entity actions.")

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
            "protection_layers": self.protection_layers,
            "protection_reduction_per_layer": str(self.protection_reduction_per_layer),
            "initial_state_tags": list(self.initial_state_tags),
            "tagged_direct_damage_reductions": {
                key: str(value)
                for key, value in self.tagged_direct_damage_reductions.items()
            },
            "action_cycle": list(self.action_cycle),
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
            protection_layers=int(data.get("protection_layers", 0)),
            protection_reduction_per_layer=Decimal(
                str(data.get("protection_reduction_per_layer", "0"))
            ),
            initial_state_tags=tuple(data.get("initial_state_tags", ())),
            tagged_direct_damage_reductions={
                key: Decimal(str(value))
                for key, value in data.get("tagged_direct_damage_reductions", {}).items()
            },
            action_cycle=tuple(data.get("action_cycle", ())),
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


def errante_stage_definition(
    stage: int, *, allowed_art_ids: tuple[str, ...] = ()
) -> TrialStageDefinition:
    """Return a frozen, trial-only Errante template with persisted Art slots."""
    if stage not in ERRANTE_ENTITY_IDS:
        raise ValueError("Errante has three documented trial stages.")
    if len(allowed_art_ids) > 3 or not set(allowed_art_ids).issubset(
        set(ERRANTE_ART_IDS.values())
    ):
        raise ValueError("Errante trials accept at most three valid equipped Arts.")

    stage_values = {
        1: (
            Decimal("580"), Decimal("95"), Decimal("85"), Decimal("90"),
            (ERRANTE_TRAINING_CUT_ACTION_ID,),
        ),
        2: (
            Decimal("620"), Decimal("105"), Decimal("85"), Decimal("90"),
            (ERRANTE_SHORT_CUT_ACTION_ID, ERRANTE_PREPARED_ACTION_ID),
        ),
        3: (
            Decimal("620"), Decimal("100"), Decimal("90"), Decimal("95"),
            (ERRANTE_STAGE_3_CUT_A_ACTION_ID,
             ERRANTE_STAGE_3_CUT_B_ACTION_ID,
             ERRANTE_EXPOSE_ACTION_ID),
        ),
    }
    hp, attack, defense, agility, action_ids = stage_values[stage]
    entity = TrialEntityDefinition(
        entity_id=ERRANTE_ENTITY_IDS[stage],
        team="hostile",
        turn_policy="active",
        max_hp=hp,
        stats={"attack": attack, "defense": defense, "agility": agility},
        action_ids=action_ids,
    )
    return TrialStageDefinition(
        stage=stage,
        entities=(entity,),
        required_conditions=(ERRANTE_CONDITION_IDS[stage],),
        allowed_art_ids=tuple(allowed_art_ids),
    )


def errante_player_actions(allowed_art_ids: tuple[str, ...]) -> dict[str, Action]:
    """Build only the Errante Arts recorded in the persisted active slots."""
    if len(allowed_art_ids) > 3 or len(set(allowed_art_ids)) != len(allowed_art_ids):
        raise ValueError("Errante combat configuration accepts at most three unique Arts.")
    if not set(allowed_art_ids).issubset(set(ERRANTE_ART_IDS.values())):
        raise ValueError("Unknown Errante Art in trial combat configuration.")
    definitions = {
        ERRANTE_ART_IDS["corte_veloz"]: Action(
            ERRANTE_ART_IDS["corte_veloz"], "Corte Veloz", Decimal("1.15"),
            cooldown=2,
        ),
        ERRANTE_ART_IDS["ferida_profunda"]: Action(
            ERRANTE_ART_IDS["ferida_profunda"], "Ferida Profunda", Decimal("0.90"),
            native_dot_kind="bleed", native_dot_stacks=1, cooldown=2,
        ),
        ERRANTE_ART_IDS["passo_velado"]: Action(
            ERRANTE_ART_IDS["passo_velado"], "Passo Velado", Decimal(0),
            cooldown=4,
            self_effect_stat="evasion",
            self_effect_magnitude=Decimal("15"),
            self_effect_kind="buff",
            self_effect_modifier_mode="percentage_points",
            self_effect_duration=1,
            self_effect_id=ERRANTE_STEP_EVASION_EFFECT_ID,
            next_direct_crit_bonus=Decimal("10"),
            next_direct_crit_duration=2,
            next_direct_crit_effect_id=ERRANTE_STEP_WINDOW_EFFECT_ID,
            target_mode="self",
        ),
        ERRANTE_ART_IDS["golpe_oportuno"]: Action(
            ERRANTE_ART_IDS["golpe_oportuno"], "Golpe Oportuno", Decimal("1.25"),
            cooldown=3, crit_bonus_if_target_debuffed=Decimal("15"),
        ),
    }
    return {
        "attack": Action("attack", "Ataque Básico", Decimal(1)),
        **{art_id: definitions[art_id] for art_id in allowed_art_ids},
    }


def errante_enemy_actions(stage: int) -> dict[str, Action]:
    """Return deterministic Errante Echo actions for the current training stage."""
    if stage == 1:
        return {
            ERRANTE_TRAINING_CUT_ACTION_ID: Action(
                ERRANTE_TRAINING_CUT_ACTION_ID,
                "Corte de Treino",
                Decimal("1.00"),
            )
        }
    if stage == 2:
        return {
            ERRANTE_SHORT_CUT_ACTION_ID: Action(
                ERRANTE_SHORT_CUT_ACTION_ID,
                "Corte Curto",
                Decimal("0.95"),
            ),
            ERRANTE_PREPARED_ACTION_ID: Action(
                ERRANTE_PREPARED_ACTION_ID,
                "Golpe de Ruptura de Treino",
                Decimal("1.65"),
                prepared=True,
            ),
        }
    if stage == 3:
        return {
            ERRANTE_STAGE_3_CUT_A_ACTION_ID: Action(
                ERRANTE_STAGE_3_CUT_A_ACTION_ID,
                "Corte de Treino",
                Decimal("0.95"),
            ),
            ERRANTE_STAGE_3_CUT_B_ACTION_ID: Action(
                ERRANTE_STAGE_3_CUT_B_ACTION_ID,
                "Corte de Treino",
                Decimal("0.95"),
            ),
            ERRANTE_EXPOSE_ACTION_ID: Action(
                ERRANTE_EXPOSE_ACTION_ID,
                "Exposto",
                Decimal(0),
                self_effect_stat="defense",
                self_effect_magnitude=Decimal(0),
                self_effect_duration=1,
                self_effect_id=ERRANTE_EXPOSED_EFFECT_ID,
                target_mode="self",
            ),
        }
    raise ValueError("Errante has three documented trial stages.")


def create_errante_trial_combat(
    player: Fighter, definition: TrialStageDefinition
) -> Combat:
    """Materialize the stage Echo and only the persisted equipped Errante Arts."""
    canonical = errante_stage_definition(
        definition.stage, allowed_art_ids=definition.allowed_art_ids
    )
    if canonical.to_data() != definition.to_data():
        raise ValueError("Errante trial parameters must match the persisted stage plan.")
    entity = definition.entities[0]
    enemy = Fighter(
        id=entity.entity_id,
        name={1: "Eco do Primeiro Corte", 2: "Eco do Passo", 3: "Eco da Brecha"}[
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
        player_actions=errante_player_actions(definition.allowed_art_ids),
        enemy_actions=errante_enemy_actions(definition.stage),
        ai_cycle=entity.action_ids,
        variant=None,
        external_consumables_allowed=False,
    )


def vigia_stage_definition(
    stage: int, *, allowed_art_ids: tuple[str, ...] = ()
) -> TrialStageDefinition:
    """Return the frozen Nv.10 Vigia training stage from TDO v1.0.12."""
    if stage not in VIGIA_ENTITY_IDS:
        raise ValueError("Vigia has three documented trial stages.")
    if len(allowed_art_ids) > 3 or not set(allowed_art_ids).issubset(
        set(VIGIA_ART_IDS.values())
    ):
        raise ValueError("Vigia trials accept at most three valid equipped Arts.")
    values = {
        1: (Decimal("600"), Decimal("95"), Decimal("125"), Decimal("85"),
            ("trial.vigia.disparo_treino",)),
        2: (Decimal("650"), Decimal("90"), Decimal("90"), Decimal("85"),
            ("trial.vigia.disparo_treino",)),
        3: (Decimal("650"), Decimal("100"), Decimal("90"), Decimal("90"),
            ("trial.vigia.disparo_protegido", "trial.vigia.disparo_exposto")),
    }
    hp, attack, defense, agility, action_ids = values[stage]
    entity = TrialEntityDefinition(
        entity_id=VIGIA_ENTITY_IDS[stage],
        team="hostile",
        turn_policy="active",
        max_hp=hp,
        stats={"attack": attack, "defense": defense, "agility": agility},
        action_ids=action_ids,
        protection_layers=3 if stage == 2 else 0,
        protection_reduction_per_layer=Decimal("0.12") if stage == 2 else Decimal(0),
        initial_state_tags=(VIGIA_PROTECTED_TAG,) if stage == 3 else (),
        tagged_direct_damage_reductions=(
            {VIGIA_PROTECTED_TAG: Decimal("0.25")} if stage == 3 else {}
        ),
        action_cycle=(
            ("trial.vigia.disparo_protegido", "trial.vigia.disparo_exposto")
            if stage == 3 else ()
        ),
    )
    return TrialStageDefinition(
        stage=stage,
        entities=(entity,),
        required_conditions=(VIGIA_CONDITION_IDS[stage],),
        allowed_art_ids=tuple(allowed_art_ids),
    )


def vigia_player_actions(allowed_art_ids: tuple[str, ...]) -> dict[str, Action]:
    if len(allowed_art_ids) > 3 or len(set(allowed_art_ids)) != len(allowed_art_ids):
        raise ValueError("Vigia combat configuration accepts at most three unique Arts.")
    if not set(allowed_art_ids).issubset(set(VIGIA_ART_IDS.values())):
        raise ValueError("Unknown Vigia Art in trial combat configuration.")
    definitions = {
        VIGIA_ART_IDS["disparo_preciso"]: Action(
            VIGIA_ART_IDS["disparo_preciso"], "Disparo Preciso", Decimal("1.15"), cooldown=2
        ),
        VIGIA_ART_IDS["marca_da_presa"]: Action(
            VIGIA_ART_IDS["marca_da_presa"], "Marca da Presa", Decimal("0.85"),
            attack_debuff=Decimal("0.08"), duration=2, cooldown=3,
            effect_stat="defense", effect_id=VIGIA_MARK_EFFECT_ID,
        ),
        VIGIA_ART_IDS["saraivada"]: Action(
            VIGIA_ART_IDS["saraivada"], "Saraivada", Decimal("0.40"),
            cooldown=3, hit_count=3,
        ),
        VIGIA_ART_IDS["olho_da_vigilia"]: Action(
            VIGIA_ART_IDS["olho_da_vigilia"], "Olho da Vigília", Decimal(0),
            cooldown=4, target_mode="self",
            self_effects=(
                ActionEffect(
                    VIGIA_EYE_PER_EFFECT_ID,
                    "per",
                    Decimal("12"),
                    2,
                    kind="buff",
                    stat_modifier_mode="percentage_points",
                ),
                ActionEffect(
                    VIGIA_EYE_CRIT_EFFECT_ID,
                    "crit",
                    Decimal("8"),
                    2,
                    kind="buff",
                    stat_modifier_mode="percentage_points",
                ),
            ),
        ),
    }
    return {
        "attack": Action("attack", "Ataque Básico", Decimal(1)),
        **{art_id: definitions[art_id] for art_id in allowed_art_ids},
    }


def vigia_enemy_actions(stage: int) -> dict[str, Action]:
    if stage in {1, 2}:
        return {
            "trial.vigia.disparo_treino": Action(
                "trial.vigia.disparo_treino", "Disparo de Treino", Decimal("0.95")
            )
        }
    if stage == 3:
        return {
            "trial.vigia.disparo_protegido": Action(
                "trial.vigia.disparo_protegido", "Disparo de Treino", Decimal("1.00"),
                self_state_tags_after=(VIGIA_EXPOSED_TAG,),
            ),
            "trial.vigia.disparo_exposto": Action(
                "trial.vigia.disparo_exposto", "Disparo de Treino", Decimal("1.00"),
                self_state_tags_after=(VIGIA_PROTECTED_TAG,),
            ),
        }
    raise ValueError("Vigia has three documented trial stages.")


def create_vigia_trial_combat(
    player: Fighter, definition: TrialStageDefinition
) -> Combat:
    canonical = vigia_stage_definition(
        definition.stage, allowed_art_ids=definition.allowed_art_ids
    )
    if canonical.to_data() != definition.to_data():
        raise ValueError("Vigia trial parameters must match the authoritative stage plan.")
    entity = definition.entities[0]
    enemy = Fighter(
        id=entity.entity_id,
        name={1: "Eco da Marca", 2: "Eco das Camadas", 3: "Eco do Momento"}[definition.stage],
        level=10,
        stats=CombatStats(
            entity.max_hp,
            entity.stats["attack"],
            entity.stats["defense"],
            entity.stats["agility"],
        ),
        hp=entity.max_hp,
        protection_layers=entity.protection_layers,
        protection_reduction_per_layer=entity.protection_reduction_per_layer,
        training_state_tags=entity.initial_state_tags,
        tagged_direct_damage_reductions=dict(entity.tagged_direct_damage_reductions),
    )
    return Combat(
        id=uuid4(),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters={"player": player, "enemy": enemy},
        player_actions=vigia_player_actions(definition.allowed_art_ids),
        enemy_actions=vigia_enemy_actions(definition.stage),
        ai_cycle=entity.action_cycle or entity.action_ids,
        variant=None,
        external_consumables_allowed=False,
    )


def tecelao_stage_definition(
    stage: int, *, allowed_art_ids: tuple[str, ...] = ()
) -> TrialStageDefinition:
    """Return the frozen Nv.10 Tecelão training stage from TDO v1.0.12."""
    if stage not in TECELAO_ENTITY_IDS:
        raise ValueError("Tecelão has three documented trial stages.")
    if len(allowed_art_ids) > 3 or not set(allowed_art_ids).issubset(
        set(TECELAO_ART_IDS.values())
    ):
        raise ValueError("Tecelão trials accept at most three valid equipped Arts.")
    if stage == 1:
        specs = (
            (TECELAO_ENTITY_IDS[1][0], "hostile", "active", Decimal("560"),
             Decimal("95"), Decimal("90"), Decimal("85"), ("trial.tecelao.fio_de_treino",)),
            (TECELAO_ENTITY_IDS[1][1], "hostile", "passive", Decimal("180"),
             Decimal("0"), Decimal("70"), Decimal("0"), ()),
            (TECELAO_ENTITY_IDS[1][2], "hostile", "passive", Decimal("180"),
             Decimal("0"), Decimal("70"), Decimal("0"), ()),
        )
    elif stage == 2:
        specs = tuple(
            (entity_id, "hostile", "active", Decimal("230"), Decimal("55"),
             Decimal("65"), Decimal("80"), ("trial.tecelao.pulso_menor",))
            for entity_id in TECELAO_ENTITY_IDS[2]
        )
    else:
        specs = (
            (TECELAO_ENTITY_IDS[3][0], "hostile", "active", Decimal("680"),
             Decimal("100"), Decimal("90"), Decimal("90"),
             ("trial.tecelao.fio_de_pressao", "trial.tecelao.ruptura_anunciada")),
        )
    entities = tuple(
        TrialEntityDefinition(
            entity_id=entity_id,
            team=team,
            turn_policy=turn_policy,
            max_hp=hp,
            stats={"attack": attack, "defense": defense, "agility": agility},
            action_ids=action_ids,
            action_cycle=(
                ("trial.tecelao.fio_de_pressao", "trial.tecelao.fio_de_pressao",
                 "trial.tecelao.ruptura_anunciada")
                if stage == 3 and entity_id == TECELAO_ENTITY_IDS[3][0]
                else ()
            ),
        )
        for entity_id, team, turn_policy, hp, attack, defense, agility, action_ids in specs
    )
    conditions = TECELAO_CONDITION_IDS[stage]
    return TrialStageDefinition(
        stage=stage,
        entities=entities,
        required_conditions=conditions,
        allowed_art_ids=tuple(allowed_art_ids),
    )


def tecelao_player_actions(allowed_art_ids: tuple[str, ...]) -> dict[str, Action]:
    if len(allowed_art_ids) > 3 or len(set(allowed_art_ids)) != len(allowed_art_ids):
        raise ValueError("Tecelão combat configuration accepts at most three unique Arts.")
    if not set(allowed_art_ids).issubset(set(TECELAO_ART_IDS.values())):
        raise ValueError("Unknown Tecelão Art in trial combat configuration.")
    definitions = {
        TECELAO_ART_IDS["fio_cortante"]: Action(
            TECELAO_ART_IDS["fio_cortante"], "Fio Cortante", Decimal("1.20"), cooldown=2,
            prepares_chain=TECELAO_THREAD_KEY,
            consumes_chain=TECELAO_THREAD_KEY,
            chain_power_bonus=TECELAO_THREAD_BASE_POWER_BONUS,
            prepares_chain_duration=TECELAO_THREAD_BASE_DURATION,
        ),
        TECELAO_ART_IDS["chama_tecida"]: Action(
            TECELAO_ART_IDS["chama_tecida"], "Chama Tecida", Decimal("0.85"),
            cooldown=2, native_dot_kind="burn", native_dot_stacks=1,
            prepares_chain=TECELAO_THREAD_KEY,
            consumes_chain=TECELAO_THREAD_KEY,
            chain_power_bonus=TECELAO_THREAD_BASE_POWER_BONUS,
            prepares_chain_duration=TECELAO_THREAD_BASE_DURATION,
        ),
        TECELAO_ART_IDS["ruptura_da_trama"]: Action(
            TECELAO_ART_IDS["ruptura_da_trama"], "Ruptura da Trama", Decimal("0.80"),
            cooldown=3, target_mode="all_opponents",
            prepares_chain=TECELAO_THREAD_KEY,
            consumes_chain=TECELAO_THREAD_KEY,
            chain_power_bonus=TECELAO_THREAD_BASE_POWER_BONUS,
            prepares_chain_duration=TECELAO_THREAD_BASE_DURATION,
        ),
        TECELAO_ART_IDS["veu_entrelacado"]: Action(
            TECELAO_ART_IDS["veu_entrelacado"], "Véu Entrelaçado", Decimal(0),
            cooldown=3, target_mode="self", self_barrier_coefficient=Decimal("0.90"),
            self_barrier_duration=2, prepares_chain=TECELAO_THREAD_KEY,
            consumes_chain=TECELAO_THREAD_KEY,
            chain_power_bonus=TECELAO_THREAD_BASE_POWER_BONUS,
            prepares_chain_duration=TECELAO_THREAD_BASE_DURATION,
        ),
    }
    return {
        "attack": Action("attack", "Ataque Básico", Decimal(1)),
        **{art_id: definitions[art_id] for art_id in allowed_art_ids},
    }


def tecelao_enemy_actions() -> dict[str, Action]:
    return {
        "trial.tecelao.fio_de_treino": Action(
            "trial.tecelao.fio_de_treino", "Fio de Treino", Decimal("0.95")
        ),
        "trial.tecelao.pulso_menor": Action(
            "trial.tecelao.pulso_menor", "Pulso Menor", Decimal("0.80")
        ),
        "trial.tecelao.fio_de_pressao": Action(
            "trial.tecelao.fio_de_pressao", "Fio de Pressão", Decimal("0.95")
        ),
        "trial.tecelao.ruptura_anunciada": Action(
            "trial.tecelao.ruptura_anunciada", "Ruptura Anunciada", Decimal("1.60"),
            prepared=True,
        ),
    }


def create_tecelao_trial_combat(
    player: Fighter, definition: TrialStageDefinition
) -> Combat:
    canonical = tecelao_stage_definition(
        definition.stage, allowed_art_ids=definition.allowed_art_ids
    )
    if canonical.to_data() != definition.to_data():
        raise ValueError("Tecelão trial parameters must match the authoritative stage plan.")
    fighters = {"player": player}
    names = {
        1: ("Eco Principal", "Manifestação Menor", "Manifestação Menor"),
        2: ("Eco Menor", "Eco Menor", "Eco Menor"),
        3: ("Eco Entrelaçado",),
    }[definition.stage]
    for entity, name in zip(definition.entities, names, strict=True):
        fighters[entity.entity_id] = Fighter(
            id=entity.entity_id,
            name=name,
            level=10,
            stats=CombatStats(
                entity.max_hp,
                entity.stats["attack"],
                entity.stats["defense"],
                entity.stats["agility"],
            ),
            hp=entity.max_hp,
            side="enemy",
            takes_turn=entity.turn_policy == "active",
            required_for_victory=True,
        )
    cycle = tuple(
        action_id
        for entity in definition.entities
        if entity.turn_policy == "active"
        for action_id in (entity.action_cycle or entity.action_ids)
    )
    return Combat(
        id=uuid4(),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters=fighters,
        player_actions=tecelao_player_actions(definition.allowed_art_ids),
        enemy_actions=tecelao_enemy_actions(),
        ai_cycle=cycle,
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
    action_instance_id: str = ""
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
    actor_effect_ids: tuple[str, ...] = ()
    prepared_action_instance_id: str = ""
    response_to_prepared_action_instance_id: str = ""
    dot_kind: str = ""
    dot_application_event_id: str = ""
    dot_source_id: str = ""
    hit_index: int = 1
    hit_count: int = 1
    protection_layers_before: int = 0
    protection_layers_after: int = 0
    target_state_tags: tuple[str, ...] = ()
    target_effect_application_event_ids: tuple[str, ...] = ()
    applied_effect_id: str = ""
    effect_application_event_id: str = ""
    chain_state_before: str = ""
    chain_state_after: str = ""
    chain_prepared_by_action_id: str = ""
    chain_consumed: bool = False
    chain_empowered: bool = False
    empowered_by_action_instance_id: str = ""
    chain_prepared_by_action_instance_id: str = ""
    chain_consumed_by_action_instance_id: str = ""
    chain_window_before: int = 0
    chain_window_after: int = 0
    power_component: str = ""
    power_multiplier: Decimal = Decimal(1)
    damage_power_multiplier: Decimal = Decimal(1)
    healing_power_multiplier: Decimal = Decimal(1)
    barrier_power_multiplier: Decimal = Decimal(1)
    trigger_scope: str = "per_action"

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
        if min(
            self.power_multiplier,
            self.damage_power_multiplier,
            self.healing_power_multiplier,
            self.barrier_power_multiplier,
        ) < 0:
            raise ValueError("Class Trial power multipliers cannot be negative.")
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
    if event.internal and event.dot_kind and action_id.startswith("dot:"):
        event_type = "dot_tick"
    elif event.action == "chain:expired":
        event_type = "chain_expired"
    if action_id.startswith("prepare:"):
        action_id = action_id.removeprefix("prepare:")
        event_type = "prepared_action"
    return TrialCombatEvent(
        event_id=(
            f"{combat.id.hex}:mechanic:{event.sequence}"
            if event.internal
            else f"{combat.id.hex}:{event.sequence}"
        ),
        event_type=event_type,
        actor_id=actor,
        target_ids=(event.target,) if event.target else (),
        action_id=action_id,
        action_instance_id=event.action_instance_id,
        actor_effect_ids=event.actor_effect_ids,
        prepared_action_instance_id=event.prepared_action_instance_id,
        response_to_prepared_action_instance_id=(
            event.response_to_prepared_action_instance_id
        ),
        dot_kind=event.dot_kind,
        dot_application_event_id=event.dot_application_event_id,
        dot_source_id=event.dot_source_id,
        hit_index=event.hit_index,
        hit_count=event.hit_count,
        protection_layers_before=event.protection_layers_before,
        protection_layers_after=event.protection_layers_after,
        target_state_tags=event.target_state_tags,
        target_effect_application_event_ids=event.target_effect_application_event_ids,
        applied_effect_id=event.effect_id,
        effect_application_event_id=event.effect_application_event_id,
        chain_state_before=event.chain_state_before,
        chain_state_after=event.chain_state_after,
        chain_prepared_by_action_id=event.chain_prepared_by_action_id,
        chain_consumed=event.chain_consumed,
        chain_empowered=event.chain_empowered,
        empowered_by_action_instance_id=event.empowered_by_action_instance_id,
        chain_prepared_by_action_instance_id=(
            event.chain_prepared_by_action_instance_id
        ),
        chain_consumed_by_action_instance_id=(
            event.chain_consumed_by_action_instance_id
        ),
        chain_window_before=event.chain_window_before,
        chain_window_after=event.chain_window_after,
        power_component=event.power_component,
        power_multiplier=event.power_multiplier,
        damage_power_multiplier=event.damage_power_multiplier,
        healing_power_multiplier=event.healing_power_multiplier,
        barrier_power_multiplier=event.barrier_power_multiplier,
        trigger_scope=event.trigger_scope,
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


def errante_conditions_for_event(
    stage: int,
    event: TrialCombatEvent,
    context: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Interpret persisted engine facts and return updated Errante trial context."""
    current = deepcopy(dict(context or {}))
    echo_id = ERRANTE_ENTITY_IDS.get(stage)
    condition = ERRANTE_CONDITION_IDS.get(stage)
    if echo_id is None or condition is None:
        return (), current

    if stage == 1:
        applications = set(current.get("bleed_application_event_ids", ()))
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id == ERRANTE_ART_IDS["ferida_profunda"]
            and event.target_ids == (echo_id,)
            and event.dot_kind == "bleed"
            and event.dot_application_event_id
        ):
            applications.add(event.dot_application_event_id)
            current["bleed_application_event_ids"] = sorted(applications)
        if (
            event.event_type == "dot_tick"
            and event.actor_id == "player"
            and event.dot_source_id == "player"
            and event.dot_kind == "bleed"
            and event.target_ids == (echo_id,)
            and event.dot_application_event_id in applications
        ):
            return (condition,), current

    elif stage == 2:
        prepared_ids = set(current.get("prepared_attack_instance_ids", ()))
        if (
            event.event_type == "prepared_action"
            and event.actor_id == echo_id
            and event.action_id == ERRANTE_PREPARED_ACTION_ID
            and event.prepared_action_instance_id
        ):
            prepared_ids.add(event.prepared_action_instance_id)
            current["prepared_attack_instance_ids"] = sorted(prepared_ids)
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id == ERRANTE_ART_IDS["passo_velado"]
            and event.target_ids == ("player",)
            and event.response_to_prepared_action_instance_id in prepared_ids
            and event.actor_effect_id == ERRANTE_STEP_EVASION_EFFECT_ID
            and event.action_instance_id
        ):
            current["passo_window_action_instance_id"] = event.action_instance_id
            current["passo_window_prepared_action_instance_id"] = (
                event.response_to_prepared_action_instance_id
            )
        window_action_id = current.get("passo_window_action_instance_id")
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id in {"attack", *ERRANTE_ART_IDS.values()}
            and event.action_instance_id != window_action_id
            and bool(window_action_id)
            and event.target_ids == (echo_id,)
            and event.effective_damage > 0
            and ERRANTE_STEP_WINDOW_EFFECT_ID in event.actor_effect_ids
        ):
            current.pop("passo_window_action_instance_id", None)
            current.pop("passo_window_prepared_action_instance_id", None)
            return (condition,), current

    elif stage == 3:
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id == ERRANTE_ART_IDS["golpe_oportuno"]
            and event.target_ids == (echo_id,)
            and ERRANTE_EXPOSED_EFFECT_ID in event.target_effect_ids
        ):
            return (condition,), current

    return (), current


def vigia_conditions_for_event(
    stage: int,
    event: TrialCombatEvent,
    context: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Evaluate Vigia pedagogy from combat facts captured at resolution time."""
    current = deepcopy(dict(context or {}))
    echo_id = VIGIA_ENTITY_IDS.get(stage)
    condition = VIGIA_CONDITION_IDS.get(stage)
    if echo_id is None or condition is None or event.event_type != "combat_action":
        return (), current
    conditions: list[str] = []
    if stage == 1:
        mark_application = current.get("mark_application_event_id")
        if (
            event.actor_id == "player"
            and event.action_id == VIGIA_ART_IDS["marca_da_presa"]
            and event.target_ids == (echo_id,)
            and event.effect_applied
            and event.applied_effect_id == VIGIA_MARK_EFFECT_ID
            and event.effect_application_event_id
        ):
            current["mark_application_event_id"] = event.effect_application_event_id
            mark_application = event.effect_application_event_id
        if (
            event.actor_id == "player"
            and event.action_id in {"attack", *VIGIA_ART_IDS.values()}
            and event.action_id != VIGIA_ART_IDS["olho_da_vigilia"]
            and event.target_ids == (echo_id,)
            and event.effective_damage > 0
            and VIGIA_MARK_EFFECT_ID in event.target_effect_ids
            and mark_application in event.target_effect_application_event_ids
        ):
            conditions.append(condition)
    elif stage == 2:
        if (
            event.actor_id == "player"
            and event.target_ids == (echo_id,)
            and not event.dodged
            and event.protection_layers_before > 0
            and event.protection_layers_after == 0
        ):
            conditions.append(condition)
    elif stage == 3:
        if (
            event.actor_id == "player"
            and event.action_id in set(VIGIA_ART_IDS.values())
            - {VIGIA_ART_IDS["olho_da_vigilia"]}
            and event.target_ids == (echo_id,)
            and event.effective_damage > 0
            and VIGIA_EXPOSED_TAG in event.target_state_tags
            and VIGIA_EYE_PER_EFFECT_ID in event.actor_effect_ids
            and VIGIA_EYE_CRIT_EFFECT_ID in event.actor_effect_ids
        ):
            conditions.append(condition)
    return tuple(conditions), current


def tecelao_conditions_for_event(
    stage: int,
    event: TrialCombatEvent,
    context: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Evaluate Tecelão pedagogy from correlated, server-observed combat events."""
    current = deepcopy(dict(context or {}))
    conditions: list[str] = []
    entity_ids = set(TECELAO_ENTITY_IDS.get(stage, ()))
    if not entity_ids:
        return (), current
    if stage == 1:
        principal_id = TECELAO_ENTITY_IDS[1][0]
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id == TECELAO_ART_IDS["chama_tecida"]
            and event.target_ids == (principal_id,)
            and event.dot_kind == "burn"
            and event.dot_application_event_id
        ):
            conditions.append(TECELAO_CONDITION_IDS[1][0])
    elif stage == 2:
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.action_id == TECELAO_ART_IDS["ruptura_da_trama"]
            and event.action_instance_id
            and event.target_ids
            and event.target_ids[0] in entity_ids
            and event.effective_damage > 0
            and not event.dodged
        ):
            by_action = dict(current.get("ruptura_targets_by_action", {}))
            targets = set(by_action.get(event.action_instance_id, ()))
            targets.add(event.target_ids[0])
            by_action[event.action_instance_id] = sorted(targets)
            current["ruptura_targets_by_action"] = by_action
            if len(targets) >= 2 and not current.get("ruptura_condition_satisfied"):
                current["ruptura_condition_satisfied"] = True
                conditions.append(TECELAO_CONDITION_IDS[2][0])
    elif stage == 3:
        if (
            event.event_type == "combat_action"
            and event.actor_id == "player"
            and event.chain_consumed
            and event.chain_empowered
            and event.action_id in set(TECELAO_ART_IDS.values())
            and event.chain_prepared_by_action_id
            and event.chain_prepared_by_action_id != event.action_id
            and event.power_multiplier == TECELAO_THREAD_BASE_POWER_BONUS + Decimal(1)
            and event.action_instance_id
        ):
            consumed = set(current.get("empowered_action_instance_ids", ()))
            consumed.add(event.action_instance_id)
            current["empowered_action_instance_ids"] = sorted(consumed)
            if len(consumed) >= 2 and not current.get("thread_condition_satisfied"):
                current["thread_condition_satisfied"] = True
                conditions.append(TECELAO_CONDITION_IDS[3][0])
        if (
            event.event_type == "combat_action"
            and event.actor_id in {TECELAO_ENTITY_IDS[3][0]}
            and event.action_id == "trial.tecelao.ruptura_anunciada"
            and event.prepared_resolution
            and event.target_ids == ("player",)
            and event.barrier_absorbed >= 1
            and event.target_barrier_source
            == f"player:{TECELAO_ART_IDS['veu_entrelacado']}"
        ):
            conditions.append(TECELAO_CONDITION_IDS[3][1])
    return tuple(dict.fromkeys(conditions)), current


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
        "pedagogic_context": {},
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
    result.prepared_action_instance_id = None
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
        fighter.next_direct_crit_bonus = Decimal(0)
        fighter.next_direct_crit_expires_opportunity = None
        fighter.next_direct_crit_effect_id = ""
        fighter.retaliation_activation_id = ""
        fighter.retaliation_source_type = ""
        fighter.retaliation_source_event_id = ""
        fighter.retaliation_source_actor_id = ""
        fighter.protection_layers = (
            entity_by_id[fighter.id].protection_layers if key != "player" else 0
        )
        fighter.protection_reduction_per_layer = (
            entity_by_id[fighter.id].protection_reduction_per_layer
            if key != "player" else Decimal(0)
        )
        fighter.training_state_tags = (
            entity_by_id[fighter.id].initial_state_tags if key != "player" else ()
        )
        fighter.tagged_direct_damage_reductions = (
            dict(entity_by_id[fighter.id].tagged_direct_damage_reductions)
            if key != "player" else {}
        )
        fighter.action_chains = {}
        if key == "player":
            fighter.hp = player_hp
        else:
            fighter.hp = entity_by_id[fighter.id].max_hp
    return result
