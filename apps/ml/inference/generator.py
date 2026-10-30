"""Async adapter for the private, loopback-only llama.cpp HTTP server."""

from __future__ import annotations

import asyncio
import ipaddress
import time
from urllib.parse import urlsplit

import httpx

from ..service.contracts import GenerationRequest, GenerationResult
from .artifacts import MODEL_NAME


class GenerationError(RuntimeError):
    """Base class for safe-to-log local generator failures."""

    code = "MODEL_UNAVAILABLE"
    retryable = True


class GenerationUnavailable(GenerationError):
    code = "MODEL_UNAVAILABLE"


class GenerationBusy(GenerationError):
    code = "MODEL_BUSY"


class GenerationTimeout(GenerationError):
    code = "MODEL_TIMEOUT"


class GenerationInvalidResponse(GenerationError):
    code = "INVALID_MODEL_OUTPUT"
    retryable = False


def _validate_loopback_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("generator base_url must be an HTTP loopback URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("generator base_url cannot contain credentials or query data")
    hostname = parsed.hostname.casefold()
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if not is_loopback:
        raise ValueError("external inference endpoints are not permitted")
    return base_url.rstrip("/")


class LocalGenerator:
    """Use one local llama.cpp server and serialize all model generations.

    An optional injected client is intended for isolated unit tests. Production
    callers use a fresh local HTTPX client per request and never contact a
    non-loopback host.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        model_name: str = MODEL_NAME,
        timeout_seconds: float = 180.0,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.base_url = _validate_loopback_url(base_url)
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._injected_client = client
        self._generation_lock = asyncio.Semaphore(1)

    async def health(self) -> bool:
        """Return true only when the local model server reports ready."""
        try:
            response = await self._request("GET", f"{self.base_url}/health")
        except (httpx.RequestError, GenerationError):
            return False
        return response.status_code == 200

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a response and report measured latency and server token use."""
        started = time.perf_counter()
        async with self._generation_lock:
            payload: dict[str, object] = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
                "temperature": 0.1,
                "max_tokens": request.max_new_tokens,
                "stream": False,
            }
            if request.response_schema is not None:
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "nyayalens_response", "strict": True, "schema": request.response_schema},
                }

            try:
                response = await self._request(
                    "POST", f"{self.base_url}/v1/chat/completions", json=payload
                )
            except httpx.TimeoutException as exc:
                raise GenerationTimeout("local model request timed out") from exc
            except httpx.RequestError as exc:
                raise GenerationUnavailable("local model server is unavailable") from exc

            if response.status_code == 429:
                raise GenerationBusy("local model is busy")
            if response.status_code in {408, 504}:
                raise GenerationTimeout("local model request timed out")
            if response.status_code >= 500:
                raise GenerationUnavailable("local model server returned an error")
            if response.status_code >= 400:
                raise GenerationInvalidResponse(
                    f"local model rejected the request (HTTP {response.status_code})"
                )

            try:
                body = response.json()
                choices = body["choices"]
                message = choices[0]["message"]
                content = message["content"]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise GenerationInvalidResponse(
                    "local model returned an invalid chat response"
                ) from exc

            if isinstance(content, list):
                content = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                )
            if not isinstance(content, str) or not content.strip():
                raise GenerationInvalidResponse("local model returned an empty response")

            usage = body.get("usage")
            output_tokens: int | None = None
            if isinstance(usage, dict):
                token_value = usage.get("completion_tokens")
                if isinstance(token_value, int) and not isinstance(token_value, bool):
                    output_tokens = token_value if token_value >= 0 else None

            returned_model = body.get("model")
            model_name = (
                returned_model.strip()
                if isinstance(returned_model, str) and returned_model.strip()
                else self.model_name
            )
            return GenerationResult(
                text=content.strip(),
                model=model_name,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                output_tokens=output_tokens,
            )

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        timeout = httpx.Timeout(self.timeout_seconds, connect=min(10.0, self.timeout_seconds))
        if self._injected_client is not None:
            try:
                return await self._injected_client.request(
                    method, url, timeout=timeout, **kwargs
                )
            except httpx.RequestError:
                raise
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(method, url, **kwargs)
