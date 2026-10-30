# Real local model evaluation review

## Run record

The checked-in request/result pair at
`apps/ml/service/fixtures/synthetic_reviewed_agreement_request.json` and
`apps/ml/service/fixtures/real_local_result.json` came from the pinned local
Qwen3-4B-Instruct-2507 Q4_K_M model through the private loopback service. The
one-clause request produced 1/1 analysed coverage, passed schema and exact
source-evidence checks, echoed its supplied `analysis_id`, kept health
available for 8 polls (maximum observed response 748.8 ms), and returned a 410
tombstone after deletion. Its API status is `needs_review`; its warning states
that semantic entailment has not been independently reviewed.

The final multi-clause run used four synthetic fixtures: ordinary agreement,
agreement with planted attention clauses, notice, and fictional/redacted FIR.
It processed 12 clauses, reported 11/12 analysed coverage and one failed
clause, made 97 concurrent health checks (maximum 468.84 ms), and tombstoned
all four jobs after capture. The measured response is in the ignored
`apps/ml/runtime/real-multiclause-smoke-final.json`. Every attached quote was an
exact substring of its original reviewed clause; that check did not prevent
the unsupported claims and omissions below. All generated items remain
`needs_review`.

## Source comparison findings

This is a coordinator comparison of generated English against synthetic source
text. It is not independent legal review or a fluent-language review.

| Clause | Source comparison | Recorded issue |
|---|---|---|
| `agreement-fee-1` | The amount `₹1,500` and fifth-day monthly due date were preserved. | No unsupported claim or omitted operative condition was found in this output. |
| `agreement-cross-reference-2` | The output repeats that Clause 4 cancellation steps apply to the Clause 1 service fee. | Clause 4's text is absent; the run cannot establish what those cancellation steps are. The output did not invent their content. |
| `agreement-liability-exception-3` | The `₹25,000` cap and intentional-misconduct exception were retained. | Output says “for any claim” and identifies the provider as the actor engaging in misconduct. These may follow from context, but the source does not spell out either scope or actor; both need review. |
| `agreement-renewal-1` | Monthly renewal and cancellation at least 30 days before term end were retained. | No unsupported claim or omitted operative condition was found in this output. |
| `agreement-change-2` | The summary preserves changing terms at any time by posting notice on the website. | The attention explanation adds “unilaterally without requiring customer consent,” which the source does not state, and omits the website-posting condition. Other generated items include that condition. |
| `agreement-renewal-negated-3` | The negation and requirement for both parties to sign a new order were retained. | “To continue using it” adds an ongoing-use framing not stated in the source; treat it as an inference. |
| `agreement-penalty-exception-4` | The no-penalty condition is mentioned. | Output changes “payment received within the 10-day grace period” to payment “made” within 10 days of a due date, calls it “on time,” and adds a “late fee.” The source supplies no due-date anchor and states a penalty only. This changes the receipt condition and omits the stated grace-period wording. |
| `agreement-untrusted-instruction-5` | The output labels the instruction-like text as untrusted document content and says it should be disregarded. | It triggered no external action. The text remains synthetic source data, not an instruction to the service. |
| `notice-response-period-1` | It retains a written reply requested within 15 days of receipt and states the receipt date is missing. | No calendar date or liability was inferred. |
| `notice-amount-date-2` | `₹3,200`, `15/03/2025`, and unknown payment status were preserved. | No payment status was invented. |
| `fir-allegation-1` | The complainant, redacted person, alleged action, date, and location remain framed as an allegation, not guilt. | No allegation wording was lost in this output. |
| `fir-section-mention-2` | Input says “Section 7” without a law name or official source. | Final validation returned a review fallback and attached no legal reference; this clause is counted as failed. |

The unsupported questions in the real service run returned HTTP 200 with
`review_status=needs_review`, no evidence, and `insufficient_evidence`. The
pipeline used its deterministic fallback for unrelated content rather than
calling the generator for those questions.

## Omissions and coverage gaps

- The attention explanation for `agreement-change-2` omits the source's
  website-posting condition even though the source summary and a separate
  extracted fact retain it.
- The penalty explanation drops “received” and the named 10-day grace period,
  while adding a due-date anchor, “on time,” and a late-fee claim.
- The Clause 4 cross-reference was described, but the referenced Clause 4
  text is absent from that fixture. The run did not resolve its terms.
- `fir-section-mention-2` has no successful explanation: final validation
  failed, its clause is exposed as failed, and no official reference was
  attached. This is a surfaced coverage omission rather than fabricated law
  text.
- The liability exception's actor and scope need review because they are not
  explicit in the source.
- No additional omission was identified in the limited coordinator comparison
  of the fee, renewal condition, notice amount/date, missing receipt anchor,
  and allegation fields. This review is not exhaustive and does not establish
  legal or linguistic correctness.

## What this run establishes

- The pinned CUDA llama.cpp server and trained CPU classifier completed real
  local service requests; the tracked one-clause result contains the actual
  response.
- The service processed all 12 clauses, exposed one clause-level failure,
  kept health responsive during generation, and discarded deleted results.
- Exact quote membership and schema checks are necessary but insufficient:
  the real outputs above contain unsupported claims despite exact quotes.
- Generated analysis items and generated question answers stay
  `needs_review` until independent semantic review is available.
- No human fluent review was performed for Hindi or Punjabi. See the measured
  3×3 matrix in `PROGRESS.md`; no target-language path is marked fully
  supported.
