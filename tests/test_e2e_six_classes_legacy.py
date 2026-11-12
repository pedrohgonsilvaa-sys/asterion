"""B7: E2E journey from public creation to Nv.60 and the first Legacy, per Class.

Each of the six Classes runs the same journey through the public application
services:

1. Creation (name, race, Class, confirmation) through ``CreationService``.
2. The scripted prologue tutorial and its combat through ``PrologueService``,
   then the first rest at the Braseiro through ``WorldService``.
3. A campaign checkpoint: P1–P34 and the Class Trial are recorded as completed
   rows, exactly as the per-chapter campaign tests seed them. Those chapters
   and the six Class Trials have their own playthrough tests; replaying all of
   them six times here would take hours.
4. The XP for levels 1→59 is credited and consolidated by a real Caçada
   victory on the Estrada das Cinzas (``RoadService``), which is the
   progression boundary that turns XP into levels.
5. Build at Nv.60: initial Caminho (``PathSelectionService``) and every
   Talent point (``TalentService``).
6. P35 and P36 played through ``AltosMissionService``. Their boss fights are
   resolved as victories, as in ``test_confins_p35``/``test_confins_p36``,
   because the Nv.60 kit balance is still being simulated (Trilha C item 6).
7. Walk back to the Nó Central and ascend at its permanent Braseiro through
   ``LegacyService`` (prepare + confirm). Braseiro travel never crosses
   regions, so the Ascensão must be allowed outside the Refúgio do Ocaso.
   The Ascensão returns the character to the Refúgio, and a post-Legacy
   Caçada on the Estrada das Cinzas grants reprogression XP.

Combat randomness (critical, dodge, block, racial duration) is fixed to
"never" so the real combats are deterministic.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application import scripted_combat
from asterion.application.altos_missions import (
    P34_CONTENT_VERSION,
    P34_ID,
    P35_ID,
    P36_ID,
    P36_REWARD_SOURCE,
    AltosMissionService,
)
from asterion.application.creation import CreationService
from asterion.application.legacy import (
    P36_CAMPAIGN_UNLOCK,
    REFUGE_BRAZIER,
    LegacyService,
)
from asterion.application.path_selection import PathSelectionService
from asterion.application.progression import level_xp
from asterion.application.prologue import PrologueService
from asterion.application.road import (
    CONFINS_CAMARA_REGENCIA_LABEL,
    CONFINS_NO_CENTRAL_LABEL,
    CONFINS_REGION_LABEL,
    REFUGE,
    ROAD,
    RoadService,
)
from asterion.application.talents import TalentService
from asterion.application.world import WorldService
from asterion.domain.combat_math import CombatRng
from asterion.domain.creation import CLASSES, RACES
from asterion.domain.legacy import legacy_xp_factor
from asterion.domain.paths import PATHS_BY_CLASS
from asterion.domain.prologue import POST_COMBAT_STAGE, PROFILE
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    LegacyAscensionRecord,
    LocationDiscovery,
    Quest,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import start_manual_hunt_after_no_match
from tests.helpers.tdo_playthrough import TDOPlaythrough

# Completed campaign chapters before P35, as the per-chapter tests seed them.
CAMPAIGN_CHECKPOINT_QUESTS = (
    ("P1", "Vozes na Estrada", 7, "tdo-1.0.2"),
    ("P24", "A Câmara da Matriz", 1, "varzeas-1.0.3"),
    ("P25", "O Peso Antigo", 9, "altos-1.0.1"),
    ("P26", "Ordens de Emergência", 8, "altos-1.0.1"),
    ("P27", "A Continuidade a Qualquer Custo", 7, "altos-1.0.1"),
    ("P28", "Os Desvelados", 8, "altos-1.0.1"),
    ("P29", "Antes da Convergência", 7, "altos-1.0.1"),
    ("P30", "O Colosso Cinéreo", 10, "altos-1.0.1"),
    ("P31", "Onde o Véu Afina", 8, "confins-1.0.0"),
    ("P32", "A Fratura", 6, "confins-1.0.0"),
    ("P33", "O Avesso", 6, "confins-1.0.0"),
    (P34_ID, "A Âncora Central", 6, P34_CONTENT_VERSION),
)
CAMPAIGN_CHECKPOINT_UNLOCKS = (
    "class_trial_completed",
    "hunt_manual.estrada_das_cinzas",
    "explore.estrada_das_cinzas",
    "region.varzeas_carmesins.available",
    "region.varzeas.camara_matriz.available",
    "unlock.location.altos.escarpa_cinza",
    "unlock.location.altos.abrigo_peso",
    "unlock.hunt.altos.escarpa",
    "unlock.explore.altos.escarpa",
    "unlock.location.altos.pontes_fuligem",
    "unlock.location.altos.pedreiras_suspensas",
    "unlock.location.altos.bastilha_carga",
    "unlock.hunt.altos.bastilha",
    "unlock.explore.altos.bastilha",
    "unlock.location.altos.coracao_colosso",
    "unlock.location.confins.marcha_nebulosa",
    "unlock.location.confins.ultimo_refugio",
    "unlock.location.confins.estradas_ausentes",
    "unlock.location.confins.fraturas_limiar",
    "unlock.location.confins.no_central",
)
CAMPAIGN_CHECKPOINT_LOCATIONS = (
    "location.altos.escarpa_cinza",
    "location.altos.abrigo_peso",
    "location.altos.pontes_fuligem",
    "location.altos.pedreiras_suspensas",
    "location.altos.bastilha_carga",
    "location.altos.coracao_colosso",
    "location.confins.marcha_nebulosa",
    "location.confins.ultimo_refugio",
    "location.confins.estradas_ausentes",
    "location.confins.fraturas_limiar",
    "location.confins.no_central",
)
CAMPAIGN_CHECKPOINT_BRAZIERS = (
    "tdo.brazier.estrada",
    REFUGE_BRAZIER,
    "bonfire.altos.escarpa",
    "bonfire.altos.abrigo",
    "bonfire.confins.marco_duplo",
    "bonfire.confins.testemunha",
    "bonfire.confins.estrada_conferida",
    "bonfire.confins.limiar_firme",
    "bonfire.confins.no_retorno",
)
XP_FOR_LEVEL_60 = sum(level_xp(level) for level in range(1, 60))


def _never(self, probability, purpose):
    """Deterministic draw: no critical, dodge, block or racial extension."""
    if not Decimal(0) <= probability <= Decimal(1):
        raise ValueError("Invalid probability")
    self.cursor += 1
    return False


def _terminal(result: str):
    """Resolve a scripted boss combat on the next action, like the P35/P36 tests."""

    def finish(combat, action, **_kwargs):
        updated = deepcopy(combat)
        updated.version += 1
        updated.result = result
        return updated

    return finish


async def _character(sessions, actor: int) -> Character:
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == "ocaso"
            )
        )
        assert character is not None
        return character


async def _create(sessions, actor: int, name: str, race_index: int, class_index: int):
    creation = CreationService(sessions, "ocaso")
    state = await creation.start(actor)
    assert state.step == "name"
    state = await creation.name(actor, name, update_id=1)
    assert state.step == "race", state
    for action in (f"r{race_index}", "choose", f"c{class_index}", "choose", "confirm"):
        state = await creation.callback(actor, state.id, state.version, action)
        assert state is not None
    assert state.step == "cinzas_na_estrada:intro", state
    assert (state.race, state.character_class) == (
        RACES[race_index],
        CLASSES[class_index],
    )
    return state


async def _play_prologue(sessions, actor: int):
    prologue = PrologueService(sessions, "ocaso", PROFILE)
    tutorial = await prologue.enter(actor)
    assert tutorial is not None and tutorial.combat is not None
    driver = TDOPlaythrough(actor, sessions)
    tutorial = await driver.combat_to_result(
        tutorial,
        lambda current, action: prologue.action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: PrologueService(sessions, "ocaso", PROFILE).resume(actor),
        label="B7 · prólogo",
    )
    assert tutorial.stage == POST_COMBAT_STAGE, tutorial.stage
    world = WorldService(sessions, "ocaso")
    brazier = await world.resume(actor)
    assert brazier is not None and brazier.kind == "brazier"
    ready = await world.rest(actor)
    assert ready is not None and ready.kind == "menu"


async def _seed_campaign_checkpoint(sessions, actor: int) -> None:
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor).with_for_update()
        )
        assert character is not None
        character_id = character.id
        existing_quests = set(
            (
                await session.scalars(
                    select(Quest.quest_id).where(Quest.character_id == character_id)
                )
            ).all()
        )
        for quest_id, title, step, version in CAMPAIGN_CHECKPOINT_QUESTS:
            if quest_id in existing_quests:
                quest = await session.scalar(
                    select(Quest).where(
                        Quest.character_id == character_id, Quest.quest_id == quest_id
                    )
                )
                quest.status, quest.step = "completed", step
                quest.progress = {**(quest.progress or {}), "completed": True}
                continue
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=quest_id,
                    title=title,
                    status="completed",
                    step=step,
                    content_version=version,
                    state_version=step,
                    progress={"completed": True},
                )
            )

        async def missing(model, column, values):
            present = set(
                (
                    await session.scalars(
                        select(column).where(model.character_id == character_id)
                    )
                ).all()
            )
            return [value for value in values if value not in present]

        for unlock_id in await missing(Unlock, Unlock.unlock_id, CAMPAIGN_CHECKPOINT_UNLOCKS):
            session.add(Unlock(character_id=character_id, unlock_id=unlock_id))
        for location_id in await missing(
            LocationDiscovery, LocationDiscovery.location_id, CAMPAIGN_CHECKPOINT_LOCATIONS
        ):
            session.add(
                LocationDiscovery(character_id=character_id, location_id=location_id)
            )
        for brazier_id in await missing(
            Brazier, Brazier.brazier_id, CAMPAIGN_CHECKPOINT_BRAZIERS
        ):
            session.add(Brazier(character_id=character_id, brazier_id=brazier_id))
        for creature_id in await missing(
            BestiaryEntry, BestiaryEntry.creature_id, ("dog_cinereo", "corvo_fuligem")
        ):
            session.add(
                BestiaryEntry(
                    character_id=character_id,
                    creature_id=creature_id,
                    bkp=7,
                    stage="observed",
                )
            )
            session.add(
                BestiaryEvidence(
                    character_id=character_id,
                    creature_id=creature_id,
                    evidence_id="first_observation",
                    category="observation",
                )
            )
        # XP earned across levels 1→59; the next Caçada boundary consolidates it.
        character.xp += XP_FOR_LEVEL_60


async def _hunt_on_road(sessions, actor: int, monkeypatch, label: str):
    road = RoadService(sessions, "ocaso")
    here = await road.resume(actor)
    assert here is not None, label
    if here.location != ROAD:
        here = await road.travel(actor, ROAD)
        assert here is not None and here.location == ROAD, label
    assert here.hunt_enabled, label
    rested = await road.rest(actor)
    assert rested is not None, label
    character = await _character(sessions, actor)
    assert character.hp == character.max_hp, label
    combat = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert combat is not None and combat.kind == "combat", label
    driver = TDOPlaythrough(actor, sessions)
    finished = await driver.combat_to_result(
        combat,
        lambda current, action: road.action(
            actor, current.activity_id, current.combat.version, action
        ),
        lambda: road.resume(actor),
        label=label,
    )
    assert finished.kind == "hunt_victory", (label, finished.kind)
    assert any(line.startswith("✨ XP") for line in finished.reward_lines), label
    await road.acknowledge_result(actor)
    back = await road.travel(actor, REFUGE)
    assert back is not None and back.location == REFUGE, label


async def _build_at_level_60(sessions, actor: int, character_class: str) -> None:
    character = await _character(sessions, actor)
    paths = PathSelectionService(sessions, "ocaso")
    chosen = await paths.choose_initial(
        actor,
        PATHS_BY_CLASS[character_class][0],
        character.combat_configuration_version,
    )
    assert chosen is not None and chosen.changed

    talents = TalentService(sessions, "ocaso")
    view = await talents.view(actor)
    assert view is not None and view.level == 60
    assert view.total_points > 0 and view.available_points == view.total_points
    for definition in TALENTS_BY_CLASS[character_class]:
        if view.available_points == 0:
            break
        mutation = await talents.acquire(
            actor, definition.talent_id, view.combat_configuration_version
        )
        assert mutation is not None and mutation.changed
        view = mutation.view
    assert view.available_points == 0, (character_class, view.available_points)


async def _play_p35_and_p36(sessions, actor: int, monkeypatch) -> None:
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        world = await session.get(WorldState, character.id)
        world.region = CONFINS_REGION_LABEL
        world.location = CONFINS_NO_CENTRAL_LABEL

    mission = AltosMissionService(sessions, "ocaso")
    road = RoadService(sessions, "ocaso")
    view = await mission.start_p35(actor)
    assert view is not None and view.status == "active" and view.quest_id == P35_ID
    for evidence in ("custodia_ancoras", "regencia_continuidade", "oposicao_desvelados"):
        view = await mission.advance(actor, view.state_version, f"record_chain_{evidence}")
        assert view is not None
    for evidence in (
        "pre_civil_deterioration",
        "anchors_stabilized",
        "growing_dependency_inequality",
        "coupled_convergence",
    ):
        view = await mission.advance(actor, view.state_version, f"verify_sequence_{evidence}")
        assert view is not None
    battle = await mission.start_solo_combat(actor, view.state_version, P35_ID)
    assert battle is not None and battle.combat is not None
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    view = await mission.action(actor, battle.activity_id, battle.combat.version, "attack")
    assert view is not None and view.step == 4
    for action in (
        "reconstruct_desvelados_sabotage",
        "record_cael_rhen_decision_context",
        "record_convergence_codices",
        "open_chamber_route",
        "conclude_with_sera",
    ):
        view = await mission.advance(actor, view.state_version, action)
        assert view is not None
    assert view.status == "completed"

    assert await road.travel_route(actor, CONFINS_CAMARA_REGENCIA_LABEL) is not None
    await mission.on_location(actor)
    p36 = await mission.resume_active(actor)
    assert p36 is not None and p36.quest_id == P36_ID and p36.status == "active"
    for evidence in ("institutional_record", "local_matter", "incompatible_states"):
        p36 = await mission.advance(actor, p36.state_version, f"record_chamber_{evidence}")
        assert p36 is not None
    for evidence in ("final_evidence_a", "final_evidence_b", "final_evidence_c"):
        p36 = await mission.advance(
            actor, p36.state_version, f"record_final_evidence_{evidence}"
        )
        assert p36 is not None
    assert p36.step == 3
    battle = await mission.start_solo_combat(actor, p36.state_version, P36_ID)
    assert battle is not None and battle.combat is not None
    assert battle.combat.fighters["enemy"].level == 60
    p36 = await mission.action(actor, battle.activity_id, battle.combat.version, "attack")
    assert p36 is not None and p36.step == 6
    p36 = await mission.advance(actor, p36.state_version, "record_regent_nature")
    p36 = await mission.advance(actor, p36.state_version, "record_regent_codices_and_recipe")
    assert p36 is not None and p36.step == 8
    p36 = await mission.choose_p36_reward(
        actor, p36.state_version, "selo_referencia_presente"
    )
    assert p36 is not None
    p36 = await mission.advance(actor, p36.state_version, "conclude_with_sera")
    assert p36 is not None and p36.status == "completed"
    monkeypatch.undo()


@pytest.mark.asyncio
@pytest.mark.parametrize("class_index", range(len(CLASSES)), ids=CLASSES)
async def test_creation_to_level_60_and_first_legacy(database, monkeypatch, class_index):
    character_class = CLASSES[class_index]
    race_index = class_index % len(RACES)
    actor = 7_600_000_000_000 + uuid4().int % 900_000_000_000
    sessions = database[1]
    monkeypatch.setattr(CombatRng, "chance", _never)

    created = await _create(sessions, actor, f"Jornada{chr(ord('a') + class_index)}",
                            race_index, class_index)
    await _play_prologue(sessions, actor)

    await _seed_campaign_checkpoint(sessions, actor)
    monkeypatch.setattr(CombatRng, "chance", _never)
    await _hunt_on_road(sessions, actor, monkeypatch, f"B7 · caçada Nv.60 · {character_class}")
    character = await _character(sessions, actor)
    assert (character.level, character.xp) == (60, 0)
    assert character.character_class == created.character_class == character_class

    await _build_at_level_60(sessions, actor, character_class)

    monkeypatch.setattr(CombatRng, "chance", _never)
    await _play_p35_and_p36(sessions, actor, monkeypatch)
    async with sessions() as session:
        character = await _character(sessions, actor)
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == P36_CAMPAIGN_UNLOCK,
            )
        ) is not None
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P36_REWARD_SOURCE,
            )
        ) is not None

    road = RoadService(sessions, "ocaso")
    assert await road.travel_route(actor, CONFINS_NO_CENTRAL_LABEL) is not None
    here = await road.resume(actor)
    assert here is not None and here.brazier_id == "bonfire.confins.no_retorno"

    legacy = LegacyService(sessions, "ocaso")
    view = await legacy.view(actor)
    assert view is not None and view.can_ascend, view.reasons
    prepared = await legacy.prepare(
        actor, expected_configuration_version=view.configuration_version
    )
    assert prepared is not None and prepared.confirmation_key is not None
    result = await legacy.confirm(actor, prepared.confirmation_key)
    assert result is not None and result.succeeded, result
    assert (result.legacy_level, result.level, result.xp) == (1, 1, 0)
    assert result.location == REFUGE
    async with sessions() as session:
        character = await _character(sessions, actor)
        assert character.legacy_level == 1
        assert await session.scalar(
            select(LegacyAscensionRecord.id).where(
                LegacyAscensionRecord.character_id == character.id
            )
        ) is not None

    monkeypatch.setattr(CombatRng, "chance", _never)
    assert legacy_xp_factor(1) == Decimal("1.75")
    await _hunt_on_road(sessions, actor, monkeypatch, f"B7 · reprogressão · {character_class}")
    character = await _character(sessions, actor)
    assert character.legacy_level == 1
    assert character.level > 1 or character.xp > 0
