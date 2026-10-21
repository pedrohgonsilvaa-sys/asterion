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
from asterion.domain.class_trials import (
    ORACULO_SELO_EFFECT_ID,
    class_player_actions,
)
from asterion.domain.combat import (
    Action,
    Effect,
    _apply_barrier,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import TALENT_DEFINITIONS
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import Account, Character

SELO = ORACULO_ART_IDS["selo_da_queda"]
SELO_EFFECT = ORACULO_SELO_EFFECT_ID
AUGURIO = ORACULO_ART_IDS["augurio_favoravel"]


def _combat(*, path: str | None = None, level: int = 34, talents=()):
    stats = resolve_combat_stats("oraculo", level, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Oráculo", "oraculo", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET

    actor = state.fighters["player"]
    actor.level = level
    actor.character_class = "oraculo"
    actor.selected_path = path
    actor.talent_ids = tuple(talents)
    actor.side = "player"
    actor.stats = replace(
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
    actor.hp = actor.stats.hp

    enemy = state.fighters["enemy"]
    enemy.race = "remanescente"
    enemy.stats = replace(
        enemy.stats,
        hp=D("10000"),
        attack=D("20"),
        defense=D("100"),
        agility=D(0),
        per=D(0),
        crit=D(0),
        evasion=D(0),
        block=D(0),
    )
    enemy.hp = enemy.stats.hp
    enemy.side = "enemy"
    enemy.takes_turn = False

    state.player_actions = class_player_actions("oraculo", (SELO,), path)
    state.enemy_actions = {
        "wait": Action("enemy.wait", "Aguardar", D(0), target_mode="self")
    }
    state.ai_cycle = ("wait",)
    return start_combat(state)


def _event(state, action_id=SELO):
    return next(
        event
        for event in reversed(state.events)
        if event.action == action_id and event.actor_entity_id == state.fighters["player"].id
    )


def _mark(state, fighter_key="enemy", *, remaining=2):
    actor = state.fighters["player"]
    target = state.fighters[fighter_key]
    actor.path_state.setdefault("omen_offensive", {})[target.id] = {
        "remaining": remaining,
        "applied_opportunity": actor.opportunity,
    }


def test_selo_catalogue_id_gates_paths_and_shared_action_contract():
    definition = active_art_definition(SELO)
    assert definition is not None
    assert definition.character_class == "oraculo"
    assert definition.min_level == 34
    assert definition.path_id is None
    assert definition.weapon_requirement == frozenset()
    assert SELO in ACTIVE_ART_IDS_BY_CLASS["oraculo"]
    assert ACTIVE_ART_DEFINITIONS[SELO] is definition
    assert ORACULO_ART_LEVELS[SELO] == 34
    assert SELO == "class_art.oraculo.selo_da_queda"

    for path in ("agoureiro", "invocador", None):
        actions = class_player_actions("oraculo", (SELO,), path)
        action = actions[SELO]
        assert (action.name, action.coefficient, action.cooldown) == (
            "Selo da Queda",
            D("1.00"),
            3,
        )
        assert (action.attack_debuff, action.effect_stat, action.duration) == (
            D("0.10"),
            "defense",
            2,
        )
        assert action.effect_id == SELO_EFFECT
        assert action.hit_count == 1
        assert action.target_mode == "opponent"
        assert action.native_dot_kind is None
        assert action.heal_coefficient == 0
        assert action.target_barrier_coefficient == 0

    with pytest.raises(ValueError, match="Unknown"):
        class_player_actions("luminar", (SELO,))


def test_selo_resolves_damage_before_applying_its_normal_defense_debuff():
    state = _combat(path="agoureiro")
    opportunity = state.fighters["player"].opportunity
    baseline = act(state, "attack", target_id=state.fighters["enemy"].id)
    baseline_event = _event(baseline, "attack")

    resolved = act(state, SELO, target_id=state.fighters["enemy"].id)
    actor = resolved.fighters["player"]
    target = resolved.fighters["enemy"]
    event = _event(resolved)
    effect = next(effect for effect in target.effects if effect.id == SELO_EFFECT)

    assert event.damage == baseline_event.damage
    assert event.path_power_multiplier == D(1)
    assert event.effect_id == SELO_EFFECT
    assert event.applied_effect_stat == "defense"
    assert event.applied_effect_kind == "debuff"
    assert event.applied_effect_magnitude == D("0.10")
    assert event.applied_effect_duration == 2
    assert effect.removable and not effect.unremovable and not effect.fixed_mechanic
    assert effect.application_event == event.effect_application_event_id
    assert target.stats.defense == D("100")
    assert target.stat("defense") == D("90.00")
    assert actor.cooldowns[SELO] == opportunity + 3
    assert actor.action_use_counts[SELO] == 1
    assert actor.path_state["omen_offensive"][target.id]["remaining"] == 2
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert "oraculo.pressagio_defensive_criado" not in event.path_triggers

    replay = act(resolved, SELO, target_id=target.id)
    assert replay is resolved
    assert len([entry for entry in resolved.events if entry.action == SELO]) == 1


@pytest.mark.parametrize(
    ("path", "expected_power"),
    ((None, D("1.12")), ("agoureiro", D("1.16")), ("invocador", D("1.12"))),
)
def test_selo_consumes_target_offensive_omen_with_path_power_and_regenerates_after_debuff(
    path, expected_power
):
    state = _combat(path=path)
    _mark(state)
    target_id = state.fighters["enemy"].id

    resolved = act(state, SELO, target_id=target_id)
    actor = resolved.fighters["player"]
    event = _event(resolved)

    assert event.path_power_multiplier == expected_power
    assert "pressagio.ofensivo_consumido" in event.path_triggers
    assert event.effect_id == SELO_EFFECT
    assert event.applied_effect_magnitude == D("0.10")
    assert actor.path_state["omen_offensive"][target_id]["remaining"] == 2
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers
    assert event.class_resource_changes == (("omen_offensive", target_id, 1, 0),)
    line = event_line(resolved, event, viewer_key="player")
    assert "Presságio Ofensivo:" in line
    assert "instância(s) consumida(s)" in line
    assert "restam <code>0</code>" in line
    assert "Presságio Ofensivo gerado" in line and "2T" in line
    assert "Presságio Ofensivo gerado" not in event_line(
        resolved, event, viewer_key="enemy"
    )


def test_selo_uses_only_the_omen_associated_with_the_selected_target():
    state = _combat()
    second = replace(state.fighters["enemy"], id="second-enemy", name="Segundo Alvo")
    state.fighters["enemy-2"] = second
    _mark(state, "enemy-2")
    other_target_id = state.fighters["enemy-2"].id

    resolved = act(state, SELO, target_id=state.fighters["enemy"].id)
    event = _event(resolved)
    actor = resolved.fighters["player"]

    assert event.path_power_multiplier == D(1)
    assert "pressagio.ofensivo_consumido" not in event.path_triggers
    assert other_target_id in actor.path_state["omen_offensive"]
    assert resolved.fighters["enemy"].id in actor.path_state["omen_offensive"]


def test_selo_preserves_defensive_omen_and_coexists_with_other_defense_debuff_sources():
    state = _combat()
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    actor.path_state["omen_defensive"] = {
        actor.id: {"remaining": 1, "applied_opportunity": actor.opportunity}
    }
    other = Effect(
        "other.defense.down",
        "defense",
        D("0.05"),
        2,
        target.opportunity,
    )
    target.effects.append(other)

    resolved = act(state, SELO, target_id=target.id)
    actor_after = resolved.fighters["player"]
    target_after = resolved.fighters["enemy"]

    assert actor_after.path_state["omen_defensive"][actor.id]["remaining"] == 1
    assert {effect.id for effect in target_after.effects} == {
        "other.defense.down",
        SELO_EFFECT,
    }
    assert target_after.stat("defense") == D("85.5000")


def test_selo_resguardo_blocks_only_the_debuff_and_suppresses_offensive_omen():
    state = _combat()
    target = state.fighters["enemy"]
    target.ward_charges = 1
    target.ward_remaining = 2
    target.ward_applied_opportunity = target.opportunity
    _mark(state)

    resolved = act(state, SELO, target_id=target.id)
    actor_after = resolved.fighters["player"]
    target_after = resolved.fighters["enemy"]
    event = _event(resolved)

    assert event.damage > 0
    assert event.effective_damage > 0
    assert not any(effect.id == SELO_EFFECT for effect in target_after.effects)
    assert target_after.ward_charges == 0
    assert "omen_offensive" not in actor_after.path_state
    assert "oraculo.pressagio_offensive_criado" not in event.path_triggers
    assert any(entry.action == "resguardo:block" for entry in resolved.events)


def test_selo_consumes_omen_on_committed_miss_without_applying_or_regenerating():
    state = _combat()
    target = state.fighters["enemy"]
    target.stats = replace(target.stats, evasion=D("100"))
    _mark(state)

    resolved = act(state, SELO, target_id=target.id)
    actor_after = resolved.fighters["player"]
    event = _event(resolved)

    assert event.dodged
    assert "pressagio.ofensivo_consumido" in event.path_triggers
    assert "omen_offensive" not in actor_after.path_state
    assert not any(effect.id == SELO_EFFECT for effect in resolved.fighters["enemy"].effects)
    assert "oraculo.pressagio_offensive_criado" not in event.path_triggers


def test_selo_generates_omen_when_damage_is_fully_absorbed_but_debuff_applies():
    state = _combat()
    target = state.fighters["enemy"]
    _apply_barrier(
        target,
        applier_id="barrier-source",
        effect_definition_id="barrier.test",
        value=D("10000"),
        duration=2,
        applied_opportunity=target.opportunity,
        round_number=state.round,
    )

    resolved = act(state, SELO, target_id=target.id)
    actor_after = resolved.fighters["player"]
    target_after = resolved.fighters["enemy"]
    event = _event(resolved)

    assert event.damage > 0
    assert event.effective_damage == 0
    assert target_after.hp == target.hp
    assert any(effect.id == SELO_EFFECT for effect in target_after.effects)
    assert target_after.id in actor_after.path_state["omen_offensive"]
    assert "oraculo.pressagio_offensive_criado" in event.path_triggers


def test_selo_rejects_invalid_target_without_consuming_omen_or_starting_cooldown():
    state = _combat()
    _mark(state)
    actor = state.fighters["player"]
    target = state.fighters["enemy"]
    invalid = act(state, SELO, target_id="outside-the-encounter")

    assert invalid is state
    assert actor.path_state["omen_offensive"][target.id]["remaining"] == 2
    assert SELO not in actor.cooldowns
    assert not any(event.action == SELO for event in state.events)


def test_selo_sinal_persistente_talent_and_codec_preserve_the_new_omen():
    talent_id = "talent.oraculo.sinal_persistente"
    assert TALENT_DEFINITIONS[talent_id].level == 15
    state = _combat(talents=(talent_id,))
    resolved = act(state, SELO, target_id=state.fighters["enemy"].id)
    actor = resolved.fighters["player"]
    target_id = resolved.fighters["enemy"].id

    assert actor.path_state["omen_offensive"][target_id]["remaining"] == 3
    restored = decode(encode(resolved), resolved.id, resolved.ruleset, resolved.version)
    restored_actor = restored.fighters["player"]
    restored_effect = next(
        effect for effect in restored.fighters["enemy"].effects if effect.id == SELO_EFFECT
    )
    assert restored_actor.path_state["omen_offensive"][target_id] == actor.path_state[
        "omen_offensive"
    ][target_id]
    assert restored_effect.remaining == 2
    assert restored_actor.cooldowns[SELO] == actor.cooldowns[SELO]
    assert act(restored, SELO, target_id=target_id) is restored


def test_selo_talents_affect_only_their_declared_pressagio_trigger():
    cutting = _combat(
        talents=("talent.oraculo.pressagio_cortante",),
    )
    _mark(cutting)
    resolved = act(cutting, SELO, target_id=cutting.fighters["enemy"].id)
    event = _event(resolved)
    assert event.path_per_bonus == D(2)
    assert event.path_power_multiplier == D("1.12")

    reading = _combat(talents=("talent.oraculo.leitura_dos_sinais",))
    resolved_reading = act(reading, SELO, target_id=reading.fighters["enemy"].id)
    reading_effect = next(
        effect
        for effect in resolved_reading.fighters["player"].effects
        if effect.id == "class_mechanic.oraculo.leitura_dos_sinais.agility"
    )
    assert reading_effect.magnitude == D("0.05")
    assert reading_effect.remaining == 1
    assert "oraculo.leitura_dos_sinais" in _event(resolved_reading).path_triggers


def test_selo_detail_and_doctrine_show_class_level_and_no_weapon_gate():
    definition = active_art_definition(SELO)
    assert definition is not None
    view = DoctrineCollectionView(
        character_name="Oráculo",
        character_class="oraculo",
        selected_path="agoureiro",
        configuration_version=4,
        foreground=False,
        current_configuration={"path": "agoureiro", "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=34,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Selo",
        revision=1,
        configuration={
            "path": "agoureiro",
            "equipment": {},
            "arts": {"1": SELO},
            "talents": [],
        },
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    assert SELO in doctrine_art_ids(view, doctrine)

    # The detail renderer uses the same persisted character view as the catalog.
    from asterion.application.active_arts import ActiveArtCharacterView

    character_view = ActiveArtCharacterView(
        character_id=uuid4(),
        character_name="Oráculo",
        character_class="oraculo",
        level=34,
        selected_path="agoureiro",
        combat_configuration_version=4,
        slots=(),
        available_art_ids=(SELO, AUGURIO),
        foreground=False,
    )
    screen = render_art_detail(character_view, SELO)
    assert "Selo da Queda" in screen.text
    assert "Nv.34" in screen.text
    assert "100% ATQ" in screen.text
    assert "10% DEF" in screen.text
    assert "2T" in screen.text and "Recarga · 3 Rodadas" in screen.text
    assert "Requisito de arma · Nenhum" in screen.text
    assert "Presságio Ofensivo" in screen.text


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
                name=f"Selo{suffix}"[:16],
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
async def test_selo_database_level_gate_slots_persistence_and_revalidation(database):
    actor_id = 9_800_000 + uuid4().int % 100_000
    character_id, sessions = await _seed_oraculo(database, actor_id, level=33, path=None)
    service = ActiveArtService(sessions, "ocaso")

    level_33 = await service.view(actor_id)
    assert level_33 is not None and SELO not in level_33.available_art_ids
    with pytest.raises(ActiveArtMutationRejected) as rejected:
        await service.equip_art(actor_id, 1, SELO)
    assert rejected.value.code == ActiveArtMutationCode.LEVEL_REQUIRED

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 34
    eligible = await service.view(actor_id)
    assert eligible is not None and SELO in eligible.available_art_ids
    assert eligible.selected_path is None
    await service.equip_art(actor_id, 1, SELO)
    await service.equip_art(actor_id, 2, ORACULO_ART_IDS["sinal_funesto"])
    await service.equip_art(actor_id, 3, ORACULO_ART_IDS["vislumbre"])
    with pytest.raises(ActiveArtMutationRejected) as fourth_slot:
        await service.equip_art(actor_id, 4, SELO)
    assert fourth_slot.value.code == ActiveArtMutationCode.INVALID_SLOT

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        snapshot = await load_active_art_configuration(session, character)
    assert snapshot.art_ids == (
        SELO,
        ORACULO_ART_IDS["sinal_funesto"],
        ORACULO_ART_IDS["vislumbre"],
    )

    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        character.level = 33
    after_level_loss = await service.view(actor_id)
    assert after_level_loss is not None
    assert SELO not in after_level_loss.available_art_ids
    assert SELO in after_level_loss.ineligible_art_ids
