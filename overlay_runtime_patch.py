import time

import controller_state_ui
import performance_extras
from icon_assets import ICON_LIBRARY


ICON_MOTIONS = ("Bounce", "Orbit")
ICON_TRANSITION_DURATION = 0.55


def _new_icon_state():
    return {
        "icon_enabled": False,
        "icon": None,
        "motion": "Bounce",
        "transition_entering": True,
        "transition_started": 0.0,
        "transition_active": False,
        "transition_duration": ICON_TRANSITION_DURATION,
    }


_overlay = {
    "front": _new_icon_state(),
    "back": _new_icon_state(),
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
                _overlay[side]["transition_active"] = False


def _begin_transition(state, entering):
    state["transition_entering"] = bool(entering)
    state["transition_started"] = time.monotonic()
    state["transition_active"] = True
    state["transition_duration"] = ICON_TRANSITION_DURATION


def _set_icon(target, name=None, enabled=None, animate=True):
    names = ICON_LIBRARY.names()
    for side in _target_sides(target):
        state = _overlay[side]
        if name in names:
            state["icon"] = name
        if not isinstance(enabled, bool):
            continue
        if enabled:
            if not state["icon_enabled"]:
                state["icon_enabled"] = True
                if animate:
                    _begin_transition(state, True)
        elif state["icon_enabled"]:
            if animate:
                _begin_transition(state, False)
            else:
                state["icon_enabled"] = False
                state["transition_active"] = False


def _toggle_icon(target, name):
    names = ICON_LIBRARY.names()
    if name not in names:
        return False
    enabled_any = False
    for side in _target_sides(target):
        state = _overlay[side]
        if state["icon_enabled"] and state["icon"] == name:
            _set_icon(side, enabled=False)
        else:
            changing = state.get("icon") != name
            state["icon"] = name
            state["icon_enabled"] = True
            if changing or not state.get("transition_active"):
                _begin_transition(state, True)
            enabled_any = True
    return enabled_any


def _set_motion(target, value):
    if value not in ICON_MOTIONS:
        return
    for side in _target_sides(target):
        _overlay[side]["motion"] = value


# Icon selection is its own controller command. Text and full-size icons remain
# exclusive until separately authored mini icons exist.
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
                out.append({"command": "text_hide", "value": None})
            continue
        if command == "icon_clear":
            _set_icon(target, enabled=False)
            continue
        if command == "icon_motion":
            _set_motion(target, str(value))
            continue
        if command == "text_show":
            _set_icon(target, enabled=False, animate=False)
            out.append(data)
            continue
        # Ignore retired icon controls from stale browser pages safely.
        if command in ("icon_position", "icon_center", "icon_transition_settings"):
            continue
        out.append(data)
    return out


controller_state_ui.PhoneControlServer.get_commands = _get_commands


_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    now = time.monotonic()
    for side in ("front", "back"):
        icon = _overlay[side]
        if icon.get("transition_active"):
            elapsed = now - float(icon.get("transition_started", now))
            duration = float(icon.get("transition_duration", ICON_TRANSITION_DURATION))
            if elapsed >= duration:
                icon["transition_active"] = False
                if not icon.get("transition_entering", True):
                    icon["icon_enabled"] = False

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
        state["icon_motions"] = list(ICON_MOTIONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
