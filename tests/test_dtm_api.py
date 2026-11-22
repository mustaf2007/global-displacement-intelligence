import unittest

import pandas as pd

from src.dtm_api import DTMConnectorError, fetch_idp_data


class FakeDTMClient:
    def __init__(self):
        self.calls = []

    def get_idp_admin0_data(self, **kwargs):
        self.calls.append(("admin0", kwargs))
        return pd.DataFrame({"admin0Name": ["Somalia"], "numberOfIndividuals": [100]})

    def get_idp_admin1_data(self, **kwargs):
        self.calls.append(("admin1", kwargs))
        return pd.DataFrame({"admin1Name": ["Banaadir"], "numberOfIndividuals": [100]})

    def get_idp_admin2_data(self, **kwargs):
        self.calls.append(("admin2", kwargs))
        return pd.DataFrame({"admin2Name": ["District"], "numberOfIndividuals": [100]})


class DTMConnectorTests(unittest.TestCase):
    def test_client_initialization_error_does_not_expose_secret(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        from src.dtm_api import build_dtm_client

        fake_module = SimpleNamespace(
            DTMApi=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("secret-value"))
        )
        with patch.dict(sys.modules, {"dtmapi": fake_module}):
            with self.assertRaises(DTMConnectorError) as raised:
                build_dtm_client(subscription_key="secret-value")
        self.assertNotIn("secret-value", str(raised.exception))

    def test_admin1_query_passes_country_and_date_filters(self):
        client = FakeDTMClient()
        result = fetch_idp_data(
            "Somalia",
            admin_level=1,
            from_reporting_date="2025-01-01",
            to_reporting_date="2025-12-31",
            client=client,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(
            client.calls,
            [("admin1", {
                "CountryName": "Somalia",
                "FromReportingDate": "2025-01-01",
                "ToReportingDate": "2025-12-31",
            })],
        )

    def test_admin_levels_zero_and_two_are_supported(self):
        for level, expected in ((0, "admin0"), (2, "admin2")):
            client = FakeDTMClient()
            fetch_idp_data("Somalia", admin_level=level, client=client)
            self.assertEqual(client.calls[0][0], expected)

    def test_invalid_country_and_admin_level_are_rejected(self):
        with self.assertRaises(ValueError):
            fetch_idp_data(" ", client=FakeDTMClient())
        with self.assertRaises(ValueError):
            fetch_idp_data("Somalia", admin_level=3, client=FakeDTMClient())

    def test_invalid_or_reversed_reporting_dates_are_rejected_before_request(self):
        for kwargs in (
            {"from_reporting_date": "2026-02-30"},
            {"to_reporting_date": "22-11-2026"},
            {"from_reporting_date": "2026-11-23", "to_reporting_date": "2026-11-22"},
        ):
            client = FakeDTMClient()
            with self.assertRaises(ValueError):
                fetch_idp_data("Somalia", client=client, **kwargs)
            self.assertEqual(client.calls, [])

    def test_non_dataframe_response_is_rejected(self):
        class BadClient:
            def get_idp_admin1_data(self, **kwargs):
                return {"not": "a dataframe"}

        with self.assertRaises(DTMConnectorError):
            fetch_idp_data("Somalia", client=BadClient())


if __name__ == "__main__":
    unittest.main()
