from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.p2 import (
    ASH_POINT_IDS,
    CHARNECA_LOCATION_ID,
    CODEX_MARKS_ENTRY,
    EXPLORE_UNLOCK,
    HUNT_UNLOCK,
    P2_COMBAT_CONTENT_ID,
    P2_ID,
    P2_REWARD_SOURCE,
    P2_VERSION,
    ROUTE_UNLOCK,
    P2Service,
)
from asterion.application.progression import level_xp
from asterion.domain.combat_math import resolve_combat_stats
from asterion.domain.road import SPIDER
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BestiaryEvidence,
    BlockedDelivery,
    Character,
    CodexEntry,
    ConsumableStack,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    MaterialStack,
    PendingItem,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


async def _seed(
    database,
    actor,
    *,
    level=3,
    xp=0,
    p1_status="completed",
    location="Refúgio do Ocaso",
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats("sentinela", level, "remanescente")
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Hero{chr(ord('a') + actor % 26)}",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=xp,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=77,
                max_vigor=100,
                crowns=11,
            )
        )
        await session.flush()
        session.add(
            Quest(
                character_id=character_id,
                quest_id="P1",
                title="Vozes na Estrada",
                status=p1_status,
                step=7,
                content_version="tdo-1.0.2",
            )
        )
        session.add(
            WorldState(
                character_id=character_id,
                region="Terras do Ocaso",
                location=location,
            )
        )
    return character_id, P2Service(sessions, "ocaso")


async def _start_combat(service, actor, order=ASH_POINT_IDS):
    view = await service.alda(actor)
    assert view is not None and view.available
    view = await service.accept(actor, view.state_version)
    assert view is not None and view.status == "active" and view.step == 1
    view = await service.travel_to_charneca(actor, view.state_version)
    assert view is not None and view.step == 2 and view.location == "Charneca da Fuligem"
    for point in order:
        view = await service.examine_ash_point(actor, point, view.state_version)
    assert view is not None and view.step == 3 and view.kind == "combat"
    return view


def _finish_with(outcome):
    def finish(combat, action):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = outcome
        if outcome == "defeat":
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


async def _complete_p2(service, actor, monkeypatch):
    import asterion.application.p2 as p2_module

    combat = await _start_combat(service, actor)
    monkeypatch.setattr(p2_module, "act", _finish_with("victory"))
    victory = await service.action(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    stone = await service.examine_pedra_marcada(actor, victory.state_version)
    refuge = await service.return_to_refuge(actor, stone.state_version)
    oren = await service.oren(actor, refuge.state_version)
    final = await service.report_to_alda(actor, oren.state_version)
    return combat, victory, stone, refuge, oren, final


@pytest.mark.asyncio
async def test_p2_offer_gate_is_explicit_and_acceptance_creates_one_quest(database):
    incomplete_id, incomplete = await _seed(
        database, 881001, p1_status="active"
    )
    low_level_id, low_level = await _seed(database, 881002, level=2)
    wrong_location_id, wrong_location = await _seed(
        database, 881003, location="Estrada das Cinzas"
    )

    for actor, service in (
        (881001, incomplete),
        (881002, low_level),
        (881003, wrong_location),
    ):
        offer = await service.alda(actor)
        assert offer is not None and not offer.available

    character_id, service = await _seed(database, 881004)
    s1_character_id, s1_service = await _seed(database, 881011)
    async with database[1]() as session:
        session.add(
            Quest(
                character_id=s1_character_id,
                quest_id="S1",
                title="Luzes Sob as Cinzas",
                status="active",
                step=1,
                content_version="tdo-1.0.2",
            )
        )
        await session.commit()
    assert (await s1_service.alda(881011)).available
    async with database[1]() as session:
        s1 = await session.scalar(
            select(Quest).where(
                Quest.character_id == s1_character_id, Quest.quest_id == "S1"
            )
        )
        s1.status = "completed"
        await session.commit()
    assert (await s1_service.alda(881011)).available

    offer = await service.alda(881004)
    assert offer is not None and offer.available and offer.kind == "offer"
    async with database[1]() as session:
        assert not await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P2_ID
            )
        )

    active = await service.accept(881004, offer.state_version)
    assert active is not None and active.status == "active" and active.step == 1
    assert (await P2Service(database[1], "ocaso").resume(881004)).step == 1
    duplicate = await service.accept(881004, offer.state_version)
    assert duplicate is not None and duplicate.step == 1
    async with database[1]() as session:
        quests = (
            await session.scalars(
                select(Quest).where(
                    Quest.character_id == character_id, Quest.quest_id == P2_ID
                )
            )
        ).all()
        assert len(quests) == 1
        assert quests[0].content_version == P2_VERSION == "tdo-1.0.7"
        assert quests[0].step == 1
        assert not await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == "S1"
            )
        )
        assert incomplete_id != low_level_id != wrong_location_id


@pytest.mark.asyncio
async def test_p2_offer_and_travel_are_blocked_by_incompatible_foreground(database):
    character_id, service = await _seed(database, 881010)
    async with database[1]() as session:
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="other.active.activity",
                status="active",
                state_version=0,
                ruleset_version="gdd-1.4.7-baseline-1.0",
            )
        )
        await session.commit()

    offer = await service.alda(881010)
    assert offer is not None and not offer.available and offer.blocked_by_foreground
    rejected = await service.accept(881010, 0)
    assert rejected is not None and rejected.status is None
    async with database[1]() as session:
        assert not await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P2_ID
            )
        )
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.character_id == character_id)
        )
        activity.status = "completed"
        await session.commit()

    accepted = await service.accept(881010, 0)
    assert accepted is not None and accepted.step == 1
    async with database[1]() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.character_id == character_id)
        )
        activity.status = "active"
        await session.commit()
    blocked_travel = await service.travel_to_charneca(
        881010, accepted.state_version
    )
    assert blocked_travel is not None and blocked_travel.step == 1
    assert blocked_travel.location == "Refúgio do Ocaso"
    async with database[1]() as session:
        assert not await session.scalar(
            select(LocationDiscovery).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CHARNECA_LOCATION_ID,
            )
        )


@pytest.mark.asyncio
async def test_p2_discovery_ash_points_observation_and_reconnect_are_idempotent(
    database,
):
    character_id, service = await _seed(database, 881005)
    offer = await service.alda(881005)
    active = await service.accept(881005, offer.state_version)
    view = await service.travel_to_charneca(881005, active.state_version)
    view = await service.examine_ash_point(881005, ASH_POINT_IDS[2], view.state_version)
    duplicate = await service.examine_ash_point(
        881005, ASH_POINT_IDS[2], view.state_version
    )
    assert duplicate.progress["ash_points"] == [ASH_POINT_IDS[2]]
    resumed_one = await P2Service(database[1], "ocaso").resume(881005)
    assert resumed_one.step == 2 and len(resumed_one.progress["ash_points"]) == 1
    view = await service.examine_ash_point(881005, ASH_POINT_IDS[0], duplicate.state_version)
    resumed_two = await P2Service(database[1], "ocaso").resume(881005)
    assert resumed_two.step == 2 and len(resumed_two.progress["ash_points"]) == 2
    combat = await service.examine_ash_point(
        881005, ASH_POINT_IDS[1], view.state_version
    )

    async with database[1]() as session:
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P2_ID
            )
        )
        assert set(quest.progress["ash_points"]) == set(ASH_POINT_IDS)
        assert quest.step == 3
        assert await session.scalar(
            select(func.count(LocationDiscovery.id)).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == CHARNECA_LOCATION_ID,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == ROUTE_UNLOCK,
            )
        ) == 1
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        ) == 1
        assert not await session.scalar(
            select(HuntContext).where(HuntContext.character_id == character_id)
        )
        character = await session.get(Character, character_id)
        assert character.crowns == 11
        assert not await session.scalar(
            select(MaterialStack).where(MaterialStack.character_id == character_id)
        )
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == SPIDER.creature_id,
            )
        )
        assert entry is not None
        assert await session.scalar(
            select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == SPIDER.creature_id,
                BestiaryEvidence.evidence_id == f"habitat:{CHARNECA_LOCATION_ID}",
            )
        )
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == f"bestiary:observation:{character_id}:{SPIDER.creature_id}",
            )
        )
        assert event is not None
        component = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == event.id
            )
        )
        assert component.quantity == 66
        character = await session.get(Character, character_id)
        assert character.level == 3
        assert character.xp == 66

    resumed = await type(service)(database[1], "ocaso").resume(881005)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    assert resumed.combat.fighters["enemy"].name == SPIDER.name
    assert resumed.combat.fighters["enemy"].level == 3
    assert resumed.combat.variant is None
    assert SPIDER.category == "uncommon"

    stale = await service.examine_ash_point(881005, ASH_POINT_IDS[1], combat.state_version)
    assert stale is not None and stale.step == 3
    async with database[1]() as session:
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
            )
        ) == 1


@pytest.mark.asyncio
async def test_p2_defeat_recovers_then_retry_reuses_spider_without_observation_xp(
    database, monkeypatch
):
    import asterion.application.p2 as p2_module

    actor = 881006
    starting_xp = level_xp(3) - 40
    character_id, service = await _seed(database, actor, xp=starting_xp)
    combat = await _start_combat(service, actor)
    async with database[1]() as session:
        session.add(
            ConsumableStack(
                character_id=character_id,
                consumable_id="consumable.erva_cinzenta",
                quantity=2,
            )
        )
        await session.commit()
    monkeypatch.setattr(p2_module, "act", _finish_with("defeat"))
    defeated = await service.action(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeated is not None and defeated.step == 3
    assert defeated.kind == "recovery" and defeated.location == "Refúgio do Ocaso"
    assert defeated.activity_status == "failed"
    resumed_defeat = await P2Service(database[1], "ocaso").resume(actor)
    assert resumed_defeat.kind == "recovery" and resumed_defeat.step == 3

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.level == 4
        assert character.xp == 26
        assert character.hp == character.max_hp
        assert character.vigor == 77
        consumable = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character_id,
                ConsumableStack.consumable_id == "consumable.erva_cinzenta",
            )
        )
        assert consumable.quantity == 2
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id.like(f"{P2_REWARD_SOURCE}:enemy-xp:%"),
            )
        ) == 0
        assert await session.scalar(
            select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == SPIDER.creature_id,
                BestiaryEvidence.evidence_id == "first_observation",
            )
        )
        assert not await session.scalar(
            select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == SPIDER.creature_id,
                BestiaryEvidence.evidence_id == "first_victory",
            )
        )

    retried = await service.return_to_charneca(actor, defeated.state_version)
    assert retried is not None and retried.kind == "combat"
    assert retried.location == "Charneca da Fuligem"
    assert retried.activity_id != defeated.activity_id
    assert retried.encounter_id != defeated.encounter_id
    assert retried.combat_id != defeated.combat_id
    assert retried.combat.fighters["enemy"].name == SPIDER.name
    assert retried.combat.fighters["enemy"].level == 3
    assert retried.combat.variant is None
    repeated = await service.return_to_charneca(actor, defeated.state_version)
    assert repeated is not None
    assert repeated.activity_id == retried.activity_id
    async with database[1]() as session:
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        ) == 1
        observation_events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id.like("bestiary:observation:%"),
                )
            )
        ).all()
        assert len(observation_events) == 1
        character = await session.get(Character, character_id)
        assert character.vigor == 77
        assert character.xp == 26


@pytest.mark.asyncio
async def test_p2_victory_pedra_return_and_final_reward_are_idempotent(
    database, monkeypatch
):
    import asterion.application.p2 as p2_module

    actor = 881007
    character_id, service = await _seed(
        database, actor, xp=level_xp(3) - 100
    )
    combat = await _start_combat(service, actor)
    monkeypatch.setattr(p2_module, "act", _finish_with("victory"))
    victory = await service.action(
        actor, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert victory is not None and victory.step == 4
    assert victory.location == "Charneca da Fuligem"
    assert victory.activity_status == "completed"
    assert (await P2Service(database[1], "ocaso").resume(actor)).step == 4

    async with database[1]() as session:
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id
                == f"{P2_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        )
        xp_component = await session.scalar(
            select(RewardComponent).where(
                RewardComponent.reward_event_id == event.id
            )
        )
        assert xp_component.quantity == 370
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == SPIDER.creature_id,
            )
        )
        assert entry.wins == 1
        assert await session.scalar(
            select(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character_id,
                BestiaryEvidence.creature_id == SPIDER.creature_id,
                BestiaryEvidence.evidence_id == "first_victory",
            )
        )
        assert not await session.scalar(
            select(HuntContext).where(HuntContext.character_id == character_id)
        )
        character = await session.get(Character, character_id)
        assert character.crowns == 11
        assert not await session.scalar(
            select(MaterialStack).where(MaterialStack.character_id == character_id)
        )

    stone = await service.examine_pedra_marcada(actor, victory.state_version)
    repeated_stone = await service.examine_pedra_marcada(
        actor, victory.state_version
    )
    assert stone is not None and stone.progress["stone_examined"]
    assert repeated_stone is not None and repeated_stone.state_version == stone.state_version
    async with database[1]() as session:
        assert await session.scalar(
            select(CodexEntry).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == CODEX_MARKS_ENTRY,
            )
        )
        assert not await session.scalar(
            select(LocationDiscovery).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "tdo.location.pedra_marcada",
            )
        )
        assert not await session.scalar(
            select(HuntContext).where(HuntContext.character_id == character_id)
        )

    refuge = await service.return_to_refuge(actor, stone.state_version)
    assert refuge is not None and refuge.step == 5
    assert refuge.location == "Refúgio do Ocaso"
    assert (await P2Service(database[1], "ocaso").resume(actor)).step == 5
    oren = await service.oren(actor, refuge.state_version)
    assert oren.step == 6
    assert (await P2Service(database[1], "ocaso").resume(actor)).step == 6
    final = await service.report_to_alda(actor, (await service.resume(actor)).state_version)
    assert final is not None and final.status == "completed"
    assert final.location == "Refúgio do Ocaso"
    repeated = await service.report_to_alda(actor, final.state_version)
    assert repeated is not None and repeated.status == "completed"
    assert not (await service.alda(actor)).available
    assert (await service.accept(actor, 0)).status == "completed"

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.level == 4
        assert character.xp == 3636
        assert character.crowns == 11 + 140
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P2_REWARD_SOURCE,
            )
        ) == 1
        components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P2_REWARD_SOURCE,
                )
                .order_by(RewardComponent.kind, RewardComponent.item_id)
            )
        ).all()
        assert sorted((row.kind, row.item_id, row.quantity) for row in components) == sorted(
            [
                ("xp", None, 3300),
                ("crowns", None, 140),
                ("material", "material.tdo.ferro_de_fuligem", 1),
                ("material", "material.tdo.erva_cinzenta", 2),
                ("material", "material.tdo.residuo_ocaso", 1),
            ]
        )
        assert all(row.payload.get("bound") for row in components if row.kind == "material")
        stacks = (
            await session.scalars(
                select(MaterialStack).where(MaterialStack.character_id == character_id)
            )
        ).all()
        assert {(row.material_id, row.quantity, row.bound) for row in stacks} == {
            ("material.tdo.ferro_de_fuligem", 1, True),
            ("material.tdo.erva_cinzenta", 2, True),
            ("material.tdo.residuo_ocaso", 1, True),
        }
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id, Unlock.unlock_id == HUNT_UNLOCK
            )
        )
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id, Unlock.unlock_id == EXPLORE_UNLOCK
            )
        )
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id, Unlock.unlock_id == ROUTE_UNLOCK
            )
        )
        assert not await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id.like("hunt_round.charneca%"),
            )
        )
        unlock_ids = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(
                        Unlock.character_id == character_id
                    )
                )
            ).all()
        )
        assert unlock_ids == {ROUTE_UNLOCK, HUNT_UNLOCK, EXPLORE_UNLOCK}
        assert await session.scalar(
            select(func.count(RewardComponent.id)).join(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P2_REWARD_SOURCE,
            )
        ) == 5
        quest = await session.scalar(
            select(Quest).where(
                Quest.character_id == character_id, Quest.quest_id == P2_ID
            )
        )
        assert quest.status == "completed" and quest.progress["completed"]
        assert not await session.scalar(
            select(GameActivity).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == P2_COMBAT_CONTENT_ID,
                GameActivity.status == "active",
            )
        )


@pytest.mark.asyncio
async def test_p2_final_reward_materials_use_pending_when_inventory_is_full(
    database, monkeypatch
):
    actor = 881008
    character_id, service = await _seed(database, actor)
    async with database[1]() as session:
        for index in range(60):
            session.add(
                MaterialStack(
                    character_id=character_id,
                    material_id=f"material.fill.{index}",
                    quantity=1,
                    bound=False,
                )
            )
        await session.commit()

    _, _, _, _, _, final = await _complete_p2(service, actor, monkeypatch)
    assert final is not None and final.status == "completed"

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.delivery_blocked is False
        pending = (
            await session.scalars(
                select(PendingItem).where(
                    PendingItem.character_id == character_id,
                    PendingItem.source_key.like(f"{P2_REWARD_SOURCE}:material:%"),
                )
            )
        ).all()
        assert len(pending) == 3
        assert {
            (row.payload["material_id"], row.quantity, row.payload["bound"])
            for row in pending
        } == {
            ("material.tdo.ferro_de_fuligem", 1, True),
            ("material.tdo.erva_cinzenta", 2, True),
            ("material.tdo.residuo_ocaso", 1, True),
        }
        assert not await session.scalar(
            select(BlockedDelivery).where(
                BlockedDelivery.character_id == character_id,
                BlockedDelivery.source_key.like(f"{P2_REWARD_SOURCE}:material:%"),
            )
        )
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P2_REWARD_SOURCE,
            )
        ) == 1


@pytest.mark.asyncio
async def test_p2_final_reward_materials_use_blocked_delivery_when_both_are_full(
    database, monkeypatch
):
    actor = 881009
    character_id, service = await _seed(database, actor)
    async with database[1]() as session:
        for index in range(60):
            session.add(
                MaterialStack(
                    character_id=character_id,
                    material_id=f"material.fill.{index}",
                    quantity=1,
                    bound=False,
                )
            )
        for index in range(20):
            session.add(
                PendingItem(
                    character_id=character_id,
                    source_key=f"pending.fill.{index}",
                    kind="material",
                    payload={"material_id": f"material.pending.{index}"},
                    quantity=1,
                )
            )
        await session.commit()

    _, _, _, _, _, final = await _complete_p2(service, actor, monkeypatch)
    assert final is not None and final.status == "completed"

    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.delivery_blocked is True
        holds = (
            await session.scalars(
                select(BlockedDelivery).where(
                    BlockedDelivery.character_id == character_id,
                    BlockedDelivery.source_key.like(f"{P2_REWARD_SOURCE}:material:%"),
                )
            )
        ).all()
        assert len(holds) == 3
        assert {hold.status for hold in holds} == {"pending"}
        assert {
            hold.source_key.removeprefix(f"{P2_REWARD_SOURCE}:material:")
            for hold in holds
        } == {
            "material.tdo.ferro_de_fuligem",
            "material.tdo.erva_cinzenta",
            "material.tdo.residuo_ocaso",
        }
        assert await session.scalar(
            select(func.count(PendingItem.id)).where(
                PendingItem.character_id == character_id
            )
        ) == 20
