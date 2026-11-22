import unittest

from src.ett_needs import (
    MAIN_IDP_NEEDS,
    NEW_ARRIVAL_NEEDS,
    SOURCE_URL,
    needs_response_gap_rows,
    validate_week19_needs,
)


class ETTNeedsTests(unittest.TestCase):
    def test_week19_needs_transcription_is_valid(self):
        checks = validate_week19_needs()
        self.assertTrue(all(checks.values()))

    def test_all_sixteen_new_arrival_sectors_are_present(self):
        self.assertEqual(len(NEW_ARRIVAL_NEEDS), 16)
        self.assertEqual(len({row["sector"] for row in NEW_ARRIVAL_NEEDS}), 16)

    def test_not_reported_and_less_than_one_are_not_zero(self):
        responses = {row["sector"]: row["response_pct"] for row in NEW_ARRIVAL_NEEDS}
        self.assertEqual(responses["GBV Services"], "<1%")
        self.assertEqual(responses["Child Protection Services"], "Not reported")

    def test_settlement_needs_are_a_separate_distribution(self):
        self.assertEqual(sum(row["share_pct"] for row in MAIN_IDP_NEEDS), 98)
        self.assertNotEqual(len(MAIN_IDP_NEEDS), len(NEW_ARRIVAL_NEEDS))

    def test_gap_is_percentage_points_and_missing_response_stays_missing(self):
        rows = {row["sector"]: row for row in needs_response_gap_rows()}
        self.assertEqual(rows["General Food Distribution"]["need_response_gap_pp"], 91)
        self.assertEqual(rows["Non-food items"]["need_response_gap_pp"], 79)
        self.assertIsNone(rows["Child Protection Services"]["need_response_gap_pp"])
        self.assertIsNone(rows["GBV Services"]["need_response_gap_pp"])

    def test_source_is_direct_report_pdf(self):
        self.assertIn("/dtm_download_track/", SOURCE_URL)


if __name__ == "__main__":
    unittest.main()
