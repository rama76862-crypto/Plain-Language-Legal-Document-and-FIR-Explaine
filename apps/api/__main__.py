"""Tested single-worker launcher: python -m apps.api."""
import logging
import uvicorn
from apps.api.config import Settings

if __name__=='__main__':
    settings=Settings.from_env()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(name)s %(message)s')
    # Third-party request logs are unnecessary; no filenames/tokens in access logs.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    uvicorn.run('apps.api.main:app',host='127.0.0.1',port=settings.api_port,workers=1,access_log=False)
