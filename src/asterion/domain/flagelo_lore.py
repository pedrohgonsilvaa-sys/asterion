"""O Despertar dos Flagelos: textos aprovados de Bestiário e Códice (espec. final §15–§16).

Copiados literalmente da especificação aprovada pelo autor. Não acrescentar lore: nada de
Avesso senciente, viagem temporal, Região 7, culpa coletiva dos Hemários ou explicação causal.
Bestiário e Códice registram o conhecimento do personagem (cada entrada é por personagem).
"""

from __future__ import annotations

from dataclasses import dataclass

# §15 Bestiário: descrição + "Conhecimento", por ``flagelo_id``.
BESTIARY_TEXTS: dict[str, tuple[str, str]] = {
    "varkhenn": (
        "Varkhenn não parece carregar cinzas. Parece ter sido construído por elas. O corpo é "
        "coberto por placas escuras, rachadas e impregnadas de fuligem. Entre as fissuras há "
        "pontos de calor baixo, como brasas que resistiram mais tempo do que deveriam. Ele "
        "avança sem pressa, e cada golpe parece carregar o peso de alguma coisa que já caiu. "
        "Os registros associam Varkhenn ao desgaste, queimaduras, redução ofensiva e golpes "
        "pesados.",
        "criatura anômala associada ao desgaste das Terras do Ocaso; origem desconhecida.",
    ),
    "nharvek": (
        "Nharvek parece uma criatura presa à própria estrutura. Fibras grossas atravessam seu "
        "corpo e desaparecem sob placas de matéria vegetal endurecida. Um puxão, uma tensão, "
        "um nó; depois o alvo percebe que já não se move como antes. Os registros associam "
        "Nharvek à redução de Agilidade e Defesa e à pressão sobre vários combatentes.",
        "criatura anômala associada a laços, pressão e alteração de ritmo.",
    ),
    "azharel": (
        "Azharel é difícil de descrever de frente. A posição das placas parece mudar conforme "
        "o ponto de observação. Uma linha pode parecer reta de um lado e inclinada de outro. "
        "Não há evidência de teletransporte ou viagem temporal. Há apenas referências que "
        "deixam de concordar.",
        "criatura anômala ligada a referências incompatíveis. Nenhuma conclusão sobre o "
        "Avesso deve ser extraída deste registro.",
    ),
    "hemrath": (
        "Hemrath apresenta anatomia que lembra estrutura médica deformada, mas não há "
        "evidência de que seja criação de Hemaris. Placas rubras, válvulas naturais e bolsas "
        "se contraem sob pressão. Quando ferido, parece reorganizar o próprio dano.",
        "criatura anômala de pressão biológica e sustentação. Relação com Hemaris não "
        "estabelecida.",
    ),
    "korvann": (
        "Korvann parece ter sido montado ao redor de um princípio: nada pode cair sem que "
        "alguma coisa carregue o peso. Placas de pedra, cabos e massas de metal estão presos "
        "ao corpo em pontos semelhantes a sistemas de sustentação. Seus golpes não são "
        "rápidos; são inevitáveis.",
        "criatura anômala associada a carga, sustentação e contrapeso.",
    ),
    "vaelith": (
        "Vaelith é difícil de registrar porque dois registros honestos podem discordar. Uma "
        "testemunha descreve uma lâmina; outra descreve duas. Uma registra uma postura; outra "
        "registra uma postura incompatível. O corpo, entretanto, permanece presente.",
        "criatura anômala associada a leituras incompatíveis e fraturas locais. Isso não prova "
        "que o Avesso seja senciente nem prova viagem temporal.",
    ),
}


def bestiary_note(flagelo_id: str) -> str:
    description, knowledge = BESTIARY_TEXTS[flagelo_id]
    return f"{description}\n\nConhecimento: {knowledge}"


@dataclass(frozen=True, slots=True)
class CodexText:
    entry_id: str
    fragment_id: str
    title: str
    text: str
    order: int


GENERAL_CODEX = CodexText(
    "codex.flagelo.despertar",
    "codex.flagelo.despertar.registro",
    "O Despertar dos Flagelos",
    "Seis ocorrências anômalas surgem após atividade regional acumulada. Não são os seis "
    "Chefes de Campanha e não os substituem. A cada derrota, o ciclo regional reinicia. Ainda "
    "não existe explicação única para o fenômeno.",
    400,
)

# §16 por ``flagelo_id``: a entrada ``codex.flagelo.<id>`` (``FlageloDefinition.codex_key``).
FLAGELO_CODEX: dict[str, CodexText] = {
    "varkhenn": CodexText(
        "codex.flagelo.varkhenn",
        "codex.flagelo.varkhenn.registro",
        "Cinzas e Varkhenn",
        "Varkhenn concentra características das Terras do Ocaso: desgaste, fuligem, peso e "
        "persistência. Sua relação exata com a atividade regional permanece desconhecida.",
        401,
    ),
    "nharvek": CodexText(
        "codex.flagelo.nharvek",
        "codex.flagelo.nharvek.registro",
        "Laços e Nharvek",
        "Nharvek apresenta estruturas semelhantes à rede subterrânea dos Vales. Isso não "
        "demonstra que a Matriarca das Raízes o criou nem que faça parte da mesma rede.",
        402,
    ),
    "azharel": CodexText(
        "codex.flagelo.azharel",
        "codex.flagelo.azharel.registro",
        "Meridiano e Azharel",
        "Azharel reproduz o problema de referências que deveriam concordar e deixam de "
        "concordar. Não há evidência suficiente para concluir deslocamento temporal, duplicação "
        "física ou consciência independente.",
        403,
    ),
    "hemrath": CodexText(
        "codex.flagelo.hemrath",
        "codex.flagelo.hemrath.registro",
        "Hemaris e Hemrath",
        "Semelhança visual não estabelece origem. Hemários modernos não são experimentos vivos "
        "nem culpados coletivos pelo Projeto Hemaris.",
        404,
    ),
    "korvann": CodexText(
        "codex.flagelo.korvann",
        "codex.flagelo.korvann.registro",
        "Peso e Korvann",
        "Korvann reproduz princípios de carga, sustentação e contrapeso conhecidos dos Altos. "
        "Isso não prova que seja máquina antiga ou fabricação asteriana.",
        405,
    ),
    "vaelith": CodexText(
        "codex.flagelo.vaelith",
        "codex.flagelo.vaelith.registro",
        "Fraturas e Vaelith",
        "Vaelith demonstra que registros incompatíveis podem continuar sendo testemunhos "
        "honestos. Sua existência não prova consciência do Avesso nem viagem temporal.",
        406,
    ),
}

ALL_CODEX: tuple[CodexText, ...] = (GENERAL_CODEX, *FLAGELO_CODEX.values())
