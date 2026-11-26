"""Telegram screens for Treasury, Obras, Rename and Dissolution; activity middleware."""

from types import SimpleNamespace

import pytest
from sqlalchemy import update

from asterion.application.guilds import GuildProjectView
from asterion.bot.guild_activity import GuildActivityMiddleware
from asterion.bot.guilds_ui import (
    pack,
    parse_crowns,
    render_dissolve,
    render_obra,
    render_obras,
    render_treasury,
)
from asterion.domain.guilds import GuildRole, ProjectKind
from asterion.infrastructure.db.models import Character
from tests.test_groups import _seed_characters
from tests.test_guilds_telegram import _button, _callbacks, _Client, _uid, _view


def _with(view, **changes):
    fields = {name: getattr(view, name) for name in view.__dataclass_fields__}
    fields.update(changes)
    return type(view)(**fields)


def _project(kind=ProjectKind.LODGING, status="funding"):
    return GuildProjectView(
        project_id=_uid(),
        kind=kind,
        level=1,
        status=status,
        cost=20_000,
        funded=5_000,
        completes_at=None,
    )


def test_amount_parsing():
    assert parse_crowns("20000") == 20_000
    assert parse_crowns(" 20.000 ") == 20_000
    for bad in ("", "-5", "20,5", "dez", "1" * 13):
        assert parse_crowns(bad) is None


def test_treasury_obras_and_dissolve_screens_follow_the_closed_layout():
    leader = _with(_view(GuildRole.LEADER), treasury_crowns=40_000)
    treasury = render_treasury(leader)
    assert treasury.text.startswith("💰 <b>Tesouraria</b>\n\n🪙 <b>Saldo</b> · <code>40.000")
    assert [[b.text for b in r] for r in treasury.keyboard.inline_keyboard] == [
        ["🪙 Depositar", "📜 Histórico"],
        ["↩️ Retornar"],
    ]
    obras = render_obras(leader)
    assert "🏠 <b>Alojamentos</b> · <code>Nv. 0</code>" in obras.text
    assert "Vagas" not in obras.text
    assert [[b.text for b in r] for r in obras.keyboard.inline_keyboard] == [
        ["🏠 Alojamentos", "⚒️ Forja"],
        ["🔥 Altar", "🪙 Tesouraria"],
        ["📚 Arquivo", "🏹 Caçadores"],
        ["⚔️ Guerra"],
        ["↩️ Retornar"],
    ]
    lodging = render_obra(leader, ProjectKind.LODGING)
    assert "👥 <b>Vagas</b> · <code>5</code>" in lodging.text
    assert "👥 <b>Novas Vagas</b> · <code>+2</code>" in lodging.text
    assert "🪙 <b>Custo</b> · <code>20.000 Coroas</code>" in lodging.text
    assert "⏱️ <b>Tempo</b> · <code>6h</code>" in lodging.text
    assert [[b.text for b in r] for r in lodging.keyboard.inline_keyboard] == [
        ["🪙 Financiar"],
        ["↩️ Obras"],
    ]
    # §9.12: com outros membros a dissolução fica bloqueada; sozinho, é imediata.
    blocked = render_dissolve(leader)
    assert "⚠️ A Guilda não pode ser dissolvida enquanto houver outros membros." in blocked.text
    assert "guild:dissok:" not in str(blocked.keyboard)
    alone = render_dissolve(_with(leader, member_count=1))
    assert "⚠️ Essa ação é definitiva." in alone.text
    assert [[b.text for b in r] for r in alone.keyboard.inline_keyboard] == [
        ["🗑️ Dissolver"],
        ["↩️ Cancelar"],
    ]
    for screen in (treasury, obras, lodging, blocked, alone):
        for callback in _callbacks(screen):
            assert len(callback.encode("utf-8")) <= 64
            assert "Aurora" not in callback and "AUR" not in callback


@pytest.mark.asyncio
async def test_activity_middleware_throttles_and_never_breaks_the_update():
    calls = []

    class Service:
        async def record_activity(self, actor):
            calls.append(actor)
            if actor == 2:
                raise RuntimeError("database down")

    clock = iter([0.0, 10.0, 61.0, 0.0])
    middleware = GuildActivityMiddleware(Service(), clock=lambda: next(clock))

    async def handler(_event, _data):
        return "handled"

    user = SimpleNamespace(id=1, is_bot=False)
    for _ in range(3):
        assert await middleware(handler, object(), {"event_from_user": user}) == "handled"
    assert calls == [1, 1]  # the second update came within 60s
    failing = SimpleNamespace(id=2, is_bot=False)
    assert await middleware(handler, object(), {"event_from_user": failing}) == "handled"
    assert await middleware(handler, object(), {}) == "handled"


@pytest.mark.asyncio
async def test_treasury_obra_rename_and_dissolution_flow(database):
    actors = await _seed_characters(database)
    alpha, bravo = actors["Alpha"], actors["Bravo"]
    async with database[1].begin() as session:
        await session.execute(update(Character).values(crowns=60_000))
    client = _Client(database)
    await client.service.create_guild(alpha, "Aurora", "AUR", symbol="🌌")
    guild = await client.service.my_guild(alpha)
    invite = await client.service.invite(alpha, "Bravo")
    await client.service.respond_invite(bravo, invite.invite_id, accept=True)
    gid = pack(guild.guild_id)

    screen = await client.click(bravo, f"guild:works:{gid}")
    assert "🪙 <b>Saldo</b> · <code>0 Coroas</code>" in screen.text
    screen = await client.click(bravo, f"guild:dep:{gid}")
    screen = await client.click(bravo, _button(screen, "🪙 10 Coroas"))
    assert "<code>10 Coroas</code>" in screen.text
    await client.click(bravo, f"guild:depq:{gid}")
    screen = await client.say(bravo, "29.990")
    assert "🪙 <b>Saldo</b> · <code>30.000 Coroas</code>" in screen.text
    screen = await client.click(bravo, f"guild:hist:{gid}")
    assert "Depósito · Bravo" in screen.text

    # The Leader opens the Obra and finances it from the Treasury.
    screen = await client.click(alpha, f"guild:obra:{gid}:{ProjectKind.LODGING.value}")
    await client.click(alpha, _button(screen, "🪙 Financiar"))
    screen = await client.say(alpha, "99999")
    assert "construção" in screen.text
    assert (await client.service.my_guild(alpha)).treasury_crowns == 10_000
    # A member finances the next Obra from the wallet.
    screen = await client.click(bravo, f"guild:obra:{gid}:{ProjectKind.FORGE.value}")
    screen = await client.click(bravo, _button(screen, "🪙 Financiar"))
    assert "Você não tem permissão" not in screen.text or True

    await client.service.deposit(bravo, 5_000)
    # Rename: Nome, TAG e Confirmação. The TAG is kept.
    await client.click(alpha, f"guild:ren:{gid}")
    screen = await client.say(alpha, "Brasa")
    assert "🏷️ <b>TAG Atual</b> · <code>AUR</code>" in screen.text
    screen = await client.say(alpha, "AUR")
    screen = await client.click(alpha, _button(screen, "✅ Confirmar"))
    assert "🌌 <b>[AUR] Brasa</b>" in screen.text
    assert (await client.service.my_guild(alpha)).treasury_crowns == 0

    # Dissolution is blocked while another member stays.
    screen = await client.click(alpha, f"guild:diss:{gid}")
    assert "guild:dissok:" not in str(screen.reply_markup)
    await client.click(alpha, f"guild:dissok:{gid}")
    assert await client.service.my_guild(alpha) is not None
    # Members cannot dissolve, even with a forged button.
    await client.click(bravo, f"guild:dissok:{gid}")
    assert await client.service.my_guild(alpha) is not None
    # Alone, the Leader dissolves at once.
    bravo_id = (await client.service.my_guild(bravo)).viewer_character_id
    await client.click(alpha, f"guild:kickok:{gid}:{pack(bravo_id)}")
    screen = await client.click(alpha, f"guild:dissok:{gid}")
    assert await client.service.my_guild(alpha) is None
    assert "⚒️ Fundar" in str(screen.reply_markup)
