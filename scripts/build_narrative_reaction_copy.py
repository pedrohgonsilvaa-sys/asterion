"""Gera o catálogo de falas de reação a partir do pacote de textos (v1.0.1).

Uso:
    python scripts/build_narrative_reaction_copy.py \
        docs/specs/ASTERION_TEXTOS_REACAO_NPCS_v1_0_1.md \
        src/asterion/domain/narrative_choices_catalog.json \
        src/asterion/domain/narrative_reactions_catalog.json

Só entra uma fala quando o ``choice_id`` do texto é o mesmo do contrato. O
script imprime os conflitos: ``choice_id`` diferente e fala de um NPC que não
recebe memória daquela opção (o runtime não mostra essa fala).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NO_NPC = "Sem fala NPC"

SPEAKERS = {
    "Alda Veyr": "alda",
    "Oren Cal": "oren",
    "Dara Venn": "dara",
    "Iven Raal": "iven",
    "Nera Voss": "nera",
    "Talen Orm": "talen_orm",
    "Talen Nyr": "talen_nyr",
    "Sera Morn": "sera_morn",
    "Sera Nol": "sera_nol",
    "Ilyan Korr": "ilyan",
    "Rava Kern": "rava",
    "Eris Val": "eris",
    "Roven Pell": "roven",
    "Haro Sen": "haro",
}


def parse(source: str) -> list[dict]:
    sections = []
    for block in re.split(r"^## ", source, flags=re.M)[1:]:
        header = re.match(r"([PS]\d+) — ", block)
        if not header:
            continue
        choice = re.search(r"\*\*choice_id:\*\* `([^`]+)`", block)
        # "Sem fala NPC" (memória só do personagem) não tem aspas: vira fala vazia.
        options = re.findall(
            r"^### Opção (\d) — .+?\n\*\*(.+?):\*\* (?:“(.+?)”|[^\n]*)\s*$",
            block,
            flags=re.M,
        )
        sections.append(
            {
                "mission_id": header.group(1),
                "choice_id": choice.group(1) if choice else None,
                "options": [
                    {"option_id": f"o{n}", "speaker_name": name, "text": text}
                    for n, name, text in options
                ],
            }
        )
    return sections


def main() -> None:
    copy_path, catalog_path, target_path = map(Path, sys.argv[1:4])
    nodes = {
        node["mission_id"]: node
        for node in json.loads(catalog_path.read_text(encoding="utf-8"))["nodes"]
    }
    reactions: dict[str, dict[str, dict]] = {}
    mismatched, unheard = [], []
    for section in parse(copy_path.read_text(encoding="utf-8")):
        node = nodes[section["mission_id"]]
        if section["choice_id"] != node["choice_id"] or len(section["options"]) != 3:
            mismatched.append(f"{section['choice_id']} (contrato: {node['choice_id']})")
            continue
        entry = {}
        for option, line in zip(node["options"], section["options"], strict=True):
            if line["speaker_name"] == NO_NPC:
                if option["npc_memory_targets"]:
                    unheard.append(
                        f"{node['choice_id']}/{option['option_id']} (sem fala, mas há alvo de NPC)"
                    )
                continue
            speaker = SPEAKERS[line["speaker_name"]]
            holders = {target["npc_id"] for target in option["npc_memory_targets"]}
            if speaker not in holders:
                unheard.append(
                    f"{node['choice_id']}/{option['option_id']} ({line['speaker_name']})"
                )
            entry[option["option_id"]] = {
                "speaker": speaker,
                "speaker_name": line["speaker_name"],
                "text": line["text"],
            }
        if entry:
            reactions[node["choice_id"]] = entry
    target_path.write_text(
        json.dumps({"version": "1.0.1", "reactions": reactions}, ensure_ascii=False, indent=1)
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(reactions)} nós com falas gravados em {target_path}")
    print(f"choice_id diferente do contrato ({len(mismatched)}): {', '.join(mismatched)}")
    print(f"fala de NPC sem memória da opção ({len(unheard)}): {', '.join(unheard)}")


if __name__ == "__main__":
    main()
