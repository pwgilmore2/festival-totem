import base64
import io
import json

from PIL import Image

import phone_server
from icon_assets import ICON_LIBRARY


def _preview_data_urls():
    out = {}
    for asset in ICON_LIBRARY.assets:
        im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        px = im.load()
        for y, row in enumerate(asset.pixels):
            for x, rgba in enumerate(row):
                px[x, y] = tuple(rgba)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        out[asset.name] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return out


_CSS = r'''
<style>
.fontButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.fontButtons button{min-height:48px}.fontButtons button.active,.iconTile.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.iconSection{margin:10px 0 16px;padding:12px 0 14px;border-bottom:1px solid #ffffff16}.iconGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:9px 0 4px}.iconTile{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;min-height:112px;padding:8px}.iconTile canvas{width:72px;height:72px;image-rendering:pixelated}.iconTile span{font-size:11px;opacity:.8}.iconTile.active span{opacity:1;font-weight:700}
#textWaveToggle{display:none!important}.textMotionExtras{grid-template-columns:1fr!important}.overlayHint{font-size:11px;opacity:.66;line-height:1.35;margin-top:5px}.modeNotice{margin:7px 0 0;padding:8px 10px;border-radius:10px;background:#ffffff0b;font-size:11px;opacity:.72}
@media(max-width:520px){.iconGrid{grid-template-columns:repeat(2,1fr)}.iconTile{min-height:116px}.fontButtons{grid-template-columns:repeat(3,1fr)}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('id="tabText" onclick="view(\'text\')">Text</button>', 'id="tabText" onclick="view(\'text\')">Overlay</button>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('>Text</button>', '>Overlay</button>')
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('<h2>Text Engine</h2>', '<h2>Overlay</h2>')

_anchor = '<div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">OVERLAY: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div>'
if _anchor not in phone_server.PHONE_HTML:
    _anchor = '<div class="textTop"><button id="textMaster" class="textToggle" onclick="toggleTextMaster()">TEXT: OFF</button><button onclick="refreshText()">↻ APPLY SETTINGS</button></div>'
_insert = _anchor.replace('OVERLAY: OFF', 'TEXT: OFF') + r'''
<div class="iconSection"><div class="quickLabel">32×32 Icon Layer — tap an icon to show it, tap again to clear</div><div class="overlayHint">Icons render authored PNG pixels 1:1 and bounce by default. Full-size icons and text are currently exclusive.</div><div id="overlayIconGrid" class="iconGrid"></div><div id="iconModeNotice" class="modeNotice">Selecting an icon hides text. Showing text hides the full-size icon.</div></div>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_anchor, _insert, 1)

_font = '<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" onchange="textChanged()"></select></div>'
_font_new = r'''<div><div class="sh"><span>Font</span></div><select id="textFont" class="selectDark" style="display:none" onchange="textChanged()"></select><div class="fontButtons"><button id="fontPixel" onclick="setOverlayFont('Pixel')">Pixel</button><button id="fontQuest" onclick="setOverlayFont('Quest')">Quest</button><button id="fontBlock" onclick="setOverlayFont('Block')">Block</button></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_font, _font_new, 1)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('Quick text — tap once to fire it immediately', 'Quick text — tap once to show it')

_PREVIEWS_JSON = json.dumps(_preview_data_urls(), separators=(",", ":"))
_JS = r'''
<script>
let overlayIconLocal='',overlayIconEnabledLocal=false;
const overlayIconPreviews=__PREVIEWS__;
function drawIconPreview(canvas,name){
 const ctx=canvas.getContext('2d');canvas.width=32;canvas.height=32;ctx.clearRect(0,0,32,32);ctx.imageSmoothingEnabled=false;
 const src=overlayIconPreviews[name];if(!src)return;let img=new Image();img.onload=()=>{ctx.imageSmoothingEnabled=false;ctx.drawImage(img,0,0,32,32)};img.src=src;
}
function renderOverlayIcons(){
 const g=document.getElementById('overlayIconGrid');if(!g)return;const names=(state.overlay_icons||[]),sig=names.join('|');
 if(g.dataset.sig!==sig){g.dataset.sig=sig;g.innerHTML='';names.forEach(name=>{let b=document.createElement('button');b.className='iconTile';b.dataset.overlayIcon=name;b.onclick=()=>selectOverlayIcon(name);let c=document.createElement('canvas'),s=document.createElement('span');s.textContent=name;b.append(c,s);g.appendChild(b);drawIconPreview(c,name)})}
 document.querySelectorAll('[data-overlay-icon]').forEach(b=>b.classList.toggle('active',overlayIconEnabledLocal&&b.dataset.overlayIcon===overlayIconLocal));
}
function selectOverlayIcon(name){cmd('icon_toggle',name)}
function setOverlayFont(name){if(['Pixel','Quest','Block'].includes(name)){textFont.value=name;textChanged();syncOverlayUI()}}
function syncOverlayLabel(){
 const tab=document.getElementById('tabText');if(tab)tab.textContent=(overlayIconEnabledLocal||textEnabledLocal)?'Overlay ●':'Overlay';
 const card=document.querySelector('.textCard h2');if(card)card.textContent='Overlay';
}
function syncOverlayUI(){
 renderOverlayIcons();
 ['Pixel','Quest','Block'].forEach(n=>{let b=document.getElementById('font'+n);if(b)b.classList.toggle('active',textFont.value===n)});
 syncTextMaster();syncOverlayLabel();
 const wave=document.getElementById('textWaveToggle');if(wave)wave.style.display='none';
}

syncTextMaster=function(){let b=document.getElementById('textMaster');if(!b)return;b.textContent='TEXT: '+(textEnabledLocal?'ON':'OFF');b.classList.toggle('active',textEnabledLocal)};
toggleTextMaster=function(){
 textEnabledLocal=!textEnabledLocal;
 if(textEnabledLocal)cmd('text_show',textPayload());else cmd('text_hide');
 syncTextMaster();
};

const _overlaySyncBase=syncTextUI;
syncTextUI=function(){
 _overlaySyncBase();let t=state.text||{},i=state.icon||{};
 overlayIconLocal=i.icon||overlayIconLocal||'';overlayIconEnabledLocal=!!i.icon_enabled;textEnabledLocal=!!t.enabled;
 if(!['Pixel','Quest','Block'].includes(textFont.value))textFont.value='Pixel';if(!textSpeedLocal)textSpeedLocal='Medium';textWaveLocal=false;syncOverlayUI();
};
if(typeof textSpeedLocal!=='undefined'&&!textSpeedLocal)textSpeedLocal='Medium';
window.addEventListener('load',()=>{syncOverlayUI()});
</script>
'''.replace('__PREVIEWS__', _PREVIEWS_JSON)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
