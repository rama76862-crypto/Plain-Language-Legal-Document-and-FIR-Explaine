> For the new Clauseora port and hosted CPU mode, read CLAUSEORA-VERIFICATION.md. The baseline below predates that feature port and does not certify its public deployment or legal accuracy.

# Integrated feature verification — 30 October 2026

The real frontend, public API (BE1), private ML service (BE2), and local Qwen model are connected. Frontend fixture datasets, fixture branches, fixture flags, canned result previews and the sample loader were removed. The frontend rejects explicitly flagged simulated backend responses.

## Verified work

- Production frontend build/typecheck passes. Translation dictionary checks cover 317 keys per language and now reject missing literal keys used in components. Health contract regression passes.
- ML suite: 123 passed. API adapter/extraction checks: 68 passed, 1 expected failure. Earlier full API suite: 127 passed, 1 skipped, 1 expected failure. These counts are different overlapping runs, not additive.
- Real public API journey: 9/9 steps passed, including upload, extraction, explicit review, analysis, grounded and unsupported questions, authenticated source access and deletion. Generation remained needs_review.
- Actual browser: uploaded synthetic PDF, extracted 10 source units, corrected penalty from INR 500 to INR 750, submitted revision 2, received 10/10 analysis, three attention cues and five deadline entries. Asked about the penalty and received INR 750 with reviewed-source evidence. Question history survived tab switching. HTML report downloaded from the backend. Citation navigation opened the original PDF. Legal-aid tab rendered.
- Cancellation and retry, and an honest model-unavailable error, were exercised in the browser during integration.
- Final source-anchor protection now rejects changing receipt of a request into submission. Regression passes; changed model prompts require preserving receipt/delivery/service/signature anchors. Earlier browser output exposed this error, so coverage must not be advertised as accuracy.
- A failed clause can retain a source risk cue, but the cue is downgraded to needs_review. The public validator remains strict. Constrained generation limits categories and references to actual candidates.
- PDF grouping preserves tightly wrapped native-text clauses and distinguishes distant or parallel text blocks. OCR remains review-dependent.

## Implemented connections

| Feature | Runtime path |
|---|---|
| PDF/DOCX upload, consent, extraction, language/type confirmation | Frontend -> BE1 |
| Reviewed text, revision invalidation, real progress, cancellation | Frontend -> BE1 -> BE2 |
| Clause explanations and local questions | BE2 -> local Qwen/llama.cpp |
| English working copy for Hindi/Punjabi | Local IndicTrans2 adapters |
| Retrieval | Local multilingual E5 ONNX + BM25 hybrid document index |
| Penalty, renewal and waiver cues | Local classifier candidates + explicit source rules |
| Dates, relative periods and unknown anchors | Source-derived rules; no invented legal due dates |
| Evidence/source view | Exact reviewed-text quotes + original PDF/DOCX navigation |
| Review report | Authenticated backend JSON/Markdown/HTML; optional questions; explicit download |
| Legal aid | Official NALSA, authority directory and Department of Justice links |
| Temporary retention | Consent, session token, expiry, delete propagation; downloaded copies remain |

## Important remaining gates

This is a working prototype, not certified legal accuracy. Five actual judge-supplied documents have not been obtained or assessed. All generated explanations and translated outputs require independent legal/fluent review. Synthetic document/language smoke checks measure technical behavior only.

The new Indian-context cue classifier uses 378 authored synthetic examples, not an expert Indian legal dataset. Its tiny held-out test recorded macro-F1 0.590476 and micro-F1 0.640000; waiver F1 was zero, with explicit waiver wording covered separately by rules. The preserved EU baseline has its own overlap caveat. Neither is an LLM accuracy score. Qwen is pretrained, not newly fine-tuned. IL-TUR access is still gated.

Reference admission remains conservative: unverified statutory excerpts are excluded. No blockchain is implemented or needed by the supplied problem statement. OCR quality, complex/scanned layouts, adversarial documents, broader multilingual meaning and concurrent load still require evaluation. Some technical UI text remains English; dictionary parity is not fluent translation certification.

Free deployment instructions are in deployment/README.md. They describe a GPU laptop with an authenticated gateway/tunnel; no public deployment or always-on free GPU hosting was established. Current model/API services bind loopback.

## Run for evaluation

From repository root in PowerShell, with the existing environments and ignored local model assets:
~~~powershell
npm --prefix frontend run build
.venv-api/Scripts/python.exe -m apps.run_local start
~~~
Open http://127.0.0.1:8000/ . Backend health: /api/v1/health. Private ML is on 8001 and model on 8080; do not expose those ports. If the browser shows No Active Session after a restart, return to upload and submit the document again.

Upload limits currently default to 25 MB and 50 PDF pages. These guard parser/OCR memory and model queue latency; they do not promise acceptable latency at the maximum. Change validated BE1 settings only with resource/load verification. Full offline operation requires all dependencies, fonts, OCR packs and model files already installed; official aid links need internet.
