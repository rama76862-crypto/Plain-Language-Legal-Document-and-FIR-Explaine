# Offline operation and a free online demonstration

## Tested local path

The API can now serve the production frontend from `frontend/dist`. One public-facing application origin is sufficient; the model and private ML service bind only to loopback.

From the repository root in PowerShell:
```powershell
npm --prefix frontend run build
.venv-api/Scripts/python.exe -m apps.run_local start
.venv-api/Scripts/python.exe -m apps.run_local status
```
Open http://127.0.0.1:8000/. Readiness is printed as real 1/3–3/3 steps. Logs and launcher-owned process IDs live under ignored `work/runtime/launcher`. Stop only processes owned by this launcher with:
```powershell
.venv-api/Scripts/python.exe -m apps.run_local stop
```
An already-running model is reused and is not claimed or stopped by the launcher. Asset downloads require internet during setup; inference, local OCR, retrieval and report export then run locally. Official legal-aid/source links require internet when opened. Report HTML bundles Indic fonts.

## Free online demonstration using this laptop

The practical free path uses the laptop for inference and a temporary HTTPS tunnel for the single application origin. The laptop must stay powered on, connected and running. No tunnel has been started or published by this change.

Install `cloudflared` only from Cloudflare's official distribution. With a current version supporting email restrictions, choose the judge's email and run:
```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --allowed-mail judge@example.com
```
Replace the example email with the intended visitor. Do not expose ports 8001 or 8080. Confirm the visitor gate and application consent flow with synthetic documents before sharing the URL. The browser must use the relative API base `/api/v1`; never embed a session token or Hub token into a URL or frontend build. This setup uses polling, not SSE.

Cloudflare documents that these URLs are temporary, have no uptime guarantee, permit at most 200 in-flight requests and do not support SSE. The hostname changes on restart. Email authentication is interactive. HTTPS terminates through Cloudflare, so this mode is not an offline or end-to-end encrypted deployment: document bytes cross its infrastructure on their way to the processing laptop. Consent and privacy copy must describe that deployment honestly. Read [official Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

For production, use a stable authenticated gateway, TLS, explicit origin configuration, request limits, restricted operating-system accounts, secret storage and an infrastructure retention review. The application has session tokens, consent checks, expiry, parser isolation and upload throttling; those do not establish the security of a hosting provider.

## Entirely free cloud GPU alternative

[Hugging Face ZeroGPU](https://huggingface.co/docs/hub/en/spaces-zerogpu) currently permits eligible verified personal accounts older than 30 days to host two free ZeroGPU Spaces. It is shared, queued and quota-limited. It uses a Gradio/PyTorch allocation lifecycle. The current always-running llama.cpp server cannot simply be copied into it and assumed compatible.

A separate cloud adapter would have to load Qwen in Transformers, allocate/release GPU inside the supported callback, retain consent and deletion controls, re-evaluate languages, and account for framework upload caches. That adapter and a public Space have NOT been implemented or validated here. The hosted API container below is now a tested alternative that does not require a cloud GPU; it uses external inference with explicit consent. There is no promise of unlimited, always-on, entirely free GPU hosting. If hackathon rules prohibit remote inference, use the tested offline path.



## Deploy this original application using hosted APIs

The root `Dockerfile` builds the existing Vite frontend and runs BE1 plus private loopback BE2 in one CPU container. It does **not** deploy the separate Clauseora repository. Local `Start.cmd` continues to use Qwen and the local classifier/IndicTrans2 assets. No actual LLM weight fine-tuning was performed by this feature port.

Hosted mode uses `openai/gpt-oss-120b` through Groq. It uses source rules and BM25 retrieval, not the local trained classifier or downloaded E5/IndicTrans2 weights. Server-owned evidence, grounding checks, dates, legal-aid links, questions, review warnings and deletion remain active. Optional Cloudflare checking compares at most six selected claims with excerpts; model agreement is not independent legal review.

### Render free preview

1. Connect the **original** GitHub repository and choose `feature/clauseora-features-and-hosted-mode`. Create a Docker Web Service with the **Free** instance type, or use the root `render.yaml` Blueprint from this branch. Auto-deploy is disabled in the Blueprint.
2. In the hosting dashboard's server-side environment variables, set `GROQ_API_KEY` and `WEB_ORIGIN` to the service's exact HTTPS origin, for example `https://your-assigned-name.onrender.com`. Do not add a trailing path or put secrets into `VITE_*` variables. `INFERENCE_MODE=hosted` is built into the image.
3. Optionally set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AI_TOKEN` with Workers AI permission. If absent/unavailable, the optional checker reports unavailable. It never silently calls another provider.
4. Set the health path to `/api/v1/health`. The supervisor binds BE1 to the platform's `PORT`; BE2 stays on 127.0.0.1:8001 inside the container. Do not publish BE2 separately. Keep a single application instance/worker because sessions are in memory.
5. Wait for startup, check that capabilities say hosted mode, and run a synthetic document through consent, extraction, source review, analysis, questions, report download and deletion before sharing it. Additional Groq consent is required before uploaded bytes are stored. The optional Cloudflare check has separate consent.

This is a free **preview**, subject to account eligibility and quotas, not an always-on production promise. Render documents 15-minute idle spin-down, roughly one-minute cold starts, ephemeral files and a workspace allowance of 750 free instance-hours/month. Restarts destroy active sessions: re-upload rather than claiming recovery. Groq's published free base limit for this model is 8,000 tokens/minute and 200,000/day, with organization-specific limits overriding those numbers. Long documents or concurrent requests can exhaust quotas; partial clauses and unavailable requests remain visible instead of becoming fake results.

Primary references: [Render free limits](https://render.com/docs/free), [Render Blueprint fields](https://render.com/docs/blueprint-spec), [Groq rate limits](https://console.groq.com/docs/rate-limits), [Cloudflare JSON response formats](https://developers.cloudflare.com/workers-ai/features/json-mode/).

A real Render service has **not** been created by this change. The container was exercised locally under a 512 MB memory / 0.5 CPU limit. That evidence is useful, but does not certify provider-side deployment, security or sustained load.

### Reproduce the container locally

Set the server-side environment variables through your local shell or secret manager first. Commands reference variable names only; never paste their values into Git or a screenshot.

```powershell
docker build -t nyayalens-hosted:review .
docker run -d --name nyayalens-hosted-review --memory 512m --cpus 0.5 -p 127.0.0.1:18080:8080 -e GROQ_API_KEY -e CLOUDFLARE_ACCOUNT_ID -e CLOUDFLARE_AI_TOKEN -e WEB_ORIGIN=http://127.0.0.1:18080 nyayalens-hosted:review
```

Open http://127.0.0.1:18080/. Run the actual synthetic journey from the repository root:

```powershell
.venv-api/Scripts/python.exe -m apps.api.scripts.smoke_features --base-url http://127.0.0.1:18080 --allow-hosted --verify-source --output work/verification/features-hosted.json
docker exec nyayalens-hosted-review python -m apps.api.scripts.smoke --base-url http://127.0.0.1:8080 --private-url http://127.0.0.1:8001 --mode real --kind pdf --allow-hosted
```

`--allow-hosted` explicitly consents to sending these synthetic files to Groq. `--verify-source` separately consents to sending selected synthetic claims/excerpts to Cloudflare. Omit the latter to avoid that external check. These are development checks, not five judge-supplied documents or a legal accuracy benchmark.

The native PDF parser is pinned to PyMuPDF 1.28.2 in this image: 2.0 initializes an unnecessary ONNX layout model on import that hung under the Linux parser's address-space limit. Parser lifetime/memory remain bounded, and hosted/Hugging Face credentials are removed from its child environment. Upload text is untrusted; these process limits are not a complete parser filesystem/network sandbox. Limited direct-identifier masking does not remove names, addresses or every identifier; provider retention terms still apply. Never market hosted processing as offline or fully anonymous.
