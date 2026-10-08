from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from asterion.application.campaign_objectives import (
    campaign_roster_ids,
    lock_campaign_roster,
    present_campaign_members,
    record_campaign_objective_credit,
)
from asterion.application.groups import GroupService
from asterion.infrastructure.db.models import (
    Account,
    CampaignObjectiveCredit,
    Character,
    GameActivity,
    Quest,
    WorldState,
)


@pytest.mark.asyncio
async def test_objective_credit_targets_only_present_same_checkpoint_members(database):
    sessions = database[1]
    actors = (992301, 992302, 992303, 992304)
    names = ("Hera", "Breno", "Celia", "Dora")
    async with sessions.begin() as session:
        for actor, name in zip(actors, names, strict=True):
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id="ocaso",
                name=name,
                race="remanescente",
                character_class="sentinela",
                stage="road_active",
                ruleset_version="test",
                level=1,
                xp=0,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
            )
            session.add(character)
            await session.flush()
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P_TEST",
                    title="Objective test",
                    status="active",
                    step=2 if actor == actors[2] else 1,
                    content_version="test-v1",
                    state_version=0,
                )
            )
            session.add(
                WorldState(
                    character_id=character.id,
                    region="Terras do Ocaso",
                    location=(
                        "Charneca da Fuligem"
                        if actor == actors[3]
                        else "Estrada das Cinzas"
                    ),
                )
            )

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    for actor, name in zip(actors[1:], names[1:], strict=True):
        invite = await groups.invite(actors[0], name, expected_group_revision=group.revision)
        group = await groups.respond_invite(
            actor, invite.invite_id, expected_revision=invite.revision, accept=True
        )

    async with sessions.begin() as session:
        owner = await session.scalar(
            select(Character).where(Character.telegram_id == actors[0])
        )
        group_id, roster = await lock_campaign_roster(session, owner.id)
        assert group_id is not None
        assert await campaign_roster_ids(session, owner.id) == roster
        present = await present_campaign_members(
            session,
            character_ids=roster,
            quest_id="P_TEST",
            content_version="test-v1",
            step=1,
            region="Terras do Ocaso",
            location="Estrada das Cinzas",
        )
        assert {member.character.telegram_id for member in present} == set(actors[:2])
        for member in present:
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id="P_TEST",
                objective_id="p_test.signal",
                source_key="p_test.signal:footprints",
                evidence={"location": "Estrada das Cinzas"},
            )
            await record_campaign_objective_credit(
                session,
                character_id=member.character.id,
                quest_id="P_TEST",
                objective_id="p_test.signal",
                source_key="p_test.signal:footprints",
                evidence={"location": "Estrada das Cinzas"},
            )

    async with sessions() as session:
        credits = list((await session.scalars(select(CampaignObjectiveCredit))).all())
        assert len(credits) == 2
        assert {credit.character_id for credit in credits} == {
            member.character.id for member in present
        }


@pytest.mark.asyncio
async def test_objective_credit_excludes_member_with_active_foreground(database):
    sessions = database[1]
    actors = (992311, 992312)
    names = ("Hera", "Breno")
    async with sessions.begin() as session:
        characters = []
        for actor, name in zip(actors, names, strict=True):
            session.add(Account(telegram_id=actor))
            character = Character(
                telegram_id=actor,
                server_id="ocaso",
                name=name,
                race="remanescente",
                character_class="sentinela",
                stage="road_active",
                ruleset_version="test",
                level=1,
                xp=0,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
            )
            session.add(character)
            characters.append(character)
            await session.flush()
            session.add(
                Quest(
                    character_id=character.id,
                    quest_id="P_TEST",
                    title="Objective test",
                    status="active",
                    step=1,
                    content_version="test-v1",
                    state_version=0,
                )
            )
            session.add(
                WorldState(
                    character_id=character.id,
                    region="Terras do Ocaso",
                    location="Estrada das Cinzas",
                )
            )
        await session.flush()
        session.add(
            GameActivity(
                id=uuid4(),
                character_id=characters[1].id,
                content_id="busy",
                status="active",
                state_version=0,
                ruleset_version="test",
            )
        )

    groups = GroupService(sessions, "ocaso")
    group = await groups.create_group(actors[0])
    invite = await groups.invite(actors[0], names[1], expected_group_revision=group.revision)
    await groups.respond_invite(
        actors[1], invite.invite_id, expected_revision=invite.revision, accept=True
    )

    async with sessions.begin() as session:
        owner = await session.scalar(
            select(Character).where(Character.telegram_id == actors[0])
        )
        _group_id, roster = await lock_campaign_roster(session, owner.id)
        present = await present_campaign_members(
            session,
            character_ids=roster,
            quest_id="P_TEST",
            content_version="test-v1",
            step=1,
            region="Terras do Ocaso",
            location="Estrada das Cinzas",
        )
        assert [member.character.telegram_id for member in present] == [actors[0]]
