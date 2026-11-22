"""Validated, source-attributed IOM Somalia ETT Week 19 snapshot.

These values are a manually transcribed static snapshot, not a live API feed.
Keep weekly arrival flows separate from IDP population stocks and from UNHCR series.
"""
from copy import deepcopy

WEEK19 = {
    "source": "IOM DTM Somalia Emergency Trend Tracking, Week 19",
    "source_url": "https://dtm.iom.int/reports/somalia-emergency-trend-tracking-report-week-19-31-october-04-november-2026",
    "period": "31 October–4 November 2026",
    "cumulative_start": "14 June 2026",
    "weekly_arrivals": 10451,
    "cumulative_arrivals": 114553,
    "districts_assessed": 16,
    "districts": [
        "Afgooye", "Afmadow", "Baardheere", "Baidoa", "Balcad", "Belet Weyne",
        "Bulo Burto", "Dayniile", "Diinsoor", "Doolow", "Jalalaqsi", "Jowhar",
        "Kahda", "Kismaayo", "Luuq", "Qansax Dheere",
    ],
    "causes": [
        {"reason": "Conflict", "share_pct": 44},
        {"reason": "Floods", "share_pct": 31},
        {"reason": "Drought", "share_pct": 20},
        {"reason": "Evictions", "share_pct": 5},
    ],
    "origins": [
        {"region": "Bay", "arrivals": 3528},
        {"region": "Middle Shabelle", "arrivals": 1862},
        {"region": "Hiraan", "arrivals": 1105},
        {"region": "Gedo", "arrivals": 875},
        {"region": "Lower Shabelle", "arrivals": 789},
        {"region": "Bakool", "arrivals": 760},
        {"region": "Banadir", "arrivals": 472},
        {"region": "Lower Juba", "arrivals": 512},
        {"region": "Middle Juba", "arrivals": 375},
        {"region": "Ethiopia", "arrivals": 173},
    ],
    "destinations": [
        {"region": "Gedo", "arrivals": 2188},
        {"region": "Bay", "arrivals": 1985},
        {"region": "Banadir", "arrivals": 1929},
        {"region": "Middle Shabelle", "arrivals": 1883},
        {"region": "Hiraan", "arrivals": 1041},
        {"region": "Lower Juba", "arrivals": 769},
        {"region": "Lower Shabelle", "arrivals": 656},
    ],
    "notes": [
        "Monitoring coverage is partial and not nationwide.",
        "Origin and destination totals are separate marginal distributions, not linked routes.",
        "New arrivals are flow measures and are not the total IDP population.",
    ],
}


def get_week19_snapshot():
    """Return a defensive copy so callers cannot mutate the canonical snapshot."""
    return deepcopy(WEEK19)


def validate_week19_snapshot(snapshot=None):
    """Return transparent arithmetic/schema checks; never silently repair data."""
    data = snapshot if snapshot is not None else WEEK19
    checks = {
        "weekly_total_positive": isinstance(data.get("weekly_arrivals"), int) and data["weekly_arrivals"] > 0,
        "cumulative_not_below_weekly": (
            isinstance(data.get("cumulative_arrivals"), int)
            and isinstance(data.get("weekly_arrivals"), int)
            and data["cumulative_arrivals"] >= data["weekly_arrivals"]
        ),
        "district_count_matches": (
            len(data.get("districts", [])) == data.get("districts_assessed")
            and len(set(data.get("districts", []))) == len(data.get("districts", []))
        ),
        "origin_distribution_reconciles": sum(x["arrivals"] for x in data.get("origins", [])) == data.get("weekly_arrivals"),
        "destination_distribution_reconciles": sum(x["arrivals"] for x in data.get("destinations", [])) == data.get("weekly_arrivals"),
        "cause_shares_sum_100": sum(x["share_pct"] for x in data.get("causes", [])) == 100,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "origin_total": sum(x["arrivals"] for x in data.get("origins", [])),
        "destination_total": sum(x["arrivals"] for x in data.get("destinations", [])),
        "cause_share_total": sum(x["share_pct"] for x in data.get("causes", [])),
    }
