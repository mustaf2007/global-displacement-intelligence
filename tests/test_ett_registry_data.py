import json
import unittest
from pathlib import Path

from src.ett_timeseries import build_ett_observations, validate_ett_observations


class ETTRegistryDataTests(unittest.TestCase):
    def _load_registry(self):
        path = Path(__file__).resolve().parents[1] / "data" / "somalia_ett_observations.json"
        with path.open(encoding="utf-8") as registry_file:
            return json.load(registry_file)

    def test_committed_week19_registry_matches_verified_builder(self):
        registry = self._load_registry()
        week19 = [row for row in registry if row["period_start"] == "2026-10-31"]
        generated = build_ett_observations()
        self.assertEqual(week19, generated)
        validation = validate_ett_observations(week19)
        self.assertTrue(validation["passed"], validation)
        self.assertEqual(validation["row_count"], 23)

    def test_registry_contains_week19_and_week20_with_expected_dimensions(self):
        registry = self._load_registry()
        self.assertEqual(
            {row["period_start"] for row in registry},
            {"2026-10-31", "2026-11-07"},
        )
        self.assertEqual(
            {row["period_end"] for row in registry},
            {"2026-11-04", "2026-11-11"},
        )
        self.assertEqual(
            {row["geography_type"] for row in registry},
            {"national", "origin_region", "destination_region"},
        )
        self.assertEqual(
            len([row for row in registry if row["period_start"] == "2026-10-31"]),
            23,
        )
        self.assertEqual(
            len([row for row in registry if row["period_start"] == "2026-11-07"]),
            23,
        )


if __name__ == "__main__":
    unittest.main()
