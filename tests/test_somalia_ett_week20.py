import unittest

from src.somalia_ett_week20 import get_week20_snapshot, validate_week20_snapshot


class SomaliaETTWeek20Tests(unittest.TestCase):
    def test_published_week20_snapshot_passes_arithmetic_checks(self):
        result = validate_week20_snapshot()
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["origin_total"], 10013)
        self.assertEqual(result["destination_total"], 10013)
        self.assertEqual(result["cause_share_total"], 100)

    def test_week20_metadata_and_settlement_counts(self):
        snapshot = get_week20_snapshot()
        self.assertEqual(snapshot["period_start"], "2026-11-07")
        self.assertEqual(snapshot["period_end"], "2026-11-11")
        self.assertEqual(snapshot["districts_assessed"], 16)
        self.assertEqual(len(snapshot["districts"]), 16)
        self.assertEqual(snapshot["settlements_assessed"], 811)
        self.assertEqual(snapshot["idp_sites"], 641)
        self.assertEqual(snapshot["urban_settlement_share_pct"] + snapshot["rural_settlement_share_pct"], 100)

    def test_origin_and_destination_are_separate_marginals(self):
        snapshot = get_week20_snapshot()
        self.assertEqual(len(snapshot["origins"]), 10)
        self.assertEqual(len(snapshot["destinations"]), 7)
        self.assertEqual(sum(x["arrivals"] for x in snapshot["origins"]), 10013)
        self.assertEqual(sum(x["arrivals"] for x in snapshot["destinations"]), 10013)

    def test_validation_detects_non_reconciling_destination_data(self):
        snapshot = get_week20_snapshot()
        snapshot["destinations"][0]["arrivals"] += 1
        result = validate_week20_snapshot(snapshot)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["destination_distribution_reconciles"])

    def test_snapshot_returns_independent_copy(self):
        first = get_week20_snapshot()
        first["weekly_arrivals"] = 1
        self.assertEqual(get_week20_snapshot()["weekly_arrivals"], 10013)


if __name__ == "__main__":
    unittest.main()
