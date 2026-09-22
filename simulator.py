import io, random, time, pygame
from PIL import Image
from effects import EFFECTS
from controller import TotemController
from particles import ParticleSystem
from image_assets import ImageLibrary
from icon_assets import ICON_LIBRARY
from runtime_io import SignalStore, VirtualDisplayBackend
from secure_phone_server import PhoneControlServer
from visual_engine import VisualLayerEngine, TRANSITIONS, LAYER_KEYS, copy_pixels
from transition_engine import TransitionManager, INTENSE_TRANSITIONS
from chaos_engine import ChaosEngine
from text_engine import TextRenderer, TEXT_FONTS, TEXT_MOTIONS, TEXT_COLORS, TEXT_EFFECTS, TEXT_BACKGROUNDS
from overlay_engine import OverlayRenderer

W,H,S,GAP,UI = 64,32,8,24,185
PW,PH = W*S,H*S
SIDES=("front","back")
ICON_MOTIONS=("Bounce","Orbit")
ICON_TRANSITION_DURATION=.55
PHONE_STATE_INTERVAL=.10
pygame.init()
screen=pygame.display.set_mode((PW*2+GAP,PH+UI))
pygame.display.set_caption("Festival Totem Simulator")
clock=pygame.time.Clock();font=pygame.font.SysFont(None,22)
library=ImageLibrary("assets/images",W,H)
display_backend=VirtualDisplayBackend(W,H)
displays=display_backend.displays
signal_store=SignalStore()
audio=signal_store.audio
motion=signal_store.motion
particles={s:ParticleSystem(W,H,count=60) for s in SIDES}
content_transitions={s:TransitionManager(W,H) for s in SIDES}
scene_transitions={s:TransitionManager(W,H) for s in SIDES}
content_snapshots={s:None for s in SIDES}
scene_snapshots={s:None for s in SIDES}
layer_engine=VisualLayerEngine(W,H)
chaos_engine=ChaosEngine(layer_engine)
text_engine=TextRenderer(W,H)
overlay_engine=OverlayRenderer(W,H)
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
_library_state_cache=None

def slideshow_state():
    ids=list(range(len(library)));random.shuffle(ids)
    return {"active":bool(ids),"indices":ids,"position":0,"duration":10.0,"elapsed":0.0,"shuffle":True,"label":"All","beat_sync":True}
def reactive_state(): return {"enabled":False,"strength":0.65,"preset":"Pulse","layers":layer_engine.preset("Pulse")}
def transition_state(): return {"kind":"Fade","duration":0.8,"random":True}
def text_state():
    st=text_engine.defaults()
    st.update(enabled=False,background="Dimmed GIF",background_brightness=.30,backplate=True,speed=34.0,motion="Static",audio_reactivity="Off",glow=False,wave=False,glitch=False,beat_pulse=False)
    if st.get("color_mode")=="Audio":st["color_mode"]="Rainbow"
    return st
def icon_state():
    names=ICON_LIBRARY.names()
    return {"icon_enabled":False,"icon":names[0] if names else None,"motion":"Bounce","transition_entering":True,"transition_started":0.0,"transition_active":False,"transition_duration":ICON_TRANSITION_DURATION}

panels={s:{"image_index":0,"slideshow":slideshow_state(),"reactive":reactive_state(),"transition":transition_state(),"text":text_state(),"icon":icon_state()} for s in SIDES}
if len(library)>1:
    f=panels["front"]["slideshow"]["indices"];b=panels["back"]["slideshow"]["indices"]
    if f and b and f[0]==b[0]:b[0],b[1]=b[1],b[0]

def metadata(a): return library.metadata_entry(a.path.name) if a else {"tags":[],"favorite":False}
def asset(side): return library.get(panels[side]["image_index"]) if len(library) else None
def target_sides(): return list(SIDES) if active_target=="both" else [active_target]
def reference_side(): return "back" if active_target=="back" else "front"
def reference_asset(): return asset(reference_side())
def save_asset(a):
    if not a:return
    a.settings.clamp();a.clear_cache();library.save_asset(a)

def invalidate_library_state():
    global _library_state_cache
    _library_state_cache=None

def library_state():
    global _library_state_cache
    if _library_state_cache is None:
        out=[]
        for i,a in enumerate(library.assets):
            m=metadata(a);out.append({"index":i,"name":a.path.name,"tags":list(m.get("tags",[])),"favorite":bool(m.get("favorite",False))})
        _library_state_cache=out
    return _library_state_cache

def audio_fresh(): return signal_store.audio_fresh()
def signals(): return signal_store.snapshot()

def party_fx(side,display,t): EFFECTS["Plasma"](display,t);particles[side].draw(display)
def image_fx(side,display,t):
    a=asset(side)
    if a:a.render(display,t,a.settings)
    else:display.clear()
def make_effects(side): return {**EFFECTS,"Party":lambda d,t,s=side:party_fx(s,d,t),"Image":lambda d,t,s=side:image_fx(s,d,t)}
controllers={s:TotemController(make_effects(s)) for s in SIDES}
for s in SIDES:
    sh=panels[s]["slideshow"]
    if sh["indices"]:panels[s]["image_index"]=sh["indices"][0]
    controllers[s].set_effect("Image")

def choose_transition(side):
    ts=panels[side]["transition"]
    return random.choice([x for x in TRANSITIONS if x!="None"]) if ts["random"] else ts["kind"]
def begin_transition(side):
    ts=panels[side]["transition"]
    content_transitions[side].begin(displays[side],choose_transition(side),ts["duration"],source=content_snapshots[side])
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

def next_index_for_side(side,fallback_ids):
    sh=panels[side]["slideshow"]
    ids=list(sh.get("indices",[])) if sh.get("active") and sh.get("indices") else fallback_ids
    if not ids:return None,None
    cur=panels[side]["image_index"]
    try:p=ids.index(cur)
    except ValueError:p=-1
    return ids[(p+1)%len(ids)],p

def commit_transition_next(side,nxt,p):
    if nxt is None:return
    sh=panels[side]["slideshow"]
    panels[side]["image_index"]=nxt
    controllers[side].set_effect("Image")
    if sh.get("active"):
        sh["position"]=(p+1)%len(sh["indices"])
        sh["elapsed"]=0.0

def pixel_melt_next(value):
    if not isinstance(value,dict):return
    fallback_ids=clean_indices(value.get("indices",[]))
    try:duration=max(.25,min(5.0,float(value.get("duration",1.8))))
    except (TypeError,ValueError):duration=1.8
    for side in target_sides():
        nxt,p=next_index_for_side(side,fallback_ids)
        if nxt is None:continue
        content_transitions[side].begin(displays[side],"Melt",duration,source=content_snapshots[side])
        commit_transition_next(side,nxt,p)

def intense_transition_next(value):
    global active_target
    if not isinstance(value,dict):return
    fallback_ids=clean_indices(value.get("indices",[]))
    kind=str(value.get("kind","Morph"))
    if kind not in INTENSE_TRANSITIONS:kind="Morph"
    try:duration=max(.25,min(4.0,float(value.get("duration",1.15))))
    except (TypeError,ValueError):duration=1.15
    active_target="both"
    for side in SIDES:
        nxt,p=next_index_for_side(side,fallback_ids)
        if nxt is None:continue
        scene_transitions[side].begin(displays[side],kind,duration,source=scene_snapshots[side])
        commit_transition_next(side,nxt,p)

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
    sides=target_sides()
    for side in sides:
        beat_sync=panels[side]["slideshow"].get("beat_sync",True)
        side_order=list(order)
        if shuffle and len(sides)==1:random.shuffle(side_order)
        panels[side]["slideshow"].update(active=True,indices=side_order,position=0,duration=duration,elapsed=0.0,shuffle=shuffle,label=label,beat_sync=beat_sync)
        select_for_side(side,side_order[0],stop=False)
    current_scene="Custom"

def advance_show(side):
    sh=panels[side]["slideshow"]
    sh["elapsed"]=0.0;sh["position"]=(sh["position"]+1)%len(sh["indices"])
    if sh["shuffle"] and sh["position"]==0 and len(sh["indices"])>1:random.shuffle(sh["indices"])
    select_for_side(side,sh["indices"][sh["position"]],stop=False)

def update_shows(dt):
    for side in SIDES:
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

def normalize_icons():
    names=ICON_LIBRARY.names();fallback=names[0] if names else None
    for side in SIDES:
        st=panels[side]["icon"]
        if st.get("icon") not in names:
            st["icon"]=fallback
            if fallback is None:st.update(icon_enabled=False,transition_active=False)

def reload_library():
    old={s:(asset(s).path.name if asset(s) else None) for s in SIDES};library.load();ICON_LIBRARY.reload();normalize_icons();invalidate_library_state()
    for s in SIDES:
        panels[s]["image_index"]=0;stop_show(s)
        if old[s]:
            for i,a in enumerate(library.assets):
                if a.path.name==old[s]:panels[s]["image_index"]=i;break

def begin_icon_transition(st,entering):
    st["transition_entering"]=bool(entering);st["transition_started"]=time.monotonic();st["transition_active"]=True;st["transition_duration"]=ICON_TRANSITION_DURATION

def set_icon_enabled(side,enabled,animate=True):
    st=panels[side]["icon"]
    if enabled:
        if not st["icon_enabled"]:
            st["icon_enabled"]=True
            if animate:begin_icon_transition(st,True)
    elif st["icon_enabled"]:
        if animate:begin_icon_transition(st,False)
        else:st.update(icon_enabled=False,transition_active=False)

def toggle_icon(name):
    names=ICON_LIBRARY.names()
    if name not in names:return
    enabled_any=False
    for side in target_sides():
        st=panels[side]["icon"]
        if st["icon_enabled"] and st.get("icon")==name:
            set_icon_enabled(side,False,True)
        else:
            changing=st.get("icon")!=name
            st["icon"]=name;st["icon_enabled"]=True
            if changing or not st.get("transition_active"):begin_icon_transition(st,True)
            enabled_any=True
    if enabled_any:hide_text()

def clear_icon():
    for side in target_sides():set_icon_enabled(side,False,True)
def set_icon_motion(value):
    if value not in ICON_MOTIONS:return
    for side in target_sides():panels[side]["icon"]["motion"]=value

def update_icon_transitions():
    now=time.monotonic()
    for side in SIDES:
        st=panels[side]["icon"]
        if not st.get("transition_active"):continue
        if now-float(st.get("transition_started",now))<float(st.get("transition_duration",ICON_TRANSITION_DURATION)):continue
        st["transition_active"]=False
        if not st.get("transition_entering",True):st["icon_enabled"]=False

def update_audio(value): signal_store.update_audio(value)
def update_motion(value): signal_store.update_motion(value)
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
        color_mode=value.get("color_mode",st.get("color_mode","Rainbow"))
        st["color_mode"]=color_mode if color_mode in TEXT_COLORS and color_mode!="Audio" else "Rainbow"
        if "color" in value:st["color"]=str(value["color"])[:16]
        if "scale" in value:
            try:st["scale"]=max(1,min(3,int(value["scale"])))
            except (TypeError,ValueError):pass
        mode=str(value.get("audio_reactivity",st.get("audio_reactivity","Off")))
        if mode=="Intense":mode="Reactive"
        if mode not in ("Off","Subtle","Reactive"):mode="Off"
        st.update(motion="Static",speed=34.0,glow=False,wave=False,glitch=False,beat_pulse=False,audio_reactivity=mode,background="Dimmed GIF",background_brightness=.30,backplate=True)

def show_text(value=None):
    if isinstance(value,dict):set_text_settings(value)
    for s in target_sides():
        set_icon_enabled(s,False,False)
        panels[s]["text"]["enabled"]=True

def hide_text():
    for s in target_sides():panels[s]["text"]["enabled"]=False

def refresh_text(value=None):
    if isinstance(value,dict):set_text_settings(value)

def trigger_guest(value): chaos_engine.trigger(value)
def update_guest_xy(value): chaos_engine.update_xy(value)
def stop_guest(): chaos_engine.stop()

def command(data):
    c,v=data.get("command"),data.get("value")
    if c=="set_target":set_target(v);return
    if c=="effect":set_effect(v);return
    if c=="select_image":select_image(v);return
    if c=="filtered_step":step_filtered(v);return
    if c=="pixel_melt_next":pixel_melt_next(v);return
    if c=="intense_transition_next":intense_transition_next(v);return
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
    if c=="icon_toggle":toggle_icon(str(v));return
    if c=="icon_clear":clear_icon();return
    if c=="icon_motion":set_icon_motion(str(v));return
    if c in ("icon_position","icon_center","icon_transition_settings"):return
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
    if c=="guest_lock":chaos_engine.set_locked(v);return
    if c in ("mode_prev","mode_next"):
        a=reference_asset()
        if a:
            try:i=MODES.index(a.settings.mode)
            except ValueError:i=0
            a.settings.mode=MODES[(i+(-1 if c=="mode_prev" else 1))%len(MODES)];save_asset(a)
        return
    a=reference_asset()
    if c=="toggle_favorite":
        if a:library.set_favorite(a,not bool(metadata(a).get("favorite",False)));invalidate_library_state()
        return
    if c=="set_favorite_index" and isinstance(v,dict):
        try:t=library.get(int(v.get("index")))
        except Exception:t=None
        if t:library.set_favorite(t,bool(v.get("favorite",False)));invalidate_library_state()
        return
    if c=="set_tags":
        if a and isinstance(v,list):library.set_tags(a,list(dict.fromkeys(str(x).strip() for x in v if str(x).strip())));invalidate_library_state()
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
    out={"effect":ctl.effect_name,"speed":ctl.speed,"brightness":ctl.brightness,"paused":ctl.paused,"image_index_zero":panels[side]["image_index"],"image_index":0,"image_name":None,"image_mode":None,"image_settings":None,"image_tags":[],"image_favorite":False,"slideshow":{"active":sh["active"],"duration":sh["duration"],"shuffle":sh["shuffle"],"label":sh["label"],"count":len(sh["indices"]),"beat_sync":sh.get("beat_sync",False)},"reactive":{"enabled":r["enabled"],"strength":r["strength"],"preset":r["preset"],"layers":dict(r["layers"])},"transition":dict(tr),"text":dict(panels[side]["text"]),"icon":dict(panels[side]["icon"])}
    if a:
        m=metadata(a);out.update(image_index=panels[side]["image_index"]+1,image_name=a.path.name,image_mode=a.settings.mode,image_settings=a.settings.to_dict(),image_tags=m.get("tags",[]),image_favorite=bool(m.get("favorite",False)))
    return out

def update_phone():
    ref=phone_panel(reference_side())
    server.update_state({"target":active_target,"reference_side":reference_side(),"image_count":len(library),"library":library_state(),"effects":list(controllers["front"].effects),"panels":{"front":phone_panel("front"),"back":phone_panel("back")},"audio":{"volume":audio["volume"],"bass":audio["bass"],"mids":audio["mids"],"highs":audio["highs"],"beat":audio["beat"],"fresh":audio_fresh()},"motion":dict(motion),"reactive_presets":REACTIVE_PRESETS,"layer_keys":LAYER_KEYS,"transitions":TRANSITIONS,"performance_scenes":list(SCENES),"current_scene":current_scene,"text_fonts":TEXT_FONTS,"text_motions":TEXT_MOTIONS,"text_color_modes":TEXT_COLORS,"text_effects":TEXT_EFFECTS,"text_backgrounds":TEXT_BACKGROUNDS,"overlay_icons":ICON_LIBRARY.names(),"icon_library_errors":list(ICON_LIBRARY.errors),"icon_motions":list(ICON_MOTIONS),"guest":chaos_engine.snapshot(),**ref})

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

update_phone();running=True;frame_number=0;last_phone_update=time.monotonic()
while running:
    dt=clock.tick(60)/1000;frame_number+=1
    for e in pygame.event.get():
        if e.type==pygame.QUIT:running=False
        elif e.type==pygame.KEYDOWN:running=keys(e.key)
    for data in server.get_commands():command(data)
    for s in SIDES:
        controllers[s].update(dt)
        if not controllers[s].paused:particles[s].update(dt)
        content_transitions[s].update(dt)
        scene_transitions[s].update(dt)
    update_shows(dt);update_icon_transitions();chaos_engine.update()
    sig=signals()
    for s in SIDES:
        controllers[s].effect(displays[s],controllers[s].time)

        # Content transitions affect only the GIF/effect beneath audio and overlays.
        content_transitions[s].apply(displays[s])
        content_snapshots[s]=copy_pixels(displays[s])

        r=panels[s]["reactive"]
        if r["enabled"]:layer_engine.apply(displays[s],sig,r["layers"],r["strength"],frame_number,1000 if s=="back" else 0)

        st=panels[s]["text"]
        icon=panels[s]["icon"]
        text_enabled=bool(st.get("enabled",False))
        if text_enabled:
            overlay_engine.draw_text(displays[s],st,controllers[s].time,sig,1000 if s=="back" else 0,bottom=bool(icon.get("icon_enabled")))
        icon_settings=dict(st);icon_settings["audio_reactivity"]="Off"
        overlay_engine.draw_icon(displays[s],icon,icon_settings,controllers[s].time,sig,1000 if s=="back" else 0,text_enabled=text_enabled)

        # Full-scene transitions intentionally move GIF + reactive layers + overlays.
        scene_transitions[s].apply(displays[s])
        scene_snapshots[s]=copy_pixels(displays[s])

        # Chaos is an explicit final-frame performance stage.
        chaos_engine.apply(displays[s],frame_number+(1000 if s=="back" else 0),sig)
    signal_store.end_frame()
    screen.fill((15,15,18));draw_panel("front",0);draw_panel("back",PW+GAP);draw_ui()
    now=time.monotonic()
    if now-last_phone_update>=PHONE_STATE_INTERVAL:
        update_phone();last_phone_update=now
    pygame.display.flip()
server.stop();pygame.quit()