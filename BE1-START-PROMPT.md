# Backend 1 — independent implementation launch prompt

Give the entire prompt below to Backend 1's coding assistant in the repository. It requires no access to the originating chat. Read the existing role handoff as instructed; it contains the complete shared Contract v1. This file is an implementation instruction, not a claim of working code.

---

You are Backend 1 for NyayaLens, a local-first plain-language legal-document and FIR explainer. Implement the public backend now. Work independently using deterministic, clearly labelled development fixtures when the ML service is unavailable. Complete a real extraction-to-review journey early, then connect the real Backend 2 service. Do not stop after producing a plan.

## 1. Read the repository and respect ownership

The current repository in the original setup is N:\Github-Repo\ct\Plain-Language-Legal-Document-and-FIR-Explaine. On a teammate's laptop, use their actual clone directory rather than assuming this drive exists.

Inspect applicable AGENTS.md files, Git status, existing code, dependencies and tests first. Read ALL of 03-BACKEND-1-API-Extraction-Sessions.md, including the Integration addendum and shared Contract v1. Read Backend 2's private-service integration section. If apps/ml/service/contracts.py and private service routes exist, inspect them read-only to align the adapter with the actual implementation. Do not assume Backend 2 is absent just because the original handoff was written before implementation.

User restriction: never use, install, enable or call TinyFish/tiny-fish. No external AI inference is authorized for the application. Do not upload user documents to external OCR, translation or AI services. Use local extraction/OCR and Backend 2's local ML service.

Own apps/api: public routes, schemas, extraction/OCR, sessions, revisions, jobs, ML adapter, integration tests and backend launch documentation. Own public contract fixtures in contracts/ in coordination with FE1. Do not overwrite apps/ml, frontend code, other owners' uncommitted work or shared dependency files without coordination. Do not install GPU models, train a duplicate classifier, create a second ML service or redesign the frontend.

Use an isolated compatible Python 3.11 or 3.12 environment. Python 3.11 is a preference, not a blocker. No GPU is needed for your development. Keep dependencies compatible with your actual Python version and pin tested versions. Never treat a global ROCm/CUDA installation as your application's environment.

## 2. Use agents with explicit file boundaries

If agent tools are available, use a coordinator plus up to THREE sub-agents. Stay within the environment's slot limit. If unavailable, execute the same responsibilities sequentially and say so. Do not claim agents are running when they are not.

- Agent A — extraction/OCR: owns apps/api/extraction and focused extraction tests. Implement PDF/DOCX parsing, page/paragraph references, selective OCR and source-linked clauses using labelled fixtures.
- Agent B — lifecycle/jobs: owns apps/api/sessions and apps/api/jobs plus focused lifecycle tests. Implement document-scoped sessions, revisions/review state, bounded extraction jobs, expiry, deletion and cleanup interfaces. Do not duplicate BE2's GPU scheduling.
- Agent C — ML integration: owns apps/api/ml_client and focused adapter tests. Inspect BE2's current private schemas/routes; implement the real HTTP adapter, development-only fake adapter, polling/error mapping, result validation and private-job cleanup.
- Coordinator — owns apps/api/main.py, public routes/schemas, configuration, shared fixtures, progress reporting, integration tests and README. Define shared typed interfaces before assigning work. Integrate agents' modules into one public service.

Agents receive this full prompt, the complete BE1 handoff and exact owned files. They report changed files, actual checks, limitations and interface examples. Only the coordinator edits shared schemas/requirements. Do not let several agents independently invent route names, statuses or response formats. Do not commit or push without a separate user request.

## 3. Publish concrete contract fixtures first

Keep all public endpoints under /api/v1 and follow Contract v1. Create or update agreed machine-readable example fixtures in contracts/ without silently overwriting someone else's changes:

- Upload accepted, document metadata, extraction awaiting review and reviewed PATCH response.
- Analysis accepted, queued/running/partial/complete/needs_review/failed snapshots.
- Grounded question answer and insufficient-evidence answer.
- Health/readiness, revision conflict, model busy/unavailable/timeout and unsupported-language errors.

Examples must include null DOCX page numbers, an unresolved relative deadline, all four result item kinds, original-language evidence, optional references, real progress fields and review warnings. Prefer the existing contract types over inventing different names. A fixture is a development example, not a real model result.

Publish the previously conceptual health shape in coordination with BE2/FE1. It must distinguish extraction readiness, available OCR languages, classifier/model readiness and tested versus unverified language paths. Missing readiness evidence means unknown/unavailable, not ready. Do not force FE developers to infer undocumented fields.

Review confirmation needs explicit state: FE1 may PATCH an empty corrections list with confirmed language/type. Record that reviewed revision is accepted. Actual text/language/type changes invalidate prior analysis/indexes. Agree revision increments consistently and reject stale expected_revision. Do not add a separate unannounced review endpoint.

## 4. Add truthful progress reporting

Maintain apps/api/PROGRESS.md with eight checklist milestones: environment/contracts; upload/storage; PDF/DOCX extraction; OCR/review/revisions; sessions/deletion; ML adapter/jobs; integrated checks; frontend handoff/startup notes. Record owner, pending/in-progress/passed/blocked status, command/evidence and next step.

Display a checklist bar such as [###-----] 3/8 passed only after checks pass. It is not a time estimate or a product-quality score. Give brief meaningful updates at least once per minute during sustained work.

Use Rich/tqdm terminal progress where helpful, with a plain-text fallback:

- Count actual uploaded bytes when the total is known; otherwise use a spinner.
- Count real PDF pages processed/OCR pages completed; DOCX paragraph/table progress can be counted if its total is known.
- For model analysis, forward BE2's real completed_clauses, total_clauses and optional stage/failed_clauses. Do not make up a second progress timer.
- A queued job remains queued. Zero/unknown total uses indeterminate progress.
- A fully processed job with failed clauses must still show partial/review/failure state and actual result coverage.

Private document text, filenames if sensitive, tokens and credentials must not be printed in progress logs. Do not edit the frontend to add a bar: expose the contracted progress so FE owners can build it.

## 5. Implement upload, validation and temporary storage

POST /documents accepts multipart file, input_language and document_type, returns 202 with document_id, random session_token, extracting status and revision. Create the record and return promptly; parsing runs in a bounded background job.

Initial limits from the handoff are 10 MB and 20 PDF pages. Enforce limits on actual received content, not just an untrusted Content-Length header. Validate extensions, content type and parser behavior. Handle empty files, malformed PDFs, encrypted/unreadable files and unsupported types with useful errors. DOCX is ZIP-based: bound expanded size, entry count and extracted characters. Do not execute macros or embedded content.

Use a verified task-specific runtime directory outside public static assets. Generate server-controlled filenames; do not concatenate user paths into storage locations. Scope one cryptographically random access token to one document. All source/extraction/analysis/question/delete routes check that token. Avoid revealing another session's document existence.

Never log raw contents or tokens, put tokens in URLs, or use uploads as training data. Explain temporary processing and retention. No authentication/account system or cloud storage is needed for v1.

## 6. Build real extraction, review and source navigation

- PDF: extract text with real 1-based page numbers and coordinates when available; preserve original text and reading order as well as practical.
- DOCX: extract paragraphs and tables in document order; page_number is null and paragraph_index is real. Do not invent pagination.
- Scanned PDF pages: use locally installed Tesseract selectively when text extraction is absent/poor. Check executable plus eng/hin/pan assets. Apply per-page timeouts and resource limits. Missing OCR returns OCR_UNAVAILABLE or a specific review warning, not fake extracted text.
- Preserve source_text separately from reviewed_text. Build stable clause IDs and source_ref. Corrections may invalidate bbox geometry; drop inaccurate boxes and retain page/paragraph navigation.
- Split on headings/numbered clauses and sentence boundaries while retaining cross-page context. Do not lose clauses or silently truncate without warnings.
- Treat language/type detection as a suggestion. Unknown/ambiguous values require review. Devanagari script alone does not establish Hindi.

GET extraction reports not-ready status while processing. PATCH uses expected_revision, validates clause IDs and handles review confirmation. Reject analysis until the current revision is reviewed. Genuine changes invalidate all associated language results and questions; do not show stale findings.

GET source returns the authenticated original with correct MIME type and safe disposition. FE1 will fetch it as a Blob; never make private runtime files openly browsable.

PyMuPDF and python-docx are the planned parsers; check licensing/current installation compatibility. If OCR setup is blocked, complete native PDF/DOCX support and visibly report the unsupported scan path. Do not label scans supported until a real scan test works.

## 7. Integrate Backend 2 through an adapter

Use a small explicit adapter boundary so you can develop without waiting for BE2:

- Real adapter: HTTP calls to the existing private ML service, normally localhost:8001 on the final host.
- Fake adapter: deterministic labelled fixtures in explicit development/test mode only. It must not silently activate when real ML fails. Health and job warnings identify simulation; fixture data must not be presented as diagnosis of an arbitrary real upload.

Backend 1 creates analysis_id and forwards document_id, document_revision, document_type, input_language, output_language and reviewed clauses to POST /internal/analyse. It returns 202; poll GET /internal/jobs/{analysis_id}. Validate returned identities, revision, status and Contract v1 result. Preserve optional progress fields supported by BE2. No direct browser access to private ML/model ports.

Verify backend evidence references belong to current reviewed clauses. Quotes must match reviewed text; reference_ids resolve to records. Keep model scores separate from legal certainty and do not synthesize a whole-document safety score. Do not strip valid warnings, limitations or provenance when proxying.

Public question requests include analysis_id; derive authenticated document ID/revision server-side and forward the private QuestionRequest with client_request_id. Questions must use a current completed/reviewable result. Current v1 question reference IDs must resolve to references already supplied in that analysis unless an optional answer.references field is explicitly agreed across owners.

Map private errors into the public envelope/status codes. Handle MODEL_BUSY, MODEL_UNAVAILABLE, MODEL_TIMEOUT, INVALID_MODEL_OUTPUT, stale revision, missing/deleted/expired jobs and connection refusal. Use finite HTTP timeouts and do not block the event loop. A model timeout must not freeze health, uploads or later requests.

De-duplicate active analysis per document revision/output language, while allowing different output languages as separate result versions. Idempotent retries with the same question client_request_id must not launch duplicate generations. Reuse with a conflicting payload should fail clearly. A language switch must not mutate source text.

## 8. Make lifecycle, expiry and deletion reliable

Use a single public API worker with in-memory metadata for v1 unless a deliberate shared-store design is introduced. Multiple workers with unrelated in-memory stores are not compatible. Document that sessions/jobs do not survive restart.

Use locks/revision checks around concurrent edits and job updates. Bound extraction jobs and the public polling workload. Avoid independently queueing unlimited analysis jobs ahead of BE2's bounded GPU queue.

Implement the disclosed default 30-minute inactivity retention consistently. If a real expiry timestamp is exposed, coordinate its optional metadata field with FE1. Otherwise frontend shows policy text, not an invented countdown. Ensure polling/active work expiry behavior is deliberate and documented.

DELETE first marks the document inaccessible, then removes uploads, extracted/reviewed text, results, question caches and public job records. Propagate deletion to EVERY related BE2 analysis ID, including older output-language versions. Cancel pending extraction and discard all late writes/results. ML computation may finish in the background, but deleted data cannot reappear.

If private cleanup fails, keep the public tombstone and report/retry private cleanup using bounded metadata-only work; never claim successful downstream cleanup merely because a request was sent. BE2 also expires private results. Do not persist sensitive cleanup logs. Define a testable retry policy and limits.

Startup orphan cleanup must resolve the runtime root and delete only verified descendants. Do not issue broad recursive deletes. No claim of forensic secure erasure is appropriate.

## 9. Implement the full public route set

Follow the handoff for exact payloads:

- GET /api/v1/health
- POST /api/v1/documents
- GET /api/v1/documents/{document_id}
- GET /api/v1/documents/{document_id}/extraction
- PATCH /api/v1/documents/{document_id}/extraction
- GET /api/v1/documents/{document_id}/source
- POST /api/v1/documents/{document_id}/analyses
- GET /api/v1/documents/{document_id}/analyses/{analysis_id}
- POST /api/v1/documents/{document_id}/questions
- DELETE /api/v1/documents/{document_id}

Use Pydantic validation and consistent errors. Expected codes include FILE_TOO_LARGE, UNSUPPORTED_FILE, EMPTY_DOCUMENT, EXTRACTION_FAILED, OCR_UNAVAILABLE, EXTRACTION_NOT_READY, REVISION_CONFLICT, ANALYSIS_NOT_READY, MODEL_UNAVAILABLE, MODEL_BUSY, MODEL_TIMEOUT, INVALID_MODEL_OUTPUT, NOT_FOUND and UNSUPPORTED_LANGUAGE. Framework request-validation errors must also be understandable to the frontend; publish their expected envelope or normalize them.

Keep legal-aid links restricted to reviewed official information. There is no requirement for a new export endpoint: FE2 handles explicit local Markdown/print export. You do not implement translation, classifiers or legal interpretation independently; those belong to BE2.

## 10. Run meaningful tests and a frontend-ready smoke journey

Create fast tests with parser fixtures and a fake ML HTTP service, and a separate optional real-ML smoke command. Distinguish clearly what each proves.

Required checks:

1. Real native PDF and DOCX upload/extraction, correct source references, and table/paragraph ordering.
2. Real scanned page OCR when installed; missing language asset and page timeout handled.
3. Empty, malformed, encrypted/unreadable and oversized uploads; DOCX expansion limits.
4. Explicit confirmation with no text corrections; real correction; stale revision rejection; analysis blocked before review.
5. Source download requires the right token; token A cannot read/delete document B.
6. Analysis accepts then polls actual statuses/progress; language variants and partial results survive proxying correctly.
7. Grounded/unsupported questions, retry deduplication and current-revision enforcement.
8. Wrong IDs/quotes/references in mocked ML output are rejected instead of displayed.
9. Busy/unavailable/timeout errors; health and another request remain responsive after a timeout.
10. Delete during extraction/analysis prevents resurrection and cleans all known language jobs; private cleanup failure is visible and retried according to policy.
11. Expiry, stale polling and restart/orphan cleanup stay within intended paths.
12. No raw text/tokens in logs; no external AI request; mock mode never silently replaces a failed real service.

As soon as possible run upload -> extraction -> confirm -> analysis accepted -> completed result -> source evidence -> question -> delete. Use a real local ML service for the final integration claim; if unavailable, complete the adapter contract tests, report the dependency and continue other independent work. Do not claim a fake-ML journey proves the model is working.

## 11. Deliver a runnable handoff

Write apps/api/README.md with exact tested environment setup, dependencies, OCR installation/assets checks, configuration, service launch, tests and smoke commands for the teammate's actual OS. Include sample curl/PowerShell requests that were exercised, without real secrets or private contents.

Configuration includes API_PORT, WEB_ORIGIN, ML_BASE_URL, optional ML_SERVICE_TOKEN for agreed cross-laptop development, RUNTIME_DIR, MAX_UPLOAD_MB, MAX_PDF_PAGES, SESSION_TTL_MINUTES and MODEL_TIMEOUT_SECONDS. Validate settings at startup; don't hard-code another laptop's localhost or personal paths.

Final deployment order: local LLM -> BE2 ML service -> BE1 public API -> frontend. Private services normally bind localhost on the GPU host. In development, if BE1 runs on another laptop, coordinate a temporary trusted-network ML access/proxy arrangement with BE2; do not silently expose its model port or change firewall settings. CORS permits only agreed origins; a frontend same-origin /api proxy is preferred.

Deliver frontend-ready public fixtures, OpenAPI output, .env.example without secrets, a tested launch command, apps/api/PROGRESS.md, test results and a short BE2 integration note. Preserve others' work and do not push without a user request.

Continue through authorized implementation and verification. Ask only for genuinely missing required information or actions that need authorization; make routine reversible choices from the handoff. Finish by separating implemented-and-tested, untested, development-only mocks, blockers and deferred scope. Never fabricate completion or metrics.
