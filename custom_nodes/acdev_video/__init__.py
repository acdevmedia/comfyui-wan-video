"""Common controls used by UI and API workflows. No extra pip dependencies."""
import math
import secrets

NEGATIVE = 'low quality, blurry, overexposed, static frame, frozen motion, temporal flicker, jitter, distorted anatomy, extra limbs, malformed hands, duplicated subjects, text, subtitles, watermark, compression artifacts'
class VideoControls:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'family': (['wan','h3'],),
            'width': ('INT', {'default':832,'min':64,'max':4096,'step':32}),
            'height': ('INT', {'default':480,'min':64,'max':4096,'step':32}),
            'length_mode': (['duration','frames'],),
            'duration': ('FLOAT', {'default':5.0,'min':0.2,'max':15.0,'step':0.1}),
            'num_frames': ('INT', {'default':81,'min':5,'max':362,'step':1}),
            'prompt': ('STRING', {'default':'A cinematic shot. The subject moves naturally as the camera slowly tracks forward.','multiline':True}),
            'negative_prompt': ('STRING', {'default':NEGATIVE,'multiline':True}),
        }}
    RETURN_TYPES=('INT','INT','INT','FLOAT','STRING','STRING')
    RETURN_NAMES=('width','height','num_frames','fps','prompt','negative_prompt')
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    # Deterministic on purpose: unchanged prompts/sizes keep text-encoder and
    # image-encode results cached between jobs. Randomness lives in RandomSeed.
    def run(self,family,width,height,length_mode,duration,num_frames,prompt,negative_prompt):
        if family not in ('wan','h3') or length_mode not in ('duration','frames'):
            raise ValueError('Invalid video family or length mode')
        if width%32 or height%32 or not 64<=width<=4096 or not 64<=height<=4096:
            raise ValueError('Dimensions must be multiples of 32, between 64 and 4096')
        fps=24.0 if family=='h3' else 16.0
        grid,offset,maximum=(17,5,362) if family=='h3' else (4,1,241)
        requested=math.ceil(duration*fps) if length_mode=='duration' else num_frames
        frames=offset+max(0,math.ceil((requested-offset)/grid))*grid
        if not 5<=frames<=maximum:
            raise ValueError(f'Request is outside the supported frame range (max {maximum})')
        print(f'[video] {width}x{height}, {frames} frames, {frames/fps:.3f}s at {fps:g}fps')
        return width,height,frames,fps,prompt,negative_prompt

class RandomSeed:
    @classmethod
    def INPUT_TYPES(cls):return {'required':{}}
    RETURN_TYPES=('INT',)
    RETURN_NAMES=('random_seed',)
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float('nan')  # Re-execute for every queued job, including API calls.
    def run(self):
        seed=secrets.randbits(63)
        print(f'[video] seed={seed}')
        return (seed,)

class WanTurboSigmas:
    @classmethod
    def INPUT_TYPES(cls):return {'required':{}}
    RETURN_TYPES=('SIGMAS',)
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    def run(self):
        import torch
        # LightX2V publisher's ComfyUI schedule; split after step two.
        return (torch.tensor([1.0,0.9375001,0.8333333,0.625,0.0]),)
NODE_CLASS_MAPPINGS={'ACDEVVideoControls':VideoControls,'ACDEVRandomSeed':RandomSeed,'ACDEVWanTurboSigmas':WanTurboSigmas}
NODE_DISPLAY_NAME_MAPPINGS={'ACDEVVideoControls':'Video controls','ACDEVRandomSeed':'Random seed (new every job)','ACDEVWanTurboSigmas':'WAN LightX2V four-step sigmas'}

class SaveVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'video':('VIDEO',),'filename_prefix':('STRING',{'default':'video/ACDEV'}),'seed':('INT',{'default':0,'min':0,'max':2**63-1})},'hidden':{'prompt':'PROMPT','extra_pnginfo':'EXTRA_PNGINFO'}}
    RETURN_TYPES=()
    OUTPUT_NODE=True
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    def run(self,video,filename_prefix,seed,prompt=None,extra_pnginfo=None):
        import json
        import os
        import folder_paths
        from comfy_api.latest import Types
        width,height=video.get_dimensions()
        folder,filename,counter,subfolder,_=folder_paths.get_save_image_path(filename_prefix,folder_paths.get_output_directory(),width,height)
        name=f'{filename}_{counter:05}_.mp4'
        metadata={'seed':str(seed),'prompt':json.dumps(prompt or {}),'workflow':json.dumps((extra_pnginfo or {}).get('workflow',{}))}
        video.save_to(os.path.join(folder,name),format=Types.VideoContainer('mp4'),codec=Types.VideoCodec('h264'),metadata=metadata)
        return {'ui':{'gifs':[{'filename':name,'subfolder':subfolder,'type':'output','format':'video/mp4'}]}}
NODE_CLASS_MAPPINGS['ACDEVSaveVideo']=SaveVideo
NODE_DISPLAY_NAME_MAPPINGS['ACDEVSaveVideo']='Save MP4 (with actual random seed)'

WEB_DIRECTORY='./web'
