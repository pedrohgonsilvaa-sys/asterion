"""Telegram screens for Treasury, Obras, Rename and Dissolution; activity middleware."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import update

from asterion.application.guilds import GuildProjectView
from asterion.bot.guild_activity import GuildActivityMiddleware
from asterion.bot.guilds_ui import (
    DEPOSIT_PROMPT,
    FOUND_PROMPT,
    RENAME_PROMPT,
    contribute_prompt,
    kind_from_contribute_prompt,
    pack,
    parse_crowns,
    render_guild_menu,
    render_new_project,
    render_works,
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


def test_amount_parsing_and_contribution_prompts():
    assert parse_crowns("20000") == 20_000
    assert parse_crowns(" 20.000 ") == 20_000
    for bad in ("", "-5", "20,5", "dez", "1" * 13):
        assert parse_crowns(bad) is None
    for kind in ProjectKind:
        for from_treasury in (False, True):
            prompt = contribute_prompt(kind, from_treasury=from_treasury)
            assert kind_from_contribute_prompt(prompt) == (kind, from_treasury)
    assert kind_from_contribute_prompt(DEPOSIT_PROMPT) is None


def test_works_screens_are_role_aware_and_carry_ids_only():
    leader = _with(_view(GuildRole.LEADER), treasury_crowns=40_000,
                   active_projects=(_project(),))  # fmt: skip
    member = _with(_view(GuildRole.MEMBER), active_projects=(_project(),))
    leader_works, member_works = render_works(leader), render_works(member)
    leader_labels = {b.text for r in leader_works.keyboard.inline_keyboard for b in r}
    member_labels = {b.text for r in member_works.keyboard.inline_keyboard for b in r}
    assert "Iniciar Obra" in leader_labels and "Iniciar Obra" not in member_labels
    assert "Tesouraria → Alojamentos" in leader_labels
    assert "Tesouraria → Alojamentos" not in member_labels
    assert "Contribuir · Alojamentos" in member_labels
    assert "40.000 Coroas" in leader_works.text

    two = _with(leader, active_projects=(_project(), _project(ProjectKind.FORGE)))
    assert "já tem 2 Obras" in render_new_project(two).text
    new_labels = [b.text for r in render_new_project(leader).keyboard.inline_keyboard for b in r]
    assert "Forja I · 20.000 · 6h" in new_labels
    assert not any(label.startswith("Alojamentos") for label in new_labels)

    frozen = _with(leader, dissolution_due_at=datetime(2026, 11, 11, tzinfo=UTC))
    frozen_labels = {b.text for r in render_works(frozen).keyboard.inline_keyboard for b in r}
    assert "Depositar na Tesouraria" not in frozen_labels
    menu = {b.text for r in render_guild_menu(frozen).keyboard.inline_keyboard for b in r}
    assert "Cancelar dissolução" in menu and "Dissolver Guilda" not in menu
    plain = {b.text for r in render_guild_menu(leader).keyboard.inline_keyboard for b in r}
    assert {"Renomear Guilda", "Dissolver Guilda", "Tesouraria e Obras"} <= plain
    officer = {b.text for r in render_guild_menu(_view(GuildRole.OFFICER)).keyboard.inline_keyboard
               for b in r}  # fmt: skip
    assert "Dissolver Guilda" not in officer and "Renomear Guilda" not in officer

    for screen in (leader_works, member_works, render_new_project(leader), render_works(frozen)):
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
    await client.say(alpha, "Aurora AUR", reply_prompt=FOUND_PROMPT)
    guild = await client.service.my_guild(alpha)
    invite = await client.service.invite(alpha, "Bravo")
    await client.service.respond_invite(bravo, invite.invite_id, accept=True)
    gid = pack(guild.guild_id)

    screen = await client.click(bravo, f"guild:works:{gid}")
    assert "Tesouraria · 0 Coroas" in screen.text
    screen = await client.say(bravo, "30.000", reply_prompt=DEPOSIT_PROMPT)
    assert "Depósito registrado: 30000 Coroas." in [m for _c, m in client.sent_to_others]
    assert "Tesouraria · 30.000 Coroas" in screen.text

    screen = await client.click(alpha, f"guild:newp:{gid}")
    screen = await client.click(alpha, _button(screen, "Alojamentos I · 20.000 · 6h"))
    assert "Alojamentos I · Financiamento · 0/20.000" in screen.text
    # A member contributes from the wallet; the Treasury button is the Leader's only.
    bravo_works = await client.click(bravo, f"guild:works:{gid}")
    bravo_labels = {b.text for r in bravo_works.reply_markup.inline_keyboard for b in r}
    assert "Tesouraria → Alojamentos" not in bravo_labels
    prompt = contribute_prompt(ProjectKind.LODGING, from_treasury=False)
    screen = await client.say(bravo, "5000", reply_prompt=prompt)
    assert "5.000/20.000" in screen.text
    prompt = contribute_prompt(ProjectKind.LODGING, from_treasury=True)
    screen = await client.say(alpha, "99999", reply_prompt=prompt)
    assert "Construção até" in screen.text
    assert (await client.service.my_guild(alpha)).treasury_crowns == 15_000

    # The Treasury holds exactly the 15.000 a rename costs; the TAG is kept.
    screen = await client.say(alpha, "Brasa -", reply_prompt=RENAME_PROMPT)
    assert "Brasa [AUR]" in screen.text and "Tesouraria · 0 Coroas" in screen.text
    screen = await client.say(alpha, "Outra -", reply_prompt=RENAME_PROMPT)
    assert "Renome está em recarga" in screen.text

    screen = await client.click(alpha, f"guild:diss:{gid}")
    screen = await client.click(alpha, _button(screen, "Confirmar"))
    assert "Dissolução marcada" in screen.text
    screen = await client.click(alpha, _button(screen, "Cancelar dissolução"))
    assert "Dissolução marcada" not in screen.text
    # Officers and Members cannot dissolve, even with a forged button.
    await client.click(bravo, f"guild:dissok:{gid}")
    assert (await client.service.my_guild(alpha)).dissolution_due_at is None
