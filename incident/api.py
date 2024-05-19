import time
from dataclasses import asdict
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from .identity import require
from .workflow import Workflow
from .http_limits import BodyLimitMiddleware
from .rate_limit import RateLimit


class LoginRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class IncidentRequest(BaseModel):
    service: str = Field(min_length=2, max_length=48)
    title: str = Field(min_length=1, max_length=160)


class RevisionRequest(BaseModel):
    revision: int = Field(ge=1)


class ReviewRequest(RevisionRequest):
    digest: str = Field(min_length=64, max_length=64)


class PlanRequest(RevisionRequest):
    steps: list[dict] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, max_length=1000)


class ChangesRequest(RevisionRequest):
    reason: str = Field(min_length=1, max_length=500)


class RolesRequest(BaseModel):
    roles: list[str] = Field(max_length=4)


class SimulationRequest(BaseModel):
    service: str = Field(min_length=2, max_length=48)
    faults: list[str] = Field(max_length=3)
    variant: int = Field(default=0, ge=0, le=1)


def create_app(store, auth, tools=None):
    app = FastAPI(title="Incident Workbench")
    app.add_middleware(BodyLimitMiddleware)
    limits = RateLimit()

    @app.middleware("http")
    async def headers(request, call_next):
        if request.url.path == "/api/session" and request.method == "POST":
            address = request.client.host if request.client else "unknown"
            if not limits.allow(address, time.monotonic()):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many sign-in attempts; wait a minute"},
                    headers={"Retry-After": "60"},
                )
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
            }
        )
        return response

    workflow = Workflow(store)
    bearer = HTTPBearer(auto_error=False)

    def token(credentials=Depends(bearer)):
        if not credentials:
            raise HTTPException(
                401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"}
            )
        return credentials.credentials

    def actor(value=Depends(token)):
        try:
            return auth.actor(value)
        except PermissionError as error:
            raise HTTPException(401, "Session is invalid or expired") from error

    @app.exception_handler(PermissionError)
    async def forbidden(request, error):
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @app.exception_handler(ValueError)
    async def conflict(request, error):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(LookupError)
    async def missing(request, error):
        return JSONResponse(
            status_code=404, content={"detail": "Incident or account not found"}
        )

    @app.post("/api/session")
    def login(request: LoginRequest):
        try:
            return {
                "access_token": auth.login(request.subject, request.password),
                "token_type": "Bearer",
                "expires_in": 1800,
            }
        except PermissionError as error:
            raise HTTPException(401, "Account or password was not accepted") from error

    @app.delete("/api/session")
    def logout(value=Depends(token)):
        try:
            auth.logout(value)
        except PermissionError as error:
            raise HTTPException(401, "Session is invalid or expired") from error
        return {"signed_out": True}

    @app.get("/api/me")
    def me(current=Depends(actor)):
        return {
            "tenant": current.tenant,
            "subject": current.subject,
            "roles": sorted(current.roles),
        }

    @app.get("/api/incidents")
    def queue(current=Depends(actor)):
        require(current, "read")
        return {
            "incidents": [
                {
                    key: item[key]
                    for key in [
                        "id",
                        "title",
                        "service",
                        "status",
                        "revision",
                        "created_at",
                    ]
                }
                for item in store.list(current.tenant)
            ]
        }

    @app.get("/api/incidents/{key}")
    def detail(key: str, current=Depends(actor)):
        require(current, "read")
        return store.get(current.tenant, key)

    @app.post("/api/incidents", status_code=201)
    def create(request: IncidentRequest, current=Depends(actor)):
        return workflow.create(current, request.service, request.title, time.time())

    @app.put("/api/incidents/{key}/plan")
    def edit(key: str, request: PlanRequest, current=Depends(actor)):
        return workflow.edit(
            current,
            key,
            request.steps,
            request.rationale,
            request.revision,
            time.time(),
        )

    @app.post("/api/incidents/{key}/approve")
    def approve(key: str, request: ReviewRequest, current=Depends(actor)):
        return workflow.approve(
            current, key, request.digest, request.revision, time.time()
        )

    @app.post("/api/incidents/{key}/cancel")
    def cancel(key: str, request: RevisionRequest, current=Depends(actor)):
        return workflow.cancel(current, key, request.revision, time.time())

    @app.post("/api/incidents/{key}/recollect")
    def recollect(key: str, request: RevisionRequest, current=Depends(actor)):
        return workflow.retry(current, key, request.revision, time.time())

    @app.post("/api/incidents/{key}/resume")
    def resume(key: str, request: RevisionRequest, current=Depends(actor)):
        return workflow.resume(current, key, request.revision, time.time())

    @app.put("/api/accounts/{subject}/roles")
    def roles(subject: str, request: RolesRequest, current=Depends(actor)):
        require(current, "admin")
        store.set_roles(current.tenant, subject, request.roles)
        return {"subject": subject, "roles": sorted(request.roles)}

    @app.post("/api/simulation")
    def simulate(request: SimulationRequest, current=Depends(actor)):
        require(current, "admin")
        if tools is None:
            raise HTTPException(503, "The local simulator is unavailable")
        tools.provision(current.tenant, request.service)
        return tools.inject(
            current.tenant, request.service, request.faults, request.variant
        )

    @app.post("/api/incidents/{key}/reconcile")
    def reconcile(key: str, current=Depends(actor)):
        require(current, "collect")
        if tools is None:
            raise HTTPException(503, "The local simulator is unavailable")
        from .engine import Engine

        return Engine(store, tools).reconcile(current.tenant, key)

    @app.get("/api/config")
    def configuration():
        return {
            "modes": ["rules"],
            "services": [
                "heap-api",
                "busy-api",
                "release-api",
                "catalog-api",
                "storage-api",
                "queue-api",
            ],
        }

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def readiness():
        try:
            with store.lock:
                store.db.execute("SELECT 1").fetchone()
        except Exception:
            raise HTTPException(503, "Storage is unavailable")
        return {"status": "ready", "simulator_configured": tools is not None}

    @app.post("/api/incidents/{key}/request-changes")
    def request_changes(key: str, request: ChangesRequest, current=Depends(actor)):
        return workflow.request_changes(
            current, key, request.revision, request.reason, time.time()
        )

    return app
