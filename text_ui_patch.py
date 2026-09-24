"""Presentation transform for the simplified Text controller."""

_CSS = r'''<style>#textMotion{display:none!important}.textCard{background:radial-gradient(circle at 5% 0%,#ff4fa029,transparent 44%),radial-gradient(circle at 100% 0%,#5e67ff24,transparent 42%),#ffffff12}</style>'''

_JS = r'''
<script>
(function simplifyTextControls(){
  const style=document.getElementById('textStyle');
  if(style){const box=style.parentElement;if(box)box.style.display='none'}

  const colorMode=document.getElementById('textColorMode');
  if(colorMode){
    [...colorMode.options].forEach(o=>{if(o.value==='Audio'||o.textContent==='Audio')o.remove()});
    if(colorMode.value==='Audio')colorMode.value='Rainbow';
  }

  const duration=document.getElementById('duration');
  if(duration&&durationPending==null){duration.value='10';dv.textContent='10s'}

  const motion=document.getElementById('textMotion');
  if(motion){motion.value='Static';const box=motion.parentElement;if(box)box.style.display='none'}
  const fast=document.getElementById('textSpeedFast');
  if(fast){const choices=fast.closest('.choice3');const box=choices&&choices.parentElement;if(box)box.style.display='none'}
})();

styleFlags=function(){return {glow:false,glitch:false,beat_pulse:false,wave:false}};
styleFromState=function(){return 'Clean'};
textPayload=function(){
  const scaleEl=document.getElementById('textScale');
  const scale=Math.max(1,Math.min(3,parseInt(scaleEl?.value||textScaleLocal||1)));
  let colorMode=document.getElementById('textColorMode')?.value||'Rainbow';
  if(colorMode==='Audio')colorMode='Rainbow';
  return {message:textMessage.value,font:textFont.value,motion:'Static',color_mode:colorMode,color:textColor.value,scale,speed:34,wave:false,glow:false,glitch:false,beat_pulse:false,background_brightness:.65,backplate:true}
};
textChanged=function(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd('text_settings',textPayload()),25)};

const _textPolishSync=syncTextUI;
syncTextUI=function(){
  _textPolishSync();
  const t=state.text||{};
  const m=document.getElementById('textMotion');if(m)m.value='Static';
  textSpeedLocal='Fast';
  const colorMode=document.getElementById('textColorMode');
  if(colorMode){[...colorMode.options].forEach(o=>{if(o.value==='Audio'||o.textContent==='Audio')o.remove()});if(colorMode.value==='Audio')colorMode.value='Rainbow'}
  const scaleEl=document.getElementById('textScale');
  if(scaleEl&&document.activeElement!==scaleEl&&t.scale!=null){scaleEl.value=t.scale;const v=document.getElementById('textScaleValue');if(v)v.textContent=t.scale+'x'}
};
</script>
'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    html = html.replace('</body>', _JS + '</body>', 1)
    return html
