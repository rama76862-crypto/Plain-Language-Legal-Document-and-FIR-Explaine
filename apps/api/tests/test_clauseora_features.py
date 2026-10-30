"""New feature contracts use real parsers and explicitly simulated ML only."""
from fastapi.testclient import TestClient
from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.tests.test_api import upload,wait_extraction,confirm,start,wait_analysis,pdf_bytes


def test_compare_requires_both_tokens_review_and_current_revisions(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',poll_interval_seconds=.005))
    with TestClient(app) as client:
        a,ah=upload(client,pdf_bytes('Tenant must pay INR 500 within 30 days.'))
        b,bh=upload(client,pdf_bytes('Tenant must pay INR 750 within 15 days.'))
        wait_extraction(client,a,ah);wait_extraction(client,b,bh)
        path=f"/api/v1/documents/{a['document_id']}/compare"
        body={'document_b_id':b['document_id'],'expected_revision_a':1,'expected_revision_b':1}
        assert client.post(path,headers=ah,json=body).status_code==404
        headers={**ah,'X-Compare-Session-Token':b['session_token']}
        assert client.post(path,headers=headers,json=body).status_code==409
        confirm(client,a,ah);confirm(client,b,bh)
        response=client.post(path,headers=headers,json=body)
        assert response.status_code==200,response.text
        changes=response.json()['changes'];assert len(changes)==1
        assert changes[0]['change_type']=='modified'
        assert '500' in changes[0]['before']['quote'] and '750' in changes[0]['after']['quote']
        assert changes[0]['before']['document_id']==a['document_id']
        assert changes[0]['after']['document_id']==b['document_id']
        confirm(client,b,bh,corrections=[{'clause_id':'c1','text':'Tenant must pay INR 900.'}])
        assert client.post(path,headers=headers,json=body).status_code==409
        client.delete(f"/api/v1/documents/{b['document_id']}",headers=bh)
        assert client.post(path,headers=headers,json=body).status_code==404


def test_action_pack_and_report_preserve_source_obligation(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',poll_interval_seconds=.005))
    with TestClient(app) as client:
        doc,headers=upload(client,pdf_bytes('The tenant must pay INR 500 within 15 days of receipt.'))
        wait_extraction(client,doc,headers);confirm(client,doc,headers)
        aid=start(client,doc,headers).json()['analysis_id'];wait_analysis(client,doc,headers,aid)
        base=f"/api/v1/documents/{doc['document_id']}/analyses/{aid}"
        assert client.get(base+'/action-pack').status_code==404
        response=client.get(base+'/action-pack',headers=headers)
        assert response.status_code==200,response.text
        value=response.json();assert 'INR 500' in value['checklist'][0]['statement']
        assert value['checklist'][0]['party']=='tenant'
        assert doc['session_token'] not in str(value)
        report=client.get(base+'/report',headers=headers).json()
        assert report['action_pack']['checklist']==value['checklist']


def test_hosted_processing_requires_separate_external_consent_before_storage(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',inference_mode='hosted'))
    with TestClient(app) as client:
        assert client.get('/api/v1/capabilities').json()['processing']['external_ai_inference'] is True
        response=client.post('/api/v1/documents',files={'file':('synthetic.pdf',pdf_bytes(),'application/pdf')},data={'processing_consent':'true'})
        assert response.status_code==422
        assert not app.state.store.records


def test_checklist_keeps_multiple_role_mentions_without_assigning_responsibility():
    from types import SimpleNamespace
    from apps.api.features import action_pack
    from apps.api.schemas import Clause,SourceRef
    source='The landlord must notify the tenant within 15 days.'
    record=SimpleNamespace(document_id='synthetic',revision=1,clauses=[Clause(clause_id='c1',source_text=source,reviewed_text=source,source_ref=SourceRef(paragraph_index=1))])
    pack=action_pack(record,{'analysis_id':'synthetic','result':{'output_language':'en'}})
    assert pack['checklist'][0]['party']=='landlord, tenant'
    assert pack['checklist'][0]['statement']==source
