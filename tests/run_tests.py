import sys
from fastapi.testclient import TestClient
from backend.main import app

def run():
    print("Testing Local Ag Backend API...")
    client = TestClient(app)

    # 1. Health
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("✓ /health passed:", res.json())

    # 2. Locations IL
    res = client.get("/api/map/locations?state=IL")
    assert res.status_code == 200, f"Locations IL failed: {res.status_code}"
    data = res.json()
    assert len(data) > 0, "No IL locations returned"
    print(f"✓ /api/map/locations?state=IL returned {len(data)} locations")

    # 3. GeoJSON VA
    res = client.get("/api/map/geojson?state=VA")
    assert res.status_code == 200
    geojson = res.json()
    assert geojson["type"] == "FeatureCollection"
    print(f"✓ /api/map/geojson?state=VA returned {len(geojson['features'])} features")

    # 4. Advisory Report
    res = client.get("/api/advisory/report?lat=40.11&lon=-88.20&name=PilotFarm")
    assert res.status_code == 200
    adv = res.json()
    assert adv["soil"]["soil_series"]
    assert len(adv["recommended_crops"]) >= 4
    print(f"✓ /api/advisory/report generated: Soil={adv['soil']['soil_series']}, Crops={len(adv['recommended_crops'])}")

    # 5. Parcel Analysis & Shapefile Exporter
    res = client.post("/api/parcels/analyze-demo?lat=40.11&lon=-88.20&acres=45.0")
    assert res.status_code == 200
    parcel = res.json()
    analysis_id = parcel["analysis_id"]
    print(f"✓ /api/parcels/analyze-demo generated: AnalysisID={analysis_id}, Zones={len(parcel['detected_zones'])}")

    # 6. Shapefile Download
    shp_res = client.get(f"/api/parcels/export/{analysis_id}/shapefile")
    assert shp_res.status_code == 200
    assert shp_res.headers["content-type"] == "application/zip"
    print(f"✓ /api/parcels/export/.../shapefile downloaded {len(shp_res.content)} bytes of zipped Shapefile (.shp/.shx/.dbf/.prj)")

    # 7. GeoJSON Download
    geo_res = client.get(f"/api/parcels/export/{analysis_id}/geojson")
    assert geo_res.status_code == 200
    print(f"✓ /api/parcels/export/.../geojson downloaded {len(geo_res.content)} bytes of GeoJSON")

    print("\nALL API TESTS PASSED SUCCESSFULLY! 🚀")

if __name__ == "__main__":
    run()
