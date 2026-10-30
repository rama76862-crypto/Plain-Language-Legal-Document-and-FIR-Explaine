# NyayaLens Backend 1

Runnable public API for local PDF/DOCX/scanned-PDF extraction, human review, temporary sessions and Backend 2 integration. All ten Contract v1 operations are implemented under `/api/v1`. BE1 can be developed and demonstrated using its own source, this README and `contracts/`; the other three role documents are not runtime dependencies. No frontend, ML service, classifier, translation model or GPU model was created by BE1.

## Verified environment and installation

Tested on Windows PowerShell with CPython **3.12.10**, isolated `.venv-api`. Python 3.11 is also intended, but was not tested here. Run all commands from the repository root (the directory containing the four role documents); do not assume another teammate's drive path.

```powershell
python --version
python -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -r apps/api/requirements.lock.txt
.\.venv-api\Scripts\python.exe -m pip check
```

The lock captures the tested Windows/Python 3.12 environment, including transitive packages. Other OS/Python combinations require their own compatibility check. Direct dependencies used: FastAPI, Pydantic, Uvicorn, HTTPX, python-multipart, PyMuPDF and python-docx; pytest/pytest-asyncio for checks. OCR invokes the installed Tesseract executable directly; Pillow/pytesseract are installed for the parser/OCR test environment. Native PDF extraction uses PyMuPDF's text-block path, with no AI layout call or model download. PyMuPDF is AGPL/commercial licensed; team must confirm its distribution obligations. Third-party versions are pinned in `requirements.lock.txt`.

## Configuration and startup

See `.env.example`; it is a shell configuration template, **not automatically loaded**. Defaults use local loopback, real ML mode and no secret. Settings reject invalid ports, origins, nonpositive/nonfinite limits and unsafe runtime roots/links. Use a dedicated private runtime directory, never the repository root, public assets, a shared teammate runtime or a linked directory.

```powershell
$env:API_PORT='8000'
$env:WEB_ORIGIN='http://localhost:5173'
$env:ML_BASE_URL='http://127.0.0.1:8001'
$env:RUNTIME_DIR='work/runtime/be1'
$env:ML_MODE='real'
.\.venv-api\Scripts\python.exe -m apps.api
```

The tested launcher binds `127.0.0.1`, runs **one worker**, disables request access logs and prints only safe counts/statuses. Visit `http://127.0.0.1:8000/docs` for interactive OpenAPI; `/openapi.json` is live. Public examples and exported OpenAPI are in `contracts/`.

Final startup order: **LLM → BE2 private ML → BE1 public API → frontend**. FE1 should use a same-origin `/api` proxy. Keep ML/model ports private on the final GPU host. For cross-laptop development, BE2 must supply an agreed trusted-network address/proxy and optional service token. No firewall or service exposure was changed. A deliberate LAN public API launch can use Uvicorn with one worker and an operator-approved binding; that deployment was not tested here.

Required documented variables: `API_PORT`, `WEB_ORIGIN`, `ML_BASE_URL`, optional `ML_SERVICE_TOKEN`, `RUNTIME_DIR`, `MAX_UPLOAD_MB` (10), `MAX_PDF_PAGES` (20), `SESSION_TTL_MINUTES` (30), `MODEL_TIMEOUT_SECONDS` (120). Parser limits: `EXTRACTION_TIMEOUT_SECONDS=120` and `EXTRACTION_MEMORY_MB=768`. Fractional timeout/TTL settings are supported. Additional bounded-resource settings are listed in `.env.example`.

## OCR status and local setup

**App-local Tesseract is installed and real scans are now tested.** The Windows setup downloads pinned upstream Tesseract/7-Zip release assets and `eng`/`hin`/`pan` tessdata, verifies SHA256, extracts installers as archives and never runs their installation actions. No system installation, registry or PATH change is made. All binary assets live in ignored `tools/ocr/`; source-only handoff archives exclude them.

```powershell
.\.venv-api\Scripts\python.exe apps/api/scripts/setup_ocr.py
.\.venv-api\Scripts\python.exe apps/api/scripts/setup_ocr.py --probe
```

Runtime verified here: **Tesseract 5.5.3.20260724**. Full version/source/hash receipt: `tools/ocr/manifest.json`. Pinned source URLs and hashes are also in the setup script. Verified cached assets allow repeat setup without network; a new laptop needs the downloads once. Offline inference/OCR then uses only local files. Other operating systems should install their local Tesseract package; this portable setup is Windows-only.

The parser automatically discovers the local executable. Alternatively set `TESSERACT_CMD` and optional `TESSDATA_PREFIX` for an existing installation. OCR capability is probed without requiring a global `tesseract` command:

```powershell
.\.venv-api\Scripts\python.exe -c "from apps.api.extraction import ocr_capabilities; print(ocr_capabilities())"
.\.venv-api\Scripts\python.exe -m pytest apps/api/tests/test_extraction.py -q -rs
```

The probe returns available with `eng`, `hin`, `pan`. Real English image-only PDF, Hindi image-only PDF and mixed native/scanned PDF checks pass; a selectable header does not suppress OCR of a scanned body. Punjabi produces genuine Gurmukhi text with payment/time anchors, but the synthetic agreement word has an extra nasalization mark: that exact quality check is recorded as an expected failure. This is **experimental Punjabi OCR quality**, not a full legal/language accuracy claim. Every OCR clause is marked for review. Indic tests render the local OS-licensed Nirmala font without redistributing it.

OCR is selective at 150 DPI, bounded to 16 million pixels/page and a 20-second subprocess timeout by default. Missing executables/assets return `OCR_UNAVAILABLE`; errors never substitute made-up extracted text. All OCR/setup child processes are hidden on Windows.

## Parser process isolation

Production extraction runs in one dedicated subprocess per document behind the bounded queue. Private request/result text travels through pipes, never argv/logs/temp JSON. Windows Job Objects cap the parser/OCR process tree to the configured memory limit and kill descendants on timeout, cancellation, deletion and shutdown. POSIX uses a separate process group with address-space/CPU limits; the Windows path is actually tested here, other OS paths require their own run.

A hard document timeout yields `EXTRACTION_TIMEOUT` (504), distinct from a model timeout. Native crashes or memory exhaustion produce safe `EXTRACTION_FAILED` responses; later jobs remain usable. Actual tests cover parser and descendant termination, memory failure/recovery, cancellation and diagnostic suppression. This is resource/process isolation, not a complete OS filesystem/network sandbox.

## Explicit development simulation

Real mode never falls back. To exercise the full transport/lifecycle without BE2, explicitly launch:

```powershell
$env:ML_MODE='fixture'
.\.venv-api\Scripts\python.exe -m apps.api
```

Fixture mode only echoes reviewed source with conspicuous `DEVELOPMENT FIXTURE` warnings and provenance. It ends `needs_review`, records **zero actually analysed clauses**, and identifies every clause as lacking real model analysis. It performs no classification, translation, legal interpretation or real model answer. Health remains degraded and marks simulation. It must not be advertised as a working legal-analysis model.

## Exercised requests and smoke commands

For an independent demonstration that needs no running service or teammate files:

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.standalone_demo
```

It starts owned loopback servers with isolated temporary runtimes, runs real HTTP PDF/DOCX and English scanned-PDF journeys when OCR is available, checks explicit real-model unavailability, deletes all sessions and gracefully stops the servers. It prints actual check counts and a privacy-safe summary with `model_tested:false`. Optional `--json-output <new-file>` writes the summary without overwriting existing files. `--skip-unavailable` omits only the intentionally absent-ML check. Scans are explicitly marked skipped if local OCR is absent. Model results/questions remain labelled simulation.

Both health requests were exercised against the locally running server:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health' | ConvertTo-Json -Depth 6
curl.exe -s http://127.0.0.1:8000/api/v1/health
```

The synthetic smoke client sends actual multipart/JSON requests, keeps tokens in memory and prints only real counts. It creates its PDF/DOCX in memory and deletes each uploaded session in `finally`:

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --mode fixture --kind pdf
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --mode fixture --kind docx
```

Both passed all eight journey checks against an actual Uvicorn server: upload → native extraction → review → source → analysis accepted → validated labelled fixture → question interface → delete/404. This proves HTTP/extraction/lifecycle behavior; **it does not prove model functionality**.

For real-mode extraction without ML (also exercised on port 8002):

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --base-url http://127.0.0.1:8002 --mode real --extraction-only
```

For the final real-ML journey, start the services in order and run:

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --mode real --kind pdf
```

The actual real-service probe reported unavailable, because BE2 is absent/unreachable on localhost:8001. A full real-mode smoke returns exit 2 when readiness is unavailable; no fake result replaces it. A final real agreement/FIR/notice and reviewed language matrix remain required with BE2. The generic synthetic smoke is a contract check, not semantic/legal evaluation.

## API and revision behavior

See `contracts/README.md` for published integration decisions and `contracts/v1-examples.json` for machine-readable synthetic examples. All later document routes use `X-Session-Token`; wrong/missing tokens return the same 404 as unknown documents.

| Method | Path after `/api/v1` | Behavior |
|---|---|---|
| GET | `/health` | Extraction/OCR/model readiness independently, cleanup counts |
| POST | `/documents` | Multipart `file`, `input_language`, `document_type`; 202 |
| GET | `/documents/{id}` | Status/revision/warnings/expiry/review state |
| GET | `/documents/{id}/extraction` | Clauses; 409 while extracting; safe parser error on failure |
| PATCH | `/documents/{id}/extraction` | Expected revision + corrections + confirmed language/type |
| GET | `/documents/{id}/source` | Authenticated original, attachment, correct MIME, no-store |
| POST | `/documents/{id}/analyses` | Reviewed revision/output language; 202 or explicit error |
| GET | `/documents/{id}/analyses/{aid}` | Actual status/progress, validated partial/terminal result |
| POST | `/documents/{id}/questions` | Current analysis, question/language/client request ID |
| DELETE | `/documents/{id}` | Immediate public tombstone; 204; bounded downstream cleanup |

PATCH with empty corrections confirms the current revision. Genuine text/language/type changes increment once and invalidate previous language results/questions/indexes. Unchanged confirmation keeps revision. Active analysis blocks edits with 409. DOCX page numbers remain null; paragraphs including table-cell paragraphs are numbered in document order. PDF page numbers are real and 1-based. Multi-page clauses retain a primary page plus explicit review warning; precise geometry is dropped when invalid.

Errors use `{error:{code,message,retryable},request_id}`, including normalized 422 validation errors without raw input values. Upload type/size checks are authoritative; multipart consumption is capped at file limit plus 1 MB envelope overhead, then actual file bytes at exact file limit. Malformed/encrypted PDFs, DOCX expansion/entry/character limits and missing OCR fail usefully. Original filenames are display-only; server-generated storage names cannot traverse paths.

Active analysis is de-duplicated by document/revision/output language. Terminal results remain accessible by analysis ID with their source revision/language and model/rule provenance; new explicit analyses start new jobs rather than reusing a possibly outdated model-version result. A document is capped at 32 known analysis jobs, 100 distinct question IDs and the service at 128 sessions, with additional cleanup/admission bounds. BE2 remains GPU queue authority. Different output languages have separate jobs. No automatic browser mutation retries are needed. Question retries with the same ID/payload share work; conflicting reuse returns 409. After failure/timeout, explicit retry uses the same ID so BE2 can deduplicate ambiguous deliveries too.

## Retention, deletion and shutdown

Default inactivity retention is 30 minutes. Automatic metadata/extraction/analysis polling does not extend it. Explicit review, analysis, question and source requests extend it. Background computation does not extend it. Metadata exposes a real UTC `expires_at`; no reset endpoint is added.

DELETE/expiry tombstones first, clears in-memory private state, cancels pending work and discards late outputs. Every known BE2 analysis ID (including old revisions/languages) is scheduled for cleanup. Local Windows file-sharing failures and private HTTP failures retain metadata-only retry work. Five attempts, with 2/4/8/16-second minimum backoff plus maintenance scheduling; private cleanup batches are at most four. Pending/exhausted counts appear in health. **204 confirms public deletion, not verified downstream erasure.** Exhausted cleanup requires operator action/restart review. No private text/token/credential is logged.

State/jobs/retry metadata are single-process and do not survive restart. Startup acquires an exclusive OS lock on `.be1.lock` before any orphan cleanup; a competing process on the same runtime fails before touching uploads. The lock file remains and is safely reusable after release/process exit. Startup removes only verified direct server-generated `doc_<32 hex>` runtime directories, refuses roots/links/junctions, and leaves unrelated files alone. BE2 must expire private results independently because a BE1 crash loses private cleanup retry IDs. Shutdown attempts cleanup; hard process termination can leave orphans for next startup. User-created exports remain separate copies. There is no claim of forensic secure erasure.

## Tests and contract export

```powershell
New-Item -ItemType Directory -Path work/verification -Force | Out-Null
.\.venv-api\Scripts\python.exe -m pytest -q --basetemp=work/verification/pytest-run -o cache_dir=work/verification/pytest-cache
.\.venv-api\Scripts\python.exe -m pip check
.\.venv-api\Scripts\python.exe -m apps.api.scripts.export_contracts
```

Latest suite: **114 passed, 1 skipped, 1 expected failure**. The skip is actual Windows symlink creation without privileges; mocked link detection still passes. The expected failure is the documented Punjabi synthetic OCR word error. English and Hindi scan checks pass. One upstream Starlette TestClient/httpx deprecation warning is present; HTTPX adapter and live HTTP smoke pass. No package change was made solely to suppress that warning. The workspace-specific test directories avoid permission conflicts with older Windows temp/cache folders; they contain only synthetic verification data and are ignored by Git.

Coverage includes native parsers/order/source references, malformed/encrypted/oversized/archive limits, review/revisions, token isolation, HTTP adapter identity/evidence/reference rejection, partial results, language variants, simultaneous question deduplication, busy/timeout responsiveness, delete during extraction/private start, all-language cleanup/retry, expiry/orphans, logs and nonfallback behavior. MockTransport tests prove the HTTP contract only.

Known limits: process/memory/time limits do not eliminate every hostile-parser risk. Full multilingual correctness and FIR/allegation semantics require BE2/human evaluation. Official reference validation checks curated IDs, HTTPS government hostnames and exact evidence; it does not independently verify the current contents of a legal source. No extra interpretation/classifier/translation is implemented in BE1.

## Source-only handoff package

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.package_handoff --output work/demo-results/be1-handoff.zip
```

This packages only BE1 source/tests/docs, public contracts, the BE1 handoff and minimal root configuration, with a SHA256 manifest. Runtime uploads, `.env`, caches, OCR binaries, downloaded weights, frontend/ML code and other role documents are excluded. Existing output files are preserved; choose a new filename for another package. Recipient installs pinned Python dependencies, optionally runs app-local OCR setup, then runs the standalone demo.

Remaining external work: actual BE2 schema alignment, real agreement/FIR/notice analysis, translation/retrieval quality, downstream private cleanup confirmation and frontend integration. Those cannot be proven by development fixtures. Punjabi OCR's observed word-level error remains visible; human review is mandatory. No TinyFish, external AI inference, cloud OCR/translation, LLM/classifier installation or training was performed. Downloaded binaries and private runtime files remain excluded from Git.
