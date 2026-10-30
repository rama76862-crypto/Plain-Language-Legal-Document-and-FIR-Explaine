"""Run independent synthetic multi-clause fixtures through the real local service."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from apps.ml.service.contracts import AnalysisRequest

ROOT = Path(__file__).resolve().parents[3]
ML_DIR = ROOT / "apps" / "ml"
FIXTURE_DIR = ML_DIR / "evaluation" / "fixtures"
DEFAULT_FIXTURES = (
    "agreement_ordinary_en.json",
    "agreement_attention_en.json",
    "notice_en.json",
    "fir_fictional_redacted_en.json",
)


class _FixtureProgress:
    def __init__(self) -> None:
        try:
            from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
        except ImportError:
            self._progress = None
            self._tasks: dict[str, int] = {}
            self._last: dict[str, tuple[object, ...]] = {}
        else:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                transient=False,
            )
            self._tasks = {}
            self._last = {}

    def start(self) -> None:
        if self._progress is not None:
            self._progress.start()

    def update(self, fixture_id: str, snapshot: dict[str, Any]) -> None:
        progress = snapshot.get("progress", {})
        completed = int(progress.get("completed_clauses", 0))
        total = int(progress.get("total_clauses", 0))
        failed = int(progress.get("failed_clauses", 0))
        stage = str(progress.get("stage") or "unknown")
        status = str(snapshot.get("status") or "unknown")
        signature = (status, completed, total, stage, failed)
        if self._progress is not None:
            task = self._tasks.get(fixture_id)
            if task is None:
                task = self._progress.add_task(f"{fixture_id}: {stage}; failed={failed}", total=total)
                self._tasks[fixture_id] = task
            self._progress.update(
                task,
                total=total,
                completed=completed,
                description=f"{fixture_id}: {status}/{stage}; failed={failed}",
            )
        elif self._last.get(fixture_id) != signature:
            print(
                f"local fixture {fixture_id}: {status} clauses={completed}/{total} stage={stage} failed={failed}",
                flush=True,
            )
        self._last[fixture_id] = signature

    def stop(self) -> None:
        if self._progress is not None:
            self._progress.stop()


def _request_from_fixture(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("synthetic") is not True or fixture.get("independent_of_training") is not True:
        raise ValueError(f"fixture is not labelled synthetic and independent: {path.name}")
    request = AnalysisRequest(
        document_id=fixture["document_id"],
        analysis_id=fixture["analysis_id"],
        document_revision=fixture["document_revision"],
        document_type=fixture["document_type"],
        input_language=fixture["source_language"],
        output_language=fixture["output_language"],
        clauses=[
            {
                "clause_id": clause["clause_id"],
                "reviewed_text": clause["reviewed_text"],
            }
            for clause in fixture["clauses"]
        ],
    )
    return fixture, request.model_dump(mode="json")


def _audit_fixture_result(fixture: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    sources = {clause["clause_id"]: clause for clause in fixture["clauses"]}
    items_by_clause: dict[str, list[dict[str, Any]]] = {}
    for item in result.get("items", []):
        items_by_clause.setdefault(item.get("clause_id", ""), []).append(item)

    clause_audits = []
    for clause_id, source in sources.items():
        items = items_by_clause.get(clause_id, [])
        evidence_quotes = [
            evidence.get("quote", "")
            for item in items
            for evidence in item.get("evidence", [])
            if evidence.get("clause_id") == clause_id
        ]
        expected = source["expected"]
        actual_attention = sorted(
            item.get("category") for item in items if item.get("kind") == "attention"
        )
        clause_audits.append(
            {
                "clause_id": clause_id,
                "source_text": source["reviewed_text"],
                "items": items,
                "expected_attention_categories": sorted(expected["attention_categories"]),
                "actual_attention_categories": actual_attention,
                "attention_category_match": actual_attention == sorted(expected["attention_categories"]),
                "all_attached_quotes_are_exact_source_substrings": bool(evidence_quotes)
                and all(quote and quote in source["reviewed_text"] for quote in evidence_quotes),
                "human_semantic_review_questions": expected["human_review_required"],
                "unsupported_claims": None,
                "omissions": None,
                "semantic_review_status": "pending independent human source review",
            }
        )
    return {
        "clause_audits": clause_audits,
        "unsupported_claims_or_omissions": "not inferred from quote presence; review each explanation against full source using the listed questions",
    }


def run_smoke(fixture_names: list[str], timeout_seconds: float) -> dict[str, Any]:
    fixture_payloads = [_request_from_fixture(FIXTURE_DIR / name) for name in fixture_names]
    host, port = "127.0.0.1", 8001
    try:
        with socket.create_connection((host, port), timeout=0.2):
            raise RuntimeError(f"{host}:{port} is already in use; stop the existing private service")
    except OSError:
        pass

    log_path = ML_DIR / "runtime" / "real-multiclause-service.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process: subprocess.Popen[bytes] | None = None
    deadline = time.monotonic() + timeout_seconds
    progress_display = _FixtureProgress()
    health_latencies_ms: list[float] = []
    reports: list[dict[str, Any]] = []

    with log_path.open("wb") as server_log:
        process = subprocess.Popen(
            [sys.executable, "-m", "apps.ml.service"],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=server_log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            with httpx.Client(
                base_url=f"http://{host}:{port}",
                timeout=httpx.Timeout(8.0, connect=1.0),
            ) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"private service exited (code {process.returncode}); see {log_path}")
                    try:
                        response = client.get("/internal/health")
                        if response.status_code == 200 and response.json().get("status") == "ready":
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.2)
                else:
                    raise TimeoutError("private service did not become ready before the smoke deadline")

                progress_display.start()
                for fixture, payload in fixture_payloads:
                    accepted = client.post("/internal/analyse", json=payload)
                    if accepted.status_code != 202:
                        error = accepted.json().get("error", {})
                        raise RuntimeError(f"fixture was rejected: {error.get('code', accepted.status_code)}")
                    analysis_id = payload["analysis_id"]
                    observed_progress: list[dict[str, Any]] = []
                    while time.monotonic() < deadline:
                        response = client.get(f"/internal/jobs/{analysis_id}")
                        if response.status_code != 200:
                            raise RuntimeError(f"job polling failed with HTTP {response.status_code}")
                        snapshot = response.json()
                        progress_display.update(fixture["fixture_id"], snapshot)
                        observed_progress.append(snapshot.get("progress", {}))
                        started = time.perf_counter()
                        health = client.get("/internal/health")
                        health_latencies_ms.append((time.perf_counter() - started) * 1000)
                        if health.status_code != 200:
                            raise RuntimeError("health stopped responding during local analysis")
                        if snapshot.get("status") in {"complete", "needs_review", "failed"}:
                            break
                        time.sleep(0.1)
                    else:
                        raise TimeoutError(f"fixture {fixture['fixture_id']} exceeded the smoke deadline")

                    result = snapshot.get("result")
                    if not isinstance(result, dict):
                        result = None
                    if result is not None and result.get("analysis_id") != analysis_id:
                        raise RuntimeError("result analysis_id does not match the submitted fixture")
                    if result is not None and result.get("coverage", {}).get("total") != len(fixture["clauses"]):
                        raise RuntimeError("result coverage does not include every fixture clause")

                    question_report = None
                    if fixture.get("unsupported_questions") and result is not None:
                        question_data = fixture["unsupported_questions"][0]
                        question_response = client.post(
                            "/internal/question",
                            json={
                                "document_id": payload["document_id"],
                                "analysis_id": analysis_id,
                                "document_revision": payload["document_revision"],
                                "question": question_data["question"],
                                "output_language": payload["output_language"],
                                "client_request_id": f"{fixture['fixture_id']}-unsupported-question",
                            },
                        )
                        question_report = {
                            "http_status": question_response.status_code,
                            "answer": question_response.json() if question_response.status_code == 200 else None,
                            "expected_insufficient_evidence": question_data["expected_status"] == "insufficient_evidence",
                        }

                    deletion = client.delete(f"/internal/jobs/{analysis_id}")
                    after_delete = client.get(f"/internal/jobs/{analysis_id}")
                    reports.append(
                        {
                            "fixture_id": fixture["fixture_id"],
                            "fixture_label": fixture["fixture_label"],
                            "synthetic": True,
                            "analysis_id": analysis_id,
                            "status": snapshot.get("status"),
                            "progress_samples": observed_progress,
                            "result": result,
                            "audit": _audit_fixture_result(fixture, result) if result is not None else None,
                            "unsupported_question": question_report,
                            "delete_http_status": deletion.status_code,
                            "after_delete_http_status": after_delete.status_code,
                        }
                    )
                progress_display.stop()
        finally:
            progress_display.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    return {
        "status": "complete" if all(item["status"] == "complete" for item in reports) else "needs_review",
        "model_mode": "real local llama.cpp; no external inference",
        "fixture_ids": [item["fixture_id"] for item in reports],
        "fixture_count": len(reports),
        "clause_count": sum(
            len(fixture[0]["clauses"]) for fixture in fixture_payloads
        ),
        "health_checks_during_analysis": len(health_latencies_ms),
        "health_max_latency_ms": round(max(health_latencies_ms, default=0.0), 2),
        "reports": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        action="append",
        dest="fixtures",
        help="synthetic fixture filename; repeat to select multiple (defaults to all four English document fixtures)",
    )
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ML_DIR / "runtime" / "real-multiclause-smoke.json",
    )
    args = parser.parse_args()
    try:
        report = run_smoke(args.fixtures or list(DEFAULT_FIXTURES), args.timeout_seconds)
    except (RuntimeError, TimeoutError, ValueError) as exc:
        print(f"real multi-clause smoke failed: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"real local multi-clause smoke finished: status={report['status']} "
        f"fixtures={report['fixture_count']} clauses={report['clause_count']} "
        f"health_checks={report['health_checks_during_analysis']} "
        f"max_health_ms={report['health_max_latency_ms']} output={args.output}",
        flush=True,
    )
    return 0 if report["status"] in {"complete", "needs_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
