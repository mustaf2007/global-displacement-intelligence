import json
import unittest
from pathlib import Path


class ETTSourceRegisterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "data" / "somalia_ett_source_register.json"
        with path.open(encoding="utf-8") as handle:
            cls.records = json.load(handle)

    def test_register_has_unique_ids_and_urls(self):
        ids = [row["record_id"] for row in self.records]
        urls = [row["source_url"] for row in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(urls), len(set(urls)))

    def test_required_metadata_and_allowed_statuses(self):
        statuses = {
            "metadata_verified_values_not_extracted",
            "verified_observations_in_registry",
            "metadata_verified_aggregate_values_not_in_weekly_registry",
            "source_catalogued_dataset_file_not_imported",
        }
        for row in self.records:
            for field in ("record_id", "title", "source_url", "source_type",
                          "period_start", "period_end", "extraction_status", "notes"):
                self.assertTrue(row.get(field), f"Missing {field}: {row}")
            self.assertIn(row["extraction_status"], statuses)
            self.assertLessEqual(row["period_start"], row["period_end"])

    def test_only_week19_is_marked_as_weekly_observations_loaded(self):
        loaded = [
            row["record_id"] for row in self.records
            if row["extraction_status"] == "verified_observations_in_registry"
        ]
        self.assertEqual(loaded, ["ett_2026_week19"])

    def test_quarterly_reports_are_not_weekly_records(self):
        for row in self.records:
            if row["source_type"] == "quarterly_overview":
                self.assertIn("aggregate", row["extraction_status"])
                self.assertIn("do not merge", row["notes"].lower())


if __name__ == "__main__":
    unittest.main()
