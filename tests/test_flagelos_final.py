"""O Despertar dos Flagelos — especificação final sobre PostgreSQL real: lock da Configuração,
snapshot de entrada, equipamento/Receita, Códice, HUD da Região e bordas de tempo."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment import EquipmentService
from asterion.application.flagelo_contributions import record_contribution
from asterion.application.flagelos import FlageloError, FlageloService
from asterion.bot.refuge_hud import RefugeHud
from asterion.bot.world_ui import render_refuge_dashboard
from asterion.domain import flagelo_lore as lore
from asterion.domain import flagelos as fl
from asterion.infrastructure.db.models import (
    Character,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    FlageloContribution,
    FlageloEvent,
    FlageloParticipant,
    FlageloRewardSettlement,
    GameActivity,
    Unlock,
)
from tests.test_flagelos_service import (
    SERVER,
    T0,
    FakeSimulator,
    _active,
    _bar,
    _characters,
    _eligible_kill,
    _round,
    _spawn,
)


@pytest.fixture
def service(database) -> FlageloService:
    return FlageloService(database[1], SERVER, FakeSimulator())


# ------------------------------------------------------------------ lock da Configuração


async def test_configuration_is_locked_in_combat_and_released_only_by_valid_resolution(
    service, database
):
    ((actor, _),) = await _characters(database, 1, base=700000)
    await _spawn(database, service)
    equipment = EquipmentService(database[1], SERVER)
    await service.enter(actor, now=T0)
    with pytest.raises(CombatConfigurationLocked) as locked:
        await equipment.unequip_slot(actor, "Cabeça")
    assert locked.value.blocker.kind == "flagelo"
    # Ver o hub, reabrir a tela ou reconectar não libera: só ``in_combat`` decide.
    await service.hub(actor, now=T0 + timedelta(seconds=3))
    await service.combat_screen(actor, now=T0 + timedelta(seconds=3))
    with pytest.raises(CombatConfigurationLocked):
        await equipment.unequip_slot(actor, "Cabeça")
    # Saída registrada é resolução válida do encontro: o lock termina.
    await service.leave(actor, now=T0 + timedelta(seconds=5))
    await equipment.unequip_slot(actor, "Cabeça")  # não está mais travado


async def test_defeat_of_the_player_releases_the_lock(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=0, player_hp=1))
    ((actor, character_id),) = await _characters(database, 1, base=701000)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    await _round(service, [actor], T0)
    async with database[1]() as session:
        row = (await session.scalars(select(FlageloParticipant))).one()
        assert row.in_combat is False and row.defeated_at is not None
    await EquipmentService(database[1], SERVER).unequip_slot(actor, "Cabeça")  # sem lock


async def test_entry_is_refused_while_another_activity_owns_the_configuration(
    service, database
):
    ((actor, character_id),) = await _characters(database, 1, base=702000)
    await _spawn(database, service)
    async with database[1].begin() as session:
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="tdo.hunt",
                status="active",
                ruleset_version="tdo-1.0.15",
            )
        )
    with pytest.raises(FlageloError) as busy:
        await service.enter(actor, now=T0)
    assert busy.value.code == "busy"


async def test_entry_snapshot_holds_the_configuration_and_reentry_takes_a_new_one(
    service, database
):
    ((actor, character_id),) = await _characters(database, 1, base=703000)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    async with database[1]() as session:
        first = (await session.scalars(select(FlageloParticipant))).one().entry_snapshot
    assert first["configuration"]["combat_configuration_version"] == 0
    assert first["configuration"]["equipment"]["ruleset_version"]
    await service.leave(actor, now=T0 + timedelta(seconds=1))
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        character.combat_configuration_version = 7
    await service.enter(actor, now=T0 + timedelta(minutes=2, seconds=1))
    async with database[1]() as session:
        second = (await session.scalars(select(FlageloParticipant))).one().entry_snapshot
    assert second["configuration"]["combat_configuration_version"] == 7


# ------------------------------------------------------------------ bordas de tempo


async def test_reentry_opens_exactly_at_two_minutes(service, database):
    ((actor, _),) = await _characters(database, 1, base=704000)
    await _spawn(database, service)
    await service.enter(actor, now=T0)
    await service.leave(actor, now=T0)
    with pytest.raises(FlageloError):
        await service.enter(actor, now=T0 + timedelta(minutes=2) - timedelta(microseconds=1))
    await service.enter(actor, now=T0 + timedelta(minutes=2))


async def test_scaling_boundaries_15_30_and_cap_without_healing(service, database):
    await _characters(database, 1, base=705000)
    event = await _spawn(database, service)
    base_hp, base_atq, hp = event.base_hp, event.base_atq, event.hp_current
    assert await service.apply_scaling(now=T0) == 0  # começa a contar
    assert await service.apply_scaling(now=T0 + timedelta(minutes=15)) == 1
    assert await service.apply_scaling(now=T0 + timedelta(minutes=15)) == 0  # idempotente
    assert await service.apply_scaling(now=T0 + timedelta(minutes=30)) == 1
    current = await _active(database)
    assert current.max_hp == fl.effective_max_hp(base_hp, Decimal("0.16"))
    assert current.attack == fl.effective_attack(base_atq, Decimal("0.06"))
    assert current.hp_current == hp  # não cura
    await service.apply_scaling(now=T0 + timedelta(minutes=600))
    current = await _active(database)
    assert current.abandonment_steps == fl.MAX_SCALING_STEPS
    assert current.max_hp == fl.effective_max_hp(base_hp, Decimal("0.80"))
    assert current.attack == fl.effective_attack(base_atq, Decimal("0.30"))
    assert current.base_def == event.base_def and current.hp_current == hp


async def test_entering_while_scaling_runs_keeps_one_consistent_state(service, database):
    ((actor, _),) = await _characters(database, 1, base=706000)
    await _spawn(database, service)
    await service.apply_scaling(now=T0)
    moment = T0 + timedelta(minutes=15)
    await asyncio.gather(service.enter(actor, now=moment), service.apply_scaling(now=moment))
    event = await _active(database)
    async with database[1]() as session:
        row = (await session.scalars(select(FlageloParticipant))).one()
    # Quem entrou viu os atributos que estavam gravados no momento (antes ou depois do passo).
    assert row.entry_snapshot["max_hp"] in {
        fl.effective_max_hp(event.base_hp, Decimal(0)),
        fl.effective_max_hp(event.base_hp, Decimal("0.08")),
    }
    assert event.abandonment_steps in {0, 1}


async def test_everyone_leaving_at_once_restarts_the_abandonment_clock(service, database):
    players = await _characters(database, 3, base=707000)
    await _spawn(database, service)
    for actor, _ in players:
        await service.enter(actor, now=T0)
    moment = T0 + timedelta(seconds=30)
    await asyncio.gather(*(service.leave(actor, now=moment) for actor, _ in players))
    event = await _active(database)
    assert event.last_zero_combat_at == moment
    assert await service.apply_scaling(now=moment + timedelta(minutes=15)) == 1


# ------------------------------------------------------------------ contribuição


async def test_group_hunt_and_dungeon_contribute_per_participant(service, database):
    players = await _characters(database, 4, base=708000)
    async with database[1].begin() as session:
        for _, character_id in players:
            character = await session.get(Character, character_id)
            await record_contribution(session, character, "group_hunt", "group:1")
            await record_contribution(session, character, "dungeon", "dungeon:1", region_id="vde")
            # Callback duplicado da mesma atividade não pontua de novo.
            await record_contribution(session, character, "dungeon", "dungeon:1", region_id="vde")
    await service.apply_contributions(now=T0)
    assert (await _bar(database, "tdo")).current_points == 4
    assert (await _bar(database, "vde")).current_points == 24


async def test_activity_during_an_active_flagelo_is_kept_but_not_counted(service, database):
    players = await _characters(database, 1, base=709000)
    await _spawn(database, service)
    async with database[1].begin() as session:
        character = await session.get(Character, players[0][1])
        await record_contribution(session, character, "mission", "q:1", region_id="tdo")
    await service.apply_contributions(now=T0)
    assert (await _bar(database, "tdo")).current_points == fl.THRESHOLD
    async with database[1]() as session:
        row = await session.scalar(
            select(FlageloContribution).where(FlageloContribution.activity_id == "q:1")
        )
    assert row.points == 4 and row.counted_points == 0


# ------------------------------------------------------------------ morte e prêmio


async def test_codex_and_bestiary_texts_are_granted_to_eligible_participants(database):
    _, event, players, _ = await _eligible_kill(database)
    async with database[1]() as session:
        entries = (
            await session.scalars(
                select(CodexEntry.entry_id).where(CodexEntry.character_id == players[0][1])
            )
        ).all()
        fragments = (
            await session.scalars(
                select(CodexFragment.fragment_id).where(
                    CodexFragment.character_id == players[0][1]
                )
            )
        ).all()
    assert {"codex.flagelo.despertar", "codex.flagelo.varkhenn"} <= set(entries)
    assert {
        lore.GENERAL_CODEX.fragment_id,
        lore.FLAGELO_CODEX["varkhenn"].fragment_id,
    } <= set(fragments)


async def test_exactly_one_equipment_and_duplicate_reward_callbacks_pay_once(database):
    service, event, players, now = await _eligible_kill(database)
    async with database[1].begin() as session:
        dead = await session.get(FlageloEvent, event.id)
        dead.status = "defeated"
        for row in (await session.scalars(select(FlageloParticipant))).all():
            row.settled_at = None
    await asyncio.gather(service.settle(event.id, now=now), service.settle(event.id, now=now))
    async with database[1]() as session:
        items = await session.scalar(
            select(func.count())
            .select_from(EquipmentItem)
            .where(EquipmentItem.source_key.like("flagelo:%"))
        )
        recipes = await session.scalar(
            select(func.count())
            .select_from(FlageloRewardSettlement)
            .where(FlageloRewardSettlement.reward_type == "recipe")
        )
        unlocks = (
            await session.scalars(
                select(Unlock.character_id).where(Unlock.unlock_id.like("recipe.flagelo.%"))
            )
        ).all()
    assert items == 1
    assert recipes == 3  # uma decisão de Receita por elegível
    assert len(unlocks) == len(set(unlocks)) <= 3  # no máximo uma descoberta por morte


async def test_no_recipe_roll_once_all_nine_are_known(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=1))
    players = await _characters(database, 3, base=880000)
    async with database[1].begin() as session:
        for recipe_id in fl.FLAGELO_RECIPES["varkhenn"]:
            session.add(Unlock(character_id=players[0][1], unlock_id=recipe_id))
    _, event, _, _ = await _eligible_kill(database, service=service, players=players)
    async with database[1]() as session:
        row = await session.scalar(
            select(FlageloRewardSettlement).where(
                FlageloRewardSettlement.character_id == players[0][1],
                FlageloRewardSettlement.reward_type == "recipe",
            )
        )
    assert row.status == "skipped" and row.payload == {"reason": "all_known"}


async def test_ineligible_participant_gets_nothing(database):
    service = FlageloService(database[1], SERVER, FakeSimulator(damage=10**6))
    ((actor, character_id),) = await _characters(database, 1, base=711000)
    event = await _spawn(database, service)
    await service.enter(actor, now=T0)
    await _round(service, [actor], T0)  # 1 ponto (só dano): mata, mas não é elegível
    await service.tick(now=T0 + timedelta(seconds=11))
    async with database[1]() as session:
        rows = (
            await session.scalars(
                select(FlageloRewardSettlement).where(
                    FlageloRewardSettlement.flagelo_id == event.id
                )
            )
        ).all()
        dead = await session.get(FlageloEvent, event.id)
        character = await session.get(Character, character_id)
    assert rows == [] and dead.equipment_winner_id is None
    assert character.crowns == 0


# ------------------------------------------------------------------ HUD da Região


async def test_region_hud_shows_bar_and_face_button(service, database):
    ((actor, _),) = await _characters(database, 1, base=712000)
    async with database[1].begin() as session:
        character = (await session.scalars(select(Character))).first()
        for index in range(123):
            await record_contribution(session, character, "hunt", f"h:{index}", region_id="tdo")
    await service.apply_contributions(now=T0)
    status = await service.region_status(actor)
    assert (status.bar.points, status.bar.threshold, status.bar.percent) == (123, 500, 24)
    assert status.flagelo_awake is False
    from tests.test_refuge_hud import _view

    screen = render_refuge_dashboard(_view(), hud=RefugeHud(flagelo=status))
    assert (
        "🩸 <b>Varkhenn, o Flagelo das Cinzas</b>\n🟥🟥⬜⬜⬜⬜⬜⬜⬜⬜ <code>24%</code>"
        .replace("🟥", "🟪")
    ) in screen.text
    buttons = [b.text for row in screen.keyboard.inline_keyboard for b in row]
    assert "⚔️ Enfrentar o Flagelo" not in buttons
    await _spawn(database, service, region_id="vde")
    status = await service.region_status(actor)
    assert status.flagelo_awake is True
    screen = render_refuge_dashboard(_view(), hud=RefugeHud(flagelo=status))
    pairs = {b.text: b.callback_data for row in screen.keyboard.inline_keyboard for b in row}
    assert pairs["⚔️ Enfrentar o Flagelo"] == "flg:hub"


# ------------------------------------------------------------------ Crafting global


@pytest.mark.parametrize(
    "recipe_id",
    [
        "recipe.flagelo.confins.arco.protocolo_incompativel",  # Lendário 2H, Núcleo
        "recipe.flagelo.vde.luvas.estrangulamento",  # Raro, Curteiro
    ],
)
async def test_flagelo_recipe_crafts_through_the_global_crafting(database, recipe_id):
    from uuid import UUID

    from asterion.application.crafting import CraftingRejected, CraftingService
    from asterion.domain import flagelo_catalog as cat
    from asterion.domain.professions import RECIPE_BY_ID, recipe_crown_cost, recipe_materials
    from tests.test_professions_crafting_integration import (
        _add_materials,
        _seed_active_professions,
        _set_profession_level,
    )

    template = cat.TEMPLATES_BY_RECIPE[recipe_id]
    recipe = RECIPE_BY_ID[recipe_id]
    actor = 993_100 + template.number
    secondary = "alchemist"
    character_id = await _seed_active_professions(
        database, actor, template.profession_id, secondary
    )
    await _set_profession_level(database, character_id, template.profession_id, 30)
    service = CraftingService(database[1], "ocaso")
    async with database[1].begin() as session:
        character = await session.get(Character, character_id)
        character.level = 60
        character.crowns = 100_000
    # Sem descobrir, a Receita não existe para o personagem.
    with pytest.raises(CraftingRejected) as unknown:
        await service.preview(actor, recipe_id)
    assert str(unknown.value) == "recipe_not_known"
    materials = {m.material_id: m.quantity for m in recipe_materials(recipe, 60)}
    await _add_materials(database, character_id, materials)
    async with database[1].begin() as session:
        session.add(Unlock(character_id=character_id, unlock_id=recipe_id))
    preview = await service.preview(actor, recipe_id)
    assert preview is not None and preview.crown_cost == recipe_crown_cost(
        recipe, preview.item_level
    )
    assert {i.material_id: i.required for i in preview.ingredients} == materials
    crafted = await service.commit(actor, preview.receipt_id)
    payload = crafted.output_payload["equipment"]
    assert payload["item_name"] == template.name and payload["rarity"] == template.rarity
    assert payload["slot"] == template.slot and payload["enhancement"] == 0
    assert payload["template_id"] == template.template_id
    if template.weapon_type_id:
        assert payload["weapon_type_id"] == template.weapon_type_id
    async with database[1]() as session:
        item = await session.get(EquipmentItem, UUID(crafted.output_payload["equipment_item_id"]))
        assert item is not None and item.character_id == character_id
