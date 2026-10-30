"""Bounded local extraction execution; BE2 owns GPU scheduling."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from apps.api.schemas import ApiError


class BoundedJobs:
    def __init__(self, workers: int, queue_size: int):
        if workers < 1 or queue_size < 1:
            raise ValueError('Job worker and queue limits must be positive')
        self.worker_count = workers
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=queue_size)
        self.workers: list[asyncio.Task] = []
        self.running: dict[asyncio.Future, asyncio.Task] = {}
        self.closed = False

    async def submit(self, coroutine_factory: Callable[[], Awaitable[Any]]) -> asyncio.Future:
        if self.closed:
            raise ApiError('MODEL_BUSY', 'Background processing is shutting down.', 503, True)
        self.workers = [worker for worker in self.workers if not worker.done()]
        self.workers.extend(asyncio.create_task(self._worker())
                            for _ in range(self.worker_count - len(self.workers)))
        # A canceled queued upload should release its admission slot even while
        # another long extraction is still running. No coroutine is created for
        # a queued factory, so pruning cannot leak unawaited work.
        queued = []
        while not self.queue.empty():
            item = self.queue.get_nowait()
            self.queue.task_done()
            if not item[1].cancelled():
                queued.append(item)
        for item in queued:
            self.queue.put_nowait(item)
        future = asyncio.get_running_loop().create_future()
        try:
            self.queue.put_nowait((coroutine_factory, future))
        except asyncio.QueueFull:
            raise ApiError('MODEL_BUSY', 'Extraction queue is full; retry later.', 429, True) from None
        # Worker failures must not become unhandled-future logs. Awaiting callers
        # still receive the same error; no document data are printed here.
        future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        future.add_done_callback(self._cancel_running)
        return future

    def _cancel_running(self, future: asyncio.Future) -> None:
        if future.cancelled():
            task = self.running.get(future)
            if task is not None:
                task.cancel()

    @staticmethod
    async def _invoke(factory: Callable[[], Awaitable[Any]]) -> Any:
        # Invoking inside the task also captures factories which raise before
        # returning their awaitable, preserving the queue worker itself.
        return await factory()

    async def _worker(self) -> None:
        while True:
            factory, future = await self.queue.get()
            try:
                if future.cancelled():
                    continue
                task = asyncio.create_task(self._invoke(factory))
                self.running[future] = task
                # Cancellation may have happened before its callback was run.
                if future.cancelled():
                    task.cancel()
                try:
                    result = await task
                except asyncio.CancelledError:
                    future.cancel()
                    if asyncio.current_task().cancelling():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                        raise
                except Exception as exc:
                    if not future.done():
                        future.set_exception(exc)
                else:
                    if not future.done():
                        future.set_result(result)
            finally:
                self.running.pop(future, None)
                self.queue.task_done()

    async def close(self) -> None:
        self.closed = True
        while not self.queue.empty():
            _, future = self.queue.get_nowait()
            future.cancel()
            self.queue.task_done()
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
