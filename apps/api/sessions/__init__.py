"""Single-process, document-scoped temporary sessions.

Automatic status polling should use ``touch=False``. Explicit user actions
extend retention; background processing does not. All late writers must hold
record.lock and check record.deleted plus their captured revision.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import secrets
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from typing import BinaryIO

from apps.api.config import Settings
from apps.api.schemas import ApiError, Clause, ReviewRequest

_DIRECTORY = re.compile(r"doc_[a-f0-9]{32}\Z")
MAX_SESSIONS = 128
MAX_LOCAL_CLEANUPS = 128


@dataclass(repr=False)
class DocumentRecord:
    document_id: str
    token_hash: str
    filename: str
    kind: str
    input_language: str
    document_type: str
    path: Path
    expires_at: float
    revision: int = 1
    reviewed_revision: int | None = None
    status: str = 'extracting'
    clauses: list[Clause] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extraction_ready: bool = False
    extraction_progress: dict[str, Any] = field(default_factory=dict)
    analyses: dict[str, dict[str, Any]] = field(default_factory=dict)
    question_cache: dict[str, Any] = field(default_factory=dict)
    verification_cache: dict[str, Any] = field(default_factory=dict)
    analysis_ids: set[str] = field(default_factory=set)
    invalidated_analysis_ids: set[str] = field(default_factory=set)
    deleted: bool = False
    inference_mode: str = 'local'
    external_ai_consent: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._raw_root = settings.runtime_dir.absolute()
        self._validate_root()
        self.root = self._raw_root.resolve()
        self.records: dict[str, DocumentRecord] = {}
        self._lock = asyncio.Lock()
        self._cleanup_lock = asyncio.Lock()
        # Metadata only: managed server paths and retry counters, never tokens,
        # source names, document text or exception strings.
        self.local_cleanup: dict[Path, dict[str, Any]] = {}
        self._runtime_lock: BinaryIO | None = None

    async def acquire_runtime(self) -> None:
        """Reserve this runtime across processes before any orphan cleanup.

        The lock file stays on disk permanently: unlinking it would let another
        process lock a different inode while this process still owns its handle.
        The API lifespan must release the handle in its outermost finally block.
        """
        if self._runtime_lock is not None:
            return
        self._validate_root()
        self.root.mkdir(parents=True, exist_ok=True)
        lock_path = self.root / '.be1.lock'
        if lock_path.is_symlink() or getattr(lock_path, 'is_junction', lambda: False)():
            raise ValueError('Runtime lock must not be a link')
        handle = lock_path.open('a+b')
        try:
            # msvcrt locks byte ranges. Ensure the first byte exists, then lock
            # from offset zero rather than append mode's initial file position.
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise RuntimeError('Runtime directory is already owned by another API process.') from None
        except BaseException:
            handle.close()
            raise
        self._runtime_lock = handle

    async def release_runtime(self) -> None:
        handle, self._runtime_lock = self._runtime_lock, None
        if handle is None:
            return
        try:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def _validate_root(self) -> None:
        for candidate in (self._raw_root, *self._raw_root.parents):
            if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
                raise ValueError('Runtime root and ancestors must not be links')
        if self._raw_root == self._raw_root.parent or (self._raw_root / '.git').exists():
            raise ValueError('Unsafe runtime root')

    def _expiry(self) -> float:
        return time.time() + self.settings.session_ttl_minutes * 60

    @staticmethod
    def _missing() -> ApiError:
        return ApiError('NOT_FOUND', 'Document not found or session expired.', 404)

    def _safe_directory(self, path: Path) -> Path:
        """Allow only direct, server-generated, non-link runtime children."""
        self._validate_root()
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Runtime links are not allowed')
        resolved = path.resolve()
        if resolved.parent != self.root or not _DIRECTORY.fullmatch(path.name):
            raise ValueError('Cleanup target is outside the managed runtime directory')
        return resolved

    async def startup_cleanup(self) -> None:
        # Refuse a filesystem root, repository directory, or linked root. Only
        # managed doc_<hex> children are considered; unrelated files survive.
        self._validate_root()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.records:
            raise RuntimeError('Startup cleanup cannot run on active sessions')
        managed = [child for child in self.root.iterdir() if _DIRECTORY.fullmatch(child.name)]
        if len(managed) > MAX_LOCAL_CLEANUPS:
            raise ValueError('Too many runtime orphans; operator cleanup is required')
        for child in managed:
            if not _DIRECTORY.fullmatch(child.name):
                continue
            target = self._safe_directory(child)
            if target.is_dir():
                self._schedule_local_cleanup(target)
        await self.retry_cleanup()

    def _schedule_local_cleanup(self, directory: Path) -> None:
        self.local_cleanup.setdefault(directory, {'attempts': 0, 'next': time.monotonic(), 'exhausted': False})

    def cleanup_status(self) -> dict[str, int]:
        return {
            'pending': sum(not entry['exhausted'] for entry in self.local_cleanup.values()),
            'exhausted': sum(entry['exhausted'] for entry in self.local_cleanup.values()),
        }

    async def retry_cleanup(self) -> None:
        """Try due local removals, at most five attempts (2/4/8/16s delays).

        Exhausted entries remain visible and consume bounded capacity until
        restart/operator action. This deliberately never claims forensic erasure.
        """
        async with self._cleanup_lock:
            for directory, entry in list(self.local_cleanup.items()):
                if entry['exhausted'] or entry['next'] > time.monotonic():
                    continue
                entry['attempts'] += 1
                try:
                    target = self._safe_directory(directory)
                    if target.exists():
                        await asyncio.to_thread(shutil.rmtree, target)
                except (OSError, ValueError):
                    entry['exhausted'] = entry['attempts'] >= 5
                    entry['next'] = time.monotonic() + min(2 ** entry['attempts'], 30)
                else:
                    self.local_cleanup.pop(directory, None)

    async def create(self, filename: str, kind: str, input_language: str,
                     document_type: str) -> tuple[DocumentRecord, str]:
        if kind not in {'pdf', 'docx'}:
            raise ApiError('UNSUPPORTED_FILE', 'Only PDF and DOCX files are supported.', 415)
        async with self._lock:
            # Admission and allocation are one critical section: concurrent
            # creators waiting for this lock must not all pass a stale cap.
            if len(self.records) >= MAX_SESSIONS or len(self.records) + len(self.local_cleanup) >= MAX_LOCAL_CLEANUPS:
                raise ApiError('MODEL_BUSY', 'Temporary session capacity is full; retry after cleanup.', 429, True)
            self._validate_root()
            self.root.mkdir(parents=True, exist_ok=True)
            token = secrets.token_urlsafe(32)
            document_id = 'doc_' + secrets.token_hex(16)
            directory = self._safe_directory(self.root / document_id)
            directory.mkdir(mode=0o700)
            record = DocumentRecord(
                document_id=document_id,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                filename=filename, kind=kind, input_language=input_language,
                document_type=document_type, path=directory / ('source.' + kind),
                expires_at=self._expiry(),
            )
            self.records[document_id] = record
        return record, token

    async def get(self, document_id: str, token: str | None,
                  touch: bool = True) -> DocumentRecord:
        record = self.records.get(document_id)
        supplied = hashlib.sha256((token or '').encode()).hexdigest()
        expected = record.token_hash if record else '0' * 64
        valid = hmac.compare_digest(supplied, expected)
        if not record or not valid:
            raise self._missing()
        async with record.lock:
            if record.deleted or time.time() >= record.expires_at:
                raise self._missing()
            if touch:
                record.expires_at = self._expiry()
        return record

    async def review(self, record: DocumentRecord, request: ReviewRequest) -> bool:
        async with record.lock:
            if record.deleted or time.time() >= record.expires_at:
                raise self._missing()
            if request.expected_revision != record.revision:
                raise ApiError('REVISION_CONFLICT', 'Document changed; reload extraction before reviewing.', 409)
            if not record.extraction_ready:
                raise ApiError('EXTRACTION_NOT_READY', 'Extraction is not ready for review.', 409, True)
            if any(job.get('status') in {'queued', 'running', 'analysing'}
                   for job in record.analyses.values()):
                raise ApiError('REVISION_CONFLICT', 'Wait for active analysis before editing extraction.', 409)
            clauses = {clause.clause_id: clause for clause in record.clauses}
            ids = [correction.clause_id for correction in request.corrections]
            if len(set(ids)) != len(ids) or any(value not in clauses for value in ids):
                raise ApiError('INVALID_REQUEST', 'Corrections must name unique existing clause IDs.', 422)
            if any(not correction.text.strip() for correction in request.corrections):
                raise ApiError('INVALID_REQUEST', 'Corrected clause text cannot be blank.', 422)
            corrected = {c.clause_id: c.text for c in request.corrections}
            total = sum(len(corrected.get(c.clause_id, c.reviewed_text)) for c in record.clauses)
            if total > self.settings.max_extracted_chars:
                raise ApiError('FILE_TOO_LARGE', 'Reviewed text exceeds the configured character limit.', 413)
            changed = (record.input_language != request.input_language
                       or record.document_type != request.document_type
                       or any(clauses[c.clause_id].reviewed_text != c.text for c in request.corrections))
            if changed:
                for correction in request.corrections:
                    clause = clauses[correction.clause_id]
                    if clause.reviewed_text != correction.text:
                        clause.reviewed_text = correction.text
                        clause.source_ref.bbox = None
                        clause.review_required = False
                record.analysis_ids.update(record.analyses)
                record.invalidated_analysis_ids.update(record.analysis_ids)
                record.analyses.clear()
                record.question_cache.clear()
                record.revision += 1
            record.input_language = request.input_language
            record.document_type = request.document_type
            record.reviewed_revision = record.revision
            record.status = 'awaiting_review'
            record.expires_at = self._expiry()
            return changed

    async def delete(self, record: DocumentRecord, *, expired_before: float | None = None) -> list[str]:
        async with record.lock:
            if record.deleted:
                return []
            if expired_before is not None and record.expires_at > expired_before:
                return []
            # Tombstone before filesystem IO: every late writer must see this.
            record.deleted = True
            ids = sorted(record.analysis_ids | set(record.analyses) | record.invalidated_analysis_ids)
            record.clauses.clear()
            record.analyses.clear()
            record.question_cache.clear()
            record.analysis_ids.clear()
            record.invalidated_analysis_ids.clear()
            record.warnings.clear()
            record.extraction_progress.clear()
            record.extraction_ready = False
            record.reviewed_revision = None
            record.token_hash = ''
            record.filename = ''
            # The removal worker revalidates this server-owned path. Even a
            # swapped link must not prevent tombstoning or lose private ML IDs.
            directory = record.path.parent
            # No await between tombstone, index removal and cleanup enrollment:
            # request cancellation must never strand a deleted record forever.
            # Creation's global critical section also contains no awaits.
            self.records.pop(record.document_id, None)
            self._schedule_local_cleanup(directory)
        await self.retry_cleanup()
        return ids

    async def expire(self) -> list[list[str]]:
        expired = []
        now = time.time()
        for record in list(self.records.values()):
            if not record.deleted and record.expires_at <= now:
                expired.append(await self.delete(record, expired_before=now))
        return expired
