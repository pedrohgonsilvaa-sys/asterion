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
    assert "**Várzeas Carmesins v1.0.1 FINAL**" in authority
    assert "ASTERION_CONTEUDO_VARZEAS_CARMESINS_v1.0.1_FINAL.md" in authority
    assert "**Índice atualizado:** 2026-10-15." in authority
    assert "Várzeas Carmesins v1.0.0 FINAL" not in authority
    assert "Várzeas v1.0.1" in authority
    assert "Não cria regra universal de duração de Barreira." in authority
