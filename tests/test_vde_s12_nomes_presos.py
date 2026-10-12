import pytest
from sqlalchemy import select

from asterion.application.cosmetic_catalog import COSMETIC_BY_ACHIEVEMENT
from asterion.application.groups import GroupService
from asterion.application.knowledge_catalog import CODEX_BY_ID, CODEX_FRAGMENTS
from asterion.application.p7 import REGION
from asterion.application.vde_missions import (
    BAIXIOS,
    CLAUSTRO,
    GARGANTA,
    MATA,
    P11_ID,
    P12_ID,
    S10_ID,
    S12_ID,
    S12_REWARD_SOURCE,
    VIGILIA,
    VDEMissionService,
)
from asterion.bot.vde_missions_ui import _route_toward, render_vde_mission
from asterion.domain.combat import active_player_key
from asterion.domain.road import VDE_TANGLED_PILGRIM, road_enemy_stats
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    BestiaryEvidence,
    Character,
    CharacterCosmetic,
    CodexEntry,
    CodexFragment,
    Quest,
    RewardComponent,
    RewardEvent,
    WorldState,
)
from tests.test_p7_integration import _terminal
from tests.test_vde_p10_s10_claustro_integration import _seed_late_region

S12_FRAGMENT_IDS = {
    "codex.fragment.vales.nomes.registro_s10",
    "codex.fragment.vales.nomes.registro_final",
    "codex.fragment.vales.nomes.registro_vigilia",
}


async def _seed_s12(
    database,
    actor: int,
    *,
    level: int = 20,
    include_s10: bool = True,
    p12_completed: bool = False,
):
    character_id, sessions = await _seed_late_region(
        database, actor, level=level, p10=True
    )
    async with sessions.begin() as session:
        character = await session.get(Character, character_id)
        world = await session.get(WorldState, character_id)
        assert character is not None and world is not None
        character.level = level
        world.region = REGION
        world.location = CLAUSTRO
        session.add(
            Quest(
                character_id=character_id,
                quest_id=P11_ID,
                title="Onde Tudo se Enreda",
                status="completed",
                step=7,
                content_version="vales-1.0.4",
                progress={"completed": True, "berco_access_open": True},
            )
        )
        if include_s10:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=S10_ID,
                    title="Água sem Reflexo",
                    status="completed",
                    step=7,
                    content_version="vales-1.0.4",
                    progress={"completed": True, "second_explorer_status": "missing"},
                )
            )
        if p12_completed:
            session.add(
                Quest(
                    character_id=character_id,
                    quest_id=P12_ID,
                    title="A Matriarca das Raízes",
                    status="completed",
                    step=7,
                    content_version="vales-1.0.4",
                    progress={"completed": True, "reward_choice": "1"},
                )
            )
    return character_id, sessions


async def _move(sessions, character_ids, location: str) -> None:
    async with sessions.begin() as session:
        for character_id in character_ids:
            world = await session.get(WorldState, character_id)
            assert world is not None
            world.location = location


async def _advance(missions, actors, lead: int, action: str, location: str):
    character_ids = [await _character_id(missions.sessions, actor) for actor in actors]
    await _move(missions.sessions, character_ids, location)
    view = await missions.resume(lead, S12_ID)
    assert view is not None and view.status == "active"
    return await missions.advance(lead, S12_ID, view.state_version, action)


async def _character_id(sessions, actor: int):
    async with sessions() as session:
        character = await session.scalar(select(Character).where(Character.telegram_id == actor))
        assert character is not None
        return character.id


async def _join_group(groups, leader: int, actors: list[int], sessions) -> None:
    group = await groups.create_group(leader)
    for actor in actors[1:]:
        character_id = await _character_id(sessions, actor)
        async with sessions() as session:
            character = await session.get(Character, character_id)
            assert character is not None
            name = character.name
        invite = await groups.invite(
            leader, name, expected_group_revision=group.revision
        )
        group = await groups.respond_invite(
            actor, invite.invite_id, expected_revision=invite.revision, accept=True
        )


@pytest.mark.asyncio
async def test_s12_gate_requires_s10_p11_and_level_20_but_not_p12(database):
    actor = 998811
    _, sessions = await _seed_s12(database, actor, level=19)
    missions = VDEMissionService(sessions, "ocaso")

    blocked = await missions.resume(actor, S12_ID)
    assert blocked is not None and not blocked.available
    blocked = await missions.start(actor, S12_ID)
    assert blocked is not None and blocked.kind == "unavailable"

    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = 20
    available = await missions.resume(actor, S12_ID)
    assert available is not None and available.available
    started = await missions.start(actor, S12_ID)
    assert started is not None and started.status == "active" and started.step == 1

    async with sessions() as session:
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == started.character_id, Quest.quest_id == "P12"
            )
        ) is None

    actor += 1
    _, sessions = await _seed_s12(database, actor, level=20, include_s10=False)
    unavailable = await VDEMissionService(sessions, "ocaso").resume(actor, S12_ID)
    assert unavailable is not None and not unavailable.available

    actor += 1
    character_id, sessions = await _seed_s12(database, actor, level=20)
    async with sessions.begin() as session:
        p11 = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == P11_ID)
        )
        assert p11 is not None
        await session.delete(p11)
    unavailable = await VDEMissionService(sessions, "ocaso").resume(actor, S12_ID)
    assert unavailable is not None and not unavailable.available


@pytest.mark.asyncio
@pytest.mark.parametrize("p12_completed", [False, True])
async def test_s12_solo_flow_records_enemy_codex_reward_and_feat_once(
    database, monkeypatch, p12_completed
):
    import asterion.application.scripted_combat as scripted_combat

    actor = 998813 + int(p12_completed)
    character_id, sessions = await _seed_s12(
        database, actor, p12_completed=p12_completed
    )
    missions = VDEMissionService(sessions, "ocaso")
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))

    view = await missions.start(actor, S12_ID)
    assert view is not None and view.kind == "read_record"
    async with sessions() as session:
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.history.nomes_dos_vales",
            )
        ) is None
    view = await missions.advance(actor, S12_ID, view.state_version, "read_record")
    assert view is not None and view.kind == "visit_garganta"
    async with sessions() as session:
        assert await session.scalar(
            select(CodexEntry.entry_id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.history.nomes_dos_vales",
            )
        ) == "codex.history.nomes_dos_vales"
        assert await session.scalar(
            select(CodexFragment.fragment_id).where(
                CodexFragment.character_id == character_id,
                CodexFragment.fragment_id == "codex.fragment.vales.nomes.registro_s10",
            )
        ) == "codex.fragment.vales.nomes.registro_s10"
    buttons = render_vde_mission(view).keyboard.inline_keyboard
    assert any(
        button.callback_data == "road:route:vde_baixios"
        for row in buttons
        for button in row
    )
    view = await _advance(missions, [actor], actor, "visit_garganta", GARGANTA)
    assert view is not None and view.kind == "find_mark"
    view = await missions.advance(actor, S12_ID, view.state_version, "find_mark")
    assert view is not None and view.kind == "visit_mata"
    view = await _advance(missions, [actor], actor, "visit_mata", MATA)
    assert view is not None and view.kind == "recover_object"
    view = await missions.advance(actor, S12_ID, view.state_version, "recover_object")
    assert view is not None and view.kind == "visit_baixios"
    view = await _advance(missions, [actor], actor, "visit_baixios", BAIXIOS)
    assert view is not None and view.kind == "combat_start" and view.step == 7

    fight = await missions.start_solo_combat(actor, S12_ID, view.state_version)
    assert fight is not None and fight.combat is not None and fight.activity_id is not None
    enemy = fight.combat.fighters["enemy"]
    assert enemy.name == VDE_TANGLED_PILGRIM.name
    assert enemy.level == 20
    assert enemy.stats == road_enemy_stats(VDE_TANGLED_PILGRIM, 20)
    assert fight.combat.variant is None
    assert VDE_TANGLED_PILGRIM.creature_id == "peregrino_enredado"
    assert VDE_TANGLED_PILGRIM.category == "uncommon"
    assert VDE_TANGLED_PILGRIM.archetype == "balanced"
    assert (VDE_TANGLED_PILGRIM.unlock_level, VDE_TANGLED_PILGRIM.max_level) == (11, 15)
    assert tuple(action[0] for action in VDE_TANGLED_PILGRIM.actions) == (
        "golpe_enredado",
        "laco_improvisado",
    )
    assert VDE_TANGLED_PILGRIM.ai == ("golpe_enredado", "laco_improvisado", "defend")

    result = await missions.action_combat(
        actor, fight.activity_id, fight.combat.version, "attack"
    )
    assert result is not None and result.kind == "examine_site" and result.step == 8
    async with sessions() as session:
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S12_REWARD_SOURCE,
            )
        ) is None
        assert await session.scalar(
            select(BestiaryEntry.id).where(
                BestiaryEntry.character_id == character_id,
                BestiaryEntry.creature_id == VDE_TANGLED_PILGRIM.creature_id,
            )
        ) is not None
        evidence = set(
            (
                await session.scalars(
                    select(BestiaryEvidence.evidence_id).where(
                        BestiaryEvidence.character_id == character_id,
                        BestiaryEvidence.creature_id == VDE_TANGLED_PILGRIM.creature_id,
                    )
                )
            ).all()
        )
        assert "first_victory" in evidence
        assert not any("s12" in item.lower() for item in evidence)

    result = await missions.advance(actor, S12_ID, result.state_version, "examine_site")
    result = await _advance(missions, [actor], actor, "visit_claustro", CLAUSTRO)
    result = await missions.advance(actor, S12_ID, result.state_version, "last_record")
    result = await missions.advance(actor, S12_ID, result.state_version, "report_iven")
    assert result is not None and result.kind == "register_names" and result.step == 12
    result = await _advance(missions, [actor], actor, "register_names", VIGILIA)
    assert result is not None and result.status == "completed"

    async with sessions() as session:
        quest = await session.scalar(
            select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S12_ID)
        )
        assert quest is not None and quest.status == "completed"
        event = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character_id,
                RewardEvent.source_id == S12_REWARD_SOURCE,
            )
        )
        assert event is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(RewardComponent.reward_event_id == event.id)
                )
            ).all()
        )
        assert {(item.kind, item.item_id, item.quantity) for item in components} == {
            ("xp", None, 18100),
            ("crowns", None, 500),
            ("material", "material.vde.ferro_enredado", 2),
            ("material", "material.vde.couro_musgoso", 2),
            ("material", "material.vde.erva_de_turfa", 2),
            ("material", "material.vde.resina_enredada", 2),
        }
        fragments = set(
            (
                await session.scalars(
                    select(CodexFragment.fragment_id).where(
                        CodexFragment.character_id == character_id
                    )
                )
            ).all()
        )
        assert S12_FRAGMENT_IDS <= fragments
        assert await session.scalar(
            select(CodexEntry.entry_id).where(
                CodexEntry.character_id == character_id,
                CodexEntry.entry_id == "codex.history.nomes_dos_vales",
            )
        ) == "codex.history.nomes_dos_vales"
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character_id,
                Achievement.achievement_id == "feat.vde.nomes_presos_madeira",
            )
        ) is not None
        cosmetic = COSMETIC_BY_ACHIEVEMENT["feat.vde.nomes_presos_madeira"]
        assert cosmetic.cosmetic_id == "cosmetic.title.vde.nome_entalhado"
        assert await session.scalar(
            select(CharacterCosmetic.cosmetic_id).where(
                CharacterCosmetic.character_id == character_id,
                CharacterCosmetic.cosmetic_id == cosmetic.cosmetic_id,
            )
        ) == cosmetic.cosmetic_id

    stale = await missions.advance(actor, S12_ID, result.state_version - 1, "register_names")
    assert stale is not None and stale.status == "completed"
    async with sessions() as session:
        assert len(
            (
                await session.scalars(
                    select(RewardEvent.id).where(
                        RewardEvent.character_id == character_id,
                        RewardEvent.source_id == S12_REWARD_SOURCE,
                    )
                )
            ).all()
        ) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("group_size", [2, 3, 4])
async def test_s12_group_uses_one_level_20_peregrino_and_rewards_members_individually(
    database, monkeypatch, group_size
):
    import asterion.application.campaign_coop as campaign_coop

    leader = 998820 + group_size * 10
    actors = [leader + offset for offset in range(group_size)]
    character_ids = []
    sessions = None
    for actor in actors:
        character_id, sessions = await _seed_s12(database, actor)
        character_ids.append(character_id)
    assert sessions is not None
    groups = GroupService(sessions, "ocaso")
    await _join_group(groups, leader, actors, sessions)
    missions = VDEMissionService(sessions, "ocaso", groups)
    for actor in actors:
        started = await missions.start(actor, S12_ID)
        assert started is not None and started.status == "active"

    view = await missions.advance(
        leader, S12_ID, (await missions.resume(leader, S12_ID)).state_version, "read_record"
    )
    view = await _advance(missions, actors, leader, "visit_garganta", GARGANTA)
    view = await missions.advance(leader, S12_ID, view.state_version, "find_mark")
    view = await _advance(missions, actors, leader, "visit_mata", MATA)
    view = await missions.advance(leader, S12_ID, view.state_version, "recover_object")
    view = await _advance(missions, actors, leader, "visit_baixios", BAIXIOS)
    assert view is not None and view.step == 7

    proposal_view = await missions.propose_group_combat(leader, S12_ID, view.state_version)
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    for actor in actors[1:]:
        await groups.respond_activity(
            actor,
            proposal.proposal_id,
            expected_revision=proposal.revision,
            accept=True,
        )
        proposal = await groups.activity_proposal(leader, proposal.proposal_id)
    started = await missions.start_group_combat(
        leader, proposal.proposal_id, expected_revision=proposal.revision
    )
    assert started is not None and started.kind == "combat"
    assert started.group_size == group_size and started.combat is not None
    enemy = started.combat.fighters["enemy"]
    assert enemy.name == VDE_TANGLED_PILGRIM.name
    assert enemy.level == 20
    assert enemy.stats == road_enemy_stats(VDE_TANGLED_PILGRIM, 20)
    assert started.combat.variant is None
    player_fighters = [
        fighter for fighter in started.combat.fighters.values() if fighter.side == "player"
    ]
    assert len(player_fighters) == group_size
    enemy_fighters = [
        fighter for fighter in started.combat.fighters.values() if fighter.side == "enemy"
    ]
    assert len(enemy_fighters) == 1

    monkeypatch.setattr(campaign_coop, "act", _terminal("victory"))
    member_views = [await missions.resume(actor, S12_ID) for actor in actors]
    current_key = active_player_key(started.combat)
    turn_owner = next(
        actor
        for actor, member_view in zip(actors, member_views, strict=True)
        if member_view is not None and member_view.combat_actor_key == current_key
    )
    current_view = next(
        member_view
        for member_view in member_views
        if member_view is not None and member_view.combat_actor_key == current_key
    )
    victory = await missions.action_combat(
        turn_owner, current_view.activity_id, current_view.combat.version, "attack"
    )
    assert victory is not None
    for actor in actors:
        member_view = await missions.resume(actor, S12_ID)
        assert member_view is not None and member_view.step == 8
    lead_view = await missions.resume(leader, S12_ID)
    assert lead_view is not None
    view = await missions.advance(
        leader, S12_ID, lead_view.state_version, "examine_site"
    )
    view = await _advance(missions, actors, leader, "visit_claustro", CLAUSTRO)
    view = await missions.advance(leader, S12_ID, view.state_version, "last_record")
    view = await missions.advance(leader, S12_ID, view.state_version, "report_iven")
    view = await _advance(missions, actors, leader, "register_names", VIGILIA)
    assert view is not None and view.status == "completed"

    async with sessions() as session:
        for character_id in character_ids:
            quest = await session.scalar(
                select(Quest).where(Quest.character_id == character_id, Quest.quest_id == S12_ID)
            )
            assert quest is not None and quest.status == "completed"
            assert await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character_id,
                    RewardEvent.source_id == S12_REWARD_SOURCE,
                )
            ) is not None
            assert await session.scalar(
                select(BestiaryEntry.id).where(
                    BestiaryEntry.character_id == character_id,
                    BestiaryEntry.creature_id == VDE_TANGLED_PILGRIM.creature_id,
                )
            ) is not None


def test_s12_codex_entry_and_fragments_are_registered_and_route_buttons_follow_valid_paths():
    entry = CODEX_BY_ID["codex.history.nomes_dos_vales"]
    assert entry.title == "Nomes dos Vales" and entry.category == "history"
    assert S12_FRAGMENT_IDS <= CODEX_FRAGMENTS.keys()
    assert _route_toward(CLAUSTRO, GARGANTA) == "road:route:vde_baixios"
    assert _route_toward(BAIXIOS, VIGILIA) == "road:route:vde_mata"
    assert _route_toward(MATA, VIGILIA) == "road:route:vde_vigilia"
    assert _route_toward(CLAUSTRO, CLAUSTRO) is None
