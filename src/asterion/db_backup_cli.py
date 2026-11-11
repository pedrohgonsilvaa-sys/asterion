"""Operator CLI: backup and restore of the game PostgreSQL (pg_dump / pg_restore).

Usage:
    python -m asterion.db_backup_cli backup  [--out-dir backups] [--docker-container NAME]
    python -m asterion.db_backup_cli restore FILE [--clean --yes] [--docker-container NAME]
    python -m asterion.db_backup_cli verify  FILE [--docker-container NAME]

The connection comes from --database-url or the ASTERION_DATABASE_URL environment
variable (``postgresql+asyncpg://`` is accepted). This tool never reads ``.env``.

Without --docker-container the tool runs pg_dump/pg_restore/psql from the PATH.
With --docker-container the same tools run inside that container (``docker exec``),
so the host does not need the PostgreSQL client installed.

restore refuses a target database that already has tables. To overwrite it, pass
--clean and --yes together: objects in the dump are dropped and recreated.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import URL, make_url


class BackupError(RuntimeError):
    """Operational failure (bad URL, tool missing, non-empty target, tool error)."""


@dataclass(frozen=True)
class Target:
    url: URL
    docker_container: str | None = None

    @property
    def database(self) -> str:
        if not self.url.database:
            raise BackupError("a URL do banco não tem nome de banco")
        return self.url.database

    def connection_args(self) -> list[str]:
        # Inside the container the server is reached by its local socket.
        args: list[str] = []
        if self.docker_container is None:
            args += ["-h", self.url.host or "localhost"]
            if self.url.port:
                args += ["-p", str(self.url.port)]
        if self.url.username:
            args += ["-U", self.url.username]
        return args + ["-d", self.database]

    def command(
        self, tool: str, *args: str, stdin: bool = False, connect: bool = True
    ) -> list[str]:
        full = [tool, *(self.connection_args() if connect else []), *args]
        if self.docker_container is None:
            return full
        prefix = ["docker", "exec"]
        if stdin:
            prefix.append("-i")
        if self.url.password:
            prefix += ["-e", "PGPASSWORD"]
        return [*prefix, self.docker_container, *full]

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.url.password:
            env["PGPASSWORD"] = self.url.password
        return env


def parse_target(database_url: str | None, docker_container: str | None = None) -> Target:
    raw = database_url or os.environ.get("ASTERION_DATABASE_URL")
    if not raw:
        raise BackupError("informe --database-url ou defina ASTERION_DATABASE_URL")
    url = make_url(raw)
    if not url.drivername.startswith("postgresql"):
        raise BackupError("a URL precisa ser de PostgreSQL")
    return Target(url=url.set(drivername="postgresql"), docker_container=docker_container)


def _run(command: list[str], env: dict[str, str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, env=env, check=False, **kwargs)
    except FileNotFoundError as exc:
        raise BackupError(
            f"ferramenta não encontrada: {command[0]} (use --docker-container ou instale o "
            "cliente PostgreSQL)"
        ) from exc


def _stderr(result: subprocess.CompletedProcess) -> str:
    raw = result.stderr or b""
    return raw.decode("utf-8", "replace").strip()


def backup(target: Target, out_dir: Path, *, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{target.database}-{stamp}.dump"
    partial = final.with_suffix(".dump.partial")
    command = target.command("pg_dump", "-Fc", "--no-owner", "--no-acl")
    try:
        with partial.open("wb") as handle:
            result = _run(command, target.env(), stdout=handle, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise BackupError(f"pg_dump falhou: {_stderr(result)}")
        verify(target, partial)
        partial.replace(final)
    finally:
        partial.unlink(missing_ok=True)
    return final


def verify(target: Target, dump: Path) -> int:
    """Return the number of entries in the dump; raise if it is unreadable."""
    if not dump.is_file() or dump.stat().st_size == 0:
        raise BackupError(f"arquivo de backup ausente ou vazio: {dump}")
    # pg_restore --list reads the archive only; it needs no database connection.
    if target.docker_container is None:
        command = target.command("pg_restore", "--list", str(dump), connect=False)
        result = _run(command, target.env(), capture_output=True)
    else:
        command = target.command("pg_restore", "--list", stdin=True, connect=False)
        with dump.open("rb") as handle:
            result = _run(command, target.env(), stdin=handle, capture_output=True)
    if result.returncode != 0:
        raise BackupError(f"backup ilegível: {_stderr(result)}")
    lines = result.stdout.decode("utf-8", "replace").splitlines()
    return sum(1 for line in lines if line and not line.startswith(";"))


def table_count(target: Target) -> int:
    query = (
        "select count(*) from information_schema.tables "
        "where table_schema not in ('pg_catalog', 'information_schema')"
    )
    result = _run(target.command("psql", "-tA", "-c", query), target.env(), capture_output=True)
    if result.returncode != 0:
        raise BackupError(f"não foi possível consultar o banco de destino: {_stderr(result)}")
    return int(result.stdout.decode().strip() or 0)


def restore(target: Target, dump: Path, *, clean: bool = False, yes: bool = False) -> None:
    verify(target, dump)
    existing = table_count(target)
    if existing and not (clean and yes):
        raise BackupError(
            f"o banco '{target.database}' já tem {existing} tabela(s). Para sobrescrever, "
            "use --clean --yes. Restaure de preferência em um banco vazio."
        )
    args = ["--no-owner", "--no-acl", "--exit-on-error"]
    if clean:
        args += ["--clean", "--if-exists"]
    if target.docker_container is None:
        command = target.command("pg_restore", *args, str(dump))
        result = _run(command, target.env(), capture_output=True)
    else:
        command = target.command("pg_restore", *args, stdin=True)
        with dump.open("rb") as handle:
            result = _run(command, target.env(), stdin=handle, capture_output=True)
    if result.returncode != 0:
        raise BackupError(f"pg_restore falhou: {_stderr(result)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="asterion.db_backup_cli")
    parser.add_argument("--database-url", help="default: variável ASTERION_DATABASE_URL")
    parser.add_argument("--docker-container", help="rodar as ferramentas dentro deste container")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup", help="gerar um dump .dump do banco")
    b.add_argument("--out-dir", type=Path, default=Path("backups"))
    r = sub.add_parser("restore", help="restaurar um dump num banco (vazio por padrão)")
    r.add_argument("file", type=Path)
    r.add_argument("--clean", action="store_true", help="apagar objetos existentes antes")
    r.add_argument("--yes", action="store_true", help="confirma o --clean")
    v = sub.add_parser("verify", help="conferir se o dump é legível")
    v.add_argument("file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        target = parse_target(args.database_url, args.docker_container)
        if args.command == "backup":
            print(f"backup gravado: {backup(target, args.out_dir)}")
        elif args.command == "verify":
            print(f"dump legível: {verify(target, args.file)} entradas")
        else:
            restore(target, args.file, clean=args.clean, yes=args.yes)
            print(f"restore concluído em '{target.database}'")
    except BackupError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
