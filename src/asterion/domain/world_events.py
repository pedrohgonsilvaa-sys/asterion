"""Eventos Mundiais e Sintonização do Véu (GDD v1.6.0 §21, §21.1, §49.15).

Every number below comes from §49.15, except the ones marked as author decisions
(2026-11-08): the source does not define them.

``WORLD_EVENT_CATALOG`` holds the six Events of the author's catalog (one per Região,
2026-11-13). With an empty catalog no occurrence is ever created.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from asterion.domain.combat_math import (
    CombatStats,
    StatMultipliers,
    enemy_stats,
    growth,
)
from asterion.domain.creature_kits import build_creature
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import Bundle
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.road import ARCHETYPE, Creature

D = Decimal

EVENT_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RULESET = "world_event_v1"

# Monday is 0: terça, quinta e sábado.
SCHEDULE_WEEKDAYS = frozenset({1, 3, 5})
SCHEDULE_TIMES = (time(12, 0), time(20, 0))

PHASE_COUNT = 3
ENTRY_WINDOW = timedelta(minutes=15)
DEADLINE = timedelta(minutes=60)
REENTRY_DELAY = timedelta(minutes=2)
# Author decision: the source has no participants to count at the opening.
GATHERING_WINDOW = timedelta(minutes=5)

PARTICIPANT_CAP = 200
HP_SCALE_EXPONENT = D("0.88")
ATTACK_PER_EXTRA_PARTICIPANT = D("0.015")
ATTACK_SCALE_CAP = D("0.60")

ELIGIBILITY_MIN_PHASES = 2
ELIGIBILITY_MIN_ACTIONS = 8
MAJOR_CONTRIBUTION_VALUE = 4

VIGOR_COST = 10
CROWN_MULTIPLIER = D("0.40")
REWARD_BASICS = 2
REWARD_FRAGMENTS = 1
XP_PERCENT = D("0.08")

ATTUNEMENT_LEVEL_MARGIN = 5

# Author decision: the source gives the scaling but no base, so the Event uses the
# Solo base of a Masmorra Chefe (§49.6).
BOSS_BASE = StatMultipliers(D("3.00"), D("1.10"), D("1.10"), D("1.00"))
# The engine applies the "boss" category (HP 220%) before these factors.
_BOSS_CATEGORY_HP = D("2.20")


@dataclass(frozen=True, slots=True)
class WorldEventPhase:
    creature: Creature
    flavor: str


@dataclass(frozen=True, slots=True)
class WorldEventDefinition:
    event_id: str
    name: str
    region: str
    reference_level: int
    phases: tuple[WorldEventPhase, ...]
    conclusion_flavor: str
    attuned: bool = False
    # A Crônica runs several versions of one Event in the same slot: ``family`` is the
    # Event the objectives count (``evt_cr01_ressonancia``), ``version`` tells them apart.
    family: str = ""
    version: str = ""

    def __post_init__(self) -> None:
        if len(self.phases) != PHASE_COUNT:
            raise ValueError("A World Event has exactly three phases.")
        if not 1 <= self.reference_level <= 60:
            raise ValueError("Event reference level must be between 1 and 60.")

    def phase(self, number: int) -> WorldEventPhase:
        return self.phases[number - 1]


def _phase(
    creature_id: str,
    name: str,
    profile: str,
    level: int,
    labels: tuple[str, str, str],
    flavor: str,
) -> WorldEventPhase:
    creature = build_creature(creature_id, name, "boss", profile, level, labels)
    return WorldEventPhase(creature, flavor)


WORLD_EVENT_CATALOG: tuple[WorldEventDefinition, ...] = (
    WorldEventDefinition(
        "evt_tdo_cerco_das_cinzas",
        "O Cerco das Cinzas",
        "Terras do Ocaso",
        10,
        (
            _phase(
                "evt_tdo_escavador_de_cinza", "Escavador de Cinza", "Bruto", 10,
                ("Mandíbula Rente ao Chão", "Fuligem Cegante", "Investida Curta"),
                "A fuligem se move antes da criatura.\n"
                "Algo cava sob a estrada como se já conhecesse o caminho.",
            ),
            _phase(
                "evt_tdo_condutor_de_brasa_morta", "Condutor de Brasa Morta", "Equilibrado", 10,
                ("Golpe de Cinza Endurecida", "Brasas Apagadas", "Avanço Protegido"),
                "Não há fogo dentro dele. Só o rastro do que queimou.\n"
                "A estrada parece estreitar quando ele se aproxima.",
            ),
            _phase(
                "evt_tdo_cerco_de_cinzas", "Cerco de Cinzas", "Blindado", 10,
                ("Varredura Larga", "Placas de Crosta", "Muralha Viva"),
                "A criatura não caça. Ela fecha portas.\n"
                "Quando o último espaço desaparece, só resta atravessar.",
            ),
        ),
        "O caminho permanece aberto.\n"
        "No silêncio depois da luta, a fuligem volta a cair sobre a estrada. "
        "O Refúgio continua de pé.",
    ),
    WorldEventDefinition(
        "evt_vde_os_que_ainda_pendem",
        "Os Que Ainda Pendem",
        "Vales dos Enforcados",
        20,
        (
            _phase(
                "evt_vde_rastejante_de_no", "Rastejante de Nó", "Ágil", 20,
                ("Ataque Lateral", "Raízes Expostas", "Salto e Recuo"),
                "Os galhos balançam sem vento.\nDepois, alguma coisa desce.",
            ),
            _phase(
                "evt_vde_carregador_enredado", "Carregador Enredado", "Bruto", 20,
                ("Esmagar o Solo", "Raízes Arremessadas", "Golpe Pesado"),
                "A madeira range como se sustentasse peso demais.\n"
                "A criatura parece ter aprendido a mesma linguagem.",
            ),
            _phase(
                "evt_vde_pendular_do_fosso", "Pendular do Fosso", "Controlador", 20,
                ("Ataque de Cima", "Partes Soltas", "Descida Abrupta"),
                "Há coisas que caem.\nEsta não.\n"
                "Ela apenas espera que alguém chegue perto o bastante.",
            ),
        ),
        "A passagem volta a respirar.\n"
        "As raízes continuam fechadas sobre o vazio, indiferentes ao que acabou de acontecer.",
    ),
    WorldEventDefinition(
        "evt_pdn_a_linha_que_nao_termina",
        "A Linha que Não Termina",
        "Planícies de Nareth",
        30,
        (
            _phase(
                "evt_pdn_marcador_sem_rumo", "Marcador Sem Rumo", "Equilibrado", 30,
                ("Golpe na Marca", "Marca no Terreno", "Linha Reta"),
                "Uma marca aparece na terra.\nNinguém a fez.",
            ),
            _phase(
                "evt_pdn_medidor_invertido", "Medidor Invertido", "Ágil", 30,
                ("Investida Alternada", "Corrida entre Extremos", "Golpe ao Mais Distante"),
                "A distância parece mudar sem que ninguém se mova.\n"
                "O horizonte continua no mesmo lugar. É isso que assusta.",
            ),
            _phase(
                "evt_pdn_linha_sem_fim", "Linha sem Fim", "Controlador", 30,
                ("Ataque Repetido", "Percurso Traçado", "Rota Fechada"),
                "A linha termina no mesmo lugar onde começou.\n"
                "Não há explicação escrita para isso.\nHá apenas a próxima marca.",
            ),
        ),
        "A rota volta a ser uma rota.\n"
        "As marcas permanecem na terra, mas ninguém consegue dizer qual delas "
        "deveria ter sido a última.",
    ),
    WorldEventDefinition(
        "evt_vc_a_agua_que_se_ergue",
        "A Água que se Ergue",
        "Várzeas Carmesins",
        40,
        (
            _phase(
                "evt_vc_lodo_de_sangria", "Lodo de Sangria", "Bruto", 40,
                ("Massa de Lodo", "Detritos Sacudidos", "Arrasto Pesado"),
                "Primeiro, a água deixa de refletir o céu.\nDepois, alguma coisa se levanta.",
            ),
            _phase(
                "evt_vc_enraizado_rubro", "Enraizado Rubro", "Controlador", 40,
                ("Extensão do Corpo", "Raízes Curtas", "Avanço Lento"),
                "A margem parece crescer.\nNão é vegetação nova.\n"
                "É a criatura tomando espaço.",
            ),
            _phase(
                "evt_vc_colosso_da_varzea_rubra", "Colosso da Várzea Rubra", "Blindado", 40,
                ("Golpe Frontal", "Couraça de Detritos", "Investida Pesada"),
                "A água sobe até os joelhos.\nDepois, até a cintura.\n"
                "O monstro não parece perceber a diferença.",
            ),
        ),
        "A água baixa devagar.\n"
        "O terreno continua vermelho, úmido e irreconhecível por alguns minutos. "
        "Ninguém encontra uma causa que explique o que aconteceu.",
        attuned=True,
    ),
    WorldEventDefinition(
        "evt_ac_o_ultimo_contrapeso",
        "O Último Contrapeso",
        "Altos Cinéreos",
        50,
        (
            _phase(
                "evt_ac_arrastador_de_basalto", "Arrastador de Basalto", "Bruto", 50,
                ("Golpe no Solo", "Placas Arrastadas", "Avanço Pesado"),
                "A montanha já range antes de a criatura aparecer.\n"
                "Então uma pedra começa a andar.",
            ),
            _phase(
                "evt_ac_operador_de_contrapeso", "Operador de Contrapeso", "Equilibrado", 50,
                ("Golpe Curto", "Posição de Sustentação", "Empurrão para Fora"),
                "Cabos estalam acima do combate.\nAlguma coisa ainda distribui peso.\n"
                "Ninguém sabe se é a estrutura ou o monstro.",
            ),
            _phase(
                "evt_ac_tita_de_escarpa", "Titã de Escarpa", "Blindado", 50,
                ("Sequência Lenta", "Placas como Escudo", "Peso do Corpo"),
                "Quando ele se move, os cabos respondem.\nQuando ele para, tudo parece esperar.\n"
                "O peso da montanha não escolhe lado.",
            ),
        ),
        "O contrapeso permanece.\n"
        "Por enquanto, as pontes continuam sustentadas e a passagem não fecha.",
        attuned=True,
    ),
    WorldEventDefinition(
        "evt_cdv_o_silencio_entre_as_camadas",
        "O Silêncio entre as Camadas",
        "Confins do Véu",
        60,
        (
            _phase(
                "evt_cdv_reflexo_desalinhado", "Reflexo Desalinhado", "Ágil", 60,
                ("Movimento Repetido", "Ângulo Brusco", "Ataque e Recuo"),
                "O som chega um instante tarde.\nO movimento, não.",
            ),
            _phase(
                "evt_cdv_dobra_sem_testemunha", "Dobra sem Testemunha", "Controlador", 60,
                ("Golpe e Recuo", "Posição Imitada", "Deslocamento Inesperado"),
                "Há duas silhuetas.\nSó uma deixa marcas no chão.\n"
                "Ninguém consegue provar qual chegou primeiro.",
            ),
            _phase(
                "evt_cdv_intervalo_sem_nome", "Intervalo Sem Nome", "Equilibrado", 60,
                ("Ataque Próximo", "Ação Repetida", "Investida Repentina"),
                "O combate continua, mas o lugar parece ter parado.\n"
                "Não há voz. Não há aviso.\nApenas o intervalo entre uma coisa e outra.",
            ),
        ),
        "O silêncio termina sem resposta.\n"
        "A área volta a apresentar seus sons habituais. "
        "O que ocorreu permanece registrado como ocorrência, não como explicação.",
        attuned=True,
    ),
)


def latest_slot(now: datetime) -> datetime | None:
    """The most recent scheduled opening at or before ``now``, within a week."""
    local = now.astimezone(EVENT_TIMEZONE)
    for days_back in range(0, 8):
        day = (local - timedelta(days=days_back)).date()
        if day.weekday() not in SCHEDULE_WEEKDAYS:
            continue
        for moment in reversed(SCHEDULE_TIMES):
            slot = datetime.combine(day, moment, EVENT_TIMEZONE)
            if slot <= local:
                return slot
    return None


def next_slot(now: datetime) -> datetime:
    """The first scheduled opening strictly after ``now``."""
    local = now.astimezone(EVENT_TIMEZONE)
    for days_ahead in range(0, 8):
        day = (local + timedelta(days=days_ahead)).date()
        if day.weekday() not in SCHEDULE_WEEKDAYS:
            continue
        for moment in SCHEDULE_TIMES:
            slot = datetime.combine(day, moment, EVENT_TIMEZONE)
            if slot > local:
                return slot
    raise RuntimeError("The weekly schedule always has a next opening.")


def occurrence_key(slot: datetime, version: str = "") -> str:
    """Stable per opening (and version): a restart or deploy resolves to the same row."""
    key = slot.astimezone(EVENT_TIMEZONE).strftime("%Y%m%dT%H%M")
    return f"{key}.{version}" if version else key


def definition_for_slot(
    catalog: tuple[WorldEventDefinition, ...], slot: datetime
) -> WorldEventDefinition | None:
    """Deterministic rotation, so every process picks the same Event."""
    if not catalog:
        return None
    local = slot.astimezone(EVENT_TIMEZONE)
    index = local.date().toordinal() * len(SCHEDULE_TIMES) + SCHEDULE_TIMES.index(
        local.timetz().replace(tzinfo=None)
    )
    return catalog[index % len(catalog)]


def phase_scale(participants: int) -> StatMultipliers:
    """§49.15 scaling, frozen when a phase starts."""
    count = max(1, min(int(participants), PARTICIPANT_CAP))
    attack = D(1) + min(ATTACK_SCALE_CAP, ATTACK_PER_EXTRA_PARTICIPANT * (count - 1))
    return StatMultipliers(D(count) ** HP_SCALE_EXPONENT, attack, D(1), D(1))


def boss_stats(creature: Creature, level: int, participants: int) -> CombatStats:
    """One single rounding on the final attribute (§49.6)."""
    return enemy_stats(level, BOSS_BASE, ARCHETYPE[creature.archetype], phase_scale(participants))


def boss_engine_multipliers(participants: int) -> StatMultipliers:
    """Factors over the engine's ``boss`` category, for the opening turn."""
    scale = phase_scale(participants)
    return StatMultipliers(BOSS_BASE.hp / _BOSS_CATEGORY_HP * scale.hp, scale.attack, D(1), D(1))


def contribution_points(significant_actions: int, major_contributions: int) -> int:
    return significant_actions + major_contributions * MAJOR_CONTRIBUTION_VALUE


def is_eligible(phases: int, significant_actions: int, major_contributions: int) -> bool:
    """§21: one hit and leaving is not enough."""
    return (
        phases >= ELIGIBILITY_MIN_PHASES
        and contribution_points(significant_actions, major_contributions) >= ELIGIBILITY_MIN_ACTIONS
    )


def reward_bundle(reference_level: int) -> Bundle:
    return Bundle(
        crowns=round_10(CROWN_MULTIPLIER * crowns_per_level(reference_level)),
        basics=REWARD_BASICS,
        fragments=REWARD_FRAGMENTS,
    )


def reward_xp(level_requirement: int) -> int:
    """``FixedPercentXP`` from §49.7."""
    return int((D(level_requirement) * XP_PERCENT).to_integral_value(rounding="ROUND_HALF_UP"))


def attuned_level(player_level: int, event_level: int) -> int:
    """§49.15: ``Lsync = min(Ljogador, Levento + 5)``."""
    return min(player_level, min(60, event_level + ATTUNEMENT_LEVEL_MARGIN))


def attuned_equipment(
    equipment: EquipmentConfigurationSnapshot, level: int
) -> EquipmentConfigurationSnapshot:
    """Flat Equipment parcels above ``level`` follow the G curve; the rest stays."""
    items = []
    target = growth(level)
    for item in equipment.items:
        if item.item_level <= level:
            items.append(item)
            continue
        factor = target / growth(item.item_level)
        items.append(replace(item, core=tuple((key, value * factor) for key, value in item.core)))
    return replace(equipment, items=tuple(items))
