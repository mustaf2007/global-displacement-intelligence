import unittest

from src.ett_registry import append_observations
from src.ett_timeseries import build_ett_observations


class ETTRegistryTests(unittest.TestCase):
    def test_appends_a_new_period_without_mutating_existing(self):
        existing = build_ett_observations()
        incoming = [row.copy() for row in existing]
        for row in incoming:
            row["period_label"] = "Illustrative later period"
            row["period_start"] = "2026-11-05"
            row["period_end"] = "2026-11-09"
            row["source_url"] = "https://example.org/verified-report"
        combined = append_observations(existing, incoming)
        self.assertEqual(len(combined), len(existing) + len(incoming))
        self.assertEqual(existing[0]["period_start"], "2026-10-31")

    def test_rejects_duplicate_batch(self):
        rows = build_ett_observations()
        with self.assertRaises(ValueError):
            append_observations(rows, [rows[0]])

    def test_rejects_invalid_incoming_record(self):
        rows = build_ett_observations()
        bad = [rows[0].copy()]
        bad[0]["value"] = -10
        with self.assertRaises(ValueError):
            append_observations(rows, bad)

    def test_rejects_corrupted_existing_registry(self):
        rows = build_ett_observations()
        rows[0]["value"] = -1
        with self.assertRaises(ValueError):
            append_observations(rows, build_ett_observations())


if __name__ == "__main__":
    unittest.main()
