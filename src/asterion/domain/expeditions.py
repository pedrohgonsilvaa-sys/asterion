"""Expedição assíncrona (GDD v1.6.0 §22.2, §49.15).

Windows, the score scale and the rewards come from §49.15. The author decided on
2026-11-09 what the source leaves open:

- the Leader or an Officer picks the roster, up to Monday 18:00;
- each stage offers three options, whose text hints at the best one;
- a stage's score is the roster average; a missing answer uses the default.

``EXPEDITION_ROUTE_CATALOG`` comes from ``ASTERION_ROTAS_EXPEDICAO_FINAL.md``. The button
order is mixed on purpose (author decision, 2026-11-12), so the favorable option is not
always first; an option's ``description`` is shown only after it is chosen.
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
    description: str = ""


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


EXPEDITION_ROUTE_CATALOG: tuple[ExpeditionRoute, ...] = (
    ExpeditionRoute(
        'expedition.estrada_perde_marcos',
        'A Estrada que Perde Marcos',
        (
            ExpeditionStage(
                (
                    'A expedição encontra a primeira marca de estrada. O suporte ainda está de pé,'
                    ' mas a indicação que deveria apontar a direção desapareceu.'
                ),
                (
                    ExpeditionOption(
                        'seguir_trilha_usada',
                        'Seguir a trilha usada',
                        OptionQuality.NEUTRAL,
                        (
                            'A equipe escolhe o caminho com maior evidência de trânsito recente. '
                            'Há mais pegadas na trilha da esquerda, mas nenhuma prova que seja a '
                            'rota correta.'
                        ),
                    ),
                    ExpeditionOption(
                        'examinar_suporte',
                        'Examinar o suporte',
                        OptionQuality.FAVORABLE,
                        (
                            'A equipe procura marcas secundárias, desgaste no chão e sinais de '
                            'passagem antes de escolher uma direção. A pedra está firme, mas o '
                            'solo ao redor foi pisado recentemente em mais de uma direção.'
                        ),
                    ),
                    ExpeditionOption(
                        'avancar_marco',
                        'Avançar sem o marco',
                        OptionQuality.POOR,
                        (
                            'A Guilda abandona a referência e segue por terreno aberto. Depois de '
                            'algum tempo, outra pedra aparece à distância e parece apontar para um'
                            ' lugar diferente.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'Mais adiante surgem dois marcos intactos. Ambos têm sinais de uso recente, '
                    'mas suas orientações não parecem concordar.'
                ),
                (
                    ExpeditionOption(
                        'confiar_nos_mapas',
                        'Confiar só nos mapas',
                        OptionQuality.POOR,
                        (
                            'Os registros da Guilda viram a referência principal. A rota '
                            'registrada passa por uma elevação que, no terreno, parece ter mudado '
                            'de função há muito tempo.'
                        ),
                    ),
                    ExpeditionOption(
                        'comparar_dois_marcos',
                        'Comparar os dois marcos',
                        OptionQuality.FAVORABLE,
                        (
                            'A equipe registra distância, posição e relação entre as duas marcas. '
                            'O desgaste de uma é mais antigo; a outra apresenta uma borda '
                            'recentemente exposta, como se tivesse sido recolocada.'
                        ),
                    ),
                    ExpeditionOption(
                        'escolher_marca_mais',
                        'Escolher a marca mais conservada',
                        OptionQuality.NEUTRAL,
                        (
                            'A Guilda assume que a pedra mais preservada é a referência mais '
                            'confiável. Ela é mais legível, mas suas costas têm a mesma erosão da '
                            'marca anterior.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'A estrada termina diante de uma bifurcação sem marco. Um caminho aparenta ser'
                    ' moderno; o outro está quase tomado pela vegetação, mas possui sinais '
                    'recentes de uso.'
                ),
                (
                    ExpeditionOption(
                        'investigar_caminho_antigo',
                        'Investigar o caminho antigo',
                        OptionQuality.FAVORABLE,
                        (
                            'Há marcas de carga, mas nenhum acampamento recente. Quem passou por '
                            'ali carregava algo pesado e não voltou pelo mesmo trajeto.'
                        ),
                    ),
                    ExpeditionOption(
                        'dividir_expedicao',
                        'Dividir a expedição',
                        OptionQuality.POOR,
                        (
                            'As equipes cobrem as duas opções. Ao reunir os registros, ambas '
                            'descrevem a mesma colina de maneiras diferentes.'
                        ),
                    ),
                    ExpeditionOption(
                        'seguir_rota_moderna',
                        'Seguir pela rota moderna',
                        OptionQuality.NEUTRAL,
                        (
                            'A estrada chega ao destino esperado. O caminho antigo, porém, aparece'
                            ' no mapa de retorno como uma linha que nunca deveria ter '
                            'desaparecido.'
                        ),
                    ),
                ),
            ),
        ),
        (
            'A estrada não desapareceu. O que desapareceu foi a certeza de que seus marcos ainda '
            'significavam a mesma coisa.'
        ),
    ),
    ExpeditionRoute(
        'expedition.rio_mudou_leito',
        'O Rio que Mudou de Leito',
        (
            ExpeditionStage(
                'O primeiro curso d’água surge antes do ponto previsto nos registros.',
                (
                    ExpeditionOption(
                        'atravessar_imediatamente',
                        'Atravessar imediatamente',
                        OptionQuality.POOR,
                        (
                            'Quando o primeiro grupo atravessa, uma segunda corrente aparece atrás'
                            ' das pedras e muda rapidamente a distribuição da água.'
                        ),
                    ),
                    ExpeditionOption(
                        'procurar_passagem_rasa',
                        'Procurar uma passagem rasa',
                        OptionQuality.NEUTRAL,
                        (
                            'O trecho mais raso existe; pedras estão dispostas em intervalos quase'
                            ' regulares dentro da água.'
                        ),
                    ),
                    ExpeditionOption(
                        'mapear_novo_curso',
                        'Mapear o novo curso',
                        OptionQuality.FAVORABLE,
                        (
                            'A água é mais profunda do que parece, mas a margem oposta mostra '
                            'marcas de carroças antigas.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                'A Guilda encontra marcas de um antigo curso seco que contradiz o traçado atual.',
                (
                    ExpeditionOption(
                        'comparar_com_registros',
                        'Comparar com registros antigos',
                        OptionQuality.FAVORABLE,
                        (
                            'As margens antigas apresentam o mesmo tipo de erosão observado onde o'
                            ' rio atual passa.'
                        ),
                    ),
                    ExpeditionOption(
                        'usar_leito_seco',
                        'Usar o leito seco',
                        OptionQuality.NEUTRAL,
                        (
                            'O terreno é firme e oferece passagem. Pequenos depósitos de barro '
                            'seco formam uma linha contínua sob a vegetação.'
                        ),
                    ),
                    ExpeditionOption(
                        'desviar_rio',
                        'Desviar do rio',
                        OptionQuality.POOR,
                        (
                            'Quanto mais a expedição se afasta, mais frequentes ficam pequenas '
                            'áreas de solo úmido sem água visível.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'Uma ponte antiga surge diante da expedição. A estrutura parece preservada '
                    'para uma corrente que já não existe.'
                ),
                (
                    ExpeditionOption(
                        'usar_ponte',
                        'Usar a ponte',
                        OptionQuality.NEUTRAL,
                        (
                            'A travessia é segura. Do outro lado, porém, existem marcas de água '
                            'acima do nível atual do terreno.'
                        ),
                    ),
                    ExpeditionOption(
                        'ignorar_ponte',
                        'Ignorar a ponte',
                        OptionQuality.POOR,
                        (
                            'A margem aparentemente firme cede em um trecho onde não deveria haver'
                            ' água.'
                        ),
                    ),
                    ExpeditionOption(
                        'estudar_ponte',
                        'Estudar a ponte',
                        OptionQuality.FAVORABLE,
                        (
                            'O centro está mais gasto que as extremidades; quem passava ali '
                            'carregava peso regularmente.'
                        ),
                    ),
                ),
            ),
        ),
        (
            'O rio não contou à Guilda quando mudou de caminho. Só deixou sinais de que um dia já '
            'correu por outro lugar.'
        ),
    ),
    ExpeditionRoute(
        'expedition.cinzas_sobre_estrada',
        'Cinzas sobre a Estrada',
        (
            ExpeditionStage(
                'A Guilda encontra carroças vazias e uma carga parcialmente intacta.',
                (
                    ExpeditionOption(
                        'recuperar_utilizavel',
                        'Recuperar o utilizável',
                        OptionQuality.NEUTRAL,
                        (
                            'O estoque permite reconstruir boa parte da carga, mas algumas caixas '
                            'foram abertas sem que o conteúdo fosse levado.'
                        ),
                    ),
                    ExpeditionOption(
                        'inventariar',
                        'Inventariar primeiro',
                        OptionQuality.FAVORABLE,
                        'Certos tipos de carga foram retirados, enquanto outros permaneceram.',
                    ),
                    ExpeditionOption(
                        'abandonar_carga',
                        'Abandonar a carga',
                        OptionQuality.POOR,
                        (
                            'Entre as caixas há registros de transporte que não correspondem à '
                            'rota esperada.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                'O caminho apresenta cinza recente, mas nenhuma fonte evidente.',
                (
                    ExpeditionOption(
                        'atravessar_area_coberta',
                        'Atravessar a área coberta',
                        OptionQuality.POOR,
                        (
                            'A cinza é leve demais para ter permanecido ali por acaso; sob ela, a '
                            'estrada está quase intacta.'
                        ),
                    ),
                    ExpeditionOption(
                        'procurar_origem',
                        'Procurar a origem',
                        OptionQuality.FAVORABLE,
                        (
                            'Não há fogo; há uma faixa de cinza acumulada dentro de depressões do '
                            'terreno, sempre voltada para o mesmo lado.'
                        ),
                    ),
                    ExpeditionOption(
                        'usar_parte_limpa',
                        'Usar a parte limpa',
                        OptionQuality.NEUTRAL,
                        (
                            'A faixa limpa é segura, mas passa entre dois trechos onde a cinza se '
                            'acumulou.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'A expedição encontra a última carga da rota. Ela permanece organizada, como '
                    'se a interrupção tivesse acontecido antes do carregamento terminar.'
                ),
                (
                    ExpeditionOption(
                        'verificar_que_nao',
                        'Verificar por que não partiu',
                        OptionQuality.FAVORABLE,
                        (
                            'O inventário está completo. O registro de saída, entretanto, já foi '
                            'preenchido.'
                        ),
                    ),
                    ExpeditionOption(
                        'desmontar_selecionar',
                        'Desmontar e selecionar',
                        OptionQuality.POOR,
                        (
                            'Entre os itens havia material destinado a uma parada que não aparece '
                            'em nenhum registro da Guilda.'
                        ),
                    ),
                    ExpeditionOption(
                        'retomar_rota',
                        'Retomar a rota',
                        OptionQuality.NEUTRAL,
                        (
                            'A carga segue intacta, mas a rota oficial continua marcada como '
                            'interrompida.'
                        ),
                    ),
                ),
            ),
        ),
        'As cinzas cobriam a estrada, mas não explicavam o abandono.',
    ),
    ExpeditionRoute(
        'expedition.posto_sem_testemunhas',
        'O Posto sem Testemunhas',
        (
            ExpeditionStage(
                'O posto está destrancado e aparenta ter sido abandonado há pouco tempo.',
                (
                    ExpeditionOption(
                        'levar_ferramentas',
                        'Levar ferramentas',
                        OptionQuality.POOR,
                        (
                            'A parede atrás da bancada possui marcas recentes de remoção de '
                            'equipamento.'
                        ),
                    ),
                    ExpeditionOption(
                        'usar_abrigo',
                        'Usar como abrigo',
                        OptionQuality.NEUTRAL,
                        (
                            'O abrigo é seguro. O relógio da sala marca uma hora que ninguém '
                            'consegue confirmar.'
                        ),
                    ),
                    ExpeditionOption(
                        'inspecionar_antes_usar',
                        'Inspecionar antes de usar',
                        OptionQuality.FAVORABLE,
                        (
                            'As ferramentas estão organizadas; o registro mais recente foi escrito'
                            ' com tinta diferente das linhas anteriores.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                'Os registros apresentam décadas de entradas e saídas.',
                (
                    ExpeditionOption(
                        'comparar_nomes_datas',
                        'Comparar nomes e datas',
                        OptionQuality.FAVORABLE,
                        (
                            'Algumas pessoas aparecem entrando em períodos em que o posto deveria '
                            'estar fechado.'
                        ),
                    ),
                    ExpeditionOption(
                        'aceitar_livro_valido',
                        'Aceitar o livro como válido',
                        OptionQuality.NEUTRAL,
                        (
                            'A caligrafia permanece consistente por várias páginas; páginas '
                            'seguintes parecem rearranjadas.'
                        ),
                    ),
                    ExpeditionOption(
                        'ignorar_livro',
                        'Ignorar o livro',
                        OptionQuality.POOR,
                        (
                            'Sem ele, desaparece a única referência sobre quem utilizava a '
                            'passagem antes do abandono.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'A Guilda encontra uma pequena construção nos fundos do posto. Há um banco, '
                    'uma caneca e uma janela voltada para a estrada.'
                ),
                (
                    ExpeditionOption(
                        'procurar_alguem',
                        'Procurar alguém',
                        OptionQuality.NEUTRAL,
                        (
                            'Não há ninguém; há apenas sinais de que alguém continua verificando a'
                            ' estrada.'
                        ),
                    ),
                    ExpeditionOption(
                        'declarar_abandono',
                        'Declarar abandono',
                        OptionQuality.POOR,
                        (
                            'Quando a Guilda parte, a porta deixada aberta aparece fechada no '
                            'registro de saída.'
                        ),
                    ),
                    ExpeditionOption(
                        'investigar_ponto_observacao',
                        'Investigar o ponto de observação',
                        OptionQuality.FAVORABLE,
                        (
                            'A janela oferece visão perfeita da passagem. O banco está gasto '
                            'apenas em uma das extremidades.'
                        ),
                    ),
                ),
            ),
        ),
        (
            'O posto tinha tudo o que uma passagem precisava para funcionar. Só faltava alguém '
            'disposto a afirmar que ainda funcionava.'
        ),
    ),
    ExpeditionRoute(
        'expedition.tres_registros_uma_rota',
        'Três Registros, Uma Rota',
        (
            ExpeditionStage(
                'O primeiro documento descreve uma estrada ampla e estável.',
                (
                    ExpeditionOption(
                        'usar_registro_mapa',
                        'Usar o registro como mapa',
                        OptionQuality.NEUTRAL,
                        'A direção geral funciona; distâncias e pontos de referência não.',
                    ),
                    ExpeditionOption(
                        'procurar_fisicamente_trecho',
                        'Procurar fisicamente o trecho',
                        OptionQuality.FAVORABLE,
                        (
                            'O terreno atual não corresponde ao desenho, mas conserva marcas de '
                            'uma passagem antiga.'
                        ),
                    ),
                    ExpeditionOption(
                        'descartar_inconsistencia',
                        'Descartar por inconsistência',
                        OptionQuality.POOR,
                        (
                            'Mesmo incorreto em detalhes, o documento contém uma indicação de '
                            'segurança que os outros dois não possuem.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                'O segundo documento apresenta a mesma rota como estreita, inclinada e difícil.',
                (
                    ExpeditionOption(
                        'seguir_descricao_mais',
                        'Seguir a descrição mais simples',
                        OptionQuality.POOR,
                        (
                            'O caminho simples leva ao mesmo ponto, mas não explica por que o '
                            'segundo registro recomenda cautela.'
                        ),
                    ),
                    ExpeditionOption(
                        'comparar_duas_descricoes',
                        'Comparar as duas descrições',
                        OptionQuality.FAVORABLE,
                        (
                            'Ambas mencionam uma estrutura na mesma altura, mas descrevem funções '
                            'diferentes para ela.'
                        ),
                    ),
                    ExpeditionOption(
                        'priorizar_mais_recente',
                        'Priorizar o mais recente',
                        OptionQuality.NEUTRAL,
                        'A data é posterior; a autoria não é indicada.',
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'O último documento contradiz ambos em um detalhe importante: indica que a '
                    'estrada possui duas passagens onde os outros registros mostram apenas uma.'
                ),
                (
                    ExpeditionOption(
                        'procurar_segunda_passagem',
                        'Procurar a segunda passagem sem assumir sua posição',
                        OptionQuality.FAVORABLE,
                        (
                            'Existe uma segunda marca, mas ela não ocupa a posição descrita; a '
                            'distância entre as duas permanece estranhamente regular.'
                        ),
                    ),
                    ExpeditionOption(
                        'escolher_registro_definitivo',
                        'Escolher um registro como definitivo',
                        OptionQuality.POOR,
                        (
                            'O trecho seguinte confirma parte de cada documento e contradiz outra '
                            'parte de cada um.'
                        ),
                    ),
                    ExpeditionOption(
                        'tratar_erro_cartografico',
                        'Tratar como erro cartográfico',
                        OptionQuality.NEUTRAL,
                        (
                            'É possível explicar a diferença como erro, mas a mesma diferença '
                            'aparece nos três documentos em lugares distintos.'
                        ),
                    ),
                ),
            ),
        ),
        (
            'Três pessoas descreveram uma estrada. O mais estranho não foi discordarem. Foi cada '
            'uma ter registrado algo que as outras não poderiam simplesmente inventar.'
        ),
    ),
    ExpeditionRoute(
        'expedition.estrada_que_continua',
        'A Estrada que Continua',
        (
            ExpeditionStage(
                'Um antigo portão de estrada está aberto.',
                (
                    ExpeditionOption(
                        'forcar_portao',
                        'Forçar o portão',
                        OptionQuality.POOR,
                        (
                            'A estrutura se move, mas o som percorre a estrada por muito mais '
                            'tempo do que deveria.'
                        ),
                    ),
                    ExpeditionOption(
                        'passar_portao',
                        'Passar pelo portão',
                        OptionQuality.NEUTRAL,
                        'O caminho continua transitável durante o primeiro trecho.',
                    ),
                    ExpeditionOption(
                        'examinar_mecanismo_marcas',
                        'Examinar mecanismo e marcas',
                        OptionQuality.FAVORABLE,
                        (
                            'O mecanismo não foi quebrado; uma peça apresenta desgaste recente e '
                            'deliberado.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                'A Guilda encontra uma seção da estrada surpreendentemente bem mantida.',
                (
                    ExpeditionOption(
                        'identificar_quem_conserva',
                        'Identificar quem conserva o trecho',
                        OptionQuality.FAVORABLE,
                        (
                            'Não há trabalhadores. Há ferramentas recentes e uma substituição de '
                            'pedra cuja cor não combina com o restante.'
                        ),
                    ),
                    ExpeditionOption(
                        'aproveitar_passagem',
                        'Aproveitar a passagem',
                        OptionQuality.NEUTRAL,
                        'O trecho é seguro; mais adiante, a manutenção termina.',
                    ),
                    ExpeditionOption(
                        'remover_material_conservado',
                        'Remover material conservado',
                        OptionQuality.POOR,
                        (
                            'Sob a pedra retirada existe uma antiga marca de orientação que não '
                            'aparece nos mapas da Guilda.'
                        ),
                    ),
                ),
            ),
            ExpeditionStage(
                (
                    'A estrada termina diante de um ponto que não deveria estar conectado à rota '
                    'moderna.'
                ),
                (
                    ExpeditionOption(
                        'usar_atalho',
                        'Usar como atalho',
                        OptionQuality.NEUTRAL,
                        (
                            'A passagem economiza tempo e funciona; o retorno exige uma decisão '
                            'diferente da ida.'
                        ),
                    ),
                    ExpeditionOption(
                        'reivindicar_caminho_permanente',
                        'Reivindicar como caminho permanente',
                        OptionQuality.POOR,
                        (
                            'A estrada pode ser usada, mas nada garante que a Guilda compreenda '
                            'por que voltou a funcionar.'
                        ),
                    ),
                    ExpeditionOption(
                        'registrar_conexao',
                        'Registrar a conexão primeiro',
                        OptionQuality.FAVORABLE,
                        (
                            'A estrutura seguinte foi construída para receber viajantes, mas não '
                            'há indicação de quem deveria chegar por ali.'
                        ),
                    ),
                ),
            ),
        ),
        (
            'A estrada estava fechada há anos. Ainda assim, alguém — ou alguma coisa — continuou '
            'preparando o caminho para quem viesse depois.'
        ),
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
