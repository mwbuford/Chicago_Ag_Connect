from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConsumerEntityType(str, Enum):
    FARMERS_MARKET = "farmers_market"
    FARM_STAND = "farm_stand"
    CSA = "csa"
    AGRITOURISM = "agritourism"
    FOOD_HUB = "food_hub"
    URBAN_FARM = "urban_farm"


class ConsumerAgLocation(BaseModel):
    id: str
    name: str
    entity_type: ConsumerEntityType
    type_label: str
    address: str
    city: str
    county: str
    state_code: str
    zip_code: str
    latitude: float
    longitude: float
    payment_methods: List[str] = Field(default_factory=list)
    products_offered: List[str] = Field(default_factory=list)
    organic_certified: bool = False
    description: Optional[str] = None
    schedule: Optional[str] = None
    website_url: Optional[str] = None
    domain_label: Optional[str] = None
    search_url: Optional[str] = None
    maps_url: Optional[str] = None
    link_match: bool = False
    data_source: Optional[str] = None


class ConsumerMapFilter(BaseModel):
    state: str = "CHICAGO"
    county: Optional[str] = None
    types: Optional[List[ConsumerEntityType]] = None
    search: Optional[str] = None
    snap_only: Optional[bool] = False
    organic_only: Optional[bool] = False
    user_lat: Optional[float] = None
    user_lon: Optional[float] = None
    radius_miles: Optional[float] = None
