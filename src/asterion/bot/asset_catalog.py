"""Automatic image catalog built from the local ``assets/`` folder.

Maps screen image keys to ``file:`` refs. A ref may hold a ``*`` wildcard that
selects among the variants (``.v01``, ``.v02`` ...) of one image; the variant is
drawn at random each time the screen is sent (see ``media.resolve_asset_file``).
Keys that have no art here are simply absent, so those screens stay text-only.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from asterion.application import road
from asterion.application.knowledge_catalog import CREATURE_PRESENTATION, LOCATION_LABELS
from asterion.bot.creation_ui import Screen
from asterion.bot.media import assets_root
from asterion.domain.creation import CLASSES, GENDERS, RACES
from asterion.domain.road import CREATURE_CATALOG

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
    "Câmara do Poente": ("terras do ocaso", "camara_poente"),
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
_QUEST_FILE = re.compile(r"^([ps]\d+)_.+\.v\d\d\.(?:png|jpe?g)$", re.IGNORECASE)
_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png")

logger = logging.getLogger(__name__)

# Race -> file prefix in assets/characters.
_RACE_CODE = {
    "remanescente": "rem",
    "velado": "vel",
    "cinereo": "cin",
    "hemario": "hem",
    "alvorano": "alv",
}

_MONSTER_FOLDERS = (
    "terras do ocaso",
    "vales dos enforcados",
    "planicies de nareth",
    "varzeas carmesins",
    "altos cinereos",
    "confins do veu",
)
_MONSTER_REGION_FOLDER = {
    "tdo": "terras do ocaso",
    "vde": "vales dos enforcados",
    "nareth": "planicies de nareth",
    "varzeas": "varzeas carmesins",
    "altos": "altos cinereos",
    "confins_do_veu": "confins do veu",
}
_CREATURES_BY_ID = {creature.creature_id: creature for creature in CREATURE_CATALOG}

# Location ids that do not use the same short stem as their monster artwork.
_HABITAT_FILE_STEMS = {
    "tdo.location.bosque_calcinado": "bosque",
    "tdo.location.camara_do_poente": "camara_poente",
    "tdo.location.charneca_da_fuligem": "charneca",
    "tdo.location.cripta_do_ocaso": "cripta",
    "tdo.location.estrada_das_cinzas": "estrada",
    "tdo.location.galerias_do_vigia": "galerias_vigia",
    "tdo.location.ruinas_do_vigia": "ruinas",
    "vde.location.baixios_enredados": "baixios",
    "vde.location.fosso_das_raizes": "fosso",
    "vde.location.garganta_dos_lacos": "garganta",
    "vde.location.mata_suspensa": "mata",
    "vde.location.santuario_do_no_antigo": "santuario",
    "nareth.location.camara_do_arconte": "camara_arconte",
    "nareth.location.campinas_do_meridiano": "campinas",
    "nareth.location.campos_invertidos": "campos",
    "nareth.location.canais_secos": "canais",
    "nareth.location.galerias_do_meridiano": "galerias_meridiano",
    "nareth.location.observatorio_afundado": "observatorio_afundado",
    "nareth.location.observatorio_do_eixo": "observatorio_eixo",
    "varzeas.location.brejos_do_pulso": "brejos",
    "varzeas.location.diques_rubros": "diques",
    "varzeas.location.galerias_transferencia": "galerias_transferencia",
    "varzeas.location.hortos_hemaris": "hortos",
    "location.altos.bastilha_carga": "bastilha",
    "location.altos.escarpa_cinza": "escarpa",
    "location.altos.pedreiras_suspensas": "pedreiras",
    "location.altos.pontes_fuligem": "pontes",
    "location.confins.estradas_ausentes": "estradas",
    "location.confins.fraturas_limiar": "fraturas",
    "location.confins.marcha_nebulosa": "marcha",
    "location.confins.no_central": "no_central",
}
_VARIANT_FILE_STEMS = {
    "furious": "furioso",
    "furioso": "furioso",
    "resistant": "resistente",
    "resistente": "resistente",
    "agile": "agil",
    "agil": "agil",
    "hemorrhagic": "hemorragico",
    "hemorragico": "hemorragico",
    "venomous": "venenoso",
    "venenoso": "venenoso",
}

# The asset names follow the phase evidence used by these two bosses, whose
# phase II and III form names are not in alphabetical order.
_BOSS_TRANSFORMATION_PHASE_FORMS = {
    "arconte_invertido": ("corrigir_o_que_permanece", "a_medida_impossivel"),
    "matriz_rubra": ("persistencia", "emergencia"),
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


def character_image_key(race: str, gender: str | None, character_class: str) -> str:
    """Image key for an established character, with a fallback for older records."""
    if gender not in GENDERS:
        return "character"
    return character_key(race, gender, character_class)


def _location_art_stem(location: str) -> str:
    if location in _MAP_LOCATIONS:
        return _MAP_LOCATIONS[location][1]
    if location in _HABITAT_FILE_STEMS:
        return _HABITAT_FILE_STEMS[location]
    label = LOCATION_LABELS.get(location, location)
    for map_label, (_folder, stem) in _MAP_LOCATIONS.items():
        if map_label.casefold() == label.casefold():
            return stem
    return _slug(label)


def _variant_art_stem(variant: str | None) -> str | None:
    if not variant:
        return None
    return _VARIANT_FILE_STEMS.get(_slug(variant))


def creature_image_key(
    creature_id: str,
    location: str | None = None,
    variant: str | None = None,
) -> str:
    key = f"creature:{creature_id}"
    if location is None:
        return key
    key += f":map:{_location_art_stem(location)}"
    state = _variant_art_stem(variant)
    return f"{key}:state:{state}" if state else key


def _creature_id_for_fighter(fighter, key: str) -> str | None:
    known_ids = set(_CREATURES_BY_ID) | set(CREATURE_PRESENTATION)
    for candidate in (getattr(fighter, "id", ""), getattr(fighter, "name", ""), key):
        if candidate in known_ids:
            return candidate
        slug = _slug(candidate) if candidate else ""
        if slug in known_ids:
            return slug
        for creature_id, creature in _CREATURES_BY_ID.items():
            if slug and _slug(creature.name) == slug:
                return creature_id
        for creature_id in CREATURE_PRESENTATION:
            if slug and _slug(creature_id.rsplit(".", 1)[-1]) == slug:
                return creature_id
    return None


def with_creature_art(
    screen: Screen,
    combat,
    location: str,
    variant: str | None = None,
) -> Screen:
    """Use the enemy's map and state art on an overland encounter screen."""
    fighters = getattr(combat, "fighters", {})
    for key, fighter in fighters.items():
        side = getattr(fighter, "side", "") or ("player" if key == "player" else "enemy")
        if side != "enemy" or getattr(fighter, "hp", 0) <= 0:
            continue
        creature_id = _creature_id_for_fighter(fighter, key)
        if creature_id:
            return replace(
                screen,
                image_key=creature_image_key(
                    creature_id,
                    location,
                    variant or getattr(combat, "variant", None),
                ),
            )
    return screen


def _boss_identity(value: str) -> str:
    stop_words = {"a", "as", "o", "os", "da", "das", "de", "do", "dos", "e"}
    return "".join(word for word in _slug(value).split("_") if word not in stop_words)


def _combat_phase(value: str | None, combat=None) -> str | None:
    phase = _slug(value or "")
    if phase in {"ii", "phase_ii", "2", "phase_2"}:
        return "II"
    if phase in {"iii", "phase_iii", "3", "phase_3"}:
        return "III"
    triggers = tuple(getattr(combat, "phase_triggers", ()))
    triggered_ids = set(getattr(combat, "phase_triggered_ids", ()))
    active = [
        (index, trigger)
        for index, trigger in enumerate(triggers)
        if trigger.trigger_id in triggered_ids
    ]
    if active:
        index, trigger = active[-1]
        trigger_phase = _slug(getattr(trigger, "phase_id", None) or "")
        if trigger_phase in {"ii", "phase_ii", "2", "phase_2"}:
            return "II"
        if trigger_phase in {"iii", "phase_iii", "3", "phase_3"}:
            return "III"
        return "II" if index == 0 else "III"
    return None


@lru_cache(maxsize=4)
def _transformation_groups(root: str) -> dict[str, tuple[str, tuple[str, ...]]]:
    base = Path(root)
    groups: dict[str, tuple[str, set[str]]] = {}
    pattern = re.compile(r"^([^.]+)\.([^.]+)\.v[0-9]{2}\.(?:png|jpe?g)$", re.IGNORECASE)
    for folder in _MONSTER_FOLDERS:
        directory = base / "monsters" / folder / "transformations"
        if not directory.is_dir():
            continue
        for file in directory.iterdir():
            if file.suffix.lower().removeprefix(".") not in _IMAGE_EXTENSIONS:
                continue
            match = pattern.match(file.name)
            if not match:
                continue
            boss, form = match.groups()
            if boss not in groups:
                groups[boss] = (folder, set())
            groups[boss][1].add(form)
    return {
        boss: (folder, tuple(sorted(forms)))
        for boss, (folder, forms) in groups.items()
    }


def _boss_phase_forms(boss: str, forms: tuple[str, ...]) -> tuple[str, str] | None:
    if not forms:
        return None
    explicit = _BOSS_TRANSFORMATION_PHASE_FORMS.get(boss)
    if explicit and all(form in forms for form in explicit):
        return explicit
    if len(forms) == 1:
        return forms[0], forms[0]
    return forms[0], forms[1]


def with_boss_transformation_art(
    screen: Screen,
    combat,
    phase_id: str | None = None,
) -> Screen:
    """Show the active boss form during phases II and III, when art exists."""
    phase = _combat_phase(phase_id or getattr(combat, "phase_id", None), combat)
    if phase is None:
        return screen
    groups = _transformation_groups(str(assets_root()))
    fighters = getattr(combat, "fighters", {})
    for key, fighter in fighters.items():
        side = getattr(fighter, "side", "") or ("player" if key == "player" else "enemy")
        if side != "enemy" or getattr(fighter, "hp", 0) <= 0:
            continue
        identities = {
            _boss_identity(str(value))
            for value in (getattr(fighter, "id", ""), getattr(fighter, "name", ""), key)
            if value
        }
        for boss, (_folder, forms) in groups.items():
            if _boss_identity(boss) not in identities:
                continue
            phase_forms = _boss_phase_forms(boss, forms)
            if phase_forms is None:
                continue
            return replace(
                screen,
                image_key=f"boss-transform:{boss}:phase:{phase}",
            )
    return screen


def with_dungeon_art(screen: Screen, family_id: str) -> Screen:
    if screen.image_key not in {"dungeon", "dungeon_crypt", "dungeon_lobby"}:
        return screen
    return replace(screen, image_key=family_id)


def location_key(location: str) -> str:
    """Image key of a Local screen."""
    return f"local:{location}"


def with_mission_art(screen: Screen, quest_id: str, combat=None) -> Screen:
    """Swap the generic "missions" key for the quest's own art key."""
    if combat is not None:
        screen = with_boss_transformation_art(screen, combat)
    if screen.image_key != "missions":
        return screen
    return replace(screen, image_key=quest_id.lower())


def _pattern(root: Path, folder: str, stem: str) -> str | None:
    """``file:`` ref for every variant of ``stem``, or None when there is none."""
    base = root / folder
    for extension in _IMAGE_EXTENSIONS:
        if any(base.glob(f"{stem}.v[0-9][0-9].{extension}")):
            return f"file:{folder}/{stem}.v*.{extension}".replace("\\", "/")
    return None


def _numbered_image_stems(folder: Path) -> set[str]:
    return {
        file.name.rsplit(".v", 1)[0]
        for extension in _IMAGE_EXTENSIONS
        for file in folder.glob(f"*.v[0-9][0-9].{extension}")
    }


def _preferred_file(folder: Path, stem: str) -> Path | None:
    for extension in _IMAGE_EXTENSIONS:
        candidate = folder / f"{stem}.{extension}"
        if candidate.is_file():
            return candidate
    return None


def _location_region_folder(location_id: str) -> str | None:
    parts = location_id.split(".")
    region_id = parts[1] if parts and parts[0] == "location" else parts[0]
    if region_id == "confins":
        region_id = "confins_do_veu"
    return _MONSTER_REGION_FOLDER.get(region_id)


def _monster_location_stems() -> dict[str, tuple[str, ...]]:
    stems: dict[str, set[str]] = {folder: set() for folder in _MONSTER_FOLDERS}
    for folder, stem in _MAP_LOCATIONS.values():
        stems[folder].add(stem)
    for location_id in LOCATION_LABELS:
        folder = _location_region_folder(location_id)
        if folder:
            stems[folder].add(_location_art_stem(location_id))
    return {folder: tuple(sorted(folder_stems)) for folder, folder_stems in stems.items()}


def _creature_candidates(creature_id: str) -> tuple[str, ...]:
    candidates = [creature_id, creature_id.rsplit(".", 1)[-1]]
    creature = _CREATURES_BY_ID.get(creature_id)
    if creature is not None:
        candidates.append(_slug(creature.name))
    return tuple(dict.fromkeys(candidates))


def _creature_region_folders(creature_id: str) -> tuple[str, ...]:
    presentation = CREATURE_PRESENTATION.get(creature_id)
    if presentation is not None:
        region = _MONSTER_REGION_FOLDER.get(presentation.region_id)
        if region:
            return (region,)
    parts = creature_id.split(".")
    region_ids = [part for part in parts if part in _MONSTER_REGION_FOLDER]
    if "confins" in parts:
        region_ids.append("confins_do_veu")
    if region_ids:
        return (_MONSTER_REGION_FOLDER[region_ids[0]],)
    return _MONSTER_FOLDERS


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
    for extension in _IMAGE_EXTENSIONS:
        for file in sorted((base / "npcs").glob(f"*/*.{extension}")):
            key = npc_key(file.stem.replace("_", " "))
            if key not in images:
                images[key] = f"file:npcs/{file.parent.name}/{file.name}"
    chars = base / "characters"
    for race in RACES:
        for gender in GENDERS:
            prefix = f"{_RACE_CODE[race]}-{gender[0]}"
            default_race = _preferred_file(chars / "default races", prefix)
            if default_race is not None:
                images[character_key(race, gender)] = (
                    f"file:characters/default races/{default_race.name}"
                )
            seen_class_art: dict[str, str] = {}
            for klass in CLASSES:
                default_class = _preferred_file(chars / "default classes", f"{prefix}-{klass}")
                if default_class is None:
                    continue
                # Two classes of one race+gender must never share the same picture:
                # a byte-identical copy means one file holds another class's art, and
                # showing it would present the wrong class. Skip the later copy.
                digest = hashlib.md5(default_class.read_bytes()).hexdigest()
                if digest in seen_class_art:
                    logger.warning(
                        "class art %s duplicates %s; not served for class %s",
                        default_class.name,
                        seen_class_art[digest],
                        klass,
                    )
                    continue
                seen_class_art[digest] = default_class.name
                key = character_key(race, gender, klass)
                images[key] = f"file:characters/default classes/{default_class.name}"
    monsters = base / "monsters"
    if monsters.is_dir():
        creature_ids = set(_CREATURES_BY_ID) | set(CREATURE_PRESENTATION)
        location_stems = _monster_location_stems()
        state_stems = tuple(dict.fromkeys(_VARIANT_FILE_STEMS.values()))
        base_art_stems = {
            folder: _numbered_image_stems(monsters / folder) for folder in _MONSTER_FOLDERS
        }
        state_art_stems = {
            folder: _numbered_image_stems(monsters / folder / "variants")
            for folder in _MONSTER_FOLDERS
        }
        for creature_id in sorted(creature_ids):
            candidates = _creature_candidates(creature_id)
            for folder in _creature_region_folders(creature_id):
                available = base_art_stems[folder]
                stem = next(
                    (
                        candidate
                        for candidate in candidates
                        if any(name.startswith(f"{candidate}.") for name in available)
                    ),
                    None,
                )
                if stem is None:
                    continue
                generic_ref = _pattern(base, f"monsters/{folder}", f"{stem}.*")
                if generic_ref is None:
                    continue
                images[creature_image_key(creature_id)] = generic_ref
                for location_stem in location_stems.get(folder, ()):
                    image_stem = f"{stem}.{location_stem}"
                    base_ref = _pattern(base, f"monsters/{folder}", image_stem) or generic_ref
                    location = creature_image_key(creature_id, location_stem)
                    images[location] = base_ref
                    for state in state_stems:
                        state_image_stem = f"{image_stem}.{state}"
                        state_ref = (
                            _pattern(base, f"monsters/{folder}/variants", state_image_stem)
                            if state_image_stem in state_art_stems[folder]
                            else None
                        )
                        images[creature_image_key(creature_id, location_stem, state)] = (
                            state_ref or base_ref
                        )
                break
        for boss, (folder, forms) in _transformation_groups(str(base)).items():
            form_refs = {
                form: _pattern(
                    base,
                    f"monsters/{folder}/transformations",
                    f"{boss}.{form}",
                )
                for form in forms
            }
            for form, ref in form_refs.items():
                if ref:
                    images[f"boss-transform:{boss}:form:{form}"] = ref
            phase_forms = _boss_phase_forms(boss, forms)
            if phase_forms:
                for phase, form in zip(("II", "III"), phase_forms, strict=True):
                    ref = form_refs.get(form)
                    if ref:
                        images[f"boss-transform:{boss}:phase:{phase}"] = ref
    missions = base / "missions"
    if missions.is_dir():
        for region in sorted(p for p in missions.iterdir() if p.is_dir()):
            seen: set[str] = set()
            for file in sorted(region.iterdir()):
                if file.suffix.lower().removeprefix(".") not in _IMAGE_EXTENSIONS:
                    continue
                match = _QUEST_FILE.match(file.name)
                if not match or match.group(1) in seen:
                    continue
                quest = match.group(1)
                seen.add(quest)
                stem = file.name.split(".v")[0]
                ref = _pattern(base, f"missions/{region.name}", stem)
                if ref is None:
                    continue
                for suffix in _QUEST_SUFFIXES:
                    images[quest + suffix] = ref
    for alias, target in _ALIASES.items():
        if target in images:
            images[alias] = images[target]
    return images
