# UNFAIR-ToS baseline metrics

These figures are from the existing single evaluation of the pinned official
LexGLUE test split. Thresholds were selected using validation data; the test
split was not used for tuning.

| Label | Test positives | Precision | Recall | F1 | Missed label assignments |
|---|---:|---:|---:|---:|---:|
| Arbitration | 7 | 1.000 | 0.429 | 0.600 | 4 |
| Choice of law | 13 | 0.923 | 0.923 | 0.923 | 1 |
| Content removal | 13 | 0.556 | 0.769 | 0.645 | 3 |
| Contract by using | 23 | 0.944 | 0.739 | 0.829 | 6 |
| Jurisdiction | 16 | 0.800 | 0.750 | 0.774 | 4 |
| Limitation of liability | 38 | 0.750 | 0.711 | 0.730 | 11 |
| Unilateral change | 38 | 0.742 | 0.605 | 0.667 | 15 |
| Unilateral termination | 38 | 0.623 | 0.868 | 0.725 | 5 |

Macro-F1 is **0.736671** and micro-F1 is **0.734584** over 1,607 test
sentences. The per-label missed counts sum to **49 missed label assignments**.
The JSON exporter saves a ranked sample capped at three records per label; the
current artifact contains **22 saved example records**. Those records contain
**21 distinct test example IDs**. The current capped export cannot establish
the total number of unique test sentences with one or more missed labels, so
that total is reported as unavailable rather than inferred from the sample.
The exporter now counts unique affected rows directly from the full prediction
matrix during the next ordinary one-pass evaluation; it does not add a second
test evaluation.

The preserved official splits have 33 unique normalized text overlaps between
train and test. The dataset provides no source document IDs for a document
level split, so held-out metrics may be optimistic. The labels are European
terms-of-service concern cues, not Indian enforceability findings. No detected
cue does not mean that a clause is safe.
