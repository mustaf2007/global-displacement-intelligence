"""Coverage-aware comparisons between explicitly reported ETT periods."""
import pandas as pd


def compare_ett_periods(rows, indicator, measure_type, geography_type,
                        earlier_period, later_period):
    """Compare shared geographic/category units across two named periods.

    Returns a tuple: comparison frame and coverage metadata. Values are compared
    only where both periods contain exactly one valid observation for the same
    unit. No missing values are filled and no coverage adjustment is inferred.
    """
    columns = ["unit", "earlier_value", "later_value", "absolute_change",
               "percent_change", "direction"]
    frame = pd.DataFrame(rows)
    metadata = {
        "earlier_period": earlier_period,
        "later_period": later_period,
        "earlier_units": 0,
        "later_units": 0,
        "shared_units": 0,
        "added_units": [],
        "removed_units": [],
        "coverage_comparable": False,
        "earlier_coverage": None,
        "later_coverage": None,
        "status": "insufficient_data",
    }
    if frame.empty:
        return pd.DataFrame(columns=columns), metadata

    subset = frame[
        (frame["indicator"] == indicator)
        & (frame["measure_type"] == measure_type)
        & (frame["geography_type"] == geography_type)
        & (frame["period_label"].isin([earlier_period, later_period]))
    ].copy()
    dimension = (
        "category"
        if geography_type == "national" and indicator == "reported_reason_share"
        else "geography"
    )
    if dimension not in subset.columns:
        return pd.DataFrame(columns=columns), metadata

    if "source" in subset.columns and subset["source"].nunique() > 1:
        metadata["status"] = "mixed_sources"
        return pd.DataFrame(columns=columns), metadata

    subset["value"] = pd.to_numeric(subset["value"], errors="coerce")
    if subset["value"].isna().any() or (subset["value"] < 0).any():
        metadata["status"] = "invalid_values"
        return pd.DataFrame(columns=columns), metadata
    if subset.duplicated(["period_label", dimension]).any():
        metadata["status"] = "duplicate_observations"
        return pd.DataFrame(columns=columns), metadata

    earlier = subset[subset["period_label"] == earlier_period].set_index(dimension)["value"]
    later = subset[subset["period_label"] == later_period].set_index(dimension)["value"]
    earlier_units, later_units = set(earlier.index), set(later.index)

    earlier_coverage = (
        sorted(
            subset.loc[
                subset["period_label"] == earlier_period, "coverage"
            ].dropna().astype(str).unique()
        )
        if "coverage" in subset else []
    )
    later_coverage = (
        sorted(
            subset.loc[
                subset["period_label"] == later_period, "coverage"
            ].dropna().astype(str).unique()
        )
        if "coverage" in subset else []
    )
    coverage_matches = earlier_coverage == later_coverage

    shared = sorted(earlier_units & later_units)
    added = sorted(later_units - earlier_units)
    removed = sorted(earlier_units - later_units)
    metadata.update({
        "earlier_coverage": earlier_coverage,
        "later_coverage": later_coverage,
        "earlier_units": len(earlier_units),
        "later_units": len(later_units),
        "shared_units": len(shared),
        "added_units": added,
        "removed_units": removed,
        "coverage_comparable": bool(shared) and not added and not removed and coverage_matches,
        "status": (
            "comparable_coverage"
            if shared and not added and not removed and coverage_matches
            else "partial_overlap" if shared else "no_shared_units"
        ),
    })

    records = []
    for unit in shared:
        old, new = float(earlier.loc[unit]), float(later.loc[unit])
        change = new - old
        pct = (change / old * 100) if old != 0 else None
        records.append({
            "unit": unit,
            "earlier_value": old,
            "later_value": new,
            "absolute_change": change,
            "percent_change": pct,
            "direction": "increase" if change > 0 else "decrease" if change < 0 else "unchanged",
        })

    result = pd.DataFrame(records, columns=columns)
    if not result.empty:
        result = result.sort_values("absolute_change", ascending=False).reset_index(drop=True)
    return result, metadata
