import io, random, pygame
from PIL import Image
from display import VirtualDisplay
from effects import EFFECTS, hsv_to_rgb
from controller import TotemController
from text import draw_scrolling_text
from particles import ParticleSystem
from image_assets import ImageLibrary
from phone_server import PhoneControlServer

W,H,S,GAP,UI = 64,32,8,24,150
PW,PH = W*S,H*S
pygame.init()
screen=pygame.display.set_mode((PW*2+GAP,PH+UI))
pygame.display.set_caption("Festival Totem Simulator")
clock=pygame.time.Clock()
font=pygame.font.SysFont(None,22)

library=ImageLibrary("assets/images",W,H)
displays={"front":VirtualDisplay(W,H),"back":VirtualDisplay(W,H)}
particles={side:ParticleSystem(W,H,count=60) for side in ("front","back")}
MODES=["crop","fit","pixel","optimize","dither"]
active_target="both"

def slideshow_state():
    return {"active":False,"indices":[],"position":0,"duration":5.0,"elapsed":0.0,"shuffle":False,"label":"All"}

panels={side:{"image_index":0,"slideshow":slideshow_state()} for side in ("front","back")}

def metadata(asset):
    return library.metadata_entry(asset.path.name) if asset else {"tags":[],"favorite":False}

def asset(side):
    return library.get(panels[side]["image_index"]) if len(library) else None

def sides():
    return ["front","back"] if active_target=="both" else [active_target]

def ref_side():
    return "back" if active_target=="back" else "front"

def ref_asset():
    return asset(ref_side())

def save_asset(a):
    if not a:return
    a.settings.clamp();a.clear_cache();library.save_asset(a)

def text_fx(display,t):
    draw_scrolling_text(display,"FESTIVAL MODE",t,color=hsv_to_rgb((t*80)%360),scale=1,speed=12)

def party_fx(side,display,t):
    EFFECTS["Plasma"](display,t);particles[side].draw(display)

def image_fx(side,display,t):
    a=asset(side)
    if a:a.render(display,t,a.settings)
    else:display.clear()

def make_effects(side):
    return {**EFFECTS,"Text":text_fx,
            "Party":lambda d,t,s=side:party_fx(s,d,t),
            "Image":lambda d,t,s=side:image_fx(s,d,t)}

controllers={side:TotemController(make_effects(side)) for side in ("front","back")}

def stop_show(side):
    sh=panels[side]["slideshow"];sh["active"]=False;sh["elapsed"]=0.0

def select_for_side(side,index,stop=True):
    if not len(library):return
    try:index=int(index)
    except (TypeError,ValueError):return
    panels[side]["image_index"]=max(0,min(len(library)-1,index))
    if stop:stop_show(side)
    controllers[side].set_effect("Image")

def select_image(index):
    for side in sides():select_for_side(side,index)

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
    for side in sides():
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
    for side in sides():
        panels[side]["slideshow"].update(active=True,indices=list(order),position=0,duration=duration,elapsed=0.0,shuffle=shuffle,label=label)
        select_for_side(side,order[0],stop=False)

def update_shows(dt):
    for side in ("front","back"):
        sh=panels[side]["slideshow"]
        if not sh["active"] or not sh["indices"]:continue
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
    except Exception as e:
        print("Thumbnail error:",e);return None

server=PhoneControlServer(8765);server.set_thumbnail_provider(thumbnail);phone_url=server.start()

def set_target(v):
    global active_target
    if v in ("front","back","both"):active_target=v

def set_effect(v):
    for side in sides():
        if v in controllers[side].effects:controllers[side].set_effect(v)

def master(attr,value,lo,hi):
    try:v=max(lo,min(hi,float(value)))
    except (TypeError,ValueError):return
    for side in sides():setattr(controllers[side],attr,v)

def toggle_pause():
    pause=not all(controllers[s].paused for s in sides())
    for s in sides():controllers[s].paused=pause

def reload_library():
    old={s:(asset(s).path.name if asset(s) else None) for s in ("front","back")}
    library.load()
    for s in ("front","back"):
        panels[s]["image_index"]=0;stop_show(s)
        if old[s]:
            for i,a in enumerate(library.assets):
                if a.path.name==old[s]:panels[s]["image_index"]=i;break

def command(data):
    c,v=data.get("command"),data.get("value")
    if c=="set_target":set_target(v);return
    if c=="effect":set_effect(v);return
    if c=="select_image":select_image(v);return
    if c=="filtered_step":step_filtered(v);return
    if c=="slideshow_start":start_show(v);return
    if c=="slideshow_stop":
        for s in sides():stop_show(s)
        return
    if c=="brightness":master("brightness",v,.1,1);return
    if c=="speed":master("speed",v,.1,5);return
    if c=="toggle_pause":toggle_pause();return
    if c=="reload_library":reload_library();return
    if c in ("mode_prev","mode_next"):
        a=ref_asset()
        if a:
            try:i=MODES.index(a.settings.mode)
            except ValueError:i=0
            a.settings.mode=MODES[(i+(-1 if c=="mode_prev" else 1))%len(MODES)];save_asset(a)
        return

    a=ref_asset()
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

    s=a.settings;changed=False
    if c in ("zoom","crop_x","crop_y","contrast","saturation","gamma"):
        try:setattr(s,c,float(v));changed=True
        except (TypeError,ValueError):pass
    elif c=="toggle_sharpen":s.sharpen=not s.sharpen;changed=True
    elif c=="toggle_dither":s.dither=not s.dither;changed=True
    elif c=="reset_image":s.reset();changed=True
    if changed:save_asset(a)

def phone_panel(side):
    ctl=controllers[side];a=asset(side);sh=panels[side]["slideshow"]
    r={"effect":ctl.effect_name,"speed":ctl.speed,"brightness":ctl.brightness,"paused":ctl.paused,
       "image_index_zero":panels[side]["image_index"],"image_index":0,"image_name":None,"image_mode":None,
       "image_settings":None,"image_tags":[],"image_favorite":False,
       "slideshow":{"active":sh["active"],"duration":sh["duration"],"shuffle":sh["shuffle"],"label":sh["label"],"count":len(sh["indices"])}}
    if a:
        m=metadata(a);r.update(image_index=panels[side]["image_index"]+1,image_name=a.path.name,image_mode=a.settings.mode,
                              image_settings=a.settings.to_dict(),image_tags=m.get("tags",[]),image_favorite=bool(m.get("favorite",False)))
    return r

def update_phone():
    lib=[]
    for i,a in enumerate(library.assets):
        m=metadata(a);lib.append({"index":i,"name":a.path.name,"tags":m.get("tags",[]),"favorite":bool(m.get("favorite",False))})
    ref=phone_panel(ref_side())
    server.update_state({"target":active_target,"reference_side":ref_side(),"image_count":len(library),"library":lib,
                         "effects":list(controllers["front"].effects),"panels":{"front":phone_panel("front"),"back":phone_panel("back")},**ref})

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

def keys(key):
    if key==pygame.K_ESCAPE:return False
    mapping={pygame.K_1:"Rainbow",pygame.K_2:"Waves",pygame.K_3:"Plasma",pygame.K_4:"Stars",pygame.K_5:"Text",pygame.K_6:"Party",pygame.K_7:"Image"}
    if key in mapping:set_effect(mapping[key])
    elif key==pygame.K_f:set_target("front")
    elif key==pygame.K_b:set_target("back")
    elif key==pygame.K_m:set_target("both")
    elif key==pygame.K_SPACE:toggle_pause()
    return True

update_phone();running=True
while running:
    dt=clock.tick(60)/1000
    for e in pygame.event.get():
        if e.type==pygame.QUIT:running=False
        elif e.type==pygame.KEYDOWN:running=keys(e.key)
    for data in server.get_commands():command(data)
    for side in ("front","back"):
        controllers[side].update(dt)
        if not controllers[side].paused:particles[side].update(dt)
    update_shows(dt)
    for side in ("front","back"):controllers[side].effect(displays[side],controllers[side].time)
    screen.fill((15,15,18));draw_panel("front",0);draw_panel("back",PW+GAP);draw_ui();update_phone();pygame.display.flip()
server.stop();pygame.quit()
