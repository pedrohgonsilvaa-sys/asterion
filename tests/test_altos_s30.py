from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P29_CONTENT_VERSION,
    P29_ID,
    S30_ID,
    AltosMissionService,
)
from asterion.application.knowledge_catalog import (
    ACHIEVEMENT_BY_ID,
    CODEX_FRAGMENTS,
)
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_BASTILHA_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.s28 import (
    S28_CODEX_ENTRY,
    S28_CONTENT_VERSION,
    S28_ID,
    S28_LETTER_FRAGMENTS,
)
from asterion.application.s30 import (
    S30_ACHIEVEMENT,
    S30_CODEX_ENTRY,
    S30_CONTENT_VERSION,
    S30_MISSION_ID,
    S30_PHYSICAL_SEALS,
    S30_REWARD_SOURCE,
    S30Service,
)
from asterion.domain.road import (
    ALTOS_BASTILHA_ACCESS_UNLOCK,
    ALTOS_CINZA_BASALTO,
    ALTOS_COURO_ESCARPA,
    ALTOS_CUSTODIO_ULTIMO_TURNO,
    ALTOS_FERRO_CONTRAPESO,
    ALTOS_LIQUEN_PEDREIRA,
    creature_for,
)
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    CampaignObjectiveCredit,
    CampaignSharedEncounter,
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
from tests.test_s4_s5_integration import _terminal


async def _seed_s30(
    database,
    actor: int,
    *,
    level: int = 50,
    s28_status: str | None = "completed",
    p29_status: str | None = "completed",
    has_bastilha_access: bool = True,
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
        world.location = ALTOS_BASTILHA_LABEL

        if s28_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=S28_ID,
                    title="Cartas de Emergência",
                    status=s28_status,
                    step=5 if s28_status == "completed" else 3,
                    content_version=S28_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed": s28_status == "completed"},
                )
            )
        if s28_status == "completed":
            session.add(CodexEntry(character_id=character.id, entry_id=S28_CODEX_ENTRY))
            session.add_all(
                CodexFragment(
                    character_id=character.id,
                    entry_id=S28_CODEX_ENTRY,
                    fragment_id=fragment_id,
                )
                for fragment_id in S28_LETTER_FRAGMENTS
            )
        if p29_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id=P29_ID,
                    title="Antes da Convergência",
                    status=p29_status,
                    step=7 if p29_status == "completed" else 5,
                    content_version=P29_CONTENT_VERSION,
                    state_version=0,
                    progress={"completed": p29_status == "completed"},
                )
            )
        if has_bastilha_access:
            session.add(
                Unlock(
                    character_id=character.id,
                    unlock_id=ALTOS_BASTILHA_ACCESS_UNLOCK,
                )
            )
    mission = AltosMissionService(sessions, "ocaso")
    return actor, road, sessions, mission, S30Service(
        sessions, "ocaso", road, mission
    )


async def _accept_s30(service: S30Service, actor: int):
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    return accepted


async def _advance(service: S30Service, actor: int, action: str, step: int):
    view = await service.resume(actor)
    assert view is not None and view.status == "active"
    result = await service.advance(actor, view.state_version, action)
    assert result is not None and result.step == step
    return result


async def _reach_s30_boss(service: S30Service, actor: int):
    view = await _accept_s30(service, actor)
    view = await service.advance(actor, view.state_version, "reconstruct_from_letters")
    assert view is not None and view.step == 2
    for index, action in enumerate(
        ("locate_seal_a", "locate_seal_b", "locate_seal_c")
    ):
        previous_version = view.state_version
        view = await service.advance(actor, previous_version, action)
        assert view is not None
        assert view.step == (3 if index == 2 else 2)
        assert len(view.physical_seals) == index + 1
        stale = await service.advance(actor, previous_version, action)
        assert stale is not None and stale.state_version == view.state_version
    view = await service.advance(actor, view.state_version, "authorize_service_post")
    assert view is not None and view.step == 4
    view = await service.advance(
        actor, view.state_version, "verify_no_current_civil_function"
    )
    assert view is not None and view.step == 5
    return view


@pytest.mark.asyncio
async def test_s30_requires_s28_p29_level_and_bastilha_access(database):
    actor, _road, _sessions, _mission, service = await _seed_s30(
        database, 793001, s28_status=None
    )
    assert not (await service.offer(actor)).available

    actor, _road, _sessions, _mission, service = await _seed_s30(
        database, 793002, p29_status="active"
    )
    assert not (await service.offer(actor)).available

    actor, _road, _sessions, _mission, service = await _seed_s30(
        database, 793003, level=49
    )
    assert not (await service.offer(actor)).available

    actor, _road, _sessions, _mission, service = await _seed_s30(
        database, 793004, has_bastilha_access=False
    )
    assert await service.offer(actor) is None

    actor, _road, sessions, _mission, service = await _seed_s30(database, 793005)
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        # S29 and P30 are deliberately absent; neither gates S30.
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id,
                Quest.quest_id.in_(("S29", "P30")),
            )
        ) is None


@pytest.mark.asyncio
async def test_s30_solo_boss_observations_codex_and_reward_are_idempotent(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor, _road, sessions, mission, service = await _seed_s30(database, 793010)
    original = await _reach_s30_boss(service, actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None
        location_before = (world.region, world.location)
        xp_before, crowns_before = character.xp, character.crowns
        inventory_before = {
            stack.material_id: stack.quantity
            for stack in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.bound.is_(True),
                    )
                )
            ).all()
        }

    opened = await service.resume(actor)
    assert opened is not None and opened.step == 5
    opened = await service.advance(actor, opened.state_version, "authorize_service_post")
    # A replayed action from a stale step cannot alter the personal mission or world state.
    assert opened is not None and opened.step == 5
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None and (world.region, world.location) == location_before

    combat_view = await mission.start_solo_combat(
        actor, original.state_version, S30_ID
    )
    assert combat_view is not None and combat_view.combat is not None
    combat = combat_view.combat
    boss = combat.fighters["enemy"]
    assert boss.name == "Custódio do Último Turno" and boss.level == 50
    assert boss.side == "enemy" and len(
        [fighter for fighter in combat.fighters.values() if fighter.side == "enemy"]
    ) == 1
    assert combat.variant is None
    assert set(combat.enemy_actions) == {
        "golpe_rotina",
        "ordem_vencida",
        "fecho_protocolo",
        "ultimo_turno",
    }
    assert combat.enemy_actions["golpe_rotina"].coefficient == Decimal("1.00")
    ordem = combat.enemy_actions["ordem_vencida"]
    assert (ordem.coefficient, ordem.attack_debuff, ordem.duration, ordem.cooldown) == (
        Decimal("0.90"),
        Decimal("0.10"),
        2,
        3,
    )
    assert ordem.effect_stat == "agility"
    assert combat.enemy_actions["fecho_protocolo"].coefficient == Decimal("1.25")
    ultimo = combat.enemy_actions["ultimo_turno"]
    assert (ultimo.coefficient, ultimo.prepared, ultimo.cooldown) == (
        Decimal("1.75"),
        True,
        4,
    )
    assert all(action.heal_coefficient == 0 for action in combat.enemy_actions.values())
    assert all(action.self_barrier_coefficient == 0 for action in combat.enemy_actions.values())
    assert all(
        not effect.hard_cc
        for action in combat.enemy_actions.values()
        for effect in (*action.self_effects, *action.target_effects)
    )

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, combat_view.activity_id, combat.version, "attack"
    )
    assert victory is not None and victory.quest_id == S30_ID and victory.step == 7
    assert victory.progress["awaiting_retry"] is False
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp == xp_before
        assert character.crowns == crowns_before
        boss_materials = {
            stack.material_id: stack.quantity
            for stack in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.bound.is_(True),
                    )
                )
            ).all()
        }
        assert boss_materials == inventory_before
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == ALTOS_CUSTODIO_ULTIMO_TURNO,
            )
        )
        assert entry is not None and entry.stage != "dominated"
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S30_REWARD_SOURCE,
            )
        ) is None

    bestiary_step = await service.advance(
        actor, victory.state_version, "record_bestiary_facts"
    )
    assert bestiary_step is not None and bestiary_step.step == 8
    codex_step = await service.advance(
        actor, bestiary_step.state_version, "record_codex"
    )
    assert codex_step is not None and codex_step.step == 9
    completed = await service.advance(
        actor, codex_step.state_version, "conclude_with_sel"
    )
    assert completed is not None and completed.status == "completed"
    replay = await service.advance(
        actor, codex_step.state_version, "conclude_with_sel"
    )
    assert replay is not None and replay.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        event_rows = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == S30_REWARD_SOURCE,
                )
            )
        ).all()
        assert len(event_rows) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(
                    RewardComponent.reward_event_id == event_rows[0].id
                )
            )
        ).all()
        assert {
            (component.kind, component.item_id, component.quantity)
            for component in components
        } == {
            ("xp", None, 74_500),
            ("crowns", None, 1_060),
            ("material", ALTOS_FERRO_CONTRAPESO, 2),
            ("material", ALTOS_COURO_ESCARPA, 2),
            ("material", ALTOS_LIQUEN_PEDREIRA, 2),
            ("material", ALTOS_CINZA_BASALTO, 2),
        }
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S30_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == S30_CODEX_ENTRY,
                CodexFragment.fragment_id == S30_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == S30_ACHIEVEMENT,
            )
        ) is not None
        assert character.xp >= xp_before + 74_500
        assert character.crowns == crowns_before + 1_060
        inventory_after = {
            stack.material_id: stack.quantity
            for stack in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.bound.is_(True),
                    )
                )
            ).all()
        }
        expected_materials = {
            ALTOS_FERRO_CONTRAPESO: 2,
            ALTOS_COURO_ESCARPA: 2,
            ALTOS_LIQUEN_PEDREIRA: 2,
            ALTOS_CINZA_BASALTO: 2,
        }
        for material_id, quantity in expected_materials.items():
            delta = inventory_after.get(material_id, 0) - inventory_before.get(material_id, 0)
            assert delta == quantity


@pytest.mark.asyncio
async def test_s30_boss_victory_survives_abandon_and_reaccept(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor, _road, sessions, mission, service = await _seed_s30(database, 793020)
    view = await _reach_s30_boss(service, actor)
    combat = await mission.start_solo_combat(actor, view.state_version, S30_ID)
    assert combat is not None and combat.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert victory is not None and victory.step == 7

    abandoned = await service.abandon(actor, victory.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    assert abandoned.boss_victory_recorded
    reaccepted = await service.accept(
        actor, abandoned.state_version, reaccept=True
    )
    assert reaccepted is not None and reaccepted.status == "active"
    assert reaccepted.step == 7 and reaccepted.boss_victory_recorded
    bestiary = await service.advance(
        actor, reaccepted.state_version, "record_bestiary_facts"
    )
    assert bestiary is not None and bestiary.step == 8
    codex = await service.advance(actor, bestiary.state_version, "record_codex")
    assert codex is not None and codex.step == 9
    completed = await service.advance(actor, codex.state_version, "conclude_with_sel")
    assert completed is not None and completed.status == "completed"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S30_REWARD_SOURCE,
            )
        ) is not None
        assert await session.scalar(
            select(CampaignObjectiveCredit.id).where(
                CampaignObjectiveCredit.character_id == character.id,
                CampaignObjectiveCredit.quest_id == S30_ID,
                CampaignObjectiveCredit.objective_id == "s30.custodian_defeated",
            )
        ) is not None


@pytest.mark.asyncio
async def test_s30_defeat_recovers_at_abrigo_and_allows_retry_without_reward(
    database, monkeypatch
):
    import asterion.application.scripted_combat as scripted_combat

    actor, _road, sessions, mission, service = await _seed_s30(database, 793030)
    view = await _reach_s30_boss(service, actor)
    combat = await mission.start_solo_combat(actor, view.state_version, S30_ID)
    assert combat is not None and combat.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await mission.action(
        actor, combat.activity_id, combat.combat.version, "defend"
    )
    assert defeat is not None and defeat.step == 5
    recovered = await service.resume(actor)
    assert recovered is not None and recovered.status == "active"
    assert recovered.location == ALTOS_ABRIGO_LABEL
    assert recovered.progress["awaiting_retry"] is True
    assert recovered.progress["recovery_brazier"]

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = ALTOS_REGION_LABEL
        world.location = ALTOS_BASTILHA_LABEL
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S30_REWARD_SOURCE,
            )
        ) is None

    retry = await mission.retry_combat(actor, recovered.state_version, S30_ID)
    assert retry is not None and retry.combat is not None
    assert retry.quest_id == S30_ID and retry.step == 5
    assert retry.combat.fighters["enemy"].name == "Custódio do Último Turno"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S30_REWARD_SOURCE,
            )
        ) is None


@pytest.mark.asyncio
async def test_s30_group_encounter_uses_campaign_boss_roster_scaling(database):
    actors = (793040, 793041)
    seeded = [await _seed_s30(database, actor) for actor in actors]
    sessions = seeded[0][2]
    for actor, _road, _sessions, _mission, service in seeded:
        await _reach_s30_boss(service, actor)

    async with sessions() as session:
        helper = await session.scalar(
            select(Character).where(Character.telegram_id == actors[1])
        )
        assert helper is not None
        helper_name = helper.name
    from asterion.application.groups import GroupService

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invitation = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[1], invitation.invite_id, expected_revision=invitation.revision, accept=True
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)
    lead = await mission.resume(actors[0], S30_ID)
    assert lead is not None and lead.step == 5
    pending = await mission.propose_group_combat(
        actors[0], lead.state_version, S30_ID
    )
    assert pending is not None and pending.proposal_id is not None
    proposal = await groups.activity_proposal(actors[0], pending.proposal_id)
    accepted = await groups.respond_activity(
        actors[1], proposal.proposal_id, expected_revision=proposal.revision, accept=True
    )
    started = await mission.start_group_combat(
        actors[0], proposal.proposal_id, expected_revision=accepted.revision
    )
    assert started is not None and started.combat is not None
    assert started.group_size == 2
    assert len(
        [fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"]
    ) == 1
    async with sessions() as session:
        encounter = await session.get(CampaignSharedEncounter, started.encounter_id)
        assert encounter is not None and encounter.roster_size == 2
        assert encounter.quest_id == S30_ID and encounter.content_id == S30_MISSION_ID
        assert encounter.scaling_snapshot is not None
        assert encounter.scaling_snapshot["roster_size"] == 2
        for actor in actors:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            assert await session.scalar(
                select(CampaignObjectiveCredit.id).where(
                    CampaignObjectiveCredit.character_id == character.id,
                    CampaignObjectiveCredit.quest_id == S30_ID,
                    CampaignObjectiveCredit.objective_id == "s30.custodian_faced",
                )
            ) is not None


@pytest.mark.asyncio
async def test_s30_bestiary_requires_thresholds_and_distinct_boss_observations(database):
    actor, road, sessions, mission, service = await _seed_s30(database, 793050)
    view = await _reach_s30_boss(service, actor)
    combat = await mission.start_solo_combat(actor, view.state_version, S30_ID)
    assert combat is not None and combat.combat is not None

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == ALTOS_CUSTODIO_ULTIMO_TURNO,
            )
        )
        assert entry is not None and entry.bkp >= 10 and entry.stage == "known"
        entry.bkp = 30
        await road.bestiary.refresh_boss_mastery(
            session, character.id, ALTOS_CUSTODIO_ULTIMO_TURNO
        )
        assert entry.stage == "studied"
        entry.bkp = 50
        await road.bestiary.refresh_boss_mastery(
            session, character.id, ALTOS_CUSTODIO_ULTIMO_TURNO
        )
        assert entry.stage == "studied"
        for evidence_id in (
            "first_victory",
            "action:ordem_vencida",
            "mechanic:ultimo_turno_telegraph",
        ):
            await road.bestiary.add_evidence(
                session,
                entry,
                character.id,
                ALTOS_CUSTODIO_ULTIMO_TURNO,
                evidence_id,
                "test_observed_fact",
                0,
            )
        await road.bestiary.refresh_boss_mastery(
            session, character.id, ALTOS_CUSTODIO_ULTIMO_TURNO
        )
        assert entry.stage == "dominated"


def test_s30_content_catalog_registers_codex_achievement_and_boss():
    assert ACHIEVEMENT_BY_ID[S30_ACHIEVEMENT].name == "A Ordem que Restou"
    assert "protocolo antigo permanece em execução" in CODEX_FRAGMENTS[
        S30_CODEX_ENTRY
    ].text.lower()
    boss = creature_for(ALTOS_CUSTODIO_ULTIMO_TURNO)
    assert (
        boss.name,
        boss.category,
        boss.archetype,
        boss.unlock_level,
        boss.max_level,
    ) == ("Custódio do Último Turno", "boss", "controller", 50, 50)
    assert S30_CONTENT_VERSION == "altos-1.0.1"
    assert S30_ID == "S30"
    assert S30_MISSION_ID == "mission.altos.s30"
    assert S30_PHYSICAL_SEALS == tuple(sorted(S30_PHYSICAL_SEALS))
