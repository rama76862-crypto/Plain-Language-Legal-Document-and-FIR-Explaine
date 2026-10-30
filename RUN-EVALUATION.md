# Run NyayaLens for evaluation

Run commands from the repository root. Use existing services when already running; do not launch duplicates. This records the integration handoff, not a claim of independently validated legal explanations.

## Working local URLs from the reported integration

- Frontend: http://127.0.0.1:5173/
- Public BE1 health: http://127.0.0.1:8000/api/v1/health
- Private BE2 health: http://127.0.0.1:8001/internal/health
- Local model health: http://127.0.0.1:8080/health

## Fresh startup: separate PowerShell terminals

1. Local model:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.inference.serve
```

2. Private ML service:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.service
```

3. Public API:

```powershell
$env:ML_MODE='real'
$env:ML_BASE_URL='http://127.0.0.1:8001'
$env:API_PORT='8000'
$env:WEB_ORIGIN='http://127.0.0.1:5173'
$env:RUNTIME_DIR='work/runtime/be1'
.\.venv-api\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

4. Frontend, after dependency setup:

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Keep VITE_USE_FIXTURES=false and the frontend /api proxy aimed at the public API. Private model/ML ports remain loopback-only. See each backend README if ignored model/classifier/environment assets must be recreated.

## Reproduce the real API check

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --mode real --kind pdf
```

The reported passing run exercised synthetic upload, native extraction, explicit review, real local analysis, grounded and unsupported questions, and public/private deletion. The subsequently added health probe requires a new run before its result is claimed.

## Demonstration and open limits

Use a short native-text synthetic/redacted PDF. Show extraction, review, processing counts, source evidence, needs_review, grounded/unsupported questions and deletion. No semantic or fluent-language review has passed; do not describe a transport test as legal accuracy. OCR is currently unavailable on this host. A browser-driven end-to-end journey remains open, and the frontend completion gaps remain documented in FRONTEND-AUDIT.md.

Do not stop existing running services after verification. INTEGRATION-PROGRESS.md separates recorded evidence from outstanding checks.
