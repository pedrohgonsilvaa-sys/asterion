"""Terras do Ocaso v1.0.18 (secao 33.1, 33.3, 33.4): Refúgio como hub.

Regras puras de navegação. Modelo hub-and-spoke: o Refúgio liga todos os Locais
descobertos e todo Local volta ao Refúgio; nunca há ida direta Local-Local.
Nada aqui toca banco.
"""

from collections.abc import Iterable

from asterion.domain.tdo_explore import (
    BOSQUE_LOCATION_ID,
    CAMARA_LOCATION_ID,
    CHARNECA_LOCATION_ID,
    REFUGIO_LOCATION_ID,
    ROAD_LOCATION_ID,
    RUINS_LOCATION_ID,
)

ROAD_LABEL = "Estrada das Cinzas"
REFUGE_LABEL = "Refúgio do Ocaso"
CHARNECA_LABEL = "Charneca da Fuligem"
BOSQUE_LABEL = "Bosque Calcinado"
RUINS_LABEL = "Ruínas do Vigia"
CAMARA_LABEL = "Câmara do Poente"

# Ordem de exibição dos Locais no Refúgio: (rótulo, location_id).
HUB_LOCALS: tuple[tuple[str, str], ...] = (
    (ROAD_LABEL, ROAD_LOCATION_ID),
    (CHARNECA_LABEL, CHARNECA_LOCATION_ID),
    (BOSQUE_LABEL, BOSQUE_LOCATION_ID),
    (RUINS_LABEL, RUINS_LOCATION_ID),
    (CAMARA_LABEL, CAMARA_LOCATION_ID),
)
HUB_LOCATION_LABELS = frozenset({REFUGE_LABEL, *(label for label, _ in HUB_LOCALS)})
_ID_BY_LABEL = dict(HUB_LOCALS) | {REFUGE_LABEL: REFUGIO_LOCATION_ID}

# Locais com Caçada (33.1: Estrada, Charneca, Bosque, Ruínas). A Câmara nunca.
HUNT_LABELS: tuple[str, ...] = (ROAD_LABEL, CHARNECA_LABEL, BOSQUE_LABEL, RUINS_LABEL)

# Estrada nasce descoberta (33.2 item 2); as demais dependem de LocationDiscovery.
ALWAYS_DISCOVERED_LABELS = frozenset({ROAD_LABEL})

# Textos canônicos da Fonte Regional v1.0.18 FINAL, seção 3.6 (narrative-designer).
TEXTO_CAMARA_DESCOBERTA = "Entre as pedras do Poente há um recinto fechado."
TEXTO_CAMARA_PRE_P6 = (
    "Um recinto fechado. As paredes são de pedra escura, sem marca nem janela. "
    "O ar está parado, e o pó no chão não tem pegadas. Nada aqui responde a quem chega. "
    "Nada aqui cede."
)
TEXTO_CAMARA_POS_P6 = (
    "O Vigia Partido não se levanta mais. Os registros chamam a estrutura de Âncora do "
    "Poente, e o Vigia a guardava. Outras Âncoras existiram. O recinto está calado, e "
    "ninguém sabe o que ela segurava."
)


def location_id_for_label(label: str) -> str | None:
    return _ID_BY_LABEL.get(label)


def is_hub_location(label: str) -> bool:
    return label in HUB_LOCATION_LABELS


def is_discovered(label: str, discovered_ids: Iterable[str]) -> bool:
    """Local descoberto: Estrada sempre; os demais por ``LocationDiscovery``."""
    if label in ALWAYS_DISCOVERED_LABELS:
        return True
    location_id = _ID_BY_LABEL.get(label)
    return location_id is not None and location_id in set(discovered_ids)


def hub_destinations(current: str, discovered_ids: Iterable[str]) -> tuple[str, ...]:
    """Destinos a partir de ``current``.

    Refúgio: todos os Locais descobertos. Qualquer Local (inclusive a Câmara):
    só o Refúgio. Nunca Local-Local.
    """
    if current == REFUGE_LABEL:
        known = set(discovered_ids)
        return tuple(label for label, _ in HUB_LOCALS if is_discovered(label, known))
    if current in HUB_LOCATION_LABELS:
        return (REFUGE_LABEL,)
    return ()


def is_hub_step(origin: str, destination: str) -> bool:
    """True se origem/destino formam uma aresta do hub (uma ponta é o Refúgio)."""
    if origin == destination:
        return False
    if origin == REFUGE_LABEL:
        return destination in HUB_LOCATION_LABELS
    return destination == REFUGE_LABEL and origin in HUB_LOCATION_LABELS


def hunt_choices(discovered_ids: Iterable[str]) -> tuple[str, ...]:
    """Locais oferecidos por Caçar no Refúgio: descobertos e com Caçada."""
    known = set(discovered_ids)
    return tuple(label for label in HUNT_LABELS if is_discovered(label, known))


def camara_entry_text(p6_completed: bool) -> str:
    """Texto de entrada da Câmara conforme a P6 de quem vê (L5)."""
    return TEXTO_CAMARA_POS_P6 if p6_completed else TEXTO_CAMARA_PRE_P6
