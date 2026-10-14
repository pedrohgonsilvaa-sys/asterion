from pathlib import Path


def test_operational_source_authority_copy_matches_repository_root():
    repository_root = Path(__file__).resolve().parents[1]
    root_copy = (repository_root / "SOURCE_AUTHORITY.md").read_bytes()
    documentation_copy = (repository_root / "docs" / "SOURCE_AUTHORITY.md").read_bytes()

    assert documentation_copy == root_copy
