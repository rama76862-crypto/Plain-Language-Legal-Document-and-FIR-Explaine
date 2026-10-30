"""Publish synthetic examples; never consumes uploaded documents."""
import json
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[3]

def examples():
    clauses = [dict(clause_id=f'c{i}',source_text=text,reviewed_text=text,
                    source_ref=dict(page_number=None,paragraph_index=i,bbox=None),
                    extraction_method='docx',review_required=i==4)
               for i,text in enumerate(['Payment is due on 30 November 2026.',
                    'This agreement renews automatically.',
                    'शिकायतकर्ता ने घटना का आरोप लगाया।',
                    'Respond within 15 days of receipt.'],1)]
    items=[]
    for i,kind in enumerate(['explanation','attention','allegation','notice_action']):
        c=clauses[i]
        items.append(dict(item_id=f'i{i+1}',clause_id=c['clause_id'],kind=kind,
            category='automatic_renewal' if kind=='attention' else None,
            explanation='SYNTHETIC UI EXAMPLE — not a model finding.',
            evidence=[dict(clause_id=c['clause_id'],quote=c['reviewed_text'])],
            reference_ids=[],review_status='supported',detector='fixture',model_score=None,
            limitations=['Development example only.']))
    result=dict(document_id='doc_example',analysis_id='a_example',document_revision=1,
        input_language='hi',output_language='en',document_type='other',coverage=dict(analysed=4,total=4),
        items=items,deadlines=[dict(deadline_id='d1',clause_id='c4',source_quote=clauses[3]['reviewed_text'],
        display_text='15 days after receipt',anchor='receipt',resolved_date=None,status='needs_information',missing_information=['receipt_date'])],
        warnings=['SYNTHETIC DEVELOPMENT EXAMPLE','Mixed-language extraction requires review.'],
        legal_aid=[dict(title='NALSA legal aid',url='https://nalsa.gov.in/legal-aid/')],
        provenance=dict(classifier_version='not-run-fixture',generator='development-fixture',rules_version='not-run'),
        references=[])
    metadata=dict(document_id='doc_example',status='awaiting_review',revision=1,filename='synthetic-example.docx',
        document_type='other',input_language='unknown',warnings=['Confirm language/type and review extraction.'],
        extraction_ready=True,reviewed_revision=None,expires_at='2026-10-30T12:30:00Z',progress=dict(stage='extracting',completed_paragraphs=4,total_paragraphs=4))
    snapshots={}
    for status in ['queued','running','complete','needs_review','failed']:
        snapshots[status]=dict(analysis_id='a_example',document_revision=1,output_language='en',status=status,
            progress=dict(completed_clauses=4 if status in ['complete','needs_review'] else 0,total_clauses=4),
            result=deepcopy(result) if status in ['complete','needs_review'] else None,warnings=['SYNTHETIC DEVELOPMENT EXAMPLE'])
    partial=deepcopy(snapshots['running']); partial['progress']['completed_clauses']=2
    partial['result']=deepcopy(result); partial['result']['coverage']['analysed']=2; partial['result']['items']=items[:2]
    snapshots['partial']=partial
    snapshots['needs_review']['result']['coverage']['analysed']=3
    snapshots['needs_review']['result']['items']=items[:3]
    snapshots['needs_review']['result']['failed_clauses']=['c4']
    snapshots['needs_review']['progress'].update(completed_clauses=4,failed_clauses=1)
    errors={code:dict(error=dict(code=code,message=message,retryable=retryable),request_id='req_example')
        for code,message,retryable in [('REVISION_CONFLICT','Reload the current revision.',False),
        ('MODEL_BUSY','Local model queue is full; retry explicitly.',True),('MODEL_UNAVAILABLE','Local ML service unavailable.',True),
        ('MODEL_TIMEOUT','Local model timed out.',True),('UNSUPPORTED_LANGUAGE','Language path is unverified or unsupported.',False),
        ('VALIDATION_ERROR','Request fields are invalid.',False),
        ('EXTRACTION_TIMEOUT','Local extraction exceeded its time limit; use a shorter document.',True)]}
    return dict(fixture_notice='SYNTHETIC DEVELOPMENT EXAMPLES — not model results',
        upload_accepted=dict(document_id='doc_example',session_token='EXAMPLE_ONLY_NOT_A_REAL_TOKEN',status='extracting',revision=1),
        document_metadata=metadata,extraction_awaiting_review=dict(document_id='doc_example',revision=1,reviewed_revision=None,clauses=clauses,warnings=metadata['warnings'],input_language='unknown',document_type='other',progress=metadata['progress']),
        reviewed_patch_response=dict(document_id='doc_example',revision=1,reviewed_revision=1,status='awaiting_review',changed=False),
        analysis_accepted=dict(analysis_id='a_example',status='queued',document_revision=1),analysis_snapshots=snapshots,
        grounded_answer=dict(answer='SYNTHETIC EXAMPLE: the source states a relative period.',evidence=[dict(clause_id='c4',quote=clauses[3]['reviewed_text'])],reference_ids=[],review_status='supported',limitations=['Receipt date unknown.','Development example.']),
        insufficient_evidence_answer=dict(answer='Insufficient evidence in this document.',evidence=[],reference_ids=[],review_status='needs_review',limitations=['Development example; no legal advice.']),
        health=dict(status='degraded',mode='real',extraction=dict(ready=True,pdf=True,docx=True,ocr=dict(available=False,languages=[]),isolation=dict(mode='subprocess',timeout_seconds=120,memory_mb=768)),ml=dict(available=False,classifier_ready=None,generator_ready=None,language_paths=[]),cleanup=dict(pending=0,exhausted=0,local=dict(pending=0,exhausted=0))),
        optional_reference_example=dict(reference_id='ref_example',title='NALSA official legal-aid information',url='https://nalsa.gov.in/legal-aid/',section=None,version='example-metadata-only',excerpt='SYNTHETIC reference display example; not a fetched quotation.'),errors=errors)

if __name__ == '__main__':
    target=ROOT/'contracts'/'v1-examples.json'
    target.write_text(json.dumps(examples(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Published labelled contract examples.')
