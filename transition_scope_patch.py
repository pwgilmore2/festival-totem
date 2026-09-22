"""Compositor-aware transition scoping.

This patch keeps the simulator loop simple while giving transitions two explicit
render scopes:
- content: run at the existing pre-overlay transition point
- scene: defer until OverlayRenderer has drawn text/icon

It also caches pre-overlay content and pre-guest scene frames so transition
sources do not accidentally include layers outside their scope.
"""

import visual_engine
from overlay_engine import OverlayRenderer
from transition_scopes import CONTENT_SCOPE, SCENE_SCOPE, transition_scope

_base_begin = visual_engine.TransitionManager.begin
_base_apply = visual_engine.TransitionManager.apply
_base_draw_icon = OverlayRenderer.draw_icon

_content_snapshots = {}
_scene_snapshots = {}
_scene_managers = {}


def _begin(self, display, kind="Fade", duration=0.8):
    scope = transition_scope(kind)
    key = id(display)
    result = _base_begin(self, display, kind, duration)
    self._transition_scope = scope

    if not getattr(self, "active", False):
        _scene_managers.pop(key, None)
        return result

    # Replace the source captured by TransitionManager with the last frame from
    # the correct compositor stage. This prevents content fades from carrying
    # old text/icons and keeps scene transitions free of Chaos/guest FX.
    cached = _scene_snapshots.get(key) if scope == SCENE_SCOPE else _content_snapshots.get(key)
    if cached is not None:
        self.source = [row[:] for row in cached]

    if scope == SCENE_SCOPE:
        _scene_managers[key] = self
    else:
        _scene_managers.pop(key, None)
    return result


def _apply(self, display):
    scope = getattr(self, "_transition_scope", transition_scope(getattr(self, "kind", "Fade")))
    key = id(display)

    if scope == SCENE_SCOPE and getattr(self, "active", False):
        # Scene transitions are applied after text/icon by _draw_icon below.
        return

    _base_apply(self, display)
    # This call occurs before reactive layers and overlays in simulator.py, so
    # it is a clean content-stage snapshot for the next content transition.
    _content_snapshots[key] = visual_engine.copy_pixels(display)


def _draw_icon(self, display, state, text_settings, t, signals=None, seed=0, text_enabled=False):
    # OverlayRenderer is called every frame even when no icon is selected, so
    # this is a reliable hook immediately after text/icon composition.
    result = _base_draw_icon(self, display, state, text_settings, t, signals, seed, text_enabled)
    key = id(display)
    manager = _scene_managers.get(key)
    if manager is not None and getattr(manager, "active", False):
        _base_apply(manager, display)
    elif manager is not None:
        _scene_managers.pop(key, None)

    # Snapshot before simulator.py applies guest/Chaos FX.
    _scene_snapshots[key] = visual_engine.copy_pixels(display)
    return result


visual_engine.TransitionManager.begin = _begin
visual_engine.TransitionManager.apply = _apply
OverlayRenderer.draw_icon = _draw_icon
