import uuid
import time
import logging
from datetime import date
from typing import List, Optional

from backend.models.phases import StoryMapResponse, StoryMapSlide, StoryMapZone
from backend.services.advisory_engine import generate_home_garden_advisory, STATE_EXTENSIONS
from backend.services.state_lookup import resolve_state_code
from backend.services.vision_parcelizer import analyze_property_aerial

logger = logging.getLogger("story_map")


class StoryMapGenerator:
    """Phase 5: Step-by-step garden/homestead walkthrough from geolocation."""

    async def generate(
        self,
        latitude: float,
        longitude: float,
        state_code: str = "IL",
        county: Optional[str] = None,
        label: Optional[str] = None,
        mode: str = "gardener",
        acreage: Optional[float] = None
    ) -> StoryMapResponse:
        start = time.time()
        story_id = str(uuid.uuid4())[:10]
        st_upper = resolve_state_code(state_code, latitude, longitude)

        if acreage is None:
            acreage = {"gardener": 0.05, "homesteader": 0.02, "small_farm": 0.1}.get(mode, 0.05)

        advisory = generate_home_garden_advisory(
            latitude=latitude,
            longitude=longitude,
            county_name=county,
            location_label=label,
            state_code=st_upper
        )

        parcel_analysis = await analyze_property_aerial(
            image_bytes=b"STORYMAP",
            center_lat=latitude,
            center_lon=longitude,
            approx_acres=acreage
        )

        zones: List[StoryMapZone] = []
        for z in parcel_analysis.detected_zones:
            sq_ft = round(z.area_acres * 43560, 0)
            zones.append(StoryMapZone(
                zone_id=z.id,
                label=z.label,
                land_class=z.land_class.value,
                area_sq_ft=sq_ft,
                color_hex=z.color_hex,
                recommended_use=z.recommended_use,
                suitability_score=self._score_zone(z.land_class.value, mode),
                geojson_geometry=z.geojson_geometry
            ))

        ext = STATE_EXTENSIONS.get(st_upper, {})
        natives = ext.get("native_species", [])
        native_names = [n["common_name"] for n in natives[:4]]
        crop_names = [c.crop_name for c in advisory.top_garden_crops[:5]]

        location_label = label or county or f"{st_upper} Property"

        slides = self._build_slides(
            location_label=location_label,
            advisory=advisory,
            zones=zones,
            mode=mode,
            native_names=native_names,
            crop_names=crop_names,
            ext=ext,
            acreage=acreage,
            state_code=st_upper
        )

        checklist = self._build_90_day_checklist(advisory, mode, crop_names)
        elapsed = round((time.time() - start) * 1000, 2)

        return StoryMapResponse(
            story_id=story_id,
            location_label=location_label,
            latitude=latitude,
            longitude=longitude,
            state_code=st_upper,
            county=county,
            total_backyard_sq_ft=round(acreage * 43560, 0),
            zones=zones,
            slides=slides,
            top_crops=crop_names,
            native_plants=native_names,
            next_90_day_checklist=checklist,
            total_steps=len(slides),
            generation_time_ms=elapsed
        )

    def _score_zone(self, land_class: str, mode: str) -> int:
        scores = {
            "gardener": {"cropland": 95, "pasture": 80, "bare_soil_rock": 70, "forest_canopy": 30, "built_structure": 5, "water_body": 10},
            "homesteader": {"cropland": 90, "pasture": 95, "bare_soil_rock": 60, "forest_canopy": 50, "built_structure": 10, "water_body": 40},
            "small_farm": {"cropland": 98, "pasture": 90, "bare_soil_rock": 50, "forest_canopy": 40, "built_structure": 15, "water_body": 30},
        }
        return scores.get(mode, scores["gardener"]).get(land_class, 50)

    def _build_slides(
        self, location_label, advisory, zones, mode, native_names, crop_names, ext, acreage, state_code
    ) -> List[StoryMapSlide]:
        climate = advisory.climate
        soil = advisory.soil
        mode_label = {"gardener": "Chicago Backyard Garden", "homesteader": "Community Garden Plot", "small_farm": "Farmers Market Grower"}[mode]
        state_name = ext.get("state_name", state_code)

        return [
            StoryMapSlide(
                slide_number=1,
                title="Welcome",
                headline=f"Your {mode_label} Plan for {location_label}",
                body=(
                    f"This walkthrough is built for your property in {state_name} using USDA soil data, "
                    f"NOAA climate normals, and land-zone analysis. Follow each step to go from planning to planting."
                ),
                bullet_points=[
                    f"Location: {location_label}, {state_code}",
                    f"Property size: {acreage} acres ({acreage * 43560:.0f} sq ft)",
                    f"Ecoregion: {ext.get('ecoregion', 'temperate').replace('_', ' ').title()}",
                    f"Hardiness zone: {climate.hardiness_zone}"
                ],
                step_type="intro"
            ),
            StoryMapSlide(
                slide_number=2,
                title="Know Your Climate",
                headline=f"Zone {climate.hardiness_zone} — {climate.frost_free_days} Frost-Free Days",
                body=(
                    f"Your growing window runs from {climate.last_spring_frost_date} "
                    f"(last spring frost) to {climate.first_fall_frost_date} (first fall frost). "
                    f"Plan warm-season crops after the last frost and cool-season crops before it."
                ),
                bullet_points=[
                    f"Last spring frost: {climate.last_spring_frost_date}",
                    f"First fall frost: {climate.first_fall_frost_date}",
                    f"Frost-free days: {climate.frost_free_days}",
                    "Start seeds indoors 6–8 weeks before last frost for tomatoes and peppers"
                ],
                step_type="soil"
            ),
            StoryMapSlide(
                slide_number=3,
                title="Understand Your Soil",
                headline=f"{soil.native_texture.title()} Soil — pH {soil.native_ph_range}",
                body=soil.garden_suitability_summary,
                bullet_points=[
                    f"Soil series: {soil.soil_series}",
                    f"Texture: {soil.native_texture}",
                    f"Raised beds: {soil.raised_bed_recommendation[:100]}…" if len(soil.raised_bed_recommendation) > 100 else f"Raised beds: {soil.raised_bed_recommendation}",
                    "Send a soil sample to your county extension office for a lab test before amending"
                ],
                step_type="soil"
            ),
            StoryMapSlide(
                slide_number=4,
                title="Map Your Land Zones",
                headline=f"{len(zones)} Zones Identified on Your Property",
                body=(
                    f"Each zone on your {acreage}-acre property has a different best use for {mode_label.lower()} activities. "
                    f"Focus planting in zones with the highest suitability scores."
                ),
                bullet_points=[f"{z.label}: {z.recommended_use} — {z.area_sq_ft:,.0f} sq ft (score {z.suitability_score}/100)" for z in zones],
                step_type="zones"
            ),
            StoryMapSlide(
                slide_number=5,
                title="Place Your Garden",
                headline="Put Beds Where the Sun Shines",
                body=(
                    "Vegetables and fruit need 6+ hours of direct sun. Use open cropland and pasture zones first. "
                    "Keep compost and tools in shaded or built zones near the house."
                ),
                bullet_points=[
                    "South-facing slopes get the most winter sun",
                    "Keep beds 10+ feet from large trees to avoid root competition",
                    "Orient raised beds north–south for even sun on both sides",
                    "Avoid low spots that collect cold air and standing water"
                ],
                step_type="layout"
            ),
            StoryMapSlide(
                slide_number=6,
                title="Plan Your Layout",
                headline=f"Suggested {mode_label} Layout",
                body=self._layout_body(mode, acreage),
                bullet_points=self._layout_bullets(mode),
                step_type="layout"
            ),
            StoryMapSlide(
                slide_number=7,
                title="Choose Your Crops",
                headline="Best Crops for Your Climate",
                body=f"These crops are top-rated for {location_label} based on your frost dates and soil:",
                bullet_points=[f"{c.crop_name} — {c.difficulty}, {c.sun_requirement}" for c in advisory.top_garden_crops[:6]],
                step_type="crops"
            ),
            StoryMapSlide(
                slide_number=8,
                title="Your 90-Day Plan",
                headline="Seasonal Action Checklist",
                body="Work through these tasks over the next 90 days to go from planning to your first harvest.",
                bullet_points=self._build_90_day_checklist(advisory, mode, crop_names)[:8],
                step_type="checklist"
            ),
        ]

    def _layout_body(self, mode: str, acreage: float) -> str:
        if mode == "gardener":
            return f"For your {acreage}-acre lot, start with 2–3 raised beds (4×8 ft), a compost corner, and a pollinator border along the property edge."
        if mode == "homesteader":
            return f"On {acreage} acres, allocate zones for a kitchen garden, chicken coop, fruit orchard, compost, and a low-maintenance pollinator meadow."
        return f"On {acreage} acres, plan field blocks for market crops, a wash/pack station, a high tunnel, and cover-crop fallow fields."

    def _layout_bullets(self, mode: str) -> List[str]:
        if mode == "gardener":
            return [
                "Bed 1 (4×8 ft): Tomatoes + basil companion planting",
                "Bed 2 (4×8 ft): Greens — spinach, kale, lettuce",
                "Bed 3 (4×4 ft): Root crops — carrots, radishes, beets",
                "Border strip: Native wildflowers for pollinators"
            ]
        if mode == "homesteader":
            return [
                "Zone A: 4×8 raised beds for kitchen vegetables",
                "Zone B: Chicken coop (4–6 hens) with attached run",
                "Zone C: 6–8 dwarf fruit trees",
                "Zone D: 3-bin compost system near the garden",
                "Zone E: Native pollinator meadow"
            ]
        return [
            "Field 1 (2 ac): Market vegetables — tomatoes, peppers, squash",
            "Field 2 (2 ac): Greens & roots — succession planted weekly",
            "High tunnel (30×96 ft): Season extension",
            "Wash/pack station near farm stand",
            "Cover crop on remaining acreage"
        ]

    def _build_90_day_checklist(self, advisory, mode: str, crop_names: List[str]) -> List[str]:
        items = []
        for i, cal_items in list(advisory.monthly_garden_calendar.items())[:3]:
            for item in cal_items[:2]:
                items.append(f"[{i}] {item}")
        if mode == "homesteader":
            items.extend([
                "Order day-old chicks or schedule coop build",
                "Plant bare-root fruit trees while still dormant",
                "Set up 3-bin compost with a browns stockpile"
            ])
        if mode == "small_farm":
            items.extend([
                "Contact local FSA office about microloan programs",
                "Draft crop plan with planting dates and yields",
                "Apply to 2–3 farmers markets for the season"
            ])
        items.append(f"Priority crops: {', '.join(crop_names[:3])}")
        return items[:12]


story_map_generator = StoryMapGenerator()
