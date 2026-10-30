"""Hosted transport regressions use controlled HTTP, never real credentials."""
import json
import httpx
import pytest
from apps.ml.inference.hosted import HostedGenerator
from apps.ml.inference.generator import GenerationBusy
from apps.ml.service.contracts import GenerationRequest


@pytest.mark.asyncio
async def test_hosted_masks_direct_identifiers_but_restores_result(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-key')
    original_client=httpx.AsyncClient
    async def handler(request):
        payload=json.loads(request.content);text=payload['messages'][1]['content']
        assert 'citizen@example.com' not in text and '9876543210' not in text
        assert 'INR 12,500' in text
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'summary':text})}}],'usage':{'completion_tokens':20}})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original_client(transport=httpx.MockTransport(handler)))
    result=await HostedGenerator().generate(GenerationRequest(system_prompt='Return JSON.',user_prompt='Contact citizen@example.com or 9876543210. The amount is INR 12,500.',response_schema={'type':'object'},max_new_tokens=100))
    assert 'citizen@example.com' in result.text and '9876543210' in result.text
    assert result.output_tokens==20


@pytest.mark.asyncio
async def test_hosted_rate_limit_is_explicit_and_does_not_forward_provider_body(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic-test-key');original_client=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original_client(transport=httpx.MockTransport(lambda _:httpx.Response(429,text='private provider body'))))
    with pytest.raises(GenerationBusy) as error:
        await HostedGenerator().generate(GenerationRequest(system_prompt='Return JSON.',user_prompt='synthetic',response_schema={'type':'object'}))
    assert 'private provider body' not in str(error.value)
