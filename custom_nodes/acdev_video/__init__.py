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
            'duration': ('FLOAT', {'default':5.0,'min':0.2,'max':1_000_000.0,'step':0.1,'tooltip':'Seconds, no upper limit. Rounded up to the model frame grid (WAN 16 fps 4k+1, H3 24 fps 17k+5). H3 was trained on ~5-15 s and WAN on ~5 s; longer clips are untested and time/VRAM grow faster than length.'}),
            'exact_frame': ('BOOLEAN', {'default':False,'tooltip':'With a starting image: off = Width x Height sets the area and the image sets the shape (portraits stay portrait); on = use exactly Width x Height and centre-crop the image.'}),
            'prompt': ('STRING', {'default':'A cinematic shot. The subject moves naturally as the camera slowly tracks forward.','multiline':True}),
            'negative_prompt': ('STRING', {'default':NEGATIVE,'multiline':True}),
        },'optional':{'image':('IMAGE',)}}
    RETURN_TYPES=('INT','INT','INT','FLOAT','STRING','STRING')
    RETURN_NAMES=('width','height','num_frames','fps','prompt','negative_prompt')
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    # Deterministic on purpose: unchanged prompts/sizes keep text-encoder and
    # image-encode results cached between jobs. Randomness lives in RandomSeed.
    def run(self,family,width,height,duration,prompt,negative_prompt,exact_frame=False,image=None):
        if family not in ('wan','h3'):
            raise ValueError('Invalid video family')
        if width%32 or height%32 or not 64<=width<=4096 or not 64<=height<=4096:
            raise ValueError('Dimensions must be multiples of 32, between 64 and 4096')
        if image is not None and not exact_frame:
            width,height=fit_frame(width,height,image.shape[2],image.shape[1])
        fps=24.0 if family=='h3' else 16.0
        grid,offset=(17,5) if family=='h3' else (4,1)
        requested=math.ceil(round(duration*fps,6))
        frames=offset+max(0,math.ceil((requested-offset)/grid))*grid
        if frames<5:
            raise ValueError('Duration is too short: the shortest clip is 5 frames')
        print(f'[video] {width}x{height}, {frames} frames, {frames/fps:.3f}s at {fps:g}fps')
        return width,height,frames,fps,prompt,negative_prompt

MAX_SEED=0xffffffffffffffff  # full 64-bit range, same as ComfyUI's KSampler

def fit_frame(width,height,image_width,image_height):
    """Same rule as the LTX/Eros bundles: keep the requested area, take the image's shape, snap to 32."""
    area=width*height
    fit=lambda a,b:max(64,round(math.sqrt(area*a/b)/32)*32)
    return fit(image_width,image_height),fit(image_height,image_width)

class RandomSeed:
    """Visible seed. web/seed-controls.js (shared with the LTX and Eros bundles) writes a
    new random value *before* each queue, so the number shown is the one used; its seed
    mode switch offers randomize/fixed/increment/decrement. 0, which the shipped API
    graphs use, draws a fresh 64-bit seed on the server so API jobs randomize too."""
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'seed':('INT',{'default':0,'min':0,'max':MAX_SEED,
            'tooltip':'Randomized before every queue in the UI (see seed mode). 0 = pick a random seed on the server (API default).'})}}
    RETURN_TYPES=('INT',)
    RETURN_NAMES=('seed',)
    FUNCTION='run'
    CATEGORY='ACDEV/Video'
    @classmethod
    def IS_CHANGED(cls, seed=0, **kwargs):
        return float('nan') if seed==0 else seed  # 0 must re-run every job, including API calls.
    def run(self,seed=0):
        seed=seed or secrets.randbits(64) or 1
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
NODE_DISPLAY_NAME_MAPPINGS={'ACDEVVideoControls':'Video controls','ACDEVRandomSeed':'Seed (randomized every job)','ACDEVWanTurboSigmas':'WAN LightX2V four-step sigmas'}

class SaveVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'video':('VIDEO',),'filename_prefix':('STRING',{'default':'video/ACDEV'}),'seed':('INT',{'default':0,'min':0,'max':MAX_SEED,'forceInput':True})},'hidden':{'prompt':'PROMPT','extra_pnginfo':'EXTRA_PNGINFO'}}
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
