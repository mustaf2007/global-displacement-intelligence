"""Schema-first inspection of the public IOM DTM ETT location-level dataset.

This module deliberately does not guess column meanings or aggregate records.
A reviewed field mapping is required before normalization.
"""


def inspect_dataset_rows(rows):
    """Profile raw records and report candidate fields without assigning semantics."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset must be a non-empty list of row dictionaries.")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Every dataset row must be a dictionary.")
    columns = sorted({key for row in rows for key in row})
    profile = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        non_null = [value for value in values if value not in (None, "")]
        profile[column] = {
            "non_null_count": len(non_null),
            "null_count": len(rows) - len(non_null),
            "distinct_non_null_count": len({str(value) for value in non_null}),
            "sample_values": list(dict.fromkeys(str(value) for value in non_null))[:5],
            "observed_types": sorted({type(value).__name__ for value in non_null}),
        }
    exact_duplicate_rows = len(rows) - len({tuple(sorted((k, str(v)) for k, v in row.items())) for row in rows})
    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "column_profile": profile,
        "exact_duplicate_row_count": exact_duplicate_rows,
        "normalization_status": "not_normalized_mapping_required",
        "warning": (
            "Column names and sample values are descriptive only. "
            "No indicator, date, unit, geography or aggregation meaning is inferred."
        ),
    }


def normalize_dataset_rows(rows, field_mapping):
    """Refuse normalization until a complete reviewed mapping is supplied.

    Mapping values must point to raw column names. Semantic interpretation remains
    the responsibility of a documented, source-reviewed mapping.
    """
    required = {
        "period_start", "period_end", "indicator", "value",
        "geography_type", "geography", "unit", "source_url",
    }
    if not isinstance(field_mapping, dict) or not required.issubset(field_mapping):
        missing = sorted(required - set(field_mapping or {}))
        raise ValueError(f"Reviewed field mapping is incomplete: {missing}")
    available = {key for row in rows for key in row}
    missing_columns = sorted(set(field_mapping.values()) - available)
    if missing_columns:
        raise ValueError(f"Mapped source columns are absent: {missing_columns}")
    raise NotImplementedError(
        "Mapping is present, but normalization requires a reviewed indicator, "
        "unit, period and aggregation specification before records can be emitted."
    )
