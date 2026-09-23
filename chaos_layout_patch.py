"""Presentation transform for the live Chaos instrument layout."""

_CSS = r'''
<style>
.chaosCard{padding-top:10px}
.chaosGroup{margin:4px 0 18px}
.chaosGroupLabel{display:flex;align-items:center;gap:9px;margin:2px 2px 9px;font-size:12px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;opacity:.78}
.chaosGroupLabel:after{content:'';height:1px;flex:1;background:#ffffff20}
.chaosGroupHint{font-size:10px;font-weight:600;letter-spacing:0;text-transform:none;opacity:.7}
.chaosFxGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}
.chaosFxGrid button{min-height:94px;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.chaosFxGrid button.holdPending{filter:brightness(1.12)}
.chaosFxGrid button.pressed{transform:scale(.97);filter:brightness(1.3)}
.xyWrap{margin-top:4px;padding-top:3px;border-top:1px solid #ffffff14}.xyPad{position:relative}.xyLabel{position:absolute;z-index:2;font-size:10px;font-weight:850;letter-spacing:.08em;opacity:.62;pointer-events:none;text-shadow:0 1px 4px #000}.xyTop{top:7px;left:50%;transform:translateX(-50%)}.xyBottom{bottom:7px;left:50%;transform:translateX(-50%)}.xyLeft{left:8px;top:50%;transform:translateY(-50%) rotate(-90deg)}.xyRight{right:8px;top:50%;transform:translateY(-50%) rotate(90deg)}
@media(max-width:520px){.chaosFxGrid button{min-height:88px}}
</style>
'''

_SECTION = r'''<section id="guest" class="view"><div class="card chaosCard">
<div class="chaosGroup"><div class="chaosGroupLabel">Heavy / Impact <span class="chaosGroupHint">drops, hits, breakdown carnage</span></div><div class="chaosFxGrid">
<button class="fxChaos" onpointerdown="safeHoldStart(event,'chaos')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">💀<br>CHAOS</button>
<button class="fxGlitch" onpointerdown="safeHoldStart(event,'glitch')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">⚡<br>GLITCH</button>
<button class="fxJumble" onpointerdown="safeHoldStart(event,'jumble')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🧩<br>JUMBLE</button>
<button class="fxPixelMelt" onpointerdown="safeHoldStart(event,'pixelmelt')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🔥<br>PIXEL MELT → NEXT</button>
<button class="fxMelt" onpointerdown="safeHoldStart(event,'meltdown')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🫠<br>MELT / REBUILD</button>
</div></div>
<div class="chaosGroup"><div class="chaosGroupLabel">Chill / Flow <span class="chaosGroupHint">slow builds, color drift, gentle warps</span></div><div class="chaosFxGrid">
<button class="fxTrance" onpointerdown="safeHoldStart(event,'trance')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🌊<br>TRANCE</button>
<button class="fxLiquid" onpointerdown="safeHoldStart(event,'liquid')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">💧<br>LIQUID</button>
<button class="fxRainbow" onpointerdown="safeHoldStart(event,'rainbow')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🌈<br>RAINBOW</button>
<button class="fxPrism" onpointerdown="safeHoldStart(event,'prism')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🔮<br>PRISM</button>
<button class="fxWarp" onpointerdown="safeHoldStart(event,'warp')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🌀<br>WARP</button>
<button class="fxTunnel" onpointerdown="safeHoldStart(event,'tunnel')" onpointermove="safeHoldMove(event)" onpointerup="safeHoldEnd(event)" onpointercancel="safeHoldEnd(event)">🕳️<br>TUNNEL</button>
</div></div>
<div class="xyWrap"><div class="sh"><span>TRUE CHAOS PAD</span><span class="tiny">center = calm • push toward an effect</span></div><div id="chaosXY" class="xyPad" onpointerdown="xyStart(event)" onpointermove="xyMove(event)" onpointerup="xyEnd(event)" onpointercancel="xyEnd(event)"><span class="xyLabel xyTop">ZOOM</span><span class="xyLabel xyBottom">SHAKE</span><span class="xyLabel xyLeft">GLITCH</span><span class="xyLabel xyRight">RGB</span><div id="xyDot" class="xyDot"></div></div></div>
<div class="guestIntensity slider"><div class="sh"><span>Chaos intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div>
</div></section>'''

_JS = r'''
<script>
let safeHold=null;
async function pixelMeltNext(){
  await cmd('set_target','both');
  const ids=(typeof visible==='function'?visible():(state.library||[])).map(x=>x.index);
  if(!ids.length)return;
  await cmd('pixel_melt_next',{indices:ids,duration:1.8});
}
function safeHoldStart(e,kind){
  if(e.pointerType==='mouse'&&e.button!==0)return;
  const el=e.currentTarget;
  safeHold={id:e.pointerId,kind,el,x:e.clientX,y:e.clientY,fired:false,oneShot:false,timer:null};
  el.classList.add('holdPending');
  safeHold.timer=setTimeout(()=>{
    if(!safeHold||safeHold.id!==e.pointerId)return;
    safeHold.fired=true;el.classList.remove('holdPending');el.classList.add('pressed');
    if(el.setPointerCapture)try{el.setPointerCapture(e.pointerId)}catch(_){ }
    if(kind==='pixelmelt'){
      safeHold.oneShot=true;
      pixelMeltNext();
    }else{
      cmd('guest_action',{kind,strength:parseFloat(guestIntensity.value),duration:30});
    }
  },130);
}
function safeHoldMove(e){
  if(!safeHold||safeHold.id!==e.pointerId||safeHold.fired)return;
  if(Math.hypot(e.clientX-safeHold.x,e.clientY-safeHold.y)>11){
    clearTimeout(safeHold.timer);safeHold.el.classList.remove('holdPending');safeHold=null;
  }
}
function safeHoldEnd(e){
  if(!safeHold||safeHold.id!==e.pointerId)return;
  clearTimeout(safeHold.timer);let fired=safeHold.fired,oneShot=safeHold.oneShot,el=safeHold.el;
  el.classList.remove('holdPending','pressed');safeHold=null;
  if(fired&&!oneShot)cmd('guest_stop');
}
</script>
'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    start = html.find('<section id="guest" class="view">')
    end = html.find('</section>', start)
    if start >= 0 and end >= 0:
        end += len('</section>')
        html = html[:start] + _SECTION + html[end:]
    html = html.replace('</body>', _JS + '</body>', 1)
    return html
