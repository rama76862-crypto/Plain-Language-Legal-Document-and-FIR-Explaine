"""Finite-timeout HTTP transport and clearly labelled deterministic development adapter."""
from copy import deepcopy
from urllib.parse import quote
import httpx
from apps.api.schemas import ApiError

FIXTURE_WARNING = 'DEVELOPMENT FIXTURE: simulated echo only; no model, translation, classifier or legal analysis ran.'
ERRORS = {
    'MODEL_BUSY': (429, True), 'MODEL_UNAVAILABLE': (503, True),
    'MODEL_TIMEOUT': (504, True), 'INVALID_MODEL_OUTPUT': (502, False),
    'NOT_FOUND': (404, False), 'REVISION_CONFLICT': (409, False),
    'ANALYSIS_NOT_READY': (409, True), 'UNSUPPORTED_LANGUAGE': (422, False),
    'MODEL_CONTEXT_LIMIT': (422, False),
}
_QUESTION_FIELDS = (
    'document_id', 'analysis_id', 'document_revision', 'question',
    'output_language', 'client_request_id',
)
_INPUT_LANGUAGES = {'en', 'hi', 'pa', 'unknown'}
_OUTPUT_LANGUAGES = {'en', 'hi', 'pa'}
_LANGUAGE_PATH_STATUSES = {'tested', 'experimental', 'unsupported', 'unknown'}


def _tested_language_matrix(data):
    """Keep only explicit pairwise language paths; source-only flags are not a matrix."""
    matrix = data.get('tested_language_matrix')
    if not isinstance(matrix, list):
        return []

    paths = []
    for path in matrix:
        if not isinstance(path, dict):
            continue
        if path.get('input_language') not in _INPUT_LANGUAGES:
            continue
        if path.get('output_language') not in _OUTPUT_LANGUAGES:
            continue
        status = path.get('status')
        if status not in _LANGUAGE_PATH_STATUSES:
            status = 'unknown'
        paths.append({**path, 'status': status})
    return paths


class RealMLClient:
    def __init__(self, settings, transport=None):
        self.settings = settings
        headers = {'X-ML-Service-Token': settings.ml_service_token} if settings.ml_service_token else {}
        self.client = httpx.AsyncClient(base_url=settings.ml_base_url.rstrip('/'),
            timeout=httpx.Timeout(settings.model_timeout_seconds, connect=min(5, settings.model_timeout_seconds)),
            headers=headers, transport=transport, follow_redirects=False, trust_env=False)

    async def _request(self, method, path, *, payload=None, statuses=(200,)):
        try:
            response = await self.client.request(method, path, json=payload)
        except httpx.TimeoutException:
            raise ApiError('MODEL_TIMEOUT', 'The local ML service timed out. Retry explicitly.', 504, True) from None
        except httpx.RequestError:
            raise ApiError('MODEL_UNAVAILABLE', 'The local ML service cannot be reached.', 503, True) from None
        if response.status_code not in statuses:
            code = None
            try:
                error = response.json().get('error', {})
                code = error.get('code') if isinstance(error, dict) else None
            except (ValueError, AttributeError):
                pass
            if code not in ERRORS:
                code = {404:'NOT_FOUND',409:'ANALYSIS_NOT_READY',429:'MODEL_BUSY',503:'MODEL_UNAVAILABLE',504:'MODEL_TIMEOUT'}.get(response.status_code, 'INVALID_MODEL_OUTPUT')
            status, retryable = ERRORS[code]
            # Never forward arbitrary upstream messages containing source text or credentials.
            raise ApiError(code, {
                'NOT_FOUND':'The private analysis is missing, deleted or expired.',
                'MODEL_BUSY':'The local model queue is full. Retry explicitly.',
                'MODEL_TIMEOUT':'The local model timed out. Retry explicitly.',
                'MODEL_UNAVAILABLE':'The local model is unavailable.',
                'UNSUPPORTED_LANGUAGE':'This language path is not supported by the local model.',
                'REVISION_CONFLICT':'The private analysis revision is stale.',
                'ANALYSIS_NOT_READY':'The private analysis is not ready.',
                'MODEL_CONTEXT_LIMIT':'The question is too long for the local model. Ask a shorter question about one clause.',
            }.get(code, 'The local ML service returned an invalid response.'), status, retryable)
        if response.status_code == 204:
            return None
        try:
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except ValueError:
            raise ApiError('INVALID_MODEL_OUTPUT', 'The local ML service did not return a JSON object.', 502) from None

    async def health(self):
        try:
            data = await self._request('GET', '/internal/health')
        except ApiError:
            return {'available':False, 'classifier_loaded':False, 'generator_loaded':False,
                    'tested_language_matrix':[], 'warnings':['ML readiness unavailable; extraction/review remain usable.'], 'mode':'real'}
        classifier = data.get('classifier_loaded', data.get('classifier_ready')) is True
        generator = data.get('generator_loaded', data.get('generator_ready')) is True
        # Missing affirmative readiness evidence never means ready.
        return {**data, 'available': classifier and generator, 'classifier_loaded':classifier,
                'generator_loaded':generator, 'tested_language_matrix':_tested_language_matrix(data), 'mode':'real'}

    async def start(self, payload):
        result = await self._request('POST', '/internal/analyse', payload=payload, statuses=(202,))
        if result.get('analysis_id') != payload['analysis_id'] or result.get('status') not in {'queued','running'}:
            raise ApiError('INVALID_MODEL_OUTPUT', 'The private start response did not preserve analysis identity/status.', 502)
        warnings = result.get('warnings', [])
        if not isinstance(warnings, list) or any(not isinstance(warning,str) for warning in warnings):
            raise ApiError('INVALID_MODEL_OUTPUT', 'The private start response contained invalid warnings.', 502)
        for key in ('document_id','document_revision','output_language'):
            if key in result and result[key] != payload[key]:
                raise ApiError('INVALID_MODEL_OUTPUT', 'The private start response did not preserve request identity.', 502)
        return result

    async def poll(self, analysis_id):
        return await self._request('GET', '/internal/jobs/' + quote(analysis_id, safe=''))

    async def question(self, payload):
        # BE1 keeps reviewed clauses in its server-side question context; BE2's
        # strict QuestionRequest accepts only these six bound request fields.
        request = {key: payload[key] for key in _QUESTION_FIELDS}
        return await self._request('POST', '/internal/question', payload=request)

    async def delete(self, analysis_id):
        try:
            await self._request('DELETE', '/internal/jobs/' + quote(analysis_id, safe=''), statuses=(200,204))
        except ApiError as error:
            if error.code != 'NOT_FOUND':
                raise

    async def close(self):
        await self.client.aclose()


class FixtureMLClient:
    """Explicit development echo. It never diagnoses arbitrary uploaded text."""
    def __init__(self, settings):
        if settings.ml_mode != 'fixture':
            raise ValueError('FixtureMLClient requires explicit ML_MODE=fixture')
        self.jobs = {}

    async def health(self):
        return {'available':True, 'classifier_loaded':False, 'generator_loaded':False,
                'tested_language_matrix':[], 'mode':'fixture', 'simulation':True, 'warnings':[FIXTURE_WARNING]}

    async def start(self, payload):
        if payload['analysis_id'] not in self.jobs:
            self.jobs[payload['analysis_id']] = {'payload':deepcopy(payload), 'polled':False}
        return {'analysis_id':payload['analysis_id'], 'status':'queued', 'warnings':[FIXTURE_WARNING]}

    async def poll(self, analysis_id):
        job = self.jobs.get(analysis_id)
        if job is None:
            raise ApiError('NOT_FOUND', 'The development job no longer exists.', 404)
        payload = job['payload']
        base = {key:payload[key] for key in ('analysis_id','document_revision','output_language')}
        total = len(payload['clauses'])
        if not job['polled']:
            job['polled'] = True
            return {**base, 'status':'running', 'progress':{'completed_clauses':0,'total_clauses':total}, 'result':None, 'warnings':[FIXTURE_WARNING]}
        items = []
        for index, clause in enumerate(payload['clauses'],1):
            items.append({'item_id':f'fixture_{index}', 'clause_id':clause['clause_id'], 'kind':'explanation',
                'category':None, 'explanation':'DEVELOPMENT FIXTURE: reviewed text echoed; no explanation or translation generated.',
                'evidence':[{'clause_id':clause['clause_id'], 'quote':clause['reviewed_text']}],
                'reference_ids':[], 'review_status':'needs_review', 'detector':'development_fixture',
                'model_score':None, 'limitations':[FIXTURE_WARNING]})
        result = {key:payload[key] for key in ('document_id','analysis_id','document_revision','input_language','output_language','document_type')}
        failures = [{'clause_id':clause['clause_id'],'reason':'development_fixture_no_model_analysis'} for clause in payload['clauses']]
        result.update(coverage={'analysed':0,'total':total},items=items,deadlines=[],warnings=[FIXTURE_WARNING],legal_aid=[],failed_clauses=failures,
            provenance={'classifier_version':'not-run','generator':'development-fixture','rules_version':'not-run'})
        return {**base, 'status':'needs_review', 'progress':{'completed_clauses':total,'total_clauses':total,'stage':'development_fixture_echo'},
                'result':result, 'warnings':[FIXTURE_WARNING], 'failed_clauses':failures}

    async def question(self, payload):
        if payload['analysis_id'] not in self.jobs:
            raise ApiError('NOT_FOUND', 'The development job no longer exists.', 404)
        return {'answer':'DEVELOPMENT FIXTURE: no model answer is available. Consult the reviewed source text.',
                'evidence':[], 'reference_ids':[], 'review_status':'needs_review', 'limitations':[FIXTURE_WARNING]}

    async def delete(self, analysis_id):
        self.jobs.pop(analysis_id, None)

    async def close(self):
        self.jobs.clear()
