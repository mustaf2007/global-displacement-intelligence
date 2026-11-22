import unittest

import pandas as pd

from src.quality import audit_population_data


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


if __name__ == "__main__":
    unittest.main()
