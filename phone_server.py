import json, socket, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue, Empty

PHONE_HTML=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>Festival Totem</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;padding:14px;background:radial-gradient(circle at top,#2a2140,#111118 40%,#09090d);color:#fff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.page{max-width:680px;margin:auto;padding-bottom:25px}h1{margin:4px 0}.muted{opacity:.62;font-size:13px}.tabs,.target,.g2,.g3{display:grid;gap:8px}.tabs,.target,.g3{grid-template-columns:repeat(3,1fr)}.g2{grid-template-columns:repeat(2,1fr)}.tabs{position:sticky;top:0;z-index:20;padding:8px 0;background:#09090def;backdrop-filter:blur(10px)}button{border:0;border-radius:12px;min-height:45px;padding:9px;background:#343442;color:#fff;font-weight:650}button.active{background:#7063d7}.warn{background:#663640}.card{background:#ffffff12;border:1px solid #ffffff16;border-radius:17px;padding:14px;margin:12px 0}.card h2{margin:0 0 10px;font-size:18px}.view{display:none}.view.active{display:block}.now{font-size:20px;font-weight:750}.row{display:flex;justify-content:space-between;align-items:center;gap:10px}.slider{margin:13px 0}.sh{display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px}.value{opacity:.65}input[type=range]{width:100%}.filters{display:flex;gap:7px;overflow-x:auto;padding:3px 0 11px}.filter{flex:0 0 auto;min-height:36px;border-radius:999px;padding:6px 12px;font-size:13px}.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.tile{position:relative;padding:0;aspect-ratio:1;border:2px solid transparent;overflow:hidden}.tile.selected{border-color:#8b7cff}.tile img{width:100%;height:100%;object-fit:cover;image-rendering:pixelated}.name{position:absolute;left:0;right:0;bottom:0;padding:18px 5px 5px;background:linear-gradient(transparent,#000e);font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left}.star{position:absolute;right:4px;top:4px;width:29px;height:29px;min-height:0;padding:0;border-radius:50%;background:#000a;z-index:2}.badge{position:absolute;left:5px;top:5px;background:#0009;border-radius:7px;padding:2px 5px;font-size:9px}.tags{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.pill{min-height:31px;border-radius:999px;padding:5px 10px;font-size:12px}.tagadd{display:flex;gap:7px}.tagadd input{flex:1;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:10px;font-size:16px}.empty{grid-column:1/-1;text-align:center;opacity:.55;padding:22px}@media(min-width:560px){.gallery{grid-template-columns:repeat(4,1fr)}}
</style></head><body><div class="page"><h1>Festival Totem</h1><div class="muted">● Live controller</div>
<div class="tabs"><button id="tabLive" class="active" onclick="view('live')">Live</button><button id="tabLibrary" onclick="view('library')">Library</button><button id="tabEdit" onclick="view('edit')">Edit</button></div>
<div class="card"><h2>Target</h2><div class="target"><button data-target="front" onclick="cmd('set_target','front')">Front</button><button data-target="both" onclick="cmd('set_target','both')">Both</button><button data-target="back" onclick="cmd('set_target','back')">Back</button></div></div>

<section id="live" class="view active">
<div class="card"><div class="row"><h2>Now Playing</h2><button id="fav" onclick="cmd('toggle_favorite')">☆</button></div><div class="now" id="now">Connecting...</div><div class="muted" id="info"></div><div class="muted" id="summary"></div><div class="muted" id="show"></div></div>
<div class="card"><h2>Effects</h2><div class="g3" id="effects"></div></div>
<div class="card"><h2>Playback</h2><div class="slider"><div class="sh"><span>Brightness</span><span id="bv" class="value"></span></div><input id="brightness" type="range" min=".1" max="1" step=".05" oninput="pct('bv',this.value);range('brightness',this.value)"></div><div class="slider"><div class="sh"><span>Speed</span><span id="sv" class="value"></span></div><input id="speed" type="range" min=".1" max="5" step=".1" oninput="num('sv',this.value,'x');range('speed',this.value)"></div><div class="g2"><button id="pause" onclick="cmd('toggle_pause')">Pause</button><button onclick="cmd('reload_library')">Reload Library</button></div></div>
<div class="card"><h2>Slideshow</h2><div class="muted" id="selection"></div><div class="slider"><div class="sh"><span>Seconds per item</span><span id="dv" class="value">5s</span></div><input id="duration" type="range" min="1" max="30" value="5" oninput="dv.textContent=this.value+'s'"></div><div class="g3"><button onclick="start(false)">Play</button><button onclick="start(true)">Shuffle</button><button class="warn" onclick="cmd('slideshow_stop')">Stop</button></div><div class="g2" style="margin-top:8px"><button onclick="step(-1)">◀ Previous</button><button onclick="step(1)">Next ▶</button></div></div>
</section>

<section id="library" class="view"><div class="card"><div class="row"><h2>Library</h2><div id="count" class="muted"></div></div><div id="filters" class="filters"></div><div id="gallery" class="gallery"></div></div></section>

<section id="edit" class="view">
<div class="card"><h2>Selected Asset</h2><div id="editname" class="now"></div><div id="mode" class="muted"></div><div id="tags" class="tags"></div><div class="tagadd"><input id="taginput" placeholder="Add a tag"><button onclick="addTag()">Add</button></div></div>
<div class="card"><h2>Framing</h2><div class="g2"><button onclick="cmd('mode_prev')">◀ Mode</button><button onclick="cmd('mode_next')">Mode ▶</button></div><div class="slider"><div class="sh"><span>Zoom</span><span id="zv"></span></div><input id="zoom" type="range" min="1" max="5" step=".05" oninput="num('zv',this.value,'x');range('zoom',this.value)"></div><div class="slider"><div class="sh"><span>Crop X</span><span id="cxv"></span></div><input id="cropX" type="range" min="0" max="1" step=".01" oninput="pct('cxv',this.value);range('crop_x',this.value)"></div><div class="slider"><div class="sh"><span>Crop Y</span><span id="cyv"></span></div><input id="cropY" type="range" min="0" max="1" step=".01" oninput="pct('cyv',this.value);range('crop_y',this.value)"></div></div>
<div class="card"><h2>Processing</h2><div class="slider"><div class="sh"><span>Contrast</span><span id="cv"></span></div><input id="contrast" type="range" min=".25" max="3" step=".05" oninput="num('cv',this.value,'');range('contrast',this.value)"></div><div class="slider"><div class="sh"><span>Saturation</span><span id="satv"></span></div><input id="saturation" type="range" min="0" max="3" step=".05" oninput="num('satv',this.value,'');range('saturation',this.value)"></div><div class="slider"><div class="sh"><span>Gamma</span><span id="gv"></span></div><input id="gamma" type="range" min=".25" max="3" step=".05" oninput="num('gv',this.value,'');range('gamma',this.value)"></div><div class="g2"><button id="sharp" onclick="cmd('toggle_sharpen')">Sharpen</button><button id="dither" onclick="cmd('toggle_dither')">Dither</button></div><button class="warn" style="width:100%;margin-top:8px" onclick="if(confirm('Reset this image?'))cmd('reset_image')">Reset Image</button></div>
</section></div>
<script>
let state={},filter="All",gs="",fs="",timers={};
function view(n){["live","library","edit"].forEach(x=>{document.getElementById(x).classList.toggle("active",x===n);document.getElementById("tab"+x[0].toUpperCase()+x.slice(1)).classList.toggle("active",x===n)})}
async function cmd(command,value=null){try{await fetch("/api/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command,value})})}catch(e){}}
function range(n,v){clearTimeout(timers[n]);timers[n]=setTimeout(()=>cmd(n,parseFloat(v)),70)}
function pct(id,v){document.getElementById(id).textContent=Math.round(v*100)+"%"}function num(id,v,s){document.getElementById(id).textContent=parseFloat(v).toFixed(2)+s}
function sync(id,v){let e=document.getElementById(id);if(document.activeElement!==e&&v!=null)e.value=v}
function tagsAll(lib){let s=new Set;lib.forEach(i=>(i.tags||[]).forEach(t=>s.add(t)));return [...s].sort()}
function visible(){let l=state.library||[];if(filter==="All")return l;if(filter==="Favorites")return l.filter(x=>x.favorite);return l.filter(x=>(x.tags||[]).includes(filter))}
function renderFilters(){let names=["All","Favorites",...tagsAll(state.library||[])],sig=JSON.stringify(names);if(sig===fs){selectFilter();return}fs=sig;filters.innerHTML="";names.forEach(n=>{let b=document.createElement("button");b.className="filter";b.dataset.f=n;b.textContent=n;b.onclick=()=>{filter=n;gs="";selectFilter();galleryRender();selection.textContent="Selection: "+filter+" ("+visible().length+" items)"};filters.appendChild(b)});selectFilter()}
function selectFilter(){document.querySelectorAll(".filter").forEach(b=>b.classList.toggle("active",b.dataset.f===filter))}
function galleryRender(){let v=visible(),sig=JSON.stringify([filter,v.map(x=>[x.index,x.name,x.favorite,x.tags])]);if(sig===gs){selectTiles();return}gs=sig;gallery.innerHTML="";if(!v.length){gallery.innerHTML='<div class="empty">Nothing in this filter yet.</div>'}v.forEach(i=>{let t=document.createElement("button");t.className="tile";t.dataset.index=i.index;t.onclick=()=>{cmd("select_image",i.index);view("live")};let im=document.createElement("img");im.src="/thumb/"+i.index;let b=document.createElement("div");b.className="badge";b.textContent=i.index+1;let st=document.createElement("button");st.className="star";st.textContent=i.favorite?"★":"☆";st.onclick=e=>{e.stopPropagation();cmd("set_favorite_index",{index:i.index,favorite:!i.favorite})};let n=document.createElement("div");n.className="name";n.textContent=i.name;t.append(im,b,st,n);gallery.appendChild(t)});count.textContent=v.length+" / "+(state.library||[]).length;selectTiles()}
function selectTiles(){let p=state.panels||{},sel=new Set;if(state.target!=="back")sel.add(p.front?.image_index_zero);if(state.target!=="front")sel.add(p.back?.image_index_zero);document.querySelectorAll(".tile").forEach(t=>t.classList.toggle("selected",sel.has(parseInt(t.dataset.index))))}
function start(shuffle){let ids=visible().map(x=>x.index);if(ids.length)cmd("slideshow_start",{indices:ids,duration:parseFloat(duration.value),shuffle,label:filter})}
function step(delta){let ids=visible().map(x=>x.index);if(ids.length)cmd("filtered_step",{indices:ids,delta})}
function addTag(){let v=taginput.value.trim();if(!v)return;let a=[...(state.image_tags||[])];if(!a.includes(v))a.push(v);cmd("set_tags",a);taginput.value=""}
function tagRender(){tags.innerHTML="";let a=state.image_tags||[];if(!a.length){tags.innerHTML='<span class="muted">No tags yet</span>';return}a.forEach(t=>{let b=document.createElement("button");b.className="pill";b.textContent=t+" ×";b.onclick=()=>cmd("set_tags",a.filter(x=>x!==t));tags.appendChild(b)})}
function effectRender(){let a=state.effects||[],sig=a.join("|");if(effects.dataset.sig!==sig){effects.dataset.sig=sig;effects.innerHTML="";a.forEach(x=>{let b=document.createElement("button");b.dataset.effect=x;b.textContent=x;b.onclick=()=>cmd("effect",x);effects.appendChild(b)})}let p=state.panels||{};document.querySelectorAll("[data-effect]").forEach(b=>{let on=state.target==="front"?p.front?.effect===b.dataset.effect:state.target==="back"?p.back?.effect===b.dataset.effect:p.front?.effect===b.dataset.effect&&p.back?.effect===b.dataset.effect;b.classList.toggle("active",on)})}
async function update(){try{let r=await fetch("/api/state",{cache:"no-store"});state=await r.json();document.querySelectorAll("[data-target]").forEach(b=>b.classList.toggle("active",b.dataset.target===state.target));effectRender();let p=state.panels||{},f=p.front||{},b=p.back||{};now.textContent=state.target==="both"?"Front: "+(f.effect||"-")+" • Back: "+(b.effect||"-"):state.effect||"-";info.textContent=state.image_name?(state.image_index+" / "+state.image_count+" • "+state.image_name):"No image selected";summary.textContent="Front: "+(f.image_name||f.effect||"-")+" | Back: "+(b.image_name||b.effect||"-");let sl=state.slideshow||{};show.textContent=sl.active?"Slideshow: "+sl.label+" • "+sl.count+" items • "+sl.duration+"s":"Slideshow: Off";fav.textContent=state.image_favorite?"★":"☆";sync("brightness",state.brightness);pct("bv",state.brightness);sync("speed",state.speed);num("sv",state.speed,"x");pause.textContent=state.paused?"Resume":"Pause";editname.textContent=state.image_name||"None";mode.textContent=state.image_mode?"Mode: "+state.image_mode+" • editing "+state.reference_side:"";tagRender();if(state.image_settings){let s=state.image_settings;sync("zoom",s.zoom);num("zv",s.zoom,"x");sync("cropX",s.crop_x);pct("cxv",s.crop_x);sync("cropY",s.crop_y);pct("cyv",s.crop_y);sync("contrast",s.contrast);num("cv",s.contrast,"");sync("saturation",s.saturation);num("satv",s.saturation,"");sync("gamma",s.gamma);num("gv",s.gamma,"");sharp.classList.toggle("active",s.sharpen);dither.classList.toggle("active",s.dither)}renderFilters();galleryRender();selection.textContent="Selection: "+filter+" ("+visible().length+" items)"}catch(e){now.textContent="Disconnected"}}
update();setInterval(update,300);
</script></body></html>'''

class PhoneControlServer:
    def __init__(self,port=8765):
        self.port=port;self.commands=Queue();self.state_lock=threading.Lock();self.state={};self.thumbnail_provider=None;self.server=None
    def update_state(self,state):
        with self.state_lock:self.state=dict(state)
    def get_state(self):
        with self.state_lock:return dict(self.state)
    def set_thumbnail_provider(self,provider):self.thumbnail_provider=provider
    def add_command(self,command,value=None):self.commands.put({"command":command,"value":value})
    def get_commands(self):
        out=[]
        while True:
            try:out.append(self.commands.get_nowait())
            except Empty:return out
    def get_local_ip(self):
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:s.connect(("8.8.8.8",80));return s.getsockname()[0]
        except Exception:
            try:return socket.gethostbyname(socket.gethostname())
            except Exception:return "127.0.0.1"
        finally:s.close()
    def start(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):return
            def send_bytes(self,data,ctype,status=200):
                self.send_response(status);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
            def do_GET(self):
                if self.path=="/":self.send_bytes(PHONE_HTML.encode(),"text/html; charset=utf-8");return
                if self.path=="/api/state":self.send_bytes(json.dumps(owner.get_state()).encode(),"application/json");return
                if self.path.startswith("/thumb/"):
                    try:
                        i=int(self.path.split("?",1)[0].split("/")[-1]);data=owner.thumbnail_provider(i) if owner.thumbnail_provider else None
                        if not data:raise RuntimeError
                        self.send_bytes(data,"image/jpeg")
                    except Exception:self.send_bytes(b"","image/jpeg",404)
                    return
                self.send_bytes(b"Not Found","text/plain",404)
            def do_POST(self):
                if self.path!="/api/command":self.send_bytes(b"Not Found","text/plain",404);return
                try:
                    n=int(self.headers.get("Content-Length","0"));p=json.loads(self.rfile.read(n).decode());c=p.get("command")
                    if c:owner.add_command(c,p.get("value"))
                    self.send_bytes(b'{"ok":true}',"application/json")
                except Exception as e:self.send_bytes(json.dumps({"ok":False,"error":str(e)}).encode(),"application/json",400)
        self.server=ThreadingHTTPServer(("0.0.0.0",self.port),Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        url=f"http://{self.get_local_ip()}:{self.port}"
        print("\n========================================\nPHONE CONTROLLER READY\n========================================\nOpen on your phone:\n"+url+"\n========================================\n")
        return url
    def stop(self):
        if self.server:self.server.shutdown();self.server.server_close();self.server=None
