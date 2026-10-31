# Frontend/backend integration verification

31 October 2026. Branch: `feature/clauseora-features-and-hosted-mode`.

The pulled branch already had the API routes and frontend client. This change repairs workflow and lifecycle gaps while preserving the existing UI layout, styling, fonts and animations. The baseline and final production builds both emit `index-EtJUO9dJ.css`; no styling was changed.

## Repairs

- Extraction polling no longer restarts on every render, elapsed-time tick or inline callback change. Terminal responses stay stopped; stale requests cannot update a replacement document. Source/extraction retrieval is aborted when the screen closes.
- Comparison CORS accepts `X-Compare-Session-Token` for the configured frontend origin. Both document authorizations and revision/review checks remain required. Revised uploads are cleaned up after an aborted completion, and comparison state is invalidated when the source revision changes.
- Action Pack, checked obligations, prefilled questions and source-verification state are reset when the completed analysis changes. Late responses from an older analysis are discarded. The actual reviewed document type is passed into the result provider.
- Uploads require extraction readiness. A successful HTML fallback from a misconfigured API URL now produces an explicit API error instead of being treated as valid JSON data. DOCX clauses count as native text in the existing review summary.
- The existing retention-extension button now calls authenticated `POST /api/v1/documents/{id}/keep-alive`. Background metadata reads synchronize the real server deadline without extending it. The frontend rechecks expiry before deleting, so a recently extended server session is not wiped using an old countdown. Expired sessions cannot be revived. OpenAPI and contract documentation include the route.
- Deletion animation elapsed time is bounded at zero because an initial animation-frame timestamp can precede effect initialization. This prevents negative canvas radii without altering the animation design.

## Verification

- API suite: **137 passed, 1 skipped, 1 expected failure**. The existing Starlette/httpx deprecation warning remains.
- Frontend regression suite: **7 passed** using the built-in Node test runner and a development-only React test renderer. Covers polling stability/termination/backoff/stale responses, analysis-bound state, HTML/error responses, retention synchronization and deletion animation timing.
- Final TypeScript/Vite production build passed. English/Hindi/Punjabi dictionary checks passed with **479 keys each**; health-contract checks passed.
- Real local PDF API journey passed **9/9** checks, including grounded and unsupported questions, authenticated source access, public deletion and private job tombstones.
- Real local feature journey passed **8/8** steps: two DOCX files extracted/reviewed, **3/3** analysed clauses, Action Pack, version comparison, JSON/Markdown/HTML reports and session deletion. Optional external verification was deliberately not requested.
- In-app browser: uploaded an authored synthetic DOCX, inspected its three extracted clauses, confirmed review, received **3/3** real analysis, loaded the Action Pack and obtained a grounded INR 500 answer. Compared a second reviewed DOCX and displayed exact **INR 500 → INR 750**, with one modified and two unchanged passages. Downloaded the backend HTML report and verified its Action Pack, amount and included question. Deleted the synthetic session and returned to upload.
- Browser screenshots and smoke output are under ignored `work/verification/`; no session tokens, uploads, model assets or provider keys are committed.

The local application is available at `http://127.0.0.1:8000/` after the normal launcher starts. Development Vite uses the existing `/api` proxy. Deploy the frontend build and backend together when using the new retention route.

These checks establish technical integration on synthetic inputs, not legal or translation accuracy. Generated results remain `needs_review`. Hosted inference and optional external source verification were not exercised in this change. Existing npm audit findings in the Vite/React Router dependencies remain; this integration does not upgrade those major versions.
