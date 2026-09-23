"""State-driven controller status presentation.

This module is intentionally side-effect free: ``apply()`` transforms a supplied
controller document and the server class simply continues the base server.
Controller build order is owned by ``controller_ui.py``.
"""

import phone_server


_STATE_CSS = r'''
<style>
.textTop{display:none!important}
.quickText button.active,.customTextTile.active{background:linear-gradient(135deg,#00b86b,#00a8ff);box-shadow:0 0 0 2px #ffffff44 inset,0 0 18px #00b8ff33}
.customTextTile{grid-column:1/-1;min-height:58px!important;background:linear-gradient(135deg,#343442,#4b3f72)}
.tabs button.runtimeOn{box-shadow:0 0 0 2px #55ffb455 inset,0 0 14px #42ff9b33;background:#245447}
.tabs button.runtimeChaos{box-shadow:0 0 0 2px #ff67bd66 inset,0 0 16px #ff3f9d44;background:#5a2450}
.tabs button.beatHit{box-shadow:0 0 0 2px #ffffff88 inset,0 0 20px #ffffff77;filter:brightness(1.25)}
</style>
'''

_STATE_JS = r'''
<script>
function runtimeText(){return state.text||{}}
function runtimeTextEnabled(){return !!runtimeText().enabled}
function normalizedMessage(v){return String(v||'').trim()}
function activeQuickMessage(){return runtimeTextEnabled()?normalizedMessage(runtimeText().message):''}

function renderQuickPresets(){
  const active=activeQuickMessage();
  let q=document.getElementById('quickTextButtons');
  if(q){
    q.innerHTML='';
    quickPresets.forEach(msg=>{
      let b=document.createElement('button');
      b.textContent=msg;b.dataset.quickText=msg;
      b.classList.toggle('active',!!active&&active===normalizedMessage(msg));
      b.onclick=()=>toggleQuickText(msg);
      q.appendChild(b)
    });
    let custom=document.createElement('button');
    custom.id='customTextTile';custom.className='customTextTile';custom.textContent='CUSTOM';
    let isPreset=quickPresets.some(x=>normalizedMessage(x)===active);
    custom.classList.toggle('active',!!active&&!isPreset);
    custom.onclick=()=>toggleCustomText();q.appendChild(custom)
  }
  let p=document.getElementById('quickPresetList');
  if(p){
    p.innerHTML='';quickPresets.forEach((msg,i)=>{
      let row=document.createElement('div');row.className='presetManageRow';
      let s=document.createElement('span');s.textContent=msg;
      let b=document.createElement('button');b.textContent='Remove';b.onclick=()=>{quickPresets.splice(i,1);saveQuickPresets()};
      row.append(s,b);p.appendChild(row)
    });
    if(!quickPresets.length)p.innerHTML='<div class="muted">No quick text presets yet.</div>'
  }
}

function toggleQuickText(message){
  let msg=normalizedMessage(message),t=runtimeText();
  if(t.enabled&&normalizedMessage(t.message)===msg){cmd('text_hide');return}
  textMessage.value=msg;cmd('text_show',textPayload())
}
function toggleCustomText(){
  let msg=normalizedMessage(textMessage.value);if(!msg)return;
  let t=runtimeText(),isPreset=quickPresets.some(x=>normalizedMessage(x)===normalizedMessage(t.message));
  if(t.enabled&&!isPreset&&normalizedMessage(t.message)===msg){cmd('text_hide');return}
  cmd('text_show',textPayload())
}
function quickText(message){toggleQuickText(message)}
function toggleTextMaster(){if(runtimeTextEnabled())cmd('text_hide');else if(normalizedMessage(textMessage.value))cmd('text_show',textPayload())}
function refreshText(){if(runtimeTextEnabled())cmd('text_settings',textPayload())}

function textChanged(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd('text_settings',textPayload()),100)}

function syncTextUI(){
  let t=runtimeText();ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);
  if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;
  if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;
  if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;
  textScaleLocal=parseInt(t.scale??2);textSpeedLocal=speedName(t.speed);syncTextChoices();renderQuickPresets();syncTabStatus()
}

function syncTabStatus(){
  let a=state.audio||{},t=runtimeText(),g=state.guest||{};
  let ta=document.getElementById('tabAudio'),tt=document.getElementById('tabText'),tg=document.getElementById('tabGuest');
  if(ta){ta.classList.toggle('runtimeOn',!!a.fresh);ta.classList.toggle('beatHit',!!(a.fresh&&a.beat));ta.title=a.fresh?'Phone audio active':'Phone audio off'}
  if(tt){tt.classList.toggle('runtimeOn',!!t.enabled);tt.title=t.enabled?('Text active: '+normalizedMessage(t.message)):'Text off'}
  if(tg){tg.classList.toggle('runtimeChaos',!!g.active);tg.title=g.active?('Active: '+String(g.kind||'Chaos')):'Chaos idle'}
}
setInterval(syncTabStatus,120);
</script>
'''


def apply(html):
    html = html.replace('</head>', _STATE_CSS + '</head>', 1)
    html = html.replace('</body>', _STATE_JS + '</body>', 1)
    return html


PhoneControlServer = phone_server.PhoneControlServer
