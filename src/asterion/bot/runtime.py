from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher

from asterion.application.consumables import ConsumableService
from asterion.application.creation import CreationService
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.inventory import InventoryService
from asterion.application.p1 import P1Service
from asterion.application.prologue import PrologueService
from asterion.application.round import RoundService
from asterion.application.s1 import S1Service
from asterion.application.world import WorldService
from asterion.bot.combat_handlers import combat_router
from asterion.bot.creation_handlers import creation_router
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.p1_handlers import p1_router
from asterion.bot.s1_handlers import s1_router
from asterion.bot.world_handlers import world_router
from asterion.config import get_settings
from asterion.domain.creation import NamePolicy
from asterion.domain.prologue import PROFILE
from asterion.infrastructure.db.session import SessionFactory


@dataclass(frozen=True, slots=True)
class BotRuntime:
    bot: Bot
    dispatcher: Dispatcher


@lru_cache
def get_bot_runtime() -> BotRuntime:
    settings = get_settings()
    if not settings.telegram_bot_enabled or not settings.telegram_bot_token:
        raise RuntimeError("Telegram bot is disabled or has no token configured")

    dispatcher = Dispatcher(disable_fsm=True)
    prologue = PrologueService(SessionFactory, settings.server_id, PROFILE)
    world = WorldService(SessionFactory, settings.server_id)
    p1 = P1Service(SessionFactory, settings.server_id)
    road = RoundService(SessionFactory, settings.server_id)
    inventory = InventoryService(SessionFactory, settings.server_id)
    equipment = EquipmentService(SessionFactory, settings.server_id)
    equipment_views = EquipmentViewService(SessionFactory, settings.server_id)
    consumables = ConsumableService(SessionFactory, settings.server_id)
    s1 = S1Service(SessionFactory, settings.server_id)
    dispatcher.include_router(p1_router(p1, settings.creation_images))
    dispatcher.include_router(s1_router(s1, settings.creation_images))
    dispatcher.include_router(combat_router(prologue, settings.creation_images, world, road))
    dispatcher.include_router(
        equipment_router(
            equipment_views,
            equipment,
            inventory,
            settings.creation_images,
            p1=p1,
            road=road,
        )
    )
    dispatcher.include_router(
        world_router(world, settings.creation_images, p1, road, inventory, s1, consumables)
    )
    dispatcher.include_router(
        creation_router(
            CreationService(
                SessionFactory,
                settings.server_id,
                NamePolicy(settings.blocked_character_names),
            ),
            settings.creation_images,
            prologue,
            world,
            p1,
            road,
        )
    )
    return BotRuntime(
        bot=Bot(token=settings.telegram_bot_token),
        dispatcher=dispatcher,
    )
