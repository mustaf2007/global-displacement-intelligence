import unittest

from src.dtm_streamlit import validate_reporting_date_filters


class TestDTMReportingDateFilters(unittest.TestCase):
    def test_empty_filters_are_none(self):
        self.assertEqual(validate_reporting_date_filters('', '  '), (None, None))

    def test_valid_dates_are_normalized(self):
        self.assertEqual(
            validate_reporting_date_filters(' 2026-01-02 ', '2026-11-22'),
            ('2026-01-02', '2026-11-22'),
        )

    def test_invalid_calendar_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'valid YYYY-MM-DD'):
            validate_reporting_date_filters('2026-02-30', '')

    def test_non_iso_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'valid YYYY-MM-DD'):
            validate_reporting_date_filters('01/02/2026', '')

    def test_reversed_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'on or before'):
            validate_reporting_date_filters('2026-11-23', '2026-11-22')

    def test_same_day_range_is_valid(self):
        self.assertEqual(
            validate_reporting_date_filters('2026-11-22', '2026-11-22'),
            ('2026-11-22', '2026-11-22'),
        )


if __name__ == '__main__':
    unittest.main()
