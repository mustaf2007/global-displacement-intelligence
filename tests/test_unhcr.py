import unittest
from unittest.mock import patch

import pandas as pd

from src.unhcr import UNHCRDataError, _fetch_all, country_ranking, explicit_global_total


class FetchAllTests(unittest.TestCase):
    @patch("src.unhcr._request_page")
    def test_fetches_every_page_until_has_next_is_false(self, request_page):
        request_page.side_effect = [
            {"data": [{"id": 1}], "pagination": {"has_next": True}},
            {"data": [{"id": 2}], "pagination": {"has_next": False}},
        ]
        result = _fetch_all({"c[pop_type]": "REF_UNHCR"}, max_pages=2)
        self.assertEqual(result["id"].tolist(), [1, 2])
        self.assertEqual(request_page.call_count, 2)

    @patch("src.unhcr._request_page")
    def test_raises_instead_of_returning_truncated_data_at_page_limit(self, request_page):
        request_page.return_value = {"data": [{"id": 1}], "pagination": {"has_next": True}}
        with self.assertRaises(UNHCRDataError):
            _fetch_all({}, max_pages=1)


class PopulationAggregationTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "ref_area_adm0_label": "Germany", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "TUR", "ref_area_adm0_label": "Türkiye", "area_ori_adm0": "_T", "obs_value": 80},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "_T", "ref_area_adm0_label": "Total", "area_ori_adm0": "_T", "obs_value": 200},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "DEU", "ref_area_adm0_label": "Germany", "area_ori_adm0": "SOM", "obs_value": 70},
            {"pop_type": "ASY", "time_period": "2026-06", "ref_area_adm0": "FRA", "ref_area_adm0_label": "France", "area_ori_adm0": "_T", "obs_value": 50},
        ])

    def test_country_ranking_filters_to_country_totals_and_selected_type(self):
        result = country_ranking(self.frame, "REF_UNHCR", "ref_area_adm0", "2026-06", limit=20)
        self.assertEqual(result["country"].tolist(), ["Germany", "Türkiye"])
        self.assertEqual(result["population"].tolist(), [100, 80])

    def test_explicit_global_total_is_not_sum_of_country_rows(self):
        self.assertEqual(explicit_global_total(self.frame, "REF_UNHCR", "2026-06"), 200)
        self.assertIsNone(explicit_global_total(self.frame, "ASY", "2026-06"))


if __name__ == "__main__":
    unittest.main()
