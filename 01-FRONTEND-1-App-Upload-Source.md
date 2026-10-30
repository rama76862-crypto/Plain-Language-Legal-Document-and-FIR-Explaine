# FE1 — Application, upload, extraction review and source viewer

You own the first half of NyayaLens and the frontend integration boundary. Give this entire file to your coding assistant. Read your role section AND the shared contract below. Build only your owned files; do not start the backend or model training.

## Your deliverables and ownership

Create the React/TypeScript/Vite app once in apps/web. Own:
- src/App.tsx and src/app/*: layout, top-level workflow and selected-document state.
- src/lib/api.ts, types.ts, config.ts: contract types, fetch client, error handling.
- src/features/upload/*: file selection, validation and upload progress.
- src/features/review/*: extraction review and correction.
- src/features/source/*: PDF/DOCX source rendering and evidence navigation.
- shared global CSS/theme tokens, package.json, lockfile and Vite proxy.
- contracts/v1-example.json together with BE1; FE2 consumes it.

FE2 owns results screens, questions and export. Establish the integration interface immediately:
~~~ts
type ResultsWorkspaceProps = {
  documentId: string;
  sessionToken: string;
  revision: number;
  outputLanguage: "en" | "hi" | "pa";
  onNavigateEvidence: (clauseId: string) => void;
  onDeleted: () => void;
};
~~~
FE2 exports ResultsWorkspace from src/features/results/ResultsWorkspace.tsx. Until it exists, use a clearly named placeholder component; remove the placeholder when integrating. FE1 owns the source viewer state and clause selection. FE2 never needs to edit App.tsx.

## User journey you implement

1. Landing screen: short product explanation, local temporary processing notice and three target-language labels with capability status.
2. Upload PDF or DOCX, select input language (auto allowed) and document type. Select answer language independently. Do not imply that choosing Hindi translates a scanned document successfully.
3. Show real extraction state. Poll document status; do not display a fake progress percentage.
4. Display extracted clauses alongside source navigation. Warn on low OCR quality, missing text or unresolved language/type.
5. Let users correct text and explicitly confirm review. PATCH corrections using expected_revision; on 409 reload and explain that the document changed.
6. Hand reviewed revision to ResultsWorkspace. Keep source viewer visible for FE2 evidence navigation.
7. Show Delete session, local-processing status and failure/retry actions.

Use a clean two-pane desktop layout: original document left; review/results right. On narrow screens use accessible tabs. Style should prioritize readable Gurmukhi/Devanagari, long text, keyboard navigation and visible evidence. Bundle necessary fonts locally after checking license; do not depend on a font CDN for the offline demo.

## Data/state implementation details

- Single source of truth: document_id, session_token, revision, document status, selected clause ID, input language, output language and document type.
- Keep tokens in memory. Do not put documents/tokens in URLs, analytics, localStorage or Git. A refresh may end the UI session; say so. Revoke source Blob URLs on delete/unmount.
- API client accepts AbortSignal, decodes the shared error shape and sends X-Session-Token. It does not automatically retry uploads, PATCH or analysis creation.
- Upload validation: reject empty files and obviously unsupported types. BE1 is authoritative for MIME/file checks and limits. Agree initial 10 MB / 20-page demo limits with BE1 and show them. DOCX has no reliable original page count.
- Source viewer: PDF.js/react-pdf is a reasonable implementation option; verify its current setup and bundle worker locally. Load authenticated source via Blob. DOCX v1 displays numbered extracted paragraphs/tables; do not run arbitrary DOCX HTML. Prefer textContent rendering and escaped text.
- Source navigation always works at clause/page/paragraph level. Bounding-box highlights are optional. A PDF bbox must be scaled/rotated to viewer coordinates; if inaccurate, use page navigation with quoted text instead.
- All visible strings use a small locale dictionary. Input-language and answer-language controls are separate from UI language.
- Warning banners have actionable text: review extraction, select language manually, retry or use a clearer file.
- Do not add sign-in, cloud uploads, marketing pages or complicated global state libraries unless already familiar.

## Handoff to teammates in the first 20 minutes

To FE2: send ResultsWorkspaceProps, shared types, the example result and import path. Give FE2 one UI card/button primitive plus theme tokens; let them use these without editing your shared files.
To BE1: confirm route prefix, multipart field names, header, response errors, limits and source download. Ask for one real sample response as soon as extraction works.
To BE2: ask only for tested language capability labels and truthful processing states; FE1 never calls ML service directly.

Use relative browser /api/v1 URLs. Vite proxy target comes from a configuration value; final host can use localhost:8000, but another laptop must not interpret its own localhost as BE1's machine. Start frontend with npm run dev, selecting the team's intended LAN binding only for the demo. Do not open firewall settings without the operator's knowledge.

## Acceptance checklist

- Upload one selectable-text PDF and one DOCX.
- Reject zero-byte/wrong-type/oversize inputs with useful errors.
- Show scan extraction warnings and editable text.
- Correction increments revision and invalidates previous result view.
- Changing output language does not mutate original input text.
- English, Hindi and Punjabi text render without missing glyphs.
- Clicking a clause from FE2 navigates to real source evidence.
- No DOCX page numbers are fabricated.
- Cancel/delete stops polling, revokes URLs and removes visible content.
- Model unavailable does not break extraction/review.
- Refresh/session loss is explained; no private document is persisted secretly.
- Development fixtures are labelled and cannot silently replace a failed real request.

## Prompt to give your coding assistant

Implement the FE1 role in this file in the shared NyayaLens repository. First inspect existing files and dependency versions. Preserve other owners' files. Create one React/Vite app only if absent. Follow Contract v1 exactly and export the shared types/client for FE2. Implement upload, asynchronous extraction polling, editable reviewed clauses, source navigation and the ResultsWorkspace integration props. Use labelled fixtures until BE1 is reachable, with an explicit development flag. Do not create fake successful analysis, external AI calls or persistent private uploads. Run the available typecheck/build and manually check the acceptance items. Report changed files, actual checks and remaining limitations.

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

