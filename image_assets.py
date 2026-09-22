import json
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

IMAGE_EXTENSIONS={'.png','.jpg','.jpeg','.webp','.gif'}
PROCESSING_PROFILES=['Raw','Clean','Detailed','Pixel-Dither']
_LIBRARIES=[]

class ImageSettings:
    def __init__(self,mode='optimize',crop_x=0.5,crop_y=0.5,zoom=1.0,contrast=1.25,saturation=1.35,sharpen=True,gamma=1.0,dither=False,processing_profile='Clean'):
        self.mode=mode;self.crop_x=crop_x;self.crop_y=crop_y;self.zoom=zoom
        self.contrast=contrast;self.saturation=saturation;self.sharpen=sharpen;self.gamma=gamma;self.dither=dither
        self.processing_profile=processing_profile if processing_profile in PROCESSING_PROFILES else 'Clean'
    def reset(self):
        self.mode='optimize';self.crop_x=0.5;self.crop_y=0.5;self.zoom=1.0
        self.contrast=1.25;self.saturation=1.35;self.sharpen=True;self.gamma=1.0;self.dither=False;self.processing_profile='Clean'
    def reset_processing(self):
        self.contrast=1.25;self.saturation=1.35;self.sharpen=True;self.gamma=1.0;self.dither=False;self.processing_profile='Clean'
    def to_dict(self):
        return {'mode':self.mode,'crop_x':self.crop_x,'crop_y':self.crop_y,'zoom':self.zoom,'contrast':self.contrast,'saturation':self.saturation,'sharpen':self.sharpen,'gamma':self.gamma,'dither':self.dither,'processing_profile':self.processing_profile}
    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict):return cls()
        s=cls();s.mode=data.get('mode',s.mode)
        for key in ('crop_x','crop_y','zoom','contrast','saturation','gamma'):
            try:setattr(s,key,float(data.get(key,getattr(s,key))))
            except (TypeError,ValueError):pass
        s.sharpen=bool(data.get('sharpen',s.sharpen));s.dither=bool(data.get('dither',s.dither))
        p=str(data.get('processing_profile',s.processing_profile))
        if p in PROCESSING_PROFILES:s.processing_profile=p
        s.clamp();return s
    def clamp(self):
        self.crop_x=max(0.0,min(1.0,self.crop_x));self.crop_y=max(0.0,min(1.0,self.crop_y));self.zoom=max(0.55,min(5.0,self.zoom))
        self.contrast=max(0.25,min(3.0,self.contrast));self.saturation=max(0.0,min(3.0,self.saturation));self.gamma=max(0.25,min(3.0,self.gamma))
        if self.processing_profile not in PROCESSING_PROFILES:self.processing_profile='Clean'

class ImageAsset:
    def __init__(self,path,width=64,height=32,settings=None):
        self.path=Path(path);self.width=width;self.height=height;self.frames=[];self.durations=[]
        self.settings=settings if settings is not None else ImageSettings();self.cache={};self.load()
    def load(self):
        self.frames=[];self.durations=[]
        with Image.open(self.path) as image:
            for frame_number in range(getattr(image,'n_frames',1)):
                image.seek(frame_number);self.frames.append(image.convert('RGB').copy())
                duration=image.info.get('duration',100)
                if not duration or duration<10:duration=100
                self.durations.append(duration/1000.0)
    def clear_cache(self):self.cache.clear()
    def crop_image(self,image,settings):
        sw,sh=image.size;cover=max(self.width/sw,self.height/sh);scale=cover*settings.zoom
        nw=max(1,int(round(sw*scale)));nh=max(1,int(round(sh*scale)));resized=image.resize((nw,nh),Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',(self.width,self.height),(0,0,0))
        if nw>=self.width:max_x=nw-self.width;src_x=int(round(max_x*settings.crop_x));src_w=self.width;dst_x=0
        else:src_x=0;src_w=nw;dst_x=int(round((self.width-nw)*settings.crop_x))
        if nh>=self.height:max_y=nh-self.height;src_y=int(round(max_y*settings.crop_y));src_h=self.height;dst_y=0
        else:src_y=0;src_h=nh;dst_y=int(round((self.height-nh)*settings.crop_y))
        cropped=resized.crop((src_x,src_y,src_x+src_w,src_y+src_h));canvas.paste(cropped,(dst_x,dst_y));return canvas
    def fit_image(self,image):
        image=image.copy();image.thumbnail((self.width,self.height),Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',(self.width,self.height),(0,0,0));canvas.paste(image,((self.width-image.width)//2,(self.height-image.height)//2));return canvas
    def pixel_image(self,image,settings):
        image=self.crop_image(image,settings);small=(max(16,self.width//2),max(8,self.height//2))
        return image.resize(small,Image.Resampling.BILINEAR).resize((self.width,self.height),Image.Resampling.NEAREST)
    def apply_gamma(self,image,gamma):
        if abs(gamma-1.0)<0.001:return image
        table=[max(0,min(255,int((value/255.0)**gamma*255+0.5))) for value in range(256)]
        return image.point(table*3)
    def apply_dither(self,image,colors=64):
        return image.convert('RGB').quantize(colors=colors,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.FLOYDSTEINBERG).convert('RGB')
    def quantize_clean(self,image,colors=56):
        return image.convert('RGB').quantize(colors=colors,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).convert('RGB')
    def _base_frame(self,image,settings):
        if settings.mode=='pixel':return self.pixel_image(image,settings)
        if settings.mode=='fit':return self.fit_image(image)
        return self.crop_image(image,settings)
    def _fine_tune(self,image,settings,sharpen_percent=120,sharpen_radius=1.0):
        image=ImageEnhance.Contrast(image).enhance(settings.contrast);image=ImageEnhance.Color(image).enhance(settings.saturation);image=self.apply_gamma(image,settings.gamma)
        if settings.sharpen:image=image.filter(ImageFilter.UnsharpMask(radius=sharpen_radius,percent=sharpen_percent,threshold=2))
        if settings.dither:image=self.apply_dither(image)
        return image
    def profile_image(self,image,settings):
        profile=settings.processing_profile
        if profile=='Raw':return self._base_frame(image,settings)
        if profile=='Pixel-Dither':
            base=self.pixel_image(image,settings);base=ImageEnhance.Contrast(base).enhance(max(1.0,settings.contrast));base=ImageEnhance.Color(base).enhance(max(1.0,settings.saturation));base=self.apply_gamma(base,settings.gamma)
            return self.apply_dither(base,colors=32)
        if profile=='Detailed':
            softened=image.filter(ImageFilter.GaussianBlur(radius=.45));base=self._base_frame(softened,settings);base=self._fine_tune(base,settings,sharpen_percent=165,sharpen_radius=.8);base=self.quantize_clean(base,colors=48)
            return ImageOps.autocontrast(base,cutoff=.7)
        return self._fine_tune(self._base_frame(image,settings),settings,sharpen_percent=120,sharpen_radius=1.0)
    def optimize_image(self,image,settings):return self.profile_image(image,settings)
    def prepare_frame(self,frame,settings):return self.profile_image(frame.convert('RGB'),settings)
    def frame_index_for_time(self,t):
        if not self.frames or len(self.frames)==1:return 0
        total=sum(self.durations)
        if total<=0:return 0
        pos=t%total
        for i,duration in enumerate(self.durations):
            if pos<duration:return i
            pos-=duration
        return len(self.frames)-1
    def render(self,display,time,settings=None):
        if not self.frames:return
        settings=settings or self.settings;settings.clamp();fi=self.frame_index_for_time(time)
        key=(fi,settings.mode,settings.processing_profile,round(settings.crop_x,4),round(settings.crop_y,4),round(settings.zoom,4),round(settings.contrast,3),round(settings.saturation,3),settings.sharpen,round(settings.gamma,3),settings.dither)
        if key not in self.cache:self.cache[key]=list(self.prepare_frame(self.frames[fi],settings).getdata())
        pixels=self.cache[key];i=0
        for y in range(self.height):
            for x in range(self.width):display.set_pixel(x,y,pixels[i]);i+=1

class ImageLibrary:
    def __init__(self,folder='assets/images',width=64,height=32,metadata_file=None):
        self.folder=Path(folder);self.width=width;self.height=height;self.metadata_file=Path(metadata_file) if metadata_file else self.folder.parent/'image_settings.json'
        self.assets=[];self.metadata={'version':1,'assets':{},'playlists':{}};self.load_metadata();self.load();_LIBRARIES.append(self)
    def load_metadata(self):
        if not self.metadata_file.exists():return
        try:
            with open(self.metadata_file,'r',encoding='utf-8') as file:loaded=json.load(file)
            if isinstance(loaded,dict):self.metadata.update(loaded)
            if not isinstance(self.metadata.get('assets'),dict):self.metadata['assets']={}
            if not isinstance(self.metadata.get('playlists'),dict):self.metadata['playlists']={}
        except Exception as error:print(f'Could not load {self.metadata_file}: {error}')
    def save_metadata(self):
        try:
            self.metadata_file.parent.mkdir(parents=True,exist_ok=True);temporary=self.metadata_file.with_suffix('.tmp')
            with open(temporary,'w',encoding='utf-8') as file:json.dump(self.metadata,file,indent=2,sort_keys=True)
            temporary.replace(self.metadata_file)
        except Exception as error:print(f'Could not save {self.metadata_file}: {error}')
    def metadata_entry(self,filename):
        assets=self.metadata.setdefault('assets',{})
        if filename not in assets:assets[filename]={'tags':[],'favorite':False,'settings':ImageSettings().to_dict()}
        entry=assets[filename];entry.setdefault('tags',[]);entry.setdefault('favorite',False);entry.setdefault('settings',ImageSettings().to_dict());return entry
    def load(self):
        self.assets.clear();self.folder.mkdir(parents=True,exist_ok=True);files=sorted(path for path in self.folder.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS);changed=False
        for path in files:
            try:
                filename=path.name;existed=filename in self.metadata.get('assets',{});entry=self.metadata_entry(filename)
                if not existed:changed=True
                settings=ImageSettings.from_dict(entry.get('settings',{}));current=ImageAsset(path,self.width,self.height,settings=settings);self.assets.append(current);print(f'Loaded: {path.name} ({len(current.frames)} frame(s))')
            except Exception as error:print(f'Could not load {path.name}: {error}')
        if changed:self.save_metadata()
    def save_asset(self,asset):
        if asset is None:return
        self.metadata_entry(asset.path.name)['settings']=asset.settings.to_dict();self.save_metadata()
    def set_tags(self,asset,tags):
        if asset is None:return
        self.metadata_entry(asset.path.name)['tags']=sorted(set(str(tag).strip() for tag in tags if str(tag).strip()));self.save_metadata()
    def set_favorite(self,asset,favorite=True):
        if asset is None:return
        self.metadata_entry(asset.path.name)['favorite']=bool(favorite);self.save_metadata()
    def get(self,index):return None if not self.assets else self.assets[index%len(self.assets)]
    def names(self):return [asset.path.name for asset in self.assets]
    def __len__(self):return len(self.assets)

def _find_asset(filename):
    if not filename:return None,None
    for library in reversed(_LIBRARIES):
        for asset in library.assets:
            if asset.path.name==filename:return library,asset
    return None,None

def set_processing_profile(filename,profile):
    library,asset=_find_asset(filename)
    if not asset or profile not in PROCESSING_PROFILES:return False
    asset.settings.processing_profile=profile;asset.clear_cache();library.save_asset(asset);return True

def reset_processing(filename):
    library,asset=_find_asset(filename)
    if not asset:return False
    asset.settings.reset_processing();asset.clear_cache();library.save_asset(asset);return True
