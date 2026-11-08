from dataclasses import dataclass
from functools import lru_cache

from aiogram import Bot, Dispatcher

from asterion.application.account import AccountService
from asterion.application.active_arts import ActiveArtService
from asterion.application.altos_missions import AltosMissionService
from asterion.application.character_surfaces import CharacterSurfacesService
from asterion.application.class_trials import ClassTrialService
from asterion.application.consumables import ConsumableService
from asterion.application.cosmetics import CosmeticService
from asterion.application.crafting import CraftingService
from asterion.application.creation import CreationService
from asterion.application.doctrines import DoctrineService
from asterion.application.dungeons import DungeonService
from asterion.application.equipment import EquipmentService
from asterion.application.equipment_modifications import EquipmentModificationService
from asterion.application.equipment_view import EquipmentViewService
from asterion.application.groups import GroupService
from asterion.application.guilds import GuildService
from asterion.application.inventory import InventoryService
from asterion.application.legacy import LegacyService
from asterion.application.nareth_missions import NarethMissionService
from asterion.application.p1 import P1Service
from asterion.application.p2 import P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.p5 import P5Service
from asterion.application.p6 import P6Service
from asterion.application.p7 import P7Service
from asterion.application.path_selection import PathSelectionService
from asterion.application.professions import ProfessionService
from asterion.application.prologue import PrologueService
from asterion.application.round import RoundService
from asterion.application.s1 import S1Service
from asterion.application.s2 import S2Service
from asterion.application.s3 import S3Service
from asterion.application.s4 import S4Service
from asterion.application.s5 import S5Service
from asterion.application.s6 import S6Service
from asterion.application.s25 import S25Service
from asterion.application.s26 import S26Service
from asterion.application.s27 import S27Service
from asterion.application.s28 import S28Service
from asterion.application.s29 import S29Service
from asterion.application.s30 import S30Service
from asterion.application.s31 import S31Service
from asterion.application.s32 import S32Service
from asterion.application.s33 import S33Service
from asterion.application.s34 import S34Service
from asterion.application.s35 import S35Service
from asterion.application.s36 import S36Service
from asterion.application.talents import TalentService
from asterion.application.varzeas_missions import VarzeasMissionService
from asterion.application.vde_missions import VDEMissionService
from asterion.application.warehouse import WarehouseService
from asterion.application.world import WorldService
from asterion.bot.altos_missions_handlers import altos_missions_router
from asterion.bot.character_progression_handlers import character_progression_router
from asterion.bot.character_surfaces_handlers import character_surfaces_router
from asterion.bot.class_trial_handlers import class_trial_router
from asterion.bot.combat_handlers import combat_router
from asterion.bot.cosmetics_handlers import cosmetics_router
from asterion.bot.creation_handlers import creation_router
from asterion.bot.doctrines_handlers import doctrines_router
from asterion.bot.dungeon_handlers import dungeon_router
from asterion.bot.equipment_handlers import equipment_router
from asterion.bot.equipment_modification_handlers import equipment_modification_router
from asterion.bot.groups_handlers import groups_router
from asterion.bot.guilds_handlers import guilds_router
from asterion.bot.nareth_missions_handlers import nareth_missions_router
from asterion.bot.p1_handlers import p1_router
from asterion.bot.p2_handlers import p2_router
from asterion.bot.p3_handlers import p3_router
from asterion.bot.p4_handlers import p4_router
from asterion.bot.p5_handlers import p5_router
from asterion.bot.p6_handlers import p6_router
from asterion.bot.p7_handlers import p7_router
from asterion.bot.path_handlers import path_router
from asterion.bot.profession_handlers import profession_router
from asterion.bot.s1_handlers import s1_router
from asterion.bot.s2_handlers import s2_router
from asterion.bot.s3_handlers import s3_router
from asterion.bot.s4_handlers import s4_router
from asterion.bot.s5_handlers import s5_router
from asterion.bot.s6_handlers import s6_router
from asterion.bot.s25_handlers import s25_router
from asterion.bot.s26_handlers import s26_router
from asterion.bot.s27_handlers import s27_router
from asterion.bot.s28_handlers import s28_router
from asterion.bot.s29_handlers import s29_router
from asterion.bot.s30_handlers import s30_router
from asterion.bot.s31_handlers import s31_router
from asterion.bot.s32_handlers import s32_router
from asterion.bot.s33_handlers import s33_router
from asterion.bot.s34_handlers import s34_router
from asterion.bot.s35_handlers import s35_router
from asterion.bot.s36_handlers import s36_router
from asterion.bot.settings_handlers import settings_router
from asterion.bot.varzeas_missions_handlers import varzeas_missions_router
from asterion.bot.vde_missions_handlers import vde_missions_router
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
    legacy = LegacyService(SessionFactory, settings.server_id)
    groups = GroupService(SessionFactory, settings.server_id)
    p1 = P1Service(SessionFactory, settings.server_id, groups=groups)
    p2 = P2Service(SessionFactory, settings.server_id, groups=groups)
    road = RoundService(SessionFactory, settings.server_id)
    inventory = InventoryService(SessionFactory, settings.server_id)
    warehouse = WarehouseService(SessionFactory, settings.server_id)
    equipment = EquipmentService(SessionFactory, settings.server_id)
    equipment_views = EquipmentViewService(SessionFactory, settings.server_id)
    equipment_modifications = EquipmentModificationService(SessionFactory, settings.server_id)
    consumables = ConsumableService(SessionFactory, settings.server_id)
    s1 = S1Service(SessionFactory, settings.server_id)
    s2 = S2Service(SessionFactory, settings.server_id, groups=groups)
    p3 = P3Service(SessionFactory, settings.server_id, groups=groups)
    s3 = S3Service(SessionFactory, settings.server_id, groups=groups)
    s4 = S4Service(SessionFactory, settings.server_id, groups=groups)
    s5 = S5Service(SessionFactory, settings.server_id, groups=groups)
    p4 = P4Service(SessionFactory, settings.server_id, groups=groups)
    p5 = P5Service(SessionFactory, settings.server_id, groups=groups)
    p6 = P6Service(SessionFactory, settings.server_id, groups=groups)
    p7 = P7Service(SessionFactory, settings.server_id, groups=groups)
    vde_missions = VDEMissionService(SessionFactory, settings.server_id, groups=groups)
    nareth_missions = NarethMissionService(SessionFactory, settings.server_id, groups=groups)
    varzeas_missions = VarzeasMissionService(SessionFactory, settings.server_id, groups=groups)
    altos_missions = AltosMissionService(SessionFactory, settings.server_id, groups=groups)
    s6 = S6Service(SessionFactory, settings.server_id, groups=groups)
    s25 = S25Service(SessionFactory, settings.server_id)
    s26 = S26Service(SessionFactory, settings.server_id, altos_missions)
    s27 = S27Service(SessionFactory, settings.server_id, altos_missions.road)
    s28 = S28Service(SessionFactory, settings.server_id, altos_missions.road)
    s29 = S29Service(SessionFactory, settings.server_id, altos_missions.road)
    s30 = S30Service(SessionFactory, settings.server_id, altos_missions.road, altos_missions)
    s31 = S31Service(SessionFactory, settings.server_id, altos_missions)
    s32 = S32Service(SessionFactory, settings.server_id, altos_missions)
    s33 = S33Service(SessionFactory, settings.server_id, altos_missions)
    s34 = S34Service(SessionFactory, settings.server_id, altos_missions)
    s35 = S35Service(SessionFactory, settings.server_id, altos_missions)
    s36 = S36Service(SessionFactory, settings.server_id, altos_missions)
    class_trials = ClassTrialService(SessionFactory, settings.server_id)
    paths = PathSelectionService(SessionFactory, settings.server_id)
    active_arts = ActiveArtService(SessionFactory, settings.server_id)
    talents = TalentService(SessionFactory, settings.server_id)
    professions = ProfessionService(SessionFactory, settings.server_id)
    crafting = CraftingService(SessionFactory, settings.server_id)
    dungeons = DungeonService(SessionFactory, settings.server_id)
    character_surfaces = CharacterSurfacesService(SessionFactory, settings.server_id)
    cosmetics = CosmeticService(SessionFactory, settings.server_id)
    doctrines = DoctrineService(SessionFactory, settings.server_id)
    account = AccountService(
        SessionFactory,
        settings.server_id,
        NamePolicy(settings.blocked_character_names),
    )
    dispatcher.include_router(
        settings_router(account, character_surfaces, settings.creation_images)
    )
    dispatcher.include_router(
        character_surfaces_router(character_surfaces, settings.creation_images)
    )
    dispatcher.include_router(cosmetics_router(cosmetics, settings.creation_images))
    dispatcher.include_router(doctrines_router(doctrines, settings.creation_images))
    # P7 is deliberately placed before the shared Group/Combat/World routers so
    # its self-contained regional callbacks can fall through safely when they
    # do not belong to P7.
    dispatcher.include_router(p7_router(p7, settings.creation_images))
    dispatcher.include_router(vde_missions_router(vde_missions, settings.creation_images))
    dispatcher.include_router(
        nareth_missions_router(nareth_missions, settings.creation_images)
    )
    dispatcher.include_router(varzeas_missions_router(varzeas_missions, settings.creation_images))
    dispatcher.include_router(
        altos_missions_router(
            altos_missions, settings.creation_images, s30=s30, s31=s31, s32=s32
        )
    )
    guilds = GuildService(SessionFactory, settings.server_id)
    dispatcher.include_router(guilds_router(guilds, settings.creation_images))
    dispatcher.include_router(
        groups_router(
            groups,
            settings.creation_images,
            p1=p1,
            p2=p2,
            p3=p3,
            p4=p4,
            p5=p5,
            p6=p6,
            s2=s2,
            s3=s3,
            s4=s4,
            s5=s5,
            s6=s6,
            road=road,
        )
    )
    dispatcher.include_router(p2_router(p2, settings.creation_images, s3=s3, p4=p4, p5=p5, p6=p6))
    dispatcher.include_router(
        p1_router(
            p1,
            settings.creation_images,
            p2=p2,
            p3=p3,
            p4=p4,
            p5=p5,
            p6=p6,
            s6=s6,
            road=road,
        )
    )
    dispatcher.include_router(s1_router(s1, settings.creation_images))
    dispatcher.include_router(s2_router(s2, settings.creation_images))
    dispatcher.include_router(p3_router(p3, settings.creation_images, s3=s3))
    dispatcher.include_router(s3_router(s3, settings.creation_images))
    dispatcher.include_router(s4_router(s4, settings.creation_images))
    dispatcher.include_router(s5_router(s5, settings.creation_images))
    dispatcher.include_router(p4_router(p4, settings.creation_images))
    dispatcher.include_router(p5_router(p5, settings.creation_images, p6=p6))
    dispatcher.include_router(s6_router(s6, settings.creation_images))
    dispatcher.include_router(s25_router(s25, settings.creation_images))
    dispatcher.include_router(s26_router(s26, settings.creation_images))
    dispatcher.include_router(s27_router(s27, settings.creation_images))
    dispatcher.include_router(s28_router(s28, settings.creation_images))
    dispatcher.include_router(s29_router(s29, settings.creation_images))
    dispatcher.include_router(s30_router(s30, settings.creation_images))
    dispatcher.include_router(s31_router(s31, settings.creation_images))
    dispatcher.include_router(s32_router(s32, settings.creation_images))
    dispatcher.include_router(s33_router(s33, settings.creation_images))
    dispatcher.include_router(s34_router(s34, settings.creation_images))
    dispatcher.include_router(s35_router(s35, settings.creation_images))
    dispatcher.include_router(s36_router(s36, settings.creation_images))
    dispatcher.include_router(p6_router(p6, settings.creation_images))
    dispatcher.include_router(path_router(paths, class_trials, settings.creation_images))
    dispatcher.include_router(
        character_progression_router(talents, active_arts, settings.creation_images)
    )
    dispatcher.include_router(profession_router(professions, crafting, settings.creation_images))
    dispatcher.include_router(class_trial_router(class_trials, settings.creation_images))
    dispatcher.include_router(dungeon_router(dungeons, settings.creation_images))
    dispatcher.include_router(
        combat_router(
            prologue,
            settings.creation_images,
            world,
            road,
            p2=p2,
            s2=s2,
            p3=p3,
            s3=s3,
            p4=p4,
            p5=p5,
            s4=s4,
            s5=s5,
            s6=s6,
            p6=p6,
            dungeons=dungeons,
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
        equipment_modification_router(
            equipment_modifications,
            equipment_views,
            inventory,
            settings.creation_images,
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
            p5=p5,
            class_trials=class_trials,
            s4=s4,
            s5=s5,
            s6=s6,
            p6=p6,
            dungeons=dungeons,
            vde_missions=vde_missions,
            nareth_missions=nareth_missions,
            varzeas_missions=varzeas_missions,
            altos_missions=altos_missions,
            s25=s25,
            s26=s26,
            s27=s27,
            s28=s28,
            s29=s29,
            s30=s30,
            s31=s31,
            s32=s32,
            s33=s33,
            s34=s34,
            s35=s35,
            s36=s36,
            legacy=legacy,
            warehouse=warehouse,
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
            p5=p5,
            class_trials=class_trials,
            s4=s4,
            s5=s5,
            s6=s6,
            p6=p6,
            dungeons=dungeons,
        )
    )
    return BotRuntime(
        bot=Bot(token=settings.telegram_bot_token),
        dispatcher=dispatcher,
    )
