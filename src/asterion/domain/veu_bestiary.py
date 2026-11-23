"""Bestiário do Véu: as 18 criaturas de A Ruptura do Véu (VEU-01..VEU-18).

Fonte: especificação do Evento Mundial A Ruptura do Véu (§7 e §8). Este módulo só
registra o que a fonte declara: nome, categoria, arquétipo, porte, morfologia e kit.
Nada aqui é número novo.

Pontos que a fonte NÃO define ficam explícitos e não resolvidos:

- Duração de Barreira: ``duration`` é sempre ``None``. No motor, duração 0 não concede
  Barreira, então nenhuma Barreira do Véu pode ser convertida sem decisão do autor.
- Arquétipos Resistente, Técnico e Suporte (e o "Equilibrado/Controlador" do Chefe) não
  têm perfil de motor definido: ``engine_archetype`` fica ``None``.

Este módulo não altera o motor de combate. Converter um kit em ``road.Creature`` é
trabalho da etapa de integração de combate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from asterion.domain.combat_math import CombatStats, enemy_stats
from asterion.domain.road import ARCHETYPE, CATEGORY
from asterion.domain.world_events import phase_scale

D = Decimal

EVENT_REFERENCE_LEVEL = 30

# Perfil de motor só onde o repositório já mapeia o rótulo de conteúdo
# (``creature_kits.PROFILE_ARCHETYPE``) ou onde o nome é o do próprio motor.
ENGINE_ARCHETYPE = {
    "Bruto": "brute",
    "Equilibrado": "balanced",
    "Ágil": "predator",
    "Blindado": "armored",
    "Controlador": "controller",
    "Predador": "predator",
}


class UnresolvedArchetypeError(ValueError):
    """The source gives no engine profile for this archetype (author decision pending)."""


class Category(StrEnum):
    """Same keys as ``road.CATEGORY``; the spec's "Chefe de ocorrência" is ``boss``."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    ELITE = "elite"
    BOSS = "boss"


class ActionKind(StrEnum):
    DAMAGE = "damage"
    DAMAGE_DEBUFF = "damage_debuff"  # dano + debuff no alvo
    DEBUFF = "debuff"  # só debuff no alvo
    SELF_BUFF = "self_buff"
    BARRIER = "barrier"
    AOE = "aoe"
    MULTI_TARGET = "multi_target"  # "contra dois alvos válidos"


@dataclass(frozen=True, slots=True)
class VeuAction:
    key: str
    label: str
    kind: ActionKind
    # Fração de ATQ (1.00 = 100% ATQ). ``None`` quando a ação não causa dano.
    coefficient: Decimal | None = None
    cooldown: int | None = None  # CD da fonte; ``None`` = sem CD declarado
    stat: str | None = None  # ATQ | DEF | AGI | PER
    magnitude: Decimal | None = None  # com sinal: -0.10 = −10%
    turns: int | None = None
    targets: int | None = None
    barrier_attack_coefficient: Decimal | None = None  # "Barreira 60% ATQ"
    barrier_hp_fraction: Decimal | None = None  # "Barreira 6% HP Máximo"
    # Fonte não define duração de Barreira. Sempre ``None`` até decisão autoral.
    duration: int | None = None
    prepared: bool = False
    always_telegraphed: bool = False
    not_consecutive: bool = False
    max_uses: int | None = None


@dataclass(frozen=True, slots=True)
class VeuCreature:
    code: str  # VEU-01
    creature_id: str  # veu_01_mandibula_vigilia (também o sufixo do asset)
    name: str
    category: Category
    archetype: str  # rótulo da fonte
    size: str
    morphology: str
    actions: tuple[VeuAction, ...]
    function: str = ""
    fear: str = ""
    notes: tuple[str, ...] = ()

    @property
    def engine_archetype(self) -> str | None:
        return ENGINE_ARCHETYPE.get(self.archetype)

    @property
    def bestiary_key(self) -> str:
        """``bestiary.veu.01_mandibula_vigilia`` (§25.2)."""
        return "bestiary.veu." + self.creature_id.removeprefix("veu_")

    @property
    def asset_key(self) -> str:
        return f"event_{self.creature_id}"


def _hit(key: str, label: str, coefficient: str, cooldown: int | None = None) -> VeuAction:
    return VeuAction(key, label, ActionKind.DAMAGE, D(coefficient), cooldown)


def _hit_debuff(
    key: str, label: str, coefficient: str, stat: str, pct: str, cooldown: int
) -> VeuAction:
    return VeuAction(
        key, label, ActionKind.DAMAGE_DEBUFF, D(coefficient), cooldown,
        stat=stat, magnitude=-D(pct), turns=2,
    )


def _debuff(key: str, label: str, stat: str, pct: str, cooldown: int) -> VeuAction:
    return VeuAction(
        key, label, ActionKind.DEBUFF, None, cooldown, stat=stat, magnitude=-D(pct), turns=2
    )


def _self_buff(key: str, label: str, stat: str, pct: str, cooldown: int) -> VeuAction:
    return VeuAction(
        key, label, ActionKind.SELF_BUFF, None, cooldown, stat=stat, magnitude=D(pct), turns=2
    )


def _barrier_atk(key: str, label: str, coefficient: str, cooldown: int, **extra) -> VeuAction:
    return VeuAction(
        key, label, ActionKind.BARRIER, None, cooldown,
        barrier_attack_coefficient=D(coefficient), **extra,
    )


def _barrier_hp(key: str, label: str, fraction: str, cooldown: int | None, **extra) -> VeuAction:
    return VeuAction(
        key, label, ActionKind.BARRIER, None, cooldown,
        barrier_hp_fraction=D(fraction), **extra,
    )


def _aoe(key: str, label: str, coefficient: str, cooldown: int) -> VeuAction:
    return VeuAction(key, label, ActionKind.AOE, D(coefficient), cooldown)


def _two_targets(key: str, label: str, coefficient: str, cooldown: int) -> VeuAction:
    return VeuAction(key, label, ActionKind.MULTI_TARGET, D(coefficient), cooldown, targets=2)


VEU_CREATURES: tuple[VeuCreature, ...] = (
    VeuCreature(
        "VEU-01", "veu_01_mandibula_vigilia", "Mandíbula de Vigília", Category.COMMON,
        "Predador", "Médio",
        "Corpo quadrúpede baixo, mas sem cabeça convencional. O tórax termina em uma "
        "mandíbula vertical enorme que abre do peito até quase o abdômen. Pequenos olhos "
        "ficam distribuídos na parte superior do dorso, como pontos de observação.",
        (
            _hit("mordida_vertical", "Mordida Vertical", "1.00"),
            _hit_debuff("fechamento_subito", "Fechamento Súbito", "0.90", "AGI", "0.10", 3),
        ),
        function="ameaça corpo a corpo",
        fear="A criatura parece estar olhando para você mesmo quando sua boca está fechada.",
        notes=("Defender: regra global.", "Sem Hard CC."),
    ),
    VeuCreature(
        "VEU-02", "veu_02_oito_pulsos", "Oito-Pulsos", Category.COMMON, "Equilibrado", "Médio",
        "Massa baixa e larga, com seis membros de formatos diferentes. O centro pulsa "
        "lentamente, como um órgão exposto protegido por placas finas.",
        (
            _hit("pulso_de_carne", "Pulso de Carne", "1.00"),
            _two_targets("pulsacao_irregular", "Pulsação Irregular", "0.80", 3),
        ),
        function="pressão contra vários alvos",
    ),
    VeuCreature(
        "VEU-03", "veu_03_costela_andante", "Costela Andante", Category.COMMON,
        "Resistente", "Médio",
        "Estrutura vertical composta por costelas sobrepostas. Não existe corpo "
        "convencional dentro delas; há tecido escuro se movendo entre os espaços.",
        (
            _hit("impacto_costal", "Impacto Costal", "1.00"),
            _barrier_atk("fechamento_toracico", "Fechamento Torácico", "0.60", 4),
        ),
    ),
    VeuCreature(
        "VEU-04", "veu_04_devorador_de_rostos", "Devorador de Rostos", Category.UNCOMMON,
        "Controlador", "Médio",
        "Corpo alongado, sem rosto. A parte frontal é uma cavidade lisa que pode formar "
        "temporariamente uma face humana incompleta.",
        (
            _hit("mordida_lisa", "Mordida Lisa", "1.00"),
            _hit_debuff("rosto_errado", "Rosto Errado", "0.85", "PER", "0.10", 3),
        ),
        notes=("Não usar medo como Hard CC.",),
    ),
    VeuCreature(
        "VEU-05", "veu_05_nascido_ao_contrario", "Nascido ao Contrário", Category.UNCOMMON,
        "Ágil", "Médio",
        "Quatro pernas dobram para dentro. Braços surgem das costas. A cabeça fica "
        "voltada para baixo, entre os membros.",
        (
            _hit("investida_invertida", "Investida Invertida", "1.10"),
            _self_buff("passo_impossivel", "Passo Impossível", "AGI", "0.10", 4),
        ),
    ),
    VeuCreature(
        "VEU-06", "veu_06_carapaca_de_carne", "Carapaça de Carne", Category.UNCOMMON,
        "Blindado", "Grande",
        "Grandes placas semelhantes a carapaça recobrem um corpo de músculo exposto. As "
        "placas se movem independentemente como peças de uma armadura viva.",
        (
            _hit("golpe_de_placa", "Golpe de Placa", "1.00"),
            _barrier_atk("recompor_carapaca", "Recompor Carapaça", "0.80", 4),
        ),
    ),
    VeuCreature(
        "VEU-07", "veu_07_colmeia_vazia", "Colmeia Vazia", Category.ELITE,
        "Controlador", "Grande",
        "Estrutura orgânica ambulante cheia de cavidades vazias. Algumas cavidades se "
        "abrem e fecham sem que nada saia delas.",
        (
            _hit("abertura", "Abertura", "1.00"),
            _aoe("chamado_oco", "Chamado Oco", "0.75", 3),
            _barrier_hp("camara_fechada", "Câmara Fechada", "0.06", 4),
        ),
        notes=("Sem invocação automática na primeira versão.",),
    ),
    VeuCreature(
        "VEU-08", "veu_08_tres_queixos", "Três-Queixos", Category.COMMON, "Predador", "Médio",
        "Três pernas sustentam um corpo curto com três mandíbulas independentes que se "
        "movimentam em ritmos diferentes.",
        (
            _hit("mordida_tripla", "Mordida Tripla", "1.00"),
            _hit("mordida_cruzada", "Mordida Cruzada", "1.20", 3),
        ),
    ),
    VeuCreature(
        "VEU-09", "veu_09_tecelao_de_ossos", "Tecelão de Ossos", Category.ELITE,
        "Técnico", "Grande",
        "Figura alta e fina com seis braços. Dedos ósseos extremamente longos. Carrega e "
        "reorganiza fragmentos de osso e pedra como se fossem fios.",
        (
            _hit("corte_de_ossatura", "Corte de Ossatura", "1.00"),
            _debuff("trama_ossea", "Trama Óssea", "DEF", "0.10", 3),
            _barrier_atk("costura_de_margem", "Costura de Margem", "0.70", 4),
        ),
    ),
    VeuCreature(
        "VEU-10", "veu_10_vazio_vestido", "Vazio Vestido", Category.ELITE,
        "Equilibrado", "Grande",
        "Casca humanoide vazia. Dentro dela existe outra criatura, visível apenas quando "
        "a casca se abre.",
        (
            _hit("golpe_da_casca", "Golpe da Casca", "1.00"),
            _hit("abertura_interna", "Abertura Interna", "1.35", 4),
            _barrier_hp("fechar_se", "Fechar-se", "0.07", 4),
        ),
    ),
    VeuCreature(
        "VEU-11", "veu_11_fauce_de_veu", "Fauce de Véu", Category.UNCOMMON,
        "Predador", "Grande",
        "Corpo rasteiro cuja boca ocupa quase todo o comprimento. Pequenas estruturas "
        "semelhantes a mãos percorrem o chão para localizar movimento.",
        (
            _hit("fauce", "Fauce", "1.10"),
            _hit_debuff("arrasto", "Arrasto", "0.90", "AGI", "0.10", 3),
        ),
    ),
    VeuCreature(
        "VEU-12", "veu_12_amontoado", "Amontoado", Category.ELITE, "Bruto", "Grande",
        "Várias anatomias incompatíveis fundidas em uma única massa. Não deve parecer uma "
        "coleção aleatória de animais; a fusão deve parecer uma anatomia que perdeu sua "
        "unidade.",
        (
            _hit("impacto_irregular", "Impacto Irregular", "1.05"),
            _hit_debuff("torcao", "Torção", "0.85", "ATQ", "0.10", 3),
            _hit("pressao_de_massa", "Pressão de Massa", "1.30", 4),
        ),
    ),
    VeuCreature(
        "VEU-13", "veu_13_coluna_sem_corpo", "Coluna sem Corpo", Category.COMMON,
        "Ágil", "Médio",
        "Uma coluna vertebral enorme se move apoiada em pequenos pontos ósseos que se "
        "abrem e fecham como patas. Não existe cabeça.",
        (
            _hit("estalo_vertebral", "Estalo Vertebral", "1.00"),
            _self_buff("salto_de_junta", "Salto de Junta", "AGI", "0.10", 4),
        ),
    ),
    VeuCreature(
        "VEU-14", "veu_14_boca_de_pedra_mole", "Boca de Pedra Mole", Category.UNCOMMON,
        "Resistente", "Grande",
        "Bloco mineral que parece pedra, mas se dobra como carne. Uma abertura vertical "
        "funciona como boca.",
        (
            _hit("esmagamento", "Esmagamento", "1.00"),
            _self_buff("pele_maleavel", "Pele Maleável", "DEF", "0.10", 4),
        ),
    ),
    VeuCreature(
        "VEU-15", "veu_15_o_portador_de_dentro", "O Portador de Dentro", Category.ELITE,
        "Suporte", "Grande",
        "Corpo humanoide curvado carregando outra massa viva no interior do torso. A "
        "massa interna tenta empurrar as costelas para fora.",
        (
            _hit("golpe_do_portador", "Golpe do Portador", "1.00"),
            _two_targets("movimento_interno", "Movimento Interno", "0.90", 3),
            _barrier_hp("expulsao", "Expulsão", "0.06", 4),
        ),
    ),
    VeuCreature(
        "VEU-16", "veu_16_o_corpo_que_falta", "O Corpo que Falta", Category.ELITE,
        "Técnico", "Médio",
        "Partes do corpo parecem estar ausentes, mas ainda sustentam peso. Braço termina "
        "antes da mão; perna termina antes do pé; a criatura continua se movendo "
        "normalmente.",
        (
            _hit("golpe_ausente", "Golpe Ausente", "1.00"),
            _hit_debuff("falha_de_contorno", "Falha de Contorno", "0.85", "DEF", "0.10", 3),
        ),
    ),
    VeuCreature(
        "VEU-17", "veu_17_a_testemunha_sem_olhos", "A Testemunha Sem Olhos", Category.ELITE,
        "Controlador", "Grande",
        "Corpo alto, sem olhos, sem face e sem cabeça funcional. Pequenas estruturas no "
        "torso se orientam para cada movimento ao redor.",
        (
            _hit("golpe_de_testemunho", "Golpe de Testemunho", "1.00"),
            _debuff("fixar_presenca", "Fixar Presença", "PER", "0.10", 3),
            _aoe("observacao_total", "Observação Total", "0.70", 4),
        ),
    ),
    VeuCreature(
        "VEU-18", "veu_18_rei_que_nao_existe", "O Rei que Não Existe", Category.BOSS,
        "Equilibrado/Controlador", "Colossal",
        "Não usar coroa ou trono. É uma figura vertical de placas, membros e cavidades, "
        "como uma estrutura administrativa que perdeu a função. O \"rosto\" é uma placa "
        "lisa com marcas contraditórias. A criatura não deve ser apresentada como rei "
        "literal. O nome é uma contradição percebida pelos personagens.",
        (
            _hit("golpe_da_margem", "Golpe da Margem", "1.00"),
            _hit_debuff("medida_contraditoria", "Medida Contraditória", "0.90", "DEF", "0.10", 3),
            _aoe("linha_impossivel", "Linha Impossível", "0.75", 3),
            VeuAction(
                "preparar_a_ruptura", "Preparar a Ruptura", ActionKind.DAMAGE, D("1.75"), 5,
                prepared=True, always_telegraphed=True, not_consecutive=True,
            ),
            _barrier_hp("recompor_a_margem", "Recompor a Margem", "0.08", None, max_uses=2),
        ),
        function="Chefe final da Fase III.",
        notes=("Sem Hard CC recorrente.",),
    ),
)

CREATURES_BY_CODE = {creature.code: creature for creature in VEU_CREATURES}
CREATURES_BY_ID = {creature.creature_id: creature for creature in VEU_CREATURES}

BOSS_FINAL_FORM_HP_FRACTION = D("0.35")


def boss_in_final_form(hp_fraction: Decimal) -> bool:
    """VEU-18, forma Ruptura: HP ≤ 35% (única fronteira que a fonte fixa sem ambiguidade).

    A fonte também cita 70% ("100% → 70%", "70% → 35%") sem dizer a que forma o próprio
    70% pertence; esse limite não tem comportamento aqui (``BLOCKED_RULES``).
    """
    if not D(0) <= hp_fraction <= D(1):
        raise ValueError("hp_fraction must be between 0 and 1")
    return hp_fraction <= BOSS_FINAL_FORM_HP_FRACTION


def creature(code_or_id: str) -> VeuCreature:
    found = CREATURES_BY_CODE.get(code_or_id) or CREATURES_BY_ID.get(code_or_id)
    if found is None:
        raise KeyError(code_or_id)
    return found


def stats_for(category: Category, engine_archetype: str, participants: int) -> CombatStats:
    """Atributos de encontro: categoria × arquétipo × escala de fase (§8.1–§8.3).

    O Chefe usa a categoria ``boss`` (HP 220%, ATQ 110%, DEF 110%, AGI 100%) e não a base
    de Masmorra Solo. Sem Sintonização: o nível é sempre o de referência do Evento.
    """
    return enemy_stats(
        EVENT_REFERENCE_LEVEL,
        CATEGORY[category.value],
        ARCHETYPE[engine_archetype],
        phase_scale(participants),
    )


def creature_stats(creature_: VeuCreature, participants: int) -> CombatStats:
    """Falha explicitamente quando a fonte não mapeia o arquétipo para o motor."""
    if creature_.engine_archetype is None:
        raise UnresolvedArchetypeError(
            f"{creature_.code}: archetype {creature_.archetype!r} has no engine profile"
        )
    return stats_for(creature_.category, creature_.engine_archetype, participants)
