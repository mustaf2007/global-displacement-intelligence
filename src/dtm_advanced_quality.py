"""Second-stage quality and returned-coverage diagnostics for DTM IDP snapshots.

These diagnostics describe only the records returned by the API. They do not
certify source assessments or establish complete national coverage.
"""
from __future__ import annotations

import pandas as pd

_GEO = {
    0: ("admin0Name", "admin0Pcode", None, None),
    1: ("admin1Name", "admin1Pcode", "admin0Name", "admin0Pcode"),
    2: ("admin2Name", "admin2Pcode", "admin1Name", "admin1Pcode"),
}


def advanced_idp_quality_report(frame: pd.DataFrame, admin_level: int) -> dict:
    """Return non-destructive geography, time, missingness and provenance checks."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")
    if admin_level not in _GEO:
        raise ValueError("admin_level must be 0, 1, or 2.")

    name_col, code_col, parent_name_col, parent_code_col = _GEO[admin_level]
    dates = (
        pd.to_datetime(frame["reportingDate"], errors="coerce")
        if "reportingDate" in frame.columns
        else pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    )
    report = {
        "admin_level": admin_level,
        "rows_returned": int(len(frame)),
        "geography": {
            "name_field": name_col,
            "code_field": code_col,
            "code_field_available": code_col in frame.columns,
            "missing_names": int(frame[name_col].isna().sum()) if name_col in frame else None,
            "missing_codes": int(frame[code_col].isna().sum()) if code_col in frame else None,
            "unique_names": int(frame[name_col].nunique(dropna=True)) if name_col in frame else 0,
            "unique_codes": int(frame[code_col].nunique(dropna=True)) if code_col in frame else None,
            "codes_mapping_to_multiple_names": 0,
            "names_mapping_to_multiple_codes": 0,
        },
        "parent_geography": {
            "parent_name_field": parent_name_col,
            "parent_code_field": parent_code_col,
            "available": bool(parent_name_col and parent_code_col and parent_name_col in frame and parent_code_col in frame),
            "district_or_unit_codes_with_multiple_parents": 0,
            "parent_codes_mapping_to_multiple_names": 0,
        },
        "temporal": {
            "valid_reporting_dates": int(dates.notna().sum()),
            "invalid_or_missing_reporting_dates": int(dates.isna().sum()),
            "earliest_reporting_date": str(dates.min().date()) if dates.notna().any() else None,
            "latest_reporting_date": str(dates.max().date()) if dates.notna().any() else None,
            "unique_reporting_dates": int(dates.dropna().nunique()),
        },
        "demographic_missingness": [],
        "provenance_breakdown": {},
        "unit_reporting_coverage": [],
        "interpretation": (
            "All counts describe records returned for this API query. They do not "
            "establish complete national or subnational coverage, source accuracy, "
            "or representativeness."
        ),
    }

    if name_col in frame and code_col in frame:
        valid = frame[[name_col, code_col]].dropna().astype("string").drop_duplicates()
        report["geography"]["codes_mapping_to_multiple_names"] = int(
            (valid.groupby(code_col)[name_col].nunique() > 1).sum()
        )
        report["geography"]["names_mapping_to_multiple_codes"] = int(
            (valid.groupby(name_col)[code_col].nunique() > 1).sum()
        )

    if report["parent_geography"]["available"] and name_col in frame and code_col in frame:
        mapping = frame[[name_col, code_col, parent_name_col, parent_code_col]].dropna().astype("string").drop_duplicates()
        report["parent_geography"]["district_or_unit_codes_with_multiple_parents"] = int(
            (mapping.groupby(code_col)[parent_code_col].nunique() > 1).sum()
        )
        parent_pairs = mapping[[parent_name_col, parent_code_col]].drop_duplicates()
        report["parent_geography"]["parent_codes_mapping_to_multiple_names"] = int(
            (parent_pairs.groupby(parent_code_col)[parent_name_col].nunique() > 1).sum()
        )

    for column in ("numberMales", "numberFemales", "idpOriginAdmin1Name", "idpOriginAdmin1Pcode"):
        if column in frame:
            missing = int(frame[column].isna().sum())
            report["demographic_missingness"].append({
                "field": column,
                "missing": missing,
                "missing_percent": round(missing / len(frame) * 100, 1) if len(frame) else 0.0,
                "non_missing": int(len(frame) - missing),
            })

    for column in ("operation", "assessmentType", "displacementReason"):
        if column in frame:
            counts = frame[column].fillna("[Missing]").astype(str).value_counts(dropna=False)
            report["provenance_breakdown"][column] = [
                {"category": str(key), "records": int(value)}
                for key, value in counts.items()
            ]

    if name_col in frame:
        temp = pd.DataFrame({
            "geographic_unit": frame[name_col].astype("string"),
            "reporting_date": dates,
        }).dropna(subset=["geographic_unit"])
        if code_col in frame:
            temp["geographic_code"] = frame[code_col].astype("string")
        else:
            temp["geographic_code"] = pd.NA
        coverage = (
            temp.groupby("geographic_unit", dropna=True)
            .agg(
                records_returned=("reporting_date", "size"),
                unique_reporting_dates=("reporting_date", "nunique"),
                first_reporting_date=("reporting_date", "min"),
                latest_reporting_date=("reporting_date", "max"),
                geographic_code=("geographic_code", "first"),
            )
            .reset_index()
            .sort_values(["latest_reporting_date", "geographic_unit"], ascending=[False, True], na_position="last")
        )
        for row in coverage.to_dict("records"):
            for key in ("first_reporting_date", "latest_reporting_date"):
                value = row[key]
                row[key] = str(value.date()) if pd.notna(value) else None
            row["records_returned"] = int(row["records_returned"])
            row["unique_reporting_dates"] = int(row["unique_reporting_dates"])
            row["geographic_code"] = None if pd.isna(row["geographic_code"]) else str(row["geographic_code"])
            report["unit_reporting_coverage"].append(row)

    return report
