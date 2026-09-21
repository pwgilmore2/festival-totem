import phone_server
import performance_phone_server

# The legacy base poller still writes to these elements. Keep tiny hidden stubs so
# the visible Now Playing card can stay removed without breaking update().
_HIDDEN = '''<div style="display:none" aria-hidden="true"><button id="fav"></button><div id="now"></div><div id="info"></div><div id="summary"></div><div id="show"></div></div>'''
if 'id="now"' not in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _HIDDEN + '</body>', 1)

_TOUCH_CSS = r'''
<style>
/* Thumb-friendly range controls: large grab area, precise visual track. */
input[type=range]{-webkit-appearance:none;appearance:none;height:46px;margin:2px 0;padding:0;background:transparent;touch-action:none;-webkit-tap-highlight-color:transparent}
input[type=range]::-webkit-slider-runnable-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;margin-top:-10px;box-shadow:0 2px 10px #0008}
input[type=range]::-moz-range-track{height:8px;border-radius:999px;background:#ffffff26}
input[type=range]::-moz-range-thumb{width:28px;height:28px;border-radius:50%;background:#8b7cff;border:3px solid #fff;box-shadow:0 2px 10px #0008}
.textSizeButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}.textSizeButtons button{min-height:56px;font-size:18px}.textSizeButtons button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
.textBgToggle{width:100%;margin:10px 0 2px;min-height:52px}.textBgToggle.active{background:linear-gradient(135deg,#6c4cff,#00b8ff)}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _TOUCH_CSS + '</head>', 1)

_OLD_SIZE = r'''<div class="textGrid"><div class="slider"><div class="sh"><span>Size</span><span id="textScaleValue">1x</span></div><input id="textScale" type="range" min="1" max="3" step="1" value="1" oninput="textScaleValue.textContent=this.value+'x';textChanged()"></div><div class="slider"><div class="sh"><span>Speed</span><span id="textSpeedValue">12</span></div><input id="textSpeed" type="range" min="1" max="40" step="1" value="12" oninput="textSpeedValue.textContent=this.value;textChanged()"></div></div>'''
_NEW_SIZE = r'''<div class="textGrid"><div><div class="sh"><span>Size</span></div><div class="textSizeButtons"><button id="textSize1" onclick="setTextSize(1)">1×</button><button id="textSize2" onclick="setTextSize(2)">2×</button><button id="textSize3" onclick="setTextSize(3)">3×</button></div></div><div class="slider"><div class="sh"><span>Speed</span><span id="textSpeedValue">12</span></div><input id="textSpeed" type="range" min="1" max="40" step="1" value="12" oninput="textSpeedValue.textContent=this.value;textChanged()"></div></div>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_OLD_SIZE, _NEW_SIZE, 1)

_BG_NEEDLE = r'''<div class="textBgBox"><div class="sh"><span>Background</span><span class="tiny">GIF brightness capped at 55%</span></div><select id="textBackground" class="selectDark" onchange="textChanged()"></select>'''
_BG_REPLACEMENT = r'''<div class="textBgBox"><div class="sh"><span>Background</span><span class="tiny">GIF brightness capped at 55%</span></div><button id="textBgSlideshow" class="textBgToggle active" onclick="toggleTextBgSlideshow()">♫ Background Slideshow: On</button><select id="textBackground" class="selectDark" onchange="textBackgroundChanged()"></select>'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_BG_NEEDLE, _BG_REPLACEMENT, 1)

_TOUCH_JS = r'''
<script>
let textScaleLocal=1,textBgSlideshowLocal=true;
function setTextSize(v){textScaleLocal=Math.max(1,Math.min(3,parseInt(v)||1));syncTextSizeButtons();textChanged()}
function syncTextSizeButtons(){[1,2,3].forEach(v=>{let b=document.getElementById('textSize'+v);if(b)b.classList.toggle('active',v===textScaleLocal)})}
function textIsLive(){let p=state.panels||{};if(state.target==='front')return p.front?.effect==='Text';if(state.target==='back')return p.back?.effect==='Text';return p.front?.effect==='Text'&&p.back?.effect==='Text'}
function textBackgroundChanged(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd(textIsLive()?'text_show':'text_settings',textPayload()),80)}
function toggleTextBgSlideshow(){textBgSlideshowLocal=!textBgSlideshowLocal;syncTextBgSlideshow();textBackgroundChanged()}
function syncTextBgSlideshow(){let b=document.getElementById('textBgSlideshow');if(!b)return;b.textContent='♫ Background Slideshow: '+(textBgSlideshowLocal?'On':'Off');b.classList.toggle('active',textBgSlideshowLocal)}
function textPayload(){return {message:textMessage.value,font:textFont.value,motion:textMotion.value,color_mode:textColorMode.value,color:textColor.value,scale:textScaleLocal,speed:parseFloat(textSpeed.value),background:textBackground.value,background_brightness:parseFloat(textBgBrightness.value),background_slideshow:textBgSlideshowLocal,backplate:textBackplateLocal,...styleFlags()}}
function syncTextUI(){let t=state.text||{};ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);ensureOptions(textBackground,state.text_backgrounds||[]);if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;if(document.activeElement!==textBackground&&t.background)textBackground.value=t.background;if(document.activeElement!==textSpeed&&t.speed!=null)textSpeed.value=t.speed;if(document.activeElement!==textBgBrightness&&t.background_brightness!=null)textBgBrightness.value=t.background_brightness;textScaleLocal=parseInt(t.scale??1);textBgSlideshowLocal=t.background_slideshow!==false;textBackplateLocal=!!t.backplate;textSpeedValue.textContent=Math.round(t.speed??12);pct('textBgValue',t.background_brightness??.28);textBackplate.classList.toggle('active',textBackplateLocal);syncTextSizeButtons();syncTextBgSlideshow()}
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _TOUCH_JS + '</body>', 1)

PhoneControlServer = performance_phone_server.PhoneControlServer
