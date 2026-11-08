import re
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.methods import EditMessageText, SendMessage
from aiogram.types import Chat, User
from aiogram.types import Message as TelegramMessage

from asterion.application.guilds import (
    GuildApplicationView,
    GuildInviteView,
    GuildMemberView,
    GuildPage,
    GuildService,
    GuildView,
    PublicGuildView,
)
from asterion.bot.guilds_handlers import guilds_router
from asterion.bot.guilds_ui import (
    FOUND_PROMPT,
    GUILD_ERROR_MESSAGES,
    INVITE_PROMPT,
    SEARCH_PROMPT,
    error_text,
    pack,
    render_browse,
    render_guild_menu,
    render_inbox,
    render_manage_members,
    render_my_applications,
    render_public_page,
    render_received_applications,
    render_search_results,
    unpack,
)
from asterion.domain.guilds import GuildRole, Recruitment
from tests.test_character_surfaces_telegram import _last_screen, _message_update
from tests.test_creation_ui import callback_update
from tests.test_groups import _seed_characters


def _callbacks(screen):
    return [
        button.callback_data
        for row in screen.keyboard.inline_keyboard
        for button in row
    ]


def _member(role, name="Alpha"):
    return GuildMemberView(
        character_id=uuid4(),
        name=name,
        level=4,
        character_class="sentinela",
        role=role,
        joined_at=None,
    )


def _view(viewer_role, recruitment=Recruitment.OPEN):
    viewer = _member(viewer_role, "Alpha")
    others = [
        _member(GuildRole.OFFICER, "Bravo"),
        _member(GuildRole.MEMBER, "Cedar"),
    ]
    return GuildView(
        guild_id=uuid4(),
        name="Aurora",
        tag="AUR",
        recruitment=recruitment,
        revision=0,
        member_count=3,
        capacity=5,
        over_cap=False,
        viewer_character_id=viewer.character_id,
        viewer_role=viewer_role,
        members=(viewer, *others),
    )


def _public(open_=True):
    return PublicGuildView(
        guild_id=uuid4(),
        name="Aurora",
        tag="AUR",
        member_count=2,
        capacity=5,
        recruitment=Recruitment.OPEN if open_ else Recruitment.CLOSED,
        accepts_applications=open_,
    )


def test_pack_roundtrip_is_compact():
    value = uuid4()
    assert len(pack(value)) == 22
    assert unpack(pack(value)) == value
    with pytest.raises(ValueError):
        unpack("curto")


def test_every_guild_error_code_has_a_portuguese_message():
    source = Path("src/asterion/application/guilds.py").read_text(encoding="utf-8")
    codes = set(re.findall(r'GuildError\("([a-z_]+)"\)', source))
    codes |= {"invalid_name", "invalid_tag"}  # raised from the domain normalisers
    assert codes <= set(GUILD_ERROR_MESSAGES)
    assert all(error_text(code).endswith(".") for code in codes)
    assert error_text("codigo_inexistente") == "Não foi possível concluir essa ação."


def test_guild_screens_use_ids_only_and_fit_telegram_limit():
    leader, officer, member = (
        _view(GuildRole.LEADER),
        _view(GuildRole.OFFICER),
        _view(GuildRole.MEMBER),
    )
    application = GuildApplicationView(
        application_id=uuid4(),
        guild_id=leader.guild_id,
        guild_name="Aurora",
        guild_tag="AUR",
        character_id=uuid4(),
        character_name="Doran",
        character_level=3,
        status="pending",
        closed_by=None,
        created_at=None,
    )
    invite = GuildInviteView(
        invite_id=uuid4(),
        guild_id=leader.guild_id,
        guild_name="Aurora",
        guild_tag="AUR",
        invitee_character_id=uuid4(),
        invitee_name="Doran",
        invitee_telegram_id=1,
        inviter_name="Alpha",
        status="pending",
    )
    screens = [
        render_guild_menu(None, invites=2),
        render_guild_menu(leader),
        render_guild_menu(officer),
        render_guild_menu(member),
        render_manage_members(leader),
        render_manage_members(officer),
        render_public_page(_public()),
        render_public_page(_public(open_=False)),
        render_public_page(None),
        render_search_results("Aurora", [_public()]),
        render_browse(GuildPage(items=(_public(),), next_after=uuid4()), first=False),
        render_my_applications([application]),
        render_inbox([invite]),
        render_received_applications(leader.guild_id, [application]),
    ]
    for screen in screens:
        for callback in _callbacks(screen):
            assert len(callback.encode("utf-8")) <= 64
            assert "Aurora" not in callback and "AUR" not in callback


def test_menu_buttons_depend_on_role():
    def labels(view, **kwargs):
        return {
            button.text
            for row in render_guild_menu(view, **kwargs).keyboard.inline_keyboard
            for button in row
        }

    without = labels(None, invites=3)
    assert {"Fundar Guilda", "Procurar Guilda", "Minhas Inscrições"} <= without
    assert "Convites recebidos · 3" in without

    leader, officer, member = (
        labels(_view(GuildRole.LEADER)),
        labels(_view(GuildRole.OFFICER)),
        labels(_view(GuildRole.MEMBER)),
    )
    assert "Convidar" in leader and "Convidar" in officer and "Convidar" not in member
    assert "Fechar recrutamento" in leader
    assert "Sair da Guilda" not in leader  # the Leader must transfer first
    assert "Sair da Guilda" in officer and "Sair da Guilda" in member

    def manage(view):
        return {
            button.text
            for row in render_manage_members(view).keyboard.inline_keyboard
            for button in row
        }

    leader_actions = " ".join(manage(_view(GuildRole.LEADER)))
    officer_actions = " ".join(manage(_view(GuildRole.OFFICER)))
    assert "Promover" in leader_actions and "Rebaixar" in leader_actions
    assert "Liderança" in leader_actions
    assert "Promover" not in officer_actions and "Liderança" not in officer_actions
    assert "Expulsar Cedar" in officer_actions and "Expulsar Bravo" not in officer_actions


class _Client:
    def __init__(self, database):
        self.service = GuildService(database[1], "ocaso")
        self.dispatcher = Dispatcher(disable_fsm=True)
        self.dispatcher.include_router(guilds_router(self.service, {}))
        self.bot = Bot("123456:local-test-token")
        self.update_id = 0
        self.ids = iter(range(5000, 6000))
        self.sent_to_others = []

        async def respond(_bot, method, **_kwargs):
            if isinstance(method, (SendMessage, EditMessageText)):
                chat_id = getattr(method, "chat_id", None)
                if isinstance(method, SendMessage) and chat_id is not None:
                    self.sent_to_others.append((chat_id, method.text))
                return TelegramMessage(
                    message_id=getattr(method, "message_id", None) or next(self.ids),
                    date=1,
                    chat=Chat(id=chat_id or 1, type="private"),
                    from_user=User(id=123456, is_bot=True, first_name="Asterion"),
                    text=method.text,
                )
            return True

        self.bot.session.make_request = AsyncMock(side_effect=respond)

    async def click(self, actor, data):
        self.update_id += 1
        await self.dispatcher.feed_raw_update(
            self.bot, callback_update(data, actor=actor, update_id=self.update_id)
        )
        return _last_screen(self.bot)

    async def say(self, actor, text, reply_prompt=None):
        self.update_id += 1
        reply = None
        if reply_prompt is not None:
            reply = {
                "message_id": 700,
                "date": 1,
                "chat": {"id": actor, "type": "private"},
                "from": {"id": 123456, "is_bot": True, "first_name": "Asterion"},
                "text": reply_prompt,
            }
        await self.dispatcher.feed_raw_update(
            self.bot,
            _message_update(text, actor=actor, update_id=self.update_id, reply_to=reply),
        )
        return _last_screen(self.bot)


def _button(screen, label):
    for row in screen.reply_markup.inline_keyboard:
        for button in row:
            if button.text == label:
                return button.callback_data
    shown = [b.text for r in screen.reply_markup.inline_keyboard for b in r]
    raise AssertionError(f"{label!r} not in {shown}")


@pytest.mark.asyncio
async def test_found_search_apply_approve_and_manage_flow(database):
    actors = await _seed_characters(database)
    alpha, bravo, cedar = actors["Alpha"], actors["Bravo"], actors["Cedar"]
    client = _Client(database)

    screen = await client.say(alpha, "/guilda")
    assert "ainda não faz parte" in screen.text
    # a bad Name is answered in Portuguese and nothing is created
    screen = await client.say(alpha, "Au AUR", reply_prompt=FOUND_PROMPT)
    assert "3 a 16 letras" in screen.text
    assert await client.service.my_guild(alpha) is None
    screen = await client.say(alpha, "Aurora AUR", reply_prompt=FOUND_PROMPT)
    assert "Aurora [AUR]" in screen.text and "Líder" in screen.text

    # a closed Guild shows no application button on its public page
    guild = await client.service.my_guild(alpha)
    screen = await client.click(bravo, f"guild:page:{pack(guild.guild_id)}")
    assert "não aceita inscrições" in screen.text

    screen = await client.click(alpha, f"guild:recr:o:{pack(guild.guild_id)}")
    assert "Recrutamento · Aberto" in screen.text

    # search by TAG, open the public page, apply
    screen = await client.say(bravo, "aur", reply_prompt=SEARCH_PROMPT)
    page_callback = _button(screen, "Aurora [AUR] · 1/5")
    screen = await client.click(bravo, page_callback)
    screen = await client.click(bravo, _button(screen, "Enviar Inscrição"))
    assert "Pendente" in screen.text

    # the Leader sees and approves it
    screen = await client.click(alpha, f"guild:recv:{pack(guild.guild_id)}")
    assert "Bravo" in screen.text
    screen = await client.click(alpha, _button(screen, "Aprovar · 1"))
    assert "Nenhuma inscrição pendente" in screen.text
    assert (await client.service.my_guild(bravo)).viewer_role is GuildRole.MEMBER

    # invite Cedar by name; Cedar accepts from the inbox
    await client.click(alpha, f"guild:invite:{pack(guild.guild_id)}")
    await client.say(alpha, "Cedar", reply_prompt=INVITE_PROMPT)
    assert any("convidou você" in text for _chat, text in client.sent_to_others)
    screen = await client.click(cedar, "guild:inbox")
    screen = await client.click(cedar, _button(screen, "Aceitar · 1"))
    assert "Membros · 3/5" in screen.text

    # promote, demote and a guarded kick
    bravo_id = (await client.service.my_guild(bravo)).viewer_character_id
    gid = pack(guild.guild_id)
    await client.click(alpha, f"guild:pro:{gid}:{pack(bravo_id)}")
    assert (await client.service.my_guild(bravo)).viewer_role is GuildRole.OFFICER
    await client.click(alpha, f"guild:dem:{gid}:{pack(bravo_id)}")
    assert (await client.service.my_guild(bravo)).viewer_role is GuildRole.MEMBER
    screen = await client.click(alpha, f"guild:kick:{gid}:{pack(bravo_id)}")
    assert "Expulsar Bravo" in screen.text
    assert await client.service.my_guild(bravo) is not None  # still only a confirmation
    await client.click(alpha, f"guild:kickok:{gid}:{pack(bravo_id)}")
    assert await client.service.my_guild(bravo) is None

    # the Leader cannot leave; transfer first, then the old Leader leaves
    await client.click(alpha, f"guild:leave:{gid}")
    assert await client.service.my_guild(alpha) is not None
    cedar_id = (await client.service.my_guild(cedar)).viewer_character_id
    await client.click(alpha, f"guild:leadok:{gid}:{pack(cedar_id)}")
    assert (await client.service.my_guild(cedar)).viewer_role is GuildRole.LEADER
    await client.click(alpha, f"guild:leaveok:{gid}")
    assert await client.service.my_guild(alpha) is None


@pytest.mark.asyncio
async def test_stale_or_foreign_guild_id_is_rejected_by_the_server(database):
    actors = await _seed_characters(database)
    alpha, bravo, cedar = actors["Alpha"], actors["Bravo"], actors["Cedar"]
    client = _Client(database)
    await client.service.create_guild(alpha, "Aurora", "AUR")
    other = await client.service.create_guild(bravo, "Brasa", "BRA")
    mine = await client.service.my_guild(alpha)

    # Alpha tries to act with Brasa's id: stale, and nothing changes
    screen = await client.click(alpha, f"guild:recr:o:{pack(other.guild_id)}")
    assert "Ação Expirada" in screen.text
    assert (await client.service.my_guild(bravo)).recruitment is Recruitment.CLOSED

    # a common Member cannot reach Leader/Officer actions even with the right id
    await client.service.set_recruitment(alpha, Recruitment.OPEN)
    app = await client.service.apply(cedar, mine.guild_id)
    await client.service.approve_application(alpha, app.application_id)
    await client.click(cedar, f"guild:recr:c:{pack(mine.guild_id)}")
    assert (await client.service.my_guild(alpha)).recruitment is Recruitment.OPEN
    assert "permissão" in error_text("no_permission")

    # a malformed token does not crash the handler
    screen = await client.click(alpha, "guild:kick:xx:yy")
    assert "Ação Expirada" in screen.text
