"""Local adapter contracts only: MockTransport never proves a real model works."""
import asyncio
from copy import deepcopy
import httpx
import pytest
from apps.api.config import Settings
from apps.api.schemas import ApiError
from apps.api.ml_client import RealMLClient, FixtureMLClient, validate_snapshot, validate_answer


def payload():
    return {'document_id':'doc_test','analysis_id':'a_test','document_revision':2,
        'input_language':'hi','output_language':'en','document_type':'notice',
        'clauses':[{'clause_id':'c1','reviewed_text':'प्राप्ति के 15 दिन के भीतर उत्तर दें।',
                    'source_ref':{'page_number':None,'paragraph_index':1,'bbox':None}}]}


def snapshot():
    request = payload()
    result = {key:request[key] for key in ('document_id','analysis_id','document_revision','input_language','output_language','document_type')}
    result.update(coverage={'analysed':1,'total':1},items=[{
        'item_id':'i1','clause_id':'c1','kind':'notice_action','category':None,
        'explanation':'Synthetic fixture: the notice requests a response.',
        'evidence':[{'clause_id':'c1','quote':'15 दिन'}], 'reference_ids':[],
        'review_status':'supported','detector':'rule','model_score':None,'limitations':[]}],
        deadlines=[{'deadline_id':'d1','clause_id':'c1','source_quote':'15 दिन',
            'display_text':'15 days after receipt','anchor':'receipt','resolved_date':None,
            'status':'needs_information','missing_information':['receipt_date']}],
        warnings=[], legal_aid=[{'title':'NALSA','url':'https://nalsa.gov.in/legal-aid/'}],
        provenance={'classifier_version':'synthetic','generator':'mock-http','rules_version':'v1'})
    return {'analysis_id':'a_test','document_revision':2,'output_language':'en','status':'complete',
        'progress':{'completed_clauses':1,'total_clauses':1,'stage':'validated'},'result':result,'warnings':[]}


def run(coroutine):
    return asyncio.run(coroutine)


def test_valid_original_language_evidence_deadline_optional_progress_preserved():
    data = snapshot()
    data['result']['translation'] = {'assisted':True,'model':'synthetic'}
    validated = validate_snapshot(data,payload())
    assert validated['progress']['stage'] == 'validated'
    assert validated['result']['translation']['assisted'] is True
    assert validated['result']['deadlines'][0]['resolved_date'] is None


@pytest.mark.parametrize('change', [
    lambda x:x.update(analysis_id='another'),
    lambda x:x.update(document_revision=1),
    lambda x:x.update(output_language='pa'),
    lambda x:x['progress'].update(completed_clauses=2),
    lambda x:x['progress'].update(total_clauses=2),
    lambda x:x['result'].update(document_id='another'),
    lambda x:x['result']['items'][0].update(clause_id='missing'),
    lambda x:x['result']['items'][0]['evidence'][0].update(quote='invented'),
    lambda x:x['result']['items'][0].update(reference_ids=['not_supplied']),
    lambda x:x['result']['coverage'].update(analysed=2),
    lambda x:x['result']['deadlines'][0].update(source_quote='invented'),
    lambda x:x['result']['deadlines'][0].update(resolved_date='2030-01-01'),
    lambda x:x['result']['legal_aid'][0].update(url='https://unreviewed.example'),
    lambda x:x.update(failed_clauses=['missing']),
    lambda x:x.update(failed_clauses=['c1']),
])
def test_invalid_model_output_rejected_without_sensitive_message(change):
    data = snapshot()
    change(data)
    with pytest.raises(ApiError) as error:
        validate_snapshot(data,payload())
    assert error.value.code == 'INVALID_MODEL_OUTPUT'
    assert 'प्राप्ति' not in error.value.message


def test_partial_result_coverage_warnings_and_failed_ids_survive():
    data = snapshot()
    request = payload()
    request['clauses'].append({'clause_id':'c2','reviewed_text':'Another synthetic clause.'})
    data.update(status='needs_review',failed_clauses=[{'clause_id':'c2','reason':'translation'}])
    data['progress'].update(completed_clauses=2,total_clauses=2)
    data['result']['coverage']['total'] = 2
    data['result']['warnings'] = ['Translation failed for c2.']
    validated = validate_snapshot(data,request)
    assert validated['failed_clauses'][0]['clause_id'] == 'c2'
    assert validated['result']['coverage'] == {'analysed':1,'total':2}


def test_terminal_missing_clauses_require_exact_failed_ids_not_only_warnings():
    data = snapshot()
    request = payload()
    request['clauses'].extend([{'clause_id':'c2','reviewed_text':'Synthetic two.'},
                              {'clause_id':'c3','reviewed_text':'Synthetic three.'}])
    data.update(status='needs_review',warnings=['A generic partial warning.'])
    data['progress'].update(completed_clauses=3,total_clauses=3)
    data['result']['coverage']['total'] = 3
    for failed in ([], ['c2']):
        data['failed_clauses'] = failed
        with pytest.raises(ApiError):
            validate_snapshot(data,request)
    data['failed_clauses'] = ['c2','c3']
    assert validate_snapshot(data,request)['status'] == 'needs_review'


def test_failed_supported_overlap_and_inconsistent_count_rejected():
    data = snapshot()
    data.update(status='needs_review',failed_clauses=['c1'])
    data['result']['coverage']['analysed'] = 0
    with pytest.raises(ApiError):
        validate_snapshot(data,payload())
    data['result']['items'][0]['review_status'] = 'needs_review'
    assert validate_snapshot(data,payload())['result']['coverage']['analysed'] == 0
    data['result']['coverage']['analysed'] = 1
    with pytest.raises(ApiError):
        validate_snapshot(data,payload())


def test_needs_review_without_content_accounts_for_all_clauses():
    data = snapshot()
    data.update(status='needs_review',result=None,warnings=['No reliable translation.'])
    with pytest.raises(ApiError):
        validate_snapshot(data,payload())
    data['failed_clauses'] = ['c1']
    assert validate_snapshot(data,payload())['result'] is None


def test_question_rejects_stale_analysis_result():
    answer = {'answer':'Synthetic answer','evidence':[],
        'reference_ids':[],'review_status':'needs_review','limitations':['Insufficient evidence.']}
    result = snapshot()['result']
    result['document_revision'] = 1
    with pytest.raises(ApiError):
        validate_answer(answer,payload(),result)


def test_complete_must_not_hide_needs_review_items():
    data = snapshot()
    data['result']['items'][0]['review_status'] = 'needs_review'
    with pytest.raises(ApiError):
        validate_snapshot(data,payload())


def test_question_evidence_and_reference_scope():
    answer = {'answer':'Synthetic answer','evidence':[{'clause_id':'c1','quote':'15 दिन'}],
        'reference_ids':[],'review_status':'supported','limitations':[]}
    assert validate_answer(answer,payload(),snapshot()['result'])['answer'] == 'Synthetic answer'
    answer['reference_ids'] = ['invented']
    with pytest.raises(ApiError):
        validate_answer(answer,payload(),snapshot()['result'])
    answer.update(reference_ids=[],evidence=[],review_status='needs_review',limitations=['Insufficient evidence.'])
    assert validate_answer(answer,payload(),snapshot()['result'])['review_status'] == 'needs_review'


def test_private_http_paths_payload_auth_and_delete():
    async def scenario():
        requests = []
        def handler(request):
            requests.append(request)
            assert request.headers['X-ML-Service-Token'] == 'synthetic-service-token'
            if request.url.path == '/internal/analyse':
                return httpx.Response(202,json={'analysis_id':'a_test','status':'queued'})
            if request.method == 'DELETE':
                return httpx.Response(204)
            if request.url.path == '/internal/question':
                return httpx.Response(200,json={'answer':'test'})
            return httpx.Response(200,json=snapshot())
        client = RealMLClient(Settings(ml_service_token='synthetic-service-token'),httpx.MockTransport(handler))
        assert (await client.start(payload()))['status'] == 'queued'
        assert (await client.poll('a_test'))['status'] == 'complete'
        await client.question({**payload(),'question':'Synthetic question','client_request_id':'retry1'})
        await client.delete('a_test')
        await client.close()
        assert len(requests) == 4
        assert all('session_token' not in request.content.decode() for request in requests)
    run(scenario())


@pytest.mark.parametrize('fields',[{'document_revision':1},{'warnings':'private string'},{'warnings':[{'private':'content'}]}])
def test_private_start_rejects_identity_and_warning_schema(fields):
    async def scenario():
        client = RealMLClient(Settings(),httpx.MockTransport(lambda request:httpx.Response(202,json={
            'analysis_id':'a_test','status':'queued',**fields})))
        with pytest.raises(ApiError) as error:
            await client.start(payload())
        assert error.value.code == 'INVALID_MODEL_OUTPUT'
        await client.close()
    run(scenario())


@pytest.mark.parametrize(('status','code'),[(429,'MODEL_BUSY'),(503,'MODEL_UNAVAILABLE'),(504,'MODEL_TIMEOUT'),(404,'NOT_FOUND'),(409,'ANALYSIS_NOT_READY'),(500,'INVALID_MODEL_OUTPUT')])
def test_private_error_mapping_does_not_leak_upstream_text(status,code):
    async def scenario():
        client = RealMLClient(Settings(),httpx.MockTransport(lambda request:httpx.Response(status,json={'error':{'message':'PRIVATE-CONTENT'}})))
        with pytest.raises(ApiError) as error:
            await client.poll('a_test')
        assert error.value.code == code
        assert 'PRIVATE-CONTENT' not in error.value.message
        await client.close()
    run(scenario())


def test_timeout_and_connection_failure_are_finite_and_not_fixture_fallback():
    async def scenario():
        calls = 0
        def handler(request):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise httpx.ReadTimeout('sensitive upstream diagnostic',request=request)
            if calls == 2:
                raise httpx.ConnectError('refused',request=request)
            return httpx.Response(200,json={'classifier_loaded':True,'generator_loaded':True})
        client = RealMLClient(Settings(model_timeout_seconds=0.1),httpx.MockTransport(handler))
        with pytest.raises(ApiError) as error:
            await client.poll('a_test')
        assert error.value.code == 'MODEL_TIMEOUT'
        with pytest.raises(ApiError) as error:
            await client.start(payload())
        assert error.value.code == 'MODEL_UNAVAILABLE'
        assert (await client.health())['mode'] == 'real'
        await client.close()
    run(scenario())


def test_readiness_accepts_backend2_ready_field_names_without_inventing_language_review():
    async def scenario():
        client = RealMLClient(Settings(), httpx.MockTransport(lambda request: httpx.Response(
            200, json={'classifier_ready': True, 'generator_ready': True,
                       'tested_languages': {'en': False, 'hi': False, 'pa': False}})))
        health = await client.health()
        assert health['available'] is True
        assert health['classifier_loaded'] is True
        assert health['generator_loaded'] is True
        assert health['tested_language_matrix'] == []
        await client.close()
    run(scenario())


def test_readiness_missing_evidence_not_ready_and_malformed_json_rejected():
    async def scenario():
        client = RealMLClient(Settings(),httpx.MockTransport(lambda request:httpx.Response(200,json={'status':'ok'})))
        health = await client.health()
        assert health['available'] is False
        assert health['tested_language_matrix'] == []
        await client.close()
        client = RealMLClient(Settings(),httpx.MockTransport(lambda request:httpx.Response(200,text='not json')))
        with pytest.raises(ApiError) as error:
            await client.poll('a_test')
        assert error.value.code == 'INVALID_MODEL_OUTPUT'
        await client.close()
    run(scenario())


def test_fixture_explicit_and_labelled_and_deleted():
    with pytest.raises(ValueError):
        FixtureMLClient(Settings())
    async def scenario():
        client = FixtureMLClient(Settings(ml_mode='fixture'))
        assert (await client.health())['simulation'] is True
        assert (await client.start(payload()))['status'] == 'queued'
        first = validate_snapshot(await client.poll('a_test'),payload())
        assert first['status'] == 'running'
        final = validate_snapshot(await client.poll('a_test'),payload())
        assert final['status'] == 'needs_review'
        assert 'DEVELOPMENT FIXTURE' in final['warnings'][0]
        assert final['result']['provenance']['classifier_version'] == 'not-run'
        assert final['result']['coverage']['analysed'] == 0
        assert final['progress']['stage'] == 'development_fixture_echo'
        assert final['failed_clauses'][0]['reason'] == 'development_fixture_no_model_analysis'
        answer = validate_answer(await client.question(payload()),payload(),final['result'])
        assert answer['review_status'] == 'needs_review'
        await client.delete('a_test')
        with pytest.raises(ApiError):
            await client.poll('a_test')
        await client.close()
    run(scenario())
