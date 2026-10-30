"""Races/timeouts are exercised independently of actual GPU availability."""
import asyncio
import time
from copy import deepcopy

import httpx
import pytest

from apps.api.config import Settings
from apps.api.main import create_app
from apps.api.ml_client import FixtureMLClient
from apps.api.schemas import ApiError
from apps.api.tests.test_api import pdf_bytes


class SlowML(FixtureMLClient):
    def __init__(self,settings):
        super().__init__(settings); self.starting=asyncio.Event(); self.release=asyncio.Event()
        self.starts=0; self.questions=0; self.deletes=[]; self.slow_start=False; self.slow_poll=False; self.slow_question=False
    async def start(self,payload):
        self.starts+=1; self.starting.set()
        if self.slow_start: await self.release.wait()
        return await super().start(payload)
    async def poll(self,aid):
        if self.slow_poll: await asyncio.sleep(1)
        return await super().poll(aid)
    async def question(self,payload):
        self.questions+=1
        if self.slow_question: await asyncio.sleep(.04)
        return await super().question(payload)
    async def delete(self,aid):
        self.deletes.append(aid); await super().delete(aid)


async def prepare(client,data=None):
    response=await client.post('/api/v1/documents',files={'file':('synthetic.pdf',data or pdf_bytes(),'application/pdf')},
        data={'input_language':'en','document_type':'agreement','processing_consent':'true'})
    value=response.json(); base='/api/v1/documents/'+value['document_id']; headers={'X-Session-Token':value['session_token']}
    for _ in range(2000):
        data=(await client.get(base,headers=headers)).json()
        if data.get('extraction_ready'): break
        await asyncio.sleep(.005)
    response=await client.patch(base+'/extraction',headers=headers,json=dict(expected_revision=1,corrections=[],input_language='en',document_type='agreement'))
    assert response.status_code==200,response.text
    return base,headers


async def wait_terminal(client,base,headers,aid):
    for _ in range(200):
        response=await client.get(base+'/analyses/'+aid,headers=headers)
        if response.json()['status'] not in {'queued','running'}: return response.json()
        await asyncio.sleep(.005)
    pytest.fail('Did not terminate')


@pytest.mark.asyncio
async def test_delete_during_private_start_and_admission_bounded(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',max_analysis_jobs=1,poll_interval_seconds=.005)
    ml=SlowML(settings); ml.slow_start=True
    app=create_app(settings,ml_client=ml)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            base,h=await prepare(client); other,oh=await prepare(client)
            starting=asyncio.create_task(client.post(base+'/analyses',headers=h,json=dict(expected_revision=1,output_language='en')))
            await ml.starting.wait()
            duplicate=await client.post(base+'/analyses',headers=h,json=dict(expected_revision=1,output_language='en'))
            assert duplicate.status_code==202 and ml.starts==1
            busy=await client.post(other+'/analyses',headers=oh,json=dict(expected_revision=1,output_language='en'))
            assert busy.status_code==429
            deleted=await asyncio.wait_for(client.delete(base,headers=h),.2)
            assert deleted.status_code==204
            ml.release.set()
            assert (await starting).status_code==404
            assert (await client.get(base,headers=h)).status_code==404
            await app.state.cleanup_once()
            assert ml.deletes and not ml.jobs


@pytest.mark.asyncio
async def test_poll_timeout_and_health_remain_responsive(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',model_timeout_seconds=.05,poll_interval_seconds=.005)
    ml=SlowML(settings); ml.slow_poll=True
    app=create_app(settings,ml_client=ml)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            base,h=await prepare(client)
            r=await client.post(base+'/analyses',headers=h,json=dict(expected_revision=1,output_language='en'))
            aid=r.json()['analysis_id']
            assert (await asyncio.wait_for(client.get('/api/v1/health'),.2)).status_code==200
            snapshot=await wait_terminal(client,base,h,aid)
            assert snapshot['error']['code']=='MODEL_TIMEOUT' and snapshot['status']=='failed'
            assert (await client.get('/api/v1/health')).status_code==200
            await prepare(client)


@pytest.mark.asyncio
async def test_concurrent_question_idempotency_and_review_invalidation(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',poll_interval_seconds=.005)
    ml=SlowML(settings); ml.slow_question=True
    app=create_app(settings,ml_client=ml)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            base,h=await prepare(client)
            aid=(await client.post(base+'/analyses',headers=h,json=dict(expected_revision=1,output_language='en'))).json()['analysis_id']
            await wait_terminal(client,base,h,aid)
            body=dict(analysis_id=aid,question='Synthetic question',output_language='en',client_request_id='once')
            a,b=await asyncio.gather(client.post(base+'/questions',headers=h,json=body),client.post(base+'/questions',headers=h,json=body))
            assert a.status_code==b.status_code==200 and ml.questions==1
            clauses=(await client.get(base+'/extraction',headers=h)).json()['clauses']
            changed=await client.patch(base+'/extraction',headers=h,json=dict(expected_revision=1,corrections=[dict(clause_id=clauses[0]['clause_id'],text='New synthetic text')],input_language='en',document_type='agreement'))
            assert changed.json()['revision']==2
            assert (await client.post(base+'/questions',headers=h,json=body)).status_code==409


@pytest.mark.asyncio
async def test_streaming_body_limit_without_content_length(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',max_upload_mb=1)
    app=create_app(settings)
    async def content():
        yield b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="synthetic.pdf"\r\nContent-Type: application/pdf\r\n\r\n'
        for _ in range(40): yield b'x'*65536
        yield b'\r\n--boundary--\r\n'
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.post('/api/v1/documents',headers={'Content-Type':'multipart/form-data; boundary=boundary'},content=content())
            assert response.status_code==413,response.text
            assert response.json()['error']['code']=='FILE_TOO_LARGE'
            assert not app.state.store.records


@pytest.mark.asyncio
async def test_partial_progress_and_terminal_failed_clause_fields_survive(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',ml_mode='fixture',poll_interval_seconds=.005)
    release=asyncio.Event()
    class PartialML(FixtureMLClient):
        async def poll(self,aid):
            job=self.jobs[aid]
            if not job.get('partial_sent'):
                await super().poll(aid)
                snapshot=await super().poll(aid)
                job['full']=deepcopy(snapshot); job['partial_sent']=True
                snapshot['status']='running'
                snapshot.pop('failed_clauses',None)
                snapshot['progress'].update(completed_clauses=1,stage='mock_first_clause',failed_clauses=0)
                snapshot['result'].pop('failed_clauses',None)
                snapshot['result']['items']=snapshot['result']['items'][:1]
                snapshot['result']['coverage']['analysed']=1
                return snapshot
            await release.wait()
            full=job['full']; failed=full['result']['items'][1]['clause_id']
            full['result']['items']=full['result']['items'][:1]
            full['result']['coverage']['analysed']=1
            full['result']['failed_clauses']=[failed]
            full['progress']['failed_clauses']=1
            full['failed_clauses']=[failed]
            return full
    app=create_app(settings,ml_client=PartialML(settings))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            base,h=await prepare(client,pdf_bytes('1. SYNTHETIC first clause.\n2. SYNTHETIC second clause.'))
            aid=(await client.post(base+'/analyses',headers=h,json=dict(expected_revision=1,output_language='hi'))).json()['analysis_id']
            for _ in range(100):
                response=await client.get(base+'/analyses/'+aid,headers=h); snapshot=response.json()
                if snapshot.get('result'): break
                await asyncio.sleep(.005)
            assert snapshot['status']=='running' and snapshot['result']['coverage']==dict(analysed=1,total=2)
            assert snapshot['progress']['stage']=='mock_first_clause'
            release.set(); terminal=await wait_terminal(client,base,h,aid)
            assert terminal['status']=='needs_review'
            assert terminal['progress']['completed_clauses']==2
            assert terminal['result']['coverage']['analysed']==1 and terminal['result']['failed_clauses']==['c2']
