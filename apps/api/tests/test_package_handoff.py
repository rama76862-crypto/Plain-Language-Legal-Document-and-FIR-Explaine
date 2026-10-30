import json
import zipfile
import pytest
from apps.api.scripts.package_handoff import build_bundle


def test_bundle_contains_source_and_examples_but_no_private_files(tmp_path):
    root=tmp_path/'repo'; api=root/'apps'/'api'; api.mkdir(parents=True)
    (root/'contracts').mkdir(); (root/'contracts'/'example.json').write_text('{}')
    (api/'main.py').write_text('# synthetic source')
    (api/'README.md').write_text('Synthetic instructions')
    (api/'.env.example').write_text('ML_SERVICE_TOKEN=')
    (api/'.env').write_text('SECRET_TOKEN=private')
    (api/'__pycache__').mkdir(); (api/'__pycache__'/'ignored.py').write_text('private cache')
    (api/'private.pdf').write_bytes(b'private upload')
    (root/'work'/'runtime').mkdir(parents=True); (root/'work'/'runtime'/'private.json').write_text('private')
    (root/'apps'/'ml').mkdir(); (root/'apps'/'ml'/'owned.py').write_text('other role')
    (root/'other-role.md').write_text('other role')
    output=tmp_path/'handoff.zip'; summary=build_bundle(output,root)
    assert summary['contains_private_runtime'] is False
    with zipfile.ZipFile(output) as archive:
        names=set(archive.namelist()); assert 'apps/api/.env.example' in names
        assert 'apps/api/.env' not in names and not any('runtime' in name or '__pycache__' in name for name in names)
        assert 'apps/ml/owned.py' not in names and 'other-role.md' not in names
        manifest=json.loads(archive.read('HANDOFF-MANIFEST.json'))
        assert all(len(item['sha256'])==64 for item in manifest['files'])
    with pytest.raises(FileExistsError): build_bundle(output,root)
