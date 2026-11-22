import unittest

import pandas as pd

from src.dtm_advanced_quality import advanced_idp_quality_report


class DTMAadvancedQualityTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "admin1Name": ["Bay", "Bay", "Banaadir", "Banaadir"],
            "admin1Pcode": ["SO080", "SO080", "SO010", "SO010"],
            "admin2Name": ["Baidoa", "Baidoa", "Dayniile", "Dayniile"],
            "admin2Pcode": ["SO0801", "SO0801", "SO0101", "SO0101"],
            "reportingDate": ["2024-01-01", "2024-02-01", "2024-01-15", "2024-02-15"],
            "numPresentIdpInd": [100, 110, 200, 210],
            "numberMales": [None, 50, None, 100],
            "numberFemales": [None, 60, None, 110],
            "idpOriginAdmin1Name": ["Bay", None, "Banaadir", None],
            "idpOriginAdmin1Pcode": ["SO080", None, "SO010", None],
            "operation": ["Baseline", "Baseline", "Monitoring", "Monitoring"],
            "assessmentType": ["BA", "BA", "BA", "BA"],
        })

    def test_district_report_includes_unit_date_coverage(self):
        result = advanced_idp_quality_report(self.frame, 2)
        self.assertEqual(result["geography"]["unique_names"], 2)
        self.assertEqual(result["temporal"]["unique_reporting_dates"], 4)
        self.assertEqual(result["temporal"]["latest_reporting_date"], "2024-02-15")
        self.assertEqual(len(result["unit_reporting_coverage"]), 2)
        self.assertEqual(result["unit_reporting_coverage"][0]["geographic_code"], "SO0101")

    def test_parent_mapping_and_code_name_consistency(self):
        result = advanced_idp_quality_report(self.frame, 2)
        self.assertEqual(result["geography"]["codes_mapping_to_multiple_names"], 0)
        self.assertEqual(result["geography"]["names_mapping_to_multiple_codes"], 0)
        self.assertEqual(result["parent_geography"]["district_or_unit_codes_with_multiple_parents"], 0)
        broken = self.frame.copy()
        broken.loc[1, "admin1Pcode"] = "SO999"
        result = advanced_idp_quality_report(broken, 2)
        self.assertEqual(result["parent_geography"]["district_or_unit_codes_with_multiple_parents"], 1)

    def test_demographic_missingness_and_provenance_are_reported(self):
        result = advanced_idp_quality_report(self.frame, 2)
        missing = {item["field"]: item["missing_percent"] for item in result["demographic_missingness"]}
        self.assertEqual(missing["numberMales"], 50.0)
        self.assertEqual(missing["idpOriginAdmin1Name"], 50.0)
        self.assertEqual(len(result["provenance_breakdown"]["operation"]), 2)

    def test_report_does_not_mutate_source(self):
        original = self.frame.copy(deep=True)
        advanced_idp_quality_report(self.frame, 2)
        pd.testing.assert_frame_equal(self.frame, original)

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(TypeError):
            advanced_idp_quality_report([], 2)
        with self.assertRaises(ValueError):
            advanced_idp_quality_report(self.frame, 3)

    def test_freshness_threshold_flags_units_individually(self):
        result = advanced_idp_quality_report(self.frame, 2, as_of="2024-03-01", stale_after_days=20)
        statuses = {row["geographic_unit"]: row["freshness_status"] for row in result["unit_reporting_coverage"]}
        self.assertEqual(statuses["Baidoa"], "Stale")
        self.assertEqual(statuses["Dayniile"], "Within threshold")
        self.assertEqual(result["freshness"]["units_stale"], 1)
        self.assertEqual(result["freshness"]["units_within_threshold"], 1)

    def test_missing_dates_are_not_marked_as_zero_or_fresh(self):
        frame = self.frame.copy()
        frame["reportingDate"] = None
        result = advanced_idp_quality_report(frame, 2, as_of="2024-03-01")
        self.assertEqual(result["freshness"]["units_without_valid_dates"], 2)
        self.assertTrue(all(row["freshness_status"] == "No valid reporting date" for row in result["unit_reporting_coverage"]))

    def test_negative_freshness_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            advanced_idp_quality_report(self.frame, 2, stale_after_days=-1)


if __name__ == "__main__":
    unittest.main()
