from uuid import uuid4

import pytest

from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.bot.doctrines_ui import doctrine_art_ids, render_art_choices
from asterion.domain.arts import (
    ACTIVE_ART_DEFINITIONS,
    AGOUREIRO_ART_IDS,
    ART_IDS_BY_CLASS,
    ATIRADOR_ART_IDS,
    BASTIAO_ART_IDS,
    CARRASCO_ART_IDS,
    CONJURADOR_ART_IDS,
    DEVASTADOR_ART_IDS,
    GUARDIAO_ART_IDS,
    INQUISIDOR_ART_IDS,
    INVOCADOR_ART_IDS,
    RASTREADOR_ART_IDS,
    RUNICO_ART_IDS,
    SABOTADOR_ART_IDS,
    SENTINEL_ART_IDS,
    VIGIA_ART_IDS,
)


def _views(*, level: int = 20, path: str | None = "devastador"):
    collection = DoctrineCollectionView(
        character_name="Sentinela",
        character_class="sentinela",
        selected_path=path,
        configuration_version=3,
        foreground=False,
        current_configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=1000,
        level=level,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Aríete",
        revision=2,
        configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )
    return collection, doctrine


def test_doctrine_choices_include_only_implemented_art_for_draft_path_and_level():
    ariete = DEVASTADOR_ART_IDS["ariete"]
    view, doctrine = _views(path="devastador")
    expected_class_arts = tuple(
        art_id
        for art_id in ART_IDS_BY_CLASS["sentinela"]
        if ACTIVE_ART_DEFINITIONS[art_id].min_level <= view.level
    )
    assert doctrine_art_ids(view, doctrine) == (
        *expected_class_arts,
        ariete,
    )
    screen = render_art_choices(view, doctrine, 1)
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert any("Aríete" in label for label in labels)

    bastion_view, bastion_doctrine = _views(path="bastiao")
    assert ariete not in doctrine_art_ids(bastion_view, bastion_doctrine)

    low_view, low_doctrine = _views(level=11, path="devastador")
    assert ariete not in doctrine_art_ids(low_view, low_doctrine)

    rechaco = SENTINEL_ART_IDS["golpe_de_rechaco"]
    assert rechaco not in doctrine_art_ids(view, doctrine)
    level_34_view, level_34_doctrine = _views(level=34, path="devastador")
    assert rechaco in doctrine_art_ids(level_34_view, level_34_doctrine)


def test_doctrine_offers_tiro_calculado_to_vigia_at_level_18_without_path_gate():
    art_id = VIGIA_ART_IDS["tiro_calculado"]

    def vigia_views(level):
        collection = DoctrineCollectionView(
            character_name="Vigia",
            character_class="vigia",
            selected_path=None,
            configuration_version=3,
            foreground=False,
            current_configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
            doctrines=(),
            crowns=1000,
            level=level,
        )
        doctrine = DoctrineView(
            doctrine_id=uuid4(),
            name="Tiro Calculado",
            revision=1,
            configuration={"path": None, "equipment": {}, "arts": {}, "talents": []},
            is_current=False,
            incomplete_reason=None,
            can_apply=True,
        )
        return collection, doctrine

    locked_view, locked_doctrine = vigia_views(17)
    assert art_id not in doctrine_art_ids(locked_view, locked_doctrine)

    available_view, available_doctrine = vigia_views(18)
    assert art_id in doctrine_art_ids(available_view, available_doctrine)
    screen = render_art_choices(available_view, available_doctrine, 1)
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert any("Tiro Calculado" in label for label in labels)


@pytest.mark.parametrize(
    ("character_class", "path", "art_id", "label"),
    [
        ("sentinela", "bastiao", BASTIAO_ART_IDS["escudo_de_cinzas"], "Escudo de Cinzas"),
        ("errante", "carrasco", CARRASCO_ART_IDS["corte_de_execucao"], "Corte de Execução"),
        ("errante", "sabotador", SABOTADOR_ART_IDS["veneno_velado"], "Veneno Velado"),
        ("vigia", "atirador", ATIRADOR_ART_IDS["tiro_perfurante"], "Tiro Perfurante"),
        ("vigia", "rastreador", RASTREADOR_ART_IDS["flecha_serrilhada"], "Flecha Serrilhada"),
        ("tecelao", "conjurador", CONJURADOR_ART_IDS["estilhaco_do_veu"], "Estilhaço do Véu"),
        ("tecelao", "runico", RUNICO_ART_IDS["runa_de_guarda"], "Runa de Guarda"),
        ("oraculo", "agoureiro", AGOUREIRO_ART_IDS["mau_agouro"], "Mau Agouro"),
        ("oraculo", "invocador", INVOCADOR_ART_IDS["lobo"], "Lobo"),
        ("luminar", "guardiao", GUARDIAO_ART_IDS["cura_solar"], "Cura Solar"),
        ("luminar", "inquisidor", INQUISIDOR_ART_IDS["lanca_de_luz"], "Lança de Luz"),
    ],
)
def test_doctrine_ui_lists_first_wave_path_art_for_its_class_and_path(
    character_class, path, art_id, label
):
    view = DoctrineCollectionView(
        character_name="Aventureiro",
        character_class=character_class,
        selected_path=path,
        configuration_version=1,
        foreground=False,
        current_configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
        doctrines=(),
        crowns=0,
        level=12,
    )
    doctrine = DoctrineView(
        doctrine_id=uuid4(),
        name="Build",
        revision=1,
        configuration={"path": path, "equipment": {}, "arts": {}, "talents": []},
        is_current=False,
        incomplete_reason=None,
        can_apply=True,
    )

    assert art_id in doctrine_art_ids(view, doctrine)
    screen = render_art_choices(view, doctrine, 1)
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert any(label in button_label for button_label in labels)
