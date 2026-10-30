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

A separate cloud adapter would have to load Qwen in Transformers, allocate/release GPU inside the supported callback, retain consent and deletion controls, re-evaluate languages, and account for framework upload caches. That adapter and a public Space have NOT been implemented or validated here. Free CPU hosting is possible in principle but is not a tested acceptable-latency substitute for this GPU service. There is no promise of unlimited, always-on, entirely free GPU hosting. If hackathon rules prohibit remote inference, use the tested offline path.

