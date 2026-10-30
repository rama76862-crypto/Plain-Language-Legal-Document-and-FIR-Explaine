# Backend completion tracker — 30 October 2026

The eight steps track engineering work, not a percentage of legal correctness.

| Step | Implemented / verified | Remaining gate |
|---|---|---|
| 1/8 Audit and baseline | Preserved existing local assets and Contract v1 boundaries; recorded historical metrics honestly. | None for the audit. |
| 2/8 Source facts, risks and deadlines | Source ledger; explicit penalty/renewal/waiver rules; mutation guards; exact/relative/recurring deadlines; document profiles. | Rule coverage is finite; no legal-validity verdict. |
| 3/8 Indian data and model resources | Restricted Hub credential; both pinned IndicTrans2 models; local E5; trained synthetic Indian-context classifier. | IL-TUR still denies gated data access. Expert-labelled target examples and licence review remain open. |
| 4/8 Retrieval and multilingual generation | Real local Qwen with enforced JSON schema; hybrid retrieval; local translation; all nine language paths passed small synthetic technical checks. | Fluent and independent meaning review not performed. |
| 5/8 Reports and frontend integration | Automatic temporary per-analysis report; authenticated JSON/MD/HTML export; embedded Indic fonts; next steps; persistent in-session Q&A tab history. | Browser verified native PDF display, review, real Punjabi output and HTML report download; complete UI localization remains unreviewed. |
| 6/8 Consent, retention and limits | Consent before session storage; deletion/cancellation; upload throttle; parser isolation; optional private-service token; 25 MB / 50-page defaults. OCR installed and exercised. | Hindi sample OCR still differs from source. Hosting infrastructure is not audited. |
| 7/8 Local packaging and free deployment path | Production frontend served by API; owned-process start/stop helper; offline and authenticated free-tunnel instructions. | No public tunnel or Space published. ZeroGPU adapter is not implemented. |
| 8/8 Acceptance and handoff | 117 ML tests; full API run 123 passed / 1 skipped / 1 expected failure; six completion tests passed after final additions. Real 9/9 API journey and 14/14 synthetic completion checks. | Five judge-supplied documents, legal meaning review, representative language/OCR evaluation and production review remain outstanding. |

## Read next

- `apps/ml/COMPLETION.md`: actual architecture, setup, endpoints, privacy and verification.
- `apps/ml/training/INDIAN-MODEL-CARD.md`: dataset provenance, measured metrics and limits.
- `deployment/README.md`: local launch and free online demonstration options.
- `apps/api/scripts/completion_smoke.py`: reproducible synthetic end-to-end and 3×3 language checks.
- `contracts/openapi.json`: exported current API contract.

## Measured behavior

The public real-model upload → extraction → review → analysis → grounded question → unsupported question → deletion journey passed 9/9. Four health probes during its analysis returned successfully; maximum observed latency was 1054.8 ms in the first run and 718.6 ms in the final repeated run.

The extended real public run passed 14/14 technical cases: five synthetic document types plus nine source/output language pairs. Reports downloaded and became inaccessible after deletion. Outputs remain needs_review. An initial checker incorrectly ignored notice_action/allegation summaries when checking script; that checker was corrected and the full run repeated. A land-clause actor invention was rejected, and stricter role instructions fixed the development fixture on the repeated run.

A 50-page simple native-text PDF yielded 50 clauses in 0.03 seconds in a direct parser probe. That is not a 50-page OCR/model throughput benchmark. Sample English OCR and Punjabi OCR matched their synthetic source after whitespace normalization; Hindi did not. Damaged Indic PDF character maps now trigger OCR/review instead of being treated as clean text.

The production frontend entry JavaScript decreased from about 1.66 MB to 354 kB before gzip, with route/PDF modules split out. The continuously rendered WebGL coverage ring was replaced by an accessible static SVG. No claim of a measured interactive-latency improvement is made.

## Accuracy is not certified

Qwen was not fine-tuned. The new classifier has macro-F1 0.590476 / micro-F1 0.64 on only 18 synthetic held-out examples. Its waiver-label F1 is zero; source rules cover explicit waiver cues separately. These are not LLM scores. The original EU model's higher score belongs to a different dataset with its documented overlap caveat.

Five statutory/reference records remain excluded from trusted citations pending direct source/reuse review; one NALSA FAQ record is admitted. Similarity, exact quotation, script checks and schema validity do not establish semantic entailment. No language was marked supported based on these tests.

No blockchain, hosted AI inference, public deployment, commit or push was performed in this implementation pass.


## Browser verification

The production UI was exercised at http://127.0.0.1:8000/. A synthetic native PDF was uploaded with consent, visually compared with extraction, confirmed for review and analysed into Punjabi by the real local model. Its HTML review report downloaded through the frontend. The original source viewer initially failed through PDF.js URL transport; it now reads the authenticated in-memory blob into bytes, which rendered successfully in the repeated check. Browser test results remain synthetic and are not fluent/legal review.
