from decimal import Decimal
from uuid import UUID

from asterion.domain.arts import (
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    DEVASTADOR_ART_IDS,
    SABOTADOR_ART_IDS,
    active_art_definition,
)
from asterion.domain.class_trials import class_player_actions
from asterion.domain.combat import Combat, Fighter, act, start_combat
from asterion.domain.combat_math import CURRENT_COMBAT_RULESET, CombatStats, direct_damage
from asterion.domain.path_arts import (
    CARRASCO_MARCA_DA_MORTE_CHAIN,
    PATH_ART_ACTIONS,
)
from asterion.infrastructure.db.combat_codec import decode, encode

D = Decimal


def _battle(
    character_class: str,
    path_id: str,
    art_ids: tuple[str, ...],
    *,
    enemy_ids: tuple[str, ...] = ("enemy",),
    talents: tuple[str, ...] = (),
) -> Combat:
    player = Fighter(
        id="player",
        name="Player",
        level=38,
        stats=CombatStats(D(1000), D(100), D(100), D(100), crit=D(0), evasion=D(0)),
        hp=D(1000),
        character_class=character_class,
        selected_path=path_id,
        talent_ids=talents,
        takes_turn=True,
    )
    fighters = {
        enemy_id: Fighter(
            id=enemy_id,
            name=f"Enemy {enemy_id}",
            level=38,
            stats=CombatStats(
                D(1000), D(100), D(0), D(0), crit=D(0), evasion=D(0)
            ),
            hp=D(1000),
            side="enemy",
            takes_turn=False,
        )
        for enemy_id in enemy_ids
    }
    fighters["player"] = player
    actions = class_player_actions(character_class, art_ids, selected_path=path_id)
    return start_combat(
        Combat(
            UUID("b38a1f12-83c4-42fa-ade3-6ba98ea72101"),
            CURRENT_COMBAT_RULESET,
            fighters,
            actions,
            {},
            (),
        )
    )


def _event(combat: Combat, action_id: str, target: str = "enemy"):
    return next(
        event
        for event in reversed(combat.events)
        if event.action == action_id and event.target == target
    )


def test_b3_a_definitions_are_publicly_catalogued_at_level_38_with_correct_paths():
    expected = (
        (BASTIAO_ART_IDS["contra_golpe"], "sentinela", "bastiao", True),
        (DEVASTADOR_ART_IDS["abalo"], "sentinela", "devastador", True),
        (CARRASCO_ART_IDS["marca_da_morte"], "errante", "carrasco", True),
        (SABOTADOR_ART_IDS["trava_de_passos"], "errante", "sabotador", True),
    )
    for art_id, character_class, path_id, has_melee in expected:
        definition = active_art_definition(art_id)
        assert definition is not None
        assert definition.min_level == 38
        assert definition.character_class == character_class
        assert definition.path_id == path_id
        assert bool(definition.weapon_requirement) is has_melee
        assert art_id in PATH_ART_ACTIONS


def test_contra_golpe_uses_retaliation_snapshot_and_consumes_once_on_commit():
    art_id = BASTIAO_ART_IDS["contra_golpe"]
    no_retaliation = _battle("sentinela", "bastiao", (art_id,))
    no_retaliation_result = act(no_retaliation, art_id, target_id="enemy")
    assert _event(no_retaliation_result, art_id).calculated_damage == direct_damage(
        D(100), D("1.20"), D(0), 38
    )
    assert not any(
        effect.id == art_id for effect in no_retaliation_result.fighters["enemy"].effects
    )

    empowered = _battle("sentinela", "bastiao", (art_id,))
    actor = empowered.fighters["player"]
    actor.retaliation_charges = 1
    actor.retaliation_remaining = 1
    actor.retaliation_activation_id = "test:retaliation"
    result = act(empowered, art_id, target_id="enemy")
    event = _event(result, art_id)
    effect = next(effect for effect in result.fighters["enemy"].effects if effect.id == art_id)
    assert event.calculated_damage == direct_damage(D(100), D("1.20"), D(0), 38)
    assert effect.stat == "attack" and effect.magnitude == D("0.10")
    assert effect.remaining == 2
    assert event.retaliation_used
    assert result.fighters["player"].retaliation_charges == 0


def test_abalo_resolves_each_target_and_consumes_retaliation_once_for_action():
    art_id = DEVASTADOR_ART_IDS["abalo"]
    combat = _battle("sentinela", "devastador", (art_id,), enemy_ids=("e1", "e2", "e3"))
    player = combat.fighters["player"]
    player.retaliation_charges = 1
    player.retaliation_remaining = 1
    player.retaliation_activation_id = "test:retaliation"
    result = act(combat, art_id)

    events = [event for event in result.events if event.action == art_id]
    assert {event.target for event in events} == {"e1", "e2", "e3"}
    expected_damage = direct_damage(D(100), D("0.90"), D(0), 38)
    assert all(event.calculated_damage == expected_damage for event in events)
    assert result.fighters["player"].retaliation_charges == 0
    for enemy_id in ("e1", "e2", "e3"):
        effect = next(
            effect for effect in result.fighters[enemy_id].effects if effect.id == art_id
        )
        assert effect.stat == "defense"
        assert effect.magnitude == D("0.08")
        assert effect.remaining == 2


def test_marca_da_morte_prepares_one_carrasco_art_without_strengthening_itself():
    marca = CARRASCO_ART_IDS["marca_da_morte"]
    corte = CARRASCO_ART_IDS["corte_de_execucao"]
    combat = _battle("errante", "carrasco", (marca, corte))
    prepared = act(combat, marca, target_id="enemy")
    mark_event = _event(prepared, marca)
    assert mark_event.calculated_damage == direct_damage(D(100), D("0.80"), D(0), 38)
    chain = prepared.fighters["player"].action_chains[CARRASCO_MARCA_DA_MORTE_CHAIN]
    assert chain["remaining"] == 2
    assert chain["prepared_by_action_id"] == marca

    restored = decode(encode(prepared), prepared.id, prepared.ruleset, prepared.version)
    empowered = act(restored, corte, target_id="enemy")
    event = _event(empowered, corte)
    assert event.chain_consumed and event.chain_empowered
    assert event.chain_window_before == 2
    assert event.damage_power_multiplier == D("1.12")
    assert event.calculated_damage == direct_damage(D(100), D("1.35") * D("1.12"), D(0), 38)
    assert CARRASCO_MARCA_DA_MORTE_CHAIN not in empowered.fighters["player"].action_chains


def test_marca_da_morte_does_not_consume_on_invalid_precommit_action():
    marca = CARRASCO_ART_IDS["marca_da_morte"]
    corte = CARRASCO_ART_IDS["corte_de_execucao"]
    combat = act(_battle("errante", "carrasco", (marca, corte)), marca, target_id="enemy")
    invalid = act(combat, corte, target_id="missing")
    assert invalid is combat
    assert CARRASCO_MARCA_DA_MORTE_CHAIN in combat.fighters["player"].action_chains


def test_trava_de_passos_uses_saboteur_duration_without_retroactive_opportunism():
    art_id = SABOTADOR_ART_IDS["trava_de_passos"]
    combat = _battle(
        "errante",
        "sabotador",
        (art_id,),
        talents=("talent.errante.oportunismo_ampliado",),
    )
    result = act(combat, art_id, target_id="enemy")
    event = _event(result, art_id)
    effect = next(effect for effect in result.fighters["enemy"].effects if effect.id == art_id)
    assert event.calculated_damage == direct_damage(D(100), D("0.80"), D(0), 38)
    assert effect.stat == "agility" and effect.magnitude == D("0.18")
    assert effect.remaining == 3
