from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.class_trials import ClassTrialService
from asterion.bot.class_trial_ui import (
    ClassTrialPageCallback,
    render_class_trial_view,
    render_trial_targets,
)
from asterion.bot.combat_ui import (
    ClassTrialActionCallback,
    class_trial_action_ids,
    class_trial_target_ids,
)
from asterion.bot.creation_handlers import present


def class_trial_router(
    service: ClassTrialService, images: dict[str, str]
) -> Router:
    router = Router(name="class_trials")
    router.callback_query.filter(F.message.chat.type == "private")

    async def current_screen(actor: int):
        view = await service.resume(actor)
        if view is None:
            return None
        return view, await render_class_trial_view(service, actor, view)

    async def show_current(query: CallbackQuery, actor: int) -> None:
        current = await current_screen(actor)
        if current is None or not isinstance(query.message, Message):
            return
        _, screen = current
        await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("trial:"))
    async def page(query: CallbackQuery):
        try:
            callback = ClassTrialPageCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            await show_current(query, query.from_user.id)
            return

        if callback.action == "begin":
            view = await service.begin(query.from_user.id, callback.state_version)
        elif callback.action in {"start", "retry"}:
            view = await service.start_attempt(query.from_user.id, callback.state_version)
        elif callback.action == "circle":
            view = await service.return_to_circle(query.from_user.id, callback.state_version)
        elif callback.action == "resume":
            view = await service.resume(query.from_user.id)
            if view is not None and view.status == "ready" and view.context == "refuge":
                view = await service.return_to_circle(
                    query.from_user.id, callback.state_version
                )
        else:
            view = await service.resume(query.from_user.id)

        await query.answer()
        if view is not None and isinstance(query.message, Message):
            screen = await render_class_trial_view(service, query.from_user.id, view)
            await present(query.message, screen, images, edit=True)

    @router.callback_query(F.data.startswith("trialact:"))
    async def action(query: CallbackQuery):
        try:
            callback = ClassTrialActionCallback.unpack(query.data or "")
        except (KeyError, TypeError, ValueError):
            await query.answer()
            await show_current(query, query.from_user.id)
            return

        view = await service.resume(query.from_user.id)
        combat = (
            await service.combat(query.from_user.id, view.attempt_id)
            if view is not None
            and view.kind == "active"
            and view.attempt_id is not None
            else None
        )
        if (
            view is None
            or combat is None
            or view.attempt_id != callback.attempt_id
            or view.combat_version != callback.combat_version
            or combat.version != callback.combat_version
        ):
            await query.answer("A Provação foi atualizada.")
            if view is not None and isinstance(query.message, Message):
                screen = await render_class_trial_view(service, query.from_user.id, view)
                await present(query.message, screen, images, edit=True)
            return

        actions = class_trial_action_ids(combat)
        if not 0 <= callback.action_index < len(actions):
            await query.answer("A ação não está mais disponível.")
            if isinstance(query.message, Message):
                screen = await render_class_trial_view(service, query.from_user.id, view)
                await present(query.message, screen, images, edit=True)
            return

        action_id = actions[callback.action_index]
        target_ids = class_trial_target_ids(combat, action_id)
        if callback.target == "b":
            await query.answer()
            if isinstance(query.message, Message):
                screen = await render_class_trial_view(service, query.from_user.id, view)
                await present(query.message, screen, images, edit=True)
            return

        if callback.target == "s":
            if len(target_ids) > 1:
                await query.answer()
                if isinstance(query.message, Message):
                    await present(
                        query.message,
                        render_trial_targets(view, combat, callback.action_index),
                        images,
                        edit=True,
                    )
                return
            if len(target_ids) == 1:
                target_id = target_ids[0]
            else:
                await query.answer("Nenhum alvo válido.")
                if isinstance(query.message, Message):
                    screen = await render_class_trial_view(service, query.from_user.id, view)
                    await present(query.message, screen, images, edit=True)
                return
        elif callback.target == "x":
            if target_ids:
                await query.answer("Escolha um alvo válido.")
                if isinstance(query.message, Message):
                    await present(
                        query.message,
                        render_trial_targets(view, combat, callback.action_index),
                        images,
                        edit=True,
                    )
                return
            target_id = None
        elif callback.direct_target:
            try:
                target_index = callback.target_index
            except ValueError:
                target_index = None
            if (
                target_index is None
                or len(target_ids) != 1
                or target_index != 0
            ):
                await query.answer("A seleção de alvo foi atualizada.")
                if isinstance(query.message, Message):
                    screen = await render_class_trial_view(service, query.from_user.id, view)
                    await present(query.message, screen, images, edit=True)
                return
            target_id = target_ids[target_index]
        else:
            try:
                target_index = callback.target_index
            except ValueError:
                target_index = None
            if (
                target_index is None
                or target_index < 0
                or target_index >= len(target_ids)
            ):
                await query.answer("O alvo não está mais disponível.")
                if isinstance(query.message, Message):
                    screen = await render_class_trial_view(service, query.from_user.id, view)
                    await present(query.message, screen, images, edit=True)
                return
            if len(target_ids) <= 1:
                await query.answer("A seleção de alvo foi atualizada.")
                if isinstance(query.message, Message):
                    screen = await render_class_trial_view(service, query.from_user.id, view)
                    await present(query.message, screen, images, edit=True)
                return
            target_id = target_ids[target_index]

        updated = await service.action(
            query.from_user.id,
            callback.attempt_id,
            callback.combat_version,
            action_id,
            target_id=target_id,
        )
        await query.answer()
        if updated is not None and isinstance(query.message, Message):
            screen = await render_class_trial_view(service, query.from_user.id, updated)
            await present(query.message, screen, images, edit=True)

    return router
