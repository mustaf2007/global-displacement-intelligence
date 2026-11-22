import unittest

import pandas as pd

from src.quality import audit_population_data, reconciliation_by_period


class PopulationQualityTests(unittest.TestCase):
    def test_reports_duplicate_keys_missing_codes_and_invalid_values(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "area_ori_adm0": "_T", "obs_value": 10},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "area_ori_adm0": "_T", "obs_value": 10},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "", "area_ori_adm0": "_T", "obs_value": "bad"},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "FRA", "area_ori_adm0": "_T", "obs_value": -1},
        ])
        result = audit_population_data(frame)
        self.assertEqual(result["duplicate_dimension_key_rows"], 2)
        self.assertEqual(result["duplicate_dimension_key_groups"], 1)
        self.assertEqual(result["missing_geography_codes"], 1)
        self.assertEqual(result["invalid_population_values"], 1)
        self.assertEqual(result["negative_population_values"], 1)

    def test_reports_missing_required_columns(self):
        result = audit_population_data(pd.DataFrame({"obs_value": [1]}))
        self.assertEqual(result["status"], "invalid_schema")
        self.assertIn("pop_type", result["missing_columns"])

    def test_reconciles_only_unique_country_rows_against_explicit_total(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "_T", "area_ori_adm0": "_T", "obs_value": 200},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "SOM", "area_ori_adm0": "_T", "obs_value": 80},
        ])
        result = reconciliation_by_period(frame, "ref_area_adm0").iloc[0]
        self.assertEqual(result["country_sum"], 180)
        self.assertEqual(result["explicit_total"], 200)
        self.assertEqual(result["difference"], -20)
        self.assertEqual(result["status"], "compared_not_certified")

    def test_does_not_sum_duplicate_country_keys(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "_T", "area_ori_adm0": "_T", "obs_value": 200},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "area_ori_adm0": "_T", "obs_value": 100},
        ])
        result = reconciliation_by_period(frame, "ref_area_adm0").iloc[0]
        self.assertIsNone(result["country_sum"])
        self.assertEqual(result["duplicate_country_keys"], 1)
        self.assertEqual(result["status"], "duplicate_country_keys")


if __name__ == "__main__":
    unittest.main()
