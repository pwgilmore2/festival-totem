import audio_phone_server
import phone_server

PERFORMANCE_CSS = r"""
<style>
.tabs{display:flex!important;overflow-x:auto;gap:8px;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tabs button{flex:0 0 auto;min-width:92px}
.transitionGrid,.layerGrid,.guestGrid{display:grid;gap:8px}.transitionGrid{grid-template-columns:repeat(2,1fr)}.layerGrid{grid-template-columns:1fr 1fr}.guestGrid{grid-template-columns:repeat(2,1fr)}
.selectDark{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:11px;font-size:16px}.tiny{font-size:11px;opacity:.65}.sectionHint{font-size:12px;opacity:.7;line-height:1.4;margin:-3px 0 10px}
.chaosCard{position:relative;overflow:hidden;background:radial-gradient(circle at 20% 0%,#ff3d9a55,transparent 34%),radial-gradient(circle at 90% 18%,#00e5ff44,transparent 34%),linear-gradient(150deg,#25113c,#101026 55%,#07151d);border:1px solid #ffffff26;box-shadow:0 12px 38px #0008}
.chaosTitle{font-size:28px!important;letter-spacing:.04em;margin-bottom:3px!important}.chaosSub{font-size:12px;opacity:.72;margin-bottom:12px}.guestGrid button{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;touch-action:manipulation;min-height:76px;font-size:16px;border:1px solid #ffffff20;box-shadow:inset 0 1px #ffffff24,0 6px 18px #0005;transition:transform .07s ease,filter .07s ease,box-shadow .07s ease}.guestGrid button:active,.guestGrid button.pressed{transform:scale(.955);filter:brightness(1.25);box-shadow:inset 0 2px 12px #0007}
.padBoom{background:linear-gradient(145deg,#ff2d55,#ff7a18)}.padGlitch{background:linear-gradient(145deg,#6c2cff,#ff2fd1)}.padSpark{background:linear-gradient(145deg,#ffbe0b,#ff5e00);color:#171006!important}.padRainbow{background:linear-gradient(135deg,#ff3366,#ffb000 30%,#00d084 62%,#3978ff)}.padWarp{background:linear-gradient(145deg,#00c6ff,#6c4cff)}.padMelt{background:linear-gradient(145deg,#26d0ce,#7b2ff7)}.padRandom{background:linear-gradient(145deg,#13d882,#00a8ff)}.padNext{background:linear-gradient(145deg,#324bff,#00a4ff)}.padParty{background:linear-gradient(145deg,#ff42b3,#7b42ff)}
.guestBig{grid-column:1/-1;min-height:104px!important;font-size:22px!important;letter-spacing:.08em;background:radial-gradient(circle at 20% 50%,#ffea00aa,transparent 22%),radial-gradient(circle at 80% 40%,#00f5ffaa,transparent 25%),linear-gradient(120deg,#ff006e,#8338ec,#3a86ff,#06d6a0);background-size:160% 160%;animation:chaosGlow 3s linear infinite;touch-action:none!important}
@keyframes chaosGlow{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}
.guestIntensity{margin-top:15px;padding:10px 12px;background:#ffffff0d;border-radius:14px}.setupDivider{margin-top:18px;padding-top:4px;border-top:1px solid #ffffff12}
@media(max-width:520px){.layerGrid{grid-template-columns:1fr}.tabs button{min-width:86px}.guestGrid button{min-height:72px}}
</style>
"""

LIBRARY_CARD = r"""
<div class="card"><div class="row"><h2>Library</h2><div id="count" class="muted"></div></div><div id="filters" class="filters"></div><div id="gallery" class="gallery"></div></div>
"""

SHOW_CARD = r"""
<div class="card"><h2>Slideshow + Transitions</h2><div class="muted" id="selection"></div>
<div class="slider"><div class="sh"><span>Seconds per item</span><span id="dv" class="value">5s</span></div><input id="duration" type="range" min="1" max="30" value="5" oninput="dv.textContent=this.value+'s'"></div>
<div class="transitionGrid"><select id="transitionKind" class="selectDark" onchange="setTransition()"></select><button id="randomTransition" onclick="toggleRandomTransition()">Random: Off</button></div>
<div class="slider"><div class="sh"><span>Transition duration</span><span id="transitionDurationValue">0.8s</span></div><input id="transitionDuration" type="range" min=".1" max="3" step=".1" value=".8" oninput="transitionDurationValue.textContent=parseFloat(this.value).toFixed(1)+'s';setTransition()"></div>
<div class="g3"><button onclick="start(false)">Play</button><button onclick="start(true)">Shuffle</button><button class="warn" onclick="cmd('slideshow_stop')">Stop</button></div>
<div class="g2" style="margin-top:8px"><button onclick="step(-1)">◀ Previous</button><button onclick="step(1)">Next ▶</button></div></div>
"""

DISPLAY_CARD = r"""
<div class="card"><h2>Display</h2><div class="sectionHint">Less-frequent display controls live here so the main controller stays clean.</div>
<div class="slider"><div class="sh"><span>Brightness</span><span id="bv" class="value"></span></div><input id="brightness" type="range" min=".1" max="1" step=".05" oninput="pct('bv',this.value);range('brightness',this.value)"></div>
<div class="slider"><div class="sh"><span>Playback speed</span><span id="sv" class="value"></span></div><input id="speed" type="range" min=".1" max="5" step=".1" oninput="num('sv',this.value,'x');range('speed',this.value)"></div>
<div class="g2"><button id="pause" onclick="cmd('toggle_pause')">Pause</button><button onclick="cmd('reload_library')">Reload Library</button></div></div>
"""

LAYER_BLOCK = r"""
<div class="setupDivider"><div class="sectionHint">Quick presets above; fine-tune individual sound mappings below.</div><div id="layerGrid" class="layerGrid"></div></div>
"""

GUEST_SECTION = r"""
<section id="guest" class="view">
<div class="card chaosCard"><h2 class="chaosTitle">CHAOS PAD</h2><div class="chaosSub">Smash buttons. Hold chaos. Saved setup stays untouched.</div>
<div class="guestGrid" style="margin-top:12px">
<button class="padBoom" onclick="guestAction('boom')">💥<br>BOOM</button><button class="padGlitch" onclick="guestAction('glitch')">⚡<br>GLITCH</button>
<button class="padSpark" onclick="guestAction('spark')">✨<br>SPARK STORM</button><button class="padRainbow" onclick="guestAction('rainbow')">🌈<br>RAINBOW</button>
<button class="padWarp" onclick="guestTransition('Ripple')">🌀<br>WARP → NEXT</button><button class="padMelt" onclick="guestTransition('Melt')">🫠<br>MELT → NEXT</button>
<button class="padRandom" onclick="guestAction('random')">🎲<br>RANDOM GIF</button><button class="padNext" onclick="guestAction('next')">➡️<br>NEXT GIF</button>
<button class="padParty" onclick="guestParty()">🎉<br>PARTY MODE</button><button class="padWarp" onclick="guestTransition('Zoom')">🛸<br>ZOOM → NEXT</button>
<button class="guestBig" onpointerdown="chaosStart(event)" onpointerup="chaosEnd(event)" onpointercancel="chaosEnd(event)" oncontextmenu="event.preventDefault()">HOLD FOR CHAOS</button>
</div><div class="guestIntensity slider"><div class="sh"><span>Chaos intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div></div>
</section>
"""

PERFORMANCE_JS = r"""
const layerLabels={bass_zoom:'Bass → Zoom',beat_flash:'Beat → Flash',mids_hue:'Mids → Hue',high_sparkle:'Highs → Sparkles',volume_brightness:'Volume → Brightness',bass_shake:'Bass → Shake',high_rgb_split:'Highs → RGB Split'};
let layerSignature='';
function setTransition(){const k=transitionKind.value,d=parseFloat(transitionDuration.value),r=state.transition||{};cmd('transition_settings',{kind:k,duration:d,random:!!r.random})}
function toggleRandomTransition(){const r=state.transition||{};cmd('transition_settings',{random:!r.random})}
function guestAction(kind){cmd('guest_action',{kind,strength:parseFloat(guestIntensity.value),duration:.8})}
async function guestTransition(kind){const tr=state.transition||{},ids=(state.library||[]).map(x=>x.index);if(!ids.length)return;const restore={kind:tr.kind||'Fade',duration:tr.duration??.8,random:!!tr.random};await cmd('transition_settings',{kind,duration:.85,random:false});await cmd('filtered_step',{indices:ids,delta:1});setTimeout(()=>cmd('transition_settings',restore),180)}
function guestParty(){cmd('effect','Party')}
function guestHold(on){if(on)cmd('guest_action',{kind:'chaos',strength:parseFloat(guestIntensity.value),duration:30});else cmd('guest_stop')}
function chaosStart(e){e.preventDefault();if(e.currentTarget.setPointerCapture)try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_){ }e.currentTarget.classList.add('pressed');guestHold(true)}
function chaosEnd(e){e.preventDefault();e.currentTarget.classList.remove('pressed');guestHold(false)}
function renderLayerControls(){const keys=state.layer_keys||[],sig=keys.join('|'),grid=document.getElementById('layerGrid');if(!grid)return;if(sig!==layerSignature){layerSignature=sig;grid.innerHTML='';keys.forEach(k=>{let wrap=document.createElement('div');wrap.className='slider';let head=document.createElement('div');head.className='sh';let a=document.createElement('span');a.textContent=layerLabels[k]||k;let val=document.createElement('span');val.id='lv_'+k;head.append(a,val);let input=document.createElement('input');input.type='range';input.min='0';input.max='1.5';input.step='.05';input.id='layer_'+k;input.oninput=()=>{num(val.id,input.value,'x');cmd('reactive_layer',{name:k,value:parseFloat(input.value)})};wrap.append(head,input);grid.appendChild(wrap)})}const layers=(state.reactive||{}).layers||{};keys.forEach(k=>{let e=document.getElementById('layer_'+k);if(e&&document.activeElement!==e)e.value=layers[k]??0;let v=document.getElementById('lv_'+k);if(v)v.textContent=parseFloat(layers[k]??0).toFixed(2)+'x'})}
function syncPerformanceUI(){if(typeof state==='undefined')return;renderLayerControls();let tr=state.transition||{},select=document.getElementById('transitionKind');if(select){let options=state.transitions||[],sig=options.join('|');if(select.dataset.sig!==sig){select.dataset.sig=sig;select.innerHTML='';options.forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;select.appendChild(o)})}if(document.activeElement!==select&&tr.kind)select.value=tr.kind}let td=document.getElementById('transitionDuration');if(td&&document.activeElement!==td&&tr.duration!=null)td.value=tr.duration;let tv=document.getElementById('transitionDurationValue');if(tv&&tr.duration!=null)tv.textContent=parseFloat(tr.duration).toFixed(1)+'s';let rb=document.getElementById('randomTransition');if(rb){rb.textContent='Random: '+(tr.random?'On':'Off');rb.classList.toggle('active',!!tr.random)}}
setInterval(syncPerformanceUI,300);
"""


def enhanced_html(source):
    html=source.replace("</head>",PERFORMANCE_CSS+"\n</head>",1)

    old_tabs = r'''<button id="tabLive" class="active" onclick="view('live')">Live</button><button id="tabLibrary" onclick="view('library')">Library</button><button id="tabAudio" onclick="view('audio')">Audio</button><button id="tabEdit" onclick="view('edit')">Edit</button>'''
    new_tabs = r'''<button id="tabLive" class="active" onclick="view('live')">Library</button><button id="tabAudio" onclick="view('audio')">Audio</button><button id="tabGuest" onclick="view('guest')">Chaos Pad</button><button id="tabEdit" onclick="view('edit')">Setup</button>'''
    html=html.replace(old_tabs,new_tabs,1)
    html=html.replace('["live","library","audio","edit"]','["live","audio","guest","edit"]')

    effects = r'''<div class="card"><h2>Effects</h2><div class="g3" id="effects"></div></div>'''
    playback = r'''<div class="card"><h2>Playback</h2><div class="slider"><div class="sh"><span>Brightness</span><span id="bv" class="value"></span></div><input id="brightness" type="range" min=".1" max="1" step=".05" oninput="pct('bv',this.value);range('brightness',this.value)"></div><div class="slider"><div class="sh"><span>Speed</span><span id="sv" class="value"></span></div><input id="speed" type="range" min=".1" max="5" step=".1" oninput="num('sv',this.value,'x');range('speed',this.value)"></div><div class="g2"><button id="pause" onclick="cmd('toggle_pause')">Pause</button><button onclick="cmd('reload_library')">Reload Library</button></div></div>'''
    slideshow = r'''<div class="card"><h2>Slideshow</h2><div class="muted" id="selection"></div><div class="slider"><div class="sh"><span>Seconds per item</span><span id="dv" class="value">5s</span></div><input id="duration" type="range" min="1" max="30" value="5" oninput="dv.textContent=this.value+'s'"></div><div class="g3"><button onclick="start(false)">Play</button><button onclick="start(true)">Shuffle</button><button class="warn" onclick="cmd('slideshow_stop')">Stop</button></div><div class="g2" style="margin-top:8px"><button onclick="step(-1)">◀ Previous</button><button onclick="step(1)">Next ▶</button></div></div>'''
    library_section = r'''<section id="library" class="view"><div class="card"><div class="row"><h2>Library</h2><div id="count" class="muted"></div></div><div id="filters" class="filters"></div><div id="gallery" class="gallery"></div></div></section>'''

    html=html.replace(effects,'',1).replace(playback,'',1).replace(slideshow,LIBRARY_CARD+SHOW_CARD,1).replace(library_section,'',1)
    html=html.replace('<section id="edit" class="view">',GUEST_SECTION+'\n<section id="edit" class="view">'+DISPLAY_CARD,1)
    html=html.replace('<div id="reactiveLayerMount"></div>',LAYER_BLOCK,1)
    html=html.replace('effectRender();','')
    html=html.replace('async function update(){',PERFORMANCE_JS+'\nasync function update(){',1)
    return html

phone_server.PHONE_HTML=enhanced_html(phone_server.PHONE_HTML)
PhoneControlServer=audio_phone_server.PhoneControlServer
