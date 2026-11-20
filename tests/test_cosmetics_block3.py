"""Bloco 3 — Cosméticos: 3 categorias, legados TDO, Aparência padrão e fallback."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from asterion.application.cosmetic_catalog import (
    COSMETIC_TYPES,
    COSMETICS,
    COSMETICS_BY_ID,
    DEFAULT_APPEARANCE_NAME,
    LEGACY_COSMETIC_CONVERSIONS,
    RETIRED_LEGACY_COSMETICS,
)
from asterion.application.cosmetics import CosmeticMutationRejected, CosmeticService
from asterion.bot.cosmetics_ui import (
    render_cosmetic_category,
    render_cosmetic_default_appearance,
    render_cosmetic_detail,
    render_cosmetics_root,
)
from asterion.infrastructure.db.models import (
    Character,
    CharacterCosmetic,
    CharacterCosmeticSelection,
    CharacterEquipmentSlot,
    EquipmentItem,
)
from tests.test_road_integration import _seed_road

MIGRATION = (
    Path(__file__).parents[1] / "alembic/versions/20261119_0054_convert_legacy_tdo_cosmetics.py"
)
NOME_APAGADO = "cosmetic.title.tdo.nome_apagado"
OCASO = "cosmetic.frame.tdo.ocaso"
OLD_NOME = "cosmetic.emblem.tdo.nome_apagado"
OLD_OCASO = "cosmetic.banner.tdo.ocaso"
APPEARANCE = "cosmetic.appearance.tdo.errante_das_cinzas"
TITLE = "cosmetic.title.tdo.vigia_das_cinzas"
FRAME = "cosmetic.frame.tdo.pedra_fraturada"


def _texts(screen) -> str:
    return (
        screen.text
        + "\n"
        + "\n".join(button.text for row in screen.keyboard.inline_keyboard for button in row)
    )


def _view_stub(selected=None, items=()):
    from asterion.application.cosmetics import (
        CosmeticCategoryView,
        CosmeticItemView,
        CosmeticsView,
    )

    def item(cosmetic_id):
        d = COSMETICS_BY_ID[cosmetic_id]
        return CosmeticItemView(cosmetic_id, d.cosmetic_type, d.name, d.achievement_id)

    categories = []
    for kind in COSMETIC_TYPES:
        sel = (
            item(selected) if selected and COSMETICS_BY_ID[selected].cosmetic_type == kind else None
        )
        its = tuple(
            item(i) for i in items if COSMETICS_BY_ID[i].cosmetic_type == kind and i != selected
        )
        categories.append(CosmeticCategoryView(kind, sel, its))
    return CosmeticsView("Hero", tuple(categories))


# --- catálogo e UI (sem banco) -------------------------------------------------


def test_catalog_has_exactly_three_categories_and_no_legacy_types():
    assert COSMETIC_TYPES == ("appearance", "title", "frame")
    assert {item.cosmetic_type for item in COSMETICS} <= set(COSMETIC_TYPES)
    assert not any(".emblem." in i or ".banner." in i for i in COSMETICS_BY_ID)


def test_hub_shows_exactly_three_categories_with_opening_phrase():
    screen = render_cosmetics_root(_view_stub())
    text_ = _texts(screen)
    assert "Escolha como seu personagem se apresenta em Asterion" in screen.text
    for label in ("🧍 Aparência · Visual", "🎖️ Título · Identidade", "🖼️ Moldura · Perfil"):
        assert label in screen.text
    assert "Emblema" not in text_ and "Banner" not in text_
    category_buttons = [
        b
        for row in screen.keyboard.inline_keyboard
        for b in row
        if b.callback_data.startswith("cos:c:")
    ]
    assert [b.callback_data for b in category_buttons] == ["cos:c:0", "cos:c:1", "cos:c:2"]


def test_category_screens_have_no_selected_label_nor_unsourced_origin():
    view = _view_stub(selected=TITLE, items=[TITLE, "cosmetic.title.varzeas.andarilho_da_salmoura"])
    title = render_cosmetic_category(view.categories[1])
    assert "Selecionado" not in title.text
    assert "Concessão não definida" not in title.text
    assert title.text.index("Vigia das Cinzas") < title.text.index("Outros Títulos")
    assert "Andarilho da Salmoura" in title.text  # sem Feito: aparece sem origem inventada
    for category in view.categories:
        assert "Emblema" not in render_cosmetic_category(category).text
        assert "Banner" not in render_cosmetic_category(category).text


def test_use_buttons_follow_ui():
    view = _view_stub(items=[APPEARANCE, TITLE, FRAME])
    for kind, expected in (
        ("appearance", "Equipar"),
        ("title", "Usar Título"),
        ("frame", "Usar Moldura"),
    ):
        category = next(c for c in view.categories if c.cosmetic_type == kind)
        index = next(
            i for i, d in enumerate(COSMETICS) if d.cosmetic_id == category.items[0].cosmetic_id
        )
        labels = [
            b.text
            for row in render_cosmetic_detail(view, index).keyboard.inline_keyboard
            for b in row
        ]
        assert expected in labels


def test_default_appearance_is_the_absence_of_a_selection_not_a_catalog_entry():
    assert all(DEFAULT_APPEARANCE_NAME != d.name for d in COSMETICS)
    nothing = render_cosmetic_category(_view_stub().categories[0])
    assert nothing.text.count(DEFAULT_APPEARANCE_NAME) == 1  # destaque no topo
    assert "Equipar" not in _texts(render_cosmetic_default_appearance(_view_stub()))
    other = _view_stub(selected=APPEARANCE, items=[APPEARANCE])
    listed = render_cosmetic_category(other.categories[0])
    assert listed.text.index("Errante das Cinzas") < listed.text.index(DEFAULT_APPEARANCE_NAME)
    assert "Equipar" in _texts(render_cosmetic_default_appearance(other))


def test_legacy_conversion_and_retirement_catalog():
    assert LEGACY_COSMETIC_CONVERSIONS == {OLD_NOME: NOME_APAGADO, OLD_OCASO: OCASO}
    assert COSMETICS_BY_ID[NOME_APAGADO].cosmetic_type == "title"
    assert COSMETICS_BY_ID[NOME_APAGADO].achievement_id == "feat.tdo.nomes_sob_a_cinza"
    assert COSMETICS_BY_ID[OCASO].cosmetic_type == "frame"
    assert COSMETICS_BY_ID[OCASO].achievement_id == "feat.tdo.terras_do_ocaso"
    assert len(RETIRED_LEGACY_COSMETICS) == 4
    assert not set(RETIRED_LEGACY_COSMETICS) & set(COSMETICS_BY_ID)
    assert OLD_NOME not in COSMETICS_BY_ID and OLD_OCASO not in COSMETICS_BY_ID


# --- banco ---------------------------------------------------------------------


async def _character(database, actor):
    await _seed_road(database, actor=actor)
    async with database[1]() as session:
        return (await session.scalar(select(Character).where(Character.telegram_id == actor))).id


async def _own(sessions, character_id, *items):
    async with sessions.begin() as session:
        for cosmetic_id, kind in items:
            session.add(
                CharacterCosmetic(
                    character_id=character_id,
                    cosmetic_id=cosmetic_id,
                    cosmetic_type=kind,
                    source_achievement_id="feat.tdo.test",
                )
            )


async def _selection(sessions, character_id):
    async with sessions() as session:
        rows = (
            await session.scalars(
                select(CharacterCosmeticSelection).where(
                    CharacterCosmeticSelection.character_id == character_id
                )
            )
        ).all()
    return {row.cosmetic_type: row.cosmetic_id for row in rows}


def _category(view, kind):
    return next(c for c in view.categories if c.cosmetic_type == kind)


@pytest.mark.asyncio
async def test_migration_converts_two_legacy_and_preserves_all_six(database):
    actor = 893001
    character_id = await _character(database, actor)
    sessions = database[1]
    retired = [
        (cid, "emblem" if ".emblem." in cid else "banner") for cid in RETIRED_LEGACY_COSMETICS
    ]
    await _own(sessions, character_id, (OLD_NOME, "emblem"), (OLD_OCASO, "banner"), *retired)
    async with sessions.begin() as session:
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="emblem", cosmetic_id=OLD_NOME
            )
        )
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="banner", cosmetic_id=OLD_OCASO
            )
        )

    spec = importlib.util.spec_from_file_location("legacy_migration", MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    for _ in range(2):  # idempotente
        async with sessions.begin() as session:
            for old_id, old_type, new_id, new_type in migration.CONVERSIONS:
                params = {
                    "old_id": old_id,
                    "old_type": old_type,
                    "new_id": new_id,
                    "new_type": new_type,
                }
                await session.execute(text(migration.OWNERSHIP_SQL), params)
                await session.execute(text(migration.SELECTION_SQL), params)

    async with sessions() as session:
        owned = set(
            (
                await session.scalars(
                    select(CharacterCosmetic.cosmetic_id).where(
                        CharacterCosmetic.character_id == character_id
                    )
                )
            ).all()
        )
    # nada foi apagado: 6 legados + 2 convertidos
    assert owned == {OLD_NOME, OLD_OCASO, NOME_APAGADO, OCASO, *RETIRED_LEGACY_COSMETICS}
    selection = await _selection(sessions, character_id)
    assert selection["title"] == NOME_APAGADO and selection["frame"] == OCASO
    assert selection["emblem"] == OLD_NOME and selection["banner"] == OLD_OCASO

    view = await CosmeticService(sessions, "ocaso").view(actor)
    assert [c.cosmetic_type for c in view.categories] == list(COSMETIC_TYPES)
    assert _category(view, "title").selected.name == "Nome Apagado"
    assert _category(view, "frame").selected.name == "Ocaso"
    listed = {i.cosmetic_id for c in view.categories for i in c.items}
    assert not listed & set(RETIRED_LEGACY_COSMETICS)


@pytest.mark.asyncio
async def test_migration_keeps_existing_selection_of_target_category(database):
    actor = 893002
    character_id = await _character(database, actor)
    sessions = database[1]
    await _own(sessions, character_id, (OLD_NOME, "emblem"), (TITLE, "title"))
    async with sessions.begin() as session:
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="title", cosmetic_id=TITLE
            )
        )
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="emblem", cosmetic_id=OLD_NOME
            )
        )
        spec = importlib.util.spec_from_file_location("legacy_migration", MIGRATION)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        await session.flush()
        old_id, old_type, new_id, new_type = migration.CONVERSIONS[0]
        params = {"old_id": old_id, "old_type": old_type, "new_id": new_id, "new_type": new_type}
        await session.execute(text(migration.OWNERSHIP_SQL), params)
        await session.execute(text(migration.SELECTION_SQL), params)
    assert (await _selection(sessions, character_id))["title"] == TITLE


async def _run_conversions(sessions):
    spec = importlib.util.spec_from_file_location("legacy_migration", MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with sessions.begin() as session:
        for old_id, old_type, new_id, new_type in migration.CONVERSIONS:
            params = {
                "old_id": old_id,
                "old_type": old_type,
                "new_id": new_id,
                "new_type": new_type,
            }
            await session.execute(text(migration.OWNERSHIP_SQL), params)
            await session.execute(text(migration.SELECTION_SQL), params)


async def _raw_snapshot(sessions, character_id):
    async with sessions() as session:
        owned = (
            await session.execute(
                text(
                    "SELECT cosmetic_id, cosmetic_type, source_achievement_id, acquired_at "
                    "FROM character_cosmetics WHERE character_id = :c ORDER BY cosmetic_id"
                ),
                {"c": character_id},
            )
        ).all()
        selected = (
            await session.execute(
                text(
                    "SELECT cosmetic_type, cosmetic_id FROM character_cosmetic_selections "
                    "WHERE character_id = :c ORDER BY cosmetic_type"
                ),
                {"c": character_id},
            )
        ).all()
    return [tuple(row) for row in owned], [tuple(row) for row in selected]


@pytest.mark.asyncio
async def test_migration_rerun_does_not_duplicate_or_change_rows(database):
    actor = 893004
    character_id = await _character(database, actor)
    sessions = database[1]
    retired = [
        (cid, "emblem" if ".emblem." in cid else "banner") for cid in RETIRED_LEGACY_COSMETICS
    ]
    await _own(sessions, character_id, (OLD_NOME, "emblem"), (OLD_OCASO, "banner"), *retired)
    async with sessions.begin() as session:
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="emblem", cosmetic_id=OLD_NOME
            )
        )
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="banner", cosmetic_id=OLD_OCASO
            )
        )

    await _run_conversions(sessions)
    first_owned, first_selected = await _raw_snapshot(sessions, character_id)
    await _run_conversions(sessions)  # segunda execução
    second_owned, second_selected = await _raw_snapshot(sessions, character_id)

    assert second_owned == first_owned
    assert second_selected == first_selected
    owned_ids = [row[0] for row in second_owned]
    assert len(owned_ids) == len(set(owned_ids)) == 2 + 2 + len(RETIRED_LEGACY_COSMETICS)
    assert owned_ids.count(NOME_APAGADO) == 1 and owned_ids.count(OCASO) == 1
    assert dict(second_selected)["title"] == NOME_APAGADO
    assert dict(second_selected)["frame"] == OCASO
    assert dict(second_selected)["emblem"] == OLD_NOME
    assert dict(second_selected)["banner"] == OLD_OCASO


@pytest.mark.asyncio
async def test_check_constraints_accept_legacy_emblem_banner_and_reject_unknown(database):
    actor = 893005
    character_id = await _character(database, actor)
    sessions = database[1]
    await _own(sessions, character_id, (OLD_NOME, "emblem"), (OLD_OCASO, "banner"))
    async with sessions.begin() as session:
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="emblem", cosmetic_id=OLD_NOME
            )
        )
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="banner", cosmetic_id=OLD_OCASO
            )
        )
    selection = await _selection(sessions, character_id)
    assert selection["emblem"] == OLD_NOME and selection["banner"] == OLD_OCASO

    # Tipos fora do conjunto legado + canônico continuam bloqueados pelo CHECK.
    with pytest.raises(IntegrityError):
        await _own(sessions, character_id, ("cosmetic.bogus.tdo.teste", "bogus"))
    with pytest.raises(IntegrityError):
        async with sessions.begin() as session:
            session.add(
                CharacterCosmeticSelection(
                    character_id=character_id, cosmetic_type="bogus", cosmetic_id=OLD_NOME
                )
            )


@pytest.mark.asyncio
async def test_select_is_idempotent_persistent_and_touches_nothing_else(database):
    actor = 893003
    character_id = await _character(database, actor)
    sessions = database[1]
    await _own(
        sessions, character_id, (TITLE, "title"), (FRAME, "frame"), (APPEARANCE, "appearance")
    )

    async def snapshot():
        async with sessions() as session:
            character = await session.get(Character, character_id)
            columns = {c.name: getattr(character, c.name) for c in Character.__table__.columns}
            items = (
                await session.scalars(
                    select(EquipmentItem.id).where(EquipmentItem.character_id == character_id)
                )
            ).all()
            slots = (
                await session.execute(
                    select(CharacterEquipmentSlot.slot, CharacterEquipmentSlot.equipment_item_id)
                    .where(CharacterEquipmentSlot.character_id == character_id)
                    .order_by(CharacterEquipmentSlot.slot)
                )
            ).all()
        return columns, sorted(items), [tuple(r) for r in slots]

    before = await snapshot()
    service = CosmeticService(sessions, "ocaso")
    for cosmetic_id in (TITLE, FRAME, APPEARANCE):
        first = await service.select(actor, cosmetic_id, None)
        assert first.changed
        again = await service.select(actor, cosmetic_id, cosmetic_id)
        assert not again.changed
        with pytest.raises(CosmeticMutationRejected):
            await service.select(actor, cosmetic_id, None)  # stale
    assert await snapshot() == before

    fresh = CosmeticService(sessions, "ocaso")  # persistência entre "sessões"
    view = await fresh.view(actor)
    assert _category(view, "title").selected.cosmetic_id == TITLE
    assert _category(view, "frame").selected.cosmetic_id == FRAME
    assert _category(view, "appearance").selected.cosmetic_id == APPEARANCE

    with pytest.raises(CosmeticMutationRejected):
        await service.select(actor, "cosmetic.frame.tdo.vigilia_antiga", None)  # não possuído


@pytest.mark.asyncio
async def test_default_appearance_reuses_existing_initial_look_and_is_idempotent(database):
    actor = 893004
    character_id = await _character(database, actor)
    sessions = database[1]
    async with sessions() as session:
        character = await session.get(Character, character_id)
        initial_look = (character.race, character.gender, character.character_class)
        rows_before = (await session.scalars(select(CharacterCosmetic))).all()
    await _own(sessions, character_id, (APPEARANCE, "appearance"))
    service = CosmeticService(sessions, "ocaso")

    start = _category(await service.view(actor), "appearance")
    assert start.selected is None and start.uses_initial_appearance  # aparência inicial
    assert (await service.select_default_appearance(actor, None)).changed is False
    await service.select(actor, APPEARANCE, None)
    with pytest.raises(CosmeticMutationRejected):
        await service.select_default_appearance(actor, None)  # stale
    result = await service.select_default_appearance(actor, APPEARANCE)
    assert result.changed
    assert _category(result.view, "appearance").selected is None
    assert _category(result.view, "appearance").uses_initial_appearance
    assert not _category(result.view, "title").uses_initial_appearance
    assert "appearance" not in await _selection(sessions, character_id)
    assert (await service.select_default_appearance(actor, None)).changed is False

    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert (character.race, character.gender, character.character_class) == initial_look
        rows_after = (await session.scalars(select(CharacterCosmetic))).all()
    assert len(rows_after) == len(rows_before) + 1  # só o item de teste: nenhuma skin criada


@pytest.mark.asyncio
async def test_fallback_for_invalid_selection_appearance_title_frame(database):
    actor = 893005
    character_id = await _character(database, actor)
    sessions = database[1]
    ghosts = (
        ("cosmetic.appearance.removed.ghost", "appearance"),
        ("cosmetic.title.removed.ghost", "title"),
        ("cosmetic.frame.removed.ghost", "frame"),
    )
    await _own(sessions, character_id, *ghosts, (OLD_OCASO, "banner"))
    async with sessions.begin() as session:
        for cosmetic_id, kind in (*ghosts, (OLD_OCASO, "banner")):
            session.add(
                CharacterCosmeticSelection(
                    character_id=character_id, cosmetic_type=kind, cosmetic_id=cosmetic_id
                )
            )
    service = CosmeticService(sessions, "ocaso")
    view = await service.view(actor)
    assert all(_category(view, kind).selected is None for kind in COSMETIC_TYPES)

    assert await service.reconcile(actor) is True
    remaining = await _selection(sessions, character_id)
    assert set(remaining) == {"banner"}  # legado preservado, categorias válidas limpas
    assert await service.reconcile(actor) is False  # idempotente


@pytest.mark.asyncio
async def test_appearance_fallback_returns_to_initial_look_without_new_cosmetic_row(database):
    actor = 893006
    character_id = await _character(database, actor)
    sessions = database[1]
    ghost = "cosmetic.appearance.removed.ghost"
    await _own(sessions, character_id, (ghost, "appearance"))
    async with sessions.begin() as session:
        session.add(
            CharacterCosmeticSelection(
                character_id=character_id, cosmetic_type="appearance", cosmetic_id=ghost
            )
        )
        before = len((await session.scalars(select(CharacterCosmetic))).all())
    service = CosmeticService(sessions, "ocaso")
    view = await service.view(actor)
    assert _category(view, "appearance").uses_initial_appearance
    assert await service.reconcile(actor) is True
    assert "appearance" not in await _selection(sessions, character_id)
    async with sessions() as session:
        assert len((await session.scalars(select(CharacterCosmetic))).all()) == before
        names = (await session.scalars(select(CharacterCosmetic.cosmetic_id))).all()
    assert not any("viajante_de_asterion" in n for n in names)
    assert _category(await service.view(actor), "appearance").uses_initial_appearance
