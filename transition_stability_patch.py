"""Make transition timing deterministic and one-shot intense routing non-sticky.

This deliberately runs after performance_extras/intense/scope patches.
"""

import time

import controller_state_ui
import performance_extras
import visual_engine
from transition_scopes import SCENE_SCOPE, transition_scope

# Performance FX should never pause or stretch transition clocks. Restore the
# original update implementation captured before performance_extras patched it.
if hasattr(performance_extras, "_original_transition_update"):
    visual_engine.TransitionManager.update = performance_extras._original_transition_update

_pending_kind = None
_pending_uses = 0
_pending_until = 0.0

_base_begin = visual_engine.TransitionManager.begin
_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _clear_pending():
    global _pending_kind, _pending_uses, _pending_until
    _pending_kind = None
    _pending_uses = 0
    _pending_until = 0.0


def _arm(kind, uses=2):
    global _pending_kind, _pending_uses, _pending_until
    # Only the deliberate full-scene family uses the one-shot bridge.
    if transition_scope(kind) != SCENE_SCOPE:
        _clear_pending()
        return
    _pending_kind = str(kind)
    _pending_uses = max(1, int(uses))
    _pending_until = time.monotonic() + 2.0


def _begin(self, display, kind="Fade", duration=0.8):
    global _pending_kind, _pending_uses
    now = time.monotonic()
    if _pending_kind and now > _pending_until:
        _clear_pending()

    if _pending_kind:
        if kind == "Melt" and _pending_uses > 0:
            chosen = _pending_kind
            _pending_uses -= 1
            if _pending_uses <= 0:
                _clear_pending()
            return _base_begin(self, display, chosen, duration)
        # Any unrelated transition cancels the pending one-shot instead of
        # leaving an override armed for some future slideshow change.
        _clear_pending()

    return _base_begin(self, display, kind, duration)


def _get_commands(self):
    commands = list(_base_get_commands(self))
    for data in commands:
        if not isinstance(data, dict) or data.get("command") != "pixel_melt_next":
            continue
        value = data.get("value")
        if not isinstance(value, dict):
            continue
        kind = value.get("kind")
        if kind:
            _arm(kind, 2)
    return commands


visual_engine.TransitionManager.begin = _begin
controller_state_ui.PhoneControlServer.get_commands = _get_commands
