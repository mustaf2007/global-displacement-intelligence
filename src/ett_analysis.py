"""Descriptive regional and driver analysis for verified Somalia ETT observations."""
import pandas as pd


def regional_distribution(rows, geography_type):
    """Return sorted regional counts and shares for one marginal dimension."""
    if geography_type not in {"origin_region", "destination_region"}:
        raise ValueError("geography_type must be origin_region or destination_region")
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["region", "arrivals", "share_pct", "rank"])
    subset = frame[
        (frame["indicator"] == "new_arrivals")
        & (frame["measure_type"] == "flow")
        & (frame["geography_type"] == geography_type)
    ].copy()
    if subset.empty:
        return pd.DataFrame(columns=["region", "arrivals", "share_pct", "rank"])
    if subset["geography"].duplicated().any():
        raise ValueError("Duplicate regional observations: distribution withheld.")
    subset["arrivals"] = pd.to_numeric(subset["value"], errors="coerce")
    if subset["arrivals"].isna().any() or (subset["arrivals"] < 0).any():
        raise ValueError("Invalid regional arrival values.")
    total = subset["arrivals"].sum()
    if total <= 0:
        raise ValueError("Regional distribution requires a positive total.")
    subset = subset.rename(columns={"geography": "region"})
    subset["share_pct"] = subset["arrivals"] / total * 100
    subset = subset.sort_values(["arrivals", "region"], ascending=[False, True])
    subset["rank"] = range(1, len(subset) + 1)
    return subset[["region", "arrivals", "share_pct", "rank"]].reset_index(drop=True)


def driver_distribution(rows):
    """Return reported reason shares; do not impute textual '<1%' categories."""
    frame = pd.DataFrame(rows)
    columns = ["reason", "share_pct", "rank"]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    subset = frame[
        (frame["indicator"] == "reported_reason_share")
        & (frame["measure_type"] == "percentage")
        & (frame["geography_type"] == "national")
    ].copy()
    if subset.empty:
        return pd.DataFrame(columns=columns)
    if subset["category"].duplicated().any():
        raise ValueError("Duplicate driver categories: distribution withheld.")
    subset["share_pct"] = pd.to_numeric(subset["value"], errors="coerce")
    if subset["share_pct"].isna().any() or ((subset["share_pct"] < 0) | (subset["share_pct"] > 100)).any():
        raise ValueError("Invalid reported reason percentage.")
    subset = subset.rename(columns={"category": "reason"}).sort_values(
        ["share_pct", "reason"], ascending=[False, True]
    )
    subset["rank"] = range(1, len(subset) + 1)
    return subset[columns].reset_index(drop=True)


def distribution_summary(distribution):
    """Summarize concentration within one reported marginal distribution only."""
    if distribution.empty:
        return {"total": 0, "top_region": None, "top_share_pct": None, "hhi": None}
    shares = distribution["share_pct"] / 100
    top = distribution.iloc[0]
    return {
        "total": int(distribution["arrivals"].sum()) if "arrivals" in distribution else None,
        "top_region": top["region"] if "region" in distribution else top["reason"],
        "top_share_pct": float(top["share_pct"]),
        "hhi": float((shares ** 2).sum()),
    }
