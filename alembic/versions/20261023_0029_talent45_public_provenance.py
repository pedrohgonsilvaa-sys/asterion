"""Quarantine pre-release Nv.45 Talent choices and frozen snapshots.

Revision ID: 20261023_0029
Revises: 20261023_0028
"""

import sqlalchemy as sa

from alembic import op

revision = "20261023_0029"
down_revision = "20261023_0028"
branch_labels = None
depends_on = None


_TIER_45_IDS = (
    "talent.sentinela.ponta_penetrante",
    "talent.sentinela.postura_de_ferro",
    "talent.sentinela.vigilia",
    "talent.errante.fio_perfurante",
    "talent.errante.pele_endurecida",
    "talent.errante.ritmo_predatorio",
    "talent.vigia.ponto_fraco",
    "talent.vigia.couro_de_campo",
    "talent.vigia.leitura_de_movimento",
    "talent.tecelao.ruptura_profunda",
    "talent.tecelao.tecelagem_defensiva",
    "talent.tecelao.eco_de_alternancia",
    "talent.oraculo.fraqueza_prevista",
    "talent.oraculo.mente_velada",
    "talent.oraculo.sequencia_profetica",
    "talent.luminar.punicao_da_fraqueza",
    "talent.luminar.luz_protetora",
    "talent.luminar.fluxo_restaurador",
)


def _sql_ids() -> str:
    return ", ".join("'" + talent_id + "'" for talent_id in _TIER_45_IDS)


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
    # Rows created while the tier was closed are not acquisitions. Preserve
    # lower-tier choices and only quarantine these 18 canonical Nv.45 IDs.
    op.execute(
        sa.text(
            "UPDATE character_talent_choices SET publicly_acquired = false "
            "WHERE talent_id = ANY(ARRAY[" + _sql_ids() + "]::text[])"
        )
    )

    ids = _sql_ids()
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION pg_temp._c2_strip_unreleased_talent45(value jsonb)
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
                            pg_temp._c2_strip_unreleased_talent45(item)
                        );
                    END LOOP;
                    RETURN result;
                ELSIF jsonb_typeof(value) = 'object' THEN
                    result := '{}'::jsonb;
                    FOR property_name, item IN
                        SELECT key, val FROM jsonb_each(value) AS e(key, val) LOOP
                        result := result || jsonb_build_object(
                            property_name,
                            pg_temp._c2_strip_unreleased_talent45(item)
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
            f"{column}::text LIKE '%{talent_id}%'" for talent_id in _TIER_45_IDS
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = "
                f"pg_temp._c2_strip_unreleased_talent45({column}) "
                f"WHERE {column} IS NOT NULL AND ({matches})"
            )
        )
    op.execute(sa.text("DROP FUNCTION pg_temp._c2_strip_unreleased_talent45(jsonb)"))


def downgrade() -> None:
    # The data cleanup is intentionally irreversible: restoring pre-release
    # talent IDs would make frozen configurations valid after a downgrade.
    pass
