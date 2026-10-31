"""One-worker public API with explicit local or consented hosted inference."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import hashlib
import os
import time
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.exceptions import HTTPException

from apps.api.config import Settings
from apps.api.extraction import extract_document, ocr_capabilities
from apps.api.extraction_worker import extract_isolated
from apps.api.jobs import BoundedJobs
from apps.api.ml_client import FixtureMLClient, RealMLClient, validate_answer, validate_snapshot
from apps.api.schemas import AnalysisRequest, ApiError, QuestionRequest, ReviewRequest
from apps.api.schemas import ErrorResponse, UploadAccepted, Metadata, ExtractionResponse, ReviewResponse, AnalysisAccepted, HealthResponse
from apps.api.ml_client.validation import Snapshot, Answer
from apps.api.limits import UploadBodyLimit
from apps.api.sessions import SessionStore
from apps.api.reports import build_report, render_markdown, render_html

log = logging.getLogger('nyayalens.api')
ACTIVE = {'queued', 'running'}
Token = Annotated[str | None, Header(alias='X-Session-Token', max_length=256)]


def _iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def create_app(settings: Settings | None = None, ml_client=None, extractor=None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = SessionStore(settings)
    jobs = BoundedJobs(settings.extraction_workers, settings.extraction_queue_size)
    ml = ml_client or (FixtureMLClient(settings) if settings.ml_mode == 'fixture' else RealMLClient(settings))
    # Test injection may use a controlled synchronous function. Production always
    # runs the real native parser in a killable, memory-limited subprocess.
    custom_extractor = extractor
    # Only metadata IDs are retained for failed downstream cleanup.
    cleanup: dict[str, dict] = {}
    analysis_tasks: dict[str, asyncio.Task] = {}
    extraction_futures: dict[str, asyncio.Future] = {}
    question_tasks: dict[tuple[str, str], asyncio.Task] = {}
    capabilities: dict = {}
    cleanup_lock=asyncio.Lock()
    upload_windows: dict[str, tuple[float, int]] = {}
    rate_salt=secrets.token_bytes(32)

    def schedule_cleanup(ids):
        for aid in ids:
            cleanup.setdefault(aid, {'attempts': 0, 'next': time.monotonic(), 'exhausted': False})

    def cancel_document(record):
        future = extraction_futures.pop(record.document_id, None)
        if future:
            future.cancel()
        for aid in record.analysis_ids | set(record.analyses):
            task = analysis_tasks.get(aid)
            if task:
                task.cancel()
        for key, task in list(question_tasks.items()):
            if key[0] == record.document_id:
                task.cancel()

    async def cleanup_once():
        async with cleanup_lock:
            await cleanup_batch()

    async def cleanup_batch():
        # One cleanup at a time, finite request timeout, at most five attempts.
        due=[(aid,entry) for aid,entry in cleanup.items() if not entry['exhausted'] and entry['next'] <= time.monotonic()][:4]
        for aid, entry in due:
            if entry['exhausted'] or entry['next'] > time.monotonic():
                continue
            entry['attempts'] += 1
            try:
                await asyncio.wait_for(ml.delete(aid), timeout=min(settings.model_timeout_seconds, 5))
            except Exception:
                entry['exhausted'] = entry['attempts'] >= 5
                entry['next'] = time.monotonic() + min(2 ** entry['attempts'], 30)
                log.warning('Private cleanup unconfirmed; attempt=%d exhausted=%s', entry['attempts'], entry['exhausted'])
            else:
                cleanup.pop(aid, None)

    async def maintenance():
        while True:
            for record in list(store.records.values()):
                now=time.time()
                if record.expires_at <= now:
                    ids=await store.delete(record,expired_before=now)
                    if not record.deleted:
                        continue
                    cancel_document(record)
                    for aid in ids:
                        task=analysis_tasks.get(aid)
                        if task: task.cancel()
                    schedule_cleanup(ids)
            await store.retry_cleanup()
            await cleanup_once()
            await asyncio.sleep(settings.cleanup_interval_seconds)

    @asynccontextmanager
    async def lifespan(app):
        await store.acquire_runtime()
        try:
            await store.startup_cleanup()
            capabilities.update(await asyncio.to_thread(ocr_capabilities))
            task = asyncio.create_task(maintenance())
            try:
                yield
            finally:
                task.cancel()
                for running in list(analysis_tasks.values()) + list(question_tasks.values()):
                    running.cancel()
                await asyncio.gather(task, *analysis_tasks.values(), *question_tasks.values(), return_exceptions=True)
                await jobs.close()
                for record in list(store.records.values()):
                    schedule_cleanup(await store.delete(record))
                await cleanup_once()
                await store.retry_cleanup()
        finally:
            try:
                await ml.close()
            finally:
                await store.release_runtime()

    app = FastAPI(title='NyayaLens Public API', version='1.0.0', lifespan=lifespan,
        responses={code:{'model':ErrorResponse} for code in [404,409,413,415,422,429,502,503,504]})
    app.state.store, app.state.ml, app.state.settings = store, ml, settings
    app.state.cleanup = cleanup
    app.state.cleanup_once = cleanup_once
    app.state.analysis_tasks = analysis_tasks
    app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin],
                       allow_methods=['GET','POST','PATCH','DELETE'],
                       allow_headers=['Content-Type','X-Session-Token','X-Compare-Session-Token'], expose_headers=['X-Request-ID'])
    # One MB multipart overhead, while actual file bytes retain the exact configured limit.
    app.add_middleware(UploadBodyLimit,max_bytes=(settings.max_upload_mb+1)*1024*1024)

    @app.middleware('http')
    async def privacy_headers(request, call_next):
        request.state.request_id = 'req_' + secrets.token_hex(8)
        if request.method=='POST' and request.url.path=='/api/v1/documents':
            now=time.monotonic()
            for key, (started, _) in list(upload_windows.items()):
                if now-started>=60:
                    upload_windows.pop(key,None)
            client=request.client.host if request.client else 'unknown'
            key=hashlib.sha256(rate_salt+client.encode()).hexdigest()
            started,count=upload_windows.get(key,(now,0))
            if count>=settings.upload_rate_limit or (len(upload_windows)>=1024 and key not in upload_windows):
                response=JSONResponse({'error':{'code':'RATE_LIMITED','message':'Upload rate limit reached. Retry later.','retryable':True},'request_id':request.state.request_id},status_code=429,headers={'Retry-After':'60','Cache-Control':'no-store'})
                return response
            upload_windows[key]=(started,count+1)
        try:
            response = await call_next(request)
        except Exception:
            # No traceback/input dump: exception messages may contain private text.
            log.error('Unhandled API failure request_id=%s', request.state.request_id)
            response = error_response(request, ApiError('INTERNAL_ERROR','An internal error occurred.',500))
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Request-ID'] = request.state.request_id
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    def error_response(request, error):
        return JSONResponse(status_code=error.status, content={
            'error': {'code':error.code,'message':error.message,'retryable':error.retryable},
            'request_id':getattr(request.state,'request_id','req_unknown')})

    @app.exception_handler(ApiError)
    async def api_error(request, error):
        return error_response(request,error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return error_response(request,ApiError('VALIDATION_ERROR','Request fields are missing or invalid. Check the published API schema.',422))

    @app.exception_handler(HTTPException)
    async def http_error(request,error):
        return error_response(request,ApiError('NOT_FOUND' if error.status_code==404 else 'INVALID_REQUEST',
            'Route not found.' if error.status_code==404 else 'Request could not be processed.',error.status_code))

    def metadata(record):
        return dict(document_id=record.document_id,status=record.status,revision=record.revision,
            filename=record.filename,document_type=record.document_type,input_language=record.input_language,
            warnings=record.warnings,extraction_ready=record.extraction_ready,
            reviewed_revision=record.reviewed_revision,expires_at=_iso(record.expires_at),
            progress=record.extraction_progress)

    def alive(record, revision=None):
        return not record.deleted and record.expires_at > time.time() and (revision is None or record.revision == revision)

    def set_analysis_status(record,fallback):
        statuses=[s['status'] for s in record.analyses.values() if s['document_revision']==record.revision]
        record.status='analysing' if 'running' in statuses else 'queued' if 'queued' in statuses else fallback

    async def run_extraction(record):
        revision=record.revision
        loop=asyncio.get_running_loop()
        def progress(value):
            def update():
                if alive(record,revision):
                    record.extraction_progress=dict(value)
                    # Only numeric counts/stages, never document text or source names.
                    log.info('Extraction progress pages=%s/%s paragraphs=%s/%s ocr_pages=%s',
                        value.get('completed_pages','?'),value.get('total_pages','?'),
                        value.get('completed_paragraphs','?'),value.get('total_paragraphs','?'),value.get('completed_ocr_pages','?'))
            loop.call_soon_threadsafe(update)
        try:
            async with record.lock:
                if not alive(record,revision):
                    return
            if custom_extractor:
                extracted = await asyncio.to_thread(custom_extractor,record.path,record.kind,record.input_language,settings,progress)
            else:
                extracted = await extract_isolated(record.path,record.kind,record.input_language,settings,progress)
            async with record.lock:
                if not alive(record,revision):
                    return
                record.clauses=extracted['clauses']
                record.warnings=extracted['warnings']
                if record.input_language=='auto':
                    record.input_language=extracted['input_language']
                if record.document_type=='auto':
                    record.document_type=extracted['document_type']
                record.extraction_ready=True
                record.status='awaiting_review'
        except ApiError as error:
            async with record.lock:
                if alive(record,revision):
                    record.status='failed'
                    record.warnings=[error.code + ': ' + error.message]
        except Exception:
            async with record.lock:
                if alive(record,revision):
                    record.status='failed'
                    record.warnings=['EXTRACTION_FAILED: The local parser could not process this document.']
        finally:
            extraction_futures.pop(record.document_id,None)

    @app.get('/api/v1/health', tags=['health'],response_model=HealthResponse)
    async def health():
        try:
            h=await asyncio.wait_for(ml.health(),timeout=min(settings.model_timeout_seconds,2))
        except (TimeoutError,ApiError):
            h={'available':False}
        model=dict(available=h.get('available') is True and settings.ml_mode=='real',
            classifier_ready=h.get('classifier_loaded'),generator_ready=h.get('generator_loaded'),
            language_paths=h.get('tested_language_matrix',[]))
        if settings.ml_mode=='fixture':
            model.update(simulation=True,warnings=h.get('warnings',[]))
        return dict(status='ok' if model['available'] else 'degraded',mode=settings.ml_mode,
            extraction=dict(ready=True,pdf=True,docx=True,ocr=capabilities,
                isolation=dict(mode='subprocess',timeout_seconds=settings.extraction_timeout_seconds,memory_mb=settings.extraction_memory_mb)),ml=model,
            cleanup=dict(pending=sum(not x['exhausted'] for x in cleanup.values()),exhausted=sum(x['exhausted'] for x in cleanup.values()),local=store.cleanup_status()))

    @app.get('/api/v1/capabilities',tags=['health'])
    async def public_capabilities():
        return {'limits':{'max_upload_bytes':settings.max_upload_mb*1024*1024,'max_pdf_pages':settings.max_pdf_pages,'max_extracted_chars':settings.max_extracted_chars,'max_analysis_seconds':settings.max_analysis_seconds},
                'processing':{'explicit_consent_required':True,'session_ttl_minutes':settings.session_ttl_minutes,'temporary_server_storage':True,'external_ai_inference':settings.inference_mode=='hosted','inference_mode':settings.inference_mode,'providers':['Groq'] if settings.inference_mode=='hosted' else []},
                'reports':['json','md','html'],'languages':{'en':'experimental','hi':'experimental','pa':'experimental'},
                'legal_advice':False,'blockchain':False}

    @app.post('/api/v1/documents',status_code=202,tags=['documents'],response_model=UploadAccepted)
    async def upload(file: Annotated[UploadFile,File()],
        input_language: Annotated[Literal['auto','en','hi','pa'],Form()]='auto',
        document_type: Annotated[Literal['auto','agreement','fir','notice','other'],Form()]='auto',
        processing_consent: Annotated[bool, Form()]=False,
        external_ai_consent: Annotated[bool, Form()]=False):
        record=None
        try:
            if len(store.records)>=128 or len(cleanup)>=128:
                raise ApiError('MODEL_BUSY','Temporary session or cleanup capacity reached.',429,True)
            # Filename is display-only; storage names are generated server-side.
            filename=(file.filename or '').replace('\\','/').split('/')[-1]
            filename=''.join(c for c in filename if c.isprintable())[:200]
            suffix=Path(filename).suffix.lower()
            kinds={'.pdf':('pdf',{'application/pdf','application/octet-stream'}),
                '.docx':('docx',{'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/zip','application/octet-stream'})}
            if suffix not in kinds or file.content_type not in kinds[suffix][1]:
                raise ApiError('UNSUPPORTED_FILE','Upload a PDF or DOCX with a matching content type.',415)
            if not processing_consent:
                raise ApiError('CONSENT_REQUIRED','Explicit consent to temporary document processing is required.',422)
            if settings.inference_mode=='hosted' and not external_ai_consent:
                raise ApiError('CONSENT_REQUIRED','Explicit consent to sending admitted text to Groq is required for this deployment.',422)
            kind=kinds[suffix][0]
            record,token=await store.create(filename,kind,input_language,document_type)
            record.inference_mode=settings.inference_mode
            record.external_ai_consent=external_ai_consent
            total=0
            with record.path.open('xb') as stream:
                while chunk:=await file.read(64*1024):
                    total+=len(chunk)
                    if total > settings.max_upload_mb*1024*1024:
                        raise ApiError('FILE_TOO_LARGE','Upload exceeds the configured size limit.',413)
                    await asyncio.to_thread(stream.write,chunk)
            if not total:
                raise ApiError('EMPTY_DOCUMENT','The uploaded file is empty.',422)
            record.extraction_progress={'stage':'uploaded','received_bytes':total}
            log.info('Upload received bytes=%d',total)
            future=await jobs.submit(lambda:run_extraction(record))
            extraction_futures[record.document_id]=future
            return dict(document_id=record.document_id,session_token=token,status='extracting',revision=1)
        except BaseException:
            if record:
                await asyncio.shield(store.delete(record))
            raise
        finally:
            await file.close()

    @app.get('/api/v1/documents/{document_id}',tags=['documents'],response_model=Metadata)
    async def get_document(document_id: str, x_session_token: Token=None):
        record=await store.get(document_id,x_session_token,touch=False)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            return metadata(record)

    @app.post('/api/v1/documents/{document_id}/keep-alive',tags=['documents'],response_model=Metadata)
    async def keep_document_alive(document_id: str, x_session_token: Token=None):
        # Only an explicit user action extends retention; metadata polling never does.
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            return metadata(record)

    @app.get('/api/v1/documents/{document_id}/extraction',tags=['extraction'],response_model=ExtractionResponse)
    async def get_extraction(document_id: str,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token,touch=False)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            if not record.extraction_ready:
                if record.status=='failed':
                    warning=record.warnings[0] if record.warnings else 'EXTRACTION_FAILED: Extraction failed.'
                    code=warning.split(':',1)[0]
                    raise ApiError(code,warning.split(':',1)[-1].strip(),
                        413 if code=='FILE_TOO_LARGE' else 503 if code=='OCR_UNAVAILABLE' else 504 if code=='EXTRACTION_TIMEOUT' else 422,
                        retryable=code in {'OCR_UNAVAILABLE','EXTRACTION_TIMEOUT'})
                raise ApiError('EXTRACTION_NOT_READY','Extraction is still processing.',409,True)
            return dict(document_id=document_id,revision=record.revision,reviewed_revision=record.reviewed_revision,
                clauses=[c.model_dump() for c in record.clauses],warnings=record.warnings,
                input_language=record.input_language,document_type=record.document_type,progress=record.extraction_progress)

    @app.patch('/api/v1/documents/{document_id}/extraction',tags=['extraction'],response_model=ReviewResponse)
    async def review(document_id: str,body: ReviewRequest,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        changed=await store.review(record,body)
        if changed:
            schedule_cleanup(record.invalidated_analysis_ids)
            for key,task in list(question_tasks.items()):
                if key[0]==record.document_id:
                    task.cancel()
        return dict(document_id=document_id,revision=record.revision,reviewed_revision=record.reviewed_revision,
            status=record.status,changed=changed)

    @app.get('/api/v1/documents/{document_id}/source',tags=['documents'])
    async def source(document_id: str,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            try:
                stream=record.path.open('rb')
            except FileNotFoundError:
                raise ApiError('NOT_FOUND','Source no longer exists.',404) from None
            template=FileResponse(record.path,media_type='application/pdf' if record.kind=='pdf' else
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',filename=record.filename,
                content_disposition_type='attachment')
        async def chunks():
            try:
                while alive(record):
                    chunk=await asyncio.to_thread(stream.read,64*1024)
                    if not chunk or not alive(record): break
                    yield chunk
            finally:
                stream.close()
        headers=dict(template.headers)
        headers.pop('accept-ranges',None)
        return StreamingResponse(chunks(),headers=headers)

    def payload_for(record,aid,language):
        return dict(document_id=record.document_id,analysis_id=aid,document_revision=record.revision,
            input_language=record.input_language,output_language=language,document_type=record.document_type,
            clauses=[dict(clause_id=c.clause_id,reviewed_text=c.reviewed_text,source_ref=c.source_ref.model_dump()) for c in record.clauses])

    async def run_analysis(record,payload):
        aid=payload['analysis_id']; revision=payload['document_revision']
        try:
            async with asyncio.timeout(min(settings.max_analysis_seconds, settings.model_timeout_seconds * max(1,len(payload['clauses'])))):
                while True:
                    snapshot=validate_snapshot(await ml.poll(aid),payload)
                    async with record.lock:
                        if not alive(record,revision) or aid not in record.analyses:
                            schedule_cleanup([aid]); return
                        previous=record.analyses[aid]
                        if snapshot['progress']['completed_clauses']<previous['progress']['completed_clauses']:
                            raise ApiError('INVALID_MODEL_OUTPUT','Local ML progress moved backwards.',502)
                        if previous['status']=='running' and snapshot['status']=='queued':
                            raise ApiError('INVALID_MODEL_OUTPUT','Local ML status moved backwards.',502)
                        record.analyses[aid]=snapshot
                        set_analysis_status(record,snapshot['status'])
                        if snapshot.get('result') and snapshot['status'] not in ACTIVE:
                            snapshot['_review_report']=build_report(record,snapshot)
                    log.info('Analysis progress completed_clauses=%d total_clauses=%d status=%s',
                        snapshot['progress']['completed_clauses'],snapshot['progress']['total_clauses'],snapshot['status'])
                    if snapshot['status'] not in ACTIVE:
                        return
                    await asyncio.sleep(settings.poll_interval_seconds)
        except asyncio.CancelledError:
            schedule_cleanup([aid]); raise
        except (ApiError,TimeoutError) as error:
            if isinstance(error,TimeoutError):
                error=ApiError('MODEL_TIMEOUT','The local model exceeded its processing timeout.',504,True)
            async with record.lock:
                if alive(record,revision) and aid in record.analyses:
                    record.analyses[aid].update(status='failed',error={'code':error.code,'message':error.message,'retryable':error.retryable})
                    record.analyses[aid]['warnings'].append(error.code+': '+error.message)
                    set_analysis_status(record,'failed')
            schedule_cleanup([aid])
        except Exception:
            async with record.lock:
                if alive(record,revision) and aid in record.analyses:
                    record.analyses[aid].update(status='failed',result=None,error=dict(code='INVALID_MODEL_OUTPUT',message='Invalid local ML response.',retryable=False))
                    record.analyses[aid]['warnings'].append('INVALID_MODEL_OUTPUT')
                    set_analysis_status(record,'failed')
            schedule_cleanup([aid])

    @app.post('/api/v1/documents/{document_id}/analyses',status_code=202,tags=['analyses'],response_model=AnalysisAccepted)
    async def analyse(document_id: str,body: AnalysisRequest,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            if body.expected_revision!=record.revision:
                raise ApiError('REVISION_CONFLICT','Reload the current document revision.',409)
            if record.reviewed_revision!=record.revision:
                raise ApiError('ANALYSIS_NOT_READY','Confirm extraction review before analysis.',409)
            for aid,snapshot in record.analyses.items():
                if snapshot['document_revision']==record.revision and snapshot['output_language']==body.output_language and snapshot['status'] in ACTIVE:
                    return dict(analysis_id=aid,status=snapshot['status'],document_revision=record.revision)
            active_count=sum(s['status'] in ACTIVE for r in store.records.values() for s in r.analyses.values())
            if active_count>=settings.max_analysis_jobs:
                raise ApiError('MODEL_BUSY','Public analysis admission limit reached. Retry explicitly.',429,True)
            if len(record.analysis_ids)>=32 or len(cleanup)>=128:
                raise ApiError('MODEL_BUSY','Session job or cleanup capacity reached. Delete this session or retry after cleanup.',429,True)
            aid='a_'+secrets.token_hex(16)
            payload=payload_for(record,aid,body.output_language)
            # Reserve before network IO, so admission is bounded and delete stays responsive.
            record.analysis_ids.add(aid)
            snapshot=dict(analysis_id=aid,status='queued',document_revision=record.revision,
                output_language=body.output_language,progress=dict(completed_clauses=0,total_clauses=len(record.clauses)),result=None,warnings=[])
            record.analyses[aid]=snapshot
            set_analysis_status(record,'queued')
        try:
            accepted=await asyncio.wait_for(ml.start(payload),settings.model_timeout_seconds)
        except asyncio.CancelledError:
            async with record.lock:
                if alive(record,payload['document_revision']) and aid in record.analyses:
                    snapshot.update(status='failed',error=dict(code='REQUEST_CANCELLED',message='Analysis start was interrupted; retry explicitly.',retryable=True))
                    snapshot['warnings'].append('REQUEST_CANCELLED: Analysis start was interrupted.')
                    set_analysis_status(record,'failed')
            schedule_cleanup([aid])
            raise
        except (TimeoutError,ApiError) as error:
            if isinstance(error,TimeoutError):
                error=ApiError('MODEL_TIMEOUT','Starting local analysis timed out.',504,True)
            async with record.lock:
                if alive(record,payload['document_revision']) and aid in record.analyses:
                    snapshot.update(status='failed',error=dict(code=error.code,message=error.message,retryable=error.retryable))
                    snapshot['warnings'].append(error.code+': '+error.message)
                    set_analysis_status(record,'failed')
            schedule_cleanup([aid])
            raise error
        async with record.lock:
            if not alive(record):
                schedule_cleanup([aid]); raise ApiError('NOT_FOUND','Document expired.',404)
            snapshot.update(status=accepted.get('status','queued'),warnings=accepted.get('warnings',[]))
            task=asyncio.create_task(run_analysis(record,payload))
            analysis_tasks[aid]=task
            task.add_done_callback(lambda done: analysis_tasks.pop(aid,None))
            return dict(analysis_id=aid,status=snapshot['status'],document_revision=record.revision)

    @app.get('/api/v1/documents/{document_id}/analyses/{analysis_id}',tags=['analyses'],response_model=Snapshot,response_model_exclude_unset=True)
    async def analysis(document_id: str,analysis_id: str,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token,touch=False)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            snapshot=record.analyses.get(analysis_id)
            if snapshot is None or snapshot['document_revision']!=record.revision:
                raise ApiError('NOT_FOUND','Analysis not found in the current revision.',404)
            value=deepcopy(snapshot)
            value.pop('_review_report',None)
            value['report_available']=bool(snapshot.get('_review_report'))
            return value

    @app.get('/api/v1/documents/{document_id}/analyses/{analysis_id}/report',tags=['reports'])
    async def report(document_id: str,analysis_id: str,format: Literal['json','md','html']='json',
                     include_questions: bool=False,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            snapshot=record.analyses.get(analysis_id)
            if not alive(record) or not snapshot or snapshot['document_revision']!=record.revision:
                raise ApiError('NOT_FOUND','Current analysis not found.',404)
            if snapshot['status'] not in {'complete','needs_review'} or not snapshot.get('result'):
                raise ApiError('ANALYSIS_NOT_READY','The review report is not ready.',409,True)
            value=build_report(record,snapshot,include_questions=include_questions)
        headers={'Content-Disposition':f'attachment; filename="review-r{value["document_revision"]}.{format}"'}
        if format=='json':
            return JSONResponse(value,headers=headers)
        if format=='html':
            headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; font-src data:; base-uri 'none'; form-action 'none'"
        return Response(render_markdown(value) if format=='md' else render_html(value),media_type='text/markdown' if format=='md' else 'text/html',headers=headers)

    @app.delete('/api/v1/documents/{document_id}/analyses/{analysis_id}',status_code=204,tags=['analyses'])
    async def cancel_analysis(document_id: str,analysis_id: str,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        async with record.lock:
            snapshot=record.analyses.pop(analysis_id,None)
            if not alive(record) or snapshot is None:
                raise ApiError('NOT_FOUND','Analysis not found.',404)
            task=analysis_tasks.get(analysis_id)
            if task:
                task.cancel()
            for key,task in list(question_tasks.items()):
                if key[0]==document_id:
                    task.cancel()
            record.question_cache.clear()
            record.status='awaiting_review'
            schedule_cleanup([analysis_id])
        return Response(status_code=204)

    @app.post('/api/v1/documents/{document_id}/questions',tags=['questions'],response_model=Answer,response_model_exclude_unset=True)
    async def question(document_id: str,body: QuestionRequest,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        fingerprint=body.model_dump()
        key=(document_id,body.client_request_id)
        async with record.lock:
            if not alive(record):
                raise ApiError('NOT_FOUND','Document not found.',404)
            snapshot=record.analyses.get(body.analysis_id)
            if not snapshot or snapshot['document_revision']!=record.revision or snapshot['status'] not in {'complete','needs_review'} or not snapshot.get('result'):
                raise ApiError('ANALYSIS_NOT_READY','A current completed or reviewable analysis is required.',409)
            cached=record.question_cache.get(body.client_request_id)
            if cached and cached['fingerprint']!=fingerprint:
                raise ApiError('IDEMPOTENCY_CONFLICT','This request ID was already used for different question content.',409)
            if cached and 'answer' in cached:
                return deepcopy(cached['answer'])
            if key not in question_tasks:
                if len(record.question_cache)>=100 and body.client_request_id not in record.question_cache:
                    raise ApiError('MODEL_BUSY','Question limit for this temporary session reached.',429,False)
                if len(question_tasks)>=settings.max_analysis_jobs:
                    raise ApiError('MODEL_BUSY','Too many active question requests.',429,True)
                revision=record.revision
                payload=payload_for(record,body.analysis_id,body.output_language)
                payload.update(question=body.question,client_request_id=body.client_request_id)
                result=deepcopy(snapshot['result'])
                record.question_cache[body.client_request_id]={'fingerprint':fingerprint}
                async def generate():
                    try:
                        raw=await asyncio.wait_for(ml.question(payload),settings.model_timeout_seconds)
                        answer=validate_answer(raw,payload,result)
                        async with record.lock:
                            if not alive(record,revision) or body.analysis_id not in record.analyses:
                                raise ApiError('NOT_FOUND','Document or analysis is no longer current.',404)
                            record.question_cache[body.client_request_id]={'fingerprint':fingerprint,'answer':answer}
                        return answer
                    except TimeoutError:
                        raise ApiError('MODEL_TIMEOUT','Local question processing timed out.',504,True) from None
                    finally:
                        question_tasks.pop(key,None)
                task=asyncio.create_task(generate())
                # Consume errors even if every browser request disconnects.
                task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                question_tasks[key]=task
            task=question_tasks[key]
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if record.deleted or not alive(record):
                raise ApiError('NOT_FOUND','Document no longer exists.',404) from None
            raise

    @app.delete('/api/v1/documents/{document_id}',status_code=204,tags=['documents'])
    async def delete(document_id: str,x_session_token: Token=None):
        record=await store.get(document_id,x_session_token)
        async def finish():
            cancel_document(record)
            schedule_cleanup(record.analysis_ids | set(record.analyses))
            ids=await store.delete(record)
            schedule_cleanup(ids)
        # Disconnects must not interrupt tombstoning/enrollment of local/private cleanup.
        await asyncio.shield(finish())
        return Response(status_code=204)

    from apps.api.features import install_feature_routes
    install_feature_routes(app,store,alive)
    web_root=Path(os.environ.get('WEB_DIST_DIR',Path(__file__).resolve().parents[2]/'frontend'/'dist')).resolve()
    if (web_root/'index.html').is_file():
        @app.get('/{web_path:path}',include_in_schema=False)
        async def web_application(web_path: str):
            if web_path.startswith('api/'):
                raise ApiError('NOT_FOUND','API route not found.',404)
            candidate=(web_root/web_path).resolve()
            if not candidate.is_relative_to(web_root):
                raise ApiError('NOT_FOUND','Asset not found.',404)
            if candidate.is_file():
                response=FileResponse(candidate)
            elif web_path in {'','workspace','privacy-check'}:
                response=FileResponse(web_root/'index.html')
            else:
                raise ApiError('NOT_FOUND','Asset not found.',404)
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' blob: data:; worker-src 'self' blob:; connect-src 'self' blob:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
            return response
    return app


app=create_app()
