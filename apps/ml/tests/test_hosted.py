"""Hosted transport regressions use controlled HTTP, never real credentials."""
import json
import httpx
import pytest
from apps.ml.inference.hosted import HostedGenerator,compact_schema
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


def test_compact_schema_retains_only_reachable_definitions_without_mutation():
    schema={'type':'object','properties':{'unused':{'type':'array','maxItems':0,'items':{'$ref':'#/$defs/Unused'}},'used':{'$ref':'#/$defs/Used'}},'$defs':{'Unused':{'type':'string'},'Used':{'type':'object','title':'Noise','properties':{'child':{'$ref':'#/$defs/Child'}}},'Child':{'type':'string'}}}
    compact=compact_schema(schema)
    assert set(compact['$defs'])=={'Used','Child'}
    assert compact['properties']['unused']['items']=={}
    assert 'title' not in compact['$defs']['Used']
    assert schema['$defs']['Used']['title']=='Noise'


def test_identifier_restoration_does_not_confuse_first_and_tenth_placeholders():
    from apps.ml.inference.pii import PiiVault
    vault=PiiVault();source=' '.join(f'citizen{n}@example.test' for n in range(12))
    protected=vault.protect(source)
    assert 'example.test' not in protected
    assert vault.restore(protected)==source
