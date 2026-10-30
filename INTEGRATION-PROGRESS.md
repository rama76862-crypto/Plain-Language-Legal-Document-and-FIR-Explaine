# Backend integration progress

Recorded 30 October 2026. This checklist measures demonstrated integration steps, not legal accuracy or time remaining.

**Checklist: [####-] 4/5 passed; browser/quality acceptance remains open.**

| Milestone | Status | Evidence |
|---|---|---|
| Local services and environments | Passed in the reported run | llama.cpp, BE2, BE1 and Vite were running on loopback ports 8080, 8001, 8000 and 5173. |
| Private/public contracts | Passed | Six-field private question payload, shared 4,000-character limit, nullable reference version and count/ID failure reconciliation implemented. |
| Real public API journey | Passed in the reported run | Synthetic native-text PDF smoke completed 9/9 steps, 1/1 clause processed, real analysis returned needs_review, grounded answer repaired once and unsupported question returned insufficient_evidence. |
| Deletion and focused regressions | Passed | Public document returned 404 afterward and private job retained JOB_DELETED tombstone. Pre-push review independently reran 41 BE1 adapter tests and 11 BE2 contract/pipeline tests successfully. |
| Browser and quality acceptance | Open | Browser-driven journey not completed. Semantic/fluent review absent; OCR unavailable. Health responsiveness during generation was not measured in the passing smoke run. |

## Important limits

- Exact evidence and successful HTTP transport do not establish semantic/legal correctness. Preserve needs_review.
- BE2 language flags remain untested; no fully reviewed language matrix is claimed.
- The passing smoke preceded the addition of an in-generation health probe. Run the updated smoke before claiming that measurement passed.
- Historical integration results above are from the supplied execution report, not a fresh GPU run during pre-push review.
- Keep model, classifier, environments and private runtime artifacts out of Git. See RUN-EVALUATION.md for startup and reproduction.
