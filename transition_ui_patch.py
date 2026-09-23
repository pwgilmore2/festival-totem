"""Presentation transform that makes transition scope obvious."""

_CSS = r'''
<style>
.transitionScopeNote{margin:8px 0 10px;padding:9px 11px;border-radius:11px;font-size:11px;line-height:1.35;background:#ffffff0d;border:1px solid #ffffff18}
.transitionScopeNote strong{display:block;font-size:12px;letter-spacing:.06em;margin-bottom:2px}
.transitionScopeNote.background{box-shadow:inset 3px 0 #39a8ff}
.transitionScopeNote.scene{box-shadow:inset 3px 0 #ff4f9a}
</style>
'''


def apply(html):
    html = html.replace('</head>', _CSS + '</head>', 1)
    html = html.replace(
        '<h2>Slideshow + Transitions</h2>',
        '<h2>Slideshow + Background Transitions</h2>',
    )
    html = html.replace(
        '<div class="transitionGrid">',
        '<div class="transitionScopeNote background"><strong>BACKGROUND ONLY</strong>Changes the GIF/image underneath. Icons and text stay steady.</div><div class="transitionGrid">',
        1,
    )
    html = html.replace(
        '<span>Transition</span>', '<span>Background transition</span>', 1
    )
    html = html.replace('Intense → Next', 'Full Scene → Next')
    html = html.replace(
        'one-shot transition to the next GIF',
        'image + icon + text move together',
    )
    html = html.replace(
        'deliberate hold • both panels • one-shot transition',
        'deliberate hold • both panels • image + icon + text',
    )
    html = html.replace('PIXEL MELT → NEXT', 'BACKGROUND MELT → NEXT')
    return html
