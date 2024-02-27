import hmac
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field


class FaultRequest(BaseModel):
    faults: list[str] = Field(max_length=3)
    variant: int = Field(default=0, ge=0, le=1)


class EffectRequest(BaseModel):
    key: str = Field(min_length=16, max_length=100)
    generation: int = Field(ge=1)
    step: dict


def create_simulator_app(simulator, worker_key, admin_key):
    if min(len(worker_key), len(admin_key)) < 24 or worker_key == admin_key:
        raise ValueError(
            "Use distinct private simulator keys of at least 24 characters"
        )
    app = FastAPI(title="Incident service simulator")
    bearer = HTTPBearer(auto_error=False)

    def worker(credentials=Depends(bearer)):
        if not credentials or not hmac.compare_digest(
            credentials.credentials, worker_key
        ):
            raise HTTPException(403, "Simulator worker authority required")

    def admin(credentials=Depends(bearer)):
        if not credentials or not hmac.compare_digest(
            credentials.credentials, admin_key
        ):
            raise HTTPException(403, "Simulator injection authority required")

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(LookupError)
    async def missing(request, error):
        return JSONResponse(
            status_code=404, content={"detail": "Simulated service not found"}
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/{tenant}/{service}/provision", dependencies=[Depends(admin)])
    def provision(tenant: str, service: str):
        return simulator.provision(tenant, service)

    @app.post("/v1/{tenant}/{service}/faults", dependencies=[Depends(admin)])
    def inject(tenant: str, service: str, request: FaultRequest):
        return simulator.inject(tenant, service, request.faults, request.variant)

    @app.get("/v1/{tenant}/{service}/observe", dependencies=[Depends(worker)])
    def observe(tenant: str, service: str):
        return simulator.observe(tenant, service)

    @app.get("/v1/{tenant}/{service}/workload", dependencies=[Depends(worker)])
    def workload(tenant: str, service: str):
        result = simulator.workload(tenant, service)
        return JSONResponse(status_code=result["status"], content=result)

    @app.get("/v1/{tenant}/{service}/metrics", dependencies=[Depends(worker)])
    def metrics(tenant: str, service: str):
        return PlainTextResponse(simulator.prometheus(tenant, service))

    @app.post("/v1/{tenant}/{service}/effects", dependencies=[Depends(worker)])
    def apply(tenant: str, service: str, request: EffectRequest):
        return simulator.apply(
            tenant, service, request.step, request.key, request.generation
        )

    @app.get("/v1/{tenant}/{service}/effects/{key}", dependencies=[Depends(worker)])
    def receipt(tenant: str, service: str, key: str):
        result = simulator.receipt(tenant, key)
        if result is None:
            raise HTTPException(404, "Receipt not found")
        return result

    return app
