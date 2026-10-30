"""Sanitized errors returned by the private ML API."""

from __future__ import annotations


class ServiceProblem(Exception):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable

