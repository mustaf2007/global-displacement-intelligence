"""Geographic label normalization for UNHCR country-level maps."""
import re
import unicodedata
import pandas as pd
import pycountry

ALIASES = {
    "Türkiye": "TUR", "Islamic Republic of Iran": "IRN",
    "United States of America": "USA",
    "United Kingdom of Great Britain and Northern Ireland": "GBR",
    "Democratic Republic of the Congo": "COD", "Republic of the Congo": "COG",
    "Netherlands (Kingdom of the)": "NLD", "United Republic of Tanzania": "TZA",
    "Côte d'Ivoire": "CIV", "Republic of Moldova": "MDA",
    "Bolivarian Republic of Venezuela": "VEN",
    "Plurinational State of Bolivia": "BOL", "Russian Federation": "RUS",
    "Syrian Arab Republic": "SYR", "Republic of Korea": "KOR", "Viet Nam": "VNM",
    "Naoero": "NRU", "Hong Kong (China)": "HKG", "Hong Kong (CHN)": "HKG",
    "Serbia*": "SRB", "State of Palestine": "PSE", "Palestine": "PSE",
    "Kosovo": "XKX", "Cayman Islands (GBR)": "CYM",
    "Sint Maarten (K. of the Netherlands)": "SXM",
    "Turks and Caicos Islands (GBR)": "TCA",
    "British Virgin Islands (GBR)": "VGB",
}

def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.lower())

def country_iso3(country_name: object) -> str | None:
    """Resolve a UNHCR label to ISO-3; return None when unrecognized."""
    if country_name is None or pd.isna(country_name):
        return None
    name = str(country_name).strip()
    if not name:
        return None
    if name in ALIASES:
        return ALIASES[name]
    target = _normalize(name)
    for country in pycountry.countries:
        candidates = (getattr(country, "name", ""), getattr(country, "official_name", ""), getattr(country, "common_name", ""))
        if any(_normalize(candidate) == target for candidate in candidates if candidate):
            return country.alpha_3
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None
