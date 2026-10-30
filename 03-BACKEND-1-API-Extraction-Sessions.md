# BE1 — Public API, extraction, sessions, jobs and integration

You own the public backend, document lifecycle and assembly of BE2's intelligence into a reliable service. Give this entire file to your coding assistant. The GPU owner BE2 builds the separate private ML service. Do not implement a second classifier or download giant models in your package.

## Files you own

apps/api/main.py, routes/*, extraction/*, sessions/*, jobs/*, schemas/*; root backend requirements/lockfile in coordination with BE2; final service launcher/integration notes. Own Contract v1 public schemas, but notify FE1/FE2/BE2 before any change. BE2 owns apps/ml, model weights, classifier artifacts and private inference endpoint.

Use Python 3.11, FastAPI, Pydantic and an HTTP client to BE2. Start with a single-process in-memory session/job store plus temporary files. Do not add Redis, Celery, Postgres or persistent vector infrastructure to the critical path. Be explicit that in-memory jobs do not survive restart; clear orphan temp files safely at startup. Do not launch multiple API workers against separate in-memory stores.

## Extraction implementation

1. Validate permitted file type, extension, actual parser behavior and size. Initial limits: 10 MB and 20 PDF pages; coordinate with FE1. For DOCX also limit expanded ZIP size, entry count and extracted characters to prevent accidental resource exhaustion.
2. Create random document ID and high-entropy session token; return 202 before expensive extraction.
3. Extract PDF text with page/coordinate metadata. Read DOCX paragraphs and tables in document order. DOCX page numbers remain null.
4. OCR only scanned/poor-text PDF pages, with locally installed Tesseract assets for eng/hin/pan. Set page/time/resource limits. Report missing OCR executable/language asset as a useful error. Do not OCR an already good text page unnecessarily.
5. Keep original extracted text. Add reviewed_text separately, preserving source_ref and extraction_method.
6. Split by headings, numbered paragraphs and sentence boundaries. Avoid destroying a clause that crosses a page. Preserve multiple source references internally if necessary; public v1 may use a primary source_ref with additional refs introduced only by contract agreement.
7. Detect probable language/type conservatively. Return unknown/other and ask user confirmation when uncertain. Script detection alone does not prove Hindi versus other Devanagari languages.
8. Do not run analysis until extraction is reviewed. PATCH uses optimistic revision checking; invalidates dependent results and indexes.

Define minimum text length/quality checks using actual fixtures rather than claiming a single OCR confidence proves correctness. Dates, numbers and negation errors should produce visible review cues.

## Session and privacy lifecycle

Use document-scoped access token checks on every file/result/question/delete route. One document's token must not read another. Compare tokens safely; never log them. Configure CORS only for actual team origins when needed; same-origin frontend proxy is simpler.
- Store uploads in a task-specific temporary runtime directory, outside public static assets.
- Expose originals only through authenticated source route, with correct content type.
- Disable content logging in app, model proxy and exception handlers.
- No automatic use of user uploads as training data.
- Use a disclosed 30-minute inactivity expiration initially, with visible remaining time via metadata if implemented. Active requests extend it consistently; cleanup must not race with active writes.
- Delete source, extracted/reviewed text, translations, cached results, questions and per-document vectors. Cancel pending jobs; mark deleted before awaiting cleanup so late ML results are discarded.
- Do not promise secure forensic erasure. Browser export is a separate user-created copy.
- On shutdown/startup handle orphan cleanup only within the verified runtime directory. Avoid broad recursive deletes.

## Async jobs and private ML interface

Run extraction and analysis in bounded jobs. A blocking OCR/model call must not freeze all FastAPI requests. Start with one analysis job at a time on the GPU and a small bounded queue; return useful busy status when full. Add timeouts and job failure states. Do not use a new model process for every clause.

BE1 calls BE2's POST /internal/analyse on localhost/private service:
~~~json
{
  "document_id":"doc_123","analysis_id":"a1","document_revision":2,
  "document_type":"agreement","input_language":"en","output_language":"hi",
  "clauses":[{"clause_id":"c1","reviewed_text":"text","source_ref":{"page_number":1,"paragraph_index":null,"bbox":null}}]
}
~~~
Response: the Contract v1 result object, or a validated error. BE2 additionally provides GET /internal/health and POST /internal/question using supplied reviewed clauses/current analysis. Do not send unreviewed hidden original text as if it were authoritative. BE2 cannot invent public session tokens.

For progress v1, BE2 can expose GET /internal/jobs/{analysis_id} or BE1 may orchestrate batches. Agree ONE approach before implementing: recommended BE2 asynchronous start -> poll private job. BE2's /internal/analyse returns 202 with analysis_id; private GET returns status/progress/result. This mirrors public job behavior and permits actual progress reporting. Private job outputs are short-lived and must support DELETE /internal/jobs/{analysis_id} for cleanup. BE1 must propagate document deletion; BE2 discards late results.

Key results by document ID + revision + output language + model/rule version. Do not return a result for a stale revision. De-duplicate analysis creation and question requests by client_request_id. A timeout is not an empty successful explanation.

## Public routes and application behavior

Implement every route in the shared contract. Health reports dependency state independently: extraction ready, OCR languages available, classifier loaded, generator loaded, tested language matrix. If model is offline, uploads/review can still work. Analysis returns MODEL_UNAVAILABLE with retryable true.

Validate ML outputs against Pydantic schemas and document membership:
- Every clause_id exists in current revision.
- Quotes match reviewed source text.
- Coverage does not exceed or hide skipped clauses.
- reference_ids resolve only to curated official references.
- No alleged guilt is fabricated by a contract formatter.
BE2 performs deeper evidence validation; BE1 enforces the boundary.

Error codes to implement at least: FILE_TOO_LARGE, UNSUPPORTED_FILE, EMPTY_DOCUMENT, EXTRACTION_FAILED, OCR_UNAVAILABLE, EXTRACTION_NOT_READY, REVISION_CONFLICT, ANALYSIS_NOT_READY, MODEL_UNAVAILABLE, MODEL_BUSY, MODEL_TIMEOUT, INVALID_MODEL_OUTPUT, NOT_FOUND, UNSUPPORTED_LANGUAGE. Use HTTP statuses consistently and share examples with FE1.

## Integration and final deployment

Development: BE1 API on laptop 3; BE2 ML service on GPU laptop 4. Restrict service access to the trusted team network and use a temporary shared service credential if cross-laptop ML access is required. Final judging: run web/public API/private ML/LLM on the GPU host, private services on localhost. Use a single browser origin and avoid internet-hosted frontend pages that cannot reach the LAN API.

Document environment variables, without real secrets: API_PORT, WEB_ORIGIN, ML_BASE_URL, ML_SERVICE_TOKEN, RUNTIME_DIR, MAX_UPLOAD_MB, MAX_PDF_PAGES, SESSION_TTL_MINUTES, MODEL_TIMEOUT_SECONDS. BE2 documents model path and its own runtime variables. Provide startup order: LLM -> ML -> public API -> web. Provide a clearly disclosed extraction-only failure mode, not a fake model fallback.

## Meaningful acceptance checks

- PDF, DOCX, scanned PDF; missing OCR asset; malformed DOCX; empty file; oversize file.
- Two documents with different tokens cannot read each other's source/results.
- Correction increments revision; stale PATCH rejected; previous analysis invalidated.
- Upload/health remain responsive while local inference runs.
- Queue busy/timeout errors are useful and do not create duplicate jobs.
- One full agreement, FIR and notice pass the real pipeline.
- Deleting during analysis prevents resurrection and removes private ML job artifacts.
- Restart cleanup stays inside runtime directory.
- No private document text/token in logs.
- Language mismatch returns warning or review state, never a silent English-only classification.

## Prompt to give your coding assistant

Implement BE1 only in this handoff. Inspect repo first, create one public FastAPI service, and coordinate schemas with FE1 and BE2. Implement Contract v1, bounded background extraction/jobs, PDF/DOCX/OCR review, revisions, per-document tokens, authenticated source download, ML proxy, explicit errors and cleanup. Keep models/training in BE2 ownership. Start with real parser fixtures and a clearly labelled ML stub for development; switch to the real private service before claiming analysis works. Run meaningful endpoint checks above and report limitations.

---

## Shared project brief — read this before coding

Build NyayaLens for CTBF-AI-09: explain agreements, FIRs and notices clause by clause in plain English, Hindi or Punjabi, identify attention clauses and deadlines, cite the source and link to official legal aid. This is a hackathon prototype, not a legal decision system. No project implementation has been started by the author of this handoff.

The team has FOUR laptops: FE1, FE2, BE1 and BE2. The BE2/GPU owner uses the machine verified as RTX 5070 Ti Laptop GPU, approximately 12 GB VRAM, with user-reported 32 GB RAM. Other laptops need no GPU. A downloaded pretrained model is assumed permitted; organizer permission has not been established. Never claim training from scratch. No external AI inference API is part of the product. Ordinary HTTP between team laptops and localhost model services is local infrastructure; clarify the organizer's definition if they prohibit even local APIs. Download dependencies/models before testing without internet.

### Product scope and multilingual truth

Input language and answer language are independent controls. Initial target: English, Hindi in Devanagari, Punjabi in Gurmukhi. This is not support for every language, Romanized Punjabi, Shahmukhi or handwriting. Input may be PDF, DOCX or a scanned PDF. OCR errors require review.

Train the first classifier on ENGLISH labelled data. An English classifier does not become multilingual by using a multilingual LLM elsewhere. For Hindi/Punjabi: retain each original clause, locally translate a working copy into English, run English classification/rules on that copy, and generate the answer in the selected language. Preserve original evidence and clause IDs throughout. This is a translation-assisted path, not a classifier trained/validated in three languages. A local model's multilingual ability is not proof of legal translation accuracy.

BE2 must evaluate the local Qwen translation path on fluent-reviewed samples. IndicTrans2 is an optional dedicated local replacement only after download, compatibility and quality checks. If translation is uncertain, return needs_review and skip untrusted classifications; never silently mark low-scored or untranslated clauses safe. Unsupported input receives an honest unsupported-language result. UI controls remain visible for target languages, but tested/experimental/unsupported capability labels reflect real checks.

Final product language support requires separate checks of extraction, translation, classification, explanations and follow-up questions. Aim to test all nine input/output combinations across en, hi, pa on short fixtures. If fewer work by evaluation, show the exact tested matrix. Keep numbers, dates, names, section identifiers, negation and allegations intact.

### Frozen architecture

Upload -> local text extraction/OCR -> editable review -> document type/language -> clauses with source references -> analyse EVERY clause -> agreement classifier OR FIR/notice extraction + date/amount rules -> optional filtered official references -> local LLM explanation -> evidence checks -> multilingual result.

Use retrieval for follow-ups and contextual references, NOT to decide which clauses receive the first inspection. Two collections: temporary uploaded-document evidence and a separate versioned official-reference collection. No graph database, autonomous agents, cloud vector database or mandatory account system.

Roles and ownership:
- FE1: application shell, upload, extraction review, source viewer, shared web contracts/client.
- FE2: results, attention cards, timelines, questions, result translations and export.
- BE1: public API, extraction/OCR, sessions, document revisions, jobs, cleanup and integration.
- BE2: datasets/training, classifier, local inference, translation, retrieval, evidence validation, evaluation.

BE1 owns apps/api/main.py and public API routes. BE2 owns apps/ml and the private ML service. FE1 owns apps/web/src/App.tsx, shared types/client and document views. FE2 owns apps/web/src/features/results. Do not create a competing root app or duplicate API server. Changes to shared contracts require notifying all four owners and updating the same contract version.

### Repository layout to create together

    apps/web/src/{app,lib,features/upload,features/review,features/source,features/results}
    apps/api/{main.py,routes,extraction,sessions,jobs,schemas}
    apps/ml/{service,training,inference,retrieval,translation,validation}
    contracts/{v1-example.json,README.md}
    data/{demo,training,eval,references}
    artifacts/{classifier,manifests,metrics}
    models/                         # downloaded weights; gitignored
    work/runtime/                   # temporary private uploads; gitignored

FE1 scaffolds the web app once. BE1 scaffolds the public API once. BE2 scaffolds only its private service/training package. Keep models, uploads, credentials, generated indexes and private documents out of Git. Synthetic fixtures must be explicitly labelled synthetic.

### Contract v1 — identical in all four handoffs

Codes: Language = en | hi | pa | unknown. DocumentType = agreement | fir | notice | other.
DocumentStatus = extracting | awaiting_review | queued | analysing | complete | needs_review | failed.
AnalysisStatus = queued | running | complete | needs_review | failed.

All public routes begin /api/v1. Return JSON except original-file download. Error shape:
~~~json
{"error":{"code":"EXTRACTION_FAILED","message":"Readable explanation","retryable":false},"request_id":"req_123"}
~~~
Never return raw document contents in application logs or error traces.

Routes:
1. GET /health -> 200 service status plus model readiness and tested language capabilities. CPU extraction may be ready while ML is unavailable.
2. POST /documents, multipart file + input_language (auto/en/hi/pa) + document_type (auto/agreement/fir/notice/other). Browser must not set the multipart Content-Type manually. Return 202:
~~~json
{"document_id":"doc_123","session_token":"opaque_random_token","status":"extracting","revision":1}
~~~
3. GET /documents/{document_id} -> status, revision, filename, document_type, input_language, warnings, extraction_ready. All later document routes require X-Session-Token; scope it to this document.
4. GET /documents/{document_id}/extraction -> original clauses and review warnings; 409 EXTRACTION_NOT_READY while extracting.
5. PATCH /documents/{document_id}/extraction -> {"expected_revision":1,"corrections":[{"clause_id":"c1","text":"corrected text"}],"input_language":"en","document_type":"agreement"}. Reject stale revisions with 409. Return new revision. Only allow before an active analysis or cancel that analysis explicitly. Invalidate old results/indexes when text/type/language changes.
6. GET /documents/{document_id}/source -> authenticated original file. FE1 fetches a Blob and creates a temporary object URL; do not put tokens in query strings.
7. POST /documents/{document_id}/analyses -> {"expected_revision":2,"output_language":"hi"}. Return 202 {"analysis_id":"a1","status":"queued","document_revision":2}. Analyse reviewed text only. De-duplicate active jobs for the same document revision/language.
8. GET /documents/{document_id}/analyses/{analysis_id} -> status, progress {completed_clauses,total_clauses}, document_revision, output_language, result (null until available), warnings. Progress is actual completed work, not a fake timer.
9. POST /documents/{document_id}/questions -> {"analysis_id":"a1","question":"What does clause 3 mean?","output_language":"en","client_request_id":"uuid"}. Return 200 answer object; 409 ANALYSIS_NOT_READY; 429 MODEL_BUSY if queue full. BE1/BE2 enforce timeout. FE2 allows explicit retry with same client_request_id, not automatic duplicate submissions.
10. DELETE /documents/{document_id} -> 204. Delete session files, source text, translated copies, document indexes, results and references to queued work; discard late outputs. In-flight model computation may finish but must not recreate deleted data. Later requests return 404.

Clauses:
~~~json
{"clause_id":"c1","source_text":"Original extracted text","reviewed_text":"Original extracted text","source_ref":{"page_number":1,"paragraph_index":null,"bbox":null},"extraction_method":"text","review_required":false}
~~~
PDF page_number is 1-based. DOCX page_number is null; paragraph_index is 1-based. bbox is optional [x0,y0,x1,y1] in original PDF points, not browser pixels. If correction invalidates precise geometry, drop bbox and retain page/paragraph navigation. reviewed_text is authoritative after human correction; show that it differs from extraction.

Completed result structure:
~~~json
{
  "document_id":"doc_123","analysis_id":"a1","document_revision":2,
  "input_language":"en","output_language":"hi",
  "document_type":"agreement","coverage":{"analysed":8,"total":8},
  "items":[{
    "item_id":"i1","clause_id":"c1","kind":"attention",
    "category":"automatic_renewal","explanation":"Explanation in selected language",
    "evidence":[{"clause_id":"c1","quote":"exact substring of reviewed_text"}],
    "reference_ids":[],"review_status":"supported",
    "detector":"rule","model_score":null,"limitations":[]
  }],
  "deadlines":[{
    "deadline_id":"d1","clause_id":"c1","source_quote":"within 15 days of receipt",
    "display_text":"15 days after receipt","anchor":"receipt",
    "resolved_date":null,"status":"needs_information","missing_information":["receipt_date"]
  }],
  "warnings":[],"legal_aid":[{"title":"NALSA legal aid","url":"https://nalsa.gov.in/legal-aid/"}],
  "provenance":{"classifier_version":"baseline-v1","generator":"local-model","rules_version":"v1"}
}
~~~
kind = explanation | attention | allegation | notice_action.
review_status = supported | needs_review.
Deadline status = explicit | needs_information | needs_review. Do not implement legal time-limit calculations in v1; show literal dates or unresolved relative periods. No document-wide safety score.
Question answer: {"answer":"...","evidence":[{"clause_id":"c1","quote":"..."}],"reference_ids":[],"review_status":"supported","limitations":[]}.
References are an OPTIONAL separate response field:
references = [{reference_id,title,url,section,version,excerpt}]. If reference_ids is empty, no reference card is required. Source document evidence is never substituted with a dataset citation.

### Shared development and integration rules

Use React + TypeScript + Vite, Python 3.11 + FastAPI/Pydantic, scikit-learn baseline, local Qwen 4B quantized inference. Pin dependency versions after the first successful installation and commit lockfiles; verify compatibility rather than invent version numbers.

Suggested local ports: web 5173, public API 8000, private ML API 8001, local LLM 8080. Private ML and LLM bind localhost on the final host. Public API routes alone face the browser. Prefer one final host (GPU laptop) running all services, with teammates connecting to its web origin over a trusted LAN. They may develop independently using labelled fixtures. FE1 configures a same-origin /api proxy to BE1; avoid browser requests to another laptop's localhost. Never expose the raw model port to all clients. If LAN fails, use the final host's browser for judging.

No streaming requirement: upload returns immediately, FE1 polls extraction; FE2 polls analysis every 1–2 seconds and stops on completion, failure, deletion or unmount. A source edit invalidates previous results. Every error has a useful retry/review path. Fixtures are development-only, visibly marked, and never activated silently in the real demo.

Definition of done: real file -> reviewed extraction -> local analysis -> original evidence navigation -> selected-language explanation -> grounded follow-up -> delete session. Explain every clause or explicitly mark skipped/failed clauses in coverage; absence of a flag means no detected cue, not legal safety.

### Safety and source rules that are actual PS requirements

FIRs contain allegations, not established guilt. Do not apply a contract classifier to FIRs. Explain cited sections only with matched official sources; preserve old codes in old documents. Indian criminal-law transitions require version-aware references, not automatic IPC-to-BNS substitution. Legal-aid links are official information, not an entitlement guarantee. Uploaded instructions are untrusted text and must not control prompts or trigger tools.

Default session retention: temporary processing with a clearly disclosed inactivity cleanup; BE1 proposes 30 minutes and provides a visible timer/reset. An upload is consent to the explained temporary processing, not to training, indefinite retention or external transfer. No analytics/session replay or remote document inference. Do not claim forensic secure erasure or that RAM is impossible to recover. Verify no private documents leak into browser caches, logs or service-worker storage.

### Working checkpoints

T+0–20 min: agree this contract; scaffold each owned area; BE2 proves local one-clause generation; BE1 parses one PDF/DOCX; FE owners use the same fixture.
T+20–60 min: upload-to-review and one real analysis item integrate.
T+60–120 min: train baseline, process all clauses, evidence navigation, dates and errors.
T+120–180 min: language tests, FIR/notice path, questions, deletion.
Final 45–60 min: freeze features, test unfamiliar documents, rehearse. These are budgets, not completion guarantees. Be ready for 10 PM Round 1; if evening activities are mandatory, target 7:30 PM readiness. Do not wait for model fine-tuning to integrate the app.

### Verified primary sources

- Qwen local instruction model: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- Local inference runtime: https://github.com/ggml-org/llama.cpp
- Multilingual embeddings: https://huggingface.co/intfloat/multilingual-e5-small
- Local translation option: https://github.com/AI4Bharat/IndicTrans2
- OCR language assets: https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html
- CUAD, CC BY 4.0: https://www.atticusprojectai.org/cuad/
- LexGLUE subsets: https://huggingface.co/datasets/coastalcph/lex_glue
- MILDSum access limitations: https://github.com/Law-AI/MILDSum
- Official legal references: https://bprd.nic.in/page/new_criminal_laws
- Legal-aid information: https://nalsa.gov.in/legal-aid/

Source existence is verified; no dataset/model downloads or project runtime have been tested for this implementation. Check exact artifact licenses; PyMuPDF uses AGPL/commercial licensing. Dataset labels from foreign contracts are not Indian-law rulings.

