from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from backend.models.spatial import ConsumerAgLocation, ConsumerEntityType, ConsumerMapFilter
from backend.services.data_store import consumer_store
from backend.config import STATE_CONFIGS, DEFAULT_STATE

router = APIRouter(prefix="/api/map", tags=["Consumer Local Ag Map"])


@router.get("/states")
def get_supported_states():
    """Chicago-only product surface."""
    return {"CHICAGO": STATE_CONFIGS["CHICAGO"]}


@router.get("/counties")
def get_state_counties(state: str = Query(DEFAULT_STATE, description="Region/state code, e.g. CHICAGO or IL")):
    """Returns county list with location counts for a selected region/state."""
    return consumer_store.get_counties_for_state(state)


@router.get("/locations", response_model=List[ConsumerAgLocation])
def get_locations(
    state: str = Query(DEFAULT_STATE, description="Region/state code, e.g. CHICAGO or IL"),
    county: Optional[str] = Query(None, description="County name, e.g. Cook, DuPage"),
    types: Optional[List[ConsumerEntityType]] = Query(None, description="Filter by entity types"),
    search: Optional[str] = Query(None, description="Search keyword in name, city, products"),
    snap_only: Optional[bool] = Query(False, description="Filter for markets accepting SNAP/EBT"),
    organic_only: Optional[bool] = Query(False, description="Filter for certified organic producers"),
    user_lat: Optional[float] = Query(None, description="User home latitude"),
    user_lon: Optional[float] = Query(None, description="User home longitude"),
    radius_miles: Optional[float] = Query(None, description="Search radius in miles, e.g. 20.0")
):
    """Query Chicagoland consumer food markets, CSAs, farm stands, and urban farms."""
    filter_obj = ConsumerMapFilter(
        state=state,
        county=county,
        types=types,
        search=search,
        snap_only=snap_only,
        organic_only=organic_only,
        user_lat=user_lat,
        user_lon=user_lon,
        radius_miles=radius_miles
    )
    return consumer_store.query(filter_obj)


@router.get("/geojson")
def get_locations_geojson(
    state: str = Query(DEFAULT_STATE),
    county: Optional[str] = Query(None),
    types: Optional[List[ConsumerEntityType]] = Query(None),
    search: Optional[str] = Query(None),
    snap_only: Optional[bool] = Query(False),
    organic_only: Optional[bool] = Query(False),
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    radius_miles: Optional[float] = Query(None)
):
    """Returns filtered locations as GeoJSON FeatureCollection."""
    filter_obj = ConsumerMapFilter(
        state=state,
        county=county,
        types=types,
        search=search,
        snap_only=snap_only,
        organic_only=organic_only,
        user_lat=user_lat,
        user_lon=user_lon,
        radius_miles=radius_miles
    )
    filtered = consumer_store.query(filter_obj)
    return consumer_store.to_geojson(filtered)


@router.get("/locations/{loc_id}", response_model=ConsumerAgLocation)
def get_location_by_id(loc_id: str):
    """Get consumer location details."""
    loc = consumer_store.get_by_id(loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc
