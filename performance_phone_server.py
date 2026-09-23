import audio_phone_server
import phone_server

PERFORMANCE_CSS = r"""
<style>
.tabs{display:flex!important;overflow-x:auto;gap:8px;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tabs button{flex:0 0 auto;min-width:92px}
.transitionGrid,.layerGrid,.guestGrid,.sceneGrid,.textGrid{display:grid;gap:8px}.transitionGrid{grid-template-columns:repeat(2,1fr)}.layerGrid{grid-template-columns:1fr 1fr}.guestGrid{grid-template-columns:repeat(2,1fr)}.sceneGrid{grid-template-columns:repeat(4,1fr)}.textGrid{grid-template-columns:repeat(2,1fr)}
.sceneGrid button{min-height:52px}.sceneGrid button.active{box-shadow:0 0 0 2px #ffffff55 inset,0 0 22px #7063d766}.selectDark,.textInput{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:11px;font-size:16px}.textInput{min-height:94px;resize:vertical;font-family:inherit;line-height:1.35}.tiny{font-size:11px;opacity:.65}.sectionHint{font-size:12px;opacity:.7;line-height:1.4;margin:-3px 0 10px}
.textCard{background:radial-gradient(circle at 10% 0%,#6c4cff22,transparent 35%),radial-gradient(circle at 100% 10%,#00c8ff18,transparent 38%),#ffffff12}.textShow{width:100%;min-height:58px;font-size:18px;background:linear-gradient(135deg,#6c4cff,#00b8ff)}.colorRow{display:grid;grid-template-columns:1fr 74px;gap:8px}.colorRow input[type=color]{width:74px;height:46px;border:0;border-radius:10px;background:#202029;padding:5px}.textBgBox{margin-top:14px;padding-top:12px;border-top:1px solid #ffffff14}
.chaosCard{position:relative;overflow:hidden;background:radial-gradient(circle at 20% 0%,#ff3d9a55,transparent 34%),radial-gradient(circle at 90% 18%,#00e5ff44,transparent 34%),linear-gradient(150deg,#25113c,#101026 55%,#07151d);border:1px solid #ffffff26;box-shadow:0 12px 38px #0008}
.chaosTitle{font-size:30px!important;letter-spacing:.04em;margin-bottom:3px!important}.chaosSub{font-size:12px;opacity:.72;margin-bottom:12px}.guestGrid button{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;touch-action:manipulation;min-height:112px;font-size:19px;border:1px solid #ffffff20;box-shadow:inset 0 1px #ffffff24,0 6px 18px #0005;transition:transform .07s ease,filter .07s ease,box-shadow .07s ease}.guestGrid button:active,.guestGrid button.pressed{transform:scale(.955);filter:brightness(1.25);box-shadow:inset 0 2px 12px #0007}
.padGlitch{background:linear-gradient(145deg,#6c2cff,#ff2fd1)}.padRainbow{background:linear-gradient(135deg,#ff3366,#ffb000 30%,#00d084 62%,#3978ff)}.padWarp{background:linear-gradient(145deg,#00c6ff,#6c4cff)}.padMelt{background:linear-gradient(145deg,#26d0ce,#7b2ff7)}.padRandom{background:linear-gradient(145deg,#13d882,#00a8ff)}
.guestBig{grid-column:1/-1;min-height:138px!important;font-size:24px!important;letter-spacing:.08em;background:radial-gradient(circle at 20% 50%,#ffea00aa,transparent 22%),radial-gradient(circle at 80% 40%,#00f5ffaa,transparent 25%),linear-gradient(120deg,#ff006e,#8338ec,#3a86ff,#06d6a0);background-size:160% 160%;animation:chaosGlow 3s linear infinite;touch-action:none!important}
@keyframes chaosGlow{0%{background-position:0 50%}50%{background-position:100% 50%}100%{background-position:0 50%}}
.guestIntensity{margin-top:15px;padding:10px 12px;background:#ffffff0d;border-radius:14px}.setupDivider{margin-top:18px;padding-top:4px;border-top:1px solid #ffffff12}.beatSync.active{background:linear-gradient(135deg,#7b42ff,#00b8ff)}
@media(max-width:520px){.layerGrid,.textGrid{grid-template-columns:1fr}.sceneGrid{grid-template-columns:repeat(2,1fr)}.tabs button{min-width:86px}.guestGrid button{min-height:104px}}
</style>
"""

LIBRARY_CARD = r"""
<div class="card"><div class="row"><h2>Library</h2><div id="count" class="muted"></div></div><div id="filters" class="filters"></div><div id="gallery" class="gallery"></div></div>
"""

SCENE_CARD = r"""
<div class="card"><h2>Performance Modes</h2><div class="sectionHint">Whole-totem vibes: slideshow pace, transitions, beat sync, audio style, and intensity together.</div><div id="sceneButtons" class="sceneGrid"></div></div>
"""

SHOW_CARD = r"""
<div class="card"><h2>Slideshow + Transitions</h2><div class="muted" id="selection"></div>
<div class="slider"><div class="sh"><span>Seconds per item</span><span id="dv" class="value">5s</span></div><input id="duration" type="range" min="1" max="30" value="5" oninput="durationPending=parseFloat(this.value);dv.textContent=this.value+'s'"></div>
<div class="g2" style="margin-bottom:8px"><button id="beatSyncButton" class="beatSync" onclick="toggleBeatSync()">Beat Sync</button><button id="randomTransition" onclick="toggleRandomTransition()">Random: On</button></div>
<div class="transitionGrid"><select id="transitionKind" class="selectDark" onchange="setTransition()"></select><div class="slider" style="margin:0"><div class="sh"><span>Transition</span><span id="transitionDurationValue">0.8s</span></div><input id="transitionDuration" type="range" min=".1" max="3" step=".1" value=".8" oninput="transitionDurationValue.textContent=parseFloat(this.value).toFixed(1)+'s';setTransition()"></div></div>
<div class="sectionHint">Beat Sync makes the timer a minimum display time, then lands the change on the next detected beat.</div>
<div class="g3"><button onclick="start(false)">Play</button><button onclick="start(true)">Shuffle</button><button class="warn" onclick="cmd('slideshow_stop')">Stop</button></div>
<div class="g2" style="margin-top:8px"><button onclick="step(-1)">◀ Previous</button><button onclick="step(1)">Next ▶</button></div></div>
"""

TEXT_SECTION = r"""
<section id="text" class="view">
<div class="card textCard"><h2>Text Engine</h2><div class="sectionHint">Build the message here, then Show Text to switch the selected display(s) into text mode.</div>
<textarea id="textMessage" class="textInput" maxlength="120" placeholder="TYPE SOMETHING UNREASONABLY IMPORTANT..."></textarea>
<div class="textGrid" style="margin-top:10px"><div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" onchange="textChanged()"></select></div><div><div class="sh"><span>Motion</span></div><select id="textMotion" class="selectDark" onchange="textChanged()"></select></div></div>
<div class="textGrid" style="margin-top:10px"><div><div class="sh"><span>Text Style</span></div><select id="textStyle" class="selectDark" onchange="textChanged()"><option>Clean</option><option>Glow</option><option>Wave</option><option>Glitch</option><option>Beat Pulse</option><option>Rave</option></select></div><div><div class="sh"><span>Color Mode</span></div><select id="textColorMode" class="selectDark" onchange="textChanged()"></select></div></div>
<div class="colorRow" style="margin-top:10px"><div class="sectionHint" style="margin:10px 0 0">Solid color</div><input id="textColor" type="color" value="#ffffff" oninput="textChanged()"></div>
<div class="textGrid"><div class="slider"><div class="sh"><span>Size</span><span id="textScaleValue">1x</span></div><input id="textScale" type="range" min="1" max="3" step="1" value="1" oninput="textScaleValue.textContent=this.value+'x';textChanged()"></div><div class="slider"><div class="sh"><span>Speed</span><span id="textSpeedValue">12</span></div><input id="textSpeed" type="range" min="1" max="40" step="1" value="12" oninput="textSpeedValue.textContent=this.value;textChanged()"></div></div>
<div class="textBgBox"><div class="sh"><span>Background</span><span class="tiny">GIF brightness capped at 55%</span></div><select id="textBackground" class="selectDark" onchange="textChanged()"></select><div class="slider"><div class="sh"><span>Background brightness</span><span id="textBgValue">28%</span></div><input id="textBgBrightness" type="range" min=".05" max=".55" step=".05" value=".28" oninput="pct('textBgValue',this.value);textChanged()"></div><button id="textBackplate" style="width:100%" onclick="toggleBackplate()">▰ Text Backplate</button></div>
<button class="textShow" style="margin-top:12px" onclick="showText()">SHOW TEXT</button>
</div></section>
"""

DISPLAY_CARD = r"""
<div class="card"><h2>Display</h2><div class="sectionHint">Less-frequent display controls live here so the main controller stays clean.</div>
<div class="slider"><div class="sh"><span>Brightness</span><span id="bv" class="value"></span></div><input id="brightness" type="range" min=".1" max="1" step=".05" oninput="pct('bv',this.value);range('brightness',this.value)"></div>
<div class="slider"><div class="sh"><span>Playback speed</span><span id="sv" class="value"></span></div><input id="speed" type="range" min=".1" max="5" step=".1" oninput="num('sv',this.value,'x');range('speed',this.value)"></div>
<div class="g2"><button id="pause" onclick="cmd('toggle_pause')">Pause</button><button onclick="cmd('reload_library')">Reload Library</button></div></div>
"""

LAYER_BLOCK = r"""
<div class="setupDivider"><div class="sectionHint">Audio Style presets above; fine-tune individual sound mappings below.</div><div id="layerGrid" class="layerGrid"></div></div>
"""

GUEST_SECTION = r"""
<section id="guest" class="view"><div class="card chaosCard"><h2 class="chaosTitle">CHAOS PAD</h2><div class="chaosSub">Always hits both panels. Big buttons, zero finesse.</div><div class="guestGrid" style="margin-top:12px">
<button class="padGlitch" onclick="guestAction('glitch')">⚡<br>GLITCH</button><button class="padRainbow" onclick="guestAction('rainbow')">🌈<br>RAINBOW</button>
<button class="padWarp" onclick="guestTransition('Ripple')">🌀<br>WARP → NEXT</button><button class="padMelt" onclick="guestTransition('Melt')">🫠<br>MELT → NEXT</button>
<button class="padRandom" onclick="guestAction('random')">🎲<br>RANDOM GIF</button><button class="padWarp" onclick="guestTransition('Zoom')">🛸<br>ZOOM → NEXT</button>
<button class="guestBig" onpointerdown="chaosStart(event)" onpointerup="chaosEnd(event)" onpointercancel="chaosEnd(event)" oncontextmenu="event.preventDefault()">HOLD FOR CHAOS</button>
</div><div class="guestIntensity slider"><div class="sh"><span>Chaos intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div></div></section>
"""

PERFORMANCE_JS = r"""
const layerLabels={bass_zoom:'Bass → Zoom',beat_flash:'Beat → Flash',mids_hue:'Mids → Hue',high_sparkle:'Highs → Sparkles',volume_brightness:'Volume → Brightness',bass_shake:'Bass → Shake',high_rgb_split:'Highs → RGB Split'};
let layerSignature='',sceneSignature='',textTimer=null,textBackplateLocal=true,durationPending=null;
const baseView=view;
view=function(n){baseView(n);let tc=document.getElementById('targetCard');if(tc)tc.style.display=n==='guest'?'none':'';if(n==='guest')cmd('set_target','both')}
function setTransition(){const k=transitionKind.value,d=parseFloat(transitionDuration.value),r=state.transition||{};cmd('transition_settings',{kind:k,duration:d,random:!!r.random})}
function toggleRandomTransition(){const r=state.transition||{};cmd('transition_settings',{random:!r.random})}
function toggleBeatSync(){const s=state.slideshow||{};cmd('slideshow_beat_sync',!s.beat_sync)}
function applyScene(name){durationPending=null;cmd('performance_scene',name)}
function renderScenes(){const names=state.performance_scenes||[],sig=names.join('|');if(sig!==sceneSignature){sceneSignature=sig;sceneButtons.innerHTML='';names.forEach(n=>{let b=document.createElement('button');b.textContent=n;b.dataset.scene=n;b.onclick=()=>applyScene(n);sceneButtons.appendChild(b)})}document.querySelectorAll('[data-scene]').forEach(b=>b.classList.toggle('active',b.dataset.scene===state.current_scene))}
function ensureOptions(el,items){if(!el)return;let sig=(items||[]).join('|');if(el.dataset.sig===sig)return;el.dataset.sig=sig;el.innerHTML='';(items||[]).forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;el.appendChild(o)})}
function styleFlags(){let s=textStyle.value;return {glow:s==='Glow'||s==='Rave',wave:s==='Wave'||s==='Rave',glitch:s==='Glitch',beat_pulse:s==='Beat Pulse'||s==='Rave'}}
function textPayload(){return {message:textMessage.value,font:textFont.value,motion:textMotion.value,color_mode:textColorMode.value,color:textColor.value,scale:parseInt(textScale.value),speed:parseFloat(textSpeed.value),background:textBackground.value,background_brightness:parseFloat(textBgBrightness.value),backplate:textBackplateLocal,...styleFlags()}}
function textChanged(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd('text_settings',textPayload()),100)}
function toggleBackplate(){textBackplateLocal=!textBackplateLocal;textBackplate.classList.toggle('active',textBackplateLocal);textChanged()}
function showText(){cmd('text_show',textPayload())}
function styleFromState(t){if(t.glow&&t.wave&&t.beat_pulse&&!t.glitch)return'Rave';if(t.glitch)return'Glitch';if(t.wave)return'Wave';if(t.glow)return'Glow';if(t.beat_pulse)return'Beat Pulse';return'Clean'}
function syncTextUI(){let t=state.text||{};ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);ensureOptions(textBackground,state.text_backgrounds||[]);if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;if(document.activeElement!==textBackground&&t.background)textBackground.value=t.background;if(document.activeElement!==textScale&&t.scale!=null)textScale.value=t.scale;if(document.activeElement!==textSpeed&&t.speed!=null)textSpeed.value=t.speed;if(document.activeElement!==textBgBrightness&&t.background_brightness!=null)textBgBrightness.value=t.background_brightness;textScaleValue.textContent=(t.scale??1)+'x';textSpeedValue.textContent=Math.round(t.speed??12);pct('textBgValue',t.background_brightness??.28);textBackplateLocal=!!t.backplate;textBackplate.classList.toggle('active',textBackplateLocal)}
async function bothThen(command,value){await cmd('set_target','both');return cmd(command,value)}
function guestAction(kind){return bothThen('guest_action',{kind,strength:parseFloat(guestIntensity.value),duration:.8})}
async function guestTransition(kind){await cmd('set_target','both');const tr=state.transition||{},ids=(state.library||[]).map(x=>x.index);if(!ids.length)return;const restore={kind:tr.kind||'Fade',duration:tr.duration??.8,random:!!tr.random};await cmd('transition_settings',{kind,duration:.85,random:false});await cmd('filtered_step',{indices:ids,delta:1});setTimeout(()=>cmd('transition_settings',restore),180)}
function guestHold(on){return bothThen(on?'guest_action':'guest_stop',on?{kind:'chaos',strength:parseFloat(guestIntensity.value),duration:30}:null)}
function chaosStart(e){e.preventDefault();if(e.currentTarget.setPointerCapture)try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_){ }e.currentTarget.classList.add('pressed');guestHold(true)}
function chaosEnd(e){e.preventDefault();e.currentTarget.classList.remove('pressed');guestHold(false)}
function renderLayerControls(){const keys=state.layer_keys||[],sig=keys.join('|'),grid=document.getElementById('layerGrid');if(!grid)return;if(sig!==layerSignature){layerSignature=sig;grid.innerHTML='';keys.forEach(k=>{let wrap=document.createElement('div');wrap.className='slider';let head=document.createElement('div');head.className='sh';let a=document.createElement('span');a.textContent=layerLabels[k]||k;let val=document.createElement('span');val.id='lv_'+k;head.append(a,val);let input=document.createElement('input');input.type='range';input.min='0';input.max='1.5';input.step='.05';input.id='layer_'+k;input.oninput=()=>{num(val.id,input.value,'x');cmd('reactive_layer',{name:k,value:parseFloat(input.value)})};wrap.append(head,input);grid.appendChild(wrap)})}const layers=(state.reactive||{}).layers||{};keys.forEach(k=>{let e=document.getElementById('layer_'+k);if(e&&document.activeElement!==e)e.value=layers[k]??0;let v=document.getElementById('lv_'+k);if(v)v.textContent=parseFloat(layers[k]??0).toFixed(2)+'x'})}
function syncPerformanceUI(){if(typeof state==='undefined')return;renderLayerControls();renderScenes();syncTextUI();let tr=state.transition||{},select=document.getElementById('transitionKind');if(select){let options=state.transitions||[],sig=options.join('|');if(select.dataset.sig!==sig){select.dataset.sig=sig;select.innerHTML='';options.forEach(n=>{let o=document.createElement('option');o.value=n;o.textContent=n;select.appendChild(o)})}if(document.activeElement!==select&&tr.kind)select.value=tr.kind}let td=document.getElementById('transitionDuration');if(td&&document.activeElement!==td&&tr.duration!=null)td.value=tr.duration;let tv=document.getElementById('transitionDurationValue');if(tv&&tr.duration!=null)tv.textContent=parseFloat(tr.duration).toFixed(1)+'s';let rb=document.getElementById('randomTransition');if(rb){rb.textContent='Random: '+(tr.random?'On':'Off');rb.classList.toggle('active',!!tr.random)}let sl=state.slideshow||{},bb=document.getElementById('beatSyncButton');if(bb){bb.textContent=sl.beat_sync?'♫ Beat Sync: On':'♫ Beat Sync: Off';bb.classList.toggle('active',!!sl.beat_sync)}if(window.duration&&sl.duration!=null){if(durationPending!=null&&Math.abs(parseFloat(sl.duration)-durationPending)<.01)durationPending=null;if(durationPending==null&&document.activeElement!==duration){duration.value=sl.duration;dv.textContent=parseFloat(sl.duration).toFixed(sl.duration%1?1:0)+'s'}}}
setInterval(syncPerformanceUI,300);
"""


def enhanced_html(source):
    html=source.replace("</head>",PERFORMANCE_CSS+"\n</head>",1)
    html=html.replace('<h1>Festival Totem</h1><div class="muted">● Live controller</div>','',1)
    html=html.replace('<div class="card"><h2>Target</h2><div class="target">','<div id="targetCard" class="card"><h2>Target</h2><div class="target">',1)
    old_tabs=r'''<button id="tabLive" class="active" onclick="view('live')">Live</button><button id="tabLibrary" onclick="view('library')">Library</button><button id="tabAudio" onclick="view('audio')">Audio</button><button id="tabEdit" onclick="view('edit')">Edit</button>'''
    new_tabs=r'''<button id="tabLive" class="active" onclick="view('live')">Library</button><button id="tabText" onclick="view('text')">Text</button><button id="tabAudio" onclick="view('audio')">Audio</button><button id="tabGuest" onclick="view('guest')">Chaos Pad</button><button id="tabEdit" onclick="view('edit')">Setup</button>'''
    html=html.replace(old_tabs,new_tabs,1).replace('["live","library","audio","edit"]','["live","text","audio","guest","edit"]')
    now_playing=r'''<div class="card"><div class="row"><h2>Now Playing</h2><button id="fav" onclick="cmd('toggle_favorite')">☆</button></div><div class="now" id="now">Connecting...</div><div class="muted" id="info"></div><div class="muted" id="summary"></div><div class="muted" id="show"></div></div>'''
    effects=r'''<div class="card"><h2>Effects</h2><div class="g3" id="effects"></div></div>'''
    playback=r'''<div class="card"><h2>Playback</h2><div class="slider"><div class="sh"><span>Brightness</span><span id="bv" class="value"></span></div><input id="brightness" type="range" min=".1" max="1" step=".05" oninput="pct('bv',this.value);range('brightness',this.value)"></div><div class="slider"><div class="sh"><span>Speed</span><span id="sv" class="value"></span></div><input id="speed" type="range" min=".1" max="5" step=".1" oninput="num('sv',this.value,'x');range('speed',this.value)"></div><div class="g2"><button id="pause" onclick="cmd('toggle_pause')">Pause</button><button onclick="cmd('reload_library')">Reload Library</button></div></div>'''
    slideshow=r'''<div class="card"><h2>Slideshow</h2><div class="muted" id="selection"></div><div class="slider"><div class="sh"><span>Seconds per item</span><span id="dv" class="value">5s</span></div><input id="duration" type="range" min="1" max="30" value="5" oninput="dv.textContent=this.value+'s'"></div><div class="g3"><button onclick="start(false)">Play</button><button onclick="start(true)">Shuffle</button><button class="warn" onclick="cmd('slideshow_stop')">Stop</button></div><div class="g2" style="margin-top:8px"><button onclick="step(-1)">◀ Previous</button><button onclick="step(1)">Next ▶</button></div></div>'''
    library_section=r'''<section id="library" class="view"><div class="card"><div class="row"><h2>Library</h2><div id="count" class="muted"></div></div><div id="filters" class="filters"></div><div id="gallery" class="gallery"></div></div></section>'''
    html=html.replace(now_playing,'',1).replace(effects,'',1).replace(playback,'',1).replace(slideshow,SCENE_CARD+SHOW_CARD+LIBRARY_CARD,1).replace(library_section,'',1)
    html=html.replace('<section id="edit" class="view">',TEXT_SECTION+'\n'+GUEST_SECTION+'\n<section id="edit" class="view">'+DISPLAY_CARD,1)
    html=html.replace('<div id="reactiveLayerMount"></div>',LAYER_BLOCK,1).replace('<h2>Sound → Visuals</h2>','<h2>Audio Style</h2>',1).replace('effectRender();','')
    html=html.replace('async function update(){',PERFORMANCE_JS+'\nasync function update(){',1)
    return html


def apply(html):
    return enhanced_html(html)


PhoneControlServer=phone_server.PhoneControlServer
