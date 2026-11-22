"""Secure, opt-in connector for the IOM DTM API v3.

This module retrieves aggregated IDP assessment snapshots. It is intentionally
separate from Somalia Emergency Trend Tracking (ETT), which measures weekly
arrival flows at site/location level.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd


class DTMConnectorError(RuntimeError):
    """Raised when the DTM connector cannot be configured or queried."""


_METHODS = {
    0: "get_idp_admin0_data",
    1: "get_idp_admin1_data",
    2: "get_idp_admin2_data",
}


def build_dtm_client(subscription_key: str | None = None) -> Any:
    """Create the official DTM API v3 client using a secret environment value."""
    key = subscription_key or os.getenv("DTMAPI_SUBSCRIPTION_KEY")
    if not key:
        raise DTMConnectorError(
            "DTM API access is not configured. Set DTMAPI_SUBSCRIPTION_KEY "
            "in the deployment secrets or environment."
        )

    try:
        from dtmapi import DTMApi
    except ImportError as exc:
        raise DTMConnectorError(
            "The optional dtmapi package is not installed. Install project "
            "requirements before enabling the DTM API connector."
        ) from exc

    try:
        return DTMApi(
            subscription_key=key,
            api_version="v3",
            timeout=30,
            max_retries=3,
        )
    except Exception as exc:
        # Constructor errors can include request/configuration details. Keep the
        # surfaced message generic so secrets are never echoed into the UI/logs.
        raise DTMConnectorError(
            "Could not initialize the DTM API v3 client. Check the package "
            "installation and subscription configuration."
        ) from exc


def fetch_idp_data(
    country_name: str,
    admin_level: int = 1,
    *,
    from_reporting_date: str | None = None,
    to_reporting_date: str | None = None,
    client: Any | None = None,
) -> pd.DataFrame:
    """Fetch an IDP assessment snapshot at Admin 0, 1, or 2.

    Date filters use the API's YYYY-MM-DD parameters. The returned data are
    population-stock assessment observations, not weekly movement/arrival
    counts. No totals are calculated or imputed by this connector.
    """
    country = country_name.strip() if isinstance(country_name, str) else ""
    if not country:
        raise ValueError("country_name must be a non-empty country name.")
    if admin_level not in _METHODS:
        raise ValueError("admin_level must be 0, 1, or 2.")

    def _validate_date(value: str | None, label: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{label} must use a valid YYYY-MM-DD date.")
        try:
            parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must use a valid YYYY-MM-DD date.") from exc
        normalized = parsed.strftime("%Y-%m-%d")
        if normalized != value:
            raise ValueError(f"{label} must use a valid YYYY-MM-DD date.")
        return normalized

    start_date = _validate_date(from_reporting_date, "from_reporting_date")
    end_date = _validate_date(to_reporting_date, "to_reporting_date")
    if start_date and end_date and pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise ValueError("from_reporting_date must be on or before to_reporting_date.")

    params: dict[str, str] = {"CountryName": country}
    if start_date:
        params["FromReportingDate"] = start_date
    if end_date:
        params["ToReportingDate"] = end_date

    api = client if client is not None else build_dtm_client()
    method_name = _METHODS[admin_level]
    method = getattr(api, method_name, None)
    if not callable(method):
        raise DTMConnectorError(
            f"The installed DTM client does not provide {method_name}."
        )

    try:
        result = method(**params)
    except Exception as exc:
        # Do not include credentials or request headers in surfaced errors.
        raise DTMConnectorError(
            f"DTM API v3 request failed for {country} at Admin {admin_level}: "
            f"{type(exc).__name__}. Check API access, subscription status and query parameters."
        ) from exc

    if not isinstance(result, pd.DataFrame):
        raise DTMConnectorError(
            "DTM API returned an unexpected response; a pandas DataFrame was expected."
        )
    return result.copy()
