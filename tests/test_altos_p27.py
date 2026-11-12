from collections import Counter
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P26_CONTENT_VERSION,
    P27_CONTENT_VERSION,
    P27_ID,
    P27_MISSION_ID,
    P27_REWARD_OPTIONS,
    P27_TITLE,
    AltosMissionService,
    AltosMissionView,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    ALTOS_REGION_ID,
    CODEX_FRAGMENTS,
    CREATURE_PRESENTATION,
    LOCATION_LABELS,
)
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.round import RoundService
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.domain.road import (
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_DUNGEON_UNLOCK,
    ALTOS_PEDREIRAS_EXPLORATION_PROFILE,
    ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
    ALTOS_PEDREIRAS_HUNT_UNLOCK,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_PEDREIRAS_PROFILE,
    ALTOS_PEDREIRAS_ROUND_UNLOCK,
    ALTOS_PONTES_ACCESS_UNLOCK,
    ALTOS_PONTES_LOCATION,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    EquipmentItem,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import disable_round_pvpve_for_test, start_manual_hunt_after_no_match
from tests.test_altos_p26 import _seed_p26_character
from tests.test_s4_s5_integration import _terminal


async def _seed_p27_character(
    database,
    actor: int,
    *,
    level: int = 45,
    p26_status: str | None = "completed",
):
    actor, road, sessions = await _seed_p26_character(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = ALTOS_ABRIGO_LABEL
        if p26_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P26",
                    title="Ordens de Emergência",
                    status=p26_status,
                    step=8 if p26_status == "completed" else 3,
                    content_version=P26_CONTENT_VERSION,
                    progress={"completed": p26_status == "completed"},
                )
            )
        if p26_status == "completed":
            session.add_all(
                (
                    Unlock(
                        character_id=character.id,
                        unlock_id=ALTOS_PONTES_ACCESS_UNLOCK,
                    ),
                    LocationDiscovery(
                        character_id=character.id,
                        location_id=ALTOS_PONTES_LOCATION,
                    ),
                )
            )
    return actor, road, sessions


def test_p27_pedreiras_profiles_and_reward_choice_ui_match_the_final_source():
    assert ALTOS_PEDREIRAS_PROFILE.creature_weights == (
        ("creature.altos.escaravelho_basalto", 18),
        ("creature.altos.carneiro_peso", 16),
        ("creature.altos.lagarto_escoria", 22),
        ("creature.altos.morcego_chamine", 17),
        ("creature.altos.carcaca_mineral", 21),
        ("elite.altos.quebra_escarpas", 2),
        ("elite.altos.devorador_escoria", 4),
    )
    assert sum(weight for _, weight in ALTOS_PEDREIRAS_PROFILE.creature_weights) == 100
    assert ALTOS_PEDREIRAS_PROFILE.variant_chance == 16
    assert ALTOS_PEDREIRAS_PROFILE.hunt_unlock == ALTOS_PEDREIRAS_HUNT_UNLOCK
    assert ALTOS_PEDREIRAS_PROFILE.explore_unlock == ALTOS_PEDREIRAS_EXPLORE_UNLOCK
    assert ALTOS_PEDREIRAS_PROFILE.round_familiarity == ALTOS_PEDREIRAS_ROUND_UNLOCK
    assert (creature_for("creature.altos.carcaca_mineral").unlock_level,
            creature_for("creature.altos.carcaca_mineral").max_level) == (45, 49)
    assert LOCATION_LABELS[ALTOS_PEDREIRAS_LOCATION] == ALTOS_PEDREIRAS_LABEL
    for creature_id in (
        "creature.altos.morcego_chamine",
        "creature.altos.carcaca_mineral",
    ):
        presentation = CREATURE_PRESENTATION[creature_id]
        assert presentation.region_id == ALTOS_REGION_ID
        assert presentation.habitats == (ALTOS_PEDREIRAS_LOCATION,)
    assert CODEX_FRAGMENTS[
        "explore.altos.pedreiras.mapa_extracao"
    ].title == "Mapa de Extração Recortado"
    assert (
        ACHIEVEMENT_BY_ID["achievement.altos.continuidade_custo"].name
        == "Continuidade a Qualquer Custo"
    )

    profile = EXPLORATION_PROFILES[ALTOS_PEDREIRAS_LOCATION]
    assert profile is ALTOS_PEDREIRAS_EXPLORATION_PROFILE
    discoveries = {
        result.result_id: (result.weight, result.unique)
        for result in profile.results
        if result.category == "great_discovery"
    }
    assert discoveries == {
        "explore.altos.pedreiras.braseiro_pedreira_velha": (50, True),
        "explore.altos.pedreiras.entrada_contrapeso": (50, True),
    }
    assert EXPLORATION_PROFILES[ALTOS_PEDREIRAS_LOCATION].results[2].result_id == (
        "explore.altos.pedreiras.mapa_extracao"
    )
    assert HUNT_PROFILES[ALTOS_PEDREIRAS_LOCATION] is ALTOS_PEDREIRAS_PROFILE

    view = AltosMissionView(
        character_id=uuid4(),
        quest_id=P27_ID,
        title=P27_TITLE,
        kind="mission",
        status="active",
        step=7,
        state_version=12,
        progress={"codex_recorded": True},
        location=ALTOS_PEDREIRAS_LABEL,
        level=45,
    )
    rendered = render_altos_mission(view)
    callbacks = {
        button.callback_data
        for row in rendered.keyboard.inline_keyboard
        for button in row
    }
    assert callbacks == {
        f"altos:choice:P27:12:{key}" for key in P27_REWARD_OPTIONS
    } | {"world:missions"}


@pytest.mark.parametrize(
    ("location", "label", "callback"),
    (
        (ALTOS_ABRIGO_LABEL, "Seguir para Pontes de Fuligem", "road:route:altos_pontes"),
        (
            ALTOS_PONTES_LABEL,
            "Seguir para Pedreiras Suspensas",
            "road:route:altos_pedreiras",
        ),
    ),
)
def test_p27_step_one_routes_through_the_adjacent_public_edge(location, label, callback):
    view = AltosMissionView(
        character_id=uuid4(),
        quest_id=P27_ID,
        title=P27_TITLE,
        kind="mission",
        status="active",
        step=1,
        state_version=1,
        progress={},
        location=location,
        level=45,
    )

    screen = render_altos_mission(view)
    buttons = [
        button
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]

    assert any(button.text == label and button.callback_data == callback for button in buttons)
    assert callback in {button.callback_data for button in buttons}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p26_status", "expected_status"),
    ((45, None, "blocked"), (44, "completed", "suspended"), (45, "active", "blocked")),
)
async def test_p27_requires_completed_p26_and_level_45(
    database, level, p26_status, expected_status
):
    actor, road, sessions = await _seed_p27_character(
        database, 781270 + level + (0 if p26_status is None else len(p26_status)),
        level=level,
        p26_status=p26_status,
    )
    mission = AltosMissionService(sessions, "ocaso")
    if expected_status == "suspended":
        offer = await mission.resume_active(actor)
        assert offer is not None and offer.quest_id == P27_ID
        assert offer.status == "suspended"
        suspended = await mission.start_p27(actor)
        assert suspended is not None and suspended.status == "suspended"
    else:
        assert await mission.start_p27(actor) is None

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_PEDREIRAS_ACCESS_UNLOCK,
            )
        ) is None
    if p26_status == "completed":
        assert await road.travel_route(actor, ALTOS_PONTES_LABEL) is not None
        assert await road.travel_route(actor, ALTOS_PEDREIRAS_LABEL) is None


@pytest.mark.asyncio
async def test_p27_solo_progress_rewards_and_local_round_gate(database, monkeypatch):
    import asterion.application.road as road_module
    import asterion.application.scripted_combat as scripted_combat

    actor, road, sessions = await _seed_p27_character(database, 781275)
    mission = AltosMissionService(sessions, "ocaso")
    initial = await mission.start_p27(actor)
    assert initial is not None and initial.status == "active" and initial.step == 1

    assert await road.travel_route(actor, ALTOS_PONTES_LABEL) is not None
    assert await road.travel_route(actor, ALTOS_PEDREIRAS_LABEL) is not None
    view = await mission.resume_active(actor)
    assert view is not None and view.step == 2 and view.location == ALTOS_PEDREIRAS_LABEL
    assert ALTOS_PEDREIRAS_LABEL in await mission.known_locations(actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        xp_before = character.xp
        crowns_before = character.crowns
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                )
            ).all()
        )
        assert ALTOS_PEDREIRAS_ACCESS_UNLOCK in unlocks
        assert ALTOS_PEDREIRAS_HUNT_UNLOCK not in unlocks
        assert ALTOS_PEDREIRAS_EXPLORE_UNLOCK not in unlocks
        assert ALTOS_PEDREIRAS_ROUND_UNLOCK not in unlocks
        assert ALTOS_PEDREIRAS_DUNGEON_UNLOCK not in unlocks

    local = await road.resume(actor)
    assert local is not None and not local.hunt_enabled and not local.explore_enabled
    assert await road.start_hunt(actor) is None
    assert await road.explore(actor) is None

    for action in (
        "inspect_block_route",
        "inspect_cable_record",
        "inspect_distribution_table",
    ):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    assert view.step == 3

    scripted = await mission.start_solo_combat(actor, view.state_version, P27_ID)
    assert scripted is not None and scripted.kind == "combat" and scripted.combat is not None
    assert scripted.combat.fighters["enemy"].level == 45
    assert scripted.combat.fighters["enemy"].name == "Carcaça Mineral"
    assert scripted.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, scripted.activity_id, scripted.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp == xp_before
        assert character.crowns == crowns_before

    view = await mission.advance(actor, victory.state_version, "recover_priority_plate")
    assert view is not None and view.step == 5
    view = await mission.advance(
        actor, view.state_version, "compare_plate_with_doren_and_rava"
    )
    assert view is not None and view.step == 6
    view = await mission.advance(actor, view.state_version, "record_priorities_codex")
    assert view is not None and view.step == 7
    assert view.progress["codex_recorded"] is True
    choice_version = view.state_version
    screen = render_altos_mission(view)
    choice_callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("altos:choice:P27:")
    }
    assert choice_callbacks == {
        f"altos:choice:P27:{choice_version}:{key}" for key in P27_REWARD_OPTIONS
    }

    chosen_key = "selo_carga_compartilhada"
    item_id, item_name, slot = P27_REWARD_OPTIONS[chosen_key]
    completed = await mission.choose_p27_reward(actor, choice_version, chosen_key)
    assert completed is not None and completed.status == "completed"
    retried = await mission.choose_p27_reward(
        actor, choice_version, "capuz_vento_preso"
    )
    assert retried is not None and retried.status == "completed"
    assert retried.progress["reward_item_id"] == item_id

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp - xp_before == 62_400
        assert character.crowns - crowns_before == 780
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P27_MISSION_ID,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 62_400): 1,
                ("crowns", None, 780): 1,
                ("equipment", item_id, 1): 1,
            }
        )
        selected_payload = next(row.payload for row in components if row.kind == "equipment")
        assert selected_payload["item_name"] == item_name
        assert selected_payload["slot"] == slot
        assert selected_payload["item_level"] == 45
        assert selected_payload["rarity"] == "Raro"
        assert selected_payload["enhancement"] == 0
        assert selected_payload["bound"] is True
        items = (
            await session.scalars(
                select(EquipmentItem).where(
                    EquipmentItem.character_id == character.id,
                    EquipmentItem.source_key == f"{P27_MISSION_ID}:equipment",
                )
            )
        ).all()
        assert len(items) == 1
        assert (items[0].item_name, items[0].rarity, items[0].slot, items[0].item_level) == (
            item_name,
            "Raro",
            slot,
            45,
        )
        assert items[0].bound is True
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == "codex.altos.prioridades_carga",
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == "achievement.altos.continuidade_custo",
            )
        ) is not None
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(Unlock.character_id == character.id)
                )
            ).all()
        )
        assert {
            ALTOS_PEDREIRAS_ACCESS_UNLOCK,
            ALTOS_PEDREIRAS_HUNT_UNLOCK,
            ALTOS_PEDREIRAS_EXPLORE_UNLOCK,
            "narrative.altos.prioridades_confirmadas",
        } <= unlocks
        assert ALTOS_PEDREIRAS_ROUND_UNLOCK not in unlocks
        assert ALTOS_PEDREIRAS_DUNGEON_UNLOCK not in unlocks
        assert "unlock.location.altos.bastilha_carga" not in unlocks
        assert "unlock.location.altos.coracao_colosso" not in unlocks
        assert await session.scalar(
            select(Brazier.id).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "bonfire.altos.pedreira_velha",
            )
        ) is None

    unlocked = await road.resume(actor)
    assert unlocked is not None and unlocked.hunt_enabled and unlocked.explore_enabled
    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked = await rounds.prepare_round(actor, 5)
    assert blocked is None or blocked.kind != "round_prepare"

    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    hunt = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert hunt is not None and hunt.combat is not None
    victory = await road.action(actor, hunt.activity_id, hunt.combat.version, "attack")
    assert victory is not None and victory.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_PEDREIRAS_ROUND_UNLOCK,
            )
        ) is not None
    prepared = await rounds.prepare_round(actor, 5)
    assert prepared is not None and prepared.kind == "round_prepare"


@pytest.mark.asyncio
async def test_p27_pedreira_brazier_and_dungeon_entry_are_distinct_discoveries(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actors = (781280, 781281)
    seeded = [await _seed_p27_character(database, actor) for actor in actors]
    sessions = seeded[0][2]
    async with sessions.begin() as session:
        characters = list(
            (
                await session.scalars(
                    select(Character).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        by_actor = {character.telegram_id: character for character in characters}
        for actor in actors:
            character = by_actor[actor]
            character.vigor = 50
            world = await session.get(WorldState, character.id)
            assert world is not None
            world.region = ALTOS_REGION_LABEL
            world.location = ALTOS_PEDREIRAS_LABEL
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P27_ID,
                    title=P27_TITLE,
                    status="completed",
                    step=7,
                    content_version=P27_CONTENT_VERSION,
                    progress={"completed": True, "reward_item_id": "already-settled"},
                )
            )
            session.add_all(
                (
                    LocationDiscovery(
                        character_id=character.id,
                        location_id=ALTOS_PEDREIRAS_LOCATION,
                    ),
                    Unlock(character_id=character.id, unlock_id=ALTOS_PEDREIRAS_ACCESS_UNLOCK),
                    Unlock(character_id=character.id, unlock_id=ALTOS_PEDREIRAS_HUNT_UNLOCK),
                    Unlock(character_id=character.id, unlock_id=ALTOS_PEDREIRAS_EXPLORE_UNLOCK),
                )
            )

    outcomes = (
        (
            "explore.altos.pedreiras.braseiro_pedreira_velha",
            "bonfire.altos.pedreira_velha",
            ALTOS_PEDREIRAS_DUNGEON_UNLOCK,
        ),
        (
            "explore.altos.pedreiras.entrada_contrapeso",
            ALTOS_PEDREIRAS_DUNGEON_UNLOCK,
            "bonfire.altos.pedreira_velha",
        ),
    )
    for (actor, road, _), (result_id, expected_id, absent_id) in zip(
        seeded, outcomes, strict=True
    ):
        monkeypatch.setattr(
            road_module,
            "_explore_result",
            lambda *_args, _result_id=result_id, **_kwargs: (
                "great_discovery",
                _result_id,
                "Descoberta registrada.",
            ),
        )
        attempt = await road.explore(actor)
        assert attempt is not None and attempt.attempt_id is not None
        await road.acknowledge_result(actor, attempt.attempt_id)
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            if expected_id.startswith("bonfire."):
                assert await session.scalar(
                    select(Brazier.id).where(
                        Brazier.character_id == character.id,
                        Brazier.brazier_id == expected_id,
                    )
                ) is not None
            else:
                assert await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == expected_id,
                    )
                ) is not None
            if absent_id.startswith("bonfire."):
                assert await session.scalar(
                    select(Brazier.id).where(
                        Brazier.character_id == character.id,
                        Brazier.brazier_id == absent_id,
                    )
                ) is None
            else:
                assert await session.scalar(
                    select(Unlock.id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id == absent_id,
                    )
                ) is None


@pytest.mark.asyncio
async def test_p27_group_member_advances_alone_and_scripted_combat_is_solo(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat


    actors = (781282, 781283)
    seeded = [await _seed_p27_character(database, actor) for actor in actors]
    sessions = seeded[0][2]
    async with sessions() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    roads = {actor: road for actor, road, _ in seeded}
    for actor in actors:
        started = await mission.start_p27(actor)
        assert started is not None and started.step == 1
        assert await roads[actor].travel_route(actor, ALTOS_PONTES_LABEL) is not None
        assert await roads[actor].travel_route(actor, ALTOS_PEDREIRAS_LABEL) is not None
        arrived = await mission.resume_active(actor)
        assert arrived is not None and arrived.step == 2

    view = await mission.resume_active(actors[0])
    assert view is not None
    view = await mission.advance(actors[0], view.state_version, "inspect_block_route")
    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 2.
    helper_view = await mission.resume_active(actors[1])
    assert helper_view is not None and helper_view.step == 2
    assert not helper_view.progress.get("pedreira_records")
    for action in ("inspect_cable_record", "inspect_distribution_table"):
        view = await mission.advance(actors[0], view.state_version, action)
        assert view is not None
    assert view.step == 3
    assert (await mission.resume_active(actors[1])).step == 2

    # P27 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await mission.propose_group_combat(actors[0], view.state_version, P27_ID)
    assert not await groups.activity_proposals(actors[0])
    started = await mission.start_solo_combat(actors[0], view.state_version, P27_ID)
    assert started is not None and started.combat is not None
    assert started.group_size == 1 and not started.combat.party_mode
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actors[0], started.activity_id, started.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4
    assert (await mission.resume_active(actors[1])).step == 2

    shared = await mission.advance(actors[0], victory.state_version, "recover_priority_plate")
    assert shared is not None and shared.step == 5
    personal = await mission.advance(
        actors[0], shared.state_version, "compare_plate_with_doren_and_rava"
    )
    assert personal is not None and personal.step == 6
    helper_after = await mission.resume_active(actors[1])
    assert helper_after is not None and helper_after.step == 2

    async with sessions() as session:
        character_ids = set(
            (
                await session.scalars(
                    select(Character.id).where(Character.telegram_id.in_(actors))
                )
            ).all()
        )
        credits = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == P27_ID,
                    CampaignObjectiveCredit.objective_id == "p27.inspect_block_route",
                )
            )
        ).all()
        assert len(credits) == 1
        assert {row.character_id for row in credits} == {personal.character_id}
        comparisons = (
            await session.scalars(
                select(CampaignObjectiveCredit).where(
                    CampaignObjectiveCredit.character_id.in_(character_ids),
                    CampaignObjectiveCredit.quest_id == P27_ID,
                    CampaignObjectiveCredit.objective_id == "p27.plate_compared",
                )
            )
        ).all()
        assert len(comparisons) == 1
        assert comparisons[0].character_id == personal.character_id
