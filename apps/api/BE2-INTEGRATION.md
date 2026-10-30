# BE1 and BE2 private integration

The services run as separate local processes. BE1 is the only browser-facing API
and binds to `127.0.0.1:8000`; BE2 binds to `127.0.0.1:8001`; llama.cpp binds to
`127.0.0.1:8080`. The frontend proxies `/api` to BE1. Never expose either
private port through the frontend.

## Request and response boundaries

- BE1 creates `analysis_id` and sends only reviewed clauses, source references,
  document/revision identity, type, and languages to `POST /internal/analyse`.
  BE2 returns 202 with the same `analysis_id` and queued/running status.
- `GET /internal/jobs/{analysis_id}` reports status and real completed/total
  clause counts. `progress.failed_clauses` is a numeric count. A terminal
  partial `result.failed_clauses` list identifies every failed clause and its
  reason; BE1 reconciles the list against the count and coverage. This is an
  additive Contract v1 result field. Failed clauses are not silently presented
  as analysed coverage.
- BE1 sends exactly six private question fields: `document_id`, `analysis_id`,
  `document_revision`, `question`, `output_language`, and `client_request_id`.
  Reviewed text and result context are retrieved by BE2 from the stored current
  analysis. The private question limit is 4,000 characters, matching public
  Contract v1. Returned evidence must match the original reviewed text and
  reference IDs must resolve to current official records.
- BE2 health uses `classifier_ready`, `generator_ready`, and source-language
  `tested_languages` flags. These flags do not establish pairwise translation
  or generation capability. BE1 preserves them but reports a language path
  only when BE2 supplies explicit input/output test pairs.
- References may have a null/omitted `version` only when the source genuinely
  has no version date. Title, excerpt, section where applicable, jurisdiction,
  and an official HTTPS URL remain required and are validated.
- BE1 session tokens are never sent to BE2. The optional `X-ML-Service-Token`
  remains unset unless both services are configured to use it.

## Lifecycle and limits

The private service owns a one-generation-worker queue with two pending slots,
30-minute result expiry, job tombstones, and source/index/translation cleanup.
Deletion is terminal: late work cannot repopulate a deleted result. BE1 rejects
stale revisions before question/analysis requests and retries bounded private
cleanup. Both services expose health on loopback only.

## Local operation

Install BE1's pinned dependencies into `.venv-api` and restore the ignored BE2
model, classifier, and llama.cpp assets as described in `apps/ml/README.md`.
Start llama.cpp, then BE2, then BE1 with `ML_MODE=real` and
`ML_BASE_URL=http://127.0.0.1:8001`. The smoke command below performs a real
synthetic upload, native extraction, explicit review, asynchronous analysis,
question, and deletion through BE1. Fixture mode is not used for this check.

```powershell
.\.venv-api\Scripts\python.exe -m apps.api.scripts.smoke --mode real --kind pdf
```

Analysis items stay `needs_review` until semantic/legal entailment is reviewed;
matching a citation section or attaching an exact quote does not prove that
every interpretation is supported. No language path is described as fluent
without fluent review. See `INTEGRATION-PROGRESS.md` and
`RUN-EVALUATION.md` for measured results, command logs, and open checks.
