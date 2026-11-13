#!/usr/bin/env python3
"""Pinned model provisioning and non-destructive workflow installation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(16*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def fingerprint(path):
    # ctime_ns cannot be set by user tools and inode changes on replacement, so any
    # rewrite, copy-over or mv invalidates the record without trusting mtime alone.
    st=path.stat()
    return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]

def load_verified(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}

def save_verified(path,records):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(records,indent=1));temporary.replace(path)

def main():
    from huggingface_hub import hf_hub_download
    versions=Path(os.getenv('VIDEO_VERSIONS_DIR','/opt/video/versions'))  # override only for tests
    available=list(versions.iterdir())
    if len(available)!=1:raise SystemExit('Image must contain exactly one version')
    version=os.environ.get('VIDEO_VERSION',available[0].name)
    if version!=available[0].name:raise SystemExit('VIDEO_VERSION does not match this image; use the matching image tag')
    source=versions/version
    profile=json.loads((source/'profile.json').read_text())
    mode=os.getenv('MODEL_MODE',profile['default_mode'])
    catalog=json.loads((source/'workflow-catalog.json').read_text())
    if mode not in [w['mode'] for w in catalog]+['all']:raise SystemExit('Invalid MODEL_MODE')
    root=Path(os.getenv('COMFYUI_DIR','/workspace/ComfyUI'));models=root/'models';models.mkdir(parents=True,exist_ok=True)
    selected=[m for m in profile['models'] if mode=='all' or 'all' in m['modes'] or mode in m['modes']]
    required=sum(m['size'] for m in selected if not (models/m['directory']/Path(m['file']).name).exists())
    if shutil.disk_usage(root).free<required+10*10**9:raise SystemExit('Not enough storage: model downloads plus 10 GB output reserve required')
    token=os.getenv('HF_TOKEN') or None
    if token and token.startswith('{{'):token=None
    # Re-hashing ~40 GB from a network volume costs minutes per boot. A file is
    # skipped only when its SHA256 was verified earlier and its inode, size,
    # mtime and ctime are all unchanged. VERIFY_MODELS=full forces a re-hash.
    ledger=models/'.acdev-verified.json'
    full=os.getenv('VERIFY_MODELS','fast').lower()=='full'
    verified={} if full else load_verified(ledger)
    for m in selected:
        dest=models/m['directory'];dest.mkdir(parents=True,exist_ok=True);target=dest/Path(m['file']).name
        key=f'{m["directory"]}/{target.name}'
        if target.exists() and target.stat().st_size==m['size']:
            record=verified.get(key)
            if record and record.get('sha256')==m['sha256'] and record.get('stat')==fingerprint(target):
                print(f'[models] previously verified {target.name}',flush=True);continue
            print(f'[models] hashing existing {target.name}',flush=True)
            if digest(target)==m['sha256']:
                verified[key]={'sha256':m['sha256'],'stat':fingerprint(target)};save_verified(ledger,verified)
                print(f'[models] verified existing {target.name}',flush=True);continue
        stale=target.exists();verified.pop(key,None)
        print(f'[models] downloading {target.name} ({m["size"]/1e9:.2f} GB)',flush=True)
        # A present-but-wrong file must not be accepted from the Hub's local metadata.
        path=Path(hf_hub_download(repo_id=m['repo'],filename=m['file'],revision=m['revision'],local_dir=dest,token=token,force_download=stale))
        if path.stat().st_size!=m['size'] or digest(path)!=m['sha256']:
            path.unlink(missing_ok=True);raise SystemExit('Model integrity check failed: '+target.name)
        if path!=target:path.replace(target)
        verified[key]={'sha256':m['sha256'],'stat':fingerprint(target)};save_verified(ledger,verified)
    dest=root/'user/default/workflows'/f'ACDEV {version} bundle {profile["bundle_version"]}';dest.mkdir(parents=True,exist_ok=True)
    for w in catalog:
        if mode!='all' and w['mode']!=mode:continue
        target=dest/(w['name']+'.json')
        # Exclusive create preserves user edits on every restart.
        with tempfile.NamedTemporaryFile(mode='w',dir=dest,delete=False) as f:
            temporary=Path(f.name);f.write((source/w['ui']).read_text())
        try:
            os.link(temporary,target)  # Atomic and exclusive; never replace user edits.
        except FileExistsError:pass
        finally:temporary.unlink(missing_ok=True)
    print('[models] Provisioning finished. ComfyUI starts next.',flush=True)
if __name__=='__main__':main()
