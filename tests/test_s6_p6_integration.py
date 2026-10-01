import pytest
from sqlalchemy import func, select

from asterion.application.p5 import P5_ID
from asterion.application.p6 import (
    P6_CAMPAIGN_UNLOCK,
    P6_CODEX_ANCHOR,
    P6_CONTENT_ID,
    P6_ID,
    P6_IRON,
    P6_NUCLEUS,
    P6_NUCLEUS_SOURCE,
    P6_RECIPE_UNLOCK,
    P6_RESIDUE,
    P6_REWARD_SOURCE,
    P6Service,
)
from asterion.application.road import REFUGE, RUINS
from asterion.application.s6 import (
    S6_CODEX_PEREGRINOS,
    S6_MARKS,
    S6_MATERIALS,
    S6_REWARD_SOURCE,
    S6Service,
)
from asterion.domain.road import FACELESS_CUSTODIAN, VIGIA_PARTIDO
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CharacterActiveArtSlot,
    CharacterTalentChoice,
    ClassTrialState,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    Encounter,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
)
from tests.test_s4_s5_integration import _seed_p4, _set_location, _terminal


async def _seed_final_campaign(database, actor: int, *, level: int = 10, door_known: bool = True):
    character_id, sessions = await _seed_p4(database, actor, level=level)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        session.add_all(
            [
                Quest(
                    character_id=character_id,
                    quest_id="S2",
                    title="S2 concluída",
                    status="completed",
                    step=5,
                    content_version="tdo-1.0.11",
                    progress={"completed": True},
                ),
                Quest(
                    character_id=character_id,
                    quest_id=P5_ID,
                    title="A Porta do Poente",
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.11",
                    progress={
                        "completed": True,
                        "door_known": door_known,
                        "recurring_symbol_recorded": True,
                        "reports": ["alda", "oren"],
                    },
                ),
            ]
        )
    return character_id, sessions


async def _ready_p6_character(sessions, character_id):
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.selected_path = "bastiao"
        session.add_all(
            [
                CharacterTalentChoice(
                    character_id=character_id,
                    point_slot=1,
                    talent_id="talent.sentinela.aco_desperto",
                ),
                CharacterTalentChoice(
                    character_id=character_id,
                    point_slot=2,
                    talent_id="talent.sentinela.carne_de_pedra",
                ),
                ClassTrialState(
                    character_id=character_id,
                    character_class="sentinela",
                    trial_id="trial.sentinela",
                    status="completed",
                    current_stage=3,
                    completed_stages=[1, 2, 3],
                    state_version=0,
                    context="circle",
                ),
                CharacterActiveArtSlot(
                    character_id=character_id,
                    slot=1,
                    art_id="class_art.sentinela.golpe_de_guarda",
                ),
            ]
        )


@pytest.mark.asyncio
async def test_s6_gate_checkpoint_retry_rewards_and_codex_are_idempotent(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998901
    character_id, sessions = await _seed_final_campaign(database, actor)
    service = S6Service(sessions, "ocaso")
    offer = await service.oren(actor)
    assert offer is not None and offer.available and offer.kind == "oren"
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1

    review = await service.action(actor, accepted.state_version, "review")
    assert review is not None and review.step == 2
    await _set_location(sessions, character_id, RUINS)
    first_mark = await service.action(actor, review.state_version, "mark", S6_MARKS[2])
    duplicate = await service.action(actor, first_mark.state_version, "mark", S6_MARKS[2])
    second_mark = await service.action(actor, duplicate.state_version, "mark", S6_MARKS[0])
    assert second_mark is not None and second_mark.step == 2
    third_mark = await service.action(actor, second_mark.state_version, "mark", S6_MARKS[1])
    assert third_mark is not None and third_mark.step == 3
    assert third_mark.progress["pilgrim_marks"] == [S6_MARKS[0], S6_MARKS[1], S6_MARKS[2]]

    combat = await service.action(actor, third_mark.state_version, "shelter")
    assert combat is not None and combat.kind == "combat" and combat.step == 4
    assert combat.combat.fighters["enemy"].name == FACELESS_CUSTODIAN.name
    assert combat.combat.fighters["enemy"].level == 10
    assert combat.combat.variant is None
    assert combat.combat.enemy_actions.keys() == {
        action[0] for action in FACELESS_CUSTODIAN.actions
    }
    assert combat.activity_id and combat.encounter_id
    assert await service.resume(actor) is not None
    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id) == (
        combat.activity_id,
        combat.encounter_id,
    )

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        xp_before_defeat = character.xp
        vigor_before = character.vigor
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeat is not None and defeat.kind == "recovery"
    assert defeat.step == 4 and defeat.progress["awaiting_retry"]
    assert defeat.progress["pilgrim_marks"] == third_mark.progress["pilgrim_marks"]
    async with sessions() as session:
        character = await session.get(Character, character_id)
        failed_activity = await session.get(GameActivity, combat.activity_id)
        assert character is not None and character.xp == xp_before_defeat
        assert character.hp == character.max_hp and character.vigor == vigor_before
        assert failed_activity is not None and failed_activity.status == "failed"
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{S6_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        ) is None

    await _set_location(sessions, character_id, RUINS)
    retry = await service.action(actor, defeat.state_version, "retry")
    assert retry is not None and retry.kind == "combat" and retry.step == 4
    assert retry.activity_id != combat.activity_id
    assert retry.combat.fighters["enemy"].level == 10 and retry.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, retry.activity_id, retry.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 5 and victory.kind == "last_record"
    record = await service.action(actor, victory.state_version, "last_record")
    assert record is not None and record.step == 6
    await _set_location(sessions, character_id, REFUGE)
    report = await service.action(actor, record.state_version, "report")
    duplicate_report = await service.action(actor, record.state_version, "report")
    assert report is not None and report.status == "completed"
    assert duplicate_report is not None and duplicate_report.status == "completed"
    from asterion.bot.s6_ui import render_s6

    completion_screen = render_s6(report)
    assert "XP · 7.900" in completion_screen.text
    assert "Coroas · 310" in completion_screen.text

    async with sessions() as session:
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S6_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        assert {
            (row.kind, row.item_id, row.quantity, row.payload.get("bound"))
            for row in components
        } == {
            ("xp", None, 7900, None),
            ("crowns", None, 310, None),
            *[("material", material, amount, True) for material, amount in S6_MATERIALS],
        }
        assert await session.scalar(
            select(func.count()).select_from(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S6_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(HuntContext.id).where(HuntContext.game_activity_id == retry.activity_id)
        ) is None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == FACELESS_CUSTODIAN.creature_id,
                BestiaryEntry.wins == 1,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.entry_id == S6_CODEX_PEREGRINOS,
            )
        ) is not None


@pytest.mark.asyncio
async def test_p6_auto_start_gate_and_requires_p5_door_knowledge(database):
    actor = 998911
    character_id, sessions = await _seed_p4(database, actor, level=10)
    service = P6Service(sessions, "ocaso")
    unavailable = await service.resume(actor)
    assert unavailable is not None and unavailable.kind == "unavailable"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P6_ID)
        ) is None

    actor += 1
    character_id, sessions = await _seed_final_campaign(
        database, actor, level=9, door_known=True
    )
    service = P6Service(sessions, "ocaso")
    level_blocked = await service.resume(actor)
    assert level_blocked is not None and level_blocked.kind == "unavailable"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P6_ID)
        ) is None

    actor += 1
    character_id, sessions = await _seed_final_campaign(
        database, actor, level=10, door_known=False
    )
    missing_door = await P6Service(sessions, "ocaso").resume(actor)
    assert missing_door is not None and missing_door.kind == "unavailable"
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P6_ID)
        ) is None


@pytest.mark.asyncio
async def test_p6_chamber_boss_retry_codex_and_campaign_reward(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998921
    character_id, sessions = await _seed_final_campaign(database, actor)
    await _ready_p6_character(sessions, character_id)
    service = P6Service(sessions, "ocaso")
    initial = await service.resume(actor)
    assert initial is not None and initial.status == "active" and initial.step == 1
    assert initial.guidance is None and initial.kind == "travel_ruins"
    assert (await service.resume(actor)).step == initial.step
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P6_ID
            )
        ) == 1

    await _set_location(sessions, character_id, RUINS)
    crossed = await service.action(actor, initial.state_version, "cross_door")
    assert crossed is not None and crossed.step == 2 and crossed.kind == "enter_chamber"
    chamber = await service.action(actor, crossed.state_version, "enter_chamber")
    assert chamber is not None and chamber.step == 3 and chamber.location == "Câmara do Poente"
    before_boss = await service.action(actor, chamber.state_version, "inspect_before")
    assert before_boss is not None and before_boss.step == 4 and before_boss.kind == "start_boss"
    async with sessions() as session:
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P6_CODEX_ANCHOR,
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.location_id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "tdo.location.camara_do_poente",
            )
        ) == "tdo.location.camara_do_poente"

    fight = await service.action(actor, before_boss.state_version, "start_boss")
    assert fight is not None and fight.kind == "combat" and fight.step == 5
    enemy = fight.combat.fighters["enemy"]
    assert enemy.name == VIGIA_PARTIDO.name and enemy.level == 10
    assert fight.combat.variant is None
    assert set(fight.combat.enemy_actions) == {action[0] for action in VIGIA_PARTIDO.actions}
    assert fight.activity_id is not None and fight.encounter_id is not None
    async with sessions() as session:
        activity = await session.get(GameActivity, fight.activity_id)
        encounter = await session.get(Encounter, fight.encounter_id)
        combat_record = await session.scalar(
            select(CombatRecord).where(CombatRecord.encounter_id == fight.encounter_id)
        )
        character = await session.get(Character, character_id)
        assert activity is not None and activity.content_id == P6_CONTENT_ID
        assert encounter is not None and encounter.game_activity_id == activity.id
        assert combat_record is not None
        config = combat_record.snapshot["configuration_snapshot"]
        assert config["selected_path"] == "bastiao"
        assert config["talents"] == [
            {"point_slot": 1, "talent_id": "talent.sentinela.aco_desperto"},
            {"point_slot": 2, "talent_id": "talent.sentinela.carne_de_pedra"},
        ]
        assert config["active_arts"] == [
            {"slot": 1, "art_id": "class_art.sentinela.golpe_de_guarda"}
        ]
        assert combat_record.snapshot["fighters"]["player"]["selected_path"] == "bastiao"
        assert set(combat_record.snapshot["fighters"]["player"]["talent_ids"]) == {
            "talent.sentinela.aco_desperto",
            "talent.sentinela.carne_de_pedra",
        }
        assert character is not None
        xp_before_boss = character.xp
        vigor_before_boss = character.vigor
        assert await session.scalar(
            select(RewardComponent.id).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P6_NUCLEUS_SOURCE,
            )
        ) is None

    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        fight.activity_id,
        fight.encounter_id,
        fight.combat_id,
    )
    assert resumed.combat.configuration_snapshot["selected_path"] == "bastiao"
    assert resumed.combat.configuration_snapshot["active_arts"] == [
        {"slot": 1, "art_id": "class_art.sentinela.golpe_de_guarda"}
    ]
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await service.action_combat(
        actor, fight.activity_id, fight.activity_state_version, "attack"
    )
    assert defeat is not None and defeat.kind == "retry_travel" and defeat.step == 5
    assert defeat.progress["awaiting_retry"] is True
    async with sessions() as session:
        character = await session.get(Character, character_id)
        failed = await session.get(GameActivity, fight.activity_id)
        assert character is not None and character.xp == xp_before_boss
        assert character.hp == character.max_hp and character.vigor == vigor_before_boss
        assert failed is not None and failed.status == "failed"

    await _set_location(sessions, character_id, RUINS)
    returned = await service.action(actor, defeat.state_version, "enter_chamber")
    assert returned is not None and returned.location == "Câmara do Poente"
    retry = await service.action(actor, returned.state_version, "retry")
    assert retry is not None and retry.kind == "combat" and retry.step == 5
    assert retry.activity_id != fight.activity_id
    assert retry.combat.fighters["enemy"].name == VIGIA_PARTIDO.name
    assert retry.combat.fighters["enemy"].level == 10 and retry.combat.variant is None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, retry.activity_id, retry.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 6 and victory.kind == "inspect_after"
    async with sessions() as session:
        assert await session.scalar(
            select(RewardComponent.id).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P6_NUCLEUS_SOURCE,
            )
        ) is not None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == VIGIA_PARTIDO.creature_id,
                BestiaryEvidence.evidence_id == "p6_completed",
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == VIGIA_PARTIDO.creature_id,
                BestiaryEvidence.evidence_id == "action:queda_ocaso",
            )
        ) is None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.like(f"{P6_REWARD_SOURCE}:enemy-xp:%"),
            )
        ) is None
        milestone = await session.scalar(
            select(RewardComponent)
            .join(RewardEvent)
            .where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == f"bestiary:first_victory:{character_id}:{VIGIA_PARTIDO.creature_id}",
                RewardComponent.kind == "bestiary_first_victory_xp",
            )
        )
        assert milestone is not None and milestone.quantity == 474
        character = await session.get(Character, character_id)
        assert character is not None and character.xp == xp_before_boss + 474

    after = await service.action(actor, victory.state_version, "inspect_after")
    assert after is not None and after.step == 7 and after.kind == "record_anchor"
    recorded = await service.action(actor, after.state_version, "record_anchor")
    assert recorded is not None and recorded.step == 8 and recorded.kind == "return_ruins"
    return_to_refuge = await service.action(actor, recorded.state_version, "return_ruins")
    assert return_to_refuge is not None and return_to_refuge.location == RUINS
    await _set_location(sessions, character_id, REFUGE)
    reports = await service.resume(actor)
    assert reports is not None and reports.kind == "reports"
    one_report = await service.action(actor, reports.state_version, "report_oren")
    assert one_report is not None and one_report.step == 8
    choice = await service.action(actor, one_report.state_version, "report_alda")
    assert choice is not None and choice.step == 9 and choice.kind == "choose_reward"
    completed = await service.choose_reward(actor, choice.state_version, "last_post")
    repeated = await service.choose_reward(actor, choice.state_version, "sunset_seal")
    assert completed is not None and completed.status == "completed"
    assert repeated is not None and repeated.status == "completed"

    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P6_ID)
        )
        assert quest is not None and quest.progress["reward_choice"] == "last_post"
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == VIGIA_PARTIDO.creature_id,
                BestiaryEvidence.evidence_id == "p6_completed",
            )
        ) is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P6_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        actual = {
            (row.kind, row.item_id, row.quantity, row.payload.get("bound"))
            for row in components
        }
        assert actual == {
            ("xp", None, 14220, None),
            ("crowns", None, 500, None),
            ("equipment", None, 1, True),
            ("material", P6_IRON, 4, True),
            ("material", P6_RESIDUE, 4, True),
        }
        assert await session.scalar(
            select(func.count()).select_from(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P6_REWARD_SOURCE,
            )
        ) == 1
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == P6_RECIPE_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == P6_CAMPAIGN_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.tdo.campaign.completed",
            )
        ) is not None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VIGIA_PARTIDO.creature_id,
                BestiaryEntry.wins == 1,
            )
        ) is not None
        assert await session.scalar(
            select(MaterialStack.id).where(
                MaterialStack.character_id == character_id,
                MaterialStack.material_id == P6_NUCLEUS,
                MaterialStack.quantity == 1,
                MaterialStack.bound.is_(True),
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P6_CODEX_ANCHOR,
            )
        ) is not None
