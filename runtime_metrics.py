"""Small allocation-conscious timing metrics for CircuitPython hardware loops."""

import time


class TimingBucket:
    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = 0
        self.total_ms = 0.0
        self.max_ms = 0.0

    def add_seconds(self, seconds):
        ms = max(0.0, float(seconds) * 1000.0)
        self.samples += 1
        self.total_ms += ms
        if ms > self.max_ms:
            self.max_ms = ms

    def average_ms(self):
        return self.total_ms / self.samples if self.samples else 0.0

    def snapshot(self):
        return {
            "samples": self.samples,
            "avg_ms": self.average_ms(),
            "max_ms": self.max_ms,
        }


class RuntimeMetrics:
    """Collect coarse loop timings without affecting scheduling decisions.

    The future full S3 runtime can feed named timings such as ``decode``,
    ``render``, ``present``, ``http`` and ``audio``. Metrics are reset after each
    report window so long festival sessions do not accumulate unbounded state.
    """

    def __init__(self, report_seconds=5.0):
        self.report_seconds = float(report_seconds)
        self.started_at = time.monotonic()
        self.next_report_at = self.started_at + self.report_seconds
        self.frames = 0
        self.loops = 0
        self.buckets = {}

    def bucket(self, name):
        item = self.buckets.get(name)
        if item is None:
            item = TimingBucket()
            self.buckets[name] = item
        return item

    def add_timing(self, name, seconds):
        self.bucket(name).add_seconds(seconds)

    def frame(self):
        self.frames += 1

    def loop(self):
        self.loops += 1

    def due(self, now=None):
        now = time.monotonic() if now is None else float(now)
        return now >= self.next_report_at

    def snapshot(self, now=None, free_ram=None):
        now = time.monotonic() if now is None else float(now)
        elapsed = max(0.001, now - self.started_at)
        out = {
            "window_seconds": elapsed,
            "fps": self.frames / elapsed,
            "loops_per_second": self.loops / elapsed,
            "free_ram": free_ram,
            "timings": {},
        }
        for name, bucket in self.buckets.items():
            out["timings"][name] = bucket.snapshot()
        return out

    def reset(self, now=None):
        now = time.monotonic() if now is None else float(now)
        self.started_at = now
        self.next_report_at = now + self.report_seconds
        self.frames = 0
        self.loops = 0
        for bucket in self.buckets.values():
            bucket.reset()

    def take_report(self, now=None, free_ram=None):
        now = time.monotonic() if now is None else float(now)
        report = self.snapshot(now, free_ram=free_ram)
        self.reset(now)
        return report
