"""Reproducible Windows teammate setup. Run: py -3.12 -m apps.setup_local."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / '.venv-api' / 'Scripts' / 'python.exe'
ML = ROOT / 'apps' / 'ml' / '.venv' / 'Scripts' / 'python.exe'


def commands():
    return [
        ('API environment', [sys.executable, '-m', 'venv', str(API.parent.parent)]),
        ('ML environment', [sys.executable, '-m', 'venv', str(ML.parent.parent)]),
        ('API packages', [str(API), '-m', 'pip', 'install', '-r', 'apps/api/requirements.lock.txt']),
        ('ML packages including CPU translation runtime', [str(ML), '-m', 'pip', 'install', '--extra-index-url', 'https://download.pytorch.org/whl/cpu', '-r', 'apps/ml/requirements.lock.txt']),
        ('Frontend packages', [shutil.which('npm.cmd') or 'npm.cmd', '--prefix', 'frontend', 'ci', '--no-audit', '--no-fund']),
        ('Pinned Qwen and llama.cpp assets', [str(ML), '-m', 'apps.ml.inference.setup_runtime']),
        ('Indian-context cue classifier', [str(ML), '-m', 'apps.ml.training.indian', '--train']),
        ('Local multilingual retrieval', [str(ML), '-m', 'apps.ml.retrieval.setup_embeddings']),
        ('Local Hindi/Punjabi translation', [str(ML), '-m', 'apps.ml.translation.setup_models']),
        ('English/Hindi/Punjabi OCR', [str(API), 'apps/api/scripts/setup_ocr.py']),
        ('Production frontend', [shutil.which('npm.cmd') or 'npm.cmd', '--prefix', 'frontend', 'run', 'build']),
        ('API package consistency', [str(API), '-m', 'pip', 'check']),
        ('ML package consistency', [str(ML), '-m', 'pip', 'check']),
    ]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def cached_model(directory):
    try:
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        entries=manifest['sha256']
        if not entries:return False
        for filename,digest in entries.items():
            path=(directory/filename).resolve()
            if path.parent!=directory.resolve():return False
            with path.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()!=digest:return False
        return True
    except (OSError,ValueError,KeyError):return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', help='Show setup stages without installing or downloading')
    args = parser.parse_args()
    stages = commands()
    if args.plan:
        for i,(label,_) in enumerate(stages,1): print(f'[{i}/{len(stages)}] {label}')
        return 0
    if os.name != 'nt' or platform.machine().lower() not in {'amd64','x86_64'}:
        raise RuntimeError('Automatic setup supports Windows x64. See TEAM-SETUP.md for prerequisites.')
    if sys.version_info[:2] != (3,12):
        raise RuntimeError('Use Python 3.12: py -3.12 -m apps.setup_local')
    if not shutil.which('npm.cmd') or not shutil.which('node'):
        raise RuntimeError('Install Node.js LTS, reopen the terminal and rerun Setup.cmd.')
    node = subprocess.check_output(['node','--version'],text=True).strip()
    if int(node.lstrip('v').split('.')[0]) < 20:
        raise RuntimeError('Node.js 20 or newer is required; Node 24 LTS is the tested version.')
    if not shutil.which('nvidia-smi'):
        raise RuntimeError('NVIDIA driver is missing. Install the official NVIDIA driver, reboot and retry.')
    run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'])
    if shutil.disk_usage(ROOT).free < 12*1024**3:
        raise RuntimeError('At least 12 GB free disk space is required. 20 GB free is recommended.')
    state_dir=ROOT/'work'/'runtime'/'setup';state_dir.mkdir(parents=True,exist_ok=True)
    # Success receipts are local and tied to their source inputs. Failed stages
    # never receive a receipt, so repeating setup resumes safely.
    for i,(label,command) in enumerate(stages,1):
        print(f'[{i}/{len(stages)}] {label}',flush=True)
        if label.endswith('environment'):
            target=API if label.startswith('API') else ML
            if not target.exists(): run(command)
            version=subprocess.check_output([str(target),'-c','import sys;print(".".join(map(str,sys.version_info[:2])))'],text=True).strip()
            if version!='3.12':raise RuntimeError(f'{target.parent.parent} uses Python {version}; recreate it with Python 3.12.')
            continue
        if i==7:
            artifact=ROOT/'apps/ml/training/indian_artifacts'
            try:
                metadata=json.loads((artifact/'metadata.json').read_text(encoding='utf-8'))
                digest=hashlib.sha256((ROOT/'apps/ml/data/indian_cues.jsonl').read_bytes()).hexdigest()
                if (artifact/'classifier.joblib').is_file() and metadata['metrics']['dataset_sha256']==digest:
                    run([str(ML),'-c','from apps.ml.training.indian import IndianClauseClassifier; IndianClauseClassifier()'])
                    print('  matching classifier already present; not retraining',flush=True);continue
            except (OSError,ValueError,KeyError):pass
        cached_dirs={8:['multilingual-e5-small'],9:['indic-en','en-indic']}.get(i)
        if cached_dirs and all(cached_model(ROOT/'apps/ml/models'/name) for name in cached_dirs):
            print('  local model hashes verified; no download needed',flush=True);continue
        if i==9:
            print('If access is denied: accept both AI4Bharat model gates in your own HF account, then run apps\\ml\\.venv\\Scripts\\hf.exe auth login and repeat setup. See TEAM-SETUP.md.',flush=True)
        inputs=[Path(__file__),ROOT/'apps/ml/requirements.lock.txt',ROOT/'apps/api/requirements.lock.txt',ROOT/'frontend/package-lock.json']
        signature=hashlib.sha256((' '.join(command)).encode()+b''.join(p.read_bytes() for p in inputs)).hexdigest()
        receipt=state_dir/f'{i}.json'
        # Installs may be skipped after success. Downloads/builds/checks are
        # rerun to restore deleted files and reverify assets, never just flags.
        # Recheck installed packages on every run. A deleted/recreated venv or
        # interrupted npm install must not be mistaken for a complete setup.
        run(command)
        receipt.write_text(json.dumps({'stage':label,'signature':signature}),encoding='utf-8')
    print('Setup complete. Run Start.cmd, then open http://127.0.0.1:8000/ .',flush=True)
    return 0


if __name__=='__main__':
    try: raise SystemExit(main())
    except (RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'SETUP INCOMPLETE: {exc}\nFix this stage and rerun Setup.cmd; never share your HF token.',file=sys.stderr)
        raise SystemExit(1)
