from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SoilProfile(BaseModel):
    soil_series: str = "Agricultural Silt Loam"
    drainage_class: str = "Moderately well drained"
    ph_min: float = 6.0
    ph_max: float = 7.0
    organic_matter_percent: float = 4.0
    farmland_class: str = "Prime farmland"
    slope_gradient_percent: float = 2.0
    available_water_capacity: float = 0.18
    hydrologic_group: str = "B"

class BackyardSoilProfile(BaseModel):
    soil_series: str
    native_texture: str
    drainage_character: str
    native_ph_range: str
    organic_matter_level: str
    garden_suitability_summary: str
    raised_bed_recommendation: str

class BackyardClimateProfile(BaseModel):
    hardiness_zone: str
    last_spring_frost_date: str
    first_fall_frost_date: str
    frost_free_days: int
    sunlight_climate_summary: str

class GardenCropGuide(BaseModel):
    crop_name: str
    garden_category: str # "Raised Bed Champion", "Container Friendly", "In-Ground Favorite", "Herb & Tea"
    difficulty: str # "Beginner Friendly", "Easy", "Moderate"
    suitability_score: int # 0-100
    why_it_works_here: str
    indoor_seed_start: Optional[str] = None
    outdoor_transplant_window: str
    harvest_season: str
    sun_requirement: str # "Full Sun (6+ hrs)", "Partial Sun (4-6 hrs)"
    container_depth_inches: int
    backyard_pro_tip: str

class NativePlantGuide(BaseModel):
    common_name: str
    botanical_name: str
    plant_category: str # "Native Wildflower & Pollinator", "Native Edible Berry / Fruit", "Native Shrub & Hedgerow", "Native Grass & Groundcover"
    ecoregion_benefits: str
    sun_and_soil: str
    water_needs: str # "Low / Drought-Tolerant", "Moderate", "Moist / Riparian"
    best_garden_use: str

class HomeGardenAdvisoryReport(BaseModel):
    location_label: str
    county: str
    state_code: str
    latitude: float
    longitude: float
    soil: BackyardSoilProfile
    climate: BackyardClimateProfile
    top_garden_crops: List[GardenCropGuide]
    native_species_recommendations: List[NativePlantGuide] = []
    organic_soil_recipe: List[str]
    monthly_garden_calendar: Dict[str, List[str]]
    common_pitfalls_to_avoid: List[str]
