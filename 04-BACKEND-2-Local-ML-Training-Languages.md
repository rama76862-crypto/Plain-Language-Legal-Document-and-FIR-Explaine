> Current integration update (30 October 2026): read FULL-FEATURE-VERIFICATION.md and the application READMEs for implemented behavior and actual checks. This document contains historical development specifications. All frontend fixture/mock modes and canned results are removed; older instructions allowing frontend fixtures are superseded. Current upload defaults are 25 MB / 50 PDF pages. Reports use authenticated backend JSON/MD/HTML endpoints. Language/legal review gates remain open.

# BE2 — GPU owner: datasets, trained classifier, local models and validation

## Integration addendum — complete feature map (30 October 2026)

This section is repeated identically in all four role handoffs so a teammate does not need the originating chat. It clarifies the existing scope; it does not claim features are implemented or expand the public API without agreement. Read the entire role file, including the shared Contract v1. These are development specifications, not a live completion report: inspect the actual repository and implementation evidence for current status.

### Backend feature -> frontend responsibility

| Backend behavior / output | Owner producing it | Frontend owner and required presentation |
|---|---|---|
| PDF/DOCX upload and file/size validation | BE1 | FE1: upload, limits, readable rejection and retry |
| Text extraction and selective scanned-PDF OCR | BE1 | FE1: extracting state, extracted text, OCR warning/review |
| Input-language/type detection and manual correction | BE1; BE2 consumes reviewed values | FE1: independent input-language and document-type selectors; uncertainty must be visible |
| Reviewed clauses and revision conflicts | BE1 | FE1: correction/confirm flow and conflict recovery; FE2: discard stale results |
| Original file, page/paragraph locations and optional boxes | BE1 | FE1: source viewer/navigation; FE2: evidence buttons invoke FE1 callback |
| Analyse every clause, including ordinary clauses | BE2, exposed through BE1 | FE2: complete clause-by-clause view, analysed/total coverage, missing/failed warnings |
| Agreement topic/attention classification | BE2 | FE2: potential-concern category, explanation, exact evidence; no legal-safety verdict |
| Automatic-renewal/penalty and other reviewed rules | BE2 | FE2: same attention cards; identify rule vs classifier in optional technical detail |
| Stated payments, amounts and obligations | BE2 | FE2: expose these in the relevant clause explanation/evidence; do not invent a new mandatory top-level amounts/obligations API |
| FIR parties, dates, sections and allegations | BE2 | FE2: FIR-specific content using allegation items; allegations remain allegations |
| Notice issuer/recipient and demanded action | BE2 | FE2: notice-action items and source-linked explanation, without personalized legal advice |
| Exact dates and unresolved relative periods | BE2 | FE2: deadline cards; missing receipt date stays unresolved; no frontend deadline calculator |
| Source language independent from answer language | BE1 + BE2 | FE1: selection/state; FE2: request matching output and reject stale-language responses |
| Local English-pivot translation for Hindi/Punjabi | BE2 | FE1/FE2: original text remains evidence; disclose translation-assisted path and needs-review limitations |
| Reviewed language capabilities and unsupported paths | BE2 -> BE1 | FE1: tested/experimental/unavailable labels from backend evidence; FE2: warnings/refusal, no false successful translation |
| Original-clause citations and evidence validation | BE2, enforced by BE1 | FE2: exact quotes and source actions; FE1 navigates to original page/paragraph |
| Filtered official reference retrieval | BE2 | FE2: title/section/version/excerpt/link when references exist; state unverified/missing instead of inventing authority |
| Document-grounded follow-up questions | BE2 through BE1 | FE2: questions, loading/busy/timeout state, answer evidence and insufficient-evidence response |
| Queued/running/partial/review/failed result states | BE2 -> BE1 | FE2: actual job state, partial findings, retry/review action |
| Real clause-level processing progress | BE2 -> BE1 | FE2: progress bar from real counts; FE1: extracting/indeterminate state when counts unavailable |
| Readiness and recoverable service errors | BE2 + BE1 | FE1: service status; FE2: model unavailable/busy/timeout errors without replacing them with mock results |
| Temporary sessions, expiry and deletion | BE1 propagates cleanup to BE2 | FE1: consent/retention notice and Delete; FE2: clear results/questions and stop polling |
| Official legal-aid information | Reviewed backend data | FE2: NALSA/DLSA information only when verified; label external links; no entitlement guarantee |
| Local explanation export | No new backend endpoint required | FE2: explicit Markdown/print export with evidence, limitations and provenance |
| Dataset preparation, model training and evaluation | BE2 | INTERNAL ONLY: terminal bars, artifacts, metrics and PROGRESS.md; no public training dashboard required |
| GPU queue, local model runtime and temporary indexes | BE2; BE1 integration | INTERNAL ONLY: expose useful status/errors; browser never calls raw model/private ML ports |

Potential classifier cue categories include limitation of liability, unilateral termination/change, content removal, contract by using, choice of law, jurisdiction and arbitration. These may appear as attention topics, not automatic findings of illegality. The category field is a string: FE2 should provide readable labels for known categories plus a safe fallback for unknown/new categories, rather than crash or drop the finding.

### Progress and readiness details to implement consistently

- Public status remains Contract v1: analysis queued/running/complete/needs_review/failed; document status uses its separately listed values. Do not copy private route paths into browser code.
- Required analysis progress fields remain completed_clauses and total_clauses. The current BE2 typed contract also defines optional stage and failed_clauses. BE1 should preserve these optional fields when provided; FE2 must also work when they are absent.
- completed_clauses counts processed clauses, including failed attempts in the current BE2 contract. failed_clauses is a subset. Thus 8/8 processed with 2 failed is NOT eight successful explanations. FE2 must show both processing completion and result coverage/warnings. Stage names are readable status text, not a closed enum the UI may assume.
- Percentage is computed only when total_clauses > 0. Otherwise show an indeterminate state. Do not estimate progress from elapsed time. A 100% processed bar must not override needs_review/failed status.
- After a timeout, show the error and a controlled retry. Backend owners must prove another job can run. Do not automatically duplicate analysis/question jobs.
- Health capability/readiness fields were described conceptually, not frozen as an exact JSON object. BE1 owns publishing one concrete health fixture agreed with BE2; FE1 consumes it through its API client. Missing readiness data means unknown, not ready. Missing fluent-review evidence must not become a tested-language badge.
- Expiry countdowns require a real server expiry timestamp/remaining-time field. Until BE1 publishes one, show the disclosed retention policy, not a fabricated ticking deadline.
- Translation checks/pivot mappings are private implementation data unless intentionally exposed. The existing warnings, limitations and review_status carry user-facing problems; do not add a mandatory response field unilaterally.

### Resolve these integration ambiguities once, before connecting real services

1. BE1 publishes a public extraction response fixture and PATCH response with revision semantics. FE1's explicit Confirm action can PATCH an empty corrections array with confirmed language/type; BE1 records review confirmation. A genuine change invalidates cached findings. Do not add an unannounced review endpoint.
2. BE1 supplies analysis_id, document_id and document_revision to BE2. BE2 echoes them, rejects conflicting ID reuse and runs the asynchronous private job API. The earlier synchronous-response wording in the BE1 role is superseded by this asynchronous approach.
3. Public question requests carry analysis_id; BE1 derives document_id/revision from the authenticated current session and forwards them to the private question API. Browsers do not invent private-session metadata.
4. Every reference_id must resolve to a supplied reference record. For analysis this is result.references. The current QuestionAnswer shape has IDs but no references array, so v1 questions may cite only official references already supplied with the selected analysis (plus document clauses). If BE2 needs a newly retrieved official source, agree and document an optional answer.references field with BE1/FE2 before using it; otherwise omit that reference and report the limitation.
5. A language change starts/loads the same reviewed revision in the selected output language. Source text does not change. FE2 ignores late responses for the old language. BE1 deletes all associated jobs/translation caches on document deletion, not just the most recent language result.
6. Python 3.11 was the original preference, not a hard requirement. A verified isolated Python 3.12 environment is acceptable when 3.11 is unavailable and the required dependencies/tests pass. Backend services need compatible JSON contracts, not identical Python installations.

FE1 and BE1 own the shared public fixtures and schemas. Put agreed examples in contracts/ when ready: extraction, analysis-start, queued/running/partial/completed analysis, question, health and error. FE2 can meanwhile derive visibly labelled fixtures from this file's shared contract. Examples must exercise all four item kinds, optional references/progress fields, null DOCX pages, an unresolved deadline, an unsupported language, a revision conflict and a model-busy state. Do not silently alter existing implementation to match a new fixture: coordinate the compatibility change.

### Required versus deferred scope

Required product targets: upload/review; clause explanations with evidence; potential attention flags; dates/deadline uncertainty; agreement/FIR/notice routing; tested en/hi/pa input/output paths; legal-aid links; temporary processing/deletion. Target-language success must be demonstrated, not assumed. Grounded questions and explicit export are agreed additional features; keep them after the primary analysis path works.

Deferred unless explicitly reprioritized: enforceable legal-deadline calculations, arbitrary languages/scripts, handwriting, automatic legal decisions, full Indian-law coverage, automatic court/complaint filing, public training dashboard, cloud accounts, cloud vector database and large-LLM fine-tuning. No risk/safety percentage is part of v1.

### End-to-end acceptance handoff

Use the same five labelled/redacted demo documents across all owners: ordinary agreement; agreement with planted attention clauses; notice with missing receipt-date anchor; fictional/redacted FIR; scanned page. Add a fluent-reviewed Hindi and Punjabi sample and preserve original evidence when output language differs.

Check upload -> extraction review -> real local analysis -> clause/source navigation -> selected-language output -> unresolved-deadline display -> grounded/unsupported questions -> export -> delete. Also check busy, timeout, partial failure and stale revision/language results. A static screen or mocked request passing does not establish that integration works.

Tell teammates when this addendum is updated. Implementation bugs and agreed contract changes must be recorded in the repository; don't rely on details available only in a chat.

---

This role belongs on the strongest laptop: measured RTX 5070 Ti Laptop GPU, approximately 12 GB VRAM, with user-reported 32 GB RAM. Give this entire file to your coding assistant. You own the intelligence pipeline; BE1 owns uploads, user sessions and public routes.

## Owned deliverables

apps/ml/{service,training,inference,retrieval,translation,validation}; dataset/source manifests; classifier artifacts and metrics; local model setup notes; frozen evaluation fixtures; private ML service. Do not modify FE root files or public API routes independently. Keep downloaded weights/data out of Git where required by size/privacy/terms.

Deliver a trained small classifier plus a working pretrained LOCAL generator. Training a classifier is real training; indexing documents or writing prompts is not language-model training. Do not claim the local LLM was trained by your team.

## First 20-minute gate

- Verify nvidia-smi and usable VRAM, then choose a compatible current runtime. GPU driver visibility does not prove installed PyTorch/CUDA compatibility; run a tiny GPU operation before transformer training.
- Load a verified 4-bit GGUF quantization of Qwen/Qwen3-4B-Instruct-2507 using CUDA-enabled llama.cpp, checking source model identity/license and actual downloaded artifact. If GGUF/runtime compatibility blocks progress, test a compatible local Transformers quantized setup; do not spend the whole round changing inference stacks.
- Explain ONE short clause with a quote and structured output. Check actual latency and memory. Start with 4K–8K context as a tunable budget, short output and one request at a time; do not allocate the maximum advertised context.
- Train a CPU TF-IDF baseline while model download/setup happens. The classifier must not depend on the LLM.
- If model cannot start, tell BE1 immediately. Return MODEL_UNAVAILABLE, not canned successful explanations.

Keep the generator GPU-resident for the demo. Run lightweight classifier/embeddings on CPU initially to leave VRAM headroom. If transformer training is attempted later, stop/unload generation deliberately and restore the demo afterward. No large-model fine-tuning on the Round-1 critical path.

## Dataset plan and exact task boundaries

1. UNFAIR-ToS via LexGLUE: FIRST training task. The documented benchmark has 9,414 sentences (5,532 train / 2,275 development / 1,607 test) and eight concern types. Use original label mappings from metadata rather than hard-coded label ordering.
   Categories: limitation of liability, unilateral termination, unilateral change, content removal, contract by using, choice of law, jurisdiction, arbitration. Normalize into stable internal slugs. These are potential concern cues from European terms of service, not Indian enforceability judgments.
2. CUAD: 510 commercial contracts, 13,000+ annotations, 41 clause types. Use annotated spans to experiment with clause types/extraction. Do not pretend every label corresponds to danger or turn unannotated text into a guaranteed negative.
3. LEDGAR via LexGLUE: 80,000 contract provisions / 100 topics. Optional second-stage topic tagger after first integration. Preserve official splits and inspect topic mapping.
4. MILDSum: 3,122 Indian judgments with English/Hindi summaries described, but repository provides samples and asks authors for full data. Do NOT make full access a dependency tonight.
5. Local evaluation: independently reviewed agreement, loan/lease-style clauses, notices, fictional/redacted FIRs, and fluent-reviewed hi/pa examples. Keep synthetic examples labelled, and never train on the independent evaluation set.

Download only needed subsets. Record URL, version/hash, license, row counts, label mapping, preprocessing and split policy in a data manifest. Source pages exist; actual download/parsing still needs a smoke test. Inspect exact reuse terms instead of treating all foreign legal text as unrestricted.

## Classifier implementation

Baseline: word + character TF-IDF features -> one-vs-rest logistic regression for multi-label UNFAIR-ToS prediction. Preserve empty labels as 'no configured cue detected'; do not introduce a learned 'safe' guarantee. Fit vocabulary/normalization on TRAIN ONLY. Address class imbalance using training-only methods. Tune per-label thresholds on development data, then evaluate test once.

Compare a second baseline with frozen multilingual-e5-small embeddings + trained classification head if time permits. For retrieval use E5's documented query:/passage: prefixes and normalized vectors. A frozen embedding classifier is still English-trained when labels are English. A future SetFit fine-tune must use a separate classifier encoder/version so retrieval indexes are not silently invalidated.

Report per-label precision/recall/F1, macro-F1, micro-F1 and false-negative examples. Accuracy alone is misleading for sparse multi-label data. Do not invent benchmarks. Save classifier, vectorizer, labels, thresholds, training config, metrics and artifact hash. Load only your trusted local artifacts.

Penalty and automatic-renewal cues are not covered by all UNFAIR-ToS labels. Implement separately reviewed lexical/context rules, including negation and exceptions. Mark detector = rule. An arbitration clause is an attention topic, not automatically an unlawful clause. Low model score is not a safety assessment.

## Multilingual path

For each non-English clause:
- Preserve original reviewed_text and clause_id.
- Locally translate only a working copy to English. Store source/pivot mapping per clause, translation model/version and needs-review status.
- Classify English pivot only if translation quality checks pass.
- Keep evidence quotes in ORIGINAL reviewed_text. English-pivot offsets cannot be used as original-document coordinates.
- Explain in chosen output language, then check immutable identifiers, numbers, dates and allegations.
- If translation fails, do not run an English classifier on raw Punjabi and pretend the outcome is reliable. Return needs_review.
- Mixed-language clauses need explicit checks; unsupported scripts/romanization get review or refusal.

Use Qwen as a candidate local translator, tested against fluent-reviewed samples. IndicTrans2 is a dedicated local alternative if setup and verification are feasible. Neither is proven correct for your documents by merely downloading it. Translating training examples synthetically does not establish multilingual validation; keep separate reviewed language tests. Do not advertise all languages.

## Analyse every clause; route document types

Agreement: classify each clause, extract obligations/payments, add reviewed attention rules, inspect related definitions and cross-references, then explain.
FIR: do NOT use unfair-contract classifier. Extract who alleges what, named roles, dates, location and sections as recorded. Phrase assertions as allegations. Unknown/incomplete facts remain unknown.
Notice: extract issuer, recipient, action demanded, exact dates and relative periods. Do not infer liability or calculate legal deadlines.
Other: conservative literal explanation with reduced scope and clear review warning.

For long clauses use sentence/paragraph windows retaining the parent clause and relevant definitions. Do not silently truncate at encoder context limits. Aggregate cue outputs with an explanation of limitations. Provide analysed/total and failed clause IDs.

## Retrieval and legal references

Build two distinct indexes: per-session reviewed document clauses and curated official references. Start with BM25 + local embedding cosine similarity; in-memory NumPy is sufficient for small corpora, FAISS optional. No hosted vector store.
- Exact-match cited section identifiers before semantic fallback.
- Filter official references by law/version/jurisdiction metadata.
- Keep definitions/cross-references close to the clause being explained.
- If reference match is uncertain, explain only supplied text and say the legal reference was not verified.
- Preserve older law citations in older documents. No automatic IPC/CrPC renumbering.
- Official legal-aid links can be a reviewed static card; do not let the model invent contact details.
- Dataset examples are training evidence, never authorities cited to the user.

## Generation, schema and validation

Prompt contains separate system instructions, selected clause texts, optional retrieved references and a strict output schema. Uploaded instructions remain quoted data. Never give the model tool access for a document's requested actions.

Ask for a plain explanation, attention reasons, exact clause IDs and evidence quotes, missing information and limitations. Avoid whole-document claims of legality. For responses in hi/pa, original-language quotes remain unmodified.
- Validate schema and clause/reference IDs.
- Confirm each quote is an exact substring of reviewed original text.
- Check names, amounts, dates and sections against evidence; explicitly label any derived interpretation.
- Check negation and allegations through independent tests; string matching alone cannot prove semantic entailment.
- One repair attempt for malformed output; then needs_review/failed with explicit reason.
- Do not use the same generator's second opinion as ground truth.

For relative deadlines return unresolved source period + missing anchor. Version 1 has no enforceable-deadline calculator. Keep classifier score separate from extraction quality and legal certainty.

## Private service and handoff to BE1

Private localhost service on 8001; local LLM on 8080. Provide GET /internal/health; POST /internal/analyse -> 202 analysis_id; GET /internal/jobs/{analysis_id} -> real status/progress/result; DELETE /internal/jobs/{analysis_id}; POST /internal/question -> validated answer. BE1 sends only reviewed clauses and document revision. Use Contract v1 result schema below.

Bound GPU queue to one generation at a time initially. Provide timeout/busy errors, actual progress and cancellation tombstones so deleted jobs cannot reappear. Private results must expire and deletion removes translated/pivot text and indexes. No persistent document-content logs.

Hand BE1: exact private request/response sample, startup command, model path variables, artifact version, health state, limits, timeouts and tested language matrix. Pair for one real PDF-to-result before training improvements.

## Evaluation and judging evidence

Prepare five mixed documents and independent annotated clause expectations. Add negation pairs, missing receipt dates, OCR digit corruption, unfamiliar clauses, unsupported language, code-like instructions inside a document and unsupported questions.
- Benchmark baseline classifier; preserve held-out documents/splits.
- Check explanations for unsupported claims and missed conditions.
- Check en/hi/pa source/output combinations, manually reviewed; record pass/fail by stage.
- Verify FIR allegations stay allegations.
- Measure p50/p95 latency only if sufficient runs; otherwise report individual timings and sample count.
- Compare local model alone with full pipeline on the SAME independent cases. Record actual changes, including regressions.
- No external API judges during runtime. Optional permitted external checking uses synthetic/redacted fixtures with explicit authorization and is labelled secondary; it is not ground truth.

## Prompt to give your coding assistant

Implement BE2 only from this complete handoff. Inspect hardware/runtime and existing repo first. Train the English UNFAIR-ToS baseline with correct splits, deliver real metrics/artifacts, load a local quantized Qwen 4B generator, and implement the private async ML API agreed with BE1. Analyse all reviewed clauses, route FIR/notices separately, preserve source/pivot mappings for translation-assisted hi/pa, build separate reference/document retrieval, validate evidence and support deletion. Do not fine-tune a large LLM before the first real integrated demo works. Do not fabricate results, use external inference, train on user uploads or claim Indian legal validity from foreign labels. Report exact checks, versions and unsupported language cases.

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

