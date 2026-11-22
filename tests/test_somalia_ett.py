import unittest

from src.somalia_ett import get_week19_snapshot, validate_week19_snapshot


class SomaliaETTSnapshotTests(unittest.TestCase):
    def test_published_week19_snapshot_passes_arithmetic_checks(self):
        result = validate_week19_snapshot()
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["origin_total"], 10451)
        self.assertEqual(result["destination_total"], 10451)
        self.assertEqual(result["cause_share_total"], 100)

    def test_snapshot_has_16_unique_assessed_districts(self):
        snapshot = get_week19_snapshot()
        self.assertEqual(snapshot["districts_assessed"], 16)
        self.assertEqual(len(snapshot["districts"]), 16)
        self.assertEqual(len(set(snapshot["districts"])), 16)

    def test_validation_detects_non_reconciling_destination_data(self):
        snapshot = get_week19_snapshot()
        snapshot["destinations"][0]["arrivals"] += 1
        result = validate_week19_snapshot(snapshot)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["destination_distribution_reconciles"])

    def test_snapshot_returns_independent_copy(self):
        first = get_week19_snapshot()
        first["weekly_arrivals"] = 1
        self.assertEqual(get_week19_snapshot()["weekly_arrivals"], 10451)


if __name__ == "__main__":
    unittest.main()
