from fastapi import APIRouter, Query
from typing import Optional
from backend.models.advisory import HomeGardenAdvisoryReport
from backend.services.advisory_engine import generate_home_garden_advisory
from backend.services.state_lookup import resolve_state_code, normalize_state_code
from backend.config import STATE_CONFIGS, DEFAULT_STATE

router = APIRouter(prefix="/api/advisory", tags=["Home Garden & Land Advisory"])

CHICAGO_DEFAULT = STATE_CONFIGS["CHICAGO"]


@router.get("/report", response_model=HomeGardenAdvisoryReport)
def get_home_garden_report(
    state: str = Query(DEFAULT_STATE, description="Region/state code, e.g. CHICAGO or IL"),
    county: Optional[str] = Query(None, description="County name, e.g. Cook, DuPage"),
    lat: Optional[float] = Query(None, description="Optional custom property latitude"),
    lon: Optional[float] = Query(None, description="Optional custom property longitude"),
    label: Optional[str] = Query(None, description="Custom label for user's garden or parcel")
):
    """
    Generates a home-gardener land advisory for Chicagoland (or another selected state)
    with soil profile, frost dates, top recommended backyard crops, and organic care roadmap.
    """
    state_upper = normalize_state_code(state) or state.upper()
    if state_upper in ("CHICAGO", "CHI", "CHICAGOLAND"):
        state_upper = "IL"

    if state_upper in ["ALL", "US", None] and county and county.lower() != "all":
        from backend.services.usda_consumer_parser import COUNTY_CENTROIDS, load_county_polygons
        load_county_polygons()
        c_clean = county.lower().split("(")[0].replace(" county", "").strip()
        for st_code, c_dict in COUNTY_CENTROIDS.items():
            if c_clean in c_dict:
                state_upper = st_code
                break

    calc_lat = lat
    calc_lon = lon

    if county and county.lower() != "all" and state_upper and state_upper not in ["ALL", "US"]:
        from backend.services.usda_consumer_parser import get_county_centroid
        centroid = get_county_centroid(state_upper, county)
        if centroid:
            if calc_lat is None or calc_lon is None:
                calc_lat, calc_lon = centroid

    if calc_lat is None or calc_lon is None:
        cfg = STATE_CONFIGS.get(
            state if state.upper() == "CHICAGO" else (state_upper if state_upper not in ["ALL", "US", None] else "CHICAGO"),
            CHICAGO_DEFAULT,
        )
        if calc_lat is None:
            calc_lat = cfg.get("lat", CHICAGO_DEFAULT["lat"])
        if calc_lon is None:
            calc_lon = cfg.get("lon", CHICAGO_DEFAULT["lon"])

    state_upper = resolve_state_code(state_upper if state_upper not in ["ALL", "US"] else None, calc_lat, calc_lon)

    return generate_home_garden_advisory(
        latitude=calc_lat,
        longitude=calc_lon,
        county_name=county,
        location_label=label,
        state_code=state_upper
    )
