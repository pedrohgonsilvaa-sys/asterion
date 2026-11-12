from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import P28_CONTENT_VERSION, P28_ID
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
)
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_BASTILHA_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.s29 import (
    S29_ACHIEVEMENT,
    S29_CINZA_BASALTO,
    S29_CIVIL_MAINTENANCE_RECORDS,
    S29_CODEX_ENTRY,
    S29_CODEX_FRAGMENT,
    S29_CROWNS_REWARD,
    S29_FERRO_CONTRAPESO,
    S29_ID,
    S29_LIQUEN_PEDREIRA,
    S29_RECORDS,
    S29_REWARD_SOURCE,
    S29_XP_REWARD,
    S29Service,
)
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
)
from asterion.infrastructure.db.models import (
    Achievement,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    GameActivity,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_altos_opening import _seed_altos_exit

_RECORD_ACTIONS = {
    S29_RECORDS[0]: "locate_record_a",
    S29_RECORDS[1]: "locate_record_b",
    S29_RECORDS[2]: "locate_record_c",
}


async def _seed_s29(
    database,
    actor: int,
    *,
    level: int = 48,
    p28_status: str | None = "completed",
    location: str = ALTOS_BASTILHA_LABEL,
    access_locations: tuple[str, ...] | None = None,
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
        if p28_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P28_ID,
                    title="Os Desvelados",
                    status=p28_status,
                    step=8 if p28_status == "completed" else 5,
                    content_version=P28_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed": p28_status == "completed"},
                )
            )
        location_unlocks = {
            ALTOS_ABRIGO_LABEL: ALTOS_ABRIGO_ACCESS_UNLOCK,
            ALTOS_BASTILHA_LABEL: ALTOS_BASTILHA_ACCESS_UNLOCK,
        }
        for unlocked_location in access_locations or tuple(location_unlocks):
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id=location_unlocks[unlocked_location],
                )
            )
    return actor, road, sessions, S29Service(sessions, "ocaso", road)


async def _move(sessions, actor: int, location: str) -> None:
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = location


async def _accept_s29(service: S29Service, actor: int):
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    return accepted


async def _locate_record(service: S29Service, actor: int, record_id: str):
    view = await service.resume(actor)
    assert view is not None and view.status == "active" and view.step == 1
    old_version = view.state_version
    result = await service.advance(actor, old_version, _RECORD_ACTIONS[record_id])
    assert result is not None
    stale = await service.advance(actor, old_version, _RECORD_ACTIONS[record_id])
    assert stale is not None and stale.state_version == result.state_version
    return result


async def _advance(service: S29Service, actor: int, action: str, expected_step: int):
    view = await service.resume(actor)
    assert view is not None and view.status == "active"
    result = await service.advance(actor, view.state_version, action)
    assert result is not None and result.step == expected_step
    return result


async def _finish_s29(service: S29Service, sessions, actor: int):
    await _move(sessions, actor, ALTOS_BASTILHA_LABEL)
    for record_id in S29_RECORDS:
        view = await service.resume(actor)
        assert view is not None and view.step == 1
        if record_id not in view.refusal_records:
            await _locate_record(service, actor, record_id)
    await _advance(service, actor, "verify_civil_maintenance", 3)
    await _advance(service, actor, "verify_no_material_sabotage", 4)
    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    await _advance(service, actor, "compare_with_maro_and_sel", 5)
    return await _advance(service, actor, "record_codex", 5)


@pytest.mark.asyncio
async def test_s29_requires_completed_p28_level_and_local_access(database):
    actor, _road, _sessions, service = await _seed_s29(
        database, 789290, p28_status="active"
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available
    assert await service.accept(actor, offer.state_version) is not None
    assert await service.resume(actor) is None

    actor, _road, _sessions, service = await _seed_s29(
        database, 789291, level=47
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _road, _sessions, service = await _seed_s29(
        database,
        789292,
        location=ALTOS_ABRIGO_LABEL,
        access_locations=(ALTOS_BASTILHA_LABEL,),
    )
    assert await service.offer(actor) is None

    # S28, P29, and P30 are intentionally absent; none is an S29 prerequisite.
    actor, _road, _sessions, service = await _seed_s29(database, 789293)
    async with service.sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id.in_(("S28", "P29", "P30")),
            )
        ) is None
    await _accept_s29(service, actor)


@pytest.mark.asyncio
async def test_s29_distinct_refusals_maintenance_sabotage_codex_feat_and_reward(database):
    actor, _road, sessions, service = await _seed_s29(database, 789294)
    await _accept_s29(service, actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        initial_xp, initial_crowns = character.xp, character.crowns
        initial_unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                )
            ).all()
        )
        initial_stacks = {
            (stack.material_id, stack.bound): stack.quantity
            for stack in (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character.id)
                )
            ).all()
        }

    for record_index, record_id in enumerate(S29_RECORDS):
        await _locate_record(service, actor, record_id)
        view = await service.resume(actor)
        assert view is not None
        assert len(view.refusal_records) == len(set(view.refusal_records))
        assert set(view.refusal_records).issubset(S29_RECORDS)
        if record_index == 0:
            duplicate = await service.advance(
                actor, view.state_version, _RECORD_ACTIONS[record_id]
            )
            assert duplicate is not None
            assert duplicate.step == 1
            assert duplicate.state_version == view.state_version
            assert duplicate.refusal_records == view.refusal_records
    view = await service.resume(actor)
    assert view is not None and view.step == 2
    assert set(view.refusal_records) == set(S29_RECORDS)

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        record_credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S29_ID,
                    CampaignObjectiveCredit.objective_id == "s29.refusal_record",
                )
            )
        ).all()
        assert {credit.source_key for credit in record_credits} == set(S29_RECORDS)
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S29_ACHIEVEMENT,
            )
        ) is None
    await _advance(service, actor, "verify_civil_maintenance", 3)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        maintenance = await session.scalar(
            select(CampaignObjectiveCredit).where(
                CampaignObjectiveCredit.character_id == character.id,
                CampaignObjectiveCredit.quest_id == S29_ID,
                CampaignObjectiveCredit.objective_id == "s29.civil_maintenance_verified",
            )
        )
        assert maintenance is not None
        assert set(maintenance.evidence["continued_civil_maintenance_record_ids"]) == set(
            S29_CIVIL_MAINTENANCE_RECORDS
        )
        assert len(maintenance.evidence["continued_civil_maintenance_record_ids"]) >= 2

    await _advance(service, actor, "verify_no_material_sabotage", 4)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        no_sabotage = await session.scalar(
            select(CampaignObjectiveCredit).where(
                CampaignObjectiveCredit.character_id == character.id,
                CampaignObjectiveCredit.quest_id == S29_ID,
                CampaignObjectiveCredit.objective_id == "s29.no_material_sabotage_verified",
            )
        )
        assert no_sabotage is not None
        assert no_sabotage.evidence["material_sabotage"] is False
        assert set(no_sabotage.evidence["refusal_record_ids"]) == set(S29_RECORDS)
        assert no_sabotage.evidence["does_not_absolve_all_dissidents"] is True
        assert no_sabotage.evidence["does_not_reverse_p30_confirmation"] is True

    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    await _advance(service, actor, "compare_with_maro_and_sel", 5)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S29_ACHIEVEMENT,
            )
        ) is None

    old_version = (await service.resume(actor)).state_version
    completed = await service.advance(actor, old_version, "record_codex")
    assert completed is not None and completed.status == "completed"
    duplicate = await service.advance(actor, old_version, "record_codex")
    assert duplicate is not None and duplicate.status == "completed"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            S29_XP_REWARD,
            S29_CROWNS_REWARD,
        )
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S29_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == S29_CODEX_ENTRY,
                CodexFragment.fragment_id == S29_CODEX_FRAGMENT,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S29_ACHIEVEMENT,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S29_REWARD_SOURCE,
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
                ("xp", None, S29_XP_REWARD): 1,
                ("crowns", None, S29_CROWNS_REWARD): 1,
                ("material", S29_FERRO_CONTRAPESO, 1): 1,
                ("material", S29_LIQUEN_PEDREIRA, 1): 1,
                ("material", S29_CINZA_BASALTO, 2): 1,
            }
        )
        assert {
            (stack.material_id, stack.bound): stack.quantity
            for stack in (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character.id)
                )
            ).all()
        } == {
            **initial_stacks,
            (S29_FERRO_CONTRAPESO, True): initial_stacks.get(
                (S29_FERRO_CONTRAPESO, True), 0
            )
            + 1,
            (S29_LIQUEN_PEDREIRA, True): initial_stacks.get(
                (S29_LIQUEN_PEDREIRA, True), 0
            )
            + 1,
            (S29_CINZA_BASALTO, True): initial_stacks.get(
                (S29_CINZA_BASALTO, True), 0
            )
            + 2,
        }
        assert set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                )
            ).all()
        ) == initial_unlocks
        world = await session.get(WorldState, character.id)
        assert world is not None and world.location == ALTOS_ABRIGO_LABEL
        assert await session.scalar(
            select(GameActivity.id).where(GameActivity.character_id == character.id)
        ) is None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == "codex.altos.sabotagem_ancora_central",
            )
        ) is None

    assert CODEX_BY_ID[S29_CODEX_ENTRY].title == "Os que Disseram Não"
    assert S29_CODEX_FRAGMENT in CODEX_FRAGMENTS
    assert ACHIEVEMENT_BY_ID[S29_ACHIEVEMENT].name == "Dizer Não"


@pytest.mark.asyncio
@pytest.mark.parametrize("records_before_abandon", (1, 2))
async def test_s29_abandon_reaccept_rebuilds_only_temporary_progress(
    database, records_before_abandon
):
    actor, _road, sessions, service = await _seed_s29(
        database, 789295 + records_before_abandon
    )
    await _accept_s29(service, actor)
    for record_id in S29_RECORDS[:records_before_abandon]:
        await _locate_record(service, actor, record_id)
    active = await service.resume(actor)
    assert active is not None and active.step == 1
    abandoned = await service.abandon(actor, active.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        saved_records = await service._record_ids(session, character.id)
        assert set(saved_records) == set(S29_RECORDS[:records_before_abandon])
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S29_REWARD_SOURCE,
            )
        ) is None

    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    reaccepted = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert reaccepted is not None and reaccepted.status == "active" and reaccepted.step == 1
    assert set(reaccepted.refusal_records) == set(S29_RECORDS[:records_before_abandon])
    await _move(sessions, actor, ALTOS_BASTILHA_LABEL)
    for record_id in S29_RECORDS[records_before_abandon:]:
        await _locate_record(service, actor, record_id)
    resumed = await service.resume(actor)
    assert resumed is not None and resumed.step == 2
    assert set(resumed.refusal_records) == set(S29_RECORDS)

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await service._record_ids(session, character.id) == tuple(sorted(S29_RECORDS))
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S29_CODEX_ENTRY,
            )
        ) is None


@pytest.mark.asyncio
async def test_s29_group_member_records_alone_and_helper_stays_on_first_step(database):
    leader, road, sessions, service = await _seed_s29(database, 789298)
    helper, _helper_road, _helper_sessions, helper_service = await _seed_s29(
        database, 789299
    )
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
    await _accept_s29(service, leader)
    await _accept_s29(helper_service, helper)

    # Objectives are Solo (Ação × Consequência §5): only the leader advances.
    for record_id in S29_RECORDS:
        await _locate_record(service, leader, record_id)
    leader_view = await service.resume(leader)
    helper_view = await helper_service.resume(helper)
    assert leader_view is not None and helper_view is not None
    assert leader_view.step == 2 and helper_view.step == 1
    assert set(leader_view.refusal_records) == set(S29_RECORDS)
    assert not helper_view.refusal_records

    await _advance(service, leader, "verify_civil_maintenance", 3)
    helper_view = await helper_service.resume(helper)
    assert helper_view is not None and helper_view.step == 1
    async with sessions() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == helper)
        )
        assert helper_character is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == helper_character.id,
                CampaignObjectiveCredit.quest_id == S29_ID,
            )
        ) is None
