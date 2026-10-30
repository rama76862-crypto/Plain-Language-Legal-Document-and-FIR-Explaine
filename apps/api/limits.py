"""Bound multipart body consumption before the framework spools the upload."""
import json


class UploadBodyLimit:
    def __init__(self,app,max_bytes):
        self.app,self.max_bytes=app,max_bytes

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method']!='POST' or scope['path']!='/api/v1/documents':
            return await self.app(scope,receive,send)
        exceeded=False; received=0; replaced=False
        async def limited_receive():
            nonlocal exceeded,received
            message=await receive()
            if message['type']=='http.request':
                received+=len(message.get('body',b''))
                if received>self.max_bytes:
                    exceeded=True
                    # Framework may translate the exception, but limited_send always
                    # normalizes the response and prevents further disk spooling.
                    raise ValueError('Upload request body limit exceeded')
            return message
        async def limited_send(message):
            nonlocal replaced
            if not exceeded:
                return await send(message)
            if message['type']=='http.response.start':
                request_id=scope.get('state',{}).get('request_id','req_body_limit')
                body=json.dumps({'error':{'code':'FILE_TOO_LARGE','message':'Upload request exceeds the configured body limit.','retryable':False},'request_id':request_id}).encode()
                await send({'type':'http.response.start','status':413,'headers':[(b'content-type',b'application/json'),(b'cache-control',b'no-store')]})
                await send({'type':'http.response.body','body':body})
                replaced=True
            elif message['type']=='http.response.body' and not replaced:
                return
        await self.app(scope,limited_receive,limited_send)
