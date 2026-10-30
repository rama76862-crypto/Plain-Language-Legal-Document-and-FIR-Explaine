> Update, 30 October 2026: the completion work and current evidence are documented in apps/ml/COMPLETION.md and BACKEND-COMPLETION.md. Earlier counts and language results below are historical snapshots.

# Backend 2 progress

The checklist bar counts completed milestones only; it is not a time estimate
or a product-quality score.

**Checklist completion:** `[#######-]` 7/8 milestones passed

| # | Milestone | Status | Owner | Evidence | Next step | Blocker / limitation |
|---|---|---|---|---|---|---|
| 1 | Environment and typed interfaces ready | passed | Coordinator | Python 3.12.10 isolated venv; pinned requirements pass `pip check`; typed Contract v1 imports and `compileall` pass. Local inference is verified separately on the RTX 5070 Ti with the pinned CUDA llama.cpp runtime; the installed ROCm Torch tensor path on AMD 890M is not used as CUDA evidence. | Recreate the venv and ignored artifacts using `README.md` on a clean clone. | Model/data downloads and trained classifier artifacts must be recreated locally. |
| 2 | Required dataset subset downloaded, parsed and manifested | passed | Classifier/data owner | `python -m apps.ml.training.train` loads only LexGLUE `UNFAIR-ToS`; the manifest records the pinned dataset revision, CC-BY-4.0, inspected features/label order, split names/counts (5,532/2,275/1,607), and hashes. | Keep fixtures independent of this training corpus. | No source-document IDs; normalized train/test text overlap exists. |
| 3 | CPU baseline trained and evaluated with saved artifacts | passed | Classifier/data owner + Coordinator | Held-out test macro-F1 `0.736671`, micro-F1 `0.734584`. Per-label recalls imply **49 missed label assignments**. The capped export saved **22 false-negative records** containing **21 distinct example IDs**; total unique affected test sentences cannot be recovered from that capped export. See [`training/METRICS.md`](training/METRICS.md). No held-out retuning or rerun was done. | Let the next normal single test pass record full-matrix unique affected rows. | 33 unique normalized train/test text overlaps can make scores optimistic; source IDs are unavailable. Empty predictions do not prove safety. |
| 4 | Real local model and one-clause service path verified | passed | Coordinator | Pinned Qwen3-4B-Instruct-2507 Q4_K_M GGUF SHA-256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`; llama.cpp b12000 CUDA commit `68d20b884c3878217de79eade0a249efde96ab38` completed generation on RTX 5070 Ti. The actual one-clause result in [`service/fixtures/real_local_result.json`](service/fixtures/real_local_result.json) has 1/1 coverage, schema-valid output, and source-exact attached evidence; 8 health polls stayed responsive (maximum 748.8 ms). Delete returned the tombstone (410). Result remains `needs_review`. | Obtain independent source-semantic review before promoting generated claims. | Exact quotes and schema do not prove entailment; see [`evaluation/REAL_LOCAL_REVIEW.md`](evaluation/REAL_LOCAL_REVIEW.md). |
| 5 | Official references curated and retrieval checks passed | passed | Agent B + Coordinator | Six official records with URLs, law/section, jurisdiction, version/date, source locators, excerpt hashes and reuse notes are in [`data/references.json`](data/references.json) and [`data/REFERENCE_SOURCES.md`](data/REFERENCE_SOURCES.md). Focused curation tests: 8 passed; full suite: 86 passed. Match tests cover exact, wrong-section, missing and competing law/version cases. | Recheck source versions and references against each concrete demo document. | DoCA E-Commerce Rules PDF could not be opened directly; excerpts were checked against the official indexed source preview. Direct source and amendment/reuse audit remains needed before release. An exact section match does not prove interpretation. |
| 6 | Private asynchronous service hardened and exercised | passed | Coordinator | Full `apps/ml/tests`: 86 passed; `compileall` and `pip check` pass. Tests cover bounded queue, saturation, timeout recovery, deletion during generation with late-result suppression, a succeeding job after timeout/deletion, stale revisions, expiry cleanup and question-index cleanup. Final real local run processed 12 clauses across four synthetic documents, reported 11/12 analysed coverage and one failed clause; 97 health checks had maximum 468.84 ms. Services bind to loopback. | Run the same Contract v1 request with BE1 when it is available. | BE1 is not in the workspace. The FIR clause without a law name correctly fell back rather than attaching an authority. |
| 7 | Multilingual and failure-path evaluation recorded | in progress | Agent A + Coordinator | Real pinned-model run attempted all nine source/output cells; every final output passed schema after at most one controlled repair. Four of six Indic-target cells passed the script check; English→Punjabi and Hindi→Punjabi failed it. Protected lexical markers changed in six cells. Hindi/Punjabi receipt-relative duration fixtures now preserve `needs_information`/missing `receipt_date` on a matching English display and reject a mismatched value or unit. All nine language cells remain `needs_review`; fluent review was not performed. Full matrix below; raw outputs are in ignored `runtime/language-matrix-smoke.json`. | Arrange independent fluent review, then rerun the same fixtures; do not promote any cell yet. | No fluent-reviewed Hindi/Punjabi set is available; no language path is fully supported. |
| 8 | Independent BE1 handoff and real smoke available | passed | Coordinator + Agent C | [`README.md`](README.md) documents clean-clone setup, artifact recreation, training, serving, tests and smoke commands. The reviewed-clause Contract v1 request and actual local result are checked in under [`service/fixtures/`](service/fixtures/). Six separate synthetic evaluation fixtures and their source-comparison findings are checked in under [`evaluation/`](evaluation/). | Connect and run the same private contract fixture when BE1 is ready. | Cross-service integration was not exercised; no frontend, OCR, upload, or public BE1 route was added. |

## Real local source/output matrix

Attempts include the initial generation and, where needed, one controlled
repair. “Script pass” checks expected target-script characters; it is not a
fluency or legal-accuracy test. Protected-marker failures are reported
separately. All nine cells returned `needs_review`, and no cell received fluent
review.

| Source → output | Attempts | Structured schema | Target script | Protected markers changed | Fluent review | Outcome |
|---|---:|---|---|---|---|---|
| English → English | 1 | passed | not applicable | none detected | not performed | `needs_review` |
| English → Hindi | 2 | passed | Devanagari passed | none detected | not performed | `needs_review` |
| English → Punjabi | 2 | passed | Gurmukhi **failed** | negation | not performed | `needs_review` |
| Hindi → English | 2 | passed | not applicable | legal codes | not performed | `needs_review` |
| Hindi → Hindi | 2 | passed | Devanagari passed | none detected | not performed | `needs_review` |
| Hindi → Punjabi | 2 | passed | Gurmukhi **failed** | legal codes | not performed | `needs_review` |
| Punjabi → English | 2 | passed | not applicable | negation | not performed | `needs_review` |
| Punjabi → Hindi | 2 | passed | Devanagari passed | negation | not performed | `needs_review` |
| Punjabi → Punjabi | 2 | passed | Gurmukhi passed | legal codes | not performed | `needs_review` |

The baseline failures were reproduced with the real local model: English→Punjabi
missed Gurmukhi, while initial Hindi→Punjabi and Punjabi→Punjabi responses
omitted the required explanation field (the failure type varied in an older
Punjabi baseline). The repair fixed those structured fields, but final
English→Punjabi and Hindi→Punjabi outputs still fail their script check. Hindi
pivot lexical checks passed in the recorded examples; a Punjabi pivot changed
negation. These mechanical checks do not establish translation accuracy.

## Runtime progress rules

- Report downloaded bytes only when the source provides a reliable total;
  otherwise show an indeterminate spinner.
- Report actual parsed examples and completed clauses. Keep failed and skipped
  clause counts separate.
- Classifier training reports fitted phases and elapsed time, not invented
  epochs.
- Local generation reports its current stage; queued jobs remain queued, and
  no percentage is estimated from time.
- Never print document text, credentials, or model tokens in progress output.
