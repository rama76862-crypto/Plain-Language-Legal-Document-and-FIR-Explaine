# Connect Backend 1 and Backend 2 — urgent implementation prompt

Execute this task now in the existing NyayaLens repository. Read applicable AGENTS.md restrictions first. Use local services and official documentation only; do not discover or enable additional external research/automation plugins. No external AI, translation or OCR inference.

## Objective

Prove a REAL Backend 1 -> Backend 2 -> local model journey before evaluation. Preserve all existing code, working model assets, classifier artifacts, virtual environments and teammates' edits. Do not stop after another plan or redesign the application.

Read both backend role handoffs in full, including their Integration addendum, apps/api/README.md, apps/ml/README.md and the actual schemas/routes. Use the current clone directory; the original laptop path is N:\Github-Repo\ct\Plain-Language-Legal-Document-and-FIR-Explaine.

## Agents and ownership

If available, use two agents: A owns BE1 environment/public adapter and B owns BE2/private model readiness. Coordinator owns startup, compatibility checks, progress and cross-service testing. One owner per file; GPU work is serial. If agents are unavailable, run the same steps sequentially. Do not claim nonexistent agents.

## Step 1 — inspect and boot existing services

- Inspect Git status and preserve local changes. Reuse the current pulled/merged code. Do not reset, clean or overwrite working source/runtime assets.
- Verify the actual BE1 and BE2 Python environments. BE1 dependency installation on this laptop previously did not finish; check it and install only what remains necessary in its own environment. Do not modify the working ML environment.
- Locate existing ignored model/classifier assets. Do not redownload them if present and verified.
- Intended ports: local model 127.0.0.1:8080; private BE2 127.0.0.1:8001; public BE1 127.0.0.1:8000. Check collisions without killing unrelated processes.
- Start the persistent model server, persistent BE2 service and BE1 in that order. A smoke script does not replace a persistent service. Keep private ports loopback-only. Background Windows processes must be hidden and have retained process IDs/log paths.
- Configure BE1 with ML_MODE=real and ML_BASE_URL=http://127.0.0.1:8001. Never silently fall back to fixture mode.

## Step 2 — verify health and contracts

- Query BE2 /internal/health, then BE1 /api/v1/health. BE2 reports classifier_ready and generator_ready; the BE1 adapter already has compatibility handling for these and its earlier loaded names. Verify the actual response, not just code existence.
- Missing readiness evidence is unavailable/unknown. Reviewed-language claims must not be invented.
- BE1 supplies document_id, analysis_id and document_revision with reviewed clauses. POST /internal/analyse returns 202; BE1 polls GET /internal/jobs/{analysis_id}.
- Preserve output language/revision, original evidence, needs_review, warnings, coverage and actual progress including optional failed_clauses/stage. Processed clauses do not all imply successful analysis.
- Forward questions using authenticated document/revision state plus client_request_id. Do not forward public session tokens to the model. Follow Contract v1 for reference resolution and error envelopes.
- Make minimal compatible fixes with targeted tests. Do not remove schema/evidence validation to make a request pass.

## Step 3 — run the real public-API journey

Create a short, explicitly synthetic English PDF or DOCX. Send it through actual BE1 HTTP endpoints:

upload -> native extraction -> explicit review confirmation -> analysis creation -> real progress polling -> result/evidence checks -> grounded question -> unsupported question -> deletion.

Use the existing BE1 smoke command when suitable, then inspect its real results. Ensure analysis invokes the trained classifier and local model. An honest needs_review response is an acceptable integration outcome, not verified legal correctness. Check actual source membership, IDs, revision and deletion of related private jobs.

If extraction/OCR setup is blocked, first prove native PDF/DOCX. Record scans as unavailable rather than inventing text. Do not use personal or unconsented documents for testing.

## Step 4 — recovery and frontend connection

- Test model unavailable/busy, finite timeout, partial result and deletion during processing. Health must remain responsive and a later job must run.
- Confirm the frontend uses /api/v1 through its BE1 proxy and VITE_USE_FIXTURES=false. It must not call raw private model ports.
- Verify the real nested health response does not crash the frontend. Existing normalization fixes should be preserved.
- If a browser is available, perform one actual English upload/review/result/evidence journey. Otherwise label browser acceptance not run; do not infer it from an API smoke.
- Keep Hindi/Punjabi experimental: fluent review is open and recorded outputs changed important details. Preserve warnings, original evidence and review fallbacks. Do not promote unverified official-source excerpts to verified citations.

## Step 5 — progress, evidence and handoff

Maintain INTEGRATION-PROGRESS.md with five milestones: environments; readiness; real analysis; question/deletion/recovery; frontend handoff. Show [###--] 3/5 only for passed checks, with commands and blockers. Runtime progress comes from actual counts, never timers.

Run targeted adapter/service tests and real cross-service smoke separately. Write BE1-BE2-INTEGRATION.md with exact tested startup commands, configuration, URLs, actual pass/fail evidence and remaining gaps. Update RUN-EVALUATION.md if present; create a concise one if missing.

Leave the intended services running for evaluation. Finish with the working URL, whether a REAL cross-service journey passed, and what remains unverified. Do not claim a running app if only mocked tests passed. Preserve current Git history; commit/push only within the user's existing explicit authorization and never force-push.
