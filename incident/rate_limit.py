from collections import OrderedDict
import threading


class RateLimit:
    def __init__(self, limit=12, max_keys=1000):
        self.limit = limit
        self.max_keys = max_keys
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def allow(self, key, now):
        with self.lock:
            values = [value for value in self.entries.pop(key, []) if now - value < 60]
            accepted = len(values) < self.limit
            if accepted:
                values.append(now)
            self.entries[key] = values
            while len(self.entries) > self.max_keys:
                self.entries.popitem(last=False)
            return accepted
