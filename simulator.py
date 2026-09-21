import io, random, time, pygame
from PIL import Image
from display import VirtualDisplay
from effects import EFFECTS
from controller import TotemController
from particles import ParticleSystem
from image_assets import ImageLibrary
from secure_phone_server import PhoneControlServer
from visual_engine import TransitionManager, VisualLayerEngine, TRANSITIONS, LAYER_KEYS
from text_engine import TextRenderer, TEXT_FONTS, TEXT_MOTIONS, TEXT_COLORS, TEXT_EFFECTS, TEXT_BACKGROUNDS

W,H,S,GAP,UI = 64,32,8,24,185
PW,PH = W*S,H*S
pygame.init()
screen=pygame.display.set_mode((PW*2+GAP,PH+UI))
pygame.display.set_caption("Festival Totem Simulator")
clock=pygame.time.Clock();font=pygame.font.SysFont(None,22)
library=ImageLibrary("assets/images",W,H)
displays={s:VirtualDisplay(W,H) for s in ("front","back")}
particles={s:ParticleSystem(W,H,count=60) for s in ("front","back")}
transitions={s:TransitionManager(W,H) for s in ("front","back")}
layer_engine=VisualLayerEngine(W,H)
text_engine=TextRenderer(W,H)
MODES=["crop","pixel","optimize","dither"]
REACTIVE_PRESETS=["Pulse","Neon","Spark","Chaos"]
SCENES={
    "Chill":{"duration":8.0,"beat_sync":True,"transition":"Fade","transition_duration":1.15,"random":False,"reactive":"Neon","strength":0.45},
    "Pulse":{"duration":5.0,"beat_sync":True,"transition":"Zoom","transition_duration":0.65,"random":True,"reactive":"Pulse","strength":0.78},
    "Glitch":{"duration":4.0,"beat_sync":True,"transition":"Glitch","transition_duration":0.45,"random":True,"reactive":"Neon","strength":0.82},
    "Chaos":{"duration":3.0,"beat_sync":True,"transition":"Glitch","transition_duration":0.35,"random":True,"reactive":"Chaos","strength":1.0},
}
active_target="both"
current_scene="Custom"
audio={"volume":0.0,"bass":0.0,"mids":0.0,"highs":0.0,"beat":False,"last_update":0.0}
motion={"tilt_x":0.0,"tilt_y":0.0,"shake":0.0,"tap":False}
guest={"kind":None,"strength":0.0,"until":0.0,"locked":False,"x":.5,"y":.5,"velocity":0.0}

def slideshow_state():
    ids=list(range(len(library)));random.shuffle(ids)
    return {"active":bool(ids),"indices":ids,"position":0,"duration":5.0,"elapsed":0.0,"shuffle":True,"label":"All","beat_sync":True}
def reactive_state(): return {"enabled":False,"strength":0.65,"preset":"Pulse","layers":layer_engine.preset("Pulse")}
def transition_state(): return {"kind":"Fade","duration":0.8,"random":True}
def text_state():
    st=text_engine.defaults()
    st.update(enabled=False,background="Dimmed GIF",background_brightness=.30,backplate=True,speed=12.0)
    return st
panels={s:{"image_index":0,"slideshow":slideshow_state(),"reactive":reactive_state(),"transition":transition_state(),"text":text_state()} for s in ("front","back")}

def metadata(a): return library.metadata_entry(a.path.name) if a else {"tags":[],"favorite":False}
def asset(side): return library.get(panels[side]["image_index"]) if len(library) else None
def target_sides(): return ["front","back"] if active_target=="both" else [active_target]
def reference_side(): return "back" if active_target=="back" else "front"
def reference_asset(): return asset(reference_side())
def save_asset(a):
    if not a:return
    a.settings.clamp();a.clear_cache();library.save_asset(a)

def clamp01(v): return max(0.0,min(1.0,float(v)))
def audio_fresh(): return time.monotonic()-audio["last_update"]<1.0
def signals():
    out={"volume":0.0,"bass":0.0,"mids":0.0,"highs":0.0,"beat":False,**motion}
    if audio_fresh():out.update({k:audio[k] for k in ("volume","bass","mids","highs","beat")})
    return out

def party_fx(side,display,t): EFFECTS["Plasma"](display,t);particles[side].draw(display)
def image_fx(side,display,t):
    a=asset(side)
    if a:a.render(display,t,a.settings)
    else:display.clear()
def text_fx(side,display,t):
    display.clear();text_engine.render(display,panels[side]["text"],t,signals(),1000 if side=="back" else 0)
def make_effects(side): return {**EFFECTS,"Text":lambda d,t,s=side:text_fx(s,d,t),"Party":lambda d,t,s=side:party_fx(s,d,t),"Image":lambda d,t,s=side:image_fx(s,d,t)}
controllers={s:TotemController(make_effects(s)) for s in ("front","back")}
for s in ("front","back"):
    sh=panels[s]["slideshow"]
    if sh["indices"]:panels[s]["image_index"]=sh["indices"][0]
    controllers[s].set_effect("Image")

def choose_transition(side):
    ts=panels[side]["transition"]
    return random.choice([x for x in TRANSITIONS if x!="None"]) if ts["random"] else ts["kind"]
def begin_transition(side):
    ts=panels[side]["transition"];transitions[side].begin(displays[side],choose_transition(side),ts["duration"])
def stop_show(side):
    sh=panels[side]["slideshow"];sh["active"]=False;sh["elapsed"]=0.0

def select_for_side(side,index,stop=True,transition=True):
    if not len(library):return
    try:index=int(index)
    except (TypeError,ValueError):return
    index=max(0,min(len(library)-1,index))
    if index==panels[side]["image_index"] and controllers[side].effect_name=="Image":return
    if transition:begin_transition(side)
    panels[side]["image_index"]=index
    if stop:stop_show(side)
    controllers[side].set_effect("Image")
def select_image(index):
    for side in target_sides():select_for_side(side,index)

def clean_indices(values):
    out=[]
    if not isinstance(values,list):return out
    for v in values:
        try:i=int(v)
        except (TypeError,ValueError):continue
        if 0<=i<len(library) and i not in out:out.append(i)
    return out

def step_filtered(value):
    if not isinstance(value,dict):return
    ids=clean_indices(value.get("indices",[]))
    if not ids:return
    try:delta=int(value.get("delta",1))
    except (TypeError,ValueError):delta=1
    for side in target_sides():
        cur=panels[side]["image_index"]
        try:p=ids.index(cur)
        except ValueError:p=-1 if delta>0 else 0
        select_for_side(side,ids[(p+delta)%len(ids)])

def start_show(value):
    global current_scene
    if not isinstance(value,dict):return
    ids=clean_indices(value.get("indices",[]))
    if not ids:return
    try:duration=max(1.0,min(120.0,float(value.get("duration",5))))
    except (TypeError,ValueError):duration=5.0
    shuffle=bool(value.get("shuffle",False));label=str(value.get("label","Selection"))[:80]
    order=list(ids)
    if shuffle:random.shuffle(order)
    for side in target_sides():
        beat_sync=panels[side]["slideshow"].get("beat_sync",True)
        panels[side]["slideshow"].update(active=True,indices=list(order),position=0,duration=duration,elapsed=0.0,shuffle=shuffle,label=label,beat_sync=beat_sync)
        select_for_side(side,order[0],stop=False)
    current_scene="Custom"

def advance_show(side):
    sh=panels[side]["slideshow"]
    sh["elapsed"]=0.0;sh["position"]=(sh["position"]+1)%len(sh["indices"])
    if sh["shuffle"] and sh["position"]==0 and len(sh["indices"])>1:random.shuffle(sh["indices"])
    select_for_side(side,sh["indices"][sh["position"]],stop=False)

def update_shows(dt):
    for side in ("front","back"):
        sh=panels[side]["slideshow"]
        if controllers[side].paused or not sh["active"] or not sh["indices"]:continue
        sh["elapsed"]+=dt
        if sh["elapsed"]<sh["duration"]:continue
        if sh.get("beat_sync",False) and audio_fresh() and sh["elapsed"]<sh["duration"]+2.0 and not audio["beat"]:continue
        advance_show(side)

def thumbnail(index):
    try:i=int(index);a=library.get(i)
    except Exception:return None
    if not a or not a.frames:return None
    try:
        preview=a.prepare_frame(a.frames[0],a.settings).resize((256,128),Image.Resampling.NEAREST)
        out=io.BytesIO();preview.save(out,format="JPEG",quality=82,optimize=True);return out.getvalue()
    except Exception as e:print("Thumbnail error:",e);return None

server=PhoneControlServer(8765);server.set_thumbnail_provider(thumbnail);phone_url=server.start()

def mark_custom():
    global current_scene
    current_scene="Custom"
def set_target(v):
    global active_target
    if v in ("front","back","both"):active_target=v
def set_effect(v):
    for side in target_sides():
        if v in controllers[side].effects:begin_transition(side);controllers[side].set_effect(v)
def master(attr,value,lo,hi):
    try:v=max(lo,min(hi,float(value)))
    except (TypeError,ValueError):return
    for side in target_sides():setattr(controllers[side],attr,v)
def toggle_pause():
    pause=not all(controllers[s].paused for s in target_sides())
    for s in target_sides():controllers[s].paused=pause

def reload_library():
    old={s:(asset(s).path.name if asset(s) else None) for s in ("front","back")};library.load()
    for s in ("front","back"):
        panels[s]["image_index"]=0;stop_show(s)
        if old[s]:
            for i,a in enumerate(library.assets):
                if a.path.name==old[s]:panels[s]["image_index"]=i;break

def update_audio(value):
    if not isinstance(value,dict):return
    for k in ("volume","bass","mids","highs"):
        if k in value:
            try:audio[k]=clamp01(value[k])
            except Exception:pass
    audio["beat"]=bool(value.get("beat",False));audio["last_update"]=time.monotonic()
def update_motion(value):
    if not isinstance(value,dict):return
    for k in ("tilt_x","tilt_y"):
        if k in value:
            try:motion[k]=max(-1.0,min(1.0,float(value[k])))
            except Exception:pass
    if "shake" in value:
        try:motion["shake"]=clamp01(value["shake"])
        except Exception:pass
    motion["tap"]=bool(value.get("tap",False))
def set_reactive_enabled(value):
    for s in target_sides():panels[s]["reactive"]["enabled"]=bool(value)
def set_reactive_strength(value):
    try:v=max(0.0,min(1.5,float(value)))
    except (TypeError,ValueError):return
    for s in target_sides():panels[s]["reactive"]["strength"]=v
    mark_custom()
def set_reactive_preset(value):
    if value not in REACTIVE_PRESETS:return
    for s in target_sides():
        r=panels[s]["reactive"];r["preset"]=value;r["layers"]=layer_engine.preset(value)
    mark_custom()
def set_layer(value):
    if not isinstance(value,dict):return
    name=value.get("name")
    if name not in LAYER_KEYS:return
    try:amount=max(0.0,min(1.5,float(value.get("value",0))))
    except (TypeError,ValueError):return
    for s in target_sides():panels[s]["reactive"]["layers"][name]=amount;panels[s]["reactive"]["preset"]="Custom"
    mark_custom()
def set_transition(value):
    if not isinstance(value,dict):return
    for s in target_sides():
        t=panels[s]["transition"]
        if value.get("kind") in TRANSITIONS:t["kind"]=value["kind"]
        if "duration" in value:
            try:t["duration"]=max(.08,min(5.0,float(value["duration"])))
            except (TypeError,ValueError):pass
        if "random" in value:t["random"]=bool(value["random"])
    mark_custom()
def set_beat_sync(value):
    for s in target_sides():panels[s]["slideshow"]["beat_sync"]=bool(value)
    mark_custom()
def apply_scene(name):
    global current_scene
    scene=SCENES.get(name)
    if not scene:return
    for s in target_sides():
        sh=panels[s]["slideshow"];tr=panels[s]["transition"];r=panels[s]["reactive"]
        if not sh["indices"]:sh["indices"]=list(range(len(library)));random.shuffle(sh["indices"])
        sh.update(active=bool(sh["indices"]),duration=scene["duration"],elapsed=0.0,shuffle=True,beat_sync=scene["beat_sync"])
        tr.update(kind=scene["transition"],duration=scene["transition_duration"],random=scene["random"])
        r.update(enabled=True,strength=scene["strength"],preset=scene["reactive"],layers=layer_engine.preset(scene["reactive"]))
        controllers[s].set_effect("Image")
    current_scene=name

def set_text_settings(value):
    if not isinstance(value,dict):return
    for s in target_sides():
        st=panels[s]["text"]
        if "message" in value:st["message"]=str(value["message"])[:120]
        if value.get("font") in TEXT_FONTS:st["font"]=value["font"]
        if value.get("motion") in TEXT_MOTIONS:st["motion"]=value["motion"]
        if value.get("color_mode") in TEXT_COLORS:st["color_mode"]=value["color_mode"]
        if "color" in value:st["color"]=str(value["color"])[:16]
        if "scale" in value:
            try:st["scale"]=max(1,min(3,int(value["scale"])))
            except (TypeError,ValueError):pass
        if "speed" in value:
            try:st["speed"]=max(1.0,min(40.0,float(value["speed"])))
            except (TypeError,ValueError):pass
        for k in ("glow","wave","glitch","beat_pulse"):
            if k in value:st[k]=bool(value[k])
        st["background"]="Dimmed GIF";st["background_brightness"]=.30;st["backplate"]=True

def show_text(value=None):
    if isinstance(value,dict):set_text_settings(value)
    for s in target_sides():panels[s]["text"]["enabled"]=True

def hide_text():
    for s in target_sides():panels[s]["text"]["enabled"]=False

def refresh_text(value=None):
    if isinstance(value,dict):set_text_settings(value)

def trigger_guest(value):
    global guest
    if guest["locked"] or not isinstance(value,dict):return
    kind=str(value.get("kind","")).lower();strength=clamp01(value.get("strength",1.0))
    guest={"kind":kind,"strength":strength,"until":time.monotonic()+float(value.get("duration",30)),"locked":False,"x":.5,"y":.5,"velocity":0.0}

def update_guest_xy(value):
    global guest
    if guest["locked"] or not isinstance(value,dict):return
    try:x=clamp01(value.get("x",.5));y=clamp01(value.get("y",.5));velocity=clamp01(value.get("velocity",0));strength=clamp01(value.get("strength",1))
    except Exception:return
    guest={"kind":"xy","strength":strength,"until":time.monotonic()+.30,"locked":False,"x":x,"y":y,"velocity":velocity}

def stop_guest():
    guest.update(kind=None,strength=0.0,until=0.0,velocity=0.0)

def apply_guest_effect(display,frame_number):
    kind=guest.get("kind");amount=clamp01(guest.get("strength",1.0))
    if not kind or guest.get("locked"):return
    if kind in ("glitch","rainbow","chaos"):
        layer_engine.guest_burst(display,kind,amount,frame_number);return
    if kind=="warp":
        layer_engine._zoom(display,.10+amount*.32)
        layer_engine._shift(display,int(random.choice((-1,1))*amount*2),int(random.choice((-1,1))*amount))
        layer_engine._hue(display,(frame_number*5)%360)
        return
    if kind=="prism":
        layer_engine._rgb_split(display,.28+amount*.70)
        layer_engine._hue(display,(frame_number*8)%360)
        layer_engine._sparkles(display,amount*.35,frame_number*23)
        return
    if kind=="meltdown":
        layer_engine._zoom(display,amount*.16)
        layer_engine._shift(display,int(__import__('math').sin(frame_number*.45)*amount*5),int(__import__('math').cos(frame_number*.31)*amount*4))
        layer_engine._hue(display,(frame_number*3)%240)
        return
    if kind=="xy":
        x=clamp01(guest.get("x",.5));y=clamp01(guest.get("y",.5));v=clamp01(guest.get("velocity",0))
        layer_engine._hue(display,(x-.5)*300*amount)
        layer_engine._rgb_split(display,abs(x-.5)*1.55*amount)
        layer_engine._zoom(display,y*.34*amount)
        if v>.03:
            layer_engine._shift(display,int(__import__('math').sin(frame_number*1.8)*v*amount*7),int(__import__('math').cos(frame_number*1.4)*v*amount*4))
            layer_engine._sparkles(display,v*amount,frame_number*37)

def command(data):
    c,v=data.get("command"),data.get("value")
    if c=="set_target":set_target(v);return
    if c=="effect":set_effect(v);return
    if c=="select_image":select_image(v);return
    if c=="filtered_step":step_filtered(v);return
    if c=="slideshow_start":start_show(v);return
    if c=="slideshow_stop":
        for s in target_sides():stop_show(s)
        mark_custom();return
    if c=="slideshow_beat_sync":set_beat_sync(v);return
    if c=="performance_scene":apply_scene(v);return
    if c=="text_settings":set_text_settings(v);return
    if c=="text_show":show_text(v);return
    if c=="text_hide":hide_text();return
    if c=="text_refresh":refresh_text(v);return
    if c=="brightness":master("brightness",v,.1,1);return
    if c=="speed":master("speed",v,.1,5);return
    if c=="toggle_pause":toggle_pause();return
    if c=="reload_library":reload_library();return
    if c=="audio_frame":update_audio(v);return
    if c=="motion_frame":update_motion(v);return
    if c=="reactive_enabled":set_reactive_enabled(v);return
    if c=="reactive_strength":set_reactive_strength(v);return
    if c=="reactive_preset":set_reactive_preset(v);return
    if c=="reactive_layer":set_layer(v);return
    if c=="transition_settings":set_transition(v);return
    if c=="guest_action":trigger_guest(v);return
    if c=="guest_xy":update_guest_xy(v);return
    if c=="guest_stop":stop_guest();return
    if c=="guest_lock":guest["locked"]=bool(v);return
    if c in ("mode_prev","mode_next"):
        a=reference_asset()
        if a:
            try:i=MODES.index(a.settings.mode)
            except ValueError:i=0
            a.settings.mode=MODES[(i+(-1 if c=="mode_prev" else 1))%len(MODES)];save_asset(a)
        return
    a=reference_asset()
    if c=="toggle_favorite":
        if a:library.set_favorite(a,not bool(metadata(a).get("favorite",False)))
        return
    if c=="set_favorite_index" and isinstance(v,dict):
        try:t=library.get(int(v.get("index")))
        except Exception:t=None
        if t:library.set_favorite(t,bool(v.get("favorite",False)))
        return
    if c=="set_tags":
        if a and isinstance(v,list):library.set_tags(a,list(dict.fromkeys(str(x).strip() for x in v if str(x).strip())))
        return
    if not a:return
    st=a.settings;changed=False
    if c in ("zoom","crop_x","crop_y","contrast","saturation","gamma"):
        try:setattr(st,c,float(v));changed=True
        except (TypeError,ValueError):pass
    elif c=="toggle_sharpen":st.sharpen=not st.sharpen;changed=True
    elif c=="toggle_dither":st.dither=not st.dither;changed=True
    elif c=="reset_image":st.reset();changed=True
    if changed:save_asset(a)

def phone_panel(side):
    ctl=controllers[side];a=asset(side);sh=panels[side]["slideshow"];r=panels[side]["reactive"];tr=panels[side]["transition"]
    out={"effect":ctl.effect_name,"speed":ctl.speed,"brightness":ctl.brightness,"paused":ctl.paused,"image_index_zero":panels[side]["image_index"],"image_index":0,"image_name":None,"image_mode":None,"image_settings":None,"image_tags":[],"image_favorite":False,"slideshow":{"active":sh["active"],"duration":sh["duration"],"shuffle":sh["shuffle"],"label":sh["label"],"count":len(sh["indices"]),"beat_sync":sh.get("beat_sync",False)},"reactive":{"enabled":r["enabled"],"strength":r["strength"],"preset":r["preset"],"layers":dict(r["layers"])},"transition":dict(tr),"text":dict(panels[side]["text"])}
    if a:
        m=metadata(a);out.update(image_index=panels[side]["image_index"]+1,image_name=a.path.name,image_mode=a.settings.mode,image_settings=a.settings.to_dict(),image_tags=m.get("tags",[]),image_favorite=bool(m.get("favorite",False)))
    return out

def update_phone():
    lib=[]
    for i,a in enumerate(library.assets):
        m=metadata(a);lib.append({"index":i,"name":a.path.name,"tags":m.get("tags",[]),"favorite":bool(m.get("favorite",False))})
    ref=phone_panel(reference_side())
    server.update_state({"target":active_target,"reference_side":reference_side(),"image_count":len(library),"library":lib,"effects":list(controllers["front"].effects),"panels":{"front":phone_panel("front"),"back":phone_panel("back")},"audio":{"volume":audio["volume"],"bass":audio["bass"],"mids":audio["mids"],"highs":audio["highs"],"beat":audio["beat"],"fresh":audio_fresh()},"motion":dict(motion),"reactive_presets":REACTIVE_PRESETS,"layer_keys":LAYER_KEYS,"transitions":TRANSITIONS,"performance_scenes":list(SCENES),"current_scene":current_scene,"text_fonts":TEXT_FONTS,"text_motions":TEXT_MOTIONS,"text_color_modes":TEXT_COLORS,"text_effects":TEXT_EFFECTS,"text_backgrounds":TEXT_BACKGROUNDS,"guest":{"locked":guest["locked"]},**ref})

def draw_panel(side,x):
    d,ctl=displays[side],controllers[side]
    for y in range(H):
        for px in range(W):
            c=d.get_pixel(px,y);b=ctl.brightness
            pygame.draw.rect(screen,(int(c[0]*b),int(c[1]*b),int(c[2]*b)),(x+px*S,y*S,S-1,S-1))
def draw_ui():
    f,b=phone_panel("front"),phone_panel("back")
    screen.blit(font.render(f"FRONT: {f['effect']} | {f['image_name'] or '-'}",True,(220,220,220)),(10,PH+10))
    screen.blit(font.render(f"BACK: {b['effect']} | {b['image_name'] or '-'}",True,(220,220,220)),(10,PH+36))
    screen.blit(font.render(f"Target: {active_target.upper()}   {phone_url}",True,(190,190,190)),(10,PH+62))
    screen.blit(font.render(f"Audio V:{audio['volume']:.2f} B:{audio['bass']:.2f} M:{audio['mids']:.2f} H:{audio['highs']:.2f} Beat:{'YES' if audio['beat'] else '-'}",True,(170,205,255)),(10,PH+88))
    screen.blit(font.render(f"Scene: {current_scene}  Beat Sync: {'ON' if f['slideshow']['beat_sync'] else 'OFF'}",True,(185,185,220)),(10,PH+114))
def keys(key):
    if key==pygame.K_ESCAPE:return False
    if key==pygame.K_f:set_target('front')
    elif key==pygame.K_b:set_target('back')
    elif key==pygame.K_m:set_target('both')
    elif key==pygame.K_SPACE:toggle_pause()
    return True

update_phone();running=True;frame_number=0
while running:
    dt=clock.tick(60)/1000;frame_number+=1
    for e in pygame.event.get():
        if e.type==pygame.QUIT:running=False
        elif e.type==pygame.KEYDOWN:running=keys(e.key)
    for data in server.get_commands():command(data)
    for s in ("front","back"):
        controllers[s].update(dt)
        if not controllers[s].paused:particles[s].update(dt)
        transitions[s].update(dt)
    update_shows(dt)
    if guest["kind"] and time.monotonic()>guest["until"]:stop_guest()
    sig=signals()
    for s in ("front","back"):
        controllers[s].effect(displays[s],controllers[s].time)
        transitions[s].apply(displays[s])
        r=panels[s]["reactive"]
        if r["enabled"]:layer_engine.apply(displays[s],sig,r["layers"],r["strength"],frame_number,1000 if s=="back" else 0)
        st=panels[s]["text"]
        if st.get("enabled",False):
            text_engine.prepare_background(displays[s],st)
            text_engine.render(displays[s],st,controllers[s].time,sig,1000 if s=="back" else 0,clear_background=False)
        apply_guest_effect(displays[s],frame_number+(1000 if s=="back" else 0))
    motion["tap"]=False;motion["shake"]*=.90
    screen.fill((15,15,18));draw_panel("front",0);draw_panel("back",PW+GAP);draw_ui();update_phone();pygame.display.flip()
server.stop();pygame.quit()
