"""Transition scope metadata used by the compositor.

Background transitions operate on the image/content layer and leave overlays
steady. Full-scene transitions intentionally move the composed image + icon +
text together.
"""

CONTENT_SCOPE = "content"
SCENE_SCOPE = "scene"

TRANSITION_SCOPES = {
    # Background/slideshow transitions. These should never move Overlay.
    "None": CONTENT_SCOPE,
    "Fade": CONTENT_SCOPE,
    "Melt": CONTENT_SCOPE,
    "Dissolve": CONTENT_SCOPE,
    "Glitch": CONTENT_SCOPE,
    "Ripple": CONTENT_SCOPE,
    "Zoom": CONTENT_SCOPE,
    "Wipe": CONTENT_SCOPE,

    # Deliberate full-scene one-shot transitions. Keep this whole family
    # together so the controller UI has one simple rule: these move everything.
    "Morph": SCENE_SCOPE,
    "Spin": SCENE_SCOPE,
    "Rip": SCENE_SCOPE,
    "Slam": SCENE_SCOPE,
    "Bounce": SCENE_SCOPE,
    "Shatter": SCENE_SCOPE,
    "Vortex": SCENE_SCOPE,
    "Implode": SCENE_SCOPE,
}


def transition_scope(kind):
    return TRANSITION_SCOPES.get(str(kind), CONTENT_SCOPE)
