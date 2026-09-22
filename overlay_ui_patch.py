import base64
import io

import phone_server
from PIL import Image
from icon_assets import ICON_LIBRARY

_CSS = r'''
<style>
.fontButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.fontButtons button{min-height:48px}.fontButtons button.active,.iconTile.active,.iconMotionGrid button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.iconCard{background:radial-gradient(circle at 15% 0%,#ff3d9a22,transparent 38%),radial-gradient(circle at 95% 5%,#00e5ff20,transparent 40%),#ffffff12}.iconGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:9px 0 4px}.iconTile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-height:112px;padding:8px}.iconTile img{width:72px;height:72px;object-fit:contain;image-rendering:pixelated}.iconTile span{font-size:11px;opacity:.8}.iconTile.active span{opacity:1;font-weight:700}
#textWaveToggle{display:none!important}.textMotionExtras{grid-template-columns:1fr!important}.iconHint{font-size:11px;opacity:.68;line-height:1.4;margin:5px 0 10px}.modeNotice{margin:9px 0 0;padding:9px 10px;border-radius:10px;background:#ffffff0b;font-size:11px;opacity:.74}
.iconControls{margin-top:12px;padding-top:12px;border-top:1px solid #ffffff16}.iconMotionGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:7px 0 10px}.iconMotionGrid button{min-height:48px;font-size:14px}.iconFadeNote{font-size:11px;opacity:.64;line-height:1.4;margin:3px 0 10px}.iconActions{display:grid;grid-template-columns:1fr;gap:8px;margin-top:8px}
@media(max-width:520px){.iconGrid{grid-template-columns:repeat(2,1fr)}.iconTile{min-height:116px}.fontButtons{grid-template-columns:repeat(3,1fr)}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('id="tabText" onclick="view(\'text\')">Overlay</button>', 'id="tabText" onclick="view(\'text\')">Text</button>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('id="tabText" onclick="view(\'text\')">Text</button>', 'id="tabText" onclick="view(\'text\')">Text</button><button id="tabIcons" onclick="view(\'icons\')">Icons</button>', 1)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<div class="card textCard"><h2>Overlay</h2>', '<div class="card textCard"><h2>Text</h2>')

_font = '<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" onchange="textChanged()"></select></div>'
_font_new = r'''<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="fontButtons"><button id="fontPixel" onclick="setOverlayFont('Pixel')">Pixel</button><button id="fontQuest" onclick="setOverlayFont('Quest')">Quest</button><button id="fontBlock" onclick="setOverlayFont('Block')">Block</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_font, _font_new, 1)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('Quick text — tap once to fire it immediately', 'Quick text — tap once to show it')


def _icon_preview_data():
    out = {}
    for asset in ICON_LIBRARY.assets:
        im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        px = im.load()
        for y, row in enumerate(asset.pixels):
            for x, rgba in enumerate(row):
                px[x, y] = tuple(rgba)
        buf = io.BytesIO()
        im.save(buf, format='PNG', optimize=True)
        out[asset.name] = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    return out


_ICON_PREVIEWS = _icon_preview_data()
_ICONS_SECTION = r'''
<section id="icons" class="view"><div class="card iconCard"><h2>Icons</h2>
<div class="iconHint">32×32 PNG assets render 1:1. Tap an icon to show it; tap the active icon again to clear it.</div>
<div id="overlayIconGrid" class="iconGrid"></div>
<div class="iconControls">
<div class="sh"><span>Motion</span><span class="tiny">whole-pixel movement only</span></div>
<div id="iconMotionGrid" class="iconMotionGrid"></div>
<div class="iconFadeNote">Icons automatically dissolve + fade in when shown and dissolve + fade out when cleared.</div>
<div class="iconActions"><button onclick="cmd('icon_clear')">CLEAR ICON</button></div>
</div>
<div class="modeNotice">Full-size icons and text are currently exclusive: selecting an icon hides text, and showing text hides the icon.</div>
</div></section>
'''
if '<section id="edit" class="view">' in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<section id="edit" class="view">', _ICONS_SECTION + '<section id="edit" class="view">', 1)
else:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _ICONS_SECTION + '</body>', 1)

import json
_PREVIEWS_JSON = json.dumps(_ICON_PREVIEWS, separators=(',', ':'))
_JS = r'''
<script>
let overlayIconLocal='',overlayIconEnabledLocal=false;
const iconPreviews=__PREVIEWS__;

function renderOverlayIcons(){
 const g=document.getElementById('overlayIconGrid');if(!g)return;
 const names=(state.overlay_icons||[]),sig=names.join('|');
 if(g.dataset.sig!==sig){g.dataset.sig=sig;g.innerHTML='';names.forEach(name=>{let b=document.createElement('button');b.className='iconTile';b.dataset.overlayIcon=name;b.onclick=()=>selectOverlayIcon(name);let im=document.createElement('img');im.alt=name;im.src=iconPreviews[name]||'';let s=document.createElement('span');s.textContent=name;b.append(im,s);g.appendChild(b)})}
 document.querySelectorAll('[data-overlay-icon]').forEach(b=>b.classList.toggle('active',overlayIconEnabledLocal&&b.dataset.overlayIcon===overlayIconLocal));
}
function selectOverlayIcon(name){cmd('icon_toggle',name)}
function setOverlayFont(name){if(['Pixel','Quest','Block'].includes(name)){textFont.value=name;textChanged();syncSplitUI()}}
function renderIconMotion(){const g=document.getElementById('iconMotionGrid');if(!g)return;const items=state.icon_motions||['Bounce','Orbit'];let sig=items.join('|');if(g.dataset.sig!==sig){g.dataset.sig=sig;g.innerHTML='';items.forEach(n=>{let b=document.createElement('button');b.textContent=n;b.dataset.iconMotion=n;b.onclick=()=>cmd('icon_motion',n);g.appendChild(b)})}let motion=(state.icon||{}).motion||'Bounce';document.querySelectorAll('[data-icon-motion]').forEach(b=>b.classList.toggle('active',b.dataset.iconMotion===motion))}
function syncIconControls(){renderIconMotion()}

const _iconsBaseView=view;
view=function(n){if(n==='icons'){document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('active'));const panel=document.getElementById('icons'),tab=document.getElementById('tabIcons');if(panel)panel.classList.add('active');if(tab)tab.classList.add('active');const tc=document.getElementById('targetCard');if(tc)tc.style.display='';renderOverlayIcons();syncIconControls();return}_iconsBaseView(n);const panel=document.getElementById('icons'),tab=document.getElementById('tabIcons');if(panel)panel.classList.remove('active');if(tab)tab.classList.remove('active')}

function syncSplitTabs(){const tt=document.getElementById('tabText'),ti=document.getElementById('tabIcons');if(tt){tt.textContent=textEnabledLocal?'Text ●':'Text';tt.classList.toggle('runtimeOn',!!textEnabledLocal)}if(ti){ti.textContent=overlayIconEnabledLocal?'Icons ●':'Icons';ti.classList.toggle('runtimeOn',!!overlayIconEnabledLocal)}const card=document.querySelector('.textCard h2');if(card)card.textContent='Text'}
function syncSplitUI(){renderOverlayIcons();syncIconControls();['Pixel','Quest','Block'].forEach(n=>{let b=document.getElementById('font'+n);if(b)b.classList.toggle('active',textFont.value===n)});syncTextMaster();syncSplitTabs();const wave=document.getElementById('textWaveToggle');if(wave)wave.style.display='none'}

syncTextMaster=function(){let b=document.getElementById('textMaster');if(!b)return;b.textContent='TEXT: '+(textEnabledLocal?'ON':'OFF');b.classList.toggle('active',textEnabledLocal)};
toggleTextMaster=function(){textEnabledLocal=!textEnabledLocal;if(textEnabledLocal)cmd('text_show',textPayload());else cmd('text_hide');syncTextMaster()};

const _splitSyncBase=syncTextUI;
syncTextUI=function(){_splitSyncBase();let t=state.text||{},i=state.icon||{};overlayIconLocal=i.icon||overlayIconLocal||'';overlayIconEnabledLocal=!!i.icon_enabled;textEnabledLocal=!!t.enabled;if(!['Pixel','Quest','Block'].includes(textFont.value))textFont.value='Pixel';if(!textSpeedLocal)textSpeedLocal='Medium';textWaveLocal=false;syncSplitUI()};
setInterval(syncSplitTabs,150);setInterval(syncIconControls,220);
window.addEventListener('load',()=>{syncSplitUI()});
</script>
'''.replace('__PREVIEWS__', _PREVIEWS_JSON)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
