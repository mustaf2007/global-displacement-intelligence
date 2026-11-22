import unittest
from unittest.mock import patch

import pandas as pd

from src.unhcr import UNHCRDataError, _fetch_all, country_ranking, explicit_global_total, population_types, population_period_coverage, country_period_changes, population_measure_type, explicit_total_trend, country_pressure_signals


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

    def test_population_types_use_valid_idp_subcategories(self):
        self.assertIn("IDP_UNHCR", population_types())
        self.assertIn("IDP_IDMC", population_types())
        self.assertNotIn("IDP", population_types())
        self.assertIn("RET", population_types())
        self.assertIn("RDP", population_types())
        self.assertIn("NAT", population_types())
        self.assertIn("RASP", population_types())


class HistoricalRangeLoadTests(unittest.TestCase):
    @patch("src.unhcr._fetch_all")
    def test_loads_from_1960_and_validates_returned_records(self, fetch_all):
        from src.unhcr import load_population_data

        fetch_all.return_value = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "1960", "obs_value": "125"},
            {"pop_type": "REF_UNHCR", "time_period": "2026", "obs_value": "250"},
        ])
        result = load_population_data("REF_UNHCR")
        params = fetch_all.call_args.args[0]
        self.assertEqual(params["time_period"], "ge:1960")
        self.assertEqual(params["c[pop_type]"], "REF_UNHCR")
        self.assertEqual(result["time_period"].tolist(), ["1960", "2026"])
        self.assertEqual(result["obs_value"].tolist(), [125, 250])

    @patch("src.unhcr._fetch_all")
    def test_raises_when_no_history_is_returned(self, fetch_all):
        from src.unhcr import load_population_data

        fetch_all.return_value = pd.DataFrame()
        with self.assertRaises(UNHCRDataError):
            load_population_data("STA")


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



class HistoricalCoverageTests(unittest.TestCase):
    @patch("src.unhcr._fetch_all")
    def test_groups_observations_by_available_reporting_period(self, fetch_all):
        fetch_all.return_value = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2024-06"},
            {"pop_type": "REF_UNHCR", "time_period": "2024-06"},
            {"pop_type": "REF_UNHCR", "time_period": "2025-06"},
            {"pop_type": "ASY", "time_period": "2025-06"},
        ])
        result = population_period_coverage("REF_UNHCR")
        self.assertEqual(result["time_period"].tolist(), ["2024-06", "2025-06"])
        self.assertEqual(result["record_count"].tolist(), [2, 1])
        self.assertEqual(fetch_all.call_args.args[0]["dimensions"], "pop_type,time_period")

    @patch("src.unhcr._fetch_all")
    def test_returns_empty_coverage_when_no_records(self, fetch_all):
        fetch_all.return_value = pd.DataFrame(columns=["pop_type", "time_period"])
        result = population_period_coverage("STA")
        self.assertTrue(result.empty)


class CountryPeriodChangeTests(unittest.TestCase):
    def test_compares_only_countries_present_in_both_periods(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2024-06", "ref_area_adm0": "AAA", "ref_area_adm0_label": "Aland", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2025-06", "ref_area_adm0": "AAA", "ref_area_adm0_label": "Aland", "area_ori_adm0": "_T", "obs_value": 150},
            {"pop_type": "REF_UNHCR", "time_period": "2024-06", "ref_area_adm0": "BBB", "ref_area_adm0_label": "Borland", "area_ori_adm0": "_T", "obs_value": 50},
            {"pop_type": "REF_UNHCR", "time_period": "2025-06", "ref_area_adm0": "CCC", "ref_area_adm0_label": "Corland", "area_ori_adm0": "_T", "obs_value": 70},
        ])
        result = country_period_changes(frame, "REF_UNHCR", "ref_area_adm0", "2024-06", "2025-06")
        self.assertEqual(result["country_code"].tolist(), ["AAA"])
        self.assertEqual(result.iloc[0]["absolute_change"], 50)
        self.assertEqual(result.iloc[0]["percentage_change"], 50)

    def test_withholds_results_when_dimension_keys_are_duplicated(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2024-06", "ref_area_adm0": "AAA", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2024-06", "ref_area_adm0": "AAA", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2025-06", "ref_area_adm0": "AAA", "area_ori_adm0": "_T", "obs_value": 150},
        ])
        result = country_period_changes(frame, "REF_UNHCR", "ref_area_adm0", "2024-06", "2025-06")
        self.assertTrue(result.empty)


class PopulationMeasureTests(unittest.TestCase):
    def test_unhcr_solution_categories_are_flows(self):
        for code in ("RET", "RDP", "NAT", "RASP"):
            self.assertEqual(population_measure_type(code), "flow")
        self.assertEqual(population_measure_type("REF_UNHCR"), "stock")
        self.assertEqual(population_measure_type("IDP_IDMC"), "stock")

    def test_explicit_total_trend_never_sums_country_records(self):
        frame = pd.DataFrame([
            {"pop_type": "REF_UNHCR", "time_period": "2025-06", "ref_area_adm0": "_T", "area_ori_adm0": "_T", "obs_value": 200},
            {"pop_type": "REF_UNHCR", "time_period": "2025-06", "ref_area_adm0": "AAA", "area_ori_adm0": "_T", "obs_value": 100},
            {"pop_type": "REF_UNHCR", "time_period": "2026-06", "ref_area_adm0": "AAA", "area_ori_adm0": "_T", "obs_value": 120},
        ])
        result = explicit_total_trend(frame, "REF_UNHCR")
        self.assertEqual(result["time_period"].tolist(), ["2025-06"])
        self.assertEqual(result["population"].tolist(), [200])

if __name__ == "__main__":
    unittest.main()
