"""Download pinned public model assets, never upload document data."""
from __future__ import annotations
import hashlib
import json
import shutil
from huggingface_hub import hf_hub_download
from .embeddings import MODEL_DIR, MODEL_REPO, MODEL_REVISION

def main():
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    hashes = {}
    for remote, local in (("onnx/model.onnx","model.onnx"),("tokenizer.json","tokenizer.json")):
        print(f"Downloading {remote}",flush=True)
        path = hf_hub_download(MODEL_REPO, remote, revision=MODEL_REVISION, cache_dir=MODEL_DIR.parent.parent / "cache" / "huggingface")
        destination = MODEL_DIR / local
        shutil.copyfile(path,destination)
        with destination.open("rb") as source:
            hashes[local] = hashlib.file_digest(source,"sha256").hexdigest()
    (MODEL_DIR/"manifest.json").write_text(json.dumps({"repo":MODEL_REPO,"revision":MODEL_REVISION,"sha256":hashes,"license":"MIT","use":"local CPU retrieval; not legal correctness"},indent=2),encoding="utf-8")
    print("Embedding assets ready; no inference API used.",flush=True)

if __name__ == "__main__":
    main()

