"""Playable content of Crônica I: NPC talks, Leituras and Desbravar results.

Source: ``ASTERION_CRONICA_I_ECOS_DA_CONVERGENCIA_v0_2_PROPOSTA.md`` §0.2, §0.3, §2 and §8.
The proposal fixes who, where and how many; the short lines below were written from
its chapter summaries and are listed in HANDOFF.md for the author's review.

Spoiler rules (§0.2): base and mirror texts name only C0 terms. A mirror text never
names a person or place of a Region the character has not reached; layer complements
are separate and shown only with the matching flag.

Weights confirmed by the author (2026-11-09): while a chapter result is pending in a
Local it takes the whole Narrativo category; the Vestígio has weight 100 there.
"""

from __future__ import annotations

from dataclasses import dataclass

from asterion.domain.chronicle import Layer
from asterion.domain.road import (
    ALTOS_BASTILHA_LOCATION,
    ALTOS_ESCARPA_LOCATION,
    ALTOS_PEDREIRAS_LOCATION,
    ALTOS_PONTES_LOCATION,
    BOSQUE_LOCATION,
    CHARNECA_LOCATION,
    CONFINS_ESTRADAS_AUSENTES_LOCATION,
    CONFINS_FRATURAS_LIMIAR_LOCATION,
    CONFINS_MARCHA_LOCATION,
    CONFINS_NO_CENTRAL_LOCATION,
    NARETH_CAMPINAS_LOCATION,
    NARETH_CAMPOS_LOCATION,
    NARETH_CANAIS_LOCATION,
    NARETH_OBSERVATORIO_LOCATION,
    ROAD_LOCATION,
    RUINS_LOCATION,
    VARZEAS_BREJOS_LOCATION,
    VARZEAS_DIQUES_LOCATION,
    VARZEAS_GALERIAS_LOCATION,
    VARZEAS_HORTOS_LOCATION,
    VDE_BAIXIOS_LOCATION,
    VDE_CLAUSTRO_LOCATION,
    VDE_GARGANTA_LOCATION,
    VDE_MATA_LOCATION,
)

DESBRAVAR_GUARANTEE_ATTEMPT = 3  # GDD §49.15: mandatory content is protected for 3 attempts.
VESTIGIO_WEIGHT = 100
CHAPTER_RESULT_WEIGHT = 100  # Alone in its category, so the value does not change the odds.
RESULT_PREFIX = "dsc_cr01_"
VESTIGIO_RESULT = "dsc_cr01_vestigio"
VESTIGIO_SOURCE = "rep_cr01_desbravar"


@dataclass(frozen=True, slots=True)
class RegionInfo:
    name: str
    min_level: int
    hub: str
    coordinator: str
    registrar: str
    locals: tuple[str, ...]  # Locals with Desbravar, least to most advanced.


OCASO = "Terras do Ocaso"
VALES = "Vales dos Enforcados"
NARETH = "Planícies de Nareth"
VARZEAS = "Várzeas Carmesins"
ALTOS = "Altos Cinéreos"
CONFINS = "Confins do Véu"

REGIONS: tuple[RegionInfo, ...] = (
    RegionInfo(
        OCASO,
        1,
        "Refúgio do Ocaso",
        "Alda Veyr",
        "Oren Cal",
        (ROAD_LOCATION, CHARNECA_LOCATION, BOSQUE_LOCATION, RUINS_LOCATION),
    ),
    RegionInfo(
        VALES,
        11,
        "Vigília do Vale",
        "Dara Venn",
        "Iven Raal",
        (
            VDE_GARGANTA_LOCATION,
            VDE_MATA_LOCATION,
            VDE_BAIXIOS_LOCATION,
            VDE_CLAUSTRO_LOCATION,
        ),
    ),
    RegionInfo(
        NARETH,
        21,
        "Posto de Nareth",
        "Nera Voss",
        "Talen Orm",
        (
            NARETH_CAMPINAS_LOCATION,
            NARETH_CANAIS_LOCATION,
            NARETH_CAMPOS_LOCATION,
            NARETH_OBSERVATORIO_LOCATION,
        ),
    ),
    RegionInfo(
        VARZEAS,
        31,
        "Porto da Salmoura",
        "Sera Morn",
        "Ilyan Korr",
        (
            VARZEAS_DIQUES_LOCATION,
            VARZEAS_BREJOS_LOCATION,
            VARZEAS_HORTOS_LOCATION,
            VARZEAS_GALERIAS_LOCATION,
        ),
    ),
    RegionInfo(
        ALTOS,
        41,
        "Abrigo do Peso",
        "Rava Kern",
        "Sel Ardan",
        (
            ALTOS_ESCARPA_LOCATION,
            ALTOS_PONTES_LOCATION,
            ALTOS_PEDREIRAS_LOCATION,
            ALTOS_BASTILHA_LOCATION,
        ),
    ),
    RegionInfo(
        CONFINS,
        51,
        "Último Refúgio",
        "Sera Nol",
        "Roven Pell",
        (
            CONFINS_MARCHA_LOCATION,
            CONFINS_ESTRADAS_AUSENTES_LOCATION,
            CONFINS_FRATURAS_LIMIAR_LOCATION,
            CONFINS_NO_CENTRAL_LOCATION,
        ),
    ),
)
REGIONS_BY_NAME: dict[str, RegionInfo] = {region.name: region for region in REGIONS}

# Chapters 1 and 8 have no focus: they always happen in the Região de Ressonância.
CHAPTER_FOCUS: dict[int, str] = {2: OCASO, 3: VALES, 4: NARETH, 5: VARZEAS, 6: ALTOS, 7: CONFINS}


@dataclass(frozen=True, slots=True)
class Complement:
    layer: Layer
    text: str


@dataclass(frozen=True, slots=True)
class NpcStep:
    role: str  # 'coordinator' or 'registrar'
    text: str  # ``{npc}`` is the speaker
    mirror: str | None = None  # None when the chapter has no focus Region
    complement: Complement | None = None


@dataclass(frozen=True, slots=True)
class ReadingPoint:
    point_id: str
    label: str
    text: str
    mirror_label: str | None = None
    mirror_text: str | None = None


@dataclass(frozen=True, slots=True)
class DesbravarStep:
    result_id: str
    text: str
    mirror: str | None = None
    complement: Complement | None = None


NPC_STEPS: dict[str, NpcStep] = {
    "cap_01_obj_01": NpcStep(
        "registrar",
        "{npc} larga a pena quando você entra.\n\n"
        "— Também sentiu? Todos os que passam aqui contam a mesma coisa: a pedra antiga "
        "estremeceu, sem fogo e sem desabamento. Nas inscrições apagadas voltou uma palavra, "
        "CONVERGÊNCIA. Ninguém aqui sabe o que ela quer dizer. Me diga a hora e o lugar.",
    ),
    "cap_02_obj_03": NpcStep(
        "registrar",
        "{npc} abre três cartas lado a lado sobre a mesa.\n\n"
        "— Outros registradores escrevem o mesmo: o pulso volta em intervalos. Mas olhe os "
        "horários. Em cada Região ele chega num momento um pouco diferente.",
    ),
    "cap_03_obj_01": NpcStep(
        "coordinator",
        "{npc} risca mais uma travessia no mapa.\n\n"
        "— A cada pulso as raízes se contraem, as cordas rangem e as pontes torcem. Nos "
        "horários de pulso, ninguém atravessa. Não é medo: é a conta de quantos quase caíram.",
        "{npc} lê em voz alta uma carta que chegou de longe.\n\n"
        "— Em travessias distantes, as passagens estão sendo fechadas nos horários de pulso. "
        "O que sentimos aqui também acontece lá. Vamos marcar nossas rotas do mesmo jeito.",
    ),
    "cap_04_obj_02": NpcStep(
        "registrar",
        "{npc} empurra a folha de medições até você, com o próprio nome no rodapé.\n\n"
        "— Durante cada pulso, todos os marcos apontam para o mesmo lado e depois voltam. "
        "Medi o desvio e publiquei a correção. Somando as leituras de três Regiões, a "
        "conclusão é incômoda: o pulso tem direção.",
        "{npc} estende um mapa enviado por outro registrador.\n\n"
        "— Os marcos daqui também desviam, menos do que lá longe, mas desviam. Somando as "
        "medições, todos chegam ao mesmo lugar: o pulso tem direção.",
        Complement(
            Layer.C2,
            "Para quem sabe o que as Âncoras faziam, o desvio parece uma comparação de "
            "referências que não recebe resposta.",
        ),
    ),
    "cap_05_obj_01": NpcStep(
        "coordinator",
        "{npc} isola mais um canal antes de responder.\n\n"
        "— O pulso antigo entrou em compasso com o dos Brejos. As válvulas se movem a cada "
        "batida, e Niva Sol testa a água antes de eu liberar qualquer rota. Nos registros de "
        "manutenção, o pulso aparece como sinal de confirmação. Confirmação de quê, ninguém "
        "escreveu.",
        "{npc} aponta a umidade que sobe pela parede.\n\n"
        "— A água daqui também reage ao pulso. Recebi a cópia de um registro antigo, e só uma "
        "expressão ficou legível: sinal de confirmação.",
        Complement(
            Layer.H,
            "Os protocolos que ainda operam nas instalações Hemaris reagem como se aguardassem "
            "instrução de fora. Isso não diz nada sobre os Hemários de hoje.",
        ),
    ),
    "cap_06_obj_01": NpcStep(
        "registrar",
        "{npc} copia a mesma linha pela terceira vez.\n\n"
        "— Uma ordem antiga gravada na Bastilha se repete a cada pulso, sem data, pedindo uma "
        "confirmação que ninguém sabe dar. Rava Kern proibiu qualquer um de tentar obedecer. "
        "Maro Keln reconheceu o formato: é coisa das instituições antigas.",
        "{npc} lê em voz baixa uma cópia enviada pelos Herdeiros, estudiosos que guardam e "
        "comparam registros antigos.\n\n"
        "— Não é um aviso. É uma pergunta à espera de resposta, e ninguém sabe quem deveria "
        "responder.",
        Complement(
            Layer.C3, "A ordem é uma etapa da Convergência interrompida na noite da Ruptura."
        ),
    ),
    "cap_07_obj_02": NpcStep(
        "registrar",
        "{npc} registra duas versões da mesma leitura, uma ao lado da outra.\n\n"
        "— Aqui o pulso não chega de longe: parte daqui. As referências de todas as Regiões "
        "convergem para um mesmo ponto. Eris Val ajuda a reunir o que falta, e cada linha da "
        "Sequência Pendente só entra com dupla testemunha.",
        "{npc} desenrola a Sequência reunida que os Herdeiros enviaram.\n\n"
        "— O pulso mais forte até agora atravessou a Região. Seja o que for isto, tenta "
        "completar uma última etapa e nunca recebe resposta.",
        Complement(
            Layer.C4,
            "A origem está no Nó Central; a etapa pendente é o último passo de coordenação que "
            "nunca foi confirmado.",
        ),
    ),
    "cap_08_obj_01": NpcStep(
        "coordinator",
        "{npc} ouve seu relato até o fim antes de falar.\n\n"
        "— A Sequência está reunida, e os pulsos ficam mais frequentes enquanto ninguém "
        "responde. Há quatro respostas na mesa: Selar, Estabilizar, Entregar aos Herdeiros ou "
        "Destruir. Nenhuma cura o mundo. Seu testemunho fica no registro.",
    ),
}

_SECOND_WITNESS = "\n\nUma segunda testemunha confirma a leitura."


def _witnessed(
    letter: str, text: str, mirror_text: str
) -> tuple[ReadingPoint, ReadingPoint]:
    """Chapter 7: each Leitura is confirmed at 2 points (§2, ``cap_07_obj_01``)."""
    name = f"Leitura {letter.upper()}"
    return (
        ReadingPoint(
            f"lei_cr01_c07_{letter}1",
            f"{name} · 1ª testemunha",
            text,
            f"{name} · 1ª testemunha",
            mirror_text,
        ),
        ReadingPoint(
            f"lei_cr01_c07_{letter}2",
            f"{name} · 2ª testemunha",
            text + _SECOND_WITNESS,
            f"{name} · 2ª testemunha",
            mirror_text + _SECOND_WITNESS,
        ),
    )


READING_STEPS: dict[str, tuple[ReadingPoint, ...]] = {
    "cap_01_obj_03": (
        ReadingPoint(
            "lei_cr01_c01_a",
            "Inscrição apagada",
            "A inscrição apagada ainda guarda o contorno das letras que voltaram durante o pulso.",
        ),
        ReadingPoint(
            "lei_cr01_c01_b",
            "Marco deslocado",
            "O pó assentou fora do lugar, como se o marco tivesse apontado para outra direção.",
        ),
        ReadingPoint(
            "lei_cr01_c01_c",
            "Rastro interrompido",
            "As marcas de patrulha param aqui e recomeçam alguns passos adiante, como se a "
            "rotina tivesse sido interrompida.",
        ),
    ),
    "cap_03_obj_02": (
        ReadingPoint(
            "lei_cr01_c03_a",
            "Raízes contraídas",
            "As raízes guardam a marca do último aperto: cada pulso as contrai no mesmo sentido.",
            "Marca de tensão",
            "A pedra guarda a marca do último pulso, sempre no mesmo sentido.",
        ),
        ReadingPoint(
            "lei_cr01_c03_b",
            "Corda refeita",
            "Os nós foram refeitos depois do último pulso. A anotação ao lado traz um horário "
            "que não bate com o de outra Região.",
            "Anotação de viagem",
            "Uma anotação de viagem registra a hora de um pulso. Comparada à sua, a diferença "
            "é pequena, mas constante.",
        ),
        ReadingPoint(
            "lei_cr01_c03_c",
            "Pedra estalada",
            "A pedra estalou como madeira no frio. A rachadura nova segue a ordem das outras: "
            "primeiro ali, depois aqui.",
            "Rachaduras finas",
            "As rachaduras finas seguem sempre a mesma sequência a cada pulso: primeiro ali, "
            "depois aqui. Existe uma ordem.",
        ),
    ),
    "cap_05_obj_02": (
        ReadingPoint(
            "lei_cr01_c05_a",
            "Válvula antiga",
            "A válvula se move sozinha a cada batida, sem água que a empurre.",
            "Goteira",
            "A água pinga no ritmo do pulso, uma gota a cada batida.",
        ),
        ReadingPoint(
            "lei_cr01_c05_b",
            "Canal isolado",
            "Mesmo com o canal isolado, a lâmina de água treme em compasso.",
            "Poça parada",
            "A água parada treme em círculos, no mesmo compasso.",
        ),
        ReadingPoint(
            "lei_cr01_c05_c",
            "Registro de manutenção",
            "Um registro de manutenção descreve o pulso com duas palavras: sinal de confirmação.",
            "Junta úmida",
            "As juntas da pedra suam a cada pulso e secam logo depois.",
        ),
        ReadingPoint(
            "lei_cr01_c05_d",
            "Juncos curvados",
            "Os juncos se curvam ao mesmo tempo, sem vento, e voltam antes da próxima batida.",
            "Mato curvado",
            "O mato rente ao chão se curva ao mesmo tempo, sem vento, e volta antes da próxima "
            "batida.",
        ),
    ),
    "cap_07_obj_01": (
        *_witnessed(
            "a",
            "A referência do marco aponta para um único ponto à frente.",
            "As marcas do lugar apontam todas para o mesmo lado, mais longe do que antes.",
        ),
        *_witnessed(
            "b",
            "O pulso chega aqui antes de chegar a qualquer outro registro.",
            "O pulso atravessa o lugar com mais força do que em qualquer registro daqui.",
        ),
        *_witnessed(
            "c",
            "Duas versões da mesma inscrição discordam em tudo, menos no último pedido.",
            "Uma cópia da Sequência confere com a inscrição local, linha por linha.",
        ),
        *_witnessed(
            "d",
            "A última linha pede confirmação. Não há marca de que alguém a tenha dado.",
            "A última linha pede confirmação. Não há marca de que alguém a tenha dado.",
        ),
    ),
}

DESBRAVAR_STEPS: dict[str, DesbravarStep] = {
    "cap_01_obj_02": DesbravarStep(
        "dsc_cr01_c01_pulso",
        "A pedra sob seus pés estremece num pulso seco. Numa inscrição que você jurava estar "
        "apagada, as letras voltam por um instante, e a mesma palavra se repete: CONVERGÊNCIA. "
        "Depois, só pedra outra vez.",
    ),
    "cap_02_obj_01": DesbravarStep(
        "dsc_cr01_c02_marcas",
        "A fuligem treme em linhas retas demais. Marcas antigas vibram sem que ninguém as "
        "toque e, a cada batida, os rastros dos Vigias mudam de rumo. Você anota o intervalo "
        "até a próxima.",
        complement=Complement(Layer.C1, "O pulso é mais forte perto da Âncora do Poente."),
    ),
    "cap_04_obj_01": DesbravarStep(
        "dsc_cr01_c04_marcos",
        "Todos os marcos da linha apontam para o mesmo lado, como se alguém tivesse puxado um "
        "fio. Você conta até o pulso passar, e eles voltam ao lugar sem sinal de terem se "
        "movido.",
        "As sombras dos marcos daqui escorregam para um mesmo lado por um instante, pouco, mas "
        "todas juntas. Quando o pulso passa, tudo volta ao lugar.",
    ),
    "cap_06_obj_02": DesbravarStep(
        "dsc_cr01_c06_ordem",
        "Na parede, uma inscrição sem data volta a ficar legível a cada pulso. É uma ordem, "
        "escrita para alguém que já não está aqui, e termina pedindo confirmação.",
        "Riscada numa pedra velha, uma linha volta a aparecer a cada pulso. Você não entende "
        "tudo, mas entende o tom: é uma ordem, e ela espera resposta.",
    ),
    "cap_08_obj_02": DesbravarStep(
        "dsc_cr01_c08_ultima_leitura",
        "O pulso agora vem sem intervalo que se possa anotar. Nas inscrições, a palavra deixa "
        "de se repetir e fica parada, inteira, como quem espera. Você registra a última "
        "leitura antes que ela se apague.",
    ),
}
DESBRAVAR_OBJECTIVES: dict[str, str] = {
    step.result_id: objective_id for objective_id, step in DESBRAVAR_STEPS.items()
}

VESTIGIO_TEXT = (
    "Um resto de pulso corre pela pedra e some. Nada que valha um relatório inteiro, mas você "
    "anota a hora e o lugar para os registradores."
)


def is_chronicle_result(result_id: str | None) -> bool:
    return bool(result_id) and str(result_id).startswith(RESULT_PREFIX)


def with_complement(text: str, complement: Complement | None, layers: frozenset[Layer]) -> str:
    if complement is None or complement.layer not in layers:
        return text
    return f"{text}\n\n{complement.text}"
