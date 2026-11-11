import pytest

from asterion.domain.narrative_identity import (
    NARRATIVE_SCENES,
    P2_ALDA_OFFER_SCENE,
    NarrativeBeat,
    NarrativeCondition,
    NarrativeContext,
    NarrativeLine,
    NarrativeOption,
    NarrativeScene,
    QuestRequirement,
    QuestState,
    resolve_scene,
)

# Test-only scene. Its text is a fixture, not canonical content.
SCENE = NarrativeScene(
    scene_id="test.scene.checkpoint",
    beats=(
        NarrativeBeat(
            beat_id="greeting",
            lines=(
                NarrativeLine("greeting.common", "common"),
                NarrativeLine(
                    "greeting.velado",
                    "race velado",
                    NarrativeCondition(races=frozenset({"velado"})),
                ),
                NarrativeLine(
                    "greeting.vigia",
                    "class vigia",
                    NarrativeCondition(classes=frozenset({"vigia"})),
                ),
                NarrativeLine(
                    "greeting.consequence",
                    "remembers what you did",
                    NarrativeCondition(required_flags=frozenset({"test.handed_over"})),
                    priority=10,
                ),
            ),
        ),
        NarrativeBeat(
            beat_id="clue",
            lines=(
                NarrativeLine("clue.common", "common clue"),
                NarrativeLine(
                    "clue.p1_late",
                    "late clue",
                    NarrativeCondition(
                        quests=(QuestRequirement("P1", frozenset({"active"}), min_step=4),)
                    ),
                ),
                NarrativeLine(
                    "clue.at_refuge",
                    "local clue",
                    NarrativeCondition(locations=frozenset({"Refúgio do Ocaso"})),
                ),
            ),
        ),
    ),
    options=(
        NarrativeOption("ask", "Ask"),
        NarrativeOption(
            "oraculo_read",
            "Read the omen",
            NarrativeCondition(classes=frozenset({"oraculo"})),
        ),
        NarrativeOption(
            "velado_vigia_signal",
            "Answer the watch signal",
            NarrativeCondition(race_classes=frozenset({("velado", "vigia")})),
        ),
        NarrativeOption(
            "not_after_betrayal",
            "Ask for trust",
            NarrativeCondition(forbidden_flags=frozenset({"test.handed_over"})),
        ),
    ),
)


def _context(race="remanescente", klass="sentinela", **kwargs):
    return NarrativeContext(character_id="c", race=race, character_class=klass, **kwargs)


def _lines(resolved):
    return [line.line_id for line in resolved.lines]


def _options(resolved):
    return [option.option_id for option in resolved.options]


def test_common_fallback_resolves_for_any_identity():
    resolved = resolve_scene(SCENE, _context())
    assert _lines(resolved) == ["greeting.common", "clue.common"]
    assert _options(resolved) == ["ask", "not_after_betrayal"]


def test_different_races_receive_different_lines_in_the_same_scene():
    velado = resolve_scene(SCENE, _context(race="velado"))
    hemario = resolve_scene(SCENE, _context(race="hemario"))
    assert velado.lines[0].line_id == "greeting.velado"
    assert hemario.lines[0].line_id == "greeting.common"


def test_different_classes_receive_different_lines_and_options():
    vigia = resolve_scene(SCENE, _context(race="cinereo", klass="vigia"))
    oraculo = resolve_scene(SCENE, _context(race="cinereo", klass="oraculo"))
    assert vigia.lines[0].line_id == "greeting.vigia"
    assert oraculo.lines[0].line_id == "greeting.common"
    assert "oraculo_read" in _options(oraculo)
    assert "oraculo_read" not in _options(vigia)


def test_race_and_class_pair_unlocks_an_option_neither_unlocks_alone():
    pair = resolve_scene(SCENE, _context(race="velado", klass="vigia"))
    race_only = resolve_scene(SCENE, _context(race="velado", klass="errante"))
    class_only = resolve_scene(SCENE, _context(race="alvorano", klass="vigia"))
    assert "velado_vigia_signal" in _options(pair)
    assert "velado_vigia_signal" not in _options(race_only)
    assert "velado_vigia_signal" not in _options(class_only)


def test_tie_between_race_and_class_lines_is_deterministic():
    context = _context(race="velado", klass="vigia")
    first = resolve_scene(SCENE, context)
    reversed_scene = NarrativeScene(
        scene_id=SCENE.scene_id,
        beats=tuple(
            NarrativeBeat(beat.beat_id, tuple(reversed(beat.lines))) for beat in SCENE.beats
        ),
        options=SCENE.options,
    )
    assert _lines(resolve_scene(reversed_scene, context)) == _lines(first)
    assert first.lines[0].line_id == "greeting.velado"


def test_recorded_consequence_outranks_identity_and_hides_incompatible_option():
    resolved = resolve_scene(
        SCENE, _context(race="velado", flags=frozenset({"test.handed_over"}))
    )
    assert resolved.lines[0].line_id == "greeting.consequence"
    assert "not_after_betrayal" not in _options(resolved)
    assert resolved.option("not_after_betrayal") is None


def test_mission_state_and_local_context_select_lines():
    late = resolve_scene(
        SCENE, _context(quests={"P1": QuestState(status="active", step=4)})
    )
    early = resolve_scene(
        SCENE, _context(quests={"P1": QuestState(status="active", step=3)})
    )
    local = resolve_scene(SCENE, _context(location="Refúgio do Ocaso"))
    assert late.lines[1].line_id == "clue.p1_late"
    assert early.lines[1].line_id == "clue.common"
    assert local.lines[1].line_id == "clue.at_refuge"


def test_scene_rules_reject_missing_fallback_and_unknown_identity():
    with pytest.raises(ValueError, match="fallback"):
        NarrativeBeat(
            "b",
            (NarrativeLine("x", "x", NarrativeCondition(races=frozenset({"velado"}))),),
        )
    with pytest.raises(ValueError, match="Unknown race"):
        NarrativeCondition(races=frozenset({"elfo"}))
    with pytest.raises(ValueError, match="Unknown class"):
        NarrativeCondition(race_classes=frozenset({("velado", "mago")}))


def test_one_scene_serves_every_identity_without_duplicating_the_mission():
    resolved = {
        (race, klass): resolve_scene(SCENE, _context(race=race, klass=klass))
        for race in ("remanescente", "velado", "cinereo", "hemario", "alvorano")
        for klass in ("sentinela", "errante", "vigia", "tecelao", "oraculo", "luminar")
    }
    assert {row.scene_id for row in resolved.values()} == {SCENE.scene_id}
    assert all(len(row.lines) == len(SCENE.beats) for row in resolved.values())


def test_canonical_catalog_holds_only_the_approved_p2_alda_offer():
    assert set(NARRATIVE_SCENES) == {P2_ALDA_OFFER_SCENE}


@pytest.mark.parametrize(
    ("race", "klass", "line", "options"),
    [
        ("remanescente", "sentinela", (), ()),
        ("hemario", "luminar", (), ()),
        ("cinereo", "sentinela", ("O nome que você carrega",), ()),
        ("velado", "vigia", ("Você olha para o chão",), ()),
        ("cinereo", "vigia", ("O nome que você carrega",), ("rotas",)),
    ],
)
def test_p2_alda_offer_reacts_only_where_identity_matters(race, klass, line, options):
    resolved = resolve_scene(NARRATIVE_SCENES[P2_ALDA_OFFER_SCENE], _context(race, klass))
    spoken = resolved.spoken_lines
    assert len(spoken) == len(line)
    assert all(text.startswith(f"— {prefix}") for text, prefix in zip(spoken, line, strict=True))
    assert _options(resolved) == list(options)
    if options:
        assert resolved.option("rotas").reply.startswith("— Rotas de cinza")
