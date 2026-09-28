import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.models.spatial import ConsumerAgLocation, ConsumerEntityType, ConsumerMapFilter
from backend.config import (
    PROCESSED_DATA_DIR,
    CHICAGO_METRO_COUNTIES,
    normalize_county_name,
    is_chicago_metro_county,
    resolve_query_state,
)
from backend.services.usda_consumer_parser import build_consumer_database


class ConsumerDataStore:
    def __init__(self):
        self._locations: List[ConsumerAgLocation] = []
        self._county_index: Dict[str, Dict[str, int]] = {"IL": {}, "VA": {}}
        self._id_map: Dict[str, ConsumerAgLocation] = {}
        self.initialize()

    def initialize(self):
        file_path = PROCESSED_DATA_DIR / "consumer_ag_locations.json"
        index_path = PROCESSED_DATA_DIR / "state_county_index.json"
        overlay_path = PROCESSED_DATA_DIR / "chicago_local_overlays.json"

        if not file_path.exists() or not index_path.exists():
            build_consumer_database()

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            self._locations = [ConsumerAgLocation(**item) for item in raw_data]

        with open(index_path, "r", encoding="utf-8") as f:
            self._county_index = json.load(f)

        self._id_map = {loc.id: loc for loc in self._locations}

        # Merge City of Chicago open-data overlays (markets + urban farms)
        if overlay_path.exists():
            with open(overlay_path, "r", encoding="utf-8") as f:
                overlays = json.load(f)
            for item in overlays:
                try:
                    loc = ConsumerAgLocation(**item)
                except Exception:
                    continue
                if loc.id in self._id_map:
                    continue
                if self._near_duplicate(loc):
                    continue
                self._locations.append(loc)
                self._id_map[loc.id] = loc

        self._rebuild_chicago_county_index()

    def _near_duplicate(self, candidate: ConsumerAgLocation, tol: float = 0.002) -> bool:
        cname = candidate.name.strip().lower()
        for loc in self._locations:
            if loc.state_code != "IL":
                continue
            if abs(loc.latitude - candidate.latitude) > tol:
                continue
            if abs(loc.longitude - candidate.longitude) > tol:
                continue
            if loc.name.strip().lower() == cname or cname in loc.name.lower() or loc.name.lower() in cname:
                # Enrich existing USDA row with Link Match / schedule when missing
                if candidate.link_match and not any("SNAP" in p.upper() for p in loc.payment_methods):
                    loc.payment_methods = list(dict.fromkeys(loc.payment_methods + ["SNAP / EBT", "Link Match"]))
                if candidate.schedule and not loc.schedule:
                    loc.schedule = candidate.schedule
                if candidate.link_match:
                    loc.link_match = True
                return True
        return False

    def _rebuild_chicago_county_index(self):
        counts: Dict[str, int] = {c: 0 for c in CHICAGO_METRO_COUNTIES}
        for loc in self._locations:
            if loc.state_code != "IL":
                continue
            for metro in CHICAGO_METRO_COUNTIES:
                if normalize_county_name(loc.county) == normalize_county_name(metro):
                    counts[metro] += 1
                    break
        self._county_index["CHICAGO"] = {k: v for k, v in counts.items() if v > 0}

    def get_counties_for_state(self, state_code: str) -> List[Dict[str, Any]]:
        state_upper = resolve_query_state(state_code)
        if state_upper in ["ALL", "US"]:
            all_counties = {}
            for st, c_dict in self._county_index.items():
                if st == "CHICAGO":
                    continue
                for c_name, cnt in c_dict.items():
                    all_counties[f"{c_name} ({st})"] = all_counties.get(f"{c_name} ({st})", 0) + cnt
            return sorted(
                [{"county": k, "count": v} for k, v in all_counties.items()],
                key=lambda x: x["county"].lower()
            )
        if state_upper == "CHICAGO":
            counties_dict = self._county_index.get("CHICAGO", {})
            # Ensure all metro counties appear even if zero (after filter rebuild)
            for c in CHICAGO_METRO_COUNTIES:
                counties_dict.setdefault(c, 0)
            return sorted(
                [{"county": k, "count": v} for k, v in counties_dict.items()],
                key=lambda x: (-x["count"], x["county"].lower())
            )
        counties_dict = self._county_index.get(state_upper, {})
        return sorted(
            [{"county": k, "count": v} for k, v in counties_dict.items()],
            key=lambda x: x["county"].lower()
        )

    def get_by_id(self, loc_id: str) -> Optional[ConsumerAgLocation]:
        return self._id_map.get(loc_id)

    def query(self, filters: ConsumerMapFilter) -> List[ConsumerAgLocation]:
        state_key = resolve_query_state(filters.state)

        if state_key in ["ALL", "US"]:
            results = list(self._locations)
        elif state_key == "CHICAGO":
            results = [
                l for l in self._locations
                if l.state_code == "IL" and is_chicago_metro_county(l.county)
            ]
        else:
            results = [l for l in self._locations if l.state_code == state_key]

        if filters.radius_miles and filters.user_lat is not None and filters.user_lon is not None:
            import math

            def haversine_miles(lat1, lon1, lat2, lon2):
                R = 3958.8
                dlat = math.radians(lat2 - lat1)
                dlon = math.radians(lon2 - lon1)
                a = (math.sin(dlat / 2) ** 2 +
                     math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                     math.sin(dlon / 2) ** 2)
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return R * c

            results = [
                l for l in results
                if haversine_miles(filters.user_lat, filters.user_lon, l.latitude, l.longitude) <= filters.radius_miles
            ]
        elif filters.county and filters.county.lower() != "all":
            c_clean = normalize_county_name(filters.county)
            results = [
                l for l in results
                if normalize_county_name(l.county) == c_clean
                or c_clean in normalize_county_name(l.county)
            ]

        if filters.types and len(filters.types) > 0:
            type_set = set(filters.types)
            results = [l for l in results if l.entity_type in type_set]

        if filters.snap_only:
            results = [
                l for l in results
                if l.link_match or any("SNAP" in p.upper() or "LINK" in p.upper() for p in l.payment_methods)
            ]

        if filters.organic_only:
            results = [l for l in results if l.organic_certified]

        if filters.search:
            q = filters.search.lower()
            results = [
                l for l in results
                if q in l.name.lower() or
                   q in l.city.lower() or
                   q in l.county.lower() or
                   (l.description and q in l.description.lower()) or
                   any(q in p.lower() for p in l.products_offered)
            ]

        return results

    def to_geojson(self, locations: List[ConsumerAgLocation]) -> Dict[str, Any]:
        features = []
        for loc in locations:
            features.append({
                "type": "Feature",
                "id": loc.id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [loc.longitude, loc.latitude]
                },
                "properties": {
                    "id": loc.id,
                    "name": loc.name,
                    "entity_type": loc.entity_type.value,
                    "type_label": loc.type_label,
                    "address": loc.address,
                    "city": loc.city,
                    "county": loc.county,
                    "state_code": loc.state_code,
                    "zip_code": loc.zip_code,
                    "payment_methods": loc.payment_methods,
                    "products_offered": loc.products_offered,
                    "organic_certified": loc.organic_certified,
                    "schedule": loc.schedule,
                    "description": loc.description,
                    "website_url": loc.website_url,
                    "domain_label": loc.domain_label,
                    "search_url": loc.search_url,
                    "maps_url": loc.maps_url,
                    "link_match": loc.link_match,
                    "data_source": loc.data_source,
                }
            })
        return {
            "type": "FeatureCollection",
            "features": features
        }


consumer_store = ConsumerDataStore()
