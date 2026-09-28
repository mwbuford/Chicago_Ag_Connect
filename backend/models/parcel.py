from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LandClass(str, Enum):
    CROPLAND = "cropland"
    PASTURE = "pasture"
    FOREST = "forest_canopy"
    WATER = "water_body"
    STRUCTURE = "built_structure"
    BARE_SOIL = "bare_soil_rock"

class ParcelPolygon(BaseModel):
    id: str
    land_class: LandClass
    label: str
    area_acres: float
    avg_slope_percent: float
    recommended_use: str
    soil_type: Optional[str] = None
    geojson_geometry: Dict[str, Any]
    color_hex: str

class PropertyAnalysisResponse(BaseModel):
    analysis_id: str
    total_acres: float
    detected_zones: List[ParcelPolygon]
    slope_summary: Dict[str, float]
    zoning_breakdown: Dict[str, float] # percentage per land_class
    agronomic_recommendations: List[str]
    shapefile_download_url: str
    geojson_download_url: str
