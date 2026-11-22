"""Period-aware summaries for verified Somalia ETT observations."""
import pandas as pd


def prepare_ett_trend(rows, indicator, measure_type, geography_type, geography=None, category=None):
    """Return one comparable observation per reporting period, or an empty frame.

    The function never aggregates regional marginals or mixes weekly and cumulative
    measures. Duplicate period keys are withheld rather than silently resolved.
    """
    columns = ["period_start", "period_end", "period_label", "value", "unit", "source_url"]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=columns)
    subset = frame[
        (frame["indicator"] == indicator)
        & (frame["measure_type"] == measure_type)
        & (frame["geography_type"] == geography_type)
    ].copy()
    if geography is not None:
        subset = subset[subset["geography"] == geography]
    if category is not None:
        subset = subset[subset["category"] == category]
    if subset.empty:
        return pd.DataFrame(columns=columns)
    keys = ["period_start", "period_end"]
    if subset.duplicated(keys, keep=False).any():
        return pd.DataFrame(columns=columns)
    subset["value"] = pd.to_numeric(subset["value"], errors="coerce")
    if subset["value"].isna().any() or (subset["value"] < 0).any():
        return pd.DataFrame(columns=columns)
    subset = subset.sort_values("period_start")
    return subset[columns].reset_index(drop=True)


def trend_readiness(trend_frame):
    """Describe whether a period comparison is supported by distinct observations."""
    count = 0 if trend_frame.empty else int(trend_frame["period_start"].nunique())
    return {
        "period_count": count,
        "ready": count >= 2,
        "status": "ready" if count >= 2 else "insufficient_periods",
    }
