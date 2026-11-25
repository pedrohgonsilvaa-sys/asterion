"""O Despertar dos Flagelos: regras puras (sem banco, sem motor, sem texto de interface).

Fonte: ``docs/specs/ASTERION_DESPERTAR_DOS_FLAGELOS_V1_0_0.md`` (especificação V1.0.0) e as
decisões do autor de 2026-11-25 registradas em ``SOURCE_AUTHORITY.md`` como exceção autoral ao
GDD §21 e §49.15. A exceção vale só para os Flagelos: o Evento Mundial genérico
(``domain/world_events.py``) e A Ruptura do Véu não mudam.

O que este módulo NÃO define (configuração pendente, ver ``PENDING``): o catálogo dos 54
equipamentos/receitas especiais (nomes, raridade, Grau, Ofício, classe de armadura, Weapon
Metadata, Proficiência, custos), a raridade/template do equipamento sorteado, os textos de
Bestiário/Códice e as imagens.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.engagement import Bundle
from asterion.domain.veu_bestiary import ActionKind, VeuAction
from asterion.domain.world_events import PARTICIPANT_CAP as _WORLD_EVENT_PARTICIPANT_CAP
from asterion.domain.world_events import REENTRY_DELAY as _WORLD_EVENT_REENTRY_DELAY
from asterion.domain.world_events import reward_xp as _fixed_percent_xp

D = Decimal

RULESET = "flagelo_v1"

# §4: barra regional.
THRESHOLD = 500
# §7.2 e §7.3: capacidade do encontro e relógio da oportunidade de ação.
PARTICIPANT_CAP = 200
assert PARTICIPANT_CAP == _WORLD_EVENT_PARTICIPANT_CAP
TURN_SECONDS = 10
DECISION_WINDOW = timedelta(seconds=TURN_SECONDS)
# §11: reentrada.
REENTRY_DELAY = timedelta(minutes=2)
assert REENTRY_DELAY == _WORLD_EVENT_REENTRY_DELAY
VIGOR_COST = 0  # exceção autoral 1.3

# GDD §49 (PvE compartilhado): 3 oportunidades seguidas sem ação marcam inatividade. O
# Flagelo tira o combatente inativo do combate (conta como saída, com a reentrada de 2 min),
# senão um personagem parado pausaria o escalonamento para sempre.
INACTIVE_ROUNDS = 3

# §8: escalonamento por abandono (exceção autoral 1.2).
SCALING_INTERVAL = timedelta(minutes=15)
HP_STEP = D("0.08")
ATQ_STEP = D("0.03")
HP_CAP = D("0.80")
ATQ_CAP = D("0.30")
MAX_SCALING_STEPS = 10

# §12: participação (exceção autoral 1.4).
PARTICIPATION_MIN = 3

# §14: recompensas (exceção autoral 1.3).
XP_PERCENT = D("0.08")
CROWN_MULTIPLIER = D("0.50")
REWARD_BASICS = 3
REWARD_FLAGELO_FRAGMENTS = 1
EQUIPMENT_PER_DEATH = 1
RANKING_SIZE = 3
# posição -> (Fragmentos do Flagelo, materiais básicos)
RANKING_REWARDS = {1: (3, 3), 2: (2, 2), 3: (1, 1)}
# §16.
RECIPE_DISCOVERY_CHANCE = D("0.25")
RECIPES_PER_FLAGELO = 9

# §4.2: pontos por atividade válida concluída. "Outro PvE equivalente" é configurável: só
# entra aqui quando o autor definir a atividade e o valor.
CONTRIBUTION_POINTS: dict[str, int] = {
    "hunt": 1,
    "group_hunt": 1,
    "desbravar": 1,
    "contract": 2,
    "mission": 4,
    "dungeon": 6,
}

RANKING_CATEGORIES = ("offensive", "defensive", "support")

# Configuração pendente: estrutura existe, conteúdo não. Nada aqui é canônico.
PENDING = frozenset(
    {
        "equipment_catalog",  # 54 templates: nomes, raridade, Grau, Ofício, armadura, armas
        "equipment_drop_rarity",
        "recipe_costs",
        "bestiary_codex_texts",
        "images",
    }
)


# ------------------------------------------------------------------ catálogo


def _hit(key: str, label: str, coefficient: str, cooldown: int | None = None) -> VeuAction:
    return VeuAction(key, label, ActionKind.DAMAGE, D(coefficient), cooldown)


def _hit_debuff(key: str, label: str, coefficient: str, stat: str, cooldown: int) -> VeuAction:
    return VeuAction(
        key,
        label,
        ActionKind.DAMAGE_DEBUFF,
        D(coefficient),
        cooldown,
        stat=stat,
        magnitude=-D("0.10"),
        turns=2,
    )


def _aoe(key: str, label: str, coefficient: str, cooldown: int | None = None, **extra) -> VeuAction:
    return VeuAction(key, label, ActionKind.AOE, D(coefficient), cooldown, **extra)


def _prepared(key: str, label: str) -> VeuAction:
    return VeuAction(key, label, ActionKind.DAMAGE, D("1.80"), 5, prepared=True)


@dataclass(frozen=True, slots=True)
class FlageloDefinition:
    flagelo_id: str
    name: str  # "Varkhenn, o Flagelo das Cinzas"
    short_name: str  # "Varkhenn"
    level: int
    hp: int
    attack: int
    defense: int
    agility: int
    actions: tuple[VeuAction, ...]
    fragment_material_id: str
    fragment_name: str

    @property
    def basic_action(self) -> VeuAction:
        return self.actions[0]

    @property
    def bestiary_key(self) -> str:
        return f"bestiary.flagelo.{self.flagelo_id}"

    @property
    def codex_key(self) -> str:
        return f"codex.flagelo.{self.flagelo_id}"

    def recipe_unlock_ids(self) -> tuple[str, ...]:
        """Receitas especiais do Flagelo: vazio até o catálogo final (``PENDING``)."""
        return FLAGELO_RECIPES.get(self.flagelo_id, ())


@dataclass(frozen=True, slots=True)
class FlageloRegion:
    region_id: str  # mesmo id regional do repositório (``knowledge_catalog``)
    region: str  # nome da Região como em ``WorldState.region``
    short_label: str  # rótulo do HUD (§17)
    emoji: str
    contract_region: str  # id regional dos Contratos (R1..R6)
    mission_region: str  # id regional do catálogo narrativo das Missões
    flagelo: FlageloDefinition

    @property
    def reference_level(self) -> int:
        return self.flagelo.level


REGIONS: tuple[FlageloRegion, ...] = (
    FlageloRegion(
        "tdo",
        "Terras do Ocaso",
        "Ocaso",
        "🌑",
        "R1",
        "terras_do_ocaso",
        FlageloDefinition(
            "varkhenn",
            "Varkhenn, o Flagelo das Cinzas",
            "Varkhenn",
            10,
            35_060,
            138,
            100,
            94,
            (
                _hit("golpe_de_cinza", "Golpe de Cinza", "1.00"),
                _aoe(
                    "sopro_de_fuligem",
                    "Sopro de Fuligem",
                    "0.80",
                    dot_kind="burn",
                    dot_stacks=1,
                ),
                _hit_debuff("cinza_no_pulso", "Cinza no Pulso", "0.90", "ATQ", 3),
                _hit("peso_do_entulho", "Peso do Entulho", "1.30", 3),
                _prepared("ultima_fagulha", "Última Fagulha"),
            ),
            "material.flagelo.fragmento_cinza_condensada",
            "Fragmento de Cinza Condensada",
        ),
    ),
    FlageloRegion(
        "vde",
        "Vales dos Enforcados",
        "Vales",
        "🪢",
        "R2",
        "vales_dos_enforcados",
        FlageloDefinition(
            "nharvek",
            "Nharvek, o Flagelo dos Laços",
            "Nharvek",
            20,
            51_000,
            195,
            120,
            101,
            (
                _hit("golpe_do_laco", "Golpe do Laço", "1.00"),
                _hit_debuff("tranco_das_raizes", "Tranco das Raízes", "0.90", "AGI", 3),
                _hit_debuff("no_de_peso", "Nó de Peso", "1.20", "DEF", 3),
                _aoe("tensao_compartilhada", "Tensão Compartilhada", "0.80"),
                _prepared("estrangulamento_final", "Estrangulamento Final"),
            ),
            "material.flagelo.fibra_laco_morto",
            "Fibra do Laço Morto",
        ),
    ),
    FlageloRegion(
        "nareth",
        "Planícies de Nareth",
        "Nareth",
        "🌾",
        "R3",
        "planicies_de_nareth",
        FlageloDefinition(
            "azharel",
            "Azharel, o Flagelo do Meridiano",
            "Azharel",
            30,
            53_300,
            198,
            160,
            165,
            (
                _hit("golpe_de_referencia", "Golpe de Referência", "1.00"),
                _hit_debuff("correcao_de_linha", "Correção de Linha", "0.90", "DEF", 3),
                _hit("medida_contraria", "Medida Contrária", "1.25", 3),
                _aoe(
                    "meridiano_divergente",
                    "Meridiano Divergente",
                    "0.80",
                    4,
                    stat="AGI",
                    magnitude=-D("0.10"),
                    turns=2,
                ),
                _prepared("linha_absoluta", "Linha Absoluta"),
            ),
            "material.flagelo.marco_meridiano_partido",
            "Marco do Meridiano Partido",
        ),
    ),
    FlageloRegion(
        "varzeas",
        "Várzeas Carmesins",
        "Várzeas",
        "🥀",
        "R4",
        "varzeas_carmesins",
        FlageloDefinition(
            "hemrath",
            "Hemrath, o Flagelo Rubro",
            "Hemrath",
            40,
            63_880,
            320,
            177,
            190,
            (
                _hit("golpe_de_salmoura", "Golpe de Salmoura", "1.00"),
                _hit_debuff("pressao_de_valvula", "Pressão de Válvula", "0.90", "DEF", 3),
                VeuAction(
                    "soro_corrosivo",
                    "Soro Corrosivo",
                    ActionKind.DAMAGE,
                    D("0.85"),
                    3,
                    dot_kind="poison",
                    dot_stacks=1,
                ),
                VeuAction(
                    "restituicao_rubra",
                    "Restituição Rubra",
                    ActionKind.HEAL,
                    None,
                    5,
                    heal_hp_fraction=D("0.05"),
                    max_uses=3,
                ),
                _prepared("sobrecarga_de_matriz", "Sobrecarga de Matriz"),
            ),
            "material.flagelo.coagulo_salmoura_rubra",
            "Coágulo de Salmoura Rubra",
        ),
    ),
    FlageloRegion(
        "altos",
        "Altos Cinéreos",
        "Altos",
        "⛰️",
        "R5",
        "altos_cinereos",
        FlageloDefinition(
            "korvann",
            "Korvann, o Flagelo do Contrapeso",
            "Korvann",
            50,
            98_740,
            310,
            306,
            204,
            (
                _hit("golpe_de_contrapeso", "Golpe de Contrapeso", "1.00"),
                _hit_debuff("carga_distribuida", "Carga Distribuída", "0.90", "DEF", 3),
                VeuAction(
                    "escora_inversa",
                    "Escora Inversa",
                    ActionKind.SELF_BUFF,
                    None,
                    5,
                    stat="ATQ",
                    magnitude=D("0.08"),
                    turns=2,
                    second_stat="DEF",
                    second_magnitude=-D("0.08"),
                ),
                _aoe("ruptura_de_cabo", "Ruptura de Cabo", "0.85", 4),
                _prepared("queda_do_contrapeso", "Queda do Contrapeso"),
            ),
            "material.flagelo.peso_fraturado",
            "Peso Fraturado",
        ),
    ),
    FlageloRegion(
        "confins_do_veu",
        "Confins do Véu",
        "Confins",
        "🌫️",
        "R6",
        "confins_do_veu",
        FlageloDefinition(
            "vaelith",
            "Vaelith, o Flagelo da Fratura",
            "Vaelith",
            60,
            107_840,
            401,
            322,
            334,
            (
                _hit("golpe_desalinhado", "Golpe Desalinhado", "1.00"),
                _hit_debuff("duas_leituras", "Duas Leituras", "0.90", "ATQ", 3),
                _hit("reflexo_partido", "Reflexo Partido", "1.25", 3),
                _aoe("fratura_local", "Fratura Local", "0.80"),
                _prepared("protocolo_incompativel", "Protocolo Incompatível"),
            ),
            "material.flagelo.fragmento_leitura_incompativel",
            "Fragmento de Leitura Incompatível",
        ),
    ),
)

REGIONS_BY_ID = {region.region_id: region for region in REGIONS}
REGIONS_BY_NAME = {region.region: region for region in REGIONS}
REGIONS_BY_CONTRACT = {region.contract_region: region for region in REGIONS}
REGIONS_BY_MISSION = {region.mission_region: region for region in REGIONS}
FLAGELOS_BY_ID = {region.flagelo.flagelo_id: region for region in REGIONS}
FRAGMENT_NAMES = {
    region.flagelo.fragment_material_id: region.flagelo.fragment_name for region in REGIONS
}

# Catálogo final pendente (§15–§16): nenhuma receita/template até o autor fechar os dados.
FLAGELO_RECIPES: dict[str, tuple[str, ...]] = {}
# Equipamento sorteado: sem template até o catálogo final. ``None`` = sorteio registrado,
# entrega pendente de catálogo.
FLAGELO_EQUIPMENT_TEMPLATES: dict[str, tuple[str, ...]] = {}


def region(region_id: str) -> FlageloRegion:
    return REGIONS_BY_ID[region_id]


def kit(flagelo_id: str) -> tuple[VeuAction, ...]:
    return FLAGELOS_BY_ID[flagelo_id].flagelo.actions


def action(flagelo_id: str, key: str) -> VeuAction:
    return next(item for item in kit(flagelo_id) if item.key == key)


# ------------------------------------------------------------------ contribuição


def contribution_points(kind: str) -> int:
    """0 = atividade não configurada (não contribui)."""
    return CONTRIBUTION_POINTS.get(kind, 0)


def apply_points(current: int, points: int, *, frozen: bool) -> tuple[int, int]:
    """(nova barra, pontos efetivamente somados). Barra congelada não soma (§5.2).

    A barra é ``atual / 500``: o que passar de 500 não é guardado.
    """
    if frozen or points <= 0:
        return current, 0
    new = min(THRESHOLD, current + points)
    return new, new - current


def percent(points: int) -> int:
    """Percentual derivado da quantidade absoluta (§4.1), arredondado para baixo."""
    return max(0, min(100, points * 100 // THRESHOLD))


# ------------------------------------------------------------------ escalonamento


@dataclass(frozen=True, slots=True)
class Scaling:
    steps: int
    hp_bonus: Decimal
    atq_bonus: Decimal


def scaling_for_steps(steps: int) -> Scaling:
    steps = max(0, min(MAX_SCALING_STEPS, steps))
    return Scaling(steps, min(HP_CAP, HP_STEP * steps), min(ATQ_CAP, ATQ_STEP * steps))


def due_steps(
    current_steps: int, idle_since: datetime | None, now: datetime, active_combatants: int
) -> int:
    """Passos devidos: 1 a cada 15 min completos sem ninguém em combate (§8).

    ``idle_since`` é o início da ausência atual (ou o último passo aplicado). Com alguém em
    combate o escalonamento fica pausado e nada é devido.
    """
    if active_combatants > 0 or idle_since is None or current_steps >= MAX_SCALING_STEPS:
        return 0
    elapsed = now - idle_since
    if elapsed < SCALING_INTERVAL:
        return 0
    return min(MAX_SCALING_STEPS - current_steps, int(elapsed // SCALING_INTERVAL))


def _round(value: Decimal) -> int:
    """GDD v1.4.9: atributo estático final fecha uma vez com ``round_half_up``."""
    return int(value.quantize(D(1), rounding=ROUND_HALF_UP))


def effective_max_hp(base_hp: int, hp_bonus: Decimal) -> int:
    return _round(D(base_hp) * (D(1) + hp_bonus))


def effective_attack(base_attack: int, atq_bonus: Decimal) -> int:
    return _round(D(base_attack) * (D(1) + atq_bonus))


# ------------------------------------------------------------------ IA


def choose_action(
    flagelo_id: str,
    *,
    cooldowns: dict[str, int],
    uses: dict[str, int],
    hp: Decimal,
    max_hp: Decimal,
    skip: Iterable[str] = (),
) -> VeuAction:
    """IA simples e determinística (decisão do autor, 2026-11-25).

    1. ação Preparada fora de recarga; 2. ação especial elegível de maior prioridade;
    3. ataque básico. Prioridade entre especiais: maior recarga primeiro (a especial sem
    recarga por último), empate pela ordem do kit na especificação. ``skip`` recalcula
    quando a ação escolhida não pode ser executada.
    """
    skipped = set(skip)
    actions = kit(flagelo_id)
    basic = actions[0]

    def eligible(item: VeuAction) -> bool:
        if item.key in skipped or cooldowns.get(item.key, 0) > 0:
            return False
        if item.max_uses is not None and uses.get(item.key, 0) >= item.max_uses:
            return False
        # Cura própria com HP cheio não muda estado nenhum: não é executável.
        return not (item.kind is ActionKind.HEAL and hp >= max_hp)

    prepared = [item for item in actions[1:] if item.prepared and eligible(item)]
    if prepared:
        return prepared[0]
    specials = [
        (index, item)
        for index, item in enumerate(actions[1:], start=1)
        if not item.prepared and eligible(item)
    ]
    if specials:
        specials.sort(key=lambda pair: (-(pair[1].cooldown or 0), pair[0]))
        return specials[0][1]
    return basic


def seed_for(flagelo_key: str, round_number: int) -> int:
    digest = hashlib.sha256(f"{flagelo_key}:{round_number}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def choose_targets(item: VeuAction, present: Sequence, seed: int) -> tuple:
    """Alvos: todos os presentes em AoE; senão um alvo por rotação semeada (como o Véu)."""
    ordered = sorted(present, key=str)
    if not ordered or item.kind in (ActionKind.SELF_BUFF, ActionKind.HEAL, ActionKind.BARRIER):
        return ()
    if item.kind is ActionKind.AOE:
        return tuple(ordered)
    count = min(item.targets or 1, len(ordered))
    start = (seed // 7) % len(ordered)
    return tuple(ordered[(start + step) % len(ordered)] for step in range(count))


# ------------------------------------------------------------------ participação


@dataclass(frozen=True, slots=True)
class ParticipationMetrics:
    effective_damage: int = 0
    effective_healing: int = 0
    barrier_absorbed: int = 0
    defender_prevented_damage: int = 0
    meaningful_effects: int = 0


def participation_points(metrics: ParticipationMetrics) -> int:
    """§12: +1 por categoria com resultado real; entrar ou só agir não pontua."""
    return sum(
        1
        for value in (
            metrics.effective_damage,
            metrics.effective_healing,
            metrics.barrier_absorbed,
            metrics.defender_prevented_damage,
            metrics.meaningful_effects,
        )
        if value > 0
    )


def is_eligible(metrics: ParticipationMetrics) -> bool:
    return participation_points(metrics) >= PARTICIPATION_MIN


def ranking_metric(category: str, metrics: ParticipationMetrics) -> int:
    if category == "offensive":
        return metrics.effective_damage
    if category == "defensive":
        return metrics.defender_prevented_damage + metrics.barrier_absorbed
    if category == "support":
        return metrics.effective_healing
    raise ValueError(category)


@dataclass(frozen=True, slots=True)
class RankingEntry:
    character_id: object
    metrics: ParticipationMetrics
    reached_at: datetime | None  # quando a métrica atingiu o valor registrado (backend)


def rank(category: str, entries: Iterable[RankingEntry]) -> list[RankingEntry]:
    """Top 3 (§13). Desempate: métrica, Participation Points, momento em que atingiu a
    métrica (mais cedo primeiro), ``character_id``. Métrica zero não entra."""
    scored = [entry for entry in entries if ranking_metric(category, entry.metrics) > 0]
    far = datetime.max.replace(tzinfo=None)
    scored.sort(
        key=lambda entry: (
            -ranking_metric(category, entry.metrics),
            -participation_points(entry.metrics),
            (entry.reached_at.replace(tzinfo=None) if entry.reached_at else far),
            str(entry.character_id),
        )
    )
    return scored[:RANKING_SIZE]


# ------------------------------------------------------------------ recompensa


def reward_bundle(reference_level: int) -> Bundle:
    """§14: ``0,50×C`` (arredondamento global ``round_10``) + 3 materiais básicos."""
    return Bundle(
        crowns=round_10(CROWN_MULTIPLIER * crowns_per_level(reference_level)),
        basics=REWARD_BASICS,
    )


def reward_xp(level_requirement: int) -> int:
    """``0,08 × XP(reference_level)`` com o mesmo ``FixedPercentXP`` do GDD §49.7."""
    assert XP_PERCENT == D("0.08")
    return _fixed_percent_xp(level_requirement)


def _draw(seed: str) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big")


def equipment_winner(flagelo_key: str, eligible: Sequence) -> object | None:
    """Exatamente 1 equipamento por morte, chance igual entre os elegíveis (§14).

    Sorteio determinístico pela identidade da ocorrência: retry/restart sorteia o mesmo.
    """
    ordered = sorted(eligible, key=str)
    if not ordered:
        return None
    return ordered[_draw(f"{flagelo_key}:equipment") % len(ordered)]


def recipe_roll(flagelo_key: str, character_id, unknown: Sequence[str]) -> str | None:
    """25% por morte enquanto houver receita desconhecida, sem pity (§16).

    Determinístico por ocorrência e personagem. Com o catálogo vazio, nunca descobre.
    """
    options = sorted(unknown)
    if not options:
        return None
    draw = _draw(f"{flagelo_key}:{character_id}:recipe")
    if D(draw % 10_000) >= RECIPE_DISCOVERY_CHANCE * 10_000:
        return None
    return options[(draw // 10_000) % len(options)]
