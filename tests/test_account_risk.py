"""GDD §36: linked accounts sharing an activity produce review flags, never blocks."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from asterion.account_risk_cli import run as cli_run
from asterion.application.account_risk import AccountRiskAdmin
from asterion.application.dungeons import DUNGEON_ACTIVITY_PREFIX, DungeonService
from asterion.application.groups import ActivityEligibility
from asterion.infrastructure.db.models import AccountRiskFlag
from tests.test_dungeon_multiplayer import _form_matchmade_party, _seed_party
from tests.test_groups import NOW, _invite_and_join, _seed_characters, _service
from tests.test_pvpve_integration import ACTORS as HUNTERS
from tests.test_pvpve_integration import _collision_for, _seed_hunters


async def _eligible(_session, character, _context):
    return ActivityEligibility("eligible", fingerprint=f"here:{character.name}")


async def _create(_session, proposal, _roster):
    return f"campaign:{proposal.id.hex}"


async def _start_trio(database, actors):
    service = _service(database)
    await service.create_group(actors["Alpha"])
    await _invite_and_join(service, actors["Alpha"], actors["Bravo"], "Bravo")
    group = await _invite_and_join(service, actors["Alpha"], actors["Cedar"], "Cedar")
    ids = {member.name: member.character_id for member in group.members}
    proposal = await service.propose_activity(
        actors["Alpha"],
        activity_type="campaign_boss",
        participant_character_ids=(ids["Alpha"], ids["Bravo"], ids["Cedar"]),
        journey_reference_character_id=ids["Alpha"],
        context_payload={"mission": "P1"},
        eligibility_resolver=_eligible,
        now=NOW,
    )
    for name in ("Bravo", "Cedar"):
        proposal = await service.respond_activity(
            actors[name],
            proposal.proposal_id,
            expected_revision=proposal.revision,
            accept=True,
            now=NOW + timedelta(seconds=1),
        )
    assert proposal.status == "ready"

    async def start():
        return await service.start_activity(
            actors["Alpha"],
            proposal.proposal_id,
            expected_revision=proposal.revision,
            eligibility_resolver=_eligible,
            create_activity=_create,
            now=NOW + timedelta(seconds=2),
        )

    return start


async def _flags(sessions):
    async with sessions() as session:
        return list(
            (await session.scalars(select(AccountRiskFlag).order_by(AccountRiskFlag.id))).all()
        )


async def test_group_activity_flags_only_linked_pair_and_never_blocks(database):
    actors = await _seed_characters(database)
    admin = AccountRiskAdmin(database[1])
    assert await admin.link(actors["Bravo"], actors["Alpha"], note="declarado")
    start = await _start_trio(database, actors)

    started = await start()
    assert started.started
    again = await start()
    assert again.started and again.activity_reference == started.activity_reference

    flags = await _flags(database[1])
    assert len(flags) == 1
    flag = flags[0]
    assert (flag.account_a, flag.account_b) == tuple(sorted((actors["Alpha"], actors["Bravo"])))
    assert flag.activity_kind == "group_activity"
    assert flag.activity_reference == started.activity_reference
    assert flag.server_id == "ocaso"
    assert flag.status == "open"
    assert flag.evidence["participant_accounts"] == 3
    assert set(flag.evidence["characters"]) == {str(actors["Alpha"]), str(actors["Bravo"])}


async def test_group_activity_without_links_writes_no_flags(database):
    actors = await _seed_characters(database)
    start = await _start_trio(database, actors)
    assert (await start()).started
    assert await _flags(database[1]) == []


@pytest.mark.parametrize("linked", (True, False))
async def test_matchmade_dungeon_flags_linked_accounts(database, linked):
    actors = (782101, 782102)
    sessions, _character_ids = await _seed_party(database, actors)
    if linked:
        await AccountRiskAdmin(sessions).link(*actors)
    ready = await _form_matchmade_party(
        DungeonService(sessions, "ocaso"), actors, "dungeon.tdo.cripta_ocaso"
    )
    assert ready.run_id is not None
    flags = await _flags(sessions)
    if not linked:
        assert flags == []
        return
    assert [(f.account_a, f.account_b, f.activity_kind) for f in flags] == [
        (782101, 782102, "dungeon_run")
    ]
    assert flags[0].activity_reference == f"{DUNGEON_ACTIVITY_PREFIX}{ready.run_id.hex}"


@pytest.mark.parametrize("linked", (True, False))
async def test_pvpve_collision_flags_linked_accounts_on_opposite_sides(database, linked):
    characters, road = await _seed_hunters(database)
    if linked:
        await AccountRiskAdmin(database[1]).link(*HUNTERS[:2])
    assert (await road.start_hunt(HUNTERS[0])).kind == "hunt_queue"
    clash = await road.start_hunt(HUNTERS[1])
    assert clash.kind == "combat" and clash.combat_context == "pvpve"
    flags = await _flags(database[1])
    if not linked:
        assert flags == []
        return
    collision = await _collision_for(database, characters[HUNTERS[0]])
    assert [(f.account_a, f.account_b, f.activity_kind) for f in flags] == [
        (*sorted(HUNTERS[:2]), "pvpve_collision")
    ]
    assert flags[0].activity_reference == f"pvpve:{collision.id.hex}"
    assert collision.status == "active"  # only marks; the clash goes on


async def test_admin_links_reviews_and_cli(database):
    actors = await _seed_characters(database)
    sessions = database[1]
    admin = AccountRiskAdmin(sessions)
    with pytest.raises(ValueError):
        await admin.link(actors["Alpha"], actors["Alpha"])
    assert await cli_run(["link", str(actors["Alpha"]), str(actors["Bravo"])], sessions) == [
        "vínculo criado"
    ]
    assert await cli_run(["link", str(actors["Bravo"]), str(actors["Alpha"])], sessions) == [
        "vínculo já existia"
    ]
    start = await _start_trio(database, actors)
    await start()

    [line] = await cli_run(["flags"], sessions)
    flag_id = line.split()[0]
    [reviewed] = await cli_run(
        ["review", flag_id, "dismissed", "--note", "jogaram separados"], sessions
    )
    assert "dismissed" in reviewed and "jogaram separados" in reviewed
    assert await cli_run(["flags"], sessions) == ["nenhuma flag"]
    async with sessions() as session:
        flag = await session.scalar(select(AccountRiskFlag))
        assert flag.reviewed_at is not None
        assert await session.scalar(select(func.count()).select_from(AccountRiskFlag)) == 1

    assert await cli_run(["unlink", str(actors["Alpha"]), str(actors["Bravo"])], sessions) == [
        "vínculo removido"
    ]
    assert await cli_run(["links"], sessions) == ["nenhum vínculo"]
    # Removing the link keeps the historical flag for audit.
    assert len(await cli_run(["flags", "--status", "all"], sessions)) == 1
