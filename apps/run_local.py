"""Start/stop this checkout's local services with real readiness progress.

Run with the API environment: python -m apps.run_local start
No tunnel or public exposure is started by this command.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"work"/"runtime"/"launcher"
STATE=RUNTIME/"processes.json"

def python_at(directory):
    candidate=directory/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    if not candidate.is_file():raise RuntimeError(f"Python environment missing: {directory}")
    return str(candidate)

def ready(url):
    try:
        with urlopen(url,timeout=2) as response:
            data=json.load(response)
            return response.status==200 and data.get("status") not in {"error","failed"}
    except Exception:return False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["start","status","stop"])
    parser.add_argument('--gpu-layers',type=int,default=99,help='99 offloads all model layers; use 20 if GPU memory is tight, or 0 for CPU')
    parser.add_argument('--ctx-size',type=int,default=4096)
    args=parser.parse_args()
    if args.gpu_layers<0 or args.ctx_size<512:parser.error('Invalid layer or context count')
    services=[("model",8080,"/health","apps.ml.inference.serve"),("ml",8001,"/internal/health","apps.ml.service"),("api",8000,"/api/v1/health","uvicorn")]
    if args.action=="status":
        for name,port,path,_ in services:print(name,ready(f"http://127.0.0.1:{port}{path}"))
        return
    if args.action=="stop":
        import psutil
        if not STATE.exists():print("No launcher-owned processes recorded.");return
        for entry in reversed(json.loads(STATE.read_text())):
            try:
                process=psutil.Process(entry["pid"])
                if abs(process.create_time()-entry["created"])>1 or entry["module"] not in " ".join(process.cmdline()):
                    print("Skipped a changed/reused process ID.");continue
                children=process.children(recursive=True)
                process.terminate()
                for child in children:
                    try:child.terminate()
                    except psutil.NoSuchProcess:pass
                _,alive=psutil.wait_procs([process,*children],timeout=8)
                for remaining in alive:remaining.kill()
            except psutil.NoSuchProcess:pass
        STATE.unlink(missing_ok=True)
        print("Launcher-owned services stopped.");return
    if not (ROOT/"frontend"/"dist"/"index.html").is_file():
        raise RuntimeError("Build frontend first: npm --prefix frontend run build")
    ml_python=python_at(ROOT/"apps"/"ml"/".venv")
    api_python=python_at(ROOT/".venv-api")
    from apps.doctor_local import check_installation
    if not check_installation():raise RuntimeError('Incomplete setup. Run Setup.cmd; see TEAM-SETUP.md.')
    RUNTIME.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(ML_MODE="real",ML_BASE_URL="http://127.0.0.1:8001",WEB_ORIGIN="http://127.0.0.1:8000",WEB_DIST_DIR=str(ROOT/"frontend"/"dist"),RUNTIME_DIR=str(ROOT/"work"/"runtime"/"be1"),OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="2",TOKENIZERS_PARALLELISM="false")
    env.update(LLAMA_GPU_LAYERS=str(args.gpu_layers),LLAMA_CTX_SIZE=str(args.ctx_size),MODEL_TIMEOUT_SECONDS='300')
    owned=json.loads(STATE.read_text()) if STATE.exists() else []
    import psutil
    for number,(name,port,path,module) in enumerate(services,1):
        url=f"http://127.0.0.1:{port}{path}"
        print(f"[{number}/3] {name}: checking readiness",flush=True)
        if ready(url):
            print(f"[{number}/3] existing service responds; not claiming process ownership",flush=True)
            continue
        command=[ml_python if name!="api" else api_python,"-m",module]
        if name=="api":command += ["apps.api.main:app","--host","127.0.0.1","--port","8000","--workers","1","--no-access-log"]
        output=(RUNTIME/(name+".out.log")).open("ab")
        errors=(RUNTIME/(name+".err.log")).open("ab")
        try:
            process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=output,stderr=errors,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        finally:output.close();errors.close()
        owned.append({"pid":process.pid,"created":psutil.Process(process.pid).create_time(),"module":module})
        STATE.write_text(json.dumps(owned,indent=2),encoding="utf-8")
        for attempt in range(180):
            if process.poll() is not None:raise RuntimeError(f"{name} exited; inspect its launcher log.")
            if ready(url):break
            if attempt%10==0:print(f"[{number}/3] waiting for {name} ({attempt}s)",flush=True)
            time.sleep(1)
        else:raise RuntimeError(f"{name} readiness timeout")
    print("Open http://127.0.0.1:8000/ ; private model services remain on loopback.",flush=True)
if __name__=="__main__":main()

