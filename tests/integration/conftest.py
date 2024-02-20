import os
import uuid
import pytest


@pytest.fixture
def pgstore():
    url = os.getenv("INCIDENT_TEST_DATABASE")
    if not url:
        pytest.skip("Set INCIDENT_TEST_DATABASE for real PostgreSQL checks")
    import psycopg2
    from psycopg2 import sql
    from incident.postgres import PostgresStore

    schema = "test_" + uuid.uuid4().hex
    connection = psycopg2.connect(url)
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    store = PostgresStore(url, schema)
    try:
        yield store
    finally:
        store.close()
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )
        connection.close()
