"""Recheck existing short official excerpts; never invent verification metadata."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from datetime import date

ROOT=Path(__file__).resolve().parents[3]
MANIFEST=ROOT/"apps"/"ml"/"data"/"references.json"

def main():
    import pymupdf
    entries=json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache,report={},[]
    for entry in entries:
        record,provenance=entry["record"],entry["provenance"]
        url=record["url"]
        if url not in cache:
            print("Rechecking official source:",urlsplit(url).hostname,flush=True)
            try:
                with urlopen(Request(url,headers={"User-Agent":"NyayaLens-reference-recheck"}),timeout=20) as response:
                    host=urlsplit(response.url).hostname or ""
                    if not host.endswith((".gov.in",".nic.in")):raise ValueError("Non-official redirect")
                    raw=response.read(20*1024*1024+1)
                    if len(raw)>20*1024*1024:raise ValueError("Reference exceeds download budget")
                if raw.startswith(b"%PDF"):
                    with pymupdf.open(stream=raw,filetype="pdf") as document:
                        content=" ".join(page.get_text() for page in document)
                else:
                    content=re.sub(r"<[^>]+>"," ",raw.decode("utf-8",errors="replace"))
                cache[url]=(" ".join(content.split()),None)
            except Exception as exc:
                cache[url]=("",type(exc).__name__)
        content,error=cache[url]
        matched=" ".join(record["excerpt"].split()) in content
        provenance["verification_status"]="verified" if matched and not error else "needs_direct_source_recheck"
        # These existing entries are brief, attributed excerpts. This does not
        # licence bulk reproduction of the source or assert legal applicability.
        provenance["reuse_status"]="short_attributed_excerpt_reviewed" if matched and provenance.get("reuse_note") else "needs_review"
        provenance["automated_recheck_date"]=date.today().isoformat()
        provenance["automated_recheck_method"]="Exact normalized excerpt match against the retrieved official source; no applicability assessment."
        report.append({"reference_id":record["reference_id"],"matched":matched,"error":error,"status":provenance["verification_status"]})
        print(record["reference_id"],provenance["verification_status"],flush=True)
    MANIFEST.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    output=ROOT/"work"/"verification"/"reference-verification.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
if __name__=="__main__":main()

