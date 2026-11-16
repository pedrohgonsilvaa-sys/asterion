"""Terras do Ocaso v1.0.18 (secao 33): regras puras da ação Explorar.

Explorar revela um Local ainda não descoberto por sorteio uniforme. Estrada
(nasce descoberta) e Refúgio (descoberto na Etapa 4 de P1) não entram no
sorteio. Nada aqui toca banco: persistência fica na camada de aplicação.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256

REFUGIO_LOCATION_ID = "tdo.location.refugio_do_ocaso"
ROAD_LOCATION_ID = "tdo.location.estrada_das_cinzas"
CHARNECA_LOCATION_ID = "tdo.location.charneca_da_fuligem"
BOSQUE_LOCATION_ID = "tdo.location.bosque_calcinado"
RUINS_LOCATION_ID = "tdo.location.ruinas_do_vigia"
CAMARA_LOCATION_ID = "tdo.location.camara_do_poente"

# Anti-spam técnico (33.2 item 1); não é regra econômica. O mesmo limite vale
# para Desbravar (fatia própria).
EXPLORE_COOLDOWN_SECONDS = 3

# 33.2 item 3: percentual já usado nas Descobertas Menores.
DISCOVERY_XP_PERCENT = Decimal("0.025")


@dataclass(frozen=True)
class ExploreTarget:
    location_id: str
    label: str
    reference_level: int


# Ordem fixa do catálogo (o sorteio é uniforme; a ordem só dá determinismo).
EXPLORE_TARGETS: tuple[ExploreTarget, ...] = (
    ExploreTarget(CHARNECA_LOCATION_ID, "Charneca da Fuligem", 4),
    ExploreTarget(BOSQUE_LOCATION_ID, "Bosque Calcinado", 6),
    ExploreTarget(RUINS_LOCATION_ID, "Ruínas do Vigia", 9),
    ExploreTarget(CAMARA_LOCATION_ID, "Câmara do Poente", 10),
)
_TARGETS_BY_ID = {target.location_id: target for target in EXPLORE_TARGETS}


def explore_target(location_id: str) -> ExploreTarget:
    return _TARGETS_BY_ID[location_id]


def remaining_explore_targets(discovered: Iterable[str]) -> tuple[ExploreTarget, ...]:
    """Alvos ainda não descobertos; Estrada e Refúgio nunca aparecem."""
    known = set(discovered)
    return tuple(t for t in EXPLORE_TARGETS if t.location_id not in known)


def pick_explore_target(seed: str, discovered: Iterable[str]) -> ExploreTarget | None:
    """Sorteio uniforme entre os não descobertos; ``None`` se não sobrou alvo."""
    remaining = remaining_explore_targets(discovered)
    if not remaining:
        return None
    value = int.from_bytes(sha256(f"{seed}:explore_target".encode()).digest(), "big")
    return remaining[value % len(remaining)]


def discovery_xp(
    reference_level: int, player_level: int, level_xp: Callable[[int], int]
) -> int:
    """``FixedPercentXP(min(referência, nível), 2,5%)``; ``level_xp`` é XP(n) do GDD 49.7."""
    effective = min(reference_level, player_level)
    return int(
        (Decimal(level_xp(effective)) * DISCOVERY_XP_PERCENT).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )


def explore_cooldown_remaining(
    last_click_at: datetime | None, now: datetime
) -> timedelta:
    """Tempo que falta para o próximo clique; zero quando já pode explorar."""
    if last_click_at is None:
        return timedelta(0)
    remaining = timedelta(seconds=EXPLORE_COOLDOWN_SECONDS) - (now - last_click_at)
    return max(timedelta(0), remaining)
