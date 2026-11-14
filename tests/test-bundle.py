#!/usr/bin/env python3
import importlib.util,json,math,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('video',ROOT/'custom_nodes/acdev_video/__init__.py');video=importlib.util.module_from_spec(spec);spec.loader.exec_module(video)
def flatten(ui):
 """Expand the single subgraph back into the flat graph ComfyUI executes."""
 (sg,)=ui['definitions']['subgraphs'];(outer,)=[n for n in ui['nodes'] if n['type']==sg['id']]
 nodes={n['id']:n for n in ui['nodes'] if n is not outer};nodes.update({n['id']:n for n in sg['nodes']})
 top={l[0]:l for l in ui['links']};inner={l['id']:l for l in sg['links']};edges=set();promoted={}
 def name_of(node,slot):return node['inputs'][slot]['name']
 for l in sg['links']:
  if l['target_id']==-20:continue
  if l['origin_id']==-10:
   src=outer['inputs'][l['origin_slot']]
   if src['link'] is None:  # promoted widget: value lives on the outer node
    widgets=[i for i in outer['inputs'] if i.get('widget')];promoted[src['name']]=outer['widgets_values'][widgets.index(src)];continue
   t=top[src['link']];edges.add((t[1],t[2],l['target_id'],name_of(nodes[l['target_id']],l['target_slot'])))
  else:edges.add((l['origin_id'],l['origin_slot'],l['target_id'],name_of(nodes[l['target_id']],l['target_slot'])))
 for t in ui['links']:
  if t[1]==outer['id']:
   (o,)=[inner[i] for i in sg['outputs'][t[2]]['linkIds']];edges.add((o['origin_id'],o['origin_slot'],t[3],name_of(nodes[t[3]],t[4])))
  elif t[3]!=outer['id']:edges.add((t[1],t[2],t[3],name_of(nodes[t[3]],t[4])))
 for n in sg['nodes']:  # every inner link id must be listed on both ends
  for i in n['inputs']:
   if i['link'] is not None:assert inner[i['link']]['target_id']==n['id']
 return nodes,edges,promoted
class BundleTests(unittest.TestCase):
 def test_controls(self):
  c=video.VideoControls();self.assertGreaterEqual(c.INPUT_TYPES()['required']['duration'][1]['max'],1_000_000);self.assertNotIn('num_frames',c.INPUT_TYPES()['required']);self.assertNotIn('length_mode',c.INPUT_TYPES()['required'])
  for family,expected,fps,longest in [('wan',81,16,241),('h3',124,24,362)]:
   args=dict(family=family,width=832,height=480,duration=5,prompt='test',negative_prompt='bad')
   a=c.run(**args);b=c.run(**args)
   self.assertEqual(a[2:6],(expected,float(fps),'test','bad'));self.assertEqual(a,b);self.assertFalse(hasattr(c,'IS_CHANGED'))
   self.assertEqual(c.run(**{**args,'duration':15})[2],longest)
   self.assertEqual(c.run(**{**args,'duration':60})[2],961 if family=='wan' else 1450)  # no upper cap
   self.assertEqual(c.run(**{**args,'duration':600})[2]>=600*fps,True)
   self.assertEqual(c.run(**{**args,'duration':0.2})[2],5)  # tiny requests snap up to the minimum
   with self.assertRaises(ValueError):c.run(**{**args,'width':833})
 def test_random_seed(self):
  r=video.RandomSeed();a,b=r.run(0)[0],r.run(0)[0];self.assertNotEqual(a,b);self.assertTrue(0<a<=video.MAX_SEED)
  self.assertEqual(r.run(123),(123,));self.assertTrue(math.isnan(r.IS_CHANGED(seed=0)));self.assertEqual(r.IS_CHANGED(seed=7),7)
  spec=r.INPUT_TYPES()['required']['seed'][1];self.assertEqual(spec['max'],2**64-1);self.assertNotIn('control_after_generate',spec)  # seed-controls.js randomizes before queue
 def test_manifests_and_graphs(self):
  for v in (ROOT/'versions').iterdir():
   schemas=json.loads((v/'node-input-schemas.json').read_text())
   p=json.loads((v/'profile.json').read_text());names={Path(m['file']).name for m in p['models']}
   self.assertRegex(p['comfy_commit'],r'^[0-9a-f]{40}$')
   for m in p['models']:
    self.assertRegex(m['revision'],r'^[0-9a-f]{40}$');self.assertRegex(m['sha256'],r'^[0-9a-f]{64}$');self.assertGreater(m['size'],0)
   for item in json.loads((v/'workflow-catalog.json').read_text()):
    api=json.loads((v/item['api']).read_text());ui=json.loads((v/item['ui']).read_text());nodes,edges,promoted=flatten(ui)
    controls=[k for k,n in api.items() if n['class_type']=='ACDEVVideoControls'];self.assertEqual(len(controls),1);control=controls[0]
    self.assertTrue(api[control]['inputs']['negative_prompt'])
    seeds=[k for k,n in api.items() if n['class_type']=='ACDEVRandomSeed'];self.assertEqual(len(seeds),1);seed=seeds[0]
    self.assertEqual(sorted(map(int,api)),sorted(nodes))
    self.assertEqual(edges,{(int(v_[0]),v_[1],int(k),name) for k,n in api.items() for name,v_ in n['inputs'].items() if isinstance(v_,list)})
    owner={'width':'ACDEVVideoControls','height':'ACDEVVideoControls','duration':'ACDEVVideoControls','negative_prompt':'ACDEVVideoControls','seed':'ACDEVRandomSeed','steps':'BasicScheduler','cfg':'CFGGuider'}
    expected={w:next(n['inputs'][w] for n in api.values() if n['class_type']==c) for w,c in owner.items() if any(n['class_type']==c for n in api.values())}
    self.assertEqual(promoted,expected)  # every Shot settings control drives the value ComfyUI executes
    if 'BasicScheduler' in json.dumps(api):self.assertTrue({'steps','cfg'}<=set(promoted))  # H3 filmmaker controls
    (prompt_node,)=[k for k,n in api.items() if n['class_type']=='PrimitiveStringMultiline'];self.assertEqual(api[control]['inputs']['prompt'],[prompt_node,0])
    (outer,)=[n for n in ui['nodes'] if n['type']==ui['definitions']['subgraphs'][0]['id']]
    self.assertEqual(len([i for i in outer['inputs'] if i.get('widget')]),len(outer['widgets_values']),'one value per widget slot or the UI shifts values')
    titles=[n.get('title') for n in ui['nodes']]
    self.assertEqual(titles,['01 · Describe your shot']+(['Starting image'] if item['task']=='i2v' else [])+['02 · Shot settings','03 · Your video'])
    self.assertEqual(api[seed]['inputs'],{'seed':0})  # API default: server-side random seed
    self.assertRegex(Path(item['ui']).name,r'^\d\d [A-Z][\w -]+ - (Image|Text) to Video\.json$')
    for k,n in api.items():
     self.assertEqual(n['class_type'],nodes[int(k)]['type'])
     if n['class_type'] in schemas:
      schema=schemas[n['class_type']];self.assertLessEqual(set(schema['required']),set(n['inputs']));self.assertLessEqual(set(n['inputs']),set(schema['allowed']))
     for name,value in n['inputs'].items():
      if isinstance(value,list):self.assertLess(value[1],len(nodes[int(value[0])]['outputs']))
      elif name in ('unet_name','clip_name','vae_name','lora_name'):self.assertIn(value,names)
     if n['class_type'] in ('RandomNoise','KSamplerAdvanced'):self.assertEqual(n['inputs']['noise_seed'],[seed,0])
     if n['class_type']=='ACDEVSaveVideo':self.assertEqual(n['inputs']['seed'],[seed,0])
    top={n['id']:n for n in ui['nodes']};sg=ui['definitions']['subgraphs'][0];inn={n['id']:n for n in sg['nodes']}
    for l in ui['links']:
     self.assertIn(l[0],top[l[1]]['outputs'][l[2]]['links']);self.assertEqual(top[l[3]]['inputs'][l[4]]['link'],l[0])
    for l in sg['links']:
     if l['origin_id']==-10:self.assertIn(l['id'],sg['inputs'][l['origin_slot']]['linkIds'])
     else:self.assertIn(l['id'],inn[l['origin_id']]['outputs'][l['origin_slot']]['links'])
     if l['target_id']==-20:self.assertIn(l['id'],sg['outputs'][l['target_slot']]['linkIds'])
     else:self.assertEqual(inn[l['target_id']]['inputs'][l['target_slot']]['link'],l['id'])
    ids=[n['id'] for n in ui['nodes']]+list(inn);self.assertEqual(len(ids),len(set(ids)))
    lids=[l[0] for l in ui['links']]+[l['id'] for l in sg['links']];self.assertEqual(len(lids),len(set(lids)));self.assertLessEqual(max(lids),ui['last_link_id'])
    if item['mode'] in ('eros','remix'):self.assertFalse(any(n['class_type']=='LoraLoaderModelOnly' for n in api.values()))
    # Only the seed node may be uncached; everything else must be reusable between jobs.
    for k,n in api.items():
     if n['class_type'] in ('CLIPTextEncode','WanImageToVideo','MiniMaxH3ImageToVideo'):self.assertFalse(any(isinstance(value,list) and value[0]==seed for value in n['inputs'].values()))
    # With real CFG the negative must see the reference image too (WAN: WanImageToVideo, H3: keyframed encode).
    for gd in api.values():
     if gd['class_type'] in ('CFGGuider','KSamplerAdvanced') and gd['inputs']['cfg']>1 and item.get('task','i2v')=='i2v':
      neg=api[gd['inputs']['negative'][0]]
      self.assertIn(neg['class_type'],('WanImageToVideo','MiniMaxH3ImageToVideo'))
      self.assertIn('LoadImage',[api[v[0]]['class_type'] for v in neg['inputs'].values() if isinstance(v,list)])
    if item['task']=='i2v' and 'MiniMaxH3ImageToVideo' in json.dumps(api):  # H3 CFG is user-adjustable, so the negative always carries the image
     for gd in api.values():
      if gd['class_type']=='CFGGuider':
       neg=api[gd['inputs']['negative'][0]];self.assertEqual(neg['class_type'],'MiniMaxH3ImageToVideo');self.assertIn('first_frame',neg['inputs'])
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
 def test_provision_downloads_in_parallel(self):
  import hashlib,os,sys,tempfile,threading,time,types
  from unittest import mock
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);versions=tmp/'versions'/'v1';(versions/'workflows').mkdir(parents=True)
   payloads={f'w{i}.safetensors':bytes([i])*4096 for i in range(3)}
   (versions/'profile.json').write_text(json.dumps(dict(default_mode='m',bundle_version='0',models=[dict(repo='r',revision='0'*40,file=n,directory='loras',size=len(p),sha256=hashlib.sha256(p).hexdigest(),modes=['all']) for n,p in payloads.items()])))
   (versions/'workflow-catalog.json').write_text('[]')
   active=[0];peak=[0];lock=threading.Lock()
   def fake_download(repo_id,filename,revision,local_dir,token,force_download):
    with lock:active[0]+=1;peak[0]=max(peak[0],active[0])
    time.sleep(0.2);out=Path(local_dir)/filename;out.write_bytes(payloads[filename])
    with lock:active[0]-=1
    return str(out)
   spec=importlib.util.spec_from_file_location('provision',ROOT/'scripts/provision.py');prov=importlib.util.module_from_spec(spec);spec.loader.exec_module(prov)
   env={'VIDEO_VERSIONS_DIR':str(tmp/'versions'),'COMFYUI_DIR':str(tmp/'comfy'),'MODEL_MODE':'all','VIDEO_VERSION':'v1'}
   with mock.patch.dict(os.environ,env),mock.patch.dict(sys.modules,{'huggingface_hub':types.SimpleNamespace(hf_hub_download=fake_download)}),mock.patch.object(prov.shutil,'disk_usage',return_value=types.SimpleNamespace(free=10**12)):
    prov.main()
   self.assertGreater(peak[0],1)
   ledger=json.loads((tmp/'comfy/models/.acdev-verified.json').read_text());self.assertEqual(len(ledger),3)
   for n,p in payloads.items():self.assertEqual((tmp/'comfy/models/loras'/n).read_bytes(),p)
 def test_context_excludes_secrets(self):
  ignore=(ROOT/'.dockerignore').read_text();self.assertTrue(ignore.startswith('*\n'));self.assertNotIn('!.env',ignore)
  for v in (ROOT/'versions').iterdir():self.assertIn(v.name,(ROOT/'Dockerfile').read_text())
if __name__=='__main__':unittest.main()
