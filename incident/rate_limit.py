from collections import OrderedDict
import threading
import math


class RateLimit:
    def __init__(self, limit=12, max_keys=1000):
        if type(limit) is not int or limit < 1 or type(max_keys) is not int or max_keys < 1:
            raise ValueError("Rate limits and capacity must be positive integers")
        self.limit = limit
        self.max_keys = max_keys
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def allow(self, key, now):
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("Rate limiter requires a finite clock")
        with self.lock:
            values = [value for value in self.entries.pop(key, []) if now - value < 60]
            accepted = len(values) < self.limit
            if accepted:
                values.append(now)
            self.entries[key] = values
            while len(self.entries) > self.max_keys:
                self.entries.popitem(last=False)
            return accepted
