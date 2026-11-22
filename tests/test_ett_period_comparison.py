import unittest

from src.ett_timeseries import build_ett_observations
from src.ett_period_comparison import compare_ett_periods


class ETTPeriodComparisonTests(unittest.TestCase):
    def setUp(self):
        self.base = build_ett_observations()
        self.later = []
        for row in self.base:
            item = row.copy()
            item["period_label"] = "Week 20"
            item["period_start"] = "2026-11-07"
            item["period_end"] = "2026-11-11"
            if item["indicator"] == "new_arrivals":
                item["value"] = float(item["value"]) + 100
            self.later.append(item)

    def compare(self, rows):
        return compare_ett_periods(
            rows, "new_arrivals", "flow", "origin_region", "31 October–4 November 2026", "Week 20"
        )

    def test_shared_regions_are_compared_without_coverage_change(self):
        result, meta = self.compare(self.base + self.later)
        self.assertEqual(meta["status"], "comparable_coverage")
        self.assertEqual(meta["shared_units"], 10)
        self.assertTrue(meta["coverage_comparable"])
        self.assertEqual(result.iloc[0]["absolute_change"], 100)

    def test_added_region_is_flagged_not_filled(self):
        extra = next(row.copy() for row in self.later if row["geography_type"] == "origin_region")
        extra["geography"] = "New region"
        result, meta = self.compare(self.base + self.later + [extra])
        self.assertEqual(meta["status"], "partial_overlap")
        self.assertEqual(meta["added_units"], ["New region"])
        self.assertEqual(len(result), 10)

    def test_no_shared_units(self):
        changed = [row.copy() for row in self.later]
        for row in changed:
            if row["geography_type"] == "origin_region":
                row["geography"] = "Different " + row["geography"]
        result, meta = self.compare(self.base + changed)
        self.assertEqual(meta["status"], "no_shared_units")
        self.assertTrue(result.empty)

    def test_mixed_sources_are_not_combined(self):
        mixed = [row.copy() for row in self.later]
        mixed[0]["source"] = "Different source"
        result, meta = self.compare(self.base + mixed)
        self.assertEqual(meta["status"], "mixed_sources")
        self.assertTrue(result.empty)

    def test_changed_coverage_label_is_flagged(self):
        changed = [row.copy() for row in self.later]
        for row in changed:
            if row["geography_type"] == "origin_region":
                row["coverage"] = "complete"
        result, meta = self.compare(self.base + changed)
        self.assertEqual(meta["status"], "partial_overlap")
        self.assertFalse(meta["coverage_comparable"])
        self.assertEqual(len(result), 10)

    def test_duplicate_period_dimension_is_withheld(self):
        duplicate = next(row.copy() for row in self.later if row["geography_type"] == "origin_region")
        result, meta = self.compare(self.base + self.later + [duplicate])
        self.assertEqual(meta["status"], "duplicate_observations")
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
