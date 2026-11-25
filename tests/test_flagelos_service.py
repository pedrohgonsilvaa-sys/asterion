"""O Despertar dos Flagelos sobre PostgreSQL real: barras, spawn, combate, morte e prêmio."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.flagelo_contributions import record_contribution
from asterion.application.flagelos import FlageloError, FlageloService
from asterion.application.world_event_veu import RoundInputs
from asterion.domain import flagelos as fl
from asterion.domain import veu_combat as vc
from asterion.infrastructure.db.models import (
    Account,
    BestiaryEntry,
    Character,
    CodexEntry,
    EquipmentItem,
    FlageloContribution,
    FlageloEvent,
    FlageloParticipant,
    FlageloRegionProgress,
    FlageloRewardSettlement,
    FlageloRound,
    MaterialStack,
    OutboxMessage,
    Quest,
    WorldState,
)

SERVER = "ocaso"
T0 = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)


class FakeSimulator:
    """Dano fixo por ataque; Defender passa pelo lote real (prevenção medida lá)."""

    def __init__(self, damage: int = 100, player_hp: int = 10_000):
        self.damage = damage
        self.player_hp = player_hp

    def __call__(self, level, boss):
        return self

    async def prepare(self, session, participants, actions, enemies, combat_key):
        players = {}
        for p in participants:
            unit = vc.PlayerUnit(
                p.character_id,
                Decimal(p.hp if p.hp is not None else self.player_hp),
                Decimal(self.player_hp),
                Decimal(50),
            )
            unit.load_state(p.combat_state or {})
            players[p.character_id] = unit
        code = next(iter(enemies))
        intents = []
        for action in actions:
            if action.action_type == "defend":
                intents.append(vc.PlayerIntent(action.character_id, "defend", None, 0))
            elif action.action_type == "art":
                support = (
                    vc.SupportResult(action.character_id, action.character_id, "heal", 10**6),
                )
                intents.append(vc.PlayerIntent(action.character_id, "art", None, 0, support, True))
            else:
                intents.append(vc.PlayerIntent(action.character_id, "attack", code, self.damage))
        return RoundInputs(intents, players)


def _name(index: int, base: int) -> str:
    letters = "abcdefghijklmnopqrstuvwxyz"
    return "Fla" + letters[base // 1000 % 26] + letters[index // 26 % 26] + letters[index % 26]


async def _characters(database, count: int, base: int = 880000, region="Terras do Ocaso"):
    async with database[1].begin() as session:
        for index in range(count):
            session.add(Account(telegram_id=base + index))
            session.add(
                Character(
                    telegram_id=base + index,
                    server_id=SERVER,
                    name=_name(index, base),
                    race="remanescente",
                    character_class="sentinela",
                    stage="menu",
                    ruleset_version="tdo-1.0.15",
                    level=10,
                    hp=Decimal("500"),
                    max_hp=Decimal("500"),
                    vigor=100,
                    max_vigor=100,
                )
            )
        await session.flush()
        rows = (
            await session.scalars(
                select(Character)
                .where(Character.telegram_id >= base, Character.telegram_id < base + count)
                .order_by(Character.telegram_id)
            )
        ).all()
        for row in rows:
            session.add(WorldState(character_id=row.id, region=region, location="x"))
        return [(row.telegram_id, row.id) for row in rows]


async def _fill(database, service, region_id: str, points: int = fl.THRESHOLD, prefix="seed"):
    """Contribuições pendentes até ``points`` (Masmorra = 6, o resto em Caçadas)."""
    async with database[1].begin() as session:
        character = (await session.scalars(select(Character).limit(1))).first()
        for index in range(points):
            await record_contribution(
                session, character, "hunt", f"{prefix}:{region_id}:{index}", region_id=region_id
            )


async def _bar(database, region_id: str) -> FlageloRegionProgress:
    async with database[1]() as session:
        return await session.get(FlageloRegionProgress, (SERVER, region_id))


async def _active(database) -> FlageloEvent | None:
    async with database[1]() as session:
        return await session.scalar(
            select(FlageloEvent).where(
                FlageloEvent.server_id == SERVER, FlageloEvent.status == "active"
            )
        )


@pytest.fixture
def service(database) -> FlageloService:
    return FlageloService(database[1], SERVER, FakeSimulator())


# ------------------------------------------------------------------ contribuição e spawn


async def test_activity_contributes_once_and_bar_increments(service, database):
    ((_, character_id),) = await _characters(database, 1)
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        assert await record_contribution(session, character, "dungeon", "dungeon:run1")
        assert not await record_contribution(session, character, "dungeon", "dungeon:run1")
        assert await record_contribution(session, character, "contract", "contract:c1")
        assert not await record_contribution(session, character, "ronda", "ronda:1")
    await service.apply_contributions(now=T0)
    await service.apply_contributions(now=T0)
    assert (await _bar(database, "tdo")).current_points == 8


async def test_concurrent_duplicate_callbacks_count_once(service, database):
    ((_, character_id),) = await _characters(database, 1)

    async def callback():
        async with database[1].begin() as session:
            character = await session.get(Character, character_id)
            await record_contribution(session, character, "hunt", "activity:same")

    await asyncio.gather(*(callback() for _ in range(5)))
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(FlageloContribution)) == 1


async def test_500_spawns_exactly_one_flagelo_and_freezes_the_bar(service, database):
    await _characters(database, 1)
    await _fill(database, service, "vde", 499)
    await service.apply_contributions(now=T0)
    assert await _active(database) is None
    await _fill(database, service, "vde", 3, prefix="more")
    _, spawned = await service.apply_contributions(now=T0)
    assert len(spawned) == 1
    event = await _active(database)
    assert (event.region_id, event.flagelo_id, event.hp_current, event.attack) == (
        "vde",
        "nharvek",
        51_000,
        195,
    )
    bar = await _bar(database, "vde")
    assert (bar.current_points, bar.active_flagelo_id) == (500, event.id)
    await _fill(database, service, "vde", 4, prefix="frozen")
    await service.apply_contributions(now=T0)
    assert (await _bar(database, "vde")).current_points == 500
    async with database[1]() as session:
        counted = await session.scalars(
            select(FlageloContribution.counted_points).where(
                FlageloContribution.activity_id.like("frozen:%")
            )
        )
        assert set(counted.all()) == {0}
        notices = await session.scalars(
            select(OutboxMessage.dedup_key).where(OutboxMessage.topic == "flagelo.community_notice")
        )
        assert notices.all() == [f"flagelo:spawn:{event.id}"]


async def test_two_regions_at_500_and_two_appliers_create_one_flagelo(service, database):
    await _characters(database, 1)
    await _fill(database, service, "tdo")
    await _fill(database, service, "altos")
    other = FlageloService(database[1], SERVER, FakeSimulator())
    results = await asyncio.gather(
        service.apply_contributions(now=T0), other.apply_contributions(now=T0)
    )
    assert sum(len(spawned) for _, spawned in results) == 1
    async with database[1]() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(FlageloEvent)
                .where(FlageloEvent.status == "active")
            )
            == 1
        )
    waiting = await _bar(database, "altos")
    assert (waiting.current_points, waiting.active_flagelo_id) == (500, None)


# ------------------------------------------------------------------ combate


async def _spawn(database, service, region_id="tdo"):
    await _fill(database, service, region_id)
    await service.apply_contributions(now=T0)
    return await _active(database)


async def _round(service, actors, now, action="attack"):
    round_ = await service.open_round(now=now)
    assert round_ is not None
    for actor in actors:
        slot = 1 if action == "art" else None
        await service.register_action(actor, round_.round_number, action, art_slot=slot, now=now)
    deadline = now + fl.DECISION_WINDOW
    assert await service.resolve_round(round_.id, now=deadline)
    return deadline


async def test_enter_leave_reentry_and_capacity(service, database):
    players = await _characters(database, 2)
    event = await _spawn(database, service)
    (actor, _), (other, _) = players
    await service.enter(actor, now=T0)
    await service.leave(actor, now=T0 + timedelta(seconds=5))
    with pytest.raises(FlageloError) as wait:
        await service.enter(actor, now=T0 + timedelta(seconds=60))
    assert wait.value.code == "reentry_wait"
    await service.enter(actor, now=T0 + timedelta(minutes=2, seconds=5))
    async with database[1].begin() as session:
        fillers = await _characters(database, fl.PARTICIPANT_CAP - 1, base=990000)
        for _, character_id in fillers:
            session.add(
                FlageloParticipant(
                    flagelo_id=event.id,
                    character_id=character_id,
                    joined_at=T0,
                    in_combat=True,
                    acts_from_round=1,
                    idle_rounds=0,
                    effective_damage=0,
                    effective_healing=0,
                    barrier_absorbed=0,
                    defender_prevented_damage=0,
                    meaningful_effects=0,
                    participation_points=0,
                )
            )
    with pytest.raises(FlageloError) as full:
        await service.enter(other, now=T0 + timedelta(minutes=3))
    assert full.value.code == "full"


async def test_round_damage_is_shared_and_resolves_once(service, database):
    players = await _characters(database, 3)
    event = await _spawn(database, service)
    for actor, _ in players:
        await service.enter(actor, now=T0)
    round_ = await service.open_round(now=T0)
    assert await service.open_round(now=T0) is None  # uma rodada aberta por vez
    for actor, _ in players:
        assert await service.register_action(actor, round_.round_number, "attack", now=T0)
        assert not await service.register_action(actor, round_.round_number, "attack", now=T0)
    with pytest.raises(FlageloError):
        await service.resolve_round(round_.id, now=T0 + timedelta(seconds=5))
    late = T0 + timedelta(seconds=11)
    with pytest.raises(FlageloError) as closed:
        await service.register_action(players[0][0], round_.round_number, "defend", now=late)
    assert closed.value.code == "window_closed"
    results = await asyncio.gather(
        service.resolve_round(round_.id, now=late), service.resolve_round(round_.id, now=late)
    )
    assert sorted(results) == [False, True]
    current = await _active(database)
    assert current.hp_current == event.hp_current - 300
    async with database[1]() as session:
        rows = (await session.scalars(select(FlageloParticipant))).all()
        assert {row.effective_damage for row in rows} == {100}
        assert {row.participation_points for row in rows} == {1}
        observed = await session.scalar(
            select(func.count())
            .select_from(BestiaryEntry)
            .where(BestiaryEntry.creature_id == "bestiary.flagelo.varkhenn")
        )
        assert observed == 3


async def test_player_entering_at_window_close_acts_next_round(service, database):
    (first, _), (late, _) = await _characters(database, 2)
    await _spawn(database, service)
    await service.enter(first, now=T0)
    round_ = await service.open_round(now=T0)
    await service.enter(late, now=T0 + timedelta(seconds=10))
    with pytest.raises(FlageloError) as waiting:
        await service.register_action(late, round_.round_number, "attack", now=T0)
    assert waiting.value.code == "waiting_next_round"


async def test_defender_counts_only_real_prevention(service, database):
    (hit, hit_id), (spared, spared_id) = await _characters(database, 2)
    await _spawn(database, service)
    await service.enter(hit, now=T0)
    await service.enter(spared, now=T0)
    round_ = await service.open_round(now=T0)
    async with database[1].begin() as session:
        row = await session.get(FlageloRound, round_.id)
        row.decision = {"action_key": "golpe_de_cinza", "targets": [str(hit_id)], "seed": 0}
    for actor in (hit, spared):
        await service.register_action(actor, round_.round_number, "defend", now=T0)
    await service.resolve_round(round_.id, now=T0 + fl.DECISION_WINDOW)
    async with database[1]() as session:
        rows = {
            row.character_id: row for row in (await session.scalars(select(FlageloParticipant)))
        }
    assert rows[hit_id].defender_prevented_damage > 0
    assert rows[hit_id].participation_points == 1
    # Defender sem ser atingido não preveniu nada: 0 pontos.
    assert rows[spared_id].defender_prevented_damage == 0
    assert rows[spared_id].participation_points == 0


async def test_three_idle_rounds_remove_the_combatant(service, database):
    ((actor, _),) = await _characters(database, 1)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    now = T0
    for _ in range(3):
        round_ = await service.open_round(now=now)
        now += fl.DECISION_WINDOW
        await service.resolve_round(round_.id, now=now)
    async with database[1]() as session:
        participant = (await session.scalars(select(FlageloParticipant))).one()
        assert not participant.in_combat
        assert participant.reentry_available_at == now + fl.REENTRY_DELAY


# ------------------------------------------------------------------ escalonamento


async def test_scaling_runs_only_without_combatants_and_never_heals(service, database):
    ((actor, _),) = await _characters(database, 1)
    event = await _spawn(database, service)
    async with database[1].begin() as session:
        row = await session.get(FlageloEvent, event.id)
        row.hp_current = 30_000
    assert await service.apply_scaling(now=T0 + timedelta(minutes=14)) == 0
    assert await service.apply_scaling(now=T0 + timedelta(minutes=15)) == 1
    scaled = await _active(database)
    assert (scaled.max_hp, scaled.attack, scaled.hp_current) == (37_865, 142, 30_000)
    await service.enter(actor, now=T0 + timedelta(minutes=16))
    assert await service.apply_scaling(now=T0 + timedelta(hours=3)) == 0
    await service.leave(actor, now=T0 + timedelta(hours=3))
    # Ausência nova recomeça a contar do zero; o passo já aplicado não volta.
    assert await service.apply_scaling(now=T0 + timedelta(hours=3, minutes=14)) == 0
    assert await service.apply_scaling(now=T0 + timedelta(hours=8)) == 9
    capped = await _active(database)
    assert (capped.abandonment_steps, capped.max_hp, capped.attack) == (10, 63_108, 179)
    assert (capped.base_def, capped.base_agi, capped.hp_current) == (100, 94, 30_000)
    assert await service.apply_scaling(now=T0 + timedelta(hours=12)) == 0


async def test_round_snapshot_is_stable(service, database):
    ((actor, _),) = await _characters(database, 1)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    round_ = await service.open_round(now=T0)
    snapshot = dict(round_.boss_snapshot)
    async with database[1].begin() as session:
        participant = (await session.scalars(select(FlageloParticipant))).one()
        boss = {k: v for k, v in participant.entry_snapshot.items() if k != "configuration"}
        assert boss == snapshot
        configuration = participant.entry_snapshot["configuration"]
        assert set(configuration) == {
            "combat_configuration_version",
            "equipment",
            "active_arts",
        }
    await service.leave(actor, now=T0 + timedelta(seconds=1))
    await service.apply_scaling(now=T0 + timedelta(minutes=40))
    async with database[1]() as session:
        assert (await session.get(FlageloRound, round_.id)).boss_snapshot == snapshot


# ------------------------------------------------------------------ morte e prêmio


async def test_death_resets_bar_settles_once_and_spawns_the_next_region(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=20_000))
    players = await _characters(database, 4)
    await _fill(database, service, "tdo")
    await _fill(database, service, "nareth")
    await service.tick(now=T0)
    event = await _active(database)
    assert event.region_id == "tdo"
    for actor, _ in players[:3]:
        await service.enter(actor, now=T0)
    # O 4º só entra e sai: sem participação real, sem prêmio.
    await service.enter(players[3][0], now=T0)
    await service.leave(players[3][0], now=T0)
    now = T0
    round_ = await service.open_round(now=now)
    for actor, _ in players[:3]:
        await service.register_action(actor, round_.round_number, "attack", now=now)
    now += fl.DECISION_WINDOW
    report = await service.tick(now=now)
    assert report.defeated == (event.id,)
    nxt = await _active(database)
    assert nxt is not None and nxt.region_id == "nareth"
    bar = await _bar(database, "tdo")
    assert (bar.current_points, bar.cycle, bar.active_flagelo_id) == (0, 2, None)
    async with database[1]() as session:
        dead = await session.get(FlageloEvent, event.id)
        assert dead.status == "settled" and dead.lifetime_seconds == 10
        assert dead.rankings["offensive"][0]["value"] == 20_000
    # Os 3 deram dano mas só têm 1 ponto: nenhum elegível, nenhum equipamento.
    assert dead.equipment_winner_id is None
    await service.tick(now=now + timedelta(seconds=1))
    async with database[1]() as session:
        notices = (
            await session.scalars(
                select(OutboxMessage.dedup_key).where(
                    OutboxMessage.topic == "flagelo.community_notice"
                )
            )
        ).all()
        assert sorted(notices) == sorted(
            [f"flagelo:spawn:{event.id}", f"flagelo:defeat:{event.id}", f"flagelo:spawn:{nxt.id}"]
        )


async def _eligible_kill(database, damage=60_000):
    """Elegível = dano (ataque) + cura (Arte de cura) + prevenção (Defender atingido)."""
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=1))
    players = await _characters(database, 3)
    event = await _spawn(database, service)
    for actor, _ in players:
        await service.enter(actor, now=T0)
    now = T0
    for action in ("defend", "attack", "art"):
        round_ = await service.open_round(now=now)
        async with database[1].begin() as session:
            row = await session.get(FlageloRound, round_.id)
            row.decision = {
                "action_key": "sopro_de_fuligem",
                "targets": [str(p) for _, p in players],
                "seed": 0,
            }
        for actor, _ in players:
            await service.register_action(
                actor,
                round_.round_number,
                action,
                art_slot=1 if action == "art" else None,
                now=now,
            )
        now += fl.DECISION_WINDOW
        await service.resolve_round(round_.id, now=now)
    service.simulator.damage = damage
    round_ = await service.open_round(now=now)
    await service.register_action(players[0][0], round_.round_number, "attack", now=now)
    now += fl.DECISION_WINDOW
    await service.tick(now=now)
    return service, event, players, now


async def test_eligible_rewards_ranking_equipment_and_idempotent_settlement(database):
    service, event, players, now = await _eligible_kill(database)
    async with database[1]() as session:
        dead = await session.get(FlageloEvent, event.id)
        assert dead.status == "settled"
        assert dead.equipment_winner_id in {p for _, p in players}
        rows = (await session.scalars(select(FlageloParticipant))).all()
        assert all(row.eligible for row in rows)
        top = dead.rankings["offensive"][0]
        assert top["character_id"] == str(players[0][1]) and top["position"] == 1
        crowns = {row.id: row.crowns for row in (await session.scalars(select(Character))).all()}
        settlements = (await session.scalars(select(FlageloRewardSettlement))).all()
        equipment = [s for s in settlements if s.reward_type == "equipment"]
        assert len(equipment) == 1 and equipment[0].status == "granted"
        assert equipment[0].character_id == dead.equipment_winner_id
        template_id = equipment[0].payload["template_id"]
        assert template_id in fl.FLAGELO_EQUIPMENT_TEMPLATES["varkhenn"]
        items = (
            await session.scalars(
                select(EquipmentItem).where(EquipmentItem.source_key.like("flagelo:%"))
            )
        ).all()
        assert len(items) == 1
        item = items[0]
        assert item.character_id == dead.equipment_winner_id
        assert item.payload["template_id"] == template_id
        assert item.payload["enhancement"] == 0 and item.item_level == 10
        recipes = [s for s in settlements if s.reward_type == "recipe"]
        assert len(recipes) == 3 and {s.status for s in recipes} <= {"granted", "skipped"}
        fragments = await session.scalar(
            select(func.sum(MaterialStack.quantity)).where(
                MaterialStack.character_id == players[0][1],
                MaterialStack.material_id == "material.flagelo.fragmento_cinza_condensada",
            )
        )
        # base 1 + 1º ofensivo 3 (+ suporte/defensivo conforme posição)
        assert fragments >= 4
        codex = await session.scalar(
            select(func.count())
            .select_from(CodexEntry)
            .where(CodexEntry.entry_id == "codex.flagelo.varkhenn")
        )
        assert codex == 3
    expected = fl.reward_bundle(10).crowns
    assert all(value >= expected for value in crowns.values())
    # Retry/restart da liquidação: nada é pago de novo.
    again = FlageloService(database[1], SERVER, FakeSimulator())
    async with database[1].begin() as session:
        dead = await session.get(FlageloEvent, event.id)
        dead.status = "defeated"
        for row in (await session.scalars(select(FlageloParticipant))).all():
            row.settled_at = None
    assert await again.settle(event.id, now=now) == 0
    async with database[1]() as session:
        after = {row.id: row.crowns for row in (await session.scalars(select(Character))).all()}
    assert after == crowns


async def test_restart_resumes_the_active_flagelo_from_the_database(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=10))
    ((actor, _),) = await _characters(database, 1)
    event = await _spawn(database, service)
    await service.enter(actor, now=T0)
    round_ = await service.open_round(now=T0)
    await service.register_action(actor, round_.round_number, "attack", now=T0)
    restarted = FlageloService(database[1], SERVER, FakeSimulator(damage=10))
    report = await restarted.tick(now=T0 + fl.DECISION_WINDOW)
    assert report.rounds_resolved == 1
    assert (await _active(database)).hp_current == event.hp_current - 10


async def test_mission_completion_contributes_four_in_its_region(service, database):
    ((_, character_id),) = await _characters(database, 1)
    async with database[1].begin() as session:
        quest = Quest(character_id=character_id, quest_id="P13", title="x", status="active", step=1)
        session.add(quest)
    async with database[1].begin() as session:
        quest = (await session.scalars(select(Quest))).one()
        quest.status = "completed"
    async with database[1].begin() as session:
        quest = (await session.scalars(select(Quest))).one()
        quest.step = 2  # outra escrita depois de concluída não conta de novo
    await service.apply_contributions(now=T0)
    async with database[1]() as session:
        rows = (await session.scalars(select(FlageloContribution))).all()
    assert [(row.kind, row.region_id, row.points) for row in rows] == [("mission", "nareth", 4)]
    assert (await _bar(database, "nareth")).current_points == 4


async def test_hub_shows_the_six_bars(service, database):
    ((actor, _),) = await _characters(database, 1)
    await _fill(database, service, "varzeas", 412)
    await service.apply_contributions(now=T0)
    view = await service.hub(actor, now=T0)
    assert [bar.label for bar in view.bars] == [
        "Ocaso",
        "Vales",
        "Nareth",
        "Várzeas",
        "Altos",
        "Confins",
    ]
    assert next(bar for bar in view.bars if bar.region_id == "varzeas").points == 412
    assert view.active is None


async def test_real_engine_attack_and_defend_through_the_existing_pipeline(database):
    """Sem simulador falso: o motor existente mede o dano e o lote aplica o golpe do Flagelo."""
    service = FlageloService(database[1], SERVER)
    (attacker, attacker_id), (defender, defender_id) = await _characters(database, 2, base=884000)
    event = await _spawn(database, service)
    for actor in (attacker, defender):
        await service.enter(actor, now=T0)
    round_ = await service.open_round(now=T0)
    async with database[1].begin() as session:
        row = await session.get(FlageloRound, round_.id)
        row.decision = {"action_key": "golpe_de_cinza", "targets": [str(defender_id)], "seed": 0}
    await service.register_action(attacker, round_.round_number, "attack", now=T0)
    await service.register_action(defender, round_.round_number, "defend", now=T0)
    await service.resolve_round(round_.id, now=T0 + fl.DECISION_WINDOW)
    current = await _active(database)
    assert current.hp_current < event.hp_current
    async with database[1]() as session:
        rows = {
            row.character_id: row for row in (await session.scalars(select(FlageloParticipant)))
        }
    assert rows[attacker_id].effective_damage == event.hp_current - current.hp_current
    assert rows[defender_id].defender_prevented_damage > 0
    async with database[1]() as session:
        history = (await session.get(FlageloRound, round_.id)).result["history"]
    hits = [item for item in history if item["kind"] == "player_damaged"]
    assert [item["character"] for item in hits] == [str(defender_id)]
