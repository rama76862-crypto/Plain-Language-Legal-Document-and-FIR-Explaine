"""Private Backend 2 HTTP API. It must not be exposed directly to browsers."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.ml.service.contracts import AnalysisRequest, JobSnapshot, QuestionAnswer, QuestionRequest, ServiceError
from apps.ml.service.errors import ServiceProblem
from apps.ml.service.manager import EnginePort, JobManager


def create_app(
    engine: EnginePort | None = None,
    *,
    max_pending: int = 2,
    ttl_seconds: int = 1800,
) -> FastAPI:
    manager = JobManager(engine, max_pending=max_pending, ttl_seconds=ttl_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await manager.start()
        try:
            yield
        finally:
            await manager.stop()

    app = FastAPI(title="NyayaLens Private ML Service", version="1.0.0", lifespan=lifespan)
    app.state.job_manager = manager

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Response:
        request.state.request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ServiceProblem)
    async def service_problem_handler(request: Request, exc: ServiceProblem) -> JSONResponse:
        payload = ServiceError(
            error={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
            request_id=getattr(request.state, "request_id", uuid.uuid4().hex),
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, _: RequestValidationError) -> JSONResponse:
        # Do not serialize validation inputs; request bodies can contain private clauses.
        payload = ServiceError(
            error={"code": "INVALID_REQUEST", "message": "The request does not match the private API schema.", "retryable": False},
            request_id=getattr(request.state, "request_id", uuid.uuid4().hex),
        )
        return JSONResponse(status_code=422, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, _: Exception) -> JSONResponse:
        payload = ServiceError(
            error={"code": "INTERNAL_ERROR", "message": "The private ML service failed to handle this request.", "retryable": True},
            request_id=getattr(request.state, "request_id", uuid.uuid4().hex),
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))

    @app.get("/internal/health")
    async def health() -> dict[str, Any]:
        classifier_ready, generator_ready = await manager.readiness()
        details = await engine.health() if engine is not None else {}
        return {
            "status": "ready" if classifier_ready and generator_ready else "degraded",
            "classifier_ready": classifier_ready,
            "generator_ready": generator_ready,
            "tested_languages": details.get("tested_languages", {"en": False, "hi": False, "pa": False}),
            "details": details,
        }

    @app.post("/internal/analyse", status_code=status.HTTP_202_ACCEPTED)
    async def analyse(payload: AnalysisRequest) -> dict[str, str]:
        snapshot = await manager.submit(payload)
        return {"analysis_id": snapshot.analysis_id, "status": snapshot.status}

    @app.get("/internal/jobs/{analysis_id}", response_model=JobSnapshot)
    async def get_job(analysis_id: str) -> JobSnapshot:
        return manager.get(analysis_id)

    @app.delete("/internal/jobs/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_job(analysis_id: str) -> Response:
        manager.delete(analysis_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/internal/question", response_model=QuestionAnswer)
    async def question(payload: QuestionRequest) -> QuestionAnswer:
        return await manager.answer_question(payload)

    return app


from apps.ml.service.bootstrap import build_default_pipeline

app = create_app(build_default_pipeline())

