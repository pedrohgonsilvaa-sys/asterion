"""Catálogo e seleção de Flavor Text contextual (GDD v1.6.0 §37.4 e §49.17).

Flavor é só apresentação: nada aqui lê ou grava estado do jogo. O chamador passa
um ``FlavorContext`` (onde o personagem está e o que ele já sabe, como flags
opacas) e recebe uma entrada. A escolha é determinística: o mesmo contexto na
mesma janela de estabilidade devolve sempre a mesma entrada, então clique,
paginação e redesenho da tela não sorteiam de novo (§37.4.4).

Entradas em rascunho (``draft=True``) só aparecem quando o chamador pede
``include_drafts=True``. Os textos ficam em ``flavor_catalog.py``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum


class FlavorKind(StrEnum):
    SYSTEM = "system"  # telas funcionais (§37.4.1)
    NARRATIVE = "narrative"  # mundo: região, local, desbravar, masmorra... (§37.4.2)
    MICRO_COMBAT = "micro_combat"  # resultados curtos de combate (§49.17)


# §49.17: (recomendado_min, recomendado_max, limite_duro) em caracteres.
LENGTH_LIMITS: dict[FlavorKind, tuple[int, int, int]] = {
    FlavorKind.SYSTEM: (80, 180, 220),
    FlavorKind.NARRATIVE: (180, 360, 420),
    FlavorKind.MICRO_COMBAT: (40, 120, 140),
}

PRIORITIES = (100, 200, 300)  # §49.17
WEIGHT_MIN = 25
WEIGHT_MAX = 200
WEIGHT_DEFAULT = 100
ANTI_REPEAT_WINDOW = 2  # exclui as últimas 2...
ANTI_REPEAT_MIN_ELIGIBLE = 3  # ...se houver ao menos 3 elegíveis

# Janela de estabilidade por tempo. Masmorra e Evento não usam tempo: o chamador
# passa ``stability_token`` (run/contexto, ou occurrence+phase).
STABILITY_SECONDS: dict[FlavorKind, int] = {
    FlavorKind.SYSTEM: 6 * 3600,
    FlavorKind.NARRATIVE: 30 * 60,
    FlavorKind.MICRO_COMBAT: 6 * 3600,
}

# Banco-base mínimo por escopo (§49.17). Só informativo: ver ``base_bank_shortfall``.
BASE_BANK_MINIMUM: dict[str, int] = {
    "system": 3,
    "region": 6,
    "local": 5,
    "explore": 3,  # "Desbravar +3"
    "dungeon": 4,
    "event": 4,
    "brazier": 3,
}


@dataclass(frozen=True, slots=True)
class FlavorEntry:
    """Uma frase do banco. ``id`` é estável e nunca reaproveitado (§48 versionamento)."""

    id: str
    kind: FlavorKind
    scope: str  # tipo de contexto: "system", "region", "local", "dungeon"...
    key: str  # qual tela/região/local/masmorra: "personagem", "tdo", ...
    text: str
    priority: int = 100
    weight: int = WEIGHT_DEFAULT
    # Spoiler/elegibilidade: flags que o personagem PRECISA ter e flags que NÃO pode ter.
    requires_all: frozenset[str] = frozenset()
    forbidden_any: frozenset[str] = frozenset()
    draft: bool = True
    active: bool = True


@dataclass(frozen=True, slots=True)
class FlavorContext:
    kind: FlavorKind
    scope: str
    key: str
    # Estado oficial já conhecido pelo personagem, como flags opacas
    # (ex.: "discovered:avesso", "campaign:cap3"). Quem chama traduz estado em flags.
    flags: frozenset[str] = frozenset()
    stability_token: str = ""  # run/occurrence+phase; vazio = usa janela de tempo
    now_epoch: int = 0  # segundos; usado só quando stability_token está vazio


def validate_entry(entry: FlavorEntry) -> list[str]:
    """Devolve a lista de problemas da entrada (vazia = válida)."""
    problems: list[str] = []
    hard = LENGTH_LIMITS[entry.kind][2]
    if not entry.id:
        problems.append("id vazio")
    if not entry.text.strip():
        problems.append(f"{entry.id}: texto vazio")
    if len(entry.text) > hard:
        problems.append(f"{entry.id}: {len(entry.text)} caracteres passa do limite duro {hard}")
    if entry.priority not in PRIORITIES:
        problems.append(f"{entry.id}: prioridade {entry.priority} fora de {PRIORITIES}")
    if not WEIGHT_MIN <= entry.weight <= WEIGHT_MAX:
        problems.append(f"{entry.id}: peso {entry.weight} fora de {WEIGHT_MIN}..{WEIGHT_MAX}")
    if entry.requires_all & entry.forbidden_any:
        problems.append(f"{entry.id}: flag exigida e proibida ao mesmo tempo")
    return problems


def validate_catalog(entries: Iterable[FlavorEntry]) -> list[str]:
    entries = tuple(entries)
    problems: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.id in seen:
            problems.append(f"{entry.id}: id repetido")
        seen.add(entry.id)
        problems.extend(validate_entry(entry))
    return problems


def base_bank_shortfall(entries: Iterable[FlavorEntry]) -> dict[tuple[str, str], int]:
    """Quantas entradas ativas faltam para o banco-base de cada (escopo, chave)."""
    counts: dict[tuple[str, str], int] = {}
    for entry in entries:
        if entry.active:
            pair = (entry.scope, entry.key)
            counts[pair] = counts.get(pair, 0) + 1
    result: dict[tuple[str, str], int] = {}
    for pair, have in counts.items():
        need = BASE_BANK_MINIMUM.get(pair[0])
        if need is not None and have < need:
            result[pair] = need - have
    return result


def eligible_entries(
    entries: Iterable[FlavorEntry],
    context: FlavorContext,
    *,
    include_drafts: bool = False,
) -> list[FlavorEntry]:
    """Entradas que casam com o contexto e não violam spoiler (§37.4.3)."""
    result = []
    for entry in entries:
        if not entry.active:
            continue
        if entry.draft and not include_drafts:
            continue
        if (entry.kind, entry.scope, entry.key) != (context.kind, context.scope, context.key):
            continue
        if not entry.requires_all <= context.flags:
            continue
        if entry.forbidden_any & context.flags:
            continue
        result.append(entry)
    return result


def stability_seed(context: FlavorContext) -> str:
    """Semente estável: muda só com janela, token ou estado (flags) diferente."""
    if context.stability_token:
        window = context.stability_token
    else:
        window = str(context.now_epoch // STABILITY_SECONDS[context.kind])
    flags = ",".join(sorted(context.flags))
    return f"{context.kind.value}|{context.scope}|{context.key}|{window}|{flags}"


def select_flavor(
    entries: Iterable[FlavorEntry],
    context: FlavorContext,
    *,
    recent_ids: Sequence[str] = (),
    include_drafts: bool = False,
) -> FlavorEntry | None:
    """Escolhe uma entrada ou ``None`` se nenhuma for elegível.

    Regra: fica só a maior prioridade entre as elegíveis; tira as últimas 2 de
    ``recent_ids`` se sobrarem 3 ou mais; sorteia por peso com semente estável.
    """
    eligible = eligible_entries(entries, context, include_drafts=include_drafts)
    if not eligible:
        return None
    top = max(entry.priority for entry in eligible)
    pool = [entry for entry in eligible if entry.priority == top]
    if len(pool) >= ANTI_REPEAT_MIN_ELIGIBLE:
        recent = set(recent_ids[-ANTI_REPEAT_WINDOW:])
        fresh = [entry for entry in pool if entry.id not in recent]
        if fresh:
            pool = fresh
    pool.sort(key=lambda entry: entry.id)  # ordem fixa => resultado reprodutível
    digest = hashlib.sha256(stability_seed(context).encode("utf-8")).digest()
    point = int.from_bytes(digest[:8], "big") % sum(entry.weight for entry in pool)
    for entry in pool:
        if point < entry.weight:
            return entry
        point -= entry.weight
    return pool[-1]  # inalcançável; satisfaz o tipo
