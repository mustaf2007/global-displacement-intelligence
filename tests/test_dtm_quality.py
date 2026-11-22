import unittest

import pandas as pd

from src.dtm_quality import profile_idp_data


class DTMQualityTests(unittest.TestCase):
    def test_valid_admin1_snapshot_passes_basic_checks(self):
        frame = pd.DataFrame({
            "admin1Name": ["Banaadir", "Bay"],
            "reportingDate": ["2026-10-01", "2026-10-01"],
            "numPresentIdpInd": [1200, 450],
        })
        result = profile_idp_data(frame, admin_level=1)
        self.assertEqual(result["status"], "passed_basic_checks")
        self.assertEqual(result["rows"], 2)

    def test_missing_required_column_is_reported(self):
        frame = pd.DataFrame({"admin1Name": ["Banaadir"]})
        result = profile_idp_data(frame, admin_level=1)
        self.assertEqual(result["status"], "incomplete_schema")
        self.assertIn("reportingDate", result["missing_required_columns"])

    def test_invalid_dates_counts_and_duplicates_are_reported(self):
        frame = pd.DataFrame({
            "admin2Name": ["District A", "District A", "District B"],
            "reportingDate": ["not-a-date", "not-a-date", "2026-10-01"],
            "numPresentIdpInd": ["unknown", -2, 100],
        })
        result = profile_idp_data(frame, admin_level=2)
        self.assertEqual(result["invalid_reporting_dates"], 2)
        self.assertEqual(result["invalid_population_values"], 1)
        self.assertEqual(result["negative_population_values"], 1)
        self.assertEqual(result["exact_duplicate_rows"], 0)
        self.assertEqual(result["status"], "review_required")

    def test_exact_duplicate_rows_are_flagged_not_removed(self):
        row = {
            "admin0Name": "Somalia",
            "reportingDate": "2026-10-01",
            "numPresentIdpInd": 100,
        }
        frame = pd.DataFrame([row, row])
        result = profile_idp_data(frame, admin_level=0)
        self.assertEqual(result["exact_duplicate_rows"], 1)
        self.assertEqual(len(frame), 2)

    def test_invalid_admin_level_is_rejected(self):
        with self.assertRaises(ValueError):
            profile_idp_data(pd.DataFrame(), admin_level=3)


if __name__ == "__main__":
    unittest.main()
