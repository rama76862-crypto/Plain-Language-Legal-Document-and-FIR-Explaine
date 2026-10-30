# Frontend integration

The React/Vite frontend talks only to the public BE1 /api/v1 routes through the typed client. BE1 calls BE2; BE2 runs local retrieval, classification, translation and Qwen generation. No browser call goes directly to private model services. No frontend fixture mode or embedded mock result datasets remain.

## Commands

~~~powershell
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend run i18n:check
node --experimental-strip-types frontend/scripts/check-health.mjs
~~~

The production build is served at http://127.0.0.1:8000/ by the configured local launcher. For development, npm --prefix frontend run dev uses the Vite /api proxy to port 8000. Copy .env.example as needed; these values are public build configuration, never secrets.

Features: consent, upload, source/output language and type selection, actual extraction/analysis polling, correction/review, revision handling, cancellation/retry, source view, clause explanations, attention flags, deadlines, local grounded questions with in-memory history, backend JSON/MD/HTML review reports, print layout, legal-aid links, deletion and server-expiry display.

The backend owns result content and review status. Missing models/readiness produce real errors. New revisions/languages invalidate stale results. Session identifiers and text stay in React memory; refresh requires starting again. Exported copies remain on the user device.

See ../FULL-FEATURE-VERIFICATION.md for observed acceptance checks and limits. Some technical copy is still English. Human language/legal review, actual judge documents, production hosting and broader device/load verification remain open.
