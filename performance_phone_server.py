import audio_phone_server
import phone_server

PERFORMANCE_CSS = r"""
<style>
.transitionGrid,.layerGrid,.guestGrid{display:grid;gap:8px}.transitionGrid{grid-template-columns:repeat(2,1fr)}.layerGrid{grid-template-columns:1fr 1fr}.guestGrid{grid-template-columns:repeat(2,1fr)}
.guestGrid button{min-height:68px;font-size:17px}.guestBig{grid-column:1/-1;min-height:82px!important;font-size:20px!important}.selectDark{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:11px;font-size:16px}.tiny{font-size:11px;opacity:.65}
@media(max-width:520px){.layerGrid{grid-template-columns:1fr}}
</style>
"""

TRANSITION_CARD = r"""
<div class="card"><h2>Transitions</h2>
<div class="transitionGrid"><select id="transitionKind" class="selectDark" onchange="setTransition()"></select><button id="randomTransition" onclick="toggleRandomTransition()">Random: Off</button></div>
<div class="slider"><div class="sh"><span>Transition duration</span><span id="transitionDurationValue">0.80s</span></div><input id="transitionDuration" type="range" min=".1" max="3" step=".1" value=".8" oninput="document.getElementById('transitionDurationValue').textContent=parseFloat(this.value).toFixed(1)+'s';setTransition()"></div>
<div class="tiny">Used for manual image changes, slideshow changes, and effect changes.</div>
</div>
<div class="card"><div class="row"><h2>Guest Controls</h2><button id="guestLockButton" onclick="toggleGuestLock()">Guest: On</button></div><div class="tiny">Lock this before handing someone the controller if you want the performance buttons disabled.</div></div>
"""

LAYER_CARD = r"""
<div class="card"><h2>Reactive Layers</h2><div class="tiny">Each slider maps a signal to a visual layer. Presets simply load combinations of these values.</div><div id="layerGrid" class="layerGrid"></div></div>
"""

GUEST_TAB = r"""<button id="tabGuest" onclick="view('guest')">Guest</button>"""

GUEST_SECTION = r"""
<section id="guest" class="view">
<div class="card"><h2>Performance Pad</h2><div id="guestStatus" class="muted">Temporary effects only — saved image settings stay untouched.</div>
<div class="guestGrid" style="margin-top:10px">
<button onclick="guestAction('boom')">💥 BOOM</button><button onclick="guestAction('glitch')">⚡ GLITCH</button>
<button onclick="guestAction('spark')">✨ SPARK</button><button onclick="guestAction('rainbow')">🌈 RAINBOW</button>
<button onclick="guestAction('melt')">🫠 MELT → NEXT</button><button onclick="guestAction('random')">🎲 RANDOM GIF</button>
<button onclick="guestAction('next')">➡️ NEXT GIF</button><button onclick="cmd('effect','Party')">🎉 PARTY</button>
<button class="guestBig" onpointerdown="guestHold('chaos',true)" onpointerup="guestHold('chaos',false)" onpointercancel="guestHold('chaos',false)" onpointerleave="guestHold('chaos',false)">HOLD FOR CHAOS</button>
</div>
<div class="slider"><div class="sh"><span>Guest intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div>
</div></section>
"""

PERFORMANCE_JS = r"""
const layerLabels={bass_zoom:'Bass → Zoom',beat_flash:'Beat → Flash',mids_hue:'Mids → Hue',high_sparkle:'Highs → Sparkles',volume_brightness:'Volume → Brightness',bass_shake:'Bass → Shake',high_rgb_split:'Highs → RGB Split'};
let layerSignature='';
function setTransition(){const k=document.getElementById('transitionKind').value,d=parseFloat(document.getElementById('transitionDuration').value),r=state.transition||{};cmd('transition_settings',{kind:k,duration:d,random:!!r.random})}
function toggleRandomTransition(){const r=state.transition||{};cmd('transition_settings',{random:!r.random})}
function toggleGuestLock(){const g=state.guest||{};cmd('guest_lock',!g.locked)}
function guestAction(kind){const g=state.guest||{};if(g.locked)return;cmd('guest_action',{kind,strength:parseFloat(document.getElementById('guestIntensity').value),duration:.8})}
function guestHold(kind,on){const g=state.guest||{};if(g.locked)return;if(on)cmd('guest_action',{kind,strength:parseFloat(document.getElementById('guestIntensity').value),duration:30});else cmd('guest_stop')}
function renderLayerControls(){const keys=state.layer_keys||[],sig=keys.join('|'),grid=document.getElementById('layerGrid');if(!grid)return;if(sig!==layerSignature){layerSignature=sig;grid.innerHTML='';keys.forEach(k=>{let wrap=document.createElement('div');wrap.className='slider';let head=document.createElement('div');head.className='sh';let a=document.createElement('span');a.textContent=layerLabels[k]||k;let val=document.createElement('span');val.id='lv_'+k;head.append(a,val);let input=document.createElement('input');input.type='range';input.min='0';input.max='1.5';input.step='.05';input.id='layer_'+k;input.oninput=()=>{num(val.id,input.value,'x');cmd('reactive_layer',{name:k,value:parseFloat(input.value)})};wrap.append(head,input);grid.appendChild(wrap)})}const layers=(state.reactive||{}).layers||{};keys.forEach(k=>{let e=document.getElementById('layer_'+k);if(e&&document.activeElement!==e)e.value=layers[k]??0;let v=document.getElementById('lv_'+k);if(v)v.textContent=parseFloat(layers[k]??0).toFixed(2)+'x'})}
function syncPerformanceUI(){if(typeof state==='undefined')return;renderLayerControls();let tr=state.transition||{},select=document.getElementById('transitionKind');if(select){let options=state.transitions||[],sig=options.join('|');if(select.dataset.sig!==sig){select.dataset.sig=sig;select.innerHTML='';options.forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;select.appendChild(o)})}if(document.activeElement!==select&&tr.kind)select.value=tr.kind}let td=document.getElementById('transitionDuration');if(td&&document.activeElement!==td&&tr.duration!=null)td.value=tr.duration;let tv=document.getElementById('transitionDurationValue');if(tv&&tr.duration!=null)tv.textContent=parseFloat(tr.duration).toFixed(1)+'s';let rb=document.getElementById('randomTransition');if(rb){rb.textContent='Random: '+(tr.random?'On':'Off');rb.classList.toggle('active',!!tr.random)}let g=state.guest||{},gb=document.getElementById('guestLockButton'),gs=document.getElementById('guestStatus');if(gb){gb.textContent=g.locked?'Guest: Locked':'Guest: On';gb.classList.toggle('warn',!!g.locked)}if(gs)gs.textContent=g.locked?'Guest controls are locked by owner.':'Temporary effects only — saved image settings stay untouched.'}
setInterval(syncPerformanceUI,300);
"""


def enhanced_html(source):
    html=source.replace("</head>",PERFORMANCE_CSS+"\n</head>",1)
    html=html.replace('<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',GUEST_TAB+'<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',1)
    html=html.replace('["live","library","audio","edit"]','["live","library","audio","guest","edit"]')
    html=html.replace('</section>\n\n<section id="library" class="view">',TRANSITION_CARD+'</section>\n\n<section id="library" class="view">',1)
    html=html.replace('<div class="card">\n<div class="row"><h2>Reactive Layer</h2>',LAYER_CARD+'\n<div class="card">\n<div class="row"><h2>Reactive Layer</h2>',1)
    html=html.replace('<section id="edit" class="view">',GUEST_SECTION+'\n<section id="edit" class="view">',1)
    html=html.replace('async function update(){',PERFORMANCE_JS+'\nasync function update(){',1)
    return html

phone_server.PHONE_HTML=enhanced_html(phone_server.PHONE_HTML)
PhoneControlServer=audio_phone_server.PhoneControlServer
