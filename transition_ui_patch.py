"""Make transition scope obvious in the phone controller."""

import phone_server

_CSS = r'''
<style>
.transitionScopeNote{margin:8px 0 10px;padding:9px 11px;border-radius:11px;font-size:11px;line-height:1.35;background:#ffffff0d;border:1px solid #ffffff18}
.transitionScopeNote strong{display:block;font-size:12px;letter-spacing:.06em;margin-bottom:2px}
.transitionScopeNote.background{box-shadow:inset 3px 0 #39a8ff}
.transitionScopeNote.scene{box-shadow:inset 3px 0 #ff4f9a}
/* controller_state_ui still updates the legacy text label every 120ms. Keep
   its runtime class/status behavior, but make the visible label stable. */
#tabText{font-size:0!important}
#tabText:after{content:'Overlay';font-size:14px}
#tabText.runtimeOn:after{content:'Overlay ●'}
</style>
'''
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace('</head>', _CSS + '</head>', 1)

# Normal slideshow transitions are background/content only.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    '<h2>Slideshow + Transitions</h2>',
    '<h2>Slideshow + Background Transitions</h2>',
)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    '<div class="transitionGrid">',
    '<div class="transitionScopeNote background"><strong>BACKGROUND ONLY</strong>Changes the GIF/image underneath. Overlay icons and text stay steady.</div><div class="transitionGrid">',
    1,
)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    '<span>Transition</span>', '<span>Background transition</span>', 1
)

# Deliberate intense transitions are full-scene by definition.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    'Intense → Next', 'Full Scene → Next'
)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    'one-shot transition to the next GIF',
    'image + icon + text move together',
)
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    'deliberate hold • both panels • one-shot transition',
    'deliberate hold • both panels • image + overlay',
)

# Make the Chaos one-shot melt unambiguous too.
phone_server.PHONE_HTML = phone_server.PHONE_HTML.replace(
    'PIXEL MELT → NEXT', 'BACKGROUND MELT → NEXT'
)
