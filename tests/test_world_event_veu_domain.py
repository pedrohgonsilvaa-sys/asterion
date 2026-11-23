"""Domínio de A Ruptura do Véu: estados, Núcleos, N global, scaling, AFK, determinismo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from asterion.domain import world_event_veu as ev
from asterion.domain.veu_bestiary import (
    CREATURES_BY_CODE,
    EVENT_REFERENCE_LEVEL,
    Category,
    UnresolvedArchetypeError,
    boss_in_final_form,
    creature_stats,
    stats_for,
)
from asterion.domain.world_events import phase_scale

D = Decimal
NOW = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)


def test_reference_level_and_global_constants():
    assert EVENT_REFERENCE_LEVEL == 30
    assert ev.DECISION_WINDOW == timedelta(seconds=10)
    assert ev.ENTRY_WINDOW == timedelta(minutes=15)
    assert ev.DEADLINE == timedelta(minutes=60)
    assert ev.REENTRY_DELAY == timedelta(minutes=2)
    assert ev.VIGOR_COST == 10


def test_decision_timer_is_an_event_override_not_a_global_one():
    from asterion.application.group_hunts import GROUP_HUNT_TURN_TIMEOUT_SECONDS
    from asterion.domain import arena, guild_battle

    assert GROUP_HUNT_TURN_TIMEOUT_SECONDS == 180
    assert arena.TURN_TTL == timedelta(seconds=90)
    assert guild_battle.TURN_TTL == timedelta(seconds=60)
    assert ev.decision_deadline(NOW) == NOW + timedelta(seconds=10)


def test_six_global_event_states_and_transitions():
    assert [state.name for state in ev.EventState] == [
        "AGENDADO", "ABERTO", "EM_ANDAMENTO", "CONCLUIDO", "FRACASSADO", "ENCERRADO",
    ]
    S = ev.EventState
    assert ev.transition_event(S.AGENDADO, S.ABERTO) is S.ABERTO
    assert ev.transition_event(S.ABERTO, S.EM_ANDAMENTO) is S.EM_ANDAMENTO
    for final in (S.CONCLUIDO, S.FRACASSADO, S.ENCERRADO):
        assert ev.transition_event(S.EM_ANDAMENTO, final) is final
    assert ev.transition_event(S.CONCLUIDO, S.ENCERRADO) is S.ENCERRADO
    assert ev.transition_event(S.FRACASSADO, S.ENCERRADO) is S.ENCERRADO


@pytest.mark.parametrize(
    "current,target",
    [
        ("AGENDADO", "EM_ANDAMENTO"),
        ("ABERTO", "CONCLUIDO"),
        ("CONCLUIDO", "FRACASSADO"),
        ("ENCERRADO", "ABERTO"),
        ("EM_ANDAMENTO", "ABERTO"),
    ],
)
def test_invalid_event_transitions_are_refused(current, target):
    with pytest.raises(ev.InvalidTransition):
        ev.transition_event(ev.EventState(current), ev.EventState(target))


def test_nucleus_states_follow_the_source_and_first_occurrence_never_collapses():
    S = ev.NucleusState
    assert {state.name for state in S} == {
        "ATIVA", "RESOLVENDO", "RESOLVIDA", "COLAPSADA", "SUBSTITUIDA",
    }
    assert not ev.nucleus_state_used_in_first_occurrence(S.COLAPSADA)
    for state in (S.ATIVA, S.RESOLVENDO, S.RESOLVIDA, S.SUBSTITUIDA):
        assert ev.nucleus_state_used_in_first_occurrence(state)


def test_nucleus_state_transitions_are_not_modeled_because_the_source_has_none():
    assert not hasattr(ev, "NUCLEUS_TRANSITIONS")
    assert not hasattr(ev, "transition_nucleus")
    assert "nucleus_state_transitions" in ev.BLOCKED_RULES


def test_only_active_nucleus_takes_players_and_rounds():
    S = ev.NucleusState
    assert ev.nucleus_accepts_players(S.ATIVA) and ev.nucleus_accepts_rounds(S.ATIVA)
    assert not ev.nucleus_accepts_rounds(S.RESOLVENDO)
    assert not ev.nucleus_accepts_players(S.RESOLVENDO)
    for state in (S.RESOLVIDA, S.COLAPSADA, S.SUBSTITUIDA):
        assert ev.nucleus_removes_participants(state)
    assert not ev.nucleus_removes_participants(S.ATIVA)


def test_round_resolves_once():
    R = ev.RoundState
    state, won = ev.begin_round_resolution(R.OPEN)
    assert (state, won) == (R.RESOLVING, True)
    assert ev.begin_round_resolution(state) == (R.RESOLVING, False)
    assert ev.begin_round_resolution(R.RESOLVED) == (R.RESOLVED, False)
    assert ev.transition_round(R.RESOLVING, R.RESOLVED) is R.RESOLVED
    with pytest.raises(ev.InvalidTransition):
        ev.transition_round(R.RESOLVED, R.OPEN)


def test_three_phases_with_three_nuclei_each():
    assert len(ev.NUCLEI) == 9
    assert [n.key for n in ev.NUCLEI] == list("ABCDEFGHI")
    for phase in (1, 2, 3):
        assert len(ev.nuclei_of_phase(phase)) == ev.NUCLEI_PER_PHASE
    assert [n.key for n in ev.nuclei_of_phase(3)] == ["G", "H", "I"]
    with pytest.raises(ValueError):
        ev.nuclei_of_phase(4)


def test_nucleus_names_and_creatures_follow_the_source():
    assert ev.NUCLEI_BY_KEY["A"].name == "O Primeiro Rasgo"
    assert ev.NUCLEI_BY_KEY["I"].creature_codes == ("VEU-18",)
    assert ev.NUCLEI_BY_KEY["D"].principal == "VEU-09"
    assert ev.NUCLEI_BY_KEY["D"].support == ("VEU-13",)
    assert ev.NUCLEI_BY_KEY["E"].principal == "VEU-10"
    assert ev.NUCLEI_BY_KEY["E"].support == ("VEU-11",)
    assert ev.NUCLEI_BY_KEY["F"].independent_targets is True
    assert not any(
        ev.NUCLEI_BY_KEY[key].independent_targets for key in "ABCDEGHI"
    )


def test_every_creature_belongs_to_exactly_one_nucleus():
    used = [code for n in ev.NUCLEI for code in n.creature_codes]
    assert sorted(used) == sorted(CREATURES_BY_CODE)


@pytest.mark.parametrize(
    "phase,resolved,expected",
    [
        (1, set(), False),
        (1, {"A"}, False),
        (1, {"A", "B"}, True),
        (1, {"B", "C"}, True),
        (1, {"A", "B", "C"}, True),
        (1, {"D", "E"}, False),  # Núcleos de outra fase não contam
        (2, {"D"}, False),
        (2, {"E", "F"}, True),
        (3, {"G", "H", "I"}, False),  # Fase III não avança
    ],
)
def test_phase_advances_with_two_of_three_nuclei(phase, resolved, expected):
    assert ev.phase_should_advance(phase, resolved) is expected


def test_victory_depends_only_on_the_final_nucleus():
    assert ev.event_completed({"I"})
    assert not ev.event_completed({"A", "B", "C", "D", "E", "F", "G", "H"})


def _records(count, **override):
    return [
        ev.ParticipantRecord(UUID(int=index + 1), **override) for index in range(count)
    ]


def test_global_n_ignores_exit_and_players_still_in_cooldown():
    records = [
        *_records(3),
        ev.ParticipantRecord(UUID(int=100), voluntary_exit=True),
        ev.ParticipantRecord(UUID(int=101), reentry_available_at=NOW + timedelta(seconds=1)),
        ev.ParticipantRecord(UUID(int=102), reentry_available_at=NOW),
    ]
    assert ev.valid_participant_count(records, NOW) == 4
    snapshot = ev.freeze_phase_snapshot(2, records, NOW)
    assert (snapshot.phase, snapshot.n) == (2, 4)


def test_afk_removal_from_a_nucleus_does_not_leave_the_event():
    afk = ev.afk_after_round(2, acted=False)
    assert afk.removed
    # O participante removido do Núcleo continua no Evento: segue contando no N.
    records = _records(3)
    assert ev.valid_participant_count(records, NOW) == 3


def test_global_n_is_capped_at_200_and_one_value_serves_every_nucleus():
    snapshot = ev.freeze_phase_snapshot(1, _records(250), NOW)
    assert snapshot.n == 200
    # um único snapshot por fase: a escala só depende dele
    assert phase_scale(snapshot.n) == phase_scale(200)


def test_snapshot_needs_aware_time_and_valid_phase():
    with pytest.raises(ValueError):
        ev.valid_participant_count([], datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        ev.freeze_phase_snapshot(0, [], NOW)


@pytest.mark.parametrize(
    "n,hp,attack",
    [(10, "7.59", "1.135"), (50, "31.27", "1.60"), (200, "105.90", "1.60")],
)
def test_qa_scaling_follows_the_formula_not_the_spec_examples(n, hp, attack):
    # §8.5 lista 30,90 (N=50) e 103,3 (N=200), mas N^0,88 dá 31,27 e 105,90.
    # A fórmula (§8.3 e GDD §49.15) é a regra; os exemplos da spec têm erro de conta.
    scale = phase_scale(n)
    assert scale.hp == D(n) ** D("0.88")
    assert abs(scale.hp - D(hp)) < D("0.01")
    assert scale.attack == D(attack)
    assert scale.defense == 1 and scale.agility == 1


def test_boss_profile_is_the_normal_boss_not_the_solo_dungeon_base():
    from asterion.domain.combat_math import StatMultipliers, enemy_stats
    from asterion.domain.road import ARCHETYPE

    stats = stats_for(Category.BOSS, "balanced", 1)
    normal = enemy_stats(
        30,
        StatMultipliers(D("2.20"), D("1.10"), D("1.10"), D("1.00")),
        ARCHETYPE["balanced"],
        phase_scale(1),
    )
    assert stats == normal
    solo = enemy_stats(
        30, StatMultipliers(D("3.00"), D("1.10"), D("1.10"), D("1.00")), phase_scale(1)
    )
    assert stats.hp < solo.hp


def test_creature_hp_follows_the_global_n_without_sintonization():
    mandibula = CREATURES_BY_CODE["VEU-01"]
    one = creature_stats(mandibula, 1)
    ten = creature_stats(mandibula, 10)
    assert ten.hp > one.hp * D("7.5")
    assert ten.attack == pytest.approx(one.attack * D("1.135"), rel=D("0.01"))
    assert ten.defense == one.defense


def test_archetypes_without_engine_profile_fail_loudly():
    for code in ("VEU-03", "VEU-09", "VEU-14", "VEU-15", "VEU-16", "VEU-18"):
        with pytest.raises(UnresolvedArchetypeError):
            creature_stats(CREATURES_BY_CODE[code], 10)


def test_boss_final_form_is_only_defined_at_or_below_35_percent():
    assert boss_in_final_form(D("0.35"))
    assert boss_in_final_form(D("0"))
    assert not boss_in_final_form(D("0.36"))
    # 70% não tem comportamento: a fonte não diz a que forma ele pertence.
    assert not hasattr(ev, "boss_form")
    assert "boss_form_70_boundary" in ev.BLOCKED_RULES
    with pytest.raises(ValueError):
        boss_in_final_form(D("1.01"))


def test_afk_counts_one_two_three_and_removes_at_the_third_round():
    first = ev.afk_after_round(0, acted=False)
    assert (first.streak, first.removed, first.label) == (1, False, "AFK 1/3")
    second = ev.afk_after_round(first.streak, acted=False)
    assert (second.streak, second.removed, second.label) == (2, False, "AFK 2/3")
    third = ev.afk_after_round(second.streak, acted=False)
    assert third.removed is True and third.streak == 3


def test_a_valid_action_resets_afk():
    state = ev.afk_after_round(2, acted=True)
    assert (state.streak, state.removed, state.label) == (0, False, None)
    with pytest.raises(ValueError):
        ev.afk_after_round(-1, acted=False)


def test_nucleus_switch_forbids_immediate_action_without_fixing_the_instant():
    assert ev.SWITCH_BLOCKED_ROUNDS == 1
    assert ev.SWITCH_ALLOWS_IMMEDIATE_ACTION is False
    assert not hasattr(ev, "blocked_through_round")
    assert not hasattr(ev, "can_act")
    assert "switch_blocked_round_instant" in ev.BLOCKED_RULES


def test_action_id_and_enemy_seed_are_deterministic():
    who = UUID(int=7)
    first = ev.action_id("20261124T1200", "A", 12, who)
    assert first == ev.action_id("20261124T1200", "A", 12, who)
    assert first != ev.action_id("20261124T1200", "A", 13, who)
    assert first != ev.action_id("20261124T1200", "B", 12, who)
    assert first != ev.action_id("20261124T2000", "A", 12, who)
    assert ev.enemy_seed("20261124T1200", "A", 12) == ev.enemy_seed("20261124T1200", "A", 12)
    assert ev.enemy_seed("20261124T1200", "A", 12) != ev.enemy_seed("20261124T1200", "A", 13)


def test_each_schedule_slot_is_independent_and_keys_are_stable():
    tuesday_noon = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)  # terça 12:00 em São Paulo
    tuesday_night = datetime(2026, 11, 24, 23, 0, tzinfo=UTC)  # terça 20:00
    wednesday = datetime(2026, 11, 25, 15, 0, tzinfo=UTC)
    assert ev.is_scheduled_slot(tuesday_noon) and ev.is_scheduled_slot(tuesday_night)
    assert not ev.is_scheduled_slot(wednesday)
    assert ev.occurrence_key(tuesday_noon) != ev.occurrence_key(tuesday_night)
    assert ev.occurrence_key(tuesday_noon) == ev.occurrence_key(tuesday_noon)
    assert ev.next_slot(tuesday_noon) == tuesday_night.astimezone(ev.EVENT_TIMEZONE)


def test_unresolved_rules_stay_blocked_and_documented():
    assert set(ev.BLOCKED_RULES) == {
        "contextual_actions",
        "nucleus_a_objective",
        "nucleus_b_structural_objective",
        "recent_contribution_priority",
        "barrier_duration",
        "remaining_nucleus_on_phase_change",
        "archetype_engine_profile",
        "nucleus_state_transitions",
        "boss_form_70_boundary",
        "switch_blocked_round_instant",
    }
    assert ev.EVENT_ID == "a_ruptura_do_veu"
    assert ev.CODEX_KEY == "codex.world_event.a_ruptura_do_veu"
