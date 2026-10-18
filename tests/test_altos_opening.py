from collections import Counter
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.altos_missions import (
    P25_CODEX_ENTRY,
    P25_ID,
    P25_MISSION_ID,
    P25_REWARD_SOURCE,
    P25_TITLE,
    AltosMissionService,
    AltosMissionView,
)
from asterion.application.character_surfaces import (
    BestiaryRecordView,
    CodexEntryView,
    CodexFragmentView,
    KnowledgeView,
)
from asterion.application.groups import GroupService
from asterion.application.inventory import MATERIAL_LABELS as INVENTORY_MATERIAL_LABELS
from asterion.application.knowledge_catalog import (
    ALTOS_REGION_ID,
    CODEX_BY_ID,
    CODEX_FRAGMENTS,
    CREATURE_PRESENTATION,
)
from asterion.application.knowledge_catalog import MATERIAL_LABELS as BESTIARY_MATERIAL_LABELS
from asterion.application.road import (
    ALTOS_ABRIGO_LABEL,
    ALTOS_ESCARPA_LABEL,
    ALTOS_LOCATIONS,
    ALTOS_PEDREIRAS_LABEL,
    ALTOS_PONTES_LABEL,
    VARZEAS_CAMARA_LABEL,
)
from asterion.application.round import RoundService
from asterion.bot.altos_missions_ui import render_altos_mission
from asterion.bot.character_surfaces_ui import (
    render_bestiary_root,
    render_codex_category,
    render_codex_detail,
    render_codex_region,
)
from asterion.domain.combat import active_player_key
from asterion.domain.professions import MATERIAL_NAMES
from asterion.domain.road import (
    ALTOS_ABRIGO_ACCESS_UNLOCK,
    ALTOS_ABRIGO_BRAZIER,
    ALTOS_ABRIGO_LOCATION,
    ALTOS_ESCARPA_ACCESS_UNLOCK,
    ALTOS_ESCARPA_BRAZIER,
    ALTOS_ESCARPA_EXPLORE_UNLOCK,
    ALTOS_ESCARPA_HUNT_UNLOCK,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_ESCARPA_PROFILE,
    ALTOS_ESCARPA_ROUND_UNLOCK,
    ALTOS_PEDREIRAS_ACCESS_UNLOCK,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_QUEBRA_ESCARPAS,
    ALTOS_REGION,
    VARIANT_POOL,
    VARZEAS_CAMARA_ACCESS_UNLOCK,
    VARZEAS_REGION,
    VARZEAS_REGION_ENTRY_UNLOCK,
)
from asterion.infrastructure.db.combat_codec import decode, encode
from asterion.infrastructure.db.models import (
    Achievement,
    BestiaryEntry,
    Brazier,
    CampaignSharedEncounter,
    Character,
    CodexEntry,
    CodexFragment,
    LocationDiscovery,
    MaterialStack,
    Quest,
    RewardComponent,
    RewardEvent,
    Unlock,
    WorldState,
)
from tests.helpers.pvpve import disable_round_pvpve_for_test, start_manual_hunt_after_no_match
from tests.test_road_integration import _seed_road
from tests.test_s4_s5_integration import _terminal


def test_altos_location_catalog_stops_at_p27():
    assert ALTOS_REGION == "Altos Cinéreos"
    assert ALTOS_LOCATIONS == {
        ALTOS_ESCARPA_LABEL,
        ALTOS_ABRIGO_LABEL,
        ALTOS_PONTES_LABEL,
        ALTOS_PEDREIRAS_LABEL,
    }
    assert ALTOS_ESCARPA_LOCATION == "location.altos.escarpa_cinza"
    assert ALTOS_ABRIGO_LOCATION == "location.altos.abrigo_peso"
    assert ALTOS_ESCARPA_ACCESS_UNLOCK == "unlock.location.altos.escarpa_cinza"
    assert ALTOS_ABRIGO_ACCESS_UNLOCK == "unlock.location.altos.abrigo_peso"
    assert ALTOS_ESCARPA_BRAZIER == "bonfire.altos.escarpa"
    assert ALTOS_ABRIGO_BRAZIER == "bonfire.altos.abrigo"
    assert ALTOS_ESCARPA_HUNT_UNLOCK == "unlock.hunt.altos.escarpa"
    assert ALTOS_ESCARPA_EXPLORE_UNLOCK == "unlock.explore.altos.escarpa"
    assert ALTOS_ESCARPA_ROUND_UNLOCK == "unlock.round.altos.escarpa"
    assert ALTOS_PEDREIRAS_LOCATION == "location.altos.pedreiras_suspensas"
    assert ALTOS_PEDREIRAS_ACCESS_UNLOCK == "unlock.location.altos.pedreiras_suspensas"
    assert P25_ID == "P25"
    assert P25_MISSION_ID == "mission.altos.p25"
    assert P25_TITLE == "O Peso Antigo"
    assert P25_CODEX_ENTRY == "codex.altos.infraestrutura_sustentacao"
    assert CODEX_BY_ID["codex.altos.regiao"].title == "Altos Cinéreos"
    assert CODEX_BY_ID[P25_CODEX_ENTRY].title == "Infraestrutura de Sustentação"
    assert CODEX_FRAGMENTS[P25_CODEX_ENTRY].title == "Carga Observável"
    assert (
        CODEX_FRAGMENTS["explore.altos.escarpa.caderno_resgate_rasgado"].title
        == "Caderno de Resgate Rasgado"
    )
    for creature_id, _weight in ALTOS_ESCARPA_PROFILE.creature_weights:
        presentation = CREATURE_PRESENTATION[creature_id]
        assert presentation.region_id == ALTOS_REGION_ID
        assert presentation.habitats == (ALTOS_ESCARPA_LOCATION,)
    for material_id, label in {
        "material.altos.ferro_contrapeso": "Ferro de Contrapeso",
        "material.altos.couro_escarpa": "Couro de Escarpa",
        "material.altos.liquen_pedreira": "Líquen de Pedreira",
        "material.altos.cinza_basalto": "Cinza de Basalto",
    }.items():
        assert MATERIAL_NAMES[material_id] == label
        assert INVENTORY_MATERIAL_LABELS[material_id] == label
        assert BESTIARY_MATERIAL_LABELS[material_id] == label
    assert ALTOS_PONTES_LABEL == "Pontes de Fuligem"
    assert ALTOS_PEDREIRAS_LABEL == "Pedreiras Suspensas"
    assert "Bastilha de Carga" not in ALTOS_LOCATIONS
    assert "Coração do Colosso" not in ALTOS_LOCATIONS


def test_altos_escarpa_hunt_profile_matches_the_final_opening_pool():
    assert ALTOS_ESCARPA_PROFILE.creature_weights == (
        ("creature.altos.lobo_escarpa", 31),
        ("creature.altos.abutre_fuligem", 29),
        ("creature.altos.escaravelho_basalto", 20),
        ("creature.altos.carneiro_peso", 17),
        (ALTOS_QUEBRA_ESCARPAS, 3),
    )
    assert sum(weight for _, weight in ALTOS_ESCARPA_PROFILE.creature_weights) == 100
    assert ALTOS_ESCARPA_PROFILE.variant_chance == 11
    assert VARIANT_POOL[ALTOS_QUEBRA_ESCARPAS] == ()
    assert ALTOS_ESCARPA_PROFILE.hunt_unlock == ALTOS_ESCARPA_HUNT_UNLOCK
    assert ALTOS_ESCARPA_PROFILE.explore_unlock == ALTOS_ESCARPA_EXPLORE_UNLOCK
    assert ALTOS_ESCARPA_PROFILE.round_familiarity == ALTOS_ESCARPA_ROUND_UNLOCK


def test_altos_p25_ui_exposes_only_the_current_step_action():
    view = AltosMissionView(
        character_id=uuid4(),
        quest_id=P25_ID,
        title=P25_TITLE,
        kind="mission",
        status="active",
        step=6,
        state_version=5,
        progress={},
        location=ALTOS_ESCARPA_LABEL,
        level=41,
    )

    screen = render_altos_mission(view)
    callbacks = {
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    }
    assert "road:route:altos_abrigo" in callbacks
    assert all("pontes" not in callback for callback in callbacks)
    assert all("pedreiras" not in callback for callback in callbacks)
    assert "Abrigo do Peso" in screen.text


def test_altos_codex_and_bestiary_surfaces_include_the_current_location():
    region_entry = CodexEntryView(
        "codex.altos.regiao",
        "Altos Cinéreos",
        "regions",
        140,
        ALTOS_ESCARPA_LOCATION,
        (),
    )
    codex_fragment = CodexFragmentView(
        P25_CODEX_ENTRY,
        CODEX_FRAGMENTS[P25_CODEX_ENTRY].title,
        CODEX_FRAGMENTS[P25_CODEX_ENTRY].text,
    )
    infrastructure_entry = CodexEntryView(
        P25_CODEX_ENTRY,
        "Infraestrutura de Sustentação",
        "regions",
        150,
        ALTOS_ESCARPA_LOCATION,
        (codex_fragment,),
    )
    bestiary_record = BestiaryRecordView(
        creature_id="creature.altos.lobo_escarpa",
        name="Lobo de Escarpa",
        stage="observed",
        stage_label="Observado",
        habitats=(ALTOS_ESCARPA_LOCATION,),
        variants=(),
        materials=("Couro de Escarpa",),
        observed_actions=(),
    )
    view = KnowledgeView(
        character_class="sentinela",
        codex_entries=(region_entry, infrastructure_entry),
        bestiary=(bestiary_record,),
        achievements=(),
        known_locations=frozenset((ALTOS_ESCARPA_LOCATION,)),
    )

    regions = render_codex_category(view, "regions")
    assert "Altos Cinéreos" in regions.text
    assert any(
        button.callback_data == "kb:r:altos"
        for row in regions.keyboard.inline_keyboard
        for button in row
    )
    region = render_codex_region(view, "altos")
    assert "Altos Cinéreos" in region.text
    assert "Infraestrutura de Sustentação" in region.text
    detail = render_codex_detail(view, infrastructure_entry)
    assert "Carga Observável" in detail.text
    assert any(
        button.callback_data == "kb:r:altos"
        for row in detail.keyboard.inline_keyboard
        for button in row
    )
    bestiary = render_bestiary_root(view)
    assert "Altos Cinéreos" in bestiary.text
    assert any(
        button.callback_data == "kb:br:altos"
        for row in bestiary.keyboard.inline_keyboard
        for button in row
    )


async def _seed_altos_exit(database, actor: int, *, level: int, p24_status: str):
    actor, road = await _seed_road(database, actor=actor)
    _, sessions = database
    async with sessions.begin() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        character.level = level
        world = await session.get(WorldState, character.id)
        assert world is not None
        world.region = VARZEAS_REGION
        world.location = VARZEAS_CAMARA_LABEL
        session.add(
            Quest(
                character_id=character.id,
                quest_id="P24",
                title="A Câmara da Matriz",
                status=p24_status,
                step=1,
                content_version="varzeas-1.0.3",
                progress={"completed": p24_status == "completed"},
            )
        )
        session.add_all(
            (
                Unlock(character_id=character.id, unlock_id=VARZEAS_REGION_ENTRY_UNLOCK),
                Unlock(character_id=character.id, unlock_id=VARZEAS_CAMARA_ACCESS_UNLOCK),
            )
        )
    return actor, road, sessions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("level", "p24_status"),
    ((40, "completed"), (41, "active")),
)
async def test_altos_entry_requires_level_41_and_completed_p24(
    database, level, p24_status
):
    actor, road, _sessions = await _seed_altos_exit(
        database, 779000 + level, level=level, p24_status=p24_status
    )

    assert await road.travel_route(actor, ALTOS_ESCARPA_LABEL) is None
    async with database[1]() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Quest.id).where(
                Quest.character_id == character.id, Quest.quest_id == P25_ID
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == ALTOS_ESCARPA_LOCATION,
            )
        ) is None


@pytest.mark.asyncio
async def test_p25_opening_persistence_rewards_and_escarpa_round_gate(database, monkeypatch):
    import asterion.application.road as road_module
    import asterion.application.scripted_combat as scripted_combat

    actor, road, sessions = await _seed_altos_exit(
        database, 779041, level=41, p24_status="completed"
    )
    entry = await road.travel_route(actor, ALTOS_ESCARPA_LABEL)
    assert entry is not None and entry.location == ALTOS_ESCARPA_LABEL

    mission = AltosMissionService(sessions, "ocaso")
    view = await mission.resume_active(actor)
    assert view is not None and view.status == "active" and view.step == 2
    assert await mission.available(actor)
    assert await mission.known_locations(actor) == {ALTOS_ESCARPA_LABEL}

    first_version = view.state_version
    view = await mission.advance(actor, first_version, "inspect_contraforte")
    assert view is not None and view.progress["support_points"] == ["inspect_contraforte"]
    duplicate = await mission.advance(actor, first_version, "inspect_contraforte")
    assert duplicate is not None and duplicate.state_version == view.state_version
    view = await mission.advance(actor, view.state_version, "inspect_cabo")
    assert view is not None and view.step == 2
    view = await mission.advance(actor, view.state_version, "inspect_escora")
    assert view is not None and view.step == 3

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        xp_before_combat = character.xp
        crowns_before_combat = character.crowns

    scripted = await mission.start_solo_combat(actor, view.state_version)
    assert scripted is not None and scripted.kind == "combat" and scripted.combat is not None
    assert scripted.combat.fighters["enemy"].level == 41
    assert scripted.combat.variant is None
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        observed = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == "creature.altos.lobo_escarpa",
            )
        )
        assert observed is not None and observed.wins == 0
    monkeypatch.setattr(scripted_combat, "act", _terminal("victory"))
    victory = await mission.action(
        actor, scripted.activity_id, scripted.combat.version, "attack"
    )
    assert victory is not None and victory.step == 4 and victory.kind == "mission"
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert character.xp == xp_before_combat
        assert character.crowns == crowns_before_combat
        lobo = await session.scalar(
            select(BestiaryEntry).where(
                BestiaryEntry.character_id == character.id,
                BestiaryEntry.creature_id == "creature.altos.lobo_escarpa",
            )
        )
        assert lobo is not None and lobo.wins == 1
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P25_REWARD_SOURCE,
            )
        ) is None

    view = await mission.advance(actor, victory.state_version, "register_escarpa_brazier")
    assert view is not None and view.step == 5
    view = await mission.advance(actor, view.state_version, "confirm_redundant_repairs")
    assert view is not None and view.step == 6
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_ABRIGO_ACCESS_UNLOCK,
            )
        ) is None
        assert await session.scalar(
            select(LocationDiscovery.id).where(
                LocationDiscovery.character_id == character.id,
                LocationDiscovery.location_id == ALTOS_ABRIGO_LOCATION,
            )
        ) is None
    assert await road.travel_route(actor, ALTOS_ABRIGO_LABEL) is not None
    view = await mission.resume_active(actor)
    assert view is not None and view.step == 7 and view.location == ALTOS_ABRIGO_LABEL
    assert await mission.known_locations(actor) == {ALTOS_ESCARPA_LABEL, ALTOS_ABRIGO_LABEL}

    view = await mission.advance(actor, view.state_version, "register_abrigo_brazier")
    assert view is not None and view.step == 8
    view = await mission.advance(actor, view.state_version, "speak_rava")
    assert view is not None and view.step == 8
    view = await mission.advance(actor, view.state_version, "speak_doren")
    assert view is not None and view.step == 9
    view = await mission.advance(actor, view.state_version, "record_codex")
    assert view is not None and view.progress["codex_recorded"]
    completed = await mission.advance(actor, view.state_version, "conclude_with_rava")
    assert completed is not None and completed.status == "completed"
    duplicate_completion = await mission.advance(
        actor, completed.state_version, "conclude_with_rava"
    )
    assert duplicate_completion is not None and duplicate_completion.status == "completed"

    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        reward = await session.scalar(
            select(RewardEvent).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P25_REWARD_SOURCE,
            )
        )
        assert reward is not None
        components = list(
            (
                await session.scalars(
                    select(RewardComponent).where(
                        RewardComponent.reward_event_id == reward.id
                    )
                )
            ).all()
        )
        assert Counter((row.kind, row.item_id, row.quantity) for row in components) == Counter(
            {
                ("xp", None, 53_500): 1,
                ("crowns", None, 720): 1,
                ("material", "material.altos.ferro_contrapeso", 1): 1,
                ("material", "material.altos.liquen_pedreira", 1): 1,
            }
        )
        assert await session.scalar(
            select(RewardEvent.id).where(
                RewardEvent.character_id == character.id,
                RewardEvent.source_id == P25_REWARD_SOURCE,
            )
        ) == reward.id
        assert await session.scalar(
            select(CodexEntry.id).where(
                CodexEntry.character_id == character.id,
                CodexEntry.entry_id == P25_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(CodexFragment.id).where(
                CodexFragment.character_id == character.id,
                CodexFragment.entry_id == P25_CODEX_ENTRY,
                CodexFragment.fragment_id == P25_CODEX_ENTRY,
            )
        ) is not None
        assert await session.scalar(
            select(Achievement.id).where(
                Achievement.character_id == character.id,
                Achievement.achievement_id == "achievement.altos.peso_antigo",
            )
        ) is not None
        unlocks = set(
            (
                await session.scalars(
                    select(Unlock.unlock_id).where(
                        Unlock.character_id == character.id,
                        Unlock.unlock_id.like("%altos%"),
                    )
                )
            ).all()
        )
        assert ALTOS_ESCARPA_HUNT_UNLOCK in unlocks
        assert ALTOS_ESCARPA_EXPLORE_UNLOCK in unlocks
        assert ALTOS_ESCARPA_ROUND_UNLOCK not in unlocks
        assert not any(
            unlock_id
            in {
                "unlock.location.altos.pontes_fuligem",
                "unlock.location.altos.pedreiras_suspensas",
                "unlock.location.altos.bastilha_carga",
                "unlock.location.altos.coracao_colosso",
                "unlock.hunt.altos.pontes",
                "unlock.hunt.altos.pedreiras",
                "unlock.hunt.altos.bastilha",
                "unlock.explore.altos.pontes",
                "unlock.explore.altos.pedreiras",
                "unlock.explore.altos.bastilha",
                "unlock.round.altos.pontes",
                "unlock.round.altos.pedreiras",
                "unlock.round.altos.bastilha",
            }
            for unlock_id in unlocks
        )
        discoveries = set(
            (
                await session.scalars(
                    select(LocationDiscovery.location_id).where(
                        LocationDiscovery.character_id == character.id,
                        LocationDiscovery.location_id.like("location.altos.%"),
                    )
                )
            ).all()
        )
        assert discoveries == {ALTOS_ESCARPA_LOCATION, ALTOS_ABRIGO_LOCATION}
        brazier_ids = set(
            (
                await session.scalars(
                    select(Brazier.brazier_id).where(Brazier.character_id == character.id)
                )
            ).all()
        )
        assert {ALTOS_ESCARPA_BRAZIER, ALTOS_ABRIGO_BRAZIER} <= brazier_ids
        material_stacks = list(
            (
                await session.scalars(
                    select(MaterialStack).where(
                        MaterialStack.character_id == character.id,
                        MaterialStack.material_id.in_(
                            (
                                "material.altos.ferro_contrapeso",
                                "material.altos.liquen_pedreira",
                            )
                        ),
                    )
                )
            ).all()
        )
        material_receipts = Counter(
            (row.material_id, row.quantity, row.bound) for row in material_stacks
        )
        assert material_receipts == Counter(
            {
                ("material.altos.ferro_contrapeso", 1, True): 1,
                ("material.altos.liquen_pedreira", 1, True): 1,
            }
        )

    at_abrigo = await road.resume(actor)
    assert at_abrigo is not None and not at_abrigo.hunt_enabled and not at_abrigo.explore_enabled
    await road.travel_brazier(actor, ALTOS_ESCARPA_BRAZIER)
    at_escarpa = await road.resume(actor)
    assert at_escarpa is not None and at_escarpa.hunt_enabled and at_escarpa.explore_enabled
    rounds = disable_round_pvpve_for_test(RoundService(sessions, "ocaso"))
    blocked_round = await rounds.prepare_round(actor, 5)
    assert blocked_round is None or blocked_round.kind != "round_prepare"

    monkeypatch.setattr(road_module, "act", _terminal("victory"))
    manual = await start_manual_hunt_after_no_match(road, actor, monkeypatch)
    assert manual is not None and manual.kind == "combat"
    manual = await road.action(
        actor, manual.activity_id, manual.combat.version, "attack"
    )
    assert manual is not None and manual.kind == "hunt_victory"
    await road.acknowledge_result(actor)
    async with sessions() as session:
        character = await session.scalar(
            select(Character).where(Character.telegram_id == actor)
        )
        assert character is not None
        assert await session.scalar(
            select(Unlock.id).where(
                Unlock.character_id == character.id,
                Unlock.unlock_id == ALTOS_ESCARPA_ROUND_UNLOCK,
            )
        ) is not None
    round_ready = await rounds.prepare_round(actor, 5)
    assert round_ready is not None and round_ready.kind == "round_prepare"


@pytest.mark.asyncio
async def test_p25_scripted_combat_uses_shared_campaign_progress_without_economy(database):
    leader, helper = 779042, 779043
    _leader, road, sessions = await _seed_altos_exit(
        database, leader, level=41, p24_status="completed"
    )
    _helper, _helper_road, _ = await _seed_altos_exit(
        database, helper, level=41, p24_status="completed"
    )
    async with sessions() as session:
        helper_character = await session.scalar(
            select(Character).where(Character.telegram_id == helper)
        )
        assert helper_character is not None
        helper_name = helper_character.name

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(leader)
    invitation = await groups.invite(
        leader, helper_name, expected_group_revision=group.revision
    )
    await groups.respond_invite(
        helper,
        invitation.invite_id,
        expected_revision=invitation.revision,
        accept=True,
    )
    mission = AltosMissionService(sessions, "ocaso", groups=groups)

    for actor in (leader, helper):
        arrived = await road.travel_route(actor, ALTOS_ESCARPA_LABEL)
        assert arrived is not None and arrived.location == ALTOS_ESCARPA_LABEL
        view = await mission.resume_active(actor)
        assert view is not None and view.step == 2

    leader_view = await mission.resume(leader)
    assert leader_view is not None
    for action in (
        "inspect_contraforte",
        "inspect_cabo",
        "inspect_escora",
    ):
        leader_view = await mission.advance(leader, leader_view.state_version, action)
        assert leader_view is not None
    assert leader_view.step == 3
    helper_view = await mission.resume(helper)
    assert helper_view is not None and helper_view.step == 3

    proposal_view = await mission.propose_group_combat(
        leader, leader_view.state_version
    )
    assert proposal_view is not None and proposal_view.proposal_id is not None
    proposal = await groups.activity_proposal(leader, proposal_view.proposal_id)
    accepted = await groups.respond_activity(
        helper,
        proposal.proposal_id,
        expected_revision=proposal.revision,
        accept=True,
    )
    started = await mission.start_group_combat(
        leader,
        proposal.proposal_id,
        expected_revision=accepted.revision,
    )
    assert started is not None and started.combat is not None
    assert started.group_size == 2 and started.combat.party_mode
    encounter_id = started.encounter_id
    assert encounter_id is not None

    async with sessions.begin() as session:
        encounter = await session.get(CampaignSharedEncounter, encounter_id)
        assert encounter is not None
        combat = decode(
            encounter.combat_snapshot,
            encounter.id,
            encounter.ruleset_version,
            encounter.state_version,
        )
        enemy = combat.fighters["enemy"]
        enemy.hp = Decimal("1")
        enemy.stats = replace(enemy.stats, hp=Decimal("1"))
        enemy.takes_turn = False
        combat.order = tuple(key for key in combat.order if key != "enemy")
        combat.turn_index = 0
        encounter.combat_snapshot = encode(combat)

    views = [await mission.resume(actor) for actor in (leader, helper)]
    current_combat = next(view.combat for view in views if view and view.combat)
    turn_owner = active_player_key(current_combat)
    current = next(
        view for view in views if view and view.combat_actor_key == turn_owner
    )
    actor = (leader, helper)[views.index(current)]
    await mission.action(
        actor,
        current.activity_id,
        current_combat.version,
        "attack",
        target_id="enemy",
    )

    async with sessions() as session:
        for actor in (leader, helper):
            character = await session.scalar(
                select(Character).where(Character.telegram_id == actor)
            )
            assert character is not None
            quest = await session.scalar(
                select(Quest).where(
                    Quest.character_id == character.id,
                    Quest.quest_id == P25_ID,
                )
            )
            assert quest is not None and quest.step == 4
            bestiary = await session.scalar(
                select(BestiaryEntry).where(
                    BestiaryEntry.character_id == character.id,
                    BestiaryEntry.creature_id == "creature.altos.lobo_escarpa",
                )
            )
            assert bestiary is not None and bestiary.wins == 1
            assert not await session.scalar(
                select(RewardEvent.id).where(
                    RewardEvent.character_id == character.id,
                    RewardEvent.source_id == P25_REWARD_SOURCE,
                )
            )
