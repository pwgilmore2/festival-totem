import time

import controller_state_ui
import performance_extras
from icon_assets import ICON_LIBRARY


ICON_MOTIONS = ("Bounce", "Drift", "Orbit", "Manual")
ICON_TRANSITIONS = ("None", "Fade", "Flicker", "Slide", "Drop", "Pixel Reveal")


def _new_icon_state():
    return {
        "icon_enabled": False,
        "icon": None,
        "motion": "Bounce",
        "x": 0.5,
        "y": 0.5,
        "enter": "Pixel Reveal",
        "exit": "Fade",
        "transition_kind": None,
        "transition_entering": True,
        "transition_started": 0.0,
        "transition_duration": 0.55,
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


def _begin_transition(state, kind, entering, duration=0.55):
    kind = kind if kind in ICON_TRANSITIONS else "None"
    state["transition_kind"] = None if kind == "None" else kind
    state["transition_entering"] = bool(entering)
    state["transition_started"] = time.monotonic()
    state["transition_duration"] = max(0.08, min(2.0, float(duration)))


def _set_icon(target, name=None, enabled=None, animate=True):
    names = ICON_LIBRARY.names()
    for side in _target_sides(target):
        state = _overlay[side]
        if name in names:
            state["icon"] = name
        if isinstance(enabled, bool):
            if enabled and not state["icon_enabled"]:
                state["icon_enabled"] = True
                if animate:
                    _begin_transition(state, state.get("enter", "Pixel Reveal"), True)
            elif not enabled and state["icon_enabled"]:
                if animate and state.get("exit", "None") != "None":
                    _begin_transition(state, state.get("exit", "Fade"), False)
                else:
                    state["icon_enabled"] = False
                    state["transition_kind"] = None


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
            if changing or not state.get("transition_kind"):
                _begin_transition(state, state.get("enter", "Pixel Reveal"), True)
            enabled_any = True
    return enabled_any


def _set_motion(target, value):
    if value not in ICON_MOTIONS:
        return
    for side in _target_sides(target):
        _overlay[side]["motion"] = value


def _set_position(target, value):
    if not isinstance(value, dict):
        return
    try:
        x = max(0.0, min(1.0, float(value.get("x", 0.5))))
        y = max(0.0, min(1.0, float(value.get("y", 0.5))))
    except (TypeError, ValueError):
        return
    for side in _target_sides(target):
        _overlay[side]["x"] = x
        _overlay[side]["y"] = y
        _overlay[side]["motion"] = "Manual"


def _set_transition_choice(target, value):
    if not isinstance(value, dict):
        return
    for side in _target_sides(target):
        state = _overlay[side]
        enter = value.get("enter")
        exit_kind = value.get("exit")
        if enter in ICON_TRANSITIONS:
            state["enter"] = enter
        if exit_kind in ICON_TRANSITIONS:
            state["exit"] = exit_kind


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
                out.append({"command": "text_hide", "value": None})
            continue
        if command == "icon_clear":
            _set_icon(target, enabled=False)
            continue
        if command == "icon_motion":
            _set_motion(target, str(value))
            continue
        if command == "icon_position":
            _set_position(target, value)
            continue
        if command == "icon_center":
            for side in _target_sides(target):
                _overlay[side]["x"] = 0.5
                _overlay[side]["y"] = 0.5
                _overlay[side]["motion"] = "Bounce"
            continue
        if command == "icon_transition_settings":
            _set_transition_choice(target, value)
            continue
        if command == "text_show":
            _set_icon(target, enabled=False, animate=False)
            out.append(data)
            continue
        out.append(data)
    return out


controller_state_ui.PhoneControlServer.get_commands = _get_commands


_base_update_state = controller_state_ui.PhoneControlServer.update_state


def _update_state(self, state):
    now = time.monotonic()
    for side in ("front", "back"):
        icon = _overlay[side]
        if icon.get("transition_kind") and not icon.get("transition_entering"):
            elapsed = now - float(icon.get("transition_started", now))
            if elapsed >= float(icon.get("transition_duration", 0.55)):
                icon["icon_enabled"] = False
                icon["transition_kind"] = None

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
        state["icon_transitions"] = list(ICON_TRANSITIONS)
    return _base_update_state(self, state)


controller_state_ui.PhoneControlServer.update_state = _update_state
