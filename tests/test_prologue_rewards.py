"""Prologue rewards are really granted once, and the Braseiro does not promise HP recovery."""

from decimal import Decimal

from sqlalchemy import func, select

from asterion.application.prologue import (
    PURSE_MATERIAL,
    PURSE_MATERIAL_QUANTITY,
    PURSE_SOURCE,
    VICTORY_CROWNS,
    VICTORY_SOURCE,
    PrologueService,
)
from asterion.bot.prologue_ui import SCENE_IDS, render_brazier, render_scene
from asterion.domain.creation import PROLOGUE
from asterion.domain.prologue import PROFILE, REWARD_XP, RULESET
from asterion.infrastructure.db.models import (
    Account,
    Character,
    MaterialStack,
    RewardComponent,
    RewardEvent,
)


async def _character(database, actor=1):
    from asterion.domain.combat_math import class_stats, racial_stats

    stats = racial_stats(class_stats("sentinela", 1), "remanescente")
    async with database[1].begin() as session:
        session.add(Account(telegram_id=actor))
        row = Character(
            telegram_id=actor,
            server_id="ocaso",
            name="Heroa",
            race="remanescente",
            character_class="sentinela",
            stage=PROLOGUE,
            ruleset_version=RULESET,
            level=1,
            xp=0,
            crowns=0,
            hp=stats.hp,
            max_hp=stats.hp,
        )
        session.add(row)
    return row


async def _weaken_enemy(database, view):
    """Make the first combat short: the rewards are under test, not the balance."""
    from asterion.infrastructure.db.combat_codec import decode, encode
    from asterion.infrastructure.db.models import CombatRecord, GameActivity

    async with database[1].begin() as session:
        activity = await session.get(GameActivity, view.activity_id)
        record = await session.scalar(select(CombatRecord))
        state = decode(
            record.snapshot, record.id, activity.ruleset_version, activity.state_version
        )
        state.fighters["enemy"].hp = Decimal(1)
        record.snapshot = encode(state)


async def _win(service, view):
    for _ in range(40):
        if view.combat.result:
            break
        view = await service.action(1, view.activity_id, view.combat.version, "attack")
    assert view.combat.result == "victory"
    return view


async def _row(database):
    async with database[1]() as session:
        return await session.scalar(select(Character).where(Character.telegram_id == 1))


async def _count(database, model, **filters):
    async with database[1]() as session:
        query = select(func.count()).select_from(model)
        for column, value in filters.items():
            query = query.where(getattr(model, column) == value)
        return await session.scalar(query)


async def test_victory_grants_320_xp_and_3_crowns_once(database):
    await _character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    view = await service.enter(1)
    await _weaken_enemy(database, view)
    await _win(service, view)

    row = await _row(database)
    assert row.xp == REWARD_XP == 320
    assert row.crowns == VICTORY_CROWNS == 3
    assert await _count(database, RewardEvent, source_id=VICTORY_SOURCE) == 1

    # Repeating the finished combat or the last action must not pay again.
    again = await service.resume(1)
    assert again is not None
    await service.action(1, view.activity_id, view.combat.version, "attack")
    row = await _row(database)
    assert (row.xp, row.crowns) == (320, 3)
    assert await _count(database, RewardEvent, source_id=VICTORY_SOURCE) == 1


async def test_wreck_purse_grants_18_crowns_and_residue_once(database):
    await _character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)

    assert await service.collect_wreck_purse(1) is True
    row = await _row(database)
    assert row.crowns == 18
    async with database[1]() as session:
        stack = await session.scalar(
            select(MaterialStack).where(
                MaterialStack.character_id == row.id,
                MaterialStack.material_id == PURSE_MATERIAL,
            )
        )
    assert stack is not None
    assert stack.quantity == PURSE_MATERIAL_QUANTITY == 1
    assert stack.bound is True

    # Revisiting the wreck: nothing more is paid and no second material appears.
    assert await service.collect_wreck_purse(1) is False
    row = await _row(database)
    assert row.crowns == 18
    async with database[1]() as session:
        quantity = await session.scalar(
            select(MaterialStack.quantity).where(
                MaterialStack.character_id == row.id,
                MaterialStack.material_id == PURSE_MATERIAL,
            )
        )
    assert quantity == 1
    assert await _count(database, RewardEvent, source_id=PURSE_SOURCE) == 1


async def test_purse_reward_components_record_crowns_and_material(database):
    await _character(database)
    service = PrologueService(database[1], "ocaso", PROFILE)
    await service.collect_wreck_purse(1)
    async with database[1]() as session:
        kinds = sorted(
            row.kind
            for row in (
                await session.scalars(
                    select(RewardComponent)
                    .join(RewardEvent, RewardComponent.reward_event_id == RewardEvent.id)
                    .where(RewardEvent.source_id == PURSE_SOURCE)
                )
            ).all()
        )
    assert kinds == ["crowns", "material"]


def test_brazier_shows_arrival_hp_and_uses_approved_narration():
    name = "Heroa"
    screen = render_brazier(name, Decimal(80), Decimal(100))
    assert "<code>80 / 100</code>" in screen.text
    assert "<code>100 / 100</code>" not in screen.text
    assert (
        "<i>O fogo permanece aceso entre as pedras. O calor atravessa o corpo de "
        f"{name}, enquanto a estrada permanece à frente, pronta para ser seguida.</i>"
    ) in screen.text
    assert "devolve as forças" not in screen.text


def test_prologue_flow_has_no_sulcos_recentes():
    assert "sulcos" not in SCENE_IDS
    for node in SCENE_IDS:
        screen = render_scene(node)
        assert "Sulcos" not in screen.text
        callbacks = [b.callback_data for row in screen.keyboard.inline_keyboard for b in row]
        assert "pl:sulcos" not in callbacks
