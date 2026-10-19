"""Persistent secondary quest S32: A Casa que Não Chegou."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asterion.application.altos_missions import (
    P32_CONTENT_VERSION,
    P32_ID,
    S32_ID,
    AltosMissionService,
)
from asterion.application.campaign_objectives import (
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.progression import consolidate_character_level
from asterion.application.road import (
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.infrastructure.db.models import (
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)

S32_MISSION_ID = "mission.confins.s32"
S32_TITLE = "A Casa que Não Chegou"
S32_CONTENT_VERSION = "confins-1.0.0"
S32_REWARD_SOURCE = S32_MISSION_ID
S32_CODEX_ENTRY = "codex.confins.casa_presente_ausente"
S32_CODEX_FRAGMENT = "mission.confins.s32.casa_presente_ausente"
S32_EXPLORATION_FRAGMENT = "explore.confins.estradas.memoria_fundacao"
S32_COMPLETION_UNLOCK = "quest.confins.s32.completed"
S32_LEVEL = 54
S32_XP_REWARD = 59_465
S32_CROWNS_REWARD = 680
S32_COURO_MARCHA = "material.confins.couro_marcha"
S32_MUSGO_LIMIAR = "material.confins.musgo_limiar"
S32_FOUNDATION_ELEMENTS = (
    "evidence.confins.s32.foundation_element_a",
    "evidence.confins.s32.foundation_element_b",
    "evidence.confins.s32.foundation_element_c",
)
S32_DOCUMENT_CARDS = (
    "evidence.confins.s32.document_card_presence",
    "evidence.confins.s32.document_card_absence",
)

_FOUNDATION_ACTIONS = {
    "recognize_foundation_a": S32_FOUNDATION_ELEMENTS[0],
    "recognize_foundation_b": S32_FOUNDATION_ELEMENTS[1],
    "recognize_foundation_c": S32_FOUNDATION_ELEMENTS[2],
}
_CARD_ACTIONS = {
    "recover_presence_card": S32_DOCUMENT_CARDS[0],
    "recover_absence_card": S32_DOCUMENT_CARDS[1],
}


@dataclass(frozen=True, slots=True)
class S32View:
    character_id: UUID
    kind: str
    status: str
    step: int
    state_version: int
    progress: dict
    location: str
    level: int
    available: bool = False
    reacceptable: bool = False
    tracked: bool = False
    action_available: bool = False
    gate_satisfied: bool = False
    foundation_elements: tuple[str, ...] = ()
    document_cards: tuple[str, ...] = ()
    victory_recorded: bool = False
    codex_owned: bool = False
    codex_recorded: bool = False
    exploration_fragment_owned: bool = False


class S32Service:
    """Per-character S32 state, shared evidence, Codex fragments, and one-time reward."""

    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        server_id: str,
        altos_missions: AltosMissionService,
    ) -> None:
        self.sessions = sessions
        self.server_id = server_id
        self.altos_missions = altos_missions

    async def giver(self, actor: int) -> S32View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_refuge(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "giver")

    async def offer(self, actor: int) -> S32View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            world = await self._world(session, character.id)
            if not self._at_refuge(world):
                return None
            quest = await self._quest(session, character.id)
            return await self._view(session, character, quest, world, "offer")

    async def summary(self, actor: int) -> S32View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None and not self._at_refuge(world):
                return None
            return await self._view(session, character, quest, world, "summary")

    async def resume(self, actor: int) -> S32View | object | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None:
                return None
            quest = await self._quest(session, character.id)
            if quest is None:
                return None
            active_combat = await self._active_combat(session, character.id)
            world = await self._world(session, character.id)
            if active_combat is not None:
                return await self.altos_missions.resume(actor, S32_ID)
            return await self._view(session, character, quest, world, "detail")

    async def resume_active(self, actor: int) -> S32View | object | None:
        view = await self.resume(actor)
        return view if view is not None and view.status == "active" else None

    async def accept(
        self,
        actor: int,
        version: int = 0,
        *,
        reaccept: bool = False,
    ) -> S32View | None:
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            await lock_campaign_roster(session, seed.id)
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            world = await self._locked_world(session, character.id)
            quest = await self._locked_quest(session, character.id)
            if (
                not await self._eligible_at_refuge(session, character, world)
                or await self._foreground(session, character.id)
            ):
                return await self._view(session, character, quest, world, "giver")
            if reaccept:
                if (
                    quest is None
                    or quest.status != "abandoned"
                    or quest.state_version != version
                    or quest.content_version != S32_CONTENT_VERSION
                ):
                    return await self._view(session, character, quest, world, "giver")
                quest.status = "active"
                quest.step = await self._next_step(session, character.id)
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.state_version += 1
            else:
                if quest is not None or version != 0:
                    return await self._view(session, character, quest, world, "giver")
                quest = Quest(
                    character_id=character.id,
                    quest_id=S32_ID,
                    title=S32_TITLE,
                    status="active",
                    step=2,
                    content_version=S32_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed_steps": [1], "house_report_accepted": True},
                )
                session.add(quest)
                await session.flush()
                await self._credit(
                    session,
                    character.id,
                    "s32.house_report_accepted",
                    "s32.house_report_accepted",
                    {"giver": "Haro Sen", "location_id": "location.confins.ultimo_refugio"},
                )
            return await self._view(session, character, quest, world, "detail")

    async def objective(self, actor: int) -> S32View | object | None:
        return await self.resume(actor)

    async def advance(self, actor: int, version: int, action: str):
        async with self.sessions.begin() as session:
            seed = await self._character(session, actor)
            if seed is None:
                return None
            _group_id, character_ids = await lock_campaign_roster(session, seed.id)
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version):
                return await self._view(session, character, quest, world, "detail")
            if await self._foreground(session, character.id):
                return await self._view(session, character, quest, world, "objective")
            if not await self._eligible(session, character):
                return await self._view(session, character, quest, world, "objective")

            if quest.step == 2 and action in _FOUNDATION_ACTIONS:
                if not self._at_estradas(world):
                    return await self._view(session, character, quest, world, "objective")
                await self._share_evidence(
                    session,
                    character_ids,
                    quest_step=2,
                    objective_id="s32.foundation_element",
                    source_key=_FOUNDATION_ACTIONS[action],
                    evidence={"physical_foundation_evidence": True, "shared_evidence": True},
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 3 and action in _CARD_ACTIONS:
                if not self._at_estradas(world):
                    return await self._view(session, character, quest, world, "objective")
                card = _CARD_ACTIONS[action]
                await self._share_evidence(
                    session,
                    character_ids,
                    quest_step=3,
                    objective_id="s32.document_card",
                    source_key=card,
                    evidence={
                        "mission_document": (
                            "presence" if card == S32_DOCUMENT_CARDS[0] else "absence"
                        ),
                        "economic_value": 0,
                        "shared_evidence": True,
                    },
                )
                return await self._refresh_actor_view(
                    session, character.id, world, "detail"
                )

            if quest.step == 5 and action == "compare_with_roven":
                if not self._at_refuge(world) or not await self._has_all_evidence(
                    session, character.id
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._credit(
                    session,
                    character.id,
                    "s32.documents_compared",
                    "s32.documents_compared",
                    {
                        "with": "Roven Pell",
                        "both_records_preserved": True,
                        "neither_record_declared_false": True,
                        "personal_analysis": True,
                    },
                )
                quest.step = 6
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.progress = dict(quest.progress or {}) | {"completed_steps": [1, 2, 3, 4, 5]}
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 6 and action == "record_codex":
                if not self._at_refuge(world) or not await self._has_credit(
                    session, character.id, "s32.documents_compared"
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._ensure(
                    session,
                    CodexEntry,
                    character_id=character.id,
                    entry_id=S32_CODEX_ENTRY,
                )
                await self._ensure(
                    session,
                    CodexFragment,
                    character_id=character.id,
                    entry_id=S32_CODEX_ENTRY,
                    fragment_id=S32_CODEX_FRAGMENT,
                )
                await self._credit(
                    session,
                    character.id,
                    "s32.codex_recorded",
                    "s32.codex_recorded",
                    {
                        "codex_entry": S32_CODEX_ENTRY,
                        "mission_fragment": S32_CODEX_FRAGMENT,
                        "foundation_element_ids": list(
                            await self._foundation_element_ids(session, character.id)
                        ),
                        "document_card_ids": list(
                            await self._document_card_ids(session, character.id)
                        ),
                        "preserves_presence_and_absence": True,
                        "does_not_assert_time_travel_or_duplicate_people": True,
                        "personal_knowledge": True,
                    },
                )
                quest.state_version += 1
                quest.progress = await self._progress_snapshot(session, character.id)
                quest.progress = dict(quest.progress or {}) | {
                    "completed_steps": [1, 2, 3, 4, 5]
                }
                return await self._view(session, character, quest, world, "detail")

            if quest.step == 6 and action == "conclude_with_haro":
                if (
                    not self._at_refuge(world)
                    or not await self._has_credit(session, character.id, "s32.codex_recorded")
                ):
                    return await self._view(session, character, quest, world, "objective")
                await self._complete(session, character, quest)
                await consolidate_character_level(session, character)
                return await self._view(session, character, quest, world, "completed")

            return await self._view(session, character, quest, world, "objective")

    async def start_solo_combat(self, actor: int, version: int):
        return await self.altos_missions.start_solo_combat(actor, version, S32_ID)

    async def propose_group_combat(self, actor: int, version: int):
        return await self.altos_missions.propose_group_combat(actor, version, S32_ID)

    async def retry_combat(self, actor: int, version: int):
        return await self.altos_missions.retry_combat(actor, version, S32_ID)

    async def toggle_tracking(self, actor: int, version: int) -> S32View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version) or await self._foreground(
                session, character.id
            ):
                return await self._view(session, character, quest, world, "detail")
            character.tracked_secondary_quest_id = (
                None if character.tracked_secondary_quest_id == S32_ID else S32_ID
            )
            quest.state_version += 1
            return await self._view(session, character, quest, world, "detail")

    async def abandon_confirmation(self, actor: int) -> S32View | None:
        async with self.sessions() as session:
            character = await self._character(session, actor)
            if character is None or await self._foreground(session, character.id):
                return None
            quest = await self._quest(session, character.id)
            world = await self._world(session, character.id)
            if quest is None or quest.status != "active":
                return None
            return await self._view(session, character, quest, world, "abandon_confirm")

    async def abandon(self, actor: int, version: int) -> S32View | None:
        async with self.sessions.begin() as session:
            character = await self._locked_character(session, actor)
            if character is None:
                return None
            quest = await self._locked_quest(session, character.id)
            world = await self._locked_world(session, character.id)
            if quest is None:
                return None
            if not self._valid_active(quest, version) or await self._foreground(
                session, character.id
            ):
                return await self._view(session, character, quest, world, "detail")
            quest.status = "abandoned"
            quest.step = await self._next_step(session, character.id)
            quest.progress = await self._progress_snapshot(session, character.id)
            quest.state_version += 1
            if character.tracked_secondary_quest_id == S32_ID:
                character.tracked_secondary_quest_id = None
            return await self._view(session, character, quest, world, "abandoned")

    async def _complete(self, session, character: Character, quest: Quest) -> None:
        required = (
            "s32.house_report_accepted",
            "s32.aranha_defeated",
            "s32.documents_compared",
            "s32.codex_recorded",
        )
        if not all(
            [
                await self._has_credit(session, character.id, objective_id)
                for objective_id in required
            ]
        ) or not await self._has_all_evidence(session, character.id):
            raise RuntimeError(
                "S32 cannot complete before all persistent personal and shared evidence"
            )

        event = await session.scalar(
            select(RewardEvent)
            .where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S32_REWARD_SOURCE,
            )
            .with_for_update()
        )
        if event is None:
            event = RewardEvent(character_id=character.id, source_id=S32_REWARD_SOURCE)
            session.add(event)
            await session.flush()
            character.xp += S32_XP_REWARD
            character.crowns += S32_CROWNS_REWARD
            session.add_all(
                (
                    RewardComponent(
                        reward_event_id=event.id, kind="xp", quantity=S32_XP_REWARD
                    ),
                    RewardComponent(
                        reward_event_id=event.id, kind="crowns", quantity=S32_CROWNS_REWARD
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S32_COURO_MARCHA,
                        quantity=1,
                        payload={"material_id": S32_COURO_MARCHA, "bound": True},
                    ),
                    RewardComponent(
                        reward_event_id=event.id,
                        kind="material",
                        item_id=S32_MUSGO_LIMIAR,
                        quantity=1,
                        payload={"material_id": S32_MUSGO_LIMIAR, "bound": True},
                    ),
                )
            )
            await self.altos_missions.road.deliver_material(
                session,
                character,
                S32_COURO_MARCHA,
                1,
                f"{S32_REWARD_SOURCE}:material:couro_marcha",
                bound=True,
            )
            await self.altos_missions.road.deliver_material(
                session,
                character,
                S32_MUSGO_LIMIAR,
                1,
                f"{S32_REWARD_SOURCE}:material:musgo_limiar",
                bound=True,
            )
        await self._ensure(
            session,
            Unlock,
            character_id=character.id,
            unlock_id=S32_COMPLETION_UNLOCK,
        )
        await self._credit(
            session,
            character.id,
            "s32.completed",
            "s32.completed",
            {"completion_unlock": S32_COMPLETION_UNLOCK, "personal_conclusion": True},
        )
        quest.status = "completed"
        quest.step = 6
        quest.state_version += 1
        quest.progress = dict(await self._progress_snapshot(session, character.id)) | {
            "completed": True,
            "completed_steps": [1, 2, 3, 4, 5, 6],
        }
        if character.tracked_secondary_quest_id == S32_ID:
            character.tracked_secondary_quest_id = None

    async def _view(self, session, character, quest, world, kind: str) -> S32View:
        progress = dict(quest.progress or {}) if quest is not None else {}
        progress.update(await self._progress_snapshot(session, character.id))
        gate_satisfied = await self._eligible(session, character)
        at_refuge = self._at_refuge(world)
        at_estradas = self._at_estradas(world)
        no_foreground = not await self._foreground(session, character.id)
        status = quest.status if quest is not None else "unaccepted"
        codex_owned = bool(
            await session.scalar(
                select(CodexEntry.id).where(
                    CodexEntry.character_id == character.id,
                    CodexEntry.entry_id == S32_CODEX_ENTRY,
                )
            )
        )
        exploration_fragment_owned = bool(
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character.id,
                    CodexFragment.entry_id == S32_CODEX_ENTRY,
                    CodexFragment.fragment_id == S32_EXPLORATION_FRAGMENT,
                )
            )
        )
        interaction_location = (
            at_estradas if quest is not None and quest.step in {2, 3, 4} else at_refuge
        )
        return S32View(
            character_id=character.id,
            kind=kind,
            status=status,
            step=quest.step if quest is not None else 1,
            state_version=quest.state_version if quest is not None else 0,
            progress=progress,
            location=world.location if world is not None else "",
            level=character.level,
            available=bool(
                gate_satisfied
                and at_refuge
                and quest is None
                and no_foreground
                and not await self._has_completion_unlock(session, character.id)
            ),
            reacceptable=bool(
                gate_satisfied
                and at_refuge
                and quest is not None
                and status == "abandoned"
                and no_foreground
            ),
            tracked=bool(
                quest is not None
                and status == "active"
                and character.tracked_secondary_quest_id == S32_ID
            ),
            action_available=bool(
                quest is not None
                and status == "active"
                and gate_satisfied
                and no_foreground
                and interaction_location
            ),
            gate_satisfied=gate_satisfied,
            foundation_elements=await self._foundation_element_ids(session, character.id),
            document_cards=await self._document_card_ids(session, character.id),
            victory_recorded=await self._has_credit(session, character.id, "s32.aranha_defeated"),
            codex_owned=codex_owned,
            codex_recorded=await self._has_credit(session, character.id, "s32.codex_recorded"),
            exploration_fragment_owned=exploration_fragment_owned,
        )

    async def _share_evidence(
        self,
        session,
        character_ids: tuple[UUID, ...],
        *,
        quest_step: int,
        objective_id: str,
        source_key: str,
        evidence: dict,
    ) -> None:
        members = await present_campaign_members(
            session,
            character_ids=character_ids,
            quest_id=S32_ID,
            content_version=S32_CONTENT_VERSION,
            step=quest_step,
            region=CONFINS_REGION_LABEL,
            location=CONFINS_ESTRADAS_AUSENTES_LABEL,
        )
        for member in members:
            if not await self._eligible_at_estradas(
                session, member.character, member.world
            ):
                continue
            created = await self._credit(
                session,
                member.character.id,
                objective_id,
                source_key,
                evidence | {"credited_by_character_id": str(member.character.id)},
            )
            if not created:
                continue
            progress = dict(member.quest.progress or {})
            if objective_id == "s32.foundation_element":
                elements = await self._foundation_element_ids(
                    session, member.character.id
                )
                progress["foundation_element_ids"] = list(elements)
                if set(S32_FOUNDATION_ELEMENTS).issubset(elements):
                    member.quest.step = 3
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {2}
                    )
            else:
                cards = await self._document_card_ids(session, member.character.id)
                progress["document_card_ids"] = list(cards)
                if set(S32_DOCUMENT_CARDS).issubset(cards):
                    member.quest.step = 4
                    progress["completed_steps"] = sorted(
                        set(progress.get("completed_steps", ())) | {3}
                    )
            member.quest.progress = progress
            member.quest.state_version += 1

    async def _refresh_actor_view(self, session, character_id: UUID, world, kind: str):
        character = await session.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        quest = await self._locked_quest(session, character_id)
        return (
            await self._view(session, character, quest, world, kind)
            if character is not None
            else None
        )

    async def _progress_snapshot(self, session, character_id: UUID) -> dict:
        return {
            "house_report_accepted": await self._has_credit(
                session, character_id, "s32.house_report_accepted"
            ),
            "foundation_element_ids": list(
                await self._foundation_element_ids(session, character_id)
            ),
            "document_card_ids": list(await self._document_card_ids(session, character_id)),
            "aranha_defeated": await self._has_credit(
                session, character_id, "s32.aranha_defeated"
            ),
            "documents_compared": await self._has_credit(
                session, character_id, "s32.documents_compared"
            ),
            "codex_recorded": await self._has_credit(
                session, character_id, "s32.codex_recorded"
            ),
            "completed": await self._has_credit(session, character_id, "s32.completed"),
        }

    async def _next_step(self, session, character_id: UUID) -> int:
        if await self._has_credit(session, character_id, "s32.completed"):
            return 6
        if await self._has_credit(session, character_id, "s32.codex_recorded"):
            return 6
        if await self._has_credit(session, character_id, "s32.documents_compared"):
            return 6
        if await self._has_credit(session, character_id, "s32.aranha_defeated"):
            return 5
        if set(S32_DOCUMENT_CARDS).issubset(
            await self._document_card_ids(session, character_id)
        ):
            return 4
        if set(S32_FOUNDATION_ELEMENTS).issubset(
            await self._foundation_element_ids(session, character_id)
        ):
            return 3
        if await self._has_credit(session, character_id, "s32.house_report_accepted"):
            return 2
        return 1

    async def _foundation_element_ids(
        self, session, character_id: UUID
    ) -> tuple[str, ...]:
        return await self._source_keys(
            session, character_id, "s32.foundation_element", S32_FOUNDATION_ELEMENTS
        )

    async def _document_card_ids(self, session, character_id: UUID) -> tuple[str, ...]:
        return await self._source_keys(
            session, character_id, "s32.document_card", S32_DOCUMENT_CARDS
        )

    async def _source_keys(
        self, session, character_id: UUID, objective_id: str, allowed: tuple[str, ...]
    ) -> tuple[str, ...]:
        rows = (
            await session.scalars(
                select(CampaignObjectiveCredit.source_key).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S32_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                    CampaignObjectiveCredit.source_key.in_(allowed),
                )
            )
        ).all()
        return tuple(sorted(set(rows).intersection(allowed)))

    async def _has_all_evidence(self, session, character_id: UUID) -> bool:
        return bool(
            set(S32_FOUNDATION_ELEMENTS).issubset(
                await self._foundation_element_ids(session, character_id)
            )
            and set(S32_DOCUMENT_CARDS).issubset(
                await self._document_card_ids(session, character_id)
            )
        )

    async def _has_credit(self, session, character_id: UUID, objective_id: str) -> bool:
        return bool(
            await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S32_ID,
                    CampaignObjectiveCredit.objective_id == objective_id,
                )
            )
        )

    async def _credit(
        self, session, character_id, objective_id: str, source_key: str, evidence: dict
    ) -> bool:
        existing = await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == S32_ID,
                CampaignObjectiveCredit.objective_id == objective_id,
                CampaignObjectiveCredit.source_key == source_key,
            )
        )
        if existing is not None:
            return False
        await record_campaign_objective_credit(
            session,
            character_id=character_id,
            quest_id=S32_ID,
            objective_id=objective_id,
            source_key=source_key,
            evidence=evidence,
        )
        return True

    async def _has_p32_completed(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Quest.id).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == P32_ID,
                    Quest.status == "completed",
                    Quest.content_version == P32_CONTENT_VERSION,
                )
            )
        )

    async def _eligible(self, session, character) -> bool:
        return bool(
            character is not None
            and character.level >= S32_LEVEL
            and await self._has_p32_completed(session, character.id)
        )

    async def _eligible_at_refuge(self, session, character, world) -> bool:
        return bool(self._at_refuge(world) and await self._eligible(session, character))

    async def _eligible_at_estradas(self, session, character, world) -> bool:
        return bool(self._at_estradas(world) and await self._eligible(session, character))

    async def _has_completion_unlock(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == S32_COMPLETION_UNLOCK,
                )
            )
        )

    async def _active_combat(self, session, character_id: UUID):
        return await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == S32_MISSION_ID,
                GameActivity.status == "active",
            )
        )

    async def _ensure(self, session, model, **values) -> bool:
        existing = await session.scalar(select(model).filter_by(**values).with_for_update())
        if existing is not None:
            return False
        session.add(model(**values))
        await session.flush()
        return True

    async def _character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character).where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
        )

    async def _locked_character(self, session, actor: int) -> Character | None:
        return await session.scalar(
            select(Character)
            .where(
                Character.telegram_id == actor,
                Character.server_id == self.server_id,
            )
            .with_for_update()
        )

    async def _quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S32_ID)
        )

    async def _locked_quest(self, session, character_id: UUID) -> Quest | None:
        return await session.scalar(
            select(Quest)
            .where(Quest.character_id == character_id, Quest.quest_id == S32_ID)
            .with_for_update()
        )

    async def _world(self, session, character_id: UUID) -> WorldState | None:
        return await session.get(WorldState, character_id)

    async def _locked_world(self, session, character_id: UUID) -> WorldState | None:
        return await session.scalar(
            select(WorldState)
            .where(WorldState.character_id == character_id)
            .with_for_update()
        )

    async def _foreground(self, session, character_id: UUID) -> bool:
        return bool(
            await session.scalar(
                select(GameActivity.id).where(
                    GameActivity.character_id == character_id,
                    GameActivity.status == "active",
                )
            )
        )

    @staticmethod
    def _at_refuge(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location == CONFINS_ULTIMO_REFUGIO_LABEL
        )

    @staticmethod
    def _at_estradas(world) -> bool:
        return bool(
            world is not None
            and world.region == CONFINS_REGION_LABEL
            and world.location == CONFINS_ESTRADAS_AUSENTES_LABEL
        )

    @staticmethod
    def _valid_active(quest: Quest, version: int) -> bool:
        return bool(
            quest.status == "active"
            and quest.content_version == S32_CONTENT_VERSION
            and quest.state_version == version
        )
