import asyncio
from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace
from uuid import uuid4

import pytest

from asterion.application.active_arts import (
    ActiveArtMutationCode,
    ActiveArtMutationRejected,
    ActiveArtService,
    load_active_art_configuration,
)
from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.application.round import RoundService
from asterion.bot.character_progression_ui import render_art_detail
from asterion.bot.combat_ui import event_line
from asterion.bot.doctrines_ui import doctrine_art_ids
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    ACTIVE_ART_IDS_BY_CLASS,
    LUMINAR_ART_IDS,
    LUMINAR_ART_LEVELS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    Action,
    Fighter,
    act,
    action_target_ids,
    allowed_actions,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import Account, Character

LUZ = LUMINAR_ART_IDS["luz_restauradora"]


def _combat(
    *, path: str | None = "guardiao", ally: bool = False, talents=(),
    hp=D("500"), level=20,
):
    stats = resolve_combat_stats("luminar", level, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Luminar", "luminar", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET

    player = state.fighters["player"]
    player.level = level
    player.character_class = "luminar"
    player.selected_path = path
    player.talent_ids = tuple(talents)
    player.side = "player"
    player.stats = replace(
        stats,
        hp=D("1000"),
        attack=D("100"),
        defense=D("100"),
        agility=D("100"),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    player.hp = hp

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
            level=20,
            stats=ally_stats,
            hp=D("500"),
            race="remanescente",
            character_class="sentinela",
            side="player",
            takes_turn=False,
        )
        state.party_mode = True
        state.manual_sides = ("player",)

    state.player_actions = class_player_actions("luminar", (LUZ,), path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _event(state, action_id=LUZ):
    return next(event for event in state.events if event.action == action_id)


def test_luz_is_the_level_18_class_art_and_has_one_hybrid_support_action():
    definition = active_art_definition(LUZ)
    assert definition is not None
    assert definition.character_class == "luminar"
    assert definition.min_level == 18
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset()
    assert LUZ in ACTIVE_ART_IDS_BY_CLASS["luminar"]
    assert LUMINAR_ART_LEVELS[LUZ] == 18
    assert LUZ not in ACTIVE_ART_IDS_BY_CLASS["oraculo"]

    for path in ("guardiao", "inquisidor", None):
        action = class_player_actions("luminar", (LUZ,), path)[LUZ]
        assert action.name == "Luz Restauradora"
        assert action.coefficient == 0
        assert action.heal_coefficient == D("0.70")
        assert action.target_barrier_coefficient == D("0.35")
        assert action.target_barrier_duration == 2
        assert action.cooldown == 4
        assert action.target_mode == "ally"
        assert not action.effect_removal
        assert not action.native_dot_kind


def test_luz_heals_and_barriers_in_one_action_and_reconnect_preserves_result():
    state = _combat(path=None, hp=D("500"))
    actor = state.fighters["player"]
    opportunity = actor.opportunity

    result = act(state, LUZ, target_id=actor.id)
    actor_after = result.fighters["player"]
    event = _event(result)

    assert actor_after.hp == D("570")
    assert actor_after.barrier == D("35")
    assert actor_after.barrier_remaining == 2
    assert actor_after.barrier_source == f"{actor.id}:{LUZ}"
    assert [
        (layer.identity, layer.value, layer.remaining) for layer in actor_after.barriers
    ] == [((actor.id, LUZ), D("35"), 2)]
    assert actor_after.stats.hp == D("1000")
    assert actor_after.cooldowns[LUZ] == opportunity + 4
    assert actor_after.action_use_counts[LUZ] == 1
    assert actor_after.path_state["luminar_state"]["kind"] == "julgamento"
    assert actor_after.path_state["luminar_state"]["remaining"] == 2
    assert event.healed == event.effective_healing == D("70")
    assert event.barrier_value == D("35")
    assert event.action_instance_id
    assert len([item for item in result.events if item.action == LUZ]) == 1

    line = event_line(result, event, viewer_key="player")
    assert "Cura efetiva" in line and "70" in line
    assert "Barreira" in line and "35" in line and "2T" in line

    restored = decode(encode(result), result.id, result.ruleset, result.version)
    restored_actor = restored.fighters["player"]
    assert restored_actor.hp == actor_after.hp
    assert restored_actor.barrier == actor_after.barrier
    assert restored_actor.barrier_remaining == 2
    assert restored_actor.barrier_source == actor_after.barrier_source
    assert restored_actor.cooldowns[LUZ] == opportunity + 4
    assert restored_actor.path_state["luminar_state"] == actor_after.path_state[
        "luminar_state"
    ]
    assert act(restored, LUZ, target_id=restored_actor.id) is restored


@pytest.mark.parametrize(
    ("path", "power", "expected_heal", "expected_barrier"),
    (("guardiao", D("1.15"), D("80"), D("40")),
     ("inquisidor", D("1.06"), D("74"), D("37")),
     (None, D("1.10"), D("77"), D("38"))),
)
def test_fulgor_strengthens_both_components_once_by_current_path(
    path, power, expected_heal, expected_barrier
):
    state = _combat(path=path, hp=D("500"))
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    result = act(state, LUZ, target_id=actor.id)
    actor_after = result.fighters["player"]
    event = _event(result)

    assert event.effective_healing == expected_heal
    assert event.barrier_value == expected_barrier
    assert "luminar.fulgor_consumido" in event.path_triggers
    assert event.class_resource_changes == (("luminar_state", actor.id, 1, 0),)
    assert "luminar_state" not in actor_after.path_state
    assert "luminar.fulgor_gerado" not in event.path_triggers
    assert "luminar.julgamento_gerado" not in event.path_triggers


def test_luz_applies_eligible_luminar_talents_without_double_counting_fulgor():
    talents = (
        "talent.luminar.egide_densa",
        "talent.luminar.cura_prudente",
        "talent.luminar.alternancia_radiante",
        "talent.luminar.fluxo_restaurador",
        "talent.luminar.contraluz_perfeita",
    )
    state = _combat(path="guardiao", talents=talents, hp=D("300"), level=55)
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    result = act(state, LUZ, target_id=actor.id)
    actor_after = result.fighters["player"]
    event = _event(result)

    assert event.effective_healing == D("85")  # floor(100 × .70 × 1.05 × 1.17)
    assert event.barrier_value == D("42")  # floor(100 × .35 × 1.17 × 1.04)
    assert event.class_resource_changes == (("luminar_state", actor.id, 1, 0),)
    assert "luminar.cura_prudente" in event.path_triggers
    assert "luminar.egide_densa" in event.path_triggers
    assert any(
        effect.id == "class_mechanic.luminar.alternancia_radiante.agility"
        and effect.magnitude == D("0.04")
        and effect.remaining == 1
        for effect in actor_after.effects
    )
    assert any(
        effect.id == "class_mechanic.luminar.fluxo_restaurador.defense"
        and effect.magnitude == D("0.04")
        and effect.remaining == 1
        for effect in actor_after.effects
    )


def test_luz_consumes_fulgor_even_at_zero_effective_healing_but_fluxo_requires_healing():
    state = _combat(path="inquisidor", hp=D("1000"), talents=("talent.luminar.fluxo_restaurador",))
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "fulgor",
        "remaining": 2,
        "applied_opportunity": actor.opportunity,
    }

    result = act(state, LUZ, target_id=actor.id)
    actor_after = result.fighters["player"]
    event = _event(result)

    assert event.effective_healing == 0
    assert event.barrier_value == D("37")
    assert event.class_resource_changes == (("luminar_state", actor.id, 1, 0),)
    assert "luminar_state" not in actor_after.path_state
    assert not any("fluxo_restaurador" in effect.id for effect in actor_after.effects)
    assert not any("luminar.julgamento_gerado" in trigger for trigger in event.path_triggers)


def test_luz_renews_existing_julgamento_without_consuming_it_or_generating_fulgor():
    state = _combat(path="guardiao", hp=D("500"))
    actor = state.fighters["player"]
    actor.path_state["luminar_state"] = {
        "kind": "julgamento",
        "remaining": 1,
        "applied_opportunity": actor.opportunity,
    }

    result = act(state, LUZ, target_id=actor.id)
    actor_after = result.fighters["player"]
    event = _event(result)

    assert actor_after.path_state["luminar_state"]["kind"] == "julgamento"
    assert actor_after.path_state["luminar_state"]["remaining"] == 2
    assert not event.class_resource_changes
    assert "luminar.julgamento_gerado" in event.path_triggers
    assert "luminar.fulgor_gerado" not in event.path_triggers


def test_luz_generates_three_turn_julgamento_with_contraluz_persistente():
    state = _combat(
        path="inquisidor",
        talents=("talent.luminar.contraluz_persistente",),
        level=20,
    )
    actor = state.fighters["player"]

    result = act(state, LUZ, target_id=actor.id)

    assert result.fighters["player"].path_state["luminar_state"] == {
        "kind": "julgamento",
        "remaining": 3,
        "applied_opportunity": actor.opportunity,
    }


def test_luz_overheal_is_discarded_and_does_not_increase_barrier():
    state = _combat(path=None, hp=D("1000"))
    actor = state.fighters["player"]

    result = act(state, LUZ, target_id=actor.id)
    event = _event(result)

    assert result.fighters["player"].hp == D("1000")
    assert event.healed == event.effective_healing == 0
    assert event.effective_healing == 0
    assert event.barrier_value == D("35")
    line = event_line(result, event, viewer_key="player")
    assert "Cura efetiva" in line and "0" in line


def test_luz_targets_only_the_explicit_living_ally_and_rejects_invalid_target():
    state = _combat(ally=True)
    actor = state.fighters["player"]
    ally = state.fighters["ally"]
    enemy = state.fighters["enemy"]
    assert set(action_target_ids(state, LUZ)) == {actor.id, ally.id}

    assert act(state, LUZ) is state
    assert act(state, LUZ, target_id=enemy.id) is state
    assert act(state, LUZ, target_id="outside-encounter") is state
    assert not actor.cooldowns
    assert "luminar_state" not in actor.path_state

    result = act(state, LUZ, target_id=ally.id)
    target = result.fighters["ally"]
    owner = result.fighters["player"]
    event = _event(result)
    assert target.hp == D("570")
    assert target.barrier == D("35")
    assert owner.hp == D("500")
    assert owner.barrier == 0
    assert event.target == ally.id
    assert owner.path_state["luminar_state"]["kind"] == "julgamento"

    dead = _combat(ally=True)
    dead.fighters["ally"].hp = 0
    assert dead.fighters["ally"].id not in action_target_ids(dead, LUZ)
    assert act(dead, LUZ, target_id=dead.fighters["ally"].id) is dead


def test_barriers_from_distinct_sources_coexist():
    state = _combat(path=None, hp=D("500"))
    actor = state.fighters["player"]
    actor.barrier = D("50")
    actor.barrier_remaining = 1
    actor.barrier_applied_opportunity = actor.opportunity
    actor.barrier_source = "other_applier:other.effect"

    result = act(state, LUZ, target_id=actor.id)

    # GDD §9.4 requires independent sources to coexist; Luz contributes 35.
    assert result.fighters["player"].barrier == D("85")


def test_luz_recovery_is_selected_by_round_only_when_equipped_and_effective():
    combat = _combat(path="guardiao", hp=D("300"))
    actions = allowed_actions(combat)
    state = SimpleNamespace(prepared_heal=False, prepared_purify=False)

    combat.fighters["player"].stats = replace(
        combat.fighters["player"].stats, attack=D("200")
    )
    choice = asyncio.run(
        RoundService._choose_round_action(
            object.__new__(RoundService),
            None,
            None,
            state,
            combat,
            consumable_uses=0,
            consumable_limit=0,
        )
    )
    assert choice == ("action_self", LUZ)
    assert RoundService._recovery_art_choice(combat, actions) == LUZ


async def _seed_luminar(database, actor: int, *, level: int, path: str | None):
    _, sessions = database
    stats = resolve_combat_stats("luminar", level, "remanescente", selected_path=path)
    character_id = uuid4()
    suffix = "".join(chr(ord("a") + int(digit)) for digit in str(actor)[-5:])
    async with sessions.begin() as session:
        session.add(Account(telegram_id=actor))
        session.add(
            Character(
                id=character_id,
                telegram_id=actor,
                server_id="ocaso",
                name=f"Restaurador{suffix}"[:16],
                race="remanescente",
                character_class="luminar",
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
async def test_luz_level_gate_persistence_ui_doctrine_and_path_revalidation(database):
    actor = 9060501
    character_id, sessions = await _seed_luminar(database, actor, level=17, path="guardiao")
    service = ActiveArtService(sessions, "ocaso")

    level_17 = await service.view(actor)
    assert level_17 is not None and LUZ not in level_17.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor, 1, LUZ)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 18
    eligible = await service.view(actor)
    assert eligible is not None and LUZ in eligible.available_art_ids
    screen = render_art_detail(eligible, LUZ)
    assert "Luz Restauradora" in screen.text
    assert "70% ATQ" in screen.text and "35% ATQ" in screen.text
    assert "2T" in screen.text and "Recarga · 4 Rodadas" in screen.text
    assert "Você ou Aliado" in screen.text
    assert "Requisito de arma · Nenhum" in screen.text

    await service.equip_art(actor, 1, LUZ)
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
    assert snapshot.art_ids == (LUZ,)
    assert snapshot.combat_configuration_version == 1

    collection = DoctrineCollectionView(
        character_name="Luminar",
        character_class="luminar",
        selected_path="guardiao",
        configuration_version=1,
        foreground=False,
        current_configuration={"path": "guardiao", "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=18,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Luz Restauradora",
        revision=1,
        configuration={"path": "guardiao", "equipment": {}, "arts": {"1": LUZ}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert LUZ in doctrine_art_ids(collection, doctrine)

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 17
    after_level_loss = await service.view(actor)
    assert after_level_loss is not None and LUZ not in after_level_loss.available_art_ids
    assert LUZ in after_level_loss.ineligible_art_ids


def test_luz_requires_no_weapon_and_does_not_make_other_classes_eligible():
    assert ACTIVE_ART_DEFINITIONS[LUZ].weapon_requirement == frozenset()
    for other_class in ("sentinela", "errante", "vigia", "tecelao", "oraculo"):
        assert LUZ not in ACTIVE_ART_IDS_BY_CLASS[other_class]
        with pytest.raises(ValueError):
            class_player_actions(other_class, (LUZ,))
