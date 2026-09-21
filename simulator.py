import io, random, time, pygame
from PIL import Image
from display import VirtualDisplay
from effects import EFFECTS, hsv_to_rgb
from controller import TotemController
from text import draw_scrolling_text
from particles import ParticleSystem
from image_assets import ImageLibrary
from secure_phone_server import PhoneControlServer
from visual_engine import TransitionManager, VisualLayerEngine, TRANSITIONS, LAYER_KEYS

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
MODES=["crop","pixel","optimize","dither"]
REACTIVE_PRESETS=["Pulse","Neon","Spark","Chaos"]
active_target="both"
audio={"volume":0.0,"bass":0.0,"mids":0.0,"highs":0.0,"beat":False,"last_update":0.0}
motion={"tilt_x":0.0,"tilt_y":0.0,"shake":0.0,"tap":False}
guest={"kind":None,"strength":0.0,"until":0.0,"locked":False}

def slideshow_state(): return {"active":False,"indices":[],"position":0,"duration":5.0,"elapsed":0.0,"shuffle":False,"label":"All"}
def reactive_state(): return {"enabled":False,"strength":0.65,"preset":"Pulse","layers":layer_engine.preset("Pulse")}
def transition_state(): return {"kind":"Fade","duration":0.8,"random":False}
panels={s:{"image_index":0,"slideshow":slideshow_state(),"reactive":reactive_state(),"transition":transition_state()} for s in ("front","back")}

def metadata(a): return library.metadata_entry(a.path.name) if a else {"tags":[],"favorite":False}
def asset(side): return library.get(panels[side]["image_index"]) if len(library) else None
def target_sides(): return ["front","back"] if active_target=="both" else [active_target]
def reference_side(): return "back" if active_target=="back" else "front"
def reference_asset(): return asset(reference_side())
def save_asset(a):
    if not a:return
    a.settings.clamp();a.clear_cache();library.save_asset(a)

def text_fx(display,t): draw_scrolling_text(display,"FESTIVAL MODE",t,color=hsv_to_rgb((t*80)%360),scale=1,speed=12)
def party_fx(side,display,t): EFFECTS["Plasma"](display,t);particles[side].draw(display)
def image_fx(side,display,t):
    a=asset(side)
    if a:a.render(display,t,a.settings)
    else:display.clear()
def make_effects(side):
    return {**EFFECTS,"Text":text_fx,"Party":lambda d,t,s=side:party_fx(s,d,t),"Image":lambda d,t,s=side:image_fx(s,d,t)}
controllers={s:TotemController(make_effects(s)) for s in ("front","back")}

def clamp01(v): return max(0.0,min(1.0,float(v)))
def audio_fresh(): return time.monotonic()-audio["last_update"]<1.0
def signals():
    out={"volume":0.0,"bass":0.0,"mids":0.0,"highs":0.0,"beat":False,**motion}
    if audio_fresh(): out.update({k:audio[k] for k in ("volume","bass","mids","highs","beat")})
    return out

def choose_transition(side):
    ts=panels[side]["transition"]
    if ts["random"]: return random.choice([x for x in TRANSITIONS if x!="None"])
    return ts["kind"]
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
    if not isinstance(value,dict):return
    ids=clean_indices(value.get("indices",[]))
    if not ids:return
    try:duration=max(1.0,min(120.0,float(value.get("duration",5))))
    except (TypeError,ValueError):duration=5.0
    shuffle=bool(value.get("shuffle",False));label=str(value.get("label","Selection"))[:80]
    order=list(ids)
    if shuffle:random.shuffle(order)
    for side in target_sides():
        panels[side]["slideshow"].update(active=True,indices=list(order),position=0,duration=duration,elapsed=0.0,shuffle=shuffle,label=label)
        select_for_side(side,order[0],stop=False)

def update_shows(dt):
    for side in ("front","back"):
        sh=panels[side]["slideshow"]
        if controllers[side].paused or not sh["active"] or not sh["indices"]:continue
        sh["elapsed"]+=dt
        if sh["elapsed"]<sh["duration"]:continue
        sh["elapsed"]%=sh["duration"];sh["position"]=(sh["position"]+1)%len(sh["indices"])
        if sh["shuffle"] and sh["position"]==0 and len(sh["indices"])>1:random.shuffle(sh["indices"])
        select_for_side(side,sh["indices"][sh["position"]],stop=False)

def thumbnail(index):
    try:i=int(index);a=library.get(i)
    except Exception:return None
    if not a or not a.frames:return None
    try:
        preview=a.prepare_frame(a.frames[0],a.settings).resize((256,128),Image.Resampling.NEAREST)
        out=io.BytesIO();preview.save(out,format="JPEG",quality=82,optimize=True);return out.getvalue()
    except Exception as e: print("Thumbnail error:",e);return None

server=PhoneControlServer(8765);server.set_thumbnail_provider(thumbnail);phone_url=server.start()

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
def set_reactive_preset(value):
    if value not in REACTIVE_PRESETS:return
    for s in target_sides():
        r=panels[s]["reactive"];r["preset"]=value;r["layers"]=layer_engine.preset(value)
def set_layer(value):
    if not isinstance(value,dict):return
    name=value.get("name")
    if name not in LAYER_KEYS:return
    try:amount=max(0.0,min(1.5,float(value.get("value",0))))
    except (TypeError,ValueError):return
    for s in target_sides():panels[s]["reactive"]["layers"][name]=amount;panels[s]["reactive"]["preset"]="Custom"
def set_transition(value):
    if not isinstance(value,dict):return
    for s in target_sides():
        t=panels[s]["transition"]
        if value.get("kind") in TRANSITIONS:t["kind"]=value["kind"]
        if "duration" in value:
            try:t["duration"]=max(.08,min(5.0,float(value["duration"])))
            except (TypeError,ValueError):pass
        if "random" in value:t["random"]=bool(value["random"])

def trigger_guest(value):
    global guest
    if guest["locked"] or not isinstance(value,dict):return
    kind=str(value.get("kind","")).lower();strength=clamp01(value.get("strength",1.0))
    if kind=="next": step_filtered({"indices":list(range(len(library))),"delta":1});return
    if kind=="random":
        if len(library):select_image(random.randrange(len(library)))
        return
    if kind=="melt":
        for s in target_sides():panels[s]["transition"]["kind"]="Melt"
        step_filtered({"indices":list(range(len(library))),"delta":1});return
    guest={"kind":kind,"strength":strength,"until":time.monotonic()+float(value.get("duration",.7)),"locked":False}
def stop_guest():guest.update(kind=None,strength=0.0,until=0.0)

def command(data):
    c,v=data.get("command"),data.get("value")
    if c=="set_target":set_target(v);return
    if c=="effect":set_effect(v);return
    if c=="select_image":select_image(v);return
    if c=="filtered_step":step_filtered(v);return
    if c=="slideshow_start":start_show(v);return
    if c=="slideshow_stop":
        for s in target_sides():stop_show(s)
        return
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
    out={"effect":ctl.effect_name,"speed":ctl.speed,"brightness":ctl.brightness,"paused":ctl.paused,"image_index_zero":panels[side]["image_index"],"image_index":0,"image_name":None,"image_mode":None,"image_settings":None,"image_tags":[],"image_favorite":False,"slideshow":{"active":sh["active"],"duration":sh["duration"],"shuffle":sh["shuffle"],"label":sh["label"],"count":len(sh["indices"])},"reactive":{"enabled":r["enabled"],"strength":r["strength"],"preset":r["preset"],"layers":dict(r["layers"])},"transition":dict(tr)}
    if a:
        m=metadata(a);out.update(image_index=panels[side]["image_index"]+1,image_name=a.path.name,image_mode=a.settings.mode,image_settings=a.settings.to_dict(),image_tags=m.get("tags",[]),image_favorite=bool(m.get("favorite",False)))
    return out

def update_phone():
    lib=[]
    for i,a in enumerate(library.assets):
        m=metadata(a);lib.append({"index":i,"name":a.path.name,"tags":m.get("tags",[]),"favorite":bool(m.get("favorite",False))})
    ref=phone_panel(reference_side())
    server.update_state({"target":active_target,"reference_side":reference_side(),"image_count":len(library),"library":lib,"effects":list(controllers["front"].effects),"panels":{"front":phone_panel("front"),"back":phone_panel("back")},"audio":{"volume":audio["volume"],"bass":audio["bass"],"mids":audio["mids"],"highs":audio["highs"],"beat":audio["beat"],"fresh":audio_fresh()},"motion":dict(motion),"reactive_presets":REACTIVE_PRESETS,"layer_keys":LAYER_KEYS,"transitions":TRANSITIONS,"guest":{"locked":guest["locked"]},**ref})

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
    screen.blit(font.render(f"Transition: {f['transition']['kind']}  Guest: {'LOCKED' if guest['locked'] else 'READY'}",True,(185,185,220)),(10,PH+114))
def keys(key):
    if key==pygame.K_ESCAPE:return False
    mapping={pygame.K_1:"Rainbow",pygame.K_2:"Waves",pygame.K_3:"Plasma",pygame.K_4:"Stars",pygame.K_5:"Text",pygame.K_6:"Party",pygame.K_7:"Image"}
    if key in mapping:set_effect(mapping[key])
    elif key==pygame.K_f:set_target("front")
    elif key==pygame.K_b:set_target("back")
    elif key==pygame.K_m:set_target("both")
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
        controllers[s].effect(displays[s],controllers[s].time);transitions[s].apply(displays[s])
        r=panels[s]["reactive"]
        if r["enabled"]:layer_engine.apply(displays[s],sig,r["layers"],r["strength"],frame_number,1000 if s=="back" else 0)
        if guest["kind"] and not guest["locked"]:layer_engine.guest_burst(displays[s],guest["kind"],guest["strength"],frame_number)
    motion["tap"]=False;motion["shake"]*=.90
    screen.fill((15,15,18));draw_panel("front",0);draw_panel("back",PW+GAP);draw_ui();update_phone();pygame.display.flip()
server.stop();pygame.quit()
