import unittest

from src.ett_timeseries import build_ett_observations, validate_ett_observations


class ETTTimeSeriesTests(unittest.TestCase):
    def test_week19_builds_normalized_observations(self):
        rows = build_ett_observations()
        result = validate_ett_observations(rows)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["row_count"], 21)
        self.assertEqual({row["measure_type"] for row in rows}, {"flow", "cumulative_flow", "percentage"})

    def test_stock_and_flow_are_not_conflated(self):
        rows = build_ett_observations()
        self.assertEqual(rows[0]["measure_type"], "flow")
        self.assertEqual(rows[1]["measure_type"], "cumulative_flow")
        self.assertNotEqual(rows[0]["indicator"], "idp_population_stock")

    def test_duplicate_observation_is_flagged(self):
        rows = build_ett_observations()
        result = validate_ett_observations(rows + [rows[0].copy()])
        self.assertFalse(result["checks"]["observation_keys_unique"])

    def test_negative_and_non_numeric_values_are_flagged(self):
        rows = build_ett_observations()
        rows[0]["value"] = -1
        result = validate_ett_observations(rows)
        self.assertFalse(result["checks"]["values_non_negative_numeric"])

    def test_missing_required_field_is_flagged(self):
        rows = build_ett_observations()
        del rows[0]["source_url"]
        result = validate_ett_observations(rows)
        self.assertFalse(result["checks"]["required_fields_present"])

    def test_unmapped_period_is_not_guessed(self):
        rows = build_ett_observations()
        rows[0]["period_label"] = "Unverified date range"
        with self.assertRaises(ValueError):
            build_ett_observations({"period": "Unverified date range"})


if __name__ == "__main__":
    unittest.main()
