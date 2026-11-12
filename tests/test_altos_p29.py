
import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P29_ACHIEVEMENT,
    P29_CODEX_ENTRY,
    P29_ID,
    P29_MISSION_ID,
    P29_NARRATIVE_UNLOCK,
    P29_TITLE,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
    LOCATION_LABELS,
)
from asterion.application.road import ALTOS_CORACAO_LABEL
from asterion.domain.road import (
    ALTOS_CORACAO_ACCESS_UNLOCK,
    ALTOS_CORACAO_LOCATION,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    RewardComponent,
    RewardEvent,
    Unlock,
)
from tests.test_altos_p28 import _seed_p28_character
from tests.test_s4_s5_integration import _terminal


@pytest.mark.asyncio
async def test_p29_is_unavailable_before_p28_completion(database):
    actor, _road, sessions = await _seed_p28_character(
        database, 781589, level=49, p28_status=None
    )
    mission = AltosMissionService(sessions, "ocaso")

    assert await mission.start_p29(actor) is None


@pytest.mark.asyncio
async def test_p29_requires_p28_and_suspends_until_level_49(database):
    actor, _road, sessions = await _seed_p28_character(
        database, 781590, level=48, p28_status="completed"
    )
    mission = AltosMissionService(sessions, "ocaso")

    suspended = await mission.start_p29(actor)
    assert suspended is not None
    assert (suspended.quest_id, suspended.status) == (P29_ID, "suspended")
    resumed = await mission.resume_active(actor)
    assert resumed is not None and resumed.status == "suspended"

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 49

    available = await mission.resume_active(actor)
    assert available is not None
    assert (available.quest_id, available.status, available.level) == (
        P29_ID,
        "available",
        49,
    )
    active = await mission.start_p29(actor)
    assert active is not None
    assert (active.quest_id, active.status, active.step) == (P29_ID, "active", 1)

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
            )
        ) is None

        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == "location.altos.coracao_colosso",
            )
        ) is None


@pytest.mark.asyncio
async def test_p29_shareable_steps_scripted_combat_and_personal_codex(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor, road, sessions = await _seed_p28_character(
        database, 781591, level=49, p28_status="completed"
    )
    mission = AltosMissionService(sessions, "ocaso")
    initial = await mission.start_p29(actor)
    assert initial is not None and initial.status == "active" and initial.step == 1
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        xp_before = character.xp
        crowns_before = character.crowns

    for record in ("priority_record_1", "priority_record_2", "priority_record_3"):
        previous_version = initial.state_version
        initial = await mission.advance(
            actor, initial.state_version, f"collect_{record}"
        )
        assert initial is not None
        assert initial.state_version > previous_version
    assert initial.step == 2
    assert len(initial.progress["priority_records"]) == 3

    initial = await mission.advance(
        actor, initial.state_version, "locate_convergence_order"
    )
    assert initial is not None and initial.step == 3
    initial = await mission.advance(
        actor, initial.state_version, "inspect_network_coupling_diagram"
    )
    assert initial is not None and initial.step == 4
    assert initial.progress["final_rupture_minutes_accessed"] is False

    scripted = await mission.start_solo_combat(
        actor, initial.state_version, P29_ID
    )
    assert scripted is not None and scripted.kind == "combat"
    assert scripted.combat is not None
    assert scripted.combat.fighters["enemy"].name == "Supervisor de Carga"
    assert scripted.combat.fighters["enemy"].level == 49
    assert scripted.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor,
        scripted.activity_id,
        scripted.combat.version,
        "attack",
    )
    assert victory is not None and victory.step == 5

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp, character.crowns) == (xp_before, crowns_before)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P29_MISSION_ID,
            )
        ) is None

    view = await mission.advance(
        actor,
        victory.state_version,
        "compare_documented_risks_with_sel_and_maro",
    )
    assert view is not None and view.step == 6
    codex = await mission.advance(
        actor, view.state_version, "record_convergence_codex"
    )
    assert codex is not None and codex.step == 7
    assert codex.progress["codex_recorded"] is True

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == P29_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == P29_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
            )
        ) is None

    completed = await mission.advance(
        actor, codex.state_version, "open_route_to_coracao"
    )
    assert completed is not None
    assert (completed.status, completed.step) == ("completed", 7)
    replayed = await mission.advance(
        actor, codex.state_version, "open_route_to_coracao"
    )
    assert replayed is not None and replayed.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.level == 49
        assert character.xp == xp_before + 72_000
        assert character.crowns == crowns_before + 1_050
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P29_NARRATIVE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == P29_ACHIEVEMENT,
            )
        ) is not None
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P29_MISSION_ID,
            )
        )
        assert event is not None
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P29_MISSION_ID,
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event.id
                )
            )
        ).all()
        assert {
            (component.kind, component.item_id, component.quantity)
            for component in components
        } == {
            ("xp", None, 72_000),
            ("crowns", None, 1_050),
            ("material", "material.altos.ferro_contrapeso", 2),
            ("material", "material.altos.liquen_pedreira", 1),
            ("material", "material.altos.cinza_basalto", 1),
        }

    assert await road.travel_route(actor, ALTOS_CORACAO_LABEL) is not None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == ALTOS_CORACAO_LOCATION,
            )
        ) is not None


@pytest.mark.asyncio
async def test_p29_group_members_play_the_mission_alone_and_in_solo_combat(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actors = (781592, 781593)
    seeded = [
        await _seed_p28_character(database, actor, level=49, p28_status="completed")
        for actor in actors
    ]
    sessions = seeded[0][2]
    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)

    for actor in actors:
        started = await mission.start_p29(actor)
        assert started is not None and started.status == "active" and started.step == 1

    async with sessions() as session:
        before = {
            row.telegram_id: (row.xp, row.crowns)
            for row in (
                await session.scalars(
                    select(Character).where(Character.telegram_id.in_(actors))
                )
            ).all()
        }

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))

    async def play_until_combat(actor):
        view = await mission.resume_active(actor)
        assert view is not None and view.step == 1
        for record in ("priority_record_1", "priority_record_2", "priority_record_3"):
            view = await mission.advance(actor, view.state_version, f"collect_{record}")
            assert view is not None
        view = await mission.advance(actor, view.state_version, "locate_convergence_order")
        assert view is not None and view.step == 3
        view = await mission.advance(
            actor, view.state_version, "inspect_network_coupling_diagram"
        )
        assert view is not None and view.step == 4
        return view

    async def finish(actor, view):
        started = await mission.start_solo_combat(actor, view.state_version, P29_ID)
        assert started is not None and started.combat is not None
        assert started.group_size == 1 and not started.combat.party_mode
        victory = await mission.action(
            actor, started.activity_id, started.combat.version, "attack"
        )
        assert victory is not None and victory.step == 5
        personal = await mission.advance(
            actor, victory.state_version, "compare_documented_risks_with_sel_and_maro"
        )
        assert personal is not None and personal.step == 6
        codex = await mission.advance(
            actor, personal.state_version, "record_convergence_codex"
        )
        assert codex is not None and codex.step == 7
        done = await mission.advance(actor, codex.state_version, "open_route_to_coracao")
        assert done is not None and done.status == "completed"

    # Objectives are Solo (Ação × Consequência §5): the leader advances alone.
    view = await play_until_combat(actors[0])
    helper_view = await mission.resume_active(actors[1])
    assert helper_view is not None and helper_view.step == 1
    assert not helper_view.progress.get("priority_records")

    # P29 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], view.state_version, P29_ID)
    assert not await groups.activity_proposals(actors[0])

    await finish(actors[0], view)
    async with sessions() as session:
        characters = (
            await session.scalars(
                select(Character).where(Character.telegram_id.in_(actors))
            )
        ).all()
        ids = {character.telegram_id: character.id for character in characters}
        assert {row.telegram_id: (row.xp, row.crowns) for row in characters}[
            actors[1]
        ] == before[actors[1]]
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == ids[actors[0]],
                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == ids[actors[1]],
                Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
            )
        ) is None
        assert not (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == ids[actors[1]],
                    RewardEvent.source_id == P29_MISSION_ID,
                )
            )
        ).all()
    helper_after = await mission.resume_active(actors[1])
    assert helper_after is not None and helper_after.step == 1

    # The other member does every earlier step alone, then the Solo fight.
    await finish(actors[1], await play_until_combat(actors[1]))
    async with sessions() as session:
        for actor in actors:
            assert await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == ids[actor],
                    Unlock.unlock_id == ALTOS_CORACAO_ACCESS_UNLOCK,
                )
            ) is not None
            assert len(
                (
                    await session.scalars(
                        select(RewardEvent).where(
                            RewardEvent.character_id == ids[actor],
                            RewardEvent.source_id == P29_MISSION_ID,
                        )
                    )
                ).all()
            ) == 1


def test_p29_catalog_entries_are_registered_without_p30_content():
    assert P29_TITLE == "Antes da Convergência"
    assert CODEX_BY_ID[P29_CODEX_ENTRY].location_id == "location.altos.bastilha_carga"
    text = CODEX_FRAGMENTS[P29_CODEX_ENTRY].text
    assert "recalibrar a rede" in text
    assert "probabilidade final de sucesso permanece desconhecida" in text
    assert P29_ACHIEVEMENT in ACHIEVEMENT_BY_ID
    assert ACHIEVEMENT_BY_ID[P29_ACHIEVEMENT].name == P29_TITLE
    assert LOCATION_LABELS[ALTOS_CORACAO_LOCATION] == "Coração do Colosso"
    assert ALTOS_CORACAO_LOCATION not in HUNT_PROFILES
    assert ALTOS_CORACAO_LOCATION not in EXPLORATION_PROFILES
