"""Week 19 ETT reported needs and response, transcribed from IOM report page 2.

Percentages refer to settlements reporting each need/response, not shares of people.
'Not reported' and '<1%' remain categorical source values, not zeroes.
"""
SOURCE_URL = "https://dtm.iom.int/dtm_download_track/107441?amp%3Bid=70226&amp%3Btype=node&file=1"
PERIOD = "31 October–4 November 2026"

NEW_ARRIVAL_NEEDS = [
    {"sector": "General Food Distribution", "need_pct": 93, "response_pct": 2},
    {"sector": "Non-food items", "need_pct": 86, "response_pct": 7},
    {"sector": "Shelter Materials", "need_pct": 84, "response_pct": 2},
    {"sector": "Health Services", "need_pct": 71, "response_pct": 4},
    {"sector": "Nutrition Services", "need_pct": 70, "response_pct": 1},
    {"sector": "Sanitation Services", "need_pct": 66, "response_pct": 2},
    {"sector": "Water Services", "need_pct": 64, "response_pct": 1},
    {"sector": "Hygiene Services", "need_pct": 57, "response_pct": 1},
    {"sector": "General Protection Services", "need_pct": 32, "response_pct": 1},
    {"sector": "GBV Services", "need_pct": 24, "response_pct": "<1%"},
    {"sector": "Child Protection Services", "need_pct": 24, "response_pct": "Not reported"},
    {"sector": "CCCM Complaints and Feedback Mechanism", "need_pct": 22, "response_pct": "Not reported"},
    {"sector": "Temporary Learning Classes", "need_pct": 20, "response_pct": "Not reported"},
    {"sector": "CCCM Site Improvement", "need_pct": 18, "response_pct": "Not reported"},
    {"sector": "CCCM Site Decongestion", "need_pct": 11, "response_pct": "Not reported"},
    {"sector": "CCCM Plot Allocation", "need_pct": 7, "response_pct": "Not reported"},
]

MAIN_IDP_NEEDS = [
    {"need": "Food", "share_pct": 62},
    {"need": "Drinking Water", "share_pct": 11},
    {"need": "Shelter", "share_pct": 10},
    {"need": "Cash", "share_pct": 8},
    {"need": "Livelihoods", "share_pct": 7},
]


def validate_week19_needs():
    """Validate transcription structure and numeric bounds without imputing text categories."""
    sectors = [row["sector"] for row in NEW_ARRIVAL_NEEDS]
    numeric_valid = all(
        isinstance(row["need_pct"], int) and 0 <= row["need_pct"] <= 100
        and (isinstance(row["response_pct"], int) and 0 <= row["response_pct"] <= 100
             or row["response_pct"] in {"<1%", "Not reported"})
        for row in NEW_ARRIVAL_NEEDS
    )
    settlement_valid = all(
        isinstance(row["share_pct"], int) and 0 <= row["share_pct"] <= 100
        for row in MAIN_IDP_NEEDS
    )
    return {
        "unique_sectors": len(sectors) == len(set(sectors)),
        "new_arrival_values_valid": numeric_valid,
        "settlement_need_values_valid": settlement_valid,
        "settlement_need_shares_sum_98": sum(row["share_pct"] for row in MAIN_IDP_NEEDS) == 98,
        "source_attached": SOURCE_URL.startswith("https://"),
    }
