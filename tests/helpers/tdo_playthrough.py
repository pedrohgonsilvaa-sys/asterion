"""Reusable, persistence-backed player driver for TDO full-playthrough tests.

The driver deliberately mutates game state only through application services. Its
database access is read-only and exists to capture milestone diagnostics.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from asterion.application.progression import level_xp
from asterion.domain.combat import allowed_actions
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    CharacterProfession,
    CharacterTalentChoice,
    ClassTrialState,
    CombatRecord,
    ConsumableStack,
    DungeonRun,
    DungeonRunMember,
    Encounter,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    HuntRound,
    MaterialStack,
    Quest,
    Unlock,
    WorldState,
)


@dataclass(frozen=True)
class JourneyMark:
    label: str
    state: dict[str, Any]


@dataclass
class TDOPlaythrough:
    actor: int
    sessions: async_sessionmaker
    marks: list[JourneyMark] = field(default_factory=list)
    level_milestones: list[dict[str, Any]] = field(default_factory=list)
    xp_by_origin: dict[str, int] = field(default_factory=dict)
    _last_total_xp: int | None = None
    _last_level: int | None = None
    _last_level_milestone_xp_total: int | None = None

    @staticmethod
    def _xp_origin(label: str) -> str:
        normalized = label.casefold()
        if "prólogo" in normalized or "prologo" in normalized:
            return "Prólogo"
        if "desbravar" in normalized or "explore" in normalized:
            return "Desbravar"
        if "cripta" in normalized or "galerias" in normalized or "masmorra" in normalized:
            return "Masmorra"
        if "ronda" in normalized:
            return "Ronda"
        if "caçada" in normalized or "cacada" in normalized or "hunt" in normalized:
            return "Caçada"
        if any(f"p{number}" in normalized for number in range(1, 7)):
            return "P1–P6"
        if any(f"s{number}" in normalized for number in range(1, 7)):
            return "S1–S6"
        return "Bestiário/outros"

    @staticmethod
    def total_xp(level: int, residual_xp: int) -> int:
        """Derive received XP from level thresholds and the current residual."""
        return sum(level_xp(value) for value in range(1, level)) + residual_xp

    async def snapshot(self, label: str) -> JourneyMark:
        """Read a compact persisted-state diagnostic; this method never writes."""
        async with self.sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == self.actor)
            )
            if character is None:
                state: dict[str, Any] = {"character": None}
            else:
                world = await session.get(WorldState, character.id)
                quests = (
                    await session.scalars(
                        select(Quest)
                        .where(Quest.character_id == character.id)
                        .order_by(Quest.quest_id)
                    )
                ).all()
                materials = (
                    await session.scalars(
                        select(MaterialStack)
                        .where(MaterialStack.character_id == character.id)
                        .order_by(MaterialStack.material_id, MaterialStack.bound)
                    )
                ).all()
                consumables = (
                    await session.scalars(
                        select(ConsumableStack)
                        .where(ConsumableStack.character_id == character.id)
                        .order_by(ConsumableStack.consumable_id)
                    )
                ).all()
                equipment = (
                    await session.execute(
                        select(CharacterEquipmentSlot.slot, EquipmentItem)
                        .join(
                            EquipmentItem,
                            EquipmentItem.id == CharacterEquipmentSlot.equipment_item_id,
                        )
                        .where(CharacterEquipmentSlot.character_id == character.id)
                        .order_by(CharacterEquipmentSlot.slot)
                    )
                ).all()
                equipment_owned = (
                    await session.scalars(
                        select(EquipmentItem)
                        .where(EquipmentItem.character_id == character.id)
                        .order_by(
                            EquipmentItem.slot,
                            EquipmentItem.item_level.desc(),
                            EquipmentItem.id,
                        )
                    )
                ).all()
                brazier_ids = (
                    await session.scalars(
                        select(Brazier.brazier_id)
                        .where(Brazier.character_id == character.id)
                        .order_by(Brazier.brazier_id)
                    )
                ).all()
                unlock_ids = (
                    await session.scalars(
                        select(Unlock.unlock_id)
                        .where(Unlock.character_id == character.id)
                        .order_by(Unlock.unlock_id)
                    )
                ).all()
                active_activities = (
                    await session.scalars(
                        select(GameActivity)
                        .where(
                            GameActivity.character_id == character.id,
                            GameActivity.status == "active",
                        )
                    )
                ).all()
                active_combat_rows = (
                    await session.execute(
                        select(
                            GameActivity.id,
                            GameActivity.content_id,
                            GameActivity.state_version,
                            CombatRecord.snapshot,
                        )
                        .join(Encounter, Encounter.game_activity_id == GameActivity.id)
                        .join(CombatRecord, CombatRecord.encounter_id == Encounter.id)
                        .where(
                            GameActivity.character_id == character.id,
                            GameActivity.status == "active",
                        )
                    )
                ).all()
                unacknowledged_hunts = (
                    await session.execute(
                        select(HuntContext.game_activity_id, GameActivity.status)
                        .join(GameActivity, GameActivity.id == HuntContext.game_activity_id)
                        .where(
                            HuntContext.character_id == character.id,
                            GameActivity.status.in_(("completed", "failed")),
                            HuntContext.result_acknowledged.is_(False),
                        )
                        .order_by(
                            GameActivity.last_valid_action_at,
                            GameActivity.id,
                        )
                    )
                ).all()
                hunt_results = (
                    await session.execute(
                        select(
                            HuntContext.game_activity_id,
                            GameActivity.status,
                            HuntContext.result_acknowledged,
                        )
                        .join(GameActivity, GameActivity.id == HuntContext.game_activity_id)
                        .where(
                            HuntContext.character_id == character.id,
                            GameActivity.status.in_(("completed", "failed")),
                        )
                        .order_by(
                            GameActivity.last_valid_action_at,
                            GameActivity.id,
                        )
                    )
                ).all()
                talents = (
                    await session.execute(
                        select(
                            CharacterTalentChoice.point_slot,
                            CharacterTalentChoice.talent_id,
                        )
                        .where(CharacterTalentChoice.character_id == character.id)
                        .order_by(CharacterTalentChoice.point_slot)
                    )
                ).all()
                arts = (
                    await session.execute(
                        select(CharacterActiveArtSlot.slot, CharacterActiveArtSlot.art_id)
                        .where(CharacterActiveArtSlot.character_id == character.id)
                        .order_by(CharacterActiveArtSlot.slot)
                    )
                ).all()
                professions = (
                    await session.execute(
                        select(
                            CharacterProfession.slot,
                            CharacterProfession.profession_id,
                            CharacterProfession.level,
                            CharacterProfession.pxp,
                        )
                        .where(CharacterProfession.character_id == character.id)
                        .order_by(CharacterProfession.slot)
                    )
                ).all()
                trial = await session.get(ClassTrialState, character.id)
                run = await session.scalar(
                    select(DungeonRun)
                    .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
                    .where(
                        DungeonRunMember.character_id == character.id,
                        DungeonRun.status == "active",
                    )
                )
                exploration_count = int(
                    await session.scalar(
                        select(func.count(ExplorationAttempt.id)).where(
                            ExplorationAttempt.character_id == character.id
                        )
                    )
                    or 0
                )
                completed_explorations = int(
                    await session.scalar(
                        select(func.count(ExplorationAttempt.id)).where(
                            ExplorationAttempt.character_id == character.id,
                            ExplorationAttempt.status == "completed",
                        )
                    )
                    or 0
                )
                manual_hunts = int(
                    await session.scalar(
                        select(func.count(HuntContext.game_activity_id))
                        .join(GameActivity, GameActivity.id == HuntContext.game_activity_id)
                        .where(
                            HuntContext.character_id == character.id,
                            GameActivity.content_id == "road_manual_hunt",
                        )
                    )
                    or 0
                )
                rounds = (
                    await session.execute(
                        select(HuntRound.status, func.count(HuntRound.id))
                        .where(HuntRound.character_id == character.id)
                        .group_by(HuntRound.status)
                    )
                ).all()
                dungeon_runs = (
                    await session.execute(
                        select(
                            DungeonRun.dungeon_family_id,
                            DungeonRun.status,
                            func.count(DungeonRun.id),
                        )
                        .join(DungeonRunMember, DungeonRunMember.run_id == DungeonRun.id)
                        .where(DungeonRunMember.character_id == character.id)
                        .group_by(DungeonRun.dungeon_family_id, DungeonRun.status)
                    )
                ).all()
                cumulative_xp = sum(
                    level_xp(level) for level in range(1, character.level)
                ) + character.xp
                xp_since_snapshot = (
                    0 if self._last_total_xp is None else cumulative_xp - self._last_total_xp
                )
                state = {
                    "name": character.name,
                    "level": character.level,
                    "xp": character.xp,
                    "xp_required_next_level": (
                        level_xp(character.level) if character.level < 60 else 0
                    ),
                    "xp_received_total": cumulative_xp,
                    "xp_received_since_previous_snapshot": xp_since_snapshot,
                    "crowns": character.crowns,
                    "vigor": character.vigor,
                    "hp": str(character.hp),
                    "max_hp": str(character.max_hp),
                    "location": world.location if world else None,
                    "quests": [
                        {
                            "id": quest.quest_id,
                            "status": quest.status,
                            "step": quest.step,
                            "progress": quest.progress,
                        }
                        for quest in quests
                    ],
                    "materials": [
                        (row.material_id, row.quantity, row.bound) for row in materials
                    ],
                    "consumables": [
                        (row.consumable_id, row.quantity) for row in consumables
                    ],
                    "equipped": [
                        (
                            slot,
                            item.id.hex,
                            item.item_name,
                            item.rarity,
                            item.item_level,
                            item.payload,
                        )
                        for slot, item in equipment
                    ],
                    "equipment_inventory": [
                        (
                            item.id.hex,
                            item.item_name,
                            item.rarity,
                            item.slot,
                            item.item_level,
                            any(equipped_item.id == item.id for _, equipped_item in equipment),
                        )
                        for item in equipment_owned
                    ],
                    "braziers": list(brazier_ids),
                    "unlocks": list(unlock_ids),
                    "foreground": [
                        (activity.id.hex, activity.content_id, activity.state_version)
                        for activity in active_activities
                    ],
                    "foreground_combat": [
                        {
                            "activity_id": activity_id.hex,
                            "content_id": content_id,
                            "state_version": state_version,
                            "result": snapshot.get("result"),
                            "turn_index": snapshot.get("turn_index"),
                            "order": snapshot.get("order"),
                            "fighters": {
                                fighter_id: fighter.get("hp")
                                for fighter_id, fighter in snapshot.get("fighters", {}).items()
                            },
                        }
                        for activity_id, content_id, state_version, snapshot in active_combat_rows
                    ],
                    "unacknowledged_hunt_results": [
                        (activity_id.hex, status) for activity_id, status in unacknowledged_hunts
                    ],
                    "hunt_results": [
                        (activity_id.hex, status, acknowledged)
                        for activity_id, status, acknowledged in hunt_results[-5:]
                    ],
                    "hunt_result_count": len(hunt_results),
                    "manual_hunt_count": manual_hunts,
                    "rounds": dict(rounds),
                    "exploration_count": exploration_count,
                    "completed_explorations": completed_explorations,
                    "dungeon_runs": [
                        (family_id, status, count)
                        for family_id, status, count in dungeon_runs
                    ],
                    "talents": list(talents),
                    "path": character.selected_path,
                    "active_arts": list(arts),
                    "professions": list(professions),
                    "trial": (
                        {
                            "status": trial.status,
                            "stage": trial.current_stage,
                            "completed_stages": trial.completed_stages,
                        }
                        if trial
                        else None
                    ),
                    "dungeon_run": (
                        {
                            "id": run.id.hex,
                            "family": run.dungeon_family_id,
                            "difficulty": run.difficulty,
                            "encounter": run.current_encounter_ordinal,
                            "state_version": run.state_version,
                        }
                        if run
                        else None
                    ),
                }
                if self._last_total_xp is not None:
                    xp_delta = max(0, cumulative_xp - self._last_total_xp)
                    if xp_delta:
                        origin = self._xp_origin(label)
                        self.xp_by_origin[origin] = (
                            self.xp_by_origin.get(origin, 0) + xp_delta
                        )
                if self._last_level is None:
                    self._last_level_milestone_xp_total = cumulative_xp
                elif character.level > self._last_level:
                    previous_total = self._last_level_milestone_xp_total or 0
                    for level in range(self._last_level + 1, character.level + 1):
                        threshold = sum(level_xp(item) for item in range(1, level))
                        milestone_total = (
                            cumulative_xp if level == character.level else threshold
                        )
                        self.level_milestones.append(
                            {
                                "level": level,
                                "xp_residual": character.xp if level == character.level else 0,
                                "xp_required_next": (
                                    level_xp(level) if level < 60 else 0
                                ),
                                "xp_received_since_previous_milestone": max(
                                    0, milestone_total - previous_total
                                ),
                                "xp_received_total": milestone_total,
                                "crowns": character.crowns,
                                "vigor": character.vigor,
                                "hp": str(character.hp),
                                "max_hp": str(character.max_hp),
                                "location": world.location if world else None,
                                "explorations": exploration_count,
                                "dungeon_runs": [
                                    (family_id, status, count)
                                    for family_id, status, count in dungeon_runs
                                ],
                                "manual_hunts": manual_hunts,
                                "rounds": dict(rounds),
                            }
                        )
                        previous_total = milestone_total
                    self._last_level_milestone_xp_total = cumulative_xp
                self._last_total_xp = cumulative_xp
                self._last_level = character.level
        mark = JourneyMark(label, state)
        self.marks.append(mark)
        return mark

    def diagnostic(self) -> str:
        if not self.marks:
            return "Nenhum marco persistido foi capturado."
        return "\n".join(
            f"{mark.label}: {mark.state!r}" for mark in self.marks[-8:]
        )
    @staticmethod
    def combat_action(combat) -> str:
        """Choose only an action currently offered by the canonical combat engine."""
        available = allowed_actions(combat)
        if not available:
            raise AssertionError(
                f"Combate sem ação elegível na janela do jogador: {combat!r}"
            )
        if combat.prepared_action is not None and "defend" in available:
            return "defend"
        arts = [
            action
            for action in available
            if action.startswith("class_art.") or action.startswith("path_art.")
        ]
        if arts:
            return arts[0]
        if "art" in available:
            return "art"
        if "attack" in available:
            return "attack"
        return available[0]

    async def combat_to_result(
        self,
        view,
        mutate: Callable[[Any, str], Awaitable[Any]],
        resume: Callable[[], Awaitable[Any]],
        *,
        label: str,
        max_actions: int = 400,
        action_picker: Callable[[Any], str] | None = None,
        trace_actions: bool = False,
    ):
        """Play a real combat and reconnect after the first committed action."""
        if view is None or getattr(view, "combat", None) is None:
            raise AssertionError(f"{label}: não iniciou um combate jogável\n{self.diagnostic()}")
        initial_ids = self.combat_ids(view)
        current = view
        reconnected = False
        for _ in range(max_actions):
            combat = getattr(current, "combat", None)
            if combat is None or combat.result is not None:
                return current
            action = (
                action_picker(current)
                if action_picker is not None
                else self.combat_action(combat)
            )
            if trace_actions:
                player = combat.fighters.get("player")
                enemies = tuple(
                    (fighter.name, str(fighter.hp), str(fighter.stats.hp))
                    for key, fighter in combat.fighters.items()
                    if key != "player" and fighter.hp > 0
                )
                print(
                    f"{label} · ação {_ + 1}: {action}; "
                    f"HP jogador={player.hp}/{player.stats.hp if player else '?'}; "
                    f"inimigos={enemies}; preparado={combat.prepared_action}",
                    flush=True,
                )
            updated = await mutate(current, action)
            if updated is None:
                raise AssertionError(
                    f"{label}: serviço rejeitou ação {action!r}\n{self.diagnostic()}"
                )
            next_combat = getattr(updated, "combat", None)
            if next_combat is not None and next_combat.version == combat.version:
                raise AssertionError(
                    f"{label}: ação {action!r} não avançou combate; "
                    f"oferecidas={allowed_actions(combat)!r}\n"
                    f"{self.diagnostic()}"
                )
            current = updated
            if (
                not reconnected
                and next_combat is not None
                and next_combat.result is None
            ):
                restored = await resume()
                if restored is None or self.combat_ids(restored) != initial_ids:
                    raise AssertionError(
                        f"{label}: reconnect não retomou a mesma atividade/Encounter; "
                        f"esperado={initial_ids!r}, atual={self.combat_ids(restored)!r}\n"
                        f"{self.diagnostic()}"
                    )
                restored_combat = getattr(restored, "combat", None)
                current_combat = getattr(current, "combat", None)
                if restored_combat != current_combat:
                    raise AssertionError(
                        f"{label}: snapshot mudou ao reconectar\n{self.diagnostic()}"
                    )
                current = restored
                reconnected = True
            if next_combat is None or next_combat.result is not None:
                return current
        raise AssertionError(f"{label}: excedeu {max_actions} ações reais\n{self.diagnostic()}")

    @staticmethod
    def combat_ids(view) -> tuple[str | None, ...]:
        if view is None:
            return (None,)
        return tuple(
            str(value) if value is not None else None
            for value in (
                getattr(view, "run_id", None),
                getattr(view, "attempt_id", None),
                getattr(view, "activity_id", None),
                getattr(view, "encounter_id", None),
                getattr(view, "combat_id", None),
            )
        )
