from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

import pytest

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.application.prologue import CombatView
from asterion.bot.character_progression_ui import render_art_detail
from asterion.bot.combat_ui import render_combat
from asterion.bot.doctrines_ui import doctrine_art_ids
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    ART_IDS_BY_CLASS,
    TECELAO_ART_IDS,
    TECELAO_ART_LEVELS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, _apply_barrier, act, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import Account, Character

SURTO = "class_art.tecelao.surto_do_veu"
FIO = TECELAO_ART_IDS["fio_cortante"]


def _combat(path: str | None = "conjurador", *, level: int = 34, arts=(SURTO,)):
    stats = resolve_combat_stats("tecelao", level, "remanescente", selected_path=path)
    combat = PROFILE.create(
        uuid4(), "Surto", "tecelao", "remanescente", stats.hp
    )
    combat.tutorial = None
    combat.ruleset = CURRENT_COMBAT_RULESET
    player = combat.fighters["player"]
    player.level = level
    player.character_class = "tecelao"
    player.selected_path = path
    player.stats = replace(
        stats,
        hp=D("1000"),
        attack=D("100"),
        defense=D("100"),
        agility=D("200"),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    player.hp = player.stats.hp
    enemy = combat.fighters["enemy"]
    enemy.level = level
    enemy.stats = replace(
        enemy.stats,
        hp=D("5000"),
        attack=D("20"),
        defense=D(0),
        agility=D("100"),
        evasion=D(0),
        block=D(0),
        crit=D(0),
    )
    enemy.hp = enemy.stats.hp
    enemy.takes_turn = False
    combat.player_actions = class_player_actions("tecelao", tuple(arts), path)
    combat.configuration_snapshot = {
        "active_arts": tuple(
            {"slot": index, "art_id": art_id}
            for index, art_id in enumerate(arts, start=1)
        )
    }
    combat.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")
    }
    combat.ai_cycle = ("wait",)
    return start_combat(combat)


def _event(state, action_id=SURTO):
    return next(event for event in state.events if event.action == action_id)


def test_surto_is_level_34_class_art_for_both_paths_and_no_path_without_weapon_gate():
    definition = active_art_definition(SURTO)
    assert definition is not None
    assert definition.art_id == SURTO
    assert definition.character_class == "tecelao"
    assert definition.min_level == 34
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset()
    assert TECELAO_ART_LEVELS[SURTO] == 34
    assert SURTO in ART_IDS_BY_CLASS["tecelao"]
    assert SURTO in ACTIVE_ART_IDS_BY_CLASS["tecelao"]
    assert ACTIVE_ART_DEFINITIONS[SURTO] is definition

    for path in (None, "conjurador", "runico"):
        action = class_player_actions("tecelao", (SURTO,), path)[SURTO]
        assert action.id == SURTO
        assert action.name == "Surto do Véu"
        assert action.coefficient == D("1.45")
        assert action.cooldown == 3
        assert action.target_mode == "opponent"
        assert action.hit_count == 1
        assert action.attack_debuff == 0
        assert action.native_dot_kind is None
        assert action.heal_coefficient == 0
        assert action.self_barrier_coefficient == 0
        assert action.target_barrier_coefficient == 0
        assert action.effect_removal is None
        assert action.prepares_chain is None
        assert action.consumes_chain is None

    with pytest.raises(ValueError):
        class_player_actions("sentinela", (SURTO,))


@pytest.mark.parametrize("path", (None, "conjurador", "runico"))
def test_surto_resolves_one_145_percent_direct_attack_then_generates_its_origin(path):
    combat = _combat(path)
    actor = combat.fighters["player"]
    opportunity = actor.opportunity
    result = act(combat, SURTO, target_id="enemy")
    event = _event(result)

    assert event.calculated_damage == direct_damage(
        D("100"), D("1.45"), D(0), 34, critical=False
    )
    assert event.path_power_multiplier == D(1)
    assert event.hit_count == 1
    assert result.fighters["enemy"].hp == D("5000") - event.effective_damage
    assert result.fighters["player"].cooldowns[SURTO] == opportunity + 3
    trama = result.fighters["player"].path_state["trama_state"]
    assert trama == {
        "origin_art": SURTO,
        "remaining": 2,
        "applied_opportunity": opportunity,
    }
    assert "tecelao.trama_gerada" in event.path_triggers

    view = CombatView(uuid4(), uuid4(), uuid4(), result, "combat", 0, context="road")
    hud = render_combat(view).text
    assert "Trama · <code>2T · Surto do Véu</code>" in hud
    assert "Trama Encadeada gerada · origem <b>Surto do Véu</b>" in hud

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    assert restored.fighters["player"].path_state["trama_state"] == trama
    assert restored.fighters["player"].cooldowns[SURTO] == opportunity + 3


def test_repeating_surto_does_not_consume_or_refresh_its_own_trama():
    combat = _combat()
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": SURTO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    trama_before = actor.path_state["trama_state"].copy()
    actor.cooldowns[SURTO] = actor.opportunity

    result = act(combat, SURTO, target_id="enemy")
    event = _event(result)

    assert event.path_power_multiplier == D(1)
    assert not event.class_resource_changes
    assert result.fighters["player"].path_state["trama_state"] == trama_before


@pytest.mark.parametrize(
    ("path", "expected_multiplier"),
    ((None, D("1.10")), ("conjurador", D("1.15")), ("runico", D("1.06"))),
)
def test_surto_consumes_a_different_arts_trama_once_with_the_path_damage_bonus(
    path, expected_multiplier
):
    combat = _combat(path, arts=(FIO, SURTO))
    primed = act(combat, FIO, target_id="enemy")
    assert primed.fighters["player"].path_state["trama_state"]["origin_art"] == FIO

    result = act(primed, SURTO, target_id="enemy")
    event = _event(result)

    assert event.path_power_multiplier == expected_multiplier
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    view = CombatView(uuid4(), uuid4(), uuid4(), result, "combat", 0, context="road")
    assert "instância(s) consumida(s)" in render_combat(view).text
    assert event.calculated_damage == direct_damage(
        D("100"), D("1.45") * expected_multiplier, D(0), 34, critical=False
    )
    assert "trama_state" not in result.fighters["player"].path_state


@pytest.mark.parametrize(
    ("path", "expected_multiplier"),
    ((None, D("1.10")), ("conjurador", D("1.15")), ("runico", D("1.06"))),
)
def test_another_art_consumes_trama_generated_by_surto(path, expected_multiplier):
    combat = _combat(path, arts=(FIO, SURTO))
    primed = act(combat, SURTO, target_id="enemy")
    assert primed.fighters["player"].path_state["trama_state"]["origin_art"] == SURTO

    result = act(primed, FIO, target_id="enemy")
    event = _event(result, FIO)

    assert event.path_power_multiplier == expected_multiplier
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert "trama_state" not in result.fighters["player"].path_state


def test_expired_trama_is_not_consumed_and_surto_generates_a_fresh_window():
    combat = _combat()
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 0,
        "applied_opportunity": actor.opportunity,
    }

    result = act(combat, SURTO, target_id="enemy")

    assert _event(result).path_power_multiplier == D(1)
    assert not _event(result).class_resource_changes
    assert result.fighters["player"].path_state["trama_state"]["origin_art"] == SURTO


def test_invalid_target_does_not_consume_trama_start_cooldown_or_resolve_damage():
    combat = _combat(arts=(FIO, SURTO))
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    trama_before = actor.path_state["trama_state"].copy()
    enemy_hp = combat.fighters["enemy"].hp

    rejected = act(combat, SURTO, target_id=actor.id)

    assert rejected is combat
    assert actor.path_state["trama_state"] == trama_before
    assert SURTO not in actor.cooldowns
    assert combat.fighters["enemy"].hp == enemy_hp
    assert not any(event.action == SURTO for event in combat.events)


def test_committed_miss_consumes_different_origin_trama_without_returning_it():
    combat = _combat(arts=(FIO, SURTO))
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    combat.fighters["enemy"].stats = replace(
        combat.fighters["enemy"].stats, evasion=D("100")
    )

    result = act(combat, SURTO, target_id="enemy")
    event = _event(result)

    assert event.dodged
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert "trama_state" not in result.fighters["player"].path_state
    assert SURTO in result.fighters["player"].cooldowns


def test_full_barrier_absorption_does_not_return_consumed_trama():
    combat = _combat(arts=(FIO, SURTO))
    actor = combat.fighters["player"]
    target = combat.fighters["enemy"]
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }
    target_hp = target.hp
    _apply_barrier(
        target,
        applier_id="enemy",
        effect_definition_id="test.protection",
        value=1000,
        duration=2,
        applied_opportunity=target.opportunity,
        round_number=combat.round,
    )

    result = act(combat, SURTO, target_id="enemy")
    event = _event(result)

    assert event.calculated_damage > 0
    assert event.barrier_absorbed == event.calculated_damage
    assert event.effective_damage == 0
    assert result.fighters["enemy"].hp == target_hp
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert "trama_state" not in result.fighters["player"].path_state


def test_trama_duradoura_extends_surto_origin_and_consumption_talents_apply_once():
    generated = _combat(level=34)
    generated.fighters["player"].talent_ids = ("talent.tecelao.trama_duradoura",)
    with_trama = act(generated, SURTO, target_id="enemy")
    assert with_trama.fighters["player"].path_state["trama_state"]["remaining"] == 3

    combat = _combat(level=55)
    actor = combat.fighters["player"]
    actor.talent_ids = (
        "talent.tecelao.trama_agressiva",
        "talent.tecelao.trama_precisa",
        "talent.tecelao.alternancia_fluida",
    )
    actor.path_state["trama_state"] = {
        "origin_art": FIO,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    result = act(combat, SURTO, target_id="enemy")
    event = _event(result)

    assert event.path_power_multiplier == D("1.17")
    assert event.path_crit_bonus == D(2)
    # The crit roll is random (Trama Precisa raises its chance): follow the event's roll.
    assert event.calculated_damage == direct_damage(
        D("100"), D("1.45") * D("1.17"), D(0), 55, critical=event.critical
    )
    assert "trama_state" not in result.fighters["player"].path_state
    assert any(
        effect.id == "class_mechanic.tecelao.alternancia_fluida.agility"
        for effect in result.fighters["player"].effects
    )


def test_doctrine_includes_surto_only_at_level_34_without_path_or_weapon_requirement():
    def views(level):
        collection = DoctrineCollectionView(
            character_name="Tecelão",
            character_class="tecelao",
            selected_path=None,
            configuration_version=1,
            foreground=False,
            current_configuration={
                "path": None,
                "equipment": {},
                "arts": {},
                "talents": [],
            },
            doctrines=(),
            crowns=1000,
            level=level,
        )
        doctrine = DoctrineView(
            doctrine_id=uuid4(),
            name="Surto",
            revision=1,
            configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
            is_current=False,
            incomplete_reason=None,
            can_apply=True,
        )
        return collection, doctrine

    low_view, low_doctrine = views(33)
    ready_view, ready_doctrine = views(34)
    assert SURTO not in doctrine_art_ids(low_view, low_doctrine)
    assert SURTO in doctrine_art_ids(ready_view, ready_doctrine)


async def _seed_tecelao(database, actor: int, level: int):
    _, sessions = database
    stats = resolve_combat_stats("tecelao", level, "remanescente")
    character_id = uuid4()
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name="Ventos",
                race="remanescente",
                character_class="tecelao",
                selected_path=None,
                stage="menu:ready",
                ruleset_version="gdd-1.4.7-baseline-1.0",
                level=level,
                xp=0,
                hp=stats.hp,
                max_hp=stats.hp,
                vigor=100,
                max_vigor=100,
                crowns=0,
            )
        )
    return character_id, sessions


@pytest.mark.asyncio
async def test_surto_level_gate_three_slots_persistence_and_ui(database):
    actor = 8840801
    _, sessions = await _seed_tecelao(database, actor, 33)
    service = ActiveArtService(sessions, "ocaso")

    low = await service.view(actor)
    assert low is not None and SURTO not in low.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, SURTO)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, low.character_id)
        character.level = 34

    view = await service.view(actor)
    assert view is not None and SURTO in view.available_art_ids
    detail = render_art_detail(view, SURTO)
    assert "Surto do Véu" in detail.text
    assert "Nv.34" in detail.text
    assert "145% ATQ" in detail.text
    assert "1 Inimigo" in detail.text
    assert "3 Rodadas" in detail.text
    assert "Requisito de arma · Nenhum" in detail.text
    assert "Trama Encadeada" in detail.text

    await service.equip_art(actor, 1, FIO)
    await service.equip_art(actor, 2, TECELAO_ART_IDS["chama_tecida"])
    await service.equip_art(actor, 3, SURTO)
    with pytest.raises(ActiveArtMutationRejected) as invalid_slot:
        await service.equip_art(actor, 4, SURTO)
    assert invalid_slot.value.code == ActiveArtMutationCode.INVALID_SLOT

    async with sessions.begin() as session:
        character = await session.get(Character, view.character_id)
        config = await load_active_art_configuration(session, character)
    assert config.art_ids == (
        FIO,
        TECELAO_ART_IDS["chama_tecida"],
        SURTO,
    )
    actions = class_player_actions("tecelao", config.art_ids, "runico")
    assert SURTO in actions
