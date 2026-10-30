"""Run a synthetic agreement clause through the real local service stack."""

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

from apps.ml.inference.artifacts import MODEL_VERSION
from apps.ml.inference.smoke import SYNTHETIC_CLAUSE
from apps.ml.training.model import UnfairToSClassifier


FIXTURE_ID = "synthetic-be2-service-smoke-001"
FIXTURE_CLAUSE_ID = "clause-change-001"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "synthetic_reviewed_agreement_request.json"


def _payload() -> dict[str, Any]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if payload["analysis_id"] != FIXTURE_ID or payload["clauses"][0]["reviewed_text"] != SYNTHETIC_CLAUSE:
        raise RuntimeError("the tracked service request fixture no longer matches the labelled smoke clause")
    return payload


class _ClauseProgress:
    """Display only the actual clause counts and stage reported by the service."""

    def __init__(self, total: int) -> None:
        try:
            from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
        except ImportError:
            self._progress = None
            self._task = None
            self._last_signature: tuple[object, ...] | None = None
        else:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                transient=False,
            )
            self._task = self._progress.add_task("queued", total=total)
            self._last_signature = None

    def start(self) -> None:
        if self._progress is not None:
            self._progress.start()

    def update(self, snapshot: dict[str, Any]) -> None:
        progress = snapshot.get("progress", {})
        completed = int(progress.get("completed_clauses", 0))
        total = int(progress.get("total_clauses", 0))
        failed = int(progress.get("failed_clauses", 0))
        stage = str(progress.get("stage") or "unknown")
        status = str(snapshot.get("status") or "unknown")
        description = f"{status}: {stage}; failed={failed}"
        if self._progress is not None:
            self._progress.update(self._task, total=total, completed=completed, description=description)
            return
        signature = (status, completed, total, stage, failed)
        if signature != self._last_signature:
            print(f"service smoke: {status} clauses={completed}/{total} stage={stage} failed={failed}", flush=True)
            self._last_signature = signature

    def stop(self) -> None:
        if self._progress is not None:
            self._progress.stop()


def _assert_trained_classifier_fixture() -> None:
    classifier = UnfairToSClassifier.load()
    detected = {
        prediction.label
        for prediction in classifier.predict(SYNTHETIC_CLAUSE).predictions
        if prediction.detected
    }
    if "unilateral_change" not in detected:
        raise RuntimeError(
            "the saved classifier did not detect the labelled synthetic unilateral-change fixture"
        )


def run_service_smoke(timeout_seconds: float = 300.0) -> dict[str, Any]:
    _assert_trained_classifier_fixture()
    host = "127.0.0.1"
    port = 8001
    try:
        with socket.create_connection((host, port), timeout=0.2):
            raise RuntimeError(f"{host}:{port} is already in use; stop that service before running this smoke")
    except OSError:
        pass

    ml_root = Path(__file__).resolve().parents[1]
    repository_root = ml_root.parents[1]
    log_path = ml_root / "runtime" / "service-smoke-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process: subprocess.Popen[bytes] | None = None
    deadline = time.monotonic() + timeout_seconds
    stages: list[str] = []
    health_latencies_ms: list[float] = []
    last_progress: tuple[object, ...] | None = None
    snapshot: dict[str, Any] = {}
    result: dict[str, Any] = {}
    after_delete_status = 0
    terminal_progress = _ClauseProgress(len(_payload()["clauses"]))

    with log_path.open("wb") as server_log:
        process = subprocess.Popen(
            [sys.executable, "-m", "apps.ml.service"],
            cwd=repository_root,
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
                health: dict[str, Any] = {}
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(
                            f"private service exited during startup (code {process.returncode}); see {log_path}"
                        )
                    try:
                        health_response = client.get("/internal/health")
                        if health_response.status_code == 200:
                            health = health_response.json()
                            if health.get("status") == "ready":
                                break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.2)
                else:
                    raise TimeoutError("private service did not become ready before the smoke deadline")

                accepted = client.post("/internal/analyse", json=_payload())
                if accepted.status_code != 202:
                    body = accepted.json().get("error", {})
                    raise RuntimeError(f"analysis was not accepted: {body.get('code', 'unknown error')}")
                if accepted.json().get("analysis_id") != FIXTURE_ID:
                    raise RuntimeError("the service did not echo BE1's supplied analysis_id")

                terminal_progress.start()
                while time.monotonic() < deadline:
                    polled = client.get(f"/internal/jobs/{FIXTURE_ID}")
                    if polled.status_code != 200:
                        raise RuntimeError(f"job polling failed with HTTP {polled.status_code}")
                    snapshot = polled.json()
                    progress = snapshot.get("progress", {})
                    signature = (
                        snapshot.get("status"),
                        progress.get("completed_clauses"),
                        progress.get("total_clauses"),
                        progress.get("stage"),
                        progress.get("failed_clauses"),
                    )
                    if signature != last_progress:
                        last_progress = signature
                        stage = progress.get("stage") or "unknown"
                        stages.append(stage)
                    terminal_progress.update(snapshot)

                    health_started = time.perf_counter()
                    concurrent_health = client.get("/internal/health")
                    health_latencies_ms.append((time.perf_counter() - health_started) * 1000.0)
                    if concurrent_health.status_code != 200:
                        raise RuntimeError("health endpoint stopped responding during analysis")

                    if snapshot.get("status") in {"complete", "needs_review", "failed"}:
                        break
                    time.sleep(0.25)
                else:
                    raise TimeoutError(f"service fixture exceeded {timeout_seconds:g} seconds")

                if snapshot.get("status") == "failed":
                    warning_codes = [
                        warning.split(":", 1)[0]
                        for warning in snapshot.get("warnings", [])
                        if isinstance(warning, str)
                    ]
                    raise RuntimeError(f"analysis failed: {', '.join(warning_codes) or 'unspecified'}")

                result_payload = snapshot.get("result")
                if not isinstance(result_payload, dict):
                    raise RuntimeError("completed service job did not contain an analysis result")
                result = result_payload
                if result.get("analysis_id") != FIXTURE_ID or result.get("document_revision") != 1:
                    raise RuntimeError("result identifiers do not match the accepted request")
                if result.get("coverage") != {"analysed": 1, "total": 1}:
                    raise RuntimeError("the fixture did not pass full clause-level result validation")
                items = result.get("items", [])
                if not items or not any(
                    item.get("detector") == "classifier"
                    and item.get("category") == "unilateral_change"
                    and any(
                        evidence.get("clause_id") == FIXTURE_CLAUSE_ID
                        and evidence.get("quote") == SYNTHETIC_CLAUSE
                        for evidence in item.get("evidence", [])
                    )
                    for item in items
                ):
                    raise RuntimeError(
                        "the final result lacks a classifier cue grounded by the exact synthetic source quote"
                    )
                if not result.get("provenance", {}).get("generator"):
                    raise RuntimeError("the result does not identify the local generator")

                deleted = client.delete(f"/internal/jobs/{FIXTURE_ID}")
                if deleted.status_code != 204:
                    raise RuntimeError("the completed fixture could not be deleted")
                after_delete = client.get(f"/internal/jobs/{FIXTURE_ID}")
                after_delete_status = after_delete.status_code
                if after_delete_status != 410:
                    raise RuntimeError("the deleted fixture was not tombstoned")
        finally:
            terminal_progress.stop()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    report = {
        "fixture_id": FIXTURE_ID,
        "fixture_label": "synthetic reviewed agreement clause",
        "classifier_label": "unilateral_change",
        "generator_artifact": MODEL_VERSION,
        "service_status": snapshot.get("status"),
        "coverage": result["coverage"],
        "evidence_validated": True,
        "analysis_id_echoed": True,
        "health_checks_during_poll": len(health_latencies_ms),
        "health_max_latency_ms": round(max(health_latencies_ms, default=0.0), 2),
        "observed_stages": stages,
        "deletion_tombstone_http_status": after_delete_status,
        "actual_local_result": result,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "runtime" / "service-smoke-result.json",
    )
    args = parser.parse_args()
    try:
        report = run_service_smoke(args.timeout_seconds)
    except (RuntimeError, TimeoutError, ValueError) as exc:
        print(f"real service smoke failed: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "real end-to-end service smoke completed: "
        f"status={report['service_status']} "
        f"fixture={FIXTURE_ID} coverage={report['coverage']['analysed']}/"
        f"{report['coverage']['total']} health_checks={report['health_checks_during_poll']} "
        f"max_health_ms={report['health_max_latency_ms']} "
        f"deleted_http={report['deletion_tombstone_http_status']} result_file={args.output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
