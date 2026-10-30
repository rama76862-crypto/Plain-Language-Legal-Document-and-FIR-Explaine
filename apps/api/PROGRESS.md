> Update, 30 October 2026: the completion work and current evidence are documented in apps/ml/COMPLETION.md and BACKEND-COMPLETION.md. Earlier counts and language results below are historical snapshots.

# Backend 1 progress

Original shared checklist: **[#######-] 7/8 passed**. This counts checked work, not time or product quality. All remaining BE1-only implementation/verification is completed; the last shared milestone requires the actual other services.

| Milestone | Owner | Status | Command/evidence | Next step |
|---|---|---|---|---|
| Environment/contracts | Coordinator | passed | Isolated Python 3.12.10; pinned dependencies; examples and ten-operation OpenAPI exported/tested | Team reviews existing additive contract decisions |
| Upload/storage | Coordinator | passed | Actual-byte/body limits, MIME, token isolation, private paths, interrupted upload cleanup pass | Frontend hookup when available |
| PDF/DOCX extraction | Agent A/coordinator | passed | Real native parsers/order/refs; hard subprocess time/memory limits; kill/recovery tests | None for independent scope |
| OCR/review/revisions | Agent A/coordinator | passed | Local Tesseract eng/hin/pan; real English/Hindi/mixed scans; corrections/stale review checks pass; Punjabi quality limitation recorded | Human review; broaden Punjabi quality evaluation with actual documents |
| Sessions/deletion | Agent B/coordinator | passed | Lifecycle 22 passed, 1 Windows privilege skip; locked files/restart/admission/cancellation/expiry/queue recovery | Actual private cleanup confirmation with BE2 |
| ML adapter/jobs | Agent C/coordinator | passed | HTTP adapter tests and concurrent start/question/timeout/partial/error checks pass; never fallback | Align with actual BE2 service when available |
| Integrated checks | Coordinator | externally blocked | BE1 standalone actual HTTP PDF/DOCX/scan and unavailable-model journeys pass; no real BE2/frontend exists in this clone | Real agreement/FIR/notice/language/UI journey |
| Frontend handoff/startup notes | Coordinator | passed | README, env template, lock, examples/OpenAPI, independent demo and source-only package command implemented/tested | Share source bundle or commit/push only when requested |

## Independent completion evidence

- Full suite: `python -m pytest -q --basetemp=work/verification/full-002 -o cache_dir=work/verification/cache-root` → **114 passed, 1 skipped, 1 xfailed**, one upstream deprecation warning. Skip: actual Windows symlink creation lacks privilege; equivalent detection regression passes. Expected failure: Punjabi synthetic agreement-word nasalization error; real payment/time anchors work, all OCR requires review.
- App-local OCR: `python apps/api/scripts/setup_ocr.py` and `--probe` exercised. Runtime Tesseract 5.5.3.20260724, recognized eng/hin/pan. Official upstream assets pinned/hashed; installers extracted as archives, no install actions/registry/PATH changes. Binaries under ignored tools/ocr. Cached repeat setup passes without network.
- Native parser tests verify an actual separate process, finite document deadline, Windows job memory limits, OCR descendant kill, cancellation, invalid protocol and recovery. Private data stays in pipes, never process argv/logs.
- Standalone demo launches only owned loopback Uvicorn children with temporary synthetic files and gracefully stops them; it needs no other role documents or running services. It explicitly labels simulation and reports model_tested:false. Actual local English scan HTTP path passes.
- Interrupted upload/model start/deletion and concurrent queue/session limits are tested; cancellation no longer leaves queued reservations or untracked local source files.
- Config supports fractional timeouts/TTL. Framework errors remain sanitized. Public contracts include EXTRACTION_TIMEOUT and truthful isolation metadata.
- Source-only handoff builder is tested for privacy exclusions, hashes and overwrite refusal. No frontend, private ML service, duplicate classifier, translation implementation or vector index was added.
- Punjabi's quality limitation was investigated with 18 actual resolution/segmentation runs. No reliable improvement was found, so resource defaults and original assertions were retained; OCR_VALIDATION.md records the evidence.

Only external dependencies remain: actual BE2 schema/service/model integration, real AI quality and downstream cleanup, plus FE1/FE2 application integration. No TinyFish, external OCR/translation/AI inference or LLM/classifier download/training was performed. Git publication was subsequently requested by the user; downloaded binaries and private runtime files remain excluded.
