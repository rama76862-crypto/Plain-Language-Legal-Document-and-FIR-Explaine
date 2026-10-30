# NyayaLens — urgent pull, integration and evaluation prompt

User addition: the user has now explicitly authorized pulling teammate changes and pushing their preserved work afterward. Review the staged source/docs, exclude private/runtime assets, run relevant checks, commit the integration and push normally to the intended remote branch. Never force-push. Audit the frontend against both role handoffs and record implemented, partial and unverified features before calling it complete. This explicit addition supersedes the earlier no-commit/no-push-unless-instructed wording below for this authorized integration.

Read and execute this prompt in the existing repository. The evaluation is imminent: prioritize one stable, real end-to-end demonstration, then minimal file organization. Do not restart the project or spend the remaining time on architecture changes.

## 1. Read the current state and preserve Backend 2

Repository on this laptop: N:\Github-Repo\ct\Plain-Language-Legal-Document-and-FIR-Explaine. Remote at prompt creation: origin https://github.com/rama76862-crypto/Plain-Language-Legal-Document-and-FIR-Explaine.git; current branch main. Verify these before acting.

Read applicable AGENTS.md instructions, the four role handoffs and their Integration addendum. Inspect actual code and Git state rather than assuming the handoffs describe finished implementation. Backend 1 and both frontend contributions have reportedly been pushed and must be fetched/integrated.

IMPORTANT: at prompt creation, local apps/ was UNTRACKED, the four role handoffs were modified, and start prompts were untracked. Preserve all this local work before pulling. Preserve ignored model weights, dataset cache, virtual environment, trained classifier and runtime binaries in place. Do not delete or redownload functioning assets.

Only the coordinator performs Git operations. Inspect ignored paths and preserve local code/documents through a recoverable backup or a named stash including untracked source files. Verify the recovery point exists before updating. Do not include ignored multi-gigabyte assets unnecessarily. Fetch origin and inspect incoming changes and relevant branches. Integrate the teammates' actual pushed work; prefer a fast-forward when possible. Restore local changes carefully; retain the backup/stash until the combined application works. Resolve ordinary conflicts while preserving both contributions. Do not reset hard, run destructive clean, force-push, discard local ML code, or overwrite a teammate's implementation wholesale. Do not push or make commits without a separate instruction.

If incoming work is on separate branches, inspect the branch contents and integrate the relevant contributions without guessing that all code is on main. If an unresolvable external blocker exists, state it immediately and continue independent startup checks. Do not repeatedly ask for routine reversible choices.

User restriction: never use/install/call TinyFish or its services. No external AI/OCR/translation inference. Local services and downloaded local assets are the intended architecture.

## 2. Use agents, but keep integration controlled

Use a coordinator plus up to three agents when available:

- Agent A: frontend integration only. Inspect the two frontend contributions, choose the intended app entrypoint, integrate FE1 and FE2 components, fix API client/proxy/state wiring, remove accidental runtime mock selection. Own the frontend files assigned by the coordinator.
- Agent B: Backend 1 integration only. Own public API routes, extraction/review flow, sessions and the real Backend 2 HTTP adapter. Publish actual endpoint/schema differences immediately.
- Agent C: Backend 2 compatibility and demo verification. Preserve the trained classifier/model, inspect private contracts, fix only necessary integration regressions and verify existing warning/coverage/reference behavior. Exclusive GPU-heavy testing ownership; avoid parallel inference test storms.
- Coordinator: Git operations, layout map, environment/port coordination, startup, progress and the final cross-service smoke/browser check. One owner per shared file. Agents do not independently move folders or change public contracts.

If agent tools are unavailable, do the same work sequentially. Do not claim imaginary agents. Reuse existing checks and dependencies. No broad refactor, new framework, extra dataset or large-model fine-tuning.

## 3. Connect the real system before sorting folders

First identify the actual frontend directory/package manager, BE1 entrypoint/environment, BE2 environment, model paths, routes and ports. Keep working service boundaries. Existing BE2 setup is documented in apps/ml/README.md; use its tested commands and local assets.

Intended runtime topology on the GPU laptop:

    Browser -> frontend /api proxy -> BE1 public API -> BE2 private ML -> local LLM
                usually 5173          usually 8000       127.0.0.1:8001  127.0.0.1:8080

Ports are defaults: inspect actual configurations and fix collisions deliberately. Browser code must not call the private ML or model ports. Another laptop's localhost is not this machine. Prefer running all services on this laptop for evaluation and using one frontend origin. Keep ML/model loopback-only. Do not change firewall settings silently.

Start the local model server again; it was stopped after verification. Check real readiness, not merely a live process. Start BE2 private service, BE1 and the frontend using their own compatible environments. The smoke command is a test, NOT a replacement for a persistent BE2 service. Do not let frontend or BE1 virtual environments overwrite the working ML environment. Keep background helpers hidden when using Start-Process, retain logs/process IDs, and avoid leaving duplicate servers occupying ports.

Connect upload -> extraction -> explicit review confirmation -> analysis creation -> real job polling -> result/evidence navigation -> grounded question -> deletion. Preserve Contract v1 unless all owners coordinate a necessary compatibility fix. BE1 supplies analysis_id/document_id/revision to the private API; it must not forward public session tokens to the model. Preserve optional progress.stage and failed_clauses and the original output-language/revision identifiers.

Check plural public /analyses routes versus singular private /internal/analyse; do not accidentally proxy raw private routes into the frontend. Source download needs authentication and Blob handling. DOCX evidence uses paragraphs, not invented pages. A language change must not display a late response from another language/revision.

## 4. Keep known limitations visible

Backend 2's recorded baseline is macro-F1 0.736671 and micro-F1 approximately 0.734584 on English UNFAIR-ToS. It is not Indian legal correctness or application accuracy. There are 33 normalized train/test overlaps. Forty-nine missed label assignments were inferred from per-label metrics; 22 saved examples are capped samples, not the total.

Recorded multi-clause service evidence is 11/12 successfully analysed with one review fallback. Exact quotations did not prevent unsupported interpretations. Generated explanations/answers remain needs_review; do not relabel them verified simply to improve the demo.

All nine language cells passed schema in a later run, but only four of six Indic-target cells passed script checks and protected markers changed in six cells. Fluent review was not performed. Prefer the verified English execution path for the primary live demo; language functionality must show its actual experimental/review status. Do not advertise fully validated Punjabi/Hindi or bypass checks. Unknown/changed amounts, anchors, consent conditions or allegations must trigger review or suppression, not a confident invented explanation.

Six official-reference records were prepared, but some Consumer Affairs excerpts and reuse terms still need direct rechecking. Do not expose unverified records as verified legal authority. Missing/unverified references should remain explicit. Do not invent a citation to fill a card. Use the existing source review record in apps/ml/evaluation/REAL_LOCAL_REVIEW.md.

## 5. Sort frontend/backend files minimally and safely

AFTER the app boots and the primary journey works, map current directories to intended ownership:

    apps/web/        one frontend app containing FE1 + FE2 features
    apps/api/        Backend 1 public API/extraction/sessions
    apps/ml/         Backend 2 classifier/local inference/private service
    contracts/       agreed payload fixtures and schema notes
    docs/            optional future location for supporting documentation

Do not move files merely to make the tree look neat before evaluation. If incoming code uses frontend/ or backend/ and already works, keep those paths temporarily and document the mapping. Consolidate duplicate frontend entrypoints only if necessary to connect FE1 and FE2. Avoid moving existing apps/ml: its runtime/artifact paths already work.

For any necessary move, resolve source/target paths, verify both stay within this repository, preserve originals until the change is verified, and update imports, package/workspace paths, commands, proxy targets and asset paths together. Never move/delete .git, models, virtual environments or datasets as part of cosmetic cleanup. Do not move the four handoffs or start prompts until teammates agree: existing instructions refer to their filenames.

Create a short root RUN-EVALUATION.md with the ACTUAL folder map, tested startup order/commands, URLs, required environment names, known limitations and demo steps. Provide .env.example files without real tokens. Do not overwrite a teammate's existing launcher/README without merging useful content.

## 6. Progress and first-demo priorities

Maintain INTEGRATION-PROGRESS.md with six evidence-based milestones:

1. Local work preserved and remote contributions integrated.
2. All four services ready on intended ports.
3. Real upload/extraction/review reaches the private ML service.
4. Results, progress, evidence and questions work in the frontend.
5. Deletion/failure paths and targeted regression checks pass.
6. Evaluation runbook and demo rehearsal complete.

Show [###---] 3/6 passed only when checks pass. Keep blockers explicit. Expose actual clause progress; processed clauses may include failures, so preserve review state and successful coverage. Give concise updates at least once per minute during sustained work. Do not fill progress bars using timers.

First checkpoint: boot services and get one short English document through the REAL path as quickly as possible. Then add one notice with a missing receipt date and one fictional/redacted FIR if time permits. Do not delay the primary demo for all-language reruns or cosmetic reorganization.

## 7. Validate and leave the demo running

Run targeted frontend typecheck/build, changed-backend tests and one real cross-service smoke. Reuse the existing 86-test ML baseline; rerun broader tests only when changed paths or failures justify it. A build passing is not proof of browser integration.

Verify in the browser if available:
- No fixture/demo-mode result silently replaces a failed real API call.
- File upload, review confirmation and analysis execute on actual data.
- Progress reaches a truthful terminal state; partial/review warnings remain visible.
- Evidence opens the correct original clause/page/paragraph.
- One grounded question and one unsupported question behave correctly.
- Delete clears UI and public/private document work without resurrection.
- Model unavailable/busy errors are readable; a failed request does not freeze the app.

Use only synthetic, redacted or consented demo documents. A recording may be a labelled backup, never presented as live execution. Do not disable safeguards or fabricate successful multilingual/legal results for evaluation.

Leave the intended application/model services running for judging. Report the working URL, exact launch commands, actual checks, remaining blockers and any deferred folder cleanup. Clearly distinguish real end-to-end success from mocked tests or partial features. Continue until the demonstrable integration works or a concrete external blocker is identified; do not stop at another plan.
