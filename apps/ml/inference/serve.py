"""Run the pinned llama.cpp server locally with the RTX 5070 Ti backend."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .artifacts import MODEL_FILENAME, MODEL_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--gpu-layers", type=int, default=99)
    parser.add_argument("--executable", type=Path, default=os.environ.get("LLAMA_SERVER"), help="Explicit official llama-server binary for another platform")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("the model server must bind to loopback only")
    if args.port < 1 or args.port > 65535 or args.ctx_size < 512 or args.gpu_layers < 0:
        parser.error("invalid port, context size, or GPU layer count")

    ml_root = Path(__file__).resolve().parents[1]
    model_path = ml_root / "models" / MODEL_FILENAME
    runtime_root = ml_root / "runtime" / "llama-b12000"
    server_candidates = [Path(args.executable)] if args.executable else list(runtime_root.rglob("llama-server.exe" if os.name=="nt" else "llama-server"))
    if not model_path.is_file():
        print(f"MODEL_UNAVAILABLE: verified model file is missing at {model_path}", file=sys.stderr)
        return 2
    if len(server_candidates) != 1 or not server_candidates[0].is_file():
        print(
            "MODEL_UNAVAILABLE: expected exactly one verified llama-server.exe under "
            f"{runtime_root}; found {len(server_candidates)}",
            file=sys.stderr,
        )
        return 2

    server = server_candidates[0]
    environment = os.environ.copy()
    environment["PATH"] = str(server.parent) + os.pathsep + environment.get('PATH', '')
    command = [
        str(server),
        "--model",
        str(model_path),
        "--alias",
        MODEL_NAME,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--ctx-size",
        str(args.ctx_size),
        "--n-gpu-layers",
        str(args.gpu_layers),
        "--parallel",
        "1",
        "--jinja",
        "--no-webui",
    ]
    print(
        f"Starting local llama.cpp {server.parent.name}; bind={args.host}:{args.port}; "
        f"context={args.ctx_size}; gpu_layers={args.gpu_layers}; model={MODEL_NAME}"
    )
    return subprocess.run(command, cwd=server.parent, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
