"""Model-free tests; generator responses here are explicit fixtures/mocks."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from apps.ml.inference.artifacts import MODEL_NAME
from apps.ml.inference.generator import GenerationBusy, GenerationError, LocalGenerator
from apps.ml.service.contracts import ClauseInput, GenerationRequest, GenerationResult
from apps.ml.translation.local_translator import LocalTranslator, assess_protected_text
from apps.ml.translation.language_matrix_smoke import (
    _run_explanation_cell,
    _target_script_check,
)


SYNTHETIC_HINDI_CLAUSE = "धारा ३०२ IPC के तहत आरोप दर्ज है। भुगतान ₹१२,५०० है।"
SYNTHETIC_PUNJABI_CLAUSE = "ਧਾਰਾ ੩੦੨ IPC ਅਧੀਨ ਦੋਸ਼ ਦਰਜ ਹੈ। ਰਕਮ ₹੧੨,੫੦੦ ਹੈ।"


def _completion(content: str, *, tokens: int | None = 7) -> dict[str, object]:
    body: dict[str, object] = {
        "model": "Qwen3-4B-Instruct-2507-Q4_K_M",
        "choices": [{"message": {"content": content}}],
    }
    if tokens is not None:
        body["usage"] = {"completion_tokens": tokens, "prompt_tokens": 18}
    return body


def test_generator_sends_schema_and_reports_server_usage() -> None:
    seen: dict[str, object] = {}

    async def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(503)
        seen["url"] = str(request.url)
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_completion('{"ok":true}', tokens=9))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            generator = LocalGenerator(client=client)
            assert await generator.health() is False  # mock only handles generation below
            result = await generator.generate(
                GenerationRequest(
                    system_prompt="system",
                    user_prompt="user",
                    response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
                    max_new_tokens=32,
                )
            )
        assert result.text == '{"ok":true}'
        assert result.model == "Qwen3-4B-Instruct-2507-Q4_K_M"
        assert result.output_tokens == 9
        assert result.latency_ms >= 0
        payload = seen["payload"]
        assert isinstance(payload, dict)
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["max_tokens"] == 32
        assert seen["url"] == "http://127.0.0.1:8080/v1/chat/completions"

    asyncio.run(run())


def test_generator_omits_token_count_when_server_does_not_supply_it() -> None:
    async def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion("answer", tokens=None))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await LocalGenerator(client=client).generate(
                GenerationRequest(system_prompt="system", user_prompt="user")
            )
        assert result.output_tokens is None

    asyncio.run(run())


def test_generator_health_accepts_local_ready_response() -> None:
    async def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            assert await LocalGenerator(client=client).health() is True

    asyncio.run(run())


def test_generator_maps_local_busy_response() -> None:
    async def handle(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "busy"}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            generator = LocalGenerator(client=client)
            with pytest.raises(GenerationBusy) as captured:
                await generator.generate(
                    GenerationRequest(system_prompt="system", user_prompt="user")
                )
        assert captured.value.code == "MODEL_BUSY"

    asyncio.run(run())


def test_generator_rejects_non_loopback_endpoints() -> None:
    for url in ("https://example.com", "http://0.0.0.0:8080", "http://192.168.1.5:8080"):
        with pytest.raises(ValueError, match="loopback|external"):
            LocalGenerator(base_url=url)


def test_local_generator_serializes_concurrent_requests() -> None:
    active = 0
    peak_active = 0

    async def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0.02)
        active -= 1
        return httpx.Response(200, json=_completion("answer"))

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            generator = LocalGenerator(client=client)
            request = GenerationRequest(system_prompt="system", user_prompt="user")
            await asyncio.gather(generator.generate(request), generator.generate(request))

    asyncio.run(run())
    assert peak_active == 1


class MockGenerator:
    """Explicit development-only generator fixture; never proof of real inference."""

    model_name = "mock-qwen-fixture"

    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text or "An allegation was recorded under Section 302 IPC. The amount is INR 12,500."
        self.error = error
        self.calls = 0

    async def generate(self, _request: GenerationRequest) -> GenerationResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return GenerationResult(
            text=json.dumps({"translation": self.text}, ensure_ascii=False),
            model=self.model_name,
            latency_ms=1.0,
            output_tokens=19,
        )


def test_english_translation_is_identity_and_does_not_call_model() -> None:
    generator = MockGenerator()
    clause = ClauseInput(clause_id="synthetic-en-1", reviewed_text="Synthetic English clause.")

    result = asyncio.run(LocalTranslator(generator).translate(clause, "en"))

    assert result.original_text == clause.reviewed_text
    assert result.pivot_text == clause.reviewed_text
    assert result.review_status == "supported"
    assert generator.calls == 0


def test_hindi_pivot_keeps_original_and_is_needs_review_without_fluent_review() -> None:
    generator = MockGenerator()
    clause = ClauseInput(clause_id="synthetic-hi-1", reviewed_text=SYNTHETIC_HINDI_CLAUSE)

    result = asyncio.run(LocalTranslator(generator).translate(clause, "hi"))

    assert result.original_text == SYNTHETIC_HINDI_CLAUSE
    assert result.pivot_text == generator.text
    assert result.review_status == "needs_review"
    assert "numeric_tokens_preserved" in result.checks
    assert "known_legal_codes_preserved" in result.checks
    assert "fluent_review_unavailable" in result.checks
    assert generator.calls == 1


def test_punjabi_numeric_mismatch_requires_review() -> None:
    generator = MockGenerator(text="An allegation was recorded under Section 302 IPC. The amount is INR 25,000.")
    clause = ClauseInput(clause_id="synthetic-pa-1", reviewed_text=SYNTHETIC_PUNJABI_CLAUSE)

    result = asyncio.run(LocalTranslator(generator).translate(clause, "pa"))

    assert result.review_status == "needs_review"
    assert "numeric_tokens_changed" in result.checks


def test_romanized_or_unknown_language_is_not_sent_to_english_classifier_path() -> None:
    generator = MockGenerator()
    romanized = ClauseInput(clause_id="synthetic-pa-romanized", reviewed_text="dhara 302 IPC de tahat")

    romanized_result = asyncio.run(LocalTranslator(generator).translate(romanized, "pa"))
    unknown_result = asyncio.run(LocalTranslator(generator).translate(romanized, "unknown"))

    assert romanized_result.pivot_text is None
    assert romanized_result.review_status == "needs_review"
    assert unknown_result.pivot_text is None
    assert unknown_result.review_status == "needs_review"
    assert generator.calls == 0


def test_translation_generation_failure_preserves_original_and_needs_review() -> None:
    generator = MockGenerator(error=GenerationError("mock unavailable"))
    clause = ClauseInput(clause_id="synthetic-hi-failed", reviewed_text=SYNTHETIC_HINDI_CLAUSE)

    result = asyncio.run(LocalTranslator(generator).translate(clause, "hi"))

    assert result.original_text == SYNTHETIC_HINDI_CLAUSE
    assert result.pivot_text is None
    assert result.review_status == "needs_review"
    assert result.checks[0] == "local_translation_generation_unavailable"
    assert "generation_attempts_1" in result.checks


def test_default_model_identity_is_the_pinned_local_artifact() -> None:
    assert LocalGenerator().model_name == MODEL_NAME


def test_protected_text_comparison_normalizes_indic_digits_and_tracks_negation() -> None:
    result = assess_protected_text(
        "धारा ३०२ IPC के तहत आरोप दर्ज नहीं है। राशि ₹१२,५०० है।",
        "The allegation under Section 302 IPC is not recorded. The amount is INR 12,500.",
        "hi",
        "en",
    )
    assert result == {
        "numbers": "preserved",
        "legal_codes": "preserved",
        "negation": "preserved",
        "allegation": "preserved",
        "names": "not_automatically_verified",
    }


def test_protected_text_comparison_detects_changed_amount_or_dropped_negation() -> None:
    result = assess_protected_text(
        "ಧਾਰਾ ੩੦੨ IPC ਅਧੀਨ ਦੋਸ਼ ਨਹੀਂ ਹੈ। ਰਕਮ ੧੨,੫੦੦ ਹੈ।",
        "An allegation under Section 302 IPC is recorded. The amount is 25,000.",
        "pa",
        "en",
    )
    assert result["numbers"] == "changed"
    assert result["negation"] == "changed"
    assert result["allegation"] == "preserved"


def test_target_script_accepts_original_latin_codes_and_amounts() -> None:
    result = _target_script_check("IPC 302 ਦੀ ਰਕਮ ₹12,500 ਹੈ।", "pa")
    assert result["status"] == "passed"
    assert result["expected_script"] == "Gurmukhi"
    assert result["latin_names_identifiers_and_digits_allowed"] is True


def test_target_script_rejects_latin_only_punjabi_explanation() -> None:
    assert _target_script_check("IPC 302 amount 12,500", "pa")["status"] == "failed"


class SequencedExplanationGenerator:
    model_name = "mock-structured-output"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls = 0

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        assert request.response_schema is not None
        self.calls += 1
        return GenerationResult(
            text=self.outputs[self.calls - 1],
            model=self.model_name,
            latency_ms=3.5,
            output_tokens=11,
        )


def test_matrix_repairs_target_script_once_and_never_marks_fluency_supported() -> None:
    generator = SequencedExplanationGenerator(
        [
            json.dumps({"explanation": "The person did not pay IPC 302 amount 10."}),
            json.dumps({"explanation": "ਵਿਅਕਤੀ ਨੇ ਭੁਗਤਾਨ ਨਹੀਂ ਕੀਤਾ। IPC 302 ਦੀ ਰਕਮ 10 ਹੈ।"}, ensure_ascii=False),
        ]
    )
    result = asyncio.run(
        _run_explanation_cell(
            generator,  # type: ignore[arg-type]
            source_language="en",
            output_language="pa",
            original_text="The person did not pay IPC 302 amount 10.",
            english_pivot=None,
        )
    )

    assert generator.calls == 2
    assert result["attempt_count"] == 2
    assert result["repair_attempted"] is True
    assert result["attempts"][0]["target_script_status"] == "failed"
    assert result["attempts"][1]["target_script_status"] == "passed"
    assert result["target_script_status"] == "passed"
    assert result["protected_text_checks"]["numbers"] == "preserved"
    assert result["protected_text_checks"]["negation"] == "preserved"
    assert result["status"] == "needs_review"
    assert result["fluent_review_status"] == "not_performed"
