"""O Despertar dos Flagelos — conteúdo final: 54 templates, 54 Receitas, custos, armas,
materialização, Bestiário/Códice e esquiva global no lote (sem banco)."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from uuid import uuid4

import pytest

from asterion.application import knowledge_catalog as kc
from asterion.domain import flagelo_catalog as cat
from asterion.domain import flagelo_lore as lore
from asterion.domain import flagelos as fl
from asterion.domain import veu_combat as vc
from asterion.domain.economy import crowns_per_level, round_10
from asterion.domain.professions import (
    MATERIAL_NAMES,
    RECIPE_BY_ID,
    recipe_crown_cost,
    recipe_materials,
)
from asterion.domain.road import materialize_equipment
from asterion.domain.weapon_metadata import (
    WEAPON_DEFINITIONS,
    resolve_weapon_metadata,
    weapon_type_id_for_recipe,
)
from asterion.domain.weapon_proficiency import WEAPON_IDENTITIES, weapon_identity_for_type

D = Decimal

SPEC_RECIPE_IDS = {
    "tdo": (
        "recipe.flagelo.tdo.lamina_ultima_brasa",
        "recipe.flagelo.tdo.guarda.fuligem_presa",
        "recipe.flagelo.tdo.maca.entulho_morto",
        "recipe.flagelo.tdo.elmo.cinza_baixa",
        "recipe.flagelo.tdo.couraca.poente_queimado",
        "recipe.flagelo.tdo.luvas.ultimo_folego",
        "recipe.flagelo.tdo.botas.estrada_carbonizada",
        "recipe.flagelo.tdo.selo.fagulha_extinta",
        "recipe.flagelo.tdo.relicario.nomes_queimados",
    ),
    "vde": (
        "recipe.flagelo.vde.lamina.laco_fechado",
        "recipe.flagelo.vde.guarda.raiz_tensa",
        "recipe.flagelo.vde.espada.no_profundo",
        "recipe.flagelo.vde.elmo.raizes_suspensas",
        "recipe.flagelo.vde.couraca.berco_enredado",
        "recipe.flagelo.vde.luvas.estrangulamento",
        "recipe.flagelo.vde.botas.turfa_presa",
        "recipe.flagelo.vde.selo.no_morto",
        "recipe.flagelo.vde.relicario.rede_sem_fim",
    ),
    "nareth": (
        "recipe.flagelo.nareth.lamina.linha_exata",
        "recipe.flagelo.nareth.guarda.marco_partido",
        "recipe.flagelo.nareth.arco.horizonte_contrario",
        "recipe.flagelo.nareth.elmo.medida_divergente",
        "recipe.flagelo.nareth.couraca.eixo_desviado",
        "recipe.flagelo.nareth.luvas.linha_corrigida",
        "recipe.flagelo.nareth.botas.meridiano_errado",
        "recipe.flagelo.nareth.selo.referencia_contraria",
        "recipe.flagelo.nareth.relicario.duas_coordenadas",
    ),
    "varzeas": (
        "recipe.flagelo.varzeas.lamina.salmoura_coagulada",
        "recipe.flagelo.varzeas.guarda.valvula_rubra",
        "recipe.flagelo.varzeas.maca.matriz_sobrecarga",
        "recipe.flagelo.varzeas.elmo.pressao_carmesim",
        "recipe.flagelo.varzeas.couraca.fluxo_contido",
        "recipe.flagelo.varzeas.luvas.soro_corrosivo",
        "recipe.flagelo.varzeas.botas.dique_rubro",
        "recipe.flagelo.varzeas.selo.restituicao_rubra",
        "recipe.flagelo.varzeas.relicario.matriz_saturada",
    ),
    "altos": (
        "recipe.flagelo.altos.lamina.contrapeso_invertido",
        "recipe.flagelo.altos.guarda.escora_profunda",
        "recipe.flagelo.altos.maca.peso_suspenso",
        "recipe.flagelo.altos.elmo.carga_distribuida",
        "recipe.flagelo.altos.couraca.sustentacao_final",
        "recipe.flagelo.altos.luvas.cabo_tensionado",
        "recipe.flagelo.altos.botas.escarpa_travada",
        "recipe.flagelo.altos.selo.carga_compartilhada",
        "recipe.flagelo.altos.relicario.peso_suspenso",
    ),
    "confins": (
        "recipe.flagelo.confins.lamina.duas_leituras",
        "recipe.flagelo.confins.guarda.fratura_local",
        "recipe.flagelo.confins.arco.protocolo_incompativel",
        "recipe.flagelo.confins.elmo.referencia_partida",
        "recipe.flagelo.confins.couraca.marcha_fraturada",
        "recipe.flagelo.confins.luvas.leitura_desalinhada",
        "recipe.flagelo.confins.botas.limiar_incompativel",
        "recipe.flagelo.confins.selo.duas_versoes",
        "recipe.flagelo.confins.relicario.duas_versoes",
    ),
}
SPEC_NAMES = (
    "Lâmina da Última Brasa", "Guarda da Fuligem Presa", "Maça do Entulho Morto",
    "Elmo da Cinza Baixa", "Couraça do Poente Queimado", "Luvas do Último Fôlego",
    "Botas da Estrada Carbonizada", "Selo da Fagulha Extinta", "Relicário dos Nomes Queimados",
    "Lâmina do Laço Fechado", "Guarda da Raiz Tensa", "Espada do Nó Profundo",
    "Elmo das Raízes Suspensas", "Couraça do Berço Enredado", "Luvas do Estrangulamento",
    "Botas da Turfa Presa", "Selo do Nó Morto", "Relicário da Rede Sem Fim",
    "Lâmina da Linha Exata", "Guarda do Marco Partido", "Arco do Horizonte Contrário",
    "Elmo da Medida Divergente", "Couraça do Eixo Desviado", "Luvas da Linha Corrigida",
    "Botas do Meridiano Errado", "Selo da Referência Contrária", "Relicário das Duas Coordenadas",
    "Lâmina da Salmoura Coagulada", "Guarda da Válvula Rubra", "Maça da Matriz Sobrecarga",
    "Elmo da Pressão Carmesim", "Couraça do Fluxo Contido", "Luvas do Soro Corrosivo",
    "Botas do Dique Rubro", "Selo da Restituição Rubra", "Relicário da Matriz Saturada",
    "Lâmina do Contrapeso Invertido", "Guarda da Escora Profunda", "Maça do Peso Suspenso",
    "Elmo da Carga Distribuída", "Couraça da Sustentação Final", "Luvas do Cabo Tensionado",
    "Botas da Escarpa Travada", "Selo da Carga Compartilhada", "Relicário do Peso Suspenso",
    "Lâmina das Duas Leituras", "Guarda da Fratura Local", "Arco do Protocolo Incompatível",
    "Elmo da Referência Partido", "Couraça da Marcha Fraturada", "Luvas da Leitura Desalinhada",
    "Botas do Limiar Incompatível", "Selo das Duas Versões", "Relicário do Retorno Impossível",
)
SLOT_SPEC = {
    "Principal": ("Épico", 2, "blacksmith"),
    "Secundária": ("Raro", 1, "blacksmith"),
    "2H": ("Lendário", 3, "blacksmith"),
    "Cabeça": ("Raro", 1, "blacksmith"),
    "Torso": ("Épico", 2, "blacksmith"),
    "Mãos": ("Raro", 1, "leatherworker"),
    "Pés": ("Raro", 1, "leatherworker"),
    "Acessório": ("Épico", 2, "jeweler"),
    "Artefato": ("Lendário", 2, "jeweler"),
}


# ------------------------------------------------------------------ catálogo


def test_54_templates_in_spec_order_with_names_slots_and_rarity():
    assert len(cat.TEMPLATES) == 54
    assert tuple(t.name for t in cat.TEMPLATES) == SPEC_NAMES
    assert [t.number for t in cat.TEMPLATES] == list(range(1, 55))
    assert len({t.template_id for t in cat.TEMPLATES}) == 54
    for template in cat.TEMPLATES:
        rarity, sw, profession = SLOT_SPEC[template.slot]
        assert (template.rarity, template.sw, template.profession_id) == (rarity, sw, profession)
    assert Counter(t.slot for t in cat.TEMPLATES) == {slot: 6 for slot in SLOT_SPEC}
    for flagelo_id, templates in cat.TEMPLATES_BY_FLAGELO.items():
        assert len(templates) == 9, flagelo_id
        assert tuple(t.slot for t in templates) == tuple(SLOT_SPEC)


def test_54_recipes_with_the_spec_ids_one_per_template():
    expected = [rid for ids in SPEC_RECIPE_IDS.values() for rid in ids]
    assert [t.recipe_id for t in cat.TEMPLATES] == expected
    assert len(set(expected)) == 54
    flagelo_recipes = [
        r for r in RECIPE_BY_ID.values() if r.recipe_id.startswith("recipe.flagelo.")
    ]
    assert len(flagelo_recipes) == 54
    for template in cat.TEMPLATES:
        recipe = RECIPE_BY_ID[template.recipe_id]
        assert recipe.unlock_id == template.recipe_id  # só aparece depois de descoberta
        assert recipe.output_kind == "equipment"
        assert recipe.output_name == template.name and recipe.output_slot == template.slot
        assert recipe.output_id == template.template_id
        assert recipe.rarity == template.rarity and recipe.sw == template.sw
        assert recipe.profession_id == template.profession_id
        assert recipe.grade == template.grade
    for region, ids in SPEC_RECIPE_IDS.items():
        flagelo_id = cat.FLAGELO_OF_REGION[region]
        assert fl.FLAGELOS_BY_ID[flagelo_id].flagelo.recipe_unlock_ids() == ids


def test_grade_and_profession_requirement_follow_the_global_tables():
    grades = {"tdo": 1, "vde": 2, "nareth": 3, "varzeas": 4, "altos": 5, "confins": 6}
    minimum = {1: 1, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15}
    rarity_req = {"Raro": 5, "Épico": 10, "Lendário": 16}
    for template in cat.TEMPLATES:
        recipe = RECIPE_BY_ID[template.recipe_id]
        assert recipe.grade == grades[template.region]
        assert recipe.required_level == max(minimum[recipe.grade], rarity_req[recipe.rarity])


@pytest.mark.parametrize(
    ("rarity", "basics", "catalysts", "fragments", "nuclei"),
    [("Raro", 8, 0, 4, 0), ("Épico", 10, 2, 6, 0), ("Lendário", 14, 4, 12, 1)],
)
def test_recipe_cost_is_the_global_formula_times_sw_plus_flagelo_fragment(
    rarity, basics, catalysts, fragments, nuclei
):
    for template in (t for t in cat.TEMPLATES if t.rarity == rarity):
        recipe = RECIPE_BY_ID[template.recipe_id]
        lines = {m.material_id: m for m in recipe_materials(recipe, 60)}
        sw = template.sw
        metal, leather, herb, fourth = cat.REGION_BASICS[template.region]
        catalyst, fragment = cat.REGION_UPGRADE_MATERIALS[template.region]
        regional = {metal, leather, herb, fourth}
        assert sum(m.quantity for k, m in lines.items() if k in regional) == basics * sw
        if catalysts:
            assert lines[catalyst].quantity == catalysts * sw
        else:
            assert catalyst not in lines
        assert lines[fragment].quantity == fragments * sw
        nucleus = cat.NUCLEUS_IDS[template.region]
        assert (lines[nucleus].quantity if nucleus in lines else 0) == nuclei * sw
        assert lines[cat.FLAGELO_FRAGMENT_IDS[template.region]].quantity == sw
        # Catalisador/Fragmento de Aprimoramento não transmitem Bind (regra do Crafting).
        assert not lines[fragment].transmits_bind
        if catalysts:
            assert not lines[catalyst].transmits_bind
        # Só materiais existentes: nenhum básico paralelo.
        allowed = regional | {catalyst, fragment, nucleus, *cat.FLAGELO_FRAGMENT_IDS.values()}
        assert set(lines) <= allowed


def test_basic_split_uses_the_regional_profession_proportion():
    tdo = {t.slot: t for t in cat.TEMPLATES if t.region == "tdo"}
    smith = recipe_materials(RECIPE_BY_ID[tdo["Principal"].recipe_id], 10)
    assert [(m.material_id, m.quantity) for m in smith[:2]] == [
        ("material.tdo.ferro_de_fuligem", 14),
        ("material.tdo.residuo_ocaso", 6),
    ]
    leather = recipe_materials(RECIPE_BY_ID[tdo["Mãos"].recipe_id], 10)
    assert [(m.material_id, m.quantity) for m in leather[:2]] == [
        ("material.tdo.couro_escoriado", 6),
        ("material.tdo.erva_cinzenta", 2),
    ]
    jewel = recipe_materials(RECIPE_BY_ID[tdo["Acessório"].recipe_id], 10)
    assert [(m.material_id, m.quantity) for m in jewel[:2]] == [
        ("material.tdo.ferro_de_fuligem", 12),
        ("material.tdo.residuo_ocaso", 8),
    ]


def test_crown_fee_is_c_times_sw_times_rarity_factor():
    factor = {"Raro": D("0.35"), "Épico": D("0.50"), "Lendário": D("0.75")}
    for template in cat.TEMPLATES:
        recipe = RECIPE_BY_ID[template.recipe_id]
        for level in (10, 37, 60):
            assert recipe_crown_cost(recipe, level) == round_10(
                D(crowns_per_level(level)) * template.sw * factor[template.rarity]
            )


def test_legendary_nucleus_is_the_second_dungeon_core_and_fragments_are_named():
    # Decisão do autor (2026-11-25): Núcleo da 2ª Masmorra da Região, sem Núcleo do Flagelo.
    assert cat.NUCLEUS_IDS == {
        "tdo": "material.tdo.nucleo_galerias_vigia",
        "vde": "material.vde.nucleo_no_antigo",
        "nareth": "material.nareth.nucleo_observatorio_afundado",
        "varzeas": "material.varzeas.nucleo_cisterna_transferencia",
        "altos": "material.special.altos.core.bastilha_profunda",
        "confins": "material.special.confins.core.camara_contradicoes",
    }
    assert not any(i.startswith("material.flagelo.nucleo") for i in MATERIAL_NAMES)
    assert not hasattr(cat, "NUCLEUS_NAMES")
    assert {MATERIAL_NAMES[i] for i in cat.NUCLEUS_IDS.values()} == {
        "Núcleo das Galerias do Vigia",
        "Núcleo do Nó Antigo",
        "Núcleo do Observatório Afundado",
        "Núcleo da Cisterna de Transferência",
        "Núcleo da Bastilha Profunda",
        "Núcleo da Câmara das Contradições",
    }
    campaign_boss_cores = {
        "material.tdo.nucleo_vigia_partido",
        "material.vde.nucleo_matriarca_das_raizes",
        "material.nareth.nucleo_arconte_invertido",
        "material.varzeas.nucleo_matriz_rubra",
        "material.special.altos.core.colosso_cinereo",
        "material.special.confins.core.regente_fraturado",
    }
    for template in cat.TEMPLATES:
        ids = {m.material_id for m in recipe_materials(RECIPE_BY_ID[template.recipe_id], 60)}
        assert not ids & campaign_boss_cores
        assert (cat.NUCLEUS_IDS[template.region] in ids) == (template.rarity == "Lendário")
    assert {MATERIAL_NAMES[i] for i in cat.FLAGELO_FRAGMENT_IDS.values()} == set(
        fl.FRAGMENT_NAMES.values()
    )
    for region, fragment in cat.FLAGELO_FRAGMENT_IDS.items():
        definition = fl.region(cat.REGION_ID[region]).flagelo
        assert definition.fragment_material_id == fragment


# ------------------------------------------------------------------ armas


def test_weapon_metadata_is_explicit_and_canonical():
    forms = {
        "tdo": "weapon.form.mace",
        "vde": "weapon.form.sword",
        "nareth": "weapon.form.bow",
        "varzeas": "weapon.form.mace",
        "altos": "weapon.form.mace",
        "confins": "weapon.form.bow",
    }
    weapons = [t for t in cat.TEMPLATES if t.slot in {"Principal", "Secundária", "2H"}]
    assert len(weapons) == 18
    for template in weapons:
        definition = WEAPON_DEFINITIONS[template.weapon_type_id]
        assert definition.item_name == template.name
        assert definition.persisted_item_slot == template.slot
        assert weapon_type_id_for_recipe(template.recipe_id) == template.weapon_type_id
        identity = weapon_identity_for_type(template.weapon_type_id)
        assert WEAPON_IDENTITIES[identity].handedness == definition.handedness
        if template.slot == "Principal":
            assert (definition.weapon_form, definition.handedness) == (
                "weapon.form.sword",
                "weapon.hands.one",
            )
            assert definition.compatibility_tags == {"weapon.compat.melee"}
        elif template.slot == "Secundária":
            assert (definition.weapon_form, definition.handedness) == (
                "weapon.form.dagger",
                "weapon.hands.one",
            )
        else:
            assert definition.weapon_form == forms[template.region]
            assert definition.handedness == "weapon.hands.two"
            expected = "weapon.compat.bow" if forms[template.region].endswith("bow") else (
                "weapon.compat.melee"
            )
            assert definition.compatibility_tags == {expected}
    # Armadura sem classe mecânica e sem metadata de arma.
    for template in cat.TEMPLATES:
        if template.slot not in {"Principal", "Secundária", "2H"}:
            assert template.weapon_type_id is None


# ------------------------------------------------------------------ materialização


@pytest.mark.parametrize("template", cat.TEMPLATES, ids=lambda t: t.template_id)
def test_every_template_materializes_at_plus_zero_with_the_global_materializer(template):
    level = fl.region(cat.REGION_ID[template.region]).reference_level
    payload = materialize_equipment(
        f"test:{template.template_id}",
        template.rarity,
        level,
        forced_name=template.name,
        forced_slot=template.slot,
        bound=True,
        weapon_type_id=template.weapon_type_id,
    )
    assert payload["item_name"] == template.name and payload["slot"] == template.slot
    assert payload["rarity"] == template.rarity and payload["item_level"] == level
    assert payload["enhancement"] == 0 and payload["rune"] is None
    assert payload["enchantment"] is None
    secondaries = {"Raro": 1, "Épico": 2, "Lendário": 3}[template.rarity]
    assert len(payload["secondaries"]) == secondaries
    if template.weapon_type_id is not None:
        assert resolve_weapon_metadata(payload).definition.weapon_type_id == (
            template.weapon_type_id
        )


def test_equipment_template_is_uniform_one_in_nine_with_duplicates():
    for flagelo_id in fl.FLAGELO_EQUIPMENT_TEMPLATES:
        draws = Counter(fl.equipment_template(f"evt{i}", flagelo_id) for i in range(9000))
        assert set(draws) == set(fl.FLAGELO_EQUIPMENT_TEMPLATES[flagelo_id])
        assert all(800 < count < 1200 for count in draws.values()), draws
    # Mesmo evento sorteia o mesmo template (retry/restart); eventos diferentes podem repetir.
    assert fl.equipment_template("evt", "varkhenn") == fl.equipment_template("evt", "varkhenn")


def test_recipe_discovery_is_one_uniform_unknown_and_none_when_all_known():
    unknown = list(fl.FLAGELO_RECIPES["korvann"])
    character = uuid4()
    hits = Counter()
    for index in range(20_000):
        found = fl.recipe_roll(f"evt{index}", character, unknown)
        if found:
            hits[found] += 1
    total = sum(hits.values())
    assert 0.23 < total / 20_000 < 0.27
    assert set(hits) == set(unknown)
    assert all(abs(count - total / 9) < total / 9 * 0.2 for count in hits.values())
    assert fl.recipe_roll("evt", character, []) is None


# ------------------------------------------------------------------ Bestiário e Códice


FORBIDDEN = ("Região 7", "Avesso é senciente", "viajou no tempo", "culpa coletiva")


def test_bestiary_texts_are_the_approved_ones_on_each_flagelo():
    assert set(lore.BESTIARY_TEXTS) == set(fl.FLAGELOS_BY_ID)
    for region in fl.REGIONS:
        note = kc.CREATURE_NOTES[region.flagelo.bestiary_key]
        description, knowledge = lore.BESTIARY_TEXTS[region.flagelo.flagelo_id]
        assert note == f"{description}\n\nConhecimento: {knowledge}"
        assert kc.CREATURE_PRESENTATION[region.flagelo.bestiary_key].region_id == region.region_id
    assert lore.BESTIARY_TEXTS["varkhenn"][0].startswith(
        "Varkhenn não parece carregar cinzas. Parece ter sido construído por elas."
    )
    assert lore.BESTIARY_TEXTS["vaelith"][1] == (
        "criatura anômala associada a leituras incompatíveis e fraturas locais. Isso não prova "
        "que o Avesso seja senciente nem prova viagem temporal."
    )


def test_codex_has_the_general_entry_and_one_per_flagelo_with_text():
    assert len(lore.ALL_CODEX) == 7
    titles = [entry.title for entry in lore.ALL_CODEX]
    assert titles == [
        "O Despertar dos Flagelos",
        "Cinzas e Varkhenn",
        "Laços e Nharvek",
        "Meridiano e Azharel",
        "Hemaris e Hemrath",
        "Peso e Korvann",
        "Fraturas e Vaelith",
    ]
    for entry in lore.ALL_CODEX:
        assert kc.CODEX_BY_ID[entry.entry_id].title == entry.title
        assert kc.CODEX_FRAGMENTS[entry.fragment_id].text == entry.text
    for region in fl.REGIONS:
        assert lore.FLAGELO_CODEX[region.flagelo.flagelo_id].entry_id == region.flagelo.codex_key
    assert lore.FLAGELO_CODEX["hemrath"].text == (
        "Semelhança visual não estabelece origem. Hemários modernos não são experimentos vivos "
        "nem culpados coletivos pelo Projeto Hemaris."
    )


def test_no_unapproved_lore_was_added():
    texts = [t for pair in lore.BESTIARY_TEXTS.values() for t in pair]
    texts += [entry.text for entry in lore.ALL_CODEX]
    for text in texts:
        for phrase in FORBIDDEN:
            assert phrase not in text


# ------------------------------------------------------------------ esquiva global


def _unit(evasion: str = "0") -> tuple:
    player_id = uuid4()
    player = vc.PlayerUnit(player_id, D(1000), D(1000), D(50), evasion=D(evasion))
    enemy = vc.EnemyUnit.from_data(
        "varkhenn",
        {"hp": "1000", "max_hp": "1000", "attack": "138", "defense": "100", "agility": "94"},
    )
    return player_id, player, enemy


def _hit(seed: str | None, evasion: str = "0", streak: int = 0):
    player_id, player, enemy = _unit(evasion)
    player.evasion_streak = streak
    decision = vc.EnemyDecisionData("varkhenn", "golpe_de_cinza", (player_id,), False)
    outcome = vc.resolve_batch(
        {"varkhenn": enemy},
        {player_id: player},
        [],
        [decision],
        kit=fl.kit,
        level=10,
        evasion_seed=seed,
    )
    return outcome, player


def test_flagelo_hits_roll_the_global_evasion():
    dodged = sum(1 for i in range(2000) if _hit(f"s{i}", "30")[0].dodged_by_character)
    assert 0.25 < dodged / 2000 < 0.35
    outcome, player = next(
        result for i in range(200) if (result := _hit(f"d{i}", "50"))[0].dodged_by_character
    )
    assert outcome.damage_taken == {} and player.hp == D(1000)
    assert player.evasion_streak == 1
    assert any(item["kind"] == "player_dodged" for item in outcome.history)


def test_no_evasion_means_every_hit_lands_and_third_hit_after_two_dodges_lands():
    outcome, _ = _hit("x", "0")
    assert outcome.damage_taken and not outcome.dodged_by_character
    # Trava anti-sequência do motor: depois de 2 esquivas seguidas, o golpe não rola.
    for index in range(50):
        outcome, player = _hit(f"streak{index}", "100", streak=2)
        assert outcome.damage_taken and player.evasion_streak == 0


def test_veu_batch_without_seed_never_dodges():
    outcome, _ = _hit(None, "100")
    assert outcome.damage_taken and not outcome.dodged_by_character


# ------------------------------------------------------------------ participação


def test_meaningful_effect_needs_a_real_state_change():
    from asterion.application.flagelo_combat import _changed
    from asterion.domain.combat import DotState, Effect

    weak = Effect("veu:atq", "attack", D("0.10"), 2, 1)
    renewed = Effect("veu:atq", "attack", D("0.10"), 3, 2)
    same = Effect("veu:atq", "attack", D("0.10"), 2, 1)
    # Resistido / imune / no-op: o motor não mudou nada no alvo.
    assert not _changed([weak], [], [same], [])
    assert not _changed([], [], [], [])
    # Novo efeito, duração renovada ou pilha aumentada contam.
    assert _changed([], [], [weak], [])
    assert _changed([weak], [], [renewed], [])
    burn = DotState("burn", 1, 3, D(100), "p")
    stacked = DotState("burn", 2, 3, D(100), "p")
    assert _changed([], [burn], [], [stacked])
    assert not _changed([], [burn], [], [DotState("burn", 1, 3, D(100), "p")])


def test_overheal_does_not_count_as_effective_healing():
    healer, hurt = uuid4(), uuid4()
    players = {
        healer: vc.PlayerUnit(healer, D(1000), D(1000), D(50)),
        hurt: vc.PlayerUnit(hurt, D(900), D(1000), D(50)),
    }
    enemy = vc.EnemyUnit.from_data(
        "varkhenn",
        {"hp": "1000", "max_hp": "1000", "attack": "138", "defense": "100", "agility": "94"},
    )
    intent = vc.PlayerIntent(
        healer, "art", None, 0, (vc.SupportResult(healer, hurt, "heal", 5000),)
    )
    outcome = vc.resolve_batch(
        {"varkhenn": enemy}, players, [intent], [], kit=fl.kit, level=10, evasion_seed="h"
    )
    assert outcome.heal_by_character == {healer: 100}
    full = vc.PlayerIntent(healer, "art", None, 0, (vc.SupportResult(healer, healer, "heal", 50),))
    outcome = vc.resolve_batch(
        {"varkhenn": enemy}, players, [full], [], kit=fl.kit, level=10, evasion_seed="h"
    )
    assert outcome.heal_by_character == {}


def test_defender_without_an_incoming_hit_prevents_nothing():
    player_id = uuid4()
    players = {player_id: vc.PlayerUnit(player_id, D(1000), D(1000), D(50))}
    enemy = vc.EnemyUnit.from_data(
        "korvann",
        {"hp": "1000", "max_hp": "1000", "attack": "310", "defense": "306", "agility": "204"},
    )
    defend = vc.PlayerIntent(player_id, "defend", None, 0)
    # O Flagelo usou um buff próprio: ninguém foi atingido, então o Defender não preveniu nada.
    buff = vc.EnemyDecisionData("korvann", "escora_inversa", (), False)
    outcome = vc.resolve_batch(
        {"korvann": enemy}, players, [defend], [buff], kit=fl.kit, level=50, evasion_seed="d"
    )
    assert outcome.prevented_by_character == {}
    metrics = fl.ParticipationMetrics(defender_prevented_damage=0)
    assert fl.participation_points(metrics) == 0
