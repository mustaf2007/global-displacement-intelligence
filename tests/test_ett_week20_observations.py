import json
import unittest
from pathlib import Path


class ETTWeek20ObservationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "data" / "somalia_ett_observations.json"
        with path.open(encoding="utf-8") as handle:
            cls.rows = [row for row in json.load(handle) if row.get("period_start") == "2026-11-07"]

    def test_week20_has_23_report_derived_observations(self):
        self.assertEqual(len(self.rows), 23)

    def test_week20_headline_and_cumulative_values(self):
        national_flow = [r for r in self.rows if r["indicator"] == "new_arrivals" and r["geography_type"] == "national"]
        cumulative = [r for r in self.rows if r["indicator"] == "cumulative_arrivals_since_start"]
        self.assertEqual([r["value"] for r in national_flow], [10013])
        self.assertEqual([r["value"] for r in cumulative], [124566])

    def test_week20_origin_and_destination_marginals_reconcile_separately(self):
        for geography_type in ("origin_region", "destination_region"):
            values = [r["value"] for r in self.rows if r["geography_type"] == geography_type]
            self.assertEqual(sum(values), 10013)

    def test_week20_cause_shares_sum_to_100_without_other_hazards_imputation(self):
        causes = [r for r in self.rows if r["indicator"] == "reported_reason_share"]
        self.assertEqual(sum(r["value"] for r in causes), 100)
        self.assertEqual({r["category"] for r in causes}, {"Conflict", "Floods", "Drought", "Evictions"})


if __name__ == "__main__":
    unittest.main()
