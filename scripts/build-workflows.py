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
 'ACDEVSaveVideo':({'video':'VIDEO'},[]),
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
   'ACDEVVideoControls':['family','width','height','length_mode','duration','num_frames','prompt','negative_prompt'],
   'UNETLoader':['unet_name','weight_dtype'],'CLIPLoader':['clip_name','type','device'],'VAELoader':['vae_name'],
   'LoadImage':['image'],'CLIPTextEncode':['text'],'LoraLoaderModelOnly':['lora_name','strength_model'],
   'ModelSamplingSD3':['shift'],'MiniMaxH3SigmaShift':['shift_video','shift_audio'],
   'WanImageToVideo':['width','height','length','batch_size'],
   'MiniMaxH3ImageToVideo':['prompt','width','height','length'],
   'KSamplerAdvanced':['add_noise','noise_seed','steps','cfg','sampler_name','scheduler','start_at_step','end_at_step','return_with_leftover_noise'],
   'CFGGuider':['cfg'],'RandomNoise':['noise_seed'],'KSamplerSelect':['sampler_name'],
   'BasicScheduler':['scheduler','steps','denoise'],'SplitSigmas':['step'],
   'CreateVideo':['fps','bit_depth','color_space','chroma_subsampling','codec'],
   'ACDEVSaveVideo':['filename_prefix','seed']}
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
 def write(self,v,name):
  dump(v/'workflows'/f'{name}.json',dict(last_node_id=len(self.nodes),last_link_id=len(self.links),nodes=self.nodes,links=self.links,groups=[],config={},extra={},version=0.4))
  dump(v/'api'/f'{name}.json',self.api)
def slot(ref,n):return [ref[0],n]
for project,version,modes in [('WAN-SETUP', '2.2', ['standard', 'turbo', 'remix'])]:
 root=ROOT;v=root/'versions'/version;profile=json.loads((v/'profile.json').read_text());catalog=[]
 for mode in modes:
  wan=project=='WAN-SETUP';g=Graph();active=[m for m in profile['models'] if mode in m['modes'] or 'all' in m['modes']]
  def file(d,fragment=''):return next(pathlib.Path(m['file']).name for m in active if m['directory']==d and fragment in m['file'])
  ctrl=g.add('ACDEVVideoControls',dict(family='wan' if wan else 'h3',width=832 if wan else 1344,height=480 if wan else 768,length_mode='duration',duration=5.0,num_frames=81 if wan else 124,prompt='A cinematic shot. The subject moves naturally as the camera slowly tracks forward.',negative_prompt='low quality, blurry, overexposed, static frame, frozen motion, temporal flicker, jitter, distorted anatomy, extra limbs, malformed hands, duplicated subjects, text, subtitles, watermark, compression artifacts'))
  image=g.add('LoadImage',dict(image='reference.png'),'Upload reference image')
  # Separate node so only sampling re-runs per job; prompt/image encodes stay cached.
  seed=g.add('ACDEVRandomSeed',{},'Random seed (new every job)')
  clip=g.add('CLIPLoader',dict(clip_name=file('text_encoders'),type='wan' if wan else 'minimax',device='default'))
  vae=g.add('VAELoader',dict(vae_name=file('vae','wan_' if wan else 'video_vae')))
  # H3: Comfy-Org's I2V template samples every path guidance-free, so standard
  # matches it (CFG 1 skips the unconditional pass, about half the compute of CFG 6).
  h3_cfg=1.0
  if not wan and h3_cfg>1:
   # H3 keyframes and Qwen3-VL image tokens live in the conditioning, so the
   # CFG negative must carry the same reference image as the positive.
   neg=g.add('MiniMaxH3ImageToVideo',dict(clip=clip,vae=vae,prompt=slot(ctrl,5),width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),first_frame=image),'Negative prompt (with reference image)')
  else:
   neg=g.add('CLIPTextEncode',dict(clip=clip,text=slot(ctrl,5)),'Negative prompt (inactive at CFG 1)' if not (wan and mode=='standard') else 'Negative prompt')
  if wan:
   pos=g.add('CLIPTextEncode',dict(clip=clip,text=slot(ctrl,4)))
   cond=g.add('WanImageToVideo',dict(positive=pos,negative=neg,vae=vae,width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),batch_size=1,start_image=image))
   models=[]
   for n in ['high','low']:
    m=g.add('UNETLoader',dict(unet_name=file('diffusion_models',n),weight_dtype='default'))
    if mode=='turbo':m=g.add('LoraLoaderModelOnly',dict(model=m,lora_name=file('loras',n),strength_model=1.0))
    models.append(g.add('ModelSamplingSD3',dict(model=m,shift=8.0 if mode in ('standard','remix') else 5.0)))
   if mode=='standard' or mode=='remix':
    # Remix already contains Lightning. Use the publisher example
    # 12-step / split-10 schedule as an experimental starting point.
    steps=20 if mode=='standard' else 12;split=10;cfg=3.5 if mode=='standard' else 1.0
    latent=slot(cond,2)
    for i,m in enumerate(models):
     latent=g.add('KSamplerAdvanced',dict(model=m,add_noise='enable' if i==0 else 'disable',noise_seed=seed,steps=steps,cfg=cfg,sampler_name='euler',scheduler='simple',positive=cond,negative=slot(cond,1),latent_image=latent,start_at_step=0 if i==0 else split,end_at_step=split if i==0 else steps,return_with_leftover_noise='enable' if i==0 else 'disable'))
   else:
    sig=g.add('ACDEVWanTurboSigmas',{});split=g.add('SplitSigmas',dict(sigmas=sig,step=2));sampler=g.add('KSamplerSelect',dict(sampler_name='euler'));noise=g.add('RandomNoise',dict(noise_seed=seed));latent=slot(cond,2)
    for i,m in enumerate(models):
     guide=g.add('CFGGuider',dict(model=m,positive=cond,negative=slot(cond,1),cfg=1.0))
     if i:noise=g.add('DisableNoise',{})
     latent=g.add('SamplerCustomAdvanced',dict(noise=noise,guider=guide,sampler=sampler,sigmas=slot(split,i),latent_image=latent))
  else:
   cond=g.add('MiniMaxH3ImageToVideo',dict(clip=clip,vae=vae,prompt=slot(ctrl,4),width=ctrl,height=slot(ctrl,1),length=slot(ctrl,2),first_frame=image))
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
  result=g.add('CreateVideo',cv);g.add('ACDEVSaveVideo',dict(video=result,filename_prefix=f'video/{version}/{mode}',seed=seed))
  name=f'{version}_{mode}_i2v';g.write(v,name);catalog.append(dict(name=name,mode=mode,ui=f'workflows/{name}.json',api=f'api/{name}.json',experimental=mode in ('eros','remix')))
 dump(v/'workflow-catalog.json',catalog)
