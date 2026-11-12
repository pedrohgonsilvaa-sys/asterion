"""Eventos Mundiais e Sintonização do Véu (GDD v1.6.0 §21, §21.1, §49.15).

Every number below comes from §49.15, except the ones marked as author decisions
(2026-11-08): the source does not define them.

``WORLD_EVENT_CATALOG`` comes from ``ASTERION_EVENTOS_PUBLICOS_IMPLEMENTACAO_v1_1_0.md``.
Author decisions (2026-11-12), since each player fights the boss in their own instance:
the AoE actions drop the "2+ alvos válidos" condition, and O Trançador de Ossos, whose
sheet has no Simples action, uses Arrasto Cruzado as fallback (no Recarga, no condition).
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
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import Bundle
from asterion.domain.equipment_stats import EquipmentConfigurationSnapshot
from asterion.domain.pve_kits import (
    AGI,
    AOE,
    ATK,
    BARRIER,
    BLEED,
    BURN,
    DEF,
    DOT,
    HEALING,
    PER,
    PREPARED,
    SIMPLE,
    STRONG,
    KitAction,
    debuff,
    kit_creature,
)
from asterion.domain.road import ARCHETYPE, VARIANTS, Creature

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
    # A §49.6 Variant on the global stats only, e.g. "agile".
    variant: str | None = None


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


WORLD_EVENT_CATALOG: tuple[WorldEventDefinition, ...] = (
    WorldEventDefinition(
        'evt_tdo_cerco_das_cinzas',
        'O Cerco das Cinzas',
        'Terras do Ocaso',
        10,
        (
            WorldEventPhase(
                kit_creature(
                    'event.tdo_cerco_das_cinzas.cortador_marcos',
                    'O Cortador de Marcos',
                    'boss',
                    'predator',
                    (
                        KitAction('quebra_passagem', 'Quebra de Passagem', PREPARED, cooldown=4),
                        KitAction(
                            'rasgo_rota',
                            'Rasgo de Rota',
                            STRONG,
                            cooldown=2,
                            **debuff(AGI, 10),
                        ),
                        KitAction('passagem_lateral', 'Passagem Lateral', AOE, cooldown=3),
                        KitAction('corte_marco', 'Corte de Marco', SIMPLE),
                    ),
                ),
                (
                    'Os primeiros sinais do cerco não são gritos. São marcos de estrada tombando '
                    'um após o outro.'
                ),
                variant='agile',
            ),
            WorldEventPhase(
                kit_creature(
                    'event.tdo_cerco_das_cinzas.arrastador_fornalha',
                    'O Arrastador de Fornalha',
                    'boss',
                    'armored',
                    (
                        KitAction(
                            'investida_fornalha',
                            'Investida de Fornalha',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'muralha_cinza',
                            'Muralha de Cinza',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'golpe_incandescente',
                            'Golpe Incandescente',
                            STRONG,
                            cooldown=2,
                            dot=BURN,
                        ),
                        KitAction('arrasto_fornalha', 'Arrasto de Fornalha', SIMPLE),
                    ),
                ),
                (
                    'A estrada começa a escurecer quando o inimigo puxa uma fornalha ainda acesa '
                    'para dentro da passagem.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.tdo_cerco_das_cinzas.quebrador_ultimo_marco',
                    'O Quebrador do Último Marco',
                    'boss',
                    'brute',
                    (
                        KitAction(
                            'investida_final',
                            'Investida Final',
                            PREPARED,
                            cooldown=4,
                            hp_at_most=D("0.40"),
                        ),
                        KitAction(
                            'golpe_demolicao',
                            'Golpe de Demolição',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('avanco_cinzas', 'Avanço de Cinzas', AOE, cooldown=3),
                        KitAction('golpe_ultimo_marco', 'Golpe do Último Marco', SIMPLE),
                    ),
                ),
                (
                    'O último marco cai. O que resta da estrada precisa ser defendido sem qualquer'
                    ' sinal para guiá-los.'
                ),
            ),
        ),
        (
            'O cerco termina quando o último marco já não existe. A estrada permanece, mas agora '
            'depende de quem aprendeu a atravessá-la sem sinais para guiá-los.'
        ),
        attuned=True,
    ),
    WorldEventDefinition(
        'evt_vales_raiz_que_puxa',
        'A Raiz que Puxa',
        'Vales dos Enforcados',
        20,
        (
            WorldEventPhase(
                kit_creature(
                    'event.vales_raiz_que_puxa.escavador_lacos',
                    'O Escavador de Laços',
                    'boss',
                    'balanced',
                    (
                        KitAction('mergulho_laco', 'Mergulho de Laço', PREPARED, cooldown=4),
                        KitAction(
                            'puxao_raiz',
                            'Puxão de Raiz',
                            STRONG,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction('rasgo_solo', 'Rasgo de Solo', AOE, cooldown=3),
                        KitAction('escavacao_laco', 'Escavação de Laço', SIMPLE),
                    ),
                ),
                (
                    'A terra se move antes que qualquer coisa apareça. Quando a primeira raiz '
                    'rompe a superfície, alguém já foi marcado.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.vales_raiz_que_puxa.trancador_ossos',
                    'O Trançador de Ossos',
                    'boss',
                    'controller',
                    (
                        KitAction(
                            'aprisionamento_preparado',
                            'Aprisionamento Preparado',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction('tranca_ossos', 'Trança de Ossos', DOT, cooldown=2, dot=BLEED),
                        KitAction('imovel', 'Nó Imóvel', STRONG, cooldown=3, **debuff(AGI, 15)),
                        KitAction(
                            'arrasto_cruzado',
                            'Arrasto Cruzado',
                            AOE,
                            **debuff(DEF, 10),
                            conditional=False,
                        ),
                    ),
                ),
                (
                    'As raízes não crescem sozinhas. Algo está usando restos antigos para dar '
                    'forma ao que prende os vivos.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.vales_raiz_que_puxa.caminha',
                    'O Nó que Caminha',
                    'boss',
                    'brute',
                    (
                        KitAction(
                            'quebra_raiz',
                            'Quebra de Raiz',
                            PREPARED,
                            cooldown=4,
                            hp_at_most=D("0.40"),
                        ),
                        KitAction(
                            'aperto_convergente',
                            'Aperto Convergente',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'arrasto_coletivo',
                            'Arrasto Coletivo',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction('passo', 'Passo do Nó', SIMPLE),
                    ),
                ),
                (
                    'O emaranhado deixa de estar preso ao chão e começa a caminhar em direção ao '
                    'grupo.'
                ),
            ),
        ),
        (
            'Quando o nó se desfaz, as raízes permanecem. O vale não ficou mais seguro; apenas '
            'voltou a lembrar que ainda tem chão.'
        ),
        attuned=True,
    ),
    WorldEventDefinition(
        'evt_nareth_campo_que_nao_devolve',
        'O Campo que Não Devolve',
        'Planícies de Nareth',
        30,
        (
            WorldEventPhase(
                kit_creature(
                    'event.nareth_campo_que_nao_devolve.contador_passagens',
                    'O Contador de Passagens',
                    'boss',
                    'balanced',
                    (
                        KitAction('retorno_ponto', 'Retorno ao Ponto', PREPARED, cooldown=4),
                        KitAction(
                            'registro_alvo',
                            'Registro de Alvo',
                            STRONG,
                            cooldown=3,
                            **debuff(PER, 10),
                        ),
                        KitAction('correcao_rota', 'Correção de Rota', AOE, cooldown=3),
                        KitAction('contagem_passagem', 'Contagem de Passagem', SIMPLE),
                    ),
                ),
                (
                    'O inimigo não ataca primeiro. Ele observa cada passagem e parece registrar '
                    'quem já cruzou o campo.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.nareth_campo_que_nao_devolve.recolhedor_vazio',
                    'O Recolhedor Vazio',
                    'boss',
                    'armored',
                    (
                        KitAction(
                            'retencao_passagem',
                            'Retenção de Passagem',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'caixa_vazia',
                            'Caixa Vazia',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'avanco_pesado',
                            'Avanço Pesado',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('recolha_vestigio', 'Recolha de Vestígio', SIMPLE),
                    ),
                ),
                (
                    'Objetos deixados no campo desaparecem quando chegam perto dele. Não há sinal '
                    'do que acontece depois.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.nareth_campo_que_nao_devolve.lavrador_ausencias',
                    'O Lavrador de Ausências',
                    'boss',
                    'controller',
                    (
                        KitAction(
                            'repeticao_caminho',
                            'Repetição de Caminho',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'sulco_ausencia',
                            'Sulco de Ausência',
                            STRONG,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction(
                            'campo_negado',
                            'Campo Negado',
                            AOE,
                            cooldown=3,
                            **debuff(PER, 10),
                        ),
                        KitAction('sinal_sulco', 'Sinal de Sulco', SIMPLE),
                    ),
                ),
                'As marcas no chão formam linhas onde ninguém deveria ter passado.',
            ),
        ),
        (
            'O campo não devolve o que toma. A única certeza é que algumas passagens continuam '
            'sendo registradas.'
        ),
        attuned=True,
    ),
    WorldEventDefinition(
        'evt_varzeas_agua_vermelha',
        'A Água Vermelha',
        'Várzeas Carmesins',
        40,
        (
            WorldEventPhase(
                kit_creature(
                    'event.varzeas_agua_vermelha.carregador_reservas',
                    'O Carregador de Reservas',
                    'boss',
                    'balanced',
                    (
                        KitAction(
                            'sobrecarga_reservatorio',
                            'Sobrecarga do Reservatório',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'descarga_controlada',
                            'Descarga Controlada',
                            STRONG,
                            cooldown=2,
                            dot=BURN,
                        ),
                        KitAction('avanco_tanque', 'Avanço de Tanque', AOE, cooldown=3),
                        KitAction('transporte_reserva', 'Transporte de Reserva', SIMPLE),
                    ),
                ),
                (
                    'A água sobe entre estruturas antigas enquanto alguma coisa transporta '
                    'recipientes que ainda não deveriam estar cheios.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.varzeas_agua_vermelha.operador_membranas',
                    'O Operador de Membranas',
                    'boss',
                    'controller',
                    (
                        KitAction('ruptura_conduto', 'Ruptura de Conduto', PREPARED, cooldown=4),
                        KitAction(
                            'vedacao_local',
                            'Vedação Local',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'pressao_membrana',
                            'Pressão de Membrana',
                            STRONG,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction('golpe_membrana', 'Golpe de Membrana', SIMPLE),
                    ),
                ),
                (
                    'O operador não parece lutar contra o grupo. Parece tentar manter uma '
                    'instalação funcionando apesar dele.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.varzeas_agua_vermelha.triador_emergencia',
                    'O Triador de Emergência',
                    'boss',
                    'brute',
                    (
                        KitAction(
                            'sobrecarga_final',
                            'Sobrecarga Final',
                            PREPARED,
                            cooldown=4,
                            hp_at_most=D("0.40"),
                        ),
                        KitAction(
                            'desvio_emergencia',
                            'Desvio de Emergência',
                            STRONG,
                            cooldown=3,
                            **debuff(HEALING, 15),
                        ),
                        KitAction('colisao_contencao', 'Colisão de Contenção', AOE, cooldown=3),
                        KitAction('triagem_brutal', 'Triagem Brutal', SIMPLE),
                    ),
                ),
                (
                    'A estrutura não distingue aliado de ameaça. Ela apenas continua decidindo o '
                    'que pode ser preservado.'
                ),
            ),
        ),
        (
            'A água baixa. Os diques permanecem. O que foi separado para sobreviver à emergência '
            'nunca volta ao mesmo lugar.'
        ),
        attuned=True,
    ),
    WorldEventDefinition(
        'evt_altos_peso_que_cede',
        'O Peso que Cede',
        'Altos Cinéreos',
        50,
        (
            WorldEventPhase(
                kit_creature(
                    'event.altos_peso_que_cede.rachador_tirantes',
                    'O Rachador de Tirantes',
                    'boss',
                    'brute',
                    (
                        KitAction('queda_escarpa', 'Queda de Escarpa', PREPARED, cooldown=4),
                        KitAction(
                            'pancada_contraforte',
                            'Pancada de Contraforte',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('ruptura_cabo', 'Ruptura de Cabo', AOE, cooldown=3),
                        KitAction('corte_tirante', 'Corte de Tirante', SIMPLE),
                    ),
                ),
                (
                    'Uma estrutura acima da estrada range. O inimigo começa pelo que parece '
                    'suportá-la.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.altos_peso_que_cede.distribuidor_peso',
                    'O Distribuidor de Peso',
                    'boss',
                    'controller',
                    (
                        KitAction(
                            'compensacao_estrutura',
                            'Compensação de Estrutura',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'pressao_cruzada',
                            'Pressão Cruzada',
                            STRONG,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction(
                            'desvio_peso',
                            'Desvio de Peso',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction('redistribuicao_carga', 'Redistribuição de Carga', SIMPLE),
                    ),
                ),
                (
                    'O problema deixa de ser derrubar a ponte e passa a ser descobrir qual parte '
                    'ainda merece ser sustentada.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.altos_peso_que_cede.sustentador_partido',
                    'O Sustentador Partido',
                    'boss',
                    'armored',
                    (
                        KitAction(
                            'queda_contida',
                            'Queda Contida',
                            PREPARED,
                            cooldown=4,
                            hp_at_most=D("0.40"),
                        ),
                        KitAction(
                            'reforco_emergencia',
                            'Reforço de Emergência',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'carga_invertida',
                            'Carga Invertida',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('guarda_contraforte', 'Guarda do Contraforte', SIMPLE),
                    ),
                ),
                'A criatura foi feita para sustentar. Agora tenta sustentar a própria ruína.',
            ),
        ),
        'O peso não desaparece. Ele apenas deixa de cair sobre a mesma estrutura.',
        attuned=True,
    ),
    WorldEventDefinition(
        'evt_confins_duas_estradas',
        'Duas Estradas para o Mesmo Lugar',
        'Confins do Véu',
        60,
        (
            WorldEventPhase(
                kit_creature(
                    'event.confins_duas_estradas.passante_duas_bordas',
                    'O Passante de Duas Bordas',
                    'boss',
                    'predator',
                    (
                        KitAction('salto_entre_bordas', 'Salto entre Bordas', PREPARED, cooldown=4),
                        KitAction(
                            'travessia_cruzada',
                            'Travessia Cruzada',
                            STRONG,
                            cooldown=2,
                            **debuff(AGI, 10),
                        ),
                        KitAction('dupla_margem', 'Dupla Margem', AOE, cooldown=3),
                        KitAction('passagem_borda', 'Passagem de Borda', SIMPLE),
                    ),
                ),
                (
                    'A primeira estrada termina no mesmo ponto em que a segunda começa. Ninguém '
                    'lembra quando as duas deixaram de ser diferentes.'
                ),
                variant='agile',
            ),
            WorldEventPhase(
                kit_creature(
                    'event.confins_duas_estradas.escrivao_desfasado',
                    'O Escrivão Desfasado',
                    'boss',
                    'controller',
                    (
                        KitAction('reescrita_final', 'Reescrita Final', PREPARED, cooldown=4),
                        KitAction(
                            'rasura_linha',
                            'Rasura de Linha',
                            STRONG,
                            cooldown=3,
                            **debuff(PER, 10),
                        ),
                        KitAction(
                            'pagina_desfasada',
                            'Página Desfasada',
                            AOE,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction('registro_incompleto', 'Registro Incompleto', SIMPLE),
                    ),
                ),
                (
                    'O registro muda enquanto é lido. A tinta parece obedecer a uma ordem que '
                    'nunca foi a mesma.'
                ),
            ),
            WorldEventPhase(
                kit_creature(
                    'event.confins_duas_estradas.retornador_incompleto',
                    'O Retornador Incompleto',
                    'boss',
                    'balanced',
                    (
                        KitAction(
                            'retorno_chegada',
                            'Retorno sem Chegada',
                            PREPARED,
                            cooldown=4,
                            hp_at_most=D("0.40"),
                        ),
                        KitAction(
                            'passo_repetido',
                            'Passo Repetido',
                            STRONG,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction('reaparicao', 'Reaparição', AOE, cooldown=3),
                        KitAction('retorno_incompleto', 'Retorno Incompleto', SIMPLE),
                    ),
                ),
                (
                    'Algo retorna sem ter terminado de partir. A repetição é pequena demais para '
                    'ser chamada de milagre.'
                ),
            ),
        ),
        (
            'As duas estradas continuam visíveis. O problema é que ambas chegam ao mesmo lugar sem'
            ' explicar por quê.'
        ),
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


def boss_stats(
    creature: Creature, level: int, participants: int, variant: str | None = None
) -> CombatStats:
    """One single rounding on the final attribute (§49.6)."""
    factors = [BOSS_BASE, ARCHETYPE[creature.archetype]]
    if variant is not None:
        factors.append(VARIANTS[variant])
    return enemy_stats(level, *factors, phase_scale(participants))


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
