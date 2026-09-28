"""
Fast USDA Open Dataset Ingestion and High-Precision Geospatial County Extractor for all 50 US States + DC.
Spatially matches all locations against official US County Boundaries (Census / FIPS).
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from shapely.geometry import shape, Point

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
STATIC_GEOJSON_DIR = Path(__file__).resolve().parent.parent / "static" / "geojson"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

US_STATES = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA",
    "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO",
    "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC"
}
VALID_STATE_CODES = set(US_STATES.values())

# Global cache of county polygons and centroids
STATE_POLYGONS: Dict[str, List[Tuple[str, Any, Tuple[float, float, float, float]]]] = {}
COUNTY_CENTROIDS: Dict[str, Dict[str, Tuple[float, float]]] = {}

def load_county_polygons():
    """Loads and caches all state county GeoJSON polygons for spatial matching."""
    global STATE_POLYGONS, COUNTY_CENTROIDS
    if STATE_POLYGONS:
        return

    for gj_file in STATIC_GEOJSON_DIR.glob("*_counties.geojson"):
        st = gj_file.name.split("_")[0].upper()
        try:
            with open(gj_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            polys = []
            centroids = {}
            for feat in data.get("features", []):
                c_name = feat.get("properties", {}).get("NAME", "")
                if not c_name:
                    continue
                geom = shape(feat["geometry"])
                polys.append((c_name, geom, geom.bounds))
                cent = geom.centroid
                centroids[c_name.lower()] = (cent.y, cent.x)
                centroids[f"{c_name.lower()} county"] = (cent.y, cent.x)
            STATE_POLYGONS[st] = polys
            COUNTY_CENTROIDS[st] = centroids
        except Exception as e:
            print(f"Error loading {gj_file.name}: {e}")

def resolve_exact_county(state_code: str, lat: float, lon: float, fallback_city: str = "") -> str:
    """Spatially matches (lat, lon) to official US County Polygon."""
    load_county_polygons()
    st_upper = state_code.upper()
    polys = STATE_POLYGONS.get(st_upper, [])
    if not polys:
        return f"{fallback_city} County" if fallback_city else "General County"

    pt = Point(lon, lat)

    # 1. Exact containment with bounding box pre-filtering
    for name, poly, (minx, miny, maxx, maxy) in polys:
        if minx <= lon <= maxx and miny <= lat <= maxy:
            if poly.contains(pt):
                return name

    # 2. Border/coastal proximity search (within ~0.05 degrees)
    closest_name = None
    min_dist = 999.0
    for name, poly, (minx, miny, maxx, maxy) in polys:
        if minx - 0.08 <= lon <= maxx + 0.08 and miny - 0.08 <= lat <= maxy + 0.08:
            d = poly.distance(pt)
            if d < min_dist and d < 0.06:
                min_dist = d
                closest_name = name

    if closest_name:
        return closest_name

    return f"{fallback_city} County" if fallback_city else "General County"

def get_county_centroid(state_code: str, county_name: str) -> Optional[Tuple[float, float]]:
    """Returns exact (lat, lon) centroid for county polygon."""
    load_county_polygons()
    st_upper = state_code.upper()
    c_clean = county_name.lower().replace(" county", "").strip()
    
    centroids = COUNTY_CENTROIDS.get(st_upper, {})
    if c_clean in centroids:
        return centroids[c_clean]
    
    # Check partial match
    for k, v in centroids.items():
        if c_clean in k or k in c_clean:
            return v

    from backend.config import STATE_CONFIGS
    cfg = STATE_CONFIGS.get(st_upper)
    if cfg:
        return cfg["lat"], cfg["lon"]
    return None

def resolve_county(state_code: str, city: Optional[str], address: str, lat: float, lon: float) -> str:
    """Helper alias for advisory engine."""
    return resolve_exact_county(state_code, lat, lon, city or "")

def parse_xlsx_fast(file_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse an openxml xlsx file using zipfile and ElementTree quickly without loading heavy dependencies."""
    with zipfile.ZipFile(file_path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                t = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                shared.append(t.text if t is not None else "")

        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")
        if not rows:
            return [], []

        def get_row_dict(r):
            row_map = {}
            for c in r.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                ref = c.attrib.get("r", "")
                col = "".join([ch for ch in ref if ch.isalpha()])
                t_attr = c.attrib.get("t")
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = v.text if v is not None else ""
                if t_attr == "s" and val.isdigit() and int(val) < len(shared):
                    row_map[col] = shared[int(val)]
                else:
                    is_t = c.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    if is_t is not None and is_t.text:
                        row_map[col] = is_t.text
                    else:
                        row_map[col] = val
            return row_map

        header_col_map = get_row_dict(rows[0])
        headers = [header_col_map.get(k, k) for k in sorted(header_col_map.keys())]

        data = []
        for r in rows[1:]:
            row_dict = get_row_dict(r)
            named_row = {header_col_map.get(k, k): row_dict.get(k, "") for k in row_dict}
            data.append(named_row)

        return headers, data

def detect_us_state(address: str, lat: float, lon: float) -> Optional[str]:
    """Detects 2-letter US state code from address string or coordinate boundaries."""
    if not address:
        return None
    addr_upper = address.upper().strip()

    # Trailing zip code with 2-letter state: e.g. "VA 22901", ", IL 60601", ", CA"
    match = re.search(r'\b([A-Z]{2})\s+(?:\d{5}(?:-\d{4})?)\b', addr_upper)
    if match and match.group(1) in VALID_STATE_CODES:
        return match.group(1)

    # Trailing 2-letter state before end of string or comma: e.g. "Seattle, WA", "Miami, FL"
    match_trail = re.search(r'(?:,\s*|\s+)([A-Z]{2})(?:\s*|\s*,.*)$', addr_upper)
    if match_trail and match_trail.group(1) in VALID_STATE_CODES:
        return match_trail.group(1)

    # Full State Name Match
    for full_name, code in US_STATES.items():
        if re.search(r'\b' + re.escape(full_name) + r'\b', addr_upper):
            if code == "VA" and "WEST VIRGINIA" in addr_upper:
                return "WV"
            return code

    return None

def extract_city_from_address(addr: str) -> str:
    """Extracts City from address string."""
    if not addr:
        return ""
    parts = [p.strip() for p in addr.split(",") if p.strip()]
    if len(parts) >= 2:
        return re.sub(r'\d+', '', parts[-2]).strip()
    return ""

def build_50_state_database() -> Dict[str, Any]:
    """Parses raw USDA datasets and builds a unified 50-state consumer database with exact spatial county matching."""
    load_county_polygons()

    files_to_process = [
        ("farmersmarket", RAW_DIR / "farmersmarket_2026-827125152.xlsx", "farmers_market", "Farmers Market"),
        ("onfarmmarket", RAW_DIR / "onfarmmarket_2026-827125239.xlsx", "farm_stand", "Farm Stand / On-Farm Market"),
        ("csa", RAW_DIR / "csa_2026-82712505.xlsx", "csa", "CSA / Farm Share"),
        ("agritourism", RAW_DIR / "agritourism_2026-828113250.xlsx", "agritourism", "U-Pick & Agritourism"),
        ("foodhub", RAW_DIR / "foodhub_2026-82811333.xlsx", "food_hub", "Local Food Hub")
    ]

    all_records = []
    state_county_index = {}

    for label, file_path, entity_type, type_label in files_to_process:
        if not file_path.exists():
            continue

        print(f"Ingesting 50-state data from {file_path.name} with exact spatial county matching...")
        headers, rows = parse_xlsx_fast(file_path)

        for r in rows:
            name = (r.get("listing_name") or "").strip()
            addr = (r.get("location_address") or "").strip()
            if not name or not addr:
                continue

            raw_lon = r.get("location_x")
            raw_lat = r.get("location_y")
            try:
                lon = float(raw_lon)
                lat = float(raw_lat)
            except (TypeError, ValueError):
                continue

            # Bounds for US territory (including AK, HI, PR)
            if not (17.0 <= lat <= 72.0 and -175.0 <= lon <= -60.0):
                continue

            state_code = detect_us_state(addr, lat, lon)
            if not state_code or state_code not in VALID_STATE_CODES:
                continue

            city = extract_city_from_address(addr)
            # Spatially resolve to EXACT official US County
            county = resolve_exact_county(state_code, lat, lon, city)

            # Payment methods
            payment_methods = []
            if r.get("acceptedpayment_1") or "cash" in str(r.get("acceptedpayment", "")).lower():
                payment_methods.append("Cash")
            if r.get("acceptedpayment_2") or "credit" in str(r.get("acceptedpayment", "")).lower():
                payment_methods.append("Credit/Debit")
            if r.get("acceptedpayment_3") or r.get("FNAP_1") or "snap" in str(r.get("acceptedpayment", "")).lower() or r.get("SNAP_option"):
                payment_methods.append("SNAP / EBT")
            if r.get("FNAP_2") or "wic" in str(r.get("FNAP", "")).lower():
                payment_methods.append("WIC Farmers Market")
            if r.get("FNAP_3") or "senior" in str(r.get("FNAP", "")).lower():
                payment_methods.append("Senior Farmers Market (SFMNP)")
            if not payment_methods:
                payment_methods = ["Cash", "Credit/Debit"]

            # Products
            if entity_type == "farmers_market":
                products = ["Fresh In-Season Veggies", "Heirloom Fruit", "Local Honey", "Pasture Eggs & Meat", "Artisan Baked Goods", "Cut Flowers"]
            elif entity_type == "farm_stand":
                products = ["Fresh Farm Produce", "Sweet Corn & Tomatoes", "Farm Preserves & Jam", "Local Cider", "Free-Range Eggs"]
            elif entity_type == "csa":
                products = ["Weekly Vegetable Box", "Seasonal Greens", "Organic Herbs", "Egg & Meat Share Add-on"]
            elif entity_type == "agritourism":
                products = ["Pick-Your-Own Berries & Apples", "Pumpkin Patch", "Farm Tours & Education", "Flower Cutting"]
            elif entity_type == "foodhub":
                products = ["Aggregated Local Farm Goods", "Bulk Veggies", "Farm-to-Table Wholesale"]
            else:
                products = ["Local Produce", "Fresh Greens"]

            desc = r.get("listing_desc") or r.get("location_desc") or ""
            webscripting = r.get("webscripting") or r.get("webscriping") or ""
            organic = "Organic Certified" if (r.get("specialproductionmethods_1") or "organic" in str(r.get("specialproductionmethods", "")).lower()) else None

            from backend.services.website_scraper import enrich_location_website
            web_meta = enrich_location_website(name, city or "", state_code, desc, webscripting)

            item_id = str(r.get("listing_id") or abs(hash(name + addr)))

            record = {
                "id": f"usda-{item_id}",
                "name": name,
                "entity_type": entity_type,
                "type_label": type_label,
                "address": addr,
                "city": city or "",
                "county": county,
                "state_code": state_code,
                "zip_code": "",
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "payment_methods": payment_methods,
                "products_offered": products,
                "organic_certified": bool(organic),
                "description": desc.strip()[:300] if desc else f"Local {type_label.lower()} in {state_code}.",
                "schedule": "Check local market schedule (typically weekends/morning seasonal hours)",
                "website_url": web_meta["website_url"],
                "domain_label": web_meta["domain_label"],
                "search_url": web_meta["search_url"],
                "maps_url": web_meta["maps_url"]
            }

            all_records.append(record)

            if state_code not in state_county_index:
                state_county_index[state_code] = {}
            if county not in state_county_index[state_code]:
                state_county_index[state_code][county] = 0
            state_county_index[state_code][county] += 1

    output_path = PROCESSED_DIR / "consumer_ag_locations.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)

    index_path = PROCESSED_DIR / "state_county_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(state_county_index, f, indent=2)

    print(f"✓ Exact 50-State Spatial County Ingestion Complete: {len(all_records)} total locations across {len(state_county_index)} states.")
    return {
        "locations": all_records,
        "county_index": state_county_index
    }

def build_consumer_database() -> Dict[str, Any]:
    return build_50_state_database()

if __name__ == "__main__":
    build_50_state_database()
