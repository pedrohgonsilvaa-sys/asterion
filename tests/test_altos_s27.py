from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import P27_CONTENT_VERSION, P27_ID
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import CODEX_BY_ID, CODEX_FRAGMENTS
from asterion.application.road import ALTOS_PEDREIRAS_LABEL, ALTOS_REGION_LABEL
from asterion.application.s27 import (
    S27_CODEX_ENTRY,
    S27_COURO_ESCARPA,
    S27_FERRO_CONTRAPESO,
    S27_ID,
    S27_REWARD_SOURCE,
    S27Service,
)
from asterion.domain.road import ALTOS_PEDREIRAS_ACCESS_UNLOCK
from asterion.infrastructure.db.models import (
    Achievement,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_altos_opening import _seed_altos_exit

S27_ACTIONS = (
    "inspect_broken_cable",
    "confirm_full_rebuild_unneeded",
    "validate_redundant_repair",
    "cross_repaired_route",
    "return_to_doren",
    "record_codex",
)


async def _seed_s27(
    database,
    actor: int,
    *,
    level: int = 45,
    p27_status: str | None = "active",
    access: bool = True,
    location: str = ALTOS_PEDREIRAS_LABEL,
):
    actor, road, sessions = await _seed_altos_exit(
        database, actor, level=level, p24_status="completed"
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = location
        if p27_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P27_ID,
                    title="A Continuidade a Qualquer Custo",
                    status=p27_status,
                    step=1 if p27_status == "active" else 7,
                    content_version=P27_CONTENT_VERSION,
                    progress={"activated": True, "completed": p27_status == "completed"},
                )
            )
        if access:
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id=ALTOS_PEDREIRAS_ACCESS_UNLOCK,
                )
            )
    return actor, road, sessions, S27Service(sessions, "ocaso", road)


async def _advance_all(service: S27Service, actor: int):
    view = await service.resume(actor)
    assert view is not None and view.status == "active"
    for action in S27_ACTIONS:
        previous_version = view.state_version
        view = await service.advance(actor, previous_version, action)
        assert view is not None
        duplicate = await service.advance(actor, previous_version, action)
        assert duplicate is not None and duplicate.state_version == view.state_version
    assert view.status == "completed"
    return view


def _material_stacks(rows):
    return {
        (row.material_id, row.bound): row.quantity
        for row in rows
        if row.material_id in {S27_FERRO_CONTRAPESO, S27_COURO_ESCARPA}
    }


@pytest.mark.asyncio
async def test_s27_gate_requires_p27_access_level_and_pedreiras(database):
    actor, _road, _sessions, service = await _seed_s27(
        database, 787270, p27_status=None
    )
    view = await service.offer(actor)
    assert view is not None and not view.available

    actor, _road, _sessions, service = await _seed_s27(
        database, 787271, access=False
    )
    view = await service.offer(actor)
    assert view is not None and not view.available

    actor, _road, _sessions, service = await _seed_s27(
        database, 787272, level=44
    )
    view = await service.offer(actor)
    assert view is not None and not view.available
    assert view.status == "unaccepted"

    actor, _road, _sessions, service = await _seed_s27(
        database, 787273, location=ALTOS_REGION_LABEL
    )
    assert await service.offer(actor) is None

    actor, _road, _sessions, service = await _seed_s27(
        database, 787274, p27_status="active"
    )
    active_offer = await service.offer(actor)
    assert active_offer is not None and active_offer.available
    accepted = await service.accept(actor, active_offer.state_version)
    assert accepted is not None and accepted.status == "active"

    actor, _road, _sessions, service = await _seed_s27(
        database, 787275, p27_status="completed"
    )
    completed_offer = await service.offer(actor)
    assert completed_offer is not None and completed_offer.available


@pytest.mark.asyncio
async def test_s27_six_steps_rewards_codex_and_personal_repair_only(database):
    actor, _road, sessions, service = await _seed_s27(database, 787276)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.step == 1

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        initial_xp, initial_crowns = character.xp, character.crowns
        initial_stacks = _material_stacks(
            (await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )).all()
        )
        initial_unlocks = set(
            (await session.scalars(
                select(Unlock.unlock_id).where(Unlock.character_id == character.id)
            )).all()
        )
        initial_discoveries = set(
            (await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character.id
                )
            )).all()
        )
        initial_world_rows = await session.scalar(
            select(WorldState.character_id).where(WorldState.character_id == character.id)
        )
        assert initial_world_rows is not None

    current = accepted
    for action in S27_ACTIONS[:2]:
        version = current.state_version
        current = await service.advance(actor, version, action)
        assert current is not None and current.step >= 2
    assert current.step == 3

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        before_repair = _material_stacks(
            (await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )).all()
        )
    assert before_repair == initial_stacks

    reconnected = await S27Service(sessions, "ocaso", _road).resume(actor)
    assert reconnected is not None and reconnected.step == 3
    current = await service.advance(
        actor, reconnected.state_version, "validate_redundant_repair"
    )
    assert current is not None and current.step == 4
    assert current.progress["modern_redundant_repair_validated"] is True
    assert current.progress["narrative_material_cost"] == 0
    assert current.progress["public_route_unlocked"] is False
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert _material_stacks(
            (await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )).all()
        ) == initial_stacks

    current = await service.advance(actor, current.state_version, S27_ACTIONS[3])
    assert current is not None and current.step == 5
    current = await service.advance(actor, current.state_version, S27_ACTIONS[4])
    assert current is not None and current.step == 6
    assert current.progress["returned_to_doren"] is True
    completed = await service.advance(actor, current.state_version, S27_ACTIONS[5])
    assert completed is not None and completed.status == "completed"
    duplicate_completion = await service.advance(
        actor, current.state_version, "record_codex"
    )
    assert duplicate_completion is not None and duplicate_completion.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            24_960,
            390,
        )
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S27_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == S27_CODEX_ENTRY,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S27_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((item.kind, item.item_id, item.quantity) for item in components) == Counter(
            {
                ("xp", None, 24_960): 1,
                ("crowns", None, 390): 1,
                ("material", S27_FERRO_CONTRAPESO, 1): 1,
                ("material", S27_COURO_ESCARPA, 1): 1,
            }
        )
        assert _material_stacks(
            (await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )).all()
        ) == {
            **initial_stacks,
            (S27_FERRO_CONTRAPESO, True): initial_stacks.get(
                (S27_FERRO_CONTRAPESO, True), 0
            )
            + 1,
            (S27_COURO_ESCARPA, True): initial_stacks.get(
                (S27_COURO_ESCARPA, True), 0
            )
            + 1,
        }
        assert set(
            (await session.scalars(
                select(Unlock.unlock_id).where(Unlock.character_id == character.id)
            )).all()
        ) == initial_unlocks
        assert set(
            (await session.scalars(
                select(LocationDiscovery.location_id).where(
                    LocationDiscovery.character_id == character.id
                )
            )).all()
        ) == initial_discoveries
        assert await session.scalar(
            select(WorldState.character_id).where(WorldState.character_id == character.id)
        ) == initial_world_rows
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id.like("achievement.altos.s27%"),
            )
        ) is None
        assert await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        ) is None

    assert CODEX_BY_ID[S27_CODEX_ENTRY].title == "Reparo Redundante"
    assert "reparo moderno redundante" in CODEX_FRAGMENTS[S27_CODEX_ENTRY].text


@pytest.mark.asyncio
async def test_s27_abandon_requires_no_foreground_and_reaccept_preserves_codex(database):
    actor, _road, sessions, service = await _seed_s27(database, 787277)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        session.add_all(
            (
                CodexEntry(character_id=character.id, entry_id=S27_CODEX_ENTRY),
                CodexFragment(
                    character_id=character.id,
                    entry_id=S27_CODEX_ENTRY,
                    fragment_id=S27_CODEX_ENTRY,
                ),
                GameActivity(
                    character_id=character.id,
                    content_id="s27.foreground_test",
                    status="active",
                    state_version=0,
                    ruleset_version="test",
                ),
            )
        )
    accepted = await service.accept(actor)
    assert accepted is None or accepted.status == "unaccepted"

    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.content_id == "s27.foreground_test")
        )
        assert activity is not None
        await session.delete(activity)
    accepted = await service.accept(actor)
    assert accepted is not None and accepted.status == "active"
    first = await service.advance(actor, accepted.state_version, S27_ACTIONS[0])
    assert first is not None and first.step == 2

    async with sessions.begin() as session:
        session.add(
            GameActivity(
                content_id="s27.foreground_test",
                character_id=first.character_id,
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    blocked = await service.abandon(actor, first.state_version)
    assert blocked is not None and blocked.status == "active" and blocked.step == 2
    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.content_id == "s27.foreground_test")
        )
        assert activity is not None
        await session.delete(activity)
    abandoned = await service.abandon(actor, first.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    assert abandoned.progress == {}
    reaccepted = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert reaccepted is not None and reaccepted.status == "active" and reaccepted.step == 1
    assert reaccepted.codex_owned is True


@pytest.mark.asyncio
async def test_s27_shareable_physical_evidence_and_personal_steps(database):
    leader, _road, sessions, service = await _seed_s27(database, 787278)
    helper, _road, _sessions, _other_service = await _seed_s27(database, 787279)
    async with sessions() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == helper)
        )
        assert helper_character is not None
        helper_name = helper_character.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    for actor in (leader, helper):
        accepted = await service.accept(actor)
        assert accepted is not None and accepted.step == 1

    leader_view = await service.resume(leader)
    assert leader_view is not None
    leader_view = await service.advance(
        leader, leader_view.state_version, S27_ACTIONS[0]
    )
    assert leader_view is not None and leader_view.step == 2
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 2

    leader_view = await service.advance(
        leader, leader_view.state_version, S27_ACTIONS[1]
    )
    assert leader_view is not None and leader_view.step == 3
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 2
    helper_view = await service.advance(
        helper, helper_view.state_version, S27_ACTIONS[1]
    )
    assert helper_view is not None and helper_view.step == 3

    leader_view = await service.resume(leader)
    assert leader_view is not None and leader_view.step == 3
    leader_view = await service.advance(
        leader, leader_view.state_version, S27_ACTIONS[2]
    )
    assert leader_view is not None and leader_view.step == 4
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 4

    leader_view = await service.advance(
        leader, leader_view.state_version, S27_ACTIONS[3]
    )
    assert leader_view is not None and leader_view.step == 5
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 5

    leader_view = await service.advance(
        leader, leader_view.state_version, S27_ACTIONS[4]
    )
    assert leader_view is not None and leader_view.step == 6
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 5

    async with sessions() as session:
        character_ids = set(
            (
                await session.scalars(
                    select(Character.id).where(Character.telegram_id.in_((leader, helper)))
                )
            ).all()
        )
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == S27_ID,
                    CampaignObjectiveCredit.objective_id.in_(
                        (
                            "s27.old_cable_inspected",
                            "s27.modern_redundant_repair_validated",
                            "s27.repaired_route_crossed",
                        )
                    ),
                )
            )
        ).all()
        assert {credit.character_id for credit in credits} == character_ids
