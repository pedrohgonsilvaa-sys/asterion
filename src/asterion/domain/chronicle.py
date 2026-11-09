"""Pure rules and catalog of Crônica I · Ecos da Convergência and its Trilha.

Sources: GDD Estrutural v1.6.0 §5, §5.1–5.4, §34, §49.14 and §49.16; content from
``ASTERION_CRONICA_I_ECOS_DA_CONVERGENCIA_v0_2_PROPOSTA.md`` (2026-11-09) with the
author decisions recorded in HANDOFF.md ("Decisões do autor sobre a proposta").

Author decisions used here:
- Day 1 is configured by the operator; without it nothing opens. Every other date
  derives from Day 1 (chapters every 7 days, the vote, T, T+2h and T+14d).
- The entry gate is P1 completed.
- The vote opens with Chapter 8 (D50); T is at 21:00 America/Sao_Paulo.
- Basic materials and Fragments use the Grade of the Dádiva Diária.
- The 2/day limits of the repeatable sources are content, subject to Balanceamento.
- Vote options are shuffled per player.
- ``pr_cr01_eco_residual`` is postponed: every outcome is narrative only.

Points the sources leave open, chosen here and listed in HANDOFF.md for review:
- a chapter opens at 06:00 America/Sao_Paulo, the daily reset of §34;
- T is the last day of week 8 (D56) at 21:00;
- "weeks released" for the repeatable cap is the number of chapters already open.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from asterion.domain.arena import elo_for

CHRONICLE_ID = "cr01"
CHRONICLE_NAME = "Ecos da Convergência"
TIMEZONE = ZoneInfo("America/Sao_Paulo")

CHAPTER_COUNT = 8
CHAPTER_CADENCE = timedelta(days=7)
CHAPTER_OPENS_AT = time(6, 0)
END_TIME = time(21, 0)
END_DAY_OFFSET = 55  # D56 is Day 1 + 55 days.
VOTE_CLOSE_BEFORE_END = timedelta(hours=48)
RUNOFF_DURATION = timedelta(hours=24)
FINALIZATION_GRACE = timedelta(hours=2)
RESCUE_PERIOD = timedelta(days=14)

ENTRY_GATE_QUEST = "P1"
CHAPTER_COMPLETION_POINTS = 250
REPEATABLE_POINTS = 25
REPEATABLE_WEEKLY_CAP = 150
REPEATABLE_MAX = 1200
MILESTONE_STEP = 100
MILESTONE_COUNT = 40
MAX_POINTS = MILESTONE_STEP * MILESTONE_COUNT
VOTE_MIN_CHAPTERS = 4
VOTE_MIN_FINAL_OBJECTIVES = 1


class Phase(StrEnum):
    UNSCHEDULED = "unscheduled"  # no Day 1 configured
    SCHEDULED = "scheduled"  # Day 1 configured, not started
    ACTIVE = "active"  # D1 .. T
    CLOSING = "closing"  # T .. T+2h: entry closed, started activities may finish
    RESCUE = "rescue"  # T+2h .. T+14d: only claims of unlocked rewards
    ARCHIVED = "archived"  # after T+14d


# ------------------------------------------------------------------ calendar


@dataclass(frozen=True, slots=True)
class Calendar:
    day1: date
    end_at: datetime  # T, the ``cycle_end_at``

    @property
    def starts_at(self) -> datetime:
        return self.chapter_opens_at(1)

    def chapter_opens_at(self, chapter: int) -> datetime:
        if not 1 <= chapter <= CHAPTER_COUNT:
            raise ValueError("chapter must be 1..8")
        day = self.day1 + CHAPTER_CADENCE * (chapter - 1)
        return datetime.combine(day, CHAPTER_OPENS_AT, TIMEZONE)

    @property
    def vote_opens_at(self) -> datetime:
        return self.chapter_opens_at(CHAPTER_COUNT)

    @property
    def vote_closes_at(self) -> datetime:
        return self.end_at - VOTE_CLOSE_BEFORE_END

    @property
    def runoff_closes_at(self) -> datetime:
        return self.vote_closes_at + RUNOFF_DURATION

    @property
    def finalization_at(self) -> datetime:
        return self.end_at + FINALIZATION_GRACE

    @property
    def rescue_ends_at(self) -> datetime:
        return self.end_at + RESCUE_PERIOD

    def phase(self, now: datetime) -> Phase:
        if now < self.starts_at:
            return Phase.SCHEDULED
        if now < self.end_at:
            return Phase.ACTIVE
        if now < self.finalization_at:
            return Phase.CLOSING
        if now < self.rescue_ends_at:
            return Phase.RESCUE
        return Phase.ARCHIVED

    def chapters_open(self, now: datetime) -> int:
        """Chapters already released; they stay playable until the cutoff (§5.2)."""
        return sum(now >= self.chapter_opens_at(n) for n in range(1, CHAPTER_COUNT + 1))

    def accepts_progress(self, now: datetime, started_at: datetime | None = None) -> bool:
        """§5.4 cutoff at T; an activity started before T may settle until T+2h."""
        if now < self.starts_at:
            return False
        if now < self.end_at:
            return True
        return (
            started_at is not None
            and self.starts_at <= started_at < self.end_at
            and now < self.finalization_at
        )

    def vote_round(self, now: datetime) -> str | None:
        if self.vote_opens_at <= now < self.vote_closes_at:
            return "main"
        if self.vote_closes_at <= now < self.runoff_closes_at:
            return "runoff"
        return None


def default_end_at(day1: date) -> datetime:
    return datetime.combine(day1 + timedelta(days=END_DAY_OFFSET), END_TIME, TIMEZONE)


def calendar_for(day1: date, end_at: datetime | None = None) -> Calendar:
    end = end_at or default_end_at(day1)
    calendar = Calendar(day1, end)
    if end <= calendar.vote_opens_at + VOTE_CLOSE_BEFORE_END:
        raise ValueError("T must leave the vote open before it closes at T-48h")
    return calendar


def repeatable_cap(weeks_released: int) -> int:
    return min(REPEATABLE_MAX, REPEATABLE_WEEKLY_CAP * max(0, weeks_released))


def daily_cycle(now: datetime) -> date:
    """The Asterion day that starts at the 06:00 reset (§34)."""
    local = now.astimezone(TIMEZONE)
    return (local - timedelta(hours=6)).date()


# ------------------------------------------------------------- spoiler layers


class Layer(StrEnum):
    C1 = "c1"
    C2 = "c2"
    H = "h"
    C3 = "c3"
    C4 = "c4"


LAYER_QUESTS: dict[Layer, str] = {
    Layer.C1: "P6",
    Layer.C2: "P18",
    Layer.H: "P24",
    Layer.C3: "P29",
    Layer.C4: "P35",
}


def layers_for(completed_quests: Iterable[str]) -> frozenset[Layer]:
    done = set(completed_quests)
    return frozenset(layer for layer, quest in LAYER_QUESTS.items() if quest in done)


# --------------------------------------------------------- chapters/objectives


class ObjectiveKind(StrEnum):
    NPC = "npc"
    DESBRAVAR = "desbravar"
    EVIDENCE = "evidence"
    ENCOUNTER = "encounter"
    DUNGEON = "dungeon"
    EVENT = "event"


KIND_LABELS: dict[ObjectiveKind, str] = {
    ObjectiveKind.NPC: "Falar com NPC",
    ObjectiveKind.DESBRAVAR: "Desbravar",
    ObjectiveKind.EVIDENCE: "Leituras",
    ObjectiveKind.ENCOUNTER: "Encontro",
    ObjectiveKind.DUNGEON: "Masmorra",
    ObjectiveKind.EVENT: "Evento Mundial",
}


@dataclass(frozen=True, slots=True)
class Objective:
    objective_id: str
    chapter: int
    title: str
    kind: ObjectiveKind
    required: bool
    points: int
    final_phase: bool = False
    min_level: int = 1


@dataclass(frozen=True, slots=True)
class Chapter:
    number: int
    title: str
    summary: str
    conclusion: str

    @property
    def chapter_id(self) -> str:
        return f"cap_{self.number:02d}"

    @property
    def conclusion_id(self) -> str:
        return f"{self.chapter_id}_conclusao"


_N, _D, _E, _F, _M, _V = (
    ObjectiveKind.NPC,
    ObjectiveKind.DESBRAVAR,
    ObjectiveKind.EVIDENCE,
    ObjectiveKind.ENCOUNTER,
    ObjectiveKind.DUNGEON,
    ObjectiveKind.EVENT,
)
ELITE_MIN_LEVEL = 3
BOSS_MIN_LEVEL = 5

# (chapter, slot, title, kind, required, points, final phase, minimum level)
_OBJECTIVES: tuple[tuple[int, int, str, ObjectiveKind, bool, int, bool, int], ...] = (
    (1, 1, "Relatar o Pulso", _N, True, 50, False, 1),
    (1, 2, "O Que a Pedra Repetiu", _D, True, 70, False, 1),
    (1, 3, "Leituras do Pulso", _E, True, 60, False, 1),
    (1, 4, "O Primeiro Eco", _F, True, 70, False, 1),
    (2, 1, "Marcas que Vibram", _D, True, 60, False, 1),
    (2, 2, "Quem Aponta", _F, True, 70, False, 1),
    (2, 3, "Cartas Cruzadas", _N, True, 50, False, 1),
    (2, 4, "Sob as Pedras que Vigiam", _M, False, 70, False, 1),
    (3, 1, "Travessias Fechadas", _N, True, 40, False, 1),
    (3, 2, "A Ordem do Pulso", _E, True, 70, False, 1),
    (3, 3, "Onde as Raízes Descem", _M, False, 70, False, 1),
    (3, 4, "O Posto Vazio", _F, True, 70, False, 1),
    (4, 1, "Marcos que Apontam", _D, True, 50, False, 1),
    (4, 2, "A Correção Publicada", _N, True, 50, False, 1),
    (4, 3, "Ressonância", _V, False, 60, False, 1),
    (4, 4, "Fim de Turno", _F, True, 90, False, BOSS_MIN_LEVEL),
    (5, 1, "Antes de Liberar a Água", _N, True, 50, False, 1),
    (5, 2, "Compasso", _E, True, 70, False, 1),
    (5, 3, "O Peso que Ninguém Vê", _F, True, 70, False, 1),
    (5, 4, "O Que Ainda Bombeia", _M, False, 60, False, 1),
    (6, 1, "A Ordem sem Data", _N, True, 50, False, 1),
    (6, 2, "Ecos da Bastilha", _D, True, 60, False, 1),
    (6, 3, "Prioridades Incompatíveis", _M, False, 60, False, 1),
    (6, 4, "Fila sem Fim", _F, True, 80, False, ELITE_MIN_LEVEL),
    (7, 1, "Dupla Testemunha", _E, True, 60, False, 1),
    (7, 2, "Registrar a Sequência", _N, True, 50, False, 1),
    (7, 3, "O Registro que Risca", _F, True, 80, False, ELITE_MIN_LEVEL),
    (7, 4, "Ressonância Plena", _V, False, 60, True, 1),
    (8, 1, "Testemunho", _N, True, 50, True, 1),
    (8, 2, "A Última Leitura", _D, True, 50, True, 1),
    (8, 3, "Ressonância Plena", _V, False, 50, True, 1),
    (8, 4, "Sem Resposta", _F, True, 100, True, BOSS_MIN_LEVEL),
)

OBJECTIVES: tuple[Objective, ...] = tuple(
    Objective(f"cap_{chapter:02d}_obj_{slot:02d}", chapter, title, kind, req, pts, final, lvl)
    for chapter, slot, title, kind, req, pts, final, lvl in _OBJECTIVES
)
OBJECTIVES_BY_ID: dict[str, Objective] = {item.objective_id: item for item in OBJECTIVES}
FINAL_PHASE_OBJECTIVES = frozenset(item.objective_id for item in OBJECTIVES if item.final_phase)

CHAPTERS: tuple[Chapter, ...] = (
    Chapter(
        1,
        "O Pulso",
        "Em todas as Regiões, ao mesmo tempo, pedras antigas estremecem num pulso seco. "
        "Inscrições apagadas ficam legíveis por instantes. Uma palavra se repete: "
        "CONVERGÊNCIA.",
        "O coordenador do hub decide tratar o pulso como risco de rota e pede que você "
        "acompanhe as próximas leituras.",
    ),
    Chapter(
        2,
        "Pedras que Respondem",
        "No Ocaso, o pulso ganha forma: a fuligem treme em linhas e marcas antigas vibram "
        "sem que ninguém as toque. O pulso volta em intervalos.",
        "Alda Veyr manda marcar os horários de pulso nos registros de rota do Refúgio.",
    ),
    Chapter(
        3,
        "Laços que se Tensionam",
        "Cada pulso contrai as raízes e as travessias fecham nos horários de pulso. "
        "O pulso não chega a todos ao mesmo tempo. Existe uma ordem.",
        "O registrador desenha a primeira tabela da ordem de chegada do pulso.",
    ),
    Chapter(
        4,
        "Linhas que Discordam",
        "Durante cada pulso, os marcos apontam para o mesmo lado e depois voltam. "
        "Os registradores chegam a uma conclusão incômoda: o pulso tem direção.",
        "O mapa conjunto dos registradores mostra o pulso vindo de muito além das Planícies.",
    ),
    Chapter(
        5,
        "Compasso sob a Água",
        "A água entra em compasso com o pulso. Registros de manutenção descrevem o pulso "
        "como um sinal de confirmação.",
        "Os registradores passam a chamar o conjunto dos pulsos de a Sequência, porque ela "
        "parece pedir algo, passo a passo.",
    ),
    Chapter(
        6,
        "Ordens sem Data",
        "Uma ordem antiga passa a se repetir a cada pulso, pedindo uma confirmação que "
        "ninguém sabe dar. Os Herdeiros propõem reunir todas as Leituras.",
        "As Leituras seguem para os Herdeiros, estudiosos que guardam e comparam registros "
        "antigos.",
    ),
    Chapter(
        7,
        "A Etapa Pendente",
        "As referências de todas as Regiões convergem para um mesmo ponto, e uma sequência "
        "antiga tenta completar sua última etapa. O pulso cresce até ser sentido no mundo "
        "inteiro.",
        "A Sequência Pendente está completa nos registros. Falta decidir o que fazer com ela.",
    ),
    Chapter(
        8,
        "A Resposta",
        "A Sequência está reunida e os pulsos ficam mais frequentes. Quatro respostas são "
        "apresentadas: Selar, Estabilizar, Entregar aos Herdeiros, Destruir.",
        "Antes da Resposta: as quatro opções estão diante do mundo. Votar não é exigido para "
        "concluir o capítulo.",
    ),
)
CHAPTERS_BY_NUMBER: dict[int, Chapter] = {item.number: item for item in CHAPTERS}
CHAPTER_CONCLUSION_IDS: dict[str, int] = {item.conclusion_id: item.number for item in CHAPTERS}

OPENING_TEXT = (
    "No mesmo instante, em todas as estradas, a pedra antiga estremeceu. Não houve "
    "desabamento nem fogo. Só um pulso seco, como um coração que não deveria existir. Nas "
    "inscrições apagadas, uma palavra voltou a aparecer, repetida: CONVERGÊNCIA. Ninguém "
    "sabe o que ela quer dizer."
)


def objectives_of(chapter: int) -> tuple[Objective, ...]:
    return tuple(item for item in OBJECTIVES if item.chapter == chapter)


def required_objectives(chapter: int) -> frozenset[str]:
    return frozenset(item.objective_id for item in objectives_of(chapter) if item.required)


def can_conclude(chapter: int, completed: Iterable[str]) -> bool:
    return required_objectives(chapter) <= set(completed)


# --------------------------------------------------------- repeatable sources


@dataclass(frozen=True, slots=True)
class RepeatableSource:
    source_id: str
    label: str
    daily_limit: int | None  # per account; None = only one grant per key


REPEATABLE_SOURCES: dict[str, RepeatableSource] = {
    source.source_id: source
    for source in (
        RepeatableSource("rep_cr01_masmorra", "Masmorra", None),
        RepeatableSource("rep_cr01_evento", "Evento Mundial", None),
        RepeatableSource("rep_cr01_desbravar", "Desbravar", 2),
        RepeatableSource("rep_cr01_encontro", "Encontro repetido", 2),
    )
}


# --------------------------------------------------------------------- Trilha


@dataclass(frozen=True, slots=True)
class TrackReward:
    crowns: int = 0
    basics: int = 0
    fragments: int = 0
    cosmetic_id: str | None = None


@dataclass(frozen=True, slots=True)
class Cosmetic:
    cosmetic_id: str
    cosmetic_type: str  # 'title', 'frame' or 'appearance'
    name: str
    description: str


CHRONICLE_COSMETICS: tuple[Cosmetic, ...] = (
    # Livres
    Cosmetic(
        "cos_cr01_titulo_ouvinte_dos_ecos",
        "title",
        "Ouvinte dos Ecos",
        "Para quem prestou atenção quando a pedra falou.",
    ),
    Cosmetic(
        "cos_cr01_moldura_do_pulso",
        "frame",
        "Moldura do Pulso",
        "Couro escuro e ferro fosco nas laterais, com marcas de entalhe em intervalos "
        "regulares, como horários anotados à faca.",
    ),
    Cosmetic(
        "cos_cr01_titulo_testemunha_convergencia",
        "title",
        "Testemunha da Convergência",
        "Esteve presente quando a palavra voltou às pedras.",
    ),
    Cosmetic(
        "cos_cr01_moldura_leituras_cruzadas",
        "frame",
        "Moldura das Leituras Cruzadas",
        "Laterais de madeira e pedra cruzadas por cordões de registro e plaquetas de leitura "
        "gastas.",
    ),
    Cosmetic(
        "cos_cr01_aparencia_quem_respondeu",
        "appearance",
        "Manto de Quem Respondeu",
        "Manto longo de viagem sobre camadas de estrada, com um estojo de registros ao peito "
        "e lacres partidos pendurados no cinto.",
    ),
    # Premium
    Cosmetic(
        "cos_cr01_titulo_contador_de_pulsos",
        "title",
        "Contador de Pulsos",
        "Sabe de cor quanto tempo há entre uma batida e outra.",
    ),
    Cosmetic(
        "cos_cr01_moldura_marco_gasto",
        "frame",
        "Moldura do Marco Gasto",
        "Pedra e ferro com riscos de medição quase apagados, faixa simples no topo e na base.",
    ),
    Cosmetic(
        "cos_cr01_titulo_que_seguiu_o_eco",
        "title",
        "Que Seguiu o Eco",
        "Atravessou estradas atrás de um som que ninguém explicava.",
    ),
    Cosmetic(
        "cos_cr01_aparencia_itinerante_ecos",
        "appearance",
        "Vestes do Itinerante dos Ecos",
        "Capa curta impermeabilizada, camadas reparadas, cordas de leitura e placas de "
        "anotação presas ao corpo.",
    ),
    Cosmetic(
        "cos_cr01_titulo_leitor_inscricoes",
        "title",
        "Leitor de Inscrições Mudas",
        "Lê o que a pedra disse antes de voltar a calar.",
    ),
    Cosmetic(
        "cos_cr01_moldura_seis_estradas",
        "frame",
        "Moldura das Seis Estradas",
        "Laterais em seis faixas de material, uma por Região: pedra fuliginosa, madeira de "
        "raiz, marco de linha, ferro salobro, basalto e pedra pálida.",
    ),
    Cosmetic(
        "cos_cr01_titulo_voz_entre_ecos",
        "title",
        "Voz entre os Ecos",
        "Falou quando todos só escutavam.",
    ),
    Cosmetic(
        "cos_cr01_aparencia_registrador_campo",
        "appearance",
        "Traje do Registrador de Campo",
        "Sobrecamadas estreitas de tecido encerado, estojos de carvão e cera, lenço contra pó "
        "e luvas de dedos livres.",
    ),
    Cosmetic(
        "cos_cr01_moldura_sequencia_interrompida",
        "frame",
        "Moldura da Sequência Interrompida",
        "Ferro gasto com uma fileira de entalhes regulares que para no meio, sem terminar.",
    ),
    Cosmetic(
        "cos_cr01_aparencia_ultima_leitura",
        "appearance",
        "Manto da Última Leitura",
        "Manto pesado e escuro, com lacres, cordões de registro e uma placa de leitura "
        "rachada presa ao ombro.",
    ),
)
CHRONICLE_COSMETICS_BY_ID: dict[str, Cosmetic] = {
    item.cosmetic_id: item for item in CHRONICLE_COSMETICS
}

FREE_TRACK: dict[int, TrackReward] = {
    2: TrackReward(crowns=250),
    4: TrackReward(basics=3),
    6: TrackReward(fragments=2),
    8: TrackReward(cosmetic_id="cos_cr01_titulo_ouvinte_dos_ecos"),
    10: TrackReward(crowns=300, basics=3),
    12: TrackReward(basics=3, fragments=2),
    14: TrackReward(crowns=350),
    16: TrackReward(basics=3, fragments=2),
    18: TrackReward(crowns=400),
    20: TrackReward(fragments=2, cosmetic_id="cos_cr01_moldura_do_pulso"),
    22: TrackReward(crowns=450, basics=3),
    24: TrackReward(basics=3, fragments=3),
    26: TrackReward(crowns=500),
    28: TrackReward(basics=3, cosmetic_id="cos_cr01_titulo_testemunha_convergencia"),
    30: TrackReward(crowns=550, fragments=2),
    32: TrackReward(basics=3, fragments=3),
    34: TrackReward(crowns=600, basics=3),
    36: TrackReward(fragments=2, cosmetic_id="cos_cr01_moldura_leituras_cruzadas"),
    38: TrackReward(crowns=700, basics=3),
    40: TrackReward(crowns=900, fragments=2, cosmetic_id="cos_cr01_aparencia_quem_respondeu"),
}

PREMIUM_TRACK: dict[int, TrackReward] = {
    4: TrackReward(cosmetic_id="cos_cr01_titulo_contador_de_pulsos"),
    8: TrackReward(cosmetic_id="cos_cr01_moldura_marco_gasto"),
    12: TrackReward(cosmetic_id="cos_cr01_titulo_que_seguiu_o_eco"),
    16: TrackReward(cosmetic_id="cos_cr01_aparencia_itinerante_ecos"),
    20: TrackReward(cosmetic_id="cos_cr01_titulo_leitor_inscricoes"),
    24: TrackReward(cosmetic_id="cos_cr01_moldura_seis_estradas"),
    28: TrackReward(cosmetic_id="cos_cr01_titulo_voz_entre_ecos"),
    32: TrackReward(cosmetic_id="cos_cr01_aparencia_registrador_campo"),
    36: TrackReward(cosmetic_id="cos_cr01_moldura_sequencia_interrompida"),
    40: TrackReward(cosmetic_id="cos_cr01_aparencia_ultima_leitura"),
}


def milestones_reached(points: int) -> int:
    return min(MILESTONE_COUNT, max(0, points) // MILESTONE_STEP)


def claimable(
    points: int, premium: bool, claimed: Iterable[tuple[str, int]]
) -> tuple[tuple[str, int], ...]:
    """(track, milestone) pairs unlocked by ``points`` and not claimed yet."""
    reached = milestones_reached(points)
    done = set(claimed)
    tracks: list[tuple[str, Mapping[int, TrackReward]]] = [("free", FREE_TRACK)]
    if premium:
        tracks.append(("premium", PREMIUM_TRACK))
    return tuple(
        (track, milestone)
        for track, table in tracks
        for milestone in sorted(table)
        if milestone <= reached and (track, milestone) not in done
    )


def reward_for(track: str, milestone: int) -> TrackReward:
    return (FREE_TRACK if track == "free" else PREMIUM_TRACK)[milestone]


# ----------------------------------------------------------------------- vote


class Outcome(StrEnum):
    SELAR = "selar"
    ESTABILIZAR = "estabilizar"
    HERDEIROS = "herdeiros"
    DESTRUIR = "destruir"
    EM_ESPERA = "em_espera"


VOTE_OPTIONS: tuple[Outcome, ...] = (
    Outcome.SELAR,
    Outcome.ESTABILIZAR,
    Outcome.HERDEIROS,
    Outcome.DESTRUIR,
)


@dataclass(frozen=True, slots=True)
class VoteOption:
    outcome: Outcome
    label: str
    text: str
    c3: str


VOTE_TEXTS: dict[Outcome, VoteOption] = {
    Outcome.SELAR: VoteOption(
        Outcome.SELAR,
        "Selar",
        "Isolar cada ponto onde o pulso nasce e lacrar a Sequência onde ela está. Os pulsos "
        "devem cessar. O que está escrito nela continuará ali, inteiro e ilegível. Custo: "
        "escolhemos não saber, e confiamos que o selo dure mais do que a pergunta.",
        "Selar guarda a última etapa da Convergência sem confirmá-la nem apagá-la, como a "
        "Custódia mantinha o que não podia resolver.",
    ),
    Outcome.ESTABILIZAR: VoteOption(
        Outcome.ESTABILIZAR,
        "Estabilizar",
        "Aprender o ritmo do pulso e mantê-lo sob controle, ponto por ponto. A Sequência "
        "continua ativa, mas contida. Custo: quem mantém o ritmo passa a depender dele, e "
        "alguém sempre carrega mais peso que os outros.",
        "Estabilizar mantém viva uma parte da rede sem completar a Convergência, e traz de "
        "volta a dependência e a carga desigual que os antigos conheceram.",
    ),
    Outcome.HERDEIROS: VoteOption(
        Outcome.HERDEIROS,
        "Entregar aos Herdeiros",
        "Confiar a Sequência reunida aos Herdeiros, estudiosos que guardam e comparam "
        "registros antigos, para que a estudem antes que alguém aja sobre ela. Custo: a "
        "decisão fica adiada, e a chave inteira fica nas mãos de poucos.",
        "Entregar torna comum o conhecimento que o segredo dos antigos escondeu, e repete o "
        "risco de concentrar em poucos uma decisão que afeta todos.",
    ),
    Outcome.DESTRUIR: VoteOption(
        Outcome.DESTRUIR,
        "Destruir",
        "Desmontar os pontos de pulso e romper a Sequência para sempre. Os pulsos acabam. "
        "Nada do que estava registrado nela poderá ser lido, usado ou repetido. Custo: "
        "perdemos de vez uma pergunta que ninguém respondeu.",
        "Destruir encerra definitivamente a última etapa da Convergência. Foi o que uma ala "
        "dos Desvelados quis um dia; os motivos de hoje não precisam ser os mesmos.",
    ),
}
VOTE_FOOTER = "Nenhuma resposta cura o mundo. Todas custam algo."

EPILOGUES: dict[Outcome, str] = {
    Outcome.SELAR: (
        "Em cada Região, mantenedores e registradores fecham os pontos de pulso com o que "
        "têm. Em poucas semanas, o silêncio volta. As inscrições se apagam outra vez. Oren "
        'Cal escreve na margem: "Selamos o que não entendemos. Espero que isso tenha sido '
        'prudência."'
    ),
    Outcome.ESTABILIZAR: (
        "Os pulsos ficam regulares. Em Nareth, os marcos passam a ser conferidos a cada "
        "batida; nos Altos, as pontes são ajustadas no mesmo compasso. Rava Kern pergunta, "
        "em voz alta, quem vai carregar o custo no dia em que o ritmo falhar. Ninguém "
        "responde."
    ),
    Outcome.HERDEIROS: (
        "Cópias parciais da Sequência chegam a cada hub e ficam com os registradores. Os "
        "Herdeiros guardam o registro completo e prometem explicar antes de decidir. Os "
        'pulsos continuam, mais fracos. Nos Altos, alguém grava numa parede: "Quem guarda '
        'a chave?"'
    ),
    Outcome.DESTRUIR: (
        "Com martelo, alavanca e paciência, os pontos de pulso são desmontados. O último "
        "pulso é sentido em todas as Regiões ao mesmo tempo, como o primeiro. Depois, nada. "
        'Iven Raal registra a data e uma frase: "Esta pergunta não será respondida."'
    ),
    Outcome.EM_ESPERA: (
        "Ninguém chegou a uma resposta. Então a Sequência fez o que sempre tinha feito: "
        "esperou. Sem confirmação, os pulsos foram rareando até quase sumir. Os "
        'registradores anotaram a mesma frase: "A pergunta continua aberta."'
    ),
}


def vote_eligible(chapters_concluded: int, final_objectives: int) -> bool:
    return chapters_concluded >= VOTE_MIN_CHAPTERS and final_objectives >= VOTE_MIN_FINAL_OBJECTIVES


def shuffled_options(
    account_id: int, chronicle_id: str = CHRONICLE_ID, options: Iterable[Outcome] = VOTE_OPTIONS
) -> tuple[Outcome, ...]:
    """Stable per-player order, so the screen does not reshuffle on every refresh."""

    def key(option: Outcome) -> str:
        return hashlib.sha256(f"{chronicle_id}:{account_id}:{option}".encode()).hexdigest()

    return tuple(sorted(options, key=key))


@dataclass(frozen=True, slots=True)
class VoteResult:
    outcome: Outcome | None  # None while a runoff is pending
    runoff: tuple[Outcome, ...] = ()


def resolve_main(votes: Iterable[Outcome]) -> VoteResult:
    counts = Counter(votes)
    top = max((counts[option] for option in VOTE_OPTIONS), default=0)
    leaders = tuple(option for option in VOTE_OPTIONS if counts[option] == top)
    if len(leaders) == 1:
        return VoteResult(leaders[0])
    return VoteResult(None, leaders)


def resolve_runoff(votes: Iterable[Outcome], options: tuple[Outcome, ...]) -> Outcome:
    """§5.1: a persistent exact tie applies the published neutral outcome."""
    counts = Counter(vote for vote in votes if vote in options)
    top = max((counts[option] for option in options), default=0)
    leaders = [option for option in options if counts[option] == top]
    return leaders[0] if len(leaders) == 1 else Outcome.EM_ESPERA


# --------------------------------------------------- competitive cycle (§5.3)

ELO_REWARD_MIN_MATCHES = 20
REGENTE_REWARD_MIN_MATCHES = 30
REGENTE_RENOME = 3000


def elo_reward_tier(renome: int, cycle_matches: int) -> str | None:
    """Elo used for the end-of-Crônica reward, or None when not eligible (§49.14).

    Regente needs >=3000 Renome and >=30 matches; with 20..29 matches a Regente
    Renome is rewarded as the highest Elo below it.
    """
    if cycle_matches < ELO_REWARD_MIN_MATCHES:
        return None
    if renome >= REGENTE_RENOME and cycle_matches < REGENTE_REWARD_MIN_MATCHES:
        return elo_for(REGENTE_RENOME - 1)
    return elo_for(renome)
