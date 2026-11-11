"""Parte 6 of Crônica I: Códice (§6), Crônica Arquivada (§9) and the cr01 Bestiário."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, update

from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.application.chronicle import (
    ChronicleAdmin,
    ChronicleError,
    ChronicleService,
    record_objective,
)
from asterion.application.chronicle_encounters import (
    ChronicleEncounterService,
    EncounterResultView,
)
from asterion.application.prologue import CombatView
from asterion.application.road import RoadService
from asterion.application.scripted_combat import current_combat
from asterion.bot.character_surfaces_ui import (
    render_bestiary_root,
    render_codex_category,
    render_codex_root,
)
from asterion.bot.chronicle_ui import ARCHIVED_TEXT, render_chapter, render_chronicle
from asterion.domain.chronicle import Layer, Outcome, Phase, calendar_for, required_objectives
from asterion.domain.chronicle_codex import (
    ALTOS,
    ENTRIES,
    FRAGMENTS,
    allowed_fragments,
)
from asterion.domain.chronicle_content import OCASO
from asterion.domain.road import ROAD_LOCATION
from asterion.infrastructure.db.combat_codec import encode
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    BestiaryEntry,
    Character,
    ChronicleCompletion,
    ChronicleCycle,
    ChroniclePointGrant,
    CodexFragment,
    GameActivity,
    LocationDiscovery,
    Quest,
    RewardEvent,
    WorldState,
)

D = Decimal
SERVER = "ocaso"
DAY1 = date(2026, 12, 1)
CAL = calendar_for(DAY1)
BEFORE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEEK1 = CAL.starts_at + timedelta(hours=1)
RESCUE = CAL.finalization_at + timedelta(hours=1)
ARCHIVED = CAL.rescue_ends_at + timedelta(hours=1)
ANA = 950601
ROAD = "Estrada das Cinzas"

# Spoiler names that only a layer Trecho may carry (§0.2).
_SPOILERS = ("Nó Central", "Âncora Central", "Regência", "Desvelados", "Hemaris", "Avesso")

# ------------------------------------------------------------------ pure rules


def test_calendar_is_playable_while_active_and_once_archived_but_not_in_rescue():
    assert CAL.playable(WEEK1) and not CAL.archived(WEEK1)
    assert not CAL.playable(RESCUE)
    assert CAL.playable(ARCHIVED) and CAL.archived(ARCHIVED)
    assert not CAL.accepts_progress(ARCHIVED)


def test_base_texts_and_titles_never_name_a_layer_term():
    for item in FRAGMENTS:
        if item.layer is None:
            assert not any(name in item.text or name in item.title for name in _SPOILERS)
    for entry in ENTRIES:
        assert not any(name in entry.title for name in _SPOILERS)


def test_fragments_follow_chapters_layers_regions_and_the_outcome():
    ids = {item.fragment_id for item in allowed_fragments({1}, frozenset(), frozenset(), None)}
    assert ids == {
        "codex_cr01_ecos_t01",
        "codex_cr01_o_pulso_texto",
        "codex_cr01_formas_do_pulso_texto",
    }
    layered = allowed_fragments({1, 6}, frozenset({Layer.C1}), frozenset({ALTOS}), None)
    ids = {item.fragment_id for item in layered}
    assert "codex_cr01_o_pulso_c1" in ids
    assert "codex_cr01_formas_do_pulso_c4" not in ids
    assert {"codex_cr01_herdeiros_altos", "codex_cr01_herdeiros_texto"} <= ids
    assert "codex_cr01_herdeiros_confins" not in ids
    outcome = allowed_fragments({2}, frozenset({Layer.C4}), frozenset(), Outcome.DESTRUIR)
    ids = {item.fragment_id for item in outcome}
    assert {"codex_cr01_desfecho_destruir", "codex_cr01_desfecho_destruir_c4"} <= ids
    assert not {i for i in ids if i.startswith("codex_cr01_desfecho_selar")}
    # Nothing without a concluded chapter, the desfecho included (Dúvida 7).
    assert allowed_fragments(set(), frozenset(Layer), frozenset(), Outcome.SELAR) == ()


# ------------------------------------------------------------------- database


async def _make(database, *, level=10):
    async with database[1].begin() as session:
        await session.merge(Account(telegram_id=ANA))
        character = Character(
            telegram_id=ANA,
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
        session.add(WorldState(character_id=character.id, region=OCASO, location=ROAD))
        session.add(Quest(character_id=character.id, quest_id="P1", title="P1", status="completed"))
        return character.id


async def _schedule(database):
    await ChronicleAdmin(database[1], SERVER).set_day1(DAY1, "teste", now=BEFORE)


def _encounters(database):
    async def latest(_session, _character, region):
        return ROAD_LOCATION if region == OCASO else None

    road = RoadService(database[1], SERVER)
    return ChronicleEncounterService(database[1], SERVER, latest, road.recover_normal_pve_defeat)


async def _record(database, objective_id, now):
    async with database[1].begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == ANA).with_for_update()
        )
        return await record_objective(session, SERVER, character, objective_id, now=now)


async def _points(database) -> int:
    async with database[1]() as session:
        rows = await session.scalars(
            select(ChroniclePointGrant.points).where(ChroniclePointGrant.account_id == ANA)
        )
        return sum(rows.all())


async def _fragments(database, character_id) -> set[str]:
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )


async def _win(database, service, chapter, slot, now):
    view = await service.start(ANA, chapter, slot, now=now)
    assert isinstance(view, CombatView)
    async with database[1].begin() as session:
        activity = await session.get(GameActivity, view.activity_id)
        combat, _, record = await current_combat(session, activity)
        combat.fighters["enemy"].hp = D(1)
        record.snapshot = encode(combat)
    return await service.action(ANA, view.activity_id, view.combat.version, "attack", now=now)


async def test_rescue_period_plays_nothing_and_archive_plays_without_points(database):
    await _make(database)
    await _schedule(database)
    assert not await _record(database, "cap_01_obj_01", RESCUE)
    assert await _record(database, "cap_01_obj_01", ARCHIVED)
    assert await _points(database) == 0
    # The same objective is never recorded twice.
    assert not await _record(database, "cap_01_obj_01", ARCHIVED)


async def test_archived_encounter_gives_bestiary_and_objective_but_no_xp(database):
    character_id = await _make(database)
    await _schedule(database)
    service = _encounters(database)
    listed = await service.encounters(ANA, now=ARCHIVED)
    assert len(listed) == 8 and not any(item.repeat_open or item.in_group for item in listed)
    result = await _win(database, service, 1, 4, ARCHIVED)
    assert isinstance(result, EncounterResultView)
    assert (result.victory, result.xp, result.objective_completed) == (True, 0, True)
    assert result.trail_points == 0
    async with database[1]() as session:
        character = await session.get(Character, character_id)
        assert character.xp == 0
        assert await session.scalar(
            select(RewardEvent.id).where(RewardEvent.character_id == character_id)
        ) is None
        entry = await session.scalar(
            select(BestiaryEntry).where(BestiaryEntry.character_id == character_id)
        )
        assert (entry.creature_id, entry.wins) == ("creature.cr01.repetidor", 1)
    assert await _points(database) == 0
    # The Eco is a ``rep_cr01_*`` source: closed at the cutoff.
    with pytest.raises(ChronicleError):
        await service.start(ANA, 1, 4, now=ARCHIVED)


async def test_archived_elite_still_grants_its_feito(database):
    character_id = await _make(database)
    await _schedule(database)
    result = await _win(database, _encounters(database), 6, 4, ARCHIVED)
    assert result.feat is not None and result.xp == 0
    async with database[1]() as session:
        assert await session.scalar(
            select(Achievement.achievement_id).where(Achievement.character_id == character_id)
        ) == "feito_cr01_multidao"


async def test_conclusion_registers_codex_and_later_layers_and_desfecho(database):
    character_id = await _make(database)
    await _schedule(database)
    for objective_id in sorted(required_objectives(1)):
        assert await _record(database, objective_id, WEEK1)
    view = await ChronicleService(database[1], SERVER).conclude_chapter(ANA, 1, now=WEEK1)
    assert view.chapters[0].concluded
    assert await _fragments(database, character_id) == {
        "codex_cr01_ecos_t01",
        "codex_cr01_o_pulso_texto",
        "codex_cr01_formas_do_pulso_texto",
    }
    # P6 reached later: the C1 Trecho shows up the next time the Códice opens.
    async with database[1].begin() as session:
        session.add(Quest(character_id=character_id, quest_id="P6", title="P6", status="completed"))
        await session.execute(
            update(ChronicleCycle)
            .where(ChronicleCycle.server_id == SERVER)
            .values(outcome=Outcome.SELAR.value)
        )
    surfaces = CharacterSurfacesService(database[1], SERVER)
    knowledge = await surfaces.knowledge(ANA)
    held = await _fragments(database, character_id)
    assert "codex_cr01_o_pulso_c1" in held
    # The result is only published at T.
    assert not {item for item in held if item.startswith("codex_cr01_desfecho")}
    async with database[1].begin() as session:
        await session.execute(
            update(ChronicleCycle)
            .where(ChronicleCycle.server_id == SERVER)
            .values(end_at=datetime.now(UTC) - timedelta(hours=1))
        )
    knowledge = await surfaces.knowledge(ANA)
    held = await _fragments(database, character_id)
    assert "codex_cr01_desfecho_selar" in held
    assert "codex_cr01_desfecho_selar_c3" not in held
    titles = {entry.title for entry in knowledge.codex_entries}
    assert {"Ecos da Convergência", "O Pulso", "O Que Foi Respondido"} <= titles
    root = render_codex_root(knowledge).text
    assert "Crônicas" in root and "Mistérios e Fenômenos" in root


async def test_archived_conclusion_registers_codex_without_points(database):
    character_id = await _make(database)
    await _schedule(database)
    async with database[1].begin() as session:
        session.add(
            LocationDiscovery(character_id=character_id, location_id="tdo.location.ruinas_do_vigia")
        )
    for objective_id in sorted(required_objectives(2)):
        assert await _record(database, objective_id, ARCHIVED)
    service = ChronicleService(database[1], SERVER)
    view = await service.conclude_chapter(ANA, 2, now=ARCHIVED)
    assert view.phase is Phase.ARCHIVED and view.chapters[1].concluded
    assert await _points(database) == 0
    assert "codex_cr01_marcas_que_vibram_texto" in await _fragments(database, character_id)
    async with database[1]() as session:
        done = set(
            (
                await session.scalars(
                    select(ChronicleCompletion.objective_id).where(
                        ChronicleCompletion.character_id == character_id
                    )
                )
            ).all()
        )
    assert "cap_02_conclusao" in done
    assert ARCHIVED_TEXT in render_chronicle(view).text
    chapter = render_chapter(view, view.chapters[1]).text
    assert "pts" not in chapter
    knowledge = await CharacterSurfacesService(database[1], SERVER).knowledge(ANA)
    # A Crônica Entry of "Regiões e Locais" has no Local: listed by itself.
    assert "Marcas que Vibram" in render_codex_category(knowledge, "regions").text


async def test_cr01_creatures_have_their_own_bestiary_group(database):
    await _make(database)
    await _schedule(database)
    await _win(database, _encounters(database), 1, 4, WEEK1)
    knowledge = await CharacterSurfacesService(database[1], SERVER).knowledge(ANA)
    assert [record.name for record in knowledge.bestiary] == ["Repetidor"]
    text = render_bestiary_root(knowledge).text
    assert "Crônica I · Ecos da Convergência" in text
