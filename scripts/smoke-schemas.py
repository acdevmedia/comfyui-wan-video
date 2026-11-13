#!/usr/bin/env python3
"""Build-time live ComfyUI schema validation without downloading model weights."""
import json,os,subprocess,time,urllib.request
from pathlib import Path
p=subprocess.Popen(['python3','/opt/ComfyUI/main.py','--cpu','--listen','127.0.0.1','--port','18188','--disable-auto-launch'])
try:
 for _ in range(120):
  if p.poll() is not None:raise SystemExit('ComfyUI exited before becoming ready')
  try:
   with urllib.request.urlopen('http://127.0.0.1:18188/object_info',timeout=2) as r:schemas=json.load(r)
   break
  except OSError:time.sleep(1)
 else:raise SystemExit('ComfyUI startup timeout')
 for path in Path('/opt/video/versions').glob('*/api/*.json'):
  graph=json.loads(path.read_text())
  for key,node in graph.items():
   kind=node['class_type'];assert kind in schemas,(path,kind,'missing node');s=schemas[kind];inputs=node['inputs']
   required=s['input'].get('required',{});optional=s['input'].get('optional',{})
   assert set(required)<=set(inputs),(path,kind,'missing',set(required)-set(inputs))
   assert set(inputs)<=set(required)|set(optional),(path,kind,'unknown inputs',set(inputs)-set(required)-set(optional))
   for name,value in inputs.items():
    spec=(required|optional)[name];expected=spec[0]
    if isinstance(value,list):
     actual=schemas[graph[value[0]]['class_type']]['output'][value[1]]
     assert expected==actual or expected=='*',(path,kind,name,expected,actual)
    elif isinstance(expected,list) and name not in ('unet_name','clip_name','vae_name','lora_name','image'):
     assert value in expected,(path,kind,name,value,expected)
  print('Schema OK:',path.name)
finally:
 p.terminate()
 try:p.wait(timeout=15)
 except subprocess.TimeoutExpired:p.kill();p.wait()
