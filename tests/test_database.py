import pytest
from incident.database import open_store


def test_database_scheme_is_explicit_and_sqlite_is_persistent(tmp_path):
    store = open_store("sqlite:///" + str(tmp_path / "incidents.db"))
    assert store.list("acme") == []
    store.close()
    with pytest.raises(ValueError):
        open_store("https://example.com/database")
