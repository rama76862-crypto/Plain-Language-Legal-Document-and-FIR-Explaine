# Clauseora features: implementation and verification

31 October 2026. Target: **the original Plain-Language Legal Document and FIR Explainer repository**. Branch: `feature/clauseora-features-and-hosted-mode`. Main is unchanged. Clauseora's working tree is clean at `2cbcf55`; the earlier wrong-target attempt remains saved in its own stash and was not pushed.

## What changed

| Before this port | Implemented here | Evidence / limits |
| --- | --- | --- |
| Primary inference required local model assets | Original local path plus an explicit Groq-backed CPU container | Real hosted public API journey passed 9/9; no public Render service created yet |
| No source comparison workspace | Two reviewed/authorized versions, exact before/after sources, bounded added/removed/modified text alignment | Real local and hosted test: one unchanged passage and three change records; exact INR 500 to INR 750 preserved |
| Generic next steps only | Action Pack: source obligation review checklist, role words, stated periods/triggers and questions for legal aid | Actual backend data in frontend; JSON/Markdown/HTML reports contain the Action Pack |
| No optional second-provider source check | Separately consented Cloudflare check, at most six selected claims/excerpts, strict ID mapping and explicit disagreement/unavailable states | Final real hosted run checked five selected claims; agreement is not independent legal review |
| Long optional generated facts/risk prose/caveats | Concise model summaries; source-derived review flags/ledgers and service-owned warnings | Local full profile remains selectable with ML_GENERATION_PROFILE=full; no LLM weight fine-tuning performed |
| Some valid duration wording was rejected | Count/unit validation accepts ASCII and typographic word hyphens | 11-month, 11‐month and 11‑month stay equivalent; changing month to week is still rejected |
| Indic numeric working-copy and FIR framing errors | Decimal normalization for translation only, earlier FIR repair, explicit unilateral-change source rules and stronger optional-prose grounding | Final six-document development run processed 14/14 source clauses with zero expected cue misses |
| Hosted identifiers unprotected / new path absent | Request-scoped limited identifier masking, exact whole-placeholder restoration and rejection of unresolved markers | Twelve-identifier regression prevents first/tenth placeholder corruption; not full anonymization |
| Parser child inherited provider credentials | Provider/HF credentials removed from parser environment | Real subprocess regression confirms removal; parser remains bounded, not a full OS sandbox |
| Linux parser import hung with PyMuPDF 2.0 layout initialization | Hosted native parser pinned to 1.28.2 with bounded process limits | Real hosted PDF and DOCX paths pass; image-only English scan OCR completed in 1.87 s |

`Start.cmd` explicitly selects local primary inference. The hosted container uses Groq plus source rules/BM25, **not** the local trained classifier, E5 or IndicTrans2 weights. Cloudflare is optional and separate from either primary inference path. Source/reference matching remains fail-closed; no invented legal authority is added.

## Checks completed

- ML suite: **138 passed**.
- API suite: **135 passed, 1 skipped, 1 expected failure**.
- The existing Starlette/httpx deprecation warning remains; no new dependency failure was observed.
- TypeScript/Vite production build passed. English/Hindi/Punjabi dictionaries retain **317 keys each**, with parity check passing.
- Real hosted upload/extract/review/analyse/grounded-question/insufficient-evidence/deletion smoke: **9/9**. Three live health checks during generation, maximum observed **8.8 ms**, in that probe.
- Final real feature journey: local **7.72 s**, hosted **8.22 s** for two DOCX uploads/reviews, three analysed clauses, Action Pack, comparison, report export and deletion. Hosted timing includes the optional five-claim Cloudflare check; local timing does not.
- The final hosted feature check returned `cross_checked`, **5** selected claims checked, no reported disagreements. Earlier invalid verifier replies correctly surfaced as unavailable; a successful later run does not guarantee future provider output or semantic correctness.
- Hosted tests ran under Docker limits of **512 MB RAM / 0.5 CPU**. This is local resource-constrained evidence, not a Render-side deployment or concurrency certification.
- Real image-only English scan: actual OCR text recovered the planted amount; authenticated session deleted afterward. Difficult/multilingual scans are not established by this single case.
- Both running application origins return frontend HTML and healthy real ML: local **http://127.0.0.1:8000/**; hosted-mode container **http://127.0.0.1:18080/**. These are localhost URLs, not public deployments.

## Synthetic local document run

These are known, authored development fixtures, **not unseen judge documents, a held-out legal benchmark, or five full-length document types**. Their exact source paragraphs were verified after DOCX extraction before automated review confirmation.

| Development fixture | Explained clauses | Observed end-to-end time |
| --- | --- | --- |
| `agreement_ordinary_en.json` | 3/3 | 5.39 s |
| `agreement_attention_en.json` | 5/5 | 7.41 s |
| `notice_en.json` | 2/2 | 3.89 s |
| `fir_fictional_redacted_en.json` | 2/2 | 3.89 s |
| `notice_hindi_hi.json` | 1/1 | 8.91 s |
| `notice_punjabi_pa.json` | 1/1 | 3.89 s |

All generated output remains `needs_review`. The totals are **14/14 clauses**, **0 request failures**, **0 missed expected cue assignments** on this fixture set. These are coverage/cue checks, not an LLM accuracy score. Timing varies with warm-up and other laptop work; an earlier Hindi run took 26.06 seconds. No universal speedup is claimed.

## Reproduce

Local services, after normal setup and frontend build:

```powershell
.venv-api/Scripts/python.exe -m apps.run_local start
.venv-api/Scripts/python.exe -m apps.api.scripts.evaluate_fixtures --include-punjabi --output work/verification/clauses-local.json
.venv-api/Scripts/python.exe -m apps.api.scripts.smoke_features --output work/verification/features-local.json
```

Hosted mode, with server-side keys configured and the Docker container running:

```powershell
.venv-api/Scripts/python.exe -m apps.api.scripts.smoke_features --base-url http://127.0.0.1:18080 --allow-hosted --verify-source --output work/verification/features-hosted.json
docker exec nyayalens-hosted-review python -m apps.api.scripts.smoke --base-url http://127.0.0.1:8080 --private-url http://127.0.0.1:8001 --mode real --kind pdf --allow-hosted
```

The feature smoke sends only its authored synthetic documents. `--allow-hosted` is explicit Groq consent; `--verify-source` is separate Cloudflare consent. Ignored JSON evidence includes the synthetic result for review, but never session tokens. Uploads/reports/models/datasets/keys remain outside Git. See `contracts/README.md` for the three new endpoints and `deployment/README.md` for Render/secret/origin setup.

## What is still not established

1. **Five actual judge-supplied documents accurately explained and planted risks reliably detected:** not demonstrated. Obtain those documents or a genuinely independent realistic evaluation set with clause-level labels; record misses, false alarms and meaning errors.
2. **Fluent legal meaning in Hindi/Punjabi:** no independent fluent/legal reviewer has certified it. More spelling/paraphrase/negation/actor/amount/anchor cases are required; lexical cues are limited.
3. **Browser-driven end-to-end acceptance:** not completed in this run. The Windows capture helper failed with Direct3D error 0x887A0005, and element geometry was unavailable. Landing accessibility and HTTP assets could be inspected, but they do not establish a full browser journey or visual QA.
4. **Public deployment:** Docker and a Render free-preview Blueprint are prepared and tested locally. A real provider service, HTTPS origin, account eligibility, live quotas and security controls still need provider-side verification. Free tiers can sleep, throttle or lose active sessions on restart. No claim of unlimited free hosting is made.
5. **LLM accuracy / training:** no independent LLM accuracy score exists and no new LLM weight fine-tuning was performed. Prior classifier F1 on small synthetic/European benchmarks does not measure document explanation accuracy. A licensed, labelled Indian legal evaluation/training corpus and human review remain separate work.
6. **Production guarantees:** no sustained concurrent load, comprehensive anonymization, infrastructure security certification or broad difficult-scan/cross-language-Q&A benchmark was performed. Privacy and review warnings remain visible rather than being converted to unsupported success.
