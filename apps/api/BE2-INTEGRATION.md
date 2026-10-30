# BE2 integration handoff

No apps/ml exists in this clone; localhost:8001 probe is unavailable. Real adapter is implemented/tested against HTTPX MockTransport and is default; actual BE2 alignment remains pending.

- BE1 supplies `analysis_id` and POSTs the handoff's reviewed-clause payload to `/internal/analyse`; require 202 preserving ID and queued/running state.
- GET `/internal/jobs/{analysis_id}` must contain analysis_id, document_revision, output_language, status, actual progress `{completed_clauses,total_clauses}`, result or null and warnings. Optional stage/failed_clauses are preserved. Identity/type/language/coverage/evidence/reference checks reject bad output. Processing failed clauses can count as completed work; coverage.analysed counts clauses with usable analysis. Terminal partial results enumerate every failed clause. Complete cannot contain failed/needs_review items.
- Private QuestionRequest currently forwards document_id, document_revision, analysis_id, question, output_language, client_request_id, document_type, input_language and reviewed clauses. BE2 should confirm this exact schema before integration. BE1 derives identity server-side. Returned reference_ids must resolve to existing current-analysis references. No unannounced answer.references extension.
- Health currently consumes explicit classifier_loaded/generator_loaded booleans and tested_language_matrix; absent evidence stays unavailable. Public health uses classifier_ready/generator_ready/language_paths. Confirm actual BE2 names to adjust the adapter, not the browser.
- Optional credential header proposal: `X-ML-Service-Token`, pending confirmation. Public session tokens never go to BE2.
- DELETE every analysis ID removes translated copies, document indexes and question caches as well as job data. BE2 must tombstone late results and expire artifacts independently. 404 delete is treated as already absent. BE1 bounded retry status is observable in health.
- Preserve model/rule/classifier provenance, warnings and extra version metadata. Source evidence must quote original reviewed_text even when English pivot translation was used.
- BE1 has bounded admission/polling, not a second GPU queue. Configure the true BE2 queue limits and timeout with the team. No browser access to private service/model ports.
- Test one real PDF/review/result/question/delete first, then agreement/FIR/notice and all actually supported language pairs. Use `python -m apps.api.scripts.smoke --mode real`; semantic quality remains BE2 evaluation responsibility.
