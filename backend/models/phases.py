from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# ── Phase 4: Agronomy SLM Modes ──────────────────────────────

AgronomyMode = Literal["gardener", "homesteader", "small_farm"]


# ── Phase 5: Auto Story Map ──────────────────────────────────

class StoryMapZone(BaseModel):
    zone_id: str
    label: str
    land_class: str
    area_sq_ft: float
    color_hex: str
    recommended_use: str
    suitability_score: int
    geojson_geometry: Dict[str, Any] = Field(default_factory=dict)


class StoryMapSlide(BaseModel):
    slide_number: int
    title: str
    headline: str
    body: str
    bullet_points: List[str] = Field(default_factory=list)
    step_type: Optional[str] = None  # intro | soil | zones | layout | crops | checklist


class StoryMapResponse(BaseModel):
    story_id: str
    location_label: str
    latitude: float
    longitude: float
    state_code: str
    county: Optional[str] = None
    total_backyard_sq_ft: float
    zones: List[StoryMapZone]
    slides: List[StoryMapSlide]
    top_crops: List[str] = Field(default_factory=list)
    native_plants: List[str] = Field(default_factory=list)
    next_90_day_checklist: List[str] = Field(default_factory=list)
    total_steps: int = 0
    generation_time_ms: float = 0.0


# ── Phase 6: Resource Hub ────────────────────────────────────

class ResourceModule(BaseModel):
    module_id: str
    title: str
    summary: str
    checklist: List[str] = Field(default_factory=list)
    ai_prompt_suggestion: Optional[str] = None
    estimated_weeks: int = 1


class SubPath(BaseModel):
    sub_path_id: str
    label: str
    description: str
    icon: str
    modules: List[str] = Field(default_factory=list)


class LearningPath(BaseModel):
    path_id: str
    title: str
    description: str
    icon: str
    target_audience: str
    agronomy_mode: AgronomyMode
    modules: List[ResourceModule]
    total_modules: int
    sub_paths: List[SubPath] = Field(default_factory=list)
    cta_label: Optional[str] = None
    cta_action: Optional[str] = None  # story_map | list_farm | ai_chat


class ResourceHubResponse(BaseModel):
    paths: List[LearningPath]
    featured_path_id: str
