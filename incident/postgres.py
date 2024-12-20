import threading
import psycopg2
from psycopg2 import sql
from .store import Store


class Connection:
    def __init__(self, url, schema):
        self.raw = psycopg2.connect(url, connect_timeout=5)
        self.raw.autocommit = True
        with self.raw.cursor() as cursor:
            cursor.execute(
                sql.SQL("SET search_path TO {},public").format(sql.Identifier(schema))
            )

    def execute(self, query, arguments=()):
        cursor = self.raw.cursor()
        if query == "BEGIN IMMEDIATE":
            cursor.execute("BEGIN")
            cursor.execute("SELECT pg_advisory_xact_lock(8852024)")
        else:
            cursor.execute(query.replace("?", "%s"), arguments)
        return cursor

    def close(self):
        self.raw.close()


class PostgresStore(Store):
    def __init__(self, url, schema="public"):
        self.url = url
        self.schema = schema
        self.db = Connection(url, schema)
        self.lock = threading.RLock()
        try:
            with self.transaction():
                self._schema()
                column = self.db.execute(
                    "SELECT data_type FROM information_schema.columns WHERE table_schema=? "
                    "AND table_name='sessions' AND column_name='expires'",
                    (schema,),
                ).fetchone()
                if column and column[0] == "real":
                    self.db.execute(
                        "ALTER TABLE sessions ALTER COLUMN expires TYPE DOUBLE PRECISION"
                    )
        except BaseException:
            self.db.close()
            raise
