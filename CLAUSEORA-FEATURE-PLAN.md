# Clauseora features in the original CTBF project

Implementation target: this repository only. Clauseora is a read-only feature/design reference. No push is authorized until the user explicitly permits it.

1. Restore the saved accuracy fixes: Indic numeric working-copy normalization, source cues for unilateral changes, grounding of optional risk descriptions, safe service-owned caveats and earlier FIR framing validation.
2. Add the Clauseora Action Pack: source-linked obligation checklist, stated due/trigger text and up to five questions to raise with legal aid. Keep all unchecked obligations and caveats visible; do not prescribe legal strategy.
3. Add version comparison: two separately authorized/reviewed documents, server-owned before/after evidence, added/removed/modified passages and explicit uncertainty about semantic significance. No invented source anchors or claim that unchanged text is legally safe.
4. Add optional hosted Groq inference for deployment; local Qwen remains the default. Add request-scoped PII placeholders and explicit external-provider consent. Source rules/BM25 work without downloading/training a classifier in the hosted image. Preserve evidence, source guard checks and review warnings.
5. Add optional Cloudflare source checking, limited to selected claims/excerpts. Treat agreement as source checking, not legal correctness. Expose unavailability and contradictions.
6. Package the original app for a hosted CPU container serving its existing frontend/public API; private ML stays loopback. Document environment variables and retention. Do not pretend Vercel can run the local CUDA model server.
7. Improve local latency with concise generation, avoiding duplicate model-generated caveats/facts when source-derived data is already available. Measure actual timings before claiming gains.
8. Verify real local and hosted workflows, compare changes, Action Pack and privacy/deletion. Reuse labelled synthetic documents and preserve failure counts. Actual judge documents and independent legal/fluent review remain unavailable.

Clauseora's Next.js routes and site are not the target. Its uncommitted port attempt was saved and removed from its working tree. Existing models/credentials/private documents remain ignored; no secrets are copied into committed files.
