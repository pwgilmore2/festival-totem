import math
import random

import phone_server
import performance_extras
import controller_state_ui
from text_engine import parse_color, hsv_color, clamp01

_audio_modes = {"front": "Off", "back": "Off"}
_startup_seeded = False


def _side(seed):
    return "back" if int(seed or 0) >= 1000 else "front"


_base_original_render = performance_extras._original_render


def _audio_render(renderer, display, settings, t, signals=None, seed=0, clear_background=True):
    st = dict(settings)
    st["audio_reactivity"] = _audio_modes[_side(seed)]
    return _base_original_render(renderer, display, st, t, signals, seed, clear_background)


performance_extras._original_render = _audio_render


def _static_auto(renderer, display, settings, t, signals, seed, clear_background):
    signals = signals or {}
    settings = dict(settings)
    settings["audio_reactivity"] = _audio_modes[_side(seed)]
    text = str(settings.get("message", "") or " ").upper()[:120]
    font = settings.get("font", "Pixel")
    color_mode = settings.get("color_mode", "Rainbow")
    requested_scale = max(1, min(3, int(settings.get("scale", 1))))
    beat = bool(signals.get("beat", False))
    bass = clamp01(signals.get("bass", 0.0))
    mids = clamp01(signals.get("mids", 0.0))
    highs = clamp01(signals.get("highs", 0.0))
    audio_mode = settings.get("audio_reactivity", "Off")

    if clear_background:
        display.clear()

    scale = requested_scale
    while scale > 1 and renderer.text_width(text, scale, font) > renderer.width - 4:
        scale -= 1

    pulse = 1.35 if settings.get("beat_pulse") and beat else 1.0
    if audio_mode == "Subtle":
        pulse = max(pulse, 1.0 + bass * .08)
    elif audio_mode == "Reactive":
        pulse = max(pulse, 1.0 + bass * .18 + (.12 if beat else 0.0))

    base = parse_color(settings.get("color", "#ffffff"))
    if color_mode == "Audio":
        base = hsv_color(210 + mids * 130 + bass * 30, .85, .65 + .35 * max(bass, mids, highs))
    elif audio_mode == "Reactive" and mids > .08:
        tint = hsv_color(260 + mids * 120, .72, 1.0)
        mix = mids * .24
        base = tuple(int(base[i] * (1.0 - mix) + tint[i] * mix) for i in range(3))

    vertical = 0
    if settings.get("wave"):
        vertical += int(round(math.sin(t * 3.8) * 2.0))
    if audio_mode == "Subtle":
        vertical += int(round(math.sin(t * 5.1) * bass * 1.6))
        if beat:
            vertical -= 1
    elif audio_mode == "Reactive":
        vertical += int(round(math.sin(t * 6.0) * bass * 3.2))
        if beat:
            vertical -= 2

    def draw_line(line, x, y, line_scale):
        width = renderer.text_width(line, line_scale, font)
        if settings.get("backplate"):
            renderer._backplate(display, x, y, width, 7 * line_scale)
        if settings.get("glow"):
            glow_strength = .22
            if audio_mode == "Subtle":
                glow_strength += bass * .06
            elif audio_mode == "Reactive":
                glow_strength += bass * .16 + highs * .08
            glow = tuple(min(255, int(c * glow_strength)) for c in base)
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                renderer._draw_text(display, line, x + ox, y + oy, glow, line_scale, font, color_mode, t, pulse)
        renderer._draw_text(display, line, x, y, base, line_scale, font, color_mode, t, pulse)

    width = renderer.text_width(text, scale, font)
    if width <= renderer.width - 4:
        x = (renderer.width - width) // 2
        y = (renderer.height - 7 * scale) // 2 + vertical
        draw_line(text, x, y, scale)
    else:
        lines = performance_extras._split_two_lines(renderer, text, font)
        if lines:
            a, b = lines
            gap = 3
            total_h = 7 + gap + 7
            y1 = (renderer.height - total_h) // 2 + vertical
            y2 = y1 + 7 + gap
            draw_line(a, (renderer.width - renderer.text_width(a, 1, font)) // 2, y1, 1)
            draw_line(b, (renderer.width - renderer.text_width(b, 1, font)) // 2, y2, 1)
        else:
            fallback = dict(settings)
            fallback["motion"] = "Scroll Left"
            fallback["scale"] = 1
            fallback["speed"] = 34.0
            performance_extras._original_render(renderer, display, fallback, t, signals, seed, clear_background=False)
            return

    if settings.get("beat_pulse") and beat:
        flash = .10 + bass * .18 + (.08 if audio_mode == "Reactive" else 0.0)
        renderer._beat_flash(display, flash)


performance_extras._draw_static_auto = _static_auto


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
                mode = str(value.get("audio_reactivity", "Off"))
                if mode not in ("Off", "Subtle", "Reactive"):
                    mode = "Off"
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
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels
        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            t = dict(state["text"])
            t["audio_reactivity"] = _audio_modes.get(ref, "Off")
            t["motion"] = "Static"
            t["speed"] = 34.0
            state["text"] = t

        if not _startup_seeded:
            library = list(state.get("library") or [])
            ids = [int(item.get("index")) for item in library if isinstance(item, dict) and item.get("index") is not None]
            if ids:
                _startup_seeded = True
                front = list(ids); back = list(ids)
                random.shuffle(front); random.shuffle(back)
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
.textMotionExtras{display:grid;grid-template-columns:1fr;gap:8px;margin-top:10px}
.textMotionExtras button{min-height:46px}
.textMotionExtras button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
#textMotion{display:none!important}
@media(max-width:520px){.textMotionExtras{grid-template-columns:1fr}}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

_JS = r'''
<script>
let textWaveLocal=false;
(function setupTextMotionExtras(){
  const style=document.getElementById('textStyle');
  if(style){
    [...style.options].forEach(o=>{if(o.value==='Wave'||o.textContent==='Wave')o.remove()});
    const row=style.closest('.textGrid');
    if(row&&!document.getElementById('textMotionExtras')){
      const extra=document.createElement('div');extra.id='textMotionExtras';extra.className='textMotionExtras';
      extra.innerHTML='<button id="textWaveToggle" onclick="toggleTextWave()">↕ Vertical Wave: Off</button><div><div class="sh"><span>Audio Reactivity</span></div><select id="textAudioMode" class="selectDark" onchange="textChanged()"><option>Off</option><option>Subtle</option><option>Reactive</option></select></div>';
      row.insertAdjacentElement('afterend',extra);
    }
  }
  const duration=document.getElementById('duration');
  if(duration&&durationPending==null){duration.value='10';dv.textContent='10s'}

  // Keep legacy elements alive for older polling code, but remove the choices
  // from the performance UI. Layout and scroll speed are automatic now.
  const motion=document.getElementById('textMotion');
  if(motion){motion.value='Static';const box=motion.parentElement;if(box)box.style.display='none'}
  const fast=document.getElementById('textSpeedFast');
  if(fast){const choices=fast.closest('.choice3');const box=choices&&choices.parentElement;if(box)box.style.display='none'}
})();
function toggleTextWave(){textWaveLocal=!textWaveLocal;syncTextMotionExtras();textChanged()}
function syncTextMotionExtras(){
  const b=document.getElementById('textWaveToggle');
  if(b){b.textContent='↕ Vertical Wave: '+(textWaveLocal?'On':'Off');b.classList.toggle('active',textWaveLocal)}
}
styleFlags=function(){let s=textStyle.value;return {glow:s==='Glow'||s==='Rave',glitch:s==='Glitch',beat_pulse:s==='Beat Pulse'||s==='Rave'}};
styleFromState=function(t){if(t.glitch)return'Glitch';if(t.glow&&t.beat_pulse)return'Rave';if(t.glow)return'Glow';if(t.beat_pulse)return'Beat Pulse';return'Clean'};
textPayload=function(){return {message:textMessage.value,font:textFont.value,motion:'Static',color_mode:textColorMode.value,color:textColor.value,scale:textScaleLocal,speed:34,wave:textWaveLocal,audio_reactivity:(document.getElementById('textAudioMode')?.value||'Off'),background:'Dimmed GIF',background_brightness:.30,backplate:true,...styleFlags()}};
const _textPolishSync=syncTextUI;
syncTextUI=function(){
  _textPolishSync();
  const t=state.text||{};
  textWaveLocal=!!t.wave;
  const a=document.getElementById('textAudioMode');
  if(a&&document.activeElement!==a)a.value=t.audio_reactivity||'Off';
  const m=document.getElementById('textMotion');if(m)m.value='Static';
  textSpeedLocal='Fast';
  syncTextMotionExtras();
};
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
