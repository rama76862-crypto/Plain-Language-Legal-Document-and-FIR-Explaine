# Public Contract v1: current frontend handoff

The frontend and both backends are implemented in this repository. The original four role files describe the initial division of work; current code, this contract and verification reports take precedence over historical status notes. `openapi.json` is exported from the application. `v1-examples.json` and `v1-example.json` are explicitly synthetic development examples, never real legal/model findings.

All routes use `/api/v1`. After upload, document routes require `X-Session-Token`; missing/wrong tokens and unknown documents share 404. Tokens must not appear in URLs, logs or browser persistent storage. Runtime source files have no public static mount.

## Core journey

1. GET `/capabilities` for effective limits, temporary-storage consent and processing-mode disclosure. POST multipart `/documents` with the file, language/type and `processing_consent=true`. Hosted mode also requires `external_ai_consent=true` **before storage**. GET metadata until extraction is ready; GET `/documents/{id}/extraction` and inspect original `/source` through its authenticated route.
2. PATCH `/documents/{id}/extraction` to confirm/correct text, language and type. Empty corrections confirm the current revision; genuine edits increment once, invalidate older findings and confirm the new revision. Editing during queued/running analysis returns 409.
3. POST `/documents/{id}/analyses` with expected_revision/output_language. Poll GET `/documents/{id}/analyses/{aid}` for real stage/completed/total/failed counts. A terminal `needs_review` can contain partial output; `failed_clauses` identifies every unanalysed clause. Never convert missing clauses to success or hide review warnings.
4. POST `/documents/{id}/questions` using the current analysis/revision and request ID. Source quotes are exact reviewed text. An insufficient-evidence answer is a valid limitation, not a generated answer to display as supported.
5. GET `/documents/{id}/analyses/{aid}/report?format=json|md|html`. Optional `include_questions=true` includes completed answers. Reports contain source text, findings, warnings, source facts, Action Pack and any selected-source check. Downloaded copies belong to the user and survive server deletion.
6. DELETE `/documents/{id}` immediately hides the session and cancels work. Cleanup status can remain pending; never claim confirmed erasure while downstream cleanup is unresolved. Expiry also cancels/hides data. Ordinary polling does not extend the session. An explicit user request may POST `/documents/{id}/keep-alive` with `X-Session-Token` to extend a still-active session and receive its current metadata/deadline. Expired sessions return 404 and cannot be revived.

Errors use `{error:{code,message,retryable},request_id}` with no rejected document text in validation messages. Effective byte/page/text/time limits come from capabilities. Parser timeouts are distinct from model timeouts. OCR availability means engine/assets are present; it does not establish extraction accuracy.

## Clauseora-inspired additive features

The target is this original app; the separate Clauseora repository is unchanged.

- GET `/documents/{id}/analyses/{aid}/action-pack`: requires a ready result from the current source revision. Returns source obligation/checklist entries, detected role words, stated deadline excerpts, clause/source locators, up to five clarification questions and limitations. Checking a box means reviewed, not legally complied. The current frontend keeps checkbox state in component memory only.
- POST `/documents/{id}/compare`: body `{document_b_id,expected_revision_a,expected_revision_b}`. Authorize A with `X-Session-Token` and B with `X-Compare-Session-Token`. Both separate documents must be reviewed and current. Returns unchanged count plus added/removed/modified records with exact before/after quotes, clause IDs and source locators. Maximum 150 passages per document. This is bounded text alignment, not legal/semantic certification; case/whitespace-only edits are ignored. B is deleted when its comparison workspace closes; interrupted requests can persist until expiry.
- POST `/documents/{id}/analyses/{aid}/verify-source`: body `{external_ai_consent:true}` separately authorizes sending up to six bounded claims/excerpts to Cloudflare. Responses: `cross_checked`, `needs_review` with clause-linked disagreements, or `unavailable`. `independent_review` is always false. Unknown/duplicate/missing model IDs invalidate the response. Successful responses are cached per analysis; a new revision or deletion prevents reuse. No provider result establishes legality, enforceability, guilt or fluent human review.

## Local versus hosted

`Start.cmd` forces primary inference to local mode. It uses Qwen, the local classifier, E5/BM25 and installed IndicTrans2 assets. An optional external source check is possible only when configured and separately consented.

The hosted Docker path uses Groq and source rules/BM25, not the local trained classifier or downloaded model assets. Capabilities and the persistent UI disclosure identify hosted processing; upload requires additional consent. Direct identifier masking is limited, not full anonymization. Provider policies apply. Hosting details and quotas: `deployment/README.md`.

BE2 remains private loopback. Public session tokens are never forwarded to it; its optional service token uses `X-ML-Service-Token`. BE1 supplies the analysis ID and validates private responses. Health/readiness is factual, and all languages remain experimental pending fluent/semantic review. Classifier metrics and synthetic coverage are not LLM/legal accuracy.

`ML_MODE=fixture` remains an explicit backend-development simulator, labelled as such. The production frontend and hosted supervisor do not select it or silently fall back to it.
