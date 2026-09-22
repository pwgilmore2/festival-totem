"""Transition scope metadata used by the compositor.

Content transitions operate on the background/content buffer and leave overlays
stable. Scene transitions operate on the fully composed frame so icon and text
participate in the transition intentionally.
"""

CONTENT_SCOPE = "content"
SCENE_SCOPE = "scene"

TRANSITION_SCOPES = {
    # Standard slideshow transitions: background/content only.
    "None": CONTENT_SCOPE,
    "Fade": CONTENT_SCOPE,
    "Melt": CONTENT_SCOPE,
    "Dissolve": CONTENT_SCOPE,
    "Glitch": CONTENT_SCOPE,
    "Ripple": CONTENT_SCOPE,
    "Zoom": CONTENT_SCOPE,
    "Wipe": CONTENT_SCOPE,

    # Intense transitions. Morph behaves best as a content transformation;
    # the others intentionally move/distort the entire composed scene.
    "Morph": CONTENT_SCOPE,
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
