"""CPU container supervisor for this app's public API and loopback ML service."""
from __future__ import annotations
import os
import signal
import subprocess
import sys
import time


def main():
    env=os.environ.copy()
    if env.get('INFERENCE_MODE')!='hosted':raise RuntimeError('Hosted image requires INFERENCE_MODE=hosted.')
    if not env.get('GROQ_API_KEY'):raise RuntimeError('Set the server-side GROQ_API_KEY before starting this deployment.')
    port=int(env.get('PORT','8080'))
    if not 1<=port<=65535:raise RuntimeError('Invalid PORT')
    env.update(ML_MODE='real',ML_BASE_URL='http://127.0.0.1:8001',ML_PORT='8001')
    commands=[[sys.executable,'-m','uvicorn','apps.ml.service.app:app','--host','127.0.0.1','--port','8001','--workers','1','--no-access-log'],
              [sys.executable,'-m','uvicorn','apps.api.main:app','--host','0.0.0.0','--port',str(port),'--workers','1','--no-access-log']]
    processes=[]
    def stop(*_):
        for p in reversed(processes):
            if p.poll() is None:p.terminate()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        for command in commands:
            processes.append(subprocess.Popen(command,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
        while all(p.poll() is None for p in processes):time.sleep(.5)
        return next((p.returncode for p in processes if p.poll() not in (None,0)),0)
    finally:
        stop()
        for p in processes:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill()


if __name__=='__main__':raise SystemExit(main())
