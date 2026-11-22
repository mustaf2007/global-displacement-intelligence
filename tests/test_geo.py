import unittest
from src.geo import ALIASES, country_iso3

class CountryISO3Tests(unittest.TestCase):
    def test_explicit_alias_codes_are_unique(self):
        codes = [country_iso3(label) for label in ALIASES]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(code and len(code) == 3 for code in codes))

    def test_recent_territory_aliases(self):
        expected = {
            "Cayman Islands (GBR)": "CYM",
            "Sint Maarten (K. of the Netherlands)": "SXM",
            "Turks and Caicos Islands (GBR)": "TCA",
            "British Virgin Islands (GBR)": "VGB",
        }
        for label, code in expected.items():
            with self.subTest(label=label):
                self.assertEqual(country_iso3(label), code)

    def test_standard_country_name(self):
        self.assertEqual(country_iso3("Germany"), "DEU")

    def test_unknown_and_missing_labels(self):
        self.assertIsNone(country_iso3("Unknown Example Territory 123"))
        self.assertIsNone(country_iso3(None))
        self.assertIsNone(country_iso3(float("nan")))
        self.assertIsNone(country_iso3("   "))

if __name__ == "__main__":
    unittest.main()
