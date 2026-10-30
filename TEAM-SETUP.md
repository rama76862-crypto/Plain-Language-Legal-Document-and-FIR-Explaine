# Run this project on another teammate's laptop

Target: Windows 10/11 x64, RTX 4050 (normally 6 GB VRAM), 16 GB RAM. This profile uses the 2.5 GB Qwen Q4 GGUF on NVIDIA, one generation slot, and CPU translation/retrieval. It has been checked on the development machine; each teammate must pass the real smoke check below before claiming their laptop works. Close games, other model servers and heavy browser sessions. Use mains power. Allow at least 12 GB free disk space, preferably 20 GB including package/download caches.

## First setup

1. Install Python **3.12 x64**, Node.js **20 or newer** (Node 24 was tested), Git, and the official NVIDIA driver. Reopen the terminal after installation. Confirm `py -3.12 --version`, `node --version`, `npm --version`, and `nvidia-smi` work.
2. Clone the repo or pull main. Any checkout directory is supported, including paths with spaces. Do not copy a teammate's Python venv, token or private runtime documents.
3. From the repo folder run `Setup.cmd`, or `py -3.12 -m apps.setup_local`. It prints actual progress through 13 stages. Downloads can take time; the files total several GB. A failed stage exits visibly. Fix it and rerun; existing valid model assets are reused and checked.
4. When translation download reports gated access, sign into **your own** Hugging Face account. Open both model pages and complete their access agreements:
   - https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M
   - https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M
   Run `apps\ml\.venv\Scripts\hf.exe auth login` in your terminal with your own read token, then repeat `Setup.cmd`. Never paste the token in chat, commit it, or share someone else's token. Standard HF cache authentication is supported. IL-TUR access is not required to run this application.

Setup installs both locked Python environments (including CPU torch from the official PyTorch index), frontend packages, hash-verified Qwen/CUDA assets, the classifier from the committed synthetic seed, E5 embeddings, IndicTrans2 models and English/Hindi/Punjabi OCR, then builds the frontend. It does not train/fine-tune Qwen. Downloaded assets and local receipts remain ignored by Git. Classifier quality and translation accuracy retain their existing review limits.

## Start, diagnose, stop

Run `Start.cmd` and open http://127.0.0.1:8000/ . Each laptop runs its own complete stack; localhost on your laptop is separate from localhost on a teammate's laptop. Setup does not expose services to the network.

```powershell
.venv-api/Scripts/python.exe -m apps.doctor_local
.venv-api/Scripts/python.exe -m apps.run_local status
```

Doctor checks required files, classifier loading, embedding/translation hashes and CPU translation dependencies. Startup refuses incomplete installations. Logs are in `work/runtime/launcher/`. If an unrelated process occupies 8000, 8001 or 8080, resolve that conflict; do not terminate random Python processes. Existing services are reused, so a new setting requires stopping the previously launched owned services first.

For a GPU out-of-memory error, stop owned services using `Stop.cmd`, then start with less GPU offload:

```powershell
.venv-api/Scripts/python.exe -m apps.run_local start --gpu-layers 20
```

This moves some model layers to system RAM and can be slower. `--gpu-layers 0` is an explicit real CPU fallback; acceptable latency is not guaranteed on CPU. Keep 4096 context initially; shorter contexts can reject longer prompts. One request is generated at a time. The launcher gives model requests 300 seconds, and long documents can still exceed the bounded overall analysis budget.

## Verify every new laptop

After startup, run the public real-model journey:

```powershell
.venv-api/Scripts/python.exe -m apps.api.scripts.smoke --mode real --kind pdf
```

It must pass all 9 steps with actual local generation, evidence, questions and deletion. It uses explicitly synthetic text. Then upload your own test PDF, review extracted text, run analysis and download a report. Check Hindi and Punjabi on that machine separately:

```powershell
.venv-api/Scripts/python.exe -m apps.api.scripts.completion_smoke --language-matrix --output work/verification/teammate
```

Passing is technical evidence, not proof of legal/fluent correctness. No fabricated fallback is used when setup fails. Do not claim five judge documents passed until those actual documents and their expected findings have been assessed.

To stop the services this checkout launched, run `Stop.cmd`. A pre-existing model process is deliberately not claimed or stopped. Internet is needed for first setup and official legal-aid links; after successful setup the document pipeline uses local models.

## Troubleshooting

- Python/Node missing: install the prerequisites and reopen the terminal. Setup does not change global execution policy or install drivers.
- Model access 401/403: confirm both gates were granted for the account used by `hf auth login`. Browser login alone does not authenticate Python.
- CUDA startup failure: inspect `model.err.log`; confirm NVIDIA driver compatibility with the pinned CUDA 13.4 runtime. CPU fallback is available for diagnosis. Driver installation/reboot is the laptop owner's step.
- Native/scanned Indic output wrong: correct extraction before analysis and keep the experimental-language warning. OCR/model readiness does not prove meaning accuracy.
- Do not use historical startup instructions saying OCR is unavailable or enabling frontend fixtures. This guide and the current root README supersede them.
