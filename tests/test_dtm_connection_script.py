import contextlib
import io
import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

from scripts import check_dtm_connection


class DTMConnectionScriptTests(unittest.TestCase):
    def test_missing_key_exits_without_request(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["check_dtm_connection.py"]):
                with patch.object(check_dtm_connection, "fetch_idp_data") as fetch:
                    with contextlib.redirect_stdout(output):
                        code = check_dtm_connection.main()

        self.assertEqual(code, 2)
        self.assertIn("No API request was made", output.getvalue())
        fetch.assert_not_called()

    def test_empty_response_does_not_claim_geographic_coverage(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"DTMAPI_SUBSCRIPTION_KEY": "test-key"}):
            with patch.object(sys, "argv", ["check_dtm_connection.py"]):
                with patch.object(
                    check_dtm_connection, "fetch_idp_data", return_value=pd.DataFrame()
                ) as fetch:
                    with contextlib.redirect_stdout(output):
                        code = check_dtm_connection.main()

        self.assertEqual(code, 3)
        self.assertIn("coverage is not established", output.getvalue())
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
