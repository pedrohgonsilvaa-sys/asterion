"""Juramento da Guilda (GDD v1.6.0 §22.1, §49.15).

Windows, limits, thresholds and rewards come from §49.15. The source does not say
what a Provação contains; the author decided on 2026-11-09:

- a Provação is three combats in a row (Elite, Elite, Chefe), using the Masmorra
  group scaling, with HP carried between them;
- C, básicos and Fragmentos use each character's own level, snapshotted when the
  character binds to the cycle; enemies use the group's average level.

``OATH_TRIAL_CATALOG`` comes from ``ASTERION_PROVACOES_JURAMENTO_IMPLEMENTACAO_v1_1_0.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from asterion.domain.combat_math import CombatStats, StatMultipliers, enemy_stats
from asterion.domain.dungeons import catalyst_material_id, rune_grade
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import REGION_SUPPLY, Bundle
from asterion.domain.pve_kits import (
    AGI,
    AOE,
    ATK,
    BARRIER,
    DEF,
    HEALING,
    MULTI_HIT,
    PER,
    PREPARED,
    SIMPLE,
    STRONG,
    KitAction,
    debuff,
    kit_creature,
)
from asterion.domain.road import ARCHETYPE, CATEGORY, VARIANTS, Creature

D = Decimal

OATH_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RULESET = "oath_v1"

# Monday is 0: sexta-feira.
OPENING_WEEKDAY = 4
OPENING_TIME = time(18, 0)
WINDOW = timedelta(hours=48)
GRACE = timedelta(minutes=30)
# Implementation choice, same limit as the Road's group combat: a roster that
# stops playing must not hold its members' Foreground until the grace period.
ATTEMPT_INACTIVITY = timedelta(minutes=30)

PROVACOES_PER_CYCLE = 3
MAX_GROUP_SIZE = 4
STAGE_COUNT = 3
STAGE_POINTS = (10, 15, 20)
CONCLUSION_POINTS = 15
MAX_INDIVIDUAL_CONTRIBUTION = 180
MIN_INDIVIDUAL_CONTRIBUTION = 60
TIER_THRESHOLDS = (120, 300, 540, 780)
TREASURY_BY_TIER = (2_000, 4_000, 7_000, 10_000)

# §49.6, Masmorra group scaling.
GROUP_HP_STEP = D("0.78")
GROUP_ATTACK_STEP = D("0.07")
BOSS_BASE = StatMultipliers(D("3.00"), D("1.10"), D("1.10"), D("1.00"))
ELITE_BASE = CATEGORY["elite"]
_BOSS_CATEGORY_HP = CATEGORY["boss"].hp


@dataclass(frozen=True, slots=True)
class IndividualReward:
    crown_multiplier: Decimal
    basics: int
    fragments: int
    catalysts: int


REWARD_BY_TIER = (
    IndividualReward(D("0.50"), 4, 0, 0),
    IndividualReward(D("0.75"), 6, 1, 0),
    IndividualReward(D("1.00"), 8, 2, 1),
    IndividualReward(D("1.25"), 10, 3, 1),
)


@dataclass(frozen=True, slots=True)
class OathEncounter:
    creature: Creature
    flavor: str
    # A §49.6 Variant on the global stats only, e.g. "agile".
    variant: str | None = None


@dataclass(frozen=True, slots=True)
class OathTrialDefinition:
    trial_id: str
    name: str
    encounters: tuple[OathEncounter, ...]
    conclusion_flavor: str

    def __post_init__(self) -> None:
        if len(self.encounters) != STAGE_COUNT:
            raise ValueError("A Provação has exactly three combats.")
        categories = tuple(encounter.creature.category for encounter in self.encounters)
        if categories != ("elite", "elite", "boss"):
            raise ValueError("A Provação is Elite, Elite and Chefe.")

    def encounter(self, stage: int) -> OathEncounter:
        return self.encounters[stage - 1]


OATH_TRIAL_CATALOG: tuple[OathTrialDefinition, ...] = (
    OathTrialDefinition(
        'oath.ultima_guarda',
        'O Juramento da Última Guarda',
        (
            OathEncounter(
                kit_creature(
                    'oath.ultima_guarda.sentinela_portao',
                    'O Sentinela do Portão',
                    'elite',
                    'armored',
                    (
                        KitAction(
                            'ordem_permanencia',
                            'Ordem de Permanência',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'guarda_portao',
                            'Guarda do Portão',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'golpe_contencao',
                            'Golpe de Contenção',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('travar_passagem', 'Travar Passagem', SIMPLE),
                    ),
                ),
                (
                    'O portão não precisa ser forte. Precisa apenas encontrar alguém disposto a '
                    'permanecer diante dele.'
                ),
            ),
            OathEncounter(
                kit_creature(
                    'oath.ultima_guarda.guarda_relevo',
                    'A Guarda sem Relevo',
                    'elite',
                    'controller',
                    (
                        KitAction(
                            'chamado_revezamento',
                            'Chamado do Revezamento',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'interdicao',
                            'Interdição',
                            STRONG,
                            cooldown=3,
                            **debuff(AGI, 10),
                        ),
                        KitAction(
                            'linha_vigilia',
                            'Linha de Vigília',
                            AOE,
                            cooldown=3,
                            **debuff(ATK, 10),
                            group_only=True,
                        ),
                        KitAction('marcar_chao', 'Marcar o Chão', SIMPLE),
                    ),
                ),
                'O primeiro guardava uma porta. O segundo guardava o espaço entre vocês.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.ultima_guarda.ultimo_fica',
                    'O Último que Fica',
                    'boss',
                    'brute',
                    (
                        KitAction(
                            'fim_vigilia',
                            'Fim da Vigília',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction(
                            'nao_recuarei',
                            'Não Recuarei',
                            BARRIER,
                            cooldown=4,
                            hp_at_most=D("0.50"),
                        ),
                        KitAction(
                            'avancar_alivio',
                            'Avançar sem Alívio',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'golpe_sentinela',
                            'Golpe da Sentinela',
                            AOE,
                            cooldown=3,
                            group_only=True,
                        ),
                        KitAction('ultima_guarda', 'Última Guarda', SIMPLE),
                    ),
                ),
                (
                    'Quando o último guardião caiu, não havia nada atrás dele. Talvez esse tenha '
                    'sido o motivo de ele ter permanecido.'
                ),
            ),
        ),
        'O Juramento continua depois que a testemunha desaparece.',
    ),
    OathTrialDefinition(
        'oath.peso_compartilhado',
        'O Juramento do Peso Compartilhado',
        (
            OathEncounter(
                kit_creature(
                    'oath.peso_compartilhado.carregador_partido',
                    'O Carregador Partido',
                    'elite',
                    'brute',
                    (
                        KitAction('retomar_carga', 'Retomar a Carga', PREPARED, cooldown=4),
                        KitAction('arrasto', 'Arrasto', STRONG, cooldown=3, **debuff(AGI, 10)),
                        KitAction('soltar_peso', 'Soltar o Peso', AOE, cooldown=3, group_only=True),
                        KitAction('impacto_carga', 'Impacto de Carga', SIMPLE),
                    ),
                ),
                'Ele não parecia forte. Parecia acostumado.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.peso_compartilhado.distribuidora',
                    'A Distribuidora',
                    'elite',
                    'controller',
                    (
                        KitAction(
                            'compensacao',
                            'Compensação',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'carga_cruzada',
                            'Carga Cruzada',
                            STRONG,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction(
                            'equilibrio_forcado',
                            'Equilíbrio Forçado',
                            AOE,
                            cooldown=3,
                            **debuff(DEF, 10),
                            group_only=True,
                        ),
                        KitAction('redistribuir_pressao', 'Redistribuir Pressão', SIMPLE),
                    ),
                ),
                'O peso não aumentou. Vocês apenas começaram a percebê-lo.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.peso_compartilhado.peso_permanece',
                    'O Peso que Permanece',
                    'boss',
                    'armored',
                    (
                        KitAction(
                            'tudo_cai',
                            'Tudo Cai',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction(
                            'contrapeso',
                            'Contrapeso',
                            BARRIER,
                            cooldown=4,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'peso_repartido',
                            'Peso Repartido',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'sobrecarga',
                            'Sobrecarga',
                            AOE,
                            cooldown=3,
                            **debuff(ATK, 10),
                            group_only=True,
                        ),
                        KitAction('carga_total', 'Carga Total', SIMPLE),
                    ),
                ),
                (
                    'Quando o peso desapareceu, ninguém comemorou. Todos perceberam quanto tempo '
                    'haviam confundido carregar com suportar.'
                ),
            ),
        ),
        'Algumas cargas só deixam de ser fardos quando deixam de pertencer a uma pessoa só.',
    ),
    OathTrialDefinition(
        'oath.linha_rompida',
        'O Juramento da Linha Rompida',
        (
            OathEncounter(
                kit_creature(
                    'oath.linha_rompida.abre_linha',
                    'O Que Abre a Linha',
                    'elite',
                    'predator',
                    (
                        KitAction('retorno_imediato', 'Retorno Imediato', PREPARED, cooldown=4),
                        KitAction(
                            'passagem_forcada',
                            'Passagem Forçada',
                            STRONG,
                            cooldown=2,
                            **debuff(AGI, 10),
                        ),
                        KitAction(
                            'pressao_lateral',
                            'Pressão Lateral',
                            AOE,
                            cooldown=3,
                            group_only=True,
                        ),
                        KitAction('rasgo_formacao', 'Rasgo de Formação', SIMPLE),
                    ),
                ),
                'Não foi o primeiro golpe que separou a linha. Foi o segundo passo.',
                variant='agile',
            ),
            OathEncounter(
                kit_creature(
                    'oath.linha_rompida.aquele_explora_falha',
                    'Aquele que Explora a Falha',
                    'elite',
                    'controller',
                    (
                        KitAction('fechar_cerco', 'Fechar o Cerco', PREPARED, cooldown=4),
                        KitAction(
                            'aproveitar_abertura',
                            'Aproveitar Abertura',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'cortar_retorno',
                            'Cortar Retorno',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                            group_only=True,
                        ),
                        KitAction('fissura_marcada', 'Fissura Marcada', SIMPLE),
                    ),
                ),
                'O segundo não precisava abrir a linha. Só precisava esperar.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.linha_rompida.rompedor_formacao',
                    'O Rompedor de Formação',
                    'boss',
                    'controller',
                    (
                        KitAction(
                            'linha_quebrada',
                            'Linha Quebrada',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction(
                            'linha_fixa',
                            'Linha Fixa',
                            BARRIER,
                            cooldown=4,
                            hp_at_most=D("0.50"),
                        ),
                        KitAction(
                            'deslocamento_brutal',
                            'Deslocamento Brutal',
                            STRONG,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction(
                            'quebra_eixo',
                            'Quebra de Eixo',
                            AOE,
                            cooldown=3,
                            **debuff(DEF, 10),
                            group_only=True,
                        ),
                        KitAction('fratura_central', 'Fratura Central', SIMPLE),
                    ),
                ),
                (
                    'Uma linha pode ser quebrada sem que ninguém desapareça. O Juramento existe '
                    'para decidir o que acontece depois.'
                ),
            ),
        ),
        'Permanecer unido nunca significou permanecer imóvel.',
    ),
    OathTrialDefinition(
        'oath.nome_mantido',
        'O Juramento do Nome Mantido',
        (
            OathEncounter(
                kit_creature(
                    'oath.nome_mantido.esquecedor_marcas',
                    'O Esquecedor de Marcas',
                    'elite',
                    'controller',
                    (
                        KitAction('repeticao_origem', 'Repetição sem Origem', PREPARED, cooldown=4),
                        KitAction(
                            'nome_vazio',
                            'Nome Vazio',
                            STRONG,
                            cooldown=3,
                            **debuff(PER, 10),
                        ),
                        KitAction(
                            'rasura',
                            'Rasura',
                            AOE,
                            cooldown=3,
                            **debuff(ATK, 10),
                            group_only=True,
                        ),
                        KitAction('apagar_marca', 'Apagar Marca', SIMPLE),
                    ),
                ),
                'O problema não era esquecer. Era começar a chamar outra coisa pelo mesmo nome.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.nome_mantido.reescritor',
                    'O Reescritor',
                    'elite',
                    'controller',
                    (
                        KitAction('correcao_forcada', 'Correção Forçada', PREPARED, cooldown=4),
                        KitAction(
                            'versao_anterior',
                            'Versão Anterior',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'contradicao',
                            'Contradição',
                            AOE,
                            cooldown=3,
                            **debuff(PER, 10),
                            group_only=True,
                        ),
                        KitAction('substituir_registro', 'Substituir Registro', SIMPLE),
                    ),
                ),
                'Primeiro apagaram a marca. Depois ofereceram outra no lugar.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.nome_mantido.nome_nao_cede',
                    'O Nome que Não Cede',
                    'boss',
                    'controller',
                    (
                        KitAction(
                            'permanece',
                            'O Que Permanece',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction(
                            'segundo_nome',
                            'Sem Segundo Nome',
                            BARRIER,
                            cooldown=4,
                            hp_at_most=D("0.50"),
                        ),
                        KitAction(
                            'recusar_substituicao',
                            'Recusar a Substituição',
                            STRONG,
                            cooldown=3,
                            **debuff(PER, 10),
                        ),
                        KitAction(
                            'marca_persistente',
                            'Marca Persistente',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                            group_only=True,
                        ),
                        KitAction('nomear_erro', 'Nomear o Erro', SIMPLE),
                    ),
                ),
                (
                    'O Nome não foi recuperado. Foi mantido. E talvez essa diferença seja o que um'
                    ' Juramento realmente exige.'
                ),
            ),
        ),
        'Um compromisso permanece quando a memória já não oferece uma resposta fácil.',
    ),
    OathTrialDefinition(
        'oath.preco',
        'O Juramento do Preço',
        (
            OathEncounter(
                kit_creature(
                    'oath.preco.cobrador',
                    'O Cobrador',
                    'elite',
                    'balanced',
                    (
                        KitAction('saldo_aberto', 'Saldo Aberto', PREPARED, cooldown=4),
                        KitAction('juros', 'Juros', STRONG, cooldown=3, **debuff(ATK, 10)),
                        KitAction(
                            'retencao',
                            'Retenção',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                            group_only=True,
                        ),
                        KitAction('cobranca', 'Cobrança', SIMPLE),
                    ),
                ),
                'O preço nunca foi alto. Apenas nunca foi zero.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.preco.penhorista',
                    'O Penhorista',
                    'elite',
                    'controller',
                    (
                        KitAction('oferta_recusada', 'Oferta Recusada', PREPARED, cooldown=4),
                        KitAction(
                            'tomar_garantia',
                            'Tomar em Garantia',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'devolver_custo',
                            'Devolver com Custo',
                            AOE,
                            cooldown=3,
                            **debuff(HEALING, 15),
                            group_only=True,
                        ),
                        KitAction('penhor', 'Penhor', SIMPLE),
                    ),
                ),
                (
                    'Quando tudo tem preço, a dificuldade deixa de ser pagar. É decidir o que vale'
                    ' ser preservado.'
                ),
            ),
            OathEncounter(
                kit_creature(
                    'oath.preco.credor_fim',
                    'O Credor do Fim',
                    'boss',
                    'brute',
                    (
                        KitAction(
                            'preco_final',
                            'Preço Final',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction('troco', 'Sem Troco', STRONG, cooldown=3, **debuff(ATK, 10)),
                        KitAction(
                            'cobranca_fracionada',
                            'Cobrança Fracionada',
                            MULTI_HIT,
                            cooldown=3,
                        ),
                        KitAction(
                            'conta_fechada',
                            'Conta Fechada',
                            AOE,
                            cooldown=3,
                            **debuff(HEALING, 15),
                            group_only=True,
                        ),
                        KitAction('cobrar_tudo', 'Cobrar Tudo', SIMPLE),
                    ),
                ),
                (
                    'O preço não estava escondido. Ele estava em cada escolha que vocês fizeram '
                    'antes de chegar aqui.'
                ),
            ),
        ),
        (
            'Toda decisão deixa uma marca. O Juramento apenas impede que vocês finjam que ela não '
            'existe.'
        ),
    ),
    OathTrialDefinition(
        'oath.que_permanece',
        'O Juramento que Permanece',
        (
            OathEncounter(
                kit_creature(
                    'oath.que_permanece.persistente',
                    'O Persistente',
                    'elite',
                    'armored',
                    (
                        KitAction('passo_inevitavel', 'Passo Inevitável', PREPARED, cooldown=4),
                        KitAction(
                            'guarda_desgastada',
                            'Guarda Desgastada',
                            BARRIER,
                            cooldown=3,
                            hp_at_most=D("0.60"),
                        ),
                        KitAction(
                            'reerguer_se',
                            'Reerguer-se',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction('persistir', 'Persistir', SIMPLE),
                    ),
                ),
                'Ele não precisava acreditar. Só precisava continuar.',
            ),
            OathEncounter(
                kit_creature(
                    'oath.que_permanece.ultimo_fiel',
                    'O Último Fiel',
                    'elite',
                    'balanced',
                    (
                        KitAction(
                            'continuar_mesmo_assim',
                            'Continuar Mesmo Assim',
                            PREPARED,
                            cooldown=4,
                        ),
                        KitAction(
                            'resposta_fiel',
                            'Resposta Fiel',
                            STRONG,
                            cooldown=3,
                            **debuff(ATK, 10),
                        ),
                        KitAction(
                            'atalho',
                            'Sem Atalho',
                            AOE,
                            cooldown=3,
                            **debuff(AGI, 10),
                            group_only=True,
                        ),
                        KitAction('retomar_posicao', 'Retomar Posição', SIMPLE),
                    ),
                ),
                (
                    'Continuar não significava fazer a mesma coisa. Significava não abandonar o '
                    'propósito.'
                ),
            ),
            OathEncounter(
                kit_creature(
                    'oath.que_permanece.juramento_permanece',
                    'O Juramento que Permanece',
                    'boss',
                    'balanced',
                    (
                        KitAction(
                            'ainda_pe',
                            'Ainda de Pé',
                            PREPARED,
                            cooldown=5,
                            hp_at_most=D("0.35"),
                        ),
                        KitAction(
                            'recusar_queda',
                            'Recusar a Queda',
                            BARRIER,
                            cooldown=4,
                            hp_at_most=D("0.50"),
                        ),
                        KitAction(
                            'resposta_proposito',
                            'Resposta ao Propósito',
                            STRONG,
                            cooldown=3,
                            **debuff(DEF, 10),
                        ),
                        KitAction(
                            'recomeco',
                            'Sem Recomeço',
                            AOE,
                            cooldown=3,
                            **debuff(ATK, 10),
                            group_only=True,
                        ),
                        KitAction('permanecer', 'Permanecer', SIMPLE),
                    ),
                ),
                (
                    'Um Juramento não prova seu valor quando tudo dá certo. Prova quando ainda '
                    'existe alguém disposto a cumpri-lo depois que o motivo mais fácil para '
                    'continuar desapareceu.'
                ),
            ),
        ),
        'O compromisso não terminou. Só perdeu a justificativa mais fácil.',
    ),
)


def latest_opening(now: datetime) -> datetime:
    """The most recent Friday 18:00 at or before ``now``."""
    local = now.astimezone(OATH_TIMEZONE)
    for days_back in range(0, 8):
        day = (local - timedelta(days=days_back)).date()
        if day.weekday() != OPENING_WEEKDAY:
            continue
        slot = datetime.combine(day, OPENING_TIME, OATH_TIMEZONE)
        if slot <= local:
            return slot
    raise RuntimeError("The weekly schedule always has a previous opening.")


def next_opening(now: datetime) -> datetime:
    """The first Friday 18:00 strictly after ``now``."""
    local = now.astimezone(OATH_TIMEZONE)
    for days_ahead in range(0, 9):
        day = (local + timedelta(days=days_ahead)).date()
        if day.weekday() != OPENING_WEEKDAY:
            continue
        slot = datetime.combine(day, OPENING_TIME, OATH_TIMEZONE)
        if slot > local:
            return slot
    raise RuntimeError("The weekly schedule always has a next opening.")


def cycle_key(opening: datetime) -> str:
    """Stable per opening: a restart or deploy resolves to the same cycle."""
    return opening.astimezone(OATH_TIMEZONE).strftime("%Y%m%d")


def definition_for_opening(
    catalog: tuple[OathTrialDefinition, ...], opening: datetime
) -> OathTrialDefinition | None:
    """Deterministic rotation, so every process picks the same Provação."""
    if not catalog:
        return None
    week = opening.astimezone(OATH_TIMEZONE).date().toordinal() // 7
    return catalog[week % len(catalog)]


def group_scale(roster_size: int) -> StatMultipliers:
    if not 1 <= roster_size <= MAX_GROUP_SIZE:
        raise ValueError("A Provação has one to four participants.")
    extra = roster_size - 1
    return StatMultipliers(
        D(1) + GROUP_HP_STEP * extra, D(1) + GROUP_ATTACK_STEP * extra, D(1), D(1)
    )


def enemy_level(levels: tuple[int, ...]) -> int:
    """The group's average level."""
    if not levels:
        raise ValueError("A Provação needs at least one participant.")
    average = D(sum(levels)) / D(len(levels))
    return int(average.to_integral_value(rounding=ROUND_HALF_UP))


def encounter_stats(
    creature: Creature, level: int, roster_size: int, variant: str | None = None
) -> CombatStats:
    """One single rounding on the final attribute (§49.6)."""
    base = BOSS_BASE if creature.category == "boss" else ELITE_BASE
    factors = [base, ARCHETYPE[creature.archetype]]
    if variant is not None:
        factors.append(VARIANTS[variant])
    return enemy_stats(level, *factors, group_scale(roster_size))


def engine_multipliers(creature: Creature, roster_size: int) -> StatMultipliers:
    """Factors over the engine's creature category, for the opening turn."""
    scale = group_scale(roster_size)
    if creature.category != "boss":
        return scale
    return StatMultipliers(BOSS_BASE.hp / _BOSS_CATEGORY_HP * scale.hp, scale.attack, D(1), D(1))


def stage_milestones(stage: int) -> tuple[tuple[str, int], ...]:
    """Milestones earned by winning ``stage``; the last one also concludes the Provação."""
    milestones = [(f"stage_{stage}", STAGE_POINTS[stage - 1])]
    if stage == STAGE_COUNT:
        milestones.append(("conclusion", CONCLUSION_POINTS))
    return tuple(milestones)


def tier_for(contribution: int) -> int:
    """The highest tier reached; 0 means no minimum tier was reached."""
    return sum(1 for threshold in TIER_THRESHOLDS if contribution >= threshold)


def next_threshold(contribution: int) -> int | None:
    return next((value for value in TIER_THRESHOLDS if contribution < value), None)


def treasury_reward(tier: int) -> int:
    return TREASURY_BY_TIER[tier - 1] if tier else 0


def is_eligible(contribution: int) -> bool:
    return contribution >= MIN_INDIVIDUAL_CONTRIBUTION


def region_for_level(level: int) -> str:
    """Fragment grades and Regions advance together, every ten levels."""
    return tuple(REGION_SUPPLY)[rune_grade(level) - 1]


def reward_bundle(level: int, tier: int) -> Bundle:
    reward = REWARD_BY_TIER[tier - 1]
    return Bundle(
        crowns=round_10(reward.crown_multiplier * crowns_per_level(level)),
        basics=reward.basics,
        fragments=reward.fragments,
    )


def reward_catalysts(tier: int) -> int:
    return REWARD_BY_TIER[tier - 1].catalysts


def reward_catalyst_id(level: int) -> str:
    return catalyst_material_id(level)
