"""Offline CPU E5 embeddings. No hosted inference and no document disk cache."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import threading
import numpy as np

MODEL_REPO = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "multilingual-e5-small"
_DEFAULT = None
_LOCK = threading.Lock()

class LocalEncoder:
    def __init__(self, directory: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("revision") != MODEL_REVISION:
            raise ValueError("embedding revision mismatch")
        for name, expected in manifest["sha256"].items():
            if name not in {"model.onnx", "tokenizer.json"}:
                raise ValueError("unexpected embedding artifact")
            with (directory / name).open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                    raise ValueError("embedding artifact hash mismatch")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(directory / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
        self.lock = threading.Lock()

    def encode(self, texts: list[str], *, query: bool = False) -> np.ndarray:
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        matrices = []
        prefix = "query: " if query else "passage: "
        with self.lock:
            for start in range(0, len(texts), 8):
                batch = self.tokenizer.encode_batch([prefix + t for t in texts[start:start+8]])
                chunks,owners=[],[]
                for owner,encoded in enumerate(batch):
                    for chunk in [encoded,*encoded.overflowing]:
                        chunks.append(chunk)
                        owners.append(owner)
                vectors=[]
                for offset in range(0,len(chunks),8):
                    part=chunks[offset:offset+8]
                    width=max(len(x.ids) for x in part)
                    ids=np.full((len(part),width),1,dtype=np.int64)
                    mask=np.zeros_like(ids)
                    for row,encoded in enumerate(part):
                        ids[row,:len(encoded.ids)]=encoded.ids
                        mask[row,:len(encoded.attention_mask)]=encoded.attention_mask
                    inputs={"input_ids":ids,"attention_mask":mask}
                    names={x.name for x in self.session.get_inputs()}
                    if "token_type_ids" in names: inputs["token_type_ids"]=np.zeros_like(ids)
                    output=self.session.run(None,{k:v for k,v in inputs.items() if k in names})[0]
                    if output.ndim==3:
                        output=(output*mask[...,None]).sum(axis=1)/np.clip(mask.sum(axis=1,keepdims=True),1,None)
                    vectors.extend(output)
                # Include every overflow window instead of silently losing the
                # end of long clauses. The public interface stays one vector/text.
                vectors=np.asarray(vectors)
                output=np.asarray([vectors[np.asarray(owners)==i].mean(axis=0) for i in range(len(batch))])
                output=output/np.clip(np.linalg.norm(output,axis=1,keepdims=True),1e-12,None)
                matrices.append(output.astype(np.float32))
        return np.concatenate(matrices)

def get_encoder() -> LocalEncoder | None:
    global _DEFAULT
    if os.environ.get("ML_EMBEDDINGS", "auto") == "off":
        return None
    directory = Path(os.environ.get("ML_EMBEDDING_DIR", str(MODEL_DIR)))
    if not (directory / "manifest.json").is_file():
        return None
    with _LOCK:
        if _DEFAULT is None:
            _DEFAULT = LocalEncoder(directory)
    return _DEFAULT

