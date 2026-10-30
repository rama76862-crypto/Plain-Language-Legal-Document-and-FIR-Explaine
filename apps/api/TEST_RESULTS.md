# Verification record — 30 October 2026

Environment: Windows PowerShell, isolated CPython 3.12.10. Python dependency versions: requirements.lock.txt. App-local Tesseract: 5.5.3.20260724; installed eng/hin/pan assets and source/hash receipt in ignored tools/ocr/manifest.json. No global OCR installation or PATH change.

| Check | Actual outcome | What it proves |
|---|---|---|
| `python -m pytest -q --basetemp=work/verification/full-002 -o cache_dir=work/verification/cache-root` | **114 passed, 1 skipped, 1 xfailed** | Public API, actual native/OCR parsers, bounded lifecycle and real HTTP standalone checks; ML only through explicit doubles |
| `python -m pip check` | No broken requirements | Installed dependency compatibility |
| Native parser subprocess tests | 7 passed within full suite | Real process separation, timeout, cancellation, descendant termination, memory limit/recovery, private protocol/errors |
| Lifecycle tests | 22 passed, 1 skip within full suite | Concurrent admission, actual Windows locked-file recovery, canceled upload/job/delete handling, restart/expiry/queue behavior |
| Real English image-only PDF | Passed | Actual local OCR, original page references and review-required clauses |
| Real Hindi image-only PDF | Passed | Synthetic अनुबंध/भुगतान anchors and review state; not general legal accuracy |
| Real Punjabi image-only PDF | Expected quality failure | Gurmukhi payment/time anchors recognized; agreement word has extra nasalization mark |
| Real mixed native/scanned PDF | Passed | Real page/source references and completed OCR page counts |
| Selectable header over scanned body | Passed | Small native header no longer suppresses OCR of the scanned body |
| Standalone actual Uvicorn demo | Passed within full suite | Native PDF/DOCX, real English scan, review/source, labelled fixture result/question, deletion and graceful shutdown |
| Controlled unavailable real ML | Passed | Explicit MODEL_UNAVAILABLE/MODEL_TIMEOUT; no fixture fallback, health remains usable |
| Source-only package test | Passed | Runtime, `.env`, binary assets and other owners' files excluded; SHA256 manifest; no overwrite |

The sole skip requires Windows symlink-creation privileges; mocked ancestor-link detection also passes. The sole expected failure deliberately retains the Punjabi word-level OCR quality limitation. It is not counted as a passing language-accuracy test. All OCR clauses require human review. Indic fixtures use an existing OS-licensed Nirmala font without redistributing it.

A targeted 18-run Punjabi resolution/segmentation experiment did not resolve the word error; payment/time anchors and numeric tokens stayed intact. Defaults and original assertions were preserved. See OCR_VALIDATION.md for scope and observations.

One upstream Starlette TestClient/httpx deprecation warning remains; no unexpected failure. Test basetemp/cache live under ignored work/verification because an older system pytest directory has incompatible permissions in this execution account.

Production extraction now uses killable subprocesses, not native-parser threads. Windows Job Objects bound the parser/OCR tree's memory and kill descendants; the tested hard timeout returns EXTRACTION_TIMEOUT (504). Other OS resource-limit paths are implemented but not verified here. Process isolation is not a full filesystem/network sandbox.

Fixtures are synthetic. Development mode reports needs_review with zero actually model-analysed clauses. Complete/partial mocked HTTP results are contract tests, not legal/translation quality evidence. Actual BE2 agreement/FIR/notice analysis, multilingual generation/retrieval and downstream private erasure remain unverified external dependencies. Frontend integration also requires the frontend implementation.
