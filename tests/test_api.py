import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["loaded_locations"] > 0

def test_map_locations():
    res = client.get("/api/map/locations?state=IL")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert all(d["state_code"] == "IL" for d in data)

def test_map_geojson():
    res = client.get("/api/map/geojson?state=VA")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

def test_advisory_report():
    res = client.get("/api/advisory/report?lat=40.11&lon=-88.20&name=TestFarm")
    assert res.status_code == 200
    data = res.json()
    assert "soil" in data
    assert "climate" in data
    assert len(data["top_garden_crops"]) > 0
    assert len(data["organic_soil_recipe"]) > 0

def test_parcel_demo_and_export():
    # 1. Run Demo Parcel Analysis
    res = client.post("/api/parcels/analyze-demo?lat=40.11&lon=-88.20&acres=50")
    assert res.status_code == 200
    data = res.json()
    analysis_id = data["analysis_id"]
    assert len(data["detected_zones"]) == 5
    assert data["total_acres"] > 0

    # 2. Download Shapefile ZIP
    shp_res = client.get(f"/api/parcels/export/{analysis_id}/shapefile")
    assert shp_res.status_code == 200
    assert shp_res.headers["content-type"] == "application/zip"
    assert len(shp_res.content) > 0

    # 3. Download GeoJSON
    geo_res = client.get(f"/api/parcels/export/{analysis_id}/geojson")
    assert geo_res.status_code == 200
    assert "FeatureCollection" in geo_res.text
