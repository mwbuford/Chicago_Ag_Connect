"""Tests for state code resolution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.state_lookup import resolve_state_code, normalize_state_code, state_from_coordinates


def test_state_lookup():
    assert normalize_state_code("Virginia") == "VA"
    assert normalize_state_code("va") == "VA"
    assert normalize_state_code("ALL") is None
    assert state_from_coordinates(38.0293, -78.4767) == "VA"
    assert state_from_coordinates(30.2672, -97.7431) == "TX"
    assert resolve_state_code("ALL", 38.0293, -78.4767) == "VA"
    assert resolve_state_code(None, 41.8781, -87.6298) == "IL"
    print("✓ state_lookup tests passed")


if __name__ == "__main__":
    test_state_lookup()
