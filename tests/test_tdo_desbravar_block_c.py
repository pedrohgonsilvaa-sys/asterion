"""Bloco C (Desbravar) da TdO v1.0.18: criterios 3, 6, 7, 16 e 17 (33.16) e UI 66."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

import asterion.application.road as road_application
from asterion.application.action_throttle import (
    ACTION_DESBRAVAR,
    RESOLVING_TIMEOUT,
    acquire_action_slot,
    release_action_slot,
)
from asterion.application.road import CHARNECA, ROAD
from asterion.application.s5 import S5_CREATURES, choose_s5_creature
from asterion.bot.groups_ui import render_hunt_unlock_blocked
from asterion.bot.road_ui import render_current_local
from asterion.domain.road import (
    BOSQUE_EXPLORATION_PROFILE,
    BOSQUE_PROFILE,
    CHARNECA_EXPLORATION_PROFILE,
    CHARNECA_LOCATION,
    ROAD_EXPLORATION_PROFILE,
    RUINS_EXPLORATION_PROFILE,
    select_exploration_result,
)
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    Character,
    CharacterActionThrottle,
    ExplorationAttempt,
    RewardComponent,
    WorldState,
)
from tests.test_charneca_content import _seed_charneca
from tests.test_road_integration import _seed_road

TDO_EXPLORATION_PROFILES = (
    ROAD_EXPLORATION_PROFILE,
    CHARNECA_EXPLORATION_PROFILE,
    BOSQUE_EXPLORATION_PROFILE,
    RUINS_EXPLORATION_PROFILE,
)
GREAT_DISCOVERIES = (
    (CHARNECA_EXPLORATION_PROFILE, "braseiro"),
    (CHARNECA_EXPLORATION_PROFILE, "cripta"),
    (BOSQUE_EXPLORATION_PROFILE, "braseiro"),
    (BOSQUE_EXPLORATION_PROFILE, "estrutura_enterrada"),
    (RUINS_EXPLORATION_PROFILE, "galerias_vigia"),
)


# ---- item 1 / criterio 2: "Local novo" nao e resultado de Desbravar ---------------------


@pytest.mark.parametrize("profile", TDO_EXPLORATION_PROFILES)
def test_no_local_result_in_desbravar_pool(profile):
    assert not [item for item in profile.results if ".local." in item.result_id]
    assert {item.category for item in profile.results} <= {
        "great_discovery",
        "knowledge",
        "narrative",
        "combat",
        "resource",
        "atmospheric",
    }


# ---- item 7: Grandes Descobertas sem trava de nivel (FINAL 11.2) ------------------------


@pytest.mark.parametrize(("profile", "key"), GREAT_DISCOVERIES)
def test_great_discoveries_have_no_level_gate(profile, key):
    assert profile.result(key).min_level == 1


@pytest.mark.parametrize(("profile", "key"), GREAT_DISCOVERIES)
def test_level_one_character_can_draw_great_discovery(profile, key):
    drawn = {select_exploration_result(f"seed{i}", 1, profile=profile) for i in range(1500)}
    assert key in drawn


# ---- item 3 / criterio 17: BKP de Habitat e marco unico por criatura e por Local ---------


@pytest.mark.asyncio
async def test_habitat_bkp_is_granted_once_per_creature_and_local(database):
    actor = 880201
    service = await _seed_charneca(database, actor=actor, level=4, location=CHARNECA)
    charneca = road_application.hunt_profile_for_local_id(CHARNECA_LOCATION)
    bosque = BOSQUE_PROFILE

    async def bkp(session, character_id):
        entry = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == "aranha_cinza",
            )
        )
        return entry.bkp

    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await service._bestiary(session, character.id, "aranha_cinza")
        await session.flush()
        base = await bkp(session, character.id)
        assert await service._record_charneca_habitat(
            session, character.id, "aranha_cinza", charneca
        )
        after_first = await bkp(session, character.id)
        assert after_first == base + 3
        for _ in range(3):
            assert not await service._record_charneca_habitat(
                session, character.id, "aranha_cinza", charneca
            )
        assert await bkp(session, character.id) == after_first
        # Outro Local conta como outro marco (por criatura E por Local).
        assert await service._record_charneca_habitat(
            session, character.id, "aranha_cinza", bosque
        )
        assert await bkp(session, character.id) == after_first + 3
        assert not await service._record_charneca_habitat(
            session, character.id, "aranha_cinza", bosque
        )


# ---- item 4 / criterio 16: S4/S5 contam qualquer criatura do tipo ------------------------


def test_s5_accepts_either_creature_without_member_unlock_level():
    drawn = {choose_s5_creature(uuid4()) for _ in range(60)}
    assert drawn == set(S5_CREATURES) == {"custodio_sem_rosto", "mariposa_brasa"}


def test_s4_and_s5_do_not_check_member_unlock_level():
    from pathlib import Path

    import asterion.application.s4 as s4_module
    import asterion.application.s5 as s5_module

    for module in (s4_module, s5_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "unlock_level_blockers" not in source
        assert "eligible_creature_weights" not in source


# ---- item 8 / UI 66.4: tela de bloqueio da Cacada em Grupo -------------------------------


def test_unlock_blocked_screen_cites_every_member_with_voltar_button():
    screen = render_hunt_unlock_blocked(["Bravo", "Cedar"])
    assert screen.text == (
        "⚠ Caçada indisponível\n\n"
        "Bravo e Cedar ainda não cumprem o nível mínimo de nenhuma criatura deste Local."
    )
    assert "nada para caçar" not in screen.text
    buttons = [button for row in screen.keyboard.inline_keyboard for button in row]
    assert [button.text for button in buttons] == ["Voltar"]
    single = render_hunt_unlock_blocked(["Bravo"])
    assert "Bravo ainda não cumpre o nível mínimo" in single.text


# ---- item 5 / UI 66.1 item 6: Cacada e Desbravar da Estrada escondidos durante P1 --------


async def _road_view(database, service, actor):
    async with database[1].begin() as session:
        await session.execute(update(WorldState).values(location=ROAD))
    async with database[1].begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        world = await session.scalar(select(WorldState))
        return await service._view_for_world(session, character, world)


@pytest.mark.asyncio
async def test_road_hides_hunt_and_desbravar_while_p1_is_active(database):
    actor = 880202
    _, service = await _seed_road(database, actor, p1_status="active")
    view = await _road_view(database, service, actor)
    assert view.location == ROAD
    assert view.activities_hidden is True
    screen = render_current_local(view)
    assert "Caçada" not in screen.text
    assert "Desbravar" not in screen.text
    labels = [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert "Caçar" not in labels
    assert "Desbravar" not in labels


@pytest.mark.asyncio
async def test_road_shows_hunt_and_desbravar_after_p1(database):
    actor = 880203
    _, service = await _seed_road(database, actor)
    view = await _road_view(database, service, actor)
    assert view.activities_hidden is False
    screen = render_current_local(view, explore_state="available")
    labels = [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert "Caçar" in labels
    assert "Desbravar" in labels


# ---- itens 1 e 6 / criterio 6: sem recarga de 5 min, sem limite 6/60 min, so anti-spam ---


async def _backdate_throttle(database, seconds=10):
    async with database[1].begin() as session:
        await session.execute(
            update(CharacterActionThrottle).values(
                last_click_at=datetime.now(UTC) - timedelta(seconds=seconds)
            )
        )


def _atmospheric(monkeypatch):
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *_a, **_k: (
            "atmospheric",
            "explore.tdo.charneca.pedras_negras",
            "Pedras negras cobrem parte do terreno.",
        ),
    )


@pytest.mark.asyncio
async def test_desbravar_has_no_five_minute_cooldown_nor_six_per_hour_limit(
    database, monkeypatch
):
    actor = 880204
    service = await _seed_charneca(database, actor=actor, level=4, location=CHARNECA)
    _atmospheric(monkeypatch)
    prepared = await service.prepare_explore(actor)
    assert prepared.kind == "explore_prepare"
    for index in range(8):
        view = await service.explore(actor)
        assert view.kind == "exploration", f"tentativa {index + 1}: {view.kind}"
        assert view.retry_available is True
        await service.acknowledge_result(actor)
        await _backdate_throttle(database)
        prepared = await service.prepare_explore(actor)
        assert prepared.kind == "explore_prepare"
    async with database[1]() as session:
        total = await session.scalar(select(func.count(ExplorationAttempt.id)))
        assert total == 8
    local_view = await service.resume(actor)
    assert local_view.explore_available is True


@pytest.mark.asyncio
async def test_desbravar_three_second_antispam_has_no_effect_on_reward(database, monkeypatch):
    actor = 880205
    service = await _seed_charneca(database, actor=actor, level=4, location=CHARNECA)
    _atmospheric(monkeypatch)
    first = await service.explore(actor)
    assert first.kind == "exploration"
    await service.acknowledge_result(actor)
    # Segundo clique imediato: recusado sem efeito.
    second = await service.explore(actor)
    assert second.kind == "explore_throttle"
    async with database[1]() as session:
        attempts = await session.scalar(select(func.count(ExplorationAttempt.id)))
        throttle = await session.scalar(select(CharacterActionThrottle))
        vigor = await session.scalar(select(Character.vigor))
    assert attempts == 1
    assert vigor == 100
    # Nada fica "em resolucao" depois do commit (item 6).
    assert throttle.resolving is False
    await _backdate_throttle(database, seconds=3)
    third = await service.explore(actor)
    assert third.kind == "exploration"


# ---- item 2 / criterio 7: Vigor 4 so quando paga economia -------------------------------


@pytest.mark.asyncio
async def test_repeatable_economy_is_capped_by_vigor_over_many_attempts(database, monkeypatch):
    actor = 880206
    service = await _seed_charneca(database, actor=actor, level=4, vigor=100, location=CHARNECA)
    # Congela a regeneracao de Vigor: o criterio mede so o gasto.
    monkeypatch.setattr(road_application, "reconcile_character_vigor", _no_regen)
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *_a, **_k: (
            "resource",
            "explore.tdo.charneca.erva",
            "Erva Cinzenta pode ser recolhida na Charneca.",
        ),
    )
    for _ in range(40):
        view = await service.explore(actor)
        assert view.kind == "exploration"
        await service.acknowledge_result(actor)
        await _backdate_throttle(database)
    async with database[1]() as session:
        crowns_payments = await session.scalar(
            select(func.count(RewardComponent.id)).where(RewardComponent.kind == "crowns")
        )
        material_payments = await session.scalar(
            select(func.count(RewardComponent.id)).where(RewardComponent.kind == "material")
        )
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
    # Vigor 100 / 4 = 25 pagamentos; as 15 tentativas seguintes ocorrem sem economia.
    assert crowns_payments == 25
    assert character.vigor == 0
    assert character.crowns == 25 * 20
    assert material_payments <= 25 * 2


async def _no_regen(*_args, **_kwargs):
    return None


@pytest.mark.asyncio
async def test_attempt_with_vigor_below_four_runs_without_repeatable_economy(
    database, monkeypatch
):
    actor = 880207
    service = await _seed_charneca(database, actor=actor, level=4, vigor=3, location=CHARNECA)
    monkeypatch.setattr(road_application, "reconcile_character_vigor", _no_regen)
    monkeypatch.setattr(
        road_application,
        "_explore_result",
        lambda *_a, **_k: (
            "resource",
            "explore.tdo.charneca.erva",
            "Erva Cinzenta pode ser recolhida na Charneca.",
        ),
    )
    view = await service.explore(actor)
    assert view.kind == "exploration"
    async with database[1]() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        paid = await session.scalar(
            select(func.count(RewardComponent.id)).where(
                RewardComponent.kind.in_(("crowns", "material"))
            )
        )
    assert character.vigor == 3
    assert character.crowns == 0
    assert paid == 0


# ---- item 6: flag "resolving" nao trava o jogador para sempre ----------------------------


@pytest.mark.asyncio
async def test_orphan_resolving_flag_expires_after_timeout(database):
    character_id = await _seed_character_row(database, 880208)
    now = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
    async with database[1].begin() as session:
        first = await acquire_action_slot(session, character_id, ACTION_DESBRAVAR, now)
        assert first.allowed
    # Processo morreu sem release: dentro do prazo ainda recusa...
    async with database[1].begin() as session:
        within = await acquire_action_slot(
            session, character_id, ACTION_DESBRAVAR, now + timedelta(seconds=10)
        )
        assert (within.allowed, within.reason) == (False, "resolving")
    # ...depois do prazo a flag orfa e ignorada e o clique passa.
    async with database[1].begin() as session:
        later = await acquire_action_slot(
            session, character_id, ACTION_DESBRAVAR, now + RESOLVING_TIMEOUT + timedelta(seconds=1)
        )
        assert later.allowed
        await release_action_slot(session, character_id)


@pytest.mark.asyncio
async def test_hold_false_never_persists_resolving(database):
    character_id = await _seed_character_row(database, 880209)
    now = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)
    async with database[1].begin() as session:
        decision = await acquire_action_slot(
            session, character_id, ACTION_DESBRAVAR, now, hold=False
        )
        assert decision.allowed
    async with database[1]() as session:
        row = await session.scalar(select(CharacterActionThrottle))
        assert row.resolving is False
        assert row.last_click_at == now


async def _seed_character_row(database, actor):
    from asterion.infrastructure.db.models import Account

    character_id = uuid4()
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Tester" + "".join(chr(ord("a") + int(digit)) for digit in str(actor)),
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.7.0-baseline-1.0",
                level=1,
                xp=0,
                hp=Decimal("900"),
                max_hp=Decimal("900"),
                vigor=50,
                max_vigor=100,
                crowns=0,
            )
        )
    return character_id
