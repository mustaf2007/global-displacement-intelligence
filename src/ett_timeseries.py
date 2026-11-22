"""Normalized, auditable observations for the Somalia IOM DTM ETT series.

The reusable builder creates the verified Week 19 seed snapshot. The committed
registry also contains the separately transcribed Week 20 report snapshot; it is
not a complete weekly time series and does not fabricate missing periods.
"""
from datetime import date

from src.somalia_ett import get_week19_snapshot


def _period_dates(period):
    """Return explicit ISO dates for the known Week 19 reporting window."""
    if period == "31 October–4 November 2026":
        return date(2026, 10, 31), date(2026, 11, 4)
    raise ValueError("Reporting period requires an explicitly verified date mapping.")


def build_ett_observations(snapshot=None):
    """Return long-form observations with source, period, measure and geography."""
    data = snapshot if snapshot is not None else get_week19_snapshot()
    start_date, end_date = _period_dates(data["period"])
    common = {
        "source": data["source"],
        "source_url": data["source_url"],
        "period_label": data["period"],
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "coverage": "partial",
        "population_group": "IDP",
        "unit": "people",
    }
    rows = [
        {
            **common,
            "indicator": "new_arrivals",
            "measure_type": "flow",
            "geography_type": "national",
            "geography": "Somalia",
            "value": data["weekly_arrivals"],
            "cumulative_start": None,
        },
        {
            **common,
            "indicator": "cumulative_arrivals_since_start",
            "measure_type": "cumulative_flow",
            "geography_type": "national",
            "geography": "Somalia",
            "value": data["cumulative_arrivals"],
            "cumulative_start": data["cumulative_start"],
        },
    ]
    for dimension, items in (("origin_region", data["origins"]), ("destination_region", data["destinations"])):
        for item in items:
            rows.append({
                **common,
                "indicator": "new_arrivals",
                "measure_type": "flow",
                "geography_type": dimension,
                "geography": item["region"],
                "value": item["arrivals"],
                "cumulative_start": None,
            })
    for item in data["causes"]:
        rows.append({
            **common,
            "indicator": "reported_reason_share",
            "measure_type": "percentage",
            "geography_type": "national",
            "geography": "Somalia",
            "value": item["share_pct"],
            "cumulative_start": None,
            "category": item["reason"],
            "unit": "percent",
        })
    return rows


def validate_ett_observations(rows):
    """Validate normalized rows without imputing, aggregating or reconciling unlike measures."""
    required = {
        "source", "source_url", "period_label", "period_start", "period_end",
        "coverage", "population_group", "unit", "indicator", "measure_type",
        "geography_type", "geography", "value",
    }
    keys = [
        "source", "period_start", "period_end", "indicator",
        "measure_type", "geography_type", "geography", "category",
    ]
    seen = set()
    duplicate_keys = []
    missing_fields = []
    invalid_values = []
    invalid_periods = []
    for index, row in enumerate(rows):
        missing = sorted(required - set(row))
        if missing:
            missing_fields.append({"row": index, "fields": missing})
        try:
            if not isinstance(row.get("value"), (int, float)) or isinstance(row.get("value"), bool) or row["value"] < 0:
                invalid_values.append(index)
        except TypeError:
            invalid_values.append(index)
        try:
            if date.fromisoformat(row["period_start"]) > date.fromisoformat(row["period_end"]):
                invalid_periods.append(index)
        except (KeyError, TypeError, ValueError):
            invalid_periods.append(index)
        key = tuple(row.get(field) for field in keys)
        if key in seen:
            duplicate_keys.append(index)
        seen.add(key)
    checks = {
        "required_fields_present": not missing_fields,
        "values_non_negative_numeric": not invalid_values,
        "period_dates_valid": not invalid_periods,
        "observation_keys_unique": not duplicate_keys,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "row_count": len(rows),
        "missing_fields": missing_fields,
        "invalid_values": invalid_values,
        "invalid_periods": invalid_periods,
        "duplicate_keys": duplicate_keys,
    }
