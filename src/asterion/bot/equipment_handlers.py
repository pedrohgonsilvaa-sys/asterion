"""Telegram callbacks for the player-facing Equipment flow."""

from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment import (
    EquipmentMutationCode,
    EquipmentMutationRejected,
    EquipmentService,
)
from asterion.application.equipment_view import (
    EquipmentViewService,
    EquipmentViewUnavailable,
)
from asterion.application.inventory import InventoryService
from asterion.application.p1 import P1Service
from asterion.application.road import RoadService
from asterion.bot.character_ui import render_character
from asterion.bot.creation_handlers import present
from asterion.bot.equipment_ui import (
    CODE_SLOTS,
    render_equipment_candidates,
    render_equipment_detail,
    render_equipment_root,
)
from asterion.bot.p1_ui import render_p1
from asterion.bot.road_ui import render_road

ERROR_COPY = {
    EquipmentMutationCode.ITEM_UNAVAILABLE: "Equipamento indisponível.",
    EquipmentMutationCode.INVALID_ITEM: "Equipamento incompatível.",
    EquipmentMutationCode.INVALID_SLOT: "Slot indisponível.",
    EquipmentMutationCode.ITEM_LEVEL_REQUIRED: "Nível insuficiente para equipar.",
    EquipmentMutationCode.SECONDARY_BLOCKED_BY_TWO_HANDED: (
        "Secundária bloqueada por arma de 2 mãos."
    ),
    EquipmentMutationCode.ITEM_EQUIPPED_IN_OTHER_SLOT: "Equipamento já está em uso.",
    EquipmentMutationCode.MYTHIC_LIMIT: "Limite de Mítico equipado atingido.",
    EquipmentMutationCode.WEAPON_UNMAPPED: "Arma sem identidade registrada.",
    EquipmentMutationCode.WEAPON_PROFICIENCY_REQUIRED: (
        "Requer a Proficiência desta arma (Treinador de Armas, no Refúgio)."
    ),
    EquipmentMutationCode.WEAPON_CLASS_FORBIDDEN: "Sua Classe não pode usar esta arma.",
    EquipmentMutationCode.STALE_CONFIGURATION: "Configuração atualizada.",
    EquipmentMutationCode.INVALID_CURRENT_CONFIGURATION: (
        "Não foi possível atualizar os Equipamentos."
    ),
}
LOCKED_COPY = "Equipamentos não podem ser alterados durante esta atividade."


def equipment_router(
    read_service: EquipmentViewService,
    equipment_service: EquipmentService,
    inventory: InventoryService,
    images: dict[str, str],
    *,
    p1: P1Service | None = None,
    road: RoadService | None = None,
) -> Router:
    router = Router(name="character_equipment")
    router.callback_query.filter(F.message.chat.type == "private")

    async def _foreground(query: CallbackQuery) -> bool:
        if road is not None:
            road_view = await road.resume(query.from_user.id)
            if road_view is not None and (
                road_view.kind in {"combat", "exploration"}
                or road_view.kind.startswith("round_")
            ):
                if isinstance(query.message, Message):
                    await present(query.message, render_road(road_view), images, edit=True)
                return True
        if p1 is not None:
            p1_view = await p1.resume(query.from_user.id)
            if p1_view is not None and p1_view.combat is not None:
                if isinstance(query.message, Message):
                    await present(query.message, render_p1(p1_view), images, edit=True)
                return True
        return False

    async def _root(query: CallbackQuery) -> None:
        if not isinstance(query.message, Message):
            return
        try:
            view = await read_service.root(query.from_user.id)
        except EquipmentViewUnavailable:
            return
        if view is not None:
            await present(query.message, render_equipment_root(view), images, edit=True)

    async def _refresh_after_mutation(
        query: CallbackQuery, context: str, item_id: UUID | None
    ) -> None:
        if not isinstance(query.message, Message):
            return
        if context == "i" and item_id is not None:
            try:
                detail = await read_service.detail(query.from_user.id, item_id)
            except EquipmentViewUnavailable:
                detail = None
            if detail is not None:
                await present(
                    query.message,
                    render_equipment_detail(detail, context="i"),
                    images,
                    edit=True,
                )
                return
            category = await inventory.category(query.from_user.id, "equipment")
            if category is not None:
                from asterion.bot.inventory_ui import render_inventory

                await present(query.message, render_inventory(category), images, edit=True)
                return
        await _root(query)

    async def _handle_rejection(
        query: CallbackQuery,
        code: EquipmentMutationCode,
        context: str,
        item_id: UUID | None,
    ) -> None:
        text = ERROR_COPY[code]
        await query.answer(text, show_alert=True)
        if code == EquipmentMutationCode.STALE_CONFIGURATION and await _foreground(query):
            return
        await _refresh_after_mutation(query, context, item_id)

    @router.callback_query(F.data == "character:root")
    async def character_root(query: CallbackQuery):
        if await _foreground(query):
            await query.answer()
            return
        await query.answer()
        if isinstance(query.message, Message):
            await present(query.message, render_character(), images, edit=True)

    @router.callback_query(F.data == "eq:r")
    async def equipment_root(query: CallbackQuery):
        if await _foreground(query):
            await query.answer()
            return
        await query.answer()
        await _root(query)

    @router.callback_query(F.data.startswith("eq:s:"))
    async def equipment_slot(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            _, _, code, expected_raw = (query.data or "").split(":")
            slot = CODE_SLOTS[code]
            expected_version = int(expected_raw)
        except (KeyError, TypeError, ValueError):
            await query.answer("Slot indisponível.", show_alert=True)
            await _root(query)
            return
        if await _foreground(query):
            await query.answer()
            return
        try:
            root = await read_service.root(query.from_user.id)
            if root is None:
                await query.answer("Personagem indisponível.", show_alert=True)
                return
            if root.combat_configuration_version != expected_version:
                await query.answer("Configuração atualizada.", show_alert=True)
                await present(query.message, render_equipment_root(root), images, edit=True)
                return
            slot_view = next(row for row in root.slots if row.slot == slot)
            if slot_view.blocked_by_two_handed:
                await query.answer()
                await present(query.message, render_equipment_root(root), images, edit=True)
            elif slot_view.item is not None:
                detail = await read_service.detail(
                    query.from_user.id, slot_view.item.item_instance_id
                )
                if detail is None:
                    await query.answer("Configuração atualizada.", show_alert=True)
                    await _root(query)
                    return
                await query.answer()
                await present(
                    query.message,
                    render_equipment_detail(detail, context="s"),
                    images,
                    edit=True,
                )
            else:
                candidates = await read_service.candidates(query.from_user.id, slot)
                if candidates is None:
                    await query.answer("Slot indisponível.", show_alert=True)
                    await _root(query)
                    return
                await query.answer()
                await present(
                    query.message,
                    render_equipment_candidates(candidates),
                    images,
                    edit=True,
                )
        except EquipmentViewUnavailable:
            await query.answer("Configuração atualizada.", show_alert=True)
            await _root(query)

    @router.callback_query(F.data.startswith("eq:c:"))
    async def equipment_candidates(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            _, _, code, expected_raw = (query.data or "").split(":")
            slot = CODE_SLOTS[code]
            expected_version = int(expected_raw)
        except (KeyError, TypeError, ValueError):
            await query.answer("Slot indisponível.", show_alert=True)
            await _root(query)
            return
        if await _foreground(query):
            await query.answer()
            return
        try:
            view = await read_service.candidates(query.from_user.id, slot)
        except EquipmentViewUnavailable:
            view = None
        if view is None:
            await query.answer("Nenhum Equipamento disponível.", show_alert=True)
            await _root(query)
            return
        if view.combat_configuration_version != expected_version:
            await query.answer("Configuração atualizada.", show_alert=True)
            await _root(query)
            return
        await query.answer()
        await present(query.message, render_equipment_candidates(view), images, edit=True)

    @router.callback_query(F.data.startswith("eq:v:"))
    async def inventory_equipment_detail(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        if await _foreground(query):
            await query.answer()
            return
        try:
            item_id = UUID(hex=(query.data or "").removeprefix("eq:v:"))
            detail = await read_service.detail(query.from_user.id, item_id)
        except (ValueError, TypeError, EquipmentViewUnavailable):
            detail = None
        if detail is None:
            await query.answer("Equipamento indisponível.", show_alert=True)
            category = await inventory.category(query.from_user.id, "equipment")
            if category is not None:
                from asterion.bot.inventory_ui import render_inventory

                await present(query.message, render_inventory(category), images, edit=True)
            return
        await query.answer()
        await present(
            query.message,
            render_equipment_detail(detail, context="i"),
            images,
            edit=True,
        )

    @router.callback_query(F.data.startswith("eq:e:"))
    async def equip_item(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            _, _, item_token, version_raw, context = (query.data or "").split(":")
            if context not in {"i", "s"}:
                raise ValueError("Invalid equipment navigation context")
            item_id = UUID(hex=item_token)
            expected_version = int(version_raw)
        except (TypeError, ValueError):
            await query.answer("Equipamento indisponível.", show_alert=True)
            await _root(query)
            return
        try:
            result = await equipment_service.equip_item(
                query.from_user.id,
                item_id,
                expected_configuration_version=expected_version,
            )
        except CombatConfigurationLocked:
            await query.answer(LOCKED_COPY, show_alert=True)
            if not await _foreground(query):
                await _refresh_after_mutation(query, context, item_id)
            return
        except EquipmentMutationRejected as exc:
            await _handle_rejection(query, exc.code, context, item_id)
            return
        if result is None:
            await query.answer("Equipamento indisponível.", show_alert=True)
            await _refresh_after_mutation(query, context, item_id)
            return
        await query.answer()
        if context == "i":
            await _refresh_after_mutation(query, "i", item_id)
        else:
            await _root(query)

    @router.callback_query(F.data.startswith("eq:u:"))
    async def unequip_item(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            _, _, code, version_raw, context = (query.data or "").split(":")
            if context not in {"i", "s"}:
                raise ValueError("Invalid equipment navigation context")
            slot = CODE_SLOTS[code]
            expected_version = int(version_raw)
        except (KeyError, TypeError, ValueError):
            await query.answer("Slot indisponível.", show_alert=True)
            await _root(query)
            return
        previous_item_id = None
        try:
            before = await read_service.root(query.from_user.id)
            if before is not None:
                slot_before = next(row for row in before.slots if row.slot == slot)
                if slot_before.item is not None:
                    previous_item_id = slot_before.item.item_instance_id
        except (EquipmentViewUnavailable, StopIteration):
            pass
        try:
            result = await equipment_service.unequip_slot(
                query.from_user.id,
                slot,
                expected_configuration_version=expected_version,
            )
        except CombatConfigurationLocked:
            await query.answer(LOCKED_COPY, show_alert=True)
            if not await _foreground(query):
                await _root(query)
            return
        except EquipmentMutationRejected as exc:
            await _handle_rejection(query, exc.code, context, None)
            return
        if result is None:
            await query.answer("Personagem indisponível.", show_alert=True)
            await _root(query)
            return
        await query.answer()
        if context == "i" and previous_item_id is not None:
            detail = await read_service.detail(query.from_user.id, previous_item_id)
            if detail is not None and isinstance(query.message, Message):
                await present(
                    query.message,
                    render_equipment_detail(detail, context="i"),
                    images,
                    edit=True,
                )
            else:
                await _refresh_after_mutation(query, "i", previous_item_id)
        else:
            await _root(query)

    return router
