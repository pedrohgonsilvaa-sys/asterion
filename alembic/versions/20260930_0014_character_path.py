"""Persist the selected character Path."""

import sqlalchemy as sa

from alembic import op

revision = "20260930_0014"
down_revision = "20260929_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("selected_path", sa.String(length=24)))
    op.create_check_constraint(
        "ck_character_selected_path",
        "characters",
        "selected_path IS NULL OR selected_path IN ('bastiao','devastador','carrasco',"
        "'sabotador','atirador','rastreador','conjurador','runico','agoureiro',"
        "'invocador','guardiao','inquisidor')",
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("LOCK TABLE characters IN SHARE ROW EXCLUSIVE MODE")
    has_selected_path = bind.scalar(
        sa.text("SELECT EXISTS (SELECT 1 FROM characters WHERE selected_path IS NOT NULL)")
    )
    if has_selected_path:
        raise RuntimeError("Cannot downgrade while characters have a selected Path")
    op.drop_constraint("ck_character_selected_path", "characters", type_="check")
    op.drop_column("characters", "selected_path")
