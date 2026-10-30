> Current integration update (30 October 2026): read FULL-FEATURE-VERIFICATION.md and the application READMEs for implemented behavior and actual checks. This document contains historical development specifications. All frontend fixture/mock modes and canned results are removed; older instructions allowing frontend fixtures are superseded. Current upload defaults are 25 MB / 50 PDF pages. Reports use authenticated backend JSON/MD/HTML endpoints. Language/legal review gates remain open.

# Frontend audit against the four role handoffs

Date: 30 October 2026. Incoming frontend revision: 38c41e7. This is a source/contract audit plus actual build and targeted regression checks. It is not a completed browser-to-real-model acceptance run.

## Verdict

The core FE1 and FE2 screens and API operations are implemented, but the frontend is not fully complete against its role handoffs. The incoming version defaulted to fixtures and had a build failure and real-backend health mismatch. These immediate blockers were corrected during this integration. Broader language, export, lifecycle and real-browser verification remain open below.

## Checks actually run on this integration

- npm ci --no-audit --no-fund: completed.
- npm run build: passed after removing a nonexistent fixture re-export; TypeScript and production Vite build passed. Vite reports a large main bundle, approximately 1.66 MB before gzip.
- npm run i18n:check: passed, 190 dictionary keys per language. This checks key parity, not actual screen translation or linguistic quality.
- node --experimental-strip-types scripts/check-health.mjs: passed. This small regression check uses Node's TypeScript stripping (tested with Node 24).
- ML environment: python -m pytest apps/api/tests/test_ml_client.py -q: 37 passed, including the new Backend 2 readiness-field compatibility check. These are adapter tests with controlled transports, not proof of a running BE1/model chain.
- python -m pytest apps/ml/tests -q: 86 passed with one existing Starlette/httpx deprecation warning.
- No full browser journey or cross-service real-model smoke was completed in this audit. Historical Backend 2 generation evidence remains documented separately in apps/ml/evaluation/REAL_LOCAL_REVIEW.md.

## Feature checklist

| Handoff feature | Implementation evidence | Status / limit |
|---|---|---|
| PDF/DOCX upload and language/type selection | frontend/src/features/upload | Present; real browser upload still needs acceptance run |
| Extraction polling and original-file download | ExtractionScreen and lib/api.ts | Present; same-origin API paths and token header wired |
| Extraction correction and explicit confirmation | features/review | Present; detected language/type now applied from backend extraction |
| Original PDF/DOCX evidence navigation | features/source | Present; PyMuPDF top-left highlight convention corrected; rotated/cropped PDF geometry not visually verified |
| Clause-by-clause explanation | features/results/ClauseExplanationList.tsx | Present; real model outputs may still need semantic review |
| Potential attention flags/model-score context | AttentionPanel and EvidenceCard | Present; no document-wide legal-safety percentage required |
| FIR/notice result kinds | ResultContext and result panels | Present; context now uses returned document_type rather than always agreement |
| Dates/unresolved relative periods | DeadlinePanel | Present; backend remains authoritative; no legal deadline calculation |
| Independent input/output languages | Upload controls and ResultContext | Present; language paths remain experimental/unreviewed, not 9/9 validated |
| Real job progress/partial-result warnings | ResultsWorkspace and OverviewSummaryPanel | Present; failed processed-clause count now displayed when available |
| Citations/original evidence | EvidenceCard, EvidenceButton, ReferenceCard | Present; reference applicability is not independently established by rendering a card |
| Grounded follow-up questions/retry ID | QuestionPanel | Present; needs real backend/browser acceptance and history persistence work |
| Local Markdown export | ResultExport | Present; now includes per-item review_status; Q&A export option remains incomplete |
| Official legal-aid links | LegalAidDirectoryCard and result footer | Present; links/contacts are not an entitlement guarantee |
| Delete session | session.tsx and DeleteSessionDialog | Present; UI now distinguishes local clearing from confirmed server deletion |
| Temporary retention UI | InactivityModal and session.tsx | Partial: local activity timer is not synchronized with server expiry |
| Responsive/mobile layouts | source/results tabs and responsive classes | Implemented in code; not visually verified across devices in this audit |
| Offline assets | bundled font packages and local PDF worker | Present in production output; full disconnected-browser check pending |

## Immediate fixes made

1. Changed frontend/.env to VITE_USE_FIXTURES=false. Fixture mode remains explicit for development; no runtime fallback to fixtures was added.
2. Added frontend/src/lib/health.ts to adapt BE1's nested extraction/ml health response; missing readiness or OCR evidence stays unavailable.
3. Made the landing-page health callback stable to prevent repeated callback-driven health fetches; uploads wait for extraction readiness.
4. Removed hard-coded tested-language labels and the 9/9-tested assertion. Language controls now disclose review/experimental status.
5. Updated the BE1 adapter to accept BE2 classifier_ready/generator_ready, as well as its former loaded field names, without inventing reviewed-language evidence.
6. Applied backend-detected language/type at extraction review, refreshed source clauses when revisions change, and invalidated old analysis requests on revision changes.
7. Corrected top-left PDF coordinates for BE1/PyMuPDF output; extended frontend types for extraction detector and optional progress stage/failed_clauses.
8. Removed fixtureGeneralQuestions re-export, which referenced a nonexistent export and broke the production build.
9. Made failed server deletion visible instead of always showing a successful-deletion toast. Clarified the inactivity modal's local-timer/temporary-retention wording.
10. Included review_status in Markdown exports and replaced the reference card's blanket 'Verified reference' label with an applicability-review notice.

## Remaining work before claiming complete

1. Q&A export: includeQuestions is toggled but never used to append question history. QuestionPanel keeps history in its own mounted component, so changing tabs discards it. Move history into session/result-level memory and implement the export option, or explicitly remove/defer the option.
2. Full UI localization: many feature labels, errors and helper strings are hard-coded English despite dictionary parity. Move them into en/hi/pa dictionaries and obtain fluent review. Generated document translations remain a separate Backend 2 quality issue.
3. Review failure handling: ReviewWorkspace explicitly presents 404/409 but does not visibly surface every other PATCH/network error. Add generic error/retry feedback while preserving unsaved edits.
4. Inactivity/expiry: the client resets its timer on local interaction while server expiry follows authenticated requests. Consume the real expires_at value/heartbeat policy or clearly retain a local-only timer; avoid asserting that both clocks are identical.
5. Run the actual browser path: PDF and DOCX -> extraction review -> real analysis -> evidence navigation -> grounded/unsupported question -> export -> deletion. Include an unavailable model, a partial result, source revision changes and output-language switching.
6. Browser performance/accessibility: measure heavy 3D/canvas effects, keyboard behavior, mobile source/results switching and actual rotated/cropped PDF highlights. A successful build does not prove these.
7. Privacy wording: review remaining locale/UI copy that promises deletion on refresh or permanent erasure; losing browser credentials is not proof of immediate server cleanup. Avoid blanket retention/security guarantees.

## Current folder organization

- frontend/: the combined FE1 + FE2 application. Kept in place to preserve working imports/build setup.
- apps/api/: Backend 1 public API, extraction, sessions and ML adapter.
- apps/ml/: Backend 2 training, private service and local inference.
- contracts/: public API schema/examples.
- frontend-spec/: teammates' frontend planning/specification materials.

No cosmetic directory move is necessary before evaluation. Do not call the application fully integrated until the remaining real-service browser acceptance run is recorded.
