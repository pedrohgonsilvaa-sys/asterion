from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

import asterion.domain.combat as combat_module
from asterion.domain.arts import TECELAO_ART_IDS
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import (
    _advance_barrier_sources,
    _apply_barrier,
    _deal_damage,
    _tick_path_resources,
    act,
    start_combat,
)
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, resolve_combat_stats
from asterion.domain.prologue import PROFILE
from asterion.domain.talents import (
    IMPLEMENTED_TALENT_LEVELS,
    TALENT_DEFINITIONS,
    TalentSelectionError,
    talent_points_at_level,
    validate_active_talent_ids,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal
ZERO = D(0)
TRAMA_AGRESSIVA = "talent.tecelao.trama_agressiva"
REFORCO_DO_VEU = "talent.tecelao.reforco_do_veu"
FIO_PERSISTENTE = "talent.tecelao.fio_persistente"
FIO_CORTANTE = TECELAO_ART_IDS["fio_cortante"]
CHAMA_TECIDA = TECELAO_ART_IDS["chama_tecida"]
SURTO_DO_VEU = TECELAO_ART_IDS["surto_do_veu"]
VEU_ENTRELACADO = TECELAO_ART_IDS["veu_entrelacado"]


def _combat(*, path=None, talent_ids=(), arts=(FIO_CORTANTE, CHAMA_TECIDA)):
    stats = resolve_combat_stats("tecelao", 35, "remanescente", selected_path=path)
    state = PROFILE.create(uuid4(), "Tecelão", "tecelao", "remanescente", stats.hp)
    state.tutorial = None
    state.ruleset = CURRENT_COMBAT_RULESET
    actor = state.fighters["player"]
    actor.level = 35
    actor.character_class = "tecelao"
    actor.selected_path = path
    actor.stats = replace(
        stats,
        hp=D(1000),
        attack=D(100),
        defense=D(100),
        agility=D(200),
        per=ZERO,
        crit=ZERO,
        evasion=ZERO,
        block=ZERO,
    )
    actor.hp = actor.stats.hp
    actor.talent_ids = tuple(talent_ids)
    enemy = state.fighters["enemy"]
    enemy.level = 35
    enemy.stats = CombatStats(D(5000), D(20), ZERO, D(100))
    enemy.hp = enemy.stats.hp
    enemy.takes_turn = False
    enemy.required_for_victory = False
    state.player_actions = class_player_actions("tecelao", arts, selected_path=path)
    state.configuration_snapshot = {
        "active_arts": tuple(
            {"slot": index, "art_id": art_id}
            for index, art_id in enumerate(arts, start=1)
        )
    }
    return start_combat(state)


def _event(state, action_id):
    return next(event for event in reversed(state.events) if event.action == action_id)


@pytest.mark.parametrize(
    ("path", "expected"),
    ((None, D("1.12")), ("conjurador", D("1.17")), ("runico", D("1.08"))),
)
def test_trama_agressiva_adds_two_points_to_the_consumed_damage_power(path, expected):
    state = _combat(path=path, talent_ids=(TRAMA_AGRESSIVA,))
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    assert generated.fighters["player"].path_state["trama_state"]["origin_art"] == FIO_CORTANTE

    consumed = act(generated, CHAMA_TECIDA, target_id="enemy")

    event = _event(consumed, CHAMA_TECIDA)
    assert event.path_power_multiplier == expected
    assert "trama_state" not in consumed.fighters["player"].path_state
    assert event.class_resource_changes == (("trama", "player", 1, 0),)


def test_trama_agressiva_does_not_trigger_on_origin_art_and_keeps_tier_closed():
    state = _combat(talent_ids=(TRAMA_AGRESSIVA,), arts=(FIO_CORTANTE,))
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    actor = generated.fighters["player"]
    original = actor.path_state["trama_state"].copy()

    repeated = act(generated, FIO_CORTANTE, target_id="enemy")

    assert repeated.fighters["player"].path_state["trama_state"] == original
    assert not any(
        change[0] == "trama"
        for change in _event(repeated, FIO_CORTANTE).class_resource_changes
    )
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert talent_points_at_level(35) == 7
    for talent_id in (TRAMA_AGRESSIVA, REFORCO_DO_VEU, FIO_PERSISTENTE):
        assert TALENT_DEFINITIONS[talent_id].level == 35
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("tecelao", 34, (talent_id,))
        for level in (35, 60):
            assert validate_active_talent_ids("tecelao", level, (talent_id,)) == (talent_id,)


def test_trama_agressiva_does_not_increase_barrier_power_when_trama_is_consumed_defensively():
    state = _combat(
        talent_ids=(TRAMA_AGRESSIVA,),
        arts=(FIO_CORTANTE, VEU_ENTRELACADO),
    )
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    consumed = act(generated, VEU_ENTRELACADO)

    event = _event(consumed, VEU_ENTRELACADO)
    assert event.barrier_power_multiplier == D("1.10")
    assert event.barrier_value == D(99)
    assert event.class_resource_changes == (("trama", "player", 1, 0),)


def test_reforco_do_veu_derives_defense_from_any_live_barrier_without_stacking():
    state = _combat(talent_ids=(REFORCO_DO_VEU,), arts=())
    owner = state.fighters["player"]
    base_defense = owner.stats.defense
    assert owner.barrier == ZERO
    assert owner.stat("defense") == base_defense

    _apply_barrier(
        owner,
        applier_id="luminar-ally",
        effect_definition_id="barrier.egide_solar",
        value=D(20),
        duration=3,
        applied_opportunity=owner.opportunity,
    )
    _apply_barrier(
        owner,
        applier_id="phase-source",
        effect_definition_id="barrier.phase",
        value=D(5),
        duration=2,
        applied_opportunity=owner.opportunity,
    )
    assert owner.barrier == D(25)
    assert owner.stat("defense") == base_defense * D("1.05")
    assert owner.stats.defense == base_defense

    _deal_damage(owner, D(20))
    assert owner.barrier == D(5)
    assert owner.stat("defense") == base_defense * D("1.05")

    _deal_damage(owner, D(5))
    assert owner.barrier == ZERO
    assert owner.stat("defense") == base_defense


def test_reforco_do_veu_supplies_dynamic_defense_to_the_shared_damage_pipeline(monkeypatch):
    state = _combat(talent_ids=(), arts=(FIO_CORTANTE,))
    target = state.fighters["enemy"]
    target.character_class = "tecelao"
    target.talent_ids = (REFORCO_DO_VEU,)
    target.stats = replace(target.stats, defense=D(100))
    _apply_barrier(
        target,
        applier_id="luminar-ally",
        effect_definition_id="barrier.light",
        value=D(10),
        duration=2,
        applied_opportunity=target.opportunity,
    )
    seen: list[Decimal] = []
    actual_direct_damage = combat_module.direct_damage

    def capture_defense(attack, coefficient, defense, attacker_level, **kwargs):
        seen.append(defense)
        return actual_direct_damage(
            attack, coefficient, defense, attacker_level, **kwargs
        )

    monkeypatch.setattr(combat_module, "direct_damage", capture_defense)
    act(state, FIO_CORTANTE, target_id="enemy")
    assert seen == [D(105)]

    target.character_class = "sentinela"
    assert target.stat("defense") == D(100)


def test_reforco_do_veu_expires_with_barrier_and_is_reconstructed_from_codec():
    state = _combat(talent_ids=(REFORCO_DO_VEU,), arts=())
    owner = state.fighters["player"]
    base_defense = owner.stats.defense
    _apply_barrier(
        owner,
        applier_id="consumable-source",
        effect_definition_id="barrier.consumable",
        value=D(1),
        duration=1,
        applied_opportunity=owner.opportunity,
    )

    restored = decode(encode(state), state.id, state.ruleset, state.version)
    restored_owner = restored.fighters["player"]
    assert restored_owner.stat("defense") == base_defense * D("1.05")
    assert restored_owner.stats.defense == base_defense

    restored_owner.opportunity += 1
    _advance_barrier_sources(restored_owner)
    assert restored_owner.barrier == ZERO
    assert restored_owner.stat("defense") == base_defense


def test_fio_persistente_renews_only_the_first_unused_trama_and_codec_keeps_window():
    state = _combat(talent_ids=(FIO_PERSISTENTE,), arts=())
    owner = state.fighters["player"]
    owner.opportunity = 2
    owner.path_state["trama_state"] = {
        "origin_art": FIO_CORTANTE,
        "remaining": 1,
        "applied_opportunity": 1,
    }

    _tick_path_resources(state, "player")

    renewed = owner.path_state["trama_state"]
    assert renewed == {
        "origin_art": FIO_CORTANTE,
        "remaining": 1,
        "applied_opportunity": 2,
    }
    assert owner.path_state["trama_expiry_renewed"] is True
    _tick_path_resources(state, "player")
    assert owner.path_state["trama_state"]["remaining"] == 1
    assert owner.path_state["trama_expiry_renewed"] is True
    restored = decode(encode(state), state.id, state.ruleset, state.version)
    restored_owner = restored.fighters["player"]
    assert restored_owner.path_state["trama_state"] == renewed
    assert restored_owner.path_state["trama_expiry_renewed"] is True

    restored_owner.opportunity = 3
    _tick_path_resources(restored, "player")
    assert "trama_state" not in restored_owner.path_state

    restored_owner.path_state["trama_state"] = {
        "origin_art": CHAMA_TECIDA,
        "remaining": 1,
        "applied_opportunity": 3,
    }
    restored_owner.opportunity = 4
    _tick_path_resources(restored, "player")
    assert "trama_state" not in restored_owner.path_state


def test_fio_persistente_does_not_restore_consumed_trama_and_duradoura_stays_three_turns():
    state = _combat(
        talent_ids=(FIO_PERSISTENTE, "talent.tecelao.trama_duradoura"),
        arts=(FIO_CORTANTE, SURTO_DO_VEU),
    )
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    trama = generated.fighters["player"].path_state["trama_state"]
    assert trama["remaining"] == 3
    consumed = act(generated, SURTO_DO_VEU, target_id="enemy")
    owner = consumed.fighters["player"]
    assert "trama_state" not in owner.path_state
    assert not owner.path_state.get("trama_expiry_renewed")
    _tick_path_resources(consumed, "player")
    assert "trama_state" not in owner.path_state
    assert not owner.path_state.get("trama_expiry_renewed")


def test_tier35_is_public_while_lower_weaver_tiers_remain_selectable():
    public_ids = (
        "talent.tecelao.fio_potente",
        "talent.tecelao.trama_duradoura",
        "talent.tecelao.fio_perfurante",
    )
    assert IMPLEMENTED_TALENT_LEVELS == frozenset({5, 15, 25, 35, 45})
    assert all(
        validate_active_talent_ids("tecelao", 25, (talent_id,)) == (talent_id,)
        for talent_id in public_ids
    )
    for talent_id in (TRAMA_AGRESSIVA, REFORCO_DO_VEU, FIO_PERSISTENTE):
        with pytest.raises(TalentSelectionError):
            validate_active_talent_ids("tecelao", 34, (talent_id,))
        assert validate_active_talent_ids("tecelao", 35, (talent_id,)) == (talent_id,)
        assert validate_active_talent_ids("tecelao", 60, (talent_id,)) == (talent_id,)


def test_all_three_tier35_talents_coexist_under_public_gate():
    state = _combat(
        talent_ids=(TRAMA_AGRESSIVA, REFORCO_DO_VEU, FIO_PERSISTENTE),
        arts=(FIO_CORTANTE, CHAMA_TECIDA),
    )
    generated = act(state, FIO_CORTANTE, target_id="enemy")
    consumed = act(generated, CHAMA_TECIDA, target_id="enemy")
    owner = consumed.fighters["player"]
    assert _event(consumed, CHAMA_TECIDA).path_power_multiplier == D("1.12")
    assert "trama_state" not in owner.path_state

    _apply_barrier(
        owner,
        applier_id="ally-source",
        effect_definition_id="barrier.ally",
        value=D(10),
        duration=2,
        applied_opportunity=owner.opportunity,
    )
    assert owner.stat("defense") == owner.stats.defense * D("1.05")

    owner.path_state["trama_state"] = {
        "origin_art": FIO_CORTANTE,
        "remaining": 1,
        "applied_opportunity": owner.opportunity - 1,
    }
    _tick_path_resources(consumed, "player")
    assert owner.path_state["trama_state"]["remaining"] == 1
    assert owner.path_state["trama_expiry_renewed"] is True
