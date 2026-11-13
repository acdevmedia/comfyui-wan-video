#!/usr/bin/env python3
"""Create redistributable workflows/template assets without weights or credentials."""
import hashlib,json,os,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist';out.mkdir(exist_ok=True)
version=next((ROOT/'versions').iterdir()).name
profile=json.loads((ROOT/'versions'/version/'profile.json').read_text())
repo=os.getenv('GITHUB_REPOSITORY','acdevmedia/comfyui-wan-video')
tag=os.getenv('GITHUB_REF_NAME','v'+profile['bundle_version'])
image=json.loads((ROOT/'config/runpod-template.json').read_text())['imageName'].split(':')[0]+':'+tag
payload=json.loads((ROOT/'config/runpod-template.json').read_text());payload['imageName']=image
(out/'runpod-template.json').write_text(json.dumps(payload,indent=2)+'\n')
archive=out/(repo.split('/')[-1]+'-'+tag+'-workflows.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for path in sorted((ROOT/'versions'/version).rglob('*.json')):z.write(path,path.relative_to(ROOT))
 for path in sorted((ROOT/'.runpod').glob('*')):
  if path.is_file():z.write(path,path.relative_to(ROOT))
 for path in [ROOT/'README.md',ROOT/'docs/research.md']:z.write(path,path.relative_to(ROOT))
 z.write(out/'runpod-template.json','runpod-template.json')
notes=f"# Video bundle {tag}\n\nModel profile: {version}. Container: `{image}`.\n\nContainer installation, live ComfyUI API schemas and authenticated output downloads are CPU-smoke-tested before this release is published. GPU generation and performance remain unvalidated; do not infer GPU quality or compatibility from CPU tests.\n\nRunpod payload is private by default until validated; Hub publication is a separate operation. No model weights or credentials are included.\n"
(out/'RELEASE.md').write_text(notes)
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print('Release assets:',', '.join(p.name for p in sorted(out.iterdir())))
