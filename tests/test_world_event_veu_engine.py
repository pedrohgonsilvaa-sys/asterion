"""A Ruptura do Véu sobre o motor de combate real: efeitos dos kits e suporte direto."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, update

from asterion.application.world_event_veu import VeuEventService, VeuEventUpkeep
from asterion.application.world_event_veu_combat import EngineRoundSimulator
from asterion.application.world_event_veu_views import VeuEventViews
from asterion.domain import veu_combat as vc
from asterion.infrastructure.db.models import (
    Character,
    CharacterActiveArtSlot,
    VeuEventAction,
    VeuEventNucleus,
    VeuEventParticipant,
)
from tests.test_world_event_veu_application import SERVER, SLOT, _characters

NOW = SLOT + timedelta(seconds=2)


@pytest.fixture
def svc(database) -> VeuEventService:
    return VeuEventService(database[1], SERVER, EngineRoundSimulator())


async def _arena(svc, database, base, count=3, luminar=()):
    characters = await _characters(database, count, base=base)
    async with database[1].begin() as session:
        for index in luminar:
            await session.execute(
                update(Character)
                .where(Character.id == characters[index])
                .values(character_class="luminar")
            )
            session.add(
                CharacterActiveArtSlot(
                    character_id=characters[index], slot=1, art_id="class_art.luminar.renovacao"
                )
            )
            session.add(
                CharacterActiveArtSlot(
                    character_id=characters[index], slot=2, art_id="class_art.luminar.egide_solar"
                )
            )
    await VeuEventUpkeep(svc).tick(SLOT)
    occurrence = (await svc.get_or_create_occurrence(SLOT)).id
    for character in characters:
        await svc.join(occurrence, character, now=SLOT)
    await VeuEventUpkeep(svc).tick(SLOT + timedelta(seconds=1))
    return occurrence, characters


async def _participant(database, occurrence, character):
    async with database[1]() as session:
        return await session.get(VeuEventParticipant, (occurrence, character))


async def _set_participant(database, occurrence, character, **values):
    async with database[1].begin() as session:
        await session.execute(
            update(VeuEventParticipant)
            .where(
                VeuEventParticipant.occurrence_id == occurrence,
                VeuEventParticipant.character_id == character,
            )
            .values(**values)
        )


@pytest.mark.asyncio
async def test_kit_debuff_lands_through_the_engine_round_lasts_two_rounds_and_expires(
    svc, database
):
    occurrence, (hero, _a, _b) = await _arena(svc, database, 790000)
    await svc.enter_nucleus(occurrence, hero, "A", now=NOW)
    round_ = await svc.open_round(occurrence, "A", now=NOW)
    await svc.register_action(round_.id, hero, "attack", now=NOW)
    # "Fechamento Súbito" (VEU-01): 90% ATQ + AGI −10% por 2T, escolhido pela IA da rodada.
    await svc.register_enemy_decision(
        round_.id, "VEU-01", "fechamento_subito", target_ids=[hero], now=NOW
    )
    before = (await _participant(database, occurrence, hero)).hp
    now = round_.decision_deadline
    await svc.resolve_round(round_.id, now=now)
    row = await _participant(database, occurrence, hero)
    (effect,) = row.combat_state["effects"]
    assert (effect["stat"], effect["kind"], effect["remaining"]) == ("agility", "debuff", 2)
    assert Decimal(effect["magnitude"]) == Decimal("0.10")
    assert row.hp is not None and (before is None or row.hp < before)  # tomou o dano do golpe
    # Duas rodadas ativos e expira (a da aplicação não conta).
    for expected in (1, None):
        nxt = await svc.open_round(occurrence, "A", now=now)
        await svc.register_action(nxt.id, hero, "attack", now=now)
        now = nxt.decision_deadline
        await svc.resolve_round(nxt.id, now=now)
        effects = (await _participant(database, occurrence, hero)).combat_state["effects"]
        assert (effects[0]["remaining"] if effects else None) == expected


@pytest.mark.asyncio
async def test_an_attack_debuff_changes_the_damage_the_engine_measures(svc, database):
    occurrence, (clean, hurt, _c) = await _arena(svc, database, 791000)
    for character in (clean, hurt):
        await svc.enter_nucleus(occurrence, character, "A", now=NOW)
    await _set_participant(
        database, occurrence, hurt,
        combat_state=vc.PlayerUnit(
            hurt, Decimal(1), Decimal(1), Decimal(1),
            effects=[vc.PlayerEffect("veu:test", "attack", Decimal("0.50"), 2)],
        ).state_data(),
    )
    round_ = await svc.open_round(occurrence, "A", now=NOW)
    for character in (clean, hurt):
        await svc.register_action(round_.id, character, "attack", target_ref="VEU-02", now=NOW)
    async with database[1].begin() as session:
        nucleus = await session.scalar(
            select(VeuEventNucleus).where(VeuEventNucleus.nucleus_key == "A")
        )
        participants = (
            await session.scalars(
                select(VeuEventParticipant).where(
                    VeuEventParticipant.character_id.in_([clean, hurt])
                )
            )
        ).all()
        actions = (await session.scalars(select(VeuEventAction))).all()
        enemies = {c: vc.EnemyUnit.from_data(c, d) for c, d in nucleus.enemy_state.items()}
        inputs = await EngineRoundSimulator().prepare(session, participants, actions, enemies, "k")
    damage = {intent.character_id: intent.damage for intent in inputs.intents}
    assert damage[clean] > damage[hurt] > 0  # ATQ −50% pelo Fighter.stat do motor


@pytest.mark.asyncio
async def test_defense_debuff_is_read_by_the_engine_stat_for_incoming_damage(svc, database):
    occurrence, (hero, _a, _b) = await _arena(svc, database, 792000)
    await svc.enter_nucleus(occurrence, hero, "A", now=NOW)
    await _set_participant(
        database, occurrence, hero,
        combat_state=vc.PlayerUnit(
            hero, Decimal(1), Decimal(1), Decimal(1),
            effects=[vc.PlayerEffect("veu:test", "defense", Decimal("0.50"), 2)],
        ).state_data(),
    )
    round_ = await svc.open_round(occurrence, "A", now=NOW)
    async with database[1].begin() as session:
        participants = (await session.scalars(select(VeuEventParticipant))).all()
        nucleus = await session.scalar(select(VeuEventNucleus))
        enemies = {c: vc.EnemyUnit.from_data(c, d) for c, d in nucleus.enemy_state.items()}
        inputs = await EngineRoundSimulator().prepare(session, participants, [], enemies, "k")
    reduced = inputs.players[hero].defense
    async with database[1].begin() as session:
        await session.execute(
            update(VeuEventParticipant).values(combat_state={})
        )
    async with database[1].begin() as session:
        participants = (await session.scalars(select(VeuEventParticipant))).all()
        nucleus = await session.scalar(select(VeuEventNucleus))
        enemies = {c: vc.EnemyUnit.from_data(c, d) for c, d in nucleus.enemy_state.items()}
        clean = await EngineRoundSimulator().prepare(session, participants, [], enemies, "k")
    assert reduced == clean.players[hero].defense * Decimal("0.5")
    assert round_.round_number == 1


@pytest.mark.asyncio
async def test_direct_heal_is_applied_in_the_same_batch_and_counts_as_significant(svc, database):
    occurrence, (healer, ally, _c) = await _arena(svc, database, 793000, luminar=(0,))
    await svc.enter_nucleus(occurrence, healer, "C", now=NOW)
    await svc.enter_nucleus(occurrence, ally, "C", now=NOW)
    await _set_participant(database, occurrence, ally, hp=Decimal(100))
    round_ = await svc.open_round(occurrence, "C", now=NOW)
    await svc.register_action(
        round_.id, healer, "art", art_slot=1, target_ref=f"c:{ally.hex}", now=NOW
    )
    await svc.resolve_round(round_.id, now=round_.decision_deadline)
    row = await _participant(database, occurrence, ally)
    assert row.hp > 100  # cura efetiva do motor (Renovação)
    async with database[1]() as session:
        action = (await session.scalars(select(VeuEventAction))).one()
        healer_row = await session.get(VeuEventParticipant, (occurrence, healer))
    assert action.significant and healer_row.significant_actions == 1


@pytest.mark.asyncio
async def test_support_barrier_carries_over_and_is_listed_only_in_the_support_section(
    svc, database
):
    occurrence, (healer, ally, _c) = await _arena(svc, database, 794000, luminar=(0,))
    for character in (healer, ally):
        await svc.enter_nucleus(occurrence, character, "C", now=NOW)
    round_ = await svc.open_round(occurrence, "C", now=NOW)
    await svc.register_action(
        round_.id, healer, "art", art_slot=2, target_ref=f"c:{ally.hex}", now=NOW
    )
    views = VeuEventViews(svc)
    async with database[1]() as session:
        telegram = (await session.get(Character, healer)).telegram_id
    # Antes da resolução: só o que foi registrado, sem números.
    screen = await views.nucleus_screen(telegram, "C", now=NOW)
    assert [(s.kind, s.source) for s in screen.support] == [("barrier", screen.self_name)]
    await svc.resolve_round(round_.id, now=round_.decision_deadline)
    row = await _participant(database, occurrence, ally)
    assert Decimal(row.combat_state["barrier"]) > 0 and row.combat_state["barrier_turns"] > 0
    assert row.combat_state["barrier_source"] == str(healer)
    # Rodada nova sem suporte registrado: a seção some.
    nxt = await svc.open_round(occurrence, "C", now=round_.decision_deadline)
    assert nxt.round_number == 2
    again = await views.nucleus_screen(telegram, "C", now=round_.decision_deadline)
    assert again.support == ()


@pytest.mark.asyncio
async def test_offensive_arts_never_appear_as_support(svc, database):
    occurrence, (hero, _a, _b) = await _arena(svc, database, 795000)
    await svc.enter_nucleus(occurrence, hero, "A", now=NOW)
    round_ = await svc.open_round(occurrence, "A", now=NOW)
    await svc.register_action(round_.id, hero, "art", art_slot=1, now=NOW)
    async with database[1]() as session:
        telegram = (await session.get(Character, hero)).telegram_id
    screen = await VeuEventViews(svc).nucleus_screen(telegram, "A", now=NOW)
    assert screen.support == ()
