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
from asterion.bot.character_progression_ui import render_art_detail
from asterion.bot.combat_ui import event_line
from asterion.bot.doctrines_ui import doctrine_art_ids
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    ORACULO_ART_IDS,
    ORACULO_ART_LEVELS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Fighter,
    act,
    action_target_ids,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import Account, Character

AUGURIO = ORACULO_ART_IDS["augurio_favoravel"]
BUFF_ID = "oraculo.augurio_favoravel.attack"


def _combat(*, path: str | None = "agoureiro", ally: bool = False, talents=()):
    stats = resolve_combat_stats("oraculo", 18, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Oráculo", "oraculo", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET

    player = state.fighters["player"]
    player.level = 18
    player.character_class = "oraculo"
    player.selected_path = path
    player.talent_ids = tuple(talents)
    player.side = "player"
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

    enemy = state.fighters["enemy"]
    enemy.stats = replace(
        enemy.stats,
        hp=D("10000"),
        attack=D("20"),
        defense=D(0),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = enemy.stats.hp
    enemy.side = "enemy"
    enemy.takes_turn = False

    if ally:
        ally_stats = replace(player.stats, attack=D("100"), agility=D("50"))
        state.fighters["ally"] = Fighter(
            id="ally-entity",
            name="Aliada",
            level=18,
            stats=ally_stats,
            hp=ally_stats.hp,
            race="remanescente",
            character_class="sentinela",
            side="player",
            takes_turn=False,
        )
        state.party_mode = True
        state.manual_sides = ("player",)

    state.player_actions = class_player_actions("oraculo", (AUGURIO,), path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def test_augurio_is_level_18_class_art_for_both_paths_and_no_weapon_gate():
    definition = active_art_definition(AUGURIO)
    assert definition is not None
    assert definition.character_class == "oraculo"
    assert definition.min_level == 18
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset()
    assert ORACULO_ART_LEVELS[AUGURIO] == 18
    assert AUGURIO in ACTIVE_ART_IDS_BY_CLASS["oraculo"]
    assert ACTIVE_ART_DEFINITIONS[AUGURIO] is definition

    for path in ("agoureiro", "invocador", None):
        action = class_player_actions("oraculo", (AUGURIO,), path)[AUGURIO]
        assert action.name == "Augúrio Favorável"
        assert action.coefficient == D(0)
        assert action.cooldown == 4
        assert action.target_mode == "ally"
        assert len(action.target_effects) == 1
        effect = action.target_effects[0]
        assert (effect.id, effect.stat, effect.magnitude, effect.duration, effect.kind) == (
            BUFF_ID,
            "attack",
            D("0.10"),
            2,
            "buff",
        )
        assert effect.removable and not effect.unremovable

    assert AUGURIO not in ACTIVE_ART_IDS_BY_CLASS["luminar"]
    with pytest.raises(ValueError):
        class_player_actions("luminar", (AUGURIO,))


def test_augurio_can_target_self_in_solo_and_persists_buff_pressagio_and_cooldown():
    state = _combat(path=None)
    actor = state.fighters["player"]
    assert action_target_ids(state, AUGURIO) == (actor.id,)
    opportunity = actor.opportunity

    resolved = act(state, AUGURIO, target_id=actor.id)
    result = resolved.fighters["player"]
    effect = next(effect for effect in result.effects if effect.id == BUFF_ID)
    event = next(event for event in resolved.events if event.action == AUGURIO)

    assert result.stats.attack == D("100")
    assert result.stat("attack") == D("110.00")
    assert (effect.magnitude, effect.remaining, effect.kind) == (D("0.10"), 2, "buff")
    assert effect.application_event
    assert effect.instance_id
    assert event.target == result.id
    assert event.actor_entity_id == actor.id
    assert event.applied_effect_stat == "attack"
    assert event.applied_effect_magnitude == D("0.10")
    assert event.applied_effect_duration == 2
    assert event.applied_effect_kind == "buff"
    assert result.cooldowns[AUGURIO] == opportunity + 4
    assert result.action_use_counts[AUGURIO] == 1
    assert result.path_state["omen_defensive"][result.id] == {
        "remaining": 2,
        "applied_opportunity": opportunity,
    }
    assert "omen_offensive" not in result.path_state
    assert "oraculo.pressagio_defensive_criado" in event.path_triggers
    assert not event.class_resource_changes

    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    restored_actor = restored.fighters["player"]
    restored_effect = next(effect for effect in restored_actor.effects if effect.id == BUFF_ID)
    assert restored_effect == effect
    assert restored_actor.stats.attack == D("100")
    assert restored_actor.stat("attack") == D("110.00")
    assert restored_actor.cooldowns[AUGURIO] == opportunity + 4
    assert restored_actor.path_state["omen_defensive"][restored_actor.id] == {
        "remaining": 2,
        "applied_opportunity": opportunity,
    }
    assert act(resolved, AUGURIO, target_id=actor.id) is resolved


def test_augurio_expiration_uses_the_targets_two_opportunities():
    state = _combat(path="invocador")
    state = act(state, AUGURIO, target_id=state.fighters["player"].id)
    effect = next(effect for effect in state.fighters["player"].effects if effect.id == BUFF_ID)
    assert effect.remaining == 2

    state = act(state, "attack", target_id=state.fighters["enemy"].id)
    effect = next(effect for effect in state.fighters["player"].effects if effect.id == BUFF_ID)
    assert effect.remaining == 1
    state = act(state, "attack", target_id=state.fighters["enemy"].id)
    assert not any(effect.id == BUFF_ID for effect in state.fighters["player"].effects)
    assert state.fighters["player"].stats.attack == D("100")
    assert state.fighters["player"].stat("attack") == D("100")


def test_augurio_targets_only_the_explicit_ally_and_generates_defensive_omen_there():
    state = _combat(ally=True)
    actor = state.fighters["player"]
    ally = state.fighters["ally"]
    enemy = state.fighters["enemy"]
    assert set(action_target_ids(state, AUGURIO)) == {actor.id, ally.id}

    no_selection = act(state, AUGURIO)
    assert no_selection is state
    invalid = act(state, AUGURIO, target_id=enemy.id)
    assert invalid is state
    invalid = act(state, AUGURIO, target_id="character-outside-encounter")
    assert invalid is state
    assert not actor.cooldowns

    resolved = act(state, AUGURIO, target_id=ally.id)
    target = resolved.fighters["ally"]
    owner = resolved.fighters["player"]
    effect = next(effect for effect in target.effects if effect.id == BUFF_ID)
    event = next(event for event in resolved.events if event.action == AUGURIO)

    assert target.stats.attack == D("100")
    assert target.stat("attack") == D("110.00")
    assert not any(effect.id == BUFF_ID for effect in owner.effects)
    assert owner.path_state["omen_defensive"] == {
        target.id: {"remaining": 2, "applied_opportunity": actor.opportunity}
    }
    assert event.actor_entity_id == owner.id
    assert event.target == target.id
    assert event.applied_effect_kind == "buff"
    assert event.effect_id == BUFF_ID
    assert effect.application_event == event.effect_application_event_id
    assert "oraculo.pressagio_defensive_criado" in event.path_triggers

    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    restored_owner = restored.fighters["player"]
    restored_target = restored.fighters["ally"]
    assert restored_target.stat("attack") == D("110.00")
    assert restored_owner.path_state["omen_defensive"][target.id] == owner.path_state[
        "omen_defensive"
    ][target.id]
    line = event_line(
        restored,
        next(event for event in restored.events if event.action == AUGURIO),
        viewer_key="player",
    )
    assert "Augúrio Favorável" in line
    assert "+<code>10% ATQ</code>" in line
    assert "Presságio Defensivo gerado" in line and "Aliada" in line


def test_augurio_renews_its_buff_and_omen_without_consuming_a_preexisting_omen():
    state = _combat(ally=True)
    actor = state.fighters["player"]
    ally = state.fighters["ally"]
    actor.path_state["omen_defensive"] = {
        ally.id: {"remaining": 1, "applied_opportunity": actor.opportunity}
    }
    first = act(state, AUGURIO, target_id=ally.id)
    actor_after = first.fighters["player"]
    assert actor_after.path_state["omen_defensive"][ally.id]["remaining"] == 2

    while actor_after.cooldowns[AUGURIO] > actor_after.opportunity:
        first = act(first, "attack", target_id=first.fighters["enemy"].id)
        actor_after = first.fighters["player"]
    reapplication = act(first, AUGURIO, target_id=ally.id)
    target_effects = [
        effect for effect in reapplication.fighters["ally"].effects if effect.id == BUFF_ID
    ]
    assert len(target_effects) == 1
    assert target_effects[0].remaining == 2
    assert reapplication.fighters["player"].path_state["omen_defensive"][ally.id][
        "remaining"
    ] == 2
    events = [event for event in reapplication.events if event.action == AUGURIO]
    assert len(events) == 2
    assert all(not event.class_resource_changes for event in events)
    assert "omen_offensive" not in reapplication.fighters["player"].path_state


def test_augurio_uses_sinal_persistente_only_for_its_defensive_omen_window():
    state = _combat(
        talents=("talent.oraculo.sinal_persistente",),
    )
    resolved = act(state, AUGURIO, target_id=state.fighters["player"].id)
    mark = resolved.fighters["player"].path_state["omen_defensive"][
        resolved.fighters["player"].id
    ]
    assert mark["remaining"] == 3
    effect = next(effect for effect in resolved.fighters["player"].effects if effect.id == BUFF_ID)
    assert effect.remaining == 2


def test_augurio_doctrine_choices_follow_class_level_and_do_not_add_a_weapon_gate():
    view = DoctrineCollectionView(
        character_name="Oráculo",
        character_class="oraculo",
        selected_path="agoureiro",
        configuration_version=4,
        foreground=False,
        current_configuration={"path": "agoureiro", "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=18,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Augúrio",
        revision=1,
        configuration={"path": "agoureiro", "equipment": {}, "arts": {"1": AUGURIO}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert AUGURIO in doctrine_art_ids(view, doctrine)


async def _seed_oraculo(database, actor: int, *, level: int, path: str | None):
    _, sessions = database
    stats = resolve_combat_stats("oraculo", level, "remanescente", selected_path=path)
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:])
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Augurio{suffix}"[:16],
                race="remanescente",
                character_class="oraculo",
                selected_path=path,
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
async def test_augurio_level_gate_configuration_ui_doctrine_and_post_legado_revalidation(database):
    actor = 9060401
    character_id, sessions = await _seed_oraculo(database, actor, level=17, path=None)
    service = ActiveArtService(sessions, "ocaso")

    level_17 = await service.view(actor)
    assert level_17 is not None and AUGURIO not in level_17.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, AUGURIO)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 18
    eligible = await service.view(actor)
    assert eligible is not None and AUGURIO in eligible.available_art_ids
    assert eligible.selected_path is None
    screen = render_art_detail(eligible, AUGURIO)
    assert "Augúrio Favorável" in screen.text
    assert "+10.00%" in screen.text and "ATQ" in screen.text
    assert "2T" in screen.text and "Recarga · 4 Rodadas" in screen.text
    assert "Você ou Aliado" in screen.text
    assert "Requisito de arma · Nenhum" in screen.text
    assert "gera Presságio Defensivo" in screen.text

    mutation = await service.equip_art(actor, 1, AUGURIO)
    assert mutation is not None and mutation.changed
    await service.equip_art(actor, 2, ORACULO_ART_IDS["sinal_funesto"])
    await service.equip_art(actor, 3, ORACULO_ART_IDS["vislumbre"])
    with pytest.raises(ActiveArtMutationRejected) as invalid_slot:
        await service.equip_art(actor, 4, AUGURIO)
    assert invalid_slot.value.code == ActiveArtMutationCode.INVALID_SLOT

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
    assert snapshot.art_ids == (
        AUGURIO,
        ORACULO_ART_IDS["sinal_funesto"],
        ORACULO_ART_IDS["vislumbre"],
    )
    assert snapshot.combat_configuration_version == 3

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 17
    after_level_loss = await service.view(actor)
    assert after_level_loss is not None
    assert AUGURIO not in after_level_loss.available_art_ids
    assert AUGURIO in after_level_loss.ineligible_art_ids
