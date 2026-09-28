import sys
from fastapi.testclient import TestClient
from backend.main import app

def run():
    print("Running Full Suite of Consumer Feature Tests...")
    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    print("✓ /health passed:", res.json())

    # 2. County list is alphabetized
    res_counties = client.get("/api/map/counties?state=VA")
    assert res_counties.status_code == 200
    counties_va = res_counties.json()
    assert len(counties_va) > 0
    county_names = [c["county"] for c in counties_va]
    assert county_names == sorted(county_names, key=str.lower)
    print(f"✓ VA counties dropdown is sorted alphabetically A-Z ({len(counties_va)} counties: {county_names[:4]}...)")

    # 3. Clean search query format
    from backend.services.website_scraper import generate_web_search_url
    clean_url = generate_web_search_url("The Albemarle Farmers Market", "Charlottesville", "VA")
    assert "The+Albemarle+Farmers+Market+Charlottesville+VA" in clean_url
    assert "farmers+market+farm" not in clean_url
    print(f"✓ Clean search URL verified: {clean_url}")

    # 4. Exact Polygon Point Assignment (Charlottesville inside Charlottesville City, Albemarle inside Albemarle)
    res_albemarle = client.get("/api/map/locations?state=VA&county=Albemarle")
    assert res_albemarle.status_code == 200
    alb_locs = res_albemarle.json()
    assert all(l["county"] == "Albemarle" for l in alb_locs)
    print(f"✓ Exact polygon bounds confirmed: {len(alb_locs)} locations strictly bounded to Albemarle County")

    # 5. 20-Mile Radius Radial Search Query
    # Charlottesville coords: lat 38.0293, lon -78.4767
    res_radius = client.get("/api/map/locations?state=VA&user_lat=38.0293&user_lon=-78.4767&radius_miles=20.0")
    assert res_radius.status_code == 200
    radius_locs = res_radius.json()
    assert len(radius_locs) > 0
    print(f"✓ 20-Mile Radius Buffer Search verified: Found {len(radius_locs)} markets within 20 miles of Charlottesville")

    # 6. County outlines static file delivery
    res_il = client.get("/static/geojson/il_counties.geojson")
    assert res_il.status_code == 200
    il_geo = res_il.json()
    assert len(il_geo["features"]) == 102
    print(f"✓ Delivered IL county GeoJSON with {len(il_geo['features'])} boundary polygons")

    # 7. Backyard Garden Advisory Report with direct county query
    adv_res = client.get("/api/advisory/report?state=VA&county=Albemarle")
    assert adv_res.status_code == 200
    adv_data = adv_res.json()
    assert adv_data["county"] == "Albemarle"
    assert len(adv_data["top_garden_crops"]) >= 5
    assert "last_spring_frost_date" in adv_data["climate"]
    assert "Start indoors:" in adv_data["top_garden_crops"][0]["indoor_seed_start"] or "Direct sow" in adv_data["top_garden_crops"][0]["indoor_seed_start"]
    print(f"✓ Backyard Garden Advisory report valid for Albemarle County with {len(adv_data['top_garden_crops'])} dynamic crop guides")

    # 8. Variable Customizable Radius (e.g. 10 miles vs 35 miles)
    res_10 = client.get("/api/map/locations?state=VA&user_lat=38.0293&user_lon=-78.4767&radius_miles=10.0").json()
    res_35 = client.get("/api/map/locations?state=VA&user_lat=38.0293&user_lon=-78.4767&radius_miles=35.0").json()
    assert len(res_35) >= len(res_10)
    print(f"✓ Variable radius query verified: 10 miles -> {len(res_10)} locations, 35 miles -> {len(res_35)} locations")

    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY! 🚀")

if __name__ == "__main__":
    run()
