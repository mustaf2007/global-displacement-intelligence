"""Reusable preparation helpers for an optional DTM IDP data explorer.

The explorer works with API-returned assessment snapshots. It filters source
observations without summing, imputing, deduplicating, or converting them into
weekly movement/arrival flows.
"""
from __future__ import annotations

import pandas as pd

from src.dtm_quality import profile_idp_data


_GEO_FIELDS = {
    0: "admin0Name",
    1: "admin1Name",
    2: "admin2Name",
}


def filter_idp_snapshot(
    frame: pd.DataFrame,
    admin_level: int,
    *,
    admin1: str | None = None,
    admin2: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> pd.DataFrame:
    """Return a copy filtered by available geography and reporting date.

    The function preserves the original rows and columns. It does not aggregate
    repeated assessments or treat absent observations as zero.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")
    if admin_level not in _GEO_FIELDS:
        raise ValueError("admin_level must be 0, 1, or 2.")

    required = [_GEO_FIELDS[admin_level], "reportingDate", "numPresentIdpInd"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Snapshot is missing required columns: {', '.join(missing)}")

    if from_date and to_date and pd.Timestamp(from_date) > pd.Timestamp(to_date):
        raise ValueError("from_date must be on or before to_date.")

    result = frame.copy()
    dates = pd.to_datetime(result["reportingDate"], errors="coerce")
    if from_date:
        result = result.loc[dates >= pd.Timestamp(from_date)].copy()
        dates = dates.loc[result.index]
    if to_date:
        result = result.loc[dates <= pd.Timestamp(to_date)].copy()

    if admin1:
        if "admin1Name" not in result.columns:
            raise ValueError("The snapshot does not contain admin1Name.")
        result = result.loc[result["admin1Name"].astype("string").eq(admin1)].copy()

    if admin2:
        if "admin2Name" not in result.columns:
            raise ValueError("The snapshot does not contain admin2Name.")
        result = result.loc[result["admin2Name"].astype("string").eq(admin2)].copy()

    return result.reset_index(drop=True)


def explorer_coverage_summary(frame: pd.DataFrame, admin_level: int) -> dict:
    """Describe returned data coverage without claiming full geographic coverage."""
    profile = profile_idp_data(frame, admin_level)
    date_values = (
        pd.to_datetime(frame["reportingDate"], errors="coerce").dropna()
        if "reportingDate" in frame.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    geo_column = _GEO_FIELDS[admin_level]
    geography = (
        sorted(frame[geo_column].dropna().astype(str).unique().tolist())
        if geo_column in frame.columns
        else []
    )

    return {
        "rows_returned": int(len(frame)),
        "geographic_units_returned": len(geography),
        "geographic_units": geography,
        "earliest_reporting_date": (
            str(date_values.min().date()) if not date_values.empty else None
        ),
        "latest_reporting_date": (
            str(date_values.max().date()) if not date_values.empty else None
        ),
        "quality_status": profile["status"],
        "coverage_interpretation": (
            "Returned-record coverage only; this response does not establish "
            "complete national or subnational geographic coverage."
        ),
    }
