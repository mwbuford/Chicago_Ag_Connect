"""Tests for Chicago (Cook County) urban food scope."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import (
    DEFAULT_STATE,
    CHICAGO_METRO_COUNTIES,
    is_chicago_metro_county,
    resolve_query_state,
)
from backend.services.state_lookup import normalize_state_code, resolve_state_code
from backend.services.data_store import consumer_store
from backend.models.spatial import ConsumerMapFilter


def test_chicago_config():
    assert DEFAULT_STATE == "CHICAGO"
    assert CHICAGO_METRO_COUNTIES == ["Cook"]
    assert is_chicago_metro_county("Cook County")
    assert not is_chicago_metro_county("DuPage")
    assert not is_chicago_metro_county("Champaign")
    assert resolve_query_state("chicago") == "CHICAGO"
    assert normalize_state_code("CHICAGO") == "IL"
    assert resolve_state_code("CHICAGO", 41.8781, -87.6298) == "IL"


def test_chicago_metro_query():
    locs = consumer_store.query(ConsumerMapFilter(state="CHICAGO"))
    assert len(locs) > 40
    for loc in locs:
        assert loc.state_code == "IL"
        assert is_chicago_metro_county(loc.county)
    sources = {getattr(loc, "data_source", None) for loc in locs}
    assert any(s and "city_of_chicago" in s for s in sources) or any(
        loc.entity_type.value == "urban_farm" for loc in locs
    )


def test_chicago_counties_endpoint_data():
    counties = consumer_store.get_counties_for_state("CHICAGO")
    names = {c["county"] for c in counties}
    assert "Cook" in names
    assert all(is_chicago_metro_county(c["county"]) for c in counties)


if __name__ == "__main__":
    test_chicago_config()
    test_chicago_metro_query()
    test_chicago_counties_endpoint_data()
    print("✓ chicago tests passed")
