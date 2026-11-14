import json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]  # repository root, whatever the checkout is named
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
# Schema fragments: required socket names/types and output types. Widget inputs stay
# in API inputs and widgets_values; linked primitives are converted widgets in UI.
S={
 'ACDEVVideoControls':({},['INT','INT','INT','FLOAT','STRING','STRING']),
 'ACDEVRandomSeed':({},['INT']),
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
   'ACDEVSaveVideo':['filename_prefix'],'ACDEVRandomSeed':['seed']}
  defaults={'width':832,'height':480,'length':81,'fps':16.0,'text':'','prompt':'','seed':0,'noise_seed':0,'bit_depth':'auto','color_space':'sRGB','chroma_subsampling':'auto','codec':'none'}
  values=[]
  for key in widget_orders.get(kind,[]):
   val=inputs.get(key,defaults.get(key))
   if isinstance(val,list):val=defaults[key]
   values.append(val)
   if kind in ('RandomNoise','KSamplerAdvanced') and key=='noise_seed':values.append('fixed')
   if kind=='ACDEVRandomSeed':values.append('randomize')
   if kind=='LoadImage':values.append('image')
  node['widgets_values']=values
  node['properties']['widget_order']=widget_orders.get(kind,[])
  self.nodes.append(node);self.api[str(id)]={'class_type':kind,'inputs':{k:([str(v[0]),v[1]] if isinstance(v,list) else v) for k,v in inputs.items()},'_meta':{'title':title or kind}}
  return [id,0]
 def write(self,v,name,title):
  dump(v/'workflows'/f'{name}.json',subgraph_ui(self,name,title))
  dump(v/'api'/f'{name}.json',self.api)

# UI layout: only the reference image, one "Generate video" node and the saver are
# visible. Everything else lives in a subgraph (same format as Comfy-Org's templates);
# the user-facing controls are subgraph inputs wired to the inner Video controls widgets.
OUTSIDE=('LoadImage','ACDEVRandomSeed','ACDEVSaveVideo')
PROMOTED=('prompt','negative_prompt','width','height','duration')
def subgraph_ui(g,name,title):
 import copy,uuid
 nodes={n['id']:copy.deepcopy(n) for n in g.nodes};flat=[list(l) for l in g.links]
 outside={i for i,n in nodes.items() if n['type'] in OUTSIDE};inner=[i for i in nodes if i not in outside]
 sid=max(nodes)+1;next_link=[len(flat)]
 def lid():next_link[0]+=1;return next_link[0]
 ns=uuid.UUID('6f1c3a52-7d0e-4b8e-9a51-acde5e0a1d01');sgid=str(uuid.uuid5(ns,name))
 sg_inputs=[];sg_outputs=[];inner_links=[];top_links=[]
 outer=dict(id=sid,type=sgid,title=title,pos=[420,0],size=[480,620],flags={},order=1,mode=0,inputs=[],outputs=[],properties={},widgets_values=[])
 def sg_input(name_,typ,label=None):
  sg_inputs.append(dict(id=str(uuid.uuid5(ns,name+'/in/'+name_)),name=name_,type=typ,linkIds=[],pos=[0,0],**({'label':label} if label else {})))
  return len(sg_inputs)-1
 # Reference image: one subgraph input fanning out to every inner consumer.
 for l in flat:
  if l[1] in outside and l[3] not in outside:
   iname={'IMAGE':'reference_image','INT':'seed'}[l[5]]
   slot_=next((i for i,x in enumerate(sg_inputs) if x['name']==iname),None)
   if slot_ is None:
    slot_=sg_input(iname,l[5]);t=lid();top_links.append([t,l[1],l[2],sid,len(outer['inputs']),l[5]])
    # The frontend gives every subgraph input that feeds an inner *widget* (e.g. the seed
    # into noise_seed) its own widget slot on the outer node, even when linked. Each such
    # slot needs a value, or every later widget value shifts by one.
    feeds_widget='widget' in nodes[l[3]]['inputs'][l[4]]
    outer['inputs'].append(dict(name=iname,type=l[5],link=t,**({'widget':{'name':iname}} if feeds_widget else {})))
    if feeds_widget:outer['widgets_values'].append(0)
   sg_inputs[slot_]['linkIds'].append(l[0]);inner_links.append(dict(id=l[0],origin_id=-10,origin_slot=slot_,target_id=l[3],target_slot=l[4],type=l[5]))
 # User controls: promote the Video controls widgets onto the subgraph node.
 ctrl=next(n for n in nodes.values() if n['type']=='ACDEVVideoControls');order=ctrl['properties']['widget_order']
 types={'prompt':'STRING','negative_prompt':'STRING','width':'INT','height':'INT','duration':'FLOAT'}
 for w in PROMOTED:
  slot_=sg_input(w,types[w]);l=lid();sg_inputs[slot_]['linkIds'].append(l)
  ctrl['inputs'].append(dict(name=w,type=types[w],widget={'name':w},link=l))
  inner_links.append(dict(id=l,origin_id=-10,origin_slot=slot_,target_id=ctrl['id'],target_slot=len(ctrl['inputs'])-1,type=types[w]))
  outer['inputs'].append(dict(name=w,type=types[w],widget={'name':w},link=None));outer['widgets_values'].append(ctrl['widgets_values'][order.index(w)])
 # Outputs that leave the subgraph (video and the actual seed for the saver).
 for l in flat:
  if l[1] not in outside and l[3] in outside:
   oname={'VIDEO':'video'}[l[5]]
   slot_=next((i for i,x in enumerate(sg_outputs) if x['name']==oname),None)
   if slot_ is None:
    sg_outputs.append(dict(id=str(uuid.uuid5(ns,name+'/out/'+oname)),name=oname,type=l[5],linkIds=[],pos=[0,0]));slot_=len(sg_outputs)-1
    outer['outputs'].append(dict(name=oname,type=l[5],links=[]))
   sg_outputs[slot_]['linkIds'].append(l[0]);inner_links.append(dict(id=l[0],origin_id=l[1],origin_slot=l[2],target_id=-20,target_slot=slot_,type=l[5]))
   t=lid();outer['outputs'][slot_]['links'].append(t);top_links.append([t,sid,slot_,l[3],l[4],l[5]])
   for i in nodes[l[3]]['inputs']:
    if i['link']==l[0]:i['link']=t
 for l in flat:
  if l[1] in outside and l[3] in outside:top_links.append(list(l))  # e.g. Seed -> Save, stays visible
 for n in nodes.values():  # rebuild outside nodes' output link lists from the top-level wiring
  if n['id'] in outside:
   for o in n['outputs']:o['links']=[t[0] for t in top_links if t[1]==n['id'] and n['outputs'][t[2]] is o]
 for l in flat:
  if l[1] not in outside and l[3] not in outside:inner_links.append(dict(id=l[0],origin_id=l[1],origin_slot=l[2],target_id=l[3],target_slot=l[4],type=l[5]))
 # Left-to-right layout by dependency depth.
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
 nodes_out=[n for i,n in nodes.items() if i in outside]
 place={'LoadImage':([0,0],[360,420]),'ACDEVRandomSeed':([0,460],[360,110]),'ACDEVSaveVideo':([960,0],[480,520])}
 for n in nodes_out:n['pos'],n['size']=place[n['type']]
 definition=dict(id=sgid,version=1,state=dict(lastGroupId=0,lastNodeId=sid,lastLinkId=next_link[0],lastRerouteId=0),revision=0,config={},name=title,
  inputNode=dict(id=-10,bounding=[0,0,180,40+30*len(sg_inputs)]),outputNode=dict(id=-20,bounding=[right,0,140,40+30*len(sg_outputs)]),
  inputs=sg_inputs,outputs=sg_outputs,widgets=[],nodes=[nodes[i] for i in inner],groups=[],links=sorted(inner_links,key=lambda l:l['id']),extra={})
 return dict(id=str(uuid.uuid5(ns,name+'/workflow')),revision=0,last_node_id=sid,last_link_id=next_link[0],nodes=nodes_out+[outer],links=sorted(top_links),groups=[],
  definitions=dict(subgraphs=[definition]),config={},extra=dict(ds=dict(scale=0.8,offset=[40,80])),version=0.4)
def slot(ref,n):return [ref[0],n]
for project,version,modes in [('WAN-SETUP', '2.2', ['standard', 'turbo', 'remix', 't2v', 't2v-turbo'])]:
 root=ROOT;v=root/'versions'/version;profile=json.loads((v/'profile.json').read_text());catalog=[]
 for mode in modes:
  for task in (['i2v', 't2v'] if project=='EROSH3-SETUP' else (['t2v'] if mode.startswith('t2v') else ['i2v'])):
   wan=project=='WAN-SETUP';g=Graph();active=[m for m in profile['models'] if mode in m['modes'] or 'all' in m['modes']]
   def file(d,fragment=''):return next(pathlib.Path(m['file']).name for m in active if m['directory']==d and fragment in m['file'])
   ctrl=g.add('ACDEVVideoControls',dict(family='wan' if wan else 'h3',width=832 if wan else 1024,height=480 if wan else 576,duration=5.0,prompt='A cinematic shot. The subject moves naturally as the camera slowly tracks forward.',negative_prompt='low quality, blurry, overexposed, static frame, frozen motion, temporal flicker, jitter, distorted anatomy, extra limbs, malformed hands, duplicated subjects, text, subtitles, watermark, compression artifacts'))
   image=g.add('LoadImage',dict(image='reference.png'),'Upload reference image') if task=='i2v' else None
   # Separate node so only sampling re-runs per job; prompt/image encodes stay cached.
   seed=g.add('ACDEVRandomSeed',dict(seed=0),'Seed (randomized every job)')
   clip=g.add('CLIPLoader',dict(clip_name=file('text_encoders'),type='wan' if wan else 'minimax',device='default'))
   vae=g.add('VAELoader',dict(vae_name=file('vae','wan_' if wan else 'video_vae')))
   # H3: Comfy-Org's I2V template samples every path guidance-free, so standard
   # matches it (CFG 1 skips the unconditional pass, about half the compute of CFG 6).
   h3_cfg=1.0
   if not wan and h3_cfg>1:
    # H3 keyframes and Qwen3-VL image tokens live in the conditioning, so the
    # CFG negative must carry the same reference image as the positive.
    neg=g.add('MiniMaxH3ImageToVideo',dict(clip=clip,vae=vae,prompt=slot(ctrl,5),width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),**({'first_frame':image} if image else {})),'Negative prompt (with reference image)')
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
   name=f'{version}_{mode}_{task}';g.write(v,name,f"Generate video: {'WAN 2.2' if wan else 'H3'} {mode} ({'image' if task=='i2v' else 'text'} to video)");catalog.append(dict(name=name,mode=mode,task=task,ui=f'workflows/{name}.json',api=f'api/{name}.json',experimental=mode in ('eros','remix')))
 dump(v/'workflow-catalog.json',catalog)
