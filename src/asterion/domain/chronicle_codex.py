"""Códice of Crônica I (proposal v0.2 §6, §9; GDD v1.6.0 §33.2).

Every Entry and Trecho comes from the proposal. Base texts are C0; a layer Trecho
(``_c1``, ``_c2``, ``_h``, ``_c3``, ``_c4``) is a separate Trecho registered only once
the character has the matching flag (§0.2). The two Herdeiro Trechos name NPCs of the
Altos and of the Confins, so they need a known Local of that Region.

Granted on the chapter conclusion, in the Crônica or in the Crônica Arquivada. The
desfecho Entry goes to every character with at least one chapter concluded, once the
result is published at T (author, 2026-11-09 and 2026-11-11).

Trecho titles are a draft (the proposal has none); HANDOFF.md lists them.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from asterion.domain.chronicle import CHAPTERS_BY_NUMBER, EPILOGUES, Layer, Outcome

CODEX_PREFIX = "codex_cr01_"
ALTOS = "altos"
CONFINS = "confins"
# A Region counts as known through any discovered Local with this prefix.
REGION_LOCATION_PREFIX = {ALTOS: "location.altos.", CONFINS: "location.confins."}


@dataclass(frozen=True, slots=True)
class ChronicleCodexEntry:
    entry_id: str
    title: str
    category: str
    order: int


@dataclass(frozen=True, slots=True)
class ChronicleCodexFragment:
    fragment_id: str
    entry_id: str
    title: str
    text: str
    chapter: int | None = None  # granted by this chapter's conclusion
    outcome: Outcome | None = None  # desfecho Trecho
    layer: Layer | None = None
    region: str | None = None


# Placed after the regional Entries of each category.
_ORDER = 1000

ECOS = "codex_cr01_ecos"
DESFECHO = "codex_cr01_desfecho"

ENTRIES: tuple[ChronicleCodexEntry, ...] = (
    ChronicleCodexEntry(ECOS, "Ecos da Convergência", "chronicles", _ORDER),
    ChronicleCodexEntry("codex_cr01_o_pulso", "O Pulso", "mysteries", _ORDER + 10),
    ChronicleCodexEntry(
        "codex_cr01_formas_do_pulso", "Formas do Pulso", "mysteries", _ORDER + 11
    ),
    ChronicleCodexEntry(
        "codex_cr01_marcas_que_vibram", "Marcas que Vibram", "regions", _ORDER + 20
    ),
    ChronicleCodexEntry(
        "codex_cr01_ordem_do_pulso", "A Ordem do Pulso", "mysteries", _ORDER + 30
    ),
    ChronicleCodexEntry(
        "codex_cr01_direcao_do_pulso", "A Direção do Pulso", "mysteries", _ORDER + 40
    ),
    ChronicleCodexEntry(
        "codex_cr01_sinal_de_confirmacao", "Sinal de Confirmação", "history", _ORDER + 50
    ),
    ChronicleCodexEntry("codex_cr01_ordem_sem_data", "A Ordem sem Data", "history", _ORDER + 60),
    ChronicleCodexEntry("codex_cr01_herdeiros", "Os Herdeiros", "peoples", _ORDER + 61),
    ChronicleCodexEntry(
        "codex_cr01_sequencia_pendente", "A Sequência Pendente", "chronicles", _ORDER + 70
    ),
    ChronicleCodexEntry(
        "codex_cr01_quatro_respostas", "As Quatro Respostas", "chronicles", _ORDER + 80
    ),
    ChronicleCodexEntry(DESFECHO, "O Que Foi Respondido", "chronicles", _ORDER + 90),
)
ENTRIES_BY_ID = {entry.entry_id: entry for entry in ENTRIES}

# §6.1: one Trecho of the continuous Entry per chapter conclusion.
_ECOS_TEXTS = (
    "No primeiro dia, estruturas antigas pulsaram ao mesmo tempo em todas as Regiões. Os "
    "registradores chamaram o fenômeno de Eco, por falta de nome melhor.",
    "O pulso volta em intervalos, e não chega a todas as Regiões no mesmo momento.",
    "Comparando horários, os registradores encontraram uma ordem de chegada.",
    "O pulso tem direção: vem de muito além das Planícies.",
    'Registros antigos chamam o pulso de "sinal de confirmação". Os registradores passaram '
    "a chamá-lo de a Sequência.",
    "Uma ordem sem data repete-se a cada pulso, pedindo confirmação. As Leituras foram "
    "reunidas.",
    "A Sequência Pendente está completa nos registros: uma última etapa que nunca recebeu "
    "resposta.",
    "Quatro respostas foram apresentadas ao mundo: Selar, Estabilizar, Entregar aos "
    "Herdeiros, Destruir.",
)


def _ecos(chapter: int, text: str) -> ChronicleCodexFragment:
    title = f"Capítulo {chapter} · {CHAPTERS_BY_NUMBER[chapter].title}"
    return ChronicleCodexFragment(f"{ECOS}_t{chapter:02d}", ECOS, title, text, chapter=chapter)


def _base(entry_id: str, chapter: int, text: str) -> ChronicleCodexFragment:
    return ChronicleCodexFragment(
        f"{entry_id}_texto", entry_id, ENTRIES_BY_ID[entry_id].title, text, chapter=chapter
    )


def _extra(
    entry_id: str,
    suffix: str,
    chapter: int,
    title: str,
    text: str,
    *,
    layer: Layer | None = None,
    region: str | None = None,
) -> ChronicleCodexFragment:
    return ChronicleCodexFragment(
        f"{entry_id}_{suffix}", entry_id, title, text, chapter=chapter, layer=layer, region=region
    )


# §6.2: Entries by chapter, base Trecho plus layer or Region Trechos.
_CHAPTER_FRAGMENTS: tuple[ChronicleCodexFragment, ...] = (
    _base(
        "codex_cr01_o_pulso",
        1,
        "Um tremor seco na pedra antiga, sem desabamento nem fogo. Dura um instante. "
        "Braseiros não reagem.",
    ),
    _extra(
        "codex_cr01_o_pulso",
        "c1",
        1,
        "Perto da Âncora",
        "Em Ocaso, o pulso é mais forte perto da Âncora do Poente.",
        layer=Layer.C1,
    ),
    _base(
        "codex_cr01_formas_do_pulso",
        1,
        "Durante o pulso, a matéria do lugar se ergue em formas que repetem gestos de gente "
        "que não está ali. Não falam, não sangram e se desfazem quando derrotadas. Ninguém "
        "sabe o que são.",
    ),
    _extra(
        "codex_cr01_formas_do_pulso",
        "c4",
        1,
        "Estados guardados",
        "Talvez sejam estados que a Sequência ainda guarda, e não criaturas. O Códice não "
        "confirma.",
        layer=Layer.C4,
    ),
    _base(
        "codex_cr01_marcas_que_vibram",
        2,
        "No Ocaso, marcas e inscrições vibram a cada pulso, e os Vigias das Ruínas mudam de "
        "rota até o pulso passar.",
    ),
    _base(
        "codex_cr01_ordem_do_pulso",
        3,
        "O pulso chega às Regiões em sequência, sempre na mesma ordem. Nos Vales, as raízes "
        "se contraem a cada batida.",
    ),
    _base(
        "codex_cr01_direcao_do_pulso",
        4,
        "Durante o pulso, marcos de Nareth apontam para o mesmo lado. Talen Orm publicou a "
        "medição com o próprio nome.",
    ),
    _extra(
        "codex_cr01_direcao_do_pulso",
        "c2",
        4,
        "Referências sem resposta",
        "O desvio lembra a comparação de referências que as Âncoras faziam, sem resposta do "
        "outro lado.",
        layer=Layer.C2,
    ),
    _base(
        "codex_cr01_sinal_de_confirmacao",
        5,
        "Registros de manutenção das Várzeas descrevem o pulso como um sinal que pede "
        "confirmação.",
    ),
    _extra(
        "codex_cr01_sinal_de_confirmacao",
        "h",
        5,
        "Protocolos em espera",
        "Protocolos das instalações Hemaris reagem ao pulso como se aguardassem instrução "
        "externa.",
        layer=Layer.H,
    ),
    _base(
        "codex_cr01_ordem_sem_data",
        6,
        "Uma ordem antiga repete-se a cada pulso. Não tem data nem autor, e pede uma "
        "confirmação que ninguém sabe dar.",
    ),
    _extra(
        "codex_cr01_ordem_sem_data",
        "c3",
        6,
        "A noite da Ruptura",
        "A ordem pertence à Convergência, interrompida na noite da Ruptura.",
        layer=Layer.C3,
    ),
    _base(
        "codex_cr01_herdeiros",
        6,
        "Estudiosos que guardam e comparam registros antigos. Pediram que as Leituras de "
        "todas as Regiões fossem reunidas.",
    ),
    _extra(
        "codex_cr01_herdeiros",
        ALTOS,
        6,
        "Maro Keln",
        "Maro Keln é um deles.",
        region=ALTOS,
    ),
    _extra(
        "codex_cr01_herdeiros",
        CONFINS,
        6,
        "Eris Val",
        "Eris Val também.",
        region=CONFINS,
    ),
    _base(
        "codex_cr01_sequencia_pendente",
        7,
        "Reunidas, as Leituras formam uma sequência antiga que tenta completar sua última "
        "etapa, e nunca consegue.",
    ),
    _extra(
        "codex_cr01_sequencia_pendente",
        "c3",
        7,
        "A etapa final",
        "É a etapa final da Convergência.",
        layer=Layer.C3,
    ),
    _extra(
        "codex_cr01_sequencia_pendente",
        "c4",
        7,
        "A origem do pedido",
        "O pedido parte do Nó Central e nunca foi confirmado.",
        layer=Layer.C4,
    ),
    _base(
        "codex_cr01_quatro_respostas",
        8,
        "Selar, Estabilizar, Entregar aos Herdeiros ou Destruir. Nenhuma cura o mundo; "
        "todas custam algo.",
    ),
)

# §4 epilogue complements, the layer Trechos of the desfecho Entry.
EPILOGUE_COMPLEMENTS: dict[Outcome, tuple[Layer, str]] = {
    Outcome.SELAR: (
        Layer.C3,
        "A etapa pendente continua intacta e inerte, à espera de uma confirmação que agora "
        "ninguém pode dar. O Véu continua tão frágil quanto antes.",
    ),
    Outcome.ESTABILIZAR: (
        Layer.C3,
        "A Sequência segue rodando em modo local e nunca chega à última etapa. É o mesmo "
        "pacto das Âncoras: tempo comprado, dependência criada.",
    ),
    Outcome.HERDEIROS: (
        Layer.C3,
        "O Arquivo Comum dos antigos fazia isso: integrava registros para muitos. A Regência "
        "também guardou o essencial para poucos.",
    ),
    Outcome.DESTRUIR: (
        Layer.C4,
        "A Âncora Central não volta a receber pedido algum desta Sequência. O Véu continua "
        "deteriorando como sempre; o Avesso continua existindo. Destruir não é reparar.",
    ),
    Outcome.EM_ESPERA: (
        Layer.C3,
        "Como tantos protocolos antigos, a última etapa da Convergência voltou a aguardar uma "
        "autorização que talvez nunca venha.",
    ),
}
OUTCOME_TITLES: dict[Outcome, str] = {
    Outcome.SELAR: "Selar",
    Outcome.ESTABILIZAR: "Estabilizar",
    Outcome.HERDEIROS: "Entregar aos Herdeiros",
    Outcome.DESTRUIR: "Destruir",
    Outcome.EM_ESPERA: "Em Espera",
}


def _desfecho_fragments() -> tuple[ChronicleCodexFragment, ...]:
    result = []
    for outcome, epilogue in EPILOGUES.items():
        result.append(
            ChronicleCodexFragment(
                f"{DESFECHO}_{outcome.value}",
                DESFECHO,
                OUTCOME_TITLES[outcome],
                epilogue,
                outcome=outcome,
            )
        )
        layer, text = EPILOGUE_COMPLEMENTS[outcome]
        result.append(
            ChronicleCodexFragment(
                f"{DESFECHO}_{outcome.value}_{layer.value}",
                DESFECHO,
                "Além do registro",
                text,
                outcome=outcome,
                layer=layer,
            )
        )
    return tuple(result)


FRAGMENTS: tuple[ChronicleCodexFragment, ...] = (
    *(_ecos(number, text) for number, text in enumerate(_ECOS_TEXTS, 1)),
    *_CHAPTER_FRAGMENTS,
    *_desfecho_fragments(),
)
FRAGMENTS_BY_ID = {item.fragment_id: item for item in FRAGMENTS}


def allowed_fragments(
    chapters_concluded: Iterable[int],
    layers: frozenset[Layer],
    known_regions: frozenset[str],
    outcome: Outcome | None,
) -> tuple[ChronicleCodexFragment, ...]:
    """Every Trecho this character may hold now. Registering is idempotent."""
    chapters = set(chapters_concluded)
    result = []
    for item in FRAGMENTS:
        if item.outcome is not None:
            if not chapters or item.outcome != outcome:
                continue
        elif item.chapter not in chapters:
            continue
        if item.layer is not None and item.layer not in layers:
            continue
        if item.region is not None and item.region not in known_regions:
            continue
        result.append(item)
    return tuple(result)
