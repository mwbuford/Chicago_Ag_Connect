"""
Fetch City of Chicago open data overlays for Chicago Ag Connect.

Sources:
  - Farmers Market Dataset (iqus-3tju) — hours, Link/SNAP flags
  - Urban Farms (2a55-dhk8)

Writes: data/processed/chicago_local_overlays.json
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "chicago_local_overlays.json"

MARKETS_URL = "https://data.cityofchicago.org/resource/iqus-3tju.json?$limit=5000"
FARMS_URL = "https://data.cityofchicago.org/resource/2a55-dhk8.json?$limit=5000"


def _get_json(url: str) -> List[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "ChicagoAgConnect/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def _maps_url(lat: float, lon: float, label: str) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def market_rows_to_locations(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        name = (row.get("location") or "").strip()
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue
        if not name or abs(lat) < 1 or abs(lon) < 1:
            continue
        key = (name.lower(), round(lat, 4), round(lon, 4))
        if key in seen:
            continue
        seen.add(key)

        link_yes = str(row.get("link_accepted", "")).strip().upper() in ("YES", "Y", "TRUE", "1")
        day = (row.get("day") or "").strip()
        start = (row.get("start_time") or "").strip()
        end = (row.get("end_time") or "").strip()
        schedule_parts = [p for p in [day, f"{start}–{end}" if start and end else start or end] if p]
        schedule = ", ".join(schedule_parts) if schedule_parts else None
        intersection = (row.get("intersection") or "").strip()
        website = None
        if isinstance(row.get("website"), dict):
            website = row["website"].get("url")
        elif isinstance(row.get("website"), str):
            website = row.get("website")

        payments = ["Cash"]
        if link_yes:
            payments.extend(["SNAP / EBT", "Link Match"])

        loc_id = f"chi-market-{_slug(name)}-{int(lat * 10000)}"
        out.append({
            "id": loc_id,
            "name": name if "market" in name.lower() else f"{name} Farmers Market",
            "entity_type": "farmers_market",
            "type_label": "Farmers Market",
            "address": intersection or f"Chicago, IL",
            "city": "Chicago",
            "county": "Cook",
            "state_code": "IL",
            "zip_code": "",
            "latitude": lat,
            "longitude": lon,
            "payment_methods": payments,
            "products_offered": ["Fresh produce", "Local foods"],
            "organic_certified": False,
            "description": f"City of Chicago listed market ({row.get('type') or 'Independent'})."
                           + (" Accepts Link Match (SNAP)." if link_yes else ""),
            "schedule": schedule,
            "website_url": website,
            "domain_label": "City of Chicago" if not website else None,
            "search_url": f"https://www.google.com/search?q={name.replace(' ', '+')}+Chicago+farmers+market",
            "maps_url": _maps_url(lat, lon, name),
            "link_match": link_yes,
            "data_source": "city_of_chicago_farmers_markets",
        })
    return out


def farm_rows_to_locations(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, row in enumerate(rows):
        address = (row.get("address") or "").strip()
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue
        if abs(lat) < 1 or abs(lon) < 1:
            continue
        name = f"Chicago Urban Farm — {address.split(',')[0].strip()}" if address else f"Chicago Urban Farm #{i + 1}"
        loc_id = f"chi-urban-farm-{_slug(address or str(i))}-{int(lat * 10000)}"
        out.append({
            "id": loc_id,
            "name": name,
            "entity_type": "urban_farm",
            "type_label": "Urban Farm",
            "address": address or "Chicago, IL",
            "city": "Chicago",
            "county": "Cook",
            "state_code": "IL",
            "zip_code": "",
            "latitude": lat,
            "longitude": lon,
            "payment_methods": [],
            "products_offered": ["Urban agriculture", "Fresh produce"],
            "organic_certified": False,
            "description": "Urban farm site from the City of Chicago Urban Farms open dataset.",
            "schedule": None,
            "website_url": None,
            "domain_label": "City of Chicago",
            "search_url": f"https://www.google.com/search?q={address.replace(' ', '+')}+Chicago+urban+farm" if address else None,
            "maps_url": _maps_url(lat, lon, name),
            "link_match": False,
            "data_source": "city_of_chicago_urban_farms",
        })
    return out


def build_overlays() -> List[Dict[str, Any]]:
    markets = market_rows_to_locations(_get_json(MARKETS_URL))
    farms = farm_rows_to_locations(_get_json(FARMS_URL))
    curated = [
        {
            "id": "chi-ugc-main",
            "name": "Urban Growers Collective",
            "entity_type": "urban_farm",
            "type_label": "Urban Farm / Food Access",
            "address": "1200 W 35th St #118, Chicago, IL 60609",
            "city": "Chicago",
            "county": "Cook",
            "state_code": "IL",
            "zip_code": "60609",
            "latitude": 41.8305,
            "longitude": -87.6558,
            "payment_methods": ["SNAP / EBT", "Link Match", "Cash"],
            "products_offered": ["Fresh produce", "CSA", "Farm stand", "Youth training", "Mobile market"],
            "organic_certified": False,
            "description": "Black- and women-led Chicago non-profit urban farm connecting neighbors to affordable, culturally affirming food. Fresh Moves Mobile Market, CSA, farm stands, and grower training.",
            "schedule": "Check website for farm stands, markets & Fresh Moves stops",
            "website_url": "https://www.urbangrowerscollective.org/",
            "domain_label": "Urban Growers Collective",
            "search_url": "https://www.urbangrowerscollective.org/",
            "maps_url": "https://www.google.com/maps/search/?api=1&query=1200+W+35th+St+Chicago+IL",
            "link_match": True,
            "data_source": "urban_growers_collective",
        },
        {
            "id": "chi-access-link-up",
            "name": "Link Up Illinois / Link Match (Chicago)",
            "entity_type": "food_hub",
            "type_label": "Food Access Resource",
            "address": "Chicago, IL",
            "city": "Chicago",
            "county": "Cook",
            "state_code": "IL",
            "zip_code": "",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "payment_methods": ["SNAP / EBT", "Link Match"],
            "products_offered": ["SNAP match", "Fresh produce access"],
            "organic_certified": False,
            "description": "Link Match doubles SNAP dollars at participating Chicago farmers markets and farm stands.",
            "schedule": None,
            "website_url": "https://www.experimentalstation.org/linkup-overview",
            "domain_label": "Link Up Illinois",
            "search_url": "https://www.experimentalstation.org/linkup-overview",
            "maps_url": "https://www.google.com/maps/search/?api=1&query=Chicago+farmers+markets+SNAP",
            "link_match": True,
            "data_source": "link_up_illinois",
        },
        {
            "id": "chi-access-aua",
            "name": "Advocates for Urban Agriculture (AUA Chicago)",
            "entity_type": "urban_farm",
            "type_label": "Urban Ag Network",
            "address": "Chicago, IL",
            "city": "Chicago",
            "county": "Cook",
            "state_code": "IL",
            "zip_code": "",
            "latitude": 41.8675,
            "longitude": -87.6270,
            "payment_methods": [],
            "products_offered": ["Urban agriculture advocacy", "Grower network"],
            "organic_certified": False,
            "description": "Chicago network supporting urban growers and food justice.",
            "schedule": None,
            "website_url": "https://www.auachicago.org/",
            "domain_label": "AUA Chicago",
            "search_url": "https://www.auachicago.org/",
            "maps_url": "https://www.google.com/maps/search/?api=1&query=Chicago+urban+agriculture",
            "link_match": False,
            "data_source": "aua_chicago",
        },
    ]
    combined = markets + farms + curated
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    print(f"Wrote {len(markets)} markets + {len(farms)} urban farms + {len(curated)} curated → {OUT}")
    return combined


if __name__ == "__main__":
    build_overlays()
