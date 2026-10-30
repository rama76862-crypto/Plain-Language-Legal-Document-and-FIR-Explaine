"""Check a teammate installation without creating documents or sharing secrets."""
from __future__ import annotations
import subprocess
import runpy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]


def check_installation():
    checks=[
        ('.venv-api/Scripts/python.exe','API Python'),
        ('apps/ml/.venv/Scripts/python.exe','ML Python'),
        ('frontend/dist/index.html','built frontend'),
        ('apps/ml/training/indian_artifacts/classifier.joblib','Indian-context classifier'),
        ('apps/ml/training/indian_artifacts/metadata.json','classifier provenance'),
        ('apps/ml/models/multilingual-e5-small/manifest.json','retrieval model'),
        ('apps/ml/models/indic-en/manifest.json','Indic to English model'),
        ('apps/ml/models/en-indic/manifest.json','English to Indic model'),
    ]
    ok=True
    for relative,label in checks:
        present=(ROOT/relative).is_file();print(f'{"OK" if present else "MISSING"}: {label}',flush=True);ok=ok and present
    artifacts=runpy.run_path(str(ROOT/'apps/ml/inference/artifacts.py'))
    model=ROOT/'apps/ml/models'/artifacts['MODEL_FILENAME']
    present=model.is_file() and model.stat().st_size==artifacts['MODEL_SIZE_BYTES']
    print(f'{"OK" if present else "MISSING/INCOMPLETE"}: Qwen GGUF',flush=True);ok=ok and present
    server=list((ROOT/'apps/ml/runtime/llama-b12000').rglob('llama-server.exe'))
    present=len(server)==1
    print(f'{"OK" if present else "MISSING"}: local llama.cpp runtime',flush=True);ok=ok and present
    if ok:
        code="from apps.ml.training.indian import IndianClauseClassifier; from apps.ml.retrieval.embeddings import LocalEncoder,MODEL_DIR; from apps.ml.translation.indic_translator import IndicTranslator; from apps.setup_local import cached_model; from pathlib import Path; c=IndianClauseClassifier(); LocalEncoder(MODEL_DIR); t=IndicTranslator(); assert t.available(); assert all(cached_model(Path('apps/ml/models')/n) for n in ['indic-en','en-indic']); import torch; assert not torch.cuda.is_available(); print('OK: classifier loads, embedding/translation hashes verified, CPU translation runtime')"
        result=subprocess.run([str(ROOT/'apps/ml/.venv/Scripts/python.exe'),'-c',code],cwd=ROOT)
        ok=result.returncode==0
    return ok


if __name__=='__main__':
    raise SystemExit(0 if check_installation() else 1)
