"""Chefes da Crônica I, Coro and the Group rule ``pr_cr01_encontro_grupo`` (§11.1, §11.4)."""

from __future__ import annotations

import copy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from asterion.application.chronicle import ChronicleAdmin
from asterion.application.chronicle_encounters import (
    ChronicleEncounterService,
    EncounterResultView,
)
from asterion.application.groups import ActivityProposalView, GroupService
from asterion.application.prologue import CombatView
from asterion.application.road import RoadService
from asterion.domain.campaign_combat import scale_campaign_boss_stats
from asterion.domain.chronicle import calendar_for
from asterion.domain.chronicle_content import OCASO
from asterion.domain.chronicle_encounters import (
    ADD_KEY,
    ENCOUNTERS_BY_OBJECTIVE,
    PHASE_I,
    PHASE_II,
    PHASE_III,
    configure_encounter,
    enemy_specs,
)
from asterion.domain.combat import _enemy_action, act
from asterion.domain.road import (
    CR01_AGUARDA_RESPOSTA,
    CR01_MESTRE_DE_TURNO,
    CR01_MULTIDAO_REPETIDA,
    CR01_REPETIDOR,
    ROAD_LOCATION,
    create_creature_party_combat,
    enemy_xp,
    road_enemy_stats,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Account,
    Achievement,
    CampaignSharedEncounter,
    CampaignSharedEncounterMember,
    Character,
    ChronicleCompletion,
    Quest,
    SocialGroup,
    SocialGroupMember,
    WorldState,
)

D = Decimal
SERVER = "ocaso"
DAY1 = date(2026, 12, 1)
CAL = calendar_for(DAY1)
BEFORE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
WEEK4 = CAL.chapter_opens_at(4) + timedelta(hours=1)
ANA, BEA, CAIO = 960001, 960002, 960003
ROAD = "Estrada das Cinzas"
REFUGE = "Refúgio do Ocaso"
MESTRE = ENCOUNTERS_BY_OBJECTIVE["cap_04_obj_04"]
AGUARDA = ENCOUNTERS_BY_OBJECTIVE["cap_08_obj_04"]


# ------------------------------------------------------------------ pure rules


def _combat(creature, level=30, roster=1):
    return create_creature_party_combat(
        uuid4(),
        "Ana",
        "sentinela",
        "remanescente",
        D(10**7),
        enemy_specs(creature, level, roster),
        player_level=level,
        configure_combat=configure_encounter,
    )


def _fight(combat, steps=300):
    """Plain attacks on the Chefe, the player kept alive; returns (phase, actor, action, opp)."""
    used = []
    for _ in range(steps):
        if combat.result:
            break
        player = combat.fighters["player"]
        player.hp = player.stats.hp
        before = len(combat.events)
        combat = act(combat, "attack", target_id="enemy")
        for event in combat.events[before:]:
            if event.actor in ("enemy", ADD_KEY):
                opportunity = combat.fighters["enemy"].opportunity
                used.append((combat.phase_id, event.actor, event.action, opportunity))
    return combat, used


def test_chefes_use_the_boss_profile_and_level_five():
    for creature in (CR01_MESTRE_DE_TURNO, CR01_AGUARDA_RESPOSTA):
        assert (creature.category, creature.unlock_level) == ("boss", 5)
    assert (CR01_MESTRE_DE_TURNO.archetype, CR01_AGUARDA_RESPOSTA.archetype) == (
        "brute",
        "balanced",
    )
    assert MESTRE.boss and AGUARDA.boss
    assert (MESTRE.feat_id, AGUARDA.feat_id) == (
        "feito_cr01_mestre_de_turno",
        "feito_cr01_aguarda_resposta",
    )


def test_mestre_calls_one_add_in_phase_two_and_ends_the_turn_in_phase_three():
    combat = _combat(CR01_MESTRE_DE_TURNO)
    add = combat.fighters[ADD_KEY]
    expected = road_enemy_stats(CR01_REPETIDOR, 30)
    assert add.hp == 0 and add.encounter_hidden and not add.required_for_victory
    assert add.stats.hp == expected.hp * D("0.50")
    assert add.stats.attack == expected.attack
    assert combat.phase_id == PHASE_I
    combat, used = _fight(combat)
    assert combat.result == "victory"
    by_action = {}
    for phase, actor, action, _ in used:
        by_action.setdefault(action.removeprefix("prepare:"), set()).add((phase, actor))
    assert by_action["e0_chamada"] == {(PHASE_II, "enemy")}
    assert [item for item in used if item[2] == "e0_chamada"].__len__() == 1
    assert {phase for phase, _ in by_action["e0_fim_de_turno"]} == {PHASE_III}
    assert all(actor == ADD_KEY for _, actor in by_action["e1_gesto_oficio"])
    assert "e0_ordem_coletiva" not in by_action  # Solo: no 2+ targets


def test_aguarda_waits_every_fourth_opportunity_of_phase_two_only():
    combat, used = _fight(_combat(CR01_AGUARDA_RESPOSTA))
    assert combat.result == "victory"
    entry = min(opp for phase, _, _, opp in used if phase == PHASE_II)
    waits = [opp for phase, _, action, opp in used if action == "espera"]
    assert waits and all(phase == PHASE_II for phase, _, a, _ in used if a == "espera")
    assert waits[0] == entry + 3  # the 4th opportunity counted from the entry
    assert all(b - a == 4 for a, b in zip(waits, waits[1:], strict=False))
    assert "insistencia" not in {action for _, _, action, _ in used}
    assert {p for p, _, a, _ in used if a == "prepare:confirmacao_exigida"} == {PHASE_III}
    espera = _combat(CR01_AGUARDA_RESPOSTA).enemy_actions["espera"]
    assert (espera.coefficient, espera.self_effect_stat, espera.self_effect_duration) == (
        0,
        "defense",
        1,
    )
    assert espera.self_effect_magnitude == D("0.12")
    selo = _combat(CR01_AGUARDA_RESPOSTA).enemy_actions["selo_pendente"]
    assert (selo.self_barrier_hp_fraction, selo.self_barrier_duration) == (D("0.08"), 2)
    assert (selo.max_uses_per_combat, selo.skip_if_barrier_active) == (2, True)


def test_only_chefes_scale_with_the_group():
    for roster in (2, 3, 4):
        boss = _combat(CR01_AGUARDA_RESPOSTA, 20, roster).fighters["enemy"].stats
        solo = road_enemy_stats(CR01_AGUARDA_RESPOSTA, 20)
        assert boss == scale_campaign_boss_stats(solo, roster)
        elite = _combat(CR01_MULTIDAO_REPETIDA, 20, roster).fighters["enemy"].stats
        assert elite == road_enemy_stats(CR01_MULTIDAO_REPETIDA, 20)
        add = _combat(CR01_MESTRE_DE_TURNO, 20, roster).fighters[ADD_KEY].stats
        assert add.hp == road_enemy_stats(CR01_REPETIDOR, 20).hp * D("0.50")
    assert scale_campaign_boss_stats(road_enemy_stats(CR01_MESTRE_DE_TURNO, 20), 1) == (
        road_enemy_stats(CR01_MESTRE_DE_TURNO, 20)
    )


def test_coro_needs_two_living_targets():
    combat = _combat(CR01_MULTIDAO_REPETIDA)
    combat.fighters["enemy"].cooldowns["a_palavra"] = 99
    assert _enemy_action(combat) != "coro"
    ally = copy.deepcopy(combat.fighters["player"])
    ally.id, ally.side = "ally", "player"
    combat.fighters["ally"] = ally
    assert _enemy_action(combat) == "coro"
    ally.hp = D(0)
    assert _enemy_action(combat) != "coro"


def test_new_engine_fields_survive_the_snapshot():
    combat = _combat(CR01_AGUARDA_RESPOSTA)
    combat.fighters["enemy"].hp = combat.fighters["enemy"].stats.hp * D("0.60")
    combat = act(combat, "attack", target_id="enemy")
    restored = decode(encode(combat), combat.id, combat.ruleset, combat.version)
    assert restored.enemy_actions["insistencia"].min_living_opponents == 2
    assert restored.phase_triggers[0].cooldown_action_ids == ("espera",)
    assert restored.phase_triggers[0].cooldown_opportunities == 4
    assert restored.fighters["enemy"].cooldowns == combat.fighters["enemy"].cooldowns


# ------------------------------------------------------------------ PostgreSQL


async def _make(database, actor, name, *, level=8, location=ROAD):
    async with database[1].begin() as session:
        await session.merge(Account(telegram_id=actor))
        character = Character(
            telegram_id=actor,
            server_id=SERVER,
            name=name,
            race="remanescente",
            character_class="sentinela",
            stage="menu",
            ruleset_version="tdo-1.0.15",
            level=level,
            hp=D("100"),
            max_hp=D("100"),
            created_at=BEFORE,
        )
        session.add(character)
        await session.flush()
        session.add(WorldState(character_id=character.id, region=OCASO, location=location))
        session.add(Quest(character_id=character.id, quest_id="P1", title="P1", status="completed"))
        return character.id


async def _group(database, *character_ids):
    async with database[1].begin() as session:
        group = SocialGroup(server_id=SERVER, leader_character_id=character_ids[0])
        session.add(group)
        await session.flush()
        for character_id in character_ids:
            session.add(SocialGroupMember(character_id=character_id, group_id=group.id))


def _service(database, groups=None):
    async def latest(_session, _character, region):
        return ROAD_LOCATION if region == OCASO else None

    road = RoadService(database[1], SERVER)
    return ChronicleEncounterService(
        database[1],
        SERVER,
        latest,
        road.recover_normal_pve_defeat,
        groups,
        clock=lambda: WEEK4,
    )


async def _schedule(database):
    await ChronicleAdmin(database[1], SERVER).set_day1(DAY1, "teste", now=BEFORE)


async def _shared_boss_hp(database, activity_id, hp):
    async with database[1].begin() as session:
        member = await session.scalar(
            select(CampaignSharedEncounterMember).where(
                CampaignSharedEncounterMember.game_activity_id == activity_id
            )
        )
        shared = await session.get(CampaignSharedEncounter, member.shared_encounter_id)
        combat = decode(
            shared.combat_snapshot, shared.id, shared.ruleset_version, shared.state_version
        )
        combat.fighters["enemy"].hp = D(hp)
        shared.combat_snapshot = encode(combat)


async def _feats(database, character_id):
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(Achievement.achievement_id).where(
                        Achievement.character_id == character_id
                    )
                )
            ).all()
        )


async def _done(database, character_id):
    async with database[1]() as session:
        return set(
            (
                await session.scalars(
                    select(ChronicleCompletion.objective_id).where(
                        ChronicleCompletion.character_id == character_id
                    )
                )
            ).all()
        )


async def test_solo_chefe_first_victory_pays_xp_objective_and_feat(database):
    ana = await _make(database, ANA, "Ana")
    await _schedule(database)
    service = _service(database)
    view = await service.start(ANA, 4, 4, now=WEEK4)
    assert isinstance(view, CombatView)
    assert set(view.combat.fighters) == {"player", "enemy", ADD_KEY}
    assert view.combat.fighters["enemy"].stats == road_enemy_stats(CR01_MESTRE_DE_TURNO, 8)
    async with database[1].begin() as session:
        from asterion.application.scripted_combat import current_combat
        from asterion.infrastructure.db.models import GameActivity

        activity = await session.get(GameActivity, view.activity_id)
        combat, _, record = await current_combat(session, activity)
        combat.fighters["enemy"].hp = D(1)
        record.snapshot = encode(combat)
    result = await service.intent(ANA, view.activity_id, view.combat.version, 0, "d0")
    assert isinstance(result, EncounterResultView) and result.victory
    assert result.xp == enemy_xp(8, "boss", player_level=8)
    assert (result.objective_completed, result.feat) == (True, "Fim de Turno")
    assert "feito_cr01_mestre_de_turno" in await _feats(database, ana)


async def test_group_chefe_scales_counts_eligible_and_ignores_helpers(database):
    ana = await _make(database, ANA, "Ana")
    bea = await _make(database, BEA, "Bea")
    caio = await _make(database, CAIO, "Caio", level=4)  # below Nv.5: Ajudante
    await _group(database, ana, bea, caio)
    await _schedule(database)
    groups = GroupService(database[1], SERVER)
    service = _service(database, groups)
    proposal = await service.propose_group(ANA, 4, 4, now=WEEK4)
    assert isinstance(proposal, ActivityProposalView)
    roles = {item.character_id: item.eligibility for item in proposal.participants}
    assert roles == {ana: "eligible", bea: "eligible", caio: "helper"}
    for actor in (BEA, CAIO):
        current = await groups.activity_proposal(actor, proposal.proposal_id)
        await groups.respond_activity(
            actor, proposal.proposal_id, expected_revision=current.revision, accept=True
        )
    current = await groups.activity_proposal(ANA, proposal.proposal_id)
    view = await service.start_group(
        ANA, proposal.proposal_id, expected_revision=current.revision
    )
    assert isinstance(view, CombatView) and view.campaign_shared
    boss = view.combat.fighters["enemy"].stats
    assert boss == scale_campaign_boss_stats(road_enemy_stats(CR01_MESTRE_DE_TURNO, 8), 3)
    await _shared_boss_hp(database, view.activity_id, 1)
    result = None
    for _ in range(12):
        for actor in (ANA, BEA, CAIO):
            current_view = await service.foreground(actor)
            if current_view is None:
                continue
            result = await service.action(
                actor,
                current_view.activity_id,
                current_view.combat.version,
                "attack",
                target_id="enemy",
                now=WEEK4,
            )
            if isinstance(result, EncounterResultView):
                break
        if isinstance(result, EncounterResultView):
            break
    assert isinstance(result, EncounterResultView) and result.victory
    for character_id in (ana, bea):
        assert "cap_04_obj_04" in await _done(database, character_id)
        assert "feito_cr01_mestre_de_turno" in await _feats(database, character_id)
    assert "cap_04_obj_04" not in await _done(database, caio)
    assert await _feats(database, caio) == set()
    for actor in (ANA, BEA, CAIO):
        assert await service.foreground(actor) is None


async def test_group_member_in_another_local_stays_out(database):
    ana = await _make(database, ANA, "Ana")
    bea = await _make(database, BEA, "Bea", location=REFUGE)
    await _group(database, ana, bea)
    await _schedule(database)
    service = _service(database, GroupService(database[1], SERVER))
    proposal = await service.propose_group(ANA, 4, 4, now=WEEK4)
    roles = {item.character_id: item.eligibility for item in proposal.participants}
    assert roles == {ana: "eligible", bea: "ineligible"}


async def test_without_a_group_the_button_fights_solo(database):
    await _make(database, ANA, "Ana")
    await _schedule(database)
    service = _service(database, GroupService(database[1], SERVER))
    view = await service.propose_group(ANA, 1, 4, now=WEEK4)
    assert isinstance(view, CombatView) and not view.campaign_shared
    listed = await service.encounters(ANA, now=WEEK4)
    assert not any(item.in_group for item in listed)
