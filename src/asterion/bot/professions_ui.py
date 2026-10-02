"""Telegram screens for active Professions and previewed TDO crafting."""

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from asterion.application.crafting import (
    CraftPreviewView,
    IngredientPreview,
    RecipeListView,
    RecipeView,
)
from asterion.application.professions import (
    ProfessionChangePreview,
    ProfessionHomeView,
    ProfessionProgress,
)
from asterion.bot.creation_ui import Screen
from asterion.domain.consumables import definition as consumable_definition
from asterion.domain.professions import (
    PROFESSION_BY_ID,
    PROFESSION_IDS,
    RECIPE_DEFINITIONS,
    ProfessionSlot,
)
from asterion.domain.road import rune_potency


def _button(label: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=callback)


def _money(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _profession_label(profession_id: str) -> str:
    item = PROFESSION_BY_ID[profession_id]
    return f"{item.emoji} {item.name}"


def _progress_line(progress: ProfessionProgress | None, slot_name: str) -> str:
    if progress is None:
        return f"{slot_name} · Não definido"
    name = PROFESSION_BY_ID[progress.profession_id].name
    return (
        f"{PROFESSION_BY_ID[progress.profession_id].emoji} {name}\n"
        f"Ofício {slot_name} · Nv.{progress.level}"
    )


def render_profession_home(view: ProfessionHomeView) -> Screen:
    lines = ["⚒️ Ofícios", ""]
    rows = []
    if not view.configured:
        lines.extend(
            [
                escape(view.character_name),
                "Escolha 1 Ofício Principal e 1 Secundário diferentes.",
                "A escolha inicial não tem custo.",
            ]
        )
        if view.location != "Refúgio do Ocaso":
            lines.extend(["", "📍 Local · Refúgio do Ocaso", "🔒 Escolha disponível no Refúgio"])
        elif view.foreground:
            lines.extend(["", "🔒 Ofícios · Indisponíveis durante a atividade"])
        else:
            rows.append([_button("Escolher Ofícios", "prof:init")])
    else:
        lines.extend(
            [
                escape(view.character_name),
                _progress_line(view.primary, "Principal"),
                f"PXP · {view.primary.pxp}/{view.primary.next_level_pxp or '—'}"
                if view.primary
                else "",
                "",
                _progress_line(view.secondary, "Secundário"),
                f"PXP · {view.secondary.pxp}/{view.secondary.next_level_pxp or '—'}"
                if view.secondary
                else "",
                "",
                "📚 Outros Ofícios",
            ]
        )
        for index, profession_id in enumerate(view.others):
            item = PROFESSION_BY_ID[profession_id]
            lines.append(f"{index + 1} {item.emoji} {item.name} · {item.descriptor}")
            rows.append([_button(str(index + 1), f"prof:d:{PROFESSION_IDS.index(profession_id)}")])
        if view.foreground:
            lines.extend(["", "🔒 Configuração · Indisponível durante a atividade"])
        rows.extend(
            [
                [_button("Criação", "craft:root")],
                [_button("Trocar Ofícios", "prof:change")],
            ]
        )
    rows.append([_button("← Personagem", "character:root")])
    return Screen(
        "\n".join(line for line in lines if line is not None),
        "character",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


def render_profession_initial_primary() -> Screen:
    lines = ["⚒️ Escolher Ofícios", "", "Escolha o Ofício Principal."]
    rows = []
    for index, profession_id in enumerate(PROFESSION_IDS):
        item = PROFESSION_BY_ID[profession_id]
        lines.append(f"{index + 1} {item.emoji} {item.name} · {item.descriptor}")
        rows.append([_button(str(index + 1), f"prof:ip:{index}")])
    rows.append([_button("← Ofícios", "prof:root")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def render_profession_initial_secondary(primary_index: int) -> Screen:
    primary_id = PROFESSION_IDS[primary_index]
    lines = [
        "⚒️ Escolher Ofícios",
        "",
        f"Principal · {PROFESSION_BY_ID[primary_id].name}",
        "Escolha um Ofício Secundário diferente.",
    ]
    rows = []
    for index, profession_id in enumerate(PROFESSION_IDS):
        if index == primary_index:
            continue
        item = PROFESSION_BY_ID[profession_id]
        lines.append(f"{index + 1} {item.emoji} {item.name} · {item.descriptor}")
        rows.append([_button(str(index + 1), f"prof:is:{primary_index}:{index}")])
    rows.append([_button("← Ofícios", "prof:root")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def render_profession_detail(
    profession_id: str,
    level: int | None,
    pxp: int,
    next_level_pxp: int | None,
    active: bool,
    foreground: bool,
    *,
    can_create: bool,
) -> Screen:
    item = PROFESSION_BY_ID[profession_id]
    lines = [f"{item.emoji} {item.name}", item.descriptor, ""]
    rows = []
    if active and level is not None:
        lines.extend(
            [
                f"Ofício Ativo · Nv.{level}",
                f"PXP · {pxp}/{next_level_pxp if next_level_pxp is not None else 'Cap'}",
                "",
                "📚 Receitas · Consultar",
            ]
        )
        rows.append([_button("Receitas", f"craft:recipes:{PROFESSION_IDS.index(profession_id)}")])
        if foreground:
            lines.extend(["", "🔒 Criação · Bloqueada durante a atividade"])
        elif not can_create:
            lines.extend(["", "📍 Local · Refúgio do Ocaso", "🔒 Criação · Disponível no Refúgio"])
        else:
            lines.append("🛠️ Criação · Produzir")
            rows.append(
                [_button("Criação", f"craft:recipes:{PROFESSION_IDS.index(profession_id)}")]
            )
    else:
        lines.extend(["Ofício Inativo", "📚 Receitas · Consultar", "🔒 Criação · Ofício Inativo"])
        rows.append([_button("Receitas", f"craft:recipes:{PROFESSION_IDS.index(profession_id)}")])
    rows.append([_button("← Ofícios", "prof:root")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def render_change_root(view: ProfessionHomeView) -> Screen:
    lines = ["⚒️ Trocar Ofícios", ""]
    rows = []
    if not view.configured:
        lines.append("Escolha inicial disponível sem custo.")
        if view.location == "Refúgio do Ocaso" and not view.foreground:
            rows.append([_button("Escolher Ofícios", "prof:init")])
    else:
        if view.primary is not None and view.secondary is not None:
            lines.extend(
                [
                    _progress_line(view.primary, "Principal"),
                    _progress_line(view.secondary, "Secundário"),
                    "",
                    "Inverter os Ofícios ativos · Custo 0,50 × C(nível do personagem)",
                ]
            )
            if view.location == "Refúgio do Ocaso" and not view.foreground:
                rows.append([_button("Inverter Principal/Secundário", "prof:swap")])
                rows.append([_button("Substituir Principal", "prof:slot:p")])
                rows.append([_button("Substituir Secundário", "prof:slot:s")])
        if view.location != "Refúgio do Ocaso":
            lines.extend(["", "📍 Local · Refúgio do Ocaso", "🔒 Local · Local Inapropriado"])
        if view.foreground:
            lines.extend(["", "🔒 Ofícios · Indisponíveis durante a atividade"])
    rows.append([_button("← Ofícios", "prof:root")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def render_replace_profession(slot: str, current_id: str, candidates: tuple[str, ...]) -> Screen:
    slot_label = "Principal" if slot == ProfessionSlot.PRIMARY.value else "Secundário"
    lines = [
        "⚒️ Substituir Ofício",
        "",
        f"{slot_label} atual · {PROFESSION_BY_ID[current_id].name}",
        "Escolha outro Ofício.",
    ]
    rows = []
    for profession_id in candidates:
        index = PROFESSION_IDS.index(profession_id)
        item = PROFESSION_BY_ID[profession_id]
        lines.append(f"{index + 1} {item.emoji} {item.name} · {item.descriptor}")
        rows.append(
            [_button(str(index + 1), f"prof:replace:{'p' if slot == 'primary' else 's'}:{index}")]
        )
    rows.append([_button("← Trocar Ofícios", "prof:change")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def render_change_preview(view: ProfessionChangePreview) -> Screen:
    lines = ["⚒️ Confirmar Troca de Ofício", ""]
    if view.operation == "swap":
        lines.extend(
            [
                "Principal ↔ Secundário",
            ]
        )
        if view.lost_level or view.lost_pxp:
            losses = []
            if view.lost_level:
                losses.append(f"Nv.{view.lost_level} perdido(s)")
            if view.lost_pxp:
                losses.append(f"{view.lost_pxp} PXP perdido(s)")
            lines.append("Perda no novo Secundário · " + " · ".join(losses))
        rows = [[_button("Confirmar Inversão", f"prof:ok:s:{view.token}")]]
    else:
        slot_label = "Principal" if view.slot == "primary" else "Secundário"
        assert view.profession_id is not None
        lines.extend(
            [
                f"{slot_label} → {PROFESSION_BY_ID[view.profession_id].name}",
                f"Progresso perdido · Nv.{view.lost_level} · {view.lost_pxp} PXP",
                "Receitas conhecidas permanecem disponíveis após recuperar os requisitos.",
            ]
        )
        slot_code = "p" if view.slot == "primary" else "s"
        profession_index = PROFESSION_IDS.index(view.profession_id)
        rows = [
            [
                _button(
                    "Confirmar Substituição",
                    f"prof:ok:r:{slot_code}:{profession_index}:{view.token}",
                )
            ]
        ]
    lines.extend(
        [
            "",
            f"🪙 Custo · {_money(view.cost)} Coroas",
            "📍 Local · Refúgio do Ocaso",
        ]
    )
    if view.reason == "wrong_location":
        lines.append("🔒 Local · Local Inapropriado")
        rows = []
    elif view.reason == "foreground":
        lines.append("🔒 Ofícios · Indisponíveis durante a atividade")
        rows = []
    elif view.reason == "insufficient_crowns":
        lines.append("🔒 Coroas · Insuficientes")
        rows = []
    elif view.reason:
        lines.append("🔒 Troca · Estado atualizado; revise os Ofícios")
        rows = []
    rows.append([_button("← Trocar Ofícios", "prof:change")])
    return Screen("\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows))


def _reason_label(reason: str | None) -> str:
    return {
        "profession_inactive": "🔒 Ofício Inativo",
        "profession_level": "🔒 Requisito de Ofício",
        "character_level": "🔒 Requisito de Nível",
        "wrong_location": "🔒 Local Inapropriado",
        "foreground": "🔒 Durante atividade",
        "delivery_blocked": "🔒 Entregas pendentes",
        "inventory_full": "🔒 Inventário Cheio",
        "materials": "🔒 Materiais Insuficientes",
        "crowns": "🔒 Coroas Insuficientes",
        "requires_equipment": "💫 Aplicação pelo detalhe do Equipamento",
    }.get(reason or "", "✨ Disponível")


def render_recipe_list(view: RecipeListView) -> Screen:
    profession = PROFESSION_BY_ID[view.profession_id]
    lines = [f"📚 Receitas · {profession.name}", ""]
    rows = []
    for index, item in enumerate(view.recipes):
        recipe_index = RECIPE_DEFINITIONS.index(item.recipe)
        status = _reason_label(item.reason)
        level_text = f" · Ofício Nv.{item.recipe.required_level}"
        lines.append(f"{index + 1} {escape(item.recipe.name)} · {status}{level_text}")
        rows.append([_button(str(index + 1), f"craft:r:{recipe_index}")])
    if not view.recipes:
        lines.append("Nenhuma Receita conhecida.")
    rows.append([_button("← Ofícios", "prof:root")])
    return Screen(
        "\n".join(lines), "character", InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML"
    )


def _ingredient_lines(ingredients: tuple[IngredientPreview, ...]) -> list[str]:
    lines = []
    for ingredient in ingredients:
        lines.append(f"{escape(ingredient.name)} · {ingredient.owned}/{ingredient.required}")
        if ingredient.consumed_stacks:
            consumption = []
            for _, quantity, bound in ingredient.consumed_stacks:
                suffix = " · Vinculado" if bound else " · Negociável"
                consumption.append(f"{quantity}{suffix}")
            lines.append("  Consumir · " + ", ".join(consumption))
    return lines


def render_recipe_detail(view: RecipeView) -> Screen:
    recipe = view.recipe
    lines = [
        "📚 Receita",
        escape(recipe.name),
        escape(recipe.description),
        "",
        "🧱 Materiais",
        *_ingredient_lines(view.ingredients),
        f"🪙 Coroas · {_money(view.crown_cost)}",
    ]
    if view.item_level is not None:
        lines.append(f"📈 Nível do Item · {view.item_level}")
    if recipe.output_kind == "rune":
        lines.append(
            f"🔷 Runa · {escape(recipe.rarity or '')} · Grau I · "
            f"{escape(rune_potency(recipe.output_family or 'Brasa', recipe.rarity or 'Rara'))}"
        )
    elif recipe.output_kind == "consumable":
        item = consumable_definition(recipe.output_id or "")
        if item is not None:
            lines.extend(
                [
                    f"🧪 Grau {item.grade}",
                    "Efeito · " + ", ".join(escape(effect) for effect in item.effect_metadata),
                ]
            )
    if recipe.output_kind == "equipment":
        lines.append(f"🎒 Destino · {escape(view.delivery)}")
        lines.append("✨ Secundários · Materializados no commit")
        lines.append("🔗 Vinculado" if view.result_bound else "🔓 Negociável")
    if not view.available:
        lines.append("")
        lines.append(_reason_label(view.reason))
    rows = []
    if view.available:
        rows.append([_button("Preview de Criação", f"craft:pv:{RECIPE_DEFINITIONS.index(recipe)}")])
    rows.append(
        [_button("← Receitas", f"craft:recipes:{PROFESSION_IDS.index(recipe.profession_id)}")]
    )
    return Screen(
        "\n".join(lines), "crafting", InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML"
    )


def render_craft_preview(view: CraftPreviewView) -> Screen:
    recipe = view.recipe
    item_name = recipe.output_name or recipe.name
    lines = ["🛠️ Criação · Preview", "", escape(item_name)]
    if recipe.rarity:
        output_label = {
            "equipment": recipe.output_slot or "Equipamento",
            "rune": "Runa",
            "enchantment": "Encantamento",
        }.get(recipe.output_kind, "Consumível")
        lines.append(f"{recipe.rarity} · {escape(output_label)}")
    if view.item_level is not None:
        lines.append(f"📈 Nível do Item · {view.item_level}")
    if recipe.output_kind == "rune":
        potency = rune_potency(recipe.output_family or "Brasa", recipe.rarity or "Rara")
        lines.append(
            f"🔷 Família · {escape(recipe.output_family or '')} · Grau I · {escape(potency)}"
        )
    lines.extend(["", "🧱 Materiais", *_ingredient_lines(view.ingredients)])
    lines.extend(
        [
            f"🪙 Coroas · {_money(view.crown_cost)}",
            f"🎒 Destino · {escape(view.delivery)}",
        ]
    )
    if recipe.output_kind in {"equipment", "rune"}:
        lines.append("🔗 Vinculado" if view.result_bound else "🔓 Negociável")
    if recipe.output_kind == "equipment":
        lines.append("✨ Secundários · Gerados uma vez ao confirmar")
    rows = [[_button("Criar", f"craft:cf:{view.receipt_id.hex}")]]
    rows.append(
        [_button("← Criação", f"craft:recipes:{PROFESSION_IDS.index(recipe.profession_id)}")]
    )
    return Screen(
        "\n".join(lines), "crafting", InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML"
    )


def render_craft_result(view: CraftPreviewView) -> Screen:
    payload = view.output_payload or {}
    lines = ["✅ Criação concluída", "", escape(view.recipe.output_name or view.recipe.name)]
    if view.item_level is not None:
        lines.append(f"{view.recipe.rarity} · Nv.{view.item_level}")
    elif view.recipe.output_kind == "rune":
        rune = payload.get("rune", {})
        lines.append(
            f"{escape(str(rune.get('rarity', view.recipe.rarity)))} · "
            f"Grau {rune.get('grade', view.recipe.grade)}"
        )
        lines.append("🔗 Vinculado" if rune.get("bound") else "🔓 Negociável")
    if view.recipe.output_kind == "consumable":
        item = consumable_definition(view.recipe.output_id or "")
        if item is not None:
            lines.append(f"🧪 {item.name} · +1")
    lines.append(f"🎒 Destino · {escape(str(payload.get('delivery', view.delivery)))}")
    if view.pxp_gained:
        lines.append(f"📈 PXP · +{view.pxp_gained}")
    if view.new_profession_level and view.new_profession_level > view.profession_level:
        lines.append(f"✨ Ofício · Nv.{view.new_profession_level}")
    return Screen(
        "\n".join(lines),
        "crafting",
        InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    _button(
                        "← Criação",
                        f"craft:recipes:{PROFESSION_IDS.index(view.recipe.profession_id)}",
                    )
                ],
                [_button("← Ofícios", "prof:root")],
            ]
        ),
        parse_mode="HTML",
    )
