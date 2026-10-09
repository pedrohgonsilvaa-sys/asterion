from copy import deepcopy
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.road import BOSQUE, CHARNECA, REFUGE, ROAD, RoadService
from asterion.application.round import RoundService
from asterion.domain.road import BOSQUE_LOCATION, BOSQUE_ROUND_FAMILIARITY, creature_for
from asterion.infrastructure.db.models import (
    Brazier,
    Character,
    GameActivity,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    Quest,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import start_manual_hunt_after_no_match
from tests.test_road_integration import _seed_road


async def _seed_bosque(
    database,
    actor: int,
    *,
    level: int = 6,
    location: str = BOSQUE,
    braziers: tuple[str, ...] = (),
    familiar: bool = False,
):
    _, service = await _seed_road(database, actor=actor, vigor=77)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        character.level = level
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character.id)
        )
        world.location = location
        session.add_all(
            (
                Quest(
                    character_id=character.id,
                    quest_id="P2",
                    title="Fuligem sem Fogo",
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.7",
                ),
                Quest(
                    character_id=character.id,
                    quest_id="P3",
                    title="Sob Galhos Calcinados",
                    status="completed",
                    step=6,
                    content_version="tdo-1.0.10",
                    progress={"bosque_entered": True, "selected_reward": "veil"},
                ),
                Unlock(character_id=character.id, unlock_id="hunt_manual.bosque_calcinado"),
                Unlock(character_id=character.id, unlock_id="explore.bosque_calcinado"),
                Unlock(character_id=character.id, unlock_id="route.tdo.charneca_bosque"),
                Unlock(character_id=character.id, unlock_id="route.tdo.refugio_charneca"),
                *(
                    (Unlock(character_id=character.id, unlock_id=BOSQUE_ROUND_FAMILIARITY),)
                    if familiar
                    else ()
                ),
                *(Brazier(character_id=character.id, brazier_id=item) for item in braziers),
            )
        )
    return character.id, RoadService(sessions, "ocaso"), RoundService(sessions, "ocaso")


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
async def test_bosque_manual_hunt_freezes_local_and_first_win_unlocks_round(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor = 998401
    character_id, service, _ = await _seed_bosque(database, actor, level=5)
    seen_profiles = []

    def choose(seed, level, **kwargs):
        seen_profiles.append(kwargs.get("profile"))
        return creature_for("carnical_fuligem")

    monkeypatch.setattr(road_module, "select_creature", choose)
    combat = await start_manual_hunt_after_no_match(service, actor, monkeypatch)
    assert combat.kind == "combat"
    assert seen_profiles and seen_profiles[0].local_id == BOSQUE_LOCATION
    async with database[1]() as session:
        context = await session.scalar(
            select(HuntContext).where(HuntContext.game_activity_id == combat.activity_id)
        )
        assert context.local_id == BOSQUE_LOCATION
        assert context.creature_id == "carnical_fuligem"
        assert context.category == "common"
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == BOSQUE_ROUND_FAMILIARITY,
            )
        ) is None

    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    victory = await service.action(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert victory.kind == "hunt_victory" and victory.location == BOSQUE
    async with database[1]() as session:
        assert await session.scalar(
            select(Unlock).where(
                Unlock.character_id == character_id,
                Unlock.unlock_id == BOSQUE_ROUND_FAMILIARITY,
            )
        ) is not None


@pytest.mark.asyncio
async def test_bosque_exploration_braseiro_is_unique_and_enters_brazier_network(
    database, monkeypatch
):
    import asterion.application.road as road_module

    actor = 998402
    character_id, service, _ = await _seed_bosque(database, actor, level=6)
    monkeypatch.setattr(
        road_module,
        "_explore_result",
        lambda *args: (
            "great_discovery",
            "explore.tdo.bosque.braseiro",
            "Braseiro dos Galhos Mortos encontrado.",
        ),
    )
    result = await service.explore(actor)
    assert result.kind == "exploration"
    assert result.result_id == "explore.tdo.bosque.braseiro"
    resumed = await service.resume(actor)
    assert resumed.attempt_id == result.attempt_id
    assert resumed.result_id == result.result_id
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert await session.scalar(
            select(func.count(Brazier.id)).where(
                Brazier.character_id == character_id,
                Brazier.brazier_id == "tdo.brazier.galhos_mortos",
            )
        ) == 1
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{result.attempt_id}",
            )
        ) == 1
        assert character.vigor == 77
    await service.acknowledge_result(actor)
    travel = await service.travel_brazier(actor, "tdo.brazier.estrada")
    assert travel.kind == "road" and travel.location == ROAD


@pytest.mark.asyncio
async def test_bosque_round_freezes_local_and_elite_interrupt_reconnects_same_encounter(
    database, monkeypatch
):
    import asterion.application.round as round_module

    actor = 998403
    character_id, _, service = await _seed_bosque(
        database, actor, level=6, familiar=True
    )
    monkeypatch.setattr(
        round_module,
        "select_creature",
        lambda seed, level, **kwargs: creature_for("viuva_fuligem"),
    )
    prepared = await service.prepare_round(actor, 5)
    assert prepared.kind == "round_prepare"
    started = await service.start_round(actor, prepared.round_id, prepared.state_version)
    assert started.kind == "round_interrupted"
    assert started.creature == "Viúva da Fuligem"
    first_encounter_id = started.encounter_id
    resumed = await service.resume(actor)
    assert resumed.kind == "round_interrupted"
    assert resumed.encounter_id == first_encounter_id
    async with database[1]() as session:
        state = await session.get(HuntRound, started.round_id)
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(HuntRoundEncounter.round_id == started.round_id)
        )
        context = await session.scalar(
            select(HuntContext).where(
                HuntContext.game_activity_id == encounter.activity_id
            )
        )
        assert (state.config_snapshot or {}).get("local_id") == BOSQUE_LOCATION
        assert encounter.creature_id == "viuva_fuligem"
        assert encounter.category == "elite"
        assert context is None
        assert await session.scalar(
            select(func.count(HuntRoundEncounter.id)).where(
                HuntRoundEncounter.id == first_encounter_id
            )
        ) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("known_braziers", "expected_name", "expected_location"),
    [
        ((), "Braseiro do Refúgio", REFUGE),
        (("tdo.brazier.vento_morto",), "Braseiro do Vento Morto", CHARNECA),
        (
            ("tdo.brazier.vento_morto", "tdo.brazier.galhos_mortos"),
            "Braseiro dos Galhos Mortos",
            BOSQUE,
        ),
    ],
)
async def test_bosque_hunt_defeat_uses_regional_recovery_priority(
    database, monkeypatch, known_braziers, expected_name, expected_location
):
    import asterion.application.road as road_module

    actor = 998410 + len(known_braziers)
    character_id, service, _ = await _seed_bosque(
        database, actor, level=6, braziers=known_braziers
    )
    combat = await start_manual_hunt_after_no_match(service, actor, monkeypatch)
    monkeypatch.setattr(road_module, "act", _terminal("defeat"))
    defeated = await service.action(
        actor, combat.activity_id, combat.combat.version, "attack"
    )
    assert defeated.kind == "hunt_defeat"
    assert defeated.recovery_brazier == expected_name
    assert defeated.recovery_location == expected_location
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.scalar(
            select(WorldState).where(WorldState.character_id == character_id)
        )
        assert world.location == expected_location
        assert character.hp == character.max_hp
        assert character.vigor == 77
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"activity:{combat.activity_id}",
            )
        ) == 0
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        ) == 0
