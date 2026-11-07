"""Quarantine pre-release Nv.35 Talent choices and frozen snapshots.

Revision ID: 20261023_0028
Revises: 20261010_0027
"""

import sqlalchemy as sa

from alembic import op

revision = "20261023_0028"
down_revision = "20261010_0027"
branch_labels = None
depends_on = None


_TIER_35_IDS = (
    "talent.sentinela.olho_de_combate",
    "talent.sentinela.barreira_densa",
    "talent.sentinela.contrapeso",
    "talent.errante.oportunismo_ampliado",
    "talent.errante.sobrevivencia",
    "talent.errante.desvio_ofensivo",
    "talent.vigia.alvo_exposto",
    "talent.vigia.recuo_instintivo",
    "talent.vigia.visao_persistente",
    "talent.tecelao.trama_agressiva",
    "talent.tecelao.reforco_do_veu",
    "talent.tecelao.fio_persistente",
    "talent.oraculo.profecia_dolorosa",
    "talent.oraculo.destino_adiado",
    "talent.oraculo.pressagio_flexivel",
    "talent.luminar.veredito_ardente",
    "talent.luminar.cura_prudente",
    "talent.luminar.ciclo_luminoso",
)


def _sql_ids() -> str:
    return ", ".join("'" + talent_id + "'" for talent_id in _TIER_35_IDS)


def _snapshot_columns() -> tuple[tuple[str, str], ...]:
    return (
        ("character_doctrines", "configuration"),
        ("group_activity_proposals", "context_payload"),
        ("group_activity_participants", "eligibility_snapshot"),
        ("combats", "snapshot"),
        ("campaign_shared_encounters", "combat_snapshot"),
        ("dungeon_run_members", "combat_configuration"),
        ("group_hunt_encounters", "combat_snapshot"),
        ("pvpve_collisions", "combat_snapshot"),
        ("hunt_rounds", "config_snapshot"),
        ("hunt_round_encounters", "combat_snapshot"),
    )


def upgrade() -> None:
    op.add_column(
        "character_talent_choices",
        sa.Column(
            "publicly_acquired",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE character_talent_choices SET publicly_acquired = false "
            "WHERE talent_id = ANY(ARRAY[" + _sql_ids() + "]::text[])"
        )
    )

    # A release cannot turn a pre-release persisted ID or frozen combat config into
    # an acquisition. Remove only those 18 IDs from stored JSON structures.
    ids = _sql_ids()
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION pg_temp._c1_strip_unreleased_talent35(value jsonb)
            RETURNS jsonb LANGUAGE plpgsql IMMUTABLE AS $$
            DECLARE
                result jsonb;
                item jsonb;
                property_name text;
            BEGIN
                IF jsonb_typeof(value) = 'object'
                   AND value->>'talent_id' = ANY(ARRAY["""
            + ids
            + """ ]::text[]) THEN
                    RETURN 'null'::jsonb;
                ELSIF jsonb_typeof(value) = 'array' THEN
                    result := '[]'::jsonb;
                    FOR item IN SELECT jsonb_array_elements(value) LOOP
                        IF jsonb_typeof(item) = 'string'
                           AND (item #>> '{}') = ANY(ARRAY["""
            + ids
            + """ ]::text[]) THEN
                            CONTINUE;
                        END IF;
                        IF jsonb_typeof(item) = 'object'
                           AND item->>'talent_id' = ANY(ARRAY["""
            + ids
            + """ ]::text[]) THEN
                            CONTINUE;
                        END IF;
                        result := result || jsonb_build_array(
                            pg_temp._c1_strip_unreleased_talent35(item)
                        );
                    END LOOP;
                    RETURN result;
                ELSIF jsonb_typeof(value) = 'object' THEN
                    result := '{}'::jsonb;
                    FOR property_name, item IN
                        SELECT key, val FROM jsonb_each(value) AS e(key, val)
                    LOOP
                        result := result || jsonb_build_object(
                            property_name,
                            pg_temp._c1_strip_unreleased_talent35(item)
                        );
                    END LOOP;
                    RETURN result;
                END IF;
                RETURN value;
            END;
            $$
            """
        )
    )
    for table, column in _snapshot_columns():
        matches = " OR ".join(
            f"{column}::text LIKE '%{talent_id}%'" for talent_id in _TIER_35_IDS
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = "
                f"pg_temp._c1_strip_unreleased_talent35({column}) "
                f"WHERE {column} IS NOT NULL AND ({matches})"
            )
        )
    op.execute(sa.text("DROP FUNCTION pg_temp._c1_strip_unreleased_talent35(jsonb)"))


def downgrade() -> None:
    op.drop_column("character_talent_choices", "publicly_acquired")
