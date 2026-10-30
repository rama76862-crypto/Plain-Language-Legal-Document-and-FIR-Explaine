"""Run the private ML service on loopback."""

from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "apps.ml.service.app:app",
        host="127.0.0.1",
        port=int(os.environ.get("ML_PORT", "8001")),
        workers=1,
        log_level="info",
    )

