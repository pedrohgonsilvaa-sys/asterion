from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import CallbackQuery, Message

from asterion.application.groups import GroupError
from asterion.application.p1 import P1Service
from asterion.bot.combat_ui import CampaignCombatCallback, CombatCallback, P1CombatCallback
from asterion.bot.creation_handlers import present
from asterion.bot.p1_ui import render_p1


def p1_router(
    service: P1Service,
    images: dict[str, str],
    *,
    p2=None,
    p5=None,
    p6=None,
    s6=None,
) -> Router:
    router = Router(name="p1")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query, view):
        await query.answer()
        if view is not None and isinstance(query.message, Message):
            await present(query.message, render_p1(view), images, edit=True)

    @router.callback_query(F.data.startswith("p1fight:"))
    async def fight(query: CallbackQuery):
        try:
            cb = P1CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await service.action(query.from_user.id, cb.activity_id, cb.version, cb.action)
        await show(query, view)

    @router.callback_query(F.data.startswith("cc:"))
    async def campaign_fight(query: CallbackQuery):
        try:
            cb = CampaignCombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        candidates = (service, p2, p5, p6, s6)
        renderers = {
            "p1": render_p1,
        }
        for candidate in candidates:
            if candidate is None:
                continue
            view = await candidate.campaign_action(
                query.from_user.id,
                cb.activity_id,
                cb.combat_version,
                cb.action_index,
                cb.target,
            )
            if view is None:
                continue
            if getattr(view, "context", None) == "p2":
                from asterion.bot.p2_ui import render_p2

                screen = render_p2(view)
            elif getattr(view, "context", None) == "p5":
                from asterion.bot.p5_ui import render_p5

                screen = render_p5(view)
            elif getattr(view, "context", None) == "p6":
                from asterion.bot.p6_ui import render_p6

                screen = render_p6(view)
            elif getattr(view, "context", None) == "s6":
                from asterion.bot.s6_ui import render_s6

                screen = render_s6(view)
            else:
                screen = renderers["p1"](view)
            await query.answer()
            if isinstance(query.message, Message):
                await present(query.message, screen, images, edit=True)
            return
        await query.answer()

    @router.callback_query(F.data.startswith("fight:"))
    async def shared_fight(query: CallbackQuery):
        """Route legacy fight callbacks to P1 only when their activity is P1."""
        try:
            cb = CombatCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            return
        view = await service.action(query.from_user.id, cb.activity_id, cb.version, cb.action)
        if view is None:
            raise SkipHandler()
        await show(query, view)

    @router.callback_query(F.data.startswith("p1:"))
    async def mutate(query: CallbackQuery):
        parts = query.data.split(":")
        if len(parts) < 3:
            await query.answer()
            return
        try:
            version = int(parts[1])
        except ValueError:
            await query.answer()
            return
        action = parts[2]
        actor = query.from_user.id
        if action == "follow":
            view = await service.follow_road(actor, version)
        elif action == "solo":
            view = await service.start_solo_combat(actor, version)
        elif action == "group":
            try:
                view = await service.propose_group_combat(actor, version)
            except GroupError:
                await query.answer(
                    "Não foi possível preparar o Grupo. Atualize a tela.", show_alert=True
                )
                return
        elif action == "examine" and len(parts) == 4:
            view = await service.examine(actor, parts[3], version)
        elif action == "retry":
            view = await service.retry(actor, version)
        elif action == "refuge":
            view = await service.enter_refuge(actor, version)
        elif action == "alda":
            view = await service.follow_alda(actor, version)
        elif action == "oren":
            view = await service.go_brazier(actor, version)
        elif action == "activate":
            view = await service.activate_brazier(actor, version)
        else:
            view = await service.resume(actor)
        await show(query, view)

    return router
