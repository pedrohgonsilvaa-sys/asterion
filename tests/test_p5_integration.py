import pytest
from sqlalchemy import func, select

from asterion.application.p5 import (
    P5_CODEX_ENTRY,
    P5_CONTENT_ID,
    P5_DOOR_FRAGMENT,
    P5_ELEMENTS,
    P5_ID,
    P5_IRON,
    P5_RESIDUE,
    P5_REWARD_SOURCE,
    P5_SYMBOL_FRAGMENT,
    P5Service,
)
from asterion.application.road import REFUGE, RUINS
from asterion.domain.road import SUNSET_CUSTODIAN, enemy_xp
from asterion.infrastructure.db.combat_codec import decode
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    CharacterActiveArtSlot,
    CharacterTalentChoice,
    CodexEntry,
    CodexFragment,
    CombatRecord,
    Encounter,
    GameActivity,
    HuntContext,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
)
from tests.test_s3_p4_integration import _seed_campaign
from tests.test_s4_s5_integration import _seed_p4, _set_location, _terminal


async def _start_combat(service, actor, sessions, character_id):
    offer = await service.offer(actor)
    assert offer is not None and offer.available
    accepted = await service.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    await _set_location(sessions, character_id, RUINS)
    first = await service.action(actor, accepted.state_version, "follow_structures")
    assert first is not None and first.step == 2
    stale = await service.action(actor, accepted.state_version, "find_door")
    assert stale is not None and stale.step == 2
    pending = await service.action(actor, first.state_version, "find_door")
    assert pending is not None and pending.kind == "combat_pending" and pending.step == 3
    return await service.action(actor, pending.state_version, "start_boss")


@pytest.mark.asyncio
async def test_p5_gate_offer_acceptance_and_no_secondary_requirements(database):
    actor = 998701
    _, sessions = await _seed_p4(database, actor, level=8)
    p5 = P5Service(sessions, "ocaso")
    blocked_level = await p5.offer(actor)
    assert blocked_level is not None and not blocked_level.available

    actor += 1
    character_id, sessions = await _seed_campaign(database, actor, level=9)
    without_p4 = await P5Service(sessions, "ocaso").offer(actor)
    assert without_p4 is not None and not without_p4.available
    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(Quest.character_id == character_id, Quest.quest_id == P5_ID)
        ) is None

    actor += 1
    character_id, sessions = await _seed_p4(database, actor, level=9)
    p5 = P5Service(sessions, "ocaso")
    offer = await p5.offer(actor)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    accepted = await p5.accept(actor, offer.state_version)
    duplicate = await p5.accept(actor, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    assert duplicate is not None and duplicate.status == "active" and duplicate.step == 1
    async with sessions() as session:
        assert await session.scalar(
            select(func.count()).select_from(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P5_ID
            )
        ) == 1


@pytest.mark.asyncio
async def test_p5_full_mission_uses_canonical_custodian_and_rewards_once(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998704
    character_id, sessions = await _seed_p4(database, actor, level=9)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        vigor_before = character.vigor
        character.selected_path = "bastiao"
        session.add(
            CharacterActiveArtSlot(
                character_id=character_id,
                slot=1,
                art_id="class_art.sentinela.golpe_de_guarda",
            )
        )
        session.add(
            CharacterTalentChoice(
                character_id=character_id,
                point_slot=1,
                talent_id="talent.sentinela.aco_desperto",
            )
        )

    service = P5Service(sessions, "ocaso")
    combat = await _start_combat(service, actor, sessions, character_id)
    assert combat is not None and combat.kind == "combat" and combat.step == 3
    assert combat.combat.fighters["enemy"].name == SUNSET_CUSTODIAN.name
    assert combat.combat.fighters["enemy"].level == 9
    assert combat.combat.variant is None
    assert set(combat.combat.enemy_actions) == {
        action[0] for action in SUNSET_CUSTODIAN.actions
    }

    async with sessions() as session:
        activity = await session.get(GameActivity, combat.activity_id)
        character = await session.get(Character, character_id)
        encounter = await session.scalar(
            select(Encounter).where(Encounter.game_activity_id == combat.activity_id)
        )
        assert activity is not None and activity.content_id == P5_CONTENT_ID
        assert encounter is not None and encounter.game_activity_id == activity.id
        record = await session.scalar(
            select(CombatRecord).where(CombatRecord.encounter_id == encounter.id)
        )
        assert record is not None
        snapshot = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        assert snapshot.configuration_snapshot["selected_path"] == "bastiao"
        assert snapshot.configuration_snapshot["talents"] == [
            {"point_slot": 1, "talent_id": "talent.sentinela.aco_desperto"}
        ]
        assert snapshot.configuration_snapshot["active_arts"] == [
            {"slot": 1, "art_id": "class_art.sentinela.golpe_de_guarda"}
        ]
        assert await session.scalar(
            select(HuntContext.id).where(HuntContext.game_activity_id == combat.activity_id)
        ) is None
        assert character is not None and character.vigor == vigor_before

    resumed = await service.resume(actor)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )

    # Drive the shared combat engine until the canonical Custodian prepares Queda.
    # Verify the mission HUD exposes the telegraph and reconnect keeps its identity.
    for _ in range(8):
        if combat.combat.prepared_action == "queda_poente":
            break
        combat = await service.action_combat(
            actor, combat.activity_id, combat.activity_state_version, "attack"
        )
        assert combat is not None and combat.kind == "combat"
    assert combat.combat.prepared_action == "queda_poente"
    assert combat.combat.prepared_action_instance_id
    from asterion.bot.p5_ui import render_p5

    telegraph = render_p5(combat)
    assert "prepara" in telegraph.text and "Queda do Poente" in telegraph.text
    prepared_instance = combat.combat.prepared_action_instance_id
    resumed = await service.resume(actor)
    assert resumed is not None and resumed.kind == "combat"
    assert resumed.activity_id == combat.activity_id
    assert resumed.encounter_id == combat.encounter_id
    assert resumed.combat.prepared_action == "queda_poente"
    assert resumed.combat.prepared_action_instance_id == prepared_instance

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 4 and victory.kind == "elements"

    found = await service.action(actor, victory.state_version, "element", P5_ELEMENTS[2])
    duplicate = await service.action(actor, found.state_version, "element", P5_ELEMENTS[2])
    second = await service.action(actor, duplicate.state_version, "element", P5_ELEMENTS[0])
    third = await service.action(actor, second.state_version, "element", P5_ELEMENTS[1])
    assert third is not None and third.step == 5 and len(third.progress["door_elements"]) == 3
    symbol = await service.action(actor, third.state_version, "record_symbol")
    assert symbol is not None and symbol.step == 6
    await _set_location(sessions, character_id, REFUGE)
    reports = await service.resume(actor)
    assert reports is not None and reports.kind == "reports"
    one_report = await service.action(actor, reports.state_version, "report_oren")
    assert one_report is not None and one_report.status == "active"
    complete = await service.action(actor, one_report.state_version, "report_alda")
    stale_report = await service.action(actor, one_report.state_version, "report_alda")
    assert complete is not None and complete.status == "completed"
    assert stale_report is not None and stale_report.status == "completed"

    async with sessions() as session:
        final_character = await session.get(Character, character_id)
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P5_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == reward.id)
            )
        ).all()
        actual_components = {
            (row.kind, row.item_id, row.quantity, row.payload.get("bound"))
            for row in components
        }
        assert actual_components == {
            ("xp", None, 7100, None),
            ("crowns", None, 300, None),
            ("material", P5_IRON, 3, True),
            ("material", P5_RESIDUE, 1, True),
        }
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{P5_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        ) is not None
        enemy_xp_component = await session.scalar(
            select(RewardComponent).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{P5_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        )
        assert enemy_xp_component is not None
        assert enemy_xp_component.quantity == enemy_xp(9, "elite", player_level=9)
        assert final_character is not None and final_character.vigor == vigor_before
        assert await session.scalar(
            select(func.count()).select_from(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P5_REWARD_SOURCE,
            )
        ) == 1
        stacks = (
            await session.scalars(
                select(MaterialStack).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.bound.is_(True),
                    MaterialStack.material_id.in_((P5_IRON, P5_RESIDUE)),
                )
            )
        ).all()
        assert {(stack.material_id, stack.quantity, stack.bound) for stack in stacks} == {
            (P5_IRON, 3, True),
            (P5_RESIDUE, 1, True),
        }
        bestiary = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "custodio_poente",
            )
        )
        assert bestiary is not None and bestiary.wins == 1
        assert await session.scalar(
            select(BestiaryEvidence.id).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == "custodio_poente",
                BestiaryEvidence.evidence_id == "action:queda_poente",
            )
        ) is not None
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == P5_CODEX_ENTRY,
            )
        ) is not None
        fragment_ids = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id,
                        CodexFragment.entry_id == P5_CODEX_ENTRY,
                    )
                )
            ).all()
        )
        assert {P5_DOOR_FRAGMENT, P5_SYMBOL_FRAGMENT} <= fragment_ids
        assert not any("ancora" in value.lower() for value in fragment_ids)


@pytest.mark.asyncio
async def test_p5_defeat_uses_ruins_recovery_and_retry_keeps_fixed_creature(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998705
    character_id, sessions = await _seed_p4(database, actor, level=9)
    service = P5Service(sessions, "ocaso")
    combat = await _start_combat(service, actor, sessions, character_id)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        vigor = character.vigor
        session.add_all(
            [
                Brazier(character_id=character_id, brazier_id="tdo.brazier.vento_morto"),
                Brazier(character_id=character_id, brazier_id="tdo.brazier.galhos_mortos"),
                Brazier(character_id=character_id, brazier_id="tdo.brazier.poente"),
            ]
        )
    monkeypatch.setattr(scripted_combat, "act", _terminal("defeat"))
    defeat = await service.action_combat(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeat is not None and defeat.kind == "recovery" and defeat.step == 3
    assert defeat.progress["awaiting_retry"] is True
    assert defeat.progress["recovery_location"] == RUINS
    assert "Poente" in defeat.progress["recovery_brazier"]
    async with sessions() as session:
        character = await session.get(Character, character_id)
        failed_activity = await session.get(GameActivity, combat.activity_id)
        assert character is not None
        assert character.hp == character.max_hp and character.vigor == vigor
        assert failed_activity is not None and failed_activity.status == "failed"
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{P5_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        ) is None
    retry = await service.action(actor, defeat.state_version, "retry")
    assert retry is not None and retry.kind == "combat" and retry.step == 3
    assert retry.activity_id != combat.activity_id
    assert retry.combat.fighters["enemy"].name == SUNSET_CUSTODIAN.name
    assert retry.combat.fighters["enemy"].level == 9
    assert retry.combat.variant is None
    assert retry.progress["awaiting_retry"] is False
