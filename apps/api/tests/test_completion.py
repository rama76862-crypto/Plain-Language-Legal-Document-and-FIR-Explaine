"""Public completion features use synthetic documents and explicit ML doubles."""
import time
import pytest
from fastapi.testclient import TestClient
from apps.api.main import create_app
from apps.api.config import Settings
from apps.api.tests.test_api import upload, wait_extraction, confirm, start, wait_analysis, pdf_bytes

def test_consent_required_before_storage(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/"runtime",ml_mode="fixture"))
    with TestClient(app) as client:
        response=client.post("/api/v1/documents",files={"file":("sample.pdf",pdf_bytes(),"application/pdf")})
        assert response.status_code==422 and response.json()["error"]["code"]=="CONSENT_REQUIRED"
        assert not app.state.store.records

def test_automatic_report_is_scoped_and_does_not_persist(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/"runtime",ml_mode="fixture",poll_interval_seconds=.005))
    with TestClient(app) as client:
        value,headers=upload(client)
        wait_extraction(client,value,headers);confirm(client,value,headers)
        aid=start(client,value,headers).json()["analysis_id"]
        response=wait_analysis(client,value,headers,aid)
        assert response.json()["report_available"] is True
        path=f"/api/v1/documents/{value['document_id']}/analyses/{aid}/report"
        assert client.get(path).status_code==404
        report=client.get(path,headers=headers).json()
        assert report["independent_review"]=="not_performed" and not report["questions"]
        assert value["session_token"] not in str(report)
        assert report["clauses"]
        assert not list((tmp_path/"runtime").rglob("*.md"))
        assert "_review_report" not in response.json()
        client.post(f"/api/v1/documents/{value['document_id']}/questions",headers=headers,json={"analysis_id":aid,"question":"What does this say?","output_language":"en","client_request_id":"report-question"})
        assert client.get(path,headers=headers).json()["questions"]==[]
        assert len(client.get(path+"?include_questions=true",headers=headers).json()["questions"])==1
        for fmt in ("md","html"):
            output=client.get(path+"?format="+fmt,headers=headers)
            assert output.status_code==200 and "attachment" in output.headers["content-disposition"]
            assert output.headers["cache-control"]=="no-store"
            assert value["session_token"] not in output.text
        assert client.delete(f"/api/v1/documents/{value['document_id']}",headers=headers).status_code==204
        assert client.get(path,headers=headers).status_code==404

def test_upload_rate_and_published_limits(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/"runtime",ml_mode="fixture",upload_rate_limit=1))
    with TestClient(app) as client:
        capabilities=client.get("/api/v1/capabilities").json()
        assert capabilities["limits"]["max_pdf_pages"]==50
        assert capabilities["limits"]["max_upload_bytes"]==25*1024*1024
        assert capabilities["processing"]["explicit_consent_required"] is True
        upload(client)
        response=client.post("/api/v1/documents",files={"file":("sample.pdf",pdf_bytes(),"application/pdf")},data={"processing_consent":"true"},headers={"X-Forwarded-For":"different-client"})
        assert response.status_code==429 and response.headers["retry-after"]=="60"

def test_cancel_analysis_removes_report_and_allows_retry(tmp_path):
    app=create_app(Settings(runtime_dir=tmp_path/"runtime",ml_mode="fixture",poll_interval_seconds=.005))
    with TestClient(app) as client:
        value,headers=upload(client);wait_extraction(client,value,headers);confirm(client,value,headers)
        aid=start(client,value,headers).json()["analysis_id"];wait_analysis(client,value,headers,aid)
        path=f"/api/v1/documents/{value['document_id']}/analyses/{aid}"
        assert client.delete(path,headers=headers).status_code==204
        assert client.get(path,headers=headers).status_code==404
        assert client.get(path+"/report",headers=headers).status_code==404
        assert start(client,value,headers).status_code==202


def test_broken_indic_pdf_mapping_is_not_treated_as_clean_native_text():
    from apps.api.extraction.service import _quality
    assert _quality("इस नोटिस की प्राप्ति के 15 दिनों के भीतर उत्तर दें।")
    assert _quality("ਪ੍ਰਾਪਤੀ ਤੋਂ 15 ਦਿਨਾਂ ਦੇ ਅੰਦਰ ਜਵਾਬ ਦਿਓ।")
    assert not _quality("ਇਸ ਨੋਟਿਸ "+chr(0x99)+" ਦੀ ਪ੍ਰਾਪਤੀ ਤੋਂ ਜਵਾਬ ਦਿਓ।")
    assert not _quality("इस नो"+"\u021c"+"टिस की "+"\u0135\u00f6\u0226\u01fd"+" प्राप्ति के भीतर उत्तर दें।")

def test_production_static_app_stays_inside_dist_and_does_not_mask_api_errors(tmp_path,monkeypatch):
    public=tmp_path/"dist";public.mkdir()
    (public/"index.html").write_text("<!doctype html><title>synthetic-ui</title>",encoding="utf-8")
    (tmp_path/"private.txt").write_text("synthetic-private-marker",encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR",str(public))
    app=create_app(Settings(runtime_dir=tmp_path/"runtime",ml_mode="fixture"))
    with TestClient(app) as client:
        assert "synthetic-ui" in client.get("/workspace").text
        assert "script-src 'self'" in client.get("/").headers["content-security-policy"]
        response=client.get("/%2e%2e/private.txt")
        assert response.status_code==404 and "synthetic-private-marker" not in response.text
        assert client.get("/api/v1/nonexistent").status_code==404

