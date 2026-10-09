from sqlalchemy import inspect


async def test_pvpve_round_takeover_migration_is_non_null_and_defaults_to_ai(database):
    engine, _sessions = database
    async with engine.connect() as connection:
        columns = await connection.run_sync(
            lambda sync: {
                column["name"]: column
                for column in inspect(sync).get_columns("pvpve_collision_members")
            }
        )
    column = columns["round_takeover"]
    assert column["nullable"] is False
    assert "false" in str(column["default"]).lower()
