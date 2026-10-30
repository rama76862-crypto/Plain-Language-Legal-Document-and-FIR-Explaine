"""Prepare app-local Windows Tesseract without running any installer.

Downloads only upstream release assets and tessdata. No documents leave the
machine. MSI APIs are used read-only to obtain the 7-Zip cabinet, never install.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / 'tools' / 'ocr'
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
ASSETS = {
    '7z2605-x64.msi': ('https://github.com/ip7z/7zip/releases/download/26.05/7z2605-x64.msi', '3fe4ab99fa15629c652944309a2b2bc6e41fc933fc6b63f5df1ebcf3aea68263'),
    'tesseract-ocr-w64-setup-5.5.3.20260724.exe': ('https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe', 'bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4'),
}
TESSDATA_REVISION = '87416418657359cb625c412a48b6e1d6d41c29bd'
TESSDATA_ASSETS = {
    'eng.traineddata': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2',
    'hin.traineddata': '4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825',
    'pan.traineddata': '1ec0907fc3534065ea9ae190c6bb7ec9e5c74fd9d2fa996aaec7407f11ad8131',
    'LICENSE': 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
}


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def download(url, path, expected=None):
    path = Path(path)
    if path.exists() and (expected is None or digest(path) == expected):
        return
    request = urllib.request.Request(url, headers={'User-Agent': 'NyayaLens-local-OCR-setup'})
    temporary = path.with_suffix(path.suffix + '.download')
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
        total = int(response.headers.get('Content-Length', '0'))
        count = 0
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > 250 * 1024 * 1024:
                raise RuntimeError('Upstream asset exceeds setup download limit')
            output.write(chunk)
            print(f'Asset download: {count}/{total or "unknown"} bytes', flush=True)
    if expected and digest(temporary) != expected:
        temporary.unlink()
        raise RuntimeError('Upstream asset SHA256 mismatch')
    temporary.replace(path)


def extract_msi_cabinet(msi_path, output):
    """Read embedded cabinet streams without invoking msiexec or custom actions."""
    msi = ctypes.WinDLL('msi')
    uint = ctypes.c_uint
    msi.MsiOpenDatabaseW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.POINTER(uint)]
    msi.MsiDatabaseOpenViewW.argtypes = [uint, ctypes.c_wchar_p, ctypes.POINTER(uint)]
    msi.MsiViewExecute.argtypes = [uint, uint]
    msi.MsiViewFetch.argtypes = [uint, ctypes.POINTER(uint)]
    msi.MsiRecordGetStringW.argtypes = [uint, uint, ctypes.c_wchar_p, ctypes.POINTER(uint)]
    msi.MsiRecordReadStream.argtypes = [uint, uint, ctypes.c_void_p, ctypes.POINTER(uint)]
    msi.MsiCloseHandle.argtypes = [uint]
    database, view = uint(), uint()
    if msi.MsiOpenDatabaseW(str(msi_path), None, ctypes.byref(database)):
        raise RuntimeError('Cannot read MSI database')
    try:
        if msi.MsiDatabaseOpenViewW(database, 'SELECT `Name`, `Data` FROM `_Streams`', ctypes.byref(view)) or msi.MsiViewExecute(view, 0):
            raise RuntimeError('Cannot read MSI streams')
        count = 0
        while True:
            record = uint()
            result = msi.MsiViewFetch(view, ctypes.byref(record))
            if result == 259:
                break
            if result:
                raise RuntimeError('Cannot fetch MSI stream')
            try:
                length = uint(4096)
                name = ctypes.create_unicode_buffer(4097)
                if msi.MsiRecordGetStringW(record, 1, name, ctypes.byref(length)):
                    raise RuntimeError('Cannot read MSI stream name')
                if not name.value.lower().endswith('.cab'):
                    continue
                cabinet = output / f'payload-{count}.cab'
                with cabinet.open('wb') as destination:
                    while True:
                        buffer = ctypes.create_string_buffer(65536)
                        size = uint(len(buffer))
                        if msi.MsiRecordReadStream(record, 2, buffer, ctypes.byref(size)):
                            raise RuntimeError('Cannot read MSI cabinet')
                        if not size.value:
                            break
                        destination.write(buffer.raw[:size.value])
                subprocess.run(['tar', '-xf', str(cabinet), '-C', str(output)], check=True, timeout=60, capture_output=True, creationflags=CREATE_FLAGS)
                count += 1
            finally:
                msi.MsiCloseHandle(record)
        if not count:
            raise RuntimeError('No MSI embedded cabinet found')
        # MSI File table identifiers for these two upstream files have a leading
        # underscore; preserve extracted originals and create portable names.
        for name in ('7z.exe', '7z.dll'):
            source = output / ('_' + name)
            if source.exists():
                shutil.copy2(source, output / name)
    finally:
        if view.value:
            msi.MsiCloseHandle(view)
        msi.MsiCloseHandle(database)


def setup():
    if os.name != 'nt':
        raise SystemExit('This portable setup is Windows-only. Use your OS Tesseract package elsewhere.')
    LOCAL.mkdir(parents=True, exist_ok=True)
    downloads = LOCAL / 'downloads'; downloads.mkdir(exist_ok=True)
    unpack = LOCAL / '7zip'; unpack.mkdir(exist_ok=True)
    runtime = LOCAL / 'tesseract'; runtime.mkdir(exist_ok=True)
    for name, (url, sha) in ASSETS.items():
        download(url, downloads / name, sha)
    sevenzip = unpack / '7z.exe'
    if not sevenzip.exists():
        extract_msi_cabinet(downloads / '7z2605-x64.msi', unpack)
    if not sevenzip.exists():
        matches = list(unpack.rglob('*7z*'))
        raise RuntimeError(f'MSI extraction did not expose 7z.exe ({[p.name for p in matches]})')
    if not (runtime / 'tesseract.exe').exists():
        subprocess.run([str(sevenzip), 'x', '-y', f'-o{runtime}', str(downloads / 'tesseract-ocr-w64-setup-5.5.3.20260724.exe')],
                       check=True, timeout=120, capture_output=True, creationflags=CREATE_FLAGS)
    executable = runtime / 'tesseract.exe'
    if not executable.exists():
        raise RuntimeError('Tesseract executable not found after unpacking')
    tessdata = runtime / 'tessdata'; tessdata.mkdir(exist_ok=True)
    for name, sha in TESSDATA_ASSETS.items():
        url = f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{TESSDATA_REVISION}/{name}'
        download(url, downloads/name, sha)
        destination = tessdata/name if name != 'LICENSE' else runtime/'TESSDATA-LICENSE'
        shutil.copy2(downloads/name, destination)
    version = subprocess.run([str(executable), '--version'], check=True, timeout=15, capture_output=True, text=True, creationflags=CREATE_FLAGS).stdout.splitlines()[0]
    probe = subprocess.run([str(executable), '--list-langs', '--tessdata-dir', str(tessdata)],
                           check=True, timeout=15, capture_output=True, text=True, creationflags=CREATE_FLAGS).stdout
    languages = sorted(line.strip() for line in probe.splitlines() if line.strip() in {'eng', 'hin', 'pan'})
    if languages != ['eng', 'hin', 'pan']:
        raise RuntimeError('Required OCR language assets were not recognized')
    manifest = {'schema_version': 1, 'runtime_version': version, 'languages': languages,
                'setup': 'app-local extraction; installers never executed; no registry/PATH changes',
                'sources': {name: {'url': url, 'sha256': sha} for name, (url, sha) in ASSETS.items()},
                'tessdata': {'repository': 'https://github.com/tesseract-ocr/tessdata_fast',
                             'revision': TESSDATA_REVISION, 'sha256': TESSDATA_ASSETS,
                             'license': 'Apache-2.0; TESSDATA-LICENSE included'},
                'runtime_sha256': {str(path.relative_to(runtime)).replace('\\','/'): digest(path)
                                   for path in runtime.rglob('*') if path.is_file() and path.suffix.lower() in {'.exe', '.dll', '.traineddata'}}}
    (LOCAL/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'runtime_version': version, 'languages': languages, 'manifest': 'tools/ocr/manifest.json'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Print local runtime/language availability without downloading')
    args = parser.parse_args()
    if args.probe:
        import sys
        sys.path.insert(0, str(ROOT))
        from apps.api.extraction import ocr_capabilities
        print(json.dumps(ocr_capabilities()))
    else:
        setup()
