import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.state_lookup import resolve_state_code, state_from_coordinates

client = TestClient(app)


def run_phases_4_6_tests():
    print("\n" + "=" * 60)
    print("PHASES 4 / 5 / 6 TEST SUITE")
    print("=" * 60)

    # State lookup
    assert resolve_state_code(None, 38.0293, -78.4767) == "VA"
    assert resolve_state_code("ALL", 30.2672, -97.7431) == "TX"
    assert resolve_state_code("Virginia", None, None) == "VA"
    print("✓ State lookup resolves VA, TX from coordinates and names")

    # Phase 4: Agronomy SLM modes — multi-state
    for mode, prompt, state, lat, lon, keyword in [
        ("gardener", "When should I transplant tomatoes?", "VA", 38.0293, -78.4767, "frost"),
        ("homesteader", "How many backyard chickens in a coop?", "TX", 30.2672, -97.7431, "chicken"),
        ("small_farm", "What should my small farm business plan include?", "CA", 36.7783, -119.4179, "farm"),
    ]:
        res = client.post("/api/ai/agronomy-slm", json={
            "prompt": prompt,
            "mode": mode,
            "state": state,
            "latitude": lat,
            "longitude": lon
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert f"v2-{mode}" in data["model_name"]
        assert data["context_injected"]["state"] == state
        print(f"✓ Phase 4: SLM mode '{mode}' for {state} ({data['inference_time_ms']}ms)")

    # SLM with no state but coordinates — should infer
    res_infer = client.post("/api/ai/agronomy-slm", json={
        "prompt": "What is my hardiness zone?",
        "mode": "gardener",
        "latitude": 38.0293,
        "longitude": -78.4767
    })
    assert res_infer.status_code == 200
    assert res_infer.json()["context_injected"]["state"] == "VA"
    print("✓ Phase 4: SLM infers VA from coordinates when state omitted")

    # Phase 5: Walkthrough (no satellite fields)
    res_map = client.get("/api/storymap/generate", params={
        "lat": 38.0293,
        "lon": -78.4767,
        "state": "VA",
        "county": "Albemarle",
        "label": "Test Homestead",
        "mode": "homesteader",
        "acres": 2.0
    })
    assert res_map.status_code == 200, res_map.text
    story = res_map.json()
    assert story["story_id"]
    assert story["total_steps"] == len(story["slides"]) >= 8
    assert story["state_code"] == "VA"
    assert "satellite_tile_url_template" not in story
    assert story["location_label"] == "Test Homestead"
    print(f"✓ Phase 5: Walkthrough generated ({story['total_steps']} steps)")

    # Phase 6: Resource hub
    res_paths = client.get("/api/resources/paths")
    assert res_paths.status_code == 200
    hub = res_paths.json()
    assert len(hub["paths"]) >= 4
    print(f"✓ Phase 6: Resource hub lists {len(hub['paths'])} paths")

    res_404 = client.get("/api/resources/paths/nonexistent_path")
    assert res_404.status_code == 404
    print("✓ Phase 6: Unknown path returns 404")

    print("\n" + "=" * 60)
    print("ALL PHASES 4–6 TESTS PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_phases_4_6_tests()
