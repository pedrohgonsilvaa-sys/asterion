"""Descrições dos itens exibidas no detalhe (em itálico, logo abaixo do título).

A descrição da Adaga é a aprovada pelo autor (2026-11-28); as demais seguem o mesmo
tom e foram escritas por tipo de item. Uma descrição própria do item (``lore``)
sempre tem prioridade sobre estas.
"""

from __future__ import annotations

WEAPON_FORM_DESCRIPTIONS = {
    "Adaga": (
        "Uma lâmina curta e leve, feita para golpes rápidos e precisos. Seu equilíbrio "
        "favorece movimentos ágeis em combate."
    ),
    "Espada": (
        "Uma lâmina equilibrada, forjada para cortes firmes e respostas rápidas. Serve a "
        "quem prefere o confronto direto."
    ),
    "Machado": (
        "Uma lâmina larga e pesada, feita para golpes que partem a defesa do inimigo. Cada "
        "movimento carrega o peso do aço."
    ),
    "Martelo": (
        "Uma cabeça maciça presa a um cabo resistente. Seus golpes quebram a postura do "
        "adversário pela pura força do impacto."
    ),
    "Maça": (
        "Uma arma de cabeça reforçada, feita para esmagar armaduras. Cada pancada abala "
        "quem a recebe, mesmo protegido."
    ),
    "Lança": (
        "Uma haste longa com ponta afiada, feita para manter o inimigo à distância. Seu "
        "alcance favorece estocadas precisas."
    ),
    "Arco": (
        "Uma arma de disparo feita de madeira flexível e corda tensa. Exige calma e "
        "pontaria para que cada flecha encontre o alvo."
    ),
    "Besta": (
        "Uma arma de disparo de mecanismo firme e travado. Seus virotes atravessam "
        "defesas com força constante."
    ),
    "Cajado": (
        "Uma haste longa que ajuda a canalizar a vontade de quem a empunha. Serve de apoio "
        "para técnicas que pedem foco."
    ),
    "Chakram": (
        "Um aro de lâmina afiada, feito para ser arremessado e recolhido com precisão. "
        "Seus giros traçam cortes inesperados."
    ),
    "Lâmina Dupla": (
        "Duas lâminas unidas por uma única empunhadura, feitas para golpes encadeados. "
        "Exigem ritmo e domínio do movimento."
    ),
    "Alabarda": (
        "Uma arma de haste longa com lâmina e gancho. Combina alcance e peso para golpes "
        "amplos e decisivos."
    ),
    "Azagaia": (
        "Uma lança curta e leve, equilibrada para o arremesso. Voa rápido e firme até o "
        "ponto escolhido."
    ),
    "Cetro": (
        "Uma haste curta e ornada, símbolo de autoridade e foco. Concentra a energia de "
        "quem a conduz."
    ),
    "Orbe": (
        "Uma esfera polida que reúne e guia energias instáveis. Responde à concentração de "
        "quem a sustenta."
    ),
    "Escudo": (
        "Uma peça firme e resistente, feita para aparar golpes e proteger quem avança. "
        "Seu peso sustenta a postura defensiva."
    ),
}

EQUIPMENT_SLOT_DESCRIPTIONS = {
    "Cabeça": (
        "Uma proteção para a cabeça, feita para amortecer impactos e manter a atenção "
        "firme em meio ao combate."
    ),
    "Torso": (
        "Uma peça robusta que cobre o tronco, feita para absorver golpes sem limitar os "
        "movimentos de quem a veste."
    ),
    "Mãos": (
        "Uma proteção para as mãos, feita para dar firmeza à empunhadura e resguardar "
        "contra cortes e impactos."
    ),
    "Pés": (
        "Um calçado resistente, feito para sustentar longas jornadas e manter o equilíbrio "
        "em terrenos hostis."
    ),
    "Acessório": (
        "Um adorno discreto que acompanha o aventureiro em suas jornadas. Pequeno, mas "
        "útil para quem sabe aproveitá-lo."
    ),
    "Artefato": (
        "Um objeto antigo que guarda uma força própria. Quem o carrega sente sua presença "
        "durante os confrontos."
    ),
}

RUNE_DESCRIPTION = (
    "Um fragmento gravado com símbolos antigos, feito para ser encaixado em equipamentos. "
    "Sua marca reforça o objeto que a recebe."
)

# Famílias de Material, na ordem em que o prefixo do nome é testado.
_MATERIAL_FAMILIES: tuple[tuple[str, str], ...] = (
    (
        "fragmento_aprimoramento",
        "Uma lasca de poder condensado, usada para reforçar equipamentos durante o "
        "Aprimoramento.",
    ),
    (
        "catalisador_elite",
        "Um componente raro, extraído de criaturas formidáveis. Serve de catalisador em "
        "trabalhos de Forja avançados.",
    ),
    (
        "nucleo_",
        "Um núcleo denso, retirado de um adversário poderoso. Guarda a energia que mantinha "
        "a criatura de pé.",
    ),
    (
        "ferro_",
        "Um ferro bruto, marcado pelo ambiente de onde foi recolhido. Ainda serve para "
        "trabalhos de forja.",
    ),
    (
        "bronze_",
        "Um bronze resistente, recolhido de estruturas antigas. Pode ser fundido para "
        "trabalhos de forja.",
    ),
    (
        "couro_",
        "Um couro curtido pelo uso e pelo tempo. Conserva resistência suficiente para "
        "trabalhos de couro.",
    ),
    (
        "erva_",
        "Uma erva colhida em terrenos difíceis. Seus usos vão do preparo de remédios ao "
        "ofício de alquimia.",
    ),
    (
        "musgo_",
        "Um musgo recolhido em locais úmidos e sombrios. Serve de base para preparos de "
        "alquimia.",
    ),
    (
        "liquen_",
        "Um líquen áspero, arrancado das pedras. Pode ser aproveitado em preparos de "
        "alquimia.",
    ),
    (
        "junco_",
        "Um junco fibroso, colhido em terrenos encharcados. Serve a diferentes trabalhos "
        "artesanais.",
    ),
    (
        "fibra_",
        "Uma fibra resistente e flexível, útil em trabalhos que pedem amarração e "
        "firmeza.",
    ),
    (
        "resina_",
        "Uma resina espessa, colhida de plantas retorcidas. Pode ser usada em preparos e "
        "acabamentos.",
    ),
    (
        "soro_",
        "Um líquido espesso, guardado há muito tempo. Pode ser aproveitado em preparos de "
        "alquimia.",
    ),
    (
        "coagulo_",
        "Um coágulo endurecido de coloração escura. Serve de ingrediente em preparos de "
        "alquimia.",
    ),
    (
        "cinza_",
        "Uma cinza fina, recolhida de terrenos marcados pelo fogo e pela pedra. Serve a "
        "diferentes ofícios.",
    ),
    (
        "po_",
        "Um pó fino, recolhido de ruínas e estruturas antigas. Pode ser aproveitado em "
        "trabalhos de ofício.",
    ),
    (
        "residuo_",
        "Um resíduo condensado das forças que atravessam as regiões de Asterion.",
    ),
    (
        "peso_",
        "Uma peça pesada de metal, marcada por rachaduras. Ainda pode ser reaproveitada em "
        "trabalhos de forja.",
    ),
    (
        "marco_",
        "Um fragmento de marco antigo, desgastado pelo tempo. Guarda ainda parte da "
        "estrutura original.",
    ),
    (
        "fragmento_",
        "Um fragmento recolhido durante a jornada. Seu uso depende do ofício de quem o "
        "examina.",
    ),
)


def material_description(key: str) -> str | None:
    """Descrição por família do Material (``material.<região>.<nome>``)."""
    stem = key.rsplit(".", 1)[-1]
    return next((text for prefix, text in _MATERIAL_FAMILIES if stem.startswith(prefix)), None)
