"""Backup/restore round trip against the disposable PostgreSQL (never the game DB)."""

import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from asterion import db_backup_cli as cli

URL = os.environ.get("ASTERION_TEST_DATABASE_URL")
_NAME = os.environ.get("ASTERION_TEST_PG_CONTAINER", "asterion-test-pg")


def _container_running(name: str) -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


# Local dev: Postgres runs in the named container (docker exec).
# CI: Postgres is a service container, so use psql/pg_dump from the PATH.
CONTAINER = _NAME if URL and _container_running(_NAME) else None

pytestmark = pytest.mark.skipif(
    not URL or (CONTAINER is None and shutil.which("pg_dump") is None),
    reason="needs ASTERION_TEST_DATABASE_URL and either the test container or pg_dump",
)


def _psql(db: str, sql: str) -> str:
    url = make_url(URL)
    if CONTAINER is None:
        command = [
            "psql",
            "-h",
            url.host or "localhost",
            "-p",
            str(url.port or 5432),
            "-U",
            url.username,
            "-d",
            db,
            "-tA",
            "-c",
            sql,
        ]
    else:
        command = [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={url.password}",
            CONTAINER,
            "psql",
            "-U",
            url.username,
            "-d",
            db,
            "-tA",
            "-c",
            sql,
        ]
    result = subprocess.run(
        command,
        env={**os.environ, "PGPASSWORD": url.password or ""},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def databases():
    # Unique names: pytest-xdist runs these tests in parallel on the same server.
    suffix = uuid.uuid4().hex[:8]
    names = (f"bk_src_{suffix}", f"bk_dst_{suffix}")
    for name in names:
        _psql("postgres", f'DROP DATABASE IF EXISTS "{name}"')
        _psql("postgres", f'CREATE DATABASE "{name}"')
    yield names
    for name in names:
        _psql("postgres", f'DROP DATABASE IF EXISTS "{name}"')


def _target(db: str) -> cli.Target:
    return cli.parse_target(
        make_url(URL).set(database=db).render_as_string(hide_password=False), CONTAINER
    )


def test_backup_and_restore_round_trip(databases, tmp_path: Path):
    src, dst = databases
    _psql(src, "CREATE TABLE players (id int primary key, name text)")
    _psql(src, "INSERT INTO players VALUES (1, 'Ásh'), (2, 'Vesper')")

    dump = cli.backup(_target(src), tmp_path)
    assert dump.suffix == ".dump" and dump.stat().st_size > 0
    assert not list(tmp_path.glob("*.partial"))

    cli.restore(_target(dst), dump)
    assert _psql(dst, "SELECT id || ':' || name FROM players ORDER BY id") == "1:Ásh\n2:Vesper"


def test_restore_refuses_non_empty_target(databases, tmp_path: Path):
    src, dst = databases
    _psql(src, "CREATE TABLE t (id int)")
    dump = cli.backup(_target(src), tmp_path)
    _psql(dst, "CREATE TABLE other (id int)")

    with pytest.raises(cli.BackupError, match="já tem"):
        cli.restore(_target(dst), dump)
    with pytest.raises(cli.BackupError, match="já tem"):
        cli.restore(_target(dst), dump, clean=True)  # --clean without --yes
    cli.restore(_target(dst), dump, clean=True, yes=True)
    assert _psql(dst, "SELECT count(*) FROM t") == "0"


def test_verify_rejects_garbage(databases, tmp_path: Path):
    bad = tmp_path / "bad.dump"
    bad.write_bytes(b"not a dump")
    with pytest.raises(cli.BackupError):
        cli.verify(_target(databases[0]), bad)


def test_parse_target_requires_url(monkeypatch):
    monkeypatch.delenv("ASTERION_DATABASE_URL", raising=False)
    with pytest.raises(cli.BackupError):
        cli.parse_target(None)
    target = cli.parse_target("postgresql+asyncpg://u:p@h:5/db")
    assert target.url.drivername == "postgresql" and target.database == "db"
