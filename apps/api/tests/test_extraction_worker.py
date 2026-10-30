"""Real subprocess limits, cancellation, private protocol and recovery."""
import asyncio
import os
from pathlib import Path
import sys

import psutil
import pytest
from apps.api.config import Settings
from apps.api.extraction_worker import extract_isolated
from apps.api.schemas import ApiError
from apps.api.tests.test_api import pdf_bytes,docx_bytes


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['pdf','docx'])
async def test_real_parser_isolated_refs_and_safe_progress(tmp_path,kind):
    path=tmp_path/('synthetic.'+kind); path.write_bytes(pdf_bytes() if kind=='pdf' else docx_bytes())
    progress=[]; pids=[]
    result=await extract_isolated(path,kind,'en',Settings(runtime_dir=tmp_path/'runtime'),progress.append,on_started=pids.append)
    assert result['clauses'] and progress and pids[0]!=os.getpid()
    assert not psutil.pid_exists(pids[0])
    assert result['clauses'][0].source_ref.page_number==(1 if kind=='pdf' else None)
    assert 'SYNTHETIC' not in repr(progress)


@pytest.mark.asyncio
async def test_hard_timeout_kills_parser_and_ocr_descendant(tmp_path):
    settings=Settings(runtime_dir=tmp_path/'runtime',extraction_timeout_seconds=.5)
    marker=tmp_path/'descendant.pid'; pids=[]
    script="import subprocess,sys,time; from pathlib import Path; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(60)"
    with pytest.raises(ApiError) as error:
        await extract_isolated(tmp_path/'unused','pdf','en',settings,
            command=[sys.executable,'-c',script,str(marker)],on_started=pids.append)
    assert error.value.code=='EXTRACTION_TIMEOUT' and error.value.status==504
    assert not psutil.pid_exists(pids[0])
    assert marker.exists(), 'Child startup must happen before the hard timeout in this test'
    child_pid=int(marker.read_text())
    for _ in range(40):
        if not psutil.pid_exists(child_pid): break
        await asyncio.sleep(.025)
    assert not psutil.pid_exists(child_pid)


@pytest.mark.asyncio
async def test_cancellation_kills_running_parser(tmp_path):
    started=asyncio.Event(); pids=[]
    def ready(pid): pids.append(pid); started.set()
    task=asyncio.create_task(extract_isolated(tmp_path/'unused','pdf','en',Settings(runtime_dir=tmp_path/'runtime'),
        command=[sys.executable,'-c','import time; time.sleep(60)'],on_started=ready))
    await started.wait(); task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert not psutil.pid_exists(pids[0])


@pytest.mark.asyncio
async def test_bad_protocol_and_native_stderr_are_not_exposed(tmp_path,capsys):
    secret='SYNTHETIC_PRIVATE_PROCESS_DIAGNOSTIC'
    script=f"import sys; sys.stderr.write('{secret}'); print('{secret}')"
    with pytest.raises(ApiError) as error:
        await extract_isolated(tmp_path/'unused','pdf','en',Settings(runtime_dir=tmp_path/'runtime'),command=[sys.executable,'-c',script])
    assert error.value.code=='EXTRACTION_FAILED' and secret not in error.value.message
    captured=capsys.readouterr(); assert secret not in captured.out+captured.err


@pytest.mark.asyncio
async def test_windows_memory_limit_and_next_job_recovery(tmp_path):
    if os.name!='nt': pytest.skip('Actual Windows Job Object memory limit check')
    pids=[]
    with pytest.raises(ApiError) as error:
        await extract_isolated(tmp_path/'unused','pdf','en',Settings(runtime_dir=tmp_path/'runtime',extraction_memory_mb=80),
            command=[sys.executable,'-c','data=bytearray(256*1024*1024)'],on_started=pids.append)
    assert error.value.code=='EXTRACTION_FAILED' and not psutil.pid_exists(pids[0])
    path=tmp_path/'synthetic.pdf'; path.write_bytes(pdf_bytes())
    result=await extract_isolated(path,'pdf','en',Settings(runtime_dir=tmp_path/'runtime'))
    assert result['clauses']


@pytest.mark.asyncio
async def test_isolated_parser_errors_keep_expected_code(tmp_path):
    path=tmp_path/'bad.docx'; path.write_bytes(b'not a docx')
    with pytest.raises(ApiError) as error:
        await extract_isolated(path,'docx','en',Settings(runtime_dir=tmp_path/'runtime'))
    assert error.value.code=='EXTRACTION_FAILED'
