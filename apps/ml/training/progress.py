"""Truthful Rich progress helpers with a simple terminal fallback."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import TypeVar

T = TypeVar("T")


@contextmanager
def status(message: str) -> Iterator[None]:
    """Show an indeterminate spinner for work whose completion is not countable."""
    if not sys.stderr.isatty():
        print(f"[working] {message}", file=sys.stderr, flush=True)
        try:
            yield
        finally:
            print(f"[done] {message}", file=sys.stderr, flush=True)
        return

    try:
        from rich.console import Console
    except ImportError:
        print(f"{message}...", file=sys.stderr, flush=True)
        try:
            yield
        finally:
            print(f"Finished: {message}", file=sys.stderr, flush=True)
        return

    console = Console(stderr=True)
    with console.status(message, spinner="line"):
        yield


def tracked(iterable: Iterable[T], *, total: int, description: str) -> Iterator[T]:
    """Show real completed-item counts while a known-size collection is processed."""
    with PhaseProgress(description, total) as progress:
        for item in iterable:
            yield item
            progress.advance()


class PhaseProgress:
    """A phase bar advanced only when a named, real training phase finishes."""

    def __init__(self, description: str, total: int) -> None:
        self.description = description
        self.total = total
        self.completed = 0
        self._progress = None
        self._task_id = None

    def __enter__(self) -> "PhaseProgress":
        try:
            from rich.console import Console
            from rich.progress import Progress, ProgressColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
            from rich.text import Text
        except ImportError:
            print(f"{self.description}: 0/{self.total} phases", file=sys.stderr, flush=True)
            return self

        class AsciiBarColumn(ProgressColumn):
            def render(self, task):
                width = 24
                if task.total is None or task.total <= 0:
                    return Text("[working]")
                fraction = min(1.0, max(0.0, task.completed / task.total))
                filled = round(width * fraction)
                return Text("[" + "#" * filled + "-" * (width - filled) + "]")

        self._progress = Progress(
            TextColumn("{task.description}"),
            AsciiBarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=Console(stderr=True, legacy_windows=True),
        )
        self._progress.start()
        self._task_id = self._progress.add_task(self.description, total=self.total)
        return self

    def advance(self, phase: str | None = None) -> None:
        self.completed += 1
        if self._progress is not None and self._task_id is not None:
            description = f"{self.description}: {phase}" if phase else self.description
            self._progress.update(self._task_id, description=description, advance=1)
        else:
            if self.completed == 1 or self.completed % 500 == 0 or self.completed == self.total:
                detail = f" ({phase})" if phase else ""
                print(f"{self.description}: {self.completed}/{self.total}{detail}", file=sys.stderr, flush=True)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._progress is not None:
            self._progress.stop()
