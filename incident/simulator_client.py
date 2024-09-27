import re
import httpx
from .identity import identifier
from .plans import validate_step


class SimulatorClient:
    def __init__(self, base_url, worker_key, admin_key=None, transport=None):
        self.client = httpx.Client(base_url=base_url, timeout=5.0, transport=transport)
        self.worker_headers = {"Authorization": "Bearer " + worker_key}
        self.admin_headers = (
            {"Authorization": "Bearer " + admin_key} if admin_key else None
        )

    def path(self, tenant, service):
        return f"/v1/{identifier(tenant)}/{identifier(service)}"

    def _json(self, response):
        if response.status_code == 409:
            raise ValueError(
                "Simulator precondition changed; recollect evidence before retrying"
            )
        response.raise_for_status()
        return response.json()

    def observe(self, tenant, service):
        return self._json(
            self.client.get(
                self.path(tenant, service) + "/observe", headers=self.worker_headers
            )
        )

    def apply(self, tenant, service, step, key, generation):
        checked = validate_step(step, service)
        return self._json(
            self.client.post(
                self.path(tenant, service) + "/effects",
                headers=self.worker_headers,
                json={"step": checked, "key": key, "generation": generation},
            )
        )

    def receipt(self, tenant, service, key):
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,100}", key):
            raise ValueError("Invalid effect receipt key")
        response = self.client.get(
            self.path(tenant, service) + "/effects/" + key, headers=self.worker_headers
        )
        return None if response.status_code == 404 else self._json(response)

    def provision(self, tenant, service):
        if not self.admin_headers:
            raise PermissionError("Simulator injection is not configured")
        return self._json(
            self.client.post(
                self.path(tenant, service) + "/provision", headers=self.admin_headers
            )
        )

    def inject(self, tenant, service, faults, variant=0):
        if not self.admin_headers:
            raise PermissionError("Simulator injection is not configured")
        return self._json(
            self.client.post(
                self.path(tenant, service) + "/faults",
                headers=self.admin_headers,
                json={"faults": faults, "variant": variant},
            )
        )

    def workload(self, tenant, service):
        response = self.client.get(
            self.path(tenant, service) + "/workload", headers=self.worker_headers
        )
        if response.status_code not in {200, 503}:
            response.raise_for_status()
        return response.json()

    def close(self):
        self.client.close()
