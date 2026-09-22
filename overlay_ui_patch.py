import phone_server

_CSS = r'''
<style>
.overlayModeRow{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}.overlayModeRow button{min-height:56px;font-size:17px}.overlayModeRow button.active,.overlayChoice button.active,.fontButtons button.active,.iconTile.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.overlayChoice,.fontButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.overlayChoice button,.fontButtons button{min-height:48px}
.iconGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:10px 0 4px}.iconTile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-height:88px;padding:8px}.iconTile canvas{width:48px;height:48px;image-rendering:pixelated}.iconTile span{font-size:11px;opacity:.78}
.overlayShared{margin-top:14px;padding-top:12px;border-top:1px solid #ffffff16}.overlaySub{margin-top:10px}.overlayTextOnly.hidden,.overlayIconOnly.hidden{display:none!important}
@media(max-width:520px){.iconGrid{grid-template-columns:repeat(3,1fr)}.overlayChoice,.fontButtons{grid-template-columns:repeat(3,1fr)}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

# Rename tab/header language from Text to Overlay without disturbing ids used by existing JS.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('>Text</button>', '>Overlay</button>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<h2>Text Engine</h2>', '<h2>Overlay</h2>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('TEXT: OFF', 'OVERLAY: OFF')

# Inject mode switcher, icon chooser and button-based font selector into the existing text card.
_anchor = '<div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">OVERLAY: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div>'
_insert = _anchor + r'''
<div class="overlayModeRow"><button id="overlayModeText" onclick="setOverlayType('Text')">TEXT</button><button id="overlayModeIcon" onclick="setOverlayType('Icon')">ICON</button></div>
<div id="overlayIconChooser" class="overlayIconOnly hidden"><div class="quickLabel">Pixel overlays</div><div id="overlayIconGrid" class="iconGrid"></div></div>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_anchor, _insert, 1)

# Hide the legacy font dropdown but keep it alive for compatibility, and add font buttons.
_font = '<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" onchange="textChanged()"></select></div>'
_font_new = r'''<div class="overlayTextOnly"><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="fontButtons"><button id="fontPixel" onclick="setOverlayFont('Pixel')">Pixel</button><button id="fontQuest" onclick="setOverlayFont('Quest')">Quest</button><button id="fontBlock" onclick="setOverlayFont('Block')">Block</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_font, _font_new, 1)

# Hide the legacy motion dropdown and supply shared motion buttons.
_motion = '<div><div class="sh"><span>Motion</span></div><select id="textMotion" class="selectDark" onchange="textChanged()"></select></div>'
_motion_new = r'''<div><div class="sh"><span>Overlay Motion</span></div><select id="textMotion" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="overlayChoice"><button id="overlayMotionStatic" onclick="setOverlayMotion('Static')">Static</button><button id="overlayMotionFloat" onclick="setOverlayMotion('Float')">Float</button><button id="overlayMotionBounce" onclick="setOverlayMotion('Bounce')">Bounce</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_motion, _motion_new, 1)

# Rename text-only labels to generalized overlay wording.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<span>Text Style</span>', '<span>Overlay Style</span>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('Quick text — tap once to fire it immediately', 'Quick text — tap once to show it')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('Or type a custom message:', 'Or type a custom message:')

_JS = r'''
<script>
let overlayTypeLocal='Text',overlayIconLocal='Heart',overlayMotionLocal='Static';
const overlaySpriteBits={
'Heart':['01100110','11111111','11111111','11111111','01111110','00111100','00011000'],
'Mushroom':['00111100','01111110','11111111','11011011','01111110','00011000','00111100','00111100'],
'Wakaan Sigil':['10000001','10011001','10111101','11100111','11100111','10111101','10011001','10000001'],
'Sprout':['00100100','01110110','00111100','00011000','00011000','00011000','00111100','01111110'],
'Rune 2H':['00011000','00111100','01111110','00111100','00011000','00011000','01111110','00111100','00011000','00011000','00100100'],
'Eye':['00011000','01111110','11100111','11011011','11011011','11100111','01111110','00011000'],
'Skull':['00111100','01111110','11111111','11011011','11111111','01111110','00100100','00111100'],
'Alien':['00111100','01111110','11111111','11011011','10000001','01100110','00111100'],
'Smiley':['00111100','01111110','11011011','11111111','10111101','11000011','01111110','00111100'],
'Crystal':['00011000','00111100','01111110','11111111','01111110','00111100','00011000'],
'Moth':['10000001','11011011','11111111','01111110','00111100','01111110','11111111','10000001'],
'Orb':['00111100','01111110','11100111','11011011','11011011','11100111','01111110','00111100']};
function drawIconPreview(canvas,name){let rows=overlaySpriteBits[name]||overlaySpriteBits.Heart,ctx=canvas.getContext('2d');canvas.width=24;canvas.height=24;ctx.clearRect(0,0,24,24);ctx.fillStyle='#fff';let w=Math.max(...rows.map(r=>r.length)),h=rows.length,scale=Math.max(1,Math.floor(Math.min(20/w,20/h))),ox=Math.floor((24-w*scale)/2),oy=Math.floor((24-h*scale)/2);rows.forEach((row,y)=>[...row].forEach((bit,x)=>{if(bit==='1')ctx.fillRect(ox+x*scale,oy+y*scale,scale,scale)}))}
function renderOverlayIcons(){let g=document.getElementById('overlayIconGrid');if(!g)return;let names=(state.overlay_icons||Object.keys(overlaySpriteBits));let sig=names.join('|');if(g.dataset.sig!==sig){g.dataset.sig=sig;g.innerHTML='';names.forEach(name=>{let b=document.createElement('button');b.className='iconTile';b.dataset.overlayIcon=name;b.onclick=()=>selectOverlayIcon(name);let c=document.createElement('canvas');let s=document.createElement('span');s.textContent=name;b.append(c,s);g.appendChild(b);drawIconPreview(c,name)})}document.querySelectorAll('[data-overlay-icon]').forEach(b=>b.classList.toggle('active',b.dataset.overlayIcon===overlayIconLocal&&overlayTypeLocal==='Icon'))}
function setOverlayType(v){overlayTypeLocal=v==='Icon'?'Icon':'Text';syncOverlayUI();textChanged()}
function selectOverlayIcon(name){overlayTypeLocal='Icon';overlayIconLocal=name;syncOverlayUI();textEnabledLocal=true;cmd('text_show',textPayload());syncTextMaster()}
function setOverlayFont(name){if(['Pixel','Quest','Block'].includes(name)){textFont.value=name;textChanged();syncOverlayUI()}}
function setOverlayMotion(name){if(!['Static','Float','Bounce'].includes(name))return;overlayMotionLocal=name;if(name==='Static'){textMotion.value='Static'}else{textMotion.value='Static'}syncOverlayUI();textChanged()}
function syncOverlayUI(){
 let bt=document.getElementById('overlayModeText'),bi=document.getElementById('overlayModeIcon');if(bt)bt.classList.toggle('active',overlayTypeLocal==='Text');if(bi)bi.classList.toggle('active',overlayTypeLocal==='Icon');
 document.querySelectorAll('.overlayTextOnly').forEach(el=>el.classList.toggle('hidden',overlayTypeLocal!=='Text'));let ic=document.getElementById('overlayIconChooser');if(ic)ic.classList.toggle('hidden',overlayTypeLocal!=='Icon');
 ['Pixel','Quest','Block'].forEach(n=>{let b=document.getElementById('font'+n);if(b)b.classList.toggle('active',textFont.value===n)});
 ['Static','Float','Bounce'].forEach(n=>{let b=document.getElementById('overlayMotion'+n);if(b)b.classList.toggle('active',overlayMotionLocal===n)});
 renderOverlayIcons();
 let master=document.getElementById('textMaster');if(master)master.textContent='OVERLAY: '+(textEnabledLocal?'ON':'OFF');
}
const _overlayPayloadBase=textPayload;
textPayload=function(){let p=_overlayPayloadBase();p.overlay_type=overlayTypeLocal;p.overlay_icon=overlayIconLocal;p.overlay_motion=overlayMotionLocal;p.speed=textSpeeds[textSpeedLocal]||22;return p};
const _overlaySyncBase=syncTextUI;
syncTextUI=function(){_overlaySyncBase();let t=state.text||{};overlayTypeLocal=t.overlay_type||overlayTypeLocal||'Text';overlayIconLocal=t.overlay_icon||overlayIconLocal||'Heart';overlayMotionLocal=t.overlay_motion||overlayMotionLocal||'Static';if(!['Pixel','Quest','Block'].includes(textFont.value))textFont.value='Pixel';if(!textSpeedLocal)textSpeedLocal='Medium';syncOverlayUI()};
const _overlayTextMasterBase=syncTextMaster;
syncTextMaster=function(){_overlayTextMasterBase();syncOverlayUI()};
// Medium is the intended default whenever there is no saved text speed yet.
if(typeof textSpeedLocal!=='undefined'&&!textSpeedLocal)textSpeedLocal='Medium';
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
