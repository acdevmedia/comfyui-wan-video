#!/usr/bin/env python3
import json
from pathlib import Path
r=Path(__file__).resolve().parents[1]
t=json.loads((r/'config/runpod-template.json').read_text())
h=json.loads((r/'.runpod/hub.json').read_text())
s=json.loads((r/'.runpod/tests.json').read_text())
assert h['type']=='serverless' and h['config']['endpointType']=='LB'
assert h['category']=='video' and h['config']['allowedCudaVersions']==['13.0']
assert s['config']['allowedCudaVersions']==h['config']['allowedCudaVersions']
env={x['key']:x['value'] for x in h['config']['env']}
test_env={x['key']:x['value'] for x in s['config']['env']}
# The Hub's automated test may use one mode to avoid downloading every model; all else must match.
assert {k:v for k,v in test_env.items() if k!='MODEL_MODE'}=={k:v for k,v in env.items() if k!='MODEL_MODE'}
modes={w['mode'] for v in (r/'versions').iterdir() for w in json.loads((v/'workflow-catalog.json').read_text())}
assert env['MODEL_MODE']=='all' and test_env['MODEL_MODE'] in modes
assert {k:env[k] for k in t['env']}==t['env']
assert env['PORT']=='8000' and env['PORT_HEALTH']=='8001'
assert t['volumeInGb']==0 and h['config']['containerDiskInGb']==t['containerDiskInGb']
assert 'handler.py' in (r/'.runpod/Dockerfile').read_text()
print('PASS: Hub metadata, test configuration and Pod template stay synchronized')
