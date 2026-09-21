import phone_server
import performance_extras

# Final controller polish: one source of truth for text/chaos state, plus a compact
# global status strip that stays visible while moving between tabs.
_STATUS_CSS = r'''
<style>
.textTop{display:none!important}
.quickText button.active,.customTextTile.active{background:linear-gradient(135deg,#00b86b,#00a8ff);box-shadow:0 0 0 2px #ffffff44 inset,0 0 18px #00b8ff33}
.customTextTile{grid-column:1/-1;min-height:58px!important;background:linear-gradient(135deg,#343442,#4b3f72)}
.globalStatus{position:sticky;top:61px;z-index:19;display:flex;gap:7px;align-items:center;overflow-x:auto;padding:5px 2px 8px;background:#09090def;backdrop-filter:blur(10px);scrollbar-width:none}.globalStatus::-webkit-scrollbar{display:none}
.statusPill{flex:0 0 auto;display:flex;align-items:center;gap:6px;min-height:30px;padding:5px 9px;border-radius:999px;background:#ffffff0d;border:1px solid #ffffff12;font-size:11px;font-weight:700;opacity:.58;white-space:nowrap}.statusPill.on{opacity:1;background:#155d493f;border-color:#39e7a555}.statusPill.textOn{max-width:220px;background:#49307855;border-color:#9a79ff66}.statusPill.chaosOn{background:#7b1d5255;border-color:#ff4ca766}.statusDot{width:7px;height:7px;border-radius:50%;background:#666}.statusPill.on .statusDot{background:#63ffb5;box-shadow:0 0 9px #63ffb5}.statusPill.chaosOn .statusDot{background:#ff61bb;box-shadow:0 0 9px #ff61bb}.beatPulse{opacity:.45}.beatPulse.on{opacity:1;background:#ffffff22}.beatPulse.on .statusDot{background:#fff;box-shadow:0 0 12px #fff}
@media(max-width:520px){.globalStatus{top:61px}.statusPill.textOn{max-width:155px;overflow:hidden;text-overflow:ellipsis}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _STATUS_CSS + '</head>', 1)

_STATUS_HTML = r'''<div id="globalStatus" class="globalStatus"><div id="statusAudio" class="statusPill"><span class="statusDot"></span>Audio</div><div id="statusText" class="statusPill"><span class="statusDot"></span><span id="statusTextLabel">Text</span></div><div id="statusChaos" class="statusPill"><span class="statusDot"></span><span id="statusChaosLabel">Chaos</span></div><div id="statusBeat" class="statusPill beatPulse"><span class="statusDot"></span>Beat</div></div>'''
_target_card = '<div id="targetCard" class="card"><h2>Target</h2>'
if _target_card in phone_server.PHONE_HTML:
    phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(_target_card, _STATUS_HTML + _target_card, 1)

_STATE_JS = r'''
<script>
function runtimeText(){return state.text||{}}
function runtimeTextEnabled(){return !!runtimeText().enabled}
function normalizedMessage(v){return String(v||'').trim()}
function activeQuickMessage(){return runtimeTextEnabled()?normalizedMessage(runtimeText().message):''}

// Runtime state, not browser memory, decides whether text is on.
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

// Settings update immediately when text is active; when inactive they simply
// prepare the next tile press.
function textChanged(){clearTimeout(textTimer);textTimer=setTimeout(()=>cmd('text_settings',textPayload()),100)}

function syncTextUI(){
  let t=runtimeText();ensureOptions(textFont,state.text_fonts||[]);ensureOptions(textMotion,state.text_motions||[]);ensureOptions(textColorMode,state.text_color_modes||[]);
  if(document.activeElement!==textMessage&&t.message!=null)textMessage.value=t.message;
  if(document.activeElement!==textFont&&t.font)textFont.value=t.font;if(document.activeElement!==textMotion&&t.motion)textMotion.value=t.motion;
  if(document.activeElement!==textStyle)textStyle.value=styleFromState(t);if(document.activeElement!==textColorMode&&t.color_mode)textColorMode.value=t.color_mode;if(document.activeElement!==textColor&&t.color)textColor.value=t.color;
  textScaleLocal=parseInt(t.scale??2);textSpeedLocal=speedName(t.speed);syncTextChoices();renderQuickPresets();syncGlobalStatus()
}
function syncGlobalStatus(){
  let a=state.audio||{},t=runtimeText(),g=state.guest||{};
  let ap=document.getElementById('statusAudio'),tp=document.getElementById('statusText'),cp=document.getElementById('statusChaos'),bp=document.getElementById('statusBeat');
  if(ap)ap.classList.toggle('on',!!a.fresh);
  if(tp){tp.classList.toggle('on',!!t.enabled);tp.classList.toggle('textOn',!!t.enabled);let l=document.getElementById('statusTextLabel');if(l)l.textContent=t.enabled?('Text: '+normalizedMessage(t.message).slice(0,22)):'Text'}
  if(cp){cp.classList.toggle('on',!!g.active);cp.classList.toggle('chaosOn',!!g.active);let l=document.getElementById('statusChaosLabel');if(l)l.textContent=g.active?('Chaos: '+String(g.kind||'ON').replaceAll('_',' ')):'Chaos'}
  if(bp)bp.classList.toggle('on',!!(a.fresh&&a.beat))
}
setInterval(syncGlobalStatus,120);
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _STATE_JS + '</body>', 1)


class PhoneControlServer(performance_extras.PhoneControlServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_guest_kind = None

    def get_commands(self):
        commands = list(super().get_commands())
        for data in commands:
            if not isinstance(data, dict):
                continue
            command = data.get('command')
            value = data.get('value')
            if command == 'guest_action' and isinstance(value, dict):
                kind = str(value.get('kind', '')).lower()
                self._active_guest_kind = getattr(performance_extras, '_chaos_mode', None) or kind or None
            elif command == 'guest_xy':
                self._active_guest_kind = 'XY Pad'
            elif command == 'guest_stop':
                self._active_guest_kind = None
        return commands

    def update_state(self, state):
        if isinstance(state, dict):
            guest = dict(state.get('guest') or {})
            guest['active'] = bool(self._active_guest_kind)
            guest['kind'] = self._active_guest_kind
            state = dict(state)
            state['guest'] = guest
        return super().update_state(state)
