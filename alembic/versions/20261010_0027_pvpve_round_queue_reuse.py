"""Allow successive PvPvE queue attempts for a persistent Ronda activity.

Revision ID: 20261010_0027
Revises: 20261009_0026
"""

import sqlalchemy as sa

from alembic import op

revision = "20261010_0027"
down_revision = "20261009_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_pvpve_queue_activity", "pvpve_queue_members", type_="unique"
    )
    op.create_index(
        "ix_pvpve_queue_member_activity",
        "pvpve_queue_members",
        ["game_activity_id", "character_id"],
    )


def downgrade() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            "SELECT game_activity_id FROM pvpve_queue_members "
            "GROUP BY game_activity_id HAVING count(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot restore uq_pvpve_queue_activity: a GameActivity has multiple "
            "historical PvPvE queue attempts. Preserve the newer schema or resolve "
            "those rows explicitly before downgrading."
        )
    op.drop_index(
        "ix_pvpve_queue_member_activity", table_name="pvpve_queue_members"
    )
    op.create_unique_constraint(
        "uq_pvpve_queue_activity",
        "pvpve_queue_members",
        ["game_activity_id"],
    )
