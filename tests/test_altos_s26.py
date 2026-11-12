from collections import Counter

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P25_CONTENT_VERSION,
    P26_CONTENT_VERSION,
    S26_ID,
    S26_MISSION_ID,
    S26_REWARD_SOURCE,
    AltosMissionService,
)
from asterion.application.groups import GroupError, GroupService
from asterion.application.knowledge_catalog import CODEX_BY_ID, CODEX_FRAGMENTS
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_PONTES_LABEL,
    ALTOS_REGION_LABEL,
)
from asterion.application.s26 import (
    S26_CODEX_ENTRY,
    S26_COURO_ESCARPA,
    S26_LIQUEN_PEDREIRA,
    S26Service,
)
from asterion.bot.s26_ui import render_s26
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
from tests.test_s4_s5_integration import _terminal


async def _seed_s26(
    database,
    actor: int,
    *,
    level: int = 44,
    p26_status: str | None = "completed",
    location: str = ALTOS_ABRIGO_LABEL,
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
        session.add(
            Quest(
                character_id=character.id,
                quest_id="P25",
                title="O Peso Antigo",
                status="completed",
                step=9,
                content_version=P25_CONTENT_VERSION,
                progress={"completed": True},
            )
        )
        if p26_status is not None:
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P26",
                    title="Ordens de Emergência",
                    status=p26_status,
                    step=7,
                    content_version=P26_CONTENT_VERSION,
                    progress={"completed": p26_status == "completed"},
                )
            )
    combat = AltosMissionService(sessions, "ocaso")
    return actor, road, sessions, S26Service(sessions, "ocaso", combat), combat


@pytest.mark.asyncio
async def test_s26_gate_requires_p26_level_44_and_an_open_local(database):
    actor, _road, _sessions, service, _combat = await _seed_s26(
        database, 786260, level=44, p26_status="active"
    )
    locked = await service.offer(actor)
    assert locked is not None and not locked.available

    actor, _road, _sessions, service, _combat = await _seed_s26(
        database, 786261, level=43
    )
    locked = await service.offer(actor)
    assert locked is not None and not locked.available

    actor, _road, _sessions, service, _combat = await _seed_s26(
        database, 786262, level=44, location=ALTOS_PONTES_LABEL
    )
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    assert offer.status == "unaccepted"


@pytest.mark.asyncio
async def test_s26_solo_steps_scripted_combat_codex_reward_and_idempotency(
    database, monkeypatch
):
    actor, _road, sessions, service, combat = await _seed_s26(database, 786263)
    async with sessions() as session:
        seed = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert seed is not None
        initial_xp, initial_crowns = seed.xp, seed.crowns

    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    screen = render_s26(await service.objective(actor))
    assert "Etapa 1/6" in screen.text

    first = await service.advance(actor, accepted.state_version, "receive_shift_marks")
    assert first is not None and first.step == 2
    assert first.progress["shift_markers_received"] == 3
    duplicate = await service.advance(actor, accepted.state_version, "receive_shift_marks")
    assert duplicate is not None and duplicate.state_version == first.state_version

    reconnected = await S26Service(sessions, "ocaso", combat).resume_active(actor)
    assert reconnected is not None and reconnected.step == 2
    second = await service.advance(actor, first.state_version, "accompany_rescue_team")
    assert second is not None and second.step == 3
    assert second.progress["rescue_team_accompanied"] is True

    objective = await service.objective(actor)
    assert objective is not None and objective.step == 3
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        material_state_before = {
            (row.material_id, row.bound, row.quantity)
            for row in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.material_id.in_(
                            (S26_COURO_ESCARPA, S26_LIQUEN_PEDREIRA)
                        ),
                    )
                )
            ).all()
        }
    battle = await combat.start_solo_combat(actor, objective.state_version, S26_ID)
    assert battle is not None and battle.kind == "combat" and battle.combat is not None
    assert battle.combat.fighters["enemy"].level == 44
    assert battle.combat.variant is None

    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeated = await combat.action(
        actor, battle.activity_id, battle.combat.version, "attack"
    )
    assert defeated is not None and defeated.step == 3
    assert defeated.progress["awaiting_retry"] is True
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp, character.crowns) == (initial_xp, initial_crowns)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S26_REWARD_SOURCE,
            )
        ) is None
        material_state_after = {
            (row.material_id, row.bound, row.quantity)
            for row in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.material_id.in_(
                            (S26_COURO_ESCARPA, S26_LIQUEN_PEDREIRA)
                        ),
                    )
                )
            ).all()
        }
        assert material_state_after == material_state_before

    retry = await combat.retry_combat(actor, defeated.state_version, S26_ID)
    assert retry is not None and retry.kind == "combat" and retry.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await combat.action(
        actor, retry.activity_id, retry.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4 and victory.status == "active"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert (character.xp, character.crowns) == (initial_xp, initial_crowns)
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S26_REWARD_SOURCE,
            )
        ) is None
        material_state_after_victory = {
            (row.material_id, row.bound, row.quantity)
            for row in (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.material_id.in_(
                            (S26_COURO_ESCARPA, S26_LIQUEN_PEDREIRA)
                        ),
                    )
                )
            ).all()
        }
        assert material_state_after_victory == material_state_before

    view = await service.resume(actor)
    assert view is not None and view.step == 4
    view = await service.advance(actor, view.state_version, "find_old_shift_record")
    assert view is not None and view.step == 5
    view = await service.advance(
        actor, view.state_version, "discuss_heroism_and_exploitation"
    )
    assert view is not None and view.step == 6
    completed = await service.advance(actor, view.state_version, "record_codex")
    assert completed is not None and completed.status == "completed"
    completed_again = await service.advance(
        actor, completed.state_version, "record_codex"
    )
    assert completed_again is not None and completed_again.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp - initial_xp == 42_070
        assert character.crowns - initial_crowns == 570
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == S26_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.fragment_id == S26_CODEX_ENTRY,
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S26_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id
                    )
                )
            ).all()
        )
        assert Counter((item.kind, item.item_id, item.quantity) for item in components) == Counter(
            {
                ("xp", None, 42_070): 1,
                ("crowns", None, 570): 1,
                ("material", S26_COURO_ESCARPA, 1): 1,
                ("material", S26_LIQUEN_PEDREIRA, 1): 1,
            }
        )
        stacks = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character.id)
            )
        ).all()
        assert {
            (stack.material_id, stack.bound, stack.quantity)
            for stack in stacks
            if stack.material_id in {S26_COURO_ESCARPA, S26_LIQUEN_PEDREIRA}
        } == {
            (S26_COURO_ESCARPA, True, 1),
            (S26_LIQUEN_PEDREIRA, True, 1),
        }
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S26_REWARD_SOURCE,
            )
        ) == reward.id
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id.like("achievement.altos.s26%"),
            )
        ) is None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id.like("unlock.%altos.%"),
            )
        ) is None
        assert await session.scalar(
            select(GameActivity.id).where(
                GameActivity.character_id == character.id,
                GameActivity.content_id == S26_MISSION_ID,
                GameActivity.status == "active",
            )
        ) is None

    assert CODEX_BY_ID["codex.altos.turno_sem_fim"].title == "Turno sem Fim"
    assert "heroísmo individual" in CODEX_FRAGMENTS["codex.altos.turno_sem_fim"].text


@pytest.mark.asyncio
async def test_s26_abandonment_is_blocked_in_foreground_and_reaccept_preserves_codex(
    database,
):
    actor, _road, sessions, service, _combat = await _seed_s26(database, 786264)
    accepted = await service.accept(actor)
    assert accepted is not None
    first = await service.advance(actor, accepted.state_version, "receive_shift_marks")
    assert first is not None and first.step == 2

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        session.add_all(
            (
                CodexEntry(character_id=character.id, entry_id="codex.altos.turno_sem_fim"),
                CodexFragment(
                    character_id=character.id,
                    entry_id="codex.altos.turno_sem_fim",
                    fragment_id="codex.altos.turno_sem_fim",
                ),
                GameActivity(
                    character_id=character.id,
                    content_id="s26.foreground_test",
                    status="active",
                    state_version=0,
                    ruleset_version="test",
                ),
            )
        )
    blocked = await service.abandon(actor, first.state_version)
    assert blocked is not None and blocked.status == "active" and blocked.step == 2

    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.content_id == "s26.foreground_test")
        )
        assert activity is not None
        activity.status = "completed"
    abandoned = await service.abandon(actor, first.state_version)
    assert abandoned is not None and abandoned.status == "abandoned"
    assert abandoned.step == 1 and abandoned.progress == {}
    offer = await service.offer(actor)
    assert offer is not None and offer.reacceptable
    restarted = await service.accept(actor, offer.state_version, reaccept=True)
    assert restarted is not None and restarted.status == "active" and restarted.step == 1
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == "codex.altos.turno_sem_fim",
            )
        ) is not None


@pytest.mark.asyncio
async def test_s26_group_member_advances_alone_and_scripted_encounter_is_solo(
    database, monkeypatch
):
    leader, _road, sessions, service, combat = await _seed_s26(database, 786265)
    helper, _road, _sessions, _service, _combat = await _seed_s26(database, 786266)
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
        marked = await service.advance(actor, accepted.state_version, "receive_shift_marks")
        assert marked is not None and marked.step == 2

    shared_combat = AltosMissionService(sessions, "ocaso", groups=groups)
    leader_view = await service.resume(leader)
    assert leader_view is not None and leader_view.step == 2
    leader_view = await service.advance(
        leader, leader_view.state_version, "accompany_rescue_team"
    )
    assert leader_view is not None and leader_view.step == 3
    # Objectives are Solo (Ação × Consequência §5): the helper stays on step 2.
    helper_view = await service.resume(helper)
    assert helper_view is not None and helper_view.step == 2

    # S26 is not a Boss: the Group proposal is refused, the fight is Solo.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await shared_combat.propose_group_combat(
            leader, leader_view.state_version, S26_ID
        )
    assert not await groups.activity_proposals(leader)
    started = await combat.start_solo_combat(leader, leader_view.state_version, S26_ID)
    assert started is not None and started.combat is not None
    assert started.group_size == 1 and not started.combat.party_mode
    assert started.combat.fighters["enemy"].level == 44
    assert started.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await combat.action(
        leader, started.activity_id, started.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4
    assert (await service.resume(helper)).step == 2

    leader_s26 = await service.resume(leader)
    assert leader_s26 is not None and leader_s26.step == 4
    old_record = await service.advance(
        leader, leader_s26.state_version, "find_old_shift_record"
    )
    assert old_record is not None and old_record.step == 5
    helper_s26 = await service.resume(helper)
    assert helper_s26 is not None and helper_s26.step == 2

    async with sessions() as session:
        character_ids = set(
            (
                await session.scalars(
                    select(Character.id).where(
                        Character.telegram_id.in_((leader, helper))
                    )
                )
            ).all()
        )
        leader_id = await session.scalar(
            select(Character.id).where(Character.telegram_id == leader)
        )
        for objective_id in (
            "s26.scripted_carneiro_victory",
            "s26.accompanied_rescue_team",
            "s26.found_old_shift_record",
        ):
            credits = (
                await session.scalars(
                    select(CampaignObjectiveCredit).where(
                        CampaignObjectiveCredit.character_id.in_(character_ids),
                        CampaignObjectiveCredit.quest_id == S26_ID,
                        CampaignObjectiveCredit.objective_id == objective_id,
                    )
                )
            ).all()
            assert {credit.character_id for credit in credits} == {leader_id}
