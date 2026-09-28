"""Resolve US state codes from coordinates or ambiguous state strings."""
from typing import Optional
import math

from backend.config import STATE_CONFIGS

# Full state name → 2-letter code (includes common Photon geocoder variants)
STATE_NAME_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


def normalize_state_code(value: Optional[str]) -> Optional[str]:
    """Convert state name or code to a 2-letter uppercase code, or None."""
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in ("CHICAGO", "CHI", "CHICAGOLAND", "METRO"):
        return "IL"
    if upper in STATE_CONFIGS and upper not in ("ALL", "CHICAGO"):
        return upper
    lower = raw.lower()
    if lower in STATE_NAME_TO_CODE:
        return STATE_NAME_TO_CODE[lower]
    for name, code in STATE_NAME_TO_CODE.items():
        if lower in name or name in lower:
            return code
    return None


def state_from_coordinates(latitude: float, longitude: float) -> Optional[str]:
    """Infer US state from lat/lon by nearest state centroid (skip metro/ALL)."""
    if latitude is None or longitude is None:
        return None
    best_code = None
    best_dist = float("inf")
    for code, cfg in STATE_CONFIGS.items():
        if code in ("ALL", "CHICAGO"):
            continue
        dlat = latitude - cfg["lat"]
        dlon = longitude - cfg["lon"]
        dist = math.sqrt(dlat * dlat + dlon * dlon)
        if dist < best_dist:
            best_dist = dist
            best_code = code
    return best_code


def resolve_state_code(
    state: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    fallback: str = "IL",
) -> str:
    """
    Resolve the best state code from explicit state and/or coordinates.
    Falls back to coordinate inference, then optional fallback (default IL).
    """
    normalized = normalize_state_code(state)
    if normalized:
        return normalized
    inferred = state_from_coordinates(latitude, longitude) if latitude and longitude else None
    if inferred:
        return inferred
    return fallback
