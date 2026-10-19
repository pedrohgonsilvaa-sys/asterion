import asyncio
from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P25_COMBAT,
    P32_CONTENT_VERSION,
    P32_ID,
    S32_ID,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.road import (
    CONFINS_ESTRADAS_AUSENTES_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.application.s32 import (
    S32_CODEX_ENTRY,
    S32_CODEX_FRAGMENT,
    S32_COMPLETION_UNLOCK,
    S32_COURO_MARCHA,
    S32_CROWNS_REWARD,
    S32_DOCUMENT_CARDS,
    S32_EXPLORATION_FRAGMENT,
    S32_FOUNDATION_ELEMENTS,
    S32_MISSION_ID,
    S32_MUSGO_LIMIAR,
    S32_XP_REWARD,
    S32Service,
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


async def _seed_s32_actor(
    database,
    actor: int,
    *,
    level: int = 54,
    p32_status: str | None = "completed",
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
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = location
        if p32_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P32_ID,
                    title="A Fratura",
                    status=p32_status,
                    step=6 if p32_status == "completed" else 2,
                    content_version=P32_CONTENT_VERSION,
                    state_version=6 if p32_status == "completed" else 2,
                    progress={"completed": p32_status == "completed"},
                )
            )
    mission = AltosMissionService(sessions, "ocaso")
    return actor, sessions, mission, S32Service(sessions, "ocaso", mission)


@pytest.mark.asyncio
async def test_s32_gate_offer_and_explicit_acceptance(database):
    actor, sessions, _mission, service = await _seed_s32_actor(
        database, 832001, level=54, p32_status=None
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, _sessions, _mission, service = await _seed_s32_actor(
        database, 832002, level=53
    )
    offer = await service.offer(actor)
    assert offer is not None and not offer.available

    actor, sessions, _mission, service = await _seed_s32_actor(database, 832003)
    offer = await service.offer(actor)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == S32_ID
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S32_MISSION_ID,
            )
        ) is None
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("with_exploration_fragment", (True, False))
async def test_s32_solo_abandon_retry_codex_fragments_and_reward_once(
    database, monkeypatch, with_exploration_fragment
):
    from tests.test_s4_s5_integration import _terminal

    actor, sessions, mission, service = await _seed_s32_actor(
        database, 832010, level=60
    )
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        initial_crowns = character.crowns
        initial_vigor = character.vigor
        if with_exploration_fragment:
            session.add_all(
                [
                    CodexEntry(character_id=character_id, entry_id=S32_CODEX_ENTRY),
                    CodexFragment(
                        character_id=character_id,
                        entry_id=S32_CODEX_ENTRY,
                        fragment_id=S32_EXPLORATION_FRAGMENT,
                    ),
                ]
            )

    offer = await service.offer(actor)
    assert offer is not None and offer.available
    view = await service.accept(actor, offer.state_version)
    assert view is not None and view.step == 2
    assert view.exploration_fragment_owned is with_exploration_fragment
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_ESTRADAS_AUSENTES_LABEL

    view = await service.advance(actor, view.state_version, "recognize_foundation_a")
    assert view is not None and view.foundation_elements == (S32_FOUNDATION_ELEMENTS[0],)
    abandoned = await service.abandon(actor, view.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    resumed = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert resumed is not None and resumed.status == "active" and resumed.step == 2
    assert resumed.foundation_elements == (S32_FOUNDATION_ELEMENTS[0],)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_ESTRADAS_AUSENTES_LABEL

    for _evidence, action in zip(
        S32_FOUNDATION_ELEMENTS[1:],
        ("recognize_foundation_b", "recognize_foundation_c"),
        strict=True,
    ):
        view = await service.advance(actor, resumed.state_version, action)
        assert view is not None
        resumed = view
    assert view is not None and view.step == 3
    duplicate = await service.advance(
        actor, view.state_version, "recognize_foundation_a"
    )
    assert duplicate is not None and duplicate.foundation_elements == S32_FOUNDATION_ELEMENTS
    assert duplicate.step == 3

    view = duplicate
    for action in ("recover_presence_card", "recover_absence_card"):
        view = await service.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 4 and set(view.document_cards) == set(S32_DOCUMENT_CARDS)

    battle = await service.start_solo_combat(actor, view.state_version)
    assert battle is not None and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert P25_COMBAT[S32_ID][3] == "creature.confins.aranha_limiar"
    assert enemies[0].name == "Aranha de Limiar"
    assert enemies[0].level == 54 and battle.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 4
    assert defeated.progress["awaiting_retry"] is True
    retry = await service.retry_combat(actor, defeated.state_version)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    assert retry.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert victory is not None and victory.step == 5

    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    view = await service.resume(actor)
    assert view is not None and view.step == 5 and view.victory_recorded
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.crowns == initial_crowns
        assert character.vigor == initial_vigor
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S32_MISSION_ID,
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id.like("unlock.round.confins.%"),
            )
        ) is None

    view = await service.advance(actor, view.state_version, "compare_with_roven")
    assert view is not None and view.step == 6
    view = await service.advance(actor, view.state_version, "record_codex")
    assert view is not None and view.codex_recorded
    assert view.exploration_fragment_owned is with_exploration_fragment
    results = await asyncio.gather(
        service.advance(actor, view.state_version, "conclude_with_haro"),
        service.advance(actor, view.state_version, "conclude_with_haro"),
    )
    assert all(result is not None and result.status == "completed" for result in results)

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.level == 60 and character.xp == 0
        assert character.crowns == initial_crowns + S32_CROWNS_REWARD
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S32_ID,
            )
        )
        assert quest is not None and quest.status == "completed"
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == S32_COMPLETION_UNLOCK,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S32_MISSION_ID,
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
                ("xp", None, S32_XP_REWARD): 1,
                ("crowns", None, S32_CROWNS_REWARD): 1,
                ("material", S32_COURO_MARCHA, 1): 1,
                ("material", S32_MUSGO_LIMIAR, 1): 1,
            }
        )
        for material_id in (S32_COURO_MARCHA, S32_MUSGO_LIMIAR):
            stack = await session.scalar(
                select(MaterialStack).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == material_id,
                )
            )
            assert stack is not None and stack.quantity == 1 and stack.bound is True
        fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id,
                        CodexFragment.entry_id == S32_CODEX_ENTRY,
                    )
                )
            ).all()
        )
        expected_fragments = {S32_CODEX_FRAGMENT}
        if with_exploration_fragment:
            expected_fragments.add(S32_EXPLORATION_FRAGMENT)
        assert fragments == expected_fragments
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S32_ID,
                )
            )
        ).all()
        for evidence_id in (*S32_FOUNDATION_ELEMENTS, *S32_DOCUMENT_CARDS):
            assert any(row.source_key == evidence_id for row in credits)
        assert any(row.objective_id == "s32.completed" for row in credits)
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id.like("unlock.location.confins.%"),
            )
        ) is None

    if not with_exploration_fragment:
        async with sessions.begin() as session:
            session.add(
                CodexFragment(
                    character_id=character_id,
                    entry_id=S32_CODEX_ENTRY,
                    fragment_id=S32_EXPLORATION_FRAGMENT,
                )
            )
        completed = await service.summary(actor)
        assert completed is not None and completed.exploration_fragment_owned
        async with sessions() as session:
            fragments = set(
                (
                    await session.scalars(
                        select(CodexFragment.fragment_id).where(
                            CodexFragment.character_id == character_id,
                            CodexFragment.entry_id == S32_CODEX_ENTRY,
                        )
                    )
                ).all()
            )
        assert fragments == {S32_EXPLORATION_FRAGMENT, S32_CODEX_FRAGMENT}


@pytest.mark.asyncio
async def test_s32_group_shares_only_accepted_present_eligible_participants(
    database, monkeypatch
):
    from asterion.application import scripted_combat
    from asterion.domain.combat import active_player_key
    from tests.test_campaign_coop_integration import _seed_enemy_at_one_hp
    from tests.test_s4_s5_integration import _terminal

    actors = (832020, 832021)
    _leader, sessions, _mission, _service = await _seed_s32_actor(
        database, actors[0]
    )
    await _seed_s32_actor(database, actors[1])
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
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S32Service(sessions, "ocaso", mission)

    leader = await service.accept(actors[0], 0)
    assert leader is not None and leader.step == 2
    async with sessions.begin() as session:
        leader_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[0])
        )
        assert leader_character is not None
        leader_id = leader_character.id
        world = await session.get(WorldState, leader_id)
        assert world is not None
        world.location = CONFINS_ESTRADAS_AUSENTES_LABEL
    leader = await service.advance(
        actors[0], leader.state_version, "recognize_foundation_a"
    )
    assert leader is not None and leader.foundation_elements == (S32_FOUNDATION_ELEMENTS[0],)
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == helper.id,
                Quest.quest_id == S32_ID,
            )
        ) is None
    helper = await service.accept(actors[1], 0)
    assert helper is not None and helper.step == 2
    async with sessions.begin() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper_character is not None
        helper_world = await session.get(WorldState, helper_character.id)
        assert helper_world is not None
        helper_world.location = CONFINS_ESTRADAS_AUSENTES_LABEL
    leader = await service.advance(
        actors[0], leader.state_version, "recognize_foundation_a"
    )
    assert leader is not None
    helper = await service.resume(actors[1])
    assert helper is not None and helper.foundation_elements == (S32_FOUNDATION_ELEMENTS[0],)

    for action in (
        "recognize_foundation_b",
        "recognize_foundation_c",
    ):
        leader = await service.summary(actors[0])
        assert leader is not None
        leader = await service.advance(actors[0], leader.state_version, action)
        assert leader is not None
    for action in ("recover_presence_card", "recover_absence_card"):
        leader = await service.summary(actors[0])
        assert leader is not None
        leader = await service.advance(actors[0], leader.state_version, action)
        assert leader is not None
    assert leader.step == 4
    helper = await service.resume(actors[1])
    assert helper is not None and helper.step == 4

    pending = await service.propose_group_combat(actors[0], leader.state_version)
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision, quest_id=S32_ID
    )
    assert started is not None and started.combat is not None and started.group_size == 2
    assert started.combat.variant is None
    enemy = [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemy) == 1 and enemy[0].level == 54
    await _seed_enemy_at_one_hp(database, started.encounter_id)
    views = {actor: await mission.resume(actor, S32_ID) for actor in actors}
    combat = next(view.combat for view in views.values() if view is not None)
    active_actor = next(
        actor
        for actor, view in views.items()
        if view is not None and view.combat_actor_key == active_player_key(combat)
    )
    active_view = views[active_actor]
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    result = await mission.action(
        active_actor, active_view.activity_id, combat.version, "attack"
    )
    assert result is not None and result.step == 5
    for actor in actors:
        resumed = await mission.resume(actor, S32_ID)
        assert resumed is not None and resumed.step == 5
    async with sessions() as session:
        for actor in actors:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S32_ID,
                    CampaignObjectiveCredit.objective_id == "s32.aranha_defeated",
                )
            ) is not None
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S32_MISSION_ID,
                )
            ) is None
