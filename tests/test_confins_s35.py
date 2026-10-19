import asyncio
from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P25_COMBAT,
    P34_CONTENT_VERSION,
    P34_ID,
    P35_CONTENT_VERSION,
    P35_ID,
    S35_ID,
    AltosMissionService,
)
from asterion.application.groups import GroupService
from asterion.application.road import (
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    CONFINS_ULTIMO_REFUGIO_LABEL,
)
from asterion.application.s35 import (
    S35_CODEX_ENTRY,
    S35_COMPLETION_UNLOCK,
    S35_CONTENT_VERSION,
    S35_EVIDENCE,
    S35_MISSION_ID,
    S35_ORDERS,
    S35Service,
)
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.s35_ui import render_s35
from asterion.domain.road import CONFINS_VIGIA_DESFASADO, creature_for
from asterion.infrastructure.db.models import (
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_campaign_coop_integration import _seed_enemy_at_one_hp
from tests.test_confins_p34 import _seed_p34_actor
from tests.test_s4_s5_integration import _terminal


async def _seed_s35_actor(
    database,
    actor: int,
    *,
    level: int = 58,
    p34_status: str | None = "completed",
    location: str = CONFINS_NO_CENTRAL_LABEL,
):
    actor, _road, sessions = await _seed_p34_actor(database, actor, level=level)
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
        if p34_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P34_ID,
                    title="A Âncora Central",
                    status=p34_status,
                    step=6 if p34_status == "completed" else 3,
                    content_version=P34_CONTENT_VERSION,
                    state_version=6 if p34_status == "completed" else 3,
                    progress={"completed": p34_status == "completed"},
                )
            )
        if location == CONFINS_NO_CENTRAL_LABEL:
            session.add(
                LocationDiscovery(
                    character_id=character.id,
                    location_id="location.confins.no_central",
                )
            )
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id="unlock.location.confins.no_central",
                )
            )
    mission = AltosMissionService(sessions, "ocaso")
    return actor, sessions, mission, S35Service(sessions, "ocaso", mission)


async def _collect_all_s35_evidence(
    service: S35Service,
    actor: int,
    *,
    present_group_actors: tuple[int, ...] = (),
):
    view = await service.accept(actor, 0)
    assert view is not None and view.status == "active" and view.step == 2
    view = await service.advance(actor, view.state_version, "inspect_seal_a")
    assert view is not None and view.evidence == (S35_EVIDENCE[0],)
    # The second seal and transmission trail are at the already-open Last Refuge.
    async with service.sessions.begin() as session:
        actors = present_group_actors or (actor,)
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        for character in characters:
            world = await session.get(WorldState, character.id)
            assert world is not None
            world.location = CONFINS_ULTIMO_REFUGIO_LABEL
    view = await service.resume(actor)
    assert view is not None and view.step == 2
    view = await service.advance(actor, view.state_version, "inspect_seal_b")
    assert view is not None and set(view.evidence) == set(S35_EVIDENCE[:2])
    view = await service.advance(actor, view.state_version, "inspect_transmission")
    assert view is not None and set(view.evidence) == set(S35_EVIDENCE)
    assert view.step == 3
    return view


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p34_status", "eligible"),
    ((58, None, False), (58, "active", False), (57, "completed", False), (58, "completed", True)),
)
async def test_s35_gate_offer_does_not_accept_and_has_no_later_campaign_dependency(
    database, level, p34_status, eligible
):
    actor, sessions, _mission, service = await _seed_s35_actor(
        database,
        834000 + level + (p34_status == "active") + (p34_status is None) * 2,
        level=level,
        p34_status=p34_status,
    )
    offer = await service.offer(actor)
    assert offer is not None and offer.available is eligible
    assert offer.status == "unaccepted"
    if eligible:
        screen = render_s35(offer)
        assert "P34 concluída" in screen.text and "Nv.58" in screen.text
        callbacks = {
            button.callback_data
            for row in screen.keyboard.inline_keyboard
            for button in row
        }
        assert "s35:accept:0" in callbacks
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == S35_ID
            )
        ) is None
        # P35/P36 and S31-S33 are intentionally absent; none is a gate.
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id.in_(
                    ("P35", "P36", "S31", "S32", "S33")
                ),
            )
        ) is None
    if eligible:
        accepted = await service.accept(actor, offer.state_version)
        assert accepted is not None and accepted.status == "active"
        assert accepted.step == 2
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            copies = (
                await session.scalars(
                    select(CampaignObjectiveCredit.source_key).where(
                        CampaignObjectiveCredit.character_id == character.id,
                        CampaignObjectiveCredit.quest_id == S35_ID,
                        CampaignObjectiveCredit.objective_id == "s35.official_order_copy",
                    )
                )
            ).all()
            assert set(copies) == set(S35_ORDERS)


@pytest.mark.asyncio
async def test_s35_integrated_scripted_retry_codex_and_reward_are_idempotent(
    database, monkeypatch
):
    actor, sessions, mission, service = await _seed_s35_actor(
        database, 834020, level=60
    )
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character_id = character.id
        starting_crowns = character.crowns
        world = await session.get(WorldState, character.id)
        assert world is not None
        initial_world = (world.region, world.location)

    view = await _collect_all_s35_evidence(service, actor)
    # The helper moves through the already-open Node to collect the remaining evidence.
    initial_world = (initial_world[0], CONFINS_ULTIMO_REFUGIO_LABEL)
    duplicate = await service.advance(
        actor, view.state_version, "inspect_transmission"
    )
    assert duplicate is not None and set(duplicate.evidence) == set(S35_EVIDENCE)
    assert P25_COMBAT[S35_ID][3:] == (
        CONFINS_VIGIA_DESFASADO,
        58,
        "uncommon",
    )
    normal = creature_for(CONFINS_VIGIA_DESFASADO)
    assert (normal.unlock_level, normal.max_level) == (58, 60)

    battle = await service.start_solo_combat(actor, view.state_version)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    enemies = [fighter for fighter in battle.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1
    assert enemies[0].level == 58
    assert battle.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await mission.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 3
    recovered = await service.resume(actor)
    assert recovered is not None and recovered.step == 3
    assert recovered.progress["awaiting_retry"] is True
    retry = await service.retry_combat(actor, defeated.state_version)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    enemies = [fighter for fighter in retry.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1 and enemies[0].level == 58
    assert retry.combat.variant is None

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S35_MISSION_ID,
            )
        ) is None

    reconciled = await service.advance(actor, victory.state_version, "compare_official_orders")
    assert reconciled is not None and reconciled.step == 5
    codex = await service.advance(actor, reconciled.state_version, "record_codex")
    assert codex is not None and codex.codex_owned and codex.codex_recorded
    results = await asyncio.gather(
        service.advance(actor, codex.state_version, "conclude_with_roven"),
        service.advance(actor, codex.state_version, "conclude_with_roven"),
    )
    assert all(result is not None and result.status == "completed" for result in results)
    duplicate_conclusion = await service.advance(
        actor, codex.state_version, "conclude_with_roven"
    )
    assert duplicate_conclusion is not None and duplicate_conclusion.status == "completed"

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.level == 60 and character.xp == 0
        assert character.crowns == starting_crowns + 730
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S35_MISSION_ID,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert Counter(
            (row.kind, row.item_id, row.quantity, row.payload.get("bound") if row.payload else None)
            for row in components
        ) == Counter(
            {
                ("xp", None, 67_270, None): 1,
                ("crowns", None, 730, None): 1,
                ("material", "material.confins.ferro_baliza", 1, True): 1,
                ("material", "material.confins.musgo_limiar", 1, True): 2,
                ("material", "material.confins.po_referencia", 1, True): 1,
            }
        )
        stacks = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        assert Counter(
            (stack.material_id, stack.quantity, stack.bound) for stack in stacks
        ) >= Counter(
            (material_id, quantity, True)
            for material_id, quantity in (
                ("material.confins.ferro_baliza", 1),
                ("material.confins.musgo_limiar", 2),
                ("material.confins.po_referencia", 1),
            )
        )
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == S35_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == S35_CODEX_ENTRY,
                CodexFragment.fragment_id == S35_CODEX_ENTRY,
            )
        ) is not None
        completed = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id,
                Quest.quest_id == S35_ID,
                Quest.content_version == S35_CONTENT_VERSION,
            )
        )
        assert completed is not None and completed.status == "completed"
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == S35_COMPLETION_UNLOCK,
            )
        ) is not None
        world = await session.get(WorldState, character_id)
        assert world is not None and (world.region, world.location) == initial_world
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id != S35_MISSION_ID,
            )
        ) is None
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == S35_ID,
                    CampaignObjectiveCredit.objective_id == "s35.field_evidence",
                )
            )
        ).all()
        assert Counter(row.source_key for row in credits) == Counter(S35_EVIDENCE)
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id.in_(
                    (
                        "unlock.location.confins.camara_regencia",
                        "unlock.hunt.confins.no",
                        "unlock.explore.confins.no",
                        "unlock.round.confins.no",
                        "unlock.dungeon.confins.camara_contradicoes",
                    )
                ),
            )
        ) is None

    # S35 completed at level 60 is recognized as context by P35 without skipping its own work.
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = CONFINS_NO_CENTRAL_LABEL
    p35 = await mission.start_p35(actor)
    assert p35 is not None and p35.quest_id == P35_ID and p35.step == 1
    assert p35.progress["s35_contextual_knowledge_available"] is True
    assert p35.progress["completed_steps"] == []
    p35_screen = render_altos_mission(p35)
    assert "duas ordens oficiais incompatíveis" in p35_screen.text
    assert "não substitui as três cadeias documentais" in p35_screen.text
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == "mission.confins.p35",
            )
        ) is None


@pytest.mark.asyncio
async def test_s35_remains_available_after_p35_and_does_not_mutate_it(database):
    actor, sessions, mission, service = await _seed_s35_actor(database, 834025, level=60)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        p35 = Quest(
            character_id=character.id,
            quest_id=P35_ID,
            title="A Noite da Convergência",
            status="completed",
            step=8,
            content_version=P35_CONTENT_VERSION,
            state_version=8,
            progress={"completed": True, "completed_steps": list(range(1, 9))},
        )
        session.add(p35)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        p35 = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == P35_ID,
            )
        )
        assert p35 is not None and p35.status == "completed"
        assert p35.progress["completed_steps"] == list(range(1, 9))


@pytest.mark.asyncio
async def test_s35_abandon_reaccept_preserves_unique_evidence_without_progress_duplication(
    database,
):
    actor, sessions, _mission, service = await _seed_s35_actor(database, 834030)
    accepted = await service.accept(actor, 0)
    assert accepted is not None
    first = await service.advance(actor, accepted.state_version, "inspect_seal_a")
    assert first is not None and first.evidence == (S35_EVIDENCE[0],)
    abandoned = await service.abandon(actor, first.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    resumed = await service.accept(actor, abandoned.state_version, reaccept=True)
    assert resumed is not None and resumed.status == "active" and resumed.step == 2
    assert resumed.evidence == (S35_EVIDENCE[0],)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S35_ID,
                    CampaignObjectiveCredit.objective_id == "s35.field_evidence",
                )
            )
        ).all()
        assert [credit.source_key for credit in credits] == [S35_EVIDENCE[0]]


@pytest.mark.asyncio
async def test_s35_shared_evidence_requires_acceptance_presence_and_individual_gate(database):
    actors = (834040, 834041)
    await _seed_s35_actor(database, actors[0], location=CONFINS_NO_CENTRAL_LABEL)
    _second, sessions, _mission, _service = await _seed_s35_actor(
        database, actors[1], location=CONFINS_NO_CENTRAL_LABEL
    )
    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        name_by_actor = {character.telegram_id: character.name for character in characters}
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], name_by_actor[actors[1]], expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S35Service(sessions, "ocaso", mission)
    first = await service.accept(actors[0], 0)
    assert first is not None
    # Presence in the Group does not accept S35 for the other character.
    async with sessions() as session:
        second = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert second is not None
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == second.id, Quest.quest_id == S35_ID)
        ) is None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == second.id,
                CampaignObjectiveCredit.quest_id == S35_ID,
                CampaignObjectiveCredit.objective_id == "s35.field_evidence",
            )
        ) is None
    second = await service.accept(actors[1], 0)
    assert second is not None and second.step == 2 and second.evidence == ()
    # Recheck P34 for each participant when shared evidence is committed.
    async with sessions.begin() as session:
        second_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert second_character is not None
        p34 = await session.scalar(
            select(Quest).where(
                Quest.character_id == second_character.id,
                Quest.quest_id == P34_ID,
            )
        )
        assert p34 is not None
        p34.status = "active"
    first = await service.advance(actors[0], first.state_version, "inspect_seal_a")
    assert first is not None and first.evidence == (S35_EVIDENCE[0],)
    async with sessions() as session:
        second_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert second_character is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == second_character.id,
                CampaignObjectiveCredit.quest_id == S35_ID,
                CampaignObjectiveCredit.objective_id == "s35.field_evidence",
            )
        ) is None


@pytest.mark.asyncio
async def test_s35_shared_scripted_victory_credits_only_present_eligible_participants(
    database, monkeypatch
):
    from asterion.domain.combat import active_player_key

    actors = (834050, 834051)
    await _seed_s35_actor(database, actors[0])
    _second, sessions, _mission, _service = await _seed_s35_actor(database, actors[1])
    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        name_by_actor = {character.telegram_id: character.name for character in characters}
        ids_by_actor = {character.telegram_id: character.id for character in characters}
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], name_by_actor[actors[1]], expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    service = S35Service(sessions, "ocaso", mission)
    for actor in actors:
        assert await service.accept(actor, 0) is not None
    leader = await _collect_all_s35_evidence(
        service, actors[0], present_group_actors=actors
    )
    proposal_view = await service.propose_group_combat(actors[0], leader.state_version)
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], proposal_view.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision, quest_id=S35_ID
    )
    assert started is not None and started.combat is not None and started.group_size == 2
    assert started.combat.variant is None
    enemies = [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    assert len(enemies) == 1 and enemies[0].level == 58
    await _seed_enemy_at_one_hp(database, started.encounter_id)
    views = {actor: await mission.resume(actor, S35_ID) for actor in actors}
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
    assert result is not None and result.step == 4
    for actor in actors:
        resumed = await service.resume(actor)
        assert resumed is not None and resumed.step == 4
        assert resumed.vigia_victory
    async with sessions() as session:
        for character_id in ids_by_actor.values():
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == S35_MISSION_ID,
                )
            ) is None
