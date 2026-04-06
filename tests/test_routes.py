import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import app  # noqa: E402



def test_public_routes_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/events" in paths
    assert "/events/{event_id}" in paths
    assert "/events/{event_id}/dashboard" in paths
    assert "/events/{event_id}/stream" in paths
    assert "/feeders/directories" in paths
