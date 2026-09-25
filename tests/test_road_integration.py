from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from asterion.application.equipment import equipment_instance_payload
from asterion.application.progression import consolidate_level, level_xp
from asterion.application.road import REFUGE, ROAD, RoadService
from asterion.domain.combat import allowed_actions
from asterion.domain.road import materialize_equipment
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    BestiaryEvidence,
    BlockedDelivery,
    Brazier,
    Character,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    MaterialStack,
    PendingItem,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


async def _seed_road(
    database,
    actor=771100,
    vigor=100,
    p1_status="completed",
    include_p1=True,
    xp=2720,
):
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
                xp=xp,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
                vigor=vigor,
                max_vigor=100,
                crowns=0,
            )
        )
        await session.flush()
        seed_rows = [
                *([Quest(
                    character_id=cid,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status=p1_status,
                    step=7,
                    content_version="tdo-1.0.2",
                )] if include_p1 else []),
                Brazier(character_id=cid, brazier_id="tdo.brazier.estrada"),
                Brazier(character_id=cid, brazier_id="tdo.brazier.refugio_do_ocaso"),
                WorldState(character_id=cid, region="Terras do Ocaso", location="Refúgio do Ocaso"),
                Unlock(character_id=cid, unlock_id="hunt_manual.estrada_das_cinzas"),
                Unlock(character_id=cid, unlock_id="explore.estrada_das_cinzas"),
                BestiaryEntry(
                    character_id=cid,
                    creature_id="dog_cinereo",
                    bkp=7,
                    stage="observed",
                ),
                BestiaryEntry(
                    character_id=cid,
                    creature_id="corvo_fuligem",
                    bkp=7,
                    stage="observed",
                ),
            ]
        session.add_all(seed_rows)
        session.add_all(
            [
                BestiaryEvidence(
                    character_id=cid,
                    creature_id="dog_cinereo",
                    evidence_id="first_observation",
                    category="observation",
                ),
                BestiaryEvidence(
                    character_id=cid,
                    creature_id="dog_cinereo",
                    evidence_id="first_combat",
                    category="combat",
                ),
                BestiaryEvidence(
                    character_id=cid,
                    creature_id="corvo_fuligem",
                    evidence_id="first_observation",
                    category="observation",
                ),
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
async def test_active_road_foreground_dominates_stale_travel_and_prepare_callbacks(database):
    actor, service = await _seed_road(database, 771118)
    await service.travel(actor, ROAD)
    combat = await service.start_hunt(actor)

    stale_travel = await service.travel(actor, REFUGE)
    assert stale_travel.kind == "combat"
    assert (stale_travel.activity_id, stale_travel.encounter_id, stale_travel.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    async with database[1]() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == combat.character_id)
        )
        assert world.location == ROAD

    stale_prepare = await service.prepare_hunt(actor)
    assert stale_prepare.kind == "combat"
    assert (stale_prepare.activity_id, stale_prepare.encounter_id, stale_prepare.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )


@pytest.mark.asyncio
async def test_unacknowledged_hunt_result_blocks_old_start_callback(database):
    actor, service = await _seed_road(database, 771119)
    await service.travel(actor, ROAD)
    view = await service.start_hunt(actor)
    for _ in range(100):
        if view.kind != "combat":
            break
        action = "art" if "art" in allowed_actions(view.combat) else "attack"
        view = await service.action(actor, view.activity_id, view.combat.version, action)
    assert view.kind == "hunt_victory"
    blocked = await service.start_hunt(actor)
    assert blocked.kind == "hunt_victory"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(GameActivity.character_id == character.id)
        ) == 1


@pytest.mark.asyncio
async def test_unacknowledged_exploration_result_blocks_old_explore_callback(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771120)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("great_discovery", "explore.tdo.estrada.marco_viajantes", "Marco."),
    )
    first = await service.explore(actor)
    stale = await service.explore(actor)
    assert stale.attempt_id == first.attempt_id
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == character.id
            )
        ) == 1


@pytest.mark.asyncio
async def test_unacknowledged_hunt_defeat_blocks_stale_travel_callback(database):
    actor, service = await _seed_road(database, 771121)
    await service.travel(actor, ROAD)
    combat = await service.start_hunt(actor)
    async with database[1]() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == combat.activity_id)
        )
        activity.status = "failed"
        await session.commit()
    blocked = await service.travel(actor, REFUGE)
    assert blocked.kind == "hunt_defeat"
    async with database[1]() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == blocked.character_id)
        )
        assert world.location == ROAD


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
    _, payload = equipment_instance_payload(
        materialize_equipment("blocked-equipment", "Raro", 1)
    )
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


@pytest.mark.asyncio
async def test_road_navigation_waits_for_p1_completed(database):
    actor, service = await _seed_road(database, 771110, include_p1=False)
    assert await service.resume(actor) is None
    assert await service.travel(actor, ROAD) is None
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            Quest(
                character_id=character.id,
                quest_id="P1",
                title="Vozes na Estrada",
                status="active",
                step=1,
                content_version="tdo-1.0.2",
            )
        )
        await session.commit()
    assert await service.resume(actor) is None
    async with database[1]() as session:
        quest = await session.scalar(select(Quest).where(Quest.quest_id == "P1"))
        quest.status = "completed"
        await session.commit()
    assert (await service.resume(actor)).kind == "refuge"


@pytest.mark.asyncio
async def test_travel_rejects_stale_callback_from_invalid_origin(database):
    actor, service = await _seed_road(database, 771111)
    async with database[1]() as session:
        world = await session.scalar(select(WorldState).where(WorldState.character_id.is_not(None)))
        world.location = "Local Antigo"
        await session.commit()
    assert await service.travel(actor, ROAD) is None
    async with database[1]() as session:
        world = await session.scalar(select(WorldState).where(WorldState.character_id.is_not(None)))
        assert world.location == "Local Antigo"


def test_progression_consolidates_carryover_and_caps_at_sixty():
    from types import SimpleNamespace

    character = SimpleNamespace(
        level=1,
        xp=level_xp(1) + 123,
        character_class="sentinela",
        race="remanescente",
        hp=Decimal("100"),
        max_hp=Decimal("999"),
    )
    assert consolidate_level(character) == 1
    assert (character.level, character.xp) == (2, 123)
    assert character.hp == Decimal("100")

    character.level = 58
    character.xp = sum(level_xp(level) for level in range(58, 60)) + 999
    consolidate_level(character)
    assert (character.level, character.xp) == (60, 0)


@pytest.mark.asyncio
async def test_first_observation_grants_fixed_xp_once_and_survives_reconnect(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771112)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await session.execute(
            delete(BestiaryEvidence).where(
                BestiaryEvidence.character_id == character.id,
                BestiaryEvidence.creature_id == "corvo_fuligem",
            )
        )
        await session.execute(
            delete(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == "corvo_fuligem",
            )
        )
        await session.commit()
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("combat", "explore.tdo.estrada.combat.corvo_fuligem", "Um Corvo."),
    )
    view = await service.explore(actor)
    assert view.kind == "combat"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2720 + 48
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == f"bestiary:observation:{character.id}:corvo_fuligem",
            )
        ) == 1
    resumed = await service.resume(actor)
    assert resumed.kind == "combat"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2720 + 48


@pytest.mark.asyncio
async def test_alpha_first_major_victory_xp_is_unique(database):
    actor, service = await _seed_road(database, 771113)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await service._bestiary(session, character.id, "alfa_cinereo", victory=True, elite=True)
        await service._bestiary(session, character.id, "alfa_cinereo", victory=True, elite=True)
        await session.commit()
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2720 + 198
        assert await session.scalar(
            select(func.count(RewardComponent.id)).join(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == f"bestiary:first_victory:{character.id}:alfa_cinereo",
                RewardComponent.kind == "bestiary_first_victory_xp",
            )
        ) == 1


@pytest.mark.asyncio
async def test_exploration_receipt_is_acknowledgeable_and_not_rerolled(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771114)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: (
            "great_discovery",
            "explore.tdo.estrada.marco_viajantes",
            "Marco oficial.",
        ),
    )
    first = await service.explore(actor)
    resumed = await service.resume(actor)
    assert first.result_text == resumed.result_text
    assert "✨ XP · 456" in resumed.result_text
    await service.acknowledge_result(actor)
    assert (await service.resume(actor)).kind == "road"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.xp == 2720 + 456
        attempt = await session.scalar(
            select(ExplorationAttempt).where(ExplorationAttempt.character_id == character.id)
        )
        assert attempt.result_acknowledged is True


@pytest.mark.asyncio
async def test_rastros_context_is_persisted_for_reconnect(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771115)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: (
            "knowledge",
            "explore.tdo.estrada.rastros_cinereos",
            "Texto-base dos rastros.",
        ),
    )
    first = await service.explore(actor)
    assert "Texto-base dos rastros." in first.result_text
    assert "Cão Cinéreo" in first.result_text or "Corvo de Fuligem" in first.result_text
    resumed = await service.resume(actor)
    assert resumed.result_text == first.result_text
    async with database[1]() as session:
        attempt = await session.scalar(select(ExplorationAttempt))
        assert attempt.progress.get("context_creature_id") in {"dog_cinereo", "corvo_fuligem"}


@pytest.mark.asyncio
async def test_rastros_with_existing_habitat_persists_flavor_without_bkp(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771122)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add_all([
            BestiaryEvidence(
                character_id=character.id,
                creature_id="dog_cinereo",
                evidence_id="habitat:estrada",
                category="habitat",
            ),
            BestiaryEvidence(
                character_id=character.id,
                creature_id="corvo_fuligem",
                evidence_id="habitat:estrada",
                category="habitat",
            ),
        ])
        await session.commit()
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("knowledge", "explore.tdo.estrada.rastros_cinereos", "Texto-base."),
    )
    first = await service.explore(actor)
    assert first.result_text.startswith("Texto-base.")
    assert any(
        context in first.result_text
        for context in road_module.RASTROS_CONTEXT_TEXT.values()
    )
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        entries = (
            await session.scalars(
                select(BestiaryEntry).where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id.in_(("dog_cinereo", "corvo_fuligem")),
                )
            )
        ).all()
        assert {entry.bkp for entry in entries} == {7}
        attempt = await session.scalar(select(ExplorationAttempt))
        assert attempt.progress["context_materialized"] is True
    resumed = await service.resume(actor)
    assert resumed.result_text == first.result_text


@pytest.mark.asyncio
async def test_rastros_without_identifiable_creature_keeps_only_base_text(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771123)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await session.execute(
            delete(BestiaryEvidence).where(BestiaryEvidence.character_id == character.id)
        )
        await session.execute(
            delete(BestiaryEntry).where(BestiaryEntry.character_id == character.id)
        )
        await session.commit()
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("knowledge", "explore.tdo.estrada.rastros_cinereos", "Texto-base."),
    )
    first = await service.explore(actor)
    assert first.result_text == "Texto-base."
    async with database[1]() as session:
        attempt = await session.scalar(select(ExplorationAttempt))
        assert "context_creature_id" not in attempt.progress


@pytest.mark.asyncio
async def test_exploration_retry_is_server_authoritative_after_cooldown(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771124)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("great_discovery", "explore.tdo.estrada.marco_viajantes", "Marco."),
    )
    first = await service.explore(actor)
    assert first.retry_available is False
    async with database[1]() as session:
        attempt = await session.scalar(select(ExplorationAttempt))
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
        await session.commit()
    resumed = await service.resume(actor)
    assert resumed.kind == "exploration"
    assert resumed.retry_available is True


@pytest.mark.asyncio
async def test_exploration_retry_is_hidden_at_six_per_hour(database, monkeypatch):
    import asterion.application.road as road_module

    actor, service = await _seed_road(database, 771125)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: ("great_discovery", "explore.tdo.estrada.marco_viajantes", "Marco."),
    )
    await service.explore(actor)
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        current = await session.scalar(select(ExplorationAttempt))
        current.created_at = datetime.now(UTC) - timedelta(minutes=10)
        now = datetime.now(UTC)
        for index in range(5):
            session.add(ExplorationAttempt(
                character_id=character.id,
                local_id=ROAD,
                ruleset_version="gdd-1.4.3-baseline-1.0",
                seed=f"retry-limit-{index}",
                category="narrative",
                result_id="explore.tdo.estrada.vozes_vento",
                status="completed",
                state_version=1,
                progress={"result_text": "Outro resultado.", "settled": True},
                created_at=now - timedelta(minutes=1),
                completed_at=now - timedelta(minutes=1),
                result_acknowledged=True,
            ))
        await session.commit()
    resumed = await service.resume(actor)
    assert resumed.kind == "exploration"
    assert resumed.retry_available is False


@pytest.mark.asyncio
async def test_road_activity_expires_once_without_vigor_or_economy(database):
    actor, service = await _seed_road(database, 771116)
    await service.travel(actor, ROAD)
    combat = await service.start_hunt(actor)
    async with database[1]() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == combat.activity_id)
        )
        activity.last_valid_action_at = datetime.now(UTC) - timedelta(minutes=31)
        await session.commit()
    expired = await service.resume(actor)
    assert expired.kind == "hunt_defeat"
    stale = await service.action(actor, combat.activity_id, combat.combat.version, "attack")
    assert stale.kind == "hunt_defeat"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.vigor == 100
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        ) == 0


@pytest.mark.asyncio
async def test_minimum_post_p1_journey_consolidates_before_next_hunt(database, monkeypatch):
    import asterion.application.road as road_module
    from asterion.domain.road import road_pool

    actor, service = await _seed_road(database, 771117, xp=level_xp(1) - 456)
    await service.travel(actor, ROAD)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: (
            "great_discovery",
            "explore.tdo.estrada.marco_viajantes",
            "Marco oficial.",
        ),
    )
    result = await service.explore(actor)
    assert result.kind == "exploration"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert (character.level, character.xp) == (2, 0)
    await service.acknowledge_result(actor)
    hunt = await service.start_hunt(actor)
    assert hunt.kind == "combat"
    assert hunt.combat.fighters["player"].level == 2
    assert "peregrino_calcinado" in {creature.creature_id for creature in road_pool(2)}
