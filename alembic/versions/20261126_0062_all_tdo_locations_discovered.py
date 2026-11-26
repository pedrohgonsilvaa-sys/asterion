"""Terras do Ocaso: todos os Locais passam a nascer descobertos (decisão do autor).

Personagens que já passaram do Prólogo (Estrada descoberta) recebem a descoberta de
Charneca, Bosque, Ruínas e Câmara do Poente, e o registro da Câmara no Códice, sem XP.
Os novos recebem o mesmo ao fim do Prólogo. Idempotente.

Revision ID: 20261126_0062
Revises: 20261126_0061
Create Date: 2026-11-26 00:00:01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261126_0062"
down_revision: str | None = "20261126_0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOCATIONS = (
    "tdo.location.charneca_da_fuligem",
    "tdo.location.bosque_calcinado",
    "tdo.location.ruinas_do_vigia",
    "tdo.location.camara_do_poente",
)


def upgrade() -> None:
    for location_id in LOCATIONS:
        op.execute(
            f"""
            INSERT INTO location_discoveries (id, character_id, location_id)
            SELECT gen_random_uuid(), d.character_id, '{location_id}'
            FROM location_discoveries d
            WHERE d.location_id = 'tdo.location.estrada_das_cinzas'
            ON CONFLICT (character_id, location_id) DO NOTHING
            """
        )
    op.execute(
        """
        INSERT INTO codex_entries (id, character_id, entry_id)
        SELECT gen_random_uuid(), d.character_id, 'codex.location.camara_do_poente'
        FROM location_discoveries d
        WHERE d.location_id = 'tdo.location.estrada_das_cinzas'
        ON CONFLICT (character_id, entry_id) DO NOTHING
        """
    )


def downgrade() -> None:
    # Volta à regra anterior (Locais revelados por Explorar). Não há como separar as
    # descobertas gravadas aqui das obtidas por Explorar antes desta revisão; com todos
    # os Locais descobertos pela regra nova, o upgrade as recria.
    op.execute(
        "DELETE FROM codex_entries WHERE entry_id = 'codex.location.camara_do_poente'"
    )
    op.execute(
        "DELETE FROM location_discoveries WHERE location_id IN ("
        + ", ".join(f"'{location_id}'" for location_id in LOCATIONS)
        + ")"
    )
