import json

import phone_server
from overlay_sprite_assets import SPRITES

_CSS = r'''
<style>
.overlayChoice,.fontButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.overlayChoice button,.fontButtons button{min-height:48px}.overlayChoice button.active,.fontButtons button.active,.iconTile.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.iconSection{margin:10px 0 16px;padding:12px 0 14px;border-bottom:1px solid #ffffff16}.iconGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:9px 0 4px}.iconTile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-height:104px;padding:8px}.iconTile canvas{width:62px;height:62px;image-rendering:pixelated}.iconTile span{font-size:11px;opacity:.8}.iconTile.active span{opacity:1;font-weight:700}
#textWaveToggle{display:none!important}.textMotionExtras{grid-template-columns:1fr!important}.overlayHint{font-size:11px;opacity:.66;line-height:1.35;margin-top:5px}
@media(max-width:520px){.iconGrid{grid-template-columns:repeat(2,1fr)}.iconTile{min-height:108px}.overlayChoice,.fontButtons{grid-template-columns:repeat(3,1fr)}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

# Keep legacy ids for compatibility, but present the feature as a generalized Overlay tab.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('>Text</button>', '>Overlay</button>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<h2>Text Engine</h2>', '<h2>Overlay</h2>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('TEXT: OFF', 'OVERLAY: OFF')

_anchor = '<div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">OVERLAY: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div>'
_insert = _anchor + r'''
<div class="iconSection"><div class="quickLabel">Pixel Icons — tap to add, tap the active icon again to remove</div><div class="overlayHint">Icons render large when used alone and automatically shrink/reposition when text is present.</div><div id="overlayIconGrid" class="iconGrid"></div></div>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_anchor, _insert, 1)

# Font buttons replace the legacy dropdown while the select remains hidden for old sync code.
_font = '<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" onchange="textChanged()"></select></div>'
_font_new = r'''<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="fontButtons"><button id="fontPixel" onclick="setOverlayFont('Pixel')">Pixel</button><button id="fontQuest" onclick="setOverlayFont('Quest')">Quest</button><button id="fontBlock" onclick="setOverlayFont('Block')">Block</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_font, _font_new, 1)

# Turn text motion into buttons and share the Float/Bounce behavior with icons.
_motion = '<div><div class="sh"><span>Motion</span></div><select id="textMotion" class="selectDark" onchange="textChanged()"></select></div>'
_motion_new = r'''<div><div class="sh"><span>Overlay Motion</span></div><select id="textMotion" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="overlayChoice"><button id="overlayMotionStatic" onclick="setOverlayMotion('Static')">Static</button><button id="overlayMotionFloat" onclick="setOverlayMotion('Float')">Float</button><button id="overlayMotionBounce" onclick="setOverlayMotion('Bounce')">Bounce</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_motion, _motion_new, 1)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<span>Text Style</span>', '<span>Overlay Style</span>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('Quick text — tap once to fire it immediately', 'Quick text — tap once to show it')

_SPRITES_JSON = json.dumps(SPRITES, separators=(',', ':'))
_JS = r'''
<script>
let overlayIconLocal='Heart',overlayIconEnabledLocal=false,overlayMotionLocal='Static';
const overlaySprites=__SPRITES__;
function drawIconPreview(canvas,name){
 const d=overlaySprites[name]||overlaySprites['Heart'],rows=d.rows,pal=d.palette,ctx=canvas.getContext('2d');canvas.width=32;canvas.height=32;ctx.clearRect(0,0,32,32);ctx.imageSmoothingEnabled=false;
 const w=Math.max(...rows.map(r=>r.length)),h=rows.length,scale=Math.max(1,Math.floor(Math.min(28/w,28/h))),ox=Math.floor((32-w*scale)/2),oy=Math.floor((32-h*scale)/2);
 rows.forEach((row,y)=>[...row].forEach((ch,x)=>{if(ch==='.')return;let c=pal[parseInt(ch)],px=ox+x*scale,py=oy+y*scale;ctx.fillStyle=`rgb(${c[0]},${c[1]},${c[2]})`;ctx.fillRect(px,py,scale,scale)}));
}
function renderOverlayIcons(){
 const g=document.getElementById('overlayIconGrid');if(!g)return;const names=(state.overlay_icons||Object.keys(overlaySprites)),sig=names.join('|');
 if(g.dataset.sig!==sig){g.dataset.sig=sig;g.innerHTML='';names.forEach(name=>{let b=document.createElement('button');b.className='iconTile';b.dataset.overlayIcon=name;b.onclick=()=>selectOverlayIcon(name);let c=document.createElement('canvas'),s=document.createElement('span');s.textContent=name;b.append(c,s);g.appendChild(b);drawIconPreview(c,name)})}
 document.querySelectorAll('[data-overlay-icon]').forEach(b=>b.classList.toggle('active',overlayIconEnabledLocal&&b.dataset.overlayIcon===overlayIconLocal));
}
function selectOverlayIcon(name){
 if(overlayIconEnabledLocal&&overlayIconLocal===name){overlayIconEnabledLocal=false}else{overlayIconLocal=name;overlayIconEnabledLocal=true}
 textEnabledLocal=true;syncOverlayUI();cmd('text_show',textPayload());syncTextMaster();
}
function setOverlayFont(name){if(['Pixel','Quest','Block'].includes(name)){textFont.value=name;textChanged();syncOverlayUI()}}
function setOverlayMotion(name){if(!['Static','Float','Bounce'].includes(name))return;overlayMotionLocal=name;textMotion.value=(name==='Static'?'Static':'Static');syncOverlayUI();textChanged()}
function syncOverlayLabel(){
 const tab=[...document.querySelectorAll('button')].find(b=>(b.getAttribute('onclick')||'').includes("view('text')"));if(tab)tab.textContent='Overlay';
 const card=document.querySelector('.textCard h2');if(card)card.textContent='Overlay';
}
function syncOverlayUI(){
 syncOverlayLabel();renderOverlayIcons();
 ['Pixel','Quest','Block'].forEach(n=>{let b=document.getElementById('font'+n);if(b)b.classList.toggle('active',textFont.value===n)});
 ['Static','Float','Bounce'].forEach(n=>{let b=document.getElementById('overlayMotion'+n);if(b)b.classList.toggle('active',overlayMotionLocal===n)});
 let master=document.getElementById('textMaster');if(master)master.textContent='OVERLAY: '+(textEnabledLocal?'ON':'OFF');
 const wave=document.getElementById('textWaveToggle');if(wave)wave.style.display='none';
}
const _overlayPayloadBase=textPayload;
textPayload=function(){let p=_overlayPayloadBase();p.overlay_icon=overlayIconLocal;p.overlay_icon_enabled=overlayIconEnabledLocal;p.overlay_motion=overlayMotionLocal;p.wave=false;p.speed=textSpeeds[textSpeedLocal]||22;return p};
const _overlaySyncBase=syncTextUI;
syncTextUI=function(){
 _overlaySyncBase();let t=state.text||{};overlayIconLocal=t.overlay_icon||overlayIconLocal||'Heart';overlayIconEnabledLocal=!!t.overlay_icon_enabled;overlayMotionLocal=t.overlay_motion||overlayMotionLocal||'Static';
 if(!['Pixel','Quest','Block'].includes(textFont.value))textFont.value='Pixel';if(!textSpeedLocal)textSpeedLocal='Medium';textWaveLocal=false;syncOverlayUI();
};
const _overlayTextMasterBase=syncTextMaster;
syncTextMaster=function(){_overlayTextMasterBase();syncOverlayUI()};
if(typeof textSpeedLocal!=='undefined'&&!textSpeedLocal)textSpeedLocal='Medium';
const _overlayObserver=new MutationObserver(()=>syncOverlayLabel());
window.addEventListener('load',()=>{syncOverlayLabel();const tabs=document.querySelector('.tabs');if(tabs)_overlayObserver.observe(tabs,{childList:true,subtree:true,characterData:true})});
</script>
'''.replace('__SPRITES__', _SPRITES_JSON)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
