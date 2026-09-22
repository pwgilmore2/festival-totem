import phone_server
import image_processing_ui
import intense_transition_patch
import visual_engine

_forced_kind = None
_forced_count = 0
_base_begin = visual_engine.TransitionManager.begin
_base_get_commands = image_processing_ui.PhoneControlServer.get_commands


def arm_intense(kind, count=2):
    global _forced_kind, _forced_count
    if kind not in intense_transition_patch.INTENSE_TRANSITIONS:
        return False
    _forced_kind = kind
    _forced_count = max(1, int(count))
    return True


def _begin(self, display, kind="Fade", duration=0.8):
    global _forced_kind, _forced_count
    if kind == "Melt" and _forced_kind and _forced_count > 0:
        forced = _forced_kind
        _forced_count -= 1
        if _forced_count <= 0:
            _forced_kind = None
        return _base_begin(self, display, forced, duration)
    return _base_begin(self, display, kind, duration)


visual_engine.TransitionManager.begin = _begin


def _get_commands(self):
    out = []
    for data in _base_get_commands(self):
        if not isinstance(data, dict) or data.get("command") != "intense_transition_next":
            out.append(data)
            continue
        value = data.get("value") or {}
        if not isinstance(value, dict):
            continue
        kind = str(value.get("kind", "Morph"))
        try:
            duration = max(.25, min(4.0, float(value.get("duration", 1.15))))
        except (TypeError, ValueError):
            duration = 1.15
        indices = value.get("indices", [])
        if not arm_intense(kind, 2):
            continue
        # Reuse the proven Pixel Melt -> next path so slideshow position/timing remains intact.
        out.append({"command": "set_target", "value": "both"})
        out.append({"command": "pixel_melt_next", "value": {"indices": indices, "duration": duration}})
    return out


image_processing_ui.PhoneControlServer.get_commands = _get_commands

_CSS = r'''
<style>
.intenseGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}
.intenseGrid button{min-height:76px;font-size:15px;touch-action:pan-y;-webkit-user-select:none;user-select:none;background:linear-gradient(145deg,#52165f,#a71967 52%,#ff5d33)}
.intenseGrid button.intensePending{filter:brightness(1.15)}
.intenseGrid button.intensePressed{transform:scale(.97);filter:brightness(1.35)}
.intenseHint{font-size:10px;font-weight:600;letter-spacing:0;text-transform:none;opacity:.72}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_SECTION = r'''
<div class="chaosGroup"><div class="chaosGroupLabel">Intense → Next <span class="intenseHint">deliberate hold • both panels • one-shot transition</span></div><div class="intenseGrid">
<button onpointerdown="intenseHoldStart(event,'Morph',1.35)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">🧬<br>MORPH</button>
<button onpointerdown="intenseHoldStart(event,'Spin',1.0)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">🌀<br>SPIN</button>
<button onpointerdown="intenseHoldStart(event,'Rip',1.0)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">⚡<br>RIP</button>
<button onpointerdown="intenseHoldStart(event,'Slam',.72)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">💥<br>SLAM</button>
<button onpointerdown="intenseHoldStart(event,'Bounce',.95)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">🏀<br>BOUNCE</button>
<button onpointerdown="intenseHoldStart(event,'Shatter',1.05)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">💎<br>SHATTER</button>
<button onpointerdown="intenseHoldStart(event,'Vortex',1.25)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">🕳️<br>VORTEX</button>
<button onpointerdown="intenseHoldStart(event,'Implode',1.05)" onpointermove="intenseHoldMove(event)" onpointerup="intenseHoldEnd(event)" onpointercancel="intenseHoldEnd(event)">💫<br>IMPLODE</button>
</div></div>
'''
_marker = '<div class="xyWrap">'
if _marker in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_marker, _SECTION + _marker, 1)

_JS = r'''
<script>
let intenseHold=null;
function intenseFire(kind,duration){
  const ids=(typeof visible==='function'?visible():(state.library||[])).map(x=>x.index);
  if(!ids.length)return;
  cmd('intense_transition_next',{kind,duration,indices:ids});
}
function intenseHoldStart(e,kind,duration){
  if(e.pointerType==='mouse'&&e.button!==0)return;
  const el=e.currentTarget;
  intenseHold={id:e.pointerId,kind,duration,el,x:e.clientX,y:e.clientY,timer:null,fired:false};
  el.classList.add('intensePending');
  intenseHold.timer=setTimeout(()=>{
    if(!intenseHold||intenseHold.id!==e.pointerId)return;
    intenseHold.fired=true;
    el.classList.remove('intensePending');el.classList.add('intensePressed');
    if(el.setPointerCapture)try{el.setPointerCapture(e.pointerId)}catch(_){ }
    intenseFire(kind,duration);
  },150);
}
function intenseHoldMove(e){
  if(!intenseHold||intenseHold.id!==e.pointerId||intenseHold.fired)return;
  if(Math.hypot(e.clientX-intenseHold.x,e.clientY-intenseHold.y)>11){
    clearTimeout(intenseHold.timer);intenseHold.el.classList.remove('intensePending');intenseHold=null;
  }
}
function intenseHoldEnd(e){
  if(!intenseHold||intenseHold.id!==e.pointerId)return;
  clearTimeout(intenseHold.timer);intenseHold.el.classList.remove('intensePending','intensePressed');intenseHold=null;
}
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
