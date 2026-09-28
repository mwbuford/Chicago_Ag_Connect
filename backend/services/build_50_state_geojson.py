"""
Downloads standard US Counties GeoJSON and generates fast individual state GeoJSON files
for interactive boundary rendering and clicking across all 50 US States + DC.
"""
import urllib.request
import json
from pathlib import Path

FIPS_TO_STATE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "72": "PR"
}

def generate_50_state_county_boundaries():
    geojson_dir = Path(__file__).resolve().parent.parent / "static" / "geojson"
    geojson_dir.mkdir(parents=True, exist_ok=True)

    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    print("Fetching national US Counties GeoJSON from repository...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LocalAg/2.0)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        full_data = json.loads(resp.read().decode("utf-8"))

    print(f"Loaded {len(full_data['features'])} national county features.")

    state_features = {st: [] for st in FIPS_TO_STATE.values()}

    for feat in full_data["features"]:
        props = feat.get("properties", {})
        fips_state = props.get("STATE", "")
        st_code = FIPS_TO_STATE.get(fips_state)
        if not st_code:
            continue

        c_name = props.get("NAME", "")
        # Ensure standard properties
        feat["properties"]["NAME"] = c_name
        feat["properties"]["COUNTY_NAME"] = f"{c_name} County"
        feat["properties"]["STATE_CODE"] = st_code
        state_features[st_code].append(feat)

    saved_count = 0
    for st_code, feats in state_features.items():
        if not feats:
            continue
        
        # Ensure sequential numeric ids for MapLibre feature-state hover effects
        for idx, f in enumerate(feats):
            f["id"] = idx

        state_geojson = {
            "type": "FeatureCollection",
            "features": feats
        }
        out_file = geojson_dir / f"{st_code.lower()}_counties.geojson"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(state_geojson, f)
        saved_count += 1

    print(f"✓ Successfully generated {saved_count} state county boundary GeoJSON files in {geojson_dir}")

if __name__ == "__main__":
    generate_50_state_county_boundaries()
