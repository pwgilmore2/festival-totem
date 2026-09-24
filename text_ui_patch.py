"""Presentation transform for the simplified Text controller."""

_CSS = r'''
<style>
#textMotion{display:none!important}
.textMotionExtras{display:block;margin-top:10px}
.textAudioButtons{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:7px}
.textAudioButtons button{min-height:48px;font-size:13px}
.textAudioButtons button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
@media(max-width:520px){.textAudioButtons{grid-template-columns:repeat(3,1fr)}}
</style>
'''

_JS = r'''
<script>
let textAudioLocal='Off';
(function simplifyTextControls(){
  const style=document.getElementById('textStyle');
  if(style){const box=style.parentElement;if(box)box.style.display='none'}

  const colorMode=document.getElementById('textColorMode');
  if(colorMode){
    [...colorMode.options].forEach(o=>{if(o.value==='Audio'||o.textContent==='Audio')o.remove()});
    if(colorMode.value==='Audio')colorMode.value='Rainbow';
  }

  const row=style?.closest('.textGrid');
  if(row&&!document.getElementById('textMotionExtras')){
    const extra=document.createElement('div');
    extra.id='textMotionExtras';
    extra.className='textMotionExtras';
    extra.innerHTML='<div class="sh"><span>Audio Reactivity</span><span class="tiny">uses the live music response</span></div><div class="textAudioButtons"><button id="textAudioOff" onclick="setTextAudio(\'Off\')">Off</button><button id="textAudioSubtle" onclick="setTextAudio(\'Subtle\')">Subtle</button><button id="textAudioIntense" onclick="setTextAudio(\'Reactive\')">Intense</button></div>';
    row.insertAdjacentElement('afterend',extra);
  }

  const duration=document.getElementById('duration');
  if(duration&&durationPending==null){duration.value='10';dv.textContent='10s'}

  const motion=document.getElementById('textMotion');
  if(motion){motion.value='Static';const box=motion.parentElement;if(box)box.style.display='none'}
  const fast=document.getElementById('textSpeedFast');
  if(fast){const choices=fast.closest('.choice3');const box=choices&&choices.parentElement;if(box)box.style.display='none'}
})();

window.setTextAudio=function(mode){
  textAudioLocal=['Off','Subtle','Reactive'].includes(mode)?mode:'Off';
  syncTextAudioButtons();
  textChanged();
};
function syncTextAudioButtons(){
  const map={Off:'textAudioOff',Subtle:'textAudioSubtle',Reactive:'textAudioIntense'};
  Object.entries(map).forEach(([mode,id])=>{const b=document.getElementById(id);if(b)b.classList.toggle('active',textAudioLocal===mode)});
}

styleFlags=function(){return {glow:false,glitch:false,beat_pulse:false,wave:false}};
styleFromState=function(){return 'Clean'};
textPayload=function(){
  const scaleEl=document.getElementById('textScale');
  const scale=Math.max(1,Math.min(3,parseInt(scaleEl?.value||textScaleLocal||1)));
  let colorMode=document.getElementById('textColorMode')?.value||'Rainbow';
  if(colorMode==='Audio')colorMode='Rainbow';
  return {message:textMessage.value,font:textFont.value,motion:'Static',color_mode:colorMode,color:textColor.value,scale,speed:34,wave:false,glow:false,glitch:false,beat_pulse:false,audio_reactivity:textAudioLocal,background:'Dimmed GIF',background_brightness:.65,backplate:true}
};
textChanged=function(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd('text_settings',textPayload()),25)};

const _textPolishSync=syncTextUI;
syncTextUI=function(){
  _textPolishSync();
  const t=state.text||{};
  textAudioLocal=(t.audio_reactivity==='Reactive')?'Reactive':(t.audio_reactivity==='Subtle'?'Subtle':'Off');
  const m=document.getElementById('textMotion');if(m)m.value='Static';
  textSpeedLocal='Fast';
  const colorMode=document.getElementById('textColorMode');
  if(colorMode){[...colorMode.options].forEach(o=>{if(o.value==='Audio'||o.textContent==='Audio')o.remove()});if(colorMode.value==='Audio')colorMode.value='Rainbow'}
  const scaleEl=document.getElementById('textScale');
  if(scaleEl&&document.activeElement!==scaleEl&&t.scale!=null){scaleEl.value=t.scale;const v=document.getElementById('textScaleValue');if(v)v.textContent=t.scale+'x'}
  syncTextAudioButtons();
};
window.addEventListener('load',syncTextAudioButtons);
</script>
'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    html = html.replace('</body>', _JS + '</body>', 1)
    return html
