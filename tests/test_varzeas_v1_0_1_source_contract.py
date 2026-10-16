import re
from pathlib import Path

BARRIER_PAIRS = (
    (
        "Casca de Suporte · Barreira `90% ATQ`, CD3.",
        "Casca de Suporte · Barreira `90% ATQ` por `2T`, CD3.",
    ),
    (
        "Placa Lavável · Barreira `95% ATQ`, CD3.",
        "Placa Lavável · Barreira `95% ATQ` por `2T`, CD3.",
    ),
    (
        "Reservatório Blindado · Barreira `100% ATQ`, CD3.",
        "Reservatório Blindado · Barreira `100% ATQ` por `2T`, CD3.",
    ),
    (
        "Placa de Procedimento · Barreira `100% ATQ`, CD3.",
        "Placa de Procedimento · Barreira `100% ATQ` por `2T`, CD3.",
    ),
    (
        "Linha Pressurizada · Barreira `95% ATQ`, CD3.",
        "Linha Pressurizada · Barreira `95% ATQ` por `2T`, CD3.",
    ),
    (
        "Membrana de Contenção** · Barreira `8% HP Máximo`, CD4.",
        "Membrana de Contenção** · Barreira `8% HP Máximo` por `2T`, CD4.",
    ),
)


def test_varzeas_source_revision_only_closes_six_barrier_durations():
    root = Path(__file__).resolve().parents[1]
    previous = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.0_FINAL.md").read_text(
        encoding="utf-8"
    )
    current = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.1_FINAL.md").read_text(
        encoding="utf-8"
    )

    normalized = re.sub(r"\\(?=\n)", "  ", current)
    normalized = normalized.replace(
        "## Várzeas Carmesins · v1.0.1 FINAL",
        "## Várzeas Carmesins · v1.0.0 FINAL",
    ).replace(
        "**Revisão v1.0.1:** fechamento explícito em `2T` das seis durações de "
        "Barreira inimiga listadas nesta revisão; nenhum outro conteúdo regional foi alterado.  \n",
        "",
    )
    for old_line, new_line in BARRIER_PAIRS:
        assert previous.count(old_line) == 1
        assert current.count(new_line) == 1
        normalized = normalized.replace(new_line, old_line)
    assert normalized == previous


def test_varzeas_source_authority_is_current_and_has_no_global_barrier_default():
    root = Path(__file__).resolve().parents[1]
    authority = (root / "SOURCE_AUTHORITY.md").read_text(encoding="utf-8")
    mirror = (root / "docs" / "SOURCE_AUTHORITY.md").read_bytes()

    assert mirror == (root / "SOURCE_AUTHORITY.md").read_bytes()
    assert "**Várzeas Carmesins v1.0.3 FINAL**" in authority
    assert "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.3_FINAL.md" in authority
    assert "**Índice atualizado:** 2026-10-15." in authority
    assert "Várzeas Carmesins v1.0.0 FINAL" not in authority
    assert "A v1.0.3 sucede a v1.0.2 exclusivamente" in authority
    assert "não cria default ou sistema universal" in authority


def test_varzeas_v1_0_2_only_adds_persistente_barrier_duration():
    root = Path(__file__).resolve().parents[1]
    previous = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.1_FINAL.md").read_text(
        encoding="utf-8"
    )
    current = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.2_FINAL.md").read_text(
        encoding="utf-8"
    )
    old_line = "- Protocolo de Continuidade · Barreira igual a `8% HP Máximo`, CD4."
    new_line = "- Protocolo de Continuidade · Barreira igual a `8% HP Máximo` por `2T`, CD4."
    assert previous.count(old_line) == 1
    assert current.count(new_line) == 1
    normalized = current.replace(new_line, old_line)
    normalized = normalized.replace("v1.0.2 FINAL", "v1.0.1 FINAL", 1)
    normalized = normalized.replace("2026-10-15", "2026-10-12", 1)
    normalized = normalized.replace(
        (
            "**Revisão v1.0.2:** preserva as seis durações de Barreira fechadas em `2T` "
            "pela v1.0.1 e acrescenta exclusivamente a duração explícita de `2T` ao "
            "Protocolo de Continuidade.\\"
        ),
        (
            "**Revisão v1.0.1:** fechamento explícito em `2T` das seis durações de "
            "Barreira inimiga listadas nesta revisão; nenhum outro conteúdo regional foi "
            "alterado.\\"
        ),
        1,
    )
    normalized = normalized.replace(
        "**Várzeas Carmesins v1.0.2 FINAL** estabelece",
        "**Várzeas Carmesins v1.0.0 FINAL** estabelece",
        1,
    )
    assert normalized == previous
    authority = (root / "SOURCE_AUTHORITY.md").read_text(encoding="utf-8")
    assert "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.3_FINAL.md" in authority
    assert "A v1.0.3 sucede a v1.0.2 exclusivamente" in authority
    assert "Preserva todas as durações regionais de Barreira em `2T`" in authority


def test_varzeas_v1_0_2_publishes_all_seven_barrier_durations_explicitly():
    root = Path(__file__).resolve().parents[1]
    source = (root / "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.2_FINAL.md").read_text(
        encoding="utf-8"
    )
    explicit_durations = (
        r"- Casca de Suporte · Barreira `90% ATQ` por `2T`, CD3\.",
        r"- Placa Lavável · Barreira `95% ATQ` por `2T`, CD3\.",
        r"- Reservatório Blindado · Barreira `100% ATQ` por `2T`, CD3\.",
        r"- Placa de Procedimento · Barreira `100% ATQ` por `2T`, CD3\.",
        r"- Protocolo de Continuidade · Barreira igual a `8% HP Máximo` por `2T`, CD4\.",
        r"- Linha Pressurizada · Barreira `95% ATQ` por `2T`, CD3\.",
        r"- \*\*Membrana de Contenção\*\* · Barreira `8% HP Máximo` por `2T`, CD4\.",
    )
    for pattern in explicit_durations:
        assert len(re.findall(pattern, source)) == 1
    assert "toda Barreira" not in source
    assert "qualquer Barreira" not in source
