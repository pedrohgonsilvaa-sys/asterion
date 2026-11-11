"""Encontros da Crônica I: creatures, [Enfrentar] and the repeated Eco (§11.1–11.3, §8)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.chronicle import ChronicleAdmin, ChronicleError
from asterion.application.chronicle_encounters import (
    ChronicleEncounterService,
    EncounterResultView,
)
from asterion.application.prologue import CombatView
from asterion.application.road import RoadService
from asterion.application.scripted_combat import current_combat
from asterion.bot.chronicle_ui import render_encounter, render_here
from asterion.domain.chronicle import ELITE_MIN_LEVEL, REPEATABLE_POINTS, calendar_for
from asterion.domain.chronicle_content import CONFINS, NARETH, OCASO
from asterion.domain.chronicle_encounters import (
    CHRONICLE_CREATURES,
    ENCOUNTERS,
    ENCOUNTERS_BY_OBJECTIVE,
    configure_encounter,
    encounter_level,
    scene_text,
)
from asterion.domain.combat import act
from asterion.domain.combat_math import enemy_stats
from asterion.domain.road import (
    ARCHETYPE,
    CATEGORY,
    CREATURE_CATALOG,
    EXPLORATION_PROFILES,
    ROAD_LOCATION,
    CreatureCombatantSpec,
    create_creature_party_combat,
    creature_for,
    enemy_xp,
    road_enemy_stats,
)
from asterion.infrastructure.db.combat_codec import encode
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    BestiaryEntry,
    Character,
    ChronicleCompletion,
    ChroniclePointGrant,
    GameActivity,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)

D = Decimal
SERVER = "ocaso"
DAY1 = date(2026, 12, 1)
CAL = calendar_for(DAY1)
BEFORE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEEK1 = CAL.starts_at + timedelta(hours=1)
WEEK6 = CAL.chapter_opens_at(6) + timedelta(hours=1)
ANA = 950001
ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"

# ------------------------------------------------------------------ pure rules

# creature id -> (category, archetype, {action: (coefficient, cooldown, hits, prepared)})
_KITS = {
    "creature.cr01.repetidor": (
        "common",
        "brute",
        {"gesto_oficio": ("1.00", None, 1, False), "golpe_repetido": ("0.60", 3, 2, False)},
    ),
    "creature.cr01.marcador": (
        "common",
        "controller",
        {"toque_medida": ("0.95", None, 1, False), "marca_desvio": ("0.90", 3, 1, False)},
    ),
    "creature.cr01.guarda_repetida": (
        "uncommon",
        "armored",
        {
            "golpe_posto": ("1.00", None, 1, False),
            "postura_copiada": ("0", 3, 1, False),
            "avanco_posto": ("1.25", 3, 1, False),
        },
    ),
    "creature.cr01.carregador_repetido": (
        "uncommon",
        "balanced",
        {"peso_largado": ("1.05", None, 1, False), "carga_preparada": ("1.60", 4, 1, True)},
    ),
    "elite.cr01.multidao_repetida": (
        "elite",
        "caster",
        {
            "empurrao": ("1.00", None, 1, False),
            "muitas_maos": ("0.40", 2, 3, False),
            "coro": ("0.75", 3, 1, False),
            "a_palavra": ("1.70", 4, 1, True),
        },
    ),
    "elite.cr01.escriba_repetido": (
        "elite",
        "controller",
        {
            "traco": ("1.00", None, 1, False),
            "rasura": ("0.90", 3, 1, False),
            "revisao": ("0", 4, 1, False),
            "registro_imposto": ("1.60", 4, 1, True),
        },
    ),
    "boss.cr01.mestre_de_turno": (
        "boss",
        "brute",
        {
            "ordem_turno": ("1.00", None, 1, False),
            "martelada_ritmo": ("1.35", 3, 1, False),
            "chamada": ("0", None, 1, False),
            "ordem_coletiva": ("0.80", 3, 1, False),
            "fim_de_turno": ("1.75", 5, 1, True),
        },
    ),
    "boss.cr01.o_que_aguarda_resposta": (
        "boss",
        "balanced",
        {
            "oferta": ("1.00", None, 1, False),
            "pedido_repetido": ("0.90", 3, 1, False),
            "insistencia": ("0.80", 3, 1, False),
            "selo_pendente": ("0", 4, 1, False),
            "espera": ("0", 4, 1, False),
            "confirmacao_exigida": ("1.85", 5, 1, True),
        },
    ),
}


def _combat(creature, level=25):
    return create_creature_party_combat(
        uuid4(),
        "Ana",
        "sentinela",
        "remanescente",
        D(99999),
        (CreatureCombatantSpec(creature, level, "enemy"),),
        player_level=level,
        configure_combat=configure_encounter,
    )


def test_kits_use_the_coefficients_of_the_proposal():
    assert set(CHRONICLE_CREATURES) == set(_KITS)
    for creature_id, (category, archetype, kit) in _KITS.items():
        creature = CHRONICLE_CREATURES[creature_id]
        assert (creature.category, creature.archetype) == (category, archetype)
        actions = _combat(creature).enemy_actions
        assert set(actions) == set(kit)
        for key, (coefficient, cooldown, hits, prepared) in kit.items():
            action = actions[key]
            assert action.coefficient == D(coefficient), key
            assert action.cooldown == cooldown, key
            assert action.hit_count == hits, key
            assert bool(action.prepared) is prepared, key


def test_effects_of_the_kits():
    marca = _combat(CHRONICLE_CREATURES["creature.cr01.marcador"]).enemy_actions["marca_desvio"]
    assert (marca.attack_debuff, marca.duration, marca.effect_stat) == (D("0.10"), 2, "defense")
    assert marca.skip_if_target_effect_active == marca.effect_id == "cr01.marca_desvio"
    escriba = _combat(CHRONICLE_CREATURES["elite.cr01.escriba_repetido"]).enemy_actions
    assert (escriba["rasura"].attack_debuff, escriba["rasura"].duration) == (D("0.12"), 2)
    revisao = escriba["revisao"]
    assert (revisao.self_barrier_coefficient, revisao.self_barrier_duration) == (D("0.80"), 2)
    assert (revisao.enemy_hp_fraction_below, revisao.max_uses_per_combat) == (D("0.50"), 2)
    postura = _combat(CHRONICLE_CREATURES["creature.cr01.guarda_repetida"]).enemy_actions[
        "postura_copiada"
    ]
    assert (postura.self_barrier_coefficient, postura.self_barrier_duration) == (D("0.70"), 2)
    assert postura.skip_if_barrier_active


def test_attributes_follow_the_published_formula_without_new_multipliers():
    for creature in CHRONICLE_CREATURES.values():
        for level in (1, 3, 25, 60):
            assert road_enemy_stats(creature, level) == enemy_stats(
                level, CATEGORY[creature.category], ARCHETYPE[creature.archetype]
            )


def test_creatures_are_in_the_catalog_but_in_no_regional_pool():
    for creature in CHRONICLE_CREATURES.values():
        assert creature in CREATURE_CATALOG
        assert creature_for(creature.creature_id) is creature
        assert creature.weight == 0
    pooled = {
        result.creature_id
        for profile in EXPLORATION_PROFILES.values()
        for result in profile.results
    }
    assert pooled.isdisjoint(CHRONICLE_CREATURES)


def test_encounter_level_stays_in_the_band_of_the_region():
    assert encounter_level(2, OCASO) == 2
    assert encounter_level(30, OCASO) == 10
    assert encounter_level(25, NARETH) == 25
    assert encounter_level(60, CONFINS) == 60
    assert "fuligem" in scene_text(ENCOUNTERS[0], OCASO)
    assert "névoa" in scene_text(ENCOUNTERS[0], CONFINS)


def test_encounters_cover_all_eight_chapters():
    assert [item.chapter for item in ENCOUNTERS] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [item.feat_id for item in ENCOUNTERS if item.feat_id] == [
        "feito_cr01_mestre_de_turno",
        "feito_cr01_multidao",
        "feito_cr01_escriba",
        "feito_cr01_aguarda_resposta",
    ]
    assert all(len(item.repeat_content_id) <= 64 for item in ENCOUNTERS)


def test_guarda_raises_a_two_turn_barrier_and_multi_hits_land_separately():
    combat = act(_combat(CHRONICLE_CREATURES["creature.cr01.guarda_repetida"]), "attack")
    enemy = combat.fighters["enemy"]
    assert any(event.action == "postura_copiada" for event in combat.events)
    assert enemy.barrier_remaining in (1, 2)
    combat = act(_combat(CHRONICLE_CREATURES["creature.cr01.repetidor"]), "attack")
    assert [e.action for e in combat.events if e.actor == "enemy"] == ["golpe_repetido"] * 2


# ------------------------------------------------------------------ PostgreSQL


async def _make(database, *, level=10, location=ROAD, actor=ANA):
    async with database[1].begin() as session:
        await session.merge(Account(telegram_id=actor))
        character = Character(
            telegram_id=actor,
            server_id=SERVER,
            name="Ana",
            race="remanescente",
            character_class="sentinela",
            stage="menu",
            ruleset_version="tdo-1.0.15",
            level=level,
            hp=D("100"),
            max_hp=D("100"),
            created_at=BEFORE,
        )
        session.add(character)
        await session.flush()
        session.add(WorldState(character_id=character.id, region=OCASO, location=location))
        session.add(Quest(character_id=character.id, quest_id="P1", title="P1", status="completed"))
        return character.id


def _service(database):
    async def latest(_session, _character, region):
        return ROAD_LOCATION if region == OCASO else None

    road = RoadService(database[1], SERVER)
    return ChronicleEncounterService(database[1], SERVER, latest, road.recover_normal_pve_defeat)


async def _schedule(database):
    await ChronicleAdmin(database[1], SERVER).set_day1(DAY1, "teste", now=BEFORE)


async def _set_hp(database, activity_id, *, enemy=None, player=None):
    async with database[1].begin() as session:
        activity = await session.get(GameActivity, activity_id)
        combat, _, record = await current_combat(session, activity)
        if enemy is not None:
            combat.fighters["enemy"].hp = D(enemy)
        if player is not None:
            combat.fighters["player"].hp = D(player)
        record.snapshot = encode(combat)


async def _win(database, service, chapter, slot, now):
    view = await service.start(ANA, chapter, slot, now=now)
    assert isinstance(view, CombatView)
    await _set_hp(database, view.activity_id, enemy=1)
    return await service.action(ANA, view.activity_id, view.combat.version, "attack", now=now)


async def _character(database) -> Character:
    async with database[1]() as session:
        return await session.scalar(select(Character).where(Character.telegram_id == ANA))


async def _trail(database) -> int:
    async with database[1]() as session:
        rows = await session.scalars(
            select(ChroniclePointGrant.points).where(ChroniclePointGrant.account_id == ANA)
        )
        return sum(rows.all())


async def test_fight_needs_the_local_the_level_and_an_open_chapter(database):
    await _make(database, level=2, location=REFUGE)
    await _schedule(database)
    service = _service(database)
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 1, 4, now=WEEK1)
    assert error.value.code == "chronicle_not_here"
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 6, 4, now=WEEK1)
    assert error.value.code == "chronicle_chapter_locked"
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 6, 4, now=WEEK6)
    assert error.value.code == "chronicle_level"
    assert ELITE_MIN_LEVEL == 3
    # Chapter 4 is a Chefe: Nv.5.
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 4, 4, now=WEEK6)
    assert error.value.code == "chronicle_level"
    listed = await service.encounters(ANA, now=WEEK6)
    assert [(item.objective.chapter, item.level_locked) for item in listed] == [
        (1, False), (2, False), (3, False), (4, True), (5, False), (6, True),
    ]  # fmt: skip
    assert await service.here(ANA, now=WEEK6) == ()


async def test_first_victory_pays_enemy_xp_and_the_objective_and_no_economy(database):
    character_id = await _make(database)
    await _schedule(database)
    service = _service(database)
    before = await _character(database)
    result = await _win(database, service, 1, 4, WEEK1)
    assert isinstance(result, EncounterResultView)
    expected = enemy_xp(10, "common", player_level=10)
    assert (result.victory, result.repeat, result.enemy_level) == (True, False, 10)
    assert (result.xp, result.objective_completed) == (expected, True)
    after = await _character(database)
    assert after.crowns == before.crowns
    assert after.xp == before.xp + expected
    assert await _trail(database) == 70
    async with database[1]() as session:
        kinds = (
            await session.scalars(
                select(RewardComponent.kind)
                .join(RewardEvent, RewardEvent.id == RewardComponent.reward_event_id)
                .where(RewardEvent.character_id == character_id)
            )
        ).all()
        assert kinds == ["enemy_xp"]
        entry = await session.scalar(
            select(BestiaryEntry).where(BestiaryEntry.character_id == character_id)
        )
        assert (entry.creature_id, entry.wins) == ("creature.cr01.repetidor", 1)
        done = await session.scalar(
            select(ChronicleCompletion.objective_id).where(
                ChronicleCompletion.character_id == character_id
            )
        )
        assert done == "cap_01_obj_04"
    assert "Enfrentar o Eco de novo" in render_here((), await service.here(ANA, now=WEEK1)).text


async def test_repeated_eco_pays_only_the_trilha_twice_a_day(database):
    await _make(database)
    await _schedule(database)
    service = _service(database)
    await _win(database, service, 1, 4, WEEK1)
    xp = (await _character(database)).xp
    for total in (1, 2):
        result = await _win(database, service, 1, 4, WEEK1)
        assert (result.repeat, result.xp, result.trail_points) == (True, 0, REPEATABLE_POINTS)
        assert await _trail(database) == 70 + total * REPEATABLE_POINTS
    assert (await _character(database)).xp == xp
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 1, 4, now=WEEK1)
    assert error.value.code == "chronicle_repeat_limit"
    assert await service.here(ANA, now=WEEK1) == ()
    tomorrow = await _win(database, service, 1, 4, WEEK1 + timedelta(days=1))
    assert tomorrow.trail_points == REPEATABLE_POINTS


async def test_defeat_costs_nothing_and_the_retry_keeps_the_frozen_level(database):
    character_id = await _make(database, level=5)
    await _schedule(database)
    service = _service(database)
    before = await _character(database)
    view = await service.start(ANA, 1, 4, now=WEEK1)
    assert view.combat.fighters["enemy"].level == 5
    assert (await service.foreground(ANA)).activity_id == view.activity_id
    with pytest.raises(ChronicleError) as error:
        await service.start(ANA, 1, 4, now=WEEK1)
    assert error.value.code == "chronicle_busy"
    await _set_hp(database, view.activity_id, player=1)
    result = await service.action(ANA, view.activity_id, view.combat.version, "attack", now=WEEK1)
    assert isinstance(result, EncounterResultView) and not result.victory
    after = await _character(database)
    assert (after.xp, after.crowns, after.level) == (before.xp, before.crowns, before.level)
    assert after.hp == after.max_hp
    assert await _trail(database) == 0
    assert await service.foreground(ANA) is None
    assert "não perdeu nada" in render_encounter(result).text
    async with database[1].begin() as session:
        (await session.get(Character, character_id)).level = 9
    retry = await service.start(ANA, 1, 4, now=WEEK1)
    assert retry.combat.fighters["enemy"].level == 5
    assert retry.combat.flavor == view.combat.flavor


async def test_level_is_held_in_the_band_of_the_resonance_region(database):
    await _make(database, level=30)
    await _schedule(database)
    view = await _service(database).start(ANA, 1, 4, now=WEEK1)
    assert view.combat.fighters["enemy"].level == 10
    screen = render_encounter(view)
    assert screen.keyboard.inline_keyboard[0][0].callback_data.startswith("crf:")


async def test_elite_first_victory_grants_its_feito_once(database):
    character_id = await _make(database)
    await _schedule(database)
    service = _service(database)
    result = await _win(database, service, 6, 4, WEEK6)
    assert result.feat == "Primeira vitória sobre a Multidão Repetida"
    assert result.xp == enemy_xp(10, "elite", player_level=10)
    again = await _win(database, service, 6, 4, WEEK6)
    assert (again.repeat, again.feat) == (True, None)
    async with database[1]() as session:
        feats = (
            await session.scalars(
                select(Achievement.achievement_id).where(Achievement.character_id == character_id)
            )
        ).all()
        assert feats == [ENCOUNTERS_BY_OBJECTIVE["cap_06_obj_04"].feat_id]


async def test_stale_or_foreign_combat_buttons_do_nothing(database):
    await _make(database)
    await _schedule(database)
    service = _service(database)
    view = await service.start(ANA, 1, 4, now=WEEK1)
    stale = await service.action(ANA, view.activity_id, view.combat.version + 7, "attack")
    assert isinstance(stale, CombatView) and stale.combat.version == view.combat.version
    assert await service.action(ANA, uuid4(), 1, "attack") is None
    assert await service.action(ANA + 1, view.activity_id, view.combat.version, "attack") is None
