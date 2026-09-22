import controller_state_ui
import performance_extras
from overlay_sprite_assets import OVERLAY_ICONS


_overlay = {
    "front": {"icon_enabled": False, "icon": "Heart", "motion": "Static"},
    "back": {"icon_enabled": False, "icon": "Heart", "motion": "Static"},
}


def get_overlay_state(side):
    """Return a copy of native overlay state for the requested panel."""
    side = "back" if side == "back" else "front"
    return dict(_overlay[side])


def _target_sides(target):
    return ("front", "back") if target == "both" else (target,)


def _apply_overlay_payload(value, target):
    if not isinstance(value, dict):
        return
    icon = value.get("overlay_icon")
    enabled = value.get("overlay_icon_enabled")
    motion = value.get("overlay_motion")
    for side in _target_sides(target):
        if isinstance(enabled, bool):
            _overlay[side]["icon_enabled"] = enabled
        if icon in OVERLAY_ICONS:
            _overlay[side]["icon"] = icon
        if motion in ("Static", "Float", "Bounce"):
            _overlay[side]["motion"] = motion


# This module intentionally owns state only. Rendering now happens explicitly
# from simulator.py through OverlayRenderer instead of monkeypatching TextRenderer.
_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    for data in commands:
        if not isinstance(data, dict):
            continue
        if data.get("command") == "set_target" and data.get("value") in ("front", "back", "both"):
            target = data.get("value")
            continue
        if data.get("command") in ("text_settings", "text_show", "text_refresh"):
            _apply_overlay_payload(data.get("value"), target)
    return commands


controller_state_ui.PhoneControlServer.get_commands = _get_commands


_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    if isinstance(state, dict):
        state = dict(state)
        panels = dict(state.get("panels") or {})
        for side in ("front", "back"):
            panel = dict(panels.get(side) or {})
            text = dict(panel.get("text") or {})
            text["overlay_icon_enabled"] = bool(_overlay[side]["icon_enabled"])
            text["overlay_icon"] = _overlay[side]["icon"]
            text["overlay_motion"] = _overlay[side]["motion"]
            text["overlay_text_visible"] = bool(text.get("enabled", False))
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels

        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            text = dict(state["text"])
            text["overlay_icon_enabled"] = bool(_overlay[ref]["icon_enabled"])
            text["overlay_icon"] = _overlay[ref]["icon"]
            text["overlay_motion"] = _overlay[ref]["motion"]
            text["overlay_text_visible"] = bool(text.get("enabled", False))
            state["text"] = text

        state["overlay_icons"] = list(OVERLAY_ICONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
