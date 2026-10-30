"""Actual loopback HTTP/Uvicorn acceptance; fixture mode is not model evidence."""
import json
import pymupdf
from apps.api.scripts.standalone_demo import image_only_pdf, main, run_demo


def test_scan_fixture_is_image_only_and_has_real_page():
    with pymupdf.open(stream=image_only_pdf(), filetype='pdf') as scan:
        assert len(scan) == 1
        assert scan[0].get_text().strip() == ''
        assert len(scan[0].get_images()) == 1


def test_standalone_actual_uvicorn_native_journeys_and_explicit_unavailable(capsys):
    summary = run_demo()
    assert summary['passed'] and summary['real_http'] and summary['uvicorn_subprocess']
    assert summary['model_tested'] is False
    assert summary['graceful_shutdown'] and summary['real_unavailable_checked']
    assert summary['checks_passed'] == summary['checks_total']
    if summary['scan_ocr']['tested']:
        assert summary['scan_ocr']['skipped'] is False
        scan = summary['journeys']['scan']
        assert scan['scan_ocr'] and not scan['native_extraction']
        assert scan['clause_count'] > 0 and scan['review'] and scan['source'] and scan['deleted']
        assert scan['model_tested'] is False
        assert summary['checks_total'] == 4
    else:
        assert summary['scan_ocr']['skipped'] is True
        assert summary['scan_ocr']['reason'] == 'english_ocr_unavailable'
        assert 'scan' not in summary['journeys']
        assert summary['checks_total'] == 3
    for kind in ('pdf','docx'):
        journey = summary['journeys'][kind]
        assert all(journey[field] for field in ('native_extraction','review','source','analysis_interface','question_interface','deleted'))
        assert journey['clause_count'] > 0 and journey['simulation'] is True
        assert journey['model_tested'] is False
    unavailable = summary['unavailable_journey']
    assert unavailable['unavailable_error'] and unavailable['deleted']
    assert not unavailable['simulation'] and not unavailable['question_interface']
    encoded = json.dumps(summary)
    assert all(word not in encoded for word in ('session_token','document_id','filename','reviewed_text','source_text','credentials'))
    assert capsys.readouterr().out == ''


def test_summary_output_preserves_existing_file(tmp_path,capsys):
    output = tmp_path/'summary.json'
    output.write_text('existing',encoding='utf-8')
    assert main(['--json-output',str(output)]) == 2
    assert output.read_text(encoding='utf-8') == 'existing'
    assert 'overwrite' in capsys.readouterr().err
