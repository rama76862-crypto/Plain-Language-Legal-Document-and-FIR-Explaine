"""Actual public API evaluation on synthetic development fixtures, never judge accuracy.

Run with .venv-api Python after Start.cmd. No external inference is used.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import time
import httpx
from docx import Document

ROOT=Path(__file__).resolve().parents[3]
FIXTURES=ROOT/'apps/ml/evaluation/fixtures'
DEFAULTS=['agreement_ordinary_en.json','agreement_attention_en.json','notice_en.json','fir_fictional_redacted_en.json','notice_hindi_hi.json']


def evaluate(client,filename):
    fixture=json.loads((FIXTURES/filename).read_text(encoding='utf-8'))
    if fixture.get('synthetic') is not True:raise ValueError('This command accepts synthetic fixtures only')
    document=Document()
    for clause in fixture['clauses']:document.add_paragraph(clause['reviewed_text'])
    stream=io.BytesIO();document.save(stream)
    response=client.post('/api/v1/documents',files={'file':('synthetic-evaluation.docx',stream.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},data={'processing_consent':'true','input_language':fixture['source_language'],'document_type':fixture['document_type']})
    response.raise_for_status();upload=response.json();headers={'X-Session-Token':upload['session_token']};path='/api/v1/documents/'+upload['document_id'];began=time.monotonic()
    try:
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            response=client.get(path,headers=headers);response.raise_for_status();meta=response.json()
            if meta['extraction_ready']:break
            if meta['status']=='failed':raise RuntimeError('extraction_failed')
            time.sleep(.3)
        else:raise TimeoutError('extraction_timeout')
        response=client.get(path+'/extraction',headers=headers);response.raise_for_status();extracted=response.json()['clauses']
        # Actual extraction must match every supplied paragraph before the
        # harness can truthfully confirm this synthetic source as reviewed.
        normalize=lambda text:' '.join(text.split())
        if [normalize(c['reviewed_text']) for c in extracted]!=[normalize(c['reviewed_text']) for c in fixture['clauses']]:
            raise ValueError('synthetic extraction differs from source; manual review needed')
        response=client.patch(path+'/extraction',headers=headers,json={'expected_revision':upload['revision'],'corrections':[],'input_language':fixture['source_language'],'document_type':fixture['document_type']});response.raise_for_status();revision=response.json()['revision']
        response=client.post(path+'/analyses',headers=headers,json={'expected_revision':revision,'output_language':fixture['output_language']});response.raise_for_status();aid=response.json()['analysis_id']
        deadline=time.monotonic()+600;previous=None
        while time.monotonic()<deadline:
            response=client.get(path+'/analyses/'+aid,headers=headers);response.raise_for_status();snapshot=response.json()
            state=(snapshot['status'],snapshot['progress']['completed_clauses'])
            if state!=previous:print(f"  {state[0]} {state[1]}/{len(extracted)}",flush=True);previous=state
            if state[0] not in {'queued','running'}:break
            time.sleep(.5)
        else:raise TimeoutError('analysis_timeout')
        result=snapshot.get('result')
        if not result:raise RuntimeError('analysis_has_no_result')
        rows=[]
        for source,clause in zip(fixture['clauses'],extracted):
            items=[i for i in result['items'] if i['clause_id']==clause['clause_id']]
            detected={i['category'] for i in items if i['kind']=='attention'}
            expected=set(source['expected']['attention_categories'])
            rows.append({'clause_id':clause['clause_id'],'source':clause['reviewed_text'],'expected_categories':sorted(expected),'detected_categories':sorted(detected),'missed':sorted(expected-detected),'additional_candidates_need_review':sorted(detected-expected),'items':items,'semantic_review':'pending independent review'})
        return {'fixture':filename,'synthetic':True,'seconds':round(time.monotonic()-began,2),'status':snapshot['status'],'coverage':result['coverage'],'failed_clauses':result.get('failed_clauses',[]),'missed_expected_categories':sum(len(r['missed']) for r in rows),'clauses':rows,'warnings':result.get('warnings',[]),'deadlines':result.get('deadlines',[]),'provenance':result.get('provenance',{})}
    finally:
        deletion=client.delete(path,headers=headers)
        if deletion.status_code!=204:raise RuntimeError('synthetic_session_cleanup_failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-punjabi',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'work/verification/five-development-documents.json')
    args=parser.parse_args();cases=DEFAULTS+(['notice_punjabi_pa.json'] if args.include_punjabi else [])
    records=[]
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=620,trust_env=False) as client:
        health=client.get('/api/v1/health');health.raise_for_status()
        if health.json().get('mode')!='real':raise RuntimeError('Real ML mode required')
        for index,name in enumerate(cases,1):
            print(f'[{index}/{len(cases)}] {name}',flush=True)
            try:record=evaluate(client,name)
            except Exception as error:record={'fixture':name,'error_type':type(error).__name__,'technical_failure':True}
            records.append(record)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps({'synthetic_development_fixtures':True,'judge_documents':False,'independent_review':False,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
    misses=sum(r.get('missed_expected_categories',0) for r in records)
    failures=sum(bool(r.get('technical_failure')) for r in records)
    print(f'Documents={len(records)}; request failures={failures}; missed expected cue assignments={misses}. No legal/fluent accuracy score is established.',flush=True)
    return int(bool(failures or misses))


if __name__=='__main__':raise SystemExit(main())
