"""Killable local parser process with private pipes and bounded execution.

Isolation limits parser lifetime/memory; this is not a filesystem/network sandbox.
Only the parent emits safe progress logs. No private data appears in argv/stderr.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from apps.api.config import Settings
from apps.api.schemas import ApiError, Clause

PARSER_FIELDS=('max_upload_mb','max_pdf_pages','max_docx_expanded_bytes','max_docx_entries',
    'max_extracted_chars','ocr_timeout_seconds','ocr_max_pixels','extraction_memory_mb','extraction_timeout_seconds')
PROGRESS_FIELDS={'completed_pages','total_pages','completed_ocr_pages','completed_paragraphs','total_paragraphs'}


class WindowsJob:
    """Kill descendants (including OCR) on close and cap per-process memory."""
    def __init__(self,pid,memory_mb):
        import ctypes
        from ctypes import wintypes
        class BASIC(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),
                ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
                ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
                ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount',
                'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class LIMITS(ctypes.Structure):
            _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),
                ('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR]; kernel.CreateJobObjectW.restype=wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]; kernel.SetInformationJobObject.restype=wintypes.BOOL
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]; kernel.AssignProcessToJobObject.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]; kernel.CloseHandle.restype=wintypes.BOOL
        self.kernel,self.handle=kernel,kernel.CreateJobObjectW(None,None)
        process=None
        try:
            if not self.handle: raise OSError('Job creation failed')
            info=LIMITS(); info.BasicLimitInformation.LimitFlags=0x2000|0x100|0x200
            info.ProcessMemoryLimit=int(memory_mb)*1024*1024
            info.JobMemoryLimit=info.ProcessMemoryLimit
            if not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
                raise OSError('Job memory limit failed')
            process=kernel.OpenProcess(0x100|0x1,False,pid)
            if not process or not kernel.AssignProcessToJobObject(self.handle,process):
                raise OSError('Job assignment failed')
        except Exception:
            self.close(); raise
        finally:
            if process: kernel.CloseHandle(process)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle=None


async def _stop(process,job):
    if job:
        job.close()  # atomically kills the Windows parser/OCR tree
    elif os.name!='nt':
        import signal
        with __import__('contextlib').suppress(ProcessLookupError):
            os.killpg(process.pid,signal.SIGKILL)
    if process.returncode is None:
        with __import__('contextlib').suppress(ProcessLookupError): process.kill()
    await process.wait()


async def extract_isolated(path: Path,kind: str,input_language: str,settings: Settings,progress=None,
                           *,command=None,on_started=None):
    """Spawn one bounded parser; test-only command injection never comes from HTTP."""
    env=dict(os.environ); env.pop('ML_SERVICE_TOKEN',None); env['PYTHONIOENCODING']='utf-8'; env['PYTHONNOUSERSITE']='1'
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
    process=await asyncio.create_subprocess_exec(*(command or [sys.executable,'-m','apps.api.extraction_worker','--child']),
        cwd=Path(__file__).resolve().parents[2],env=env,stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,
        limit=settings.max_extracted_chars*16+4*1024*1024,**options)
    job=None
    try:
        if os.name=='nt': job=WindowsJob(process.pid,settings.extraction_memory_mb)
        if on_started: on_started(process.pid)
        payload={'path':str(path),'kind':kind,'input_language':input_language,
                 'settings':{name:getattr(settings,name) for name in PARSER_FIELDS}}
        result=None
        async with asyncio.timeout(settings.extraction_timeout_seconds):
            process.stdin.write(json.dumps(payload).encode()+b'\n')
            await process.stdin.drain(); process.stdin.close()
            while line:=await process.stdout.readline():
                message=json.loads(line)
                if not isinstance(message,dict): raise ValueError('Invalid worker message')
                if message.get('type')=='progress':
                    value=message.get('value',{})
                    if not isinstance(value,dict) or set(value)-PROGRESS_FIELDS-{'stage'}:
                        raise ValueError('Invalid worker progress')
                    if value.get('stage')!='extracting' or any(type(v) is not int or v<0 for k,v in value.items() if k!='stage'):
                        raise ValueError('Invalid worker counts')
                    if progress: progress(value)
                elif message.get('type')=='error':
                    code=message.get('code')
                    codes={'FILE_TOO_LARGE':(413,'Document exceeds a parser resource limit.'),
                        'UNSUPPORTED_FILE':(415,'Document type or archive content is unsupported.'),
                        'EMPTY_DOCUMENT':(422,'No usable text was extracted.'),
                        'OCR_UNAVAILABLE':(503,'Local OCR executable or required language asset is unavailable.'),
                        'EXTRACTION_FAILED':(422,'Local document parsing or OCR failed.')}
                    status,text=codes.get(code,(422,'Local document parsing failed.'))
                    raise ApiError(code if code in codes else 'EXTRACTION_FAILED',text,status,message.get('retryable') is True)
                elif message.get('type')=='result' and result is None:
                    result=message['value']
                    result['clauses']=[Clause.model_validate(c) for c in result['clauses']]
                    if not result['clauses'] or sum(len(c.source_text) for c in result['clauses'])>settings.max_extracted_chars:
                        raise ValueError('Invalid worker text size')
                    if not isinstance(result['warnings'],list) or any(not isinstance(w,str) for w in result['warnings']):
                        raise ValueError('Invalid warnings')
                    if result['input_language'] not in {'en','hi','pa','unknown'} or result['document_type'] not in {'agreement','fir','notice','other'}:
                        raise ValueError('Invalid metadata')
                else: raise ValueError('Unexpected parser output')
            if await process.wait()!=0 or result is None:
                raise ValueError('Parser exited without a valid result')
        return result
    except TimeoutError:
        raise ApiError('EXTRACTION_TIMEOUT','Local document extraction exceeded its time limit. Try a shorter document.',504,True) from None
    except (ApiError,asyncio.CancelledError):
        raise
    except Exception:
        raise ApiError('EXTRACTION_FAILED','The isolated local parser failed or exceeded its memory limit.',422) from None
    finally:
        await asyncio.shield(_stop(process,job))


def _child():
    """One input request; stdout is a structured private pipe, never a terminal."""
    output=sys.stdout
    def emit(value):
        output.write(json.dumps(value,ensure_ascii=True,separators=(',',':'))+'\n'); output.flush()
    try:
        payload=json.loads(sys.stdin.buffer.readline(1024*1024))
        settings=Settings(**payload['settings'])
        if os.name!='nt':
            import resource
            memory=settings.extraction_memory_mb*1024*1024
            resource.setrlimit(resource.RLIMIT_AS,(memory,memory))
            cpu=math.ceil(settings.extraction_timeout_seconds)
            resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+1))
        from apps.api.extraction import extract_document
        result=extract_document(Path(payload['path']),payload['kind'],payload['input_language'],settings,
            lambda value:emit({'type':'progress','value':value}))
        result['clauses']=[c.model_dump() for c in result['clauses']]
        emit({'type':'result','value':result})
    except ApiError as error:
        emit({'type':'error','code':error.code,'retryable':error.retryable})
    except BaseException:
        emit({'type':'error','code':'EXTRACTION_FAILED','retryable':False})


if __name__=='__main__':
    if sys.argv[1:]!=['--child']: raise SystemExit('Use the public API or parser tests.')
    _child()
