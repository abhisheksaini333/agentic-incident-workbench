import time
import httpx


class Worker:
    def __init__(self, store, engine_factory, clock=None):
        self.store = store
        self.engine_factory = engine_factory
        self.clock = clock or time.time

    def once(self):
        candidates = self.store.runnable(self.clock())
        for incident in candidates:
            engine = self.engine_factory(incident)
            try:
                engine.run_until_pause(incident["tenant"], incident["id"])
                return True
            except (ConnectionError, TimeoutError, httpx.HTTPError):
                self.store.defer_transport(
                    incident["tenant"], incident["id"], self.clock()
                )
                continue
            except ValueError:
                # Another process may have claimed this incident after the scan.
                continue
        return False

    def run(self, stop):
        while not stop.is_set():
            if not self.once():
                stop.wait(1)
