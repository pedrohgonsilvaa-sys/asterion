from dataclasses import replace
from decimal import Decimal as D
from uuid import UUID, uuid4

import pytest

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.bot.character_progression_ui import render_art_detail
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    TECELAO_ART_IDS,
    TECELAO_ART_LEVELS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, act, purifiable, start_combat
from asterion.domain.combat_math import (
    CURRENT_COMBAT_RULESET,
    direct_damage,
    resolve_combat_stats,
)
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import Account, Character

GEADA = "class_art.tecelao.geada_tecida"
GEADA_AGILITY = "class_art.tecelao.geada_tecida"


@pytest.mark.parametrize("path", ("conjurador", "runico"))
def test_geada_catalogue_is_class_art_for_both_tecelao_paths(path):
    definition = active_art_definition(GEADA)
    assert definition is not None
    assert definition.character_class == "tecelao"
    assert definition.path_id is None
    assert definition.min_level == 18
    assert not definition.weapon_requirement
    assert TECELAO_ART_LEVELS[GEADA] == 18
    assert GEADA in ACTIVE_ART_IDS_BY_CLASS["tecelao"]
    assert ACTIVE_ART_DEFINITIONS[GEADA] is definition

    action = class_player_actions("tecelao", (GEADA,), selected_path=path)[GEADA]
    assert action.name == "Geada Tecida"
    assert action.coefficient == D("0.90")
    assert action.attack_debuff == D("0.15")
    assert action.effect_stat == "agility"
    assert action.duration == 2
    assert action.cooldown == 3
    assert action.target_mode == "opponent"
    assert action.effect_id == GEADA_AGILITY
    assert action.prepares_chain is None
    assert action.consumes_chain is None
    assert class_player_actions("tecelao", (GEADA,), selected_path=None)[GEADA].id == GEADA
    assert GEADA not in class_player_actions("tecelao", (), path)
    assert GEADA not in ACTIVE_ART_IDS_BY_CLASS["sentinela"]
    with pytest.raises(ValueError):
        class_player_actions("sentinela", (GEADA,))


def _combat(path: str, *, enemy_turns: bool = False):
    stats = resolve_combat_stats("tecelao", 18, "remanescente", selected_path=path)
    combat = PROFILE.create(
        UUID("735a8a63-d8c9-4b38-a8ac-cad48194d5d2"),
        "Geada",
        "tecelao",
        "remanescente",
        stats.hp,
    )
    combat.tutorial = None
    combat.ruleset = CURRENT_COMBAT_RULESET
    player = combat.fighters["player"]
    player.level = 18
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
    enemy.level = 18
    enemy.stats = replace(
        enemy.stats,
        hp=D("5000"),
        attack=D("20"),
        defense=D("0"),
        agility=D("100"),
        evasion=D(0),
        block=D(0),
        crit=D(0),
    )
    enemy.hp = enemy.stats.hp
    enemy.takes_turn = enemy_turns
    combat.player_actions = class_player_actions("tecelao", (GEADA,), path)
    combat.enemy_actions = {"wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")}
    combat.ai_cycle = ("wait",)
    return start_combat(combat)


@pytest.mark.parametrize("path", ("conjurador", "runico"))
def test_geada_resolves_90_percent_damage_and_persistent_two_turn_agility_debuff(path):
    combat = _combat(path)
    actor = combat.fighters["player"]
    target = combat.fighters["enemy"]
    actor_opportunity = actor.opportunity

    resolved = act(combat, GEADA, target_id=target.id)
    event = next(event for event in resolved.events if event.action == GEADA)
    target_after = resolved.fighters["enemy"]
    debuff = next(effect for effect in target_after.effects if effect.id == GEADA_AGILITY)

    assert event.calculated_damage == direct_damage(
        D("100"), D("0.90"), D("0"), 18, critical=False
    )
    assert event.applied_effect_stat == "agility"
    assert event.applied_effect_magnitude == D("0.15")
    assert event.applied_effect_duration == 2
    assert event.applied_effect_kind == "debuff"
    assert debuff.remaining == 2
    assert debuff.application_event
    assert target_after.stats.agility == D("100")
    assert target_after.stat("agility") == D("85.00")
    assert resolved.fighters["player"].stats.agility == D("200")
    assert resolved.fighters["player"].cooldowns[GEADA] == actor_opportunity + 3

    restored = decode(
        encode(resolved), resolved.id, resolved.ruleset, resolved.version
    )
    restored_debuff = next(
        effect for effect in restored.fighters["enemy"].effects if effect.id == GEADA_AGILITY
    )
    assert restored_debuff.remaining == 2
    assert restored_debuff.magnitude == D("0.15")
    assert restored_debuff.application_event == debuff.application_event
    assert restored.fighters["player"].cooldowns[GEADA] == actor_opportunity + 3
    assert purifiable(restored_debuff)


def test_geada_debuff_expires_after_two_target_opportunities():
    combat = _combat("conjurador", enemy_turns=True)
    first = act(combat, GEADA, target_id="enemy")
    event = next(event for event in first.events if event.action == GEADA)
    assert event.applied_effect_duration == 2
    effect = next(
        effect
        for effect in first.fighters["enemy"].effects
        if effect.id == GEADA_AGILITY
    )
    assert effect.remaining == 1

    second = act(first, "attack", target_id="enemy")
    assert not any(effect.id == GEADA_AGILITY for effect in second.fighters["enemy"].effects)


def test_geada_does_not_apply_agi_debuff_when_direct_attack_is_evaded():
    combat = _combat("runico")
    target = combat.fighters["enemy"]
    target.stats = replace(target.stats, evasion=D("100"))

    resolved = act(combat, GEADA, target_id=target.id)
    event = next(event for event in resolved.events if event.action == GEADA)
    assert event.dodged
    assert not any(effect.id == GEADA_AGILITY for effect in resolved.fighters["enemy"].effects)
    assert resolved.fighters["player"].cooldowns[GEADA] > 0


def test_geada_generates_its_own_trama_after_resolving():
    combat = _combat("conjurador")
    resolved = act(combat, GEADA, target_id="enemy")
    trama = resolved.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == GEADA
    assert trama["remaining"] == 2
    assert trama["applied_opportunity"] == combat.fighters["player"].opportunity
    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    assert restored.fighters["player"].path_state["trama_state"] == trama


@pytest.mark.parametrize(
    ("path", "expected_multiplier"),
    (("conjurador", D("1.15")), ("runico", D("1.06"))),
)
def test_geada_consumes_other_trama_once_and_strengthens_only_direct_damage(
    path, expected_multiplier
):
    combat = _combat(path)
    actor = combat.fighters["player"]
    actor.path_state["trama_state"] = {
        "origin_art": TECELAO_ART_IDS["chama_tecida"],
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    resolved = act(combat, GEADA, target_id="enemy")
    event = next(event for event in resolved.events if event.action == GEADA)

    assert event.path_power_multiplier == expected_multiplier
    assert event.class_resource_changes == (("trama", "player", 1, 0),)
    assert event.calculated_damage == direct_damage(
        D("100"), D("0.90") * expected_multiplier, D("0"), 18, critical=False
    )
    assert "trama_state" not in resolved.fighters["player"].path_state
    debuff = next(
        effect
        for effect in resolved.fighters["enemy"].effects
        if effect.id == GEADA_AGILITY
    )
    assert debuff.magnitude == D("0.15")
    assert debuff.remaining == 2


def test_geada_as_trama_origin_is_not_consumed_or_refreshed_by_same_art():
    combat = _combat("conjurador")
    actor = combat.fighters["player"]
    actor.cooldowns[GEADA] = actor.opportunity
    actor.path_state["trama_state"] = {
        "origin_art": GEADA,
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    resolved = act(combat, GEADA, target_id="enemy")
    trama = resolved.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == GEADA
    assert trama["remaining"] == 2


@pytest.mark.parametrize(
    ("path", "expected_multiplier"),
    (("conjurador", D("1.15")), ("runico", D("1.06"))),
)
def test_geada_consumes_a_runtime_trama_created_by_another_class_art(
    path, expected_multiplier
):
    combat = _combat(path)
    fio = TECELAO_ART_IDS["fio_cortante"]
    combat.player_actions = class_player_actions("tecelao", (fio, GEADA), path)

    primed = act(combat, fio, target_id="enemy")
    trama = primed.fighters["player"].path_state["trama_state"]
    assert trama["origin_art"] == fio

    resolved = act(primed, GEADA, target_id="enemy")
    event = next(event for event in resolved.events if event.action == GEADA)
    assert event.path_power_multiplier == expected_multiplier
    assert "trama_state" not in resolved.fighters["player"].path_state
    assert not resolved.fighters["player"].action_chains


def test_geada_trama_talents_modify_damage_once_without_strengthening_agi_debuff():
    combat = _combat("conjurador")
    actor = combat.fighters["player"]
    actor.talent_ids = (
        "talent.tecelao.trama_agressiva",
        "talent.tecelao.trama_precisa",
    )
    actor.path_state["trama_state"] = {
        "origin_art": TECELAO_ART_IDS["chama_tecida"],
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    resolved = act(combat, GEADA, target_id="enemy")
    event = next(event for event in resolved.events if event.action == GEADA)
    effect = next(
        effect
        for effect in resolved.fighters["enemy"].effects
        if effect.id == GEADA_AGILITY
    )

    assert event.path_power_multiplier == D("1.17")
    assert event.path_crit_bonus == D("2")
    assert effect.magnitude == D("0.15")
    assert effect.remaining == 2


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
                name="Geadas",
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
async def test_geada_level_gate_and_active_configuration_persist_without_weapon_gate(database):
    actor = 8840601
    _, sessions = await _seed_tecelao(database, actor, 17)
    service = ActiveArtService(sessions, "ocaso")

    before = await service.view(actor)
    assert before is not None
    assert GEADA not in before.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, GEADA)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, before.character_id)
        character.level = 18

    available = await service.view(actor)
    assert available is not None
    assert GEADA in available.available_art_ids
    screen = render_art_detail(available, GEADA)
    assert "Geada Tecida" in screen.text
    assert "90%" in screen.text
    assert "AGI" in screen.text and "15%" in screen.text
    assert "Recarga · 3 Rodadas" in screen.text
    assert "Requisito de arma · Nenhum" in screen.text
    assert "Trama Encadeada" in screen.text

    mutation = await service.equip_art(actor, 1, GEADA)
    assert mutation is not None and mutation.changed
    async with sessions.begin() as session:
        character = await session.get(Character, available.character_id)
        configuration = await load_active_art_configuration(session, character)
    assert configuration.art_ids == (GEADA,)
    assert configuration.combat_configuration_version == 1

    actions = class_player_actions("tecelao", configuration.art_ids, "runico")
    assert GEADA in actions
    assert active_art_definition(GEADA) is not None
    assert not active_art_definition(GEADA).weapon_requirement

    async with sessions.begin() as session:
        character = await session.get(Character, available.character_id)
        character.level = 17
    after_level_loss = await service.view(actor)
    assert after_level_loss is not None
    assert GEADA not in after_level_loss.available_art_ids
