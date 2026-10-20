from uuid import uuid4

from asterion.application.doctrines import DoctrineCollectionView, DoctrineView
from asterion.bot.doctrines_ui import doctrine_art_ids, render_art_choices
from asterion.domain.arts import ART_IDS_BY_CLASS, DEVASTADOR_ART_IDS, VIGIA_ART_IDS


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
    assert doctrine_art_ids(view, doctrine) == (
        *ART_IDS_BY_CLASS["sentinela"],
        ariete,
    )
    screen = render_art_choices(view, doctrine, 1)
    labels = [button.text for row in screen.keyboard.inline_keyboard for button in row]
    assert any("Ariete" in label for label in labels)

    bastion_view, bastion_doctrine = _views(path="bastiao")
    assert ariete not in doctrine_art_ids(bastion_view, bastion_doctrine)

    low_view, low_doctrine = _views(level=11, path="devastador")
    assert ariete not in doctrine_art_ids(low_view, low_doctrine)


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
