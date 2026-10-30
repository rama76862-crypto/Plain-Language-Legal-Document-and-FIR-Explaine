# NyayaSarathi / NyayaLens

Local plain-language legal document and FIR explainer for CTBF-AI-09. English, Hindi and Punjabi paths are implemented with mandatory review warnings. Generated text is information only, not legal advice.

Read FULL-FEATURE-VERIFICATION.md for current checks and unresolved accuracy gates. Role handoffs are specifications; historical audit files are not current acceptance evidence.

## Start on the configured GPU laptop

~~~powershell
npm --prefix frontend run build
.venv-api/Scripts/python.exe -m apps.run_local start
~~~

Open http://127.0.0.1:8000/ . The launcher starts missing local services, preserves existing model assets, and does not start public exposure. Use the real local model; the frontend has no fixture mode.

Setup and artifact recreation: apps/api/README.md and apps/ml/README.md. Frontend details: frontend/README.md. Deployment options: deployment/README.md. The model weights, datasets, runtime documents, credentials and generated verification output are ignored by Git.

The core path is consent -> upload -> extraction -> explicit review -> local analysis -> evidence/questions -> optional report download -> deletion or expiry. Do not represent synthetic checks, classifier F1 or coverage as legal/LLM accuracy.
