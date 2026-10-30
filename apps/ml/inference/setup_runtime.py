"""Download and verify the pinned local Qwen GGUF and official llama.cpp zip.

Run from the repository root with `python -m apps.ml.inference.setup_runtime`.
All payloads are placed under ignored apps/ml/models or apps/ml/runtime paths.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import math
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .artifacts import (
    LLAMA_BINARY_FILENAME,
    LLAMA_BINARY_SHA256,
    LLAMA_BINARY_SIZE_BYTES,
    LLAMA_CUDA_FILENAME,
    LLAMA_CUDA_SHA256,
    LLAMA_CUDA_SIZE_BYTES,
    LLAMA_RELEASE_URL,
    MODEL_FILENAME,
    MODEL_RESOLVE_URL,
    MODEL_SHA256,
    MODEL_SIZE_BYTES,
)


CHUNK_SIZE = 1024 * 1024
RANGE_SIZE = 32 * 1024 * 1024
DOWNLOAD_WORKERS = 8
ML_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ML_ROOT / "runtime"
DOWNLOAD_ROOT = RUNTIME_ROOT / "downloads"
RUNTIME_INSTALL_ROOT = RUNTIME_ROOT / "llama-b12000"
MODEL_ROOT = ML_ROOT / "models"


def _format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GiB"


def _print_progress(label: str, received: int, total: int | None) -> None:
    if total and total > 0:
        width = 24
        fraction = min(received / total, 1.0)
        filled = int(width * fraction)
        bar = "#" * filled + "-" * (width - filled)
        line = (
            f"\r{label}: [{bar}] {fraction * 100:5.1f}% "
            f"{_format_bytes(received)}/{_format_bytes(total)}"
        )
    else:
        spinner = "|/-\\"[(received // CHUNK_SIZE) % 4]
        line = f"\r{label}: {spinner} {_format_bytes(received)} received (total unavailable)"
    sys.stdout.write(line)
    sys.stdout.flush()


class DownloadProgress:
    """Render measured download bytes with Rich or a plain terminal fallback."""

    def __init__(self, label: str, total: int) -> None:
        self.label = label
        self.total = total
        self._lock = threading.Lock()
        self._last_plain_bytes = -1
        self._progress = None
        self._task_id = None
        if not sys.stderr.isatty():
            return
        try:
            from rich.console import Console
            from rich.progress import (
                BarColumn,
                DownloadColumn,
                Progress,
                TaskProgressColumn,
                TextColumn,
                TimeElapsedColumn,
                TransferSpeedColumn,
            )
        except ImportError:
            return
        self._progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
            console=Console(stderr=True, legacy_windows=True),
        )
        self._progress.start()
        self._task_id = self._progress.add_task(label, total=total)

    def update(self, received: int) -> None:
        with self._lock:
            received = min(max(received, 0), self.total)
            if self._progress is not None and self._task_id is not None:
                self._progress.update(self._task_id, completed=received)
                return
            interval = max(16 * 1024 * 1024, self.total // 20)
            if (
                self._last_plain_bytes < 0
                or received - self._last_plain_bytes >= interval
                or received >= self.total
            ):
                print(
                    f"{self.label}: {received}/{self.total} bytes "
                    f"({_format_bytes(received)}/{_format_bytes(self.total)})",
                    file=sys.stderr,
                    flush=True,
                )
                self._last_plain_bytes = received

    def close(self) -> None:
        if self._progress is not None:
            self._progress.stop()


def _download(
    label: str,
    url: str,
    destination: Path,
    expected_size: int,
    expected_sha256: str,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        actual_size = destination.stat().st_size
        digest = _sha256(destination)
        if actual_size == expected_size and digest == expected_sha256:
            print(f"{label}: already present; SHA-256 verified ({digest})")
            return destination
        raise RuntimeError(f"{label}: existing file failed size/hash verification")

    partial_path = destination.with_suffix(destination.suffix + ".part")
    parts_root = destination.with_name(destination.name + ".parts")
    if partial_path.exists() and partial_path.stat().st_size == expected_size:
        digest = _sha256(partial_path)
        if digest == expected_sha256:
            partial_path.replace(destination)
            print(f"{label}: resumed file already complete; SHA-256 verified ({digest})")
            return destination
        partial_path.unlink()
    chunk_count = math.ceil(expected_size / RANGE_SIZE)
    parts_root.mkdir(parents=True, exist_ok=True)

    # Convert a sequential partial from an interrupted earlier run into ranges.
    # Existing bytes are retained and counted as already received.
    if partial_path.exists():
        old_size = min(partial_path.stat().st_size, expected_size)
        with partial_path.open("rb") as old_file:
            for index in range(chunk_count):
                start = index * RANGE_SIZE
                if start >= old_size:
                    break
                end = min(start + RANGE_SIZE, expected_size) - 1
                part_path = parts_root / f"{index:05d}.part"
                remaining = min(end + 1, old_size) - start
                with part_path.open("wb") as part_file:
                    old_file.seek(start)
                    copied = 0
                    while copied < remaining:
                        data = old_file.read(min(CHUNK_SIZE, remaining - copied))
                        if not data:
                            break
                        part_file.write(data)
                        copied += len(data)
        partial_path.unlink()

    def range_bounds(index: int) -> tuple[int, int]:
        start = index * RANGE_SIZE
        end = min(start + RANGE_SIZE, expected_size) - 1
        return start, end

    initial_done = 0
    for index in range(chunk_count):
        _, end = range_bounds(index)
        part_path = parts_root / f"{index:05d}.part"
        if part_path.exists():
            size = part_path.stat().st_size
            chunk_length = end - range_bounds(index)[0] + 1
            if size > chunk_length:
                part_path.unlink()
            else:
                initial_done += size
    state = {"done": initial_done, "last_printed": initial_done, "last_time": time.monotonic()}
    progress_lock = threading.Lock()
    reporter = DownloadProgress(label, expected_size)
    reporter.update(initial_done)

    def fetch_range(index: int) -> None:
        start, end = range_bounds(index)
        part_path = parts_root / f"{index:05d}.part"
        expected_chunk_bytes = end - start + 1
        existing = part_path.stat().st_size if part_path.exists() else 0
        if existing > expected_chunk_bytes:
            part_path.unlink()
            existing = 0
        if existing == expected_chunk_bytes:
            return

        request_start = start + existing
        headers = {
            "User-Agent": "NyayaLens-Backend2-local-setup/1.0",
            "Accept-Encoding": "identity",
            "Range": f"bytes={request_start}-{end}",
        }
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                content_range = response.headers.get("Content-Range", "")
                if status != 206 or not content_range.startswith(f"bytes {request_start}-"):
                    raise RuntimeError(f"{label}: source did not honor byte range {index}")
                expected_range_suffix = f"/{expected_size}"
                if not content_range.endswith(expected_range_suffix):
                    raise RuntimeError(f"{label}: source reported an unexpected range total")
                mode = "ab" if existing else "wb"
                with part_path.open(mode) as output:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        output.write(chunk)
                        with progress_lock:
                            state["done"] += len(chunk)
                            now = time.monotonic()
                            if (
                                state["done"] - state["last_printed"] >= 8 * CHUNK_SIZE
                                or now - state["last_time"] >= 1.0
                            ):
                                reporter.update(state["done"])
                                state["last_printed"] = state["done"]
                                state["last_time"] = now
        except RuntimeError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"{label}: range {index} failed ({type(exc).__name__})") from exc
        if part_path.stat().st_size != expected_chunk_bytes:
            raise RuntimeError(f"{label}: byte count mismatch for range {index}")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
            futures = [executor.submit(fetch_range, index) for index in range(chunk_count)]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        with partial_path.open("wb") as output:
            assembled = 0
            for index in range(chunk_count):
                part_path = parts_root / f"{index:05d}.part"
                with part_path.open("rb") as part_file:
                    while chunk := part_file.read(CHUNK_SIZE):
                        output.write(chunk)
                        assembled += len(chunk)
            if assembled != expected_size:
                raise RuntimeError(
                    f"{label}: assembled byte count {assembled} does not match {expected_size}"
                )
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(f"{label}: download failed ({type(exc).__name__})") from exc
    finally:
        with progress_lock:
            reporter.update(state["done"])
        reporter.close()

    if partial_path.stat().st_size != expected_size:
        raise RuntimeError(
            f"{label}: byte count mismatch; received {partial_path.stat().st_size}, "
            f"expected {expected_size}"
        )
    digest = _sha256(partial_path)
    if digest != expected_sha256:
        raise RuntimeError(f"{label}: SHA-256 mismatch ({digest})")
    partial_path.replace(destination)
    for part_path in parts_root.glob("*.part"):
        part_path.unlink()
    parts_root.rmdir()
    print(f"{label}: verified SHA-256 {digest}")
    return destination


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            normalized = PurePosixPath(member.filename)
            if normalized.is_absolute() or ".." in normalized.parts:
                raise RuntimeError(f"unsafe path in official runtime archive: {member.filename}")
            target = (destination / Path(*normalized.parts)).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"runtime archive path escaped destination: {member.filename}")
        for member in archive.infolist():
            target=destination / Path(*PurePosixPath(member.filename).parts)
            if not member.is_dir() and target.is_file() and target.stat().st_size==member.file_size:
                # Repeated setup must not overwrite DLLs held by a live model.
                with target.open('rb') as installed, archive.open(member) as bundled:
                    if hashlib.file_digest(installed,'sha256').digest()==hashlib.file_digest(bundled,'sha256').digest():
                        continue
            archive.extract(member,destination)


def _download_runtime() -> None:
    binary_zip = _download(
        "llama.cpp Windows CUDA 13.4 binary",
        f"{LLAMA_RELEASE_URL}/{LLAMA_BINARY_FILENAME}",
        DOWNLOAD_ROOT / LLAMA_BINARY_FILENAME,
        LLAMA_BINARY_SIZE_BYTES,
        LLAMA_BINARY_SHA256,
    )
    cuda_zip = _download(
        "llama.cpp CUDA 13.4 runtime DLLs",
        f"{LLAMA_RELEASE_URL}/{LLAMA_CUDA_FILENAME}",
        DOWNLOAD_ROOT / LLAMA_CUDA_FILENAME,
        LLAMA_CUDA_SIZE_BYTES,
        LLAMA_CUDA_SHA256,
    )
    _safe_extract(binary_zip, RUNTIME_INSTALL_ROOT)
    _safe_extract(cuda_zip, RUNTIME_INSTALL_ROOT)
    print(f"Runtime archives extracted to {RUNTIME_INSTALL_ROOT}")


def _download_model() -> None:
    _download(
        "Qwen3-4B-Instruct-2507 Q4_K_M GGUF",
        MODEL_RESOLVE_URL,
        MODEL_ROOT / MODEL_FILENAME,
        MODEL_SIZE_BYTES,
        MODEL_SHA256,
    )


def _runtime_members() -> list[str]:
    if not RUNTIME_INSTALL_ROOT.exists():
        return []
    return [
        str(path.relative_to(RUNTIME_INSTALL_ROOT))
        for path in RUNTIME_INSTALL_ROOT.rglob("llama-server.exe")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assets",
        choices=("all", "runtime", "model"),
        default="all",
        help="choose which pinned local assets to download",
    )
    args = parser.parse_args()

    if args.assets in {"all", "runtime"}:
        _download_runtime()
    if args.assets in {"all", "model"}:
        _download_model()

    if args.assets in {"all", "runtime"}:
        server_paths = _runtime_members()
        if not server_paths:
            raise RuntimeError("verified archive did not contain llama-server.exe")
        print(f"llama-server executable: {RUNTIME_INSTALL_ROOT / server_paths[0]}")
    if args.assets in {"all", "model"}:
        model_path = MODEL_ROOT / MODEL_FILENAME
        if not model_path.is_file():
            raise RuntimeError("verified model GGUF was not installed")
        print(f"model GGUF: {model_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, zipfile.BadZipFile) as exc:
        print(f"setup error: {exc}", file=sys.stderr)
        raise SystemExit(1)
