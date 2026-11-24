"""Leituras de A Ruptura do Véu para a UI (somente leitura, sem texto de interface)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from asterion.application.active_arts import load_active_art_configuration
from asterion.application.equipment_configuration import load_equipment_configuration
from asterion.application.world_event_veu import VeuEventError, VeuEventService
from asterion.domain import veu_combat as vc
from asterion.domain import world_event_veu as ev
from asterion.domain.class_trials import class_player_actions
from asterion.domain.veu_bestiary import creature
from asterion.infrastructure.db.models import (
    Character,
    CharacterNotificationPreference,
    VeuEventAction,
    VeuEventEnemyDecision,
    VeuEventNucleus,
    VeuEventOccurrence,
    VeuEventParticipant,
    VeuEventRound,
)

PAGE_SIZE = 5


@dataclass(frozen=True, slots=True)
class NucleusLine:
    key: str
    name: str
    objective: str
    participants: int
    state: str


@dataclass(frozen=True, slots=True)
class PanelView:
    kind: str  # none | scheduled | active | final
    next_slot: datetime | None = None
    occurrence_id: UUID | None = None
    state: str | None = None
    phase: int = 0
    seconds_left: int = 0
    joined: bool = False
    current_nucleus: str | None = None
    nuclei: tuple[NucleusLine, ...] = ()
    victory: bool = False
    reward: dict | None = None
    eligible: bool | None = None


@dataclass(frozen=True, slots=True)
class EnemyBar:
    code: str
    name: str
    hp: int
    max_hp: int
    defeated: bool
    barrier: int = 0


@dataclass(frozen=True, slots=True)
class HistoryLine:
    kind: str  # enemy_damaged | barrier_absorbed | player_damaged
    name: str
    amount: int


@dataclass(frozen=True, slots=True)
class SupportLine:
    """Suporte direto registrado na rodada atual (sem números, antes da resolução)."""

    source: str
    kind: str  # heal | barrier | protection
    target: str  # nome do aliado ou "" para todos os aliados


@dataclass(frozen=True, slots=True)
class NucleusScreen:
    key: str
    name: str
    state: str
    round_number: int
    seconds_left: int
    enemies: tuple[EnemyBar, ...]
    self_name: str
    self_hp: int
    self_max_hp: int
    art_slots: tuple[int, ...]
    acted: bool
    waiting: bool
    removed: bool
    telegraphs: tuple[str, ...]
    history: tuple[HistoryLine, ...]
    support: tuple[SupportLine, ...] = ()


@dataclass(frozen=True, slots=True)
class ParticipantRow:
    name: str
    character_class: str
    hp: int
    max_hp: int
    character_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ParticipantsPage:
    key: str
    page: int
    pages: int
    rows: tuple[ParticipantRow, ...]


def _seconds(deadline: datetime, now: datetime) -> int:
    return max(0, int((deadline - now).total_seconds()))


class VeuEventViews:
    def __init__(self, service: VeuEventService):
        self.service = service
        self.sessions = service.sessions

    async def _character(self, session, actor: int) -> Character:
        character = await session.scalar(
            select(Character).where(
                Character.telegram_id == actor, Character.server_id == self.service.server_id
            )
        )
        if character is None:
            raise VeuEventError("no_character")
        return character

    async def character_id(self, actor: int) -> UUID:
        async with self.sessions() as session:
            return (await self._character(session, actor)).id

    async def notice_recipients(self) -> list[int]:
        """Telegram IDs com a categoria Eventos ligada (linha ausente = ligada)."""
        async with self.sessions() as session:
            disabled = select(CharacterNotificationPreference.character_id).where(
                CharacterNotificationPreference.category == "events",
                CharacterNotificationPreference.enabled.is_(False),
            )
            rows = await session.scalars(
                select(Character.telegram_id).where(
                    Character.server_id == self.service.server_id,
                    Character.id.not_in(disabled),
                )
            )
            return sorted(set(rows.all()))

    async def panel(self, actor: int, *, now: datetime | None = None) -> PanelView:
        now = (now or datetime.now(UTC)).astimezone(UTC)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            occurrence = await session.scalar(
                select(VeuEventOccurrence)
                .where(
                    VeuEventOccurrence.server_id == self.service.server_id,
                    VeuEventOccurrence.state.in_(
                        (ev.EventState.ABERTO.value, ev.EventState.EM_ANDAMENTO.value)
                    ),
                )
                .order_by(VeuEventOccurrence.scheduled_at.desc())
            )
            if occurrence is None:
                last = await self._last_final(session, character)
                if last is not None:
                    return last
                return PanelView("scheduled", ev.next_slot(now))
            participant = await session.get(
                VeuEventParticipant, (occurrence.id, character.id)
            )
            nuclei = await self._nuclei_lines(session, occurrence)
            current = None
            if participant is not None and participant.current_nucleus_id is not None:
                nucleus = await session.get(VeuEventNucleus, participant.current_nucleus_id)
                current = nucleus.nucleus_key
            return PanelView(
                "active",
                occurrence.scheduled_at,
                occurrence.id,
                occurrence.state,
                occurrence.phase,
                _seconds(occurrence.deadline_at, now),
                participant is not None and not participant.voluntary_exit,
                current,
                nuclei,
            )

    async def _last_final(self, session, character) -> PanelView | None:
        occurrence = await session.scalar(
            select(VeuEventOccurrence)
            .join(
                VeuEventParticipant,
                VeuEventParticipant.occurrence_id == VeuEventOccurrence.id,
            )
            .where(
                VeuEventOccurrence.server_id == self.service.server_id,
                VeuEventParticipant.character_id == character.id,
                VeuEventOccurrence.state.in_(
                    (
                        ev.EventState.CONCLUIDO.value,
                        ev.EventState.FRACASSADO.value,
                        ev.EventState.ENCERRADO.value,
                    )
                ),
            )
            .order_by(VeuEventOccurrence.scheduled_at.desc())
        )
        if occurrence is None:
            return None
        participant = await session.get(VeuEventParticipant, (occurrence.id, character.id))
        nuclei = await session.scalars(
            select(VeuEventNucleus.nucleus_key).where(
                VeuEventNucleus.occurrence_id == occurrence.id,
                VeuEventNucleus.nucleus_key == ev.FINAL_NUCLEUS_KEY,
                VeuEventNucleus.state == ev.NucleusState.RESOLVIDA.value,
            )
        )
        return PanelView(
            "final",
            occurrence.scheduled_at,
            occurrence.id,
            occurrence.state,
            occurrence.phase,
            0,
            True,
            None,
            (),
            victory=nuclei.first() is not None,
            reward=dict(participant.reward) if participant else None,
            eligible=participant.eligible if participant else None,
        )

    async def _nuclei_lines(self, session, occurrence) -> tuple[NucleusLine, ...]:
        rows = (
            await session.scalars(
                select(VeuEventNucleus)
                .where(
                    VeuEventNucleus.occurrence_id == occurrence.id,
                    VeuEventNucleus.phase == occurrence.phase,
                    VeuEventNucleus.state == ev.NucleusState.ATIVA.value,
                )
                .order_by(VeuEventNucleus.nucleus_key)
            )
        ).all()
        lines = []
        for row in rows:
            count = await session.scalar(
                select(func.count())
                .select_from(VeuEventParticipant)
                .where(
                    VeuEventParticipant.occurrence_id == occurrence.id,
                    VeuEventParticipant.current_nucleus_id == row.id,
                )
            )
            definition = ev.NUCLEI_BY_KEY[row.nucleus_key]
            lines.append(
                NucleusLine(
                    row.nucleus_key, definition.name, definition.objective, count or 0, row.state
                )
            )
        return tuple(lines)

    async def nucleus_screen(
        self, actor: int, nucleus_key: str, *, now: datetime | None = None
    ) -> NucleusScreen:
        now = (now or datetime.now(UTC)).astimezone(UTC)
        async with self.sessions() as session:
            character = await self._character(session, actor)
            occurrence = await session.scalar(
                select(VeuEventOccurrence).where(
                    VeuEventOccurrence.server_id == self.service.server_id,
                    VeuEventOccurrence.state == ev.EventState.EM_ANDAMENTO.value,
                )
            )
            if occurrence is None:
                raise VeuEventError("event_not_running")
            nucleus = await session.scalar(
                select(VeuEventNucleus).where(
                    VeuEventNucleus.occurrence_id == occurrence.id,
                    VeuEventNucleus.nucleus_key == nucleus_key,
                )
            )
            if nucleus is None:
                raise VeuEventError("nucleus_not_available")
            participant = await session.get(VeuEventParticipant, (occurrence.id, character.id))
            round_ = await session.scalar(
                select(VeuEventRound)
                .where(VeuEventRound.nucleus_id == nucleus.id)
                .order_by(VeuEventRound.round_number.desc())
            )
            open_round = round_ if round_ is not None and round_.state != "RESOLVED" else None
            enemies = tuple(
                EnemyBar(
                    code,
                    creature(code).name,
                    int(Decimal(data["hp"])),
                    int(Decimal(data["max_hp"])),
                    Decimal(data["hp"]) <= 0,
                    int(Decimal(data.get("barrier", "0"))),
                )
                for code, data in sorted(nucleus.enemy_state.items())
            )
            acted = False
            telegraphs: tuple[str, ...] = ()
            if open_round is not None:
                acted = (
                    await session.scalar(
                        select(VeuEventAction.id).where(
                            VeuEventAction.round_id == open_round.id,
                            VeuEventAction.character_id == character.id,
                        )
                    )
                    is not None
                )
                telegraphs = tuple(
                    sorted(
                        row.enemy_key
                        for row in (
                            await session.scalars(
                                select(VeuEventEnemyDecision).where(
                                    VeuEventEnemyDecision.round_id == open_round.id,
                                    VeuEventEnemyDecision.telegraph_key.is_not(None),
                                )
                            )
                        ).all()
                    )
                )
            history = await self._history(session, nucleus, character, occurrence)
            support = await self._support(session, open_round)
            arts = await load_active_art_configuration(session, character, lock_rows=False)
            slots = tuple(
                int(entry["slot"])
                for entry in arts.to_data().get("active_arts", ())
                if isinstance(entry, dict) and entry.get("slot")
            )
            max_hp = int(character.max_hp)
            hp = int(participant.hp) if participant and participant.hp is not None else max_hp
            number = (open_round or round_).round_number if (open_round or round_) else 1
            return NucleusScreen(
                nucleus_key,
                ev.NUCLEI_BY_KEY[nucleus_key].name,
                nucleus.state,
                number,
                _seconds(open_round.decision_deadline, now) if open_round else 0,
                enemies,
                character.name,
                hp,
                max_hp,
                slots,
                acted,
                participant is not None and number < participant.acts_from_round,
                participant is not None and participant.nucleus_removed_at is not None,
                telegraphs,
                history,
                support,
            )

    async def _support(self, session, open_round) -> tuple[SupportLine, ...]:
        """Seção 🤝 Suporte: só ações de suporte direto a aliados registradas nesta rodada."""
        if open_round is None:
            return ()
        rows = (
            await session.scalars(
                select(VeuEventAction)
                .where(
                    VeuEventAction.round_id == open_round.id,
                    VeuEventAction.action_type == "art",
                )
                .order_by(VeuEventAction.registered_at, VeuEventAction.character_id)
            )
        ).all()
        lines: list[SupportLine] = []
        for action in rows:
            source = await session.get(Character, action.character_id)
            if source is None:
                continue
            info = await self._art_info(session, source, action.art_slot or 0)
            if info is None or info[0] not in {"ally", "all_allies"}:
                continue
            target_name = ""
            if info[0] == "ally":
                ref = action.target_ref or ""
                target = await self._character_by_hex(session, ref)
                if target is None or target.id == source.id:
                    continue
                target_name = target.name
            for kind in info[1]:
                lines.append(SupportLine(source.name, kind, target_name))
        return tuple(lines)

    async def _character_by_hex(self, session, ref: str):
        if not ref.startswith("c:") or len(ref) != 34:
            return None
        try:
            character_id = UUID(ref[2:])
        except ValueError:
            return None
        return await session.get(Character, character_id)

    async def _art_info(self, session, character, slot: int):
        """(modo de alvo, categorias de suporte) da Arte no slot, pelo motor existente."""
        arts = await load_active_art_configuration(session, character, lock_rows=False)
        ids = list(arts.art_ids)
        if not 0 < slot <= len(ids):
            return None
        equipment = await load_equipment_configuration(session, character)
        actions = class_player_actions(
            character.character_class, tuple(ids), selected_path=equipment.selected_path
        )
        action = actions.get(ids[slot - 1])
        if action is None:
            return None
        return action.target_mode, vc.support_kinds(action)

    async def art_info(self, actor: int, slot: int):
        async with self.sessions() as session:
            character = await self._character(session, actor)
            return await self._art_info(session, character, slot)

    async def _history(self, session, nucleus, character, occurrence) -> tuple[HistoryLine, ...]:
        last = await session.scalar(
            select(VeuEventRound)
            .where(
                VeuEventRound.nucleus_id == nucleus.id,
                VeuEventRound.state == ev.RoundState.RESOLVED.value,
            )
            .order_by(VeuEventRound.round_number.desc())
        )
        if last is None:
            return ()
        names = {
            str(row.id): row.name
            for row in (
                await session.scalars(
                    select(Character).where(
                        Character.id.in_(
                            [
                                UUID(item["character"])
                                for item in last.result.get("history", ())
                                if item.get("character")
                            ]
                        )
                    )
                )
            ).all()
        }
        lines: list[HistoryLine] = []
        for item in last.result.get("history", ()):
            kind = item["kind"]
            if kind == "enemy_damaged":
                lines.append(HistoryLine(kind, creature(item["enemy"]).name, item["amount"]))
            elif kind == "barrier_absorbed":
                lines.append(HistoryLine(kind, "", item["amount"]))
            elif kind == "player_damaged":
                lines.append(
                    HistoryLine(kind, names.get(item["character"], ""), item["amount"])
                )
        return tuple(lines)

    async def participants_page(
        self, actor: int, nucleus_key: str, page: int, *, exclude_self: bool = False
    ) -> ParticipantsPage:
        async with self.sessions() as session:
            me = await self._character(session, actor)
            occurrence = await session.scalar(
                select(VeuEventOccurrence).where(
                    VeuEventOccurrence.server_id == self.service.server_id,
                    VeuEventOccurrence.state == ev.EventState.EM_ANDAMENTO.value,
                )
            )
            if occurrence is None:
                raise VeuEventError("event_not_running")
            nucleus = await session.scalar(
                select(VeuEventNucleus).where(
                    VeuEventNucleus.occurrence_id == occurrence.id,
                    VeuEventNucleus.nucleus_key == nucleus_key,
                )
            )
            if nucleus is None:
                raise VeuEventError("nucleus_not_available")
            rows = (
                await session.execute(
                    select(Character, VeuEventParticipant)
                    .join(
                        VeuEventParticipant,
                        VeuEventParticipant.character_id == Character.id,
                    )
                    .where(
                        VeuEventParticipant.occurrence_id == occurrence.id,
                        VeuEventParticipant.current_nucleus_id == nucleus.id,
                    )
                    .order_by(Character.name)
                )
            ).all()
            if exclude_self:
                rows = [row for row in rows if row[0].id != me.id]
            pages = max(1, -(-len(rows) // PAGE_SIZE))
            page = min(max(page, 0), pages - 1)
            chunk = rows[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
            return ParticipantsPage(
                nucleus_key,
                page,
                pages,
                tuple(
                    ParticipantRow(
                        character.name,
                        character.character_class,
                        int(participant.hp if participant.hp is not None else character.max_hp),
                        int(character.max_hp),
                        character.id,
                    )
                    for character, participant in chunk
                ),
            )

    async def current_round(self, nucleus_key: str):
        """Rodada em aberto do Núcleo da ocorrência em andamento (ou ``None``)."""
        async with self.sessions() as session:
            occurrence = await session.scalar(
                select(VeuEventOccurrence).where(
                    VeuEventOccurrence.server_id == self.service.server_id,
                    VeuEventOccurrence.state == ev.EventState.EM_ANDAMENTO.value,
                )
            )
            if occurrence is None:
                return None
            nucleus = await session.scalar(
                select(VeuEventNucleus).where(
                    VeuEventNucleus.occurrence_id == occurrence.id,
                    VeuEventNucleus.nucleus_key == nucleus_key,
                )
            )
            if nucleus is None:
                return None
            row = await session.scalar(
                select(VeuEventRound).where(
                    VeuEventRound.nucleus_id == nucleus.id,
                    VeuEventRound.state == ev.RoundState.OPEN.value,
                )
            )
            return None if row is None else (occurrence.id, row)
