import unittest

import pandas as pd

from src.dtm_explorer import explorer_coverage_summary, filter_idp_snapshot


class DTMExplorerTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "admin0Name": ["Somalia"] * 4,
            "admin1Name": ["Banaadir", "Banaadir", "Bay", "Bay"],
            "admin2Name": ["Hamar", "Dayniile", "Baidoa", "Diinsoor"],
            "reportingDate": [
                "2026-09-01", "2026-10-01", "2026-10-01", "2026-11-01"
            ],
            "numPresentIdpInd": [100, 120, 200, 240],
            "assessmentType": ["baseline", "round", "round", "round"],
        })

    def test_filters_by_date_and_admin_units_without_aggregation(self):
        result = filter_idp_snapshot(
            self.frame,
            2,
            admin1="Banaadir",
            from_date="2026-10-01",
            to_date="2026-10-31",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["admin2Name"], "Dayniile")
        self.assertEqual(result.iloc[0]["numPresentIdpInd"], 120)
        self.assertEqual(list(result.columns), list(self.frame.columns))

    def test_filter_returns_copy_and_does_not_mutate_source(self):
        original = self.frame.copy(deep=True)
        result = filter_idp_snapshot(self.frame, 1, admin1="Bay")
        result.loc[0, "numPresentIdpInd"] = 999
        pd.testing.assert_frame_equal(self.frame, original)

    def test_reversed_date_range_is_rejected(self):
        with self.assertRaises(ValueError):
            filter_idp_snapshot(
                self.frame, 1, from_date="2026-11-01", to_date="2026-09-01"
            )

    def test_missing_geography_field_is_rejected(self):
        with self.assertRaises(ValueError):
            filter_idp_snapshot(self.frame.drop(columns=["admin2Name"]), 2)

    def test_coverage_summary_describes_returned_records_only(self):
        result = explorer_coverage_summary(self.frame, 2)
        self.assertEqual(result["rows_returned"], 4)
        self.assertEqual(result["geographic_units_returned"], 4)
        self.assertEqual(result["earliest_reporting_date"], "2026-09-01")
        self.assertEqual(result["latest_reporting_date"], "2026-11-01")
        self.assertIn("does not establish complete", result["coverage_interpretation"])


if __name__ == "__main__":
    unittest.main()
