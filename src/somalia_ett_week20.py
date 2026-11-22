"""Validated, source-attributed IOM Somalia ETT Week 20 snapshot.

Manually transcribed from the three-page IOM report supplied for this project.
This is a report-derived static snapshot, not a live API feed or raw location-level
ETT dataset. Keep weekly arrival flows separate from IDP population stocks.
"""
from copy import deepcopy

WEEK20 = {
    "source": "IOM DTM Somalia Emergency Trend Tracking, Week 20",
    "source_url": "https://humara.org/report/2552b18b-af4f-490f-805c-a005a3b012ba",
    "source_document": "IOM_DTM_Somalia_ETT_2026_week_20.pdf (three-page IOM report copy supplied for project extraction)",
    "period": "7–11 November 2026",
    "period_start": "2026-11-07",
    "period_end": "2026-11-11",
    "cumulative_start": "14 June 2026",
    "weekly_arrivals": 10013,
    "cumulative_arrivals": 124566,
    "districts_assessed": 16,
    "settlements_assessed": 811,
    "urban_settlement_share_pct": 86,
    "rural_settlement_share_pct": 14,
    "idp_sites": 641,
    "districts": ["Afgooye","Afmadow","Baardheere","Baidoa","Balcad","Belet Weyne","Bulo Burto","Dayniile","Diinsoor","Doolow","Jalalaqsi","Jowhar","Kahda","Kismaayo","Luuq","Qansax Dheere"],
    "causes": [{"reason":"Conflict","share_pct":41},{"reason":"Floods","share_pct":34},{"reason":"Drought","share_pct":18},{"reason":"Evictions","share_pct":7}],
    "origins": [{"region":"Bay","arrivals":3620},{"region":"Banadir","arrivals":674},{"region":"Lower Shabelle","arrivals":486},{"region":"Bakool","arrivals":300},{"region":"Gedo","arrivals":869},{"region":"Middle Juba","arrivals":321},{"region":"Lower Juba","arrivals":453},{"region":"Ethiopia","arrivals":164},{"region":"Hiraan","arrivals":1179},{"region":"Middle Shabelle","arrivals":1947}],
    "destinations": [{"region":"Bay","arrivals":2261},{"region":"Lower Shabelle","arrivals":511},{"region":"Banadir","arrivals":2096},{"region":"Gedo","arrivals":1481},{"region":"Lower Juba","arrivals":687},{"region":"Hiraan","arrivals":1149},{"region":"Middle Shabelle","arrivals":1828}],
    "main_idp_needs": [
        {"need": "Food", "share_pct": 59},
        {"need": "Drinking Water", "share_pct": 11},
        {"need": "Shelter", "share_pct": 10},
        {"need": "Cash", "share_pct": 8},
        {"need": "Livelihoods", "share_pct": 7},
    ],
    "notes": [
        "Monitoring coverage is partial and focuses on main urban centres and surrounding villages in assessed districts.",
        "Origin and destination totals are separate marginal distributions, not linked routes.",
        "New arrivals are flow measures and are not the total IDP population.",
        "Other hazards were reported as less than 1%; this categorical value is not converted to zero.",
        "Main IDP needs are reported as leading needs and do not form an exhaustive 100% distribution.",
        "Findings are estimates from key informant interviews; detailed origins are not collected for every arrival.",
    ],
}

def get_week20_snapshot():
    """Return a defensive copy so callers cannot mutate the canonical snapshot."""
    return deepcopy(WEEK20)

def validate_week20_snapshot(snapshot=None):
    """Return transparent arithmetic/schema checks; never silently repair data."""
    data = snapshot if snapshot is not None else WEEK20
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
        "settlement_shares_sum_100": (
            data.get("urban_settlement_share_pct", 0) + data.get("rural_settlement_share_pct", 0) == 100
        ),
        "settlement_counts_positive": (
            isinstance(data.get("settlements_assessed"), int) and data["settlements_assessed"] > 0
            and isinstance(data.get("idp_sites"), int) and 0 < data["idp_sites"] <= data["settlements_assessed"]
        ),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "origin_total": sum(x["arrivals"] for x in data.get("origins", [])),
        "destination_total": sum(x["arrivals"] for x in data.get("destinations", [])),
        "cause_share_total": sum(x["share_pct"] for x in data.get("causes", [])),
    }
