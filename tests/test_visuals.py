from pathlib import Path

import pytest

from asterion.application.cosmetic_catalog import COSMETICS, COSMETICS_BY_ID
from asterion.bot.media import resolve_asset_file, visual_image_key
from asterion.domain import visuals
from asterion.domain.visuals import VisualDefinition, validate_visuals

TYPES = {item.cosmetic_id: item.cosmetic_type for item in COSMETICS}
APPEARANCE = next(i.cosmetic_id for i in COSMETICS if i.cosmetic_type == "appearance")
TITLE = next(i.cosmetic_id for i in COSMETICS if i.cosmetic_type == "title")


def test_real_catalog_is_valid():
    validate_visuals(visuals.VISUALS, TYPES)
    for visual in visuals.VISUALS:
        assert visual.cosmetic_id is None or visual.cosmetic_id in COSMETICS_BY_ID


def test_valid_catalog_and_bindings():
    catalog = (
        VisualDefinition("visual.a", "appearance", "A", cosmetic_id=APPEARANCE),
        VisualDefinition("visual.skin.b", "item_skin", "B", item_id="item.x"),
    )
    validate_visuals(catalog, TYPES)


@pytest.mark.parametrize(
    "bad",
    [
        VisualDefinition("A", "appearance", "A", cosmetic_id=APPEARANCE),
        VisualDefinition("visual.a", "weapon_family", "A", item_id="i"),
        VisualDefinition("visual.a", "appearance", "A", cosmetic_id=TITLE),
        VisualDefinition("visual.a", "appearance", "A", cosmetic_id="nope"),
        VisualDefinition("visual.a", "appearance", "A", cosmetic_id=APPEARANCE, item_id="i"),
        VisualDefinition("visual.a", "item_skin", "A"),
        VisualDefinition("visual.a", "item_skin", "A", cosmetic_id=APPEARANCE, item_id="i"),
        VisualDefinition("visual.a", "item_skin", " ", item_id="i"),
    ],
)
def test_invalid_visuals_rejected(bad):
    with pytest.raises(ValueError):
        validate_visuals((bad,), TYPES)


def test_duplicate_id_and_binding_rejected():
    one = VisualDefinition("visual.a", "item_skin", "A", item_id="i")
    with pytest.raises(ValueError):
        validate_visuals((one, one), TYPES)
    with pytest.raises(ValueError):
        validate_visuals((one, VisualDefinition("visual.b", "item_skin", "B", item_id="i")), TYPES)


def test_visual_has_no_mechanical_fields():
    fields = set(VisualDefinition.__slots__)
    assert fields == {"visual_id", "kind", "name", "cosmetic_id", "item_id"}
    assert "weapon_family" not in fields


def test_visual_image_key_requires_configured_art(monkeypatch):
    visual = VisualDefinition("visual.a", "appearance", "A", cosmetic_id=APPEARANCE)
    monkeypatch.setattr("asterion.bot.media.VISUAL_BY_COSMETIC", {APPEARANCE: visual})
    assert visual_image_key({}, cosmetic_id=APPEARANCE) is None
    assert visual_image_key({"visual.a": "FILEID"}, cosmetic_id=APPEARANCE) == "visual.a"
    assert visual_image_key({"visual.a": "FILEID"}, cosmetic_id=TITLE) is None


def test_asset_path_stays_inside_root(tmp_path: Path, monkeypatch):
    root = tmp_path / "assets"
    root.mkdir()
    (root / "ok.png").write_bytes(b"x")
    (tmp_path / "secret.txt").write_bytes(b"s")
    monkeypatch.chdir(tmp_path)
    assert resolve_asset_file("file:assets/ok.png", root) == (root / "ok.png").resolve()
    assert resolve_asset_file("file:ok.png", root) == (root / "ok.png").resolve()
    assert resolve_asset_file("file:../secret.txt", root) is None
    assert resolve_asset_file("file:assets/../secret.txt", root) is None
    assert resolve_asset_file(f"file:{tmp_path / 'secret.txt'}", root) is None
    assert resolve_asset_file("file:", root) is None
    assert resolve_asset_file("file:assets/missing.png", root) is None
    assert resolve_asset_file("file:assets", root) is None
