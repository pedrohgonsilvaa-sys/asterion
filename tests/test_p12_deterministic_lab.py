"""P12 laboratory with an explicit organic CAPTURE and cheap domain REPLAY.

CAPTURE is opt-in and uses a disposable PostgreSQL schema. REPLAY reads a safe,
hashed JSON checkpoint and never enters the campaign driver or database fixture.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import select

from asterion.domain.arts import DEVASTADOR_ART_IDS, SENTINEL_ART_IDS
from asterion.domain.combat import (
    Combat,
    Fighter,
    _damage_aura_reduction,
    act,
    action_target_ids,
    allowed_actions,
    combat_consumable_options,
    player_actions_for,
    use_combat_consumable,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats
from asterion.domain.consumables import ConsumableFamily, definition
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Character,
    Quest,
)

D = Decimal
P12_RNG_NAMESPACE = "asterion:p12:a2:combat-seed:"
P12_CHECKPOINT_FORMAT = "asterion-p12-combat-checkpoint"
P12_CHECKPOINT_VERSION = 1
P12_CAPTURE_COMMAND = (
    "$env:ASTERION_P12_MODE='capture'; $env:PYTHONIOENCODING='utf-8'; "
    ".venv/Scripts/python.exe -m pytest -q "
    "tests/test_p12_deterministic_lab.py -k p12_checkpoint_capture"
)
CONNECTIONS = ("connection_a", "connection_b", "connection_c")
ART_ID = DEVASTADOR_ART_IDS["ariete"]
GUARD_ART_ID = SENTINEL_ART_IDS["golpe_de_guarda"]
WALL_ART_ID = SENTINEL_ART_IDS["muralha_breve"]
P12_CAPTURED = "p12-checkpoint-captured"


class _CheckpointCaptured(Exception):
    pass


def _combat_id(seed: int):
    return uuid5(NAMESPACE_URL, f"{P12_RNG_NAMESPACE}{seed}")


def _snapshot_hash(state) -> str:
    payload = _canonical_json(encode(state))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_json(value) -> str:
    def encode_decimal(item):
        if isinstance(item, Decimal):
            return str(item)
        raise TypeError(f"Unsupported checkpoint JSON value: {type(item).__name__}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=encode_decimal,
    )


def _checkpoint_path() -> Path:
    configured = os.getenv("ASTERION_P12_CHECKPOINT_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "asterion-p12-lab" / "checkpoint.json"


def _report_directory() -> Path:
    configured = os.getenv("ASTERION_P12_REPORT_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return _checkpoint_path().parent / "reports"


def _current_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    return result.stdout.strip()


def _domain_fingerprints() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    sources = {
        "combat": root / "src/asterion/domain/combat.py",
        "combat_math": root / "src/asterion/domain/combat_math.py",
        "combat_codec": root / "src/asterion/infrastructure/db/combat_codec.py",
    }
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in sources.items()
    }


def _configure_capture_console() -> None:
    """Keep legacy playthrough progress output safe on Windows CP1252 consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def _checkpoint_digest(document: dict) -> str:
    unsigned = {key: value for key, value in document.items() if key != "sha256"}
    return hashlib.sha256(_canonical_json(unsigned).encode("utf-8")).hexdigest()


def _seal_checkpoint(document: dict) -> dict:
    sealed = dict(document)
    sealed.pop("sha256", None)
    sealed["sha256"] = _checkpoint_digest(sealed)
    return sealed


def _write_checkpoint(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(_canonical_json(document) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_checkpoint(path: Path):
    if not path.is_file():
        raise FileNotFoundError(
            f"P12 checkpoint not found at {path}. Run CAPTURE explicitly: {P12_CAPTURE_COMMAND}"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"P12 checkpoint is not readable JSON: {path}") from exc
    if not isinstance(document, dict) or document.get("format") != P12_CHECKPOINT_FORMAT:
        raise ValueError("Unsupported P12 checkpoint format; capture a fresh checkpoint")
    if document.get("format_version") != P12_CHECKPOINT_VERSION:
        raise ValueError(
            f"Unsupported P12 checkpoint format version {document.get('format_version')!r}; "
            "capture a fresh checkpoint"
        )
    captured_head = document.get("captured_git_head")
    if not isinstance(captured_head, str) or not re.fullmatch(r"[0-9a-f]{40}", captured_head):
        raise ValueError("P12 checkpoint has malformed Git provenance")
    stored_hash = document.get("sha256")
    if not isinstance(stored_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", stored_hash):
        raise ValueError("P12 checkpoint has no valid SHA-256; capture a fresh checkpoint")
    if not hmac.compare_digest(stored_hash, _checkpoint_digest(document)):
        raise ValueError("P12 checkpoint SHA-256 mismatch; the file may be incomplete or altered")
    if document.get("domain_ruleset") != CURRENT_COMBAT_RULESET:
        raise ValueError(
            f"P12 checkpoint ruleset {document.get('domain_ruleset')!r} is incompatible with "
            f"{CURRENT_COMBAT_RULESET!r}; capture a fresh checkpoint"
        )
    if document.get("domain_fingerprints") != _domain_fingerprints():
        raise ValueError(
            "P12 checkpoint combat/codec sources differ from the captured domain version; "
            "capture a fresh checkpoint"
        )
    combat_id = document.get("combat_id")
    version = document.get("combat_version")
    if not isinstance(combat_id, str) or not isinstance(version, int):
        raise ValueError("P12 checkpoint combat identity/version is malformed")
    try:
        from uuid import UUID

        state = decode(document["combat"], UUID(combat_id), document["domain_ruleset"], version)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("P12 checkpoint combat payload cannot be decoded") from exc
    if state.id.hex != combat_id.replace("-", ""):
        raise ValueError("P12 checkpoint combat identity does not match its payload")
    if state.ruleset != CURRENT_COMBAT_RULESET or state.version != version:
        raise ValueError("P12 checkpoint decoded with an incompatible domain version")
    if encode(state) != document.get("combat"):
        raise ValueError("P12 checkpoint codec round-trip changed its combat state")
    if state.result is not None or state.phase_id != "I" or state.rng_cursor != 0:
        raise ValueError("P12 checkpoint is not at the pre-action Matriarch start")
    if not set(CONNECTIONS).issubset(state.fighters):
        raise ValueError("P12 checkpoint is missing the Matriarch's Radicular Connections")
    if not isinstance(document.get("provenance"), dict):
        raise ValueError("P12 checkpoint provenance is missing")
    return document, state


def _active_connections(state) -> tuple[str, ...]:
    return tuple(key for key in CONNECTIONS if state.fighters[key].hp > 0)


def _effects(fighter) -> tuple[dict, ...]:
    return tuple(
        {
            "id": effect.id,
            "stat": effect.stat,
            "magnitude": str(effect.magnitude),
            "remaining": effect.remaining,
            "kind": effect.kind,
        }
        for effect in fighter.effects
        if effect.remaining > 0
    )


def _dots(state, fighter) -> tuple[dict, ...]:
    return tuple(
        {
            "kind": dot.kind,
            "stacks": dot.stacks,
            "remaining": dot.remaining,
            "source": dot.source,
        }
        for dot in state.dot_states.get(fighter.id, ())
        if dot.remaining > 0
    )


def _event_trace(event) -> dict:
    return {
        "round": event.round,
        "actor": event.actor,
        "action": event.action,
        "target": event.target,
        "calculated_damage": event.calculated_damage,
        "direct_damage": event.damage,
        "effective_damage": event.effective_damage,
        "barrier_absorbed": str(event.barrier_absorbed),
        "critical": event.critical,
        "dodged": event.dodged,
        "blocked": event.blocked,
        "defending": event.target_defending,
        "healed": str(event.healed),
        "dot_kind": event.dot_kind,
        "effect_id": event.effect_id,
        "effect_stat": event.applied_effect_stat,
        "effect_magnitude": str(event.applied_effect_magnitude),
        "effect_duration": event.applied_effect_duration,
        "prepared_resolution": event.prepared_resolution,
        "hit": f"{event.hit_index}/{event.hit_count}",
    }


def _compact_trace(trace: list[dict]) -> list[dict]:
    """Keep each decision auditable without repeating empty event fields."""
    compact = []
    for row in trace:
        events = []
        for event in row["events"]:
            events.append(
                {
                    key: value
                    for key, value in event.items()
                    if value not in (None, "", False, 0, "0")
                    or key in {
                        "round", "actor", "action", "target", "hit", "calculated_damage",
                        "direct_damage", "effective_damage", "barrier_absorbed", "critical",
                        "dodged", "blocked", "defending", "healed",
                    }
                }
            )
        mechanics = []
        for event in row["mechanic_events"]:
            mechanics.append(
                {
                    key: value
                    for key, value in event.items()
                    if value not in (None, "", False, 0, "0")
                    or key in {
                        "round", "actor", "action", "target", "hit", "calculated_damage",
                        "direct_damage", "effective_damage", "barrier_absorbed", "critical",
                        "dodged", "blocked", "defending", "healed",
                    }
                }
            )
        compact.append(
            {
                key: row[key]
                for key in (
                    "round", "opportunity", "action", "target", "reason", "legal",
                    "rejection", "hp_before", "hp_after", "barrier_before",
                    "barrier_after", "boss_hp_before", "boss_hp_after",
                    "boss_barrier_before", "boss_barrier_after", "phase_before", "phase_after",
                    "connections_before", "connections_after", "active_connections_before",
                    "active_connections_after", "aura_reduction_before",
                    "aura_reduction_after", "rng_cursor_before", "rng_cursor_after",
                    "cooldowns", "effects", "player_per", "dots", "boss_effects",
                    "boss_dots", "consumables_remaining", "prepared_action", "result",
                )
                if key in row
            }
            | {"events": events, "mechanic_events": mechanics}
        )
    return compact


def _estimated_damage(state, action: str, target_id: str, *, ignore_aura: bool = False) -> Decimal:
    """Conservative, RNG-free estimate used only by the adaptive policy."""
    action_def = player_actions_for(state).get(action)
    if action_def is None or action_def.coefficient <= 0:
        return D(0)
    attacker = state.fighters["player"]
    target = state.fighters[target_id]
    attack = attacker.stat("attack") * action_def.coefficient
    defense = target.stats.defense
    # The official direct-damage formula is used with no crit and no lucky hit.
    from asterion.domain.combat_math import direct_damage

    damage = D(
        direct_damage(
            attack,
            D(1),
            defense,
            attacker.level,
            penetration=attacker.stat("per"),
        )
    )
    if target_id == "enemy" and not ignore_aura:
        damage *= D(1) - _damage_aura_reduction(state, target_id)
    return damage


def _adaptive_connection_target(state) -> str | None:
    alive = _active_connections(state)
    if not alive:
        return None
    candidates = [
        action
        for action in allowed_actions(state)
        if action in player_actions_for(state)
        and player_actions_for(state)[action].coefficient > 0
    ]
    boss = state.fighters["enemy"]
    current_reduction = _damage_aura_reduction(state, "enemy")
    for connection_id in alive:
        best_boss_hit_with_connection = max(
            (_estimated_damage(state, action, "enemy") for action in candidates),
            default=D(0),
        )
        best_boss_hit_without_connection = max(
            (
                _estimated_damage(state, action, "enemy", ignore_aura=True)
                for action in candidates
            ),
            default=D(0),
        )
        best_connection_hit = max(
            (_estimated_damage(state, action, connection_id) for action in candidates),
            default=D(0),
        )
        if (
            best_boss_hit_with_connection <= 0
            or best_boss_hit_without_connection <= 0
            or best_connection_hit <= 0
        ):
            continue
        # Connections reduce the Matriarch's incoming final damage. Estimate
        # player actions saved by removing one 4% reduction, then compare that
        # with the attacks diverted to destroy the connection. This is an
        # RNG-free decision aid, not a claim about exact future crits or evades.
        after_reduction = max(D(0), current_reduction - D("0.04"))
        best_boss_hit_after = best_boss_hit_without_connection * (D(1) - after_reduction)
        actions_before = boss.hp / best_boss_hit_with_connection
        actions_after = boss.hp / best_boss_hit_after
        estimated_attacks_saved = actions_before - actions_after
        actions_to_destroy = state.fighters[connection_id].hp / best_connection_hit
        if estimated_attacks_saved > actions_to_destroy:
            return connection_id
    return None


def _choose_intent(state, *, connection_plan: str, defense_plan: str, stock: dict,
                   budget_limit: int) -> tuple[str, str | None, str | None]:
    available = allowed_actions(state)
    if not available:
        raise AssertionError("P12 lab found no legal player action")
    player = state.fighters["player"]
    hp_fraction = player.hp / player.stats.hp

    if state.prepared_action == "estrangulamento_vale" and "defend" in available:
        return "defend", None, None

    healing_ids = tuple(
        item_id
        for item_id, quantity in sorted(stock.items())
        if quantity > 0
        and (item := definition(item_id)) is not None
        and item.family == ConsumableFamily.HEALING
    )
    heal_threshold = {
        "cautious": D("0.60"),
        "barrier": D("0.50"),
        "aggressive": D("0.32"),
    }[defense_plan]
    heal_options = combat_consumable_options(
        state, healing_ids, budget_limit=budget_limit
    )
    if hp_fraction <= heal_threshold and heal_options:
        option = heal_options[0]
        return f"consumable:{option.item_id}", option.target_id, option.effect_id

    wall = WALL_ART_ID if WALL_ART_ID in available else None
    barrier_active = player.barrier > 0 and player.barrier_remaining != 0
    barrier_threshold = D("0.85") if defense_plan == "barrier" else D("0.50")
    if wall and not barrier_active and hp_fraction <= barrier_threshold:
        return wall, None, None

    ariete = ART_ID if ART_ID in available else None
    guard = GUARD_ART_ID if GUARD_ART_ID in available else None
    charge = player.path_state.get("devastador_charge")
    has_charge = isinstance(charge, dict) and player.opportunity <= int(
        charge.get("expires_opportunity", -1)
    )
    if ariete and (has_charge or hp_fraction >= D("0.45")):
        return ariete, None, None
    if guard and player.retaliation_charges > 0 and player.retaliation_remaining > 0:
        return guard, None, None
    if ariete:
        return ariete, None, None

    for candidate in (guard, "attack", "defend"):
        if candidate and candidate in available:
            return candidate, None, None
    return available[0], None, None


def _decision_reason(state, action: str, target_id: str | None, plan: str) -> str:
    if state.prepared_action == "estrangulamento_vale" and action == "defend":
        return "defender contra Estrangulamento telegrafado"
    if action.startswith("consumable:"):
        return "usar Cura quando o HP cruza o limiar da política defensiva"
    if action == WALL_ART_ID:
        return "repor Barreira sem sobrepor camada ativa"
    if target_id in CONNECTIONS:
        return f"plano {plan}: destruir Conexão opcional {target_id}"
    if plan == "E" and target_id == "enemy":
        return "plano adaptativo: custo estimado de Conexão supera dano futuro recuperado"
    if action == ART_ID:
        return "usar Aríete legal quando disponível"
    if action == GUARD_ART_ID:
        return "usar Golpe de Guarda, priorizando Retaliação válida quando ativa"
    if action == "defend":
        return "nenhuma ofensiva escolhida; ação defensiva permitida"
    return "ofensiva de alvo único contra a Matriarca"


def _target_for_action(state, action: str, *, plan: str, destroyed: set[str]) -> str | None:
    action_def = player_actions_for(state).get(action)
    if action_def is None or action_def.target_mode == "all_opponents":
        return None
    if action_def.target_mode != "opponent":
        return None
    if plan in {"B", "C", "D"}:
        needed = {"B": 1, "C": 2, "D": 3}[plan]
        active = tuple(key for key in _active_connections(state) if key not in destroyed)
        if len(destroyed) < needed and active:
            return min(active, key=lambda key: (state.fighters[key].hp, CONNECTIONS.index(key)))
    if plan == "E":
        active = tuple(key for key in _active_connections(state) if key not in destroyed)
        if active:
            target = _adaptive_connection_target(state)
            if target is not None:
                return target
    targets = action_target_ids(state, action)
    return "enemy" if "enemy" in targets else (targets[0] if targets else None)


def _simulate(initial, *, seed: int, connection_plan: str, defense_plan: str,
              stock: dict, budget_limit: int, max_actions: int = 400) -> dict:
    state = deepcopy(initial)
    state.id = _combat_id(seed)
    stock = dict(stock)
    sequence: list[dict] = []
    trace: list[dict] = []
    destroyed: set[str] = set()
    initial_boss_hp = state.fighters["enemy"].hp
    initial_player_hp = state.fighters["player"].hp
    boss_direct = D(0)
    boss_effective = D(0)
    boss_absorbed = D(0)
    connections_direct = D(0)
    connections_effective = D(0)
    connections_absorbed = D(0)
    incoming = D(0)
    player_absorbed = D(0)
    heals_used = 0

    for _ in range(max_actions):
        if state.result:
            break
        action, consumable_target, effect_id = _choose_intent(
            state,
            connection_plan=connection_plan,
            defense_plan=defense_plan,
            stock=stock,
            budget_limit=budget_limit,
        )
        is_consumable = action.startswith("consumable:")
        item_id = action.removeprefix("consumable:") if is_consumable else None
        target_id = (
            consumable_target
            if is_consumable
            else _target_for_action(
                state, action, plan=connection_plan, destroyed=destroyed
            )
        )
        valid_targets = action_target_ids(state, action) if not is_consumable else ()
        if not is_consumable and target_id is not None and target_id not in valid_targets:
            raise AssertionError(f"Lab policy selected illegal target {target_id!r} for {action!r}")

        before_player = state.fighters["player"]
        before_boss = state.fighters["enemy"]
        before_connections = {key: state.fighters[key].hp for key in CONNECTIONS}
        before_rng_cursor = state.rng_cursor
        event_start = len(state.events)
        mechanic_start = len(state.mechanic_events)
        intent = {
            "round": state.round,
            "opportunity": before_player.opportunity,
            "action": action,
            "target": target_id,
            "reason": _decision_reason(state, action, target_id, connection_plan),
            "legal": True,
            "hp_before": str(before_player.hp),
            "barrier_before": str(before_player.barrier),
            "boss_hp_before": str(before_boss.hp),
            "boss_barrier_before": str(before_boss.barrier),
            "phase_before": state.phase_id,
            "connections_before": {key: str(value) for key, value in before_connections.items()},
            "active_connections_before": len(_active_connections(state)),
            "aura_reduction_before": str(_damage_aura_reduction(state, "enemy")),
            "rng_cursor_before": before_rng_cursor,
        }
        sequence.append({
            "action": action,
            "target_id": target_id,
            "consumable_id": item_id,
            "effect_id": effect_id,
        })
        if is_consumable:
            updated = use_combat_consumable(
                state,
                item_id,
                target_id=target_id,
                effect_id=effect_id,
                budget_limit=budget_limit,
            )
            if updated.version == state.version:
                intent["legal"] = False
                intent["rejection"] = "consumable rejected by production domain"
                raise AssertionError(intent)
            stock[item_id] -= 1
            heals_used += 1
        else:
            updated = act(state, action, target_id=target_id)
            if updated.version == state.version:
                intent["legal"] = False
                intent["rejection"] = "action rejected by production domain"
                raise AssertionError(intent)

        added_events = updated.events[event_start:]
        added_mechanics = updated.mechanic_events[mechanic_start:]
        for event in added_events:
            if event.actor == "player":
                if event.target == "enemy":
                    boss_direct += D(event.damage)
                    boss_effective += D(event.effective_damage)
                    boss_absorbed += D(event.barrier_absorbed)
                elif event.target in CONNECTIONS:
                    connections_direct += D(event.damage)
                    connections_effective += D(event.effective_damage)
                    connections_absorbed += D(event.barrier_absorbed)
            if event.target == "player":
                if event.effective_damage > 0:
                    incoming += D(event.effective_damage)
                player_absorbed += D(event.barrier_absorbed)
        for key in CONNECTIONS:
            if before_connections[key] > 0 and updated.fighters[key].hp <= 0:
                destroyed.add(key)
        player = updated.fighters["player"]
        boss = updated.fighters["enemy"]
        connection_after = {key: updated.fighters[key].hp for key in CONNECTIONS}
        trace.append({
            **intent,
            "hp_after": str(player.hp),
            "barrier_after": str(player.barrier),
            "boss_hp_after": str(boss.hp),
            "boss_barrier_after": str(boss.barrier),
            "phase_after": updated.phase_id,
            "connections_after": {key: str(value) for key, value in connection_after.items()},
            "active_connections_after": len(_active_connections(updated)),
            "aura_reduction_after": str(_damage_aura_reduction(updated, "enemy")),
            "rng_cursor_after": updated.rng_cursor,
            "cooldowns": {
                key: value - player.opportunity
                for key, value in sorted(player.cooldowns.items())
                if value > player.opportunity
            },
            "effects": _effects(player),
            "player_per": str(player.stat("per")),
            "dots": _dots(updated, player),
            "boss_effects": _effects(boss),
            "boss_dots": _dots(updated, boss),
            "consumables_remaining": dict(sorted(stock.items())),
            "prepared_action": updated.prepared_action,
            "events": tuple(_event_trace(event) for event in added_events),
            "mechanic_events": tuple(_event_trace(event) for event in added_mechanics),
            "result": updated.result,
        })
        state = updated
    else:
        raise AssertionError(f"P12 simulation exceeded {max_actions} player actions")

    return {
        "seed": seed,
        "connection_plan": connection_plan,
        "defense_plan": defense_plan,
        "result": state.result,
        "rounds": state.round,
        "player_actions": len(sequence),
        "phase_reached": state.phase_id,
        "initial_player_hp": str(initial_player_hp),
        "player_hp_remaining": str(state.fighters["player"].hp),
        "player_damage_received": str(incoming),
        "damage_absorbed": str(player_absorbed),
        "player_barrier_absorbed": str(player_absorbed),
        "heals_used": heals_used,
        "initial_boss_hp": str(initial_boss_hp),
        "boss_hp_remaining": str(state.fighters["enemy"].hp),
        "boss_damage_dealt": str(boss_effective),
        "boss_direct_damage": str(boss_direct),
        "boss_barrier_absorbed": str(boss_absorbed),
        "connection_damage_dealt": str(connections_effective),
        "connection_direct_damage": str(connections_direct),
        "connection_barrier_absorbed": str(connections_absorbed),
        "boss_net_hp_removed": str(initial_boss_hp - state.fighters["enemy"].hp),
        "connections_destroyed": tuple(sorted(destroyed)),
        "connection_hp_remaining": {
            key: str(state.fighters[key].hp) for key in CONNECTIONS
        },
        "active_connections": len(_active_connections(state)),
        "aura_reduction": str(_damage_aura_reduction(state, "enemy")),
        "telegraph": state.prepared_action,
        "defeat_cause": (
            "player_hp_zero"
            if state.result == "defeat" and state.fighters["player"].hp <= 0
            else None
        ),
        "sequence": sequence,
        "trace": trace,
        "final_state": state,
    }


def _public_sequence_entry(view, entry, missions, actor):
    state = view.combat
    if entry["consumable_id"]:
        return missions.action_combat(
            actor,
            view.activity_id,
            state.version,
            consumable_id=entry["consumable_id"],
            target_id=entry["target_id"],
            effect_id=entry["effect_id"],
        )
    return missions.action_combat(
        actor,
        view.activity_id,
        state.version,
        entry["action"],
        target_id=entry["target_id"],
    )


@pytest.mark.skipif(
    os.getenv("ASTERION_P12_MODE", "").casefold() != "capture",
    reason="organic P1-P12 capture is long and runs only with ASTERION_P12_MODE=capture",
)
@pytest.mark.asyncio
async def test_p12_checkpoint_capture(database, monkeypatch):
    """Capture the legal P12 pre-action state once through public campaign services."""
    _configure_capture_console()
    import asterion.application.campaign_coop as campaign_coop
    import asterion.application.vde_missions as vde_module
    import tests.test_vde_full_playthrough as journey
    from asterion.application.active_arts import (
        ActiveArtMutationCode,
        ActiveArtMutationRejected,
        ActiveArtService,
    )
    from asterion.application.talents import TalentService
    from asterion.infrastructure.db.models import ConsumableStack
    actor_box: dict[str, int] = {}
    capture: dict = {}
    seed_box = {"seed": 0}
    original_start = journey.VDEMissionService.start_solo_combat
    original_resume = journey.VDEMissionService.resume
    original_equipper = journey._equip_best_available_combat_gear
    original_profile = vde_module.create_campaign_boss_profile
    original_equip_art = ActiveArtService.equip_art

    async def seeded_campaign_profile(*args, **kwargs):
        state = await original_profile(*args, **kwargs)
        # The initial initiative and opening resolution are built from one
        # stable base ID. Swap only the CombatRng key before it is persisted,
        # matching the clones whose combat IDs vary by seed.
        state.id = _combat_id(seed_box["seed"])
        return state

    monkeypatch.setattr(vde_module, "create_campaign_boss_profile", seeded_campaign_profile)

    async def equip_best_with_melee_fallback(sessions, actor):
        changed = await original_equipper(sessions, actor)
        # The A1 organic journey already uses this public fallback when the
        # best owned weapon is incompatible with Aríete.
        from asterion.application.equipment import EquipmentService
        from asterion.application.weapon_metadata import (
            equipped_weapon_compatibility_tags,
            resolve_equipment_weapon,
        )
        from asterion.infrastructure.db.models import EquipmentItem

        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor,
                    Character.server_id == "ocaso",
                )
            )
            assert character is not None
            tags = await equipped_weapon_compatibility_tags(session, character.id)
            if "weapon.compat.melee" in tags:
                return changed
            candidates = []
            for item in await session.scalars(
                select(EquipmentItem).where(EquipmentItem.character_id == character.id)
            ):
                if item.slot != "Principal" or item.item_level > character.level:
                    continue
                weapon = await resolve_equipment_weapon(session, item)
                if weapon is not None and "weapon.compat.melee" in weapon.compatibility_tags:
                    candidates.append((item.item_level, str(item.id), item.id, item.item_name))
            assert candidates, "Organic P12 preparation needs a legitimately owned melee weapon"
            _level, _key, item_id, item_name = max(candidates)
            version = character.combat_configuration_version
        result = await EquipmentService(sessions, "ocaso").equip_item(
            actor, item_id, expected_configuration_version=version
        )
        assert result is not None and result.changed
        return (*changed, ("Principal", item_name, "melee compatible"))

    async def resume_with_public_talents(self, actor, quest_id):
        view = await original_resume(self, actor, quest_id)
        if quest_id == journey.P12_ID and view is not None and view.status == "active":
            talents = TalentService(self.sessions, self.server_id)
            current = await talents.view(actor)
            assert current is not None and current.level >= 20
            for talent_id in (
                "talent.sentinela.ponta_revidada",
                "talent.sentinela.guarda_preparada",
            ):
                if current.available_points <= 0 or talent_id in {
                    choice.talent_id for choice in current.choices
                }:
                    continue
                result = await talents.acquire(
                    actor, talent_id, current.combat_configuration_version
                )
                assert result is not None and result.changed
                current = result.view
        return view

    async def equip_art_from_clean_loadout(
        self, actor, slot, art_id, *, expected_configuration_version=None
    ):
        try:
            return await original_equip_art(
                self,
                actor,
                slot,
                art_id,
                expected_configuration_version=expected_configuration_version,
            )
        except ActiveArtMutationRejected as exc:
            if exc.code != ActiveArtMutationCode.INVALID_CURRENT_CONFIGURATION:
                raise
            # A legitimate equipment upgrade can invalidate an old loadout.
            # Clear those slots through the public service before applying S6's
            # already-published legal loadout, matching the UI recovery path.
            current = await self.view(actor)
            assert current is not None
            removed = []
            for active_slot in tuple(current.slots):
                result = await self.unequip_slot(
                    actor,
                    active_slot.slot,
                    expected_configuration_version=current.combat_configuration_version,
                )
                assert result is not None and result.changed
                removed.append(active_slot.slot)
                current = await self.view(actor)
                assert current is not None
            capture.setdefault("configuration_setup_repairs", []).append(
                {
                    "service": "ActiveArtService.unequip_slot",
                    "slots_cleared": removed,
                    "reason": "old arts incompatible after legitimate equipment upgrade",
                }
            )
            return await original_equip_art(
                self,
                actor,
                slot,
                art_id,
                expected_configuration_version=current.combat_configuration_version,
            )

    async def capture_p12_start(self, actor, quest_id, version):
        if quest_id != journey.P12_ID or capture.get("view") is not None:
            return await original_start(self, actor, quest_id, version)
        actor_box["actor"] = actor
        seed_box["seed"] = 0
        monkeypatch.setattr(campaign_coop, "uuid4", lambda: _combat_id(0))
        # Capture the driver's currently selected, service-validated setup.
        # Changing Arts here could make a different persisted configuration
        # than the one whose public version the caller is about to commit.
        view = await original_start(self, actor, quest_id, version)
        assert view is not None and view.kind == "combat" and view.combat is not None
        assert view.progress.get("activity_id")
        assert view.combat.result is None
        assert view.combat.events == []
        assert view.combat.rng_cursor == 0
        assert view.combat.phase_id == "I"
        capture.update({
            "view": view,
            "checkpoint_hash": _snapshot_hash(view.combat),
            "preparation": await journey._p12_preparation_snapshot(self.sessions, actor),
            "seed": 0,
        })
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(
                    Character.telegram_id == actor,
                    Character.server_id == self.server_id,
                )
            )
            quests = (
                await session.execute(
                    select(Quest.quest_id, Quest.status, Quest.step)
                    .where(Quest.character_id == character.id)
                    .order_by(Quest.quest_id)
                )
            ).all()
            stocks = (
                await session.execute(
                    select(ConsumableStack.consumable_id, ConsumableStack.quantity)
                    .where(
                        ConsumableStack.character_id == character.id,
                        ConsumableStack.quantity > 0,
                    )
                    .order_by(ConsumableStack.consumable_id)
                )
            ).all()
            capture["provenance"] = {
                "capture_method": (
                    "organic test driver through public campaign, equipment, talent, "
                    "and P12 activity services"
                ),
                "campaign_attestation": (
                    "The organic driver completed P1-P11 and S12 before P12 combat; "
                    "no quest, XP, reward, or equipment progress was seeded."
                ),
                "configuration_setup_repairs": capture.get(
                    "configuration_setup_repairs", []
                ),
                "race": character.race,
                "class": character.character_class,
                "level": character.level,
                "xp": character.xp,
                "hp": str(character.hp),
                "max_hp": str(character.max_hp),
                "location": view.location,
                "quest_progress": [list(row) for row in quests],
                "equipment": capture["preparation"]["equipment"],
                "consumable_stock": [
                    [key, int(quantity)] for key, quantity in stocks
                ],
                "consumable_budget_limit": view.consumable_budget_limit,
                "combat_id": str(view.combat.id),
                "combat_checkpoint_hash": capture["checkpoint_hash"],
                "arts": tuple(
                    entry.art_id
                    for entry in sorted(
                        (view.combat.configuration_snapshot or {}).get("active_arts", ()),
                        key=lambda item: item["slot"],
                    )
                ),
                "talents": tuple(view.combat.fighters["player"].talent_ids),
                "path": view.combat.fighters["player"].selected_path,
                "combat_stats": {
                    key: str(value)
                    for key, value in (
                        ("HP", view.combat.fighters["player"].stats.hp),
                        ("ATQ", view.combat.fighters["player"].stats.attack),
                        ("DEF", view.combat.fighters["player"].stats.defense),
                        ("AGI", view.combat.fighters["player"].stats.agility),
                        ("PER", view.combat.fighters["player"].stats.per),
                        ("CRIT", view.combat.fighters["player"].stats.crit),
                    )
                },
                "rng": {
                    "seed": seed_box["seed"],
                    "source": "CombatRng derives rolls from combat_id and rng_cursor",
                    "cursor_at_capture": view.combat.rng_cursor,
                },
            }
        raise _CheckpointCaptured(P12_CAPTURED)

    monkeypatch.setattr(
        journey,
        "_equip_best_available_combat_gear",
        equip_best_with_melee_fallback,
    )
    monkeypatch.setattr(journey.VDEMissionService, "resume", resume_with_public_talents)
    monkeypatch.setattr(journey.VDEMissionService, "start_solo_combat", capture_p12_start)
    monkeypatch.setattr(ActiveArtService, "equip_art", equip_art_from_clean_loadout)

    checkpoint_path = _checkpoint_path()
    if checkpoint_path.exists() and os.getenv("ASTERION_P12_OVERWRITE_CHECKPOINT") != "1":
        pytest.fail(
            f"Refusing to replace existing checkpoint {checkpoint_path}; "
            "set ASTERION_P12_OVERWRITE_CHECKPOINT=1 only for an intentional recapture"
        )
    started = time.perf_counter()
    try:
        await journey.test_vde_full_playthrough_from_fresh_tdo_exit(database, monkeypatch)
    except _CheckpointCaptured as captured_error:
        assert str(captured_error) == P12_CAPTURED
    else:
        pytest.fail("The organic journey did not reach the first P12 combat creation")
    journey_seconds = time.perf_counter() - started

    checkpoint = capture["view"]
    initial = checkpoint.combat
    assert initial is not None
    assert checkpoint.status == "active" and checkpoint.step == 5
    assert checkpoint.location == "Berço da Matriarca"
    assert capture["preparation"]["level"] == 20
    assert len(capture["preparation"]["arts"]) == 3
    assert capture["provenance"]["xp"] >= 0
    assert capture["provenance"]["quest_progress"]
    assert capture["provenance"]["combat_checkpoint_hash"] == _snapshot_hash(initial)
    # A PostgreSQL reload of the still-active snapshot is an actual persistence
    # round trip, not a manually reconstructed fixture.
    resumed = await journey.VDEMissionService(database[1], "ocaso").resume_active(
        actor_box["actor"]
    )
    assert resumed is not None and resumed.combat == initial
    assert _snapshot_hash(resumed.combat) == capture["checkpoint_hash"]

    document = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION,
            "captured_git_head": _current_head(),
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "capture_elapsed_seconds": round(journey_seconds, 2),
            "domain_ruleset": initial.ruleset,
            "domain_fingerprints": _domain_fingerprints(),
            "combat_id": str(initial.id),
            "combat_version": initial.version,
            "combat": encode(initial),
            "provenance": capture["provenance"],
        }
    )
    _write_checkpoint(checkpoint_path, document)
    loaded_document, reconstructed = _load_checkpoint(checkpoint_path)
    assert loaded_document["sha256"] == document["sha256"]
    assert encode(reconstructed) == encode(initial)
    assert reconstructed == initial
    print(
        "P12_CHECKPOINT_CAPTURED="
        + json.dumps(
            {
                "path": str(checkpoint_path),
                "sha256": document["sha256"],
                "capture_seconds": round(journey_seconds, 2),
                "level": capture["provenance"]["level"],
                "class": capture["provenance"]["class"],
                "path_name": capture["provenance"]["path"],
                "domain_ruleset": initial.ruleset,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return


def _median_decimal(values) -> str:
    ordered = sorted(D(str(value)) for value in values)
    middle = len(ordered) // 2
    value = (
        ordered[middle]
        if len(ordered) % 2
        else (ordered[middle - 1] + ordered[middle]) / D(2)
    )
    return str(value.quantize(D("0.01")))


def _run_metrics(result: dict) -> dict:
    return {
        key: result[key]
        for key in (
            "seed",
            "connection_plan",
            "defense_plan",
            "result",
            "rounds",
            "phase_reached",
            "player_hp_remaining",
            "player_damage_received",
            "player_barrier_absorbed",
            "heals_used",
            "boss_hp_remaining",
            "boss_damage_dealt",
            "boss_direct_damage",
            "boss_barrier_absorbed",
            "connection_damage_dealt",
            "connection_direct_damage",
            "connection_barrier_absorbed",
            "connections_destroyed",
            "connection_hp_remaining",
            "active_connections",
            "aura_reduction",
            "defeat_cause",
        )
    }


def _best_run_key(result: dict):
    return (
        result["result"] != "victory",
        D(result["boss_hp_remaining"]),
        -D(result["player_hp_remaining"]),
        result["rounds"],
        result["seed"],
    )


def _save_matrix_report(report: dict, checkpoint_hash: str) -> tuple[Path, Path]:
    directory = _report_directory()
    directory.mkdir(parents=True, exist_ok=True)
    report["report_sha256"] = hashlib.sha256(
        _canonical_json(report).encode("utf-8")
    ).hexdigest()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    paths = (
        directory / f"matrix-{checkpoint_hash[:12]}-{stamp}.json",
        directory / "latest-report.json",
    )
    for path in paths:
        temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temporary.write_text(_canonical_json(report) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    return paths


@pytest.mark.skipif(
    os.getenv("ASTERION_P12_MODE", "").casefold() != "replay",
    reason="P12 strategy replay runs only with ASTERION_P12_MODE=replay",
)
def test_p12_checkpoint_replay_matrix():
    """Replay ten A-E cases from JSON; this test has no DB fixture or journey call."""
    checkpoint_path = _checkpoint_path()
    document, initial = _load_checkpoint(checkpoint_path)
    initial_hash = _snapshot_hash(initial)
    provenance = document["provenance"]
    stock = {
        item_id: int(quantity)
        for item_id, quantity in provenance["consumable_stock"]
    }
    budget_limit = int(provenance["consumable_budget_limit"])
    plans = ("A", "B", "C", "D", "E")
    seeds = (0, 1)
    names = {
        "A": "focus Matriarch",
        "B": "destroy one Connection then Matriarch",
        "C": "destroy two Connections then Matriarch",
        "D": "destroy three Connections then Matriarch",
        "E": "adaptive Connection opportunity-cost policy",
    }
    results = []
    started = time.perf_counter()
    for plan in plans:
        for seed in seeds:
            results.append(
                _simulate(
                    initial,
                    seed=seed,
                    connection_plan=plan,
                    defense_plan="cautious",
                    stock=stock,
                    budget_limit=budget_limit,
                )
            )
    matrix_seconds = time.perf_counter() - started

    # Cheap repeat verifies deterministic replay separately from the ten-case matrix.
    repeated_a = _simulate(
        initial,
        seed=0,
        connection_plan="A",
        defense_plan="cautious",
        stock=stock,
        budget_limit=budget_limit,
    )
    repeated_b = _simulate(
        initial,
        seed=0,
        connection_plan="A",
        defense_plan="cautious",
        stock=stock,
        budget_limit=budget_limit,
    )
    assert repeated_a["sequence"] == repeated_b["sequence"]
    assert repeated_a["trace"] == repeated_b["trace"]
    assert _run_metrics(repeated_a) == _run_metrics(repeated_b)
    assert _snapshot_hash(initial) == initial_hash, "a simulation mutated the checkpoint"

    # Verify the encoded phase, active connection set, and whole state survive codec reload.
    decoded = decode(
        document["combat"],
        initial.id,
        document["domain_ruleset"],
        document["combat_version"],
    )
    assert decoded.phase_id == "I"
    assert _active_connections(decoded) == _active_connections(initial)
    assert _snapshot_hash(decoded) == initial_hash

    strategy_summaries = []
    for plan in plans:
        cohort = [item for item in results if item["connection_plan"] == plan]
        best = min(cohort, key=_best_run_key)
        strategy_summaries.append(
            {
                "strategy": plan,
                "strategy_name": names[plan],
                "defense_policy": "cautious",
                "seeds": list(seeds),
                "simulations": len(cohort),
                "victories": sum(item["result"] == "victory" for item in cohort),
                "defeats": sum(item["result"] == "defeat" for item in cohort),
                "medians": {
                    "matriarch_damage": _median_decimal(
                        item["boss_damage_dealt"] for item in cohort
                    ),
                    "matriarch_hp_remaining": _median_decimal(
                        item["boss_hp_remaining"] for item in cohort
                    ),
                    "connection_damage": _median_decimal(
                        item["connection_damage_dealt"] for item in cohort
                    ),
                    "player_barrier_absorbed": _median_decimal(
                        item["player_barrier_absorbed"] for item in cohort
                    ),
                    "rounds": _median_decimal(item["rounds"] for item in cohort),
                    "consumables_used": _median_decimal(
                        item["heals_used"] for item in cohort
                    ),
                    "connections_destroyed": _median_decimal(
                        len(item["connections_destroyed"]) for item in cohort
                    ),
                },
                "best_execution": {
                    **_run_metrics(best),
                    "sequence": best["sequence"],
                    "turn_trace": _compact_trace(best["trace"]),
                },
            }
        )

    victories = sum(item["result"] == "victory" for item in results)
    report = {
        "format": "asterion-p12-strategy-matrix",
        "format_version": 1,
        "checkpoint_sha256": document["sha256"],
        "checkpoint_captured_git_head": document["captured_git_head"],
        "replay_git_head": _current_head(),
        "domain_ruleset": document["domain_ruleset"],
        "build": {
            key: provenance[key]
            for key in (
                "race",
                "class",
                "path",
                "level",
                "location",
                "equipment",
                "talents",
                "arts",
                "combat_stats",
            )
        },
        "rng": provenance["rng"],
        "mode": "domain REPLAY; no campaign journey, public service, or PostgreSQL",
        "defense_policy": "cautious",
        "strategy_definitions": names,
        "seeds": list(seeds),
        "matrix_simulations": len(results),
        "additional_determinism_replays": 2,
        "determinism_verified": True,
        "victories": victories,
        "defeats": len(results) - victories,
        "classification": "VICTORY_CONFIRMED" if victories else "INCONCLUSIVE",
        "matrix_runtime_seconds": round(matrix_seconds, 4),
        "strategy_summaries": strategy_summaries,
        "runs": [_run_metrics(item) for item in results],
    }
    report_paths = _save_matrix_report(report, document["sha256"])
    print(
        "P12_REPLAY_MATRIX="
        + json.dumps(
            {
                "checkpoint_sha256": document["sha256"],
                "matrix_simulations": len(results),
                "additional_determinism_replays": 2,
                "victories": victories,
                "classification": report["classification"],
                "matrix_runtime_seconds": report["matrix_runtime_seconds"],
                "report": str(report_paths[0]),
                "latest_report": str(report_paths[1]),
                "strategies": [
                    {
                        "strategy": summary["strategy"],
                        "victories": summary["victories"],
                        "best_matriarch_hp": summary["best_execution"][
                            "boss_hp_remaining"
                        ],
                        "best_seed": summary["best_execution"]["seed"],
                    }
                    for summary in strategy_summaries
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )


def test_p12_checkpoint_hash_is_stable_and_tampering_is_rejected(tmp_path):
    assert _canonical_json({"value": D("1.20")}) == '{"value":"1.20"}'
    document = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION,
            "captured_git_head": "0" * 40,
            "domain_ruleset": CURRENT_COMBAT_RULESET,
            "combat_id": str(_combat_id(0)),
            "combat_version": 1,
            "combat": {},
            "provenance": {},
        }
    )
    assert document["sha256"] == _checkpoint_digest(document)
    path = tmp_path / "tampered.json"
    _write_checkpoint(path, document)
    changed = json.loads(path.read_text(encoding="utf-8"))
    changed["combat_version"] = 2
    _write_checkpoint(path, changed)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _load_checkpoint(path)


def test_p12_checkpoint_json_codec_round_trip_preserves_phase_and_connections(tmp_path):
    stats = CombatStats(D(100), D(20), D(12), D(10))
    fighters = {
        key: Fighter(
            id=key,
            name=key,
            level=20,
            stats=stats,
            hp=D(100),
            side="player" if key == "player" else "enemy",
        )
        for key in ("player", "enemy", *CONNECTIONS)
    }
    combat = Combat(
        id=_combat_id(5),
        ruleset=CURRENT_COMBAT_RULESET,
        fighters=fighters,
        player_actions={},
        enemy_actions={},
        ai_cycle=(),
        phase_id="I",
    )
    document = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION,
            "captured_git_head": _current_head(),
            "domain_ruleset": CURRENT_COMBAT_RULESET,
            "domain_fingerprints": _domain_fingerprints(),
            "combat_id": str(combat.id),
            "combat_version": combat.version,
            "combat": encode(combat),
            "provenance": {"consumable_stock": [], "consumable_budget_limit": 3},
        }
    )
    path = tmp_path / "round-trip.json"
    _write_checkpoint(path, document)
    loaded, rebuilt = _load_checkpoint(path)
    assert loaded["sha256"] == document["sha256"]
    assert rebuilt == combat
    assert rebuilt.phase_id == "I"
    assert _active_connections(rebuilt) == CONNECTIONS


def test_p12_checkpoint_rejects_missing_and_incompatible_versions(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError, match="CAPTURE explicitly"):
        _load_checkpoint(missing)
    obsolete = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION,
            "captured_git_head": "0" * 40,
            "domain_ruleset": "obsolete-ruleset",
            "combat_id": str(_combat_id(0)),
            "combat_version": 1,
            "combat": {},
            "provenance": {},
        }
    )
    path = tmp_path / "obsolete.json"
    _write_checkpoint(path, obsolete)
    with pytest.raises(ValueError, match="incompatible"):
        _load_checkpoint(path)
    stale_domain = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION,
            "captured_git_head": "0" * 40,
            "domain_ruleset": CURRENT_COMBAT_RULESET,
            "domain_fingerprints": {},
            "combat_id": str(_combat_id(0)),
            "combat_version": 1,
            "combat": {},
            "provenance": {},
        }
    )
    _write_checkpoint(path, stale_domain)
    with pytest.raises(ValueError, match="sources differ"):
        _load_checkpoint(path)


def test_p12_checkpoint_rejects_unsupported_format_version(tmp_path):
    document = _seal_checkpoint(
        {
            "format": P12_CHECKPOINT_FORMAT,
            "format_version": P12_CHECKPOINT_VERSION + 1,
            "captured_git_head": "0" * 40,
            "domain_ruleset": CURRENT_COMBAT_RULESET,
            "combat_id": str(_combat_id(0)),
            "combat_version": 1,
            "combat": {},
            "provenance": {},
        }
    )
    path = tmp_path / "unsupported.json"
    _write_checkpoint(path, document)
    with pytest.raises(ValueError, match="format version"):
        _load_checkpoint(path)
