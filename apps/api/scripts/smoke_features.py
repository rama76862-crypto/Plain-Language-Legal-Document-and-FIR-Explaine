"""Real synthetic comparison/Action Pack/export/deletion journey; no mock ML."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import time
from urllib.parse import urlparse

import httpx
from docx import Document


def run(base: str, *, allow_hosted: bool = False, verify_source: bool = False):
    if urlparse(base).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise SystemExit('Use a loopback test server and synthetic documents only.')
    sources = [
        ['The tenant must pay INR 500 within 15 days of receipt of the notice.',
         'The agreement renews automatically for 11 months unless cancelled 30 days before the end.',
         'The tenant waives the right to claim a refund of the deposit.'],
        ['The tenant must pay INR 750 within 10 days of receipt of the notice.',
         'The agreement renews automatically for 11 months unless cancelled 30 days before the end.',
         'Both parties must sign any written amendment.'],
    ]
    sessions = []
    started = time.monotonic()
    with httpx.Client(base_url=base, timeout=60, trust_env=False) as client:
        health = client.get('/api/v1/health'); health.raise_for_status()
        if health.json().get('mode') != 'real' or not health.json()['ml']['available']:
            raise RuntimeError('Real inference must be ready; fixture substitution is forbidden.')
        capabilities = client.get('/api/v1/capabilities'); capabilities.raise_for_status()
        hosted = capabilities.json()['processing']['external_ai_inference']
        if hosted and not allow_hosted:
            raise SystemExit('Pass --allow-hosted to consent to Groq processing this synthetic probe.')
        print('[1/8] real processing mode confirmed', flush=True)
        try:
            for paragraphs in sources:
                document = Document()
                for text in paragraphs: document.add_paragraph(text)
                stream = io.BytesIO(); document.save(stream)
                response = client.post('/api/v1/documents',
                    files={'file': ('synthetic-version.docx', stream.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')},
                    data={'processing_consent': 'true', 'external_ai_consent': str(allow_hosted).lower(), 'input_language': 'en', 'document_type': 'agreement'})
                response.raise_for_status(); uploaded = response.json()
                path = '/api/v1/documents/' + uploaded['document_id']
                headers = {'X-Session-Token': uploaded['session_token']}
                sessions.append((uploaded, path, headers))
                deadline = time.monotonic() + 125
                while True:
                    response = client.get(path, headers=headers); response.raise_for_status()
                    metadata = response.json()
                    if metadata['status'] == 'failed': raise RuntimeError('Synthetic native extraction failed.')
                    if metadata['extraction_ready']: break
                    if time.monotonic() > deadline: raise TimeoutError('Extraction timeout')
                    time.sleep(.2)
                response = client.get(path + '/extraction', headers=headers); response.raise_for_status()
                clauses = response.json()['clauses']
                assert [c['reviewed_text'].strip() for c in clauses] == paragraphs
                response = client.patch(path + '/extraction', headers=headers, json={
                    'expected_revision': uploaded['revision'], 'corrections': [], 'input_language': 'en', 'document_type': 'agreement'})
                response.raise_for_status(); uploaded['revision'] = response.json()['revision']
            print('[2/8] two real DOCX files extracted, exact text checked and reviewed', flush=True)
            a, path, headers = sessions[0]; b, _, _ = sessions[1]
            response = client.post(path + '/analyses', headers=headers, json={'expected_revision': a['revision'], 'output_language': 'en'})
            response.raise_for_status(); aid = response.json()['analysis_id']; analysis_path = path + '/analyses/' + aid
            deadline = time.monotonic() + 600
            while True:
                response = client.get(analysis_path, headers=headers); response.raise_for_status(); snapshot = response.json()
                if snapshot['status'] not in {'queued', 'running'}: break
                if time.monotonic() > deadline: raise TimeoutError('Real analysis timeout')
                time.sleep(.4)
            result = snapshot.get('result')
            if not result or result['coverage']['analysed'] != 3:
                print(json.dumps({'status': snapshot['status'], 'coverage': (result or {}).get('coverage'),
                                  'failed_clauses': (result or {}).get('failed_clauses'),
                                  'warnings': (result or {}).get('warnings')}), flush=True)
                raise RuntimeError('Real model did not explain all three synthetic clauses; no success claimed.')
            print('[3/8] real model processed 3/3 clauses; semantic review remains required', flush=True)
            response = client.get(analysis_path + '/action-pack', headers=headers); response.raise_for_status(); pack = response.json()
            assert any(x['statement'] == sources[0][0] for x in pack['checklist'])
            assert pack['lawyer_questions']
            print('[4/8] source obligation checklist and legal-aid questions verified', flush=True)
            response = client.post(path + '/compare', headers={**headers, 'X-Compare-Session-Token': b['session_token']}, json={
                'document_b_id': b['document_id'], 'expected_revision_a': a['revision'], 'expected_revision_b': b['revision']})
            response.raise_for_status(); comparison = response.json()
            assert comparison['unchanged_passages'] == 1
            assert any(c['before'] and c['after'] and 'INR 500' in c['before']['quote'] and 'INR 750' in c['after']['quote'] for c in comparison['changes'])
            print('[5/8] comparison preserves exact INR 500 to INR 750 source passages', flush=True)
            check = None
            if verify_source:
                response = client.post(analysis_path + '/verify-source', headers=headers, json={'external_ai_consent': True})
                response.raise_for_status(); check = response.json()
                print(f"[6/8] real optional source checker: {check['status']}, {check['checked_claims']} claims checked", flush=True)
            else: print('[6/8] external source checker intentionally not requested', flush=True)
            report = client.get(analysis_path + '/report', headers=headers); report.raise_for_status()
            assert report.json()['action_pack']['checklist'] == pack['checklist']
            if check: assert report.json()['selected_source_verification'] == check
            for format_name in ('md', 'html'):
                response = client.get(analysis_path + '/report', headers=headers, params={'format': format_name}); response.raise_for_status()
                assert 'Action Pack' in response.text
            print('[7/8] JSON/Markdown/HTML review exports contain the actual Action Pack', flush=True)
            return {'real_inference': True, 'hosted': hosted, 'coverage': result['coverage'],
                    'comparison_changes': len(comparison['changes']), 'unchanged_passages': comparison['unchanged_passages'],
                    'checklist_items': len(pack['checklist']), 'source_verification': check,
                    'independent_review': False, 'seconds': round(time.monotonic() - started, 2),
                    'synthetic_analysis_result': result}
        finally:
            for _, path, headers in reversed(sessions):
                response = client.delete(path, headers=headers)
                assert response.status_code == 204
                assert client.get(path, headers=headers).status_code == 404
            print('[8/8] both synthetic sessions deleted; authenticated reads return 404', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--allow-hosted', action='store_true', help='Consent to Groq processing these synthetic files')
    parser.add_argument('--verify-source', action='store_true', help='Separately consent to sending selected synthetic claims/excerpts to Cloudflare')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run(args.base_url, allow_hosted=args.allow_hosted, verify_source=args.verify_source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='synthetic_analysis_result'}), flush=True)


if __name__ == '__main__': main()
