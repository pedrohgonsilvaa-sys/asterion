import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from asterion.application.active_arts import ActiveArtService
from asterion.application.creation import CreationService
from asterion.application.p1 import P1Service
from asterion.application.p2 import ASH_POINT_IDS, P2Service
from asterion.application.prologue import PrologueService
from asterion.application.road import REFUGE, ROAD, RoadService
from asterion.application.round import RoundService
from asterion.application.s1 import S1Service
from asterion.application.world import WorldService
from asterion.domain.arts import FIRST_CLASS_ART_IDS
from asterion.domain.prologue import PROFILE as PROLOGUE_PROFILE
from asterion.infrastructure.db.models import (
    Character,
    GameActivity,
    Quest,
    RewardEvent,
    WorldState,
)
from tests.helpers.tdo_playthrough import TDOPlaythrough

pytestmark = pytest.mark.skipif(
    os.getenv("ASTERION_RUN_TDO_FULL_PLAYTHROUGH") != "1",
    reason="playthrough diagnóstico longo; habilite ASTERION_RUN_TDO_FULL_PLAYTHROUGH=1",
)


async def _create_remanescente_sentinela(driver: TDOPlaythrough) -> None:
    creation = CreationService(driver.sessions, "ocaso")
    state = await creation.start(driver.actor)
    state = await creation.name(driver.actor, "Bravaro", update_id=1)
    for action in ("r0", "choose", "c0", "choose"):
        state = await creation.callback(driver.actor, state.id, state.version, action)
    assert state.step == "confirm"
    state = await creation.callback(driver.actor, state.id, state.version, "confirm")
    assert (state.step, state.name, state.race, state.character_class) == (
        "cinzas_na_estrada:intro",
        "Bravaro",
        "remanescente",
        "sentinela",
    )


@pytest.mark.asyncio
async def test_tdo_full_playthrough_stops_at_first_blocker(database, monkeypatch):
    """Begin a real Nv.1 journey; every progression mutation uses a public service."""
    actor = 7_000_000_000_000 + uuid4().int % 100_000_000_000
    _, sessions = database
    driver = TDOPlaythrough(actor, sessions)
    await _create_remanescente_sentinela(driver)
    await driver.snapshot("personagem criado pelo fluxo público")

    prologue = PrologueService(sessions, "ocaso", PROLOGUE_PROFILE)
    view = await prologue.enter(actor)
    assert view is not None and view.stage == "cinzas_na_estrada:first_combat"
    for expected_action in ("attack", "defend", "art"):
        view = await prologue.action(actor, view.activity_id, view.combat.version, expected_action)
        resumed = await PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).resume(actor)
        assert resumed == view
    assert view.combat.tutorial_stage == "normal"
    view = await driver.combat_to_result(
        view,
        lambda current, action: PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: PrologueService(sessions, "ocaso", PROLOGUE_PROFILE).resume(actor),
        label="Prólogo · Cão Cinéreo",
    )
    assert view.combat.result in {"victory", "defeat"}
    await driver.snapshot(f"Prólogo · {view.combat.result}")

    world = WorldService(sessions, "ocaso")
    at_brazier = await world.resume(actor)
    assert at_brazier is not None and at_brazier.kind == "brazier"
    rested = await world.rest(actor)
    assert rested is not None and rested.kind == "menu"
    p1 = P1Service(sessions, "ocaso")
    quest = await p1.resume(actor)
    assert quest is not None and quest.status == "active" and quest.step == 1

    quest = await p1.follow_road(actor, quest.state_version)
    quest = await p1.examine(actor, "pegadas", quest.state_version)
    quest = await p1.examine(actor, "sulcos", quest.state_version)
    assert quest is not None and quest.step == 3 and quest.combat is not None
    quest = await driver.combat_to_result(
        quest,
        lambda current, action: p1.action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: p1.resume(actor),
        label="P1 · encontro da Estrada",
    )
    for _ in range(4):
        if quest.progress.get("arrival"):
            break
        quest = await p1.retry(actor, quest.state_version)
        quest = await driver.combat_to_result(
            quest,
            lambda current, action: p1.action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: p1.resume(actor),
            label="P1 · retry",
        )
    assert quest.progress.get("arrival"), driver.diagnostic()
    for mutation in (p1.enter_refuge, p1.follow_alda, p1.go_brazier, p1.activate_brazier):
        quest = await mutation(actor, quest.state_version)
    assert quest.status == "completed"
    await driver.snapshot("P1 concluída e Braseiro do Refúgio ativado")

    active_arts = ActiveArtService(sessions, "ocaso")
    art_view = await active_arts.view(actor)
    assert art_view is not None
    equipped = await active_arts.equip_art(
        actor,
        1,
        FIRST_CLASS_ART_IDS["sentinela"],
        expected_configuration_version=art_view.combat_configuration_version,
    )
    assert equipped is not None and equipped.changed

    road = RoadService(sessions, "ocaso")
    location = await road.travel(actor, ROAD)
    assert location is not None and location.location == ROAD
    hunt = None
    for attempt in range(12):
        hunt = await road.start_hunt(actor)
        assert hunt is not None and hunt.kind == "combat", driver.diagnostic()
        hunt = await driver.combat_to_result(
            hunt,
            lambda current, action: road.action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: RoadService(sessions, "ocaso").resume(actor),
            label=f"Caçada Manual · tentativa {attempt + 1}",
        )
        if hunt.kind == "hunt_victory":
            await road.acknowledge_result(actor)
            break
        assert hunt.kind == "hunt_defeat", hunt
        await road.acknowledge_defeat(actor)
        await driver.snapshot(f"Caçada Manual · tentativa {attempt + 1} · derrota")
    assert hunt is not None and hunt.kind == "hunt_victory", driver.diagnostic()
    await driver.snapshot("primeira vitória de Caçada Manual")
    await road.travel(actor, REFUGE)
    await WorldService(sessions, "ocaso").rest(actor)
    await road.travel(actor, ROAD)

    # The timed Ronda is exercised with a test-only clock; game state still
    # advances exclusively through RoundService's public maintenance operation.
    import asterion.application.round as round_module

    class JourneyClock(datetime):
        instant = datetime.now(UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)

    monkeypatch.setattr(round_module, "datetime", JourneyClock)
    rounds = RoundService(sessions, "ocaso")
    prepared = await rounds.prepare_round(actor, 5)
    assert prepared is not None and prepared.kind == "round_prepare", (
        f"preparação da Ronda bloqueada: {prepared!r}; "
        "resultados não reconhecidos="
        f"{driver.marks[-1].state.get('unacknowledged_hunt_results')!r}; "
        f"histórico de Caçadas={driver.marks[-1].state.get('hunt_results')!r}; "
        f"{driver.diagnostic()}"
    )
    started = await rounds.start_round(actor, prepared.round_id, prepared.state_version)
    assert started is not None and started.kind in {"round_active", "round_interrupted"}
    resumed_round = await RoundService(sessions, "ocaso").resume(actor)
    assert resumed_round is not None and resumed_round.round_id == started.round_id
    blocked_hunt = await rounds.start_hunt(actor)
    assert blocked_hunt is not None and blocked_hunt.kind.startswith("round_")
    if started.kind == "round_active":
        cancel = await rounds.cancel_round(actor, started.round_id, started.state_version)
        assert cancel is not None and cancel.cancel_requested
        JourneyClock.instant += timedelta(minutes=3)
        assert await rounds.advance_due_rounds() == 1
        round_result = await rounds.resume(actor)
        assert round_result is not None and round_result.kind == "round_cancelled"
        await rounds.round_back(actor, started.round_id)
    else:
        elite = await rounds.engage_round_elite(actor, started.round_id, started.state_version)
        assert elite is not None and elite.combat is not None
        elite = await driver.combat_to_result(
            elite,
            lambda current, action: RoadService(sessions, "ocaso").action(
                actor, current.activity_id, current.combat.version, action
            ),
            lambda: RoundService(sessions, "ocaso").resume(actor),
            label="Ronda · Elite interrompida",
        )
        await RoundService(sessions, "ocaso").acknowledge_result(actor)
    await driver.snapshot("Ronda real encerrada sem mutação direta do estado")

    # S1 is a normal secondary quest, available once the character reaches Nv.2.
    async def manual_hunt(label):
        service = RoadService(sessions, "ocaso")
        for _receipt in range(6):
            view = await service.start_hunt(actor)
            if view is not None and view.kind == "hunt_defeat":
                await service.acknowledge_defeat(actor)
                await driver.snapshot(f"{label} · recibo de derrota reconhecido")
                continue
            if view is not None and view.kind == "hunt_victory":
                await service.acknowledge_result(actor)
                await driver.snapshot(f"{label} · recibo de vitória reconhecido")
                continue
            assert view is not None and view.kind == "combat", (view, driver.diagnostic())
            view = await driver.combat_to_result(
                view,
                lambda current, action: RoadService(sessions, "ocaso").action(
                    actor, current.activity_id, current.combat.version, action
                ),
                lambda: RoadService(sessions, "ocaso").resume(actor),
                label=label,
            )
            if view.kind == "hunt_victory":
                await service.acknowledge_result(actor)
            else:
                assert view.kind == "hunt_defeat", view
                await service.acknowledge_defeat(actor)
            await driver.snapshot(f"{label} · {view.kind}")
            return view
        blocked = await driver.snapshot(f"primeiro bloqueio persistido · {label}")
        raise AssertionError(
            f"{label}: recibo antigo continua bloqueando uma nova Caçada após seis confirmações. "
            f"Último estado persistido={blocked.state!r}\n{driver.diagnostic()}"
        )

    async def current_level():
        async with sessions() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            return character.level

    await road.travel(actor, REFUGE)
    for attempt in range(40):
        offer = await S1Service(sessions, "ocaso").offer(actor)
        if offer is not None and offer.kind == "offer":
            break
        assert await current_level() < 2 or offer is not None, driver.diagnostic()
        if await current_level() < 2:
            await road.travel(actor, ROAD)
            await manual_hunt(f"Nv.2 · Caçada {attempt + 1}")
            await road.travel(actor, REFUGE)
    s1 = S1Service(sessions, "ocaso")
    accepted_s1 = await s1.accept(actor)
    assert accepted_s1 is not None and accepted_s1.status == "active", accepted_s1
    await road.travel(actor, ROAD)
    for point in (3, 1, 2):
        accepted_s1 = await s1.investigate_point(actor, point, accepted_s1.state_version)
    accepted_s1 = await s1.examine_ashes(actor, accepted_s1.state_version)
    accepted_s1 = await s1.observe_light(actor, accepted_s1.state_version)
    assert accepted_s1.step == 4
    await road.travel(actor, REFUGE)
    completed_s1 = await s1.complete_with_oren(actor, accepted_s1.state_version)
    assert completed_s1 is not None and completed_s1.status == "completed"
    await driver.snapshot("S1 concluída por Oren")

    p2 = P2Service(sessions, "ocaso")
    for attempt in range(50):
        offer = await p2.alda(actor)
        if offer is not None and offer.available:
            break
        assert await current_level() < 3, (offer, driver.diagnostic())
        await road.travel(actor, ROAD)
        await manual_hunt(f"Nv.3 · Caçada {attempt + 1}")
        await road.travel(actor, REFUGE)
    active_p2 = await p2.accept(actor, offer.state_version)
    assert active_p2 is not None and active_p2.status == "active", active_p2
    active_p2 = await p2.travel_to_charneca(actor, active_p2.state_version)
    assert active_p2.step == 2 and active_p2.location == "Charneca da Fuligem"
    for point in ASH_POINT_IDS:
        active_p2 = await p2.examine_ash_point(actor, point, active_p2.state_version)
    assert active_p2.step == 3 and active_p2.combat is not None
    active_p2 = await driver.combat_to_result(
        active_p2,
        lambda current, action: p2.action(
            actor, current.activity_id, current.activity_state_version, action
        ),
        lambda: P2Service(sessions, "ocaso").resume(actor),
        label="P2 · Aranha da Fuligem",
    )
    assert active_p2.progress.get("combat_result") == "victory", driver.diagnostic()
    active_p2 = await p2.examine_pedra_marcada(actor, active_p2.state_version)
    active_p2 = await p2.return_to_refuge(actor, active_p2.state_version)
    active_p2 = await p2.oren(actor, active_p2.state_version)
    active_p2 = await p2.report_to_alda(actor, active_p2.state_version)
    assert active_p2.status == "completed"
    await driver.snapshot("P2 concluída")

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.level >= 3
        assert character.xp >= 2720
        assert character.crowns >= 120
        assert character.vigor >= 0
        assert character.hp >= 0
        p1_row = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P1")
        )
        assert p1_row is not None and p1_row.status == "completed"
        assert await session.scalar(
            select(func.count()).select_from(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == "p1.vozes_na_estrada",
            )
        ) == 1
        assert await session.scalar(
            select(func.count()).select_from(GameActivity).where(
                GameActivity.character_id == character.id,
                GameActivity.status == "active",
            )
        ) == 0
        p2_row = await session.scalar(
            select(Quest).where(Quest.character_id == character.id, Quest.quest_id == "P2")
        )
        assert p2_row is not None and p2_row.status == "completed"
        world_row = await session.get(WorldState, character.id)
        assert world_row is not None and world_row.location == REFUGE

    await driver.snapshot("fim da primeira perna · P2 concluída")
