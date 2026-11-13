"""Automatic image catalog built from the local ``assets/`` folder.

Maps screen image keys to ``file:`` refs. A ref may hold a ``*`` wildcard that
selects among the variants (``.v01``, ``.v02`` ...) of one image; the variant is
drawn at random each time the screen is sent (see ``media.resolve_asset_file``).
Keys that have no art here are simply absent, so those screens stay text-only.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from pathlib import Path

from asterion.application import road
from asterion.bot.creation_ui import Screen
from asterion.bot.media import assets_root
from asterion.domain.creation import CLASSES, GENDERS, RACES

# Creation step -> file stem in assets/creation.
_CREATION = {
    "name": "cc.nome",
    "gender": "cc.genero",
    "race": "cc.raca",
    "class": "cc.classe",
    "confirm": "cc.confirmacao",
}

# Brazier id prefix -> folder in assets/bonfire.
_BONFIRE_REGION = {
    "tdo.brazier.": "terras do ocaso",
    "varzeas.brazier.": "varzeas carmesins",
    "nareth.brazier.": "planicies de nareth",
    "bonfire.altos.": "altos cinereos",
    "bonfire.confins.": "confins do veu",
    "vde.brazier.": "vales dos enforcados",
}

# Brazier ids whose art file does not carry the same name as the id suffix.
_BONFIRE_FILE = {
    "tdo.brazier.refugio_do_ocaso": "braseiro_refugio",
    "vde.brazier.garganta_dos_lacos": "braseiro_lacos",
    "vde.brazier.mata_suspensa": "braseiro_copas_suspensas",
    "vde.brazier.vigilia_do_vale": "braseiro_vigilia",
}

# Screens that show the first permanent Brazier keep their historical key.
_ALIASES = {"brazier_estrada": "tdo.brazier.estrada"}


# Location (road constants) -> (folder in assets/maps, file stem).
_MAP_LOCATIONS = {
    road.ROAD: ("terras do ocaso", "estrada"),
    road.REFUGE: ("terras do ocaso", "refugio"),
    road.CHARNECA: ("terras do ocaso", "charneca"),
    road.BOSQUE: ("terras do ocaso", "bosque"),
    road.RUINS: ("terras do ocaso", "ruinas"),
    road.VDE_GARGANTA: ("vales dos enforcados", "garganta"),
    road.VDE_VIGILIA: ("vales dos enforcados", "vigilia"),
    road.VDE_MATA: ("vales dos enforcados", "mata"),
    road.VDE_BAIXIOS: ("vales dos enforcados", "baixios"),
    road.VDE_CLAUSTRO: ("vales dos enforcados", "claustro"),
    road.VDE_BERCO: ("vales dos enforcados", "berco"),
    road.NARETH_CAMPINAS: ("planicies de nareth", "campinas"),
    road.NARETH_POSTO: ("planicies de nareth", "posto"),
    road.NARETH_CANAIS: ("planicies de nareth", "canais"),
    road.NARETH_CAMPOS: ("planicies de nareth", "campos"),
    road.NARETH_OBSERVATORIO: ("planicies de nareth", "observatorio_eixo"),
    road.NARETH_CAMARA: ("planicies de nareth", "camara_arconte"),
    road.VARZEAS_DIQUES: ("varzeas carmesins", "diques"),
    road.VARZEAS_PORTO: ("varzeas carmesins", "porto"),
    road.VARZEAS_BREJOS: ("varzeas carmesins", "brejos"),
    road.VARZEAS_HORTOS: ("varzeas carmesins", "hortos"),
    road.VARZEAS_GALERIAS: ("varzeas carmesins", "galerias_transferencia"),
    road.VARZEAS_CAMARA: ("varzeas carmesins", "camara_matriz"),
    road.ALTOS_ESCARPA: ("altos cinereos", "escarpa"),
    road.ALTOS_ABRIGO: ("altos cinereos", "abrigo"),
    road.ALTOS_PONTES: ("altos cinereos", "pontes"),
    road.ALTOS_PEDREIRAS: ("altos cinereos", "pedreiras"),
    road.ALTOS_BASTILHA: ("altos cinereos", "bastilha"),
    road.ALTOS_CORACAO: ("altos cinereos", "coracao_colosso"),
    road.CONFINS_MARCHA: ("confins do veu", "marcha"),
    road.CONFINS_ULTIMO_REFUGIO: ("confins do veu", "ultimo_refugio"),
    road.CONFINS_ESTRADAS_AUSENTES: ("confins do veu", "estradas"),
    road.CONFINS_FRATURAS_LIMIAR: ("confins do veu", "fraturas"),
    road.CONFINS_NO_CENTRAL: ("confins do veu", "no_central"),
    road.CONFINS_CAMARA_REGENCIA: ("confins do veu", "camara_regencia"),
}

# Screens of one quest share its art: "s2" also serves "s2_detail", "p1_completed"...
_QUEST_SUFFIXES = ("", "_detail", "_giver", "_objective", "_completed", "_recovery")
_QUEST_FILE = re.compile(r"^([ps]\d+)_.+\.v\d\d\.png$")


# Race -> file prefix in assets/characters.
_RACE_CODE = {
    "remanescente": "rem",
    "velado": "vel",
    "cinereo": "cin",
    "hemario": "hem",
    "alvorano": "alv",
}

# Region key of the region map screens -> (folder, stem) in assets/maps.
_MAP_REGIONS = {
    "tdo": ("terras do ocaso", "terras_do_ocaso"),
    "vde": ("vales dos enforcados", "vales_dos_enforcados"),
    "nareth": ("planicies de nareth", "planicies_de_nareth"),
    "varzeas": ("varzeas carmesins", "varzeas_carmesins"),
    "altos": ("altos cinereos", "altos_cinereos"),
    "confins": ("confins do veu", "confins_do_veu"),
}

# Dungeon family id -> (folder, stem) in assets/maps.
_DUNGEONS = {
    "dungeon.tdo.cripta_ocaso": ("terras do ocaso", "cripta"),
    "dungeon.tdo.galerias_vigia": ("terras do ocaso", "galerias_vigia"),
    "dungeon.vde.fosso_raizes": ("vales dos enforcados", "fosso"),
    "dungeon.vde.santuario_no_antigo": ("vales dos enforcados", "santuario"),
    "dungeon.nareth.galerias_meridiano": ("planicies de nareth", "galerias_meridiano"),
    "dungeon.nareth.observatorio_afundado": ("planicies de nareth", "observatorio_afundado"),
    "dungeon.varzeas.enfermaria_afundada": ("varzeas carmesins", "enfermaria"),
    "dungeon.varzeas.cisterna_transferencia": ("varzeas carmesins", "cisterna"),
    "dungeon.altos.pedreira_contrapeso": ("altos cinereos", "pedreira_contrapeso"),
    "dungeon.altos.bastilha_profunda": ("altos cinereos", "bastilha_profunda"),
    "dungeon.confins.arquivo_retorno": ("confins do veu", "arquivo"),
    "dungeon.confins.camara_contradicoes": ("confins do veu", "contradicoes"),
}


def _slug(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "_".join(plain.lower().split())


def npc_key(name: str) -> str:
    return f"npc.{_slug(name)}"


def npc_key_from_text(text: str) -> str | None:
    """Key of the NPC speaking on a screen whose first line is "✒️ <Name>"."""
    first = text.splitlines()[0].strip() if text else ""
    if not first.startswith("✒"):
        return None
    name = first.lstrip("✒️ ").split(" · ")[0].strip()
    return npc_key(name) if name else None


def character_key(race: str, gender: str, character_class: str | None = None) -> str:
    key = f"char.{race}.{gender}"
    return f"{key}.{character_class}" if character_class else key


def with_dungeon_art(screen: Screen, family_id: str) -> Screen:
    if screen.image_key not in {"dungeon_crypt", "dungeon_lobby"}:
        return screen
    return replace(screen, image_key=family_id)


def location_key(location: str) -> str:
    """Image key of a Local screen."""
    return f"local:{location}"


def with_mission_art(screen: Screen, quest_id: str) -> Screen:
    """Swap the generic "missions" key for the quest's own art key."""
    if screen.image_key != "missions":
        return screen
    return replace(screen, image_key=quest_id.lower())


def _pattern(root: Path, folder: str, stem: str) -> str | None:
    """``file:`` ref for every variant of ``stem``, or None when there is none."""
    base = root / folder
    if any(base.glob(f"{stem}.v[0-9][0-9].png")):
        return f"file:{folder}/{stem}.v*.png".replace("\\", "/")
    return None


def build_asset_images(brazier_ids: tuple[str, ...], root: Path | None = None) -> dict[str, str]:
    base = (root or assets_root()).resolve()
    images: dict[str, str] = {}
    for key, stem in _CREATION.items():
        ref = _pattern(base, "creation", stem)
        if ref:
            images[key] = ref
    for brazier_id in brazier_ids:
        prefix = next((p for p in _BONFIRE_REGION if brazier_id.startswith(p)), None)
        if prefix is None:
            continue
        stem = _BONFIRE_FILE.get(brazier_id, f"braseiro_{brazier_id.removeprefix(prefix)}")
        ref = _pattern(base, f"bonfire/{_BONFIRE_REGION[prefix]}", stem)
        if ref:
            images[brazier_id] = ref
    for label, (folder, stem) in _MAP_LOCATIONS.items():
        ref = _pattern(base, f"maps/{folder}", stem)
        if ref:
            images[location_key(label)] = ref
    for region_key, (folder, stem) in _MAP_REGIONS.items():
        ref = _pattern(base, f"maps/{folder}", stem)
        if ref:
            images[f"region.{region_key}"] = ref
    for family_id, (folder, stem) in _DUNGEONS.items():
        ref = _pattern(base, f"maps/{folder}", stem)
        if ref:
            images[family_id] = ref
    for file in sorted((base / "npcs").glob("*/*.png")):
        images[npc_key(file.stem.replace("_", " "))] = f"file:npcs/{file.parent.name}/{file.name}"
    chars = base / "characters"
    for race in RACES:
        for gender in GENDERS:
            prefix = f"{_RACE_CODE[race]}-{gender[0]}"
            if (chars / "default races" / f"{prefix}.png").is_file():
                images[character_key(race, gender)] = f"file:characters/default races/{prefix}.png"
            for klass in CLASSES:
                name = f"{prefix}-{klass}.png"
                if (chars / "default classes" / name).is_file():
                    key = character_key(race, gender, klass)
                    images[key] = f"file:characters/default classes/{name}"
    missions = base / "missions"
    if missions.is_dir():
        for region in sorted(p for p in missions.iterdir() if p.is_dir()):
            seen: set[str] = set()
            for file in sorted(region.glob("*.png")):
                match = _QUEST_FILE.match(file.name)
                if not match or match.group(1) in seen:
                    continue
                quest = match.group(1)
                seen.add(quest)
                stem = file.name.split(".v")[0]
                for suffix in _QUEST_SUFFIXES:
                    images[quest + suffix] = f"file:missions/{region.name}/{stem}.v*.png"
    for alias, target in _ALIASES.items():
        if target in images:
            images[alias] = images[target]
    return images
