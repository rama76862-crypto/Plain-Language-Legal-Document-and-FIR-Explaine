"""Source-only BE1 handoff; excludes runtime, binaries, credentials and other roles."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]


def build_bundle(output: Path,repo_root: Path=ROOT):
    root=repo_root.resolve(); output=Path(output).absolute()
    if output.exists(): raise FileExistsError('Handoff output exists; choose a new path.')
    candidates=[]
    for folder in [root/'apps'/'api',root/'contracts']:
        for path in folder.rglob('*'):
            if not path.is_file() or path.is_symlink(): continue
            if '__pycache__' in path.parts or path.name=='.env': continue
            if path.suffix not in {'.py','.md','.json','.txt'} and path.name!='.env.example': continue
            if not path.resolve().is_relative_to(root): continue
            candidates.append(path)
    for name in ['pytest.ini','.gitignore','03-BACKEND-1-API-Extraction-Sessions.md']:
        path=root/name
        if path.is_file() and not path.is_symlink(): candidates.append(path)
    files={path.relative_to(root).as_posix():path.read_bytes() for path in sorted(candidates)}
    if not files: raise ValueError('No BE1 source files found.')
    manifest={'scope':'Backend 1 source-only handoff','contains_private_runtime':False,
        'ocr_binaries_included':False,'model_tested':False,
        'files':[dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in files.items()]}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items(): archive.writestr(name,data)
        archive.writestr('HANDOFF-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    return {'source_files':len(files),'archive_bytes':output.stat().st_size,
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'contains_private_runtime':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try: summary=build_bundle(args.output)
    except (FileExistsError,ValueError) as error: parser.exit(2,str(error)+'\n')
    print(json.dumps(summary,indent=2))
