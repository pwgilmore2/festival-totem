import audio_phone_server
import phone_server

PERFORMANCE_CSS = r"""
<style>
.tabs{display:flex!important;overflow-x:auto;gap:8px;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tabs button{flex:0 0 auto;min-width:88px}
.transitionGrid,.layerGrid,.guestGrid{display:grid;gap:8px}.transitionGrid{grid-template-columns:repeat(2,1fr)}.layerGrid{grid-template-columns:1fr 1fr}.guestGrid{grid-template-columns:repeat(2,1fr)}
.selectDark{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:11px;font-size:16px}.tiny{font-size:11px;opacity:.65}
.chaosCard{position:relative;overflow:hidden;background:radial-gradient(circle at 20% 0%,#ff3d9a55,transparent 34%),radial-gradient(circle at 90% 18%,#00e5ff44,transparent 34%),linear-gradient(150deg,#25113c,#101026 55%,#07151d);border:1px solid #ffffff26;box-shadow:0 12px 38px #0008}
.chaosTitle{font-size:28px!important;letter-spacing:.04em;margin-bottom:3px!important}.chaosSub{font-size:12px;opacity:.72;margin-bottom:12px}.guestGrid button{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;touch-action:manipulation;min-height:76px;font-size:16px;border:1px solid #ffffff20;box-shadow:inset 0 1px #ffffff24,0 6px 18px #0005;transition:transform .07s ease,filter .07s ease,box-shadow .07s ease}.guestGrid button:active,.guestGrid button.pressed{transform:scale(.955);filter:brightness(1.25);box-shadow:inset 0 2px 12px #0007}.guestGrid button:disabled{filter:grayscale(1) brightness(.55);opacity:.55}
.padBoom{background:linear-gradient(145deg,#ff2d55,#ff7a18)}.padGlitch{background:linear-gradient(145deg,#6c2cff,#ff2fd1)}.padSpark{background:linear-gradient(145deg,#ffbe0b,#ff5e00);color:#171006!important}.padRainbow{background:linear-gradient(135deg,#ff3366,#ffb000 30%,#00d084 62%,#3978ff)}.padWarp{background:linear-gradient(145deg,#00c6ff,#6c4cff)}.padMelt{background:linear-gradient(145deg,#26d0ce,#7b2ff7)}.padRandom{background:linear-gradient(145deg,#13d882,#00a8ff)}.padNext{background:linear-gradient(145deg,#324bff,#00a4ff)}.padParty{background:linear-gradient(145deg,#ff42b3,#7b42ff)}
.guestBig{grid-column:1/-1;min-height:104px!important;font-size:22px!important;letter-spacing:.08em;background:radial-gradient(circle at 20% 50%,#ffea00aa,transparent 22%),radial-gradient(circle at 80% 40%,#00f5ffaa,transparent 25%),linear-gradient(120deg,#ff006e,#8338ec,#3a86ff,#06d6a0);background-size:160% 160%;animation:chaosGlow 3s linear infinite;touch-action:none!important}
@keyframes chaosGlow{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}
.guestIntensity{margin-top:15px;padding:10px 12px;background:#ffffff0d;border-radius:14px}.modeHint{padding:9px 11px;border-radius:12px;background:#ffffff0b;margin-top:8px;font-size:12px;line-height:1.4}
@media(max-width:520px){.layerGrid{grid-template-columns:1fr}.tabs button{min-width:82px}.guestGrid button{min-height:72px}}
</style>
"""

TRANSITION_CARD = r"""
<div class="card"><h2>Transitions</h2>
<div class="transitionGrid"><select id="transitionKind" class="selectDark" onchange="setTransition()"></select><button id="randomTransition" onclick="toggleRandomTransition()">Random: Off</button></div>
<div class="slider"><div class="sh"><span>Transition duration</span><span id="transitionDurationValue">0.80s</span></div><input id="transitionDuration" type="range" min=".1" max="3" step=".1" value=".8" oninput="document.getElementById('transitionDurationValue').textContent=parseFloat(this.value).toFixed(1)+'s';setTransition()"></div>
<div class="tiny">Manual image changes, slideshows, and effect changes all use this transition.</div>
</div>
<div class="card"><div class="row"><h2>Guest Controls</h2><button id="guestLockButton" onclick="toggleGuestLock()">Guest: On</button></div><div class="tiny">Guest mode can fire temporary performance effects, but cannot change image correction/setup settings.</div></div>
"""

LAYER_CARD = r"""
<div class="card"><h2>Reactive Layers</h2><div class="tiny">These are the live performance mappings. Presets load a combination; moving a slider makes it Custom.</div><div id="layerGrid" class="layerGrid"></div></div>
"""

GUEST_TAB = r"""<button id="tabGuest" onclick="view('guest')">Chaos Pad</button>"""

GUEST_SECTION = r"""
<section id="guest" class="view">
<div class="card chaosCard"><h2 class="chaosTitle">CHAOS PAD</h2><div class="chaosSub">Smash buttons. Hold chaos. Saved setup stays safe.</div><div id="guestStatus" class="muted">Performance controls are live.</div>
<div class="guestGrid" style="margin-top:12px">
<button data-guest class="padBoom" onclick="guestAction('boom')">💥<br>BOOM</button><button data-guest class="padGlitch" onclick="guestAction('glitch')">⚡<br>GLITCH</button>
<button data-guest class="padSpark" onclick="guestAction('spark')">✨<br>SPARK STORM</button><button data-guest class="padRainbow" onclick="guestAction('rainbow')">🌈<br>RAINBOW</button>
<button data-guest class="padWarp" onclick="guestTransition('Ripple')">🌀<br>WARP → NEXT</button><button data-guest class="padMelt" onclick="guestTransition('Melt')">🫠<br>MELT → NEXT</button>
<button data-guest class="padRandom" onclick="guestAction('random')">🎲<br>RANDOM GIF</button><button data-guest class="padNext" onclick="guestAction('next')">➡️<br>NEXT GIF</button>
<button data-guest class="padParty" onclick="guestParty()">🎉<br>PARTY MODE</button><button data-guest class="padWarp" onclick="guestTransition('Zoom')">🛸<br>ZOOM → NEXT</button>
<button data-guest class="guestBig" onpointerdown="chaosStart(event)" onpointerup="chaosEnd(event)" onpointercancel="chaosEnd(event)" oncontextmenu="event.preventDefault()">HOLD FOR CHAOS</button>
</div>
<div class="guestIntensity slider"><div class="sh"><span>Chaos intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div>
</div></section>
"""

PERFORMANCE_JS = r"""
const layerLabels={bass_zoom:'Bass → Zoom',beat_flash:'Beat → Flash',mids_hue:'Mids → Hue',high_sparkle:'Highs → Sparkles',volume_brightness:'Volume → Brightness',bass_shake:'Bass → Shake',high_rgb_split:'Highs → RGB Split'};
let layerSignature='';
function setTransition(){const k=document.getElementById('transitionKind').value,d=parseFloat(document.getElementById('transitionDuration').value),r=state.transition||{};cmd('transition_settings',{kind:k,duration:d,random:!!r.random})}
function toggleRandomTransition(){const r=state.transition||{};cmd('transition_settings',{random:!r.random})}
function toggleGuestLock(){const g=state.guest||{};cmd('guest_lock',!g.locked)}
function guestAction(kind){const g=state.guest||{};if(g.locked)return;cmd('guest_action',{kind,strength:parseFloat(document.getElementById('guestIntensity').value),duration:.8})}
async function guestTransition(kind){const g=state.guest||{};if(g.locked)return;const tr=state.transition||{},ids=(state.library||[]).map(x=>x.index);if(!ids.length)return;const restore={kind:tr.kind||'Fade',duration:tr.duration??.8,random:!!tr.random};await cmd('transition_settings',{kind,duration:.85,random:false});await cmd('filtered_step',{indices:ids,delta:1});setTimeout(()=>cmd('transition_settings',restore),180)}
function guestParty(){const g=state.guest||{};if(g.locked)return;cmd('effect','Party')}
function guestHold(kind,on){const g=state.guest||{};if(g.locked)return;if(on)cmd('guest_action',{kind,strength:parseFloat(document.getElementById('guestIntensity').value),duration:30});else cmd('guest_stop')}
function chaosStart(e){e.preventDefault();if(e.currentTarget.setPointerCapture)try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_){ }e.currentTarget.classList.add('pressed');guestHold('chaos',true)}
function chaosEnd(e){e.preventDefault();e.currentTarget.classList.remove('pressed');guestHold('chaos',false)}
function renderLayerControls(){const keys=state.layer_keys||[],sig=keys.join('|'),grid=document.getElementById('layerGrid');if(!grid)return;if(sig!==layerSignature){layerSignature=sig;grid.innerHTML='';keys.forEach(k=>{let wrap=document.createElement('div');wrap.className='slider';let head=document.createElement('div');head.className='sh';let a=document.createElement('span');a.textContent=layerLabels[k]||k;let val=document.createElement('span');val.id='lv_'+k;head.append(a,val);let input=document.createElement('input');input.type='range';input.min='0';input.max='1.5';input.step='.05';input.id='layer_'+k;input.oninput=()=>{num(val.id,input.value,'x');cmd('reactive_layer',{name:k,value:parseFloat(input.value)})};wrap.append(head,input);grid.appendChild(wrap)})}const layers=(state.reactive||{}).layers||{};keys.forEach(k=>{let e=document.getElementById('layer_'+k);if(e&&document.activeElement!==e)e.value=layers[k]??0;let v=document.getElementById('lv_'+k);if(v)v.textContent=parseFloat(layers[k]??0).toFixed(2)+'x'})}
function syncPerformanceUI(){if(typeof state==='undefined')return;renderLayerControls();let tr=state.transition||{},select=document.getElementById('transitionKind');if(select){let options=state.transitions||[],sig=options.join('|');if(select.dataset.sig!==sig){select.dataset.sig=sig;select.innerHTML='';options.forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;select.appendChild(o)})}if(document.activeElement!==select&&tr.kind)select.value=tr.kind}let td=document.getElementById('transitionDuration');if(td&&document.activeElement!==td&&tr.duration!=null)td.value=tr.duration;let tv=document.getElementById('transitionDurationValue');if(tv&&tr.duration!=null)tv.textContent=parseFloat(tr.duration).toFixed(1)+'s';let rb=document.getElementById('randomTransition');if(rb){rb.textContent='Random: '+(tr.random?'On':'Off');rb.classList.toggle('active',!!tr.random)}let g=state.guest||{},gb=document.getElementById('guestLockButton'),gs=document.getElementById('guestStatus');if(gb){gb.textContent=g.locked?'Guest: Locked':'Guest: On';gb.classList.toggle('warn',!!g.locked)}if(gs)gs.textContent=g.locked?'Chaos Pad is locked by owner.':'Performance controls are live.';document.querySelectorAll('[data-guest]').forEach(b=>b.disabled=!!g.locked)}
setInterval(syncPerformanceUI,300);
"""


def enhanced_html(source):
    html=source.replace("</head>",PERFORMANCE_CSS+"\n</head>",1)
    html=html.replace('<button id="tabEdit" onclick="view(\'edit\')">Edit</button>',GUEST_TAB+'<button id="tabEdit" onclick="view(\'edit\')">Setup</button>',1)
    html=html.replace('["live","library","audio","edit"]','["live","library","audio","guest","edit"]')
    html=html.replace('</section>\n\n<section id="library" class="view">',TRANSITION_CARD+'</section>\n\n<section id="library" class="view">',1)
    html=html.replace('<div class="card">\n<div class="row"><h2>Reactive Layer</h2>',LAYER_CARD+'\n<div class="card">\n<div class="row"><h2>Reactive Layer</h2>',1)
    html=html.replace('<section id="edit" class="view">',GUEST_SECTION+'\n<section id="edit" class="view">',1)
    html=html.replace('async function update(){',PERFORMANCE_JS+'\nasync function update(){',1)
    old_tabs='<button id="tabLive" class="active" onclick="view(\'live\')">Live</button><button id="tabLibrary" onclick="view(\'library\')">Library</button><button id="tabAudio" onclick="view(\'audio\')">Audio</button><button id="tabGuest" onclick="view(\'guest\')">Chaos Pad</button><button id="tabEdit" onclick="view(\'edit\')">Setup</button>'
    new_tabs='<button id="tabLive" class="active" onclick="view(\'live\')">Live</button><button id="tabAudio" onclick="view(\'audio\')">Audio</button><button id="tabGuest" onclick="view(\'guest\')">Chaos Pad</button><button id="tabLibrary" onclick="view(\'library\')">Library</button><button id="tabEdit" onclick="view(\'edit\')">Setup</button>'
    html=html.replace(old_tabs,new_tabs,1)
    return html

phone_server.PHONE_HTML=enhanced_html(phone_server.PHONE_HTML)
PhoneControlServer=audio_phone_server.PhoneControlServer
