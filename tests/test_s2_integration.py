from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import select

from asterion.application.active_arts import ActiveArtService
from asterion.application.groups import GroupError, GroupService
from asterion.application.road import CHARNECA, REFUGE, RoadService
from asterion.application.s2 import (
    S2_CODEX_ENTRY,
    S2_ID,
    S2_REWARD_SOURCE,
    S2Service,
)
from asterion.domain.arts import FIRST_CLASS_ART_IDS
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    ConsumableStack,
    GameActivity,
    HuntContext,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts
from tests.test_p2_integration import _seed as _seed_p2_character


async def _seed_s2(database, actor: int, *, level: int = 4, p2_status: str = "completed"):
    character_id, _ = await _seed_p2_character(database, actor, level=level)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.id == character_id)
        )
        character.level = level
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P2",
                title="Fuligem sem Fogo",
                status=p2_status,
                step=6 if p2_status == "completed" else 1,
                content_version="tdo-1.0.7",
            )
        )
        session.add(
            Unlock(
                character_id=character_id,
                unlock_id="route.tdo.refugio_charneca",
            )
        )
    return character_id, S2Service(sessions, "ocaso")


async def _start_scripted_combat(service: S2Service, actor: int):
    view = await service.accept(actor)
    assert view is not None and view.status == "active" and view.step == 1
    async with service.sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = CHARNECA
    view = await service.find_camp(actor, view.state_version)
    assert view is not None and view.step == 2 and view.progress["camp_found"]
    for vestige in ("s2.vestige.3", "s2.vestige.1", "s2.vestige.2"):
        view = await service.examine_vestige(actor, vestige, view.state_version)
    assert view is not None and view.kind == "combat" and view.combat is not None
    return view


def _terminal(result: str):
    def finish(combat, action, **_kwargs):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


@pytest.mark.asyncio
async def test_s2_gate_and_offer_do_not_create_quest(database):
    low_id, low = await _seed_s2(database, 997101, level=3)
    active_id, active = await _seed_s2(database, 997102, p2_status="active")
    eligible_id, eligible = await _seed_s2(database, 997103)

    assert not (await low.oren(997101)).available
    assert not (await active.oren(997102)).available
    offer = await eligible.oren(997103)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    assert (await eligible.offer(997103)).kind == "offer"
    async with database[1]() as session:
        for character_id in (low_id, active_id, eligible_id):
            assert await session.scalar(
                select(Quest).where(
                    Quest.character_id == character_id,
                    Quest.quest_id == S2_ID,
                )
            ) is None

    accepted = await eligible.accept(997103, offer.state_version)
    assert accepted.status == "active" and accepted.step == 1
    duplicate = await eligible.accept(997103, offer.state_version)
    assert duplicate.status == "active" and duplicate.state_version == accepted.state_version
    async with database[1]() as session:
        quests = (
            await session.scalars(
                select(Quest).where(
                    Quest.character_id == eligible_id,
                    Quest.quest_id == S2_ID,
                )
            )
        ).all()
        assert len(quests) == 1


@pytest.mark.asyncio
async def test_s2_camp_vestiges_and_combat_are_persistent_and_fixed(database):
    character_id, service = await _seed_s2(database, 997104)
    art_id = FIRST_CLASS_ART_IDS["sentinela"]
    async with database[1].begin() as session:
        await add_compatible_weapon_for_arts(session, character_id, (art_id,))
    equipped = await ActiveArtService(database[1], "ocaso").equip_art(997104, 1, art_id)
    assert equipped is not None and equipped.combat_configuration_version == 1
    accepted = await service.accept(997104)
    blocked = await service.find_camp(997104, accepted.state_version)
    assert not blocked.progress.get("camp_found")

    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.id == character_id)
        )
        character.vigor = 37
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world.location = CHARNECA

    camp = await service.find_camp(997104, accepted.state_version)
    assert camp.step == 2 and camp.progress["camp_found"] is True
    first = await service.examine_vestige(997104, "s2.vestige.3", camp.state_version)
    duplicate_stale = await service.examine_vestige(
        997104, "s2.vestige.3", camp.state_version
    )
    assert duplicate_stale.progress["vestiges"] == ["s2.vestige.3"]
    assert duplicate_stale.state_version == first.state_version
    second = await service.examine_vestige(
        997104, "s2.vestige.1", first.state_version
    )
    combat = await service.examine_vestige(
        997104, "s2.vestige.2", second.state_version
    )
    assert combat.kind == "combat"
    assert combat.activity_id and combat.encounter_id and combat.combat_id
    assert combat.activity_id != combat.encounter_id
    assert combat.activity_id != combat.combat_id
    assert combat.encounter_id != combat.combat_id
    assert combat.combat.fighters["enemy"].name == "Peregrino Calcinado"
    assert combat.combat.fighters["enemy"].level == 4
    assert combat.consumable_budget_limit == 1
    assert art_id in combat.combat.player_actions
    assert combat.combat.configuration_snapshot["active_arts"] == [
        {"slot": 1, "art_id": art_id}
    ]

    resumed = await service.resume(997104)
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    async with database[1]() as session:
        assert await session.scalar(
            select(HuntContext).where(
                HuntContext.game_activity_id == combat.activity_id
            )
        ) is None
        assert await session.scalar(
            select(GameActivity).where(GameActivity.id == combat.activity_id)
        ) is not None
        character = await session.scalar(
            select(Character).where(Character.id == character_id)
        )
        assert character.vigor == 37
        assert await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "peregrino_calcinado",
            )
        ) is not None


@pytest.mark.asyncio
async def test_s2_defeat_recovers_to_refuge_and_retry_uses_new_same_encounter(
    database, monkeypatch
):
    import asterion.application.s2 as s2_module

    _, service = await _seed_s2(database, 997105)
    combat = await _start_scripted_combat(service, 997105)
    monkeypatch.setattr(s2_module, "act", _terminal("defeat"))
    defeated = await service.action(
        997105,
        combat.activity_id,
        combat.activity_state_version,
        "attack",
    )
    assert defeated.kind == "recovery"
    assert defeated.progress["awaiting_retry"] is True
    assert defeated.location == REFUGE
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == 997105)
        )
        assert character.hp == character.max_hp
        assert character.vigor == 77
        assert await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == S2_REWARD_SOURCE,
            )
        ) is None

    road = RoadService(database[1], "ocaso")
    route = await road.travel_route(997105, CHARNECA)
    assert route is not None and route.location == CHARNECA
    recovery = await service.resume(997105)
    retry = await service.retry(997105, recovery.state_version)
    assert retry.kind == "combat"
    assert retry.activity_id != combat.activity_id
    assert retry.encounter_id != combat.encounter_id
    assert retry.combat.fighters["enemy"].name == "Peregrino Calcinado"
    assert retry.combat.fighters["enemy"].level == 4


@pytest.mark.asyncio
async def test_s2_combat_consumable_uses_shared_budget_and_decrements_once(database):
    character_id, service = await _seed_s2(database, 997109)
    async with database[1].begin() as session:
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.protection.vde.ii",
                quantity=2,
            )
        )
    combat = await _start_scripted_combat(service, 997109)
    assert combat.consumable_budget_limit == 1
    assert any(
        option.item_id == "consumable.protection.vde.ii"
        for option in combat.consumable_options
    )
    option = next(
        option
        for option in combat.consumable_options
        if option.item_id == "consumable.protection.vde.ii"
    )
    used = await service.action(
        997109,
        combat.activity_id,
        combat.activity_state_version,
        consumable_id=option.item_id,
        target_id=option.target_id,
        effect_id=option.effect_id,
    )
    assert used.kind == "combat" and used.combat.consumable_uses == 1
    rejected = await service.action(
        997109,
        used.activity_id,
        used.activity_state_version,
        consumable_id=option.item_id,
        target_id=option.target_id,
        effect_id=option.effect_id,
    )
    assert rejected.kind == "combat" and rejected.combat.consumable_uses == 1
    assert rejected.consumable_notice == "⏳ Consumíveis · Em Recarga"
    async with database[1]() as session:
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.protection.vde.ii",
            )
        )
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == combat.activity_id)
        )
        assert stack.quantity == 1
        assert activity.content_id == "s2_scripted_peregrino_calcinado"


@pytest.mark.asyncio
async def test_s2_defeat_after_vento_morto_keeps_character_in_charneca(database, monkeypatch):
    import asterion.application.s2 as s2_module

    character_id, service = await _seed_s2(database, 997106)
    async with database[1].begin() as session:
        session.add(Brazier(character_id=character_id, brazier_id="tdo.brazier.vento_morto"))
    combat = await _start_scripted_combat(service, 997106)
    monkeypatch.setattr(s2_module, "act", _terminal("defeat"))
    defeated = await service.action(
        997106,
        combat.activity_id,
        combat.activity_state_version,
        "attack",
    )
    assert defeated.kind == "recovery"
    assert defeated.location == CHARNECA
    assert defeated.progress["recovery_brazier"] == "Braseiro do Vento Morto"
    retry = await service.retry(997106, defeated.state_version)
    assert retry.kind == "combat"
    assert retry.activity_id != combat.activity_id


@pytest.mark.asyncio
async def test_s2_victory_fragment_and_oren_completion_are_idempotent(database, monkeypatch):
    import asterion.application.s2 as s2_module

    character_id, service = await _seed_s2(database, 997107)
    combat = await _start_scripted_combat(service, 997107)
    monkeypatch.setattr(s2_module, "act", _terminal("victory"))
    victory = await service.action(
        997107,
        combat.activity_id,
        combat.activity_state_version,
        "attack",
    )
    assert victory.kind == "fragment" and victory.step == 5
    async with database[1]() as session:
        enemy_reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{S2_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        )
        assert enemy_reward is not None
        assert await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == enemy_reward.id,
                RewardComponent.kind == "enemy_xp",
            )
        ) is not None
        assert await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S2_REWARD_SOURCE,
            )
        ) is None

    fragment = await service.recover_fragment(997107, victory.state_version)
    stale_fragment = await service.recover_fragment(997107, victory.state_version)
    assert fragment.step == 6
    assert stale_fragment.step == 6 and stale_fragment.state_version == fragment.state_version
    async with database[1].begin() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world.location = REFUGE
    oren = await service.oren(997107)
    final = await service.complete_with_oren(997107, oren.state_version)
    assert final.status == "completed"
    duplicate = await service.complete_with_oren(997107, oren.state_version)
    assert duplicate.status == "completed"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.id == character_id)
        )
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S2_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
            )
        ).all()
        assert {(row.kind, row.item_id, row.quantity) for row in components} == {
            ("xp", None, 2695),
            ("crowns", None, 120),
            ("material", "material.tdo.erva_cinzenta", 1),
            ("material", "material.tdo.residuo_ocaso", 1),
        }
        assert character.crowns == 131
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == S2_CODEX_ENTRY,
            )
        ) is not None
        stacks = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        assert {(row.material_id, row.quantity, row.bound) for row in stacks} >= {
            ("material.tdo.erva_cinzenta", 1, True),
            ("material.tdo.residuo_ocaso", 1, True),
        }


@pytest.mark.asyncio
async def test_s2_abandon_and_reaccept_reset_only_transient_progress(database):
    character_id, service = await _seed_s2(database, 997108)
    accepted = await service.accept(997108)
    async with database[1].begin() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world.location = CHARNECA
    camp = await service.find_camp(997108, accepted.state_version)
    abandoned = await service.abandon(997108, camp.state_version)
    assert abandoned.status == "abandoned" and abandoned.progress == {}
    async with database[1].begin() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        world.location = REFUGE
    offer = await service.offer(997108)
    assert offer.reacceptable and offer.kind == "offer"
    restarted = await service.accept(997108, offer.state_version, reaccept=True)
    assert restarted.status == "active" and restarted.step == 1
    assert restarted.progress == {}


@pytest.mark.asyncio
async def test_s2_group_members_find_vestiges_alone_and_group_combat_is_refused(
    database, monkeypatch
):
    import asterion.application.s2 as s2_module

    actors = (997120, 997121, 997122)
    seeded = [await _seed_s2(database, actor) for actor in actors]
    character_ids = [row[0] for row in seeded]
    sessions = database[1]
    groups = GroupService(sessions, "ocaso")
    service = S2Service(sessions, "ocaso", groups=groups)
    for actor in actors[:2]:
        accepted = await service.accept(actor)
        assert accepted is not None and accepted.status == "active"
    async with sessions.begin() as session:
        session.add(
            Quest(
                character_id=character_ids[2],
                quest_id=S2_ID,
                title="Os Nomes Esquecidos",
                status="completed",
                step=6,
                content_version="tdo-1.0.9",
            )
        )
    async with sessions() as session:
        invitee = await session.scalar(
            select(Character).where(Character.id == character_ids[1])
        )
        assert invitee is not None
        invitee_name = invitee.name
    group = await groups.create_group(actors[0])
    invite = await groups.invite(
        actors[0], invitee_name, expected_group_revision=group.revision
    )
    group = await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )
    async with sessions() as session:
        helper = await session.scalar(select(Character).where(Character.id == character_ids[2]))
        assert helper is not None
        helper_name = helper.name
    invite = await groups.invite(
        actors[0], helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        actors[2], invite.invite_id, expected_revision=invite.revision, accept=True
    )

    async with sessions.begin() as session:
        for character_id in character_ids:
            world = await session.scalar(
                select(WorldState).where(WorldState.character_id == character_id)
            )
            world.location = CHARNECA

    async def play_to_fight(actor):
        view = await service.resume(actor)
        view = await service.find_camp(actor, view.state_version)
        assert view.step == 2
        for vestige_id in ("s2.vestige.2", "s2.vestige.1", "s2.vestige.3"):
            view = await service.examine_vestige(actor, vestige_id, view.state_version)
        return view

    # Objectives are Solo (Ação × Consequência §5): only the actor advances.
    view = await service.resume(actors[0])
    view = await service.find_camp(actors[0], view.state_version)
    assert view.step == 2
    other = await service.resume(actors[1])
    assert other.step == 1 and not other.progress.get("camp_found")
    for vestige_id in ("s2.vestige.2", "s2.vestige.1", "s2.vestige.3"):
        view = await service.examine_vestige(actors[0], vestige_id, view.state_version)
    # The fight opens as a Solo combat even though the actor belongs to a Group.
    assert view.step == 3 and view.kind == "combat" and view.group_size == 1
    other = await service.resume(actors[1])
    assert other.step == 1 and not other.progress.get("vestiges")

    # S2 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await service.propose_group_combat(actors[0], view.state_version)
    for actor in actors:
        assert not await groups.activity_proposals(actor)
    reconnected = await service.resume(actors[0])
    assert reconnected.activity_id == view.activity_id

    monkeypatch.setattr(s2_module, "act", _terminal("victory"))
    resolved = await service.action(
        actors[0], view.activity_id, view.activity_state_version, "attack"
    )
    assert resolved.step == 5 and resolved.kind == "fragment"
    assert resolved.progress["encounter_result"] == "victory"
    other = await service.resume(actors[1])
    assert other.status == "active" and other.step == 1
    helper_view = await service.resume(actors[2])
    assert helper_view.status == "completed"

    # The other member plays the same steps on their own.
    second = await play_to_fight(actors[1])
    assert second.kind == "combat" and second.group_size == 1
    second = await service.action(
        actors[1], second.activity_id, second.activity_state_version, "attack"
    )
    assert second.step == 5 and second.kind == "fragment"

    async with sessions() as session:
        quests = (
            await session.scalars(
                select(Quest).where(
                    Quest.character_id.in_(character_ids), Quest.quest_id == S2_ID
                )
            )
        ).all()
        assert {row.step for row in quests if row.status == "active"} == {5}
        helper_quest = next(
            row for row in quests if row.character_id == character_ids[2]
        )
        assert helper_quest.status == "completed"
        credited = set(
            (
                await session.scalars(
                    select(CampaignObjectiveCredit.character_id).where(
                        CampaignObjectiveCredit.character_id.in_(character_ids),
                        CampaignObjectiveCredit.quest_id == S2_ID,
                    )
                )
            ).all()
        )
        assert credited == set(character_ids[:2])
        enemy_xp_events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id.in_(character_ids),
                    RewardEvent.source_id.like(f"{S2_REWARD_SOURCE}:enemy-xp:%"),
                )
            )
        ).all()
        assert {event.character_id for event in enemy_xp_events} == set(character_ids[:2])
        assert len(enemy_xp_events) == 2
        assert await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id.in_(character_ids),
                RewardEvent.source_id == S2_REWARD_SOURCE,
            )
        ) is None
