# Backend 2: local ML service

Backend 2 is a private, loopback-only service under `apps/ml`. It accepts the
Contract v1 analysis payload, keeps the supplied `analysis_id`, and stores job
state and reviewed document text in process memory for up to 30 minutes. It
does not call an external AI inference service.

## Runtime layout

- Python 3.12.10 project environment: `apps/ml/.venv`.
- The word and character TF-IDF classifier and BM25 retrieval run on CPU.
- The local generator is Qwen3-4B-Instruct-2507 Q4_K_M on the pinned
  `llama.cpp` Windows CUDA 13.4 build, bound to `127.0.0.1:8080`.
- The private FastAPI service binds to `127.0.0.1:8001` and uses one analysis
  worker, two pending queue slots, and a 30-minute result lifetime.
- Downloads, classifier artifacts, model runtime files, and job content are
  local runtime data. The model and runtime download roots are ignored by Git.

The model artifact is pinned in `inference/artifacts.py`: GGUF repository
revision `ae44f08e1392f39c0e474af10c3ff8355c8b6688`, file SHA-256
`2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`, and
upstream Qwen revision `cdbee75f17c01a7cc42f958dc650907174af0554`. The
llama.cpp build is b12000, commit
`68d20b884c3878217de79eade0a249efde96ab38`. Setup downloads are hash checked
before extraction or use. Qwen's upstream model declares Apache-2.0; check the
quantizer repository card and notices before redistributing its GGUF.

## Environment setup

From the repository root in PowerShell:

```powershell
py -3.12 --version
py -3.12 -m venv apps/ml/.venv
apps/ml/.venv/Scripts/python.exe -m pip install --upgrade pip
apps/ml/.venv/Scripts/python.exe -m pip install -r apps/ml/requirements.lock.txt
apps/ml/.venv/Scripts/python.exe -m pip check
```

The checked-in constraints are in `requirements.in`; `requirements.lock.txt`
records the Windows environment used for this implementation. Recreate the
venv when changing Python minor versions.

## Dataset and classifier

Training downloads only the pinned LexGLUE `UNFAIR-ToS` configuration, inspects
its card and feature metadata before label mapping, checks the license, split
names/counts and source hashes, and caches its data under the ignored
`apps/ml/cache/` directory. It fits word and character TF-IDF on train, tunes
one threshold per label on validation, and evaluates test once.

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.training.train
```

Locally generated classifier artifacts are written under
`apps/ml/training/artifacts/`: the hash-checked joblib classifier and vectorizer,
label map and thresholds, pinned dataset manifest, and held-out metrics with
false-negative examples. These are local artifacts; rerun training to recreate
them after a clean checkout. The recorded test result was macro-F1 `0.736671`
and micro-F1 `0.734584` over 1,607 examples. The current export saves 22
ranked false-negative example records, capped at three per label. Per-label
support and recall imply 49 missed label assignments; the saved records contain
21 distinct test example IDs. The total number of unique affected test
sentences is unavailable from this capped export. The updated exporter counts
that value from the full prediction matrix during its single test pass on a
future training run. See [METRICS.md](training/METRICS.md) for per-label counts
and caveats. The official splits contain 33 unique normalized text overlaps
between train and test; because source document IDs are absent, this may make
held-out metrics optimistic. An empty classifier prediction is not proof of
safety.

The model is a European terms-of-service cue baseline. It is not a classifier
of Indian enforceability or a legal conclusion. Agreement results combine its
cues with reviewed wording rules and source evidence.

The curated official-reference set is versioned at
`apps/ml/data/references.json`; source locators, access dates, excerpt hashes,
reuse notes, and known limits are in
`apps/ml/data/REFERENCE_SOURCES.md`. It contains six short records from India
Code, the Department of Consumer Affairs, and NALSA. Reference matches are
filtered by law, jurisdiction, version, and exact section where available. An
exact section match does not establish that a provision applies or supports an
interpretation. The E-Commerce Rules source PDF timed out during direct opening;
its excerpts were confirmed from the official indexed source preview and
remain marked for direct recheck before release. Applicable reuse terms have
not been independently established.

## Local model setup and generation

The setup command uses verified byte-range downloads with real byte progress
bars; all payloads go to ignored local directories. It downloads the pinned
GGUF and CUDA runtime archives and verifies each expected size and SHA-256.

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.inference.setup_runtime
```

After setup completes successfully, open PowerShell terminal 1 and start the
model server. It rejects non-loopback bind addresses and starts one generation
slot:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.inference.serve
```

In terminal 2, verify the model server with one labelled synthetic clause. This
command checks the model's structured explanation, then attaches an exact quote
verbatim from the reviewed fixture as source evidence. It records measured
latency and sampled NVIDIA GPU memory; the output report is saved locally under
the ignored runtime directory. Evidence is source-selected by the service and
is never invented by the generator.

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.inference.smoke
```

`smoke.py` checks the real generator. For the full classifier + generator +
evidence validator + asynchronous HTTP service fixture, keep the model server
running and use:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.service.smoke
```

To run real local pivot and explanation checks for all 3×3 source/output
combinations with synthetic clauses, run:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.translation.language_matrix_smoke
```

It writes measured local outputs and per-cell checks under the ignored runtime
directory. Hindi/Punjabi source fixtures pass through an English pivot before
target-language generation is checked. All cells remain `needs_review` because
no fluent-reviewed Hindi or Punjabi set is configured; this command does not
claim linguistic accuracy.

The latest 3×3 run attempted all nine cells. Schema checks passed in all nine;
script checks passed in four of six Indic-output cells and failed for
English→Punjabi and Hindi→Punjabi. Protected lexical markers changed in six
cells. All nine remain `needs_review`; none has fluent review. See
`PROGRESS.md` for cell-by-cell results and the ignored runtime report for
per-attempt output.

The model-required commands (`inference.smoke`, `service.smoke`,
`translation.language_matrix_smoke`, and `evaluation.real_local_smoke`) require
the pinned model assets and a working NVIDIA CUDA runtime. They run separately
from fast unit tests; no mock result is used as local-inference proof.

## Private service

Start the service from the repository root in a separate terminal after the
model server is healthy:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.service
```

The core endpoints are:

- `GET http://127.0.0.1:8001/internal/health`
- `POST http://127.0.0.1:8001/internal/analyse` (returns 202)
- `GET http://127.0.0.1:8001/internal/jobs/{analysis_id}`
- `DELETE http://127.0.0.1:8001/internal/jobs/{analysis_id}`
- `POST http://127.0.0.1:8001/internal/question`

BE1 supplies `analysis_id`; BE2 echoes and binds it to the request. Reusing an
ID with a conflicting request is rejected. A deleted or expired job cannot
restore its result. Queue saturation, model timeout, model unavailability,
revision conflict, and deletion have explicit error codes. Keep this service
private; do not proxy its API to an untrusted public client. Request bodies are
not written to application logs.

### Language and document behavior

Agreement clauses run through the trained classifier and reviewed rules. FIR
items preserve allegation framing. Notice items describe the stated requested
action; relative deadlines such as “within 15 days of receipt” remain
unresolved until the receipt date is supplied. The original reviewed text is
retained as evidence.

Hindi and Punjabi text may be translated locally to an English working pivot,
but no fluent-reviewed evaluation set is currently configured. Such clauses
remain `needs_review`; health does not claim those languages are tested.
Question responses use only stored reviewed clauses, completed analysis items,
and references attached to that result. Without reliable matching evidence,
the service returns an insufficient-evidence answer. Official references are
loaded from the versioned `apps/ml/data/references.json`; no authority is
fabricated when no reliable match exists. Generated explanations and grounded
question answers stay `needs_review` with a
`semantic_entailment_not_independently_verified` limitation until an
independent source review is available. Schema validity and exact quote
membership alone do not establish semantic support.

## Independent handoff fixtures

`apps/ml/service/fixtures/synthetic_reviewed_agreement_request.json` is a
machine-readable Contract v1 request with a BE1-supplied `analysis_id`. The
real local response is stored at
`apps/ml/service/fixtures/real_local_result.json`; it is a synthetic one-clause
result captured from the local CUDA model and private service. It remains
`needs_review` because schema and source-evidence checks do not verify semantic
entailment.

To recreate that response after installing the ignored assets, start the model
server first, then run:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.service.smoke --output apps/ml/service/fixtures/real_local_result.json
```

To run ordinary agreement, planted-attention agreement, notice, and fictional
FIR fixtures through the real private service and local model, run:

```powershell
apps/ml/.venv/Scripts/python.exe -m apps.ml.evaluation.real_local_smoke
```

That command writes measured results under ignored `apps/ml/runtime/`, checks
actual clause progress and health responses, and records source quotes,
attention-category differences, semantic-review fields, and deletion
tombstones. Its output is not a semantic or legal quality score. The latest
four-document run processed 12 clauses, produced 11/12 analysed coverage, and
exposed one failed clause. Exact attached quotes did not prevent unsupported
claims; the source-by-source findings and omissions are recorded in
[`evaluation/REAL_LOCAL_REVIEW.md`](evaluation/REAL_LOCAL_REVIEW.md). Generated
items stay `needs_review` until independent semantic review.

## Tests and verification

Fast tests use explicit labelled fixtures and fake model ports; they do not
count as local-generation proof:

```powershell
apps/ml/.venv/Scripts/python.exe -m pytest apps/ml/tests -q
apps/ml/.venv/Scripts/python.exe -m compileall -q apps/ml
```

The model-required checks are the smoke commands described above. Run them
after model setup, one at a time, with one local server and one generation
worker. A result that reaches 100% processed clauses can still be
`needs_review`; check the failure count, warnings, and semantic-review status.
See `PROGRESS.md` for milestone evidence and current blockers.

## Configuration

Optional environment variables, set in PowerShell before starting the service:

```powershell
$env:ML_PORT = "8001"
$env:ML_LLM_BASE_URL = "http://127.0.0.1:8080"
$env:MODEL_TIMEOUT_SECONDS = "180"
# Optional local classifier artifact directory:
# $env:ML_CLASSIFIER_DIR = "D:\local\be2\classifier-artifacts"
```

The model launcher accepts `--host`, `--port`, `--ctx-size`, and `--gpu-layers`,
but bind hosts must remain loopback addresses. The service intentionally
starts with degraded health if the classifier or model assets are missing.
