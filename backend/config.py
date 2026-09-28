import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MARKETPLACE_DATA_DIR = PROCESSED_DATA_DIR / "marketplace"
SAMPLE_AERIALS_DIR = DATA_DIR / "sample_aerials"

# Ensure directories exist
for d in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MARKETPLACE_DATA_DIR, SAMPLE_AERIALS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_STATE = "CHICAGO"

# Chicago area = Cook County (city + near neighborhoods). Collar counties removed.
CHICAGO_METRO_COUNTIES = ["Cook"]

# Product viewport — Chicago city focus
STATE_CONFIGS = {
    "CHICAGO": {
        "name": "Chicago",
        "lat": 41.8781,
        "lon": -87.6298,
        "zoom": 10.2,
        "state_code": "IL",
        "counties": CHICAGO_METRO_COUNTIES,
    },
    "ALL": {"name": "All United States", "lat": 39.8283, "lon": -98.5795, "zoom": 4.2},
    "AL": {"name": "Alabama", "lat": 32.8067, "lon": -86.7911, "zoom": 7.0},
    "AK": {"name": "Alaska", "lat": 61.3707, "lon": -152.4044, "zoom": 4.5},
    "AZ": {"name": "Arizona", "lat": 33.7298, "lon": -111.4312, "zoom": 6.8},
    "AR": {"name": "Arkansas", "lat": 34.9697, "lon": -92.3731, "zoom": 7.0},
    "CA": {"name": "California", "lat": 36.1162, "lon": -119.6816, "zoom": 6.0},
    "CO": {"name": "Colorado", "lat": 39.0598, "lon": -105.3111, "zoom": 6.8},
    "CT": {"name": "Connecticut", "lat": 41.5978, "lon": -72.7554, "zoom": 8.5},
    "DE": {"name": "Delaware", "lat": 39.3185, "lon": -75.5071, "zoom": 8.5},
    "DC": {"name": "District of Columbia", "lat": 38.8974, "lon": -77.0268, "zoom": 11.0},
    "FL": {"name": "Florida", "lat": 27.7663, "lon": -81.6868, "zoom": 6.6},
    "GA": {"name": "Georgia", "lat": 33.0406, "lon": -83.6431, "zoom": 6.8},
    "HI": {"name": "Hawaii", "lat": 21.0943, "lon": -157.4983, "zoom": 7.0},
    "ID": {"name": "Idaho", "lat": 44.2405, "lon": -114.4788, "zoom": 6.2},
    "IL": {"name": "Illinois", "lat": 40.0417, "lon": -89.1965, "zoom": 6.8},
    "IN": {"name": "Indiana", "lat": 39.8494, "lon": -86.2583, "zoom": 7.0},
    "IA": {"name": "Iowa", "lat": 42.0115, "lon": -93.2105, "zoom": 7.0},
    "KS": {"name": "Kansas", "lat": 38.5266, "lon": -96.7265, "zoom": 6.8},
    "KY": {"name": "Kentucky", "lat": 37.6681, "lon": -84.6701, "zoom": 7.0},
    "LA": {"name": "Louisiana", "lat": 31.1695, "lon": -91.8678, "zoom": 7.0},
    "ME": {"name": "Maine", "lat": 44.6939, "lon": -69.3819, "zoom": 6.8},
    "MD": {"name": "Maryland", "lat": 39.0639, "lon": -76.8021, "zoom": 7.8},
    "MA": {"name": "Massachusetts", "lat": 42.2302, "lon": -71.5301, "zoom": 8.0},
    "MI": {"name": "Michigan", "lat": 43.3266, "lon": -84.5361, "zoom": 6.5},
    "MN": {"name": "Minnesota", "lat": 45.6945, "lon": -93.9002, "zoom": 6.3},
    "MS": {"name": "Mississippi", "lat": 32.7416, "lon": -89.6787, "zoom": 7.0},
    "MO": {"name": "Missouri", "lat": 38.4561, "lon": -92.2884, "zoom": 6.8},
    "MT": {"name": "Montana", "lat": 46.9219, "lon": -110.4544, "zoom": 6.0},
    "NE": {"name": "Nebraska", "lat": 41.1254, "lon": -98.2681, "zoom": 6.8},
    "NV": {"name": "Nevada", "lat": 38.3135, "lon": -117.0554, "zoom": 6.2},
    "NH": {"name": "New Hampshire", "lat": 43.4525, "lon": -71.5639, "zoom": 7.8},
    "NJ": {"name": "New Jersey", "lat": 40.2989, "lon": -74.5210, "zoom": 8.0},
    "NM": {"name": "New Mexico", "lat": 34.8405, "lon": -106.2485, "zoom": 6.5},
    "NY": {"name": "New York", "lat": 42.1657, "lon": -74.9481, "zoom": 6.8},
    "NC": {"name": "North Carolina", "lat": 35.6301, "lon": -79.8064, "zoom": 6.8},
    "ND": {"name": "North Dakota", "lat": 47.5289, "lon": -99.7840, "zoom": 6.5},
    "OH": {"name": "Ohio", "lat": 40.3888, "lon": -82.7649, "zoom": 7.0},
    "OK": {"name": "Oklahoma", "lat": 35.5653, "lon": -96.9289, "zoom": 6.8},
    "OR": {"name": "Oregon", "lat": 44.5720, "lon": -122.0709, "zoom": 6.5},
    "PA": {"name": "Pennsylvania", "lat": 40.5908, "lon": -77.2098, "zoom": 7.0},
    "RI": {"name": "Rhode Island", "lat": 41.6809, "lon": -71.5118, "zoom": 9.2},
    "SC": {"name": "South Carolina", "lat": 33.8569, "lon": -80.9450, "zoom": 7.2},
    "SD": {"name": "South Dakota", "lat": 44.2998, "lon": -99.4388, "zoom": 6.5},
    "TN": {"name": "Tennessee", "lat": 35.7478, "lon": -86.6923, "zoom": 6.8},
    "TX": {"name": "Texas", "lat": 31.0545, "lon": -97.5635, "zoom": 5.8},
    "UT": {"name": "Utah", "lat": 40.1500, "lon": -111.8624, "zoom": 6.5},
    "VT": {"name": "Vermont", "lat": 44.0459, "lon": -72.7107, "zoom": 7.8},
    "VA": {"name": "Virginia", "lat": 37.5407, "lon": -78.8569, "zoom": 7.0},
    "WA": {"name": "Washington", "lat": 47.4009, "lon": -121.4905, "zoom": 6.6},
    "WV": {"name": "West Virginia", "lat": 38.4912, "lon": -80.9545, "zoom": 7.2},
    "WI": {"name": "Wisconsin", "lat": 44.2685, "lon": -89.6165, "zoom": 6.8},
    "WY": {"name": "Wyoming", "lat": 42.7560, "lon": -107.3025, "zoom": 6.5}
}

SUPPORTED_STATES = list(STATE_CONFIGS.keys())


def normalize_county_name(name: Optional[str]) -> str:
    """Normalize county labels for metro matching."""
    if not name:
        return ""
    return name.lower().replace(" county", "").split("(")[0].strip()


def is_chicago_metro_county(county: Optional[str]) -> bool:
    cleaned = normalize_county_name(county)
    return cleaned in {normalize_county_name(c) for c in CHICAGO_METRO_COUNTIES}


def resolve_query_state(state: Optional[str]) -> str:
    """Map product scope codes to filterable state/metro keys."""
    if not state:
        return DEFAULT_STATE
    upper = state.strip().upper()
    if upper in ("CHICAGO", "CHI", "CHICAGOLAND", "METRO"):
        return "CHICAGO"
    return upper
