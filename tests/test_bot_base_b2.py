from decimal import ROUND_FLOOR, Decimal
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage
from alembic.config import Config
from sqlalchemy import delete, select

from alembic import command
from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT, COSMETICS
from asterion.application.cosmetics import CosmeticMutationRejected, CosmeticService
from asterion.application.doctrines import DoctrineRejected, DoctrineService
from asterion.application.knowledge_catalog import ACHIEVEMENTS
from asterion.application.tdo_feats import (
    CRYPT_CLEAR,
    CRYPT_ID,
    GALLERIES_CLEAR,
    GALLERIES_ID,
    TDO_BASE_CREATURES,
    TDO_ELITES,
    TDO_GUARDIANS,
    TDO_MAIN_LOCATIONS,
    TDO_PERMANENT_BRAZIERS,
    reconcile_tdo_feats,
)
from asterion.bot.character_surfaces_handlers import character_surfaces_router
from asterion.bot.cosmetics_handlers import cosmetics_router
from asterion.bot.doctrines_handlers import doctrines_router
from asterion.bot.doctrines_ui import b36, render_doctrine_detail
from asterion.domain.arts import ART_IDS_BY_CLASS, DEVASTADOR_ART_IDS, VIGIA_ART_IDS
from asterion.domain.economy import crowns_per_level, path_switch_cost
from asterion.domain.equipment import assign_equipment_instance_id
from asterion.domain.road import materialize_equipment
from asterion.domain.talents import TALENTS_BY_CLASS
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Brazier,
    Character,
    CharacterCosmetic,
    CharacterTalentChoice,
    CodexEntry,
    CodexFragment,
    EquipmentItem,
    GameActivity,
    LocationDiscovery,
    Quest,
    Unlock,
)
from tests.helpers.weapon_metadata import add_compatible_weapon_for_arts
from tests.test_character_surfaces_telegram import _button, _last_screen, _message_update
from tests.test_creation_ui import callback_update
from tests.test_road_integration import _seed_road

FEAT_IDS = {item.achievement_id for item in ACHIEVEMENTS if item.player_facing}
TDO_FEAT_IDS = {item for item in FEAT_IDS if item.startswith("feat.tdo.")}
TDO_COSMETIC_BY_ACHIEVEMENT = {
    achievement_id: cosmetic
    for achievement_id, cosmetic in COSMETIC_BY_ACHIEVEMENT.items()
    if achievement_id.startswith("feat.tdo.")
}
EXPECTED_MISSING = {
    "prologue": {"feat.tdo.cinzas_na_estrada"},
    "wanderer": {"feat.tdo.andarilho_das_cinzas"},
    "wanderer_location": {
        "feat.tdo.andarilho_das_cinzas",
        "feat.tdo.terras_do_ocaso",
    },
    "hidden_depths": {"feat.tdo.sob_a_superficie"},
    "last_guard": {"feat.tdo.a_ultima_guarda"},
    "crypt_stable": {"feat.tdo.silencio_entre_os_nomes", "feat.tdo.nomes_sob_a_cinza"},
    "galleries_stable": {
        "feat.tdo.a_ordem_interrompida",
        "feat.tdo.a_ordem_ainda_permanece",
    },
    "fractured": {"feat.tdo.cinzas_fraturadas"},
    "bestiary_base": {
        "feat.tdo.cacador_do_ocaso",
        "feat.tdo.entre_aquilo_que_caca",
    },
    "variants": {"feat.tdo.entre_aquilo_que_caca"},
    "elites": {"feat.tdo.entre_aquilo_que_caca"},
    "guardians": {"feat.tdo.testemunha_dos_guardioes"},
    "names": {"feat.tdo.nomes_sob_a_cinza"},
    "orders": {"feat.tdo.a_ordem_ainda_permanece"},
    "campaign_level": {"feat.tdo.terras_do_ocaso"},
    "campaign_location": {
        "feat.tdo.andarilho_das_cinzas",
        "feat.tdo.terras_do_ocaso",
    },
    "complete": set(),
}


@pytest.mark.asyncio
async def test_fresh_postgresql_schema_matches_alembic_head(database):
    engine, _sessions = database
    async with engine.connect() as connection:

        def check(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.check(config)

        await connection.run_sync(check)


@pytest.mark.asyncio
async def test_0019_downgrade_refuses_cosmetic_data(database):
    actor = 890990
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        session.add(
            CharacterCosmetic(
                character_id=character.id,
                cosmetic_id="cosmetic.title.tdo.vigia_das_cinzas",
                cosmetic_type="title",
                source_achievement_id="feat.tdo.a_ultima_guarda",
            )
        )
    with pytest.raises(RuntimeError, match="character_cosmetics"):
        async with database[0].begin() as connection:

            def downgrade(sync_connection):
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                command.downgrade(config, "20261002_0018")

            await connection.run_sync(downgrade)
    async with sessions() as session:
        assert await session.scalar(
            select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.cosmetic_id == "cosmetic.title.tdo.vigia_das_cinzas"
            )
        ) is not None


async def _install_feat_facts(session, character_id, omission):
    character = await session.get(Character, character_id)
    character.level = 9 if omission == "campaign_level" else 10
    # The shared road seed includes a completed campaign fixture. An omission
    # case must start without the achievement it is meant to gate.
    if omission in EXPECTED_MISSING:
        await session.execute(
            delete(Achievement).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id.in_(EXPECTED_MISSING[omission]),
            )
        )
        await session.flush()
        if "feat.tdo.terras_do_ocaso" in EXPECTED_MISSING[omission]:
            assert await session.scalar(
                select(Achievement.id).where(
                    Achievement.character_id == character_id,
                    Achievement.achievement_id == "feat.tdo.terras_do_ocaso",
                )
            ) is None

    if omission != "prologue":
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="prologue_first_combat",
                status="completed",
                state_version=3,
                ruleset_version="gdd-1.4.7",
            )
        )

    if omission in {"wanderer_location", "campaign_location"}:
        # `_seed_road` may already have discovered the Ruins. Remove that
        # durable fact so these cases actually exercise the missing-location gate.
        await session.execute(
            delete(LocationDiscovery).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "tdo.location.ruinas_do_vigia",
            )
        )
    session.add_all(
        LocationDiscovery(character_id=character_id, location_id=location_id)
        for location_id in TDO_MAIN_LOCATIONS
        if not (
            omission in {"wanderer_location", "campaign_location"}
            and location_id == "tdo.location.ruinas_do_vigia"
        )
    )
    if omission in {"wanderer_location", "campaign_location"}:
        await session.flush()
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character_id,
                LocationDiscovery.location_id == "tdo.location.ruinas_do_vigia",
            )
        ) is None
        if omission == "campaign_location":
            known_main_locations = set(
                (
                    await session.scalars(
                        select(LocationDiscovery.location_id).where(
                            LocationDiscovery.character_id == character_id,
                            LocationDiscovery.location_id.in_(TDO_MAIN_LOCATIONS),
                        )
                    )
                ).all()
            )
            assert not TDO_MAIN_LOCATIONS.issubset(known_main_locations)
    session.add_all(
        Brazier(character_id=character_id, brazier_id=brazier_id)
        for brazier_id in TDO_PERMANENT_BRAZIERS
        if brazier_id not in {"tdo.brazier.estrada", "tdo.brazier.refugio_do_ocaso"}
        and not (omission == "wanderer" and brazier_id == "tdo.brazier.poente")
    )
    unlock_ids = {
        CRYPT_ID,
        GALLERIES_ID,
        f"{CRYPT_CLEAR}stable",
        f"{GALLERIES_CLEAR}stable",
        f"{CRYPT_CLEAR}fractured",
        f"{GALLERIES_CLEAR}fractured",
    }
    if omission == "hidden_depths":
        unlock_ids.remove(GALLERIES_ID)
    if omission == "crypt_stable":
        unlock_ids.remove(f"{CRYPT_CLEAR}stable")
    if omission == "galleries_stable":
        unlock_ids.remove(f"{GALLERIES_CLEAR}stable")
    if omission == "fractured":
        unlock_ids.remove(f"{GALLERIES_CLEAR}fractured")
    session.add_all(
        Unlock(character_id=character_id, unlock_id=unlock_id) for unlock_id in unlock_ids
    )

    for quest_id in ("P6", "S2", "S6"):
        if omission == "names" and quest_id == "S6":
            continue
        session.add(
            Quest(
                character_id=character_id,
                quest_id=quest_id,
                title=quest_id,
                status="completed",
                step=9 if quest_id == "P6" else 6,
            )
        )

    all_creatures = TDO_BASE_CREATURES | TDO_ELITES | TDO_GUARDIANS
    for creature_id in all_creatures:
        prior = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == creature_id,
            )
        )
        stage = "dominated"
        wins = 1 if creature_id == "vigia_partido" else 0
        if omission == "bestiary_base" and creature_id == "custodio_sem_rosto":
            stage = "studied"
        if omission == "elites" and creature_id in TDO_ELITES and creature_id not in {
            "alfa_cinereo",
            "viuva_fuligem",
        }:
            stage = "studied"
        if omission == "guardians" and creature_id == "vigia_partido":
            stage = "observed"
        if omission == "last_guard" and creature_id == "vigia_partido":
            wins = 0
        if prior is None:
            session.add(
                BestiaryEntry(
                    character_id=character_id,
                    creature_id=creature_id,
                    bkp=100,
                    stage=stage,
                    wins=wins,
                )
            )
        else:
            prior.stage = stage
            prior.bkp = 100
            prior.wins = wins

    variant_creatures = {
        "furious": "dog_cinereo",
        "resistant": "peregrino_calcinado",
        "agile": "corvo_fuligem",
        "hemorrhagic": "carnical_fuligem",
        "venomous": "aranha_cinza",
    }
    session.add_all(
        BestiaryEvidence(
            character_id=character_id,
            creature_id=creature_id,
            evidence_id=f"variant:{variant_type}",
            category="variant",
        )
        for variant_type, creature_id in variant_creatures.items()
        if not (omission == "variants" and variant_type == "venomous")
    )

    entry_ids = {
        "codex.history.os_sem_nome",
        "codex.history.primeiro_selo",
        "codex.history.ordens_que_permanecem",
        "codex.mystery.ancora_do_poente",
    }
    session.add_all(CodexEntry(character_id=character_id, entry_id=item) for item in entry_ids)
    fragments = {
        ("codex.history.os_sem_nome", "codex.fragment.crypt.sem_nome"),
        ("codex.history.primeiro_selo", "codex.fragment.galleries.first_seal"),
        ("codex.history.ordens_que_permanecem", "codex.fragment.galleries.orders_remain"),
        (
            "codex.mystery.ancora_do_poente",
            "codex.fragment.ancora_do_poente.nome_registrado",
        ),
    }
    if omission == "orders":
        fragments.remove(
            ("codex.history.ordens_que_permanecem", "codex.fragment.galleries.orders_remain")
        )
    session.add_all(
        CodexFragment(character_id=character_id, entry_id=entry_id, fragment_id=fragment_id)
        for entry_id, fragment_id in fragments
    )


@pytest.mark.asyncio
async def test_all_thirteen_tdo_feats_reconcile_from_facts_and_backfill_cosmetics(database):
    actors = range(891000, 891000 + len(EXPECTED_MISSING))
    character_ids = {}
    for index, actor in enumerate(actors):
        await _seed_road(database, actor=actor)
        async with database[1].begin() as session:
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            character.name = f"Hero{chr(ord('b') + index)}"
            omission = (
                "complete"
                if index == len(EXPECTED_MISSING) - 1
                else tuple(EXPECTED_MISSING)[index]
            )
            character_ids[omission] = character.id
            if omission == "prologue":
                # A real legacy post-prologue state is a valid backfill fact;
                # keep this omission in a pre-prologue synthetic state.
                character.stage = "creation:complete"

    initial = await CharacterSurfacesService(database[1], "ocaso").knowledge(891000)
    assert initial is not None
    hidden_ids = {
        "feat.tdo.sob_a_superficie",
        "feat.tdo.entre_aquilo_que_caca",
        "feat.tdo.nomes_sob_a_cinza",
        "feat.tdo.a_ordem_ainda_permanece",
    }
    assert hidden_ids.isdisjoint(item.achievement_id for item in initial.achievements)

    before = {}
    for omission, character_id in character_ids.items():
        async with database[1].begin() as session:
            character = await session.get(Character, character_id)
            before[omission] = (character.xp, character.crowns)
            await _install_feat_facts(session, character_id, omission)

    for omission, character_id in character_ids.items():
        async with database[1].begin() as session:
            character = await session.get(Character, character_id)
            awarded = await reconcile_tdo_feats(session, character)
            if omission == "complete":
                assert set(awarded) == TDO_FEAT_IDS
            else:
                assert not EXPECTED_MISSING[omission].intersection(awarded)
            assert len(set(awarded)) == len(awarded)

        async with database[1]() as session:
            found = set(
                (
                    await session.scalars(
                        select(Achievement.achievement_id).where(
                            Achievement.character_id == character_id
                        )
                    )
                ).all()
            )
            expected_missing = EXPECTED_MISSING[omission]
            assert TDO_FEAT_IDS - expected_missing <= found, omission
            assert not (expected_missing & found)
            cosmetics = list(
                (
                    await session.scalars(
                        select(CharacterCosmetic.cosmetic_id).where(
                            CharacterCosmetic.character_id == character_id
                        )
                    )
                ).all()
            )
            expected_cosmetics = len(TDO_COSMETIC_BY_ACHIEVEMENT) - len(
                expected_missing.intersection(TDO_COSMETIC_BY_ACHIEVEMENT)
            )
            assert len(cosmetics) == expected_cosmetics
            character = await session.get(Character, character_id)
            assert (character.xp, character.crowns) == before[omission]

        async with database[1].begin() as session:
            character = await session.get(Character, character_id)
            assert await reconcile_tdo_feats(session, character) == ()

    assert len(TDO_FEAT_IDS) == 13
    assert len([
        item for item in COSMETICS
        if item.achievement_id is not None and item.achievement_id.startswith("feat.tdo.")
    ]) == 12


@pytest.mark.asyncio
async def test_cosmetic_selection_is_owned_stale_safe_and_profile_only(database):
    actor = 891100
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character_id = character.id
        session.add(
            Achievement(character_id=character_id, achievement_id="feat.tdo.a_ultima_guarda")
        )
        version = character.combat_configuration_version
        hp = character.hp
        max_hp = character.max_hp
        xp, crowns = character.xp, character.crowns
        await reconcile_tdo_feats(session, character)

    cosmetics = CosmeticService(sessions, "ocaso")
    view = await cosmetics.view(actor)
    assert view is not None
    titles = next(item for item in view.categories if item.cosmetic_type == "title")
    assert [item.name for item in titles.items] == ["Vigia das Cinzas"]
    cosmetic_id = titles.items[0].cosmetic_id
    result = await cosmetics.select(actor, cosmetic_id, None)
    assert result is not None and result.changed
    assert await cosmetics.select(actor, cosmetic_id, cosmetic_id) is not None
    with pytest.raises(CosmeticMutationRejected):
        await cosmetics.select(actor, COSMETICS[0].cosmetic_id, None)
    with pytest.raises(CosmeticMutationRejected):
        await cosmetics.select(actor, cosmetic_id, None)

    profile = await CharacterSurfacesService(sessions, "ocaso").profile(actor)
    assert profile is not None and profile.selected_title == "Vigia das Cinzas"
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert (character.combat_configuration_version, character.hp, character.max_hp) == (
            version,
            hp,
            max_hp,
        )
        assert (character.xp, character.crowns) == (xp, crowns)


@pytest.mark.asyncio
async def test_doctrines_snapshot_apply_cost_noop_foreground_and_limit(database):
    actor = 891200
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 10
        character.selected_path = "bastiao"
        character.hp = Decimal("351")
        character.max_hp = Decimal("702")
        character.crowns = 20_000
        session.add(Unlock(character_id=character.id, unlock_id="class_trial_completed"))
        talent = next(
            item
            for item in TALENTS_BY_CLASS["sentinela"]
            if item.level == 5 and item.attack_percent
        )
        session.add(
            CharacterTalentChoice(
                character_id=character.id,
                point_slot=1,
                talent_id=talent.talent_id,
            )
        )
        await add_compatible_weapon_for_arts(
            session, character.id, (ART_IDS_BY_CLASS["sentinela"][0],)
        )
        character_id = character.id

    service = DoctrineService(sessions, "ocaso")
    initial = await service.view(actor)
    assert initial is not None and not initial.foreground
    version = initial.configuration_version
    created = await service.create(actor, "Guarda Cinzenta", version)
    assert created is not None and created.changed
    doctrine_id = created.doctrine_id
    assert doctrine_id is not None
    created_view = await service.view(actor)
    assert created_view is not None
    doctrine = next(item for item in created_view.doctrines if item.doctrine_id == doctrine_id)
    assert doctrine.is_current

    path_change = await service.update_component(
        actor, doctrine_id, doctrine.revision, version, "path", "devastador"
    )
    assert path_change is not None and path_change.changed
    edit_view = await service.view(actor)
    doctrine = next(item for item in edit_view.doctrines if item.doctrine_id == doctrine_id)
    unchanged = await service.update_component(
        actor,
        doctrine_id,
        doctrine.revision,
        version,
        "path",
        "devastador",
    )
    assert unchanged is not None and not unchanged.changed
    assert (await service.view(actor)).configuration_version == version
    doctrine = next(
        item for item in (await service.view(actor)).doctrines if item.doctrine_id == doctrine_id
    )
    no_talents = await service.update_component(
        actor, doctrine_id, doctrine.revision, version, "talents", []
    )
    assert no_talents is not None and no_talents.changed
    doctrine = next(
        item for item in (await service.view(actor)).doctrines if item.doctrine_id == doctrine_id
    )
    assert doctrine.incomplete_reason is None and doctrine.can_apply

    initial_crowns = 20_000
    required_cost = path_switch_cost(10) + 2 * crowns_per_level(10)
    applied = await service.apply(actor, doctrine_id, doctrine.revision, version)
    assert applied is not None and applied.changed
    assert applied.configuration_version == version + 1
    assert applied.configuration_version == 1
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.crowns == initial_crowns - required_cost
        assert character.selected_path == "devastador"
        expected_hp = (Decimal("351") * character.max_hp / Decimal("702")).to_integral_value(
            rounding=ROUND_FLOOR
        )
        assert character.hp == expected_hp
        assert await session.scalar(
            select(CharacterTalentChoice.point_slot).where(
                CharacterTalentChoice.character_id == character_id
            )
        ) is None
    current = await service.view(actor)
    doctrine = next(item for item in current.doctrines if item.doctrine_id == doctrine_id)
    assert doctrine.is_current
    replay = await service.apply(
        actor, doctrine_id, doctrine.revision, current.configuration_version
    )
    assert replay is not None and not replay.changed
    assert (await service.view(actor)).configuration_version == 1

    art_id = ART_IDS_BY_CLASS["sentinela"][0]
    for index in range(2, 6):
        result = await service.create(actor, f"Doutrina {index}", 1)
        assert result is not None and result.changed
    with pytest.raises(DoctrineRejected, match="limit"):
        await service.create(actor, "Sexta Doutrina", 1)

    root = await service.view(actor)
    empty_doctrine = next(item for item in root.doctrines if item.name == "Doutrina 2")
    edited_art = await service.update_component(
        actor, empty_doctrine.doctrine_id, empty_doctrine.revision, 1, "arts", ("1", art_id)
    )
    assert edited_art is not None and edited_art.changed
    art_view = next(
        item
        for item in (await service.view(actor)).doctrines
        if item.doctrine_id == empty_doctrine.doctrine_id
    )
    applied_art = await service.apply(actor, art_view.doctrine_id, art_view.revision, 1)
    assert (
        applied_art is not None
        and applied_art.changed
        and applied_art.configuration_version == 2
    )

    saved_for_overwrite = next(
        item for item in (await service.view(actor)).doctrines if item.name == "Doutrina 3"
    )
    overwritten = await service.overwrite_current(
        actor, saved_for_overwrite.doctrine_id, saved_for_overwrite.revision, 2
    )
    assert overwritten is not None and overwritten.changed
    overwrite_view = await service.view(actor)
    saved_for_overwrite = next(
        item
        for item in overwrite_view.doctrines
        if item.doctrine_id == saved_for_overwrite.doctrine_id
    )
    assert saved_for_overwrite.is_current
    repeated_overwrite = await service.overwrite_current(
        actor, saved_for_overwrite.doctrine_id, saved_for_overwrite.revision, 2
    )
    assert repeated_overwrite is not None and not repeated_overwrite.changed
    assert (await service.view(actor)).configuration_version == 2

    assert await service.begin_name_input(
        actor,
        "rename",
        12345,
        2,
        doctrine_id=saved_for_overwrite.doctrine_id,
        expected_revision=saved_for_overwrite.revision,
    )
    renamed = await service.save_name_reply(actor, 12345, "  Guarda Atual  ")
    assert renamed is not None and renamed.changed
    with pytest.raises(DoctrineRejected, match="stale_input"):
        await service.save_name_reply(actor, 12345, "resposta antiga")
    rename_view = await service.view(actor)
    renamed_view = next(
        item
        for item in rename_view.doctrines
        if item.doctrine_id == saved_for_overwrite.doctrine_id
    )
    assert renamed_view.name == "Guarda Atual"

    doctrine_to_delete = next(
        item for item in rename_view.doctrines if item.name == "Doutrina 4"
    )
    deleted = await service.delete(
        actor, doctrine_to_delete.doctrine_id, doctrine_to_delete.revision
    )
    assert deleted is not None and deleted.changed
    assert (await service.view(actor)).configuration_version == 2

    async with sessions.begin() as session:
        session.add(
            GameActivity(
                character_id=character_id,
                content_id="b2_foreground_test",
                status="active",
                state_version=0,
                ruleset_version="gdd-1.4.7",
            )
        )
    locked_view = await service.view(actor)
    assert locked_view is not None and locked_view.foreground
    with pytest.raises(DoctrineRejected, match="foreground"):
        await service.update_component(
            actor, art_view.doctrine_id, art_view.revision, 2, "arts", ("1", None)
        )
    with pytest.raises(DoctrineRejected, match="foreground"):
        await service.apply(actor, art_view.doctrine_id, art_view.revision, 2)
    async with sessions.begin() as session:
        activity = await session.scalar(
            select(GameActivity).where(GameActivity.content_id == "b2_foreground_test")
        )
        activity.status = "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actor", "art_id", "character_class", "selected_path", "incompatible_weapon"),
    [
        (
            891240,
            DEVASTADOR_ART_IDS["ariete"],
            "sentinela",
            "devastador",
            "weapon.type.tdo.arma_pesada_caminhante",
        ),
        (
            891241,
            VIGIA_ART_IDS["tiro_calculado"],
            "vigia",
            "atirador",
            "weapon.type.tdo.arma_caminhante",
        ),
    ],
)
async def test_doctrine_rejects_art_with_incompatible_saved_weapon(
    database, actor, art_id, character_class, selected_path, incompatible_weapon
):
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        character.level = 20
        character.character_class = character_class
        character.selected_path = selected_path
        character.crowns = 20_000
        session.add(Unlock(character_id=character.id, unlock_id="class_trial_completed"))
        await add_compatible_weapon_for_arts(session, character.id, (art_id,))
        bow_payload = materialize_equipment(
            f"doctrine-incompatible-weapon-{actor}",
            "Comum",
            20,
            weapon_type_id=incompatible_weapon,
        )
        bow_id, bow_payload = assign_equipment_instance_id(bow_payload)
        session.add(
            EquipmentItem(
                id=bow_id,
                character_id=character.id,
                source_key=f"test:doctrine-incompatible-weapon:{actor}",
                item_name=bow_payload["item_name"],
                rarity=bow_payload["rarity"],
                slot=bow_payload["slot"],
                item_level=bow_payload["item_level"],
                bound=False,
                payload=bow_payload,
            )
        )

    service = DoctrineService(sessions, "ocaso")
    initial = await service.view(actor)
    assert initial is not None
    created = await service.create(
        actor, f"Arte incompatível {actor}", initial.configuration_version
    )
    assert created is not None and created.doctrine_id is not None
    doctrine = next(
        item for item in (await service.view(actor)).doctrines
        if item.doctrine_id == created.doctrine_id
    )
    equipped_art = await service.update_component(
        actor,
        doctrine.doctrine_id,
        doctrine.revision,
        initial.configuration_version,
        "arts",
        ("1", art_id),
    )
    assert equipped_art is not None and equipped_art.changed
    doctrine = next(
        item for item in (await service.view(actor)).doctrines
        if item.doctrine_id == created.doctrine_id
    )
    applied_melee = await service.apply(
        actor,
        doctrine.doctrine_id,
        doctrine.revision,
        initial.configuration_version,
    )
    assert applied_melee is not None and applied_melee.changed
    assert applied_melee.configuration_version == initial.configuration_version + 1
    doctrine = next(
        item for item in (await service.view(actor)).doctrines
        if item.doctrine_id == created.doctrine_id
    )
    selected_bow = await service.update_component(
        actor,
        doctrine.doctrine_id,
        doctrine.revision,
        applied_melee.configuration_version,
        "equipment",
        ("Principal", bow_id),
    )
    assert selected_bow is not None and selected_bow.changed
    doctrine = next(
        item for item in (await service.view(actor)).doctrines
        if item.doctrine_id == created.doctrine_id
    )
    assert doctrine.incomplete_reason == "weapon_requirement"
    assert not doctrine.can_apply
    with pytest.raises(DoctrineRejected, match="weapon_requirement"):
        await service.apply(
            actor,
            doctrine.doctrine_id,
            doctrine.revision,
            applied_melee.configuration_version,
        )


@pytest.mark.asyncio
async def test_doctrine_rejects_two_hand_conflict_and_missing_item(database):
    actor = 891250
    await _seed_road(database, actor=actor)
    sessions = database[1]
    item_ids = []
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 10
        for label, slot in (("Pesada", "2H"), ("Secundária", "Secundária")):
            payload = materialize_equipment(
                f"doctrine-2h-{label}",
                "Comum",
                10,
                forced_name=f"Arma {label}",
                forced_slot=slot,
            )
            item_id, payload = assign_equipment_instance_id(payload)
            item_ids.append(item_id)
            session.add(
                EquipmentItem(
                    id=item_id,
                    character_id=character.id,
                    source_key=f"b2:doctrine-2h:{label}",
                    item_name=payload["item_name"],
                    rarity=payload["rarity"],
                    slot=payload["slot"],
                    item_level=payload["item_level"],
                    bound=False,
                    payload=payload,
                )
            )

    service = DoctrineService(sessions, "ocaso")
    view = await service.view(actor)
    created = await service.create(actor, "Mãos Ocupadas", view.configuration_version)
    doctrine_id = created.doctrine_id
    doctrine = (await service.view(actor)).doctrines[0]
    await service.update_component(
        actor,
        doctrine_id,
        doctrine.revision,
        view.configuration_version,
        "equipment",
        ("Principal", item_ids[0]),
    )
    doctrine = (await service.view(actor)).doctrines[0]
    await service.update_component(
        actor,
        doctrine_id,
        doctrine.revision,
        view.configuration_version,
        "equipment",
        ("Secundária", item_ids[1]),
    )
    doctrine = (await service.view(actor)).doctrines[0]
    assert doctrine.incomplete_reason == "invalid_equipment" and not doctrine.can_apply

    await service.update_component(
        actor,
        doctrine_id,
        doctrine.revision,
        view.configuration_version,
        "equipment",
        ("Secundária", None),
    )
    doctrine = (await service.view(actor)).doctrines[0]
    assert doctrine.incomplete_reason is None and doctrine.can_apply
    async with sessions.begin() as session:
        await session.delete(await session.get(EquipmentItem, item_ids[0]))
    doctrine = (await service.view(actor)).doctrines[0]
    assert doctrine.incomplete_reason == "item_unavailable" and not doctrine.can_apply
    assert "⚠️ Item Indisponível" in render_doctrine_detail(await service.view(actor), doctrine).text


@pytest.mark.asyncio
async def test_cosmetic_and_doctrine_telegram_flows_use_real_callbacks(database):
    actor = 891300
    await _seed_road(database, actor=actor)
    sessions = database[1]
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        await add_compatible_weapon_for_arts(
            session, character.id, (ART_IDS_BY_CLASS["sentinela"][0],)
        )
        session.add(
            Achievement(character_id=character.id, achievement_id="feat.tdo.a_ultima_guarda")
        )
        await reconcile_tdo_feats(session, character)

    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(
        character_surfaces_router(CharacterSurfacesService(sessions, "ocaso"), {})
    )
    dispatcher.include_router(cosmetics_router(CosmeticService(sessions, "ocaso"), {}))
    dispatcher.include_router(doctrines_router(DoctrineService(sessions, "ocaso"), {}))
    bot = Bot("123456:local-test-token")
    message_ids = iter(range(900, 940))
    sent_prompt_ids = []

    async def telegram_response(_bot, method, **_kwargs):
        if isinstance(method, SendMessage):
            message_id = next(message_ids)
            if method.reply_markup is not None and method.reply_markup.force_reply:
                sent_prompt_ids.append(message_id)
            return TelegramMessage(
                message_id=message_id,
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        if isinstance(method, EditMessageText):
            return TelegramMessage(
                message_id=method.message_id,
                date=1,
                chat=Chat(id=actor, type="private"),
                from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                text=method.text,
            )
        return True

    bot.session.make_request = AsyncMock(side_effect=telegram_response)
    update_id = 1
    await dispatcher.feed_raw_update(
        bot, callback_update("character:root", actor=actor, update_id=update_id)
    )
    screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(_button(screen, "Cosméticos").callback_data, actor=actor, update_id=2),
    )
    screen = _last_screen(bot)
    assert "Cosméticos" in screen.text
    await dispatcher.feed_raw_update(
        bot, callback_update("cos:c:1", actor=actor, update_id=3)
    )
    screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot, callback_update(_button(screen, "1").callback_data, actor=actor, update_id=4)
    )
    screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(_button(screen, "Usar Título").callback_data, actor=actor, update_id=5),
    )
    screen = _last_screen(bot)
    assert "Vigia das Cinzas" in screen.text
    await dispatcher.feed_raw_update(
        bot, callback_update("character:root", actor=actor, update_id=6)
    )
    character_screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(
            _button(character_screen, "Perfil").callback_data, actor=actor, update_id=7
        ),
    )
    assert "🎖️ Vigia das Cinzas" in _last_screen(bot).text

    await dispatcher.feed_raw_update(
        bot, callback_update("character:root", actor=actor, update_id=8)
    )
    screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(_button(screen, "Doutrinas").callback_data, actor=actor, update_id=9),
    )
    screen = _last_screen(bot)
    await dispatcher.feed_raw_update(
        bot,
        callback_update(_button(screen, "Nova Doutrina").callback_data, actor=actor, update_id=10),
    )
    assert sent_prompt_ids
    prompt_id = sent_prompt_ids[-1]
    reply_to = {
        "message_id": prompt_id,
        "date": 1,
        "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
        "chat": {"id": actor, "type": "private"},
        "text": "Responda a esta mensagem com o nome da Doutrina.",
    }
    await dispatcher.feed_raw_update(
        bot,
        _message_update("Guarda da Estrada", actor=actor, update_id=11, reply_to=reply_to),
    )
    screen = _last_screen(bot)
    assert "Guarda da Estrada" in screen.text
    assert "Configuração Atual" in screen.text

    doctrine_service = DoctrineService(sessions, "ocaso")
    doctrine_view = await doctrine_service.view(actor)
    saved = doctrine_view.doctrines[0]
    art_id = ART_IDS_BY_CLASS["sentinela"][0]
    await doctrine_service.update_component(
        actor,
        saved.doctrine_id,
        saved.revision,
        doctrine_view.configuration_version,
        "arts",
        ("1", art_id),
    )
    edited_view = await doctrine_service.view(actor)
    edited = edited_view.doctrines[0]
    apply_callback = (
        f"doc:ap:{edited.doctrine_id.hex}:"
        f"{b36(edited.revision)}:{b36(edited_view.configuration_version)}"
    )
    await dispatcher.feed_raw_update(
        bot, callback_update(apply_callback, actor=actor, update_id=12)
    )
    applied_screen = _last_screen(bot)
    assert "Configuração Atual" in applied_screen.text
    assert "Confirmar Aplicação" not in applied_screen.text
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character.combat_configuration_version == edited_view.configuration_version + 1
    for call in bot.session.make_request.call_args_list:
        method = call.args[1]
        markup = getattr(method, "reply_markup", None)
        if markup and getattr(markup, "inline_keyboard", None):
            for row in markup.inline_keyboard:
                for button in row:
                    assert len(button.callback_data.encode("utf-8")) < 64
    await bot.session.close()
