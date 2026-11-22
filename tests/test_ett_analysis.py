import unittest

from src.ett_timeseries import build_ett_observations
from src.ett_analysis import regional_distribution, driver_distribution, distribution_summary


class ETTAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = build_ett_observations()

    def test_origin_distribution_ranks_and_shares(self):
        dist = regional_distribution(self.rows, "origin_region")
        self.assertEqual(dist.iloc[0]["region"], "Bay")
        self.assertEqual(int(dist["arrivals"].sum()), 10451)
        self.assertAlmostEqual(dist["share_pct"].sum(), 100.0)

    def test_destination_distribution_is_separate(self):
        dist = regional_distribution(self.rows, "destination_region")
        self.assertEqual(dist.iloc[0]["region"], "Gedo")
        self.assertEqual(int(dist["arrivals"].sum()), 10451)
        self.assertNotEqual(dist.iloc[0]["region"], "Bay")

    def test_driver_shares_and_rank(self):
        dist = driver_distribution(self.rows)
        self.assertEqual(dist.iloc[0]["reason"], "Conflict")
        self.assertEqual(float(dist["share_pct"].sum()), 100.0)

    def test_distribution_summary_is_within_dimension(self):
        dist = regional_distribution(self.rows, "origin_region")
        summary = distribution_summary(dist)
        self.assertEqual(summary["top_region"], "Bay")
        self.assertGreater(summary["hhi"], 0)
        self.assertLessEqual(summary["hhi"], 1)

    def test_duplicate_region_is_rejected(self):
        rows = self.rows + [self.rows[2].copy()]
        with self.assertRaises(ValueError):
            regional_distribution(rows, "origin_region")

    def test_invalid_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            regional_distribution(self.rows, "route")


if __name__ == "__main__":
    unittest.main()
