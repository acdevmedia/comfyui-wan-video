#!/usr/bin/env python3
"""Print the template payload, or explicitly create/update it with --apply.

The template always points at the model-version tag in config/runpod-template.json
(e.g. wan-comfyui:2.2), which every passing develop build moves forward,
like the LTX and Eros templates. Digests and sha-<commit> tags are refused: they freeze
the template on one build. Pin a single Pod to a sha- tag by hand when you need to.
"""
import argparse,json,os,re,urllib.error,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UA={'User-Agent':'curl/8.0'}
def check_image(image):
    """The template image must be a model tag (no digest, no sha- tag) that exists in GHCR."""
    m=re.fullmatch(r'ghcr\.io/([^@:]+):([A-Za-z0-9_.-]+)',image)
    if not m or m.group(2).startswith('sha-') or m.group(2)=='latest':
        raise SystemExit(f'Template image must be a model-version tag, not a digest, sha- or latest tag: {image}')
    return m.group(1),m.group(2)
def tag_published(repo,tag):
    token=json.load(urllib.request.urlopen(urllib.request.Request(f'https://ghcr.io/token?scope=repository:{repo}:pull',headers=UA),timeout=30))['token']
    accept='application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'
    try:urllib.request.urlopen(urllib.request.Request(f'https://ghcr.io/v2/{repo}/manifests/{tag}',method='HEAD',headers={**UA,'Authorization':'Bearer '+token,'Accept':accept}),timeout=30);return True
    except urllib.error.HTTPError as e:
        if e.code in (401,403,404):return False
        raise
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--apply',action='store_true');p.add_argument('--registry-auth-id',help='Existing Runpod registry authorization for a private test template');p.add_argument('--public',action='store_true',help='Publish the template to Runpod Explore');args=p.parse_args()
    payload=json.loads((ROOT/'config/runpod-template.json').read_text())
    repo,tag=check_image(payload['imageName'])
    if args.public:payload['isPublic']=True
    if args.registry_auth_id:
        if args.public:raise SystemExit('Public templates must use an anonymously pullable image')
        payload['containerRegistryAuthId']=args.registry_auth_id
    payload['readme']=(ROOT/'README.md').read_text()
    if not args.apply:print(json.dumps(payload,indent=2));return
    if not tag_published(repo,tag):raise SystemExit(f'{payload["imageName"]} is not anonymously pullable from GHCR yet; publish it from develop first')
    key=os.environ.get('RUNPOD_API_KEY')
    if not key:raise SystemExit('RUNPOD_API_KEY is required')
    def request(path,method='GET',data=None):
        req=urllib.request.Request('https://rest.runpod.io/v1'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={**UA,'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    matches=[x for x in request('/templates') if x['name']==payload['name']]
    if len(matches)>1:raise SystemExit('Duplicate template names; refusing ambiguous update')
    update={k:v for k,v in payload.items() if k not in ('isServerless','category')}  # create-only fields; PATCH rejects them
    result=request('/templates/'+matches[0]['id'],'PATCH',update) if matches else request('/templates','POST',payload)
    print(json.dumps({k:result.get(k) for k in ('id','name','imageName')},indent=2))
if __name__=='__main__':main()
