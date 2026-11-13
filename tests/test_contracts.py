"""Contratos Regionais (Documento B): criterios de aceitacao AC-01 a AC-24 e guardas estaticas."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from asterion.application import contracts as contracts_module
from asterion.application.character_deletion import delete_character_owned_data
from asterion.application.contracts import (
    ContractError,
    ContractService,
    record_hunt_victory,
    record_material_gain,
)
from asterion.application.road import RoadService
from asterion.bot import contracts_ui
from asterion.domain import contracts_config as cfg
from asterion.domain.chronicle_content import REGIONS_BY_NAME
from asterion.domain.contracts_catalog import BY_ID, CATALOG
from asterion.domain.narrative_choices import validate_node
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterNarrativeMemory,
    ConsumableStack,
    ContractInstance,
    EquipmentItem,
    MaterialStack,
    NarrativeChoiceRecord,
    NpcNarrativeMemory,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
A, B = 851001, 851002
OCASO = REGIONS_BY_NAME["Terras do Ocaso"]
VALES = REGIONS_BY_NAME["Vales dos Enforcados"]
COLETA = "CON_TDO_03"  # Couro Escoriado
CACA = "CON_TDO_01"
ENTREGA = "CON_TDO_04"
SRC = Path(__file__).resolve().parents[1] / "src" / "asterion"


@pytest.fixture(autouse=True)
def enabled():
    contracts_module.set_enabled(True)
    yield
    contracts_module.set_enabled(False)


async def _seed(database, *actors: int, gate: bool = True, level: int = 5) -> None:
    async with database[1].begin() as session:
        for actor in actors:
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id="ocaso",
                name="Contratante" if actor == A else "Mensageiro",
                race="remanescente",
                character_class="sentinela",
                stage="menu",
                ruleset_version="tdo-1.0.15",
                hp=Decimal("100"),
                max_hp=Decimal("100"),
                vigor=100,
                max_vigor=100,
                crowns=100,
                level=level,
            )
            session.add(character)
            await session.flush()
            session.add(
                WorldState(character_id=character.id, region="Terras do Ocaso", location=OCASO.hub)
            )
            if gate:
                session.add(
                    Quest(character_id=character.id, quest_id="P1", title="P1", status="completed")
                )


def _service(database) -> ContractService:
    return ContractService(database[1], "ocaso", RoadService(database[1], "ocaso"))


async def _char(database, actor: int) -> Character:
    async with database[1]() as session:
        return await session.scalar(select(Character).where(Character.telegram_id == actor))


async def _offer(service, definition_id: str, actor: int = A, now: datetime = NOW):
    board = await service.board(actor, now=now)
    return next(item for item in board.offers if item.definition.definition_id == definition_id)


async def _accept(service, definition_id: str, actor: int = A, now: datetime = NOW):
    offer = await _offer(service, definition_id, actor, now)
    return await service.accept(actor, offer.instance_id, offer.version, now=now)


async def _row(database, instance_id) -> ContractInstance:
    async with database[1]() as session:
        return await session.get(ContractInstance, instance_id)


async def _complete_coleta(database, service, definition_id: str = COLETA):
    view = await _accept(service, definition_id)
    char = await _char(database, A)
    material = BY_ID[definition_id].material_id
    async with database[1].begin() as session:
        character = await session.get(Character, char.id)
        await record_material_gain(
            session, character, material, cfg.TARGET_BY_TYPE["COLETA"], "test:drop", now=NOW
        )
    return view


# ---------------------------------------------------------------- guardas estaticas


def test_catalog_has_36_contracts_and_escort_is_off():
    assert len(CATALOG) == 36
    assert cfg.ESCORT_ACTIVE_CONTRACTS == 0
    assert "ESCOLTA" not in cfg.ACTIVE_TYPES
    assert {item.contract_type for item in CATALOG} <= set(cfg.ACTIVE_TYPES)


def test_system_is_disabled_by_default():
    from asterion.config import Settings

    assert Settings.model_fields["contracts_enabled"].default is False
    contracts_module.set_enabled(False)
    assert contracts_module.is_enabled() is False


def test_game_numbers_live_only_in_the_config_file():
    """§38: nenhum outro modulo de Contratos repete recompensa, duracao ou limite."""
    names = ("contracts.py", "contracts_catalog.py", "contracts_ui.py", "contracts_handlers.py")
    for path in SRC.rglob("*.py"):
        if path.name not in names:
            continue
        text = path.read_text(encoding="utf-8")
        for value in re.findall(r"\b(?:REWARD_R\d_[A-Z_]+\"\s*:\s*\()", text):
            raise AssertionError(f"{path.name} repeats reward values: {value}")
        assert "timedelta(hours" not in text, path.name


def test_reward_materials_belong_to_the_region():
    from asterion.domain.professions import MATERIAL_NAMES

    prefixes = {
        "R1": "tdo",
        "R2": "vde",
        "R3": "nareth",
        "R4": "varzeas",
        "R5": "altos",
        "R6": "confins",
    }
    for region, material in cfg.REGION_REWARD_MATERIAL.items():
        assert material in MATERIAL_NAMES and material.startswith(f"material.{prefixes[region]}.")
    for item in CATALOG:
        if item.material_id:
            assert item.material_id.startswith(f"material.{prefixes[item.region]}.")


def test_screens_respect_the_button_limit_and_callback_size():
    from uuid import uuid4

    definition = BY_ID[CACA]
    view = contracts_module.ContractView(
        uuid4(), 3, definition, "ACEITO", 0, 1, NOW, 120, 20, 2, "x", True, "req", None
    )
    board = contracts_module.BoardView("R1", "Terras do Ocaso", True, None, (view,) * 6, 0)
    screens = [
        contracts_ui.render_board(board),
        contracts_ui.render_detail(view),
        contracts_ui.render_mine((view,) * 3),
        contracts_ui.render_contract(view),
        contracts_ui.render_abandon(view),
    ]
    for screen in screens:
        buttons = [b for row in screen.keyboard.inline_keyboard for b in row]
        assert len(buttons) <= cfg.MAX_BUTTONS
        assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert len([b for row in screens[0].keyboard.inline_keyboard for b in row]) == 8


def test_xp_and_crowns_sit_in_the_25_percent_band_of_the_region_reference():
    """Fechamento §8: XP/Coroas ficam entre 20% e 30% do ganho de referencia da regiao."""
    from asterion.application.progression import level_xp
    from asterion.domain.economy import crowns_per_level

    for region, (minimum, _) in cfg.LEVEL_BAND.items():
        xp_ref = level_xp(minimum)
        crowns_ref = crowns_per_level(minimum)
        for contract_type in cfg.ACTIVE_TYPES:
            reward = cfg.reward_profile(f"REWARD_{region}_{contract_type}")
            assert 0.20 <= reward.xp / xp_ref <= 0.30, f"{region}_{contract_type} xp fora da faixa"
            assert 0.20 <= reward.crowns / crowns_ref <= 0.30, (
                f"{region}_{contract_type} coroas fora da faixa"
            )


def test_material_gain_hook_is_never_reachable_from_trade_or_market():
    """Fechamento §4.4: transferencia/comercio entre jogadores nunca conta para Coleta."""
    forbidden = ("market.py", "trades.py")
    for path in SRC.rglob("*.py"):
        if path.name not in forbidden:
            continue
        text = path.read_text(encoding="utf-8")
        assert "record_material_gain" not in text, path.name
        assert "deliver_material" not in text, path.name


# ------------------------------------------------------------------- AC-01 a AC-24


async def test_ac_01_board_lists_only_available_eligible_contracts(database):
    await _seed(database, A)
    board = await _service(database).board(A, now=NOW)
    assert board.eligible and len(board.offers) == cfg.BOARD_OFFERS
    assert {o.state for o in board.offers} == {"DISPONIVEL"}
    assert all(o.eligible and o.definition.region == "R1" for o in board.offers)


async def test_ac_02_ineligible_character_cannot_accept(database):
    await _seed(database, A, gate=False)
    service = _service(database)
    board = await service.board(A, now=NOW)
    assert not board.eligible and board.offers == ()
    async with database[1].begin() as session:
        char = (await session.scalars(select(Character))).one()
        session.add(Quest(character_id=char.id, quest_id="P1", title="P1", status="completed"))
    offer = await _offer(service, CACA)
    async with database[1].begin() as session:
        await session.execute(Quest.__table__.delete())
    with pytest.raises(ContractError) as error:
        await service.accept(A, offer.instance_id, offer.version, now=NOW)
    assert error.value.code == "not_eligible"
    assert (await _row(database, offer.instance_id)).state == "DISPONIVEL"


async def test_ac_03_accept_creates_persistent_accepted_instance(database):
    await _seed(database, A)
    view = await _accept(_service(database), CACA)
    row = await _row(database, view.instance_id)
    assert row.state == "ACEITO" and row.accepted_at == NOW
    assert row.expires_at == NOW + cfg.ACCEPTED_DURATION


async def test_ac_04_duplicate_accept_keeps_one_accepted_instance(database):
    await _seed(database, A)
    service = _service(database)
    offer = await _offer(service, CACA)
    results = await asyncio.gather(
        service.accept(A, offer.instance_id, offer.version, now=NOW),
        service.accept(A, offer.instance_id, offer.version, now=NOW),
        return_exceptions=True,
    )
    assert sum(isinstance(r, ContractError) for r in results) == 1
    async with database[1]() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ContractInstance)
            .where(ContractInstance.state == "ACEITO")
        )
    assert count == 1


async def test_ac_05_matching_action_records_progress(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, COLETA)
    char = await _char(database, A)
    async with database[1].begin() as session:
        await record_material_gain(
            session,
            await session.get(Character, char.id),
            BY_ID[COLETA].material_id,
            1,
            "t:1",
            now=NOW,
        )
    row = await _row(database, view.instance_id)
    assert row.progress == 1 and row.state == "EM_ANDAMENTO"


async def test_ac_06_non_matching_action_does_not_change_progress(database):
    await _seed(database, A)
    service = _service(database)
    coleta = await _accept(service, COLETA)
    caca = await _accept(service, CACA)
    char = await _char(database, A)
    async with database[1].begin() as session:
        character = await session.get(Character, char.id)
        await record_material_gain(
            session, character, "material.tdo.erva_cinzenta", 5, "t:1", now=NOW
        )
        await record_hunt_victory(
            session, character, local_id=VALES.locals[0], action_started_at=NOW, now=NOW
        )
        await record_material_gain(
            session, character, BY_ID[COLETA].material_id, 2, "contract:own-reward", now=NOW
        )
    assert (await _row(database, coleta.instance_id)).progress == 0
    assert (await _row(database, caca.instance_id)).state == "ACEITO"


async def test_ac_07_requirements_met_completes_contract(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    row = await _row(database, view.instance_id)
    assert row.state == "CONCLUIDO" and row.completed_at == NOW and not row.claimed


async def test_ac_08_claim_pays_profile_once(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    before = await _char(database, A)
    result = await service.claim(A, view.instance_id, done.version, now=NOW)
    after = await _char(database, A)
    reward = cfg.reward_profile("REWARD_R1_COLETA")
    assert result.state == "RESGATADO"
    assert after.crowns - before.crowns == reward.crowns
    async with database[1]() as session:
        stack = await session.scalar(
            select(func.sum(MaterialStack.quantity)).where(
                MaterialStack.character_id == after.id,
                MaterialStack.material_id == BY_ID[COLETA].material_id,
            )
        )
    assert stack >= reward.materials


async def test_ac_09_old_claim_callback_pays_nothing(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    await service.claim(A, view.instance_id, done.version, now=NOW)
    paid = await _char(database, A)
    with pytest.raises(ContractError):
        await service.claim(A, view.instance_id, done.version, now=NOW)
    again = await _char(database, A)
    assert (again.crowns, again.xp, again.level) == (paid.crowns, paid.xp, paid.level)
    async with database[1]() as session:
        events = await session.scalar(
            select(func.count())
            .select_from(RewardEvent)
            .where(RewardEvent.source_id == f"contract:{view.instance_id.hex}")
        )
    assert events == 1


async def test_ac_10_confirmed_abandon_sets_abandoned(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, CACA)
    await service.abandon(A, view.instance_id, view.version, now=NOW)
    row = await _row(database, view.instance_id)
    assert row.state == "ABANDONADO" and row.abandoned_at == NOW
    with pytest.raises(ContractError):
        await service.abandon(A, view.instance_id, row.version, now=NOW)


async def test_ac_11_keeping_contract_leaves_it_active(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, CACA)
    keep = contracts_ui.render_abandon(view).keyboard.inline_keyboard[1][0]
    assert keep.text == "MANTER CONTRATO" and keep.callback_data.startswith("ctr:o:")
    assert (await service.get(A, view.instance_id, now=NOW)).state == "ACEITO"
    assert (await _row(database, view.instance_id)).state == "ACEITO"


async def test_ac_12_lapsed_instance_becomes_expired(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, CACA)
    later = NOW + cfg.ACCEPTED_DURATION + timedelta(seconds=1)
    assert (await service.get(A, view.instance_id, now=later)).state == "EXPIRADO"
    offer_row = await _row(database, view.instance_id)
    assert offer_row.state == "EXPIRADO"


async def test_ac_13_combat_started_before_expiry_may_complete_after(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, CACA)
    char = await _char(database, A)
    started = NOW + cfg.ACCEPTED_DURATION - timedelta(seconds=30)
    resolved = NOW + cfg.ACCEPTED_DURATION + timedelta(seconds=30)
    async with database[1].begin() as session:
        await record_hunt_victory(
            session,
            await session.get(Character, char.id),
            local_id=OCASO.locals[0],
            action_started_at=started,
            now=resolved,
        )
    assert (await _row(database, view.instance_id)).state == "CONCLUIDO"


async def test_ac_14_action_started_after_expiry_cannot_complete(database):
    await _seed(database, A)
    service = _service(database)
    view = await _accept(service, CACA)
    char = await _char(database, A)
    late = NOW + cfg.ACCEPTED_DURATION + timedelta(seconds=5)
    async with database[1].begin() as session:
        await record_hunt_victory(
            session,
            await session.get(Character, char.id),
            local_id=OCASO.locals[0],
            action_started_at=late,
            now=late,
        )
    row = await _row(database, view.instance_id)
    assert row.state == "EXPIRADO" and row.progress == 0


async def test_ac_15_restart_restores_state_without_duplication(database):
    await _seed(database, A)
    first = _service(database)
    view = await _complete_coleta(database, first)
    restarted = _service(database)
    mine = await restarted.mine(A, now=NOW)
    assert [m.instance_id for m in mine] == [view.instance_id] and mine[0].state == "CONCLUIDO"
    await restarted.board(A, now=NOW)
    await restarted.board(A, now=NOW)
    async with database[1]() as session:
        total = await session.scalar(select(func.count()).select_from(ContractInstance))
    assert total == cfg.BOARD_OFFERS
    assert (await _char(database, A)).crowns == 100


async def test_ac_16_deleted_character_leaves_no_playable_contract(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    char = await _char(database, A)
    async with database[1].begin() as session:
        await delete_character_owned_data(session, char.id)
        await session.execute(Character.__table__.delete().where(Character.id == char.id))
    assert await _row(database, view.instance_id) is None
    with pytest.raises(ContractError):
        await service.claim(A, view.instance_id, 3, now=NOW)
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(RewardEvent)) == 0


async def test_ac_17_blocked_region_rejects_action_without_bypassing_gate(database):
    await _seed(database, A)
    service = _service(database)
    caca = await _accept(service, CACA)
    entrega = await _accept(service, ENTREGA)
    char = await _char(database, A)
    async with database[1].begin() as session:
        await session.execute(Quest.__table__.delete())
    with pytest.raises(ContractError) as error:
        await service.act(A, entrega.instance_id, entrega.version, now=NOW)
    assert error.value.code == "not_eligible"
    async with database[1].begin() as session:
        await record_hunt_victory(
            session,
            await session.get(Character, char.id),
            local_id=OCASO.locals[0],
            action_started_at=NOW,
            now=NOW,
        )
    row = await _row(database, caca.instance_id)
    assert row.state == "ACEITO" and row.progress == 0


async def test_ac_18_contract_never_grants_equipment(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    await service.claim(A, view.instance_id, done.version, now=NOW)
    async with database[1]() as session:
        kinds = set(await session.scalars(select(RewardComponent.kind)))
        assert kinds <= {"xp", "crowns", "material"}
        assert await session.scalar(select(func.count()).select_from(EquipmentItem)) == 0
        assert await session.scalar(select(func.count()).select_from(ConsumableStack)) == 0


async def test_ac_19_completing_contract_records_no_narrative_choice(database):
    with pytest.raises(ValueError):
        validate_node(SimpleNamespace(mission_kind="contrato", choice_id="CON_X"))
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    await service.claim(A, view.instance_id, done.version, now=NOW)
    async with database[1]() as session:
        for model in (NarrativeChoiceRecord, CharacterNarrativeMemory, NpcNarrativeMemory):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


async def test_ac_20_contracts_never_touch_the_campaign(database):
    await _seed(database, A)
    service = _service(database)
    async with database[1]() as session:
        quests = sorted((await session.scalars(select(Quest.quest_id))).all())
        world = (await session.scalars(select(WorldState.location))).all()
    for definition_id in (COLETA, "CON_TDO_02"):
        view = await _complete_coleta(database, service, definition_id)
        done = await service.get(A, view.instance_id, now=NOW)
        await service.claim(A, view.instance_id, done.version, now=NOW)
    async with database[1]() as session:
        assert sorted((await session.scalars(select(Quest.quest_id))).all()) == quests
        assert (await session.scalars(select(WorldState.location))).all() == world


async def test_ac_21_reward_cannot_move_between_characters(database):
    await _seed(database, A, B)
    service = _service(database)
    view = await _complete_coleta(database, service)
    done = await service.get(A, view.instance_id, now=NOW)
    before = await _char(database, B)
    with pytest.raises(ContractError) as error:
        await service.claim(B, view.instance_id, done.version, now=NOW)
    assert error.value.code == "not_found"
    after = await _char(database, B)
    assert (after.crowns, after.xp) == (before.crowns, before.xp)
    assert (await _row(database, view.instance_id)).state == "CONCLUIDO"


async def test_ac_22_renewed_board_creates_new_identities(database):
    await _seed(database, A)
    service = _service(database)
    first = await service.board(A, now=NOW)
    second = await service.board(A, now=NOW + cfg.BOARD_REFRESH + timedelta(minutes=1))
    old_ids = {o.instance_id for o in first.offers}
    assert len(second.offers) == cfg.BOARD_OFFERS
    assert old_ids.isdisjoint({o.instance_id for o in second.offers})
    async with database[1]() as session:
        states = set(
            await session.scalars(
                select(ContractInstance.state).where(
                    ContractInstance.contract_instance_id.in_(old_ids)
                )
            )
        )
    assert states == {"EXPIRADO"}


async def test_ac_23_completed_contract_keeps_reward_pending_and_slot(database):
    await _seed(database, A)
    service = _service(database)
    view = await _complete_coleta(database, service)
    assert (await _char(database, A)).crowns == 100
    async with database[1]() as session:
        assert await session.scalar(select(func.count()).select_from(RewardEvent)) == 0
    for definition_id in ("CON_TDO_02", CACA):
        await _accept(service, definition_id)
    offer = await _offer(service, ENTREGA)
    with pytest.raises(ContractError) as error:
        await service.accept(A, offer.instance_id, offer.version, now=NOW)
    assert error.value.code == "limit"
    assert (await service.get(A, view.instance_id, now=NOW)).state == "CONCLUIDO"


async def test_ac_24_stale_buttons_are_revalidated_before_any_mutation(database):
    await _seed(database, A)
    service = _service(database)
    offer = await _offer(service, CACA)
    accepted = await service.accept(A, offer.instance_id, offer.version, now=NOW)
    with pytest.raises(ContractError):
        await service.accept(A, offer.instance_id, offer.version, now=NOW)
    with pytest.raises(ContractError) as error:
        await service.abandon(A, offer.instance_id, offer.version, now=NOW)
    assert error.value.code == "stale"
    with pytest.raises(ContractError):
        await service.claim(A, offer.instance_id, accepted.version, now=NOW)
    row = await _row(database, offer.instance_id)
    assert row.state == "ACEITO" and row.version == accepted.version
