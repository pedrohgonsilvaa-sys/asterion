from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher

from asterion.application.class_trials import ClassTrialService
from asterion.application.consumables import ConsumableService
from asterion.application.creation import CreationService
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.inventory import InventoryService
from asterion.application.p1 import P1Service
from asterion.application.p2 import P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.path_selection import PathSelectionService
from asterion.application.prologue import PrologueService
from asterion.application.round import RoundService
from asterion.application.s1 import S1Service
from asterion.application.s2 import S2Service
from asterion.application.s3 import S3Service
from asterion.application.world import WorldService
from asterion.bot.class_trial_handlers import class_trial_router
from asterion.bot.combat_handlers import combat_router
from asterion.bot.creation_handlers import creation_router
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.p1_handlers import p1_router
from asterion.bot.p2_handlers import p2_router
from asterion.bot.p3_handlers import p3_router
from asterion.bot.p4_handlers import p4_router
from asterion.bot.path_handlers import path_router
from asterion.bot.s1_handlers import s1_router
from asterion.bot.s2_handlers import s2_router
from asterion.bot.s3_handlers import s3_router
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
    p2 = P2Service(SessionFactory, settings.server_id)
    road = RoundService(SessionFactory, settings.server_id)
    inventory = InventoryService(SessionFactory, settings.server_id)
    equipment = EquipmentService(SessionFactory, settings.server_id)
    equipment_views = EquipmentViewService(SessionFactory, settings.server_id)
    consumables = ConsumableService(SessionFactory, settings.server_id)
    s1 = S1Service(SessionFactory, settings.server_id)
    s2 = S2Service(SessionFactory, settings.server_id)
    p3 = P3Service(SessionFactory, settings.server_id)
    s3 = S3Service(SessionFactory, settings.server_id)
    p4 = P4Service(SessionFactory, settings.server_id)
    class_trials = ClassTrialService(SessionFactory, settings.server_id)
    paths = PathSelectionService(SessionFactory, settings.server_id)
    dispatcher.include_router(p2_router(p2, settings.creation_images, s3=s3, p4=p4))
    dispatcher.include_router(p1_router(p1, settings.creation_images))
    dispatcher.include_router(s1_router(s1, settings.creation_images))
    dispatcher.include_router(s2_router(s2, settings.creation_images))
    dispatcher.include_router(p3_router(p3, settings.creation_images, s3=s3))
    dispatcher.include_router(s3_router(s3, settings.creation_images))
    dispatcher.include_router(p4_router(p4, settings.creation_images))
    dispatcher.include_router(path_router(paths, class_trials, settings.creation_images))
    dispatcher.include_router(class_trial_router(class_trials, settings.creation_images))
    dispatcher.include_router(
        combat_router(
            prologue, settings.creation_images, world, road, p2=p2, s2=s2, p3=p3,
            s3=s3, p4=p4,
        )
    )
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
        world_router(
            world,
            settings.creation_images,
            p1,
            road,
            inventory,
            s1,
            consumables,
            prologue=prologue,
            p2=p2,
            s2=s2,
            p3=p3,
            s3=s3,
            p4=p4,
            class_trials=class_trials,
        )
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
            p2=p2,
            s2=s2,
            p3=p3,
            s3=s3,
            p4=p4,
            class_trials=class_trials,
        )
    )
    return BotRuntime(
        bot=Bot(token=settings.telegram_bot_token),
        dispatcher=dispatcher,
    )
