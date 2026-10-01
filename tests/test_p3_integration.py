from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.active_arts import ActiveArtService
from asterion.application.p3 import (
    P3_COMBAT_CONTENT_ID,
    P3_ID,
    P3_REWARD_SOURCE,
    P3Service,
)
from asterion.application.road import BOSQUE, CHARNECA, REFUGE
from asterion.domain.arts import FIRST_CLASS_ART_IDS
from asterion.domain.combat_math import resolve_combat_stats
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    GameActivity,
    HuntContext,
    LocationDiscovery,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)


async def _seed_p3(database, actor: int, *, level: int = 5, p2_status: str = "completed"):
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
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=61,
                max_vigor=100,
                crowns=11,
            )
        )
        session.add_all(
            (
                Quest(
                    character_id=character_id,
                    quest_id="P1",
                    title="Vozes na Estrada",
                    status="completed",
                    step=7,
                    content_version="tdo-1.0.2",
                ),
                Quest(
                    character_id=character_id,
                    quest_id="P2",
                    title="Fuligem sem Fogo",
                    status=p2_status,
                    step=6 if p2_status == "completed" else 1,
                    content_version="tdo-1.0.7",
                ),
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location=REFUGE,
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="route.tdo.refugio_charneca",
                ),
            )
        )
    return character_id, P3Service(sessions, "ocaso")


async def _start_scripted_combat(service: P3Service, actor: int):
    view = await service.accept(actor)
    assert view is not None and view.status == "active" and view.step == 1
    view = await service.mission_route(actor, view.state_version, CHARNECA)
    assert view is not None and view.location == CHARNECA
    view = await service.enter_bosque(actor, view.state_version)
    assert view is not None and view.step == 2 and view.location == BOSQUE
    for fragment_id in ("p3.fragment.3", "p3.fragment.1", "p3.fragment.2"):
        view = await service.examine_fragment(actor, fragment_id, view.state_version)
    assert view is not None and view.kind == "combat" and view.combat is not None
    return view


@pytest.mark.asyncio
async def test_p3_scripted_combat_freezes_equipped_class_art(database):
    _, service = await _seed_p3(database, 998304)
    art_id = FIRST_CLASS_ART_IDS["sentinela"]
    equipped = await ActiveArtService(database[1], "ocaso").equip_art(998304, 1, art_id)
    assert equipped is not None and equipped.combat_configuration_version == 1

    combat = await _start_scripted_combat(service, 998304)
    assert art_id in combat.combat.player_actions
    assert combat.combat.configuration_snapshot["active_arts"] == [
        {"slot": 1, "art_id": art_id}
    ]


def _terminal(result: str):
    def finish(combat, action):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        if result == "defeat":
            updated.fighters["player"].hp = Decimal(0)
        return updated

    return finish


@pytest.mark.asyncio
async def test_p3_offer_requires_p2_and_level_five_without_s2(database):
    low_id, low = await _seed_p3(database, 998301, level=4)
    active_id, active = await _seed_p3(database, 998302, p2_status="active")
    eligible_id, eligible = await _seed_p3(database, 998303)

    assert not (await low.oren(998301)).available
    assert not (await active.oren(998302)).available
    offer = await eligible.oren(998303)
    assert offer is not None and offer.available and offer.status == "unaccepted"
    assert (await eligible.offer(998303)).kind == "offer"
    async with database[1]() as session:
        for character_id in (low_id, active_id, eligible_id):
            assert (
                await session.scalar(
                    select(Quest).where(
                        Quest.character_id == character_id,
                        Quest.quest_id == P3_ID,
                    )
                )
                is None
            )
    accepted = await eligible.accept(998303, offer.state_version)
    assert accepted is not None and accepted.status == "active" and accepted.step == 1
    duplicate = await eligible.accept(998303, offer.state_version)
    assert duplicate is not None and duplicate.state_version == accepted.state_version


@pytest.mark.asyncio
async def test_p3_bosque_entry_fragments_and_scripted_cervo_are_persistent(database):
    character_id, service = await _seed_p3(database, 998304)
    accepted = await service.accept(998304)
    assert accepted is not None
    moved = await service.mission_route(998304, accepted.state_version, CHARNECA)
    entered = await service.enter_bosque(998304, moved.state_version)
    assert entered is not None and entered.location == BOSQUE and entered.step == 2
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(LocationDiscovery).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == "tdo.location.bosque_calcinado",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(Unlock).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == "route.tdo.charneca_bosque",
                )
            )
            is not None
        )
    first = await service.examine_fragment(998304, "p3.fragment.3", entered.state_version)
    duplicate = await service.examine_fragment(998304, "p3.fragment.3", entered.state_version)
    assert duplicate.progress["fragments"] == ["p3.fragment.3"]
    assert duplicate.state_version == first.state_version
    second = await service.examine_fragment(998304, "p3.fragment.1", first.state_version)
    combat = await service.examine_fragment(998304, "p3.fragment.2", second.state_version)
    assert combat is not None and combat.kind == "combat"
    assert combat.activity_id and combat.encounter_id and combat.combat_id
    assert combat.combat.fighters["enemy"].name == "Cervo Escoriado"
    assert combat.combat.fighters["enemy"].level == 5
    assert combat.combat.variant is None
    assert combat.consumable_budget_limit == 1
    assert combat.combat.enemy_actions["ocaso_charge"].prepared is True
    assert combat.combat.ai_cycle[0] == "ocaso_charge"
    resumed = await service.resume(998304)
    assert resumed is not None
    assert (resumed.activity_id, resumed.encounter_id, resumed.combat_id) == (
        combat.activity_id,
        combat.encounter_id,
        combat.combat_id,
    )
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(HuntContext).where(HuntContext.game_activity_id == combat.activity_id)
            )
            is None
        )
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.id == combat.activity_id)
        )
        assert activity.content_id == P3_COMBAT_CONTENT_ID


@pytest.mark.asyncio
async def test_p3_defeat_uses_bosque_recovery_and_explicit_new_attempt(database, monkeypatch):
    import asterion.application.p3 as p3_module

    character_id, service = await _seed_p3(database, 998305)
    combat = await _start_scripted_combat(service, 998305)
    monkeypatch.setattr(p3_module, "act", _terminal("defeat"))
    defeated = await service.action(
        998305,
        combat.activity_id,
        combat.activity_state_version,
        "attack",
    )
    assert defeated is not None and defeated.kind == "recovery"
    assert defeated.location == REFUGE and defeated.progress["awaiting_retry"]
    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.hp == character.max_hp
        assert character.vigor == 61
        assert (
            await session.scalar(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P3_REWARD_SOURCE,
                )
            )
            is None
        )
    to_charneca = await service.mission_route(998305, defeated.state_version, CHARNECA)
    to_bosque = await service.enter_bosque(998305, to_charneca.state_version)
    retry = await service.retry(998305, to_bosque.state_version)
    assert retry is not None and retry.kind == "combat"
    assert retry.activity_id != combat.activity_id
    assert retry.encounter_id != combat.encounter_id
    assert retry.combat.fighters["enemy"].name == "Cervo Escoriado"
    assert retry.combat.fighters["enemy"].level == 5


@pytest.mark.asyncio
async def test_p3_victory_returns_to_oren_and_grants_one_selected_item(database, monkeypatch):
    import asterion.application.p3 as p3_module

    character_id, service = await _seed_p3(database, 998306)
    combat = await _start_scripted_combat(service, 998306)
    monkeypatch.setattr(p3_module, "act", _terminal("victory"))
    victory = await service.action(
        998306,
        combat.activity_id,
        combat.activity_state_version,
        "attack",
    )
    carved = await service.examine_carved_fragment(998306, victory.state_version)
    to_charneca = await service.mission_route(998306, carved.state_version, CHARNECA)
    to_refuge = await service.mission_route(998306, to_charneca.state_version, REFUGE)
    choice = await service.talk_to_oren(998306, to_refuge.state_version)
    completed = await service.choose_reward(998306, choice.state_version, "veil")
    assert completed is not None and completed.status == "completed"
    assert completed.progress["selected_reward"] == "veil"
    repeated = await service.choose_reward(998306, choice.state_version, "seal")
    assert repeated.progress["selected_reward"] == "veil"
    async with database[1]() as session:
        events = (
            await session.scalars(
                select(RewardEvent).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P3_REWARD_SOURCE,
                )
            )
        ).all()
        assert len(events) == 1
        components = (
            await session.scalars(
                select(RewardComponent).where(RewardComponent.reward_event_id == events[0].id)
            )
        ).all()
        assert {(row.kind, row.quantity) for row in components} == {
            ("xp", 4400),
            ("crowns", 180),
            ("equipment", 1),
        }
        enemy_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"{P3_REWARD_SOURCE}:enemy-xp:{combat.activity_id}",
            )
        )
        assert enemy_event is not None
        assert await session.scalar(
            select(func.count(HuntContext.game_activity_id)).where(
                HuntContext.game_activity_id == combat.activity_id
            )
        ) == 0
        items = (
            await session.scalars(
                select(EquipmentItem).where(EquipmentItem.character_id == character_id)
            )
        ).all()
        assert len(items) == 1
        item = items[0]
        assert (item.item_name, item.slot, item.rarity, item.item_level, item.bound) == (
            "Véu do Bosque",
            "Cabeça",
            "Raro",
            5,
            True,
        )
        assert item.payload["enhancement"] == 0
        assert item.payload["rune"] is None and item.payload["enchantment"] is None
        assert (
            await session.scalar(
                select(CodexEntry).where(
                    CodexEntry.character_id == character_id,
                    CodexEntry.entry_id == "codex.history.antigos_asterianos",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(CodexFragment).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.entry_id == "codex.mystery.marcas_na_fuligem",
                )
            )
            is not None
        )
        for unlock_id in (
            "hunt_manual.bosque_calcinado",
            "explore.bosque_calcinado",
            "route.tdo.charneca_bosque",
        ):
            assert (
                await session.scalar(
                    select(Unlock).where(
                        Unlock.character_id == character_id,
                        Unlock.unlock_id == unlock_id,
                    )
                )
                is not None
            )


@pytest.mark.asyncio
async def test_p3_defeat_after_vento_morto_recovers_to_charneca_and_retries(database, monkeypatch):
    import asterion.application.p3 as p3_module

    character_id, service = await _seed_p3(database, 998307)
    async with database[1].begin() as session:
        session.add(
            Brazier(character_id=character_id, brazier_id="tdo.brazier.vento_morto")
        )
    combat = await _start_scripted_combat(service, 998307)
    monkeypatch.setattr(p3_module, "act", _terminal("defeat"))
    defeated = await service.action(
        998307, combat.activity_id, combat.activity_state_version, "attack"
    )
    assert defeated.kind == "recovery"
    assert defeated.location == CHARNECA
    assert defeated.progress["recovery_brazier"] == "Braseiro do Vento Morto"
    assert defeated.progress["awaiting_retry"] is True
    async with database[1]() as session:
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        character = await session.get(Character, character_id)
        assert world.location == CHARNECA
        assert character.vigor == 61
    to_bosque = await service.mission_route(
        998307, defeated.state_version, BOSQUE
    )
    retry = await service.retry(998307, to_bosque.state_version)
    assert retry.kind == "combat"
    assert retry.activity_id != combat.activity_id
    assert retry.encounter_id != combat.encounter_id
    assert retry.combat.ai_cycle[0] == "ocaso_charge"
