"""Final compatibility/polish transform for the controller foundation.

This keeps only the cleanup behavior the current UI still uses. Obsolete
intermediate Chaos/Text markup from the old ui_cleanup_server patch is omitted;
newer feature transforms own those final sections.
"""

import phone_server

_HIDDEN = '''<div style="display:none" aria-hidden="true"><button id="fav"></button><div id="now"></div><div id="info"></div><div id="summary"></div><div id="show"></div></div>'''

_CSS = r'''
<style>
input[type=range]{-webkit-appearance:none;appearance:none;height:46px;margin:2px 0;padding:0;background:transparent;touch-action:pan-y;-webkit-tap-highlight-color:transparent}
input[type=range]::-webkit-slider-runnable-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;margin-top:-10px;box-shadow:0 2px 10px #0008}
input[type=range]::-moz-range-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-moz-range-thumb{width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;box-shadow:0 2px 10px #0008}
.textTop{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.textTop button{min-height:58px;font-size:17px}.textToggle.active{background:linear-gradient(135deg,#00b86b,#00a8ff)}
.quickText{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0 12px}.quickText button{min-height:54px;font-size:14px}.quickLabel{font-size:12px;opacity:.68;margin-top:5px}
.choice3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.choice3 button{min-height:54px;font-size:17px}.choice3 button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.fxGlitch{background:linear-gradient(145deg,#6c2cff,#ff2fd1)}.fxRainbow{background:linear-gradient(135deg,#ff3366,#ffb000 30%,#00d084 62%,#3978ff)}.fxChaos{background:linear-gradient(145deg,#ff006e,#8338ec,#3a86ff)}.fxWarp{background:linear-gradient(145deg,#00c6ff,#6c4cff)}.fxPrism{background:linear-gradient(145deg,#ff42b3,#00e5ff)}.fxMelt{background:linear-gradient(145deg,#ff7a18,#7b2ff7)}.fxPixelMelt{background:linear-gradient(145deg,#ff4d00,#7a001f)}.fxJumble{background:linear-gradient(145deg,#ffd000,#ff4d00);color:#160d00!important}.fxBass{background:linear-gradient(145deg,#4318ff,#ff185f)}.fxTrance{background:linear-gradient(145deg,#004e92,#00c9a7)}.fxLiquid{background:linear-gradient(145deg,#00b4d8,#7209b7)}.fxTunnel{background:linear-gradient(145deg,#001d3d,#ff006e)}
.xyWrap{margin-top:14px}.xyPad{height:270px;position:relative;overflow:hidden;border-radius:18px;border:1px solid #ffffff2b;touch-action:none;background:radial-gradient(circle at 50% 50%,#ffffff18,transparent 8%),linear-gradient(135deg,#ff006e33,#8338ec44 35%,#3a86ff44 68%,#06d6a044)}.xyDot{position:absolute;width:34px;height:34px;border-radius:50%;border:3px solid white;background:#ffffff55;box-shadow:0 0 24px #fff8;transform:translate(-50%,-50%);left:50%;top:50%;pointer-events:none}
.presetManage{display:flex;flex-direction:column;gap:7px;margin:9px 0}.presetManageRow{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;background:#ffffff0b;border-radius:11px;padding:7px 8px}.presetManageRow span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.presetManageRow button{min-height:36px;padding:6px 11px;background:#663640}.presetAdd{display:grid;grid-template-columns:1fr auto;gap:8px}.presetAdd input{width:100%;background:#202029;color:#fff;border:1px solid #444456;border-radius:10px;padding:11px;font-size:16px}
@media(max-width:520px){.quickText{grid-template-columns:1fr 1fr}.xyPad{height:240px}}
</style>
'''

_TEXT_HEAD = r'''<div class="card textCard"><h2>Text Engine</h2><div class="sectionHint">Build the message here, then Show Text to switch the selected display(s) into text mode.</div>'''
_TEXT_HEAD_NEW = r'''<div class="card textCard"><h2>Text Engine</h2><div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">TEXT: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div><div class="quickLabel">Quick text — tap once to fire it immediately</div><div id="quickTextButtons" class="quickText"></div><div class="sectionHint">Or type a custom message:</div>'''

_OLD_SIZE = r'''<div class="textGrid"><div class="slider"><div class="sh"><span>Size</span><span id="textScaleValue">1x</span></div><input id="textScale" type="range" min="1" max="3" step="1" value="1" oninput="textScaleValue.textContent=this.value+'x';textChanged()"></div><div class="slider"><div class="sh"><span>Speed</span><span id="textSpeedValue">12</span></div><input id="textSpeed" type="range" min="1" max="40" step="1" value="12" oninput="textSpeedValue.textContent=this.value;textChanged()"></div></div>'''
_NEW_SIZE = r'''<div class="textGrid"><div><div class="sh"><span>Size</span></div><div class="choice3"><button id="textSize1" onclick="setTextSize(1)">1×</button><button id="textSize2" onclick="setTextSize(2)">2×</button><button id="textSize3" onclick="setTextSize(3)">3×</button></div></div><div><div class="sh"><span>Speed</span></div><div class="choice3"><button id="textSpeedSlow" onclick="setTextSpeed('Slow')">Slow</button><button id="textSpeedMedium" onclick="setTextSpeed('Medium')">Med</button><button id="textSpeedFast" onclick="setTextSpeed('Fast')">Fast</button></div></div></div>'''

_BG_BOX = r'''<div class="textBgBox"><div class="sh"><span>Background</span><span class="tiny">GIF brightness capped at 55%</span></div><select id="textBackground" class="selectDark" onchange="textChanged()"></select><div class="slider"><div class="sh"><span>Background brightness</span><span id="textBgValue">28%</span></div><input id="textBgBrightness" type="range" min=".05" max=".55" step=".05" value=".28" oninput="pct('textBgValue',this.value);textChanged()"></div><button id="textBackplate" style="width:100%" onclick="toggleBackplate()">▰ Text Backplate</button></div>'''

_PRESET_SETUP = r'''<div class="card"><h2>Quick Text Presets</h2><div class="sectionHint">Add or remove the one-tap messages shown on the Text tab. Saved on this controller device.</div><div id="quickPresetList" class="presetManage"></div><div class="presetAdd"><input id="quickPresetInput" maxlength="120" placeholder="Add quick text"><button onclick="addQuickPreset()">Add</button></div><button style="width:100%;margin-top:8px" onclick="resetQuickPresets()">Restore Defaults</button></div>'''

_JS = r'''
<script>
let textScaleLocal=2,textSpeedLocal='Medium',textEnabledLocal=false;
const textSpeeds={Slow:12,Medium:22,Fast:34};
const quickPresetDefaults=['DRINK WATER','YOU GOOD?','WAKAAN','K HOLE','SPAGHETTI TIME','BASS FACE'];
let quickPresets=[];
function loadQuickPresets(){try{let raw=localStorage.getItem('festivalTotem.quickText');quickPresets=raw?JSON.parse(raw):[...quickPresetDefaults];if(!Array.isArray(quickPresets))throw 0}catch(_){quickPresets=[...quickPresetDefaults]}quickPresets=quickPresets.map(x=>String(x).trim()).filter(Boolean).slice(0,24);renderQuickPresets()}
function saveQuickPresets(){localStorage.setItem('festivalTotem.quickText',JSON.stringify(quickPresets));renderQuickPresets()}
function renderQuickPresets(){let q=document.getElementById('quickTextButtons');if(q){q.innerHTML='';quickPresets.forEach(msg=>{let b=document.createElement('button');b.textContent=msg;b.onclick=()=>quickText(msg);q.appendChild(b)});if(!quickPresets.length)q.innerHTML='<div class="muted">Add presets in Setup.</div>'}let p=document.getElementById('quickPresetList');if(p){p.innerHTML='';quickPresets.forEach((msg,i)=>{let row=document.createElement('div');row.className='presetManageRow';let s=document.createElement('span');s.textContent=msg;let b=document.createElement('button');b.textContent='Remove';b.onclick=()=>{quickPresets.splice(i,1);saveQuickPresets()};row.append(s,b);p.appendChild(row)});if(!quickPresets.length)p.innerHTML='<div class="muted">No quick text presets yet.</div>'}}
function addQuickPreset(){let i=document.getElementById('quickPresetInput'),v=(i?.value||'').trim();if(!v)return;if(!quickPresets.includes(v))quickPresets.push(v);quickPresets=quickPresets.slice(0,24);if(i)i.value='';saveQuickPresets()}
function resetQuickPresets(){quickPresets=[...quickPresetDefaults];saveQuickPresets()}
function setTextSize(v){textScaleLocal=Math.max(1,Math.min(3,parseInt(v)||2));syncTextChoices();textChanged()}
function setTextSpeed(v){if(textSpeeds[v])textSpeedLocal=v;syncTextChoices();textChanged()}
function syncTextChoices(){[1,2,3].forEach(v=>{let b=document.getElementById('textSize'+v);if(b)b.classList.toggle('active',v===textScaleLocal)});['Slow','Medium','Fast'].forEach(v=>{let b=document.getElementById('textSpeed'+v);if(b)b.classList.toggle('active',v===textSpeedLocal)})}
function textPayload(){return {message:textMessage.value,font:textFont.value,motion:textMotion.value,color_mode:textColorMode.value,color:textColor.value,scale:textScaleLocal,speed:textSpeeds[textSpeedLocal]||22,background:'Dimmed GIF',background_brightness:.30,backplate:true,...styleFlags()}}
function toggleTextMaster(){textEnabledLocal=!textEnabledLocal;if(textEnabledLocal)cmd('text_show',textPayload());else cmd('text_hide');syncTextMaster()}
function refreshText(){cmd('text_refresh',textPayload())}
function quickText(message){textMessage.value=message;textEnabledLocal=true;cmd('text_show',textPayload());syncTextMaster()}
function syncTextMaster(){let b=document.getElementById('textMaster');if(!b)return;b.textContent='TEXT: '+(textEnabledLocal?'ON':'OFF');b.classList.toggle('active',textEnabledLocal)}
function speedName(v){v=parseFloat(v??22);return v<17?'Slow':v>=29?'Fast':'Medium'}
function syncTextUI(){let t=state.text||{};ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;textScaleLocal=parseInt(t.scale??2);textSpeedLocal=speedName(t.speed);textEnabledLocal=!!t.enabled;syncTextChoices();syncTextMaster()}
let xyActive=false,xyLast=null,xyLastSend=0;
function xyPoint(e){let r=chaosXY.getBoundingClientRect(),x=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height));return{x,y}}
function sendXY(e,force=false){let p=xyPoint(e),now=performance.now(),vel=0;if(xyLast){let dt=Math.max(1,now-xyLast.t),dx=p.x-xyLast.x,dy=p.y-xyLast.y;vel=Math.min(1,Math.hypot(dx,dy)*900/dt)}xyLast={...p,t:now};xyDot.style.left=(p.x*100)+'%';xyDot.style.top=(p.y*100)+'%';if(force||now-xyLastSend>35){xyLastSend=now;cmd('guest_xy',{x:p.x,y:p.y,velocity:vel,strength:parseFloat(guestIntensity.value)})}}
function xyStart(e){e.preventDefault();xyActive=true;xyLast=null;if(chaosXY.setPointerCapture)try{chaosXY.setPointerCapture(e.pointerId)}catch(_){ }sendXY(e,true)}
function xyMove(e){if(!xyActive)return;e.preventDefault();sendXY(e)}
function xyEnd(e){if(!xyActive)return;e.preventDefault();xyActive=false;xyLast=null;cmd('guest_stop')}
loadQuickPresets();
</script>
'''


def apply(html):
    if 'id="now"' not in html:
        html = html.replace('</body>', _HIDDEN + '</body>', 1)
    html = html.replace('</head>', _CSS + '</head>', 1)
    html = html.replace(_TEXT_HEAD, _TEXT_HEAD_NEW, 1)
    html = html.replace(_OLD_SIZE, _NEW_SIZE, 1)
    html = html.replace(_BG_BOX, '', 1)
    html = html.replace('<button class="textShow" style="margin-top:12px" onclick="showText()">SHOW TEXT</button>', '', 1)
    html = html.replace('<section id="edit" class="view">', '<section id="edit" class="view">' + _PRESET_SETUP, 1)
    html = html.replace('</body>', _JS + '</body>', 1)
    return html


PhoneControlServer = phone_server.PhoneControlServer
