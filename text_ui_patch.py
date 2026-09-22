import math
import random

import phone_server
import performance_extras
from text_engine import parse_color, hsv_color, clamp01


def _static_auto(renderer, display, settings, t, signals, seed, clear_background):
    signals = signals or {}
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
            fallback["speed"] = min(8.0, float(settings.get("speed", 8.0)))
            performance_extras._original_render(renderer, display, fallback, t, signals, seed, clear_background=False)
            return

    if settings.get("beat_pulse") and beat:
        flash = .10 + bass * .18 + (.08 if audio_mode == "Reactive" else 0.0)
        renderer._beat_flash(display, flash)


performance_extras._draw_static_auto = _static_auto

_CSS = r'''
<style>
.textMotionExtras{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.textMotionExtras button{min-height:46px}
.textMotionExtras button.active{background:linear-gradient(135deg,#6c4cff,#00b8ff);box-shadow:0 0 0 2px #ffffff33 inset}
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
})();
function toggleTextWave(){textWaveLocal=!textWaveLocal;syncTextMotionExtras();textChanged()}
function syncTextMotionExtras(){
  const b=document.getElementById('textWaveToggle');
  if(b){b.textContent='↕ Vertical Wave: '+(textWaveLocal?'On':'Off');b.classList.toggle('active',textWaveLocal)}
}
styleFlags=function(){let s=textStyle.value;return {glow:s==='Glow'||s==='Rave',glitch:s==='Glitch',beat_pulse:s==='Beat Pulse'||s==='Rave'}};
styleFromState=function(t){if(t.glitch)return'Glitch';if(t.glow&&t.beat_pulse)return'Rave';if(t.glow)return'Glow';if(t.beat_pulse)return'Beat Pulse';return'Clean'};
textPayload=function(){return {message:textMessage.value,font:textFont.value,motion:textMotion.value,color_mode:textColorMode.value,color:textColor.value,scale:textScaleLocal,speed:textSpeeds[textSpeedLocal]||22,wave:textWaveLocal,audio_reactivity:(document.getElementById('textAudioMode')?.value||'Off'),background:'Dimmed GIF',background_brightness:.30,backplate:true,...styleFlags()}};
const _textPolishSync=syncTextUI;
syncTextUI=function(){
  _textPolishSync();
  const t=state.text||{};
  textWaveLocal=!!t.wave;
  const a=document.getElementById('textAudioMode');
  if(a&&document.activeElement!==a)a.value=t.audio_reactivity||'Off';
  syncTextMotionExtras();
};
</script>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</body>', _JS + '</body>', 1)
