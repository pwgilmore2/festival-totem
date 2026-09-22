import controller_state_ui
import performance_extras
from icon_assets import ICON_LIBRARY


_overlay = {
    "front": {"icon_enabled": False, "icon": None},
    "back": {"icon_enabled": False, "icon": None},
}


def _default_icon():
    names = ICON_LIBRARY.names()
    return names[0] if names else None


for _side in ("front", "back"):
    _overlay[_side]["icon"] = _default_icon()


def get_overlay_state(side):
    """Return a copy of icon-layer state for the requested panel."""
    side = "back" if side == "back" else "front"
    return dict(_overlay[side])


def _target_sides(target):
    return ("front", "back") if target == "both" else (target,)


def _normalize_selected_icons():
    names = ICON_LIBRARY.names()
    fallback = names[0] if names else None
    for side in ("front", "back"):
        if _overlay[side]["icon"] not in names:
            _overlay[side]["icon"] = fallback
            if fallback is None:
                _overlay[side]["icon_enabled"] = False


def _set_icon(target, name=None, enabled=None):
    names = ICON_LIBRARY.names()
    for side in _target_sides(target):
        if name in names:
            _overlay[side]["icon"] = name
        if isinstance(enabled, bool):
            _overlay[side]["icon_enabled"] = enabled


def _toggle_icon(target, name):
    names = ICON_LIBRARY.names()
    if name not in names:
        return False
    enabled_any = False
    for side in _target_sides(target):
        state = _overlay[side]
        if state["icon_enabled"] and state["icon"] == name:
            state["icon_enabled"] = False
        else:
            state["icon"] = name
            state["icon_enabled"] = True
            enabled_any = True
    return enabled_any


# Icon selection is now its own controller command. Text and full-size icons are
# deliberately exclusive until authored 16x16 companion assets exist.
_base_get_commands = controller_state_ui.PhoneControlServer.get_commands


def _get_commands(self):
    commands = list(_base_get_commands(self))
    target = getattr(performance_extras, "_target", "both")
    out = []
    for data in commands:
        if not isinstance(data, dict):
            out.append(data)
            continue
        command = data.get("command")
        value = data.get("value")
        if command == "set_target" and value in ("front", "back", "both"):
            target = value
            out.append(data)
            continue
        if command == "reload_library":
            ICON_LIBRARY.reload()
            _normalize_selected_icons()
            out.append(data)
            continue
        if command == "icon_toggle":
            if _toggle_icon(target, str(value)):
                # Showing a 32x32 icon explicitly leaves text mode.
                out.append({"command": "text_hide", "value": None})
            continue
        if command == "icon_clear":
            _set_icon(target, enabled=False)
            continue
        if command == "text_show":
            # Showing text explicitly leaves full-size icon mode.
            _set_icon(target, enabled=False)
            out.append(data)
            continue
        out.append(data)
    return out


controller_state_ui.PhoneControlServer.get_commands = _get_commands


_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    if isinstance(state, dict):
        state = dict(state)
        panels = dict(state.get("panels") or {})
        for side in ("front", "back"):
            panel = dict(panels.get(side) or {})
            panel["icon"] = dict(_overlay[side])
            panels[side] = panel
        state["panels"] = panels

        ref = state.get("reference_side", "front")
        state["icon"] = dict(_overlay.get(ref, _overlay["front"]))
        state["overlay_icons"] = ICON_LIBRARY.names()
        state["icon_library_errors"] = list(ICON_LIBRARY.errors)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
