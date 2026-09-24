"""Small, asset-independent 64x32 scenes shared by desktop and CircuitPython.

Clock time and the festival's UTC offset are supplied by the phone. Weather is
supplied by the phone; this renderer never makes a network request.
"""

import math
import time

from text import FONT


SCENES = ("Clock", "Weather", "Set Times", "Waveform")
CONDITIONS = ("Clear", "Cloudy", "Rain", "Snow", "Wind")
FESTIVAL_DAYS = (("2026-09-30", "WED"), ("2026-10-01", "THU"),
                 ("2026-10-02", "FRI"), ("2026-10-03", "SAT"))


def clamp01(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def clean_schedule(value):
    if not isinstance(value, list):
        return []
    result = []
    for entry in value[:128]:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()[:36]
        when = str(entry.get("time", "")).strip()[:12]
        day = str(entry.get("day", "2026-09-30"))
        if name and day in (item[0] for item in FESTIVAL_DAYS):
            result.append({"name": name, "time": when, "day": day})
    return result


class InfoScenes:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.clock_epoch = None
        self.clock_at = 0.0
        self.clock_offset = 0
        self.weather = {"temperature": "", "condition": "Clear"}
        self.backgrounds = {"Clock": "Black", "Weather": "Sky", "Set Times": "Black", "Waveform": "Black"}
        self.schedule = []
        self.schedule_index = 0
        self.schedule_day = "Auto"
        self.schedule_manual = False

    def sync_time(self, value):
        offset = 0
        if isinstance(value, dict):
            offset = value.get("offset_seconds", 0)
            value = value.get("epoch")
        try:
            epoch = float(value)
            offset = int(offset)
        except (TypeError, ValueError, OverflowError):
            return False
        if not 946684800 <= epoch <= 4102444800 or not -50400 <= offset <= 50400:
            return False
        self.clock_epoch = epoch
        self.clock_offset = offset
        self.clock_at = time.monotonic()
        return True

    def local_time(self):
        if self.clock_epoch is None:
            return None
        return time.gmtime(int(self.clock_epoch + self.clock_offset + time.monotonic() - self.clock_at))

    def active_day(self, now=None):
        if self.schedule_day != "Auto":
            return self.schedule_day
        now = now or self.local_time()
        if now is None:
            return FESTIVAL_DAYS[0][0]
        date = "%04d-%02d-%02d" % (now.tm_year, now.tm_mon, now.tm_mday)
        days = [day for day, _ in FESTIVAL_DAYS]
        if date in days:
            index = days.index(date)
            if now.tm_hour < 9 and index > 0:
                index -= 1  # Overnight sets still belong to the previous evening.
            return days[index]
        if date == "2026-10-04" and now.tm_hour < 9:
            return days[-1]
        return days[0] if date < days[0] else days[-1]

    def day_schedule(self, now=None):
        day = self.active_day(now)
        return [entry for entry in self.schedule if entry["day"] == day]

    def select_day(self, day):
        if day != "Auto" and day not in (item[0] for item in FESTIVAL_DAYS):
            return
        self.schedule_day = day
        self.schedule_index = 0
        self.schedule_manual = False

    def step_schedule(self, direction):
        rows = self.day_schedule()
        if rows:
            self.schedule_index = (self.current_schedule_index(rows) + (1 if direction == 1 else -1)) % len(rows)
            self.schedule_manual = True

    def current_schedule_index(self, rows, now=None):
        if not rows:
            return 0
        if self.schedule_manual:
            return self.schedule_index % len(rows)
        now = now or self.local_time()
        if now is None or self.schedule_day != "Auto":
            return 0
        minutes = now.tm_hour * 60 + now.tm_min
        if now.tm_hour < 9:
            minutes += 1440
        selected = 0
        for index, row in enumerate(rows):
            parts = row["time"].upper().replace(" ", "")
            suffix = parts[-2:]
            try:
                if suffix in ("AM", "PM"):
                    hour, minute = (int(x) for x in parts[:-2].split(":"))
                    if not 1 <= hour <= 12:
                        continue
                    hour = hour % 12 + (12 if suffix == "PM" else 0)
                else:
                    hour, minute = (int(x) for x in parts.split(":"))
                    if not 0 <= hour <= 23:
                        continue
                if not 0 <= minute <= 59:
                    continue
            except (ValueError, IndexError):
                continue
            start = hour * 60 + minute + (1440 if hour < 9 else 0)
            if start <= minutes:
                selected = index
        return selected

    def set_weather(self, value):
        if not isinstance(value, dict):
            return
        temperature = str(value.get("temperature", "")).strip()[:6]
        if temperature and not (temperature.lstrip("-+").isdigit() and -99 <= int(temperature) <= 130):
            temperature = ""
        condition = str(value.get("condition", "Clear")).title()
        self.weather = {"temperature": temperature, "condition": condition if condition in CONDITIONS else "Clear"}

    def draw_label(self, display, value, y, color, scale=1):
        value = str(value).upper()
        width = len(value) * (5 * scale + 2) - 2
        x = (display.width - width) // 2
        for char in value:
            for dy, row in enumerate(FONT.get(char, FONT["?"])):
                for dx, point in enumerate(row):
                    if point == "1":
                        for py in range(scale):
                            for px in range(scale):
                                display.set_pixel(x + dx * scale + px, y + dy * scale + py, color)
            x += 5 * scale + 2

    def _sky(self, display, now, t, condition="Clear"):
        hour = now.tm_hour if now else 23
        daylight = 7 <= hour < 19
        dusk = 6 <= hour < 8 or 18 <= hour < 20
        if daylight:
            display.fill((2, 10, 17) if not dusk else (13, 5, 14))
            if condition == "Clear":
                x = int(display.width * (hour - 7) / 12)
                y = 6 + int(2 * math.sin(t * 0.65))
                for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                    display.set_pixel(x + dx, y + dy, (96, 70, 24) if dusk else (100, 82, 30))
        else:
            display.fill((2, 3, 10))
            for x, y in ((4, 5), (18, 3), (42, 7), (57, 4), (10, 15), (53, 18)):
                display.set_pixel(x, y, (32 + int(10 * (1 + math.sin(t * 2 + x))), 37, 65))
        if condition in ("Cloudy", "Rain", "Snow"):
            for x in (8 + int(t * 2) % 8, 46 - int(t) % 9):
                for dx, dy in ((0, 0), (1, 0), (2, 0), (1, -1)):
                    display.set_pixel(x + dx, 5 + dy, (26, 41, 55))
        if condition in ("Rain", "Snow"):
            for i in range(7):
                x = (i * 23 + (int(t * 8) if condition == "Rain" else int(t * 2))) % display.width
                y = (i * 11 + int(t * (12 if condition == "Rain" else 3))) % display.height
                display.set_pixel(x, y, (35, 65, 105) if condition == "Rain" else (70, 90, 105))
        elif condition == "Wind":
            for i in range(3):
                x = (i * 22 + int(t * 6)) % display.width
                display.set_pixel(x, 5 + i * 6, (35, 60, 85))
                display.set_pixel(x + 1, 5 + i * 6, (35, 60, 85))

    def render(self, mode, display, t, signals=None):
        display.clear()
        now = self.local_time()
        if mode == "Waveform":
            signals = signals or {}
            low = clamp01(signals.get("bass", 0))
            body = clamp01(signals.get("mids", 0))
            bright = clamp01(signals.get("highs", 0))
            energy = clamp01(signals.get("volume", 0))
            beat = bool(signals.get("beat", False))
            amplitude = 1.0 + low * 11 + energy * 3 + (3 if beat else 0)
            for x in range(display.width):
                phase = x * (0.17 + body * 0.12) - t * (2.0 + bright * 8)
                y = int(display.height / 2 + math.sin(phase) * amplitude * (0.45 + 0.55 * math.sin(x * math.pi / display.width) ** 2))
                color = (int(22 + bright * 150), int(85 + body * 150), int(145 + low * 100))
                display.set_pixel(x, y, color)
                if energy > .18:
                    display.set_pixel(x, y + 1, tuple(c // 4 for c in color))
            return
        if self.backgrounds.get(mode) == "Sky":
            self._sky(display, now, t, self.weather["condition"] if mode == "Weather" else "Clear")
        if mode == "Clock":
            if now is None:
                self.draw_label(display, "SET TIME", 12, (140, 185, 225))
            else:
                self.draw_label(display, "%02d:%02d" % (now.tm_hour, now.tm_min), 12, (235, 243, 255))
        elif mode == "Weather":
            temperature = self.weather["temperature"]
            self.draw_label(display, temperature + "F" if temperature else "--F", 3, (236, 243, 255), 2)
            self.draw_label(display, self.weather["condition"] if temperature else "NO DATA", 23, (125, 190, 220))
        elif mode == "Set Times":
            day = self.active_day(now)
            self.draw_label(display, dict(FESTIVAL_DAYS)[day], 1, (125, 190, 220))
            rows = self.day_schedule(now)
            if not rows:
                self.draw_label(display, "TIMES TBA", 15, (140, 185, 225))
            else:
                item = rows[self.current_schedule_index(rows, now)]
                self.draw_label(display, item["time"] or "TIME TBA", 10, (180, 234, 240))
                name = item["name"].upper()
                if len(name) * 7 - 2 > display.width:
                    name = name[:9]
                self.draw_label(display, name, 22, (235, 243, 255))
