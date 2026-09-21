"""aiogram adapters. Identity is always from Telegram's authenticated sender."""

from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message, Update

from asterion.application.creation import CreationService
from asterion.application.prologue import PrologueService
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import CreationCallback, Screen, render


def unavailable_media(exc: TelegramBadRequest) -> bool:
    return any(
        fragment in exc.message.lower()
        for fragment in (
            "wrong file identifier",
            "wrong remote file identifier",
            "file_id_invalid",
        )
    )


async def present(message: Message, screen: Screen, images: dict[str, str], *, edit=False):
    image = images.get(screen.image_key)
    if image and image.startswith("file:"):
        path = Path(image.removeprefix("file:"))
        media = FSInputFile(path) if path.is_file() else None
    else:
        media = image
    if edit:
        try:
            if media:
                await message.edit_media(
                    InputMediaPhoto(media=media, caption=screen.text, parse_mode=screen.parse_mode),
                    reply_markup=screen.keyboard,
                )
                return
            if not message.photo:
                await message.edit_text(
                    screen.text,
                    reply_markup=screen.keyboard,
                    parse_mode=screen.parse_mode,
                )
                return
        except TelegramBadRequest as exc:
            reason = exc.message.lower()
            if "message is not modified" in reason:
                return
            if media and unavailable_media(exc):
                media = None
            elif not any(
                fragment in reason
                for fragment in (
                    "message to edit not found",
                    "message can't be edited",
                    "message_id_invalid",
                )
            ):
                raise
    # A missing/deleted/uneditable message cannot invalidate committed game state.
    if media:
        try:
            await message.answer_photo(
                media,
                caption=screen.text,
                reply_markup=screen.keyboard,
                parse_mode=screen.parse_mode,
            )
            return
        except TelegramBadRequest as exc:
            if not unavailable_media(exc):
                raise
    await message.answer(screen.text, reply_markup=screen.keyboard, parse_mode=screen.parse_mode)


def creation_router(
    service: CreationService,
    images: dict[str, str],
    prologue: PrologueService | None = None,
) -> Router:
    router = Router(name="character_creation")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def current_screen(actor, state):
        if prologue is not None:
            view = await prologue.resume(actor)
            if view is not None:
                return render_combat(view)
        return render(state)

    @router.message(CommandStart())
    async def start(message: Message):
        if message.from_user:
            state = await service.start(message.from_user.id)
            await present(message, await current_screen(message.from_user.id, state), images)

    @router.callback_query(F.data.startswith("cc:"))
    async def callback(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            data = CreationCallback.unpack(query.data or "")
            draft_id = data.draft_id
        except (ValueError, TypeError):
            await query.answer()
            return
        state = await service.callback(query.from_user.id, draft_id, data.version, data.action)
        await query.answer()
        if state is not None:
            await present(
                query.message, await current_screen(query.from_user.id, state), images, edit=True
            )

    @router.message(F.text, ~F.text.startswith("/"))
    async def name(message: Message, event_update: Update):
        if message.from_user:
            state = await service.name(
                message.from_user.id,
                message.text or "",
                event_update.update_id,
            )
            await present(message, await current_screen(message.from_user.id, state), images)

    return router
