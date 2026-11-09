"""Telegram presentation for the Batalha de Guildas (GDD v1.6.0 §15, §49.14; UI §48.3).

The Leader's Inscrição is drafted without server state: the draft travels in the
callback data as indexes into the Leader's list of eligible members, plus a short
fingerprint of that list. If the list changes mid-draft the fingerprint no longer
matches and the draft restarts, so an index never points at another character.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.guild_battle import (
    GuildBattleFightView,
    GuildBattleHubView,
    GuildBattleMessageView,
    GuildBattleResultView,
    GuildBattleView,
    MemberOption,
    RegistrationView,
    RosterSlotView,
    StandingRow,
)
from asterion.bot.combat_ui import render_combat
from asterion.bot.creation_ui import Screen
from asterion.bot.guilds_ui import pack
from asterion.domain.guild_battle import (
    COMBATANTS,
    FRONT_SIZES,
    GUILD_BATTLE_MIN_LEVEL,
    GUILD_BATTLE_TIMEZONE,
    MAX_RESERVES,
    MIN_INDIVIDUAL_PARTICIPATIONS,
    MIN_REAL_BATTLES_FOR_REWARD,
    FightKind,
    classification_points,
    schedule_for,
)
from asterion.domain.pvp_flavor import pvp_flavor

_IMAGE = "links"
# Author decision 2026-11-09: the top 10 Guilds, plus the viewer's own if lower.
STANDINGS_TOP = 10
_WEEKDAYS = ("Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo")
_KIND_LABELS = {
    FightKind.FRONT_I.value: "Frente I · 2v2",
    FightKind.FRONT_II.value: "Frente II · 3v3",
    FightKind.CHAMPION.value: "Campeão · 1v1",
}
_SLOT_TITLES = {
    FightKind.FRONT_I.value: "⚔️ Frente I · 2v2",
    FightKind.FRONT_II.value: "⚔️ Frente II · 3v3",
    "reserve": "🪑 Reservas",
}
_OUTCOME = {"win": ("🏆", "Vitória"), "loss": ("💀", "Derrota"), "draw": ("⚖️", "Empate")}
_STATUS = {
    "registered": "📝 Inscrita",
    "paired": "⚔️ Pareada",
    "bye": "🌙 Bye",
    "finished": "🏁 Encerrada",
    "cancelled": "✖️ Cancelada",
}

_ERRORS = {
    "no_character": "Crie um personagem antes de abrir a Batalha de Guildas.",
    "not_in_guild": "Você precisa estar em uma Guilda.",
    "no_permission": "Só o Líder pode inscrever a Guilda e trocar combatentes.",
    "registration_closed": "A Inscrição está fechada. Ela abre 24h antes e fecha às 20:30.",
    "cycle_closed": (
        "Esta Batalha começaria depois do fim da Crônica. A Inscrição volta a abrir "
        "depois da finalização do ciclo."
    ),
    "invalid_roster": (
        f"A Inscrição precisa de {FRONT_SIZES[FightKind.FRONT_I]} na Frente I, "
        f"{FRONT_SIZES[FightKind.FRONT_II]} na Frente II, um Campeão entre os "
        f"{COMBATANTS} e até {MAX_RESERVES} reservas, sem repetir ninguém."
    ),
    "guild_dissolving": "A Guilda está em dissolução e não pode se inscrever.",
    "member_ineligible": (
        f"Todos precisam ser membros da Guilda e estar no Nv. {GUILD_BATTLE_MIN_LEVEL} ou acima."
    ),
    "not_registered": "A Guilda não tem Inscrição para cancelar.",
    "not_in_roster": "Você não é combatente desta Batalha de Guildas.",
    "confirmation_closed": "A Confirmação de Entrada fechou às 20:50.",
    "busy": "Conclua sua atividade atual antes de confirmar a entrada.",
    "not_paired": "A Guilda ainda não foi pareada para esta Batalha.",
    "invalid_substitution": (
        "Só um reserva pode entrar, e só no lugar de um combatente que ainda não confirmou."
    ),
    "not_found": "Esta luta não existe mais.",
    "roster_changed": "A lista de membros mudou. Monte a Inscrição de novo.",
}
_MESSAGES = {
    "paired": (
        "⚔️ Batalha de Guildas · Pareamento\n\n"
        "Sua Guilda foi pareada para hoje às 21:00.\n"
        "Faça a Confirmação de Entrada até 20:50. Quem não confirmar deixa a frente "
        "sem combatente e a Guilda perde essa frente."
    ),
    "bye": (
        "🌙 Batalha de Guildas · Bye\n\n"
        "O número de Guildas inscritas foi ímpar e sua Guilda ficou sem adversário "
        "nesta Batalha. O bye não dá vitória, rating nem recompensa."
    ),
}


def error_text(code: str) -> str:
    return _ERRORS.get(code, "Esta ação não está mais disponível.")


def _button(text: str, data: str) -> InlineKeyboardButton:
    assert len(data.encode("utf-8")) <= 64, data
    return InlineKeyboardButton(text=text, callback_data=data)


def _keyboard(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=list(rows))


_BACK_TO_GUILD = [_button("← Guilda", "guild:root")]
_BACK_TO_HUB = [_button("← Batalha de Guildas", "gb:hub")]


def _when(moment: datetime) -> str:
    local = moment.astimezone(GUILD_BATTLE_TIMEZONE)
    return f"{_WEEKDAYS[local.weekday()]}, {local:%d/%m} às {local:%H:%M}"


def _clock(moment: datetime) -> str:
    return moment.astimezone(GUILD_BATTLE_TIMEZONE).strftime("%H:%M")


def _points(value: Decimal) -> str:
    text = f"{value.normalize():f}" if value == value.to_integral() else f"{value:.1f}"
    return text.replace(".", ",")


# ------------------------------------------------------------------- draft

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


@dataclass(frozen=True, slots=True)
class Draft:
    """Indexes into the Leader's candidate list."""

    front_1: tuple[int, ...] = ()
    front_2: tuple[int, ...] = ()
    champion: int | None = None
    reserves: tuple[int, ...] = ()

    @property
    def combatants(self) -> tuple[int, ...]:
        return (*self.front_1, *self.front_2)

    @property
    def chosen(self) -> tuple[int, ...]:
        return (*self.combatants, *self.reserves)

    @property
    def step(self) -> str:
        if len(self.front_1) < FRONT_SIZES[FightKind.FRONT_I]:
            return FightKind.FRONT_I.value
        if len(self.front_2) < FRONT_SIZES[FightKind.FRONT_II]:
            return FightKind.FRONT_II.value
        if self.champion is None:
            return FightKind.CHAMPION.value
        return "reserve"

    def pick(self, index: int) -> Draft:
        if index in self.chosen:
            return self
        step = self.step
        if step == FightKind.FRONT_I.value:
            return Draft((*self.front_1, index))
        if step == FightKind.FRONT_II.value:
            return Draft(self.front_1, (*self.front_2, index))
        if step == FightKind.CHAMPION.value:
            return self
        if len(self.reserves) >= MAX_RESERVES:
            return self
        return Draft(self.front_1, self.front_2, self.champion, (*self.reserves, index))

    def crown(self, index: int) -> Draft:
        if self.step != FightKind.CHAMPION.value or index not in self.combatants:
            return self
        return Draft(self.front_1, self.front_2, index)

    def pack(self) -> str:
        champion = "" if self.champion is None else _ALPHABET[self.champion]
        parts = (self.front_1, self.front_2, champion, self.reserves)
        return ".".join(
            part if isinstance(part, str) else "".join(_ALPHABET[i] for i in part)
            for part in parts
        )

    @classmethod
    def unpack(cls, text: str, size: int) -> Draft:
        parts = text.split(".")
        if len(parts) != 4:
            raise ValueError("invalid draft")

        def indexes(part: str) -> tuple[int, ...]:
            values = tuple(_ALPHABET.index(char) for char in part)
            if any(value >= size for value in values):
                raise ValueError("invalid draft index")
            return values

        front_1, front_2 = indexes(parts[0]), indexes(parts[1])
        champion = indexes(parts[2])
        reserves = indexes(parts[3])
        draft = cls(front_1, front_2, champion[0] if champion else None, reserves)
        if (
            len(front_1) > FRONT_SIZES[FightKind.FRONT_I]
            or len(front_2) > FRONT_SIZES[FightKind.FRONT_II]
            or len(champion) > 1
            or len(reserves) > MAX_RESERVES
            or len(set(draft.chosen)) != len(draft.chosen)
            or (draft.champion is not None and draft.champion not in draft.combatants)
            or ((front_2 or champion) and len(front_1) < FRONT_SIZES[FightKind.FRONT_I])
            or ((champion or reserves) and len(front_2) < FRONT_SIZES[FightKind.FRONT_II])
            or (reserves and draft.champion is None)
        ):
            raise ValueError("invalid draft")
        return draft


def fingerprint(candidates: tuple[MemberOption, ...]) -> str:
    digest = sha256(b"".join(item.character_id.bytes for item in candidates)).digest()
    return "".join(_ALPHABET[byte % 64] for byte in digest[:4])


def _draft_lines(draft: Draft, candidates: tuple[MemberOption, ...]) -> list[str]:
    def name(index: int) -> str:
        crown = "👑 " if index == draft.champion else ""
        return f"{crown}{escape(candidates[index].name)}"

    def joined(indexes: tuple[int, ...]) -> str:
        return ", ".join(name(i) for i in indexes) or "—"

    return [
        f"⚔️ Frente I · {joined(draft.front_1)}",
        f"⚔️ Frente II · {joined(draft.front_2)}",
        f"🪑 Reservas · {joined(draft.reserves)}",
    ]


def render_draft(hub: GuildBattleHubView, draft: Draft) -> Screen:
    candidates = hub.candidates
    fp = fingerprint(candidates)
    step = draft.step
    prompts = {
        FightKind.FRONT_I.value: (
            f"Escolha {FRONT_SIZES[FightKind.FRONT_I] - len(draft.front_1)} "
            "para a Frente I (2v2)."
        ),
        FightKind.FRONT_II.value: (
            f"Escolha {FRONT_SIZES[FightKind.FRONT_II] - len(draft.front_2)} "
            "para a Frente II (3v3)."
        ),
        FightKind.CHAMPION.value: (
            f"Escolha o Campeão entre os {COMBATANTS}. Ele luta o 1v1 se as Frentes empatarem."
        ),
        "reserve": f"Escolha até {MAX_RESERVES} reservas, ou revise a Inscrição.",
    }
    lines = [
        "🛡️ Batalha de Guildas · Inscrição",
        f"{_when(hub.next_starts_at)}",
        "",
        *_draft_lines(draft, candidates),
        "",
        prompts[step],
    ]
    rows: list[list[InlineKeyboardButton]] = []
    if step == FightKind.CHAMPION.value:
        options = draft.combatants
        for index in options:
            rows.append(
                [
                    _button(
                        f"👑 {candidates[index].name}",
                        f"gb:d:{fp}:{draft.crown(index).pack()}",
                    )
                ]
            )
    else:
        options = tuple(i for i in range(len(candidates)) if i not in draft.chosen)
        if step != "reserve" or len(draft.reserves) < MAX_RESERVES:
            for index in options:
                item = candidates[index]
                rows.append(
                    [
                        _button(
                            f"{item.name} · Nv. {item.level}",
                            f"gb:d:{fp}:{draft.pick(index).pack()}",
                        )
                    ]
                )
    if step == FightKind.FRONT_I.value and len(candidates) < COMBATANTS:
        lines.extend(
            [
                "",
                f"⚠️ A Guilda tem {len(candidates)} membros no Nv. {GUILD_BATTLE_MIN_LEVEL}+. "
                f"São necessários {COMBATANTS}.",
            ]
        )
    if step == "reserve":
        rows.append([_button("Revisar Inscrição", f"gb:rv:{fp}:{draft.pack()}")])
    if draft.chosen:
        rows.append([_button("Recomeçar", f"gb:d:{fp}:{Draft().pack()}")])
    rows.append(_BACK_TO_HUB)
    return Screen("\n".join(lines), _IMAGE, _keyboard(*rows), "HTML")


def render_review(hub: GuildBattleHubView, draft: Draft) -> Screen:
    fp = fingerprint(hub.candidates)
    lines = [
        "🛡️ Batalha de Guildas · Revisar Inscrição",
        f"{_when(hub.next_starts_at)}",
        "",
        *_draft_lines(draft, hub.candidates),
        "",
        "Depois do pareamento, às 20:30, o roster fica travado: ninguém dele pode sair "
        "da Guilda nem ser removido até o resultado. Até 20:50, o Líder pode trocar por "
        "um reserva quem ainda não confirmou.",
    ]
    return Screen(
        "\n".join(lines),
        _IMAGE,
        _keyboard(
            [_button("Inscrever Guilda", f"gb:reg:{fp}:{draft.pack()}")],
            [_button("Alterar", f"gb:d:{fp}:{draft.pack()}")],
            _BACK_TO_HUB,
        ),
        "HTML",
    )


# --------------------------------------------------------------------- hub


def _roster_lines(registration: RegistrationView, *, show_confirmation: bool) -> list[str]:
    lines: list[str] = []
    for slot in (FightKind.FRONT_I.value, FightKind.FRONT_II.value, "reserve"):
        entries = [row for row in registration.roster if row.slot == slot]
        if not entries:
            continue
        lines.extend(["", _SLOT_TITLES[slot]])
        for row in entries:
            lines.append(_roster_line(row, show_confirmation=show_confirmation))
    return lines


def _roster_line(row: RosterSlotView, *, show_confirmation: bool) -> str:
    crown = " 👑 Campeão" if row.is_champion else ""
    if row.replaced:
        state = " · substituído"
    elif row.slot == "reserve" or not show_confirmation:
        state = ""
    else:
        state = " · ✅ confirmado" if row.confirmed else " · ⏳ aguardando"
    return f"· {escape(row.name)}{crown}{state}"


def _own_slot(hub: GuildBattleHubView) -> RosterSlotView | None:
    if hub.registration is None:
        return None
    return next(
        (row for row in hub.registration.roster if row.character_id == hub.character_id), None
    )


def render_hub(hub: GuildBattleHubView, *, now: datetime) -> Screen:
    registration = hub.registration
    lines = [f"🛡️ Batalha de Guildas · {escape(hub.guild_name)}", ""]
    rows: list[list[InlineKeyboardButton]] = []
    if hub.in_fight:
        rows.append([_button("⚔️ Voltar ao combate", "gb:ref")])
    if registration is None:
        schedule = schedule_for(hub.next_starts_at)
        lines.extend(
            [
                f"📅 Próxima Batalha · {_when(hub.next_starts_at)}",
                f"📝 Inscrição · {_when(schedule.registration_opens_at)} até "
                f"{_clock(schedule.registration_closes_at)}",
                "",
                "Frente I 2v2 e Frente II 3v3, cada uma vale 1 ponto. Empate nos pontos "
                "leva ao Campeão 1v1. Todos precisam do Nv. "
                f"{GUILD_BATTLE_MIN_LEVEL} atual.",
                "",
                "🟢 Inscrição aberta" if hub.registration_open else "🔴 Inscrição fechada",
            ]
        )
        if hub.is_leader and hub.registration_open:
            fp = fingerprint(hub.candidates)
            rows.append([_button("Montar Inscrição", f"gb:d:{fp}:{Draft().pack()}")])
    else:
        schedule = schedule_for(registration.starts_at)
        lines.append(f"📅 {_when(registration.starts_at)}")
        lines.append(_STATUS.get(registration.status, registration.status))
        if registration.opponent_name:
            lines.append(f"🆚 {escape(registration.opponent_name)}")
        paired = registration.status == "paired"
        confirming = paired and now < schedule.confirmation_closes_at
        if registration.status == "registered":
            lines.append(f"Pareamento às {_clock(schedule.registration_closes_at)}.")
        if confirming:
            lines.append(
                f"Confirmação de Entrada até {_clock(schedule.confirmation_closes_at)}. "
                f"Início às {_clock(schedule.starts_at)}."
            )
        if registration.status == "bye":
            lines.append("Sem adversário nesta Batalha: sem vitória, rating ou recompensa.")
        lines.extend(_roster_lines(registration, show_confirmation=paired))
        own = _own_slot(hub)
        if (
            confirming
            and own is not None
            and own.slot != "reserve"
            and not own.replaced
            and not own.confirmed
        ):
            lines.extend(
                [
                    "",
                    "A Confirmação de Entrada registra e trava sua Configuração de Combate "
                    "completa até o fim da sua participação.",
                ]
            )
            rows.append([_button("✅ Confirmar Entrada", "gb:ok")])
        if hub.is_leader and registration.status == "registered" and hub.registration_open:
            fp = fingerprint(hub.candidates)
            rows.append([_button("Refazer Inscrição", f"gb:d:{fp}:{Draft().pack()}")])
            rows.append([_button("Cancelar Inscrição", "gb:cx")])
        if hub.is_leader and confirming and _substitution_pairs(registration):
            rows.append([_button("Substituir por reserva", "gb:sub")])
    rows.append([_button("📈 Classificação", "gb:std")])
    rows.append(_BACK_TO_GUILD)
    return Screen("\n".join(lines), _IMAGE, _keyboard(*rows), "HTML")


def render_cancel_confirm() -> Screen:
    return Screen(
        "🛡️ Cancelar a Inscrição da Guilda nesta Batalha?\n\n"
        "Você pode se inscrever de novo enquanto a Inscrição estiver aberta.",
        _IMAGE,
        _keyboard([_button("Confirmar cancelamento", "gb:cxok")], _BACK_TO_HUB),
        "HTML",
    )


# ------------------------------------------------------------ substitution


def _substitution_pairs(registration: RegistrationView):
    out = [
        row
        for row in registration.roster
        if row.slot != "reserve" and not row.confirmed and not row.replaced
    ]
    reserves = [row for row in registration.roster if row.slot == "reserve" and not row.replaced]
    return (out, reserves) if out and reserves else None


def render_substitution(registration: RegistrationView, replaced: RosterSlotView | None) -> Screen:
    pairs = _substitution_pairs(registration)
    rows: list[list[InlineKeyboardButton]] = []
    if pairs is None:
        return Screen(
            "🛡️ Não há combatente sem confirmação ou reserva disponível.",
            _IMAGE,
            _keyboard(_BACK_TO_HUB),
            "HTML",
        )
    out, reserves = pairs
    if replaced is None:
        text = (
            "🛡️ Substituir por reserva\n\n"
            "Escolha o combatente que sai. Só quem ainda não confirmou pode ser trocado, "
            "até 20:50."
        )
        for row in out:
            crown = " 👑" if row.is_champion else ""
            rows.append(
                [
                    _button(
                        f"{row.name} · {_KIND_LABELS[row.slot]}{crown}",
                        f"gb:sb:{pack(row.character_id)}",
                    )
                ]
            )
    else:
        crown = " O reserva também herda o papel de Campeão." if replaced.is_champion else ""
        text = (
            f"🛡️ Substituir {escape(replaced.name)} · {_KIND_LABELS[replaced.slot]}\n\n"
            f"Escolha o reserva que entra. Ele também precisa confirmar até 20:50.{crown}"
        )
        for row in reserves:
            rows.append(
                [
                    _button(
                        row.name,
                        f"gb:sbok:{pack(replaced.character_id)}:{pack(row.character_id)}",
                    )
                ]
            )
        rows.append([_button("← Escolher outro", "gb:sub")])
    rows.append(_BACK_TO_HUB)
    return Screen(text, _IMAGE, _keyboard(*rows), "HTML")


# ----------------------------------------------------------- combat & notices


def _render_fight(view: GuildBattleFightView) -> Screen:
    screen = render_combat(view.battle)
    timer = (
        f"⏳ Seu turno · {view.seconds_left}s"
        if view.my_turn
        else f"⏳ Aguardando · {view.seconds_left}s"
    )
    rows = list(screen.keyboard.inline_keyboard) if screen.keyboard is not None else []
    rows.append([_button("Atualizar", "gb:ref")])
    return Screen(
        f"{screen.text}\n\n🛡️ {_KIND_LABELS.get(view.kind, view.kind)}\n{timer}",
        screen.image_key,
        _keyboard(*rows),
        screen.parse_mode,
    )


def _render_result(view: GuildBattleResultView) -> Screen:
    icon, label = _OUTCOME[view.outcome]
    lines = [
        f"{icon} Batalha de Guildas · {label}",
        f"{escape(view.guild_name)} vs {escape(view.opponent_name)}",
        "",
        f"⚔️ Frentes · {_points(view.points)}–{_points(view.opponent_points)}",
    ]
    if view.points == view.opponent_points:
        # UI §48.3: the Champion is a separate result, never a third Front point.
        lines.append(f"👑 Campeão · {label}")
    score = {"win": Decimal(1), "draw": Decimal("0.5"), "loss": Decimal(0)}[view.outcome]
    lines.extend(["", f"📈 Classificação · +{classification_points(score)}"])
    flavor = pvp_flavor("guild_battle", view.outcome, str(view.battle_id))
    lines.extend(["", f"<i>{escape(flavor)}</i>"])
    return Screen("\n".join(lines), _IMAGE, _keyboard(_BACK_TO_GUILD), "HTML")


def _render_message(view: GuildBattleMessageView) -> Screen:
    if view.code == "fight_over":
        label = _KIND_LABELS.get(view.fight_kind or "", "Luta")
        text = (
            f"🏁 Batalha de Guildas · Fim da luta\n{label}\n\n"
            "O resultado da Batalha chega quando todas as lutas terminarem."
        )
        rows = [[_button("Atualizar", "gb:hub")]]
    elif view.code == "paired":
        text = _MESSAGES["paired"]
        rows = [[_button("Abrir Batalha de Guildas", "gb:hub")]]
    else:
        text = _MESSAGES.get(view.code, "Esta ação não está mais disponível.")
        rows = [_BACK_TO_HUB]
    return Screen(text, _IMAGE, _keyboard(*rows), "HTML")


def render_guild_battle(view: GuildBattleView) -> Screen:
    if isinstance(view, GuildBattleFightView):
        return _render_fight(view)
    if isinstance(view, GuildBattleResultView):
        return _render_result(view)
    return _render_message(view)


# ---------------------------------------------------------------- standings


def _standing_lines(row: StandingRow, *, own: bool) -> list[str]:
    marker = "👉 " if own else ""
    eligible = "🎁 Elegível" if row.reward_eligible else (
        f"Batalhas reais · {row.real_battles}/{MIN_REAL_BATTLES_FOR_REWARD}"
    )
    return [
        f"{marker}#{row.position} {escape(row.guild_name)} · {row.points} pts",
        f"{row.wins}V · {row.draws}E · {row.losses}D · {row.byes} bye · {eligible}",
    ]


def render_standings(
    rows: tuple[StandingRow, ...],
    *,
    own_guild: str | None,
    individual_eligible: bool | None,
) -> Screen:
    lines = ["📈 Classificação · Batalha de Guildas", ""]
    lines.append(
        "Vitória 3 · Empate 1 · Derrota 0 · Bye 0. A recompensa final exige "
        f"{MIN_REAL_BATTLES_FOR_REWARD} batalhas reais da Guilda e "
        f"{MIN_INDIVIDUAL_PARTICIPATIONS} participações reais do personagem."
    )
    lines.append("")
    own = next((row for row in rows if row.guild_name == own_guild), None)
    if not rows:
        lines.append("Nenhuma Guilda disputou uma Batalha ainda.")
    for row in rows[:STANDINGS_TOP]:
        lines.extend(_standing_lines(row, own=row is own))
        lines.append("")
    if own is not None and own.position > STANDINGS_TOP:
        lines.extend(["…", *_standing_lines(own, own=True), ""])
    if individual_eligible is not None:
        lines.append(
            "🎁 Você já tem as participações para a recompensa individual."
            if individual_eligible
            else f"Você ainda não tem {MIN_INDIVIDUAL_PARTICIPATIONS} participações reais."
        )
    return Screen("\n".join(lines).rstrip(), _IMAGE, _keyboard(_BACK_TO_HUB), "HTML")
