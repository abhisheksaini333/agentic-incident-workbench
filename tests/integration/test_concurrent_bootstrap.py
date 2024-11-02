from concurrent.futures import ThreadPoolExecutor
import os
import threading
import time
import uuid
import pytest


def test_simultaneous_service_bootstrap_does_not_race_postgres_catalog(monkeypatch):
    url = os.getenv("INCIDENT_TEST_DATABASE")
    if not url:
        pytest.skip("Set INCIDENT_TEST_DATABASE for real PostgreSQL checks")
    import psycopg2
    from psycopg2 import sql
    from incident.postgres import Connection, PostgresStore

    schema = "bootstrap_" + uuid.uuid4().hex
    admin = psycopg2.connect(url)
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    original = Connection.execute

    def delayed(connection, query, arguments=()):
        if query.startswith("CREATE TABLE"):
            time.sleep(0.02)
        return original(connection, query, arguments)

    monkeypatch.setattr(Connection, "execute", delayed)
    barrier = threading.Barrier(6)

    def open_one(_):
        barrier.wait(timeout=5)
        store = PostgresStore(url, schema)
        try:
            assert store.list("acme") == []
        finally:
            store.close()

    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(open_one, range(6)))
    finally:
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )
        admin.close()
