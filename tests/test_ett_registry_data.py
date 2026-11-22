import json
import unittest
from pathlib import Path

from src.ett_timeseries import build_ett_observations, validate_ett_observations


class ETTRegistryDataTests(unittest.TestCase):
    def test_committed_registry_matches_verified_week19_builder(self):
        path = Path(__file__).resolve().parents[1] / "data" / "somalia_ett_observations.json"
        with path.open(encoding="utf-8") as registry_file:
            registry = json.load(registry_file)
        generated = build_ett_observations()
        self.assertEqual(registry, generated)
        validation = validate_ett_observations(registry)
        self.assertTrue(validation["passed"], validation)
        self.assertEqual(validation["row_count"], 23)

    def test_registry_has_one_reporting_period_and_expected_dimensions(self):
        path = Path(__file__).resolve().parents[1] / "data" / "somalia_ett_observations.json"
        with path.open(encoding="utf-8") as registry_file:
            registry = json.load(registry_file)
        self.assertEqual({row["period_start"] for row in registry}, {"2026-10-31"})
        self.assertEqual({row["period_end"] for row in registry}, {"2026-11-04"})
        self.assertEqual(
            {row["geography_type"] for row in registry},
            {"national", "origin_region", "destination_region"},
        )


if __name__ == "__main__":
    unittest.main()
