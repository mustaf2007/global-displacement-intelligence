from __future__ import annotations

from typing import Any

import pandas as pd


KEY_COLUMNS = ["pop_type", "time_period", "ref_area_adm0", "area_ori_adm0"]


def audit_population_data(frame: pd.DataFrame) -> dict[str, Any]:
    """
    Return transparent data-quality diagnostics without changing or aggregating data.

    Missing geography codes are counted as coverage gaps. Duplicate dimension keys
    are flagged for investigation; they are not silently summed or discarded.
    """
    required = {"pop_type", "time_period", "obs_value"}
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        return {
            "status": "invalid_schema",
            "missing_columns": missing_columns,
            "row_count": int(len(frame)),
        }

    values = pd.to_numeric(frame["obs_value"], errors="coerce")
    invalid_values = values.isna()
    negative_values = values.lt(0).fillna(False)

    geo_columns = [column for column in ("ref_area_adm0", "area_ori_adm0") if column in frame.columns]
    missing_geo = pd.Series(False, index=frame.index)
    for column in geo_columns:
        normalized = frame[column].astype("string").str.strip()
        missing_geo |= normalized.isna() | normalized.eq("")

    available_keys = [column for column in KEY_COLUMNS if column in frame.columns]
    duplicate_key_rows = 0
    duplicate_key_groups = 0
    if len(available_keys) == len(KEY_COLUMNS):
        duplicated = frame.duplicated(subset=KEY_COLUMNS, keep=False)
        duplicate_key_rows = int(duplicated.sum())
        duplicate_key_groups = int(
            frame.loc[duplicated, KEY_COLUMNS].drop_duplicates().shape[0]
        )

    return {
        "status": "ok",
        "row_count": int(len(frame)),
        "invalid_population_values": int(invalid_values.sum()),
        "negative_population_values": int(negative_values.sum()),
        "missing_geography_codes": int(missing_geo.sum()),
        "duplicate_dimension_key_rows": duplicate_key_rows,
        "duplicate_dimension_key_groups": duplicate_key_groups,
        "geography_columns_checked": geo_columns,
    }


def reconciliation_by_period(frame: pd.DataFrame, geography: str) -> pd.DataFrame:
    """
    Compare explicit total rows with distinct country-level rows by period.

    The country sum is a diagnostic only, not an official global estimate.
    Periods with missing totals or duplicate country keys are left unreconciled.
    """
    if geography not in ("ref_area_adm0", "area_ori_adm0"):
        raise ValueError("geography must be ref_area_adm0 or area_ori_adm0")
    required = {"pop_type", "time_period", "obs_value", geography}
    opposite = "area_ori_adm0" if geography == "ref_area_adm0" else "ref_area_adm0"
    required.add(opposite)
    if not required.issubset(frame.columns):
        return pd.DataFrame(columns=[
            "pop_type", "time_period", "explicit_total", "country_sum",
            "difference", "difference_pct", "country_count", "duplicate_country_keys",
            "status",
        ])

    rows = []
    for (pop_type, period), group in frame.groupby(["pop_type", "time_period"], dropna=False):
        numeric = pd.to_numeric(group["obs_value"], errors="coerce")
        data = group.assign(_value=numeric)
        total_mask = (
            data[geography].astype("string").isin(["_T", "<NA>", "nan"])
            & data[opposite].astype("string").isin(["_T", "<NA>", "nan"])
        )
        totals = data.loc[total_mask, "_value"].dropna().drop_duplicates()
        explicit_total = float(totals.iloc[0]) if len(totals) == 1 else None

        country_mask = (
            data[geography].notna()
            & ~data[geography].astype("string").isin(["_T", "_X"])
            & data[opposite].astype("string").eq("_T")
        )
        countries = data.loc[country_mask, [geography, "_value"]].dropna(subset=["_value"])
        duplicate_codes = countries[geography].duplicated(keep=False)
        duplicate_count = int(countries.loc[duplicate_codes, geography].nunique())
        country_count = int(countries[geography].nunique())
        country_sum = None
        difference = None
        difference_pct = None
        if duplicate_count == 0 and country_count > 0:
            country_sum = float(countries["_value"].sum())
            if explicit_total is not None:
                difference = country_sum - explicit_total
                difference_pct = difference / explicit_total * 100 if explicit_total else None

        if explicit_total is None:
            status = "no_unique_explicit_total"
        elif duplicate_count:
            status = "duplicate_country_keys"
        elif country_count == 0:
            status = "no_country_records"
        else:
            status = "compared_not_certified"

        rows.append({
            "pop_type": pop_type,
            "time_period": period,
            "explicit_total": explicit_total,
            "country_sum": country_sum,
            "difference": difference,
            "difference_pct": difference_pct,
            "country_count": country_count,
            "duplicate_country_keys": duplicate_count,
            "status": status,
        })
    return pd.DataFrame(rows).sort_values(["pop_type", "time_period"]).reset_index(drop=True)
