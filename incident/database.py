from .store import Store


def open_store(url):
    if url.startswith("sqlite:///"):
        return Store(url[len("sqlite:///") :])
    if url.startswith("postgresql://"):
        from .postgres import PostgresStore

        return PostgresStore(url)
    raise ValueError("Use a sqlite:/// path or postgresql:// connection URL")
