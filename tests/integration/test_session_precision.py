from incident.postgres import PostgresStore


def test_large_session_expiry_is_not_rounded_by_postgres_storage(pgstore):
    expires = 1790777777
    pgstore.add_session("precision-session", "subject", expires)
    stored = pgstore.db.execute(
        "SELECT expires FROM sessions WHERE id=?", ("precision-session",)
    ).fetchone()[0]
    assert stored == expires
    assert pgstore.session_active("precision-session", "subject", expires - 1)
    assert not pgstore.session_active("precision-session", "subject", expires)


def test_existing_real_column_is_upgraded_without_removing_session_records(pgstore):
    pgstore.add_session("retained-session", "subject", 100)
    pgstore.db.execute("ALTER TABLE sessions ALTER COLUMN expires TYPE REAL")
    second = PostgresStore(pgstore.url, pgstore.schema)
    try:
        column = second.db.execute(
            "SELECT data_type FROM information_schema.columns WHERE table_schema=? AND table_name='sessions' AND column_name='expires'",
            (pgstore.schema,),
        ).fetchone()[0]
        assert column == "double precision"
        assert second.session_active("retained-session", "subject", 99)
    finally:
        second.close()
