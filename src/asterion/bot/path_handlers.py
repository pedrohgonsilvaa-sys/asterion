"""Callbacks for authoritative Path selection and safe-location changes."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.class_trials import ClassTrialService
from asterion.application.path_selection import (
    PathMutationRejected,
    PathSelectionService,
)
from asterion.bot.creation_handlers import present
from asterion.bot.path_ui import (
    render_path_choices,
    render_path_detail,
    render_path_exchange,
    render_path_preview,
    render_path_root,
)
from asterion.domain.paths import path_belongs_to_class


def _version(value: str) -> int:
    return int(value, 36)


def _decode(data: str) -> tuple[str, str | None, int | None]:
    parts = data.split(":")
    if parts == ["path", "root"]:
        return "root", None, None
    if parts == ["path", "choose"]:
        return "choose", None, None
    if len(parts) == 4 and parts[0] == "path" and parts[1] in {
        "preview",
        "confirm",
        "detail",
        "swap",
        "swapconfirm",
    }:
        return parts[1], parts[2], _version(parts[3])
    raise ValueError("Invalid Path callback.")


def path_router(
    paths: PathSelectionService,
    trials: ClassTrialService,
    images: dict[str, str],
) -> Router:
    router = Router(name="character_paths")
    router.callback_query.filter(F.message.chat.type == "private")

    async def present_root(query: CallbackQuery, actor: int) -> None:
        view = await paths.view(actor)
        if view is None or not isinstance(query.message, Message):
            return
        trial = await trials.resume(actor)
        await present(
            query.message,
            render_path_root(view, trial),
            images,
            edit=True,
        )

    @router.callback_query(F.data == "character:path")
    async def open_path(query: CallbackQuery) -> None:
        await query.answer()
        await present_root(query, query.from_user.id)

    @router.callback_query(F.data.startswith("path:"))
    async def path_action(query: CallbackQuery) -> None:
        data = query.data or ""
        actor = query.from_user.id
        try:
            action, path_id, expected_version = _decode(data)
        except (TypeError, ValueError):
            await query.answer("A tela foi atualizada.")
            await present_root(query, actor)
            return

        view = await paths.view(actor)
        if view is None or not isinstance(query.message, Message):
            await query.answer()
            return

        if action == "root":
            trial = await trials.resume(actor)
            screen = render_path_root(view, trial)
        elif action == "choose":
            if view.trial_completed and view.selected_path is None:
                screen = render_path_choices(view)
            else:
                screen = render_path_root(view, await trials.resume(actor))
        elif action in {"preview", "confirm"}:
            if (
                expected_version != view.configuration_version
                or path_id is None
                or not view.trial_completed
                or view.selected_path is not None
                or not path_belongs_to_class(path_id, view.character_class)
            ):
                await query.answer("A tela foi atualizada.")
                await present_root(query, actor)
                return
            if action == "preview":
                screen = render_path_preview(view, path_id)
            else:
                try:
                    await paths.choose_initial(actor, path_id, expected_version)
                except PathMutationRejected:
                    await query.answer("A escolha foi atualizada.")
                    await present_root(query, actor)
                    return
                await query.answer()
                await present_root(query, actor)
                return
        elif action in {"detail", "swap", "swapconfirm"}:
            if (
                expected_version != view.configuration_version
                or path_id is None
                or not view.trial_completed
                or view.selected_path is None
                or not path_belongs_to_class(path_id, view.character_class)
            ):
                await query.answer("A tela foi atualizada.")
                await present_root(query, actor)
                return
            if action == "detail":
                screen = render_path_detail(view, path_id)
            elif action == "swap":
                if path_id == view.selected_path:
                    screen = render_path_detail(view, path_id)
                else:
                    count = await paths.incompatible_art_count(actor, path_id)
                    screen = render_path_exchange(view, path_id, count or 0)
            else:
                try:
                    await paths.exchange(actor, path_id, expected_version)
                except PathMutationRejected:
                    await query.answer("A troca foi atualizada.")
                    await present_root(query, actor)
                    return
                await query.answer()
                await present_root(query, actor)
                return
        else:
            await query.answer("A tela foi atualizada.")
            await present_root(query, actor)
            return

        await query.answer()
        await present(query.message, screen, images, edit=True)

    return router
