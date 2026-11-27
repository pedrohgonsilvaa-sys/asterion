"""Rotas de Doutrinas (especificação consolidada 2026-11-26, Parte II).

Selecionar uma Doutrina abre direto a Configuração; Editar abre direto cada parte.
O nome é digitado na própria tela (``text_prompt``): a resposta do jogador é apagada
e a mesma mensagem é editada, sem prompts antigos no chat.
"""

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.doctrines import (
    MAX_DOCTRINE_NAME_CHARACTERS,
    DoctrineRejected,
    DoctrineService,
)
from asterion.bot.creation_handlers import present
from asterion.bot.doctrines_ui import (
    EQUIPMENT_SLOT_LABELS,
    REASON_LABELS,
    TALENT_LEVELS,
    TALENT_LEVELS_PER_PAGE,
    available_talent_points,
    doctrine_art_ids,
    equipment_candidates,
    in_use_doctrine,
    render_apply_preview,
    render_art_choices,
    render_art_slots,
    render_doctrine_detail,
    render_doctrine_root,
    render_editor,
    render_equipment_choices,
    render_equipment_slots,
    render_name_prompt,
    render_talent_page,
)
from asterion.bot.text_prompt import (
    PROMPTS,
    HasPrompt,
    PendingPrompt,
    consume_reply,
    show_on_prompt,
)
from asterion.domain.economy import crowns_per_level, path_switch_cost
from asterion.domain.talents import TALENTS_BY_CLASS, talent_points_at_level

NAME_PROMPT_KIND = "doc:name"
NAME_ERRORS = {
    "invalid_name": f"⚠️ O nome deve ter de 1 a {MAX_DOCTRINE_NAME_CHARACTERS} caracteres.",
    "duplicate_name": "⚠️ Já existe uma Doutrina com esse nome.",
}
STALE_ERRORS = {
    "stale_input": "A solicitação ficou desatualizada. Abra Doutrinas novamente.",
    "stale_configuration": "A configuração mudou. Abra Doutrinas novamente.",
    "stale_doctrine": "A Doutrina foi atualizada. Abra novamente.",
    "limit": "O limite de Doutrinas foi atingido.",
    "foreground": "Não é possível alterar Doutrinas durante uma atividade.",
}


def _from36(value: str) -> int:
    if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
        raise ValueError("invalid version")
    return int(value, 36)


def _uuid(value: str) -> UUID:
    return UUID(hex=value)


def apply_cost(view, doctrine) -> int:
    """Coroas cobradas ao usar a Doutrina, pelas regras já existentes de troca (GDD)."""
    target = doctrine.configuration
    cost = 0
    if target["path"] != view.selected_path and view.selected_path is not None:
        cost += path_switch_cost(view.level)
    current_pairs = {
        (item["point_slot"], item["talent_id"]) for item in view.current_configuration["talents"]
    }
    target_pairs = {(item["point_slot"], item["talent_id"]) for item in target["talents"]}
    if target_pairs != current_pairs and not current_pairs.issubset(target_pairs):
        cost += 2 * crowns_per_level(view.level)
    return cost


def doctrines_router(service: DoctrineService, images: dict[str, str]) -> Router:
    router = Router(name="character_doctrines")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show(query: CallbackQuery, screen) -> None:
        if isinstance(query.message, Message):
            await present(query.message, screen, images, edit=True)

    async def show_root(
        query: CallbackQuery, *, alert: str | None = None, notice: str | None = None
    ) -> None:
        view = await service.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        await query.answer(alert or notice, show_alert=bool(alert))
        await show(query, render_doctrine_root(view))

    async def load(query: CallbackQuery, doctrine_id: UUID, expected_revision: int | None):
        """A Doutrina atual; com revisão desatualizada, volta à lista de Doutrinas."""
        view = await service.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return None
        doctrine = next((item for item in view.doctrines if item.doctrine_id == doctrine_id), None)
        if doctrine is None or (
            expected_revision is not None and doctrine.revision != expected_revision
        ):
            await query.answer("A Doutrina foi atualizada.", show_alert=True)
            await show(query, render_doctrine_root(view))
            return None
        return view, doctrine

    async def reload(query: CallbackQuery, doctrine_id: UUID):
        return await load(query, doctrine_id, None)

    async def open_name_prompt(query, action, config_version, back, doctrine_id=None, revision=0):
        if not isinstance(query.message, Message):
            return
        view = await service.view(query.from_user.id)
        if view is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            return
        if view.foreground:
            await query.answer(STALE_ERRORS["foreground"], show_alert=True)
            return
        try:
            started = await service.begin_name_input(
                query.from_user.id,
                action,
                query.message.message_id,
                config_version,
                doctrine_id=doctrine_id,
                expected_revision=revision,
            )
        except DoctrineRejected as exc:
            await show_root(query, alert=STALE_ERRORS.get(exc.code, "A tela foi atualizada."))
            return
        if not started:
            await show_root(query, alert="A tela foi atualizada.")
            return
        await query.answer()
        await show(query, render_name_prompt(back))
        PROMPTS.open(query.from_user.id, NAME_PROMPT_KIND, query.message, {"back": back})

    async def toggle_talent(query, doctrine_id, revision, config_version, index) -> None:
        result = await load(query, doctrine_id, revision)
        if result is None:
            return
        view, doctrine = result
        options = TALENTS_BY_CLASS[view.character_class]
        if index >= len(options):
            raise ValueError
        talent = options[index]
        values = list(doctrine.configuration["talents"])
        if any(item["talent_id"] == talent.talent_id for item in values):
            values = [item for item in values if item["talent_id"] != talent.talent_id]
        else:
            if talent.level > view.level:
                raise ValueError
            if available_talent_points(view, doctrine) <= 0:
                await query.answer(REASON_LABELS["talent_points"], show_alert=True)
                return
            used = {item["point_slot"] for item in values}
            free = next(
                slot
                for slot in range(1, talent_points_at_level(view.level) + 1)
                if slot not in used
            )
            values.append({"point_slot": free, "talent_id": talent.talent_id})
        await service.update_component(
            query.from_user.id, doctrine_id, revision, config_version, "talents", values
        )
        page = TALENT_LEVELS.index(talent.level) // TALENT_LEVELS_PER_PAGE
        result = await reload(query, doctrine_id)
        if result:
            await query.answer()
            await show(query, render_talent_page(*result, page))

    async def use(query, doctrine_id, revision, config_version, *, confirmed: bool) -> None:
        result = await load(query, doctrine_id, revision)
        if result is None:
            return
        view, doctrine = result
        if view.configuration_version != config_version:
            await show_root(query, alert="A configuração mudou. Revise a Doutrina.")
            return
        current = in_use_doctrine(view)
        if current is not None and current.doctrine_id == doctrine.doctrine_id:
            await query.answer("Esta Doutrina já está em uso.")
            return
        if not doctrine.can_apply:
            reason = doctrine.incomplete_reason or ("foreground" if view.foreground else None)
            await query.answer(
                REASON_LABELS.get(reason, "A Doutrina não pode ser usada agora."),
                show_alert=True,
            )
            return
        cost = apply_cost(view, doctrine)
        if cost and not confirmed:
            await query.answer()
            await show(query, render_apply_preview(view, doctrine, cost))
            return
        await service.apply(query.from_user.id, doctrine_id, revision, config_version)
        await show_root(query, notice="Doutrina em uso.")

    @router.callback_query(F.data == "character:doctrines")
    async def open_root(query: CallbackQuery):
        await show_root(query)

    @router.callback_query(F.data.startswith("doc:"))
    async def navigate(query: CallbackQuery):
        parts = (query.data or "").split(":")
        action = parts[1] if len(parts) > 1 else ""
        try:
            if parts == ["doc", "r"]:
                await show_root(query)
                return
            if action == "n" and len(parts) == 3:
                await open_name_prompt(query, "create", _from36(parts[2]), "doc:r")
                return
            if len(parts) < 4:
                raise ValueError
            doctrine_id, revision = _uuid(parts[2]), _from36(parts[3])
            if action == "d" and len(parts) == 4:
                result = await load(query, doctrine_id, revision)
                if result:
                    await query.answer()
                    await show(query, render_doctrine_detail(*result))
                return
            if action == "x" and len(parts) == 4:
                await service.delete(query.from_user.id, doctrine_id, revision)
                await show_root(query, notice="Doutrina excluída.")
                return
            if len(parts) < 5:
                raise ValueError
            config_version = _from36(parts[4])
            keys = ":".join(parts[2:5])
            if action in {"u", "ok"} and len(parts) == 5:
                await use(query, doctrine_id, revision, config_version, confirmed=action == "ok")
                return
            if action == "nm" and len(parts) == 5:
                await open_name_prompt(
                    query, "rename", config_version, f"doc:ed:{keys}", doctrine_id, revision
                )
                return
            if action == "tt" and len(parts) == 6:
                await toggle_talent(
                    query, doctrine_id, revision, config_version, _from36(parts[5])
                )
                return
            result = await load(query, doctrine_id, revision)
            if result is None:
                return
            view, doctrine = result
            if action == "ed" and len(parts) == 5:
                screen = render_editor(view, doctrine)
            elif action == "es" and len(parts) == 5:
                screen = render_equipment_slots(view, doctrine)
            elif action == "as" and len(parts) == 5:
                screen = render_art_slots(view, doctrine)
            elif action == "ts" and len(parts) == 6:
                screen = render_talent_page(view, doctrine, _from36(parts[5]))
            elif action == "eq" and len(parts) == 6:
                slot_index = _from36(parts[5])
                if slot_index >= len(EQUIPMENT_SLOT_LABELS):
                    raise ValueError
                owned = await service.owned_equipment(query.from_user.id) or ()
                screen = render_equipment_choices(view, doctrine, slot_index, owned)
            elif action == "ei" and len(parts) == 7:
                slot_index = _from36(parts[5])
                if slot_index >= len(EQUIPMENT_SLOT_LABELS):
                    raise ValueError
                selected = None
                if parts[6] != "x":
                    owned = await service.owned_equipment(query.from_user.id) or ()
                    candidates = equipment_candidates(owned, slot_index)
                    index = _from36(parts[6])
                    if index >= len(candidates):
                        raise ValueError
                    selected = candidates[index][0]
                await service.update_component(
                    query.from_user.id,
                    doctrine_id,
                    revision,
                    config_version,
                    "equipment",
                    (EQUIPMENT_SLOT_LABELS[slot_index], selected),
                )
                result = await reload(query, doctrine_id)
                if result is None:
                    return
                screen = render_equipment_slots(*result)
            elif action == "al" and len(parts) == 7:
                slot = _from36(parts[5])
                if slot not in {1, 2, 3}:
                    raise ValueError
                screen = render_art_choices(view, doctrine, slot, _from36(parts[6]))
            elif action == "ai" and len(parts) == 7:
                slot = _from36(parts[5])
                if slot not in {1, 2, 3}:
                    raise ValueError
                art_id = None
                if parts[6] != "x":
                    arts = doctrine_art_ids(view, doctrine)
                    index = _from36(parts[6])
                    if index >= len(arts):
                        raise ValueError
                    art_id = arts[index]
                await service.update_component(
                    query.from_user.id,
                    doctrine_id,
                    revision,
                    config_version,
                    "arts",
                    (slot, art_id),
                )
                result = await reload(query, doctrine_id)
                if result is None:
                    return
                screen = render_art_slots(*result)
            else:
                raise ValueError
            await query.answer()
            await show(query, screen)
        except DoctrineRejected as exc:
            message = REASON_LABELS.get(exc.code) or STALE_ERRORS.get(
                exc.code, "A Doutrina ou configuração mudou. Revise e tente novamente."
            )
            await show_root(query, alert=message)
        except ValueError:
            await show_root(query, alert="A tela foi atualizada.")

    @router.message(F.text, HasPrompt(NAME_PROMPT_KIND))
    async def doctrine_name(message: Message, prompt: PendingPrompt):
        actor = message.from_user.id
        await consume_reply(message)
        back = prompt.data.get("back", "doc:r")
        try:
            mutation = await service.save_name_reply(actor, prompt.message_id, message.text or "")
        except DoctrineRejected as exc:
            if exc.code in NAME_ERRORS:
                # O pedido continua aberto na mesma tela, com o aviso.
                await show_on_prompt(
                    message, prompt, render_name_prompt(back, NAME_ERRORS[exc.code]), images
                )
                PROMPTS.follow(actor, prompt)
                return
            PROMPTS.close(actor)
            view = await service.view(actor)
            if view is not None:
                await show_on_prompt(message, prompt, render_doctrine_root(view), images)
            return
        PROMPTS.close(actor)
        view = await service.view(actor)
        if view is None:
            return
        doctrine = next(
            (
                item
                for item in view.doctrines
                if mutation is not None and item.doctrine_id == mutation.doctrine_id
            ),
            None,
        )
        if back != "doc:r" and doctrine is not None:
            screen = render_editor(view, doctrine)
        else:
            screen = render_doctrine_root(view)
        await show_on_prompt(message, prompt, screen, images)

    return router
