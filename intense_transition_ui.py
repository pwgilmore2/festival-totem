"""Presentation transform for deliberate full-scene transitions."""

_CSS = r'''
<style>
.intenseGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;margin-top:9px}
.intenseGrid button{min-height:74px;font-size:15px;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.intenseGrid button.holdPending{filter:brightness(1.12)}
.intenseGrid button.pressed{transform:scale(.97);filter:brightness(1.3)}
</style>
'''

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


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    anchor = '<div class="xyWrap">'
    if anchor in html and 'id="intenseTransitionGrid"' not in html:
        block = r'''<div class="chaosGroup"><div class="chaosGroupLabel">Intense → Next <span class="chaosGroupHint">one-shot transition to the next GIF</span></div><div id="intenseTransitionGrid" class="intenseGrid"></div></div>
'''
        html = html.replace(anchor, block + anchor, 1)
    html = html.replace('</body>', _JS + '</body>', 1)
    return html
