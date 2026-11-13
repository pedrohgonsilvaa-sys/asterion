from pathlib import Path

from asterion.application.road import BRAZIER_DETAILS
from asterion.bot.asset_catalog import build_asset_images
from asterion.bot.media import resolve_asset_file


def _touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_catalog_maps_creation_and_brazier_and_draws_a_variant(tmp_path):
    for n in (1, 2, 3):
        _touch(tmp_path, f"creation/cc.raca.v0{n}.png")
        _touch(tmp_path, f"bonfire/terras do ocaso/braseiro_estrada.v0{n}.png")
    images = build_asset_images(tuple(BRAZIER_DETAILS), tmp_path)
    assert images["race"] == "file:creation/cc.raca.v*.png"
    assert images["brazier_estrada"] == images["tdo.brazier.estrada"]
    assert "gender" not in images
    drawn = {resolve_asset_file(images["race"], tmp_path).name for _ in range(80)}
    assert drawn == {"cc.raca.v01.png", "cc.raca.v02.png", "cc.raca.v03.png"}


def test_wildcard_cannot_escape_assets_root(tmp_path):
    root = tmp_path / "assets"
    _touch(tmp_path, "secret.v01.png")
    root.mkdir()
    assert resolve_asset_file("file:../secret.v*.png", root) is None
    assert resolve_asset_file("file:*/x.v*.png", root) is None


def test_every_real_brazier_has_art_when_assets_exist():
    import pytest

    from asterion.bot.media import assets_root

    if not (assets_root() / "bonfire").is_dir():
        pytest.skip("assets/ not present")
    images = build_asset_images(tuple(BRAZIER_DETAILS))
    assert sorted(set(BRAZIER_DETAILS) - set(images)) == []
    assert {"name", "gender", "race", "class", "confirm"} <= set(images)


def test_mission_and_location_keys(tmp_path):
    from dataclasses import replace

    from asterion.application.road import ROAD
    from asterion.bot.asset_catalog import location_key, with_mission_art
    from asterion.bot.creation_ui import Screen

    _touch(tmp_path, "missions/altos cinereos/p26_ordens_de_emergencia.v01.png")
    _touch(tmp_path, "missions/altos cinereos/p26_ordens_de_emergencia.v02.png")
    _touch(tmp_path, "maps/terras do ocaso/estrada.v01.png")
    images = build_asset_images((), tmp_path)
    assert images["p26"].startswith("file:missions/altos cinereos/p26_")
    assert images["p26_detail"] == images["p26"]
    assert location_key(ROAD) in images
    screen = Screen("t", "missions", None)
    assert with_mission_art(screen, "P26").image_key == "p26"
    other = replace(screen, image_key="map")
    assert with_mission_art(other, "P26").image_key == "map"


def test_real_assets_cover_quests_and_locations():
    import pytest

    from asterion.bot.asset_catalog import _MAP_LOCATIONS, location_key
    from asterion.bot.media import assets_root

    if not (assets_root() / "missions").is_dir():
        pytest.skip("assets/ not present")
    images = build_asset_images(tuple(BRAZIER_DETAILS))
    for quest in [f"p{n}" for n in range(1, 37)] + [f"s{n}" for n in range(1, 37)]:
        assert quest in images, quest
    assert [loc for loc in _MAP_LOCATIONS if location_key(loc) not in images] == []
    for ref in images.values():
        assert resolve_asset_file(ref) is not None, ref


def test_npc_dungeon_region_and_character_keys():
    import pytest

    from asterion.bot.asset_catalog import npc_key_from_text
    from asterion.bot.media import assets_root

    assert npc_key_from_text("✒️ Oren Cal\nRefúgio") == "npc.oren_cal"
    assert npc_key_from_text("✒️ Oren Cal · Refúgio do Ocaso\nx") == "npc.oren_cal"
    assert npc_key_from_text("📜 Missões") is None
    if not (assets_root() / "npcs").is_dir():
        pytest.skip("assets/ not present")
    images = build_asset_images(tuple(BRAZIER_DETAILS))
    npcs = [k for k in images if k.startswith("npc.")]
    assert len(npcs) == 30
    assert len([k for k in images if k.startswith("region.")]) == 6
    assert len([k for k in images if k.startswith("dungeon.")]) == 12
    assert len([k for k in images if k.startswith("char.")]) == 70
    assert "char.velado.feminino.errante" in images
    for ref in images.values():
        assert resolve_asset_file(ref) is not None, ref
