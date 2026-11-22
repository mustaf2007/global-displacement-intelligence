import unittest

from src.ett_timeseries import build_ett_observations
from src.ett_trends import prepare_ett_trend, trend_readiness


class ETTTrendTests(unittest.TestCase):
    def setUp(self):
        self.rows = build_ett_observations()

    def test_single_period_is_not_ready_for_trend(self):
        trend = prepare_ett_trend(self.rows, "new_arrivals", "flow", "national", "Somalia")
        self.assertEqual(len(trend), 1)
        self.assertFalse(trend_readiness(trend)["ready"])

    def test_two_periods_are_comparable_when_same_measure(self):
        later = [row.copy() for row in self.rows]
        for row in later:
            row["period_label"] = "5–9 November 2026"
            row["period_start"] = "2026-11-05"
            row["period_end"] = "2026-11-09"
        trend = prepare_ett_trend(self.rows + later, "new_arrivals", "flow", "national", "Somalia")
        self.assertEqual(len(trend), 2)
        self.assertTrue(trend_readiness(trend)["ready"])

    def test_weekly_and_cumulative_measures_stay_separate(self):
        weekly = prepare_ett_trend(self.rows, "new_arrivals", "flow", "national", "Somalia")
        cumulative = prepare_ett_trend(self.rows, "cumulative_arrivals_since_start", "cumulative_flow", "national", "Somalia")
        self.assertEqual(len(weekly), 1)
        self.assertEqual(len(cumulative), 1)
        self.assertNotEqual(weekly.iloc[0]["value"], cumulative.iloc[0]["value"])

    def test_duplicate_period_observation_is_withheld(self):
        duplicate = self.rows[0].copy()
        trend = prepare_ett_trend(self.rows + [duplicate], "new_arrivals", "flow", "national", "Somalia")
        self.assertTrue(trend.empty)

    def test_no_data_returns_empty(self):
        trend = prepare_ett_trend([], "new_arrivals", "flow", "national", "Somalia")
        self.assertTrue(trend.empty)


if __name__ == "__main__":
    unittest.main()
