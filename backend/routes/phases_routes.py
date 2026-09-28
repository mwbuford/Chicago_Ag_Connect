from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from backend.models.phases import StoryMapResponse, ResourceHubResponse, LearningPath
from backend.services.story_map_service import story_map_generator
from backend.services.resource_hub_service import resource_hub_service

router = APIRouter(tags=["Story Map & Resource Hub"])


# ── Phase 5: Auto Story Map ──────────────────────────────────

@router.get("/api/storymap/generate", response_model=StoryMapResponse)
async def generate_story_map(
    lat: float = Query(..., description="Property latitude"),
    lon: float = Query(..., description="Property longitude"),
    state: str = Query("IL"),
    county: Optional[str] = Query(None),
    label: Optional[str] = Query(None, description="Address or property label"),
    mode: str = Query("gardener", description="gardener | homesteader | small_farm"),
    acres: Optional[float] = Query(None, description="Property size in acres")
):
    """
    Phase 5: Auto-generate a geolocation-based story map with satellite context,
    GIS land zones, crop recommendations, and a 90-day action checklist.
    """
    return await story_map_generator.generate(
        latitude=lat,
        longitude=lon,
        state_code=state,
        county=county,
        label=label,
        mode=mode,
        acreage=acres
    )


# ── Phase 6: Resource Hub ────────────────────────────────────

@router.get("/api/resources/paths", response_model=ResourceHubResponse)
def get_learning_paths():
    """Returns all homestead & farm learning paths with modules and checklists."""
    return resource_hub_service.get_all_paths()


@router.get("/api/resources/paths/{path_id}", response_model=LearningPath)
def get_learning_path(path_id: str):
    path = resource_hub_service.get_path(path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return path


@router.get("/api/resources/paths/{path_id}/sub/{sub_path_id}")
def get_sub_path_modules(path_id: str, sub_path_id: str):
    modules = resource_hub_service.get_modules_for_sub_path(path_id, sub_path_id)
    if not modules:
        raise HTTPException(status_code=404, detail="Sub-path not found")
    return {"path_id": path_id, "sub_path_id": sub_path_id, "modules": [m.model_dump() for m in modules]}
