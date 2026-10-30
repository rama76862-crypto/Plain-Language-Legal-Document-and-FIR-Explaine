"""Bounded verifier transport and explicit-consent/caching regression checks."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api import verification
from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.tests.test_api import upload, wait_extraction, confirm, start, wait_analysis


@pytest.mark.parametrize('decoded_object',[False,True])
def test_selected_checker_masks_identifiers_and_rejects_missing_verdicts(monkeypatch,decoded_object):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'a' * 32)
    monkeypatch.setenv('CLOUDFLARE_AI_TOKEN', 'synthetic-test-token')
    original = httpx.AsyncClient
    received = []
    malformed = [False]

    def handler(request):
        body = json.loads(request.content)
        received.append(body)
        rows = json.loads(body['messages'][1]['content'])
        assert 'citizen@example.test' not in request.content.decode()
        assert all(row['item_id'].startswith('check_') and 'clause_id' not in row for row in rows)
        assert len(rows) == 6
        verdicts = [{'item_id': row['item_id'], 'verdict': 'unclear' if i==0 else 'supported'} for i,row in enumerate(rows)]
        if malformed[0]:
            verdicts.pop()
        value={'results': verdicts}
        return httpx.Response(200, json={'result': {'response': value if decoded_object else json.dumps(value)}})

    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    result = {'items': [{'item_id': f'i{n}', 'clause_id': f'c{n}', 'kind': 'explanation',
                         'explanation': 'Contact citizen@example.test.',
                         'evidence': [{'quote': 'Contact citizen@example.test.'}]} for n in range(9)]}
    checked = asyncio.run(verification.verify_selected(result))
    assert checked['status'] == 'needs_review'
    assert checked['checked_claims'] == 6 and checked['independent_review'] is False
    assert checked['issues'][0]['item_id']=='i0' and checked['issues'][0]['clause_id']=='c0'
    malformed[0] = True
    assert asyncio.run(verification.verify_selected(result))['status'] == 'unavailable'
    assert len(received) == 2


def test_source_check_consent_authorization_cache_and_report(tmp_path, monkeypatch):
    calls = []

    async def selected(result):
        calls.append(result)
        return {'status': 'cross_checked', 'provider': 'cloudflare', 'checked_claims': 1,
                'selected_claims': 1, 'issues': [], 'independent_review': False,
                'limitation': 'Selected source claims only.'}

    monkeypatch.setattr(verification, 'verify_selected', selected)
    app = create_app(Settings(runtime_dir=tmp_path / 'runtime', ml_mode='fixture', poll_interval_seconds=.005))
    with TestClient(app) as client:
        doc, headers = upload(client)
        wait_extraction(client, doc, headers)
        confirm(client, doc, headers)
        aid = start(client, doc, headers).json()['analysis_id']
        wait_analysis(client, doc, headers, aid)
        base = f"/api/v1/documents/{doc['document_id']}/analyses/{aid}"
        assert client.post(base + '/verify-source', headers=headers, json={}).status_code == 422
        assert client.post(base + '/verify-source', json={'external_ai_consent': True}).status_code == 404
        for _ in range(2):
            response = client.post(base + '/verify-source', headers=headers, json={'external_ai_consent': True})
            assert response.status_code == 200, response.text
        assert len(calls) == 1
        report = client.get(base + '/report', headers=headers).json()
        assert report['selected_source_verification']['checked_claims'] == 1
        client.delete(f"/api/v1/documents/{doc['document_id']}", headers=headers)
        assert client.post(base + '/verify-source', headers=headers, json={'external_ai_consent': True}).status_code == 404
        assert len(calls) == 1
