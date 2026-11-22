import unittest

from src.ett_dataset_ingest import inspect_dataset_rows, normalize_dataset_rows


class ETTDatasetInspectionTests(unittest.TestCase):
    def test_profiles_columns_without_interpreting_them(self):
        rows = [
            {"District": "Baidoa", "Count": 10, "Week": "W19"},
            {"District": "Doolow", "Count": 20, "Week": "W19"},
        ]
        result = inspect_dataset_rows(rows)
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["column_count"], 3)
        self.assertEqual(result["column_profile"]["Count"]["observed_types"], ["int"])
        self.assertEqual(result["normalization_status"], "not_normalized_mapping_required")
        self.assertIn("No indicator", result["warning"])

    def test_reports_missing_values_and_duplicates(self):
        rows = [
            {"location": "A", "value": 3},
            {"location": "A", "value": 3},
            {"location": "B", "value": None},
        ]
        result = inspect_dataset_rows(rows)
        self.assertEqual(result["exact_duplicate_row_count"], 1)
        self.assertEqual(result["column_profile"]["value"]["null_count"], 1)

    def test_rejects_empty_or_non_dictionary_input(self):
        with self.assertRaises(ValueError):
            inspect_dataset_rows([])
        with self.assertRaises(ValueError):
            inspect_dataset_rows([{"x": 1}, "bad"])

    def test_incomplete_mapping_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            normalize_dataset_rows([{"x": 1}], {"value": "x"})

    def test_absent_mapped_column_is_rejected(self):
        mapping = {
            "period_start": "start", "period_end": "end", "indicator": "metric",
            "value": "amount", "geography_type": "level", "geography": "area",
            "unit": "unit", "source_url": "source",
        }
        with self.assertRaisesRegex(ValueError, "absent"):
            normalize_dataset_rows([{"start": "2026-01-01"}], mapping)


if __name__ == "__main__":
    unittest.main()
