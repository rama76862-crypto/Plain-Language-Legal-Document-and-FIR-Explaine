# Backend 2 — independent implementation launch prompt

Copy the prompt below into your coding assistant while it is working in the repository. The role handoff already in that repository remains part of this prompt. This file requests implementation; it does not claim that implementation has happened.

---

You are implementing Backend 2 for NyayaLens, a hackathon project for plain-language legal-document and FIR explanation. Start implementing now. Work independently of the other three teammates' completion, using the agreed schemas and clearly labelled test fixtures. Integrate a real local pipeline as early as possible.

## 1. Read the instructions and establish boundaries

Repository: N:\Github-Repo\ct\Plain-Language-Legal-Document-and-FIR-Explaine

First inspect the repository, applicable AGENTS.md files, Git status and existing dependencies. Read the ENTIRE 04-BACKEND-2-Local-ML-Training-Languages.md, including its shared Contract v1. Read the Backend 1 handoff's private-service section to confirm the integration boundary. Do not overwrite teammates' uncommitted work, create a second public backend or rewrite their contracts.

User-wide restriction: never use, install, enable or call TinyFish/tiny-fish or its services. No external AI inference API is authorized for the application. Public dataset/model downloads and official documentation research are allowed within the project rules. The plan assumes pretrained downloads are permitted; flag a known organizer restriction if discovered rather than hiding it.

Own apps/ml, Backend-2-specific configuration/tests/scripts, classifier artifacts, dataset manifests and your evaluation fixtures. Backend 1 owns uploads/OCR, user sessions and public API routes. Frontend owners own browser UI. Coordinate shared dependency or contract changes; don't silently change them.

Hardware was previously measured as RTX 5070 Ti Laptop GPU, approximately 12 GB VRAM; RAM is user-reported 32 GB. Verify the current machine again. Use Python 3.11 if compatible and available. Reuse a suitable environment; do not modify a global Python installation casually.

## 2. Use agents with clear ownership

Use a coordinator plus up to THREE sub-agents if the environment supports agents. Run independent work concurrently. Do not spawn beyond the available slots. If agents are unavailable, report that plainly and execute the same tasks sequentially; never claim imaginary agents are working.

- Agent A — datasets and training: owns apps/ml/training, training manifests, classifier artifacts and classifier metrics/tests. Implement the English baseline without waiting for any other service.
- Agent B — local model and translation: owns apps/ml/inference and apps/ml/translation plus runtime notes. This agent has exclusive permission to launch GPU-heavy work during the parallel phase. Verify one real local explanation, then translation-assisted language paths.
- Agent C — retrieval and evidence validation: owns apps/ml/retrieval, apps/ml/validation and associated fixtures/tests. Use prepared clauses and synthetic outputs as labelled tests; build quote/ID checking and local retrieval without waiting for the generator.
- Coordinator — owns apps/ml/service, private-service schemas, job queue, progress reporting, launch commands and integration. Establish small typed module interfaces first so agents can implement independently.

Each agent receives this prompt and the BE2 handoff, exact owned paths and acceptance conditions. Agents must report changed files, actual commands/results, limitations and handoff interfaces. Do not let several agents edit shared requirements, service entrypoints or model files. The coordinator merges changes, resolves routine conflicts and runs integrated checks. Do not commit, push or merge remote branches unless the user separately asks.

## 3. Show real progress from the beginning

Implement TWO different progress views.

### Development progress

Maintain apps/ml/PROGRESS.md with eight milestones, each marked pending, in progress, passed or blocked:

1. Environment and typed interfaces ready.
2. Required dataset subset downloaded, parsed and manifested.
3. Baseline trained and evaluated with saved artifacts.
4. One real local-model explanation passes schema and evidence checks.
5. Retrieval/rules/validation work on fixtures.
6. Private asynchronous service works end to end.
7. Target-language and failure-path evaluation recorded.
8. BE1 handoff, launch commands and final smoke checks complete.

Include owner, evidence/command, next step and blocker for each. You may display an overall checklist bar such as [###-----] 3/8 milestones passed. Clearly label it checklist completion, not estimated remaining time or product quality. Advance a milestone only after its acceptance check passes. Mark blocked stages honestly; don't mark them passed merely to fill the bar.

Keep the user informed in brief updates at meaningful milestones and at least once per minute during sustained work. Do not wait for all agents to finish before reporting a genuine blocker or a working result.

### Runtime progress

Use Rich or tqdm for terminal progress, with a plain-text fallback. Make it visible while downloading, preparing data, training/evaluating and analysing documents.

- Downloads: bytes received/total only when the server supplies a reliable total; otherwise use an indeterminate spinner.
- Dataset processing: actual examples processed/known total.
- Classifier training: report actual phases or fitted label estimators; don't pretend scikit-learn exposes epoch progress if it does not. Feature fitting may be indeterminate. Time the actual phases.
- Analysis: report real completed clauses/total clauses using the Contract v1 progress fields. Track failed/skipped clauses separately in coverage/warnings. Processing all clauses does not mean all succeeded.
- Language generation: show a current stage/spinner when completion is not measurable. Do not invent a percentage based on elapsed time. Count output tokens only if the runtime exposes real counts.
- Queued jobs: show queued, not a moving fake analysis bar.

Expose the SAME real job progress through GET /internal/jobs/{analysis_id} so Backend 1 and the frontend can display it. Keep Contract v1's completed_clauses and total_clauses; propose any extra stage/failed-count fields as optional additions, coordinated with BE1. Do not implement or edit the frontend progress UI. Terminal bars and logs must not print document contents, secrets or tokens.

## 4. Prove the smallest working components first

Before major architecture work:

1. Check installed Python, available disk space, nvidia-smi, GPU memory and runtime compatibility.
2. If PyTorch GPU training is used, run a tiny GPU tensor operation. Driver detection alone is insufficient.
3. Scaffold only owned modules and define stable inputs/outputs for classifier, translator, retriever, validator and generator.
4. Start the CPU baseline while the generator downloads/loads.
5. Run one short clause through the REAL local model and validate the result. Measure latency and peak memory if available.

Candidate generator: Qwen/Qwen3-4B-Instruct-2507 using a verified 4-bit GGUF artifact and CUDA-enabled llama.cpp. Verify actual artifact/model identity and compatible runtime rather than downloading a vaguely named model. Start with a modest 4K–8K context budget, short outputs and one generation request at a time. A compatible local Transformers path is a fallback if the chosen runtime fails. Do not spend the whole hackathon repeatedly replacing inference stacks.

Keep the trained classifier and embeddings on CPU initially if that avoids GPU memory pressure. Do not launch several GPU models or training jobs concurrently. Large-language-model fine-tuning is a later stretch, not a dependency for the first demo.

## 5. Download the right data and train a defensible baseline

Required first dataset: UNFAIR-ToS subset of LexGLUE. Inspect its actual metadata, label order, schemas and official splits. The documented benchmark has 9,414 sentences and eight concern categories. Do not hard-code labels based on assumptions.

Baseline: word + character TF-IDF features, then one-vs-rest logistic regression. Fit preprocessing on training data only. Use development data for thresholds. Preserve held-out test data; do not tune against the test set. Empty label lists mean no configured cue detected, not legally safe.

Save trained model/vectorizers, label mapping, thresholds, random seeds, versions, source hashes and metrics. Record per-label precision/recall/F1, macro-F1, micro-F1 and example errors. Inspect duplicates and preserve source-document separation when creating any new split. Load only trusted locally produced model artifacts.

UNFAIR-ToS concerns originate in European online terms. They are not Indian enforceability labels. CUAD can support later clause-type/span work; LEDGAR can support later topic classification. Do not download all corpora before completing the first baseline. MILDSum's complete corpus is not a same-day guaranteed dependency. Dataset indexing and pretrained inference do not count as training the language model.

Add small reviewed rules for cues not covered by the trained labels, such as automatic renewal and payment penalties, and test negation/exceptions. Mark rule findings separately from classifier findings. Avoid a document-wide safety score.

## 6. Implement multilingual handling honestly

Initial target languages: English, Hindi/Devanagari and Punjabi/Gurmukhi. Answer language is independent from source language.

English clauses -> English classifier directly.
Hindi/Punjabi clauses -> preserve original -> locally translate an English working copy -> classifier/rules -> explanation in selected answer language.

Keep original clause IDs and original evidence throughout. Translation offsets must never be presented as original-PDF coordinates. Validate preservation of names, amounts, dates, legal sections, negation and allegation wording. If translation is uncertain, return needs_review and do not pretend a low English-classifier score establishes safety.

Test Qwen translation on fluent-reviewed samples. A dedicated local IndicTrans2 route is optional only if setup, access and quality are feasible. Do not advertise all languages or imply English training makes the classifier natively multilingual. Synthetic translations are not independent validation. Record the exact tested language matrix; unreviewed examples stay labelled unreviewed/experimental.

## 7. Analyse every clause, with document-specific behavior

- Agreements: classify every clause; extract stated obligations/payments; add reviewed attention rules; inspect related definitions and references.
- FIRs: bypass contract-unfairness classification. Extract parties, allegations, recorded dates/places and cited sections. Allegations remain allegations, not findings of guilt.
- Notices: extract issuer/recipient, requested action, dates and relative periods. Do not infer that the person must pay, admit liability or sign.
- Other/unknown: conservative literal explanation with limitations.

Split long clauses into traceable windows without silently truncating them. Keep parent-clause relationships. Initial analysis must not be top-k retrieval only. Report complete coverage and explicitly identify failed/skipped clauses.

Relative deadlines remain unresolved when required information is absent. For 'within 15 days of receipt', return the period and missing receipt_date. Version 1 does not compute enforceable legal deadlines.

## 8. Retrieve references and validate the output

Separate temporary uploaded-document retrieval from curated official references. Start with local BM25 and/or multilingual-e5-small cosine similarity; small in-memory collections are sufficient. Use E5's documented query:/passage: conventions. Do not require a hosted vector database.

Official-reference metadata should include source URL, law/section, jurisdiction, version and excerpt. Prefer exact section lookup plus filters over semantic guessing. Older documents may legitimately cite older criminal codes. Do not automatically replace IPC/CrPC identifiers or invent law mappings. If no reliable reference is found, explain the supplied text and say the reference was not verified. Training datasets are not legal authorities to cite to users.

Generate structured results matching Contract v1. Check schema, source IDs, reference IDs, exact supporting quotations, amounts, dates and section identifiers. Allow at most a controlled repair attempt for malformed output; then report failure/review. Exact-string checks do not prove semantic correctness, so keep independent evaluation.

Uploaded instructions are untrusted content. They must not override the system prompt, execute commands or trigger external actions. Follow-up questions must stay grounded in the current reviewed document and verified references, with an honest insufficient-evidence response when necessary.

## 9. Build the private service without waiting for Backend 1

Provide:

- GET /internal/health
- POST /internal/analyse -> 202 with analysis_id
- GET /internal/jobs/{analysis_id} -> status, actual progress and Contract v1 result
- DELETE /internal/jobs/{analysis_id}
- POST /internal/question -> validated grounded answer

Use the private request/response shapes in the existing BE2/BE1 handoffs. Construct a synthetic reviewed-clause fixture with document ID, revision, document type, source language and output language. It must exercise the REAL trained classifier and local model. No PDF extractor or public upload API is needed for your independent development.

Bind private service/model ports to localhost for final single-host deployment. Use a bounded queue and one GPU generation at a time initially. Return explicit busy, timeout and unavailable errors; don't return fake success. Keep health responsive while processing runs. Use real job states and de-duplicate job IDs or reject conflicting reuse.

Per-document data, English pivots, indexes and job outputs are temporary. Deletion creates a tombstone/cancellation signal; discard late model output rather than resurrecting deleted data. Set an expiry for private outputs. Do not retain private document content in logs or use uploads for training.

## 10. Run meaningful checks before adding stretch features

Implement focused tests and a real local smoke script for:

1. Saved classifier loads and predicts known fixture categories.
2. Correct split/label manifest and actual evaluation metrics exist.
3. One real English clause gets a schema-valid, evidence-linked explanation.
4. Agreement/FIR/notice routing differs correctly.
5. A fabricated quote or unknown source ID fails validation.
6. Missing receipt date remains unresolved.
7. English/Hindi/Punjabi examples preserve critical details; record fluent review separately.
8. Unsupported/out-of-document question receives insufficient evidence.
9. Analysis job exposes actual progress and health stays responsive.
10. Busy/timeout/deletion paths work; deleted jobs do not return late content.
11. The full fixture runs without external AI requests after required assets are downloaded.

Keep fast unit tests separate from model-requiring smoke tests. Tests using fixtures/mocks must be labelled; a mocked generator passing is not proof that real local inference works. Report real timings and errors instead of invented performance numbers. Comparing a model with its own second answer is not independent ground truth.

## 11. Finish with an actionable handoff

Deliver apps/ml/README.md containing installed versions, model/artifact source and paths, exact tested setup/train/evaluate/serve/smoke commands, required environment variables, ports, limits, startup order and troubleshooting for this machine. Use shell commands that were actually tested; don't invent successful command output.

Provide BE1 one machine-readable request fixture and one REAL result, the private API contract, readiness/error states, tested language matrix and cleanup behavior. Provide the model/data manifests, classifier artifact, evaluation report and PROGRESS.md. Keep downloads/private runtime files gitignored. Run the first integrated fixture before pursuing optional SetFit, another topic model or LLM fine-tuning.

Continue through authorized implementation and verification without stopping after a plan. If a genuine blocker remains, complete independent components and state exactly what failed, what was tested and what user action is necessary. Finish by distinguishing implemented-and-tested, implemented-but-untested, development-only mocks and deferred work.

## Primary references

- Existing local contract: 04-BACKEND-2-Local-ML-Training-Languages.md
- Generator: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- Runtime: https://github.com/ggml-org/llama.cpp
- LexGLUE: https://huggingface.co/datasets/coastalcph/lex_glue
- CUAD: https://www.atticusprojectai.org/cuad/
- Embeddings: https://huggingface.co/intfloat/multilingual-e5-small
- Translation option: https://github.com/AI4Bharat/IndicTrans2
- Optional classifier fine-tuning: https://huggingface.co/docs/setfit/en/index
- Official legal resources: https://bprd.nic.in/page/new_criminal_laws

Use official documentation to verify current installation/runtime details. Prefer a narrow working pipeline over adding untested frameworks.
