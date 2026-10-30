# Backend model implementation and reproduction

This document supersedes older progress claims about the new components. Historical reports remain evidence of their original runs.

## Actual architecture

Upload with consent → isolated PDF/DOCX extraction (local Tesseract fallback) → explicit source review → source fact ledger and document profile → lexical rules plus optional Indian-context classifier → BM25 + local multilingual E5 retrieval → local Qwen generation → literal/script/grounding checks and one repair → explanation, risk cues, unresolved deadlines and clarification steps → authenticated temporary review report / questions → deletion or expiry.

Qwen is a pretrained language model, not a newly trained Indian legal model. The Indian-context classifier was trained separately. IndicTrans2 supplies local translation in both directions; its portable preprocessing implementation is not certified equivalent to the official toolkit. English explanations are generated before Indic output translation. Every generated legal explanation remains needs_review.

## Install and recreate

Python 3.12. Use separate API and ML virtual environments. The ML lock includes CPU PyTorch; configure the official CPU wheel index when reproducing:
```powershell
apps/ml/.venv/Scripts/python.exe -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r apps/ml/requirements.lock.txt
apps/ml/.venv/Scripts/python.exe -m apps.ml.training.indian --train
apps/ml/.venv/Scripts/python.exe -m apps.ml.retrieval.setup_embeddings
apps/ml/.venv/Scripts/python.exe -m apps.ml.translation.setup_models
```
The translation setup needs approved access to both AI4Bharat repositories. An explicitly authorized read-only token is read internally from ignored `work/runtime/hf/token`. Never put a token in Git, chat, a command argument or frontend environment variables. Browser login alone does not authenticate Python. Keep model licences and access conditions with redistributed artifacts.

The existing README documents the pinned Qwen GGUF and llama.cpp downloads. They were preserved. For Tesseract:
```powershell
.venv-api/Scripts/python.exe apps/api/scripts/setup_ocr.py
```
Model files, native runtimes and classifier artifacts are intentionally ignored by Git: a clean clone requires setup. No private document data is used for training.

## Models and training

See `training/INDIAN-MODEL-CARD.md`. The default now prefers the locally trained Indian-context cue model if its artifact exists. Missing Indian artifacts fall back to the preserved EU baseline; inspect health/provenance before claiming the Indian model is active. Neither benchmark is an LLM score.

The new seed contains 378 authored synthetic Indian-context examples, split by template family. It is not expert-labelled legal data. IL-TUR access/terms are separate; a download token cannot accept those terms. Court datasets are also not automatically labelled for unfair rent/loan clauses. Adding reviewed real examples requires source URL, licence, review status and family-separated train/validation/test splits. Do not tune on the held-out test.

## New behavior and bounds

- Explicit source cues for payment penalties, automatic renewal and waived rights survive a failed paraphrase. A flag means review a quoted phrase, not that a term is illegal.
- Profiles distinguish rent, loan, land, notice and FIR while retaining Contract v1 document types.
- Numeric amounts, durations, roles, conditions, negation and timing anchors receive conservative checks. These catch some mutations but are not a semantic entailment proof.
- Dates and periods retain original units and exact source text. Ambiguous dates, relative anchors and monthly recurrence remain unresolved; no legal due date is invented.
- Hybrid retrieval uses local E5 cosine candidates plus BM25 reciprocal-rank fusion. E5 averages overflow windows for long clauses. Similarity is not truth probability.
- References require official hosts, matching law/section, provenance and excerpt hashes. Current automated rechecks admitted only the NALSA FAQ record; five statutory/reference entries remain excluded pending source/reuse review. This is not a comprehensive Indian law corpus.
- Literal source ledgers and localized clarification steps appear in reports; next steps are also displayed in the results overview.
- Output translation checks script and protected details, with one controlled repair. Fluent legal translation review remains outstanding; no language was promoted to supported.
- Qwen JSON schema now uses the nested json_schema form tested against the real llama.cpp server.
- 25 MB / 50 PDF pages are configurable ceilings, with 500,000 extracted characters, bounded DOCX expansion, parser memory/time limits and an overall analysis budget. They are not an accuracy or latency guarantee.

## Public report and cancellation endpoints

`GET /api/v1/documents/{document_id}/analyses/{analysis_id}/report?format=json|md|html&include_questions=false`

Requires the document's X-Session-Token header and a current ready analysis. A report is assembled automatically in temporary server memory. It is not silently saved to permanent server disk. The user downloads it explicitly. JSON/Markdown/self-contained HTML include source, explanations, warnings, review status, deadlines, next steps, provenance and optionally Q&A. HTML has embedded Devanagari/Gurmukhi fonts and can be printed locally. Report exports remain on the user's computer after server deletion.

`DELETE /api/v1/documents/{document_id}/analyses/{analysis_id}` cancels/deletes that analysis and report while allowing a fresh analysis of the reviewed document. Session deletion removes the document too.

`GET /api/v1/capabilities` publishes current limits, consent policy and experimental language state. Upload requires multipart processing_consent=true before application session storage. ML_SERVICE_TOKEN can protect BE1↔BE2 calls in addition to loopback binding.

## Verification

```powershell
apps/ml/.venv/Scripts/python.exe -m pytest apps/ml/tests -q
.venv-api/Scripts/python.exe -m pytest apps/api/tests -q
.venv-api/Scripts/python.exe -m apps.api.scripts.smoke --mode real --kind pdf
.venv-api/Scripts/python.exe -m apps.api.scripts.completion_smoke --language-matrix
```
The completion script uses explicitly synthetic documents. It saves only synthetic review examples and evidence to ignored `work/verification/completion`. It checks reports, all 3×3 language paths, source cue presence, coverage and deletion. Its result is not legal accuracy. Independent meaning/fluent review and judge-supplied documents remain separate acceptance gates.

Start/stop and free deployment options are in `deployment/README.md`. No external AI inference service, blockchain or invented model score was added.

