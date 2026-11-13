"""Juramento da Guilda (GDD v1.6.0 §22.1, §49.15).

Windows, limits, thresholds and rewards come from §49.15. The source does not say
what a Provação contains; the author decided on 2026-11-09:

- a Provação is three combats in a row (Elite, Elite, Chefe), using the Masmorra
  group scaling, with HP carried between them;
- C, básicos and Fragmentos use each character's own level, snapshotted when the
  character binds to the cycle; enemies use the group's average level.

``OATH_TRIAL_CATALOG`` holds the eleven Provações of the author's catalog (2026-11-13).
With an empty catalog no cycle is ever created.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from asterion.domain.combat_math import CombatStats, StatMultipliers, enemy_stats
from asterion.domain.creature_kits import build_creature
from asterion.domain.dungeons import catalyst_material_id, rune_grade
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import REGION_SUPPLY, Bundle
from asterion.domain.road import ARCHETYPE, CATEGORY, Creature

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


def _fight(
    creature_id: str,
    name: str,
    category: str,
    profile: str,
    labels: tuple[str, str, str],
    flavor: str,
) -> OathEncounter:
    # The creature level comes from the group's average when the combat is built;
    # ``level`` here only fills the Creature record.
    return OathEncounter(build_creature(creature_id, name, category, profile, 1, labels), flavor)


OATH_TRIAL_CATALOG: tuple[OathTrialDefinition, ...] = (
    OathTrialDefinition(
        "jur_guardioes_do_limiar",
        "Guardiões do Limiar",
        (
            _fight(
                "jur_cao_do_limiar", "Cão do Limiar", "elite", "Ágil",
                ("Mordida Lateral", "Salto sobre Isolado", "Investida Direta"),
                "A passagem está vazia.\nO cão não.",
            ),
            _fight(
                "jur_sentinela_de_fuligem", "Sentinela de Fuligem", "elite", "Equilibrado",
                ("Golpe Endurecido", "Observação", "Investida Curta"),
                "Não guarda uma porta.\n"
                "Guarda a ideia de que alguma coisa deveria estar atrás dela.",
            ),
            _fight(
                "jur_guardiao_do_limiar", "Guardião do Limiar", "boss", "Blindado",
                ("Varredura Larga", "Placas Naturais", "Golpe no Chão"),
                "O último guardião não pergunta quem passa.\nEle apenas permanece.",
            ),
        ),
        "O limiar permanece aberto.\n"
        "Você atravessou sem receber permissão — apenas sem ser impedido.",
    ),
    OathTrialDefinition(
        "jur_peso_dos_nomes",
        "O Peso dos Nomes",
        (
            _fight(
                "jur_entalhador_enredado", "Entalhador Enredado", "elite", "Controlador",
                ("Golpe de Raízes", "Marca no Chão", "Prender e Recuar"),
                "Primeiro vem o risco na madeira.\nDepois vem a criatura.",
            ),
            _fight(
                "jur_portador_de_nomes", "Portador de Nomes", "elite", "Equilibrado",
                ("Golpe de Placa", "Troca de Alvo", "Placa Arremessada"),
                "Há nomes gravados nas placas.\nNenhum deles pertence à criatura.",
            ),
            _fight(
                "jur_arquivista_do_vale", "Arquivista do Vale", "boss", "Blindado",
                ("Golpe das Placas", "Couraça de Placas", "Varredura Pesada"),
                "O arquivo não sabe esquecer.\nTalvez seja por isso que ainda pesa tanto.",
            ),
        ),
        "Os nomes continuam legíveis.\n"
        "Isso é pouco, mas em Asterion pouco raramente significa nada.",
    ),
    OathTrialDefinition(
        "jur_medida_sem_norte",
        "A Medida sem Norte",
        (
            _fight(
                "jur_rastreador_de_horizonte", "Rastreador de Horizonte", "elite", "Ágil",
                ("Golpe e Retorno", "Ataque ao Distante", "Investida em Linha"),
                "Ele escolhe um ponto no horizonte.\nNinguém sabe qual.",
            ),
            _fight(
                "jur_escorregador_de_marco", "Escorregador de Marco", "elite", "Equilibrado",
                ("Golpe na Marca", "Mudança de Direção", "Avanço de Marco"),
                "Os marcos continuam imóveis.\nO caminho entre eles, não.",
            ),
            _fight(
                "jur_cartografo_invertido", "Cartógrafo Invertido", "boss", "Controlador",
                ("Ataque Próximo", "Percurso Desenhado", "Passagem Bloqueada"),
                "Não existe mapa em suas mãos.\n"
                "Só caminhos que deveriam estar em algum lugar.",
            ),
        ),
        "O caminho volta a parecer simples.\nPor um momento, basta seguir em frente.",
    ),
    OathTrialDefinition(
        "jur_sangue_que_permanece",
        "O Sangue que Permanece",
        (
            _fight(
                "jur_coletor_rubro", "Coletor Rubro", "elite", "Ágil",
                ("Golpe Rápido", "Mergulho Parcial", "Ataque ao Isolado"),
                "A água está parada.\nO vermelho, não.",
            ),
            _fight(
                "jur_enxerto_de_mare", "Enxerto de Maré", "elite", "Bruto",
                ("Massa Endurecida", "Detritos Sacudidos", "Investida sem Recuo"),
                "A coisa parece ter crescido onde não deveria.\n"
                "Ninguém pergunta o que a alimentou.",
            ),
            _fight(
                "jur_matriz_de_sangria", "Matriz de Sangria", "boss", "Controlador",
                ("Golpe Largo", "Extensões Espalhadas", "Avanço Lento"),
                "Não parece ferida.\nParece uma ferida que aprendeu a caminhar.",
            ),
        ),
        "A água volta a se mover.\nO vermelho permanece apenas onde sempre esteve.",
    ),
    OathTrialDefinition(
        "jur_o_que_sustenta",
        "O Que Sustenta",
        (
            _fight(
                "jur_quebra_peso", "Quebra-Peso", "elite", "Bruto",
                ("Golpe no Solo", "Placas Arrastadas", "Avanço Pesado"),
                "O primeiro som é pedra contra pedra.\nO segundo é algo respirando.",
            ),
            _fight(
                "jur_fiscal_de_escarpa", "Fiscal de Escarpa", "elite", "Equilibrado",
                ("Golpe Lateral", "Posição Central", "Empurrão"),
                "Não fiscaliza pessoas.\nFiscaliza peso.",
            ),
            _fight(
                "jur_sustentador_cinereo", "Sustentador Cinéreo", "boss", "Blindado",
                ("Varredura Larga", "Placas de Cobertura", "Golpe Firmado"),
                "Tudo ao redor parece antigo.\nO monstro parece mais antigo ainda.\n"
                "Talvez seja apenas o peso.",
            ),
        ),
        "A estrutura permanece.\n"
        "Não porque estava inteira, mas porque ainda havia alguma coisa sustentando-a.",
    ),
    OathTrialDefinition(
        "jur_testemunhas_do_veu",
        "Testemunhas do Véu",
        (
            _fight(
                "jur_cao_sem_eco", "Cão sem Eco", "elite", "Ágil",
                ("Ataque Lateral", "Alvo Afastado", "Retorno Oculto"),
                "O chão registra a pegada.\nO lugar não registra o som.",
            ),
            _fight(
                "jur_duplicante_de_margem", "Duplicante de Margem", "elite", "Controlador",
                ("Golpe Repetido", "Posição Imitada", "Troca de Lado"),
                "Há um movimento que parece familiar.\n"
                "Isso não significa que ele tenha acontecido antes.",
            ),
            _fight(
                "jur_testemunha_do_intervalo", "Testemunha do Intervalo", "boss", "Equilibrado",
                ("Ataque Curto", "Ação Repetida", "Mudança de Ritmo"),
                "Ela observa sem olhos que se possam reconhecer.\n"
                "O silêncio ao redor parece mais antigo que a criatura.\n"
                "Nada além disso pode ser afirmado.",
            ),
        ),
        "A presença desaparece sem deixar resposta.\n"
        "O Juramento registra apenas o que foi feito. "
        "O restante permanece onde estava: do outro lado do Véu.",
    ),
    OathTrialDefinition(
        "jur_cinza_que_nao_cede",
        "Cinza que Não Cede",
        (
            _fight(
                "jur_sentinela_de_cinza", "Sentinela de Cinza", "elite", "Blindado",
                ("Golpe de Cinza", "Postura de Cinza", "Queda da Armadura"),
                "A cinza se ergue como uma armadura que ainda espera uma ordem.\n"
                "O vulto não recua quando você se aproxima.",
            ),
            _fight(
                "jur_rastejante_de_fuligem", "Rastejante de Fuligem", "elite", "Ágil",
                ("Mordida Baixa", "Corte Rastejante", "Salto de Fuligem"),
                "Algo baixo demais para ser visto de frente corre entre as cinzas.\n"
                "Só os movimentos rápidos denunciam onde ele está.",
            ),
            _fight(
                "jur_coroa_de_escoria", "Coroa de Escória", "boss", "Bruto",
                ("Golpe de Escória", "Brasa Rachada", "Desabamento de Escória"),
                "A massa escura se levanta como um monte de restos que recusou "
                "permanecer imóvel.\nO calor dela não ilumina nada.",
            ),
        ),
        "A cinza finalmente baixa.\n"
        "O Juramento reconhece que você permaneceu de pé quando tudo ao redor queria ruir.",
    ),
    OathTrialDefinition(
        "jur_raizes_sem_sepultura",
        "Raízes sem Sepultura",
        (
            _fight(
                "jur_mastigador_de_raiz", "Mastigador de Raiz", "elite", "Bruto",
                ("Mordida de Raiz", "Raiz Cortante", "Esmagar com Raízes"),
                "Raízes grossas se movem sob uma carcaça torta de madeira e carne.\n"
                "O chão parece respirar antes do primeiro golpe.",
            ),
            _fight(
                "jur_tecela_do_musgo_negro", "Tecelã do Musgo Negro", "elite", "Controlador",
                ("Toque de Musgo", "Esporos Negros", "Teia de Musgo"),
                "O musgo cobre a criatura como um véu pesado.\n"
                "Quando ela se move, folhas antigas se desfazem de seus membros.",
            ),
            _fight(
                "jur_raiz_do_juramento", "Raiz do Juramento", "boss", "Equilibrado",
                ("Golpe de Raiz", "Marca na Terra", "Raiz que Desaba"),
                "Uma raiz larga demais para o espaço se ergue diante de você.\n"
                "Não há rosto, mas há algo nela que parece esperar uma resposta.",
            ),
        ),
        "A raiz se parte e o silêncio retorna.\n"
        "Você atravessou o peso da terra sem entregar o próprio nome a ela.",
    ),
    OathTrialDefinition(
        "jur_ferro_sob_a_pele",
        "Ferro sob a Pele",
        (
            _fight(
                "jur_portador_da_ferrugem", "Portador da Ferrugem", "elite", "Equilibrado",
                ("Golpe Enferrujado", "Marca de Ferrugem", "Placa Caída"),
                "Placas enferrujadas parecem ter crescido sobre o corpo.\n"
                "Cada passo range como uma porta que não deveria abrir.",
            ),
            _fight(
                "jur_quebrador_de_grilhoes", "Quebrador de Grilhões", "elite", "Bruto",
                ("Golpe de Corrente", "Elo Cortante", "Arrebentar Grilhões"),
                "Correntes partidas pendem de seus braços e arrastam pelo chão.\n"
                "Ele não parece carregá-las; parece ter nascido preso a elas.",
            ),
            _fight(
                "jur_o_ferreiro_cego", "O Ferreiro Cego", "boss", "Blindado",
                ("Martelada Cega", "Couraça do Ferreiro", "Bigorna Caída"),
                "Um vulto de ferro permanece imóvel até você se aproximar.\n"
                "Onde deveria haver um olhar, há apenas sombra entre placas.",
            ),
        ),
        "O ferro perde a voz.\n"
        "O Juramento não pede que você seja indestrutível — "
        "apenas que não abandone a promessa quando ela pesa.",
    ),
    OathTrialDefinition(
        "jur_o_olho_na_escuridao",
        "O Olho na Escuridão",
        (
            _fight(
                "jur_vigia_da_fenda", "Vigia da Fenda", "elite", "Ágil",
                ("Golpe da Fenda", "Corte Oculto", "Salto da Fenda"),
                "Um único brilho opaco acompanha cada movimento seu.\n"
                "O corpo permanece escondido onde a luz termina.",
            ),
            _fight(
                "jur_batedor_sem_palpebras", "Batedor Sem Pálpebras", "elite", "Ágil",
                ("Garra Sem Piscar", "Rasgo Atento", "Bote do Batedor"),
                "Ele não pisca.\n"
                "Nem quando se aproxima, nem quando recebe o golpe que deveria fazê-lo recuar.",
            ),
            _fight(
                "jur_a_testemunha_escura", "A Testemunha Escura", "boss", "Controlador",
                ("Toque de Sombra", "Olhar Peçonhento", "Peso do Olhar"),
                "A escuridão toma uma forma que parece observar antes de atacar.\n"
                "Você sente o peso daquele olhar sem encontrar olhos.",
            ),
        ),
        "A presença se desfaz sem deixar resposta.\n"
        "Você venceu sem precisar saber o que observava — e isso também faz parte do Juramento.",
    ),
    OathTrialDefinition(
        "jur_o_peso_do_silencio",
        "O Peso do Silêncio",
        (
            _fight(
                "jur_carregador_de_ossos", "Carregador de Ossos", "elite", "Bruto",
                ("Golpe de Ossos", "Costela Quebrada", "Desabar os Ossos"),
                "Restos de armaduras e ossos se acumulam sobre um corpo grande demais.\n"
                "Nada se move além das mãos.",
            ),
            _fight(
                "jur_sussurrante_de_cinza", "Sussurrante de Cinza", "elite", "Controlador",
                ("Toque de Cinza", "Murmúrio Peçonhento", "Cinza Pesada"),
                "A criatura não parece falar, mas o ar ao redor dela vibra com um murmúrio "
                "baixo.\nA cinza cai para cima por um instante.",
            ),
            _fight(
                "jur_o_peso_sem_nome", "O Peso sem Nome", "boss", "Equilibrado",
                ("Golpe Calado", "Marca do Peso", "Queda do Peso"),
                "Algo enorme permanece curvado sob um peso que ninguém mais consegue ver.\n"
                "Quando ele ergue a cabeça, o silêncio parece ocupar todo o espaço.",
            ),
        ),
        "O silêncio cede primeiro. Depois, o peso.\n"
        "Você permanece diante do vazio e leva consigo apenas a parte do Juramento "
        "que conseguiu cumprir.",
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


def encounter_stats(creature: Creature, level: int, roster_size: int) -> CombatStats:
    """One single rounding on the final attribute (§49.6)."""
    base = BOSS_BASE if creature.category == "boss" else ELITE_BASE
    return enemy_stats(level, base, ARCHETYPE[creature.archetype], group_scale(roster_size))


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
