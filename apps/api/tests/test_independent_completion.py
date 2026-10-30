"""Remaining BE1-only integration failures, without any frontend or ML role."""
import asyncio
import sys
import time

import httpx
import psutil
import pytest
from starlette.datastructures import UploadFile

from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.extraction_worker import extract_isolated
from apps.api.tests.test_api import pdf_bytes
from apps.api.tests.test_concurrency import SlowML,prepare


@pytest.mark.asyncio
async def test_real_parser_timeout_public_error_health_and_next_upload(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',extraction_timeout_seconds=.01)
    app=create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/documents',files={'file':('synthetic.pdf',pdf_bytes(),'application/pdf')})
            assert response.status_code==202
            doc=response.json(); headers={'X-Session-Token':doc['session_token']}; base='/api/v1/documents/'+doc['document_id']
            for _ in range(100):
                status=(await client.get(base,headers=headers)).json()['status']
                if status=='failed': break
                await asyncio.sleep(.01)
            error=await client.get(base+'/extraction',headers=headers)
            assert error.status_code==504 and error.json()['error']['code']=='EXTRACTION_TIMEOUT'
            assert (await client.get('/api/v1/health')).status_code==200
            settings.extraction_timeout_seconds=30
            await prepare(client)


@pytest.mark.asyncio
async def test_delete_terminates_real_running_parser_process(tmp_path,monkeypatch):
    started=asyncio.Event(); pids=[]
    def ready(pid): pids.append(pid); started.set()
    async def slow(path,kind,language,settings,progress):
        return await extract_isolated(path,kind,language,settings,progress,
            command=[sys.executable,'-c','import time; time.sleep(60)'],on_started=ready)
    monkeypatch.setattr('apps.api.main.extract_isolated',slow)
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture')
    app=create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/documents',files={'file':('synthetic.pdf',pdf_bytes(),'application/pdf')})
            doc=response.json(); base='/api/v1/documents/'+doc['document_id']; headers={'X-Session-Token':doc['session_token']}
            await asyncio.wait_for(started.wait(),5)
            assert (await client.delete(base,headers=headers)).status_code==204
            for _ in range(100):
                if not psutil.pid_exists(pids[0]): break
                await asyncio.sleep(.01)
            assert not psutil.pid_exists(pids[0])
            assert (await client.get(base,headers=headers)).status_code==404
            assert not app.state.store.records


@pytest.mark.asyncio
async def test_interrupted_upload_does_not_leave_session_or_source(tmp_path,monkeypatch):
    original=UploadFile.read; calls=0
    async def interrupted(self,size=-1):
        nonlocal calls
        calls+=1
        if calls==2: raise asyncio.CancelledError()
        return await original(self,size)
    monkeypatch.setattr(UploadFile,'read',interrupted)
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture')
    app=create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            # Starlette normalizes an inner cancellation into a no-response
            # error; either way our boundary must clear the partial upload.
            response=await client.post('/api/v1/documents',files={'file':('synthetic.pdf',pdf_bytes(),'application/pdf')})
            assert response.status_code==500 and response.json()['error']['code']=='INTERNAL_ERROR'
            assert not app.state.store.records
            assert not list(settings.runtime_dir.glob('doc_*'))


@pytest.mark.asyncio
async def test_interrupted_ml_start_does_not_leave_queued_reservation(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture')
    ml=SlowML(settings); ml.slow_start=True
    app=create_app(settings,ml_client=ml)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            base,headers=await prepare(client)
            task=asyncio.create_task(client.post(base+'/analyses',headers=headers,json={'expected_revision':1,'output_language':'en'}))
            await ml.starting.wait(); task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
            record=next(iter(app.state.store.records.values()))
            assert all(s['status']=='failed' for s in record.analyses.values())
            assert app.state.cleanup


def test_fractional_timeout_and_ttl_environment(monkeypatch):
    monkeypatch.setenv('SESSION_TTL_MINUTES','0.5'); monkeypatch.setenv('CLEANUP_INTERVAL_SECONDS','0.25')
    monkeypatch.setenv('EXTRACTION_TIMEOUT_SECONDS','1.75'); monkeypatch.setenv('WEB_ORIGIN','http://localhost:5173/')
    settings=Settings.from_env()
    assert settings.session_ttl_minutes==.5 and settings.cleanup_interval_seconds==.25
    assert settings.extraction_timeout_seconds==1.75 and settings.web_origin=='http://localhost:5173'
