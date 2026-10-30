"""Fetch approved gated translation artifacts at pinned revisions."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from huggingface_hub import snapshot_download

ROOT=Path(__file__).resolve().parents[3]
MODELS={
 "indic-en":("ai4bharat/indictrans2-indic-en-dist-200M","d66a2122ad6d28184f3dc3797b652bd80ae3f65f"),
 "en-indic":("ai4bharat/indictrans2-en-indic-dist-200M","2cfd0a20057756d756bf3e53528f492afc52f91a"),
}
def main():
    token_path=ROOT/"work"/"runtime"/"hf"/"token"
    token=token_path.read_text().strip() if token_path.exists() else None
    for name,(repo,revision) in MODELS.items():
        directory=ROOT/"apps"/"ml"/"models"/name
        print(f"Downloading approved {repo}",flush=True)
        snapshot_download(repo,revision=revision,local_dir=directory,cache_dir=ROOT/"apps"/"ml"/"cache"/"huggingface",token=token,allow_patterns=["*.json","*.py","model.safetensors","model.SRC","model.TGT","LICENSE"],max_workers=3)
        hashes={}
        for path in directory.iterdir():
            if path.is_file() and path.name!="manifest.json":
                with path.open("rb") as stream:
                    hashes[path.name]=hashlib.file_digest(stream,"sha256").hexdigest()
        (directory/"manifest.json").write_text(json.dumps({"repo":repo,"revision":revision,"sha256":hashes,"license":"MIT","remote_code":"Pinned official model implementation; inspect before loading"},indent=2),encoding="utf-8")
        print(f"{name}: pinned files and hashes saved",flush=True)

if __name__=="__main__":main()

