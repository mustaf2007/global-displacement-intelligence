import unittest

from scripts.check_unhcr_api import _population_type_codes


class UNHCRConstraintsTests(unittest.TestCase):
    def test_extracts_codes_from_list_response_shape(self):
        payload = {
            "data": [
                {
                    "dimension": "pop_type",
                    "values": [
                        {"code": "REF_UNHCR", "has_data": True},
                        {"code": "IDP_UNHCR", "has_data": True},
                        {"code": "EMPTY", "has_data": False},
                    ],
                }
            ]
        }
        self.assertEqual(
            _population_type_codes(payload),
            {"REF_UNHCR", "IDP_UNHCR"},
        )

    def test_extracts_codes_from_nested_dimensions_shape(self):
        payload = {
            "data": {
                "dimensions": [
                    {
                        "dimension": "pop_type",
                        "values": [{"code": "ASY", "has_data": True}],
                    }
                ]
            }
        }
        self.assertEqual(_population_type_codes(payload), {"ASY"})

    def test_rejects_missing_population_dimension(self):
        with self.assertRaisesRegex(ValueError, "pop_type"):
            _population_type_codes({"data": []})

    def test_rejects_empty_or_malformed_values(self):
        with self.assertRaisesRegex(ValueError, "no usable codes"):
            _population_type_codes({
                "data": [{
                    "dimension": "pop_type",
                    "values": [{"code": "IDP_UNHCR", "has_data": False}],
                }]
            })


if __name__ == "__main__":
    unittest.main()
