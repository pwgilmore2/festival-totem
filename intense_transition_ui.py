import phone_server
import controller_state_ui
import intense_transition_patch  # noqa: F401

INTENSE = list(intense_transition_patch.INTENSE_TRANSITIONS)

_CSS = r'''
<style>
.intenseGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:9px}
.intenseGrid button{min-height:74px;font-size:15px;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.intenseGrid button.holdPending{filter:brightness(1.12)}
.intenseGrid button.pressed{transform:scale(.97);filter:brightness(1.3)}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_anchor = '<div class="chaosGroup"><div class="chaosGroupLabel">Chill / Flow'
if _anchor in phone_server.PHONE_HTML and 'id="intenseTransitionGrid"' not in phone_server.PHONE_HTML:
    block = r'''<div class="chaosGroup"><div class="chaosGroupLabel">Intense → Next <span class="chaosGroupHint">one-shot transition to the next GIF</span></div><div id="intenseTransitionGrid" class="intenseGrid"></div></div>
'''
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_anchor, block + _anchor, 1)

_JS = r'''
<script>
const intenseTransitionNames=['Morph','Spin','Rip','Slam','Bounce','Shatter','Vortex','Implode'];
(function buildIntenseTransitions(){
  const grid=document.getElementById('intenseTransitionGrid');if(!grid)return;
  const icons={Morph:'🧬',Spin:'🌀',Rip:'⚡',Slam:'💥',Bounce:'↔️',Shatter:'💎',Vortex:'🌪️',Implode:'⚫'};
  grid.innerHTML='';
  intenseTransitionNames.forEach(name=>{
    const b=document.createElement('button');
    b.innerHTML=(icons[name]||'✨')+'<br>'+name.toUpperCase();
    b.onpointerdown=e=>intenseHoldStart(e,name);
    b.onpointermove=intenseHoldMove;
    b.onpointerup=intenseHoldEnd;
    b.onpointercancel=intenseHoldEnd;
    grid.appendChild(b);
  });
})();
let intenseHold=null;
function intenseHoldStart(e,name){
  if(e.pointerType==='mouse'&&e.button!==0)return;
  const el=e.currentTarget;
  intenseHold={id:e.pointerId,name,el,x:e.clientX,y:e.clientY,fired:false,timer:null};
  el.classList.add('holdPending');
  intenseHold.timer=setTimeout(()=>{
    if(!intenseHold||intenseHold.id!==e.pointerId)return;
    intenseHold.fired=true;el.classList.remove('holdPending');el.classList.add('pressed');
    const ids=(typeof visible==='function'?visible():(state.library||[])).map(x=>x.index);
    if(ids.length)cmd('intense_transition_next',{kind:name,indices:ids,duration:1.15});
  },130);
}
function intenseHoldMove(e){
  if(!intenseHold||intenseHold.id!==e.pointerId||intenseHold.fired)return;
  if(Math.hypot(e.clientX-intenseHold.x,e.clientY-intenseHold.y)>11){clearTimeout(intenseHold.timer);intenseHold.el.classList.remove('holdPending');intenseHold=null}
}
function intenseHoldEnd(e){
  if(!intenseHold||intenseHold.id!==e.pointerId)return;
  clearTimeout(intenseHold.timer);intenseHold.el.classList.remove('holdPending','pressed');intenseHold=null;
}
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)

# Route one-shot intense commands explicitly. The simulator now owns transition
# scope, so no TransitionManager monkeypatch or disguised Melt command is needed.
_base_get_commands = controller_state_ui.PhoneControlServer.get_commands

def _get_commands(self):
    out=[]
    for data in _base_get_commands(self):
        if not isinstance(data, dict) or data.get('command') != 'intense_transition_next':
            out.append(data);continue
        value=data.get('value') if isinstance(data.get('value'),dict) else {}
        kind=str(value.get('kind','Morph'))
        if kind not in INTENSE: kind='Morph'
        try:
            duration=max(.25,min(4.0,float(value.get('duration',1.15))))
        except (TypeError,ValueError):
            duration=1.15
        out.append({'command':'set_target','value':'both'})
        out.append({'command':'pixel_melt_next','value':{
            'indices':value.get('indices',[]),
            'duration':duration,
            'kind':kind,
        }})
    return out

controller_state_ui.PhoneControlServer.get_commands = _get_commands
