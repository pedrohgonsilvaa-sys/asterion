from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

from asterion.domain.arts import (
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    DEVASTADOR_ART_IDS,
    SABOTADOR_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Action, Combat, Fighter, _perform, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import PATH_ART_ACTIONS
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(
    character_class: str,
    path_id: str,
    art_ids: tuple[str, ...],
    *,
    include_ally: bool = False,
) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=22,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(1000),
        character_class=character_class,
        selected_path=path_id,
        takes_turn=True,
    )
    enemy = Fighter(
        id="enemy",
        name="Enemy",
        level=22,
        stats=CombatStats(D(1000), D(100), D(0), D(0), crit=D(0), evasion=D(0)),
        hp=D(1000),
        side="enemy",
        takes_turn=False,
    )
    fighters = {"player": player, "enemy": enemy}
    ai_target_cycle = ("player",)
    if include_ally:
        fighters["ally"] = Fighter(
            id="ally",
            name="Ally",
            level=22,
            stats=CombatStats(D(1000), D(0), D(0), D(0), evasion=D(0)),
            hp=D(1000),
            side="player",
            takes_turn=False,
        )
        ai_target_cycle = ("ally",)
    actions = class_player_actions(
        character_class,
        art_ids,
        selected_path=path_id,
    )
    return start_combat(
        Combat(
            UUID("a81c7af2-8340-4f6a-a4e3-c40d1d410012"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
            ai_target_cycle=ai_target_cycle,
        )
    )


def test_b2_lot_a_path_art_definitions_are_level_22_and_path_bound():
    expected = (
        (BASTIAO_ART_IDS["interpor"], "sentinela", "bastiao", False),
        (DEVASTADOR_ART_IDS["golpe_de_ruptura"], "sentinela", "devastador", True),
        (CARRASCO_ART_IDS["hemorragia"], "errante", "carrasco", True),
        (SABOTADOR_ART_IDS["fio_cortado"], "errante", "sabotador", True),
    )
    for art_id, character_class, path_id, weapon_required in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert definition.min_level == 22
        assert bool(definition.weapon_requirement) is weapon_required
        assert art_id in PATH_ART_ACTIONS


def test_interpor_protects_selected_ally_once_before_barrier_and_survives_codec():
    art_id = BASTIAO_ART_IDS["interpor"]
    combat = _battle(
        "sentinela",
        "bastiao",
        (art_id,),
        include_ally=True,
    )
    protected = act(combat, art_id, target_id="ally")
    effect = next(
        effect
        for effect in protected.fighters["ally"].effects
        if effect.stat == "interpor_next_direct"
    )
    assert effect.magnitude == D("0.25")
    assert effect.remaining == 2
    assert not any(
        candidate.stat == "interpor_next_direct"
        for candidate in protected.fighters["player"].effects
    )

    restored = decode(encode(protected), protected.id, protected.ruleset, protected.version)
    assert next(
        candidate
        for candidate in restored.fighters["ally"].effects
        if candidate.stat == "interpor_next_direct"
    ).remaining == 2
    restored.enemy_actions["incoming"] = Action("incoming", "Incoming", D(1))
    assert _perform(restored, "enemy", "incoming", target_id="ally")
    hit = restored
    event = next(event for event in hit.events if event.action == "incoming")
    assert event.calculated_damage == int(
        (D(direct_damage(D(100), D(1), D(0), 22)) * D("0.75")).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    assert "sentinela.interpor_consumido" in event.path_triggers
    assert not any(
        effect.stat == "interpor_next_direct" for effect in hit.fighters["ally"].effects
    )


def test_interpor_self_target_uses_one_reduction_and_never_reduces_dot_ticks():
    art_id = BASTIAO_ART_IDS["interpor"]
    combat = _battle("sentinela", "bastiao", (art_id,))
    protected = act(combat, art_id, target_id="player")
    assert any(
        effect.stat == "interpor_next_direct" for effect in protected.fighters["player"].effects
    )
    protected.enemy_actions["incoming"] = Action("incoming", "Incoming", D(1))
    assert _perform(protected, "enemy", "incoming", target_id="player")
    hit = protected
    event = next(event for event in hit.events if event.action == "incoming")
    assert event.calculated_damage == int(
        (
            D(direct_damage(D(100), D(1), D(100), 22)) * D("0.75")
        ).to_integral_value(rounding=ROUND_FLOOR)
    )
    assert not any(
        effect.stat == "interpor_next_direct" for effect in hit.fighters["player"].effects
    )


def test_golpe_de_ruptura_uses_retaliation_power_once_on_valid_commit():
    art_id = DEVASTADOR_ART_IDS["golpe_de_ruptura"]
    regular = _battle("sentinela", "devastador", (art_id,))
    regular_result = act(regular, art_id, target_id="enemy")
    regular_event = next(event for event in regular_result.events if event.action == art_id)
    assert regular_event.calculated_damage == direct_damage(
        D(100), D("1.25"), D(0), 22
    )

    empowered = _battle("sentinela", "devastador", (art_id,))
    empowered.fighters["player"].retaliation_charges = 1
    empowered.fighters["player"].retaliation_remaining = 1
    empowered.fighters["player"].retaliation_activation_id = "test:retaliation"
    empowered_result = act(empowered, art_id, target_id="enemy")
    event = next(event for event in empowered_result.events if event.action == art_id)
    assert event.path_power_multiplier == D("1.20")
    assert event.calculated_damage == direct_damage(D(100), D("1.50"), D(0), 22)
    assert event.retaliation_used
    assert empowered_result.fighters["player"].retaliation_charges == 0


def test_hemorragia_applies_two_canonical_bleed_stacks_once():
    art_id = CARRASCO_ART_IDS["hemorragia"]
    combat = _battle("errante", "carrasco", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    event = next(event for event in result.events if event.action == art_id)
    dots = result.dot_states["enemy"]
    assert event.dot_kind == "bleed"
    assert len(dots) == 1
    assert dots[0].kind == "bleed"
    assert dots[0].stacks == 2
    assert dots[0].remaining == 2
    assert len(dots[0].stack_snapshots) == 2


def test_fio_cortado_applies_sabotador_interference_to_atk_debuff_duration():
    art_id = SABOTADOR_ART_IDS["fio_cortado"]
    combat = _battle("errante", "sabotador", (art_id,))
    result = act(combat, art_id, target_id="enemy")
    event = next(event for event in result.events if event.action == art_id)
    effect = next(effect for effect in result.fighters["enemy"].effects if effect.id == art_id)
    assert event.effective_damage > 0
    assert effect.stat == "attack"
    assert effect.kind == "debuff"
    assert effect.magnitude == D("0.12")
    assert effect.remaining == 3
