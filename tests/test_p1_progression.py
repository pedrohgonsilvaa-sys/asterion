from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.application.p1 import P1Service
from asterion.infrastructure.db.models import Character, Quest, WorldState


def test_p1_metadata_constraints_match_models():
    from asterion.infrastructure.db.models import Character as C
    from asterion.infrastructure.db.models import CodexEntry
    from asterion.infrastructure.db.models import Quest as Q

    assert any(getattr(x, "name", None) == "ck_character_crowns" for x in C.__table__.constraints)
    assert any(
        getattr(x, "name", None) == "ck_quest_state_version" for x in Q.__table__.constraints
    )
    assert any(
        getattr(x, "name", None) == "uq_character_codex" for x in CodexEntry.__table__.constraints
    )


@pytest.mark.asyncio
async def test_p1_follow_is_exactly_one_step_and_stale_is_noop(database):
    engine, sessions = database
    async with sessions() as s:
        from asterion.infrastructure.db.models import Account

        actor = 998877
        cid = uuid4()
        s.add(Account(telegram_id=actor))
        s.add(
            Character(
                id=cid,
                telegram_id=actor,
                server_id="ocaso",
                name="Heroa",
                race="remanescente",
                character_class="sentinela",
                stage="menu:ready",
                ruleset_version="gdd-1.4.3-baseline-1.0",
                level=1,
                xp=320,
                hp=Decimal("702"),
                max_hp=Decimal("702"),
            )
        )
        s.add(
            Quest(
                character_id=cid,
                quest_id="P1",
                title="Vozes na Estrada",
                status="active",
                step=1,
                content_version="tdo-1.0.2",
            )
        )
        s.add(
            WorldState(
                character_id=cid,
                region="Terras do Ocaso",
                location="Estrada das Cinzas",
            )
        )
        await s.commit()
    service = P1Service(sessions, "ocaso")
    result = await service.follow_road(actor, 0)
    assert result.step == 2
    stale = await service.follow_road(actor, 0)
    assert stale.step == 2
    assert stale.state_version == result.state_version
