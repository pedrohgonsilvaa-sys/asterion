"""Bestiário do Véu: VEU-01..VEU-18 conforme a fonte (§7)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from asterion.domain.road import CATEGORY
from asterion.domain.veu_bestiary import (
    CREATURES_BY_CODE,
    VEU_CREATURES,
    ActionKind,
    Category,
    creature,
)

D = Decimal

# código: (categoria, arquétipo, porte)
SOURCE = {
    "VEU-01": ("common", "Predador", "Médio"),
    "VEU-02": ("common", "Equilibrado", "Médio"),
    "VEU-03": ("common", "Resistente", "Médio"),
    "VEU-04": ("uncommon", "Controlador", "Médio"),
    "VEU-05": ("uncommon", "Ágil", "Médio"),
    "VEU-06": ("uncommon", "Blindado", "Grande"),
    "VEU-07": ("elite", "Controlador", "Grande"),
    "VEU-08": ("common", "Predador", "Médio"),
    "VEU-09": ("elite", "Técnico", "Grande"),
    "VEU-10": ("elite", "Equilibrado", "Grande"),
    "VEU-11": ("uncommon", "Predador", "Grande"),
    "VEU-12": ("elite", "Bruto", "Grande"),
    "VEU-13": ("common", "Ágil", "Médio"),
    "VEU-14": ("uncommon", "Resistente", "Grande"),
    "VEU-15": ("elite", "Suporte", "Grande"),
    "VEU-16": ("elite", "Técnico", "Médio"),
    "VEU-17": ("elite", "Controlador", "Grande"),
    "VEU-18": ("boss", "Equilibrado/Controlador", "Colossal"),
}

# código: [(rótulo, kind, coeficiente, CD)]
KITS = {
    "VEU-01": [("Mordida Vertical", "damage", "1.00", None),
               ("Fechamento Súbito", "damage_debuff", "0.90", 3)],
    "VEU-02": [("Pulso de Carne", "damage", "1.00", None),
               ("Pulsação Irregular", "multi_target", "0.80", 3)],
    "VEU-03": [("Impacto Costal", "damage", "1.00", None),
               ("Fechamento Torácico", "barrier", None, 4)],
    "VEU-04": [("Mordida Lisa", "damage", "1.00", None),
               ("Rosto Errado", "damage_debuff", "0.85", 3)],
    "VEU-05": [("Investida Invertida", "damage", "1.10", None),
               ("Passo Impossível", "self_buff", None, 4)],
    "VEU-06": [("Golpe de Placa", "damage", "1.00", None),
               ("Recompor Carapaça", "barrier", None, 4)],
    "VEU-07": [("Abertura", "damage", "1.00", None), ("Chamado Oco", "aoe", "0.75", 3),
               ("Câmara Fechada", "barrier", None, 4)],
    "VEU-08": [("Mordida Tripla", "damage", "1.00", None),
               ("Mordida Cruzada", "damage", "1.20", 3)],
    "VEU-09": [("Corte de Ossatura", "damage", "1.00", None),
               ("Trama Óssea", "debuff", None, 3), ("Costura de Margem", "barrier", None, 4)],
    "VEU-10": [("Golpe da Casca", "damage", "1.00", None),
               ("Abertura Interna", "damage", "1.35", 4), ("Fechar-se", "barrier", None, 4)],
    "VEU-11": [("Fauce", "damage", "1.10", None), ("Arrasto", "damage_debuff", "0.90", 3)],
    "VEU-12": [("Impacto Irregular", "damage", "1.05", None),
               ("Torção", "damage_debuff", "0.85", 3), ("Pressão de Massa", "damage", "1.30", 4)],
    "VEU-13": [("Estalo Vertebral", "damage", "1.00", None),
               ("Salto de Junta", "self_buff", None, 4)],
    "VEU-14": [("Esmagamento", "damage", "1.00", None),
               ("Pele Maleável", "self_buff", None, 4)],
    "VEU-15": [("Golpe do Portador", "damage", "1.00", None),
               ("Movimento Interno", "multi_target", "0.90", 3),
               ("Expulsão", "barrier", None, 4)],
    "VEU-16": [("Golpe Ausente", "damage", "1.00", None),
               ("Falha de Contorno", "damage_debuff", "0.85", 3)],
    "VEU-17": [("Golpe de Testemunho", "damage", "1.00", None),
               ("Fixar Presença", "debuff", None, 3), ("Observação Total", "aoe", "0.70", 4)],
    "VEU-18": [("Golpe da Margem", "damage", "1.00", None),
               ("Medida Contraditória", "damage_debuff", "0.90", 3),
               ("Linha Impossível", "aoe", "0.75", 3),
               ("Preparar a Ruptura", "damage", "1.75", 5),
               ("Recompor a Margem", "barrier", None, None)],
}


def test_the_eighteen_ids_exist_once_and_in_order():
    codes = [c.code for c in VEU_CREATURES]
    assert codes == [f"VEU-{n:02d}" for n in range(1, 19)]
    assert len({c.creature_id for c in VEU_CREATURES}) == 18


def test_ids_assets_and_bestiary_keys_follow_the_naming_of_the_source():
    first = creature("VEU-01")
    assert first.creature_id == "veu_01_mandibula_vigilia"
    assert first.asset_key == "event_veu_01_mandibula_vigilia"
    assert first.bestiary_key == "bestiary.veu.01_mandibula_vigilia"
    last = creature("veu_18_rei_que_nao_existe")
    assert last.asset_key == "event_veu_18_rei_que_nao_existe"
    assert last.bestiary_key == "bestiary.veu.18_rei_que_nao_existe"
    with pytest.raises(KeyError):
        creature("VEU-19")


@pytest.mark.parametrize("code", sorted(SOURCE))
def test_category_archetype_and_size_follow_the_source(code):
    category, archetype, size = SOURCE[code]
    found = CREATURES_BY_CODE[code]
    assert found.category.value == category
    assert found.archetype == archetype
    assert found.size == size
    assert found.category.value in CATEGORY  # a categoria existe no motor


@pytest.mark.parametrize("code", sorted(KITS))
def test_kit_follows_the_source(code):
    found = CREATURES_BY_CODE[code]
    got = [
        (a.label, a.kind.value, str(a.coefficient) if a.coefficient is not None else None,
         a.cooldown)
        for a in found.actions
    ]
    expected = [
        (label, kind, coefficient, cooldown) for label, kind, coefficient, cooldown in KITS[code]
    ]
    assert got == expected


def test_all_four_categories_are_used():
    assert {c.category for c in VEU_CREATURES} == set(Category)
    assert [c.code for c in VEU_CREATURES if c.category is Category.BOSS] == ["VEU-18"]


def test_debuffs_are_ten_percent_for_two_turns_on_the_declared_stat():
    expected = {
        "VEU-01": ("AGI", D("-0.10")), "VEU-04": ("PER", D("-0.10")),
        "VEU-09": ("DEF", D("-0.10")), "VEU-11": ("AGI", D("-0.10")),
        "VEU-12": ("ATQ", D("-0.10")), "VEU-16": ("DEF", D("-0.10")),
        "VEU-17": ("PER", D("-0.10")), "VEU-18": ("DEF", D("-0.10")),
    }
    for code, (stat, magnitude) in expected.items():
        action = next(
            a for a in CREATURES_BY_CODE[code].actions
            if a.kind in {ActionKind.DAMAGE_DEBUFF, ActionKind.DEBUFF}
        )
        assert (action.stat, action.magnitude, action.turns) == (stat, magnitude, 2)


def test_self_buffs_are_plus_ten_percent_for_two_turns():
    expected = {"VEU-05": "AGI", "VEU-13": "AGI", "VEU-14": "DEF"}
    for code, stat in expected.items():
        action = next(a for a in CREATURES_BY_CODE[code].actions
                      if a.kind is ActionKind.SELF_BUFF)
        assert (action.stat, action.magnitude, action.turns) == (stat, D("0.10"), 2)


def test_barriers_use_the_declared_basis_and_never_invent_a_duration():
    attack_basis = {"VEU-03": "0.60", "VEU-06": "0.80", "VEU-09": "0.70"}
    hp_basis = {"VEU-07": "0.06", "VEU-10": "0.07", "VEU-15": "0.06", "VEU-18": "0.08"}
    for code, value in attack_basis.items():
        barrier = next(a for a in CREATURES_BY_CODE[code].actions
                       if a.kind is ActionKind.BARRIER)
        assert barrier.barrier_attack_coefficient == D(value)
        assert barrier.barrier_hp_fraction is None
    for code, value in hp_basis.items():
        barrier = next(a for a in CREATURES_BY_CODE[code].actions
                       if a.kind is ActionKind.BARRIER)
        assert barrier.barrier_hp_fraction == D(value)
        assert barrier.barrier_attack_coefficient is None
    every_barrier = [a for c in VEU_CREATURES for a in c.actions
                     if a.kind is ActionKind.BARRIER]
    assert len(every_barrier) == 7
    assert all(a.duration is None for a in every_barrier)


def test_two_target_actions_hit_two_targets():
    for code in ("VEU-02", "VEU-15"):
        action = next(a for a in CREATURES_BY_CODE[code].actions
                      if a.kind is ActionKind.MULTI_TARGET)
        assert action.targets == 2


def test_boss_prepared_action_is_always_telegraphed_and_never_consecutive():
    prepared = next(a for a in creature("VEU-18").actions if a.prepared)
    assert prepared.label == "Preparar a Ruptura"
    assert prepared.coefficient == D("1.75") and prepared.cooldown == 5
    assert prepared.always_telegraphed and prepared.not_consecutive
    recompose = next(a for a in creature("VEU-18").actions if a.key == "recompor_a_margem")
    assert recompose.max_uses == 2
    assert not any(a.prepared for c in VEU_CREATURES if c.code != "VEU-18" for a in c.actions)


def test_no_automatic_summon_and_notes_of_the_source():
    assert "Sem invocação automática na primeira versão." in creature("VEU-07").notes
    assert "Sem Hard CC recorrente." in creature("VEU-18").notes
    assert creature("VEU-01").function == "ameaça corpo a corpo"
    assert creature("VEU-02").function == "pressão contra vários alvos"
