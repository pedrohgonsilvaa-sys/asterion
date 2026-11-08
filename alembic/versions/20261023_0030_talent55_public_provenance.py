"""Quarantine pre-release Nv.55 Talent choices and frozen snapshots.

Revision ID: 20261023_0030
Revises: 20261023_0029
"""

import sqlalchemy as sa

from alembic import op

revision = "20261023_0030"
down_revision = "20261023_0029"
branch_labels = None
depends_on = None


_TIER_55_IDS = (
    "talent.sentinela.punicao_final",
    "talent.sentinela.persistencia",
    "talent.sentinela.guarda_integra",
    "talent.errante.fim_proximo",
    "talent.errante.primeiro_desvio",
    "talent.errante.instinto_de_fuga",
    "talent.vigia.disparo_implacavel",
    "talent.vigia.ultimo_horizonte",
    "talent.vigia.cacada_metodica",
    "talent.tecelao.sobrecarga_controlada",
    "talent.tecelao.veu_de_emergencia",
    "talent.tecelao.trama_precisa",
    "talent.oraculo.fim_anunciado",
    "talent.oraculo.ultima_visao",
    "talent.oraculo.sinais_convergentes",
    "talent.luminar.sentenca_solar",
    "talent.luminar.ultimo_alvorecer",
    "talent.luminar.contraluz_perfeita",
)


def _sql_ids() -> str:
    return ", ".join("'" + talent_id + "'" for talent_id in _TIER_55_IDS)


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
    # A row recorded while Nv.55 was closed is not a public acquisition. Keep
    # its history, but quarantine it so opening the shared gate cannot bless it.
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
            CREATE OR REPLACE FUNCTION pg_temp._c3_strip_unreleased_talent55(value jsonb)
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
                            pg_temp._c3_strip_unreleased_talent55(item)
                        );
                    END LOOP;
                    RETURN result;
                ELSIF jsonb_typeof(value) = 'object' THEN
                    result := '{}'::jsonb;
                    FOR property_name, item IN
                        SELECT key, val FROM jsonb_each(value) AS e(key, val) LOOP
                        result := result || jsonb_build_object(
                            property_name,
                            pg_temp._c3_strip_unreleased_talent55(item)
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
            f"{column}::text LIKE '%{talent_id}%'" for talent_id in _TIER_55_IDS
        )
        op.execute(
            sa.text(
                f"UPDATE {table} SET {column} = "
                f"pg_temp._c3_strip_unreleased_talent55({column}) "
                f"WHERE {column} IS NOT NULL AND ({matches})"
            )
        )
    op.execute(sa.text("DROP FUNCTION pg_temp._c3_strip_unreleased_talent55(jsonb)"))


def downgrade() -> None:
    # The quarantine is intentionally irreversible; restoring these IDs would
    # make pre-release configurations usable after a downgrade.
    pass
