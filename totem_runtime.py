"""Platform-neutral live-performance runtime for the festival totem.

The runtime owns state, command routing and render ordering. Desktop concerns
(Pygame, PIL thumbnails, HTTPS) and MatrixPortal concerns (RGBMatrix, gifio,
WiFi polling) stay in their platform shells/adapters.
"""

import random
import time

from chaos_engine import ChaosEngine
from controller import TotemController
from info_scenes import InfoScenes, SCENES as INFO_SCENES, clean_schedule
from particles import ParticleSystem
from runtime_io import SignalStore
from text_engine import (
    TEXT_BACKGROUNDS,
    TEXT_COLORS,
    TEXT_EFFECTS,
    TEXT_FONTS,
    TEXT_MOTIONS,
    TextRenderer,
)
from transition_engine import INTENSE_TRANSITIONS, TransitionManager
from visual_engine import LAYER_KEYS, TRANSITIONS, VisualLayerEngine, copy_pixels


SIDES = ("front", "back")
ICON_MOTIONS = ("Bounce", "Orbit")
ICON_TRANSITION_DURATION = 0.55
REACTIVE_PRESETS = ("Pulse", "Neon", "Spark", "Chaos")

DEFAULT_SCENES = {
    "Chill": {
        "duration": 8.0,
        "beat_sync": True,
        "transition": "Fade",
        "transition_duration": 1.15,
        "random": False,
        "reactive": "Neon",
        "strength": 0.45,
    },
    "Pulse": {
        "duration": 5.0,
        "beat_sync": True,
        "transition": "Zoom",
        "transition_duration": 0.65,
        "random": True,
        "reactive": "Pulse",
        "strength": 0.78,
    },
    "Glitch": {
        "duration": 4.0,
        "beat_sync": True,
        "transition": "Glitch",
        "transition_duration": 0.45,
        "random": True,
        "reactive": "Neon",
        "strength": 0.82,
    },
    "Chaos": {
        "duration": 3.0,
        "beat_sync": True,
        "transition": "Glitch",
        "transition_duration": 0.35,
        "random": True,
        "reactive": "Chaos",
        "strength": 1.0,
    },
}


class TotemRuntime:
    """Shared front/back totem state machine and compositor."""

    def __init__(
        self,
        width,
        height,
        displays,
        media,
        icon_library,
        overlay_renderer,
        effects,
        signal_store=None,
        scenes=None,
        particle_factory=ParticleSystem,
        mirrored=False,
    ):
        self.width = int(width)
        self.height = int(height)
        self.displays = displays
        self.media = media
        self.icon_library = icon_library
        self.icon_library_revision = 0
        self.overlay_renderer = overlay_renderer
        self.base_effects = effects
        self.signal_store = signal_store or SignalStore()
        self.audio = self.signal_store.audio
        self.motion = self.signal_store.motion
        self.scenes = dict(scenes or DEFAULT_SCENES)

        self.active_target = "both"
        self.current_scene = "Custom"
        self.mirrored = bool(mirrored)
        self.info_scenes = InfoScenes(self.width, self.height)

        self.layer_engine = VisualLayerEngine(self.width, self.height)
        self.chaos_engine = ChaosEngine(self.layer_engine)
        self.text_engine = TextRenderer(self.width, self.height)
        self.particles = {
            side: particle_factory(self.width, self.height, count=60) for side in SIDES
        }
        self.content_transitions = {
            side: TransitionManager(self.width, self.height) for side in SIDES
        }
        self.scene_transitions = {
            side: TransitionManager(self.width, self.height) for side in SIDES
        }
        self.content_snapshots = {side: None for side in SIDES}
        self.scene_snapshots = {side: None for side in SIDES}

        self.panels = {
            side: {
                "image_index": 0,
                "slideshow": self._slideshow_state(),
                "reactive": self._reactive_state(),
                "transition": self._transition_state(),
                "text": self._text_state(),
                "icon": self._icon_state(),
                "info_scene": None,
            }
            for side in SIDES
        }
        self._media_suspended = {side: False for side in SIDES}
        self._separate_initial_media()

        self.controllers = {
            side: TotemController(self._make_effects(side)) for side in SIDES
        }
        for side in SIDES:
            show = self.panels[side]["slideshow"]
            if show["indices"]:
                self.panels[side]["image_index"] = show["indices"][0]
                if not (self.mirrored and side == "back"):
                    self.media.select(side, show["indices"][0])
            self.controllers[side].set_effect("Image")
        if self.mirrored:
            self._suspend_media("back")

    def _suspend_media(self, side):
        if self._media_suspended[side]:
            return
        suspend = getattr(self.media, "suspend", None)
        if suspend:
            suspend(side)
            self._media_suspended[side] = True

    def _black_background(self, side):
        panel = self.panels[side]
        if panel["info_scene"]:
            return True
        return (panel["text"]["enabled"] and panel["text"]["background"] == "Black") or (
            panel["icon"]["icon_enabled"] and not panel["text"]["enabled"]
            and panel["icon"].get("background") == "Black"
        )

    def _refresh_media(self, side):
        if (self.mirrored and side == "back") or self._black_background(side):
            self._suspend_media(side)
        elif self._media_suspended[side] and len(self.media):
            self.media.select(side, self.panels[side]["image_index"])
            self._media_suspended[side] = False

    def set_mirrored(self, enabled):
        enabled = bool(enabled)
        if enabled == self.mirrored:
            return
        self.mirrored = enabled
        if enabled:
            self._suspend_media("back")
            self.content_snapshots["back"] = None
            self.scene_snapshots["back"] = None
            self.content_transitions["back"].active = False
            self.content_transitions["back"].source = None
            self.scene_transitions["back"].active = False
            self.scene_transitions["back"].source = None
            self.active_target = "both"
        else:
            self._refresh_media("back")

    def _exit_info_scene(self, side):
        if self.panels[side]["info_scene"] is not None:
            self.panels[side]["info_scene"] = None
            self._refresh_media(side)

    def set_info_scene(self, mode):
        if mode not in INFO_SCENES and mode is not None:
            return
        for side in self.target_sides():
            if self.panels[side]["info_scene"] == mode:
                continue
            self._begin_transition(side)
            if mode is None:
                self._exit_info_scene(side)
            else:
                self.panels[side]["info_scene"] = mode
                self._stop_show(side)
                self.panels[side]["text"]["enabled"] = False
                self._set_icon_enabled(side, False, False)
                self._suspend_media(side)
        self.current_scene = mode or "Custom"

    # ----- state factories -------------------------------------------------

    def _slideshow_state(self):
        indices = list(range(len(self.media)))
        random.shuffle(indices)
        return {
            "active": bool(indices),
            "indices": indices,
            "position": 0,
            "duration": 10.0,
            "elapsed": 0.0,
            "shuffle": True,
            "label": "All",
            "beat_sync": True,
        }

    def _reactive_state(self):
        return {
            "enabled": False,
            "strength": 0.65,
            "preset": "Pulse",
            "layers": self.layer_engine.preset("Pulse"),
        }

    @staticmethod
    def _transition_state():
        return {"kind": "Fade", "duration": 0.8, "random": True}

    def _text_state(self):
        state = self.text_engine.defaults()
        state.update(
            enabled=False,
            background="Dimmed GIF",
            background_brightness=0.65,
            backplate=True,
            speed=34.0,
            motion="Static",
            audio_reactivity="Off",
            glow=False,
            wave=False,
            glitch=False,
            beat_pulse=False,
        )
        if state.get("color_mode") == "Audio":
            state["color_mode"] = "Rainbow"
        return state

    def _icon_state(self):
        names = self.icon_library.names()
        return {
            "icon_enabled": False,
            "icon": names[0] if names else None,
            "motion": "Bounce",
            "transition_entering": True,
            "transition_started": 0.0,
            "transition_active": False,
            "transition_duration": ICON_TRANSITION_DURATION,
        }

    def _separate_initial_media(self):
        if len(self.media) <= 1:
            return
        front = self.panels["front"]["slideshow"]["indices"]
        back = self.panels["back"]["slideshow"]["indices"]
        if front and back and front[0] == back[0]:
            back[0], back[1] = back[1], back[0]

    # ----- media/effect helpers -------------------------------------------

    def target_sides(self):
        if self.mirrored:
            return ["front"]
        return list(SIDES) if self.active_target == "both" else [self.active_target]

    def reference_side(self):
        if self.mirrored:
            return "front"
        return "back" if self.active_target == "back" else "front"

    def reference_index(self):
        return self.panels[self.reference_side()]["image_index"]

    def signals(self):
        return self.signal_store.snapshot()

    def audio_fresh(self):
        return self.signal_store.audio_fresh()

    def _party_fx(self, side, display, t):
        self.base_effects["Plasma"](display, t)
        self.particles[side].draw(display)

    def _image_fx(self, side, display, t):
        self.media.render(side, self.panels[side]["image_index"], display, t)

    def _make_effects(self, side):
        effects = dict(self.base_effects)
        effects["Party"] = lambda display, t, target=side: self._party_fx(
            target, display, t
        )
        effects["Image"] = lambda display, t, target=side: self._image_fx(
            target, display, t
        )
        return effects

    def _choose_transition(self, side):
        state = self.panels[side]["transition"]
        if state["random"]:
            choices = [kind for kind in TRANSITIONS if kind != "None"]
            return random.choice(choices)
        return state["kind"]

    def _begin_transition(self, side):
        state = self.panels[side]["transition"]
        self.content_transitions[side].begin(
            self.displays[side],
            self._choose_transition(side),
            state["duration"],
            source=self.content_snapshots[side],
        )

    def _begin_background_transition(self, side):
        self.content_transitions[side].begin(
            self.displays[side], "Fade", 0.45,
            source=self.scene_snapshots[side],
        )

    def _stop_show(self, side):
        show = self.panels[side]["slideshow"]
        show["active"] = False
        show["elapsed"] = 0.0

    def _select_for_side(self, side, index, stop=True, transition=True):
        if not len(self.media):
            return
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        index = max(0, min(len(self.media) - 1, index))
        if (
            index == self.panels[side]["image_index"]
            and self.controllers[side].effect_name == "Image"
            and self.panels[side]["info_scene"] is None
        ):
            return
        if transition:
            self._begin_transition(side)
        self.panels[side]["image_index"] = index
        self.panels[side]["info_scene"] = None
        if not (self.mirrored and side == "back"):
            self.media.select(side, index)
            self._media_suspended[side] = False
        if stop:
            self._stop_show(side)
        self.controllers[side].set_effect("Image")

    def _clean_indices(self, values):
        out = []
        if not isinstance(values, list):
            return out
        for value in values:
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= index < len(self.media) and index not in out:
                out.append(index)
        return out

    # ----- slideshow / transitions ----------------------------------------

    def select_image(self, index):
        for side in self.target_sides():
            self._select_for_side(side, index)

    def step_filtered(self, value):
        if not isinstance(value, dict):
            return
        indices = self._clean_indices(value.get("indices", []))
        if not indices:
            return
        try:
            delta = int(value.get("delta", 1))
        except (TypeError, ValueError):
            delta = 1
        for side in self.target_sides():
            current = self.panels[side]["image_index"]
            try:
                position = indices.index(current)
            except ValueError:
                position = -1 if delta > 0 else 0
            self._select_for_side(side, indices[(position + delta) % len(indices)])

    def _next_index_for_side(self, side, fallback_indices):
        show = self.panels[side]["slideshow"]
        if show.get("active") and show.get("indices"):
            indices = list(show["indices"])
        else:
            indices = fallback_indices
        if not indices:
            return None, None
        current = self.panels[side]["image_index"]
        try:
            position = indices.index(current)
        except ValueError:
            position = -1
        return indices[(position + 1) % len(indices)], position

    def _commit_transition_next(self, side, next_index, position):
        if next_index is None:
            return
        show = self.panels[side]["slideshow"]
        self.panels[side]["image_index"] = next_index
        self.media.select(side, next_index)
        self.controllers[side].set_effect("Image")
        if show.get("active"):
            show["position"] = (position + 1) % len(show["indices"])
            show["elapsed"] = 0.0

    def pixel_melt_next(self, value):
        if not isinstance(value, dict):
            return
        fallback = self._clean_indices(value.get("indices", []))
        try:
            duration = max(0.25, min(5.0, float(value.get("duration", 1.8))))
        except (TypeError, ValueError):
            duration = 1.8
        for side in self.target_sides():
            next_index, position = self._next_index_for_side(side, fallback)
            if next_index is None:
                continue
            self.content_transitions[side].begin(
                self.displays[side],
                "Melt",
                duration,
                source=self.content_snapshots[side],
            )
            self._commit_transition_next(side, next_index, position)

    def intense_transition_next(self, value):
        if not isinstance(value, dict):
            return
        fallback = self._clean_indices(value.get("indices", []))
        kind = str(value.get("kind", "Morph"))
        if kind not in INTENSE_TRANSITIONS:
            kind = "Morph"
        try:
            duration = max(0.25, min(4.0, float(value.get("duration", 1.15))))
        except (TypeError, ValueError):
            duration = 1.15
        self.active_target = "both"
        for side in SIDES:
            next_index, position = self._next_index_for_side(side, fallback)
            if next_index is None:
                continue
            self.scene_transitions[side].begin(
                self.displays[side],
                kind,
                duration,
                source=self.scene_snapshots[side],
            )
            self._commit_transition_next(side, next_index, position)

    def start_show(self, value):
        if not isinstance(value, dict):
            return
        indices = self._clean_indices(value.get("indices", []))
        if not indices:
            return
        try:
            duration = max(1.0, min(120.0, float(value.get("duration", 5))))
        except (TypeError, ValueError):
            duration = 5.0
        shuffle = bool(value.get("shuffle", False))
        label = str(value.get("label", "Selection"))[:80]
        order = list(indices)
        if shuffle:
            random.shuffle(order)
        sides = self.target_sides()
        for side in sides:
            beat_sync = self.panels[side]["slideshow"].get("beat_sync", True)
            side_order = list(order)
            if shuffle and len(sides) == 1:
                random.shuffle(side_order)
            self.panels[side]["slideshow"].update(
                active=True,
                indices=side_order,
                position=0,
                duration=duration,
                elapsed=0.0,
                shuffle=shuffle,
                label=label,
                beat_sync=beat_sync,
            )
            self._select_for_side(side, side_order[0], stop=False)
        self.current_scene = "Custom"

    def _advance_show(self, side):
        show = self.panels[side]["slideshow"]
        show["elapsed"] = 0.0
        show["position"] = (show["position"] + 1) % len(show["indices"])
        if show["shuffle"] and show["position"] == 0 and len(show["indices"]) > 1:
            random.shuffle(show["indices"])
        self._select_for_side(
            side, show["indices"][show["position"]], stop=False
        )

    def _update_shows(self, dt):
        for side in SIDES:
            show = self.panels[side]["slideshow"]
            if (
                self.controllers[side].paused
                or not show["active"]
                or not show["indices"]
            ):
                continue
            show["elapsed"] += dt
            if show["elapsed"] < show["duration"]:
                continue
            if (
                show.get("beat_sync", False)
                and self.audio_fresh()
                and show["elapsed"] < show["duration"] + 2.0
                and not self.audio["beat"]
            ):
                continue
            self._advance_show(side)

    # ----- text / icons ----------------------------------------------------

    @staticmethod
    def _begin_icon_transition(state, entering):
        state["transition_entering"] = bool(entering)
        state["transition_started"] = time.monotonic()
        state["transition_active"] = True
        state["transition_duration"] = ICON_TRANSITION_DURATION

    def _set_icon_enabled(self, side, enabled, animate=True):
        state = self.panels[side]["icon"]
        if enabled:
            if not state["icon_enabled"]:
                state["icon_enabled"] = True
                if animate:
                    self._begin_icon_transition(state, True)
        elif state["icon_enabled"]:
            if animate:
                self._begin_icon_transition(state, False)
            else:
                state.update(icon_enabled=False, transition_active=False)

    def toggle_icon(self, name):
        names = self.icon_library.names()
        if name not in names:
            return
        enabled_any = False
        for side in self.target_sides():
            if self.panels[side]["icon"].get("background") == "Black":
                self._begin_background_transition(side)
            self._exit_info_scene(side)
            state = self.panels[side]["icon"]
            if state["icon_enabled"] and state.get("icon") == name:
                self._set_icon_enabled(side, False, True)
            else:
                changing = state.get("icon") != name
                state["icon"] = name
                state["icon_enabled"] = True
                if changing or not state.get("transition_active"):
                    self._begin_icon_transition(state, True)
                enabled_any = True
        if enabled_any:
            self.hide_text()

    def clear_icon(self):
        for side in self.target_sides():
            self._set_icon_enabled(side, False, True)

    def set_icon_motion(self, value):
        if value not in ICON_MOTIONS:
            return
        for side in self.target_sides():
            self.panels[side]["icon"]["motion"] = value

    def _update_icon_transitions(self):
        now = time.monotonic()
        for side in SIDES:
            state = self.panels[side]["icon"]
            if not state.get("transition_active"):
                continue
            duration = float(
                state.get("transition_duration", ICON_TRANSITION_DURATION)
            )
            if now - float(state.get("transition_started", now)) < duration:
                continue
            state["transition_active"] = False
            if not state.get("transition_entering", True):
                if state.get("background") == "Black" and not self.panels[side]["text"]["enabled"]:
                    self._begin_background_transition(side)
                state["icon_enabled"] = False

    def set_text_settings(self, value):
        if not isinstance(value, dict):
            return
        for side in self.target_sides():
            state = self.panels[side]["text"]
            if (
                state["enabled"]
                and value.get("background") in ("Black", "Dimmed GIF")
                and value["background"] != state["background"]
            ):
                self._begin_background_transition(side)
            if "message" in value:
                state["message"] = str(value["message"])[:120]
            if value.get("font") in TEXT_FONTS:
                state["font"] = value["font"]
            color_mode = value.get("color_mode", state.get("color_mode", "Rainbow"))
            state["color_mode"] = (
                color_mode
                if color_mode in TEXT_COLORS and color_mode != "Audio"
                else "Rainbow"
            )
            if "color" in value:
                state["color"] = str(value["color"])[:16]
            if "scale" in value:
                try:
                    state["scale"] = max(1, min(3, int(value["scale"])))
                except (TypeError, ValueError):
                    pass
            audio_mode = str(
                value.get("audio_reactivity", state.get("audio_reactivity", "Off"))
            )
            if audio_mode == "Intense":
                audio_mode = "Reactive"
            if audio_mode not in ("Off", "Subtle", "Reactive"):
                audio_mode = "Off"
            state.update(
                motion="Static",
                speed=34.0,
                glow=False,
                wave=False,
                glitch=False,
                beat_pulse=False,
                audio_reactivity=audio_mode,
                background=(
                    value.get("background")
                    if value.get("background") in ("Black", "Dimmed GIF")
                    else state.get("background", "Dimmed GIF")
                ),
                background_brightness=0.65,
                backplate=True,
            )

    def show_text(self, value=None):
        if isinstance(value, dict):
            self.set_text_settings(value)
        for side in self.target_sides():
            if self.panels[side]["text"]["background"] == "Black":
                self._begin_background_transition(side)
            self._exit_info_scene(side)
            self._set_icon_enabled(side, False, False)
            self.panels[side]["text"]["enabled"] = True

    def hide_text(self):
        for side in self.target_sides():
            if (
                self.panels[side]["text"]["enabled"]
                and self.panels[side]["text"]["background"] == "Black"
            ):
                self._begin_background_transition(side)
            self.panels[side]["text"]["enabled"] = False

    # ----- audio / presets -------------------------------------------------

    def set_target(self, value):
        if self.mirrored:
            self.active_target = "both"
        elif value in ("front", "back", "both"):
            self.active_target = value

    def set_effect(self, value):
        for side in self.target_sides():
            if value in self.controllers[side].effects:
                self._begin_transition(side)
                self._exit_info_scene(side)
                self.controllers[side].set_effect(value)

    def _master(self, attr, value, minimum, maximum):
        try:
            amount = max(minimum, min(maximum, float(value)))
        except (TypeError, ValueError):
            return
        for side in self.target_sides():
            setattr(self.controllers[side], attr, amount)

    def toggle_pause(self):
        pause = not all(self.controllers[side].paused for side in self.target_sides())
        for side in self.target_sides():
            self.controllers[side].paused = pause

    def _mark_custom(self):
        self.current_scene = "Custom"

    def set_reactive_enabled(self, value):
        for side in self.target_sides():
            self.panels[side]["reactive"]["enabled"] = bool(value)

    def set_reactive_strength(self, value):
        try:
            amount = max(0.0, min(1.5, float(value)))
        except (TypeError, ValueError):
            return
        for side in self.target_sides():
            self.panels[side]["reactive"]["strength"] = amount
        self._mark_custom()

    def set_reactive_preset(self, value):
        if value not in REACTIVE_PRESETS:
            return
        for side in self.target_sides():
            reactive = self.panels[side]["reactive"]
            reactive["preset"] = value
            reactive["layers"] = self.layer_engine.preset(value)
        self._mark_custom()

    def set_layer(self, value):
        if not isinstance(value, dict):
            return
        name = value.get("name")
        if name not in LAYER_KEYS:
            return
        try:
            amount = max(0.0, min(1.5, float(value.get("value", 0))))
        except (TypeError, ValueError):
            return
        for side in self.target_sides():
            reactive = self.panels[side]["reactive"]
            reactive["layers"][name] = amount
            reactive["preset"] = "Custom"
        self._mark_custom()

    def set_transition(self, value):
        if not isinstance(value, dict):
            return
        for side in self.target_sides():
            transition = self.panels[side]["transition"]
            if value.get("kind") in TRANSITIONS:
                transition["kind"] = value["kind"]
            if "duration" in value:
                try:
                    transition["duration"] = max(
                        0.08, min(5.0, float(value["duration"]))
                    )
                except (TypeError, ValueError):
                    pass
            if "random" in value:
                transition["random"] = bool(value["random"])
        self._mark_custom()

    def set_beat_sync(self, value):
        for side in self.target_sides():
            self.panels[side]["slideshow"]["beat_sync"] = bool(value)
        self._mark_custom()

    def apply_scene(self, name):
        scene = self.scenes.get(name)
        if not scene:
            return
        for side in self.target_sides():
            show = self.panels[side]["slideshow"]
            transition = self.panels[side]["transition"]
            reactive = self.panels[side]["reactive"]
            if not show["indices"]:
                show["indices"] = list(range(len(self.media)))
                random.shuffle(show["indices"])
            show.update(
                active=bool(show["indices"]),
                duration=scene["duration"],
                elapsed=0.0,
                shuffle=True,
                beat_sync=scene["beat_sync"],
            )
            transition.update(
                kind=scene["transition"],
                duration=scene["transition_duration"],
                random=scene["random"],
            )
            reactive.update(
                enabled=True,
                strength=scene["strength"],
                preset=scene["reactive"],
                layers=self.layer_engine.preset(scene["reactive"]),
            )
            self.controllers[side].set_effect("Image")
        self.current_scene = name

    # ----- reload / command routing ---------------------------------------

    def _normalize_icons(self):
        names = self.icon_library.names()
        fallback = names[0] if names else None
        for side in SIDES:
            state = self.panels[side]["icon"]
            if state.get("icon") not in names:
                state["icon"] = fallback
                if fallback is None:
                    state.update(icon_enabled=False, transition_active=False)

    def reload_media(self):
        old_names = {
            side: self.media.name(self.panels[side]["image_index"]) for side in SIDES
        }
        self.media.reload()
        reload_icons = getattr(self.icon_library, "reload", None)
        if reload_icons:
            reload_icons()
            self.icon_library_revision += 1
        self._normalize_icons()
        for side in SIDES:
            self.panels[side]["image_index"] = 0
            self._stop_show(side)
            old_name = old_names[side]
            found = self.media.find_index(old_name) if old_name else None
            if found is not None:
                self.panels[side]["image_index"] = found
            if len(self.media):
                self.media.select(side, self.panels[side]["image_index"])

    def handle_command(self, data):
        if not isinstance(data, dict):
            return False
        command = data.get("command")
        value = data.get("value")

        if command == "set_target":
            self.set_target(value)
        elif command == "mirror_displays":
            self.set_mirrored(value)
        elif command == "info_scene":
            self.set_info_scene(value)
        elif command == "clock_sync":
            self.info_scenes.sync_time(value)
        elif command == "weather_update":
            self.info_scenes.set_weather(value)
        elif command == "scene_background":
            if (isinstance(value, dict) and value.get("scene") in INFO_SCENES
                    and value.get("background") in ("Black", "Sky")):
                self.info_scenes.backgrounds[value["scene"]] = value["background"]
        elif command == "schedule_update":
            self.info_scenes.schedule = clean_schedule(value)
            self.info_scenes.schedule_index = 0
            self.info_scenes.schedule_manual = False
        elif command == "schedule_append":
            self.info_scenes.schedule = clean_schedule(self.info_scenes.schedule + clean_schedule(value))
        elif command == "schedule_day":
            self.info_scenes.select_day(value)
        elif command == "schedule_step":
            self.info_scenes.step_schedule(value)
        elif command == "icon_background":
            if value in ("Black", "GIF"):
                for side in self.target_sides():
                    if (self.panels[side]["icon"]["icon_enabled"]
                            and self.panels[side]["icon"].get("background") != value):
                        self._begin_background_transition(side)
                    self.panels[side]["icon"]["background"] = value
        elif command == "effect":
            self.set_effect(value)
        elif command == "select_image":
            self.select_image(value)
        elif command == "filtered_step":
            self.step_filtered(value)
        elif command == "pixel_melt_next":
            self.pixel_melt_next(value)
        elif command == "intense_transition_next":
            self.intense_transition_next(value)
        elif command == "slideshow_start":
            self.start_show(value)
        elif command == "slideshow_stop":
            for side in self.target_sides():
                self._stop_show(side)
            self._mark_custom()
        elif command == "slideshow_beat_sync":
            self.set_beat_sync(value)
        elif command == "performance_scene":
            self.apply_scene(value)
        elif command == "text_settings":
            self.set_text_settings(value)
        elif command == "text_show":
            self.show_text(value)
        elif command == "text_hide":
            self.hide_text()
        elif command == "text_refresh":
            if isinstance(value, dict):
                self.set_text_settings(value)
        elif command == "icon_toggle":
            self.toggle_icon(str(value))
        elif command == "icon_clear":
            self.clear_icon()
        elif command == "icon_motion":
            self.set_icon_motion(str(value))
        elif command in (
            "icon_position",
            "icon_center",
            "icon_transition_settings",
        ):
            pass
        elif command == "brightness":
            self._master("brightness", value, 0.1, 1.0)
        elif command == "speed":
            self._master("speed", value, 0.1, 5.0)
        elif command == "toggle_pause":
            self.toggle_pause()
        elif command == "reload_library":
            self.reload_media()
        elif command == "audio_frame":
            self.signal_store.update_audio(value)
        elif command == "motion_frame":
            self.signal_store.update_motion(value)
        elif command == "reactive_enabled":
            self.set_reactive_enabled(value)
        elif command == "reactive_strength":
            self.set_reactive_strength(value)
        elif command == "reactive_preset":
            self.set_reactive_preset(value)
        elif command == "reactive_layer":
            self.set_layer(value)
        elif command == "transition_settings":
            self.set_transition(value)
        elif command == "guest_action":
            self.chaos_engine.trigger(value)
        elif command == "guest_xy":
            self.chaos_engine.update_xy(value)
        elif command == "guest_stop":
            self.chaos_engine.stop()
        elif command == "guest_lock":
            self.chaos_engine.set_locked(value)
        else:
            return bool(
                self.media.handle_command(
                    command, value, self.reference_index()
                )
            )
        return True

    # ----- frame update / rendering ---------------------------------------

    def update(self, dt):
        for side in ("front",) if self.mirrored else SIDES:
            self._refresh_media(side)
            controller = self.controllers[side]
            controller.update(dt)
            if not controller.paused:
                self.particles[side].update(dt)
            self.content_transitions[side].update(dt)
            self.scene_transitions[side].update(dt)
        self._update_shows(dt)
        self._update_icon_transitions()
        self.chaos_engine.update()

    def render(self, frame_number):
        signals = self.signals()
        for side in ("front",) if self.mirrored else SIDES:
            display = self.displays[side]
            controller = self.controllers[side]
            seed = 1000 if side == "back" else 0

            mode = self.panels[side]["info_scene"]
            if mode:
                self.info_scenes.render(mode, display, controller.time, signals)
            elif self._black_background(side):
                display.clear()
            else:
                controller.effect(display, controller.time)

            self.content_transitions[side].apply(display)
            self.content_snapshots[side] = copy_pixels(display)

            reactive = self.panels[side]["reactive"]
            if reactive["enabled"] and not mode:
                self.layer_engine.apply(
                    display,
                    signals,
                    reactive["layers"],
                    reactive["strength"],
                    frame_number,
                    seed,
                )

            text = self.panels[side]["text"]
            icon = self.panels[side]["icon"]
            text_enabled = bool(text.get("enabled", False)) and not mode
            if text_enabled:
                if text.get("background") == "Dimmed GIF":
                    self.text_engine.prepare_background(display, text)
                self.overlay_renderer.draw_text(
                    display,
                    text,
                    controller.time,
                    signals,
                    seed,
                    bottom=bool(icon.get("icon_enabled")),
                )
            icon_settings = dict(text)
            icon_settings["audio_reactivity"] = "Off"
            if not mode:
                self.overlay_renderer.draw_icon(
                    display,
                    icon,
                    icon_settings,
                    controller.time,
                    signals,
                    seed,
                    text_enabled=text_enabled,
                )

            self.scene_transitions[side].apply(display)
            self.scene_snapshots[side] = copy_pixels(display)

            if not mode:
                self.chaos_engine.apply(display, frame_number + seed, signals)

        if self.mirrored:
            self.displays["back"].copy_from(self.displays["front"])

        self.signal_store.end_frame()

    def step(self, dt, frame_number):
        self.update(dt)
        self.render(frame_number)

    # ----- controller state ------------------------------------------------

    def phone_panel(self, side):
        if self.mirrored:
            side = "front"
        controller = self.controllers[side]
        show = self.panels[side]["slideshow"]
        reactive = self.panels[side]["reactive"]
        transition = self.panels[side]["transition"]
        index = self.panels[side]["image_index"]
        info = self.media.info(index)
        out = {
            "effect": controller.effect_name,
            "speed": controller.speed,
            "brightness": controller.brightness,
            "paused": controller.paused,
            "image_index_zero": index,
            "image_index": index + 1 if info.get("image_name") else 0,
            "slideshow": {
                "active": show["active"],
                "duration": show["duration"],
                "shuffle": show["shuffle"],
                "label": show["label"],
                "count": len(show["indices"]),
                "beat_sync": show.get("beat_sync", False),
            },
            "reactive": {
                "enabled": reactive["enabled"],
                "strength": reactive["strength"],
                "preset": reactive["preset"],
                "layers": dict(reactive["layers"]),
            },
            "transition": dict(transition),
            "text": dict(self.panels[side]["text"]),
            "icon": dict(self.panels[side]["icon"]),
            "info_scene": self.panels[side]["info_scene"],
        }
        out.update(info)
        return out

    def controller_state(self):
        reference = self.phone_panel(self.reference_side())
        icon_errors = getattr(self.icon_library, "errors", [])
        return {
            "target": self.active_target,
            "reference_side": self.reference_side(),
            "image_count": len(self.media),
            "library": self.media.library_state(),
            "effects": list(self.controllers["front"].effects),
            "panels": {
                "front": self.phone_panel("front"),
                "back": self.phone_panel("back"),
            },
            "audio": {
                "volume": self.audio["volume"],
                "bass": self.audio["bass"],
                "mids": self.audio["mids"],
                "highs": self.audio["highs"],
                "beat": self.audio["beat"],
                "fresh": self.audio_fresh(),
            },
            "motion": dict(self.motion),
            "reactive_presets": list(REACTIVE_PRESETS),
            "layer_keys": list(LAYER_KEYS),
            "transitions": list(TRANSITIONS),
            "performance_scenes": list(self.scenes),
            "current_scene": self.current_scene,
            "info_scenes": list(INFO_SCENES),
            "mirrored": self.mirrored,
            "weather": dict(self.info_scenes.weather),
            "scene_backgrounds": dict(self.info_scenes.backgrounds),
            "schedule_count": len(self.info_scenes.schedule),
            "schedule_index": self.info_scenes.schedule_index,
            "schedule_day": self.info_scenes.schedule_day,
            "clock_ready": self.info_scenes.local_time() is not None,
            "text_fonts": list(TEXT_FONTS),
            "text_motions": list(TEXT_MOTIONS),
            "text_color_modes": list(TEXT_COLORS),
            "text_effects": list(TEXT_EFFECTS),
            "text_backgrounds": list(TEXT_BACKGROUNDS),
            "overlay_icons": self.icon_library.names(),
            "icon_library_revision": self.icon_library_revision,
            "icon_library_errors": list(icon_errors),
            "icon_motions": list(ICON_MOTIONS),
            "guest": self.chaos_engine.snapshot(),
            **reference,
        }
