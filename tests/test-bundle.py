#!/usr/bin/env python3
import importlib.util,json,math,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('video',ROOT/'custom_nodes/acdev_video/__init__.py');video=importlib.util.module_from_spec(spec);spec.loader.exec_module(video)
class BundleTests(unittest.TestCase):
 def test_controls(self):
  c=video.VideoControls()
  for family,expected,fps in [('wan',81,16),('h3',124,24)]:
   args=dict(family=family,width=832,height=480,length_mode='duration',duration=5,num_frames=81,prompt='test',negative_prompt='bad')
   a=c.run(**args);b=c.run(**args)
   self.assertEqual(a[2:6],(expected,float(fps),'test','bad'));self.assertEqual(a,b);self.assertFalse(hasattr(c,'IS_CHANGED'))
   args.update(length_mode='frames',num_frames=82);self.assertEqual(c.run(**args)[2],85 if family=='wan' else 90)
   with self.assertRaises(ValueError):c.run(**{**args,'width':833})
   with self.assertRaises(ValueError):c.run(**{**args,'num_frames':999})
 def test_random_seed(self):
  r=video.RandomSeed();self.assertNotEqual(r.run(),r.run());self.assertTrue(math.isnan(r.IS_CHANGED()))
 def test_manifests_and_graphs(self):
  for v in (ROOT/'versions').iterdir():
   schemas=json.loads((v/'node-input-schemas.json').read_text())
   p=json.loads((v/'profile.json').read_text());names={Path(m['file']).name for m in p['models']}
   self.assertRegex(p['comfy_commit'],r'^[0-9a-f]{40}$')
   for m in p['models']:
    self.assertRegex(m['revision'],r'^[0-9a-f]{40}$');self.assertRegex(m['sha256'],r'^[0-9a-f]{64}$');self.assertGreater(m['size'],0)
   for item in json.loads((v/'workflow-catalog.json').read_text()):
    api=json.loads((v/item['api']).read_text());ui=json.loads((v/item['ui']).read_text());nodes={n['id']:n for n in ui['nodes']}
    controls=[k for k,n in api.items() if n['class_type']=='ACDEVVideoControls'];self.assertEqual(len(controls),1);control=controls[0]
    self.assertTrue(api[control]['inputs']['negative_prompt'])
    seeds=[k for k,n in api.items() if n['class_type']=='ACDEVRandomSeed'];self.assertEqual(len(seeds),1);seed=seeds[0]
    self.assertEqual(len(api),len(nodes))
    for k,n in api.items():
     self.assertEqual(n['class_type'],nodes[int(k)]['type'])
     if n['class_type'] in schemas:
      schema=schemas[n['class_type']];self.assertLessEqual(set(schema['required']),set(n['inputs']));self.assertLessEqual(set(n['inputs']),set(schema['allowed']))
     for name,value in n['inputs'].items():
      if isinstance(value,list):
       source=nodes[int(value[0])];self.assertLess(value[1],len(source['outputs']))
       match=next(i for i in nodes[int(k)]['inputs'] if i['name']==name);link=next(l for l in ui['links'] if l[0]==match['link']);self.assertEqual(link[1:4],[int(value[0]),value[1],int(k)])
      elif name in ('unet_name','clip_name','vae_name','lora_name'):self.assertIn(value,names)
     if n['class_type'] in ('RandomNoise','KSamplerAdvanced'):self.assertEqual(n['inputs']['noise_seed'],[seed,0])
     if n['class_type']=='ACDEVSaveVideo':self.assertEqual(n['inputs']['seed'],[seed,0])
    for l in ui['links']:
     self.assertIn(l[0],nodes[l[1]]['outputs'][l[2]]['links']);self.assertEqual(nodes[l[3]]['inputs'][l[4]]['link'],l[0])
    if item['mode'] in ('eros','remix'):self.assertFalse(any(n['class_type']=='LoraLoaderModelOnly' for n in api.values()))
    # Only the seed node may be uncached; everything else must be reusable between jobs.
    for k,n in api.items():
     if n['class_type'] in ('CLIPTextEncode','WanImageToVideo','MiniMaxH3ImageToVideo'):self.assertNotIn(seed,json.dumps(n['inputs']))
    # With real CFG the negative must see the reference image too (WAN: WanImageToVideo, H3: keyframed encode).
    for gd in api.values():
     if gd['class_type'] in ('CFGGuider','KSamplerAdvanced') and gd['inputs']['cfg']>1:
      neg=api[gd['inputs']['negative'][0]]
      self.assertIn(neg['class_type'],('WanImageToVideo','MiniMaxH3ImageToVideo'))
      self.assertIn('LoadImage',[api[v[0]]['class_type'] for v in neg['inputs'].values() if isinstance(v,list)])
    if item['mode']=='turbo':self.assertEqual(sum(n['class_type']=='LoraLoaderModelOnly' for n in api.values()),2)
 def test_provision_skips_rehash_until_file_changes(self):
  import hashlib,os,sys,tempfile,types
  from unittest import mock
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);payload=b'weights'*1000;versions=tmp/'versions'/'v1';(versions/'workflows').mkdir(parents=True)
   (versions/'profile.json').write_text(json.dumps(dict(default_mode='m',bundle_version='0',models=[dict(repo='r',revision='0'*40,file='sub/w.safetensors',directory='diffusion_models',size=len(payload),sha256=hashlib.sha256(payload).hexdigest(),modes=['all'])])))
   (versions/'workflow-catalog.json').write_text(json.dumps([dict(name='w',mode='m',ui='workflows/w.json')]));(versions/'workflows/w.json').write_text('{}')
   downloads=[]
   def fake_download(repo_id,filename,revision,local_dir,token,force_download):
    downloads.append(force_download);out=Path(local_dir)/filename;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(payload);return str(out)
   spec=importlib.util.spec_from_file_location('provision',ROOT/'scripts/provision.py');prov=importlib.util.module_from_spec(spec);spec.loader.exec_module(prov)
   env={'VIDEO_VERSIONS_DIR':str(tmp/'versions'),'COMFYUI_DIR':str(tmp/'comfy'),'MODEL_MODE':'m','VIDEO_VERSION':'v1'}
   with mock.patch.dict(os.environ,env),mock.patch.dict(sys.modules,{'huggingface_hub':types.SimpleNamespace(hf_hub_download=fake_download)}),mock.patch.object(prov.shutil,'disk_usage',return_value=types.SimpleNamespace(free=10**12)):
    hashed=[];real=prov.digest
    with mock.patch.object(prov,'digest',side_effect=lambda p:(hashed.append(p),real(p))[1]):
     prov.main();self.assertEqual((len(downloads),len(hashed)),(1,1))
     prov.main();self.assertEqual((len(downloads),len(hashed)),(1,1))  # ledger hit: no download, no hash
     import time;time.sleep(0.05)  # kernel timestamps are coarse-grained
     target=tmp/'comfy/models/diffusion_models/w.safetensors';target.write_bytes(payload)  # rewrite changes ctime
     prov.main();self.assertEqual((len(downloads),len(hashed)),(1,2))  # re-hashed, still valid
     time.sleep(0.05);target.write_bytes(b'x'*len(payload))
     prov.main();self.assertEqual(len(downloads),2);self.assertTrue(downloads[-1])  # corrupt: forced re-download
     with mock.patch.dict(os.environ,{'VERIFY_MODELS':'full'}):n=len(hashed);prov.main();self.assertEqual(len(hashed),n+1)
 def test_context_excludes_secrets(self):
  ignore=(ROOT/'.dockerignore').read_text();self.assertTrue(ignore.startswith('*\n'));self.assertNotIn('!.env',ignore)
  for v in (ROOT/'versions').iterdir():self.assertIn(v.name,(ROOT/'Dockerfile').read_text())
if __name__=='__main__':unittest.main()
