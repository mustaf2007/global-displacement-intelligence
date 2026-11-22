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
