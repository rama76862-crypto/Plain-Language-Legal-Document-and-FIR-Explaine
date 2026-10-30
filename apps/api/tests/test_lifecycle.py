"""Focused lifecycle tests with synthetic text and private temp directories."""
import asyncio
import os
import time
import subprocess
import sys
from unittest.mock import patch

import pytest

from apps.api.config import Settings
from apps.api.jobs import BoundedJobs
from apps.api.schemas import ApiError, Clause, ReviewRequest, SourceRef
from apps.api.sessions import SessionStore


def run(coroutine):
    return asyncio.run(coroutine)


def store_at(tmp_path):
    return SessionStore(Settings(runtime_dir=tmp_path / 'runtime'))


def ready(record):
    record.clauses = [Clause(clause_id='c1', source_text='Synthetic original.',
                            reviewed_text='Synthetic original.',
                            source_ref=SourceRef(page_number=1, bbox=[1, 2, 3, 4]))]
    record.extraction_ready = True
    record.status = 'awaiting_review'


def test_token_scope_source_paths_and_expiry(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        await store.startup_cleanup()
        a, token_a = await store.create('../../private.pdf', 'pdf', 'en', 'agreement')
        b, token_b = await store.create('b.pdf', 'pdf', 'en', 'agreement')
        assert token_a != token_b and token_a not in repr(a)
        assert a.path.parent.parent == store.root and a.path.name == 'source.pdf'
        assert a.token_hash != token_a
        assert await store.get(a.document_id, token_a) is a
        for document_id, token in [(a.document_id, token_b), ('missing', token_a), (b.document_id, None)]:
            with pytest.raises(ApiError) as err:
                await store.get(document_id, token)
            assert err.value.code == 'NOT_FOUND' and err.value.status == 404
        expiry = a.expires_at
        await store.get(a.document_id, token_a, touch=False)
        assert a.expires_at == expiry
        a.expires_at = time.time() - 1
        with pytest.raises(ApiError):
            await store.get(a.document_id, token_a)
        a.analyses['old-language'] = {'status': 'complete'}
        assert await store.expire() == [['old-language']]
        assert a.deleted and a.document_id not in store.records
    run(scenario())


def test_review_confirmation_correction_atomic_conflict_and_cleanup(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, _ = await store.create('a.pdf', 'pdf', 'en', 'agreement')
        ready(record)
        unchanged = ReviewRequest(expected_revision=1, corrections=[], input_language='en', document_type='agreement')
        assert not await store.review(record, unchanged)
        assert record.revision == record.reviewed_revision == 1
        record.analyses['english'] = {'status': 'complete'}
        record.analyses['hindi'] = {'status': 'complete'}
        record.question_cache['question'] = {'answer': 'synthetic'}
        changed = ReviewRequest(expected_revision=1, corrections=[{'clause_id': 'c1', 'text': 'Synthetic correction.'}], input_language='en', document_type='agreement')
        assert await store.review(record, changed)
        assert record.revision == record.reviewed_revision == 2
        assert record.clauses[0].source_text == 'Synthetic original.'
        assert record.clauses[0].reviewed_text == 'Synthetic correction.'
        assert record.clauses[0].source_ref.bbox is None
        assert record.invalidated_analysis_ids == {'english', 'hindi'}
        assert not record.analyses and not record.question_cache
        with pytest.raises(ApiError) as err:
            await store.review(record, unchanged)
        assert err.value.code == 'REVISION_CONFLICT'
        record.path.write_bytes(b'synthetic file')
        directory = record.path.parent
        ids = await store.delete(record)
        assert ids == ['english', 'hindi']
        assert record.deleted and not directory.exists() and not record.clauses
        assert await store.delete(record) == []
    run(scenario())


def test_review_rejects_active_unknown_duplicate_and_blank(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, _ = await store.create('a.docx', 'docx', 'unknown', 'other')
        request = ReviewRequest(expected_revision=1, input_language='en', document_type='agreement')
        with pytest.raises(ApiError) as err:
            await store.review(record, request)
        assert err.value.code == 'EXTRACTION_NOT_READY'
        ready(record)
        record.analyses['a'] = {'status': 'running'}
        with pytest.raises(ApiError):
            await store.review(record, request)
        record.analyses.clear()
        for corrections in [[{'clause_id': 'missing', 'text': 'x'}], [{'clause_id': 'c1', 'text': ' '}], [{'clause_id': 'c1', 'text': 'a'}, {'clause_id': 'c1', 'text': 'b'}]]:
            bad = request.model_copy(update={'corrections': ReviewRequest(expected_revision=1, input_language='en', document_type='agreement', corrections=corrections).corrections})
            with pytest.raises(ApiError):
                await store.review(record, bad)
        assert record.revision == 1 and record.reviewed_revision is None
    run(scenario())


def test_concurrent_revision_one_winner(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, _ = await store.create('a.pdf', 'pdf', 'en', 'agreement')
        ready(record)
        requests = [ReviewRequest(expected_revision=1, input_language='en', document_type='agreement', corrections=[{'clause_id': 'c1', 'text': text}]) for text in ['first', 'second']]
        results = await asyncio.gather(*(store.review(record, request) for request in requests), return_exceptions=True)
        assert sum(result is True for result in results) == 1
        assert sum(isinstance(result, ApiError) for result in results) == 1
        assert record.revision == 2
    run(scenario())


def test_startup_cleanup_preserves_unmanaged_paths(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        store.root.mkdir()
        unrelated = store.root / 'keep.txt'
        unrelated.write_text('synthetic')
        outside = tmp_path / 'outside'
        outside.mkdir()
        (outside / 'keep.txt').write_text('outside')
        managed = store.root / ('doc_' + 'a' * 32)
        managed.mkdir()
        (managed / 'source.pdf').write_bytes(b'synthetic')
        await store.startup_cleanup()
        assert not managed.exists() and unrelated.exists() and (outside / 'keep.txt').exists()
        with pytest.raises(ValueError):
            store._safe_directory(outside)
        record, _ = await store.create('a.pdf', 'pdf', 'en', 'agreement')
        with pytest.raises(RuntimeError):
            await store.startup_cleanup()
        # Expiry scan must recheck the TTL under the document lock.
        assert await store.delete(record, expired_before=time.time() - 100) == []
        assert not record.deleted
    run(scenario())


def test_bounded_jobs_queue_busy_failure_and_close():
    async def scenario():
        jobs = BoundedJobs(1, 1)
        gate = asyncio.Event()
        started = asyncio.Event()
        async def blocked():
            started.set()
            await gate.wait()
            return 'done'
        first = await jobs.submit(blocked)
        await started.wait()
        second = await jobs.submit(blocked)
        with pytest.raises(ApiError) as err:
            await jobs.submit(blocked)
        assert err.value.code == 'MODEL_BUSY'
        gate.set()
        assert await first == await second == 'done'
        async def failure():
            raise ValueError('synthetic failure')
        failed = await jobs.submit(failure)
        with pytest.raises(ValueError):
            await failed
        await jobs.close()
        with pytest.raises(ApiError):
            await jobs.submit(blocked)
    run(scenario())


def test_windows_delete_failure_retains_only_bounded_cleanup_metadata(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, token = await store.create('private.pdf', 'pdf', 'en', 'agreement')
        ready(record)
        record.analysis_ids = {'a-en', 'a-hi'}
        record.path.write_bytes(b'synthetic')
        directory = record.path.parent
        with patch('apps.api.sessions.shutil.rmtree', side_effect=PermissionError('sharing violation')):
            assert await store.delete(record) == ['a-en', 'a-hi']
            assert record.deleted and not record.clauses and not record.token_hash
            assert record.document_id not in store.records
            assert store.cleanup_status() == {'pending': 1, 'exhausted': 0}
            assert token not in repr(store.local_cleanup) and 'private.pdf' not in repr(store.local_cleanup)
            for _ in range(4):
                store.local_cleanup[directory]['next'] = 0
                await store.retry_cleanup()
            assert store.cleanup_status() == {'pending': 0, 'exhausted': 1}
            assert store.local_cleanup[directory]['attempts'] == 5
        # Exhausted work is not silently declared successful; operator may retry
        # explicitly after resolving locks, or restart safe orphan cleanup.
        store.local_cleanup[directory]['exhausted'] = False
        store.local_cleanup[directory]['next'] = 0
        await store.retry_cleanup()
        assert store.cleanup_status() == {'pending': 0, 'exhausted': 0}
        assert not directory.exists()
    run(scenario())


def test_session_admission_reserves_cleanup_capacity(tmp_path, monkeypatch):
    async def scenario():
        monkeypatch.setattr('apps.api.sessions.MAX_LOCAL_CLEANUPS', 2)
        store = store_at(tmp_path)
        first, _ = await store.create('one.pdf', 'pdf', 'en', 'agreement')
        second, _ = await store.create('two.pdf', 'pdf', 'en', 'agreement')
        with pytest.raises(ApiError) as err:
            await store.create('three.pdf', 'pdf', 'en', 'agreement')
        assert err.value.code == 'MODEL_BUSY'
        with patch('apps.api.sessions.shutil.rmtree', side_effect=PermissionError()):
            await store.delete(first)
            await store.delete(second)
        assert len(store.local_cleanup) == 2 and not store.records
        with pytest.raises(ApiError):
            await store.create('four.pdf', 'pdf', 'en', 'agreement')
    run(scenario())


def test_linked_runtime_root_rejected_before_resolution(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Creating local symlinks requires privileges on this Windows host')
    settings = Settings(runtime_dir=tmp_path / 'normal')
    settings.runtime_dir = link
    with pytest.raises(ValueError):
        SessionStore(settings)


def test_runtime_ancestor_link_detection_without_os_privileges(tmp_path, monkeypatch):
    settings = Settings(runtime_dir=tmp_path / 'linked-parent' / 'runtime')
    original = type(settings.runtime_dir).is_symlink
    ancestor = settings.runtime_dir.parent
    monkeypatch.setattr(type(settings.runtime_dir), 'is_symlink',
                        lambda path: path == ancestor or original(path))
    with pytest.raises(ValueError, match='ancestors'):
        SessionStore(settings)


def test_runtime_lock_conflict_release_and_cleanup_preserves_lock(tmp_path):
    async def scenario():
        first, second = store_at(tmp_path), store_at(tmp_path)
        await first.acquire_runtime()
        try:
            lock_path = first.root / '.be1.lock'
            assert lock_path.exists()
            # This models a second server starting before its port bind fails:
            # it must never reach orphan cleanup on the first server's files.
            with pytest.raises(RuntimeError, match='already owned'):
                await second.acquire_runtime()
            managed = first.root / ('doc_' + 'b' * 32)
            managed.mkdir()
            (managed / 'source.pdf').write_bytes(b'synthetic orphan')
            await first.startup_cleanup()
            assert lock_path.exists() and not managed.exists()
            with pytest.raises(RuntimeError):
                await second.acquire_runtime()
        finally:
            await first.release_runtime()
        await second.acquire_runtime()
        await second.release_runtime()
        await second.release_runtime()  # shutdown remains idempotent
    run(scenario())


def test_runtime_lock_excludes_second_process(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        script = '''
import asyncio, sys
from pathlib import Path
from apps.api.config import Settings
from apps.api.sessions import SessionStore
async def main():
    store = SessionStore(Settings(runtime_dir=Path(sys.argv[1])))
    try:
        await store.acquire_runtime()
    except RuntimeError:
        return 3
    await store.release_runtime()
    return 0
sys.exit(asyncio.run(main()))
'''
        await store.acquire_runtime()
        try:
            blocked = await asyncio.to_thread(subprocess.run, [sys.executable, '-c', script, str(store.root)], capture_output=True, timeout=10)
            assert blocked.returncode == 3
        finally:
            await store.release_runtime()
        released = await asyncio.to_thread(subprocess.run, [sys.executable, '-c', script, str(store.root)], capture_output=True, timeout=10)
        assert released.returncode == 0
    run(scenario())


def test_concurrent_session_admission_is_atomic(tmp_path, monkeypatch):
    async def scenario():
        monkeypatch.setattr('apps.api.sessions.MAX_SESSIONS', 2)
        store = store_at(tmp_path)
        await store._lock.acquire()
        tasks = [asyncio.create_task(store.create(f'synthetic-{i}.pdf', 'pdf', 'en', 'agreement')) for i in range(12)]
        await asyncio.sleep(0)
        store._lock.release()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert sum(isinstance(result, tuple) for result in results) == 2
        assert sum(isinstance(result, ApiError) for result in results) == 10
        assert len(store.records) == 2
        assert len(list(store.root.glob('doc_*'))) == 2
    run(scenario())


def test_canceled_creation_allocates_no_orphan(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        await store._lock.acquire()
        task = asyncio.create_task(store.create('synthetic.pdf', 'pdf', 'en', 'agreement'))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        store._lock.release()
        assert not store.records and not store.root.exists()
    run(scenario())


def test_interrupted_delete_enrolls_cleanup_before_await(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, token = await store.create('partial.pdf', 'pdf', 'en', 'agreement')
        record.path.write_bytes(b'synthetic partial upload')
        directory = record.path.parent
        await store._cleanup_lock.acquire()
        deletion = asyncio.create_task(store.delete(record))
        await asyncio.sleep(0)
        assert record.deleted and record.document_id not in store.records
        assert directory in store.local_cleanup
        deletion.cancel()
        with pytest.raises(asyncio.CancelledError):
            await deletion
        store._cleanup_lock.release()
        with pytest.raises(ApiError):
            await store.get(record.document_id, token)
        await store.retry_cleanup()
        assert not directory.exists() and not store.local_cleanup
    run(scenario())


def test_restart_recovers_partial_upload_and_locked_orphan(tmp_path):
    async def scenario():
        first = store_at(tmp_path)
        record, _ = await first.create('partial.docx', 'docx', 'en', 'other')
        record.path.write_bytes(b'synthetic interrupted archive')
        directory = record.path.parent
        restarted = store_at(tmp_path)
        await restarted.acquire_runtime()
        try:
            with patch('apps.api.sessions.shutil.rmtree', side_effect=PermissionError('synthetic lock')):
                await restarted.startup_cleanup()
            assert restarted.cleanup_status() == {'pending': 1, 'exhausted': 0}
            restarted.local_cleanup[directory]['next'] = 0
            await restarted.retry_cleanup()
            assert not directory.exists() and not restarted.records
            assert (restarted.root / '.be1.lock').exists()
        finally:
            await restarted.release_runtime()
    run(scenario())


def test_expiry_rechecks_after_concurrent_touch(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, _ = await store.create('synthetic.pdf', 'pdf', 'en', 'agreement')
        record.expires_at = time.time() - 1
        await record.lock.acquire()
        expiring = asyncio.create_task(store.expire())
        await asyncio.sleep(0)
        # An already-admitted user action refreshes its session while holding
        # the same lock; expiry must recheck instead of deleting a fresh session.
        record.expires_at = store._expiry()
        record.lock.release()
        await expiring
        assert not record.deleted and record.document_id in store.records
        assert record.path.parent.exists()
    run(scenario())


def test_cancel_running_job_cleans_up_without_killing_worker():
    async def scenario():
        jobs = BoundedJobs(1, 2)
        started, cleaned = asyncio.Event(), asyncio.Event()
        async def blocked():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        first = await jobs.submit(blocked)
        await started.wait()
        first.cancel()
        await asyncio.wait_for(cleaned.wait(), 1)
        async def succeeds():
            return 'next extraction'
        next_job = await jobs.submit(succeeds)
        assert await asyncio.wait_for(next_job, 1) == 'next extraction'
        await asyncio.wait_for(jobs.queue.join(), 1)
        assert not jobs.running
        await jobs.close()
    run(scenario())


def test_canceled_pending_job_frees_queue_slot_without_running():
    async def scenario():
        jobs = BoundedJobs(1, 1)
        started, release = asyncio.Event(), asyncio.Event()
        executions = []
        async def blocked():
            started.set()
            await release.wait()
        first = await jobs.submit(blocked)
        await started.wait()
        async def pending():
            executions.append('should not execute')
        canceled = await jobs.submit(pending)
        canceled.cancel()
        async def replacement():
            return 'replacement'
        queued = await jobs.submit(replacement)
        release.set()
        await first
        assert await queued == 'replacement' and executions == []
        await asyncio.wait_for(jobs.queue.join(), 1)
        await jobs.close()
    run(scenario())


def test_self_canceling_and_synchronous_failure_preserve_worker():
    async def scenario():
        jobs = BoundedJobs(1, 1)
        async def self_cancel():
            raise asyncio.CancelledError()
        canceled = await jobs.submit(self_cancel)
        with pytest.raises(asyncio.CancelledError):
            await canceled
        def bad_factory():
            raise ValueError('synthetic factory error')
        failed = await jobs.submit(bad_factory)
        with pytest.raises(ValueError):
            await failed
        async def succeeds():
            return 1
        assert await (await jobs.submit(succeeds)) == 1
        await jobs.close()
    run(scenario())


def test_close_cancels_running_and_pending_jobs():
    async def scenario():
        jobs = BoundedJobs(1, 2)
        started, cleaned = asyncio.Event(), asyncio.Event()
        async def blocked():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        first = await jobs.submit(blocked)
        await started.wait()
        queued = await jobs.submit(blocked)
        await asyncio.wait_for(jobs.close(), 1)
        assert first.cancelled() and queued.cancelled() and cleaned.is_set()
        assert not jobs.running and not jobs.workers
        await asyncio.wait_for(jobs.queue.join(), 1)
        await jobs.close()
    run(scenario())


def test_real_open_source_handle_delete_and_recovery(tmp_path):
    async def scenario():
        store = store_at(tmp_path)
        record, _ = await store.create('synthetic.pdf', 'pdf', 'en', 'agreement')
        record.path.write_bytes(b'synthetic original bytes')
        directory = record.path.parent
        with record.path.open('rb') as active_download:
            await store.delete(record)
            assert record.deleted and record.document_id not in store.records
            if os.name == 'nt':
                # Standard Windows file handles deny delete sharing. Public
                # deletion still succeeds, while physical cleanup is honest.
                assert directory.exists()
                assert store.cleanup_status() == {'pending': 1, 'exhausted': 0}
            else:
                assert not directory.exists()
            assert active_download.read() == b'synthetic original bytes'
        if directory in store.local_cleanup:
            store.local_cleanup[directory]['next'] = 0
        await store.retry_cleanup()
        assert not directory.exists() and not store.local_cleanup
    run(scenario())


def test_bounded_jobs_never_exceeds_worker_concurrency():
    async def scenario():
        jobs = BoundedJobs(2, 6)
        release, both_started = asyncio.Event(), asyncio.Event()
        active = peak = 0
        async def counted():
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 2:
                both_started.set()
            try:
                await release.wait()
            finally:
                active -= 1
        futures = [await jobs.submit(counted) for _ in range(6)]
        await asyncio.wait_for(both_started.wait(), 1)
        futures.extend([await jobs.submit(counted) for _ in range(2)])
        with pytest.raises(ApiError):
            await jobs.submit(counted)
        release.set()
        await asyncio.gather(*futures)
        assert peak == 2 and active == 0
        await jobs.close()
    run(scenario())
