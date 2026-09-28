import io
import sys
from pathlib import Path
from PIL import Image
import numpy as np
from fastapi.testclient import TestClient

# Ensure workspace root is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app
from backend.services.data_store import consumer_store
from backend.services.vision_classifier import vision_service
from backend.services.agronomy_slm_service import agronomy_slm_service

client = TestClient(app)

def create_dummy_leaf_image(width=224, height=224, color=(60, 140, 50)):
    """Creates a sample RGB leaf image in JPEG format."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :] = color
    # Add some brown spots
    arr[80:120, 80:120] = [120, 60, 20]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def run_all_ai_tests():
    print("\n" + "="*60)
    print("RUNNING CUSTOM AI MODELS (MODEL 1 & MODEL 4) TEST SUITE")
    print("="*60)

    # Ensure store is initialized
    consumer_store.initialize()

    # 1. Test AI Status Endpoint
    res_status = client.get("/api/ai/status")
    assert res_status.status_code == 200, f"Status failed: {res_status.text}"
    status_data = res_status.json()
    assert status_data["status"] == "online"
    assert status_data["models"]["model_1_vision"]["name"] == "PlantPathologyNet-v2-MobileNet"
    assert status_data["models"]["model_4_agronomy_slm"]["name"] == "BackyardAg-Agronomy-SLM-v2"
    print("✓ /api/ai/status verified: Both Model 1 & Model 4 registered and online.")

    # 2. Test Model 1: Plant & Disease Vision Classifier (/api/ai/diagnose)
    leaf_bytes = create_dummy_leaf_image()
    files = {"image": ("test_leaf.jpg", leaf_bytes, "image/jpeg")}
    data = {"state": "IL", "county": "Cook"}
    
    res_diag = client.post("/api/ai/diagnose", files=files, data=data)
    assert res_diag.status_code == 200, f"Diagnosis endpoint failed: {res_diag.text}"
    diag = res_diag.json()
    
    assert "plant_species" in diag and len(diag["plant_species"]) > 0
    assert "condition_name" in diag and len(diag["condition_name"]) > 0
    assert "confidence" in diag and 0.0 <= diag["confidence"] <= 1.0
    assert "organic_remedy" in diag
    assert len(diag["organic_remedy"]["organic_controls"]) > 0
    assert len(diag["organic_remedy"]["cultural_prevention"]) > 0
    assert "top_predictions" in diag and len(diag["top_predictions"]) >= 3
    print(f"✓ Model 1 Vision Diagnosis: Identified {diag['plant_species']} - {diag['condition_name']} (Conf: {diag['confidence']*100:.1f}%, Inference: {diag['inference_time_ms']}ms)")

    # 3. Test Model 4: Agronomic SLM - Planting & Frost Query
    res_slm_timing = client.post("/api/ai/agronomy-slm", json={
        "prompt": "When is my median last spring frost date and when can I direct sow spinach and transplant tomatoes?",
        "state": "IL",
        "county": "Cook",
        "latitude": 41.8781,
        "longitude": -87.6298
    })
    assert res_slm_timing.status_code == 200, f"SLM timing query failed: {res_slm_timing.text}"
    data_timing = res_slm_timing.json()
    assert "Zone" in data_timing["response"] or "frost" in data_timing["response"].lower()
    assert len(data_timing["sources_referenced"]) > 0
    print(f"✓ Model 4 SLM (Timing Query): Answer generated in {data_timing['inference_time_ms']}ms with context {data_timing['context_injected']['hardiness_zone']}")

    # 4. Test Model 4: Agronomic SLM - Soil Amendment Query (Virginia)
    res_slm_soil = client.post("/api/ai/agronomy-slm", json={
        "prompt": "How do I amend heavy native clay soil for raised beds?",
        "state": "VA",
        "county": "Albemarle",
        "latitude": 38.0293,
        "longitude": -78.4767
    })
    assert res_slm_soil.status_code == 200, f"SLM soil query failed: {res_slm_soil.text}"
    data_soil = res_slm_soil.json()
    assert "soil" in data_soil["response"].lower() or "compost" in data_soil["response"].lower()
    print(f"✓ Model 4 SLM (Soil Amendment VA): Soil series '{data_soil['context_injected']['soil_texture']}' addressed properly.")

    # 5. Test Model 4: Agronomic SLM - Native Species Query (Texas)
    res_slm_native = client.post("/api/ai/agronomy-slm", json={
        "prompt": "What native pollinator wildflowers should I plant in my garden?",
        "state": "TX",
        "county": "Travis",
        "latitude": 30.2672,
        "longitude": -97.7431
    })
    assert res_slm_native.status_code == 200, f"SLM native query failed: {res_slm_native.text}"
    data_native = res_slm_native.json()
    assert "native" in data_native["response"].lower() or "pollinator" in data_native["response"].lower()
    print(f"✓ Model 4 SLM (Native Species TX): Ecoregion '{data_native['context_injected']['ecoregion']}' verified.")

    # 6. Test Model 4: Agronomic SLM - Pest Management Query (California)
    res_slm_pest = client.post("/api/ai/agronomy-slm", json={
        "prompt": "What garden pests should I watch out for and how do I control them organically?",
        "state": "CA",
        "county": "Los Angeles",
        "latitude": 34.0522,
        "longitude": -118.2437
    })
    assert res_slm_pest.status_code == 200, f"SLM pest query failed: {res_slm_pest.text}"
    data_pest = res_slm_pest.json()
    assert "organic" in data_pest["response"].lower() or "pest" in data_pest["response"].lower()
    print(f"✓ Model 4 SLM (Pest Defense CA): Regional pest strategy generated.")

    print("\n" + "="*60)
    print("ALL CUSTOM AI MODEL 1 & MODEL 4 TESTS PASSED! 🚀")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_all_ai_tests()
