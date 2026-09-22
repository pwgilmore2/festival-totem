import random

import phone_server
import performance_extras
import controller_state_ui
from overlay_engine import OverlayRenderer

_audio_modes = {"front": "Off", "back": "Off"}
_startup_seeded = False


def _side(seed):
    return "back" if int(seed or 0) >= 1000 else "front"


# Keep the legacy renderer compatible with the simplified text model.
_base_original_render = performance_extras._original_render


def _audio_render(renderer, display, settings, t, signals=None, seed=0, clear_background=True):
    st = dict(settings)
    st["audio_reactivity"] = _audio_modes[_side(seed)]
    st["glow"] = False
    st["wave"] = False
    st["glitch"] = False
    st["beat_pulse"] = False
    if st.get("color_mode") == "Audio":
        st["color_mode"] = "Rainbow"
    return _base_original_render(renderer, display, st, t, signals, seed, clear_background)


performance_extras._original_render = _audio_render


# The final-frame overlay compositor is the active text renderer. Inject the
# runtime-only audio mode here so phone controls and rendered text stay aligned.
_base_overlay_draw_text = OverlayRenderer.draw_text


def _overlay_draw_text(self, display, settings, t, signals=None, seed=0, bottom=False):
    st = dict(settings)
    st["audio_reactivity"] = _audio_modes[_side(seed)]
    st["glow"] = False
    st["wave"] = False
    st["glitch"] = False
    st["beat_pulse"] = False
    if st.get("color_mode") == "Audio":
        st["color_mode"] = "Rainbow"
    return _base_overlay_draw_text(self, display, st, t, signals, seed, bottom)


OverlayRenderer.draw_text = _overlay_draw_text


# Normalize incoming text commands. Text layout/speed/style are automatic now;
# only content, font, color, size and audio intensity remain user-facing.
_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    for data in commands:
        if not isinstance(data, dict):
            continue
        if data.get("command") == "set_target" and data.get("value") in ("front", "back", "both"):
            target = data.get("value")
        if data.get("command") in ("text_settings", "text_show", "text_refresh"):
            value = data.get("value")
            if isinstance(value, dict):
                value["motion"] = "Static"
                value["speed"] = 34.0
                value["glow"] = False
                value["wave"] = False
                value["glitch"] = False
                value["beat_pulse"] = False
                if value.get("color_mode") == "Audio":
                    value["color_mode"] = "Rainbow"
                mode = str(value.get("audio_reactivity", "Off"))
                if mode == "Intense":
                    mode = "Reactive"
                if mode not in ("Off", "Subtle", "Reactive"):
                    mode = "Off"
                value["audio_reactivity"] = mode
                sides = ("front", "back") if target == "both" else (target,)
                for side in sides:
                    _audio_modes[side] = mode
    return commands


controller_state_ui.PhoneControlServer.get_commands = _get_commands


_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    global _startup_seeded
    if isinstance(state, dict):
        state = dict(state)
        panels = dict(state.get("panels") or {})
        for side in ("front", "back"):
            panel = dict(panels.get(side) or {})
            text = dict(panel.get("text") or {})
            text["audio_reactivity"] = _audio_modes[side]
            text["motion"] = "Static"
            text["speed"] = 34.0
            text["glow"] = False
            text["wave"] = False
            text["glitch"] = False
            text["beat_pulse"] = False
            if text.get("color_mode") == "Audio":
                text["color_mode"] = "Rainbow"
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels
        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            text = dict(state["text"])
            text["audio_reactivity"] = _audio_modes.get(ref, "Off")
            text["motion"] = "Static"
            text["speed"] = 34.0
            text["glow"] = False
            text["wave"] = False
            text["glitch"] = False
            text["beat_pulse"] = False
            if text.get("color_mode") == "Audio":
                text["color_mode"] = "Rainbow"
            state["text"] = text

        if not _startup_seeded:
            library = list(state.get("library") or [])
            ids = [int(item.get("index")) for item in library if isinstance(item, dict) and item.get("index") is not None]
            if ids:
                _startup_seeded = True
                front = list(ids)
                back = list(ids)
                random.shuffle(front)
                random.shuffle(back)
                if len(ids) > 1 and front[0] == back[0]:
                    back[0], back[1] = back[1], back[0]
                self.add_command("set_target", "front")
                self.add_command("slideshow_start", {"indices": front, "duration": 10.0, "shuffle": False, "label": "All"})
                self.add_command("set_target", "back")
                self.add_command("slideshow_start", {"indices": back, "duration": 10.0, "shuffle": False, "label": "All"})
                self.add_command("set_target", "both")
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state

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
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

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

  const oldExtra=document.querySelector('.textMotionExtras select#textAudioMode');
  if(oldExtra){const oldBox=oldExtra.closest('.textMotionExtras');if(oldBox&&oldBox.id!=='textMotionExtras')oldBox.style.display='none'}

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
  return {message:textMessage.value,font:textFont.value,motion:'Static',color_mode:colorMode,color:textColor.value,scale,speed:34,wave:false,glow:false,glitch:false,beat_pulse:false,audio_reactivity:textAudioLocal,background:'Dimmed GIF',background_brightness:.30,backplate:true}
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
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
