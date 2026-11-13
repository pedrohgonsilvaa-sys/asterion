"""Expedição assíncrona (GDD v1.6.0 §22.2, §49.15).

Windows, the score scale and the rewards come from §49.15. The author decided on
2026-11-09 what the source leaves open:

- the Leader or an Officer picks the roster, up to Monday 18:00;
- each stage offers three options, whose text hints at the best one;
- a stage's score is the roster average; a missing answer uses the default.

``EXPEDITION_ROUTE_CATALOG`` holds the five Routes the author approved on 2026-11-12.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import Bundle

D = Decimal

EXPEDITION_TIMEZONE = ZoneInfo("America/Sao_Paulo")
RULESET = "expedition_v1"

# Monday is 0.
START_WEEKDAY = 0
START_TIME = time(18, 0)
DURATION = timedelta(hours=72)
STAGE_DURATION = timedelta(hours=24)
STAGE_COUNT = 3
ROSTER_MIN = 3
ROSTER_MAX = 6
MIN_ACTIVE_STAGES = 2
DEFAULT_POINTS = 20


class OptionQuality(StrEnum):
    FAVORABLE = "favorable"
    NEUTRAL = "neutral"
    POOR = "poor"


QUALITY_POINTS = {
    OptionQuality.FAVORABLE: 100,
    OptionQuality.NEUTRAL: 50,
    OptionQuality.POOR: 25,
}


class ExpeditionResult(StrEnum):
    FAILED = "failed"
    COMPLETED = "completed"
    DEEP = "deep"
    EXCEPTIONAL = "exceptional"


RESULT_LABELS = {
    ExpeditionResult.FAILED: "Fracassada",
    ExpeditionResult.COMPLETED: "Concluída",
    ExpeditionResult.DEEP: "Profunda",
    ExpeditionResult.EXCEPTIONAL: "Excepcional",
}
TREASURY_BY_RESULT = {
    ExpeditionResult.FAILED: 0,
    ExpeditionResult.COMPLETED: 1_500,
    ExpeditionResult.DEEP: 3_000,
    ExpeditionResult.EXCEPTIONAL: 5_000,
}
_REWARDS = {
    ExpeditionResult.COMPLETED: (D("0.50"), 3, 0),
    ExpeditionResult.DEEP: (D("0.80"), 5, 1),
    ExpeditionResult.EXCEPTIONAL: (D("1.25"), 8, 3),
}


@dataclass(frozen=True, slots=True)
class ExpeditionOption:
    option_id: str
    label: str
    quality: OptionQuality


@dataclass(frozen=True, slots=True)
class ExpeditionStage:
    flavor: str
    options: tuple[ExpeditionOption, ...]

    def __post_init__(self) -> None:
        if sorted(option.quality for option in self.options) != sorted(OptionQuality):
            raise ValueError("A stage has one favorable, one neutral and one poor option.")
        if len({option.option_id for option in self.options}) != len(self.options):
            raise ValueError("Option ids must be unique within a stage.")

    def option(self, option_id: str) -> ExpeditionOption | None:
        return next((row for row in self.options if row.option_id == option_id), None)


@dataclass(frozen=True, slots=True)
class ExpeditionRoute:
    route_id: str
    name: str
    stages: tuple[ExpeditionStage, ...]
    return_flavor: str

    def __post_init__(self) -> None:
        if len(self.stages) != STAGE_COUNT:
            raise ValueError("A Route has exactly three stages.")

    def stage(self, number: int) -> ExpeditionStage:
        return self.stages[number - 1]


def _stage(flavor: str, *options: tuple[str, str, OptionQuality]) -> ExpeditionStage:
    return ExpeditionStage(
        flavor, tuple(ExpeditionOption(oid, label, q) for oid, label, q in options)
    )


_F = OptionQuality.FAVORABLE
_N = OptionQuality.NEUTRAL
_P = OptionQuality.POOR

# Texto aprovado pelo autor em 2026-11-12 (IDs da Consolidação Final, seção 7).
# O campo "Default" das fontes não entra: resposta ausente vale DEFAULT_POINTS.
EXPEDITION_ROUTE_CATALOG: tuple[ExpeditionRoute, ...] = (
    # Terras do Ocaso
    ExpeditionRoute(
        "expedition.rotas_sob_a_cinza",
        "Rotas sob a Cinza",
        (
            _stage(
                "A estrada antiga ainda mostra seus marcos, embora metade deles esteja torta"
                " sob a cinza. Mais adiante, a encosta parece inteira; só de perto se nota que"
                " parte dela cedeu há muito tempo. Os sinais deixados na pedra parecem ter sido"
                " feitos para quem soubesse exatamente por onde seguir.",
                ("a", "Seguir marcos antigos", _F),
                ("b", "Contornar encosta", _P),
                ("c", "Parar reforçar rota", _N),
            ),
            _stage(
                "Uma passagem bloqueada separa vocês de uma estrutura antiga, e a força bruta"
                " faria mais barulho do que avanço. Perto da parede, restos de um mecanismo"
                " ainda formam uma linha compreensível entre as pedras. A saída lateral existe,"
                " mas ninguém sabe onde ela termina.",
                ("a", "Abrir pela força", _P),
                ("b", "Procurar mecanismo apoio", _F),
                ("c", "Procurar entrada lateral", _N),
            ),
            _stage(
                "A travessia seguinte parece simples quando vista à distância. Sob a cinza,"
                " porém, há marcas de desgaste diferentes nas partes que ainda suportam peso,"
                " como se alguém tivesse aprendido isso tarde demais. O caminho pede olhos"
                " antes de pés.",
                ("a", "Avançar imediatamente", _N),
                ("b", "Observar antes cruzar", _F),
                ("c", "Testar estrutura", _P),
            ),
        ),
        "A rota termina onde a cinza cobre quase tudo, menos os sinais que ainda resistiram."
        " Vocês seguem adiante com a sensação de que, aqui, ruína não significa ausência —"
        " significa algo que ainda não terminou de cair.",
    ),
    # Vales dos Enforcados
    ExpeditionRoute(
        "expedition.o_que_se_enreda",
        "O Que se Enreda",
        (
            _stage(
                "As cordas úmidas estão cobertas de musgo e apertam a madeira como se fizessem"
                " parte dela. A ponte range acima do vazio, mas ainda conserva seus antigos"
                " pontos de amarração. Sob as raízes, a passagem parece existir — embora"
                " ninguém saiba o que a sustenta.",
                ("a", "Reforçar cordas", _N),
                ("b", "Procurar passagem por baixo", _P),
                ("c", "Seguir ponte como está", _F),
            ),
            _stage(
                "As marcas na madeira foram deixadas em alturas diferentes, mas repetem o mesmo"
                " padrão. Limpar o caminho abriria espaço; comparar os sinais talvez revele por"
                " que aquela trilha foi usada tantas vezes. A mata parece engolir qualquer passo"
                " que não seja lembrado.",
                ("a", "Comparar marcações", _F),
                ("b", "Limpar passagem", _P),
                ("c", "Seguir trilha aberta", _N),
            ),
            _stage(
                "A trilha aberta conduz ao centro dos Vales, onde raízes antigas se cruzam como"
                " veias sobre pedra. Ao lado dela existem estruturas parcialmente suspensas,"
                " ainda presas apesar da idade. Algumas coisas aqui continuam de pé porque"
                " alguém, em algum momento, entendeu onde o peso deveria ficar.",
                ("a", "Evitar centro", _P),
                ("b", "Conferir estruturas antigas", _F),
                ("c", "Manter rota atual", _N),
            ),
        ),
        "Os Vales ficam para trás, mas as raízes continuam na memória como cordas que não se"
        " soltam. O caminho ensinou uma coisa simples: nem tudo que está preso está perdido.",
    ),
    # Planícies de Nareth
    ExpeditionRoute(
        "expedition.medida_do_meridiano",
        "A Medida do Meridiano",
        (
            _stage(
                "Três marcos aparecem no horizonte, quase perfeitamente alinhados. De longe,"
                " parecem confirmar a mesma estrada; de perto, pequenas diferenças começam a"
                " surgir entre eles. Em Nareth, uma única referência pode mentir sem deixar de"
                " parecer correta.",
                ("a", "Usar marco mais antigo", _P),
                ("b", "Comparar os três", _F),
                ("c", "Seguir estrada visível", _N),
            ),
            _stage(
                "A comporta antiga ainda conserva sinais de funcionamento, mas a marca junto ao"
                " metal não coincide com a direção indicada pela estrada. Mais adiante, uma rota"
                " diferente parece se corrigir à medida que vocês avançam. O erro não está"
                " necessariamente onde parece estar.",
                ("a", "Conferir comporta", _N),
                ("b", "Ignorar marca", _P),
                ("c", "Recalcular rota", _F),
            ),
            _stage(
                "A linha reta atravessa a planície como se tivesse sido desenhada para nunca"
                " hesitar. O declive, porém, contradiz o mapa; o último marco confirmado oferece"
                " uma alternativa menos elegante e mais segura. Aqui, voltar pode ser a única"
                " forma de continuar.",
                ("a", "Prosseguir linha reta", _N),
                ("b", "Confiar declive", _P),
                ("c", "Voltar último marco confirmado", _F),
            ),
        ),
        "Nareth não entrega certeza; entrega referências suficientes para desconfiar da própria"
        " certeza. Vocês deixam as planícies sabendo que um caminho verdadeiro pode ser aquele"
        " que precisou ser conferido duas vezes.",
    ),
    # Várzeas Carmesins
    ExpeditionRoute(
        "expedition.linhas_de_transferencia",
        "Linhas de Transferência",
        (
            _stage(
                "Os tubos antigos ainda cruzam a água ferruginosa como veias metálicas sobre o"
                " lodo. Alguns estão mortos; outros carregam um ruído baixo que desaparece"
                " quando a água sobe. A travessia mais curta não é necessariamente a que toca o"
                " solo menos profundo.",
                ("a", "Seguir tubos", _F),
                ("b", "Atravessar água rasa", _P),
                ("c", "Contornar dique", _N),
            ),
            _stage(
                "As válvulas permanecem, mas seus sinais foram gastos pelo tempo e pela"
                " ferrugem. Ao lado, uma linha seca acompanha o dique sem exigir que ninguém"
                " interrompa o que ainda funciona. Há lugares onde observar basta para descobrir"
                " qual parte da antiga rede ainda merece ser preservada.",
                ("a", "Examinar válvulas", _N),
                ("b", "Procurar linha seca", _F),
                ("c", "Interromper linha antiga", _P),
            ),
            _stage(
                "Além do canal, pequenas áreas cultivadas sobrevivem entre instalações antigas e"
                " água pesada. A rota direta corta o terreno como se nada dependesse dele. Dar a"
                " volta revela marcas de quem aprendeu a passar sem destruir o que ainda"
                " alimenta os vivos.",
                ("a", "Seguir direto", _P),
                ("b", "Observar cultivos", _F),
                ("c", "Dar volta canal", _N),
            ),
        ),
        "As Várzeas ficam atrás como uma superfície que nunca parece inteiramente quieta. Entre"
        " ferrugem, água e estruturas antigas, vocês levam consigo a impressão de que a vida ali"
        " continuou — mesmo quando ninguém mais sabia para quê.",
    ),
    # Altos Cinéreos
    ExpeditionRoute(
        "expedition.carga_sem_fim",
        "Carga sem Fim",
        (
            _stage(
                "O vento passa pelas estruturas e faz os cabos vibrarem acima do abismo. Alguns"
                " apoios parecem antigos demais para sustentar qualquer coisa, mas ainda carregam"
                " o peso distribuído da montanha. Antes de escolher a trilha, vale lembrar que"
                " uma estrutura não precisa parecer nova para continuar funcionando.",
                ("a", "Reforçar apoios", _F),
                ("b", "Escolher trilha inferior", _N),
                ("c", "Cruzar imediatamente", _P),
            ),
            _stage(
                "A passagem está parada, e esse silêncio pesa mais do que o vento. Um conjunto de"
                " contrapesos permanece imóvel enquanto todo o restante range ao redor. Há"
                " momentos em que tocar menos é a forma mais segura de atravessar.",
                ("a", "Ajustar equilíbrio", _N),
                ("b", "Passar enquanto imóvel", _F),
                ("c", "Forçar estrutura", _P),
            ),
            _stage(
                "A rota seguinte passa perto de uma sustentação que já perdeu parte da cobertura."
                " A estrutura não pede velocidade; pede distância. Ao lado, uma passagem lateral"
                " permanece aberta e não exige que ninguém descubra quanto peso aquele sistema"
                " ainda consegue suportar.",
                ("a", "Seguir sem tocar estrutura", _F),
                ("b", "Procurar passagem lateral", _N),
                ("c", "Testar peso estrutura", _P),
            ),
        ),
        "Os Altos permanecem atrás, sustentados por pedra, cabos e escolhas feitas muito antes"
        " de vocês chegarem. A estrada ensina pouco sobre força e muito sobre aquilo que precisa"
        " continuar inteiro.",
    ),
)


def next_start(now: datetime) -> datetime:
    """The first Monday 18:00 strictly after ``now``."""
    local = now.astimezone(EXPEDITION_TIMEZONE)
    for days_ahead in range(0, 9):
        day = (local + timedelta(days=days_ahead)).date()
        if day.weekday() != START_WEEKDAY:
            continue
        slot = datetime.combine(day, START_TIME, EXPEDITION_TIMEZONE)
        if slot > local:
            return slot
    raise RuntimeError("The weekly schedule always has a next start.")


def week_key(start: datetime) -> str:
    return start.astimezone(EXPEDITION_TIMEZONE).strftime("%Y%m%d")


def route_for_start(
    catalog: tuple[ExpeditionRoute, ...], start: datetime
) -> ExpeditionRoute | None:
    """Deterministic rotation, so every process picks the same Route."""
    if not catalog:
        return None
    week = start.astimezone(EXPEDITION_TIMEZONE).date().toordinal() // 7
    return catalog[week % len(catalog)]


def stage_at(starts_at: datetime, now: datetime) -> int:
    """The stage open at ``now``; 0 before the start, 4 after the end."""
    if now < starts_at:
        return 0
    return min(STAGE_COUNT + 1, int((now - starts_at) / STAGE_DURATION) + 1)


def stage_ends_at(starts_at: datetime, stage: int) -> datetime:
    return starts_at + STAGE_DURATION * stage


def final_score(points_by_stage: Iterable[Iterable[int]]) -> int:
    """Sum of each stage's roster average, rounded down once at the end."""
    total = sum((D(sum(points)) / D(len(points)) for points in map(tuple, points_by_stage)), D(0))
    return int(total)


def result_for(score: int) -> ExpeditionResult:
    if score >= 240:
        return ExpeditionResult.EXCEPTIONAL
    if score >= 180:
        return ExpeditionResult.DEEP
    if score >= 100:
        return ExpeditionResult.COMPLETED
    return ExpeditionResult.FAILED


def treasury_reward(result: ExpeditionResult) -> int:
    return TREASURY_BY_RESULT[result]


def is_eligible(active_stages: int) -> bool:
    return active_stages >= MIN_ACTIVE_STAGES


def reward_bundle(level: int, result: ExpeditionResult) -> Bundle | None:
    reward = _REWARDS.get(result)
    if reward is None:
        return None
    multiplier, basics, fragments = reward
    return Bundle(
        crowns=round_10(multiplier * crowns_per_level(level)),
        basics=basics,
        fragments=fragments,
    )
