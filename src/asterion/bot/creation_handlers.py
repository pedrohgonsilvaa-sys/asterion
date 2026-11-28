"""aiogram adapters. Identity is always from Telegram's authenticated sender."""

import logging
from collections.abc import Awaitable, Callable

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Chat, FSInputFile, InputMediaPhoto, Message, Update
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from asterion.application.class_trials import ClassTrialService
from asterion.application.creation import CreationService
from asterion.application.dungeons import DungeonService
from asterion.application.p1 import P1Service
from asterion.application.p2 import P2Service
from asterion.application.p3 import P3Service
from asterion.application.p4 import P4Service
from asterion.application.p5 import P5Service
from asterion.application.p6 import P6Service
from asterion.application.prologue import PrologueService
from asterion.application.road import RoadService
from asterion.application.s2 import S2Service
from asterion.application.s3 import S3Service
from asterion.application.s4 import S4Service
from asterion.application.s5 import S5Service
from asterion.application.s6 import S6Service
from asterion.application.tdo_explore import TdoExploreService
from asterion.application.world import WorldService
from asterion.bot.asset_catalog import character_key, npc_key_from_text
from asterion.bot.class_trial_ui import render_class_trial_view
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import CreationCallback, Screen, render
from asterion.bot.dungeon_ui import render_dungeons
from asterion.bot.media import assets_root, resolve_asset_file
from asterion.bot.p1_ui import render_p1
from asterion.bot.p2_ui import render_p2
from asterion.bot.p3_ui import render_p3
from asterion.bot.p4_ui import render_p4
from asterion.bot.p5_ui import render_p5
from asterion.bot.p6_ui import render_p6
from asterion.bot.refuge_hud import RefugeHudLoader
from asterion.bot.s2_ui import render_s2
from asterion.bot.s3_ui import render_s3
from asterion.bot.s4_ui import render_s4
from asterion.bot.s5_ui import render_s5
from asterion.bot.s6_ui import render_s6
from asterion.bot.world_ui import render_refuge_dashboard, render_world
from asterion.infrastructure.db.models import TelegramMediaCache
from asterion.infrastructure.db.session import SessionFactory

logger = logging.getLogger(__name__)


# Telegram returns a stable file_id after the first upload. Reusing it avoids
# uploading the same local variant again on every callback while keeping the
# random selection among the configured variants.
_PHOTO_FILE_IDS: dict[str, str] = {}
_PHOTO_CACHE_LOOKED_UP: set[str] = set()

# Looks up (race, gender, class) of the player's character; set once at startup.
CharacterArtLookup = Callable[[int], Awaitable[tuple[str, str | None, str] | None]]
_character_art_lookup: CharacterArtLookup | None = None


def set_character_art_lookup(lookup: CharacterArtLookup | None) -> None:
    global _character_art_lookup
    _character_art_lookup = lookup


async def _player_character_image(images: dict[str, str], telegram_id: int) -> str | None:
    if _character_art_lookup is None:
        return None
    try:
        found = await _character_art_lookup(telegram_id)
    except Exception:
        return None
    if found is None:
        return None
    race, gender, character_class = found
    if gender is None:
        return None
    exact = images.get(character_key(race, gender, character_class))
    if exact:
        return exact
    # Audited fallback: only the class-neutral race+gender portrait. Never another
    # class's art; with no portrait at all the screen goes out without a picture.
    logger.warning(
        "no exact art for %s/%s/%s; using the class-neutral race portrait",
        race,
        gender,
        character_class,
    )
    return images.get(character_key(race, gender))


def _asset_cache_key(path) -> str:
    try:
        return path.relative_to(assets_root()).as_posix()
    except ValueError:
        return str(path)


def _asset_fingerprint(path) -> str:
    stat = path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


async def _load_persisted_file_id(path) -> str | None:
    """Load one cold-path file id; warm requests remain memory-only."""
    memory_key = str(path)
    if memory_key in _PHOTO_CACHE_LOOKED_UP:
        return None
    _PHOTO_CACHE_LOOKED_UP.add(memory_key)
    try:
        async with SessionFactory() as session:
            return await session.scalar(
                select(TelegramMediaCache.file_id).where(
                    TelegramMediaCache.asset_key == _asset_cache_key(path),
                    TelegramMediaCache.fingerprint == _asset_fingerprint(path),
                )
            )
    except Exception:  # noqa: BLE001 - media cache must never block a response
        logger.debug("could not load Telegram media cache", exc_info=True)
        return None


async def warm_photo_file_ids() -> None:
    """Warm valid persisted media ids once before polling starts."""
    try:
        async with SessionFactory() as session:
            rows = (
                await session.execute(
                    select(
                        TelegramMediaCache.asset_key,
                        TelegramMediaCache.fingerprint,
                        TelegramMediaCache.file_id,
                    )
                )
            ).all()
        root = assets_root()
        for asset_key, fingerprint, file_id in rows:
            path = (root / asset_key).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if not path.is_file() or _asset_fingerprint(path) != fingerprint:
                continue
            memory_key = str(path)
            _PHOTO_FILE_IDS[memory_key] = file_id
            _PHOTO_CACHE_LOOKED_UP.add(memory_key)
    except Exception:  # noqa: BLE001 - warmup must never block bot startup
        logger.debug("could not warm Telegram media cache", exc_info=True)


async def _persist_file_id(path, file_id: str) -> None:
    try:
        async with SessionFactory.begin() as session:
            statement = insert(TelegramMediaCache).values(
                asset_key=_asset_cache_key(path),
                fingerprint=_asset_fingerprint(path),
                file_id=file_id,
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[TelegramMediaCache.asset_key],
                    set_={
                        "fingerprint": statement.excluded.fingerprint,
                        "file_id": statement.excluded.file_id,
                        "updated_at": func.now(),
                    },
                )
            )
    except Exception:  # noqa: BLE001 - media cache must never block a response
        logger.debug("could not persist Telegram media cache", exc_info=True)


async def _forget_file_id(path) -> None:
    memory_key = str(path)
    _PHOTO_FILE_IDS.pop(memory_key, None)
    _PHOTO_CACHE_LOOKED_UP.discard(memory_key)
    try:
        async with SessionFactory.begin() as session:
            await session.execute(
                delete(TelegramMediaCache).where(
                    TelegramMediaCache.asset_key == _asset_cache_key(path)
                )
            )
    except Exception:  # noqa: BLE001 - media cache must never block a response
        logger.debug("could not invalidate Telegram media cache", exc_info=True)


def unavailable_media(exc: TelegramBadRequest) -> bool:
    return any(
        fragment in exc.message.lower()
        for fragment in (
            "wrong file identifier",
            "wrong remote file identifier",
            "file_id_invalid",
        )
    )


def _sent_message_id(sent) -> int | None:
    # aiogram returns the sent Message; test doubles may return True instead.
    return getattr(sent, "message_id", None)


async def _screen_media(screen: Screen, images: dict[str, str], chat: Chat):
    npc = npc_key_from_text(screen.text)
    image = (npc and images.get(npc)) or images.get(screen.image_key)
    if not image and screen.image_key == "character" and chat.type == "private":
        image = await _player_character_image(images, chat.id)
    cache_key: str | None = None
    path = None
    if image and image.startswith("file:"):
        # A live combat keeps one picture for the whole activity: without a seed every
        # re-render drew a new random variant and swapped the photo on each action.
        activity = screen.timer.partition(":")[2] if screen.timer else ""
        seed = screen.media_seed or (f"activity:{activity}" if activity else None)
        path = resolve_asset_file(
            image,
            selection_key=f"{seed}:{screen.image_key}" if seed else None,
        )
        cache_key = str(path) if path else None
        media = _PHOTO_FILE_IDS.get(cache_key) if cache_key else None
        if media is None and path:
            media = await _load_persisted_file_id(path)
            if media:
                _PHOTO_FILE_IDS[cache_key] = media
        if media is None and path:
            media = FSInputFile(path)
    else:
        media = image
    return media, cache_key, path


async def present(
    message: Message, screen: Screen, images: dict[str, str], *, edit=False
) -> int | None:
    """Show ``screen`` and return the id of the Telegram message that now shows it.

    A timed combat screen also (re)starts its live turn countdown on that message.
    """
    from asterion.bot.combat_timer import SKIPPED, on_present, ticker

    chat = getattr(message, "chat", None)
    current_id = getattr(message, "message_id", None)
    if edit and chat is not None and current_id is not None and (
        screen.timer or ticker.tracks(chat.id, current_id)
    ):
        # Live combat message: this edit and the countdown share one ordered writer,
        # so a stale countdown read can never overwrite the action's newer render.
        message_id = await ticker.write(
            chat.id,
            current_id,
            ticker.begin(),
            screen,
            lambda: _present(message, screen, images, edit=edit),
            force=True,
        )
        if message_id is SKIPPED:
            message_id = current_id
    else:
        message_id = await _present(message, screen, images, edit=edit)
        if screen.timer and chat is not None and message_id is not None:
            ticker.seed(chat.id, message_id, screen)
    on_present(message, message_id, screen)
    return message_id


async def _present(
    message: Message, screen: Screen, images: dict[str, str], *, edit=False
) -> int | None:
    media, cache_key, path = await _screen_media(screen, images, message.chat)
    if edit:
        try:
            if media:
                if (
                    isinstance(media, str)
                    and message.photo
                    and message.photo[-1].file_id == media
                ):
                    await message.edit_caption(
                        caption=screen.text,
                        reply_markup=screen.keyboard,
                        parse_mode=screen.parse_mode,
                    )
                    return message.message_id
                edited = await message.edit_media(
                    InputMediaPhoto(media=media, caption=screen.text, parse_mode=screen.parse_mode),
                    reply_markup=screen.keyboard,
                )
                if cache_key and isinstance(media, FSInputFile) and edited.photo:
                    file_id = edited.photo[-1].file_id
                    _PHOTO_FILE_IDS[cache_key] = file_id
                    await _persist_file_id(path, file_id)
                return message.message_id
            if not message.photo:
                await message.edit_text(
                    screen.text,
                    reply_markup=screen.keyboard,
                    parse_mode=screen.parse_mode,
                )
                return message.message_id
        except TelegramBadRequest as exc:
            reason = exc.message.lower()
            if "message is not modified" in reason:
                return message.message_id
            if media and unavailable_media(exc):
                if cache_key and path and isinstance(media, str):
                    await _forget_file_id(path)
                    media = FSInputFile(path)
                    try:
                        edited = await message.edit_media(
                            InputMediaPhoto(
                                media=media,
                                caption=screen.text,
                                parse_mode=screen.parse_mode,
                            ),
                            reply_markup=screen.keyboard,
                        )
                        if edited.photo:
                            file_id = edited.photo[-1].file_id
                            _PHOTO_FILE_IDS[cache_key] = file_id
                            await _persist_file_id(path, file_id)
                        return message.message_id
                    except TelegramBadRequest as retry_exc:
                        if not unavailable_media(retry_exc):
                            raise
                media = None
            elif not any(
                fragment in reason
                for fragment in (
                    "message to edit not found",
                    "message can't be edited",
                    "message_id_invalid",
                )
            ):
                raise
    # A missing/deleted/uneditable message cannot invalidate committed game state.
    if media:
        try:
            sent = await message.answer_photo(
                media,
                caption=screen.text,
                reply_markup=screen.keyboard,
                parse_mode=screen.parse_mode,
            )
            if cache_key and isinstance(media, FSInputFile) and sent.photo:
                file_id = sent.photo[-1].file_id
                _PHOTO_FILE_IDS[cache_key] = file_id
                await _persist_file_id(path, file_id)
            return _sent_message_id(sent)
        except TelegramBadRequest as exc:
            if not unavailable_media(exc):
                raise
            if cache_key and path and isinstance(media, str):
                await _forget_file_id(path)
                try:
                    sent = await message.answer_photo(
                        FSInputFile(path),
                        caption=screen.text,
                        reply_markup=screen.keyboard,
                        parse_mode=screen.parse_mode,
                    )
                    if sent.photo:
                        file_id = sent.photo[-1].file_id
                        _PHOTO_FILE_IDS[cache_key] = file_id
                        await _persist_file_id(path, file_id)
                    return _sent_message_id(sent)
                except TelegramBadRequest as retry_exc:
                    if not unavailable_media(retry_exc):
                        raise
    sent = await message.answer(
        screen.text, reply_markup=screen.keyboard, parse_mode=screen.parse_mode
    )
    return _sent_message_id(sent)


async def edit_screen(
    message: Message, message_id: int, screen: Screen, images: dict[str, str]
) -> bool:
    """Edit an existing creation screen in place (photo caption included).

    Returns False when that message can no longer be edited; the caller then
    sends the screen as a new message, as ``present`` does.
    """
    media, cache_key, path = await _screen_media(screen, images, message.chat)
    chat_id = message.chat.id
    bot = message.bot
    try:
        if media is None:
            await bot.edit_message_text(
                screen.text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=screen.keyboard,
                parse_mode=screen.parse_mode,
            )
            return True
        try:
            edited = await bot.edit_message_media(
                media=InputMediaPhoto(
                    media=media, caption=screen.text, parse_mode=screen.parse_mode
                ),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=screen.keyboard,
            )
        except TelegramBadRequest as exc:
            if not (unavailable_media(exc) and cache_key and path and isinstance(media, str)):
                raise
            await _forget_file_id(path)
            edited = await bot.edit_message_media(
                media=InputMediaPhoto(
                    media=FSInputFile(path), caption=screen.text, parse_mode=screen.parse_mode
                ),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=screen.keyboard,
            )
        if cache_key and isinstance(media, FSInputFile) and getattr(edited, "photo", None):
            file_id = edited.photo[-1].file_id
            _PHOTO_FILE_IDS[cache_key] = file_id
            await _persist_file_id(path, file_id)
        return True
    except TelegramBadRequest as exc:
        reason = exc.message.lower()
        if "message is not modified" in reason:
            return True
        if any(
            fragment in reason
            for fragment in (
                "message to edit not found",
                "message can't be edited",
                "message_id_invalid",
                "there is no text in the message",
            )
        ):
            return False
        raise




def creation_router(
    service: CreationService,
    images: dict[str, str],
    prologue: PrologueService | None = None,
    world: WorldService | None = None,
    p1: P1Service | None = None,
    road: RoadService | None = None,
    p2: P2Service | None = None,
    s2: S2Service | None = None,
    p3: P3Service | None = None,
    s3: S3Service | None = None,
    p4: P4Service | None = None,
    class_trials: ClassTrialService | None = None,
    p5: P5Service | None = None,
    s4: S4Service | None = None,
    s5: S5Service | None = None,
    s6: S6Service | None = None,
    p6: P6Service | None = None,
    dungeons: DungeonService | None = None,
    tdo_explore: TdoExploreService | None = None,
    refuge_hud: RefugeHudLoader | None = None,
) -> Router:
    router = Router(name="character_creation")
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")

    async def tdo_refuge_screen(actor, world_view):
        if (
            world_view is None
            or world_view.region != "Terras do Ocaso"
            or world_view.location != "Refúgio do Ocaso"
        ):
            return None
        road_view = await road.resume(actor) if road is not None else None
        p1_view = await p1.resume(actor) if p1 is not None else None
        dungeon_view = await dungeons.known(actor) if dungeons is not None else None
        remaining = await tdo_explore.remaining(actor) if tdo_explore is not None else None
        routes = road_view.route_destinations if road_view is not None else ()
        return render_refuge_dashboard(
            world_view,
            route_destinations=routes,
            explore_remaining=len(remaining) if remaining is not None else None,
            can_hunt=bool(routes) and not (p1_view is not None and p1_view.status == "active"),
            known_dungeons=bool(dungeon_view and dungeon_view.known_dungeons),
            hud=await refuge_hud(actor) if refuge_hud is not None else None,
        )

    async def current_screen(actor, state):
        dungeon_view = await dungeons.resume(actor) if dungeons is not None else None
        if dungeon_view is not None:
            return render_dungeons(dungeon_view)
        p2_view = await p2.resume(actor) if p2 is not None else None
        if p2_view is not None and p2_view.status == "active" and p2_view.kind == "combat":
            return render_p2(p2_view)
        trial_view = (
            await class_trials.resume(actor) if class_trials is not None else None
        )
        if trial_view is not None and trial_view.kind == "active":
            return await render_class_trial_view(class_trials, actor, trial_view)
        p4_view = await p4.resume(actor) if p4 is not None else None
        if p4_view is not None and p4_view.status == "active" and p4_view.kind == "combat":
            return render_p4(p4_view)
        p5_view = await p5.resume(actor) if p5 is not None else None
        if p5_view is not None and p5_view.status == "active" and p5_view.kind == "combat":
            return render_p5(p5_view)
        p6_view = await p6.resume(actor) if p6 is not None else None
        if p6_view is not None and p6_view.status == "active" and p6_view.kind == "combat":
            return render_p6(p6_view)
        s6_view = await s6.resume(actor) if s6 is not None else None
        if s6_view is not None and s6_view.status == "active" and s6_view.kind == "combat":
            return render_s6(s6_view)
        s4_view = await s4.resume(actor) if s4 is not None else None
        if s4_view is not None and s4_view.status == "active" and s4_view.kind == "combat":
            return render_s4(s4_view)
        s5_view = await s5.resume(actor) if s5 is not None else None
        if s5_view is not None and s5_view.status == "active" and s5_view.kind == "combat":
            return render_s5(s5_view)
        s3_view = await s3.resume(actor) if s3 is not None else None
        if s3_view is not None and s3_view.status == "active" and s3_view.kind == "combat":
            return render_s3(s3_view)
        s2_view = await s2.resume(actor) if s2 is not None else None
        if s2_view is not None and s2_view.status == "active" and s2_view.kind == "combat":
            return render_s2(s2_view)
        p3_view = await p3.resume(actor) if p3 is not None else None
        if p3_view is not None and p3_view.status == "active" and p3_view.kind == "combat":
            return render_p3(p3_view)
        if p1 is not None:
            p1_view = await p1.resume(actor)
            if p1_view is not None and (p1_view.status == "active" or p1_view.combat is not None):
                if p1_view.combat is not None:
                    return render_p1(p1_view)
                world_view = await world.resume(actor) if world is not None else None
                refuge_screen = await tdo_refuge_screen(actor, world_view)
                if refuge_screen is not None:
                    return refuge_screen
                return render_p1(p1_view)
        if p2_view is not None and p2_view.status == "active":
            return render_p2(p2_view)
        road_view = None
        if road is not None:
            road_view = await road.resume(actor)
            if road_view is not None and road_view.location == "Refúgio do Ocaso":
                world_view = await world.resume(actor) if world is not None else None
                refuge_screen = await tdo_refuge_screen(actor, world_view)
                if refuge_screen is not None:
                    return refuge_screen
            if road_view is not None and (
                road_view.kind in {"combat", "exploration", "hunt_victory", "hunt_defeat"}
                or road_view.kind.startswith("round_")
            ):
                from asterion.bot.road_ui import render_road

                return render_road(road_view)
        if p6_view is not None and p6_view.status == "active":
            return render_p6(p6_view)
        if s6_view is not None and s6_view.status == "active":
            return render_s6(s6_view)
        if p3_view is not None and p3_view.status == "active":
            return render_p3(p3_view)
        if p4_view is not None and p4_view.status == "active":
            return render_p4(p4_view)
        if p5_view is not None and p5_view.status == "active":
            return render_p5(p5_view)
        if s3_view is not None and s3_view.status == "active":
            return render_s3(s3_view)
        if s2_view is not None and s2_view.status == "active":
            return render_s2(s2_view)
        if road_view is not None:
            from asterion.bot.road_ui import render_road

            return render_road(road_view)
        if world is not None:
            world_view = await world.resume(actor)
            if world_view is not None:
                return await tdo_refuge_screen(actor, world_view) or render_world(world_view)
        if prologue is not None:
            view = await prologue.resume(actor)
            if view is not None:
                if world is not None:
                    world_view = await world.resume(actor)
                    if world_view is not None:
                        return render_world(world_view)
                return render_combat(view)
        return render(state)

    async def remember(actor: int, state, message_id: int | None) -> None:
        # Persist which message shows the draft's screen, but only when it changed.
        if message_id is not None and message_id != state.screen_message_id:
            await service.remember_screen(actor, state.id, message_id)

    @router.message(CommandStart())
    async def start(message: Message):
        if message.from_user:
            actor = message.from_user.id
            state = await service.start(actor)
            message_id = await present(message, await current_screen(actor, state), images)
            await remember(actor, state, message_id)

    @router.callback_query(F.data.startswith("cc:"))
    async def callback(query: CallbackQuery):
        if not isinstance(query.message, Message):
            await query.answer()
            return
        try:
            data = CreationCallback.unpack(query.data or "")
            draft_id = data.draft_id
        except (ValueError, TypeError):
            await query.answer()
            return
        actor = query.from_user.id
        state = await service.callback(actor, draft_id, data.version, data.action)
        await query.answer()
        if state is not None:
            message_id = await present(
                query.message, await current_screen(actor, state), images, edit=True
            )
            await remember(actor, state, message_id)

    @router.message(F.text, ~F.text.startswith("/"))
    async def name(message: Message, event_update: Update):
        if message.from_user:
            actor = message.from_user.id
            state = await service.name(actor, message.text or "", event_update.update_id)
            screen = await current_screen(actor, state)
            # Unavailable name: edit the Nome screen already in the chat. If that
            # message is gone, fall through and show the screen as a new message.
            if (
                state.step == "name"
                and state.error == "unavailable"
                and state.screen_message_id is not None
                and await edit_screen(message, state.screen_message_id, screen, images)
            ):
                return
            message_id = await present(message, screen, images)
            await remember(actor, state, message_id)

    return router
