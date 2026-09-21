import phone_server
import performance_phone_server

# Hidden compatibility targets for the legacy base poller.
_HIDDEN = '''<div style="display:none" aria-hidden="true"><button id="fav"></button><div id="now"></div><div id="info"></div><div id="summary"></div><div id="show"></div></div>'''
if 'id="now"' not in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _HIDDEN + '</body>', 1)

_EXTRA_CSS = r'''
<style>
input[type=range]{-webkit-appearance:none;appearance:none;height:46px;margin:2px 0;padding:0;background:transparent;touch-action:none;-webkit-tap-highlight-color:transparent}
input[type=range]::-webkit-slider-runnable-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;margin-top:-10px;box-shadow:0 2px 10px #0008}
input[type=range]::-moz-range-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-moz-range-thumb{width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;box-shadow:0 2px 10px #0008}
.textTop{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.textTop button{min-height:58px;font-size:17px}.textToggle.active{background:linear-gradient(135deg,#00b86b,#00a8ff)}
.quickText{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0 12px}.quickText button{min-height:54px;font-size:14px}.quickLabel{font-size:12px;opacity:.68;margin-top:5px}
.choice3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.choice3 button{min-height:54px;font-size:17px}.choice3 button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.chaosFxGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.chaosFxGrid button{min-height:112px;font-size:19px;touch-action:none;-webkit-user-select:none;user-select:none}.chaosFxGrid button.pressed{transform:scale(.96);filter:brightness(1.3)}
.fxGlitch{background:linear-gradient(145deg,#6c2cff,#ff2fd1)}.fxRainbow{background:linear-gradient(135deg,#ff3366,#ffb000 30%,#00d084 62%,#3978ff)}.fxChaos{background:linear-gradient(145deg,#ff006e,#8338ec,#3a86ff)}.fxWarp{background:linear-gradient(145deg,#00c6ff,#6c4cff)}.fxPrism{background:linear-gradient(145deg,#ff42b3,#00e5ff)}.fxMelt{background:linear-gradient(145deg,#ff7a18,#7b2ff7)}
.xyWrap{margin-top:14px}.xyPad{height:270px;position:relative;overflow:hidden;border-radius:18px;border:1px solid #ffffff2b;touch-action:none;background:radial-gradient(circle at 50% 50%,#ffffff18,transparent 8%),linear-gradient(135deg,#ff006e33,#8338ec44 35%,#3a86ff44 68%,#06d6a044)}
.xyPad:before{content:'COLOR / SPLIT  ↔';position:absolute;left:12px;top:10px;font-size:11px;opacity:.65}.xyPad:after{content:'ZOOM / ENERGY  ↕';position:absolute;right:10px;bottom:10px;font-size:11px;opacity:.65}.xyDot{position:absolute;width:34px;height:34px;border-radius:50%;border:3px solid white;background:#ffffff55;box-shadow:0 0 24px #fff8;transform:translate(-50%,-50%);left:50%;top:50%;pointer-events:none}
@media(max-width:520px){.quickText{grid-template-columns:1fr 1fr}.chaosFxGrid button{min-height:102px}.xyPad{height:240px}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _EXTRA_CSS + '</head>', 1)

# Put text master controls and quick-fire messages at the very top.
_TEXT_HEAD = r'''<div class="card textCard"><h2>Text Engine</h2><div class="sectionHint">Build the message here, then Show Text to switch the selected display(s) into text mode.</div>'''
_TEXT_HEAD_NEW = r'''<div class="card textCard"><h2>Text Engine</h2><div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">TEXT: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div><div class="quickLabel">Quick text — tap once to fire it immediately</div><div class="quickText"><button onclick="quickText('DRINK WATER')">DRINK WATER</button><button onclick="quickText('MEET ME HERE')">MEET ME HERE</button><button onclick="quickText('FOLLOW THE TOTEM')">FOLLOW THE TOTEM</button><button onclick="quickText(&quot;WHERE'S THE AFTERS?&quot;)">WHERE'S THE AFTERS?</button><button onclick="quickText('YOU GOOD?')">YOU GOOD?</button><button onclick="quickText('HAPPY BIRTHDAY')">HAPPY BIRTHDAY</button></div><div class="sectionHint">Or type a custom message:</div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_TEXT_HEAD, _TEXT_HEAD_NEW, 1)

# Size and speed become discrete choices.
_OLD_SIZE = r'''<div class="textGrid"><div class="slider"><div class="sh"><span>Size</span><span id="textScaleValue">1x</span></div><input id="textScale" type="range" min="1" max="3" step="1" value="1" oninput="textScaleValue.textContent=this.value+'x';textChanged()"></div><div class="slider"><div class="sh"><span>Speed</span><span id="textSpeedValue">12</span></div><input id="textSpeed" type="range" min="1" max="40" step="1" value="12" oninput="textSpeedValue.textContent=this.value;textChanged()"></div></div>'''
_NEW_SIZE = r'''<div class="textGrid"><div><div class="sh"><span>Size</span></div><div class="choice3"><button id="textSize1" onclick="setTextSize(1)">1×</button><button id="textSize2" onclick="setTextSize(2)">2×</button><button id="textSize3" onclick="setTextSize(3)">3×</button></div></div><div><div class="sh"><span>Speed</span></div><div class="choice3"><button id="textSpeedSlow" onclick="setTextSpeed('Slow')">Slow</button><button id="textSpeedMedium" onclick="setTextSpeed('Medium')">Med</button><button id="textSpeedFast" onclick="setTextSpeed('Fast')">Fast</button></div></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_OLD_SIZE, _NEW_SIZE, 1)

# Background is now intentionally boring: current visual continues, dimmed to 30%, backplate always on.
_BG_BOX = r'''<div class="textBgBox"><div class="sh"><span>Background</span><span class="tiny">GIF brightness capped at 55%</span></div><select id="textBackground" class="selectDark" onchange="textChanged()"></select><div class="slider"><div class="sh"><span>Background brightness</span><span id="textBgValue">28%</span></div><input id="textBgBrightness" type="range" min=".05" max=".55" step=".05" value=".28" oninput="pct('textBgValue',this.value);textChanged()"></div><button id="textBackplate" style="width:100%" onclick="toggleBackplate()">▰ Text Backplate</button></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_BG_BOX, '', 1)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<button class="textShow" style="margin-top:12px" onclick="showText()">SHOW TEXT</button>', '', 1)

# Replace Chaos Pad with holdable effects + XY performance surface.
_GUEST_START = phone_server.PHONE_HTML.find('<section id="guest" class="view">')
_GUEST_END = phone_server.PHONE_HTML.find('</section>', _GUEST_START)
if _GUEST_START >= 0 and _GUEST_END >= 0:
    _GUEST_END += len('</section>')
    _NEW_GUEST = r'''<section id="guest" class="view"><div class="card chaosCard"><h2 class="chaosTitle">CHAOS PAD</h2><div class="chaosSub">Everything here hits both panels. Hold a button, or drag around the pad.</div><div class="chaosFxGrid"><button class="fxGlitch" onpointerdown="holdFxStart(event,'glitch')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">⚡<br>GLITCH</button><button class="fxRainbow" onpointerdown="holdFxStart(event,'rainbow')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">🌈<br>RAINBOW</button><button class="fxChaos" onpointerdown="holdFxStart(event,'chaos')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">💀<br>CHAOS</button><button class="fxWarp" onpointerdown="holdFxStart(event,'warp')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">🌀<br>WARP</button><button class="fxPrism" onpointerdown="holdFxStart(event,'prism')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">🔮<br>PRISM</button><button class="fxMelt" onpointerdown="holdFxStart(event,'meltdown')" onpointerup="holdFxEnd(event)" onpointercancel="holdFxEnd(event)">🫠<br>MELTDOWN</button></div><div class="xyWrap"><div class="sh"><span>TRUE CHAOS PAD</span><span class="tiny">drag + move fast</span></div><div id="chaosXY" class="xyPad" onpointerdown="xyStart(event)" onpointermove="xyMove(event)" onpointerup="xyEnd(event)" onpointercancel="xyEnd(event)"><div id="xyDot" class="xyDot"></div></div></div><div class="guestIntensity slider"><div class="sh"><span>Chaos intensity</span><span id="guestIntensityValue">100%</span></div><input id="guestIntensity" type="range" min=".1" max="1" step=".05" value="1" oninput="pct('guestIntensityValue',this.value)"></div></div></section>'''
    phone_server.PHONE_HTML = phone_server.PHONE_HTML[:_GUEST_START] + _NEW_GUEST + phone_server.PHONE_HTML[_GUEST_END:]

_EXTRA_JS = r'''
<script>
let textScaleLocal=1,textSpeedLocal='Medium',textEnabledLocal=false;
const textSpeeds={Slow:6,Medium:12,Fast:22};
function setTextSize(v){textScaleLocal=Math.max(1,Math.min(3,parseInt(v)||1));syncTextChoices();textChanged()}
function setTextSpeed(v){if(textSpeeds[v])textSpeedLocal=v;syncTextChoices();textChanged()}
function syncTextChoices(){[1,2,3].forEach(v=>{let b=document.getElementById('textSize'+v);if(b)b.classList.toggle('active',v===textScaleLocal)});['Slow','Medium','Fast'].forEach(v=>{let b=document.getElementById('textSpeed'+v);if(b)b.classList.toggle('active',v===textSpeedLocal)})}
function textPayload(){return {message:textMessage.value,font:textFont.value,motion:textMotion.value,color_mode:textColorMode.value,color:textColor.value,scale:textScaleLocal,speed:textSpeeds[textSpeedLocal]||12,background:'Dimmed GIF',background_brightness:.30,backplate:true,...styleFlags()}}
function toggleTextMaster(){textEnabledLocal=!textEnabledLocal;if(textEnabledLocal)cmd('text_show',textPayload());else cmd('text_hide');syncTextMaster()}
function refreshText(){cmd('text_refresh',textPayload())}
function quickText(message){textMessage.value=message;textEnabledLocal=true;cmd('text_show',textPayload());syncTextMaster()}
function syncTextMaster(){let b=document.getElementById('textMaster');if(!b)return;b.textContent='TEXT: '+(textEnabledLocal?'ON':'OFF');b.classList.toggle('active',textEnabledLocal)}
function speedName(v){v=parseFloat(v??12);return v<=8?'Slow':v>=18?'Fast':'Medium'}
function syncTextUI(){let t=state.text||{};ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;textScaleLocal=parseInt(t.scale??1);textSpeedLocal=speedName(t.speed);textEnabledLocal=!!t.enabled;syncTextChoices();syncTextMaster()}
let holdFx=null;
function holdFxStart(e,kind){e.preventDefault();holdFx=kind;e.currentTarget.classList.add('pressed');if(e.currentTarget.setPointerCapture)try{e.currentTarget.setPointerCapture(e.pointerId)}catch(_){ }cmd('guest_action',{kind,strength:parseFloat(guestIntensity.value),duration:30})}
function holdFxEnd(e){e.preventDefault();if(e.currentTarget)e.currentTarget.classList.remove('pressed');holdFx=null;cmd('guest_stop')}
let xyActive=false,xyLast=null,xyLastSend=0;
function xyPoint(e){let r=chaosXY.getBoundingClientRect(),x=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));return{x,y}}
function sendXY(e,force=false){let p=xyPoint(e),now=performance.now(),vel=0;if(xyLast){let dt=Math.max(1,now-xyLast.t),dx=p.x-xyLast.x,dy=p.y-xyLast.y;vel=Math.min(1,Math.hypot(dx,dy)*900/dt)}xyLast={...p,t:now};xyDot.style.left=(p.x*100)+'%';xyDot.style.top=(p.y*100)+'%';if(force||now-xyLastSend>35){xyLastSend=now;cmd('guest_xy',{x:p.x,y:p.y,velocity:vel,strength:parseFloat(guestIntensity.value)})}}
function xyStart(e){e.preventDefault();xyActive=true;xyLast=null;if(chaosXY.setPointerCapture)try{chaosXY.setPointerCapture(e.pointerId)}catch(_){ }sendXY(e,true)}
function xyMove(e){if(!xyActive)return;e.preventDefault();sendXY(e)}
function xyEnd(e){if(!xyActive)return;e.preventDefault();xyActive=false;xyLast=null;cmd('guest_stop')}
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _EXTRA_JS + '</body>', 1)

PhoneControlServer = performance_phone_server.PhoneControlServer
