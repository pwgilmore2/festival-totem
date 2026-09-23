import unittest

from runtime_metrics import RuntimeMetrics, TimingBucket


class RuntimeMetricsTests(unittest.TestCase):
    def test_timing_bucket_tracks_average_and_max(self):
        bucket = TimingBucket()
        bucket.add_seconds(0.010)
        bucket.add_seconds(0.030)
        self.assertEqual(bucket.samples, 2)
        self.assertAlmostEqual(bucket.average_ms(), 20.0)
        self.assertAlmostEqual(bucket.max_ms, 30.0)

    def test_report_contains_named_timings_and_rates(self):
        metrics = RuntimeMetrics(report_seconds=5)
        start = metrics.started_at
        metrics.frame()
        metrics.frame()
        metrics.loop()
        metrics.loop()
        metrics.loop()
        metrics.add_timing("decode", 0.012)
        report = metrics.snapshot(start + 2.0, free_ram=123456)
        self.assertAlmostEqual(report["fps"], 1.0)
        self.assertAlmostEqual(report["loops_per_second"], 1.5)
        self.assertEqual(report["free_ram"], 123456)
        self.assertAlmostEqual(report["timings"]["decode"]["avg_ms"], 12.0)


if __name__ == "__main__":
    unittest.main()
