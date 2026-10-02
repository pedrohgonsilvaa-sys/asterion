"""Versioned Telegram callbacks for equipment modification."""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from asterion.application.combat_configuration_guard import CombatConfigurationLocked
from asterion.application.equipment_modifications import (
    EquipmentModificationRejected,
    EquipmentModificationService,
)
from asterion.application.equipment_view import EquipmentViewService, EquipmentViewUnavailable
from asterion.application.inventory import InventoryService
from asterion.bot.creation_handlers import present
from asterion.bot.equipment_modification_ui import (
    render_dismantle_preview,
    render_enchantment_preview,
    render_enchantments,
    render_enhancement,
    render_reroll_choices,
    render_reroll_preview,
    render_rune_preview,
    render_runes,
)
from asterion.bot.equipment_ui import render_equipment_detail
from asterion.bot.inventory_ui import render_inventory


def equipment_modification_router(
    service: EquipmentModificationService,
    read_service: EquipmentViewService,
    inventory: InventoryService,
    images: dict[str, str],
) -> Router:
    router = Router(name="equipment_modification")
    router.callback_query.filter(F.message.chat.type == "private")

    async def show_detail(query: CallbackQuery, item_id: UUID) -> None:
        if not isinstance(query.message, Message):
            return
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
            await present(query.message, render_inventory(category), images, edit=True)

    async def show_inventory(query: CallbackQuery) -> None:
        if not isinstance(query.message, Message):
            return
        category = await inventory.category(query.from_user.id, "equipment")
        if category is not None:
            await present(query.message, render_inventory(category), images, edit=True)

    def _versions(view, item_version: int, configuration_version: int) -> bool:
        return (
            view is not None
            and getattr(view, "item_version", getattr(view.item, "item_version", None))
            == item_version
            and view.combat_configuration_version == configuration_version
        )

    async def _candidate(view, index: int, item_version: int, configuration_version: int):
        if not _versions(view, item_version, configuration_version):
            return None
        candidates = tuple(view.details.get("candidates", ()))
        return candidates[index] if 0 <= index < len(candidates) else None

    def _rune_candidate(view, token: str, item_version: int, configuration_version: int):
        if not _versions(view, item_version, configuration_version):
            return None
        if len(token) != 8 or any(char not in "0123456789abcdef" for char in token):
            return None
        candidates = tuple(view.details.get("candidates", ()))
        matching = [
            candidate
            for candidate in candidates
            if sha256(str(candidate["stack_id"]).encode()).hexdigest()[:8] == token
        ]
        return matching[0] if len(matching) == 1 else None

    def _parse_base36(value: str) -> int:
        if not value or any(char not in "0123456789abcdefghijklmnopqrstuvwxyz" for char in value):
            raise ValueError("Invalid compact version")
        return int(value, 36)

    @router.callback_query(F.data.startswith("em:"))
    async def modification_callback(query: CallbackQuery) -> None:
        if not isinstance(query.message, Message):
            await query.answer()
            return
        raw = (query.data or "").split(":")
        try:
            operation = raw[1]
            item_id = UUID(hex=raw[2])
            actor = query.from_user.id
            screen = None

            if operation == "h" and len(raw) == 3:
                view = await service.enhancement_preview(actor, item_id)
                if view is None:
                    raise ValueError("Unknown item")
                screen = render_enhancement(view)
            elif operation == "hc" and len(raw) == 5:
                await service.enhance(
                    actor,
                    item_id,
                    expected_item_version=int(raw[3]),
                    expected_configuration_version=int(raw[4]),
                )
                await query.answer()
                await show_detail(query, item_id)
                return
            elif operation == "r" and len(raw) in {3, 4}:
                affinity = raw[3] if len(raw) == 4 else "A"
                if affinity not in {"A", "B"}:
                    raise ValueError("Invalid Rune affinity")
                view = await service.runes(actor, item_id, affinity=affinity)
                if view is None:
                    raise ValueError("Unknown item")
                screen = render_runes(view, affinity=affinity)
            elif operation in {"rp", "ri"} and len(raw) == 7:
                affinity = raw[3]
                if affinity not in {"A", "B"}:
                    raise ValueError("Invalid Rune affinity")
                item_version, configuration_version = map(_parse_base36, raw[5:7])
                listing = await service.runes(actor, item_id, affinity=affinity)
                candidate = _rune_candidate(listing, raw[4], item_version, configuration_version)
                if candidate is None:
                    await query.answer("Estado atualizado.", show_alert=True)
                    await show_detail(query, item_id)
                    return
                stack_id = UUID(str(candidate["stack_id"]))
                if operation == "rp":
                    view = await service.rune_preview(actor, item_id, affinity, stack_id)
                    if view is None:
                        raise ValueError("Unknown item")
                    screen = render_rune_preview(view, affinity=affinity)
                else:
                    await service.install_rune(
                        actor,
                        item_id,
                        affinity,
                        stack_id,
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                    )
                    await query.answer()
                    await show_detail(query, item_id)
                    return
            elif operation == "rr" and len(raw) == 6:
                affinity = raw[3]
                if affinity not in {"A", "B"}:
                    raise ValueError("Invalid Rune affinity")
                await service.remove_rune(
                    actor,
                    item_id,
                    affinity,
                    expected_item_version=int(raw[4]),
                    expected_configuration_version=int(raw[5]),
                )
                await query.answer()
                await show_detail(query, item_id)
                return
            elif operation == "e" and len(raw) == 3:
                view = await service.enchantments(actor, item_id)
                if view is None:
                    raise ValueError("Unknown item")
                screen = render_enchantments(view)
            elif operation in {"ep", "ec"} and len(raw) == (6 if operation == "ep" else 7):
                index, item_version, configuration_version = map(int, raw[3:6])
                listing = await service.enchantments(actor, item_id)
                candidate = await _candidate(listing, index, item_version, configuration_version)
                if candidate is None:
                    await query.answer("Estado atualizado.", show_alert=True)
                    await show_detail(query, item_id)
                    return
                recipe_id = candidate["recipe_id"]
                if operation == "ep":
                    view = await service.enchantment_preview(actor, item_id, recipe_id)
                    if view is None:
                        raise ValueError("Unknown item")
                    screen = render_enchantment_preview(view, candidate_index=index)
                else:
                    await service.apply_enchantment(
                        actor,
                        item_id,
                        recipe_id,
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                        expected_preview_token=raw[6],
                    )
                    await query.answer()
                    await show_detail(query, item_id)
                    return
            elif operation == "l" and len(raw) == 3:
                detail = await read_service.detail(actor, item_id)
                if detail is None:
                    raise ValueError("Unknown item")
                screen = render_reroll_choices(detail.item, detail.combat_configuration_version)
            elif operation in {"lp", "lc"} and len(raw) == 6:
                index, item_version, configuration_version = map(int, raw[3:6])
                detail = await read_service.detail(actor, item_id)
                if detail is None or not _versions(detail, item_version, configuration_version):
                    await query.answer("Estado atualizado.", show_alert=True)
                    await show_detail(query, item_id)
                    return
                if operation == "lp":
                    view = await service.reroll_preview(actor, item_id, index)
                    if view is None:
                        raise ValueError("Unknown item")
                    screen = render_reroll_preview(view, index=index)
                else:
                    await service.reroll(
                        actor,
                        item_id,
                        index,
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                    )
                    await query.answer()
                    await show_detail(query, item_id)
                    return
            elif operation == "d" and len(raw) == 3:
                view = await service.dismantle_preview(actor, item_id)
                if view is None:
                    raise ValueError("Unknown item")
                screen = render_dismantle_preview(view)
            elif operation in {"dm", "dc"} and len(raw) in {5, 6}:
                item_version, configuration_version = map(int, raw[3:5])
                view = await service.dismantle_preview(actor, item_id)
                if view is None:
                    raise ValueError("Unknown item")
                if not _versions(view, item_version, configuration_version):
                    await query.answer("Estado atualizado.", show_alert=True)
                    await show_detail(query, item_id)
                    return
                if operation == "dm" and len(raw) == 5:
                    screen = render_dismantle_preview(view, reinforced=True)
                elif operation == "dc" and len(raw) == 6:
                    await service.dismantle(
                        actor,
                        item_id,
                        confirm_mythic=raw[5] == "1",
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                    )
                    await query.answer()
                    await show_inventory(query)
                    return
                else:
                    raise ValueError("Invalid dismantle callback")
            elif operation in {"f", "k"} and len(raw) == 5:
                item_version, configuration_version = map(int, raw[3:5])
                detail = await read_service.detail(actor, item_id)
                if detail is None or not _versions(detail, item_version, configuration_version):
                    await query.answer("Estado atualizado.", show_alert=True)
                    await show_detail(query, item_id)
                    return
                if operation == "f":
                    await service.set_favorite(
                        actor,
                        item_id,
                        not detail.item.favorite,
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                    )
                else:
                    await service.set_locked(
                        actor,
                        item_id,
                        not detail.item.locked,
                        expected_item_version=item_version,
                        expected_configuration_version=configuration_version,
                    )
                await query.answer()
                await show_detail(query, item_id)
                return
            else:
                raise ValueError("Invalid equipment operation callback")

            if screen is None:
                raise ValueError("Unknown equipment operation")
            await query.answer()
            await present(query.message, screen, images, edit=True)
        except (ValueError, TypeError, KeyError, IndexError, EquipmentViewUnavailable):
            await query.answer("Equipamento indisponível.", show_alert=True)
            if len(raw) > 2:
                try:
                    await show_detail(query, UUID(hex=raw[2]))
                except ValueError:
                    pass
        except CombatConfigurationLocked:
            await query.answer(
                "Equipamentos não podem ser alterados durante esta atividade.",
                show_alert=True,
            )
            await show_detail(query, item_id)
        except EquipmentModificationRejected as exc:
            message = "Estado atualizado." if str(exc.code) == "STALE" else "Operação indisponível."
            await query.answer(message, show_alert=True)
            await show_detail(query, item_id)

    return router
