from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.groups import GroupError, GroupService
from asterion.application.p7 import (
    GARGANTA as VDE_GARGANTA,
)
from asterion.application.p7 import (
    GARGANTA_BRAZIER,
    GARGANTA_EXPLORE_UNLOCK,
    GARGANTA_HUNT_UNLOCK,
    GARGANTA_LOCATION_ID,
    GARGANTA_VIGILIA_ROUTE,
    P7_ID,
    VIGILIA_BRAZIER,
    VIGILIA_LOCATION_ID,
)
from asterion.application.p7 import (
    REGION as VDE_REGION,
)
from asterion.application.p7 import (
    VIGILIA as VDE_VIGILIA,
)
from asterion.application.road import (
    HUNT_CONTENT,
    VDE_EXPLORATION_UNIQUE_XP,
    VDE_MATA,
    RoadService,
)
from asterion.application.round import RoundService
from asterion.application.vde_missions import (
    MATA_EXPLORE_UNLOCK,
    MATA_HUNT_UNLOCK,
    MISSION_CONTENT_IDS,
    P8_ID,
    P8_REWARD_SOURCE,
    S7_ID,
    S7_REWARD_SOURCE,
    VDEMissionService,
)
from asterion.bot.road_ui import render_current_local
from asterion.domain.combat_math import Stats
from asterion.domain.road import (
    EXPLORATION_CATEGORY_WEIGHTS,
    EXPLORATION_PROFILES,
    HUNT_PROFILES,
    MATERIAL_POOLS,
    VARIANT_POOL,
    VDE_BASIC_MATERIAL_CREATURE_IDS,
    VDE_CREATURES,
    VDE_GARGANTA_LOCATION,
    VDE_GARGANTA_ROUND_FAMILIARITY,
    VDE_MATA_BRAZIER,
    VDE_MATA_LOCATION,
    create_road_combat,
    creature_for,
    material_for,
    select_exploration_result,
    weighted_choice,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Brazier,
    CampaignObjectiveCredit,
    Character,
    CodexEntry,
    CodexFragment,
    ExplorationAttempt,
    GameActivity,
    HuntContext,
    HuntRound,
    HuntRoundEncounter,
    LocationDiscovery,
    MaterialStack,
    PvpveCollision,
    PvpveCollisionMember,
    PvpveDomainGrant,
    PvpveQueue,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.test_p7_integration import _seed_p7_ready, _terminal

VDE_BASIC_MATERIAL_POOLS = {
    "lobo_musgoso": (("material.vde.couro_musgoso", 100),),
    "gralha_vale": (
        ("material.vde.erva_de_turfa", 70),
        ("material.vde.resina_enredada", 30),
    ),
    "peregrino_enredado": (
        ("material.vde.ferro_enredado", 70),
        ("material.vde.resina_enredada", 30),
    ),
    "aranha_cipo": (
        ("material.vde.erva_de_turfa", 60),
        ("material.vde.resina_enredada", 40),
    ),
    "cervo_no": (("material.vde.couro_musgoso", 100),),
    "sanguessuga_turfa": (
        ("material.vde.erva_de_turfa", 80),
        ("material.vde.resina_enredada", 20),
    ),
    "casca_errante": (
        ("material.vde.resina_enredada", 80),
        ("material.vde.erva_de_turfa", 20),
    ),
    "mariposa_breu_verde": (
        ("material.vde.erva_de_turfa", 65),
        ("material.vde.resina_enredada", 35),
    ),
    "vigia_enraizado": (
        ("material.vde.ferro_enredado", 90),
        ("material.vde.resina_enredada", 10),
    ),
    "no_feroz": (
        ("material.vde.couro_musgoso", 80),
        ("material.vde.resina_enredada", 20),
    ),
    "viuva_cipos": (
        ("material.vde.erva_de_turfa", 60),
        ("material.vde.resina_enredada", 40),
    ),
    "carrasco_casca": (
        ("material.vde.resina_enredada", 70),
        ("material.vde.ferro_enredado", 30),
    ),
}


def test_vde_basic_material_pools_match_the_regional_authority():
    assert VDE_BASIC_MATERIAL_CREATURE_IDS == frozenset(VDE_BASIC_MATERIAL_POOLS)
    for creature_id, expected_pool in VDE_BASIC_MATERIAL_POOLS.items():
        assert MATERIAL_POOLS[creature_id] == expected_pool
        assert sum(weight for _, weight in expected_pool) == 100
        allowed = {material for material, _ in expected_pool}
        assert {
            material_for(creature_id, f"vde-pool-check:{index}")
            for index in range(256)
        } <= allowed

    assert material_for("lobo_musgoso", "seed-a") == "material.vde.couro_musgoso"
    assert material_for("cervo_no", "seed-b") == "material.vde.couro_musgoso"
    assert MATERIAL_POOLS["vigia_enraizado"] == (
        ("material.vde.ferro_enredado", 90),
        ("material.vde.resina_enredada", 10),
    )
    assert MATERIAL_POOLS["casca_errante"] == (
        ("material.vde.resina_enredada", 80),
        ("material.vde.erva_de_turfa", 20),
    )


def test_vde_material_unit_subdraws_are_ordinal_deterministic_and_allow_repeats():
    base_seed = "persisted-economic-seed"
    pool = VDE_BASIC_MATERIAL_POOLS["peregrino_enredado"]
    actual = tuple(
        material_for("peregrino_enredado", f"{base_seed}:material.basic.{ordinal}")
        for ordinal in range(4)
    )
    expected = tuple(
        weighted_choice(f"{base_seed}:material.basic.{ordinal}", pool)
        for ordinal in range(4)
    )
    assert actual == expected
    assert actual == tuple(
        material_for("peregrino_enredado", f"{base_seed}:material.basic.{ordinal}")
        for ordinal in range(4)
    )
    repeatable = tuple(
        material_for("lobo_musgoso", f"{base_seed}:material:{ordinal}")
        for ordinal in range(4)
    )
    assert repeatable == ("material.vde.couro_musgoso",) * 4


async def _seed_vde_ready(
    database, actor: int, *, level: int = 13, round_ready: bool = True
):
    character_id, sessions = await _seed_p7_ready(database, actor, level=level)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.region = VDE_REGION
        world.location = VDE_VIGILIA
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P7_ID,
                title="A Estrada Estrangulada",
                status="completed",
                step=7,
                content_version="vales-1.0.3",
                progress={"completed": True},
            )
        )
        round_unlocks = (
            [
                Unlock(
                    character_id=character_id,
                    unlock_id=VDE_GARGANTA_ROUND_FAMILIARITY,
                )
            ]
            if round_ready
            else []
        )
        session.add_all(
            [
                Unlock(character_id=character_id, unlock_id=GARGANTA_VIGILIA_ROUTE),
                Brazier(character_id=character_id, brazier_id=GARGANTA_BRAZIER),
                Brazier(character_id=character_id, brazier_id=VIGILIA_BRAZIER),
                LocationDiscovery(character_id=character_id, location_id=GARGANTA_LOCATION_ID),
                LocationDiscovery(character_id=character_id, location_id=VIGILIA_LOCATION_ID),
                Unlock(character_id=character_id, unlock_id=GARGANTA_HUNT_UNLOCK),
                Unlock(character_id=character_id, unlock_id=GARGANTA_EXPLORE_UNLOCK),
                *round_unlocks,
            ]
        )
    return character_id, sessions


@pytest.mark.asyncio
async def test_vde_garganta_hunt_and_exploration_are_available_after_p7(
    database, monkeypatch
):
    actor = 999731
    character_id, sessions = await _seed_vde_ready(
        database, actor, round_ready=False
    )
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = VDE_GARGANTA

    hunt = HUNT_PROFILES[VDE_GARGANTA_LOCATION]
    assert hunt.creature_weights == (
        ("lobo_musgoso", 34),
        ("gralha_vale", 33),
        ("peregrino_enredado", 30),
        ("no_feroz", 3),
    )
    assert hunt.variant_chance == 10
    mata = HUNT_PROFILES[VDE_MATA_LOCATION]
    assert mata.creature_weights == (
        ("lobo_musgoso", 20),
        ("gralha_vale", 17),
        ("peregrino_enredado", 15),
        ("aranha_cipo", 21),
        ("cervo_no", 23),
        ("no_feroz", 2),
        ("viuva_cipos", 2),
    )
    assert mata.variant_chance == 12
    assert {creature.creature_id for creature in VDE_CREATURES} >= {
        creature_id for creature_id, _ in hunt.creature_weights
    }
    assert all(creature_id in MATERIAL_POOLS for creature_id, _ in hunt.creature_weights)
    creatures = {creature.creature_id: creature for creature in VDE_CREATURES}
    assert {
        creature_id: (
            creature.category,
            creature.archetype,
            creature.unlock_level,
            creature.max_level,
        )
        for creature_id, creature in creatures.items()
    } == {
        "lobo_musgoso": ("common", "predator", 11, 14),
        "gralha_vale": ("common", "predator", 11, 14),
        "peregrino_enredado": ("uncommon", "balanced", 11, 15),
        "aranha_cipo": ("common", "controller", 13, 16),
        "cervo_no": ("common", "brute", 13, 17),
        "no_feroz": ("elite", "predator", 13, 14),
        "viuva_cipos": ("elite", "controller", 15, 17),
        "sanguessuga_turfa": ("common", "balanced", 15, 18),
        "casca_errante": ("uncommon", "armored", 15, 19),
        "mariposa_breu_verde": ("common", "caster", 16, 19),
        "vigia_enraizado": ("uncommon", "armored", 18, 20),
        "carrasco_casca": ("elite", "armored", 18, 20),
    }
    assert VARIANT_POOL["no_feroz"] == ()
    assert VARIANT_POOL["viuva_cipos"] == ()
    assert VARIANT_POOL["lobo_musgoso"] == ("furious", "agile", "hemorrhagic")

    explore = EXPLORATION_PROFILES[VDE_GARGANTA_LOCATION]
    mata_explore = EXPLORATION_PROFILES[VDE_MATA_LOCATION]
    assert dict(explore.category_weights) == EXPLORATION_CATEGORY_WEIGHTS
    assert dict(mata_explore.category_weights) == EXPLORATION_CATEGORY_WEIGHTS

    def weights(profile, category):
        return {
            item.key: item.weight for item in profile.results if item.category == category
        }

    assert weights(explore, "great_discovery") == {"marco_lacos": 100}
    assert weights(explore, "knowledge") == {"pegadas_barranco": 60, "cordas_arrastadas": 40}
    assert weights(explore, "narrative") == {"sinos_sem_maos": 70, "nevoa_paredoes": 30}
    assert weights(explore, "combat") == {
        "lobo_musgoso": 40,
        "gralha_vale": 35,
        "peregrino_enredado": 25,
    }
    resource_weights = {
        result.key: result.weight for result in explore.results if result.category == "resource"
    }
    assert resource_weights == {"ferro": 30, "couro": 30, "erva": 25, "resina": 15}
    assert weights(explore, "atmospheric") == {
        "pedra_musgo": 34,
        "ponte_sem_caminho": 33,
        "cordas_abismo": 33,
    }
    assert weights(mata_explore, "great_discovery") == {
        "brazier_copas": 50,
        "fosso_raizes": 50,
    }
    assert weights(mata_explore, "knowledge") == {
        "passarela_partida": 55,
        "rastros_copas": 45,
    }
    assert weights(mata_explore, "narrative") == {
        "madeira_geme": 55,
        "galhos_sem_vento": 45,
    }
    assert weights(mata_explore, "combat") == {
        "lobo_musgoso": 20,
        "gralha_vale": 15,
        "peregrino_enredado": 15,
        "aranha_cipo": 25,
        "cervo_no": 25,
    }
    assert not any(
        creature_for(result.creature_id).category == "elite"
        for result in mata_explore.results
        if result.category == "combat" and result.creature_id is not None
    )
    mata_resources = {
        result.key: result.weight
        for result in mata_explore.results
        if result.category == "resource"
    }
    assert mata_resources == {"couro": 35, "erva": 30, "resina": 25, "ferro": 10}
    assert weights(mata_explore, "atmospheric") == {
        "troncos_vazio": 34,
        "folhas_nao_caem": 33,
        "ruina_copas": 33,
    }
    unique_xp = {
        item.result_id: (item.unique, item.min_level)
        for profile in (explore, mata_explore)
        for item in profile.results
        if item.unique
    }
    assert unique_xp == {
        "explore.vde.garganta.marco_dos_lacos": (True, 11),
        "explore.vde.garganta.sinos_sem_maos": (True, 11),
        "explore.vde.mata.braseiro_das_copas": (True, 13),
        "explore.vde.mata.entrada_fosso_raizes": (True, 13),
        "explore.vde.mata.passarela_partida": (True, 13),
    }
    assert VDE_EXPLORATION_UNIQUE_XP == {
        "explore.vde.garganta.marco_dos_lacos": 1536,
        "explore.vde.garganta.sinos_sem_maos": 480,
        "explore.vde.mata.braseiro_das_copas": 1832,
        "explore.vde.mata.entrada_fosso_raizes": 1832,
        "explore.vde.mata.passarela_partida": 573,
        "explore.vde.baixios.braseiro_turfa_fria": 2336,
        "explore.vde.baixios.galeria_afogada": 2336,
        "explore.vde.baixios.marcas_sob_a_agua": 730,
        "explore.vde.claustro.braseiro_pedras_enlacadas": 2704,
        "explore.vde.claustro.entrada_santuario_no_antigo": 2704,
        "explore.vde.claustro.tracado_do_no": 845,
    }
    assert select_exploration_result(
        "repeat-test",
        13,
        excluded=("explore.vde.mata.braseiro_das_copas",),
        profile=mata_explore,
    ) != "brazier_copas"

    road = RoadService(sessions, "ocaso")
    current = await road.resume(actor)
    assert current is not None and current.kind == "vde_garganta"
    assert current.hunt_enabled is True and current.explore_enabled is True
    prepared_hunt = await road.prepare_hunt(actor)
    assert prepared_hunt is not None and prepared_hunt.kind == "hunt_prepare"
    prepared = await road.prepare_explore(actor)
    assert prepared is not None and prepared.kind == "explore_prepare"
    round_gate = await RoundService(sessions, "ocaso").prepare_round(actor, 5)
    assert round_gate is not None and round_gate.kind == "vde_garganta"
    assert round_gate.familiar is False
    screen = render_current_local(current, explore_state="available")
    callbacks = [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]
    assert "road:explore:start" in callbacks
    assert "Caçada · Disponível" in screen.text
    assert any(
        button.callback_data == "road:hunt"
        for row in screen.keyboard.inline_keyboard
        for button in row
    )
    assert "Aguardando tabela canônica" not in screen.text

    import asterion.application.road as road_application

    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args, **kwargs: (
            "resource",
            "explore.vde.garganta.ferro_enredado",
            "Ferro Enredado pode ser recolhido na Garganta.",
        ),
    )
    result = await road.explore(actor)
    assert result is not None and result.kind == "exploration"
    assert result.result_id == "explore.vde.garganta.ferro_enredado"
    async with sessions() as session:
        assert (
            await session.scalar(
                select(MaterialStack.quantity).where(
                    MaterialStack.character_id == character_id,
                    MaterialStack.material_id == "material.vde.ferro_enredado",
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"explore:{result.attempt_id}",
                )
            )
            is not None
        )

    # Ronda's safety preflight requires the character to be healthy enough to
    # begin its automatic encounter; the test is about the unlock and regional
    # settlement profile, so restore the fixture's HP between activities.
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = character.max_hp

@pytest.mark.asyncio
async def test_vde_first_manual_victory_unlocks_ronda_and_ronda_can_start(
    database, monkeypatch
):
    import asterion.application.pvpve as pvpve_application
    import asterion.application.road as road_application
    import asterion.application.round as round_application
    import asterion.application.vigor as vigor_application

    actor = 999741
    character_id, sessions = await _seed_vde_ready(database, actor, round_ready=False)
    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, VDE_GARGANTA) is not None
    monkeypatch.setattr(
        road_application,
        "select_creature",
        lambda _seed, _level, profile=None: creature_for("lobo_musgoso"),
    )

    before = await road.resume(actor)
    assert before is not None and before.kind == "vde_garganta"
    assert before.hunt_enabled and not before.familiar
    queued = await road.start_hunt(actor)
    assert queued is not None and queued.kind == "hunt_queue"
    assert queued.pvpve_queue_id is not None
    combat = await road.pvpve.continue_queue(actor, queued.pvpve_queue_id)
    assert combat is not None and combat.kind == "combat"

    for _ in range(120):
        if combat.kind != "combat":
            break
        combat = await road.action(
            actor,
            combat.activity_id,
            combat.combat.version,
            "attack",
        )
        assert combat is not None
    assert combat.kind == "hunt_victory"
    await road.acknowledge_result(actor)

    # The Ronda's PvPvE exposure ends at its official three-minute frontier.
    # A controlled clock keeps the integration test deterministic without
    # shortening the production cadence.
    round_start = datetime.now(UTC)

    class ControlledDateTime(datetime):
        current = round_start

        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls.current.replace(tzinfo=None)
            return cls.current.astimezone(tz)

    monkeypatch.setattr(round_application, "datetime", ControlledDateTime)
    monkeypatch.setattr(vigor_application, "utcnow", lambda: ControlledDateTime.current)
    monkeypatch.setattr(pvpve_application, "_utcnow", lambda: ControlledDateTime.current)
    monkeypatch.setattr(
        round_application,
        "select_creature",
        lambda _seed, _level, profile=None: creature_for("lobo_musgoso"),
    )
    original_create_road_combat = round_application.create_road_combat

    def safe_round_combat(*args, **kwargs):
        state = original_create_road_combat(*args, **kwargs)
        enemy = state.fighters["enemy"]
        enemy.stats = Stats(
            enemy.stats.hp,
            Decimal(1),
            enemy.stats.defense,
            enemy.stats.agility,
        )
        return state

    monkeypatch.setattr(round_application, "create_road_combat", safe_round_combat)
    original_draw_int = road_application._draw_int
    monkeypatch.setattr(
        road_application,
        "_draw_int",
        lambda seed, purpose, upper: (
            0 if purpose == "material-roll" else original_draw_int(seed, purpose, upper)
        ),
    )

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = character.max_hp
        before_material = await session.scalar(
            select(MaterialStack.quantity).where(
                MaterialStack.character_id == character_id,
                MaterialStack.material_id == "material.vde.couro_musgoso",
            )
        ) or 0

    round_service = RoundService(sessions, "ocaso")
    prepared = await round_service.prepare_round(actor, 5)
    assert prepared is not None and prepared.kind == "round_prepare"
    started = await round_service.start_round(
        actor, prepared.round_id, prepared.state_version
    )
    assert started is not None and started.kind == "hunt_queue"
    assert started.pvpve_queue_id is not None
    resumed_queue = await round_service.resume(actor)
    assert resumed_queue is not None
    assert resumed_queue.kind == "hunt_queue"
    assert resumed_queue.pvpve_queue_id == started.pvpve_queue_id
    async with sessions() as session:
        active_round = await session.scalar(
            select(HuntRound).where(
                HuntRound.character_id == character_id,
                HuntRound.status == "active",
            )
        )
        assert active_round is not None
        round_id = active_round.id
        waiting_queue = await session.get(PvpveQueue, started.pvpve_queue_id)
        assert waiting_queue is not None and waiting_queue.status == "waiting"

    ControlledDateTime.current += timedelta(minutes=3)
    assert await round_service.advance_due_rounds() == 1
    after_frontier = await round_service.resume(actor)
    assert after_frontier is not None
    assert after_frontier.kind in {"hunt_queue", "round_active"}
    async with sessions() as session:
        state = await session.get(HuntRound, round_id)
        assert state is not None and state.completed_encounters == 1
        encounter = await session.scalar(
            select(HuntRoundEncounter).where(
                HuntRoundEncounter.round_id == round_id,
                HuntRoundEncounter.ordinal == 1,
            )
        )
        assert encounter is not None and encounter.status == "completed"
        after_material = await session.scalar(
            select(MaterialStack.quantity).where(
                MaterialStack.character_id == character_id,
                MaterialStack.material_id == "material.vde.couro_musgoso",
            )
        ) or 0
        assert after_material == before_material + 1
    assert MATERIAL_POOLS["lobo_musgoso"] == VDE_BASIC_MATERIAL_POOLS["lobo_musgoso"]


@pytest.mark.asyncio
async def test_vde_hunt_keeps_global_material_quantities_and_settlement_idempotent(
    database,
):
    from asterion.application.road import _draw_int

    def seed_for(purpose: str, modulo: int, result: int) -> str:
        for index in range(100_000):
            seed = f"vde-quantity-{purpose}-{result}-{index}"
            if _draw_int(seed, purpose, modulo) == result:
                return seed
        raise AssertionError("could not derive a deterministic loot test seed")

    actor = 999742
    character_id, sessions = await _seed_vde_ready(database, actor)
    road = RoadService(sessions, "ocaso")
    cases = (
        ("common", "lobo_musgoso", 13, seed_for("material-roll", 100, 79), 1),
        ("common", "lobo_musgoso", 13, seed_for("material-roll", 100, 80), 0),
        ("uncommon", "peregrino_enredado", 13, seed_for("uncommon-materials", 2, 0), 1),
        ("uncommon", "peregrino_enredado", 13, seed_for("uncommon-materials", 2, 1), 2),
        ("elite", "no_feroz", 13, seed_for("elite-materials", 2, 0), 3),
        ("elite", "no_feroz", 13, seed_for("elite-materials", 2, 1), 4),
    )
    expected_per_activity = {}

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character)
            .where(Character.id == character_id)
            .with_for_update()
        )
        assert character is not None
        for index, (category, creature_id, level, seed, material_count) in enumerate(
            cases, start=1
        ):
            activity = GameActivity(
                character_id=character.id,
                content_id=HUNT_CONTENT,
                status="completed",
                state_version=0,
                ruleset_version="gdd-1.5.0-baseline-1.0",
            )
            session.add(activity)
            await session.flush()
            session.add(
                HuntContext(
                    game_activity_id=activity.id,
                    character_id=character.id,
                    local_id=VDE_GARGANTA_LOCATION,
                    creature_id=creature_id,
                    category=category,
                    enemy_level=level,
                    seed=seed,
                    loot_profile="hunt",
                )
            )
            await session.flush()
            expected_per_activity[activity.id] = material_count

            await road._settle_hunt(session, character, activity, UUID(int=index))
            vigor_after_first_commit = character.vigor
            rows = list(
                (
                    await session.scalars(
                        select(RewardComponent)
                        .join(RewardEvent)
                        .where(
                            RewardEvent.character_id == character.id,
                            RewardEvent.source_id == f"activity:{activity.id}",
                            RewardComponent.kind == "material",
                        )
                    )
                ).all()
            )
            assert len(rows) == material_count
            expected_materials = [
                material_for(
                    creature_id,
                    f"{seed}:material.basic.{ordinal}",
                )
                for ordinal in range(material_count)
            ]
            assert sorted(row.item_id for row in rows) == sorted(expected_materials)

            if category == "elite":
                catalyst = await session.scalar(
                    select(RewardComponent)
                    .join(RewardEvent)
                    .where(
                        RewardEvent.character_id == character.id,
                        RewardEvent.source_id == f"activity:{activity.id}",
                        RewardComponent.kind == "catalyst",
                    )
                )
                assert catalyst is not None
                assert catalyst.item_id == "material.vde.catalisador_elite_ii"

            # Duplicate settlement cannot re-roll units, re-spend Vigor, or
            # create a second reward receipt for the same persisted activity.
            await road._settle_hunt(session, character, activity, UUID(int=index))
            assert character.vigor == vigor_after_first_commit
            assert len(
                (
                    await session.scalars(
                        select(RewardComponent)
                        .join(RewardEvent)
                        .where(
                            RewardEvent.character_id == character.id,
                            RewardEvent.source_id == f"activity:{activity.id}",
                            RewardComponent.kind == "material",
                        )
                    )
                ).all()
            ) == material_count

    # Reconnect reads persisted receipts; it does not invoke a second material draw.
    await road.resume(actor)
    async with sessions() as session:
        for activity_id, material_count in expected_per_activity.items():
            assert (
                await session.scalar(
                    select(func.count(RewardComponent.id))
                    .join(RewardEvent)
                    .where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == f"activity:{activity_id}",
                        RewardComponent.kind == "material",
                    )
                )
                == material_count
            )


@pytest.mark.asyncio
async def test_vde_pvpve_domain_adds_a_separate_material_after_normal_prey_settlement(
    database,
):
    winner_actor = 999744
    opponent_actor = 999745
    winner_id, sessions = await _seed_vde_ready(database, winner_actor)
    opponent_id, _ = await _seed_vde_ready(database, opponent_actor)
    road = RoadService(sessions, "ocaso")
    collision_id = uuid4()
    queue_a_id = uuid4()
    queue_b_id = uuid4()
    prey_activity_id = uuid4()
    opponent_activity_id = uuid4()
    context_seed = "vde-pvpve-prey-economic-seed"

    async with sessions.begin() as session:
        winner = await session.get(Character, winner_id)
        opponent = await session.get(Character, opponent_id)
        assert winner is not None and opponent is not None
        now = datetime.now(UTC)
        session.add_all(
            [
                PvpveQueue(
                    id=queue_a_id,
                    server_id="ocaso",
                    local_id=VDE_GARGANTA_LOCATION,
                    roster_size=1,
                    source_type="manual",
                    roster_snapshot=[winner.id.hex],
                    status="matched",
                    created_at=now,
                    expires_at=now + timedelta(minutes=20),
                ),
                PvpveQueue(
                    id=queue_b_id,
                    server_id="ocaso",
                    local_id=VDE_GARGANTA_LOCATION,
                    roster_size=1,
                    source_type="manual",
                    roster_snapshot=[opponent.id.hex],
                    status="matched",
                    created_at=now,
                    expires_at=now + timedelta(minutes=20),
                ),
                GameActivity(
                    id=prey_activity_id,
                    character_id=winner.id,
                    content_id=HUNT_CONTENT,
                    status="completed",
                    state_version=0,
                    ruleset_version="gdd-1.5.0-baseline-1.0",
                ),
                GameActivity(
                    id=opponent_activity_id,
                    character_id=opponent.id,
                    content_id=HUNT_CONTENT,
                    status="failed",
                    state_version=0,
                    ruleset_version="gdd-1.5.0-baseline-1.0",
                ),
            ]
        )
        await session.flush()
        session.add(
            PvpveCollision(
                id=collision_id,
                server_id="ocaso",
                local_id=VDE_GARGANTA_LOCATION,
                roster_size=1,
                queue_a_id=queue_a_id,
                queue_b_id=queue_b_id,
                combat_id=uuid4(),
                ruleset_version="gdd-1.5.0-baseline-1.0",
                state_version=0,
                combat_snapshot={},
                status="prey",
                winner_side="a",
                prey_reference_level=13,
                created_at=now,
                resolved_at=now,
            )
        )
        await session.flush()
        session.add_all(
            [
                PvpveCollisionMember(
                    collision_id=collision_id,
                    character_id=winner.id,
                    account_id=winner_actor,
                    game_activity_id=prey_activity_id,
                    actor_key="a1",
                    side="a",
                    contributed=True,
                    domain_eligible=True,
                    status="prey",
                ),
                PvpveCollisionMember(
                    collision_id=collision_id,
                    character_id=opponent.id,
                    account_id=opponent_actor,
                    game_activity_id=opponent_activity_id,
                    actor_key="b1",
                    side="b",
                    contributed=True,
                    domain_eligible=False,
                    status="defeated",
                ),
                HuntContext(
                    game_activity_id=prey_activity_id,
                    character_id=winner.id,
                    local_id=VDE_GARGANTA_LOCATION,
                    creature_id="peregrino_enredado",
                    category="uncommon",
                    enemy_level=13,
                    seed=context_seed,
                    loot_profile="hunt",
                    pvpve_collision_id=collision_id,
                    pvpve_reference_level=13,
                    pvpve_domain_eligible=True,
                ),
            ]
        )
        await session.flush()
        vigor_before = winner.vigor
        prey_activity = await session.get(GameActivity, prey_activity_id)
        assert prey_activity is not None
        await road._settle_hunt(session, winner, prey_activity, uuid4())
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == winner.id,
                RewardEvent.source_id == f"activity:{prey_activity_id}",
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        normal_materials = [
            component
            for component in components
            if component.kind == "material"
            and component.payload.get("source") != "dominio_do_rastro"
        ]
        domain_materials = [
            component
            for component in components
            if component.kind == "material"
            and component.payload.get("source") == "dominio_do_rastro"
        ]
        legal_materials = {
            "material.vde.ferro_enredado",
            "material.vde.resina_enredada",
        }
        assert 1 <= len(normal_materials) <= 2
        assert all(row.item_id in legal_materials for row in normal_materials)
        assert len(domain_materials) == 1
        assert domain_materials[0].item_id in legal_materials
        grant = await session.get(PvpveDomainGrant, (collision_id, winner.id))
        assert grant is not None and grant.status == "granted"
        assert grant.material_id == domain_materials[0].item_id
        assert grant.material_id == material_for(
            "peregrino_enredado", f"pvpve-domain:{collision_id.hex}:{winner.id.hex}"
        )
        assert winner.vigor == vigor_before - 2

        # Repeating the same settlement cannot add a prey unit or Domain unit.
        await road._settle_hunt(
            session, winner, await session.get(GameActivity, prey_activity_id), uuid4()
        )
        assert len(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        ) == len(components)


def test_vde_conditional_creature_actions_survive_combat_snapshot_round_trip():
    expected_actions = {
        "gralha_vale": "assedio",
        "no_feroz": "cacada_ferido",
        "viuva_cipos": "veneno_concentrado",
    }
    combats = {}
    for creature_id, action_id in expected_actions.items():
        creature = creature_for(creature_id)
        combat = create_road_combat(
            UUID(int=len(combats) + 1),
            "Aventureiro",
            "sentinela",
            "remanescente",
            Decimal(1000),
            creature,
            creature.unlock_level,
            None,
        )
        action = combat.enemy_actions[action_id]
        if creature_id == "gralha_vale":
            assert action.coefficient == Decimal("0.80")
            assert action.cooldown == 3
            assert action.actor_per_bonus_if_target_hp_fraction_at_most == Decimal("0.10")
            assert action.actor_per_bonus_hp_fraction_threshold == Decimal("0.40")
        elif creature_id == "no_feroz":
            assert action.coefficient == Decimal("1.30")
            assert action.cooldown == 3
            assert action.actor_per_bonus_if_target_bleeding == Decimal("0.10")
        else:
            assert action.coefficient == Decimal("0.95")
            assert action.cooldown == 3
            assert action.native_dot_kind == "poison"
            assert action.native_dot_stacks_if_target_poisoned == 1
        combats[creature_id] = combat

    for index, combat in enumerate(combats.values(), start=1):
        restored = decode(encode(combat), UUID(int=index + 10), combat.ruleset, combat.version)
        for action in restored.enemy_actions.values():
            if action.id == "assedio":
                assert action.actor_per_bonus_if_target_hp_fraction_at_most == Decimal("0.10")
            elif action.id == "cacada_ferido":
                assert action.actor_per_bonus_if_target_bleeding == Decimal("0.10")
            elif action.id == "veneno_concentrado":
                assert action.native_dot_stacks_if_target_poisoned == 1


@pytest.mark.asyncio
async def test_vigilia_is_safe_hub_without_hunt_or_round(database):
    actor = 999732
    _, sessions = await _seed_vde_ready(database, actor)
    road = RoadService(sessions, "ocaso")
    view = await road.resume(actor)
    assert view is not None and view.kind == "vde_vigilia"
    assert view.hunt_enabled is False and view.explore_enabled is False
    screen = render_current_local(view)
    callbacks = [button.callback_data for row in screen.keyboard.inline_keyboard for button in row]
    assert "Caçadas · Indisponíveis neste Local" in screen.text
    assert "road:hunt" not in callbacks
    assert "road:explore:start" not in callbacks
    assert "world:round" not in callbacks


@pytest.mark.asyncio
async def test_mata_desbravar_discovers_brazier_once_and_enables_brazier_travel(
    database, monkeypatch
):
    import asterion.application.road as road_application

    actor = 999738
    character_id, sessions = await _seed_vde_ready(database, actor, level=13)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")

    p8 = await missions.start(actor, P8_ID)
    assert p8 is not None and p8.kind == "enter_mata"
    assert await road.travel_route(actor, VDE_MATA) is not None
    p8 = await missions.enter_mata(actor, p8.state_version)
    assert p8 is not None and p8.step == 2

    available = await road.resume(actor)
    assert available is not None and available.location == VDE_MATA
    assert available.explore_enabled is True
    assert available.hunt_enabled is False
    assert await road.prepare_explore(actor) is not None
    async with sessions() as session:
        assert (
            await session.scalar(
                select(Unlock.id).where(
                    Unlock.character_id == character_id,
                    Unlock.unlock_id == MATA_EXPLORE_UNLOCK,
                )
            )
            is not None
        )

    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *args, **kwargs: (
            "great_discovery",
            "explore.vde.mata.braseiro_das_copas",
            "Braseiro das Copas Suspensas encontrado.",
        ),
    )
    result = await road.explore(actor)
    assert result is not None and result.kind == "exploration"
    assert result.result_id == "explore.vde.mata.braseiro_das_copas"

    async with sessions() as session:
        assert (
            await session.scalar(
                select(Brazier.id).where(
                    Brazier.character_id == character_id,
                    Brazier.brazier_id == VDE_MATA_BRAZIER,
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == character_id,
                    LocationDiscovery.location_id == VDE_MATA_LOCATION,
                )
            )
            is not None
        )
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == f"explore:{result.attempt_id}",
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert {(item.kind, item.quantity) for item in components} == {
            ("xp", 1832),
            ("brazier", 1),
        }
        attempt = await session.get(ExplorationAttempt, result.attempt_id)
        character = await session.get(Character, character_id)
        assert attempt is not None and character is not None
        async with session.begin_nested():
            await road._settle_vde_exploration(session, character, attempt, "Braseiro encontrado.")
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == f"explore:{result.attempt_id}",
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(RewardComponent.id)).where(
                    RewardComponent.reward_event_id == event.id,
                    RewardComponent.kind == "xp",
                    RewardComponent.quantity == 1832,
                )
            )
            == 1
        )

    await road.acknowledge_result(actor, result.attempt_id)
    back = await road.travel_route(actor, VDE_VIGILIA)
    assert back is not None and back.location == VDE_VIGILIA
    vigilia = await road.resume(actor)
    assert vigilia is not None
    assert (
        VDE_MATA_BRAZIER,
        "Braseiro das Copas Suspensas",
        VDE_MATA,
    ) in vigilia.brazier_destinations
    assert await road.travel_brazier(actor, VDE_MATA_BRAZIER) is not None
    returned = await road.resume(actor)
    assert returned is not None and returned.location == VDE_MATA


@pytest.mark.asyncio
async def test_mata_hunt_is_available_after_p8_and_level_gate(database):
    actor = 999743
    character_id, sessions = await _seed_vde_ready(database, actor, level=13)
    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        assert world is not None
        world.location = VDE_MATA
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P8_ID,
                title="Entre Galhos Suspensos",
                status="completed",
                step=7,
                content_version="vales-1.0.3",
                progress={"completed": True, "returned_vigilia": True},
            )
        )
        session.add(Unlock(character_id=character_id, unlock_id=MATA_HUNT_UNLOCK))
        session.add(Unlock(character_id=character_id, unlock_id=MATA_EXPLORE_UNLOCK))

    road = RoadService(sessions, "ocaso")
    view = await road.resume(actor)
    assert view is not None and view.kind == "vde_mata"
    assert view.hunt_enabled is True and view.explore_enabled is True
    prepared = await road.prepare_hunt(actor)
    assert prepared is not None and prepared.kind == "hunt_prepare"


@pytest.mark.asyncio
async def test_p8_opening_defeat_is_settled_and_retryable(database):
    actor = 999799
    character_id, sessions = await _seed_vde_ready(database, actor, level=13)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")

    p8 = await missions.start(actor, P8_ID)
    assert p8 is not None and p8.kind == "enter_mata"
    arrived = await road.travel_route(actor, VDE_MATA)
    assert arrived is not None and arrived.location == VDE_MATA
    p8 = await missions.enter_mata(actor, p8.state_version)
    for point in ("a", "b", "c"):
        p8 = await missions.examine(actor, P8_ID, p8.state_version, point)

    # A very low but valid persistent HP snapshot makes the scripted creature's
    # opening action terminal. This is test setup; settlement and retry remain
    # public service operations.
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        character.hp = Decimal("1")

    p8 = await missions.start_solo_combat(actor, P8_ID, p8.state_version)
    assert p8 is not None and p8.kind == "retry"
    assert p8.progress["awaiting_retry"] is True
    assert p8.progress.get("activity_id") is None
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character is not None and character.hp == character.max_hp
        assert await session.scalar(
            select(GameActivity.status).where(
                GameActivity.character_id == character_id,
                GameActivity.content_id == MISSION_CONTENT_IDS[P8_ID],
            )
        ) == "failed"
        assert await session.scalar(
            select(func.count(GameActivity.id)).where(
                GameActivity.character_id == character_id,
                GameActivity.status == "active",
            )
        ) == 0
        assert await session.scalar(
            select(func.count(RewardEvent.id)).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P8_REWARD_SOURCE,
            )
        ) == 0

    retried = await missions.start_solo_combat(actor, P8_ID, p8.state_version)
    assert retried is not None and retried.kind == "combat"
    assert retried.activity_id is not None and retried.combat is not None


@pytest.mark.asyncio
async def test_s7_and_p8_solo_flow_routes_codex_rewards_and_idempotence(database, monkeypatch):
    import asterion.application.scripted_combat as scripted_combat

    actor = 999733
    character_id, sessions = await _seed_vde_ready(database, actor)
    missions = VDEMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")

    assert await missions.region_access(actor)
    local = await road.resume(actor)
    assert local is not None and local.location == VDE_VIGILIA
    to_garganta = await road.travel_route(actor, VDE_GARGANTA)
    assert to_garganta is not None and to_garganta.location == VDE_GARGANTA

    offer = await missions.resume(actor, S7_ID)
    assert offer is not None and offer.available and offer.kind == "offer"
    s7 = await missions.start(actor, S7_ID)
    assert s7 is not None and s7.status == "active" and s7.step == 1
    for point in ("a", "b", "c"):
        s7 = await missions.examine(actor, S7_ID, s7.state_version, point)
    assert s7 is not None and s7.step == 2
    combat = await missions.start_solo_combat(actor, S7_ID, s7.state_version)
    assert combat is not None and combat.kind == "combat" and combat.activity_id is not None
    resumed = await missions.resume_active(actor)
    assert resumed is not None and resumed.activity_id == combat.activity_id

    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    s7 = await missions.action_combat(actor, combat.activity_id, combat.combat.version, "attack")
    assert s7 is not None and s7.step == 3 and s7.kind == "rope"
    s7 = await missions.advance(actor, S7_ID, s7.state_version, "rope")
    assert s7 is not None and s7.step == 4 and s7.kind == "report"
    blocked_report = await missions.advance(actor, S7_ID, s7.state_version, "report")
    assert blocked_report is not None and blocked_report.status == "active"
    assert blocked_report.step == 4
    to_vigilia = await road.travel_route(actor, VDE_VIGILIA)
    assert to_vigilia is not None and to_vigilia.location == VDE_VIGILIA
    s7 = await missions.advance(actor, S7_ID, blocked_report.state_version, "report")
    assert s7 is not None and s7.status == "completed"
    await missions.advance(actor, S7_ID, s7.state_version, "report")

    async with sessions() as session:
        s7_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S7_REWARD_SOURCE,
            )
        )
        assert s7_event is not None
        s7_components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == s7_event.id)
                )
            ).all()
        )
        assert {(item.kind, item.quantity) for item in s7_components} == {
            ("xp", 3840),
            ("crowns", 140),
        }
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == S7_REWARD_SOURCE,
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(CodexFragment.id).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id == "codex.fragment.vales.routes.s7_marker_shift",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == "vde_scripted_fauna",
                )
            )
            is None
        )

    p8 = await missions.start(actor, P8_ID)
    assert p8 is not None and p8.status == "active" and p8.kind == "enter_mata"
    route_view = await road.resume(actor)
    assert route_view is not None and VDE_MATA in route_view.route_destinations
    to_mata = await road.travel_route(actor, VDE_MATA)
    assert to_mata is not None and to_mata.location == VDE_MATA
    p8 = await missions.enter_mata(actor, p8.state_version)
    assert p8 is not None and p8.step == 2
    await missions.enter_mata(actor, p8.state_version)
    for point in ("a", "b", "c"):
        p8 = await missions.examine(actor, P8_ID, p8.state_version, point)
    assert p8 is not None and p8.step == 3
    combat = await missions.start_solo_combat(actor, P8_ID, p8.state_version)
    assert combat is not None and combat.activity_id is not None
    resumed = await missions.resume_active(actor)
    assert resumed is not None and resumed.activity_id == combat.activity_id
    p8 = await missions.action_combat(actor, combat.activity_id, combat.combat.version, "attack")
    assert p8 is not None and p8.step == 4 and p8.kind == "compare"
    for action in ("compare", "masonry", "record"):
        p8 = await missions.advance(actor, P8_ID, p8.state_version, action)
    assert p8 is not None and p8.step == 7 and p8.kind == "return_vigilia"
    async with sessions() as session:
        mata_discovery = await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "vde.location.mata_suspensa",
            )
        )
        assert mata_discovery is not None
        for entry_id in (
            "codex.location.mata_suspensa",
            "codex.mystery.raizes_que_seguem_pedra",
        ):
            assert (
                await session.scalar(
                    select(CodexEntry.id).where(
                        CodexEntry.character_id == character_id,
                        CodexEntry.entry_id == entry_id,
                    )
                )
                is not None
            )

    back = await road.travel_route(actor, VDE_VIGILIA)
    assert back is not None and back.location == VDE_VIGILIA
    p8 = await missions.return_vigilia(actor, p8.state_version)
    assert p8 is not None and p8.status == "completed"
    await missions.return_vigilia(actor, p8.state_version)

    async with sessions() as session:
        p8_event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == P8_REWARD_SOURCE,
            )
        )
        assert p8_event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == p8_event.id)
                )
            ).all()
        )
        assert {(item.kind, item.item_id, item.quantity) for item in components} == {
            ("xp", None, 10500),
            ("crowns", None, 300),
            ("material", "material.vde.ferro_enredado", 1),
            ("material", "material.vde.erva_de_turfa", 2),
            ("material", "material.vde.resina_enredada", 1),
        }
        assert (
            await session.scalar(
                select(func.count(RewardEvent.id)).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == P8_REWARD_SOURCE,
                )
            )
            == 1
        )
        stacks = list(
            (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character_id,
                        MaterialStack.material_id.in_(
                            (
                                "material.vde.ferro_enredado",
                                "material.vde.erva_de_turfa",
                                "material.vde.resina_enredada",
                            )
                        ),
                    )
                )
            ).all()
        )
        assert (
            sum(
                stack.quantity
                for stack in stacks
                if stack.material_id == "material.vde.ferro_enredado"
            )
            == 1
        )
        assert (
            sum(
                stack.quantity
                for stack in stacks
                if stack.material_id == "material.vde.erva_de_turfa"
            )
            == 2
        )
        assert (
            sum(
                stack.quantity
                for stack in stacks
                if stack.material_id == "material.vde.resina_enredada"
            )
            == 1
        )
        assert all(stack.bound for stack in stacks)
        assert (
            await session.scalar(
                select(func.count(CodexFragment.id)).where(
                    CodexFragment.character_id == character_id,
                    CodexFragment.fragment_id.in_(
                        (
                            "codex.fragment.mata.entrada_registrada",
                            "codex.fragment.mata.raizes_sob_a_pedra",
                        )
                    ),
                )
            )
            == 2
        )
        assert (
            await session.scalar(
                select(func.count(CampaignObjectiveCredit.id)).where(
                    CampaignObjectiveCredit.character_id == character_id,
                    CampaignObjectiveCredit.quest_id == P8_ID,
                    CampaignObjectiveCredit.objective_id == "p8.record_find",
                )
            )
            == 1
        )


@pytest.mark.asyncio
async def test_s7_group_member_examines_alone_and_reconnects_to_own_solo_encounter(database):
    leader = 999734
    helper = 999735
    leader_id, sessions = await _seed_vde_ready(database, leader)
    helper_id, _ = await _seed_vde_ready(database, helper)
    async with sessions.begin() as session:
        for character_id in (leader_id, helper_id):
            world = await session.get(WorldState, character_id)
            assert world is not None
            world.location = VDE_GARGANTA
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader,
        helper_name,
        expected_group_revision=group.revision,
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    leader_view = await missions.start(leader, S7_ID)
    helper_view = await missions.start(helper, S7_ID)
    assert leader_view is not None and leader_view.status == "active"
    assert helper_view is not None and helper_view.status == "active"

    # Objectives are Solo (Ação × Consequência §5): only the leader advances.
    for point in ("a", "b", "c"):
        leader_view = await missions.examine(leader, S7_ID, leader_view.state_version, point)
    assert leader_view is not None and leader_view.step == 2
    async with sessions() as session:
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == S7_ID)
        )
        assert helper_quest is not None
        assert helper_quest.step == 1
        assert not (helper_quest.progress or {}).get("markers")
        assert (
            await session.scalar(
                select(func.count(CampaignObjectiveCredit.id)).where(
                    CampaignObjectiveCredit.character_id == helper_id,
                    CampaignObjectiveCredit.quest_id == S7_ID,
                    CampaignObjectiveCredit.objective_id.like("s7.markers.%"),
                )
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count(CampaignObjectiveCredit.id)).where(
                    CampaignObjectiveCredit.character_id == leader_id,
                    CampaignObjectiveCredit.quest_id == S7_ID,
                    CampaignObjectiveCredit.objective_id.like("s7.markers.%"),
                )
            )
            == 3
        )

    # S7 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await missions.propose_group_combat(leader, S7_ID, leader_view.state_version)
    assert not await groups.activity_proposals(leader)
    assert not await groups.activity_proposals(helper)

    started = await missions.start_solo_combat(leader, S7_ID, leader_view.state_version)
    assert started is not None and started.activity_id is not None
    assert started.group_size == 1
    resumed = await missions.resume_active(leader)
    assert resumed is not None
    assert resumed.activity_id == started.activity_id
    assert resumed.encounter_id == started.encounter_id
    helper_active = await missions.resume_active(helper)
    assert helper_active is not None and helper_active.step == 1
    assert helper_active.activity_id is None


@pytest.mark.asyncio
async def test_p8_group_member_enters_mata_alone_and_reconnects_to_own_solo_encounter(database):
    leader = 999736
    helper = 999737
    leader_id, sessions = await _seed_vde_ready(database, leader, level=13)
    helper_id, _ = await _seed_vde_ready(database, helper, level=13)

    async with sessions() as session:
        helper_character = await session.get(Character, helper_id)
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader,
        helper_name,
        expected_group_revision=group.revision,
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    missions = VDEMissionService(sessions, "ocaso", groups)
    road = RoadService(sessions, "ocaso")

    leader_view = await missions.start(leader, P8_ID)
    helper_view = await missions.start(helper, P8_ID)
    assert leader_view is not None and leader_view.status == "active"
    assert helper_view is not None and helper_view.status == "active"
    assert await road.travel_route(leader, VDE_MATA) is not None
    assert await road.travel_route(helper, VDE_MATA) is not None

    leader_view = await missions.enter_mata(leader, leader_view.state_version)
    assert leader_view is not None and leader_view.step == 2
    for point in ("a", "b", "c"):
        leader_view = await missions.examine(
            leader, P8_ID, leader_view.state_version, point
        )
    assert leader_view is not None and leader_view.step == 3

    # Objectives are Solo (Ação × Consequência §5): only the leader advances.
    async with sessions() as session:
        helper_quest = await session.scalar(
            select(Quest).where(Quest.character_id == helper_id, Quest.quest_id == P8_ID)
        )
        assert helper_quest is not None
        assert helper_quest.step == 1
        assert not (helper_quest.progress or {}).get("roots")
        for character_id, expected in ((leader_id, 3), (helper_id, 0)):
            assert (
                await session.scalar(
                    select(func.count(CampaignObjectiveCredit.id)).where(
                        CampaignObjectiveCredit.character_id == character_id,
                        CampaignObjectiveCredit.quest_id == P8_ID,
                        CampaignObjectiveCredit.objective_id.like("p8.roots.%"),
                    )
                )
                == expected
            )

    # P8 is not a Boss: the Group proposal is refused and nothing is reserved.
    with pytest.raises(GroupError, match="mission_coop_boss_only"):
        await missions.propose_group_combat(leader, P8_ID, leader_view.state_version)
    assert not await groups.activity_proposals(leader)
    assert not await groups.activity_proposals(helper)

    started = await missions.start_solo_combat(leader, P8_ID, leader_view.state_version)
    assert started is not None and started.group_size == 1
    resumed = await missions.resume_active(leader)
    assert resumed is not None
    assert resumed.activity_id == started.activity_id
    assert resumed.encounter_id == started.encounter_id
    helper_active = await missions.resume_active(helper)
    assert helper_active is not None and helper_active.step == 1
    assert helper_active.activity_id is None

    async with sessions() as session:
        assert (
            await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == leader_id,
                    LocationDiscovery.location_id == "vde.location.mata_suspensa",
                )
            )
            is not None
        )
        assert (
            await session.scalar(
                select(LocationDiscovery.id).where(
                    LocationDiscovery.character_id == helper_id,
                    LocationDiscovery.location_id == "vde.location.mata_suspensa",
                )
            )
            is None
        )
