"""Telegram callbacks for P2; every transition is delegated to P2Service."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from asterion.application.p2 import ASH_POINT_IDS, P2Service
from asterion.application.p4 import P4Service
from asterion.application.s3 import S3Service
from asterion.bot.creation_handlers import present
from asterion.bot.creation_ui import Screen
from asterion.bot.p2_ui import render_p2
from asterion.bot.p4_ui import render_p4
from asterion.bot.s3_ui import render_s3


def p2_router(
    service: P2Service,
    images: dict[str, str],
    s3: S3Service | None = None,
    p4: P4Service | None = None,
) -> Router:
    router = Router(name="p2")
    router.callback_query.filter(F.message.chat.type == "private")

    @router.callback_query(F.data.startswith("p2:"))
    async def callback(query: CallbackQuery):
        data = query.data or ""
        parts = data.split(":")
        actor = query.from_user.id
        view = None

        if data == "p2:alda":
            p4_view = await p4.alda(actor) if p4 is not None else None
            s3_view = await s3.alda(actor) if s3 is not None else None
            if p4_view is not None and (
                p4_view.status == "active" or p4_view.available
            ):
                screen = render_p4(p4_view)
                if s3_view is not None and (
                    s3_view.status == "active" or s3_view.available or s3_view.reacceptable
                ):
                    callback = "s3:detail" if s3_view.status == "active" else "s3:offer"
                    rows = list(screen.keyboard.inline_keyboard) if screen.keyboard else []
                    rows.insert(
                        max(0, len(rows) - 1),
                        [
                            InlineKeyboardButton(
                                text="Rastros sob os Galhos", callback_data=callback
                            )
                        ],
                    )
                    screen = Screen(
                        screen.text,
                        screen.image_key,
                        InlineKeyboardMarkup(inline_keyboard=rows),
                        screen.parse_mode,
                    )
                await query.answer()
                if isinstance(query.message, Message):
                    await present(query.message, screen, images, edit=True)
                return
            if s3_view is not None and (
                s3_view.status == "active" or s3_view.available or s3_view.reacceptable
            ):
                await query.answer()
                if isinstance(query.message, Message):
                    await present(query.message, render_s3(s3_view), images, edit=True)
                return
            view = await service.alda(actor)
        elif data == "p2:resume":
            view = await service.resume(actor)
            if view is None:
                view = await service.alda(actor)
        elif len(parts) >= 3:
            try:
                version = int(parts[1])
            except ValueError:
                version = None
            action = parts[2]
            if version is not None:
                if action == "accept" and len(parts) == 3:
                    view = await service.accept(actor, version)
                elif action == "travel" and len(parts) == 3:
                    view = await service.travel_to_charneca(actor, version)
                elif action == "ash" and len(parts) == 4:
                    point_id = parts[3]
                    if point_id in ASH_POINT_IDS:
                        view = await service.examine_ash_point(
                            actor, point_id, version
                        )
                elif action == "retry" and len(parts) == 3:
                    view = await service.return_to_charneca(actor, version)
                elif action == "stone" and len(parts) == 3:
                    view = await service.examine_pedra_marcada(actor, version)
                elif action == "refuge" and len(parts) == 3:
                    view = await service.return_to_refuge(actor, version)
                elif action == "oren" and len(parts) == 3:
                    view = await service.oren(actor, version)
                elif action == "report" and len(parts) == 3:
                    view = await service.report_to_alda(actor, version)

        if view is None:
            view = await service.resume(actor)
            if view is None and data not in {"p2:resume", "p2:alda"}:
                view = await service.alda(actor)

        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p2(view), images, edit=True)

    return router
