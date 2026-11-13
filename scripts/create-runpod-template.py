#!/usr/bin/env python3
"""Print the template payload, or explicitly create/update it with --apply."""
import argparse,json,os,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--image',help='Published image digest or tested tag');args=p.parse_args()
    payload=json.loads((ROOT/'config/runpod-template.json').read_text())
    if args.image:payload['imageName']=args.image
    payload['readme']=(ROOT/'README.md').read_text()
    if not args.apply:print(json.dumps(payload,indent=2));return
    if not args.image:raise SystemExit('--apply requires --image naming an already published and tested image')
    key=os.environ.get('RUNPOD_API_KEY')
    if not key:raise SystemExit('RUNPOD_API_KEY is required')
    def request(path,method='GET',data=None):
        req=urllib.request.Request('https://rest.runpod.io/v1'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    matches=[x for x in request('/templates') if x['name']==payload['name']]
    if len(matches)>1:raise SystemExit('Duplicate template names; refusing ambiguous update')
    result=request('/templates/'+matches[0]['id'],'PATCH',payload) if matches else request('/templates','POST',payload)
    print(json.dumps({k:result.get(k) for k in ('id','name','imageName')},indent=2))
if __name__=='__main__':main()
