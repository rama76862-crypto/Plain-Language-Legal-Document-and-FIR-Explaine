"""Export reviewed examples and OpenAPI without starting services."""
import json
from pathlib import Path
from apps.api.main import create_app
from apps.api.scripts.publish_examples import examples, ROOT

if __name__=='__main__':
    (ROOT/'contracts'/'openapi.json').write_text(json.dumps(create_app().openapi(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'contracts'/'v1-examples.json').write_text(json.dumps(examples(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Preserve the singular handoff path expected by FE1/FE2 as one result example.
    (ROOT/'contracts'/'v1-example.json').write_text(json.dumps(examples()['analysis_snapshots']['complete']['result'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Exported OpenAPI (10 public operations) and synthetic examples.')
