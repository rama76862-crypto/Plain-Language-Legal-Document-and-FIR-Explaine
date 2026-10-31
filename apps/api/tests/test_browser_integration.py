"""Browser transport checks for separately hosted frontend/API origins."""
from fastapi.testclient import TestClient

from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.tests.test_api import upload, wait_extraction
import time


def test_compare_cors_allows_both_session_tokens_only_for_configured_origin(tmp_path):
    app = create_app(Settings(runtime_dir=tmp_path / 'runtime', ml_mode='fixture'))
    with TestClient(app) as client:
        headers = {
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,x-session-token,x-compare-session-token',
        }
        response = client.options('/api/v1/documents/synthetic/compare', headers=headers)
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == headers['Origin']
        assert 'x-compare-session-token' in response.headers['access-control-allow-headers'].lower()
        rejected = client.options('/api/v1/documents/synthetic/compare', headers={
            **headers, 'Origin': 'https://unconfigured.example',
        })
        assert rejected.status_code == 400
        assert 'access-control-allow-origin' not in rejected.headers


def test_explicit_keep_alive_extends_retention_without_polling_or_reviving_expired_session(tmp_path):
    app = create_app(Settings(runtime_dir=tmp_path / 'runtime', ml_mode='fixture'))
    with TestClient(app) as client:
        doc, headers = upload(client)
        wait_extraction(client, doc, headers)
        path = f"/api/v1/documents/{doc['document_id']}"
        record = app.state.store.records[doc['document_id']]
        record.expires_at = time.time() + 60
        old_expiry = record.expires_at
        assert client.get(path, headers=headers).status_code == 200
        assert record.expires_at == old_expiry
        assert client.post(path + '/keep-alive').status_code == 404
        assert record.expires_at == old_expiry
        response = client.post(path + '/keep-alive', headers=headers)
        assert response.status_code == 200
        assert record.expires_at > old_expiry + 1700
        assert response.json()['expires_at'] == client.get(path, headers=headers).json()['expires_at']
        record.expires_at = time.time() - 1
        assert client.post(path + '/keep-alive', headers=headers).status_code == 404
