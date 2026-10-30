"""Real public acceptance checks over explicitly synthetic fixtures, not judge accuracy.

python -m apps.api.scripts.completion_smoke --language-matrix
All generated language/meaning remains unreviewed. Save synthetic evidence only.
"""
import argparse,io,json,time
from pathlib import Path
import httpx
from docx import Document

DOCUMENTS=[
 ("rent","agreement","en","en","The tenant must pay a penalty of INR 500 if rent is received more than 7 days after the due date. This agreement automatically renews for 12 months unless the tenant gives written notice at least 30 days before expiry.",{"payment_penalty","automatic_renewal"}),
 ("loan","agreement","en","en","The borrower waives the right to dispute collection charges. A penalty of INR 100 applies if the monthly payment is late.",{"payment_penalty","waived_rights"}),
 ("land","other","en","en","The seller must provide copies of the title documents within 15 days of signing this land agreement.",set()),
 ("notice","notice","en","en","Respond within 15 days of receipt of this notice. The notice alleges that a payment is outstanding.",set()),
 ("fir","fir","en","en","This fictional FIR records an allegation that a person took INR 1000 on 10 January 2026. The allegation has not been proven and does not establish guilt.",set()),
]
SOURCES={"en":"Respond within 15 days of receipt of this notice.","hi":"इस नोटिस की प्राप्ति के 15 दिनों के भीतर उत्तर दें।","pa":"ਇਸ ਨੋਟਿਸ ਦੀ ਪ੍ਰਾਪਤੀ ਤੋਂ 15 ਦਿਨਾਂ ਦੇ ਅੰਦਰ ਜਵਾਬ ਦਿਓ।"}
def run_case(client,case,folder):
 name,kind,source,target,text,expected=case
 document=Document();document.add_paragraph(text)
 stream=io.BytesIO();document.save(stream)
 response=client.post("/api/v1/documents",files={"file":(name+".docx",stream.getvalue(),"application/vnd.openxmlformats-officedocument.wordprocessingml.document")},data={"processing_consent":"true","input_language":source,"document_type":kind})
 response.raise_for_status();upload=response.json()
 headers={"X-Session-Token":upload["session_token"]};path="/api/v1/documents/"+upload["document_id"]
 began=time.monotonic();health=[];result=None;aid=None
 try:
  for _ in range(300):
   response=client.get(path,headers=headers);response.raise_for_status();meta=response.json()
   if meta["extraction_ready"]:break
   if meta["status"]=="failed":raise RuntimeError("extraction_failed")
   time.sleep(.2)
  else:raise RuntimeError("extraction_timeout")
  response=client.patch(path+"/extraction",headers=headers,json={"expected_revision":upload["revision"],"corrections":[],"input_language":source,"document_type":kind});response.raise_for_status()
  revision=response.json()["revision"]
  response=client.post(path+"/analyses",headers=headers,json={"expected_revision":revision,"output_language":target});response.raise_for_status();aid=response.json()["analysis_id"]
  deadline=time.monotonic()+300;previous=None
  while time.monotonic()<deadline:
   response=client.get(path+"/analyses/"+aid,headers=headers);response.raise_for_status();snapshot=response.json()
   progress=snapshot["progress"]
   state=(snapshot["status"],progress["completed_clauses"])
   if state!=previous:print("   ",name,f"{progress['completed_clauses']}/{progress['total_clauses']}",snapshot["status"],flush=True);previous=state
   if snapshot["status"] not in {"queued","running"}:break
   started=time.monotonic();probe=client.get("/api/v1/health");probe.raise_for_status();health.append((time.monotonic()-started)*1000)
   time.sleep(.5)
  else:raise RuntimeError("analysis_timeout")
  result=snapshot.get("result")
  if not result:raise RuntimeError("analysis_no_result")
  categories={item["category"] for item in result["items"] if item["kind"]=="attention"}
  response=client.get(path+"/analyses/"+aid+"/report",headers=headers);response.raise_for_status();report=response.json()
  assert report["analysis"]["analysis_id"]==aid and report["independent_review"]=="not_performed"
  assert upload["session_token"] not in json.dumps(report)
  for fmt in ("md","html"):
   output=client.get(path+"/analyses/"+aid+"/report?format="+fmt,headers=headers);output.raise_for_status()
   (folder/(name+"."+fmt)).write_bytes(output.content)
  from collections import Counter
  summaries=[i for i in result["items"] if i["kind"] in {"explanation","notice_action","allegation"}]
  text_output=" ".join(i["explanation"] for i in summaries)
  block=range(0x0900,0x0980) if target=="hi" else range(0x0A00,0x0A80)
  script_pass=any(ord(c) in block for c in text_output) if target!="en" else True
  record={"fixture":name,"input_language":source,"output_language":target,"coverage":result["coverage"],"status":snapshot["status"],"expected_cues":sorted(expected),"detected_cues":sorted(categories),"expected_cues_found":expected<=categories,"script_presence_check":script_pass,"health_polls":len(health),"health_max_ms":round(max(health,default=0),2),"seconds":round(time.monotonic()-began,2),"independent_meaning_review":"not_performed","fluent_review":"not_performed","result":result}
  record["technical_pass"]=result["coverage"]["analysed"]==result["coverage"]["total"] and expected<=categories and script_pass
  return record
 finally:
  deletion=client.delete(path,headers=headers);assert deletion.status_code==204
  assert client.get(path,headers=headers).status_code==404
  if aid:assert client.get(path+"/analyses/"+aid+"/report",headers=headers).status_code==404

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--language-matrix",action="store_true");parser.add_argument("--output",type=Path,default=Path("work/verification/completion"))
 args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 cases=list(DOCUMENTS)
 if args.language_matrix:
  cases += [(f"language-{source}-{target}","notice",source,target,text,set()) for source,text in SOURCES.items() for target in SOURCES]
 records=[]
 with httpx.Client(base_url="http://127.0.0.1:8000",timeout=310,trust_env=False) as client:
  assert client.get("/api/v1/health").json()["mode"]=="real"
  for number,case in enumerate(cases,1):
   print(f"[{number}/{len(cases)}] synthetic {case[0]}",flush=True)
   try:record=run_case(client,case,args.output)
   except Exception as error:record={"fixture":case[0],"technical_pass":False,"error_type":type(error).__name__}
   records.append(record)
   print("    technical_pass=",record["technical_pass"],"meaning/fluent review not performed",flush=True)
   (args.output/"results.json").write_text(json.dumps({"synthetic_only":True,"expert_review":False,"records":records},ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"Technical checks: {sum(r['technical_pass'] for r in records)}/{len(records)}. Not a legal or language accuracy score.",flush=True)
 raise SystemExit(0 if all(r["technical_pass"] for r in records) else 1)
if __name__=="__main__":main()

