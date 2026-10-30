"""Tesseract subprocesses with finite deadlines and no document logging."""
import os
import shutil
import subprocess
from pathlib import Path
from apps.api.schemas import ApiError

_CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


def _executable():
    requested = os.environ.get('TESSERACT_CMD')
    if requested:
        return shutil.which(requested)
    portable = Path(__file__).resolve().parents[3] / 'tools' / 'ocr' / 'tesseract' / 'tesseract.exe'
    if portable.is_file():
        return str(portable)
    return shutil.which('tesseract')


def _data_args(executable):
    configured = os.environ.get('TESSDATA_PREFIX')
    data = Path(configured) if configured else Path(executable).parent / 'tessdata'
    return ['--tessdata-dir', str(data)] if data.is_dir() else []


def ocr_capabilities() -> dict:
    executable = _executable()
    if not executable:
        return {'available': False, 'languages': [], 'reason': 'OCR executable unavailable'}
    try:
        process = subprocess.run([executable, '--list-langs', *_data_args(executable)], capture_output=True,
                                 text=True, timeout=5, check=False, creationflags=_CREATE_FLAGS)
        languages = [line.strip() for line in process.stdout.splitlines()
                     if line.strip() in {'eng', 'hin', 'pan'}]
        return {'available': process.returncode == 0, 'languages': sorted(languages),
                'reason': None if process.returncode == 0 else 'OCR language probe failed'}
    except (OSError, subprocess.TimeoutExpired):
        return {'available': False, 'languages': [], 'reason': 'OCR language probe failed'}


def ocr_page(page, input_language, settings):
    capability = ocr_capabilities()
    language = {'en': 'eng', 'hi': 'hin', 'pa': 'pan'}.get(input_language)
    languages = capability['languages']
    selected = [language] if language else [code for code in ('eng', 'hin', 'pan') if code in languages]
    if not capability['available'] or not selected or any(code not in languages for code in selected):
        raise ApiError('OCR_UNAVAILABLE', 'Local OCR executable or required language asset is unavailable.', 503)
    # 150 DPI is a demo resource budget, not a claim of extraction accuracy.
    import pymupdf as fitz
    scale = 150 / 72
    if page.rect.width * page.rect.height * scale * scale > settings.ocr_max_pixels:
        raise ApiError('EXTRACTION_FAILED', 'Scanned page exceeds the OCR pixel limit.', 422)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    try:
        executable = _executable()
        process = subprocess.run([executable, 'stdin', 'stdout', *_data_args(executable), '-l', '+'.join(selected), '--psm', '3'],
                                 input=pixmap.tobytes('png'), capture_output=True,
                                 timeout=settings.ocr_timeout_seconds, check=False, creationflags=_CREATE_FLAGS)
    except subprocess.TimeoutExpired:
        raise ApiError('EXTRACTION_FAILED', 'Local OCR page timeout; use a clearer or shorter document.', 422, True) from None
    except OSError:
        raise ApiError('OCR_UNAVAILABLE', 'Local OCR could not be started.', 503) from None
    if process.returncode:
        raise ApiError('EXTRACTION_FAILED', 'Local OCR failed for a scanned page.', 422)
    return process.stdout.decode('utf-8', errors='replace').strip()
