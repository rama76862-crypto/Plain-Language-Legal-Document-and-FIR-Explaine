"""Bounded asynchronous analysis jobs with expiry and deletion tombstones."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Awaitable, Callable, Protocol

from apps.ml.service.contracts import (
    AnalysisProgress,
    AnalysisRequest,
    AnalysisResult,
    JobSnapshot,
    QuestionAnswer,
    QuestionRequest,
)
from apps.ml.service.errors import ServiceProblem


ProgressCallback = Callable[[AnalysisProgress], Awaitable[None]]


class EnginePort(Protocol):
    async def analyze(self, request: AnalysisRequest, progress: ProgressCallback) -> AnalysisResult: ...

    async def answer(self, question: QuestionRequest, request: AnalysisRequest, result: AnalysisResult) -> QuestionAnswer: ...

    async def health(self) -> dict[str, object]: ...

    async def readiness(self) -> tuple[bool, bool]: ...


@dataclass
class _Job:
    request: AnalysisRequest
    status: str = "queued"
    progress: AnalysisProgress = field(default_factory=lambda: AnalysisProgress(completed_clauses=0, total_clauses=0, stage="queued"))
    result: AnalysisResult | None = None
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class JobManager:
    def __init__(self, engine: EnginePort | None, *, max_pending: int = 2, ttl_seconds: int = 1800):
        self.engine = engine
        self.ttl_seconds = ttl_seconds
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_pending)
        self._jobs: dict[str, _Job] = {}
        self._tombstones: dict[str, datetime] = {}
        self._latest_revision_by_document: dict[str, int] = {}
        self._worker: asyncio.Task[None] | None = None
        self._expiry_sweeper: asyncio.Task[None] | None = None
        self._active_analysis_id: str | None = None
        self._generation_lock = asyncio.Lock()
        self._question_results: dict[str, tuple[str, QuestionAnswer, datetime]] = {}
        self._question_locks: dict[str, asyncio.Lock] = {}

    async def start(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._run_worker(), name="be2-analysis-worker")
        if self._expiry_sweeper is None or self._expiry_sweeper.done():
            self._expiry_sweeper = asyncio.create_task(
                self._run_expiry_sweeper(), name="be2-expiry-sweeper"
            )

    async def stop(self) -> None:
        for task in (self._worker, self._expiry_sweeper):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._worker = None
        self._expiry_sweeper = None

    async def _run_expiry_sweeper(self) -> None:
        # Expiry must clean private text even when no client polls another job.
        interval = min(5.0, max(0.1, self.ttl_seconds / 10))
        while True:
            await asyncio.sleep(interval)
            self._expire()

    def _expire(self) -> None:
        now = datetime.now(UTC)
        ttl = timedelta(seconds=self.ttl_seconds)
        for analysis_id, job in list(self._jobs.items()):
            if job.status not in ("queued", "running") and now - job.updated_at > ttl:
                self._jobs.pop(analysis_id, None)
                self._tombstones[analysis_id] = now
                discard = getattr(self.engine, "discard_analysis", None)
                if discard is not None:
                    discard(analysis_id)
        for analysis_id, deleted_at in list(self._tombstones.items()):
            if now - deleted_at > timedelta(hours=24):
                self._tombstones.pop(analysis_id, None)
        for key, (_, _, created_at) in list(self._question_results.items()):
            if now - created_at > ttl:
                self._question_results.pop(key, None)
                lock = self._question_locks.get(key)
                if lock is not None and not lock.locked():
                    self._question_locks.pop(key, None)

    async def readiness(self) -> tuple[bool, bool]:
        if self.engine is None:
            return False, False
        method = getattr(self.engine, "readiness", None)
        if method is not None:
            try:
                return await method()
            except Exception:
                return False, False
        return bool(getattr(self.engine, "classifier_ready", False)), bool(getattr(self.engine, "generator_ready", False))

    async def submit(self, request: AnalysisRequest) -> JobSnapshot:
        self._expire()
        analysis_id = request.analysis_id
        if analysis_id in self._tombstones:
            raise ServiceProblem(410, "JOB_DELETED", "This analysis was deleted and cannot be reused.")
        existing = self._jobs.get(analysis_id)
        if existing is not None:
            if existing.request == request:
                return self._snapshot(analysis_id, existing)
            raise ServiceProblem(409, "ANALYSIS_ID_CONFLICT", "This analysis_id is already bound to a different request.")
        latest_revision = self._latest_revision_by_document.get(request.document_id)
        if latest_revision is not None and request.document_revision < latest_revision:
            raise ServiceProblem(409, "REVISION_CONFLICT", "This analysis request uses a stale document revision.")
        classifier_ready, generator_ready = await self.readiness()
        if not classifier_ready or not generator_ready or self.engine is None:
            raise ServiceProblem(503, "MODEL_UNAVAILABLE", "The local classifier or generator is not ready.", retryable=True)
        # Check capacity before invalidating older work. A rejected busy request
        # must not tombstone a result or advance the remembered document revision.
        if self._queue.full():
            raise ServiceProblem(429, "MODEL_BUSY", "The local analysis queue is full. Retry when a job finishes.", retryable=True)
        if latest_revision is None or request.document_revision > latest_revision:
            for old_id, old_job in list(self._jobs.items()):
                if old_job.request.document_id == request.document_id and old_job.request.document_revision < request.document_revision:
                    self._tombstones[old_id] = datetime.now(UTC)
                    self._jobs.pop(old_id, None)
                    discard = getattr(self.engine, "discard_analysis", None)
                    if discard is not None:
                        discard(old_id)
            self._latest_revision_by_document[request.document_id] = request.document_revision
        job = _Job(
            request=request,
            progress=AnalysisProgress(completed_clauses=0, total_clauses=len(request.clauses), stage="queued"),
        )
        self._jobs[analysis_id] = job
        self._queue.put_nowait(analysis_id)
        return self._snapshot(analysis_id, job)

    def get(self, analysis_id: str) -> JobSnapshot:
        self._expire()
        if analysis_id in self._tombstones:
            raise ServiceProblem(410, "JOB_DELETED", "This analysis was deleted.")
        job = self._jobs.get(analysis_id)
        if job is None:
            raise ServiceProblem(404, "NOT_FOUND", "No active analysis has this ID.")
        return self._snapshot(analysis_id, job)

    def delete(self, analysis_id: str) -> None:
        now = datetime.now(UTC)
        self._tombstones[analysis_id] = now
        self._jobs.pop(analysis_id, None)
        discard = getattr(self.engine, "discard_analysis", None)
        if discard is not None:
            discard(analysis_id)
        for key in [key for key in self._question_results if key.startswith(f"{analysis_id}:")]:
            self._question_results.pop(key, None)
            lock = self._question_locks.get(key)
            if lock is not None and not lock.locked():
                self._question_locks.pop(key, None)

    async def answer_question(self, question: QuestionRequest) -> QuestionAnswer:
        self._expire()
        if question.analysis_id in self._tombstones:
            raise ServiceProblem(410, "JOB_DELETED", "This analysis was deleted.")
        job = self._jobs.get(question.analysis_id)
        if job is None:
            raise ServiceProblem(404, "NOT_FOUND", "No active analysis has this ID.")
        if (
            job.request.document_id != question.document_id
            or job.request.document_revision != question.document_revision
            or job.request.output_language != question.output_language
        ):
            raise ServiceProblem(409, "REVISION_CONFLICT", "The question does not match the current document revision or language.")
        if job.status not in ("complete", "needs_review") or job.result is None:
            raise ServiceProblem(409, "ANALYSIS_NOT_READY", "Wait for this analysis to finish before asking a question.", retryable=True)
        if self.engine is None:
            raise ServiceProblem(503, "MODEL_UNAVAILABLE", "The local generator is not ready.", retryable=True)

        cache_key = f"{question.analysis_id}:{question.client_request_id}"
        fingerprint = question.model_dump_json()
        cached = self._question_results.get(cache_key)
        if cached is not None:
            if cached[0] != fingerprint:
                raise ServiceProblem(409, "CLIENT_REQUEST_ID_CONFLICT", "This client_request_id was already used for another question.")
            return cached[1]

        if self._active_analysis_id is not None or self._generation_lock.locked():
            raise ServiceProblem(429, "MODEL_BUSY", "The local model is processing another request.", retryable=True)

        lock = self._question_locks.setdefault(cache_key, asyncio.Lock())
        async with lock:
            cached = self._question_results.get(cache_key)
            if cached is not None:
                if cached[0] != fingerprint:
                    raise ServiceProblem(409, "CLIENT_REQUEST_ID_CONFLICT", "This client_request_id was already used for another question.")
                return cached[1]
            if self._active_analysis_id is not None or self._generation_lock.locked():
                raise ServiceProblem(429, "MODEL_BUSY", "The local model is processing another request.", retryable=True)
            async with self._generation_lock:
                self._active_analysis_id = f"question:{question.analysis_id}"
                try:
                    answer = await self.engine.answer(question, job.request, job.result)
                except TimeoutError:
                    raise ServiceProblem(504, "MODEL_TIMEOUT", "The local model timed out while answering.", retryable=True)
                finally:
                    self._active_analysis_id = None
            if question.analysis_id in self._tombstones or self._jobs.get(question.analysis_id) is not job:
                raise ServiceProblem(410, "JOB_DELETED", "This analysis was deleted while the question was being processed.")
            self._question_results[cache_key] = (fingerprint, answer, datetime.now(UTC))
            return answer

    async def _run_worker(self) -> None:
        while True:
            analysis_id = await self._queue.get()
            try:
                job = self._jobs.get(analysis_id)
                if job is None or analysis_id in self._tombstones:
                    continue
                if self.engine is None:
                    job.status = "failed"
                    job.warnings = ["Local ML engine is unavailable."]
                    job.updated_at = datetime.now(UTC)
                    continue

                async with self._generation_lock:
                    current = self._jobs.get(analysis_id)
                    if current is None or analysis_id in self._tombstones:
                        continue
                    self._active_analysis_id = analysis_id
                    job.status = "running"
                    job.progress = job.progress.model_copy(update={"stage": "starting"})
                    job.updated_at = datetime.now(UTC)

                    async def update(progress: AnalysisProgress) -> None:
                        current_job = self._jobs.get(analysis_id)
                        if current_job is None or analysis_id in self._tombstones:
                            raise ServiceProblem(410, "JOB_DELETED", "This analysis was deleted while processing.")
                        current_job.progress = progress
                        current_job.updated_at = datetime.now(UTC)

                    try:
                        result = await self.engine.analyze(job.request, update)
                    except TimeoutError:
                        current = self._jobs.get(analysis_id)
                        if current is not None and analysis_id not in self._tombstones:
                            current.status = "failed"
                            current.warnings = ["MODEL_TIMEOUT: The local model timed out. Retry or review this document."]
                            current.progress = current.progress.model_copy(update={"stage": "failed"})
                            current.updated_at = datetime.now(UTC)
                        continue
                    except ServiceProblem as error:
                        current = self._jobs.get(analysis_id)
                        if current is not None and analysis_id not in self._tombstones:
                            current.status = "failed"
                            current.warnings = [f"{error.code}: {error.message}"]
                            current.progress = current.progress.model_copy(update={"stage": "failed"})
                            current.updated_at = datetime.now(UTC)
                        continue
                    except Exception:
                        current = self._jobs.get(analysis_id)
                        if current is not None and analysis_id not in self._tombstones:
                            current.status = "failed"
                            current.warnings = ["Analysis failed. Retry or review this document."]
                            current.progress = current.progress.model_copy(update={"stage": "failed"})
                            current.updated_at = datetime.now(UTC)
                        continue
                    finally:
                        self._active_analysis_id = None

                    current = self._jobs.get(analysis_id)
                    if current is None or analysis_id in self._tombstones:
                        continue
                    current.result = result
                    incomplete_coverage = result.coverage.analysed < result.coverage.total
                    has_review_items = any(item.review_status == "needs_review" for item in result.items)
                    current.status = "needs_review" if result.warnings or has_review_items or incomplete_coverage else "complete"
                    current.progress = AnalysisProgress(
                        completed_clauses=len(job.request.clauses),
                        total_clauses=len(job.request.clauses),
                        stage="complete" if current.status == "complete" else "needs_review",
                        failed_clauses=max(0, len(job.request.clauses) - result.coverage.analysed),
                    )
                    current.warnings = list(result.warnings)
                    current.updated_at = datetime.now(UTC)
            finally:
                discard = getattr(self.engine, "discard_analysis", None)
                if discard is not None:
                    discard(analysis_id)
                if self._active_analysis_id == analysis_id:
                    self._active_analysis_id = None
                self._queue.task_done()

    @staticmethod
    def _snapshot(analysis_id: str, job: _Job) -> JobSnapshot:
        return JobSnapshot(
            analysis_id=analysis_id,
            status=job.status,  # type: ignore[arg-type]
            progress=job.progress,
            document_revision=job.request.document_revision,
            output_language=job.request.output_language,
            result=job.result,
            warnings=list(job.warnings),
        )

