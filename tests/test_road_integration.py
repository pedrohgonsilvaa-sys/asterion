from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.road import ROAD, RoadService
from asterion.domain.combat import allowed_actions
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BlockedDelivery,
    Brazier,
    Character,
    EquipmentItem,
    GameActivity,
    HuntContext,
    MaterialStack,
    PendingItem,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


async def _seed_road(database, actor=771100, vigor=100):
    _, sessions = database
    cid = uuid4()
    async with sessions() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=cid,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.3-baseline-1.0",
                level=1,
                xp=2720,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=vigor,
                max_vigor=100,
                crowns=0,
            )
        )
        await session.flush()
        session.add_all(
            [
                Brazier(character_id=cid, brazier_id="tdo.brazier.estrada"),
                Brazier(character_id=cid, brazier_id="tdo.brazier.refugio_do_ocaso"),
                WorldState(character_id=cid, region="Terras do Ocaso", location="Refúgio do Ocaso"),
                Unlock(character_id=cid, unlock_id="hunt_manual.estrada_das_cinzas"),
                Unlock(character_id=cid, unlock_id="explore.estrada_das_cinzas"),
            ]
        )
        await session.commit()
    return actor, RoadService(sessions, "ocaso")


@pytest.mark.asyncio
async def test_road_travel_and_hunt_reconnect_are_persistent(database):
    actor, service = await _seed_road(database)
    refuge = await service.resume(actor)
    assert refuge.kind == "refuge"
    road = await service.travel(actor, ROAD)
    assert road.kind == "road"
    assert road.location == ROAD
    combat = await service.start_hunt(actor)
    assert combat.kind == "combat"
    assert combat.activity_id != combat.encounter_id != combat.combat_id
    resumed = await service.resume(actor)
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    assert set(allowed_actions(resumed.combat)) >= {"attack", "defend", "art"}


@pytest.mark.asyncio
async def test_hunt_victory_receipt_reconstructs_without_duplicate_reward(database):
    actor, service = await _seed_road(database, 771104)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "hunt_victory"
    receipt = (view.creature, view.variant, view.reward_lines)
    resumed = await service.resume(actor)
    assert resumed.kind == "hunt_victory"
    assert (resumed.creature, resumed.variant, resumed.reward_lines) == receipt
    await service.acknowledge_result(actor)
    assert (await service.resume(actor)).kind == "road"


@pytest.mark.asyncio
async def test_road_exploration_result_is_persisted_once(database):
    actor, service = await _seed_road(database, 771101)
    await service.travel(actor, ROAD)
    first = await service.explore(actor)
    assert first.kind in {"exploration", "combat"}
    async with database[1]() as session:
        from asterion.infrastructure.db.models import ExplorationAttempt

        attempts = (await session.scalars(select(ExplorationAttempt))).all()
        assert len(attempts) == 1
        assert attempts[0].seed


@pytest.mark.asyncio
async def test_exploration_combat_pays_xp_crowns_material_and_vigor(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771102, vigor=100)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.dog_cinereo", "Cão"),
    )
    view = await service.explore(actor)
    assert view.kind == "combat"
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "exploration"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2960
        assert character.crowns == 20
        assert character.vigor == 96
        assert (await session.scalar(select(func.count(RewardEvent.id)).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == f"explore:{view.attempt_id}",
        ))) == 1
        assert (await session.scalar(select(func.count(RewardComponent.id)).join(RewardEvent).where(
            RewardEvent.character_id == character.id,
            RewardEvent.source_id == f"explore:{view.attempt_id}",
        ))) >= 2
        assert (
            await session.scalar(
                select(func.count(MaterialStack.id)).where(
                    MaterialStack.character_id == character.id
                )
            )
        ) >= 1


@pytest.mark.asyncio
async def test_exploration_combat_with_low_vigor_only_pays_quarter_xp(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771103, vigor=3)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.dog_cinereo", "Cão"),
    )
    view = await service.explore(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2780
        assert character.crowns == 0
        assert character.vigor == 3
        assert (await session.scalar(select(func.count(MaterialStack.id)).where(
            MaterialStack.character_id == character.id
        ))) == 0


@pytest.mark.asyncio
async def test_inventory_slots_pending_cap_and_overflow_are_auditable(database):
    actor, service = await _seed_road(database, 771105)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        stack = MaterialStack(
            character_id=character.id,
            material_id="material.test.merge",
            quantity=998,
            bound=False,
        )
        session.add(stack)
        await session.flush()
        await service._deliver_material(
            session, character, "material.test.merge", 2, "merge-overflow"
        )
        await session.flush()
        assert stack.quantity == 999
        material_stacks = (
            await session.scalars(
                select(MaterialStack)
                .where(
                    MaterialStack.character_id == character.id,
                    MaterialStack.material_id == "material.test.merge",
                )
                .order_by(MaterialStack.id)
            )
        ).all()
        assert sorted(item.quantity for item in material_stacks) == [1, 999]
        assert await session.scalar(
            select(PendingItem).where(PendingItem.source_key == "merge-overflow")
        ) is None

        for index in range(58):
            session.add(MaterialStack(
                character_id=character.id,
                material_id=f"material.test.slot.{index}",
                quantity=1,
                bound=False,
            ))
        await session.flush()
        await service._deliver_material(
            session, character, "material.test.last", 1, "slot-60"
        )
        await service._deliver_material(
            session, character, "material.test.pending", 1, "slot-pending"
        )
        for index in range(17):
            session.add(PendingItem(
                character_id=character.id,
                source_key=f"pending.fill.{index}",
                kind="material",
                payload={"material_id": f"material.fill.{index}"},
                quantity=1,
            ))
        await session.flush()
        await service._pending(
            session, character.id, "pending.twentieth", "material",
            {"material_id": "material.twentieth"},
        )
        await service._pending(
            session, character.id, "pending.blocked", "material",
            {"material_id": "material.blocked"},
        )
        await session.flush()
        assert (
            await session.scalar(
                select(func.count(PendingItem.id)).where(PendingItem.character_id == character.id)
            )
        ) == 20
        assert character.delivery_blocked is True
        blocked = await session.scalar(
            select(BlockedDelivery).where(BlockedDelivery.source_key == "pending.blocked")
        )
        assert blocked is not None
        assert blocked.kind == "material"
        assert blocked.payload == {"material_id": "material.blocked"}
        assert blocked.quantity == 1
        await session.commit()


@pytest.mark.asyncio
async def test_full_inventory_and_pending_hold_concrete_equipment_without_loss(database):
    actor, service = await _seed_road(database, 771109)
    await service.travel(actor, ROAD)
    payload = materialize_equipment("blocked-equipment", "Raro", 1)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        for index in range(60):
            session.add(
                EquipmentItem(
                    character_id=character.id,
                    source_key=f"fill.equipment.{index}",
                    item_name=f"Item {index}",
                    rarity="Comum",
                    slot="Principal",
                    item_level=1,
                    bound=False,
                    payload={},
                )
            )
        for index in range(20):
            session.add(
                PendingItem(
                    character_id=character.id,
                    source_key=f"fill.pending.{index}",
                    kind="material",
                    payload={"material_id": f"material.fill.{index}"},
                    quantity=1,
                )
            )
        await session.flush()
        await service._pending(
            session,
            character.id,
            "blocked.equipment",
            "equipment",
            payload,
        )
        await session.flush()
        hold = await session.scalar(
            select(BlockedDelivery).where(BlockedDelivery.source_key == "blocked.equipment")
        )
        assert hold is not None
        assert hold.payload == payload
        assert hold.quantity == 1
        assert character.delivery_blocked is True
        await session.commit()

    blocked_view = await service.start_hunt(actor)
    assert blocked_view is not None and blocked_view.kind == "road"

    async with database[1]() as session:
        pending = await session.scalar(
            select(PendingItem).where(PendingItem.source_key == "fill.pending.0")
        )
        await session.delete(pending)
        await session.commit()
    assert await service.retry_blocked_deliveries(actor) is True
    assert await service.retry_blocked_deliveries(actor) is True
    async with database[1]() as session:
        hold = await session.scalar(
            select(BlockedDelivery).where(BlockedDelivery.source_key == "blocked.equipment")
        )
        queued = await session.scalar(
            select(PendingItem).where(PendingItem.source_key == "blocked.equipment")
        )
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert hold.status == "resolved"
        assert queued is not None and queued.payload == payload
        assert character.delivery_blocked is False


@pytest.mark.asyncio
async def test_bestiary_observed_at_seven_and_known_at_ten(database):
    actor, service = await _seed_road(database, 771107)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await service._bestiary(session, character.id, "dog_cinereo")
        await session.flush()
        entry = await session.scalar(select(BestiaryEntry).where(
            BestiaryEntry.character_id == character.id,
            BestiaryEntry.creature_id == "dog_cinereo",
        ))
        assert (entry.bkp, entry.stage) == (7, "observed")
        await service._add_bestiary_evidence(
            session, entry, character.id, "dog_cinereo", "test.known", "test", 3
        )
        await service._bestiary(session, character.id, "dog_cinereo")
        assert entry.stage == "known"


@pytest.mark.asyncio
async def test_hunt_receipt_persists_equipment_rune_and_bestiary_details(database):
    actor, service = await _seed_road(database, 771108)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        activity = GameActivity(
            character_id=character.id,
            content_id="road_manual_hunt",
            status="completed",
            state_version=1,
            ruleset_version="gdd-1.4.3-baseline-1.0",
        )
        session.add(activity)
        await session.flush()
        session.add(HuntContext(
            game_activity_id=activity.id,
            character_id=character.id,
            creature_id="dog_cinereo",
            category="common",
            enemy_level=1,
            variant="furious",
            seed="receipt-seed",
            loot_profile="hunt",
        ))
        event = RewardEvent(character_id=character.id, source_id=f"activity:{activity.id}")
        session.add(event)
        await session.flush()
        session.add_all([
            RewardComponent(
                reward_event_id=event.id,
                kind="equipment",
                item_id="Arma do Caminhante",
                quantity=1,
                payload={
                    "item_name": "Arma do Caminhante",
                    "enhancement": 0,
                    "rarity": "Raro",
                    "slot": "Principal",
                    "item_level": 1,
                    "bound": False,
                },
            ),
            RewardComponent(
                reward_event_id=event.id,
                kind="rune",
                item_id="Brasa",
                quantity=1,
                payload={
                    "family": "Brasa",
                    "rarity": "Rara",
                    "grade": 1,
                    "potency": "0.35%",
                    "bound": False,
                },
            ),
            RewardComponent(
                reward_event_id=event.id,
                kind="bestiary",
                item_id="dog_cinereo",
                quantity=1,
                payload={
                    "creature_name": "Cão Cinéreo",
                    "stage": "known",
                    "stage_label": "Conhecido",
                },
            ),
        ])
        await session.commit()

    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.character_id == character.id)
        )
        immediate = await service._hunt_victory_view(session, character, activity)
    resumed = await service.resume(actor)
    assert immediate is not None and resumed is not None
    assert immediate.reward_lines == resumed.reward_lines
    assert any(
        "Arma do Caminhante · +0" in line and "Nível do Item 1" in line
        for line in immediate.reward_lines
    )
    assert any(
        "🔮 Runa Brasa · Rara · Grau 1 · Negociável" == line
        for line in immediate.reward_lines
    )
    assert any(
        "📖 Bestiário · Cão Cinéreo · Conhecido" == line
        for line in immediate.reward_lines
    )


@pytest.mark.asyncio
async def test_bestiary_variant_repetition_and_alpha_requirements(database):
    actor, service = await _seed_road(database, 771106)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await service._bestiary(
            session, character.id, "dog_cinereo", variant="furious"
        )
        await session.flush()
        for _ in range(5):
            await service._bestiary(
                session, character.id, "dog_cinereo", victory=True, variant="furious"
            )
        dog = await session.scalar(select(BestiaryEntry).where(
            BestiaryEntry.character_id == character.id,
            BestiaryEntry.creature_id == "dog_cinereo",
        ))
        assert dog.wins == 5
        assert dog.bkp >= 30
        assert dog.stage == "studied"

        await service._bestiary(
            session, character.id, "alfa_cinereo", victory=True, elite=True
        )
        alpha = await session.scalar(select(BestiaryEntry).where(
            BestiaryEntry.character_id == character.id,
            BestiaryEntry.creature_id == "alfa_cinereo",
        ))
        await service._add_bestiary_evidence(
            session, alpha, character.id, "alfa_cinereo", "mechanic:bleed", "mechanic", 5
        )
        await service._add_bestiary_evidence(
            session, alpha, character.id, "alfa_cinereo", "mechanic:prepared_leap", "mechanic", 5
        )
        alpha.bkp = 45
        await service._bestiary(
            session, character.id, "alfa_cinereo", victory=True, elite=True
        )
        assert alpha.stage == "dominated"
