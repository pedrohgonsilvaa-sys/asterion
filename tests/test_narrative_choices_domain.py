"""Ação × Consequência v1.0.0: catalog contract and pure resolution rules."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from asterion.application.narrative_choices import NarrativeNodeView
from asterion.bot.narrative_choice_ui import (
    IMMEDIATE_REACTIONS,
    future_reaction,
    narrative_option_rows,
)
from asterion.domain.narrative_choices import (
    BACKFILL_SOURCE,
    NARRATIVE_MISSION_IDS,
    PLAYER_SOURCE,
    RAPPORT_STATES,
    CommittedChoice,
    build_catalog,
    legitimate_reaction,
    narrative_catalog,
    reaction_lines,
    resolve_hook,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/ASTERION_SISTEMA_ACAO_CONSEQUENCIA_NARRATIVA_v1_0_0.md"
CATALOG = ROOT / "src/asterion/domain/narrative_choices_catalog.json"


def test_every_principal_and_secondary_has_exactly_one_valid_node():
    catalog = narrative_catalog()
    assert len(catalog.nodes) == 72
    assert {node.mission_id for node in catalog.nodes.values()} == NARRATIVE_MISSION_IDS
    for node in catalog.nodes.values():
        assert node.choice_id.startswith(f"{node.mission_id}_")
        assert node.mission_kind == ("principal" if node.mission_id[0] == "P" else "secundaria")
        assert len(node.options) == 3
        assert node.future_hooks
        for option in node.options:
            assert option.character_memory_tags or option.npc_memory_targets
            assert option.label and "_" not in option.label


def test_catalog_json_is_exactly_what_the_spec_generates(tmp_path):
    target = tmp_path / "catalog.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_narrative_choice_catalog.py"),
            str(SPEC),
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(
        CATALOG.read_text(encoding="utf-8")
    )


def test_spec_examples_are_parsed_with_the_right_owners():
    catalog = narrative_catalog()
    p1 = catalog.nodes["P1_choice_posture"]
    assert [(t.npc_id, t.tag) for t in p1.option("o1").npc_memory_targets] == [
        ("alda", "cautela_no_relato"),
        ("oren", "fatos_primeiro"),
    ]
    p12 = catalog.nodes["P12_climax_interpretation"]
    assert {t.npc_id for t in p12.option("o3").npc_memory_targets} == {"dara", "iven"}
    p27 = catalog.nodes["P27_continuity_cost"]
    assert p27.option("o2").character_memory_tags == ("recusa_coercao",)
    assert p27.option("o2").npc_memory_targets == ()
    hook = catalog.hook("P1_choice_posture->P2")
    assert hook is not None and hook[1].knowledge_holders == ("alda",)
    assert [h.target for h in catalog.nodes["P2_evidentiary_posture"].future_hooks] == [
        "S2",
        "P3",
        "P4",
    ]


def test_identity_conditions_follow_the_contract_without_npc_identity_leaking():
    catalog = narrative_catalog()
    p11 = catalog.nodes["P11_conflicting_evidence"]
    assert p11.matched_identity("velado", "oraculo") == ("race_class:velado+oraculo",)
    assert p11.matched_identity("velado", "vigia") == ()
    assert catalog.nodes["P2_evidentiary_posture"].matched_identity("cinereo", "vigia") == (
        "race:cinereo",
        "class:vigia",
    )
    # Haro (Hemário) and Eris (Alvorana) are NPCs: their identity is not a player condition.
    assert catalog.nodes["S32_record_conflict"].identity_conditions == ()
    assert catalog.nodes["P34_anchor_model"].matched_identity("alvorano", "vigia") == ()
    # "Nenhuma Raça recebe culpa ou privilégio automático" (S6).
    assert all(c.kind != "race" for c in catalog.nodes["S6_missing_people"].identity_conditions)
    # Identity never removes an option of the contract.
    for node in catalog.nodes.values():
        assert node.available_options("hemario", "luminar") == node.options


def _synthetic(**option_overrides):
    option = {
        "option_id": "o1",
        "label": "Opção",
        "character_memory_tags": ["evidence_first"],
        "npc_memory_targets": [{"npc_id": "dara", "tag": "rigor"}],
    }
    option.update(option_overrides)
    return {
        "choice_id": "P1_test",
        "mission_id": "P1",
        "mission_kind": "principal",
        "title": "Teste",
        "region": "terras_do_ocaso",
        "step": 5,
        "step_context": "teste",
        "question": "?",
        "options": [
            option,
            {
                "option_id": "o2",
                "label": "Outra",
                "character_memory_tags": ["x"],
                "npc_memory_targets": [],
            },
        ],
        "future_hooks": [
            {"hook_id": "P1_test->P2", "target": "P2", "knowledge_holders": ["dara"], "summary": ""}
        ],
        "identity_conditions": [],
    }


def test_invalid_nodes_are_rejected():
    with pytest.raises(ValueError):
        build_catalog([_synthetic(character_memory_tags=[], npc_memory_targets=[])])
    contract = _synthetic()
    contract["mission_kind"] = "contrato"
    with pytest.raises(ValueError):
        build_catalog([contract])
    unknown_holder = _synthetic()
    unknown_holder["future_hooks"][0]["knowledge_holders"] = ["iven"]
    with pytest.raises(ValueError):
        build_catalog([unknown_holder])


def test_option_restricted_by_identity_is_unavailable_to_others():
    catalog = build_catalog([_synthetic(requires=[{"kind": "class", "values": ["vigia"]}])])
    node = catalog.nodes["P1_test"]
    assert [o.option_id for o in node.available_options("velado", "vigia")] == ["o1", "o2"]
    assert [o.option_id for o in node.available_options("velado", "luminar")] == ["o2"]


def test_future_hook_reads_only_legitimate_memory():
    catalog = narrative_catalog()
    node, hook = catalog.hook("P1_choice_posture->P2")
    assert resolve_hook(node, hook, None) is None
    backfill = CommittedChoice(
        "P1_choice_posture", "neutral_backfill", BACKFILL_SOURCE, frozenset()
    )
    assert resolve_hook(node, hook, backfill) is None
    known = CommittedChoice(
        "P1_choice_posture", "o2", PLAYER_SOURCE, frozenset({("alda", "aceita_vulnerabilidade")})
    )
    assert resolve_hook(node, hook, known) == "o2"
    # Alda never received the memory: she cannot react to it.
    unknown = CommittedChoice(
        "P1_choice_posture", "o2", PLAYER_SOURCE, frozenset({("oren", "honestidade")})
    )
    assert resolve_hook(node, hook, unknown) is None


def test_ui_shows_labels_only_and_no_unapproved_copy():
    assert IMMEDIATE_REACTIONS == {}
    node = narrative_catalog().nodes["P1_choice_posture"]
    view = NarrativeNodeView(
        node.choice_id, None, tuple((o.option_id, o.label) for o in node.options)
    )
    rows = narrative_option_rows(view, "p1:7")
    assert [row[0].callback_data for row in rows] == ["p1:7:nc:o1", "p1:7:nc:o2", "p1:7:nc:o3"]
    texts = " ".join(row[0].text for row in rows)
    for option in node.options:
        for target in option.npc_memory_targets:
            assert target.tag not in texts
    assert not any(char.isdigit() for char in texts)
    assert (
        narrative_option_rows(NarrativeNodeView(node.choice_id, "o1", view.options), "p1:7") == []
    )
    assert "neutral" in RAPPORT_STATES


COPY = ROOT / "docs/specs/ASTERION_TEXTOS_REACAO_NPCS_v1_0_1.md"
REACTIONS = ROOT / "src/asterion/domain/narrative_reactions_catalog.json"


def test_reaction_json_is_exactly_what_the_copy_generates(tmp_path):
    target = tmp_path / "reactions.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_narrative_reaction_copy.py"),
            str(COPY),
            str(CATALOG),
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(
        REACTIONS.read_text(encoding="utf-8")
    )
    lines = reaction_lines()
    catalog = narrative_catalog()
    assert {choice for choice, _ in lines} <= set(catalog.nodes)
    # The 9 Nareth/Várzeas nodes now use the contract's choice_ids: their copy is loaded.
    assert ("P15_anomaly_method", "o1") in lines
    assert ("P19_priority", "o3") in lines
    # Options the contract gives no NPC target ("Sem fala NPC") have no line at all.
    assert not any(choice.startswith(("P27_", "P29_", "P30_")) for choice, _ in lines)


def test_every_loaded_line_is_spoken_by_an_npc_that_holds_the_memory():
    catalog = narrative_catalog()
    for (choice_id, option_id), line in reaction_lines().items():
        holders = {t.npc_id for t in catalog.nodes[choice_id].option(option_id).npc_memory_targets}
        assert line.speaker in holders, (choice_id, option_id, line.speaker)


def test_homonym_npcs_never_share_memory():
    catalog = narrative_catalog()
    assert {t.npc_id for t in catalog.nodes["P19_priority"].option("o1").npc_memory_targets} == {
        "sera_morn"
    }
    assert {
        t.npc_id for t in catalog.nodes["P31_source_conflict"].option("o1").npc_memory_targets
    } == {"sera_nol"}
    assert {
        t.npc_id for t in catalog.nodes["P15_anomaly_method"].option("o1").npc_memory_targets
    } == {"talen_orm"}
    assert {
        t.npc_id for t in catalog.nodes["S31_trail_method"].option("o1").npc_memory_targets
    } == {"talen_nyr"}


def test_reaction_line_needs_the_speaker_to_hold_the_memory():
    catalog = narrative_catalog()
    node, hook = catalog.hook("P1_choice_posture->P2")
    alda_knows = CommittedChoice(
        "P1_choice_posture", "o1", PLAYER_SOURCE, frozenset({("alda", "cautela_no_relato")})
    )
    line = legitimate_reaction(node, hook, alda_knows)
    assert line is not None and line.speaker_name == "Alda Veyr"
    assert future_reaction(line).startswith("Alda Veyr: “Você não enfeitou o relato.")
    assert legitimate_reaction(node, hook, None) is None
    # P14: only Nera received the memory, so Nera speaks; with Talen's memory alone it stays hidden.
    node, hook = catalog.hook("P14_map_vs_world->P15")
    nera_only = CommittedChoice(
        "P14_map_vs_world", "o1", PLAYER_SOURCE, frozenset({("nera", "pragmatismo")})
    )
    line = legitimate_reaction(node, hook, nera_only)
    assert line is not None and line.speaker_name == "Nera Voss"
    talen_only = CommittedChoice(
        "P14_map_vs_world", "o1", PLAYER_SOURCE, frozenset({("talen_orm", "pragmatismo")})
    )
    assert legitimate_reaction(node, hook, talen_only) is None
