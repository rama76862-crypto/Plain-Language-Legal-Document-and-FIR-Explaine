"""Explicit hosted deployment adapter; local inference never selects this implicitly."""
from __future__ import annotations
import asyncio
import json
import os
import time
import httpx
from apps.ml.service.contracts import GenerationResult
from .generator import GenerationBusy,GenerationTimeout,GenerationUnavailable,GenerationInvalidResponse
from .pii import PiiVault


class HostedGenerator:
    def __init__(self):
        self.key=os.environ.get('GROQ_API_KEY','').strip()
        self.model_name=os.environ.get('GROQ_MODEL','openai/gpt-oss-120b')
        self.base_url='https://api.groq.com/openai/v1'
        self._lock=asyncio.Semaphore(1)
        self._health_until=0;self._healthy=False

    async def health(self):
        if not self.key:return False
        if time.monotonic()<self._health_until:return self._healthy
        try:
            async with httpx.AsyncClient(timeout=8,trust_env=False) as client:
                response=await client.get(self.base_url+'/models',headers={'Authorization':'Bearer '+self.key})
            self._healthy=response.status_code==200
        except httpx.RequestError:self._healthy=False
        self._health_until=time.monotonic()+20
        return self._healthy

    async def generate(self,request):
        if not self.key:raise GenerationUnavailable('Hosted provider is not configured.')
        vault=PiiVault();started=time.monotonic()
        system=vault.protect(request.system_prompt)+'\nReturn only JSON matching this schema: '+json.dumps(request.response_schema)
        prompt=vault.protect(request.user_prompt)
        payload={'model':self.model_name,'messages':[{'role':'system','content':system},{'role':'user','content':prompt}],
                 'temperature':0,'max_tokens':min(request.max_new_tokens,1024),'response_format':{'type':'json_object'}}
        async with self._lock:
            try:
                async with httpx.AsyncClient(timeout=40,trust_env=False) as client:
                    response=await client.post(self.base_url+'/chat/completions',headers={'Authorization':'Bearer '+self.key},json=payload)
            except httpx.TimeoutException:raise GenerationTimeout('Hosted request timed out.') from None
            except httpx.RequestError:raise GenerationUnavailable('Hosted service is unavailable.') from None
        if response.status_code==429:raise GenerationBusy('Hosted provider quota reached; retry later.')
        if response.status_code!=200:raise GenerationUnavailable('Hosted provider rejected the request.')
        try:
            body=response.json();content=body['choices'][0]['message']['content']
            if not isinstance(content,str) or not content.strip():raise ValueError('empty')
            tokens=body.get('usage',{}).get('completion_tokens')
        except (ValueError,KeyError,IndexError,TypeError):raise GenerationInvalidResponse('Invalid hosted response.') from None
        return GenerationResult(text=vault.restore(content),model=self.model_name,latency_ms=(time.monotonic()-started)*1000,output_tokens=tokens if isinstance(tokens,int) else None)
