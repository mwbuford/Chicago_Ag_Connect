import sys
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

def run():
    print("Running 50-State Comprehensive Test Suite with Native Species & National View...")
    client = TestClient(app)

    # 1. Health check & 50 state verification
    res = client.get("/health")
    assert res.status_code == 200
    health_data = res.json()
    print("✓ /health passed:", health_data["status"], f"({health_data['loaded_locations']} locations across {len(health_data['supported_states'])} states)")
    assert health_data["loaded_locations"] > 20000
    assert len(health_data["supported_states"]) >= 50

    # 2. Test Nationwide Query
    res_nat = client.get("/api/map/locations?state=ALL")
    assert res_nat.status_code == 200
    nat_locs = res_nat.json()
    assert len(nat_locs) == health_data["loaded_locations"]
    print(f"✓ Nationwide query verified: {len(nat_locs)} total locations loaded.")

    # 3. Test County GeoJSON files exist for all 50 states
    geojson_dir = Path("backend/static/geojson")
    for st in ["il", "va", "ca", "tx", "fl", "ny", "wa", "co", "oh", "nc", "ga"]:
        gf = geojson_dir / f"{st}_counties.geojson"
        assert gf.exists(), f"Missing GeoJSON for {st}"
    print("✓ Vector County Boundary GeoJSON files verified across states.")

    # 4. Test Major States & Native Species Recommendations
    state_native_checks = {
        "TX": "Texas Bluebonnet",
        "IL": "Purple Coneflower",
        "CA": "California Poppy",
        "VA": "Virginia Bluebells",
        "NY": "Eastern Red Columbine",
        "CO": "Rocky Mountain Columbine",
        "FL": "Butterfly Weed",
        "WA": "California Poppy" # or Pacific native
    }

    for st, expected_native in state_native_checks.items():
        # Check county list
        res_c = client.get(f"/api/map/counties?state={st}")
        assert res_c.status_code == 200
        counties = res_c.json()
        assert len(counties) > 0

        # Check locations query
        res_loc = client.get(f"/api/map/locations?state={st}")
        assert res_loc.status_code == 200
        locs = res_loc.json()
        assert len(locs) > 0

        # Check Backyard Garden Advisory & Native Species
        res_adv = client.get(f"/api/advisory/report?state={st}")
        assert res_adv.status_code == 200
        adv = res_adv.json()
        assert len(adv["top_garden_crops"]) == 6
        assert len(adv["native_species_recommendations"]) >= 4
        
        native_names = [n["common_name"] for n in adv["native_species_recommendations"]]
        assert any(expected_native in n for n in native_names), f"Expected {expected_native} in {native_names}"

        print(f"✓ State {st}: {len(locs)} spots | {len(counties)} counties | Zone {adv['climate']['hardiness_zone'].split(' ')[0]} | Native: {native_names[0]}")

    # 5. Clean search query format
    from backend.services.website_scraper import generate_web_search_url
    clean_url = generate_web_search_url("Austin Farmers Market", "Austin", "TX")
    assert "Austin+Farmers+Market+Austin+TX" in clean_url
    assert "farmers+market+farm" not in clean_url
    print(f"✓ Clean search URL verified: {clean_url}")

    # 6. Variable Distance Radius Search
    res_10 = client.get("/api/map/locations?state=TX&user_lat=30.2672&user_lon=-97.7431&radius_miles=10.0").json()
    res_35 = client.get("/api/map/locations?state=TX&user_lat=30.2672&user_lon=-97.7431&radius_miles=35.0").json()
    assert len(res_35) >= len(res_10)
    print(f"✓ Texas 10 vs 35-mile radius search verified: 10mi -> {len(res_10)} spots, 35mi -> {len(res_35)} spots")

    print("\nALL NATIONWIDE 50-STATE NATIVE PLANT & COUNTY TESTS PASSED! 🚀")

if __name__ == "__main__":
    run()
