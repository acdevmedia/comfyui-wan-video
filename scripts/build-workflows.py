import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]  # repository root, whatever the checkout is named
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
# Schema fragments: required socket names/types and output types. Widget inputs stay
# in API inputs and widgets_values; linked primitives are converted widgets in UI.
S={
 'ACDEVVideoControls':({},['INT','INT','INT','FLOAT','STRING','STRING']),
 'ACDEVRandomSeed':({},['INT']),
 'PrimitiveStringMultiline':({},['STRING']),
 'ACDEVWanTurboSigmas':({},['SIGMAS']),
 'UNETLoader':({},['MODEL']), 'CLIPLoader':({},['CLIP']), 'VAELoader':({},['VAE']),
 'LoadImage':({},['IMAGE','MASK']),
 'CLIPTextEncode':({'clip':'CLIP'},['CONDITIONING']),
 'LoraLoaderModelOnly':({'model':'MODEL'},['MODEL']),
 'ModelSamplingSD3':({'model':'MODEL'},['MODEL']),
 'MiniMaxH3SigmaShift':({'model':'MODEL'},['MODEL']),
 'EmptyHunyuanLatentVideo':({},['LATENT']),
 'WanImageToVideo':({'positive':'CONDITIONING','negative':'CONDITIONING','vae':'VAE','start_image':'IMAGE'},['CONDITIONING','CONDITIONING','LATENT']),
 'MiniMaxH3ImageToVideo':({'clip':'CLIP','vae':'VAE','first_frame':'IMAGE'},['CONDITIONING','LATENT']),
 'KSamplerAdvanced':({'model':'MODEL','positive':'CONDITIONING','negative':'CONDITIONING','latent_image':'LATENT'},['LATENT']),
 'CFGGuider':({'model':'MODEL','positive':'CONDITIONING','negative':'CONDITIONING'},['GUIDER']),
 'RandomNoise':({},['NOISE']), 'DisableNoise':({},['NOISE']),
 'KSamplerSelect':({},['SAMPLER']),
 'BasicScheduler':({'model':'MODEL'},['SIGMAS']),
 'SplitSigmas':({'sigmas':'SIGMAS'},['SIGMAS','SIGMAS']),
 'SamplerCustomAdvanced':({'noise':'NOISE','guider':'GUIDER','sampler':'SAMPLER','sigmas':'SIGMAS','latent_image':'LATENT'},['LATENT','LATENT']),
 'VAEDecode':({'samples':'LATENT','vae':'VAE'},['IMAGE']),
 'VAEDecodeAudio':({'samples':'LATENT','vae':'VAE'},['AUDIO']),
 'CreateVideo':({'images':'IMAGE','audio':'AUDIO'},['VIDEO']),
 'ACDEVSaveVideo':({'video':'VIDEO','seed':'INT'},[]),
}
class Graph:
 def __init__(self):self.api={};self.nodes=[];self.links=[]
 def add(self,kind,inputs,title=None):
  id=len(self.nodes)+1; sockets,outs=S[kind]; links=[];widgets=[]
  node=dict(id=id,type=kind,pos=[(id-1)%4*440,(id-1)//4*780],size=[410,700 if kind=='ACDEVVideoControls' else 340],flags={},order=id-1,mode=0,inputs=[],outputs=[dict(name=t,type=t,links=[]) for t in outs],properties={'Node name for S&R':kind},widgets_values=widgets)
  if title:node['title']=title
  for key,val in inputs.items():
   if isinstance(val,list):
    source=self.nodes[val[0]-1];typ=source['outputs'][val[1]]['type'];lid=len(self.links)+1
    node['inputs'].append(dict(name=key,type=typ,link=lid,**({'widget':{'name':key}} if key not in sockets else {})))
    source['outputs'][val[1]]['links'].append(lid);self.links.append([lid,val[0],val[1],id,len(node['inputs'])-1,typ])
   else:
    widgets.append(val)
    if kind=='LoadImage' and key=='image':widgets.append('image')
    if kind in ('RandomNoise','KSamplerAdvanced') and key in ('noise_seed','seed'):widgets.append('fixed')
  widget_orders={
   'ACDEVVideoControls':['family','width','height','duration','prompt','negative_prompt'],
   'UNETLoader':['unet_name','weight_dtype'],'CLIPLoader':['clip_name','type','device'],'VAELoader':['vae_name'],
   'LoadImage':['image'],'CLIPTextEncode':['text'],'LoraLoaderModelOnly':['lora_name','strength_model'],
   'ModelSamplingSD3':['shift'],'MiniMaxH3SigmaShift':['shift_video','shift_audio'],
   'EmptyHunyuanLatentVideo':['width','height','length','batch_size'],
   'WanImageToVideo':['width','height','length','batch_size'],
   'MiniMaxH3ImageToVideo':['prompt','width','height','length'],
   'KSamplerAdvanced':['add_noise','noise_seed','steps','cfg','sampler_name','scheduler','start_at_step','end_at_step','return_with_leftover_noise'],
   'CFGGuider':['cfg'],'RandomNoise':['noise_seed'],'KSamplerSelect':['sampler_name'],
   'BasicScheduler':['scheduler','steps','denoise'],'SplitSigmas':['step'],
   'CreateVideo':['fps','bit_depth','color_space','chroma_subsampling','codec'],
   'ACDEVSaveVideo':['filename_prefix'],'ACDEVRandomSeed':['seed'],'PrimitiveStringMultiline':['value']}
  defaults={'width':832,'height':480,'length':81,'fps':16.0,'text':'','prompt':'','seed':0,'noise_seed':0,'bit_depth':'auto','color_space':'sRGB','chroma_subsampling':'auto','codec':'none'}
  values=[]
  for key in widget_orders.get(kind,[]):
   val=inputs.get(key,defaults.get(key))
   if isinstance(val,list):val=defaults[key]
   values.append(val)
   if kind in ('RandomNoise','KSamplerAdvanced') and key=='noise_seed':values.append('fixed')
   if kind=='LoadImage':values.append('image')
  node['widgets_values']=values
  node['properties']['widget_order']=widget_orders.get(kind,[])
  self.nodes.append(node);self.api[str(id)]={'class_type':kind,'inputs':{k:([str(v[0]),v[1]] if isinstance(v,list) else v) for k,v in inputs.items()},'_meta':{'title':title or kind}}
  return [id,0]
 def write(self,v,name,ui_file,subgraph_name):
  dump(v/'workflows'/ui_file,subgraph_ui(self,name,subgraph_name))
  dump(v/'api'/f'{name}.json',self.api)

# UI layout (same panels, names and colours as the Eros/LTX bundles):
#   01 · Describe your shot  -> prompt text box
#   Starting image           -> image-to-video only
#   02 · Shot settings       -> subgraph node holding the whole pipeline; shows width,
#                               height, duration, seed, steps, CFG and negative prompt
#   03 · Your video          -> MP4 saver (records the seed actually used)
OUTSIDE=('PrimitiveStringMultiline','LoadImage','ACDEVSaveVideo')
# (inner node, widget, label) in panel order; skipped when the node is absent (e.g. WAN).
PROMOTE=[('ACDEVVideoControls','width','Width'),('ACDEVVideoControls','height','Height'),
 ('ACDEVVideoControls','duration','Duration (seconds)'),('ACDEVRandomSeed','seed','Seed'),
 ('BasicScheduler','steps','Steps'),('CFGGuider','cfg','CFG'),
 ('ACDEVVideoControls','negative_prompt','Negative prompt (used when CFG > 1)')]
WIDGET_TYPES={'width':'INT','height':'INT','duration':'FLOAT','seed':'INT','steps':'INT','cfg':'FLOAT','negative_prompt':'STRING'}
LINKED={'STRING':('prompt','Prompt — describe the shot'),'IMAGE':('reference_image','Starting image — upload your own')}
OUT_NAMES={'VIDEO':'video','INT':'seed'}
PANELS={'PrimitiveStringMultiline':('01 · Describe your shot','#28524d','#172f2c',[0,100],[480,220]),
 'LoadImage':('Starting image','#334c63','#1b2b3b',[0,380],[480,680]),
 'outer':('02 · Shot settings','#484661','#29283d',[540,100],[520,960]),
 'ACDEVSaveVideo':('03 · Your video','#3c5540','#223025',[1120,100],[580,960])}
def subgraph_ui(g,name,subgraph_name):
 import copy,uuid
 nodes={n['id']:copy.deepcopy(n) for n in g.nodes};flat=[list(l) for l in g.links]
 outside={i for i,n in nodes.items() if n['type'] in OUTSIDE};inner=[i for i in nodes if i not in outside]
 sid=max(nodes)+1;next_link=[len(flat)]
 def lid():next_link[0]+=1;return next_link[0]
 ns=uuid.UUID('6f1c3a52-7d0e-4b8e-9a51-acde5e0a1d01');sgid=str(uuid.uuid5(ns,name))
 title,color,bgcolor,pos,size=PANELS['outer']
 outer=dict(id=sid,type=sgid,title=title,color=color,bgcolor=bgcolor,pos=pos,size=size,flags={},order=1,mode=0,inputs=[],outputs=[],properties={},widgets_values=[])
 sg_inputs=[];sg_outputs=[];inner_links=[];top_links=[]
 def add_input(iname,typ,label,feeds_widget,value,link=None):
  sg_inputs.append(dict(id=str(uuid.uuid5(ns,name+'/in/'+iname)),name=iname,type=typ,linkIds=[],pos=[0,0],label=label))
  # The frontend gives every subgraph input that feeds an inner *widget* a widget slot
  # on the outer node, linked or not. Each slot needs a value, or later values shift.
  outer['inputs'].append(dict(name=iname,label=label,type=typ,link=link,**({'widget':{'name':iname}} if feeds_widget else {})))
  if feeds_widget:outer['widgets_values'].append(value)
  return len(sg_inputs)-1
 for kind,w,label in PROMOTE:
  owners=[nodes[i] for i in inner if nodes[i]['type']==kind]
  if not owners:continue
  (n,)=owners;typ=WIDGET_TYPES[w];value=n['widgets_values'][n['properties']['widget_order'].index(w)]
  slot_=add_input(w,typ,label,True,value);l=lid();sg_inputs[slot_]['linkIds'].append(l)
  n['inputs'].append(dict(name=w,type=typ,widget={'name':w},link=l))
  inner_links.append(dict(id=l,origin_id=-10,origin_slot=slot_,target_id=n['id'],target_slot=len(n['inputs'])-1,type=typ))
 for l in flat:  # prompt text and starting image flow in from their own panels
  if l[1] in outside and l[3] not in outside:
   iname,label=LINKED[l[5]]
   slot_=next((i for i,x in enumerate(sg_inputs) if x['name']==iname),None)
   if slot_ is None:
    t=lid();feeds='widget' in nodes[l[3]]['inputs'][l[4]]
    slot_=add_input(iname,l[5],label,feeds,nodes[l[1]]['widgets_values'][0] if feeds else None,t)
    top_links.append([t,l[1],l[2],sid,len(outer['inputs'])-1,l[5]])
   sg_inputs[slot_]['linkIds'].append(l[0]);inner_links.append(dict(id=l[0],origin_id=-10,origin_slot=slot_,target_id=l[3],target_slot=l[4],type=l[5]))
 for l in flat:  # video and the seed actually used leave for the saver
  if l[1] not in outside and l[3] in outside:
   oname=OUT_NAMES[l[5]]
   slot_=next((i for i,x in enumerate(sg_outputs) if x['name']==oname),None)
   if slot_ is None:
    sg_outputs.append(dict(id=str(uuid.uuid5(ns,name+'/out/'+oname)),name=oname,type=l[5],linkIds=[],pos=[0,0]));slot_=len(sg_outputs)-1
    outer['outputs'].append(dict(name=oname,type=l[5],links=[]))
   sg_outputs[slot_]['linkIds'].append(l[0]);inner_links.append(dict(id=l[0],origin_id=l[1],origin_slot=l[2],target_id=-20,target_slot=slot_,type=l[5]))
   t=lid();outer['outputs'][slot_]['links'].append(t);top_links.append([t,sid,slot_,l[3],l[4],l[5]])
   for i in nodes[l[3]]['inputs']:
    if i['link']==l[0]:i['link']=t
 for l in flat:
  if l[1] in outside and l[3] in outside:top_links.append(list(l))
  elif l[1] not in outside and l[3] not in outside:inner_links.append(dict(id=l[0],origin_id=l[1],origin_slot=l[2],target_id=l[3],target_slot=l[4],type=l[5]))
 for n in nodes.values():
  if n['id'] in outside:
   for o in n['outputs']:o['links']=[t[0] for t in top_links if t[1]==n['id'] and n['outputs'][t[2]] is o]
 depth={}
 def d(i):
  if i not in depth:depth[i]=1+max([d(l[1]) for l in flat if l[3]==i and l[1] in inner] or [0])
  return depth[i]
 cols={}
 for i in sorted(inner,key=lambda i:(d(i),i)):
  n=nodes[i];col=cols.setdefault(d(i),[]);y=sum(nodes[j]['size'][1]+40 for j in col)
  n['size']=[400,540] if n['type']=='ACDEVVideoControls' else [340,90+28*(len(n['inputs'])+len(n['widgets_values']))]
  n['pos']=[300+(d(i)-1)*420,y];col.append(i)
 right=300+max(cols)*420
 for k,x in enumerate(sg_inputs):x['pos']=[200,40+30*k]
 for k,x in enumerate(sg_outputs):x['pos']=[right+20,40+30*k]
 nodes_out=[nodes[i] for i in sorted(outside,key=lambda i:list(PANELS).index(nodes[i]['type']))]
 for n in nodes_out:
  n['title'],n['color'],n['bgcolor'],n['pos'],n['size']=PANELS[n['type']]
 definition=dict(id=sgid,version=1,state=dict(lastGroupId=0,lastNodeId=sid,lastLinkId=next_link[0],lastRerouteId=0),revision=0,config={},name=subgraph_name,
  inputNode=dict(id=-10,bounding=[0,0,180,40+30*len(sg_inputs)]),outputNode=dict(id=-20,bounding=[right,0,140,40+30*len(sg_outputs)]),
  inputs=sg_inputs,outputs=sg_outputs,widgets=[],nodes=[nodes[i] for i in inner],groups=[],links=sorted(inner_links,key=lambda l:l['id']),extra={})
 return dict(id=str(uuid.uuid5(ns,name+'/workflow')),revision=0,last_node_id=sid,last_link_id=next_link[0],nodes=[n for n in nodes_out if n['type']!='ACDEVSaveVideo']+[outer]+[n for n in nodes_out if n['type']=='ACDEVSaveVideo'],links=sorted(top_links),groups=[],
  definitions=dict(subgraphs=[definition]),config={},extra=dict(ds=dict(scale=0.75,offset=[40,20])),version=0.4)
def slot(ref,n):return [ref[0],n]
LABELS={'eros':'Eros','turbo8':'Turbo 8-step','turbo4':'Turbo 4-step','standard':'Standard 20-step',
 'turbo':'Turbo','t2v-turbo':'Turbo','t2v':'Standard 20-step','remix':'Remix'}
TASKS={'i2v':'Image to Video','t2v':'Text to Video'}
PROMPT='A cinematic shot. The subject moves naturally as the camera slowly tracks forward.'
for project,version,modes in [('WAN-SETUP', '2.2', ['turbo', 't2v-turbo', 'standard', 't2v', 'remix'])]:
 root=ROOT;v=root/'versions'/version;profile=json.loads((v/'profile.json').read_text());catalog=[]
 for sub in ('workflows','api'):
  for old in (v/sub).glob('*.json'):old.unlink()  # renamed files must not linger
 for mode in modes:
  for task in (['i2v', 't2v'] if project=='EROSH3-SETUP' else (['t2v'] if mode.startswith('t2v') else ['i2v'])):
   wan=project=='WAN-SETUP';g=Graph();active=[m for m in profile['models'] if mode in m['modes'] or 'all' in m['modes']]
   def file(d,fragment=''):return next(pathlib.Path(m['file']).name for m in active if m['directory']==d and fragment in m['file'])
   prm=g.add('PrimitiveStringMultiline',dict(value=PROMPT),'01 · Describe your shot')
   ctrl=g.add('ACDEVVideoControls',dict(family='wan' if wan else 'h3',width=832 if wan else 1024,height=480 if wan else 576,duration=5.0,prompt=prm,negative_prompt='low quality, blurry, overexposed, static frame, frozen motion, temporal flicker, jitter, distorted anatomy, extra limbs, malformed hands, duplicated subjects, text, subtitles, watermark, compression artifacts'))
   image=g.add('LoadImage',dict(image='reference.png'),'Starting image') if task=='i2v' else None
   # Separate node so only sampling re-runs per job; prompt/image encodes stay cached.
   seed=g.add('ACDEVRandomSeed',dict(seed=0),'Seed')
   clip=g.add('CLIPLoader',dict(clip_name=file('text_encoders'),type='wan' if wan else 'minimax',device='default'))
   vae=g.add('VAELoader',dict(vae_name=file('vae','wan_' if wan else 'video_vae')))
   # H3: Comfy-Org's I2V template samples every path guidance-free, so standard
   # matches it (CFG 1 skips the unconditional pass, about half the compute of CFG 6).
   h3_cfg=1.0  # CFG is a Shot settings control; >1 activates the negative prompt
   if not wan:
    # H3 keyframes and Qwen3-VL image tokens live in the conditioning, so the
    # CFG negative must carry the same reference image as the positive.
    neg=g.add('MiniMaxH3ImageToVideo',dict(clip=clip,vae=vae,prompt=slot(ctrl,5),width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),**({'first_frame':image} if image else {})),'Negative prompt')
   else:
    neg=g.add('CLIPTextEncode',dict(clip=clip,text=slot(ctrl,5)),'Negative prompt (inactive at CFG 1)' if not (wan and mode in ('standard','t2v','turbo','t2v-turbo')) else 'Negative prompt')
   if wan:
    pos=g.add('CLIPTextEncode',dict(clip=clip,text=slot(ctrl,4)))
    if task=='t2v':
     cond=g.add('EmptyHunyuanLatentVideo',dict(width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),batch_size=1));positive,negative,initial=pos,neg,cond
    else:
     cond=g.add('WanImageToVideo',dict(positive=pos,negative=neg,vae=vae,width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),batch_size=1,start_image=image));positive,negative,initial=cond,slot(cond,1),slot(cond,2)
    if mode in ('turbo','t2v-turbo'):
     # Three-stage LightX2V schedule (8 steps, shift 8, Euler/simple). Stage 1 runs the
     # high-noise expert WITHOUT the speed LoRA at CFG 3.5 for two steps, so the
     # coarse motion is set by the base model with real guidance; stages 2-3 finish
     # with the matched high/low LoRAs at CFG 1. GPU A/B on the drawing-room I2V test:
     # LoRA-only turbo moved ~60% as much as standard (the "slow motion" look),
     # this schedule ~94%, at 47 s vs 25 s turbo / 176 s standard (RTX PRO 6000).
     high=g.add('UNETLoader',dict(unet_name=file('diffusion_models','high'),weight_dtype='default'))
     low=g.add('UNETLoader',dict(unet_name=file('diffusion_models','low'),weight_dtype='default'))
     high_base=g.add('ModelSamplingSD3',dict(model=high,shift=8.0))
     high_fast=g.add('ModelSamplingSD3',dict(model=g.add('LoraLoaderModelOnly',dict(model=high,lora_name=file('loras','high'),strength_model=1.0)),shift=8.0))
     low_fast=g.add('ModelSamplingSD3',dict(model=g.add('LoraLoaderModelOnly',dict(model=low,lora_name=file('loras','low'),strength_model=1.0)),shift=8.0))
     stages=[(high_base,0,2,3.5),(high_fast,2,4,1.0),(low_fast,4,8,1.0)];latent=initial
     for i,(m,start,end,cfg) in enumerate(stages):
      last=i==len(stages)-1
      latent=g.add('KSamplerAdvanced',dict(model=m,add_noise='enable' if i==0 else 'disable',noise_seed=seed,steps=8,cfg=cfg,sampler_name='euler',scheduler='simple',positive=positive,negative=negative,latent_image=latent,start_at_step=start,end_at_step=end,return_with_leftover_noise='disable' if last else 'enable'))
    else:
     models=[]
     for n in ['high','low']:
      m=g.add('UNETLoader',dict(unet_name=file('diffusion_models',n),weight_dtype='default'))
      models.append(g.add('ModelSamplingSD3',dict(model=m,shift=8.0)))
     # Remix already contains Lightning. Use the publisher example
     # 12-step / split-10 schedule as an experimental starting point.
     steps=20 if mode in ('standard','t2v') else 12;split=10;cfg=3.5 if mode in ('standard','t2v') else 1.0
     latent=initial
     for i,m in enumerate(models):
      latent=g.add('KSamplerAdvanced',dict(model=m,add_noise='enable' if i==0 else 'disable',noise_seed=seed,steps=steps,cfg=cfg,sampler_name='euler',scheduler='simple',positive=positive,negative=negative,latent_image=latent,start_at_step=0 if i==0 else split,end_at_step=split if i==0 else steps,return_with_leftover_noise='enable' if i==0 else 'disable'))
   else:
    cond=g.add('MiniMaxH3ImageToVideo',dict(clip=clip,vae=vae,prompt=slot(ctrl,4),width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),**({'first_frame':image} if image else {})))
    m=g.add('UNETLoader',dict(unet_name=file('diffusion_models'),weight_dtype='default'))
    if mode in ('turbo4','turbo8'):m=g.add('LoraLoaderModelOnly',dict(model=m,lora_name=file('loras'),strength_model=1.0))
    m=g.add('MiniMaxH3SigmaShift',dict(model=m,shift_video=12.0,shift_audio=3.0))
    guide=g.add('CFGGuider',dict(model=m,positive=cond,negative=neg,cfg=h3_cfg))
    sampler=g.add('KSamplerSelect',dict(sampler_name='euler' if mode=='eros' else 'res_multistep'))
    sig=g.add('BasicScheduler',dict(model=m,scheduler='simple',steps=20 if mode=='standard' else (4 if mode=='turbo4' else 8),denoise=1.0));noise=g.add('RandomNoise',dict(noise_seed=seed))
    latent=g.add('SamplerCustomAdvanced',dict(noise=noise,guider=guide,sampler=sampler,sigmas=sig,latent_image=slot(cond,1)))
   video=g.add('VAEDecode',dict(samples=latent,vae=vae))
   cv=dict(images=video,fps=slot(ctrl,3))
   if not wan:
    av=g.add('VAELoader',dict(vae_name=file('vae','audio')));audio=g.add('VAEDecodeAudio',dict(samples=latent,vae=av));cv['audio']=audio
   result=g.add('CreateVideo',cv);g.add('ACDEVSaveVideo',dict(video=result,filename_prefix=f'video/{version}/{mode}/{task}',seed=seed))
   name=f'{version}_{mode}_{task}';number=len(catalog)+1;title=f'{LABELS[mode]} - {TASKS[task]}'
   ui_file=f'{number:02d} {title}.json';g.write(v,name,ui_file,f'Shot settings — {TASKS[task]} — {LABELS[mode]}')
   catalog.append(dict(name=name,title=f'{number:02d} {title}',mode=mode,task=task,ui=f'workflows/{ui_file}',api=f'api/{name}.json',experimental=mode in ('eros','remix')))
 dump(v/'workflow-catalog.json',catalog)
