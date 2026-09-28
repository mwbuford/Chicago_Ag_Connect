import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

# Use isolated marketplace data for tests
os.environ["MARKETPLACE_TEST"] = "1"

from backend.main import app
from backend.services.data_store import consumer_store
from backend.config import MARKETPLACE_DATA_DIR

client = TestClient(app)


def _get_sample_market_id():
    consumer_store.initialize()
    for loc in consumer_store._locations:
        if loc.entity_type.value == "farmers_market" and loc.state_code == "VA":
            return loc.id, loc.name
    return consumer_store._locations[0].id, consumer_store._locations[0].name


def run_marketplace_tests():
    print("\n" + "=" * 60)
    print("MARKETPLACE PHASE 0 / 2 / 3 TEST SUITE")
    print("=" * 60)

    market_id, market_name = _get_sample_market_id()
    print(f"Using test market: {market_name} ({market_id})")

    # Phase 0: Auth
    email = f"test_vendor_{date.today().isoformat().replace('-','')}@example.com"
    res_reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "secret123",
        "display_name": "Test Vendor",
        "role": "consumer"
    })
    assert res_reg.status_code == 200, res_reg.text
    token = res_reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Phase 0: User registration works")

    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    user = res_me.json()
    assert user["display_name"] == "Test Vendor"
    print("✓ Phase 0: Auth token / me endpoint works")

    # Phase 2: Vendor profile
    res_vendor = client.post("/api/vendors", headers=headers, json={
        "farm_name": "Blue Ridge Honey Farm",
        "product_tags": ["raw_honey", "eggs"],
        "sells_direct": True,
        "farm_stand_lat": 38.0293,
        "farm_stand_lon": -78.4767
    })
    assert res_vendor.status_code == 200, res_vendor.text
    vendor = res_vendor.json()
    vendor_id = vendor["id"]
    assert vendor["farm_name"] == "Blue Ridge Honey Farm"
    print(f"✓ Phase 2: Vendor profile created ({vendor_id})")

    visit_date = date.today().isoformat()

    # Vendor self-report presence
    res_presence = client.post(f"/api/markets/{market_id}/presence", headers=headers, json={
        "visit_date": visit_date,
        "products_available": ["raw honey", "eggs", "sourdough"],
        "booth_hint": "Near the fountain"
    })
    assert res_presence.status_code == 200, res_presence.text
    presence = res_presence.json()
    assert presence["vendor_confirmed"] is True
    assert presence["reported_by"] == "vendor"
    print("✓ Phase 2: Vendor self-reported presence at market")

    # Community user logs another vendor
    email2 = f"test_shopper_{date.today().isoformat().replace('-','')}@example.com"
    res_reg2 = client.post("/api/auth/register", json={
        "email": email2,
        "password": "secret123",
        "display_name": "Test Shopper",
        "role": "consumer"
    })
    headers2 = {"Authorization": f"Bearer {res_reg2.json()['token']}"}

    res_community = client.post(f"/api/markets/{market_id}/community-visit", headers=headers2, json={
        "visit_date": visit_date,
        "vendor_entries": [
            {"vendor_name": "Goat Lady Dairy", "products_seen": ["goat milk", "cheese"], "booth_hint": "Row B"},
            {"vendor_name": "Baker Bros", "products_seen": ["sourdough", "bread"]}
        ]
    })
    assert res_community.status_code == 200, res_community.text
    assert len(res_community.json()) == 2
    print("✓ Phase 2: Community visit log (2 vendors) submitted")

    # Attendance merge view
    res_att = client.get(f"/api/markets/{market_id}/attendance?visit_date={visit_date}")
    assert res_att.status_code == 200
    att = res_att.json()
    assert att["total_vendors"] >= 3
    vendor_names = [v["farm_name"] for v in att["vendors"]]
    assert "Blue Ridge Honey Farm" in vendor_names
    assert any("Goat Lady" in n for n in vendor_names)
    print(f"✓ Phase 2: Attendance merged view shows {att['total_vendors']} vendors")

    # Phase 3: Product search
    res_search = client.get(f"/api/search/products?q=goat+milk&state=VA&when=any")
    assert res_search.status_code == 200
    search = res_search.json()
    assert search["total"] >= 1
    assert "goat_milk" in search["matched_tags"] or "goat" in search["normalized_query"]
    print(f"✓ Phase 3: Product search 'goat milk' → {search['total']} hit(s)")

    res_honey = client.get(f"/api/search/products?q=raw+honey&state=VA&when=today")
    assert res_honey.status_code == 200
    honey = res_honey.json()
    assert honey["total"] >= 1
    top = honey["results"][0]
    assert top["confidence"] >= 0.5
    print(f"✓ Phase 3: Product search 'raw honey' → top hit: {top.get('vendor_name') or top.get('market_name')}")

    res_tags = client.get("/api/search/product-tags")
    assert res_tags.status_code == 200
    assert len(res_tags.json()) >= 10
    print(f"✓ Phase 3: Product taxonomy has {len(res_tags.json())} tags")

    print("\n" + "=" * 60)
    print("ALL MARKETPLACE TESTS PASSED! 🚀")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_marketplace_tests()
