"""Synthetic local HTTP journey. Never prints text, filenames or tokens."""
import argparse
import io
import time
from urllib.parse import urlparse
import httpx
import pymupdf
from docx import Document


def synthetic(kind):
    if kind=='pdf':
        doc=pymupdf.open(); doc.new_page().insert_text((50,80),'SYNTHETIC agreement. Payment is due within 15 days of receipt.')
        data=doc.tobytes(); doc.close(); return data,'application/pdf'
    doc=Document(); doc.add_paragraph('SYNTHETIC agreement. Payment is due within 15 days of receipt.')
    doc.add_table(rows=1,cols=1).cell(0,0).text='SYNTHETIC agreement table.'
    stream=io.BytesIO(); doc.save(stream)
    return stream.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def run(base,kind,mode,extraction_only=False):
    parsed=urlparse(base)
    if parsed.hostname not in {'localhost','127.0.0.1','::1'}:
        raise SystemExit('Smoke defaults to local loopback only. Use a local trusted proxy for teammate testing.')
    with httpx.Client(base_url=base.rstrip('/'),timeout=10,trust_env=False) as client:
        health=client.get('/api/v1/health'); health.raise_for_status(); h=health.json()
        if h['mode']!=mode:
            raise SystemExit('Server mode differs from explicit smoke expectation.')
        if mode=='real' and not h['ml']['available'] and not extraction_only:
            print('[--------] Real ML unavailable; extraction/review can be checked with --extraction-only.')
            return False
        data,mime=synthetic(kind)
        response=client.post('/api/v1/documents',files={'file':('synthetic.'+kind,data,mime)},data={'input_language':'en','document_type':'agreement'})
        response.raise_for_status(); upload=response.json(); headers={'X-Session-Token':upload['session_token']}
        path='/api/v1/documents/'+upload['document_id']
        print('[#-------] Upload accepted (synthetic fixture).')
        try:
            deadline=time.monotonic()+30
            while True:
                metadata=client.get(path,headers=headers); metadata.raise_for_status(); metadata=metadata.json()
                if metadata['status']=='failed': raise RuntimeError('Extraction failed; inspect safe metadata warnings.')
                if metadata['extraction_ready']: break
                if time.monotonic()>deadline: raise RuntimeError('Extraction smoke timeout')
                time.sleep(.1)
            extraction=client.get(path+'/extraction',headers=headers); extraction.raise_for_status()
            clauses=extraction.json()['clauses']; assert clauses
            assert all(c['source_ref']['page_number'] is None for c in clauses) if kind=='docx' else clauses[0]['source_ref']['page_number']==1
            print('[##------] Real native extraction and source references checked.')
            review=client.patch(path+'/extraction',headers=headers,json=dict(expected_revision=upload['revision'],corrections=[],input_language='en',document_type='agreement'))
            review.raise_for_status(); revision=review.json()['revision']
            assert review.json()['reviewed_revision']==revision
            print('[###-----] Explicit unchanged-text review confirmed.')
            source=client.get(path+'/source',headers=headers); source.raise_for_status(); assert source.content==data
            print('[####----] Authenticated original source checked.')
            if extraction_only:
                return True
            accepted=client.post(path+'/analyses',headers=headers,json=dict(expected_revision=revision,output_language='en'))
            accepted.raise_for_status(); aid=accepted.json()['analysis_id']
            print('[#####---] Analysis accepted; polling actual work counts.')
            deadline=time.monotonic()+180
            while True:
                response=client.get(path+'/analyses/'+aid,headers=headers); response.raise_for_status(); snapshot=response.json()
                progress=snapshot['progress']
                print(f"  clauses={progress['completed_clauses']}/{progress['total_clauses']} status={snapshot['status']}")
                if snapshot['status'] not in {'queued','running'}: break
                if time.monotonic()>deadline: raise RuntimeError('Analysis smoke timeout')
                time.sleep(.5)
            if snapshot['status']=='failed' or not snapshot.get('result'):
                raise RuntimeError('No usable analysis result; smoke failed honestly.')
            if mode=='fixture':
                assert snapshot['status']=='needs_review' and snapshot['result']['coverage']['analysed']==0
                assert 'DEVELOPMENT FIXTURE' in str(snapshot['warnings'])
            by_id={c['clause_id']:c['reviewed_text'] for c in clauses}
            for item in snapshot['result']['items']:
                for evidence in item['evidence']: assert evidence['quote'] in by_id[evidence['clause_id']]
            print('[######--] Validated result and source evidence checked.')
            answer=client.post(path+'/questions',headers=headers,json=dict(analysis_id=aid,question='What period is stated in the document?',output_language='en',client_request_id='smoke-once'))
            answer.raise_for_status()
            print('[#######-] Question interface checked.' + (' DEVELOPMENT SIMULATION ONLY.' if mode=='fixture' else ''))
        finally:
            deleted=client.delete(path,headers=headers); deleted.raise_for_status()
            if extraction_only:
                assert client.get(path,headers=headers).status_code==404
                print('[#####] 5/5 native extraction/review/source/delete checks passed. ML was not called.')
        assert client.get(path,headers=headers).status_code==404
        print('[########] 8/8 journey checks passed.' + (' Model/classifier/translation NOT tested.' if mode=='fixture' else ' Real-service journey; semantic quality still requires BE2 evaluation.'))
        return True


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--kind',choices=['pdf','docx'],default='pdf')
    parser.add_argument('--mode',choices=['real','fixture'],default='real')
    parser.add_argument('--extraction-only',action='store_true')
    args=parser.parse_args()
    raise SystemExit(0 if run(args.base_url,args.kind,args.mode,args.extraction_only) else 2)
