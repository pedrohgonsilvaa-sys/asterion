import asyncio
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from asterion.application.active_arts import ActiveArtCharacterView, ActiveArtSlotSnapshot
from asterion.application.doctrines import DoctrineRejected, DoctrineService
from asterion.application.equipment_configuration import (
    load_equipment_configuration,
    resolve_character_combat_stats,
)
from asterion.application.progression import (
    consolidate_character_level,
    consolidate_level,
    level_xp,
)
from asterion.application.talents import (
    TalentChoiceView,
    TalentMutationCode,
    TalentMutationRejected,
    TalentService,
    TalentView,
)
from asterion.bot.character_progression_ui import (
    render_art_detail,
    render_art_root,
    render_talent_detail,
    render_talent_list,
    render_talent_root,
)
from asterion.domain.arts import ART_IDS_BY_CLASS, DEVASTADOR_ART_IDS
from asterion.domain.combat_math import (
    class_stats,
    finalize_primary_stats,
    racial_stats,
    resolve_combat_stats,
)
from asterion.domain.economy import crowns_per_level
from asterion.domain.equipment_stats import (
    EquipmentConfigurationError,
    EquipmentStatContribution,
    equipment_configuration_from_data,
)
from asterion.domain.paths import PATH_DEFINITIONS
from asterion.domain.talents import (
    TALENT_CATALOG,
    TALENTS_BY_CLASS,
    TalentDefinition,
    TalentSelectionError,
    talent_points_at_level,
    validate_active_talent_ids,
    validate_talent_choices,
)
from asterion.infrastructure.db.models import (
    Account,
    Character,
    CharacterDoctrine,
    CharacterTalentChoice,
    GameActivity,
    WorldState,
)

D = Decimal
ONE = D(1)
REFUGE = "Refúgio do Ocaso"
REGION = "Terras do Ocaso"


def _talent(character_class: str, name: str) -> TalentDefinition:
    return next(talent for talent in TALENTS_BY_CLASS[character_class] if talent.name == name)


async def _seed_character(
    database,
    actor: int,
    *,
    character_class: str = "sentinela",
    level: int = 10,
    crowns: int = 2000,
    selected_path: str | None = None,
    location: str = REFUGE,
    hp_ratio: Decimal = ONE,
):
    _, sessions = database
    character_id = uuid4()
    stats = resolve_combat_stats(
        character_class, level, "remanescente", selected_path=selected_path
    )
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Talent" + "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:]),
                race="remanescente",
                character_class=character_class,
                selected_path=selected_path,
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp * hp_ratio,
                max_hp=stats.hp,
                vigor=71,
                max_vigor=100,
                crowns=crowns,
            )
        )
        session.add(WorldState(character_id=character_id, region=REGION, location=location))
    return character_id, sessions


def test_talent_catalog_contains_all_classes_tiers_and_point_levels():
    assert len(TALENT_CATALOG) == 108
    assert {character_class: len(rows) for character_class, rows in TALENTS_BY_CLASS.items()} == {
        "sentinela": 18,
        "errante": 18,
        "vigia": 18,
        "tecelao": 18,
        "oraculo": 18,
        "luminar": 18,
    }
    assert talent_points_at_level(4) == 0
    assert talent_points_at_level(5) == 1
    assert talent_points_at_level(9) == 1
    assert talent_points_at_level(10) == 2
    assert talent_points_at_level(60) == 12
    for talents in TALENTS_BY_CLASS.values():
        assert [talent.level for talent in talents] == [
            5,
            5,
            5,
            15,
            15,
            15,
            25,
            25,
            25,
            35,
            35,
            35,
            45,
            45,
            45,
            55,
            55,
            55,
        ]


@pytest.mark.parametrize(
    ("level", "expected_points"),
    [
        (1, 0), (4, 0), (5, 1), (9, 1), (10, 2), (14, 2),
        (15, 3), (19, 3), (20, 4), (24, 4), (25, 5), (29, 5),
        (30, 6), (34, 6), (35, 7), (39, 7), (40, 8), (44, 8),
        (45, 9), (49, 9), (50, 10), (54, 10), (55, 11), (59, 11),
        (60, 12),
    ],
)
def test_talent_point_budget_matches_every_canonical_level_milestone(level, expected_points):
    assert talent_points_at_level(level) == expected_points


def test_level_progression_crosses_multiple_talent_milestones_without_duplicate_points():
    from types import SimpleNamespace

    character = SimpleNamespace(
        level=1,
        xp=sum(level_xp(level) for level in range(1, 20)),
        hp=D(1),
        max_hp=D(1),
        race="remanescente",
        character_class="sentinela",
    )
    assert consolidate_level(character) == 19
    assert character.level == 20
    assert talent_points_at_level(character.level) == 4
    assert consolidate_level(character) == 0
    assert talent_points_at_level(character.level) == 4


def test_authoritative_talent_validator_rejects_invalid_active_ids_and_rank_duplicates():
    steel = _talent("sentinela", "Aço Desperto").talent_id
    other_class = _talent("errante", "Fio Afiado").talent_id
    future = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 25
    )
    for ids in (("talent.unknown.injected",), (other_class,), (future,), (steel, steel)):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("sentinela", 20, ids)
    with pytest.raises(TalentSelectionError):
        validate_active_talent_ids(
            "sentinela",
            5,
            (steel, _talent("sentinela", "Carne de Pedra").talent_id),
        )
    with pytest.raises(TalentSelectionError):
        validate_talent_choices("sentinela", 10, ((1, steel), (1, steel)))
    with pytest.raises(TalentSelectionError):
        validate_talent_choices("sentinela", 10, ((3, steel),))


def test_nv5_talent_stat_effects_match_all_six_class_catalogs():
    choices = {
        "sentinela": ("Aço Desperto", "Carne de Pedra", "Ritmo de Guarda"),
        "errante": ("Fio Afiado", "Passo Prudente", "Instinto Rápido"),
        "vigia": ("Mão Firme", "Sobrevivente das Trilhas", "Passo do Caçador"),
        "tecelao": ("Fio Potente", "Trama Vital", "Passo Entre Fios"),
        "oraculo": ("Visão Cruel", "Pressentimento Vital", "Passos do Destino"),
        "luminar": ("Luz Incisiva", "Vitalidade Solar", "Clarão Ágil"),
    }
    for character_class, names in choices.items():
        intrinsic = class_stats(character_class, 10)
        base = resolve_combat_stats(character_class, 10, "alvorano")
        attack = resolve_combat_stats(
            character_class,
            10,
            "alvorano",
            talent_ids=(_talent(character_class, names[0]).talent_id,),
        )
        hp = resolve_combat_stats(
            character_class,
            10,
            "alvorano",
            talent_ids=(_talent(character_class, names[1]).talent_id,),
        )
        agility = resolve_combat_stats(
            character_class,
            10,
            "alvorano",
            talent_ids=(_talent(character_class, names[2]).talent_id,),
        )
        expected_attack = finalize_primary_stats(
            racial_stats(replace(intrinsic, attack=intrinsic.attack * D("1.01")), "alvorano")
        )
        expected_hp = finalize_primary_stats(
            racial_stats(replace(intrinsic, hp=intrinsic.hp * D("1.01")), "alvorano")
        )
        agility_multiplier = D(1) if character_class == "sentinela" else D("1.03")
        expected_agility = finalize_primary_stats(
            racial_stats(
                replace(intrinsic, agility=intrinsic.agility * agility_multiplier),
                "alvorano",
            )
        )
        assert attack.attack == expected_attack.attack
        assert hp.hp == expected_hp.hp
        assert agility.agility == expected_agility.agility
        assert base.defense == attack.defense == hp.defense == agility.defense


def test_talent_and_art_screens_render_every_class_catalog_without_future_execution():
    for index, (character_class, talents) in enumerate(TALENTS_BY_CLASS.items()):
        view = TalentView(
            uuid4(),
            f"Hero{index}",
            character_class,
            10,
            None,
            3,
            2,
            1,
            (TalentChoiceView(1, talents[0].talent_id),),
            0,
            REFUGE,
            False,
        )
        listing = render_talent_list(view)
        assert sum(talent.name in listing.text for talent in talents) == 18
        assert "Nv.15" in listing.text and "Requer Nv.15" in listing.text
        assert "Disponível" in listing.text and "Adquirido" in listing.text
        root = render_talent_root(view)
        assert "Disponíveis · 1" in root.text
        assert all(
            len(button.callback_data.encode("utf-8")) <= 64
            for row in listing.keyboard.inline_keyboard
            for button in row
        )
        detail = render_talent_detail(view, talents[1])
        assert "Adquirir Talento" in [
            button.text for row in detail.keyboard.inline_keyboard for button in row
        ]

        art_ids = ART_IDS_BY_CLASS[character_class]
        art_view = ActiveArtCharacterView(
            uuid4(),
            f"Hero{index}",
            character_class,
            10,
            None,
            3,
            tuple(
                ActiveArtSlotSnapshot(slot, art_id) for slot, art_id in enumerate(art_ids[:3], 1)
            ),
            art_ids,
            False,
        )
        arts = render_art_root(art_view)
        assert all(art_id not in arts.text for art_id in art_ids)
        assert all(
            len(button.callback_data.encode("utf-8")) <= 64
            for row in arts.keyboard.inline_keyboard
            for button in row
        )
        art_detail = render_art_detail(art_view, art_ids[0])
        assert "Arte Ativa" in art_detail.text
        if character_class == "vigia":
            assert "Dano · 40% ATQ" in render_art_detail(art_view, art_ids[2]).text
            assert "Atinge · 3 vezes" in render_art_detail(art_view, art_ids[2]).text
        if character_class == "luminar":
            detail = render_art_detail(art_view, art_ids[1])
            assert "Cura · 85% ATQ" in detail.text
            assert "Alvo · Você ou Aliado" in detail.text
        if character_class == "oraculo":
            detail = render_art_detail(art_view, art_ids[1])
            assert "Alvo · Você ou Aliado" in detail.text


def test_devastador_ariete_is_visible_with_explicit_melee_requirement():
    ariete = DEVASTADOR_ART_IDS["ariete"]
    view = ActiveArtCharacterView(
        character_id=uuid4(),
        character_name="Hero",
        character_class="sentinela",
        level=12,
        selected_path="devastador",
        combat_configuration_version=4,
        slots=(),
        available_art_ids=(ariete,),
        foreground=False,
    )

    root = render_art_root(view)
    assert "Aríete" in root.text
    detail = render_art_detail(view, ariete)
    assert "135% ATQ" in detail.text
    assert "+10 p.p." in detail.text
    assert "Recarga · 2 Rodadas" in detail.text
    assert "Arma corpo a corpo compatível" in detail.text
    assert "Equipar Arte" in [
        button.text for row in detail.keyboard.inline_keyboard for button in row
    ]

    incompatible = render_art_detail(
        replace(view, weapon_incompatible_art_ids=(ariete,)), ariete
    )
    assert "equipe uma arma compatível" in incompatible.text
    assert "Equipar Arte" not in [
        button.text for row in incompatible.keyboard.inline_keyboard for button in row
    ]


@pytest.mark.asyncio
async def test_nv10_acquires_two_of_three_nv5_talents_and_rejects_invalid_choices(database):
    actor = 772101
    _, sessions = await _seed_character(database, actor, level=10)
    service = TalentService(sessions, "ocaso")
    steel = _talent("sentinela", "Aço Desperto").talent_id
    flesh = _talent("sentinela", "Carne de Pedra").talent_id
    rhythm = _talent("sentinela", "Ritmo de Guarda").talent_id

    first = await service.acquire(actor, steel, 0)
    assert first is not None and first.changed
    assert first.point_slot == 1
    assert first.combat_configuration_version == 1
    second = await service.acquire(actor, flesh, 1)
    assert second is not None and second.changed
    assert second.point_slot == 2
    assert second.view.available_points == 0

    with pytest.raises(TalentMutationRejected) as no_points:
        await service.acquire(actor, rhythm, 2)
    assert no_points.value.code == TalentMutationCode.NO_POINTS
    with pytest.raises(TalentMutationRejected) as duplicate:
        await service.acquire(actor, steel, 2)
    assert duplicate.value.code == TalentMutationCode.DUPLICATE_TALENT
    with pytest.raises(TalentMutationRejected) as future:
        await service.acquire(
            actor,
            _talent("sentinela", "Ponta Revidada").talent_id,
            2,
        )
    assert future.value.code == TalentMutationCode.LEVEL_REQUIRED
    with pytest.raises(TalentMutationRejected) as wrong_class:
        await service.acquire(actor, _talent("errante", "Fio Afiado").talent_id, 2)
    assert wrong_class.value.code == TalentMutationCode.WRONG_CLASS

    view = await service.view(actor)
    assert view is not None
    assert [(choice.point_slot, choice.talent_id) for choice in view.choices] == [
        (1, steel),
        (2, flesh),
    ]
    assert view.combat_configuration_version == 2


@pytest.mark.asyncio
async def test_talent_acquire_preserves_hp_ratio_and_uses_path_before_equipment(database):
    actor = 772102
    character_id, sessions = await _seed_character(
        database,
        actor,
        character_class="sentinela",
        level=10,
        selected_path="bastiao",
        hp_ratio=D("0.5"),
    )
    talent_id = _talent("sentinela", "Carne de Pedra").talent_id
    result = await TalentService(sessions, "ocaso").acquire(actor, talent_id, 0)
    assert result is not None
    expected = resolve_combat_stats(
        "sentinela",
        10,
        "remanescente",
        EquipmentStatContribution(hp=D(100), attack=D(100)),
        selected_path="bastiao",
        talent_ids=(talent_id,),
    )
    intrinsic = class_stats("sentinela", 10)
    path = PATH_DEFINITIONS["bastiao"]
    expected_from_order = finalize_primary_stats(
        racial_stats(
            replace(
                intrinsic,
                hp=intrinsic.hp * (D(1) + path.hp) * D("1.01") + D(100),
                attack=intrinsic.attack * (D(1) + path.attack) + D(100),
                defense=intrinsic.defense * (D(1) + path.defense),
                agility=intrinsic.agility * (D(1) + path.agility),
            ),
            "remanescente",
        )
    )
    assert expected.hp == expected_from_order.hp
    assert expected.attack == expected_from_order.attack
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert (
            character.max_hp
            == resolve_combat_stats(
                "sentinela", 10, "remanescente", selected_path="bastiao", talent_ids=(talent_id,)
            ).hp
        )
        assert character.hp == (character.max_hp / D(2)).to_integral_value(rounding="ROUND_FLOOR")


@pytest.mark.asyncio
async def test_talent_acquire_and_respec_share_foreground_guard(database):
    actor = 772103
    character_id, sessions = await _seed_character(database, actor)
    talent_id = _talent("sentinela", "Aço Desperto").talent_id
    async with sessions.begin() as session:
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    service = TalentService(sessions, "ocaso")
    with pytest.raises(TalentMutationRejected) as blocked:
        await service.acquire(actor, talent_id, 0)
    assert blocked.value.code == TalentMutationCode.FOREGROUND


@pytest.mark.asyncio
async def test_talent_respec_rejects_wrong_location_balance_and_foreground(database):
    actor = 772106
    character_id, sessions = await _seed_character(
        database, actor, level=10, crowns=1000, location="Bosque Calcinado"
    )
    async with sessions.begin() as session:
        session.add(
            CharacterTalentChoice(
                character_id=character_id,
                point_slot=1,
                talent_id=_talent("sentinela", "Aço Desperto").talent_id,
            )
        )
    service = TalentService(sessions, "ocaso")
    before = await service.view(actor)
    assert before is not None
    with pytest.raises(TalentMutationRejected) as location:
        await service.respec(actor, before.combat_configuration_version)
    assert location.value.code == TalentMutationCode.WRONG_LOCATION

    async with sessions.begin() as session:
        world = await session.get(WorldState, character_id)
        character = await session.get(Character, character_id)
        world.location = REFUGE
        character.crowns = 0
    with pytest.raises(TalentMutationRejected) as poor:
        await service.respec(actor, before.combat_configuration_version)
    assert poor.value.code == TalentMutationCode.INSUFFICIENT_CROWNS

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.crowns = 1000
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=character_id,
                content_id="test.foreground",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )
    with pytest.raises(TalentMutationRejected) as foreground:
        await service.respec(actor, before.combat_configuration_version)
    assert foreground.value.code == TalentMutationCode.FOREGROUND

    after = await service.view(actor)
    assert after is not None
    assert after.combat_configuration_version == before.combat_configuration_version
    assert after.choices == before.choices
    assert after.crowns == 1000


@pytest.mark.asyncio
async def test_nv15_remains_public_and_nv35_requires_level_then_acquires(database):
    actor = 772107
    _, sessions = await _seed_character(database, actor, level=14)
    service = TalentService(sessions, "ocaso")
    talent_id = _talent("sentinela", "Ponta Revidada").talent_id
    with pytest.raises(TalentMutationRejected) as under_level:
        await service.acquire(actor, talent_id, 0)
    assert under_level.value.code == TalentMutationCode.LEVEL_REQUIRED
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 15
    acquired = await service.acquire(actor, talent_id, 0)
    assert acquired is not None and acquired.point_slot == 1
    assert acquired.view.available_points == 2
    future_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 35
    )
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 34
    with pytest.raises(TalentMutationRejected) as under_level:
        await service.acquire(actor, future_id, acquired.combat_configuration_version)
    assert under_level.value.code == TalentMutationCode.LEVEL_REQUIRED
    async with sessions.begin() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        character.level = 60
    high_level = await service.view(actor)
    assert high_level is not None
    acquired35 = await service.acquire(actor, future_id, high_level.combat_configuration_version)
    assert acquired35 is not None and acquired35.point_slot == 2


@pytest.mark.asyncio
async def test_respec_cost_local_atomicity_and_hp_reconciliation(database):
    actor = 772104
    character_id, sessions = await _seed_character(
        database, actor, level=10, crowns=1000, selected_path="bastiao", hp_ratio=D("0.5")
    )
    first = _talent("sentinela", "Aço Desperto").talent_id
    second = _talent("sentinela", "Carne de Pedra").talent_id
    async with sessions.begin() as session:
        session.add_all(
            [
                CharacterTalentChoice(character_id=character_id, point_slot=1, talent_id=first),
                CharacterTalentChoice(character_id=character_id, point_slot=2, talent_id=second),
            ]
        )
        character = await session.get(Character, character_id)
        with_talents = resolve_combat_stats(
            "sentinela",
            10,
            "remanescente",
            selected_path="bastiao",
            talent_ids=(first, second),
        )
        character.max_hp = with_talents.hp
        character.hp = (with_talents.hp / D(2)).to_integral_value(rounding="ROUND_FLOOR")

    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None
    assert view.respec_cost == 2 * crowns_per_level(10)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        old_hp = character.hp
        old_max_hp = character.max_hp
    baseline = resolve_combat_stats("sentinela", 10, "remanescente", selected_path="bastiao")
    ratio = Fraction(old_hp) * Fraction(baseline.hp) / Fraction(old_max_hp)
    expected_hp_after_respec = D(ratio.numerator // ratio.denominator)
    empty_actor = 772105
    await _seed_character(database, empty_actor, level=10, crowns=1000)
    empty_view = await service.view(empty_actor)
    assert empty_view is not None
    with pytest.raises(TalentMutationRejected) as empty:
        await service.respec(empty_actor, empty_view.combat_configuration_version)
    assert empty.value.code == TalentMutationCode.NOTHING_TO_RESPEC

    result = await service.respec(actor, view.combat_configuration_version)
    assert result is not None and result.changed
    assert result.view.choices == ()
    assert result.view.available_points == 2
    assert result.view.crowns == 1000 - 2 * crowns_per_level(10)
    assert result.combat_configuration_version == view.combat_configuration_version + 1
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.max_hp == baseline.hp
        assert character.hp == expected_hp_after_respec
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice).where(
                        CharacterTalentChoice.character_id == character_id
                    )
                )
            ).all()
        )
        assert rows == []

    with pytest.raises(TalentMutationRejected) as nothing:
        await service.respec(actor, result.combat_configuration_version)
    assert nothing.value.code == TalentMutationCode.NOTHING_TO_RESPEC


def test_legacy_combat_configuration_has_no_talents_and_new_snapshot_roundtrips():
    from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot

    legacy = equipment_configuration_from_data(
        {"combat_configuration_version": 4, "ruleset_version": "old", "equipment": []}
    )
    assert legacy.talent_choices == ()
    current = EquipmentConfigurationSnapshot(
        5,
        selected_path="bastiao",
        talent_choices=((1, _talent("sentinela", "Aço Desperto").talent_id),),
    )
    restored = equipment_configuration_from_data(current.to_data("ruleset") | {"active_arts": []})
    assert restored == current


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_choice",
    (
        "unsupported",
        "unsupported_35",
        "unsupported_45",
        "wrong_class",
        "unknown",
        "over_budget",
    ),
)
async def test_persisted_invalid_talents_fail_closed_without_deleting_rows(
    database, invalid_choice
):
    invalid_cases = (
        "unsupported",
        "unsupported_35",
        "unsupported_45",
        "wrong_class",
        "unknown",
        "over_budget",
    )
    actor = 772108 + invalid_cases.index(invalid_choice)
    level = (
        20
        if invalid_choice == "unsupported"
        else 40
        if invalid_choice == "unsupported_35"
        else 60
        if invalid_choice == "unsupported_45"
        else 10
    )
    character_id, sessions = await _seed_character(database, actor, level=level)
    choices = {
        "unsupported": (
            3,
            next(
                talent.talent_id
                for talent in TALENTS_BY_CLASS["sentinela"]
                if talent.level == 25
            ),
        ),
        "unsupported_35": (7, _talent("sentinela", "Olho de Combate").talent_id),
        "unsupported_45": (
            9,
            next(
                talent.talent_id
                for talent in TALENTS_BY_CLASS["sentinela"]
                if talent.level == 45
            ),
        ),
        "wrong_class": (1, _talent("errante", "Fio Afiado").talent_id),
        "unknown": (1, "talent.unknown.injected"),
        "over_budget": (5, _talent("sentinela", "Aço Desperto").talent_id),
    }
    point_slot, talent_id = choices[invalid_choice]
    async with sessions.begin() as session:
        session.add(
            CharacterTalentChoice(
                character_id=character_id,
                point_slot=point_slot,
                talent_id=talent_id,
                publicly_acquired=invalid_choice
                not in {"unsupported_35", "unsupported_45"},
            )
        )

    service = TalentService(sessions, "ocaso")
    with pytest.raises(TalentMutationRejected) as rejected:
        await service.view(actor)
    assert rejected.value.code == TalentMutationCode.INVALID_CURRENT_CONFIGURATION
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        before_hp = character.hp
        before_max_hp = character.max_hp
        with pytest.raises(EquipmentConfigurationError):
            await load_equipment_configuration(session, character)
    async with sessions() as session:
        character = await session.get(Character, character_id)
        saved = await session.scalar(
            select(CharacterTalentChoice).where(
                CharacterTalentChoice.character_id == character_id
            )
        )
        assert saved is not None and (saved.point_slot, saved.talent_id) == (
            point_slot,
            talent_id,
        )
        assert (character.hp, character.max_hp) == (before_hp, before_max_hp)


@pytest.mark.asyncio
async def test_valid_nv5_talent_reloads_through_combat_configuration_snapshot(database):
    actor = 772112
    character_id, sessions = await _seed_character(database, actor, level=10)
    talent_id = _talent("sentinela", "Aço Desperto").talent_id
    acquired = await TalentService(sessions, "ocaso").acquire(actor, talent_id, 0)
    assert acquired is not None and acquired.point_slot == 1

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        configuration = await load_equipment_configuration(session, character)
        stats = resolve_character_combat_stats(character, configuration)
        serialized = configuration.to_data("test-ruleset")
    restored = equipment_configuration_from_data(serialized)
    restored_stats = resolve_combat_stats(
        "sentinela",
        10,
        "remanescente",
        selected_path=None,
        talent_ids=tuple(talent for _, talent in restored.talent_choices),
    )
    assert restored.talent_choices == ((1, talent_id),)
    assert stats.attack == restored_stats.attack
    assert stats.attack > resolve_combat_stats("sentinela", 10, "remanescente").attack


@pytest.mark.asyncio
async def test_doctrine_cannot_activate_injected_nv55_talent(database):
    actor = 772113
    character_id, sessions = await _seed_character(database, actor, level=40)
    service = DoctrineService(sessions, "ocaso")
    created = await service.create(actor, "Futura", 0)
    assert created is not None and created.doctrine_id is not None
    unsupported_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 55
    )
    async with sessions.begin() as session:
        doctrine = await session.get(CharacterDoctrine, created.doctrine_id)
        doctrine.configuration = {
            "path": None,
            "equipment": {},
            "arts": {},
            "talents": [{"point_slot": 7, "talent_id": unsupported_id}],
        }
    with pytest.raises(DoctrineRejected) as rejected:
        await service.apply(actor, created.doctrine_id, 0, 0)
    assert rejected.value.code == "invalid_talents"
    async with sessions() as session:
        character = await session.get(Character, character_id)
        assert character.combat_configuration_version == 0
        assert await session.scalar(
            select(CharacterTalentChoice).where(
                CharacterTalentChoice.character_id == character_id
            )
        ) is None
        doctrine = await session.get(CharacterDoctrine, created.doctrine_id)
        assert doctrine.configuration["talents"] == [
            {"point_slot": 7, "talent_id": unsupported_id}
        ]


@pytest.mark.asyncio
async def test_level_60_preserves_unspent_points_with_nv5_nv15_nv25_nv35_nv45_available(database):
    actor = 772114
    character_id, sessions = await _seed_character(database, actor, level=60)
    service = TalentService(sessions, "ocaso")
    view = await service.view(actor)
    assert view is not None and view.total_points == 12 and view.available_points == 12
    for talent in TALENTS_BY_CLASS["sentinela"][:9]:
        result = await service.acquire(
            actor,
            talent.talent_id,
            view.combat_configuration_version,
        )
        assert result is not None and result.changed
        view = result.view
    assert len(view.choices) == 9
    assert view.total_points == 12
    assert view.available_points == 3
    future_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 35
    )
    acquired35 = await service.acquire(actor, future_id, view.combat_configuration_version)
    assert acquired35 is not None and acquired35.point_slot == 10
    view = acquired35.view
    assert view.available_points == 2
    level45_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 45
    )
    acquired45 = await service.acquire(actor, level45_id, view.combat_configuration_version)
    assert acquired45 is not None and acquired45.point_slot == 11
    view = acquired45.view
    assert view.available_points == 1
    level55_id = next(
        talent.talent_id
        for talent in TALENTS_BY_CLASS["sentinela"]
        if talent.level == 55
    )
    with pytest.raises(TalentMutationRejected) as future:
        await service.acquire(actor, level55_id, view.combat_configuration_version)
    assert future.value.code == TalentMutationCode.TIER_NOT_IMPLEMENTED
    async with sessions() as session:
        saved = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character_id)
                    .order_by(CharacterTalentChoice.point_slot)
                )
            ).all()
        )
    assert [row.talent_id for row in saved] == [
        item.talent_id for item in TALENTS_BY_CLASS["sentinela"][:9]
    ] + [future_id, level45_id]


@pytest.mark.asyncio
async def test_database_progression_awards_milestone_points_once_and_keeps_unspent_budget(database):
    actor = 772116
    character_id, sessions = await _seed_character(database, actor, level=4)
    service = TalentService(sessions, "ocaso")
    talents = TALENTS_BY_CLASS["sentinela"][:3]
    selected = 0

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.xp = level_xp(4)
        assert await consolidate_character_level(session, character) == 1
        assert character.level == 5

    view = await service.view(actor)
    assert view is not None and view.total_points == 1 and view.available_points == 1
    first = await service.acquire(actor, talents[0].talent_id, view.combat_configuration_version)
    assert first is not None and first.point_slot == 1
    selected += 1

    for current_level, target_level, expected_points in ((5, 10, 2), (10, 15, 3)):
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            character.xp = sum(level_xp(level) for level in range(current_level, target_level))
            advanced = await consolidate_character_level(session, character)
            assert advanced == target_level - current_level
            assert character.level == target_level
        view = await service.view(actor)
        assert view is not None and view.total_points == expected_points
        assert view.available_points == expected_points - selected
        result = await service.acquire(
            actor,
            talents[selected].talent_id,
            view.combat_configuration_version,
        )
        assert result is not None and result.point_slot == selected + 1
        selected += 1
        async with sessions.begin() as session:
            character = await session.get(Character, character_id)
            assert await consolidate_character_level(session, character) == 0
        unchanged = await service.view(actor)
        assert unchanged is not None
        assert unchanged.total_points == expected_points
        assert unchanged.available_points == expected_points - selected

    async with sessions() as session:
        rows = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice)
                    .where(CharacterTalentChoice.character_id == character_id)
                    .order_by(CharacterTalentChoice.point_slot)
                )
            ).all()
        )
        assert [(row.point_slot, row.talent_id) for row in rows] == [
            (index + 1, talents[index].talent_id) for index in range(3)
        ]


@pytest.mark.asyncio
async def test_concurrent_acquisition_cannot_spend_one_point_twice(database):
    actor = 772115
    character_id, sessions = await _seed_character(database, actor, level=5)
    talents = TALENTS_BY_CLASS["sentinela"][:2]
    service = TalentService(sessions, "ocaso")
    results = await asyncio.gather(
        *(service.acquire(actor, talent.talent_id, 0) for talent in talents),
        return_exceptions=True,
    )
    successes = [result for result in results if not isinstance(result, Exception)]
    failures = [result for result in results if isinstance(result, TalentMutationRejected)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code == TalentMutationCode.STALE_CONFIGURATION
    view = await service.view(actor)
    assert view is not None and view.total_points == 1 and view.available_points == 0
    async with sessions() as session:
        saved = list(
            (
                await session.scalars(
                    select(CharacterTalentChoice).where(
                        CharacterTalentChoice.character_id == character_id
                    )
                )
            ).all()
        )
        assert len(saved) == 1


@pytest.mark.asyncio
async def test_0015_talent_migration_constraints_and_safe_downgrade(database):
    engine, _ = database
    async with engine.begin() as connection:
        constraints = set(
            (
                await connection.execute(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid='character_talent_choices'::regclass"
                    )
                )
            ).scalars()
        )
    assert constraints == {
        "ck_character_talent_point_slot",
        "fk_character_talent_choices_character_id_characters",
        "pk_character_talent_choices",
        "uq_character_talent_choice",
    }
