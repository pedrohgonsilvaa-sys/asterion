"""Telegram routes for saved, reference-based combat configurations."""

from uuid import UUID

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import CallbackQuery, ForceReply, Message

from asterion.application.doctrines import (
    MAX_DOCTRINE_NAME_CHARACTERS,
    DoctrineRejected,
    DoctrineService,
)
from asterion.bot.creation_handlers import present
from asterion.bot.doctrines_ui import (
    render_apply_preview,
    render_art_choices,
    render_art_slots,
    render_delete_confirmation,
    render_doctrine_detail,
    render_doctrine_root,
    render_editor,
    render_equipment_choices,
    render_equipment_slots,
    render_overwrite_preview,
    render_paths,
    render_talent_choices,
    render_talent_slots,
)
from asterion.domain.arts import ART_IDS_BY_CLASS
from asterion.domain.economy import crowns_per_level, path_switch_cost
from asterion.domain.equipment import assignment_for_item_slot
from asterion.domain.paths import PATHS_BY_CLASS
from asterion.domain.talents import TALENTS_BY_CLASS

DOCTRINE_PROMPT = "Responda a esta mensagem com o nome da Doutrina."


def _from36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid version")
    return int(value, 36)


def _uuid(value: str) -> UUID:
    return UUID(hex=value)


def doctrines_router(service: DoctrineService, images: dict[str, str]) -> Router:
    router = Router(name="character_doctrines")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def current_view(query):
        return await service.view(query.from_user.id)

    async def show_root(query, *, alert: str | None = None):
        if not isinstance(query.message, Message):
            return
        view = await current_view(query)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if alert:
            await query.answer(alert, show_alert=True)
        await present(query.message, render_doctrine_root(view), images, edit=True)

    async def show_detail(query, doctrine_id: UUID, *, expected_revision: int | None = None):
        if not isinstance(query.message, Message):
            return None
        view = await current_view(query)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return None
        doctrine = next((item for item in view.doctrines if item.doctrine_id == doctrine_id), None)
        if doctrine is None or (
            expected_revision is not None and doctrine.revision != expected_revision
        ):
            await query.answer("A Doutrina foi atualizada.", show_alert=True)
            await present(query.message, render_doctrine_root(view), images, edit=True)
            return None
        await present(query.message, render_doctrine_detail(view, doctrine), images, edit=True)
        return view, doctrine

    async def show_editor(query, doctrine_id, expected_revision):
        result = await show_detail(query, doctrine_id, expected_revision=expected_revision)
        if result is None or not isinstance(query.message, Message):
            return
        view, doctrine = result
        await present(query.message, render_editor(view, doctrine), images, edit=True)

    async def start_name_prompt(query, action, config_version, doctrine_id=None, revision=0):
        if not isinstance(query.message, Message):
            return
        view = await current_view(query)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if view.foreground:
            await query.answer("Configuração bloqueada durante atividade.", show_alert=True)
            return
        prompt = await query.message.answer(
            f"{DOCTRINE_PROMPT} Limite técnico de {MAX_DOCTRINE_NAME_CHARACTERS} caracteres.",
            reply_markup=ForceReply(selective=True, input_field_placeholder="Nome da Doutrina"),
            parse_mode=None,
        )
        try:
            started = await service.begin_name_input(
                query.from_user.id,
                action,
                prompt.message_id,
                config_version,
                doctrine_id=doctrine_id,
                expected_revision=revision,
            )
        except DoctrineRejected:
            started = False
        if not started:
            await prompt.edit_text("A tela foi atualizada. Abra Doutrinas para tentar novamente.")
            await show_root(query)
            await query.answer("A tela foi atualizada.", show_alert=True)
        else:
            await query.answer("Envie o nome em resposta à solicitação.")

    @router.callback_query(F.data == "character:doctrines")
    async def open_root(query: CallbackQuery):
        await query.answer()
        await show_root(query)

    @router.callback_query(F.data.startswith("doc:"))
    async def navigate(query: CallbackQuery):
        parts = (query.data or "").split(":")
        try:
            if parts == ["doc", "r"]:
                await query.answer()
                await show_root(query)
                return
            if len(parts) == 3 and parts[1] == "n":
                await start_name_prompt(query, "create", _from36(parts[2]))
                return
            if len(parts) < 3:
                raise ValueError
            doctrine_id = _uuid(parts[2]) if parts[1] not in {"r"} else None
            if parts[1] == "d" and len(parts) == 4:
                await query.answer()
                await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                return
            if parts[1] == "ed" and len(parts) == 5:
                await query.answer()
                await show_editor(query, doctrine_id, _from36(parts[3]))
                return
            if parts[1] == "nm" and len(parts) == 5:
                await start_name_prompt(
                    query, "rename", _from36(parts[4]), doctrine_id, _from36(parts[3])
                )
                return
            if parts[1] == "ep" and len(parts) == 5:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    view, doctrine = result
                    await present(
                        query.message,
                        render_paths(view, doctrine, PATHS_BY_CLASS[view.character_class]),
                        images,
                        edit=True,
                    )
                    await query.answer()
                return
            if parts[1] == "p" and len(parts) == 6:
                revision, config_version, index = (
                    _from36(parts[3]),
                    _from36(parts[4]),
                    _from36(parts[5]),
                )
                result = await show_detail(query, doctrine_id, expected_revision=revision)
                if not result:
                    return
                view, doctrine = result
                options = PATHS_BY_CLASS[view.character_class]
                if index > len(options):
                    raise ValueError
                path = None if index == 0 else options[index - 1]
                await service.update_component(
                    query.from_user.id, doctrine_id, revision, config_version, "path", path
                )
                await query.answer("Caminho salvo.")
                await show_detail(query, doctrine_id)
                return
            if parts[1] == "es" and len(parts) == 5:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    await present(query.message, render_equipment_slots(*result), images, edit=True)
                    await query.answer()
                return
            if parts[1] == "eq" and len(parts) == 6:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if not result:
                    return
                view, doctrine = result
                slot_index = _from36(parts[5])
                await present(
                    query.message,
                    render_equipment_choices(
                        view,
                        doctrine,
                        slot_index,
                        await service.owned_equipment(query.from_user.id) or (),
                    ),
                    images,
                    edit=True,
                )
                await query.answer()
                return
            if parts[1] == "ei" and len(parts) == 7:
                revision, config_version = _from36(parts[3]), _from36(parts[4])
                slot_index = _from36(parts[5])
                result = await show_detail(query, doctrine_id, expected_revision=revision)
                if not result:
                    return
                view, doctrine = result
                labels = (
                    "Principal",
                    "Secundária",
                    "Cabeça",
                    "Torso",
                    "Mãos",
                    "Pés",
                    "Acessório",
                    "Artefato",
                )
                if slot_index >= len(labels):
                    raise ValueError
                slot = labels[slot_index]
                token = parts[6]
                selected = None
                if token != "x":
                    candidates = []
                    for item in await service.owned_equipment(query.from_user.id) or ():
                        assignment = assignment_for_item_slot(item[2])
                        if assignment and assignment.slot.value == slot:
                            candidates.append(item)
                    index = _from36(token)
                    if index >= len(candidates):
                        raise ValueError
                    selected = candidates[index][0]
                mutation = await service.update_component(
                    query.from_user.id,
                    doctrine_id,
                    revision,
                    config_version,
                    "equipment",
                    (slot, selected),
                )
                await query.answer("Equipamento salvo.")
                await show_editor(
                    query,
                    doctrine_id,
                    revision + (1 if mutation is not None and mutation.changed else 0),
                )
                return
            if parts[1] == "as" and len(parts) == 5:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    await present(query.message, render_art_slots(*result), images, edit=True)
                    await query.answer()
                return
            if parts[1] == "al" and len(parts) == 6:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if not result:
                    return
                view, doctrine = result
                slot = _from36(parts[5])
                if slot not in {1, 2, 3}:
                    raise ValueError
                await present(
                    query.message, render_art_choices(view, doctrine, slot), images, edit=True
                )
                await query.answer()
                return
            if parts[1] == "ai" and len(parts) == 7:
                revision, config_version, slot = (
                    _from36(parts[3]),
                    _from36(parts[4]),
                    _from36(parts[5]),
                )
                result = await show_detail(query, doctrine_id, expected_revision=revision)
                if not result:
                    return
                view, doctrine = result
                token = parts[6]
                art_id = None
                if token != "x":
                    arts = ART_IDS_BY_CLASS[view.character_class]
                    index = _from36(token)
                    if index >= len(arts):
                        raise ValueError
                    art_id = arts[index]
                mutation = await service.update_component(
                    query.from_user.id,
                    doctrine_id,
                    revision,
                    config_version,
                    "arts",
                    (slot, art_id),
                )
                await query.answer("Artes salvas.")
                await show_editor(
                    query,
                    doctrine_id,
                    revision + (1 if mutation is not None and mutation.changed else 0),
                )
                return
            if parts[1] == "ts" and len(parts) == 5:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    await present(query.message, render_talent_slots(*result), images, edit=True)
                    await query.answer()
                return
            if parts[1] == "tl" and len(parts) == 6:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if not result:
                    return
                view, doctrine = result
                slot = _from36(parts[5])
                await present(
                    query.message, render_talent_choices(view, doctrine, slot), images, edit=True
                )
                await query.answer()
                return
            if parts[1] == "ti" and len(parts) == 7:
                revision, config_version, point_slot = (
                    _from36(parts[3]),
                    _from36(parts[4]),
                    _from36(parts[5]),
                )
                result = await show_detail(query, doctrine_id, expected_revision=revision)
                if not result:
                    return
                view, doctrine = result
                values = list(doctrine.configuration["talents"])
                token = parts[6]
                if token == "x":
                    values = [item for item in values if item["point_slot"] != point_slot]
                else:
                    options = TALENTS_BY_CLASS[view.character_class]
                    index = _from36(token)
                    if index >= len(options):
                        raise ValueError
                    selected = options[index]
                    values = [item for item in values if item["point_slot"] != point_slot]
                    values.append({"point_slot": point_slot, "talent_id": selected.talent_id})
                mutation = await service.update_component(
                    query.from_user.id, doctrine_id, revision, config_version, "talents", values
                )
                await query.answer("Talentos salvos.")
                await show_editor(
                    query,
                    doctrine_id,
                    revision + (1 if mutation is not None and mutation.changed else 0),
                )
                return
            if parts[1] == "ow" and len(parts) == 5:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    view, doctrine = result
                    await present(
                        query.message,
                        render_overwrite_preview(doctrine, _from36(parts[4])),
                        images,
                        edit=True,
                    )
                    await query.answer()
                return
            if parts[1] == "owok" and len(parts) == 5:
                mutation = await service.overwrite_current(
                    query.from_user.id, doctrine_id, _from36(parts[3]), _from36(parts[4])
                )
                await query.answer("Doutrina atualizada.")
                await show_detail(
                    query,
                    doctrine_id,
                    expected_revision=_from36(parts[3])
                    + (1 if mutation is not None and mutation.changed else 0),
                )
                return
            if parts[1] == "del" and len(parts) == 4:
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    await present(
                        query.message, render_delete_confirmation(result[1]), images, edit=True
                    )
                    await query.answer()
                return
            if parts[1] == "x" and len(parts) == 4:
                await service.delete(query.from_user.id, doctrine_id, _from36(parts[3]))
                await query.answer("Doutrina excluída.")
                await show_root(query)
                return
            if parts[1] == "ap" and len(parts) == 5:
                expected_configuration_version = _from36(parts[4])
                result = await show_detail(query, doctrine_id, expected_revision=_from36(parts[3]))
                if result:
                    view, doctrine = result
                    if view.configuration_version != expected_configuration_version:
                        await show_root(query, alert="A configuração mudou. Revise a Doutrina.")
                        return
                    target = doctrine.configuration
                    cost = 0
                    if target["path"] != view.selected_path and view.selected_path is not None:
                        cost += path_switch_cost(view.level)
                    current_talent_rows = view.current_configuration["talents"]
                    current_talent_pairs = {
                        (item["point_slot"], item["talent_id"]) for item in current_talent_rows
                    }
                    target_talent_pairs = {
                        (item["point_slot"], item["talent_id"])
                        for item in target["talents"]
                    }
                    if (
                        target_talent_pairs != current_talent_pairs
                        and not current_talent_pairs.issubset(target_talent_pairs)
                    ):
                        cost += 2 * crowns_per_level(view.level)
                    requires_review = cost > 0 or target["path"] != view.selected_path
                    if doctrine.can_apply and requires_review:
                        await present(
                            query.message,
                            render_apply_preview(view, doctrine, cost),
                            images,
                            edit=True,
                        )
                    elif doctrine.can_apply:
                        await service.apply(
                            query.from_user.id,
                            doctrine_id,
                            doctrine.revision,
                            expected_configuration_version,
                        )
                        await query.answer("Doutrina aplicada.")
                        await show_detail(
                            query, doctrine_id, expected_revision=doctrine.revision
                        )
                        return
                    else:
                        await present(
                            query.message, render_doctrine_detail(view, doctrine), images, edit=True
                        )
                    await query.answer()
                return
            if parts[1] == "ok" and len(parts) == 5:
                await service.apply(
                    query.from_user.id, doctrine_id, _from36(parts[3]), _from36(parts[4])
                )
                await query.answer("Doutrina aplicada.")
                await show_detail(query, doctrine_id)
                return
            if parts[1] == "ed" and len(parts) == 5:
                await query.answer()
                await show_editor(query, doctrine_id, _from36(parts[3]))
                return
        except (ValueError, DoctrineRejected):
            await show_root(
                query, alert="A Doutrina ou configuração mudou. Revise e tente novamente."
            )
            return
        await show_root(query, alert="A tela foi atualizada.")

    @router.message(F.text, F.reply_to_message)
    async def doctrine_name_reply(message: Message):
        if message.from_user is None or message.text is None:
            raise SkipHandler()
        prompt = message.reply_to_message
        if (
            prompt is None
            or prompt.from_user is None
            or not prompt.from_user.is_bot
            or not (prompt.text or "").startswith(DOCTRINE_PROMPT)
        ):
            raise SkipHandler()
        if message.text.startswith("/"):
            raise SkipHandler()
        try:
            await service.save_name_reply(message.from_user.id, prompt.message_id, message.text)
        except DoctrineRejected as exc:
            messages = {
                "invalid_name": "O nome deve ter de 1 a 40 caracteres.",
                "duplicate_name": "Já existe uma Doutrina com esse nome.",
                "stale_input": "Esta solicitação ficou desatualizada. Abra Doutrinas novamente.",
                "stale_configuration": "A configuração mudou. Abra Doutrinas novamente.",
                "stale_doctrine": "A Doutrina foi atualizada. Abra novamente.",
                "limit": "O limite de cinco Doutrinas foi atingido.",
                "foreground": "Não é possível alterar Doutrinas durante uma atividade.",
            }
            await message.answer(messages.get(exc.code, "Não foi possível salvar a Doutrina."))
            return
        view = await service.view(message.from_user.id)
        if view is not None:
            await present(message, render_doctrine_root(view), images)

    @router.message(F.text.startswith("/"))
    async def pass_commands(message: Message):
        raise SkipHandler()

    return router
