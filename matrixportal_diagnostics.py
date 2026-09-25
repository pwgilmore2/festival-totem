"""One-shot, serial-only profiling tour through the real board runtime.

No onboard log files are created: CIRCUITPY has previously had FAT damage.
Each stage includes its transition and a separate steady playback window.
"""

import gc
import json
import time

from runtime_metrics import TimingBucket
from transition_engine import INTENSE_TRANSITIONS
from visual_engine import TRANSITIONS
from text_engine import TEXT_FONTS


CHAOS_MODES = ("chaos", "glitch", "rainbow", "trance", "liquid",
               "warp", "prism", "tunnel", "pixelmelt", "meltdown",
               "jumble", "bassjostle", "xyintent")


class PhaseStats:
    def __init__(self):
        self.started = time.monotonic()
        self.frames = 0
        self.last_frame = None
        self.intervals = []
        self.timings = {}
        self.low_ram = gc.mem_free()

    def timing(self, label, seconds):
        bucket = self.timings.get(label)
        if bucket is None:
            bucket = TimingBucket()
            self.timings[label] = bucket
        bucket.add_seconds(seconds)

    def frame(self, now):
        self.frames += 1
        if self.last_frame is not None:
            self.intervals.append((now - self.last_frame) * 1000)
        self.last_frame = now
        if self.frames % 15 == 0:
            self.low_ram = min(self.low_ram, gc.mem_free())

    def report(self, elapsed):
        intervals = sorted(self.intervals)
        n = len(intervals)
        timing = {}
        for key, value in self.timings.items():
            if value.samples:
                timing[key] = [round(value.average_ms(), 1),
                               round(value.max_ms, 1), value.samples]
        return {"seconds": round(max(.001, elapsed), 2),
                "frames": self.frames,
                "fps": round(self.frames / max(.001, elapsed), 2),
                "p95_ms": round(intervals[min(n - 1, int(n * .95))], 1) if n else None,
                "max_gap_ms": round(intervals[-1], 1) if n else None,
                "gaps_over_50": sum(v > 50 for v in intervals),
                "gaps_over_100": sum(v > 100 for v in intervals),
                "low_ram": self.low_ram,
                "timings_ms": timing}


def stage_catalog(runtime, media):
    stages = [("media", "GIF", i) for i in range(len(media))]
    stages.extend(("effect", "Effect/" + name, name)
                  for name in runtime.base_effects)
    stages.extend(("chaos", "Chaos/" + name, name) for name in CHAOS_MODES)
    stages.extend(("transition", "Content/" + name, name)
                  for name in TRANSITIONS if name != "None")
    stages.extend(("intense", "Scene/" + name, name)
                  for name in INTENSE_TRANSITIONS)
    stages.extend(("info", "Info/" + name, name)
                  for name in ("Clock", "Set Times", "Waveform"))
    stages.extend(("text", "Text/" + name, name) for name in TEXT_FONTS)
    stages.extend(("icon", "Icon/" + name, name)
                  for name in runtime.icon_library.names())
    stages.extend(("overlay", "Overlay/" + kind, kind)
                  for kind in ("Black", "Dimmed", "Orbit", "Audio"))
    stages.extend(("reactive_preset", "Audio/" + kind, kind)
                  for kind in ("Pulse", "Spark", "Neon", "Chaos"))
    stages.extend(("preset_scene", "Preset/" + name, name)
                  for name in runtime.scenes)
    stages.extend((("reactive", "Audio/synthetic", None),
                   ("slideshow", "Slideshow", None),
                   ("independent", "Independent/two panels", None)))
    return stages


class BoardDiagnostics:
    def __init__(self, runtime, media, backend, stage_seconds=5.0,
                 startup_seconds=7.0):
        self.runtime = runtime
        self.media = media
        self.backend = backend
        self.stages = stage_catalog(runtime, media)
        self.stage_seconds = stage_seconds
        self.warmup_seconds = min(1.25, stage_seconds * .4)
        self.min_frames = min(40, int(stage_seconds * 8))
        self.min_steady_frames = min(20, int(stage_seconds * 4))
        self.max_stage_seconds = max(stage_seconds * 2.4, stage_seconds + 2)
        self.ready_at = time.monotonic() + startup_seconds
        self.index = -1
        self.current_started = 0.0
        self.early = None
        self.steady = None
        self.failures = []
        self.done = False
        self._last_index = 0
        self.pending = None
        self.prepare_started = 0.0
        self.prepare_frames = 0
        self.force_advance = False
        self.finishing_at = None
        self.finishing_frames = 0
        print("DIAG_READY stages", len(self.stages), "gifs", len(media),
              "starts_in_seconds", startup_seconds)

    def profile(self, label, seconds):
        if self.index < 0 or self.done or self.pending or self.finishing_at is not None:
            return
        now = time.monotonic()
        active = self.early if now - self.current_started < self.warmup_seconds else self.steady
        active.timing(label, seconds)

    def frame(self, now):
        if self.index < 0 or self.done:
            return
        if self.finishing_at is not None:
            self.finishing_frames += 1
            return
        if self.pending:
            self.prepare_frames += 1
            return
        active = self.early if now - self.current_started < self.warmup_seconds else self.steady
        active.frame(now)

    def tick(self, now):
        if self.done or now < self.ready_at:
            return
        if self.finishing_at is not None:
            if ((now - self.finishing_at >= 3 and self.finishing_frames >= 2)
                    or now - self.finishing_at >= 15):
                self._finish()
            return
        if self.pending:
            if now - self.prepare_started < .9 or self.prepare_frames < 2:
                if now - self.prepare_started >= 18:
                    self.skip_current(RuntimeError("No two source frames presented in 18 seconds"))
                else:
                    return
            if self.force_advance:
                return
            kind, value = self.pending
            self.pending = None
            self.early = PhaseStats()
            self.steady = PhaseStats()
            self.current_started = time.monotonic()
            print("DIAG_BEGIN", self.index + 1, "/", len(self.stages),
                  self.stages[self.index][1], "prepared_frames", self.prepare_frames)
            try:
                self._activate_transition(kind, value)
            except Exception as exc:
                self.skip_current(exc)
            return
        if self.index >= 0:
            elapsed = now - self.current_started
            total_frames = self.early.frames + self.steady.frames
            enough = (elapsed >= self.stage_seconds and total_frames >= self.min_frames
                      and self.steady.frames >= self.min_steady_frames)
            if (not self.force_advance and not enough
                    and (elapsed < self.max_stage_seconds or total_frames < 2)
                    and elapsed < max(25, self.max_stage_seconds)):
                return
        if self.index >= 0:
            label = self.stages[self.index][1]
            early = self.early.report(self.warmup_seconds)
            steady = self.steady.report(max(.001, now - self.current_started - self.warmup_seconds))
            steady_ok = (steady["fps"] >= 27 and steady["p95_ms"] is not None
                         and steady["p95_ms"] <= 40 and steady["gaps_over_100"] == 0)
            if not steady_ok and not self.force_advance:
                self.failures.append((label, steady["fps"], steady["p95_ms"]))
            status = "ERROR" if self.force_advance else ("PASS" if steady_ok else "SLOW")
            result = {"name": label, "status": status,
                      "transition": early, "steady": steady}
            if len(self.media) == 1 and self.stages[self.index][0] in ("slideshow", "independent"):
                result["note"] = "Single GIF: no distinct second image"
            elif len(self.media) == 1 and self.stages[self.index][0] in ("transition", "intense"):
                result["note"] = "Rainbow source to only GIF"
            print("DIAG_STAGE", json.dumps(result))
        self.index += 1
        if self.index >= len(self.stages):
            self._restore()
            self.runtime.set_overlay_background("Black")
            self.runtime.show_text({"message": "DONE", "font": "Pixel", "scale": 1,
                                    "color_mode": "Solid", "color": "#00ff00"})
            self.finishing_at = time.monotonic()
            self.finishing_frames = 0
            print("DIAG_FINISHING waiting_for_DONE_to_appear")
            return
        kind, label, value = self.stages[self.index]
        self.early = PhaseStats()
        self.steady = PhaseStats()
        self.current_started = time.monotonic()
        self.force_advance = False
        try:
            self._enter(kind, value)
            if self.pending:
                print("DIAG_PREP", self.index + 1, "/", len(self.stages),
                      label, "waiting_for_visible_source")
            else:
                print("DIAG_BEGIN", self.index + 1, "/", len(self.stages), label)
        except Exception as exc:
            print("DIAG_ERROR", label, type(exc).__name__, str(exc))
            self.failures.append((label, "error", str(exc)))
            self.force_advance = True

    def skip_current(self, exc):
        if self.index >= len(self.stages):
            print("DIAG_ERROR", "Done screen", type(exc).__name__, str(exc))
            self.failures.append(("Done screen", "error", str(exc)))
            self._finish()
            return
        label = self.stages[self.index][1]
        print("DIAG_ERROR", label, type(exc).__name__, str(exc))
        self.failures.append((label, "error", str(exc)))
        self.force_advance = True
        self.pending = None

    def _finish(self):
        self.done = True
        print("DIAG_DONE", json.dumps({"stages": len(self.stages),
                                      "slow_count": len(self.failures),
                                      "slow": self.failures}))

    def _reset(self):
        rt = self.runtime
        rt.set_transition({"kind": "None", "random": False})
        rt.chaos_engine._clear()
        for side in ("front", "back"):
            rt._stop_show(side)
            for transition in (rt.content_transitions[side], rt.scene_transitions[side]):
                transition.active = False
                transition.source = None
        rt.hide_text(animate=False)
        for side in ("front", "back"):
            rt._set_icon_enabled(side, False, False)
        rt.set_overlay_background("None")
        rt.set_overlay_audio_reactivity("Off")
        rt.set_icon_motion("Bounce")
        rt.set_info_scene(None)
        rt.set_mirrored(True)
        rt.set_reactive_enabled(False)

    def _enter(self, kind, value):
        rt = self.runtime
        self._reset()
        if kind == "media":
            rt.set_effect("Image")
            rt.select_image(value)
            self._last_index = value
        elif kind == "effect":
            rt.set_effect(value)
        elif kind == "chaos":
            rt.set_effect("Image")
            rt.chaos_engine.trigger({"kind": value, "strength": .85, "duration": 15})
            if value == "xyintent":
                rt.chaos_engine.update_xy({"x": .85, "y": .72, "velocity": .7})
        elif kind == "transition":
            rt.set_effect("Image")
            if len(self.media) == 1:
                rt.set_effect("Rainbow")
                self.pending = (kind, value)
                self.prepare_started = time.monotonic()
                self.prepare_frames = 0
            else:
                self._activate_transition(kind, value)
        elif kind == "intense":
            if len(self.media) == 1:
                rt.set_effect("Rainbow")
                self.pending = (kind, value)
                self.prepare_started = time.monotonic()
                self.prepare_frames = 0
            else:
                rt.set_effect("Image")
                self._activate_transition(kind, value)
        elif kind == "info":
            rt.info_scenes.sync_time({"epoch": 1790380000, "offset_seconds": -18000})
            rt.info_scenes.set_weather({"temperature": "72", "condition": "Clear"})
            rt.info_scenes.schedule = [{"name": "DIAGNOSTIC", "time": "20:00",
                                        "day": "2026-09-30"}]
            rt.set_info_scene(value)
        elif kind == "text":
            rt.show_text({"message": "FESTIVAL TEST", "font": value,
                          "scale": 1, "color_mode": "Solid", "color": "#ffffff"})
        elif kind == "icon":
            rt.toggle_icon(value)
        elif kind == "overlay":
            names = rt.icon_library.names()
            if names:
                rt.toggle_icon(names[0])
            if value in ("Black", "Dimmed"):
                rt.set_overlay_background(value)
            elif value == "Orbit":
                rt.set_icon_motion("Orbit")
            else:
                rt.set_overlay_audio_reactivity("Intense")
                rt.signal_store.update_audio({"volume": .8, "bass": .9,
                                              "highs": .7, "beat": True})
        elif kind == "reactive_preset":
            rt.set_reactive_enabled(True)
            rt.set_reactive_preset(value)
            rt.signal_store.update_audio({"volume": .8, "bass": .9,
                                          "mids": .65, "highs": .8, "beat": True})
        elif kind == "preset_scene":
            rt.apply_scene(value)
        elif kind == "reactive":
            rt.set_reactive_enabled(True)
            rt.set_reactive_preset("Chaos")
            rt.signal_store.update_audio({"volume": .8, "bass": .9,
                                          "mids": .65, "highs": .8, "beat": True})
        elif kind == "slideshow":
            rt.set_transition({"kind": "Fade", "duration": .45})
            rt.start_show({"indices": list(range(len(self.media))),
                           "duration": 1.0, "shuffle": False})
        elif kind == "independent":
            rt.set_mirrored(False)
            rt.set_target("back")
            rt.set_effect("Image")
            rt.select_image(min(1, len(self.media) - 1))
            rt.set_target("both")

    def _activate_transition(self, kind, value):
        rt = self.runtime
        if kind == "transition":
            rt.set_transition({"kind": value, "duration": .65})
            if len(self.media) > 1:
                self._last_index = (rt.panels["front"]["image_index"] + 1) % len(self.media)
                rt.select_image(self._last_index)
            else:
                rt.set_effect("Image")
        else:
            rt.intense_transition_next({"kind": value, "duration": .65,
                                       "indices": list(range(len(self.media)))})

    def _restore(self):
        self._reset()
        self.runtime.set_effect("Image")
        self.runtime.select_image(0)
