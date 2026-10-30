"""Pinned local IndicTrans2 adapter with Python preprocessing and no network.

The native IndicTransToolkit wheel is optional. The portable path uses
indic-nlp-library normalization/transliteration and sacremoses tokenization.
Its translations must be evaluated; this is not a claim of toolkit equivalence.
"""
from __future__ import annotations
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import threading
import unicodedata
from apps.ml.service.contracts import ClauseInput, TranslationResult
from .local_translator import assess_protected_text, _checks_from_assessment

ROOT=Path(__file__).resolve().parents[3]
TAGS={"en":"eng_Latn","hi":"hin_Deva","pa":"pan_Guru"}

def normalize_decimal_digits(text):
    """Use equivalent ASCII digits in the working copy; retain original evidence."""
    return ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)

class IndicTranslator:
    def __init__(self):
        self.models={}
        self.lock=threading.RLock()
        self.model_version="IndicTrans2-distilled-local; portable-preprocessing-v1"
        self.model_name="IndicTrans2-distilled-local"

    def available(self):
        return all((ROOT/"apps"/"ml"/"models"/name/"manifest.json").is_file() for name in ("indic-en","en-indic")) and importlib.util.find_spec("transformers") is not None

    def _load(self, direction):
        if direction in self.models:
            return self.models[direction]
        os.environ.setdefault("HF_MODULES_CACHE",str(ROOT/"apps"/"ml"/"cache"/"modules"))
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
        from sacremoses import MosesTokenizer, MosesDetokenizer
        torch.set_num_threads(2)
        directory=ROOT/"apps"/"ml"/"models"/direction
        manifest=json.loads((directory/"manifest.json").read_text())
        for filename,digest in manifest["sha256"].items():
            path=(directory/filename).resolve()
            if path.parent != directory.resolve():
                raise ValueError("Invalid translation artifact path")
            with path.open("rb") as stream:
                if hashlib.file_digest(stream,"sha256").hexdigest()!=digest:
                    raise ValueError("Translation artifact hash mismatch")
        tokenizer=AutoTokenizer.from_pretrained(str(directory),trust_remote_code=True,local_files_only=True)
        model=AutoModelForSeq2SeqLM.from_pretrained(str(directory),trust_remote_code=True,local_files_only=True,attn_implementation="eager").eval()
        value=(model,tokenizer,IndicNormalizerFactory(),MosesTokenizer(lang="en"),MosesDetokenizer(lang="en"))
        self.models[direction]=value
        return value

    @staticmethod
    def _preprocess(text, source, target, factory, english_tokenizer):
        from indicnlp.tokenize import indic_tokenize
        from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
        if source=="en":
            text=" ".join(english_tokenizer.tokenize(text,escape=False))
        else:
            text=factory.get_normalizer(source).normalize(text)
            if source=="pa":
                text=UnicodeIndicTransliterator.transliterate(text,"pa","hi")
            text=" ".join(indic_tokenize.trivial_tokenize(text,lang="hi"))
        return TAGS[source]+" "+TAGS[target]+" "+text

    def translate_many(self, texts: list[str], source: str, target: str) -> list[str]:
        if source==target:return list(texts)
        if source!="en" and target!="en":
            return self.translate_many(self.translate_many(texts,source,"en"),"en",target)
        if source not in TAGS or target not in TAGS:
            raise ValueError("Unsupported translation language")
        direction="en-indic" if source=="en" else "indic-en"
        import torch
        from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
        with self.lock:
            model,tokenizer,factory,en_tokenizer,en_detokenizer=self._load(direction)
            chunks,owners=[],[]
            for owner,text in enumerate(texts):
                text=normalize_decimal_digits(text)
                rest=text.strip()
                while rest:
                    lo,hi=1,len(rest)
                    while lo<hi:
                        mid=(lo+hi+1)//2
                        prepared=self._preprocess(rest[:mid],source,target,factory,en_tokenizer)
                        if len(tokenizer(prepared)["input_ids"])<=220:lo=mid
                        else:hi=mid-1
                    end=lo
                    if end<len(rest):
                        boundary=rest.rfind(" ",0,end)
                        if boundary>max(1,end//2):end=boundary
                    part=rest[:end].strip()
                    if not part:raise ValueError("Translation segmentation failed")
                    chunks.append(self._preprocess(part,source,target,factory,en_tokenizer));owners.append(owner)
                    rest=rest[end:].strip()
            grouped=[[] for _ in texts]
            for start in range(0,len(chunks),4):
                inputs=tokenizer(chunks[start:start+4],return_tensors="pt",padding=True,truncation=False)
                if inputs["input_ids"].shape[1]>256:
                    raise ValueError("Translation input exceeds model context")
                with torch.inference_mode():
                    outputs=model.generate(**inputs,max_new_tokens=256,num_beams=2,do_sample=False)
                for offset,(tokens,decoded) in enumerate(zip(outputs,tokenizer.batch_decode(outputs,skip_special_tokens=True,clean_up_tokenization_spaces=False))):
                    if tokenizer.eos_token_id not in tokens[1:].tolist():
                        raise ValueError("Translation output may be truncated")
                    if target=="pa":
                        decoded=UnicodeIndicTransliterator.transliterate(decoded,"hi","pa")
                    elif target=="en":
                        decoded=en_detokenizer.detokenize(decoded.split())
                    grouped[owners[start+offset]].append(decoded.strip())
            return [" ".join(parts) for parts in grouped]

    async def translate(self, clause: ClauseInput, source_language: str) -> TranslationResult:
        original=clause.reviewed_text
        if source_language=="en":
            return TranslationResult(clause_id=clause.clause_id,original_text=original,source_language="en",pivot_text=original,model="identity",review_status="supported",automated_checks_passed=True)
        try:
            pivot=(await asyncio.to_thread(self.translate_many,[original],source_language,"en"))[0]
            assessment=assess_protected_text(original,pivot,source_language,"en")
            passed=all(assessment.get(k)=="preserved" for k in ("numbers","legal_codes","negation","allegation"))
            return TranslationResult(clause_id=clause.clause_id,original_text=original,source_language=source_language,pivot_text=pivot if passed else None,model=self.model_name,version=self.model_version,review_status="needs_review",automated_checks_passed=passed,checks=[*_checks_from_assessment(assessment),"portable_preprocessing_needs_evaluation","fluent_review_missing"])
        except (ValueError,RuntimeError,ImportError,OSError):
            return TranslationResult(clause_id=clause.clause_id,original_text=original,source_language=source_language,pivot_text=None,model=self.model_name,review_status="needs_review",checks=["dedicated_translation_failed"])

