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
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.s28 import (
    S28_ACHIEVEMENT,
    S28_CINZA_BASALTO,
    S28_CODEX_ENTRY,
    S28_CROWNS_REWARD,
    S28_FERRO_CONTRAPESO,
    S28_ID,
    S28_LETTER_FRAGMENTS,
    S28_LIQUEN_PEDREIRA,
    S28_REWARD_SOURCE,
    S28_XP_REWARD,
    S28Service,
)
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PONTES_ACCESS_UNLOCK,
)
from asterion.infrastructure.db.models import (
    Achievement,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_altos_opening import _seed_altos_exit

S28_ACTIONS = (
    "recover_civil_letter",
    "recover_workers_letter",
    "recover_archive_letter",
    "compare_with_maro",
    "corroborate_codex",
)
S28_LOCATIONS = (
    ALTOS_PONTES_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_BASTILHA_LABEL,
)
S28_UNLOCKS = (
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
)
S28_REQUIRED_UNLOCKS = {
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_BASTILHA_ACCESS_UNLOCK,
}


async def _seed_s28(
    database,
    actor: int,
    *,
    level: int = 47,
    p28_status: str | None = "active",
    location: str = ALTOS_ABRIGO_LABEL,
    access: bool = True,
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
                    step=5 if p28_status == "active" else 8,
                    content_version=P28_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed": p28_status == "completed"},
                )
            )
        if access:
            location_unlocks = {
                ALTOS_ABRIGO_LABEL: ALTOS_ABRIGO_ACCESS_UNLOCK,
                ALTOS_PONTES_LABEL: ALTOS_PONTES_ACCESS_UNLOCK,
                ALTOS_PEDREIRAS_LABEL: ALTOS_PEDREIRAS_ACCESS_UNLOCK,
                ALTOS_BASTILHA_LABEL: ALTOS_BASTILHA_ACCESS_UNLOCK,
            }
            selected = access_locations or tuple(location_unlocks)
            session.add_all(
                Unlock(character_id=character.id, unlock_id=location_unlocks[item])
                for item in selected
            )
    return actor, road, sessions, S28Service(sessions, "ocaso", road)


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


async def _collect_letter(service: S28Service, sessions, actor: int, step: int):
    await _move(sessions, actor, S28_LOCATIONS[step - 1])
    view = await service.resume(actor)
    assert view is not None and view.status == "active" and view.step == step
    action = S28_ACTIONS[step - 1]
    old_version = view.state_version
    advanced = await service.advance(actor, old_version, action)
    assert advanced is not None and advanced.step == step + 1
    duplicate = await service.advance(actor, old_version, action)
    assert duplicate is not None and duplicate.state_version == advanced.state_version
    return advanced


async def _accept_s28(service: S28Service, actor: int):
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    return accepted


async def _fragment_ids(session, character_id):
    return set(
        (
            await session.scalars(
                select(CodexFragment.fragment_id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.entry_id == S28_CODEX_ENTRY,
                )
            )
        ).all()
    )


@pytest.mark.asyncio
async def test_s28_gate_requires_p28_level_and_access_at_maro(database):
    actor, _road, _sessions, service = await _seed_s28(
        database, 788280, p28_status=None
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _road, _sessions, service = await _seed_s28(
        database, 788281, level=46
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _road, _sessions, service = await _seed_s28(
        database, 788282, access=False
    )
    assert await service.offer(actor) is None

    actor, _road, _sessions, service = await _seed_s28(
        database, 788283, p28_status="completed"
    )
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active"


@pytest.mark.asyncio
async def test_s28_five_steps_three_permanent_fragments_reward_and_achievement(database):
    actor, _road, sessions, service = await _seed_s28(database, 788284)
    accepted = await _accept_s28(service, actor)
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
            (item.material_id, item.bound): item.quantity
            for item in (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character.id)
                )
            ).all()
        }

    current = accepted
    for step in (1, 2, 3):
        current = await _collect_letter(service, sessions, actor, step)
        assert current is not None
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            owned = await _fragment_ids(session, character.id)
            assert len(owned) == step
            assert await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character.id,
                    Achievement.achievement_id == S28_ACHIEVEMENT,
                )
            ) is None
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S28_REWARD_SOURCE,
                )
            ) is None

    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    current = await service.resume(actor)
    assert current is not None and current.step == 4
    current = await service.advance(actor, current.state_version, "compare_with_maro")
    assert current is not None and current.step == 5
    old_version = current.state_version
    current = await service.advance(actor, old_version, "corroborate_codex")
    assert current is not None and current.status == "completed"
    duplicate = await service.advance(actor, old_version, "corroborate_codex")
    assert duplicate is not None and duplicate.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp - initial_xp, character.crowns - initial_crowns) == (
            S28_XP_REWARD,
            S28_CROWNS_REWARD,
        )
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S28_CODEX_ENTRY,
            )
        ) is not None
        assert await _fragment_ids(session, character.id) == set(S28_LETTER_FRAGMENTS)
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S28_ACHIEVEMENT,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S28_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == reward.id
                )
            )
        ).all()
        assert Counter((item.kind, item.item_id, item.quantity) for item in components) == Counter(
            {
                ("xp", None, S28_XP_REWARD): 1,
                ("crowns", None, S28_CROWNS_REWARD): 1,
                ("material", S28_FERRO_CONTRAPESO, 1): 1,
                ("material", S28_LIQUEN_PEDREIRA, 1): 1,
                ("material", S28_CINZA_BASALTO, 2): 1,
            }
        )
        assert {
            (item.material_id, item.bound): item.quantity
            for item in (
                await session.scalars(
                    select(MaterialStack).where(MaterialStack.character_id == character.id)
                )
            ).all()
        } == {
            **initial_stacks,
            (S28_FERRO_CONTRAPESO, True): initial_stacks.get(
                (S28_FERRO_CONTRAPESO, True), 0
            )
            + 1,
            (S28_LIQUEN_PEDREIRA, True): initial_stacks.get(
                (S28_LIQUEN_PEDREIRA, True), 0
            )
            + 1,
            (S28_CINZA_BASALTO, True): initial_stacks.get(
                (S28_CINZA_BASALTO, True), 0
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

    assert CODEX_BY_ID[S28_CODEX_ENTRY].title == "Cartas de Emergência"
    assert set(S28_LETTER_FRAGMENTS).issubset(CODEX_FRAGMENTS)
    assert ACHIEVEMENT_BY_ID[S28_ACHIEVEMENT].name == "Fora do Arquivo"


@pytest.mark.asyncio
@pytest.mark.parametrize("cards_before_abandon", (1, 2))
async def test_s28_abandon_reaccept_keeps_individual_letter_fragments(
    database, cards_before_abandon
):
    actor, _road, sessions, service = await _seed_s28(
        database, 788285 + cards_before_abandon
    )
    await _accept_s28(service, actor)
    current = None
    for step in range(1, cards_before_abandon + 1):
        current = await _collect_letter(service, sessions, actor, step)
    assert current is not None and current.step == cards_before_abandon + 1
    abandoned = await service.abandon(actor, current.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert len(await _fragment_ids(session, character.id)) == cards_before_abandon

    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    reaccepted = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert reaccepted is not None and reaccepted.step == 1
    current = reaccepted
    for step in range(1, cards_before_abandon + 1):
        current = await _collect_letter(service, sessions, actor, step)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert len(await _fragment_ids(session, character.id)) == cards_before_abandon


@pytest.mark.asyncio
async def test_s28_cannot_corroborate_without_all_three_letters(database):
    actor, _road, sessions, service = await _seed_s28(database, 788288)
    await _accept_s28(service, actor)
    await _collect_letter(service, sessions, actor, 1)
    await _collect_letter(service, sessions, actor, 2)
    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == S28_ID,
            )
        )
        assert quest is not None
        quest.step = 5
        quest.progress = {"compared_with_maro": True}
    blocked = await service.resume(actor)
    assert blocked is not None and blocked.step == 5
    result = await service.advance(actor, blocked.state_version, "corroborate_codex")
    assert result is not None and result.status == "active"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S28_ACHIEVEMENT,
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S28_REWARD_SOURCE,
            )
        ) is None

@pytest.mark.asyncio
async def test_s28_letters_credit_only_the_acting_member(database):
    leader, _road, sessions, service = await _seed_s28(database, 788289)
    helper, _road, _sessions, helper_service = await _seed_s28(database, 788290)
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
    await _accept_s28(service, leader)
    await _accept_s28(helper_service, helper)
    await _move(sessions, leader, ALTOS_PONTES_LABEL)
    await _move(sessions, helper, ALTOS_PONTES_LABEL)
    leader_view = await service.resume(leader)
    assert leader_view is not None and leader_view.step == 1
    # Objectives are Solo (Ação × Consequência §5): only the leader advances.
    shared = await service.advance(
        leader, leader_view.state_version, S28_ACTIONS[0]
    )
    assert shared is not None and shared.step == 2
    helper_view = await helper_service.resume(helper)
    assert helper_view is not None and helper_view.step == 1

    async with sessions() as session:
        leader_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == leader)
        )
        helper_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == helper)
        )
        quests = {
            quest.character_id: quest
            for quest in (
                await session.scalars(
                    select(Quest).where(
                        Quest.character_id.in_((leader_id, helper_id)),
                        Quest.quest_id == S28_ID,
                    )
                )
            ).all()
        }
        assert quests[leader_id].step == 2 and quests[helper_id].step == 1
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == leader_id,
                CodexFragment.fragment_id == S28_LETTER_FRAGMENTS[0],
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == helper_id,
                CodexFragment.fragment_id == S28_LETTER_FRAGMENTS[0],
            )
        ) is None
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_((leader_id, helper_id)),
                    CampaignObjectiveCredit.quest_id == S28_ID,
                    CampaignObjectiveCredit.objective_id == "s28.letter.civil",
                )
            )
        ).all()
        assert {credit.character_id for credit in credits} == {leader_id}

    for step in (2, 3):
        location = S28_LOCATIONS[step - 1]
        await _move(sessions, leader, location)
        leader_view = await service.resume(leader)
        assert leader_view is not None and leader_view.step == step
        leader_view = await service.advance(
            leader, leader_view.state_version, S28_ACTIONS[step - 1]
        )
        assert leader_view is not None and leader_view.step == step + 1
        helper_view = await helper_service.resume(helper)
        assert helper_view is not None and helper_view.step == 1

    leader_view = await service.resume(leader)
    assert leader_view is not None and leader_view.step == 4
    leader_view = await service.advance(
        leader, leader_view.state_version, "compare_with_maro"
    )
    assert leader_view is not None and leader_view.step == 5
    helper_view = await helper_service.resume(helper)
    assert helper_view is not None and helper_view.step == 1


@pytest.mark.asyncio
async def test_s28_wrong_location_or_missing_location_unlock_cannot_award_letter(database):
    actor, _road, sessions, service = await _seed_s28(
        database,
        788291,
        access_locations=(ALTOS_ABRIGO_LABEL, ALTOS_PEDREIRAS_LABEL, ALTOS_BASTILHA_LABEL),
    )
    await _accept_s28(service, actor)
    await _move(sessions, actor, ALTOS_ABRIGO_LABEL)
    current = await service.resume(actor)
    assert current is not None
    blocked = await service.advance(actor, current.state_version, S28_ACTIONS[0])
    assert blocked is not None and blocked.step == 1

    await _move(sessions, actor, ALTOS_PONTES_LABEL)
    current = await service.resume(actor)
    assert current is not None
    blocked = await service.advance(actor, current.state_version, S28_ACTIONS[0])
    assert blocked is not None and blocked.step == 1
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == S28_CODEX_ENTRY,
            )
        ) is None
