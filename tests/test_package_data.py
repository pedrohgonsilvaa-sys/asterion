import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROLOGUE_CATALOG = "asterion/domain/narrative_choices_prologue_catalog.json"


def test_prologue_catalog_is_packaged_in_wheel(tmp_path):
    # Regressão: o JSON existia no repositório mas não entrava no wheel,
    # então o /start quebrava em produção com FileNotFoundError.
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(REPO_ROOT), "--no-deps", "-w", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stderr[-2000:]

    wheels = list(tmp_path.glob("asterion-*.whl"))
    assert len(wheels) == 1, f"esperado 1 wheel, achei {wheels}"

    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())

    assert PROLOGUE_CATALOG in names, (
        f"{PROLOGUE_CATALOG} ausente do wheel; confira package-data no pyproject.toml"
    )
