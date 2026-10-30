# Synthetic Multi-Clause Evaluation Plan and Fixture Report

## Purpose and limits

These fixtures exercise the private `AnalysisRequest` and `AnalysisPipeline` interfaces with labelled, synthetic reviewed text. They are independent of classifier training data and contain no curated legal references. The Hindi and Punjabi samples are explicitly **not fluent-reviewed**. Tests use deterministic fake classifier, generator, and translator ports; a passing test is not evidence of real local inference quality, translation quality, legal accuracy, or user-facing safety.

In fixture metadata, `expected.status: "complete"` means the clause completed the pipeline and counts toward processed coverage. It does **not** mean the generated explanation or attention reason is semantically supported. The pipeline marks generated summaries, attention reasons, and extracted facts `needs_review` with `semantic_entailment_not_independently_verified` until an independent human reviewer checks entailment. Schema validity and exact source evidence are provenance checks only.

The tests verify routing, processed clause coverage, configured cue categories, unresolved relative periods, source-ID membership, exact evidence substring checks, and the `needs_review` semantic status. Exact quote presence alone does not establish that an explanation correctly interprets negation, exceptions, cross-references, amounts, allegations, or requested actions. Those assertions require independent human semantic review before any quality or language-support claim.

## Fixtures

| Fixture | Clauses and expected behavior | Required human review |
|---|---|---|
| `agreement_ordinary_en.json` | Three ordinary agreement clauses; amount, date-like period wording, cross-reference, liability cap and exception; no attention cue expected. | Confirm the amount, cross-reference, and exception are explained without adding a payment consequence or omitting conditions. |
| `agreement_attention_en.json` | Automatic renewal with a cancellation exception should produce a rule cue; unilateral changes should produce the fixture classifier cue; direct renewal and penalty negations should not produce those rules; embedded document instructions remain data. | Review cue precision, negation scope, cancellation exception, and prompt-injection resistance. |
| `notice_en.json` | Two notice clauses; “within 15 days of receipt” stays unresolved without `receipt_date`; amount and date remain source literals; agreement classifier is skipped. | Confirm the requested action and that payment, liability, and calendar deadlines are not inferred. |
| `fir_fictional_redacted_en.json` | Two fictional, redacted FIR clauses; FIR route bypasses contract classification; allegations remain framed as allegations; an unverified Section 7 mention receives no reference. | Check roles, wording, date, location, allegation framing, and that no statute is guessed. |
| `notice_hindi_hi.json` | One Hindi notice clause containing an amount and receipt-relative period; without a fluent-reviewed translation it returns `needs_review`, preserves original evidence, and leaves the receipt date missing. | Fluent Hindi review before any translation-assisted explanation or classification. |
| `notice_punjabi_pa.json` | One Punjabi notice clause with the same failure-path expectations and source preservation. | Fluent Punjabi review before any translation-assisted explanation or classification. |

Every clause records its expected route, status, attention categories, source evidence anchors, failure code if applicable, and semantic review tasks. Fixture text is synthetic and should not be represented as an actual agreement, notice, FIR, or legal authority.

## Model-free checks

Run from the repository root:

```powershell
& 'apps\ml\.venv\Scripts\python.exe' -m pytest 'apps\ml\tests\test_multiclause_evaluation.py' -q
```

The tests assert that the pipeline processes every fixture clause marked `complete`, while generated items remain `needs_review` with the semantic-entailment limitation. They also assert that the pipeline skips the classifier for notices/FIRs and unreviewed Indic translations, emits original-clause evidence, reports unresolved receipt dates, flags configured English attention cues, rejects unsupported follow-up questions without another generation, and keeps embedded document instructions inside the untrusted prompt payload. All generation and classification outputs in these tests are deterministic mocks.

## Real-inference evaluation still required

Use the separate local-model smoke command in `apps/ml/README.md` to verify one real English clause through the trained classifier and local generator. It does not validate this fixture set's semantic expectations. Before describing these examples as quality results, have independent reviewers mark each expected explanation/fact against the full reviewed source, especially:

- whether negation and exception clauses are scoped correctly;
- whether a cross-reference is followed to the correct clause;
- whether amounts, dates, and time periods retain their original meaning;
- whether a notice request is not converted into an asserted duty or debt;
- whether each FIR statement stays an allegation and redacted roles remain distinct;
- whether Hindi/Punjabi source details survive local translation and selected-language explanation.

No fluent review, official-source verification, independent semantic labels, or real model response is claimed by this report.

## Indic notice deadline regression coverage

The Hindi and Punjabi notice fixtures remain `needs_review` because no fluent-reviewed translation is supplied. The regression tests separately check that the extracted source periods validate against the English display “15 days after receipt,” that `receipt_date` remains missing and no date is resolved, and that mismatched values (`16 days`) or units (`15 weeks`) are rejected. Passing this literal-alignment check does not validate translation or semantic correctness.
