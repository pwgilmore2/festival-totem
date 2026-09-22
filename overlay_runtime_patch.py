import controller_state_ui
import performance_extras
from overlay_sprite_assets import OVERLAY_ICONS


_overlay = {
    "front": {"icon_enabled": False, "icon": "Heart", "motion": "Static", "text_visible": False},
    "back": {"icon_enabled": False, "icon": "Heart", "motion": "Static", "text_visible": False},
}


def get_overlay_state(side):
    side = "back" if side == "back" else "front"
    return dict(_overlay[side])


_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    for data in commands:
        if not isinstance(data, dict):
            continue
        if data.get("command") == "set_target" and data.get("value") in ("front", "back", "both"):
            target = data.get("value")
        if data.get("command") not in ("text_settings", "text_show", "text_refresh", "text_hide"):
            continue

        sides = ("front", "back") if target == "both" else (target,)
        if data.get("command") == "text_hide":
            for side in sides:
                _overlay[side]["text_visible"] = False
            continue

        value = data.get("value")
        if not isinstance(value, dict):
            continue
        icon = value.get("overlay_icon")
        enabled = value.get("overlay_icon_enabled")
        motion = value.get("overlay_motion")
        text_visible = value.get("overlay_text_visible")
        for side in sides:
            if isinstance(enabled, bool):
                _overlay[side]["icon_enabled"] = enabled
            if icon in OVERLAY_ICONS:
                _overlay[side]["icon"] = icon
            if motion in ("Static", "Float", "Bounce"):
                _overlay[side]["motion"] = motion
            if isinstance(text_visible, bool):
                _overlay[side]["text_visible"] = text_visible

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
            text["overlay_text_visible"] = bool(_overlay[side]["text_visible"])
            panel["text"] = text
            panels[side] = panel
        state["panels"] = panels
        ref = state.get("reference_side", "front")
        if isinstance(state.get("text"), dict):
            text = dict(state["text"])
            text["overlay_icon_enabled"] = bool(_overlay[ref]["icon_enabled"])
            text["overlay_icon"] = _overlay[ref]["icon"]
            text["overlay_motion"] = _overlay[ref]["motion"]
            text["overlay_text_visible"] = bool(_overlay[ref]["text_visible"])
            state["text"] = text
        state["overlay_icons"] = list(OVERLAY_ICONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
