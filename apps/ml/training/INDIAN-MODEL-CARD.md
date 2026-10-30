# Indian-context clause cue classifier v1

## Purpose and limits

A fast TF-IDF word/character-feature logistic classifier proposes attention categories for reviewed agreements. Conservative source rules guard its core cues. It does not determine enforceability, legal rights, guilt, case outcomes or document safety.

This is an English classifier. Hindi/Punjabi text can be translated into an English working copy by the local translation adapter; that is not proof of multilingual classification accuracy.

## Data and splits

- Data: 378 authored synthetic examples in `apps/ml/data/indian_cues.jsonl`.
- Labels: payment_penalty, automatic_renewal, waived_rights, deposit_forfeiture, unilateral_change, unilateral_termination, limitation_of_liability.
- Train: 344 examples / 43 template families.
- Validation: 16 examples / 16 families.
- Held-out development test: 18 examples / 18 families, two positives per label.
- Numeric variants remain in the same family/split. Loader rejects exact text and family overlap across splits.
- Corpus SHA-256: b248e5a3ed05e38a0bcf05ae596281921950e962adda1c561d7db05924824760.
- Source/review: authored synthetic; not independently reviewed. This is not an Indian legal benchmark.

## Measured single held-out evaluation

Macro-F1: **0.590476**. Micro-F1: **0.640000**.
Fit time: **0.064666 seconds**, excluding environment setup, data preparation and downloads.

| Label | Precision | Recall | F1 |
|---|---:|---:|---:|
| payment_penalty | 1.000 | 0.500 | 0.667 |
| automatic_renewal | 1.000 | 1.000 | 1.000 |
| waived_rights | 0.000 | 0.000 | 0.000 |
| deposit_forfeiture | 0.500 | 0.500 | 0.500 |
| unilateral_change | 0.667 | 1.000 | 0.800 |
| unilateral_termination | 0.500 | 0.500 | 0.500 |
| limitation_of_liability | 1.000 | 0.500 | 0.667 |

The test is tiny and synthetic. Waived-right detection failed in the classifier evaluation; deterministic source rules cover explicit waiver wording. Rule performance is separate from classifier F1. Do not represent combined demo successes as classifier improvement or retune this test.

The preserved UNFAIR-ToS model has macro-F1 0.736671 / micro-F1 0.734584 on its different EU dataset. That score cannot be compared directly to the new Indian-context test. Its documented 33 normalized train/test overlaps remain a limitation.

## What has not been trained

Qwen3-4B-Instruct-2507 weights were not fine-tuned, and no LLM legal-accuracy metric was established. IndicTrans2 and E5 are pretrained downloaded components. There is no honest single score for the complete pipeline yet.

To improve: obtain appropriate permission for real Indian source examples, have qualified reviewers label the target risk categories and negatives, separate by source document/template family, tune only on training/validation, and evaluate once on a fresh untouched test. IL-TUR/court-language resources may help domain or language tasks but do not automatically supply these contract-cue labels.

