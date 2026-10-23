"""Opt-in P12 laboratory: one organic checkpoint, many deterministic simulations.

Run with ASTERION_RUN_P12_DETERMINISTIC_LAB=1 and a disposable PostgreSQL URL.
The campaign journey is deliberately executed once. All strategy comparisons
after checkpoint capture operate on deep copies through the production domain
combat functions and never write synthetic progress to the database.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from copy import deepcopy
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest
from sqlalchemy import func, select

from asterion.application.road import RoadService
from asterion.domain.arts import DEVASTADOR_ART_IDS, SENTINEL_ART_IDS
from asterion.domain.combat import (
    _damage_aura_reduction,
    act,
    action_target_ids,
    allowed_actions,
    combat_consumable_options,
    player_actions_for,
    use_combat_consumable,
)
from asterion.domain.consumables import ConsumableFamily, definition
from asterion.infrastructure.db.combat_codec import encode
from asterion.infrastructure.db.models import (
    Character,
    Quest,
)

D = Decimal
P12_RNG_NAMESPACE = "asterion:p12:a2:combat-seed:"
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
    payload = json.dumps(encode(state), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
                    "boss_barrier_after", "phase_before", "phase_after",
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
    outgoing = D(0)
    incoming = D(0)
    absorbed = D(0)
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
            if event.actor == "player" and event.effective_damage > 0:
                outgoing += D(event.effective_damage)
            if event.target == "player" and event.effective_damage > 0:
                incoming += D(event.effective_damage)
                absorbed += D(event.barrier_absorbed)
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
        "damage_absorbed": str(absorbed),
        "heals_used": heals_used,
        "initial_boss_hp": str(initial_boss_hp),
        "boss_hp_remaining": str(state.fighters["enemy"].hp),
        "boss_damage_dealt": str(outgoing),
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
    os.getenv("ASTERION_RUN_P12_DETERMINISTIC_LAB") != "1",
    reason="P12 lab runs one long organic journey; enable explicitly",
)
@pytest.mark.asyncio
async def test_p12_deterministic_lab_from_one_organic_checkpoint(database, monkeypatch):
    """Capture one legal P12 checkpoint then compare cloned deterministic fights."""
    import asterion.application.campaign_coop as campaign_coop
    import asterion.application.vde_missions as vde_module
    import tests.test_vde_full_playthrough as journey
    from asterion.application.talents import TalentService
    from asterion.infrastructure.db.models import ConsumableStack, RewardEvent
    actor_box: dict[str, int] = {}
    capture: dict = {}
    seed_box = {"seed": 0}
    original_start = journey.VDEMissionService.start_solo_combat
    original_resume = journey.VDEMissionService.resume
    original_equipper = journey._equip_best_available_combat_gear
    original_profile = vde_module.create_campaign_boss_profile

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
                "character_id": str(character.id),
                "name": character.name,
                "race": character.race,
                "class": character.character_class,
                "level": character.level,
                "xp": character.xp,
                "hp": character.hp,
                "max_hp": character.max_hp,
                "crowns": character.crowns,
                "location": view.location,
                "quests": tuple(tuple(row) for row in quests),
                "stocks": tuple((key, int(quantity)) for key, quantity in stocks),
                "combat_id": str(view.combat.id),
                "combat_checkpoint_hash": capture["checkpoint_hash"],
                "active_arts": tuple(
                    entry.art_id
                    for entry in sorted(
                        (view.combat.configuration_snapshot or {}).get("active_arts", ()),
                        key=lambda item: item["slot"],
                    )
                ),
                "talents": tuple(view.combat.fighters["player"].talent_ids),
                "path": view.combat.fighters["player"].selected_path,
                "fight_stats": {
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
            }
        raise _CheckpointCaptured(P12_CAPTURED)

    monkeypatch.setattr(
        journey,
        "_equip_best_available_combat_gear",
        equip_best_with_melee_fallback,
    )
    monkeypatch.setattr(journey.VDEMissionService, "resume", resume_with_public_talents)
    monkeypatch.setattr(journey.VDEMissionService, "start_solo_combat", capture_p12_start)

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
    assert capture["provenance"]["quests"]
    assert capture["provenance"]["combat_checkpoint_hash"] == _snapshot_hash(initial)
    print(
        "P12_A2_CHECKPOINT="
        + json.dumps(
            {"journey_seconds": round(journey_seconds, 2), **capture["provenance"]},
            ensure_ascii=False,
            default=str,
            sort_keys=True,
        ),
        flush=True,
    )

    # A PostgreSQL reload of the still-active snapshot is an actual persistence
    # round trip, not a manually reconstructed fixture.
    resumed = await journey.VDEMissionService(database[1], "ocaso").resume_active(
        actor_box["actor"]
    )
    assert resumed is not None and resumed.combat == initial
    assert _snapshot_hash(resumed.combat) == capture["checkpoint_hash"]

    stock = {key: int(quantity) for key, quantity in checkpoint.consumable_quantities}
    heal_stock = {
        item_id: quantity
        for item_id, quantity in stock.items()
        if (item := definition(item_id)) is not None and item.family == ConsumableFamily.HEALING
    }
    assert sum(heal_stock.values()) >= 1
    budget = checkpoint.consumable_budget_limit
    assert budget == 3

    plans = ("A", "B", "C", "D", "E")
    defenses = ("cautious", "barrier", "aggressive")
    seeds = tuple(range(12))
    results: list[dict] = []
    detailed_trace: dict[str, list[dict]] = {}
    for plan in plans:
        detailed_trace[plan] = _simulate(
            initial,
            seed=0,
            connection_plan=plan,
            defense_plan="cautious",
            stock=stock,
            budget_limit=budget,
        )["trace"]
        for defense in defenses:
            for seed in seeds:
                result = _simulate(
                    initial,
                    seed=seed,
                    connection_plan=plan,
                    defense_plan=defense,
                    stock=stock,
                    budget_limit=budget,
                )
                results.append(result)

    # Repetition of same input + seed + decisions must be byte-stable.
    repeat_a = _simulate(
        initial,
        seed=7,
        connection_plan="C",
        defense_plan="barrier",
        stock=stock,
        budget_limit=budget,
    )
    repeat_b = _simulate(
        initial,
        seed=7,
        connection_plan="C",
        defense_plan="barrier",
        stock=stock,
        budget_limit=budget,
    )
    assert repeat_a["sequence"] == repeat_b["sequence"]
    assert repeat_a["trace"] == repeat_b["trace"]
    assert {
        key: value
        for key, value in repeat_a.items()
        if key not in {"final_state", "trace", "sequence"}
    } == {
        key: value
        for key, value in repeat_b.items()
        if key not in {"final_state", "trace", "sequence"}
    }

    def _average_decimal(values):
        values = tuple(D(str(value)) for value in values)
        return str((sum(values, D(0)) / D(len(values))).quantize(D("0.01")))

    summaries = []
    for plan in plans:
        for defense in defenses:
            cohort = [
                result
                for result in results
                if result["connection_plan"] == plan and result["defense_plan"] == defense
            ]
            summaries.append(
                {
                    "connection_plan": plan,
                    "defense_plan": defense,
                    "seeds": len(cohort),
                    "victories": sum(
                        result["result"] == "victory" for result in cohort
                    ),
                    "average_boss_damage": _average_decimal(
                        result["boss_damage_dealt"] for result in cohort
                    ),
                    "best_boss_hp_remaining": min(
                        D(result["boss_hp_remaining"]) for result in cohort
                    ),
                    "average_rounds": _average_decimal(
                        result["rounds"] for result in cohort
                    ),
                    "average_player_damage": _average_decimal(
                        result["player_damage_received"] for result in cohort
                    ),
                    "average_heals": _average_decimal(
                        result["heals_used"] for result in cohort
                    ),
                    "average_connections_destroyed": _average_decimal(
                        len(result["connections_destroyed"]) for result in cohort
                    ),
                }
            )
    print(
        "P12_A2_STRATEGY_MATRIX="
        + json.dumps(summaries, ensure_ascii=False, default=str, sort_keys=True),
        flush=True,
    )
    print(
        "P12_A2_TRACE_SEED_0="
        + json.dumps(
            {plan: _compact_trace(trace) for plan, trace in detailed_trace.items()},
            ensure_ascii=False,
            default=str,
            sort_keys=True,
        ),
        flush=True,
    )

    winners = [result for result in results if result["result"] == "victory"]
    if winners:
        winner = sorted(
            winners,
            key=lambda result: (
                result["seed"] != 0,
                result["rounds"],
                -D(result["player_hp_remaining"]),
            ),
        )[0]
        missions = journey.VDEMissionService(database[1], "ocaso")
        if winner["seed"] != 0:
            # Persist the deterministic seed-0 loss through the public action
            # service to open an ordinary retry. This path spends no consumables.
            baseline_loss = _simulate(
                initial,
                seed=0,
                connection_plan="A",
                defense_plan="aggressive",
                stock={},
                budget_limit=budget,
            )
            if baseline_loss["result"] == "victory":
                winner = baseline_loss
                live = resumed
            else:
                assert baseline_loss["result"] == "defeat", (
                    "A seed-0 non-winning setup must end in defeat before retry"
                )
                live = resumed
                for entry in baseline_loss["sequence"]:
                    live = await _public_sequence_entry(
                        live, entry, missions, actor_box["actor"]
                    )
                retry_view = await missions.resume(actor_box["actor"], journey.P12_ID)
                assert retry_view is not None and retry_view.progress.get("awaiting_retry")
                road = RoadService(database[1], "ocaso")
                await journey._move_to(road, actor_box["actor"], journey.VDE_VIGILIA)
                await journey._craft_vde_p12_retry_consumables(
                    journey.CraftingService(database[1], "ocaso"), actor_box["actor"]
                )
                await journey._move_to(road, actor_box["actor"], journey.VDE_BERCO)
                retry_view = await missions.resume(actor_box["actor"], journey.P12_ID)
                assert retry_view is not None
                seed_box["seed"] = winner["seed"]
                live = await missions.start_solo_combat(
                    actor_box["actor"], journey.P12_ID, retry_view.state_version
                )
                assert live is not None and live.combat is not None
                assert live.combat.id == _combat_id(winner["seed"])
                assert _snapshot_hash(live.combat) == capture["checkpoint_hash"]
        else:
            live = resumed
        last_callback = None
        for entry in winner["sequence"]:
            if live.combat is None:
                break
            last_callback = (live, entry)
            live = await _public_sequence_entry(live, entry, missions, actor_box["actor"])
            if live.combat is None or live.combat.result is not None:
                break
        assert live is not None and live.kind == "examine_center", (
            f"Pure-domain candidate failed through public service: {live!r}"
        )
        assert last_callback is not None
        repeated = await _public_sequence_entry(
            last_callback[0], last_callback[1], missions, actor_box["actor"]
        )
        assert repeated is not None and repeated.kind == "examine_center"
        p12 = await missions.advance(
            actor_box["actor"], journey.P12_ID, live.state_version, "examine_center"
        )
        p12 = await missions.advance(
            actor_box["actor"], journey.P12_ID, p12.state_version, "register"
        )
        assert p12.status == "completed" and p12.kind == "choice"
        completed = await missions.choose_p12_reward(actor_box["actor"], p12.state_version, "2")
        assert completed is not None and completed.kind == "completed"
        await missions.choose_p12_reward(
            actor_box["actor"], p12.state_version, "2"
        )
        async with database[1]() as session:
            nucleus_events = await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == checkpoint.character_id,
                    RewardEvent.source_id == journey.P12_NUCLEUS_SOURCE,
                )
            )
            assert nucleus_events is not None
            nucleus_count = await session.scalar(
                select(func.count())
                .select_from(RewardEvent)
                .where(
                    RewardEvent.character_id == checkpoint.character_id,
                    RewardEvent.source_id == journey.P12_NUCLEUS_SOURCE,
                )
            )
            assert nucleus_count == 1
            choice_reward_count = await session.scalar(
                select(func.count())
                .select_from(RewardEvent)
                .where(
                    RewardEvent.character_id == checkpoint.character_id,
                    RewardEvent.source_id.like(f"{journey.P12_REWARD_SOURCE}:%"),
                )
            )
            assert choice_reward_count == 1
        reloaded = await journey.VDEMissionService(database[1], "ocaso").resume(
            actor_box["actor"], journey.P12_ID
        )
        assert reloaded is not None and reloaded.status == "completed"
        print(
            "P12_A2_VICTORY_CONFIRMED="
            + json.dumps(
                {
                    "seed": winner["seed"],
                    "connection_plan": winner["connection_plan"],
                    "defense_plan": winner["defense_plan"],
                    "sequence": winner["sequence"],
                    "boss_hp_remaining_simulated": winner["boss_hp_remaining"],
                    "player_hp_remaining_simulated": winner["player_hp_remaining"],
                    "quest_completed": completed.status,
                    "nucleus_reward": str(nucleus_events),
                    "nucleus_reward_count": nucleus_count,
                    "choice_reward_count": choice_reward_count,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
    else:
        best = sorted(
            results,
            key=lambda result: (
                D(result["boss_hp_remaining"]),
                -D(result["player_hp_remaining"]),
                result["rounds"],
            ),
        )[0]
        print(
            "P12_A2_NO_VICTORY_IN_SEARCH="
            + json.dumps(
                {
                    "classification": "INCONCLUSIVE",
                    "trials": len(results),
                    "best": {
                        key: best[key]
                        for key in (
                            "seed", "connection_plan", "defense_plan", "rounds",
                            "phase_reached", "boss_hp_remaining", "boss_damage_dealt",
                            "player_hp_remaining", "player_damage_received",
                            "damage_absorbed", "heals_used", "connections_destroyed",
                            "active_connections", "aura_reduction", "defeat_cause",
                        )
                    },
                },
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            ),
            flush=True,
        )

    # The entire journey and checkpoint remained in the disposable DB schema;
    # this lab does not assert that a bounded strategy search proves impossibility.
