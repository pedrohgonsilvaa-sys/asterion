from pathlib import Path


def test_p1_migration_declares_safe_legacy_conversion_and_constraints():
    migration = Path("alembic/versions/20260921_0005_p1_voices.py").read_text(encoding="utf-8")
    assert "content_version <> 'tdo-1.0.1'" in migration
    assert "Cannot migrate incompatible P1 state" in migration
    assert "ck_quest_state_version" in migration
    assert "uq_character_codex" in migration
