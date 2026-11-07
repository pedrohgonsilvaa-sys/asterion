from collections import deque
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

import asterion.application.road as road_application
import asterion.application.round as round_application
from asterion.application.road import (
    CHARNECA,
    EXPLORE_CONTENT,
    HUNT_CONTENT,
    REFUGE,
    ROAD,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.domain.road import (
    CHARNECA_EXPLORATION_PROFILE,
    CHARNECA_LOCATION,
    CHARNECA_PROFILE,
    CREATURE_CATALOG,
    EXPLORATION_CATEGORY_WEIGHTS,
    MATERIAL_POOLS,
    ROAD_PROFILE,
    SPIDER,
    ExplorationLocationProfile,
    ExplorationResultDefinition,
    create_road_combat,
    creature_for,
    crowns,
    enemy_xp,
    equipment_rarity,
    hunt_pool,
    material_for,
    select_creature,
    select_exploration_result,
)
from asterion.infrastructure.db.models import (
    Account,
    Brazier,
    Character,
    CodexEntry,
    ConsumableStack,
    EquipmentItem,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    RuneStack,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import (
    disable_round_pvpve_for_test,
    start_manual_hunt_after_no_match,
)


async def _seed_charneca(
    database,
    *,
    actor: int,
    name: str = "Heroa",
    level: int = 4,
    vigor: int = 100,
    location: str = REFUGE,
    round_familiarity: bool = False,
    road_familiarity: bool = False,
    permanent_braziers: tuple[str, ...] = (),
) -> RoadService:
    _, sessions = database
    character_id = uuid4()
    async with sessions() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=name,
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
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
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.7",
                    progress={"completed": True},
                ),
                WorldState(
                    character_id=character_id,
                    region="Terras do Ocaso",
                    location=location,
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="route.tdo.refugio_charneca",
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="hunt_manual.charneca_da_fuligem",
                ),
                Unlock(
                    character_id=character_id,
                    unlock_id="explore.charneca_da_fuligem",
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.estrada_das_cinzas",
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id="tdo.location.refugio_do_ocaso",
                ),
                LocationDiscovery(
                    character_id=character_id,
                    location_id=CHARNECA_LOCATION,
                ),
            ]
        )
        session.add_all(
            Brazier(character_id=character_id, brazier_id=brazier_id)
            for brazier_id in permanent_braziers
        )
        if round_familiarity:
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id="hunt_round.charneca_da_fuligem",
                )
            )
        if road_familiarity:
            session.add(
                Unlock(
                    character_id=character_id,
                    unlock_id="hunt_round.estrada_das_cinzas",
                )
            )
        await session.commit()
    return RoadService(sessions, "ocaso")


def test_charneca_hunt_profile_and_level_gates_are_local():
    assert CHARNECA_PROFILE.local_id == CHARNECA_LOCATION
    assert CHARNECA_PROFILE.creature_weights == (
        ("peregrino_calcinado", 31),
        ("dog_cinereo", 31),
        ("aranha_cinza", 18),
        ("cervo_escoriado", 20),
    )
    assert CHARNECA_PROFILE.variant_chance == 10
    assert {creature.creature_id for creature in hunt_pool(3, CHARNECA_PROFILE)} == {
        "peregrino_calcinado",
        "dog_cinereo",
        "aranha_cinza",
    }
    assert {creature.creature_id for creature in hunt_pool(4, CHARNECA_PROFILE)} == {
        "peregrino_calcinado",
        "dog_cinereo",
        "aranha_cinza",
        "cervo_escoriado",
    }
    for level in range(3, 7):
        assert all(
            select_creature(str(seed), level, ROAD_PROFILE).creature_id
            != "aranha_cinza"
            for seed in range(64)
        )
        assert all(
            select_creature(str(seed), level, ROAD_PROFILE).creature_id
            != "cervo_escoriado"
            for seed in range(64)
        )
    assert "alfa_cinereo" not in {
        creature.creature_id for creature in hunt_pool(7, CHARNECA_PROFILE)
    }


def test_charneca_explore_profile_gates_and_shared_category_weights():
    assert dict(CHARNECA_EXPLORATION_PROFILE.category_weights) == EXPLORATION_CATEGORY_WEIGHTS
    assert {
        (result.key, result.weight)
        for result in CHARNECA_EXPLORATION_PROFILE.results
        if result.category == "great_discovery"
    } == {("braseiro", 50), ("cripta", 50)}
    assert {
        (result.key, result.weight)
        for result in CHARNECA_EXPLORATION_PROFILE.results
        if result.category == "combat"
    } == {
        ("peregrino_calcinado", 35),
        ("aranha_cinza", 35),
        ("cervo_escoriado", 30),
    }
    forbidden_at_3 = {
        "explore.tdo.charneca.braseiro",
        "explore.tdo.charneca.cripta",
        "explore.tdo.charneca.combat.cervo_escoriado",
    }
    results_at_3 = {
        select_exploration_result(str(seed), 3, profile=CHARNECA_EXPLORATION_PROFILE)
        for seed in range(3000)
    }
    assert not forbidden_at_3.intersection(
        CHARNECA_EXPLORATION_PROFILE.result(key).result_id for key in results_at_3
    )
    results_at_4 = {
        select_exploration_result(str(seed), 4, profile=CHARNECA_EXPLORATION_PROFILE)
        for seed in range(3000)
    }
    assert {"braseiro", "cripta", "cervo_escoriado"}.issubset(results_at_4)


def test_cervo_catalog_material_and_prepared_action_are_canonical():
    deer = creature_for("cervo_escoriado")
    assert deer in CREATURE_CATALOG
    assert (deer.category, deer.archetype, deer.unlock_level, deer.max_level) == (
        "common",
        "brute",
        4,
        7,
    )
    assert deer.ai == ("antler_gore", "ocaso_charge")
    assert deer.actions[0][2] == Decimal("1.05")
    assert deer.actions[1][2] == Decimal("1.60")
    assert deer.actions[1][8] is True
    assert material_for("cervo_escoriado", "any-seed") == "material.tdo.couro_escoriado"
    combat = create_road_combat(
        uuid4(), "Heroa", "sentinela", "remanescente", Decimal("702"), deer, 4, None
    )
    assert combat.enemy_actions["ocaso_charge"].prepared is True
    assert set(combat.ai_cycle) == {"antler_gore", "ocaso_charge"}


@pytest.mark.parametrize(
    ("draw", "expected"),
    [
        (0, "Comum"),
        (6499, "Comum"),
        (6500, "Raro"),
        (9399, "Raro"),
        (9400, "Épico"),
        (9949, "Épico"),
        (9950, "Lendário"),
        (9999, "Lendário"),
    ],
)
def test_uncommon_equipment_rarity_boundaries(draw, expected, monkeypatch):
    monkeypatch.setattr("asterion.domain.road._stable_draw", lambda seed, purpose, modulo: draw)
    assert equipment_rarity("fixed", "uncommon") == expected


def test_uncommon_global_xp_and_crowns_factors():
    assert enemy_xp(3, "uncommon", player_level=3) == 370
    assert crowns(3, "uncommon") == 10


def test_tdo_material_pools_match_v1016_regional_authority():
    assert MATERIAL_POOLS["corvo_fuligem"] == (
        ("material.tdo.residuo_ocaso", 100),
    )
    assert MATERIAL_POOLS["alfa_cinereo"] == (
        ("material.tdo.couro_escoriado", 100),
    )

    peregrino_pool = dict(MATERIAL_POOLS["peregrino_calcinado"])
    total_weight = sum(peregrino_pool.values())
    normalized_percentages = {
        material_id: weight * 100 // total_weight
        for material_id, weight in peregrino_pool.items()
    }
    assert normalized_percentages == {
        "material.tdo.ferro_de_fuligem": 50,
        "material.tdo.erva_cinzenta": 50,
    }

    assert material_for("corvo_fuligem", "regional-pool") == "material.tdo.residuo_ocaso"
    assert material_for("alfa_cinereo", "regional-pool") == (
        "material.tdo.couro_escoriado"
    )


def test_spider_material_ordinal_rolls_allow_independent_same_results():
    outcomes = {
        material_for("aranha_cinza", f"hunt-seed:material:{ordinal}")
        for ordinal in range(256)
    }
    assert outcomes == {
        "material.tdo.erva_cinzenta",
        "material.tdo.residuo_ocaso",
    }
    assert any(
        material_for("aranha_cinza", f"hunt-seed:material:{left}")
        == material_for("aranha_cinza", f"hunt-seed:material:{right}")
        for left in range(64)
        for right in range(left + 1, 64)
    )


@pytest.mark.parametrize(
    ("purpose", "draw", "expected"),
    [
        ("equipment", 6499, "Comum"),
        ("equipment", 6500, "Raro"),
        ("equipment", 9400, "Épico"),
        ("equipment", 9950, "Lendário"),
        ("rune", 8999, "Rara"),
        ("rune", 9000, "Épica"),
        ("rune", 9950, "Lendária"),
    ],
)
def test_uncommon_optional_loot_rarity_boundaries(purpose, draw, expected, monkeypatch):
    monkeypatch.setattr(road_application, "_draw_int", lambda seed, key, modulo: draw)
    assert road_application._rarity("fixed", "uncommon", purpose) == expected


@pytest.mark.asyncio
async def test_charneca_overland_route_and_hunt_freeze_local(database, monkeypatch):
    actor = 880301
    service = await _seed_charneca(database, actor=actor, level=3)
    moved = await service.travel(actor, CHARNECA)
    assert moved.kind == "charneca"
    assert moved.location == CHARNECA
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert world.location == CHARNECA
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id
            )
        ) == 0
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "tdo.brazier.vento_morto",
            )
        ) == 0

    monkeypatch.setattr(road_application, "select_creature", lambda seed, level, profile: SPIDER)
    monkeypatch.setattr(road_application, "select_variant", lambda seed, creature, profile: None)
    combat = await start_manual_hunt_after_no_match(service, actor, monkeypatch)
    assert combat.kind == "combat"
    assert combat.location == CHARNECA
    assert combat.combat.fighters["enemy"].name == "Aranha de Cinza"
    assert combat.combat.variant is None
    blocked_route = await service.travel(actor, REFUGE)
    assert blocked_route.kind == "combat"
    assert blocked_route.activity_id == combat.activity_id
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == combat.activity_id)
        )
        assert (context.local_id, context.category, context.enemy_level) == (
            CHARNECA_LOCATION,
            "uncommon",
            3,
        )
        assert await session.scalar(
            select(func.count(HuntContext.id)).where(
                HuntContext.character_id == combat.character_id,
                HuntContext.local_id == "tdo.location.estrada_das_cinzas",
            )
        ) == 0


@pytest.mark.asyncio
async def test_overland_and_brazier_travel_are_distinct_and_free(database):
    actor = 880311
    service = await _seed_charneca(
        database,
        actor=actor,
        location=REFUGE,
        permanent_braziers=(
            "tdo.brazier.estrada",
            "tdo.brazier.refugio_do_ocaso",
            "tdo.brazier.vento_morto",
        ),
    )

    charneca = await service.travel_route(actor, CHARNECA)
    assert charneca is not None and charneca.location == CHARNECA
    assert charneca.brazier_id == "tdo.brazier.vento_morto"
    assert {destination[1] for destination in charneca.brazier_destinations} == {
        "Braseiro da Estrada",
        "Braseiro do Refúgio",
    }

    refuge = await service.travel_brazier(actor, "tdo.brazier.refugio_do_ocaso")
    assert refuge is not None and refuge.location == REFUGE
    assert refuge.brazier_id == "tdo.brazier.refugio_do_ocaso"
    assert {
        destination[0] for destination in refuge.brazier_destinations
    } == {"tdo.brazier.estrada", "tdo.brazier.vento_morto"}

    back_by_route = await service.travel_route(actor, CHARNECA)
    assert back_by_route is not None and back_by_route.location == CHARNECA
    refuge_again = await service.travel_route(actor, REFUGE)
    assert refuge_again is not None and refuge_again.location == REFUGE
    assert await service.travel_route(actor, ROAD) is None
    assert await service.travel_brazier(actor, "tdo.brazier.not_discovered") is None

    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id
            )
        ) == 0
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character.id
            )
        ) == 0
        p2 = await session.scalar(
            select(Quest).where(
                Quest.character_id == character.id,
                Quest.quest_id == "P2",
            )
        )
        p2.status = "active"
        await session.commit()
    assert await service.travel_route(actor, CHARNECA) is None


def _forced_defeat(combat, _action, **_kwargs):
    updated = deepcopy(combat)
    updated.version += 1
    updated.result = "defeat"
    updated.fighters["player"].hp = Decimal(0)
    return updated


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("has_vento", "expected_location", "expected_brazier"),
    (
        (False, REFUGE, "Braseiro do Refúgio"),
        (True, CHARNECA, "Braseiro do Vento Morto"),
    ),
)
async def test_charneca_hunt_defeat_recovers_at_discovered_brazier_and_persists(
    database, monkeypatch, has_vento, expected_location, expected_brazier
):
    actor = 880312 if has_vento else 880313
    service = await _seed_charneca(
        database,
        actor=actor,
        location=CHARNECA,
        permanent_braziers=(
            ("tdo.brazier.vento_morto",) if has_vento else ()
        ),
    )
    monkeypatch.setattr(
        road_application, "select_creature", lambda _seed, _level, profile: SPIDER
    )
    monkeypatch.setattr(
        road_application, "select_variant", lambda _seed, _creature, profile: None
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.hp = Decimal("500")
        session.add_all(
            [
                ConsumableStack(
                    character_id=character.id,
                    consumable_id="consumable.heal",
                    quantity=2,
                )
            ]
        )
        await session.commit()

    encounter = await start_manual_hunt_after_no_match(service, actor, monkeypatch)
    assert encounter is not None and encounter.kind == "combat"

    heal = await service.action(
        actor,
        encounter.activity_id,
        encounter.combat.version,
        consumable_id="consumable.heal",
    )
    assert heal is not None and heal.kind == "combat"
    assert dict(heal.consumable_quantities)["consumable.heal"] == 1
    monkeypatch.setattr(road_application, "act", _forced_defeat)
    defeat = await service.action(
        actor,
        encounter.activity_id,
        heal.combat.version,
        "attack",
    )
    assert defeat is not None and defeat.kind == "hunt_defeat"
    assert defeat.location == CHARNECA
    assert defeat.recovery_location == expected_location
    assert defeat.recovery_brazier == expected_brazier
    assert defeat.route_available is (expected_location == REFUGE)

    reconnected = await service.resume(actor)
    assert reconnected is not None and reconnected.kind == "hunt_defeat"
    assert reconnected.activity_id == encounter.activity_id
    assert reconnected.recovery_location == expected_location
    assert reconnected.recovery_brazier == expected_brazier
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        activity = await session.get(GameActivity, encounter.activity_id)
        stack = await session.scalar(
            select(ConsumableStack).where(
                ConsumableStack.character_id == character.id,
                ConsumableStack.consumable_id == "consumable.heal",
            )
        )
        assert world.location == expected_location
        assert character.hp == character.max_hp
        assert character.vigor == 100
        assert stack.quantity == 1
        assert activity.status == "failed"
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == f"hunt:{encounter.activity_id}",
            )
        ) == 0


@pytest.mark.asyncio
async def test_charneca_exploration_defeat_keeps_failed_attempt_and_recovery(database, monkeypatch):
    actor = 880314
    service = await _seed_charneca(database, actor=actor, location=CHARNECA)
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *_args, **_kwargs: (
            "combat",
            "explore.tdo.charneca.combat.aranha_cinza",
            "Aranha de Cinza.",
        ),
    )
    monkeypatch.setattr(
        road_application, "select_variant", lambda _seed, _creature, profile: None
    )
    encounter = await service.explore(actor)
    assert encounter is not None and encounter.kind == "combat"
    assert encounter.location == CHARNECA
    monkeypatch.setattr(road_application, "act", _forced_defeat)
    defeat = await service.action(
        actor,
        encounter.activity_id,
        encounter.combat.version,
        "attack",
    )
    assert defeat is not None and defeat.kind == "exploration"
    assert defeat.result_id == "explore.tdo.charneca.combat.aranha_cinza"
    assert defeat.recovery_brazier == "Braseiro do Refúgio"
    assert defeat.recovery_location == REFUGE
    reconnected = await service.resume(actor)
    assert reconnected is not None and reconnected.attempt_id == defeat.attempt_id
    assert reconnected.recovery_location == REFUGE
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        attempt = await session.get(ExplorationAttempt, defeat.attempt_id)
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert attempt.status == "failed"
        assert attempt.progress["settled"] is True
        assert attempt.progress["recovery_brazier"] == "Braseiro do Refúgio"
        assert world.location == REFUGE
        assert character.hp == character.max_hp


@pytest.mark.asyncio
async def test_charneca_round_defeat_recovers_without_restarting_and_preparing_resumes(
    database, monkeypatch
):
    actor = 880315
    await _seed_charneca(
        database,
        actor=actor,
        location=CHARNECA,
        round_familiarity=True,
    )
    rounds = disable_round_pvpve_for_test(RoundService(database[1], "ocaso"))
    monkeypatch.setattr(
        round_application,
        "select_creature",
        lambda _seed, _level, **_kwargs: SPIDER,
    )
    monkeypatch.setattr(
        round_application,
        "select_variant",
        lambda _seed, _creature, **_kwargs: None,
    )

    preparing = await rounds.prepare_round(actor, 5)
    assert preparing.kind == "round_prepare"
    resumed_preparing = await RoundService(database[1], "ocaso").resume(actor)
    assert resumed_preparing.kind == "round_prepare"
    assert resumed_preparing.round_id == preparing.round_id
    assert resumed_preparing.state_version == preparing.state_version
    async with database[1]() as session:
        assert await session.scalar(select(func.count(HuntRound.id))) == 1
        state = await session.get(HuntRound, preparing.round_id)
        assert state.config_snapshot["local_id"] == CHARNECA_LOCATION

    started = await rounds.start_round(actor, preparing.round_id, preparing.state_version)
    assert started.kind == "round_active"
    monkeypatch.setattr(round_application, "act", _forced_defeat)
    async with database[1]() as session:
        state = await session.get(HuntRound, started.round_id)
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    assert await rounds.advance_due_rounds() == 1

    defeated = await RoundService(database[1], "ocaso").resume(actor)
    assert defeated.kind == "round_defeated"
    assert defeated.round_id == started.round_id
    assert defeated.recovery_brazier == "Braseiro do Refúgio"
    assert defeated.recovery_location == REFUGE
    assert defeated.route_available is True
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        state = await session.get(HuntRound, started.round_id)
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter).where(
                    HuntRoundEncounter.round_id == state.id
                )
            )
        ).all()
        assert state.status == "defeated"
        assert state.config_snapshot["recovery_location"] == REFUGE
        assert world.location == REFUGE
        assert character.hp == character.max_hp
        assert len(encounters) == 1
        assert encounters[0].status == "defeated"


@pytest.mark.asyncio
async def test_charneca_round_defeat_after_vento_keeps_prior_rewards_and_location(
    database, monkeypatch
):
    actor = 880316
    await _seed_charneca(
        database,
        actor=actor,
        location=CHARNECA,
        round_familiarity=True,
        permanent_braziers=("tdo.brazier.vento_morto",),
    )
    rounds = disable_round_pvpve_for_test(RoundService(database[1], "ocaso"))
    monkeypatch.setattr(
        round_application,
        "select_creature",
        lambda _seed, _level, **_kwargs: SPIDER,
    )
    monkeypatch.setattr(
        round_application,
        "select_variant",
        lambda _seed, _creature, **_kwargs: None,
    )
    outcomes = iter(("victory", "defeat"))

    def resolve_outcome(combat, _action):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = next(outcomes)
        if updated.result == "victory":
            updated.fighters["enemy"].hp = Decimal(0)
        else:
            updated.fighters["player"].hp = Decimal(0)
        return updated

    monkeypatch.setattr(round_application, "act", resolve_outcome)
    prepared = await rounds.prepare_round(actor, 5)
    started = await rounds.start_round(actor, prepared.round_id, prepared.state_version)
    async with database[1]() as session:
        state = await session.get(HuntRound, started.round_id)
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    assert await rounds.advance_due_rounds() == 1
    after_victory = await rounds.resume(actor)
    assert after_victory.kind == "round_active"
    assert after_victory.completed_encounters == 1
    async with database[1]() as session:
        first_encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == started.round_id,
                HuntRoundEncounter.ordinal == 1,
            )
        )
        assert first_encounter.status == "completed"
        first_activity_id = first_encounter.activity_id
        assert first_activity_id is not None
        first_reward_count = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.source_id == f"activity:{first_activity_id}"
            )
        )
        assert first_reward_count == 1
        state = await session.get(HuntRound, started.round_id)
        state.next_resolution_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()

    assert await rounds.advance_due_rounds() == 1
    defeated = await RoundService(database[1], "ocaso").resume(actor)
    assert defeated.kind == "round_defeated"
    assert defeated.round_id == started.round_id
    assert defeated.recovery_brazier == "Braseiro do Vento Morto"
    assert defeated.recovery_location == CHARNECA
    assert defeated.route_available is False

    reconnected = await RoundService(database[1], "ocaso").resume(actor)
    assert reconnected.kind == "round_defeated"
    assert reconnected.round_id == started.round_id
    assert reconnected.recovery_brazier == "Braseiro do Vento Morto"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        state = await session.get(HuntRound, started.round_id)
        encounters = (
            await session.scalars(
                select(HuntRoundEncounter)
                .where(HuntRoundEncounter.round_id == state.id)
                .order_by(HuntRoundEncounter.ordinal)
            )
        ).all()
        assert state.status == "defeated"
        assert world.location == CHARNECA
        assert character.hp == character.max_hp
        assert len(encounters) == 2
        assert encounters[0].status == "completed"
        assert encounters[1].status == "defeated"
        assert await session.scalar(
            select(func.count(HuntRound.id)).where(
                HuntRound.character_id == character.id
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.source_id == f"activity:{first_activity_id}"
            )
        ) == first_reward_count
        reward_count_before_ack = await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id
            )
        )

    back = await rounds.round_back(actor, started.round_id)
    assert back.kind == "charneca"
    repeated_back = await rounds.round_back(actor, started.round_id)
    assert repeated_back.kind == "charneca"
    after_ack = await RoundService(database[1], "ocaso").resume(actor)
    assert after_ack.kind == "charneca"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        assert world.location == CHARNECA
        assert character.hp == character.max_hp
        assert await session.scalar(
            select(func.count(HuntRound.id)).where(
                HuntRound.character_id == character.id
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.source_id == f"activity:{first_activity_id}"
            )
        ) == first_reward_count
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character.id
            )
        ) == reward_count_before_ack


@pytest.mark.asyncio
async def test_charneca_round_requires_local_manual_familiarity_and_freezes_local(
    database, monkeypatch
):
    actor = 880302
    await _seed_charneca(
        database,
        actor=actor,
        level=4,
        location=CHARNECA,
        road_familiarity=True,
    )
    rounds = disable_round_pvpve_for_test(RoundService(database[1], "ocaso"))
    blocked = await rounds.prepare_round(actor, 5)
    assert blocked.kind == "charneca"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(func.count(HuntRound.id)).where(
                HuntRound.character_id == character.id
            )
        ) == 0
        session.add(
            Unlock(
                character_id=character.id,
                unlock_id="hunt_round.charneca_da_fuligem",
            )
        )
        await session.commit()
    monkeypatch.setattr(round_application, "select_creature", lambda seed, level, profile: SPIDER)
    monkeypatch.setattr(round_application, "select_variant", lambda seed, creature, profile: None)
    prepared = await rounds.prepare_round(actor, 5)
    assert prepared.kind == "round_prepare"
    assert prepared.location == CHARNECA
    started = await rounds.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.location == CHARNECA
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        state = await session.scalar(
            select(HuntRound).where(HuntRound.id == started.round_id)
        )
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.round_id == state.id)
        )
        assert state.config_snapshot["local_id"] == CHARNECA_LOCATION
        assert encounter is not None
        assert encounter.creature_id == "aranha_cinza"
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "hunt_round.charneca_da_fuligem",
            )
        ) == 1


@pytest.mark.asyncio
async def test_charneca_resource_economy_and_inventory_delivery(database, monkeypatch):
    actor = 880303
    service = await _seed_charneca(
        database, actor=actor, level=4, vigor=4, location=CHARNECA
    )
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args: (
            "resource",
            "explore.tdo.charneca.erva",
            "Erva Cinzenta pode ser recolhida na Charneca.",
        ),
    )
    result = await service.explore(actor)
    assert result.kind == "exploration"
    assert result.location == CHARNECA
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character.vigor == 0
        assert character.crowns == 20
        assert await session.scalar(
            select(func.sum(MaterialStack.quantity)).where(
                MaterialStack.character_id == character.id,
                MaterialStack.material_id == "material.tdo.erva_cinzenta",
            )
        ) == 1


@pytest.mark.asyncio
async def test_charneca_resource_without_vigor_has_no_partial_economy(database, monkeypatch):
    actor = 880306
    service = await _seed_charneca(
        database, actor=actor, level=4, vigor=3, location=CHARNECA
    )
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args: (
            "resource",
            "explore.tdo.charneca.residuo",
            "Resíduo do Ocaso pode ser recolhido na Charneca.",
        ),
    )
    result = await service.explore(actor)
    assert result.result_id == "explore.tdo.charneca.residuo"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert (character.vigor, character.crowns) == (3, 0)
        assert await session.scalar(
            select(func.count(MaterialStack.id)).where(
                MaterialStack.character_id == character.id
            )
        ) == 0


@pytest.mark.asyncio
async def test_charneca_unique_discovery_rewards_and_reveals_are_idempotent(database):
    actor = 880307
    service = await _seed_charneca(
        database, actor=actor, level=4, location=CHARNECA
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )

        async def settle(result_id, category, seed):
            attempt = ExplorationAttempt(
                character_id=character.id,
                local_id=CHARNECA_LOCATION,
                ruleset_version="gdd-1.4.7-baseline-1.0",
                seed=seed,
                category=category,
                result_id=result_id,
                status="completed",
                state_version=1,
                progress={"result_text": seed},
            )
            session.add(attempt)
            await session.flush()
            await service._settle_charneca_exploration(
                session, character, attempt, seed
            )
            return attempt

        brazier_attempt = await settle(
            "explore.tdo.charneca.braseiro", "great_discovery", "brazier"
        )
        crypt_attempt = await settle(
            "explore.tdo.charneca.cripta", "great_discovery", "crypt"
        )
        wind_attempt = await settle(
            "explore.tdo.charneca.vento_morto", "narrative", "wind"
        )
        atmosphere_attempt = await settle(
            "explore.tdo.charneca.cinzas_nao_assentam", "narrative", "ash"
        )
        assert all(
            (attempt.progress or {}).get("settled")
            for attempt in (brazier_attempt, crypt_attempt, wind_attempt, atmosphere_attempt)
        )
        assert character.xp == 1425
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == character.id,
                Brazier.brazier_id == "tdo.brazier.vento_morto",
            )
        ) == 1
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id.in_(
                    {"dungeon.tdo.cripta_ocaso", "known_path.tdo.cripta_ocaso"}
                ),
            )
        ) == 2
        assert await session.scalar(
            select(func.count(RewardComponent.id)).where(
                RewardComponent.kind == "xp",
                RewardComponent.reward_event_id.in_(
                    select(RewardEvent.id).where(RewardEvent.character_id == character.id)
                ),
            )
        ) == 3


@pytest.mark.asyncio
async def test_uncommon_hunt_optional_loot_uses_global_boundaries(database, monkeypatch):
    actor = 880308
    service = await _seed_charneca(
        database, actor=actor, level=4, location=CHARNECA
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        activity = GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=HUNT_CONTENT,
            status="completed",
            state_version=0,
            ruleset_version="gdd-1.4.7-baseline-1.0",
            last_valid_action_at=datetime.now(UTC),
        )
        session.add(activity)
        await session.flush()
        session.add(
            HuntContext(
                game_activity_id=activity.id,
                character_id=character.id,
                local_id=CHARNECA_LOCATION,
                creature_id="aranha_cinza",
                category="uncommon",
                enemy_level=3,
                variant=None,
                seed="optional-loot-seed",
                loot_profile="hunt",
            )
        )
        await session.flush()
        draws = {
            "uncommon-materials": 0,
            "fragment": 4,
            "equipment": 13,
            "rune": 14,
            "rune:rarity": 0,
            "rune.family": 0,
        }
        monkeypatch.setattr(
            road_application,
            "_draw_int",
            lambda seed, purpose, modulo: draws.get(purpose, 99),
        )
        await service._settle_hunt(session, character, activity, uuid4())
        components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id == f"activity:{activity.id}")
            )
        ).all()
        assert any(row.kind == "equipment" for row in components)
        assert any(
            row.kind == "rune" and row.payload["rarity"] == "Rara"
            for row in components
        )
        assert any(
            row.kind == "fragment"
            and row.item_id == "material.tdo.fragmento_aprimoramento_i"
            for row in components
        )
        assert not any(row.kind == "catalyst" for row in components)
        assert await session.scalar(
            select(func.count(EquipmentItem.id)).where(
                EquipmentItem.character_id == character.id
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RuneStack.id)).where(
                RuneStack.character_id == character.id
            )
        ) == 1


@pytest.mark.asyncio
async def test_charneca_exploration_combat_uses_only_thematic_economy(database, monkeypatch):
    actor = 880309
    service = await _seed_charneca(
        database, actor=actor, level=4, location=CHARNECA
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        activity = GameActivity(
            id=uuid4(),
            character_id=character.id,
            content_id=EXPLORE_CONTENT,
            status="completed",
            state_version=0,
            ruleset_version="gdd-1.4.7-baseline-1.0",
            last_valid_action_at=datetime.now(UTC),
        )
        session.add(activity)
        await session.flush()
        attempt = ExplorationAttempt(
            character_id=character.id,
            local_id=CHARNECA_LOCATION,
            ruleset_version="gdd-1.4.7-baseline-1.0",
            seed="explore-spider-seed",
            category="combat",
            result_id="explore.tdo.charneca.combat.aranha_cinza",
            status="active",
            state_version=0,
            progress={"result_text": "Aranha."},
            activity_id=activity.id,
        )
        session.add(attempt)
        await session.flush()
        session.add(
            HuntContext(
                game_activity_id=activity.id,
                character_id=character.id,
                local_id=CHARNECA_LOCATION,
                creature_id="aranha_cinza",
                category="uncommon",
                enemy_level=3,
                variant=None,
                seed=attempt.seed,
                loot_profile="exploration_combat",
            )
        )
        await session.flush()
        monkeypatch.setattr(
            road_application,
            "_draw_int",
            lambda seed, purpose, modulo: 0
            if purpose == "exploration-material-extra"
            else 99,
        )
        await service._settle_charneca_exploration(session, character, attempt, "Aranha.")
        components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id == f"explore:{attempt.id}")
            )
        ).all()
        assert character.vigor == 96
        assert character.crowns == 20
        assert len([row for row in components if row.kind == "material"]) == 2
        assert all(
            row.item_id
            in {"material.tdo.erva_cinzenta", "material.tdo.residuo_ocaso"}
            for row in components
            if row.kind == "material"
        )
        assert not any(
            row.kind in {"equipment", "rune", "fragment", "catalyst"}
            for row in components
        )
        assert await session.scalar(
            select(func.count(Unlock.id)).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == "hunt_round.charneca_da_fuligem",
            )
        ) == 0


@pytest.mark.asyncio
async def test_p2_codex_entry_does_not_consume_explore_stone_unique(database, monkeypatch):
    actor = 880304
    service = await _seed_charneca(
        database, actor=actor, level=4, location=CHARNECA
    )
    custom = ExplorationLocationProfile(
        local_id=CHARNECA_LOCATION,
        category_weights=(("knowledge", 100),),
        results=(
            ExplorationResultDefinition(
                "pedra_marcada",
                "knowledge",
                "explore.tdo.charneca.pedra_marcada",
                60,
                "A Pedra Marcada foi examinada.",
                unique=True,
            ),
            ExplorationResultDefinition(
                "vestigios_fuligem",
                "knowledge",
                "explore.tdo.charneca.vestigios_fuligem",
                40,
                "Vestígios observados.",
            ),
        ),
    )
    monkeypatch.setitem(
        road_application.EXPLORATION_PROFILES, CHARNECA_LOCATION, custom
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        session.add(
            CodexEntry(
                character_id=character.id,
                entry_id="codex.mystery.marcas_na_fuligem",
            )
        )
        await session.commit()

    first_seed = next(
        f"{value:032x}"
        for value in range(10000)
        if select_exploration_result(
            f"{value:032x}", 4, profile=custom
        ) == "pedra_marcada"
    )
    seeds = deque((first_seed, "00000000000000000000000000000001"))
    monkeypatch.setattr(
        road_application, "uuid4", lambda: SimpleNamespace(hex=seeds.popleft())
    )
    first = await service.explore(actor)
    assert first.result_id == "explore.tdo.charneca.pedra_marcada"
    await service.acknowledge_result(actor)
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        attempt = await session.scalar(
            select(ExplorationAttempt).where(ExplorationAttempt.id == first.attempt_id)
        )
        assert character.xp == 193
        attempt.created_at = datetime.now(UTC) - timedelta(minutes=6)
        await session.commit()

    second = await service.explore(actor)
    assert second.result_id == "explore.tdo.charneca.vestigios_fuligem"
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(func.count(ExplorationAttempt.id)).where(
                ExplorationAttempt.character_id == character.id,
                ExplorationAttempt.result_id == "explore.tdo.charneca.pedra_marcada",
                ExplorationAttempt.status == "completed",
            )
        ) == 1


@pytest.mark.asyncio
async def test_charneca_uncommon_and_common_hunt_settlement(database, monkeypatch):
    actor = 880305
    service = await _seed_charneca(
        database, actor=actor, level=4, location=CHARNECA
    )
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )

        async def add_context(creature_id, category, enemy_level, seed):
            activity = GameActivity(
                id=uuid4(),
                character_id=character.id,
                content_id=HUNT_CONTENT,
                status="completed",
                state_version=0,
                ruleset_version="gdd-1.4.7-baseline-1.0",
                last_valid_action_at=datetime.now(UTC),
            )
            session.add(activity)
            await session.flush()
            context = HuntContext(
                game_activity_id=activity.id,
                character_id=character.id,
                local_id=CHARNECA_LOCATION,
                creature_id=creature_id,
                category=category,
                enemy_level=enemy_level,
                variant=None,
                seed=seed,
                loot_profile="hunt",
            )
            session.add(context)
            await session.flush()
            return activity

        def draw(seed, purpose, modulo):
            return {
                "uncommon-materials": 1,
                "fragment": 99,
                "equipment": 99,
                "rune": 999,
                "material-roll": 99,
            }.get(purpose, 0)

        monkeypatch.setattr(road_application, "_draw_int", draw)
        spider_activity = await add_context("aranha_cinza", "uncommon", 3, "spider-seed")
        await service._settle_hunt(session, character, spider_activity, uuid4())
        components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id == f"activity:{spider_activity.id}")
            )
        ).all()
        spider_materials = [row.item_id for row in components if row.kind == "material"]
        assert len(spider_materials) == 2
        assert set(spider_materials) <= {
            "material.tdo.erva_cinzenta",
            "material.tdo.residuo_ocaso",
        }
        assert not any(row.kind == "catalyst" for row in components)
        assert any(row.kind == "xp" and row.quantity == 370 for row in components)
        assert any(row.kind == "crowns" and row.quantity == 10 for row in components)

        deer_miss = await add_context("cervo_escoriado", "common", 4, "deer-miss")
        await service._settle_hunt(session, character, deer_miss, uuid4())
        miss_components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id == f"activity:{deer_miss.id}")
            )
        ).all()
        assert not any(row.kind == "material" for row in miss_components)

        monkeypatch.setattr(
            road_application,
            "_draw_int",
            lambda seed, purpose, modulo: 0 if purpose == "material-roll" else 99,
        )
        deer_success = await add_context("cervo_escoriado", "common", 4, "deer-success")
        await service._settle_hunt(session, character, deer_success, uuid4())
        success_components = (
            await session.scalars(
                select(RewardComponent)
                .join(RewardEvent)
                .where(RewardEvent.source_id == f"activity:{deer_success.id}")
            )
        ).all()
        deer_materials = [row.item_id for row in success_components if row.kind == "material"]
        assert deer_materials == ["material.tdo.couro_escoriado"]
