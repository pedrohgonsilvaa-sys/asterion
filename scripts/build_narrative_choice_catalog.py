"""Gera o catálogo das 72 escolhas narrativas a partir da especificação v1.0.0.

Uso:
    python scripts/build_narrative_choice_catalog.py \
        docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md \
        src/asterion/domain/narrative_choices_catalog.json

Prólogo (Documento A, 2 nós, arquivo separado):
    python scripts/build_narrative_choice_catalog.py --prologue \
        docs/specs/ASTERION_DECISOES_PROLOGO_E_CONTRATOS_v1_0_0.md \
        src/asterion/domain/narrative_choices_prologue_catalog.json

O documento é a fonte; o JSON é derivado e nunca deve ser editado à mão.
Só nomes de tags são normalizados (ASCII, minúsculas), como permite a §8.2.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

REGIONS = {
    "Terras do Ocaso": "terras_do_ocaso",
    "Vales dos Enforcados": "vales_dos_enforcados",
    "Planícies de Nareth": "planicies_de_nareth",
    "Várzeas Carmesins": "varzeas_carmesins",
    "Altos Cinéreos": "altos_cinereos",
    "Confins do Véu": "confins_do_veu",
}
NPCS = {"Alda", "Oren", "Dara", "Iven", "Nera", "Talen", "Sera", "Ilyan", "Rava", "Eris",
        "Roven", "Haro"}
CHARACTER_OWNERS = {"memoria", "memoria_global"}
RACE_WORDS = {
    "remanescente": "remanescente", "velado": "velado", "cinereo": "cinereo",
    "hemario": "hemario", "alvorano": "alvorano",
}
CLASS_WORDS = {
    "sentinela": "sentinela", "errante": "errante", "vigia": "vigia",
    "tecelao": "tecelao", "oraculo": "oraculo", "luminar": "luminar",
}
# Menções de identidade que não são condição do personagem do jogador: a frase
# nega o vínculo ou fala da identidade de um NPC (Haro é Hemário, Eris é Alvorana).
NOT_PLAYER_CONDITIONS = {
    "P18": {"alvorano"},
    "P24": {"alvorano"},
    "S32": {"hemario"},
    "P34": {"alvorano"},
}
# Two pairs of NPCs share a first name (Bíblia v4.0.7 / Regionais): they are
# different people and must never share memory.
HOMONYMS = {
    "varzeas_carmesins": {"sera": "sera_morn"},
    "planicies_de_nareth": {"talen": "talen_orm"},
    "confins_do_veu": {"sera": "sera_nol", "talen": "talen_nyr"},
}
TARGET_RE = re.compile(r"\b(?:Pós-)?[PS]\d+\b")


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def parse_memory(raw: str, node_npcs: set[str]) -> tuple[list[str], list[dict]]:
    raw = raw.strip().rstrip(".")
    character_tags: list[str] = []
    npc_targets: list[dict] = []
    for segment in re.split(r";_?", raw):
        segment = segment.strip("_ ")
        if not segment:
            continue
        owner, _, tag = segment.partition(":")
        tag = fold(tag)
        owner_key = fold(owner)
        if not tag:
            raise ValueError(f"memória sem tag: {raw!r}")
        if owner_key in CHARACTER_OWNERS:
            character_tags.append(tag)
            continue
        if owner_key == "ambos":
            names = sorted(node_npcs)
        else:
            names = [name.strip() for name in owner.split("/")]
        for name in names:
            if name not in NPCS:
                raise ValueError(f"dono de memória desconhecido: {name!r} em {raw!r}")
            npc_targets.append({"npc_id": fold(name), "tag": tag})
    return character_tags, npc_targets


def parse_identity(choice_id: str, mission_id: str, text: str) -> list[dict]:
    folded = fold(text)
    words = set(folded.split("_"))
    excluded = NOT_PLAYER_CONDITIONS.get(mission_id, set())
    conditions: list[dict] = []
    paired: set[str] = set()
    for left, right in re.findall(r"([A-Za-zÀ-ú]+) \+ ([A-Za-zÀ-ú]+)", text):
        race, klass = fold(left), fold(right)
        if race in RACE_WORDS and klass in CLASS_WORDS:
            conditions.append({"kind": "race_class", "values": [[race, klass]]})
            paired = {race, klass}
    races = sorted(w for w in words if w in RACE_WORDS and w not in excluded and w not in paired)
    classes = sorted(w for w in words if w in CLASS_WORDS and w not in paired)
    if "nenhuma" in words and "raca" in words:
        races = []
    if races:
        conditions.append({"kind": "race", "values": races})
    if classes:
        conditions.append({"kind": "class", "values": classes})
    return conditions


def parse_hooks(choice_id: str, text: str, node_npcs: set[str]) -> list[dict]:
    """Cada trecho "DESTINOS: texto" vira um gancho por destino.

    ``knowledge_holders`` são os NPCs citados no trecho que receberam memória
    neste nó. Sem nenhum, o gancho só pode ler a memória do próprio personagem.
    """
    hooks: list[dict] = []
    for segment in re.split(r";\s+(?=(?:Pós-)?[PS]\d+[/:])", text):
        head, _, _ = segment.partition(":")
        targets = TARGET_RE.findall(head) or [part for part in head.split("/")]
        mentioned = sorted(name for name in NPCS if re.search(rf"\b{name}\b", segment))
        holders = [fold(name) for name in mentioned if name in node_npcs]
        for target in targets:
            target_id = fold(target).upper() if TARGET_RE.fullmatch(target) else fold(target)
            hooks.append(
                {
                    "hook_id": f"{choice_id}->{target_id}",
                    "target": target_id,
                    "knowledge_holders": holders,
                    "summary": segment.strip(),
                }
            )
    return hooks


def build(source: str) -> list[dict]:
    nodes: list[dict] = []
    blocks = re.split(r"^#### ", source, flags=re.M)
    for block in blocks[1:]:
        header = block.splitlines()[0].strip()
        match = re.match(r"([PS]\d+) — (.+)", header)
        if not match:
            continue
        mission_id, title = match.groups()
        choice_id = re.search(r"\*\*Nó:\*\* `([^`]+)`", block).group(1)
        moment = re.search(r"\*\*Momento:\*\* (.+)", block).group(1).strip()
        question = re.search(r"\*\*Pergunta dramática:\*\* (.+)", block).group(1).strip()
        future = re.search(r"\*\*Retorno futuro:\*\* (.+)", block).group(1).strip()
        identity = re.search(r"\*\*Identidade contextual:\*\* (.+)", block).group(1).strip()
        raw_options = re.findall(r"^(\d)\. \*\*(.+?)\*\* → memória: `([^`]+)`", block, flags=re.M)
        if len(raw_options) != 3:
            raise ValueError(f"{choice_id}: esperadas 3 opções, achei {len(raw_options)}")
        node_npcs = {
            name.strip()
            for _n, _l, memory in raw_options
            for segment in re.split(r";_?", memory)
            for name in segment.partition(":")[0].strip("_ ").split("/")
            if name.strip() in NPCS
        }
        options = []
        for number, label, memory in raw_options:
            character_tags, npc_targets = parse_memory(memory, node_npcs)
            if not character_tags and not npc_targets:
                raise ValueError(f"{choice_id}: opção {number} sem memória")
            options.append(
                {
                    "option_id": f"o{number}",
                    "label": label.strip(),
                    "character_memory_tags": character_tags,
                    "npc_memory_targets": npc_targets,
                }
            )
        step = re.search(r"Etapa (\d+)", moment)
        nodes.append(
            {
                "choice_id": choice_id,
                "mission_id": mission_id,
                "mission_kind": "principal" if mission_id.startswith("P") else "secundaria",
                "title": title.strip(),
                "region": None,
                "step": int(step.group(1)) if step else None,
                "step_context": moment,
                "question": question,
                "options": options,
                "future_hooks": parse_hooks(choice_id, future, node_npcs),
                "identity_conditions": parse_identity(choice_id, mission_id, identity),
                "identity_note": identity,
            }
        )
    # Região: a seção "### <emoji> <Região>" anterior a cada nó.
    current = None
    order = {node["mission_id"]: node for node in nodes}
    for line in source.splitlines():
        if line.startswith("### "):
            for title, key in REGIONS.items():
                if title in line:
                    current = key
        match = re.match(r"#### ([PS]\d+) — ", line)
        if match and match.group(1) in order:
            order[match.group(1)]["region"] = current
    for node in nodes:
        rename = HOMONYMS.get(node["region"], {})
        for option in node["options"]:
            for target in option["npc_memory_targets"]:
                if target["npc_id"] in {"sera", "talen"}:
                    target["npc_id"] = rename[target["npc_id"]]
        for hook in node["future_hooks"]:
            hook["knowledge_holders"] = [rename.get(npc, npc) for npc in hook["knowledge_holders"]]
    return nodes


def build_prologue(source: str) -> list[dict]:
    """Documento A §3: as escolhas do Prólogo (sem Quest, só memória de personagem)."""
    nodes: list[dict] = []
    section = source.split("## 3. Catálogo de escolhas", 1)[1].split("\n## 4.", 1)[0]
    for block in re.split(r"^### 3\.\d+ ", section, flags=re.M)[1:]:

        def field(name: str, block: str = block) -> str:
            return re.search(rf"\| `{name}` \| (.+?) \|", block).group(1).strip("` ")

        options = []
        for number, label, kind, tags in re.findall(
            r"#### Opção `o(\d)`\s+\*\*Label:\*\* (.+?)\s+\*\*Memória\*\*\s+"
            r"- `memory_type`: `(\w+)`\s+- `character_memory_tags`:\s+((?:\s*- `\w+`\n?)+)",
            block,
        ):
            options.append(
                {
                    "option_id": f"o{number}",
                    "label": label.strip(),
                    "memory_type": kind,
                    "character_memory_tags": re.findall(r"`(\w+)`", tags),
                    "npc_memory_targets": [],
                }
            )
        if len(options) != 3:
            raise ValueError(f"{field('choice_id')}: esperadas 3 opções")
        nodes.append(
            {
                "choice_id": field("choice_id"),
                "mission_id": field("mission_id"),
                "mission_kind": field("mission_kind"),
                "title": field("title"),
                "region": field("region"),
                "step": None,
                "step_context": re.search(r"\*\*Contexto:\*\* (.+)", block).group(1).strip(),
                "question": re.search(r"\*\*Pergunta:\*\* \*\*(.+?)\*\*", block).group(1),
                "moment": field("step"),
                "options": options,
                "future_hooks": [],
                "identity_conditions": [],
            }
        )
    return nodes


def main_prologue(source_path: Path, target_path: Path) -> None:
    nodes = build_prologue(source_path.read_text(encoding="utf-8"))
    ids = [node["choice_id"] for node in nodes]
    if ids != ["PRO_choice_aftermath", "PRO_choice_first_fire"]:
        raise SystemExit(f"catálogo do Prólogo incompleto: {ids}")
    target_path.write_text(
        json.dumps({"version": "1.0.0", "nodes": nodes}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"{len(nodes)} nós do Prólogo gravados em {target_path}")


def main() -> None:
    if sys.argv[1] == "--prologue":
        main_prologue(Path(sys.argv[2]), Path(sys.argv[3]))
        return
    source_path, target_path = Path(sys.argv[1]), Path(sys.argv[2])
    nodes = build(source_path.read_text(encoding="utf-8"))
    missions = {node["mission_id"] for node in nodes}
    expected = {f"P{i}" for i in range(1, 37)} | {f"S{i}" for i in range(1, 37)}
    if missions != expected or len(nodes) != 72:
        raise SystemExit(f"catálogo incompleto: faltam {sorted(expected - missions)}")
    target_path.write_text(
        json.dumps({"version": "1.0.0", "nodes": nodes}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"{len(nodes)} nós gravados em {target_path}")


if __name__ == "__main__":
    main()
