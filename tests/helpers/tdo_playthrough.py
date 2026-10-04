"""Reusable, persistence-backed player driver for TDO full-playthrough tests.

The driver deliberately mutates game state only through application services. Its
database access is read-only and exists to capture milestone diagnostics.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from asterion.domain.combat import allowed_actions
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    CharacterActiveArtSlot,
    CharacterEquipmentSlot,
    CharacterProfession,
    CharacterTalentChoice,
    ClassTrialState,
    ConsumableStack,
    DungeonRun,
    DungeonRunMember,
    EquipmentItem,
    GameActivity,
    HuntContext,
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
                unacknowledged_hunts = (
                    await session.execute(
                        select(HuntContext.game_activity_id, GameActivity.status)
                        .join(GameActivity, GameActivity.id == HuntContext.game_activity_id)
                        .where(
                            HuntContext.character_id == character.id,
                            GameActivity.status.in_(("completed", "failed")),
                            HuntContext.result_acknowledged.is_(False),
                        )
                        .order_by(GameActivity.id)
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
                        .order_by(GameActivity.id)
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
                state = {
                    "name": character.name,
                    "level": character.level,
                    "xp": character.xp,
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
                    "braziers": list(brazier_ids),
                    "unlocks": list(unlock_ids),
                    "foreground": [
                        (activity.id.hex, activity.content_id, activity.state_version)
                        for activity in active_activities
                    ],
                    "unacknowledged_hunt_results": [
                        (activity_id.hex, status) for activity_id, status in unacknowledged_hunts
                    ],
                    "hunt_results": [
                        (activity_id.hex, status, acknowledged)
                        for activity_id, status, acknowledged in hunt_results
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
            action = self.combat_action(combat)
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
