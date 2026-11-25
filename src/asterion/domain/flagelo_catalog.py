"""O Despertar dos Flagelos: catálogo dos 54 equipamentos, 54 Receitas e 6 Núcleos.

Fonte: ``ASTERION_O_DESPERTAR_DOS_FLAGELOS_ESPEC_FINAL.md`` §10–§14 (aprovada pelo autor).

Só dados. Este módulo não importa ``professions`` nem ``weapon_metadata``: os dois leem daqui
(as Receitas entram no Crafting global, as armas no registro canônico de Weapon Metadata).
Não há atributos fixos: núcleo, secundários, Bind, Runas, Encantamentos e Aprimoramento vêm do
materializador e das regras globais. Todo item nasce +0.

IDs de Receita: copiados literalmente da especificação, inclusive as três grafias que fogem do
padrão (ver ``RECIPE_ID_NOTES``).
"""

from __future__ import annotations

from dataclasses import dataclass

# Ofícios do Crafting global (``professions.PROFESSIONS``).
FERREIRO = "blacksmith"
CURTEIRO = "leatherworker"
JOALHEIRO = "jeweler"

# §10: slot → (raridade, SW, Ofício). O SW coincide com ``professions.SLOT_ECONOMY_SW``.
SLOT_RULES: dict[str, tuple[str, int, str]] = {
    "Principal": ("Épico", 2, FERREIRO),
    "Secundária": ("Raro", 1, FERREIRO),
    "2H": ("Lendário", 3, FERREIRO),
    "Cabeça": ("Raro", 1, FERREIRO),
    "Torso": ("Épico", 2, FERREIRO),
    "Mãos": ("Raro", 1, CURTEIRO),
    "Pés": ("Raro", 1, CURTEIRO),
    "Acessório": ("Épico", 2, JOALHEIRO),
    "Artefato": ("Lendário", 2, JOALHEIRO),
}
SLOT_ORDER = tuple(SLOT_RULES)

# §10 Armas: forma, mãos, slot e compatibilidade explícitos (contrato de Weapon Metadata).
_ONE, _TWO = "weapon.hands.one", "weapon.hands.two"
_MAIN, _SECONDARY, _TWO_HANDED = (
    "weapon.slot.main_only",
    "weapon.slot.secondary_only",
    "weapon.slot.main_two_handed",
)
_MELEE, _BOW = "weapon.compat.melee", "weapon.compat.bow"
WEAPON_SHAPES: dict[str, tuple[str, str, str, tuple[str, ...]]] = {
    "sword_main": ("weapon.form.sword", _ONE, _MAIN, (_MELEE,)),
    "dagger_secondary": ("weapon.form.dagger", _ONE, _SECONDARY, (_MELEE,)),
    "mace_2h": ("weapon.form.mace", _TWO, _TWO_HANDED, (_MELEE,)),
    "sword_2h": ("weapon.form.sword", _TWO, _TWO_HANDED, (_MELEE,)),
    "bow_2h": ("weapon.form.bow", _TWO, _TWO_HANDED, (_BOW,)),
}
# Identidade de Proficiência de cada forma. Maça 2H: a única identidade contundente de duas
# mãos do catálogo é Martelo de Guerra (mesmo critério de mãos+família já usado no registro).
WEAPON_SHAPE_IDENTITY = {
    "sword_main": "weapon.identity.sword",
    "dagger_secondary": "weapon.identity.dagger",
    "mace_2h": "weapon.identity.war_hammer",
    "sword_2h": "weapon.identity.war_sword",
    "bow_2h": "weapon.identity.bow",
}
TWO_HANDED_SHAPE = {
    "tdo": "mace_2h",
    "vde": "sword_2h",
    "nareth": "bow_2h",
    "varzeas": "mace_2h",
    "altos": "mace_2h",
    "confins": "bow_2h",
}

# Grau do Crafting por Região (mesma faixa de nível do Flagelo: 10/20/.../60).
REGION_GRADE = {"tdo": 1, "vde": 2, "nareth": 3, "varzeas": 4, "altos": 5, "confins": 6}

# §13: materiais básicos existentes de cada Região (metal, couro, erva, quarto material).
REGION_BASICS: dict[str, tuple[str, str, str, str]] = {
    "tdo": (
        "material.tdo.ferro_de_fuligem",
        "material.tdo.couro_escoriado",
        "material.tdo.erva_cinzenta",
        "material.tdo.residuo_ocaso",
    ),
    "vde": (
        "material.vde.ferro_enredado",
        "material.vde.couro_musgoso",
        "material.vde.erva_de_turfa",
        "material.vde.resina_enredada",
    ),
    "nareth": (
        "material.nareth.bronze_de_marco",
        "material.nareth.couro_de_horizonte",
        "material.nareth.erva_de_vento",
        "material.nareth.po_de_eixo",
    ),
    "varzeas": (
        "material.varzeas.ferro_de_salmoura",
        "material.varzeas.couro_de_varzea",
        "material.varzeas.junco_ferruginoso",
        "material.varzeas.soro_antigo",
    ),
    "altos": (
        "material.altos.ferro_contrapeso",
        "material.altos.couro_escarpa",
        "material.altos.liquen_pedreira",
        "material.altos.cinza_basalto",
    ),
    "confins": (
        "material.confins.ferro_baliza",
        "material.confins.couro_marcha",
        "material.confins.musgo_limiar",
        "material.confins.po_referencia",
    ),
}
# Catalisador de Elite e Fragmento de Aprimoramento do Grau (os já existentes no Crafting).
REGION_UPGRADE_MATERIALS: dict[str, tuple[str, str]] = {
    "tdo": ("material.tdo.catalisador_elite_i", "material.tdo.fragmento_aprimoramento_i"),
    "vde": ("material.vde.catalisador_elite_ii", "material.vde.fragmento_aprimoramento_ii"),
    "nareth": (
        "material.nareth.catalisador_elite_iii",
        "material.nareth.fragmento_aprimoramento_iii",
    ),
    "varzeas": (
        "material.varzeas.catalisador_elite_iv",
        "material.varzeas.fragmento_aprimoramento_iv",
    ),
    "altos": ("material.tdo.catalisador_elite_v", "material.tdo.fragmento_aprimoramento_v"),
    "confins": ("material.tdo.catalisador_elite_vi", "material.tdo.fragmento_aprimoramento_vi"),
}

# Núcleo das Receitas lendárias: o Núcleo de Masmorra já existente da 2ª Masmorra da Região
# (decisão do autor, 2026-11-25). Não existe "Núcleo do Flagelo" e Núcleos de Chefe de
# Campanha não entram. Quantidade: 1 × SW (§12).
NUCLEUS_IDS = {
    "tdo": "material.tdo.nucleo_galerias_vigia",
    "vde": "material.vde.nucleo_no_antigo",
    "nareth": "material.nareth.nucleo_observatorio_afundado",
    "varzeas": "material.varzeas.nucleo_cisterna_transferencia",
    "altos": "material.special.altos.core.bastilha_profunda",
    "confins": "material.special.confins.core.camara_contradicoes",
}
# Fragmento do Flagelo (mesmo id de ``domain/flagelos.py``) por Região.
FLAGELO_FRAGMENT_IDS = {
    "tdo": "material.flagelo.fragmento_cinza_condensada",
    "vde": "material.flagelo.fibra_laco_morto",
    "nareth": "material.flagelo.marco_meridiano_partido",
    "varzeas": "material.flagelo.coagulo_salmoura_rubra",
    "altos": "material.flagelo.peso_fraturado",
    "confins": "material.flagelo.fragmento_leitura_incompativel",
}
# Região do catálogo → ``FlageloRegion.region_id`` (Confins usa o id regional do repositório).
REGION_ID = {
    "tdo": "tdo",
    "vde": "vde",
    "nareth": "nareth",
    "varzeas": "varzeas",
    "altos": "altos",
    "confins": "confins_do_veu",
}
FLAGELO_OF_REGION = {
    "tdo": "varkhenn",
    "vde": "nharvek",
    "nareth": "azharel",
    "varzeas": "hemrath",
    "altos": "korvann",
    "confins": "vaelith",
}

# Divergências literais da especificação, preservadas (o relatório final as cita).
RECIPE_ID_NOTES = {
    "recipe.flagelo.tdo.lamina_ultima_brasa": "sem o segmento de slot (as demais têm .lamina.)",
    "recipe.flagelo.confins.elmo.referencia_partida": "o nome do item é 'Referência Partido'",
    "recipe.flagelo.confins.relicario.duas_versoes": (
        "o item é 'Relicário do Retorno Impossível'"
    ),
}


@dataclass(frozen=True, slots=True)
class FlageloEquipmentTemplate:
    template_id: str
    number: int  # 1..54, ordem da especificação §11
    region: str  # tdo | vde | nareth | varzeas | altos | confins
    name: str
    slot: str
    recipe_id: str
    weapon_shape: str | None = None

    @property
    def rarity(self) -> str:
        return SLOT_RULES[self.slot][0]

    @property
    def sw(self) -> int:
        return SLOT_RULES[self.slot][1]

    @property
    def profession_id(self) -> str:
        return SLOT_RULES[self.slot][2]

    @property
    def grade(self) -> int:
        return REGION_GRADE[self.region]

    @property
    def flagelo_id(self) -> str:
        return FLAGELO_OF_REGION[self.region]

    @property
    def weapon_type_id(self) -> str | None:
        if self.weapon_shape is None:
            return None
        return "weapon.type.flagelo." + self.template_id.removeprefix("equipment.flagelo.")


# §11 + §12: (nome, chave do template, id da Receita) na ordem dos slots de ``SLOT_ORDER``.
_ROWS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "tdo": (
        (
            "Lâmina da Última Brasa",
            "lamina.ultima_brasa",
            "recipe.flagelo.tdo.lamina_ultima_brasa",
        ),
        (
            "Guarda da Fuligem Presa",
            "guarda.fuligem_presa",
            "recipe.flagelo.tdo.guarda.fuligem_presa",
        ),
        ("Maça do Entulho Morto", "maca.entulho_morto", "recipe.flagelo.tdo.maca.entulho_morto"),
        ("Elmo da Cinza Baixa", "elmo.cinza_baixa", "recipe.flagelo.tdo.elmo.cinza_baixa"),
        (
            "Couraça do Poente Queimado",
            "couraca.poente_queimado",
            "recipe.flagelo.tdo.couraca.poente_queimado",
        ),
        ("Luvas do Último Fôlego", "luvas.ultimo_folego", "recipe.flagelo.tdo.luvas.ultimo_folego"),
        (
            "Botas da Estrada Carbonizada",
            "botas.estrada_carbonizada",
            "recipe.flagelo.tdo.botas.estrada_carbonizada",
        ),
        (
            "Selo da Fagulha Extinta",
            "selo.fagulha_extinta",
            "recipe.flagelo.tdo.selo.fagulha_extinta",
        ),
        (
            "Relicário dos Nomes Queimados",
            "relicario.nomes_queimados",
            "recipe.flagelo.tdo.relicario.nomes_queimados",
        ),
    ),
    "vde": (
        ("Lâmina do Laço Fechado", "lamina.laco_fechado", "recipe.flagelo.vde.lamina.laco_fechado"),
        ("Guarda da Raiz Tensa", "guarda.raiz_tensa", "recipe.flagelo.vde.guarda.raiz_tensa"),
        ("Espada do Nó Profundo", "espada.no_profundo", "recipe.flagelo.vde.espada.no_profundo"),
        (
            "Elmo das Raízes Suspensas",
            "elmo.raizes_suspensas",
            "recipe.flagelo.vde.elmo.raizes_suspensas",
        ),
        (
            "Couraça do Berço Enredado",
            "couraca.berco_enredado",
            "recipe.flagelo.vde.couraca.berco_enredado",
        ),
        (
            "Luvas do Estrangulamento",
            "luvas.estrangulamento",
            "recipe.flagelo.vde.luvas.estrangulamento",
        ),
        ("Botas da Turfa Presa", "botas.turfa_presa", "recipe.flagelo.vde.botas.turfa_presa"),
        ("Selo do Nó Morto", "selo.no_morto", "recipe.flagelo.vde.selo.no_morto"),
        (
            "Relicário da Rede Sem Fim",
            "relicario.rede_sem_fim",
            "recipe.flagelo.vde.relicario.rede_sem_fim",
        ),
    ),
    "nareth": (
        ("Lâmina da Linha Exata", "lamina.linha_exata", "recipe.flagelo.nareth.lamina.linha_exata"),
        (
            "Guarda do Marco Partido",
            "guarda.marco_partido",
            "recipe.flagelo.nareth.guarda.marco_partido",
        ),
        (
            "Arco do Horizonte Contrário",
            "arco.horizonte_contrario",
            "recipe.flagelo.nareth.arco.horizonte_contrario",
        ),
        (
            "Elmo da Medida Divergente",
            "elmo.medida_divergente",
            "recipe.flagelo.nareth.elmo.medida_divergente",
        ),
        (
            "Couraça do Eixo Desviado",
            "couraca.eixo_desviado",
            "recipe.flagelo.nareth.couraca.eixo_desviado",
        ),
        (
            "Luvas da Linha Corrigida",
            "luvas.linha_corrigida",
            "recipe.flagelo.nareth.luvas.linha_corrigida",
        ),
        (
            "Botas do Meridiano Errado",
            "botas.meridiano_errado",
            "recipe.flagelo.nareth.botas.meridiano_errado",
        ),
        (
            "Selo da Referência Contrária",
            "selo.referencia_contraria",
            "recipe.flagelo.nareth.selo.referencia_contraria",
        ),
        (
            "Relicário das Duas Coordenadas",
            "relicario.duas_coordenadas",
            "recipe.flagelo.nareth.relicario.duas_coordenadas",
        ),
    ),
    "varzeas": (
        (
            "Lâmina da Salmoura Coagulada",
            "lamina.salmoura_coagulada",
            "recipe.flagelo.varzeas.lamina.salmoura_coagulada",
        ),
        (
            "Guarda da Válvula Rubra",
            "guarda.valvula_rubra",
            "recipe.flagelo.varzeas.guarda.valvula_rubra",
        ),
        (
            "Maça da Matriz Sobrecarga",
            "maca.matriz_sobrecarga",
            "recipe.flagelo.varzeas.maca.matriz_sobrecarga",
        ),
        (
            "Elmo da Pressão Carmesim",
            "elmo.pressao_carmesim",
            "recipe.flagelo.varzeas.elmo.pressao_carmesim",
        ),
        (
            "Couraça do Fluxo Contido",
            "couraca.fluxo_contido",
            "recipe.flagelo.varzeas.couraca.fluxo_contido",
        ),
        (
            "Luvas do Soro Corrosivo",
            "luvas.soro_corrosivo",
            "recipe.flagelo.varzeas.luvas.soro_corrosivo",
        ),
        ("Botas do Dique Rubro", "botas.dique_rubro", "recipe.flagelo.varzeas.botas.dique_rubro"),
        (
            "Selo da Restituição Rubra",
            "selo.restituicao_rubra",
            "recipe.flagelo.varzeas.selo.restituicao_rubra",
        ),
        (
            "Relicário da Matriz Saturada",
            "relicario.matriz_saturada",
            "recipe.flagelo.varzeas.relicario.matriz_saturada",
        ),
    ),
    "altos": (
        (
            "Lâmina do Contrapeso Invertido",
            "lamina.contrapeso_invertido",
            "recipe.flagelo.altos.lamina.contrapeso_invertido",
        ),
        (
            "Guarda da Escora Profunda",
            "guarda.escora_profunda",
            "recipe.flagelo.altos.guarda.escora_profunda",
        ),
        ("Maça do Peso Suspenso", "maca.peso_suspenso", "recipe.flagelo.altos.maca.peso_suspenso"),
        (
            "Elmo da Carga Distribuída",
            "elmo.carga_distribuida",
            "recipe.flagelo.altos.elmo.carga_distribuida",
        ),
        (
            "Couraça da Sustentação Final",
            "couraca.sustentacao_final",
            "recipe.flagelo.altos.couraca.sustentacao_final",
        ),
        (
            "Luvas do Cabo Tensionado",
            "luvas.cabo_tensionado",
            "recipe.flagelo.altos.luvas.cabo_tensionado",
        ),
        (
            "Botas da Escarpa Travada",
            "botas.escarpa_travada",
            "recipe.flagelo.altos.botas.escarpa_travada",
        ),
        (
            "Selo da Carga Compartilhada",
            "selo.carga_compartilhada",
            "recipe.flagelo.altos.selo.carga_compartilhada",
        ),
        (
            "Relicário do Peso Suspenso",
            "relicario.peso_suspenso",
            "recipe.flagelo.altos.relicario.peso_suspenso",
        ),
    ),
    "confins": (
        (
            "Lâmina das Duas Leituras",
            "lamina.duas_leituras",
            "recipe.flagelo.confins.lamina.duas_leituras",
        ),
        (
            "Guarda da Fratura Local",
            "guarda.fratura_local",
            "recipe.flagelo.confins.guarda.fratura_local",
        ),
        (
            "Arco do Protocolo Incompatível",
            "arco.protocolo_incompativel",
            "recipe.flagelo.confins.arco.protocolo_incompativel",
        ),
        (
            "Elmo da Referência Partido",
            "elmo.referencia_partido",
            "recipe.flagelo.confins.elmo.referencia_partida",
        ),
        (
            "Couraça da Marcha Fraturada",
            "couraca.marcha_fraturada",
            "recipe.flagelo.confins.couraca.marcha_fraturada",
        ),
        (
            "Luvas da Leitura Desalinhada",
            "luvas.leitura_desalinhada",
            "recipe.flagelo.confins.luvas.leitura_desalinhada",
        ),
        (
            "Botas do Limiar Incompatível",
            "botas.limiar_incompativel",
            "recipe.flagelo.confins.botas.limiar_incompativel",
        ),
        ("Selo das Duas Versões", "selo.duas_versoes", "recipe.flagelo.confins.selo.duas_versoes"),
        (
            "Relicário do Retorno Impossível",
            "relicario.retorno_impossivel",
            "recipe.flagelo.confins.relicario.duas_versoes",
        ),
    ),
}

REGIONS = ("tdo", "vde", "nareth", "varzeas", "altos", "confins")


def _templates() -> tuple[FlageloEquipmentTemplate, ...]:
    result = []
    number = 0
    for region in REGIONS:
        rows = _ROWS[region]
        assert len(rows) == len(SLOT_ORDER)
        for slot, (name, key, recipe_id) in zip(SLOT_ORDER, rows, strict=True):
            number += 1
            shape = {
                "Principal": "sword_main",
                "Secundária": "dagger_secondary",
                "2H": TWO_HANDED_SHAPE[region],
            }.get(slot)
            result.append(
                FlageloEquipmentTemplate(
                    f"equipment.flagelo.{region}.{key}",
                    number,
                    region,
                    name,
                    slot,
                    recipe_id,
                    shape,
                )
            )
    return tuple(result)


TEMPLATES: tuple[FlageloEquipmentTemplate, ...] = _templates()
TEMPLATES_BY_ID = {template.template_id: template for template in TEMPLATES}
TEMPLATES_BY_RECIPE = {template.recipe_id: template for template in TEMPLATES}
TEMPLATES_BY_FLAGELO: dict[str, tuple[FlageloEquipmentTemplate, ...]] = {
    flagelo_id: tuple(t for t in TEMPLATES if t.flagelo_id == flagelo_id)
    for flagelo_id in FLAGELO_OF_REGION.values()
}
RECIPES_BY_FLAGELO: dict[str, tuple[str, ...]] = {
    flagelo_id: tuple(t.recipe_id for t in templates)
    for flagelo_id, templates in TEMPLATES_BY_FLAGELO.items()
}

# Linhas no formato de ``weapon_metadata._CANONICAL_WEAPON_ROWS``.
WEAPON_ROWS: tuple[tuple[str, str, str, str, str, tuple[str, ...]], ...] = tuple(
    (template.weapon_type_id, template.name, *WEAPON_SHAPES[template.weapon_shape])
    for template in TEMPLATES
    if template.weapon_shape is not None
)
WEAPON_IDENTITY_BY_TYPE: dict[str, str] = {
    template.weapon_type_id: WEAPON_SHAPE_IDENTITY[template.weapon_shape]
    for template in TEMPLATES
    if template.weapon_shape is not None
}
RECIPE_TO_WEAPON_TYPE: dict[str, str] = {
    template.recipe_id: template.weapon_type_id
    for template in TEMPLATES
    if template.weapon_type_id is not None
}


# ------------------------------------------------------------------ custo (§12)


def recipe_cost_lines(template: FlageloEquipmentTemplate) -> tuple[tuple[str, int, bool], ...]:
    """Custo global de Crafting por SW + 1 Fragmento do Flagelo × SW (§12).

    Raro: 8 básicos + 4 Fragmentos de Aprimoramento; Épico: 10 básicos + 2 Catalisadores + 6
    Fragmentos; Lendário: 14 básicos + 4 Catalisadores + 12 Fragmentos + 1 Núcleo; tudo × SW.
    Os básicos seguem a proporção das Receitas regionais do mesmo Ofício (Ferreiro: metal +
    quarto material 70/30; Curteiro: couro + erva 70/30; Joalheiro: metal + quarto material
    60/40), com o mesmo arredondamento de ``professions.recipe_materials``.

    Devolve ``(material_id, quantidade, transmite_bind)`` (mesma convenção do Crafting).
    """
    rarity, sw = template.rarity, template.sw
    basics_per_sw, catalyst_per_sw, fragment_per_sw, nucleus_per_sw = {
        "Raro": (8, 0, 4, 0),
        "Épico": (10, 2, 6, 0),
        "Lendário": (14, 4, 12, 1),
    }[rarity]
    metal, leather, herb, fourth = REGION_BASICS[template.region]
    primary, secondary, ratio_tenths = {
        FERREIRO: (metal, fourth, 7),
        CURTEIRO: (leather, herb, 7),
        JOALHEIRO: (metal, fourth, 6),
    }[template.profession_id]
    total = basics_per_sw * sw
    # floor(total × ratio + 0,5), em inteiros (idêntico ao ``ROUND_FLOOR`` do Crafting).
    primary_quantity = (total * ratio_tenths * 2 + 10) // 20
    catalyst, fragment = REGION_UPGRADE_MATERIALS[template.region]
    lines = [
        (primary, primary_quantity, True),
        (secondary, total - primary_quantity, True),
        (catalyst, catalyst_per_sw * sw, False),
        (fragment, fragment_per_sw * sw, False),
        (NUCLEUS_IDS[template.region], nucleus_per_sw * sw, True),
        (FLAGELO_FRAGMENT_IDS[template.region], 1 * sw, True),
    ]
    return tuple(line for line in lines if line[1] > 0)
