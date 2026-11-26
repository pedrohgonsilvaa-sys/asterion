"""Telas do Mapa (Contrato Mestre de Telas UI v1.0.0 §15).

O Mapa é navegação, geografia e acesso: registra o que já foi conhecido. Não mostra
nível na Região, nem Braseiro, nem ``Ir para o Local``; Explorar é outro sistema.
Os estados (Regiões e Locais conhecidos) vêm do handler, que lê os serviços.
"""

from __future__ import annotations

from asterion.bot.asset_catalog import location_key
from asterion.bot.creation_ui import Screen
from asterion.bot.refuge_ui import REFUGE_TEXT
from asterion.bot.ui_format import back, blocks, button, column, keyboard, narrative
from asterion.domain.tdo_hub import (
    BOSQUE_LABEL,
    CAMARA_LABEL,
    REFUGE_LABEL,
    camara_entry_text,
)

TDO_REGION = "Terras do Ocaso"
CHARNECA_LABEL = "Charneca da Fuligem"
RUINS_LABEL = "Ruínas do Vigia"

MAP_TEXT = (
    "O conhecimento das terras se forma pouco a pouco, conforme caminhos, regiões e "
    "locais são descobertos. O mapa registra aquilo que já foi conhecido e permite "
    "acompanhar as conexões entre os lugares alcançados durante a jornada."
)
TDO_REGION_TEXT = (
    "Uma região marcada por cinzas, fuligem, pedra escurecida e vegetação calcinada. "
    "Entre caminhos antigos e estruturas que ainda resistem, o Refúgio do Ocaso permanece "
    "como um dos poucos pontos seguros antes das terras mais perigosas."
)
CHARNECA_TEXT = (
    "Uma extensa região coberta por cinzas se estende além das árvores. O terreno "
    "permanece silencioso, marcado por trilhas antigas e sinais de passagem. Entre a "
    "vegetação calcinada e os caminhos abandonados, vestígios de antigas construções "
    "ainda podem ser encontrados."
)
# Ordem e ícones dos Locais das Terras do Ocaso no Mapa (§15).
TDO_LOCALS = (
    (REFUGE_LABEL, "refuge", "🛖"),
    (CHARNECA_LABEL, "charneca", "🌫️"),
    (BOSQUE_LABEL, "bosque", "🌲"),
    (RUINS_LABEL, "ruinas", "🏚️"),
    (CAMARA_LABEL, "camara", "🕯️"),
)
TDO_LOCAL_BY_KEY = {key: (label, icon) for label, key, icon in TDO_LOCALS}
REGION_ICONS = {TDO_REGION: "🌘"}


def _suffix(from_local: bool) -> str:
    return ":fromlocal" if from_local else ""


def render_map(
    regions: list[tuple[str, str, str]], *, back_callback: str, from_local: bool = False
) -> Screen:
    """Raiz do Mapa: um botão por Região conhecida (``(nome, chave, ícone)``)."""
    rows = column(
        *(
            button(f"{icon} {name}", f"world:map:region:{key}{_suffix(from_local)}")
            for name, key, icon in regions
        )
    )
    return Screen(
        blocks("🗺️ <b>Mapa</b>", narrative(MAP_TEXT)),
        "map",
        keyboard(*rows, back(back_callback)),
        "HTML",
    )


def render_tdo_region(known: set[str], *, from_local: bool = False) -> Screen:
    """Terras do Ocaso: só os Locais já conhecidos, sem nível nem Braseiro."""
    rows = column(
        *(
            button(f"{icon} {label}", f"world:map:local:{key}{_suffix(from_local)}")
            for label, key, icon in TDO_LOCALS
            if label in known
        )
    )
    return Screen(
        blocks(f"{REGION_ICONS[TDO_REGION]} <b>{TDO_REGION}</b>", narrative(TDO_REGION_TEXT)),
        "region.tdo",
        keyboard(*rows, back(f"world:map{_suffix(from_local)}")),
        "HTML",
    )


def tdo_local_text(label: str, *, p6_completed: bool = False) -> str | None:
    """Descrição canônica do Local; sem texto na Fonte, nenhuma descrição é inventada."""
    if label == REFUGE_LABEL:
        return REFUGE_TEXT
    if label == CHARNECA_LABEL:
        return CHARNECA_TEXT
    if label == CAMARA_LABEL:
        return camara_entry_text(p6_completed)
    return None


def render_tdo_local(key: str, *, p6_completed: bool = False, from_local: bool = False) -> Screen:
    """Local das Terras do Ocaso no Mapa: título, descrição e ``↩️ Retornar``."""
    label, icon = TDO_LOCAL_BY_KEY[key]
    description = tdo_local_text(label, p6_completed=p6_completed)
    return Screen(
        blocks(f"{icon} <b>{label}</b>", narrative(description) if description else None),
        location_key(label),
        keyboard(back(f"world:map:region:tdo{_suffix(from_local)}")),
        "HTML",
    )
