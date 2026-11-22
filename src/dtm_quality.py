"""Quality checks for aggregated IOM DTM IDP API snapshots.

These checks report issues without changing, deduplicating, aggregating, or
imputing observations.
"""
from __future__ import annotations

import pandas as pd


_GEO_FIELDS = {
    0: "admin0Name",
    1: "admin1Name",
    2: "admin2Name",
}


def profile_idp_data(frame: pd.DataFrame, admin_level: int) -> dict:
    """Return transparent schema and value-quality diagnostics for DTM IDP data."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")
    if admin_level not in _GEO_FIELDS:
        raise ValueError("admin_level must be 0, 1, or 2.")

    required = [_GEO_FIELDS[admin_level], "reportingDate", "numPresentIdpInd"]
    missing_columns = [column for column in required if column not in frame.columns]

    result = {
        "admin_level": admin_level,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "missing_required_columns": missing_columns,
        "null_counts": {
            column: int(frame[column].isna().sum())
            for column in required
            if column in frame.columns
        },
        "invalid_reporting_dates": None,
        "invalid_population_values": None,
        "negative_population_values": None,
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "status": "incomplete_schema" if missing_columns else "review_required",
    }

    if "reportingDate" in frame.columns:
        dates = pd.to_datetime(frame["reportingDate"], errors="coerce")
        result["invalid_reporting_dates"] = int(dates.isna().sum())

    if "numPresentIdpInd" in frame.columns:
        counts = pd.to_numeric(frame["numPresentIdpInd"], errors="coerce")
        result["invalid_population_values"] = int(counts.isna().sum())
        result["negative_population_values"] = int((counts.dropna() < 0).sum())

    if not missing_columns:
        has_issues = (
            result["null_counts"].get(_GEO_FIELDS[admin_level], 0) > 0
            or result["null_counts"].get("reportingDate", 0) > 0
            or result["null_counts"].get("numPresentIdpInd", 0) > 0
            or result["invalid_reporting_dates"] > 0
            or result["invalid_population_values"] > 0
            or result["negative_population_values"] > 0
            or result["exact_duplicate_rows"] > 0
        )
        result["status"] = "review_required" if has_issues else "passed_basic_checks"

    return result
