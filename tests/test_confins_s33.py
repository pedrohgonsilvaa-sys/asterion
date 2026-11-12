import asyncio
from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P33_CONTENT_VERSION,
    P33_ID,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.road import (
    CONFINS_FRATURAS_ACCESS_UNLOCK,
    CONFINS_FRATURAS_LIMIAR_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.application.s33 import (
    S33_CODEX_ENTRY,
    S33_CODEX_FRAGMENT,
    S33_COMPLETION_UNLOCK,
    S33_CROWNS_REWARD,
    S33_DOCUMENT_LISTS,
    S33_FERRO_BALIZA,
    S33_FIELD_INSCRIPTIONS,
    S33_ID,
    S33_MISSION_ID,
    S33_MUSGO_LIMIAR,
    S33_XP_REWARD,
    S33Service,
)
from asterion.infrastructure.db.models import (
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
from tests.test_confins_p31 import _seed_confins_actor


async def _seed_s33(
    database,
    actor: int,
    *,
    level: int = 55,
    p33_status: str | None = "completed",
    fraturas_access: bool = True,
    location: str = CONFINS_ULTIMO_REFUGIO_LABEL,
):
    actor, _road, sessions = await _seed_confins_actor(
        database, actor, level=max(51, level)
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        if level >= 60:
            character.xp = 0
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = location
        if p33_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P33_ID,
                    title="O Avesso",
                    status=p33_status,
                    step=6 if p33_status == "completed" else 1,
                    content_version=P33_CONTENT_VERSION,
                    state_version=6 if p33_status == "completed" else 1,
                    progress={"completed": p33_status == "completed"},
                )
            )
        if fraturas_access:
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id=CONFINS_FRATURAS_ACCESS_UNLOCK,
                )
            )
    mission = AltosMissionService(sessions, "ocaso")
    return actor, sessions, mission, S33Service(sessions, "ocaso", mission)


@pytest.mark.asyncio
async def test_s33_gate_offer_and_explicit_acceptance(database):
    actor, _sessions, _mission, service = await _seed_s33(
        database, 833001, level=55, p33_status=None
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _sessions, _mission, service = await _seed_s33(
        database, 833002, level=54
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, sessions, _mission, service = await _seed_s33(database, 833003, level=55)
    offer = await service.offer(actor)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    assert await service.giver(actor) is not None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == S33_ID
            )
        ) is None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == "P34"
            )
        ) is None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == "S31"
            )
        ) is None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == "S32"
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S33_MISSION_ID,
            )
        ) is None
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 2
    assert accepted.lists_received and not accepted.codex_owned
    assert not hasattr(service, "start_solo_combat")


@pytest.mark.asyncio
async def test_s33_inscriptions_abandon_codex_and_reward_are_idempotent(database):
    actor, sessions, _mission, service = await _seed_s33(
        database, 833010, level=60
    )
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        initial_crowns = character.crowns
        world = await session.get(WorldState, character_id)
        assert world is not None
        initial_region, initial_location = world.region, world.location

    accepted = await service.accept(actor, 0)
    assert accepted is not None and accepted.step == 2
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_FRATURAS_LIMIAR_LABEL

    first = await service.advance(actor, accepted.state_version, "inspect_inscription_a")
    assert first is not None and first.step == 2
    assert first.field_inscriptions == (S33_FIELD_INSCRIPTIONS[0],)
    abandoned = await service.abandon(actor, first.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    resumed = await service.accept(
        actor, abandoned.state_version, reaccept=True
    )
    assert resumed is not None and resumed.status == "active" and resumed.step == 2
    assert resumed.field_inscriptions == (S33_FIELD_INSCRIPTIONS[0],)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_FRATURAS_LIMIAR_LABEL

    duplicate = await service.advance(
        actor, resumed.state_version, "inspect_inscription_a"
    )
    assert duplicate is not None and duplicate.step == 2
    assert duplicate.field_inscriptions == (S33_FIELD_INSCRIPTIONS[0],)
    complete_inscriptions = await service.advance(
        actor, duplicate.state_version, "inspect_inscription_b"
    )
    assert complete_inscriptions is not None and complete_inscriptions.step == 3
    assert set(complete_inscriptions.field_inscriptions) == set(S33_FIELD_INSCRIPTIONS)

    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    analyzed = await service.advance(
        actor, complete_inscriptions.state_version, "analyze_documents"
    )
    assert analyzed is not None and analyzed.step == 4
    assert analyzed.progress["proven_copy_error"] is True
    assert analyzed.progress["material_discrepancy_unresolved"] is True
    assert analyzed.progress["documents_analyzed"] is True
    recorded = await service.advance(actor, analyzed.state_version, "record_codex")
    assert recorded is not None and recorded.step == 5 and recorded.codex_recorded
    assert recorded.codex_owned
    async with sessions() as session:
        entry = await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == S33_CODEX_ENTRY,
            )
        )
        fragment = await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == S33_CODEX_ENTRY,
                CodexFragment.fragment_id == S33_CODEX_FRAGMENT,
            )
        )
        assert entry is not None and fragment is not None
        analysis_credit = await session.scalar(
            select(CampaignObjectiveCredit).where(
                CampaignObjectiveCredit.character_id == character_id,
                CampaignObjectiveCredit.quest_id == S33_ID,
                CampaignObjectiveCredit.objective_id == "s33.documents_analyzed",
            )
        )
        assert analysis_credit is not None
        assert analysis_credit.evidence["document_list_ids"] == list(S33_DOCUMENT_LISTS)
        assert set(analysis_credit.evidence["field_inscription_ids"]) == set(
            S33_FIELD_INSCRIPTIONS
        )

    results = await asyncio.gather(
        service.advance(actor, recorded.state_version, "conclude_with_roven"),
        service.advance(actor, recorded.state_version, "conclude_with_roven"),
    )
    assert all(result is not None and result.status == "completed" for result in results)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.level == 60 and character.xp == 0
        assert character.crowns == initial_crowns + S33_CROWNS_REWARD
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S33_ID,
            )
        )
        assert quest is not None and quest.status == "completed" and quest.step == 5
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == S33_COMPLETION_UNLOCK,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S33_MISSION_ID,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, S33_XP_REWARD): 1,
                ("crowns", None, S33_CROWNS_REWARD): 1,
                ("material", S33_FERRO_BALIZA, 1): 1,
                ("material", S33_MUSGO_LIMIAR, 1): 1,
            }
        )
        for material_id in (S33_FERRO_BALIZA, S33_MUSGO_LIMIAR):
            stack = await session.scalar(
                select(MaterialStack).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == material_id,
                    MaterialStack.bound.is_(True),
                )
            )
            assert stack is not None and stack.quantity == 1
        world = await session.get(WorldState, character_id)
        assert world is not None
        assert (world.region, world.location) == (initial_region, initial_location)
        regional_unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(
                        Unlock.character_id == character_id,
                        Unlock.unlock_id.like("unlock.%confins.%"),
                    )
                )
            ).all()
        )
        assert regional_unlocks == {CONFINS_FRATURAS_ACCESS_UNLOCK}


@pytest.mark.asyncio
async def test_s33_inscriptions_advance_only_the_acting_member(database):
    actors = (833020, 833021, 833022)
    _leader, sessions, _mission, _service = await _seed_s33(
        database, actors[0], level=55
    )
    await _seed_s33(database, actors[1], level=55)
    await _seed_s33(database, actors[2], level=55, p33_status=None)

    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        names = {character.telegram_id: character.name for character in characters}
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], names[actors[1]], expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    group = await groups.group(actors[0])
    invite = await groups.invite(
        actors[0], names[actors[2]], expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[2], invite.invite_id, expected_revision=invite.revision, accept=True
    )

    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S33Service(sessions, "ocaso", mission)
    leader = await service.accept(actors[0], 0)
    helper = await service.accept(actors[1], 0)
    spectator = await service.accept(actors[2], 0)
    assert leader is not None and leader.status == "active" and leader.step == 2
    assert helper is not None and helper.status == "active" and helper.step == 2
    assert spectator is not None and not spectator.available and spectator.status == "unaccepted"

    async with sessions.begin() as session:
        for telegram_id in actors:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == telegram_id)
            )
            assert character is not None
            world = await session.get(WorldState, character.id)
            assert world is not None
            world.location = CONFINS_FRATURAS_LIMIAR_LABEL

    # Inscriptions are Solo (Ação × Consequência §5): only the leader advances.
    leader = await service.advance(actors[0], leader.state_version, "inspect_inscription_a")
    helper = await service.resume(actors[1])
    assert leader is not None and helper is not None
    assert leader.field_inscriptions == (S33_FIELD_INSCRIPTIONS[0],)
    assert helper.step == 2 and helper.field_inscriptions == ()
    spectator_view = await service.resume(actors[2])
    assert spectator_view is None

    leader = await service.summary(actors[0])
    assert leader is not None
    leader = await service.advance(actors[0], leader.state_version, "inspect_inscription_b")
    helper = await service.resume(actors[1])
    assert leader is not None and helper is not None
    assert leader.step == 3 and helper.step == 2
    assert set(leader.field_inscriptions) == set(S33_FIELD_INSCRIPTIONS)
    assert helper.field_inscriptions == ()

    async with sessions.begin() as session:
        for telegram_id in actors:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == telegram_id)
            )
            assert character is not None
            world = await session.get(WorldState, character.id)
            assert world is not None
            world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    leader = await service.advance(actors[0], leader.state_version, "analyze_documents")
    assert leader is not None and leader.step == 4
    helper = await service.resume(actors[1])
    assert helper is not None and helper.step == 2 and not helper.analysis_recorded

    async with sessions() as session:
        leader_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[0])
        )
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert leader_character is not None and helper_character is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == leader_character.id,
                CodexEntry.entry_id == S33_CODEX_ENTRY,
            )
        ) is None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == helper_character.id,
                CampaignObjectiveCredit.quest_id == S33_ID,
                CampaignObjectiveCredit.objective_id == "s33.documents_analyzed",
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == leader_character.id,
                RewardEvent.source_id == S33_MISSION_ID,
            )
        ) is None
