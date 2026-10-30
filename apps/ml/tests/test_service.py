"""Fast service tests use an explicitly fake engine; they are not model proof."""

from __future__ import annotations

import asyncio
import threading
import time

from fastapi.testclient import TestClient

from apps.ml.service.app import create_app
from apps.ml.service.contracts import (
    AnalysisProgress,
    AnalysisRequest,
    AnalysisResult,
    Coverage,
    Evidence,
    QuestionAnswer,
    QuestionRequest,
)
from apps.ml.service.manager import JobManager


TEXT = "The provider may change these terms at any time without prior notice."


def make_request(analysis_id: str = "a1", revision: int = 1) -> dict[str, object]:
    return {
        "document_id": "doc-fixture",
        "analysis_id": analysis_id,
        "document_revision": revision,
        "document_type": "agreement",
        "input_language": "en",
        "output_language": "en",
        "clauses": [{"clause_id": "c1", "reviewed_text": TEXT}],
    }


class FakeEngine:
    classifier_ready = True
    generator_ready = True

    def __init__(self, *, block: bool = False, block_answer: bool = False) -> None:
        self.block = block
        self.block_answer = block_answer
        self.started = threading.Event()
        self.release = threading.Event()
        self.answer_started = asyncio.Event()
        self.answer_release = asyncio.Event()
        self.answer_calls = 0
        self.active_generation_calls = 0
        self.max_active_generation_calls = 0
        self.discarded_analysis_ids: list[str] = []

    def _enter_generation(self) -> None:
        self.active_generation_calls += 1
        self.max_active_generation_calls = max(
            self.max_active_generation_calls, self.active_generation_calls
        )

    def _leave_generation(self) -> None:
        self.active_generation_calls -= 1

    async def readiness(self) -> tuple[bool, bool]:
        return True, True

    def discard_analysis(self, analysis_id: str) -> None:
        self.discarded_analysis_ids.append(analysis_id)

    async def health(self) -> dict[str, object]:
        return {"tested_languages": {"en": False, "hi": False, "pa": False}}

    async def analyze(self, request: AnalysisRequest, progress) -> AnalysisResult:
        self._enter_generation()
        try:
            self.started.set()
            if self.block:
                await asyncio.to_thread(self.release.wait, 5)
            await progress(AnalysisProgress(completed_clauses=1, total_clauses=1, stage="complete"))
            return AnalysisResult(
                document_id=request.document_id,
                analysis_id=request.analysis_id,
                document_revision=request.document_revision,
                input_language=request.input_language,
                output_language=request.output_language,
                document_type=request.document_type,
                coverage=Coverage(analysed=1, total=1),
                items=[
                    {
                        "item_id": "i1",
                        "clause_id": "c1",
                        "kind": "explanation",
                        "category": "plain_language_explanation",
                        "explanation": "The provider can change the terms without notice.",
                        "evidence": [{"clause_id": "c1", "quote": "change these terms"}],
                        "detector": "model",
                    }
                ],
            )
        finally:
            self._leave_generation()

    async def answer(self, question: QuestionRequest, request: AnalysisRequest, result: AnalysisResult) -> QuestionAnswer:
        self.answer_calls += 1
        self._enter_generation()
        try:
            self.answer_started.set()
            if self.block_answer:
                await self.answer_release.wait()
            return QuestionAnswer(
                answer="The provider may change the terms.",
                evidence=[Evidence(clause_id="c1", quote="change these terms")],
            )
        finally:
            self._leave_generation()


class TimeoutEngine(FakeEngine):
    async def analyze(self, request: AnalysisRequest, progress) -> AnalysisResult:
        raise TimeoutError("synthetic local timeout")


class TimeoutOnceEngine(FakeEngine):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    async def analyze(self, request: AnalysisRequest, progress) -> AnalysisResult:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("synthetic first-call timeout")
        return await super().analyze(request, progress)


def _wait_for_status(client: TestClient, analysis_id: str, target: str) -> dict[str, object]:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/internal/jobs/{analysis_id}")
        if response.status_code == 200 and response.json()["status"] == target:
            return response.json()
        time.sleep(0.02)
    raise AssertionError(f"job {analysis_id} did not reach {target}")


def test_async_job_reports_real_clause_progress_and_question_is_idempotent() -> None:
    engine = FakeEngine()
    with TestClient(create_app(engine)) as client:
        started = client.post("/internal/analyse", json=make_request())
        assert started.status_code == 202
        assert started.json() == {"analysis_id": "a1", "status": "queued"}
        snapshot = _wait_for_status(client, "a1", "complete")
        assert snapshot["progress"] == {
            "completed_clauses": 1,
            "total_clauses": 1,
            "stage": "complete",
            "failed_clauses": 0,
        }
        assert snapshot["result"]["coverage"] == {"analysed": 1, "total": 1}

        question = {
            "document_id": "doc-fixture",
            "analysis_id": "a1",
            "document_revision": 1,
            "question": "What may the provider change?",
            "output_language": "en",
            "client_request_id": "q1",
        }
        first = client.post("/internal/question", json=question)
        second = client.post("/internal/question", json=question)
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert engine.answer_calls == 1

        changed_question = {**question, "question": "What does the provider pay?"}
        conflict = client.post("/internal/question", json=changed_question)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "CLIENT_REQUEST_ID_CONFLICT"

        conflicting_analysis = make_request("a1")
        conflicting_analysis["clauses"] = [
            {"clause_id": "c1", "reviewed_text": "A different synthetic clause."}
        ]
        conflict = client.post("/internal/analyse", json=conflicting_analysis)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "ANALYSIS_ID_CONFLICT"


def test_queue_is_bounded_and_health_stays_responsive() -> None:
    engine = FakeEngine(block=True)
    with TestClient(create_app(engine)) as client:
        assert client.post("/internal/analyse", json=make_request("a1")).status_code == 202
        assert engine.started.wait(2)
        assert client.post("/internal/analyse", json=make_request("a2")).status_code == 202
        assert client.post("/internal/analyse", json=make_request("a3")).status_code == 202
        full = client.post("/internal/analyse", json=make_request("a4"))
        assert full.status_code == 429
        assert full.json()["error"]["code"] == "MODEL_BUSY"
        start = time.monotonic()
        health = client.get("/internal/health")
        assert health.status_code == 200
        assert time.monotonic() - start < 1
        engine.release.set()
        _wait_for_status(client, "a1", "complete")
        _wait_for_status(client, "a2", "complete")
        _wait_for_status(client, "a3", "complete")


def test_deletion_and_new_revision_tombstone_late_and_stale_jobs() -> None:
    engine = FakeEngine(block=True)
    with TestClient(create_app(engine)) as client:
        assert client.post("/internal/analyse", json=make_request("old", revision=1)).status_code == 202
        assert engine.started.wait(2)
        assert client.post("/internal/analyse", json=make_request("new", revision=2)).status_code == 202
        assert client.get("/internal/jobs/old").status_code == 410
        stale = client.post("/internal/analyse", json=make_request("stale", revision=1))
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "REVISION_CONFLICT"
        engine.release.set()
        _wait_for_status(client, "new", "complete")
        assert client.delete("/internal/jobs/new").status_code == 204
        assert client.get("/internal/jobs/new").status_code == 410


def test_invalid_request_error_does_not_echo_private_text() -> None:
    secret_clause = "PRIVATE CLAUSE THAT MUST NOT APPEAR IN AN ERROR"
    with TestClient(create_app(None)) as client:
        response = client.post(
            "/internal/analyse",
            json={"document_id": "doc", "reviewed_text": secret_clause},
        )
        assert response.status_code == 422
        assert secret_clause not in response.text
        assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unavailable_and_timeout_failures_have_explicit_codes() -> None:
    with TestClient(create_app(None)) as client:
        unavailable = client.post("/internal/analyse", json=make_request())
        assert unavailable.status_code == 503
        assert unavailable.json()["error"]["code"] == "MODEL_UNAVAILABLE"

    with TestClient(create_app(TimeoutEngine())) as client:
        assert client.post("/internal/analyse", json=make_request()).status_code == 202
        failed = _wait_for_status(client, "a1", "failed")
        assert failed["progress"]["stage"] == "failed"
        assert failed["warnings"][0].startswith("MODEL_TIMEOUT:")


def test_a_new_job_succeeds_after_timeout_releases_the_worker() -> None:
    engine = TimeoutOnceEngine()
    with TestClient(create_app(engine)) as client:
        assert client.post("/internal/analyse", json=make_request("timeout")).status_code == 202
        timed_out = _wait_for_status(client, "timeout", "failed")
        assert timed_out["warnings"][0].startswith("MODEL_TIMEOUT:")

        recovered = client.post("/internal/analyse", json=make_request("recovered"))
        assert recovered.status_code == 202
        completed = _wait_for_status(client, "recovered", "complete")
        assert completed["result"]["analysis_id"] == "recovered"
        assert engine.calls == 2


def test_a_new_job_succeeds_after_deletion_while_generation_is_running() -> None:
    engine = FakeEngine(block=True)
    with TestClient(create_app(engine)) as client:
        assert client.post("/internal/analyse", json=make_request("deleted")).status_code == 202
        assert engine.started.wait(2)
        assert client.delete("/internal/jobs/deleted").status_code == 204
        engine.release.set()
        assert client.get("/internal/jobs/deleted").status_code == 410

        recovered = client.post("/internal/analyse", json=make_request("after-delete", revision=2))
        assert recovered.status_code == 202
        completed = _wait_for_status(client, "after-delete", "complete")
        assert completed["result"]["analysis_id"] == "after-delete"
        assert engine.max_active_generation_calls == 1


def test_expiry_sweeper_removes_completed_private_text_and_question_cache() -> None:
    engine = FakeEngine()
    app = create_app(engine, ttl_seconds=1)
    manager = app.state.job_manager
    with TestClient(app) as client:
        assert client.post("/internal/analyse", json=make_request()).status_code == 202
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            job = manager._jobs.get("a1")
            if job is not None and job.status == "complete":
                break
            time.sleep(0.01)
        assert manager._jobs["a1"].status == "complete"
        question = {
            "document_id": "doc-fixture",
            "analysis_id": "a1",
            "document_revision": 1,
            "question": "What may the provider change?",
            "output_language": "en",
            "client_request_id": "expire-question",
        }
        assert client.post("/internal/question", json=question).status_code == 200
        engine.discarded_analysis_ids.clear()
        manager.ttl_seconds = 0
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and manager._jobs:
            time.sleep(0.02)

        assert "a1" not in manager._jobs
        assert not manager._question_results
        assert "a1" in engine.discarded_analysis_ids
        expired = client.get("/internal/jobs/a1")
        assert expired.status_code == 410
        assert expired.json()["error"]["code"] == "JOB_DELETED"


def test_delete_tombstone_suppresses_late_running_result() -> None:
    engine = FakeEngine(block=True)
    with TestClient(create_app(engine)) as client:
        assert client.post("/internal/analyse", json=make_request()).status_code == 202
        assert engine.started.wait(2)
        assert client.delete("/internal/jobs/a1").status_code == 204
        engine.release.set()
        time.sleep(0.05)
        deleted = client.get("/internal/jobs/a1")
        assert deleted.status_code == 410
        assert deleted.json()["error"]["code"] == "JOB_DELETED"


def test_question_generation_and_analysis_share_one_model_slot() -> None:
    async def scenario() -> None:
        engine = FakeEngine(block_answer=True)
        manager = JobManager(engine)
        await manager.start()
        try:
            await manager.submit(AnalysisRequest.model_validate(make_request("a1")))
            deadline = time.monotonic() + 3
            while manager.get("a1").status != "complete" and time.monotonic() < deadline:
                await asyncio.sleep(0.01)
            assert manager.get("a1").status == "complete"

            question = QuestionRequest(
                document_id="doc-fixture",
                analysis_id="a1",
                document_revision=1,
                question="What may the provider change?",
                output_language="en",
                client_request_id="q-blocking",
            )
            question_task = asyncio.create_task(manager.answer_question(question))
            await asyncio.wait_for(engine.answer_started.wait(), timeout=2)

            queued = await manager.submit(AnalysisRequest.model_validate(make_request("a2")))
            assert queued.status == "queued"
            await asyncio.sleep(0.05)
            assert manager.get("a2").status == "queued"
            assert engine.max_active_generation_calls == 1

            engine.answer_release.set()
            answer = await asyncio.wait_for(question_task, timeout=2)
            assert answer.answer == "The provider may change the terms."
            deadline = time.monotonic() + 3
            while manager.get("a2").status != "complete" and time.monotonic() < deadline:
                await asyncio.sleep(0.01)
            assert manager.get("a2").status == "complete"
            assert engine.max_active_generation_calls == 1
        finally:
            engine.answer_release.set()
            engine.release.set()
            await manager.stop()

    asyncio.run(scenario())

