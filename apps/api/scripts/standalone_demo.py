"""Self-contained real-HTTP acceptance demo; model work is explicitly simulated.

Run: python -m apps.api.scripts.standalone_demo
Starts only owned loopback Uvicorn children and temporary synthetic documents.
No existing server, private documents, models or credentials are needed.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

import httpx
import pymupdf

from apps.api.config import Settings
from apps.api.scripts.smoke import synthetic

REPO_ROOT = Path(__file__).resolve().parents[3]


class DemoError(RuntimeError):
    """Safe, fixed diagnostic without request contents, paths or tokens."""


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _child():
    """Actual Uvicorn server, gracefully stopped through its private stdin pipe."""
    import uvicorn
    settings = Settings.from_env()
    config = uvicorn.Config('apps.api.main:app', host='127.0.0.1', port=settings.api_port,
                            workers=1, access_log=False, log_level='warning')
    server = uvicorn.Server(config)

    def stop_when_parent_closes():
        # EOF also shuts down if the coordinator exits unexpectedly.
        sys.stdin.readline()
        server.should_exit = True

    threading.Thread(target=stop_when_parent_closes, daemon=True).start()
    asyncio.run(server.serve())


@contextmanager
def _server(runtime: Path, mode: str, *, startup_timeout: float = 30,
            request_timeout: float = 10):
    port = _port()
    # Ignore inherited application settings: this demo must not touch a user's
    # runtime directory, service credential or remote ML configuration.
    env = os.environ.copy()
    for field in Settings.__dataclass_fields__:
        env.pop(field.upper(), None)
    env.update(API_PORT=str(port), ML_MODE=mode, RUNTIME_DIR=str(runtime),
               MODEL_TIMEOUT_SECONDS='2', POLL_INTERVAL_SECONDS='0.02',
               CLEANUP_INTERVAL_SECONDS='1', ML_SERVICE_TOKEN='',
               ML_BASE_URL=f'http://127.0.0.1:{_port()}', PYTHONUNBUFFERED='1')
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(
        [sys.executable, '-m', 'apps.api.scripts.standalone_demo', '--serve-child'],
        cwd=REPO_ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, creationflags=creationflags)
    client = httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=request_timeout,
                          trust_env=False, follow_redirects=False)
    graceful = False
    try:
        deadline = time.monotonic() + startup_timeout
        while True:
            if process.poll() is not None:
                raise DemoError('Owned Uvicorn child exited before readiness.')
            try:
                response = client.get('/api/v1/health')
                if response.status_code == 200:
                    health = response.json()
                    if health.get('mode') != mode:
                        raise DemoError('Demo server mode does not match explicit expectation.')
                    break
            except httpx.RequestError:
                pass
            if time.monotonic() >= deadline:
                raise DemoError('Owned Uvicorn child did not become ready in time.')
            time.sleep(.05)
        yield client
    finally:
        client.close()
        if process.poll() is None:
            try:
                process.stdin.write(b'stop\n')
                process.stdin.flush()
                process.stdin.close()
                process.wait(timeout=15)
                graceful = process.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        else:
            graceful = process.returncode == 0
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        if not graceful and sys.exc_info()[0] is None:
            raise DemoError('Owned Uvicorn child required forced shutdown.')


def _require(condition: bool, message: str):
    if not condition:
        raise DemoError(message)


def _json(response: httpx.Response, expected: int) -> dict:
    _require(response.status_code == expected, 'Unexpected public API response status.')
    try:
        value = response.json()
    except ValueError:
        raise DemoError('Public API returned invalid JSON.') from None
    _require(isinstance(value, dict), 'Public API returned an invalid object.')
    return value


def image_only_pdf() -> bytes:
    """Rasterize a labelled synthetic PDF; uploaded page has no text layer."""
    native, _ = synthetic('pdf')
    with pymupdf.open(stream=native, filetype='pdf') as source:
        page = source[0]
        image = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes('png')
        with pymupdf.open() as scan:
            scanned_page = scan.new_page(width=page.rect.width, height=page.rect.height)
            scanned_page.insert_image(scanned_page.rect, stream=image)
            return scan.tobytes()


def _journey(client: httpx.Client, kind: str, *, unavailable: bool = False, scan: bool = False) -> dict:
    data, mime = (image_only_pdf(), 'application/pdf') if scan else synthetic(kind)
    value = _json(client.post('/api/v1/documents',
        files={'file':('synthetic.' + kind, data, mime)},
        data={'input_language':'en', 'document_type':'agreement','processing_consent':'true'}), 202)
    headers = {'X-Session-Token': value['session_token']}
    base = '/api/v1/documents/' + value['document_id']
    result = {'native_extraction':False, 'scan_ocr':False, 'review':False, 'source':False,
              'analysis_interface':False, 'question_interface':False, 'deleted':False,
              'clause_count':0, 'simulation':not unavailable, 'model_tested':False}
    try:
        deadline = time.monotonic() + 30
        while True:
            metadata = _json(client.get(base, headers=headers), 200)
            _require(metadata['status'] != 'failed', 'Synthetic local extraction failed.')
            if metadata['extraction_ready']:
                break
            _require(time.monotonic() < deadline, 'Synthetic extraction timed out.')
            time.sleep(.05)
        extraction = _json(client.get(base + '/extraction', headers=headers), 200)
        clauses = extraction['clauses']
        _require(bool(clauses), 'Synthetic extraction returned no clauses.')
        if kind == 'docx':
            _require(all(c['source_ref']['page_number'] is None and
                         c['source_ref']['paragraph_index'] >= 1 for c in clauses),
                     'DOCX references do not use real paragraph indexes.')
        else:
            _require(all(c['source_ref']['page_number'] >= 1 for c in clauses),
                     'PDF references do not use real page numbers.')
        if scan:
            _require(all(c['extraction_method'] == 'ocr' and c['review_required'] is True
                         and c['source_ref']['page_number'] == 1 for c in clauses),
                     'Image-only scan did not use reviewable OCR and real page references.')
            result['scan_ocr'] = True
        else:
            result['native_extraction'] = True
        result['clause_count'] = len(clauses)
        _require(client.get(base + '/source').status_code == 404,
                 'Unauthenticated source request was not denied.')
        source = client.get(base + '/source', headers=headers)
        _require(source.status_code == 200 and source.content == data and
                 source.headers.get('cache-control') == 'no-store',
                 'Authenticated source bytes or privacy headers were incorrect.')
        result['source'] = True
        before = client.post(base + '/analyses', headers=headers,
            json={'expected_revision':value['revision'], 'output_language':'en'})
        _require(before.status_code == 409, 'Analysis was accepted before review.')
        review = _json(client.patch(base + '/extraction', headers=headers,
            json={'expected_revision':value['revision'], 'corrections':[],
                  'input_language':'en', 'document_type':'agreement'}), 200)
        _require(review['reviewed_revision'] == review['revision'],
                 'Unchanged extraction was not explicitly confirmed.')
        result['review'] = True
        accepted = client.post(base + '/analyses', headers=headers,
            json={'expected_revision':review['revision'], 'output_language':'en'})
        if unavailable:
            # Windows may surface a closed loopback port as connect timeout
            # rather than immediate refusal. Both must remain explicit failures.
            _require(accepted.status_code in {503,504}, 'Unavailable ML unexpectedly accepted analysis.')
            error = _json(accepted, accepted.status_code)
            code = error.get('error', {}).get('code')
            _require(code in {'MODEL_UNAVAILABLE','MODEL_TIMEOUT'},
                     'Unavailable real ML did not return an explicit error.')
            _require(client.get('/api/v1/health').status_code == 200,
                     'Health failed after unavailable ML.')
            result.update(analysis_interface=True, unavailable_error=True, unavailable_error_code=code)
        else:
            accepted = _json(accepted, 202)
            aid = accepted['analysis_id']
            deadline = time.monotonic() + 15
            while True:
                snapshot = _json(client.get(base + '/analyses/' + aid, headers=headers), 200)
                if snapshot['status'] not in {'queued', 'running'}:
                    break
                _require(time.monotonic() < deadline, 'Development job polling timed out.')
                time.sleep(.05)
            _require(snapshot['status'] == 'needs_review' and snapshot.get('result') is not None,
                     'Development fixture did not end in its labelled review state.')
            model_result = snapshot['result']
            _require(model_result['coverage']['analysed'] == 0 and
                     snapshot['progress']['completed_clauses'] == len(clauses) and
                     snapshot['progress']['total_clauses'] == len(clauses),
                     'Development fixture coverage or actual echo progress was misleading.')
            _require(any('DEVELOPMENT FIXTURE' in warning for warning in snapshot['warnings']),
                     'Development fixture warning was missing.')
            by_id = {c['clause_id']:c['reviewed_text'] for c in clauses}
            for item in model_result['items']:
                for evidence in item['evidence']:
                    _require(evidence['clause_id'] in by_id and evidence['quote'] in by_id[evidence['clause_id']],
                             'Development evidence failed original-source matching.')
            result['analysis_interface'] = True
            question = {'analysis_id':aid, 'question':'What period is stated?',
                        'output_language':'en', 'client_request_id':'standalone-synthetic-question'}
            answer = _json(client.post(base + '/questions', headers=headers, json=question), 200)
            _require(answer['review_status'] == 'needs_review' and
                     any('DEVELOPMENT FIXTURE' in limitation for limitation in answer['limitations']),
                     'Development question was not labelled as simulation.')
            retry = _json(client.post(base + '/questions', headers=headers, json=question), 200)
            _require(retry == answer, 'Question retry did not reuse the same response.')
            result['question_interface'] = True
    finally:
        _require(client.delete(base, headers=headers).status_code == 204,
                 'Synthetic session deletion failed.')
        _require(client.get(base, headers=headers).status_code == 404,
                 'Deleted synthetic session remained accessible.')
        result['deleted'] = True
    return result


def run_demo(*, include_unavailable: bool = True, progress=None) -> dict:
    """Return privacy-safe counts/booleans after actual subprocess HTTP checks.

    No text, filenames, document IDs, source paths, tokens or credentials appear
    in the returned summary. Fixture success never represents model success.
    """
    summary = {'schema_version':1, 'mode':'explicit-development-fixture',
               'model_tested':False, 'real_http':True, 'uvicorn_subprocess':True,
               'journeys':{}, 'real_unavailable_checked':False, 'graceful_shutdown':False,
               'scan_ocr':{'tested':False,'skipped':True,'reason':'english_ocr_unavailable'}}
    passed = 0
    checks = 2 + int(include_unavailable)

    def checked():
        nonlocal passed
        passed += 1
        if progress:
            progress(f"[{'#' * passed}{'-' * (checks-passed)}] {passed}/{checks} standalone checks passed; real model not tested.")

    with tempfile.TemporaryDirectory(prefix='nyayalens-standalone-') as directory:
        runtime = Path(directory) / 'fixture-runtime'
        with _server(runtime, 'fixture') as client:
            health = _json(client.get('/api/v1/health'), 200)
            _require(health['mode'] == 'fixture' and health['ml'].get('simulation') is True and
                     health['ml']['available'] is False,
                     'Fixture health incorrectly claimed real ML readiness.')
            ocr = health.get('extraction', {}).get('ocr', {})
            scan_available = ocr.get('available') is True and 'eng' in ocr.get('languages', [])
            checks += int(scan_available)
            for kind in ('pdf', 'docx'):
                summary['journeys'][kind] = _journey(client, kind)
                checked()
            if scan_available:
                summary['journeys']['scan'] = _journey(client, 'pdf', scan=True)
                summary['scan_ocr'] = {'tested':True,'skipped':False,'reason':None}
                checked()
            elif progress:
                progress('English scan OCR skipped: local executable or eng asset unavailable; scan support not claimed.')
        _require(not list(runtime.glob('doc_*')), 'Temporary source artifacts remained after shutdown.')
        if include_unavailable:
            runtime = Path(directory) / 'real-unavailable-runtime'
            with _server(runtime, 'real') as client:
                health = _json(client.get('/api/v1/health'), 200)
                _require(health['mode'] == 'real' and health['ml']['available'] is False and
                         not health['ml'].get('simulation', False),
                         'Real unavailable mode unexpectedly used simulation.')
                summary['unavailable_journey'] = _journey(client, 'pdf', unavailable=True)
                summary['real_unavailable_checked'] = True
            _require(not list(runtime.glob('doc_*')), 'Unavailable-mode artifacts remained after shutdown.')
            checked()
        summary['graceful_shutdown'] = True
    summary['passed'] = True
    summary['checks_passed'] = passed
    summary['checks_total'] = checks
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json-output', type=Path, help='Write a new privacy-safe summary; existing files are preserved.')
    parser.add_argument('--skip-unavailable', action='store_true')
    parser.add_argument('--serve-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.serve_child:
        _child()
        return 0
    if args.json_output and args.json_output.exists():
        print('Standalone demo refused to overwrite an existing summary file.', file=sys.stderr)
        return 2
    try:
        summary = run_demo(include_unavailable=not args.skip_unavailable,
                           progress=lambda message: print(message, flush=True))
        encoded = json.dumps(summary, ensure_ascii=True, indent=2) + '\n'
        if args.json_output:
            with args.json_output.open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        print(encoded, end='', flush=True)
        return 0
    except (DemoError, httpx.HTTPError, OSError, ValueError, KeyError):
        # Deliberately suppress exception details to avoid private request echoes.
        print('Standalone demo failed a check; no model completion is claimed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
